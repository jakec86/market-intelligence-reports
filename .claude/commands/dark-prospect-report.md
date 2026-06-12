# Dark-Prospect Inventory Performance Report — `/dark-prospect-report`

Show a **dark prospect** (a dealer not currently on Cars.com) how their *current used inventory* would perform on the marketplace — plotted onto the admin.cars.com Demand Signals "Churners" quadrant and projected to monthly VDPs / connections / leads / incremental gross. A non-price reason to come (back) on.

**Engine:** `~/Documents/scripts/dark_prospect_report.py` (config-driven). **Outputs:** a full HTML report + a deck-styled pitch slide in `~/Documents/Reports/<Group>/`.
**Worked example:** Park Place Mercedes-Benz (Dallas/Fort Worth/Arlington), DFW — see [[park-place-prospect]].

**Required input:** prospect group name + its store CCIDs/UUIDs, the DMA, and an **active comparable store** in the same DMA/brand (ask if not provided).

---

## Data sources

| Input | Source | Notes |
|---|---|---|
| Prospect used inventory | The prospect's **own dealer website** | Akamai-protected → scrape via chrome-devtools real Chrome (not curl/Firecrawl). See [[reference_dealer_site_scrape]]. |
| Demand quadrant axes | admin.cars.com **Demand Signals → Market Comparison** crosstab (CSV) | Per make/model: Market vehicles + Market VDPs (+ connections). Full 4-quadrant via median splits. |
| Broad churner classification | admin.cars.com **Demand Quadrants** crosstab (CSV) | All-make; classifies trade-in nameplates the Market Comparison misses. Export with the quadrant filter cleared for all 4 quadrants. |
| Comparable per-vehicle rates | admin.cars.com **Performance Trends KPIs** (Avg Inventory, VDPs, Connections) | Monthly. Pull from the active comparable store. |
| Market supply / comparable mix (optional) | `cars-mcp` `carscom_search_listings` | No auth; identifies the comparable by dealer name; market supply proxy. |

> **Used is the focus** — used is performance-driven. Inventory is used-only (incl. CPO); filter all market data to Used (exclude New).

---

## Critical gotchas (read before running)

1. **Akamai bot protection** on dealer.com/DDC sites → plain HTTP is 403'd. Scrape only via the **chrome-devtools MCP real Chrome**.
2. **Pooled group feed** — many dealer groups (incl. Park Place) serve ONE inventory feed on every store site. Scrape any one site, then **filter by the `account` field**, not the domain.
3. **Mixed-make lots** — a franchise store's used lot is ~30% other-make trade-ins. The Demand Quadrants file classifies most of these; the rest project at the base rate (shown as "Unmatched / Trade").
4. **Comparable inventory KPI scope** — a Performance Trends "Avg Inventory" KPI may include all stock types, not used-only, making that leg's per-vehicle rate conservative. The blend de-weights it; flag it on the report.
5. **Honesty guardrail** — quadrant multipliers are normalized so the inventory-weighted mean = 1.0. Reclassifying toward Churner only *redistributes* the projection; it can never inflate the total.

---

## Workflow

### Step 1 — Identify the prospect + comparable
- Per store: name, CCID, admin UUID (`/dealers/all/reports?query={name|CCID}`), DMA. Salesforce for status/products.
- Pick one **active comparable** (same DMA + brand) whose admin.cars reports you can view.

### Step 2 — Scrape the prospect's used inventory (chrome-devtools)
- `new_page` to the store's used-inventory URL (e.g. `https://www.{site}.com/used-inventory/index.htm`) — real Chrome clears Akamai.
- In-browser `fetch()` the DDC widget, paginating by returned offset, dedup by VIN:
  `/apis/widget/INVENTORY_LISTING_DEFAULT_AUTO_USED:inventory-data-bus1/getInventory?start=N&count=50`
  Fields: vin, year, make, model, bodyStyle, odometer (mileage), `pricing.dprice` (isFinalPrice), certified, stockNumber, **accountId**. (`attributes[]` holds mileage/trim.)
- Save to `~/Documents/Reports/<Group>/inventory/<group>_MB_stores_<date>.json`, filtered to the prospect's store accounts. Treat a `$225`-only price (doc fee, "call for price") as null.

### Step 3 — Pull admin.cars data (from the comparable / an accessible active store)
- **Demand Signals → Download Crosstab → Market Comparison** (Stock type **Used**, Market Inventory, latest month) → CSV.
- **Demand Quadrants** crosstab (all-make; clear the quadrant filter) → CSV.
- **Performance Trends** KPIs: Avg Inventory, VDPs, Connections (Leads optional) → CSV.
- Save all to `~/Documents/Tableau/`. Crosstabs are UTF-16, tab-delimited — the script's loader handles both.

### Step 4 — Configure the engine
Edit the `CONFIG` block in `dark_prospect_report.py` (or copy it per prospect): inventory JSON, the three CSV paths, `primary_make`, the three benchmark `legs` (self prior-Cars.com history + comparable monthly KPIs + DMA market), `weights`, `quad_mult`, `revenue` assumptions, output paths.

### Step 5 — Run
```bash
python3 ~/Documents/scripts/dark_prospect_report.py
```
Writes the full HTML report **and** the deck-styled pitch slide; prints the quadrant mix, blended base rates, and projected totals.

### Step 6 — Verify & deliver
- Open and eyeball: `! open "<report>.html"` and the `_SLIDE_` file.
- **Sanity check:** projected connections should track the prospect's own prior Cars.com actuals.
- Pitch slide drops into the group deck (`park_place_pitch_v2.html` style).
- If emailing: **draft to `jcrawley@cars.com` first** (pre-send rule) before any client send.

---

## Methodology (what the report shows)
- **Quadrant:** median splits on Market vehicles (supply) × Market VDPs (demand) → Churner / Niche / Lot Sitter / Rarity. Demand Quadrants fills in trade-in nameplates.
- **Blended per-vehicle monthly rates:** weighted blend of (a) prospect's own prior Cars.com history, (b) active comparable, (c) DMA market — weights shown on the report; missing legs renormalize.
- **Projection:** base rate × normalized quadrant multiplier, summed over inventory → VDPs/connections; leads = connections × lead-share.
- **Revenue (winback = net-new):** connections × close rate × GPU, shown as a low/mid/high range.
- Every assumption, source, and the matched/unmatched count print on the report.
