#!/usr/bin/env python3
"""
ACA Price Badge Report — per-store Gmail drafts from a Tableau LEI export.

Usage:
    python3 aca_pb_report.py --lei ~/Downloads/aca_lei.csv
    python3 aca_pb_report.py --lei ~/Downloads/aca_lei.csv --threshold 500 --dry-run
    python3 aca_pb_report.py --lei ~/Downloads/aca_lei.csv --send   # skip drafts, send directly

Pre-send review rule: all drafts go to jcrawley@cars.com first.
Flip PRESEND=False only after Jake approves the format.

GM contacts are read live from the Danielle GM List Google Sheet (ACA tab).
Sheet ID: 1oZa3ZjDO-oyQ7oCHXOzad14r--o5XdW7rPPpw3BF1i4
"""

import argparse, base64, codecs, csv, io, json, os, re, sys, time, urllib.request, urllib.parse
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# ── CONFIG ────────────────────────────────────────────────────────────────────

THRESHOLD_DEFAULT = 500
PRESEND           = False         # True = all drafts go to Jake; False = client direct
PRESEND_TO        = "jcrawley@cars.com"
CC_ALWAYS         = "dmcjunkins@carscommerce.inc"   # Danielle always CC'd
ACA_PB_SHEET_URL  = "https://docs.google.com/spreadsheets/d/1aNX9cATbgVWTefK-a4O_ektZLd6DxNoRln80AL5rLcA/edit#gid=565895707"
GM_SHEET_ID       = "1oZa3ZjDO-oyQ7oCHXOzad14r--o5XdW7rPPpw3BF1i4"
GM_SHEET_TAB      = "ACA"
TOP_N             = 5             # max vehicles to list per email

# Virtual/delivery stores — LEI includes these cross-market listings; skip for emails
VIRTUAL_STORE_PATTERNS = [
    "delivery from",
    "nowcar",
    "nye automotive group - delivery",
]

# Manual name overrides: LEI dealer name → GM sheet dealer name
DEALER_NAME_MAP = {
    "ford of morgantown":                      "ford lincoln of morgantown",
    "ford lincoln of morgantown":              "ford lincoln of morgantown",
    "subaru of morgantown":                    "morgantown subaru",
    "chrysler dodge jeep ram fiat of morgantown": "morgantown cdjr",
    "university mitsubishi - fl":              "university mitsubishi",
    "southern chevrolet":                      "southern chevrolet chesapeake",
    "southern chevrolet newport news":         "southern chevrolet of newport news",
    "southern ford":                           "southern ford newport news",
    "southern chrysler dodge jeep ram greenbrier": "southern chrysler jeep greenbrier",
    "southern dodge chrysler jeep ram fiat norfolk": "southern dodge chrysler jeep ram fiat norfolk",
    "southern chrysler dodge jeep ram newport news": "southern cdjr newport news",
    "vision hyundai canandaigua":              "vision hyundai of canandaigua",
    "vision hyundai mitsubishi webster":       "vision hyundai mitsubishi of webster",
    "vision kia canandaigua":                  "vision kia of canandaigua",
    "vision chrysler dodge jeep ram":          "vision dodge chrysler jeep and ram",
    "vision nissan of canandaigua":            "vision nissan canandaigua",
    "vision nissan of webster":                "vision nissan webster",
    "new motors automall - bmw subaru volkswagen": "new motors subaru",  # send to Allen Yingling or pick one GM
    "southern acura newport news":             "southern acura newport news",
    "jaguar land rover akron":                 "jaguar land rover akron",
    "rob lambdin's university dodge ram":      "rob lambdin's university dodge",
    "southern team hyundai nissan subaru volkswagen": "southern team hyundai of roanoke",
    "southern team nissan of new river valley": "southern team nissan of new river valley",
    "sunrise ford":                            "sunrise ford of ft pierce",
    "nye buick gmc":                           "nye automotive group",
    "nye chevrolet":                           "nye automotive group",
    "nye chrysler dodge jeep ram":             "nye automotive group",
    "nye ford":                                "nye automotive group",
    "nye toyota":                              "nye automotive group",
    "nye volkswagen":                          "nye automotive group",
    "new motors automall - bmw subaru volkswagen": None,   # skip — platform director (Allen Yingling); aggregate separately
    "mercedes benz of washington":             None,   # skip — no contact in GM sheet
}

TOKEN_GMAIL       = os.path.expanduser("~/.claude/tokens/gmail_jcrawley.json")
TOKEN_SHEETS      = os.path.expanduser("~/.claude/tokens/sheets_token.json")
CLIENT_SECRETS    = os.path.expanduser("~/gcp-oauth.keys.json")
SCOPES_GMAIL      = ["https://www.googleapis.com/auth/gmail.compose",
                      "https://www.googleapis.com/auth/gmail.modify"]
SCOPES_SHEETS     = ["https://www.googleapis.com/auth/spreadsheets"]

_LEI_EXPECTED = ["Dealer name", "Dealer id", "Stock num", "VIN", "Make name"]


# ── AUTH ──────────────────────────────────────────────────────────────────────

def _load_creds(token_path, scopes):
    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, scopes)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            from google_auth_oauthlib.flow import InstalledAppFlow
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS, scopes)
            creds = flow.run_local_server(port=0)
        with open(token_path, "w") as f:
            f.write(creds.to_json())
    return creds


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


def _sheets_token():
    """Return a valid Sheets API access token, refreshing if needed."""
    data = json.load(open(TOKEN_SHEETS))
    creds = Credentials.from_authorized_user_file(TOKEN_SHEETS, SCOPES_SHEETS)
    if not creds.valid and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        data["token"] = creds.token
        with open(TOKEN_SHEETS, "w") as f:
            json.dump(data, f, indent=2)
    return data.get("token") or creds.token


def _sheets_request(method, path, body=None, token=None):
    """Make a Sheets API REST call. Returns parsed JSON."""
    url = f"https://sheets.googleapis.com/v4/spreadsheets{path}"
    payload = json.dumps(body).encode() if body else None
    req = urllib.request.Request(
        url, data=payload, method=method,
        headers={"Authorization": f"Bearer {token}",
                 "Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as r:
        return json.load(r)


# ── GOOGLE SHEET BUILDER ──────────────────────────────────────────────────────

PURPLE = {"red": 0.42, "green": 0.18, "blue": 0.55}
WHITE  = {"red": 1.0,  "green": 1.0,  "blue": 1.0}
TEAL   = {"red": 0.0,  "green": 0.66, "blue": 0.56}

SHEET_HEADERS = ["Vehicle", "Stock #", "Current Badge", "Drop Needed", "Target Price"]


def create_pb_sheet(by_dealer, threshold, today_str):
    """
    Create a Google Sheet with one tab per store via Sheets REST API.
    Returns dict: dealer_name → direct tab URL (with #gid=...).
    """
    token = _sheets_token()
    title = f"ACA Price Badge Report — {today_str}"
    print(f"  Creating Google Sheet: {title}")

    dealers_sorted = [d for d in sorted(by_dealer.keys())]

    # Create spreadsheet with all sheets defined up-front (one API call)
    sheets_def = [{"properties": {"title": d[:99]}} for d in dealers_sorted]
    body = {"properties": {"title": title}, "sheets": sheets_def}
    resp = _sheets_request("POST", "", body=body, token=token)

    sid = resp["spreadsheetId"]
    base_url = f"https://docs.google.com/spreadsheets/d/{sid}/edit"
    print(f"  ✓ Sheet: {base_url}")

    # Build lookup: dealer name → sheet GID
    sheet_meta = {s["properties"]["title"]: s["properties"]["sheetId"]
                  for s in resp["sheets"]}

    dealer_urls = {}
    value_data  = []   # for batch values write
    fmt_requests = []  # for batch format

    for dealer_name in dealers_sorted:
        vehicles   = by_dealer[dealer_name]
        safe_title = dealer_name[:99]
        gid        = sheet_meta.get(safe_title, 0)
        dealer_urls[dealer_name] = f"{base_url}#gid={gid}"

        # Values: title row, blank, headers, data
        rows = [
            [f"{dealer_name} — Price Badge Opportunities (within ${threshold:,}) — {today_str}"],
            [],
            SHEET_HEADERS,
        ] + [[v["ymmt"], v["stock"], v["current_badge"], v["diff"], v["target_price"]]
             for v in vehicles]

        value_data.append({
            "range": f"'{safe_title}'!A1",
            "values": rows,
        })

        # Format requests for this tab
        fmt_requests += [
            {"mergeCells": {
                "range": {"sheetId": gid, "startRowIndex": 0, "endRowIndex": 1,
                          "startColumnIndex": 0, "endColumnIndex": 5},
                "mergeType": "MERGE_ALL"}},
            {"repeatCell": {
                "range": {"sheetId": gid, "startRowIndex": 0, "endRowIndex": 1,
                          "startColumnIndex": 0, "endColumnIndex": 5},
                "cell": {"userEnteredFormat": {
                    "backgroundColor": PURPLE,
                    "textFormat": {"foregroundColor": WHITE, "bold": True, "fontSize": 13},
                    "horizontalAlignment": "CENTER", "verticalAlignment": "MIDDLE"}},
                "fields": "userEnteredFormat"}},
            {"repeatCell": {
                "range": {"sheetId": gid, "startRowIndex": 2, "endRowIndex": 3,
                          "startColumnIndex": 0, "endColumnIndex": 5},
                "cell": {"userEnteredFormat": {
                    "backgroundColor": TEAL,
                    "textFormat": {"foregroundColor": WHITE, "bold": True},
                    "horizontalAlignment": "CENTER"}},
                "fields": "userEnteredFormat"}},
            {"updateSheetProperties": {
                "properties": {"sheetId": gid,
                               "gridProperties": {"frozenRowCount": 3}},
                "fields": "gridProperties.frozenRowCount"}},
            {"updateDimensionProperties": {
                "range": {"sheetId": gid, "dimension": "COLUMNS",
                          "startIndex": 0, "endIndex": 1},
                "properties": {"pixelSize": 310}, "fields": "pixelSize"}},
            {"updateDimensionProperties": {
                "range": {"sheetId": gid, "dimension": "COLUMNS",
                          "startIndex": 1, "endIndex": 2},
                "properties": {"pixelSize": 110}, "fields": "pixelSize"}},
            {"updateDimensionProperties": {
                "range": {"sheetId": gid, "dimension": "COLUMNS",
                          "startIndex": 2, "endIndex": 5},
                "properties": {"pixelSize": 130}, "fields": "pixelSize"}},
            {"updateDimensionProperties": {
                "range": {"sheetId": gid, "dimension": "ROWS",
                          "startIndex": 0, "endIndex": 1},
                "properties": {"pixelSize": 40}, "fields": "pixelSize"}},
        ]

    # Batch write all values
    _sheets_request("POST", f"/{sid}/values:batchUpdate",
                    body={"valueInputOption": "RAW", "data": value_data}, token=token)

    # Batch apply formatting
    _sheets_request("POST", f"/{sid}:batchUpdate",
                    body={"requests": fmt_requests}, token=token)

    return dealer_urls


# ── CSV PARSING ───────────────────────────────────────────────────────────────

def read_csv_auto(path):
    """Read a Tableau export CSV, handling UTF-16 or UTF-8 and tab vs comma."""
    try:
        text = codecs.open(path, encoding="utf-16").read()
    except Exception:
        text = open(path, encoding="utf-8-sig").read()
    delimiter = "\t" if "\t" in text[:2000] else ","
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    return list(reader)


def clean_num(val):
    """Strip $, commas; return float or None."""
    if not val:
        return None
    s = val.replace("$", "").replace(",", "").strip()
    try:
        return float(s)
    except ValueError:
        return None


def validate_headers(path, rows, expected):
    if not rows:
        sys.exit(f"ERROR: {path} is empty.")
    actual = rows[0]
    for col in expected:
        if not any(col.lower() in h.lower() for h in actual):
            print(f"WARNING: Expected column '{col}' not found in {path}")
            print(f"  Actual headers: {actual[:8]}")


# ── LEI PROCESSING ────────────────────────────────────────────────────────────

def parse_lei(rows, threshold):
    """
    Returns dict: dealer_name → list of vehicle dicts within threshold.

    Sign convention in this ACA export (opposite from Hendrick):
      - "Not Badged" / "Not Badged - Review Price": positive good_diff = drop needed for Good
      - "Fair": negative good_diff = drop needed for Good (abs value)
      - "Good": negative great_diff = drop needed for Great (abs value)
    We normalise to drop_needed > 0 in all cases.
    """
    if not rows:
        return {}

    hdr = rows[0]
    def cidx(keyword):
        for i, h in enumerate(hdr):
            if keyword.lower() in h.lower():
                return i
        return None

    idx_dealer     = cidx("dealer name")    or 0
    idx_stock      = cidx("stock num")      or 2
    idx_vin        = cidx("vin")            or 3
    idx_ymmt       = cidx("ymmt")           or 5
    idx_badge      = cidx("price badge")    or 6
    idx_price      = cidx("sum of price")   or 11
    idx_good_diff  = cidx("difference - good")  or 14
    idx_great_diff = cidx("difference - great") or 16

    seen_stocks = set()
    by_dealer   = {}

    for row in rows[1:]:
        if len(row) < 6:
            continue

        dealer  = row[idx_dealer].strip()  if len(row) > idx_dealer  else ""
        stock   = row[idx_stock].strip()   if len(row) > idx_stock   else ""
        vin     = row[idx_vin].strip()     if len(row) > idx_vin     else ""
        ymmt    = row[idx_ymmt].strip()    if len(row) > idx_ymmt    else ""
        badge   = row[idx_badge].strip()   if len(row) > idx_badge   else ""
        price_s = row[idx_price].strip()   if len(row) > idx_price   else ""

        if not dealer or not stock:
            continue

        key = (dealer, stock)
        if key in seen_stocks:
            continue
        seen_stocks.add(key)

        price = clean_num(price_s)

        # Determine which diff column applies and normalise drop_needed > 0
        if badge in ("Not Badged", "Not Badged - Review Price"):
            # Positive diff = drop needed for Good
            raw = row[idx_good_diff].strip() if len(row) > idx_good_diff else ""
            diff = clean_num(raw)
            next_badge = "Good"
            drop_needed = diff if (diff is not None and diff > 0) else 0.0
        elif badge == "Fair":
            # Check path to Good first (negative diff = drop needed for Good)
            raw = row[idx_good_diff].strip() if len(row) > idx_good_diff else ""
            diff = clean_num(raw)
            next_badge = "Good"
            drop_needed = -diff if (diff is not None and diff < 0) else 0.0
        elif badge == "Good":
            # Negative great_diff = drop needed for Great
            raw = row[idx_great_diff].strip() if len(row) > idx_great_diff else ""
            diff = clean_num(raw)
            next_badge = "Great"
            drop_needed = -diff if (diff is not None and diff < 0) else 0.0
        else:
            continue  # Great = already maxed; skip unknown badges

        if not (0 < drop_needed <= threshold):
            continue

        target_price = f"${price - drop_needed:,.0f}" if price else "—"

        vehicle = {
            "dealer":        dealer,
            "stock":         stock,
            "vin":           vin,
            "ymmt":          ymmt,
            "price":         f"${price:,.0f}" if price else "—",
            "current_badge": badge,
            "next_badge":    next_badge,
            "diff":          f"${drop_needed:,.0f}",
            "target_price":  target_price,
        }

        by_dealer.setdefault(dealer, []).append(vehicle)

    # Sort each dealer's list by drop amount ascending (smallest drop first)
    for dealer in by_dealer:
        by_dealer[dealer].sort(key=lambda v: clean_num(v["diff"].replace("$","").replace(",","")) or 0)

    return by_dealer


# ── GM CONTACT MATCHING ───────────────────────────────────────────────────────

def load_gm_contacts(sheets_svc=None):
    """
    Return ACA GM contacts as dict: normalized_name → {name, email}.
    Hardcoded from the Danielle GM List Sheet (ACA tab, loaded 2026-06-24).
    Source: Sheet 1oZa3ZjDO-oyQ7oCHXOzad14r--o5XdW7rPPpw3BF1i4, ACA tab.
    """
    raw = [
        ("(New Motors) BMW of Erie",                     "Tony Confer",          "tonyconfer@newmotors.com"),
        ("Audi Lakeland",                                "Sidd Chandra",         "sidd@audilakeland.com"),
        ("Aventura Chrysler Jeep Dodge Ram",             "Oren Cohen",           "ocohen@aventuracjdr.com"),
        ("Cape Coral Chrysler Dodge Jeep Ram",           "Josh Clinton",         "josh.clinton@capecoralcdjr.com"),
        ("Drivers Automart",                             "Dyango Ramirez",       "dyango.ramirez@driversautomart.com"),
        ("Ford Lincoln of Morgantown",                   "Cade Ingram",          "cingram@fordmorgantown.com"),
        ("Hollywood Chrysler Jeep",                      "Nick Burba",           "nick.burba@hollywoodcj.com"),
        ("Jaguar Land Rover Akron",                      "Milton Colon",         "mcolon@jaguarlandroverakron.com"),
        ("John Sisson Motors",                           "Angela Marcinizyn",    "amarcinizyn@johnsissonmotors.com"),
        ("John Sisson Nissan",                           "Jim Fronzaglio",       "jfronzaglio@johnsissonmotors.com"),
        ("Kendall Dodge Chrysler Jeep Ram",              "Carlos Rodriguez",     "carlos.rodriguez@kendalldcjr.com"),
        ("Kenny Ross Ford",                              "John Eberlein",        "jeberlein@kennyross.com"),
        ("Kenny Ross Ford South",                        "Benjamin Leone",       "bleone@kennyross.com"),
        ("Kenny Ross Mazda",                             "Joe Woleslagle",       "jwoleslagle@kennyross.com"),
        ("Kenny Ross Subaru",                            "Maureen Bailey",       "mbailey@kennyross.com"),
        ("Miami Lakes Chevrolet",                        "Lazaro Veliz",         "lazaro.veliz@miamilakesautomall.com"),
        ("Miami Lakes Dodge Chrysler Jeep Ram",          "Albert Lopez",         "albert.lopez@miamilakesautomall.com"),
        ("Miami Lakes Kia",                              "Victor Heredia",       "victor.heredia@miamilakesautomall.com"),
        ("Miami Lakes Mitsubishi",                       "Lazaro Veliz",         "lazaro.veliz@miamilakesautomall.com"),
        ("Morgantown CDJR",                              "Eric Kinkead",         "ekinkead@cdjrmorgantown.com"),
        ("Morgantown Subaru",                            "Eric Kinkead",         "ekinkead@cdjrmorgantown.com"),
        ("New Motors Subaru",                            "Ryan Franklin",        "ryanf@newmotors.com"),
        ("New Motors Volkswagen",                        "Tony Confer",          "tonyconfer@newmotors.com"),
        ("Nissan Of Fort Pierce",                        "Jay Ganzi",            "jay.ganzi@nissanoffortpierce.com"),
        ("Rob Lambdin's University Dodge",               "Nick Salerno",         "nick.salerno@universitydodge.com"),
        ("Southern Acura Newport News",                  "Travis Battles",       "travis.battles@drivingsouthern.com"),
        ("Southern Alfa Romeo of Norfolk",               "Cameron Shaw",         "cshaw@drivingsouthern.com"),
        ("Southern Buick GMC Greenbrier",                "Brett Lloyd",          "blloyd@drivingsouthern.com"),
        ("Southern Buick GMC Virginia Beach",            "David Jensen",         "djensen@drivingsouthern.com"),
        ("Southern CDJR Newport News",                   "Brison Chu",           "bchu@drivingsouthern.com"),
        ("Southern Chevrolet Chesapeake",                "Steven Santomieri",    "steven.santomieri@drivingsouthern.com"),
        ("Southern Chevrolet of Newport News",           "Nathan Hollis",        "nhollis@drivingsouthern.com"),
        ("Southern Chrysler Dodge Jeep RAM Chesapeake",  "Nate Enlow",           "nenlow@drivingsouthern.com"),
        ("Southern Chrysler Jeep Greenbrier",            "Joe Cuellar",          "jcuellar@drivingsouthern.com"),
        ("Southern Dodge Chrysler Jeep Ram Fiat Norfolk","Cameron Shaw",         "cshaw@drivingsouthern.com"),
        ("Southern Ford Newport News",                   "Manny Patel",          "manal.patel@drivingsouthern.com"),
        ("Southern Hyundai Chesapeake",                  "Jay Cunningham",       "jcunningham@drivingsouthern.com"),
        ("Southern Hyundai Newport News",                "Keith McCullers",      "keith.mccullers@drivingsouthern.com"),
        ("Southern Kia Greenbrier",                      "Brett Lloyd",          "blloyd@drivingsouthern.com"),
        ("Southern Kia Virginia Beach",                  "David Jensen",         "djensen@drivingsouthern.com"),
        ("Southern Liquidation Outlet",                  "David Barrett",        "dbarrett@drivingsouthern.com"),
        ("Southern Mazda Newport News",                  "Byron Reese",          "BReese@drivingsouthern.com"),
        ("Southern Nissan Chesapeake",                   "Joseph Jensen",        "joe.jensen@drivingsouthern.com"),
        ("Southern Team Hyundai of Roanoke",             "Greg Shortridge",      "gshortridge@southernteam.com"),
        ("Southern Team Nissan of New River Valley",     "James Nardo",          "jnardo@southernteam.com"),
        ("Southern Team Nissan of Roanoke",              "Jason Porter",         "jporter@southernteam.com"),
        ("Southern Team Subaru",                         "Jason Porter",         "jporter@southernteam.com"),
        ("Southern Team Volkswagen of Roanoke",          "Juan Ramirez",         "jramirez@southernteam.com"),
        ("Southern Volkswagen Greenbrier",               "Peter Faris",          "pfaris@drivingsouthern.com"),
        ("Sunrise Ford of Ft Pierce",                    "Alex Medina",          "Alex@sunrise-ford.com"),
        ("Sunrise Volkswagen of Ft Pierce",              "Michael Eagle",        "mike@sunrise-vw.com"),
        ("University Mitsubishi",                        "Nick Salerno",         "nick.salerno@universitydodge.com"),
        ("Vision Buick GMC",                             "Anthony Farina",       "anthony@visionauto.com"),
        ("Vision Dodge Chrysler Jeep and Ram",           "Joe Foster",           "jfoster@visionauto.com"),
        ("Vision Hyundai Henrietta",                     "Justin Morgante",      "jmorgante@visionauto.com"),
        ("Vision Hyundai Mitsubishi of Webster",         "Justin Morgante",      "jmorgante@visionauto.com"),
        ("Vision Hyundai of Canandaigua",                "Steven Mansfield",     "smansfield@visionauto.com"),
        ("Vision Kia East Rochester",                    "Ziad Hasasneh",        "ziad@visionauto.com"),
        ("Vision Kia of Canandaigua",                    "Ziad Hasasneh",        "ziad@visionauto.com"),
        ("Vision Chevrolet",                             "Jesus Francos",        "jfrancos@visionauto.com"),
        ("Vision Nissan Canandaigua",                    "Thomas Conradt",       "thomas@visionauto.com"),
        ("Vision Nissan Greece",                         "Michael Morton",       "mmorton@visionauto.com"),
        ("Vision Nissan Webster",                        "Bobby Mcmullen",       "bmc@visionauto.com"),
        ("Volkswagen Brandon",                           "Paul Gomez",           "pgomez@vwbrandon.com"),
        ("Wayne Akers Ford",                             "Jim Doyle",            "jim.doyle@wayneakers.com"),
        ("NYE Automotive Group",                         "Mike Sacco",           "msacco@nyeauto.com"),
    ]
    contacts = {}
    for dealer_name, gm_name, gm_email in raw:
        contacts[_norm(dealer_name)] = {
            "raw_name":  dealer_name,
            "gm_name":   gm_name,
            "gm_first":  gm_name.split()[0],
            "gm_email":  gm_email,
        }
    return contacts


def _norm(s):
    """Normalize a string for fuzzy matching."""
    s = s.lower()
    # Strip common noise words
    for word in ["the ", " llc", " inc", " -", "  "]:
        s = s.replace(word, " ")
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return " ".join(s.split())


def is_virtual_store(dealer_name):
    """True if this is a virtual delivery/marketplace store (not a physical dealership)."""
    nd = dealer_name.lower()
    return any(pat in nd for pat in VIRTUAL_STORE_PATTERNS)


def match_contact(dealer_name, contacts):
    """Return contact dict for dealer_name using manual map → exact → fuzzy match."""
    nd = _norm(dealer_name)

    # Check manual override table — only keys explicitly present apply
    if nd in DEALER_NAME_MAP:
        mapped = DEALER_NAME_MAP[nd]
        if mapped is None:
            return None   # explicit skip (e.g. NYE sub-stores)
        nd = _norm(mapped)

    if nd in contacts:
        return contacts[nd]

    # Fuzzy: score by word overlap
    words = set(nd.split())
    best, best_score = None, 0
    for key, val in contacts.items():
        kwords = set(key.split())
        overlap = len(words & kwords)
        score = overlap / max(len(words), len(kwords))
        if score > best_score:
            best_score = score
            best = val
    if best_score >= 0.55:
        return best
    return None


# ── EMAIL COMPOSITION ─────────────────────────────────────────────────────────

def format_vehicle_line(v):
    return (
        f"<li style='margin:4px 0'>"
        f"<b>{v['ymmt']}</b> (Stock #{v['stock']}) &mdash; "
        f"drop <b>{v['diff']}</b> for <b>{v['next_badge']}</b> badge &rarr; {v['target_price']}"
        f"</li>"
    )


def build_email_html(gm_first, dealer_name, vehicles, threshold, today_str, sheet_url):
    n   = len(vehicles)
    top = vehicles[:TOP_N]
    lines = "\n".join(format_vehicle_line(v) for v in top)
    more  = f"<p style='margin:6px 0;color:#555'>+ {n - TOP_N} more &mdash; <a href='{sheet_url}'>see full report</a></p>" if n > TOP_N else ""

    return f"""<div style="font-family:Arial,sans-serif;font-size:14px;color:#222;max-width:640px">
<p>Dear {gm_first},</p>

<p>I wanted to share a current <strong><a href="{sheet_url}">Price Badge Opportunity Report</a></strong>
for <strong>{dealer_name}</strong> as of <em>{today_str}</em>.</p>

<p>You currently have <strong>{n} used vehicle{"s" if n != 1 else ""} within ${threshold:,}
of moving into a higher Price Badge category</strong>
(such as <em>Fair &rarr; Good</em> or <em>Good &rarr; Great</em>).
Small pricing adjustments on these units could lead to stronger merchandising positions
and improved shopper visibility on Cars.com.</p>

<p><strong><u>Vehicles within ${threshold:,} of the next tier:</u></strong></p>
<ul style="margin:6px 0 12px 0;padding-left:20px">
{lines}
</ul>
{more}

<p>Happy to walk through this together if it would be helpful. Just let us know.</p>

<p>Cheers,<br><br>
<strong>Jacob Crawley</strong><br>
Client Service Manager, Enterprise Accounts<br>
M: 918.694.1670</p>
</div>"""


def build_subject(dealer_name, today_str):
    return f"Cars.com Price Badge Opportunity | {dealer_name} | {today_str}"


# ── GMAIL DRAFT/SEND ──────────────────────────────────────────────────────────

def create_draft(gmail_svc, to, cc, subject, html_body, send=False):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = "jcrawley@cars.com"
    msg["To"]      = to
    if cc:
        msg["Cc"] = cc
    msg.attach(MIMEText(html_body, "html"))

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    if send:
        gmail_svc.users().messages().send(userId="me", body={"raw": raw}).execute()
        return "SENT"
    else:
        draft = gmail_svc.users().drafts().create(userId="me", body={"message": {"raw": raw}}).execute()
        return draft["id"]


# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="ACA per-store Price Badge email drafts")
    ap.add_argument("--lei",       required=True, help="Path to ACA LEI CSV from Tableau")
    ap.add_argument("--threshold", type=int, default=THRESHOLD_DEFAULT, help="Badge diff threshold (default 500)")
    ap.add_argument("--dry-run",   action="store_true", help="Print report without creating drafts")
    ap.add_argument("--send",      action="store_true", help="Send emails directly (skip draft)")
    ap.add_argument("--store",     help="Only process this one store (partial name match)")
    args = ap.parse_args()

    today_str = date.today().strftime("%B %-d, %Y")
    print(f"\n{'='*60}")
    print(f"ACA Price Badge Report — {today_str}")
    print(f"Threshold: ${args.threshold:,} | Mode: {'DRY RUN' if args.dry_run else ('SEND' if args.send else 'DRAFT')}")
    print(f"{'='*60}\n")

    # 1. Parse LEI CSV
    print(f"[1/4] Parsing LEI CSV: {args.lei}")
    rows = read_csv_auto(args.lei)
    validate_headers(args.lei, rows, _LEI_EXPECTED)
    total_vehicles = len(rows) - 1
    print(f"  ✓ {total_vehicles} vehicles loaded")

    # 2. Find vehicles within threshold, grouped by dealer
    print(f"[2/4] Finding vehicles within ${args.threshold:,} of next badge tier...")
    by_dealer = parse_lei(rows, args.threshold)
    stores_with_opps = len(by_dealer)
    total_opps = sum(len(v) for v in by_dealer.values())
    print(f"  ✓ {total_opps} opportunities across {stores_with_opps} stores")

    if not by_dealer:
        print("\nNo vehicles within threshold. Check the CSV filters (used-only?) and re-run.")
        sys.exit(0)

    # 3. Load GM contacts
    print(f"[3/4] Loading GM contacts...")
    contacts = load_gm_contacts()
    print(f"  ✓ {len(contacts)} GM contacts loaded")

    if not args.dry_run:
        # Build per-store Google Sheet (one tab per store)
        print(f"[3b] Building per-store Google Sheet...")
        # Only include physical stores with contacts for the sheet
        sheet_dealers = {d: v for d, v in by_dealer.items()
                         if not is_virtual_store(d)
                         and (not args.store or args.store.lower() in d.lower())}
        dealer_urls = create_pb_sheet(sheet_dealers, args.threshold, today_str)
        gmail_svc = get_gmail_service()
    else:
        dealer_urls = {}
        gmail_svc  = None

    # 4. Create draft / send per store
    print(f"\n[4/4] Processing {stores_with_opps} stores...\n")
    sent_count = skipped_count = matched_count = 0

    for dealer_name in sorted(by_dealer.keys()):
        if is_virtual_store(dealer_name):
            continue
        if args.store and args.store.lower() not in dealer_name.lower():
            continue

        vehicles = by_dealer[dealer_name]
        n        = len(vehicles)
        contact  = match_contact(dealer_name, contacts)

        if args.dry_run:
            status = f"GM: {contact['gm_name']} <{contact['gm_email']}>" if contact else "⚠ No GM match"
            print(f"  {dealer_name}  [{n} veh] — {status}")
            for v in vehicles[:TOP_N]:
                print(f"    • {v['ymmt']} (#{v['stock']}) → drop {v['diff']} for {v['next_badge']}")
            print()
            matched_count += bool(contact)
            skipped_count += not bool(contact)
            continue

        if not contact:
            print(f"  ⚠ SKIP {dealer_name} — no GM contact match")
            skipped_count += 1
            continue

        sheet_url = dealer_urls.get(dealer_name, ACA_PB_SHEET_URL)
        to_addr   = PRESEND_TO if PRESEND else contact["gm_email"]
        cc_addr   = "" if PRESEND else CC_ALWAYS

        html   = build_email_html(contact["gm_first"], dealer_name, vehicles,
                                   args.threshold, today_str, sheet_url)
        subj   = build_subject(dealer_name, today_str)
        result = create_draft(gmail_svc, to_addr, cc_addr, subj, html, send=args.send)
        action = "sent" if args.send else f"draft {result}"
        print(f"  ✓ {dealer_name} ({n} veh) → {contact['gm_first']} — {action}")
        sent_count += 1

    print(f"\n{'='*60}")
    if args.dry_run:
        print(f"DRY RUN complete. {matched_count} stores matched to GM, {skipped_count} skipped (no GM match).")
    else:
        print(f"Done. {sent_count} draft{'s' if sent_count!=1 else ''} created, {skipped_count} skipped (no GM match).")
        if PRESEND and not args.send:
            print(f"\n⚠  Pre-send mode: all drafts sent to {PRESEND_TO}")
            print("   Review in Gmail, then flip PRESEND=False and re-run to send to GMs.")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
