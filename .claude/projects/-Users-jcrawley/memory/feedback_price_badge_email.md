---
name: Price Badge Email Formatting Rules
description: Rules for formatting the weekly Price Badge Report email draft — hyperlink, body structure, spacing, data inclusion
type: feedback
originSessionId: d06823ff-f6a5-435e-b515-6079468439c7
---
1. Delete any blank rows (missing VIN or Stock #) from the Price Badge Tool tab before sending.
2. Sort column J (Difference to Next Badge) by green fill color (ascending, so green/small values are at top).
3. Hyperlink the Google Sheet link to the text "Price Badge Report" — do not paste raw URL.
4. Include brief price comparison info from the Demand Signals report (At Market %, Above Market %, Under Market %).
5. Email body order: price badge insight first, then price comparison info. When describing vehicles within range of a badge upgrade, say "Good or Great" (not just Great) — the next badge could be either.
6. Switch up the opening line and messaging each time — never repeat the same opening twice in a row.
7. Place a blank line between "Cheers," and "Jake".
8. Reference the date as "week ending M/D" (not "today" or just the date) — e.g. "updated for the week ending 4/23".

**Why:** User wants the email to feel polished, data-rich, and fresh each time. The raw URL looks sloppy; the price comparison context gives the dealer a fuller picture.

**How to apply:** Every time the nalley-pb-report (or any price badge report) workflow runs, apply these rules to the email draft step and the Google Sheet QC step.
