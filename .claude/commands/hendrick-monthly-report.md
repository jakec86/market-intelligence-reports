# Hendrick Monthly Brand Performance Report — Monthly Workflow

Run the monthly Hendrick Automotive Group brand performance report. Produces per-brand email drafts with store scorecards, market context, and actionable deep dives.

---

## Overview

Hendrick Automotive Group (~72 active stores, 19 brands) gets brand-segmented monthly reporting on a **rotating schedule**:
- **Luxury rotation (odd months):** BMW, Acura, Audi, Lexus, Mercedes-Benz, Porsche = 20 stores
- **Volume rotation (even months):** Honda, Chevrolet, Chrysler/Dodge/Jeep/RAM, Buick/GMC, VW, Subaru, Kia, Toyota, Mazda, MINI, Volvo = ~49 stores

A **Group Overview email to Anne Lewis** gates per-brand drafts — get her approval before sending individual brand emails.

**Tableau filter:** `vf_Maj%20Cust%20Name=Hendrick%20Automotive%20Group`

---

## Brand → Store Mapping

```yaml
BRAND_STORES:
  BMW:
    - {name: "BMW of Kansas City South",                   ccid: "5366219"}
    - {name: "BMW of McKinney",                            ccid: "6063497"}
    - {name: "BMW of Murrieta",                            ccid: "196006"}
    - {name: "BMW of South Austin",                        ccid: "5381948"}
    - {name: "BMW of Southpoint",                          ccid: "5366929"}
    - {name: "East Bay BMW",                               ccid: "25596"}
    - {name: "Hendrick BMW",                               ccid: "9842"}
    - {name: "Hendrick BMW Certified Pre-Owned South Charlotte", ccid: "6059705"}
    - {name: "Hendrick BMW Northlake",                     ccid: "2216817"}
    - {name: "Rick Hendrick BMW Charleston",               ccid: "10278"}

  Honda:
    - {name: "Barbour-Hendrick Honda Greenville",          ccid: "9672"}
    - {name: "Darrell Waltrip Honda",                      ccid: "5357864"}
    - {name: "Gwinnett Place Honda",                       ccid: "10596"}
    - {name: "Hendrick Honda",                             ccid: "113552"}
    - {name: "Hendrick Honda Bradenton",                   ccid: "12073"}
    - {name: "Hendrick Honda Hickory",                     ccid: "10023"}
    - {name: "Hendrick Honda of Charleston",               ccid: "113526"}
    - {name: "Hendrick Honda of Easley",                   ccid: "10406"}
    - {name: "Honda Cars of McKinney",                     ccid: "21589"}
    - {name: "Honda Cars of Rock Hill",                    ccid: "10452"}
    - {name: "Honda of Concord",                           ccid: "9835"}
    - {name: "Honda of Newnan",                            ccid: "5384840"}
    - {name: "Reggie Jackson Airport Honda",               ccid: "6035228"}
    - {name: "Rick Hendrick Honda",                        ccid: "6072155"}
    - {name: "Stevenson-Hendrick Honda Jacksonville",      ccid: "6061234"}
    - {name: "Stevenson-Hendrick Honda Wilmington",        ccid: "5381793"}

  Chevrolet:
    - {name: "Dale Earnhardt Jr. Chevrolet",               ccid: "11294"}
    - {name: "Hendrick Chevrolet",                         ccid: "6070622"}
    - {name: "Hendrick Chevrolet Shawnee Mission",         ccid: "81091"}
    - {name: "Rick Hendrick Chevrolet Charleston",         ccid: "148588"}
    - {name: "Rick Hendrick Chevrolet of Buford",          ccid: "195265"}
    - {name: "Rick Hendrick Chevrolet of Duluth",          ccid: "108102"}
    - {name: "Rick Hendrick City Chevrolet",               ccid: "81003"}
    - {name: "Terry Labonte Chevrolet",                    ccid: "9542"}

  Chrysler_CDJR:  # Chrysler/Dodge/Jeep/RAM combined bucket
    - {name: "Hendrick Chrysler Dodge Jeep RAM Hoover",    ccid: "205678"}
    - {name: "Hendrick Chrysler Dodge Jeep Ram FIAT of Concord", ccid: "209886"}
    - {name: "Hendrick Chrysler Jeep FIAT",                ccid: "192313"}
    - {name: "Rick Hendrick Chrysler Dodge Jeep RAM Duluth", ccid: "5366833"}
    - {name: "Rick Hendrick Dodge Chrysler Jeep RAM Charleston", ccid: "148592"}
    - {name: "Rick Hendrick Jeep Chrysler Dodge RAM North Charleston", ccid: "148664"}
    - {name: "Hendrick Dodge FIAT",                        ccid: "150456"}

  Buick_GMC:  # Buick/GMC combined
    - {name: "Dale Earnhardt Jr. Buick GMC Cadillac",      ccid: "111953"}
    - {name: "Darrell Waltrip Buick GMC",                  ccid: "5249931"}
    - {name: "Rick Hendrick Buick GMC",                    ccid: "10597"}
    - {name: "Rick Hendrick Chevrolet Buick GMC",          ccid: "151532"}

  Volkswagen:
    - {name: "Hendrick Volkswagen Frisco",                 ccid: "5351262"}
    - {name: "Hendrick Volkswagen of Concord",             ccid: "5342368"}
    - {name: "Volkswagen of Murrieta",                     ccid: "107802"}

  Acura:
    - {name: "Acura of Pleasanton",                        ccid: "5355806"}
    - {name: "Hendrick Acura",                             ccid: "9841"}

  Audi:
    - {name: "Audi Northlake",                             ccid: "5327599"}
    - {name: "Audi South Austin",                          ccid: "5333024"}

  Subaru:
    - {name: "Darrell Waltrip Subaru",                     ccid: "12648"}
    - {name: "Hendrick Subaru",                            ccid: "5385496"}

  Kia:
    - {name: "Hendrick Kia of Cary",                       ccid: "204337"}
    - {name: "Hendrick Kia of Concord",                    ccid: "5342363"}

  Lexus:
    - {name: "Hendrick Lexus Kansas City",                 ccid: "81127"}
    - {name: "Hendrick Lexus Kansas City North",           ccid: "107889"}

  MINI:
    - {name: "Hendrick MINI",                              ccid: "192698"}
    - {name: "Mall of Georgia MINI",                       ccid: "5358010"}

  Porsche:
    - {name: "Hendrick Porsche",                           ccid: "9843"}
    - {name: "Porsche Southpoint",                         ccid: "5363459"}

  Toyota:
    - {name: "Hendrick Toyota Merriam",                    ccid: "81081"}
    - {name: "Hendrick Toyota North Charleston",           ccid: "10284"}

  Mazda:
    - {name: "Mall of Georgia Mazda",                      ccid: "2172862"}
    - {name: "Stevenson Hendrick Mazda Wilmington",        ccid: "5389686"}

  Mercedes_Benz:
    - {name: "Mercedes-Benz of Durham",                    ccid: "5348859"}
    - {name: "Mercedes-Benz of Northlake",                 ccid: "2311989"}

  Volvo:
    - {name: "Hendrick Volvo Cars of Charleston",          ccid: "2439974"}

  Other:  # Multi-franchise or specialty — include in volume rotation
    - {name: "Hendrick INEOS Grenadier",                   ccid: "6070304"}
    - {name: "Hendrick Motors of Charlotte",               ccid: "195015"}
    - {name: "Hendrick Southpoint Auto Mall",              ccid: "9571"}
```

---

## Rotation Schedule

| Month | Rotation | Brands |
|---|---|---|
| Odd (Jan, Mar, May…) | **Luxury** | BMW (10), Acura (2), Audi (2), Lexus (2), Mercedes-Benz (2), Porsche (2) = **20 stores** |
| Even (Feb, Apr, Jun…) | **Volume** | Honda (16), Chevrolet (8), CDJR (7), Buick/GMC (4), VW (3), Subaru (2), Kia (2), Toyota (2), Mazda (2), MINI (2), Volvo (1), Other (3) = **52 stores** |

Override with user input at Step 0.

---

## Recipient Mapping

**Primary contact (all emails):** Anne Lewis — `anne.Lewis@hendrickauto.com`

**Brand managers** (TBD — confirm before first production run):

```yaml
RECIPIENTS:
  default_to: anne.Lewis@hendrickauto.com   # fallback until brand managers confirmed

  # Luxury brands
  BMW:           {to: [anne.Lewis@hendrickauto.com], cc: []}   # TBD brand manager
  Acura:         {to: [anne.Lewis@hendrickauto.com], cc: []}
  Audi:          {to: [anne.Lewis@hendrickauto.com], cc: []}
  Lexus:         {to: [anne.Lewis@hendrickauto.com], cc: []}
  Mercedes_Benz: {to: [anne.Lewis@hendrickauto.com], cc: []}
  Porsche:       {to: [anne.Lewis@hendrickauto.com], cc: []}

  # Volume brands
  Honda:         {to: [anne.Lewis@hendrickauto.com], cc: []}   # TBD brand manager
  Chevrolet:     {to: [anne.Lewis@hendrickauto.com], cc: []}
  Chrysler_CDJR: {to: [anne.Lewis@hendrickauto.com], cc: []}
  Buick_GMC:     {to: [anne.Lewis@hendrickauto.com], cc: []}
  Volkswagen:    {to: [anne.Lewis@hendrickauto.com], cc: []}
  Subaru:        {to: [anne.Lewis@hendrickauto.com], cc: []}
  Kia:           {to: [anne.Lewis@hendrickauto.com], cc: []}
  Toyota:        {to: [anne.Lewis@hendrickauto.com], cc: []}
  Mazda:         {to: [anne.Lewis@hendrickauto.com], cc: []}
  MINI:          {to: [anne.Lewis@hendrickauto.com], cc: []}
  Volvo:         {to: [anne.Lewis@hendrickauto.com], cc: []}
```

**Action required before first send:** Ask Anne for brand manager contacts at Hendrick HQ (same role as Sonic brand managers). Until confirmed, all drafts route to Anne only with `[TEST]` prefix.

---

## Email Drafting Rule

- **Always use HTML-formatted email** — `Content-Type: text/html`, base64url-encoded as RFC 2822 `raw` parameter. Never fall back to unformatted text.
- **Target length:** 200–350 words per brand email
- **Tone:** Professional-casual, data-first, action-oriented
- **Vary:** opening line, lead insight, callout phrasing
- **Close:** "Cheers, Jake"
- **Never:** use the same opener twice, skip the sheet link, be vague about stats

---

## Steps

### Step 0 — Determine Rotation & Month

Ask: **Which rotation — Luxury or Volume?**
- Luxury: BMW, Acura, Audi, Lexus, Mercedes-Benz, Porsche (20 stores)
- Volume: Honda, Chevrolet, CDJR, Buick/GMC, VW, Subaru, Kia, Toyota, Mazda, MINI, Volvo, Other (52 stores)

Confirm reporting month (default: prior calendar month).

---

### Step 1 — Salesforce Roster Validation

```sql
SELECT Name, CCID__c, BillingCity, BillingState, Account_Status__c, Type
FROM Account
WHERE Parent.Name LIKE '%Hendrick%'
ORDER BY Name
```

Then pull active subscriptions:
```sql
SELECT SBQQ__Account__r.Name, SBQQ__Account__r.CCID__c,
       SBQQ__ProductName__c, SBQQ__NetPrice__c
FROM SBQQ__Subscription__c
WHERE SBQQ__Account__r.Parent.Name LIKE '%Hendrick%'
AND SBQQ__SubscriptionEndDate__c > TODAY
```

Flag: stores added/dropped, minimal packages (upsell candidates), SF/billing mismatches.

---

### Step 2 — Tableau Health Metrics

Pull from By Store view via REST API:

```bash
TOKEN=$(curl -s -X POST "https://us-west-2b.online.tableau.com/api/3.22/auth/signin" \
  -H "Content-Type: application/json" \
  -d '{"credentials":{"personalAccessTokenName":"Claude","personalAccessTokenSecret":"'$TABLEAU_PAT_SECRET'","site":{"contentUrl":"cars"}}}' \
  | python3 -c "import sys,json; body=sys.stdin.read(); \
    import xml.etree.ElementTree as ET; root=ET.fromstring(body); \
    creds=root.find('{http://tableau.com/api}credentials') or root.find('credentials'); \
    print(creds.attrib['token'])")

curl -s "https://us-west-2b.online.tableau.com/api/3.22/sites/12338861-20b1-46ed-8841-269a5a937edb/views/a0b9bdce-2db3-4ea0-a2fc-365fd08c5786/data?vf_Maj%20Cust%20Name=Hendrick%20Automotive%20Group" \
  -H "X-Tableau-Auth: $TOKEN" > hendrick_health_metrics.csv
```

**Do NOT send `Accept: text/csv` header** — returns 406.

Pivot long→wide format:
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
            'Maj Cust Name': row.get('Maj Cust Name',''),
        }
    stores[name][row['Measure Names'].strip()] = row['Measure Values']
stores_list = list(stores.values())
```

**Returns 48 metrics per store** (CP/PP/Delta): VDPs, Connections, Avg Daily Vehicles, Cost/Lead, Avg Daily Rating, Minimally Merchandised %, etc.

---

### Step 3 — admin.cars.com Data (Flagged Stores Only)

Requires active JumpCloud SSO session. Prompt user to confirm before proceeding.

For top 3–5 flagged stores per brand (from Step 5):

**3a. Performance Trends** — `https://admin.cars.com/dealers/{UUID}/reports/performance_trends`
- Capture: Avg Inventory, Under-Merchandised %, Connections, VDPs, Fair/Above Badge %

**3b. Demand Signals** — `https://admin.cars.com/dealers/{UUID}/reports/demand_signals`
- Download Market Comparison crosstab (CSV)
- Compute Share Index / Quadrant per `/dealer-marketshareanalysis` methodology

---

### Step 4 — Market Demand Context

Per-store Market DI:
```
Store Market DI = Store VDP Share of DMA ÷ Store Inventory Share of DMA
% to Market = (DI − 1) × 100
```

Brand-level rollup uses per-DMA aggregation to avoid double-counting shared markets (same as Sonic).

Fallback to Portfolio DI (Hendrick group avg) when admin data unavailable — label explicitly as **"Internal benchmark (vs Hendrick group avg)"**.

---

### Step 5 — Store Scoring & Flagging

Use `investigation_triggers.py`:

```python
import sys, os
sys.path.insert(0, os.path.expanduser("~/Documents/scripts"))
from investigation_triggers import investigate_stores, format_triage_report

brand_results = investigate_stores(brand_stores)
print(format_triage_report(brand_results, title=f"Hendrick {brand} — {month} {year}"))
```

Flag assignment:
```python
flagged_stores = [e["store"] for e in brand_results["high"][:5]]
if len(flagged_stores) < 3:
    flagged_stores += [e["store"] for e in brand_results["medium"][:3 - len(flagged_stores)]]
bright_spot_stores = [e["store"] for e in brand_results["bright_spots"][:3]]
```

Opportunity score: 30pts per HIGH flag + 15pts per MEDIUM, capped at 100.

---

### Step 5b — Per-Brand Rollup

| Field | Computation |
|---|---|
| Store Count | # stores in rotation |
| Total VDPs | Sum across brand stores |
| VDP MoM% | Brand total vs prior month |
| Total Connections | Sum across brand stores |
| Connections MoM% | Brand total vs prior month |
| % to Market | `(Brand Market DI − 1) × 100` |
| DI Source | "Market" or "Internal benchmark" |
| Investigation Flags | `{HIGH}/M {MED}` |
| Top Opportunity | highest-score flagged store |
| Top Bright Spot | first bright spot |

Sort brands by % to Market descending.

---

### Step 6 — Auto-Research Deep Dive (Flagged Stores)

For each flagged store, lead with scenario flags from Step 5:
- S1 flag → Historical Connections + Low Engaged Inventory
- S3 flag → Performance Trends SRP/VDP split + Demand Signals
- S4 flag → Demand Signals + Market Area Planner
- S5 flag → Cost/Lead vs. Competitive Set

Per-store insight (2–3 sentences): what's happening → revenue impact → specific next step.

---

### Step 6.5 — Group Overview Email to Anne (Verification Gate)

**Send BEFORE any per-brand drafts.** Per-brand drafting gated on Anne's approval.

**To:** anne.Lewis@hendrickauto.com
**Subject:** `Hendrick — {Month} {Year} Overview | Pre-Send Review`

```html
<p>Anne,</p>
<p>Pre-send review for {Month} {Year} — {brand_count} brands / {store_count} stores in this rotation.
Per-brand drafts are ready pending your sign-off.</p>

<h3>Portfolio Pulse — {Month} {Year}</h3>
<p>{total_stores} stores · {total_VDPs} VDPs ({VDP_MoM%} MoM) · {total_connections} Connections ({Conn_MoM%} MoM)</p>

<h3>Brand Scorecard</h3>
<table>
  <!-- Brand | Stores | VDPs | VDP MoM% | Connections | Conn MoM% | % to Market | Flags | Top Opportunity -->
  <!-- Sorted by % to Market descending -->
  <!-- Color: % to Market heatmap green>0, red<0; MoM% green/red -->
</table>

<h3>Headline Read</h3>
<ul>
  <li><strong>Biggest story:</strong> {brand driving or dragging this month}</li>
  <li><strong>Top ROI lever:</strong> {brand with most HIGH flags × avg demand gap}</li>
</ul>

<p>Please reply <strong>approved</strong>, <strong>changes requested</strong>, or specific edits.
Once approved I'll finalize the {brand_count} per-brand drafts.</p>

<p>Cheers,<br>Jake</p>
```

**Gate logic:**
- Approved → Step 7
- Changes requested → apply, resend, loop
- No reply 48h → ping once; do NOT auto-proceed

**Test-run phase** (until brand manager contacts confirmed):
- All per-brand drafts route **To: anne.Lewis@hendrickauto.com** with `[TEST]` prefix
- Remove `[TEST]` once brand managers identified

---

### Step 7 — Compose Brand Emails

For each brand in rotation:

**Subject (test run):** `[TEST] Hendrick {Brand} — Monthly Performance Update | {Month} {Year}`
**Subject (production):** `Hendrick {Brand} — Monthly Performance Update | {Month} {Year}`
**To:** Brand manager (from recipient mapping; route to Anne during test run)
**CC:** anne.Lewis@hendrickauto.com (when primary = brand manager)

```html
<h3>{Brand} — {Store count} stores, {Month} {Year}</h3>
<p>
  Market capture: <strong>{±X%} to market</strong> · VDPs {±X%} MoM · Connections {±X%} MoM<br>
  <strong>Top story:</strong> {one-line headline}
</p>

<h3>Store Scorecard</h3>
<table>
  <!-- Sorted by opportunity score descending -->
  <!-- Store | VDPs | MoM | Connections | MoM | Cost/Lead | Badge % | Flags | Signal -->
  <!-- Green MoM = positive, red = negative; bold flagged stores -->
</table>

<h3>Top Opportunities</h3>
<ol>
  <li><strong>{Store}</strong> — {scenario insight}<br>
      <em>Action: {specific recommendation}</em></li>
</ol>

<h3>Bright Spots</h3>
<ul>
  <li><strong>{Store}</strong> — {what's working}</li>
</ul>

<p><a href="{Google Sheet URL}">Full data in the Hendrick Monthly Performance sheet</a></p>
<p>Cheers,<br>Jake</p>
```

---

### Step 8 — Google Sheet Update

Create or update **"Hendrick Monthly Performance — {Year}"**:

**Tab: "{Month} Overview"** — group-level dashboard
- Columns: Brand, Stores, Total VDPs, VDP MoM%, Total Connections, Conn MoM%, % to Market, DI Source, Flags, Top Opportunity, Top Bright Spot
- Header: Poppins 11, bold white on `#6a0dad` purple
- Heatmap: % to Market (red −25% → yellow 0% → green +25%)

**Tab: "{Month} - {Brand} Summary"** — one per brand
- All stores with full metrics from Steps 2–3
- Columns: Store, CCID, VDPs (CP/PP), VDP MoM%, Connections (CP/PP), Conn MoM%, Cost/Lead, Avg Inventory, Badge %, Opportunity Score, Flags, Signal
- Poppins font, purple headers (`#6a0dad`), banded rows

**Tab: "Brand Overview"** — rolling across months
- One row per brand per month; sorted month desc, brand alpha

**Tab: "Store Flags"** — rolling flag log
- Month, Store, Brand, Score, Flag Reason, Action Taken (manual fill)

Use gspread with `~/.claude/tokens/sheets_credentials.json`.

---

### Step 9 — QC

- [ ] Store counts match expected roster per brand
- [ ] No all-zero metrics (data pull failure)
- [ ] Any store >30% MoM swing — verify not artifact
- [ ] All flagged stores have investigation insights
- [ ] Email length 200–350 words per brand
- [ ] Sheet formatting correct (Poppins, purple headers, conditional colors)
- [ ] Sheet link in email body is correct
- [ ] Group Overview sent and Anne's approval recorded
- [ ] DI Source consistent across Sheet + per-brand emails
- [ ] Test run: all drafts To: anne.Lewis@hendrickauto.com with `[TEST]` prefix

---

### Step 10 — Gmail Drafts

For each brand email:
1. Compose HTML body per Step 7 template
2. Create Gmail draft via Gmail MCP — **draft only, never send**
3. Confirm draft created and report subject + recipient

Fallback: save HTML to `~/Documents/Reports/HendrickAutomotive/hendrick_{brand}_{month}_{year}.html`

---

## Key Reference

- **Parent Group:** Hendrick Automotive Group (CCID: 546973)
- **~72 active stores** across 19 brands
- **Primary contact:** Anne Lewis (anne.Lewis@hendrickauto.com) — all emails, verification gate
- **Tableau workbook:** Cars Monthly Marketplace Dealer Health Metrics (ID: 1792343)
- **Tableau filter:** `vf_Maj%20Cust%20Name=Hendrick%20Automotive%20Group`
- **investigation_triggers:** `~/Documents/scripts/investigation_triggers.py`
- **Report folder:** `~/Documents/Reports/HendrickAutomotive/`
- **gspread token:** `~/.claude/tokens/sheets_credentials.json`
- **Related skills:** `/sonic-monthly-report` (template), `/investigate-stores`, `/auto-research`
- **Schedule:** Monthly, manually triggered

## Luxury Rotation Brands
BMW (10), Acura (2), Audi (2), Lexus (2), Mercedes-Benz (2), Porsche (2) = **20 stores**

## Volume Rotation Brands
Honda (16), Chevrolet (8), CDJR/7, Buick/GMC (4), VW (3), Subaru (2), Kia (2), Toyota (2), Mazda (2), MINI (2), Volvo (1), Other (3) = **52 stores**
