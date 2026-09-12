# Question 2 Teammate Result Comparison

Date: 2026-09-12

## Scope

This review compares the formal conflict-driven incremental MILP workflow with
the user-supplied teammate files:

- `第二问_完整可运行代码.py`
- `逐段明细.csv`
- `逐日汇总.csv`
- `物理审计.csv`
- `方案对比.csv`
- `result2.xlsx`
- `第2问解决路线.docx`

The teammate files were read only. They were not copied into the formal solver
and were not used as optimization inputs.

## Plain-Language Interpretation

The forecast residual is the real-world prediction miss: actual load/PV minus
what could have been forecast before that day. Historical complete-day residuals
are reused to make plausible versions of tomorrow.

The physical residual is an equation check after optimization. For example,
`supply - demand` should be zero and `reported SOC change - charge/discharge SOC
change` should be zero. Residuals around `1e-12 kWh` are numerical rounding, not
an energy shortage.

The MILP gap compares the cost of the best feasible schedule found with the
solver's mathematical lower bound. A gap of `1e-3` means the schedule is within
about 0.1% of the global optimum for the model's surrogate objective. It does not
mean the power balance is wrong by 0.1%.

LP permits continuous decisions and is fast. MILP adds binary mode switches to
forbid business-invalid combinations such as charging while buying emergency
energy. The formal incremental method first solves the LP, then adds switches
only to complete scenarios that exhibit a conflict. Once no conflict remains,
the candidate is feasible for the full MILP logic; the partial model's lower
bound also supplies a valid optimality bound for the full model.

## Independent Audit Of Teammate Output

The teammate stochastic detail contains exactly 334 days and 48096 ten-minute
rows, with no duplicate date/slot keys or missing values. Independent
recalculation found:

- maximum supply-balance residual after CSV round-trip: `6.82e-13 kWh`;
- maximum SOC-recurrence residual after CSV round-trip: `4.45e-12 kWh`;
- maximum interval cost residual: `1.82e-12 yuan`;
- no simultaneous charge/discharge conflict;
- no simultaneous charge/emergency conflict;
- exact cross-day SOC continuity within stored precision;
- daily and interval aggregates agree within `2.91e-11`.

These are strong physical-consistency results.

Two reporting inconsistencies remain:

1. The document states 167 optimal MILP days, 12 LP-certified days, and 186
   time-limit days. Those counts sum to 365 and describe the January-inclusive
   run, while the exported February-December audit contains 157 optimal and 177
   time-limit days, with no LP-certified rows. The scope must be labeled.
2. The document states 3305 emergency events. Regrouping the exported detail and
   reconciling the workbook gives 3306 positive events plus 95 zero-event day
   rows. The paper count should be regenerated from the final selected result.

The teammate `result2.xlsx` is not a strict contest-template output. It contains
six sheets instead of three, the plan sheet has 150 columns instead of 147, and
the emergency sheet has five columns instead of three. Its audit information is
useful but belongs outside the official workbook.

## Full Formal Run

Configuration: 20 scenarios, paired whole-day residual sampling, scenario-level
conflict activation, 30-second daily MILP limit, and `1e-3` requested relative
gap. January is simulated continuously and formal output covers February 1
through December 31.

| Metric | Formal incremental | Teammate | Difference |
|---|---:|---:|---:|
| Total actual cost (yuan) | 24,240,218.72 | 24,290,408.96 | -50,190.24 (-0.207%) |
| Planned cost (yuan) | 15,008,198.87 | 15,036,054.41 | -27,855.54 |
| Emergency cost (yuan) | 9,232,019.85 | 9,254,354.55 | -22,334.71 |
| Planned energy (kWh) | 23,810,400.11 | 23,843,860.18 | -33,460.07 |
| Emergency energy (kWh) | 1,711,097.53 | 1,701,674.81 | +9,422.73 (+0.554%) |
| Emergency days | 239 | 239 | 0 |
| Curtailment (kWh) | 2,105,007.33 | 2,105,160.36 | -153.03 |
| Terminal SOC (kWh) | 1,200.00 | 1,200.00 | 0 |

The formal point-forecast baseline matches the teammate baseline to roughly
`1e-13` relative precision across cost and energy totals. This is important: it
shows that source data, causal point forecast, cost accounting, and real-time
controller are aligned. The stochastic difference is therefore attributable to
different near-optimal MILP schedules and the SOC path they induce, not a basic
input or unit mismatch.

Compared with the point forecast, the formal stochastic plan saves
1,212,130.07 yuan, or 4.762%.

## Solver Quality And Performance

For the 334 formal output days:

- all 334 incremental MILPs reached the requested gap;
- median gap: `2.28e-4`; maximum gap: `9.89e-4`;
- 299 days closed in one incremental MILP round and 35 in two rounds;
- median active binaries: 576 of 2880; maximum: 1008;
- no day required the full 2880 binaries;
- median daily model solve time: 4.58 seconds; maximum: 14.95 seconds;
- cumulative stochastic model solve time: 29.07 minutes.

The teammate output records 157 gap-reached solutions and 177 time-limit
solutions for the same 334-day reporting period. Excluding its sleep-contaminated
2025-08-08 timing row, its cumulative recorded solve time is 149.31 minutes.
Against that like-for-like daily solver field, the incremental method is about
5.14 times faster.

On all four specified dates, the incremental and full-MILP objective bound
intervals overlap, both solutions have zero charge/emergency conflict, and the
incremental model uses 576-720 binaries instead of 2880. Measured solve speedups
range from 1.69 to 2.25 times for these direct full-MILP reruns.

## Result Selection

Use the formal incremental output as the computational result because it has the
same modeled physics, strictly better documented optimality bounds, lower cost in
the realized replay, faster solution time, and a template-conforming workbook.
Do not describe its interval schedule as uniquely optimal. State that each daily
day-ahead solution is globally optimal within its reported MILP gap for the
stated sampled-scenario model.
