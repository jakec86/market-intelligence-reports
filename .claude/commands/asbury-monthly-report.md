# Asbury Group Monthly Performance Report — Monthly Workflow

Run the monthly Asbury umbrella report covering all 4 sub-groups and 149 stores. Produces a Group Overview verification email + one per-sub-group email draft per month. No rotation — all sub-groups run every month.

---

## Overview

The Asbury umbrella covers 4 sub-groups with a combined **149 active stores**:

| Sub-Group | Stores | Tableau Filter |
|---|---|---|
| Asbury | 69 | `vf_Maj%20Cust%20Name=Asbury` |
| Larry H. Miller (LHM) | 29 | `vf_Maj%20Cust%20Name=Larry%20Miller` |
| Koons | 18 | `vf_Maj%20Cust%20Name=Koons%20Automotive%20MA%20Group` |
| Herb Chambers | 33 | `vf_Maj%20Cust%20Name=Herb%20Chambers%20MA%20Group` |

**No rotation** — all 4 sub-groups run every month.

**Verification gate (Step 6.5):** BEFORE per-sub-group drafts are composed, a **Group Overview email** goes to the primary contact for verification. Per-sub-group drafting (Step 7) is gated on sign-off.

**Google Sheet:** TBD — create on first run, save ID to memory.
**Report folder:** `~/Documents/Reports/AsburyGroup/`

---

## Sub-Group → Store Mapping

```yaml
SUB_GROUPS:

  Asbury:
    tableau_filter: "vf_Maj%20Cust%20Name=Asbury"
    stores:
      - {name: "Arapahoe Hyundai",                         ccid: "6001244"}
      - {name: "Audi North Atlanta",                        ccid: "149346"}
      - {name: "Bentley Atlanta",                           ccid: "5333020"}
      - {name: "Bill Estes Ford",                           ccid: "5385979"}
      - {name: "Bill Estes Toyota",                         ccid: "5388870"}
      - {name: "Coggin Acura",                              ccid: "12212"}
      - {name: "Coggin BMW of Treasure Coast",              ccid: "184619"}
      - {name: "Coggin Buick GMC",                          ccid: "147828"}
      - {name: "Coggin DeLand Hyundai",                     ccid: "5335322"}
      - {name: "Coggin Deland Ford",                        ccid: "2365855"}
      - {name: "Coggin Deland Honda",                       ccid: "11415"}
      - {name: "Coggin Ford of Jacksonville",               ccid: "5357591"}
      - {name: "Coggin Honda Jacksonville",                 ccid: "11257"}
      - {name: "Coggin Honda of Fort Pierce",               ccid: "12200"}
      - {name: "Coggin Honda of Orlando",                   ccid: "11504"}
      - {name: "Coggin Honda of St. Augustine",             ccid: "11187"}
      - {name: "Coggin Nissan at the Avenues",              ccid: "113820"}
      - {name: "Coggin Nissan on Atlantic",                 ccid: "11258"}
      - {name: "Courtesy Chrysler Jeep Dodge RAM of Tampa", ccid: "107418"}
      - {name: "Courtesy Hyundai Tampa",                    ccid: "2324012"}
      - {name: "Courtesy Kia of Brandon",                   ccid: "147191"}
      - {name: "Courtesy Nissan of Tampa",                  ccid: "112766"}
      - {name: "Courtesy Palm Harbor Honda",                ccid: "109973"}
      - {name: "Crown Acura Richmond",                      ccid: "8875"}
      - {name: "Crown MINI of Richmond",                    ccid: "5357740"}
      - {name: "Crown Nissan of Greenville",                ccid: "106594"}
      - {name: "David McDavid Honda Irving",                ccid: "21562"}
      - {name: "David McDavid Honda of Frisco",             ccid: "108308"}
      - {name: "David McDavid Lincoln Frisco",              ccid: "21595"}
      - {name: "Hare Chevrolet",                            ccid: "80398"}
      - {name: "Hare Honda",                                ccid: "5378816"}
      - {name: "Herb Chambers Maserati of Millbury (Asbury)", ccid: "6070367"}
      - {name: "Herb Chambers Maserati of Warwick (Asbury)", ccid: "6070366"}
      - {name: "INFINITI of Tampa",                         ccid: "147204"}
      - {name: "Jaguar Lakewood",                           ccid: "6050828"}
      - {name: "Maserati Boston",                           ccid: "6070368"}
      - {name: "McDavid Ford",                              ccid: "2478883"}
      - {name: "Mercedes-Benz Of Tampa",                    ccid: "147205"}
      - {name: "Mercedes-Benz of Ft. Pierce",               ccid: "147106"}
      - {name: "Mike Shaw Subaru",                          ccid: "5390082"}
      - {name: "Mike Shaw Subaru Greeley",                  ccid: "6000501"}
      - {name: "Nalley Acura",                              ccid: "10538"}
      - {name: "Nalley BMW of Decatur",                     ccid: "109749"}
      - {name: "Nalley Honda",                              ccid: "10702"}
      - {name: "Nalley Hyundai",                            ccid: "5243635"}
      - {name: "Nalley INFINITI Marietta",                  ccid: "10539"}
      - {name: "Nalley INFINITI of Atlanta",                ccid: "149127"}
      - {name: "Nalley Kia",                                ccid: "5243639"}
      - {name: "Nalley Lexus Galleria",                     ccid: "109754"}
      - {name: "Nalley Lexus Roswell",                      ccid: "107891"}
      - {name: "Nalley Toyota of Roswell",                  ccid: "109056"}
      - {name: "Nalley Volkswagen",                         ccid: "109560"}
      - {name: "Park Place Acura",                          ccid: "21616"}
      - {name: "Park Place Lexus Grapevine",                ccid: "5394899"}
      - {name: "Park Place Lexus Plano",                    ccid: "5394900"}
      - {name: "Park Place Motorcars Arlington",            ccid: "5394924"}
      - {name: "Park Place Motorcars Dallas",               ccid: "5394925"}
      - {name: "Park Place Motorcars Fort Worth",           ccid: "5394926"}
      - {name: "Park Place Volvo Cars",                     ccid: "5394902"}
      - {name: "Porsche Dallas",                            ccid: "5394901"}
      - {name: "Porsche Littleton",                         ccid: "6050774"}
      - {name: "Richmond BMW",                              ccid: "182761"}
      - {name: "Richmond BMW Midlothian",                   ccid: "183110"}
      - {name: "Stevinson Chevrolet",                       ccid: "6050758"}
      - {name: "Stevinson Hyundai of Frederick",            ccid: "6050773"}
      - {name: "Stevinson Lexus of Frederick",              ccid: "6050756"}
      - {name: "Stevinson Lexus of Lakewood",               ccid: "6050744"}
      - {name: "Stevinson Toyota West",                     ccid: "6050775"}
      - {name: "Toyota of Greenville",                      ccid: "10366"}

  LHM:  # Larry H. Miller
    tableau_filter: "vf_Maj%20Cust%20Name=Larry%20Miller"
    stores:
      - {name: "Genesis of Peoria",                                    ccid: "6000301"}
      - {name: "Larry H. Miller American Toyota",                      ccid: "23933"}
      - {name: "Larry H. Miller Casa Chevrolet",                       ccid: "5392260"}
      - {name: "Larry H. Miller Casa Chrysler Jeep",                   ccid: "5392265"}
      - {name: "Larry H. Miller Chrysler Dodge Jeep Ram 104th",        ccid: "23066"}
      - {name: "Larry H. Miller Chrysler Jeep Dodge RAM Boise",        ccid: "23461"}
      - {name: "Larry H. Miller Chrysler Jeep Dodge RAM Surprise",     ccid: "2492193"}
      - {name: "Larry H. Miller Chrysler Jeep Dodge Ram Albuquerque",  ccid: "196483"}
      - {name: "Larry H. Miller Chrysler Jeep Tucson",                 ccid: "99872"}
      - {name: "Larry H. Miller Colorado Jeep",                        ccid: "22976"}
      - {name: "Larry H. Miller Dodge RAM Peoria",                     ccid: "80230"}
      - {name: "Larry H. Miller Dodge Ram Avondale",                   ccid: "2572943"}
      - {name: "Larry H. Miller Dodge Ram FIAT Tucson",                ccid: "84355"}
      - {name: "Larry H. Miller Ford Draper",                          ccid: "23527"}
      - {name: "Larry H. Miller Ford Lakewood",                        ccid: "23047"}
      - {name: "Larry H. Miller Ford Mesa",                            ccid: "5386490"}
      - {name: "Larry H. Miller Honda Boise",                          ccid: "23457"}
      - {name: "Larry H. Miller Honda Murray",                         ccid: "23555"}
      - {name: "Larry H. Miller Hyundai Albuquerque",                  ccid: "150111"}
      - {name: "Larry H. Miller Hyundai Peoria",                       ccid: "193011"}
      - {name: "Larry H. Miller Nissan Mesa",                          ccid: "80276"}
      - {name: "Larry H. Miller Southwest Hyundai",                    ccid: "150012"}
      - {name: "Larry H. Miller Subaru Boise",                         ccid: "84182"}
      - {name: "Larry H. Miller Super Ford Salt Lake City",            ccid: "113131"}
      - {name: "Larry H. Miller Toyota Peoria",                        ccid: "80232"}
      - {name: "Larry H. Miller Volkswagen Avondale",                  ccid: "108290"}
      - {name: "Larry H. Miller Volkswagen Lakewood",                  ccid: "108090"}
      - {name: "Larry H. Miller Volkswagen Tucson",                    ccid: "2255409"}
      - {name: "Mercedes-Benz of Draper",                              ccid: "6051042"}

  Koons:
    tableau_filter: "vf_Maj%20Cust%20Name=Koons%20Automotive%20MA%20Group"
    stores:
      - {name: "Koons Annapolis Toyota",              ccid: "8489"}
      - {name: "Koons Arlington Toyota",              ccid: "2653"}
      - {name: "Koons Chevrolet of White Marsh",      ccid: "8439"}
      - {name: "Koons Clarksville Chevy GMC",         ccid: "5384915"}
      - {name: "Koons Ford of Baltimore",             ccid: "8476"}
      - {name: "Koons Kia",                           ccid: "194425"}
      - {name: "Koons Kia Owings Mills",              ccid: "5397936"}
      - {name: "Koons Sterling Ford",                 ccid: "2459"}
      - {name: "Koons Toyota Of Westminster",         ccid: "8422"}
      - {name: "Koons Tysons Chrysler Dodge Jeep RAM", ccid: "2419"}
      - {name: "Koons Tysons Toyota",                 ccid: "2451"}
      - {name: "Koons Volvo Cars White Marsh",        ccid: "8405"}
      - {name: "Koons Woodbridge Buick GMC",          ccid: "5396946"}
      - {name: "Koons Woodbridge Ford",               ccid: "6000459"}
      - {name: "Koons Woodbridge Hyundai",            ccid: "5392269"}
      - {name: "Koons of Falls Church Ford",          ccid: "2456"}
      - {name: "Koons of Tysons Chevrolet GMC",       ccid: "2453"}
      - {name: "Mercedes-Benz of Catonsville",        ccid: "197344"}

  Herb_Chambers:
    tableau_filter: "vf_Maj%20Cust%20Name=Herb%20Chambers%20MA%20Group"
    stores:
      - {name: "Audi Brookline",                                        ccid: "5343560"}
      - {name: "Audi Burlington",                                       ccid: "3205"}
      - {name: "BMW Certified Pre-Owned Medford A Herb Chambers Company", ccid: "6000779"}
      - {name: "Bentley Boston",                                        ccid: "6036793"}
      - {name: "Flagship Motorcars of Lynnfield",                       ccid: "27153"}
      - {name: "Herb Chambers Alfa Romeo of Boston",                    ccid: "5373020"}
      - {name: "Herb Chambers BMW MINI of Boston",                      ccid: "3111"}
      - {name: "Herb Chambers BMW of Sudbury",                          ccid: "196465"}
      - {name: "Herb Chambers Cadillac of Lynnfield",                   ccid: "5243150"}
      - {name: "Herb Chambers Cadillac of Warwick",                     ccid: "81741"}
      - {name: "Herb Chambers Chevrolet of Danvers",                    ccid: "156476"}
      - {name: "Herb Chambers Chrysler Dodge Jeep RAM FIAT of Danvers", ccid: "99392"}
      - {name: "Herb Chambers Chrysler Dodge Jeep RAM FIAT of Millbury", ccid: "3123"}
      - {name: "Herb Chambers Exotics",                                 ccid: "159284"}
      - {name: "Herb Chambers Ford of Braintree",                       ccid: "81773"}
      - {name: "Herb Chambers Ford of Westborough",                     ccid: "3138"}
      - {name: "Herb Chambers Honda",                                   ccid: "3349"}
      - {name: "Herb Chambers Honda of Burlington",                     ccid: "3204"}
      - {name: "Herb Chambers Honda of Seekonk",                        ccid: "3544"}
      - {name: "Herb Chambers Hyundai of Auburn",                       ccid: "3112"}
      - {name: "Herb Chambers Kia",                                     ccid: "198442"}
      - {name: "Herb Chambers Lexus of Hingham",                        ccid: "5243175"}
      - {name: "Herb Chambers Lexus of Sharon",                         ccid: "3304"}
      - {name: "Herb Chambers Lincoln of Norwood",                      ccid: "5354177"}
      - {name: "Herb Chambers Lincoln of Westborough",                  ccid: "6062473"}
      - {name: "Herb Chambers Porsche",                                 ccid: "178854"}
      - {name: "Herb Chambers Toyota of Auburn",                        ccid: "99374"}
      - {name: "Herb Chambers Toyota of Boston",                        ccid: "99373"}
      - {name: "Herb Chambers Volvo Cars Norwood",                      ccid: "3299"}
      - {name: "Jaguar Land Rover Boston",                              ccid: "5397676"}
      - {name: "Jaguar Land Rover Sudbury",                             ccid: "3194"}
      - {name: "Mercedes-Benz of Sudbury",                              ccid: "98282"}
      - {name: "Porsche Burlington",                                    ccid: "5373653"}
```

---

## Recipient Mapping

All sub-group emails currently route to **Sharon Cunane** (EAE) until per-sub-group client contacts are confirmed. Sharon acts as the verification gate across all four groups.

```yaml
RECIPIENTS:
  # ── UMBRELLA OVERVIEW EMAIL ────────────────────────────────────────────────
  overview_to:   scunane@cars.com   # Sharon Cunane — EAE, all sub-groups
  overview_cc:   []

  # ── PER-SUB-GROUP EMAILS ───────────────────────────────────────────────────
  Asbury:
    to:   [scunane@cars.com]   # TBD client contact → Sharon until confirmed
    cc:   []

  LHM:
    to:   [scunane@cars.com]   # TBD client contact → Sharon until confirmed
    cc:   []

  Koons:
    to:   [scunane@cars.com]   # TBD client contact → Sharon until confirmed
    cc:   []

  Herb_Chambers:
    to:   [scunane@cars.com]   # TBD client contact → Sharon until confirmed
    cc:   []
```

**When client contacts are identified:** swap `scunane@cars.com` per sub-group and add Sharon to `cc:` instead.

---

## Email Drafting Rule

- **Always use HTML-formatted email** — `Content-Type: text/html`, base64url-encoded as RFC 2822 `raw` parameter. Never fall back to unformatted text.
- **Target length:** 250–400 words per sub-group email
- **Tone:** Professional-casual, data-first, action-oriented
- **Vary:** opening line, lead insight, callout phrasing
- **Close:** "Cheers, Jake"
- **Never:** use the same opener twice, skip the sheet link, be vague about stats

---

## Steps

### Step 0 — Confirm Month

Confirm the reporting month (default: prior calendar month). No rotation selection needed — all 4 sub-groups run every month.

Display planned scope:
```
Month: {Month} {Year}
Sub-groups: Asbury (69) · LHM (29) · Koons (18) · Herb Chambers (33) = 149 stores total
```

---

### Step 1 — Salesforce Roster Validation

Query SF to validate active stores across all 4 sub-groups:

```sql
SELECT Name, CCID__c, BillingCity, BillingState, Account_Status__c, Type
FROM Account
WHERE (Parent.Name LIKE '%Asbury%'
   OR Parent.Name LIKE '%Larry%Miller%'
   OR Parent.Name LIKE '%Koons%'
   OR Parent.Name LIKE '%Herb%Chambers%')
ORDER BY Parent.Name, Name
```

Then pull active subscriptions:
```sql
SELECT SBQQ__Account__r.Name, SBQQ__Account__r.CCID__c,
       SBQQ__ProductName__c, SBQQ__NetPrice__c
FROM SBQQ__Subscription__c
WHERE (SBQQ__Account__r.Parent.Name LIKE '%Asbury%'
    OR SBQQ__Account__r.Parent.Name LIKE '%Larry%Miller%'
    OR SBQQ__Account__r.Parent.Name LIKE '%Koons%'
    OR SBQQ__Account__r.Parent.Name LIKE '%Herb%Chambers%')
AND SBQQ__SubscriptionEndDate__c > TODAY
```

**Important:** Use `SBQQ__Subscription__c` for actual products — `Account_Status__c` can be stale.

Flag per sub-group:
- Stores added or dropped since last month
- Stores with minimal product packages (upsell candidates)
- SF/billing mismatches

---

### Step 2 — Tableau Health Metrics

Pull each sub-group separately using the Tableau REST API. Run all 4 pulls sequentially, then combine.

```bash
TOKEN=$(curl -s -X POST "https://us-west-2b.online.tableau.com/api/3.22/auth/signin" \
  -H "Content-Type: application/json" \
  -d '{"credentials":{"personalAccessTokenName":"Claude","personalAccessTokenSecret":"'$TABLEAU_PAT_SECRET'","site":{"contentUrl":"cars"}}}' \
  | python3 -c "import sys,json; body=sys.stdin.read(); \
    import xml.etree.ElementTree as ET; root=ET.fromstring(body); \
    creds=root.find('{http://tableau.com/api}credentials') or root.find('credentials'); \
    print(creds.attrib['token'])")

# Pull each sub-group — store outputs separately for per-sub-group rollup
curl -s "https://us-west-2b.online.tableau.com/api/3.22/sites/12338861-20b1-46ed-8841-269a5a937edb/views/a0b9bdce-2db3-4ea0-a2fc-365fd08c5786/data?vf_Maj%20Cust%20Name=Asbury" \
  -H "X-Tableau-Auth: $TOKEN" > asbury_health_metrics.csv

curl -s "https://us-west-2b.online.tableau.com/api/3.22/sites/12338861-20b1-46ed-8841-269a5a937edb/views/a0b9bdce-2db3-4ea0-a2fc-365fd08c5786/data?vf_Maj%20Cust%20Name=Larry%20Miller" \
  -H "X-Tableau-Auth: $TOKEN" > lhm_health_metrics.csv

curl -s "https://us-west-2b.online.tableau.com/api/3.22/sites/12338861-20b1-46ed-8841-269a5a937edb/views/a0b9bdce-2db3-4ea0-a2fc-365fd08c5786/data?vf_Maj%20Cust%20Name=Koons%20Automotive%20MA%20Group" \
  -H "X-Tableau-Auth: $TOKEN" > koons_health_metrics.csv

curl -s "https://us-west-2b.online.tableau.com/api/3.22/sites/12338861-20b1-46ed-8841-269a5a937edb/views/a0b9bdce-2db3-4ea0-a2fc-365fd08c5786/data?vf_Maj%20Cust%20Name=Herb%20Chambers%20MA%20Group" \
  -H "X-Tableau-Auth: $TOKEN" > herb_chambers_health_metrics.csv
```

**Do NOT send `Accept: text/csv` header** — returns 406.

Pivot long→wide per sub-group:
```python
import csv, io, sys, os
sys.path.insert(0, os.path.expanduser("~/Documents/scripts"))

def pivot_csv(raw_csv):
    stores = {}
    for row in csv.DictReader(io.StringIO(raw_csv)):
        name = row['Customer Name']
        if name not in stores:
            stores[name] = {
                'Customer Name': name,
                'Legacy Id': row['Legacy Id'],
                'Maj Cust Name': row.get('Maj Cust Name', ''),
            }
        stores[name][row['Measure Names'].strip()] = row['Measure Values']
    return list(stores.values())
```

**Returns 48 metrics per store** (CP/PP/Delta): VDPs, Connections, Avg Daily Vehicles, Cost/Lead, Avg Daily Rating, Minimally Merchandised %, etc.

---

### Step 3 — admin.cars.com Data (Flagged Stores Only)

Requires active JumpCloud SSO session. Prompt user to confirm before proceeding.

For the top 3–5 flagged stores per sub-group (from Step 5):

**3a. Performance Trends** — `https://admin.cars.com/dealers/{UUID}/reports/performance_trends`
- Capture: Avg Inventory, Under-Merchandised %, Connections, VDPs, Fair/Above Badge %
- Discover UUIDs via: `https://admin.cars.com/dealers/all/reports?query={store_name_or_ccid}`

**3b. Demand Signals** — `https://admin.cars.com/dealers/{UUID}/reports/demand_signals`
- Download Market Comparison crosstab (CSV)
- Compute Share Index / Quadrant per `/dealer-marketshareanalysis` methodology:
  - VDP Index = VDP Share % / Vehicle Share %
  - Connection Index = Connections Share % / Vehicle Share %
  - Share Index = (VDP Index × 0.4) + (Connection Index × 0.6)
  - Quadrant: Churner / Lot Sitter / Rarity / Niche (median split)

---

### Step 4 — Market Demand Context

Per-store Market DI:
```
Store Market DI = Store VDP Share of DMA ÷ Store Inventory Share of DMA
% to Market = (DI − 1) × 100
```

Sub-group-level rollup uses per-DMA aggregation to avoid double-counting shared markets. When multiple stores in the same sub-group share a DMA, count the market denominator once per DMA:

```
For each DMA where the sub-group has ≥1 store:
    subgroup_dma_vdps      = Σ dealer VDPs for sub-group stores in that DMA
    subgroup_dma_inventory = Σ dealer inventory for sub-group stores in that DMA
    market_dma_vdps        = total market VDPs in that DMA (counted once)
    market_dma_inventory   = total market inventory in that DMA (counted once)

Sub-group Market DI = (Σ subgroup_dma_vdps / Σ market_dma_vdps)
                    ÷ (Σ subgroup_dma_inventory / Σ market_dma_inventory)
```

Fallback to Portfolio DI (Asbury umbrella avg) when admin data unavailable — label explicitly as **"Internal benchmark (vs Asbury umbrella avg)"**.

---

### Step 5 — Store Scoring & Flagging

Use `investigation_triggers.py` for all stores. Run per sub-group:

```python
import sys, os
sys.path.insert(0, os.path.expanduser("~/Documents/scripts"))
from investigation_triggers import investigate_stores, format_triage_report

# Run for each sub-group
for subgroup_name, subgroup_stores in all_subgroups.items():
    results = investigate_stores(subgroup_stores)
    print(format_triage_report(results,
                               title=f"{subgroup_name} — {month} {year}",
                               show_sams=False))  # No SAM data for Asbury yet
```

Flag assignment per sub-group:
```python
flagged_stores = [e["store"] for e in results["high"][:5]]
if len(flagged_stores) < 3:
    flagged_stores += [e["store"] for e in results["medium"][:3 - len(flagged_stores)]]
bright_spot_stores = [e["store"] for e in results["bright_spots"][:3]]
```

Opportunity score: 30pts per HIGH flag + 15pts per MEDIUM, capped at 100.

---

### Step 5b — Per-Sub-Group Rollup

Build one summary row per sub-group (feeds Step 6.5 Group Overview):

| Field | Computation |
|---|---|
| Store Count | # stores in sub-group |
| Total VDPs | Sum across sub-group stores |
| VDP MoM% | Sub-group total vs prior month |
| Total Connections | Sum across sub-group stores |
| Connections MoM% | Sub-group total vs prior month |
| % to Market | `(Sub-group Market DI − 1) × 100` |
| DI Source | "Market" or "Internal benchmark" |
| Investigation Flags | `{HIGH} HIGH / {MED} MEDIUM` |
| Top Opportunity | highest-score flagged store |
| Top Bright Spot | first bright spot store |

Sort sub-groups by % to Market descending in the overview.

---

### Step 6 — Auto-Research Deep Dive (Flagged Stores)

For each flagged store, lead with scenario flags from Step 5:
- S1 flag → Historical Connections + Low Engaged Inventory
- S2 flag → Merchandising %, Best Match audit
- S3 flag → Performance Trends SRP/VDP split + Demand Signals
- S4 flag → Demand Signals + Market Area Planner
- S5 flag → Cost/Lead vs. Competitive Set

Per-store insight (2–3 sentences): what's happening → revenue impact → specific next step.

---

### Step 6.5 — Umbrella Overview Email (Verification Gate)

**Send BEFORE any per-sub-group drafts.** Per-sub-group drafting is gated on sign-off.

**Subject:** `Asbury Group — {Month} {Year} Overview | Pre-Send Review`

**To:** scunane@cars.com (Sharon Cunane — EAE)
**CC:** (none)

```html
<p>[Contact name],</p>
<p>Pre-send review for {Month} {Year} — 4 sub-groups / 149 stores.
Per-sub-group drafts are ready pending your sign-off.</p>

<h3>Portfolio Pulse — {Month} {Year}</h3>
<p>
  149 stores · {total_VDPs} VDPs ({VDP_MoM%} MoM) · {total_connections} Connections ({Conn_MoM%} MoM)
</p>

<h3>Sub-Group Scorecard</h3>
<table>
  <!-- Columns: Sub-Group | Stores | VDPs | VDP MoM% | Connections | Conn MoM% | % to Market | Flags | Top Opportunity -->
  <!-- Sorted by % to Market descending -->
  <!-- % to Market heatmap: green >0, red <0; MoM% green/red -->
  <!-- If Internal benchmark used, mark row with asterisk + footnote -->
</table>

<h3>Headline Read</h3>
<ul>
  <li><strong>Biggest story:</strong> {sub-group driving or dragging this month}</li>
  <li><strong>Top ROI lever:</strong> {sub-group with most HIGH flags × avg demand gap}</li>
</ul>

<h3>Per-Sub-Group Drafts Ready</h3>
<ol>
  <!-- One line per sub-group: "Asbury — 69 stores, +X% to market, Top Opp: [Store]" -->
</ol>

<p>Please reply <strong>approved</strong>, <strong>changes requested</strong>, or specific edits.
Once approved I'll finalize the 4 per-sub-group drafts.</p>

<p>Cheers,<br>Jake</p>
```

**Gate logic:**
- Approved → Step 7
- Changes requested → apply, resend, loop
- No reply 48h → ping once; do NOT auto-proceed

All drafts currently route to **Sharon Cunane (scunane@cars.com)** until per-sub-group client contacts are confirmed.

---

### Step 7 — Compose Per-Sub-Group Emails

**Gate:** Proceed ONLY after umbrella overview sign-off from Step 6.5.

One email per sub-group (not per brand). For each:

**Subject:** `{Sub-Group Name} — Monthly Performance Update | {Month} {Year}`
**To:** scunane@cars.com (Sharon Cunane — until client contact confirmed per sub-group)

Sub-group display names for subjects:
- `Asbury` → "Asbury Automotive Group"
- `LHM` → "Larry H. Miller Dealerships"
- `Koons` → "Koons Automotive"
- `Herb_Chambers` → "Herb Chambers Companies"

```html
<h3>{Sub-Group Display Name} — {Store count} stores, {Month} {Year}</h3>
<p>
  Market capture: <strong>{±X%} to market</strong> · VDPs {±X%} MoM · Connections {±X%} MoM<br>
  <strong>Top story:</strong> {one-line headline}
</p>

<!-- If Portfolio DI fallback used:
     "Internal benchmark: {±X%} vs Asbury umbrella avg (market data unavailable)" -->

<h3>Store Scorecard</h3>
<table>
  <!-- Sorted by opportunity score descending -->
  <!-- Columns: Store | VDPs | MoM | Connections | MoM | Cost/Lead | Badge % | Flags | Signal -->
  <!-- Color: green MoM = positive, red = negative; bold flagged stores -->
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

<p><a href="{Google Sheet URL}">Full data in the Asbury Group Monthly Performance sheet</a></p>
<p>Cheers,<br>Jake</p>
```

---

### Step 8 — Google Sheet Update

Create or update **"Asbury Group Monthly Performance — {Year}"**:

**Tab: "{Month} Overview"** — umbrella-level dashboard
- One row per sub-group (sorted by % to Market descending)
- Columns: Sub-Group, Stores, Total VDPs, VDP MoM%, Total Connections, Conn MoM%, % to Market, DI Source, Flags, Top Opportunity, Top Bright Spot
- Header: Poppins 11, bold white on `#6a0dad` purple
- % to Market heatmap: red −25% → yellow 0% → green +25%

**Tab: "{Month} - {Sub-Group} Summary"** — one per sub-group
- All stores with full metrics from Steps 2–3
- Columns: Store, CCID, VDPs (CP/PP), VDP MoM%, Connections (CP/PP), Conn MoM%, Cost/Lead, Avg Inventory, Badge %, Opportunity Score, Flags, Signal
- Poppins font, purple headers (`#6a0dad`), banded rows

**Tab: "Sub-Group Overview"** — rolling across months
- One row per sub-group per month; sorted month desc, sub-group alpha

**Tab: "Store Flags"** — rolling flag log
- Month, Store, Sub-Group, Score, Flag Reason, Action Taken (manual fill)

Conditional formatting via `spreadsheet.batch_update({"requests": [...]})`:
- MoM% columns: green text for positive, red for negative
- Signal column: Market Leader (#006100/#FFFFFF bold), Underperformer (#f6b26b/#990000 bold), Well Positioned (#b6d7a8/#274e13), Hidden Gem (#9fc5e8/#073763), Niche Winner (#1155cc/#FFFFFF bold), Oversaturated (#ffe599/#7f6000), Specialty (#d9d9d9/#434343), Low Priority (#efefef/#999999)
- Opportunity Score: gradient green scale (high = darker green)

Use gspread with `~/.claude/tokens/sheets_credentials.json`.

---

### Step 9 — QC

- [ ] Store counts match expected roster per sub-group (69 / 29 / 18 / 33 = 149 total)
- [ ] No stores with all-zero metrics (data pull failure)
- [ ] Any store with >30% MoM swing — verify not artifact
- [ ] All flagged stores have investigation insights
- [ ] Email length 250–400 words per sub-group
- [ ] Sheet formatting correct (Poppins, purple headers, conditional colors)
- [ ] Sheet link in each email body is correct
- [ ] Umbrella Overview drafted (Step 6.5) and sign-off recorded
- [ ] DI Source consistent across Sheet + per-sub-group emails
- [ ] All email-facing demand KPIs displayed as `±X% to market` — no raw index numbers
- [x] Routing confirmed: all drafts To: scunane@cars.com (Sharon Cunane — EAE) until per-sub-group client contacts identified

---

### Step 10 — Gmail Drafts

For each sub-group email:
1. Compose HTML body per Step 7 template
2. Create Gmail draft via Gmail MCP — **draft only, never send**
3. Confirm draft created and report subject + recipient

Fallback: save HTML to `~/Documents/Reports/AsburyGroup/asbury_{subgroup}_{month}_{year}.html`

---

## Key Reference

- **Umbrella:** Asbury Group (4 sub-groups, 149 stores)
- **Sub-groups:** Asbury (69) · Larry H. Miller (29) · Koons (18) · Herb Chambers (33)
- **EAE contact (all sub-groups):** Sharon Cunane — scunane@cars.com (until per-sub-group client contacts confirmed)
- **Tableau workbook:** Cars Monthly Marketplace Dealer Health Metrics (ID: 1792343)
- **Tableau view:** `a0b9bdce-2db3-4ea0-a2fc-365fd08c5786`
- **Tableau filters (one per sub-group):**
  - Asbury: `vf_Maj%20Cust%20Name=Asbury`
  - LHM: `vf_Maj%20Cust%20Name=Larry%20Miller`
  - Koons: `vf_Maj%20Cust%20Name=Koons%20Automotive%20MA%20Group`
  - Herb Chambers: `vf_Maj%20Cust%20Name=Herb%20Chambers%20MA%20Group`
- **investigation_triggers:** `~/Documents/scripts/investigation_triggers.py` (`show_sams=False`)
- **Report folder:** `~/Documents/Reports/AsburyGroup/`
- **gspread token:** `~/.claude/tokens/sheets_credentials.json`
- **Related skills:** `/herb-chambers-employee-update` (quarterly DR audit for Herb Chambers stores), `/investigate-stores`, `/auto-research`, `/dealer-marketshareanalysis`
- **Schedule:** Monthly, manually triggered
- **No rotation** — all 4 sub-groups run every month
