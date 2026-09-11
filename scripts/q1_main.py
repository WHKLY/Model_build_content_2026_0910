"""Question 1 Python entry point."""
from __future__ import annotations

import argparse
from pathlib import Path

from project_paths import ATTACHMENT_1, ensure_output_dirs, q1_output_dir
from q1_data import load_q1_source_data
from q1_export import export_all
from q1_model import no_storage_baseline, prepare_interval_data, solve_at_same_cost, solve_primary
from q1_plot import plot_all
from q1_verify import verify_pair


def run_question_1(*, output_dir: Path | None = None, target_index: int = 140, make_plots: bool = True) -> dict[str, object]:
    ensure_output_dirs()
    outdir = output_dir or q1_output_dir()
    source = load_q1_source_data(ATTACHMENT_1)
    interval_data = prepare_interval_data(source)

    primary_solution, lp = solve_primary(interval_data)
    plan_a = solve_at_same_cost(interval_data, lp, primary_solution.cost, target_index=target_index, sense="min")
    plan_b = solve_at_same_cost(interval_data, lp, primary_solution.cost, target_index=target_index, sense="max")
    baseline = no_storage_baseline(interval_data)
    checks = verify_pair(interval_data, plan_a, plan_b, lp)

    exported = export_all(outdir, source, interval_data, baseline, plan_a, plan_b, checks)
    figures = plot_all(source, interval_data, baseline, plan_a, plan_b, outdir / "figures") if make_plots else {}

    print("Question 1 completed.")
    print(f"No-storage cost: {baseline.cost:.10f}")
    print(f"Plan A cost: {plan_a.cost:.10f}")
    print(f"Plan B cost: {plan_b.cost:.10f}")
    print(f"Plan A g{target_index}: {plan_a.target_grid_kwh:.10f}")
    print(f"Plan B g{target_index}: {plan_b.target_grid_kwh:.10f}")
    print(f"Schedule CSV: {exported['schedule_csv']}")
    print(f"Summary CSV: {exported['summary_csv']}")
    print(f"Workbook path: {exported['workbook']}")
    print(f"Template result1 path: {exported['template_result1']}")

    return {
        "baseline": baseline,
        "plan_a": plan_a,
        "plan_b": plan_b,
        "checks": checks,
        "exported": exported,
        "figures": figures,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Solve question 1 microgrid purchase scheduling model.")
    parser.add_argument("--output-dir", type=Path, default=None, help="Override output directory. Defaults to output/question_1.")
    parser.add_argument("--target-index", type=int, default=140, help="One-based interval index used to demonstrate alternate optima.")
    parser.add_argument("--skip-plots", action="store_true", help="Export tables only, without PNG/SVG figures.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_question_1(output_dir=args.output_dir, target_index=args.target_index, make_plots=not args.skip_plots)


if __name__ == "__main__":
    main()
