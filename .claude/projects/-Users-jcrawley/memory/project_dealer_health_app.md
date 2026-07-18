---
name: dealer-health-app-progress
description: Dealer Health Dashboard Streamlit app — architecture decisions, data source findings, and current state of implementation
type: project
originSessionId: d06823ff-f6a5-435e-b515-6079468439c7
---
# Dealer Health Dashboard — Implementation Progress

**Goal:** Self-serve Streamlit app where a colleague enters a dealer name and gets a health snapshot using the Dealer Growth Triangle framework.

**File:** `~/Documents/scripts/dealer_health.py` (created, needs Tableau data source update)

## Architecture (Confirmed Working)

### Data Sources

1. **Salesforce CLI** (`sf data query`) — WORKS
   - Fields: Name, CCID__c, Type, OEM__c, Account_Status__c, DI_Package__c, BillingCity, BillingState, Product_Amount__c, etc.
   - CCID__c is the key field linking SF to admin.cars.com and Tableau

2. **admin.cars.com** (via Chrome DevTools Protocol) — WORKS, needs automation
   - Auth: JumpCloud SSO (manual login required, session persists)
   - Search: `GET /dealers/all/reports?query={dealer_name_or_ccid}` → HTML response containing UUID
   - UUID extraction: regex `dealers/([a-f0-9-]{36})/reports` from HTML
   - Reports URL: `https://admin.cars.com/dealers/{UUID}/reports/performance_trends`
   - Example: Nalley Lexus Galleria → UUID `156f9bb7-3c44-549c-b16b-0c3af73fdb1f`, Dealer Id `12070`, CCID `109754`
   - **Performance Trends** page has: Avg Inventory, Under-Merchandised %, Connections, VDPs, Fair/Above Badges — all with MoM % changes
   - Data is in an embedded Tableau iframe from `reports.cars.com` (separate Tableau server)
   - Has "Download Crosstab" button for CSV export
   - Other available reports: Demand Signals, Reputation Health, Listings Optimizer, Sales Attribution, DMV Market Share, Connections & Contact Details, Walk-in Demand, Vehicle Demand, ROI One Sheeter

3. **Claude API** (claude-sonnet-4-6) — WORKS
   - Streaming via `client.messages.stream()`
   - System prompt with Dealer Growth Triangle framework from `/auto-research` skill

### What Didn't Work (Dead Ends)

- **Tableau REST API view export** — "By Store Table for Export" view is locked to one AE's dealers via row-level security. Even with jcrawley's PAT, only returns 32 Cochran dealers. View filters via `vf_` URL params are ignored.
- **Tableau VizQL Data Service** (`query-datasource`) — jcrawley's account lacks `VIZQL_DATA_API_ACCESS` permission on the "Cars Dealer Activity 13Mo Detail" datasource (LUID: `943e324b-9fe6-4f0d-b008-37933fc73615`).
- **Tableau At Risk Score views** — Work via REST API (9,429+ dealers) but use different dealer names than Salesforce (e.g., "Nalley GMC (148073)" ≠ "Nalley Lexus Galleria"). These are different rooftops, NOT the same store.
- **Tableau dashboard filter automation** — Filters cascade (Sales Director → Regional Sales Mgr → AE → Major Cust → Dealer Name). The PAT user's row-level security restricts to Arthur Carina's book regardless of filter changes.

### Tableau PAT Status

- **"Claude" PAT** — has limited row-level security (Arthur Carina's dealers only)
- **"DealerHealth" PAT** (jcrawley's) — created 2026-04-06, expires same day. Secret: `4luoWSfAQvWLwr4j0UGxfw==:eo6oya1xBRZ9wkqLakOwfHItsPZhJapH`. Has broader datasource access but same view-level restrictions. Settings.json updated to use this PAT.
- **Why:** Both PATs are subject to the same row-level security on the "Monthly Marketplace Dealer Health Metrics" workbook views.

## Next Steps (updated 2026-04-23)

**Approach change:** Use `playwright` Python library instead of CDP scraper. Playwright is proven on admin.cars.com from the PB report workflow — same JumpCloud SSO session, same `tableau-viz` Web Component JS API pattern.

**Plan for next dev session:**
1. `pip install playwright` + `playwright install chromium` in the scripts env
2. In `dealer_health.py`: add a `fetch_performance_trends(uuid)` function that:
   - Launches Playwright with a persistent browser context (to reuse JumpCloud SSO session)
   - Navigates to `admin.cars.com/dealers/{UUID}/reports/performance_trends`
   - Uses `tableau-viz` JS API to access worksheet data (same pattern as Demand Signals today)
   - Extracts: Avg Inventory, Under-Merchandised %, VDPs, Connections, Fair/Above Badges + MoM % changes
3. Feed extracted metrics into Claude streaming analysis alongside existing SF data
4. Display in Streamlit sidebar/main panel

**Key insight from PB workflow (2026-04-23):** The `tableau-viz` custom element on admin.cars.com exposes `workbook.activeSheet.worksheets` — can read KPI values directly via JS without downloading CSVs. Performance Trends uses same embed pattern as Demand Signals.
