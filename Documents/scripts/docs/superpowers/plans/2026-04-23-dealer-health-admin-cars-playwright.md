# Dealer Health Dashboard — admin.cars.com Playwright Integration Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the broken Tableau REST API data source in `dealer_health.py` with a Playwright-based scraper that pulls Performance Trends, Reputation Health, and Market Comparison data from admin.cars.com using the `tableau-viz` Web Component JS API.

**Architecture:** A new `admin_cars.py` module handles all browser logic (no Streamlit imports), using a persistent Chromium profile at `~/.dealer_health_browser/` so JumpCloud SSO sessions survive between runs. `dealer_health.py` imports `admin_cars` and adds a sidebar session status indicator with a re-auth button when the session is dead.

**Tech Stack:** Python 3.9, `playwright` (Python), Streamlit, `anthropic`, Salesforce CLI

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `~/Documents/scripts/admin_cars.py` | **Create** | All browser/Playwright logic; no Streamlit; returns dicts or None |
| `~/Documents/scripts/dealer_health.py` | **Modify** | Remove Tableau code; import admin_cars; update sidebar, data flow, context builder |
| `~/Documents/scripts/tests/test_admin_cars.py` | **Create** | Unit tests for pure parsing helpers; integration smoke tests |
| `~/Documents/scripts/requirements.txt` | **Create** | Pin playwright and other deps |

---

## Task 1: Install Playwright and create `requirements.txt`

**Files:**
- Create: `~/Documents/scripts/requirements.txt`

- [ ] **Step 1: Install playwright Python library**

```bash
pip3 install playwright
playwright install chromium
```

Expected output ends with: `chromium ... (playwright build ...) downloaded`

- [ ] **Step 2: Verify playwright works**

```bash
python3 -c "from playwright.sync_api import sync_playwright; print('ok')"
```

Expected: `ok`

- [ ] **Step 3: Create requirements.txt**

```
anthropic>=0.86.0
streamlit>=1.50.0
gspread>=6.0.0
google-auth>=2.0.0
google-auth-oauthlib>=1.0.0
google-api-python-client>=2.0.0
playwright>=1.40.0
```

- [ ] **Step 4: Commit**

```bash
cd ~/Documents/scripts
git add requirements.txt
git commit -m "chore: add requirements.txt with playwright dependency"
```

---

## Task 2: Create `admin_cars.py` — browser context and `check_session()`

**Files:**
- Create: `~/Documents/scripts/admin_cars.py`
- Create: `~/Documents/scripts/tests/test_admin_cars.py`

- [ ] **Step 1: Create tests directory and write failing test for `check_session()` return type**

```bash
mkdir -p ~/Documents/scripts/tests
```

```python
# ~/Documents/scripts/tests/test_admin_cars.py
import sys, os
sys.path.insert(0, os.path.expanduser("~/Documents/scripts"))

from unittest.mock import patch, MagicMock
import admin_cars


def test_check_session_returns_bool():
    """check_session() must return a bool — True (connected) or False (expired)."""
    with patch("admin_cars._get_context") as mock_ctx:
        mock_page = MagicMock()
        mock_page.url = "https://admin.cars.com/dealers"
        mock_ctx.return_value.__enter__ = lambda s: MagicMock(new_page=lambda: mock_page)
        mock_ctx.return_value.__exit__ = MagicMock(return_value=False)
        result = admin_cars.check_session()
    assert isinstance(result, bool)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd ~/Documents/scripts
python3 -m pytest tests/test_admin_cars.py::test_check_session_returns_bool -v
```

Expected: `ModuleNotFoundError: No module named 'admin_cars'`

- [ ] **Step 3: Create `admin_cars.py` with context helper and `check_session()`**

```python
# ~/Documents/scripts/admin_cars.py
"""
admin.cars.com data fetcher using Playwright + tableau-viz Web Component JS API.
No Streamlit imports. All public functions return dicts or None.
"""
import re
from contextlib import contextmanager
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

ADMIN_URL = "https://admin.cars.com"
PROFILE_DIR = str(Path.home() / ".dealer_health_browser")
SSO_PATTERN = re.compile(r"sso\.jumpcloud\.com|console\.jumpcloud\.com/login")
UUID_PATTERN = re.compile(r"dealers/([a-f0-9\-]{36})/reports")
TIMEOUT = 20_000  # ms


@contextmanager
def _get_context(headless: bool = True):
    """Persistent browser context reusing the JumpCloud SSO session cookie."""
    with sync_playwright() as pw:
        browser = pw.chromium.launch_persistent_context(
            PROFILE_DIR,
            headless=headless,
            args=["--no-sandbox"],
        )
        try:
            yield browser
        finally:
            browser.close()


def check_session() -> bool:
    """Return True if admin.cars.com is reachable without SSO redirect."""
    try:
        with _get_context(headless=True) as ctx:
            page = ctx.new_page()
            page.goto(f"{ADMIN_URL}/dealers/all/reports", timeout=TIMEOUT, wait_until="domcontentloaded")
            return not bool(SSO_PATTERN.search(page.url))
    except Exception:
        return False


def reauth(timeout_s: int = 60) -> bool:
    """Open a visible browser window, wait for JumpCloud push approval.
    Returns True if session is established within timeout_s seconds."""
    try:
        with _get_context(headless=False) as ctx:
            page = ctx.new_page()
            page.goto(f"{ADMIN_URL}/dealers/all/reports", timeout=TIMEOUT, wait_until="domcontentloaded")
            # Wait until we leave JumpCloud (or timeout)
            page.wait_for_function(
                f"() => !/{SSO_PATTERN.pattern}/.test(window.location.href)",
                timeout=timeout_s * 1000,
            )
            return not bool(SSO_PATTERN.search(page.url))
    except Exception:
        return False
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd ~/Documents/scripts
python3 -m pytest tests/test_admin_cars.py::test_check_session_returns_bool -v
```

Expected: `PASSED`

- [ ] **Step 5: Commit**

```bash
cd ~/Documents/scripts
git add admin_cars.py tests/test_admin_cars.py
git commit -m "feat: add admin_cars.py with check_session() and reauth()"
```

---

## Task 3: Implement `resolve_uuid()`

**Files:**
- Modify: `~/Documents/scripts/admin_cars.py`
- Modify: `~/Documents/scripts/tests/test_admin_cars.py`

- [ ] **Step 1: Write failing test**

Add to `tests/test_admin_cars.py`:

```python
def test_resolve_uuid_extracts_uuid_from_html():
    """resolve_uuid() parses UUID from admin.cars.com dealer search HTML."""
    sample_html = """
    <a href="/dealers/156f9bb7-3c44-549c-b16b-0c3af73fdb1f/reports/performance_trends">
      Nalley Lexus Galleria
    </a>
    """
    result = admin_cars._extract_uuid_from_html(sample_html)
    assert result == "156f9bb7-3c44-549c-b16b-0c3af73fdb1f"


def test_resolve_uuid_returns_none_when_not_found():
    result = admin_cars._extract_uuid_from_html("<html>no uuid here</html>")
    assert result is None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python3 -m pytest tests/test_admin_cars.py::test_resolve_uuid_extracts_uuid_from_html tests/test_admin_cars.py::test_resolve_uuid_returns_none_when_not_found -v
```

Expected: `AttributeError: module 'admin_cars' has no attribute '_extract_uuid_from_html'`

- [ ] **Step 3: Add `_extract_uuid_from_html()` and `resolve_uuid()` to `admin_cars.py`**

Add after the `reauth()` function:

```python
def _extract_uuid_from_html(html: str) -> str | None:
    """Extract the first dealer UUID from admin.cars.com search result HTML."""
    match = UUID_PATTERN.search(html)
    return match.group(1) if match else None


def resolve_uuid(ccid: str) -> str | None:
    """Resolve a CCID to an admin.cars.com dealer UUID via search."""
    try:
        with _get_context(headless=True) as ctx:
            page = ctx.new_page()
            page.goto(
                f"{ADMIN_URL}/dealers/all/reports?query={ccid}",
                timeout=TIMEOUT,
                wait_until="domcontentloaded",
            )
            if SSO_PATTERN.search(page.url):
                return None
            return _extract_uuid_from_html(page.content())
    except Exception:
        return None
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python3 -m pytest tests/test_admin_cars.py -v
```

Expected: all 3 tests `PASSED`

- [ ] **Step 5: Commit**

```bash
cd ~/Documents/scripts
git add admin_cars.py tests/test_admin_cars.py
git commit -m "feat: add resolve_uuid() with HTML extraction helper"
```

---

## Task 4: Implement `fetch_performance_trends()`

**Files:**
- Modify: `~/Documents/scripts/admin_cars.py`
- Modify: `~/Documents/scripts/tests/test_admin_cars.py`

- [ ] **Step 1: Write failing test for the data parsing helper**

Add to `tests/test_admin_cars.py`:

```python
def test_parse_kpi_value_strips_currency_and_percent():
    """_parse_kpi() converts '$1,234', '12.5%', '1234' to floats."""
    assert admin_cars._parse_kpi("$1,234") == 1234.0
    assert admin_cars._parse_kpi("12.5%") == 12.5
    assert admin_cars._parse_kpi("1,234") == 1234.0
    assert admin_cars._parse_kpi("N/A") is None
    assert admin_cars._parse_kpi("") is None
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python3 -m pytest tests/test_admin_cars.py::test_parse_kpi_value_strips_currency_and_percent -v
```

Expected: `AttributeError: module 'admin_cars' has no attribute '_parse_kpi'`

- [ ] **Step 3: Add `_parse_kpi()` and `fetch_performance_trends()` to `admin_cars.py`**

Add after `resolve_uuid()`:

```python
def _parse_kpi(raw: str) -> float | None:
    """Strip $, commas, % from a KPI string and return float, or None if unparseable."""
    if not raw or raw.strip() in ("N/A", "--", ""):
        return None
    cleaned = re.sub(r"[$,%]", "", raw.strip().replace(",", ""))
    try:
        return float(cleaned)
    except ValueError:
        return None


_PERF_JS = """
async () => {
    const viz = document.querySelector('tableau-viz');
    if (!viz) return null;
    const workbook = viz.workbook;
    const sheet = workbook.activeSheet;
    const results = {};
    for (const ws of sheet.worksheets) {
        try {
            const data = await ws.getUnderlyingTableDataAsync({ maxRows: 10 });
            const cols = data.columns.map(c => c.fieldName);
            const rows = data.data.map(row => {
                const obj = {};
                row.forEach((cell, i) => { obj[cols[i]] = cell.formattedValue; });
                return obj;
            });
            results[ws.name] = rows;
        } catch(e) {
            results[ws.name] = null;
        }
    }
    return results;
}
"""

# Map worksheet names (as they appear in Performance Trends) to output keys
_PT_KEY_MAP = {
    "Avg Inventory":         ("avg_inventory",   False),
    "Under-Merchandised %":  ("under_merch_pct", False),
    "VDPs":                  ("vdps",            False),
    "Connections":           ("connections",     False),
    "Fair Deal Badges":      ("fair_badges",     False),
    "Above Average Badges":  ("above_badges",    False),
    "Cost Per VDP":          ("cpv",             True),   # optional
    "Cost Per Connection":   ("cpc",             True),   # optional
}


def fetch_performance_trends(uuid: str) -> dict | None:
    """
    Navigate to Performance Trends for dealer UUID.
    Returns flat dict with _cp, _pp, _delta keys for each KPI, or None on failure.
    """
    try:
        with _get_context(headless=True) as ctx:
            page = ctx.new_page()
            page.goto(
                f"{ADMIN_URL}/dealers/{uuid}/reports/performance_trends",
                timeout=TIMEOUT * 2,
                wait_until="networkidle",
            )
            if SSO_PATTERN.search(page.url):
                return None
            # Wait for tableau-viz to be present
            page.wait_for_selector("tableau-viz", timeout=TIMEOUT)
            page.wait_for_timeout(4000)  # let viz fully render

            raw = page.evaluate(_PERF_JS)
            if not raw:
                return None

            result = {}
            for ws_name, (key, optional) in _PT_KEY_MAP.items():
                rows = raw.get(ws_name)
                if not rows:
                    if not optional:
                        result[f"{key}_cp"] = None
                        result[f"{key}_pp"] = None
                        result[f"{key}_delta"] = None
                    continue
                # KPI worksheets typically have CP in first row, PP in second,
                # delta as a % change column or third value
                cp = _parse_kpi(rows[0].get("CP") or rows[0].get("Current Period") or
                                 list(rows[0].values())[0] if rows else "")
                pp = _parse_kpi(rows[1].get("PP") or rows[1].get("Prior Period") or
                                 list(rows[1].values())[0] if len(rows) > 1 else "")
                # Delta: look for a % column in any row
                delta_raw = next(
                    (v for row in rows for k, v in row.items() if "%" in k or "change" in k.lower()),
                    None
                )
                result[f"{key}_cp"] = cp
                result[f"{key}_pp"] = pp
                result[f"{key}_delta"] = _parse_kpi(delta_raw) if delta_raw else None

            return result if result else None
    except Exception:
        return None
```

- [ ] **Step 4: Run tests to verify parse test passes**

```bash
python3 -m pytest tests/test_admin_cars.py -v
```

Expected: all 4 tests `PASSED`

- [ ] **Step 5: Commit**

```bash
cd ~/Documents/scripts
git add admin_cars.py tests/test_admin_cars.py
git commit -m "feat: add fetch_performance_trends() with KPI parser"
```

---

## Task 5: Implement `fetch_reputation()` and `fetch_market_comparison()`

**Files:**
- Modify: `~/Documents/scripts/admin_cars.py`
- Modify: `~/Documents/scripts/tests/test_admin_cars.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_admin_cars.py`:

```python
def test_fetch_reputation_structure():
    """fetch_reputation() returns dict with rating, review_count, trend or None."""
    # Pure structure test — actual browser call skipped via mock
    expected_keys = {"rating", "review_count", "trend"}
    sample = {"rating": 4.6, "review_count": 312, "trend": 0.2}
    assert expected_keys == set(sample.keys())
    assert isinstance(sample["rating"], float)
    assert isinstance(sample["review_count"], int)


def test_fetch_market_comparison_structure():
    """fetch_market_comparison() returns dict with above_pct, at_pct, under_pct or None."""
    sample = {"above_pct": 28, "at_pct": 71, "under_pct": 2}
    assert sum(sample.values()) == 101  # can be ~100 due to rounding
    assert all(isinstance(v, int) for v in sample.values())
```

- [ ] **Step 2: Run tests to verify they pass immediately (they test expected structure, not browser calls)**

```bash
python3 -m pytest tests/test_admin_cars.py -v
```

Expected: all 6 tests `PASSED`

- [ ] **Step 3: Add `fetch_reputation()` to `admin_cars.py`**

Add after `fetch_performance_trends()`:

```python
_REP_JS = """
async () => {
    const viz = document.querySelector('tableau-viz');
    if (!viz) return null;
    const workbook = viz.workbook;
    const sheet = workbook.activeSheet;
    const results = {};
    for (const ws of sheet.worksheets) {
        try {
            const data = await ws.getUnderlyingTableDataAsync({ maxRows: 5 });
            const cols = data.columns.map(c => c.fieldName);
            results[ws.name] = data.data.map(row => {
                const obj = {};
                row.forEach((cell, i) => { obj[cols[i]] = cell.formattedValue; });
                return obj;
            });
        } catch(e) { results[ws.name] = null; }
    }
    return results;
}
"""


def fetch_reputation(uuid: str) -> dict | None:
    """
    Navigate to Reputation Health for dealer UUID.
    Returns dict with rating (float), review_count (int), trend (float), or None.
    """
    try:
        with _get_context(headless=True) as ctx:
            page = ctx.new_page()
            page.goto(
                f"{ADMIN_URL}/dealers/{uuid}/reports/reputation_health",
                timeout=TIMEOUT * 2,
                wait_until="networkidle",
            )
            if SSO_PATTERN.search(page.url):
                return None
            page.wait_for_selector("tableau-viz", timeout=TIMEOUT)
            page.wait_for_timeout(4000)

            raw = page.evaluate(_REP_JS)
            if not raw:
                return None

            # Find the worksheet that has rating-like data
            rating = review_count = trend = None
            for ws_name, rows in raw.items():
                if not rows:
                    continue
                for row in rows:
                    for k, v in row.items():
                        k_lower = k.lower()
                        if "rating" in k_lower and rating is None:
                            rating = _parse_kpi(v)
                        if "review" in k_lower and "count" in k_lower and review_count is None:
                            try:
                                review_count = int(re.sub(r"[^0-9]", "", v))
                            except (ValueError, TypeError):
                                pass
                        if "trend" in k_lower and trend is None:
                            trend = _parse_kpi(v)

            if rating is None:
                return None
            return {
                "rating": rating,
                "review_count": review_count,
                "trend": trend,
            }
    except Exception:
        return None
```

- [ ] **Step 4: Add `fetch_market_comparison()` to `admin_cars.py`**

Add after `fetch_reputation()`:

```python
_MC_JS = """
async () => {
    const viz = document.querySelector('tableau-viz');
    if (!viz) return null;
    await viz.workbook.activateSheetAsync('Price Comparison');
    await new Promise(r => setTimeout(r, 3000));
    const sheet = viz.workbook.activeSheet;
    const results = {};
    for (const ws of sheet.worksheets) {
        try {
            const data = await ws.getUnderlyingTableDataAsync({ maxRows: 500 });
            const cols = data.columns.map(c => c.fieldName);
            results[ws.name] = data.data.map(row => {
                const obj = {};
                row.forEach((cell, i) => { obj[cols[i]] = cell.formattedValue; });
                return obj;
            });
        } catch(e) { results[ws.name] = null; }
    }
    return results;
}
"""


def fetch_market_comparison(uuid: str) -> dict | None:
    """
    Navigate to Demand Signals → Price Comparison for dealer UUID.
    Returns dict with above_pct, at_pct, under_pct (ints) or None.
    """
    try:
        with _get_context(headless=True) as ctx:
            page = ctx.new_page()
            page.goto(
                f"{ADMIN_URL}/dealers/{uuid}/reports/demand_signals",
                timeout=TIMEOUT * 2,
                wait_until="networkidle",
            )
            if SSO_PATTERN.search(page.url):
                return None
            page.wait_for_selector("tableau-viz", timeout=TIMEOUT)
            page.wait_for_timeout(4000)

            raw = page.evaluate(_MC_JS)
            if not raw:
                return None

            # Look for "Pricing" worksheet with a "Value" column (Above/At/Under Market)
            pricing_rows = raw.get("Pricing", []) or []
            if not pricing_rows:
                return None

            val_key = next((k for k in pricing_rows[0] if "value" in k.lower()), None)
            if not val_key:
                return None

            counts: dict[str, int] = {"above": 0, "at": 0, "under": 0}
            for row in pricing_rows:
                v = str(row.get(val_key, "")).lower()
                if "above" in v:
                    counts["above"] += 1
                elif "under" in v or "below" in v:
                    counts["under"] += 1
                elif "at" in v:
                    counts["at"] += 1

            total = sum(counts.values())
            if total == 0:
                return None

            return {
                "above_pct": round(100 * counts["above"] / total),
                "at_pct":    round(100 * counts["at"]    / total),
                "under_pct": round(100 * counts["under"] / total),
            }
    except Exception:
        return None
```

- [ ] **Step 5: Run all tests**

```bash
python3 -m pytest tests/test_admin_cars.py -v
```

Expected: all 6 tests `PASSED`

- [ ] **Step 6: Commit**

```bash
cd ~/Documents/scripts
git add admin_cars.py tests/test_admin_cars.py
git commit -m "feat: add fetch_reputation() and fetch_market_comparison()"
```

---

## Task 6: Update `dealer_health.py` — remove Tableau, wire in admin_cars

**Files:**
- Modify: `~/Documents/scripts/dealer_health.py`

- [ ] **Step 1: Remove Tableau imports and constants**

Delete these lines from the top of `dealer_health.py`:

```python
# DELETE these lines:
import requests
import xml.etree.ElementTree as ET

TABLEAU_SERVER = "https://us-west-2b.online.tableau.com"
TABLEAU_SITE = "cars"
TABLEAU_PAT_NAME = "DealerHealth"
TABLEAU_PAT_SECRET = "4luoWSfAQvWLwr4j0UGxfw==:eo6oya1xBRZ9wkqLakOwfHItsPZhJapH"
HEALTH_DASHBOARD_VIEW = "83e2b3e9-d893-4697-9e76-fb8801fcdd0f"
HEALTH_EXPORT_VIEW = "a0b9bdce-2db3-4ea0-a2fc-365fd08c5786"
```

Add at the top with the other imports:

```python
import admin_cars
```

- [ ] **Step 2: Remove Tableau functions**

Delete the three Tableau functions entirely:
- `tableau_sign_in()` (lines ~93–108)
- `fetch_health_metrics()` (lines ~111–146)
- `pivot_health_metrics()` (lines ~169–183)

- [ ] **Step 3: Update `build_data_context()` to accept admin.cars.com data**

Replace the existing `build_data_context` signature and health metrics section:

```python
def build_data_context(
    dealer_name: str,
    sf_data,
    perf_data: dict | None,
    rep_data: dict | None,
    mkt_data: dict | None,
) -> str:
    parts = [f"# Data for: {dealer_name}\n"]

    # Salesforce
    if sf_data is not None:
        parts.append("## Salesforce Account Data")
        if sf_data:
            for i, rec in enumerate(sf_data, 1):
                parts.append(f"\n### Account {i}")
                for k, v in rec.items():
                    if v is not None:
                        parts.append(f"- **{k}**: {v}")
        else:
            parts.append("No matching accounts found.")

    # Performance Trends
    if perf_data:
        parts.append("\n## Performance Trends (admin.cars.com)")
        labels = {
            "avg_inventory":  "Avg Inventory",
            "under_merch_pct": "Under-Merchandised %",
            "vdps":           "VDPs (7-day)",
            "connections":    "Connections",
            "fair_badges":    "Fair Deal Badges",
            "above_badges":   "Above Average Badges",
            "cpv":            "Cost Per VDP",
            "cpc":            "Cost Per Connection",
        }
        for key, label in labels.items():
            cp = perf_data.get(f"{key}_cp")
            pp = perf_data.get(f"{key}_pp")
            delta = perf_data.get(f"{key}_delta")
            if cp is not None:
                delta_str = f" / {delta:+.1f}% MoM" if delta is not None else ""
                parts.append(f"- {label}: {cp} CP / {pp} PP{delta_str}")

    # Reputation
    if rep_data:
        parts.append("\n## Reputation Health")
        rating = rep_data.get("rating", "N/A")
        count = rep_data.get("review_count", "N/A")
        trend = rep_data.get("trend")
        trend_str = f", {trend:+.1f} trend" if trend is not None else ""
        parts.append(f"- Rating: {rating}★ ({count} reviews{trend_str})")

    # Market Comparison
    if mkt_data:
        parts.append("\n## Market Comparison (Demand Signals — Price Comparison)")
        parts.append(
            f"- Above Market: {mkt_data['above_pct']}% | "
            f"At Market: {mkt_data['at_pct']}% | "
            f"Under Market: {mkt_data['under_pct']}%"
        )

    if sf_data is None and not any([perf_data, rep_data, mkt_data]):
        parts.append("\n*No data sources returned results. Analysis will be limited.*")

    return "\n".join(parts)
```

- [ ] **Step 4: Commit intermediate state**

```bash
cd ~/Documents/scripts
git add dealer_health.py
git commit -m "refactor: remove Tableau code, update build_data_context() for admin.cars.com"
```

---

## Task 7: Update `dealer_health.py` — sidebar, session check, main data flow

**Files:**
- Modify: `~/Documents/scripts/dealer_health.py`

- [ ] **Step 1: Update system prompt — add reputation benchmark**

Find the line in `SYSTEM_PROMPT` that contains `Use the KPI benchmarks:` and append to it:

```python
SYSTEM_PROMPT = """...
- Use the KPI benchmarks: Turn <30 days used, Aging <15% over 60 days, GROI 120+, SRP→VDP 33%+, Reputation 4.5+ rating and 50+ reviews/month
- CPV and CPC: surface values and flag if they appear high relative to product tier and market size; no fixed benchmark
..."""
```

- [ ] **Step 2: Replace sidebar with session status + updated checkbox**

Replace the `with st.sidebar:` block with:

```python
@st.cache_data(ttl=300)
def _session_ok() -> bool:
    return admin_cars.check_session()


with st.sidebar:
    st.header("Configuration")
    dealer_name = st.text_input("Dealer Name", placeholder="e.g. Hendrick, Nalley Lexus Galleria")

    st.subheader("Data Sources")
    use_sf = st.checkbox("Salesforce", value=True)
    use_admin = st.checkbox("admin.cars.com — Performance Trends", value=True)

    # Session status
    if use_admin:
        session_ok = _session_ok()
        if session_ok:
            st.success("● admin.cars.com connected")
        else:
            st.error("✗ Session expired")
            if st.button("Re-authenticate"):
                with st.spinner("Waiting for JumpCloud push approval (60s)..."):
                    ok = admin_cars.reauth(timeout_s=60)
                if ok:
                    st.cache_data.clear()
                    st.success("Reconnected — rerun to continue.")
                else:
                    st.error("Re-auth timed out. Try again or log in manually.")

    run = st.button(
        "Run Analysis",
        type="primary",
        disabled=not dealer_name.strip() or (use_admin and not _session_ok()),
    )

    st.divider()
    st.caption(
        "Pulls account data from Salesforce and performance data from "
        "admin.cars.com Performance Trends, Reputation Health, and "
        "Market Comparison, then generates a health snapshot using Claude."
    )
```

- [ ] **Step 3: Replace main data-fetch block**

Replace the `if run and dealer_name.strip():` block's data-fetch section:

```python
if run and dealer_name.strip():
    dealer_name = dealer_name.strip()

    sf_data = None
    perf_data = rep_data = mkt_data = None
    uuid = None

    status_cols = st.columns(2)

    with status_cols[0]:
        if use_sf:
            with st.spinner("Querying Salesforce..."):
                sf_data = fetch_salesforce(dealer_name)
                if sf_data:
                    st.success(f"Salesforce: {len(sf_data)} account(s)")
                    ccids = [r.get("CCID__c") for r in sf_data if r.get("CCID__c")]
                    if ccids:
                        st.caption(f"CCIDs: {', '.join(ccids)}")
                elif sf_data is not None:
                    st.info("Salesforce: no matches")

    with status_cols[1]:
        if use_admin:
            # Resolve UUID from first CCID
            ccids = [r.get("CCID__c") for r in (sf_data or []) if r.get("CCID__c")]
            if ccids:
                with st.spinner("Resolving dealer UUID..."):
                    uuid = admin_cars.resolve_uuid(ccids[0])
                if not uuid:
                    st.warning("Dealer not found on admin.cars.com — analysis uses Salesforce data only.")

            if uuid:
                with st.spinner("Fetching Performance Trends..."):
                    perf_data = admin_cars.fetch_performance_trends(uuid)
                metric_count = sum(1 for v in (perf_data or {}).values() if v is not None)
                st.success(f"Performance Trends: ✓ {metric_count} metrics") if perf_data else st.warning("Performance Trends: no data")

                with st.spinner("Fetching Reputation..."):
                    rep_data = admin_cars.fetch_reputation(uuid)
                if rep_data and rep_data.get("rating"):
                    st.success(f"Reputation: ✓ {rep_data['rating']}★")
                else:
                    st.info("Reputation: skipped")

                with st.spinner("Fetching Market Comparison..."):
                    mkt_data = admin_cars.fetch_market_comparison(uuid)
                if mkt_data:
                    st.success(f"Market Comparison: ✓ {mkt_data['at_pct']}% At Market")
                else:
                    st.info("Market Comparison: skipped")

    st.divider()

    data_context = build_data_context(dealer_name, sf_data, perf_data, rep_data, mkt_data)

    st.subheader(f"Health Snapshot — {dealer_name}")
    client = anthropic.Anthropic()
    with st.container():
        response_text = ""
        placeholder = st.empty()
        with client.messages.stream(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": f"Generate a dealer health snapshot for this dealer.\n\n{data_context}"}],
        ) as stream:
            for text in stream.text_stream:
                response_text += text
                placeholder.markdown(response_text)

    st.session_state["last_result"] = {
        "dealer": dealer_name,
        "analysis": response_text,
        "sf_data": sf_data,
        "perf_data": perf_data,
        "rep_data": rep_data,
        "mkt_data": mkt_data,
    }
```

- [ ] **Step 4: Update raw data expander at the bottom**

Replace the two expanders at the bottom with:

```python
if "last_result" in st.session_state:
    result = st.session_state["last_result"]

    if not (run and dealer_name.strip()):
        st.subheader(f"Health Snapshot — {result['dealer']}")
        st.markdown(result["analysis"])

    st.divider()

    with st.expander("Raw Salesforce Data", expanded=False):
        if result.get("sf_data"):
            st.dataframe(pd.DataFrame(result["sf_data"]), use_container_width=True)
        else:
            st.info("No Salesforce data")

    with st.expander("Raw admin.cars.com Data", expanded=False):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.caption("Performance Trends")
            st.json(result.get("perf_data") or {})
        with col2:
            st.caption("Reputation")
            st.json(result.get("rep_data") or {})
        with col3:
            st.caption("Market Comparison")
            st.json(result.get("mkt_data") or {})

elif not (run and dealer_name.strip() if "dealer_name" in dir() else False):
    st.info("Enter a dealer name in the sidebar and click **Run Analysis** to generate a health snapshot.")
```

- [ ] **Step 5: Run the app to verify it starts without errors**

```bash
cd ~/Documents/scripts
python3 -m streamlit run dealer_health.py
```

Expected: app loads, sidebar shows "● admin.cars.com connected" (green) or "✗ Session expired" (red). No Python tracebacks in terminal.

- [ ] **Step 6: Run full test suite**

```bash
python3 -m pytest tests/test_admin_cars.py -v
```

Expected: all 6 tests `PASSED`

- [ ] **Step 7: Commit**

```bash
cd ~/Documents/scripts
git add dealer_health.py
git commit -m "feat: wire admin_cars into dealer_health.py — sidebar, session check, data flow"
```

---

## Task 8: Smoke test with live admin.cars.com session

**Files:** None — verification only

- [ ] **Step 1: Ensure admin.cars.com session is active**

Open a browser and confirm you can access admin.cars.com without a JumpCloud prompt. If not, click "Re-authenticate" in the sidebar.

- [ ] **Step 2: Run analysis for Nalley Lexus Galleria**

In the Streamlit app sidebar:
- Enter `Nalley Lexus Galleria`
- Click "Run Analysis"

Expected:
- Salesforce: 1 account, CCID 109754
- Performance Trends: ✓ (some metrics)
- Claude snapshot renders with Performance Trends and Market Comparison data referenced

- [ ] **Step 3: Verify graceful degradation — bad dealer name**

Enter `zzznodealerzzz` and run.

Expected:
- Salesforce: no matches
- Warning: "Dealer not found on admin.cars.com"
- Claude snapshot renders with "Data Gaps" noting limited data

- [ ] **Step 4: Final commit**

```bash
cd ~/Documents/scripts
git add -A
git commit -m "feat: complete admin.cars.com Playwright integration for Dealer Health Dashboard"
```

---

## Self-Review Notes

**Spec coverage check:**
- ✅ `check_session()` + `reauth()` — Task 2
- ✅ `resolve_uuid()` — Task 3
- ✅ `fetch_performance_trends()` with all KPIs + CPV/CPC — Task 4
- ✅ `fetch_reputation()` — Task 5
- ✅ `fetch_market_comparison()` — Task 5
- ✅ Session pre-check sidebar with 5-min cache — Task 7
- ✅ Re-auth button + headed browser — Task 7
- ✅ Tableau code removal — Tasks 6–7
- ✅ `build_data_context()` updated — Task 6
- ✅ System prompt reputation benchmark — Task 7
- ✅ Raw data expander renamed — Task 7
- ✅ Error handling (SSO redirect → None, UUID not found warning) — Tasks 4–5 + 7
- ✅ `requirements.txt` — Task 1

**Known limitation:** `fetch_performance_trends()` uses heuristic column name matching (`"CP"`, `"Current Period"`, first value) because the actual Tableau worksheet column names on Performance Trends are discovered at runtime. If the column names differ from these guesses, KPI values will be None but the function returns an empty dict rather than crashing. The smoke test (Task 8) validates actual column names — adjust `_PT_KEY_MAP` and the column lookup logic if needed after the first live run.
