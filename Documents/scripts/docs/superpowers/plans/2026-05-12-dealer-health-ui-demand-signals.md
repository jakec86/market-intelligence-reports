# Dealer Health Dashboard — UI Refresh + Demand Signals Expansion

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Cars.com-branded % fill score bars, then wire Walk-in Demand and Vehicle Demand from admin.cars.com into the Claude context.

**Architecture:** (1) Update `SYSTEM_PROMPT` so Claude emits a parseable `---SCORES---` block; parse + render it as colored HTML bars above the narrative. (2) Add two new `_on` fetchers + `_Session` methods in `admin_cars.py` following the exact existing pattern. (3) Thread new data through `build_data_context()` and the sidebar.

**Tech Stack:** Python 3.9, Streamlit, Playwright CDP, Cars.com admin dashboard JS API

---

## File Map

| File | Role |
|---|---|
| `dealer_health.py` | `CC_CSS` brand constant, `_parse_scores()`, `_render_score_bars()`, `SYSTEM_PROMPT` update, `build_data_context()` new params, sidebar new checkboxes, fetch wiring |
| `admin_cars.py` | `_WID_JS`, `_fetch_walk_in_demand_on()`, `_VD_JS`, `_fetch_vehicle_demand_on()`, two new `_Session` methods, two new one-shot public functions, `REQUIRED_WORKSHEETS` entries |
| `tests/test_admin_cars.py` | Tests for new parse helpers |
| `tests/test_dealer_health.py` | Tests for `_parse_scores` and `_render_score_bars` |

---

### Task 1: Cars.com CSS branding constant

**Files:**
- Modify: `dealer_health.py` (the `st.markdown(...)` block starting at line ~406)

- [ ] **Replace the existing `st.markdown(...)` CSS block** with a `CC_CSS` constant and a separate `st.markdown(CC_CSS, unsafe_allow_html=True)` call. Paste this exact block immediately after the imports, before `SYSTEM_PROMPT`:

```python
CC_CSS = """
<style>
  @import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,500;0,9..40,700&display=swap');
  html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
  .block-container { padding-top: 2rem; }
  div[data-testid="stStatusWidget"] { visibility: hidden; }
  /* Header */
  .cc-brand { font-size: 0.72rem; letter-spacing: 0.18em; text-transform: uppercase;
               color: #5B2D8E; font-weight: 700; }
  .cc-title { font-size: 2.0rem; font-weight: 700; color: #111827; margin: 0; line-height: 1.15; }
  .cc-sub   { color: #6b7280; font-size: 0.95rem; margin: 0.15rem 0 0.25rem 0; }
  .cc-accent { height: 4px; background: linear-gradient(90deg,#5B2D8E 0%,#a78bfa 100%);
               margin: 0 0 1rem 0; border-radius: 2px; }
  /* Sidebar tweaks */
  section[data-testid="stSidebar"] .stCheckbox label { font-size: 0.88rem; }
  section[data-testid="stSidebar"] h2 { color: #5B2D8E; border-left: 3px solid #5B2D8E;
                                         padding-left: 8px; }
</style>
<div class="cc-brand">Cars.com · Growth Insights</div>
<h1 class="cc-title">Dealer Health Dashboard</h1>
<p class="cc-sub">Health snapshots powered by the Dealer Growth Triangle</p>
<div class="cc-accent"></div>
"""
```

- [ ] **Remove** the old `st.markdown("""<style>...""", unsafe_allow_html=True)` block (the one that currently contains `.cc-accent`, `.cc-brand`, etc.).

- [ ] **Add** immediately after `st.set_page_config(...)`:
```python
st.markdown(CC_CSS, unsafe_allow_html=True)
```

- [ ] **Syntax check:**
```bash
cd ~/Documents/scripts && python3 -m py_compile dealer_health.py && echo OK
```
Expected: `OK`

- [ ] **Commit:**
```bash
git add Documents/scripts/dealer_health.py
git commit -m "style: Cars.com DM Sans branding + CC_CSS constant"
```

---

### Task 2: Update SYSTEM_PROMPT — structured scores block

**Files:**
- Modify: `dealer_health.py` — `SYSTEM_PROMPT` constant (lines ~26–114)

- [ ] **Replace the opening task instructions** in `SYSTEM_PROMPT`. Find this passage:

```
## Your Task

Produce a **Dealer Health Snapshot** in this exact format. Use emojis for trend indicators (🟢 healthy, 🟡 watch, 🔴 action needed) and keep each section tight.

### 📊 Health Snapshot — [Dealer Name]

| Dimension | Score | Trend | Key Driver |
|---|---|---|---|
| Inventory Health | X/100 | 🟢/🟡/🔴 ↑↓→ | one short phrase |
| Pricing Position | X/100 | 🟢/🟡/🔴 ↑↓→ | one short phrase |
| Engagement (VDPs) | X/100 | 🟢/🟡/🔴 ↑↓→ | one short phrase |
| Reputation | X/100 | 🟢/🟡/🔴 ↑↓→ | one short phrase |
| Lead Performance | X/100 | 🟢/🟡/🔴 ↑↓→ | one short phrase |
| Marketplace Investment | X/100 | 🟢/🟡/🔴 ↑↓→ | one short phrase |
```

Replace with:

```
## Your Task

**REQUIRED — start your response with this block, no text before it:**

---SCORES---
Inventory Health|<integer 0-100>|<green|yellow|red>|<↑|↓|→>|<one key driver phrase>
Pricing Position|<integer 0-100>|<green|yellow|red>|<↑|↓|→>|<one key driver phrase>
Engagement (VDPs)|<integer 0-100>|<green|yellow|red>|<↑|↓|→>|<one key driver phrase>
Reputation|<integer 0-100>|<green|yellow|red>|<↑|↓|→>|<one key driver phrase>
Lead Performance|<integer 0-100>|<green|yellow|red>|<↑|↓|→>|<one key driver phrase>
Marketplace Investment|<integer 0-100>|<green|yellow|red>|<↑|↓|→>|<one key driver phrase>
---END SCORES---

Color thresholds: green = 75–100, yellow = 50–74, red = 0–49.
Trend: ↑ improving MoM, ↓ declining MoM, → flat/mixed.

Then continue with the full snapshot:

### 📊 Health Snapshot — [Dealer Name]
```

- [ ] **Syntax check:**
```bash
python3 -m py_compile ~/Documents/scripts/dealer_health.py && echo OK
```
Expected: `OK`

- [ ] **Commit:**
```bash
git add Documents/scripts/dealer_health.py
git commit -m "feat: structured SCORES block in system prompt"
```

---

### Task 3: `_parse_scores` and `_render_score_bars` helpers

**Files:**
- Modify: `dealer_health.py` — add two functions after the `build_data_context` function (after line ~394), before the `# ─── UI ───` section

- [ ] **Write the failing tests** in `tests/test_dealer_health.py` (create if absent):

```python
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from dealer_health import _parse_scores, _render_score_bars

SAMPLE = """\
---SCORES---
Inventory Health|74|yellow|→|Under-merch rising
Pricing Position|88|green|↑|95% at market
Engagement (VDPs)|61|red|↓|VDPs down 4.8%
Reputation|82|green|→|4.7 star
Lead Performance|55|red|↓|0.03 leads/VIN
Marketplace Investment|70|yellow|→|Premium only
---END SCORES---

### 📊 Health Snapshot — Test Dealer
Some narrative text.
"""

def test_parse_scores_extracts_six_dimensions():
    scores, narrative = _parse_scores(SAMPLE)
    assert len(scores) == 6

def test_parse_scores_fields():
    scores, _ = _parse_scores(SAMPLE)
    s = scores[0]
    assert s["name"] == "Inventory Health"
    assert s["score"] == 74
    assert s["color"] == "yellow"
    assert s["trend"] == "→"
    assert s["driver"] == "Under-merch rising"

def test_parse_scores_strips_block_from_narrative():
    _, narrative = _parse_scores(SAMPLE)
    assert "---SCORES---" not in narrative
    assert "Health Snapshot" in narrative

def test_parse_scores_graceful_on_missing_block():
    scores, narrative = _parse_scores("Just some text with no block.")
    assert scores == []
    assert narrative == "Just some text with no block."

def test_render_score_bars_returns_html_string():
    scores, _ = _parse_scores(SAMPLE)
    html = _render_score_bars(scores)
    assert "<div" in html
    assert "74%" in html
    assert "88%" in html

def test_render_score_bars_empty_list():
    assert _render_score_bars([]) == ""
```

- [ ] **Run tests to confirm they fail:**
```bash
cd ~/Documents/scripts && python3 -m pytest tests/test_dealer_health.py -v 2>&1 | head -20
```
Expected: `ImportError` or `AttributeError` — functions not defined yet.

- [ ] **Add the two functions** to `dealer_health.py`, between `build_data_context` and `# ─── UI ───`:

```python
import re as _re

def _parse_scores(text: str) -> tuple:
    """Extract ---SCORES--- block from Claude output.
    Returns (scores_list, narrative_text). scores_list is [] if block is absent.
    """
    m = _re.search(r"---SCORES---\n(.*?)\n---END SCORES---\n?", text, _re.DOTALL)
    if not m:
        return [], text
    scores = []
    for line in m.group(1).strip().splitlines():
        parts = [p.strip() for p in line.split("|")]
        if len(parts) >= 5:
            try:
                scores.append({
                    "name":   parts[0],
                    "score":  int(parts[1]),
                    "color":  parts[2],
                    "trend":  parts[3],
                    "driver": parts[4],
                })
            except (ValueError, IndexError):
                pass
    narrative = (text[: m.start()] + text[m.end() :]).strip()
    return scores, narrative


_SCORE_GRADIENTS = {
    "green":  ("linear-gradient(90deg,#22c55e,#16a34a)", "#166534"),
    "yellow": ("linear-gradient(90deg,#f59e0b,#d97706)", "#92400e"),
    "red":    ("linear-gradient(90deg,#f87171,#dc2626)", "#991b1b"),
}

def _render_score_bars(scores: list) -> str:
    """Return an HTML string with one % fill bar per score dict."""
    if not scores:
        return ""
    rows = []
    for s in scores:
        grad, text_color = _SCORE_GRADIENTS.get(s["color"], _SCORE_GRADIENTS["yellow"])
        pct = max(0, min(100, s["score"]))
        rows.append(
            f'<div style="margin-bottom:10px">'
            f'<div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:3px">'
            f'<span style="font-size:13px;font-weight:600;color:#111827">{s["name"]}</span>'
            f'<span style="font-size:13px;font-weight:700;color:{text_color}">{pct}%&nbsp;{s["trend"]}</span>'
            f'</div>'
            f'<div style="background:#f0ebf8;border-radius:4px;height:8px;overflow:hidden">'
            f'<div style="width:{pct}%;height:100%;border-radius:4px;background:{grad}"></div>'
            f'</div>'
            f'<div style="font-size:11px;color:#6b7280;margin-top:2px">{s["driver"]}</div>'
            f'</div>'
        )
    return f'<div style="margin-bottom:20px">{"".join(rows)}</div>'
```

- [ ] **Run tests:**
```bash
cd ~/Documents/scripts && python3 -m pytest tests/test_dealer_health.py -v
```
Expected: all 6 tests PASS.

- [ ] **Commit:**
```bash
git add Documents/scripts/dealer_health.py tests/test_dealer_health.py
git commit -m "feat: _parse_scores + _render_score_bars with tests"
```

---

### Task 4: Wire score bars into the UI render loop

**Files:**
- Modify: `dealer_health.py` — the response rendering block (~line 633–638)

- [ ] **Find** this block (after the subprocess call):

```python
    response_text = result.stdout.strip()
    if result.returncode != 0 or not response_text:
        status_box.empty()
        st.error(f"Claude CLI error (exit {result.returncode}):\n\n{''.join(stderr_lines)[:1000]}")
```

Wait — the current code uses `Popen` streaming, not `subprocess.run`. Locate the actual rendering lines after the stream loop. They look like:

```python
    if proc.returncode != 0 or not response_text:
        status_box.empty()
        st.error(...)
```

- [ ] **Replace** that error/render block with:

```python
    response_text = response_text.strip()
    if proc.returncode != 0 or not response_text:
        status_box.empty()
        st.error(f"Claude CLI error (exit {proc.returncode}):\n\n{''.join(stderr_lines)[:1000]}")
    else:
        scores, narrative = _parse_scores(response_text)
        if scores:
            st.markdown(_render_score_bars(scores), unsafe_allow_html=True)
        st.markdown(narrative)
```

- [ ] **Syntax check:**
```bash
python3 -m py_compile ~/Documents/scripts/dealer_health.py && echo OK
```

- [ ] **Commit:**
```bash
git add Documents/scripts/dealer_health.py
git commit -m "feat: render score bars above narrative in UI"
```

---

### Task 5: Walk-in Demand fetcher in admin_cars.py

**Files:**
- Modify: `admin_cars.py` — add after the `_fetch_market_comparison_on` / `fetch_market_comparison` block (~line 559)

- [ ] **Add** `REQUIRED_WORKSHEETS` entry for the new slug (line ~55, inside the dict):

```python
    "walk_in_demand": [],   # diagnostic-first: __available logged on first run
```

- [ ] **Add** the JS constant and `_on` fetcher immediately after `fetch_market_comparison`:

```python
_WID_JS = """
async () => {
    const viz = document.querySelector('tableau-viz');
    if (!viz || !viz.workbook) return null;
    const sheet = viz.workbook.activeSheet;
    const names = sheet.worksheets.map(w => w.name);
    const ws = sheet.worksheets.find(w => w.name === 'Walk-In Demand');
    if (!ws) return { __available: names };
    try {
        const data = await ws.getSummaryDataAsync({ maxRows: 50 });
        return {
            cols: data.columns.map(c => c.fieldName),
            rows: data.data.map(r => r.map(c => c.formattedValue))
        };
    } catch(e) { return { __available: names }; }
}
"""


def _fetch_walk_in_demand_on(page, uuid: str) -> Optional[dict]:
    """Navigate to walk_in_demand report and extract demand index data."""
    if not _load_report(page, uuid, "walk_in_demand"):
        return None
    try:
        raw = page.evaluate(_WID_JS)
        if not raw:
            return None
        if "__available" in raw:
            log.warning("Walk-In Demand worksheet not found. Available: %s", raw["__available"])
            return None
        if not raw.get("rows"):
            return None
        return {"cols": raw["cols"], "rows": raw["rows"]}
    except Exception:
        log.exception("fetch_walk_in_demand parse failed for uuid=%s", uuid)
        return None


def fetch_walk_in_demand(uuid: str) -> Optional[dict]:
    """One-shot fetch. Prefer session() for multi-fetch flows."""
    with session() as s:
        return s.fetch_walk_in_demand(uuid)
```

- [ ] **Add** the method to `_Session` (inside the class, after `fetch_roi_one_sheeter`):

```python
    def fetch_walk_in_demand(self, uuid: str) -> Optional[dict]:
        return _fetch_walk_in_demand_on(self.page, uuid)
```

- [ ] **Syntax check:**
```bash
python3 -m py_compile ~/Documents/scripts/admin_cars.py && echo OK
```

- [ ] **Commit:**
```bash
git add Documents/scripts/admin_cars.py
git commit -m "feat: Walk-in Demand fetcher with diagnostic JS"
```

---

### Task 6: Vehicle Demand fetcher in admin_cars.py

**Files:**
- Modify: `admin_cars.py` — add after the Walk-in Demand block from Task 5

- [ ] **Add** `REQUIRED_WORKSHEETS` entry:

```python
    "vehicle_demand": [],   # diagnostic-first: __available logged on first run
```

- [ ] **Add** the JS constant, `_on` fetcher, and one-shot function:

```python
_VD_JS = """
async () => {
    const viz = document.querySelector('tableau-viz');
    if (!viz || !viz.workbook) return null;
    const sheet = viz.workbook.activeSheet;
    const names = sheet.worksheets.map(w => w.name);
    const ws = sheet.worksheets.find(w => w.name === 'Vehicle Demand');
    if (!ws) return { __available: names };
    try {
        const data = await ws.getSummaryDataAsync({ maxRows: 10 });
        return {
            cols: data.columns.map(c => c.fieldName),
            rows: data.data.map(r => r.map(c => c.formattedValue))
        };
    } catch(e) { return { __available: names }; }
}
"""


def _fetch_vehicle_demand_on(page, uuid: str) -> Optional[dict]:
    """Navigate to vehicle_demand report and extract top-searched segment data."""
    if not _load_report(page, uuid, "vehicle_demand"):
        return None
    try:
        raw = page.evaluate(_VD_JS)
        if not raw:
            return None
        if "__available" in raw:
            log.warning("Vehicle Demand worksheet not found. Available: %s", raw["__available"])
            return None
        if not raw.get("rows"):
            return None
        return {"cols": raw["cols"], "rows": raw["rows"]}
    except Exception:
        log.exception("fetch_vehicle_demand parse failed for uuid=%s", uuid)
        return None


def fetch_vehicle_demand(uuid: str) -> Optional[dict]:
    """One-shot fetch. Prefer session() for multi-fetch flows."""
    with session() as s:
        return s.fetch_vehicle_demand(uuid)
```

- [ ] **Add** `_Session` method after `fetch_walk_in_demand`:

```python
    def fetch_vehicle_demand(self, uuid: str) -> Optional[dict]:
        return _fetch_vehicle_demand_on(self.page, uuid)
```

- [ ] **Write tests** in `tests/test_admin_cars.py` — add at bottom of existing file:

```python
# ── Walk-in Demand + Vehicle Demand manifest ──────────────────────────────────

def test_walk_in_demand_in_required_worksheets():
    assert "walk_in_demand" in admin_cars.REQUIRED_WORKSHEETS

def test_vehicle_demand_in_required_worksheets():
    assert "vehicle_demand" in admin_cars.REQUIRED_WORKSHEETS

def test_session_has_fetch_walk_in_demand():
    assert hasattr(admin_cars._Session, "fetch_walk_in_demand")

def test_session_has_fetch_vehicle_demand():
    assert hasattr(admin_cars._Session, "fetch_vehicle_demand")
```

- [ ] **Run tests:**
```bash
cd ~/Documents/scripts && python3 -m pytest tests/test_admin_cars.py -k "walk_in or vehicle_demand" -v
```
Expected: 4 PASS.

- [ ] **Syntax check + commit:**
```bash
python3 -m py_compile ~/Documents/scripts/admin_cars.py && echo OK
git add Documents/scripts/admin_cars.py tests/test_admin_cars.py
git commit -m "feat: Vehicle Demand fetcher with diagnostic JS + manifest tests"
```

---

### Task 7: Wire demand data into dealer_health.py

**Files:**
- Modify: `dealer_health.py` — sidebar, session fetch block, `build_data_context()`, system prompt

#### 7a — Sidebar checkboxes

- [ ] **Find** the `st.subheader("Data Sources")` block and replace the existing `use_admin` line with:

```python
    st.subheader("Data Sources")
    use_sf = st.checkbox("Salesforce", value=True)
    use_admin = st.checkbox("admin.cars.com — Performance Trends", value=True)
    with st.expander("Extended Demand Signals", expanded=False):
        use_wid = st.checkbox("Walk-in Demand Index", value=True)
        use_vd  = st.checkbox("Vehicle Demand (top segments)", value=True)
```

#### 7b — Fetch calls in the session block

- [ ] **Find** the `with admin_cars.session() as admin:` block. After the `si_data` fetch (~line 578) and before the closing of the `with` block, add:

```python
                wid_data = vd_data = None
                if use_wid:
                    _progress("Pulling Walk-in Demand…")
                    wid_data = admin.fetch_walk_in_demand(uuid)
                    if wid_data:
                        source_summary.append("Walk-in Demand: data available")
                    else:
                        source_summary.append("Walk-in Demand: not available (worksheet TBD)")

                if use_vd:
                    _progress("Pulling Vehicle Demand…")
                    vd_data = admin.fetch_vehicle_demand(uuid)
                    if vd_data:
                        source_summary.append("Vehicle Demand: data available")
                    else:
                        source_summary.append("Vehicle Demand: not available (worksheet TBD)")
```

- [ ] **Initialize** `wid_data = vd_data = None` in the variable init block near the top of the `if run:` block (alongside `perf_data = rep_data = ...`).

#### 7c — Pass to `build_data_context`

- [ ] **Update** the `build_data_context(...)` call signature — add two new keyword args:

```python
    data_context = build_data_context(
        dealer_name=dealer_name,
        sf_data=sf_data,
        perf_data=perf_data,
        rep_data=rep_data,
        mkt_data=mkt_data,
        sub_data=sub_data,
        lo_data=lo_data,
        si_data=si_data,
        roi_data=roi_data,
        wid_data=wid_data,
        vd_data=vd_data,
    )
```

#### 7d — Update `build_data_context` signature + body

- [ ] **Add** `wid_data: Optional[dict] = None, vd_data: Optional[dict] = None` to the function signature.

- [ ] **Add** these two sections at the end of `build_data_context`, just before the final `return "\n".join(parts)`:

```python
    # Walk-in Demand (raw rows — Claude interprets)
    if wid_data and wid_data.get("rows"):
        parts.append("\n## Walk-in Demand (admin.cars.com — DMA foot traffic index)")
        cols = wid_data.get("cols", [])
        for row in wid_data["rows"][:10]:
            parts.append("- " + " | ".join(f"{c}: {v}" for c, v in zip(cols, row)))

    # Vehicle Demand (raw rows — Claude interprets)
    if vd_data and vd_data.get("rows"):
        parts.append("\n## Vehicle Demand — Top Searched Segments (DMA)")
        cols = vd_data.get("cols", [])
        for row in vd_data["rows"][:5]:
            parts.append("- " + " | ".join(f"{c}: {v}" for c, v in zip(cols, row)))
```

- [ ] **Syntax check:**
```bash
python3 -m py_compile ~/Documents/scripts/dealer_health.py && echo OK
```

- [ ] **Commit:**
```bash
git add Documents/scripts/dealer_health.py
git commit -m "feat: Wire Walk-in Demand + Vehicle Demand into UI and context"
```

---

### Task 8: System prompt — demand signals guidance

**Files:**
- Modify: `dealer_health.py` — `SYSTEM_PROMPT` rules section

- [ ] **Append** the following to the end of the `## Rules` section in `SYSTEM_PROMPT` (before the closing `"""`):

```
- **Walk-in Demand data** (if present): the rows contain DMA-level foot traffic index values. Interpret them as a demand signal — a high index means the market is actively shopping, a low index is a warning that marketing should focus on creating demand. Cross-reference against the dealer's connections trend.
- **Vehicle Demand data** (if present): shows the top-searched vehicle segments in the dealer's DMA. If the dealer's inventory mix doesn't match the top-searched segments, flag it as a specific growth opportunity (e.g., "DMA searches are 40% SUV but dealer is 70% sedan-heavy").
```

- [ ] **Syntax check:**
```bash
python3 -m py_compile ~/Documents/scripts/dealer_health.py && echo OK
```

- [ ] **Commit:**
```bash
git add Documents/scripts/dealer_health.py
git commit -m "feat: demand signals interpretation rules in system prompt"
```

---

### Task 9: End-to-end verification

- [ ] **Run full test suite:**
```bash
cd ~/Documents/scripts && python3 -m pytest tests/ -v 2>&1 | tail -20
```
Expected: all existing tests pass + new tests pass. No regressions.

- [ ] **Launch dashboard:**
```bash
python3 -m streamlit run ~/Documents/scripts/dealer_health.py
```

- [ ] **Run Dyer & Dyer Volvo Cars** (CCID 10730 — has good existing data from the session earlier):
  - Enter `Dyer & Dyer Volvo` in the dealer name field
  - Check "Extended Demand Signals" expander (both boxes on)
  - Click Run Analysis
  - **Expected:** Blue "Connecting to Claude CLI…" info box for ~20s, then colored % fill bars appear (6 rows), then the narrative text below

- [ ] **Check score bars:**
  - 6 dimensions visible
  - Colors match green/yellow/red thresholds (≥75 green, 50–74 yellow, <50 red)
  - Trend arrows correct

- [ ] **Check demand signals:**
  - "Walk-in Demand: not available (worksheet TBD)" or data in expander — either is correct on first run
  - Python log (terminal running Streamlit) should show `Available worksheets: [...]` — **record these names** for the one-line fix below

- [ ] **One-line worksheet name fix** (after recording from log):
  - In `admin_cars.py`, find `_WID_JS` line: `w.name === 'Walk-In Demand'` → replace with actual name from log
  - Same for `_VD_JS` line: `w.name === 'Vehicle Demand'` → replace with actual name
  - Same for `_MC_JS` line: `w.name === 'Pricing Summary'` → replace with actual name
  - Update the corresponding `REQUIRED_WORKSHEETS` entries with the confirmed names
  - Commit: `git commit -m "fix: update worksheet names from live diagnostic"`

- [ ] **Re-run** with corrected names to confirm market comparison + demand signals all populate.
