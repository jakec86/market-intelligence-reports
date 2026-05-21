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
    "at_threshold_vehicles": [{"mmyt": "2022 Lexus RX 350", "diff": "$0", "current": "Good", "next": "Great", "sam": "Jake C.", "vehicle": "2022 Lexus RX 350", "stock": "STK001"}],
    "already_great": 2,
    "top_vehicles": [
        {"mmyt": "2021 Lexus ES 350", "diff": "$499", "current": "Fair", "next": "Good", "sam": "Jake C.", "vehicle": "2021 Lexus ES 350", "stock": "STK002"},
        {"mmyt": "2020 Lexus NX 300", "diff": "$750", "current": "Not Badged", "next": "Fair", "sam": "Jake C.", "vehicle": "2020 Lexus NX 300", "stock": "STK003"},
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


# ── FM-1 runtime: safe_sort_pbt must never sort before data_start_row ─────────

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

    # acell() for threshold_cell ("E1") -> "$1,000"
    mock_cell = MagicMock()
    mock_cell.value = "$1,000"
    mock_pbt.acell.return_value = mock_cell

    # get() for J column -> three values, two green (<=1000), one not
    mock_pbt.get.return_value = [["500"], ["750"], ["1200"]]

    safe_sort_pbt(mock_sh, DEALERS["nalley"])

    # Every sort() call must use a range starting at row >= data_start_row (4)
    assert mock_pbt.sort.called, "safe_sort_pbt did not call sort() at all"
    for i, sort_call in enumerate(mock_pbt.sort.call_args_list):
        # sort() called as ws.sort(spec, range=range_str) — range is a keyword arg
        range_str = sort_call[1].get("range", "")
        match = re.search(r'A(\d+)', range_str)
        assert match, f"Sort call {i} range '{range_str}' has no A-row — unexpected format"
        start_row = int(match.group(1))
        assert start_row >= DEALERS["nalley"]["data_start_row"], (
            f"Sort call {i} uses range '{range_str}' — starts before data_start_row=4"
        )


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

    body_arg = create_fn.call_args[1]["body"]
    raw_bytes = base64.urlsafe_b64decode(body_arg["message"]["raw"])
    raw_msg = raw_bytes.decode("utf-8", errors="replace")

    assert "Content-Type: text/html" in raw_msg, (
        "Gmail draft does not use text/html content type — "
        "recipient would receive plain text instead of formatted HTML"
    )


# ── FM-5: Nalley column reorder must put Stock/VIN/Make in correct positions ──

def test_reorder_nalley_columns_swaps_make_stock_vin_correctly():
    """reorder_nalley_columns() maps CSV col order (Make,Stock,VIN) -> sheet order (Stock,VIN,Make).

    Input:  [Dealer, id, Make,   Stock,  VIN     ]
    Output: [Dealer, id, Stock,  VIN,    Make    ]

    The function applies the swap to every row with >= 5 columns (including the header).
    """
    rows = [
        ["Dealer name", "Dealer id", "Make name", "Stock num", "VIN", "Extra"],
        ["Nalley",      "109754",    "LEXUS",      "STK001",   "1HGBH41", "x"],
    ]
    out = reorder_nalley_columns(rows)

    # Header row: same swap applies — col[2]=Stock num, col[3]=VIN, col[4]=Make name
    assert out[0][2] == "Stock num",  f"header col[2] expected 'Stock num', got '{out[0][2]}'"
    assert out[0][3] == "VIN",        f"header col[3] expected 'VIN', got '{out[0][3]}'"
    assert out[0][4] == "Make name",  f"header col[4] expected 'Make name', got '{out[0][4]}'"

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
