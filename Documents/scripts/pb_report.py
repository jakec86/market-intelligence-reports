#!/usr/bin/env python3
"""
Price Badge Report — automated sheet import, sort, stats, and Gmail draft.

Usage:
    python3 pb_report.py --dealer nalley --lei ~/Documents/Tableau/nalley_lei.csv
    python3 pb_report.py --dealer nalley --lei lei.csv --dem dem_signal.csv
    python3 pb_report.py --dealer hendrick --lei ~/Documents/Tableau/hendrick_lei.csv
    python3 pb_report.py --dealer nalley --stats-only   # skip import, just sort + draft

Steps handled:
  1. Parse LEI CSV (+ Dem Signal CSV for Nalley) and push to Google Sheet
  2. Safe-sort PBT tab by column J ascending (data range only — never header)
  3. Read J1 stat + count vehicles within threshold
  4. Compose Gmail draft with hyperlinked "Price Badge Report"
"""

import argparse, codecs, csv, io, json, os, sys, time, base64, re
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from collections import Counter

import gspread.exceptions

import gspread
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# ─── CONFIG ──────────────────────────────────────────────────────────────────

SCOPES_SHEETS = ["https://www.googleapis.com/auth/spreadsheets"]
SCOPES_GMAIL  = [
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.modify",
]
TOKEN_SHEETS   = os.path.expanduser("~/.claude/tokens/sheets_token.json")
TOKEN_GMAIL    = os.path.expanduser("~/.claude/tokens/gmail_jcrawley.json")
CLIENT_SECRETS = os.path.expanduser("~/gcp-oauth.keys.json")

DEALERS = {
    "hendrick": {
        "sheet_id": "1guqWV9HFb2MijC7qQ7qinL4oljbu0N1o9TU5zcmy3GM",
        "import_tab": "Data Import_Inventory Report",
        "pbt_tab": "Price Badge Tool",
        "dem_signal_tab": None,
        "col_reorder": False,
        "sort_range": "A3:J5000",   # Hendrick: R1=threshold, R2=headers, data R3+, K deleted
        "sort_col": 10,             # Column J (1-indexed in gspread)
        "data_start_row": 3,
        "threshold_cell": "E1",
        "pct_cell": "J1",
        "stock_col": "D",
        "sheet_url": "https://docs.google.com/spreadsheets/d/1guqWV9HFb2MijC7qQ7qinL4oljbu0N1o9TU5zcmy3GM/edit?gid=565895707#gid=565895707",
        "email_to": "anne.Lewis@hendrickauto.com",
        "email_subject": "Re: Cars.com: Price Badge Report",
        "email_from": "jcrawley@carscommerce.inc",
        "display_name": "Hendrick Automotive Group",
        "has_dem_signal": False,
        "callout_style": "sam",
        "pbt_store_col": 1,    # col B = Store name
        "pbt_vehicle_col": 2,  # col C = Vehicle (MMYT)
    },
    "nalley": {
        "sheet_id": "13Jn8vJSG7vRYW9xpuxrMi9kXNhiV_TaCrjQ5lNQRPP8",
        "import_tab": "Data Import_Inventory Report",
        "pbt_tab": "Price Badge Tool",
        "dem_signal_tab": "Data Import_Dem Signal - $ Comp",
        "col_reorder": False,       # LEI CSV now: Dealer,id,Stock,VIN,Make,YMMT — matches sheet, no reorder
        "sort_range": "A4:L5000",   # Nalley: header row 3, data starts row 4
        "sort_col": 10,
        "data_start_row": 4,
        "threshold_cell": "E1",
        "pct_cell": "J1",
        "stock_col": "D",
        "sheet_url": "https://docs.google.com/spreadsheets/d/13Jn8vJSG7vRYW9xpuxrMi9kXNhiV_TaCrjQ5lNQRPP8/edit?gid=565895707#gid=565895707",
        "email_to": "gcaudill1@nalleycars.com, jbrown1@nalleycars.com, zibrahimbegovic@asburyauto.com, rsaeed@nalleycars.com",
        "email_cc": "sdharanendra@asburyauto.com",
        "email_subject": f"Nalley Lexus Galleria — Price Badge Report {date.today().strftime('%-m.%-d.%y')}",
        "email_from": "jcrawley@cars.com",
        "display_name": "Nalley Lexus Galleria",
        "has_dem_signal": True,
        "callout_style": "mmyt",
        "pbt_store_col": None,  # Nalley has no SAM/Store col — single dealer
        "pbt_vehicle_col": 1,   # col B = MMYT
    },
    "dyer": {
        "sheet_id": "1TWMwKUnntKZpjQDX6rbrScDHHfV5jQisG1EIAwIFwC8",
        "import_tab": "Data Import_Inventory Report",
        "pbt_tab": "Price Badge Tool",
        "dem_signal_tab": "Data Import_Dem Signal - $ Comp",
        "col_reorder": False,
        "sort_range": "A4:L5000",
        "sort_col": 10,
        "data_start_row": 4,
        "threshold_cell": "E1",
        "pct_cell": "J1",
        "stock_col": "D",
        "sheet_url": "https://docs.google.com/spreadsheets/d/1TWMwKUnntKZpjQDX6rbrScDHHfV5jQisG1EIAwIFwC8/edit?gid=565895707#gid=565895707",
        "email_to": "",
        "email_subject": f"Dyer & Dyer Volvo Cars — Price Badge Report {date.today().strftime('%-m.%-d.%y')}",
        "email_from": "jcrawley@cars.com",
        "display_name": "Dyer & Dyer Volvo Cars",
        "has_dem_signal": True,
    },
}


# ─── AUTH ────────────────────────────────────────────────────────────────────

def get_sheets_client():
    creds = None
    if os.path.exists(TOKEN_SHEETS):
        creds = Credentials.from_authorized_user_file(TOKEN_SHEETS, SCOPES_SHEETS)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            from google_auth_oauthlib.flow import InstalledAppFlow
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS, SCOPES_SHEETS)
            creds = flow.run_local_server(port=0)
        os.makedirs(os.path.dirname(TOKEN_SHEETS), exist_ok=True)
        with open(TOKEN_SHEETS, "w") as f:
            f.write(creds.to_json())
    from gspread.http_client import BackOffHTTPClient
    return gspread.Client(auth=creds, http_client=BackOffHTTPClient)


def get_gmail_service():
    with open(TOKEN_GMAIL) as f:
        token_data = json.load(f)
    with open(CLIENT_SECRETS) as f:
        secrets = json.load(f)
    client_config = secrets.get("installed") or secrets.get("web") or {}
    creds = Credentials(
        token=token_data["access_token"],
        refresh_token=token_data["refresh_token"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_config["client_id"],
        client_secret=client_config["client_secret"],
        scopes=SCOPES_GMAIL,
    )
    if not creds.valid:
        creds.refresh(Request())
        token_data["access_token"] = creds.token
        with open(TOKEN_GMAIL, "w") as f:
            json.dump(token_data, f, indent=2)
    return build("gmail", "v1", credentials=creds)


# ─── CSV PARSING ─────────────────────────────────────────────────────────────

# Expected column headers — abort if the Tableau export format has changed
_LEI_EXPECTED = ["Dealer name", "Dealer id", "Stock num", "VIN", "Make name"]
_DEM_EXPECTED = ["YMMT", "Stock num", "Stock type", "Days live", "Price",
                 "Price vs Market (%)", "Value"]


def read_csv_auto(path):
    """Read a CSV, auto-detecting UTF-16 vs UTF-8 encoding and tab vs comma delimiter."""
    raw = open(path, "rb").read(4)
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        text = codecs.open(path, encoding="utf-16").read()
    else:
        text = open(path, encoding="utf-8-sig").read()
    # Auto-detect delimiter from first line
    first_line = text.split("\n", 1)[0]
    delimiter = "\t" if "\t" in first_line else ","
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    rows = list(reader)
    return rows


def _validate_csv_headers(path, rows, expected, label):
    """Abort with a schema diff if the CSV header doesn't match expected columns."""
    if not rows:
        print(f"  ✗ {label} CSV is empty: {path}")
        sys.exit(1)
    actual = [str(c).strip() for c in rows[0]]
    missing = [c for c in expected if c not in actual]
    if missing:
        print(f"  ✗ {label} CSV schema mismatch — {path}")
        print(f"    Expected: {expected}")
        print(f"    Actual:   {actual}")
        print(f"    Missing cols: {missing}")
        sys.exit(1)
    print(f"  ✓ {label} CSV schema OK ({len(actual)} columns)")


def reorder_nalley_columns(rows):
    """Swap columns C/D/E: CSV has Make,Stock,VIN → Sheet expects Stock,VIN,Make."""
    reordered = []
    for row in rows:
        if len(row) >= 5:
            new_row = row[:2] + [row[3], row[4], row[2]] + row[5:]
            reordered.append(new_row)
        else:
            reordered.append(row)
    return reordered


# ─── SHEET OPERATIONS ────────────────────────────────────────────────────────

def _sort_with_retry(ws, spec, range_str, max_attempts=4, base_wait=20):
    """Wrap gspread sort() with retry on 503 — batchUpdate/sortRange is flaky."""
    for attempt in range(1, max_attempts + 1):
        try:
            ws.sort(spec, range=range_str)
            return
        except gspread.exceptions.APIError as e:
            if "503" in str(e) and attempt < max_attempts:
                wait = base_wait * attempt
                print(f"  ⚠ Sort 503 (attempt {attempt}/{max_attempts}), retrying in {wait}s...")
                time.sleep(wait)
            else:
                raise


def _clean_numeric(val):
    """Strip $ and , from browser-formatted numbers (e.g. '-1,247' → '-1247', '$36,249' → '36249').
    Leaves non-numeric strings untouched so badge labels, stock nums, etc. are unaffected."""
    stripped = val.replace('$', '').replace(',', '').strip()
    try:
        float(stripped)
        return stripped
    except ValueError:
        return val


def _clean_rows(rows):
    """Apply _clean_numeric to all data cells (skip header row)."""
    if not rows:
        return rows
    return [rows[0]] + [[_clean_numeric(c) for c in row] for row in rows[1:]]


def import_to_sheet(gc, cfg, lei_rows, dem_rows=None):
    """Push CSV data to the Data Import tabs."""
    sh = gc.open_by_key(cfg["sheet_id"])

    # LEI → Data Import_Inventory Report
    ws_import = sh.worksheet(cfg["import_tab"])
    ws_import.clear()
    ws_import.update(_clean_rows(lei_rows), value_input_option="RAW")
    print(f"  ✓ Imported {len(lei_rows)-1} LEI rows to '{cfg['import_tab']}'")

    # Dem Signal (Nalley only)
    if dem_rows and cfg["dem_signal_tab"]:
        ws_dem = sh.worksheet(cfg["dem_signal_tab"])
        ws_dem.clear()
        ws_dem.update(dem_rows, value_input_option="RAW")
        print(f"  ✓ Imported {len(dem_rows)-1} Dem Signal rows to '{cfg['dem_signal_tab']}'")

    return sh


def safe_sort_pbt(sh, cfg):
    """Sort PBT: green (J ≤ threshold) at top by SAM A-Z, then non-green by SAM A-Z.

    4-pass sort — DATA RANGE ONLY, never the header:
      1. Push empty rows to bottom (Stock # desc)
      2. Sort all data by J ascending (green values to top)
      3. Sort green section by SAM A-Z
      4. Sort non-green section by SAM A-Z
    """
    pbt = sh.worksheet(cfg["pbt_tab"])
    sort_range = cfg["sort_range"]
    stock_col_idx = ord(cfg["stock_col"]) - 64  # e.g. D → 4
    data_start = cfg["data_start_row"]

    # Find actual data extent before any sort — avoids sending a 5000-row sort
    # request to the API (which 503s). Scan for the highest row with any data.
    all_stock = pbt.col_values(stock_col_idx)
    max_data_row = data_start
    for i, val in enumerate(all_stock[data_start - 1:], start=data_start):
        if val.strip():
            max_data_row = i
    data_end_col = sort_range.split(":")[1][0]  # e.g. "J" from "A3:J5000"
    actual_range = f"A{data_start}:{data_end_col}{max_data_row}"

    # Pass 1: push empty rows to the bottom (sort only actual extent)
    _sort_with_retry(pbt, (stock_col_idx, "des"), actual_range)
    print(f"  ✓ Pass 1: empty rows pushed to bottom ({actual_range})")

    # Find last data row (now contiguous after Pass 1)
    all_stock = pbt.col_values(stock_col_idx)
    last_data_row = data_start
    for i, val in enumerate(all_stock[data_start - 1:], start=data_start):
        if val.strip():
            last_data_row = i
        else:
            break

    data_count = last_data_row - data_start + 1

    # Pass 2: sort all data by J ascending (green to top)
    data_range = f"A{data_start}:{data_end_col}{last_data_row}"
    _sort_with_retry(pbt, (cfg["sort_col"], "asc"), data_range)
    print(f"  ✓ Pass 2: sorted {data_range} by J ascending")

    # Find boundary: last green row (J > 0 and J ≤ threshold)
    time.sleep(2)
    threshold_val = float(re.sub(r"[,$]", "", pbt.acell(cfg["threshold_cell"]).value))
    j_vals = pbt.get(f"J{data_start}:J{last_data_row}")
    last_green_row = data_start - 1
    for i, row in enumerate(j_vals, data_start):
        raw = row[0].strip() if row else ""
        if raw:
            try:
                val = float(re.sub(r"[,$]", "", raw))
                if 0 < val <= threshold_val:
                    last_green_row = i
                elif val > threshold_val:
                    break
                # val == 0: skip (exactly at threshold, not "within" range)
            except ValueError:
                break

    green_count = max(0, last_green_row - data_start + 1)
    non_green_start = last_green_row + 1

    # Pass 3: sort green section by SAM A-Z
    if green_count > 0:
        _sort_with_retry(pbt, (1, "asc"), f"A{data_start}:{data_end_col}{last_green_row}")
        print(f"  ✓ Pass 3: green section A{data_start}:{data_end_col}{last_green_row} sorted by SAM A-Z ({green_count} vehicles)")

    # Pass 4: sort non-green section by SAM A-Z
    if non_green_start <= last_data_row:
        _sort_with_retry(pbt, (1, "asc"), f"A{non_green_start}:{data_end_col}{last_data_row}")
        non_green_count = last_data_row - non_green_start + 1
        print(f"  ✓ Pass 4: non-green section A{non_green_start}:{data_end_col}{last_data_row} sorted by SAM A-Z ({non_green_count} vehicles)")

    print(f"  ✓ {data_count} total rows: {green_count} green at top, {data_count - green_count} below")
    return pbt


def format_pbt_price_column(sh, cfg):
    """Apply currency format ($#,##0) to the Price column (G) in PBT tab."""
    ws = sh.worksheet(cfg["pbt_tab"])
    data_start = cfg["data_start_row"]
    sh.batch_update({"requests": [{"repeatCell": {
        "range": {
            "sheetId": ws.id,
            "startRowIndex": data_start - 1,
            "endRowIndex": 200,
            "startColumnIndex": 6,
            "endColumnIndex": 7,
        },
        "cell": {"userEnteredFormat": {"numberFormat": {"type": "CURRENCY", "pattern": "$#,##0"}}},
        "fields": "userEnteredFormat.numberFormat",
    }}]})


def hide_import_tab(sh, cfg):
    """Hide the Data Import tab so the client-facing sheet is clean."""
    ws_import = sh.worksheet(cfg["import_tab"])
    sh.batch_update({
        "requests": [{
            "updateSheetProperties": {
                "properties": {
                    "sheetId": ws_import.id,
                    "hidden": True
                },
                "fields": "hidden"
            }
        }]
    })
    print(f"  ✓ Hidden tab '{cfg['import_tab']}'")


def _pick_top_vehicles(within_deduped, n=5):
    """Pick top N vehicles ensuring SAM diversity — one per SAM first, then fill."""
    seen_sams = set()
    diverse = []
    remainder = []
    for v in within_deduped:
        sam = v.get("sam", "")
        if sam and sam not in seen_sams:
            seen_sams.add(sam)
            diverse.append(v)
        else:
            remainder.append(v)
        if len(diverse) >= n:
            break
    # If fewer than n unique SAMs, fill with remainder (sorted by diff already)
    result = diverse + remainder
    return result[:n]


def read_stats(pbt, cfg):
    """Read key stats from the PBT tab for the email."""
    time.sleep(3)  # wait for formula recalc

    pct = pbt.acell(cfg["pct_cell"]).value or "0%"
    threshold = pbt.acell(cfg["threshold_cell"]).value or "$1,000"

    all_values = pbt.get_all_values()
    data_start = cfg["data_start_row"] - 1  # 0-indexed
    data_rows = [r for r in all_values[data_start:] if r[3].strip()]  # col D = Stock #

    total = len(data_rows)

    # Column indices (0-based): A=0 SAM, B=1 Store, C=2 Vehicle, G=6 Price,
    #   H=7 Current Badge, I=8 Next Badge, J=9 Diff
    at_threshold = []   # diff == $0: already qualify, no price drop needed
    within_threshold = []  # 0 < diff <= threshold: need a small price drop
    already_great = 0
    for r in data_rows:
        sam          = r[0].strip() if len(r) > 0 else ""
        vcol         = cfg.get("pbt_vehicle_col", 1)
        scol         = cfg.get("pbt_store_col")
        vehicle      = r[vcol].strip() if len(r) > vcol else ""
        store        = r[scol].strip() if scol is not None and len(r) > scol else ""
        vin          = r[2].strip() if len(r) > 2 else ""
        stock        = r[3].strip() if len(r) > 3 else ""
        price_raw    = r[6].strip() if len(r) > 6 else ""
        current_badge = r[7].strip() if len(r) > 7 else ""
        next_badge   = r[8].strip() if len(r) > 8 else ""
        diff_raw     = r[9].strip() if len(r) > 9 else ""

        if current_badge == "Great" and not next_badge:
            already_great += 1
        elif diff_raw:
            try:
                diff_val = float(re.sub(r"[,$]", "", diff_raw))
            except ValueError:
                continue  # skip non-numeric rows (e.g. header text from VLOOKUP)
            thresh_val = float(re.sub(r"[,$]", "", threshold))
            # Compute target price (what to reprice to for next badge)
            try:
                price_val = float(re.sub(r"[,$]", "", price_raw))
                target_price = f"${price_val - diff_val:,.0f}"
            except (ValueError, TypeError):
                target_price = ""
            if diff_val == 0.0:
                at_threshold.append({
                    "sam": sam, "store": store, "vehicle": vehicle,
                    "vin": vin, "stock": stock,
                    "diff": diff_raw, "current": current_badge, "next": next_badge,
                    "target_price": target_price,
                })
            elif 0 < diff_val <= thresh_val:
                within_threshold.append({
                    "sam": sam, "store": store, "vehicle": vehicle,
                    "vin": vin, "stock": stock,
                    "diff": diff_raw, "current": current_badge, "next": next_badge,
                    "target_price": target_price,
                })

    # Deduplicate by stock number (LEI CSV has multiple rows per vehicle)
    seen_stocks = set()
    within_deduped = []
    for v in within_threshold:
        stock = v.get("stock", "")
        if stock and stock in seen_stocks:
            continue
        if stock:
            seen_stocks.add(stock)
        within_deduped.append(v)

    seen_stocks_at = set()
    at_deduped = []
    for v in at_threshold:
        stock = v.get("stock", "")
        if stock and stock in seen_stocks_at:
            continue
        if stock:
            seen_stocks_at.add(stock)
        at_deduped.append(v)

    stats = {
        "pct": pct,
        "threshold": threshold,
        "total": total,
        "at_threshold_count": len(at_deduped),
        "at_threshold_vehicles": at_deduped,
        "within_count": len(within_deduped),
        "already_great": already_great,
        "top_vehicles": _pick_top_vehicles(within_deduped, n=5),
    }
    print(f"  ✓ Stats: {stats['within_count']}/{total} within {threshold} ({pct}), "
          f"{len(at_threshold)} at $0, {already_great} already Great")
    return stats


def read_dem_signal_stats(sh, cfg):
    """Read price comparison breakdown from Dem Signal tab (Nalley only)."""
    if not cfg["dem_signal_tab"]:
        return None
    try:
        ws = sh.worksheet(cfg["dem_signal_tab"])
        all_vals = ws.get_all_values()
        # Find the "Value" column (At Market / Above Market / Under Market)
        header = all_vals[0] if all_vals else []
        val_idx = None
        for i, h in enumerate(header):
            if "value" in h.lower():
                val_idx = i
                break
        if val_idx is None:
            return None

        categories = [r[val_idx].strip() for r in all_vals[1:] if len(r) > val_idx and r[val_idx].strip()]
        counts = Counter(categories)
        total = len(categories)
        if total == 0:
            return None

        at_mkt = sum(v for k, v in counts.items() if "at market" in k.lower() and "above" not in k.lower() and "under" not in k.lower())
        above  = sum(v for k, v in counts.items() if "above" in k.lower())
        under  = sum(v for k, v in counts.items() if "under" in k.lower())

        return {
            "at_market_pct": round(100 * at_mkt / total),
            "above_market_pct": round(100 * above / total),
            "under_market_pct": round(100 * under / total),
            "total": total,
        }
    except Exception as e:
        print(f"  ⚠ Dem Signal stats failed: {e}")
        return None


# ─── EMAIL DRAFT ─────────────────────────────────────────────────────────────

def compose_email_html(cfg, stats, dem_stats=None):
    """Build HTML email body with hyperlinked Price Badge Report."""
    top_vehicles_html = ""
    callout_style = cfg.get("callout_style", "sam")
    for v in stats["top_vehicles"]:
        price_note = f" &rarr; reprice to <b>{v['target_price']}</b>" if v.get("target_price") else f" &mdash; <b>{v['diff']}</b> from {v['next']}"
        if callout_style == "mmyt":
            vin_stk = ", ".join(filter(None, [v.get("vin"), v.get("stock")]))
            id_label = f" ({vin_stk})" if vin_stk else ""
            drop_note = f" &rarr; drop <b>{v['diff']}</b> for <b>{v['next']}</b>"
            top_vehicles_html += (
                f'<li><b>{v["vehicle"]}</b>{id_label}{drop_note}</li>\n'
            )
        else:
            store_label = f" / {v['store']}" if v.get("store") else ""
            top_vehicles_html += (
                f'<li><b>{v["sam"]}</b>{store_label} &mdash; {v["vehicle"]}{price_note} for <b>{v["next"]}</b></li>\n'
            )

    # $0 vehicles: already qualify, badge update pending on Cars.com side
    at_threshold_html = ""
    if stats.get("at_threshold_count", 0) > 0:
        names = ", ".join(f'<b>{v["mmyt"]}</b>' for v in stats["at_threshold_vehicles"])
        at_threshold_html = (
            f'<p>Additionally, <b>{stats["at_threshold_count"]} vehicle(s) already qualify '
            f'for a badge upgrade at their current price</b> &mdash; no action needed, '
            f'Cars.com will reflect the updated badge on the next cycle: {names}.</p>'
        )

    dem_paragraph = ""
    if dem_stats:
        dem_paragraph = (
            f'<p>From a broader pricing standpoint, your Demand Signals show '
            f'<b>{dem_stats["at_market_pct"]}% At Market</b>, '
            f'<b>{dem_stats["above_market_pct"]}% Above Market</b>, and '
            f'<b>{dem_stats["under_market_pct"]}% Under Market</b> &mdash; '
            f'majority of inventory is competitively positioned, though '
            f'nearly a third has room to sharpen up and capture more shopper attention.</p>'
        )

    html = f"""\
<html><body>
<p>Hi team,</p>

<p>Wanted to flag some quick wins sitting in your current inventory. This week,
<b>{stats["within_count"]} vehicles ({stats["pct"]} of your lot)</b> are within
{stats["threshold"]} of earning a Good or Great badge &mdash; a few are remarkably close:</p>

<ul>
{top_vehicles_html}
</ul>

{at_threshold_html}

<p>The full breakdown is in your
<a href="{cfg["sheet_url"]}">Price Badge Report</a>,
sorted by closest to upgrade at the top.
{f'{stats["already_great"]} vehicles are already sitting at Great.' if stats["already_great"] else ''}</p>

{dem_paragraph}

<p>Cheers,</p>

<p>Jake</p>
</body></html>
"""
    return html


def create_gmail_draft(gmail, cfg, html_body):
    """Create a Gmail draft with HTML body. Returns (draft_id, draft_object)."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = cfg["email_subject"]
    msg["From"] = cfg.get("email_from", "jcrawley@cars.com")
    if cfg.get("email_to"):
        msg["To"] = cfg["email_to"]
    if cfg.get("email_cc"):
        msg["Cc"] = cfg["email_cc"]
    msg.attach(MIMEText(html_body, "html"))

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    draft = gmail.users().drafts().create(
        userId="me", body={"message": {"raw": raw}}
    ).execute()
    draft_id = draft["id"]
    print(f"  ✓ Gmail draft created (id: {draft_id})")
    return draft_id, draft


def send_gmail_draft(gmail, draft_id):
    """Send an existing draft immediately."""
    result = gmail.users().drafts().send(
        userId="me", body={"id": draft_id}
    ).execute()
    print(f"  ✓ Email sent (message id: {result['id']})")
    return result["id"]


def qc_other_tabs(sh):
    """QC check: verify other tabs Anne may use have data and aren't blank."""
    tabs_to_check = [
        "Inventory Engagement",
        "Low Engaged Inventory",
        "Missing Features_AutoCorrected",
    ]
    print("  QC: checking other tabs...")
    issues = []
    for tab_name in tabs_to_check:
        try:
            ws = sh.worksheet(tab_name)
            all_vals = ws.get_all_values()
            data_rows = [r for r in all_vals[1:] if any(c.strip() for c in r)]
            row_count = len(data_rows)
            if row_count == 0:
                issues.append(f"⚠ '{tab_name}' appears empty (0 data rows)")
                print(f"    ⚠ '{tab_name}': EMPTY")
            else:
                print(f"    ✓ '{tab_name}': {row_count:,} rows")
        except Exception as e:
            issues.append(f"⚠ '{tab_name}' could not be read: {e}")
            print(f"    ⚠ '{tab_name}': error — {e}")
    if issues:
        print(f"  ⚠ QC issues found: {'; '.join(issues)}")
    else:
        print("  ✓ All tabs have data")
    return issues


# ─── MAIN ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Price Badge Report automation")
    parser.add_argument("--dealer", required=True, choices=DEALERS.keys())
    parser.add_argument("--lei", help="Path to LEI CSV file")
    parser.add_argument("--dem", help="Path to Demand Signals CSV file (Nalley only)")
    parser.add_argument("--stats-only", action="store_true",
                        help="Skip import, just sort + read stats + draft email")
    parser.add_argument("--no-draft", action="store_true",
                        help="Skip Gmail draft creation")
    parser.add_argument("--send", action="store_true",
                        help="Send the email immediately after draft creation")
    parser.add_argument("--to", metavar="EMAIL",
                        help="Override To: recipients (comma-separated)")
    parser.add_argument("--cc", metavar="EMAIL",
                        help="Override Cc: recipients (comma-separated)")
    parser.add_argument("--json-stats", metavar="FILE",
                        help="Write final stats as JSON to FILE (used by parallel runner)")
    args = parser.parse_args()

    cfg = DEALERS[args.dealer]
    today = date.today().strftime("%-m.%-d.%y")
    cfg["email_subject"] = f"{cfg['display_name']} — Price Badge Report {today}"

    print(f"\n{'='*60}")
    print(f"Price Badge Report — {cfg['display_name']} — {today}")
    print(f"{'='*60}\n")

    # Auth
    print("[1/6] Authenticating...")
    gc = get_sheets_client()
    sh = gc.open_by_key(cfg["sheet_id"])
    print("  ✓ Google Sheets connected")

    # Rename spreadsheet to today's date
    new_title = f"Price Badge Report - {cfg['display_name']} - {today}"
    if sh.title != new_title:
        sh.update_title(new_title)
        print(f"  ✓ Renamed spreadsheet: {new_title}")

    # Import CSVs (unless --stats-only)
    if not args.stats_only:
        if not args.lei:
            print("  ✗ --lei CSV path required (or use --stats-only)")
            sys.exit(1)

        print("[2/6] Importing CSV data...")
        lei_rows = read_csv_auto(args.lei)
        _validate_csv_headers(args.lei, lei_rows, _LEI_EXPECTED, "LEI")
        # Deduplicate by stock number (LEI CSV can have multiple rows per vehicle)
        seen_stocks, deduped = set(), []
        for row in lei_rows:
            stk = row[2].strip() if len(row) > 2 else ""
            if stk and stk in seen_stocks:
                continue
            if stk:
                seen_stocks.add(stk)
            deduped.append(row)
        if len(deduped) < len(lei_rows):
            print(f"  ✓ Deduplicated LEI rows: {len(lei_rows)} → {len(deduped)}")
        lei_rows = deduped
        if cfg["col_reorder"]:
            lei_rows = reorder_nalley_columns(lei_rows)
            print(f"  ✓ Reordered Nalley columns (C/D/E swap)")

        dem_rows = None
        if args.dem and cfg["has_dem_signal"]:
            dem_rows = read_csv_auto(args.dem)
            _validate_csv_headers(args.dem, dem_rows, _DEM_EXPECTED, "Dem Signal")

        sh = import_to_sheet(gc, cfg, lei_rows, dem_rows)
        print("  Waiting 5s for formula recalc...")
        time.sleep(5)
    else:
        print("[2/6] Skipping import (--stats-only)")

    # Sort
    print("[3/6] Sorting PBT by SAM A-Z, then column J ascending...")
    pbt = safe_sort_pbt(sh, cfg)
    format_pbt_price_column(sh, cfg)

    # Stats
    print("[4/6] Reading stats...")
    stats = read_stats(pbt, cfg)
    dem_stats = read_dem_signal_stats(sh, cfg) if cfg["has_dem_signal"] else None
    if dem_stats:
        print(f"  ✓ Dem Signal: {dem_stats['at_market_pct']}% At / {dem_stats['above_market_pct']}% Above / {dem_stats['under_market_pct']}% Under")

    # QC other tabs
    print("[5/6] Hiding data import tab + QC other tabs...")
    try:
        hide_import_tab(sh, cfg)
    except Exception as e:
        print(f"  ⚠ Could not hide tab: {e}")
    qc_other_tabs(sh)

    # Apply --to / --cc overrides before composing email
    if args.to:
        cfg["email_to"] = args.to
        # --to override implies test mode — suppress CC unless explicitly set
        if not args.cc:
            cfg["email_cc"] = ""
    if args.cc:
        cfg["email_cc"] = args.cc

    # Email draft (and optional send)
    draft_id = None
    action = "Sending" if args.send else "Creating Gmail draft"
    if not args.no_draft:
        print(f"[6/6] {action}...")
        html = compose_email_html(cfg, stats, dem_stats)
        try:
            gmail = get_gmail_service()
            draft_id, draft_obj = create_gmail_draft(gmail, cfg, html)
            if args.send:
                send_gmail_draft(gmail, draft_id)
        except Exception as e:
            print(f"  ⚠ Gmail {'send' if args.send else 'draft'} failed: {e}")
            # Save HTML fallback
            fallback = os.path.expanduser(f"~/Documents/Reports/pb_email_{args.dealer}_{today}.html")
            os.makedirs(os.path.dirname(fallback), exist_ok=True)
            with open(fallback, "w") as f:
                f.write(html)
            print(f"  ✓ HTML saved to {fallback} (copy/paste into Gmail)")
    else:
        print("[6/6] Skipping Gmail draft (--no-draft)")

    # Write structured stats for parallel runner aggregation
    if args.json_stats:
        import json as _json
        result = {
            "dealer": args.dealer,
            "display_name": cfg["display_name"],
            "pct": stats["pct"],
            "within_count": stats["within_count"],
            "total": stats["total"],
            "already_great": stats["already_great"],
            "draft_id": draft_id,
            "sheet_url": cfg["sheet_url"],
        }
        if dem_stats:
            result["dem_stats"] = dem_stats
        with open(args.json_stats, "w") as f:
            _json.dump(result, f, indent=2)
        print(f"  ✓ Stats written to {args.json_stats}")

    print(f"\n{'='*60}")
    print(f"Done! Sheet: {cfg['sheet_url']}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
