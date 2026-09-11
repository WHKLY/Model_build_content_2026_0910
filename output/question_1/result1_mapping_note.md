# result1.xlsx Mapping Note

Submitted schedule: Plan A.

The generated `output/question_1/result1.xlsx` strictly preserves the official template at `raw/附件/附件5/result1.xlsx`, including its original purchase-row labels, formatting, worksheets, shared strings, and printer settings. Only the designated blank numeric result cells are populated.

The model interprets Attachment 1 labels as interval endpoints and therefore covers physical intervals `00:00-00:10` through `23:50-24:00`. Those physical labels are retained in the audit CSV and `q1_results.xlsx`; they are not written over the official template. Purchase values are written in the template's existing row order. Four-hour charge/discharge totals and the explicit 0:00/24:00 SOC values use the same Plan A schedule.
