---
name: feedback_hendrick_pb_email_format
description: "Hendrick PB report email format — SAM + vehicle + target price, not store + diff; QC tab check added"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 3bd82dce-9e2f-4eda-94a1-7b8dd0925334
---

Show SAM name, vehicle, and target price to reprice to — not store name and price difference.

**Format:** `SAM — Vehicle → reprice to $X for [Next Badge]`
Example: `Abby Livingston — 2018 Porsche Macan Macan Turbo → reprice to $27,872 for Great`

**Why:** Anne and her team act on actionable instructions (who, what vehicle, what price) rather than diagnostic info (which store, how much gap).

**How to apply:** pb_report.py now captures SAM (col A), Vehicle (col C), Stock # (col D), Your Price (col G), and computes target_price = Your Price − Diff. Top-5 email callout uses this format. Deduplicated by stock number (LEI CSV has 2 rows/vehicle).

**QC tab check:** pb_report.py now runs `qc_other_tabs()` after hiding the import tab. Checks Inventory Engagement, Low Engaged Inventory, and Missing Features_AutoCorrected for non-empty data. Warns if any tab is empty.
