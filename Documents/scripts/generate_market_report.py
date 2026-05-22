#!/usr/bin/env python3
"""
Market Intelligence Report Generator

Pulls "Search Volume by Zip Code" data from Tableau, maps ZIPs to cities via pgeocode,
and injects the aggregated data into an HTML template to produce a standalone report.

Usage:
    python3 generate_market_report.py
    python3 generate_market_report.py --dma "Norfolk-Portsmth-Newpt Nws" --makes "Toyota,Honda"

Paths:
    Template:  ~/Documents/templates/market_intelligence_template.html
    Reports:   ~/Documents/Reports/<DMA-slug>/
    Tableau:   ~/Documents/Tableau/SearchVolumeByZipCode.csv  (manual download fallback)
"""

import os
import re
import json
import sys
import shutil
import argparse
import requests
import pandas as pd
import pgeocode
from io import StringIO
from datetime import datetime
from pathlib import Path
from collections import namedtuple

QCResult = namedtuple('QCResult', ['filter_ignored', 'rows_filtered', 'rows_unfiltered'])

# ── Config ────────────────────────────────────────────────────────────────────

TABLEAU_SERVER     = "https://us-west-2b.online.tableau.com"
TABLEAU_SITE       = "cars"
TABLEAU_PAT_NAME   = os.environ.get("TABLEAU_PAT_NAME", "Claude")
TABLEAU_PAT_SECRET = os.environ.get("TABLEAU_PAT_SECRET", "")

# "Searches by Zip Code" view (dashboard with 2 sheets)
VIEW_ID = "39464986-86f3-49a2-af82-37f1486743ff"

TEMPLATE_PATH = Path.home() / "Documents" / "templates" / "market_intelligence_template.html"
REPORTS_BASE  = Path.home() / "Documents" / "Reports"
TABLEAU_DIR   = Path.home() / "Documents" / "Tableau"

# ── Prompts ───────────────────────────────────────────────────────────────────

def prompt_inputs(args):
    """Prompt for DMA and makes if not supplied via CLI args."""
    dma = args.dma
    if not dma:
        print("\nEnter the Tableau DMA name exactly as it appears in the data.")
        print('  Example: "Norfolk-Portsmth-Newpt Nws"  or  "Atlanta"')
        dma = input("DMA: ").strip()
        if not dma:
            print("DMA is required.")
            sys.exit(1)

    makes = args.makes
    if not makes:
        print("\nEnter make(s) to filter, comma-separated — or press Enter for All.")
        print('  Example: "Toyota,Honda,Ford"')
        raw = input("Make(s) [All]: ").strip()
        makes = raw if raw else "All"

    return dma, makes


def parse_makes(makes_str):
    """Return list of makes, or empty list if 'All'."""
    if makes_str.strip().lower() in ("all", ""):
        return []
    return [m.strip() for m in makes_str.split(",") if m.strip()]

# ── Tableau Auth ──────────────────────────────────────────────────────────────

def tableau_signin():
    url = f"{TABLEAU_SERVER}/api/3.21/auth/signin"
    payload = {
        "credentials": {
            "personalAccessTokenName": TABLEAU_PAT_NAME,
            "personalAccessTokenSecret": TABLEAU_PAT_SECRET,
            "site": {"contentUrl": TABLEAU_SITE},
        }
    }
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    r = requests.post(url, json=payload, headers=headers)
    r.raise_for_status()
    creds = r.json()["credentials"]
    return creds["token"], creds["site"]["id"]


def tableau_signout(token):
    requests.post(f"{TABLEAU_SERVER}/api/3.21/auth/signout",
                  headers={"x-tableau-auth": token})

# ── Data Download ─────────────────────────────────────────────────────────────

def download_view_csv(token, site_id, dma):
    """Download ZIP-level search volume for the DMA. All-make only — vf_make is silently ignored by this view."""
    url = f"{TABLEAU_SERVER}/api/3.21/sites/{site_id}/views/{VIEW_ID}/data"
    params = {"vf_dma_market_name": dma, "maxAge": 1}
    r = requests.get(url, headers={"x-tableau-auth": token}, params=params)
    r.raise_for_status()
    return r.text


def _qc_filter_check(token, site_id, dma, makes):
    """Verify vf_make filter has actual effect on this view. Non-blocking — logs findings only."""
    if not makes:
        return QCResult(filter_ignored=False, rows_filtered=0, rows_unfiltered=0)
    url = f"{TABLEAU_SERVER}/api/3.21/sites/{site_id}/views/{VIEW_ID}/data"
    base = {"vf_dma_market_name": dma, "maxAge": 1}
    r_all  = requests.get(url, headers={"x-tableau-auth": token}, params=base)
    r_make = requests.get(url, headers={"x-tableau-auth": token},
                          params={**base, "vf_make": ",".join(makes)})
    n_all  = len(r_all.text.strip().splitlines())
    n_make = len(r_make.text.strip().splitlines())
    ignored = n_make >= n_all * 0.95
    print(f"  QC filter check: unfiltered={n_all} rows, make-filtered={n_make} rows "
          f"→ filter {'SILENTLY IGNORED' if ignored else 'working'}")
    return QCResult(filter_ignored=ignored, rows_filtered=n_make, rows_unfiltered=n_all)


def parse_csv(raw):
    """
    Parse Tableau CSV export.  Handles:
      - UTF-16 LE (Tableau crosstab export) or UTF-8
      - Tab-separated crosstab with 2-row meta-header (quarterly pivot)
      - Standard comma-separated single-header CSV
    """
    # Decode bytes
    if isinstance(raw, (bytes, bytearray)):
        if raw[:2] in (b'\xff\xfe', b'\xfe\xff'):
            text = raw.decode('utf-16')
        else:
            text = raw.decode('utf-8', errors='replace')
    else:
        text = raw

    # Tableau crosstab: tab-separated, first two rows are meta-headers
    try:
        df = pd.read_csv(StringIO(text), sep='\t', skiprows=[0, 1], header=0)
        if len(df.columns) > 2:
            return df
    except Exception:
        pass

    return pd.read_csv(StringIO(text))


def aggregate_quarter_cols(df, quarters=None):
    """
    If the dataframe has quarterly columns (e.g. '2023 Q4', '2024 Q1'),
    sum them into a single 'searches' column and return updated df.
    If quarters is set, only use the most recent N quarters.
    """
    quarter_cols = sorted([c for c in df.columns if re.match(r'^\d{4}\s+Q\d$', str(c).strip())])
    if not quarter_cols:
        return df
    if quarters and quarters < len(quarter_cols):
        quarter_cols = quarter_cols[-quarters:]
        print(f"Using trailing {quarters} quarters: {quarter_cols}")
    for c in quarter_cols:
        df[c] = pd.to_numeric(df[c].astype(str).str.replace(',', ''), errors='coerce')
    df['searches'] = df[quarter_cols].sum(axis=1, min_count=1)
    df['filled_quarters'] = df[quarter_cols].notna().sum(axis=1)
    df['searches_avg_per_q'] = (df['searches'] / df['filled_quarters'].replace(0, 1)).round(1)
    print(f"Quarterly columns summed → 'searches': {quarter_cols}")
    return df


def _qc_quarter_coverage(df, quarter_cols):
    """Warn if many ZIPs have incomplete quarter history (causes raw-sum skew)."""
    if not quarter_cols:
        return
    max_q = len(quarter_cols)
    full_count = (df[quarter_cols].notna().sum(axis=1) == max_q).sum()
    pct = full_count / len(df) * 100 if len(df) > 0 else 100.0
    print(f"Quarter coverage: {full_count}/{len(df)} ZIPs have all {max_q} quarters ({pct:.0f}%)")
    if pct < 60:
        print(f"  WARNING: Only {pct:.0f}% of ZIPs fully covered — "
              f"using searches_avg_per_q (per-quarter avg) to reduce skew. "
              f"Pass --quarters 4 to limit to trailing year.")


def detect_sheet_type(df):
    cols_lower = [c.lower() for c in df.columns]
    # Quarterly pivot = volume data
    if any(re.match(r'^\d{4}\s+Q\d$', str(c).strip()) for c in df.columns):
        return "volume"
    if any("%" in c for c in df.columns) and not any("search" in c and "%" not in c for c in cols_lower):
        return "pct_change"
    if any("search" in c and "%" not in c for c in cols_lower):
        return "volume"
    return "unknown"

# ── Demand Mode (v2) ─────────────────────────────────────────────────────────

_DEMAND_COL_MAP = {
    'market vdps': 'market_vdps',
    'market vehicles': 'market_vehicles',
    'market connections': 'market_connections',
    'dealer vdps': 'dealer_vdps',
    'dealer vehicles': 'dealer_vehicles',
    'dealer connections': 'dealer_connections',
    'vdp share (%)': 'vdp_share_pct',
    'vehicle share (%)': 'vehicle_share_pct',
    'connections share (%)': 'conn_share_pct',
    'make': 'make',
    'model': 'model',
    'stock type': 'stock_type',
    'dma market name': 'dma',
}
_DEMAND_NUMERIC = ['market_vdps', 'market_vehicles', 'market_connections',
                   'dealer_vdps', 'dealer_vehicles', 'dealer_connections']
_DEMAND_METRIC_COL = {'vdp': 'market_vdps', 'connections': 'market_connections', 'vehicles': 'market_vehicles'}
_DEMAND_METRIC_LABEL = {'vdp': 'Market VDPs', 'connections': 'Market Connections', 'vehicles': 'Market Vehicles'}


def load_demand_signals_csv(path, makes=None, stock_types=None):
    """
    Load a demand signals Market Comparison CSV (admin.cars.com crosstab).
    Returns a normalized DataFrame with make/model/stock_type + Market VDPs/connections/vehicles.
    Make filtering works here — data has a Make column (unlike the ZIP view).
    """
    with open(path, 'rb') as f:
        raw = f.read()
    if raw[:2] in (b'\xff\xfe', b'\xfe\xff'):
        text = raw.decode('utf-16')
    else:
        text = raw.decode('utf-8', errors='replace')

    df = pd.read_csv(StringIO(text), sep='\t')

    # Normalize column names using lowercase key lookup
    col_map = {}
    for c in df.columns:
        key = c.strip().lower()
        if key in _DEMAND_COL_MAP:
            col_map[c] = _DEMAND_COL_MAP[key]
    df = df.rename(columns=col_map)

    # Keep only known columns
    keep = [v for v in _DEMAND_COL_MAP.values() if v in df.columns]
    df = df[keep].copy()

    _required = {'make', 'market_vdps'}
    missing_required = _required - set(df.columns)
    if missing_required:
        raw_cols = [c.strip() for c in pd.read_csv(StringIO(text), sep='\t', nrows=0).columns]
        print(f"  ✗ Demand Signal CSV missing required columns after rename: {missing_required}")
        print(f"    Raw CSV headers: {raw_cols}")
        print(f"    Recognized columns found: {list(df.columns)}")
        sys.exit(1)

    # Parse numeric columns (strip commas)
    for c in _DEMAND_NUMERIC:
        if c in df.columns:
            df[c] = pd.to_numeric(
                df[c].astype(str).str.replace(',', '').str.strip(),
                errors='coerce'
            ).fillna(0).astype(int)

    # Drop rows where make is blank
    if 'make' in df.columns:
        df = df[df['make'].notna() & (df['make'].str.strip() != '')]

    # Optional filters (actually work — data has Make and Stock type columns)
    if makes:
        df = df[df['make'].str.lower().isin([m.lower() for m in makes])]
    if stock_types:
        df = df[df['stock_type'].str.lower().isin([s.lower() for s in stock_types])]

    return df


def aggregate_dma_demand(df, metric='vdp', group_by='make'):
    """
    Aggregate DMA market demand totals.
    group_by: 'make' | 'make_model'
    Returns DataFrame sorted descending by the chosen metric.
    """
    metric_col = _DEMAND_METRIC_COL.get(metric, 'market_vdps')
    agg_cols = [c for c in _DEMAND_NUMERIC if c in df.columns]

    if group_by == 'make':
        grp_keys = ['make']
    else:
        grp_keys = [k for k in ['make', 'model', 'stock_type'] if k in df.columns]

    grp = df.groupby(grp_keys)[agg_cols].sum().reset_index()
    grp = grp.sort_values(metric_col, ascending=False).reset_index(drop=True)

    total = grp[metric_col].sum()
    grp['pct'] = (grp[metric_col] / total * 100).round(1) if total > 0 else 0.0

    return grp


def _find_demand_csv(dma, makes):
    """Auto-discover the most recent demand signals CSV in ~/Documents/Tableau/."""
    import glob
    patterns = ['*market_comparison*', '*demand_signals*', '*demand*']
    candidates = []
    for pat in patterns:
        candidates.extend(glob.glob(str(TABLEAU_DIR / pat)))
    # Sort by modification time, newest first
    candidates = sorted(set(candidates), key=lambda p: Path(p).stat().st_mtime, reverse=True)
    return candidates[0] if candidates else None


def inject_demand_into_template(demand_df, model_df, dma, makes, metric, template_path, data_date, stock_types=None):
    """Build the v2 demand chart HTML by injecting data into the template."""
    makes_label = ', '.join(makes) if makes else 'All Makes'
    stock_label = ', '.join(stock_types) if stock_types else 'All Stock Types'
    metric_col = _DEMAND_METRIC_COL.get(metric, 'market_vdps')
    metric_label = _DEMAND_METRIC_LABEL.get(metric, 'Market VDPs')

    # Build make-level demand array
    demand_data = []
    for _, row in demand_df.iterrows():
        demand_data.append({
            'make': str(row.get('make', '')),
            'vdps': int(row.get('market_vdps', 0)),
            'connections': int(row.get('market_connections', 0)),
            'vehicles': int(row.get('market_vehicles', 0)),
            'pct': float(row.get('pct', 0)),
        })

    # Build model drill-down dict {make: [model rows]}
    model_data = {}
    for _, row in model_df.iterrows():
        make = str(row.get('make', ''))
        model = str(row.get('model', ''))
        stock = str(row.get('stock_type', 'All'))
        if make not in model_data:
            model_data[make] = []
        model_data[make].append({
            'model': model,
            'stock_type': stock,
            'vdps': int(row.get('market_vdps', 0)),
            'connections': int(row.get('market_connections', 0)),
            'vehicles': int(row.get('market_vehicles', 0)),
        })

    demand_config = {
        'mode': 'demand',
        'metric': metric,
        'metricLabel': metric_label,
        'dma': dma,
        'makes': makes,
        'makesLabel': makes_label,
        'stockLabel': stock_label,
        'period': data_date,
        'totalVdps': int(demand_df['market_vdps'].sum()) if 'market_vdps' in demand_df.columns else 0,
        'totalConnections': int(demand_df['market_connections'].sum()) if 'market_connections' in demand_df.columns else 0,
    }

    js_demand = f"const demandData = {json.dumps(demand_data, indent=2)};"
    js_model  = f"const modelData = {json.dumps(model_data, indent=2)};"
    js_config = f"const demandConfig = {json.dumps(demand_config, indent=2)};"

    html = template_path.read_text(encoding='utf-8')
    for placeholder, replacement in [
        ('// %%DEMAND_DATA%%',   js_demand),
        ('// %%MODEL_DATA%%',    js_model),
        ('// %%DEMAND_CONFIG%%', js_config),
        ('// %%CITY_DATA%%',     'const cities = [];\nconst mapConfig = {center: [39.5, -98.35], zoom: 4};'),
        ('// %%ZIP_DATA%%',      'const zipData = [];'),
        ('// %%HITLIST_ZIPS%%',  'const hitlistZips = [];'),
        ('// %%DEALER_PIN%%',    'const dealerPin = {};'),
    ]:
        html = html.replace(placeholder, replacement)

    html = html.replace('%%PAGE_TITLE%%',   f"{dma} Demand — Cars.com")
    html = html.replace('%%REPORT_TITLE%%', f"Market Demand · {dma}" + (f" | {makes_label}" if makes else ""))
    html = html.replace('%%DATA_DATE%%',    data_date)
    return html


# ── ZIP → City Mapping ────────────────────────────────────────────────────────

def map_zips_to_cities(df, zip_col, search_col):
    """
    Map all ZIP codes in the dataframe to cities via pgeocode.
    Aggregates search volumes by city.
    Returns DataFrame: city, searches, lat, lon, state
    """
    nomi = pgeocode.Nominatim("us")
    rows = []

    for _, row in df.iterrows():
        zip_code = str(row[zip_col]).zfill(5)
        try:
            searches = float(str(row[search_col]).replace(",", "").replace("%", ""))
        except (ValueError, TypeError):
            continue

        info = nomi.query_postal_code(zip_code)
        if pd.isna(info.place_name) or pd.isna(info.latitude):
            continue

        rows.append({
            "city":     info.place_name,
            "lat":      info.latitude,
            "lon":      info.longitude,
            "searches": searches,
            "state":    info.state_code,
            "zip_code": zip_code,
        })

    if not rows:
        return pd.DataFrame()

    df_raw = pd.DataFrame(rows)
    df_agg = (
        df_raw.groupby("city")
        .agg(
            searches=("searches", "sum"),
            lat=("lat", "median"),
            lon=("lon", "median"),
            state=("state", "first"),
            zips=("zip_code", lambda x: ", ".join(sorted(x.unique()))),
        )
        .reset_index()
        .sort_values("searches", ascending=False)
    )
    return df_agg


def compute_map_center(df_cities, zoom=8):
    """Compute weighted centroid from top 10 cities by search volume."""
    top = df_cities.head(10)
    weights = top["searches"]
    lat = (top["lat"] * weights).sum() / weights.sum()
    lon = (top["lon"] * weights).sum() / weights.sum()
    return [round(float(lat), 4), round(float(lon), 4)], zoom

# ── HTML Injection ────────────────────────────────────────────────────────────

def build_report_title(dma, makes):
    """Build human-readable title for the report header."""
    makes_label = " | " + " · ".join(makes) if makes else ""
    return f"{dma} Market Intelligence{makes_label}"


def inject_into_template(df_cities, dma, makes, template_path, data_date="",
                         zip_rows=None, hitlist_zips=None, dealer_pin=None):
    city_data = [
        {
            "name":  row["city"],
            "total": int(row["searches"]),
            "lat":   round(float(row["lat"]), 5),
            "lng":   round(float(row["lon"]), 5),
            "zips":  row.get("zips", ""),
        }
        for _, row in df_cities.iterrows()
    ]

    center, zoom = compute_map_center(df_cities)
    report_title = build_report_title(dma, makes)
    page_title   = f"{dma} Search Volume — Cars.com"

    js_block = (
        f"const cities = {json.dumps(city_data, indent=2)};\n"
        f"const mapConfig = {{center: {center}, zoom: {zoom}}};"
    )

    # ZIP-level data for toggle view
    zip_block = "const zipData = [];"
    if zip_rows:
        zip_block = f"const zipData = {json.dumps(zip_rows, indent=2)};"

    # Hitlist ZIPs
    hl_block = "const hitlistZips = [];"
    if hitlist_zips:
        hl_block = f"const hitlistZips = {json.dumps(hitlist_zips)};"

    # Dealer pin
    dp_block = "const dealerPin = {};"
    if dealer_pin:
        dp_block = f"const dealerPin = {json.dumps(dealer_pin)};"

    html = template_path.read_text(encoding="utf-8")

    if "// %%CITY_DATA%%" not in html:
        raise ValueError("Template missing '// %%CITY_DATA%%' placeholder.")

    html = html.replace("// %%CITY_DATA%%", js_block)
    html = html.replace("// %%ZIP_DATA%%", zip_block)
    html = html.replace("// %%HITLIST_ZIPS%%", hl_block)
    html = html.replace("// %%DEALER_PIN%%", dp_block)
    # Stub out demand placeholders so search-mode HTML has no unresolved comments
    html = html.replace("// %%DEMAND_DATA%%",   "const demandData = [];")
    html = html.replace("// %%MODEL_DATA%%",    "const modelData = {};")
    html = html.replace("// %%DEMAND_CONFIG%%", "const demandConfig = {mode: 'search'};")
    html = html.replace("%%PAGE_TITLE%%", page_title)
    html = html.replace("%%REPORT_TITLE%%", report_title)
    html = html.replace("%%DATA_DATE%%", data_date)
    return html

# ── Main ──────────────────────────────────────────────────────────────────────

def slugify(text):
    return re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_")


def main():
    parser = argparse.ArgumentParser(description="Generate Market Intelligence HTML report.")
    parser.add_argument("--dma",   help="Tableau DMA name (e.g. 'Norfolk-Portsmth-Newpt Nws')")
    parser.add_argument("--makes", help="Comma-separated makes to filter, or 'All'")
    parser.add_argument("--force-tableau", action="store_true",
                        help="Skip manual CSV fallback; always pull fresh data from Tableau API")
    parser.add_argument("--quarters", type=int, default=None,
                        help="Use only the most recent N quarters (e.g. --quarters 4 for trailing year)")
    parser.add_argument("--config", help="YAML config file for batch runs (overrides --dma/--makes)")
    parser.add_argument("--csv", help="Path to a specific CSV file (overrides auto-lookup)")
    parser.add_argument("--hitlist", help="Comma-separated hitlist ZIP codes (e.g. '32514,32563,32533')")
    parser.add_argument("--dealer-name", help="Dealer name for map pin")
    parser.add_argument("--dealer-address", help="Dealer address for map pin geocoding")
    parser.add_argument("--mode", default="demand", choices=["demand", "search"],
                        help="'demand' = VDP/Lead market chart (default); 'search' = legacy ZIP search-volume map")
    parser.add_argument("--metric", default="vdp", choices=["vdp", "connections", "vehicles"],
                        help="Primary metric for demand mode: vdp (default), connections, or vehicles")
    parser.add_argument("--stock-types", default=None,
                        help="Comma-separated stock types to filter: New, Used, CPO (default: all)")
    args = parser.parse_args()

    if args.config:
        run_config(args.config, args)
        return

    if args.mode == 'demand' and not args.makes:
        args.makes = 'All'
    dma, makes_str = prompt_inputs(args)
    makes = parse_makes(makes_str)

    today      = datetime.now().strftime("%m.%d.%y")
    dma_slug   = slugify(dma)
    output_dir = REPORTS_BASE / dma_slug
    output_dir.mkdir(parents=True, exist_ok=True)

    makes_slug   = ("_" + "_".join(makes)) if makes else ""
    stock_types  = [s.strip() for s in args.stock_types.split(",")] if args.stock_types else None

    if args.mode == 'demand':
        output_path = output_dir / f"market_demand_{dma_slug}{makes_slug}_{today}.html"
    else:
        output_path = output_dir / f"market_intelligence_{dma_slug}{makes_slug}_{today}.html"

    makes_label = ", ".join(makes) if makes else "All makes"
    print(f"\nGenerating report:")
    print(f"  Mode:  {args.mode} ({'VDP/Lead demand chart' if args.mode == 'demand' else 'Search volume map (legacy)'})")
    print(f"  DMA:   {dma}")
    print(f"  Makes: {makes_label}")
    print(f"  Output: {output_path}\n")

    # ── Demand mode (v2) ──────────────────────────────────────────────────────
    if args.mode == 'demand':
        csv_path = None
        if args.csv:
            csv_path = Path(args.csv).expanduser()
            if not csv_path.exists():
                print(f"CSV not found: {csv_path}")
                sys.exit(1)
        else:
            csv_path_str = _find_demand_csv(dma, makes)
            if csv_path_str:
                csv_path = Path(csv_path_str)
                print(f"Auto-detected demand signals CSV: {csv_path.name}")
            else:
                print(f"No demand signals CSV found in {TABLEAU_DIR}.")
                print(f"Download Market Comparison from admin.cars.com/dealers/{{UUID}}/reports/demand_signals")
                print(f"and pass it with --csv <path>")
                sys.exit(1)

        print(f"Loading demand signals data…")
        df = load_demand_signals_csv(csv_path, makes=makes if makes else None, stock_types=stock_types)
        if df.empty:
            print("No rows after filtering. Check make/stock-type filters or CSV format.")
            sys.exit(1)

        dma_name = df['dma'].iloc[0] if 'dma' in df.columns else dma
        data_date = datetime.now().strftime("%b %Y")
        print(f"  Rows: {len(df)} | DMA: {dma_name}")
        if makes:
            print(f"  Make filter applied — {len(df['make'].unique())} make(s) loaded")

        demand_df = aggregate_dma_demand(df, metric=args.metric, group_by='make')
        model_df  = aggregate_dma_demand(df, metric=args.metric, group_by='make_model')
        print(f"  {len(demand_df)} makes | metric: {_DEMAND_METRIC_LABEL[args.metric]}")

        if not TEMPLATE_PATH.exists():
            print(f"Template not found: {TEMPLATE_PATH}")
            sys.exit(1)

        final_html = inject_demand_into_template(
            demand_df, model_df, dma_name, makes, args.metric,
            TEMPLATE_PATH, data_date, stock_types=stock_types
        )
        output_path.write_text(final_html, encoding='utf-8')
        print(f"\n✓ Demand report saved: {output_path}")

        build_index = REPORTS_BASE / "build_index.py"
        if build_index.exists():
            import subprocess
            print("Rebuilding index.html...")
            subprocess.run([sys.executable, str(build_index), str(REPORTS_BASE)], check=False)
        return

    # ── Search mode (v1 legacy) ───────────────────────────────────────────────
    if makes:
        print(f"WARNING: make filter '{', '.join(makes)}' is cosmetic only.")
        print(f"         Tableau ZIP view 39464986 returns all-make data — vf_make is silently ignored.")
        print(f"         Report will be labeled '{', '.join(makes)}' but contains all makes.\n")

    # ── Step 1: Get CSV data ──────────────────────────────────────────────────
    # Lookup order: --csv flag > SearchVolume_{DMA}_{Make}.csv > generic > Tableau API
    csv_text = None
    csv_source = None
    specific_csv = TABLEAU_DIR / f"SearchVolume_{dma_slug}{makes_slug}.csv"
    generic_csv  = TABLEAU_DIR / "SearchVolumeByZipCode.csv"

    if args.csv:
        csv_path = Path(args.csv).expanduser()
        if not csv_path.exists():
            print(f"⚠  CSV not found: {csv_path}")
            sys.exit(1)
        print(f"Reading CSV (explicit): {csv_path}")
        csv_text = csv_path.read_bytes()
        csv_source = csv_path
    elif specific_csv.exists() and not args.force_tableau:
        print(f"Reading CSV (DMA/make-specific): {specific_csv}")
        csv_text = specific_csv.read_bytes()
        csv_source = specific_csv
    elif generic_csv.exists() and not args.force_tableau:
        print(f"Reading CSV (generic): {generic_csv}")
        csv_text = generic_csv.read_bytes()
        csv_source = generic_csv
        # Preserve a copy with the specific name so it's not overwritten
        shutil.copy2(generic_csv, specific_csv)
        print(f"  → Saved as: {specific_csv.name}")
    else:
        print("Authenticating to Tableau...")
        try:
            token, site_id = tableau_signin()
        except Exception as e:
            print(f"Tableau auth failed: {e}")
            sys.exit(1)

        try:
            print(f"Downloading view data...")
            if makes:
                _qc_filter_check(token, site_id, dma, makes)
            csv_text = download_view_csv(token, site_id, dma)
        finally:
            tableau_signout(token)

    # ── Step 2: Parse & validate ──────────────────────────────────────────────
    df = parse_csv(csv_text)
    df = aggregate_quarter_cols(df, quarters=args.quarters)

    # Determine data period range from quarterly columns for "Data as of" stamp
    quarter_cols_found = [c for c in df.columns if re.match(r'^\d{4}\s+Q\d$', str(c).strip())]
    if quarter_cols_found:
        earliest_q = min(quarter_cols_found).strip()  # e.g. "2023 Q4"
        latest_q = max(quarter_cols_found).strip()    # e.g. "2026 Q1"
        e_parts = earliest_q.split()
        l_parts = latest_q.split()
        data_date = f"{e_parts[1]} {e_parts[0]} \u2013 {l_parts[1]} {l_parts[0]}"  # "Q4 2023 – Q1 2026"
        _qc_quarter_coverage(df, quarter_cols_found)
    else:
        data_date = datetime.now().strftime("%b %Y")

    print(f"Columns: {list(df.columns)}")
    print(f"Rows:    {len(df)}")

    if detect_sheet_type(df) == "pct_change":
        print(
            "\n⚠  Got '% Change' data, not raw search counts.\n"
            "   In Tableau: open 'Searches by Zip Code' view → Download → Crosstab\n"
            f"  → select 'Search Volume by Zip Code' → CSV → Download\n"
            f"   Save as: {manual_csv}\n"
            "   Then re-run.\n"
        )
        sys.exit(1)

    # ── Step 3: Identify & filter columns ────────────────────────────────────
    cols = df.columns.tolist()
    zip_col    = next((c for c in cols if "zip" in c.lower()), None)
    search_col = next((c for c in cols if c == "searches_avg_per_q"), None) or \
                 next((c for c in cols if c == "searches"), None) or \
                 next((c for c in cols if "search" in c.lower() and "%" not in c.lower()), None)
    make_col   = next((c for c in cols if c.lower() == "make"), None)

    if not zip_col or not search_col:
        print(f"Could not find required columns. Available: {cols}")
        sys.exit(1)

    # Filter by DMA if column present
    dma_col = next((c for c in cols if "dma" in c.lower()), None)
    if dma_col:
        before = len(df)
        df = df[df[dma_col].str.contains(dma, na=False, case=False, regex=False)]
        print(f"DMA filter: {before} → {len(df)} rows")

    # Filter by make(s) if specified and column present
    if makes and make_col:
        before = len(df)
        df = df[df[make_col].str.lower().isin([m.lower() for m in makes])]
        print(f"Make filter ({', '.join(makes)}): {before} → {len(df)} rows")
    elif makes and not make_col:
        print(f"ℹ  Make '{', '.join(makes)}' is label only — this view has no make column (vf_make filter silently ignored).")

    if df.empty:
        print("No data after filtering. Check DMA name or make filter.")
        sys.exit(1)

    # ── Step 4: ZIP → city mapping ────────────────────────────────────────────
    # Capture ZIP-level data before city aggregation
    nomi = pgeocode.Nominatim("us")
    zip_rows = []
    for _, row in df.iterrows():
        z = str(row[zip_col]).zfill(5)
        try:
            searches = float(str(row[search_col]).replace(",", "").replace("%", ""))
        except (ValueError, TypeError):
            continue
        if pd.isna(searches):
            continue
        info = nomi.query_postal_code(z)
        if pd.isna(info.place_name) or pd.isna(info.latitude):
            continue
        zip_rows.append({
            "zip": z, "total": int(searches),
            "lat": round(float(info.latitude), 5),
            "lng": round(float(info.longitude), 5),
            "city": info.place_name, "state": info.state_code or "",
        })
    zip_rows.sort(key=lambda x: x["total"], reverse=True)

    print("Mapping ZIPs to cities...")
    df_cities = map_zips_to_cities(df, zip_col, search_col)

    if df_cities.empty:
        print("No cities found after ZIP mapping.")
        sys.exit(1)

    total = int(df_cities["searches"].sum())
    print(f"\nTop cities ({len(df_cities)} total, {total:,} total searches):")
    print(df_cities.head(10).to_string(index=False))

    # ── Step 5: Generate HTML ─────────────────────────────────────────────────
    if not TEMPLATE_PATH.exists():
        print(f"\n⚠  Template not found at {TEMPLATE_PATH}")
        sys.exit(1)

    # Parse hitlist and dealer pin from args
    hitlist_zips = [z.strip() for z in args.hitlist.split(",")] if args.hitlist else None
    dealer_pin = None
    if args.dealer_name:
        dealer_pin = {"name": args.dealer_name, "address": args.dealer_address or "", "lat": 0, "lng": 0}

    print("\nInjecting data into template...")
    try:
        final_html = inject_into_template(
            df_cities, dma, makes, TEMPLATE_PATH, data_date,
            zip_rows=zip_rows,
            hitlist_zips=hitlist_zips,
            dealer_pin=dealer_pin,
        )
    except ValueError as e:
        print(f"\n⚠  {e}")
        sys.exit(1)

    output_path.write_text(final_html, encoding="utf-8")
    print(f"\n✓ Report saved: {output_path}")
    print("  Open in any browser — fully standalone.")

    # ── Auto-rebuild index.html ──────────────────────────────────────────────
    build_index = REPORTS_BASE / "build_index.py"
    if build_index.exists():
        import subprocess
        print("\nRebuilding index.html...")
        subprocess.run([sys.executable, str(build_index), str(REPORTS_BASE)], check=False)


def run_config(config_path, args):
    """Run batch reports from a YAML config file."""
    try:
        import yaml
    except ImportError:
        print("pip install pyyaml to use --config")
        sys.exit(1)

    with open(config_path) as f:
        config = yaml.safe_load(f)

    for entry in config.get("reports", []):
        dma = entry["dma"]
        makes_str = entry.get("makes", "All")
        makes = parse_makes(makes_str)
        quarters = entry.get("quarters", args.quarters)

        today = datetime.now().strftime("%m.%d.%y")
        dma_slug = slugify(dma)
        output_dir = REPORTS_BASE / dma_slug
        output_dir.mkdir(parents=True, exist_ok=True)

        makes_slug = ("_" + "_".join(makes)) if makes else ""
        output_path = output_dir / f"market_intelligence_{dma_slug}{makes_slug}_{today}.html"

        makes_label = ", ".join(makes) if makes else "All makes"
        print(f"\n{'='*60}")
        print(f"  DMA:   {dma}")
        print(f"  Makes: {makes_label}")
        print(f"  Output: {output_path}\n")

        csv_text = None
        specific_csv = TABLEAU_DIR / f"SearchVolume_{dma_slug}{makes_slug}.csv"
        generic_csv  = TABLEAU_DIR / "SearchVolumeByZipCode.csv"

        if specific_csv.exists() and not args.force_tableau:
            print(f"  Reading CSV (DMA/make-specific): {specific_csv.name}")
            csv_text = specific_csv.read_bytes()
        elif generic_csv.exists() and not args.force_tableau:
            print(f"  Reading CSV (generic): {generic_csv.name}")
            csv_text = generic_csv.read_bytes()
            shutil.copy2(generic_csv, specific_csv)
            print(f"  → Saved as: {specific_csv.name}")
        else:
            try:
                token, site_id = tableau_signin()
                if makes:
                    _qc_filter_check(token, site_id, dma, makes)
                csv_text = download_view_csv(token, site_id, dma)
                tableau_signout(token)
            except Exception as e:
                print(f"Tableau failed for {dma}: {e}")
                continue

        df = parse_csv(csv_text)
        df = aggregate_quarter_cols(df, quarters=quarters)

        quarter_cols_found = [c for c in df.columns if re.match(r'^\d{4}\s+Q\d$', str(c).strip())]
        if quarter_cols_found:
            earliest_q = min(quarter_cols_found).strip()
            latest_q = max(quarter_cols_found).strip()
            e_parts = earliest_q.split()
            l_parts = latest_q.split()
            data_date = f"{e_parts[1]} {e_parts[0]} \u2013 {l_parts[1]} {l_parts[0]}"
            _qc_quarter_coverage(df, quarter_cols_found)
        else:
            data_date = datetime.now().strftime("%b %Y")

        zip_col = next((c for c in df.columns if "zip" in c.lower()), None)
        search_col = next((c for c in df.columns if c == "searches_avg_per_q"), None) or \
                     next((c for c in df.columns if c == "searches"), None)
        dma_col = next((c for c in df.columns if "dma" in c.lower()), None)
        if dma_col:
            df = df[df[dma_col].str.contains(dma, na=False, case=False, regex=False)]

        make_col = next((c for c in df.columns if c.lower() == "make"), None)
        if makes and make_col:
            df = df[df[make_col].str.lower().isin([m.lower() for m in makes])]

        if df.empty:
            print(f"No data for {dma}")
            continue

        df_cities = map_zips_to_cities(df, zip_col, search_col)
        final_html = inject_into_template(df_cities, dma, makes, TEMPLATE_PATH, data_date)
        output_path.write_text(final_html, encoding="utf-8")
        print(f"✓ Report saved: {output_path}")

    # Rebuild index after all reports
    build_index_script = REPORTS_BASE / "build_index.py"
    if build_index_script.exists():
        import subprocess
        print("\nRebuilding index.html...")
        subprocess.run([sys.executable, str(build_index_script), str(REPORTS_BASE)], check=False)


if __name__ == "__main__":
    main()
