# Hendrick Monthly Brand Performance Report — Monthly Workflow

Run the monthly Hendrick Automotive Group brand performance report. Produces per-brand email drafts with store scorecards, market context, and actionable deep dives.

---

> **⚠️ PRE-SEND REVIEW RULE:** All Gmail drafts must be addressed To: `jcrawley@cars.com` first. Do not use client recipient addresses until Jake reviews the format and gives explicit approval. This applies to every draft created by this skill.


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

**Primary contact (all emails — until brand managers confirmed):** Anne Lewis — `anne.Lewis@hendrickauto.com`

All drafts currently route to Anne with `[TEST]` prefix. When Hendrick brand managers are identified, swap recipients below per brand.

```yaml
RECIPIENTS:
  default_to: anne.Lewis@hendrickauto.com

  BMW:           {to: [anne.Lewis@hendrickauto.com], cc: []}
  Acura:         {to: [anne.Lewis@hendrickauto.com], cc: []}
  Audi:          {to: [anne.Lewis@hendrickauto.com], cc: []}
  Lexus:         {to: [anne.Lewis@hendrickauto.com], cc: []}
  Mercedes_Benz: {to: [anne.Lewis@hendrickauto.com], cc: []}
  Porsche:       {to: [anne.Lewis@hendrickauto.com], cc: []}
  Honda:         {to: [anne.Lewis@hendrickauto.com], cc: []}
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

---

## SAM Assignments (Cars Commerce Internal)

GAE = Growth Account Executive · Sr. Ad Mgr = Senior Advertising Manager  
Used for internal routing, investigation consultations, and flagged-store follow-up — **not copied on client emails unless instructed.**

```yaml
SAM_ASSIGNMENTS:
  # ── Dwight Pope (25 stores) ────────────────────────────────────────────
  "Audi Northlake":                              {gae: "Dwight Pope",        sr_ad_mgr: "Tyler Marovich"}
  "Hendrick Acura":                              {gae: "Dwight Pope",        sr_ad_mgr: "Abby Livingston"}
  "Hendrick BMW":                                {gae: "Dwight Pope",        sr_ad_mgr: "Tyler Marovich"}
  "Hendrick BMW Certified Pre-Owned South Charlotte": {gae: "Dwight Pope",   sr_ad_mgr: "Tyler Marovich"}
  "Hendrick BMW Northlake":                      {gae: "Dwight Pope",        sr_ad_mgr: "Tyler Marovich"}
  "Hendrick Chevrolet Cadillac":                 {gae: "Dwight Pope",        sr_ad_mgr: "Tim Webster"}
  "Hendrick Chrysler Dodge Jeep Ram FIAT of Concord": {gae: "Dwight Pope",   sr_ad_mgr: "Kim Kirchner"}
  "Hendrick Honda":                              {gae: "Dwight Pope",        sr_ad_mgr: "Krystal Hines"}
  "Hendrick Honda Hickory":                      {gae: "Dwight Pope",        sr_ad_mgr: "Krystal Hines"}
  "Hendrick Honda of Charleston":                {gae: "Dwight Pope",        sr_ad_mgr: "Kim Kirchner"}
  "Hendrick Honda of Easley":                    {gae: "Dwight Pope",        sr_ad_mgr: "Krystal Hines"}
  "Hendrick Kia of Concord":                     {gae: "Dwight Pope",        sr_ad_mgr: "Robert Weisbach"}
  "Hendrick Lexus Kansas City":                  {gae: "Dwight Pope",        sr_ad_mgr: "Mike Judge"}    # Note: sheet shows Blake Hoeber; confirm
  "Hendrick MINI":                               {gae: "Dwight Pope",        sr_ad_mgr: "Mike Judge"}
  "Hendrick Motors of Charlotte":                {gae: "Dwight Pope",        sr_ad_mgr: "Mike Judge"}
  "Hendrick Porsche":                            {gae: "Dwight Pope",        sr_ad_mgr: "Abby Livingston"}
  "Hendrick Toyota North Charleston":            {gae: "Dwight Pope",        sr_ad_mgr: "Kim Kirchner"}
  "Hendrick Toyota Merriam":                     {gae: "Blake Hoeber",       sr_ad_mgr: "Kim Kirchner"}
  "Hendrick Volkswagen of Concord":              {gae: "Dwight Pope",        sr_ad_mgr: "Krystal Hines"}
  "Hendrick Volvo Cars of Charleston":           {gae: "Dwight Pope",        sr_ad_mgr: "Tyler Marovich"}
  "Honda Cars of Rock Hill":                     {gae: "Dwight Pope",        sr_ad_mgr: "Kim Kirchner"}
  "Honda of Concord":                            {gae: "Dwight Pope",        sr_ad_mgr: "Robert Weisbach"}
  "Mercedes-Benz of Northlake":                  {gae: "Dwight Pope",        sr_ad_mgr: "Mike Judge"}
  "Rick Hendrick BMW Charleston":                {gae: "Dwight Pope",        sr_ad_mgr: "Tyler Marovich"}
  "Rick Hendrick Chevrolet Charleston":          {gae: "Dwight Pope",        sr_ad_mgr: "Virginia Shields"}
  "Rick Hendrick City Chevrolet":                {gae: "Dwight Pope",        sr_ad_mgr: "Julia Rowe"}
  "Rick Hendrick Toyota of Fayetteville":        {gae: "Dwight Pope",        sr_ad_mgr: "Kim Kirchner"}

  # ── Andy Allen (14 stores) ─────────────────────────────────────────────
  "Barbour-Hendrick Honda Greenville":           {gae: "Andy Allen",         sr_ad_mgr: "Krystal Hines"}
  "BMW of Southpoint":                           {gae: "Andy Allen",         sr_ad_mgr: "Tyler Marovich"}
  "Hendrick Cadillac Cary":                      {gae: "Andy Allen",         sr_ad_mgr: "Virginia Shields"}
  "Hendrick Chevrolet Buick GMC Southpoint":     {gae: "Andy Allen",         sr_ad_mgr: "Virginia Shields"}
  "Hendrick Chrysler Jeep FIAT":                 {gae: "Andy Allen",         sr_ad_mgr: "Reilly Jackson"}
  "Hendrick Kia of Cary":                        {gae: "Andy Allen",         sr_ad_mgr: "Virginia Shields"}
  "Hendrick Southpoint Auto Mall":               {gae: "Andy Allen",         sr_ad_mgr: "Abby Livingston"}
  "Mercedes-Benz of Durham":                     {gae: "Andy Allen",         sr_ad_mgr: "Mike Judge"}
  "Porsche Southpoint":                          {gae: "Andy Allen",         sr_ad_mgr: "Abby Livingston"}
  "Reggie Jackson Airport Honda":                {gae: "Andy Allen",         sr_ad_mgr: "Kim Kirchner"}
  "Stevenson Hendrick Mazda Wilmington":         {gae: "Andy Allen",         sr_ad_mgr: "Tim Webster"}
  "Stevenson-Hendrick Honda Jacksonville":       {gae: "Andy Allen",         sr_ad_mgr: "Kim Kirchner"}
  "Stevenson-Hendrick Honda Wilmington":         {gae: "Andy Allen",         sr_ad_mgr: "Krystal Hines"}
  "Terry Labonte Chevrolet":                     {gae: "Andy Allen",         sr_ad_mgr: "Virginia Shields"}

  # ── Dana Aderhold (11 stores) ──────────────────────────────────────────
  "BMW of Murrieta":                             {gae: "Dana Aderhold",      sr_ad_mgr: "Abby Livingston"}
  "Gwinnett Place Honda":                        {gae: "Dana Aderhold",      sr_ad_mgr: "Krystal Hines"}
  "Hendrick Chevrolet":                          {gae: "Dana Aderhold",      sr_ad_mgr: "Julia Rowe"}
  "Hendrick Chrysler Dodge Jeep Ram Hoover":     {gae: "Dana Aderhold",      sr_ad_mgr: "Tim Webster"}
  "Hendrick Subaru":                             {gae: "Dana Aderhold",      sr_ad_mgr: "Tim Webster"}
  "Honda of Newnan":                             {gae: "Dana Aderhold",      sr_ad_mgr: "Krystal Hines"}
  "Mall of Georgia Mazda":                       {gae: "Dana Aderhold",      sr_ad_mgr: "Tim Webster"}
  "Mall of Georgia MINI":                        {gae: "Dana Aderhold",      sr_ad_mgr: "Tim Webster"}
  "Rick Hendrick Buick GMC":                     {gae: "Dana Aderhold",      sr_ad_mgr: "Virginia Shields"}
  "Rick Hendrick Chevrolet of Buford":           {gae: "Dana Aderhold",      sr_ad_mgr: "Tim Webster"}
  "Rick Hendrick Chrysler Dodge Jeep RAM Duluth": {gae: "Dana Aderhold",     sr_ad_mgr: "Tim Webster"}

  # ── Blake Hoeber (5 stores) ────────────────────────────────────────────
  "BMW of Kansas City South":                    {gae: "Blake Hoeber",       sr_ad_mgr: "Tyler Marovich"}
  "Hendrick Chevrolet Shawnee Mission":          {gae: "Blake Hoeber",       sr_ad_mgr: "Tim Webster"}
  "Hendrick Lexus Kansas City North":            {gae: "Blake Hoeber",       sr_ad_mgr: "Mike Judge"}
  "Hendrick Volkswagen Frisco":                  {gae: "Chris Sadafsaz",     sr_ad_mgr: "Krystal Hines"}

  # ── Other GAEs ─────────────────────────────────────────────────────────
  "Audi South Austin":                           {gae: "Jaye Skidmore",      sr_ad_mgr: "Tyler Marovich"}
  "BMW of South Austin":                         {gae: "Jaye Skidmore",      sr_ad_mgr: "Tyler Marovich"}
  "Acura of Pleasanton":                         {gae: "Lisa Castro",        sr_ad_mgr: "Mike Judge"}
  "East Bay BMW":                                {gae: "Lisa Castro",        sr_ad_mgr: "Tyler Marovich"}
  "Dale Earnhardt Jr. Buick GMC Cadillac":       {gae: "Brenda Ashley",      sr_ad_mgr: "Tim Webster"}
  "Dale Earnhardt Jr. Chevrolet":                {gae: "Brenda Ashley",      sr_ad_mgr: "Tim Webster"}
  "Darrell Waltrip Buick GMC":                   {gae: "Jimmy Johnson",      sr_ad_mgr: "Abby Livingston"}
  "Darrell Waltrip Honda":                       {gae: "Jimmy Johnson",      sr_ad_mgr: "Abby Livingston"}
  "Darrell Waltrip Subaru":                      {gae: "Jimmy Johnson",      sr_ad_mgr: "Abby Livingston"}
  "Honda Cars of McKinney":                      {gae: "Chris Sadafsaz",     sr_ad_mgr: "Krystal Hines"}
  "Hendrick Honda Bradenton":                    {gae: "Rick Castillo",      sr_ad_mgr: "Krystal Hines"}
  "Rick Hendrick Chevrolet of Duluth":           {gae: "Jennifer Carbonell", sr_ad_mgr: "Tim Webster"}
  "Volkswagen of Murrieta":                      {gae: "Manny Sandoval",     sr_ad_mgr: "Krystal Hines"}
  "Rick Hendrick Honda":                         {gae: "",                   sr_ad_mgr: "Kim Kirchner"}
  "BMW of McKinney":                             {gae: "",                   sr_ad_mgr: "Tyler Marovich"}
  "Rick Hendrick Jeep Chrysler Dodge RAM North Charleston": {gae: "",        sr_ad_mgr: "Virginia Shields"}
  "Rick Hendrick Dodge Chrysler Jeep RAM Charleston": {gae: "",              sr_ad_mgr: "Virginia Shields"}
```

### SAM Coverage by Sr. Ad Mgr

| Sr. Ad Mgr | Brands/Focus | Used for |
|---|---|---|
| **Krystal Hines** | Honda, VW, some Subaru | Volume account consults |
| **Tyler Marovich** | BMW, Audi, Volvo, VW | Luxury/import consults |
| **Tim Webster** | Chevy, Buick/GMC, CDJR, Mazda, Subaru | Domestic/volume consults |
| **Kim Kirchner** | Honda (SC/FL), CDJR (Concord), Toyota | Southeast consults |
| **Mike Judge** | Lexus, Acura, MB, Porsche, MINI | Luxury consults |
| **Abby Livingston** | Porsche, BMW (Murrieta/DW), Darrell Waltrip | Mixed luxury/import |
| **Virginia Shields** | Buick/GMC, Chevy (NC/VA), Kia | Southeast domestic |
| **Julia Rowe** | Chevy (City, Buford area) | Volume southeast |
| **Robert Weisbach** | Kia Concord, Honda of Concord | Concord market |
| **Reilly Jackson** | CDJR Fayetteville area | FIAT/CDJR specialist |

### Using SAM Data in Reports

When a store is flagged HIGH or has an investigation flag:
1. Note the GAE and Sr. Ad Mgr in the internal triage output
2. If reaching out for deeper analysis, loop in the GAE by name in internal notes
3. The `format_triage_report()` output can include SAM context:
   ```
   🔵 [HIGH/SUSTAINED] Hendrick Honda Hickory  (CCID 10023)
      GAE: Dwight Pope · Sr. Ad Mgr: Krystal Hines
      Scenario 1: Connections -18% MoM
   ```
4. **Client-facing emails (to Anne) do not include SAM names** unless instructed

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
print(format_triage_report(brand_results, title=f"Hendrick {brand} — {month} {year}",
                           show_sams=True))  # surfaces GAE + Sr. Ad Mgr on each flagged store
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
