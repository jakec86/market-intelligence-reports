---
name: Nalley LEI Tableau Filter Sequence
description: Exact cascade order and values to filter the LEI - Local v2 view to Nalley Lexus Galleria
type: reference
originSessionId: d06823ff-f6a5-435e-b515-6079468439c7
---
Apply filters in this exact cascade order (each selection unlocks the next dropdown):

1. **DMA** = `Atlanta`
2. **Maj dealer name** = `Asbury`
3. **Grp dealer name** = `Asbury - Nalley`
4. **Dealer Name and ID** = `Nalley Lexus Galleria - 109754`
5. **Stock type** = `(All)` (clear the default "Used" filter)

**Why:** The filters cascade — selecting DMA first populates Maj dealer, which populates Grp dealer, which populates Dealer. Selecting the dealer before DMA results in empty data because the cascade breaks.

**Key correction:** The Tableau dealer ID is `109754`, NOT `26880` (which is the CustomerUUID used in admin.cars.com). These are different ID systems.

**Download:** After filtering, use Download → Crosstab. File lands in `~/.playwright-mcp/` as `Low-Engaged-Inventory-Report---Local-v2.csv` (UTF-16, tab-separated). Copy to `~/Documents/Tableau/`.
