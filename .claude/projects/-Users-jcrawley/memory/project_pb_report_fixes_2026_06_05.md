---
name: project-pb-report-fixes-2026-06-05
description: Technical fixes to pb_report.py and Hendrick PBT sheet from 6/5/26 session — critical for future runs
metadata: 
  node_type: memory
  type: project
  originSessionId: ca589fff-9f98-4381-a976-02db7636b893
---

Major bugs found and fixed in the Hendrick PB report on 6/5/26. These are now in pb_report.py but document them here so future debugging is faster.

**Why:** Production run sent 6+ emails to Anne (every --send debug re-run), showed 77% stat, broke filter display, and needed multiple sheet fixes.

**How to apply:** Run QC benchmark after every Hendrick run — within-$500 should be 5-13% (~237-370 vehicles). If stat is outside that range, something is broken.

---

## Bug 1 — Hendrick PBT J column has row-position formulas

**Root cause:** The PBT's J column (Difference to Next Badge) was built with row-position references (`=IF(I3="Good", ABS(DataImport!O4526), ...)`) that break whenever rows are sorted. After sorting, the references point to wrong/empty DataImport rows → `ABS("") = 0` → J = $0 for thousands of vehicles.

**Fix:** Copy the correct VLOOKUP formula from J3 to J4:J4997 using copyPaste with PASTE_FORMULA:
```python
svc.spreadsheets().batchUpdate(SID, body={'requests': [{'copyPaste': {
    'source': {'sheetId': pbt_id, 'startRowIndex': 2, 'endRowIndex': 3,
               'startColumnIndex': 9, 'endColumnIndex': 10},
    'destination': {'sheetId': pbt_id, 'startRowIndex': 3, 'endRowIndex': 4997,
                    'startColumnIndex': 9, 'endColumnIndex': 10},
    'pasteType': 'PASTE_FORMULA', 'pasteOrientation': 'NORMAL',
}}]}).execute()
```
**Correct J3 formula:** `=IFERROR(IF(I3="Good",ABS(VLOOKUP(D3,'Data Import_Inventory Report'!$C$2:$Q$10000,13,FALSE)),IF(I3="Great",ABS(VLOOKUP(D3,'Data Import_Inventory Report'!$C$2:$Q$10000,15,FALSE)),"")),"")`

**Detection:** Stats show "X% at $0" when most vehicles should show non-zero J. If at_zero > 1000, J formulas are broken.

---

## Bug 2 — sortRange API calls corrupt basicFilter hiddenByFilter state

**Root cause:** The Hendrick PBT has an active basicFilter with sortSpecs. Calling the sortRange API while a basicFilter is active corrupts the `hiddenByFilter` row metadata, hiding thousands of data rows.

**Fix:** `reset_pbt_filter()` in pb_report.py clears and re-adds the filter after every run. The `pbt_filter` config in the Hendrick dealer config defines the correct filter spec.

**Detection:** Sheet shows only 2-3 rows in the browser. Row metadata shows thousands of rows marked `hiddenByFilter: True`.

**Recovery:** Clear and re-add the basicFilter:
```python
svc.batchUpdate(SID, {'requests': [{'clearBasicFilter': {'sheetId': pbt_id}}]})
# Then re-add with: D ASC → SAM ASC → green-J DESC, filterSpecs: hide blank SAM
```

---

## Bug 3 — J1 formula included $0 vehicles (>=0 should be >0)

**Root cause:** `=COUNTIFS(J3:J9999,">=0",J3:J9999,"<="&E1)/COUNTA(D3:D9999)` counted vehicles already AT the threshold (J=0) → showed 77% instead of ~5%.

**Fix:** Changed to `">0"` to count only vehicles that actually need a price drop.

**Current formula in J1:** `=COUNTIFS(J3:J9999,">0",J3:J9999,"<="&E1)/COUNTA(D3:D9999)`

---

## Bug 4 — Nalley PBT columns B (MMYT), C (VIN) were swapped

**Root cause:** The anchor write hardcoded YMMT to col C. Nalley's MMYT is in col B, VIN in col C.

**Fix:** Added `pbt_vehicle_col` config field (Nalley=1=B, Hendrick=2=C) and `pbt_vin_col`/`lei_vin_idx` for Nalley to write actual VINs from LEI col 3 to col C.

---

## Bug 5 — Stale rows from prior larger runs polluted stats

**Root cause:** The clear operation used a fixed cap (5000) but previous runs had written to rows 11000+. Stale rows with old stock#s caused wrong J values and inflated counts.

**Fix:** Dynamic clear using `pbt_ws.col_values()` to find actual sheet extent before clearing. Also: clear to 6000 minimum.

---

## Bug 6 — Nalley CC (Shashank) leaked in pre-send mode (2026-06-08)

**Root cause:** `create_gmail_draft()` always added `email_cc` from config regardless of pre-send mode. When `email_to = jcrawley@cars.com` (Jake), the CC (Shashank) was still appended — so the review email went to Jake + Shashank, not Jake alone.

**Fix:** `create_gmail_draft()` now checks `is_presend` = (`email_final_to` is set AND `email_to` contains `jcrawley@cars.com`). CC is suppressed when in pre-send mode.

**Detection:** Email shows Cc: header with a client-adjacent contact even though it was routed to Jake for review.

---

## Bug 7 — Nalley Pass 2 sorted by col A (dealer name) instead of col J (2026-06-08)

**Root cause:** `safe_sort_pbt()` Pass 2 always sorted by column 1 (A) A-Z, which is the SAM column for Hendrick. For Nalley (single dealer, no SAM), col A is the dealer name — not useful. Green rows (within-$1,000) were not floated to the top.

**Fix:** `safe_sort_pbt()` now branches on `pbt_store_col`:
- `None` (Nalley): Pass 2 sorts by `sort_col` (J) ascending → green rows at top
- Non-None (Hendrick): Pass 2 sorts by col A (SAM) A-Z → basicFilter handles green-first within each SAM

**Detection:** Sheet rows not in J-ascending order; smallest-diff vehicles not at top.

---

## QC Benchmark — Hendrick

| Metric | Expected range | Red flag |
|---|---|---|
| Within $500 (J1 %) | 5-13% | < 3% or > 15% |
| Vehicle count | 237-370 vehicles | < 100 or > 500 |
| At $0 count | 0-10 | > 100 → J formula broken |
| Already Great | 350-500 | < 100 → data issue |
| Total rows | ~4695 | < 4000 or > 6000 → import issue |

Historical reference points:
- 4/17/26: 8%, 6/1/26: 237 (5%), 5/18/26: 247 (5%), 5/11/26: 274 (13%), 4/27/26: 327 (7%), 5/4/26: 370 (8%)
