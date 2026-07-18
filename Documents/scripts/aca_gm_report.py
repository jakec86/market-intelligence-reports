#!/usr/bin/env python3
"""
ACA Monthly GM Performance Email
Sends personalized Cars.com performance highlight emails to each ACA store GM.

Usage:
    python3 aca_gm_report.py                      # TEST MODE — one email to jcrawley@cars.com
    python3 aca_gm_report.py --send               # send to all ACA store GMs
    python3 aca_gm_report.py --draft              # create Gmail drafts instead of sending
    python3 aca_gm_report.py --month "May 2026"   # override month label

Required CSV (place in ~/Documents/Tableau/ before running):
  aca_market_opp_YYYY_MM.csv  — admin.cars.com → ACA group → Market Opportunities → Store tab
                                filter to target month → Download Crosstab → "By Store" sheet → CSV
                                Contains SRPs, VDPs, Connections, Website Transfers, Reviews, Rating.

Optional CSV (omit if not available — attribution block will adapt):
  aca_sales_attr_YYYY_MM.csv  — admin.cars.com → ACA group → Sales Attribution
                                filter to target month → Download Crosstab (if per-store export exists)
"""

import argparse, codecs, csv, io, json, os, random, re, sys, base64, subprocess
from datetime import datetime, date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import gspread
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# ─── CONFIG ───────────────────────────────────────────────────────────────────

GM_SHEET_ID  = "1oZa3ZjDO-oyQ7oCHXOzad14r--o5XdW7rPPpw3BF1i4"
GM_SHEET_GID = 1075199220  # ACA tab

TEST_EMAIL = "jcrawley@cars.com"
CC_AE      = "dmcjunkins@carscommerce.inc"  # CC'd on every sent email

TEMP_CONTACT_OVERRIDES = {
    # Jaguar Akron — sheet entry "Jaguar Land Rover Akron" resolves to Land Rover only via alias;
    # Jaguar Akron is a separate CSV store needing its own email to the same GM
    "jaguar akron": {
        "gm_name": "Milton Colon", "first_name": "Milton",
        "email": "mcolon@jaguarlandroverakron.com",
    },
    # Kenny Ross Subaru — listed as "Meeting scheduled" in GM sheet; Maureen Bailey confirmed as contact
    "kenny ross subaru": {
        "gm_name": "Maureen Bailey", "first_name": "Maureen",
        "email": "mbailey@kennyross.com",
    },
    # Mercedes-Benz of Washington — not in GM sheet; Angela Marcinizyn confirmed
    "mercedes benz of washington": {
        "gm_name": "Angela Marcinizyn", "first_name": "Angela",
        "email": "amarcinizyn@johnsissonmotors.com",
    },
    # Southern Team Hyundai Nissan Subaru Volkswagen — combined CSV store; individual GM sheet
    # rows (Hyundai/VW of Roanoke) have 0 SRPs and don't match this entry. All 4 managers on To:.
    "southern team hyundai nissan subaru volkswagen": {
        "gm_name": "Greg Shortridge", "first_name": "Greg",
        "email": "gshortridge@southernteam.com",
        "_to_list": [
            "gshortridge@southernteam.com",
            "jnardo@southernteam.com",
            "jporter@southernteam.com",
            "jramirez@southernteam.com",
        ],
    },
    # Vision Chevrolet — no entry in GM sheet; Jesus Francos manages multiple Vision stores
    "vision chevrolet": {
        "gm_name": "Jesus Francos", "first_name": "Jesus",
        "email": "jfrancos@visionauto.com",
    },
}

# NYE Automotive Group — one combined email per month to Mike Sacco listing all stores
NYE_GROUP = {
    "contact": {
        "gm_name": "Mike Sacco", "first_name": "Mike",
        "email": "msacco@nyeauto.com",
    },
    "store_keys": [
        "nye buick gmc",
        "nye chevrolet",
        "nye chrysler dodge jeep ram",
        "nye ford",
        "nye toyota",
        "nye volkswagen",
    ],
}

TOKEN_SHEETS   = os.path.expanduser("~/.claude/tokens/sheets_token.json")
TOKEN_GMAIL    = os.path.expanduser("~/.claude/tokens/gmail_jcrawley.json")
CLIENT_SECRETS = os.path.expanduser("~/gcp-oauth.keys.json")

SCOPES_SHEETS = ["https://www.googleapis.com/auth/spreadsheets"]
SCOPES_GMAIL  = [
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.modify",
]

# Store name fragments that indicate group-level rows (not individual stores)
_GROUP_KEYWORDS = [
    "all stores in",
    "automotive group",
    "auto group",
    "automall",
    "meeting scheduled",
    "kenny ross, john",   # "Kenny Ross, John Sisson, Morgantown..."
]

# Maps GM sheet store name (normalized) → exact CSV Customer Name.
# Add entries here whenever the GM sheet name and CSV name diverge.
_NAME_ALIASES = {
    # "of" wording differences
    "vision hyundai mitsubishi of webster":   "Vision Hyundai Mitsubishi Webster",
    "vision hyundai of canandaigua":           "Vision Hyundai Canandaigua",
    "vision kia of canandaigua":               "Vision Kia Canandaigua",
    "vision nissan webster":                   "Vision Nissan of Webster",
    "vision nissan canandaigua":               "Vision Nissan of Canandaigua",
    "southern chevrolet of newport news":      "Southern Chevrolet Newport News",
    "sunrise volkswagen of ft pierce":         "Sunrise Volkswagen of Fort Pierce",
    "sunrise ford of ft pierce":               "Sunrise Ford",

    # Brand name abbreviations / expansions
    "southern chrysler jeep greenbrier":               "Southern Chrysler Dodge Jeep Ram Greenbrier",
    "southern cdjr newport news":                      "Southern Chrysler Dodge Jeep Ram Newport News",
    "vision dodge chrysler jeep and ram":              "Vision Chrysler Dodge Jeep Ram",
    "morgantown cdjr":                                 "Chrysler Dodge Jeep Ram Fiat of Morgantown",
    "rob lambdin s university dodge":                  "Rob Lambdin's University Dodge RAM",

    # City / suffix differences
    "morgantown subaru":                       "Subaru of Morgantown",
    "ford lincoln of morgantown":              "Ford of Morgantown",
    "university mitsubishi":                   "University Mitsubishi - FL",
    "john sisson motors":                      "John Sisson Nissan",
    "southern team hyundai of roanoke":        "Southern Team Hyundai",
    "southern team volkswagen of roanoke":     "Southern Team Volkswagen",
    "southern chevrolet chesapeake":           "Southern Chevrolet",
    "southern ford newport news":              "Southern Ford",

    # Miami Lakes — individual brands listed in GM sheet map to combined or CDJR CSV entry
    "miami lakes dodge chrysler jeep ram":     "Miami Lakes CDJR",
    "miami lakes kia":                         "Miami Lakes Automall - Chevrolet Kia Dodge Chrysler Jeep Ram Mitsubishi",
    "miami lakes chevrolet":                   "Miami Lakes Automall - Chevrolet Kia Dodge Chrysler Jeep Ram Mitsubishi",
    "miami lakes mitsubishi":                  "Miami Lakes Automall - Chevrolet Kia Dodge Chrysler Jeep Ram Mitsubishi",

    # New Motors / Jaguar Land Rover — combined automall entries in CSV
    "new motors bmw of erie":                  "New Motors AutoMall - BMW Subaru Volkswagen",
    "new motors subaru":                       "New Motors AutoMall - BMW Subaru Volkswagen",
    "new motors volkswagen":                   "New Motors AutoMall - BMW Subaru Volkswagen",
    "jaguar land rover akron":                 "Land Rover Akron",   # Jaguar Akron handled separately via TEMP_CONTACT_OVERRIDES
}

# Overrides the display name used in email subject/body when the GM sheet label
# doesn't match the desired label. Keyed on normalized store name (lowercase).
_DISPLAY_OVERRIDES = {
    "miami lakes mitsubishi":  "Miami Lakes Chevrolet Kia Dodge Chrysler Jeep Ram Mitsubishi",
    "new motors bmw of erie":  "New Motors AutoMall - BMW Subaru Volkswagen",
    "new motors subaru":       "New Motors AutoMall - BMW Subaru Volkswagen",
    "new motors volkswagen":   "New Motors AutoMall - BMW Subaru Volkswagen",
    "sunrise ford of ft pierce": "Sunrise Ford",
}


# ─── AUTH ─────────────────────────────────────────────────────────────────────

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


# ─── CSV PARSING ──────────────────────────────────────────────────────────────

def read_csv_auto(path):
    """Read CSV with auto-detection of UTF-16/UTF-8 encoding and tab/comma delimiter."""
    raw = open(path, "rb").read(4)
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        text = codecs.open(path, encoding="utf-16").read()
    else:
        text = open(path, encoding="utf-8-sig").read()
    first_line = text.split("\n", 1)[0]
    delimiter = "\t" if "\t" in first_line else ","
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    return list(reader)


def _normalize(name):
    """Lowercase, strip punctuation, collapse spaces — for fuzzy store name matching."""
    name = name.lower()
    name = re.sub(r"[^\w\s]", " ", name)
    return re.sub(r"\s+", " ", name).strip()


def _find_col(headers, candidates):
    """Return the first header that contains any candidate substring (case-insensitive)."""
    for h in headers:
        for c in candidates:
            if c.lower() in h.lower():
                return h
    return None


def _require_col(col, name, path):
    """Abort if a critical column could not be matched — prevents silent N/A data."""
    if col is None:
        print(f"  ✗ Required column '{name}' not found in {os.path.basename(path)}")
        print(f"    Update _find_col candidates if the column was renamed.")
        sys.exit(1)


def _to_num(v):
    """Convert CSV string value to float; 0.0 for empty/invalid."""
    try:
        return float(str(v).replace(",", "").strip())
    except (ValueError, TypeError):
        return 0.0


# ─── DATA LOADERS ─────────────────────────────────────────────────────────────

def load_gm_contacts(gc):
    """
    Read the ACA tab from Danielle's GM List Google Sheet.
    Returns list of {store_name, store_key, gm_name, first_name, email}.
    Skips group-level rows and rows missing email.
    """
    sh = gc.open_by_key(GM_SHEET_ID)
    # Find the worksheet by gid
    ws = None
    for w in sh.worksheets():
        if w.id == GM_SHEET_GID:
            ws = w
            break
    if ws is None:
        print(f"  ✗ ACA tab (gid {GM_SHEET_GID}) not found in sheet")
        sys.exit(1)

    rows = ws.get_all_values()
    contacts = []

    for row in rows:
        if len(row) < 2:
            continue
        store_name = row[0].strip()
        gm_cell    = row[1].strip()

        if not store_name or not gm_cell:
            continue

        # Skip header rows
        if store_name.lower() in ("dealerships", "stores", "store", "no_header", ""):
            continue

        # Skip group-level rows
        store_lower = store_name.lower()
        if any(kw in store_lower for kw in _GROUP_KEYWORDS):
            continue

        # Parse "GM Name <email@domain.com>" or plain "email@domain.com"
        email_match = re.search(r"<([^>]+@[^>]+)>", gm_cell)
        if email_match:
            email    = email_match.group(1).strip()
            raw_name = gm_cell[: gm_cell.index("<")].strip()
            # Strip role suffix like " - GM Hollywood CJ" or " - GSM"
            gm_name  = re.split(r"\s+-\s+", raw_name)[0].strip()
        else:
            plain = re.search(r"\b[\w.+-]+@[\w.-]+\.\w+\b", gm_cell)
            if not plain:
                continue
            email   = plain.group(0).strip()
            gm_name = store_name

        if not email:
            continue

        first_name = gm_name.split()[0] if gm_name else "there"

        contacts.append({
            "store_name": store_name,
            "store_key":  _normalize(store_name),
            "gm_name":    gm_name,
            "first_name": first_name,
            "email":      email,
        })

    print(f"  ✓ Loaded {len(contacts)} GM contacts")
    return contacts


def load_kpi_data(path):
    """
    Parse Market Opportunities CSV.
    Returns (by_name_dict, by_ccid_dict) keyed on normalized store name and CCID respectively.
    Each value: {ccid, store_name, srps, vdps, connections, web_transfers, reviews, rating}
    Reviews and Rating are included here — no separate review CSV is needed.
    """
    rows = read_csv_auto(path)
    if not rows:
        print(f"  ✗ No data in {path}")
        return {}, {}

    headers = list(rows[0].keys())
    print(f"  Market Opp headers: {headers}")

    col_name    = _find_col(headers, ["Customer Name", "Store Name", "Account Name"])
    col_ccid    = _find_col(headers, ["Legacy Id", "Legacy_Id", "CCID", "Dealer Id"])
    col_srps    = _find_col(headers, ["Total SRP Imps", "SRP Imps", "Total SRPs", "SRPs"])
    col_vdps    = _find_col(headers, ["Total VDP Imps", "VDP Imps", "Total VDPs", "VDPs"])
    col_conns   = _find_col(headers, ["Total Connections", "Connections"])
    col_web_deep  = _find_col(headers, ["VDP Deep Link", "Deep Link"])
    col_web_visit = _find_col(headers, ["Visit Dealer Web Contact", "Website Transfer", "Web Transfer"])
    col_reviews   = _find_col(headers, ["Reviews Received", "Reviews", "Total Reviews"])
    col_rating    = _find_col(headers, ["Avg. Rating", "Rating Reviews", "Dealer Rating", "Overall Rating"])

    print(f"  Column map → name={col_name}, ccid={col_ccid}, srps={col_srps}, "
          f"vdps={col_vdps}, conns={col_conns}, "
          f"web_deep={col_web_deep}, web_visit={col_web_visit}, "
          f"reviews={col_reviews}, rating={col_rating}")

    _require_col(col_name,  "Customer Name (store name)", path)
    _require_col(col_ccid,  "Legacy Id / CCID",           path)
    _require_col(col_srps,  "Total SRP Imps",             path)
    _require_col(col_vdps,  "Total VDP Imps",             path)
    _require_col(col_conns, "Total Connections",          path)

    by_name, by_ccid = {}, {}
    for row in rows:
        name = (row.get(col_name) or "").strip()
        ccid = str((row.get(col_ccid) or "")).strip()
        if not name and not ccid:
            continue
        # Website Transfers = VDP Deep Links + Visit Dealer Web Contact
        web_total = (_to_num(row.get(col_web_deep, ""))  if col_web_deep  else 0.0) + \
                    (_to_num(row.get(col_web_visit, "")) if col_web_visit else 0.0)
        data = {
            "ccid":          ccid,
            "store_name":    name,
            "srps":          row.get(col_srps, ""),
            "vdps":          row.get(col_vdps, ""),
            "connections":   row.get(col_conns, ""),
            "web_transfers": str(int(web_total)) if web_total > 0 else "",
            "reviews":       row.get(col_reviews, "") if col_reviews else "",
            "rating":        row.get(col_rating, "")  if col_rating  else "",
        }
        if name:
            by_name[_normalize(name)] = data
        if ccid:
            by_ccid[ccid] = data

    print(f"  ✓ KPI data: {len(by_name)} stores")
    return by_name, by_ccid


def load_sales_data(path):
    """
    Parse Sales Attribution CSV.
    Returns {ccid: {units_influenced, total_connections, new_pct}}
    """
    rows = read_csv_auto(path)
    if not rows:
        return {}

    headers = list(rows[0].keys())
    print(f"  Sales Attr headers: {headers}")

    col_ccid  = _find_col(headers, ["CCID", "Legacy Id", "Legacy_Id", "Dealer Id"])
    col_units = _find_col(headers, ["Sales Influenced", "Units Influenced", "Influenced"])
    col_conns = _find_col(headers, ["Total Connections", "Connections"])
    col_new   = _find_col(headers, ["% Of New", "New Vehicle", "New Vehicles", "% New", "new_pct"])

    _require_col(col_ccid,  "CCID / Legacy Id",  path)
    _require_col(col_units, "Sales Influenced",   path)
    _require_col(col_conns, "Total Connections",  path)

    result = {}
    for row in rows:
        ccid = str((row.get(col_ccid) or "")).strip()
        if not ccid:
            continue
        result[ccid] = {
            "units_influenced":  row.get(col_units, ""),
            "total_connections": row.get(col_conns, ""),
            "new_pct":           row.get(col_new, ""),
        }

    print(f"  ✓ Sales data: {len(result)} stores")
    return result


def load_review_data(path):
    """
    Parse Review Data Detail CSV.
    Returns {ccid: {reviews, rating}}
    Deduplicates: keeps the row with a non-empty rating per CCID.
    """
    rows = read_csv_auto(path)
    if not rows:
        return {}

    headers = list(rows[0].keys())

    col_ccid        = _find_col(headers, ["Customer ID", "Legacy Id", "CCID", "Dealer Id"])
    col_reviews_30d = _find_col(headers, ["Cars/DR reviews", "reviews last 30"])
    col_total_rev   = _find_col(headers, ["Total Number of Reviews", "Total Number"])
    col_rating      = _find_col(headers, ["Dealer Overall Rating", "Overall Rating", "Rating"])

    result = {}
    for row in rows:
        ccid   = str((row.get(col_ccid) or "")).strip()
        rating = (row.get(col_rating) or "").strip()
        if not ccid:
            continue
        if ccid not in result or (rating and not result[ccid]["rating"]):
            result[ccid] = {
                "reviews_30d":   row.get(col_reviews_30d, "") if col_reviews_30d else "",
                "total_reviews": row.get(col_total_rev, "")   if col_total_rev   else "",
                "rating":        rating,
            }

    print(f"  ✓ Review data: {len(result)} stores")
    return result


# ─── FORMATTING ───────────────────────────────────────────────────────────────

def fmt(v):
    """None/empty → 'N/A'; number → comma-formatted integer."""
    if v is None or str(v).strip() in ("", "N/A", "#N/A", "#VALUE!"):
        return "N/A"
    try:
        n = float(str(v).replace(",", "").replace("%", "").strip())
        return f"{int(round(n)):,}"
    except (ValueError, TypeError):
        return str(v).strip() or "N/A"


def fmt_pct(v):
    """None/empty → 'N/A'; number → 'X.X%'."""
    if v is None or str(v).strip() in ("", "N/A", "#N/A"):
        return "N/A"
    try:
        n = float(str(v).replace(",", "").replace("%", "").strip())
        return f"{n:.1f}%"
    except (ValueError, TypeError):
        return str(v).strip() or "N/A"


def fmt_rating(v):
    """None/empty → 'N/A'; number → 'X.X'."""
    if v is None or str(v).strip() in ("", "N/A"):
        return "N/A"
    try:
        return f"{float(str(v).strip()):.1f}"
    except (ValueError, TypeError):
        return "N/A"


# ─── EMAIL TEMPLATE ───────────────────────────────────────────────────────────

def get_html_template():
    """HTML email template with [PLACEHOLDER] tokens for per-store substitution."""
    return """\
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f0ede8;font-family:Arial,sans-serif;">

<table width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#f0ede8;">
<tr><td align="center" style="padding:24px 16px;">

<table width="620" cellpadding="0" cellspacing="0" border="0" style="background:#ffffff;border-radius:4px;">

  <!-- HEADER -->
  <tr>
    <td style="background:#1a1a2e;padding:14px 22px;border-radius:4px 4px 0 0;">
      <table width="100%" cellpadding="0" cellspacing="0" border="0">
        <tr>
          <td style="vertical-align:middle;padding-right:20px;">
            <img src="https://admin.cars.com/images/logo_cars-856ce78c79cc80b44f2a7106e93cfea9.png" alt="Cars.com" height="40" style="display:block;" />
          </td>
          <td style="vertical-align:middle;">
            <div style="color:#ffffff;font-family:Arial,sans-serif;font-size:20px;font-weight:700;line-height:1.2;">[MONTH_LABEL] Performance Highlights</div>
            <div style="color:rgba(255,255,255,0.6);font-family:Arial,sans-serif;font-size:11px;font-weight:400;margin-top:3px;">[Dealership Name]</div>
          </td>
        </tr>
      </table>
    </td>
  </tr>

  <!-- SECTION 1: KPI TILES + ATTRIBUTION + REVIEWS -->
  <tr>
    <td style="padding:22px 28px;border-bottom:1px solid #f0ede8;">

      <!-- 4 metric tiles -->
      <table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-bottom:10px;">
        <tr>
          <td width="25%" style="padding-right:5px;">
            <table width="100%" cellpadding="0" cellspacing="0" border="0">
              <tr><td style="background:#f7f5ff;border:1px solid #ede9ff;border-radius:8px;padding:12px 10px;text-align:center;">
                <div style="font-size:9px;font-weight:600;color:#888;letter-spacing:0.06em;text-transform:uppercase;margin-bottom:6px;">SRPs</div>
                <div style="font-size:22px;font-weight:700;color:#1a1a2e;">[SRPS]</div>
              </td></tr>
            </table>
          </td>
          <td width="25%" style="padding-left:5px;padding-right:5px;">
            <table width="100%" cellpadding="0" cellspacing="0" border="0">
              <tr><td style="background:#f7f5ff;border:1px solid #ede9ff;border-radius:8px;padding:12px 10px;text-align:center;">
                <div style="font-size:9px;font-weight:600;color:#888;letter-spacing:0.06em;text-transform:uppercase;margin-bottom:6px;">VDPs</div>
                <div style="font-size:22px;font-weight:700;color:#1a1a2e;">[VDPS]</div>
              </td></tr>
            </table>
          </td>
          <td width="25%" style="padding-left:5px;padding-right:5px;">
            <table width="100%" cellpadding="0" cellspacing="0" border="0">
              <tr><td style="background:#f7f5ff;border:1px solid #ede9ff;border-radius:8px;padding:12px 10px;text-align:center;">
                <div style="font-size:9px;font-weight:600;color:#888;letter-spacing:0.06em;text-transform:uppercase;margin-bottom:6px;">Total Connections</div>
                <div style="font-size:22px;font-weight:700;color:#1a1a2e;">[CONNECTIONS]</div>
              </td></tr>
            </table>
          </td>
          <td width="25%" style="padding-left:5px;">
            <table width="100%" cellpadding="0" cellspacing="0" border="0">
              <tr><td style="background:#f7f5ff;border:1px solid #ede9ff;border-radius:8px;padding:12px 10px;text-align:center;">
                <div style="font-size:9px;font-weight:600;color:#888;letter-spacing:0.06em;text-transform:uppercase;margin-bottom:6px;">Total Website Transfers</div>
                <div style="font-size:22px;font-weight:700;color:#1a1a2e;">[WEBSITE_TRANSFERS]</div>
              </td></tr>
            </table>
          </td>
        </tr>
      </table>

      <!-- Sales Attribution block -->
      <table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-bottom:10px;">
        <tr>
          <td style="background:#1a1a2e;border-radius:8px;padding:14px 18px;">
            <div style="color:#ffffff;font-size:13px;line-height:1.7;">
              In [MONTH_LABEL] <span style="color:#C09BEC;font-weight:700;">[SALES_INFL]</span> units with Cars.com Influence - Removed from Inventory with <span style="color:#C09BEC;font-weight:700;">[TOTAL_CONNS]</span> Cars.com Connections. <span style="color:#C09BEC;font-weight:700;">[NEW_VEH_PCT]</span> were New Vehicles.
            </div>
            <div style="color:rgba(255,255,255,0.4);font-size:9px;line-height:1.4;margin-top:6px;font-style:italic;">
              Connections reflect cumulative shopper interactions on sold units over their full listing period, not monthly activity alone.
            </div>
          </td>
        </tr>
      </table>

      <!-- Reviews + Rating + Why Reviews Matter -->
      <table width="100%" cellpadding="0" cellspacing="0" border="0">
        <tr>
          <td width="33%" style="padding-right:5px;">
            <table width="100%" cellpadding="0" cellspacing="0" border="0">
              <tr><td style="background:#f7f5ff;border:1px solid #ede9ff;border-radius:8px;padding:12px 10px;text-align:center;">
                <div style="font-size:9px;font-weight:600;color:#888;letter-spacing:0.06em;text-transform:uppercase;margin-bottom:6px;">Total Reviews</div>
                <div style="font-size:22px;font-weight:700;color:#1a1a2e;">[REVIEWS]</div>
              </td></tr>
            </table>
          </td>
          <td width="33%" style="padding-left:5px;padding-right:5px;">
            <table width="100%" cellpadding="0" cellspacing="0" border="0">
              <tr><td style="background:#f7f5ff;border:1px solid #ede9ff;border-radius:8px;padding:12px 10px;text-align:center;">
                <div style="font-size:9px;font-weight:600;color:#888;letter-spacing:0.06em;text-transform:uppercase;margin-bottom:6px;">Rating</div>
                <div style="font-size:22px;font-weight:700;color:#1a1a2e;">[RATING]</div>
              </td></tr>
            </table>
          </td>
          <td width="33%" style="padding-left:5px;">
            <table width="100%" cellpadding="0" cellspacing="0" border="0">
              <tr><td style="background:#7c3aed;border-radius:8px;padding:12px 10px;text-align:center;">
                <div style="font-size:9px;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;color:rgba(255,255,255,0.75);margin-bottom:4px;">Why Reviews Matter</div>
                <div style="font-size:22px;font-weight:800;color:#ffffff;line-height:1;margin-bottom:3px;">84%</div>
                <div style="font-size:8px;color:rgba(255,255,255,0.9);line-height:1.4;">of consumers consider dealership reviews crucial to their decision-making process.</div>
              </td></tr>
            </table>
          </td>
        </tr>
      </table>

    </td>
  </tr>

  <!-- SECTION 2: MARKET MOVERS -->
  <tr>
    <td style="padding:22px 28px;border-top:1px solid #f0ede8;">
      <div style="font-size:10px;font-weight:700;color:#7c3aed;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:6px;">Market Movers</div>
      <div style="font-size:17px;font-weight:800;color:#1a1a2e;line-height:1.2;margin-bottom:10px;">Industry Insights to Watch</div>
      <p style="font-size:11px;color:#444;line-height:1.6;margin:0 0 14px;">The market is shifting rapidly, pushing shoppers toward hybrids, used inventory, and CPO vehicles. Here are the latest trends we are tracking to help you align your inventory and marketing strategies:</p>
      <table width="100%" cellpadding="0" cellspacing="0" border="0">
        <tr>
          <td style="padding-bottom:10px;vertical-align:top;">
            <table width="100%" cellpadding="0" cellspacing="0" border="0">
              <tr>
                <td style="background:#f9f6ff;border-left:3px solid #7c3aed;border-radius:0 6px 6px 0;padding:10px 14px;">
                  <div style="font-size:11px;font-weight:700;color:#1a1a2e;margin-bottom:3px;">&#9981; Fuel Prices</div>
                  <div style="font-size:11px;color:#444;line-height:1.5;">Gas has hit an average of <strong>$4.61/gallon</strong>, marking the fourth straight monthly increase.</div>
                </td>
              </tr>
            </table>
          </td>
        </tr>
        <tr>
          <td style="padding-bottom:10px;vertical-align:top;">
            <table width="100%" cellpadding="0" cellspacing="0" border="0">
              <tr>
                <td style="background:#f9f6ff;border-left:3px solid #7c3aed;border-radius:0 6px 6px 0;padding:10px 14px;">
                  <div style="font-size:11px;font-weight:700;color:#1a1a2e;margin-bottom:3px;">&#9889; EV &amp; Hybrid Demand</div>
                  <div style="font-size:11px;color:#444;line-height:1.5;">Interest in new EVs is up <strong>56% YoY</strong>, while used hybrids are currently the fastest-turning segment in the market, averaging just <strong>37 days on lot</strong>.</div>
                </td>
              </tr>
            </table>
          </td>
        </tr>
        <tr>
          <td style="vertical-align:top;">
            <table width="100%" cellpadding="0" cellspacing="0" border="0">
              <tr>
                <td style="background:#f9f6ff;border-left:3px solid #7c3aed;border-radius:0 6px 6px 0;padding:10px 14px;">
                  <div style="font-size:11px;font-weight:700;color:#1a1a2e;margin-bottom:3px;">&#128176; New Vehicle Pricing</div>
                  <div style="font-size:11px;color:#444;line-height:1.5;">Average new car prices have reached <strong>$50,718</strong>, heavily driving the consumer pivot toward more budget-friendly alternatives.</div>
                </td>
              </tr>
            </table>
          </td>
        </tr>
      </table>
    </td>
  </tr>

</table>

</td></tr>
</table>

</body>
</html>"""


def render_email(contact, kpi, sales, month_label):
    """Substitute all tokens into the template; return (subject, full_html).
    Reviews and Rating come from kpi dict (sourced from Market Opp CSV).
    Sales dict is optional; if empty, the attribution block uses an alternate copy.
    """
    intro = (
        f"<p>Hello {contact['first_name']}!</p>"
        f"<p>Below is a quick, high-level overview of your Cars.com {month_label} "
        f"activity highlights. We&rsquo;ve also included the latest market trends shaping "
        f"shopper behavior &mdash; scroll down for our June market movers. "
        f"Please don&rsquo;t hesitate to reach out with any questions!</p>"
    )

    body = get_html_template()

    # Attribution block MUST be handled before [MONTH_LABEL] is substituted,
    # so the old_block literal can match what's still in the template.
    has_sales = bool(sales.get("units_influenced") or sales.get("total_connections"))
    if has_sales:
        body = body.replace("[SALES_INFL]",  fmt(sales.get("units_influenced")))
        body = body.replace("[TOTAL_CONNS]", fmt(sales.get("total_connections")))
        body = body.replace("[NEW_VEH_PCT]", fmt_pct(sales.get("new_pct")))
    else:
        old_block = (
            'In [MONTH_LABEL] <span style="color:#C09BEC;font-weight:700;">[SALES_INFL]</span>'
            ' units with Cars.com Influence - Removed from Inventory with '
            '<span style="color:#C09BEC;font-weight:700;">[TOTAL_CONNS]</span>'
            ' Cars.com Connections. '
            '<span style="color:#C09BEC;font-weight:700;">[NEW_VEH_PCT]</span>'
            ' were New Vehicles.'
        )
        new_block = (
            f'In {month_label}, your dealership had '
            f'<span style="color:#C09BEC;font-weight:700;">{fmt(kpi.get("connections"))}</span>'
            f' Cars.com Connections and '
            f'<span style="color:#C09BEC;font-weight:700;">{fmt(kpi.get("web_transfers"))}</span>'
            f' Website Transfers &#8212; real shoppers actively engaging with your inventory.'
        )
        body = body.replace(old_block, new_block)

    # Now substitute all remaining tokens
    body = body.replace("[MONTH_LABEL]",        month_label)
    body = body.replace("[Dealership Name]",     contact["store_name"])
    body = body.replace("[SRPS]",               fmt(kpi.get("srps")))
    body = body.replace("[VDPS]",               fmt(kpi.get("vdps")))
    body = body.replace("[CONNECTIONS]",        fmt(kpi.get("connections")))
    body = body.replace("[WEBSITE_TRANSFERS]",  fmt(kpi.get("web_transfers")))
    body = body.replace("[REVIEWS]",            fmt(kpi.get("reviews")))
    body = body.replace("[RATING]",             fmt_rating(kpi.get("rating")))

    ccid    = kpi.get("ccid", "")
    subject = f"Cars.com {month_label} Performance Highlights | {contact['store_name']} | {ccid}"

    return subject, intro + body


def render_group_email(group_name, stores_data, month_label, first_name=None):
    """Render a single combined email for a multi-store group.

    stores_data: list of (store_name, kpi, sales) tuples, sorted by store name.
    Returns (subject, html_body).
    """
    def store_section(store_name, kpi, sales):
        has_sales = bool(sales.get("units_influenced") or sales.get("total_connections"))
        if has_sales:
            attr_html = (
                f'<table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-top:10px;">'
                f'<tr><td style="background:#1a1a2e;border-radius:8px;padding:12px 14px;">'
                f'<div style="color:#ffffff;font-size:12px;line-height:1.7;">'
                f'In {month_label} <span style="color:#C09BEC;font-weight:700;">{fmt(sales.get("units_influenced"))}</span> units with Cars.com Influence — Removed from Inventory with '
                f'<span style="color:#C09BEC;font-weight:700;">{fmt(sales.get("total_connections"))}</span> Cars.com Connections. '
                f'<span style="color:#C09BEC;font-weight:700;">{fmt_pct(sales.get("new_pct"))}</span> were New Vehicles.'
                f'</div>'
                f'<div style="color:rgba(255,255,255,0.4);font-size:9px;line-height:1.4;margin-top:6px;font-style:italic;">'
                f'Connections reflect cumulative shopper interactions on sold units over their full listing period, not monthly activity alone.'
                f'</div></td></tr></table>'
            )
        else:
            attr_html = (
                f'<table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-top:10px;">'
                f'<tr><td style="background:#1a1a2e;border-radius:8px;padding:12px 14px;">'
                f'<div style="color:#ffffff;font-size:12px;line-height:1.7;">'
                f'<span style="color:#C09BEC;font-weight:700;">{fmt(kpi.get("connections"))}</span> Total Connections &nbsp;&mdash;&nbsp; '
                f'<span style="color:#C09BEC;font-weight:700;">{fmt(kpi.get("web_transfers"))}</span> Website Transfers'
                f'</div></td></tr></table>'
            )

        rev    = fmt(kpi.get("reviews"))
        rating = fmt_rating(kpi.get("rating"))
        rev_str = f'{rev} reviews · {rating} ★' if rev != "N/A" else ""

        return f"""\
<tr>
  <td style="padding:16px 28px 0;">
    <div style="font-size:13px;font-weight:700;color:#1a1a2e;border-bottom:2px solid #ede9ff;
                padding-bottom:6px;margin-bottom:10px;">{store_name}</div>
    <table width="100%" cellpadding="0" cellspacing="0" border="0">
      <tr>
        <td width="25%" style="padding-right:5px;">
          <table width="100%" cellpadding="0" cellspacing="0" border="0">
            <tr><td style="background:#f7f5ff;border:1px solid #ede9ff;border-radius:8px;
                           padding:10px 8px;text-align:center;">
              <div style="font-size:8px;font-weight:600;color:#888;letter-spacing:.06em;
                          text-transform:uppercase;margin-bottom:4px;">SRPs</div>
              <div style="font-size:18px;font-weight:700;color:#1a1a2e;">{fmt(kpi.get("srps"))}</div>
            </td></tr>
          </table>
        </td>
        <td width="25%" style="padding-left:5px;padding-right:5px;">
          <table width="100%" cellpadding="0" cellspacing="0" border="0">
            <tr><td style="background:#f7f5ff;border:1px solid #ede9ff;border-radius:8px;
                           padding:10px 8px;text-align:center;">
              <div style="font-size:8px;font-weight:600;color:#888;letter-spacing:.06em;
                          text-transform:uppercase;margin-bottom:4px;">VDPs</div>
              <div style="font-size:18px;font-weight:700;color:#1a1a2e;">{fmt(kpi.get("vdps"))}</div>
            </td></tr>
          </table>
        </td>
        <td width="25%" style="padding-left:5px;padding-right:5px;">
          <table width="100%" cellpadding="0" cellspacing="0" border="0">
            <tr><td style="background:#f7f5ff;border:1px solid #ede9ff;border-radius:8px;
                           padding:10px 8px;text-align:center;">
              <div style="font-size:8px;font-weight:600;color:#888;letter-spacing:.06em;
                          text-transform:uppercase;margin-bottom:4px;">Connections</div>
              <div style="font-size:18px;font-weight:700;color:#1a1a2e;">{fmt(kpi.get("connections"))}</div>
            </td></tr>
          </table>
        </td>
        <td width="25%" style="padding-left:5px;">
          <table width="100%" cellpadding="0" cellspacing="0" border="0">
            <tr><td style="background:#f7f5ff;border:1px solid #ede9ff;border-radius:8px;
                           padding:10px 8px;text-align:center;">
              <div style="font-size:8px;font-weight:600;color:#888;letter-spacing:.06em;
                          text-transform:uppercase;margin-bottom:4px;">Web Transfers</div>
              <div style="font-size:18px;font-weight:700;color:#1a1a2e;">{fmt(kpi.get("web_transfers"))}</div>
            </td></tr>
          </table>
        </td>
      </tr>
    </table>
    {attr_html}
    {'<p style="font-size:11px;color:#999;margin:4px 0 0;">' + rev_str + '</p>' if rev_str else ''}
  </td>
</tr>
<tr><td style="padding:0 28px;"><div style="height:1px;background:#f0ede8;margin-top:16px;"></div></td></tr>"""

    store_rows = "\n".join(store_section(name, kpi, sales) for name, kpi, sales in stores_data)

    html = f"""\
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f0ede8;font-family:Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#f0ede8;">
<tr><td align="center" style="padding:24px 16px;">
<table width="620" cellpadding="0" cellspacing="0" border="0"
       style="background:#ffffff;border-radius:4px;">

  <!-- HEADER -->
  <tr>
    <td style="background:#1a1a2e;padding:14px 22px;border-radius:4px 4px 0 0;">
      <table width="100%" cellpadding="0" cellspacing="0" border="0">
        <tr>
          <td style="vertical-align:middle;padding-right:20px;">
            <img src="https://admin.cars.com/images/logo_cars-856ce78c79cc80b44f2a7106e93cfea9.png"
                 alt="Cars.com" height="40" style="display:block;" />
          </td>
          <td style="vertical-align:middle;">
            <div style="color:#ffffff;font-family:Arial,sans-serif;font-size:20px;font-weight:700;
                        line-height:1.2;">{month_label} Performance Highlights</div>
            <div style="color:rgba(255,255,255,0.6);font-family:Arial,sans-serif;font-size:11px;font-weight:400;margin-top:3px;">{group_name}</div>
          </td>
        </tr>
      </table>
    </td>
  </tr>

  <!-- INTRO -->
  <tr>
    <td style="padding:18px 28px 0;">
      {'<p style="margin:0 0 6px;font-size:13px;color:#333;font-weight:600;">Hello ' + first_name + '!</p>' if first_name else ''}
      <p style="margin:0;font-size:13px;color:#555;line-height:1.6;">
        Below is a quick, high-level overview of your Cars.com <strong>{month_label}</strong>
        activity highlights across all {len(stores_data)} {group_name} stores.
        Please don't hesitate to reach out with any questions!
      </p>
    </td>
  </tr>

  <!-- STORE SECTIONS -->
  {store_rows}

  <!-- MARKET MOVERS -->
  <tr>
    <td style="padding:22px 28px;border-top:1px solid #f0ede8;">
      <div style="font-size:10px;font-weight:700;color:#7c3aed;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:6px;">Market Movers</div>
      <div style="font-size:17px;font-weight:800;color:#1a1a2e;line-height:1.2;margin-bottom:10px;">Industry Insights to Watch</div>
      <p style="font-size:11px;color:#444;line-height:1.6;margin:0 0 14px;">The market is shifting rapidly, pushing shoppers toward hybrids, used inventory, and CPO vehicles. Here are the latest trends we are tracking to help you align your inventory and marketing strategies:</p>
      <table width="100%" cellpadding="0" cellspacing="0" border="0">
        <tr>
          <td style="padding-bottom:10px;vertical-align:top;">
            <table width="100%" cellpadding="0" cellspacing="0" border="0">
              <tr>
                <td style="background:#f9f6ff;border-left:3px solid #7c3aed;border-radius:0 6px 6px 0;padding:10px 14px;">
                  <div style="font-size:11px;font-weight:700;color:#1a1a2e;margin-bottom:3px;">&#9981; Fuel Prices</div>
                  <div style="font-size:11px;color:#444;line-height:1.5;">Gas has hit an average of <strong>$4.61/gallon</strong>, marking the fourth straight monthly increase.</div>
                </td>
              </tr>
            </table>
          </td>
        </tr>
        <tr>
          <td style="padding-bottom:10px;vertical-align:top;">
            <table width="100%" cellpadding="0" cellspacing="0" border="0">
              <tr>
                <td style="background:#f9f6ff;border-left:3px solid #7c3aed;border-radius:0 6px 6px 0;padding:10px 14px;">
                  <div style="font-size:11px;font-weight:700;color:#1a1a2e;margin-bottom:3px;">&#9889; EV &amp; Hybrid Demand</div>
                  <div style="font-size:11px;color:#444;line-height:1.5;">Interest in new EVs is up <strong>56% YoY</strong>, while used hybrids are currently the fastest-turning segment in the market, averaging just <strong>37 days on lot</strong>.</div>
                </td>
              </tr>
            </table>
          </td>
        </tr>
        <tr>
          <td style="vertical-align:top;">
            <table width="100%" cellpadding="0" cellspacing="0" border="0">
              <tr>
                <td style="background:#f9f6ff;border-left:3px solid #7c3aed;border-radius:0 6px 6px 0;padding:10px 14px;">
                  <div style="font-size:11px;font-weight:700;color:#1a1a2e;margin-bottom:3px;">&#128176; New Vehicle Pricing</div>
                  <div style="font-size:11px;color:#444;line-height:1.5;">Average new car prices have reached <strong>$50,718</strong>, heavily driving the consumer pivot toward more budget-friendly alternatives.</div>
                </td>
              </tr>
            </table>
          </td>
        </tr>
      </table>
    </td>
  </tr>

  <!-- FOOTER -->
  <tr>
    <td style="padding:18px 28px 20px;">
      <p style="margin:0;font-size:11px;color:#999;">
        Questions? Reply to this email or contact your Cars.com account team.
      </p>
    </td>
  </tr>

</table>
</td></tr>
</table>
</body>
</html>"""

    subject = f"Cars.com {month_label} Performance Highlights | {group_name}"
    return subject, html


def deliver_email(gmail, to, cc, subject, html_body, draft_mode=False, text_body=None):
    """Send or draft a single email via Gmail API. Returns message/draft id.

    text_body (optional): a plain-text alternative. If given, the message
    becomes a proper multipart/alternative (text/plain attached first, then
    text/html — per convention, clients render the last part they support).
    HTML-only emails with no plain-text part are a real spam-scoring signal
    for many mail filters; passing text_body avoids that. Default None
    preserves the exact prior HTML-only behavior for existing callers."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = "jcrawley@cars.com"
    msg["To"]      = to if isinstance(to, str) else ", ".join(to)
    if cc:
        msg["Cc"]  = cc if isinstance(cc, str) else ", ".join(cc)
    if text_body:
        msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()

    if draft_mode:
        result = gmail.users().drafts().create(
            userId="me", body={"message": {"raw": raw}}
        ).execute()
        return result.get("id")
    else:
        result = gmail.users().messages().send(
            userId="me", body={"raw": raw}
        ).execute()
        return result.get("id")


# ─── SALESFORCE LOGGING ───────────────────────────────────────────────────────

def _get_sf_creds():
    """Return (access_token, instance_url) from SF CLI session, or (None, None)."""
    try:
        result = subprocess.run(
            ["sf", "org", "display", "--json", "--target-org", "cars-commerce"],
            capture_output=True, text=True, timeout=15
        )
        data = json.loads(result.stdout).get("result", {})
        token = data.get("accessToken")
        url   = data.get("instanceUrl", "").rstrip("/")
        return (token, url) if token and url else (None, None)
    except Exception:
        return (None, None)


def get_sf_account_map(ccids):
    """
    Query SF for Account IDs by CCID. Returns ({ccid: sf_id}, {access_token, instance_url}).
    Returns ({}, {}) if SF is unreachable or query fails.
    """
    import urllib.parse, urllib.request
    token, instance_url = _get_sf_creds()
    if not token:
        return {}, {}

    unique_ccids = [c for c in set(ccids) if c]
    if not unique_ccids:
        return {}, {}

    in_clause = ", ".join(f"'{c}'" for c in unique_ccids)
    soql = f"SELECT Id, CCID__c FROM Account WHERE CCID__c IN ({in_clause})"
    url  = f"{instance_url}/services/data/v59.0/query?q={urllib.parse.quote(soql)}"

    try:
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            records = json.loads(resp.read()).get("records", [])
        account_map = {r["CCID__c"]: r["Id"] for r in records if r.get("CCID__c")}
        return account_map, {"access_token": token, "instance_url": instance_url}
    except Exception:
        return {}, {}


def log_sf_tasks(sf_log, account_map, month_label, access_token, instance_url):
    """
    Batch-insert Completed Email Tasks in SF for each sent email.
    Uses the Composite sObjects endpoint (max 200 records per call).
    Returns count of successfully logged records.
    """
    import urllib.request
    today = date.today().isoformat()
    records = []
    for entry in sf_log:
        sf_id = account_map.get(str(entry.get("ccid", "")))
        if not sf_id:
            continue
        records.append({
            "attributes": {"type": "Task"},
            "Subject":      f"Cars.com {month_label} Performance Email",
            "Status":       "Completed",
            "Type":         "Email",
            "ActivityDate": today,
            "WhatId":       sf_id,
            "Description":  f"{entry['store_name']} — {entry['subject']}",
        })

    if not records:
        return 0

    url     = f"{instance_url}/services/data/v59.0/composite/sobjects"
    payload = json.dumps({"allOrNone": False, "records": records}).encode()
    req     = urllib.request.Request(
        url, data=payload, method="POST",
        headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            results = json.loads(resp.read())
        successes = sum(1 for r in results if r.get("success"))
        failures  = [r for r in results if not r.get("success")]
        if failures:
            print(f"  ⚠  SF: {len(failures)} record(s) failed: {failures[0].get('errors', '')}")
        return successes
    except Exception as e:
        print(f"  ⚠  SF batch insert error: {e}")
        return 0


# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="ACA monthly GM performance emails")
    parser.add_argument("--month",      default=None, help='Month label, e.g. "May 2026"')
    parser.add_argument("--send",       action="store_true", help="Send to all stores (default: TEST MODE)")
    parser.add_argument("--draft",      action="store_true", help="Create Gmail drafts instead of sending")
    parser.add_argument("--market-opp",  default=None, help="Path to Market Opportunities CSV (required)")
    parser.add_argument("--sales-attr",   default=None, help="Path to Sales Attribution CSV (optional)")
    parser.add_argument("--review-data",  default=None, help="Path to Review Data Detail CSV (optional; supplies Total Reviews tile)")
    parser.add_argument("--test-count",  type=int, default=1, metavar="N",
                        help="Number of random stores to email in test mode (default: 1)")
    parser.add_argument("--store",       default=None, metavar="NAME",
                        help="Test a specific store by name (partial match, case-insensitive)")
    parser.add_argument("--to",          default=None, metavar="EMAIL",
                        help="Override test recipient address (default: TEST_EMAIL constant)")
    parser.add_argument("--nye",         action="store_true",
                        help="Send only the NYE group email (test mode)")
    args = parser.parse_args()

    test_mode   = not args.send
    test_count  = args.test_count
    month_label = args.month or datetime.now().strftime("%B %Y")
    mode_str    = "DRAFT" if args.draft else ("TEST" if test_mode else "SEND")

    print(f"\n{'='*60}")
    print(f"ACA GM Performance Emails — {month_label}")
    print(f"Mode: {mode_str}")
    print(f"{'='*60}\n")

    # ── Locate CSVs ──────────────────────────────────────────────────────────
    tableau_dir = os.path.expanduser("~/Documents/Tableau")
    aca_dir     = os.path.expanduser("~/Documents/Reports/ACA")

    def find_csv(arg_path, keywords, extra_dirs=None):
        if arg_path:
            return os.path.expanduser(arg_path)
        for d in ([tableau_dir] + (extra_dirs or [])):
            if os.path.isdir(d):
                for fname in sorted(os.listdir(d), reverse=True):
                    if all(k.lower() in fname.lower() for k in keywords):
                        return os.path.join(d, fname)
        return None

    path_kpi     = find_csv(args.market_opp,  ["aca", "market"])
    path_sales   = find_csv(args.sales_attr,  ["aca", "sales"])
    path_reviews = find_csv(args.review_data, ["review"],        extra_dirs=[aca_dir])

    if not path_kpi:
        print("✗ Missing required CSV: Market Opportunities — name it aca_market_opp_YYYY_MM.csv in ~/Documents/Tableau/")
        print("  admin.cars.com → ACA group → Market Opportunities → Store tab → filter month → Download Crosstab → By Store → CSV")
        sys.exit(1)

    print(f"[1/5] CSV sources:")
    print(f"  KPI (required):     {path_kpi}")
    print(f"  Sales (optional):   {path_sales   or 'not found — attribution block will use connections data'}")
    print(f"  Reviews (optional): {path_reviews or 'not found — Reviews tile will use Market Opp data'}\n")

    # ── Auth ─────────────────────────────────────────────────────────────────
    print("[2/5] Authenticating...")
    gc    = get_sheets_client()
    gmail = get_gmail_service()
    print("  ✓ Sheets + Gmail ready\n")

    # ── Load data ────────────────────────────────────────────────────────────
    print("[3/5] Loading contacts and data...")
    contacts                 = load_gm_contacts(gc)
    for c in contacts:
        if c["store_key"] in _DISPLAY_OVERRIDES:
            c["store_name"] = _DISPLAY_OVERRIDES[c["store_key"]]
    kpi_by_name, kpi_by_ccid = load_kpi_data(path_kpi)
    sales_data               = load_sales_data(path_sales)   if path_sales   else {}
    review_data              = load_review_data(path_reviews) if path_reviews else {}
    if not path_sales:
        print("  ℹ  No sales CSV — attribution block will show Connections + Website Transfers")
    if not path_reviews:
        print("  ℹ  No review CSV — Reviews tile will use Market Opp monthly count")

    # Inject temp overrides for stores without a GM contact in the sheet yet
    existing_keys = {c["store_key"] for c in contacts}
    for store_key, override in TEMP_CONTACT_OVERRIDES.items():
        if store_key not in existing_keys and kpi_by_name.get(store_key):
            kpi_row = kpi_by_name[store_key]
            entry = {
                "store_name":   kpi_row.get("name", store_key.title()),
                "store_key":    store_key,
                "gm_name":      override["gm_name"],
                "first_name":   override["first_name"],
                "email":        override["email"],
                "_cc_override": override.get("cc", []),
            }
            if "_to_list" in override:
                entry["_to_list"] = override["_to_list"]
            contacts.append(entry)
            print(f"  ℹ  {kpi_row.get('name', store_key)} — no GM contact; routing to {override['email']} (temp)")
    print()

    # ── Generate and deliver ──────────────────────────────────────────────────
    print("[4/5] Generating emails...")
    sent, skipped = 0, []
    sf_log = []

    send_list = contacts
    if test_mode:
        def _has_kpi(c):
            if kpi_by_name.get(c["store_key"]):
                return True
            alias = _NAME_ALIASES.get(c["store_key"])
            return bool(alias and kpi_by_name.get(_normalize(alias)))
        eligible = [c for c in contacts if _has_kpi(c)]
        if args.nye:
            send_list = []
            _test_dest = args.to if args.to else TEST_EMAIL
            print(f"  Test mode: NYE group email only → {_test_dest}\n")
        elif args.store:
            needle = args.store.lower()
            eligible = [c for c in eligible if needle in c["store_name"].lower()]
            if not eligible:
                print(f"  ✗ No matched store found for --store '{args.store}'")
                sys.exit(1)
            send_list = eligible[:test_count]
            _test_dest = args.to if args.to else TEST_EMAIL
            print(f"  Test mode: sending {len(send_list)} of {len(eligible)} matched stores to {_test_dest}\n")
        else:
            random.shuffle(eligible)
            send_list = eligible[:test_count]
            _test_dest = args.to if args.to else TEST_EMAIL
            print(f"  Test mode: sending {len(send_list)} of {len(eligible)} matched stores to {_test_dest}\n")

    for contact in send_list:
        kpi = kpi_by_name.get(contact["store_key"])
        if not kpi:
            # Try alias map
            alias_csv_name = _NAME_ALIASES.get(contact["store_key"])
            if alias_csv_name:
                kpi = kpi_by_name.get(_normalize(alias_csv_name))
        if not kpi:
            skipped.append(f"{contact['store_name']} — no KPI match (check store name in CSV or _NAME_ALIASES)")
            continue

        # Skip stores not active on Cars.com marketplace (0 SRPs = not listing)
        srps_raw = str(kpi.get("srps", "") or "").replace(",", "").strip()
        try:
            srps_val = float(srps_raw)
        except (ValueError, TypeError):
            srps_val = 0.0
        if srps_val == 0:
            skipped.append(f"{contact['store_name']} — 0 SRPs, not active on marketplace")
            continue

        kpi   = dict(kpi)  # shallow copy — avoid mutating shared alias entries
        ccid  = kpi.get("ccid", "")
        sales = sales_data.get(ccid, {})

        # Supplement reviews/rating from Review Data Detail CSV (total reviews preferred over monthly)
        if review_data and ccid in review_data:
            rv = review_data[ccid]
            if rv.get("total_reviews"):
                kpi["reviews"] = rv["total_reviews"]
            if rv.get("rating") and not kpi.get("rating"):
                kpi["rating"] = rv["rating"]

        subject, html_body = render_email(contact, kpi, sales, month_label)

        if test_mode:
            to      = args.to if args.to else TEST_EMAIL
            cc      = [TEST_EMAIL] if args.to and args.to != TEST_EMAIL else []
            subject = f"[TEST] {subject}"
        else:
            to = contact.get("_to_list", contact["email"])
            cc = [CC_AE] if CC_AE not in (to if isinstance(to, list) else [to]) else []

        try:
            deliver_email(gmail, to, cc, subject, html_body, draft_mode=args.draft)
            action = "Drafted" if args.draft else "Sent"
            print(f"  ✓ {action}: {contact['store_name']} → {to}")
            sent += 1
            if not args.draft:
                sf_log.append({"ccid": ccid, "store_name": contact["store_name"], "subject": subject})
        except Exception as e:
            print(f"  ✗ Failed: {contact['store_name']} — {e}")
            skipped.append(f"{contact['store_name']} — error: {e}")

    if test_mode:
        print(f"\n  {sent} test email(s) sent to {TEST_EMAIL}.")
        print("  Check your inbox, verify emails look correct, then re-run with --send.")

    # ── NYE group email ───────────────────────────────────────────────────────
    nye_stores_data = []
    for sk in NYE_GROUP["store_keys"]:
        kpi = kpi_by_name.get(sk)
        if not kpi:
            continue
        srps_raw = str(kpi.get("srps", "") or "").replace(",", "").strip()
        try:
            srp_val = float(srps_raw)
        except (ValueError, TypeError):
            srp_val = 0.0
        if srp_val == 0:
            continue
        kpi  = dict(kpi)
        ccid = kpi.get("ccid", "")
        if review_data and ccid in review_data:
            rv = review_data[ccid]
            if rv.get("total_reviews"):
                kpi["reviews"] = rv["total_reviews"]
            if rv.get("rating") and not kpi.get("rating"):
                kpi["rating"] = rv["rating"]
        store_name = _DISPLAY_OVERRIDES.get(sk, kpi.get("store_name", sk.title()))
        sales = sales_data.get(ccid, {})
        nye_stores_data.append((store_name, kpi, sales))

    if nye_stores_data:
        nye_stores_data.sort(key=lambda x: x[0])
        nye_subject, nye_body = render_group_email("NYE Automotive Group", nye_stores_data, month_label, first_name=NYE_GROUP["contact"]["first_name"])
        nye_contact = NYE_GROUP["contact"]
        if test_mode:
            nye_to      = args.to if args.to else TEST_EMAIL
            nye_cc      = []
            nye_subject = f"[TEST] {nye_subject}"
        else:
            nye_to = nye_contact["email"]
            nye_cc = [CC_AE] if CC_AE != nye_to else []
        try:
            deliver_email(gmail, nye_to, nye_cc, nye_subject, nye_body, draft_mode=args.draft)
            action = "Drafted" if args.draft else "Sent"
            print(f"  ✓ {action} NYE group email ({len(nye_stores_data)} stores) → {nye_to}")
            sent += 1
        except Exception as e:
            print(f"  ✗ Failed NYE group email — {e}")
            skipped.append(f"NYE Automotive Group — error: {e}")

    # ── Salesforce logging ────────────────────────────────────────────────────
    if sf_log and not args.draft:
        print("\n[5/5] Logging to Salesforce...")
        account_map, sf_creds = get_sf_account_map([e["ccid"] for e in sf_log])
        if account_map:
            sf_logged = log_sf_tasks(sf_log, account_map, month_label, **sf_creds)
            print(f"  ✓ {sf_logged} of {len(sf_log)} sends logged to Salesforce")
        else:
            print("  ⚠  Salesforce unreachable — skipped (emails were sent successfully)")

    # ── Summary ───────────────────────────────────────────────────────────────
    step = "6" if (sf_log and not args.draft) else "5"
    action_word = "drafted" if args.draft else "sent"
    print(f"\n[{step}/{step}] Done — {sent} emails {action_word}")
    if skipped:
        print(f"  {len(skipped)} skipped:")
        for s in skipped:
            print(f"    • {s}")
    print(f"\n{'='*60}\n")


if __name__ == "__main__":
    main()
