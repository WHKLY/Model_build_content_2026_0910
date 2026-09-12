"""Complete Question 2 workflow using conflict-driven incremental MILP."""
from __future__ import annotations

import argparse
from dataclasses import asdict, replace
from hashlib import sha256
import json
from pathlib import Path

import numpy as np
import pandas as pd

from project_paths import TEMPLATE_RESULT_2, q2_output_dir
from q2_control import simulate_frozen_plan_day
from q2_data import (
    CausalForecast,
    Q2SourceData,
    load_q2_source,
    make_joint_residual_scenarios,
    point_forecast_scenario,
    prepare_causal_forecast,
)
from q2_export import export_q2_outputs
from q2_model import (
    Q2Config,
    objective_intervals_overlap,
    solve_full_milp,
    solve_incremental_milp,
)
from q2_verify import (
    compare_with_teammate,
    comparison_table,
    summarize_day,
    verify_dispatch,
    verify_period,
)


OUTPUT_START = pd.Timestamp("2025-02-01")
SPECIAL_DATES = (
    "2025-03-20",
    "2025-06-21",
    "2025-09-23",
    "2025-12-21",
)


def _file_sha256(path: Path) -> str:
    digest = sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _checkpoint_fingerprint(
    method: str,
    config: Q2Config,
    source: Q2SourceData,
    start_day: int,
    end_day: int,
) -> dict[str, object]:
    return {
        "format": "q2-conflict-driven-checkpoint-v1",
        "method": method,
        "config": asdict(config),
        "start_day": start_day,
        "end_day": end_day,
        "price_sha256": _file_sha256(source.price_path),
        "actual_sha256": _file_sha256(source.actual_path),
    }


def _checkpoint_paths(root: Path, method: str) -> dict[str, Path]:
    directory = Path(root) / method
    directory.mkdir(parents=True, exist_ok=True)
    return {
        "directory": directory,
        "state": directory / "state.json",
        "detail": directory / "detail.csv",
        "daily": directory / "daily.csv",
        "audit": directory / "audit.csv",
    }


def _clear_checkpoint(paths: dict[str, Path]) -> None:
    for key in ("state", "detail", "daily", "audit"):
        if paths[key].exists():
            paths[key].unlink()


def _read_checkpoint(
    paths: dict[str, Path],
    fingerprint: dict[str, object],
    fresh: bool,
) -> tuple[int, float | None, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if fresh:
        _clear_checkpoint(paths)
    if not paths["state"].is_file():
        orphaned = [paths[key] for key in ("detail", "daily", "audit") if paths[key].exists()]
        if orphaned:
            raise RuntimeError(
                f"Checkpoint state is missing under {paths['directory']} while CSV files remain; "
                "rerun with --fresh"
            )
        return 0, None, pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    state = json.loads(paths["state"].read_text(encoding="utf-8"))
    if state.get("fingerprint") != fingerprint:
        raise RuntimeError(
            f"Checkpoint parameters changed under {paths['directory']}; rerun with --fresh"
        )
    completed = int(state["completed_days"])
    detail = pd.read_csv(paths["detail"], parse_dates=["date"]).head(completed * 144)
    daily = pd.read_csv(paths["daily"], parse_dates=["date"]).head(completed)
    audit = pd.read_csv(paths["audit"], parse_dates=["date"]).head(completed)
    if len(detail) != completed * 144 or len(daily) != completed or len(audit) != completed:
        raise RuntimeError(f"Checkpoint files are incomplete under {paths['directory']}")
    detail.to_csv(paths["detail"], index=False, encoding="utf-8-sig")
    daily.to_csv(paths["daily"], index=False, encoding="utf-8-sig")
    audit.to_csv(paths["audit"], index=False, encoding="utf-8-sig")
    return completed, float(state["soc_end_kwh"]), detail, daily, audit


def _append_csv(path: Path, frame: pd.DataFrame) -> None:
    frame.to_csv(
        path,
        mode="a",
        header=not path.exists() or path.stat().st_size == 0,
        index=False,
        encoding="utf-8-sig",
        float_format="%.12g",
    )


def _commit_checkpoint(
    paths: dict[str, Path],
    fingerprint: dict[str, object],
    completed_days: int,
    soc_end_kwh: float,
    day_detail: pd.DataFrame,
    day_summary: dict[str, object],
    day_audit: dict[str, object],
) -> None:
    _append_csv(paths["detail"], day_detail)
    _append_csv(paths["daily"], pd.DataFrame([day_summary]))
    _append_csv(paths["audit"], pd.DataFrame([day_audit]))
    state = {
        "fingerprint": fingerprint,
        "completed_days": completed_days,
        "soc_end_kwh": float(soc_end_kwh),
    }
    temporary = paths["state"].with_suffix(".json.tmp")
    temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(paths["state"])


def _scenario_for_method(
    method: str,
    day: int,
    source: Q2SourceData,
    forecast: CausalForecast,
    config: Q2Config,
):
    if method == "stochastic":
        return make_joint_residual_scenarios(
            day,
            forecast,
            source,
            scenario_count=config.scenario_count,
            history_days=config.scenario_history_days,
            random_seed=config.random_seed,
            residual_scale=config.residual_scale,
        )
    if method == "point":
        return point_forecast_scenario(day, forecast)
    raise ValueError(f"Unknown Question 2 method: {method}")


def run_period(
    method: str,
    source: Q2SourceData,
    forecast: CausalForecast,
    config: Q2Config,
    checkpoint_root: Path,
    start_day: int = 0,
    end_day: int = 365,
    fresh: bool = False,
    trace: bool = False,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    paths = _checkpoint_paths(checkpoint_root, method)
    fingerprint = _checkpoint_fingerprint(method, config, source, start_day, end_day)
    completed, saved_soc, _, _, _ = _read_checkpoint(paths, fingerprint, fresh)
    state = config.initial_soc_kwh if completed == 0 else float(saved_soc)
    resume_day = start_day + completed
    if completed:
        print(
            f"[q2 {method}] resume {completed}/{end_day - start_day} days, "
            f"SOC={state:.3f} kWh",
            flush=True,
        )

    for day in range(resume_day, end_day):
        date = pd.Timestamp(source.dates[day])
        scenarios = _scenario_for_method(method, day, source, forecast, config)
        if scenarios.source_day_indices.size:
            source_causal = bool(np.max(scenarios.source_day_indices) < day)
            source_day_max = int(np.max(scenarios.source_day_indices))
        else:
            source_causal = True
            source_day_max = -1
        if not source_causal:
            raise AssertionError(f"Scenario leakage detected on {date.date()}")
        terminal_free = day == end_day - 1
        incremental = solve_incremental_milp(
            scenarios.load_kwh,
            scenarios.pv_kwh,
            scenarios.weights,
            source.price_yuan_per_kwh,
            state,
            config,
            terminal_free=terminal_free,
            trace=trace,
        )
        solution = incremental.solution
        if not solution.has_feasible_solution:
            raise RuntimeError(f"No full-model feasible plan on {date.date()}")
        day_detail = simulate_frozen_plan_day(
            source.load_kwh[day],
            source.pv_kwh[day],
            forecast.load_hat_kwh[day],
            forecast.pv_hat_kwh[day],
            source.price_yuan_per_kwh,
            solution.plan_kwh,
            state,
            source.physical_intervals,
            config,
            terminal_free=terminal_free,
        )
        day_detail.insert(0, "method", method)
        day_detail.insert(0, "date", date)
        checks = verify_dispatch(day_detail, config)
        summary: dict[str, object] = summarize_day(day_detail)
        summary.update(
            {
                "date": date,
                "method": method,
                "solver_method": solution.method,
                "solver_success": solution.solver_success,
                "solver_status_code": solution.status_code,
                "mip_gap": solution.relative_gap,
                "surrogate_objective_yuan": solution.objective_yuan,
                "dual_bound_yuan": solution.dual_bound_yuan,
                "lp_lower_bound_yuan": incremental.relaxation.objective_yuan,
                "lp_initial_conflicts": len(incremental.relaxation.conflicts),
                "incremental_rounds": incremental.rounds,
                "active_binary_count": solution.active_binary_count,
                "total_possible_binaries": int(scenarios.load_kwh.size),
                "binary_history": ">".join(map(str, incremental.binary_history)),
                "model_build_seconds": incremental.total_build_seconds,
                "model_solve_seconds": incremental.total_solve_seconds,
                "model_max_constraint_violation": solution.max_constraint_violation,
                "source_day_count": int(scenarios.source_day_indices.size),
                "source_day_max": source_day_max,
                "source_causal": source_causal,
                "plan_frozen": True,
                "physical_checks_passed": bool(checks["passed"]),
            }
        )
        audit = {
            "date": date,
            "method": method,
            **checks,
            "source_causal": source_causal,
            "plan_frozen": True,
            "solver_method": solution.method,
            "solver_success": solution.solver_success,
            "solver_status_code": solution.status_code,
            "mip_gap": solution.relative_gap,
            "lp_initial_conflicts": len(incremental.relaxation.conflicts),
            "incremental_rounds": incremental.rounds,
            "active_binary_count": solution.active_binary_count,
            "total_possible_binaries": int(scenarios.load_kwh.size),
            "model_max_constraint_violation": solution.max_constraint_violation,
        }
        state = float(summary["soc_end_kwh"])
        completed += 1
        _commit_checkpoint(
            paths,
            fingerprint,
            completed,
            state,
            day_detail,
            summary,
            audit,
        )
        if day == resume_day or completed % 15 == 0 or day == end_day - 1:
            print(
                f"[q2 {method}] {date.date()} {completed}/{end_day - start_day} "
                f"cost={float(summary['total_cost_yuan']):,.2f} "
                f"gap={solution.relative_gap:.3g} "
                f"binaries={solution.active_binary_count}/{scenarios.load_kwh.size} "
                f"solve={incremental.total_solve_seconds:.2f}s",
                flush=True,
            )

    detail = pd.read_csv(paths["detail"], parse_dates=["date"])
    daily = pd.read_csv(paths["daily"], parse_dates=["date"])
    audit = pd.read_csv(paths["audit"], parse_dates=["date"])
    verify_period(detail, daily, config, end_day - start_day)
    return detail, daily, audit


def run_solver_benchmarks(
    source: Q2SourceData,
    forecast: CausalForecast,
    config: Q2Config,
    stochastic_daily: pd.DataFrame,
) -> pd.DataFrame:
    daily = stochastic_daily.set_index(pd.to_datetime(stochastic_daily["date"]).dt.normalize())
    records: list[dict[str, object]] = []
    for date_text in SPECIAL_DATES:
        date = pd.Timestamp(date_text)
        day = source.dates.index(date.to_pydatetime())
        state = float(daily.loc[date, "soc_start_kwh"])
        scenarios = _scenario_for_method("stochastic", day, source, forecast, config)
        terminal_free = day == len(source.dates) - 1
        incremental = solve_incremental_milp(
            scenarios.load_kwh,
            scenarios.pv_kwh,
            scenarios.weights,
            source.price_yuan_per_kwh,
            state,
            config,
            terminal_free=terminal_free,
        )
        full = solve_full_milp(
            scenarios.load_kwh,
            scenarios.pv_kwh,
            scenarios.weights,
            source.price_yuan_per_kwh,
            state,
            config,
            terminal_free=terminal_free,
        )
        candidate = incremental.solution
        records.append(
            {
                "date": date,
                "initial_soc_kwh": state,
                "lp_initial_conflicts": len(incremental.relaxation.conflicts),
                "incremental_rounds": incremental.rounds,
                "incremental_active_binaries": candidate.active_binary_count,
                "full_binaries": int(scenarios.load_kwh.size),
                "incremental_objective_yuan": candidate.objective_yuan,
                "incremental_dual_bound_yuan": candidate.dual_bound_yuan,
                "incremental_gap": candidate.relative_gap,
                "full_objective_yuan": full.objective_yuan,
                "full_dual_bound_yuan": full.dual_bound_yuan,
                "full_gap": full.relative_gap,
                "objective_difference_yuan": candidate.objective_yuan - full.objective_yuan,
                "bound_intervals_overlap": objective_intervals_overlap(candidate, full),
                "incremental_solve_seconds": incremental.total_solve_seconds,
                "full_solve_seconds": full.solve_seconds,
                "solve_speedup": full.solve_seconds
                / max(incremental.total_solve_seconds, 1.0e-12),
                "max_plan_abs_difference_kwh": float(
                    np.max(np.abs(candidate.plan_kwh - full.plan_kwh))
                ),
                "incremental_conflicts": len(candidate.conflicts),
                "full_conflicts": len(full.conflicts),
            }
        )
    result = pd.DataFrame(records)
    if not result["bound_intervals_overlap"].all():
        raise AssertionError("Incremental and full MILP objective intervals do not overlap")
    return result


def _verify_export_readback(paths: dict[str, Path], expected_cost: float) -> None:
    detail = pd.read_csv(paths["detail"])
    daily = pd.read_csv(paths["daily"])
    comparison = pd.read_csv(paths["comparison"])
    if len(detail) != 334 * 144 or len(daily) != 334 or len(comparison) != 2:
        raise AssertionError("Question 2 CSV read-back row count mismatch")
    difference = abs(float(detail["total_cost_yuan"].sum()) - expected_cost)
    if difference > 1.0e-4:
        raise AssertionError(f"Question 2 CSV cost read-back mismatch: {difference}")


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Solve and verify the complete Question 2 conflict-driven MILP workflow"
    )
    parser.add_argument("--fresh", action="store_true", help="Discard matching Q2 checkpoints")
    parser.add_argument("--trace", action="store_true", help="Print each incremental MILP round")
    parser.add_argument("--scenario-count", type=int, default=20)
    parser.add_argument("--mip-relative-gap", type=float, default=1.0e-3)
    parser.add_argument("--time-limit", type=float, default=30.0)
    parser.add_argument(
        "--team-output",
        type=Path,
        help="Optional teammate output directory containing 方案对比.csv",
    )
    parser.add_argument(
        "--skip-full-benchmark",
        action="store_true",
        help="Skip four-date full-MILP solver comparison",
    )
    return parser.parse_args()


def main() -> dict[str, object]:
    arguments = parse_arguments()
    config = replace(
        Q2Config(),
        scenario_count=arguments.scenario_count,
        mip_relative_gap=arguments.mip_relative_gap,
        mip_time_limit_seconds=arguments.time_limit,
    ).validate()
    output_directory = q2_output_dir()
    output_directory.mkdir(parents=True, exist_ok=True)
    checkpoint_root = output_directory / "checkpoints"

    source = load_q2_source()
    forecast = prepare_causal_forecast(
        source.load_kwh,
        source.pv_kwh,
        config.forecast_window_days,
    )
    stochastic_detail, stochastic_daily, stochastic_audit = run_period(
        "stochastic",
        source,
        forecast,
        config,
        checkpoint_root,
        fresh=arguments.fresh,
        trace=arguments.trace,
    )
    point_detail, point_daily, _ = run_period(
        "point",
        source,
        forecast,
        config,
        checkpoint_root,
        fresh=arguments.fresh,
        trace=arguments.trace,
    )

    detail = stochastic_detail[stochastic_detail["date"] >= OUTPUT_START].reset_index(drop=True)
    daily = stochastic_daily[stochastic_daily["date"] >= OUTPUT_START].reset_index(drop=True)
    audit = stochastic_audit[stochastic_audit["date"] >= OUTPUT_START].reset_index(drop=True)
    point_output_detail = point_detail[point_detail["date"] >= OUTPUT_START].reset_index(drop=True)
    point_output_daily = point_daily[point_daily["date"] >= OUTPUT_START].reset_index(drop=True)
    verify_period(detail, daily, config, 334)
    verify_period(point_output_detail, point_output_daily, config, 334)

    comparison = comparison_table(daily, point_output_daily)
    team_comparison = None
    if arguments.team_output is not None:
        team_comparison = compare_with_teammate(comparison, arguments.team_output)
    paths = export_q2_outputs(
        output_directory,
        detail,
        daily,
        point_output_daily,
        audit,
        comparison,
        config.energy_tolerance_kwh,
        team_comparison,
        TEMPLATE_RESULT_2,
    )
    _verify_export_readback(paths, float(detail["total_cost_yuan"].sum()))

    benchmark = None
    if not arguments.skip_full_benchmark:
        benchmark = run_solver_benchmarks(source, forecast, config, stochastic_daily)
        benchmark_path = output_directory / "q2_solver_benchmark.csv"
        benchmark.to_csv(
            benchmark_path,
            index=False,
            encoding="utf-8-sig",
            float_format="%.12g",
        )
        paths["solver_benchmark"] = benchmark_path

    print("\nQuestion 2 completed.")
    print(comparison.to_string(index=False))
    if team_comparison is not None:
        total = team_comparison[
            (team_comparison["method"] == "stochastic")
            & (team_comparison["metric"] == "total_cost_yuan")
        ].iloc[0]
        print(
            "Team stochastic total-cost difference: "
            f"{total['difference']:,.2f} yuan ({total['relative_difference']:.3%})"
        )
    print(f"Official workbook: {paths['template']}")
    return {
        "config": config,
        "comparison": comparison,
        "team_comparison": team_comparison,
        "benchmark": benchmark,
        "paths": paths,
    }


if __name__ == "__main__":
    main()
