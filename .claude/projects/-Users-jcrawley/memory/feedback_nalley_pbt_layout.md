---
name: Nalley PBT Correct Layout
description: Exact layout of the Nalley Lexus Galleria Price Badge Tool tab — row structure, colors, formulas
type: feedback
originSessionId: 5e89c129-f77f-4999-ae43-9da2b2dff386
---
Correct layout of the Price Badge Tool tab (Nalley Lexus Galleria sheet):

**Row 1:** Merged A1:D1 (EMPTY — no "Threshold" text), E1 = $1,000 (green fill), J1 = percentage formula `=COUNTIFS(J4:J998,">=0",J4:J998,"<="&E1)/COUNTA(D4:D9998)`
**Row 2:** Empty spacer row
**Row 3:** Column headers — dark teal/cyan background, white bold text, filter dropdown arrows. Headers: MMYT (B), VIN (C), Stock # (D), Days Live (E), # Photos (F), Your Price (G), Current Badge (H), Next Badge (I), Difference to Next Badge (J), Updated Price (K), PTM % (L). Column A is hidden (always "Nalley Lexus Galleria").
**Row 4+:** Data rows with formulas referencing Data Import tabs

**Why:** During a previous session I incorrectly added "Threshold (less than or equal to)" text and used purple/dark-cornflower-blue header colors. The Nalley sheet is different from Hendrick — no threshold label, different header color (teal not purple), column K is "Updated Price" not "Target Price".

**How to apply:** When rebuilding or QC'ing the PBT tab, match this exact layout. Do NOT copy Hendrick's formatting 1:1 — the two sheets have different structures.
