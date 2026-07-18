---
name: Prospect Pipeline Tab Formatting
description: Formatting, filters, insights sidebar, and structure for the Prospect Pipeline (59) tab in Asbury Portfolio Google Sheet
type: project
---

Asbury Portfolio Sheet: `1uN92bRUVjAOqm8ncNbnyAP2cKtqtBkkiwhQaljh_eJ8`
Tab: "Prospect Pipeline (59)" (sheetId=3)

## Columns (A–K)
| Col | Header |
|-----|--------|
| A | Store |
| B | Parent Group |
| C | Est MRR |
| D | Focus |
| E | Description |
| F | State |
| G | DMA |
| H | Last MKP Date |
| I | Used Inv (Yipit) |
| J | POC Name |
| K | POC Email |

## Data
- 59 prospect stores + TOTAL row at row 63 (rows 61-62 blank)
- TOTAL row shows combined Est MRR ($138,624)
- Est MRR column formatted as currency (`$#,##0`)
- Sorted by Last MKP Date descending (most recent lapsed first)

## Insights Sidebar (Column M)
Jake added a "Quickhit List" summary sidebar in column M with borders and color-coded tiers:

### M1: Header
- "Quickhit List:" — purple dark bg, white bold Inter 10pt, center, solid medium borders (top/left/right)

### M2–M4: Tiered prospect segments (bordered box, gradient warm colors)
- **M2**: "6 Hot Targets: High demand and/or recently on (LHM & Asbury)" — peach bg (`rgb 0.976, 0.796, 0.612`), borders left/right
- **M3**: "23 Targets: DR active (Herb C.)" — light peach bg (`rgb 0.988, 0.898, 0.804`), borders left/right
- **M4**: "10 Dealers w/ the comp (LHM & Asbury)" — light yellow bg (`rgb 1.0, 0.949, 0.8`), borders left/right/bottom

### M6–M19: Revenue potential calculations
- **M6**: "49 Stores w/ estimated rev potential of -" (bold)
- **M7**: `=SUM(C2:C40)` — total MRR for top 39 stores (bold, left-aligned)
- **M9**: "Q3-4 Revenue potential:" (bold)
- **M10**: `=M7*6` — 6-month revenue projection (bold)
- **M12**: "75% attainment:" (italic)
- **M13**: `=M7*6*0.75` (italic)
- **M15**: "50% attainment:" (italic)
- **M16**: `=M7*6*0.5` (italic)
- **M18**: "25% attainment:" (italic)
- **M19**: `=M7*6*0.25` (italic)

## Filter
- Basic filter applied on A1:K61
- Default sort: column H (Last MKP Date) descending

## Formatting
- **Header row**: Cars Commerce purple dark bg (`#370B55` / rgb 0.216, 0.039, 0.329), white bold Inter 10pt, center-aligned, wrap text
- **Gridlines**: hidden (`hideGridlines: true`)
- **Frozen**: row 1 frozen
- **Banded rows**: header purple dark, first band white, second band light gray (`#F2F2F2`)
- **No conditional formatting** on this tab

**Why:** This is the final reporting format Jake applies — the quickhit list and attainment tiers are the presentation layer for stakeholders. Replicate this sidebar pattern when building prospect tabs for other accounts.
**How to apply:** Build A–K data first, then add column M sidebar with tiered segments (bordered warm-color box), revenue sum formula from Est MRR column, and attainment scenarios at 75/50/25%. Jake is open to creative formatting improvements — suggest cleaner visuals, better color palettes, or layout refinements when building reports.
