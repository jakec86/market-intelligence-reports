"""
Price Badge Report — per-dealer configuration.

This is DATA ONLY. Adding a new store should never require editing pb_report.py —
add an entry here following the template at the bottom, then see
~/Documents/scripts/pb_onboarding.md for the full new-store checklist
(sheet clone, Tableau custom view, skill file, launchd schedule, test run).
"""

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
        "email_to": "jcrawley@cars.com",          # pre-send review: goes to Jake first
        "email_final_to": "anne.Lewis@hendrickauto.com",  # client recipient after approval
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
            "sort_specs": [
                {"dimensionIndex": 3, "sortOrder": "ASCENDING"},
                {"dimensionIndex": 0, "sortOrder": "ASCENDING"},
                {"dimensionIndex": 9, "sortOrder": "DESCENDING",
                 "backgroundColorStyle": {"rgbColor": {"green": 1}}},
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
        "email_to": "",             # ⚠ not onboarded yet — no recipients configured
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
