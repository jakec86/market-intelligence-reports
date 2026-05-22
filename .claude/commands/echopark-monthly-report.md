# EchoPark Monthly Performance Report — Monthly Workflow

Run the monthly EchoPark Automotive performance report. Covers all 17 used-car superstore locations under Sonic Automotive ownership. Single group email (no brand rotation, no brand segmentation).

---

## Overview

EchoPark Automotive is a **used-car-only** brand (no new vehicles, no OEM franchise segmentation). All 17 stores share the "EchoPark Automotive [City]" naming convention. Monthly reporting is a single-group workflow — one scorecard, one email, no rotation.

**Key framing for EchoPark:** Volume + pricing efficiency is the core model. **Badge % and Cost/Lead are the most important signals** — they directly reflect how well each store is converting inventory presence into buyer engagement at competitive price points.

**Contact:** TBD — confirm the correct EchoPark/Sonic recipient before first send. Route all drafts to `scunane@cars.com` (Sharon Cunane) during test-run phase. See Recipient Mapping below.

**Tableau filter:** `vf_Maj%20Cust%20Name=EchoPark%20MA%20Group`

**Google Sheet:** TBD — create on first run, save ID to memory.

**Report folder:** `~/Documents/Reports/EchoPark/`

---

## Store Roster (17 stores)

```yaml
STORES:
  - {name: "EchoPark Automotive Atlanta (Duluth)",         ccid: "5396337"}
  - {name: "EchoPark Automotive Birmingham",               ccid: "5397548"}
  - {name: "EchoPark Automotive Centennial",               ccid: "5348836"}
  - {name: "EchoPark Automotive Charlotte",                ccid: "5383952"}
  - {name: "EchoPark Automotive Colorado Springs",         ccid: "5375247"}
  - {name: "EchoPark Automotive Dallas",                   ccid: "195001"}
  - {name: "EchoPark Automotive Houston",                  ccid: "5384904"}
  - {name: "EchoPark Automotive Houston Stafford",         ccid: "5395044"}
  - {name: "EchoPark Automotive Las Vegas",                ccid: "6000419"}
  - {name: "EchoPark Automotive Nashville",                ccid: "5395537"}
  - {name: "EchoPark Automotive New Braunfels - Outlet",   ccid: "5379242"}
  - {name: "EchoPark Automotive Phoenix",                  ccid: "5396882"}
  - {name: "EchoPark Automotive Raleigh",                  ccid: "6058184"}
  - {name: "EchoPark Automotive Sacramento - Roseville",   ccid: "6060031"}
  - {name: "EchoPark Automotive San Antonio - Outlet",     ccid: "5380236"}
  - {name: "EchoPark Automotive St. Louis",                ccid: "6058815"}
  - {name: "EchoPark Automotive Thornton",                 ccid: "5348350"}
```

**Total: 17 stores** — all used-vehicle only. Do not report new vehicle metrics (there are none).

---

## Recipient Mapping

> **CONTACT TBD — confirm before first live send.**
> All drafts currently route to Sharon Cunane during the test-run phase. Once the correct EchoPark/Sonic contact is identified, update `default_to` below and remove the `[TEST]` subject prefix.

```yaml
RECIPIENTS:
  # ⚠️ TBD — confirm EchoPark contact before going live
  default_to: scunane@cars.com       # Sharon Cunane — test-run gate
  default_cc: scunane@cars.com       # Always CC Sharon once live contact identified

  EchoPark:
    to:  [TBD]                       # ← confirm: likely EchoPark digital/marketing or Sonic liaison
    cc:  [scunane@cars.com]
```

**Known contacts from ep-review-report (may carry over):**
- Julie McAlister — `julie.mcalister@echopark.com`
- Shane Stevens — `shane.stevens@sonicautomotive.com`
- Travielle Ross — `Travielle.Ross@sonicautomotive.com`

Confirm with Jake or Sharon which contact owns the monthly marketplace performance report before first send.

---

## Email Drafting Rule

- **Always HTML-formatted** — `Content-Type: text/html`, base64url-encoded as RFC 2822 `raw` parameter. Never fall back to plain text.
- **Target length:** 200–350 words
- **Tone:** Professional-casual, data-first, action-oriented
- **Lead with:** Badge % trend and Cost/Lead efficiency — these are the EchoPark model's core KPIs
- **Vary:** opening line, lead insight, callout phrasing — never reuse prior month's opener
- **Close:** "Cheers, Jake"
- **Never:** paste raw data, use generic observations, skip the sheet link

Example openings (rotate and riff on these):
- "Here's the EchoPark monthly marketplace snapshot for {Month}..."
- "Dropping in the {Month} performance numbers for the EchoPark group..."
- "{Month} data is in — here's how the 17 stores are tracking..."
- "Quick update on EchoPark's marketplace performance for {Month}..."

---

## Steps

### Step 0 — Confirm Month

Ask: **What month are we reporting on?** (Default: prior calendar month.)

No rotation selection needed — EchoPark runs a single all-stores report every month.

---

### Step 1 — Salesforce Roster Validation

Query SF to validate the store list and capture current product packages:

```sql
SELECT Name, CCID__c, BillingCity, BillingState, Account_Status__c, Type
FROM Account
WHERE Parent.Name LIKE '%EchoPark%'
ORDER BY Name
```

Then pull active subscriptions:
```sql
SELECT SBQQ__Account__r.Name, SBQQ__Account__r.CCID__c,
       SBQQ__ProductName__c, SBQQ__NetPrice__c
FROM SBQQ__Subscription__c
WHERE SBQQ__Account__r.Parent.Name LIKE '%EchoPark%'
AND SBQQ__SubscriptionEndDate__c > TODAY
```

**Important:** Use `SBQQ__Subscription__c` for actual products, NOT `Account_Status__c` (can be stale).

Flag:
- Stores added or dropped since last month's roster
- Stores with minimal product packages (upsell candidates — Cost/Lead product especially relevant for EchoPark's model)
- SF/billing mismatches

---

### Step 2 — Tableau Health Metrics (All 17 Stores)

Pull store-level metrics from the By Store view via REST API. **No admin.cars.com needed for baseline scorecard.**

```bash
TOKEN=$(curl -s -X POST "https://us-west-2b.online.tableau.com/api/3.22/auth/signin" \
  -H "Content-Type: application/json" \
  -d '{"credentials":{"personalAccessTokenName":"Claude","personalAccessTokenSecret":"'$TABLEAU_PAT_SECRET'","site":{"contentUrl":"cars"}}}' \
  | python3 -c "import sys,json; body=sys.stdin.read(); \
    import xml.etree.ElementTree as ET; root=ET.fromstring(body); \
    creds=root.find('{http://tableau.com/api}credentials') or root.find('credentials'); \
    print(creds.attrib['token'])")

curl -s "https://us-west-2b.online.tableau.com/api/3.22/sites/12338861-20b1-46ed-8841-269a5a937edb/views/a0b9bdce-2db3-4ea0-a2fc-365fd08c5786/data?vf_Maj%20Cust%20Name=EchoPark%20MA%20Group" \
  -H "X-Tableau-Auth: $TOKEN" > echopark_health_metrics.csv
```

**Do NOT send `Accept: text/csv` header** — returns 406.

Expected: **17 stores × 48 metrics** in long/pivoted format. Pivot to wide:

```python
import csv, io, sys, os
sys.path.insert(0, os.path.expanduser("~/Documents/scripts"))
stores = {}
for row in csv.DictReader(io.StringIO(raw_csv)):
    name = row['Customer Name']
    if name not in stores:
        stores[name] = {
            'Customer Name': name,
            'Legacy Id': row['Legacy Id'],
            'Maj Cust Name': row.get('Maj Cust Name', ''),
            'AE': row.get('AE', ''),
        }
    stores[name][row['Measure Names'].strip()] = row['Measure Values']
stores_list = list(stores.values())
```

**Key metrics (all CP/PP/Delta) — EchoPark priority order:**
1. **Used VDP Total Imps** (CP/PP/Delta) — primary volume signal
2. **Cost/Lead** (CP/PP/Delta) — pricing efficiency flag
3. **Avg Daily Vehicles (Used)** — inventory depth
4. **Avg Daily Pct Minimally Merchandised (Used)** — listing quality
5. **Total Contacts** (CP/PP/Delta) — note: pull Connections from admin.cars.com for flagged stores
6. **Avg Daily Rating** — reputation health

**Note:** EchoPark is used-vehicle only. If New vehicle metrics appear in the Tableau export for any store, treat as data artifact — do not include in the report.

**Schema validation:** Before parsing, confirm the returned columns include `Measure Names`, `Measure Values`, `Legacy Id`, `Customer Name`. If column structure differs from expected, stop and surface the diff before proceeding.

---

### Step 3 — admin.cars.com (Flagged Stores Only)

**Requires active JumpCloud SSO session.** Prompt:
> "Please confirm you have an active admin.cars.com session (JumpCloud SSO), then I'll proceed with flagged-store deep dives."

If user skips SSO, run in `--skip-admin` mode — Tableau-only scorecard, no deep dive.

For each store flagged HIGH or MEDIUM in Step 5 (top 3–5 stores):

**3a. Performance Trends** — `https://admin.cars.com/dealers/{UUID}/reports/performance_trends`

Discover UUIDs via: `https://admin.cars.com/dealers/all/reports?query={store_name_or_ccid}`

Cache discovered UUIDs in memory. Capture:
- Avg Inventory (Used) + MoM %
- Under-Merchandised % + MoM change
- Connections (total) + MoM %
- VDPs (Used, total) + MoM %
- Fair/Above Badge % — **critical for EchoPark; this directly measures price competitiveness**

**3b. Demand Signals** — `https://admin.cars.com/dealers/{UUID}/reports/demand_signals`

Download Market Comparison crosstab (CSV) for flagged stores. Compute per `/dealer-marketshareanalysis` methodology:
- VDP Index = VDP Share % / Vehicle Share %
- Connection Index = Connection Share % / Vehicle Share %
- Share Index = (VDP Index × 0.4) + (Connection Index × 0.6)
- Quadrant: Churner / Lot Sitter / Rarity / Niche (median split)
- Signal: Market Leader / Underperformer / Well Positioned / Oversaturated / Niche Winner / Hidden Gem / Specialty / Low Priority

**EchoPark Demand Signals interpretation:**
- "Lot Sitter" (high inventory share, low VDP share) → pricing or merchandising issue → check Badge %
- "Churner" (low inventory, low VDPs) → inventory depth problem → check Avg Daily Vehicles trend
- "Rarity" + low SI → Hidden Gem / Niche Winner → less urgent but note in bright spots

---

### Step 4 — Market Demand Context (DI per Store)

Per-store Market DI from admin.cars.com Market Comparison (Step 3b):

```
Store Market DI = Store VDP Share of DMA ÷ Store Inventory Share of DMA
% to Market = (DI − 1) × 100
```

- DI > 1.0 → store captures more VDP share than inventory share → out-merchandising/pricing market
- DI < 1.0 → underperforming relative to inventory share → pricing or listing quality issue

**Group-level rollup:** Aggregate per-DMA to avoid double-counting shared markets (e.g., Houston has two EchoPark stores — Houston and Houston Stafford). Use same per-DMA aggregation logic as Sonic:

```
For each DMA with ≥1 EchoPark store:
    group_dma_vdps / market_dma_vdps
  ÷ group_dma_inventory / market_dma_inventory
```

**Fallback (no admin data):** Portfolio DI vs EchoPark group average. Label explicitly as **"Internal benchmark (vs EchoPark group avg)"** — never surface as market comparison in stakeholder copy.

---

### Step 5 — Store Scoring via investigation_triggers.py

```python
import sys, os
sys.path.insert(0, os.path.expanduser("~/Documents/scripts"))
from investigation_triggers import investigate_stores, format_triage_report

# stores_list = list of wide-format dicts from Step 2
ep_results = investigate_stores(stores_list)

# show_sams=False — no SAM assignments for EchoPark yet; update once assigned
print(format_triage_report(ep_results, title=f"EchoPark — {month} {year}",
                           show_sams=False))
```

**Scenario → Playbook mapping:**
| Scenario | Trigger |
|---|---|
| 1 — Drop in Connections | Connections delta ≤ −10% (HIGH) or ≤ −5% (MEDIUM) |
| 2 — Merchandising | Minimally Merchandised % > 25%, worsening MoM |
| 3 — VDP Decrease | VDP delta ≤ −10% (HIGH) or ≤ −5% (MEDIUM) |
| 4 — Demand/Inventory Mismatch | Inventory up ≥5% while VDPs down ≥5% simultaneously |
| 5 — Lead Quality / Cost | Cost/Lead > 1.5× group median (HIGH) or > 1.25× (MEDIUM) |

**EchoPark-specific weighting:** Scenario 5 (Cost/Lead) and Scenario 2 (Merchandising) are highest-priority flags for this used-car model. Scenario 3 (VDP drop) combined with S5 strongly signals a pricing efficiency problem.

**Flag assignment:**
```python
flagged_stores = [e["store"] for e in ep_results["high"][:5]]
if len(flagged_stores) < 3:
    flagged_stores += [e["store"] for e in ep_results["medium"][:3 - len(flagged_stores)]]
bright_spot_stores = [e["store"] for e in ep_results["bright_spots"][:3]]
```

**Opportunity score:**
```python
def opportunity_score(entry):
    score = 0
    for flag in entry.get("flags", []):
        score += 30 if flag["severity"] == "HIGH" else 15
    return min(score, 100)
```

---

### Step 5b — Group Rollup

Build a single group summary row (no brand breakdown):

| Field | Computation |
|---|---|
| Store Count | 17 (verify vs SF roster) |
| Total Used VDPs | Sum of Used VDPs (CP) across all stores |
| VDP MoM% | Group total vs prior month |
| Total Connections | Sum across all stores |
| Connections MoM% | Group total vs prior month |
| Avg Badge % | Group-weighted avg Fair/Above Badge % (from admin.cars.com where available) |
| Avg Cost/Lead | Group-weighted avg (from Tableau CP) |
| % to Market | `(Group Market DI − 1) × 100` per Step 4; fallback Internal benchmark |
| DI Source | "Market" or "Internal benchmark" |
| Investigation Flags | `{len(HIGH)} HIGH / {len(MEDIUM)} MEDIUM` |
| Top Opportunity | `ep_results["high"][0]["store"]` if any HIGH, else first MEDIUM |
| Top Bright Spot | `ep_results["bright_spots"][0]["store"]` if any |

---

### Step 6 — Auto-Research Deep Dives (Top 3–5 Flagged Stores)

For each store in `flagged_stores`, lead with the scenario signals from Step 5. Use admin.cars.com data from Step 3 to direct the deep dive:

- **S1 flag** → Historical Connections report, Low Engaged Inventory tab
- **S2 flag** → Listings Optimizer; check photo/notes completion rate; Badge % trend
- **S3 flag** → Used VDP split; check SRP trend; cross-reference with Badge % (if badge % drops → pricing problem)
- **S4 flag** → Demand Signals Market Comparison; check make/model mix in DMA vs EchoPark's available inventory
- **S5 flag** → Cost/Lead vs competitor set; cross-reference with Badge % and Under-Merchandised % — EchoPark's competitive advantage depends on price badge attainment; Cost/Lead elevation is usually a badge/pricing signal

Per-store insight (2–3 sentences): what's happening → revenue/retention impact → specific next step.

---

### Step 6.5 — Group Overview Email to Contact (Verification Gate)

**BEFORE composing the main performance email (Step 7), send a pre-send review to the EchoPark contact.**

> **⚠️ CONTACT TBD** — During test-run phase, route this to Sharon Cunane only.

**To:** TBD (EchoPark contact) — use `scunane@cars.com` during test run
**Subject:** `EchoPark — {Month} {Year} Overview | Pre-Send Review`

```html
<p>[Contact first name],</p>

<p>Pre-send review for {Month} {Year} — 17 stores.
The monthly performance draft is ready pending your sign-off.</p>

<h3>Portfolio Pulse — {Month} {Year}</h3>
<p>
  17 stores · {total_used_VDPs} Used VDPs ({VDP_MoM%} MoM) · {total_connections} Connections ({Conn_MoM%} MoM)<br>
  <strong>Badge %:</strong> {avg_badge_pct} group avg · <strong>Avg Cost/Lead:</strong> ${avg_cost_per_lead}<br>
  <strong>% to Market:</strong> {±X%} ({DI_source})
</p>

<h3>Store Scorecard</h3>
<table>
  <!-- Columns: Store | Used VDPs | MoM | Connections | MoM | Cost/Lead | Badge % | Flags | Signal -->
  <!-- Sorted by Opportunity Score descending -->
  <!-- Color: MoM green/red; Badge % green if ≥70%, yellow 50–69%, red <50% -->
</table>

<h3>Headline Read</h3>
<ul>
  <li><strong>Biggest story:</strong> {one-line — top driver or risk this month}</li>
  <li><strong>Top ROI lever:</strong> {store with highest badge % gap × inventory depth}</li>
  <li><strong>Bright spots:</strong> {1–2 stores performing above group avg on both VDPs + Cost/Lead}</li>
</ul>

<p>Please reply with <strong>approved</strong>, <strong>changes requested</strong>, or specific edits.
Once approved, I'll finalize the performance email draft.</p>

<p>Cheers,<br>Jake</p>
```

**Gate logic:**
- Approved → Step 7
- Changes requested → apply edits, resend overview, loop
- No reply within 48h → ping once; do NOT auto-proceed

**During test-run phase** (until EchoPark contact confirmed):
- All drafts route **To: scunane@cars.com** with `[TEST]` subject prefix
- Remove `[TEST]` and swap recipient once contact is confirmed

---

### Step 7 — Compose Monthly Performance Email

**Gate:** Proceed ONLY after Step 6.5 overview is approved.

**Subject (test run):** `[TEST] EchoPark — Monthly Performance Update | {Month} {Year}`
**Subject (production):** `EchoPark — Monthly Performance Update | {Month} {Year}`

**To:** EchoPark contact (TBD) — `scunane@cars.com` during test run
**CC:** `scunane@cars.com` (when primary recipient is the EchoPark contact)

```html
<h3>EchoPark Automotive — 17 Stores, {Month} {Year}</h3>
<p>
  Market capture: <strong>{±X%} to market</strong> · Used VDPs {±X%} MoM · Connections {±X%} MoM<br>
  <strong>Group Avg Badge %:</strong> {pct} · <strong>Group Avg Cost/Lead:</strong> ${value}<br>
  <strong>Top story:</strong> {one-line headline — biggest story this month}
</p>

<!-- If Portfolio DI fallback used, replace % to market with:
     "Internal benchmark: {±X%} vs EchoPark group avg (market data unavailable)" -->

<h3>Store Scorecard</h3>
<table>
  <!-- Sorted by Opportunity Score descending -->
  <!-- Columns: Store | Used VDPs | MoM | Connections | MoM | Cost/Lead | Badge % | Signal -->
  <!-- Color: green MoM = positive, red = negative -->
  <!-- Bold flagged (HIGH) stores -->
  <!-- Badge % cell color: ≥70% green, 50–69% yellow, <50% red -->
</table>

<h3>Top Opportunities</h3>
<ol>
  <li><strong>{Store}</strong> — {scenario insight: what's happening + revenue impact}<br>
      <em>Action: {specific next step — badge pricing, photo completion, merchandising}</em></li>
  <!-- Up to 3 stores -->
</ol>

<h3>Bright Spots</h3>
<ul>
  <li><strong>{Store}</strong> — {what's working — VDP efficiency, Cost/Lead compression, badge attainment}</li>
  <!-- Up to 3 stores; omit section entirely if bright_spots is empty -->
</ul>

<p><a href="{Google Sheet URL}">Full data in the EchoPark Monthly Performance sheet</a></p>

<p>Cheers,<br>Jake</p>
```

Use `Content-Type: text/html` and base64url-encode as RFC 2822 `raw` parameter for Gmail API.

---

### Step 8 — Google Sheet Update

Create or update **"EchoPark Monthly Performance — {Year}"**:

**Tab: "{Month} Overview"** — group-level dashboard
- Columns: Store, CCID, Used VDPs (CP), VDP MoM%, Connections (CP), Conn MoM%, Avg Inventory (Used), Cost/Lead, Badge %, Opportunity Score, Flags (HIGH/MED), Signal, % to Market, DI Source
- Sorted by Opportunity Score descending
- Header: Poppins 11, bold white on `#6a0dad` purple
- Conditional formatting:
  - MoM% columns: green text positive, red text negative
  - Badge %: green cell ≥70%, yellow 50–69%, red <50%
  - Opportunity Score: gradient green (high) → red (low)
  - Signal column: same color scheme as `/dealer-marketshareanalysis`
- Apply all formatting via `spreadsheet.batch_update({"requests": [...]})` — no Apps Script

**Tab: "Group Trend"** — rolling across months
- One row per month: Month, Total Used VDPs, VDP MoM%, Total Connections, Conn MoM%, Avg Badge %, Avg Cost/Lead, % to Market, DI Source, HIGH Flags, MEDIUM Flags

**Tab: "Store Flags"** — rolling flag log
- Month, Store, CCID, Opportunity Score, Flag Reason, Action Taken (manual fill)

Use gspread with credentials at `~/.claude/tokens/sheets_credentials.json`.

Signal color mapping:
| Signal | Background | Text |
|--------|-----------|------|
| Market Leader | #006100 | #FFFFFF bold |
| Niche Winner | #1155cc | #FFFFFF bold |
| Well Positioned | #b6d7a8 | #274e13 |
| Hidden Gem | #9fc5e8 | #073763 |
| Specialty | #d9d9d9 | #434343 |
| Underperformer | #f6b26b | #990000 bold |
| Oversaturated | #ffe599 | #7f6000 |
| Low Priority | #efefef | #999999 |

---

### Step 9 — QC

Before creating Gmail drafts:

- [ ] All 17 stores have data in the monthly scorecard tab
- [ ] No stores with all-zero metrics (data pull failure)
- [ ] Any store with >30% MoM swing — verify it's real, not a data artifact
- [ ] All flagged stores have auto-research insights (Step 6)
- [ ] Email length 200–350 words
- [ ] Badge % and Cost/Lead values populated for all stores (or explicitly noted as unavailable)
- [ ] Google Sheet formatting correct (Poppins, purple headers, conditional colors)
- [ ] Sheet link in email body is correct
- [ ] Group Overview (Step 6.5) sent and contact approval recorded
- [ ] DI Source label consistent across Sheet + email (Market vs Internal benchmark)
- [ ] No new vehicle metrics in any store's data row
- [ ] **Test-run phase:** all drafts route To: `scunane@cars.com` with `[TEST]` prefix
- [ ] **Contact confirmed?** If not, block send and surface to user

Report QC findings before creating Gmail drafts. Resolve anomalies before proceeding.

---

### Step 10 — Create Gmail Drafts

1. Compose HTML body per Step 7 template
2. Create Gmail draft via Gmail MCP — **draft only, never send**
3. Confirm draft created; report subject line + recipient to user

Fallback: if Gmail MCP fails, save HTML to `~/Documents/Reports/EchoPark/echopark_monthly_{month}_{year}.html`

---

## Key Reference

- **Parent Group:** Sonic Automotive (EchoPark brand)
- **17 stores** — used-car only, no new vehicle franchise
- **Tableau filter:** `EchoPark MA Group`
- **Primary contact:** TBD — confirm before first live send; use `scunane@cars.com` (Sharon Cunane) during test run
- **Tableau workbook:** Cars Monthly Marketplace Dealer Health Metrics (ID: 1792343)
- **Tableau By Store view:** `a0b9bdce-2db3-4ea0-a2fc-365fd08c5786`
- **investigation_triggers:** `~/Documents/scripts/investigation_triggers.py` — use `show_sams=False`
- **Report folder:** `~/Documents/Reports/EchoPark/`
- **Google Sheet:** TBD — create on first run; save ID to memory
- **gspread token:** `~/.claude/tokens/sheets_credentials.json`
- **Related skills:**
  - `/ep-review-report` — EchoPark DealerRater review report (monthly, 1st of month)
  - `/sonic-monthly-report` — Sonic brand-segmented report (template origin)
  - `/auto-research` — deep dive playbooks for flagged stores
  - `/dealer-marketshareanalysis` — Market DI / Share Index methodology
- **Schedule:** Monthly, manually triggered
- **No rotation** — single report covering all 17 stores every month
