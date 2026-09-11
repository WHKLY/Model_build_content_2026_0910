"""Orchestrate Question 1 without plots or environment management."""
from __future__ import annotations

from project_paths import ATTACHMENT_1, ensure_output_dir, output_dir
from q1_certificate import build_certificate, write_certificate
from q1_certificate_verify import verify_certificate_file
from q1_data import load_q1_source_data
from q1_export import export_all
from q1_model import no_storage_baseline, prepare_interval_data, solve_at_same_cost, solve_primary
from q1_verify import verify_pair


TARGET_INDEX = 140


def run_question_1() -> None:
    ensure_output_dir()
    destination = output_dir()
    source = load_q1_source_data(ATTACHMENT_1)
    interval_data = prepare_interval_data(source)

    primary_solution, lp, inequality_marginals = solve_primary(interval_data)
    plan_a = solve_at_same_cost(
        interval_data,
        lp,
        primary_solution.cost,
        target_index=TARGET_INDEX,
        sense="min",
    )
    plan_b = solve_at_same_cost(
        interval_data,
        lp,
        primary_solution.cost,
        target_index=TARGET_INDEX,
        sense="max",
    )
    baseline = no_storage_baseline(interval_data)
    checks = verify_pair(interval_data, plan_a, plan_b, lp)

    certificate = build_certificate(ATTACHMENT_1, plan_a, inequality_marginals)
    certificate_path = write_certificate(destination / "certificate_q1.json", certificate)
    certificate_verification = verify_certificate_file(certificate_path, ATTACHMENT_1)

    exported = export_all(
        destination,
        source,
        interval_data,
        baseline,
        plan_a,
        plan_b,
        checks,
        certificate,
        certificate_verification,
    )

    print("Question 1 completed.")
    print(f"Optimal purchase cost: {plan_a.cost:.10f}")
    print(f"Exact certificate gap: {certificate['gap']}")
    print(f"Output directory: {destination}")
    for name in sorted((*exported.keys(), "certificate")):
        path = certificate_path if name == "certificate" else exported[name]
        print(f"- {path.name}")
