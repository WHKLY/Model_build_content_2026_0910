# Question 1 One-Touch Submission Plan

Date: 2026-09-11

## Goal

Build a self-contained Question 1 submission under `one_touch_start/` that the contest environment can run with one command:

```text
python main.py
```

The contest environment is assumed to provide the required Python packages. The bundle must not create environments, install packages, inspect Conda, or depend on repository files outside `one_touch_start/`.

## Allowed Inputs

All input paths are resolved from the entry script location, not from the caller's current working directory. The only data sources are:

- `one_touch_start/assets/附件1.xlsx`
- `one_touch_start/assets/附件5/result1.xlsx`

Attachments 2-4 and the remaining result templates stay in `assets/` for future questions but are not read by the Question 1 entry point.

## Structure

- `one_touch_start/main.py`: argument-free one-touch entry point.
- `one_touch_start/scripts/project_paths.py`: bundle-relative asset and output paths.
- `one_touch_start/scripts/q1_data.py`: Attachment 1 loading and interval labels.
- `one_touch_start/scripts/q1_model.py`: LP construction and optimization.
- `one_touch_start/scripts/q1_verify.py`: numerical and physical checks.
- `one_touch_start/scripts/q1_certificate.py`: exact rational certificate generation.
- `one_touch_start/scripts/q1_certificate_verify.py`: optimizer-independent certificate verification.
- `one_touch_start/scripts/q1_export.py`: non-image output generation and strict template filling.
- `one_touch_start/scripts/q1_runner.py`: orchestration without plotting.

The submission copies the reviewed Question 1 implementation so it remains independent of the repository-level `scripts/` directory. Imports are forced to the bundle's own `scripts/` directory.

## Outputs

The command writes only non-image results under `one_touch_start/output/`:

- `q1_schedule.csv`
- `q1_summary.csv`
- `q1_four_hour_summary.csv`
- `q1_target_purchase.csv`
- `q1_results.xlsx`
- `result1.xlsx`
- `result1_mapping_note.md`
- `certificate_q1.json`

No PNG, SVG, figure directory, environment file, package installation, or external download is produced.

## Template Rule

`result1.xlsx` must preserve `assets/附件5/result1.xlsx` exactly except for the designated numeric result cells. The one-touch exporter must not read `raw/`, `original_source/`, `recieve/`, root `scripts/`, or root `output/`.

## Verification

1. Run from inside `one_touch_start/` with `python main.py` semantics.
2. Run from the repository root to prove current-working-directory independence.
3. Confirm all expected files exist and no image files are generated.
4. Confirm the exact certificate has zero primal-dual gap.
5. Confirm `result1.xlsx` retains all template package members and all non-worksheet parts byte-for-byte.
6. Search submission code for references to repository-level source/output directories or absolute project paths.

## Known Assumption

This bundle currently implements Question 1 only because Questions 2-4 do not yet have reviewed executable implementations in the repository. Their assets are retained but unused.
