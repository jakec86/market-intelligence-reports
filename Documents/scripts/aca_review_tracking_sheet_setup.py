#!/usr/bin/env python3
"""One-off setup script: creates the "ACA ReviewBuilder Engagement Tracking"
Google Sheet with its 3 tabs (Sends, Engagements, Status) and header rows.

Run once. Prints the resulting spreadsheet ID — paste that into
aca_review_shared.py::TRACKING_SHEET_ID afterward.
"""
import os

from googleapiclient.discovery import build as build_service

from aca_gm_report import get_sheets_client
from aca_review_shared import (
    TAB_SENDS, TAB_ENGAGEMENTS, TAB_STATUS,
    SENDS_HEADER, ENGAGEMENTS_HEADER, STATUS_HEADER,
)


def main():
    gc = get_sheets_client()
    sheets_svc = build_service("sheets", "v4", credentials=gc.http_client.auth)

    created = sheets_svc.spreadsheets().create(
        body={"properties": {"title": "ACA ReviewBuilder Engagement Tracking"}}
    ).execute()
    sheet_id = created["spreadsheetId"]
    print("Created:", sheet_id, "https://docs.google.com/spreadsheets/d/" + sheet_id)

    sh = gc.open_by_key(sheet_id)
    default_ws = sh.sheet1
    default_ws.update_title(TAB_SENDS)
    default_ws.update([SENDS_HEADER], "A1")
    default_ws.format("A1:J1", {"textFormat": {"bold": True}})
    default_ws.freeze(rows=1)

    eng_ws = sh.add_worksheet(title=TAB_ENGAGEMENTS, rows=500, cols=len(ENGAGEMENTS_HEADER))
    eng_ws.update([ENGAGEMENTS_HEADER], "A1")
    eng_ws.format(f"A1:{chr(64+len(ENGAGEMENTS_HEADER))}1", {"textFormat": {"bold": True}})
    eng_ws.freeze(rows=1)

    status_ws = sh.add_worksheet(title=TAB_STATUS, rows=200, cols=len(STATUS_HEADER))
    status_ws.update([STATUS_HEADER], "A1")
    status_ws.format(f"A1:{chr(64+len(STATUS_HEADER))}1", {"textFormat": {"bold": True}})
    status_ws.freeze(rows=1)

    print(f"\nTabs created: {TAB_SENDS}, {TAB_ENGAGEMENTS}, {TAB_STATUS}")
    print(f"\nPaste this into aca_review_shared.py:\nTRACKING_SHEET_ID = \"{sheet_id}\"")


if __name__ == "__main__":
    main()
