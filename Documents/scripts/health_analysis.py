"""
health_analysis.py — Shared logic for the Dealer Health Dashboard.

Imported by both dealer_health.py (standalone app) and
investigation_dashboard.py (integrated Tab 4). Contains no Streamlit calls.
"""

import io
import json
import os
import re as _re
import subprocess
import tempfile
import datetime
from typing import List, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build as _gapi_build
from googleapiclient.http import MediaIoBaseUpload

import admin_cars  # CDP scraper — requires Chrome running on port 9223

# ─── CONFIG ───────────────────────────────────────────────────────────────────

SF_CLI = "/Users/jcrawley/.npm-global/bin/sf"
SF_ORG = "cars-commerce"

SF_QUERY = """SELECT
    Id, Name, Type, Industry, OEM__c, Account_Status__c, DI_Package__c,
    BillingCity, BillingState, Phone, Website, CCID__c,
    OEM_Deal__c, Product_Amount__c, Cancelled_Product_Amount__c,
    Account_Live_Date__c, Performance_Onboarding_Date__c,
    Dealer_Code__c, Account_Notes__c
FROM Account
WHERE Name LIKE '%{dealer}%'
ORDER BY Name
LIMIT 20"""

SF_QUERY_BY_CCID = SF_QUERY.replace(
    "WHERE Name LIKE '%{dealer}%'",
    "WHERE CCID__c = '{ccid}'",
).replace("LIMIT 20", "LIMIT 5")

SF_SUBSCRIPTIONS_QUERY = """SELECT
    Name,
    SBQQ__Product__r.Name,
    SBQQ__SubscriptionStartDate__c,
    SBQQ__SubscriptionEndDate__c,
    SBQQ__Quantity__c,
    SBQQ__NetPrice__c,
    SBQQ__ListPrice__c,
    Line_of_Business__c
FROM SBQQ__Subscription__c
WHERE SBQQ__Account__c = '{account_id}'
  AND (SBQQ__SubscriptionEndDate__c = NULL OR SBQQ__SubscriptionEndDate__c >= TODAY)
ORDER BY SBQQ__NetPrice__c DESC NULLS LAST
LIMIT 50"""

# ─── SYSTEM PROMPT ────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a Cars Commerce dealer health analyst. You use the Dealer Growth Triangle framework to assess dealer performance.

## Dealer Growth Triangle

Three forces drive dealer performance:

    Pricing Position
       /        \\
      /          \\
Days on Lot ---- Market Share

- Pricing too high → increases DOL → erodes margins → costs market share
- Pricing too aggressive → moves metal but sacrifices profitability
- Right-priced inventory → earns badges → drives VDPs → generates leads → wins share

GROI (Gross Return on Investment) = Gross % of Sale × Turn Rate. Target: minimum 120.

## Your Task

**REQUIRED — start your response with this block, no text before it:**

---SCORES---
Inventory Health|<integer 0-100>|<green|yellow|red>|<↑|↓|→>|<one key driver phrase>
Pricing Position|<integer 0-100>|<green|yellow|red>|<↑|↓|→>|<one key driver phrase>
Engagement (VDPs)|<integer 0-100>|<green|yellow|red>|<↑|↓|→>|<one key driver phrase>
Reputation|<integer 0-100>|<green|yellow|red>|<↑|↓|→>|<one key driver phrase>
Lead Performance|<integer 0-100>|<green|yellow|red>|<↑|↓|→>|<one key driver phrase>
Marketplace Investment|<integer 0-100>|<green|yellow|red>|<↑|↓|→>|<one key driver phrase>
---END SCORES---

Color thresholds: green = 75–100, yellow = 50–74, red = 0–49.
Trend: ↑ improving MoM, ↓ declining MoM, → flat/mixed.

**Keep responses tight and scannable. Use bullets over paragraphs. Bold key numbers. Every section must be completed.**

Then continue with the full snapshot:

### 📊 Health Snapshot — [Dealer Name]

---

### 🔑 Key Findings

Max 5 bullets. Each bullet = one bold headline (≤8 words) + one data point. No prose.

- **🟢 [Positive]** — metric: value (source)
- **🟡 [Watch]** — metric: value (source)
- **🔴 [Risk]** — metric: value (source)

---

### 🚀 Growth Opportunities

Up to 4 opportunities, ranked by impact. Tight format:

**1. [Action headline]**
> **Do:** [specific vehicle / stock# / price move]
> **Lift:** [+X VDPs, $Y revenue, X badge upgrades]
> **Signal:** [metric that confirms it worked]

---

### 📈 Market Demand Analysis

Only include if Walk-in Demand or Vehicle Demand data is present. 3–4 bullets max. Omit entirely if no data.

---

### ⚠️ Risks

Bullets only. Bold the metric, one-line plain-English risk.

---

### 📋 Data Gaps

DMS connectivity only. Skip if connected.

## Rules

- **Inventory metric = Avg Daily Vehicles (not Unique VINs).** Unique VINs inflate counts by including wholesales, trades, and short-cycle units — they do not reflect actual stocking levels. Use Avg Daily as the primary inventory gauge for all inventory-related findings and benchmarks.
- **Badge pricing language must be direct action:** "Reduce [YMMT] by $X to earn [Good/Great Deal] badge" — never "needs attention" or vague framing.
- **Be specific** — name vehicles, stock numbers, price points, market segments.
- **Frame in revenue impact** — "$X/mo" beats "down 7%".
- **Dealer-friendly language** — "price to earn a Great Deal badge" not "optimize distribution".
- **Marketplace products matter** — tie opportunities to current product tier.
- **When Listings Optimizer data is present, USE IT.** "Within $500" vehicles = cite by YMMT + stock# as top Growth Opportunities.
- **KPI benchmarks:** Turn <30 days used, Aging <15% over 60 days, GROI 120+ (DMS only), Reputation 4.5+.
- **Fair/Above Badge %** is the primary merchandising proxy.
- All MoM deltas are percentage changes vs. prior month.
- SRPs are not a current focus — do not build findings around them."""

# ─── SALESFORCE ───────────────────────────────────────────────────────────────

def _run_sf_query(query: str) -> Optional[List[dict]]:
    try:
        result = subprocess.run(
            [SF_CLI, "data", "query", "--query", query, "--target-org", SF_ORG, "--json"],
            capture_output=True, text=True, timeout=90,
        )
        idx = result.stdout.find("{")
        if idx == -1:
            return []
        data = json.loads(result.stdout[idx:])
        if data.get("status") == 0 and data["result"]["totalSize"] > 0:
            records = data["result"]["records"]
            for r in records:
                r.pop("attributes", None)
            return records
        return []
    except Exception as e:
        print(f"[WARN] SF query failed: {e}")
        return None


def fetch_salesforce(dealer_name: str) -> Optional[List[dict]]:
    return _run_sf_query(SF_QUERY.format(dealer=dealer_name.replace("'", "\\'")))


def fetch_salesforce_by_ccid(ccid: str) -> Optional[List[dict]]:
    return _run_sf_query(SF_QUERY_BY_CCID.format(ccid=ccid.replace("'", "\\'")))


def fetch_subscriptions(account_id: str) -> Optional[List[dict]]:
    records = _run_sf_query(SF_SUBSCRIPTIONS_QUERY.format(account_id=account_id.replace("'", "\\'")))
    if not records:
        return records
    for r in records:
        prod_ref = r.pop("SBQQ__Product__r", None) or {}
        if isinstance(prod_ref, dict):
            r["Product_Name"] = prod_ref.get("Name")
    return records


# ─── DATA CONTEXT ─────────────────────────────────────────────────────────────

def build_data_context(
    dealer_name: str,
    sf_data,
    perf_data: Optional[dict],
    rep_data: Optional[dict],
    mkt_data: Optional[dict],
    sub_data: Optional[List[dict]] = None,
    lo_data: Optional[dict] = None,
    si_data: Optional[dict] = None,
    roi_data: Optional[dict] = None,
    wid_data: Optional[dict] = None,
    vd_data: Optional[dict] = None,
    use_prev_month: bool = False,
) -> str:
    parts = [f"# Data for: {dealer_name}\n"]

    if sf_data is not None:
        parts.append("## Salesforce Account Data")
        if sf_data:
            for i, rec in enumerate(sf_data, 1):
                parts.append(f"\n### Account {i}")
                for k, v in rec.items():
                    if v is not None and k != "Id":
                        parts.append(f"- **{k}**: {v}")
        else:
            parts.append("No matching accounts found.")

    if sub_data:
        parts.append("\n## Active Marketplace Subscriptions (Salesforce → Customer360 → Live Products)")
        total_mrr = 0.0
        for sub in sub_data:
            prod = sub.get("Product_Name") or sub.get("Name") or "Unknown product"
            qty = sub.get("SBQQ__Quantity__c")
            price = sub.get("SBQQ__NetPrice__c")
            start = sub.get("SBQQ__SubscriptionStartDate__c")
            lob = sub.get("Line_of_Business__c")
            line = f"- **{prod}**"
            if qty: line += f" × {qty:g}"
            if price is not None:
                line += f" — ${price:,.2f}"
                try: total_mrr += float(price)
                except (TypeError, ValueError): pass
            if lob: line += f" ({lob})"
            if start: line += f" — active since {start}"
            parts.append(line)
        if total_mrr > 0:
            parts.append(f"- **Total active subscription value: ${total_mrr:,.2f}**")

    if perf_data:
        _td = datetime.date.today()
        _pm_dt = (_td.replace(day=1) - datetime.timedelta(days=1))
        _period_label = (f"{_pm_dt.strftime('%B %Y')} (complete month)" if use_prev_month
                         else f"{_td.strftime('%B %Y')} (MTD)")
        parts.append(f"\n## Performance Trends (admin.cars.com — {_period_label})")
        labels = {
            "avg_inventory": "Monthly Avg Inventory",
            "avg_days_live": "Avg Days Live (days on lot)",
            "under_merch":   "Minimally Merchandised vehicles (avg daily %)",
            "vdps":          "VDPs (monthly total)",
            "connections":   "Connections / Total Leads (monthly)",
            "fair_above_badges": "Fair/Above Badge vehicles (monthly)",
            "reviews":       "New Reviews (this month)",
        }
        _split_keys = {"avg_inventory", "vdps", "connections"}
        for key, label in labels.items():
            primary = perf_data.get(f"{key}_pp" if use_prev_month else f"{key}_cp")
            delta = None if use_prev_month else perf_data.get(f"{key}_delta_pct")
            if primary is not None:
                delta_str = f" ({delta:+.1f}% MoM)" if delta is not None else ""
                value_str = f"{primary:.1f}" if key == "avg_days_live" else f"{primary:,.0f}"
                parts.append(f"- {label}: {value_str}{delta_str}")
                if key in _split_keys:
                    used_cp = perf_data.get(f"{key}_used_cp")
                    new_cp  = perf_data.get(f"{key}_new_cp")
                    if used_cp is not None or new_cp is not None:
                        parts.append(f"  - Used: {used_cp:,.0f if used_cp else 'N/A'} / New: {new_cp:,.0f if new_cp else 'N/A'}")

    if rep_data:
        parts.append("\n## Reputation Health")
        if rep_data.get("rating") is not None:
            parts.append(f"- Overall Rating: {rep_data['rating']}★ ({rep_data.get('review_count', 'N/A')} total reviews)")
        if rep_data.get("dma_avg_rating") is not None:
            parts.append(f"- Market context: DMA avg {rep_data['dma_avg_rating']}★ | National OEM avg {rep_data.get('national_avg_rating')}★")
        for field, label in [("pricing_transparency","Pricing Transparency"),("lead_response_rate_pct","Lead response rate"),("lead_handling_rating","Lead handling rating")]:
            if rep_data.get(field) is not None:
                parts.append(f"- {label}: {rep_data[field]}{'★' if 'rating' in field else '%' if 'pct' in field else ''}")

    if mkt_data:
        parts.append("\n## Market Comparison (Demand Signals — Price Comparison)")
        parts.append(f"- Above Market (>105%): {mkt_data.get('above_pct',0)}% ({mkt_data.get('above_count',0)} vehicles)")
        parts.append(f"- At Market: {mkt_data.get('at_pct',0)}% ({mkt_data.get('at_count',0)} vehicles)")
        parts.append(f"- Under Market (<95%): {mkt_data.get('under_pct',0)}% ({mkt_data.get('under_count',0)} vehicles)")

    if lo_data:
        parts.append("\n## Listings Optimizer (admin.cars.com)")
        if lo_data.get("merch_complete_pct") is not None:
            parts.append(f"- Merchandising: {lo_data['merch_complete_pct']:.1f}% complete ({int(lo_data.get('merch_needs_attention_count') or 0)} need attention)")
        badges = lo_data.get("badge_details") or []
        if badges:
            parts.append("\n### Badge impact (engagement per badge tier)")
            parts.append("| Badge | Vehicles | % of inv | VDPs / VIN | Connections / VIN |")
            parts.append("|---|---|---|---|---|")
            for b in badges:
                parts.append(f"| {b['badge']} | {int(b.get('vehicles') or 0)} | {b.get('pct_of_inventory',0):.1f}% | {b.get('vdps_per_vin',0):.1f} | {b.get('connections_per_vin',0):.2f} |")
        for tier, heading in [("within_500_good","Vehicles within $500 of earning the Good Badge"),("within_500_great","Vehicles within $500 of earning the Great Badge")]:
            ops = lo_data.get(tier) or []
            if ops:
                parts.append(f"\n### {heading}")
                for v in ops:
                    parts.append(f"- **{v['ymmt']}** (stock {v['stock_num']}) — priced ${v['price']:,.0f}, {int(v.get('days_live') or 0)} days live, reduce by **${v['reduce_by']:,.0f}**")
        stock_split = lo_data.get("stock_type_breakdown") or {}
        if stock_split:
            parts.append("\n### Used vs. New inventory performance (last 7 days)")
            for stype, metrics in stock_split.items():
                if not metrics: continue
                parts.append(f"\n**{stype}:**")
                for mname, val in metrics.items():
                    if val is None: continue
                    if "Price" in mname or "price" in mname: parts.append(f"- {mname}: ${val:,.2f}")
                    elif "Photos" in mname or "Days" in mname: parts.append(f"- {mname}: {val:.1f}")
                    else: parts.append(f"- {mname}: {val:,.0f}")

    if roi_data and roi_data.get("lead_sources"):
        ls = roi_data["lead_sources"]
        parts.append(f"\n## Lead Source Breakdown (ROI One-Sheeter — {ls.get('month','current month')})")
        total = ls.get("total") or 0
        for label, key in [("Phone leads","phone"),("Email leads","email"),("Chat","chat"),("Website transfers","website_transfers"),("Walk-ins","walk_ins")]:
            val = ls.get(key) or 0
            if val:
                parts.append(f"- {label}: **{val}** ({(val/total*100) if total else 0:.0f}% of connections)")
        parts.append(f"- **Total connections: {total}**")
        if roi_data.get("leads_per_vin") is not None:
            parts.append(f"- Leads per VIN: {roi_data['leads_per_vin']:.2f}")

    if si_data:
        parts.append("\n## Sales Influence Summary (admin.cars.com — DMS-backed)")
        if si_data.get("dms_connected"):
            for field, label in [("leads","Leads (attributed)"),("connections","Connections (attributed)"),("influenced_sales","Cars.com-influenced sales"),("influenced_sales_pct","% of sales influenced")]:
                if si_data.get(field) is not None:
                    parts.append(f"- {label}: {si_data[field]:,.1f}" if "pct" in field else f"- {label}: {si_data[field]:,.0f}")
        else:
            parts.append("- No DMS feed connected — GROI/Turn and influenced-sales data unavailable.")

    if sf_data is None and not any([perf_data, rep_data, mkt_data, lo_data]):
        parts.append("\n*No data sources returned results. Analysis will be limited.*")

    if wid_data and wid_data.get("rows"):
        parts.append("\n## Walk-in Demand (admin.cars.com — DMA foot traffic index)")
        cols = wid_data.get("cols", [])
        for row in wid_data["rows"][:10]:
            parts.append("- " + " | ".join(f"{c}: {v}" for c, v in zip(cols, row)))

    if vd_data and vd_data.get("rows"):
        parts.append("\n## Vehicle Demand — Top Searched Segments (DMA)")
        cols = vd_data.get("cols", [])
        for row in vd_data["rows"][:5]:
            parts.append("- " + " | ".join(f"{c}: {v}" for c, v in zip(cols, row)))

    return "\n".join(parts)


# ─── SCORE PARSING ────────────────────────────────────────────────────────────

def parse_scores(text: str) -> tuple:
    """Extract ---SCORES--- block. Returns (scores_list, narrative_text)."""
    m = _re.search(r"---SCORES---\n(.*?)\n---END SCORES---\n?", text, _re.DOTALL)
    if not m:
        return [], text
    scores = []
    for line in m.group(1).strip().splitlines():
        parts = [p.strip() for p in line.split("|")]
        if len(parts) >= 5:
            try:
                scores.append({"name": parts[0], "score": int(parts[1]),
                                "color": parts[2], "trend": parts[3], "driver": parts[4]})
            except (ValueError, IndexError):
                pass
    return scores, (text[:m.start()] + text[m.end():]).strip()


_SCORE_GRADIENTS = {
    "green":  ("linear-gradient(90deg,#22c55e,#16a34a)", "#166534"),
    "yellow": ("linear-gradient(90deg,#f59e0b,#d97706)", "#92400e"),
    "red":    ("linear-gradient(90deg,#f87171,#dc2626)", "#991b1b"),
}


def extract_snapshot_header(narrative: str) -> tuple:
    """
    Pull the '### 📊 Health Snapshot — [Name]' line out of the narrative.
    Returns (header_line, remaining_narrative).
    The header should render ABOVE the score bars.
    """
    import re as _re2
    m = _re2.search(r"(###\s*📊[^\n]+)", narrative)
    if not m:
        return "", narrative
    header = m.group(1).strip()
    # Remove the header line (and the --- divider that usually follows) from narrative
    remaining = narrative[: m.start()] + narrative[m.end():]
    remaining = _re2.sub(r"^\s*---\s*\n", "", remaining.lstrip())
    return header, remaining.strip()


def render_score_bars(scores: list) -> str:
    if not scores:
        return ""
    rows = []
    for s in scores:
        grad, text_color = _SCORE_GRADIENTS.get(s["color"], _SCORE_GRADIENTS["yellow"])
        pct = max(0, min(100, s["score"]))
        rows.append(
            f'<div style="margin-bottom:10px">'
            f'<div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:3px">'
            f'<span style="font-size:13px;font-weight:600;color:#111827">{s["name"]}</span>'
            f'<span style="font-size:13px;font-weight:700;color:{text_color}">{pct}%&nbsp;{s["trend"]}</span>'
            f'</div>'
            f'<div style="background:#f0ebf8;border-radius:4px;height:8px;overflow:hidden">'
            f'<div style="width:{pct}%;height:100%;border-radius:4px;background:{grad}"></div>'
            f'</div>'
            f'<div style="font-size:11px;color:#6b7280;margin-top:2px">{s["driver"]}</div>'
            f'</div>'
        )
    return f'<div style="margin-bottom:20px">{"".join(rows)}</div>'


# ─── CLAUDE ANALYSIS ──────────────────────────────────────────────────────────

def run_health_analysis(dealer_name: str, data_context: str, period_label: str) -> str:
    """Run Claude CLI health snapshot. Returns raw response text."""
    env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(SYSTEM_PROMPT)
        sys_path = f.name
    try:
        result = subprocess.run(
            ["claude", "-p",
             f"Generate a dealer health snapshot for this dealer. Report period: {period_label}\n\n{data_context}",
             "--system-prompt-file", sys_path,
             "--model", "claude-sonnet-4-6",
             "--output-format", "text",
             "--mcp-config", '{"mcpServers":{}}',
             "--strict-mcp-config"],
            capture_output=True, text=True, timeout=180, env=env,
        )
        if result.returncode != 0:
            return f"ERROR: {result.stderr[:500]}"
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        return "ERROR: Claude timed out after 3 minutes."
    finally:
        if os.path.exists(sys_path):
            os.unlink(sys_path)


# ─── GOOGLE DOC EXPORT ────────────────────────────────────────────────────────

_GDOCS_TOKEN_PATH = os.path.expanduser("~/.claude/tokens/gdocs_credentials.json")
_GDOCS_OAUTH_KEYS = os.path.expanduser("~/gcp-oauth.keys.json")
_GDOCS_SCOPES = ["https://www.googleapis.com/auth/documents",
                 "https://www.googleapis.com/auth/drive.file"]
_SCORE_COLORS_HEX = {"green": "#1a5c33", "yellow": "#7a4210", "red": "#8b1a14"}


def _gdrive_service():
    with open(_GDOCS_TOKEN_PATH) as f: tok = json.load(f)
    with open(_GDOCS_OAUTH_KEYS) as f: keys = json.load(f)["installed"]
    creds = Credentials(
        token=tok.get("access_token"), refresh_token=tok.get("refresh_token"),
        token_uri=keys["token_uri"], client_id=keys["client_id"],
        client_secret=keys["client_secret"], scopes=_GDOCS_SCOPES,
    )
    if not creds.valid:
        creds.refresh(Request())
        tok["access_token"] = creds.token
        with open(_GDOCS_TOKEN_PATH, "w") as f: json.dump(tok, f)
    return _gapi_build("drive", "v3", credentials=creds)


def build_health_html(dealer_name: str, scores: list, narrative: str,
                      wid_data: Optional[dict], vd_data: Optional[dict], today: str) -> str:
    parts = ["""<!DOCTYPE html><html><head><meta charset="UTF-8">
<style>
  body{font-family:Arial,sans-serif;font-size:11pt;color:#111827;margin:40px 60px}
  .eyebrow{font-size:9pt;letter-spacing:.12em;text-transform:uppercase;color:#5B2D8E;font-weight:bold;margin-bottom:4px}
  h1{font-size:20pt;font-weight:bold;color:#111827;margin:4px 0 2px 0}
  .subtitle{font-size:9pt;color:#6b7280;margin-bottom:6px}
  .accent{height:4px;background:linear-gradient(90deg,#5B2D8E,#a78bfa);margin:8px 0 18px 0;border-radius:2px}
  h2{font-size:13pt;font-weight:bold;color:#111827;margin:20px 0 6px 0;border-bottom:1px solid #e5e7eb;padding-bottom:3px}
  h3{font-size:11pt;font-weight:bold;color:#111827;margin:14px 0 4px 0}
  p,li{font-size:11pt;line-height:1.55;margin:4px 0}
  ul{margin:4px 0 8px 20px;padding:0}
  .score-row{display:flex;align-items:center;margin-bottom:8px;gap:10px}
  .score-label{width:180px;font-size:10pt;font-weight:600;flex-shrink:0}
  .score-bar-wrap{flex:1;background:#f0ebf8;border-radius:4px;height:10px;overflow:hidden}
  .score-bar{height:100%;border-radius:4px}
  .score-pct{width:55px;font-size:10pt;font-weight:bold;text-align:right;flex-shrink:0}
  .score-meta{width:200px;font-size:9pt;color:#6b7280;flex-shrink:0}
  hr{border:none;border-top:1px solid #e5e7eb;margin:14px 0}
  .footer{font-size:8pt;color:#9ca3af;margin-top:24px;border-top:1px solid #e5e7eb;padding-top:8px}
</style></head><body>"""]
    parts.append(f'<div class="eyebrow">Cars.com · Growth Insights</div>')
    parts.append(f'<h1>{dealer_name} — Dealer Health Snapshot</h1>')
    parts.append(f'<div class="subtitle">Generated {today} &nbsp;·&nbsp; Powered by the Dealer Growth Triangle</div>')
    parts.append('<div class="accent"></div>')
    if scores:
        _bg = {"green":"linear-gradient(90deg,#22c55e,#16a34a)","yellow":"linear-gradient(90deg,#f59e0b,#d97706)","red":"linear-gradient(90deg,#f87171,#dc2626)"}
        parts.append('<h2>Health Scores</h2>')
        for s in scores:
            pct = max(0, min(100, s["score"]))
            parts.append(f'<div class="score-row"><div class="score-label">{s["name"]}</div>'
                         f'<div class="score-bar-wrap"><div class="score-bar" style="width:{pct}%;background:{_bg.get(s["color"],_bg["yellow"])}"></div></div>'
                         f'<div class="score-pct" style="color:{_SCORE_COLORS_HEX.get(s["color"],"#7a4210")}">{pct}% {s["trend"]}</div>'
                         f'<div class="score-meta">{s["driver"]}</div></div>')
    in_ul = False
    for line in narrative.splitlines():
        s = line.strip()
        if s.startswith("### "):
            if in_ul: parts.append("</ul>"); in_ul = False
            parts.append(f"<h3>{s[4:]}</h3>")
        elif s.startswith("## "):
            if in_ul: parts.append("</ul>"); in_ul = False
            parts.append(f"<h2>{s[3:]}</h2>")
        elif s.startswith(("- ","* ")):
            if not in_ul: parts.append("<ul>"); in_ul = True
            parts.append(f"<li>{s[2:].replace('**','<b>',1).replace('**','</b>',1)}</li>")
        elif s == "---":
            if in_ul: parts.append("</ul>"); in_ul = False
            parts.append("<hr>")
        elif s:
            if in_ul: parts.append("</ul>"); in_ul = False
            parts.append(f"<p>{s.replace('**','<b>',1).replace('**','</b>',1)}</p>")
        else:
            if in_ul: parts.append("</ul>"); in_ul = False
    if in_ul: parts.append("</ul>")
    parts.append(f'<div class="footer">Cars.com Dealer Health Dashboard &nbsp;·&nbsp; {today}</div>')
    parts.append("</body></html>")
    return "\n".join(parts)


def create_health_doc(dealer_name: str, scores: list, narrative: str,
                      wid_data: Optional[dict] = None, vd_data: Optional[dict] = None,
                      sf_data=None, perf_data: Optional[dict] = None) -> str:
    today = datetime.date.today().strftime("%B %d, %Y")
    html = build_health_html(dealer_name, scores, narrative, wid_data, vd_data, today)
    drive = _gdrive_service()
    f = drive.files().create(
        body={"name": f"Dealer Health Snapshot — {dealer_name} — {today}",
              "mimeType": "application/vnd.google-apps.document"},
        media_body=MediaIoBaseUpload(io.BytesIO(html.encode()), mimetype="text/html", resumable=False),
        fields="id",
    ).execute()
    return f"https://docs.google.com/document/d/{f['id']}/edit"
