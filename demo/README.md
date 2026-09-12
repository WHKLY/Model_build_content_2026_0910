# Question 2 Incremental-MILP Demo

This directory is an isolated solver experiment. It does not modify or import
the received preliminary Question 2 program, the formal scripts, or the
contest-facing one-touch package.

## Purpose

The strict model forbids battery charging and emergency purchasing in the same
scenario interval. The existing preliminary implementation solves an LP first,
but activates all scenario-interval binaries when any conflict appears.

This demo instead repeats the following steps:

1. solve the LP relaxation;
2. detect every interval with positive charge and emergency energy;
3. activate binaries using a conflict-driven scope;
4. solve the reduced MILP;
5. add any newly appearing conflicts and repeat;
6. compare the final solution against a full MILP containing every binary.

The incremental result is full-MILP feasible when no conflicts remain. If the
reduced MILP was solved to optimality, that result also attains the full-MILP
optimum because the reduced model is a relaxation of the full model. Numerical
claims remain limited by the configured solver gap.

## Data Boundary

The demo reads only:

- `raw/附件/附件1.xlsx`
- `raw/附件/附件2.xlsx`

Generated CSV files are restricted to `demo/output/` and ignored by Git.

## Commands

Run the fast synthetic regression tests from a PowerShell `-NoProfile` window:

```powershell
.\.venv\Scripts\python.exe -m unittest demo\test_q2_incremental_milp.py -v
```

Run one real date first:

```powershell
.\.venv\Scripts\python.exe demo\run_q2_incremental_comparison.py --dates 2025-03-20
```

Run all four dates requested by the problem statement:

```powershell
.\.venv\Scripts\python.exe demo\run_q2_incremental_comparison.py
```

The default comparison uses 20 scenarios, a 60-second limit per MILP solve,
and a relative gap target of `1e-4`. The default `scenario` scope activates all
144 intervals of a scenario once that scenario exhibits a conflict. This avoids
slow conflict migration within the same adverse scenario while still leaving
unaffected scenarios continuous. Use `--activation-scope pair` for the narrowest
strategy or `--activation-scope interval` to activate a conflicted time column
across all scenarios. These are demo settings and do not silently change the
received preliminary script.

## Interpretation

The key fields are:

- `lp_initial_conflicts`: binaries suggested by the first LP solution;
- `incremental_binary_history`: active binary count after each round;
- `incremental_active_binaries`: final reduced count;
- `total_possible_binaries`: binary count in the reference full MILP;
- `bound_intervals_overlap`: whether numerical objective-bound intervals agree;
- `objective_difference`: incremental objective minus full objective;
- plan-difference fields: reported because equal objectives do not imply a
  unique purchase schedule;
- remaining conflicts and maximum constraint violations: both must be within
  tolerance.

This demo does not perform January warm-up, actual-day rolling dispatch, Excel
template export, or contest result generation. Its only purpose is to test the
day-ahead solver formulation and its computational behavior.

## Local Results On 2026-09-11

Environment: repository `.venv`, CPython 3.11.9, NumPy 2.3.5, SciPy 1.16.3,
and openpyxl 3.1.5. The four-date comparison used 20 scenarios, a 30-second
per-solve limit, and a `1e-3` relative MILP gap target.

| Date | Initial LP conflicts | Incremental binaries | Full binaries | Incremental solve | Full solve | Speed ratio |
|---|---:|---:|---:|---:|---:|---:|
| 2025-03-20 | 39 | 720 | 2880 | 4.212 s | 6.177 s | 1.47x |
| 2025-06-21 | 66 | 576 | 2880 | 3.819 s | 6.492 s | 1.70x |
| 2025-09-23 | 34 | 576 | 2880 | 4.207 s | 5.964 s | 1.42x |
| 2025-12-21 | 69 | 576 | 2880 | 4.196 s | 7.485 s | 1.78x |

All scenario-scope runs converged in one reduced-MILP round, had no remaining
charge/emergency conflicts, and had maximum reported constraint violation below
`4.4e-9`. Incremental and full-MILP objective-bound intervals overlapped on all
four dates. Plan vectors were not identical, which is expected when both solves
stop at nonzero relative gaps and the model can have alternate near-optimal
plans.

The narrow scopes were not stable on the March 20 case:

- `pair` scope kept moving a few conflicts to new pairs and did not converge in
  the configured 20 rounds;
- `interval` scope grew from 340 to 900 active binaries and still had two new
  conflicts after 20 rounds;
- `scenario` scope activated five affected scenarios, or 720 binaries, and
  converged in one round.

At the stricter `1e-4` target on March 20, the scenario-scope incremental solve
finished in about 4.34 seconds with gap `8.12e-5`. The full 2880-binary model
reached the 60-second limit with gap about `1.36e-4`. This supports using the
incremental model as the certificate-producing solve and the full model as a
bounded cross-check rather than requiring the larger model to finish first.
