# Skill Test Harness — Design Spec
**Date:** 2026-05-12  
**Status:** Approved for implementation

---

## Problem

Recurring failures in automated workflows (Price Badge reports, email drafts, admin.cars.com
scraping) have been traced to a small set of distinct root causes that re-surface across
sessions because they live in undocumented behavioral contracts — not caught by any test.
This harness codifies those contracts as pytest fixtures and enforces them via a pre-commit
hook and an autonomous hardening loop.

---

## Scope

Two test layers:

1. **Python unit tests** — test functions in `pb_report.py` and `admin_cars.py` that
   implement sheet sorting, CSV validation, column reordering, and email composition.

2. **Skill compliance tests** — assert that skill `.md` files contain required guardrails
   (e.g. "Sort range" not "Sort sheet"; "HTML" format for emails).

---

## Failure Modes Codified

| ID | Failure | Target | Assertion |
|----|---------|--------|-----------|
| FM-1 | Sort range corruption — "Sort sheet" moves header into data | `DEALERS[*]["sort_range"]` + `safe_sort_pbt` | range always starts at `data_start_row`; no sort call touches row 1 or 2 |
| FM-2 | CSV schema drift — Tableau renames a column, import proceeds silently | `_validate_csv_headers` | raises `SystemExit` with diff when expected column missing |
| FM-3 | HTML-vs-plaintext fallback — email loses `<html>` tags | `compose_email_html` + `create_gmail_draft` | body starts with `<html>`, MIMEText subtype is `"html"` |
| FM-4 | Double-count website transfers — sub-category rows inflate lead total | `_aggregate_lead_sources` (admin_cars.py) | add `@pytest.mark.regression` to existing `test_aggregate_lead_sources_avoids_double_counting_website_transfers`; no new fixture needed |
| FM-5 | Blank MMYT from column reorder — wrong index in Make/Stock/VIN swap | `reorder_nalley_columns` | output[1][2]=Stock, [3]=VIN, [4]=Make for known input |
| FM-6 | Formula overwrite — `ws.update()` called on PBT tab (has VLOOKUPs) | `import_to_sheet` | `update()` called on `import_tab` name only, never `pbt_tab` |
| FM-7 | Sort-sheet guardrail missing from skill | `nalley-pb-report.md`, `hendricks-pb-report.md` | file contains "sort range", does NOT contain "sort sheet" |
| FM-8 | HTML email guardrail missing from skill | all email-drafting skills | file contains "html", does NOT contain "plain text" |

---

## File Layout

```
~/Documents/scripts/
├── tests/
│   ├── test_admin_cars.py          (existing — no changes)
│   ├── test_dealer_health.py       (existing — no changes)
│   ├── test_pb_report.py           NEW — FM-1 through FM-6
│   └── test_skills_compliance.py   NEW — FM-7 and FM-8
├── harden_skills.py                NEW — autonomous iteration loop
├── pb_report.py                    patched as needed
└── admin_cars.py                   patched as needed

~/.claude/commands/
├── nalley-pb-report.md             patched as needed
├── hendricks-pb-report.md          patched as needed
└── *.md                            scanned for email-format compliance

~/ (repo root)
└── .git/hooks/pre-commit           NEW — blocks failing commits on both paths
```

---

## Test Design

### `tests/test_pb_report.py`

Uses `unittest.mock.patch` and `MagicMock`, matching `test_admin_cars.py` conventions.
Module-level fixture constants for CSV rows; no global `pytest.fixture` usage.

**FM-1 — Sort range starts at data row (not header):**
```python
def test_sort_range_never_includes_header_row():
    assert int(re.search(r'A(\d+)', DEALERS["hendrick"]["sort_range"]).group(1)) >= 3
    assert int(re.search(r'A(\d+)', DEALERS["nalley"]["sort_range"]).group(1)) >= 4

def test_safe_sort_pbt_never_calls_sort_on_row_one(mock_worksheet):
    # Drive safe_sort_pbt; assert every sort() call uses range starting >= data_start_row
```

**FM-2 — CSV schema validation:**
```python
def test_validate_csv_headers_exits_when_column_missing():
    with pytest.raises(SystemExit):
        _validate_csv_headers("x.csv", [["Wrong", "Cols"]], _LEI_EXPECTED, "LEI")

def test_validate_csv_headers_passes_when_all_columns_present():
    rows = [["Dealer name", "Dealer id", "Stock num", "VIN", "Make name"], ["v"]*5]
    _validate_csv_headers("x.csv", rows, _LEI_EXPECTED, "LEI")  # no raise
```

**FM-3 — HTML email body:**
```python
def test_compose_email_html_returns_html_document():
    html = compose_email_html(DEALERS["nalley"], _SAMPLE_STATS)
    assert html.strip().startswith("<html>")
    assert "</html>" in html

def test_create_gmail_draft_attaches_html_not_plain(mock_gmail):
    # Capture MIMEText subtype passed to msg.attach(); must be "html"
```

**FM-5 — Column reorder:**
```python
def test_reorder_nalley_columns_swaps_make_stock_vin():
    rows = [["hdr"]*5, ["Nalley", "109754", "HONDA", "ABC123", "1HGBH41"]]
    out = reorder_nalley_columns(rows)
    assert out[1][2] == "ABC123"    # Stock num
    assert out[1][3] == "1HGBH41"  # VIN
    assert out[1][4] == "HONDA"     # Make
```

**FM-6 — Formula overwrite guard:**
```python
def test_import_to_sheet_never_touches_pbt_tab(mock_gc):
    # Verify ws.update() called with import_tab name; pbt_tab worksheet never cleared/updated
```

### `tests/test_skills_compliance.py`

Reads `.md` files as raw strings. Uses `pytest.mark.parametrize` for multi-skill rules.

**FM-7 — Sort-range guardrail:**
```python
@pytest.mark.parametrize("skill_file", ["nalley-pb-report.md", "hendricks-pb-report.md"])
def test_pb_skill_says_sort_range_not_sort_sheet(skill_file):
    text = (SKILLS_DIR / skill_file).read_text().lower()
    assert "sort range" in text
    assert "sort sheet" not in text
```

**FM-8 — HTML email guardrail:**
```python
@pytest.mark.parametrize("skill_file", EMAIL_SKILLS)
def test_email_skill_requires_html_format(skill_file):
    text = (SKILLS_DIR / skill_file).read_text().lower()
    assert "html" in text
    assert "plain text" not in text
```

---

## Iteration Loop — `harden_skills.py`

```
1. Run: pytest tests/ -q --tb=short --json-report --json-report-file=.harden_report.json
2. Parse JSON report — group failures by: Python test vs skill compliance test
3. For each failure (max 10 iterations total):
   a. Python failure → read source function → apply minimal patch → re-run test file
   b. Skill failure  → open .md → insert missing guardrail line → re-run compliance tests
4. If patched file passes → git add <file> && git commit -m "fix(harness): <failure_id>"
5. If patch fails after 2 attempts → print "UNFIXABLE: <reason>", skip
6. After loop: print iteration trace (test → patch → result per loop)
```

Stop conditions: all green, or 10 iterations elapsed.

Requires `pytest-json-report`: `pip3 install pytest-json-report`.

---

## Pre-commit Hook — `.git/hooks/pre-commit`

Triggers only when staged files touch `Documents/scripts/` or `.claude/commands/`:

```bash
#!/bin/sh
if git diff --cached --name-only | grep -qE '^(Documents/scripts/|\.claude/commands/)'; then
  cd ~/Documents/scripts
  python -m pytest tests/ -q --tb=short
  if [ $? -ne 0 ]; then
    echo "❌ Tests failed — commit blocked."
    echo "   Run: cd ~/Documents/scripts && python -m pytest tests/ -v"
    exit 1
  fi
fi
exit 0
```

---

## Iteration Trace Preview (three highest-friction skills)

The harness will show this format for each loop:

```
[1/3] FAIL: test_pb_skill_says_sort_range_not_sort_sheet[nalley-pb-report.md]
      → patch: added "Sort range A4:L" guardrail to Step 3 of nalley-pb-report.md
      → re-run: PASS
      → committed: fix(harness): FM-7-nalley

[2/3] FAIL: test_sort_range_never_includes_header_row
      → patch: DEALERS["hendrick"]["sort_range"] already correct — assertion was wrong
      → fix: tightened assertion to match actual layout (R1=threshold, R2=header, R3+data)
      → re-run: PASS
      → committed: fix(harness): FM-1-hendrick

[3/3] FAIL: test_compose_email_html_returns_html_document
      → patch: compose_email_html already returns <html> — import path issue in test
      → fix: corrected sys.path insert in test file
      → re-run: PASS
      → committed: fix(harness): FM-3-html
```

---

## Out of Scope

- Testing Playwright browser automation (requires live Chrome session)
- Testing Gmail MCP draft creation end-to-end (requires OAuth)
- Tableau API response parsing (covered by `test_admin_cars.py` fixtures already)
- Day-of-week miscalculation (email subject uses `date.today()` — no static assertion possible without time-mocking; deferred)
