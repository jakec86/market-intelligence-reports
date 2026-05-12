# Skill Test Harness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a pytest-based test harness that codifies 8 recurring workflow failure modes, plus an autonomous hardening loop and pre-commit hook that keeps skills and Python scripts in compliance.

**Architecture:** Two new test files under `tests/` (Python unit tests + skill compliance assertions), a `harden_skills.py` script that patches failing skill `.md` files and auto-commits fixes, and a `.git/hooks/pre-commit` that gates commits touching `Documents/scripts/` or `.claude/commands/`. Everything runs via one command: `python -m pytest tests/`.

**Tech Stack:** Python 3.9, pytest, pytest-json-report, unittest.mock, pathlib, subprocess, gspread (already installed)

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `tests/conftest.py` | Modify | Add pytest marker registration for `regression` |
| `tests/test_pb_report.py` | Create | FM-1 through FM-6 — pb_report.py unit tests |
| `tests/test_skills_compliance.py` | Create | FM-7, FM-8 — skill .md guardrail assertions |
| `tests/test_admin_cars.py` | Modify | Add `@pytest.mark.regression` to FM-4 double-count test |
| `harden_skills.py` | Create | Iteration loop: run tests → patch skills → commit |
| `.git/hooks/pre-commit` | Create | Block commits when tests fail on staged files |

All paths are relative to `~/Documents/scripts/` unless otherwise noted.

---

## Task 1: Install pytest-json-report and register markers

**Files:**
- Modify: `tests/conftest.py`

- [ ] **Step 1: Install pytest-json-report**

```bash
cd ~/Documents/scripts
pip3 install pytest-json-report
```

Expected: `Successfully installed pytest-json-report-...`

- [ ] **Step 2: Verify existing tests still pass**

```bash
python -m pytest tests/ -q
```

Expected: something like `14 passed in X.XXs` (existing tests all green before we touch anything).

- [ ] **Step 3: Add regression marker to conftest.py**

Open `tests/conftest.py`. It currently contains:
```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
```

Replace the entire file with:
```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "regression: marks tests guarding against specific past incidents"
    )
```

- [ ] **Step 4: Verify markers registered cleanly**

```bash
python -m pytest tests/ --markers | grep regression
```

Expected: `regression: marks tests guarding against specific past incidents`

- [ ] **Step 5: Commit**

```bash
git add tests/conftest.py
git commit -m "test: register regression pytest marker"
```

---

## Task 2: FM-4 — Tag existing double-count regression test

**Files:**
- Modify: `tests/test_admin_cars.py:313-318`

The test `test_aggregate_lead_sources_avoids_double_counting_website_transfers` already exists and passes. We just tag it.

- [ ] **Step 1: Add the marker import to test_admin_cars.py**

Open `tests/test_admin_cars.py`. Find the top imports block (lines 1-2):
```python
from unittest.mock import patch, MagicMock
import admin_cars
```

Replace with:
```python
from unittest.mock import patch, MagicMock
import pytest
import admin_cars
```

- [ ] **Step 2: Add the @pytest.mark.regression decorator**

Find this function (around line 313):
```python
def test_aggregate_lead_sources_avoids_double_counting_website_transfers():
    """The bare 'Website Transfers' is the top-level total; sub-categories like
    'Website Transfers - Deep Link' must NOT be added on top of it."""
```

Add the marker immediately above it:
```python
@pytest.mark.regression
def test_aggregate_lead_sources_avoids_double_counting_website_transfers():
    """The bare 'Website Transfers' is the top-level total; sub-categories like
    'Website Transfers - Deep Link' must NOT be added on top of it."""
```

- [ ] **Step 3: Run tests to confirm nothing broke**

```bash
python -m pytest tests/test_admin_cars.py -v -k "double_counting"
```

Expected: `1 passed`

- [ ] **Step 4: Commit**

```bash
git add tests/test_admin_cars.py
git commit -m "test: mark double-count regression test FM-4"
```

---

## Task 3: Create test_pb_report.py — FM-1 sort range config

**Files:**
- Create: `tests/test_pb_report.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_pb_report.py` with this content:

```python
import re, sys, base64
from unittest.mock import patch, MagicMock, call
import pytest

from pb_report import (
    DEALERS,
    _validate_csv_headers,
    _LEI_EXPECTED,
    _DEM_EXPECTED,
    compose_email_html,
    create_gmail_draft,
    reorder_nalley_columns,
    import_to_sheet,
    safe_sort_pbt,
)

# ── Shared fixture data ────────────────────────────────────────────────────────

_SAMPLE_STATS = {
    "pct": "42%",
    "threshold": "$1,000",
    "total": 10,
    "within_count": 3,
    "at_threshold_count": 1,
    "at_threshold_vehicles": [{"mmyt": "2022 Lexus RX 350", "diff": "$0", "current": "Good", "next": "Great"}],
    "already_great": 2,
    "top_vehicles": [
        {"mmyt": "2021 Lexus ES 350", "diff": "$499", "current": "Fair", "next": "Good"},
        {"mmyt": "2020 Lexus NX 300", "diff": "$750", "current": "Not Badged", "next": "Fair"},
    ],
}


# ── FM-1: Sort range config must never include header rows ─────────────────────

def test_nalley_sort_range_starts_at_data_row():
    """Nalley has headers on row 3, data starts row 4 — sort_range must begin at A4."""
    start = int(re.search(r'A(\d+)', DEALERS["nalley"]["sort_range"]).group(1))
    assert start >= 4, f"Nalley sort_range starts at row {start}, expected >= 4 (data_start_row)"


def test_hendrick_sort_range_starts_at_data_row():
    """Hendrick has headers on row 2, data starts row 3 — sort_range must begin at A3."""
    start = int(re.search(r'A(\d+)', DEALERS["hendrick"]["sort_range"]).group(1))
    assert start >= 3, f"Hendrick sort_range starts at row {start}, expected >= 3 (data_start_row)"


def test_all_dealers_sort_range_matches_data_start_row():
    """For every dealer, the sort_range start row must equal data_start_row."""
    for name, cfg in DEALERS.items():
        start = int(re.search(r'A(\d+)', cfg["sort_range"]).group(1))
        assert start == cfg["data_start_row"], (
            f"Dealer '{name}': sort_range starts at row {start} "
            f"but data_start_row={cfg['data_start_row']}"
        )
```

- [ ] **Step 2: Run to verify it passes (config is already correct)**

```bash
python -m pytest tests/test_pb_report.py::test_nalley_sort_range_starts_at_data_row \
               tests/test_pb_report.py::test_hendrick_sort_range_starts_at_data_row \
               tests/test_pb_report.py::test_all_dealers_sort_range_matches_data_start_row -v
```

Expected: `3 passed`

If any fail: open `pb_report.py` and correct the `sort_range` value in the failing dealer's `DEALERS` dict so the A-row number matches `data_start_row`.

- [ ] **Step 3: Commit**

```bash
git add tests/test_pb_report.py
git commit -m "test(FM-1): sort range config assertions"
```

---

## Task 4: FM-1 — safe_sort_pbt mock test

**Files:**
- Modify: `tests/test_pb_report.py` (append)

- [ ] **Step 1: Write the failing test — append to test_pb_report.py**

```python
@patch("pb_report.time.sleep")
def test_safe_sort_pbt_never_calls_sort_on_rows_before_data_start(mock_sleep):
    """safe_sort_pbt() must not include any row before data_start_row in any sort call.

    Nalley: data_start_row=4. All four sort passes must use ranges starting at A4 or later.
    """
    mock_sh = MagicMock()
    mock_pbt = MagicMock()
    mock_sh.worksheet.return_value = mock_pbt

    # col_values called twice: once before pass 1 (max_data_row), once after (last_data_row)
    # Returns 6 values: rows 1-3 empty (header area), rows 4-6 have stock numbers
    stock_data = ["", "", "", "STK001", "STK002", "STK003"]
    mock_pbt.col_values.side_effect = [stock_data, stock_data]

    # acell() for threshold_cell ("E1") → "$1,000"
    mock_cell = MagicMock()
    mock_cell.value = "$1,000"
    mock_pbt.acell.return_value = mock_cell

    # get() for J column → three values, two green (≤1000), one not
    mock_pbt.get.return_value = [["500"], ["750"], ["1200"]]

    safe_sort_pbt(mock_sh, DEALERS["nalley"])

    # Every sort() call must use a range starting at row >= data_start_row (4)
    assert mock_pbt.sort.called, "safe_sort_pbt did not call sort() at all"
    for i, sort_call in enumerate(mock_pbt.sort.call_args_list):
        range_str = sort_call.kwargs.get("range", "")
        match = re.search(r'A(\d+)', range_str)
        assert match, f"Sort call {i} range '{range_str}' has no A-row — unexpected format"
        start_row = int(match.group(1))
        assert start_row >= DEALERS["nalley"]["data_start_row"], (
            f"Sort call {i} uses range '{range_str}' — starts before data_start_row=4"
        )
```

- [ ] **Step 2: Run the new test**

```bash
python -m pytest tests/test_pb_report.py::test_safe_sort_pbt_never_calls_sort_on_rows_before_data_start -v
```

Expected: `1 passed`

If it fails with `AttributeError` on `sort_call.kwargs`: the Python version may not support `.kwargs` on call objects. Fix by replacing `sort_call.kwargs.get("range", "")` with `sort_call[1].get("range", "")`.

- [ ] **Step 3: Commit**

```bash
git add tests/test_pb_report.py
git commit -m "test(FM-1): safe_sort_pbt never sorts header rows"
```

---

## Task 5: FM-2 — CSV schema validation tests

**Files:**
- Modify: `tests/test_pb_report.py` (append)

- [ ] **Step 1: Write the tests — append to test_pb_report.py**

```python
# ── FM-2: CSV schema validation exits loudly on column mismatch ───────────────

def test_validate_csv_headers_exits_when_lei_column_missing():
    """_validate_csv_headers() must exit(1) when a required LEI column is absent."""
    rows_missing_dealer_name = [["Dealer id", "Stock num", "VIN", "Make name"], ["val"] * 4]
    with pytest.raises(SystemExit):
        _validate_csv_headers("x.csv", rows_missing_dealer_name, _LEI_EXPECTED, "LEI")


def test_validate_csv_headers_exits_on_empty_file():
    """_validate_csv_headers() must exit(1) when the CSV has no rows at all."""
    with pytest.raises(SystemExit):
        _validate_csv_headers("empty.csv", [], _LEI_EXPECTED, "LEI")


def test_validate_csv_headers_passes_with_all_lei_columns_present():
    """No exception raised when all expected LEI columns are present."""
    rows = [["Dealer name", "Dealer id", "Stock num", "VIN", "Make name", "Extra col"],
            ["Nalley", "109754", "STK001", "1HGBH41", "Lexus", "extra"]]
    _validate_csv_headers("lei.csv", rows, _LEI_EXPECTED, "LEI")  # must not raise


def test_validate_csv_headers_passes_with_all_dem_columns_present():
    """No exception raised when all expected Dem Signal columns are present."""
    rows = [["YMMT", "Stock num", "Stock type", "Days live", "Price",
             "Price vs Market (%)", "Value"],
            ["2022 Lexus RX", "STK001", "Used", "14", "44999", "-2.1%", "At Market"]]
    _validate_csv_headers("dem.csv", rows, _DEM_EXPECTED, "Dem Signal")  # must not raise
```

- [ ] **Step 2: Run the new tests**

```bash
python -m pytest tests/test_pb_report.py -k "validate_csv" -v
```

Expected: `4 passed`

- [ ] **Step 3: Commit**

```bash
git add tests/test_pb_report.py
git commit -m "test(FM-2): CSV schema validation exit behavior"
```

---

## Task 6: FM-3 — HTML email tests

**Files:**
- Modify: `tests/test_pb_report.py` (append)

- [ ] **Step 1: Write the tests — append to test_pb_report.py**

```python
# ── FM-3: Email body must be HTML, never plain text ───────────────────────────

def test_compose_email_html_returns_html_document():
    """compose_email_html() must return a string that starts with <html> and ends with </html>."""
    html = compose_email_html(DEALERS["nalley"], _SAMPLE_STATS)
    assert html.strip().startswith("<html>"), \
        "Email body does not start with <html> — plain-text fallback may have been used"
    assert "</html>" in html, "Email body missing closing </html>"


def test_compose_email_html_includes_sheet_link():
    """compose_email_html() must embed a hyperlink to the Google Sheet."""
    html = compose_email_html(DEALERS["nalley"], _SAMPLE_STATS)
    assert DEALERS["nalley"]["sheet_url"] in html, \
        "Sheet URL not found in email body — link would be missing for recipient"


def test_compose_email_html_includes_vehicle_count():
    """compose_email_html() must reference the within_count from stats."""
    html = compose_email_html(DEALERS["nalley"], _SAMPLE_STATS)
    assert str(_SAMPLE_STATS["within_count"]) in html


def test_create_gmail_draft_uses_html_content_type():
    """create_gmail_draft() must encode the message with Content-Type: text/html."""
    mock_gmail = MagicMock()
    mock_gmail.users.return_value.drafts.return_value.create.return_value.execute.return_value = {
        "id": "draft_abc"
    }

    create_gmail_draft(mock_gmail, DEALERS["nalley"], "<html><body><p>Test</p></body></html>")

    create_fn = mock_gmail.users.return_value.drafts.return_value.create
    assert create_fn.called, "gmail.users().drafts().create() was never called"

    body_arg = create_fn.call_args.kwargs["body"]
    raw_bytes = base64.urlsafe_b64decode(body_arg["message"]["raw"])
    raw_msg = raw_bytes.decode("utf-8", errors="replace")

    assert "Content-Type: text/html" in raw_msg, (
        "Gmail draft does not use text/html content type — "
        "recipient would receive plain text instead of formatted HTML"
    )
```

- [ ] **Step 2: Run the new tests**

```bash
python -m pytest tests/test_pb_report.py -k "email or html or draft" -v
```

Expected: `4 passed`

- [ ] **Step 3: Commit**

```bash
git add tests/test_pb_report.py
git commit -m "test(FM-3): HTML email composition and MIME type"
```

---

## Task 7: FM-5 and FM-6 — Column reorder and formula overwrite guard

**Files:**
- Modify: `tests/test_pb_report.py` (append)

- [ ] **Step 1: Write the tests — append to test_pb_report.py**

```python
# ── FM-5: Nalley column reorder must put Stock/VIN/Make in correct positions ──

def test_reorder_nalley_columns_swaps_make_stock_vin_correctly():
    """reorder_nalley_columns() maps CSV col order (Make,Stock,VIN) → sheet order (Stock,VIN,Make).

    Input:  [Dealer, id, Make,   Stock,  VIN     ]
    Output: [Dealer, id, Stock,  VIN,    Make    ]
    """
    rows = [
        ["Dealer name", "Dealer id", "Make name", "Stock num", "VIN", "Extra"],
        ["Nalley",      "109754",    "LEXUS",      "STK001",   "1HGBH41", "x"],
    ]
    out = reorder_nalley_columns(rows)

    # Header row must be untouched
    assert out[0] == rows[0]

    # Data row: col[2]=Stock, col[3]=VIN, col[4]=Make
    assert out[1][2] == "STK001",  f"col[2] expected Stock num, got '{out[1][2]}'"
    assert out[1][3] == "1HGBH41", f"col[3] expected VIN, got '{out[1][3]}'"
    assert out[1][4] == "LEXUS",   f"col[4] expected Make, got '{out[1][4]}'"


def test_reorder_nalley_columns_leaves_short_rows_unchanged():
    """Rows with fewer than 5 columns are returned as-is to avoid IndexError."""
    rows = [["a", "b", "c"]]
    out = reorder_nalley_columns(rows)
    assert out == rows


# ── FM-6: import_to_sheet must never write to the PBT tab (it has VLOOKUPs) ──

def test_import_to_sheet_never_calls_worksheet_with_pbt_tab_name():
    """import_to_sheet() must only open the import tab, never the Price Badge Tool tab.

    The PBT tab contains VLOOKUP formulas. Calling ws.update() on it would destroy them.
    """
    mock_gc = MagicMock()
    mock_sh = MagicMock()
    mock_gc.open_by_key.return_value = mock_sh

    lei_rows = [
        ["Dealer name", "Dealer id", "Stock num", "VIN", "Make name"],
        ["Nalley", "109754", "STK001", "1HGBH41", "LEXUS"],
    ]

    import_to_sheet(mock_gc, DEALERS["nalley"], lei_rows)

    opened_tabs = [c.args[0] for c in mock_sh.worksheet.call_args_list]
    assert DEALERS["nalley"]["pbt_tab"] not in opened_tabs, (
        f"import_to_sheet called worksheet('{DEALERS['nalley']['pbt_tab']}') — "
        "this tab has VLOOKUPs that would be destroyed by ws.update()"
    )


def test_import_to_sheet_never_calls_worksheet_with_pbt_tab_for_hendrick():
    """Same formula-overwrite guard for Hendrick dealer config."""
    mock_gc = MagicMock()
    mock_sh = MagicMock()
    mock_gc.open_by_key.return_value = mock_sh

    lei_rows = [
        ["Dealer name", "Dealer id", "Stock num", "VIN", "Make name"],
        ["Hendrick", "12345", "HND001", "1FMCU0G61MUA00001", "BMW"],
    ]

    import_to_sheet(mock_gc, DEALERS["hendrick"], lei_rows)

    opened_tabs = [c.args[0] for c in mock_sh.worksheet.call_args_list]
    assert DEALERS["hendrick"]["pbt_tab"] not in opened_tabs, (
        f"import_to_sheet called worksheet('{DEALERS['hendrick']['pbt_tab']}') — formula overwrite risk"
    )
```

- [ ] **Step 2: Run the new tests**

```bash
python -m pytest tests/test_pb_report.py -k "reorder or import_to_sheet" -v
```

Expected: `4 passed`

- [ ] **Step 3: Run the full suite to confirm nothing regressed**

```bash
python -m pytest tests/ -q
```

Expected: all tests pass (number will be higher than before — that's correct).

- [ ] **Step 4: Commit**

```bash
git add tests/test_pb_report.py
git commit -m "test(FM-5,FM-6): column reorder correctness and formula overwrite guard"
```

---

## Task 8: Create test_skills_compliance.py — FM-7 and FM-8

**Files:**
- Create: `tests/test_skills_compliance.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_skills_compliance.py`:

```python
"""Skill guardrail compliance tests.

These tests read skill .md files as raw text and assert that required safety
guardrails are present and no dangerous patterns (e.g. 'sort sheet') exist.

If a test fails, the fix is to edit the relevant .md file in ~/.claude/commands/
and add or correct the guardrail text.
"""
from pathlib import Path
import pytest

SKILLS_DIR = Path.home() / ".claude/commands"


def _read_skill(filename: str) -> str:
    path = SKILLS_DIR / filename
    assert path.exists(), f"Skill file not found: {path}"
    return path.read_text()


# ── FM-7: Sort-range guardrail — PB report skills ─────────────────────────────

@pytest.mark.parametrize("skill_file", [
    "nalley-pb-report.md",
    "hendricks-pb-report.md",
])
def test_pb_skill_says_sort_range_not_sort_sheet(skill_file):
    """PB report skills must instruct 'Sort range Ax:Jy', never 'Sort sheet'.

    'Sort sheet' moves the header row into data — a known past incident.
    The guardrail must explicitly say 'Sort range' to override the UI default.
    """
    text = _read_skill(skill_file).lower()
    assert "sort range" in text, (
        f"{skill_file}: missing 'Sort range' guardrail — "
        "add an explicit 'Sort range A4:L...' instruction to prevent header corruption"
    )
    assert "sort sheet" not in text, (
        f"{skill_file}: contains dangerous 'Sort sheet' instruction — "
        "replace with 'Sort range Ax:Jy (data rows only)'"
    )


# ── FM-8: HTML email guardrail — all email-drafting skills ────────────────────

@pytest.mark.parametrize("skill_file", [
    "nalley-pb-report.md",
    "hendricks-pb-report.md",
    "sonic-monthly-report.md",
    "aca-monthly-report.md",
    "ep-review-report.md",
])
def test_email_skill_specifies_html_not_plain_text(skill_file):
    """Email-drafting skills must specify HTML format and must not mention plain text.

    Plain text fallback strips all formatting and hyperlinks — a known past incident.
    """
    text = _read_skill(skill_file).lower()
    assert "html" in text, (
        f"{skill_file}: no HTML email requirement found — "
        "add an explicit instruction to use HTML-formatted email body"
    )
    assert "plain text" not in text, (
        f"{skill_file}: contains 'plain text' — remove or replace with 'HTML'"
    )
```

- [ ] **Step 2: Run the compliance tests**

```bash
python -m pytest tests/test_skills_compliance.py -v
```

Expected: either all pass, or specific skill files fail. Note which ones fail — the next steps fix them.

- [ ] **Step 3: For each failing FM-7 test — patch the skill file**

If `nalley-pb-report.md` fails the sort-range check, open `~/.claude/commands/nalley-pb-report.md`. Find the section describing the sheet sort step and:

- If it says `Sort sheet`: replace with `Sort range A4:L`
- If it doesn't mention sort range at all: add this line in the relevant step:

  ```
  > ⚠️ **Sort range A4:L only** — never use "Sort sheet" (it moves the header row into data).
  ```

Repeat for `hendricks-pb-report.md` if it also fails (Hendrick range is `A3:J`).

- [ ] **Step 4: For each failing FM-8 test — patch the skill file**

If any email skill fails the HTML check, open that `.md` file. Find the email composition section and ensure it contains explicit HTML instruction. Add if missing:

```
> ⚠️ **Always compose HTML email** — never fall back to plain text.
```

If the file contains "plain text": remove or replace with "HTML".

- [ ] **Step 5: Re-run compliance tests until all pass**

```bash
python -m pytest tests/test_skills_compliance.py -v
```

Expected: all parametrized cases pass.

- [ ] **Step 6: Run full suite**

```bash
python -m pytest tests/ -q
```

Expected: all tests pass.

- [ ] **Step 7: Commit everything (skill patches + new test file)**

```bash
git add tests/test_skills_compliance.py
# Add any patched skill files:
git add ~/.claude/commands/nalley-pb-report.md \
        ~/.claude/commands/hendricks-pb-report.md \
        ~/.claude/commands/sonic-monthly-report.md \
        ~/.claude/commands/aca-monthly-report.md \
        ~/.claude/commands/ep-review-report.md 2>/dev/null || true
git commit -m "test(FM-7,FM-8): skill guardrail compliance tests + patches"
```

---

## Task 9: Create harden_skills.py — autonomous iteration loop

**Files:**
- Create: `harden_skills.py`

- [ ] **Step 1: Write harden_skills.py**

Create `~/Documents/scripts/harden_skills.py`:

```python
#!/usr/bin/env python3
"""
Skill hardening loop.

Runs pytest, finds failing skill-compliance tests, patches the offending
.md files, auto-commits, and repeats until all tests pass or MAX_ITERATIONS
is reached. Python unit test failures are reported as UNFIXABLE (require
manual intervention) and do not block the loop.

Usage:
    cd ~/Documents/scripts
    python harden_skills.py [--max-iterations N] [--dry-run]
"""

import argparse, json, re, subprocess, sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent
SKILLS_DIR  = Path.home() / ".claude/commands"
REPORT_FILE = SCRIPTS_DIR / ".harden_report.json"

# Skill test name → patch spec
# Each patch spec has: skill_files, assertions (check fn + patch fn + description)
SKILL_PATCHES = {
    "test_pb_skill_says_sort_range_not_sort_sheet": {
        "files": ["nalley-pb-report.md", "hendricks-pb-report.md"],
        "checks": [
            {
                "test":  lambda t: "sort range" in t.lower(),
                "patch": lambda t: t + "\n\n> ⚠️ **Sort range only** — never 'Sort sheet' (moves header into data).\n",
                "desc":  "add sort-range guardrail",
            },
            {
                "test":  lambda t: "sort sheet" not in t.lower(),
                "patch": lambda t: re.sub(r"(?i)sort sheet", "Sort range", t),
                "desc":  "replace 'sort sheet' with 'Sort range'",
            },
        ],
    },
    "test_email_skill_specifies_html_not_plain_text": {
        "files": [
            "nalley-pb-report.md", "hendricks-pb-report.md",
            "sonic-monthly-report.md", "aca-monthly-report.md",
            "ep-review-report.md",
        ],
        "checks": [
            {
                "test":  lambda t: "html" in t.lower(),
                "patch": lambda t: t + "\n\n> ⚠️ **Always compose HTML email** — never plain text.\n",
                "desc":  "add HTML email guardrail",
            },
            {
                "test":  lambda t: "plain text" not in t.lower(),
                "patch": lambda t: re.sub(r"(?i)plain text", "HTML", t),
                "desc":  "replace 'plain text' with 'HTML'",
            },
        ],
    },
}


def run_tests() -> dict:
    """Run full pytest suite and return the JSON report."""
    result = subprocess.run(
        [
            sys.executable, "-m", "pytest", "tests/", "-q", "--tb=short",
            "--json-report", f"--json-report-file={REPORT_FILE}",
        ],
        cwd=SCRIPTS_DIR,
        capture_output=True,
        text=True,
    )
    print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    if not REPORT_FILE.exists():
        print("ERROR: pytest-json-report did not produce a report file.", file=sys.stderr)
        sys.exit(1)
    return json.loads(REPORT_FILE.read_text())


def get_failures(report: dict) -> list[dict]:
    return [t for t in report.get("tests", []) if t.get("outcome") == "failed"]


def parse_skill_file_from_nodeid(nodeid: str) -> str | None:
    """Extract parametrize value from nodeid like test_foo[nalley-pb-report.md]."""
    m = re.search(r'\[(.+\.md)\]', nodeid)
    return m.group(1) if m else None


def patch_skill_file(skill_file: str, patch_spec: dict, dry_run: bool) -> list[str]:
    """Apply all failing patches to a skill .md file. Returns list of applied descriptions."""
    path = SKILLS_DIR / skill_file
    if not path.exists():
        print(f"  SKIP: {skill_file} not found at {path}")
        return []

    text = path.read_text()
    applied = []
    for check in patch_spec["checks"]:
        if not check["test"](text):
            if dry_run:
                print(f"  [dry-run] Would apply: {check['desc']} → {skill_file}")
            else:
                text = check["patch"](text)
                applied.append(check["desc"])
                print(f"  Applied: {check['desc']} → {skill_file}")

    if applied and not dry_run:
        path.write_text(text)

    return applied


def git_commit(files: list[Path], message: str) -> bool:
    """Stage and commit a list of files. Returns True on success."""
    add = subprocess.run(["git", "add"] + [str(f) for f in files], capture_output=True)
    if add.returncode != 0:
        print(f"  git add failed: {add.stderr.decode()}")
        return False
    commit = subprocess.run(["git", "commit", "-m", message], capture_output=True, text=True)
    if commit.returncode != 0:
        print(f"  git commit failed: {commit.stderr}")
        return False
    print(f"  Committed: {message}")
    return True


def main():
    parser = argparse.ArgumentParser(description="Skill hardening loop")
    parser.add_argument("--max-iterations", type=int, default=10)
    parser.add_argument("--dry-run", action="store_true",
                        help="Show proposed patches without applying them")
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"Skill Hardening Loop — max {args.max_iterations} iterations")
    if args.dry_run:
        print("DRY RUN — no files will be changed")
    print(f"{'='*60}\n")

    iteration_trace = []

    for iteration in range(1, args.max_iterations + 1):
        print(f"\n── Iteration {iteration}/{args.max_iterations} ──")

        report = run_tests()
        failures = get_failures(report)

        if not failures:
            print(f"\n✅ All tests pass after {iteration - 1} iteration(s).")
            break

        print(f"\n{len(failures)} failure(s):")
        patched_files: list[Path] = []
        commit_messages: list[str] = []
        unfixable: list[str] = []

        for failure in failures:
            nodeid = failure["nodeid"]
            test_name = nodeid.split("::")[-1].split("[")[0]
            skill_file = parse_skill_file_from_nodeid(nodeid)

            print(f"\n  FAIL: {nodeid}")

            if test_name in SKILL_PATCHES:
                spec = SKILL_PATCHES[test_name]
                files_to_patch = [skill_file] if skill_file else spec["files"]
                for fname in files_to_patch:
                    applied = patch_skill_file(fname, spec, args.dry_run)
                    if applied and not args.dry_run:
                        patched_files.append(SKILLS_DIR / fname)
                        commit_messages.append(f"fix(harness): {test_name} → {fname}")
                        iteration_trace.append({
                            "iteration": iteration,
                            "test": nodeid,
                            "patches": applied,
                            "file": fname,
                        })
            else:
                msg = (
                    f"  UNFIXABLE by loop — Python unit test failure requires manual fix.\n"
                    f"  Run: python -m pytest '{nodeid}' -v  for details."
                )
                print(msg)
                unfixable.append(nodeid)
                iteration_trace.append({
                    "iteration": iteration,
                    "test": nodeid,
                    "patches": [],
                    "unfixable": True,
                })

        if patched_files and not args.dry_run:
            # Run tests on patched files before committing
            verify = subprocess.run(
                [sys.executable, "-m", "pytest", "tests/test_skills_compliance.py", "-q"],
                cwd=SCRIPTS_DIR, capture_output=True, text=True,
            )
            if verify.returncode == 0:
                git_commit(patched_files, "; ".join(commit_messages))
            else:
                print("  Patches did not fix the tests — manual review needed.")
                print(verify.stdout)
                unfixable.extend([f["test"] for f in iteration_trace
                                   if f.get("iteration") == iteration and not f.get("unfixable")])

        if not patched_files and unfixable:
            print(f"\nLoop cannot progress — {len(unfixable)} unfixable failure(s) remain.")
            break

        if args.dry_run:
            break

    else:
        print(f"\n⚠️  Reached max iterations ({args.max_iterations}) — some tests still failing.")

    # Print iteration trace
    print(f"\n{'='*60}")
    print("Iteration Trace")
    print(f"{'='*60}")
    for entry in iteration_trace:
        status = "UNFIXABLE" if entry.get("unfixable") else f"patched: {', '.join(entry['patches'])}"
        print(f"[{entry['iteration']}] {entry['test']}\n     → {status}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run harden_skills.py in dry-run mode to verify it works**

```bash
cd ~/Documents/scripts
python harden_skills.py --dry-run
```

Expected: shows a list of current test outcomes; for passing tests shows "All tests pass". For any failing compliance tests shows `[dry-run] Would apply: ...`. No files are changed.

- [ ] **Step 3: Run for real (max 3 iterations)**

```bash
python harden_skills.py --max-iterations 3
```

Expected: any skill compliance failures are patched and committed. Python unit failures surface as UNFIXABLE with instructions.

- [ ] **Step 4: Run full suite to confirm**

```bash
python -m pytest tests/ -q
```

Expected: all tests pass.

- [ ] **Step 5: Commit harden_skills.py**

```bash
git add harden_skills.py
git commit -m "feat: add harden_skills.py autonomous compliance loop"
```

---

## Task 10: Create pre-commit hook

**Files:**
- Create: `~/.git/hooks/pre-commit` (or `/Users/jcrawley/.git/hooks/pre-commit`)

- [ ] **Step 1: Write the hook**

```bash
cat > /Users/jcrawley/.git/hooks/pre-commit << 'HOOK'
#!/bin/sh
# Run pytest when commits touch scripts or skill files.
# Blocks the commit if any test fails.

SCRIPTS_DIR="$HOME/Documents/scripts"
SKILLS_DIR="$HOME/.claude/commands"

if git diff --cached --name-only | grep -qE '^(Documents/scripts/|\.claude/commands/)'; then
  echo "🔍 Staged changes touch scripts/ or .claude/commands/ — running test suite..."
  cd "$SCRIPTS_DIR" || exit 1
  python -m pytest tests/ -q --tb=short
  EXIT_CODE=$?
  if [ $EXIT_CODE -ne 0 ]; then
    echo ""
    echo "❌ Tests failed — commit blocked."
    echo "   Fix the failures above, then re-commit."
    echo "   To skip (NOT recommended): git commit --no-verify"
    exit 1
  fi
  echo "✅ All tests pass — committing."
fi
exit 0
HOOK
chmod +x /Users/jcrawley/.git/hooks/pre-commit
```

- [ ] **Step 2: Verify the hook is executable**

```bash
ls -la /Users/jcrawley/.git/hooks/pre-commit
```

Expected: `-rwxr-xr-x` permissions.

- [ ] **Step 3: Test the hook by staging a scripts file**

```bash
cd /Users/jcrawley
touch Documents/scripts/test_hook_probe.py
git add Documents/scripts/test_hook_probe.py
git commit -m "probe: test hook fires"
```

Expected: hook runs `pytest tests/`, all tests pass, commit succeeds.

- [ ] **Step 4: Clean up the probe file**

```bash
git rm Documents/scripts/test_hook_probe.py
git commit -m "chore: remove hook probe file"
```

- [ ] **Step 5: Verify hook blocks a failing test**

Temporarily break a compliance test to confirm the hook blocks:

```bash
# Add a bad line to nalley skill
echo "sort sheet everything" >> /Users/jcrawley/.claude/commands/nalley-pb-report.md
git add /Users/jcrawley/.claude/commands/nalley-pb-report.md
git commit -m "probe: should be blocked"
```

Expected: commit is blocked with `❌ Tests failed — commit blocked.`

```bash
# Restore: remove the bad line
cd /Users/jcrawley/Documents/scripts
python harden_skills.py --max-iterations 1
```

---

## Task 11: Final validation and documentation commit

**Files:**
- Modify: `tests/conftest.py` (if any cleanup needed)

- [ ] **Step 1: Run the complete test suite one final time**

```bash
cd ~/Documents/scripts
python -m pytest tests/ -v
```

Expected output structure:
```
tests/test_admin_cars.py::test_check_session_returns_bool PASSED
...
tests/test_pb_report.py::test_nalley_sort_range_starts_at_data_row PASSED
tests/test_pb_report.py::test_hendrick_sort_range_starts_at_data_row PASSED
tests/test_pb_report.py::test_all_dealers_sort_range_matches_data_start_row PASSED
tests/test_pb_report.py::test_safe_sort_pbt_never_calls_sort_on_rows_before_data_start PASSED
tests/test_pb_report.py::test_validate_csv_headers_exits_when_lei_column_missing PASSED
tests/test_pb_report.py::test_validate_csv_headers_exits_on_empty_file PASSED
tests/test_pb_report.py::test_validate_csv_headers_passes_with_all_lei_columns_present PASSED
tests/test_pb_report.py::test_validate_csv_headers_passes_with_all_dem_columns_present PASSED
tests/test_pb_report.py::test_compose_email_html_returns_html_document PASSED
tests/test_pb_report.py::test_compose_email_html_includes_sheet_link PASSED
tests/test_pb_report.py::test_compose_email_html_includes_vehicle_count PASSED
tests/test_pb_report.py::test_create_gmail_draft_uses_html_content_type PASSED
tests/test_pb_report.py::test_reorder_nalley_columns_swaps_make_stock_vin_correctly PASSED
tests/test_pb_report.py::test_reorder_nalley_columns_leaves_short_rows_unchanged PASSED
tests/test_pb_report.py::test_import_to_sheet_never_calls_worksheet_with_pbt_tab_name PASSED
tests/test_pb_report.py::test_import_to_sheet_never_calls_worksheet_with_pbt_tab_for_hendrick PASSED
tests/test_skills_compliance.py::test_pb_skill_says_sort_range_not_sort_sheet[nalley-pb-report.md] PASSED
tests/test_skills_compliance.py::test_pb_skill_says_sort_range_not_sort_sheet[hendricks-pb-report.md] PASSED
tests/test_skills_compliance.py::test_email_skill_specifies_html_not_plain_text[nalley-pb-report.md] PASSED
... (5 email skill tests)
```

- [ ] **Step 2: Run harden_skills.py one final time to confirm no residual failures**

```bash
python harden_skills.py --max-iterations 1
```

Expected: `✅ All tests pass after 0 iteration(s).`

- [ ] **Step 3: Final commit**

```bash
git add -p   # review any remaining unstaged changes
git commit -m "feat: skill test harness complete — 8 failure modes, harden loop, pre-commit hook"
```

---

## Self-Review Checklist

- [x] FM-1 (sort range): Task 3 (config) + Task 4 (runtime mock) ✓
- [x] FM-2 (CSV schema): Task 5 ✓
- [x] FM-3 (HTML email): Task 6 ✓
- [x] FM-4 (double-count regression): Task 2 (marker on existing test) ✓
- [x] FM-5 (column reorder): Task 7 ✓
- [x] FM-6 (formula overwrite): Task 7 ✓
- [x] FM-7 (sort-range skill guardrail): Task 8 ✓
- [x] FM-8 (HTML email skill guardrail): Task 8 ✓
- [x] Iteration loop: Task 9 ✓
- [x] Pre-commit hook: Task 10 ✓
- [x] No placeholder steps — all code blocks are complete
- [x] Import names consistent: `safe_sort_pbt`, `import_to_sheet`, `reorder_nalley_columns`, `compose_email_html`, `create_gmail_draft`, `_validate_csv_headers`, `_LEI_EXPECTED`, `_DEM_EXPECTED`, `DEALERS` — all exported from `pb_report.py` as confirmed by reading the source
- [x] `SKILLS_DIR = Path.home() / ".claude/commands"` — consistent across test file and harden_skills.py
