# Scripts

Primary implementation language: Python running inside the repository virtual environment.

## Files

- `project_paths.py`: fixed project paths and source-data filenames.
- `q1_data.py`: Attachment 1 loading and interval-label construction.
- `q1_model.py`: deterministic LP construction, solve wrappers, and schedule recovery.
- `q1_verify.py`: numerical and physical checks.
- `q1_certificate.py`: exact rational optimality certificate generation.
- `q1_certificate_verify.py`: independent certificate validation without calling an optimizer.
- `q1_export.py`: CSV and XLSX output.
- `q1_plot.py`: PNG and SVG visualizations.
- `q1_main.py`: question 1 orchestration entry point.
- `q2_data.py`: Question 2 source loading, causal forecasts, and residual scenarios.
- `q2_model.py`: conflict-driven incremental MILP and full-MILP benchmark.
- `q2_control.py`: frozen-plan causal real-time replay.
- `q2_verify.py`: physical, numerical, causal, and comparison checks.
- `q2_export.py`: audit CSVs and strict `result2.xlsx` template export.
- `q2_main.py`: complete 2025 Question 2 orchestration with checkpoints.

Question 2 run details and interpretation are in `RUN_Q2.md`.

## Build Discipline

Before changing executable scripts for a modeling step, add or update a note under `../note/` describing the intended implementation and checks.
