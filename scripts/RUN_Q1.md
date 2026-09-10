# Run Question 1

## Recommended Way

Use MWORKS.Syslab 2024a or 2026a.

1. Open Syslab.
2. Set the working directory to the project root:

   `G:\a for HIT\project\Model_build_content_2026_0910`

3. Open and run:

   `scripts/q1_main.jl`

The script imports hard-coded data from `scripts/q1_data.jl`, so it does not need to read Excel during solving.

## Expected Output

The script writes files under:

`output/question_1/`

Expected table outputs:

- `q1_schedule.csv`
- `q1_summary.csv`
- `q1_four_hour_summary.csv`
- `q1_target_purchase.csv`
- `q1_results.xlsx` if Excel COM export succeeds

Expected visualization outputs:

- `figures/q1_dispatch_overview.png`
- `figures/q1_dispatch_overview.syslabfig`
- `figures/q1_plan_difference.png`
- `figures/q1_plan_difference.syslabfig`
- `figures/q1_cost_comparison.png`
- `figures/q1_cost_comparison.syslabfig`

## If Excel Export Fails

The CSV outputs are the primary fallback. Excel export uses Windows COM through `PyCall` and requires Microsoft Excel to be installed and available to the Syslab Python bridge.

## If PNG Export Fails

Open the generated `.syslabfig` files in Syslab and export manually. The plotting code still creates the figures with the same visual style.
