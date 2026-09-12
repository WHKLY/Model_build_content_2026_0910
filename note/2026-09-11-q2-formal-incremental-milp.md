# Question 2 Formal Conflict-Driven MILP Build

Date: 2026-09-11

## Purpose

Build the complete Question 2 Python workflow from the isolated demo. The formal
workflow must solve the continuous 2025 replay, preserve the day-ahead
information boundary, export the official `result2.xlsx` template without
changing its structure, and produce independent audit tables. Teammate outputs
are comparison evidence only and are never used as solver inputs.

## Sources

- Problem statement: `original_source/C题.pdf`
- Price and nominal curves: `original_source/附件/附件1.xlsx`
- Actual 2025 load and PV: `original_source/附件/附件2.xlsx`
- Official output template: `original_source/附件/附件5/result2.xlsx`
- Experimental solver: `demo/q2_incremental_milp.py`
- Received method document and teammate run under `recieve/problem_2/` and the
  user-provided external Q2 directory

Original workbooks are immutable. Formal outputs go to `output/question_2/`.

## Time And Energy Convention

- One interval is 10 minutes, so `dt = 1/6 h`.
- Source load and PV values are kW and are converted to interval kWh by
  multiplication by `1/6`.
- Attachment 2 labels are interval endpoints. Audit data use physical intervals
  `00:00-00:10` through `23:50-24:00`.
- The official template labels are preserved verbatim even though its first
  displayed interval is shifted. Values are written in chronological slot order.

## Battery And Cost Assumptions

- Capacity: 12000 kWh.
- SOC bounds: 1200 to 10800 kWh.
- Initial SOC at 2025-01-01 00:00: 6000 kWh.
- Charge and discharge efficiencies: 0.9.
- AC-side charge/discharge power limit: 5000 kW, or 833.333333 kWh per slot.
- No sale-to-grid revenue. PV may be curtailed.
- Day-ahead purchases are paid in full even when unused.
- Emergency purchases supply the remaining load only and cost five times the
  interval transaction price. They cannot charge the battery.
- January is a causal warm-up period. Its terminal SOC becomes the February 1
  initial SOC. Official output covers February 1 through December 31.

## Forecast And Scenarios

- Point forecast: same-slot mean of the preceding seven completed days.
- Forecast residual: actual minus the forecast that was available before that
  historical day.
- Stochastic scenarios: sample up to 20 complete residual days without
  replacement from the preceding 28 days and add each complete residual path to
  the target-day point forecast.
- Load and PV residuals from the same source day stay paired. This preserves
  within-day persistence and cross-series dependence.
- Every scenario source index must be strictly earlier than the target day.

## Day-Ahead Optimization

The first-stage variable `q[t]` is the common frozen day-ahead purchase. Each
scenario has recourse SOC, emergency energy, and terminal-SOC shortfall. The
objective is planned purchase cost plus expected five-times-price emergency cost
plus a terminal shortfall penalty used only for planning.

The battery energy change is represented by the convex piecewise-linear relation
used in the existing implementation. A positive SOC change implies AC-side
charge `delta/eta_c`; a negative change implies delivered discharge
`eta_d*(-delta)`. Supply may exceed demand because unused planned electricity and
curtailment are allowed.

### Conflict-Driven Integrality

1. Solve the continuous LP relaxation.
2. Detect scenario slots with both positive charge and emergency purchase.
3. If none exist, the LP solution is feasible for the full MILP and its LP lower
   bound certifies global optimality for the stated model.
4. Otherwise activate binary charge/emergency mode constraints for every slot in
   each conflicting scenario, then solve the smaller MILP.
5. Repeat only if a previously inactive scenario develops a conflict.
6. Accept a solution only when no full-model conflict remains. Record the solver
   dual bound and relative gap. A feasible solution is described as globally
   optimal only within that reported gap.

Scenario-level closure is intentional. Pair-only and interval-only activation
were tested and allowed conflict migration across iterations. Scenario closure
converged in one round on all four specified dates while using 576-720 binaries
instead of 2880 for the full 20-scenario MILP.

## Real-Time Replay

After `q[t]` is fixed, a receding-horizon LP uses the current actual net load and
only the day-ahead forecast for future intervals. It executes one battery action,
clips that action to physical limits and available surplus/deficit, purchases any
remaining deficit as emergency energy, and passes SOC to the next interval and
day. The day-ahead plan is never modified during replay.

## Script Plan

- `scripts/q2_data.py`: paths, validated input loading, causal forecast, scenarios.
- `scripts/q2_model.py`: model construction and conflict-driven incremental MILP.
- `scripts/q2_control.py`: frozen-plan causal real-time replay.
- `scripts/q2_verify.py`: independent physical, causal, cost, and output checks.
- `scripts/q2_export.py`: audit CSVs and strict official-template export.
- `scripts/q2_main.py`: command-line orchestration, checkpointing, and comparison.
- `scripts/RUN_Q2.md`: reproducible commands and interpretation.
- `tests/test_q2_workflow.py`: synthetic and selected-date regression checks.

After review, the same self-contained modules may be copied into
`one_touch_start/scripts/` and Question 2 registered there. The bundle must read
only `one_touch_start/assets/`.

## Required Outputs

- `output/question_2/result2.xlsx`: exact official template structure with only
  designated result cells populated.
- `q2_detail.csv`: 10-minute execution trajectory.
- `q2_daily.csv`: daily costs, energy totals, SOC, solver status, gap, conflicts,
  binary counts, and solve time.
- `q2_audit.csv`: independent residuals and pass/fail checks.
- `q2_comparison.csv`: stochastic method versus point-forecast baseline.
- `q2_team_comparison.csv`: comparable metrics against the supplied teammate run
  when its directory is available.
- `result2_mapping_note.md`: template-to-physical-slot mapping statement.

No figures are required for this build.

## Verification Gates

- Exactly 365 source days and 144 intervals per day; finite nonnegative data.
- No forecast or scenario uses current-day or future actual data.
- Solver returns finite variables and a feasible status.
- No charge/discharge or charge/emergency overlap above tolerance.
- Supply balance and SOC recurrence residuals stay within tolerance.
- SOC and power bounds hold at every interval and across day boundaries.
- Exported cost equals `sum(price*q + 5*price*emergency)`.
- February-December output has exactly 334 days and 48096 detail rows.
- Official workbook retains exactly three sheets, original labels, styles, package
  members, printer settings, and all non-editable cells.
- Template purchase rows, six four-hour totals per day, 0:00/24:00 SOC entries,
  and emergency events read back equal the audited schedule.
- Selected-date incremental results are compared with full MILP bound intervals.
- Full-period aggregate differences from the teammate run are reported, not
  silently treated as errors, because different valid near-optimal plans may
  differ within solver gaps.

## Known Risks

- A 20-scenario daily MILP over 365 days is CPU-intensive. Checkpointing is
  required so interruption does not lose completed days.
- A `1e-3` MIP relative gap is a cost-bound tolerance, not a physical residual.
- The terminal penalty is a policy parameter and not part of reported actual
  purchase cost. Its sensitivity should be discussed in the paper.
- The official template contains a shifted interval header. The template is
  preserved and the discrepancy is documented rather than silently corrected.
- Multiple near-optimal schedules can have similar cost but different interval
  purchases and SOC trajectories. Comparison must use cost bounds and physical
  checks, not elementwise schedule equality alone.

## Completed Verification (2026-09-12)

- Four synthetic/model/template tests passed.
- A real March 20 formal-module run activated 720 of 2880 binaries, removed all
  conflicts in one round, and had an objective-bound interval overlapping the
  full MILP.
- The continuous 365-day stochastic and point-forecast replays completed.
- All 334 formal output days passed independent physical and causal checks.
- Every output-day stochastic solve reached the requested `1e-3` gap; maximum
  reported gap was `9.89e-4`.
- The strict template exporter passed package, sheet, header, shape, and value
  read-back checks.
- The four specified dates passed incremental-versus-full-MILP bound comparisons.
- Formal stochastic actual cost was 24,240,218.72 yuan, 4.762% below the aligned
  point-forecast baseline and 0.207% below the supplied teammate stochastic run.
