# Run Guide

## Question 1

Primary entry point:

`scripts/q1_main.jl`

Recommended workflow:

1. Open MWORKS.Syslab.
2. Set the working directory to this project root:

   `G:\a for HIT\project\Model_build_content_2026_0910`

3. Run:

   `include("scripts/q1_main.jl")`

Detailed output notes are in:

`scripts/RUN_Q1.md`

## Important Notes

- The solver scripts use MWorks/Syslab `.jl`, not MATLAB `.m`.
- Source data for question 1 is hard-coded in `scripts/q1_data.jl`, generated from `original_source/附件/附件1.xlsx`.
- Every substantial rebuild should first add a short Markdown note under `note/`.
- Results are written to `output/question_1/`.
