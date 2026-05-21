#!/usr/bin/env python3
"""
biz_scan.py — Weekly book-of-business health scan.

Pulls Tableau metrics across all accessible dealer groups, runs investigation
triggers, cross-references Salesforce for expiring products and upsell signals,
compares to the previous scan to surface NEW / SUSTAINED / CRITICAL trends,
then writes an HTML digest and prints a console triage.

Usage:
    python3 biz_scan.py                        # full scan, all groups
    python3 biz_scan.py --groups sonic,aca     # specific groups only
    python3 biz_scan.py --email                # also draft a Gmail digest
    python3 biz_scan.py --dry-run              # skip SF queries (Tableau only)
    python3 biz_scan.py --no-history           # ignore prior scan comparison
"""

import argparse
import csv
import io
import json
import os
import subprocess
import sys
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional

sys.path.insert(0, os.path.dirname(__file__))
from investigation_triggers import investigate_stores, _get, _delta, _pct, SCENARIO_META

# ─── CONFIG ───────────────────────────────────────────────────────────────────

TABLEAU_HOST    = "https://us-west-2b.online.tableau.com"
SITE_ID         = "12338861-20b1-46ed-8841-269a5a937edb"
BY_STORE_VIEW   = "a0b9bdce-2db3-4ea0-a2fc-365fd08c5786"


def _load_tableau_pat() -> tuple:
    """Load PAT name + secret. Prefers env vars; falls back to ~/.claude/settings.json."""
    name   = os.environ.get("TABLEAU_PAT_NAME") or os.environ.get("PAT_NAME")
    secret = os.environ.get("TABLEAU_PAT_SECRET") or os.environ.get("PAT_VALUE")
    if not secret:
        try:
            settings_path = os.path.expanduser("~/.claude/settings.json")
            with open(settings_path) as f:
                cfg = json.load(f)
            tab_env = cfg.get("mcpServers", {}).get("tableau", {}).get("env", {})
            name   = name   or tab_env.get("PAT_NAME", "Claude")
            secret = secret or tab_env.get("PAT_VALUE", "")
        except Exception:
            pass
    return (name or "Claude"), (secret or "")


PAT_NAME, PAT_SECRET = _load_tableau_pat()

SF_CLI          = os.path.expanduser("~/.npm-global/bin/sf")
SF_ORG          = "cars-commerce"

HISTORY_DIR     = os.path.expanduser("~/.claude/scan_history")
HISTORY_FILE    = os.path.join(HISTORY_DIR, "biz_scan_latest.json")
EXPORT_DIR      = os.path.expanduser("~/Documents/Reports/InvestigationScans")

# Jake's book of business — 5 clients, ~445 stores
# Asbury is the parent account; Larry H. Miller, Koons, and Herb Chambers
# are sub-groups billed under the Asbury umbrella in Tableau.
ALL_GROUPS = [
    ("sonic",        "Sonic"),
    ("echopark",     "EchoPark MA Group"),
    ("hendrick",     "Hendrick Automotive Group"),
    ("aca",          "Atlantic Coast Automotive MA Group"),
    # Asbury umbrella — output grouped together in triage
    ("asbury",       "Asbury"),
    ("larry_miller", "Larry Miller"),
    ("koons",        "Koons Automotive MA Group"),
    ("herb",         "Herb Chambers MA Group"),
]

# Asbury sub-group keys — displayed together under the Asbury client header
ASBURY_KEYS = {"asbury", "larry_miller", "koons", "herb"}

# Expiration windows (days)
EXPIRY_CRITICAL = 30
EXPIRY_WARN     = 90


# ─── TABLEAU PULL ─────────────────────────────────────────────────────────────

def _tableau_auth() -> str:
    if not PAT_SECRET:
        raise RuntimeError(
            "Tableau PAT not found. Set TABLEAU_PAT_SECRET env var or ensure "
            "~/.claude/settings.json has mcpServers.tableau.env.PAT_VALUE."
        )
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
    # Response is XML: <credentials token="...">
    import xml.etree.ElementTree as ET
    root = ET.fromstring(body)
    ns = {"t": "http://tableau.com/api"}
    creds = root.find("t:credentials", ns)
    if creds is None:
        creds = root.find("credentials")
    if creds is None:
        raise RuntimeError(f"Unexpected Tableau auth response: {body[:200]}")
    return creds.attrib["token"]


def pull_group(token: str, filter_val: str) -> List[Dict]:
    """Pull By Store view for one group, pivot to wide store dicts."""
    encoded = urllib.parse.quote(filter_val)
    url = f"{TABLEAU_HOST}/api/3.22/sites/{SITE_ID}/views/{BY_STORE_VIEW}/data?vf_Maj%20Cust%20Name={encoded}"
    req = urllib.request.Request(url, headers={"X-Tableau-Auth": token})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            raw = r.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"  [WARN] Tableau pull failed for '{filter_val}': {e}", file=sys.stderr)
        return []

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


# ─── SALESFORCE ───────────────────────────────────────────────────────────────

def _sf_query(soql: str) -> List[Dict]:
    """Run a SOQL query via SF CLI, return list of record dicts."""
    try:
        result = subprocess.run(
            [SF_CLI, "data", "query", "--query", soql,
             "--target-org", SF_ORG, "--json"],
            capture_output=True, text=True, timeout=60,
        )
        data = json.loads(result.stdout)
        return data.get("result", {}).get("records", [])
    except Exception as e:
        print(f"  [WARN] SF query failed: {e}", file=sys.stderr)
        return []


def fetch_expirations() -> List[Dict]:
    """Subscriptions expiring within EXPIRY_WARN days."""
    cutoff = (date.today() + timedelta(days=EXPIRY_WARN)).isoformat()
    soql = f"""
        SELECT SBQQ__Account__r.Name, SBQQ__Account__r.CCID__c,
               SBQQ__ProductName__c, SBQQ__NetPrice__c,
               SBQQ__SubscriptionEndDate__c
        FROM SBQQ__Subscription__c
        WHERE SBQQ__SubscriptionEndDate__c <= {cutoff}
        AND SBQQ__SubscriptionEndDate__c >= TODAY
        ORDER BY SBQQ__SubscriptionEndDate__c
        LIMIT 200
    """
    rows = _sf_query(soql.strip())
    results = []
    for r in rows:
        acct = r.get("SBQQ__Account__r", {}) or {}
        days_left = (
            datetime.strptime(r["SBQQ__SubscriptionEndDate__c"], "%Y-%m-%d").date()
            - date.today()
        ).days
        results.append({
            "name":     acct.get("Name", "Unknown"),
            "ccid":     acct.get("CCID__c", ""),
            "product":  r.get("SBQQ__ProductName__c", ""),
            "mrr":      r.get("SBQQ__NetPrice__c", 0),
            "days_left": days_left,
            "severity": "CRITICAL" if days_left <= EXPIRY_CRITICAL else "WARN",
        })
    return results


def fetch_upsell_candidates(bright_ccids: List[str]) -> List[Dict]:
    """Stores with strong metrics (bright spots) that have low product spend."""
    if not bright_ccids:
        return []
    ccid_list = "','".join(bright_ccids[:50])
    soql = f"""
        SELECT Name, CCID__c, Product_Amount__c, Products__c
        FROM Account
        WHERE CCID__c IN ('{ccid_list}')
        AND Product_Amount__c < 3000
        ORDER BY Product_Amount__c ASC
        LIMIT 30
    """
    rows = _sf_query(soql.strip())
    return [
        {
            "name":    r.get("Name", ""),
            "ccid":    r.get("CCID__c", ""),
            "mrr":     r.get("Product_Amount__c", 0),
            "products": r.get("Products__c", ""),
        }
        for r in rows
    ]


# ─── SCAN HISTORY ─────────────────────────────────────────────────────────────

def load_history() -> Dict:
    """Load previous scan results. Returns {} if no history exists."""
    if not os.path.exists(HISTORY_FILE):
        return {}
    try:
        with open(HISTORY_FILE) as f:
            return json.load(f)
    except Exception:
        return {}


def save_history(scan_results: Dict):
    """Save current scan results for next week's comparison."""
    os.makedirs(HISTORY_DIR, exist_ok=True)
    payload = {
        "scan_date": date.today().isoformat(),
        "stores": scan_results,
    }
    with open(HISTORY_FILE, "w") as f:
        json.dump(payload, f, indent=2)


def classify_trend(store_name: str, current_severity: str, history: Dict) -> str:
    """
    NEW       — first time flagged (not in last scan)
    SUSTAINED — flagged last scan too (2 consecutive weeks)
    CRITICAL  — flagged in last 2+ scans (recorded as CRITICAL in history)
    RESOLVED  — was flagged, now clean (not called for clean stores)
    """
    prev = history.get("stores", {}).get(store_name, {})
    if not prev:
        return "NEW"
    prev_sev = prev.get("severity", "")
    if prev_sev == "CRITICAL":
        return "CRITICAL"
    if prev_sev in ("HIGH", "MEDIUM", "SUSTAINED", "NEW"):
        return "SUSTAINED" if current_severity in ("HIGH", "MEDIUM") else "RESOLVED"
    return "NEW"


# ─── HTML DIGEST ──────────────────────────────────────────────────────────────

def _sev_color(sev: str) -> str:
    return {
        "CRITICAL": "#c0392b", "HIGH": "#e67e22",
        "MEDIUM": "#f39c12",   "RESOLVED": "#27ae60",
    }.get(sev, "#666")


def _trend_badge(trend: str) -> str:
    colors = {
        "CRITICAL": ("#c0392b", "#fff"),
        "SUSTAINED": ("#e67e22", "#fff"),
        "NEW": ("#2980b9", "#fff"),
        "RESOLVED": ("#27ae60", "#fff"),
    }
    bg, fg = colors.get(trend, ("#999", "#fff"))
    return f'<span style="background:{bg};color:{fg};padding:2px 7px;border-radius:3px;font-size:11px;font-weight:600;">{trend}</span>'


def build_html_digest(
    groups_results: List[Dict],
    expirations: List[Dict],
    upsell_candidates: List[Dict],
    scan_date: str,
) -> str:
    total_stores = sum(g["store_count"] for g in groups_results)
    total_high   = sum(g["high_count"] for g in groups_results)
    total_med    = sum(g["medium_count"] for g in groups_results)
    total_bright = sum(g["bright_count"] for g in groups_results)
    critical_trends = sum(
        1 for g in groups_results
        for s in g["flagged"]
        if s.get("trend") == "CRITICAL"
    )

    rows_html = ""
    for group in groups_results:
        for entry in group["flagged"]:
            trend = entry.get("trend", "NEW")
            scenarios = ", ".join(
                SCENARIO_META[f["scenario"]]["name"]
                for f in entry["flags"]
                if f["severity"] == "HIGH"
            ) or "Medium flags only"
            top_signal = entry["flags"][0]["signal"] if entry["flags"] else ""
            rows_html += f"""
            <tr>
                <td style="padding:6px 10px;border-bottom:1px solid #eee;">{_trend_badge(trend)}</td>
                <td style="padding:6px 10px;border-bottom:1px solid #eee;font-weight:500;">{entry['store']}</td>
                <td style="padding:6px 10px;border-bottom:1px solid #eee;color:#888;font-size:12px;">{group['group_label']}</td>
                <td style="padding:6px 10px;border-bottom:1px solid #eee;font-size:12px;">{scenarios}</td>
                <td style="padding:6px 10px;border-bottom:1px solid #eee;font-size:12px;color:#555;">{top_signal}</td>
            </tr>"""

    expiry_rows = ""
    for e in expirations[:20]:
        sev_color = "#c0392b" if e["severity"] == "CRITICAL" else "#e67e22"
        expiry_rows += f"""
            <tr>
                <td style="padding:6px 10px;border-bottom:1px solid #eee;color:{sev_color};font-weight:600;">{e['days_left']}d</td>
                <td style="padding:6px 10px;border-bottom:1px solid #eee;font-weight:500;">{e['name']}</td>
                <td style="padding:6px 10px;border-bottom:1px solid #eee;font-size:12px;">{e['product']}</td>
                <td style="padding:6px 10px;border-bottom:1px solid #eee;font-size:12px;">${e['mrr']:,.0f}/mo</td>
            </tr>"""

    upsell_rows = ""
    for u in upsell_candidates[:10]:
        upsell_rows += f"""
            <tr>
                <td style="padding:6px 10px;border-bottom:1px solid #eee;font-weight:500;">{u['name']}</td>
                <td style="padding:6px 10px;border-bottom:1px solid #eee;font-size:12px;">${u['mrr']:,.0f}/mo</td>
                <td style="padding:6px 10px;border-bottom:1px solid #eee;font-size:12px;color:#888;">{u['products'] or '—'}</td>
            </tr>"""

    # Build client-level summary — roll Asbury sub-groups into one row
    CLIENT_ORDER = ["Sonic", "EchoPark MA Group", "Hendrick Automotive Group",
                    "Atlantic Coast Automotive MA Group", "_asbury_combined"]
    asbury_labels = {"Asbury", "Larry Miller", "Koons Automotive MA Group", "Herb Chambers MA Group"}
    asbury_row = {"label": "Asbury Group (incl. LHM, Koons, Herb Chambers)",
                  "store_count": 0, "high_count": 0, "medium_count": 0, "bright_count": 0}
    client_rows = []
    for g in groups_results:
        if g["group_label"] in asbury_labels:
            asbury_row["store_count"] += g["store_count"]
            asbury_row["high_count"]   += g["high_count"]
            asbury_row["medium_count"] += g["medium_count"]
            asbury_row["bright_count"] += g["bright_count"]
        else:
            client_rows.append(g)
    client_rows.append(asbury_row)

    group_summary_rows = ""
    for g in client_rows:
        lbl = g.get("group_label") or g.get("label", "")
        group_summary_rows += f"""
            <tr>
                <td style="padding:6px 10px;border-bottom:1px solid #eee;font-weight:500;">{lbl}</td>
                <td style="padding:6px 10px;border-bottom:1px solid #eee;text-align:center;">{g['store_count']}</td>
                <td style="padding:6px 10px;border-bottom:1px solid #eee;text-align:center;color:#c0392b;font-weight:600;">{g['high_count']}</td>
                <td style="padding:6px 10px;border-bottom:1px solid #eee;text-align:center;color:#e67e22;">{g['medium_count']}</td>
                <td style="padding:6px 10px;border-bottom:1px solid #eee;text-align:center;color:#27ae60;">{g['bright_count']}</td>
            </tr>"""

    return f"""<html>
<head>
<meta charset="UTF-8">
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
  body {{ font-family: Inter, sans-serif; margin: 0; background: #f5f5f5; color: #1a1a2e; }}
  .container {{ max-width: 960px; margin: 0 auto; padding: 24px; }}
  .header {{ background: linear-gradient(135deg, #6B2D8B 0%, #00A88E 100%); color: white; padding: 28px 32px; border-radius: 10px; margin-bottom: 24px; }}
  .header h1 {{ margin: 0 0 4px 0; font-size: 22px; font-weight: 700; }}
  .header p {{ margin: 0; opacity: 0.85; font-size: 14px; }}
  .kpi-row {{ display: flex; gap: 12px; margin-bottom: 24px; }}
  .kpi {{ flex: 1; background: white; border-radius: 8px; padding: 16px 20px; box-shadow: 0 1px 4px rgba(0,0,0,.08); }}
  .kpi .val {{ font-size: 28px; font-weight: 700; color: #6B2D8B; }}
  .kpi .lbl {{ font-size: 12px; color: #888; text-transform: uppercase; letter-spacing: .05em; margin-top: 2px; }}
  .kpi.alert .val {{ color: #c0392b; }}
  .section {{ background: white; border-radius: 8px; padding: 20px 24px; margin-bottom: 20px; box-shadow: 0 1px 4px rgba(0,0,0,.08); }}
  .section h2 {{ font-size: 15px; font-weight: 600; color: #6B2D8B; margin: 0 0 14px 0; border-bottom: 2px solid #f0e8f5; padding-bottom: 8px; }}
  table {{ width: 100%; border-collapse: collapse; }}
  th {{ font-size: 11px; text-transform: uppercase; letter-spacing: .06em; color: #888; padding: 6px 10px; text-align: left; }}
  .empty {{ color: #aaa; font-size: 13px; padding: 12px 0; }}
  .footer {{ text-align: center; color: #aaa; font-size: 11px; margin-top: 24px; }}
</style>
</head>
<body>
<div class="container">

  <div class="header">
    <h1>Book-of-Business Health Scan</h1>
    <p>Weekly automated scan &nbsp;·&nbsp; {scan_date} &nbsp;·&nbsp; {total_stores} stores across 5 clients</p>
  </div>

  <div class="kpi-row">
    <div class="kpi {'alert' if critical_trends else ''}">
      <div class="val">{critical_trends}</div>
      <div class="lbl">Critical Trends (3+ wks)</div>
    </div>
    <div class="kpi {'alert' if total_high else ''}">
      <div class="val">{total_high}</div>
      <div class="lbl">HIGH Flags This Week</div>
    </div>
    <div class="kpi">
      <div class="val">{total_med}</div>
      <div class="lbl">Medium Flags</div>
    </div>
    <div class="kpi">
      <div class="val" style="color:#27ae60">{total_bright}</div>
      <div class="lbl">Bright Spots</div>
    </div>
    <div class="kpi {'alert' if any(e['severity']=='CRITICAL' for e in expirations) else ''}">
      <div class="val">{len(expirations)}</div>
      <div class="lbl">Expiring ≤{EXPIRY_WARN}d</div>
    </div>
  </div>

  <div class="section">
    <h2>Group Summary</h2>
    <table>
      <tr>
        <th>Group</th><th style="text-align:center">Stores</th>
        <th style="text-align:center">HIGH</th><th style="text-align:center">MED</th>
        <th style="text-align:center">Bright</th>
      </tr>
      {group_summary_rows if group_summary_rows else '<tr><td class="empty" colspan="5">No data</td></tr>'}
    </table>
  </div>

  <div class="section">
    <h2>Flagged Stores — Priority Order</h2>
    <table>
      <tr><th>Trend</th><th>Store</th><th>Group</th><th>Scenarios</th><th>Top Signal</th></tr>
      {rows_html if rows_html else '<tr><td class="empty" colspan="5">No flags this week</td></tr>'}
    </table>
  </div>

  <div class="section">
    <h2>Expiring Products (≤{EXPIRY_WARN} days)</h2>
    <table>
      <tr><th>Days Left</th><th>Account</th><th>Product</th><th>MRR</th></tr>
      {expiry_rows if expiry_rows else '<tr><td class="empty" colspan="4">No expirations in window</td></tr>'}
    </table>
  </div>

  <div class="section">
    <h2>Upsell Signals — Bright Spots with Growth Headroom</h2>
    <table>
      <tr><th>Account</th><th>Current MRR</th><th>Products</th></tr>
      {upsell_rows if upsell_rows else '<tr><td class="empty" colspan="3">No upsell candidates identified</td></tr>'}
    </table>
  </div>

  <div class="footer">
    Generated by biz_scan.py · {datetime.now().strftime("%Y-%m-%d %H:%M")} · Full triage in InvestigationScans/
  </div>
</div>
</body>
</html>"""


# ─── CONSOLE TRIAGE ───────────────────────────────────────────────────────────

def print_console_triage(
    groups_results: List[Dict],
    expirations: List[Dict],
    upsell_candidates: List[Dict],
):
    total_stores = sum(g["store_count"] for g in groups_results)
    total_high   = sum(g["high_count"] for g in groups_results)
    total_med    = sum(g["medium_count"] for g in groups_results)
    total_bright = sum(g["bright_count"] for g in groups_results)

    # Client names for header display
    CLIENT_LABELS = {
        "Sonic":                              "SONIC",
        "EchoPark MA Group":                  "ECHOPARK",
        "Hendrick Automotive Group":          "HENDRICK",
        "Atlantic Coast Automotive MA Group": "ACA",
        "Asbury":                             "ASBURY",
        "Larry Miller":                       "ASBURY — LARRY H. MILLER",
        "Koons Automotive MA Group":          "ASBURY — KOONS",
        "Herb Chambers MA Group":             "ASBURY — HERB CHAMBERS",
    }
    ASBURY_LABELS = {"Asbury", "Larry Miller", "Koons Automotive MA Group", "Herb Chambers MA Group"}

    print(f"\n{'═'*70}")
    print(f"  BOOK-OF-BUSINESS SCAN  |  {date.today().isoformat()}")
    print(f"  {total_stores} stores across 5 clients  |  {total_high} HIGH  {total_med} MED  {total_bright} bright")
    print(f"{'═'*70}")

    # Print non-Asbury groups first, then Asbury umbrella
    non_asbury = [g for g in groups_results if g["group_label"] not in ASBURY_LABELS]
    asbury_groups = [g for g in groups_results if g["group_label"] in ASBURY_LABELS]

    def _print_group(group):
        if not group["flagged"] and not group["bright"]:
            return
        label = CLIENT_LABELS.get(group["group_label"], group["group_label"].upper())
        print(f"\n── {label} ({group['store_count']} stores) ──")
        for entry in group["flagged"]:
            trend = entry.get("trend", "NEW")
            prefix = {"CRITICAL": "🔴", "SUSTAINED": "🟠", "NEW": "🔵"}.get(trend, "⚪")
            sev = "HIGH" if any(f["severity"] == "HIGH" for f in entry["flags"]) else "MED"
            print(f"  {prefix} [{sev}/{trend}] {entry['store']}  (CCID {entry['ccid']})")
            for flag in entry["flags"][:2]:
                print(f"       Scenario {flag['scenario']}: {flag['signal']}")
        for b in group["bright"][:3]:
            print(f"  ✓ [BRIGHT] {b['store']}  —  {b['signal']}")

    for group in non_asbury:
        _print_group(group)

    # Asbury umbrella — combined header then each sub-group
    asbury_any = any(g["flagged"] or g["bright"] for g in asbury_groups)
    if asbury_any:
        asbury_stores = sum(g["store_count"] for g in asbury_groups)
        asbury_high   = sum(g["high_count"]   for g in asbury_groups)
        asbury_med    = sum(g["medium_count"]  for g in asbury_groups)
        print(f"\n{'─'*70}")
        print(f"  ASBURY GROUP  ({asbury_stores} stores — {asbury_high}H {asbury_med}M)")
        print(f"  Includes: Asbury · Larry H. Miller · Koons · Herb Chambers")
        print(f"{'─'*70}")
        for group in asbury_groups:
            _print_group(group)

    if expirations:
        print(f"\n── EXPIRING PRODUCTS ({len(expirations)}) ──")
        for e in expirations[:10]:
            flag = "🔴" if e["severity"] == "CRITICAL" else "🟡"
            print(f"  {flag} {e['days_left']}d  {e['name']}  —  {e['product']}  (${e['mrr']:,.0f}/mo)")

    if upsell_candidates:
        print(f"\n── UPSELL SIGNALS ({len(upsell_candidates)}) ──")
        for u in upsell_candidates[:5]:
            print(f"  ↑ {u['name']}  —  ${u['mrr']:,.0f}/mo  |  {u['products'] or 'minimal package'}")

    print()


# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Weekly book-of-business health scan.")
    parser.add_argument("--groups", help="Comma-separated group keys (e.g. sonic,aca)")
    parser.add_argument("--dry-run",    action="store_true", help="Skip SF queries")
    parser.add_argument("--no-history", action="store_true", help="Ignore prior scan history")
    parser.add_argument("--no-export",  action="store_true", help="Skip HTML file export")
    parser.add_argument("--email",      action="store_true", help="Print email-ready digest summary")
    args = parser.parse_args()

    # Determine which groups to scan
    if args.groups:
        group_keys = {k.strip().lower() for k in args.groups.split(",")}
        groups_to_scan = [(k, v) for k, v in ALL_GROUPS if k in group_keys]
    else:
        groups_to_scan = ALL_GROUPS

    print(f"Authenticating with Tableau...", end=" ", flush=True)
    try:
        token = _tableau_auth()
        print("OK")
    except Exception as e:
        print(f"FAILED: {e}")
        sys.exit(1)

    history = {} if args.no_history else load_history()
    scan_date = date.today().isoformat()
    current_scan_state = {}

    groups_results = []
    all_bright_ccids = []

    for group_key, filter_val in groups_to_scan:
        print(f"Pulling {filter_val}...", end=" ", flush=True)
        stores = pull_group(token, filter_val)
        if not stores:
            print("no data (RLS or empty)")
            continue
        print(f"{len(stores)} stores")

        results = investigate_stores(stores)

        # Classify trends against history
        flagged_with_trend = []
        for bucket in ("high", "medium"):
            for entry in results[bucket]:
                sev = "HIGH" if bucket == "high" else "MEDIUM"
                trend = classify_trend(entry["store"], sev, history)
                entry["trend"] = trend
                flagged_with_trend.append(entry)
                current_scan_state[entry["store"]] = {
                    "ccid": entry["ccid"],
                    "severity": "CRITICAL" if trend == "CRITICAL" else sev,
                    "group": group_key,
                }

        # Track bright spots for upsell query
        bright_entries = [
            {"store": b["store"], "ccid": b["ccid"], "signal": b["signal"]}
            for b in results["bright_spots"]
        ]
        all_bright_ccids.extend(b["ccid"] for b in results["bright_spots"] if b["ccid"])

        # Sort flagged: CRITICAL first, then SUSTAINED, then NEW; HIGH before MEDIUM
        trend_order = {"CRITICAL": 0, "SUSTAINED": 1, "NEW": 2}
        sev_order   = {"HIGH": 0, "MEDIUM": 1}
        flagged_with_trend.sort(key=lambda e: (
            trend_order.get(e.get("trend", "NEW"), 9),
            sev_order.get("HIGH" if any(f["severity"] == "HIGH" for f in e["flags"]) else "MEDIUM", 9),
        ))

        groups_results.append({
            "group_key":   group_key,
            "group_label": filter_val,
            "store_count": len(stores),
            "high_count":  len(results["high"]),
            "medium_count": len(results["medium"]),
            "bright_count": len(results["bright_spots"]),
            "flagged":     flagged_with_trend,
            "bright":      bright_entries,
        })

    if not groups_results:
        print("No groups returned data. Check PAT_SECRET and Tableau access.")
        sys.exit(1)

    # SF queries
    expirations = []
    upsell_candidates = []
    if not args.dry_run:
        print("Querying Salesforce for expirations...", end=" ", flush=True)
        expirations = fetch_expirations()
        print(f"{len(expirations)} found")

        print("Querying Salesforce for upsell signals...", end=" ", flush=True)
        upsell_candidates = fetch_upsell_candidates(all_bright_ccids)
        print(f"{len(upsell_candidates)} found")

    # Save history
    if not args.no_history:
        save_history(current_scan_state)

    # Console output
    print_console_triage(groups_results, expirations, upsell_candidates)

    # HTML export
    if not args.no_export:
        os.makedirs(EXPORT_DIR, exist_ok=True)
        html = build_html_digest(groups_results, expirations, upsell_candidates, scan_date)
        fname = f"biz_scan_{scan_date}.html"
        fpath = os.path.join(EXPORT_DIR, fname)
        with open(fpath, "w") as f:
            f.write(html)
        # Keep a symlink to latest for easy browser open
        latest = os.path.join(EXPORT_DIR, "biz_scan_latest.html")
        if os.path.exists(latest):
            os.remove(latest)
        os.symlink(fpath, latest)
        print(f"HTML digest: {fpath}")
        print(f"  open ~/Documents/Reports/InvestigationScans/biz_scan_latest.html")

    if args.email:
        total_high = sum(g["high_count"] for g in groups_results)
        total_stores = sum(g["store_count"] for g in groups_results)
        critical = [e for g in groups_results for e in g["flagged"] if e.get("trend") == "CRITICAL"]
        print("\n── EMAIL DIGEST ──")
        print(f"Subject: Book-of-Business Scan — {scan_date} | {total_high} HIGH flags across {total_stores} stores")
        print()
        if critical:
            print(f"Critical trends (3+ weeks): {', '.join(e['store'] for e in critical[:5])}")
        print(f"Full digest: ~/Documents/Reports/InvestigationScans/biz_scan_{scan_date}.html")


if __name__ == "__main__":
    main()
