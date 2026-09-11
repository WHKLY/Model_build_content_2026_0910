# Scripts

Primary implementation language: Python running inside the repository virtual environment.

## Files

- `project_paths.py`: fixed project paths and source-data filenames.
- `q1_data.py`: Attachment 1 loading and interval-label construction.
- `q1_model.py`: deterministic LP construction, solve wrappers, and schedule recovery.
- `q1_verify.py`: numerical and physical checks.
- `q1_export.py`: CSV and XLSX output.
- `q1_plot.py`: PNG and SVG visualizations.
- `q1_main.py`: question 1 orchestration entry point.

## Build Discipline

Before changing executable scripts for a modeling step, add or update a note under `../note/` describing the intended implementation and checks.
