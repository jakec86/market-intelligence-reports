# Pre-Call Briefing — /prep

Generate a 60-second call prep brief for any dealer. Pulls account, metrics, flags, and reputation in parallel then produces 3 ready-to-use talking points.

**Usage:**
```
/prep Nalley Lexus Galleria
/prep 109754
/prep Stevens Creek BMW
```

---

## What This Produces

A single structured brief covering:
- Account snapshot (products, MRR, status)
- Current period metrics vs. prior month
- Active investigation flags (from investigation_triggers)
- Reputation (DealerRater rating + review velocity)
- 3 talking points generated from the data

Target: complete in under 90 seconds. Never block waiting for admin.cars.com SSO — mark that section as "available via /auto-research" and move on.

---

## Steps

### Step 1 — Resolve the Dealer

Determine if input is a CCID (all digits) or dealer name.

**If CCID:** query SF directly.

**If name:** run a fuzzy SF name lookup:
```
SELECT Id, Name, CCID__c, BillingCity, BillingState, Account_Status__c
FROM Account
WHERE Name LIKE '%{input}%'
ORDER BY Name
LIMIT 5
```

If multiple results, show the list and ask the user to confirm which one. If only one result, proceed.

Capture: `dealer_name`, `ccid`, `sf_id`, `billing_city`, `billing_state`, `account_status`.

---

### Step 2 — Parallel Data Pulls

Run all four pulls simultaneously. Each is independent — failures are non-blocking.

#### 2a. Salesforce — Products & MRR

```
SELECT SBQQ__ProductName__c, SBQQ__NetPrice__c, SBQQ__SubscriptionEndDate__c
FROM SBQQ__Subscription__c
WHERE SBQQ__Account__r.CCID__c = '{ccid}'
AND SBQQ__SubscriptionEndDate__c > TODAY
ORDER BY SBQQ__NetPrice__c DESC
```

Extract: active product names, total MRR (sum of `SBQQ__NetPrice__c`), any products expiring within 90 days.

If SF subscription query fails, fall back to:
```
SELECT Products__c, Product_Amount__c FROM Account WHERE CCID__c = '{ccid}'
```

#### 2b. Tableau — Current Period Metrics

Pull from the By Store view using the Tableau REST API:

```bash
TOKEN=$(curl -s -X POST "https://us-west-2b.online.tableau.com/api/3.22/auth/signin" \
  -H "Content-Type: application/json" \
  -d '{"credentials":{"personalAccessTokenName":"Claude","personalAccessTokenSecret":"'$TABLEAU_PAT_SECRET'","site":{"contentUrl":"cars"}}}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['credentials']['token'])")

curl -s "https://us-west-2b.online.tableau.com/api/3.22/sites/12338861-20b1-46ed-8841-269a5a937edb/views/a0b9bdce-2db3-4ea0-a2fc-365fd08c5786/data" \
  -H "X-Tableau-Auth: $TOKEN" > /tmp/prep_tableau_raw.csv
```

The view returns all stores accessible to the PAT. Filter client-side by `Legacy Id == ccid`.

Parse into a store dict and run investigation triggers:

```python
import sys, csv, io, json
sys.path.insert(0, os.path.expanduser("~/Documents/scripts"))
from investigation_triggers import investigate_stores, format_triage_report, _delta, _get, _pct

raw = open("/tmp/prep_tableau_raw.csv").read()
stores = {}
for row in csv.DictReader(io.StringIO(raw)):
    if row.get("Legacy Id", "").strip() != ccid:
        continue
    name = row["Customer Name"]
    if name not in stores:
        stores[name] = {"Customer Name": name, "Legacy Id": ccid}
    stores[name][row["Measure Names"].strip()] = row["Measure Values"]

store_list = list(stores.values())
tableau_ok = len(store_list) > 0

if tableau_ok:
    store = store_list[0]
    flags = investigate_stores(store_list)
    metrics = {
        "vdps_cp":   _get(store, "vdp_cp"),
        "vdps_delta": _delta(store, "vdp_cp", "vdp_pp", "vdp_delta"),
        "conn_cp":   _get(store, "conn_cp"),
        "conn_delta": _delta(store, "conn_cp", "conn_pp", "conn_delta"),
        "inv_cp":    _get(store, "inv_cp"),
        "inv_delta":  _delta(store, "inv_cp", "inv_pp", "inv_delta"),
        "cost_lead":  _get(store, "cost_lead_cp"),
    }
```

If Tableau returns no rows for this CCID, note "Tableau: no data (RLS or store not in PAT scope)" and continue.

#### 2c. DealerRater — Rating & Review Velocity

WebFetch `https://www.dealerrater.com/dealer/{slug}/` — the slug is usually the dealer name lowercased with hyphens.

If the slug isn't known, search: `https://www.dealerrater.com/search/?q={dealer_name}`

Extract: overall star rating, total review count, reviews in last 30 days. If WebFetch fails or returns no data, note "DealerRater: unavailable" and continue.

#### 2d. Memory Context

Read `~/.claude/projects/-Users-jcrawley/memory/auto_research_learnings.md` and search for any entries referencing this dealer name or CCID. Pull any dealer-specific patterns or prior session notes.

---

### Step 3 — Format the Brief

Output a clean, scannable brief. No markdown headers — use ASCII dividers for terminal readability.

```
══════════════════════════════════════════════════════════════════
  CALL PREP  |  {Dealer Name}  |  {City, State}  |  {Today's Date}
══════════════════════════════════════════════════════════════════

ACCOUNT
  CCID:       {ccid}
  Status:     {account_status}
  Products:   {comma-separated product names}
  MRR:        ${total_mrr:,.0f}/mo
  ⚠ Expiring: {product} in {N} days   ← only if within 90 days

METRICS  (current period vs. prior month)
  VDPs:         {vdps_cp:,}   ({vdps_delta:+.1%})
  Connections:  {conn_cp:,}   ({conn_delta:+.1%})
  Inventory:    {inv_cp:.0f} avg/day  ({inv_delta:+.1%})
  Cost/Lead:    ${cost_lead:.0f}
                           ← "Tableau: no data" if pull failed

FLAGS  ({N} active)
  {format_triage_report output, condensed — scenario + signal only, no next-steps}
  ✓ No flags   ← if clean

REPUTATION
  DealerRater:  {rating}★  ({total_reviews:,} reviews, +{last_30} last 30 days)
                           ← "unavailable" if fetch failed

PRIOR CONTEXT
  {1-2 sentences from memory if found, else omit this section}

──────────────────────────────────────────────────────────────────
TALKING POINTS
──────────────────────────────────────────────────────────────────
```

After printing the data sections, generate the talking points using Claude — pass all gathered data as context and produce exactly 3 talking points:

**Talking point structure:**
1. **Win / opener** — lead with a specific positive data point. Frame as recognition, not report delivery. ("Your VDPs are up 8% — shoppers are engaging more with your inventory this month.")
2. **Opportunity** — the highest-priority flag or gap, framed as revenue impact. ("Stores at your inventory level typically see 15-20% more connections when badge % is above 70%. You're at 54% — that's roughly X leads/month left on the table.")
3. **Next step / question** — a specific action or question that moves something forward. Tie to a product, report, or conversation. ("Have you had a chance to look at the Demand Signals report? I want to walk you through where your mix may be diverging from what local shoppers are searching for.")

**Talking point rules:**
- Use actual numbers from the data — never generic observations
- Revenue-frame the opportunity (estimate impact even if rough)
- The question in TP3 should be genuinely curious, not a setup for a pitch
- If no flags exist, find the best growth opportunity from the metrics instead
- Vary the opener style each run — don't always lead with VDPs

---

### Step 4 — Post-Brief Options

After printing the brief, offer:

```
Options:
  [1] Run full /auto-research deep dive
  [2] Pull admin.cars.com Performance Trends (requires SSO)
  [3] Check Demand Signals for inventory/demand mismatch
  [4] Save this brief to ~/Documents/Reports/PrepBriefs/{dealer_name}_{date}.txt
  [Enter] Done
```

Wait for user selection. If they choose [4], write the formatted brief to the file path. Otherwise close.

---

## Failure Handling

| What fails | Action |
|---|---|
| SF name lookup returns 0 results | Ask user to try a different name or provide CCID directly |
| SF subscription query fails | Fall back to `Products__c` field on Account object |
| Tableau returns no rows for CCID | Note inline — continue with other data |
| DealerRater fetch fails | Note "unavailable" — don't retry |
| investigation_triggers import fails | Note inline — skip flags section |
| All data pulls fail | Abort with: "Could not pull data — check SF/Tableau auth and retry" |

Never show stack traces to the user. Summarize failures in one line in the relevant section.

---

## Key Reference

- **Tableau By Store view:** `a0b9bdce-2db3-4ea0-a2fc-365fd08c5786` (RLS-filtered to PAT scope)
- **AE Insights view:** `a60dbfc3-0156-4728-884a-fec77a3b7d2c` (no RLS — all dealers, use if By Store returns nothing)
- **investigation_triggers:** `~/Documents/scripts/investigation_triggers.py`
- **Tableau host:** `https://us-west-2b.online.tableau.com`
- **SF CLI:** `~/.npm-global/bin/sf --target-org cars-commerce`
- **Brief save path:** `~/Documents/Reports/PrepBriefs/`
- **Related skills:** `/auto-research` (deep dive), `/dealer-marketshareanalysis` (demand analysis), `/investigate-stores` (book-of-business scan)
