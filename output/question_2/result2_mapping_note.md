# result2.xlsx Mapping Note

The generated `result2.xlsx` retains the official workbook's three worksheets,
column names, formatting resources, and non-worksheet package parts. The
abbreviated storage and emergency examples in the empty template are expanded to
the complete February 1 through December 31 records.

Attachment 2 labels each ten-minute interval by its endpoint. Audit CSV files use
physical intervals `00:00-00:10` through `23:50-24:00`. The official plan sheet
starts at `0:10-0:20` and ends at `0:00-0:10+1`; those supplied labels are not
changed. The 144 chronological planned-purchase values are written in source slot
order, and this known one-slot label offset must be stated when the table is used.

`全天计划购电量` is the sum of the 144 frozen day-ahead purchases. `全天计划购电费`
is the audited actual purchase cost: planned purchase cost plus five-times-price
emergency purchase cost. Emergency rows merge consecutive positive ten-minute
quantities into one event; their amount is summed while cost remains calculated
at the original interval prices in the audit CSV.
