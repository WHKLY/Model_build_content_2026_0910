# Agent Workflow Guide

Before changing code, outputs, or paper text, read `UNIFIED_PLAN.md` first. It is the current source of truth for the Python workflow, Question 1 submission package, verification scope, and paper claims.
This file is written for teammates and local AI assistants after pulling this repository. Treat every change as part of a shared mathematical-modeling workflow.

## First Things To Read

Before editing anything, read these files in order:

1. `AGENT.md`
2. `PROJECT.md`
3. `RUN.md`
4. `scripts/README.md`
5. The relevant note under `note/`
6. The relevant received materials under `recieve/`

If this file conflicts with a more specific problem note, state the conflict clearly and ask which rule should win.

## Repository Purpose

This repository is for the 2026 mathematical modeling C problem on microgrid external power purchase strategy. The formal reproducibility target is Windows x64 with PowerShell.

The formal implementation now uses Python inside a recorded virtual environment. Earlier MWorks/Syslab scripts were removed because that environment was too restrictive for contest verification.

Primary goals:

- keep modeling assumptions explicit;
- keep original competition data immutable;
- make every script explainable by a human teammate;
- make generated results reproducible across local environments;
- avoid hidden data leakage, especially in forecasting questions;
- keep commits focused enough for teammates to review.

## Environment Rules

Every teammate may have a different local environment. Before running or changing executable scripts, record the Windows environment under `env/`.

Important environment details include:

- Windows version and PowerShell version;
- Python version and virtual-environment path;
- pip version;
- installed package versions from `python -m pip freeze`;
- whether Excel files can be read through `openpyxl`;
- plotting backend and font behavior;
- locale and encoding behavior for Chinese filenames.

Use a repository-local `.venv` for formal runs. Invoke `.venv\Scripts\python.exe` explicitly so an active Conda environment or another global Python cannot silently change the run. Linux and Termux environments are outside the formal submission workflow.

## Runtime Rules

The implementation language is Python. Do not depend on MWorks/Syslab for formal runs.

Keep code simple and explicit. Prefer readable arrays, named intermediate values, and small helper functions over compact expressions that make unit checks harder.

Before adding or changing dependencies, update `requirements.txt` and the relevant environment note.

## Directory Layout

Use the existing layout consistently:

- `original_source/`: canonical immutable competition source files.
- `raw/`: early setup copy of raw materials.
- `recieve/`: received problem statements, teammate notes, and intermediate documents.
- `note/`: required modeling and implementation notes.
- `scripts/`: Python implementation scripts.
- `env/`: Windows environment records used for formal verification.
- `output/`: generated outputs, normally ignored by Git.

Do not edit source Excel files in place. If an exported workbook is needed, write it under `output/`.

## Required Note Before Coding

Before building or substantially changing a script, write a note under `note/`.

The note should include source files, model assumptions, variables and units, objective function, constraints, implementation plan, expected outputs, verification checks, and known risks.

## Script Organization

Preferred pattern for each question:

- `scripts/qN_data.py` for source data loading or generated constants.
- `scripts/qN_model.py` for mathematical model construction and solver calls.
- `scripts/qN_verify.py` for numerical and physical checks.
- `scripts/qN_certificate.py` for certificate generation when an exact proof is claimed.
- `scripts/qN_certificate_verify.py` for independent certificate verification without an optimizer.
- `scripts/qN_export.py` for CSV/XLSX/table output.
- `scripts/qN_plot.py` for visualizations.
- `scripts/qN_main.py` for orchestration.

Avoid putting all logic into one large main script.

## Modeling Discipline

Always state the physical meaning of variables and units.

For this microgrid problem, be especially careful with kW vs kWh, ten-minute interval conversion, endpoint time labels, battery-internal energy versus AC-side energy, charge and discharge efficiencies, SOC bounds, terminal SOC, curtailment, sale-to-grid assumptions, emergency purchase behavior, and data leakage.

If two mathematically equivalent formulations exist, prefer the one that is easier to audit and less likely to create unit mistakes.

## Question 1 Baseline

Question 1 uses deterministic scheduling with known load and photovoltaic generation.

Current important assumptions:

- ten-minute time step;
- 144 intervals per day;
- battery capacity: 12000 kWh;
- allowed SOC range: 1200 kWh to 10800 kWh;
- initial SOC: 6000 kWh;
- terminal SOC: 6000 kWh;
- charge efficiency: 0.9;
- discharge efficiency: 0.9;
- charge/discharge power limit: 5000 kW on the AC connection side;
- no sale-to-grid revenue unless explicitly modeled later;
- surplus photovoltaic energy may be curtailed;
- the 5000 kW limit is not a grid-purchase power limit.
- unused supply may be discarded without revenue, matching the inequality model in the paper.

Before changing Question 1 code, read:

- `recieve/problem_1/第一问方案与核验说明.md`
- `recieve/problem_1/建模方案.docx`
- `note/2026-09-11-python-q1-refactor-plan.md`
- `scripts/RUN_Q1.md`

## Future Questions

Question 2 and later questions must avoid data leakage. Day-ahead purchase decisions must use only information available before the planned day. Scenario-specific recourse variables are allowed only after uncertainty is realized inside the model.

Forecasting should be simple enough to defend unless the group deliberately chooses a more complex model. Use rolling-origin validation rather than random train/test splitting.

Every solver call should be followed by checks for solver status, balance residuals, SOC bounds, power limits, nonnegative purchases, and cost recomputation from exported schedules.

## Commands For Teammates

Create the virtual environment and install dependencies from Windows PowerShell started with `-NoProfile`:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Run Question 1 from the repository root:

```powershell
.\.venv\Scripts\python.exe scripts\q1_main.py
.\.venv\Scripts\python.exe scripts\q1_certificate_verify.py --certificate output\question_1\certificate_q1.json --input original_source\附件\附件1.xlsx
```

Run Question 2 from the repository root:

```powershell
.\.venv\Scripts\python.exe scripts\q2_main.py
```

Question 2 is CPU-intensive, uses daily checkpoints, and normally takes about
35 minutes on the recorded Windows machine. Read `scripts/RUN_Q2.md` before
changing its forecast, scenario, MILP, replay, or template-export behavior.

## Git Workflow

Before changing files, check:

```bash
git status --short --branch
```

Keep commits focused. Do not commit generated outputs unless the group explicitly wants them. Do not rewrite history, reset, or force-push without explicit group approval.

## AI Assistant Rules

If you are a local AI assistant reading this file:

- inspect the repository before changing files;
- keep edits small and directly related to the user request;
- do not overwrite user changes;
- do not delete, move, or rename source files without explicit approval;
- do not introduce new dependencies without explaining the benefit and risk;
- do not claim that code was tested unless you actually ran the test;
- mention any check that could not be run;
- preserve Chinese filenames and paths carefully;
- explain modeling assumptions, not just code changes.
