# Question 2 Conflict-Driven MILP Demo Plan

Date: 2026-09-11

## Scope

This build is an isolated local experiment for Question 2. It does not modify,
import, or replace the received preliminary solver under `recieve/problem_2/`,
the formal scripts under `scripts/`, or the contest package under
`one_touch_start/`.

The experiment answers one question: can the strict day-ahead model retain the
rule that emergency purchases and battery charging cannot occur in the same
scenario interval, while introducing binary variables only where the current
relaxation needs them?

## Data And Information Boundary

- Read-only data source: `raw/附件/附件1.xlsx` and
  `raw/附件/附件2.xlsx`.
- Attachment 1 supplies the repeated 144-interval price curve.
- Attachment 2 supplies 2025 actual load and photovoltaic power.
- Power in kW is converted to ten-minute energy in kWh with `dt = 1/6` hour.
- A target day's forecast uses only earlier days.
- Joint scenarios sample complete historical load/PV residual days, never the
  target day or a future day.

## Shared Model

All comparison methods use the same variables, objective, bounds, scenarios,
and terminal reserve term. The only difference is how many charge/emergency
mode binaries are present.

The physical assumptions are:

- planned purchases are nonnegative and paid in full;
- unused planned energy and unused photovoltaic energy may be discarded;
- emergency energy costs five times the interval price;
- charging and emergency purchasing are mutually exclusive in every scenario
  interval;
- charge and discharge efficiencies are each 0.9;
- AC-side charge and discharge limits are 5000 kW;
- SOC remains between 1200 and 10800 kWh;
- the initial comparison SOC is supplied explicitly;
- the terminal reserve penalty affects planning but is not reported as actual
  electricity cost.

## Compared Solvers

1. LP relaxation: no binary variables. This gives a lower bound and identifies
   intervals with simultaneous positive charging and emergency purchase.
2. Conflict-driven incremental MILP: add binaries only for currently violated
   scenario intervals, solve again, and repeat until no unrestricted conflict
   remains.
3. Full MILP: add one binary variable to every scenario interval. This is the
   reference implementation for numerical comparison.

If an incremental solve is optimal and its solution has no conflict in any
scenario interval, it is feasible for the full MILP. Because the incremental
model is a relaxation of the full MILP, the same solution is also globally
optimal for the full model, subject to the solver's reported numerical gap.

The implementation also tests conflict-driven closures. The narrow `pair`
scope adds only exact conflicts. The default `scenario` scope activates all 144
intervals of any scenario that exhibits a conflict, preventing a conflict from
migrating through that same adverse scenario one interval per iteration. The
`interval` scope activates a conflicted time column across every scenario. All
three scopes add constraints from the full MILP and therefore preserve the same
feasible set once the returned solution has no remaining conflict.

## Planned Files

- `demo/q2_incremental_milp.py`: data loading, forecast/scenario construction,
  common sparse model builder, LP relaxation, incremental MILP, full MILP, and
  independent result checks.
- `demo/run_q2_incremental_comparison.py`: command-line comparison on selected
  real dates; writes a CSV only under `demo/output/`.
- `demo/test_q2_incremental_milp.py`: synthetic no-conflict and conflict tests.
- `demo/README.md`: purpose, commands, interpretation, and limitations.
- `demo/output/.gitignore`: prevent generated benchmark data from entering the
  formal result set.

## Expected Comparison Fields

- target date and scenario count;
- LP lower bound and number of LP conflicts;
- incremental iterations and active binary count;
- incremental and full-MILP objective values;
- solver relative gaps and dual bounds;
- maximum and total absolute plan differences;
- solve and total wall-clock times;
- base-constraint residuals and remaining physical conflicts.

## Required Checks

- LP, incremental MILP, and full MILP return finite solutions;
- all plans and emergency purchases are nonnegative;
- SOC and per-interval power limits hold;
- all common model constraints hold independently;
- incremental and full solutions contain no charge/emergency conflict;
- incremental and full objectives agree within their numerical solver gaps;
- plan differences are reported even when objectives agree, because optimal
  schedules need not be unique;
- scenario source indices are strictly earlier than the target day;
- source workbooks remain unchanged.

## Known Risks

- SciPy `milp` has no warm-start interface, so each incremental round starts a
  fresh HiGHS solve.
- A new conflict may appear after earlier conflicts receive binaries; the demo
  must iterate rather than fixing only the first conflict set.
- The worst case still activates all scenario-interval binaries.
- Equal objective values do not guarantee identical purchase plans.
- A nonzero MIP gap is a numerical optimality tolerance, not an exact symbolic
  certificate.
- This demo evaluates the day-ahead optimizer only. It does not yet perform the
  full January warm-up or February-to-December causal operating replay.

## Test Findings

The synthetic no-conflict and one-conflict regression tests pass. On all four
problem-statement dates, scenario-scope activation converged in one reduced
MILP round with 576 to 720 binaries instead of 2880. Numerical objective-bound
intervals from the incremental and full models overlapped, no final physical
conflicts remained, and maximum constraint violation was below `4.4e-9`.

The exact-pair and interval-column scopes exposed a conflict-migration effect.
Constraining the current optimum can move a small number of charge/emergency
conflicts to previously inactive positions. March 20 did not converge within
20 rounds under either narrow scope. Activating the complete day for each
conflicting scenario prevents this within-scenario migration and was the only
stable tested scope.

At a `1e-3` relative gap target, scenario-scope incremental solves were 1.42x
to 1.78x faster than full MILP solves on the four selected dates. At `1e-4` on
March 20, the incremental solve finished in about 4.34 seconds with a reported
gap below the target; the full model reached its 60-second time limit with a
gap still above the target. These measurements are local benchmarks, not an
annual runtime guarantee.
