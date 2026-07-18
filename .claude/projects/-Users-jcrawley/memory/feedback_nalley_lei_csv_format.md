---
name: Nalley LEI CSV column order (current)
description: The Tableau LEI-Local v2 crosstab for Nalley no longer needs column reorder — CSV already matches sheet layout
type: feedback
originSessionId: f3635768-f407-43b2-b5b3-c6bedfb26fd9
---
The Tableau LEI-Local v2 crosstab CSV comes in column order: `Dealer name | Dealer id | Stock num | VIN | Make name | YMMT | ...`. This **already matches** the layout the Nalley PBT formulas expect (Stock num in column C) — so **no reorder is needed**.

**Why:** Historical memory (`project_pb_automation_plan.md`, 9 days old) states the CSV arrived as `Dealer, Dealer id, Make, Stock, VIN, YMMT` and had to be reordered. That's outdated — the CSV format changed at some point. Running the old reorder logic now moves Stock num from column C → E, which misaligns every PBT VLOOKUP (MMYT blanks, PTM % all blank, wrong vehicle callouts).

**How to apply:**
- In `pb_report.py`, Nalley config has `col_reorder: False` (as of 2026-04-20).
- If MMYT or PTM % come back blank in a future run, first inspect the raw CSV column order with `awk -F'\t' 'NR==1' file.csv` — Stock num should be column 3. If the format changes again, update the reorder logic rather than re-enabling the old swap.
- Hendrick LEI never needed reorder; that behavior is unchanged.
