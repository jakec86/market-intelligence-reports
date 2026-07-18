#!/usr/bin/env python3
"""
Price Badge Report — automated sheet import, sort, stats, and Gmail draft.

Usage:
    python3 pb_report.py --dealer nalley --lei ~/Documents/Tableau/nalley_lei.csv
    python3 pb_report.py --dealer nalley --lei lei.csv --dem dem_signal.csv
    python3 pb_report.py --dealer hendrick --lei ~/Documents/Tableau/hendrick_lei.csv
    python3 pb_report.py --dealer nalley --stats-only   # skip import, just sort + draft
    python3 pb_report.py --dealer nalley --lei lei.csv --dry-run   # zero remote calls

Per-dealer config (sheet IDs, recipients, layout) lives in pb_dealers.py.
New-store onboarding checklist: pb_onboarding.md.

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

# Per-dealer config lives in pb_dealers.py — new stores are added there, not here.
from pb_dealers import DEALERS


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

    # Anchor the two positional columns in the PBT with static values.
    #
    # The PBT's col B (Store) and col D (Stock#) are direct row references
    # (e.g. ='Data Import_Inventory Report'!A928) — not key-based.  After a
    # sort Google Sheets adjusts those relative refs by displacement, so they
    # land on wrong import rows.  All other PBT columns (C, E-J) VLOOKUP on D
    # or B, so fixing these two roots fixes the entire formula chain.
    #
    # Writing static values here means each cell carries its own data through
    # any subsequent sort without formula drift.
    if cfg.get("pbt_tab") and cfg.get("data_start_row"):
        pbt_ws = sh.worksheet(cfg["pbt_tab"])
        data_start = cfg["data_start_row"]
        n = len(lei_rows) - 1  # rows excluding header

        # Derive write columns from config so each dealer lands in the right cells.
        # pbt_vehicle_col is 0-indexed (1=B, 2=C); stock_col is already a letter.
        ymmt_col_letter  = chr(ord('A') + cfg.get('pbt_vehicle_col', 2))
        stock_col_letter = cfg.get('stock_col', 'D')
        vin_col_letter   = (chr(ord('A') + cfg['pbt_vin_col'])
                            if cfg.get('pbt_vin_col') is not None else None)
        lei_vin_idx      = cfg.get('lei_vin_idx', 3)

        # Col Vehicle formula uses approximate VLOOKUP (missing FALSE arg) —
        # broken on unsorted import data. Write YMMT directly as a static value.
        hdr_row = lei_rows[0]
        ymmt_idx = next((i for i,h in enumerate(hdr_row)
                         if h.strip().lower() in ("ymmt","mmyt") or "ymmt" in h.lower()), None)

        stock_vals  = [[row[2]]              for row in lei_rows[1:] if len(row) > 2]
        dealer_vals = [[row[0]]              for row in lei_rows[1:] if len(row) > 0]
        ymmt_vals   = ([[row[ymmt_idx]]      for row in lei_rows[1:] if len(row) > ymmt_idx]
                       if ymmt_idx is not None else [])
        vin_vals    = ([[row[lei_vin_idx]]   for row in lei_rows[1:] if len(row) > lei_vin_idx]
                       if vin_col_letter else [])

        # Clear only the columns we write to — avoids wiping unrelated formula columns.
        cols_to_clear = sorted(
            {ymmt_col_letter, stock_col_letter}
            | ({vin_col_letter} if vin_col_letter else set())
            | ({'B'} if cfg.get('pbt_store_col') is not None else set())
        )
        # Determine the actual extent of stale data before clearing so we wipe
        # every row a previous (possibly larger) run wrote, not just up to a fixed cap.
        # Also cover the filter range end_row (for multi-store dealers like Hendrick that
        # use a basicFilter sort over the full sheet — old data outside the normal data
        # range but inside the filter range interleaves with new data after the sort).
        stock_col_idx = ord(stock_col_letter) - 64  # D → 4
        existing_stock = pbt_ws.col_values(stock_col_idx)
        filter_end_row = cfg.get("pbt_filter", {}).get("end_row", 0)
        clear_end = max(
            data_start + n + 50,                    # at least current import + buffer
            len(existing_stock) + data_start - 1,   # actual sheet extent
            filter_end_row,                         # cover full basicFilter range for multi-store dealers
        )
        pbt_ws.batch_clear([f"{c}{data_start}:{c}{clear_end}" for c in cols_to_clear])

        if stock_vals:
            pbt_ws.update(values=stock_vals,
                          range_name=f"{stock_col_letter}{data_start}:{stock_col_letter}{data_start+n-1}",
                          value_input_option="RAW")
        if ymmt_vals:
            pbt_ws.update(values=ymmt_vals,
                          range_name=f"{ymmt_col_letter}{data_start}:{ymmt_col_letter}{data_start+n-1}",
                          value_input_option="RAW")
        if vin_vals and vin_col_letter:
            pbt_ws.update(values=vin_vals,
                          range_name=f"{vin_col_letter}{data_start}:{vin_col_letter}{data_start+n-1}",
                          value_input_option="RAW")
        if dealer_vals and cfg.get("pbt_store_col") is not None:
            pbt_ws.update(values=dealer_vals, range_name=f"B{data_start}:B{data_start+n-1}",
                          value_input_option="RAW")
        print(f"  ✓ Anchored PBT cols B/C/D with {n} static values (sort-safe)")

    # Repair J ("Difference to Next Badge") with a VLOOKUP-by-stock formula on every
    # run, for every dealer — not just ones with a wide basicFilter. J starts life in
    # the template as a relative cross-sheet reference (e.g. ='Data Import...'!O136).
    # Google Sheets preserves that row *offset*, not the target row, when a sort
    # relocates the row, so after safe_sort_pbt's Pass 2 (sort by J ascending) J
    # silently shows another vehicle's diff — confirmed 2026-07-13: 60/69 Nalley rows
    # wrong after a single-dealer sort with no basicFilter involved at all. Cols
    # C/E-I already VLOOKUP off D (stock#) and are unaffected; this brings J in line.
    filter_end_row = cfg.get("pbt_filter", {}).get("end_row", 0)
    repair_end_row = max(filter_end_row, clear_end) if cfg.get("pbt_tab") and cfg.get("data_start_row") else 0
    if repair_end_row and repair_end_row > data_start:
        try:
            import googleapiclient.discovery as _disc
            from google.oauth2.credentials import Credentials as _Creds
            # copyPaste silently skips any row currently hiddenByFilter — confirmed
            # 2026-07-13: leftover filter state (present even on dealers with no
            # pbt_filter config, e.g. Dyer) left 7/5698 Hendrick rows and 1/54 Dyer
            # rows on the stale pre-VLOOKUP formula despite this block "succeeding".
            # Clear any basicFilter unconditionally before pasting so nothing is hidden.
            try:
                sh.batch_update({"requests": [{"clearBasicFilter": {"sheetId": pbt_ws.id}}]})
            except Exception:
                pass  # no filter present — nothing to clear
            _creds = _Creds.from_authorized_user_file(TOKEN_SHEETS, SCOPES_SHEETS)
            if _creds.expired and _creds.refresh_token:
                from google.auth.transport.requests import Request as _Req
                _creds.refresh(_Req())
            _svc = _disc.build("sheets", "v4", credentials=_creds, cache_discovery=False)
            j_col_idx = 9  # column J (0-indexed)
            # Write anchor formula to J(data_start) then copyPaste to full filter range
            j_formula = (
                f'=IFERROR(IF(I{data_start}="Good",'
                f'ABS(VLOOKUP(D{data_start},\'Data Import_Inventory Report\'!$C$2:$Q$10000,13,FALSE)),'
                f'IF(I{data_start}="Great",'
                f'ABS(VLOOKUP(D{data_start},\'Data Import_Inventory Report\'!$C$2:$Q$10000,15,FALSE)),'
                f'"")),"")'
            )
            pbt_ws.update(f"J{data_start}", [[j_formula]], value_input_option="USER_ENTERED")
            _svc.spreadsheets().batchUpdate(
                spreadsheetId=pbt_ws.spreadsheet.id,
                body={"requests": [{"copyPaste": {
                    "source": {"sheetId": pbt_ws.id,
                               "startRowIndex": data_start - 1, "endRowIndex": data_start,
                               "startColumnIndex": j_col_idx, "endColumnIndex": j_col_idx + 1},
                    "destination": {"sheetId": pbt_ws.id,
                                    "startRowIndex": data_start, "endRowIndex": repair_end_row,
                                    "startColumnIndex": j_col_idx, "endColumnIndex": j_col_idx + 1},
                    "pasteType": "PASTE_FORMULA",
                }}]},
            ).execute()
            print(f"  ✓ Repaired J formula J{data_start}:J{repair_end_row} (VLOOKUP, sort-safe)")
        except Exception as _e:
            print(f"  ⚠ J formula repair skipped: {_e}")

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

    data_range = f"A{data_start}:{data_end_col}{last_data_row}"

    if cfg.get("pbt_store_col") is None:
        # Single-dealer (Nalley): no SAM groups — sort J ascending so green (within-threshold)
        # rows appear at the top. No basicFilter to rely on for color-sort.
        _sort_with_retry(pbt, (cfg["sort_col"], "asc"), data_range)
        print(f"  ✓ Pass 2: sorted {data_range} by J ascending (green first)")
    else:
        # Multi-dealer (Hendrick): sort by SAM A-Z.
        # The sheet's basicFilter (with its own sortSpecs) owns the final display order:
        # it puts rows where col J has conditional-format green (AND(J<=threshold, J>0))
        # at the top within each SAM group. We provide clean SAM-sorted data and let
        # the filter handle green-first display automatically.
        # DO NOT set userEnteredFormat.backgroundColor — it overrides the conditional
        # format on col J and breaks the filter's color-based sort.
        _sort_with_retry(pbt, (1, "asc"), data_range)
        print(f"  ✓ Pass 2: sorted {data_range} by SAM A-Z")

    # Count green rows for the status line (read J unformatted; no background write).
    # Status-line only — never let a transient API error here kill the pipeline.
    green_count = None
    try:
        import googleapiclient.discovery as _disc
        from google.oauth2.credentials import Credentials as _Creds
        _creds = _Creds.from_authorized_user_file(TOKEN_SHEETS, SCOPES_SHEETS)
        if _creds.expired and _creds.refresh_token:
            from google.auth.transport.requests import Request as _Req
            _creds.refresh(_Req())
        _svc = _disc.build("sheets", "v4", credentials=_creds, cache_discovery=False)

        time.sleep(5)
        threshold_val = float(re.sub(r"[,$]", "", pbt.acell(cfg["threshold_cell"]).value))
        j_raw = _svc.spreadsheets().values().get(
            spreadsheetId=pbt.spreadsheet.id,
            range=f"'{pbt.title}'!J{data_start}:J{last_data_row}",
            valueRenderOption="UNFORMATTED_VALUE",
        ).execute().get("values", [])
        green_count = sum(
            1 for row in j_raw
            if row and isinstance(row[0], (int, float)) and 0 < row[0] <= threshold_val
        )
    except Exception as e:
        print(f"  ⚠ Green-count read failed (status line only, sort unaffected): {e}")

    if green_count is not None:
        print(f"  ✓ {data_count} total rows: {green_count} within threshold (green via CF), {data_count - green_count} above")
    else:
        print(f"  ✓ {data_count} total rows sorted")
    return pbt


def reset_pbt_filter(sh, cfg):
    """Clear and re-apply the basicFilter to fix hiddenByFilter corruption from sortRange calls.

    The Hendrick PBT has a basicFilter whose sortSpecs conflict with our sortRange API calls,
    leaving rows erroneously marked hiddenByFilter. Clearing + re-adding the filter resets this.
    Only runs when a 'pbt_filter' config block is present (Hendrick-specific).
    """
    filter_cfg = cfg.get("pbt_filter")
    if not filter_cfg:
        return
    ws = sh.worksheet(cfg["pbt_tab"])
    sheet_id = ws.id
    sh.batch_update({"requests": [{"clearBasicFilter": {"sheetId": sheet_id}}]})
    sh.batch_update({"requests": [{"setBasicFilter": {"filter": {
        "range": {
            "sheetId": sheet_id,
            "startRowIndex": filter_cfg["start_row"],
            "endRowIndex": filter_cfg["end_row"],
            "startColumnIndex": filter_cfg["start_col"],
            "endColumnIndex": filter_cfg["end_col"],
        },
        "sortSpecs": filter_cfg["sort_specs"],
        "filterSpecs": filter_cfg["filter_specs"],
    }}}]})
    print(f"  ✓ Reset basicFilter (hiddenByFilter state cleared)")


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


def read_stats(sh, pbt, cfg):
    """Read key stats from the PBT tab for the email."""
    time.sleep(3)  # wait for formula recalc

    pct = pbt.acell(cfg["pct_cell"]).value or "0%"
    threshold = pbt.acell(cfg["threshold_cell"]).value or "$1,000"

    all_values = pbt.get_all_values()
    data_start = cfg["data_start_row"] - 1  # 0-indexed
    data_rows = [r for r in all_values[data_start:] if r[3].strip()]  # col D = Stock #

    # Build stock# → {vehicle, dealer} from the raw import tab to avoid reading
    # PBT formula cells that may be stale immediately after a sort.
    import_lookup = {}
    try:
        import_ws = sh.worksheet(cfg["import_tab"])
        import_all = import_ws.get_all_values()
        if import_all:
            import_hdr = [h.strip() for h in import_all[0]]
            stk_idx = next((i for i, h in enumerate(import_hdr) if "stock" in h.lower()), 2)
            ymmt_idx = next((i for i, h in enumerate(import_hdr)
                             if h.lower() in ("ymmt", "mmyt") or "ymmt" in h.lower()), None)
            dealer_idx = next((i for i, h in enumerate(import_hdr)
                               if "dealer name" in h.lower()), 0)
            for row in import_all[1:]:
                stk = row[stk_idx].strip() if len(row) > stk_idx else ""
                if not stk:
                    continue
                import_lookup[stk] = {
                    "vehicle": (row[ymmt_idx].strip() if ymmt_idx is not None and len(row) > ymmt_idx else ""),
                    "dealer":  (row[dealer_idx].strip() if len(row) > dealer_idx else ""),
                }
            print(f"  ✓ Import lookup built: {len(import_lookup)} stock entries")
    except Exception as e:
        print(f"  ⚠ Could not build import lookup (will fall back to PBT formulas): {e}")

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
        stock        = r[3].strip() if len(r) > 3 else ""

        # Prefer import tab data for vehicle/store — PBT formula columns can be
        # stale immediately after a sort if the formulas use row-position lookups.
        if stock and stock in import_lookup:
            lu = import_lookup[stock]
            if lu["vehicle"]:
                vehicle = lu["vehicle"]
            if lu["dealer"]:
                store = lu["dealer"]
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
                    "stock": stock,
                    "diff": diff_raw, "current": current_badge, "next": next_badge,
                    "target_price": target_price,
                })
            elif 0 < diff_val <= thresh_val:
                within_threshold.append({
                    "sam": sam, "store": store, "vehicle": vehicle,
                    "stock": stock,
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

    # Compute top-5 callout directly from the raw import tab.
    # PBT formula columns (vehicle name, stock#) can be stale immediately after a
    # multi-pass sort — reading from the import tab avoids that entirely.
    top_vehicles_import = []
    try:
        def _fnum(v):
            try: return float(re.sub(r"[$,]", "", v))
            except: return None

        if import_all and len(import_all) > 1:
            ih = [h.strip() for h in import_all[0]]
            i_stk    = next((i for i,h in enumerate(ih) if "stock" in h.lower()), 2)
            i_ymmt   = next((i for i,h in enumerate(ih) if h.lower() in ("ymmt","mmyt") or "ymmt" in h.lower()), None)
            i_dealer = next((i for i,h in enumerate(ih) if "dealer name" in h.lower()), 0)
            i_price  = next((i for i,h in enumerate(ih) if "sum of price" in h.lower()), None)
            i_good   = next((i for i,h in enumerate(ih) if "difference - good" in h.lower()), None)
            i_great  = next((i for i,h in enumerate(ih) if "difference - great" in h.lower()), None)
            i_badge  = next((i for i,h in enumerate(ih) if h.lower() == "price badge"), None)
            thresh_val_import = _fnum(threshold) or 500.0

            seen_import = set()
            candidates_import = []
            for row in import_all[1:]:
                stk = row[i_stk].strip() if len(row) > i_stk else ""
                if not stk or stk in seen_import:
                    continue
                seen_import.add(stk)
                good_d  = _fnum(row[i_good])  if i_good  is not None and len(row) > i_good  else None
                great_d = _fnum(row[i_great]) if i_great is not None and len(row) > i_great else None
                badge   = row[i_badge].strip() if i_badge is not None and len(row) > i_badge else ""

                # LEI sign convention: negative diff = price is above threshold
                # by |diff| dollars → vehicle needs to drop |diff| to earn badge.
                # Only count a diff as a candidate if the vehicle doesn't already
                # hold that badge — this mirrors the PBT's tier-up logic and
                # ensures every callout vehicle is findable in the PBT green section.
                is_good_plus  = badge in ("Good", "Great")
                is_great      = badge == "Great"
                diffs = [(abs(d), "Great" if idx == 1 else "Good", d)
                         for idx, d in enumerate([good_d, great_d])
                         if d is not None and -thresh_val_import <= d < 0
                         and not (idx == 0 and is_good_plus)  # skip Good if already Good+
                         and not (idx == 1 and is_great)]     # skip Great if already Great
                if not diffs:
                    continue
                drop, next_b, raw_d = min(diffs, key=lambda x: x[0])
                price  = _fnum(row[i_price])  if i_price  is not None and len(row) > i_price  else None
                ymmt   = row[i_ymmt].strip()   if i_ymmt   is not None and len(row) > i_ymmt   else ""
                dealer = row[i_dealer].strip() if len(row) > i_dealer else ""
                badge  = row[i_badge].strip()  if i_badge  is not None and len(row) > i_badge  else ""
                target = f"${price + raw_d:,.0f}" if price is not None else ""
                candidates_import.append({
                    "sam": dealer, "store": "", "vehicle": ymmt,
                    "stock": stk, "diff": f"${drop:,.0f}",
                    "current": badge, "next": next_b, "target_price": target,
                })
            candidates_import.sort(key=lambda x: float(re.sub(r"[$,]", "", x["diff"])))
            top_vehicles_import = _pick_top_vehicles(candidates_import, n=5)
    except Exception as e:
        print(f"  ⚠ Import-based top-vehicles failed, falling back to PBT: {e}")

    # Recalculate percentage excluding $0 rows (already-qualifying vehicles inflate
    # the denominator and make the badge-opportunity rate look smaller than it is).
    non_zero_total = total - len(at_deduped)
    computed_pct = f"{len(within_deduped)/non_zero_total:.0%}" if non_zero_total > 0 else "0%"

    stats = {
        "pct": computed_pct,
        "threshold": threshold,
        "total": total,
        "at_threshold_count": len(at_deduped),
        "at_threshold_vehicles": at_deduped,
        "within_count": len(within_deduped),
        "already_great": already_great,
        "top_vehicles": top_vehicles_import if top_vehicles_import else _pick_top_vehicles(within_deduped, n=5),
    }
    print(f"  ✓ Stats: {stats['within_count']}/{non_zero_total} within {threshold} ({computed_pct}), "
          f"{len(at_deduped)} at $0 (excluded from %), {already_great} already Great")
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


# ─── DRY RUN (CSV-only, zero remote calls) ───────────────────────────────────

def csv_stats(lei_rows, cfg):
    """Compute report stats directly from the LEI CSV — no sheet access.

    Mirrors the import-tab callout logic in read_stats(): per unique stock,
    a vehicle is "within" if it needs a drop of 0 < |diff| <= threshold for a
    badge tier it doesn't already hold (LEI sign convention: negative diff =
    price above threshold by |diff|).
    """
    def _fnum(v):
        try: return float(re.sub(r"[$,]", "", v))
        except (ValueError, TypeError): return None

    threshold = float(cfg.get("threshold", 500))
    hdr = [h.strip() for h in lei_rows[0]]
    i_stk    = next((i for i, h in enumerate(hdr) if "stock" in h.lower()), 2)
    i_ymmt   = next((i for i, h in enumerate(hdr) if "ymmt" in h.lower()), None)
    i_dealer = next((i for i, h in enumerate(hdr) if "dealer name" in h.lower()), 0)
    i_vin    = cfg.get("lei_vin_idx", 3)
    i_price  = next((i for i, h in enumerate(hdr) if "sum of price" in h.lower()), None)
    i_good   = next((i for i, h in enumerate(hdr) if "difference - good" in h.lower()), None)
    i_great  = next((i for i, h in enumerate(hdr) if "difference - great" in h.lower()), None)
    i_badge  = next((i for i, h in enumerate(hdr) if h.lower() == "price badge"), None)
    if i_good is None or i_great is None:
        print("  ✗ Dry run requires 'Difference - Good'/'Difference - Great' columns in the LEI CSV")
        sys.exit(1)

    seen = set()
    within, at_thresh = [], []
    already_great = 0
    for row in lei_rows[1:]:
        stk = row[i_stk].strip() if len(row) > i_stk else ""
        if not stk or stk in seen:
            continue
        seen.add(stk)
        badge   = row[i_badge].strip() if i_badge is not None and len(row) > i_badge else ""
        good_d  = _fnum(row[i_good])  if len(row) > i_good  else None
        great_d = _fnum(row[i_great]) if len(row) > i_great else None
        if badge == "Great":
            already_great += 1
            continue
        is_good_plus = badge in ("Good", "Great")
        diffs = [(abs(d), "Great" if idx == 1 else "Good", d)
                 for idx, d in enumerate([good_d, great_d])
                 if d is not None and -threshold <= d <= 0
                 and not (idx == 0 and is_good_plus)]
        if not diffs:
            continue
        drop, next_b, raw_d = min(diffs, key=lambda x: x[0])
        price  = _fnum(row[i_price]) if i_price is not None and len(row) > i_price else None
        rec = {
            "sam": row[i_dealer].strip() if len(row) > i_dealer else "",
            "store": "",
            "vehicle": (row[i_ymmt].strip() if i_ymmt is not None and len(row) > i_ymmt else ""),
            "vin": (row[i_vin].strip() if len(row) > i_vin else ""),
            "stock": stk,
            "diff": f"${drop:,.0f}",
            "current": badge, "next": next_b,
            "target_price": (f"${price + raw_d:,.0f}" if price is not None else ""),
        }
        (at_thresh if drop == 0 else within).append(rec)

    within.sort(key=lambda x: float(re.sub(r"[$,]", "", x["diff"])))
    total = len(seen)
    pct = f"{round(100 * len(within) / total)}%" if total else "0%"
    return {
        "pct": pct,
        "threshold": f"${threshold:,.0f}",
        "total": total,
        "at_threshold_count": len(at_thresh),
        "at_threshold_vehicles": at_thresh,
        "within_count": len(within),
        "already_great": already_great,
        "top_vehicles": _pick_top_vehicles(within, n=5),
    }


def csv_dem_stats(dem_rows):
    """Compute Demand Signal breakdown directly from the Pricing CSV."""
    header = dem_rows[0] if dem_rows else []
    val_idx = next((i for i, h in enumerate(header) if "value" in h.lower()), None)
    if val_idx is None:
        return None
    categories = [r[val_idx].strip() for r in dem_rows[1:]
                  if len(r) > val_idx and r[val_idx].strip()]
    total = len(categories)
    if total == 0:
        return None
    counts = Counter(categories)
    at_mkt = sum(v for k, v in counts.items()
                 if "at market" in k.lower() and "above" not in k.lower() and "under" not in k.lower())
    above = sum(v for k, v in counts.items() if "above" in k.lower())
    under = sum(v for k, v in counts.items() if "under" in k.lower())
    return {
        "at_market_pct": round(100 * at_mkt / total),
        "above_market_pct": round(100 * above / total),
        "under_market_pct": round(100 * under / total),
        "total": total,
    }


def run_dry_run(args, cfg, today):
    """Full pipeline verification with ZERO remote calls — no auth, no sheet
    reads/writes, no Gmail. Parses + validates the CSVs, computes stats from
    the CSV alone, and writes the composed email HTML to a local file."""
    print("  MODE: DRY RUN — no Google auth, no sheet writes, no email\n")
    if not args.lei:
        print("  ✗ --lei CSV path required for --dry-run")
        sys.exit(1)

    print("[1/3] Parsing + validating CSVs...")
    lei_rows = read_csv_auto(args.lei)
    _validate_csv_headers(args.lei, lei_rows, _LEI_EXPECTED, "LEI")
    dem_rows = None
    if args.dem and cfg["has_dem_signal"]:
        dem_rows = read_csv_auto(args.dem)
        _validate_csv_headers(args.dem, dem_rows, _DEM_EXPECTED, "Dem Signal")

    print("[2/3] Computing stats from CSV...")
    stats = csv_stats(lei_rows, cfg)
    dem_stats = csv_dem_stats(dem_rows) if dem_rows else None
    print(f"  ✓ Stats: {stats['within_count']}/{stats['total']} within {stats['threshold']} "
          f"({stats['pct']}), {stats['at_threshold_count']} at $0, "
          f"{stats['already_great']} already Great")
    if dem_stats:
        print(f"  ✓ Dem Signal: {dem_stats['at_market_pct']}% At / "
              f"{dem_stats['above_market_pct']}% Above / {dem_stats['under_market_pct']}% Under")

    print("[3/3] Composing email HTML (local file only)...")
    html = compose_email_html(cfg, stats, dem_stats)
    out_path = os.path.expanduser(f"~/Documents/Reports/pb_dryrun_{args.dealer}_{today}.html")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        f.write(html)
    print(f"  ✓ Email preview: {out_path}")

    if args.json_stats:
        result = {
            "dealer": args.dealer,
            "display_name": cfg["display_name"],
            "dry_run": True,
            "pct": stats["pct"],
            "within_count": stats["within_count"],
            "total": stats["total"],
            "already_great": stats["already_great"],
            "draft_id": None,
            "sheet_url": cfg["sheet_url"],
        }
        if dem_stats:
            result["dem_stats"] = dem_stats
        with open(args.json_stats, "w") as f:
            json.dump(result, f, indent=2)
        print(f"  ✓ Stats written to {args.json_stats}")

    print(f"\n{'='*60}")
    print(f"Dry run complete — nothing was written to Sheets or Gmail.")
    print(f"Note: dry-run stats come from the CSV alone; live-run %s come from")
    print(f"the sheet's J1 formula and may differ slightly.")
    print(f"{'='*60}\n")


# ─── EMAIL DRAFT ─────────────────────────────────────────────────────────────

def compose_email_html(cfg, stats, dem_stats=None):
    """Build HTML email body with hyperlinked Price Badge Report."""
    top_vehicles_html = ""
    callout_style = cfg.get("callout_style", "sam")
    for v in stats["top_vehicles"]:
        price_note = f" &rarr; reprice to <b>{v['target_price']}</b>" if v.get("target_price") else f" &mdash; <b>{v['diff']}</b>"
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

    # (Removed 2026-06-12 per Jake: the "$0 / already qualify, no action needed"
    # paragraph was unneeded filler.) Kept empty so the template insertion is a no-op.
    at_threshold_html = ""

    dem_paragraph = ""
    if dem_stats:
        # Closing clause scales to the actual off-market share (above + under),
        # so it stays accurate whether a store is 92% At Market or 60%.
        off_market_pct = float(dem_stats["above_market_pct"]) + float(dem_stats["under_market_pct"])
        if off_market_pct <= 15:
            dem_close = (
                f'the vast majority is competitively positioned, with just '
                f'{off_market_pct:.0f}% sitting off-market.'
            )
        elif off_market_pct <= 40:
            dem_close = (
                f'most inventory is competitively positioned, though '
                f'{off_market_pct:.0f}% has room to sharpen up and capture more shopper attention.'
            )
        else:
            dem_close = (
                f'{off_market_pct:.0f}% of inventory has room to sharpen up and '
                f'capture more shopper attention.'
            )
        dem_paragraph = (
            f'<p>From a broader pricing standpoint, your Demand Signals show '
            f'<b>{dem_stats["at_market_pct"]}% At Market</b>, '
            f'<b>{dem_stats["above_market_pct"]}% Above Market</b>, and '
            f'<b>{dem_stats["under_market_pct"]}% Under Market</b> &mdash; '
            f'{dem_close}</p>'
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
<a href="{cfg.get("email_link_url", cfg["sheet_url"])}">Price Badge Report</a>,
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
    # Suppress CC in pre-send mode (when email goes to Jake for review, not the final recipients)
    is_presend = bool(cfg.get("email_final_to") and
                      "jcrawley@cars.com" in cfg.get("email_to", ""))
    if cfg.get("email_cc") and not is_presend:
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
                        help="Skip import, just sort + read stats + draft email "
                             "(still MUTATES the sheet and creates a draft)")
    parser.add_argument("--dry-run", action="store_true",
                        help="True dry run: parse + validate CSVs, compute stats, "
                             "write email HTML locally. Zero remote calls.")
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

    if args.dry_run:
        run_dry_run(args, cfg, today)
        return

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

    # Sort + filter reset
    print("[3/6] Sorting PBT by SAM A-Z, then column J ascending...")
    pbt = safe_sort_pbt(sh, cfg)
    format_pbt_price_column(sh, cfg)
    reset_pbt_filter(sh, cfg)  # repairs hiddenByFilter corruption from sortRange calls

    # Stats
    print("[4/6] Reading stats...")
    stats = read_stats(sh, pbt, cfg)
    dem_stats = read_dem_signal_stats(sh, cfg) if cfg["has_dem_signal"] else None
    if dem_stats:
        print(f"  ✓ Dem Signal: {dem_stats['at_market_pct']}% At / {dem_stats['above_market_pct']}% Above / {dem_stats['under_market_pct']}% Under")

    # QC other tabs
    print("[5/6] Hiding data import tab + QC other tabs...")
    try:
        hide_import_tab(sh, cfg)
    except Exception as e:
        print(f"  ⚠ Could not hide tab: {e}")
    for tab_name in cfg.get("extra_hide_tabs", []):
        try:
            ws_extra = sh.worksheet(tab_name)
            sh.batch_update({"requests": [{"updateSheetProperties": {
                "properties": {"sheetId": ws_extra.id, "hidden": True},
                "fields": "hidden"}}]})
            print(f"  ✓ Hidden tab '{tab_name}'")
        except Exception as e:
            print(f"  ⚠ Could not hide '{tab_name}': {e}")
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
