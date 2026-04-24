"""
admin.cars.com data fetcher using Playwright + tableau-viz Web Component JS API.
Connects to the user's Chrome via CDP (the JumpCloud device policy blocks
standalone Chromium instances that aren't JumpCloud-managed).

**Setup:** The user must launch Chrome with remote debugging enabled before
running the app:

    /Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome \\
        --remote-debugging-port=9222 --user-data-dir=$HOME/Library/Application\\ Support/Google/Chrome

Then log in to admin.cars.com in that Chrome window. The app will connect
over CDP and reuse the existing authenticated session.

No Streamlit imports. All public functions return dicts or None.
"""
import re
from contextlib import contextmanager
from typing import Optional
from urllib.parse import urlencode

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

ADMIN_URL = "https://admin.cars.com"
CDP_ENDPOINT = "http://localhost:9222"
UUID_PATTERN = re.compile(r"dealers/([a-f0-9\-]{36})/reports")
TIMEOUT = 20_000  # ms


@contextmanager
def _get_context():
    """Connect to the user's running Chrome via CDP and yield its default context."""
    with sync_playwright() as pw:
        browser = pw.chromium.connect_over_cdp(CDP_ENDPOINT)
        try:
            ctx = browser.contexts[0] if browser.contexts else browser.new_context()
            yield ctx
        finally:
            # Detaches from the user's Chrome; does not close their browser.
            browser.close()


def check_session() -> bool:
    """Return True if admin.cars.com is reachable without SSO redirect."""
    try:
        with _get_context() as ctx:
            page = ctx.new_page()
            page.goto(f"{ADMIN_URL}/dealers/all/reports", timeout=TIMEOUT, wait_until="domcontentloaded")
            return "admin.cars.com" in page.url
    except Exception:
        return False


def _extract_uuid_from_html(html: str) -> Optional[str]:
    """Extract the first dealer UUID from admin.cars.com search result HTML."""
    match = UUID_PATTERN.search(html)
    return match.group(1) if match else None


def resolve_uuid(ccid: str) -> Optional[str]:
    """Resolve a CCID to an admin.cars.com dealer UUID via search."""
    try:
        with _get_context() as ctx:
            page = ctx.new_page()
            page.goto(
                f"{ADMIN_URL}/dealers/all/reports?{urlencode({'query': ccid})}",
                timeout=TIMEOUT,
                wait_until="domcontentloaded",
            )
            if "admin.cars.com" not in page.url:
                return None
            return _extract_uuid_from_html(page.content())
    except Exception:
        return None


def _parse_kpi(raw: Optional[str]) -> Optional[float]:
    """Strip $, commas, % from a KPI string and return float, or None if unparseable."""
    if not raw or raw.strip() in ("N/A", "--", ""):
        return None
    cleaned = re.sub(r"[$,%]", "", raw.strip())
    try:
        return float(cleaned)
    except ValueError:
        return None


_PERF_JS = """
async (targetWorksheets) => {
    const viz = document.querySelector('tableau-viz');
    if (!viz || !viz.workbook) return null;
    const sheet = viz.workbook.activeSheet;
    const results = {};
    for (const name of targetWorksheets) {
        const ws = sheet.worksheets.find(w => w.name === name);
        if (!ws) { results[name] = null; continue; }
        try {
            // getSummaryDataAsync works for viewers;
            // getUnderlyingTableDataAsync requires Access Underlying Data permission (denied).
            const data = await ws.getSummaryDataAsync({ maxRows: 5 });
            results[name] = {
                cols: data.columns.map(c => c.fieldName),
                rows: data.data.map(row => row.map(c => c.formattedValue))
            };
        } catch(e) {
            results[name] = null;
        }
    }
    return results;
}
"""

# Map worksheet names (as they appear in Performance Trends) to output key prefix
_PT_KEY_MAP = {
    "Avg Inventory KPI":      "avg_inventory",
    "VDPs KPI":               "vdps",
    "Connections KPI":        "connections",
    "Fair/Above Badge KPI":   "fair_above_badges",
    "Review KPI":             "reviews",
    "Incomplete Vehicles KPI": "under_merch",
}

# The Vehicle Summary AVG Days Trend worksheet has pivoted measure rows —
# only rows where Measure Names == "Avg days live" carry the AVG(Avg days live) value.
_PT_TREND_WORKSHEET = "Vehicle Summary AVG Days Trend"


def _extract_kpi(cols, rows) -> dict:
    """Extract current-month value and MoM delta from a Performance Trends KPI worksheet.
    Returns {"cp": float|None, "delta_pct": float|None}."""
    if not rows:
        return {"cp": None, "delta_pct": None}
    row = rows[0]
    cp = delta = None
    # Current-month value is typically "SUM(... Selected Month)"
    for col, val in zip(cols, row):
        if "Selected Month" in col and "%" not in col:
            cp = _parse_kpi(val)
            break
    # MoM delta: column with "MoM" but not the "(up)" / "(down)" arrow indicators
    for col, val in zip(cols, row):
        if "MoM" in col and "(up)" not in col and "(down)" not in col:
            parsed = _parse_kpi(val)
            if parsed is not None:
                # Deltas come in two formats: "22.0%" (already a pct) or decimal "0.0107794" (= 1.08%).
                # If the raw value has no % sign, treat as decimal and scale to percent.
                delta = parsed if "%" in (val or "") else parsed * 100
            break
    return {"cp": cp, "delta_pct": delta}


_TREND_JS = """
async (worksheetName) => {
    const viz = document.querySelector('tableau-viz');
    if (!viz || !viz.workbook) return null;
    const sheet = viz.workbook.activeSheet;
    const ws = sheet.worksheets.find(w => w.name === worksheetName);
    if (!ws) return null;
    try {
        const d = await ws.getSummaryDataAsync({ maxRows: 200 });
        return {
            cols: d.columns.map(c => c.fieldName),
            rows: d.data.map(r => r.map(c => c.formattedValue))
        };
    } catch(e) { return null; }
}
"""


def _extract_avg_days_live(cols, rows) -> dict:
    """Find the most-recent and prior-month Avg Days Live values from the trend worksheet.
    Returns {"cp": float|None, "delta_pct": float|None}."""
    if not rows:
        return {"cp": None, "delta_pct": None}
    try:
        month_idx = cols.index("MONTH(Activity Date)")
        measure_idx = cols.index("Measure Names")
        days_idx = cols.index("AVG(Avg days live)")
    except ValueError:
        return {"cp": None, "delta_pct": None}

    from datetime import datetime
    entries = []
    for r in rows:
        if len(r) <= max(month_idx, measure_idx, days_idx):
            continue
        if (r[measure_idx] or "").strip().lower() != "avg days live":
            continue
        val = _parse_kpi(r[days_idx])
        if val is None:
            continue
        try:
            dt = datetime.strptime(r[month_idx], "%B %Y")
        except (ValueError, TypeError):
            continue
        entries.append((dt, val))

    if not entries:
        return {"cp": None, "delta_pct": None}
    entries.sort(key=lambda t: t[0], reverse=True)
    cp = entries[0][1]
    delta_pct = None
    if len(entries) > 1 and entries[1][1] not in (None, 0):
        delta_pct = ((cp - entries[1][1]) / entries[1][1]) * 100
    return {"cp": cp, "delta_pct": delta_pct}


def fetch_performance_trends(uuid: str) -> Optional[dict]:
    """
    Navigate to Performance Trends for dealer UUID.
    Returns flat dict with _cp and _delta_pct keys per KPI, or None on failure.
    """
    try:
        with _get_context() as ctx:
            page = ctx.new_page()
            page.goto(
                f"{ADMIN_URL}/dealers/{uuid}/reports/performance_trends",
                timeout=TIMEOUT * 2,
                wait_until="domcontentloaded",
            )
            if "admin.cars.com" not in page.url:
                return None
            page.wait_for_selector("tableau-viz", timeout=TIMEOUT)
            page.wait_for_timeout(12_000)  # viz needs time to load workbook + worksheets

            raw = page.evaluate(_PERF_JS, list(_PT_KEY_MAP.keys()))
            if not raw:
                return None

            result = {}
            for ws_name, key in _PT_KEY_MAP.items():
                entry = raw.get(ws_name)
                if not entry:
                    result[f"{key}_cp"] = None
                    result[f"{key}_delta_pct"] = None
                    continue
                kpi = _extract_kpi(entry["cols"], entry["rows"])
                result[f"{key}_cp"] = kpi["cp"]
                result[f"{key}_delta_pct"] = kpi["delta_pct"]

            # Avg Days Live comes from a pivoted trend worksheet — separate extraction.
            trend = page.evaluate(_TREND_JS, _PT_TREND_WORKSHEET)
            if trend:
                days = _extract_avg_days_live(trend["cols"], trend["rows"])
                result["avg_days_live_cp"] = days["cp"]
                result["avg_days_live_delta_pct"] = days["delta_pct"]
            else:
                result["avg_days_live_cp"] = None
                result["avg_days_live_delta_pct"] = None

            return result if any(v is not None for v in result.values()) else None
    except Exception:
        return None


_REP_JS = """
async (targetWorksheets) => {
    const viz = document.querySelector('tableau-viz');
    if (!viz || !viz.workbook) return null;
    const sheet = viz.workbook.activeSheet;
    const results = {};
    for (const name of targetWorksheets) {
        const ws = sheet.worksheets.find(w => w.name === name);
        if (!ws) { results[name] = null; continue; }
        try {
            const data = await ws.getSummaryDataAsync({ maxRows: 5 });
            results[name] = {
                cols: data.columns.map(c => c.fieldName),
                rows: data.data.map(row => row.map(c => c.formattedValue))
            };
        } catch(e) { results[name] = null; }
    }
    return results;
}
"""

_REP_WORKSHEETS = [
    "Dealer KPI",           # [?, ?, AVG(Cars.com) rating, AVG(Total Number of Reviews)]
    "Market KPI",           # [AVG(National OEM Avg), AVG(Your Market Average DMA)]
    "Pricing KPI",          # [AVG(Pricing Transparency DMA AVG Rating), AVG(Pricing Transparency)]
    "Lead Response Rate KPI", # [AVG(% of Response Leads)]
    "Lead Survey Response", # [AVG(Follow up DMA AVG Rating), AVG(Lead Handling)]
]


def _find_val(cols, row, keyword: str) -> Optional[float]:
    """Return the first parsed value in `row` whose column contains `keyword` (case-insensitive)."""
    kw = keyword.lower()
    for col, val in zip(cols, row):
        if kw in col.lower():
            return _parse_kpi(val)
    return None


def fetch_reputation(uuid: str) -> Optional[dict]:
    """
    Navigate to Reputation Health for dealer UUID.
    Returns dict with rating, review_count, dma_avg_rating, national_avg_rating,
    pricing_transparency, lead_response_rate_pct, lead_handling_rating, or None.
    """
    try:
        with _get_context() as ctx:
            page = ctx.new_page()
            page.goto(
                f"{ADMIN_URL}/dealers/{uuid}/reports/reputation_health",
                timeout=TIMEOUT * 2,
                wait_until="domcontentloaded",
            )
            if "admin.cars.com" not in page.url:
                return None
            page.wait_for_selector("tableau-viz", timeout=TIMEOUT)
            page.wait_for_timeout(12_000)

            raw = page.evaluate(_REP_JS, _REP_WORKSHEETS)
            if not raw:
                return None

            def get(ws_name, keyword, exclude=None):
                """Find value in a worksheet row by keyword, optionally excluding columns
                containing `exclude` (useful to skip DMA/market-avg variants)."""
                entry = raw.get(ws_name)
                if not entry or not entry["rows"]:
                    return None
                kw = keyword.lower()
                ex = exclude.lower() if exclude else None
                for col, val in zip(entry["cols"], entry["rows"][0]):
                    c = col.lower()
                    if kw in c and (ex is None or ex not in c):
                        return _parse_kpi(val)
                return None

            # Dealer KPI row: the rating is the AVG(Cars.com) column
            dealer_kpi = raw.get("Dealer KPI") or {}
            dealer_rows = dealer_kpi.get("rows") or []
            rating = review_count = None
            if dealer_rows:
                rating = _find_val(dealer_kpi["cols"], dealer_rows[0], "cars.com")
                rev = _find_val(dealer_kpi["cols"], dealer_rows[0], "number of reviews")
                review_count = int(rev) if rev is not None else None

            result = {
                "rating": rating,
                "review_count": review_count,
                "dma_avg_rating": get("Market KPI", "market average"),
                "national_avg_rating": get("Market KPI", "national oem"),
                "pricing_transparency": get("Pricing KPI", "pricing transparency", exclude="dma"),
                "lead_response_rate_pct": get("Lead Response Rate KPI", "response leads"),
                "lead_handling_rating": get("Lead Survey Response", "lead handling"),
            }
            # Return None if we couldn't find even the primary rating
            if result["rating"] is None:
                return None
            return result
    except Exception:
        return None


_MC_JS = """
async () => {
    const viz = document.querySelector('tableau-viz');
    if (!viz || !viz.workbook) return null;
    await viz.workbook.activateSheetAsync('Price Comparison');
    await new Promise(r => setTimeout(r, 3000));
    const sheet = viz.workbook.activeSheet;
    const ws = sheet.worksheets.find(w => w.name === 'Pricing Summary');
    if (!ws) return null;
    try {
        const data = await ws.getSummaryDataAsync({ maxRows: 20 });
        return {
            cols: data.columns.map(c => c.fieldName),
            rows: data.data.map(row => row.map(c => c.formattedValue))
        };
    } catch(e) { return null; }
}
"""


def fetch_market_comparison(uuid: str) -> Optional[dict]:
    """
    Navigate to Demand Signals → Price Comparison → Pricing Summary for dealer UUID.
    Returns dict with above_pct, at_pct, under_pct (ints) and counts, or None.
    """
    try:
        with _get_context() as ctx:
            page = ctx.new_page()
            page.goto(
                f"{ADMIN_URL}/dealers/{uuid}/reports/demand_signals",
                timeout=TIMEOUT * 2,
                wait_until="domcontentloaded",
            )
            if "admin.cars.com" not in page.url:
                return None
            page.wait_for_selector("tableau-viz", timeout=TIMEOUT)
            page.wait_for_timeout(12_000)

            raw = page.evaluate(_MC_JS)
            if not raw or not raw.get("rows"):
                return None

            # Pricing Summary columns: ["Market price", "AGG(Vehicles)" (pct), "AGG(Vehicles)" (count)]
            # Each row: [category_label, "70.4142%", "119"]
            buckets = {"above_pct": 0, "at_pct": 0, "under_pct": 0,
                       "above_count": 0, "at_count": 0, "under_count": 0}
            for row in raw["rows"]:
                if len(row) < 3:
                    continue
                label = (row[0] or "").lower()
                pct = _parse_kpi(row[1])
                count = _parse_kpi(row[2])
                if "above" in label:
                    buckets["above_pct"] = round(pct) if pct is not None else 0
                    buckets["above_count"] = int(count) if count is not None else 0
                elif "under" in label or "below" in label:
                    buckets["under_pct"] = round(pct) if pct is not None else 0
                    buckets["under_count"] = int(count) if count is not None else 0
                elif "at market" in label or label.strip() == "at":
                    buckets["at_pct"] = round(pct) if pct is not None else 0
                    buckets["at_count"] = int(count) if count is not None else 0

            if buckets["above_count"] + buckets["at_count"] + buckets["under_count"] == 0:
                return None
            return buckets
    except Exception:
        return None

