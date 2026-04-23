# Dealer Health Dashboard — admin.cars.com Playwright Integration

**Date:** 2026-04-23  
**Status:** Approved  
**File:** `~/Documents/scripts/dealer_health.py`  
**New module:** `~/Documents/scripts/admin_cars.py`

---

## Background

The Dealer Health Dashboard (`dealer_health.py`) currently pulls account data from Salesforce (working) and health metrics from Tableau via REST API (blocked by row-level security — never returns useful per-dealer data). This design replaces the Tableau source with a Playwright-based scraper targeting admin.cars.com Performance Trends, Reputation Health, and Demand Signals/Market Comparison pages.

The Playwright `tableau-viz` Web Component JS API pattern was proven in the PB report workflow on 2026-04-23 — same JumpCloud SSO session, same embed pattern.

---

## Architecture

### New module: `admin_cars.py`

All browser logic isolated here. No Streamlit imports. Functions return plain dicts or `None`.

**Persistent browser context:** `~/.dealer_health_browser/`  
Separate from the PB report's `~/.playwright-mcp/` directory (managed by the MCP server). Headless by default; headed only during re-auth.

#### Public API

```python
check_session() -> bool
    # Navigate to admin.cars.com, return True if no SSO redirect

resolve_uuid(ccid: str) -> str | None
    # GET /dealers/all/reports?query={ccid}
    # Regex-extract UUID from HTML: dealers/([a-f0-9-]{36})/reports
    # Return UUID string or None

fetch_performance_trends(uuid: str) -> dict
    # Navigate to /dealers/{uuid}/reports/performance_trends
    # Read tableau-viz workbook.activeSheet.worksheets via JS API
    # Return flat dict: avg_inventory_cp/pp/delta, under_merch_cp/pp/delta,
    #   vdps_cp/pp/delta, connections_cp/pp/delta,
    #   fair_badges_cp/pp/delta, above_badges_cp/pp/delta,
    #   cpv (if present), cpc (if present)

fetch_reputation(uuid: str) -> dict
    # Navigate to /dealers/{uuid}/reports/reputation_health
    # Return: rating, review_count, trend

fetch_market_comparison(uuid: str) -> dict | None
    # Navigate to /dealers/{uuid}/reports/demand_signals
    # activateSheetAsync('Price Comparison') → read Pricing worksheet
    # Return: above_pct, at_pct, under_pct
    # Return None gracefully if data shape unexpected
```

All functions: individual try/except, failure returns `None`, never blocks other fetches.

### Updated: `dealer_health.py`

- Remove all Tableau auth/fetch code (`tableau_sign_in`, `fetch_health_metrics`, `pivot_health_metrics`, Tableau config constants)
- Import `admin_cars`
- Add session pre-check (cached 5 min) to sidebar
- Replace Tableau checkbox with "admin.cars.com — Performance Trends" checkbox
- Update `build_data_context()` with three new sections
- Rename raw data expander

---

## Session Pre-Check & Re-Auth Flow

On app load, sidebar runs `admin_cars.check_session()` (cached `ttl=300`):

- **Green ✓ admin.cars.com connected** — proceed normally
- **Red ✗ Session expired** — show "Re-authenticate" button

Re-auth button:
1. Launches **headed** (visible) Chromium using persistent profile
2. Navigates to admin.cars.com
3. Waits up to 60s for JumpCloud push approval
4. On success: clears cache, flips indicator green
5. On timeout: shows error message

Mid-analysis SSO redirect: caught by each fetch function, returns `None` + warning rather than crashing.

---

## Data Extraction

All three report pages use the `tableau-viz` custom element. Data is read via JavaScript — no CSV downloads.

### Performance Trends
- Worksheets accessed via `workbook.activeSheet.worksheets`
- Target KPIs: Avg Inventory, Under-Merchandised %, VDPs (7-day), Connections, Fair badges, Above Average badges
- Each KPI: CP value, PP value, MoM % delta
- CPV / CPC: extracted if present as KPI tiles; skipped gracefully if not

### Reputation Health
- Overall rating (float), review count (int), recent trend (+/- float)

### Market Comparison (Demand Signals → Price Comparison tab)
- `workbook.activateSheetAsync('Price Comparison')` → read Pricing worksheet
- Extract: above_pct, at_pct, under_pct
- Returns `None` if data shape differs from expected

### Execution order in `dealer_health.py`
1. `resolve_uuid(ccid)` — from CCID returned by Salesforce
2. `fetch_performance_trends(uuid)`
3. `fetch_reputation(uuid)`
4. `fetch_market_comparison(uuid)` — runs last, most likely to vary

---

## UI Changes

### Sidebar
```
[●] admin.cars.com connected        ← green dot, cached 5 min
  [Re-authenticate]                 ← only shown when session dead

☑ Salesforce
☑ admin.cars.com — Performance Trends
```

### Main Panel
Status columns show per-source results:
- "Performance Trends: ✓ 12 metrics"
- "Reputation: ✓ 4.6★"  
- "Market Comparison: ✓ / skipped"

### `build_data_context()` new sections
```
## Performance Trends (admin.cars.com)
- Avg Inventory: 142 CP / 138 PP / +3% MoM
- VDPs: 2,450 CP / 2,100 PP / +17% MoM
...

## Reputation Health
- Rating: 4.6 (312 reviews, +0.2 trend)

## Market Comparison
- Above Market: 28% | At Market: 71% | Under Market: 2%
```

### System prompt additions
Add to KPI benchmarks:
- CPV / CPC: no fixed benchmark in the prompt — if present in data, Claude surfaces the values and flags whether they look high/low based on context (product tier, market size). Benchmarks can be added to the prompt later once targets are established.
- Reputation: 4.5+ rating, 50+ reviews/month considered healthy

### Raw data expander
"Raw Tableau — Health Metrics" → "Raw admin.cars.com Data"  
Shows structured dicts from all three fetch functions.

---

## Error Handling

| Scenario | Behavior |
|---|---|
| Session expired on load | Sidebar shows red warning + re-auth button; analysis disabled |
| Session expires mid-run | Fetch returns `None`; warning shown; other sources still run |
| UUID not found | Warning: "Dealer not found on admin.cars.com"; analysis runs on SF data only |
| Performance Trends timeout | Returns `None`; noted in Claude's Data Gaps section |
| Market Comparison shape mismatch | Returns `None` silently; not shown in UI |

---

## Dependencies

```bash
pip install playwright
playwright install chromium
```

Added to `~/Documents/scripts/requirements.txt` (or equivalent).

---

## Out of Scope

- Automating JumpCloud TOTP (pending IT reset of Authenticator App enrollment)
- Caching fetched metrics between runs
- Multi-dealer batch mode
- Demand Signals Main Report tab (separate from Market Comparison)
