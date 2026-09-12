"""Run real-data comparisons for the isolated incremental-MILP demo."""

from __future__ import annotations

import argparse
import csv
from dataclasses import replace
from datetime import datetime
from pathlib import Path

import numpy as np

from q2_incremental_milp import (
    Config,
    ROOT_DIR,
    load_raw_inputs,
    make_joint_scenarios,
    numerical_objective_agreement,
    prepare_causal_forecast,
    solve_full_milp,
    solve_incremental_milp,
)


DEFAULT_DATES = (
    "2025-03-20",
    "2025-06-21",
    "2025-09-23",
    "2025-12-21",
)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compare conflict-driven incremental MILP with the full Question 2 "
            "MILP on selected dates."
        )
    )
    parser.add_argument("--dates", nargs="+", default=list(DEFAULT_DATES))
    parser.add_argument("--scenario-count", type=int, default=20)
    parser.add_argument("--mip-relative-gap", type=float, default=1e-4)
    parser.add_argument("--time-limit", type=float, default=60.0)
    parser.add_argument("--max-iterations", type=int, default=20)
    parser.add_argument(
        "--activation-scope",
        choices=("pair", "scenario", "interval"),
        default="scenario",
        help=(
            "Activate exact conflicting pairs, all intervals of a conflicting "
            "scenario, or all scenarios of a conflicting interval."
        ),
    )
    parser.add_argument(
        "--trace",
        action="store_true",
        help="Print conflict counts and solve time after every incremental round.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT_DIR / "demo" / "output" / "q2_incremental_comparison.csv",
    )
    return parser.parse_args()


def _day_index(dates: tuple[datetime, ...], text: str) -> int:
    target = datetime.strptime(text, "%Y-%m-%d")
    try:
        return dates.index(target)
    except ValueError as exc:
        raise ValueError(f"Date {text} is not present in Attachment 2.") from exc


def run_comparison(arguments: argparse.Namespace) -> list[dict[str, object]]:
    config = replace(
        Config(),
        scenario_count=arguments.scenario_count,
        mip_relative_gap=arguments.mip_relative_gap,
        mip_time_limit_seconds=arguments.time_limit,
    ).validate()
    data = load_raw_inputs()
    forecast = prepare_causal_forecast(
        data.load_kwh,
        data.pv_kwh,
        config.forecast_window_days,
    )
    records: list[dict[str, object]] = []
    for date_text in arguments.dates:
        day = _day_index(data.dates, date_text)
        scenario_load, scenario_pv, weights, sources = make_joint_scenarios(
            day,
            forecast,
            data.load_kwh,
            data.pv_kwh,
            config,
        )
        terminal_free = day == len(data.dates) - 1
        incremental = solve_incremental_milp(
            scenario_load,
            scenario_pv,
            weights,
            data.price,
            config.initial_soc_kwh,
            config,
            terminal_free=terminal_free,
            max_iterations=arguments.max_iterations,
            activation_scope=arguments.activation_scope,
            trace=arguments.trace,
        )
        full = solve_full_milp(
            scenario_load,
            scenario_pv,
            weights,
            data.price,
            config.initial_soc_kwh,
            config,
            terminal_free=terminal_free,
        )
        candidate = incremental.solution
        plan_difference = candidate.plan_kwh - full.plan_kwh
        objective_difference = candidate.objective - full.objective
        record = {
            "date": date_text,
            "scenario_count": len(weights),
            "activation_scope": arguments.activation_scope,
            "source_day_max": int(sources.max()),
            "total_possible_binaries": int(scenario_load.size),
            "lp_objective_lower_bound": incremental.relaxation.objective,
            "lp_initial_conflicts": len(incremental.relaxation.conflicts),
            "incremental_iterations": incremental.iterations,
            "incremental_binary_history": ">".join(
                map(str, incremental.binary_history)
            ),
            "incremental_active_binaries": candidate.active_binary_count,
            "incremental_success": candidate.success,
            "incremental_status_code": candidate.status_code,
            "incremental_message": candidate.message,
            "full_success": full.success,
            "full_status_code": full.status_code,
            "full_message": full.message,
            "incremental_objective": candidate.objective,
            "full_objective": full.objective,
            "objective_difference": objective_difference,
            "objective_relative_difference": objective_difference
            / max(abs(full.objective), 1.0),
            "bound_intervals_overlap": numerical_objective_agreement(
                candidate, full
            ),
            "incremental_gap": candidate.relative_gap,
            "full_gap": full.relative_gap,
            "incremental_dual_bound": candidate.dual_bound,
            "full_dual_bound": full.dual_bound,
            "incremental_nodes": candidate.node_count,
            "full_nodes": full.node_count,
            "incremental_total_build_seconds": incremental.total_build_seconds,
            "incremental_total_solve_seconds": incremental.total_solve_seconds,
            "full_build_seconds": full.build_seconds,
            "full_solve_seconds": full.solve_seconds,
            "solve_speedup_full_over_incremental": full.solve_seconds
            / max(incremental.total_solve_seconds, 1e-12),
            "max_plan_abs_difference_kwh": float(
                np.max(np.abs(plan_difference))
            ),
            "sum_plan_abs_difference_kwh": float(
                np.sum(np.abs(plan_difference))
            ),
            "incremental_remaining_conflicts": len(candidate.conflicts),
            "full_remaining_conflicts": len(full.conflicts),
            "incremental_full_model_feasible": not candidate.conflicts,
            "incremental_certified_within_reported_gap": (
                candidate.success and not candidate.conflicts
            ),
            "incremental_max_constraint_violation": (
                candidate.max_constraint_violation
            ),
            "full_max_constraint_violation": full.max_constraint_violation,
        }
        records.append(record)
        print(
            f"{date_text} | LP conflicts={record['lp_initial_conflicts']} | "
            f"incremental binaries={record['incremental_active_binaries']}/"
            f"{record['total_possible_binaries']} | "
            f"rounds={record['incremental_iterations']} | "
            f"objective diff={objective_difference:.6g} | "
            f"solve={incremental.total_solve_seconds:.3f}s vs "
            f"{full.solve_seconds:.3f}s",
            flush=True,
        )
    return records


def write_csv(records: list[dict[str, object]], output_path: Path) -> None:
    output_path = output_path.resolve()
    allowed_directory = (ROOT_DIR / "demo" / "output").resolve()
    if output_path.parent != allowed_directory:
        raise ValueError(f"Demo output must be written directly under {allowed_directory}.")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)
    print(f"Comparison CSV written: {output_path}")


def main() -> None:
    arguments = parse_arguments()
    records = run_comparison(arguments)
    if not records:
        raise RuntimeError("No comparison dates were supplied.")
    write_csv(records, arguments.output)


if __name__ == "__main__":
    main()
