"""
investigation_dashboard.py — Investigation Workflow Dashboard

Interactive fleet-level investigation tool. Select a scope (store, group, or
full book), run the scan, click any flagged store for an instant prep brief
and Claude-generated talking points.

Run:
    python3 -m streamlit run ~/Documents/scripts/investigation_dashboard.py
"""

import csv
import io
import json
import os
import re as _re
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request
from datetime import date, datetime
from typing import Dict, List, Optional

import pandas as pd
import streamlit as st

sys.path.insert(0, os.path.dirname(__file__))
from investigation_triggers import (
    investigate_stores,
    _get,
    _delta,
    _pct,
    SCENARIO_META,
    THRESHOLDS,
)
from health_analysis import (
    fetch_salesforce, fetch_salesforce_by_ccid, fetch_subscriptions,
    build_data_context, parse_scores, render_score_bars,
    run_health_analysis, create_health_doc,
)
import admin_cars as _admin_cars

# ─── BRANDING ─────────────────────────────────────────────────────────────────

CC_CSS = """
<style>
  @import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,500;0,9..40,700&display=swap');
  html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
  .block-container { padding-top: 1.5rem; }
  div[data-testid="stStatusWidget"] { visibility: hidden; }

  /* Header */
  .cc-brand  { font-size: 0.72rem; letter-spacing: 0.18em; text-transform: uppercase;
               color: #5B2D8E; font-weight: 700; }
  .cc-title  { font-size: 1.9rem; font-weight: 700; color: #111827; margin: 0; line-height: 1.15; }
  .cc-sub    { color: #6b7280; font-size: 0.9rem; margin: 0.1rem 0 0.2rem; }
  .cc-accent { height: 4px; background: linear-gradient(90deg,#5B2D8E 0%,#00A88E 100%);
               margin: 0 0 1rem; border-radius: 2px; }

  /* KPI tiles */
  .kpi-grid  { display: flex; gap: 12px; margin-bottom: 1.2rem; flex-wrap: wrap; }
  .kpi-tile  { flex: 1; min-width: 110px; background: white; border: 1px solid #ede9fb;
               border-radius: 10px; padding: 14px 18px; box-shadow: 0 1px 4px rgba(0,0,0,.06); }
  .kpi-val   { font-size: 2rem; font-weight: 700; color: #5B2D8E; line-height: 1; }
  .kpi-lbl   { font-size: 0.72rem; text-transform: uppercase; letter-spacing: .06em;
               color: #9ca3af; margin-top: 3px; }
  .kpi-tile.alert .kpi-val { color: #c0392b; }
  .kpi-tile.teal  .kpi-val { color: #00A88E; }

  /* Trend badges */
  .badge { display:inline-block; padding:2px 8px; border-radius:4px;
           font-size:11px; font-weight:700; letter-spacing:.04em; }
  .badge-CRITICAL { background:#fdecea; color:#c0392b; }
  .badge-SUSTAINED{ background:#fef3c7; color:#d97706; }
  .badge-NEW      { background:#dbeafe; color:#2563eb; }
  .badge-RESOLVED { background:#d1fae5; color:#059669; }

  /* Store brief card */
  .brief-card { background:white; border:1px solid #ede9fb; border-radius:10px;
                padding:20px 24px; margin-top:8px; }
  .brief-meta { font-size:0.8rem; color:#9ca3af; margin-bottom:12px; }
  .flag-chip  { display:inline-block; margin:2px 4px 2px 0; padding:3px 9px;
                border-radius:4px; font-size:12px; font-weight:600; }
  .chip-HIGH  { background:#fdecea; color:#c0392b; }
  .chip-MED   { background:#fef3c7; color:#d97706; }

  /* Talking points */
  .tp-block   { border-left:3px solid #5B2D8E; padding:8px 14px; margin:8px 0;
                background:#f9f7fd; border-radius:0 6px 6px 0; font-size:0.88rem; }
  .tp-num     { font-weight:700; color:#5B2D8E; margin-bottom:2px; }

  /* Quick links */
  .qlink a    { display:inline-block; margin:4px 6px 0 0; padding:4px 12px;
                background:#f3f0fc; color:#5B2D8E; border-radius:6px;
                font-size:12px; font-weight:600; text-decoration:none; }
  .qlink a:hover { background:#ede9fb; }

  /* Sidebar */
  section[data-testid="stSidebar"] h2 {
    color:#5B2D8E; border-left:3px solid #5B2D8E; padding-left:8px; }
  section[data-testid="stSidebar"] .stButton button {
    width:100%; }
</style>
"""

HEADER_HTML = """
<div class="cc-brand">Cars.com · Growth Insights</div>
<h1 class="cc-title">Investigation Workflow Dashboard</h1>
<p class="cc-sub">Fleet-level investigation · Pre-call briefs · Talking points</p>
<div class="cc-accent"></div>
"""

# ─── CONFIG ───────────────────────────────────────────────────────────────────

TABLEAU_HOST    = "https://us-west-2b.online.tableau.com"
SITE_ID         = "12338861-20b1-46ed-8841-269a5a937edb"
BY_STORE_VIEW   = "a0b9bdce-2db3-4ea0-a2fc-365fd08c5786"

# Scenario → admin.cars.com report slug mapping (used for scenario-aware quick links)
SCENARIO_REPORTS = {
    1: [("Historical Connections",   "historical_connections"),
        ("Low Engaged Inventory",    "listings_optimizer")],
    2: [("Listings Optimizer",       "listings_optimizer"),
        ("Performance Trends",       "performance_trends")],
    3: [("Performance Trends",       "performance_trends"),
        ("Demand Signals",           "demand_signals")],
    4: [("Demand Signals",           "demand_signals"),
        ("Market Opportunities",     "market_opportunities")],
    5: [("Connections & Contact Details", "connections_contact_details"),
        ("ROI One-Sheeter",          "roi_one_sheeter")],
}
def _load_tableau_pat() -> tuple:
    """
    Load PAT name + secret. Priority order:
    1. Env vars TABLEAU_PAT_SECRET / TABLEAU_PAT_NAME (set by .zshrc or run-report.sh)
    2. macOS Keychain entry 'tableau-pat' (canonical store)
    3. ~/.claude/settings.json mcpServers.tableau.env (legacy fallback)
    """
    name   = os.environ.get("TABLEAU_PAT_NAME") or os.environ.get("PAT_NAME")
    secret = os.environ.get("TABLEAU_PAT_SECRET") or os.environ.get("PAT_VALUE")

    if not secret:
        # Try macOS Keychain directly
        try:
            result = subprocess.run(
                ["security", "find-generic-password", "-a", "jcrawley", "-s", "tableau-pat", "-w"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip():
                secret = result.stdout.strip()
                name = name or "Claude"
        except Exception:
            pass

    if not secret:
        # Final fallback: settings.json
        try:
            with open(os.path.expanduser("~/.claude/settings.json")) as f:
                cfg = json.load(f)
            tab_env = cfg.get("mcpServers", {}).get("tableau", {}).get("env", {})
            name   = name   or tab_env.get("PAT_NAME", "Claude")
            secret = secret or tab_env.get("PAT_VALUE", "")
        except Exception:
            pass

    return (name or "Claude"), (secret or "")


PAT_NAME, PAT_SECRET = _load_tableau_pat()

SF_CLI = "/Users/jcrawley/.npm-global/bin/sf"
SF_ORG = "cars-commerce"

ADMIN_BASE = "https://admin.cars.com"

GROUP_OPTIONS = {
    # 5 clients — Asbury sub-groups shown separately for per-group drill-down
    "Sonic Automotive":              "Sonic",
    "EchoPark":                      "EchoPark MA Group",
    "Hendrick Automotive":           "Hendrick Automotive Group",
    "ACA":                           "Atlantic Coast Automotive MA Group",
    "Asbury":                        "Asbury",
    "Asbury — Larry H. Miller":      "Larry Miller",
    "Asbury — Koons":                "Koons Automotive MA Group",
    "Asbury — Herb Chambers":        "Herb Chambers MA Group",
}

# Keys treated as Asbury sub-groups for "Full Book" display consolidation
ASBURY_FILTER_VALS = {
    "Asbury", "Larry Miller", "Koons Automotive MA Group", "Herb Chambers MA Group"
}

# Parent/group CCID → list of Tableau filter values to pull
# Allows entering e.g. 538486 to load all Sonic stores
PARENT_CCID_MAP = {
    "538486":  ["Sonic"],                                         # Sonic Automotive Group
    "546973":  ["Hendrick Automotive Group"],                     # Hendrick Automotive Group
    "6051462": ["Atlantic Coast Automotive MA Group"],            # ACA
    "6051464": ["EchoPark MA Group"],                             # EchoPark
    "539890":  ["Asbury", "Larry Miller",                         # Asbury full umbrella
                "Koons Automotive MA Group", "Herb Chambers MA Group"],
    "1875929": ["Larry Miller"],                                  # Larry H. Miller standalone
    "5392338": ["Koons Automotive MA Group"],                     # Koons standalone
    "185555":  ["Koons Automotive MA Group"],                     # Koons Group 2
    "6048251": ["Herb Chambers MA Group"],                        # Herb Chambers standalone
}

FOCUS_OPTIONS = {
    "All Scenarios":      None,
    "Connections":        {1},
    "VDPs":               {3},
    "Demand Mismatch":    {4},
    "Merchandising":      {2},
    "Cost / Lead":        {5},
}

TREND_ORDER   = {"CRITICAL": 0, "SUSTAINED": 1, "NEW": 2, "RESOLVED": 3}
SEV_ORDER     = {"HIGH": 0, "MEDIUM": 1}
TREND_COLORS  = {
    "CRITICAL": "#c0392b", "SUSTAINED": "#d97706",
    "NEW": "#2563eb",      "RESOLVED": "#059669",
}


# ─── DATA LAYER ───────────────────────────────────────────────────────────────

@st.cache_data(ttl=1800, show_spinner=False)
def _tableau_token() -> str:
    payload = json.dumps({
        "credentials": {
            "personalAccessTokenName": PAT_NAME,
            "personalAccessTokenSecret": PAT_SECRET,
            "site": {"contentUrl": "cars"},
        }
    }).encode()
    req = urllib.request.Request(
        f"{TABLEAU_HOST}/api/3.22/auth/signin",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        body = r.read()
    import xml.etree.ElementTree as ET
    root = ET.fromstring(body)
    ns = {"t": "http://tableau.com/api"}
    creds = root.find("t:credentials", ns) or root.find("credentials")
    if creds is None:
        raise RuntimeError(f"Unexpected Tableau auth response: {body[:200]}")
    return creds.attrib["token"]


@st.cache_data(ttl=1800, show_spinner=False)
def _pull_group(filter_val: str) -> List[Dict]:
    token = _tableau_token()
    encoded = urllib.parse.quote(filter_val)
    url = (
        f"{TABLEAU_HOST}/api/3.22/sites/{SITE_ID}/views/{BY_STORE_VIEW}"
        f"/data?vf_Maj%20Cust%20Name={encoded}"
    )
    req = urllib.request.Request(url, headers={"X-Tableau-Auth": token})
    with urllib.request.urlopen(req, timeout=60) as r:
        raw = r.read().decode("utf-8", errors="replace")

    stores: Dict[str, Dict] = {}
    for row in csv.DictReader(io.StringIO(raw)):
        name = row.get("Customer Name", "").strip()
        if not name:
            continue
        if name not in stores:
            stores[name] = {
                "Customer Name": name,
                "Legacy Id": row.get("Legacy Id", "").strip(),
                "Maj Cust Name": row.get("Maj Cust Name", "").strip(),
                "Group Cust Name": row.get("Group Cust Name", "").strip(),
            }
        measure = row.get("Measure Names", "").strip()
        value   = row.get("Measure Values", "").strip()
        if measure:
            stores[name][measure] = value
    return list(stores.values())


@st.cache_data(ttl=1800, show_spinner=False)
def _pull_by_name(name: str) -> List[Dict]:
    """Pull all accessible groups and filter by store name (fuzzy)."""
    all_stores = []
    for filter_val in GROUP_OPTIONS.values():
        try:
            all_stores.extend(_pull_group(filter_val))
        except Exception:
            pass
    name_lower = name.lower()
    return [s for s in all_stores if name_lower in s["Customer Name"].lower()]


@st.cache_data(ttl=1800, show_spinner=False)
def _pull_by_ccid(ccid: str) -> List[Dict]:
    all_stores = []
    for filter_val in GROUP_OPTIONS.values():
        try:
            all_stores.extend(_pull_group(filter_val))
        except Exception:
            pass
    return [s for s in all_stores if s.get("Legacy Id", "").strip() == ccid.strip()]


@st.cache_data(ttl=300, show_spinner=False)
def _sf_query(soql: str) -> List[Dict]:
    try:
        r = subprocess.run(
            [SF_CLI, "data", "query", "--query", soql, "--target-org", SF_ORG, "--json"],
            capture_output=True, text=True, timeout=30,
        )
        data = json.loads(r.stdout[r.stdout.find("{"):])
        recs = data.get("result", {}).get("records", [])
        for rec in recs:
            rec.pop("attributes", None)
        return recs
    except Exception:
        return []


def _sf_account(name_or_ccid: str) -> Optional[Dict]:
    if name_or_ccid.isdigit():
        recs = _sf_query(
            f"SELECT Name, CCID__c, BillingCity, BillingState, Account_Status__c, "
            f"Product_Amount__c, Products__c FROM Account "
            f"WHERE CCID__c = '{name_or_ccid}' LIMIT 1"
        )
    else:
        safe = name_or_ccid.replace("'", "\\'")
        recs = _sf_query(
            f"SELECT Name, CCID__c, BillingCity, BillingState, Account_Status__c, "
            f"Product_Amount__c, Products__c FROM Account "
            f"WHERE Name LIKE '%{safe}%' ORDER BY Name LIMIT 5"
        )
    return recs[0] if recs else None


def _sf_subscriptions(ccid: str) -> List[Dict]:
    recs = _sf_query(
        f"SELECT SBQQ__Account__r.Name, SBQQ__ProductName__c, SBQQ__NetPrice__c, "
        f"SBQQ__SubscriptionEndDate__c "
        f"FROM SBQQ__Subscription__c "
        f"WHERE SBQQ__Account__r.CCID__c = '{ccid}' "
        f"AND SBQQ__SubscriptionEndDate__c > TODAY "
        f"ORDER BY SBQQ__NetPrice__c DESC LIMIT 20"
    )
    return recs


def _sf_expirations(days: int = 90, scanned_ccids: Optional[List[str]] = None) -> List[Dict]:
    """Return expiring subscriptions scoped to the scanned stores only."""
    from datetime import timedelta
    cutoff = (date.today() + timedelta(days=days)).isoformat()

    if scanned_ccids:
        all_results = []
        for i in range(0, len(scanned_ccids), 100):
            batch = scanned_ccids[i:i+100]
            ccid_clause = "','".join(batch)
            all_results.extend(_sf_query(
                f"SELECT SBQQ__Account__r.Name, SBQQ__Account__r.CCID__c, "
                f"SBQQ__ProductName__c, SBQQ__NetPrice__c, SBQQ__SubscriptionEndDate__c "
                f"FROM SBQQ__Subscription__c "
                f"WHERE SBQQ__SubscriptionEndDate__c <= {cutoff} "
                f"AND SBQQ__SubscriptionEndDate__c >= TODAY "
                f"AND SBQQ__Account__r.CCID__c IN ('{ccid_clause}') "
                f"ORDER BY SBQQ__SubscriptionEndDate__c LIMIT 100"
            ))
        return all_results

    # Fallback: filter by Jake's client names when no CCIDs available
    name_filter = (
        "SBQQ__Account__r.Parent.Name LIKE '%Sonic%' OR "
        "SBQQ__Account__r.Parent.Name LIKE '%Hendrick%' OR "
        "SBQQ__Account__r.Parent.Name LIKE '%Atlantic Coast%' OR "
        "SBQQ__Account__r.Parent.Name LIKE '%Asbury%' OR "
        "SBQQ__Account__r.Parent.Name LIKE '%EchoPark%' OR "
        "SBQQ__Account__r.Parent.Name LIKE '%Larry%Miller%' OR "
        "SBQQ__Account__r.Parent.Name LIKE '%Koons%' OR "
        "SBQQ__Account__r.Parent.Name LIKE '%Herb%Chambers%'"
    )
    return _sf_query(
        f"SELECT SBQQ__Account__r.Name, SBQQ__Account__r.CCID__c, "
        f"SBQQ__ProductName__c, SBQQ__NetPrice__c, SBQQ__SubscriptionEndDate__c "
        f"FROM SBQQ__Subscription__c "
        f"WHERE SBQQ__SubscriptionEndDate__c <= {cutoff} "
        f"AND SBQQ__SubscriptionEndDate__c >= TODAY "
        f"AND ({name_filter}) "
        f"ORDER BY SBQQ__SubscriptionEndDate__c LIMIT 100"
    )


# ─── HISTORY ──────────────────────────────────────────────────────────────────

HISTORY_FILE = os.path.expanduser("~/.claude/scan_history/biz_scan_latest.json")


def _load_history() -> Dict:
    if not os.path.exists(HISTORY_FILE):
        return {}
    try:
        with open(HISTORY_FILE) as f:
            return json.load(f)
    except Exception:
        return {}


def _trend(store_name: str, severity: str, history: Dict) -> str:
    prev = history.get("stores", {}).get(store_name, {})
    if not prev:
        return "NEW"
    prev_sev = prev.get("severity", "")
    if prev_sev == "CRITICAL":
        return "CRITICAL"
    if prev_sev in ("HIGH", "MEDIUM", "SUSTAINED", "NEW"):
        return "SUSTAINED" if severity in ("HIGH", "MEDIUM") else "RESOLVED"
    return "NEW"


# ─── INVESTIGATION ENGINE ─────────────────────────────────────────────────────

def run_investigation(stores: List[Dict], focus_scenarios=None) -> Dict:
    results = investigate_stores(stores)
    if focus_scenarios:
        for bucket in ("high", "medium"):
            for entry in results[bucket]:
                entry["flags"] = [f for f in entry["flags"] if f["scenario"] in focus_scenarios]
            results[bucket] = [e for e in results[bucket] if e["flags"]]
    return results


def enrich_with_trends(results: Dict, history: Dict) -> Dict:
    for bucket in ("high", "medium"):
        for entry in results[bucket]:
            sev = "HIGH" if bucket == "high" else "MEDIUM"
            entry["trend"] = _trend(entry["store"], sev, history)
    return results


def build_flag_dataframe(results: Dict) -> pd.DataFrame:
    rows = []
    for bucket in ("high", "medium"):
        for entry in results[bucket]:
            sev = "HIGH" if bucket == "high" else "MED"
            trend = entry.get("trend", "NEW")
            top_scenario = entry["flags"][0]["scenario"] if entry["flags"] else 0
            top_signal   = entry["flags"][0]["signal"] if entry["flags"] else ""
            flag_summary = "  ·  ".join(
                f"S{f['scenario']} {f['severity'][:1]}" for f in entry["flags"][:4]
            )
            rows.append({
                "trend":        trend,
                "store":        entry["store"],
                "ccid":         entry["ccid"],
                "severity":     sev,
                "flags":        flag_summary,
                "top_scenario": f"Scenario {top_scenario} — {SCENARIO_META.get(top_scenario, {}).get('name', '')}",
                "top_signal":   top_signal,
                "_entry":       entry,
            })
    # Sort: CRITICAL first, then SUSTAINED, NEW; HIGH before MED
    rows.sort(key=lambda r: (TREND_ORDER.get(r["trend"], 9), SEV_ORDER.get(r["severity"], 9)))
    return pd.DataFrame(rows)


# ─── CLAUDE TALKING POINTS ────────────────────────────────────────────────────

def generate_talking_points(store_name: str, metrics: Dict, flags: List[Dict], sf_account: Optional[Dict]) -> str:
    """Call Claude CLI for 3 talking points. Returns markdown string."""
    mrr = sf_account.get("Product_Amount__c", 0) if sf_account else 0
    products = sf_account.get("Products__c", "") if sf_account else ""
    city = sf_account.get("BillingCity", "") if sf_account else ""

    flag_lines = "\n".join(
        f"- Scenario {f['scenario']} ({f['severity']}): {f['signal']}"
        for f in flags[:5]
    )

    vdp_cp   = _get(metrics, "vdp_cp")
    conn_cp  = _get(metrics, "conn_cp")
    vdp_d    = _delta(metrics, "vdp_cp", "vdp_pp", "vdp_delta")
    conn_d   = _delta(metrics, "conn_cp", "conn_pp", "conn_delta")
    inv_cp   = _get(metrics, "inv_cp")
    cost_cp  = _get(metrics, "cost_lead_cp")

    metrics_txt = "\n".join(filter(None, [
        f"VDPs: {int(vdp_cp):,} ({_pct(vdp_d)} MoM)" if vdp_cp else None,
        f"Connections: {int(conn_cp):,} ({_pct(conn_d)} MoM)" if conn_cp else None,
        f"Avg Inventory: {int(inv_cp)} vehicles/day" if inv_cp else None,
        f"Cost/Lead: ${cost_cp:.0f}" if cost_cp else None,
        f"MRR: ${mrr:,.0f}/mo" if mrr else None,
        f"Products: {products}" if products else None,
    ]))

    # Build scenario-specific report guidance for TP3
    report_guidance = ""
    if flags:
        top_scenario = flags[0]["scenario"]
        report_map = {
            1: ("Listings Optimizer (Best Match tab + Low Engaged Inventory)",
                "admin.cars.com → Reports → Listings Optimizer"),
            2: ("Listings Optimizer (Best Match tab — photo bucket, price-to-market)",
                "admin.cars.com → Reports → Listings Optimizer"),
            3: ("Demand Signals (inventory mix vs. what local shoppers are searching for)",
                "admin.cars.com → Reports → Demand Signals"),
            4: ("Demand Signals (make/model demand vs. inventory — what's missing from the lot)",
                "admin.cars.com → Reports → Demand Signals"),
            5: ("Connections & Contact Details (lead source breakdown and cost-per-lead by type)",
                "admin.cars.com → Reports → Connections & Contact Details"),
        }
        if top_scenario in report_map:
            report_name, report_path = report_map[top_scenario]
            report_guidance = (
                f"\nFor TP3, reference this specific report: {report_name}\n"
                f"Path: {report_path}\n"
                f"Ask a question that invites the dealer to review it together on the call."
            )

    prompt = f"""You are a Cars.com account executive preparing for a dealer call.
Generate exactly 3 talking points for a call with {store_name} ({city}).

CURRENT METRICS:
{metrics_txt}

INVESTIGATION FLAGS:
{flag_lines if flag_lines else "No active flags — store is performing well."}
{report_guidance}
Rules:
- TP1: open with a specific WIN or positive data point (use actual numbers from metrics above)
- TP2: the highest-priority flag framed as revenue or competitive impact — estimate dollar or lead impact even if rough
- TP3: a specific, named report question — use the exact report name from REPORT FOR TP3 above.
  Format: "Have you had a chance to look at [Report Name] in admin.cars.com? I want to walk you through [specific insight from the data]."
- Every TP must cite at least one real number from the data
- Keep each under 3 sentences
- Do NOT write headings — just three numbered paragraphs

Output format:
1. [talking point one]

2. [talking point two]

3. [talking point three]"""

    env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
    try:
        r = subprocess.run(
            ["claude", "-p", prompt, "--model", "claude-sonnet-4-6",
             "--output-format", "text", "--mcp-config", '{"mcpServers":{}}',
             "--strict-mcp-config"],
            capture_output=True, text=True, timeout=60, env=env,
        )
        return r.stdout.strip() if r.returncode == 0 else f"_(Error generating talking points: {r.stderr[:200]})_"
    except Exception as e:
        return f"_(Talking points unavailable: {e})_"


# ─── RENDERING HELPERS ────────────────────────────────────────────────────────

def _trend_badge_html(trend: str) -> str:
    return f'<span class="badge badge-{trend}">{trend}</span>'


def _kpi_tile(val: str, label: str, alert: bool = False, teal: bool = False) -> str:
    cls = "kpi-tile alert" if alert else ("kpi-tile teal" if teal else "kpi-tile")
    return (
        f'<div class="{cls}">'
        f'<div class="kpi-val">{val}</div>'
        f'<div class="kpi-lbl">{label}</div>'
        f'</div>'
    )


def _render_kpis(results: Dict, expirations: List) -> str:
    total   = len(results["high"]) + len(results["medium"]) + len(results["bright_spots"]) + len(results["clean"])
    high    = len(results["high"])
    med     = len(results["medium"])
    bright  = len(results["bright_spots"])
    crit    = sum(1 for e in results["high"] + results["medium"] if e.get("trend") == "CRITICAL")
    expiry_crit = sum(1 for e in expirations if _days_left(e) <= 30)

    tiles = [
        _kpi_tile(str(total),  "Stores Scanned"),
        _kpi_tile(str(crit),   "Critical Trends", alert=bool(crit)),
        _kpi_tile(str(high),   "HIGH Flags",      alert=bool(high)),
        _kpi_tile(str(med),    "Medium Flags"),
        _kpi_tile(str(bright), "Bright Spots",    teal=bool(bright)),
        _kpi_tile(str(len(expirations)), f"Expiring ≤90d", alert=bool(expiry_crit)),
    ]
    return f'<div class="kpi-grid">{"".join(tiles)}</div>'


def _days_left(expiry_rec: Dict) -> int:
    end = expiry_rec.get("SBQQ__SubscriptionEndDate__c", "")
    if not end:
        return 999
    try:
        return (datetime.strptime(end, "%Y-%m-%d").date() - date.today()).days
    except Exception:
        return 999


def _get_uuid(ccid: str) -> Optional[str]:
    """Look up cached admin.cars.com UUID for a CCID."""
    for cache_path in [
        os.path.expanduser("~/.claude/aca_uuid_cache.json"),
        os.path.expanduser("~/.claude/uuid_cache.json"),
    ]:
        try:
            with open(cache_path) as f:
                cache = json.load(f)
            if ccid in cache:
                return cache[ccid]
        except Exception:
            pass
    return None


def _admin_links(ccid: str, flags: Optional[List] = None) -> str:
    """
    Render admin.cars.com quick links. Always shows a working search link.
    When scenario flags are provided, surfaces the two most relevant reports
    for the highest-priority scenario first (scenario-aware).
    """
    if not ccid:
        return ""
    uuid = _get_uuid(ccid)

    # Always-available: search by CCID
    links = [f'<a href="https://admin.cars.com/dealers/all/reports?query={ccid}" target="_blank">🔍 Open in admin.cars.com</a>']

    if uuid:
        base = f"https://admin.cars.com/dealers/{uuid}/reports"

        if flags:
            # Scenario-aware: show reports relevant to the highest-priority scenario first
            shown_slugs = set()
            for flag in sorted(flags, key=lambda f: (0 if f["severity"] == "HIGH" else 1, f["scenario"])):
                for label, slug in SCENARIO_REPORTS.get(flag["scenario"], []):
                    if slug not in shown_slugs:
                        links.append(f'<a href="{base}/{slug}" target="_blank">→ {label}</a>')
                        shown_slugs.add(slug)
                if len(shown_slugs) >= 3:
                    break
            # Always add Performance Trends as a baseline if not already shown
            if "performance_trends" not in shown_slugs:
                links.append(f'<a href="{base}/performance_trends" target="_blank">Performance Trends</a>')
        else:
            # No flags — show standard set for a healthy store (upsell/optimize focus)
            links += [
                f'<a href="{base}/performance_trends" target="_blank">Performance Trends</a>',
                f'<a href="{base}/listings_optimizer" target="_blank">Listings Optimizer</a>',
                f'<a href="{base}/demand_signals" target="_blank">Demand Signals</a>',
            ]
    else:
        # No UUID cached — give instructions to resolve
        links.append(
            f'<span style="color:#9ca3af;font-size:11px;">'
            f'(Deep links available after first admin.cars.com visit for this store)</span>'
        )

    return f'<div class="qlink">{"".join(links)}</div>'


# ─── PAGE SETUP ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Cars.com | Investigation Dashboard",
    page_icon="🔍",
    layout="wide",
)
st.markdown(CC_CSS, unsafe_allow_html=True)
st.markdown(HEADER_HTML, unsafe_allow_html=True)


# ─── SIDEBAR ──────────────────────────────────────────────────────────────────

with st.sidebar:
    st.header("Scope")

    mode = st.radio("Mode", ["Group", "Store / CCID", "Full Book"], horizontal=False)

    selected_group_label = None
    store_input = ""

    if mode == "Group":
        selected_group_label = st.selectbox("Group", list(GROUP_OPTIONS.keys()))

    elif mode == "Store / CCID":
        store_input = st.text_input(
            "Store name or CCID",
            placeholder="e.g. Nalley Lexus Galleria or 109754",
        )

    st.header("Filters")
    focus_label = st.selectbox("Focus", list(FOCUS_OPTIONS.keys()))
    focus_scenarios = FOCUS_OPTIONS[focus_label]

    show_expirations = st.checkbox("Show expiring products (SF)", value=True)
    expiry_days = st.slider("Expiration window (days)", 30, 180, 90) if show_expirations else 90

    st.divider()
    run = st.button("Run Scan", type="primary", use_container_width=True)
    if st.button("Clear Cache", use_container_width=True):
        st.cache_data.clear()
        st.session_state.clear()
        st.rerun()

    st.divider()
    st.caption("Tableau data cached 30 min · SF data cached 5 min")
    if PAT_SECRET:
        src = "env" if os.environ.get("TABLEAU_PAT_SECRET") else "keychain/settings"
        st.success(f"● Tableau PAT ready ({PAT_NAME} · {src})")
    else:
        st.error("✗ Tableau PAT not found")
        st.caption("Run: `security add-generic-password -a jcrawley -s tableau-pat -w 'YOUR_PAT'`")

    # admin.cars.com session status (for Tab 4 Health Analysis)
    st.divider()
    st.caption("Health Analysis (Tab 4)")

    @st.cache_data(ttl=60)
    def _admin_session_ok() -> bool:
        # Two-stage: Chrome up + actually authenticated to admin.cars.com
        if not _admin_cars.check_session():
            return False
        return _admin_cars.check_admin_auth()

    _cdp_ok = _admin_session_ok()

    if _cdp_ok:
        st.success("● admin.cars.com — authenticated")
        if st.button("Refresh", use_container_width=True, key="refresh_cdp"):
            st.cache_data.clear()
            st.rerun()
    else:
        # Differentiate: Chrome not running vs. Chrome running but not signed in
        _chrome_up = _admin_cars.check_session.__wrapped__() if hasattr(_admin_cars.check_session, "__wrapped__") else None
        try:
            import urllib.request as _ur
            _ur.urlopen("http://localhost:9223/json/version", timeout=2)
            _chrome_running = True
        except Exception:
            _chrome_running = False

        if _chrome_running:
            st.warning("● Chrome running — sign in to admin.cars.com")
            st.caption(
                "Chrome is up on port 9223 but not signed into admin.cars.com. "
                "Open admin.cars.com in that Chrome window and sign in via JumpCloud, "
                "then click Re-check."
            )
            st.caption("To open admin.cars.com in that Chrome window, run:")
            st.code('open -a "Google Chrome" --args --profile-directory=Default https://admin.cars.com', language="bash")
        else:
            st.error("● Chrome not running on port 9223")
            st.caption("Launch Chrome with remote debugging:")
            st.code(
                'mkdir -p ~/.chrome-dealer-health && '
                'nohup "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" '
                '--remote-debugging-port=9223 '
                '--user-data-dir="$HOME/.chrome-dealer-health" '
                "--remote-allow-origins='*' --no-first-run "
                '> /tmp/chrome-debug.log 2>&1 &',
                language="bash",
            )
        if st.button("Re-check", use_container_width=True, key="recheck_cdp"):
            st.cache_data.clear()
            st.rerun()


# ─── RUN SCAN ─────────────────────────────────────────────────────────────────

if run:
    stores: List[Dict] = []
    group_label = ""
    error = None

    with st.spinner("Pulling Tableau data…"):
        try:
            if mode == "Group" and selected_group_label:
                filter_val = GROUP_OPTIONS[selected_group_label]
                stores = _pull_group(filter_val)
                group_label = selected_group_label

            elif mode == "Store / CCID" and store_input.strip():
                inp = store_input.strip()
                if inp.isdigit():
                    # Check if this is a parent/group CCID first
                    if inp in PARENT_CCID_MAP:
                        filter_vals = PARENT_CCID_MAP[inp]
                        for fv in filter_vals:
                            try:
                                stores.extend(_pull_group(fv))
                            except Exception as e:
                                st.warning(f"{fv}: {e}")
                        group_label = f"Group {inp} ({', '.join(filter_vals)})"
                    else:
                        stores = _pull_by_ccid(inp)
                        group_label = f"CCID {inp}"
                else:
                    stores = _pull_by_name(inp)
                    group_label = inp

            elif mode == "Full Book":
                for label, fv in GROUP_OPTIONS.items():
                    try:
                        chunk = _pull_group(fv)
                        stores.extend(chunk)
                    except Exception as e:
                        st.warning(f"{label}: {e}")
                group_label = "Full Book"

        except Exception as e:
            error = str(e)

    if error:
        st.error(f"Tableau pull failed: {error}")
    elif not stores:
        st.warning("No stores returned — check PAT scope or try a different group.")
    else:
        history = _load_history()
        results = run_investigation(stores, focus_scenarios)
        results = enrich_with_trends(results, history)

        # Collect scanned CCIDs to scope SF queries to Jake's book only
        scanned_ccids = [s.get("Legacy Id", "") for s in stores if s.get("Legacy Id")]

        expirations = []
        if show_expirations:
            with st.spinner("Checking Salesforce for expirations…"):
                expirations = _sf_expirations(expiry_days, scanned_ccids=scanned_ccids)

        st.session_state["scan"] = {
            "stores":       stores,
            "results":      results,
            "expirations":  expirations,
            "group_label":  group_label,
            "scanned_at":   datetime.now().strftime("%b %d, %Y %H:%M"),
        }
        st.session_state.pop("brief", None)   # clear stale brief on new scan
        st.rerun()


# ─── MAIN CONTENT ─────────────────────────────────────────────────────────────

if "scan" not in st.session_state:
    st.info("Select a scope in the sidebar and click **Run Scan** to get started.")
    st.stop()

scan        = st.session_state["scan"]
results     = scan["results"]
stores      = scan["stores"]
expirations = scan["expirations"]
group_label = scan["group_label"]
scanned_at  = scan["scanned_at"]

st.markdown(
    f'<div style="color:#9ca3af;font-size:0.8rem;margin-bottom:.5rem;">'
    f'Scanned: <strong>{group_label}</strong> · {len(stores)} stores · {scanned_at}</div>',
    unsafe_allow_html=True,
)

# KPI row
st.markdown(_render_kpis(results, expirations), unsafe_allow_html=True)

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_book, tab_brief, tab_expiry, tab_health = st.tabs([
    "📋 Flagged Stores", "🔍 Store Brief", "⚠️ Expirations & Upsell", "🏥 Health Analysis"
])

# ═══════════════════════ TAB 1: FLAGGED STORES ════════════════════════════════
with tab_book:
    flagged_df = build_flag_dataframe(results)

    if flagged_df.empty:
        st.success("No flags this period — all stores look healthy.")
    else:
        col_l, col_r = st.columns([3, 1])
        with col_r:
            trend_filter = st.multiselect(
                "Filter by trend",
                ["CRITICAL", "SUSTAINED", "NEW"],
                default=["CRITICAL", "SUSTAINED", "NEW"],
                key="trend_filter",
            )
        filtered_df = flagged_df[flagged_df["trend"].isin(trend_filter)] if trend_filter else flagged_df

        # Display table (hide internal _entry column)
        display_cols = ["trend", "store", "ccid", "severity", "flags", "top_scenario", "top_signal"]
        event = st.dataframe(
            filtered_df[display_cols],
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row",
            column_config={
                "trend":        st.column_config.TextColumn("Trend", width=90),
                "store":        st.column_config.TextColumn("Store", width=220),
                "ccid":         st.column_config.TextColumn("CCID", width=80),
                "severity":     st.column_config.TextColumn("Sev", width=60),
                "flags":        st.column_config.TextColumn("Flag Summary", width=130),
                "top_scenario": st.column_config.TextColumn("Top Scenario"),
                "top_signal":   st.column_config.TextColumn("Signal"),
            },
        )

        # Store selection → show inline quick brief
        selected_rows = event.selection.get("rows", []) if hasattr(event, "selection") else []
        if selected_rows:
            row_idx = selected_rows[0]
            entry   = filtered_df.iloc[row_idx]["_entry"]
            store_name = entry["store"]
            ccid       = entry["ccid"]

            st.divider()
            st.markdown(
                f'<div class="brief-card">'
                f'<div style="font-size:1.05rem;font-weight:700;color:#111827;margin-bottom:4px;">'
                f'{store_name}</div>'
                f'<div class="brief-meta">CCID {ccid} &nbsp;·&nbsp; '
                f'{_trend_badge_html(entry.get("trend","NEW"))} &nbsp; '
                + "".join(
                    f'<span class="flag-chip chip-{"HIGH" if f["severity"]=="HIGH" else "MED"}">'
                    f'S{f["scenario"]} {f["severity"]}</span>'
                    for f in entry["flags"]
                )
                + f'</div>',
                unsafe_allow_html=True,
            )

            # Flags detail
            for flag in entry["flags"]:
                meta = SCENARIO_META.get(flag["scenario"], {})
                with st.expander(
                    f"{'🔴' if flag['severity']=='HIGH' else '🟡'} "
                    f"Scenario {flag['scenario']} — {meta.get('name','')}: {flag['signal']}",
                    expanded=True,
                ):
                    st.caption(f"**Next step:** {meta.get('next_step','')}")

            # Scenario-aware admin.cars.com quick links
            st.markdown(_admin_links(ccid, flags=entry["flags"]), unsafe_allow_html=True)

            # Talking points button + "Open Full Brief" shortcut to Tab 2
            store_metrics = next((s for s in stores if s["Customer Name"] == store_name), {})
            col_tp, col_brief = st.columns(2)
            run_tp = col_tp.button("⚡ Generate Talking Points", key=f"tp_{ccid}")
            if col_brief.button("📋 Open Full Brief →", key=f"brief_nav_{ccid}"):
                st.session_state["brief_prefill"] = store_name
                st.session_state["active_tab"] = "brief"
            if run_tp:
                with st.spinner("Generating talking points…"):
                    sf_acct = _sf_account(ccid) if ccid else None
                    tp_text = generate_talking_points(store_name, store_metrics, entry["flags"], sf_acct)
                st.session_state["brief"] = {
                    "store": store_name, "ccid": ccid,
                    "tp": tp_text, "flags": entry["flags"],
                    "sf_acct": sf_acct,
                }

            st.markdown("</div>", unsafe_allow_html=True)

        # Talking points from session state (persist across reruns)
        if "brief" in st.session_state and st.session_state["brief"]["store"] == (
            filtered_df.iloc[selected_rows[0]]["store"] if selected_rows else ""
        ):
            brief = st.session_state["brief"]
            st.subheader("Talking Points")
            for i, line in enumerate(brief["tp"].strip().split("\n\n"), 1):
                if line.strip():
                    clean = line.strip().lstrip("0123456789. ")
                    st.markdown(
                        f'<div class="tp-block"><div class="tp-num">{i}</div>{clean}</div>',
                        unsafe_allow_html=True,
                    )

    # Bright spots
    if results["bright_spots"]:
        st.divider()
        st.subheader(f"✓ Bright Spots ({len(results['bright_spots'])})")
        bright_data = [
            {"Store": b["store"], "CCID": b["ccid"], "Signal": b["signal"]}
            for b in results["bright_spots"]
        ]
        st.dataframe(pd.DataFrame(bright_data), use_container_width=True, hide_index=True)


# ═══════════════════════ TAB 2: STORE BRIEF ═══════════════════════════════════
with tab_brief:
    st.subheader("Pre-Call Brief")

    # Auto-populate from Tab 1 "Open Full Brief" or Tab 3 "Get Brief" buttons
    prefill = st.session_state.pop("brief_prefill", "")

    col_inp, col_btn = st.columns([4, 1])
    with col_inp:
        brief_store = st.text_input(
            "Store name or CCID",
            value=prefill,
            placeholder="e.g. Stevens Creek BMW or 25732",
            key="brief_store_input",
        )
    with col_btn:
        st.write("")
        run_brief = st.button("Get Brief", type="primary", key="run_brief_btn")

    if run_brief and brief_store.strip():
        inp = brief_store.strip()
        if inp.isdigit():
            store_list = [s for s in stores if s.get("Legacy Id", "") == inp]
        else:
            store_list = [s for s in stores if inp.lower() in s["Customer Name"].lower()]

        if not store_list:
            # try pulling fresh from all groups
            with st.spinner("Searching across all groups…"):
                if inp.isdigit():
                    store_list = _pull_by_ccid(inp)
                else:
                    store_list = _pull_by_name(inp)

        if not store_list:
            st.warning("Store not found. Check the name or CCID and try again.")
        else:
            store_rec = store_list[0]
            store_name = store_rec["Customer Name"]
            ccid = store_rec.get("Legacy Id", "")

            # Run investigation triggers on just this store
            single_results = run_investigation([store_rec])
            flags = (single_results["high"] + single_results["medium"])
            all_flags = flags[0]["flags"] if flags else []
            trend = flags[0].get("trend", "NEW") if flags else "—"

            with st.spinner("Fetching SF account…"):
                sf_acct = _sf_account(ccid or store_name)

            with st.spinner("Generating talking points…"):
                tp_text = generate_talking_points(store_name, store_rec, all_flags, sf_acct)

            st.session_state["store_brief"] = {
                "store": store_name, "ccid": ccid,
                "flags": all_flags, "trend": trend,
                "sf": sf_acct, "tp": tp_text, "metrics": store_rec,
            }

    if "store_brief" in st.session_state:
        brief = st.session_state["store_brief"]
        sf = brief.get("sf") or {}

        st.markdown(
            f'<div class="brief-card">',
            unsafe_allow_html=True,
        )

        # Header row
        col_h1, col_h2 = st.columns([3, 2])
        with col_h1:
            city = f"{sf.get('BillingCity','')}, {sf.get('BillingState','')}" if sf else ""
            st.markdown(f"### {brief['store']}")
            if city.strip(", "):
                st.caption(city)
        with col_h2:
            mrr  = sf.get("Product_Amount__c", 0) or 0
            prods = sf.get("Products__c", "") or ""
            if mrr:
                st.metric("MRR", f"${mrr:,.0f}/mo")
            if prods:
                st.caption(prods[:100])

        # Metrics
        m = brief["metrics"]
        vdp_cp   = _get(m, "vdp_cp")
        conn_cp  = _get(m, "conn_cp")
        inv_cp   = _get(m, "inv_cp")
        cost_cp  = _get(m, "cost_lead_cp")
        vdp_d    = _delta(m, "vdp_cp", "vdp_pp", "vdp_delta")
        conn_d   = _delta(m, "conn_cp", "conn_pp", "conn_delta")

        if any([vdp_cp, conn_cp, inv_cp, cost_cp]):
            st.divider()
            cols = st.columns(4)
            if vdp_cp:
                cols[0].metric("VDPs", f"{int(vdp_cp):,}", f"{_pct(vdp_d)}" if vdp_d else None)
            if conn_cp:
                cols[1].metric("Connections", f"{int(conn_cp):,}", f"{_pct(conn_d)}" if conn_d else None)
            if inv_cp:
                cols[2].metric("Avg Inventory", f"{int(inv_cp)}/day")
            if cost_cp:
                cols[3].metric("Cost/Lead", f"${cost_cp:.0f}")

        # Flags
        if brief["flags"]:
            st.divider()
            st.markdown("**Active Flags**")
            for flag in brief["flags"]:
                meta = SCENARIO_META.get(flag["scenario"], {})
                color = "🔴" if flag["severity"] == "HIGH" else "🟡"
                st.markdown(
                    f"{color} **Scenario {flag['scenario']} — {meta.get('name','')}**  \n"
                    f"↳ {flag['signal']}  \n"
                    f"→ *{meta.get('next_step','')}*"
                )
        else:
            st.success("No active flags — store is performing well.")

        # Scenario-aware quick links
        st.markdown(_admin_links(brief["ccid"], flags=brief.get("flags")), unsafe_allow_html=True)

        if st.button("🏥 Run Full Health Analysis →", key="brief_to_health"):
            st.session_state["health_prefill"] = brief.get("store", brief.get("ccid", ""))
            st.session_state["active_tab"] = "health"

        # Talking points
        if brief["tp"]:
            st.divider()
            st.markdown("**Talking Points**")
            for i, line in enumerate(brief["tp"].strip().split("\n\n"), 1):
                if line.strip():
                    clean = line.strip().lstrip("0123456789. ")
                    st.markdown(
                        f'<div class="tp-block"><div class="tp-num">{i}</div>{clean}</div>',
                        unsafe_allow_html=True,
                    )

        st.markdown("</div>", unsafe_allow_html=True)


# ═══════════════════════ TAB 3: EXPIRATIONS & UPSELL ═════════════════════════
with tab_expiry:

    # ── Expiring products ──────────────────────────────────────────────────────
    if not expirations:
        if show_expirations:
            st.success(
                f"✓ No expiring products in the next {expiry_days} days for your scanned accounts. "
                f"Results are scoped to your book only — not the full Salesforce org."
            )
        else:
            st.info("Enable 'Show expiring products' in the sidebar and re-run to see renewals.")
    else:
        st.subheader(f"⚠️ Expiring Products ({len(expirations)})")
        expiry_rows = []
        for e in expirations:
            days = _days_left(e)
            acct = e.get("SBQQ__Account__r") or {}
            name = acct.get("Name", "Unknown") if isinstance(acct, dict) else "Unknown"
            expiry_rows.append({
                "Days Left": days,
                "Account":   name,
                "Product":   e.get("SBQQ__ProductName__c", ""),
                "MRR":       f"${e.get('SBQQ__NetPrice__c', 0):,.0f}",
                "Expires":   e.get("SBQQ__SubscriptionEndDate__c", ""),
                "_days":     days,
            })
        expiry_rows.sort(key=lambda r: r["_days"])
        expiry_df = pd.DataFrame([{k: v for k, v in r.items() if k != "_days"} for r in expiry_rows])

        def _color_days(val):
            try:
                d = int(val)
                if d <= 30: return "color: #c0392b; font-weight: 700"
                if d <= 60: return "color: #d97706; font-weight: 600"
            except Exception:
                pass
            return ""

        st.dataframe(
            expiry_df.style.applymap(_color_days, subset=["Days Left"]),
            use_container_width=True, hide_index=True,
        )

    st.divider()

    # ── Upsell scoring ─────────────────────────────────────────────────────────
    st.subheader("📈 Upsell Opportunities")
    st.caption(
        "Scored across ALL scanned stores — not limited to bright spots. "
        "Score = metric trajectory × product gap. "
        "Higher = stronger upsell conversation."
    )

    include_flagged = st.checkbox(
        "Include flagged stores",
        value=False,
        help="Flagged stores have active issues — typically fix first, then upsell",
    )

    # Build upsell candidates from scan data only — no external API needed.
    # Score = metric trajectory (VDP + connection growth) × scenario gap weight.
    # Enterprise accounts don't expose per-store MRR via Tableau or SF,
    # so trajectory is the primary signal; flagged scenarios indicate product gaps.

    SCENARIO_UPSELL_WEIGHT = {
        1: ("Connections drop → Listings Optimizer / MAE conversation", 20),
        2: ("Merch gap → Listings Optimizer Premium",                    25),
        3: ("VDP decline → Demand Signals / Market Area Expansion",      20),
        4: ("Demand mismatch → AccuTrade / inventory mix conversation",  25),
        5: ("High Cost/Lead → lead quality product or package review",   15),
    }

    upsell_candidates = []
    all_scan_stores = (
        results["high"] + results["medium"] + results["bright_spots"] + results["clean"]
    )

    for entry in all_scan_stores:
        is_flagged = entry in (results["high"] + results["medium"])
        if is_flagged and not include_flagged:
            continue

        ccid  = entry.get("ccid", "")
        name  = entry.get("store", "") or entry.get("Customer Name", "")
        flags = entry.get("flags", [])

        store_rec = next((s for s in stores if s.get("Legacy Id") == ccid), {})
        vdp_d  = _delta(store_rec, "vdp_cp", "vdp_pp", "vdp_delta") or 0
        conn_d = _delta(store_rec, "conn_cp","conn_pp","conn_delta") or 0

        # Trajectory score (0–50): growth momentum = upsell readiness
        traj_score = min(50, int(max(0, vdp_d) * 120 + max(0, conn_d) * 120))

        # Gap score (0–50): active flags identify which products to bring up
        gap_score   = 0
        gap_labels  = []
        seen_scenarios = set()
        for f in flags:
            s = f["scenario"]
            if s not in seen_scenarios:
                label, weight = SCENARIO_UPSELL_WEIGHT.get(s, ("", 0))
                gap_score += weight
                if label:
                    gap_labels.append(label)
                seen_scenarios.add(s)
        gap_score = min(50, gap_score)

        total_score = traj_score + gap_score
        if total_score < 15:
            continue

        upsell_candidates.append({
            "Score":          total_score,
            "Store":          name,
            "CCID":           ccid,
            "Metric Trend":   f"VDPs {_pct(vdp_d) if vdp_d else '→'}  Conn {_pct(conn_d) if conn_d else '→'}",
            "Conversation":   gap_labels[0] if gap_labels else "Growth momentum — package review",
            "_score":         total_score,
        })

    upsell_candidates.sort(key=lambda r: -r["_score"])

    if not upsell_candidates:
        st.info("No upsell candidates found. Run a scan first, or enable 'Include flagged stores'.")
    else:
        def _score_color(val):
            try:
                s = int(val)
                if s >= 60: return "background-color: #d1fae5; color: #065f46; font-weight:700"
                if s >= 35: return "background-color: #fef3c7; color: #92400e"
            except Exception:
                pass
            return ""

        display_cols = ["Score", "Store", "CCID", "Metric Trend", "Conversation"]
        upsell_df = pd.DataFrame(
            [{k: v for k, v in r.items() if not k.startswith("_")} for r in upsell_candidates]
        )
        st.dataframe(
            upsell_df[display_cols].style.applymap(_score_color, subset=["Score"]),
            use_container_width=True, hide_index=True,
        )
        st.caption(
            f"**{len(upsell_candidates)} candidates** · "
            f"Score = metric trajectory (0–50) + scenario gap weight (0–50). "
            f"Green ≥60 = strong conversation; yellow ≥35 = worth raising. "
            f"Per-store MRR not available for enterprise accounts — use for conversation direction only."
        )

        # Quick link to prep brief for top candidate
        top = upsell_candidates[0]
        if st.button(f"📋 Get Brief for top candidate — {top['Store']}", key="upsell_top_brief"):
            st.session_state["brief_prefill"] = top["Store"]

# ═══════════════════════ TAB 4: HEALTH ANALYSIS ══════════════════════════════
with tab_health:
    st.subheader("🏥 Dealer Health Analysis")
    st.caption(
        "Full Growth Triangle analysis — Salesforce + admin.cars.com + Claude. "
        "Requires Chrome running on port 9223 for admin.cars.com data."
    )

    # Auto-populate from Tab 2 "Run Full Health Analysis" button
    health_prefill = st.session_state.pop("health_prefill", "")

    h_col1, h_col2 = st.columns([3, 1])
    with h_col1:
        health_dealer = st.text_input(
            "Dealer name or CCID",
            value=health_prefill,
            placeholder="e.g. Nalley Lexus Galleria or 109754",
            key="health_dealer_input",
        )
    with h_col2:
        import datetime as _hdt
        _ht = _hdt.date.today()
        _hpm = (_ht.replace(day=1) - _hdt.timedelta(days=1))
        _hcl = f"Current MTD ({_ht.strftime('%B %Y')})"
        _hpl = f"Prior Month ({_hpm.strftime('%B %Y')})"
        health_period = st.radio("Period", [_hcl, _hpl], horizontal=True, key="health_period")

    h_src_col1, h_src_col2 = st.columns(2)
    with h_src_col1:
        h_use_sf    = st.checkbox("Salesforce", value=True, key="h_sf")
        h_use_admin = st.checkbox("admin.cars.com", value=_cdp_ok, disabled=not _cdp_ok, key="h_admin")
    with h_src_col2:
        h_use_wid = st.checkbox("Walk-in Demand", value=_cdp_ok, disabled=not _cdp_ok, key="h_wid")
        h_use_vd  = st.checkbox("Vehicle Demand", value=_cdp_ok, disabled=not _cdp_ok, key="h_vd")

    run_health = st.button("Run Health Analysis", type="primary", key="run_health",
                            disabled=not health_dealer.strip())

    if run_health and health_dealer.strip():
        inp = health_dealer.strip()
        h_use_prev = health_period == _hpl
        h_dealer_name = inp
        h_effective_ccid = inp if inp.isdigit() else None
        h_sf_data = h_sub_data = None
        h_perf = h_rep = h_mkt = h_lo = h_si = h_roi = h_wid = h_vd = None
        h_source_summary = []

        h_prog = st.empty()
        _h_start = _hdt.datetime.now()

        def _h_progress(msg):
            elapsed = (_hdt.datetime.now() - _h_start).seconds
            h_prog.markdown(
                f"<div style='color:#5b2d8e;font-size:0.9rem;'>⏳ {msg} "
                f"<span style='color:#999;font-size:0.8rem;'>({elapsed}s)</span></div>",
                unsafe_allow_html=True,
            )

        if h_use_sf:
            _h_progress("Querying Salesforce…")
            if h_effective_ccid:
                h_sf_data = fetch_salesforce_by_ccid(h_effective_ccid)
            else:
                h_sf_data = fetch_salesforce(inp)
            if h_sf_data:
                ccids = [r.get("CCID__c") for r in h_sf_data if r.get("CCID__c")]
                if not h_effective_ccid and ccids:
                    h_effective_ccid = ccids[0]
                if h_sf_data[0].get("Name"):
                    h_dealer_name = h_sf_data[0]["Name"]
                h_source_summary.append(f"Salesforce: {len(h_sf_data)} account · CCID {h_effective_ccid}")
            elif h_sf_data is not None:
                h_source_summary.append("Salesforce: no matches")
            if h_sf_data and h_sf_data[0].get("Id"):
                _h_progress("Pulling subscriptions…")
                h_sub_data = fetch_subscriptions(h_sf_data[0]["Id"])
                if h_sub_data:
                    total = sum(float(s.get("SBQQ__NetPrice__c") or 0) for s in h_sub_data)
                    h_source_summary.append(f"Subscriptions: {len(h_sub_data)} · ${total:,.0f}/mo")

        if h_use_admin and h_effective_ccid and _cdp_ok:
            _h_progress("Connecting to admin.cars.com (30s timeout per report)…")
            _admin_error = None
            try:
                import signal as _signal

                def _timeout_handler(signum, frame):
                    raise TimeoutError("admin.cars.com data pull exceeded 90 seconds")

                _signal.signal(_signal.SIGALRM, _timeout_handler)
                _signal.alarm(90)  # hard 90-second ceiling for entire admin block

                try:
                    with _admin_cars.session(restart=False) as _admin:
                        _uuid = _admin.resolve_uuid(h_effective_ccid)
                        if _uuid:
                            for _report, _fetch, _label in [
                                ("Performance Trends", _admin.fetch_performance_trends,
                                 lambda d: f"Performance Trends: {sum(1 for v in d.values() if v is not None)} metrics"),
                                ("Reputation",         _admin.fetch_reputation,
                                 lambda d: f"Reputation: {d.get('rating')}★" if d.get("rating") else None),
                                ("Market Comparison",  _admin.fetch_market_comparison,
                                 lambda d: f"Market Comparison: {d.get('at_pct')}% at market"),
                                ("Listings Optimizer", _admin.fetch_listings_optimizer,
                                 lambda d: f"Listings Optimizer: {len(d.get('within_500_good',[]))+len(d.get('within_500_great',[]))} pricing opps"),
                                ("ROI One-Sheeter",    _admin.fetch_roi_one_sheeter,
                                 lambda d: f"Lead sources: {d['lead_sources'].get('total',0)} connections" if d.get("lead_sources") else None),
                                ("Sales Influence",    _admin.fetch_sales_influence,
                                 lambda d: "DMS: connected" if d and d.get("dms_connected") else "DMS: not connected"),
                            ]:
                                _h_progress(f"Pulling {_report}… (admin.cars.com)")
                                _data = _fetch(_uuid)
                                if _report == "Performance Trends":   h_perf = _data
                                elif _report == "Reputation":         h_rep  = _data
                                elif _report == "Market Comparison":  h_mkt  = _data
                                elif _report == "Listings Optimizer": h_lo   = _data
                                elif _report == "ROI One-Sheeter":    h_roi  = _data
                                elif _report == "Sales Influence":    h_si   = _data
                                if _data:
                                    _lbl = _label(_data)
                                    if _lbl: h_source_summary.append(_lbl)

                            if h_use_wid:
                                _h_progress("Pulling Walk-in Demand…")
                                h_wid = _admin.fetch_walk_in_demand(_uuid)
                                h_source_summary.append("Walk-in Demand: " + ("available" if h_wid else "not available"))
                            if h_use_vd:
                                _h_progress("Pulling Vehicle Demand…")
                                h_vd = _admin.fetch_vehicle_demand(_uuid)
                                h_source_summary.append("Vehicle Demand: " + ("available" if h_vd else "not available"))
                        else:
                            h_source_summary.append("admin.cars.com: UUID not found")
                finally:
                    _signal.alarm(0)  # cancel alarm regardless of outcome

            except TimeoutError as _te:
                _admin_error = "Timed out after 90s"
                h_source_summary.append("admin.cars.com: timed out — proceeding with SF data")
                st.warning("⚠️ admin.cars.com pull timed out (90s). Generating snapshot with Salesforce data only.")
            except Exception as _e:
                _admin_error = str(_e)
                h_source_summary.append(f"admin.cars.com: skipped — {_admin_error[:80]}")
                if "jumpcloud" in _admin_error.lower():
                    st.warning(
                        "⚠️ **admin.cars.com requires sign-in.** Sign in to admin.cars.com "
                        "in the dealer health Chrome window, then click Run Health Analysis again."
                    )
                else:
                    st.warning(f"admin.cars.com unavailable — proceeding with Salesforce data only.")

        _h_progress("Generating health snapshot…")
        data_ctx = build_data_context(
            dealer_name=h_dealer_name, sf_data=h_sf_data,
            perf_data=h_perf, rep_data=h_rep, mkt_data=h_mkt,
            sub_data=h_sub_data, lo_data=h_lo, si_data=h_si,
            roi_data=h_roi, wid_data=h_wid, vd_data=h_vd,
            use_prev_month=h_use_prev,
        )
        h_prog.empty()

        period_label = _hpl if h_use_prev else _hcl
        with st.spinner("Generating health snapshot… (~90s)"):
            h_response = run_health_analysis(h_dealer_name, data_ctx, period_label)

        if h_response.startswith("ERROR:"):
            st.error(h_response)
        else:
            h_scores, _ = parse_scores(h_response)
            st.session_state["health_result"] = {
                "dealer": h_dealer_name, "analysis": h_response, "scores": h_scores,
                "sf_data": h_sf_data, "sub_data": h_sub_data,
                "perf_data": h_perf, "rep_data": h_rep, "mkt_data": h_mkt,
                "lo_data": h_lo, "wid_data": h_wid, "vd_data": h_vd,
                "source_summary": h_source_summary,
            }

        if h_source_summary:
            with st.expander(f"Data sources · {len(h_source_summary)} checks", expanded=False):
                for l in h_source_summary: st.markdown(f"- {l}")

    # Show results
    if "health_result" in st.session_state:
        h_res = st.session_state["health_result"]

        h_c1, h_c2 = st.columns([1, 1])
        if h_c1.button("📄 Export to Google Doc", key="h_export_doc"):
            with st.spinner("Creating Google Doc…"):
                try:
                    _, _hn = parse_scores(h_res["analysis"])
                    doc_url = create_health_doc(
                        dealer_name=h_res["dealer"], scores=h_res.get("scores",[]),
                        narrative=_hn, wid_data=h_res.get("wid_data"),
                        vd_data=h_res.get("vd_data"), sf_data=h_res.get("sf_data"),
                        perf_data=h_res.get("perf_data"),
                    )
                    st.success(f"[Open in Google Docs]({doc_url})")
                except Exception as _e:
                    st.error(f"Export failed: {_e}")
        if h_c2.button("🔍 Also run investigation scan for this store", key="h_to_brief"):
            inp = h_res["dealer"]
            if h_res.get("sf_data") and h_res["sf_data"][0].get("CCID__c"):
                inp = h_res["sf_data"][0]["CCID__c"]
            st.session_state["brief_prefill"] = inp

        _h_scores = h_res.get("scores", [])
        if _h_scores:
            st.markdown(render_score_bars(_h_scores), unsafe_allow_html=True)
        _, _h_narrative = parse_scores(h_res["analysis"])
        st.markdown(_re.sub(r'\$(?!\$)', r'\\$', _h_narrative))

        with st.expander("Raw Salesforce & Subscription Data", expanded=False):
            if h_res.get("sf_data"):
                st.dataframe(pd.DataFrame(h_res["sf_data"]), use_container_width=True)
            if h_res.get("sub_data"):
                st.dataframe(pd.DataFrame(h_res["sub_data"]), use_container_width=True)

    elif not run_health:
        if not _cdp_ok:
            st.info(
                "admin.cars.com is not connected. Health Analysis will run with Salesforce data only. "
                "Launch Chrome on port 9223 (see sidebar) to enable the full dataset."
            )
        else:
            st.info("Enter a dealer name or CCID above and click **Run Health Analysis**.")

# ─── EXPORT ───────────────────────────────────────────────────────────────────
st.divider()
col_exp1, col_exp2, _ = st.columns([2, 2, 6])
with col_exp1:
    if st.button("💾 Export HTML Digest"):
        sys.path.insert(0, os.path.dirname(__file__))
        from biz_scan import build_html_digest

        groups_results = [{
            "group_key":   "dashboard",
            "group_label": group_label,
            "store_count": len(stores),
            "high_count":  len(results["high"]),
            "medium_count": len(results["medium"]),
            "bright_count": len(results["bright_spots"]),
            "flagged":     results["high"] + results["medium"],
            "bright":      results["bright_spots"],
        }]
        html = build_html_digest(groups_results, expirations, [], date.today().isoformat())
        export_dir = os.path.expanduser("~/Documents/Reports/InvestigationScans")
        os.makedirs(export_dir, exist_ok=True)
        fname = os.path.join(export_dir, f"scan_{group_label.replace(' ','_')}_{date.today().isoformat()}.html")
        with open(fname, "w") as f:
            f.write(html)
        st.success(f"Saved → `{fname}`")

with col_exp2:
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.session_state.pop("scan", None)
        st.rerun()
