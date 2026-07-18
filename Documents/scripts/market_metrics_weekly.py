#!/usr/bin/env python3
"""
Weekly Marketplace Metrics (Contact Details) tracker.

Pulls Total Contact Details per store per Mon-Sun week, broken out by type
(Email/Phone/Chat/Website/Other), from admin.cars.com's Connections &
Contact Details report, for the 11 stores listed in the onboarding-audit
sheet (Sheet1 of TRACKING_SHEET_ID), and upserts results into that same
spreadsheet's "Weekly Contact Details" tab.

NOTE: "Contact Details" is a narrower metric than the report's "Total
Connections" KPI -- see market_metrics_shared.py's module docstring for
why (the two are not interchangeable and should never be conflated).

Auth: reuses the existing admin.cars.com-trusted Playwright profile
(pb-profile, ~/Library/Caches/ms-playwright-mcp/pb-profile) rather than a
fresh/isolated profile -- JumpCloud enforces device-trust conditional
access on the webadmin SAML app fronting admin.cars.com, and a brand-new
profile gets a policyDenial even with fully correct credentials+MFA (see
reference_jumpcloud_device_trust.md). Only fill the login form when a
navigation actually lands on the JumpCloud domain -- the persistent
profile should normally already carry a valid session.

Usage:
    python3 market_metrics_weekly.py                 # backfill + current week for all 11 stores
    python3 market_metrics_weekly.py --dry-run        # print results, skip the sheet write

Run this from a scheduled Monday-morning task pulling the just-completed
week; re-running mid-week (e.g. for the initial 7/13 backfill) is safe --
writes are upserts keyed on (CCID, Week Start), never blind appends.
"""

import argparse
import subprocess
import sys
import time
from datetime import date

sys.path.insert(0, __import__("os").path.dirname(__file__))
from market_metrics_shared import (  # noqa: E402
    TRACKING_SHEET_ID, SOURCE_TAB, METRICS_TAB, METRICS_HEADER, CONNECTION_TYPES,
    build_extract_js, load_uuid_cache, save_uuid_cache,
    report_url, uuid_lookup_url, bucket_weekly_counts,
)

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout  # noqa: E402

PROFILE_DIR = "/Users/jcrawley/Library/Caches/ms-playwright-mcp/pb-profile"
FIRST_WEEK_START = date(2026, 7, 13)


def get_secret(service):
    return subprocess.check_output(
        ["security", "find-generic-password", "-s", service, "-a", "jcrawley", "-w"],
        stderr=subprocess.DEVNULL,
    ).decode().strip()


def get_totp():
    return subprocess.check_output(
        [sys.executable, __import__("os").path.expanduser("~/.claude/scripts/jumpcloud-totp.py")],
    ).decode().strip()


def ensure_logged_in(page, timeout_s=90):
    """No-op if the pb-profile session is already valid (the common case).
    Only fills the JumpCloud form if actually redirected there."""
    page.goto("https://admin.cars.com/", wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(1500)
    if "jumpcloud" not in page.url:
        return True

    username = get_secret("jumpcloud-username")
    password = get_secret("jumpcloud-password")

    page.fill('input[type="email"], input[name="email" i]', username, timeout=10000)
    page.click('button:has-text("Continue")', timeout=5000)
    page.wait_for_timeout(1500)

    page.fill('input[type="password"]', password, timeout=10000)
    page.click('button:has-text("Continue"), button:has-text("Sign In")', timeout=5000)
    page.wait_for_timeout(2000)

    # TOTP page: 6 single-char boxes, per feedback_playwright_credential_fill.md
    totp_boxes = page.locator('input[maxlength="1"]')
    if totp_boxes.count() == 6:
        code = get_totp()
        for i, digit in enumerate(code):
            totp_boxes.nth(i).fill(digit)
        page.wait_for_timeout(1000)
        submit = page.locator('button:has-text("Continue"), button:has-text("Verify")')
        if submit.count():
            submit.first.click()

    deadline = time.time() + timeout_s
    while time.time() < deadline:
        page.wait_for_timeout(2000)
        if "jumpcloud" not in page.url:
            return True
    return False


def resolve_uuid(page, ccid, cache):
    if ccid in cache:
        return cache[ccid]
    page.goto(uuid_lookup_url(ccid), wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(1500)
    href = page.evaluate(
        """() => {
            const links = Array.from(document.querySelectorAll('a[href*="/reports"]'));
            const m = links.map(a => a.href).find(h => /\\/dealers\\/[a-f0-9-]{36}\\/reports/.test(h));
            return m || null;
        }"""
    )
    if not href:
        raise RuntimeError(f"Could not resolve admin.cars.com UUID for CCID {ccid}")
    import re
    uuid = re.search(r"/dealers/([a-f0-9-]{36})/reports", href).group(1)
    cache[ccid] = uuid
    save_uuid_cache(cache)
    return uuid


def fetch_timestamps(page, uuid, from_date_iso, to_date_iso):
    page.goto(report_url(uuid), wait_until="domcontentloaded", timeout=60000)
    page.wait_for_selector("text=Connections & Contact Details", timeout=30000)
    result = page.evaluate(build_extract_js(from_date_iso, to_date_iso))
    if result.get("error"):
        raise RuntimeError(f"Extraction failed for {uuid}: {result['error']}")
    return result["timestamps_by_type"]


def load_stores():
    """Read CCID + Store Name from Sheet1 via the Sheets REST API
    (token-based, same pattern as reference_google_sheets_mcp_cert.md)."""
    import json, os, urllib.request, urllib.parse

    token_path = os.path.expanduser("~/.claude/tokens/sheets_token.json")
    with open(token_path) as f:
        tok = json.load(f)
    data = urllib.parse.urlencode({
        "client_id": tok["client_id"], "client_secret": tok["client_secret"],
        "refresh_token": tok["refresh_token"], "grant_type": "refresh_token",
    }).encode()
    req = urllib.request.Request(tok["token_uri"], data=data, method="POST")
    with urllib.request.urlopen(req) as resp:
        access_token = json.loads(resp.read())["access_token"]

    url = f"https://sheets.googleapis.com/v4/spreadsheets/{TRACKING_SHEET_ID}/values/{SOURCE_TAB}!A2:B"
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {access_token}")
    with urllib.request.urlopen(req) as resp:
        values = json.loads(resp.read()).get("values", [])
    return [(row[0], row[1]) for row in values if len(row) >= 2 and row[0]]


def upsert_rows(new_rows):
    """Read existing Weekly Contact Details rows, upsert by (CCID, Week Start),
    write back the full table. new_rows: list of
    [ccid, store_name, week_start, week_end, total, email, phone, chat,
    website, other, partial_flag]."""
    import json, os, urllib.request, urllib.parse

    token_path = os.path.expanduser("~/.claude/tokens/sheets_token.json")
    with open(token_path) as f:
        tok = json.load(f)
    data = urllib.parse.urlencode({
        "client_id": tok["client_id"], "client_secret": tok["client_secret"],
        "refresh_token": tok["refresh_token"], "grant_type": "refresh_token",
    }).encode()
    req = urllib.request.Request(tok["token_uri"], data=data, method="POST")
    with urllib.request.urlopen(req) as resp:
        access_token = json.loads(resp.read())["access_token"]

    def call(method, url, body=None):
        b = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(url, data=b, method=method)
        req.add_header("Authorization", f"Bearer {access_token}")
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())

    n_cols = len(METRICS_HEADER)
    last_col = chr(ord("A") + n_cols - 1)  # 11 columns -> 'K'

    read_url = (
        f"https://sheets.googleapis.com/v4/spreadsheets/{TRACKING_SHEET_ID}"
        f"/values/{urllib.parse.quote(METRICS_TAB)}!A2:{last_col}"
    )
    existing = call("GET", read_url).get("values", [])

    by_key = {(r[0], r[2]): r for r in existing if len(r) >= n_cols}
    for row in new_rows:
        key = (row[0], row[2])
        by_key[key] = row

    def sort_key(r):
        return (r[2], r[0])

    all_rows = [METRICS_HEADER] + sorted(by_key.values(), key=sort_key)

    write_url = (
        f"https://sheets.googleapis.com/v4/spreadsheets/{TRACKING_SHEET_ID}"
        f"/values/{urllib.parse.quote(METRICS_TAB)}!A1:{last_col}{len(all_rows)}?valueInputOption=RAW"
    )
    call("PUT", write_url, {"values": all_rows})
    return len(all_rows) - 1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    today = date.today()
    stores = load_stores()
    cache = load_uuid_cache()

    results = []
    with sync_playwright() as pw:
        context = pw.chromium.launch_persistent_context(
            PROFILE_DIR, headless=True,
        )
        page = context.pages[0] if context.pages else context.new_page()

        if not ensure_logged_in(page):
            print("ERROR: could not establish admin.cars.com session (login timed out).", file=sys.stderr)
            sys.exit(1)

        for ccid, store_name in stores:
            uuid = resolve_uuid(page, ccid, cache)
            timestamps_by_type = fetch_timestamps(
                page, uuid, FIRST_WEEK_START.isoformat(), today.isoformat()
            )
            weeks = bucket_weekly_counts(timestamps_by_type, FIRST_WEEK_START, today)
            for w in weeks:
                results.append(
                    [ccid, store_name, w["week_start"], w["week_end"], w["total_contact_details"]]
                    + [w[t] for t in CONNECTION_TYPES]
                    + ["Yes" if w["partial_week"] else "No"]
                )
            print(f"  {store_name} ({ccid}): {len(weeks)} week(s) computed")

        context.close()

    if args.dry_run:
        for r in results:
            print(r)
        return

    n = upsert_rows(results)
    print(f"Upserted. {METRICS_TAB} now has {n} data rows.")


if __name__ == "__main__":
    main()
