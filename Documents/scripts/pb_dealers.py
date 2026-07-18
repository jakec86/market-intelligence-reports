"""
Price Badge Report — per-dealer configuration.

This is DATA ONLY. Adding a new store should never require editing pb_report.py —
add an entry here following the template at the bottom, then see
~/Documents/scripts/pb_onboarding.md for the full new-store checklist
(sheet clone, Tableau custom view, skill file, launchd schedule, test run).
"""

# Open-tracking web app (Apps Script). The email hyperlink uses a tracked link
# (TRACKER_BASE?report=<key>&r=<tag>) instead of the raw sheet_url, so an open by
# the dealer emails jcrawley@cars.com and then redirects them to the live Sheet.
# You keep using sheet_url yourself, so every alert = a genuine outside open.
# Project + deploy notes: ~/Documents/scripts/pb_link_tracker/DEPLOY.md
TRACKER_BASE = "https://script.google.com/macros/s/AKfycbySKt9As-7CVpAeoi3oCzlk7YEYLOxDZXrNc55wrIZEXEZ5pZnsqtK-ggqmF-3ww6juMg/exec"

DEALERS = {
    "hendrick": {
        "sheet_id": "1guqWV9HFb2MijC7qQ7qinL4oljbu0N1o9TU5zcmy3GM",
        "import_tab": "Data Import_Inventory Report",
        "pbt_tab": "Price Badge Tool",
        "dem_signal_tab": None,
        "col_reorder": False,
        "sort_range": "A3:J5000",   # Hendrick: R1=threshold, R2=headers, data R3+, K deleted
        "sort_col": 10,             # Column J (1-indexed in gspread)
        "data_start_row": 3,
        "threshold_cell": "E1",
        "threshold": 500,           # badge range $ — used by --dry-run (live runs read threshold_cell)
        "pct_cell": "J1",
        "stock_col": "D",
        "sheet_url": "https://docs.google.com/spreadsheets/d/1guqWV9HFb2MijC7qQ7qinL4oljbu0N1o9TU5zcmy3GM/edit?gid=565895707#gid=565895707",
        "email_link_url": f"{TRACKER_BASE}?report=hendrick&r=hendrick",  # tracked link used in the email body
        "email_to": "anne.Lewis@hendrickauto.com",
        "extra_hide_tabs": ["_open_log"],
        "email_subject": "Re: Cars.com: Price Badge Report",
        "email_from": "jcrawley@carscommerce.inc",
        "display_name": "Hendrick Automotive Group",
        "has_dem_signal": False,
        "callout_style": "sam",
        "pbt_store_col": 1,    # col B = Store name
        "pbt_vehicle_col": 2,  # col C = Vehicle (MMYT)
        # Hendrick PBT has a basicFilter that conflicts with sortRange API calls.
        # reset_pbt_filter() clears + re-adds it after each run to fix hiddenByFilter corruption.
        "pbt_filter": {
            "start_row": 1, "end_row": 11002, "start_col": 0, "end_col": 10,
            # Green-first (primary): col J cells the conditional format paints green
            # (within-threshold) sort to the top. SAM A-Z (secondary) orders the rest.
            # 2026-06-22: dropped the Stock#-primary key (dimensionIndex 3) that was
            # forcing Stock#-order on every run and overriding the intended
            # green-first + SAM A-Z display (required manual re-sorting each week).
            "sort_specs": [
                {"dimensionIndex": 9, "sortOrder": "DESCENDING",
                 "backgroundColorStyle": {"rgbColor": {"green": 1}}},
                {"dimensionIndex": 0, "sortOrder": "ASCENDING"},
            ],
            "filter_specs": [
                {"columnIndex": 0, "filterCriteria": {"hiddenValues": [""]}},
            ],
        },
    },
    "nalley": {
        "sheet_id": "13Jn8vJSG7vRYW9xpuxrMi9kXNhiV_TaCrjQ5lNQRPP8",
        "import_tab": "Data Import_Inventory Report",
        "pbt_tab": "Price Badge Tool",
        "dem_signal_tab": "Data Import_Dem Signal - $ Comp",
        "col_reorder": False,       # LEI CSV now: Dealer,id,Stock,VIN,Make,YMMT — matches sheet, no reorder
        "sort_range": "A4:L5000",   # Nalley: header row 3, data starts row 4
        "sort_col": 10,
        "data_start_row": 4,
        "threshold_cell": "E1",
        "threshold": 1000,
        "pct_cell": "J1",
        "stock_col": "D",
        "sheet_url": "https://docs.google.com/spreadsheets/d/13Jn8vJSG7vRYW9xpuxrMi9kXNhiV_TaCrjQ5lNQRPP8/edit?gid=565895707#gid=565895707",
        "email_link_url": f"{TRACKER_BASE}?report=nalley&r=nalley",  # tracked link used in the email body
        "email_to": "gcaudill1@nalleycars.com, jbrown1@nalleycars.com, zibrahimbegovic@asburyauto.com, rsaeed@nalleycars.com",
        "email_cc": "sdharanendra@asburyauto.com",
        "email_subject": "",        # set at runtime from display_name + date
        "email_from": "jcrawley@cars.com",
        "display_name": "Nalley Lexus Galleria",
        "has_dem_signal": True,
        "callout_style": "mmyt",
        "pbt_store_col": None,  # Nalley has no SAM/Store col — single dealer
        "pbt_vehicle_col": 1,   # col B = MMYT
        "pbt_vin_col": 2,       # col C = VIN (LEI CSV col 3)
        "lei_vin_idx": 3,       # VIN is at index 3 in the LEI CSV
    },
    "dyer": {
        "sheet_id": "1TWMwKUnntKZpjQDX6rbrScDHHfV5jQisG1EIAwIFwC8",
        "import_tab": "Data Import_Inventory Report",
        "pbt_tab": "Price Badge Tool",
        "dem_signal_tab": "Data Import_Dem Signal - $ Comp",
        "col_reorder": False,
        "sort_range": "A4:L5000",
        "sort_col": 10,
        "data_start_row": 4,
        "threshold_cell": "E1",
        "threshold": 1000,
        "pct_cell": "J1",
        "stock_col": "D",
        "sheet_url": "https://docs.google.com/spreadsheets/d/1TWMwKUnntKZpjQDX6rbrScDHHfV5jQisG1EIAwIFwC8/edit?gid=565895707#gid=565895707",
        "email_link_url": f"{TRACKER_BASE}?report=dyer&r=dyer",  # tracker "dyer" key → this sheet
        # Onboarded 2026-06-12 (Marielle approved). Weekly Thursdays, $1000 threshold.
        # Format approved by Jake 2026-06-12 → live client-send to Roman & Victor.
        "email_to": "Roman.Byczek@dyeranddyervolvo.com, Victor.Traitel@dyeranddyervolvo.com",
        "email_subject": "",
        "email_from": "jcrawley@cars.com",
        "display_name": "Dyer & Dyer Volvo Cars",
        "has_dem_signal": True,
        "callout_style": "mmyt",
        "pbt_store_col": None,
        "pbt_vehicle_col": 1,
        "pbt_vin_col": 2,
        "lei_vin_idx": 3,
    },

    # ── Herb Chambers GM monthly touchpoint — 6 single-store reports (Nalley layout) ──
    # Onboarded 2026-06-15. Used-only, has_dem_signal, callout_style "mmyt", data row 4.
    # Pre-send gated: email_to=jcrawley until format approved → then swap email_final_to into email_to + --send.
    # Run all six via /herb-chambers-pb-report (pb_parallel.py). Threshold $500 Honda / $1000 luxury.
    "hc_seekonk_honda": {
        "sheet_id": "12B1r6uvZ7B9nuFTBcqUIgyhxXNbQv4jyIiOpYzhQh8w",
        "import_tab": "Data Import_Inventory Report",
        "pbt_tab": "Price Badge Tool",
        "dem_signal_tab": "Data Import_Dem Signal - $ Comp",
        "col_reorder": False,
        "sort_range": "A4:L5000",
        "sort_col": 10,
        "data_start_row": 4,
        "threshold_cell": "E1",
        "threshold": 500,
        "pct_cell": "J1",
        "stock_col": "D",
        "sheet_url": "https://docs.google.com/spreadsheets/d/12B1r6uvZ7B9nuFTBcqUIgyhxXNbQv4jyIiOpYzhQh8w/edit?gid=565895707#gid=565895707",
        "email_link_url": f"{TRACKER_BASE}?report=hc_seekonk_honda&r=hc_seekonk_honda",
        "email_to": "jcrawley@cars.com",
        "email_final_to": "scott@herbchambers.com",
        "email_subject": "",
        "email_from": "jcrawley@cars.com",
        "display_name": "Herb Chambers Honda of Seekonk",
        "has_dem_signal": True,
        "callout_style": "mmyt",
        "pbt_store_col": None,
        "pbt_vehicle_col": 1,
        "pbt_vin_col": 2,
        "lei_vin_idx": 3,
    },
    "hc_boston_bmwmini": {
        "sheet_id": "1bHQG0Ceb6NEkLBOOgN3L1EhbazuO6i5hsvgZWqPdPLI",
        "import_tab": "Data Import_Inventory Report",
        "pbt_tab": "Price Badge Tool",
        "dem_signal_tab": "Data Import_Dem Signal - $ Comp",
        "col_reorder": False,
        "sort_range": "A4:L5000",
        "sort_col": 10,
        "data_start_row": 4,
        "threshold_cell": "E1",
        "threshold": 1000,
        "pct_cell": "J1",
        "stock_col": "D",
        "sheet_url": "https://docs.google.com/spreadsheets/d/1bHQG0Ceb6NEkLBOOgN3L1EhbazuO6i5hsvgZWqPdPLI/edit?gid=565895707#gid=565895707",
        "email_link_url": f"{TRACKER_BASE}?report=hc_boston_bmwmini&r=hc_boston_bmwmini",
        "email_to": "jcrawley@cars.com",
        "email_final_to": "msteffy@herbchambers.com",
        "email_subject": "",
        "email_from": "jcrawley@cars.com",
        "display_name": "Herb Chambers BMW MINI of Boston",
        "has_dem_signal": True,
        "callout_style": "mmyt",
        "pbt_store_col": None,
        "pbt_vehicle_col": 1,
        "pbt_vin_col": 2,
        "lei_vin_idx": 3,
    },
    "hc_boston_jlr": {
        "sheet_id": "1l3C0s3oC94fT_a_OqvbWtKT_kGt1tZA0oQnJUq0qnu0",
        "import_tab": "Data Import_Inventory Report",
        "pbt_tab": "Price Badge Tool",
        "dem_signal_tab": "Data Import_Dem Signal - $ Comp",
        "col_reorder": False,
        "sort_range": "A4:L5000",
        "sort_col": 10,
        "data_start_row": 4,
        "threshold_cell": "E1",
        "threshold": 1000,
        "pct_cell": "J1",
        "stock_col": "D",
        "sheet_url": "https://docs.google.com/spreadsheets/d/1l3C0s3oC94fT_a_OqvbWtKT_kGt1tZA0oQnJUq0qnu0/edit?gid=565895707#gid=565895707",
        "email_link_url": f"{TRACKER_BASE}?report=hc_boston_jlr&r=hc_boston_jlr",
        "email_to": "jcrawley@cars.com",
        # GM per HC GM master list (Asbury Contact List sheet, "HC GM list" tab): Adil Elomri (Jaguar/Land Rover Boston).
        # Prior value jsaghbini@ was the Land Rover/Jaguar *Sudbury* GM — corrected 2026-06-16.
        "email_final_to": "aelomri@herbchambers.com",
        "email_subject": "",
        "email_from": "jcrawley@cars.com",
        "display_name": "Jaguar Land Rover Boston",
        "has_dem_signal": True,
        "callout_style": "mmyt",
        "pbt_store_col": None,
        "pbt_vehicle_col": 1,
        "pbt_vin_col": 2,
        "lei_vin_idx": 3,
    },
    "hc_exotics": {
        "sheet_id": "13B2_DcZPoeFg1sNEMVBRFikV-ouXuQwnKlwhqlsiIo8",
        "import_tab": "Data Import_Inventory Report",
        "pbt_tab": "Price Badge Tool",
        "dem_signal_tab": "Data Import_Dem Signal - $ Comp",
        "col_reorder": False,
        "sort_range": "A4:L5000",
        "sort_col": 10,
        "data_start_row": 4,
        "threshold_cell": "E1",
        "threshold": 5000,  # ultra-luxury (RR/Bentley/Lambo) — $1000 too tight; smallest reduce-by ~$1.5k
        "pct_cell": "J1",
        "stock_col": "D",
        "sheet_url": "https://docs.google.com/spreadsheets/d/13B2_DcZPoeFg1sNEMVBRFikV-ouXuQwnKlwhqlsiIo8/edit?gid=565895707#gid=565895707",
        "email_link_url": f"{TRACKER_BASE}?report=hc_exotics&r=hc_exotics",
        "email_to": "jcrawley@cars.com",
        "email_final_to": "btaylor@herbchambers.com",
        "email_subject": "",
        "email_from": "jcrawley@cars.com",
        "display_name": "Herb Chambers Exotics",
        "has_dem_signal": True,
        "callout_style": "mmyt",
        "pbt_store_col": None,
        "pbt_vehicle_col": 1,
        "pbt_vin_col": 2,
        "lei_vin_idx": 3,
    },
    "hc_medford_bmw": {
        "sheet_id": "1sy_nWQNy1DGMZRPu2P9lXtvekAfgbLnNFOwVkhqg2Pk",
        "import_tab": "Data Import_Inventory Report",
        "pbt_tab": "Price Badge Tool",
        "dem_signal_tab": "Data Import_Dem Signal - $ Comp",
        "col_reorder": False,
        "sort_range": "A4:L5000",
        "sort_col": 10,
        "data_start_row": 4,
        "threshold_cell": "E1",
        "threshold": 1000,
        "pct_cell": "J1",
        "stock_col": "D",
        "sheet_url": "https://docs.google.com/spreadsheets/d/1sy_nWQNy1DGMZRPu2P9lXtvekAfgbLnNFOwVkhqg2Pk/edit?gid=565895707#gid=565895707",
        "email_link_url": f"{TRACKER_BASE}?report=hc_medford_bmw&r=hc_medford_bmw",
        "email_to": "jcrawley@cars.com",
        "email_final_to": "msteffy@herbchambers.com",
        "email_subject": "",
        "email_from": "jcrawley@cars.com",
        "display_name": "BMW of Medford",
        "has_dem_signal": True,
        "callout_style": "mmyt",
        "pbt_store_col": None,
        "pbt_vehicle_col": 1,
        "pbt_vin_col": 2,
        "lei_vin_idx": 3,
    },
    "hc_porsche": {
        "sheet_id": "1-u7DO9PvJuSyQK7cpjhBIEZt16dgNyGWG_km-Y4KbbQ",
        "import_tab": "Data Import_Inventory Report",
        "pbt_tab": "Price Badge Tool",
        "dem_signal_tab": "Data Import_Dem Signal - $ Comp",
        "col_reorder": False,
        "sort_range": "A4:L5000",
        "sort_col": 10,
        "data_start_row": 4,
        "threshold_cell": "E1",
        "threshold": 1000,
        "pct_cell": "J1",
        "stock_col": "D",
        "sheet_url": "https://docs.google.com/spreadsheets/d/1-u7DO9PvJuSyQK7cpjhBIEZt16dgNyGWG_km-Y4KbbQ/edit?gid=565895707#gid=565895707",
        "email_link_url": f"{TRACKER_BASE}?report=hc_porsche&r=hc_porsche",
        "email_to": "jcrawley@cars.com",
        "email_final_to": "jasonobrien@herbchambers.com",
        "email_subject": "",
        "email_from": "jcrawley@cars.com",
        "display_name": "Herb Chambers Porsche",
        "has_dem_signal": True,
        "callout_style": "mmyt",
        "pbt_store_col": None,
        "pbt_vehicle_col": 1,
        "pbt_vin_col": 2,
        "lei_vin_idx": 3,
    },

    # ── NEW STORE TEMPLATE ────────────────────────────────────────────────────
    # Copy this block, fill in every value, then follow pb_onboarding.md.
    # Single-store dealers: clone the Nalley sheet layout (data starts row 4,
    # callout_style "mmyt", pbt_store_col None).
    # Multi-store groups: clone the Hendrick layout (data starts row 3,
    # callout_style "sam", pbt_store_col 1, and a pbt_filter block).
    #
    # "newstore": {
    #     "sheet_id": "",                 # from the cloned Google Sheet URL
    #     "import_tab": "Data Import_Inventory Report",
    #     "pbt_tab": "Price Badge Tool",
    #     "dem_signal_tab": "Data Import_Dem Signal - $ Comp",  # or None
    #     "col_reorder": False,
    #     "sort_range": "A4:L5000",       # Nalley layout; "A3:J5000" for Hendrick layout
    #     "sort_col": 10,
    #     "data_start_row": 4,            # 3 for Hendrick layout
    #     "threshold_cell": "E1",
    #     "threshold": 1000,              # must match the sheet's E1 value
    #     "pct_cell": "J1",
    #     "stock_col": "D",
    #     "sheet_url": "",
    #     "email_link_url": f"{TRACKER_BASE}?report=<key>&r=<key>",  # add <key> to REPORTS in pb_link_tracker/Code.js + redeploy
    #     "email_to": "jcrawley@cars.com",       # Jake first until format approved
    #     "email_final_to": "",                  # client recipient(s) after approval
    #     "email_subject": "",
    #     "email_from": "jcrawley@cars.com",
    #     "display_name": "",
    #     "has_dem_signal": True,
    #     "callout_style": "mmyt",        # "sam" for multi-store groups
    #     "pbt_store_col": None,          # 1 for multi-store groups
    #     "pbt_vehicle_col": 1,           # 2 for Hendrick layout
    #     "pbt_vin_col": 2,
    #     "lei_vin_idx": 3,
    # },
}
