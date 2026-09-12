"""Independent numerical, physical, and comparison checks for Question 2."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from q2_model import Q2Config


ENERGY_COLUMNS = (
    "plan_kwh",
    "emergency_kwh",
    "charge_kwh",
    "discharge_kwh",
    "curtailment_kwh",
    "unused_plan_kwh",
)
COST_COLUMNS = ("plan_cost_yuan", "emergency_cost_yuan", "total_cost_yuan")


def verify_dispatch(frame: pd.DataFrame, config: Q2Config) -> dict[str, float | bool]:
    required = {
        "load_kwh",
        "pv_kwh",
        "plan_kwh",
        "charge_kwh",
        "discharge_kwh",
        "emergency_kwh",
        "pv_used_kwh",
        "plan_used_kwh",
        "soc_start_kwh",
        "soc_end_kwh",
        "price_yuan_per_kwh",
        "plan_cost_yuan",
        "emergency_cost_yuan",
        "total_cost_yuan",
    }
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Dispatch is missing columns: {sorted(missing)}")
    if frame.empty:
        raise ValueError("Dispatch is empty")
    values = frame[list(required)].to_numpy(dtype=float)
    if not np.isfinite(values).all():
        raise AssertionError("Dispatch contains non-finite values")

    tolerance = config.energy_tolerance_kwh
    load = frame["load_kwh"].to_numpy()
    pv = frame["pv_kwh"].to_numpy()
    plan = frame["plan_kwh"].to_numpy()
    charge = frame["charge_kwh"].to_numpy()
    discharge = frame["discharge_kwh"].to_numpy()
    emergency = frame["emergency_kwh"].to_numpy()
    pv_used = frame["pv_used_kwh"].to_numpy()
    plan_used = frame["plan_used_kwh"].to_numpy()
    soc_start = frame["soc_start_kwh"].to_numpy()
    soc_end = frame["soc_end_kwh"].to_numpy()
    price = frame["price_yuan_per_kwh"].to_numpy()

    balance_residual = (
        plan_used + pv_used + discharge + emergency - load - charge
    )
    soc_residual = (
        soc_end
        - soc_start
        - config.eta_c * charge
        + discharge / config.eta_d
    )
    emergency_residual = emergency - np.maximum(
        load - pv - plan - discharge,
        0.0,
    )
    expected_plan_cost = price * plan
    expected_emergency_cost = config.emergency_multiplier * price * emergency
    cost_residual = frame["total_cost_yuan"].to_numpy() - (
        expected_plan_cost + expected_emergency_cost
    )

    failures: list[str] = []
    if np.max(np.abs(balance_residual)) > tolerance:
        failures.append("supply balance")
    if np.max(np.abs(soc_residual)) > tolerance:
        failures.append("SOC recurrence")
    if np.max(np.abs(emergency_residual)) > tolerance:
        failures.append("emergency definition")
    if min(soc_start.min(), soc_end.min()) < config.soc_min_kwh - tolerance:
        failures.append("SOC lower bound")
    if max(soc_start.max(), soc_end.max()) > config.soc_max_kwh + tolerance:
        failures.append("SOC upper bound")
    if np.any(plan < -tolerance) or np.any(charge < -tolerance):
        failures.append("nonnegative plan/charge")
    if np.any(discharge < -tolerance) or np.any(emergency < -tolerance):
        failures.append("nonnegative discharge/emergency")
    if max(charge.max(), discharge.max()) > config.interval_limit_kwh + tolerance:
        failures.append("charge/discharge interval limit")
    if np.any((charge > tolerance) & (discharge > tolerance)):
        failures.append("simultaneous charge and discharge")
    if np.any((charge > tolerance) & (emergency > tolerance)):
        failures.append("emergency purchase used while charging")
    if np.any(plan_used < -tolerance) or np.any(plan_used > plan + tolerance):
        failures.append("planned energy allocation")
    if np.any(pv_used < -tolerance) or np.any(pv_used > pv + tolerance):
        failures.append("photovoltaic allocation")
    if not np.allclose(
        frame["plan_cost_yuan"], expected_plan_cost, atol=tolerance, rtol=1.0e-10
    ):
        failures.append("planned cost")
    if not np.allclose(
        frame["emergency_cost_yuan"],
        expected_emergency_cost,
        atol=tolerance,
        rtol=1.0e-10,
    ):
        failures.append("emergency cost")
    if np.max(np.abs(cost_residual)) > tolerance:
        failures.append("total cost")
    if len(frame) > 1:
        continuity = np.max(np.abs(soc_end[:-1] - soc_start[1:]))
        if continuity > tolerance:
            failures.append("within-day SOC continuity")
    else:
        continuity = 0.0
    if failures:
        raise AssertionError("Question 2 dispatch check failed: " + ", ".join(failures))

    return {
        "passed": True,
        "balance_max_abs_kwh": float(np.max(np.abs(balance_residual))),
        "soc_recurrence_max_abs_kwh": float(np.max(np.abs(soc_residual))),
        "emergency_definition_max_abs_kwh": float(
            np.max(np.abs(emergency_residual))
        ),
        "cost_max_abs_yuan": float(np.max(np.abs(cost_residual))),
        "within_day_soc_continuity_max_abs_kwh": float(continuity),
        "soc_min_kwh": float(min(soc_start.min(), soc_end.min())),
        "soc_max_kwh": float(max(soc_start.max(), soc_end.max())),
        "max_charge_kwh": float(charge.max()),
        "max_discharge_kwh": float(discharge.max()),
        "charge_discharge_conflicts": int(
            np.sum((charge > tolerance) & (discharge > tolerance))
        ),
        "charge_emergency_conflicts": int(
            np.sum((charge > tolerance) & (emergency > tolerance))
        ),
    }


def summarize_day(frame: pd.DataFrame) -> dict[str, float | int]:
    result = {
        column: float(frame[column].sum())
        for column in ENERGY_COLUMNS + COST_COLUMNS
    }
    result.update(
        soc_start_kwh=float(frame["soc_start_kwh"].iloc[0]),
        soc_end_kwh=float(frame["soc_end_kwh"].iloc[-1]),
        emergency_intervals=int((frame["emergency_kwh"] > 2.0e-5).sum()),
    )
    return result


def verify_period(
    detail: pd.DataFrame,
    daily: pd.DataFrame,
    config: Q2Config,
    expected_days: int,
) -> dict[str, float | int | bool]:
    if detail.duplicated(["date", "t"]).any():
        raise AssertionError("Duplicate date/interval keys in Question 2 detail")
    grouped_size = detail.groupby("date").size()
    if len(grouped_size) != expected_days or not grouped_size.eq(144).all():
        raise AssertionError("Question 2 detail must contain 144 rows per expected day")
    if len(daily) != expected_days:
        raise AssertionError("Question 2 daily row count is incorrect")
    if not pd.DatetimeIndex(detail["date"].drop_duplicates()).is_monotonic_increasing:
        raise AssertionError("Question 2 detail dates are not increasing")
    if not pd.DatetimeIndex(daily["date"]).is_monotonic_increasing:
        raise AssertionError("Question 2 daily dates are not increasing")
    cross_day = np.max(
        np.abs(
            daily["soc_end_kwh"].to_numpy()[:-1]
            - daily["soc_start_kwh"].to_numpy()[1:]
        )
    ) if expected_days > 1 else 0.0
    if cross_day > config.energy_tolerance_kwh:
        raise AssertionError("Question 2 SOC is not continuous across days")

    recalculated = detail.groupby("date", sort=True)[
        list(ENERGY_COLUMNS + COST_COLUMNS)
    ].sum()
    reported = daily.set_index("date")
    maximum_daily_difference = 0.0
    for column in recalculated.columns:
        difference = np.max(np.abs(recalculated[column] - reported[column]))
        maximum_daily_difference = max(maximum_daily_difference, float(difference))
    if maximum_daily_difference > config.energy_tolerance_kwh:
        raise AssertionError("Daily totals do not match the interval detail")
    if not daily["source_causal"].all():
        raise AssertionError("A day-ahead scenario used non-causal data")
    if not daily["plan_frozen"].all():
        raise AssertionError("A day-ahead plan was not frozen")
    if not daily["physical_checks_passed"].all():
        raise AssertionError("A daily physical audit failed")

    return {
        "passed": True,
        "days": expected_days,
        "detail_rows": len(detail),
        "cross_day_soc_max_abs_kwh": float(cross_day),
        "daily_recalculation_max_abs": maximum_daily_difference,
        "total_cost_yuan": float(detail["total_cost_yuan"].sum()),
    }


def comparison_table(
    stochastic_daily: pd.DataFrame,
    point_daily: pd.DataFrame,
) -> pd.DataFrame:
    def row(name: str, frame: pd.DataFrame) -> dict[str, float | int | str]:
        return {
            "method": name,
            "total_cost_yuan": float(frame["total_cost_yuan"].sum()),
            "plan_cost_yuan": float(frame["plan_cost_yuan"].sum()),
            "emergency_cost_yuan": float(frame["emergency_cost_yuan"].sum()),
            "plan_kwh": float(frame["plan_kwh"].sum()),
            "emergency_kwh": float(frame["emergency_kwh"].sum()),
            "emergency_days": int((frame["emergency_kwh"] > 2.0e-5).sum()),
            "emergency_intervals": int(frame["emergency_intervals"].sum()),
            "curtailment_kwh": float(frame["curtailment_kwh"].sum()),
            "unused_plan_kwh": float(frame["unused_plan_kwh"].sum()),
            "charge_kwh": float(frame["charge_kwh"].sum()),
            "discharge_kwh": float(frame["discharge_kwh"].sum()),
            "terminal_soc_kwh": float(frame["soc_end_kwh"].iloc[-1]),
        }
    return pd.DataFrame(
        [row("conflict_driven_stochastic", stochastic_daily), row("point_forecast", point_daily)]
    )


def compare_with_teammate(
    ours: pd.DataFrame,
    teammate_directory: Path,
) -> pd.DataFrame:
    teammate_path = Path(teammate_directory) / "方案对比.csv"
    if not teammate_path.is_file():
        raise FileNotFoundError(f"Teammate comparison CSV not found: {teammate_path}")
    teammate = pd.read_csv(teammate_path)
    if len(teammate) < 2:
        raise ValueError("Teammate comparison CSV must contain two methods")
    mapping = {
        "total_cost_yuan": "总购电费(元)",
        "plan_cost_yuan": "计划购电费(元)",
        "emergency_cost_yuan": "紧急购电费(元)",
        "plan_kwh": "计划购电量(kWh)",
        "emergency_kwh": "紧急购电量(kWh)",
        "emergency_days": "紧急天数",
        "curtailment_kwh": "弃光量(kWh)",
        "terminal_soc_kwh": "期末SOC(kWh)",
    }
    rows: list[dict[str, float | str]] = []
    for ours_index, teammate_index, method in (
        (0, 0, "stochastic"),
        (1, 1, "point_forecast"),
    ):
        for our_column, teammate_column in mapping.items():
            our_value = float(ours.iloc[ours_index][our_column])
            teammate_value = float(teammate.iloc[teammate_index][teammate_column])
            rows.append(
                {
                    "method": method,
                    "metric": our_column,
                    "ours": our_value,
                    "teammate": teammate_value,
                    "difference": our_value - teammate_value,
                    "relative_difference": (our_value - teammate_value)
                    / max(abs(teammate_value), 1.0),
                }
            )
    return pd.DataFrame(rows)
