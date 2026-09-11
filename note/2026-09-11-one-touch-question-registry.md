# One-Touch Multi-Question Entry Design

Date: 2026-09-11

## Current Boundary

The repository currently contains an executable implementation only for Question 1. Question 2 has an analysis document, while Questions 2-4 have no reviewed solver/export runners. The one-touch entry must therefore be extensible without claiming that missing questions have been solved.

## Entry Contract

- `python main.py`: run every question currently registered as implemented.
- `python main.py --question 1`: run one implemented question.
- `python main.py --list-questions`: list implemented question numbers without running models.
- An unregistered question number must fail clearly instead of generating placeholder output.

## Registry Design

Add `one_touch_start/scripts/question_registry.py` as the only place that binds question numbers to runner functions. Question 1 remains registered through `q1_runner.run_question_1`.

When a later question is implemented:

1. Add a self-contained `qN_runner.py` and its supporting modules under `one_touch_start/scripts/`.
2. Keep all source paths under `one_touch_start/assets/` and outputs under `one_touch_start/output/`.
3. Register `N: run_question_N` in `QUESTION_RUNNERS`.
4. Add expected-output and verification checks before describing the question as implemented.

## Safety And Output Policy

- Default execution never silently skips a registered question.
- Missing or failed runners propagate a nonzero process exit.
- No placeholder result files are generated for Questions 2-4.
- No plots, environment setup, downloads, or external repository paths are introduced.

## Verification

- List mode reports only Question 1.
- Default mode runs Question 1 successfully.
- Explicit `--question 1` mode runs successfully.
- Explicit `--question 2` is rejected with a clear message.
- Existing Question 1 outputs and exact certificate remain unchanged in meaning.
