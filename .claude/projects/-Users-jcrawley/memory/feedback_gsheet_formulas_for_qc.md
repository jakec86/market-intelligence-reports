---
name: Google Sheet Formulas for QC
description: Always use live ARRAYFORMULA-based formulas for computed columns in Google Sheets, not hardcoded values — enables QC and spot-checking
type: feedback
originSessionId: dd12b762-f688-425a-aa65-f5d915d98341
---
Always write computed columns in Google Sheets as live ARRAYFORMULA formulas, not static values — even when the data is pre-calculated in Python.

**Why:** Jake wants to be able to QC and examine the logic directly in the sheet. Hardcoded values are a black box; formulas let him trace calculations, spot anomalies, and adjust thresholds (e.g., change the Share Index weighting or median cutoffs) without re-running scripts.

**How to apply:** For any analysis sheet with derived columns (indices, ratios, classifications, labels), write ARRAYFORMULA in row 2 of each computed column. Store any threshold/config values (medians, weights) in clearly labeled helper cells (e.g., column T/U with labels) so they're visible and editable. The raw source data columns can remain as values.
