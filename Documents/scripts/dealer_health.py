import streamlit as st
import anthropic
import pandas as pd
import subprocess
import json
import admin_cars
from typing import Optional, List

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

Produce a **Dealer Health Snapshot** in this exact format. Use emojis for trend indicators (🟢 healthy, 🟡 watch, 🔴 action needed) and keep each section tight.

### 📊 Health Snapshot — [Dealer Name]

| Dimension | Score | Trend | Key Driver |
|---|---|---|---|
| Inventory Health | X/100 | 🟢/🟡/🔴 ↑↓→ | one short phrase |
| Pricing Position | X/100 | 🟢/🟡/🔴 ↑↓→ | one short phrase |
| Engagement (VDPs) | X/100 | 🟢/🟡/🔴 ↑↓→ | one short phrase |
| Reputation | X/100 | 🟢/🟡/🔴 ↑↓→ | one short phrase |
| Lead Performance | X/100 | 🟢/🟡/🔴 ↑↓→ | one short phrase |
| Marketplace Investment | X/100 | 🟢/🟡/🔴 ↑↓→ | one short phrase |

---

### 🔑 Key Findings

Format each as a bold headline + one-line supporting data point. Max 4 findings.

- **🟢 [Strong positive pattern]** — supporting number + source
- **🟡 [Watch item]** — supporting number + source
- **🔴 [Concern]** — supporting number + source

---

### 🚀 Growth Opportunities

Ranked by impact. Format each as a callout card:

**1. [Opportunity headline in bold]**
> **Action:** what to do (specific, vehicle/segment/price-range level when possible)
> **Expected lift:** quantified outcome (e.g. "+X% VDPs" or "$Y additional revenue")
> **How we'd measure:** the metric that should move

Repeat for up to 3 opportunities.

---

### ⚠️ Risks / Watch Items

Short bulleted list. For each, bold the metric and state the direction in plain language.

- **Metric name** — plain-English risk statement + the data point

---

### 📋 Data Gaps

Bulleted list of what's missing that would strengthen the analysis. Keep it short.

## Rules

- **Be specific** — name vehicles, price ranges, market segments, product names.
- **Frame findings in revenue impact** — not just metric changes. "$X lost/gained per month" beats "down 7%".
- **Use dealer-friendly language** — "price to earn a Great Deal badge" not "optimize pricing distribution".
- **Marketplace spend matters** — call out current products (Franchise Premium Listings, Cars Social, AccuTrade Connected, etc.) and tie opportunities to product tier. A dealer on Basic has different levers than one on Premium.
- **KPI benchmarks:** Turn <30 days used, Aging <15% over 60 days, GROI 120+, Reputation 4.5+ rating and 50+ reviews/month. SRPs are not a current focus — do not build findings around them.
- **Fair/Above Badge %** is the primary merchandising proxy (not SRP volume).
- **Inventory metrics shown are monthly averages** (not point-in-time), so frame trend language accordingly ("average inventory rose by..." not "current inventory is...").
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

    if sf_data is None and not any([perf_data, rep_data, mkt_data]):
        parts.append("\n*No data sources returned results. Analysis will be limited.*")

    return "\n".join(parts)


# ─── UI ──────────────────────────────────────────────────────────────────────

st.set_page_config(page_title="Dealer Health Dashboard", layout="wide")

st.markdown(
    "<h1 style='margin-bottom:0'>Dealer Health Dashboard</h1>"
    "<p style='color:#888; margin-top:0'>Self-serve health snapshots powered by the Dealer Growth Triangle</p>",
    unsafe_allow_html=True,
)

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
    perf_data = rep_data = mkt_data = None
    uuid = None

    # Determine which CCID to use: override wins, otherwise derived from SF name lookup
    effective_ccid = ccid_override or None

    status_cols = st.columns(2)

    with status_cols[0]:
        if use_sf:
            with st.spinner("Querying Salesforce..."):
                if effective_ccid:
                    sf_data = fetch_salesforce_by_ccid(effective_ccid)
                else:
                    sf_data = fetch_salesforce(dealer_name)
                if sf_data:
                    st.success(f"Salesforce: {len(sf_data)} account(s)")
                    ccids = [r.get("CCID__c") for r in sf_data if r.get("CCID__c")]
                    if ccids:
                        st.caption(f"CCIDs: {', '.join(ccids)}")
                    # If no override, use the first CCID from the name lookup
                    if not effective_ccid and ccids:
                        effective_ccid = ccids[0]
                    # Derive display name from the matched SF record
                    if sf_data[0].get("Name"):
                        dealer_name = sf_data[0]["Name"]
                elif sf_data is not None:
                    st.info("Salesforce: no matches")

            # Pull Live Products / marketplace subscriptions for the matched account
            if sf_data and sf_data[0].get("Id"):
                with st.spinner("Fetching Live Products (subscriptions)..."):
                    sub_data = fetch_subscriptions(sf_data[0]["Id"])
                if sub_data:
                    total = sum(float(s.get("SBQQ__NetPrice__c") or 0) for s in sub_data)
                    st.success(f"Subscriptions: {len(sub_data)} active (${total:,.0f})")
                else:
                    st.info("Subscriptions: no active products")

    with status_cols[1]:
        if use_admin:
            if effective_ccid:
                with st.spinner(f"Resolving dealer UUID for CCID {effective_ccid}..."):
                    uuid = admin_cars.resolve_uuid(effective_ccid)
                if not uuid:
                    st.warning("Dealer not found on admin.cars.com — analysis uses Salesforce data only.")

            if uuid:
                with st.spinner("Fetching Performance Trends..."):
                    perf_data = admin_cars.fetch_performance_trends(uuid)
                if perf_data:
                    metric_count = sum(1 for v in perf_data.values() if v is not None)
                    st.success(f"Performance Trends: ✓ {metric_count} metrics")
                else:
                    st.warning("Performance Trends: no data")

                with st.spinner("Fetching Reputation..."):
                    rep_data = admin_cars.fetch_reputation(uuid)
                if rep_data and rep_data.get("rating"):
                    st.success(f"Reputation: ✓ {rep_data['rating']}★")
                else:
                    st.info("Reputation: skipped")

                with st.spinner("Fetching Market Comparison..."):
                    mkt_data = admin_cars.fetch_market_comparison(uuid)
                if mkt_data:
                    st.success(f"Market Comparison: ✓ {mkt_data['at_pct']}% At Market")
                else:
                    st.info("Market Comparison: skipped")

    st.divider()

    data_context = build_data_context(dealer_name, sf_data, perf_data, rep_data, mkt_data, sub_data)

    st.subheader(f"Health Snapshot — {dealer_name}")
    client = anthropic.Anthropic()
    with st.container():
        response_text = ""
        placeholder = st.empty()
        with client.messages.stream(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": f"Generate a dealer health snapshot for this dealer.\n\n{data_context}"}],
        ) as stream:
            for text in stream.text_stream:
                response_text += text
                placeholder.markdown(response_text)

    st.session_state["last_result"] = {
        "dealer": dealer_name,
        "analysis": response_text,
        "sf_data": sf_data,
        "sub_data": sub_data,
        "perf_data": perf_data,
        "rep_data": rep_data,
        "mkt_data": mkt_data,
    }

# Show raw data from last run
if "last_result" in st.session_state:
    result = st.session_state["last_result"]

    if not (run and (dealer_name.strip() or ccid_override.strip())):
        st.subheader(f"Health Snapshot — {result['dealer']}")
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

elif not run:
    st.info("Enter a dealer name in the sidebar and click **Run Analysis** to generate a health snapshot.")
