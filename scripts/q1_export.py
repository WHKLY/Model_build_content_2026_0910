"""Question 1 table and workbook exports."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from q1_data import INTERVAL_COUNT, Q1SourceData
from q1_model import BaselineSolution, IntervalData, ScheduleSolution
from q1_verify import SolutionCheck


def _round_frame(frame: pd.DataFrame) -> pd.DataFrame:
    return frame.copy()


def schedule_table(
    source: Q1SourceData,
    interval_data: IntervalData,
    plan_a: ScheduleSolution,
    plan_b: ScheduleSolution,
) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "index": np.arange(1, INTERVAL_COUNT + 1),
            "source_time": source.source_time,
            "interval": source.interval,
            "price_yuan_per_kwh": interval_data.price,
            "load_kw": interval_data.load_kw,
            "pv_forecast_kw": interval_data.pv_kw,
            "load_kwh": interval_data.load_kwh,
            "pv_forecast_kwh": interval_data.pv_kwh,
            "grid_A_kwh": plan_a.grid_kwh,
            "charge_A_kwh": plan_a.charge_kwh,
            "discharge_A_kwh": plan_a.discharge_kwh,
            "curtail_A_kwh": plan_a.curtail_kwh,
            "soc_A_kwh": plan_a.soc_kwh,
            "grid_B_kwh": plan_b.grid_kwh,
            "charge_B_kwh": plan_b.charge_kwh,
            "discharge_B_kwh": plan_b.discharge_kwh,
            "curtail_B_kwh": plan_b.curtail_kwh,
            "soc_B_kwh": plan_b.soc_kwh,
            "diff_grid_B_minus_A_kwh": plan_b.grid_kwh - plan_a.grid_kwh,
            "diff_soc_B_minus_A_kwh": plan_b.soc_kwh - plan_a.soc_kwh,
        }
    )


def summary_table(
    baseline: BaselineSolution,
    plan_a: ScheduleSolution,
    plan_b: ScheduleSolution,
    checks: dict[str, SolutionCheck],
) -> pd.DataFrame:
    rows = [
        ("no_storage_cost_yuan", baseline.cost),
        ("no_storage_grid_kwh", baseline.total_grid_kwh),
        ("plan_A_cost_yuan", plan_a.cost),
        ("plan_A_grid_kwh", plan_a.total_grid_kwh),
        ("plan_A_charge_kwh", plan_a.total_charge_kwh),
        ("plan_A_discharge_kwh", plan_a.total_discharge_kwh),
        ("plan_A_curtail_kwh", plan_a.total_curtail_kwh),
        ("plan_A_target_index", plan_a.target_index),
        ("plan_A_target_grid_kwh", plan_a.target_grid_kwh),
        ("plan_A_max_balance_residual", checks["plan_a"].max_balance_residual),
        ("plan_B_cost_yuan", plan_b.cost),
        ("plan_B_grid_kwh", plan_b.total_grid_kwh),
        ("plan_B_charge_kwh", plan_b.total_charge_kwh),
        ("plan_B_discharge_kwh", plan_b.total_discharge_kwh),
        ("plan_B_curtail_kwh", plan_b.total_curtail_kwh),
        ("plan_B_target_index", plan_b.target_index),
        ("plan_B_target_grid_kwh", plan_b.target_grid_kwh),
        ("plan_B_max_balance_residual", checks["plan_b"].max_balance_residual),
        ("cost_saving_A_vs_no_storage_yuan", baseline.cost - plan_a.cost),
        ("cost_saving_B_vs_no_storage_yuan", baseline.cost - plan_b.cost),
        ("max_abs_grid_difference_B_minus_A_kwh", float(np.max(np.abs(plan_b.grid_kwh - plan_a.grid_kwh)))),
        ("model_note", "same optimal purchase cost, different interval-level purchase schedules"),
    ]
    return pd.DataFrame(rows, columns=["metric", "value"])


def four_hour_table(plan_a: ScheduleSolution, plan_b: ScheduleSolution) -> pd.DataFrame:
    labels = ["00:00-04:00", "04:00-08:00", "08:00-12:00", "12:00-16:00", "16:00-20:00", "20:00-24:00"]
    rows = []
    for k, label in enumerate(labels):
        idx = slice(k * 24, (k + 1) * 24)
        rows.append(
            {
                "interval": label,
                "charge_A_kwh": float(np.sum(plan_a.charge_kwh[idx])),
                "discharge_A_kwh": float(np.sum(plan_a.discharge_kwh[idx])),
                "grid_A_kwh": float(np.sum(plan_a.grid_kwh[idx])),
                "charge_B_kwh": float(np.sum(plan_b.charge_kwh[idx])),
                "discharge_B_kwh": float(np.sum(plan_b.discharge_kwh[idx])),
                "grid_B_kwh": float(np.sum(plan_b.grid_kwh[idx])),
            }
        )
    return pd.DataFrame(rows)


def target_purchase_table(source: Q1SourceData, plan_a: ScheduleSolution, plan_b: ScheduleSolution) -> pd.DataFrame:
    targets = ["10:00-10:10", "12:00-12:10", "14:00-14:10", "16:00-16:10", "18:00-18:10", "20:00-20:10"]
    rows = []
    for interval in targets:
        try:
            idx = source.interval.index(interval)
        except ValueError as exc:
            raise ValueError(f"target interval not found: {interval}") from exc
        rows.append(
            {
                "interval": interval,
                "index": idx + 1,
                "grid_A_kwh": float(plan_a.grid_kwh[idx]),
                "grid_B_kwh": float(plan_b.grid_kwh[idx]),
            }
        )
    return pd.DataFrame(rows)


def export_all(
    outdir: Path,
    source: Q1SourceData,
    interval_data: IntervalData,
    baseline: BaselineSolution,
    plan_a: ScheduleSolution,
    plan_b: ScheduleSolution,
    checks: dict[str, SolutionCheck],
) -> dict[str, Path]:
    outdir.mkdir(parents=True, exist_ok=True)
    schedule = schedule_table(source, interval_data, plan_a, plan_b)
    summary = summary_table(baseline, plan_a, plan_b, checks)
    four_hour = four_hour_table(plan_a, plan_b)
    target_purchase = target_purchase_table(source, plan_a, plan_b)

    paths = {
        "schedule_csv": outdir / "q1_schedule.csv",
        "summary_csv": outdir / "q1_summary.csv",
        "four_hour_csv": outdir / "q1_four_hour_summary.csv",
        "target_purchase_csv": outdir / "q1_target_purchase.csv",
        "workbook": outdir / "q1_results.xlsx",
    }

    schedule.to_csv(paths["schedule_csv"], index=False, encoding="utf-8-sig", float_format="%.10f")
    summary.to_csv(paths["summary_csv"], index=False, encoding="utf-8-sig")
    four_hour.to_csv(paths["four_hour_csv"], index=False, encoding="utf-8-sig", float_format="%.10f")
    target_purchase.to_csv(paths["target_purchase_csv"], index=False, encoding="utf-8-sig", float_format="%.10f")

    with pd.ExcelWriter(paths["workbook"], engine="xlsxwriter") as writer:
        schedule.to_excel(writer, sheet_name="schedule", index=False)
        summary.to_excel(writer, sheet_name="summary", index=False)
        four_hour.to_excel(writer, sheet_name="four_hour", index=False)
        target_purchase.to_excel(writer, sheet_name="target_purchase", index=False)

    return paths
