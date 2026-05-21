# Investigate Stores — /investigate-stores

Unified investigation workflow. Accepts any scope — one store, a list, or an entire group — with optional timeframe and focus filters. Uses `investigation_triggers.py` as the detection engine and routes output based on intent.

---

## Usage

```
/investigate-stores sonic bmw
/investigate-stores aca
/investigate-stores 109754,25732,12070
/investigate-stores Nalley Lexus Galleria
/investigate-stores hendrick --focus connections
/investigate-stores sonic --since 90d
/investigate-stores sonic bmw --brief
/investigate-stores aca --export
/investigate-stores all --triage
```

---

## Input Parsing

Parse the user's input to extract:

| Token | Type | Examples |
|---|---|---|
| All-digits, comma-separated | CCID list | `109754,25732` |
| Known group keyword | Group name | `sonic`, `aca`, `hendrick`, `asbury`, `herb`, `greenway`, `koons`, `echopark`, `indigo` |
| Group + brand filter | Group + brand | `sonic bmw`, `sonic honda`, `hendrick lexus` |
| Any other string | Store name → SF lookup | `Nalley Lexus Galleria` |
| `all` | Full book scan | All accessible groups |

**Flags (all optional):**
| Flag | Default | Meaning |
|---|---|---|
| `--triage` | default | Prioritized flag list with next steps |
| `--brief` | off | Add /prep-style talking points for each HIGH store |
| `--report` | off | Email-ready group summary (for group scopes only) |
| `--export` | off | Save output to `~/Documents/Reports/InvestigationScans/` |
| `--focus {area}` | all | Filter to specific scenario: `connections`, `vdps`, `demand`, `merch`, `cost` |
| `--since {period}` | CP vs PP | Extend to multi-month context: `30d`, `60d`, `90d` |

If no flags given, default to `--triage`.

---

## Step 1 — Resolve Scope

### CCID list

Use directly. Optionally run a quick SF lookup to get store names:
```
SELECT Name, CCID__c, BillingCity, BillingState
FROM Account
WHERE CCID__c IN ('{ccid1}', '{ccid2}', ...)
```

### Store name

SF fuzzy lookup:
```
SELECT Name, CCID__c, BillingCity, BillingState, Account_Status__c
FROM Account
WHERE Name LIKE '%{input}%'
ORDER BY Name LIMIT 5
```

If multiple results, show list and ask user to confirm. If one result, proceed.

### Group name (or group + brand)

Map to Tableau filter value:

```python
GROUP_FILTERS = {
    "sonic":      "Sonic",
    "aca":        "Atlantic Coast Automotive MA Group",
    "hendrick":   "Hendrick Automotive Group",
    "asbury":     "Asbury",
    "herb":       "Herb Chambers MA Group",
    "greenway":   "Greenway MA Group",
    "koons":      "Koons Automotive MA Group",
    "echopark":   "EchoPark MA Group",
    "indigo":     "Indigo Auto MA Group",
    "doherty":    "Doherty MA Group",
    "jim_ellis":  "Jim Ellis MA Group",
    "larry_miller": "Larry Miller",
}
```

If a brand filter was specified (e.g., `sonic bmw`), store it as `brand_filter = "BMW"` — applied after Tableau pull.

### `all`

Pull each group separately and concatenate. Order: Sonic → Hendrick → ACA → Asbury → Herb → Greenway → Koons → EchoPark → Indigo → Doherty. Skip any group that returns 0 rows (silent RLS). Report which groups were included in the output header.

---

## Step 2 — Pull Tableau Data

For each group in scope, pull from the By Store view using the REST API:

```bash
TOKEN=$(curl -s -X POST "https://us-west-2b.online.tableau.com/api/3.22/auth/signin" \
  -H "Content-Type: application/json" \
  -d '{"credentials":{"personalAccessTokenName":"Claude","personalAccessTokenSecret":"'$TABLEAU_PAT_SECRET'","site":{"contentUrl":"cars"}}}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['credentials']['token'])")

curl -s "https://us-west-2b.online.tableau.com/api/3.22/sites/12338861-20b1-46ed-8841-269a5a937edb/views/a0b9bdce-2db3-4ea0-a2fc-365fd08c5786/data?vf_Maj%20Cust%20Name={filter_val}" \
  -H "X-Tableau-Auth: $TOKEN" > /tmp/inv_raw_{group}.csv
```

**Key gotchas:**
- Omit `Accept: text/csv` header — returns 406
- Filter value is `Sonic` not `Sonic Automotive Group`
- Data is long format (Measure Names / Measure Values) — pivot before passing to triggers

**Pivot to wide format:**
```python
import csv, io, sys, os
sys.path.insert(0, os.path.expanduser("~/Documents/scripts"))

stores = {}
for row in csv.DictReader(io.StringIO(raw_csv)):
    name = row.get("Customer Name", "").strip()
    if not name:
        continue
    ccid = row.get("Legacy Id", "").strip()
    # Apply CCID or brand filter if set
    if ccid_filter and ccid not in ccid_filter:
        continue
    if brand_filter:
        group_name = row.get("Group Cust Name", "")
        # Brand filter: match group name contains brand keyword
        # e.g. brand_filter="BMW" matches "BMW of Nashville", "Stevens Creek BMW"
        if brand_filter.lower() not in name.lower():
            continue
    if name not in stores:
        stores[name] = {
            "Customer Name": name,
            "Legacy Id": ccid,
            "Maj Cust Name": row.get("Maj Cust Name", ""),
            "Group Cust Name": row.get("Group Cust Name", ""),
        }
    measure = row.get("Measure Names", "").strip()
    value   = row.get("Measure Values", "").strip()
    if measure:
        stores[name][measure] = value

stores_list = list(stores.values())
```

If a specific CCID has no Tableau data after pulling all accessible groups, note: `"[Store Name]: Tableau — no data (outside PAT scope)"`.

---

## Step 3 — Multi-Month Context (if `--since` specified)

When `--since 30d / 60d / 90d` is requested, supplement CP/PP data with historical data from the rolling Google Sheets tabs where available.

For groups with monthly reporting sheets:
- **Sonic:** `Brand Overview` tab (one row per brand per month)
- **ACA:** `Monthly Overview` tab (one row per month)

Pull the relevant months and compute trend direction for each store:
- "2+ consecutive months declining" → escalate to HIGH if currently MEDIUM
- "recovering after 2+ months declining" → note as "Recovering" in signal
- "3+ consecutive months declining" → prefix flag with `[SUSTAINED]`

If historical sheets aren't available for the group, note "Trend context: CP vs PP only (no rolling sheet for this group)" and proceed with single-period data.

---

## Step 4 — Run Investigation Triggers

```python
from investigation_triggers import investigate_stores, format_triage_report, SCENARIO_META

results = investigate_stores(stores_list)
```

**Apply focus filter if set:**

```python
FOCUS_MAP = {
    "connections": {1},
    "vdps":        {3},
    "demand":      {4},
    "merch":       {2},
    "cost":        {5},
}

if focus_filter:
    allowed = FOCUS_MAP.get(focus_filter, set())
    for bucket in ["high", "medium"]:
        for entry in results[bucket]:
            entry["flags"] = [f for f in entry["flags"] if f["scenario"] in allowed]
        results[bucket] = [e for e in results[bucket] if e["flags"]]
```

---

## Step 5 — Format Output

### Always: Print the triage header

```
══════════════════════════════════════════════════════════════════
  INVESTIGATION SCAN  |  {Scope Label}  |  {Today's Date}
  {store_count} stores analyzed  |  {timeframe note}
══════════════════════════════════════════════════════════════════

{N} store(s) flagged  ({HIGH} HIGH · {MED} MEDIUM)
{B} bright spot(s)  |  {C} clean

```

Then print the full `format_triage_report()` output.

---

### `--brief` mode (add after triage)

For each HIGH store (up to 5), generate a condensed /prep-style brief:

```
──────────────────────────────────────────────────────────────────
  BRIEF: {Store Name}  ({City, State if available})  CCID {ccid}
──────────────────────────────────────────────────────────────────
Flags:   {scenario name}: {signal}  [each flag on its own line]

TALKING POINTS
  1. [Win / opener using specific metric from the data]
  2. [Opportunity — highest-priority flag framed as revenue impact]
  3. [Next step / question tied to a specific admin.cars.com report]
```

Generate talking points using the store's flag signals + metric values. Each talking point must use actual numbers. Revenue-frame TP2 even if rough.

---

### `--report` mode (group scopes only)

Produce a concise email-ready summary structured as:

```
Subject: {Group} — {Month} Investigation Scan

{N} stores reviewed across {group}.

WATCH LIST — {HIGH count} stores need attention this month:
  • {Store} — {primary scenario}: {signal}
  • ...  (max 5)

BRIGHT SPOTS — {B count} stores showing positive momentum:
  • {Store} — VDPs {delta} + Connections {delta}
  • ...  (max 3)

Top pattern this month: {Claude-synthesized 1-sentence read across all flags}

Full triage available in: ~/Documents/Reports/InvestigationScans/{scope}_{date}.txt
```

In `--report` mode, always also `--export` the full triage automatically.

---

### `--export` mode

Save the full triage output to:
```
~/Documents/Reports/InvestigationScans/{scope_slug}_{YYYY-MM-DD}.txt
```

Where `scope_slug` is the group name, a CCID list (truncated if >3 CCIDs: `{ccid1}_{ccid2}_and_{N}_more`), or store name slug.

Print the save path after output.

---

## Step 6 — Post-Scan Options

After output, offer next actions based on what was found:

```
What next?
  [1] Run /prep brief for a specific flagged store
  [2] Pull Demand Signals for top flagged store (requires admin SSO)
  [3] Run /auto-research deep dive on {top flagged store}
  [4] Re-run with different focus (connections / vdps / demand / merch / cost)
  [5] Export this scan
  [Enter] Done
```

---

## Failure Handling

| Failure | Action |
|---|---|
| Tableau auth fails (401) | Run `/recover/tableau-401`, then retry |
| Group returns 0 rows | Note `"{group}: no data (outside PAT scope)"`, continue with others |
| SF lookup returns 0 results | Ask user to try CCID directly |
| investigation_triggers import error | Print Python traceback summary + path check for `~/Documents/scripts/investigation_triggers.py` |
| `all` scope returns 0 total stores | Abort: "No accessible groups — check Tableau PAT and retry" |

---

## Key Reference

- **By Store view ID:** `a0b9bdce-2db3-4ea0-a2fc-365fd08c5786`
- **AE Insights view ID:** `a60dbfc3-0156-4728-884a-fec77a3b7d2c` (no RLS — all dealers, use if By Store returns nothing)
- **Tableau host:** `https://us-west-2b.online.tableau.com`
- **Site ID:** `12338861-20b1-46ed-8841-269a5a937edb`
- **investigation_triggers:** `~/Documents/scripts/investigation_triggers.py`
- **Export path:** `~/Documents/Reports/InvestigationScans/`
- **Related skills:** `/prep` (single store brief), `/auto-research` (deep dive), `/sonic-monthly-report`, `/aca-monthly-report`
- **Flows into:** `/prep --brief` for talking points, `/auto-research` for root cause deep dive
