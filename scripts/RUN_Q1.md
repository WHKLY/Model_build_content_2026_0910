# Run Question 1

## Environment

Create and activate the project virtual environment, then install the pinned requirements:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

The Termux environment used for this refactor is recorded in `env/LRX_Termux_python_venv.md`. For contest verification, record the actual judge or teammate environment after installing dependencies with:

```bash
python --version
python -m pip --version
python -m pip freeze
```

## Run

From the project root:

```bash
. .venv/bin/activate
python scripts/q1_main.py
```

Expected outputs are written under `output/question_1/`.

Expected tables:

- `q1_schedule.csv`
- `q1_summary.csv`
- `q1_four_hour_summary.csv`
- `q1_target_purchase.csv`
- `q1_results.xlsx`

Expected figures:

- `figures/q1_dispatch_overview.png`
- `figures/q1_dispatch_overview.svg`
- `figures/q1_plan_difference.png`
- `figures/q1_plan_difference.svg`
- `figures/q1_cost_comparison.png`
- `figures/q1_cost_comparison.svg`
