#!/usr/bin/env python3
"""
pb_lo_report.py — Price Badge report from admin.cars Listings Optimizer.

Source: the Listings Optimizer "Live Inventory" crosstab (admin.cars, per dealer,
NOT RLS-limited — works for any store). It already carries, per vehicle, the
current Price badge, the $ "Reduce by" to the next badge, and the Good/Great
badge target prices — so no Google-Sheet formula machinery is needed; we compute
everything here and write a clean values table.

Used as the source for the Herb Chambers GM touchpoint (stores missing from the
Tableau LEI view due to row-level security). Reuses pb_report's auth + Gmail
draft helpers and pb_dealers.py config (sheet_id, threshold, recipients, etc.).

Usage:
    python3 pb_lo_report.py --dealer hc_seekonk_honda --lo ~/.playwright-mcp/hc_seekonk_honda_lo.csv --dry-run
    python3 pb_lo_report.py --dealer hc_seekonk_honda --lo lo.csv            # populate sheet + draft to Jake
    python3 pb_lo_report.py --dealer hc_seekonk_honda --lo lo.csv --send     # ...and send
"""
import argparse, csv, io, os, sys, html
from datetime import date
from pathlib import Path
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pb_dealers import DEALERS
from pb_report import get_sheets_client, get_gmail_service, create_gmail_draft, send_gmail_draft

# Live Inventory crosstab columns we rely on (validate before parsing).
LO_REQUIRED = ["Stock num", "VIN", "Stock type", "YMMT", "Price badge",
               "Price vs Market (%)", "Days live", "Photos", "Price",
               "Reduce by", "Good badge target", "Great badge target"]

BADGE_ORDER = {"Not Badged": 0, "Fair": 1, "Good": 2, "Great": 3}


def num(x):
    try:
        return float(str(x).replace(",", "").replace("$", "").replace("%", "").strip() or 0)
    except Exception:
        return 0.0


def load_lo(path):
    """Parse the Live Inventory crosstab (UTF-16/tab), return used-only rows + validate schema."""
    raw = Path(path).read_bytes()
    text = raw.decode("utf-16", "replace") if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else raw.decode("utf-8", "replace")
    first = text.split("\n", 1)[0]
    delim = "\t" if first.count("\t") >= first.count(",") else ","
    rdr = csv.DictReader(io.StringIO(text), delimiter=delim)
    headers = [h.strip() for h in (rdr.fieldnames or [])]
    missing = [c for c in LO_REQUIRED if c not in headers]
    if missing:
        sys.exit(f"❌ LO CSV schema drift — missing columns: {missing}\n   Got: {headers}")
    rows = [{k.strip(): (v or "").strip() for k, v in r.items() if k} for r in rdr]
    used = [r for r in rows if r.get("Stock type", "").lower() == "used"]
    return rows, used


def next_badge(cur):
    """Next achievable badge above the current one (Reduce by targets that tier)."""
    cur = (cur or "").strip()
    if cur in ("Not Badged", "Fair"):
        return "Good"
    if cur == "Good":
        return "Great"
    return None  # already Great


def target_for(row, nxt):
    return num(row.get("Great badge target")) if nxt == "Great" else num(row.get("Good badge target"))


def compute(used, threshold):
    great = [r for r in used if r.get("Price badge") == "Great"]
    # eligible = not already Great, has a positive reduce-by to the next tier
    elig = []
    for r in used:
        nb = next_badge(r.get("Price badge"))
        rb = num(r.get("Reduce by"))
        if nb and rb > 0:
            elig.append({**r, "_next": nb, "_reduce": rb, "_target": target_for(r, nb)})
    within = [r for r in elig if r["_reduce"] <= threshold]
    within.sort(key=lambda r: r["_reduce"])
    used_n = len(used)
    pct = round(100 * len(within) / used_n) if used_n else 0
    # pricing context from Price vs Market (%): <100% = priced under market
    under = sum(1 for r in used if 0 < num(r.get("Price vs Market (%)")) < 100)
    return {
        "used_total": used_n,
        "within_count": len(within),
        "pct": pct,
        "threshold": threshold,
        "great_count": len(great),
        "top": within[:5],
        "under_market_pct": round(100 * under / used_n) if used_n else 0,
        "all_eligible_sorted": sorted(elig, key=lambda r: r["_reduce"]),
    }


def fmt_money(v):
    return f"${v:,.0f}"


def compose_email(cfg, st):
    disp = cfg["display_name"]
    lines = []
    for r in st["top"]:
        lines.append(
            f'<li><b>{html.escape(r["YMMT"])}</b> ({html.escape(r["Stock num"])}) — currently '
            f'<b>{html.escape(r.get("Price badge") or "Not Badged")}</b>; drop {fmt_money(r["_reduce"])} '
            f'to <b>{r["_next"]}</b> (target {fmt_money(r["_target"])})</li>'
        )
    top_html = "\n".join(lines)
    link = cfg.get("email_link_url", cfg["sheet_url"])
    dem = ""
    if st["under_market_pct"]:
        dem = (f'<p>Pricing-wise, <b>{st["under_market_pct"]}%</b> of your used lot is already '
               f'priced under market — the badge gains above are small moves on top of that.</p>')
    return f"""\
<html><body>
<p>Hi team,</p>
<p>A few quick wins sitting in your current used inventory. Right now
<b>{st["within_count"]} vehicles ({st["pct"]}% of your used lot)</b> are within
{fmt_money(st["threshold"])} of earning a better price badge on Cars.com — small
repricing moves that lift search ranking and engagement.</p>
<ul>
{top_html}
</ul>
{dem}
<p>The full breakdown, sorted by closest to an upgrade, is in your
<a href="{link}">Price Badge Report</a>. {st["great_count"]} vehicles are already at Great.</p>
<p>Cheers,</p>
<p>Jake</p>
</body></html>"""


# Column order: the within-range "$ to Next Badge" is J (green CF) and "Price vs Market %" is K (orange CF).
SHEET_HEADERS = ["Stock #", "Year/Make/Model/Trim", "Stock Type", "Days Live", "Photos",
                 "Price", "Current Badge", "Next Badge", "Target Price", "$ to Next Badge",
                 "Price vs Market %"]
PURPLE = {"red": 0x6B/255, "green": 0x2D/255, "blue": 0x8B/255}
WHITE  = {"red": 1, "green": 1, "blue": 1}
GREEN  = {"red": 0.72, "green": 0.88, "blue": 0.80}   # within range
ORANGE = {"red": 0.98, "green": 0.78, "blue": 0.52}   # above market (>100% PTM)


def populate_sheet(cfg, used, st):
    """Reset the cloned template's leftover formatting and write a clean, formatted PB table.
    $ to Next Badge = col J (green CF when within range); Price vs Market % = col K (orange CF when >100%)."""
    gc = get_sheets_client()
    sh = gc.open_by_key(cfg["sheet_id"])
    ws = sh.worksheet(cfg["pbt_tab"])
    sid = ws.id

    # --- reset leftover Nalley-template formatting (stray green fills, merges, CF rules, extra cols) ---
    meta = sh.fetch_sheet_metadata(params={
        "fields": "sheets(properties(sheetId,gridProperties),conditionalFormats,merges)"})
    tgt = next(s for s in meta["sheets"] if s["properties"]["sheetId"] == sid)
    cf_n = len(tgt.get("conditionalFormats", []))
    merges = tgt.get("merges", [])
    col_count = tgt["properties"]["gridProperties"].get("columnCount", 26)

    ws.clear()
    reset = [{"unmergeCells": {"range": m}} for m in merges]
    reset += [{"deleteConditionalFormatRule": {"sheetId": sid, "index": i}} for i in range(cf_n - 1, -1, -1)]
    reset.append({"repeatCell": {
        "range": {"sheetId": sid, "startRowIndex": 0, "endRowIndex": 2000,
                  "startColumnIndex": 0, "endColumnIndex": max(col_count, 11)},
        "cell": {"userEnteredFormat": {"backgroundColor": WHITE, "textFormat": {"bold": False}}},
        "fields": "userEnteredFormat(backgroundColor,textFormat)"}})
    if col_count > 11:  # drop stray column L and beyond
        reset.append({"deleteDimension": {"range": {"sheetId": sid, "dimension": "COLUMNS",
                                                     "startIndex": 11, "endIndex": col_count}}})
    sh.batch_update({"requests": reset})

    # --- values: R1 title + E1 threshold + J1 % ; R3 headers ; R4+ data ---
    today = date.today().strftime("%-m.%-d.%y")
    pct_frac = round(st["within_count"] / st["used_total"], 4) if st["used_total"] else 0
    row1 = [""] * 11
    row1[0] = f'{cfg["display_name"]} — Price Badge Report — {today}'
    row1[3], row1[4] = "Badge range", st["threshold"]      # D1 label, E1 threshold
    row1[8], row1[9] = "% within range", pct_frac          # I1 label, J1 %
    body = []
    for r in st["all_eligible_sorted"]:
        body.append([r["Stock num"], r["YMMT"], r["Stock type"], num(r.get("Days live")),
                     num(r.get("Photos")), num(r.get("Price")), r.get("Price badge") or "Not Badged",
                     r["_next"], r["_target"], r["_reduce"], num(r.get("Price vs Market (%)")) / 100.0])
    ws.update(range_name="A1", values=[row1], value_input_option="USER_ENTERED")
    ws.update(range_name="A3", values=[SHEET_HEADERS] + body, value_input_option="USER_ENTERED")
    last = 3 + len(body)

    # --- formatting ---
    def cell(sr, er, sc, ec, ufmt, fields):
        return {"repeatCell": {"range": {"sheetId": sid, "startRowIndex": sr, "endRowIndex": er,
                "startColumnIndex": sc, "endColumnIndex": ec}, "cell": {"userEnteredFormat": ufmt}, "fields": fields}}
    CUR = {"type": "CURRENCY", "pattern": "$#,##0"}
    fmt = [
        cell(0, 1, 0, 1, {"textFormat": {"bold": True, "fontSize": 12, "foregroundColor": PURPLE}}, "userEnteredFormat.textFormat"),
        cell(0, 1, 3, 4, {"textFormat": {"bold": True}, "horizontalAlignment": "RIGHT"}, "userEnteredFormat(textFormat,horizontalAlignment)"),
        cell(0, 1, 8, 9, {"textFormat": {"bold": True}, "horizontalAlignment": "RIGHT"}, "userEnteredFormat(textFormat,horizontalAlignment)"),
        cell(0, 1, 4, 5, {"numberFormat": CUR, "textFormat": {"bold": True}}, "userEnteredFormat(numberFormat,textFormat)"),
        cell(0, 1, 9, 10, {"numberFormat": {"type": "PERCENT", "pattern": "0%"}, "textFormat": {"bold": True}}, "userEnteredFormat(numberFormat,textFormat)"),
        cell(2, 3, 0, 11, {"backgroundColor": PURPLE, "textFormat": {"bold": True, "foregroundColor": WHITE},
                           "horizontalAlignment": "CENTER", "verticalAlignment": "MIDDLE", "wrapStrategy": "WRAP"},
             "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,verticalAlignment,wrapStrategy)"),
        {"updateSheetProperties": {"properties": {"sheetId": sid, "gridProperties": {"frozenRowCount": 3}},
                                   "fields": "gridProperties.frozenRowCount"}},
    ]
    if body:
        for ci in (5, 8, 9):  # Price, Target Price, $ to Next Badge → currency
            fmt.append(cell(3, last, ci, ci + 1, {"numberFormat": CUR}, "userEnteredFormat.numberFormat"))
        fmt.append(cell(3, last, 10, 11, {"numberFormat": {"type": "PERCENT", "pattern": "0.0%"}}, "userEnteredFormat.numberFormat"))
        fmt.append({"addConditionalFormatRule": {"index": 0, "rule": {  # green: within range (0 < J ≤ E1)
            "ranges": [{"sheetId": sid, "startRowIndex": 3, "endRowIndex": last, "startColumnIndex": 9, "endColumnIndex": 10}],
            "booleanRule": {"condition": {"type": "CUSTOM_FORMULA", "values": [{"userEnteredValue": "=AND($J4>0,$J4<=$E$1)"}]},
                            "format": {"backgroundColor": GREEN}}}}})
        fmt.append({"addConditionalFormatRule": {"index": 0, "rule": {  # orange: above market (K > 100%)
            "ranges": [{"sheetId": sid, "startRowIndex": 3, "endRowIndex": last, "startColumnIndex": 10, "endColumnIndex": 11}],
            "booleanRule": {"condition": {"type": "CUSTOM_FORMULA", "values": [{"userEnteredValue": "=$K4>1"}]},
                            "format": {"backgroundColor": ORANGE}}}}})
    sh.batch_update({"requests": fmt})
    return sh.url


def run(dealer, lo_path, send=False, dry=False, no_draft=False):
    if dealer not in DEALERS:
        sys.exit(f"❌ unknown dealer key: {dealer}")
    cfg = dict(DEALERS[dealer])
    all_rows, used = load_lo(lo_path)
    if not used:
        sys.exit(f"⚠️  {dealer}: 0 USED vehicles in LO export — store may have lapsed; skipping.")
    st = compute(used, cfg["threshold"])
    today = date.today().strftime("%a %-m.%-d.%y")
    cfg["email_subject"] = f"{cfg['display_name']} — Price Badge Report {today}"

    print(f"[{dealer}] used={st['used_total']}  within ${cfg['threshold']:,}={st['within_count']} ({st['pct']}%)  "
          f"already Great={st['great_count']}  under-market={st['under_market_pct']}%")
    for r in st["top"]:
        print(f"   {r['YMMT']} ({r['Stock num']}) {r.get('Price badge')} → -${r['_reduce']:,.0f} {r['_next']}")

    html_body = compose_email(cfg, st)

    if dry:
        out = Path.home() / "Documents" / "Reports" / f"pb_dryrun_{dealer}_{date.today().isoformat()}.html"
        out.write_text(html_body)
        print(f"   [dry-run] email HTML → {out}  (no sheet write, no draft)")
        return st

    url = populate_sheet(cfg, used, st)
    print(f"   ✓ sheet populated: {url}")
    if no_draft:
        print("   [--no-draft] sheet reformatted only; existing draft untouched")
        return st
    gmail = get_gmail_service()
    draft_id, _ = create_gmail_draft(gmail, cfg, html_body)
    print(f"   ✓ draft created: {draft_id}  (To: {cfg['email_to']})")
    if send:
        send_gmail_draft(gmail, draft_id)
    return st


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dealer", required=True)
    ap.add_argument("--lo", required=True, help="Listings Optimizer 'Live Inventory' crosstab CSV")
    ap.add_argument("--send", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-draft", action="store_true", help="populate/reformat sheet only, skip Gmail draft")
    a = ap.parse_args()
    run(a.dealer, a.lo, send=a.send, dry=a.dry_run, no_draft=a.no_draft)


if __name__ == "__main__":
    main()
