---
name: Hendrick PBT Formatting Rules
description: Hendrick Price Badge Tool tab formatting — header row, green colors, column K removal, sort safety
type: feedback
originSessionId: a8597a82-6dc3-492a-aade-b12c238596cb
---
**Hendrick PBT layout (finalized 2026-04-17):**
- Row 1: Threshold row — B1="Threshold (less than or equal to)", E1=$500 (green bg), J1=formula (green bg)
- Row 2: Headers — purple/blue bg (#8989EB), white bold text, centered, filter arrows enabled. Columns: SAM | Store | Vehicle | Stock # | Days Live | # of Photos | Your Price | Current Badge | Next Badge | Difference to next badge
- Row 3+: Data (formula rows referencing Data Import tab)
- Column K deleted — was redundant since PTM % is shown instead
- J1 formula: `=COUNTIFS(J4:J10000,">=0",J4:J10000,"<="&E1)/COUNTA(D4:D10000)`

**Green color matching:**
- E1 and J1 background green MUST match the J column conditional format green (`{"green": 1}` = pure green #00FF00)
- J3 (first data cell) needs explicit green background to match — conditional formatting may not cover it

**Sort safety (CRITICAL):**
- Sort range must be `A3:J{last_row}` (NOT `A2:...`) — Row 2 is the header row and MUST be excluded
- If header row gets sorted into data (text sorts after numbers to the bottom), find it by checking the last row for text like "SAM | Store | Vehicle"
- After deleting column K, sort range end column is J (was L before)

**Why:** Sorting A3:L4886 accidentally included the header row, which sorted to the very bottom (row 4886) because text values sort after numbers. Required manual header restoration and formatting rebuild.

**How to apply:** When running PB sort for Hendrick, always use `pbt.sort((10, 'asc'), range='A3:J{last_row}')` — start at Row 3, end at column J (10 columns after K deletion). Verify Row 2 still has headers after sort.
