# Run Guide

## Contest One-Touch Package

The self-contained Question 1 contest package is under `one_touch_start/`. In the contest environment, run:

```text
cd one_touch_start
python main.py
```

It reads only `one_touch_start/assets/`, writes non-image files to `one_touch_start/output/`, and performs no environment setup.

The entry runs all implemented questions by default. Use `python main.py --list-questions` to inspect the registry or `python main.py --question 1` to run one implemented question. Questions without reviewed executable runners are not registered and do not produce placeholder files.

## Question 1

Primary entry point:

`scripts/q1_main.py`

### Windows PowerShell

Start PowerShell with `-NoProfile`. The supported formal environment is Windows x64 with CPython 3.11.

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts\q1_main.py
.\.venv\Scripts\python.exe scripts\q1_certificate_verify.py --certificate output\question_1\certificate_q1.json --input original_source\附件\附件1.xlsx
```

Detailed output notes are in:

`scripts/RUN_Q1.md`

## Important Notes

- The project uses Python instead of MWorks/Syslab.
- Keep virtual-environment details under `env/` because contest verification depends on reproducible package versions.
- The target clean-install dependency set is in `requirements.txt` and is verified against the Windows CPython 3.11 project environment.
- Source data for question 1 is read from `original_source/附件/附件1.xlsx`.
- Results are written to `output/question_1/` when the entry script is run.
- The official output is `output/question_1/result1.xlsx`. It preserves the supplied template exactly except for designated numeric result cells; audit outputs remain in `q1_*.csv` and `q1_results.xlsx`.
- The exact optimality certificate is `output/question_1/certificate_q1.json` and must pass the independent verifier command above.
