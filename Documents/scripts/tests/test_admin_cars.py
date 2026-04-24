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


# ═══ Fixture-based parser tests for the newer fetchers ═══
# All fixtures captured from a live smoke run against Land Rover Newport Beach
# (UUID 217494e4-…, CCID 6071013) on 2026-04-24. Locks in parser behavior so a
# Cars.com worksheet-column rename produces a loud test failure instead of a
# silent wrong number in a dealer email.


# ── Listings Optimizer ──────────────────────────────────────────────────────

_LO_BADGE_DETAILS = {
    "cols": [
        "Price badge", "FALSE", "TRUE",
        "AGG(Connections per VIN)", "AGG(VDPs per VIN)",
        "AGG(Vehicles)", "AGG(Vehicles)",
        "ATTR(Dealer Name & Id)", "ATTR(Price badge desc)",
    ],
    "rows": [
        ["Not Badged", "False", "True", "0.00000", "0.3333", "7.8947%", "3",
         "Land Rover Newport Beach (6071013)", "desc"],
        ["Great", "False", "True", "1.00000", "39.3333", "15.7895%", "6",
         "Land Rover Newport Beach (6071013)", "desc"],
        ["Good", "False", "True", "0.45000", "27.4500", "52.6316%", "20",
         "Land Rover Newport Beach (6071013)", "desc"],
        ["Fair", "False", "True", "1.77778", "47.2222", "23.6842%", "9",
         "Land Rover Newport Beach (6071013)", "desc"],
    ],
}

_LO_WITHIN_500 = {
    "cols": ["Dealer Name & Id", "Stock num", "YMMT", "Measure Names",
             "FALSE", "TRUE", "Measure Values"],
    "rows": [
        ["LRNB (6071013)", "TNA233572", "2022 Range Rover Sport HST MHEV",
         "Reduce by", "False", "True", "385.00"],
        ["LRNB (6071013)", "TNA233572", "2022 Range Rover Sport HST MHEV",
         "Days live", "False", "True", "4.00"],
        ["LRNB (6071013)", "TNA233572", "2022 Range Rover Sport HST MHEV",
         "Price", "False", "True", "54,999.00"],
        ["LRNB (6071013)", "SN0410801", "2022 Cadillac CT4-V Blackwing",
         "Reduce by", "False", "True", "472.00"],
        ["LRNB (6071013)", "SN0410801", "2022 Cadillac CT4-V Blackwing",
         "Days live", "False", "True", "18.00"],
        ["LRNB (6071013)", "SN0410801", "2022 Cadillac CT4-V Blackwing",
         "Price", "False", "True", "52,499.00"],
    ],
}

_LO_PERF_SNAPSHOT = {
    "cols": ["Dealer name (dynamic)", "Measure Names", "Stock type", "Measure Values"],
    "rows": [
        ["LRNB", "VDPs (07 days)", "Used", "504.00"],
        ["LRNB", "Connections (07 days)", "Used", "11.00"],
        ["LRNB", "Avg. Price", "Used", "48,404.42"],
        ["LRNB", "Avg. Days live", "Used", "15.61"],
        ["LRNB", "VDPs (07 days)", "New", "186.00"],
        ["LRNB", "Avg. Days live", "New", "60.83"],
    ],
}


def test_parse_badge_details_extracts_all_tiers():
    """Badge Details parser pulls vehicles, pct, VDPs/VIN, Connections/VIN per tier."""
    badges = admin_cars._parse_badge_details(_LO_BADGE_DETAILS)
    assert len(badges) == 4
    by_name = {b["badge"]: b for b in badges}
    assert by_name["Great"]["vdps_per_vin"] == 39.3333
    assert by_name["Great"]["connections_per_vin"] == 1.0
    assert by_name["Great"]["vehicles"] == 6.0
    assert by_name["Not Badged"]["vdps_per_vin"] == 0.3333
    assert by_name["Not Badged"]["vehicles"] == 3.0


def test_parse_within_500_groups_rows_by_stock_num():
    """Within-$500 parser pivots the per-measure rows into one dict per vehicle."""
    ops = admin_cars._parse_within_500_vehicles(_LO_WITHIN_500)
    assert len(ops) == 2
    # Sorted by smallest reduction first
    assert ops[0]["reduce_by"] == 385.0
    assert ops[0]["stock_num"] == "TNA233572"
    assert ops[0]["ymmt"] == "2022 Range Rover Sport HST MHEV"
    assert ops[0]["price"] == 54999.0
    assert ops[0]["days_live"] == 4.0


def test_parse_performance_snapshot_splits_by_stock_type():
    """Performance Snapshot parser returns {Used: {...}, New: {...}}."""
    split = admin_cars._parse_performance_snapshot(_LO_PERF_SNAPSHOT)
    assert "Used" in split and "New" in split
    assert split["Used"]["VDPs (07 days)"] == 504.0
    assert split["Used"]["Avg. Days live"] == 15.61
    assert split["New"]["Avg. Days live"] == 60.83  # 4x Used — the aging insight


# ── Reputation (_find_val) already covered above; add dealer-KPI test ────────

_REP_DEALER = {
    "cols": ["'1'", "'1'", "AVG(Cars.com)", "AVG(Total Number of Reviews)"],
    "rows": [["1", "1", "4.8", "911"]],
}


def test_reputation_dealer_kpi_columns_parse_cleanly():
    """Dealer KPI worksheet: rating in AVG(Cars.com) col, count in AVG(Total Number of Reviews)."""
    rating = admin_cars._find_val(_REP_DEALER["cols"], _REP_DEALER["rows"][0], "cars.com")
    reviews = admin_cars._find_val(_REP_DEALER["cols"], _REP_DEALER["rows"][0], "number of reviews")
    assert rating == 4.8
    assert reviews == 911.0


# ── ROI One-Sheeter lead-source aggregation ─────────────────────────────────

_ROI_CONNECTIONS = {
    "cols": ["Measure Names", "Begin date", "Measure Values"],
    "rows": [
        ["Phone Lead - Used",           "4/1/2026", "11"],
        ["Phone Lead - New",            "4/1/2026", "0"],
        ["Email Lead - Used",           "4/1/2026", "11"],
        ["Email Lead - New",            "4/1/2026", "1"],
        ["Email Lead - Finance Intent", "4/1/2026", "1"],
        ["Email Lead - Credit Application", "4/1/2026", "2"],
        ["Chat Lead - Used",            "4/1/2026", "1"],
        ["Chat Event - Used",           "4/1/2026", "1"],
        ["Website Transfers",           "4/1/2026", "13"],
        ["Website Transfers - Deep Link", "4/1/2026", "29"],  # sub-category — should NOT double-count
        ["Total Walk Ins",              "4/1/2026", "1"],
        ["Map Views",                   "4/1/2026", "3"],
        ["VDP Print",                   "4/1/2026", "0"],
        # Older month — should be ignored
        ["Phone Lead - Used",           "3/1/2026", "999"],
    ],
}


def test_aggregate_lead_sources_picks_most_recent_month():
    """Only current-month rows should be included; older months are dropped."""
    agg = admin_cars._aggregate_lead_sources(_ROI_CONNECTIONS)
    assert agg["phone"] == 11  # NOT 11 + 999
    assert agg["month"] == "April 2026"


def test_aggregate_lead_sources_avoids_double_counting_website_transfers():
    """The bare 'Website Transfers' is the top-level total; sub-categories like
    'Website Transfers - Deep Link' must NOT be added on top of it."""
    agg = admin_cars._aggregate_lead_sources(_ROI_CONNECTIONS)
    # Top-level 'Website Transfers' = 13 → use that; ignore the 29 sub-line.
    assert agg["website_transfers"] == 13


def test_aggregate_lead_sources_buckets_email_subcategories_correctly():
    """Only the whitelisted email sub-categories contribute, no double-counting."""
    agg = admin_cars._aggregate_lead_sources(_ROI_CONNECTIONS)
    # email = Used (11) + New (1) + Finance Intent (1) + Credit App (2) = 15
    assert agg["email"] == 15


def test_aggregate_lead_sources_total_matches_sum_of_buckets():
    """The 'total' field must equal the sum of all bucket counts."""
    agg = admin_cars._aggregate_lead_sources(_ROI_CONNECTIONS)
    bucket_keys = ["phone", "email", "chat", "website_transfers",
                   "walk_ins", "vdp_print", "instant_offer", "other"]
    assert agg["total"] == sum(agg[k] for k in bucket_keys)


# ── Market Comparison pricing-bucket aggregation ────────────────────────────
# This logic lives inline in _fetch_market_comparison_on, but the per-row
# classification is easy to drive via a minimal mock page.

def test_market_comparison_bucket_classification():
    """Above/At/Under classification keyed on the label column."""
    mock_page = MagicMock()
    mock_page.url = "https://admin.cars.com/dealers/217494e4-.../reports/demand_signals"
    # Stub _load_report to succeed so the fetcher falls through to page.evaluate
    with patch("admin_cars._load_report", return_value=True), \
         patch.object(mock_page, "evaluate", return_value={
             "cols": ["Market price", "AGG(Vehicles) pct", "AGG(Vehicles) count"],
             "rows": [
                 ["Under Market (<95%)",  "1.7751%",  "3"],
                 ["At Market",            "70.4142%", "119"],
                 ["Above Market (>105%)", "27.8107%", "47"],
             ],
         }):
        result = admin_cars._fetch_market_comparison_on(mock_page, "fake-uuid")
    assert result is not None
    assert result["above_pct"] == 28 and result["above_count"] == 47
    assert result["at_pct"] == 70 and result["at_count"] == 119
    assert result["under_pct"] == 2 and result["under_count"] == 3


# ── Sales Influence — DMS-absent short circuit ──────────────────────────────

def test_sales_influence_returns_dms_false_when_sentinel_present():
    """When the 'No DMS' sentinel worksheet is returned, we short-circuit to
    {dms_connected: False} and do not try to parse the mini-trend worksheets."""
    mock_page = MagicMock()
    mock_page.url = "https://admin.cars.com/dealers/x/reports/sales_influence_summary"
    with patch("admin_cars._load_report", return_value=True), \
         patch.object(mock_page, "evaluate", return_value={"no_dms": True}):
        result = admin_cars._fetch_sales_influence_on(mock_page, "fake-uuid")
    assert result == {"dms_connected": False}


# ── REQUIRED_WORKSHEETS manifest sanity ─────────────────────────────────────

def test_required_worksheets_manifest_covers_every_report_slug():
    """Every slug we pass to _load_report must be in REQUIRED_WORKSHEETS."""
    expected_slugs = {
        "performance_trends", "reputation_health", "demand_signals",
        "listings_optimizer", "sales_influence_summary", "roi_one_sheeter",
    }
    assert set(admin_cars.REQUIRED_WORKSHEETS.keys()) >= expected_slugs


def test_get_last_missing_worksheets_returns_only_nonempty_entries():
    """Slugs with an empty missing-list should not appear in the returned dict."""
    admin_cars._last_missing.clear()
    admin_cars._last_missing["a"] = ["Missing WS"]
    admin_cars._last_missing["b"] = []  # should be excluded
    result = admin_cars.get_last_missing_worksheets()
    assert result == {"a": ["Missing WS"]}
