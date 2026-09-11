# Run Question 1

## Environment

Use Windows PowerShell started with `-NoProfile`. Create the project virtual environment and install the pinned requirements:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

For contest verification, record the actual environment after installing dependencies:

```powershell
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -m pip --version
.\.venv\Scripts\python.exe -m pip freeze
```

## Run

From the project root:

```powershell
.\.venv\Scripts\python.exe scripts\q1_main.py
.\.venv\Scripts\python.exe scripts\q1_certificate_verify.py --certificate output\question_1\certificate_q1.json --input original_source\附件\附件1.xlsx
```

Expected outputs are written under `output/question_1/`.

Audit table outputs:

- `q1_schedule.csv`
- `q1_summary.csv`
- `q1_four_hour_summary.csv`
- `q1_target_purchase.csv`
- `q1_results.xlsx`
- `certificate_q1.json`

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
