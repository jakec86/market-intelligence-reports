#!/usr/bin/env python3
"""
investigation_triggers.py
Detect playbook investigation scenarios from pivoted Tableau By Store data.

Usage (standalone):
    python3 investigation_triggers.py --group sonic
    python3 investigation_triggers.py --ccids 109754,12070
    python3 investigation_triggers.py --csv ~/Documents/Tableau/my_export.csv

Usage (as module):
    from investigation_triggers import investigate_stores, format_triage_report
    flags = investigate_stores(stores_list)
    print(format_triage_report(flags, title="Sonic BMW — May 2026"))

Input shape (list of store dicts, pivoted from Tableau long format):
    {
        "Customer Name": "Stevens Creek BMW",
        "Legacy Id": "25732",
        "Maj Cust Name": "Sonic",
        "VDP Total Imps CP": "45230",
        "VDP Total Imps PP": "51800",
        "VDP Total Imps Delta": "-0.1265",
        "Total Contacts CP": "312",
        "Total Contacts PP": "389",
        "Total Contacts Delta": "-0.198",
        "Avg Daily Vehicles CP": "148",
        "Avg Daily Vehicles PP": "131",
        "Cost/Lead CP": "186.40",
        "Cost/Lead PP": "142.10",
        "Avg Daily Pct Minimally Merchandised - Total CP": "0.18",
        ...
    }
"""

import argparse
import csv
import io
import json
import os
import sys
from collections import defaultdict
from typing import Any, Dict, List, Optional

# ─── THRESHOLDS (tune here, not in logic) ─────────────────────────────────────

THRESHOLDS = {
    "connections_drop_high":   -0.10,   # Scenario 1: ≥10% MoM drop → HIGH
    "connections_drop_medium": -0.05,   # Scenario 1: ≥5% MoM drop  → MEDIUM
    "vdp_drop_high":           -0.10,   # Scenario 3: ≥10% MoM drop → HIGH
    "vdp_drop_medium":         -0.05,   # Scenario 3: ≥5% MoM drop  → MEDIUM
    "inventory_up":             0.05,   # Scenario 4: inventory rose ≥5%
    "vdp_down_while_inv_up":   -0.05,   # Scenario 4: VDPs down ≥5% when inventory up
    "cost_lead_multiplier":     1.50,   # Scenario 5: Cost/Lead > 1.5× group median → HIGH
    "cost_lead_watch":          1.25,   # Scenario 5: Cost/Lead > 1.25× group median → MEDIUM
    "merch_gap":                0.25,   # Scenario 2: under-merchandised % > 25% (i.e., <75% of inventory properly photo'd)
    "merch_worsening":          0.05,   # Scenario 2: under-merch worsened ≥5pp MoM
}

# ─── SCENARIO DEFINITIONS ─────────────────────────────────────────────────────

SCENARIO_META = {
    1: {
        "name": "Drop in Connections",
        "next_step": "Check Historical Connections for removed high-performers; review Low Engaged Inventory for above-market pricing or merchandising gaps.",
    },
    2: {
        "name": "Best Match / Merchandising Concerns",
        "next_step": "Review Best Match tab in Listings Optimizer (photo bucket, price-to-market, reviews). Check Under-Merchandised % and Competitive Set.",
    },
    3: {
        "name": "Gradual VDP Decrease",
        "next_step": "Isolate NEW vs USED split. If SRPs also declining → Best Match issue. If SRPs stable → Low Engaged Inventory (pricing/merchandising). Pull Demand Signals for vehicle mix vs DMA demand.",
    },
    4: {
        "name": "Vehicle Demand / Inventory Mismatch",
        "next_step": "Pull Demand Signals (inventory mix vs DMA demand). Review Market Area Planner for SRPs/VDPs/connections by make. Consider Accu-Trade for acquisition conversation.",
    },
    5: {
        "name": "Lead Quality / Cost Efficiency",
        "next_step": "Review Dealer Lead Intelligence + Shopper Details. Check listing quality and response time. Compare Cost/Lead vs Competitive Set.",
    },
}

# ─── METRIC KEY ALIASES ───────────────────────────────────────────────────────
# Supports both Tableau long-format pivot keys and wide-format crosstab column names.

METRIC_ALIASES = {
    # VDPs — Sonic long-format keys + ACA wide-format keys
    "vdp_cp":        ["VDP Total Imps CP", "VDP Total Imps (CP)", "Total VDP Imps"],
    "vdp_pp":        ["VDP Total Imps PP", "VDP Total Imps (PP)"],
    "vdp_delta":     ["VDP Total Imps Delta", "VDP Total Imps (Delta)",
                      "Total VDPs Delta"],                               # ACA wide format

    # Connections
    "conn_cp":       ["Total Contacts CP", "Total Contacts (CP)", "Total Connections"],
    "conn_pp":       ["Total Contacts PP", "Total Contacts (PP)"],
    "conn_delta":    ["Total Contacts Delta", "Total Contacts (Delta)",
                      "Total Contacts Delta %"],                         # ACA wide format (has % suffix)

    # Inventory
    "inv_cp":        ["Avg Daily Vehicles CP", "Avg Daily Vehicles (CP)",
                      "Avg Daily Vehicles Total CP"],
    "inv_pp":        ["Avg Daily Vehicles PP", "Avg Daily Vehicles (PP)",
                      "Avg Daily Vehicles Total PP"],
    "inv_delta":     ["Avg Daily Vehicles Delta", "Avg Daily Vehicles (Delta)"],

    # Cost/Lead — ACA uses "Marketplace Cost/Lead (no contacts)"
    "cost_lead_cp":  ["Cost/Lead CP", "Cost/Lead (CP)", "Cost Per Lead CP",
                      "Marketplace Cost/Lead (no contacts) (CP)"],       # ACA wide format
    "cost_lead_pp":  ["Cost/Lead PP", "Cost/Lead (PP)",
                      "Marketplace Cost/Lead (no contacts) (PP)"],

    # Merchandising — ACA prefixes with "Avg."
    "merch_cp":      ["Avg Daily Pct Minimally Merchandised - Total CP",
                      "Minimally Merchandised % CP", "Pct Minimally Merchandised CP",
                      "Avg. Avg Daily Pct Minimally Merchandised (CP)"], # ACA wide format
    "merch_pp":      ["Avg Daily Pct Minimally Merchandised - Total PP",
                      "Minimally Merchandised % PP",
                      "Avg. Avg Daily Pct Minimally Merchandised (PP)"],
    "merch_delta":   ["Avg Daily Pct Minimally Merchandised - Total Delta",
                      "Minimally Merchandised % Delta",
                      "Avg Daily Pct Minimally Merchandised Delta"],     # ACA wide format
}


def _get(store: dict, key: str) -> Optional[float]:
    """Look up a metric by alias list, return as float or None."""
    for alias in METRIC_ALIASES.get(key, [key]):
        val = store.get(alias)
        if val is not None and val != "" and val != "Null":
            try:
                return float(str(val).replace(",", "").replace("%", "").strip())
            except (ValueError, TypeError):
                continue
    return None


def _delta(store: dict, cp_key: str, pp_key: str, delta_key: str) -> Optional[float]:
    """
    Return MoM delta as a decimal fraction (−0.10 = −10%).

    Prefers computing from CP/PP directly — avoids the ambiguity between
    Tableau's two delta formats (decimal fraction vs. already-percentage).
    Falls back to the stored delta column with auto-normalization only when
    CP or PP is missing.
    """
    cp = _get(store, cp_key)
    pp = _get(store, pp_key)
    if cp is not None and pp is not None and pp != 0:
        return (cp - pp) / abs(pp)

    # Fall back to stored delta, normalizing if it looks like a percentage
    raw = _get(store, delta_key)
    if raw is not None and abs(raw) > 1.5:
        raw = raw / 100.0
    return raw


def _pct(val: Optional[float]) -> str:
    if val is None:
        return "n/a"
    return f"{val:+.1%}"


# ─── SCENARIO DETECTORS ───────────────────────────────────────────────────────

def _scenario_1(store: dict) -> Optional[Dict]:
    """Connections drop."""
    cp = _get(store, "conn_cp")
    pp = _get(store, "conn_pp")
    delta = _delta(store, "conn_cp", "conn_pp", "conn_delta")
    if delta is None:
        return None
    if delta <= THRESHOLDS["connections_drop_high"]:
        return {
            "scenario": 1,
            "severity": "HIGH",
            "signal": f"Connections {_pct(delta)} MoM  ({int(pp or 0):,} → {int(cp or 0):,})",
        }
    if delta <= THRESHOLDS["connections_drop_medium"]:
        return {
            "scenario": 1,
            "severity": "MEDIUM",
            "signal": f"Connections {_pct(delta)} MoM  ({int(pp or 0):,} → {int(cp or 0):,})",
        }
    return None


def _scenario_2(store: dict) -> Optional[Dict]:
    """
    Merchandising gap (Best Match proxy — no Best Match score in Tableau export).

    "Avg Daily Pct Minimally Merchandised" = % of inventory that HAS proper
    photos/content (high = good). Under-merchandised % = 100 - this value.
    Flag when under-merchandised % > 25 (i.e., minimally merchandised < 75%).
    """
    merch_cp = _get(store, "merch_cp")
    merch_delta = _delta(store, "merch_cp", "merch_pp", "merch_delta")
    if merch_cp is None:
        return None

    # Normalize to 0–100 scale if stored as 0–1 decimal
    if merch_cp <= 1.0:
        merch_cp = merch_cp * 100

    under_merch_pct = 100.0 - merch_cp

    if under_merch_pct >= THRESHOLDS["merch_gap"] * 100:
        # merch_delta is positive when MORE vehicles become merchandised (improving)
        # worsening = delta is negative (fewer vehicles properly merchandised MoM)
        merch_delta_pp = (merch_delta * 100) if merch_delta is not None else None
        worsening = merch_delta_pp is not None and merch_delta_pp < -(THRESHOLDS["merch_worsening"] * 100)
        delta_str = f", worsening {abs(merch_delta_pp):.1f}pp MoM" if worsening else ""
        severity = "HIGH" if worsening else "MEDIUM"
        return {
            "scenario": 2,
            "severity": severity,
            "signal": f"Under-merchandised {under_merch_pct:.0f}% of inventory{delta_str}",
        }
    return None


def _scenario_3(store: dict) -> Optional[Dict]:
    """VDP decrease."""
    cp = _get(store, "vdp_cp")
    pp = _get(store, "vdp_pp")
    delta = _delta(store, "vdp_cp", "vdp_pp", "vdp_delta")
    if delta is None:
        return None
    if delta <= THRESHOLDS["vdp_drop_high"]:
        return {
            "scenario": 3,
            "severity": "HIGH",
            "signal": f"VDPs {_pct(delta)} MoM  ({int(pp or 0):,} → {int(cp or 0):,})",
        }
    if delta <= THRESHOLDS["vdp_drop_medium"]:
        return {
            "scenario": 3,
            "severity": "MEDIUM",
            "signal": f"VDPs {_pct(delta)} MoM  ({int(pp or 0):,} → {int(cp or 0):,})",
        }
    return None


def _scenario_4(store: dict) -> Optional[Dict]:
    """Inventory up, VDPs down → demand mismatch."""
    inv_delta = _delta(store, "inv_cp", "inv_pp", "inv_delta")
    vdp_delta = _delta(store, "vdp_cp", "vdp_pp", "vdp_delta")
    if inv_delta is None or vdp_delta is None:
        return None
    if inv_delta >= THRESHOLDS["inventory_up"] and vdp_delta <= THRESHOLDS["vdp_down_while_inv_up"]:
        inv_cp = _get(store, "inv_cp")
        inv_pp = _get(store, "inv_pp")
        return {
            "scenario": 4,
            "severity": "HIGH",
            "signal": (
                f"Inventory {_pct(inv_delta)} MoM "
                f"({int(inv_pp or 0)} → {int(inv_cp or 0)} avg/day) "
                f"while VDPs {_pct(vdp_delta)} — mix/demand mismatch"
            ),
        }
    return None


def _scenario_5(store: dict, group_median_cost_lead: Optional[float]) -> Optional[Dict]:
    """Cost/Lead outlier vs group median."""
    cost_cp = _get(store, "cost_lead_cp")
    if cost_cp is None or group_median_cost_lead is None or group_median_cost_lead == 0:
        return None
    ratio = cost_cp / group_median_cost_lead
    if ratio >= THRESHOLDS["cost_lead_multiplier"]:
        return {
            "scenario": 5,
            "severity": "HIGH",
            "signal": f"Cost/Lead ${cost_cp:.0f} vs group median ${group_median_cost_lead:.0f} ({ratio:.1f}×)",
        }
    if ratio >= THRESHOLDS["cost_lead_watch"]:
        return {
            "scenario": 5,
            "severity": "MEDIUM",
            "signal": f"Cost/Lead ${cost_cp:.0f} vs group median ${group_median_cost_lead:.0f} ({ratio:.1f}×)",
        }
    return None


# ─── BRIGHT SPOT DETECTOR ─────────────────────────────────────────────────────

def _is_bright_spot(store: dict) -> Optional[Dict]:
    """Positive momentum: VDPs AND connections both growing MoM."""
    vdp_d  = _delta(store, "vdp_cp",  "vdp_pp",  "vdp_delta")
    conn_d = _delta(store, "conn_cp", "conn_pp", "conn_delta")
    if vdp_d is not None and conn_d is not None and vdp_d > 0.05 and conn_d > 0.05:
        return {
            "signal": f"VDPs {_pct(vdp_d)} + Connections {_pct(conn_d)} MoM",
        }
    return None


# ─── MAIN ENTRY POINTS ────────────────────────────────────────────────────────

def investigate_stores(stores: List[Dict], group_label: str = "") -> dict:
    """
    Run all scenario detectors across a list of store dicts.

    Returns:
        {
            "high":   [{"store": str, "ccid": str, "flags": [...]}],
            "medium": [...],
            "bright_spots": [...],
            "clean":  [...],   # stores with no flags
        }
    """
    # Compute group median Cost/Lead (ignoring zeros/nulls)
    cost_leads = [
        v for s in stores
        if (v := _get(s, "cost_lead_cp")) is not None and v > 0
    ]
    median_cost_lead = sorted(cost_leads)[len(cost_leads) // 2] if cost_leads else None

    results = {"high": [], "medium": [], "bright_spots": [], "clean": []}

    for store in stores:
        name = store.get("Customer Name", "Unknown")
        ccid = store.get("Legacy Id", "")

        flags = []
        for detect_fn in [_scenario_1, _scenario_3, _scenario_4, _scenario_2]:
            flag = detect_fn(store)
            if flag:
                flags.append(flag)

        cost_flag = _scenario_5(store, median_cost_lead)
        if cost_flag:
            flags.append(cost_flag)

        bright = _is_bright_spot(store)

        if flags:
            entry = {"store": name, "ccid": ccid, "flags": flags}
            if any(f["severity"] == "HIGH" for f in flags):
                results["high"].append(entry)
            else:
                results["medium"].append(entry)
        elif bright:
            results["bright_spots"].append({"store": name, "ccid": ccid, "signal": bright["signal"]})
        else:
            results["clean"].append({"store": name, "ccid": ccid})

    # Sort high-priority by number of HIGH flags descending
    results["high"].sort(key=lambda x: sum(1 for f in x["flags"] if f["severity"] == "HIGH"), reverse=True)

    return results


def format_triage_report(results: dict, title: str = "Investigation Triage") -> str:
    """Format investigate_stores() output as a readable triage report."""
    lines = [f"\n{'─'*60}", f"  {title.upper()}", f"{'─'*60}"]

    high = results["high"]
    medium = results["medium"]
    bright = results["bright_spots"]
    clean = results["clean"]

    total_flagged = len(high) + len(medium)
    lines.append(
        f"\n{total_flagged} store(s) flagged  "
        f"({len(high)} HIGH · {len(medium)} MEDIUM)  "
        f"| {len(bright)} bright spot(s) | {len(clean)} clean\n"
    )

    for severity_label, bucket in [("HIGH PRIORITY", high), ("MEDIUM PRIORITY", medium)]:
        if not bucket:
            continue
        lines.append(f"{severity_label} ({len(bucket)} stores)")
        lines.append("─" * 40)
        for i, entry in enumerate(bucket, 1):
            lines.append(f"\n  {i}. {entry['store']}  (CCID {entry['ccid']})")
            seen_scenarios = set()
            for flag in entry["flags"]:
                snum = flag["scenario"]
                lines.append(f"     [{flag['severity']}] Scenario {snum} — {SCENARIO_META[snum]['name']}")
                lines.append(f"           {flag['signal']}")
                seen_scenarios.add(snum)
            # Deduplicated next steps
            for snum in sorted(seen_scenarios):
                lines.append(f"     → {SCENARIO_META[snum]['next_step']}")
        lines.append("")

    if bright:
        lines.append(f"BRIGHT SPOTS ({len(bright)} stores)")
        lines.append("─" * 40)
        for entry in bright:
            lines.append(f"  ✓ {entry['store']}  —  {entry['signal']}")
        lines.append("")

    return "\n".join(lines)


# ─── CSV LOADER (for standalone CLI use) ──────────────────────────────────────

def load_tableau_csv(path: str, ccid_filter: Optional[List[str]] = None) -> list[dict]:
    """
    Load a Tableau By Store export CSV (long or wide format) into store dicts.
    Handles UTF-16LE BOM automatically.
    """
    raw = open(path, "rb").read()
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        text = raw.decode("utf-16")
    else:
        text = raw.decode("utf-8", errors="replace")

    # Detect delimiter
    sample = text[:500]
    delimiter = "\t" if "\t" in sample else ","

    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    rows = list(reader)

    if not rows:
        return []

    headers = list(rows[0].keys())

    # Long format: has 'Measure Names' + 'Measure Values' columns
    if "Measure Names" in headers and "Measure Values" in headers:
        stores: dict[str, dict] = {}
        for row in rows:
            name = row.get("Customer Name", "").strip()
            if not name:
                continue
            if ccid_filter and row.get("Legacy Id", "").strip() not in ccid_filter:
                continue
            if name not in stores:
                stores[name] = {
                    "Customer Name": name,
                    "Legacy Id": row.get("Legacy Id", "").strip(),
                    "Maj Cust Name": row.get("Maj Cust Name", "").strip(),
                    "AE": row.get("AE", "").strip(),
                }
            measure = row.get("Measure Names", "").strip()
            value = row.get("Measure Values", "").strip()
            if measure:
                stores[name][measure] = value
        return list(stores.values())

    # Wide format: one row per store
    result = []
    for row in rows:
        name = row.get("Customer Name", row.get("Store Name", "")).strip()
        if not name:
            continue
        ccid = row.get("Legacy Id", row.get("CCID", "")).strip()
        if ccid_filter and ccid not in ccid_filter:
            continue
        result.append(dict(row))
    return result


# ─── CLI ──────────────────────────────────────────────────────────────────────

def _cli():
    parser = argparse.ArgumentParser(
        description="Run investigation triggers on Tableau store data."
    )
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--csv", metavar="PATH", help="Path to Tableau By Store CSV export")
    src.add_argument("--group", metavar="NAME",
                     help="Pull live Tableau data for a group (sonic, aca, hendrick, etc.) — requires TABLEAU_PAT_SECRET env var")
    parser.add_argument("--ccids", metavar="1234,5678", help="Filter to specific CCIDs (comma-separated)")
    parser.add_argument("--title", default="", help="Report title")
    parser.add_argument("--json", action="store_true", dest="output_json", help="Output raw JSON instead of formatted report")
    args = parser.parse_args()

    ccid_filter = [c.strip() for c in args.ccids.split(",")] if args.ccids else None
    title = args.title

    if args.csv:
        stores = load_tableau_csv(args.csv, ccid_filter=ccid_filter)
        if not title:
            title = f"Investigation Triage — {os.path.basename(args.csv)}"
    else:
        stores = _pull_tableau_group(args.group, ccid_filter=ccid_filter)
        if not title:
            title = f"Investigation Triage — {args.group.title()}"

    if not stores:
        print("No stores loaded. Check the CSV path or group filter.", file=sys.stderr)
        sys.exit(1)

    results = investigate_stores(stores)

    if args.output_json:
        print(json.dumps(results, indent=2))
    else:
        print(format_triage_report(results, title=title))
        print(f"\n{len(stores)} stores analyzed.\n")


def _pull_tableau_group(group: str, ccid_filter: Optional[List[str]] = None) -> list[dict]:
    """Pull live Tableau By Store data for a named group via REST API."""
    import subprocess
    import urllib.request

    GROUP_FILTERS = {
        "sonic":    "Sonic",
        "aca":      "Atlantic Coast Automotive MA Group",
        "hendrick": "Hendrick Automotive Group",
        "asbury":   "Asbury",
        "herb":     "Herb Chambers MA Group",
        "greenway": "Greenway MA Group",
        "koons":    "Koons Automotive MA Group",
        "echopark": "EchoPark MA Group",
        "indigo":   "Indigo Auto MA Group",
        "doherty":  "Doherty MA Group",
        "jim_ellis":"Jim Ellis MA Group",
        "larry_miller": "Larry Miller",
    }

    filter_val = GROUP_FILTERS.get(group.lower().replace(" ", "_"), group)

    pat_name   = os.environ.get("TABLEAU_PAT_NAME", "Claude")
    pat_secret = os.environ.get("TABLEAU_PAT_SECRET", "")
    if not pat_secret:
        print("Error: set TABLEAU_PAT_SECRET env var to use --group mode.", file=sys.stderr)
        sys.exit(1)

    tableau_host = "https://us-west-2b.online.tableau.com"
    site_id      = "12338861-20b1-46ed-8841-269a5a937edb"
    view_id      = "a0b9bdce-2db3-4ea0-a2fc-365fd08c5786"

    # Auth
    auth_payload = json.dumps({
        "credentials": {
            "personalAccessTokenName": pat_name,
            "personalAccessTokenSecret": pat_secret,
            "site": {"contentUrl": "cars"},
        }
    }).encode()
    auth_req = urllib.request.Request(
        f"{tableau_host}/api/3.22/auth/signin",
        data=auth_payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(auth_req) as resp:
        token = json.loads(resp.read())["credentials"]["token"]

    # Data fetch
    import urllib.parse
    filter_param = urllib.parse.quote(filter_val)
    data_url = (
        f"{tableau_host}/api/3.22/sites/{site_id}/views/{view_id}"
        f"/data?vf_Maj%20Cust%20Name={filter_param}"
    )
    data_req = urllib.request.Request(data_url, headers={"X-Tableau-Auth": token})
    with urllib.request.urlopen(data_req) as resp:
        raw_csv = resp.read().decode("utf-8", errors="replace")

    stores: dict[str, dict] = {}
    for row in csv.DictReader(io.StringIO(raw_csv)):
        name = row.get("Customer Name", "").strip()
        if not name:
            continue
        ccid = row.get("Legacy Id", "").strip()
        if ccid_filter and ccid not in ccid_filter:
            continue
        if name not in stores:
            stores[name] = {
                "Customer Name": name,
                "Legacy Id": ccid,
                "Maj Cust Name": row.get("Maj Cust Name", "").strip(),
            }
        measure = row.get("Measure Names", "").strip()
        value   = row.get("Measure Values", "").strip()
        if measure:
            stores[name][measure] = value

    return list(stores.values())


if __name__ == "__main__":
    _cli()
