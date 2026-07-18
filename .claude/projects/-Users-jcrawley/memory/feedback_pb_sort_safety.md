---
name: Price Badge Sort Safety
description: NEVER use "Sort sheet" on PBT — it moves the header row. Always use "Sort range" on the data-only range (e.g. A4:L54).
type: feedback
originSessionId: 5e89c129-f77f-4999-ae43-9da2b2dff386
---
NEVER use Data > Sort sheet on the Price Badge Tool tab. It sorts ALL rows including the header row (row 3), pushing it into the data and breaking the layout. This is what caused the original "top rows not formatted correctly" bug.

**Why:** The header row (row 3, dark teal with white text) has hardcoded labels, not formulas. When "Sort sheet" runs, it treats the header as a data row and sorts it by value — text headers sort to the bottom of a numeric column. Restoring from version history is the only fix.

**How to apply:**
1. Select the DATA range only (e.g. `A4:L54`, skip rows 1-3)
2. Use Data > Sort range > Advanced range sorting options
3. Choose Column J, A to Z (ascending)
4. This sorts data while keeping the header row intact

Also: the filter dropdown arrows on the header row do NOT prevent "Sort sheet" from moving the header. Only "Sort range" with an explicit data selection is safe.
