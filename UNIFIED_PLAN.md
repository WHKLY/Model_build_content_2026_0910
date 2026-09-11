# Unified Execution Plan

Date: 2026-09-11

This document is the project-level source of truth after reviewing:

- `/data/data/com.termux/files/home/storage/downloads/QQ/参赛论文0911-2.pdf`
- `/data/data/com.termux/files/home/storage/downloads/QQ/41016777d4c40050b84e92b2132cb7ea_3247872800853498438_m.md`

Follow this plan before changing code, outputs, or paper text. If a future request conflicts with this document, state the conflict first and update this document only after the team explicitly chooses a new rule.

## 1. Current Project Position

The project has abandoned MWorks/Syslab. The formal implementation is Python.

Question 1 already has a working Python implementation that reproduces the main paper numbers:

- no-storage cost: 48052.05 yuan;
- optimized cost: 35126.95 yuan;
- saving versus no-storage: 12925.10 yuan, 26.90%;
- Plan A total grid purchase: 59482.70 kWh;
- Plan A charge/discharge totals: 20740.67 kWh and 16799.94 kWh;
- initial and terminal SOC: 6000.00 kWh.

The current Python result is usable as a computational baseline, but it is not yet a complete contest submission package. The review Markdown identifies missing submission-grade pieces that must be fixed before final delivery.

## 2. Runtime And Dependency Policy

Use Python as the only formal runtime. Do not return to MWorks/Syslab.

The repository must support a clean, judge-friendly Python environment. Termux is allowed for development, but Termux system packages are not enough as the final reproducibility story.

Required environment work:

1. Choose and document the target verification environment. Preferred target is Windows x64 CPython 3.12, because the review already tested that family of environment.
2. Create a clean venv in that target environment.
3. Install dependencies from `requirements.txt` without relying on preinstalled scientific packages.
4. Run `python scripts/q1_main.py` from the clean venv.
5. Record `python --version`, `python -m pip --version`, and `python -m pip freeze` under `env/`.

Do not pin package versions that have not been clean-install tested on the target environment. The review found `matplotlib==3.11.2` unsuitable for Windows CPython 3.12 through the tested index. Fix requirements against a real clean install before claiming reproducibility.

## 3. Question 1 Model Policy

Use the current deterministic battery-internal energy-increment LP as the baseline model.

Keep these assumptions fixed unless the paper and code are updated together:

- 144 ten-minute intervals;
- attachment time labels interpreted as interval endpoints;
- load and PV power converted to interval energy using `dt = 1/6` hour;
- battery capacity 12000 kWh;
- SOC bounds 1200 to 10800 kWh;
- initial SOC and terminal SOC both 6000 kWh;
- charge efficiency and discharge efficiency both 0.9;
- charge/discharge power limit 5000 kW on the AC side;
- no sale-to-grid revenue;
- surplus PV may be curtailed;
- discharge cannot exceed same-interval load in the current formulation.

The discharge-not-exceed-load constraint must be mentioned in the paper, because it is stricter than a pure power-limit statement. It is acceptable if described as the no-sale/no-dump interpretation of the physical model.

## 4. Output Policy

Keep two output layers separate.

Audit outputs:

- `q1_schedule.csv`
- `q1_summary.csv`
- `q1_four_hour_summary.csv`
- `q1_target_purchase.csv`
- `q1_results.xlsx`
- PNG/SVG figures

Contest template outputs:

- official `result1.xlsx`, based on `original_source/附件/附件5/result1.xlsx`.

The current code now creates audit outputs and `output/question_1/result1.xlsx`. Keep the template export and read-back verification active before final submission.

Template export rules:

1. Use Plan A as the submitted schedule.
2. Preserve the original template structure unless the team deliberately creates a clearly named corrected-copy template.
3. Explicitly fill 0:00 SOC as 6000 kWh and 24:00 SOC as 6000 kWh.
4. Do not use the first schedule-row SOC of 6750 kWh as the 0:00 SOC.
5. Handle the template time-label offset deliberately. The code uses physical intervals `00:00-00:10` through `23:50-24:00`; the original template labels may start at `0:10-0:20`. The export must document the chosen mapping and apply it consistently to purchase, charge/discharge, and SOC.
6. After writing the workbook, read it back and verify that template values match the selected Plan A schedule and four-hour totals.

## 5. Verification Policy

The current checks are useful but not sufficient for final submission. Strengthen verification before final delivery.

Required independent checks:

- input arrays contain 144 finite numeric values;
- prices are finite and nonnegative;
- load and PV are finite and nonnegative;
- solver reports success;
- all decision variables are finite;
- grid purchase is nonnegative;
- charge and discharge are nonnegative;
- no same-interval simultaneous charge/discharge beyond tolerance;
- SOC recurrence holds independently from exported charge/discharge values;
- SOC lower/upper bounds hold;
- initial and terminal SOC hold;
- charge/discharge power limits hold;
- PV curtailment is nonnegative and does not exceed available PV;
- original LP inequalities and equalities hold on the returned solution;
- reported cost equals recomputed cost from grid purchase and price;
- CSV and XLSX outputs can be read back and match in-memory results;
- `result1.xlsx` can be read back and matches the submitted Plan A schedule.

Do not treat `curtail_kwh` computed from the balance equation as an independent proof of balance. Balance checks must recompute from independent schedule columns or original LP constraints.

Do not treat Plan A and Plan B equal floating-point costs as an optimality certificate. They demonstrate non-uniqueness only after the primary LP optimum has already been accepted numerically.

## 6. Paper-Writing Policy

The PDF currently uses the right core numbers and the right high-level Python/HiGHS story, but paper claims must stay within what the program actually proves.

Allowed wording:

- The model is a linear program solved numerically with SciPy/HiGHS.
- The returned solution passed feasibility and consistency checks within stated tolerances.
- Plan A and Plan B show that interval-level schedules need not be unique under the same optimal cost, within numerical tolerance.
- Tables are computed from unrounded data and displayed rounded to two decimals.

Forbidden unless new code is added:

- claiming rational exact verification;
- claiming a strict primal-dual zero-gap certificate;
- claiming the program exports and validates the official template if it only exports `q1_results.xlsx`;
- claiming independent workbook verification unless the workbook is read back and checked;
- claiming `q1_plot.py` is an independent plotting entry unless such an entry is added.

Paper table policy:

- Use Plan A for the reported schedule.
- Display tiny negative zeros and tiny curtailment residuals as 0.00, but state they are floating-point residuals, not exact symbolic zeros.
- Keep the no-storage baseline definition precise: it is direct grid purchase of `max(load energy - PV energy, 0)`, not a no-PV baseline.

## 7. Visualization Policy

Keep visualizations generated from code, not manually edited.

Before final paper insertion, ensure figures match the paper narrative. The review notes that the current four-subplot dispatch figure differs from an earlier requested two-subplot style.

Minimum figure set for Question 1:

1. Plan A purchase and SOC over time, with SOC bounds at 1200 and 10800 kWh and explicit initial/terminal 6000 kWh points where visually useful.
2. Charge/discharge over time, with charge positive and discharge negative or clearly separated.
3. Cost comparison between no-storage and optimized schedule.
4. Optional Plan B minus Plan A figure only for non-uniqueness explanation, not as the main operational result.

If the paper references a figure, the code must generate that exact figure or a documented equivalent.

## 8. Code-Change Order

Execute future work in this order:

1. Fix dependencies in a target clean Python environment and update `requirements.txt` plus `env/` records.
2. Improve verification as listed in Section 5.
3. Maintain official `result1.xlsx` template export and read-back checks.
4. Maintain plotting outputs that match the paper figure requirements.
5. Re-run `scripts/q1_main.py` and compare core values with the known baseline after every material code change.
6. Update paper text so claims match implemented evidence.
7. Commit code, environment records, outputs, and paper-related docs in focused commits.

Do not start Questions 2-4 implementation until Question 1's submission package is internally consistent.

## 9. AI Collaboration Rule

For future AI work, start by reading this file. Do not re-litigate the MWorks-to-Python decision, the Plan A submission choice, or the need for template export/read-back verification unless the team explicitly changes the strategy.
