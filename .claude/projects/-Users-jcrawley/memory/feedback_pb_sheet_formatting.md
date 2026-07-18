---
name: Price Badge Sheet Formatting Automation
description: Automated formatting steps for PBT tab — MUST use in-place Sheets API sort, NEVER clear+rewrite (destroys VLOOKUPs)
type: feedback
originSessionId: a381b1b2-dc17-49cc-aefd-c546ad1ffdff
---
After data import to the Price Badge Tool tab, apply these formatting steps automatically:

1. **Remove blank Stock # rows** — delete rows where Stock # (col D) is empty
2. **Sort SAMs alphabetically A-Z** — sort data range by col A ascending
3. **Sort column J by green fill first** — green = within $500 threshold = smallest J values; sort J ascending achieves the same result

**CRITICAL: NEVER use clear+rewrite on the Price Badge Tool tab.** Reading values and writing them back replaces VLOOKUP formulas with static text, breaking the sheet for future weeks. This happened on 2026-04-10.

**Why:** The PBT tab has VLOOKUPs to Data Import + SAM Assignment tabs, and a COUNTIFS formula in J1 (`=COUNTIFS(J4:J8999,">=0",J4:J8999,"<="&E1)/COUNTA(D4:D8999)`) that computes the badge % stat. These formulas are the backbone of the sheet.

**Correct approach for automation:**
- Use Sheets API `SortRangeRequest` via batchUpdate to sort in place (preserves formulas)
- For blank row deletion: leave blank rows at bottom (formulas return empty, no visual harm) — deleting is risky and slow
- Read J1 AFTER formulas recalculate (wait a few seconds after data import)
- `gspread.Worksheet.sort((1, 'asc'), range='A4:J5000')` works for in-place sort and preserves formulas

**How to apply:** In the PB Report workflow, after importing data to Data Import tab:
1. Wait for formulas to populate (~5 sec)
2. Use `pbt.sort((10, 'asc'), (1, 'asc'), range='A4:J5000')` — sorts J asc then SAM asc, in-place
3. Read J1 for the email stat
4. Do NOT clear, rewrite, or batch-delete rows on the PBT tab
