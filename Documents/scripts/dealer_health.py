"""
dealer_health.py — Dealer Health Dashboard (standalone Streamlit app).

All analysis logic lives in health_analysis.py. This file is pure UI.

Run:
    python3 -m streamlit run ~/Documents/scripts/dealer_health.py
"""

import os
import re as _re
import time
import streamlit as st
import pandas as pd
import admin_cars
from typing import Optional, List

from health_analysis import (
    fetch_salesforce, fetch_salesforce_by_ccid, fetch_subscriptions,
    build_data_context, parse_scores, render_score_bars,
    run_health_analysis, create_health_doc,
)

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

# ─── PAGE CONFIG ──────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Cars.com | Dealer Health Dashboard",
    page_icon="🚗",
    layout="wide",
)
st.markdown(CC_CSS, unsafe_allow_html=True)


@st.cache_data(ttl=300)
def _session_ok() -> bool:
    return admin_cars.check_session()


# ─── SIDEBAR ──────────────────────────────────────────────────────────────────

with st.sidebar:
    st.header("Configuration")
    dealer_name = st.text_input("Dealer Name", placeholder="e.g. Hendrick, Nalley Lexus Galleria")
    ccid_override = st.text_input(
        "CCID (optional)",
        placeholder="Use when the name matches multiple accounts",
        help="If provided, skips the name-based Salesforce lookup and uses this CCID directly.",
    )

    st.subheader("Data Sources")
    use_sf    = st.checkbox("Salesforce", value=True)
    use_admin = st.checkbox("admin.cars.com — Performance Trends", value=True)
    with st.expander("Extended Demand Signals", expanded=False):
        use_wid = st.checkbox("Walk-in Demand Index", value=True)
        use_vd  = st.checkbox("Vehicle Demand (top segments)", value=True)

    import datetime as _dt
    _today = _dt.date.today()
    _prev_month_dt = (_today.replace(day=1) - _dt.timedelta(days=1))
    _curr_label = f"Current MTD ({_today.strftime('%B %Y')})"
    _prev_label = f"Previous Month ({_prev_month_dt.strftime('%B %Y')})"
    report_period  = st.radio("Report Period", [_curr_label, _prev_label], index=0, horizontal=True)
    use_prev_month = report_period == _prev_label

    session_ok = _session_ok() if use_admin else True
    if use_admin:
        if session_ok:
            st.success("● admin.cars.com connected")
            if st.button("Refresh session status", use_container_width=True):
                st.cache_data.clear()
                st.rerun()
        else:
            st.error("✗ Not connected to Chrome / not signed in")
            st.caption("Launch Chrome with remote debugging and sign in to admin.cars.com:")
            st.code(
                'pkill -x "Google Chrome" 2>/dev/null; sleep 2; '
                'mkdir -p ~/.chrome-dealer-health && '
                'nohup "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" '
                '--remote-debugging-port=9223 '
                '--user-data-dir="$HOME/.chrome-dealer-health" '
                "--remote-allow-origins='*' "
                '--no-first-run --no-default-browser-check '
                '> /tmp/chrome-debug.log 2>&1 &',
                language="bash",
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
        "admin.cars.com, then generates a health snapshot using Claude."
    )

# ─── MAIN ANALYSIS ────────────────────────────────────────────────────────────

if run and (dealer_name.strip() or ccid_override.strip()):
    dealer_name    = dealer_name.strip()
    ccid_override  = ccid_override.strip()
    effective_ccid = ccid_override or None

    sf_data = sub_data = None
    perf_data = rep_data = mkt_data = lo_data = si_data = roi_data = None
    wid_data = vd_data = None
    source_summary = []

    progress  = st.empty()
    _run_start = time.time()

    def _progress(msg):
        elapsed = time.time() - _run_start
        progress.markdown(
            f"<div style='color:#5b2d8e;font-size:0.9rem;'>⏳ {msg} "
            f"<span style='color:#999;font-size:0.8rem;'>({elapsed:.0f}s)</span></div>",
            unsafe_allow_html=True,
        )

    if use_sf:
        _progress("Querying Salesforce…")
        sf_data = fetch_salesforce_by_ccid(effective_ccid) if effective_ccid else fetch_salesforce(dealer_name)
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
        _progress("Opening admin.cars.com and resolving dealer UUID…")
        _admin_err = None
        try:
            with admin_cars.session(restart=False) as admin:
                uuid = admin.resolve_uuid(effective_ccid)
                if not uuid:
                    source_summary.append("admin.cars.com: dealer UUID not found")
                else:
                    for report, fetch_fn, label_fn in [
                        ("Performance Trends",  admin.fetch_performance_trends,  lambda d: f"Performance Trends: {sum(1 for v in d.values() if v is not None)} metrics"),
                        ("Reputation Health",   admin.fetch_reputation,          lambda d: f"Reputation: {d.get('rating')}★"),
                        ("Market Comparison",   admin.fetch_market_comparison,   lambda d: f"Market Comparison: {d.get('at_pct')}% at market"),
                        ("Listings Optimizer",  admin.fetch_listings_optimizer,  lambda d: f"Listings Optimizer: {len(d.get('within_500_good',[]))+len(d.get('within_500_great',[]))} pricing opps"),
                        ("ROI One-Sheeter",     admin.fetch_roi_one_sheeter,     lambda d: f"Lead sources: {d['lead_sources'].get('total',0)} connections" if d.get('lead_sources') else None),
                        ("Sales Influence",     admin.fetch_sales_influence,     lambda d: "DMS: connected" if d.get('dms_connected') else "DMS: not connected"),
                    ]:
                        _progress(f"Pulling {report}…")
                        data = fetch_fn(uuid)
                        if report == "Performance Trends":    perf_data = data
                        elif report == "Reputation Health":  rep_data  = data
                        elif report == "Market Comparison":  mkt_data  = data
                        elif report == "Listings Optimizer": lo_data   = data
                        elif report == "ROI One-Sheeter":    roi_data  = data
                        elif report == "Sales Influence":    si_data   = data
                        if data:
                            lbl = label_fn(data)
                            if lbl: source_summary.append(lbl)

                    if use_wid:
                        _progress("Pulling Walk-in Demand…")
                        wid_data = admin.fetch_walk_in_demand(uuid)
                        source_summary.append("Walk-in Demand: " + ("data available" if wid_data else "not available"))
                    if use_vd:
                        _progress("Pulling Vehicle Demand…")
                        vd_data = admin.fetch_vehicle_demand(uuid)
                        source_summary.append("Vehicle Demand: " + ("data available" if vd_data else "not available"))
        except Exception as _e:
            _admin_err = str(_e)
            source_summary.append(f"admin.cars.com: skipped — session error")
            progress.empty()
            st.warning(
                "⚠️ **admin.cars.com session issue.** "
                "Chrome may have been redirected to JumpCloud SSO. "
                "Sign in to admin.cars.com in the dealer health Chrome window, "
                "then click **Run Analysis** again. "
                "Generating snapshot with Salesforce data only."
            )

    _progress("Generating health snapshot…")

    data_context = build_data_context(
        dealer_name=dealer_name, sf_data=sf_data,
        perf_data=perf_data, rep_data=rep_data, mkt_data=mkt_data,
        sub_data=sub_data, lo_data=lo_data, si_data=si_data,
        roi_data=roi_data, wid_data=wid_data, vd_data=vd_data,
        use_prev_month=use_prev_month,
    )
    progress.empty()

    missing = admin_cars.get_last_missing_worksheets()
    if missing:
        st.warning(
            "⚠️ admin.cars.com layout has changed — some worksheets not found:\n\n" +
            "\n\n".join(f"**{s}**: missing `{', '.join(ws)}`" for s, ws in missing.items())
        )

    period_label = _prev_label if use_prev_month else _curr_label
    with st.spinner("Generating health snapshot… (~90s)"):
        response_text = run_health_analysis(dealer_name, data_context, period_label)

    if response_text.startswith("ERROR:"):
        st.error(response_text)
    else:
        scores, _ = parse_scores(response_text)
        st.session_state["last_result"] = {
            "dealer": dealer_name, "analysis": response_text, "scores": scores,
            "sf_data": sf_data, "sub_data": sub_data,
            "perf_data": perf_data, "rep_data": rep_data, "mkt_data": mkt_data,
            "lo_data": lo_data, "si_data": si_data, "roi_data": roi_data,
            "wid_data": wid_data, "vd_data": vd_data, "source_summary": source_summary,
        }

    if source_summary:
        with st.expander(f"Data sources pulled · {len(source_summary)} checks", expanded=False):
            for line in source_summary:
                st.markdown(f"- {line}")

# ─── RESULTS ──────────────────────────────────────────────────────────────────

if "last_result" in st.session_state:
    result = st.session_state["last_result"]

    if st.button("📄 Export to Google Doc", key="export_doc"):
        with st.spinner("Creating Google Doc…"):
            try:
                _, _narrative = parse_scores(result["analysis"])
                doc_url = create_health_doc(
                    dealer_name=result["dealer"], scores=result.get("scores", []),
                    narrative=_narrative, wid_data=result.get("wid_data"),
                    vd_data=result.get("vd_data"), sf_data=result.get("sf_data"),
                    perf_data=result.get("perf_data"),
                )
                st.success(f"Doc created — [Open in Google Docs]({doc_url})")
            except Exception as _e:
                st.error(f"Doc creation failed: {_e}")

    _scores = result.get("scores", [])
    if _scores:
        st.markdown(render_score_bars(_scores), unsafe_allow_html=True)
    _, _narrative = parse_scores(result["analysis"])
    st.markdown(_re.sub(r'\$(?!\$)', r'\\$', _narrative))

    st.divider()

    with st.expander("Raw Salesforce Data", expanded=False):
        st.dataframe(pd.DataFrame(result["sf_data"]), use_container_width=True) if result.get("sf_data") else st.info("No Salesforce data")

    with st.expander("Active Marketplace Subscriptions (Live Products)", expanded=False):
        st.dataframe(pd.DataFrame(result["sub_data"]), use_container_width=True) if result.get("sub_data") else st.info("No active subscriptions")

    with st.expander("Raw admin.cars.com Data", expanded=False):
        col1, col2, col3 = st.columns(3)
        col1.caption("Performance Trends"); col1.json(result.get("perf_data") or {})
        col2.caption("Reputation");         col2.json(result.get("rep_data") or {})
        col3.caption("Market Comparison");  col3.json(result.get("mkt_data") or {})
        col4, col5, col6 = st.columns(3)
        col4.caption("Listings Optimizer"); col4.json(result.get("lo_data") or {})
        col5.caption("Sales Influence");    col5.json(result.get("si_data") or {})
        col6.caption("ROI One-Sheeter");    col6.json(result.get("roi_data") or {})

elif not run:
    st.info("Enter a dealer name in the sidebar and click **Run Analysis** to generate a health snapshot.")
