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
import logging
import re
from contextlib import contextmanager
from typing import Optional
from urllib.parse import urlencode

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

log = logging.getLogger("admin_cars")

ADMIN_URL = "https://admin.cars.com"
CDP_ENDPOINT = "http://localhost:9222"
UUID_PATTERN = re.compile(r"dealers/([a-f0-9\-]{36})/reports")
TIMEOUT = 20_000            # ms — single-page navigation timeout
NAV_TIMEOUT = TIMEOUT * 2   # ms — report-page navigation (heavier, includes tableau-viz iframe)
VIZ_LOAD_MS = 12_000        # ms — wait after tableau-viz selector appears so the workbook API is ready

# Registry of the report slugs we fetch + the worksheets each one depends on. If any
# required worksheet is missing from a live page, the fetcher logs a WARNING and the
# missing set is surfaced back to the caller so the UI can show a "dashboard changed"
# warning. Updating Cars.com dashboards should update this manifest.
REQUIRED_WORKSHEETS: dict = {
    "performance_trends": [
        "Avg Inventory KPI", "VDPs KPI", "Connections KPI",
        "Fair/Above Badge KPI", "Review KPI", "Incomplete Vehicles KPI",
        "Vehicle Summary AVG Days Trend",
    ],
    "reputation_health": [
        "Dealer KPI", "Market KPI", "Pricing KPI",
        "Lead Response Rate KPI", "Lead Survey Response",
    ],
    "demand_signals": [],  # worksheet name changed; diagnostic logged via _MC_JS __available
    "listings_optimizer": [
        "Merchandising Completion", "Badge Details",
        "Within $500 of Good Badge", "Within $500 of Great Badge",
        "Performance Snapshot",
    ],
    "sales_influence_summary": [],  # no strict requirements — DMS absence is the common case
    "roi_one_sheeter": ["Connections", "Impressions", "Per VIN"],
    "walk_in_demand": [],   # diagnostic-first: __available logged on first run
    "vehicle_demand": [],   # diagnostic-first: __available logged on first run
}

# Track which worksheets were missing on the most recent fetch, keyed by report slug.
# Populated by `_load_report` and consumed by `get_last_missing_worksheets()`.
_last_missing: dict = {}


@contextmanager
def _get_context():
    """Connect to the user's running Chrome via CDP and yield its default context.

    Kept for the one-shot `check_session()` probe — multi-step flows should
    use `session()` instead so all navigations reuse a single tab.
    """
    with sync_playwright() as pw:
        browser = pw.chromium.connect_over_cdp(CDP_ENDPOINT)
        try:
            ctx = browser.contexts[0] if browser.contexts else browser.new_context()
            yield ctx
        finally:
            # Detaches from the user's Chrome; does not close their browser.
            browser.close()


@contextmanager
def session():
    """Yield a single reusable Playwright page connected via CDP.

    All fetches inside a `with session() as s:` block reuse the same tab —
    the tab opens once at the start, navigates between admin.cars.com
    reports, and closes when the block exits. Gives a single-interruption UX
    instead of one new tab per fetch.
    """
    _last_missing.clear()  # reset per-session so the UI shows a clean slate
    with sync_playwright() as pw:
        browser = pw.chromium.connect_over_cdp(CDP_ENDPOINT)
        ctx = browser.contexts[0] if browser.contexts else browser.new_context()
        page = ctx.new_page()
        try:
            yield _Session(page)
        finally:
            try:
                page.close()
            except Exception:
                pass
            browser.close()


def _load_report(page, uuid: str, report_slug: str) -> bool:
    """Navigate `page` to /dealers/{uuid}/reports/{report_slug} and wait for the
    tableau-viz workbook to be ready. Also records any missing REQUIRED_WORKSHEETS
    against `_last_missing[report_slug]` so callers can surface 'dashboard changed'
    warnings. Returns True if the page loaded on admin.cars.com, False otherwise."""
    try:
        page.goto(
            f"{ADMIN_URL}/dealers/{uuid}/reports/{report_slug}",
            timeout=NAV_TIMEOUT,
            wait_until="domcontentloaded",
        )
    except Exception:
        log.exception("report load failed: slug=%s uuid=%s", report_slug, uuid)
        return False
    if "admin.cars.com" not in page.url:
        log.warning("redirected off admin.cars.com: slug=%s url=%s", report_slug, page.url)
        return False
    try:
        page.wait_for_selector("tableau-viz", timeout=TIMEOUT)
    except Exception:
        log.exception("tableau-viz selector timeout: slug=%s uuid=%s", report_slug, uuid)
        return False
    page.wait_for_timeout(VIZ_LOAD_MS)

    # Probe required worksheets and record any that are missing
    required = REQUIRED_WORKSHEETS.get(report_slug, [])
    if required:
        try:
            present = page.evaluate("""() => {
                const viz = document.querySelector('tableau-viz');
                if (!viz || !viz.workbook) return [];
                const s = viz.workbook.activeSheet;
                return s.worksheets ? s.worksheets.map(w => w.name) : [];
            }""")
            missing = [w for w in required if w not in (present or [])]
            _last_missing[report_slug] = missing
            if missing:
                log.warning(
                    "worksheets missing on %s for uuid=%s: %s",
                    report_slug, uuid, missing,
                )
        except Exception:
            log.exception("worksheet probe failed: slug=%s uuid=%s", report_slug, uuid)
            _last_missing[report_slug] = []
    return True


def get_last_missing_worksheets() -> dict:
    """Return a copy of {report_slug: [missing_worksheet_names]} from the most recent
    session. UI can check this to show a 'dashboard layout changed' warning."""
    return {k: list(v) for k, v in _last_missing.items() if v}


class _Session:
    """Thin wrapper exposing the fetch functions as methods sharing one page."""

    def __init__(self, page):
        self.page = page

    def resolve_uuid(self, ccid: str) -> Optional[str]:
        return _resolve_uuid_on(self.page, ccid)

    def fetch_performance_trends(self, uuid: str) -> Optional[dict]:
        return _fetch_performance_trends_on(self.page, uuid)

    def fetch_reputation(self, uuid: str) -> Optional[dict]:
        return _fetch_reputation_on(self.page, uuid)

    def fetch_market_comparison(self, uuid: str) -> Optional[dict]:
        return _fetch_market_comparison_on(self.page, uuid)

    def fetch_listings_optimizer(self, uuid: str) -> Optional[dict]:
        return _fetch_listings_optimizer_on(self.page, uuid)

    def fetch_sales_influence(self, uuid: str) -> Optional[dict]:
        return _fetch_sales_influence_on(self.page, uuid)

    def fetch_roi_one_sheeter(self, uuid: str) -> Optional[dict]:
        return _fetch_roi_one_sheeter_on(self.page, uuid)

    def fetch_walk_in_demand(self, uuid: str) -> Optional[dict]:
        return _fetch_walk_in_demand_on(self.page, uuid)

    def fetch_vehicle_demand(self, uuid: str) -> Optional[dict]:
        return _fetch_vehicle_demand_on(self.page, uuid)


def check_session() -> bool:
    """Return True if admin.cars.com is reachable without SSO redirect.

    Uses a one-shot page because this is called on every Streamlit rerender
    (through an `@st.cache_data(ttl=300)` wrapper) and we don't want the
    session check to hold the tab open.
    """
    try:
        with _get_context() as ctx:
            page = ctx.new_page()
            try:
                page.goto(f"{ADMIN_URL}/dealers/all/reports", timeout=TIMEOUT, wait_until="domcontentloaded")
                return "admin.cars.com" in page.url
            finally:
                try:
                    page.close()
                except Exception:
                    pass
    except Exception:
        return False


def _extract_uuid_from_html(html: str) -> Optional[str]:
    """Extract the first dealer UUID from admin.cars.com search result HTML."""
    match = UUID_PATTERN.search(html)
    return match.group(1) if match else None


def _resolve_uuid_on(page, ccid: str) -> Optional[str]:
    """Navigate an existing page to search for the CCID and extract the UUID."""
    try:
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


def resolve_uuid(ccid: str) -> Optional[str]:
    """One-shot CCID → UUID resolver. Opens a tab, closes it when done."""
    with session() as s:
        return s.resolve_uuid(ccid)


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


def _fetch_performance_trends_on(page, uuid: str) -> Optional[dict]:
    """Navigate an existing page to Performance Trends and extract KPI data."""
    if not _load_report(page, uuid, "performance_trends"):
        return None
    try:
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
        log.exception("fetch_performance_trends parse failed for uuid=%s", uuid)
        return None


def fetch_performance_trends(uuid: str) -> Optional[dict]:
    """One-shot fetch. Opens a tab, fetches, closes. Prefer `session()` for multi-fetch flows."""
    with session() as s:
        return s.fetch_performance_trends(uuid)


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


def _fetch_reputation_on(page, uuid: str) -> Optional[dict]:
    """Navigate an existing page to Reputation Health and extract the rating panel."""
    if not _load_report(page, uuid, "reputation_health"):
        return None
    try:
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
        log.exception("fetch_reputation parse failed for uuid=%s", uuid)
        return None


_MC_JS = """
async () => {
    const viz = document.querySelector('tableau-viz');
    if (!viz || !viz.workbook) return null;
    await viz.workbook.activateSheetAsync('Price Comparison');
    await new Promise(r => setTimeout(r, 3000));
    const sheet = viz.workbook.activeSheet;
    const names = sheet.worksheets.map(w => w.name);
    const ws = sheet.worksheets.find(w => w.name === 'Pricing Summary');
    if (!ws) return { __available: names };
    try {
        const data = await ws.getSummaryDataAsync({ maxRows: 20 });
        return {
            cols: data.columns.map(c => c.fieldName),
            rows: data.data.map(row => row.map(c => c.formattedValue))
        };
    } catch(e) { return { __available: names }; }
}
"""


def _fetch_market_comparison_on(page, uuid: str) -> Optional[dict]:
    """Navigate an existing page to Demand Signals → Price Comparison and extract the bucket totals."""
    if not _load_report(page, uuid, "demand_signals"):
        return None
    try:
        raw = page.evaluate(_MC_JS)
        if not raw:
            return None
        if "__available" in raw:
            log.warning("Pricing Summary not found. Available worksheets: %s", raw["__available"])
            return None
        if not raw.get("rows"):
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
        log.exception("fetch_market_comparison parse failed for uuid=%s", uuid)
        return None


def fetch_market_comparison(uuid: str) -> Optional[dict]:
    """One-shot fetch. Opens a tab, fetches, closes. Prefer `session()` for multi-fetch flows."""
    with session() as s:
        return s.fetch_market_comparison(uuid)


_WID_JS = """
async () => {
    const viz = document.querySelector('tableau-viz');
    if (!viz || !viz.workbook) return null;
    const sheet = viz.workbook.activeSheet;
    const names = sheet.worksheets.map(w => w.name);
    const ws = sheet.worksheets.find(w => w.name === 'Walk-In Demand');
    if (!ws) return { __available: names };
    try {
        const data = await ws.getSummaryDataAsync({ maxRows: 50 });
        return {
            cols: data.columns.map(c => c.fieldName),
            rows: data.data.map(r => r.map(c => c.formattedValue))
        };
    } catch(e) { return { __available: names }; }
}
"""


def _fetch_walk_in_demand_on(page, uuid: str) -> Optional[dict]:
    """Navigate to walk_in_demand report and extract demand index data."""
    if not _load_report(page, uuid, "walk_in_demand"):
        return None
    try:
        raw = page.evaluate(_WID_JS)
        if not raw:
            return None
        if "__available" in raw:
            log.warning("Walk-In Demand worksheet not found. Available: %s", raw["__available"])
            return None
        if not raw.get("rows"):
            return None
        return {"cols": raw["cols"], "rows": raw["rows"]}
    except Exception:
        log.exception("fetch_walk_in_demand parse failed for uuid=%s", uuid)
        return None


def fetch_walk_in_demand(uuid: str) -> Optional[dict]:
    """One-shot fetch. Prefer session() for multi-fetch flows."""
    with session() as s:
        return s.fetch_walk_in_demand(uuid)


_VD_JS = """
async () => {
    const viz = document.querySelector('tableau-viz');
    if (!viz || !viz.workbook) return null;
    const sheet = viz.workbook.activeSheet;
    const names = sheet.worksheets.map(w => w.name);
    const ws = sheet.worksheets.find(w => w.name === 'Vehicle Demand');
    if (!ws) return { __available: names };
    try {
        const data = await ws.getSummaryDataAsync({ maxRows: 10 });
        return {
            cols: data.columns.map(c => c.fieldName),
            rows: data.data.map(r => r.map(c => c.formattedValue))
        };
    } catch(e) { return { __available: names }; }
}
"""


def _fetch_vehicle_demand_on(page, uuid: str) -> Optional[dict]:
    """Navigate to vehicle_demand report and extract top-searched segment data."""
    if not _load_report(page, uuid, "vehicle_demand"):
        return None
    try:
        raw = page.evaluate(_VD_JS)
        if not raw:
            return None
        if "__available" in raw:
            log.warning("Vehicle Demand worksheet not found. Available: %s", raw["__available"])
            return None
        if not raw.get("rows"):
            return None
        return {"cols": raw["cols"], "rows": raw["rows"]}
    except Exception:
        log.exception("fetch_vehicle_demand parse failed for uuid=%s", uuid)
        return None


def fetch_vehicle_demand(uuid: str) -> Optional[dict]:
    """One-shot fetch. Prefer session() for multi-fetch flows."""
    with session() as s:
        return s.fetch_vehicle_demand(uuid)


def fetch_reputation(uuid: str) -> Optional[dict]:
    """One-shot fetch. Opens a tab, fetches, closes. Prefer `session()` for multi-fetch flows."""
    with session() as s:
        return s.fetch_reputation(uuid)


# ─── Listings Optimizer ──────────────────────────────────────────────────────
# The Listings Optimizer report (admin.cars.com/dealers/{uuid}/reports/listings_optimizer)
# has vehicle-level pricing opportunities, badge-impact data, and Used/New breakdowns.

_LO_JS = """
async () => {
    const viz = document.querySelector('tableau-viz');
    if (!viz || !viz.workbook) return null;
    const sheet = viz.workbook.activeSheet;
    const out = {};
    const target = ['Merchandising Completion', 'Badge Details',
                    'Within $500 of Good Badge', 'Within $500 of Great Badge',
                    'Performance Snapshot'];
    for (const name of target) {
        const ws = sheet.worksheets.find(w => w.name === name);
        if (!ws) { out[name] = null; continue; }
        try {
            const d = await ws.getSummaryDataAsync({ maxRows: 50 });
            out[name] = {
                cols: d.columns.map(c => c.fieldName),
                rows: d.data.map(r => r.map(c => c.formattedValue))
            };
        } catch(e) { out[name] = null; }
    }
    return out;
}
"""


def _parse_within_500_vehicles(entry) -> list:
    """Parse the 'Within $500 of [Good/Great] Badge' worksheet — rows are pivoted by
    measure (Reduce by / Days live / Price), grouped by stock num. Returns a list of
    dicts [{"stock_num", "ymmt", "reduce_by", "days_live", "price"}] sorted by reduce_by."""
    if not entry or not entry.get("rows"):
        return []
    try:
        cols = entry["cols"]
        stock_idx = cols.index("Stock num")
        ymmt_idx = cols.index("YMMT")
        measure_idx = cols.index("Measure Names")
        value_idx = cols.index("Measure Values")
    except ValueError:
        return []
    by_stock: dict = {}
    for row in entry["rows"]:
        if len(row) <= max(stock_idx, ymmt_idx, measure_idx, value_idx):
            continue
        stock = row[stock_idx]
        measure = (row[measure_idx] or "").strip().lower()
        val = _parse_kpi(row[value_idx])
        entry_d = by_stock.setdefault(stock, {"stock_num": stock, "ymmt": row[ymmt_idx]})
        if "reduce" in measure:
            entry_d["reduce_by"] = val
        elif "days live" in measure:
            entry_d["days_live"] = val
        elif measure == "price":
            entry_d["price"] = val
    # Filter to entries that have all three measures populated, sorted by smallest reduction
    ready = [e for e in by_stock.values() if e.get("reduce_by") is not None and e.get("price") is not None]
    ready.sort(key=lambda e: e["reduce_by"])
    return ready


def _parse_badge_details(entry) -> list:
    """Parse the Badge Details worksheet. Returns list of
    [{"badge", "pct_of_inventory", "vehicles", "vdps_per_vin", "connections_per_vin"}]."""
    if not entry or not entry.get("rows"):
        return []
    cols = entry["cols"]
    try:
        badge_idx = cols.index("Price badge")
    except ValueError:
        return []
    # Find column indices via keyword matching
    def idx_containing(keyword):
        kw = keyword.lower()
        for i, c in enumerate(cols):
            if kw in c.lower():
                return i
        return None
    conn_idx = idx_containing("connections per vin")
    vdp_idx = idx_containing("vdps per vin")
    # There are two AGG(Vehicles) columns — the first is the pct, the second is the count
    veh_indices = [i for i, c in enumerate(cols) if c.lower() == "agg(vehicles)"]
    pct_idx = veh_indices[0] if len(veh_indices) > 0 else None
    count_idx = veh_indices[1] if len(veh_indices) > 1 else None

    out = []
    for row in entry["rows"]:
        badge = row[badge_idx]
        if not badge or badge.lower() in ("null", ""):
            continue
        entry_d = {"badge": badge}
        if pct_idx is not None:
            entry_d["pct_of_inventory"] = _parse_kpi(row[pct_idx])
        if count_idx is not None:
            entry_d["vehicles"] = _parse_kpi(row[count_idx])
        if conn_idx is not None:
            entry_d["connections_per_vin"] = _parse_kpi(row[conn_idx])
        if vdp_idx is not None:
            entry_d["vdps_per_vin"] = _parse_kpi(row[vdp_idx])
        out.append(entry_d)
    return out


def _parse_performance_snapshot(entry) -> dict:
    """Parse the Used/New breakdown from Performance Snapshot. Returns
    {"Used": {metric: value, ...}, "New": {metric: value, ...}}."""
    if not entry or not entry.get("rows"):
        return {}
    cols = entry["cols"]
    try:
        stock_idx = cols.index("Stock type")
        measure_idx = cols.index("Measure Names")
        value_idx = cols.index("Measure Values")
    except ValueError:
        return {}
    out: dict = {}
    for row in entry["rows"]:
        stock = row[stock_idx]
        measure = row[measure_idx]
        val = _parse_kpi(row[value_idx])
        if not stock or not measure:
            continue
        out.setdefault(stock, {})[measure] = val
    return out


def _fetch_listings_optimizer_on(page, uuid: str) -> Optional[dict]:
    """Navigate an existing page to Listings Optimizer and extract vehicle-level
    pricing opportunities, badge impact stats, and Used/New performance split."""
    if not _load_report(page, uuid, "listings_optimizer"):
        return None
    try:
        raw = page.evaluate(_LO_JS)
        if not raw:
            return None

        result: dict = {
            "badge_details": _parse_badge_details(raw.get("Badge Details")),
            "within_500_good": _parse_within_500_vehicles(raw.get("Within $500 of Good Badge"))[:5],
            "within_500_great": _parse_within_500_vehicles(raw.get("Within $500 of Great Badge"))[:5],
            "stock_type_breakdown": _parse_performance_snapshot(raw.get("Performance Snapshot")),
            "merch_complete_pct": None,
            "merch_needs_attention_count": None,
        }
        # Pull merchandising completion summary
        mc = raw.get("Merchandising Completion")
        if mc and mc.get("rows"):
            for row in mc["rows"]:
                if row and row[0] == "Complete" and len(row) > 4:
                    result["merch_complete_pct"] = _parse_kpi(row[4])
                elif row and row[0] == "Needs Attention" and len(row) > 5:
                    result["merch_needs_attention_count"] = _parse_kpi(row[5])

        # If we got nothing useful, return None
        if (not result["badge_details"] and not result["within_500_good"]
                and not result["within_500_great"] and not result["stock_type_breakdown"]):
            return None
        return result
    except Exception:
        log.exception("fetch_listings_optimizer parse failed for uuid=%s", uuid)
        return None


def fetch_listings_optimizer(uuid: str) -> Optional[dict]:
    """One-shot fetch. Opens a tab, fetches, closes. Prefer `session()` for multi-fetch flows."""
    with session() as s:
        return s.fetch_listings_optimizer(uuid)


# ─── Sales Influence Summary (DMS-backed GROI / Turn data) ───────────────────

_SIS_JS = """
async () => {
    const viz = document.querySelector('tableau-viz');
    if (!viz || !viz.workbook) return null;
    const sheet = viz.workbook.activeSheet;
    // First check whether the 'No DMS' sentinel worksheet has the "no data" message
    const noDms = sheet.worksheets.find(w => w.name === 'No DMS');
    if (noDms) {
        try {
            const d = await noDms.getSummaryDataAsync({ maxRows: 3 });
            const text = (d.data[0]?.[0]?.formattedValue || '').toLowerCase();
            if (text.includes('no dms') || text.includes('not connected') || text.includes('dms connections')) {
                return { no_dms: true };
            }
        } catch(e) {}
    }
    // Otherwise try to pull the summary worksheets
    const out = { no_dms: false };
    for (const name of ['Leads', 'Connections', 'Influenced Sales', 'Influenced Sales %', 'Vehicle Gross Sales']) {
        const ws = sheet.worksheets.find(w => w.name === name);
        if (!ws) { out[name] = null; continue; }
        try {
            const d = await ws.getSummaryDataAsync({ maxRows: 5 });
            out[name] = {
                cols: d.columns.map(c => c.fieldName),
                rows: d.data.map(r => r.map(c => c.formattedValue))
            };
        } catch(e) { out[name] = null; }
    }
    return out;
}
"""


def _fetch_sales_influence_on(page, uuid: str) -> Optional[dict]:
    """Navigate to Sales Influence Summary and extract DMS-backed attribution.
    Returns {"dms_connected": bool, ...metrics} — metrics will be empty/None if DMS is not connected."""
    if not _load_report(page, uuid, "sales_influence_summary"):
        return None
    try:
        raw = page.evaluate(_SIS_JS)
        if not raw:
            return None

        if raw.get("no_dms"):
            return {"dms_connected": False}

        # Extract headline numbers from each mini-summary worksheet. Each typically has
        # one row with the aggregate figure.
        def first_val(ws_name):
            entry = raw.get(ws_name)
            if not entry or not entry.get("rows") or not entry["rows"][0]:
                return None
            # Find the first numeric-looking cell
            for val in entry["rows"][0]:
                parsed = _parse_kpi(val)
                if parsed is not None:
                    return parsed
            return None

        return {
            "dms_connected": True,
            "leads": first_val("Leads"),
            "connections": first_val("Connections"),
            "influenced_sales": first_val("Influenced Sales"),
            "influenced_sales_pct": first_val("Influenced Sales %"),
            "vehicle_gross_sales": first_val("Vehicle Gross Sales"),
        }
    except Exception:
        log.exception("fetch_sales_influence parse failed for uuid=%s", uuid)
        return None


def fetch_sales_influence(uuid: str) -> Optional[dict]:
    """One-shot fetch. Opens a tab, fetches, closes. Prefer `session()` for multi-fetch flows."""
    with session() as s:
        return _fetch_sales_influence_on(s.page, uuid)


# ─── ROI One-Sheeter (lead source breakdown) ─────────────────────────────────
# The "Connections" worksheet breaks out every connection type:
# Website Transfers, Phone Lead - Used/New, Email Lead - *, Chat Event/Lead - Used/New,
# Walk Ins, Map Views, Driving Directions, Instant Offer, etc.
# We aggregate these into high-level categories for the dealer snapshot.

_ROI_JS = """
async () => {
    const viz = document.querySelector('tableau-viz');
    if (!viz || !viz.workbook) return null;
    const sheet = viz.workbook.activeSheet;
    const out = {};
    for (const name of ['Connections', 'Impressions', 'Per VIN']) {
        const ws = sheet.worksheets.find(w => w.name === name);
        if (!ws) { out[name] = null; continue; }
        try {
            const d = await ws.getSummaryDataAsync({ maxRows: 100 });
            out[name] = {
                cols: d.columns.map(c => c.fieldName),
                rows: d.data.map(r => r.map(c => c.formattedValue))
            };
        } catch(e) { out[name] = null; }
    }
    return out;
}
"""


def _aggregate_lead_sources(entry) -> dict:
    """Aggregate the fine-grained Connections worksheet into high-level lead-source buckets.
    Returns {"phone", "email", "chat", "website_transfers", "walk_ins", "vdp_print",
             "instant_offer", "total"} — all counts from the most-recent month."""
    if not entry or not entry.get("rows"):
        return {}
    cols = entry["cols"]
    try:
        measure_idx = cols.index("Measure Names")
        date_idx = cols.index("Begin date")
        value_idx = cols.index("Measure Values")
    except ValueError:
        return {}

    # Find the most-recent Begin date so we only aggregate the current month
    from datetime import datetime
    most_recent = None
    for r in entry["rows"]:
        if len(r) <= date_idx:
            continue
        try:
            dt = datetime.strptime(r[date_idx], "%m/%d/%Y")
        except (ValueError, TypeError):
            continue
        if most_recent is None or dt > most_recent:
            most_recent = dt
    if most_recent is None:
        return {}
    target_date = most_recent.strftime("%-m/%-d/%Y")

    buckets = {"phone": 0.0, "email": 0.0, "chat": 0.0, "website_transfers": 0.0,
               "walk_ins": 0.0, "vdp_print": 0.0, "instant_offer": 0.0, "other": 0.0}
    for r in entry["rows"]:
        if len(r) <= max(measure_idx, date_idx, value_idx):
            continue
        if r[date_idx] != target_date:
            continue
        measure = (r[measure_idx] or "").lower()
        val = _parse_kpi(r[value_idx]) or 0.0
        if val == 0:
            continue
        # Skip aggregated/subtotal rows (e.g. plain "Website Transfers" already summed)
        # We want the leaf categories; de-duplicate by excluding the bare totals.
        if measure == "website transfers":
            # Use this as the total rather than summing sub-items to avoid double-counting
            buckets["website_transfers"] = val
        elif measure.startswith("website transfers -"):
            continue  # already captured by 'website transfers' total
        elif "phone lead" in measure:
            buckets["phone"] += val
        elif measure.startswith("email lead"):
            # Avoid double-counting: 'Email Lead - Used' and 'Email Lead - New' are the top-level totals
            # Sub-categories like 'Email Lead - Online Shopper - Used' are double-counted in Used; skip.
            if measure in ("email lead - used", "email lead - new",
                           "email lead - finance intent", "email lead - credit application",
                           "email lead - prequalified"):
                buckets["email"] += val
        elif "chat lead" in measure or "chat event" in measure:
            buckets["chat"] += val
        elif "total walk ins" in measure or measure == "walk ins":
            buckets["walk_ins"] = val
        elif "vdp print" in measure:
            buckets["vdp_print"] = val
        elif "instant offer" in measure:
            buckets["instant_offer"] += val
        elif measure in ("map views", "driving directions"):
            buckets["other"] += val

    buckets["total"] = sum(v for k, v in buckets.items() if k != "total")
    buckets["month"] = most_recent.strftime("%B %Y")
    # Convert to ints for display tidiness
    for k in list(buckets.keys()):
        if k != "month" and isinstance(buckets[k], float):
            buckets[k] = int(round(buckets[k]))
    return buckets


def _fetch_roi_one_sheeter_on(page, uuid: str) -> Optional[dict]:
    """Navigate to ROI One-Sheeter and extract the lead-source breakdown + leads-per-VIN."""
    if not _load_report(page, uuid, "roi_one_sheeter"):
        return None
    try:
        raw = page.evaluate(_ROI_JS)
        if not raw:
            return None

        result: dict = {"lead_sources": _aggregate_lead_sources(raw.get("Connections"))}

        # Pull Leads Per VIN (any non-null value; take the most recent)
        per_vin = raw.get("Per VIN")
        if per_vin and per_vin.get("rows"):
            cols = per_vin["cols"]
            try:
                measure_idx = cols.index("Measure Names")
                value_idx = cols.index("Measure Values")
            except ValueError:
                measure_idx = value_idx = None
            if measure_idx is not None:
                for row in per_vin["rows"]:
                    if (row[measure_idx] or "").lower() == "leads per vin":
                        val = _parse_kpi(row[value_idx])
                        if val is not None:
                            result["leads_per_vin"] = val
                            break

        if not result.get("lead_sources"):
            return None
        return result
    except Exception:
        log.exception("fetch_roi_one_sheeter parse failed for uuid=%s", uuid)
        return None


def fetch_roi_one_sheeter(uuid: str) -> Optional[dict]:
    """One-shot fetch. Opens a tab, fetches, closes. Prefer `session()` for multi-fetch flows."""
    with session() as s:
        return _fetch_roi_one_sheeter_on(s.page, uuid)

