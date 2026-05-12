import os
import tempfile
import threading
import streamlit as st
import pandas as pd
import subprocess
import json
import admin_cars
from typing import Optional, List

# ─── BRANDING ─────────────────────────────────────────────────────────────────

CC_CSS = """
<style>
  @import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,500;0,9..40,700&display=swap');
  html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
  .block-container { padding-top: 2rem; }
  div[data-testid="stStatusWidget"] { visibility: hidden; }
  .cc-brand { font-size: 0.72rem; letter-spacing: 0.18em; text-transform: uppercase;
               color: #5B2D8E; font-weight: 700; }
  .cc-title { font-size: 2.0rem; font-weight: 700; color: #111827; margin: 0; line-height: 1.15; }
  .cc-sub   { color: #6b7280; font-size: 0.95rem; margin: 0.15rem 0 0.25rem 0; }
  .cc-accent { height: 4px; background: linear-gradient(90deg,#5B2D8E 0%,#a78bfa 100%);
               margin: 0 0 1rem 0; border-radius: 2px; }
  section[data-testid="stSidebar"] .stCheckbox label { font-size: 0.88rem; }
  section[data-testid="stSidebar"] h2 { color: #5B2D8E; border-left: 3px solid #5B2D8E;
                                         padding-left: 8px; }
</style>
<div class="cc-brand">Cars.com · Growth Insights</div>
<h1 class="cc-title">Dealer Health Dashboard</h1>
<p class="cc-sub">Health snapshots powered by the Dealer Growth Triangle</p>
<div class="cc-accent"></div>
"""

# ─── CONFIG ──────────────────────────────────────────────────────────────────

SF_CLI = "/Users/jcrawley/.npm-global/bin/sf"

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

Then continue with the full snapshot:

### 📊 Health Snapshot — [Dealer Name]

---

### 🔑 Key Findings

Format each as a bold headline + one-line supporting data point. Max 4 findings.

- **🟢 [Strong positive pattern]** — supporting number + source
- **🟡 [Watch item]** — supporting number + source
- **🔴 [Concern]** — supporting number + source

---

### 🚀 Growth Opportunities

Up to 3 opportunities, ranked by impact. Keep each to 3 lines — no blockquote callouts, no headers within the bullet. Use this exact format:

**1. [Headline — one bold phrase]**
- Action: specific move (name vehicles, stock numbers, price points)
- Expected lift: quantified outcome ("+X% VDPs" or "$Y/mo additional revenue")
- Measure: the metric that should move

Leave one blank line between opportunities.

---

### ⚠️ Risks / Watch Items

Short bulleted list. For each, bold the metric and state the direction in plain language.

- **Metric name** — plain-English risk statement + the data point

---

### 📋 Data Gaps

Only mention ONE thing here: **DMS connectivity status** (connected or not connected). If DMS is not connected, note it as the key gap that would unlock GROI/Turn Rate and influenced-sales data. If DMS IS connected, note nothing in this section or skip it entirely.

## Rules

- **Be specific** — name vehicles, price ranges, market segments, product names.
- **Frame findings in revenue impact** — not just metric changes. "$X lost/gained per month" beats "down 7%".
- **Use dealer-friendly language** — "price to earn a Great Deal badge" not "optimize pricing distribution".
- **Marketplace spend matters** — call out current products (Franchise Premium Listings, Cars Social, AccuTrade Connected, etc.) and tie opportunities to product tier. A dealer on Basic has different levers than one on Premium.
- **When Listings Optimizer data is present, USE IT.** The Badge impact table shows the real VDPs/VIN and Connections/VIN delta between badge tiers — this is the concrete engagement lift from re-pricing. Cite specific vehicles from the "Within $500 of Good Badge" / "Within $500 of Great Badge" lists as your top Growth Opportunities (they're the highest-ROI pricing moves).
- **KPI benchmarks:** Turn <30 days used, Aging <15% over 60 days, GROI 120+ (only when DMS is connected), Reputation 4.5+ rating and 50+ reviews/month. SRPs are not a current focus — do not build findings around them.
- **Fair/Above Badge %** is the primary merchandising proxy (not SRP volume).
- **Inventory metrics shown are monthly averages** (not point-in-time), so frame trend language accordingly ("average inventory rose by..." not "current inventory is...").
- **Stock-type (Used/New) split** is in the Listings Optimizer Performance Snapshot — if one stock type is aging much faster than the other, that's a specific finding worth calling out.
- **Data gap guidance — the ONLY allowable gap is DMS connectivity. Do NOT list these others as gaps (they're architectural limitations, not addressable data gaps):**
    - Platform-specific review ratings (Google/Facebook/DealerRater) — admin.cars.com only exposes Cars.com ratings, by design
    - Full badge distribution for New inventory — Cars.com does not badge New inventory, so Not-Badged counts for New vehicles are expected; do not treat as a gap
    - Competitor pricing at the model/trim level — the Market Comparison data IS this, and the "Within $500 of Good/Great Badge" lists give per-vehicle pricing opportunities
    - Monthly inventory trend — the MoM % delta captures month-over-month movement; don't ask for a 9-month chart
    - Competitive-set performance — not pulled today; do not flag as a gap
- If data is limited, score what you can and clearly note what's estimated vs. data-backed.
- Be concise and direct — this is for busy account teams.
- All MoM deltas are percentage changes vs. prior month."""


# ─── DATA SOURCES ────────────────────────────────────────────────────────────

SF_QUERY_BY_CCID = SF_QUERY.replace(
    "WHERE Name LIKE '%{dealer}%'",
    "WHERE CCID__c = '{ccid}'",
).replace("LIMIT 20", "LIMIT 5")


def _run_sf_query(query: str) -> Optional[List[dict]]:
    try:
        result = subprocess.run(
            [SF_CLI, "data", "query", "--query", query, "--json"],
            capture_output=True, text=True, timeout=30,
        )
        data = json.loads(result.stdout[result.stdout.index("{"):])
        if data.get("status") == 0 and data["result"]["totalSize"] > 0:
            records = data["result"]["records"]
            for r in records:
                r.pop("attributes", None)
            return records
        return []
    except Exception as e:
        st.warning(f"Salesforce: {e}")
        return None


def fetch_salesforce(dealer_name: str) -> Optional[List[dict]]:
    safe_name = dealer_name.replace("'", "\\'")
    return _run_sf_query(SF_QUERY.format(dealer=safe_name))


def fetch_salesforce_by_ccid(ccid: str) -> Optional[List[dict]]:
    safe_ccid = ccid.replace("'", "\\'")
    return _run_sf_query(SF_QUERY_BY_CCID.format(ccid=safe_ccid))


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


def fetch_subscriptions(account_id: str) -> Optional[List[dict]]:
    """Fetch active marketplace subscriptions (Live Products) for an SF Account."""
    safe_id = account_id.replace("'", "\\'")
    records = _run_sf_query(SF_SUBSCRIPTIONS_QUERY.format(account_id=safe_id))
    if not records:
        return records
    # Flatten the SBQQ__Product__r.Name reference
    for r in records:
        prod_ref = r.pop("SBQQ__Product__r", None) or {}
        if isinstance(prod_ref, dict):
            r["Product_Name"] = prod_ref.get("Name")
    return records


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
) -> str:
    parts = [f"# Data for: {dealer_name}\n"]

    # Salesforce account
    if sf_data is not None:
        parts.append("## Salesforce Account Data")
        if sf_data:
            for i, rec in enumerate(sf_data, 1):
                parts.append(f"\n### Account {i}")
                for k, v in rec.items():
                    if v is not None and k != "Id":  # Id is for internal lookup only
                        parts.append(f"- **{k}**: {v}")
        else:
            parts.append("No matching accounts found.")

    # Marketplace subscriptions (Live Products from Customer360 tab)
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
            if qty:
                line += f" × {qty:g}"
            if price is not None:
                line += f" — ${price:,.2f}"
                try:
                    total_mrr += float(price)
                except (TypeError, ValueError):
                    pass
            if lob:
                line += f" ({lob})"
            if start:
                line += f" — active since {start}"
            parts.append(line)
        if total_mrr > 0:
            parts.append(f"- **Total active subscription value: ${total_mrr:,.2f}**")

    # Performance Trends (monthly averages + MoM % change)
    if perf_data:
        parts.append("\n## Performance Trends (admin.cars.com — monthly averages vs. prior month)")
        labels = {
            "avg_inventory":      "Monthly Avg Inventory",
            "avg_days_live":      "Avg Days Live (days on lot)",
            "under_merch":        "Under-Merchandised vehicles",
            "vdps":               "VDPs (monthly total)",
            "connections":        "Connections / Total Leads (monthly)",
            "fair_above_badges":  "Fair/Above Badge vehicles (monthly)",
            "reviews":            "New Reviews (this month)",
        }
        for key, label in labels.items():
            cp = perf_data.get(f"{key}_cp")
            delta = perf_data.get(f"{key}_delta_pct")
            if cp is not None:
                delta_str = f" ({delta:+.1f}% MoM)" if delta is not None else ""
                # Avg Days Live is typically small and fractional — no comma formatting needed
                value_str = f"{cp:.1f}" if key == "avg_days_live" else f"{cp:,.0f}"
                parts.append(f"- {label}: {value_str}{delta_str}")

    # Reputation
    if rep_data:
        parts.append("\n## Reputation Health")
        rating = rep_data.get("rating")
        count = rep_data.get("review_count")
        dma = rep_data.get("dma_avg_rating")
        nat = rep_data.get("national_avg_rating")
        pricing_tr = rep_data.get("pricing_transparency")
        lead_resp = rep_data.get("lead_response_rate_pct")
        lead_hand = rep_data.get("lead_handling_rating")
        if rating is not None:
            parts.append(f"- Overall Rating: {rating}★ ({count or 'N/A'} total reviews)")
        if dma is not None and nat is not None:
            parts.append(f"- Market context: DMA avg {dma}★ | National OEM avg {nat}★")
        if pricing_tr is not None:
            parts.append(f"- Pricing Transparency rating: {pricing_tr}★")
        if lead_resp is not None:
            parts.append(f"- Lead response rate: {lead_resp}%")
        if lead_hand is not None:
            parts.append(f"- Lead handling rating: {lead_hand}★")

    # Market Comparison (Demand Signals — Price Comparison)
    if mkt_data:
        parts.append("\n## Market Comparison (Demand Signals — Price Comparison)")
        parts.append(
            f"- Above Market (>105%): {mkt_data.get('above_pct', 0)}% ({mkt_data.get('above_count', 0)} vehicles)"
        )
        parts.append(
            f"- At Market: {mkt_data.get('at_pct', 0)}% ({mkt_data.get('at_count', 0)} vehicles)"
        )
        parts.append(
            f"- Under Market (<95%): {mkt_data.get('under_pct', 0)}% ({mkt_data.get('under_count', 0)} vehicles)"
        )

    # Listings Optimizer — badge impact, specific pricing opportunities, Used/New split
    if lo_data:
        parts.append("\n## Listings Optimizer (admin.cars.com)")
        if lo_data.get("merch_complete_pct") is not None:
            parts.append(
                f"- Merchandising: {lo_data['merch_complete_pct']:.1f}% complete "
                f"({int(lo_data.get('merch_needs_attention_count') or 0)} vehicles need attention)"
            )
        # Badge impact table — shows the concrete value of badge tier changes
        badges = lo_data.get("badge_details") or []
        if badges:
            parts.append("\n### Badge impact (engagement per badge tier)")
            parts.append("| Badge | Vehicles | % of inv | VDPs / VIN | Connections / VIN |")
            parts.append("|---|---|---|---|---|")
            for b in badges:
                parts.append(
                    f"| {b['badge']} | {int(b.get('vehicles') or 0)} | "
                    f"{b.get('pct_of_inventory', 0):.1f}% | "
                    f"{b.get('vdps_per_vin', 0):.1f} | "
                    f"{b.get('connections_per_vin', 0):.2f} |"
                )

        # Pricing opportunities with specific stock numbers
        good_ops = lo_data.get("within_500_good") or []
        great_ops = lo_data.get("within_500_great") or []
        if good_ops:
            parts.append("\n### Vehicles within $500 of earning the Good Badge")
            for v in good_ops:
                parts.append(
                    f"- **{v['ymmt']}** (stock {v['stock_num']}) — "
                    f"priced ${v['price']:,.0f}, {int(v.get('days_live') or 0)} days live, "
                    f"reduce by **${v['reduce_by']:,.0f}**"
                )
        if great_ops:
            parts.append("\n### Vehicles within $500 of earning the Great Badge")
            for v in great_ops:
                parts.append(
                    f"- **{v['ymmt']}** (stock {v['stock_num']}) — "
                    f"priced ${v['price']:,.0f}, {int(v.get('days_live') or 0)} days live, "
                    f"reduce by **${v['reduce_by']:,.0f}**"
                )

        # Used / New inventory breakdown
        stock_split = lo_data.get("stock_type_breakdown") or {}
        if stock_split:
            parts.append("\n### Used vs. New inventory performance (last 7 days)")
            for stype, metrics in stock_split.items():
                if not metrics:
                    continue
                parts.append(f"\n**{stype}:**")
                for metric_name, val in metrics.items():
                    if val is None:
                        continue
                    if "Price" in metric_name or "price" in metric_name:
                        parts.append(f"- {metric_name}: ${val:,.2f}")
                    elif "Photos" in metric_name or "Days" in metric_name:
                        parts.append(f"- {metric_name}: {val:.1f}")
                    else:
                        parts.append(f"- {metric_name}: {val:,.0f}")

    # ROI One-Sheeter — lead source breakdown
    if roi_data and roi_data.get("lead_sources"):
        ls = roi_data["lead_sources"]
        parts.append(f"\n## Lead Source Breakdown (ROI One-Sheeter — {ls.get('month', 'current month')})")
        mapping = [
            ("Phone leads", "phone"),
            ("Email leads", "email"),
            ("Chat (leads + events)", "chat"),
            ("Website transfers (to DI site)", "website_transfers"),
            ("Walk-ins", "walk_ins"),
            ("Instant Offer (trade-in requests)", "instant_offer"),
            ("VDP Print", "vdp_print"),
            ("Map views / directions", "other"),
        ]
        total = ls.get("total") or 0
        for label, key in mapping:
            val = ls.get(key) or 0
            if val:
                share = (val / total * 100) if total else 0
                parts.append(f"- {label}: **{val}** ({share:.0f}% of connections)")
        parts.append(f"- **Total connections this month: {total}**")
        if roi_data.get("leads_per_vin") is not None:
            parts.append(f"- Leads per VIN: {roi_data['leads_per_vin']:.2f}")

    # Sales Influence Summary (DMS-backed GROI / Turn — only when DMS is connected)
    if si_data:
        parts.append("\n## Sales Influence Summary (admin.cars.com — DMS-backed)")
        if si_data.get("dms_connected"):
            if si_data.get("leads") is not None:
                parts.append(f"- Leads (attributed): {si_data['leads']:,.0f}")
            if si_data.get("connections") is not None:
                parts.append(f"- Connections (attributed): {si_data['connections']:,.0f}")
            if si_data.get("influenced_sales") is not None:
                parts.append(f"- Cars.com-influenced sales: {si_data['influenced_sales']:,.0f}")
            if si_data.get("influenced_sales_pct") is not None:
                parts.append(f"- % of sales influenced by Cars.com: {si_data['influenced_sales_pct']:.1f}%")
            if si_data.get("vehicle_gross_sales") is not None:
                parts.append(f"- Total vehicle gross sales: {si_data['vehicle_gross_sales']:,.0f}")
        else:
            parts.append("- No DMS feed connected for this dealer — GROI/Turn and influenced-sales data unavailable.")

    if sf_data is None and not any([perf_data, rep_data, mkt_data, lo_data]):
        parts.append("\n*No data sources returned results. Analysis will be limited.*")

    return "\n".join(parts)


# ─── SCORE PARSING ───────────────────────────────────────────────────────────

import re as _re

def _parse_scores(text: str) -> tuple:
    """Extract ---SCORES--- block from Claude output.
    Returns (scores_list, narrative_text). scores_list is [] if block is absent.
    """
    m = _re.search(r"---SCORES---\n(.*?)\n---END SCORES---\n?", text, _re.DOTALL)
    if not m:
        return [], text
    scores = []
    for line in m.group(1).strip().splitlines():
        parts = [p.strip() for p in line.split("|")]
        if len(parts) >= 5:
            try:
                scores.append({
                    "name":   parts[0],
                    "score":  int(parts[1]),
                    "color":  parts[2],
                    "trend":  parts[3],
                    "driver": parts[4],
                })
            except (ValueError, IndexError):
                pass
    narrative = (text[: m.start()] + text[m.end() :]).strip()
    return scores, narrative


_SCORE_GRADIENTS = {
    "green":  ("linear-gradient(90deg,#22c55e,#16a34a)", "#166534"),
    "yellow": ("linear-gradient(90deg,#f59e0b,#d97706)", "#92400e"),
    "red":    ("linear-gradient(90deg,#f87171,#dc2626)", "#991b1b"),
}

def _render_score_bars(scores: list) -> str:
    """Return an HTML string with one % fill bar per score dict."""
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


# ─── UI ──────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Cars.com | Dealer Health Dashboard",
    page_icon="🚗",
    layout="wide",
)

st.markdown(CC_CSS, unsafe_allow_html=True)

@st.cache_data(ttl=300)
def _session_ok() -> bool:
    return admin_cars.check_session()


with st.sidebar:
    st.header("Configuration")
    dealer_name = st.text_input("Dealer Name", placeholder="e.g. Hendrick, Nalley Lexus Galleria")
    ccid_override = st.text_input(
        "CCID (optional)",
        placeholder="Use when the name matches multiple accounts",
        help="If provided, skips the name-based Salesforce lookup and uses this CCID directly.",
    )

    st.subheader("Data Sources")
    use_sf = st.checkbox("Salesforce", value=True)
    use_admin = st.checkbox("admin.cars.com — Performance Trends", value=True)

    # Session status — computed once, reused for indicator and button disabled state
    session_ok = _session_ok() if use_admin else True
    if use_admin:
        if session_ok:
            st.success("● admin.cars.com connected")
            if st.button("Refresh session status", use_container_width=True):
                st.cache_data.clear()
                st.rerun()
        else:
            st.error("✗ Not connected to Chrome / not signed in")
            st.caption(
                "Launch Chrome with remote debugging and sign in to admin.cars.com. "
                "Run this in Terminal (close existing Chrome first):"
            )
            st.code(
                'mkdir -p ~/.chrome-dealer-health && '
                '"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" '
                '--remote-debugging-port=9222 '
                '--user-data-dir="$HOME/.chrome-dealer-health"',
                language="bash",
            )
            st.caption(
                "A dedicated profile is required — company policy blocks "
                "remote debugging on the default Chrome profile. Sign in to "
                "admin.cars.com in the new Chrome window once, then click Re-check."
            )
            if st.button("Re-check", use_container_width=True):
                st.cache_data.clear()
                st.rerun()

    run = st.button(
        "Run Analysis",
        type="primary",
        disabled=(not dealer_name.strip() and not ccid_override.strip()) or not session_ok,
    )

    st.divider()
    st.caption(
        "Pulls account data from Salesforce and performance data from "
        "admin.cars.com Performance Trends, Reputation Health, and "
        "Market Comparison, then generates a health snapshot using Claude."
    )

# Main area
if run and (dealer_name.strip() or ccid_override.strip()):
    dealer_name = dealer_name.strip()
    ccid_override = ccid_override.strip()

    sf_data = None
    sub_data = None
    perf_data = rep_data = mkt_data = lo_data = si_data = roi_data = None
    uuid = None

    # Determine which CCID to use: override wins, otherwise derived from SF name lookup
    effective_ccid = ccid_override or None

    # Single unified progress indicator — all status chatter goes into this one container,
    # which we clear once the snapshot is ready so the user is not left with tiles they
    # already scanned past.
    progress = st.empty()

    def _progress(msg):
        progress.markdown(
            f"<div style='color:#5b2d8e;font-size:0.9rem;'>⏳ {msg}</div>",
            unsafe_allow_html=True,
        )

    source_summary = []  # populated while fetching, shown in a small expander below the snapshot

    if use_sf:
        _progress("Querying Salesforce…")
        if effective_ccid:
            sf_data = fetch_salesforce_by_ccid(effective_ccid)
        else:
            sf_data = fetch_salesforce(dealer_name)
        if sf_data:
            ccids = [r.get("CCID__c") for r in sf_data if r.get("CCID__c")]
            if not effective_ccid and ccids:
                effective_ccid = ccids[0]
            if sf_data[0].get("Name"):
                dealer_name = sf_data[0]["Name"]
            source_summary.append(f"Salesforce: {len(sf_data)} account · CCID {effective_ccid}")
        elif sf_data is not None:
            source_summary.append("Salesforce: no matches")

        if sf_data and sf_data[0].get("Id"):
            _progress("Pulling active marketplace subscriptions…")
            sub_data = fetch_subscriptions(sf_data[0]["Id"])
            if sub_data:
                total = sum(float(s.get("SBQQ__NetPrice__c") or 0) for s in sub_data)
                source_summary.append(f"Subscriptions: {len(sub_data)} active · ${total:,.0f}/mo")
            else:
                source_summary.append("Subscriptions: none active")

    if use_admin and effective_ccid:
        _progress("Opening admin.cars.com (single tab) and resolving dealer UUID…")
        with admin_cars.session() as admin:
            uuid = admin.resolve_uuid(effective_ccid)
            if not uuid:
                source_summary.append("admin.cars.com: dealer UUID not found")
            else:
                _progress("Pulling Performance Trends…")
                perf_data = admin.fetch_performance_trends(uuid)
                if perf_data:
                    metric_count = sum(1 for v in perf_data.values() if v is not None)
                    source_summary.append(f"Performance Trends: {metric_count} metrics")

                _progress("Pulling Reputation Health…")
                rep_data = admin.fetch_reputation(uuid)
                if rep_data and rep_data.get("rating"):
                    source_summary.append(f"Reputation: {rep_data['rating']}★")

                _progress("Pulling Market Comparison (Demand Signals)…")
                mkt_data = admin.fetch_market_comparison(uuid)
                if mkt_data:
                    source_summary.append(f"Market Comparison: {mkt_data['at_pct']}% at market")

                _progress("Pulling Listings Optimizer (badge impact + pricing ops)…")
                lo_data = admin.fetch_listings_optimizer(uuid)
                if lo_data:
                    n_ops = len(lo_data.get("within_500_good", [])) + len(lo_data.get("within_500_great", []))
                    source_summary.append(f"Listings Optimizer: {n_ops} pricing opps")

                _progress("Pulling ROI One-Sheeter (lead source breakdown)…")
                roi_data = admin.fetch_roi_one_sheeter(uuid)
                if roi_data and roi_data.get("lead_sources"):
                    source_summary.append(
                        f"Lead sources: {roi_data['lead_sources'].get('total', 0)} connections"
                    )

                _progress("Checking Sales Influence / DMS connectivity…")
                si_data = admin.fetch_sales_influence(uuid)
                if si_data and si_data.get("dms_connected"):
                    source_summary.append("DMS: connected (influenced-sales data available)")
                else:
                    source_summary.append("DMS: not connected")

    _progress("Generating health snapshot…")

    data_context = build_data_context(
        dealer_name=dealer_name,
        sf_data=sf_data,
        perf_data=perf_data,
        rep_data=rep_data,
        mkt_data=mkt_data,
        sub_data=sub_data,
        lo_data=lo_data,
        si_data=si_data,
        roi_data=roi_data,
    )

    # Note: Claude's output renders its own "### 📊 Health Snapshot — [Dealer]" heading
    # per the system prompt, so no st.subheader() here to avoid duplication.
    # Clear the progress indicator and show the snapshot
    progress.empty()

    # Fail-loud if the admin.cars.com dashboard layout has drifted
    missing = admin_cars.get_last_missing_worksheets()
    if missing:
        lines = [f"**{slug}**: missing `{', '.join(ws)}`" for slug, ws in missing.items()]
        st.warning(
            "⚠️ **admin.cars.com dashboard layout has changed** — some worksheets we rely on "
            "were not found. Numbers for the affected reports may be stale or incomplete.\n\n"
            + "\n\n".join(lines)
        )

    _env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as sys_f:
        sys_f.write(SYSTEM_PROMPT)
        sys_path = sys_f.name
    try:
        proc = subprocess.Popen(
            [
                "claude", "-p",
                f"Generate a dealer health snapshot for this dealer.\n\n{data_context}",
                "--system-prompt-file", sys_path,
                "--model", "claude-sonnet-4-6",
                "--output-format", "text",
                "--mcp-config", '{"mcpServers":{}}',
                "--strict-mcp-config",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=_env,
        )
    finally:
        os.unlink(sys_path)

    # Drain stderr in background so its buffer never blocks stdout
    stderr_lines: list = []
    threading.Thread(target=lambda: stderr_lines.extend(proc.stderr.readlines()), daemon=True).start()

    status_box = st.empty()
    status_box.info("Connecting to Claude CLI… (startup takes ~20s, then text will stream in)")
    placeholder = st.empty()
    response_text = ""
    for chunk in iter(lambda: proc.stdout.read(64), ""):
        if not response_text:
            status_box.empty()
        response_text += chunk
        placeholder.markdown(response_text)
    proc.wait()
    response_text = response_text.strip()

    if proc.returncode != 0 or not response_text:
        status_box.empty()
        st.error(f"Claude CLI error (exit {proc.returncode}):\n\n{''.join(stderr_lines)[:1000]}")
    else:
        scores, narrative = _parse_scores(response_text)
        placeholder.empty()
        if scores:
            st.markdown(_render_score_bars(scores), unsafe_allow_html=True)
        st.markdown(narrative)

    # Compact data-source summary — collapsed by default so the snapshot is the hero
    if source_summary:
        with st.expander(f"Data sources pulled · {len(source_summary)} checks", expanded=False):
            for line in source_summary:
                st.markdown(f"- {line}")

    st.session_state["last_result"] = {
        "dealer": dealer_name,
        "analysis": response_text,
        "sf_data": sf_data,
        "sub_data": sub_data,
        "perf_data": perf_data,
        "rep_data": rep_data,
        "mkt_data": mkt_data,
        "lo_data": lo_data,
        "si_data": si_data,
        "roi_data": roi_data,
        "source_summary": source_summary,
    }

# Show raw data from last run
if "last_result" in st.session_state:
    result = st.session_state["last_result"]

    if not (run and (dealer_name.strip() or ccid_override.strip())):
        # Claude's output already contains the "📊 Health Snapshot — …" heading
        st.markdown(result["analysis"])

    st.divider()

    with st.expander("Raw Salesforce Data", expanded=False):
        if result.get("sf_data"):
            st.dataframe(pd.DataFrame(result["sf_data"]), use_container_width=True)
        else:
            st.info("No Salesforce data")

    with st.expander("Active Marketplace Subscriptions (Live Products)", expanded=False):
        if result.get("sub_data"):
            st.dataframe(pd.DataFrame(result["sub_data"]), use_container_width=True)
        else:
            st.info("No active subscriptions")

    with st.expander("Raw admin.cars.com Data", expanded=False):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.caption("Performance Trends")
            st.json(result.get("perf_data") or {})
        with col2:
            st.caption("Reputation")
            st.json(result.get("rep_data") or {})
        with col3:
            st.caption("Market Comparison")
            st.json(result.get("mkt_data") or {})
        col4, col5, col6 = st.columns(3)
        with col4:
            st.caption("Listings Optimizer")
            st.json(result.get("lo_data") or {})
        with col5:
            st.caption("Sales Influence")
            st.json(result.get("si_data") or {})
        with col6:
            st.caption("ROI One-Sheeter")
            st.json(result.get("roi_data") or {})

elif not run:
    st.info("Enter a dealer name in the sidebar and click **Run Analysis** to generate a health snapshot.")
