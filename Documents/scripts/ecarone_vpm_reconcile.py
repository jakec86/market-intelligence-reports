#!/usr/bin/env python3
"""
eCarOne VPM Results — one-off reconcile + canonical formatting.

Task A: Reconcile Sep–Feb 2026 rows (sheet rows 2–7) from the OLD additive
        convention (C = Tableau Total, E = C+D) to the corrected spec
        (C = Total - VPM, E = Total). Leads likewise (F = Total - VPM, H = Total).
        Pure arithmetic from existing cells — preserves each month's recorded
        totals, only fixes the VPM/non-VPM split. Does NOT restate historicals
        from current (restated) Tableau.

Task B: Apply canonical per-column formatting (per the VPM formatting standard)
        to all data rows 2–10 via batchUpdate/repeatCell, so March/April/May
        (which had copy/paste drift) match the canonical Oct–Feb rows.

Safety: rows 2–7 are hardcoded as old-convention (cannot be auto-detected since
        E==C+D holds for both conventions). Expected-old-value assertions abort
        the run if any row doesn't read its known old values (guards against
        double-run / wrong row).

Rows 8 (March), 9 (April), 10 (May) are already correct — values untouched.
I/J/K are formulas — never written; they recompute.
"""
import os
import sys
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SPREADSHEET_ID = "1E6CIiKbmFIWJdr3uWZHPkXMyQFtnDpAK6xdnJ58jz1Q"
SHEET_GID = 247007646
SHEET_NAME = "VPM Performance"
TOKEN_SHEETS = os.path.expanduser("~/.claude/tokens/sheets_token.json")
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# Known OLD-convention values for rows 2-7 (Sep..Feb): (C, D, F, G)
# C = Tableau Total VDPs, D = VPM VDPs, F = Tableau Total Leads, G = VPM Leads
EXPECTED_OLD = {
    2: (9407, 210, 88, 0),     # September 22-30
    3: (40823, 1841, 334, 2),  # October
    4: (34933, 1648, 296, 3),  # November
    5: (34029, 1940, 293, 4),  # December
    6: (35772, 2329, 355, 9),  # January
    7: (31316, 2381, 229, 4),  # February
}


def get_service():
    creds = Credentials.from_authorized_user_file(TOKEN_SHEETS, SCOPES)
    if not creds.valid:
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(TOKEN_SHEETS, "w") as f:
                f.write(creds.to_json())
        else:
            sys.exit("ERROR: Sheets token invalid and not refreshable.")
    return build("sheets", "v4", credentials=creds)


def reconcile_values(svc):
    rng = f"'{SHEET_NAME}'!B2:H7"
    resp = svc.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID, range=rng,
        valueRenderOption="UNFORMATTED_VALUE").execute()
    rows = resp.get("values", [])
    if len(rows) != 6:
        sys.exit(f"ERROR: expected 6 rows B2:H7, got {len(rows)}")

    data = []
    print("=== Task A: reconcile rows 2-7 (Sep-Feb) ===")
    for i, row in enumerate(rows):
        r = i + 2
        # row = [B(month), C, D, E, F, G, H]
        month, C, D, E, F, G, H = (row + [None] * 7)[:7]
        C, D, E, F, G, H = (int(round(x)) for x in (C, D, E, F, G, H))
        # Guard: confirm this row is still in old convention with known values
        exp = EXPECTED_OLD[r]
        if (C, D, F, G) != exp:
            sys.exit(f"ABORT row {r} ({month}): read (C,D,F,G)={ (C,D,F,G) } "
                     f"!= expected old {exp}. Row may already be corrected — not touching.")
        new_C = C - D
        new_E = C
        new_F = F - G
        new_H = F
        print(f"  row {r:>2} {str(month):<14} "
              f"C {C:>6}->{new_C:>6}  E {E:>6}->{new_E:>6}  "
              f"F {F:>4}->{new_F:>4}  H {H:>4}->{new_H:>4}  "
              f"(I=D/E now {D/new_E:.4%})")
        data.append({"range": f"'{SHEET_NAME}'!C{r}:H{r}",
                     "values": [[new_C, D, new_E, new_F, G, new_H]]})

    body = {"valueInputOption": "USER_ENTERED", "data": data}
    svc.spreadsheets().values().batchUpdate(
        spreadsheetId=SPREADSHEET_ID, body=body).execute()
    print("  -> values updated for rows 2-7\n")


def apply_formatting(svc):
    """Replicate the REAL canonical format from row 7 (Feb, B7:K7) onto the
    drift-prone rows 8, 9, 10 (March/April/May) via copyPaste PASTE_FORMAT.
    Leaves canonical rows 2-7 untouched. Source row index 6 (=row 7)."""
    print("=== Task B: copy canonical format from row 7 (Feb) -> rows 8,9,10 ===")
    src = {"sheetId": SHEET_GID, "startRowIndex": 6, "endRowIndex": 7,
           "startColumnIndex": 1, "endColumnIndex": 11}  # B7:K7
    requests = []
    for dest_row_idx in (7, 8, 9):  # rows 8, 9, 10 (0-based 7,8,9)
        requests.append({"copyPaste": {
            "source": src,
            "destination": {"sheetId": SHEET_GID,
                            "startRowIndex": dest_row_idx, "endRowIndex": dest_row_idx + 1,
                            "startColumnIndex": 1, "endColumnIndex": 11},
            "pasteType": "PASTE_FORMAT", "pasteOrientation": "NORMAL"}})
    svc.spreadsheets().batchUpdate(
        spreadsheetId=SPREADSHEET_ID, body={"requests": requests}).execute()
    print("  -> canonical format copied to rows 8-10 (B:K)\n")


def verify(svc):
    print("=== Verify: rows 2-11 (formatted display) ===")
    resp = svc.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID, range=f"'{SHEET_NAME}'!B2:K11",
        valueRenderOption="FORMATTED_VALUE").execute()
    for row in resp.get("values", []):
        print("  " + " | ".join(f"{c:>10}" for c in row))


if __name__ == "__main__":
    svc = get_service()
    reconcile_values(svc)
    apply_formatting(svc)
    verify(svc)
    print("\nDONE.")
