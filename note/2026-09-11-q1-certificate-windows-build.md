# Question 1 Certificate And Windows Build Plan

Date: 2026-09-11

## Scope

This build reconciles the Question 1 Python implementation with `recieve/problem_1/第一问.pdf`, adds the missing independently verifiable optimality certificate, and makes the supported execution instructions Windows-only.

The received directory `recieve/problem_1/问题1源程序(1)/` is a reference implementation. Its files are not imported by the formal scripts and will not be copied wholesale.

## Sources

- `recieve/problem_1/第一问.pdf`: paper model, reported values, and certificate claim.
- `original_source/附件/附件1.xlsx`: immutable price, load, and PV input.
- `original_source/附件/附件5/result1.xlsx`: immutable contest output template.
- `recieve/problem_1/问题1源程序(1)/问题1源程序/`: reference only for certificate and output expectations.

## Model Reconciliation

The paper uses 144 ten-minute intervals and the battery-internal SOC increment LP:

- `g_t >= L_t - V_t + x_t / eta_c`;
- `g_t >= L_t - V_t + eta_d * x_t`;
- `-P_max * dt / eta_d <= x_t <= eta_c * P_max * dt`;
- `1200 <= s_t <= 10800`;
- `s_0 = s_144 = 6000`;
- `g_t >= 0`.

The current code additionally limits discharge to the same-interval load. That restriction is absent from the paper PDF, so this build removes it from the formal LP and its verifier. The resulting numerical schedule must be compared with the current baseline before acceptance.

## Exact Certificate

The solver remains a floating-point HiGHS LP solver. The certificate layer will:

1. read attachment values as exact decimal fractions;
2. recover the reported Plan A SOC trajectory on an exact rational lattice;
3. reconstruct the corresponding minimum grid purchase exactly;
4. verify every model inequality and bound with `fractions.Fraction`;
5. convert HiGHS inequality marginals to feasible rational dual multipliers;
6. calculate an exact primal upper bound and exact dual lower bound;
7. report exact global optimality only if the rational gap is exactly zero.

The dual certificate uses the redundant bound `g_t <= L_t + P_max * dt`. Positive prices and the charge-power bound imply that an optimum always exists within this box, so the bound does not change the paper model's optimal value. The independent verifier will reconstruct the model without calling SciPy or any optimizer.

## Outputs

- `output/question_1/certificate_q1.json`: machine-readable exact certificate.
- `output/question_1/q1_results.xlsx`: audit workbook with certificate summary.
- `output/question_1/result1.xlsx`: Plan A in the contest template, with corrected physical interval labels in the output copy.
- Existing CSV, PNG, and SVG outputs regenerated from the same Plan A/Plan B results.

The original attachment and template are never modified.

## Windows Environment Policy

- Formal commands target Windows PowerShell launched with `-NoProfile`.
- Use a repository-local `.venv` and invoke `\.venv\Scripts\python.exe` explicitly.
- Do not rely on the active Conda base environment or global `python` resolution.
- `.venv/` remains ignored and is not committed.
- Linux and Termux commands are removed from active run instructions. Existing historical environment files are not used by this build.

## Acceptance Checks

- 144 finite, nonnegative load/PV inputs and positive prices.
- HiGHS solver success and finite decision variables.
- Exact rational primal feasibility.
- Exact rational dual feasibility and zero primal-dual gap.
- Independent certificate verification against the SHA-256 and values of Attachment 1.
- Plan A and Plan B have exactly the same certified cost and different interval purchases.
- Numerical balance, SOC, power, bounds, and terminal checks pass.
- `q1_results.xlsx` and `result1.xlsx` read back successfully and match in-memory values.
- Output template contains physical intervals `00:00-00:10` through `23:50-24:00`.
- Reported cost remains approximately 35126.94858929 yuan.

## Known Risks

- Exact dual recovery depends on rationalizing HiGHS marginals. The build must fail rather than claim exact optimality if the gap is nonzero.
- The local machine currently has dependencies split across Python installations. A clean Windows `.venv` is required before claiming reproducibility.
- The received paper still contains placeholder title and abstract text; this build checks Question 1 mathematics and outputs, not full-paper editorial completion.
