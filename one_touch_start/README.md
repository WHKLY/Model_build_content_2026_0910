# Contest One-Touch Submission

Run from this directory:

```text
python main.py
```

The script reads only from `assets/` and writes non-image results to `output/`.
No environment creation, dependency installation, network access, or plotting is performed.

By default, `main.py` runs every question registered as fully implemented. To inspect or select implementations:

```text
python main.py --list-questions
python main.py --question 1
```

Questions 1 and 2 have reviewed executable implementations. Questions 3-4 must not be registered until their model, output, and verification modules are complete.

Expected output files:

- `certificate_q1.json`
- `q1_schedule.csv`
- `q1_summary.csv`
- `q1_four_hour_summary.csv`
- `q1_target_purchase.csv`
- `q1_results.xlsx`
- `result1.xlsx`
- `result1_mapping_note.md`
- `q2_detail.csv`
- `q2_daily.csv`
- `q2_point_daily.csv`
- `q2_audit.csv`
- `q2_comparison.csv`
- `result2.xlsx`
- `result2_mapping_note.md`

Question 2 is CPU-intensive and may take about 35 minutes. It writes daily
checkpoints under `output/checkpoints/` and resumes them when the inputs and
configuration are unchanged. It creates no figures and uses only `assets/`.

To add a later question, place its self-contained modules under `scripts/` and register its runner in `scripts/question_registry.py`.
