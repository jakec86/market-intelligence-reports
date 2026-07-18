---
name: Tableau LEI Filter Automation
description: LEI-Local v2 Tableau filters — confirmed working Playwright flow via portal URL + Dealer Name filter; no DMA filter needed for Nalley; pb_report.py handles import/sort/email
type: feedback
originSessionId: 03d05f28-537c-427b-8ddd-843e4a0e41e1
---
**Confirmed working Playwright flow for Nalley LEI (2026-05-08):**

Use the **full Tableau Cloud portal URL** (not the workbook list or embed URL):
```
https://us-west-2b.online.tableau.com/#/site/cars/views/LowEngagedInventoryReport/LEI-Localv2
```

**DMA filter is NOT needed** — skip it entirely. Go straight to the Dealer Name filter. The portal URL gives access to all dealers including Nalley (unlike the `?:embed=y` iframe URL which showed "No matches" for Nalley searches).

**Dealer Name filter sequence that works:**
1. Click `Filter Dealer Name and ID Inclusive` combobox
2. Search for `Nalley Lexus Galleria` → "Found 1 matches"
3. If all dealers are checked (All state): click the **inner `<input>` checkbox** inside the `(All)` row to deselect all — clicking the outer label row doesn't reliably toggle
4. Search again, check `Nalley Lexus Galleria - 109754`
5. Clear search box (fill space + Backspace) — Apply button is **disabled while search text is present**
6. Click **Apply**
7. Wait ~15–30s for recompute (tab-glass overlay disappears)

**vf_ URL params do NOT work** — `?vf_Dealer%20Name%20and%20ID=Nalley%20Lexus%20Galleria%20-%20109754` appears in URL but filter is not applied in the UI. Must use the interactive filter.

**Download flow:**
Download → Crosstab → `Low Engaged Inventory Report - Local v2` (pre-selected) → CSV → Download
File: `~/.playwright-mcp/Low-Engaged-Inventory-Report---Local-v2.csv`

**Stock type: leave as "Used"** — correct for this report, no change needed.

**Tableau MCP is blocked (RLS):** The PAT returns 401 for LEI view. Do NOT try MCP — Playwright only.

---

**pb_report.py handles all sheet work (confirmed 2026-05-08):**
```bash
python3 ~/Documents/scripts/pb_report.py --dealer nalley \
  --lei ~/.playwright-mcp/Low-Engaged-Inventory-Report---Local-v2.csv \
  --dem ~/.playwright-mcp/Pricing.csv
```
Does: import both CSVs → 4-pass PBT sort → read stats → hide Data Import tab → create Gmail draft. No manual sheet manipulation needed.

**admin.cars.com Price Comparison — Playwright download works cleanly:**
Direct URL → click Price Comparison tab → Download Crosstab → Pricing sheet (pre-selected) → CSV → Download.
File: `~/.playwright-mcp/Pricing.csv`. Schema: `YMMT | Stock num | Stock type | Days live | Price | Price vs Market (%) | Value`
