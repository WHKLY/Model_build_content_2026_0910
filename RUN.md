# Run Guide

## Question 1

Primary entry point:

`scripts/q1_main.py`

### Linux / Termux / Git Bash

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python scripts/q1_main.py
```

### Windows PowerShell

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python scripts/q1_main.py
```

Detailed output notes are in:

`scripts/RUN_Q1.md`

## Important Notes

- The project uses Python instead of MWorks/Syslab.
- Keep virtual-environment details under `env/` because contest verification depends on reproducible package versions.
- The target clean-install dependency set is in `requirements.txt` and is based on the Windows CPython 3.12 review environment.
- Source data for question 1 is read from `original_source/附件/附件1.xlsx`.
- Results are written to `output/question_1/` when the entry script is run.
- The official template-style output is `output/question_1/result1.xlsx`; audit outputs remain in `q1_*.csv` and `q1_results.xlsx`.
