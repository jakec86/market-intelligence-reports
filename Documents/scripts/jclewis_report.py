#!/usr/bin/env python3
"""
J.C. Lewis Auto Group — Cars Commerce Research Sheet (condensed, corrected)
"""
import json
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

TODAY = "April 23, 2026"

def load_creds():
    data = json.load(open('/Users/jcrawley/.claude/tokens/sheets_token.json'))
    creds = Credentials(
        token=data.get('token') or data.get('access_token'),
        refresh_token=data['refresh_token'],
        token_uri='https://oauth2.googleapis.com/token',
        client_id=data['client_id'],
        client_secret=data['client_secret'],
        scopes=data.get('scopes', ['https://www.googleapis.com/auth/spreadsheets'])
    )
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return creds

def hex_rgb(h):
    h = h.lstrip('#')
    return {"red": int(h[0:2],16)/255, "green": int(h[2:4],16)/255, "blue": int(h[4:6],16)/255}

def header_fmt(sid, row, col_end, bg, fg="#FFFFFF", bold=True, size=11):
    return {"repeatCell": {
        "range": {"sheetId": sid, "startRowIndex": row, "endRowIndex": row+1,
                  "startColumnIndex": 0, "endColumnIndex": col_end},
        "cell": {"userEnteredFormat": {
            "backgroundColor": hex_rgb(bg),
            "textFormat": {"bold": bold, "fontSize": size,
                           "foregroundColor": hex_rgb(fg)}}},
        "fields": "userEnteredFormat(backgroundColor,textFormat)"}}

def merge(sid, r1, r2, c1, c2):
    return {"mergeCells": {"range": {"sheetId": sid,
        "startRowIndex": r1, "endRowIndex": r2,
        "startColumnIndex": c1, "endColumnIndex": c2},
        "mergeType": "MERGE_ALL"}}

def col_w(sid, col, px):
    return {"updateDimensionProperties": {
        "range": {"sheetId": sid, "dimension": "COLUMNS",
                  "startIndex": col, "endIndex": col+1},
        "properties": {"pixelSize": px}, "fields": "pixelSize"}}

def freeze(sid, rows):
    return {"updateSheetProperties": {
        "properties": {"sheetId": sid, "gridProperties": {"frozenRowCount": rows}},
        "fields": "gridProperties.frozenRowCount"}}

def cell_bg(sid, r1, r2, c1, c2, color):
    return {"repeatCell": {
        "range": {"sheetId": sid, "startRowIndex": r1, "endRowIndex": r2,
                  "startColumnIndex": c1, "endColumnIndex": c2},
        "cell": {"userEnteredFormat": {"backgroundColor": hex_rgb(color)}},
        "fields": "userEnteredFormat(backgroundColor)"}}

def create_sheet(svc):
    ss = svc.spreadsheets().create(body={
        "properties": {"title": f"J.C. Lewis — Cars Commerce Opportunity Brief ({TODAY})"}
    }).execute()
    sid_map_raw = ss['spreadsheetId']

    # Add tabs, remove Sheet1
    tabs = ["Focus Stores", "Pixel Audit", "Promo Opportunity"]
    svc.spreadsheets().batchUpdate(spreadsheetId=sid_map_raw, body={"requests": [
        {"addSheet": {"properties": {"title": t}}} for t in tabs
    ]}).execute()

    sheets = svc.spreadsheets().get(spreadsheetId=sid_map_raw).execute()['sheets']
    ids = {s['properties']['title']: s['properties']['sheetId'] for s in sheets}
    sheet1 = next(s['properties']['sheetId'] for s in sheets if s['properties']['title'] == 'Sheet1')
    svc.spreadsheets().batchUpdate(spreadsheetId=sid_map_raw, body={
        "requests": [{"deleteSheet": {"sheetId": sheet1}}]
    }).execute()

    # ── Focus Stores ─────────────────────────────────────────────────────────
    tab = "Focus Stores"
    sid = ids[tab]

    rows = [
        [f"J.C. Lewis Auto Group — Focus Store Profiles", "", "", "", ""],
        [f"None of the three stores hold an active Cars.com marketplace subscription | {TODAY}", "", "", "", ""],
        ["", "", "", "", ""],
        ["Store", "CCID", "Status", "Current Cars Commerce Products", "Marketplace"],
        ["J.C. Lewis Mazda", "6035432", "Active",
         "DI Website $350/mo, FB Data $474, Fuel PPC $200, Digital Ad Spend ~$1,164, Programmatic Display $400, Cars Premium Display $500",
         "NONE"],
        ["J.C. Lewis Lincoln of Savannah", "6039661", "Prospecting",
         "No active products", "NONE"],
        ["J.C. Lewis Ford Pooler", "6062323", "Active",
         "DI Website $1,799/mo, Conversations w/ Trade Eval (free), DealerRater AutoResponse (free)",
         "NONE"],
        ["", "", "", "", ""],
        ["OTHER ACTIVE STORES (not focus)", "", "", "", ""],
        ["J.C. Lewis Ford Savannah", "148304", "Active", "DI Website, Cars Social, DealerRater, media addons", "None"],
        ["J.C. Lewis Ford Hinesville", "5371360", "Active", "DI Website, DealerRater", "None"],
        ["J.C. Lewis Ford Statesboro", "6039660", "Active", "DI Website, AccuTrade Core, DealerRater", "None"],
    ]

    svc.spreadsheets().values().update(
        spreadsheetId=sid_map_raw, range=f"'{tab}'!A1",
        valueInputOption="RAW", body={"values": rows}
    ).execute()

    fmts = [
        merge(sid, 0, 1, 0, 5),
        header_fmt(sid, 0, 5, "#1A3A4A", size=13),
        merge(sid, 1, 2, 0, 5),
        {"repeatCell": {"range": {"sheetId": sid, "startRowIndex": 1, "endRowIndex": 2},
            "cell": {"userEnteredFormat": {"backgroundColor": hex_rgb("#E8F0F4"),
                "textFormat": {"italic": True, "fontSize": 9}}},
            "fields": "userEnteredFormat(backgroundColor,textFormat)"}},
        header_fmt(sid, 3, 5, "#2C5F7A"),
        # Mazda row highlight
        cell_bg(sid, 4, 5, 0, 5, "#FFF8E8"),
        # Lincoln row highlight
        cell_bg(sid, 5, 6, 0, 5, "#F8F0FF"),
        # Pooler row highlight
        cell_bg(sid, 6, 7, 0, 5, "#F0F8FF"),
        # NONE cells in col E (red text)
        {"repeatCell": {"range": {"sheetId": sid, "startRowIndex": 4, "endRowIndex": 7,
            "startColumnIndex": 4, "endColumnIndex": 5},
            "cell": {"userEnteredFormat": {"textFormat": {"bold": True,
                "foregroundColor": {"red": 0.8, "green": 0, "blue": 0}}}},
            "fields": "userEnteredFormat(textFormat)"}},
        # Other stores header
        merge(sid, 8, 9, 0, 5),
        header_fmt(sid, 8, 5, "#607D8B", size=10),
        # Other stores grey
        cell_bg(sid, 9, 12, 0, 5, "#F5F5F5"),
        col_w(sid, 0, 240), col_w(sid, 1, 90), col_w(sid, 2, 100),
        col_w(sid, 3, 400), col_w(sid, 4, 100),
        freeze(sid, 4),
    ]
    svc.spreadsheets().batchUpdate(spreadsheetId=sid_map_raw, body={"requests": fmts}).execute()

    # ── Pixel Audit ───────────────────────────────────────────────────────────
    tab = "Pixel Audit"
    sid = ids[tab]

    pa_rows = [
        ["jclewisford.com — Critical & High Findings Only", "", "", ""],
        [f"Live browser audit · {TODAY} · 45 total scripts from 24 domains on site", "", "", ""],
        ["", "", "", ""],
        ["Risk", "Vendor", "Scripts / IDs", "Finding"],
        ["CRITICAL", "Edmunds (CarMax-owned)",
         "3 scripts + ADSOL.EdmundsEventTracking()",
         "Live conversion tracker fires on every form/phone click — sends data to CarMax. CarMax acquired Edmunds June 2021 for $404M. J.C. Lewis pays Edmunds for ads while CarMax receives conversion data from their own website visitors."],
        ["HIGH", "Google Analytics 4",
         "6 GA4 properties simultaneously",
         "6 property IDs active: G-2GTYV7LP1E, G-SCQTRE2HTH, G-QSNH7F1THK, G-ZXC8D4FY9F, G-0BVT4KXKL3 + placeholder. Every conversion counted multiple times — no vendor's reported ROI is independently trustworthy."],
        ["HIGH", "Google Ads",
         "4 conversion IDs (AW-17907272959, AW-11520541305, AW-11516667208, AW-797634152)",
         "Each account claims 100% of conversion credit independently. Reported ROAS figures from any single vendor are inflated."],
    ]

    svc.spreadsheets().values().update(
        spreadsheetId=sid_map_raw, range=f"'{tab}'!A1",
        valueInputOption="RAW", body={"values": pa_rows}
    ).execute()

    risk_colors = {"CRITICAL": "#CC0000", "HIGH": "#E65C00"}
    pa_fmts = [
        merge(sid, 0, 1, 0, 4), header_fmt(sid, 0, 4, "#1A3A4A", size=12),
        merge(sid, 1, 2, 0, 4),
        {"repeatCell": {"range": {"sheetId": sid, "startRowIndex": 1, "endRowIndex": 2},
            "cell": {"userEnteredFormat": {"backgroundColor": hex_rgb("#FFE8E8"),
                "textFormat": {"italic": True, "fontSize": 9}}},
            "fields": "userEnteredFormat(backgroundColor,textFormat)"}},
        header_fmt(sid, 3, 4, "#2C5F7A"),
        # Edmunds row background
        cell_bg(sid, 4, 5, 0, 4, "#FFF0F0"),
        col_w(sid, 0, 90), col_w(sid, 1, 180), col_w(sid, 2, 260), col_w(sid, 3, 460),
        freeze(sid, 4),
    ]
    for i, row in enumerate(pa_rows[4:]):
        risk = row[0]
        color = risk_colors.get(risk, "#888888")
        pa_fmts.append({"repeatCell": {
            "range": {"sheetId": sid, "startRowIndex": 4+i, "endRowIndex": 5+i,
                      "startColumnIndex": 0, "endColumnIndex": 1},
            "cell": {"userEnteredFormat": {"backgroundColor": hex_rgb(color),
                "textFormat": {"bold": True, "foregroundColor": {"red":1,"green":1,"blue":1}}}},
            "fields": "userEnteredFormat(backgroundColor,textFormat)"}})
    svc.spreadsheets().batchUpdate(spreadsheetId=sid_map_raw, body={"requests": pa_fmts}).execute()

    # ── Promo Opportunity ─────────────────────────────────────────────────────
    tab = "Promo Opportunity"
    sid = ids[tab]

    po_rows = [
        ["Promo Variation — Marketplace Pitch", "", "", ""],
        ["Three stores, three different entry angles — all viable for a promotional marketplace offer", "", "", ""],
        ["", "", "", ""],
        ["Store", "CCID", "Promo Angle", "Talking Point"],
        ["J.C. Lewis Mazda", "6035432",
         "Media buyer missing marketplace reach",
         "Already spending on Cars Commerce media. Marketplace puts listings in front of the shoppers that media is trying to reach. Without it, they're paying to drive traffic to a destination that isn't on Cars.com."],
        ["J.C. Lewis Lincoln of Savannah", "6039661",
         "Clean open — high-intent brand, limited competition",
         "Lincoln buyers are a small, intentional audience. Cars.com is where they search. Competing Lincoln stores in the DMA are active on marketplace today — this store isn't visible."],
        ["J.C. Lewis Ford Pooler", "6062323",
         "Existing website relationship — natural extension",
         "Already trusts Cars Commerce with their website ($1,799/mo). Inventory is invisible on Cars.com marketplace. A promo gets them in at low risk with an existing partner."],
        ["", "", "", ""],
        ["NOTES", "", "", ""],
        ["", "", "Edmunds pixel is live on jclewisford.com — CarMax receives their conversion data. This supports the competitive risk argument for consolidating to Cars Commerce.",
         ""],
        ["", "", "All three stores have DealerRater and DI website history — relationship exists, this is an expansion conversation not a cold open.",
         ""],
    ]

    svc.spreadsheets().values().update(
        spreadsheetId=sid_map_raw, range=f"'{tab}'!A1",
        valueInputOption="RAW", body={"values": po_rows}
    ).execute()

    store_colors = {"J.C. Lewis Mazda": "#FFF8E8",
                    "J.C. Lewis Lincoln of Savannah": "#F8F0FF",
                    "J.C. Lewis Ford Pooler": "#F0F8FF"}

    po_fmts = [
        merge(sid, 0, 1, 0, 4), header_fmt(sid, 0, 4, "#1A3A4A", size=12),
        merge(sid, 1, 2, 0, 4),
        {"repeatCell": {"range": {"sheetId": sid, "startRowIndex": 1, "endRowIndex": 2},
            "cell": {"userEnteredFormat": {"backgroundColor": hex_rgb("#E8F0F4"),
                "textFormat": {"italic": True, "fontSize": 9}}},
            "fields": "userEnteredFormat(backgroundColor,textFormat)"}},
        header_fmt(sid, 3, 4, "#2C5F7A"),
        cell_bg(sid, 4, 5, 0, 4, "#FFF8E8"),
        cell_bg(sid, 5, 6, 0, 4, "#F8F0FF"),
        cell_bg(sid, 6, 7, 0, 4, "#F0F8FF"),
        merge(sid, 8, 9, 0, 4), header_fmt(sid, 8, 4, "#607D8B", size=10),
        cell_bg(sid, 9, 11, 0, 4, "#F9F9F9"),
        col_w(sid, 0, 220), col_w(sid, 1, 90), col_w(sid, 2, 260), col_w(sid, 3, 420),
        freeze(sid, 4),
    ]
    svc.spreadsheets().batchUpdate(spreadsheetId=sid_map_raw, body={"requests": po_fmts}).execute()

    return sid_map_raw

def main():
    creds = load_creds()
    svc = build('sheets', 'v4', credentials=creds)
    ss_id = create_sheet(svc)
    print(f"SHEET: https://docs.google.com/spreadsheets/d/{ss_id}")
    return ss_id

if __name__ == "__main__":
    main()
