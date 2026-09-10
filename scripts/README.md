# Scripts

Primary implementation language: MWorks/Syslab `.jl`.

Do not assume MATLAB compatibility. Check MWorks/Syslab examples or documentation before using Excel import, table handling, optimization, plotting, or file-output APIs.

## Files

- `project_paths.jl`: fixed project paths and source-data filenames.
- `q1_main.jl`: entry point for question 1.
- `q1_model.jl`: data conversion and LP construction.
- `q1_verify.jl`: numerical and physical checks.

## Build Discipline

Before changing executable scripts for a modeling step, write a short note under `../note/` describing the intended implementation and checks.
