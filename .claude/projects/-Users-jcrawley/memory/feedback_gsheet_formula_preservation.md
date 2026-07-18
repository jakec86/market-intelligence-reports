---
name: Google Sheet Formula Preservation
description: General rule for ALL Google Sheet updates — never sort across formula columns, never paste values over formula cells, verify formulas intact before finishing
type: feedback
originSessionId: aec5ab60-e931-4ff7-b0bd-6b33673fab73
---
# Google Sheet Formula Preservation

When updating any Google Sheet, never sort across formula columns and never paste values over cells containing formulas. If you need to sort, copy data to a staging range, sort there, and paste only data values back into non-formula columns. Confirm the formula columns are intact before finishing.

**Why:** Multiple past sessions corrupted formulas by sorting across them or overwriting them with pasted values — the Hendrick PB sheet got its header sorted into row 4886, and a sheet-cleanup step overwrote formula columns that had to be manually restored. Formula loss is silent until someone reads the data and sees wrong numbers.

**How to apply:** Rule is global — applies to every Google Sheet operation, not just PB reports. Before any sort: identify which columns contain formulas; either exclude them from the sort range or stage the sort off-sheet. After any update: spot-check the formula columns (read a cell that should still contain `=VLOOKUP(...)` or similar) before reporting the update as done.
