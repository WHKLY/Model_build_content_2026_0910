# Agent Workflow Guide

This file is written for teammates and their local AI assistants after pulling this repository.

The project is a group mathematical-modeling repository. Treat every change as part of a shared modeling workflow, not as an isolated local experiment.

## 1. First Things To Read

Before editing anything, read these files in order:

1. `AGENT.md` - collaboration and AI-agent workflow rules.
2. `PROJECT.md` - project-level constraints, source-data policy, and modeling assumptions.
3. `RUN.md` - user-facing run guide.
4. `scripts/README.md` - script layout and build discipline.
5. The relevant note under `note/` for the question being modified.
6. The relevant received materials under `recieve/`.

If this file conflicts with a more specific problem note in `note/`, do not guess. State the conflict clearly and ask the teammate which rule should win.

## 2. Repository Purpose

This repository is for the 2026 mathematical modeling C problem on microgrid external power purchase strategy.

The repository currently uses MWorks/Syslab script files with `.jl` suffixes. Do not assume these files are Julia programs in the usual Julia ecosystem, and do not assume MATLAB compatibility.

Primary goals:

- keep the modeling assumptions explicit;
- keep raw competition data immutable;
- make every script explainable by a human teammate;
- make generated results reproducible across different local environments;
- avoid hidden data leakage, especially in forecasting questions;
- keep commits focused enough for teammates to review.

## 3. Environment Rules

Every teammate may have a different local environment. Before running or changing executable scripts, check and record the local environment.

Important environment differences may include:

- MWorks/Syslab version;
- available optimization functions and solver behavior;
- plotting backend and figure export behavior;
- Excel-reading support;
- Windows path handling;
- active Python or Conda environment if helper scripts are used;
- locale and encoding behavior for Chinese filenames;
- whether Microsoft Excel/COM is installed and accessible.

Do not create a new Conda environment unless the teammate explicitly asks for it. This project is primarily MWorks/Syslab-based, so a Python virtual environment is not automatically required.

If Python is used only for one-time data inspection or conversion, document that fact and avoid turning Python into a hidden runtime dependency for the final model unless the group agrees.

## 4. Language And Runtime Constraints

The implementation language is MWorks/Syslab `.jl` script style.

Critical rule: MWorks/Syslab is not MATLAB.

Do not write MATLAB-style code from habit. Before using syntax or APIs involving the following, verify against local MWorks/Syslab behavior or existing project code:

- Excel import/export;
- table or dataframe operations;
- linear programming and integer programming APIs;
- plotting APIs;
- figure sizing and export;
- path joining;
- dictionary/map syntax;
- anonymous functions;
- broadcasting/vectorization;
- exception handling;
- string encoding and Chinese paths.

Keep code simple and explicit. Prefer readable loops, named intermediate variables, and small helper functions over clever compact expressions that may not be portable across teammate environments.

## 5. Directory Layout

Use the existing layout consistently:

- `original_source/`
  - Canonical copy of competition source files.
  - Treat as immutable.
  - Do not edit, rename, reformat, or overwrite files here.

- `raw/`
  - Local raw-material holding area from early setup.
  - Do not depend on this directory for final scripts unless the group explicitly changes the data policy.

- `recieve/`
  - Received problem statements, teammate notes, and intermediate documents.
  - Preserve original wording where possible.
  - New analysis documents can be added here if they are source materials rather than generated outputs.

- `note/`
  - Required modeling and implementation notes.
  - Before every meaningful script build or rewrite, create a Markdown note here.

- `scripts/`
  - MWorks/Syslab scripts.
  - Keep scripts modular and explainable.

- `env/`
  - Local environment records.
  - Each teammate should write their own environment note instead of overwriting another person's note.

- `output/`
  - Generated outputs.
  - Normally ignored by `.gitignore`.
  - Commit only selected final outputs when the group explicitly wants generated artifacts in Git.

## 6. Source Data Policy

The canonical source-data location is `original_source/`.

Current expected source files:

- `original_source/C题.pdf`
- `original_source/附件/附件1.xlsx`
- `original_source/附件/附件2.xlsx`
- `original_source/附件/附件3.xlsx`
- `original_source/附件/附件4.xlsx`
- `original_source/附件/附件5/result1.xlsx`
- `original_source/附件/附件5/result2.xlsx`
- `original_source/附件/附件5/result3.xlsx`
- `original_source/附件/附件5/result4-2.xlsx`
- `original_source/附件/附件5/result4-3.xlsx`

Do not edit source Excel files in place. If an exported workbook is needed, write it under `output/`.

If a script needs fixed source data, centralize paths and constants in a dedicated script such as `scripts/project_paths.jl` or a question-specific data script. Do not scatter hard-coded filenames across model, plotting, and export files.

## 7. Required Note Before Coding

Before building or substantially changing a script, write a note under `note/`.

The note should include:

- question number;
- date and author or local AI identity if relevant;
- source files used;
- model assumptions;
- variables and units;
- objective function;
- constraints;
- implementation plan;
- expected outputs;
- verification checks;
- known risks or unresolved questions.

Do not treat the note as a formality. The note is the bridge between theory and code. If the note is unclear, the code will likely be hard to defend in the final paper.

Suggested filename pattern:

`note/YYYY-MM-DD-qN-short-topic.md`

Example:

`note/2026-09-11-q2-stochastic-dispatch-plan.md`

## 8. Script Organization Rules

Keep each script focused.

Preferred pattern for each question:

- `scripts/qN_data.jl`
  - hard-coded or generated data constants;
  - data validation helpers if needed.

- `scripts/qN_model.jl`
  - mathematical model construction;
  - parameter conversion;
  - solver call wrapper.

- `scripts/qN_verify.jl`
  - numerical checks;
  - physical feasibility checks;
  - result consistency checks.

- `scripts/qN_export.jl`
  - CSV/XLSX/table output.

- `scripts/qN_plot.jl`
  - unified figure style;
  - plot functions only.

- `scripts/qN_main.jl`
  - orchestration entry point.

Avoid putting all logic into one large main script. Also avoid splitting code so finely that a teammate cannot trace the flow.

## 9. Modeling Discipline

Always state the physical meaning of variables and units.

For this microgrid problem, be especially careful with:

- kW vs kWh;
- ten-minute interval conversion, usually `dt = 1/6` hour;
- endpoint time labels versus interval labels;
- charge power versus charge energy;
- discharge power versus delivered energy;
- battery-internal energy versus AC-side energy;
- charge efficiency and discharge efficiency;
- state-of-charge bounds;
- terminal state-of-charge assumptions;
- whether surplus photovoltaic power is curtailed;
- whether planned grid purchase can be unused;
- whether sale to grid is allowed;
- whether emergency purchase can charge the battery;
- whether a forecast or optimization uses future actual data.

If two mathematically equivalent formulations exist, prefer the one that is easier to audit and less likely to create unit mistakes.

## 10. Question 1 Baseline

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

Before changing Question 1 code, read:

- `recieve/problem_1/第一问方案与核验说明.md`
- `recieve/problem_1/建模方案.docx`
- `note/2026-09-11-q1-script-build-plan.md`
- `scripts/RUN_Q1.md`

Question 1 generated outputs are under `output/question_1/` when produced locally.

## 11. Question 2 Theory Requirements

Question 2 is not just Question 1 repeated over many days.

The key difference is uncertainty. Day-ahead purchase decisions must be made before the true load and photovoltaic generation are known.

Recommended theoretical framing:

- use causal forecasting;
- use only information available before the planned day;
- build a fixed day-ahead purchase plan;
- simulate real operation with actual load and photovoltaic data;
- use storage for real-time correction;
- use emergency purchase only when planned purchase, photovoltaic generation, and storage cannot cover demand;
- calculate final cost from planned purchase cost plus actual emergency purchase cost.

Avoid data leakage:

- do not use same-day actual values to construct same-day purchase plans;
- do not sample forecast errors from future dates;
- do not tune parameters on the final evaluation days without reporting that choice;
- do not use result templates as data sources.

Useful baselines:

- point-forecast plan with the same real-time controller;
- stochastic scenario plan with the same real-time controller;
- perfect-information hindsight lower bound for comparison only.

For stochastic optimization, keep non-anticipativity clear: the day-ahead purchase amount must be shared across scenarios. Scenario-specific recourse variables are allowed only after uncertainty is realized inside the model.

For real-time replay, keep cross-day SOC continuity unless the problem statement explicitly requires daily reset.

## 12. Forecasting Rules

Forecasting should be simple enough to defend unless the group deliberately chooses a more complex model.

Acceptable simple methods include:

- previous-day profile;
- rolling 7-day average;
- rolling 14-day average;
- weekday/weekend grouped average if justified;
- weighted average of recent days.

Evaluation should use rolling-origin validation, not random train/test splitting.

When comparing forecasts, report both:

- forecast error metrics, such as MAE or RMSE;
- downstream cost impact, because the cheapest dispatch is not always produced by the lowest RMSE forecast.

## 13. Optimization And Solver Rules

Before adding a model, estimate scale:

- number of days;
- number of intervals per day;
- number of scenarios;
- number of continuous variables;
- number of binary variables;
- expected solve time.

If a mixed-integer formulation is used, document why binary variables are necessary. If the same physical behavior can be enforced with a linear formulation or by a post-processing rule, prefer the simpler approach.

Do not silently accept infeasible solver results. Every solver call should be followed by checks such as:

- solver status;
- maximum balance residual;
- SOC lower and upper bound violations;
- charge/discharge power limit violations;
- terminal SOC condition if applicable;
- negative purchase, charge, discharge, or emergency energy;
- total cost recomputation from exported schedules.

## 14. Plot And Output Style

Keep visualization style consistent across questions.

Recommended style:

- clear titles with question number;
- readable axis labels with units;
- consistent colors for grid purchase, photovoltaic usage, battery charge/discharge, SOC, and emergency purchase;
- avoid overcrowded legends;
- use larger figure size when plotting multiple subplots;
- export both image files and editable figure files if supported by MWorks/Syslab.

Generated outputs should go under:

`output/question_N/`

Recommended subdirectories:

- `output/question_N/figures/`
- `output/question_N/tables/`
- `output/question_N/logs/`

If an Excel template must be filled, preserve the template structure unless the group agrees to change it.

## 15. Git Workflow

Before changing files, check:

`git status --short --branch`

General rules:

- keep commits focused;
- do not mix unrelated problem analysis, code changes, and generated outputs in one commit unless requested;
- do not commit personal temporary files;
- do not commit Office lock files such as `~$*.docx`;
- do not commit large generated outputs unless the group explicitly wants them;
- do not rewrite history, reset, or force-push without explicit group approval.

Recommended commit categories:

- documentation and workflow;
- question note;
- model implementation;
- output/export update;
- plotting update;
- verification fix.

Before committing, review:

`git diff --stat`

and, when practical:

`git diff`

If there are untracked files from another teammate or another task, do not add them unless the current request explicitly includes them.

## 16. Pulling And Merging

Before starting work:

1. save local changes if any;
2. inspect `git status`;
3. pull the latest remote state;
4. resolve conflicts manually and carefully;
5. rerun the smallest relevant check.

If there is a merge conflict in a model script, do not blindly choose one side. Compare the modeling assumptions behind both sides.

If there is a conflict in an output file, prefer regenerating the output from scripts after resolving code and data assumptions.

## 17. Commands For Teammates

PowerShell examples:

```powershell
git status --short --branch
git pull
git diff --stat
```

Run Question 1 in MWorks/Syslab after setting the working directory to the repository root:

```julia
include("scripts/q1_main.jl")
```

Do not assume `&&`, Unix path syntax, or Bash environment-variable syntax works in every teammate terminal.

## 18. AI Assistant Behavior Rules

If you are a local AI assistant reading this file:

- inspect the repository before changing files;
- prefer `rg` for search if available;
- keep edits small and directly related to the user's request;
- do not overwrite user changes;
- do not delete, move, or rename source files without explicit approval;
- do not introduce new dependencies without explaining the benefit and risk;
- do not claim that code was tested unless you actually ran the test;
- mention any check that could not be run;
- preserve Chinese filenames and paths carefully;
- use full paths when reporting important local files;
- explain modeling assumptions, not just code changes.

When asked to review theory, do not build code unless explicitly asked. Evaluate assumptions, equations, units, boundary conditions, data leakage risk, and output requirements first.

When asked to build code, first confirm that the corresponding `note/` document exists or create it as part of the change.

## 19. Safety Boundaries

High-risk actions require explicit human confirmation:

- deleting files or directories;
- moving or renaming many files;
- overwriting source Excel files;
- resetting Git state;
- cleaning untracked files;
- force-pushing;
- installing new global packages;
- changing system environment variables;
- running long or resource-heavy computations.

Prefer dry-run or read-only inspection commands before destructive operations.

## 20. Final Response Checklist

After completing a task, report:

- what changed;
- which files were modified;
- which checks were run;
- whether anything was intentionally left untracked or uncommitted;
- any remaining modeling or environment risk.

Keep the report concise, but do not hide uncertainty.
