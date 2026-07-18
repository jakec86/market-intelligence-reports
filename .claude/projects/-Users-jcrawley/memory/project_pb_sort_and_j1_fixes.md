---
name: project_pb_sort_and_j1_fixes
description: "Hendrick sort_specs config fix (green-first+SAM); Nalley J1 excludes $0; lesson—don't hand re-run import/sort on a finalized live PB sheet"
metadata: 
  node_type: memory
  type: project
  originSessionId: 44b4867b-9d56-4ab9-8a9d-c6197363644e
---

**Hendrick sort config fix (2026-06-22):** `pb_dealers.py` → `DEALERS["hendrick"]["pbt_filter"]["sort_specs"]` had **Stock# (dimensionIndex 3) as the PRIMARY key**, so every automated run output Stock#-order and Jake had to manually re-sort to green-first + SAM A-Z each week (the "sorting update" pending since 6/15). Fixed to `[{dim9 DESC, green bg}, {dim0 ASC}]` = green-first (primary, via the col-J conditional-format color) + SAM A-Z (secondary). Stock#-primary key dropped. Verified the [green DESC, SAM ASC] basicFilter reproduces green-first + SAM A-Z (Abby Livingston on top).

**Nalley J1 fix (2026-06-22):** the J1 % formula used `">=0"`, which counted the $0.00 price-change vehicles in the numerator (19/67 = 28%) while the email quoted "13 vehicles" (excl. $0). Per Jake, **$0.00 price changes are NOT part of the J1 percentage** → changed live-sheet J1 to `">0"` (`=COUNTIFS(J4:J9998,">0",J4:J9998,"<="&E1)/COUNTA(D4:D9998)`) → 13/67 = 19%. `import_to_sheet` never writes J1, so the fix persists across runs. Apply the same `">0"` convention to any other PB dealer J1 if Jake wants consistency.

**LESSON — do NOT hand re-run `safe_sort_pbt`/`import_to_sheet` on a PB sheet Jake has already finalized.** On 2026-06-22 I re-ran the sort on an already-correctly-sorted Hendrick sheet: (1) `safe_sort_pbt` Pass 1 computes extent from the whole D column, so it sorted ~1,003 **stale rows beyond row 9999** (old larger import) INTO the live data; (2) a follow-up full re-import churned the 4,593-row VLOOKUP recalc and left my reads mutually inconsistent (D non-empty read as 4593 / 3592 / 168 on successive calls); numbers diverged from the approved email (165 vs 214 within $500). If a finalized sheet looks right on first read, STOP — trust it. To recover a destabilized live sheet, use Google Sheets **Version history** (File ▸ Version history ▸ restore the approved snapshot) — fast and exact — NOT more hand-edits. A fresh full `/hendricks-pb-report` run is the alternative (rebuilds clean + self-consistent email).

Related: [[feedback_pb_sort_safety]], [[feedback_hendrick_filter]], [[feedback_pb_formulas]], [[feedback_nalley_pbt_filter]], [[project_pb_pending_enhancements]].
