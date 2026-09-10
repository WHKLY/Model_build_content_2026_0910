# Initial MWorks Project Structure

## Goal

Prepare the repository for MWorks/Syslab implementation of the microgrid scheduling model, without yet implementing or running the full solver.

## Context

The project already contains the original problem files under `raw/` and received first-question modeling materials under `recieve/`.

The current working decision is to use MWorks/Syslab `.jl` scripts, because the installed Syslab examples use `.jl` files. This should still be verified with a minimal run before any large implementation.

## Data Layout Decision

Use `original_source/` as the canonical immutable source-data directory.

For now, do not automatically move files from `raw/` into `original_source/`. Moving source files changes existing paths and may affect teammates. The planned canonical paths are documented in `PROJECT.md` and hard-coded in `scripts/project_paths.jl`.

## Script Design

The first set of scripts is intentionally split by responsibility:

- `project_paths.jl`: one place for project paths and fixed source-data filenames.
- `q1_main.jl`: entry point for question 1.
- `q1_model.jl`: model constants, input conversion, and LP matrix construction.
- `q1_verify.jl`: checks for SOC bounds, terminal SOC, power limits, purchase nonnegativity, and cost equality.

This structure is chosen so that MWorks-specific Excel import and LP solver APIs can be filled in after checking the local Syslab documentation/examples.

## Constraints to Preserve

- Do not silently switch from MWorks to MATLAB/Python as the primary implementation.
- Do not scatter source file paths across scripts.
- Do not modify original competition files.
- Before implementing a solver build, add another note describing the exact model equations and MWorks APIs to be used.

## Next Build Note Should Cover

- which MWorks/Syslab version will be used for the first executable run;
- the exact Excel import function or COM workflow;
- the exact LP solver function/API available in MWorks;
- output workbook sheet names and schema;
- numerical tolerances for validation.
