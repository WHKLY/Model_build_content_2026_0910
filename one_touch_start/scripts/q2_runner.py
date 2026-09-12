"""Run the reviewed Question 2 workflow inside the contest bundle."""
from __future__ import annotations

from project_paths import TEMPLATE_RESULT_2, ensure_output_dir, output_dir
from q2_data import load_q2_source, prepare_causal_forecast
from q2_export import export_q2_outputs
from q2_main import OUTPUT_START, _verify_export_readback, run_period
from q2_model import Q2Config
from q2_verify import comparison_table, verify_period


def run_question_2() -> None:
    ensure_output_dir()
    destination = output_dir()
    checkpoint_root = destination / "checkpoints"
    config = Q2Config().validate()
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
    )
    point_detail, point_daily, _ = run_period(
        "point",
        source,
        forecast,
        config,
        checkpoint_root,
    )

    detail = stochastic_detail[stochastic_detail["date"] >= OUTPUT_START].reset_index(drop=True)
    daily = stochastic_daily[stochastic_daily["date"] >= OUTPUT_START].reset_index(drop=True)
    audit = stochastic_audit[stochastic_audit["date"] >= OUTPUT_START].reset_index(drop=True)
    point_detail = point_detail[point_detail["date"] >= OUTPUT_START].reset_index(drop=True)
    point_daily = point_daily[point_daily["date"] >= OUTPUT_START].reset_index(drop=True)
    verify_period(detail, daily, config, 334)
    verify_period(point_detail, point_daily, config, 334)
    comparison = comparison_table(daily, point_daily)
    paths = export_q2_outputs(
        destination,
        detail,
        daily,
        point_daily,
        audit,
        comparison,
        config.energy_tolerance_kwh,
        template_path=TEMPLATE_RESULT_2,
    )
    _verify_export_readback(paths, float(detail["total_cost_yuan"].sum()))

    print("Question 2 completed.")
    print(comparison.to_string(index=False))
    print(f"Official workbook: {paths['template']}")
