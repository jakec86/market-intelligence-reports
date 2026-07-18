---
name: reference_admin_cars_tableau_embed_extract
description: "Pull data from admin.cars.com embedded Tableau reports via the Embedding API — no PAT, no CSV download"
metadata: 
  node_type: memory
  type: reference
  originSessionId: 36c675f4-0a55-4be7-b180-73d5817eb7f2
---

admin.cars.com report pages (Market Opportunities, Performance Trends, etc.) embed a Tableau viz from reports.cars.com using the **Tableau Embedding API v3** (`<tableau-viz>` element; the page's "Export" link has `data-handler="viz-export"`). You can read the underlying data **directly as JSON** from an authenticated session via `chrome-devtools` `evaluate_script` on the **top page** (the API objects are reachable from the parent even though the viz is a cross-origin iframe, because it talks via postMessage).

This **sidesteps both the Tableau PAT (which dies after ~15 days inactivity → 401001) and RLS**, and avoids fragile CSV-download interception.

Pattern:
```js
const viz = document.querySelector('tableau-viz');
const wb = viz.workbook;
await wb.activateSheetAsync('Store Performance');      // switch dashboard tab
await new Promise(r=>setTimeout(r,4000));              // let it render
const ws = wb.activeSheet.worksheets.find(w=>w.name==='By Store');
const dt = await ws.getSummaryDataAsync({maxRows:40000, ignoreSelection:true});
// dt.columns[].fieldName ; dt.data[][].value (native; null shows as "%null%") / .formattedValue
```
- `wb.publishedSheetsInfo` lists dashboard tabs; `activeSheet.worksheets` lists the worksheets on the current tab. Per-store data is usually a worksheet named `By Store` (long format: MONTH(Begin Date), Customer Name, Legacy Id, Measure Names, Measure Values) — pivot in Python.
- Use `evaluate_script`'s `filePath` arg to dump large results straight to disk (e.g. `~/Documents/Tableau/*.json`) instead of returning inline.
- Filters: `ws.getFiltersAsync()` / `ws.applyFilterAsync()`. Pulling all months unfiltered then slicing in code is simplest.
- chrome-devtools runs its own Chrome instance; navigating to an admin.cars.com URL worked already-authenticated in this env (no JumpCloud prompt). See [[reference_login_flows]], [[project_aca_mae_proposal]].

**Reports with no date-range control (2026-07-17):** Connections & Contact Details
(`Connections13MoSummary` workbook) has fixed KPI windows (13mo/MTD/7-day/prev-month)
and no "Custom" date picker at all. Its `exportdetails` worksheet is the workaround —
a per-lead detail table with a real `Submitted Date/Time` field (format confirmed:
`"2026-07-09 11:46:01"`, trivially parseable), alongside PII columns (Name/Email/
phone/etc.) that must be filtered out in the same `evaluate()`/`page.evaluate()` call
before any data crosses back to the caller — never let PII reach Python. Pull unfiltered
(`maxRows: 20000`), bucket into whatever custom range you need client-side. The
`tableau-viz` element can take several seconds to finish rendering after page load —
poll for `wb.activeSheet.worksheets.length` truthy in a retry loop (~1s intervals, ~20
attempts) rather than a fixed sleep. Full working extraction code:
`~/Documents/scripts/market_metrics_shared.py` (`EXTRACT_TIMESTAMPS_JS`). See
[[project_market_metrics_weekly]].
