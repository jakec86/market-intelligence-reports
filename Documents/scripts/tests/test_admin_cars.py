from unittest.mock import patch, MagicMock
import admin_cars


def test_check_session_returns_bool():
    """check_session() must return a bool — True (connected) or False (expired)."""
    with patch("admin_cars._get_context") as mock_ctx:
        mock_page = MagicMock()
        mock_page.url = "https://admin.cars.com/dealers"
        mock_ctx.return_value.__enter__ = lambda s: MagicMock(new_page=lambda: mock_page)
        mock_ctx.return_value.__exit__ = MagicMock(return_value=False)
        result = admin_cars.check_session()
    assert isinstance(result, bool)


def test_check_session_returns_false_when_redirected_off_admin_cars():
    """check_session() returns False for any non-admin.cars.com URL (SSO, policy denial, etc.)."""
    for url in (
        "https://sso.jumpcloud.com/saml2/tableau",
        "https://console.jumpcloud.com/userconsole#/?error=policyDenial",
        "https://console.jumpcloud.com/login",
    ):
        with patch("admin_cars._get_context") as mock_ctx:
            mock_page = MagicMock()
            mock_page.url = url
            mock_ctx.return_value.__enter__ = lambda s: MagicMock(new_page=lambda: mock_page)
            mock_ctx.return_value.__exit__ = MagicMock(return_value=False)
            assert admin_cars.check_session() is False, f"expected False for {url}"


def test_resolve_uuid_extracts_uuid_from_html():
    """resolve_uuid() parses UUID from admin.cars.com dealer search HTML."""
    sample_html = """
    <a href="/dealers/156f9bb7-3c44-549c-b16b-0c3af73fdb1f/reports/performance_trends">
      Nalley Lexus Galleria
    </a>
    """
    result = admin_cars._extract_uuid_from_html(sample_html)
    assert result == "156f9bb7-3c44-549c-b16b-0c3af73fdb1f"


def test_resolve_uuid_returns_none_when_not_found():
    result = admin_cars._extract_uuid_from_html("<html>no uuid here</html>")
    assert result is None


def test_resolve_uuid_on_returns_none_when_redirected_off_admin_cars():
    """_resolve_uuid_on() returns None when the search page redirects off admin.cars.com."""
    mock_page = MagicMock()
    mock_page.url = "https://console.jumpcloud.com/userconsole#/?error=policyDenial"
    mock_page.content.return_value = "<html>denied</html>"
    assert admin_cars._resolve_uuid_on(mock_page, "109754") is None


def test_resolve_uuid_on_returns_uuid_from_valid_page():
    """_resolve_uuid_on() extracts the UUID when admin.cars.com responds normally."""
    mock_page = MagicMock()
    mock_page.url = "https://admin.cars.com/dealers/all/reports?query=109754"
    mock_page.content.return_value = (
        '<a href="/dealers/156f9bb7-3c44-549c-b16b-0c3af73fdb1f/reports/performance_trends">'
        'Nalley Lexus Galleria</a>'
    )
    assert admin_cars._resolve_uuid_on(mock_page, "109754") == "156f9bb7-3c44-549c-b16b-0c3af73fdb1f"


def test_parse_kpi_value_strips_currency_and_percent():
    """_parse_kpi() converts '$1,234', '12.5%', '1234' to floats."""
    assert admin_cars._parse_kpi("$1,234") == 1234.0
    assert admin_cars._parse_kpi("12.5%") == 12.5
    assert admin_cars._parse_kpi("1,234") == 1234.0
    assert admin_cars._parse_kpi("N/A") is None
    assert admin_cars._parse_kpi("") is None


# Fixtures captured from a live smoke test against Nalley Lexus Galleria (UUID 156f9bb7…) on 2026-04-24.
# Each entry is (cols, rows) matching what getSummaryDataAsync returns.
# Used to catch regressions if admin.cars.com renames worksheet columns.

_PERF_AVG_INVENTORY_KPI = (
    ["AGG(Vehicles MoM % (down))", "AGG(Vehicles MoM % (up))", "AGG(Vehicles MoM %)", "SUM(Vehicles Selected Month)"],
    [["", "▲", "22.0%", "494"]],
)
_PERF_VDPS_KPI = (
    ["AGG(VDPs MoM (down))", "AGG(VDPs MoM (up))", "AGG(VDPs MoM)", "SUM(VDPs Selected Month)"],
    [["", "▲", "0.0107794", "10,596"]],
)
_PERF_CONNECTIONS_KPI = (
    ["AGG(Total Leads MoM (down))", "AGG(Total Leads MoM (up))", "AGG(Total Leads MoM)", "SUM(Total Leads Selected Month)"],
    [["▼", "", "-7.0%", "319"]],
)

_REP_DEALER_KPI_COLS = ["'1'", "'1'", "AVG(Cars.com)", "AVG(Total Number of Reviews)"]
_REP_DEALER_KPI_ROW = ["1", "1", "4.8", "911"]
_REP_MARKET_KPI_COLS = ["AVG(National OEM Average)", "AVG(Your Market Average DMA)"]
_REP_MARKET_KPI_ROW = ["4.8", "4.6"]
_REP_PRICING_KPI_COLS = ["AVG(Pricing Transparency DMA AVG Rating)", "AVG(Pricing Transparency)"]
_REP_PRICING_KPI_ROW = ["4.7", "4.8"]


def test_extract_kpi_avg_inventory_percent_delta():
    """Delta formatted as '22.0%' must parse to 22.0 (not multiplied by 100)."""
    cols, rows = _PERF_AVG_INVENTORY_KPI
    kpi = admin_cars._extract_kpi(cols, rows)
    assert kpi["cp"] == 494.0
    assert kpi["delta_pct"] == 22.0


def test_extract_kpi_vdps_decimal_delta_scales_to_percent():
    """Delta formatted as raw decimal '0.0107794' must scale to ~1.08% (multiplied by 100)."""
    cols, rows = _PERF_VDPS_KPI
    kpi = admin_cars._extract_kpi(cols, rows)
    assert kpi["cp"] == 10596.0
    assert abs(kpi["delta_pct"] - 1.07794) < 0.001


def test_extract_kpi_connections_negative_delta():
    """Delta formatted as '-7.0%' must parse to -7.0."""
    cols, rows = _PERF_CONNECTIONS_KPI
    kpi = admin_cars._extract_kpi(cols, rows)
    assert kpi["cp"] == 319.0
    assert kpi["delta_pct"] == -7.0


def test_extract_kpi_handles_empty_rows():
    """Empty worksheet returns {cp: None, delta_pct: None} rather than raising."""
    kpi = admin_cars._extract_kpi(["col1", "col2"], [])
    assert kpi == {"cp": None, "delta_pct": None}


def test_find_val_matches_keyword_case_insensitively():
    """_find_val finds the first column containing the keyword."""
    rating = admin_cars._find_val(_REP_DEALER_KPI_COLS, _REP_DEALER_KPI_ROW, "cars.com")
    assert rating == 4.8
    reviews = admin_cars._find_val(_REP_DEALER_KPI_COLS, _REP_DEALER_KPI_ROW, "number of reviews")
    assert reviews == 911.0


def test_find_val_returns_none_when_no_match():
    result = admin_cars._find_val(["Col A", "Col B"], ["1", "2"], "nonexistent")
    assert result is None


def test_find_val_matches_dma_and_national_distinctly():
    """Market KPI worksheet has both DMA avg and national avg — they're different columns."""
    dma = admin_cars._find_val(_REP_MARKET_KPI_COLS, _REP_MARKET_KPI_ROW, "market average")
    national = admin_cars._find_val(_REP_MARKET_KPI_COLS, _REP_MARKET_KPI_ROW, "national oem")
    assert dma == 4.6
    assert national == 4.8


def test_pricing_kpi_exclude_dma_picks_dealer_value():
    """The 'exclude' arg on the reputation get() helper should skip DMA variant of a metric.

    Pricing KPI has two columns — 'AVG(Pricing Transparency DMA AVG Rating)' (4.7) and
    'AVG(Pricing Transparency)' (4.8). Without exclude, first match wins (the DMA col).
    With exclude='dma', we should get 4.8 (the dealer's own value).
    """
    # Without exclude — picks DMA column (4.7) because it's first
    dma_match = admin_cars._find_val(_REP_PRICING_KPI_COLS, _REP_PRICING_KPI_ROW, "pricing transparency")
    assert dma_match == 4.7
    # The reputation get() closure uses an explicit exclude — simulate that behavior
    kw = "pricing transparency"
    ex = "dma"
    dealer_val = None
    for col, val in zip(_REP_PRICING_KPI_COLS, _REP_PRICING_KPI_ROW):
        c = col.lower()
        if kw in c and ex not in c:
            dealer_val = admin_cars._parse_kpi(val)
            break
    assert dealer_val == 4.8
