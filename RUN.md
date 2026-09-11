# Run Guide

## Question 1

Primary entry point:

`scripts/q1_main.py`

Recommended workflow from the project root:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python scripts/q1_main.py
```

Detailed output notes are in:

`scripts/RUN_Q1.md`

## Important Notes

- The project now uses Python instead of MWorks/Syslab.
- Keep the virtual-environment details under `env/` because contest verification depends on reproducible package versions.
- Source data for question 1 is read from `original_source/附件/附件1.xlsx`.
- Every substantial rebuild should first add a short Markdown note under `note/`.
- Results are written to `output/question_1/` when the entry script is run.
