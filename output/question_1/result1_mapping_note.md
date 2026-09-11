# result1.xlsx Mapping Note

Submitted schedule: Plan A.

The supplied template is shifted by ten minutes: its purchase rows start at `0:10-0:20` and end on the following day. The source Attachment 1 labels are interpreted as interval endpoints, so the physical model covers `00:00-00:10` through `23:50-24:00`. The generated `output/question_1/result1.xlsx` corrects the row labels to those physical intervals and writes Plan A values accordingly. The immutable source template under `original_source/` is not modified. Four-hour charge/discharge totals and the explicit 0:00/24:00 SOC values use the same Plan A schedule.
