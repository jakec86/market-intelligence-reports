---
name: Price Badge Report Full Automation Plan
description: Complete automation roadmap for weekly PB reports — every step, blocker, and solution. Target: Mon/Fri 6AM MST cron.
type: project
originSessionId: 5e89c129-f77f-4999-ae43-9da2b2dff386
---
## Goal: Cron-schedulable Mon/Fri Price Badge Report (Hendrick + Nalley)

### Target Schedule
- **Monday & Friday, 6:00 AM MST** (8:00 AM ET)
- Run via `/schedule` or cron trigger
- Sends draft (not auto-send) for Jake to review + fire off

---

### End-to-End Workflow (per dealer)

#### Step 1 — Tableau LEI CSV Download
- URL: `https://us-west-2b.online.tableau.com/#/site/cars/views/LowEngagedInventoryReport/LEI-Localv2`
- Auth: JumpCloud SSO (manual login, session persists in MCP browser)
- JS API sequence: `revertAllAsync()` → DMA filter → Maj dealer name → reset dependents → download crosstab
- Save to `~/Documents/Tableau/{dealer}_lei_{date}.csv`
- **Blocker:** SSO session must be active. If expired → fall back to checking `~/Downloads/` for today's CSV

#### Step 2 — Demand Signals CSV (Nalley only)
- admin.cars.com → Dealer Management → Reports → search Nalley (109754) → Demand Signals → Price Comparison tab → Download Crosstab → "Pricing" sheet + CSV
- Save to `~/Documents/Tableau/nalley_demand_signals_{date}.csv`
- CSVs are UTF-16 — convert with `iconv -f UTF-16 -t UTF-8`
- **Hendrick does NOT have a Dem Signal tab** — LEI CSV alone feeds everything

#### Step 3 — CSV Parse + Filter
- Python: `codecs` + `csv`, filter by dealer name
- **Nalley column reorder:** CSV comes as `Dealer name, Dealer id, Make name, Stock num, VIN, YMMT...` → must reorder to `Dealer name, Dealer id, Stock num, VIN, Make name, YMMT...` (swap C/D/E)
- **Hendrick:** columns match sheet directly, no reorder needed

#### Step 4 — Google Sheet Import (gspread)
- Push filtered LEI rows → "Data Import_Inventory Report" tab (clear existing data, paste from A1 including headers)
- Nalley only: push Dem Signal CSV → "Data Import_Dem Signal - $ Comp" tab
- Formulas in PBT and LEI tabs auto-update
- Wait 5 sec for formula recalc

#### Step 5 — Sort PBT Data (CRITICAL: safe sort)
```python
# NEVER sort the full sheet — it moves the header row!
# Select DATA rows only (skip rows 1-3: threshold, spacer, header)

# Hendrick: header in row 3, data starts row 4
pbt.sort((10, 'asc'), range='A4:L5000')  # Column J = col index 10

# Nalley: same structure — header in row 3, data starts row 4
pbt.sort((10, 'asc'), range='A4:L5000')  # Column J = col index 10
```
**Why this matters:** "Sort sheet" in Google Sheets sorts ALL rows including the header. The header row (row 3) has hardcoded text labels — when sorted by col J (numeric), text goes to the bottom, destroying the layout. Restoring from version history is the only fix. ALWAYS use range-limited sort.

#### Step 6 — Read Stats for Email
```python
# Read J1 (% within threshold)
j1_pct = pbt.acell('J1').value  # e.g. "25%"

# Read E1 (threshold amount)
threshold = pbt.acell('E1').value  # e.g. "$1,000"

# Count data rows
total_vehicles = len([r for r in pbt.get_all_values()[3:] if r[3]])  # col D = Stock #

# Count vehicles within threshold (non-empty J values ≤ threshold)
# Count vehicles already at Great (col I empty, col H = "Great")

# Nalley only: read Dem Signal tab for price comparison
# Count At Market / Above Market / Under Market from col G ("Value")
```

#### Step 7 — Compose Email Draft
- Gmail API with compose scope (token at `~/.claude/tokens/gmail_jcrawley.json`)
- **Port 3000 stale process:** Kill before Gmail MCP use: `lsof -ti :3000 | xargs kill -9`
- HTML body with hyperlinked "Price Badge Report" text (not raw URL)
- Email rules from memory:
  1. Hyperlink sheet link to text "Price Badge Report"
  2. Price badge insight first, then price comparison (Nalley)
  3. Say "Good or Great" not just "Great"
  4. Vary the opening line each time
  5. Blank line between "Cheers," and "Jake"
  6. Delete any blank rows before sending (VIN or Stock # missing)
  7. Sort col J by green fill ascending before sending

---

### Config per Dealer

```python
DEALERS = {
    "hendrick": {
        "sheet_id": "1guqWV9HFb2MijC7qQ7qinL4oljbu0N1o9TU5zcmy3GM",
        "pbt_gid": 565895707,
        "import_tab": "Data Import_Inventory Report",
        "pbt_tab": "Price Badge Tool",
        "maj_dealer_name": "Hendrick Automotive Group",
        "filter_keyword": "hendrick",
        "email_to": "anne.Lewis@hendrickauto.com",
        "email_subject": "Re: Cars.com: Price Badge Report",
        "threshold_col": "E1",  # $500
        "pct_col": "J1",       # 7%
        "has_dem_signal": False,
        "col_reorder": False,   # CSV columns match sheet
        "sort_range": "A4:L5000",
        "sort_col": 10,         # Column J
        "header_row": 3,
        "data_start_row": 4,
        # Layout: Row 1 = "Threshold (less than or equal to)" + $500
        #         Row 2 = Headers (SAM, Dealer, MMYT, Stock #, ...)
        #         Row 3 = Data starts
        # NOTE: Hendrick has SAM column (A), no spacer row
    },
    "nalley": {
        "sheet_id": "13Jn8vJSG7vRYW9xpuxrMi9kXNhiV_TaCrjQ5lNQRPP8",
        "pbt_gid": 565895707,
        "import_tab": "Data Import_Inventory Report",
        "dem_signal_tab": "Data Import_Dem Signal - $ Comp",
        "pbt_tab": "Price Badge Tool",
        "maj_dealer_name": "Nalley",
        "filter_keyword": "nalley",
        "email_to": "TBD",
        "email_subject": "Nalley Lexus Galleria — Price Badge Report",
        "threshold_col": "E1",  # $1,000
        "pct_col": "J1",       # 25%
        "has_dem_signal": True,
        "col_reorder": True,    # Must reorder C/D/E before import
        "sort_range": "A4:L5000",
        "sort_col": 10,         # Column J
        "header_row": 3,
        "data_start_row": 4,
        # Layout: Row 1 = Empty merged A1:D1 + $1,000 green (NO "Threshold" text)
        #         Row 2 = Empty spacer row
        #         Row 3 = Dark teal headers (MMYT, VIN, Stock #, Days Live, # Photos,
        #                 Your Price, Current Badge, Next Badge, Difference to Next Badge,
        #                 Updated Price, PTM %)
        #         Row 4+ = Data. Column A hidden (always "Nalley Lexus Galleria")
        # Col K = "Updated Price" (not "Target Price")
    }
}
```

---

### Blocking Issues

| Blocker | Impact | Workaround |
|---------|--------|------------|
| JumpCloud SSO | Tableau LEI download | Manual login once per session; cookie persists days/weeks |
| admin.cars.com SSO | Dem Signal download (Nalley) | Same JumpCloud session; or pre-download CSV |
| Row-level security | Tableau REST API exports empty | Must use web UI + JS API instead |
| Gmail port 3000 | MCP server won't connect | Kill stale process: `lsof -ti :3000 \| xargs kill -9` |

### Lessons Learned (2026-04-10 sessions)

1. **NEVER use "Sort sheet"** — moves header row into data. Use "Sort range" / `gspread.sort(range=...)` with data rows only.
2. **Nalley ≠ Hendrick layout** — different header colors (teal vs purple), different row structure (spacer row, no threshold text), different columns (Updated Price vs Target Price, VIN column present).
3. **gviz CSV API** caches aggressively — cell changes may not appear immediately in exports.
4. **Inserting rows** before sorting is safe for formulas (references shift automatically), but don't insert into the sort range.
5. **Gmail MCP** may not be available in every session — have fallback: serve HTML email locally (`python3 -m http.server`) for copy/paste into Gmail.
6. **Nalley Dem Signal CSVs** are UTF-16 encoded — must convert before processing.

**Why:** Jake wants Mon/Fri 6AM MST automated reports for both Hendrick and Nalley. SSO is the sole hard blocker.

**How to apply:** Build `~/Documents/scripts/pb_report.py` with this architecture. Test each dealer independently. Once SSO persistence is confirmed reliable, schedule via `/schedule` cron trigger.
