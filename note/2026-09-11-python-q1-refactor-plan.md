# Python Question 1 Refactor Plan

## Question

Question 1 deterministic microgrid external power purchase scheduling.

## Reason For Rebuild

The project is abandoning MWorks/Syslab because the environment is too restrictive for reproducible contest verification. The formal implementation will use Python in a recorded virtual environment.

## Source Files

- `original_source/附件/附件1.xlsx` for price, load, and photovoltaic forecast data.
- Existing received analysis under `recieve/problem_1/` for model assumptions and result interpretation.

## Model Assumptions

- 144 ten-minute intervals, `dt = 1/6` hour.
- Attachment time labels are interpreted as interval endpoints.
- Battery capacity is 12000 kWh.
- SOC bounds are 1200 kWh to 10800 kWh.
- Initial and terminal SOC are both 6000 kWh.
- Charge and discharge efficiencies are both 0.9.
- Charge/discharge power limit is 5000 kW on the AC connection side.
- No sale-to-grid revenue; surplus PV may be curtailed.

## Implementation Plan

Replace the old MWorks/Syslab `scripts/` implementation with Python modules following the same structure:

- `project_paths.py` for fixed paths.
- `q1_data.py` for Attachment 1 loading and interval labels.
- `q1_model.py` for the battery-internal energy-increment LP.
- `q1_verify.py` for physical and numerical checks.
- `q1_export.py` for CSV and XLSX output.
- `q1_plot.py` for PNG/SVG visualizations.
- `q1_main.py` for orchestration.

## Expected Outputs

- `output/question_1/q1_schedule.csv`
- `output/question_1/q1_summary.csv`
- `output/question_1/q1_four_hour_summary.csv`
- `output/question_1/q1_target_purchase.csv`
- `output/question_1/q1_results.xlsx`
- three figure pairs under `output/question_1/figures/`, each as PNG and SVG.

## Checks That Must Pass When Run

- input length equals 144;
- solver success for primary and alternate LPs;
- nonnegative grid purchase;
- SOC bounds and terminal SOC;
- charge/discharge power limits;
- nonnegative PV curtailment not exceeding available PV;
- energy balance residual below tolerance;
- equal optimal cost for Plan A and Plan B;
- at least one interval-level purchase difference between Plan A and Plan B.

## Run Policy For This Refactor

The code is prepared for the teammate to run. Codex does not execute `scripts/q1_main.py` during this refactor.
