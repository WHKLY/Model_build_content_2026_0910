# Question 1 MWorks Script Build Plan

## Goal

Build runnable MWorks/Syslab scripts for question 1:

- load fixed source data;
- solve the deterministic battery scheduling LP;
- generate two distinct optimal purchase schedules when possible;
- verify constraints and optimal-cost equality;
- export tables and unified visualizations.

## Implementation Approach

Use MWorks/Syslab `.jl` scripts. Treat the language as MWorks/Syslab, not MATLAB.

Keep responsibilities separated:

- `q1_data.jl`: hard-coded source data module generated from Attachment 1.
- `q1_model.jl`: LP matrices and schedule recovery.
- `q1_verify.jl`: numerical and physical checks.
- `q1_plot.jl`: unified chart theme and visualization output.
- `q1_main.jl`: orchestration.

## Data Policy

Copy original competition source files into `original_source/` rather than moving them, so existing `raw/` references remain valid.

Generate `scripts/q1_data.jl` from `original_source/附件/附件1.xlsx`. It should contain explicit arrays for source labels, prices, load power, and PV forecast power. The model code imports this script instead of reading Excel repeatedly.

## Model

Use the battery-internal energy-increment LP:

- variables `z = [g_1..g_144, s_1..s_144]`;
- objective `min sum(price_t * g_t)`;
- `x_t = s_t - s_{t-1}`;
- `g_t >= 0`;
- `g_t >= n_t + x_t / eta_c`;
- `g_t >= n_t + eta_d * x_t`;
- SOC bounds and terminal SOC;
- AC-side charge/discharge power limits;
- no sale-to-grid revenue;
- allow PV curtailment.

For alternate optima:

- first solve the minimum purchase-cost LP;
- then add `purchase_cost == F*`;
- minimize and maximize `g_140` to construct two distinct optimal schedules.

## Visual Output

Use one unified theme across figures:

- consistent color palette;
- white background;
- clear gridlines;
- common time-axis labels;
- kWh for exported tables, MW/MWh where plots need compact labels.

Expected plots:

- dispatch overview with price, net load/PV context, charge-discharge, SOC, and grid purchase;
- cost comparison between no-storage, primary optimum, and alternate optimum;
- difference plot between plan A and plan B.

## Verification

Checks must include:

- input length equals 144;
- SOC lower/upper bounds;
- terminal SOC;
- charge/discharge power bounds;
- nonnegative grid purchase;
- PV curtailment nonnegative within tolerance;
- energy balance residual;
- equal optimal purchase cost for plan A and plan B;
- at least one interval with different purchase amount.

## Known Risk

MWorks/Syslab optimization, Excel, and plotting APIs must be verified against local examples. If the exact LP function is unavailable, the scripts should fail clearly and keep the model construction easy to port.
