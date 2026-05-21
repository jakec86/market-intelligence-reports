# Sonic Monthly Brand Performance Report — Monthly Workflow

Run the monthly Sonic Automotive Group brand performance report. Produces per-brand email drafts to Sonic brand managers (CC Sharon Cunane) with store scorecards, market context, and actionable deep dives.

---

## Overview

Sonic Automotive Group (~101 active stores, 18 brands) gets brand-segmented monthly reporting on a **rotating schedule**:
- **Luxury rotation:** BMW, Audi, Mercedes-Benz, Land Rover, Porsche, Jaguar
- **Volume rotation:** Honda, Toyota, Ford, Chevrolet, Cadillac, Lexus, Hyundai, VW, MINI, Volvo, Subaru, Nissan, CDJR

Each rotation produces one email per brand → Sonic brand manager, CC Sharon Cunane (scunane@cars.com). Emails are **drafts only** — never auto-sent.

**Verification gate (Step 6.5):** BEFORE per-brand drafts are composed, a **Group Overview email** goes to Sharon for verification/examination. Per-brand drafting (Step 7) is gated on her sign-off.

**Uncap baseline carry-forward:** Nov '25 (pre-uncap) group baseline is **22,151 non-phone + 2,954 phone = 25,105 total connections/mo**. Carry forward as a persistent comparison column in the Group Overview and a one-line context in each brand email **until stated otherwise**.

**Exclusions:** eCarOne (separate reporting), Tactical Fleet Charlotte (CCID 6001077), Tactical Fleet Dallas (CCID 5383761)

**Google Sheet:** TBD — create on first run, save ID to memory
**Report folder:** `~/Documents/Reports/SonicAutomotive/`

---

## Brand → Store Mapping (from March 2026 billing file)

```
BRAND_STORES:
  Audi:
    - {name: "Audi Birmingham", max_id: "5365542"}  # placeholder — resolve CCIDs at runtime
    - {name: "Audi Central Houston", max_id: "147534"}
    - {name: "Audi Nashville", max_id: "12716"}
    - {name: "Audi Nashville Downtown", max_id: "6061993"}
    - {name: "Audi New Orleans", max_id: "6068520"}
    - {name: "Audi Owings Mills", max_id: "6060022"}
    - {name: "Audi Pensacola", max_id: "5373633"}
    - {name: "Audi Rockville", max_id: "2749"}
    - {name: "Audi West Houston", max_id: "147555"}
  BMW:
    - {name: "Beverly Hills BMW", max_id: "24234"}
    - {name: "BMW Certified Pre-Owned Nashville", max_id: "84231"}
    - {name: "BMW Mini of Birmingham", max_id: "182765"}
    - {name: "BMW of Chattanooga", max_id: "182757"}
    - {name: "BMW of Denver Downtown", max_id: "5243850"}
    - {name: "BMW of Fairfax", max_id: "2256"}
    - {name: "BMW of Fort Myers", max_id: "182768"}
    - {name: "BMW of Monrovia", max_id: "2903"}
    - {name: "BMW of Montgomery", max_id: "12462"}
    - {name: "BMW of Nashville", max_id: "5376822"}
    - {name: "BMW of West Houston", max_id: "182950"}
    - {name: "Century BMW", max_id: "83846"}
    - {name: "Global Imports BMW", max_id: "10726"}
    - {name: "Long Beach BMW", max_id: "864"}
    - {name: "Momentum BMW", max_id: "147503"}
    - {name: "Stevens Creek BMW", max_id: "25732"}
  Cadillac:
    - {name: "Cadillac of Las Vegas", max_id: "2393300"}
    - {name: "Cadillac of South Charlotte", max_id: "179855"}
    - {name: "Massey Cadillac of Orlando", max_id: "53844"}
    - {name: "Massey Cadillac of South Orlando", max_id: "203150"}
    - {name: "Ron Craft Cadillac", max_id: "6043280"}
  CDJR:
    - {name: "Bonham Chrysler Jeep Dodge Ram", max_id: "21733"}
    - {name: "Greenville Chrysler Dodge Jeep Ram", max_id: "21730"}
  Chevrolet:
    - {name: "Capitol Chevrolet AL", max_id: "12450"}
    - {name: "Lone Star Chevrolet", max_id: "97046"}
    - {name: "Ron Craft Chevrolet", max_id: "22358"}
    - {name: "Sun Chevrolet", max_id: "6050982"}
  Ford:
    - {name: "Baytown Ford", max_id: "22357"}
    - {name: "Fort Mill Ford", max_id: "10442"}
    - {name: "Jordan Ford", max_id: "6053161"}
    - {name: "North Central Ford", max_id: "21602"}
    - {name: "Philpott Ford", max_id: "6040466"}
    - {name: "Town & Country Ford", max_id: "9838"}
    - {name: "Vernon Ford", max_id: "6034503"}
  Honda:
    - {name: "Buena Park Honda", max_id: "88062"}
    - {name: "Carson Honda", max_id: "1066"}
    - {name: "Concord Honda", max_id: "25509"}
    - {name: "Crest Honda", max_id: "85925"}
    - {name: "Economy Honda Superstore", max_id: "12792"}
    - {name: "Honda West", max_id: "96089"}
    - {name: "Honda of Jefferson City", max_id: "5354901"}
    - {name: "Honda of Serramonte", max_id: "113555"}
    - {name: "Honda of Stevens Creek", max_id: "25759"}
    - {name: "Lute Riley Honda", max_id: "21600"}
    - {name: "Pensacola Honda", max_id: "11359"}
    - {name: "Poway Honda", max_id: "24797"}
  Hyundai:
    - {name: "Greenville Hyundai", max_id: "2364461"}
    - {name: "Hyundai of Jefferson City", max_id: "5354866"}
    - {name: "Philpott Hyundai", max_id: "6034393"}
  Jaguar:
    - {name: "Jaguar Houston Central", max_id: "6034689"}
    - {name: "Jaguar Newport Beach", max_id: "6071012"}
    - {name: "Jaguar San Jose", max_id: "6071016"}
    # INACTIVE on marketplace — confirmed by Jake 2026-04-20, excluded:
    # - Jaguar Los Angeles (6071014)
  Land Rover:
    - {name: "Land Rover Houston Central", max_id: "147549"}
    - {name: "Land Rover Houston North", max_id: "109956"}
    - {name: "Land Rover Los Angeles", max_id: "6071015"}
    - {name: "Land Rover Newport Beach", max_id: "6071013"}
    - {name: "Land Rover Pasadena", max_id: "6071011"}
    - {name: "Land Rover Roaring Fork", max_id: "152846"}
    - {name: "Land Rover San Jose", max_id: "6071017"}
    - {name: "Land Rover Santa Monica", max_id: "6071214"}
    - {name: "Land Rover South Atlanta", max_id: "5384914"}
    - {name: "Land Rover Southwest Houston", max_id: "147497"}
  Lexus:
    - {name: "Crown Lexus", max_id: "24634"}
    - {name: "Jordan Lexus", max_id: "6063744"}
    - {name: "Lexus of Birmingham", max_id: "12310"}
    - {name: "Lexus of Marin", max_id: "25668"}
    - {name: "Lexus of Serramonte", max_id: "25417"}
  Mercedes-Benz:
    - {name: "Mercedes-Benz of Calabasas", max_id: "24471"}
    - {name: "Mercedes-Benz of Denver", max_id: "5243849"}
    - {name: "Mercedes-Benz of Fort Myers", max_id: "90280"}
    - {name: "Mercedes-Benz of McKinney", max_id: "5368348"}
    - {name: "Mercedes-Benz of Nashville", max_id: "150607"}
    - {name: "Mercedes-Benz of Walnut Creek", max_id: "25621"}
  MINI:
    - {name: "Global Imports MINI", max_id: "208813"}
    - {name: "MINI of Fort Myers", max_id: "197042"}
    - {name: "Momentum MINI", max_id: "5363009"}
  Nissan:
    - {name: "Nissan of Chattanooga East", max_id: "5344514"}
    - {name: "Nissan of Greenville", max_id: "5354478"}
    - {name: "Nissan of Jefferson City", max_id: "5372219"}
  Porsche:
    - {name: "Porsche Bethesda", max_id: "5378208"}
    - {name: "Porsche Birmingham", max_id: "148921"}
    - {name: "Porsche of Nashville", max_id: "5327921"}
    - {name: "Porsche River Oaks", max_id: "5256482"}
    - {name: "Porsche West Houston", max_id: "5250295"}
  Subaru:
    - {name: "Grand Junction Subaru", max_id: "6000393"}
  Toyota:
    - {name: "Clearwater Toyota", max_id: "11947"}
    - {name: "Concord Toyota", max_id: "25512"}
    - {name: "Jordan Toyota", max_id: "6053160"}
    - {name: "Mountain States Toyota", max_id: "83544"}
    - {name: "Philpott Toyota", max_id: "5355963"}
    - {name: "Town and Country Toyota", max_id: "9865"}
    - {name: "Toyota of Mt. Pleasant", max_id: "5390276"}
    - {name: "Toyota of Paris", max_id: "5390396"}
    - {name: "Toyota of Santa Fe", max_id: "5355839"}
  Volkswagen:
    - {name: "Grand Junction Volkswagen", max_id: "6000392"}
    - {name: "Momentum Volkswagen of Upper Kirby", max_id: "22257"}
    - {name: "Volkswagen Of Fort Myers", max_id: "178060"}
    - {name: "Volkswagen of Fallston", max_id: "6001306"}
  Volvo:
    - {name: "Dyer & Dyer Volvo Cars", max_id: "10730"}
    - {name: "North Point Volvo Cars", max_id: "149338"}

UNMATCHED (assign manually or verify brand via SF):
  - Autobahn Motors (84916) — likely Mercedes-Benz, Belmont CA
  - Dave Smith Coeur d'Alene (190771) — multi-franchise (CDJR/Kia)
  - Vernon Auto Group (194763) — multi-franchise
  - W.I. Simonson Inc. (24293) — likely Mercedes-Benz, Santa Monica CA

EXCLUDED:
  - Tactical Fleet Charlotte (6001077)
  - Tactical Fleet Dallas (5383761)
  - eCarOne stores (separate billing entity, not in Sonic billing file)
```

**Brand counts (post 2026-04-22 roster cleanup):** BMW (16), Honda (12), Land Rover (10), Toyota (9), Audi (9), Ford (7), Mercedes-Benz (6), Porsche (5), Lexus (5), Cadillac (5), VW (4), Chevrolet (4), Jaguar (3), Hyundai (3), MINI (3), Nissan (3), Volvo (2), CDJR (2), Subaru (1) = **109 stores covered**. Plus ~9 still-unmatched (multi-franchise groups Dave Smith / Vernon Auto Group / W.I. Simonson / Autobahn Motors, admin-only entities Central Buying Service / Retail Trade Center, and inactive Jaguar LA + eCarOne).

---

## Recipient Mapping

Each brand email goes **To:** the Sonic brand manager(s), **CC:** marketing manager(s) + VP Brand + Sharon Cunane (default CC always).

Some brand managers cover multiple brands (e.g., BMW/MINI share Gregory Madaleno, Land Rover/Jaguar share John Tusa). Confirmed 2026-04-22.

```yaml
RECIPIENTS:
  default_cc: scunane@cars.com   # Sharon always CC'd on every brand email

  Audi:
    to:  [Zachary.Dobbins@sonicautomotive.com]
    cc:  [Morgan.schwartz@sonicautomotive.com, larry.sevrin@sonicautomotive.com]

  BMW:
    to:  [Gregory.Madaleno@sonicautomotive.com]
    cc:  [mike.walker@sonicautomotive.com]
  MINI:
    to:  [Gregory.Madaleno@sonicautomotive.com]   # shared with BMW
    cc:  [mike.walker@sonicautomotive.com]

  Mercedes-Benz:
    to:  [Christine.Wright@sonicautomotive.com]
    cc:  []   # no marketing manager / VP on file

  Land Rover:
    to:  [John.Tusa@sonicautomotive.com]
    cc:  [kortney.boston@sonicautomotive.com, Jeff.quisenberry@sonicautomotive.com]
  Jaguar:
    to:  [John.Tusa@sonicautomotive.com]   # shared with Land Rover
    cc:  [kortney.boston@sonicautomotive.com, Jeff.quisenberry@sonicautomotive.com]

  Porsche:
    to:  [Leah.webb@sonicautomotive.com]
    cc:  [kortney.boston@sonicautomotive.com, maria.moncada@sonicautomotive.com]

  Honda:
    to:  [Austin.McGonigal@sonicautomotive.com]
    cc:  [Morgan.schwartz@sonicautomotive.com]
  Ford:
    to:  [Austin.McGonigal@sonicautomotive.com]   # shared with CDJR
    cc:  [Morgan.schwartz@sonicautomotive.com, Thomas.quintana@sonicautomotive.com]
  CDJR:
    to:  [Austin.McGonigal@sonicautomotive.com]   # shared with Ford
    cc:  [Morgan.schwartz@sonicautomotive.com, Thomas.quintana@sonicautomotive.com]

  Toyota:
    to:  [Sierra.Mascilak@sonicautomotive.com]
    cc:  [rebecca.hauer@sonicautomotive.com, dewayne.fairchild@sonicautomotive.com]
  Lexus:
    to:  [Sierra.Mascilak@sonicautomotive.com]   # shared with Toyota
    cc:  [rebecca.hauer@sonicautomotive.com, phuong.nguyen@sonicautomotive.com]

  Chevrolet:    # "GM" bucket (Chevrolet + Cadillac)
    to:  [Paige.risner@sonicautomotive.com]
    cc:  [sara.thompson@sonicautomotive.com, bill.hull@sonicautomotive.com]
  Cadillac:
    to:  [Paige.risner@sonicautomotive.com]       # shared with Chevrolet (GM bucket)
    cc:  [sara.thompson@sonicautomotive.com, bill.hull@sonicautomotive.com]
  Subaru:
    to:  [Paige.risner@sonicautomotive.com]       # shared with GM
    cc:  [sara.thompson@sonicautomotive.com, bill.hull@sonicautomotive.com]
  Nissan:
    to:  [Paige.risner@sonicautomotive.com]       # shared with GM/Subaru
    cc:  [sara.thompson@sonicautomotive.com, bill.hull@sonicautomotive.com]

  Hyundai:
    to:  [Marielle.bernacchi@sonicautomotive.com]
    cc:  [kortney.boston@sonicautomotive.com]
  Volkswagen:
    to:  [Marielle.bernacchi@sonicautomotive.com]   # shared with Hyundai
    cc:  [kortney.boston@sonicautomotive.com]

  Volvo: TBD   # no Sonic brand manager identified yet
```

**Always CC Sharon (scunane@cars.com)** on every per-brand email regardless of brand.

### Consolidation: brand-manager groupings (send once, list all brands)

When the same brand manager owns multiple brands, consider **combining into one email** to that manager covering all their brands rather than sending duplicates:
- Gregory Madaleno → BMW + MINI (one combined email)
- John Tusa → Land Rover + Jaguar (one combined email)
- Austin McGonigal → Honda + Ford + CDJR (one combined email)
- Sierra Mascilak → Toyota + Lexus (one combined email)
- Paige Risner → Chevrolet + Cadillac + Subaru + Nissan (one combined "GM/Subaru/Nissan" email)
- Marielle Bernacchi → Hyundai + Volkswagen (one combined email)

The Group Overview email already provides cross-brand view to Sharon; per-manager combining keeps their inbox cleaner while still giving per-brand detail via sections within the email. Default to combined emails unless a brand-specific deep dive warrants a standalone.

---

## Email Drafting Rule

Each brand email must be concise and consultative — not a data dump:
- **Target length:** 250-400 words per brand email
- **Tone:** Professional-casual, data-first, action-oriented
- **Vary:** opening line, which insight to lead with, callout phrasing
- **Keep consistent:** scorecard table format, "Top Opportunities" + "Bright Spots" sections, close with "Cheers, Jake"
- **Never:** paste raw data, use generic observations, skip the sheet link
- **Frame findings as:** revenue impact, competitive advantage, or risk — not just metric movement

---

## Steps

### Step 0 — Determine Rotation & Month

Ask: **Which rotation this month — Luxury or Volume?**
- Luxury: BMW (16), Audi (6), Mercedes-Benz (6), Land Rover (10), Porsche (5), Jaguar (2) = **45 stores**
- Volume: Honda (12), Toyota (8), Ford (6), Chevrolet (3), Cadillac (4), Lexus (5), Hyundai (3), VW (4), MINI (2), Volvo (2), Subaru (1), Nissan (1), CDJR (1) = **52 stores**

Confirm the reporting month (default: prior calendar month).

### Step 1 — Salesforce Roster Validation

Query SF to validate the brand mapping and capture current product packages:

```sql
SELECT Name, CCID__c, BillingCity, BillingState, Account_Status__c, Type
FROM Account
WHERE Parent.Name LIKE '%Sonic%'
```

Then pull active subscriptions:
```sql
SELECT SBQQ__Account__r.Name, SBQQ__Account__r.CCID__c, SBQQ__ProductName__c, SBQQ__NetPrice__c
FROM SBQQ__Subscription__c
WHERE SBQQ__Account__r.Parent.Name LIKE '%Sonic%'
AND SBQQ__SubscriptionEndDate__c > TODAY
```

**Important:** Use `SBQQ__Subscription__c` for actual products, NOT `Account_Status__c` (can be stale).

Flag:
- Stores added or dropped since last month's mapping
- Stores with minimal product packages (upsell candidates)
- Stores missing from SF but present in billing (data integrity issue)

### Step 2 — Tableau Health Metrics (VDPs, Inventory, Cost/Lead)

Pull store-level VDPs, inventory, Cost/Lead, Cost/VDP, merchandising metrics from **Tableau REST API** — no Playwright or SSO needed.

**Important — Connection counts come from admin.cars.com (Step 3), NOT Tableau.**
Tableau's "Total Contacts" is a subset of the real Connection count (excludes walk-ins, map views, some "other" types). For consistent reporting with prior Sonic analyses (phone/non-phone uncap reports), pull Connections from admin.cars.com group-level Connections & Contact Details report.

**API call:**
```bash
TOKEN=$(curl -s -X POST "https://us-west-2b.online.tableau.com/api/3.22/auth/signin" \
  -H "Content-Type: application/json" \
  -d '{"credentials":{"personalAccessTokenName":"Claude","personalAccessTokenSecret":"'$TABLEAU_PAT_SECRET'","site":{"contentUrl":"cars"}}}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['credentials']['token'])")

curl -s "https://us-west-2b.online.tableau.com/api/3.22/sites/12338861-20b1-46ed-8841-269a5a937edb/views/a0b9bdce-2db3-4ea0-a2fc-365fd08c5786/data?vf_Maj%20Cust%20Name=Sonic" \
  -H "X-Tableau-Auth: $TOKEN" > sonic_health_metrics.csv
```

**Returns:** 120 stores × 48 metrics = ~5,808 rows. Columns: AE, Customer Name, Group Cust Name, Legacy Id, Maj Cust Name, Marketplace Score, Measure Names, Measure Values.

**Key metrics available (all CP/PP/Delta):**
- Avg Daily Vehicles (Used/New/Total), Minimally Merchandised %
- VDP Total Imps (Used/New), New VDPs, Used VDPs
- Total Contacts, Marketplace Leads (Used/New)
- Cost/VDP, Cost/Lead
- Avg Daily Rating

**Important API gotchas:**
- **Do NOT send `Accept: text/csv` header** — returns 406. Omit the header entirely.
- Filter value is `Sonic` (not "Sonic Automotive Group")
- Data is in long/pivoted format (Measure Names / Measure Values) — pivot to wide format in Python for the scorecard

Parse the CSV and pivot to wide format:
```python
import csv, io
# Group by Customer Name, pivot Measure Names → columns
stores = {}
for row in csv.DictReader(io.StringIO(raw_csv)):
    name = row['Customer Name']
    if name not in stores:
        stores[name] = {
            'Customer Name': name,
            'Legacy Id': row['Legacy Id'],   # canonical key — used by investigation_triggers
            'Maj Cust Name': row.get('Maj Cust Name', ''),
            'AE': row.get('AE', ''),
        }
    stores[name][row['Measure Names'].strip()] = row['Measure Values']
```

This gives the full scorecard data for all Sonic stores. No admin.cars.com needed for the brand summary.

### Step 3 — admin.cars.com Data Collection

**Requires active JumpCloud SSO session.** Prompt:
> "Please log into admin.cars.com via JumpCloud SSO in your browser, then confirm to proceed."

If user skips SSO (or session expired), use `--skip-admin` mode — Tableau-only scorecard, no deep dive.

**For each brand in the rotation:**

#### 3a. Performance Trends (all stores in brand)

Navigate per store: `https://admin.cars.com/dealers/{UUID}/reports/performance_trends`

**First, discover UUIDs:** Search `https://admin.cars.com/dealers/all/reports?query={store_name_or_ccid}` to find each store's UUID. Cache discovered UUIDs in the memory file.

Capture from KPI tiles:
- Avg Inventory (Used) + MoM %
- Under-Merchandised % + MoM change
- Connections (total) + MoM %
- VDPs (total) + MoM %
- Fair/Above Badge % (from badge distribution)

#### 3b. Demand Signals (flagged stores only — after Step 5 scoring)

For top 3-5 flagged stores per brand:
- Navigate to `https://admin.cars.com/dealers/{UUID}/reports/demand_signals`
- Download **Market Comparison** crosstab (CSV)
- Compute Share Index / Quadrant / Signal per `/dealer-marketshareanalysis` methodology:
  - VDP Index = VDP Share % / Vehicle Share %
  - Connection Index = Connections Share % / Vehicle Share %
  - Share Index = (VDP Index × 0.4) + (Connection Index × 0.6)
  - Quadrant: Churner / Lot Sitter / Rarity / Niche (median split)
  - Signal: Market Leader / Underperformer / Well Positioned / Oversaturated / Niche Winner / Hidden Gem / Specialty / Low Priority

#### 3c. MAE vs Organic Split (if store has MAE product)

For flagged stores with Market Area Expansion:
- Navigate to `https://admin.cars.com/dealers/{UUID}/reports/connections_contact_details`
- Filter "Market expansion leads" = "Yes" → MAE connections
- Filter "Market expansion leads" = "No" → Organic connections
- Compare MoM trends — if organic grows but MAE drops, it's a merchandising/pricing issue

### Step 4 — Market Demand Context

**Market Demand Index (primary — from admin.cars.com Market Comparison):**

Per-store Market DI measures how efficiently a store converts inventory presence into VDP capture within its own DMA competitive set:

```
Store Market DI = Store VDP Share of DMA ÷ Store Inventory Share of DMA
```

- DI > 1.0 → store captures MORE VDP share than its inventory share → out-merchandising market
- DI < 1.0 → store captures LESS VDP share than its inventory share → under-merchandising
- DI = 1.0 → parity with market

**Stakeholder-facing form:** always convert to `% to Market = (DI − 1) × 100`
- DI 1.24 → **+24% to market**
- DI 0.78 → **−22% to market**

**Brand-level Market DI (per-DMA aggregation to avoid double-counting shared markets):**

When multiple Sonic stores share a DMA (e.g., 3 Land Rover Houston stores all compete in the Houston LR market), the market-size denominator must be counted once per DMA, not once per store. Correct rollup:

```
For each DMA where the brand has ≥1 Sonic store:
    brand_dma_vdps       = Σ dealer VDPs for Sonic stores of that brand in that DMA
    brand_dma_inventory  = Σ dealer inventory for Sonic stores of that brand in that DMA
    market_dma_vdps      = total market VDPs in that DMA (counted once)
    market_dma_inventory = total market inventory in that DMA (counted once)

Brand Market DI = (Σ brand_dma_vdps / Σ market_dma_vdps)
                ÷ (Σ brand_dma_inventory / Σ market_dma_inventory)

Brand % to Market = (Brand Market DI − 1) × 100
```

The per-DMA grouping is critical — summing store-level shares directly would triple-count the Houston market across Houston Central / Houston North / Southwest Houston.

**Portfolio Demand Index (emergency fallback — internal benchmark only):**

Only used when admin.cars.com data is unavailable for the brand. Do NOT surface in emails as "Demand Index" — label explicitly as **"Internal benchmark (vs Sonic group avg)"** so stakeholders don't confuse a self-referential number with true market position.

```
Portfolio DI = (Brand VDPs / Brand Avg Inventory) ÷ (All-Sonic VDPs / All-Sonic Avg Inventory)
```

- Above 1.0 = brand beats Sonic-portfolio-average efficiency (not the market)
- Below 1.0 = brand lags the Sonic portfolio average

**Rule:** Market DI is the default for all per-brand rollups and all email-facing KPIs. If admin data is missing for >20% of the stores in a brand, flag it in the Group Overview email and fall back to Portfolio DI **with the internal-benchmark label**.

Compare stores within the brand to each other — who captures the most share relative to inventory.

### Step 5 — Store Scoring & Flagging

Use `investigation_triggers.py` to score and flag stores. This replaces manual weighted scoring with the standardized playbook scenario detector shared across all group workflows.

```python
import sys
sys.path.insert(0, os.path.expanduser("~/Documents/scripts"))
from investigation_triggers import investigate_stores, format_triage_report

# brand_stores = list of store dicts already pivoted from Step 2 Tableau data
brand_results = investigate_stores(brand_stores)

# Print triage for QC visibility
print(format_triage_report(brand_results, title=f"Sonic {brand} — {month} {year}"))
```

**What `investigate_stores()` returns:**

```python
{
    "high":         [{"store": str, "ccid": str, "flags": [...]}],  # ≥1 HIGH severity flag
    "medium":       [{"store": str, "ccid": str, "flags": [...]}],  # MEDIUM flags only
    "bright_spots": [{"store": str, "ccid": str, "signal": str}],   # VDPs + Connections both up ≥5%
    "clean":        [{"store": str, "ccid": str}],
}
```

Each flag in `flags` has: `{"scenario": int, "severity": "HIGH"|"MEDIUM", "signal": str}`

**Scenario → Playbook mapping detected automatically:**
| Scenario | Trigger |
|---|---|
| 1 — Drop in Connections | Connections delta ≤ −10% (HIGH) or ≤ −5% (MEDIUM) |
| 2 — Best Match / Merchandising | Under-merchandised % > 25%, worsening MoM |
| 3 — Gradual VDP Decrease | VDP delta ≤ −10% (HIGH) or ≤ −5% (MEDIUM) |
| 4 — Demand / Inventory Mismatch | Inventory up ≥5% while VDPs down ≥5% simultaneously |
| 5 — Lead Quality / Cost | Cost/Lead > 1.5× brand median (HIGH) or > 1.25× (MEDIUM) |

**Flag assignment for Step 6:**

```python
# Primary candidates: all HIGH stores (up to 5 per brand)
flagged_stores = [e["store"] for e in brand_results["high"][:5]]

# If fewer than 3 HIGH, pull top MEDIUM stores to fill to 3
if len(flagged_stores) < 3:
    flagged_stores += [e["store"] for e in brand_results["medium"][:3 - len(flagged_stores)]]

# Bright spots feed Step 7 email "Bright Spots" section directly
bright_spot_stores = [e["store"] for e in brand_results["bright_spots"][:3]]
```

**Opportunity score for sheet (Step 8):** Derive from flag count + severity rather than a weighted formula:

```python
def opportunity_score(entry):
    score = 0
    for flag in entry.get("flags", []):
        score += 30 if flag["severity"] == "HIGH" else 15
    return min(score, 100)
```

### Step 5b — Per-Brand Rollup (for Group Overview)

Build one row per brand (for Step 6.5 Group Overview dashboard):

| Field | Computation |
|-------|-------------|
| Store Count | # stores in rotation |
| Total VDPs | Sum of VDPs across brand stores |
| VDP MoM% | Brand total vs prior month |
| Total Connections | Sum across brand stores |
| Connections MoM% | Brand total vs prior month |
| vs Nov '25 % | (Current Connections / Brand's Nov '25 Connections) − 1 (if Nov brand-level available; else group-level) |
| % to Market | `(Brand Market DI − 1) × 100` (per-DMA aggregation per Step 4). Fallback: "Internal benchmark %" if Portfolio DI used. |
| DI Source | "Market" or "Internal benchmark" — carry through to sheet + emails |
| Investigation Flags | `{len(high)} HIGH / {len(medium)} MEDIUM` — from `brand_results` |
| Signal Counts | Market Leaders / Hidden Gems / Underperformers / Well Positioned / Niche Winners / Specialty / Low Priority / Oversaturated — from Step 3b Demand Signals |
| Top Opportunity | `brand_results["high"][0]["store"]` if any HIGH, else first MEDIUM |
| Top Bright Spot | `brand_results["bright_spots"][0]["store"]` if any |

Sort brands by % to Market descending for the overview.

### Step 6 — Auto-Research Deep Dive (Flagged Stores)

**Input:** `flagged_stores` list from Step 5. Each store already has scenario flags explaining *why* it was flagged — use these to direct the deep dive rather than re-diagnosing from scratch.

For each flagged store:

1. **Lead with the scenario signals** from Step 5 flags — these are the confirmed data-driven triggers:
   - Scenario 1 flag → focus on Historical Connections report, Low Engaged Inventory
   - Scenario 3 flag → isolate NEW vs USED VDP split; check SRP trend
   - Scenario 4 flag → pull Demand Signals market comparison, check make/model mix vs DMA
   - Scenario 5 flag → review Cost/Lead vs Competitive Set, listing quality

2. **Layer in Demand Signals context** (from Step 3b, if available):
   - Count of Underperformers (Churner + SI < 1.0) — biggest ROI lever
   - Hidden Gems (Rarity + SI < 1.0) — demand exists, not capturing it
   - Niche Winners (Rarity + SI ≥ 1.0) — bright spots to protect

3. **Produce per-store insight** (2-3 sentences):
   - What's happening (scenario signal)
   - Why it matters (revenue/retention impact)
   - What to do (specific next step from scenario's playbook action)

### Step 6.5 — Group Overview Email to Sharon (Verification Gate)

**BEFORE composing per-brand drafts, send a Group Overview email to Sharon for verification/examination.** Per-brand drafting (Step 7) is gated on her sign-off.

**Subject:** `Sonic — {Month} {Year} Overview | Pre-Send Review`

**To:** scunane@cars.com
**CC:** (none)

**Body structure:**

```html
<p>Sharon,</p>
<p>Pre-send review for {Month} {Year} — {brand_count} brands / {store_count} stores.
Per-brand drafts are ready to queue pending your sign-off.</p>

<h3>Portfolio Pulse — {Month} {Year}</h3>
<p>
  {total_stores} stores · {total_VDPs} VDPs ({VDP_MoM%} MoM) · {total_connections} Connections ({Conn_MoM%} MoM)<br>
  <strong>vs Nov '25 uncap baseline:</strong> {±X%} ({current_connections} vs 25,105)
</p>

<h3>Brand Scorecard</h3>
<table>
  <!-- Columns: Brand | Stores | VDPs | VDP MoM% | Connections | Conn MoM% | % to Market | Leaders | Hidden Gems | Underperformers | Top Opportunity -->
  <!-- Sorted by % to Market descending -->
  <!-- Color: % to Market heatmap green>0, red<0; MoM% green/red -->
  <!-- If any brand used Internal benchmark fallback, mark its row with an asterisk and footnote -->
</table>

<h3>Headline Read</h3>
<ul>
  <li><strong>Biggest story:</strong> {one-line — which brand is driving or dragging}</li>
  <li><strong>Biggest ROI lever:</strong> {brand with most Underperformers × avg demand gap}</li>
  <li><strong>Uncap trajectory:</strong> {still above / back to / below Nov baseline}</li>
</ul>

<h3>Per-Brand Drafts Ready</h3>
<ol>
  <!-- One line per brand: "BMW — 16 stores, +12% to market, Top Opp: Stevens Creek BMW" -->
</ol>

<p>Please reply with <strong>approved</strong>, <strong>changes requested</strong>, or specific edits per brand.
Once approved, I'll finalize the {brand_count} per-brand drafts to your inbox (recipients TBD — currently routed to you for the test run).</p>

<p>Cheers,<br>Jake</p>
```

**Gate logic:**
- If Sharon replies **approved** → proceed to Step 7
- If Sharon replies **changes requested** → apply edits, resend overview, loop
- If no reply within 48 hrs → ping once; do NOT auto-proceed

**During test-run phase (before brand manager recipient list is finalized):**
- All per-brand drafts (Step 7) route **To: scunane@cars.com** for review — no external recipients
- Subject prefix: `[TEST] Sonic {Brand} — Monthly Performance Update | {Month} {Year}`
- Once brand managers are confirmed, remove test prefix and swap primary recipient

### Step 7 — Compose Brand Emails

**Gate:** Proceed ONLY after Sharon approves the Group Overview from Step 6.5.

For each brand in the rotation, compose an HTML email draft:

**Subject (test-run phase):** `[TEST] Sonic {Brand} — Monthly Performance Update | {Month} {Year}`
**Subject (production):** `Sonic {Brand} — Monthly Performance Update | {Month} {Year}`

**To:** Brand manager (from recipient mapping). **During test run → scunane@cars.com only.**
**CC:** scunane@cars.com (when primary recipient is the brand manager; omit during test run)

**Body structure:**

```html
<h3>{Brand} — {Store count} stores, {Month} {Year}</h3>
<p>
  Market capture: <strong>{±X%} to market</strong> · VDPs {±X%} MoM · Connections {±X%} MoM<br>
  <strong>Top story:</strong> {One-line headline — biggest story this month}
</p>

<!-- If Portfolio DI fallback was used, replace "{±X%} to market" with:
     "Internal benchmark: {±X%} vs Sonic group avg (market data unavailable)" -->
<!-- Omit the Nov '25 uncap baseline line from per-brand emails; it lives in the Group Overview only -->
<!-- Signal mix moves to the Store Scorecard table below, not the header -->

<h3>Store Scorecard</h3>
<table>
  <!-- Sorted by opportunity score descending -->
  <!-- Columns: Store | VDPs | MoM | Connections | MoM | Cost/Lead | Badge % | Signal -->
  <!-- Color: green MoM = positive, red = negative -->
  <!-- Bold flagged stores -->
</table>

<h3>Top Opportunities</h3>
<ol>
  <li><strong>{Store}</strong> — {auto-research insight}<br>
      <em>Action: {specific recommendation}</em></li>
  <li>...</li>
  <li>...</li>
</ol>

<h3>Bright Spots</h3>
<ul>
  <li><strong>{Store}</strong> — {what's working and why}</li>
  <li>...</li>
</ul>

<p><a href="{Google Sheet URL}">Full data in the Sonic Monthly Performance sheet</a></p>

<p>Cheers,<br>Jake</p>
```

Use `Content-Type: text/html` and base64url-encode as RFC 2822 `raw` parameter for Gmail API.

### Step 8 — Google Sheet Update

Create or update the Google Sheet **"Sonic Monthly Performance — {Year}"**:

**Tab: "{Month} Overview"** (new — group-level dashboard)
- One row per brand in the rotation (sorted by % to Market descending)
- Columns: Brand, Stores, Total VDPs, VDP MoM%, Total Connections, Conn MoM%, vs Nov '25 Baseline %, % to Market, DI Source (Market / Internal benchmark), Market Leaders, Hidden Gems, Underperformers, Well Positioned, Other Signals, Top Opportunity Store, Top Bright Spot
- Header: Poppins 11, bold white on #6a0dad purple
- % to Market cell: heatmap gradient (red −25% → yellow 0% → green +25%)
- Signal count cells: small heatmap per column (green for Leaders/NicheWinners, red for Underperformers/Oversaturated)
- vs Nov '25 Baseline %: green >0, red <0
- This tab is the source of truth for the Group Overview email (Step 6.5)

**Tab: "{Month} - {Brand} Summary"** (one per brand in rotation)
- All stores in the brand with full metrics from Steps 2-3
- Columns: Store Name, CCID, VDPs (CP), VDPs (PP), VDP MoM%, Connections (CP), Connections (PP), Conn MoM%, Cost/Lead, Avg Inventory, Badge %, Opportunity Score, Flags (HIGH/MED), Signal
- Opportunity Score: derived from `investigation_triggers` flag severity — 30pts per HIGH flag + 15pts per MEDIUM flag, capped at 100. Write as integer.
- Flags column: e.g. `"2H / 1M"` — count of HIGH and MEDIUM flags from Step 5 `brand_results`
- Poppins font, purple headers (#6a0dad), banded rows

**Conditional formatting via gspread `batch_update`** (no Apps Script):

Apply all formatting in the same Python session that writes the data, using `spreadsheet.batch_update({"requests": [...]})` with these request types:

```python
# 1. MoM% columns — green for positive, red for negative
{"addConditionalFormatRule": {
    "rule": {
        "ranges": [{"sheetId": sheet_id, "startRowIndex": 1, "startColumnIndex": col, "endColumnIndex": col+1}],
        "booleanRule": {
            "condition": {"type": "NUMBER_GREATER", "values": [{"userEnteredValue": "0"}]},
            "format": {"textFormat": {"foregroundColorStyle": {"rgbColor": {"red": 0.13, "green": 0.55, "blue": 0.13}}}}
        }
    }, "index": 0
}}
# Repeat with NUMBER_LESS + red (0.8, 0.0, 0.0) for negative deltas

# 2. Signal column — color per signal type
{"addConditionalFormatRule": {
    "rule": {
        "ranges": [{"sheetId": sheet_id, "startRowIndex": 1, "startColumnIndex": signal_col, "endColumnIndex": signal_col+1}],
        "booleanRule": {
            "condition": {"type": "TEXT_EQ", "values": [{"userEnteredValue": "Market Leader"}]},
            "format": {"backgroundColor": {"red": 0, "green": 0.38, "blue": 0}, "textFormat": {"foregroundColorStyle": {"rgbColor": {"red": 1, "green": 1, "blue": 1}}, "bold": True}}
        }
    }, "index": 0
}}
# Repeat for each signal: Underperformer (orange/red), Well Positioned (light green),
# Oversaturated (yellow), Niche Winner (blue/white), Hidden Gem (light blue),
# Specialty (gray), Low Priority (light gray)
# Use same color scheme as /dealer-marketshareanalysis

# 3. Opportunity Score column — color scale (green high → red low)
{"addConditionalFormatRule": {
    "rule": {
        "ranges": [{"sheetId": sheet_id, "startRowIndex": 1, "startColumnIndex": score_col, "endColumnIndex": score_col+1}],
        "gradientRule": {
            "minpoint": {"color": {"red": 0.87, "green": 0.95, "blue": 0.87}, "type": "MIN"},
            "maxpoint": {"color": {"red": 0, "green": 0.38, "blue": 0}, "type": "MAX"}
        }
    }, "index": 0
}}

# 4. Flagged stores — bold entire row
# Use repeatCell request with bold format for flagged store rows after data is written
```

Signal color mapping (matches `/dealer-marketshareanalysis`):
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

**Tab: "Brand Overview"** (rolling — persists across months)
- One row per brand per month
- Columns: Month, Brand, Store Count, Total VDPs, VDP MoM%, Total Connections, Conn MoM%, % to Market, DI Source
- Sorted by month descending, then brand alphabetically

**Tab: "Store Flags"** (rolling — persists across months)
- Stores flagged each month with: Month, Store, Brand, Opportunity Score, Flag Reason, Action Taken (manual fill)

Use gspread with credentials at `~/.claude/tokens/sheets_credentials.json`.

### Step 9 — QC & Finalize

Before creating per-brand Gmail drafts (Step 10):

- [ ] Store counts match expected roster per brand
- [ ] No stores with all-zero metrics (data pull failure)
- [ ] Any store with >30% MoM swing — verify it's real, not a data artifact
- [ ] All flagged stores have auto-research insights
- [ ] Email length within 250-400 words per brand
- [ ] Google Sheet formatting is correct (Poppins, purple headers, conditional colors)
- [ ] Sheet link in email body is correct
- [ ] **Group Overview email drafted (Step 6.5) and Sharon's sign-off received** — record approval timestamp in the report folder
- [ ] **Nov '25 uncap baseline** column populated in Group Overview tab
- [ ] DI Source (Market vs Internal benchmark) consistent across Sheet + all per-brand emails
- [ ] All email-facing demand KPIs displayed as `±X% to market` — no raw index numbers in stakeholder copy
- [ ] No "luxury rotation" or "volume rotation" phrasing in any subject line or email body
- [ ] Test-run phase: all per-brand drafts route **To: scunane@cars.com** with `[TEST]` subject prefix

Report QC findings to user before drafting emails. If anomalies found, resolve before proceeding.

### Step 10 — Create Gmail Drafts

For each brand email:
1. Compose HTML body per Step 7 template
2. Create Gmail draft via Gmail MCP — **draft only, never send**
3. Confirm draft created and report subject line + recipient to user

Fallback: if Gmail MCP fails, save HTML to `~/Documents/Reports/SonicAutomotive/sonic_{brand}_{month}_{year}.html`

---

## Rotation Cadence

| Month | Rotation | Brands |
|-------|----------|--------|
| Odd months (Jan, Mar, May...) | Luxury | BMW, Audi, MB, LR, Porsche, Jaguar |
| Even months (Feb, Apr, Jun...) | Volume | Honda, Toyota, Ford, Chevy, Cadillac, Lexus, Hyundai, VW, MINI, Volvo, Subaru, Nissan, CDJR |

Override with user input at Step 0.

---

## Key Reference

- **Parent Group:** Sonic Automotive Group (CCID: 538486)
- **~101 active stores** across 18 brands (excluding Tactical Fleet + eCarOne)
- **Primary contact:** Sharon Cunane (scunane@cars.com) — billing/operations
- **Billing file:** `~/Documents/Reports/SonicAutomotive/Sonic Billing Files-{Month} {Year}.xlsx`
- **Tableau workbook:** Cars Monthly Marketplace Dealer Health Metrics (ID: 1792343)
- **gspread token:** `~/.claude/tokens/sheets_credentials.json`
- **Porsche UUIDs (known):**
  - Porsche Bethesda: 58980917-f29d-5b36-97b9-23c901b28942
  - Porsche Birmingham: 71172a89-0310-5446-ae95-1a8f2d857b84
  - Porsche of Nashville: 1e521c7c-b5b4-5202-9899-94a7d438a8ab
  - Porsche River Oaks: 1da18bfa-c58a-52e5-b42e-cda3d2b816f8
  - Porsche West Houston: a9aefa07-0f2a-5c98-9642-eff42d286a75
- **Admin.cars.com UUIDs:** Discover via search, cache in memory file as found
- **Related skills:** `/sonic-billing` (monthly billing pivot), `/dealer-marketshareanalysis` (demand score), `/auto-research` (deep dive playbooks)
- **Schedule:** Monthly, manually triggered — luxury rotation odd months, volume rotation even months
