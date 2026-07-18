#!/usr/bin/env python3
"""
ACA Sales Attribution Scraper
Collects per-store units influenced, connections, and % new vehicles
from admin.cars.com individual store Sales Attribution pages via Playwright.

The page uses Tableau Embedding API v3. The Tableau JS API is used directly
to set date parameters and read worksheet summary data — no file download needed.

Prerequisites:
    - On first run a headed browser opens; log into admin.cars.com via JumpCloud SSO.
    - Session state is saved to ~/.claude/admin_cars_session.json for reuse.
    - To use an existing Chrome instance: pass --cdp-port 9222 (Chrome must be running
      with --remote-debugging-port=9222).

Usage:
    python3 aca_sales_attr_scraper.py --month "April 2026"
    python3 aca_sales_attr_scraper.py --month "April 2026" --market-opp ~/path/to/file.csv
    python3 aca_sales_attr_scraper.py --month "April 2026" --ccid 6067469   # one store
    python3 aca_sales_attr_scraper.py --month "April 2026" --cdp-port 9222  # existing Chrome

Output:
    ~/Documents/Tableau/aca_sales_attr_YYYY_MM.csv
"""

import argparse, calendar, codecs, csv, io, json, os, sys, time
from datetime import datetime
from typing import Optional, Dict, List, Tuple

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

ADMIN_BASE   = "https://admin.cars.com"
SESSION_FILE = os.path.expanduser("~/.claude/admin_cars_session.json")
UUID_CACHE   = os.path.expanduser("~/.claude/aca_uuid_cache.json")
OUT_DIR      = os.path.expanduser("~/Documents/Tableau")


def month_date_range(month_label: str) -> Tuple[str, str]:
    """'April 2026' -> ('2026-04-01', '2026-04-30')"""
    dt = datetime.strptime(month_label, "%B %Y")
    last = calendar.monthrange(dt.year, dt.month)[1]
    return (f"{dt.year:04d}-{dt.month:02d}-01",
            f"{dt.year:04d}-{dt.month:02d}-{last:02d}")


def read_csv_auto(path: str) -> List[Dict]:
    raw = open(path, "rb").read(4)
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        import codecs as _c
        text = _c.open(path, encoding="utf-16").read()
    else:
        text = open(path, encoding="utf-8-sig").read()
    first = text.split("\n", 1)[0]
    delim = "\t" if "\t" in first else ","
    return list(csv.DictReader(io.StringIO(text), delimiter=delim))


def load_uuid_cache() -> Dict:
    if os.path.exists(UUID_CACHE):
        with open(UUID_CACHE) as f:
            return json.load(f)
    return {}


def save_uuid_cache(cache: Dict) -> None:
    os.makedirs(os.path.dirname(UUID_CACHE), exist_ok=True)
    with open(UUID_CACHE, "w") as f:
        json.dump(cache, f, indent=2)


def launch_browser(playwright, cdp_port: Optional[int] = None, headless: bool = False):
    """Connect to existing Chrome via CDP, or launch a new browser."""
    if cdp_port:
        try:
            browser = playwright.chromium.connect_over_cdp(f"http://localhost:{cdp_port}")
            ctx = browser.contexts[0] if browser.contexts else browser.new_context()
            print(f"  Connected to Chrome via CDP on port {cdp_port}")
            return browser, ctx
        except Exception as e:
            print(f"  CDP connection failed: {e} — falling back to fresh browser")

    browser = playwright.chromium.launch(headless=headless)
    if os.path.exists(SESSION_FILE):
        ctx = browser.new_context(storage_state=SESSION_FILE)
        print(f"  Loaded saved session from {SESSION_FILE}")
    else:
        ctx = browser.new_context()
        print("  No saved session — you may need to log in")
    return browser, ctx


def ensure_logged_in(page, timeout_seconds: int = 120) -> bool:
    page.goto(ADMIN_BASE, wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(2000)
    url = page.url
    if "admin.cars.com" in url and "jumpcloud" not in url.lower() and "login" not in url.lower():
        print("  admin.cars.com session is active")
        return True

    print(f"\n  Not logged in. Authenticate via JumpCloud SSO in the browser window.")
    print(f"  Waiting up to {timeout_seconds} seconds...")
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        page.wait_for_timeout(3000)
        url = page.url
        if "admin.cars.com" in url and "jumpcloud" not in url.lower() and "login" not in url.lower():
            print("  Login detected")
            try:
                page.context.storage_state(path=SESSION_FILE)
                print(f"  Session saved to {SESSION_FILE}")
            except Exception:
                pass
            return True

    print("  Login timeout")
    return False


def lookup_uuid(page, ccid: str, cache: Dict) -> Optional[str]:
    if ccid in cache:
        return cache[ccid]
    url = f"{ADMIN_BASE}/dealers/all/reports?query={ccid}"
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=15000)
        page.wait_for_timeout(1500)
        uuid = page.evaluate("""() => {
            const links = Array.from(document.querySelectorAll('a[href]'))
                .filter(l => /[a-f0-9]{8}-[a-f0-9]{4}/.test(l.href));
            if (!links.length) return null;
            const m = links[0].href.match(/[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}/);
            return m ? m[0] : null;
        }""")
        if uuid:
            cache[ccid] = uuid
            save_uuid_cache(cache)
        return uuid
    except Exception as e:
        print(f"    UUID lookup failed for CCID {ccid}: {e}")
        return None


# JavaScript injected into each store's SA page
EXTRACT_JS = """
async ({fromDate, toDate}) => {
    const viz = document.querySelector('tableau-viz');
    if (!viz) return {error: 'no tableau-viz element'};

    // Poll until _workbookImpl is populated (internal init signal for Tableau Embedding API v3)
    let wb = null;
    for (let i = 0; i < 60; i++) {
        try {
            const w = viz.workbook;
            if (w && w._workbookImpl) { wb = w; break; }
        } catch(e) {}
        await new Promise(r => setTimeout(r, 500));
    }
    if (!wb) return {error: 'workbook not ready after 30s'};

    // Set date range; use LeadDate=999 to include all influenced vehicles
    try {
        await wb.changeParameterValueAsync('FromDate', new Date(fromDate));
        await wb.changeParameterValueAsync('ToDate',   new Date(toDate));
        await wb.changeParameterValueAsync('LeadDate', 999);
    } catch(e) {
        return {error: 'param change failed: ' + e.message};
    }

    await new Promise(r => setTimeout(r, 4000));

    const dashboard = wb.activeSheet;
    const result = {};

    for (const ws of dashboard.worksheets) {
        if (!['InfluencedSales', 'TotalConnections', 'VehicleDetails'].includes(ws.name)) continue;
        try {
            const maxRows = ws.name === 'VehicleDetails' ? 500 : 10;
            const data = await ws.getSummaryDataAsync({maxRows, includeAllColumns: true});
            const cols = data.columns.map(c => c.fieldName);
            const rows = data.data.map(r => {
                const row = {};
                r.forEach((cell, j) => { row[cols[j]] = cell.formattedValue != null ? cell.formattedValue : cell.value; });
                return row;
            });
            result[ws.name] = {cols, rows};
        } catch(e) {
            result[ws.name] = {error: e.message};
        }
    }
    return result;
}
"""


def extract_store_data(page, uuid: str, from_date: str, to_date: str,
                       store_name: str) -> Optional[Dict]:
    url = f"{ADMIN_BASE}/dealers/{uuid}/reports/sales_attribution"
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=20000)
    except PlaywrightTimeout:
        print(f"    Page load timeout for {store_name}")
        return None

    try:
        page.wait_for_selector("tableau-viz", timeout=30000)
    except PlaywrightTimeout:
        print(f"    Tableau viz not found for {store_name}")
        return None

    page.wait_for_timeout(2000)
    page.set_default_timeout(90000)

    try:
        raw = page.evaluate(EXTRACT_JS, {"fromDate": from_date, "toDate": to_date})
    except Exception as e:
        print(f"    JS eval error for {store_name}: {e}")
        return None

    if not raw or (isinstance(raw, dict) and "error" in raw):
        err = raw.get("error", raw) if isinstance(raw, dict) else raw
        print(f"    Data extract error for {store_name}: {err}")
        return None

    # Parse InfluencedSales
    influenced = "N/A"
    if "InfluencedSales" in raw and isinstance(raw["InfluencedSales"], dict):
        rows = raw["InfluencedSales"].get("rows", [])
        if rows:
            val = next(iter(rows[0].values()), "")
            try:
                influenced = str(int(float(str(val).replace(",", "").strip())))
            except Exception:
                influenced = str(val).strip() or "N/A"

    # Parse TotalConnections
    connections = "N/A"
    if "TotalConnections" in raw and isinstance(raw["TotalConnections"], dict):
        rows = raw["TotalConnections"].get("rows", [])
        if rows:
            val = next(iter(rows[0].values()), "")
            try:
                connections = str(int(float(str(val).replace(",", "").strip())))
            except Exception:
                connections = str(val).strip() or "N/A"

    # Compute % New from VehicleDetails (influenced vehicles with LeadDate=999)
    new_pct = "N/A"
    if "VehicleDetails" in raw and isinstance(raw["VehicleDetails"], dict):
        rows = raw["VehicleDetails"].get("rows", [])
        if rows:
            total = len(rows)
            new_count = sum(
                1 for r in rows
                if str(r.get("Stock type", "")).lower() in ("new", "cpo")
            )
            if total > 0:
                new_pct = f"{new_count / total * 100:.1f}"

    return {
        "units_influenced":  influenced,
        "total_connections": connections,
        "new_pct":           new_pct,
    }


def main():
    parser = argparse.ArgumentParser(description="Scrape ACA Sales Attribution per store")
    parser.add_argument("--month",      required=True, help='Month label, e.g. "April 2026"')
    parser.add_argument("--market-opp", default=None,  help="Path to Market Opportunities CSV")
    parser.add_argument("--ccid",       default=None,  help="Scrape only this CCID (for testing)")
    parser.add_argument("--cdp-port",   type=int, default=None, help="Connect to existing Chrome on this CDP port")
    parser.add_argument("--headless",   action="store_true", help="Run browser headlessly")
    parser.add_argument("--delay",      type=float, default=1.5, help="Seconds between store requests")
    args = parser.parse_args()

    month_label = args.month
    from_date, to_date = month_date_range(month_label)
    yyyy_mm = datetime.strptime(month_label, "%B %Y").strftime("%Y_%m")

    print(f"\n{'='*60}")
    print(f"ACA Sales Attribution Scraper -- {month_label}")
    print(f"Date range: {from_date} to {to_date}")
    print(f"{'='*60}\n")

    # Locate Market Opp CSV
    tableau_dir = os.path.expanduser("~/Documents/Tableau")
    mop_path = args.market_opp
    if not mop_path:
        for fname in sorted(os.listdir(tableau_dir), reverse=True):
            if "aca" in fname.lower() and "market" in fname.lower():
                mop_path = os.path.join(tableau_dir, fname)
                break
    if not mop_path or not os.path.exists(mop_path):
        print("Missing Market Opportunities CSV. Pass --market-opp or place aca_market_opp_YYYY_MM.csv in ~/Documents/Tableau/")
        sys.exit(1)
    print(f"Source CSV:  {mop_path}")

    rows = read_csv_auto(mop_path)
    headers = list(rows[0].keys()) if rows else []
    col_ccid = next((h for h in headers if "legacy" in h.lower() or "ccid" in h.lower()), None)
    col_name = next((h for h in headers if "customer name" in h.lower() or "store name" in h.lower()), None)

    stores = []
    for r in rows:
        ccid = str((r.get(col_ccid) or "")).strip().split(".")[0]
        name = (r.get(col_name) or "").strip()
        if ccid and name:
            stores.append({"ccid": ccid, "name": name})

    if args.ccid:
        stores = [s for s in stores if s["ccid"] == str(args.ccid)]
        if not stores:
            print(f"CCID {args.ccid} not found in CSV")
            sys.exit(1)

    print(f"Stores to scrape: {len(stores)}\n")

    uuid_cache = load_uuid_cache()
    results = []

    with sync_playwright() as p:
        browser, ctx = launch_browser(p, cdp_port=args.cdp_port, headless=args.headless)
        page = ctx.new_page()

        if not ensure_logged_in(page):
            sys.exit(1)

        print(f"\n[Scraping {len(stores)} stores]\n")
        for i, store in enumerate(stores, 1):
            ccid = store["ccid"]
            name = store["name"]
            print(f"  [{i:2d}/{len(stores)}] {name} ({ccid})")
            sys.stdout.flush()

            uuid = lookup_uuid(page, ccid, uuid_cache)
            if not uuid:
                print(f"    UUID not found -- skipping")
                results.append({"ccid": ccid, "store_name": name,
                                 "units_influenced": "N/A", "total_connections": "N/A", "new_pct": "N/A"})
                continue

            data = extract_store_data(page, uuid, from_date, to_date, name)
            if data:
                print(f"    influenced={data['units_influenced']}, "
                      f"connections={data['total_connections']}, "
                      f"new={data['new_pct']}%")
                results.append({"ccid": ccid, "store_name": name, **data})
            else:
                results.append({"ccid": ccid, "store_name": name,
                                 "units_influenced": "N/A", "total_connections": "N/A", "new_pct": "N/A"})

            sys.stdout.flush()
            if args.delay > 0:
                time.sleep(args.delay)

        if not args.cdp_port:
            try:
                ctx.storage_state(path=SESSION_FILE)
            except Exception:
                pass

        browser.close()

    # Write output CSV — merge into existing file when a single store was targeted
    os.makedirs(OUT_DIR, exist_ok=True)
    out_path = os.path.join(OUT_DIR, f"aca_sales_attr_{yyyy_mm}.csv")
    fieldnames = ["ccid", "store_name", "units_influenced", "total_connections", "new_pct"]
    if args.ccid and os.path.exists(out_path):
        existing = read_csv_auto(out_path)
        merged = {r["ccid"]: r for r in existing}
        for r in results:
            merged[r["ccid"]] = r
        results = list(merged.values())
        print(f"  Merged into existing CSV ({len(existing)} existing rows)")
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    ok    = sum(1 for r in results if r["units_influenced"] != "N/A")
    skips = len(results) - ok
    print(f"\n{'='*60}")
    print(f"Done -- {ok} stores scraped, {skips} skipped")
    print(f"Output: {out_path}")
    print(f"{'='*60}\n")

    if skips:
        print("Skipped stores:")
        for r in results:
            if r["units_influenced"] == "N/A":
                print(f"  * {r['store_name']} ({r['ccid']})")


if __name__ == "__main__":
    main()
