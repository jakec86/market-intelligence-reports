#!/usr/bin/env python3
"""
ACA ReviewBuilder DealerRater Config Writer

Reads "Status" tab rows in state 'ready', logs into DealerRater, and writes the
resolved message-tone option into that dealer's live ReviewBuilder Sales
Request Email settings (Subject/Message/When-to-Send). NEVER touches the
Service Request Email template — Sales only, per explicit scope decision.

Usage:
    python3 aca_review_config_writer.py                  # process all 'ready' rows
    python3 aca_review_config_writer.py --legacy-id 6063288 --option 1   # manual one-off test
    python3 aca_review_config_writer.py --dry-run         # show what would be written, no browser/writes
"""

import argparse, os, sys, time
from datetime import datetime

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

sys.path.insert(0, os.path.dirname(__file__))
from aca_gm_report import get_sheets_client, get_gmail_service, deliver_email, TEST_EMAIL  # noqa: E402
from aca_review_shared import (  # noqa: E402
    TRACKING_SHEET_ID, TAB_STATUS, MESSAGE_OPTIONS, TIMING_LABEL,
    load_review_data_by_legacy_id,
)

DEALERRATER_BASE = "https://www.dealerrater.com"

# IMPORTANT — two things confirmed live 2026-07-16, both required reading this
# comment before touching login logic again:
#
# 1. A brand-new/isolated browser context CANNOT complete DealerRater login
#    unattended: login.carscommerce.inc serves a real email+password form (no
#    password on file for this account) rather than the passwordless METAL SSO
#    flow, because the device isn't trusted — same device-trust behavior found
#    earlier for admin.cars.com (see memory: reference_jumpcloud_device_trust.md).
#
# 2. Pointing launch_persistent_context directly at the interactive Playwright
#    MCP tool's own profile dir (~/Library/Caches/ms-playwright-mcp/mcp-chrome-*)
#    does NOT reliably inherit that trusted session either — tested directly,
#    launch succeeds with no error, but Chrome silently serves an unauthenticated
#    profile state when the real one is locked by the live MCP-managed process,
#    landing back on the login page. Sharing that profile from a second process
#    is not a safe path.
#
# THE FIX: this script owns its OWN dedicated persistent profile directory,
# separate from the MCP tool's. That profile starts unauthenticated and needs
# ONE-TIME interactive bootstrapping — run this script with --headed once,
# manually complete the real DealerRater/METAL login (email + password) in the
# window that opens, then Playwright persists that profile's cookies to
# WRITER_PROFILE_DIR for all future headless/unattended runs. This is a real
# password Jake has to type once himself; nothing here can or should acquire it.
WRITER_PROFILE_DIR = os.path.expanduser("~/.claude/dealerrater_config_writer_profile")
MAX_RETRIES = 2


def launch_browser(playwright, headless=True):
    """Launch this script's own dedicated persistent profile (see comment
    above for why it can't share the MCP tool's profile). First run needs
    --headed so Jake can complete the one-time login bootstrap."""
    os.makedirs(WRITER_PROFILE_DIR, exist_ok=True)
    ctx = playwright.chromium.launch_persistent_context(
        WRITER_PROFILE_DIR, headless=headless,
    )
    return ctx, ctx  # persistent context serves as both "browser" and "ctx" for ctx.close()


def ensure_logged_in(page, dr_id, timeout_seconds=60):
    """Navigate to a DR admin page using WRITER_PROFILE_DIR's persisted
    session (established via the one-time --headed bootstrap login). If
    somehow still redirected to login (session expired), attempt the
    email-only METAL SSO completion as a best effort; if that doesn't clear
    within timeout_seconds, return False rather than hang — an expired
    session needs Jake to redo the --headed bootstrap, which this unattended
    script cannot do on its own."""
    page.goto(f"{DEALERRATER_BASE}/dp/{dr_id}/dashboard", wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(2000)

    if "login.carscommerce.inc" in page.url:
        try:
            page.fill('input[type="email"], input[name="email" i]', "jcrawley@cars.com", timeout=5000)
            page.click('button:has-text("Sign In"), button:has-text("Continue")', timeout=5000)
        except PlaywrightTimeout:
            pass

        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            page.wait_for_timeout(2000)
            if "login.carscommerce.inc" not in page.url:
                break
        else:
            return False  # still stuck on login after timeout — trusted session likely expired

    return "login.carscommerce.inc" not in page.url


def apply_sales_template(page, dr_id, subject, message, timing_days=None):
    """Write Subject/Message (and optionally timing) to the Sales Request Email
    editor only — never expands/touches Customize Service Request Email."""
    page.goto(f"{DEALERRATER_BASE}/dp/{dr_id}/reviews/reviewbuilder", wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(2000)

    page.get_by_text("Customize Sales Request Email", exact=True).click()
    page.wait_for_timeout(1000)

    # Stable element IDs confirmed by live inspection 2026-07-16 (verified via
    # a real test-write + revert on Southern Ford, DR ID 6197) — these are
    # specific to the Sales editor and cannot collide with the Service
    # editor's fields (which use different IDs and stay unrendered/collapsed
    # since we never click "Customize Service Request Email").
    page.fill("#rb-hub-sales-subject", subject)
    page.fill("#rb-hub-sales-body", message)

    if timing_days:
        label = TIMING_LABEL.get(timing_days)
        if label:
            # NOTE: unlike the Subject/Message fields, this selector was not
            # exercised during the 2026-07-16 live Southern Ford test (timing
            # was left at its default there) — verify on first real use with
            # a non-default timing_days value.
            select_el = page.locator("select").first
            select_el.select_option(label=label)
            # Some frameworks need an explicit change event dispatched to pick
            # up a programmatic select — see ~/.claude/commands/dr-employee-update.md
            select_el.evaluate("el => el.dispatchEvent(new Event('change', {bubbles: true}))")

    page.get_by_role("button", name="Save Changes").click()
    page.wait_for_timeout(3000)  # brief settle; caller verifies via screenshot/manual check for now


def process_row(status_row, review_data_by_id, headless=True):
    legacy_id = status_row["legacy_id"]
    dealer_name = status_row["dealer_name"]
    option = int(status_row["resolved_option"])
    timing = status_row.get("resolved_timing") or None
    info = MESSAGE_OPTIONS[option]

    review_row = review_data_by_id.get(legacy_id)
    if not review_row or not review_row.get("dr_id"):
        return "failed", f"No dr_id found for legacy_id {legacy_id}"

    dr_id = review_row["dr_id"]

    with sync_playwright() as p:
        browser, ctx = launch_browser(p, headless=headless)
        page = ctx.new_page()
        try:
            if not ensure_logged_in(page, dr_id):
                return "failed", "SSO session expired — needs interactive re-auth"
            apply_sales_template(page, dr_id, info["subject"], info["message"], timing)
            return "applied", ""
        except Exception as e:
            return "failed", str(e)
        finally:
            browser.close()


def notify_engine_failure(gmail, dealer_name, legacy_id, error_detail):
    subject = f"ReviewBuilder config-writer failed — {dealer_name}"
    body = f"<p><b>{dealer_name}</b> (legacy_id {legacy_id}) failed after {MAX_RETRIES} retries.</p><pre>{error_detail}</pre>"
    deliver_email(gmail, TEST_EMAIL, [], subject, body, draft_mode=False)


def notify_sso_blocked(gmail):
    subject = "ReviewBuilder config-writer BLOCKED — SSO session expired"
    body = "<p>The DealerRater admin session has expired and needs interactive re-authentication before any pending selections can be applied.</p>"
    deliver_email(gmail, TEST_EMAIL, [], subject, body, draft_mode=False)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--legacy-id", default=None, help="Process only this dealer (manual test)")
    parser.add_argument("--option", type=int, default=None, help="Force this option for --legacy-id (bypasses Status tab)")
    parser.add_argument("--headless", action="store_true", default=True)
    parser.add_argument("--headed", dest="headless", action="store_false")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not TRACKING_SHEET_ID:
        print("✗ TRACKING_SHEET_ID is empty in aca_review_shared.py — aborting")
        sys.exit(1)

    review_data_by_id = load_review_data_by_legacy_id()

    if args.legacy_id and args.option:
        dealer_name = review_data_by_id.get(args.legacy_id, {}).get("dealer_name", args.legacy_id)
        fake_row = {
            "legacy_id": args.legacy_id, "dealer_name": dealer_name,
            "resolved_option": str(args.option), "resolved_timing": "",
        }
        if args.dry_run:
            print(f"[dry-run] Would write Option {args.option} to {dealer_name} (legacy_id {args.legacy_id})")
            return
        status, detail = process_row(fake_row, review_data_by_id, headless=args.headless)
        print(f"{status}: {dealer_name} — {detail}")
        return

    gc = get_sheets_client()
    sh = gc.open_by_key(TRACKING_SHEET_ID)
    status_ws = sh.worksheet(TAB_STATUS)
    all_values = status_ws.get_all_values()
    header = all_values[0]
    rows = [dict(zip(header, r)) for r in all_values[1:]]

    ready_rows = [r for r in rows if r.get("resolution_status") == "ready"]
    print(f"Found {len(ready_rows)} row(s) in state 'ready'")

    if args.dry_run:
        for r in ready_rows:
            print(f"  [dry-run] {r['dealer_name']} → Option {r['resolved_option']}, timing={r.get('resolved_timing') or 'default'}")
        return

    if not ready_rows:
        return

    gmail = get_gmail_service()
    sso_blocked = False

    for idx, row in enumerate(rows):
        if row.get("resolution_status") != "ready":
            continue

        row_idx = idx + 2  # 1-indexed + header row
        legacy_id = row["legacy_id"]
        dealer_name = row["dealer_name"]

        if sso_blocked:
            print(f"  Skipping {dealer_name} — SSO already confirmed blocked this run")
            continue

        # Mark in_progress BEFORE touching the page, so a mid-run crash never
        # leaves an ambiguous 'ready' row that gets blindly retried.
        status_ws.update_cell(row_idx, header.index("resolution_status") + 1, "in_progress")

        status, detail = process_row(row, review_data_by_id, headless=args.headless)

        if status == "applied":
            status_ws.update_cell(row_idx, header.index("resolution_status") + 1, "applied")
            status_ws.update_cell(row_idx, header.index("applied_at") + 1, datetime.now().isoformat(timespec="seconds"))
            print(f"  ✓ Applied: {dealer_name}")
        else:
            retry_count = int(row.get("retry_count") or 0) + 1
            if "SSO session expired" in detail:
                sso_blocked = True
                notify_sso_blocked(gmail)
                status_ws.update_cell(row_idx, header.index("resolution_status") + 1, "ready")  # not this dealer's fault — retry next cycle
                status_ws.update_cell(row_idx, header.index("error_detail") + 1, detail)
                print(f"  ✗ BLOCKED (SSO): {dealer_name} — halting remaining rows this run")
                continue

            next_status = "failed"
            status_ws.update_cell(row_idx, header.index("resolution_status") + 1, next_status)
            status_ws.update_cell(row_idx, header.index("error_detail") + 1, detail)
            status_ws.update_cell(row_idx, header.index("retry_count") + 1, retry_count)
            print(f"  ✗ Failed: {dealer_name} — {detail} (retry {retry_count})")

            if retry_count > MAX_RETRIES:
                notify_engine_failure(gmail, dealer_name, legacy_id, detail)
            else:
                # allow next cycle to retry: flip back to ready
                status_ws.update_cell(row_idx, header.index("resolution_status") + 1, "ready")


if __name__ == "__main__":
    main()
