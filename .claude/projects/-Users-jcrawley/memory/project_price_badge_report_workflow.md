---
name: Price Badge Report Workflow
description: Step-by-step workflow for compiling and sending the weekly Price Badge Report to dealer stores
type: project
originSessionId: 5e89c129-f77f-4999-ae43-9da2b2dff386
---
Weekly report compiled for individual dealer stores using two data sources that auto-feed a Google Sheet.

**Step 1 — Tableau (Low Engaged Inventory)**
- URL: https://us-west-2b.online.tableau.com/#/site/cars/views/LowEngagedInventoryReport/LEI-Localv2
- Auth: JumpCloud SSO (jcrawley@cars.com)
- Download CSV → save to ~/Documents/Tableau/{dealer}_lei_{date}.csv

**Step 2 — admin.cars.com (Demand Signals → Price Comparison)**
- URL: https://admin.cars.com/
- Path: Dealer Management → Reports → search dealer by name/ID → Demand Signals → Price Comparison tab → Download Crosstab → select "Pricing" sheet + CSV format
- Save to ~/Documents/Tableau/{dealer}_demand_signals_{date}.csv
- NOTE: Group-level accounts (e.g. Hendrick 546973) do NOT have the Pricing crosstab — must use individual store pages for Demand Signals download
- Downloaded CSVs are UTF-16 encoded — convert with `iconv -f UTF-16 -t UTF-8` before use

**Step 3 — Google Sheet updates via Playwright**
- Paste LEI CSV into "Data Import_Inventory Report" tab (select all → delete → paste from A1)
- Paste Demand Signals CSV into "Data Import_Dem Signal - $ Comp" tab (same process)
- Use Playwright clipboard API: `context.grantPermissions(['clipboard-read', 'clipboard-write'])` → `page.evaluate(async (text) => { await navigator.clipboard.writeText(text); }, data)` → `Meta+v`
- Formulas in "Price Badge Tool" and "Low Engaged Inventory" tabs auto-update
- Update sheet title date

**Step 4 — Sort column J (SAFE METHOD ONLY)**
- **NEVER use Data > Sort sheet** — it sorts ALL rows including headers, destroying the layout
- Select data range only (e.g. A4:L54), use Data > Sort range > Advanced range sorting options > Column J, A to Z
- Or via gspread: `pbt.sort((10, 'asc'), range='A4:L5000')`

**Hendrick-specific notes**
- Group account: Hendrick Automotive Group | Customer ID 546973 (admin.cars.com UUID: 9a342d68-1a3b-537b-83a2-ff39d8507e71)
- Sheet has NO Dem Signal tab — LEI CSV alone feeds everything
- LEI CSV column order matches sheet directly (Dealer name, Dealer id, Make name, Stock num, VIN, YMMT...)
- 32 stores, ~2,800+ vehicles
- Layout: Row 1 = "Threshold (less than or equal to)" + $500 + 7%, Row 2 = Headers (purple bg, dark text, filter arrows), Row 3+ = Data

**Nalley-specific notes**
- Individual store: Nalley Lexus Galleria | Customer ID 109754 (admin.cars.com UUID: 156f9bb7-3c44-549c-b16b-0c3af73fdb1f)
- Sheet HAS Dem Signal tab (hidden by default — becomes visible after first interaction)
- CRITICAL: Data Import tab expects column order: Dealer name, Dealer id, **Stock num, VIN, Make name**, YMMT... — different from CSV order (which is Dealer name, Dealer id, **Make name, Stock num, VIN**, YMMT). Must reorder columns C/D/E before pasting.
- ~51 used vehicles, ~130 demand signals entries
- Layout: Row 1 = Empty merged A1:D1 + $1,000 green (NO "Threshold" text), Row 2 = Empty spacer, Row 3 = Dark teal headers (white bold text, filter arrows), Row 4+ = Data. Col A hidden. Col K = "Updated Price" (not "Target Price").

**Step 5 — Send to dealer**
- Email the updated report link/export to the dealer store via Gmail draft
- "Price Badge Report" text hyperlinked to sheet URL (no raw URLs)
- Include Dem Signal price comparison (At Market %, Above Market %, Under Market %) for Nalley

**Pre-send QC Checklist**
1. Sort column J by green fill color / ascending (use Sort range, NOT Sort sheet)
2. Verify J1 formula is correct: `=COUNTIFS(J4:J998,">=0",J4:J998,"<="&E1)/COUNTA(D4:D9998)`
3. Verify column L (PTM %) formatting is accurate
4. Delete any blank rows (missing VIN or Stock #)
5. Verify header row (row 3 for Nalley, row 2 for Hendrick) is intact after sort

**Why:** This is a recurring CSM report task — knowing this workflow enables automation or assistance building/sending the report.
**How to apply:** When user asks to build or send a Price Badge Report, follow this exact sequence. Target: automate to Mon/Fri 6AM MST cron.
