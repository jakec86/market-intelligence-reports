---
name: Price Badge Report — Do Not Modify Formulas
description: Never change VLOOKUP indices or column J formulas on the Price Badge Tool tab — data import drives everything
type: feedback
originSessionId: d06823ff-f6a5-435e-b515-6079468439c7
---
Do NOT modify formulas on the Price Badge Tool tab (VLOOKUP indices, column J IF/ABS formulas, etc.). The formulas are correct — if data looks wrong, it's a data import issue, not a formula issue.

**Why:** Jake reverted the sheet after formula changes caused issues. The sheet formulas are calibrated to the expected Tableau export column layout. If Tableau changes columns, fix the data import, not the formulas.

**How to apply:**
- Data import is the only step: paste Tableau crosstab → Data Import_Inventory Report tab, Demand Signals CSV → Dem Signal - $ Comp tab. Formulas auto-populate.
- Before sorting column J by green, always ensure the filter is showing ALL data (clear any active filters first) so no rows get excluded.
- If data looks wrong after import, check the Data Import tab column headers — don't touch Price Badge Tool formulas.
- **After import, check that formula columns (E–J) are filled down to cover all data rows.** If any rows below the existing formula range are missing formulas, copy them down from the last populated formula row. This can happen when the new import has more rows than the previous run's formula range covered. The script does not auto-extend formulas — this is a manual step for now.
