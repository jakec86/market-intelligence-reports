---
name: reference_dealer_site_scrape
description: "How to scrape a dealer's own-website used inventory (Akamai-protected, dealer.com/DDC) + chrome-devtools MCP orphan recovery"
metadata: 
  node_type: memory
  type: reference
  originSessionId: f837ad02-f48d-4c65-88ef-5f45397a6b5c
---

Scraping a dealer's OWN website inventory (e.g. for dark-prospect analysis like [[project-park-place-prospect]]):

**Dealer.com (DDC) sites are Akamai Bot Manager protected.** Plain `curl`/WebFetch/Firecrawl-CLI get a 403 `BOT-BROWSER-IMPERSONATOR`. No Firecrawl/Brightdata CLI or API key is configured on this machine anyway. → **Must use a real fingerprinted Google Chrome via the chrome-devtools MCP** (its real-Chrome profile clears Akamai; Playwright's bundled Chromium often won't).

**Scrape recipe (verified 2026-06-12 on mercedesdallas.com):**
1. `new_page` to the used-inventory URL (e.g. `https://www.mercedesdallas.com/used-inventory/index.htm`).
2. Vehicle data lives in `window.DDC.dataLayer.vehicles` — 24 objects/page. Fields: `vin, year, make, model, trim, bodyStyle, odometer (mileage), internetPrice/askingPrice/salePrice, certified (CPO), newOrUsed, stockNumber, exteriorColor, accountId`. `accountId` (e.g. `parkplacemotorcarsdallasmb`) gives per-store attribution.
3. Paginate via URL `?start=N` (step 24). OR — faster — same-origin `fetch()` the JSON widget endpoint `/apis/widget/INVENTORY_LISTING_DEFAULT_AUTO_USED:inventory-data-bus1/getInventory?start=N&count=50` (returns `{inventory:[...]}`; price in `pricing.dprice` find `isFinalPrice`; mileage/trim in `attributes[]` by name regex). Page size is inconsistent — paginate by `start += inv.length`, dedup by VIN, stop on empty. One async fetch-loop in a single `evaluate_script` (use `filePath` to save) pulls the whole feed in one call.
4. Strip `Â®`/`®` from model strings; parse prices/mileage with `replace(/[^0-9.]/g,'')`.

**GOTCHA 1 — pooled group feed:** Park Place runs ONE unified inventory feed surfaced on every store's site (mercedesdallas.com, mercedesfortworth.com, parkplacemotorcarsarlington.com all return the same ~827-vehicle group pool incl. Lexus/Acura/Volvo/JLR). Per-store attribution is the `account` field, NOT the domain. Scrape ANY one site, then filter by account (e.g. `test("motorcars.*mb$")`). Verified 2026-06-12: 3 MB stores = 313 used (Dallas `parkplacemotorcarsdallasmb` 155, Fort Worth 104, Arlington 54). See [[project-park-place-prospect]].

**GOTCHA 2 — mixed-make lot:** even within one MB store, ~28% of used is trade-ins of other makes (MB stores: 226/313 = 72% Mercedes). The demand crosstab must cover all makes on the lot, or classify only the target-make subset and show trades separately.

**chrome-devtools MCP orphan recovery:** if tools error "browser is already running for .../chrome-devtools-mcp/chrome-profile", a stale Chrome holds the MCP's dedicated profile. Fix: `kill` the Chrome PIDs whose command line contains `chrome-devtools-mcp/chrome-profile` (NOT your main Chrome on the default profile, NOT the parent `chrome-devtools-mcp` node server). The node server respawns a clean Chrome on the next tool call. Session restart alone does NOT fix it — the orphan keeps the profile locked. Distinct from [[reference_port3000_fix]] (Gmail MCP).
