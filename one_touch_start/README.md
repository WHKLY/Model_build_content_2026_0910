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

At present, only Question 1 has a reviewed executable implementation. Questions 2-4 must not be registered until their model, output, and verification modules are complete.

Expected output files:

- `certificate_q1.json`
- `q1_schedule.csv`
- `q1_summary.csv`
- `q1_four_hour_summary.csv`
- `q1_target_purchase.csv`
- `q1_results.xlsx`
- `result1.xlsx`
- `result1_mapping_note.md`

To add a later question, place its self-contained modules under `scripts/` and register its runner in `scripts/question_registry.py`.
