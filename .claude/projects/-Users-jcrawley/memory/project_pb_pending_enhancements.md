---
name: project_pb_pending_enhancements
description: Pending requested changes to PB (Price Badge) report email/sheet — sorting update + deep-link email to the Price Badge tab
metadata: 
  node_type: memory
  type: project
  originSessionId: f837ad02-f48d-4c65-88ef-5f45397a6b5c
---

Requested by Jake 2026-06-15 (quick #note, to implement): two pending PB report changes —

1. **Sorting update** — change to how the PB sheet/report is sorted (specifics TBD — confirm column/order and whether sheet-side or email-callout order). MUST respect sort-safety rules: never "Sort sheet" on the PBT tab; sort the data range only, preserve the header row + col-K formulas. See [[feedback_pb_sort_safety]], [[feedback_pb_formulas]], [[feedback_nalley_pbt_filter]], [[feedback_hendrick_filter]].

2. **Email link → Price Badge tab directly** — the report email's sheet hyperlink should deep-link to the **Price Badge (PBT) tab** via its `#gid=<tab_gid>` anchor, not the spreadsheet root, so recipients land on the badge data. Touch points: `email_link_url`/`sheet_url` in `pb_dealers.py` and `compose_email_html` in `pb_report.py`; note the link currently routes through the Apps Script click-tracker redirect, so the **redirect target** is what must carry the PBT gid. See [[feedback_price_badge_email]], [[project_pb_link_tracker]].

Status: **Done per Jake 2026-06-15** — he made both changes himself; exact specifics/locations not captured here. Verify on the next scheduled run that the email's link target carries the PBT `#gid=` and the sort landed correctly, with the header row + col-K formulas preserved.
