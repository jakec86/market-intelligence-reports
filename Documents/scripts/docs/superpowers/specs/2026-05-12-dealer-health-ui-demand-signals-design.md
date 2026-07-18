# Design: Dealer Health Dashboard — UI Refresh + Demand Signals Expansion

**Date:** 2026-05-12  
**Status:** Approved for implementation

---

## Context

Three improvements to the Dealer Health Dashboard after the initial debug/simplify pass:

1. **Score bars** — replace the flat `X/100` markdown table with rendered % fill bars (more scannable)
2. **Cars.com branding** — tighten brand alignment with Cars.com palette and typography
3. **Demand signals expansion** — fix broken market comparison + add Walk-in Demand and Vehicle Demand data from admin.cars.com

---

## 1. Score Bar Charts

### Output format
The system prompt is updated so Claude outputs a delimited scores block **at the top** of its response, before the narrative:

```
---SCORES---
Inventory Health|74|yellow|→|Under-merchandised vehicles rising
Pricing Position|88|green|↑|95% at-market or better
VDP Engagement|61|red|↓|VDPs down 4.8% MoM
Reputation|82|green|→|4.7★ on 962 reviews
Lead Performance|55|red|↓|0.03 leads/VIN
Marketplace Investment|70|yellow|→|Franchise Premium only
---END SCORES---
```

Each line: `Dimension|score(0-100)|color(green/yellow/red)|trend(↑↓→)|key driver phrase`

Color thresholds (defined in system prompt):
- `green`: 75–100
- `yellow`: 50–74
- `red`: 0–49

### Python parsing — `_parse_scores(text: str) -> tuple[list[dict], str]`
New helper in `dealer_health.py`:
- Extracts the `---SCORES---` block via regex
- Returns `(scores_list, narrative_text)` — narrative has the block stripped out
- Each score dict: `{name, score, color, trend, driver}`
- Returns `([], text)` if block missing (graceful degradation)

### HTML rendering — `_render_score_bars(scores: list[dict]) -> str`
Generates injected HTML with:
- One row per dimension: name left-aligned, `score%` + trend emoji right-aligned
- Colored fill bar using Cars.com purple gradient for green, amber for yellow, red for red
- Rendered via `st.markdown(html, unsafe_allow_html=True)` above the narrative

Scores block renders **above** `st.markdown(response_text)`. The narrative text (Key Findings, Growth Opps, etc.) renders below unchanged.

---

## 2. Cars.com Branding

All styling lives in a single `CC_CSS` constant injected via `st.markdown(unsafe_allow_html=True)` in the page config block.

### Color palette
```
--cc-purple:       #5B2D8E  (primary brand)
--cc-purple-light: #8B5FBF  (accent)
--cc-purple-pale:  #f3eeff  (chip backgrounds)
--cc-green:        #1a8a4a
--cc-yellow:       #b45309
--cc-red:          #c0392b
--cc-text:         #111827
--cc-gray:         #6b7280
--cc-border:       #e5e7eb
```

### Typography
Inject `DM Sans` from Google Fonts (lightweight, one weight range). Apply to `body` via the CSS block.

### Header
Keep existing structure but refine:
- `Cars.com · Growth Insights` eyebrow label (purple, 11px uppercase)
- `Dealer Health Dashboard` h1 (700 weight, dark)
- Purple gradient accent bar (4px, `#5B2D8E → #a78bfa`)
- Subheadline in gray

### Sidebar
- Section headers styled with purple left-border
- Status indicators use Cars.com green/red rather than Streamlit defaults

### Score bar colors (tied to palette)
- Green fill: `linear-gradient(90deg, #22c55e, #16a34a)`
- Yellow fill: `linear-gradient(90deg, #f59e0b, #d97706)`
- Red fill: `linear-gradient(90deg, #f87171, #dc2626)`
- Bar track: `#f0ebf8` (pale purple)

---

## 3. Demand Signals Expansion

### 3A — Fix Market Comparison (Pricing Summary)

The diagnostic is already in place (`_MC_JS` returns `{__available: [...]}` on miss, Python logs worksheet names). 

**Remaining work:** Run the dashboard once with SSO to capture the log output, then update line ~503 in `admin_cars.py`:
```python
const ws = sheet.worksheets.find(w => w.name === 'Pricing Summary');
# → update to new name once discovered from diagnostic log
```

This is a one-line fix once the name is known. Implementation can hard-code the name; no dynamic discovery needed.

### 3B — Walk-in Demand Index

**New report slug:** `walk_in_demand`  
**New JS constant:** `_WID_JS` — activates the default sheet, finds the demand index worksheet, extracts the dealer's index value vs. market.

Expected return: `{"demand_index": 112, "market_avg": 100}` (or similar — exact structure TBD from live inspection)

**New function:** `_fetch_walk_in_demand_on(page, uuid)` / `fetch_walk_in_demand(uuid)`  
Same pattern as existing fetch functions — returns `None` on failure.

**REQUIRED_WORKSHEETS entry:** Start empty (`[]`) with diagnostic JS, same as demand_signals. Populate after first live run reveals worksheet names.

**Context addition** in `build_data_context()`:
```
## Walk-in Demand (admin.cars.com)
- Dealer demand index: 112 (market avg: 100)
- Interpretation: dealer is drawing 12% above-average walk-in/drive-by traffic for this DMA
```

**Sidebar checkbox:** Folded under a new "Extended Demand Signals" expander alongside Vehicle Demand.

### 3C — Vehicle Demand (Top Searched Segments)

**New report slug:** `vehicle_demand`  
**New JS constant:** `_VD_JS` — extracts top 3–5 vehicle segments/makes by search volume in the dealer's DMA.

Expected return: `[{"segment": "Compact SUV", "index": 145}, ...]`

**New function:** `_fetch_vehicle_demand_on(page, uuid)` / `fetch_vehicle_demand(uuid)`

**Context addition** in `build_data_context()`:
```
## Vehicle Demand — Top Searched Segments (DMA)
- #1 Compact SUV: 145 demand index
- #2 Pickup Truck: 138 demand index
- #3 Midsize Sedan: 92 demand index
```

**System prompt update:** Add guidance for Claude to cross-reference vehicle demand against the dealer's inventory mix and call out mismatches (e.g., dealer heavy on sedans when the DMA is searching for SUVs).

### New sidebar checkbox placement
Under "Data Sources", add:
```
☑ admin.cars.com — Demand Signals (Market Comparison)   [existing, renamed]
  ☑ Walk-in Demand Index                                 [new, nested]
  ☑ Vehicle Demand (top segments)                        [new, nested]
```

---

## Files to Modify

| File | Changes |
|---|---|
| `dealer_health.py` | `CC_CSS` constant, `_parse_scores()`, `_render_score_bars()`, sidebar checkboxes, `build_data_context()` additions, system prompt update |
| `admin_cars.py` | `_WID_JS`, `_VD_JS`, `_fetch_walk_in_demand_on()`, `fetch_walk_in_demand()`, `_fetch_vehicle_demand_on()`, `fetch_vehicle_demand()`, `REQUIRED_WORKSHEETS` entries, `_MC_JS` name fix (post-diagnostic) |

---

## Verification

1. Run `python3 -m py_compile dealer_health.py admin_cars.py` — no errors
2. Launch Streamlit, run Dyer & Dyer Volvo (CCID 10730 — already has good data)
3. Confirm: scores block renders as colored bars above narrative
4. Confirm: Cars.com header/accent bar visible, DM Sans font loads
5. Confirm: market comparison data populates (once Pricing Summary name fixed)
6. Confirm: Walk-in Demand and Vehicle Demand sections appear in data context expander
7. Check `_parse_scores` degrades gracefully if Claude omits the block — narrative still renders
