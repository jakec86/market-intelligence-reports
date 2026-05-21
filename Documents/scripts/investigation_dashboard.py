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

TABLEAU_HOST  = "https://us-west-2b.online.tableau.com"
SITE_ID       = "12338861-20b1-46ed-8841-269a5a937edb"
BY_STORE_VIEW = "a0b9bdce-2db3-4ea0-a2fc-365fd08c5786"
PAT_NAME      = os.environ.get("TABLEAU_PAT_NAME", "Claude")
PAT_SECRET    = os.environ.get("TABLEAU_PAT_SECRET", "")

SF_CLI = "/Users/jcrawley/.npm-global/bin/sf"
SF_ORG = "cars-commerce"

ADMIN_BASE = "https://admin.cars.com"

GROUP_OPTIONS = {
    "Sonic Automotive":                "Sonic",
    "ACA (Atlantic Coast Auto)":       "Atlantic Coast Automotive MA Group",
    "Hendrick Automotive":             "Hendrick Automotive Group",
    "Asbury Automotive":               "Asbury",
    "Herb Chambers":                   "Herb Chambers MA Group",
    "Greenway Auto":                   "Greenway MA Group",
    "Koons Automotive":                "Koons Automotive MA Group",
    "EchoPark":                        "EchoPark MA Group",
    "Indigo Auto":                     "Indigo Auto MA Group",
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
        return json.loads(r.read())["credentials"]["token"]


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


def _sf_expirations(days: int = 90) -> List[Dict]:
    cutoff = date.today().replace(day=1).__class__(
        date.today().year + (date.today().month // 12),
        (date.today().month % 12) + 1,
        1,
    ).isoformat() if days > 60 else date.today().isoformat()
    from datetime import timedelta
    cutoff = (date.today() + timedelta(days=days)).isoformat()
    return _sf_query(
        f"SELECT SBQQ__Account__r.Name, SBQQ__Account__r.CCID__c, "
        f"SBQQ__ProductName__c, SBQQ__NetPrice__c, SBQQ__SubscriptionEndDate__c "
        f"FROM SBQQ__Subscription__c "
        f"WHERE SBQQ__SubscriptionEndDate__c <= {cutoff} "
        f"AND SBQQ__SubscriptionEndDate__c >= TODAY "
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

    prompt = f"""You are a Cars.com account executive preparing for a dealer call.
Generate exactly 3 talking points for a call with {store_name} ({city}).

CURRENT METRICS:
{metrics_txt}

INVESTIGATION FLAGS:
{flag_lines if flag_lines else "No active flags — store is performing well."}

Rules:
- TP1: open with a specific WIN or positive data point (use actual numbers)
- TP2: the highest-priority opportunity framed as revenue or competitive impact (estimate even if rough)
- TP3: a specific question or next step tied to a particular report or product
- Each TP must use real numbers from the data above
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


def _admin_links(ccid: str) -> str:
    if not ccid:
        return ""
    uuid_cache = os.path.expanduser("~/.claude/aca_uuid_cache.json")
    uuid = None
    try:
        with open(uuid_cache) as f:
            cache = json.load(f)
        uuid = cache.get(ccid)
    except Exception:
        pass

    links = [f'<a href="https://admin.cars.com/dealers/all/reports?query={ccid}" target="_blank">Search admin.cars.com</a>']
    if uuid:
        base = f"https://admin.cars.com/dealers/{uuid}/reports"
        links += [
            f'<a href="{base}/performance_trends" target="_blank">Performance Trends</a>',
            f'<a href="{base}/demand_signals" target="_blank">Demand Signals</a>',
            f'<a href="{base}/listings_optimizer" target="_blank">Listings Optimizer</a>',
        ]
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
        st.success("● Tableau PAT configured")
    else:
        st.error("✗ TABLEAU_PAT_SECRET not set")


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

        expirations = []
        if show_expirations:
            with st.spinner("Checking Salesforce for expirations…"):
                expirations = _sf_expirations(expiry_days)

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
tab_book, tab_brief, tab_expiry = st.tabs(["📋 Flagged Stores", "🔍 Store Brief", "⚠️ Expirations & Upsell"])

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

            # admin.cars.com quick links
            st.markdown(_admin_links(ccid), unsafe_allow_html=True)

            # Talking points button
            store_metrics = next((s for s in stores if s["Customer Name"] == store_name), {})
            if st.button("⚡ Generate Talking Points", key=f"tp_{ccid}"):
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

    col_inp, col_btn = st.columns([4, 1])
    with col_inp:
        brief_store = st.text_input(
            "Store name or CCID",
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

        # Quick links
        st.markdown(_admin_links(brief["ccid"]), unsafe_allow_html=True)

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
    if not expirations:
        if show_expirations:
            st.info("No expiring products found in the selected window, or SF query was skipped.")
        else:
            st.info("Enable 'Show expiring products' in the sidebar and re-run.")
    else:
        st.subheader(f"Expiring Products ({len(expirations)})")

        expiry_rows = []
        for e in expirations:
            days = _days_left(e)
            acct = (e.get("SBQQ__Account__r") or {}) if isinstance(e.get("SBQQ__Account__r"), dict) else {}
            name = acct.get("Name") or e.get("SBQQ__Account__r", {}).get("Name", "Unknown") if isinstance(e.get("SBQQ__Account__r"), dict) else "Unknown"
            expiry_rows.append({
                "Days Left":  days,
                "Account":    name,
                "Product":    e.get("SBQQ__ProductName__c", ""),
                "MRR":        f"${e.get('SBQQ__NetPrice__c', 0):,.0f}",
                "Expires":    e.get("SBQQ__SubscriptionEndDate__c", ""),
                "_days":      days,
            })

        expiry_rows.sort(key=lambda r: r["_days"])
        expiry_df = pd.DataFrame([{k: v for k, v in r.items() if k != "_days"} for r in expiry_rows])

        def _color_days(val):
            try:
                d = int(val)
                if d <= 30:
                    return "color: #c0392b; font-weight: 700"
                if d <= 60:
                    return "color: #d97706; font-weight: 600"
            except Exception:
                pass
            return ""

        st.dataframe(
            expiry_df.style.applymap(_color_days, subset=["Days Left"]),
            use_container_width=True,
            hide_index=True,
        )

    # Upsell signals from current scan
    st.divider()
    st.subheader("Upsell Signals — Bright Spots with Growth Headroom")

    bright_ccids = [b["ccid"] for b in results["bright_spots"] if b["ccid"]]
    if not bright_ccids:
        st.info("No bright spots identified in current scan.")
    else:
        with st.spinner("Checking Salesforce for product spend…"):
            upsell_recs = []
            if bright_ccids:
                ccid_list = "','".join(bright_ccids[:30])
                upsell_recs = _sf_query(
                    f"SELECT Name, CCID__c, Product_Amount__c, Products__c "
                    f"FROM Account WHERE CCID__c IN ('{ccid_list}') "
                    f"AND Product_Amount__c < 3000 ORDER BY Product_Amount__c ASC LIMIT 20"
                )
        if upsell_recs:
            upsell_df = pd.DataFrame([{
                "Store":       r.get("Name", ""),
                "CCID":        r.get("CCID__c", ""),
                "Current MRR": f"${r.get('Product_Amount__c', 0):,.0f}/mo",
                "Products":    r.get("Products__c", "") or "—",
            } for r in upsell_recs])
            st.dataframe(upsell_df, use_container_width=True, hide_index=True)
            st.caption(
                f"{len(upsell_recs)} stores with strong metrics (both VDPs and Connections growing) "
                f"and MRR < $3,000/mo — prime growth conversation candidates."
            )
        else:
            st.info("No upsell candidates found (SF query returned no results).")

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
