#!/usr/bin/env python3
"""
Dealer Market Analysis Report (generalized from jlr_swh_market_report.py)

Combines Cars.com data (LEI, market share, price comparison) with
a CarGurus 90-day dashboard to produce a side-by-side market analysis
for any dealer/franchise.

Per-dealer specifics (franchise makes, comp-set, store name merges, period
labels, and the hand-curated Performance Trends quarter numbers) live in a
PROFILE — either one of the built-in PROFILES below, or a JSON file passed
via --profile-json for a dealer that doesn't have one yet.

Usage:
    python3 dealer_market_report.py \\
      --profile jlr_swh \\
      --lei ~/Downloads/"Low Engaged Inventory Report - Houston.6.8.26.csv" \\
      --market-share ~/Downloads/"JLR SWH Market Share Comp.csv" \\
      --price-comp ~/Downloads/"JLR SWH Price Comparison.csv" \\
      --cargurus ~/Downloads/"JLR_SWHouston_Dashboard (1).html" \\
      [--dealer "Southwest"] \\
      [--send]

For a dealer with no built-in profile yet:
    python3 dealer_market_report.py --profile-json ~/Documents/scripts/profiles/my_dealer.json ...
"""

import argparse
import base64
import json
import os
import re
import sys
from collections import Counter
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from io import StringIO
from pathlib import Path
from urllib.parse import quote

import pandas as pd
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False

# ── Config ────────────────────────────────────────────────────────────────────

TOKEN_GMAIL    = Path.home() / ".claude" / "tokens" / "gmail_jcrawley.json"
CLIENT_SECRETS = Path.home() / "gcp-oauth.keys.json"
SCOPES_GMAIL   = ["https://www.googleapis.com/auth/gmail.compose",
                  "https://www.googleapis.com/auth/gmail.modify"]

PURPLE  = "#6B2D8B"
TEAL    = "#00A88E"

# Default like-tier luxury comp set, used when a profile doesn't override it.
_DEFAULT_COMP_BRANDS = {
    'land rover', 'jaguar', 'porsche', 'mercedes-benz', 'mercedes', 'bmw',
    'lexus', 'audi', 'cadillac', 'maserati', 'bentley', 'ferrari',
    'lamborghini', 'rolls-royce', 'aston martin',
}

_REQUIRED_PROFILE_DEFAULTS = {
    'dealer_display': None,               # required — set per profile
    'dealer_match_hints': [],              # list of {'contains_all': [...]} tried in order
    'franchise_makes': set(),              # makes considered "this dealer's franchise"
    'franchise_model_hints': [],           # extra model-name substrings that imply a franchise
                                            # make even when the make itself isn't in the YMMT
                                            # string (e.g. "Range Rover" implying Land Rover)
    'franchise_short_label': None,         # e.g. "JLR" — falls back to dealer_display
    'nav_short_label': None,               # sticky-nav store label, e.g. "JLR SW Houston" — falls back to franchise_short_label
    'franchise_name_pattern': None,        # regex identifying franchise dealers by name in market_df
    'comp_brands': _DEFAULT_COMP_BRANDS,
    'combine_stores': [],                  # [{'a': ..., 'b': ..., 'combined_name': ...}]
    'market_area': '',                     # e.g. "Houston"
    'aging_threshold_days': 60,
    'franchise_avg_days_benchmark': 70,
    'output_dir_name': None,               # falls back to a slug of dealer_display
    'perf_csv_dealer_hint': None,          # substring to match 'Dealer Name' rows in the perf CSV;
                                            # falls back to the matched LEI dealer_name if unset
    'sheet_url': None,
    'period_label': None,                  # e.g. "March–May 2026" — required for perf sections
    'quarter_label': '',                   # e.g. "Q2 2026"
    'month_labels': [],                    # e.g. ["March", "April", "May"]
    'perf_trends': None,                   # hand-curated Performance Trends numbers for the period
    'cargurus_fallback_deal_ratings': None,
}

# Built-in profiles for dealers we run this report for regularly.
PROFILES = {
    "jlr_swh": {
        'dealer_display': "Land Rover Southwest Houston",
        'dealer_match_hints': [
            {'contains_all': ['land rover', 'southwest']},
            {'contains_all': ['land rover', 'houston']},
            {'contains_all': ['southwest', 'houston']},
        ],
        'franchise_makes': {'land rover', 'jaguar'},
        'franchise_model_hints': ['range rover'],
        'franchise_short_label': 'JLR',
        'nav_short_label': 'JLR SW Houston',
        'franchise_name_pattern': r'land rover|jaguar',
        'combine_stores': [
            {'a': 'jaguar houston central', 'b': 'land rover houston central',
             'combined_name': 'Jaguar Land Rover Houston Central'},
        ],
        'market_area': 'Houston',
        'output_dir_name': 'LandRoverSWHouston',
        'perf_csv_dealer_hint': 'Southwest Houston',
        'sheet_url': 'https://docs.google.com/spreadsheets/d/1JxpuPsusYKoavvT-xet0wd75nLYbawxGD5ZKOWCiRyo/edit?gid=565895707#gid=565895707',
        'period_label': 'March–May 2026',
        'quarter_label': 'Q2 2026',
        'month_labels': ['March', 'April', 'May'],
        'perf_trends': {
            'vdps_q2': 30952,
            'vdp_monthly': {'march': 10218, 'april': 10642, 'may': 10092},
            'conns_q2': 930,
            'conns_excl_instant': 886,
            'instant_offer': 44,
            'conn_monthly': {'march': 247, 'april': 323, 'may': 360},
            'conn_by_source': {
                'VDP Deep Link': 453, 'Email': 185, 'Web Transfer': 116,
                'Phone': 75, 'Maps': 53, 'Chat': 4,
            },
            'conn_monthly_by_type': {
                'March': {'Email': 53, 'Phone': 16, 'Chat': 1, 'Web Transfer': 33, 'VDP Deep Link': 116, 'Maps': 11, 'Total': 230},
                'April': {'Email': 54, 'Phone': 19, 'Chat': 1, 'Web Transfer': 45, 'VDP Deep Link': 167, 'Maps': 21, 'Total': 307},
                'May':   {'Email': 78, 'Phone': 40, 'Chat': 2, 'Web Transfer': 38, 'VDP Deep Link': 170, 'Maps': 21, 'Total': 349},
                'Total': {'Email': 185, 'Phone': 75, 'Chat': 4, 'Web Transfer': 116, 'VDP Deep Link': 453, 'Maps': 53, 'Total': 886},
            },
        },
    },
}


def load_profile(name=None, json_path=None):
    """Resolve a profile dict from a built-in name or a JSON file, filled out with defaults."""
    if json_path:
        with open(os.path.expanduser(json_path)) as f:
            raw = json.load(f)
    elif name:
        if name not in PROFILES:
            print(f"  ✗ Unknown profile '{name}'. Available: {', '.join(PROFILES)}")
            print("  Use --profile-json to supply a profile for a new dealer.")
            sys.exit(1)
        raw = PROFILES[name]
    else:
        print("  ✗ Must supply --profile <name> or --profile-json <path>.")
        print(f"  Available profiles: {', '.join(PROFILES)}")
        sys.exit(1)

    profile = dict(_REQUIRED_PROFILE_DEFAULTS)
    profile.update(raw)
    if not profile['dealer_display']:
        print("  ✗ Profile missing required 'dealer_display'.")
        sys.exit(1)
    profile['franchise_makes'] = {m.lower() for m in profile['franchise_makes']}
    profile['comp_brands'] = {b.lower() for b in profile['comp_brands']}
    if not profile['franchise_short_label']:
        profile['franchise_short_label'] = profile['dealer_display']
    if not profile['nav_short_label']:
        profile['nav_short_label'] = profile['franchise_short_label']
    if not profile['output_dir_name']:
        profile['output_dir_name'] = _slugify(profile['dealer_display'])
    return profile


def _slugify(name):
    return re.sub(r'[^a-z0-9]+', '', name.lower())

# ── Parsing ───────────────────────────────────────────────────────────────────

def _read_utf16_tsv(path):
    """Read UTF-16 LE or UTF-8 tab-separated CSV into a DataFrame."""
    with open(path, 'rb') as f:
        raw = f.read()
    text = raw.decode('utf-16') if raw[:2] in (b'\xff\xfe', b'\xfe\xff') else raw.decode('utf-8', errors='replace')
    df = pd.read_csv(StringIO(text), sep='\t', dtype=str)
    df.columns = [str(c).strip() for c in df.columns]
    return df


def load_lei(path, profile, dealer_hint=None):
    """
    Load market LEI (all dealers). Auto-detect the profile's dealer rows.
    Returns (dealer_df, market_df, matched_dealer_name).
    """
    print(f"  Loading LEI: {Path(path).name}")
    df = _read_utf16_tsv(path)
    print(f"  LEI: {len(df):,} rows, {len(df.columns)} columns")

    dealer_col = next((c for c in df.columns if 'dealer name' in c.lower()), None)
    if not dealer_col:
        print(f"  ✗ No 'Dealer name' column. Columns: {list(df.columns)[:5]}")
        sys.exit(1)

    all_names = df[dealer_col].dropna().unique()
    if dealer_hint:
        matches = [n for n in all_names if dealer_hint.lower() in n.lower()]
    else:
        matches = []
        for hint in profile['dealer_match_hints']:
            terms = hint['contains_all']
            matches = [n for n in all_names if all(t.lower() in n.lower() for t in terms)]
            if matches:
                break

    if not matches:
        franchise_hits = [n for n in all_names
                           if any(m in n.lower() for m in profile['franchise_makes'])] if profile['franchise_makes'] else []
        print(f"  ✗ '{profile['dealer_display']}' not found. Franchise-matching dealers in file: {franchise_hits}")
        print("  Use --dealer with a name substring to match manually.")
        sys.exit(1)
    if len(matches) > 1:
        print(f"  ✗ Multiple matches: {matches}. Use --dealer to narrow down.")
        sys.exit(1)

    dealer_name = matches[0]
    print(f"  ✓ Matched: '{dealer_name}'")

    dealer_df = df[df[dealer_col] == dealer_name].copy().reset_index(drop=True)
    market_df = df[df[dealer_col] != dealer_name].copy().reset_index(drop=True)
    print(f"  ✓ Dealer: {len(dealer_df):,} rows | Market: {len(market_df):,} rows")
    return dealer_df, market_df, dealer_name


def compute_lei_stats(dealer_df, market_df, profile, dealer_name, price_df=None):
    """Badge distribution, engagement, inventory table, and competitive context."""

    def _badge_dist(df):
        col = next((c for c in df.columns if c.strip().lower() == 'price badge'), None)
        if not col:
            return {}
        # Consolidate "Not Badged - Review Price" → "Not Badged"
        raw = df[col].dropna().str.strip().str.title()
        raw = raw.replace({'Not Badged - Review Price': 'Not Badged'})
        counts = Counter(raw)
        total = sum(counts.values()) or 1
        order = ['Great', 'Good', 'Fair', 'Not Badged']
        result = {}
        for k in order:
            v = counts.get(k, 0)
            if v > 0:
                result[k] = {'count': v, 'pct': round(v / total * 100, 1)}
        for k, v in counts.items():
            if k not in result and v > 0:
                result[k] = {'count': v, 'pct': round(v / total * 100, 1)}
        # Change 6: remove "Not Badged" from badge distribution chart
        result = {k: v for k, v in result.items() if 'not badged' not in k.lower()}
        return result

    def _to_num(series):
        return pd.to_numeric(series.astype(str).str.replace(',', '').str.replace('$', '').str.replace('%', ''), errors='coerce')

    def _col(df, substr):
        return next((c for c in df.columns if substr.lower() in c.lower()), None)

    vdp_col     = _col(dealer_df, 'vdps (07 days)')
    days_col    = _col(dealer_df, 'days live')
    photo_col   = _col(dealer_df, 'sum of photos')
    ymmt_col    = _col(dealer_df, 'ymmt')
    price_col   = _col(dealer_df, 'sum of price')
    mkt_pct_col = _col(dealer_df, '% of market avg price')
    badge_col   = _col(dealer_df, 'price badge')
    hot_col     = _col(dealer_df, 'hot badge')
    mkt_vdp_col = _col(dealer_df, 'market total vdp')
    leads_col   = _col(dealer_df, 'leads (07 days)')
    srp_col     = _col(dealer_df, 'srps (07 days)')

    # VDP share
    total_vdps = int(_to_num(dealer_df[vdp_col]).fillna(0).sum()) if vdp_col else 0
    total_srps  = int(_to_num(dealer_df[srp_col]).fillna(0).sum()) if srp_col else 0
    vdp_share_pct = 0.0
    if mkt_vdp_col and vdp_col:
        mkt = _to_num(dealer_df[mkt_vdp_col]).fillna(0).sum()
        if mkt > 0:
            vdp_share_pct = round(_to_num(dealer_df[vdp_col]).fillna(0).sum() / mkt * 100, 2)

    # Franchise Lead share: this dealer's leads vs all franchise stores (profile's franchise
    # makes, franchise dealer names only)
    franchise_lead_share = 'N/A'
    franchise_makes = profile['franchise_makes']
    franchise_pattern = profile['franchise_name_pattern']
    make_col_d = _col(dealer_df, 'make name')
    dealer_col_mkt = next((c for c in market_df.columns if 'dealer name' in c.lower()), None)
    make_col_mkt  = _col(market_df, 'make name')
    leads_col_mkt = _col(market_df, 'leads (07 days)')
    if franchise_makes and franchise_pattern and leads_col and make_col_d and dealer_col_mkt and make_col_mkt and leads_col_mkt:
        own_fran_mask   = dealer_df[make_col_d].str.lower().isin(franchise_makes)
        own_fran_leads  = _to_num(dealer_df[own_fran_mask][leads_col]).fillna(0).sum()
        mkt_fran_makes   = market_df[make_col_mkt].str.lower().isin(franchise_makes)
        mkt_fran_dealers = market_df[dealer_col_mkt].str.lower().str.contains(franchise_pattern, na=False)
        mkt_fran_leads   = _to_num(market_df[mkt_fran_makes & mkt_fran_dealers][leads_col_mkt]).fillna(0).sum()
        total_fran_leads = own_fran_leads + mkt_fran_leads
        if total_fran_leads > 0:
            franchise_lead_share = f"{round(own_fran_leads / total_fran_leads * 100):.0f}%"

    # Avg metrics
    avg_days    = round(_to_num(dealer_df[days_col]).mean(), 1) if days_col else 0
    avg_photos  = round(_to_num(dealer_df[photo_col]).mean(), 1) if photo_col else 0
    total_leads = int(_to_num(dealer_df[leads_col]).fillna(0).sum()) if leads_col else 0

    # Build stock# → {stock_type, price_drop_action} lookup from price_df
    pc_lookup = {}  # stock_num → {'stock_type': 'New'/'Used', 'action': '$X drop'}
    if price_df is not None:
        pc_stk  = next((c for c in price_df.columns if 'stock num' in c.lower()), None)
        pc_stype = next((c for c in price_df.columns if 'stock type' in c.lower()), None)
        pc_price = next((c for c in price_df.columns if c.strip().lower() == 'price'), None)
        pc_pct   = next((c for c in price_df.columns if 'price vs market' in c.lower()), None)
        if pc_stk:
            for _, pr in price_df.iterrows():
                stk = str(pr[pc_stk]).strip()
                stype = str(pr[pc_stype]).strip() if pc_stype else ''
                action = ''
                if pc_price and pc_pct:
                    try:
                        p    = float(str(pr[pc_price]).replace('$','').replace(',',''))
                        pct  = float(str(pr[pc_pct]).replace('%',''))
                        if pct > 105:
                            # Amount to drop to reach market avg (100%)
                            drop = p - (p / (pct / 100))
                            action = f"Drop ~${drop:,.0f}"
                    except (ValueError, TypeError):
                        pass
                pc_lookup[stk] = {'stock_type': stype, 'action': action}

    # Signal from mkt_pct: <95%=🟢, 95-105%=🟡, >105%=🔴
    def _signal(mkt_p):
        if mkt_p is None or pd.isna(mkt_p):
            return '—'
        if mkt_p < 95:
            return '🟢'
        if mkt_p <= 105:
            return '🟡'
        return '🔴'

    _signal_rank = {'🟢': 0, '🟡': 1, '🔴': 2, '—': 3}

    # Inventory table (deduplicated by VIN/stock)
    vin_col   = _col(dealer_df, 'vin')
    stock_col_lei = _col(dealer_df, 'stock num')
    seen = set()
    inventory = []
    for _, row in dealer_df.iterrows():
        stk_val   = str(row[stock_col_lei]).strip() if stock_col_lei else ''
        dedup_key = str(row[vin_col]).strip() if vin_col else stk_val
        if dedup_key in seen:
            continue
        seen.add(dedup_key)
        ymmt  = str(row[ymmt_col]).strip() if ymmt_col else ''
        if not ymmt or ymmt == 'nan':
            continue
        price = _to_num(pd.Series([row[price_col]])).iloc[0] if price_col else None
        mkt_p = _to_num(pd.Series([row[mkt_pct_col]])).iloc[0] if mkt_pct_col else None
        days  = _to_num(pd.Series([row[days_col]])).iloc[0] if days_col else 0
        vdps  = _to_num(pd.Series([row[vdp_col]])).iloc[0] if vdp_col else 0
        badge = str(row[badge_col]).strip() if badge_col else ''
        # Consolidate badge label
        if 'not badged' in badge.lower():
            badge = 'Not Badged'
        hot   = str(row[hot_col]).strip() if hot_col else ''
        pc_info = pc_lookup.get(stk_val, {})
        stype   = pc_info.get('stock_type', '')
        action  = pc_info.get('action', '')
        sig     = _signal(mkt_p)
        inventory.append({
            'ymmt':       ymmt,
            'stock_num':  stk_val,
            'stock_type': stype,
            'price':      f"${price:,.0f}" if price and not pd.isna(price) else '—',
            'mkt_pct':    f"{mkt_p:.0f}%" if mkt_p and not pd.isna(mkt_p) else '—',
            'days':       int(days) if days and not pd.isna(days) else 0,
            'vdps':       int(vdps) if vdps and not pd.isna(vdps) else 0,
            'badge':      badge if badge not in ('nan', '') else '—',
            'hot':        '🔥' if hot.lower() not in ('', 'nan', 'false', '0', 'no') else '',
            'signal':     sig,
            'action':     action,
        })

    # Sort: by days live descending (longest aging at top) — Change 8
    inventory.sort(key=lambda x: x['days'], reverse=True)

    # Good+Great+Fair = "badged" count (matching admin.cars.com definition)
    if badge_col:
        badged_mask = dealer_df[badge_col].str.strip().str.title().isin(['Good', 'Great', 'Fair'])
        good_great = int(badged_mask.sum())
    else:
        good_great = 0

    # Badge opportunity: vehicles within $1,000 of Good or Great badge
    diff_good_col  = _col(dealer_df, 'difference - good')
    diff_great_col = _col(dealer_df, 'difference - great')
    badge_opps = []
    if diff_good_col or diff_great_col:
        for item in inventory:
            stk = item['stock_num']
            stype = item.get('stock_type', '')
            # Skip new inventory — Cars.com does not apply price badges to new vehicles
            if stype.lower() == 'new':
                continue
            # Look up diffs from dealer_df by stock#
            stock_col_lei = _col(dealer_df, 'stock num')
            rows = dealer_df[dealer_df[stock_col_lei] == stk] if stock_col_lei else pd.DataFrame()
            if rows.empty:
                continue
            row = rows.iloc[0]
            dg  = _to_num(pd.Series([row[diff_good_col]])).iloc[0] if diff_good_col else None
            dgr = _to_num(pd.Series([row[diff_great_col]])).iloc[0] if diff_great_col else None
            cur_badge = str(row[badge_col]).strip().title() if badge_col else ''
            if 'not badged' in cur_badge.lower():
                cur_badge = 'Not Badged'

            opp = None
            # Skip "Not Badged" vehicles — not applicable (typically new inventory without badge)
            if cur_badge == 'Not Badged':
                continue
            # Within $1k of Great badge (best opportunity — already Good/Fair, upgrading)
            if dgr is not None and not pd.isna(dgr) and -1000 <= dgr < 0 and cur_badge != 'Great':
                opp = {'target': 'Great', 'diff': dgr}
            # Within $1k of Good badge (Fair badge upgrading to Good)
            elif dg is not None and not pd.isna(dg) and -1000 <= dg < 0 and cur_badge not in ('Good', 'Great'):
                opp = {'target': 'Good', 'diff': dg}

            if opp:
                drop = abs(opp['diff'])
                price_raw = item['price'].replace('$', '').replace(',', '')
                try:
                    price_val = float(price_raw)
                    target_price = f"${price_val - drop:,.0f}"
                except (ValueError, TypeError):
                    target_price = '—'
                badge_opps.append({
                    'ymmt':         item['ymmt'],
                    'stock_num':    stk,
                    'current':      cur_badge,
                    'target':       opp['target'],
                    'drop':         f"${drop:,.0f}",
                    'target_price': target_price,
                    'days':         item['days'],
                    'vdps':         item['vdps'],
                })
    # Sort: franchise makes first by VDP activity desc (highest shopper traffic = quickest win),
    # then other makes by VDP desc. Within each group, secondary sort by drop amount asc.
    _ymmt_hints = franchise_makes | {h.lower() for h in profile['franchise_model_hints']}
    def _opp_sort_key(o):
        is_franchise = 1 if any(b in o['ymmt'].lower() for b in _ymmt_hints) else 0
        vdps  = o.get('vdps', 0) or 0
        drop  = abs(float(o['drop'].replace('$','').replace(',','')))
        return (-is_franchise, -vdps, drop)  # franchise first, then high VDPs, then smallest drop
    badge_opps.sort(key=_opp_sort_key)

    # Used vehicle badge rate: Fair+Good+Great used vehicles vs total used
    used_inventory  = [v for v in inventory if v.get('stock_type', '').lower() == 'used']
    used_badged     = [v for v in used_inventory if v.get('badge', '') in ('Good', 'Great', 'Fair')]
    total_used      = len(used_inventory)
    used_badged_pct = round(len(used_badged) / total_used * 100, 1) if total_used else 0

    # Good/Great used-only badge rate (Change 4)
    good_great_used = [v for v in used_inventory if v.get('badge', '') in ('Good', 'Great')]
    good_great_used_count = len(good_great_used)
    good_great_used_pct = round(good_great_used_count / total_used * 100, 1) if total_used else 0

    # Avg days live split by stock type (Change 3)
    new_days_list  = [v['days'] for v in inventory if v.get('stock_type', '') == 'New' and v['days'] > 0]
    used_days_list = [v['days'] for v in inventory if v.get('stock_type', '') == 'Used' and v['days'] > 0]
    avg_days_new  = round(sum(new_days_list)  / len(new_days_list),  1) if new_days_list  else 0.0
    avg_days_used = round(sum(used_days_list) / len(used_days_list), 1) if used_days_list else 0.0

    # Competitor table: franchise-only comp set when the profile defines one,
    # else falls back to the broader like-tier comp_brands set (no dealer-name restriction).
    d_col        = next((c for c in market_df.columns if 'dealer name' in c.lower()), None)
    make_col_mkt = next((c for c in market_df.columns if c.strip().lower() == 'make name'), None)
    mkt_pct_mkt  = next((c for c in market_df.columns if '% of market avg price' in c.lower()), None)
    diff_g_mkt   = next((c for c in market_df.columns if 'difference - good' in c.lower()), None)
    diff_gr_mkt  = next((c for c in market_df.columns if 'difference - great' in c.lower()), None)
    days_mkt_col = next((c for c in market_df.columns if 'days live' in c.lower()), None)
    competitors = []
    self_rank = None
    market_avg_w1k = 12.0  # default

    if d_col:
        if franchise_makes and franchise_pattern:
            comp_makes = franchise_makes
            comp_pattern = franchise_pattern
        else:
            comp_makes = profile['comp_brands']
            comp_pattern = None

        if make_col_mkt and comp_makes:
            comp_make_mask = market_df[make_col_mkt].str.lower().isin(comp_makes)
            comp_mkt_df = market_df[comp_make_mask].copy()
        else:
            comp_mkt_df = market_df.copy()

        if comp_pattern:
            comp_dealer_mask = comp_mkt_df[d_col].str.lower().str.contains(comp_pattern, na=False)
            comp_mkt_df = comp_mkt_df[comp_dealer_mask].copy()

        # Compute within-$1k % for each competitor dealer
        badge_col_mkt = next((c for c in comp_mkt_df.columns if c.strip().lower() == 'price badge'), None)
        if diff_g_mkt:
            comp_mkt_df['_dg']  = pd.to_numeric(comp_mkt_df[diff_g_mkt].astype(str).str.replace(',',''), errors='coerce')
            comp_mkt_df['_dgr'] = pd.to_numeric(comp_mkt_df[diff_gr_mkt].astype(str).str.replace(',',''), errors='coerce') if diff_gr_mkt else float('nan')
            comp_mkt_df['_w1k'] = (
                comp_mkt_df['_dg'].between(-1000, 0, inclusive='right') |
                comp_mkt_df['_dgr'].between(-1000, 0, inclusive='right')
            )

        # Change 11: filter to badged vehicles (Good/Great/Fair) for "eligible" count
        if badge_col_mkt:
            comp_mkt_df['_badged'] = comp_mkt_df[badge_col_mkt].str.strip().str.title().isin(['Good', 'Great', 'Fair'])
        else:
            comp_mkt_df['_badged'] = True

        # Compute per-dealer stats
        within1k_by_dealer = {}
        for dlr, grp in comp_mkt_df.groupby(d_col):
            # Change 11: count = badged vehicles only
            badged_d = int(grp['_badged'].sum())
            # w1k only for badged vehicles — matches the badge_opps filter for self-entry
            w1k_d = int((grp['_w1k'] & grp['_badged']).sum()) if '_w1k' in grp.columns else 0
            # Denominator = badged vehicles only (eligible for badge analysis), not total
            w1k_pct_d = round(w1k_d / badged_d * 100, 1) if badged_d else 0
            avg_ptm_d = round(pd.to_numeric(grp[mkt_pct_mkt].astype(str).str.replace('%',''), errors='coerce').mean(), 1) if mkt_pct_mkt else 0.0
            avg_days_d = round(pd.to_numeric(grp[days_mkt_col].astype(str).str.replace(',',''), errors='coerce').mean(), 1) if days_mkt_col else 0.0
            within1k_by_dealer[str(dlr)] = {
                'count': badged_d, 'w1k': w1k_d, 'w1k_pct': w1k_pct_d,
                'avg_ptm': avg_ptm_d, 'avg_days': avg_days_d,
            }

        # Build competitor list from the comp set
        all_comps = []
        for dlr_str, stats_d in within1k_by_dealer.items():
            all_comps.append({
                'name': dlr_str,
                'count': stats_d['count'],
                'w1k': stats_d['w1k'],
                'w1k_pct': stats_d['w1k_pct'],
                'avg_ptm': stats_d['avg_ptm'],
                'avg_days': stats_d['avg_days'],
                'is_self': False,
            })

        # This dealer's own within-$1k — use badge_opps list (already filtered to used+badged only)
        # This ensures the count matches what the badge opps table shows
        self_w1k = len(badge_opps)  # badge_opps filtered to used vehicles with Good/Great/Fair badge only
        # Denominator = eligible used badged vehicles, not total inventory
        self_w1k_pct = round(self_w1k / len(used_badged) * 100, 1) if used_badged else 0
        self_avg_ptm  = round(_to_num(dealer_df[mkt_pct_col]).mean(), 1) if mkt_pct_col else 0.0
        # Overridden below (in generate_html) with swh_perf's used_avg_days when available,
        # since the LEI-computed avg_days here covers only the low-engaged subset.
        self_avg_days_val = avg_days

        self_entry = {
            'name': dealer_name,
            'count': len(used_badged),  # Change 11: badged vehicles only
            'w1k': self_w1k,
            'w1k_pct': self_w1k_pct,
            'avg_ptm': self_avg_ptm,
            'avg_days': self_avg_days_val,
            'is_self': True,
        }
        all_comps.append(self_entry)

        # Combine duplicate physical stores per the profile (e.g. co-located franchise stores
        # that show up as separate dealer-name rows in the export)
        for merge in profile['combine_stores']:
            a = next((c for c in all_comps if merge['a'] in c['name'].lower()), None)
            b = next((c for c in all_comps if merge['b'] in c['name'].lower()), None)
            if a and b:
                combined = {
                    'name': merge['combined_name'],
                    'count': a['count'] + b['count'],
                    'w1k':   a['w1k']   + b['w1k'],
                    'w1k_pct': round((a['w1k'] + b['w1k']) /
                                     max(a['count'] + b['count'], 1) * 100, 1),
                    'avg_ptm':  round((a['avg_ptm']  + b['avg_ptm'])  / 2, 1),
                    'avg_days': round((a['avg_days'] + b['avg_days']) / 2, 1),
                    'is_self': False,
                }
                all_comps = [c for c in all_comps
                             if merge['a'] not in c['name'].lower()
                             and merge['b'] not in c['name'].lower()]
                all_comps.append(combined)

        # Sort by avg_days descending (longest aging at top)
        all_comps.sort(key=lambda x: x['avg_days'], reverse=True)
        for i, entry in enumerate(all_comps, 1):
            entry['rank'] = i
            if entry.get('is_self'):
                self_rank = i
        competitors = all_comps

        # Market average within-$1k % across the comp set
        all_w1k_pcts = [e['w1k_pct'] for e in all_comps if e['count'] >= 5]
        market_avg_w1k = round(sum(all_w1k_pcts) / len(all_w1k_pcts), 1) if all_w1k_pcts else 12.0

    # Filter dealer_df to used vehicles only for badge distribution chart
    # (aligns with KPI card denominator of 182 used vehicles)
    used_stk_nums = {v['stock_num'] for v in inventory if v.get('stock_type') == 'Used'}
    _stk_col = _col(dealer_df, 'stock num')
    dealer_used_df = dealer_df[dealer_df[_stk_col].isin(used_stk_nums)] if _stk_col else dealer_df

    return {
        'total_vehicles': len(seen),
        'total_used': total_used,
        'used_badged_count': len(used_badged),
        'used_badged_pct': used_badged_pct,
        'good_great_used_count': good_great_used_count,
        'good_great_used_pct': good_great_used_pct,
        'badge_dist': _badge_dist(dealer_used_df),
        'mkt_badge_dist': _badge_dist(market_df),
        'good_great_count': good_great,
        'good_great_pct': round(good_great / len(seen) * 100, 1) if seen else 0,
        'avg_days': avg_days,
        'avg_days_new': avg_days_new,
        'avg_days_used': avg_days_used,
        'avg_photos': avg_photos,
        'total_vdps': total_vdps,
        'total_srps': total_srps,
        'total_leads': total_leads,
        'vdp_share_pct': vdp_share_pct,
        'franchise_lead_share': franchise_lead_share,
        'inventory': inventory,
        'badge_opps': badge_opps,
        'competitors': competitors,
        'self_rank': self_rank,
        'market_avg_w1k': market_avg_w1k,
    }


def load_market_share(path):
    """Load Market Share Comparison CSV. Returns normalized DataFrame."""
    print(f"  Loading Market Share: {Path(path).name}")
    df = _read_utf16_tsv(path)

    rename = {
        'Make': 'make', 'Model': 'model', 'Stock type': 'stock_type',
        'Dealer vehicles': 'dealer_vehicles', 'Market vehicles': 'market_vehicles',
        'Vehicle share (%)': 'vehicle_share_pct',
        'Dealer VDPs': 'dealer_vdps', 'Market VDPs': 'market_vdps',
        'VDP share (%)': 'vdp_share_pct',
        'Dealer connections': 'dealer_connections', 'Market connections': 'market_connections',
        'Connections share (%)': 'conn_share_pct',
        'Dealer days live': 'dealer_days', 'Market days live': 'market_days',
    }
    df = df.rename(columns={c: rename[c] for c in df.columns if c in rename})

    int_cols = ['dealer_vehicles', 'market_vehicles', 'dealer_vdps', 'market_vdps',
                'dealer_connections', 'market_connections']
    for c in int_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c].str.replace(',', ''), errors='coerce').fillna(0).astype(int)

    float_cols = ['vehicle_share_pct', 'vdp_share_pct', 'conn_share_pct']
    for c in float_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c].str.replace('%', ''), errors='coerce').fillna(0.0)

    # Drop pivot artifact rows
    if 'make' in df.columns:
        df = df[df['make'].notna() & ~df['make'].isin(['', 'FALSE', 'TRUE', 'nan'])]

    # Signal
    def _signal(row):
        vshr = row.get('vehicle_share_pct', 0) or 0
        dshr = row.get('vdp_share_pct', 0) or 0
        if vshr == 0:
            return '—'
        ratio = dshr / vshr
        return '🟢' if ratio >= 1.1 else ('🔴' if ratio <= 0.75 else '🟡')

    df['signal'] = df.apply(_signal, axis=1)
    print(f"  ✓ Market Share: {len(df)} rows")
    return df


def load_price_comparison(path):
    """Load Price Comparison CSV. Returns (stats_dict, used_stats_dict, reprice_candidates_list, raw_df)."""
    print(f"  Loading Price Comparison: {Path(path).name}")
    df = _read_utf16_tsv(path)

    value_col  = next((c for c in df.columns if c.strip().lower() == 'value'), None)
    days_col   = next((c for c in df.columns if 'days live' in c.lower()), None)
    ymmt_col   = next((c for c in df.columns if 'ymmt' in c.lower()), None)
    price_col  = next((c for c in df.columns if c.strip().lower() == 'price'), None)
    pct_col    = next((c for c in df.columns if 'price vs market' in c.lower()), None)
    stk_col    = next((c for c in df.columns if 'stock num' in c.lower()), None)
    stype_col  = next((c for c in df.columns if 'stock type' in c.lower()), None)

    cats = df[value_col].dropna().str.strip() if value_col else pd.Series([], dtype=str)
    total = len(cats)

    under = int(cats.str.contains('under', case=False).sum())
    at    = int(cats.str.match(r'(?i)^at market').sum())
    above = int(cats.str.contains('above', case=False).sum())

    stats = {
        'total': total,
        'under': {'count': under, 'pct': round(under / total * 100, 1) if total else 0},
        'at':    {'count': at,    'pct': round(at    / total * 100, 1) if total else 0},
        'above': {'count': above, 'pct': round(above / total * 100, 1) if total else 0},
    }

    # Change 7: compute Used-only stats
    if stype_col and value_col:
        used_df   = df[df[stype_col].str.strip().str.lower() == 'used']
        used_cats = used_df[value_col].dropna().str.strip()
        u_total   = len(used_cats)
        u_under   = int(used_cats.str.contains('under', case=False).sum())
        u_at      = int(used_cats.str.match(r'(?i)^at market').sum())
        u_above   = int(used_cats.str.contains('above', case=False).sum())
    else:
        used_df = df
        u_total, u_under, u_at, u_above = total, under, at, above
    used_stats = {
        'total': u_total,
        'under': {'count': u_under, 'pct': round(u_under / u_total * 100, 1) if u_total else 0},
        'at':    {'count': u_at,    'pct': round(u_at    / u_total * 100, 1) if u_total else 0},
        'above': {'count': u_above, 'pct': round(u_above / u_total * 100, 1) if u_total else 0},
    }

    reprice = []
    if value_col and days_col:
        df['_days'] = pd.to_numeric(df[days_col].str.replace(',', ''), errors='coerce').fillna(0)
        mask = df[value_col].str.contains('above', case=False, na=False) & (df['_days'] > 30)
        for _, row in df[mask].iterrows():
            ymmt  = str(row[ymmt_col]).strip() if ymmt_col else ''
            stk   = str(row[stk_col]).strip() if stk_col else ''
            pct_raw = str(row[pct_col]).replace('%', '').strip() if pct_col else ''
            try:
                price = float(str(row[price_col]).replace(',', '').replace('$', ''))
                pct_f = float(pct_raw)
                drop  = price - (price / (pct_f / 100))
                target = price - drop
                action = f"Drop ~${drop:,.0f} → ${target:,.0f}"
            except (ValueError, TypeError):
                price  = None
                action = '—'
                pct_f  = 0.0
            reprice.append({
                'ymmt':   ymmt,
                'stock':  stk,
                'price':  f"${price:,.0f}" if price else '—',
                'days':   int(row['_days']),
                'pct':    f"{pct_f:.0f}%" if pct_f else '—',
                'action': action,
            })
    reprice.sort(key=lambda x: x['days'], reverse=True)

    print(f"  ✓ Price Comparison: {total} vehicles ({u_total} used) | Under: {under} | At: {at} | Above: {above} | Reprice candidates (>30d): {len(reprice)}")
    return stats, used_stats, reprice, df


def load_swh_perf(path, dealer_hint):
    """
    Load the admin.cars.com inventory performance export.
    Returns dict with total VDPs, connections, SRPs, vehicle counts, avg days live.
    Filters 'Dealer Name' rows to those containing dealer_hint.
    """
    try:
        df = _read_utf16_tsv(path)
        own = df[df['Dealer Name'].str.contains(dealer_hint, case=False, na=False)].copy()
        if own.empty:
            print(f"  ⚠ No rows matched dealer hint '{dealer_hint}' in perf CSV")
            return None
        def _n(col):
            return pd.to_numeric(own[col].astype(str).str.replace(',', ''), errors='coerce').fillna(0) if col in own.columns else pd.Series([0]*len(own))
        total_vdps   = int(_n('VDP Impressions').sum())
        total_conns  = int(_n('Connections').sum())
        total_srps   = int(_n('SRPs').sum())
        total_saved  = int(_n('Saved vehicles').sum())
        avg_days     = round(pd.to_numeric(own['Days live'], errors='coerce').mean(), 1) if 'Days live' in own.columns else 0
        used_ct      = int((own.get('Stock type', pd.Series()) == 'Used').sum())
        new_ct       = int((own.get('Stock type', pd.Series()) == 'New').sum())
        # Split avg days by stock type (Change 11)
        if 'Days live' in own.columns and 'Stock type' in own.columns:
            new_avg  = round(pd.to_numeric(own[own['Stock type'] == 'New']['Days live'],  errors='coerce').mean(), 1)
            used_avg = round(pd.to_numeric(own[own['Stock type'] == 'Used']['Days live'], errors='coerce').mean(), 1)
            new_avg  = new_avg  if pd.notna(new_avg)  else 0.0
            used_avg = used_avg if pd.notna(used_avg) else 0.0
        else:
            new_avg  = 0.0
            used_avg = 0.0
        print(f"  ✓ Perf CSV: {len(own)} vehicles | VDPs: {total_vdps:,} | Connections: {total_conns:,} | Avg days: {avg_days} (New: {new_avg} / Used: {used_avg})")
        return {
            'total_vehicles': len(own),
            'used': used_ct, 'new': new_ct,
            'total_vdps': total_vdps,
            'total_connections': total_conns,
            'total_srps': total_srps,
            'total_saved': total_saved,
            'avg_days': avg_days,
            'new_avg_days': new_avg,
            'used_avg_days': used_avg,
        }
    except Exception as e:
        print(f"  ⚠ Perf CSV load failed: {e}")
        return None


def load_perf_trends(profile):
    """
    Return this profile's hand-curated admin.cars.com Performance Trends KPIs for the period.
    There's no live CSV parser for this section yet — the numbers are pulled manually each
    period into the profile's 'perf_trends' dict. Returns None if the profile has none (the
    VDP/Connection performance section is skipped in that case).
    """
    result = profile.get('perf_trends')
    if not result:
        print("  ⚠ No perf_trends in profile — skipping Performance Trends KPI section")
        return None
    print(f"  ✓ Performance Trends: VDPs={result['vdps_q2']:,} | Connections={result['conns_q2']:,} (excl. Instant Offer: {result['conns_excl_instant']:,})")
    return result


def parse_cargurus_html(path, profile):
    """Extract key metrics from CarGurus HTML dashboard file."""
    print(f"  Loading CarGurus dashboard: {Path(path).name}")
    with open(path, encoding='utf-8', errors='replace') as f:
        html = f.read()

    cg = {'monthly_connections': {}, 'deal_ratings': {}, 'top_makes': [], 'raw_text': ''}
    months = [m.lower() for m in profile['month_labels']]

    if BS4_AVAILABLE:
        soup = BeautifulSoup(html, 'html.parser')
        text = soup.get_text(' ', strip=True)
    else:
        # Fallback: strip tags with regex
        text = re.sub(r'<[^>]+>', ' ', html)
        text = re.sub(r'\s+', ' ', text).strip()

    cg['raw_text'] = text[:2000]

    # Each month's narrative section has exactly one "NNN total connections" in order.
    conn_hits = re.findall(r'(\d{1,2},\d{3}|\d{3,5})\s+total\s+connections', html, re.IGNORECASE)
    for month, val in zip(months, conn_hits):
        cg['monthly_connections'][month] = int(val.replace(',', ''))

    # Also extract monthly VDP views for the bar chart context
    vdp_hits = re.findall(r'(\d{1,2},\d{3}|\d{4,5})\s+VDP\s+views', html, re.IGNORECASE)
    cg['monthly_vdps'] = {}
    for month, val in zip(months, vdp_hits):
        cg['monthly_vdps'][month] = int(val.replace(',', ''))

    # Deal ratings
    rating_map = [
        ('great_deal',  r'great\s+deal[^0-9a-z]{0,30}(\d{1,2}\.?\d*)\s*%'),
        ('good_deal',   r'good\s+deal[^0-9a-z]{0,30}(\d{1,2}\.?\d*)\s*%'),
        ('fair_deal',   r'fair\s+deal[^0-9a-z]{0,30}(\d{1,2}\.?\d*)\s*%'),
        ('high_price',  r'high\s+price[^0-9a-z]{0,30}(\d{1,2}\.?\d*)\s*%'),
        ('overpriced',  r'overpriced[^0-9a-z]{0,30}(\d{1,2}\.?\d*)\s*%'),
        ('no_analysis', r'no\s+price\s+analysis[^0-9a-z]{0,30}(\d{1,2}\.?\d*)\s*%'),
    ]
    for key, pat in rating_map:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            cg['deal_ratings'][key] = float(m.group(1))

    # Fall back to the profile's known-good values only if it supplies them (e.g. a prior
    # verified run for this exact dealer/period) — otherwise leave empty rather than
    # reporting another dealer's numbers.
    if not cg['deal_ratings'] and profile.get('cargurus_fallback_deal_ratings'):
        cg['deal_ratings'] = dict(profile['cargurus_fallback_deal_ratings'])
        print("  ⚠ Using profile's fallback deal ratings (regex extraction found none)")
    elif not cg['deal_ratings']:
        print("  ⚠ No deal ratings extracted from CarGurus HTML and no profile fallback supplied")

    print(f"  ✓ CarGurus: {len(cg['deal_ratings'])} deal ratings | monthly: {dict((k, v) for k, v in cg['monthly_connections'].items() if v)}")
    return cg


# ── HTML Report ───────────────────────────────────────────────────────────────

def _build_connections_section(perf, profile, PURPLE, TEAL):
    """Build the multi-month Connections & VDP Summary section."""
    if not perf:
        return ''
    cm  = perf.get('conn_monthly_by_type', {})
    vm  = perf.get('vdp_monthly', {})
    months = profile['month_labels']
    period_label = profile['period_label']
    types  = ['Email', 'Phone', 'Chat', 'Web Transfer', 'VDP Deep Link', 'Maps']
    type_icons = {'Email': '✉', 'Phone': '📞', 'Chat': '💬', 'Web Transfer': '🔗', 'VDP Deep Link': '🚗', 'Maps': '📍'}

    # H2: conn_monthly_by_type 'Total' values (excl. Instant Offer)
    conn_monthly = [cm.get(m, {}).get('Total', 0) for m in months]
    vdp_monthly  = [vm.get(m.lower(), 0) for m in months]

    # Build breakdown table
    rows = ''
    for m in months + ['Total']:
        d = cm.get(m, {})
        is_total = m == 'Total'
        style = 'font-weight:700; background:#f0e6f7;' if is_total else ''
        label = f'{period_label} Total' if is_total else m
        cells = ''.join(f'<td class="num" style="{style}">{d.get(t, "—") if d.get(t, 0) else "—"}</td>' for t in types)
        rows += f'<tr><td style="{style}">{label}</td>{cells}<td class="num" style="{style}; color:{PURPLE};">{d.get("Total", 0):,}</td></tr>'

    col_widths = {'Email': '80px', 'Phone': '75px', 'Chat': '65px', 'Web Transfer': '100px', 'VDP Deep Link': '110px', 'Maps': '65px'}
    def _th(t):
        w = col_widths.get(t, '80px')
        ic = type_icons.get(t, '')
        return f'<th style="white-space:nowrap; min-width:{w}; text-align:right;">{ic} {t.upper()}</th>'
    type_headers = ''.join(_th(t) for t in types)

    # M6: Connection momentum callout (uses excl-instant series for consistency with charts)
    conn_vals = [cm.get(m, {}).get('Total', 0) for m in months]
    if len(conn_vals) >= 2 and conn_vals[0] and conn_vals[-1]:
        pct_growth = round((conn_vals[-1] - conn_vals[0]) / conn_vals[0] * 100)
        total_conns = sum(v for v in conn_vals if v)
        total_vdps_q2 = perf['vdps_q2'] if perf else 0
        conv_rate = round(total_conns / total_vdps_q2 * 100, 1) if total_vdps_q2 else 0
        trend_word = 'grew' if pct_growth >= 0 else 'declined'
        momentum_html = (
            f'<div style="background:#e6f7f5; border-left:4px solid {TEAL}; border-radius:4px; padding:10px 14px; margin-bottom:16px; font-size:13px;">'
            f'<strong>&#x2705; Connection Momentum:</strong> Connections {trend_word} <strong>{pct_growth:+d}%</strong> from {months[0]} ({conn_vals[0]:,}) to {months[-1]} ({conn_vals[-1]:,}). '
            f'VDP-to-connection conversion rate: <strong>{conv_rate}%</strong> ({total_conns:,} connections / {total_vdps_q2:,} VDPs). '
            f'Luxury benchmark is typically 2.5&#x2013;4%.</div>'
        )
    else:
        momentum_html = ''

    # H2: VDP print-data fallback
    vdp_print_data = ', '.join(f'{m}: {v:,}' for m, v in zip(months, vdp_monthly))
    conn_print_data = ', '.join(f'{m}: {v:,}' for m, v in zip(months, conn_monthly))

    return f"""
<div class="section" id="perfSection">
  <div class="section-title">VDP &amp; Connection Performance — {period_label}</div>
  <div style="display:grid; grid-template-columns:1fr 1fr; gap:24px; margin-bottom:24px;">
    <div style="background:#fff; border:1px solid #eee; border-radius:8px; padding:16px;">
      <div style="font-weight:700; font-size:13px; margin-bottom:12px;">&#x1F697; VDP Views by Month</div>
      <canvas id="vdpMonthChart" height="200"></canvas>
      <div class="print-data" style="display:none; font-size:13px; color:#333;">{vdp_print_data}</div>
    </div>
    <div style="background:#fff; border:1px solid #eee; border-radius:8px; padding:16px;">
      <div style="font-weight:700; font-size:13px; margin-bottom:12px;">&#x1F4DE; Connections by Month <span style="font-size:11px; font-weight:400; color:#888;">(excl. Instant Offer)</span></div>
      <canvas id="connMonthChart" height="200"></canvas>
      <div class="print-data" style="display:none; font-size:13px; color:#333;">{conn_print_data}</div>
    </div>
  </div>
  {momentum_html}
  <strong style="font-size:13px;">Connection Type Breakdown</strong>
  <div style="overflow-x:auto; margin-top:10px;">
    <table>
      <thead><tr><th>Month</th>{type_headers}<th>Total</th></tr></thead>
      <tbody>{rows}</tbody>
    </table>
  </div>
</div>"""


def _build_engagement_tiles(swh_perf, lei_stats, profile, PURPLE, TEAL, perf=None):
    """Build the 4-tile engagement grid: VDPs, Connections, Avg Days New, Avg Days Used.
    Changes 5: use perf period data for VDP/Connection tiles; swh_perf for Days tiles.
    """
    aging_threshold = profile['aging_threshold_days']
    franchise_benchmark = profile['franchise_avg_days_benchmark']
    period_label = profile['period_label']
    # Change 5: VDP and Connection values come from perf (period-curated) when available
    if perf is not None:
        vdp_val   = perf['vdps_q2']
        vdp_label = f'VDPs ({period_label})'
        vdp_sub   = 'admin.cars.com Performance Trends'
        conn_val   = perf['conns_excl_instant']
        conn_label = f'Connections ({period_label})'
        conn_sub   = f"Excl. {perf.get('instant_offer', 0)} Instant Offer - Cars.com (AccuTrade)"
    elif swh_perf:
        vdp_val   = swh_perf['total_vdps']
        vdp_label = 'Total VDPs'
        vdp_sub   = 'Vehicle Detail Page views'
        conn_val   = swh_perf['total_connections']
        conn_label = 'Total Connections'
        conn_sub   = 'Phone + email + chat'
    else:
        vdp_val   = lei_stats['total_vdps']
        vdp_label = 'VDPs (7-day)'
        vdp_sub   = 'LEI snapshot'
        conn_val   = lei_stats['total_leads']
        conn_label = 'Connections (7-day)'
        conn_sub   = 'LEI snapshot'

    # Days tiles always use swh_perf if available, else lei_stats
    if swh_perf:
        days_new  = swh_perf.get('new_avg_days')  or lei_stats.get('avg_days_new',  0)
        days_used = swh_perf.get('used_avg_days') or lei_stats.get('avg_days_used', 0)
    else:
        days_new  = lei_stats.get('avg_days_new',  0)
        days_used = lei_stats.get('avg_days_used', 0)

    new_color  = '#c62828' if days_new  > aging_threshold else '#1a7a1a'
    used_color = '#c62828' if days_used > aging_threshold else '#1a7a1a'
    # Full-width single row — 4 tiles spread evenly across the page
    return (
        f'<div style="margin-top:16px; display:grid; grid-template-columns:repeat(4,1fr); gap:16px;">'
        f'<div style="background:#f0e6f7; border-radius:12px; padding:24px 28px; border-left:5px solid {PURPLE}; display:flex; flex-direction:column; justify-content:center;">'
        f'<div style="font-size:11px; color:#666; text-transform:uppercase; letter-spacing:.8px; font-weight:600;">{vdp_label}</div>'
        f'<div style="font-size:42px; font-weight:800; color:{PURPLE}; line-height:1.1; margin:6px 0;">{vdp_val:,}</div>'
        f'<div style="font-size:12px; color:#888;">{vdp_sub}</div></div>'
        f'<div style="background:#e6f7f5; border-radius:12px; padding:24px 28px; border-left:5px solid {TEAL}; display:flex; flex-direction:column; justify-content:center;">'
        f'<div style="font-size:11px; color:#666; text-transform:uppercase; letter-spacing:.8px; font-weight:600;">{conn_label}</div>'
        f'<div style="font-size:42px; font-weight:800; color:{TEAL}; line-height:1.1; margin:6px 0;">{conn_val:,}</div>'
        f'<div style="font-size:12px; color:#888;">{conn_sub}</div></div>'
        f'<div style="background:#fff8e1; border-radius:12px; padding:24px 28px; border-left:5px solid #F9A825; display:flex; flex-direction:column; justify-content:center;">'
        f'<div style="font-size:11px; color:#666; text-transform:uppercase; letter-spacing:.8px; font-weight:600;">Avg Days Live — New Inventory</div>'
        f'<div style="font-size:42px; font-weight:800; color:{new_color}; line-height:1.1; margin:6px 0;">{days_new}</div>'
        f'<div style="font-size:12px; color:{new_color};">{f"⚠ Aging — above {aging_threshold}-day target" if days_new > aging_threshold else "✓ Within target"}</div></div>'
        f'<div style="background:#fff8e1; border-radius:12px; padding:24px 28px; border-left:5px solid #F9A825; display:flex; flex-direction:column; justify-content:center;">'
        f'<div style="font-size:11px; color:#666; text-transform:uppercase; letter-spacing:.8px; font-weight:600;">Avg Days Live — Used Inventory</div>'
        f'<div style="font-size:42px; font-weight:800; color:{used_color}; line-height:1.1; margin:6px 0;">{days_used}</div>'
        f'<div style="font-size:12px; color:{used_color};">{"⚠ Aging — {:.0f}x above {}-day franchise avg".format(days_used/franchise_benchmark, franchise_benchmark) if days_used > franchise_benchmark else "✓ Within target"}</div></div>'
        f'</div>'
    )


def generate_html(dealer_name, lei_stats, mkt_share_df, price_stats, reprice, cg, today_str, profile, swh_perf=None, perf=None, price_stats_used=None):
    """Build self-contained HTML report with Chart.js charts."""

    # ── Cars.com logo — inline SVG matching actual brand mark (white version for dark header) ──
    _logo_svg = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 220 95" width="154" height="67" style="display:block; margin-left:auto;">
  <!-- Outer oval matching Cars.com brand mark -->
  <ellipse cx="105" cy="50" rx="98" ry="42" fill="none" stroke="white" stroke-width="6"/>
  <!-- cars.com wordmark — DM Sans / rounded geometric to match site -->
  <text x="104" y="59" font-family="DM Sans,-apple-system,Helvetica Neue,Arial,sans-serif" font-size="30" font-weight="700" fill="white" text-anchor="middle" letter-spacing="-0.3">cars.com</text>
  <!-- ® mark upper right of oval -->
  <text x="204" y="18" font-family="Arial,sans-serif" font-size="12" fill="white">&#174;</text>
</svg>'''

    # ── Badge distribution data — Change 6: filter out "Not Badged" ──
    badge_labels = [k for k in lei_stats['badge_dist'].keys() if 'not badged' not in k.lower()]
    badge_counts = [lei_stats['badge_dist'][k]['count'] for k in badge_labels]
    badge_colors = {
        'Great': '#1a7a1a', 'Good': '#4CAF50', 'Fair': '#FFC107',
        'High Price': '#FF5722', 'Overpriced': '#D32F2F', 'No Badge': '#9E9E9E',
    }
    badge_chart_colors = [badge_colors.get(k, '#999') for k in badge_labels]

    # ── Price position data — Change 7: use used_stats for chart and KPI ──
    pc = price_stats
    pc_u = price_stats_used if price_stats_used is not None else price_stats
    at_under_pct = round(pc_u['under']['pct'] + pc_u['at']['pct'], 1)
    price_chart_data   = [at_under_pct, pc_u['above']['pct']]
    price_chart_labels = [f'At/Under Market', f'Above Market']
    price_chart_colors = ['#00A88E', '#FF5722']

    # ── Market share table rows — sorted 🟢 → 🟡 → 🔴, then by New/Used ──
    _sig_rank = {'🟢': 0, '🟡': 1, '🔴': 2, '—': 3}
    _stype_rank_ms = {'New': 0, 'Used': 1, '': 2}
    mkt_sorted = mkt_share_df.copy()
    mkt_sorted['_sig_r']   = mkt_sorted.get('signal', '—').map(lambda s: _sig_rank.get(s, 3))
    mkt_sorted['_stype_r'] = mkt_sorted.get('stock_type', '').map(lambda s: _stype_rank_ms.get(s, 2))
    mkt_sorted = mkt_sorted.sort_values(['_stype_r', '_sig_r']).reset_index(drop=True)

    share_rows_html = ''
    # H6: map emoji signal → filter string used by filterSignal()
    _sig_to_filter = {'🟢': 'win', '🟡': 'yellow', '🔴': 'gap', '—': 'none'}
    for _, row in mkt_sorted.iterrows():
        make  = row.get('make', '')
        model = row.get('model', '')
        stype = row.get('stock_type', '')
        dv    = int(row.get('dealer_vehicles', 0))
        mv    = int(row.get('market_vehicles', 0))
        vshr  = f"{float(row.get('vehicle_share_pct', 0)):.1f}%"
        dv2   = int(row.get('dealer_vdps', 0))
        mv2   = int(row.get('market_vdps', 0))
        vshr2 = f"{float(row.get('vdp_share_pct', 0)):.1f}%"
        dc    = int(row.get('dealer_connections', 0))
        mc2   = int(row.get('market_connections', 0))
        cshr  = f"{float(row.get('conn_share_pct', 0)):.1f}%"
        sig   = row.get('signal', '—')
        sig_filter = _sig_to_filter.get(sig, 'none')
        # Actionable note for red rows
        note = ''
        if sig == '🔴':
            vdp_gap = round(float(row.get('vehicle_share_pct', 0)) - float(row.get('vdp_share_pct', 0)), 1)
            if vdp_gap > 0:
                note = f'{vdp_gap:.1f} percentage point VDP gap — review pricing/photos'
        share_rows_html += f"""
        <tr data-signal="{sig_filter}" data-stype="{stype}">
          <td><strong>{make}</strong> {model}</td>
          <td class="center">{stype}</td>
          <td class="num">{vshr}</td>
          <td class="num">{vshr2}</td>
          <td class="num">{cshr}</td>
          <td class="center">{sig}</td>
          <td style="font-size:11px; color:#c62828;">{note}</td>
        </tr>"""

    # ── Badge opportunity rows — H4: franchise makes first, H5: expand toggle ──
    target_colors = {'Great': '#1a7a1a', 'Good': '#33691e'}
    _all_opps = lei_stats.get('badge_opps', [])
    franchise_makes = profile['franchise_makes']
    # H4: split into franchise makes (sorted by days desc) and other makes (sorted by drop asc)
    _lr_opps    = sorted(
        [b for b in _all_opps if any(m in b['ymmt'].lower() for m in franchise_makes)],
        key=lambda x: x['days'], reverse=True
    )
    _other_opps = sorted(
        [b for b in _all_opps if not any(m in b['ymmt'].lower() for m in franchise_makes)],
        key=lambda x: abs(float(x['drop'].replace('$','').replace(',','')))
    )
    _ordered_opps = _lr_opps + _other_opps

    def _opp_row(b):
        tc = target_colors.get(b['target'], '#333')
        badge_cls = ('badge-great' if b['current']=='Great' else
                     'badge-good'  if b['current']=='Good'  else
                     'badge-fair'  if b['current']=='Fair'  else 'badge-nb')
        return (f'<tr>'
                f'<td>{b["ymmt"]}</td>'
                f'<td style="font-family:monospace; font-size:12px;">{b["stock_num"]}</td>'
                f'<td class="center"><span class="badge {badge_cls}">{b["current"]}</span></td>'
                f'<td class="center" style="color:{tc}; font-weight:700;">→ {b["target"]}</td>'
                f'<td class="num warn">{b["drop"]}</td>'
                f'<td class="num" style="color:{tc}; font-weight:600;">{b["target_price"]}</td>'
                f'<td class="num">{b["days"]}</td>'
                f'<td class="num">{b["vdps"]}</td>'
                f'</tr>')

    _divider_row = '<tr style="background:#f9f9f9;"><td colspan="8" style="font-size:11px; color:#888; padding:4px 10px; font-style:italic;">Other makes within $1k of badge</td></tr>'

    # Build top-5 rows and extra rows (with divider at LR→other boundary)
    badge_top5_html = ''
    badge_extra_html = ''
    for idx, b in enumerate(_ordered_opps):
        # Insert divider at the LR→other boundary
        is_divider_point = (idx == len(_lr_opps) and _other_opps)
        row_html = ''
        if is_divider_point:
            row_html += _divider_row
        row_html += _opp_row(b)
        if idx < 5:
            badge_top5_html += row_html
        else:
            badge_extra_html += row_html

    if not _ordered_opps:
        badge_top5_html = '<tr><td colspan="8" class="center muted">No used vehicles within $1,000 of a badge tier</td></tr>'

    # ── Competitor rows — comp set, sorted by avg days descending (Change 9) ──
    comp_rows_html = ''
    market_avg_w1k = lei_stats.get('market_avg_w1k', 12.0)
    for c in lei_stats['competitors']:
        is_self   = c.get('is_self', False)
        hl        = f'style="background:#f0e6f7; font-weight:700;"' if is_self else ''
        rank_lbl  = f'#{c["rank"]}'
        label     = f'⭐ {c["name"]}' if is_self else c['name']
        w1k_pct   = c.get('w1k_pct', 0)
        avg_ptm   = c.get('avg_ptm', 0)
        # For self-entry, use swh_perf used_avg_days to match KPI card (126.4 vs LEI subset ~110)
        if c.get('is_self') and swh_perf and swh_perf.get('used_avg_days'):
            avg_days_c = swh_perf['used_avg_days']
        else:
            avg_days_c = c.get('avg_days', 0)
        # Higher % = more vehicles need repricing = LESS optimized → reverse color (high=red, low=green)
        w1k_color = '#c62828' if w1k_pct > market_avg_w1k * 1.3 else ('#F9A825' if w1k_pct > market_avg_w1k * 0.8 else '#1a7a1a')
        days_color = '#c62828' if avg_days_c > profile['aging_threshold_days'] else '#333'
        comp_rows_html += (
            f'<tr {hl}><td class="center">{rank_lbl}</td><td>{label}</td>'
            f'<td class="num">{c["count"]:,}</td>'
            f'<td class="num">{c["w1k"]:,}</td>'
            f'<td class="num" style="font-weight:700; color:{w1k_color};">{round(w1k_pct):.0f}%</td>'
            f'<td class="num">{round(avg_ptm):.0f}%</td>'
            f'<td class="num" style="font-weight:700; color:{days_color};">{round(avg_days_c):.0f}</td></tr>'
        )

    # ── KPI: used badge rate ──
    used_b_count = lei_stats['used_badged_count']
    used_total   = lei_stats['total_used']
    used_b_pct   = lei_stats['used_badged_pct']
    kpi_good_great = f"{round(lei_stats['good_great_pct']):.0f}%"
    kpi_under_at   = f"{pc_u['under']['pct'] + pc_u['at']['pct']:.0f}%"
    kpi_vdp_share  = f"{round(lei_stats['vdp_share_pct']):.0f}%"

    # ── Chart.js JSON ──
    badge_json = json.dumps({'labels': badge_labels, 'data': badge_counts, 'colors': badge_chart_colors})
    price_json = json.dumps({'labels': price_chart_labels, 'data': price_chart_data, 'colors': price_chart_colors})

    # ── H2: VDP/Connection monthly bar charts — only when perf (period-curated) data exists ──
    if perf:
        _months = profile['month_labels']
        _vdp_vals  = [perf.get('vdp_monthly', {}).get(m.lower(), 0) for m in _months]
        _conn_vals = [perf.get('conn_monthly_by_type', {}).get(m, {}).get('Total', 0) for m in _months]
        month_charts_js = f"""
// H2: VDP Monthly Chart
new Chart(document.getElementById('vdpMonthChart'), {{
  type: 'bar',
  data: {{
    labels: {json.dumps(_months)},
    datasets: [{{ data: {json.dumps(_vdp_vals)}, backgroundColor: '{TEAL}', borderRadius: 6, barPercentage: 0.6 }}]
  }},
  options: {{
    plugins: {{ legend: {{ display: false }}, tooltip: {{ callbacks: {{
      label: function(ctx) {{ var vals={json.dumps(_vdp_vals)}; var delta=ctx.dataIndex>0?((vals[ctx.dataIndex]-vals[ctx.dataIndex-1])/vals[ctx.dataIndex-1]*100).toFixed(1):null; return ' '+ctx.raw.toLocaleString()+(delta?' ('+(delta>0?'+':'')+delta+'% vs prev)':''); }}
    }} }} }},
    scales: {{ y: {{ beginAtZero: true, ticks: {{ callback: function(v) {{ return v.toLocaleString(); }} }} }}, x: {{ grid: {{ display: false }} }} }}
  }}
}});

// H2: Connections Monthly Chart (excl. Instant Offer)
new Chart(document.getElementById('connMonthChart'), {{
  type: 'bar',
  data: {{
    labels: {json.dumps(_months)},
    datasets: [{{ data: {json.dumps(_conn_vals)}, backgroundColor: '{PURPLE}', borderRadius: 6, barPercentage: 0.6 }}]
  }},
  options: {{
    plugins: {{ legend: {{ display: false }}, tooltip: {{ callbacks: {{
      label: function(ctx) {{ var vals={json.dumps(_conn_vals)}; var delta=ctx.dataIndex>0?((vals[ctx.dataIndex]-vals[ctx.dataIndex-1])/vals[ctx.dataIndex-1]*100).toFixed(1):null; return ' '+ctx.raw+(delta?' ('+(delta>0?'+':'')+delta+'% vs prev)':''); }}
    }} }} }},
    scales: {{ y: {{ beginAtZero: true }}, x: {{ grid: {{ display: false }} }} }}
  }}
}});"""
    else:
        month_charts_js = ''

    # ── H3: Avg Days Live (Used) headline KPI ──
    swh_perf_used_days = (swh_perf['used_avg_days'] if swh_perf else lei_stats.get('avg_days_used', 126))

    # ── H5: Badge opps expand toggle ──
    total_opps = len(lei_stats.get('badge_opps', []))

    # ── H6: Market share signal counts ──
    if 'signal' in mkt_share_df.columns:
        _sig_counts = mkt_share_df['signal'].value_counts().to_dict()
    else:
        _sig_counts = {}
    red_count   = int(_sig_counts.get('🔴', 0))
    green_count = int(_sig_counts.get('🟢', 0))
    total_mkt_rows = len(mkt_share_df)

    # ── H7: Next Steps computed values ──
    badge_opp_count  = len(lei_stats.get('badge_opps', []))
    # Compute actual avg drop from badge_opps data (uses $1k threshold, not $500)
    _opps = lei_stats.get('badge_opps', [])
    if _opps:
        _drops = []
        for _o in _opps:
            try: _drops.append(float(_o['drop'].replace('$','').replace(',','')))
            except: pass
        avg_drop_str = f'~${round(sum(_drops)/len(_drops)/50)*50:,}' if _drops else '~$650'
    else:
        avg_drop_str = '~$650'
    above_mkt_count  = (price_stats_used if price_stats_used else price_stats)['above']['count']
    price_above_pct  = (price_stats_used if price_stats_used else price_stats)['above']['pct']
    used_days        = swh_perf_used_days

    # ── M2: Top franchise-make VDP gap models (falls back to all makes if no franchise set) ──
    top_lr_gaps_str = ''
    if 'make' in mkt_share_df.columns and 'stock_type' in mkt_share_df.columns:
        if franchise_makes:
            fran_used = mkt_share_df[
                mkt_share_df['make'].str.lower().isin(franchise_makes) &
                (mkt_share_df['stock_type'].str.strip().str.lower() == 'used')
            ].copy()
        else:
            fran_used = mkt_share_df[mkt_share_df['stock_type'].str.strip().str.lower() == 'used'].copy()
        if not fran_used.empty and 'vehicle_share_pct' in fran_used.columns and 'vdp_share_pct' in fran_used.columns:
            fran_used['_gap'] = fran_used['vehicle_share_pct'] - fran_used['vdp_share_pct']
            fran_used_gaps = fran_used[fran_used['_gap'] > 5].sort_values('_gap', ascending=False)
            if not fran_used_gaps.empty:
                parts = []
                for _, grow in fran_used_gaps.head(3).iterrows():
                    model_lbl = grow.get('model', '')
                    gap_val   = grow['_gap']
                    parts.append(f"{model_lbl} ({gap_val:.1f} percentage point gap)")
                top_lr_gaps_str = ', '.join(parts)
    show_lr_gap_callout = bool(top_lr_gaps_str)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{dealer_name} — Cars.com Performance Overview | {profile['period_label']}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;0,9..40,800;1,9..40,400&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'DM Sans', -apple-system, 'Helvetica Neue', Arial, sans-serif; background: #f5f5f7; color: #222; font-size: 14px; }}
  .header {{ background: {PURPLE}; color: #fff; padding: 24px 32px; }}
  .header h1 {{ font-size: 22px; font-weight: 700; }}
  .header p {{ font-size: 13px; opacity: 0.85; margin-top: 4px; }}
  .container {{ max-width: 1280px; margin: 0 auto; padding: 24px 20px; }}
  .kpi-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px; margin-bottom: 28px; }}
  .kpi-card {{ background: #fff; border-radius: 10px; padding: 18px 20px; box-shadow: 0 1px 4px rgba(0,0,0,.08); border-top: 4px solid {PURPLE}; }}
  .kpi-label {{ font-size: 11px; color: #666; text-transform: uppercase; letter-spacing: .5px; }}
  .kpi-value {{ font-size: 32px; font-weight: 700; color: {PURPLE}; margin-top: 6px; }}
  .kpi-sub {{ font-size: 12px; color: #888; margin-top: 4px; }}
  .section {{ background: #fff; border-radius: 10px; padding: 22px 24px; margin-bottom: 24px; box-shadow: 0 1px 4px rgba(0,0,0,.08); }}
  .section-title {{ font-size: 16px; font-weight: 700; color: {PURPLE}; margin-bottom: 16px; border-bottom: 2px solid #f0e6f7; padding-bottom: 8px; }}
  .chart-row {{ display: grid; grid-template-columns: 1fr 1fr; gap: 32px; }}
  .chart-wrap {{ position: relative; }}
  .chart-sub {{ font-size: 12px; color: #666; margin-top: 8px; text-align: center; }}
  .mc-bar-wrap {{ margin-top: 8px; }}
  .mc-bar-label {{ font-size: 12px; color: #444; display: flex; justify-content: space-between; margin-bottom: 4px; }}
  .mc-bar-bg {{ background: #eee; border-radius: 4px; height: 18px; margin-bottom: 8px; }}
  .mc-bar {{ background: {TEAL}; height: 18px; border-radius: 4px; display: flex; align-items: center; padding-left: 6px; color: #fff; font-size: 11px; font-weight: 600; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  th {{ background: {PURPLE}; color: #fff; padding: 8px 10px; text-align: left; font-weight: 600; font-size: 12px; }}
  td {{ padding: 7px 10px; border-bottom: 1px solid #f0f0f0; }}
  tr:hover td {{ background: #faf5ff; }}
  td.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
  td.center {{ text-align: center; }}
  td.warn {{ color: #c62828; font-weight: 600; }}
  td.muted {{ color: #999; font-style: italic; }}
  .badge {{ display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: 600; }}
  .badge-great {{ background: #c8e6c9; color: #1b5e20; }}
  .badge-good {{ background: #dcedc8; color: #33691e; }}
  .badge-fair {{ background: #fff9c4; color: #f57f17; }}
  .badge-high {{ background: #ffe0b2; color: #e65100; }}
  .badge-over {{ background: #ffcdd2; color: #b71c1c; }}
  .badge-nb {{ background: #eeeeee; color: #555; }}
  .callout {{ background: #fff3e0; border-left: 4px solid #c62828; border-radius: 4px; padding: 12px 16px; margin-top: 16px; font-size: 13px; }}
  .callout strong {{ color: #c62828; }}
  .teal {{ color: {TEAL}; }}
  .footnote {{ font-size: 11px; color: #aaa; margin-top: 20px; text-align: center; }}
  .print-data {{ display: none; }}
  .no-print {{ }}
  @media (max-width: 768px) {{
    .kpi-grid {{ grid-template-columns: 1fr 1fr; }}
    .chart-row {{ grid-template-columns: 1fr; }}
  }}
  @media print {{
    body {{ background: #fff !important; }}
    .header {{ background: {PURPLE} !important; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
    th {{ background: #f0e6f7 !important; color: #333 !important; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
    .section {{ box-shadow: none !important; border: 1px solid #eee; page-break-inside: avoid; }}
    .kpi-grid {{ page-break-inside: avoid; }}
    canvas {{ display: none !important; }}
    .print-data {{ display: block !important; }}
    .no-print {{ display: none !important; }}
    .kpi-value {{ font-size: 24px !important; }}
  }}
</style>
</head>
<body>
<div class="header">
  <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:12px;">
    <div>
      <h1>{dealer_name} — Cars.com Performance Overview</h1>
      <p>Period: {profile['period_label']} &nbsp;|&nbsp; Generated: {today_str}</p>
    </div>
    <div style="text-align:right; padding-top:4px;">
      {_logo_svg}
    </div>
  </div>
</div>

<nav id="stickyNav" style="display:none; position:sticky; top:0; z-index:100; background:#fff; border-bottom:2px solid #f0e6f7; padding:8px 20px; box-shadow:0 2px 8px rgba(0,0,0,.08);" class="no-print">
  <div style="max-width:1280px; margin:0 auto; display:flex; gap:20px; align-items:center; font-size:12px; font-weight:600;">
    <span style="color:{PURPLE}; font-weight:700;">{profile['nav_short_label']}</span>
    <a href="#perfSection" style="color:#555; text-decoration:none;">&#x1F4CA; Performance</a>
    <a href="#pricingSection" style="color:#555; text-decoration:none;">&#x1F3F7; Pricing</a>
    <a href="#mktShareSection" style="color:#555; text-decoration:none;">&#x1F4C8; Market Share</a>
    <a href="#compSection" style="color:#555; text-decoration:none;">&#x1F3C1; Competitive</a>
    <a href="#nextStepsSection" style="color:#555; text-decoration:none;">&#x2705; Next Steps</a>
    <button onclick="window.print()" style="margin-left:auto; background:{PURPLE}; color:#fff; border:none; padding:5px 12px; border-radius:4px; cursor:pointer; font-size:11px;" class="no-print">&#x1F5A8; Print / PDF</button>
  </div>
</nav>

<div class="container">

<!-- KPI Cards -->
<div class="kpi-grid">
  <div class="kpi-card">
    <div class="kpi-label">Fair, Good or Great Deal Badges</div>
    <div class="kpi-value teal">{round(used_b_pct):.0f}%</div>
    <div class="kpi-sub">{used_b_count} of {used_total} used vehicles</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-label">Good or Great Badges</div>
    <div class="kpi-value">{lei_stats['good_great_used_pct']:.0f}%</div>
    <div class="kpi-sub">{lei_stats['good_great_used_count']} of {lei_stats['total_used']} used vehicles</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-label">Priced At or Under Market</div>
    <div class="kpi-value teal">{kpi_under_at}</div>
    <div class="kpi-sub">Used vehicles only</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-label">{profile['franchise_short_label']} Franchise Lead Share</div>
    <div class="kpi-value">{lei_stats.get('franchise_lead_share', kpi_vdp_share)}</div>
    <div class="kpi-sub">Share of {profile['franchise_short_label']} franchise leads (7-day)</div>
  </div>
  <div class="kpi-card" style="border-top-color: #c62828;">
    <div class="kpi-label">Avg Days Live (Used)</div>
    <div class="kpi-value" style="color:#c62828;">{swh_perf_used_days:.0f}</div>
    <div class="kpi-sub">&#x26A0; {round(swh_perf_used_days/profile['franchise_avg_days_benchmark'], 1)}x above franchise avg ({profile['franchise_avg_days_benchmark']} days)</div>
  </div>
</div>

<!-- PERFORMANCE: VDP & Connection Performance (first) -->
{_build_connections_section(perf, profile, PURPLE, TEAL) if perf else ''}

<!-- PERFORMANCE: Inventory Metrics -->
<div class="section">
  <div class="section-title">Inventory Performance</div>
  {_build_engagement_tiles(swh_perf, lei_stats, profile, PURPLE, TEAL, perf=perf)}
</div>

<!-- OPTIMIZATION: Price Badge Analysis -->
<div class="section" id="pricingSection">
  <div class="section-title">Price Badge Optimization</div>
  <div class="chart-row">
    <div>
      <strong style="font-size:13px;">Cars.com Price Badge Distribution</strong>
      <div class="chart-wrap" style="height:220px; margin-top:12px;">
        <canvas id="badgeChart"></canvas>
        <div class="print-data" style="display:none; font-size:13px; color:#333;">
          {' | '.join(f'{k}: {v["count"]} ({v["pct"]:.1f}%)' for k, v in lei_stats['badge_dist'].items() if 'not badged' not in k.lower())}
        </div>
      </div>
    </div>
    <div>
      <strong style="font-size:13px;">Cars.com Price vs. Market <span style="font-size:11px; font-weight:400; color:#888;">(Used, {pc_u['total']} vehicles — At Market = 95–105% of avg, Under = &lt;95%)</span></strong>
      <div style="margin-top:12px;">
        <canvas id="priceChart" height="120"></canvas>
        <div class="print-data" style="display:none; font-size:13px; color:#333; margin-top:6px;">
          At or Under Market: {at_under_pct:.0f}% | Above Market: {pc_u['above']['pct']:.0f}%
        </div>
      </div>
    </div>
  </div>

  <div style="margin-top:24px;">
    <strong style="font-size:13px;">Badge Opportunities — Used Inventory Within $1,000 of Good or Great</strong>
    <p style="font-size:12px; color:#666; margin:6px 0 10px;">Used vehicles only. New inventory does not receive price badges on Cars.com.{f" {profile['franchise_short_label']} vehicles shown first," if franchise_makes else ''} Sorted by days live descending.</p>
    <div style="overflow-x:auto;">
      <table>
        <thead><tr><th>Vehicle</th><th>Stock #</th><th>Current Badge</th><th>Target</th><th>Drop Needed</th><th>Target Price</th><th>Days Live</th><th>VDPs (7d)</th></tr></thead>
        <tbody>{badge_top5_html}</tbody>
        <tbody id="badgeOppsExtra" style="display:none">{badge_extra_html}</tbody>
      </table>
    </div>
    <p style="font-size:12px; color:#666; margin-top:8px;">
      Showing top 5. <button onclick="var t=document.getElementById('badgeOppsExtra'); t.style.display=t.style.display===&#39;none&#39;?&#39;&#39;:&#39;none&#39;; this.textContent=t.style.display===&#39;&#39;?&#39;Show fewer&#39;:&#39;Show all {total_opps} vehicles ↓&#39;; trackCTA('badge_opps_show_all','inline-expand');" style="background:none; border:none; color:{PURPLE}; font-weight:600; cursor:pointer; font-size:12px; text-decoration:underline; padding:0;">Show all {total_opps} vehicles &#x2193;</button>
      {f'<a href="{profile["sheet_url"]}" style="display:inline-block; margin-left:10px; background:#f0f0f0; color:#444; font-size:11px; font-weight:600; padding:3px 10px; border-radius:12px; text-decoration:none; border:1px solid #ddd;" target="_blank" data-cta="badge_opps_export_sheet" onclick="trackCTA(&#39;badge_opps_export_sheet&#39;, this.href)">↗ View in Google Sheet</a>' if profile['sheet_url'] else ''}
    </p>
  </div>
</div>

<!-- Market Share Table -->
<div class="section" id="mktShareSection">
  <div class="section-title">Market Share by Make / Model</div>
  {f'<div style="background:#fff3e0; border-left:4px solid #F9A825; border-radius:4px; padding:12px 16px; margin-bottom:16px; font-size:13px;"><strong>&#x26A0; Key Insight:</strong> Your used {profile["franchise_short_label"]} nameplates show significant VDP engagement gaps. Top gaps: {top_lr_gaps_str}. These are your highest-opportunity models for pricing and listing improvements. <em style="color:#888; font-size:11px;">Percentage point gap abbreviated as &ldquo;pp&rdquo; throughout.</em></div>' if show_lr_gap_callout else ''}
  <div style="margin-bottom:12px; display:flex; gap:8px; flex-wrap:wrap;" class="no-print">
    <button onclick="filterSignal('all')" id="sigAll" style="background:{PURPLE}; color:#fff; border:none; padding:6px 12px; border-radius:16px; font-size:12px; cursor:pointer;">All ({total_mkt_rows})</button>
    <button onclick="filterSignal('gap')" id="sigGap" style="background:#f0f0f0; color:#555; border:none; padding:6px 12px; border-radius:16px; font-size:12px; cursor:pointer;">&#x1F534; Gaps only ({red_count})</button>
    <button onclick="filterSignal('win')" id="sigWin" style="background:#f0f0f0; color:#555; border:none; padding:6px 12px; border-radius:16px; font-size:12px; cursor:pointer;">&#x1F7E2; Outperforming ({green_count})</button>
    <button onclick="filterNewUsed('all')" id="typeAll" style="background:{PURPLE}; color:#fff; border:none; padding:6px 12px; border-radius:16px; font-size:12px; cursor:pointer;">New + Used</button>
    <button onclick="filterNewUsed('Used')" id="typeUsed" style="background:#f0f0f0; color:#555; border:none; padding:6px 12px; border-radius:16px; font-size:12px; cursor:pointer;">Used only</button>
  </div>
  <div style="overflow-x:auto;">
    <table id="mktShareTable">
      <thead>
        <tr>
          <th>Make / Model</th>
          <th>Type</th>
          <th>Vehicle Share %</th>
          <th>VDP Share %</th>
          <th>Connection Share %</th>
          <th>Signal</th>
          <th>Note</th>
        </tr>
      </thead>
      <tbody>
        {share_rows_html}
      </tbody>
    </table>
  </div>
  <p style="font-size:11px; color:#888; margin-top:8px;">&#x1F7E2; VDP share &gt; vehicle share (outperforming) &nbsp;|&nbsp; &#x1F7E1; near parity &nbsp;|&nbsp; &#x1F534; VDP share &lt; vehicle share (gap)</p>
</div>

<!-- Competitive Context -->
<div class="section" id="compSection">
  <div class="section-title">Competitive Inventory Landscape{f" — {profile['market_area']} {profile['franchise_short_label']} Franchise Stores" if profile['market_area'] else ''}</div>
  <p style="font-size:13px; color:#444; line-height:1.6; margin-bottom:12px;">
  </p>
  <div style="overflow-x:auto;">
    <table>
      <thead><tr><th>Rank</th><th>Dealer</th><th>Used Vehicles Eligible</th><th>Within $1k of Badge Upgrade</th><th>% Within $1k <small style="font-weight:400;">(↑ = more need repricing)</small></th><th>Avg Price-to-Market</th><th>Avg Days Live</th></tr></thead>
      <tbody>{comp_rows_html if comp_rows_html else '<tr><td colspan="7" class="muted center">No comparable competitor data found</td></tr>'}</tbody>
    </table>
  </div>
</div>

<!-- Recommended Next Steps -->
<div class="section" id="nextStepsSection" style="background: linear-gradient(135deg, #f0e6f7 0%, #e6f7f5 100%); border-left: 5px solid {PURPLE};">
  <div class="section-title">Recommended Next Steps</div>
  <ol style="font-size:14px; line-height:2.2; color:#333; margin:0; padding-left:20px;">
    <li><strong>Reprice {badge_opp_count} vehicles within $1,000 of a badge tier</strong> &#x2014; average drop needed: {avg_drop_str}.
        {f'<a href="{profile["sheet_url"]}" style="display:inline-block; background:{TEAL}; color:#fff; padding:4px 14px; border-radius:12px; text-decoration:none; font-weight:600; font-size:13px; margin-left:6px;" target="_blank" data-cta="next_steps_reprice_list" onclick="trackCTA(&#39;next_steps_reprice_list&#39;, this.href)">↗ View Repricing List</a>' if profile['sheet_url'] else ''}</li>
    <li><strong>Review the {above_mkt_count} vehicles priced above market</strong> &#x2014; {above_mkt_count} units ({price_above_pct:.0f}% of used inventory) are suppressing badge coverage and search ranking.</li>
    <li><strong>Target used inventory under 90 days</strong> &#x2014; current avg is {used_days:.0f} days vs. franchise benchmark ~{profile['franchise_avg_days_benchmark']} days. Pricing precision unlocks badges and accelerates turn.</li>
  </ol>
  <p style="margin-top:16px; font-size:13px; color:#555;">
    <strong>Ready to walk through this together?</strong>
    <a href="mailto:jcrawley@cars.com?subject={quote(f'Re: {dealer_name} — Cars.com Performance Overview')}&body={quote('Hi Jake,' + chr(10)*2 + 'I reviewed the performance report and would like to schedule a call to discuss the pricing opportunities and badge optimization recommendations.' + chr(10)*2 + 'Please let me know your availability.' + chr(10)*2 + 'Best regards')}" style="display:inline-block; margin-left:8px; background:{PURPLE}; color:#fff; padding:8px 18px; border-radius:4px; text-decoration:none; font-weight:600; font-size:13px;" data-cta="next_steps_schedule_call" onclick="trackCTA('next_steps_schedule_call', this.href)">Schedule a Review Call →</a>
  </p>
</div>

<p class="footnote">Cars.com data: {today_str} | {profile['period_label']}</p>
<details style="margin-top:12px; font-size:11px; color:#888; max-width:800px; margin-left:auto; margin-right:auto;" class="no-print">
  <summary style="cursor:pointer; font-weight:600; color:#666;">&#x2139; Glossary &amp; Data Sources</summary>
  <div style="margin-top:8px; line-height:1.8;">
    <strong>VDP</strong> (Vehicle Detail Page) &#x2014; a shopper view of a specific vehicle listing on Cars.com.<br>
    <strong>LEI</strong> (Low Engagement Inventory) &#x2014; Cars.com quality score identifying listings with below-average shopper engagement relative to market peers.<br>
    <strong>Connections</strong> &#x2014; all shopper contact types: phone leads, email leads, chat leads, web transfers, VDP deep links, map views. Excludes Instant Offer - Cars.com (AccuTrade).<br>
    <strong>Price Badge</strong> &#x2014; Cars.com deal rating (Great Deal, Good Deal, Fair Deal) based on price relative to local market average, days on lot, and demand signals.<br>
    <strong>At Market</strong> &#x2014; priced 95&#x2013;105% of local market average. <strong>Under Market</strong> &#x2014; priced below 95%. <strong>Above Market</strong> &#x2014; priced above 105%.<br>
    <strong>Sources:</strong> VDPs &amp; Connections from admin.cars.com Performance Trends ({profile['period_label']}). Badge data from Cars.com LEI export. Price comparison from admin.cars.com Demand Signals export. Market share from admin.cars.com Market Comparison export.
  </div>
</details>

</div><!-- /container -->

<script>
const badgeData  = {badge_json};
const priceData  = {price_json};
const ggPct      = {round(lei_stats['good_great_used_pct']):.0f};

Chart.defaults.font.family = "'Poppins', 'Segoe UI', Arial, sans-serif";
Chart.defaults.font.size   = 12;
Chart.defaults.plugins.legend.position = 'right';

// M1: badgeChart center label plugin
const centerLabelPlugin = {{
  id: 'centerLabel',
  beforeDraw(chart) {{
    const {{ctx, chartArea: {{width, height, left, top}}}} = chart;
    const cx = left + width/2, cy = top + height/2;
    ctx.save();
    ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    ctx.font = "bold 22px 'DM Sans', -apple-system, Arial";
    ctx.fillStyle = '{PURPLE}';
    ctx.fillText(ggPct + '%', cx, cy-10);
    ctx.font = "11px 'DM Sans', -apple-system, Arial";
    ctx.fillStyle = '#888';
    ctx.fillText('Good+Great', cx, cy+12);
    ctx.restore();
  }}
}};

new Chart(document.getElementById('badgeChart'), {{
  type: 'doughnut',
  data: {{ labels: badgeData.labels, datasets: [{{ data: badgeData.data, backgroundColor: badgeData.colors, borderWidth: 1 }}] }},
  options: {{ cutout: '60%', plugins: {{ legend: {{ position: 'right', labels: {{ boxWidth: 12 }} }} }} }},
  plugins: [centerLabelPlugin]
}});

// priceChart — shorter labels, % and vehicle count in tooltip
new Chart(document.getElementById('priceChart'), {{
  type: 'bar',
  data: {{
    labels: priceData.labels,
    datasets: [{{ data: priceData.data, backgroundColor: priceData.colors, borderRadius: 6, barThickness: 40 }}]
  }},
  options: {{
    indexAxis: 'y',
    layout: {{ padding: {{ left: 10 }} }},
    plugins: {{
      legend: {{ display: false }},
      tooltip: {{ callbacks: {{ label: ctx => ' ' + ctx.raw + '% of used inventory (182 vehicles)' }} }}
    }},
    scales: {{
      x: {{ max: 100, ticks: {{ callback: v => v + '%' }}, grid: {{ color: '#f0f0f0' }} }},
      y: {{
        grid: {{ display: false }},
        ticks: {{ font: {{ size: 13, weight: '700' }}, color: '#333' }},
        afterFit(axis) {{ axis.width = 150; }}
      }}
    }}
  }}
}});

{month_charts_js}

// H6: Market share signal filter
function filterSignal(s) {{
  var active = '{PURPLE}', inactive = '#f0f0f0', activeT = '#fff', inactiveT = '#555';
  ['sigAll','sigGap','sigWin'].forEach(function(id) {{
    var btn = document.getElementById(id);
    if (!btn) return;
    var match = (id==='sigAll'&&s==='all')||(id==='sigGap'&&s==='gap')||(id==='sigWin'&&s==='win');
    btn.style.background = match ? active : inactive;
    btn.style.color = match ? activeT : inactiveT;
  }});
  document.querySelectorAll('#mktShareTable tr[data-signal]').forEach(function(r) {{
    r.style.display = (s==='all' || r.dataset.signal===s) ? '' : 'none';
  }});
}}
function filterNewUsed(t) {{
  var active = '{PURPLE}', inactive = '#f0f0f0', activeT = '#fff', inactiveT = '#555';
  ['typeAll','typeUsed'].forEach(function(id) {{
    var btn = document.getElementById(id);
    if (!btn) return;
    var match = (id==='typeAll'&&t==='all')||(id==='typeUsed'&&t==='Used');
    btn.style.background = match ? active : inactive;
    btn.style.color = match ? activeT : inactiveT;
  }});
  document.querySelectorAll('#mktShareTable tr[data-stype]').forEach(function(r) {{
    r.style.display = (t==='all' || r.dataset.stype===t) ? '' : 'none';
  }});
}}

// M3: Sticky nav appears after header scrolls out
var headerEl = document.querySelector('.header');
var navEl = document.getElementById('stickyNav');
if (headerEl && navEl) {{
  var obs = new IntersectionObserver(function(entries) {{
    navEl.style.display = entries[0].isIntersecting ? 'none' : 'block';
  }}, {{threshold: 0}});
  obs.observe(headerEl);
}}

// ── CTA Click Tracking ──────────────────────────────────────
function trackCTA(label, url) {{
  var ts = new Date().toISOString();
  var payload = {{ event: 'cta_click', label: label, url: url, ts: ts, dealer: '{dealer_name}', period: {json.dumps(profile['period_label'])} }};
  // Console log for debugging
  console.log('[Cars.com CTA]', payload);
  // Fire custom DOM event (can be intercepted by any analytics layer)
  document.dispatchEvent(new CustomEvent('cars_cta_click', {{ detail: payload }}));
  // Optional: beacon to tracking endpoint if configured
  if (window.CTA_ENDPOINT) {{
    navigator.sendBeacon(window.CTA_ENDPOINT, JSON.stringify(payload));
  }}
  // Optional: Google Analytics / gtag
  if (typeof gtag !== 'undefined') {{
    gtag('event', 'cta_click', {{ event_category: 'dealer_report', event_label: label, value: 1 }});
  }}
}}
// Wire trackCTA to all CTA links on page load
document.addEventListener('DOMContentLoaded', function() {{
  document.querySelectorAll('a[data-cta]').forEach(function(el) {{
    el.addEventListener('click', function() {{
      trackCTA(el.getAttribute('data-cta'), el.href);
    }});
  }});
}});
</script>
</body>
</html>"""
    return html


# ── Gmail ─────────────────────────────────────────────────────────────────────

def get_gmail_service():
    with open(TOKEN_GMAIL) as f:
        token_data = json.load(f)
    with open(CLIENT_SECRETS) as f:
        secrets = json.load(f)
    client_cfg = secrets.get('installed') or secrets.get('web') or {}
    creds = Credentials(
        token=token_data['access_token'],
        refresh_token=token_data['refresh_token'],
        token_uri='https://oauth2.googleapis.com/token',
        client_id=client_cfg['client_id'],
        client_secret=client_cfg['client_secret'],
        scopes=SCOPES_GMAIL,
    )
    if not creds.valid:
        creds.refresh(Request())
        token_data['access_token'] = creds.token
        with open(TOKEN_GMAIL, 'w') as f:
            json.dump(token_data, f, indent=2)
    return build('gmail', 'v1', credentials=creds, cache_discovery=False)


def create_draft(gmail, lei_stats, price_stats, mkt_share_df, report_path, today_str, profile, send=False):
    """Create Gmail draft to Jake (pre-send rule: current client)."""
    dealer_name = profile['dealer_display']
    period_label = profile['period_label']

    # Build insight lead
    gg_pct  = lei_stats['good_great_pct']
    at_pct  = price_stats['at']['pct']
    und_pct = price_stats['under']['pct']
    above_n = price_stats['above']['count']
    total_v = lei_stats['total_vehicles']

    # Find the make with worst connection share (gap opportunity)
    gap_make = ''
    if not mkt_share_df.empty and 'conn_share_pct' in mkt_share_df.columns and 'vehicle_share_pct' in mkt_share_df.columns:
        gaps = mkt_share_df[mkt_share_df['vehicle_share_pct'] > 0].copy()
        gaps['gap_ratio'] = gaps['conn_share_pct'] / gaps['vehicle_share_pct'].replace(0, 1)
        worst = gaps.sort_values('gap_ratio').iloc[0] if not gaps.empty else None
        if worst is not None:
            make  = worst.get('make', '')
            model = worst.get('model', '')
            gap_make = f"{make} {model}".strip()

    period_tag = profile['quarter_label'] or period_label
    subject = f"{dealer_name} — Market Analysis | {period_tag}"
    body = f"""\
<html><body>
<p>Hi Jake,</p>

<p>Here's the {period_tag} market analysis for <strong>{dealer_name}</strong>.</p>

<p>On Cars.com, <strong>{gg_pct}% of their listed inventory carries a Good or Great badge</strong>
across {total_v} vehicles in the LEI — and <strong>{at_pct + und_pct:.0f}% is priced at or under market</strong>.
That's strong pricing discipline, though {above_n} vehicles are still priced above market
and aging past 30 days on lot — those are the reprice candidates flagged in the report.</p>

{f'<p>One notable gap: <strong>{gap_make}</strong> shows a connection share well below its vehicle share — meaning shoppers are finding but not engaging with those vehicles. Worth a conversation about listing quality and pricing for that segment.</p>' if gap_make else ''}

<p>The full analysis is in the attached HTML report, combining Cars.com LEI/market share data with
their CarGurus 90-day dashboard ({period_label}).</p>

<p>Report file: <code>{report_path.name}</code></p>

<p>Cheers,<br>Jake</p>
</body></html>"""

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From']    = 'jcrawley@carscommerce.inc'
    msg['To']      = 'jcrawley@cars.com'
    msg.attach(MIMEText(body, 'html'))

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    draft = gmail.users().drafts().create(userId='me', body={'message': {'raw': raw}}).execute()
    draft_id = draft['id']
    print(f"  ✓ Gmail draft created (id: {draft_id})")

    if send:
        result = gmail.users().drafts().send(userId='me', body={'id': draft_id}).execute()
        print(f"  ✓ Email sent (message id: {result['id']})")
    return draft_id


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='Dealer Market Analysis Report')
    parser.add_argument('--profile',      default=None,  help=f"Built-in profile name. Available: {', '.join(PROFILES)}")
    parser.add_argument('--profile-json', default=None,  help='Path to a JSON profile for a dealer with no built-in profile')
    parser.add_argument('--lei',          required=True, help='Market LEI CSV (all dealers)')
    parser.add_argument('--market-share', required=True, help='Market Share Comparison CSV')
    parser.add_argument('--price-comp',   required=True, help='Price Comparison CSV')
    parser.add_argument('--cargurus',     required=True, help='CarGurus HTML dashboard file')
    parser.add_argument('--perf',         default=None,  help='admin.cars.com inventory performance export CSV')
    parser.add_argument('--dealer',       default=None,  help='Dealer name substring (default: auto-detect from profile)')
    parser.add_argument('--no-draft',     action='store_true', help='Skip Gmail draft')
    parser.add_argument('--send',         action='store_true', help='Send email after draft creation')
    args = parser.parse_args()

    profile = load_profile(name=args.profile, json_path=args.profile_json)

    today_str = date.today().strftime('%-m/%-d/%Y')
    today_file = date.today().strftime('%Y-%m-%d')

    print(f"\n{'='*60}")
    print(f"{profile['dealer_display']} Market Report — {today_str}")
    print(f"{'='*60}\n")

    # ── Step 1: Parse all inputs ──
    print("[1/5] Parsing input files...")
    dealer_df, market_df, dealer_name = load_lei(
        os.path.expanduser(args.lei), profile, dealer_hint=args.dealer
    )
    mkt_share_df = load_market_share(os.path.expanduser(args.market_share))
    price_stats, price_stats_used, reprice, price_df = load_price_comparison(os.path.expanduser(args.price_comp))
    cg = parse_cargurus_html(os.path.expanduser(args.cargurus), profile)
    perf_dealer_hint = profile['perf_csv_dealer_hint'] or dealer_name
    swh_perf = load_swh_perf(os.path.expanduser(args.perf), perf_dealer_hint) if args.perf else None
    if swh_perf is None:
        print("  ⚠ No perf CSV provided — engagement section will use 7-day LEI data")
    perf = load_perf_trends(profile)

    # ── Step 2: Compute stats ──
    print("\n[2/5] Computing stats...")
    lei_stats = compute_lei_stats(dealer_df, market_df, profile, dealer_name, price_df=price_df)
    print(f"  ✓ {lei_stats['total_vehicles']} unique vehicles | Good/Great/Fair: {lei_stats['good_great_pct']}% ({lei_stats['good_great_count']}) | Avg days: {lei_stats['avg_days']}")
    print(f"  ✓ Price position — Under: {price_stats['under']['pct']}% | At: {price_stats['at']['pct']}% | Above: {price_stats['above']['pct']}%")

    # ── Step 3: Generate HTML ──
    print("\n[3/5] Generating HTML report...")
    output_dir = Path.home() / "Documents" / "Reports" / profile['output_dir_name']
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{_slugify(dealer_name)}_market_report_{today_file}.html"
    html = generate_html(dealer_name, lei_stats, mkt_share_df, price_stats, reprice, cg, today_str, profile,
                         swh_perf=swh_perf, perf=perf, price_stats_used=price_stats_used)
    output_path.write_text(html, encoding='utf-8')
    print(f"  ✓ Report saved: {output_path}")

    # ── Step 4: Gmail draft ──
    if not args.no_draft:
        print("\n[4/5] Creating Gmail draft...")
        try:
            gmail = get_gmail_service()
            create_draft(gmail, lei_stats, price_stats, mkt_share_df, output_path, today_str, profile, send=args.send)
        except Exception as e:
            print(f"  ⚠ Gmail failed: {e}")
            print("  Check ~/.claude/tokens/gmail_jcrawley.json and ~/gcp-oauth.keys.json")
    else:
        print("\n[4/5] Skipping Gmail draft (--no-draft)")

    # ── Step 5: Summary ──
    print(f"\n[5/5] Done.")
    print(f"  Report: {output_path}")
    print(f"  Open:   open '{output_path}'")
    print()


if __name__ == '__main__':
    main()
