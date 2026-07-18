---
name: Market Intelligence — Client-Facing Improvements
description: User-requested improvements for polished dealer-facing market intelligence deliverables — auto-index, combined ZIP/city tab, interactive map link, configurable options
type: feedback
---

## Auto-generate GitHub index.html
Never manually update index.html — it should auto-discover report .html files and rebuild the index page.

**Why:** Manually adding report cards to index.html was missed during the Honda report push, breaking the link for the user.

**How to apply:** Build a `build_index.py` script that globs `*/market_intelligence_*.html`, parses DMA/make/date from filenames, and regenerates index.html. Call it at the end of `generate_market_report.py` and in the GitHub Actions workflow.

## Google Sheet should have combined ZIP+City summary tab
In addition to the raw ZIP-level data tab, add a second tab that aggregates ZIPs by city — showing city name, state, constituent ZIPs, total searches, and whether any hitlist ZIPs fall in that city.

**Why:** The interactive map report aggregates to city level, but the QC sheet only shows ZIP level. A city summary tab bridges the two views and is easier for dealers to scan.

**How to apply:** When creating QC sheets, add a "City Summary" tab alongside "ZIP QC".

## Link interactive map from Google Sheet
Include a hyperlinked reference to the GitHub Pages interactive map report directly in the Google Sheet (e.g., in a header row or a dedicated "Links" section).

**Why:** The sheet and map are companion deliverables — the sheet has the data, the map has the visual. They should cross-reference each other.

**How to apply:** Add the GitHub Pages URL in cell H1 or a dedicated row above the data.
