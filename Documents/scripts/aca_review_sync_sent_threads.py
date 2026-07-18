#!/usr/bin/env python3
"""
ACA ReviewBuilder — Sync Sent Threads

One-time-per-batch script. Run this AFTER Jake has manually reviewed and sent
(from the Gmail UI) some or all of the drafted ReviewBuilder Spotlight emails.
Finds each sent message by the legacy_id embedded in its subject line
(f"Cars.com ReviewBuilder Spotlight | {dealer_name} | {legacy_id}"), and
backfills thread_id/message_id/status=sent onto the matching Sends-tab row.

Usage:
    python3 aca_review_sync_sent_threads.py
    python3 aca_review_sync_sent_threads.py --dry-run
"""

import argparse, os, sys

sys.path.insert(0, os.path.dirname(__file__))
from aca_gm_report import get_sheets_client, get_gmail_service  # noqa: E402
from aca_review_shared import TRACKING_SHEET_ID, TAB_SENDS  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not TRACKING_SHEET_ID:
        print("✗ TRACKING_SHEET_ID is empty in aca_review_shared.py — aborting")
        sys.exit(1)

    gc = get_sheets_client()
    gmail = get_gmail_service()
    sh = gc.open_by_key(TRACKING_SHEET_ID)
    ws = sh.worksheet(TAB_SENDS)

    all_values = ws.get_all_values()
    header = all_values[0]
    rows = all_values[1:]

    idx_legacy = header.index("legacy_id")
    idx_status = header.index("status")
    idx_thread = header.index("thread_id")
    idx_msg = header.index("message_id")

    pending = [(i, r) for i, r in enumerate(rows, start=2) if r[idx_status] == "drafted"]
    print(f"Found {len(pending)} row(s) still marked 'drafted'")

    updated, still_pending, ambiguous = 0, 0, 0

    for row_idx, row in pending:
        legacy_id = row[idx_legacy]
        dealer_name = row[header.index("dealer_name")]

        query = f'subject:"ReviewBuilder Spotlight" "{legacy_id}" in:sent'
        try:
            res = gmail.users().messages().list(userId="me", q=query, maxResults=5).execute()
        except Exception as e:
            print(f"  ⚠ Gmail search failed for {dealer_name}: {e}")
            continue

        msgs = res.get("messages", [])
        if not msgs:
            still_pending += 1
            continue
        if len(msgs) > 1:
            print(f"  ⚠ {dealer_name} (legacy_id {legacy_id}): {len(msgs)} sent matches — skipping, resolve manually")
            ambiguous += 1
            continue

        msg_id = msgs[0]["id"]
        full = gmail.users().messages().get(userId="me", id=msg_id, format="minimal").execute()
        thread_id = full["threadId"]

        print(f"  ✓ {dealer_name}: thread_id={thread_id}, message_id={msg_id}")
        if not args.dry_run:
            ws.update_cell(row_idx, idx_thread + 1, thread_id)
            ws.update_cell(row_idx, idx_msg + 1, msg_id)
            ws.update_cell(row_idx, idx_status + 1, "sent")
        updated += 1

    print(f"\nDone — {updated} backfilled, {still_pending} still not sent, {ambiguous} ambiguous.")
    if args.dry_run:
        print("(dry-run — no sheet writes made)")


if __name__ == "__main__":
    main()
