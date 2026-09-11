# Run Question 1

## Environment

Create and activate the project virtual environment, then install the pinned requirements.

Linux / Termux / Git Bash:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

For contest verification, record the actual environment after installing dependencies:

```bash
python --version
python -m pip --version
python -m pip freeze
```

## Run

From the project root:

```bash
python scripts/q1_main.py
```

Expected outputs are written under `output/question_1/`.

Audit table outputs:

- `q1_schedule.csv`
- `q1_summary.csv`
- `q1_four_hour_summary.csv`
- `q1_target_purchase.csv`
- `q1_results.xlsx`

Official template-style output:

- `result1.xlsx`
- `result1_mapping_note.md`

Expected figures:

- `figures/q1_purchase_soc.png`
- `figures/q1_purchase_soc.svg`
- `figures/q1_charge_discharge.png`
- `figures/q1_charge_discharge.svg`
- `figures/q1_dispatch_overview.png`
- `figures/q1_dispatch_overview.svg`
- `figures/q1_plan_difference.png`
- `figures/q1_plan_difference.svg`
- `figures/q1_cost_comparison.png`
- `figures/q1_cost_comparison.svg`
