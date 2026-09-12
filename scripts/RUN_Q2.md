# Question 2 Run Guide

## What The Model Does

Statistics supplies plausible versions of tomorrow. For each day, the program
uses only completed earlier days to form a seven-day same-time forecast, then
samples complete historical forecast-error days to preserve persistent cloudy or
high-load periods.

Operations research chooses the frozen day-ahead purchase and battery response.
The LP relaxation is a fast continuous approximation and a mathematical lower
bound. If it proposes charging while buying emergency energy in the same
scenario and interval, the program adds binary mode switches for that entire
scenario and resolves a smaller MILP. A result is accepted only after every such
conflict is gone.

Three numerical quantities have different meanings:

- Forecast residual: actual minus forecast. It measures uncertainty and builds
  scenarios.
- Constraint residual: the difference between the two sides of supply balance or
  SOC recurrence after solving. Values near `1e-9 kWh` are floating-point noise.
- MILP relative gap: the remaining cost difference between the best feasible
  solution and the solver's lower bound. `1e-3` means at most about `0.1%` for the
  stated surrogate objective; it is not an energy-balance error.

## Formal Run

Start Windows PowerShell with `-NoProfile`, then run from the repository root:

```powershell
.\.venv\Scripts\python.exe scripts\q2_main.py
```

The first complete run normally takes about 35 minutes on the recorded LRX
machine. It is CPU-intensive and does not use CUDA. Progress is committed daily
under `output\question_2\checkpoints\`; rerunning the same command resumes.

To discard Question 2 checkpoints after deliberately changing model parameters:

```powershell
.\.venv\Scripts\python.exe scripts\q2_main.py --fresh
```

`--fresh` deletes only the known Question 2 checkpoint files. Use it only when a
clean rerun is intended.

Optional settings:

```powershell
.\.venv\Scripts\python.exe scripts\q2_main.py --scenario-count 20 --mip-relative-gap 0.001 --time-limit 30
```

To create a metric-by-metric comparison with the supplied teammate run:

```powershell
.\.venv\Scripts\python.exe scripts\q2_main.py --team-output "F:\wechatmp\xwechat_files\wxid_djpj9c7yru0w22_f447\msg\file\2026-09\Q2\Q2"
```

The external path is optional and never becomes an optimization input.

## Outputs

All formal outputs are under `output\question_2\`:

- `result2.xlsx`: official three-sheet format only.
- `q2_detail.csv`: 48096 ten-minute execution rows for February-December.
- `q2_daily.csv`: 334 daily stochastic-scheme rows with solver evidence.
- `q2_point_daily.csv`: point-forecast baseline.
- `q2_audit.csv`: independent physical and numerical checks.
- `q2_comparison.csv`: main scheme versus point forecast.
- `q2_solver_benchmark.csv`: four specified dates, incremental versus full MILP.
- `q2_team_comparison.csv`: generated only when `--team-output` is supplied.
- `result2_mapping_note.md`: official-header offset and output meanings.

The result workbook is read back after export. It must retain the official three
worksheets and columns; diagnostic fields remain in CSV files.

## Current Verified Baseline

With 20 scenarios, `mip_relative_gap=1e-3`, and a 30-second daily limit:

- stochastic actual cost: 24,240,218.72 yuan;
- point-forecast actual cost: 25,452,348.79 yuan;
- saving: 1,212,130.07 yuan, or 4.762%;
- all 334 output days reached the requested gap;
- no output day required all 2880 possible binaries;
- median active binaries: 576; maximum: 1008;
- median daily model solve time: 4.58 seconds;
- maximum physical balance residual: approximately `3.1e-13 kWh`.

These are floating-point optimization results. Paper wording should say
"globally optimal within the reported MILP gap", not exact symbolic optimality.
