# Project Constraints

This repository is for the 2026 mathematical modeling C problem on microgrid external power purchase strategy.

## Collaboration Rules

- Treat this as a group project. Every teammate may have a different local MWorks/Syslab environment.
- Record local environment details under `env/` before running or modifying executable code.
- Do not assume another teammate has the same MWorks version, `PATH`, Excel/COM availability, Python environment, or shell behavior.
- Do not push to any remote repository unless the group explicitly agrees.

## Language and Runtime

- Primary implementation language: MWorks/Syslab script files.
- Use `.jl` files for now because the local Syslab examples use `.jl`.
- Do not write MATLAB-style code by habit. MWorks/Syslab syntax and APIs must be checked against local examples or documentation before relying on them.
- Keep MATLAB-specific assumptions out of the model implementation unless they have been verified in MWorks.

## Source Data Policy

- Original competition files should be treated as immutable.
- Store the canonical source data under `original_source/`.
- Keep data-file paths in one dedicated MWorks script, not scattered through model code.
- Prefer explicit hard-coded source filenames in that path script. This makes the data dependency easy to inspect and easy for teammates to adjust.
- Generated outputs should be written outside `original_source/`.

Current source-data plan:

| Logical data | Expected canonical path |
|---|---|
| Problem statement | `original_source/C题.pdf` |
| Attachment 1 | `original_source/附件/附件1.xlsx` |
| Attachment 2 | `original_source/附件/附件2.xlsx` |
| Attachment 3 | `original_source/附件/附件3.xlsx` |
| Attachment 4 | `original_source/附件/附件4.xlsx` |
| Result templates | `original_source/附件/附件5/` |

The existing `raw/` directory has not been moved automatically. Move or copy source files only after the group confirms the canonical layout.

## Build Notes Requirement

Before each meaningful code build or rewrite, write a Markdown note under `note/`.

Each note should include:

- the question being solved;
- model assumptions and data口径;
- planned script changes;
- expected outputs;
- checks that must pass.

This prevents implementation drift and makes it clear why a script was written in a particular way.

## Question 1 Modeling Constraints

Use the existing received materials as the starting point:

- `recieve/problem_1/第一问方案与核验说明.md`
- `recieve/problem_1/建模方案.docx`
- `recieve/前置.docx`

The current first-question implementation target is:

- deterministic daily scheduling;
- no sale-to-grid revenue unless later explicitly modeled;
- surplus PV may be curtailed;
- ten-minute time step, 144 intervals;
- attachment time labels interpreted as interval endpoints unless later corrected;
- battery capacity: 12000 kWh;
- allowed state of charge: 1200 kWh to 10800 kWh;
- initial state of charge: 6000 kWh;
- terminal state of charge: 6000 kWh;
- charge efficiency: 0.9;
- discharge efficiency: 0.9;
- charge/discharge power limit: 5000 kW on the AC connection side;
- the 5000 kW limit is not a grid-purchase power limit.

The preferred first-question model is the battery-internal energy-increment LP described in the received implementation document.

Important result interpretation:

- The minimum total purchase cost may be unique even when interval-level purchase schedules are not.
- If demonstrating non-uniqueness, generate two schedules with the same optimal purchase cost but at least one different interval purchase amount.
- Do not claim two plans are equally optimal only because rounded costs match.

## Script Organization

Keep scripts small and explainable:

- `scripts/project_paths.jl`: hard-coded project and source-data paths.
- `scripts/q1_main.jl`: question 1 orchestration entry point.
- `scripts/q1_model.jl`: model parameter conversion and LP construction.
- `scripts/q1_verify.jl`: physical and numerical checks.

Future scripts should follow the same pattern: path/config, model, run, verify, output.

## Git Policy

- A local Git repository may be used for versioning.
- Keep commits focused when commits are eventually requested.
- Do not push unless explicitly requested.
- Do not move or delete original source files without explicit confirmation.
