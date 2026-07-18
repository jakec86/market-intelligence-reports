#!/usr/bin/env python3
"""
ACA ReviewBuilder Spotlight Email — one-time send to ACA store GMs.

Usage:
    python3 aca_review_report.py                        # TEST MODE — 1 random store to jcrawley@cars.com
    python3 aca_review_report.py --test-count 5          # 5 random test stores
    python3 aca_review_report.py --store "Sunrise Ford"  # test a specific store
    python3 aca_review_report.py --draft                 # create Gmail drafts for ALL matched stores

Data source: dealerrater_results.json (real per-store DealerRater 30-day pull —
Tableau's ReviewDashboard numbers were confirmed unreliable, off by 5-10x).
Case study store: Southern Ford (90 reviews/30d, 100% via ReviewBuilder).
"""

import argparse, os, random, sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))
from aca_gm_report import (  # noqa: E402
    get_sheets_client, get_gmail_service, deliver_email, load_gm_contacts,
    _normalize, _NAME_ALIASES, _DISPLAY_OVERRIDES, TEMP_CONTACT_OVERRIDES,
    TEST_EMAIL,
)
from aca_review_shared import (  # noqa: E402
    MESSAGE_OPTIONS, load_review_data,
    TRACKING_SHEET_ID, TAB_SENDS,
)

# Deployed 2026-07-16 via aca_review_click_tracker/deploy.sh. NOTIFY_TO in that
# script's Code.js is currently jcrawley-only for testing — see its DEPLOY.md
# "Before going live" note to re-add Danielle before the real batch.
CLICK_TRACKER_BASE_URL = (
    "https://script.google.com/macros/s/"
    "AKfycbwoMkVAe5h2BG_0baMOIO0Dt_YaHjwCClqldK3KsODCbdkEr57xgYIIjexpsUSmfAI3mw/exec"
)

CASE_STUDY_KEY = "southern ford"  # matches _normalize(dealer_name)

# Stores excluded from the send entirely (satellite/delivery entities, not real
# GM-facing storefronts) even though enrolled in ReviewBuilder per Tableau.
EXCLUDED_KEYS = {
    _normalize("Vision Automotive Group - Delivery from Rochester, NY for Buffalo, NY"),
}

BROKEN_FEED_THRESHOLD = 1  # rb_reviews_30d <= this ⇒ "broken feed" variant


def find_review_row(contact, by_name):
    row = by_name.get(contact["store_key"])
    if row:
        return row
    alias = _NAME_ALIASES.get(contact["store_key"])
    if alias:
        row = by_name.get(_normalize(alias))
    return row


def num(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def fmt_int(v):
    n = num(v)
    return f"{n:,}" if n is not None else "N/A"


def fmt_pct1(v):
    if v is None:
        return "N/A"
    try:
        return f"{float(v):.0f}%"
    except (TypeError, ValueError):
        return "N/A"


def build_tone_picker_link(legacy_id, dealer_name):
    """Single tracked link (no option param) — lands on a list page showing
    all 3 full drafts with their own confirm buttons. Deliberately ONE link
    per email rather than one per option: fewer external links helps spam/
    security-gateway scoring, and script.google.com/macros links in particular
    draw extra scrutiny from gateways like Mimecast (a known phishing-abuse
    URL pattern) — cutting 3 down to 1 is a real deliverability mitigation,
    not just tidiness."""
    from urllib.parse import quote
    return f"{CLICK_TRACKER_BASE_URL}?legacy_id={quote(str(legacy_id))}&dealer={quote(dealer_name)}"


def log_pending_send(gc, legacy_id, dealer_name, dr_id, gm_email, gm_name, draft_id):
    """Write one row to the tracking sheet's Sends tab at draft time.
    thread_id/message_id are backfilled later by aca_review_sync_sent_threads.py
    once Jake actually sends the reviewed draft."""
    if not TRACKING_SHEET_ID:
        return
    sh = gc.open_by_key(TRACKING_SHEET_ID)
    ws = sh.worksheet(TAB_SENDS)
    ws.append_row([
        legacy_id, dealer_name, dr_id, gm_email, gm_name,
        draft_id, "", "", "drafted", datetime.now().isoformat(timespec="seconds"),
    ])


CASE_STUDY_TILE = """\
<table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-top:14px;">
  <tr><td style="background:#7c3aed;border-radius:8px;padding:16px 18px;">
    <div style="font-size:9px;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;color:rgba(255,255,255,0.75);margin-bottom:6px;">Case Study</div>
    <div style="font-size:15px;font-weight:800;color:#ffffff;line-height:1.3;margin-bottom:4px;">
      Southern Ford Generated 90 Reviews Last Month — 100% via ReviewBuilder
    </div>
    <div style="font-size:11px;color:rgba(255,255,255,0.9);line-height:1.5;">
      Every one of Southern Ford's 90 reviews in the last 30 days came through ReviewBuilder's automated post-sale/service follow-up — zero manual outreach, zero organic asks needed. It's proof of what a fully-working ReviewBuilder feed can do.
    </div>
  </td></tr>
</table>"""

CASE_STUDY_TILE_SELF = """\
<table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-top:14px;">
  <tr><td style="background:#7c3aed;border-radius:8px;padding:16px 18px;">
    <div style="font-size:9px;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;color:rgba(255,255,255,0.75);margin-bottom:6px;">You're the Benchmark</div>
    <div style="font-size:15px;font-weight:800;color:#ffffff;line-height:1.3;margin-bottom:4px;">
      90 Reviews Last Month — 100% via ReviewBuilder
    </div>
    <div style="font-size:11px;color:rgba(255,255,255,0.9);line-height:1.5;">
      Southern Ford is the ACA group's top single-brand performer on ReviewBuilder this month — every review came in automatically through post-sale/service follow-up. Other ACA GMs are seeing this as the standard to aim for. Nice work.
    </div>
  </td></tr>
</table>"""


def card2_healthy(store_name, row):
    total = fmt_int(row.get("total_reviews_30d"))
    rb = fmt_int(row.get("rb_reviews_30d"))
    rb_pct = fmt_pct1(row.get("rb_pct"))
    return f"""\
<div style="background:#f9f6ff;border-left:3px solid #7c3aed;border-radius:0 6px 6px 0;padding:10px 14px;">
  <div style="font-size:11px;font-weight:700;color:#1a1a2e;margin-bottom:3px;">&#128200; Your Current Standing</div>
  <div style="font-size:11px;color:#444;line-height:1.5;">{store_name} generated <strong>{total} reviews</strong> in the last 30 days, with <strong>{rb} ({rb_pct})</strong> coming automatically through ReviewBuilder.</div>
</div>"""


def card2_broken(store_name, row):
    total = fmt_int(row.get("total_reviews_30d"))
    rb = fmt_int(row.get("rb_reviews_30d"))
    return f"""\
<div style="background:#fff7f0;border-left:3px solid #e07b39;border-radius:0 6px 6px 0;padding:10px 14px;">
  <div style="font-size:11px;font-weight:700;color:#1a1a2e;margin-bottom:3px;">&#9888; Worth a Quick Check</div>
  <div style="font-size:11px;color:#444;line-height:1.5;">{store_name} generated <strong>{total} reviews</strong> in the last 30 days, with only <strong>{rb}</strong> coming through ReviewBuilder despite being enrolled. That's lower than expected — worth a quick check with your Cars.com rep to confirm the feed is capturing your sales/service transactions correctly.</div>
</div>"""


CARD1 = """\
<div style="background:#f9f6ff;border-left:3px solid #7c3aed;border-radius:0 6px 6px 0;padding:10px 14px;">
  <div style="font-size:11px;font-weight:700;color:#1a1a2e;margin-bottom:3px;">&#128260; How It Works</div>
  <div style="font-size:11px;color:#444;line-height:1.5;">ReviewBuilder is included with your Premium/Premium+ subscription. It automatically follows up with customers after sales and service visits, prompting them to leave a review on Cars.com, Google, or Facebook — no extra work for your team.</div>
</div>"""

CARD3 = """\
<div style="background:#f9f6ff;border-left:3px solid #7c3aed;border-radius:0 6px 6px 0;padding:10px 14px;">
  <div style="font-size:11px;font-weight:700;color:#1a1a2e;margin-bottom:3px;">&#128176; The Payoff</div>
  <div style="font-size:11px;color:#444;line-height:1.5;">Across ACA, stores with an active ReviewBuilder feed are generating 30+ reviews a month on average — building a stronger, fresher reputation with zero manual follow-up required.</div>
</div>"""


def build_tone_picker_card(legacy_id, dealer_name):
    """Subject-only preview of each of the 3 customer-message tone options
    (no body text — the click-through already shows the full draft, so
    repeating it here just makes the email longer without adding value),
    plus ONE tracked link for the whole email (not one per option — see
    build_tone_picker_link for why). Two selection paths are both advertised:
    the button (click-through shows the full draft, then confirm) or
    reply-all with a plain option number — the poller already parsed replies
    as a fallback; now it's a first-class advertised path again. Also
    surfaces the "When to Send Requests" timing choice (Tomorrow/7/14/30
    days), defaulting to Tomorrow if the GM doesn't specify one."""
    dealer_message = lambda text: text.replace("[DealerName]", dealer_name)  # noqa: E731
    link = build_tone_picker_link(legacy_id, dealer_name)
    option_rows = []
    for opt in (1, 2, 3):
        info = MESSAGE_OPTIONS[opt]
        subject = dealer_message(info["subject"])
        option_rows.append(f"""\
<tr><td style="padding:6px 0;border-bottom:1px solid #f0ede8;">
  <span style="font-size:10px;font-weight:700;color:#7c3aed;">Option {opt}</span>
  <span style="font-size:11px;color:#1a1a2e;font-weight:600;margin-left:6px;">“{subject}”</span>
</td></tr>""")

    return f"""\
<div style="font-size:10px;font-weight:700;color:#7c3aed;text-transform:uppercase;letter-spacing:0.08em;margin:20px 0 6px;">Pick Your Customer Message</div>
<div style="font-size:15px;font-weight:800;color:#1a1a2e;line-height:1.2;margin-bottom:8px;">Choose the Tone Your ReviewBuilder Uses</div>
<p style="font-size:11px;color:#444;line-height:1.6;margin:0 0 10px;">3 personalized review-request templates, already reviewed and approved by ACA:</p>
<table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-bottom:14px;">
{"".join(option_rows)}
</table>
<p style="font-size:11px;color:#444;line-height:1.6;margin:0 0 14px;">Click below to preview the full drafts and confirm your pick, or just reply-all to this email with your option number (1, 2, or 3).</p>
<div style="text-align:center;margin-bottom:16px;">
  <a href="{link}" style="display:inline-block;background:#7c3aed;color:#ffffff;text-decoration:none;font-size:12px;font-weight:700;padding:10px 20px;border-radius:6px;">Preview &amp; Choose Your Message &rarr;</a>
</div>
<div style="background:#f9f6ff;border-left:3px solid #7c3aed;border-radius:0 6px 6px 0;padding:10px 14px;">
  <div style="font-size:11px;font-weight:700;color:#1a1a2e;margin-bottom:3px;">When to Send Requests</div>
  <div style="font-size:11px;color:#444;line-height:1.5;">Requests go out <strong>the next day by default (recommended)</strong>. Want a different timing instead — 7, 14, or 30 days after the sale? Just include it in your reply, e.g. "Option 2, 7 days." No reply needed if the next-day default works for you.</div>
</div>"""


def get_html_template():
    return """\
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f0ede8;font-family:Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#f0ede8;">
<tr><td align="center" style="padding:24px 16px;">
<table width="620" cellpadding="0" cellspacing="0" border="0" style="background:#ffffff;border-radius:4px;">

  <!-- HEADER -->
  <tr>
    <td style="background:#1a1a2e;padding:14px 22px;border-radius:4px 4px 0 0;">
      <table width="100%" cellpadding="0" cellspacing="0" border="0">
        <tr>
          <td style="vertical-align:middle;padding-right:20px;">
            <img src="https://admin.cars.com/images/logo_cars-856ce78c79cc80b44f2a7106e93cfea9.png" alt="Cars.com" height="40" style="display:block;" />
          </td>
          <td style="vertical-align:middle;">
            <div style="color:#ffffff;font-family:Arial,sans-serif;font-size:20px;font-weight:700;line-height:1.2;">ReviewBuilder Spotlight</div>
            <div style="color:rgba(255,255,255,0.6);font-family:Arial,sans-serif;font-size:11px;font-weight:400;margin-top:3px;">[Dealership Name]</div>
          </td>
        </tr>
      </table>
    </td>
  </tr>

  <!-- INTRO -->
  <tr>
    <td style="padding:18px 28px 0;">
      <p style="margin:0 0 6px;font-size:13px;color:#333;font-weight:600;">Hello [FIRST_NAME]!</p>
      <p style="margin:0;font-size:13px;color:#555;line-height:1.6;">
        Quick spotlight on your Cars.com ReviewBuilder activity — the automated review-solicitation feature included with your subscription.
      </p>
    </td>
  </tr>

  <!-- TONE PICKER -->
  <tr>
    <td style="padding:22px 28px;">
      [TONE_PICKER_CARD]
    </td>
  </tr>

  <!-- REVIEWBUILDER SECTION -->
  <tr>
    <td style="padding:0 28px 22px;border-top:1px solid #f0ede8;padding-top:22px;">
      <div style="font-size:10px;font-weight:700;color:#7c3aed;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:6px;">ReviewBuilder</div>
      <div style="font-size:17px;font-weight:800;color:#1a1a2e;line-height:1.2;margin-bottom:10px;">Turn Every Sale Into a 5-Star Review — Automatically</div>
      <table width="100%" cellpadding="0" cellspacing="0" border="0">
        <tr><td style="padding-bottom:10px;vertical-align:top;">[CARD1]</td></tr>
        <tr><td style="padding-bottom:10px;vertical-align:top;">[CARD2]</td></tr>
        <tr><td style="vertical-align:top;">[CARD3]</td></tr>
      </table>
      [CASE_STUDY_TILE]
    </td>
  </tr>

  <!-- SIGNATURE -->
  <tr>
    <td style="padding:18px 28px 0;border-top:1px solid #f0ede8;">
      <p style="margin:0 0 10px;font-size:12px;color:#555;line-height:1.6;">Questions? Just reply to this email.</p>
      <p style="margin:0;font-size:13px;color:#1a1a2e;font-weight:700;line-height:1.5;">Jacob Crawley</p>
      <p style="margin:0;font-size:11px;color:#555;line-height:1.5;">Client Service Manager, Enterprise Accounts</p>
      <p style="margin:4px 0 0;font-size:11px;color:#555;line-height:1.5;">M: 918.694.1670</p>
      <p style="margin:8px 0 0;font-size:11px;color:#1a1a2e;font-weight:700;line-height:1.5;">Cars Commerce</p>
      <p style="margin:2px 0 0;font-size:10px;color:#999;line-height:1.5;">Cars.com &nbsp;|&nbsp; Fuel &nbsp;|&nbsp; Dealer Inspire &nbsp;|&nbsp; DealerRater &nbsp;|&nbsp; Accu-Trade</p>
    </td>
  </tr>

  <!-- FOOTER -->
  <tr>
    <td style="padding:14px 28px 20px;">
      <p style="margin:0;font-size:10px;color:#bbb;">
        Cars.com ReviewBuilder Spotlight
      </p>
    </td>
  </tr>

</table>
</td></tr>
</table>
</body>
</html>"""


def render_email(contact, row):
    store_name = contact["store_name"]
    is_case_study = _normalize(row.get("dealer_name", "")) == CASE_STUDY_KEY
    is_broken = (num(row.get("rb_reviews_30d")) or 0) <= BROKEN_FEED_THRESHOLD

    card2 = card2_broken(store_name, row) if is_broken else card2_healthy(store_name, row)
    case_tile = CASE_STUDY_TILE_SELF if is_case_study else CASE_STUDY_TILE

    legacy_id = row.get("legacy_id", "")
    tone_picker = build_tone_picker_card(legacy_id, store_name)

    body = get_html_template()
    body = body.replace("[Dealership Name]", store_name)
    body = body.replace("[FIRST_NAME]", contact["first_name"])
    body = body.replace("[CARD1]", CARD1)
    body = body.replace("[CARD2]", card2)
    body = body.replace("[CARD3]", CARD3)
    body = body.replace("[CASE_STUDY_TILE]", case_tile)
    body = body.replace("[TONE_PICKER_CARD]", tone_picker)

    subject = f"Cars.com ReviewBuilder Spotlight | {store_name} | {legacy_id}"
    return subject, body


def render_text_body(contact, row):
    """Plain-text alternative for the multipart email — a real spam-scoring
    signal (many filters penalize HTML-only messages with no text/plain
    part), and a reasonable plain fallback for any client that prefers it."""
    store_name = contact["store_name"]
    legacy_id = row.get("legacy_id", "")
    link = build_tone_picker_link(legacy_id, store_name)
    is_case_study = _normalize(row.get("dealer_name", "")) == CASE_STUDY_KEY
    is_broken = (num(row.get("rb_reviews_30d")) or 0) <= BROKEN_FEED_THRESHOLD
    total = fmt_int(row.get("total_reviews_30d"))
    rb = fmt_int(row.get("rb_reviews_30d"))
    rb_pct = fmt_pct1(row.get("rb_pct"))

    lines = [
        f"Hello {contact['first_name']}!",
        "",
        "Quick spotlight on your Cars.com ReviewBuilder activity — the automated",
        "review-solicitation feature included with your subscription.",
        "",
        "PICK YOUR CUSTOMER MESSAGE",
        "3 personalized review-request templates, already reviewed and approved by ACA:",
    ]
    for opt in (1, 2, 3):
        subject = MESSAGE_OPTIONS[opt]["subject"].replace("[DealerName]", store_name)
        lines.append(f'  Option {opt}: "{subject}"')
    lines += [
        "",
        f"Preview & choose your message: {link}",
        "(or just reply-all to this email with your option number: 1, 2, or 3)",
        "",
        "When to Send Requests: next day by default (recommended). Want a different",
        "timing (7, 14, or 30 days)? Include it in your reply, e.g. \"Option 2, 7 days.\"",
        "No reply needed if the next-day default works for you.",
        "",
        "REVIEWBUILDER",
        "Turn Every Sale Into a 5-Star Review — Automatically",
        "",
    ]
    if is_broken:
        lines.append(
            f"Worth a Quick Check: {store_name} generated {total} reviews in the last 30 days, "
            f"with only {rb} coming through ReviewBuilder despite being enrolled. Worth a check "
            f"with your Cars.com rep to confirm the feed is capturing your transactions correctly."
        )
    else:
        lines.append(
            f"Your Current Standing: {store_name} generated {total} reviews in the last 30 days, "
            f"with {rb} ({rb_pct}) coming automatically through ReviewBuilder."
        )
    if is_case_study:
        lines.append(
            "\nYou're the Benchmark: Southern Ford is the ACA group's top single-brand "
            "performer on ReviewBuilder this month — every review came in automatically. "
            "Other ACA GMs are seeing this as the standard to aim for. Nice work."
        )
    else:
        lines.append(
            "\nCase Study: Southern Ford generated 90 reviews last month, 100% via ReviewBuilder."
        )
    lines += [
        "",
        "Questions? Just reply to this email.",
        "",
        "Jacob Crawley",
        "Client Service Manager, Enterprise Accounts",
        "M: 918.694.1670",
        "Cars Commerce",
        "Cars.com | Fuel | Dealer Inspire | DealerRater | Accu-Trade",
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="ACA ReviewBuilder Spotlight emails")
    parser.add_argument("--draft", action="store_true", help="Create Gmail drafts for ALL matched stores")
    parser.add_argument("--test-count", type=int, default=1, metavar="N")
    parser.add_argument("--store", default=None, metavar="NAME")
    parser.add_argument("--to", default=None, metavar="EMAIL")
    args = parser.parse_args()

    test_mode = not args.draft
    print(f"\n{'='*60}\nACA ReviewBuilder Spotlight Emails\nMode: {'TEST' if test_mode else 'DRAFT (all matched stores)'}\n{'='*60}\n")

    print("[1/3] Authenticating...")
    gc = get_sheets_client()
    gmail = get_gmail_service()
    print("  ✓ Sheets + Gmail ready\n")

    print("[2/3] Loading contacts and review data...")
    contacts = load_gm_contacts(gc)
    for c in contacts:
        if c["store_key"] in _DISPLAY_OVERRIDES:
            c["store_name"] = _DISPLAY_OVERRIDES[c["store_key"]]
    by_name = load_review_data()
    print(f"  ✓ {len(by_name)} stores in DealerRater dataset\n")

    existing_keys = {c["store_key"] for c in contacts}
    for store_key, override in TEMP_CONTACT_OVERRIDES.items():
        if store_key not in existing_keys and by_name.get(store_key):
            row = by_name[store_key]
            entry = {
                "store_name": row.get("dealer_name", store_key.title()),
                "store_key": store_key,
                "gm_name": override["gm_name"],
                "first_name": override["first_name"],
                "email": override["email"],
            }
            if "_to_list" in override:
                entry["_to_list"] = override["_to_list"]
            contacts.append(entry)

    print("[3/3] Matching contacts to review data...")
    matched, skipped = [], []
    for c in contacts:
        if c["store_key"] in EXCLUDED_KEYS:
            continue
        row = find_review_row(c, by_name)
        if not row:
            skipped.append(f"{c['store_name']} — no DealerRater match")
            continue
        matched.append((c, row))
    print(f"  ✓ {len(matched)} matched, {len(skipped)} skipped")
    for s in skipped:
        print(f"    • {s}")
    print()

    send_list = matched
    if test_mode:
        if args.store:
            needle = args.store.lower()
            send_list = [(c, r) for c, r in matched if needle in c["store_name"].lower()]
            if not send_list:
                print(f"✗ No matched store found for --store '{args.store}'")
                sys.exit(1)
            send_list = send_list[:args.test_count]
        else:
            pool = list(matched)
            random.shuffle(pool)
            send_list = pool[:args.test_count]
        dest = args.to or TEST_EMAIL
        print(f"Test mode: sending {len(send_list)} email(s) to {dest}\n")

    sent = 0
    for contact, row in send_list:
        subject, html_body = render_email(contact, row)
        text_body = render_text_body(contact, row)
        if test_mode:
            to = args.to or TEST_EMAIL
            subject = f"[TEST] {subject}"
            cc = []
        else:
            to = contact.get("_to_list", contact["email"])
            cc = [TEST_EMAIL]  # standing pre-send review rule — Jake CC'd on every draft
        try:
            draft_id = deliver_email(  # ALWAYS draft, never send
                gmail, to, cc, subject, html_body, draft_mode=True, text_body=text_body,
            )
            print(f"  ✓ Drafted: {contact['store_name']} → {to}")
            sent += 1
            if not test_mode:
                # Only log real (non-test) drafts — test sends go to jcrawley,
                # not the real GM, so they'd be a dead end for the reply-poller.
                try:
                    log_pending_send(
                        gc, row.get("legacy_id", ""), contact["store_name"],
                        row.get("dr_id", ""), contact["email"], contact.get("gm_name", ""),
                        draft_id,
                    )
                except Exception as log_err:
                    print(f"    ⚠ Sends-tab log failed for {contact['store_name']}: {log_err}")
        except Exception as e:
            print(f"  ✗ Failed: {contact['store_name']} — {e}")

    print(f"\nDone — {sent} draft(s) created.")
    if test_mode:
        print(f"Check {args.to or TEST_EMAIL}'s inbox, verify rendering, then re-run with --draft for the full batch.")
    print(f"\n{'='*60}\n")


if __name__ == "__main__":
    main()
