# ACA Monthly Store Reporting — Monthly Workflow

Run the monthly ACA (Atlantic Coast Automotive) store reporting update. Manually triggered ~1x/month on a Wednesday.

---

## Overview

Atlantic Coast Automotive, Inc. (CCID: 6051462) has ~72 stores. Each month, two Tableau data exports are downloaded by the user, then processed and imported into the Google Sheet via Python/gspread. A new monthly detail tab is created, Monthly Overview is updated, and a draft email is sent to Danielle McJunkins.

**Google Sheet:** [ACA | CARS.COM - Store Reporting](https://docs.google.com/spreadsheets/d/1QFjG0ogyPz699uZbIMaAFV1PbSH26Ci2c8FiYuEjg9s/edit)

**Report folder:** `~/Documents/Reports/ACA/`

**gspread auth token:** `~/.claude/tokens/sheets_credentials.json` (scope: `spreadsheets`, refresh via `~/gcp-oauth.keys.json`)

---

## Email Drafting Rule

Each draft must feel fresh but follow a consistent strategy:
- **Vary:** opening line, phrasing of the insight stat, any notable callout (e.g. a store with a big rating jump, inventory change)
- **Keep consistent:** professional-casual tone, concise (3-5 sentences max), lead with the data, close with "Cheers, Jake"
- **Never:** use the same opening line twice in a row, be vague about the stat, or skip the sheet link

Example openings (rotate and riff on these):
- "Danielle, your ACA monthly reporting is ready for review..."
- "Here's the latest store reporting for Atlantic Coast Automotive..."
- "Monthly update is in — see below for the highlights..."
- "Danielle, dropping in the ACA numbers for this month..."
- "Quick update on ACA's monthly performance..."

---

## Sheet Structure

| Tab Pattern | Purpose |
|---|---|
| **Monthly Overview** | Trend summary — one row per month with USED, NEW, REPUTATION aggregates |
| **{Month} 26'** | Per-store monthly detail (~72 stores) — presentation tab (colored) |
| **Mrkt Sum - RAW - {Month} 26'** | Raw Tableau "Table for Export - Dealer" (54 columns, CP/PP/Delta format) |
| **Tableau - Review Data Detail - {Month}** | Raw Tableau review/reputation export (13 columns) |

### Monthly Detail Tab Columns ({Month} 26')
| Section | Columns | Metrics |
|---|---|---|
| ID/Store | A, C | Customer ID (Legacy Id), Store Name |
| **USED** | D, E, F, G | Avg Daily Used, Used SRP/VDP %, Used % with Pic, Used % with Seller's Notes |
| **NEW** | I, J, K, L | Avg Daily New, New SRP/VDP %, New % with Pic, New % with Seller's Notes |
| **REPUTATION** | N, O, P, Q | Days since last Cars review, Dealer Overall Rating, Reviews last 30 days, Total Number of Reviews |
| **Totals/Averages** | Bottom rows | Totals for count metrics, Averages for percentage metrics |

### Monthly Overview Columns (row per month starting at row 7)
B=Month, C=Avg Daily Used, D=Used SRP/VDP %, E=Used % with Pic, F=Used % with Seller's Notes, H=Avg Daily New, I=New SRP/VDP %, J=New % with Pic, K=New % with Seller's Notes, M=Days since last Cars review, N=Dealer Overall Rating, O=Reviews last 30 days, P=Total Number of Reviews

---

## Data Sources — Tableau Downloads (Manual)

Both CSVs are downloaded manually by the user from Tableau Online. They export as **UTF-16LE tab-delimited** files and must be converted to UTF-8 before processing.

### CSV 1 — Dealer Health Metrics ("Table for Export - Dealer")

- **Workbook:** Cars Monthly Marketplace Dealer Health Metrics (workbook ID: `1792343`)
- **URL:** `https://us-west-2b.online.tableau.com/#/site/cars/workbooks/1792343`
- **Filter:** Major Account = "Atlantic Coast Automotive" → Dealer-level view
- **Download:** Toolbar → Download → Crosstab → CSV
- **54 columns** in CP/PP/Delta format per dealer:
  - Maj Cust Name, Group Cust Name, Customer Name, Legacy Id, Marketplace Score, AE
  - Avg Daily Vehicles/New/Used (CP, PP, Delta)
  - Avg Daily Pct Minimally Merchandised — Total/New/Used (CP, PP, Delta)
  - VDP Total Imps/New/Used (CP, PP, Delta)
  - Total Contacts (CP, PP, Delta)
  - Marketplace Leads/New Leads/Used Leads (CP, PP, Delta)
  - Cost/VDP, Cost/Lead (CP, PP, Delta)
  - Avg Daily Rating (CP, PP, Delta)
- **Maps to:** Avg Daily Used/New in detail tab; aggregates for Monthly Overview
- **Does NOT contain:** SRP/VDP % (get from admin.cars.com Market Opportunities — see Step 2), % with Seller's Notes (from Listings Optimizer)

### CSV 2 — Review Data Detail

- **Workbook:** Same workbook or related Reputation view in Tableau
- **Filter:** Major Account ID = `6051462`
- **13 columns:** account_executive_name, Customer ID, Account Name, major_account_id, major_account_name, dealer_group_id, dealer_group_name, Max. last_review_received, >30 day reviews color, Days since last Cars review, Dealer Overall Rating, Cars/DR reviews last 30 days, Total Number of Reviews
- **Note:** Point-in-time snapshot (not period-filtered). Review dates may include current month data.
- **Note:** Contains **duplicate rows** per Customer ID. When processing, keep the row with the most populated data (non-empty rating preferred).

---

## Steps

### Step 1 — User Downloads Tableau CSVs

Open the Tableau workbook for the user:
```
open "https://us-west-2b.online.tableau.com/#/site/cars/workbooks/1792343"
```

Instruct the user to download:
1. **"Table for Export - Dealer"** — the per-dealer view filtered to ACA (inventory, merchandising, VDPs, contacts, rating)
2. **"Review Data"** — the review/reputation detail view filtered to ACA

Both saved to `~/Documents/Reports/ACA/`

### Step 2 — Download SRP/VDP Conversion from Market Opportunities

Use Playwright to download from admin.cars.com Market Opportunities (see detailed steps in "SRP/VDP Conversion" section above):
1. Navigate to `https://admin.cars.com/dealer_groups/b5bfa8c4-9e2e-454e-a56a-5a1057a58f58/reports/market_opportunities`
2. Click Store tab → filter Date range to target month → filter Stock type to "Used" → Download Crosstab CSV
3. Repeat with Stock type = "New"
4. Save both to `~/Documents/Reports/ACA/` as `{month}{year}_used_store.csv` and `{month}{year}_new_store.csv`

### Step 3 — Convert & Process CSVs (Python)

```bash
# Convert UTF-16LE to UTF-8
iconv -f UTF-16LE -t UTF-8 "Table for Export- Dealer.csv" > mrkt_sum_dealer_{month}{year}.csv
iconv -f UTF-16LE -t UTF-8 "Review Data.csv" > review_data_{month}{year}.csv
iconv -f UTF-16LE -t UTF-8 "{month}{year}_used_store.csv" | tr -d '\r' > {month}{year}_used_utf8.csv
iconv -f UTF-16LE -t UTF-8 "{month}{year}_new_store.csv" | tr -d '\r' > {month}{year}_new_utf8.csv
```

**Review data deduplication:** The review CSV has ~2 rows per Customer ID. When building the reviews dict, keep the entry where `Dealer Overall Rating` is non-empty. Join on `Customer ID` (review) = `Legacy Id` (dealer).

### Step 4 — Update Google Sheet via gspread

Use gspread with credentials at `~/.claude/tokens/sheets_credentials.json`:

```python
import gspread
from google.oauth2.credentials import Credentials
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
gc = gspread.authorize(creds)
sh = gc.open_by_key("1QFjG0ogyPz699uZbIMaAFV1PbSH26Ci2c8FiYuEjg9s")
```

1. **Create "Tableau - Review Data Detail - {Month}" tab:**
   - Duplicate prior month's Review Data Detail tab
   - Clear and populate with deduplicated review data (71 rows)

2. **Create "Mrkt Sum - RAW - {Month} 26'" tab:**
   - Duplicate prior month's raw tab → rename
   - Clear and populate with dealer CSV data (72 rows x 54 cols)

3. **Create "{Month} 26'" detail tab:**
   - Build merged data from both CSVs:
     - A=Legacy Id, C=Customer Name, D=Avg Daily Used Vehicles (CP), I=Avg Daily New Vehicles (CP)
     - E=Used SRP/VDP % (from Market Opps Used CSV), J=New SRP/VDP % (from Market Opps New CSV)
     - F/G=Used % with Pic/Seller's Notes, K/L=New % with Pic/Seller's Notes (from perf_trends/listings_optimizer)
     - N=Days since last Cars review, O=Dealer Overall Rating, P=Cars/DR reviews last 30 days, Q=Total Number of Reviews
   - Write SRP/VDP % with `value_input_option='USER_ENTERED'` (critical — otherwise stored as text)
   - Include section headers (USED, NEW, REPUTATION) and Totals/Averages row with AVERAGE/SUM formulas
   - Sorted alphabetically by Store name

4. **Update Monthly Overview:**
   - Add new row at the next available row after the last month
   - B=Month name, C=total used, H=total new, M=avg days since review, N=avg rating, O=total reviews 30d, P=total reviews all

### Step 4b — Investigation Triage

After building the store data dict from the dealer health CSV, run the investigation trigger module:

```python
import sys
sys.path.insert(0, os.path.expanduser("~/Documents/scripts"))
from investigation_triggers import investigate_stores, format_triage_report

# stores_list = list of row dicts from the wide-format ACA dealer health CSV
# Each dict already has Customer Name, Legacy Id, and all CP/PP/Delta columns
aca_results = investigate_stores(stores_list)
print(format_triage_report(aca_results, title=f"ACA — {month} {year}"))
```

The triage output prints to the console for QC visibility before the sheet and email are produced.

**Extract top stores for email callouts:**
```python
top_flags   = aca_results["high"][:3]     # up to 3 HIGH stores for email "Watch List"
bright_spots = aca_results["bright_spots"][:2]  # up to 2 bright spots for email "Standouts"
```

### Step 5 — QC Validation

- Confirm ~72 stores have data in the new monthly detail tab
- Spot-check: no blanks where data should exist, no unexpected zeros
- Compare vs prior month — flag:
  - Stores added or dropped
  - Significant metric swings (>20% change)
  - Reputation anomalies (rating drops >0.3, stores with 0 reviews in 30 days)
- Verify Monthly Overview new row matches the detail tab totals/averages
- Review investigation triage from Step 4b — any HIGH stores with >30% MoM swings should be verified as real data before appearing in the email

### Step 6 — Draft Email (do NOT send — draft only)

Use Gmail MCP to compose a draft:

**To:** Danielle McJunkins (dmcjunkins@cars.com)
**Subject:** `ACA | CARS.COM - Store Reporting - {Month} {Year}`
**Body:** (vary wording per the Email Drafting Rule above, always HTML)

```html
<p>[Varied opening — e.g. "Danielle, your ACA monthly reporting is ready for review..."]</p>

<p>[1-2 sentence group-level insight — lead with the most notable trend this month:
   VDP/connection direction, inventory shift, or reputation movement across the group]</p>

<!-- Include investigation callouts only when top_flags is non-empty -->
<p><strong>Watch List ({count} stores flagged this month):</strong><br>
<ul>
  <!-- For each store in top_flags[:3]:
       <li><strong>{store}</strong> — {primary scenario name}: {signal}</li> -->
</ul></p>

<!-- Include bright spots only when bright_spots is non-empty -->
<p><strong>Standouts:</strong><br>
<ul>
  <!-- For each store in bright_spots[:2]:
       <li><strong>{store}</strong> — {signal}</li> -->
</ul></p>

<p><a href="https://docs.google.com/spreadsheets/d/1QFjG0ogyPz699uZbIMaAFV1PbSH26Ci2c8FiYuEjg9s/edit">ACA Store Reporting</a></p>

<p>Cheers,<br>Jake</p>
```

**Rules:**
- Omit the Watch List block entirely if `top_flags` is empty
- Omit the Standouts block entirely if `bright_spots` is empty
- Keep each callout to one line — scenario name + signal only, no next-step recommendations in the email (those are internal)
- Never send directly — draft only

- **Hyperlink** the Google Sheet name (e.g. `<a href="URL">ACA Store Reporting</a>`) — do NOT paste raw URL
- Use `Content-Type: text/html` and base64url-encode as RFC 2822 `raw` parameter
- Save as draft for review — **never send directly**

---

## SRP/VDP Conversion — Market Opportunities (admin.cars.com)

**IMPORTANT:** SRP/VDP conversion must come from **admin.cars.com Market Opportunities → Store tab**. Do NOT use the Tableau "SRP Detail" view (45-col format) — it undercounts SRP impressions by ~25%, inflating conversion rates. Do NOT use the old 79-col Market Summary format either (slightly different counts). Market Opportunities is the canonical source for apples-to-apples comparison across all months.

### Group URL
`https://admin.cars.com/dealer_groups/b5bfa8c4-9e2e-454e-a56a-5a1057a58f58/reports/market_opportunities`

### Playwright Steps (requires active JumpCloud SSO session)

For each stock type (Used, then New):

1. Navigate to the Market Opportunities URL above
2. Click **"Store"** tab in the embedded Tableau viz
3. Set **Date range** filter: uncheck (All) → check only the target month
   - Use inner `<input>` checkbox refs (outer checkbox clicks may not register in Tableau iframes)
   - Click Apply after changing selections
4. Set **Stock type** filter: select "Used" or "New" (single-select listbox, no Apply needed)
5. Wait 8-10s for viz refresh. If a `.tab-glass` overlay blocks clicks, remove it:
   ```js
   document.querySelectorAll('.tab-glass').forEach(g => g.remove());
   ```
6. Click **"Download Crosstab"** (Export Data) button
7. In the dialog: select "By Store" sheet, choose **CSV** format, click **Download**
8. CSV downloads as UTF-16LE. Convert: `iconv -f UTF-16LE -t UTF-8 "By Store.csv" > mar26_used_store_utf8.csv`

### Key Columns in Export
`Month of Begin Date`, `Customer Name`, `Legacy Id`, `Unique VINs`, `Total SRP Imps`, `Total VDP Imps`, **`SRPs to VDPs`** (= VDPs / SRPs — this is the conversion rate), plus Email Lead, Phone Lead, Chat Lead, Total Leads, Total Connections, etc.

### Writing to Sheet
- Write SRP/VDP % values using `value_input_option='USER_ENTERED'` so Google Sheets parses them as numbers (not text strings). The `update_cells` batch method defaults to RAW which stores "6.78%" as text.
- Used SRP/VDP % → column E (Jan/Feb/Mar) or D (Dec — no ID column)
- New SRP/VDP % → column J (Jan/Feb/Mar) or I (Dec)

### % with Pic / Seller's Notes
- **% with Pic:** Currently sourced from admin.cars.com Performance Trends (overall, not split Used/New). Applied as the same value for both Used and New columns.
- **% with Seller's Notes (Used/New split):** Computed from admin.cars.com Listings Optimizer: `(vehicles - missing_fields) / vehicles` per stock type. Stored in `listings_optimizer_{month}{year}.json`.

---

## Key Reference

- **Account:** Atlantic Coast Automotive, Inc. (CCID: 6051462)
- **~72 stores** across FL, VA, WV, NY (franchise dealers)
- **Google Sheet:** `1QFjG0ogyPz699uZbIMaAFV1PbSH26Ci2c8FiYuEjg9s`
- **Report folder:** `~/Documents/Reports/ACA/`
- **Recipient:** Danielle McJunkins (dmcjunkins@cars.com) — internal review
- **Schedule:** Monthly on a Wednesday, manually triggered
- **Tableau workbook:** Cars Monthly Marketplace Dealer Health Metrics (ID: 1792343)
- **gspread token:** `~/.claude/tokens/sheets_credentials.json`
- **Tableau MCP PAT:** "DealerHealth" — if 401 errors, PAT may need refresh at Tableau Online profile settings
