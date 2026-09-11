# Question 1 result1.xlsx Template-Fidelity Fix

Date: 2026-09-11

## Problem

The generated `output/question_1/result1.xlsx` contained the correct Plan A values, but it did not strictly preserve the official workbook at `raw/附件/附件5/result1.xlsx`. The exporter changed time labels, header styling, column widths, freeze panes, and number formats. Saving through a workbook reconstruction path also removed template package parts such as printer settings and the shared-string table.

## Source And Scope

- Format reference: `raw/附件/附件5/result1.xlsx`.
- Canonical mirror: `original_source/附件/附件5/result1.xlsx`.
- The two source files must be byte-identical before export.
- Submitted schedule: Question 1 Plan A.

Only the following cells may change from blank template cells to numeric result values:

- `计划购电量!B2:B145`: 144 ten-minute grid-purchase values, in model row order.
- `充放电量!B2:C7`: six four-hour charge/discharge totals.
- `充放电量!E2:E3`: 0:00 and 24:00 stored energy.

All other cells and workbook-level resources must remain unchanged. In particular, the exporter must not correct or normalize the template's labels, restyle headers, resize columns, add freeze panes, change number formats, add worksheets, or remove printer settings.

## Implementation

1. Validate that the raw template and canonical mirror have the same SHA-256 hash.
2. Copy the template OOXML package entry-by-entry.
3. Modify only the numeric cell nodes listed above in the two worksheet XML parts.
4. Preserve all other ZIP members and worksheet structure.
5. Read the output back and verify numeric values against Plan A.
6. Compare the output package with the template: all non-worksheet members must be byte-identical, and worksheet XML must be structurally identical after removing the approved editable cells.

## Expected Output

- `output/question_1/result1.xlsx`, visually and structurally matching the supplied template, with only the required numeric result cells populated.
- `output/question_1/result1_mapping_note.md`, documenting that template labels are preserved verbatim while model/audit tables retain physical interval labels.

## Acceptance Checks

- Two worksheets with the original names and order.
- No new freeze panes, widths, styles, number formats, or labels.
- Original shared strings and printer settings retained.
- Exactly 144 purchase values, six charge totals, six discharge totals, and two SOC values match Plan A.
- Unapproved workbook content and package resources match the raw template.
- Full Question 1 build and independent exact-certificate verification still pass.

