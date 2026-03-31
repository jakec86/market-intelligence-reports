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
import argparse
import requests
import pandas as pd
import pgeocode
from io import StringIO
from datetime import datetime
from pathlib import Path

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

def download_view_csv(token, site_id, dma, makes):
    url = f"{TABLEAU_SERVER}/api/3.21/sites/{site_id}/views/{VIEW_ID}/data"
    params = {"vf_dma_market_name": dma, "maxAge": 1}
    if makes:
        params["vf_make"] = ",".join(makes)
    r = requests.get(url, headers={"x-tableau-auth": token}, params=params)
    r.raise_for_status()
    return r.text


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


def aggregate_quarter_cols(df):
    """
    If the dataframe has quarterly columns (e.g. '2023 Q4', '2024 Q1'),
    sum them into a single 'searches' column and return updated df.
    """
    quarter_cols = [c for c in df.columns if re.match(r'^\d{4}\s+Q\d$', str(c).strip())]
    if not quarter_cols:
        return df
    for c in quarter_cols:
        df[c] = pd.to_numeric(df[c].astype(str).str.replace(',', ''), errors='coerce')
    df['searches'] = df[quarter_cols].sum(axis=1, min_count=1)
    print(f"Quarterly columns summed → 'searches': {quarter_cols}")
    return df


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


def inject_into_template(df_cities, dma, makes, template_path, data_date=""):
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

    html = template_path.read_text(encoding="utf-8")

    if "// %%CITY_DATA%%" not in html:
        raise ValueError("Template missing '// %%CITY_DATA%%' placeholder.")

    html = html.replace("// %%CITY_DATA%%", js_block)
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
    args = parser.parse_args()

    dma, makes_str = prompt_inputs(args)
    makes = parse_makes(makes_str)

    today      = datetime.now().strftime("%m.%d.%y")
    dma_slug   = slugify(dma)
    output_dir = REPORTS_BASE / dma_slug
    output_dir.mkdir(parents=True, exist_ok=True)

    makes_slug   = ("_" + "_".join(makes)) if makes else ""
    output_path  = output_dir / f"market_intelligence_{dma_slug}{makes_slug}_{today}.html"

    makes_label = ", ".join(makes) if makes else "All makes"
    print(f"\nGenerating report:")
    print(f"  DMA:   {dma}")
    print(f"  Makes: {makes_label}")
    print(f"  Output: {output_path}\n")

    # ── Step 1: Get CSV data ──────────────────────────────────────────────────
    csv_text = None
    manual_csv = TABLEAU_DIR / "SearchVolumeByZipCode.csv"

    if manual_csv.exists() and not args.force_tableau:
        print(f"Reading manually-downloaded CSV: {manual_csv}")
        csv_text = manual_csv.read_bytes()
    else:
        print("Authenticating to Tableau...")
        try:
            token, site_id = tableau_signin()
        except Exception as e:
            print(f"Tableau auth failed: {e}")
            sys.exit(1)

        try:
            print(f"Downloading view data...")
            csv_text = download_view_csv(token, site_id, dma, makes)
        finally:
            tableau_signout(token)

    # ── Step 2: Parse & validate ──────────────────────────────────────────────
    df = parse_csv(csv_text)
    df = aggregate_quarter_cols(df)

    # Determine latest data period from quarterly columns for "Data as of" stamp
    quarter_cols_found = [c for c in df.columns if re.match(r'^\d{4}\s+Q\d$', str(c).strip())]
    if quarter_cols_found:
        latest_q = max(quarter_cols_found).strip()   # e.g. "2026 Q1"
        parts = latest_q.split()
        data_date = f"{parts[1]} {parts[0]}"         # → "Q1 2026"
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
    search_col = next((c for c in cols if c == "searches"), None) or \
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
        print(f"ℹ  Make '{', '.join(makes)}' applied as label only — data is already filtered by make in Tableau.")

    if df.empty:
        print("No data after filtering. Check DMA name or make filter.")
        sys.exit(1)

    # ── Step 4: ZIP → city mapping ────────────────────────────────────────────
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

    print("\nInjecting data into template...")
    try:
        final_html = inject_into_template(df_cities, dma, makes, TEMPLATE_PATH, data_date)
    except ValueError as e:
        print(f"\n⚠  {e}")
        sys.exit(1)

    output_path.write_text(final_html, encoding="utf-8")
    print(f"\n✓ Report saved: {output_path}")
    print("  Open in any browser — fully standalone.")


if __name__ == "__main__":
    main()
