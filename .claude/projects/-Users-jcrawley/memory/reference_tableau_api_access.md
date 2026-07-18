---
name: Tableau API Access Map
description: Confirmed Tableau REST API access via PAT "Claude" — view IDs, filter values, RLS behavior, and research recommendations for each view
type: reference
originSessionId: e5887f6e-ee90-42c2-9282-6053f498c62f
---
# Tableau API Access Map

**PAT:** "Claude" | **Site Role:** Viewer | **Expires:** ~April 2027 | **Auth:** SAML
**API base:** `https://us-west-2b.online.tableau.com/api/3.22`
**Site ID:** `12338861-20b1-46ed-8841-269a5a937edb`
**API gotcha:** Never send `Accept: text/csv` (returns 406). Omit the header — CSV comes back as default.

**⚠️ 2026-06-18: PAT "Claude" is DEAD** — REST signin returns `401001 "personal access token is invalid"` (Tableau Cloud PATs auto-expire after ~15 days of non-use, regardless of the April-2027 date). Tableau MCP 401s until rotated: Tableau Cloud → Account → Personal Access Tokens → delete + recreate "Claude" → update `PAT_VALUE` in `~/.claude.json` (tableau env). NOTE: the PAT lives in `~/.claude.json`, NOT `settings.json` — the `check-tableau-pat.sh` recovery script reads the wrong file and reports "config unreadable." For admin.cars.com embedded Tableau reports you can skip the PAT entirely — see [[reference_admin_cars_tableau_embed_extract]].

---

## Tier 1: Filterable by Account (Primary Research Tool)

### Dealer Health Metrics — By Store Table for Export

**View ID:** `a0b9bdce-2db3-4ea0-a2fc-365fd08c5786`
**Filter:** `vf_Maj%20Cust%20Name={value}` — WORKS, returns account-specific data
**Metrics:** 48 per store in Measure Names/Measure Values pivot (CP/PP/Delta):
- Inventory: Avg Daily Vehicles (Used/New/Total), Minimally Merchandised % (Used/New/Total)
- Engagement: VDP Total Imps (Used/New), New VDPs, Used VDPs
- Leads: Total Contacts, Marketplace Leads (Used/New)
- Efficiency: Cost/VDP, Cost/Lead
- Quality: Avg Daily Rating

| Account | vf_Maj Cust Name | Stores | Rows |
|---------|-----------------|--------|------|
| Sonic | `Sonic` | 120 | 5,808 |
| Asbury | `Asbury` | 79 | 3,792 |
| ACA | `Atlantic Coast Automotive MA Group` | 72 | 3,456 |
| Hendrick | `Hendrick Automotive Group` | 72 | 3,456 |
| Greenway | `Greenway MA Group` | 36 | 1,776 |
| Herb Chambers | `Herb Chambers MA Group` | 34 | 1,632 |
| Larry H Miller | `Larry Miller` | 32 | 1,536 |
| Doherty | `Doherty MA Group` | 21 | 1,008 |
| Jim Ellis | `Jim Ellis MA Group` | 21 | 1,008 |
| Koons | `Koons Automotive MA Group` | 18 | 864 |
| EchoPark | `EchoPark MA Group` | 17 | 816 |
| Indigo | `Indigo Auto MA Group` | 25 | 1,200 |
| #1 Cochran | (default, no filter) | 32 | 1,536 |

**Naming pattern:** Most use `{Name} MA Group`. Exceptions: `Sonic`, `Asbury`, `Larry Miller`, `Hendrick Automotive Group`.

**Research use:** Monthly brand scorecards, store-vs-store comparison, MoM trend detection, portfolio-wide health snapshots. Pivot Measure Names/Values to wide format in Python for analysis.

---

## Tier 2: Unrestricted Views (Full Universe, No RLS)

### AE Insights Dashboard
**View ID:** `a60dbfc3-0156-4728-884a-fec77a3b7d2c`
**Rows:** 75,933 | **Filter:** None needed — returns all dealers
**Columns (37):** Account ID, Account Name, AE, AE Region, AE Service Level, AE Team, Category Description, CCID, Channel, Contact Email/Name, CPL, DMA, Estimated Revenue, Focus Category, Former MKP Rate, Franchise/Independent, Inventory Aggregator, Last Activity, Last MKP Date, Main POC Email/Name, Market Category, MKP Active/Prospect, Open Opp, Paid CarGurus Sub, Pending Cancel, Product Tower, SF Total New/Used Inventory, State, Ultimate Parent Account, Yipit New/Used, Cars MRR

**Research use:**
- Instant account lookup: CCID, DMA, AE, products, MRR for any dealer
- Prospecting: filter by MKP Active/Prospect, Market Category, DMA
- Portfolio intelligence: compare MRR, product adoption, inventory across accounts
- Contact discovery: Main POC Email/Name, Last Activity dates
- Competitive intel: Paid CarGurus Sub, Inventory Aggregator, Yipit inventory counts

### Searches by Zip Code
**View ID:** `39464986-86f3-49a2-af82-37f1486743ff`
**Rows:** 490,645 | **Filter:** None needed — returns all DMAs
**Columns:** dma_market_name, Quarter of first_date_of_month, Year of first_date_of_month, zip_code, % Difference in searches

**Research use:**
- Market intelligence reports (replaces manual Tableau crosstab download)
- DMA-level demand trends by ZIP and quarter
- Download full dataset → filter by DMA/make in Python (same as generate_market_report.py)
- Identify growing/declining markets for prospect targeting

### Marketplace Market Share and Opportunity
**View ID:** `9528856a-7213-44de-8950-47457c0db012`
**Columns:** Franchise/Independent, Market Category, ARPD, Share %, Prospects count

**Research use:** Market-level prospect sizing by category and franchise type. Useful for pipeline analysis and territory planning.

### Major Accounts Product Summary
**View ID:** `7b02b87e-117c-4c7e-b995-7193854fcad3`
**Filter:** `vf_Ultimate%20Parent%20Account={name}` — returns monthly trend
**Columns:** Month, Year, % Share of Stores

**Research use:** Product adoption trends by account over time.

---

## Tier 3: RLS-Locked Views (Default Dealer Only)

These return data but `vf_` filters are silently ignored. Data is for the RLS-default dealer (currently Cochran/Arthur Carina). Useful for understanding data structure; NOT useful for account-specific research until RLS is remapped.

| View | ID | Rows (default) | Data |
|------|-----|----------------|------|
| LEI - Local v2 | `6b8a7ea9-9ad2-4677-b044-c088c776ce23` | 279,820 (231 dealers) | VIN-level: badge, price, make, photos, days live, SRPs. **All filters ignored** (DMA, Maj Cust Name). In UI, DMA must be changed to "All" before crosstab download — this cannot be done via API. |
| Competitive Set | `ac634cc0-a5ed-4b10-9d04-82dab8a4410a` | 81 (9 dealers) | % share: Vehicles, Email, Phone, Leads, SRPs, VDPs, Rating |
| Radius Performance | `e31f8d3e-2a82-41a1-ad52-e0480cd9c426` | 522 | SRP/VDP by ZIP, distance, lat/lon |
| Market Comparison (badges) | `9cdedf40-a1ec-415b-bc34-8270fa05f5fb` | ~26 | Badge % dealer vs DMA, 13 months |
| Market Comparison (group) | `a1e57e53-3c10-4c24-b990-b67dc7d02aaf` | ~26 | Connections/VIN dealer vs DMA |
| Price Comparison | `b2abcde2-df35-4c0c-83ba-fad29956ff37` | 523 | VIN-level: price, days live, market position |
| Performance Trends | `50534dda-fa3b-4ac2-9380-7a3df61a09c8` | ~1 | KPI summary tiles only |
| DealerRater Experience | `42f8be05-9afe-4b12-962d-ed658e45b65b` | ~2 | Avg rating dealer vs DMA |
| Review Details | `56e5d504-4e74-45a3-b17e-04a5113e63da` | ~1 | Review count + avg rating |
| Market Area Planner | `a0f0ef43-2345-42e5-b048-784aeb88e230` | ~9 | Vehicle category metrics |

**If RLS default is remapped to Jake's book**, these unlock instantly:
- LEI becomes a direct API replacement for manual LEI crosstab downloads (price badge reports)
- Competitive Set gives anonymous share comparison vs peers
- Radius Performance shows where dealer impressions/leads originate geographically

---

## Research Recommendations

### For Monthly Reporting (Sonic, ACA, Hendrick, etc.)
1. **Primary:** Health Metrics API (Tier 1) — 48 metrics per store, filterable by account
2. **Supplement:** admin.cars.com for per-dealer deep dives (Demand Signals, Market Comparison crosstab, MAE splits)
3. **Context:** AE Insights for account metadata, Searches by Zip Code for market demand

### For Prospecting / Pipeline Analysis
1. **AE Insights Dashboard** — filter by MKP Active/Prospect, Market Category, DMA
2. **Marketplace Market Share and Opportunity** — prospect counts by category
3. **Searches by Zip Code** — identify high-demand DMAs for targeting

### For Auto-Research / Dealer Deep Dives
1. **Health Metrics** (Tier 1) for the portfolio-level view + store scoring
2. **admin.cars.com** for the deep dive: Demand Signals crosstab → Share Index, Performance Trends → badge/merchandising, Connections Contact Details → MAE vs organic
3. **AE Insights** for instant CCID/DMA/product/contact lookup (faster than SF query)

### For Market Intelligence Reports
1. **Searches by Zip Code** (Tier 2) — download full 490K rows, filter in Python
2. Replaces the Playwright-based Tableau crosstab download in generate_market_report.py
3. No PAT refresh issues — same API call every time

### What Still Requires Playwright (Tableau UI or admin.cars.com + JumpCloud SSO)
- **LEI crosstab download** — API returns RLS-default DMA only; in UI, DMA must be changed to "All" + Maj Dealer filtered before download. Treat as manual step per existing PB workflow.
- Demand Signals Market Comparison crosstab (per-dealer make/model share data)
- Market Opportunities SRP/VDP conversion (per-dealer, per-stock-type)
- Connections Contact Details (MAE vs organic split)
- Listings Optimizer (Best Match scoring, photo analysis)
- Indigo deep dives beyond Health Metrics (use admin.cars.com)
- Any VIN-level data for a specific dealer (LEI/Price Comparison are RLS-locked)

---

## Quick Reference: API Call Pattern

```bash
# 1. Authenticate
TOKEN=$(curl -s -X POST "$BASE/auth/signin" \
  -H "Content-Type: application/json" \
  -d '{"credentials":{"personalAccessTokenName":"Claude","personalAccessTokenSecret":"'"$TABLEAU_PAT_SECRET"'","site":{"contentUrl":"cars"}}}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['credentials']['token'])")

# 2. Pull data (NO Accept header)
curl -s "$BASE/sites/$SITE_ID/views/$VIEW_ID/data?vf_Maj%20Cust%20Name=Sonic" \
  -H "X-Tableau-Auth: $TOKEN" > output.csv

# 3. Parse pivoted data to wide format
python3 -c "
import csv, io
with open('output.csv') as f:
    stores = {}
    for row in csv.DictReader(f):
        name = row['Customer Name']
        if name not in stores:
            stores[name] = {'ccid': row['Legacy Id']}
        stores[name][row['Measure Names'].strip()] = row['Measure Values']
    # stores is now {dealer: {metric: value, ...}}
"
```
