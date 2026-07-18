"""
CSM SIP QC — Cross-Reference & Corrected Retention
Compares Tableau SIP dashboard CSVs against the master Book of Business Google Sheet
and writes a "SIP QC" tab with discrepancies and corrected retention.

Usage:
    python3 ~/Documents/scripts/csm_sip_qc.py
"""

import os, re, json
import gspread
import gspread.exceptions
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

# ─── CONFIG ──────────────────────────────────────────────────────────────────

SHEET_ID       = "1SyRXRGO5RMbndATw1ABSjRQT9arhKMm-V96EADL_X7M"
TOKEN_SHEETS   = os.path.expanduser("~/.claude/tokens/sheets_token.json")
CLIENT_SECRETS = os.path.expanduser("~/gcp-oauth.keys.json")
SCOPES_SHEETS  = ["https://www.googleapis.com/auth/spreadsheets"]

CSV_OVERVIEW   = os.path.expanduser("~/Downloads/CSM Overview.csv")
CSV_DETAILS    = os.path.expanduser("~/Downloads/Account Details.csv")
SF_MRR_FILE    = "/tmp/missing_sf_mrr_sip_v3.json"

# Known exclusions (wrong SF account owner)
CROWN_EXCLUDE  = {"11920", "13729"}  # CCIDs as strings
# Group billing — acknowledged, no action
ASBURY_NOTE    = {"539890"}

# Expected positional column layout — abort if CSV structure has changed
_OVERVIEW_COL_CHECK = {2: "ccid", 6: "mrr", 7: "mrr"}  # SIP Overview.csv
_DETAILS_COL_CHECK  = {0: "ccid"}                        # Account Details.csv

QC_TAB_TITLE   = "SIP QC"

# ─── COLORS (RGB dicts for gspread) ──────────────────────────────────────────

RED    = {"red": 0.96, "green": 0.80, "blue": 0.80}
YELLOW = {"red": 1.0,  "green": 0.95, "blue": 0.60}
ORANGE = {"red": 1.0,  "green": 0.85, "blue": 0.60}
BLUE   = {"red": 0.75, "green": 0.88, "blue": 1.0}
GRAY   = {"red": 0.85, "green": 0.85, "blue": 0.85}
PURPLE = {"red": 0.38, "green": 0.20, "blue": 0.56}  # Cars Commerce purple
WHITE  = {"red": 1.0,  "green": 1.0,  "blue": 1.0}

ISSUE_COLORS = {
    "Exclude — Wrong Owner":          RED,
    "Missing from SIP":               YELLOW,
    "Extra in SIP":                   ORANGE,
    "MRR Mismatch":                   BLUE,
    "Group Billing — Acknowledged":   GRAY,
    "Extra in Acct Details / Not in SIP": ORANGE,
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


# ─── DATA LOADERS ────────────────────────────────────────────────────────────

def _validate_positional_cols(header_line, required, label):
    """Abort if expected substrings aren't at specific tab-delimited column positions."""
    cols = [h.strip().lower() for h in header_line.split("\t")]
    errors = []
    for pos, fragment in required.items():
        actual = cols[pos] if pos < len(cols) else "<missing>"
        if fragment.lower() not in actual:
            errors.append(f"    col[{pos}]: expected '{fragment}' in column, got '{actual}'")
    if errors:
        print(f"  ✗ {label} CSV positional schema mismatch:")
        for e in errors:
            print(e)
        print(f"    Full header: {cols[:10]}")
        sys.exit(1)
    print(f"  ✓ {label} CSV schema OK")


def parse_mrr(val):
    """Convert '$1,234.56' or '' to float."""
    if not val:
        return 0.0
    return float(re.sub(r"[^\d.]", "", val)) if val.strip() else 0.0


def load_sheet_book(gc):
    """Read Sheet1 (header row 3, data rows 4+). Returns list of dicts."""
    sh = gc.open_by_key(SHEET_ID)
    ws = sh.worksheet("BoB")
    all_rows = ws.get_all_values()

    # Row index 2 (0-based) = row 3 = header
    header = [h.strip() for h in all_rows[2]]

    def col(name_fragment):
        """Return index of first column whose header contains name_fragment (case-insensitive)."""
        frag = name_fragment.lower()
        for i, h in enumerate(header):
            if frag in h.lower():
                return i
        return None

    idx_ccid    = col("ccid")
    idx_parent  = col("ultimate par")
    idx_acct    = col("account nam")
    idx_eae     = col("eae")
    idx_mkp     = col("mkp active/prospect")

    # Fallback: find second "account nam" for short name
    all_acct_cols = [i for i, h in enumerate(header) if "account nam" in h.lower()]
    idx_acct = all_acct_cols[0] if all_acct_cols else idx_acct

    print(f"  Sheet1 — detected columns: CCID={idx_ccid}, Parent={idx_parent}, "
          f"Account={idx_acct}, EAE={idx_eae}, MKP={idx_mkp}")
    print(f"  Sheet1 — header row: {header[:20]}")

    records = []
    for row in all_rows[3:]:  # data starts row 4 (index 3)
        if not row or not (row[idx_ccid] if idx_ccid is not None else "").strip():
            continue
        records.append({
            "ccid":    str(row[idx_ccid]).strip(),
            "parent":  row[idx_parent].strip() if idx_parent is not None else "",
            "account": row[idx_acct].strip()   if idx_acct is not None else "",
            "eae":     row[idx_eae].strip()    if idx_eae is not None else "",
            "mkp":     row[idx_mkp].strip()    if idx_mkp is not None else "",
        })
    print(f"  Sheet1 — {len(records)} data rows loaded")
    return records


def load_sip_overview():
    """Parse CSM Overview.csv (UTF-16). Returns dict keyed by CCID string."""
    with open(CSV_OVERVIEW, "r", encoding="utf-16") as f:
        content = f.read()
    lines = content.strip().split("\n")
    _validate_positional_cols(lines[0], _OVERVIEW_COL_CHECK, "SIP Overview")
    # header: seat, name, ccid, parent, account, onecar_id, start_mrr, end_mrr, variance, retention
    sip = {}
    for line in lines[1:]:
        parts = [p.strip() for p in line.split("\t")]
        if len(parts) < 10:
            continue
        ccid = str(parts[2]).strip()
        if not ccid:
            continue
        sip[ccid] = {
            "ccid":      ccid,
            "csm":       parts[1].strip(),
            "parent":    parts[3].strip(),
            "account":   parts[4].strip(),
            "start_mrr": parse_mrr(parts[6]),
            "end_mrr":   parse_mrr(parts[7]),
            "retention": parts[9].strip(),
        }
    print(f"  CSM Overview — {len(sip)} accounts loaded")
    return sip


def load_sf_mrr():
    """Load Salesforce MRR for missing accounts from temp JSON. Returns dict keyed by CCID."""
    if not os.path.exists(SF_MRR_FILE):
        print(f"  SF MRR file not found at {SF_MRR_FILE} — skipping")
        return {}
    with open(SF_MRR_FILE) as f:
        records = json.load(f)
    sf = {str(r["ccid"]): r for r in records}
    total = sum(r["mrr"] for r in records)
    print(f"  SF MRR data — {len(sf)} accounts, ${total:,.0f} total SIP MRR")
    return sf


def load_account_details():
    """Parse Account Details.csv (UTF-16). Returns dict: ccid -> {account, may_mrr}."""
    with open(CSV_DETAILS, "r", encoding="utf-16") as f:
        content = f.read()
    lines = content.strip().split("\n")
    _validate_positional_cols(lines[1], _DETAILS_COL_CHECK, "Account Details")
    # Skip first header line (Month of Date x3), use second line as real header
    # Real header: Ccid, Account Name, OneCars Account ID, Product, March, April, May
    detail = {}
    for line in lines[2:]:  # skip 2 header rows
        parts = [p.strip() for p in line.split("\t")]
        if len(parts) < 7:
            continue
        ccid = str(parts[0]).strip()
        if not ccid:
            continue
        acct = parts[1].strip()
        may_val = parse_mrr(parts[6]) if parts[6].strip() else 0.0
        if ccid not in detail:
            detail[ccid] = {"account": acct, "may_mrr": 0.0}
        detail[ccid]["may_mrr"] += may_val
    print(f"  Account Details — {len(detail)} unique CCIDs loaded")
    return detail


# ─── QC LOGIC ────────────────────────────────────────────────────────────────

def run_qc(sheet_records, sip, details, sf_mrr=None):
    """
    Returns (findings, summary_stats).
    findings: list of dicts with issue details.
    sf_mrr: dict of ccid -> SF subscription MRR for accounts missing from SIP.
    """
    if sf_mrr is None:
        sf_mrr = {}
    sheet_ccids = {r["ccid"]: r for r in sheet_records}
    sip_ccids   = set(sip.keys())
    detail_ccids = set(details.keys())

    findings = []

    # ── 1. Crown exclusions (highest priority) ───────────────────────────────
    for ccid in CROWN_EXCLUDE:
        if ccid in sip:
            s = sip[ccid]
            findings.append({
                "ccid":         ccid,
                "account":      s["account"],
                "parent":       s["parent"],
                "eae":          sheet_ccids.get(ccid, {}).get("eae", ""),
                "issue":        "Exclude — Wrong Owner",
                "sheet_mrr":    "",
                "sip_start":    s["start_mrr"],
                "sip_end":      s["end_mrr"],
                "may_mrr":      details.get(ccid, {}).get("may_mrr", 0.0),
                "notes":        "Under Traci Pecci in SF — remove from Jacob's SIP book",
            })

    # ── 2. Asbury acknowledgement ────────────────────────────────────────────
    for ccid in ASBURY_NOTE:
        if ccid in sip:
            s = sip[ccid]
            findings.append({
                "ccid":         ccid,
                "account":      s["account"],
                "parent":       s["parent"],
                "eae":          sheet_ccids.get(ccid, {}).get("eae", ""),
                "issue":        "Group Billing — Acknowledged",
                "sheet_mrr":    "",
                "sip_start":    s["start_mrr"],
                "sip_end":      s["end_mrr"],
                "may_mrr":      details.get(ccid, {}).get("may_mrr", 0.0),
                "notes":        "Entire Asbury group billed as single SF record — no action needed",
            })

    already_flagged = CROWN_EXCLUDE | ASBURY_NOTE

    # ── 3. Missing from SIP: in Sheet (MKP active) but not in SIP Overview ──
    for ccid, rec in sheet_ccids.items():
        if ccid in already_flagged:
            continue
        mkp_val = rec["mkp"].lower()
        is_mkp_active = mkp_val.lower() == "mkp"
        if is_mkp_active and ccid not in sip_ccids:
            sf_rec   = sf_mrr.get(ccid, {})
            sf_val   = sf_rec.get("mrr", 0.0)
            products = sf_rec.get("products", "")
            note = "In book of business (MKP Active) but absent from Tableau SIP dashboard"
            if sf_val:
                note += f" | SF MRR: ${sf_val:,.0f}"
            if products:
                note += f" | {products}"
            findings.append({
                "ccid":         ccid,
                "account":      rec["account"],
                "parent":       rec["parent"],
                "eae":          rec["eae"],
                "issue":        "Missing from SIP",
                "sheet_mrr":    sf_val if sf_val else details.get(ccid, {}).get("may_mrr", ""),
                "sip_start":    sf_val,  # use SF MRR as proxy for starting MRR
                "sip_end":      sf_val,  # and ending MRR (current active subscription)
                "may_mrr":      details.get(ccid, {}).get("may_mrr", sf_val),
                "notes":        note,
            })

    # ── 4. Extra in SIP: in SIP Overview but not in Sheet ───────────────────
    for ccid in sip_ccids:
        if ccid in already_flagged or ccid in sheet_ccids:
            continue
        s = sip[ccid]
        findings.append({
            "ccid":         ccid,
            "account":      s["account"],
            "parent":       s["parent"],
            "eae":          "",
            "issue":        "Extra in SIP",
            "sheet_mrr":    "",
            "sip_start":    s["start_mrr"],
            "sip_end":      s["end_mrr"],
            "may_mrr":      details.get(ccid, {}).get("may_mrr", 0.0),
            "notes":        "In Tableau SIP dashboard but not found in book of business sheet",
        })

    # ── 5. Extra in Account Details but not in SIP ──────────────────────────
    for ccid in detail_ccids:
        if ccid in already_flagged or ccid in sip_ccids:
            continue
        d = details[ccid]
        findings.append({
            "ccid":         ccid,
            "account":      d["account"],
            "parent":       sheet_ccids.get(ccid, {}).get("parent", ""),
            "eae":          sheet_ccids.get(ccid, {}).get("eae", ""),
            "issue":        "Extra in Acct Details / Not in SIP",
            "sheet_mrr":    d["may_mrr"],
            "sip_start":    "",
            "sip_end":      "",
            "may_mrr":      d["may_mrr"],
            "notes":        "Has live MRR in Account Details but absent from SIP dashboard",
        })

    # ── 6. MRR Mismatches ────────────────────────────────────────────────────
    flagged_ccids = {f["ccid"] for f in findings}
    for ccid, s in sip.items():
        if ccid in flagged_ccids:
            continue
        if ccid in details:
            may = details[ccid]["may_mrr"]
            if abs(may - s["end_mrr"]) > 0.01:
                findings.append({
                    "ccid":         ccid,
                    "account":      s["account"],
                    "parent":       s["parent"],
                    "eae":          sheet_ccids.get(ccid, {}).get("eae", ""),
                    "issue":        "MRR Mismatch",
                    "sheet_mrr":    "",
                    "sip_start":    s["start_mrr"],
                    "sip_end":      s["end_mrr"],
                    "may_mrr":      may,
                    "notes":        f"SIP ending ${s['end_mrr']:,.0f} vs Acct Details May ${may:,.0f}",
                })

    # ── Corrected retention ──────────────────────────────────────────────────
    orig_start = sum(s["start_mrr"] for ccid, s in sip.items() if s["start_mrr"] > 0)
    orig_end   = sum(s["end_mrr"]   for ccid, s in sip.items() if s["start_mrr"] > 0)

    corr_start = orig_start
    corr_end   = orig_end

    # Remove Crown (wrong owner)
    for ccid in CROWN_EXCLUDE:
        if ccid in sip:
            s = sip[ccid]
            corr_start -= s["start_mrr"]
            corr_end   -= s["end_mrr"]

    # Add missing accounts' SF MRR (current active subscriptions = proxy for both start/end)
    missing_sf_total = 0.0
    missing_findings = [f for f in findings if f["issue"] == "Missing from SIP"]
    for f in missing_findings:
        sf_val = f["sip_start"]  # we stored sf_mrr as sip_start for missing accounts
        if isinstance(sf_val, (int, float)) and sf_val > 0:
            corr_start     += sf_val
            corr_end       += sf_val
            missing_sf_total += sf_val

    orig_ret  = (orig_end  / orig_start  * 100) if orig_start  else 0
    corr_ret  = (corr_end  / corr_start  * 100) if corr_start else 0

    summary = {
        "orig_start":       orig_start,
        "orig_end":         orig_end,
        "orig_ret":         orig_ret,
        "corr_start":       corr_start,
        "corr_end":         corr_end,
        "corr_ret":         corr_ret,
        "missing_sf_total": missing_sf_total,
        "sip_count":        len(sip),
        "exclude_count":    len([f for f in findings if f["issue"] == "Exclude — Wrong Owner"]),
        "missing_count":    len([f for f in findings if f["issue"] == "Missing from SIP"]),
        "extra_count":      len([f for f in findings if "Extra" in f["issue"]]),
        "mismatch_count":   len([f for f in findings if f["issue"] == "MRR Mismatch"]),
    }

    print(f"\n  === QC Summary ===")
    print(f"  Original retention:  {orig_ret:.2f}%  (start ${orig_start:,.0f} → end ${orig_end:,.0f})")
    print(f"  Missing accts SF MRR added to corrected: ${missing_sf_total:,.0f}")
    print(f"  Corrected retention: {corr_ret:.2f}%  (start ${corr_start:,.0f} → end ${corr_end:,.0f})")
    print(f"  Issues found: {len(findings)} total")
    for issue_type in ["Exclude — Wrong Owner", "Missing from SIP", "Extra in SIP",
                       "Extra in Acct Details / Not in SIP", "MRR Mismatch",
                       "Group Billing — Acknowledged"]:
        count = len([f for f in findings if f["issue"] == issue_type])
        if count:
            print(f"    {issue_type}: {count}")

    return findings, summary


# ─── SHEET WRITER ────────────────────────────────────────────────────────────

def fmt_mrr(val):
    if val == "" or val is None:
        return ""
    try:
        return f"${float(val):,.0f}"
    except (ValueError, TypeError):
        return str(val)


def write_qc_tab(gc, findings, summary):
    sh = gc.open_by_key(SHEET_ID)

    # Delete existing QC tab if present
    try:
        existing = sh.worksheet(QC_TAB_TITLE)
        sh.del_worksheet(existing)
        print(f"  Deleted existing '{QC_TAB_TITLE}' tab")
    except gspread.exceptions.WorksheetNotFound:
        pass

    ws = sh.add_worksheet(title=QC_TAB_TITLE, rows=str(len(findings) + 20), cols="11")

    # ── Build cell data ──────────────────────────────────────────────────────
    HEADERS = [
        "CCID", "Account Name", "Parent Group", "EAE",
        "Issue Type",
        "Sheet / May MRR", "SIP Starting MRR", "SIP Ending MRR",
        "Acct Details May MRR", "Notes",
    ]

    rows = []

    # Row 1: Title
    rows.append(["SIP QC — Jacob Crawley (MajorsCSM01) | Q2 2026", "", "", "", "", "", "", "", "", ""])
    # Row 2: blank
    rows.append([""] * 10)
    # Row 3: Retention summary
    rows.append([
        "Original Retention",
        f"{summary['orig_ret']:.2f}%",
        "",
        "Corrected Retention",
        f"{summary['corr_ret']:.2f}%",
        "",
        f"Original: Start ${summary['orig_start']:,.0f}  →  End ${summary['orig_end']:,.0f}",
        "",
        f"Corrected: Start ${summary['corr_start']:,.0f}  →  End ${summary['corr_end']:,.0f}",
        "",
    ])
    # Row 4: Account counts
    rows.append([
        "Accounts in SIP (Tableau)", str(summary["sip_count"]),
        "", "Wrong Owner (Remove)", str(summary["exclude_count"]),
        "", "Missing from SIP", str(summary["missing_count"]),
        "", f"Missing SF MRR: ${summary['missing_sf_total']:,.0f}",
    ])
    # Row 5: Other counts
    rows.append([
        "Extra in SIP / Details", str(summary["extra_count"]),
        "", "MRR Mismatches", str(summary["mismatch_count"]),
        "", "Group Billing (noted)", "1",
        "", "NOTE: Corrected retention uses current SF MRR as start+end proxy for missing accts (no March 31 snapshot available). True corrected retention requires historical MRR at Q2 start.",
    ])
    # Row 6: blank
    rows.append([""] * 10)
    # Row 7: Column headers
    rows.append(HEADERS)
    # Row 8+: Findings
    for f in findings:
        rows.append([
            f["ccid"],
            f["account"],
            f["parent"],
            f["eae"],
            f["issue"],
            fmt_mrr(f["sheet_mrr"]),
            fmt_mrr(f["sip_start"]) if f["sip_start"] != "" else "",
            fmt_mrr(f["sip_end"])   if f["sip_end"]   != "" else "",
            fmt_mrr(f["may_mrr"]),
            f["notes"],
        ])

    ws.update("A1", rows)

    # ── Formatting ────────────────────────────────────────────────────────────
    sheet_id = ws._properties["sheetId"]
    requests = []

    def cell_range(r1, c1, r2, c2):
        return {
            "sheetId": sheet_id,
            "startRowIndex": r1, "endRowIndex": r2,
            "startColumnIndex": c1, "endColumnIndex": c2,
        }

    def bg_request(r1, c1, r2, c2, color):
        return {
            "repeatCell": {
                "range": cell_range(r1, c1, r2, c2),
                "cell": {"userEnteredFormat": {"backgroundColor": color}},
                "fields": "userEnteredFormat.backgroundColor",
            }
        }

    def bold_request(r1, c1, r2, c2):
        return {
            "repeatCell": {
                "range": cell_range(r1, c1, r2, c2),
                "cell": {"userEnteredFormat": {"textFormat": {"bold": True}}},
                "fields": "userEnteredFormat.textFormat.bold",
            }
        }

    def text_color_request(r1, c1, r2, c2, color):
        return {
            "repeatCell": {
                "range": cell_range(r1, c1, r2, c2),
                "cell": {"userEnteredFormat": {"textFormat": {"foregroundColor": color}}},
                "fields": "userEnteredFormat.textFormat.foregroundColor",
            }
        }

    # Title row: purple bg, white bold text
    requests.append(bg_request(0, 0, 1, 10, PURPLE))
    requests.append(bold_request(0, 0, 1, 10))
    requests.append(text_color_request(0, 0, 1, 10, WHITE))

    # Summary rows 3-5: light gray bg, bold labels
    requests.append(bg_request(2, 0, 5, 10, {"red": 0.95, "green": 0.95, "blue": 0.95}))
    requests.append(bold_request(2, 0, 5, 1))
    requests.append(bold_request(2, 3, 5, 4))
    requests.append(bold_request(2, 6, 5, 7))

    # Header row (row 7, index 6): purple bg, white bold
    requests.append(bg_request(6, 0, 7, 10, PURPLE))
    requests.append(bold_request(6, 0, 7, 10))
    requests.append(text_color_request(6, 0, 7, 10, WHITE))

    # Color-code each data row by issue type
    data_start = 7  # 0-indexed
    for i, f in enumerate(findings):
        color = ISSUE_COLORS.get(f["issue"])
        if color:
            requests.append(bg_request(data_start + i, 0, data_start + i + 1, 10, color))

    # Bold the Issue Type column for data rows
    if findings:
        requests.append(bold_request(data_start, 4, data_start + len(findings), 5))

    # Freeze header rows (first 7 rows) and column A
    requests.append({
        "updateSheetProperties": {
            "properties": {
                "sheetId": sheet_id,
                "gridProperties": {"frozenRowCount": 7, "frozenColumnCount": 1},
            },
            "fields": "gridProperties.frozenRowCount,gridProperties.frozenColumnCount",
        }
    })

    # Auto-resize all columns
    requests.append({
        "autoResizeDimensions": {
            "dimensions": {
                "sheetId": sheet_id,
                "dimension": "COLUMNS",
                "startIndex": 0,
                "endIndex": 10,
            }
        }
    })

    sh.batch_update({"requests": requests})
    print(f"  '{QC_TAB_TITLE}' tab written with {len(findings)} findings + formatting applied")


# ─── MAIN ────────────────────────────────────────────────────────────────────

def main():
    print("── Authenticating with Google Sheets ──")
    gc = get_sheets_client()

    print("\n── Loading data ──")
    sheet_records = load_sheet_book(gc)
    sip           = load_sip_overview()
    details       = load_account_details()
    sf_mrr        = load_sf_mrr()

    print("\n── Running QC cross-reference ──")
    findings, summary = run_qc(sheet_records, sip, details, sf_mrr)

    print("\n── Writing SIP QC tab ──")
    write_qc_tab(gc, findings, summary)

    print("\n✓ Done. Open the sheet to review:")
    print(f"  https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit")


if __name__ == "__main__":
    main()
