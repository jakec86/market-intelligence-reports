---
name: nalley-pbt-filter-corruption
description: Nalley PBT basic filter corrupts the J-sort; clear+re-add clean after pb_report.py
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 63520f4a-e531-4281-bc57-6ab9a787114c
---

On 2026-06-12 the Nalley PBT (`Price Badge Tool` tab, sheet `13Jn8vJSG7vRYW9xpuxrMi9kXNhiV_TaCrjQ5lNQRPP8`) had a **corrupted basicFilter**: sortSpec was `dimensionIndex 9 (col J) DESCENDING` with a `backgroundColor {green:1}` — the same corruption signature as Hendrick (see [[hendrick-pbt-filter]]). This overrode `pb_report.py`'s "sort A4:L60 by J ascending" so the **physical row order was scrambled** (first ~3 data rows out of place) even though the script reported success.

**Why:** A basicFilter with its own sortSpec governs row order; the script's sortRange does not hold while the corrupted descending/backgroundColor spec is present.

**How to apply:** After running `pb_report.py --dealer nalley`, QC the sort by reading `J4:J60` UNFORMATTED and checking ascending. The 57 rows = 39 numeric J (need next badge) + 18 blank J ("already Great" → bottom). If not ascending, fix with gspread `batch_update` (token `~/.claude/tokens/sheets_token.json`, sheetId 565895707):
1. `clearBasicFilter`
2. `sortRange` rows 3–60 (0-idx), cols 0–12, sortSpec `dimensionIndex 9 ASCENDING`
3. re-add clean `setBasicFilter`: range startRow2/endRow59/startCol1/endCol12, sortSpecs `[{dimensionIndex:9, sortOrder:ASCENDING}]`, filterSpecs `[{columnIndex:9, filterCriteria:{hiddenValues:["$0.00"]}}]` — **no backgroundColor**.

Col K formulas (`=G-J`, "Updated Price") and the CF-based green must stay untouched — CF handles green, not the filter sortSpec. Consider patching `pb_report.py` to clearBasicFilter before its Pass-2 sort so this stops recurring. Related: [[nalley-pbt-layout]], [[nalley-pb-postrun]], [[pb-formulas-do-not-touch]].
