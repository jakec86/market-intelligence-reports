#!/usr/bin/env python3
"""
ACA ReviewBuilder Engagement Poller

Polls Gmail for GM replies on each "Sends"-tab thread, extracts a 1/2/3 tone
selection (+ optional timing override), dedupes on Gmail message_id, appends
to the "Engagements" tab, and reconciles per-dealer state into the "Status"
tab that aca_review_config_writer.py reads.

Usage:
    python3 aca_review_engagement_poller.py            # normal run
    python3 aca_review_engagement_poller.py --dry-run   # parse only, no writes
"""

import argparse, base64, html, json, os, re, sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))
from aca_gm_report import get_sheets_client, get_gmail_service  # noqa: E402
from aca_review_shared import (  # noqa: E402
    TRACKING_SHEET_ID, TAB_SENDS, TAB_ENGAGEMENTS, TAB_STATUS,
    VALID_TIMING_DAYS, TIMING_LABEL,
)

SEEN_CACHE_PATH = os.path.expanduser("~/.claude/aca_review_poller_seen_msgids.json")

# Internal AE addresses whose messages in a thread are never a GM's answer.
INTERNAL_SENDERS = {"jcrawley@cars.com", "dmcjunkins@carscommerce.inc"}

QUOTE_MARKERS = [
    re.compile(r"^\s*On .{0,80} wrote:\s*$", re.MULTILINE),
    re.compile(r"^-{2,}\s*Original Message\s*-{2,}", re.MULTILINE | re.IGNORECASE),
    re.compile(r"^From:\s.+$", re.MULTILINE),
]

SELECTION_RE = re.compile(
    r"^\s*(?:option\s*)?([123])\b(?:[,\s-]+(\d{1,2})\s*days?)?",
    re.IGNORECASE,
)


def load_seen_cache():
    if os.path.exists(SEEN_CACHE_PATH):
        with open(SEEN_CACHE_PATH) as f:
            return set(json.load(f))
    return set()


def save_seen_cache(seen):
    os.makedirs(os.path.dirname(SEEN_CACHE_PATH), exist_ok=True)
    with open(SEEN_CACHE_PATH, "w") as f:
        json.dump(sorted(seen), f)


def get_header(message, name):
    for h in message.get("payload", {}).get("headers", []):
        if h["name"].lower() == name.lower():
            return h["value"]
    return ""


def _walk_parts(part, mime_type):
    if part.get("mimeType") == mime_type and part.get("body", {}).get("data"):
        return part["body"]["data"]
    for sub in part.get("parts", []) or []:
        found = _walk_parts(sub, mime_type)
        if found:
            return found
    return None


def extract_plaintext_body(message):
    """Return decoded text/plain body, falling back to a tag-stripped
    text/html body (lower confidence — logged separately by the caller)."""
    payload = message.get("payload", {})
    data = _walk_parts(payload, "text/plain")
    if data:
        return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4)).decode("utf-8", errors="replace"), False

    data = _walk_parts(payload, "text/html")
    if data:
        raw_html = base64.urlsafe_b64decode(data + "=" * (-len(data) % 4)).decode("utf-8", errors="replace")
        text = re.sub(r"<[^>]+>", " ", raw_html)
        text = html.unescape(text)
        text = re.sub(r"\s+", " ", text)
        return text, True

    return "", False


def strip_quoted(text):
    """Keep only the new content above the first quoted-reply marker."""
    earliest = len(text)
    for pattern in QUOTE_MARKERS:
        m = pattern.search(text)
        if m:
            earliest = min(earliest, m.start())
    # Also cut at the first run of '>'-quoted lines
    lines = text.split("\n")
    cut_at = len(lines)
    for i, line in enumerate(lines):
        if line.strip().startswith(">"):
            cut_at = i
            break
    quoted_by_gt = "\n".join(lines[:cut_at])
    return text[:earliest] if earliest < len(quoted_by_gt) else quoted_by_gt


def parse_selection(new_text):
    """Return (option:int|None, timing:str|None, unmatched_timing:str|None)."""
    snippet = new_text.strip()[:200]
    m = SELECTION_RE.search(snippet)
    if not m:
        return None, None, None
    option = int(m.group(1))
    timing_num = m.group(2)
    if timing_num is None:
        return option, None, None
    if timing_num in VALID_TIMING_DAYS:
        return option, timing_num, None
    return option, None, timing_num  # unmatched timing phrase — flagged, not applied


def notify_conflict(gmail_send_fn, dealer_name, legacy_id, detail):
    from aca_gm_report import deliver_email, TEST_EMAIL
    subject = f"⚠ Conflicting ReviewBuilder selection — {dealer_name}"
    body = (
        f"<p><b>{dealer_name}</b> (legacy_id {legacy_id}) has conflicting ReviewBuilder "
        f"tone selections that were NOT auto-applied.</p><pre>{detail}</pre>"
        f"<p>Set a value in the Status tab's resolution_override column to resolve.</p>"
    )
    deliver_email(gmail_send_fn, TEST_EMAIL, ["dmcjunkins@carscommerce.inc"], subject, body, draft_mode=False)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Parse only, make no sheet writes or notifications")
    args = parser.parse_args()

    if not TRACKING_SHEET_ID:
        print("✗ TRACKING_SHEET_ID is empty in aca_review_shared.py — aborting")
        sys.exit(1)

    gc = get_sheets_client()
    gmail = get_gmail_service()
    sh = gc.open_by_key(TRACKING_SHEET_ID)
    sends_ws = sh.worksheet(TAB_SENDS)
    eng_ws = sh.worksheet(TAB_ENGAGEMENTS)
    status_ws = sh.worksheet(TAB_STATUS)

    sends_rows = sends_ws.get_all_records()
    eng_rows = eng_ws.get_all_records()
    status_rows = status_ws.get_all_records()
    status_by_legacy = {r["legacy_id"]: r for r in status_rows}

    seen = load_seen_cache()
    existing_dedupe_keys = {r["dedupe_key"] for r in eng_rows}

    new_engagement_rows = []
    touched_legacy_ids = set()

    for send in sends_rows:
        thread_id = send.get("thread_id", "")
        legacy_id = send.get("legacy_id", "")
        dealer_name = send.get("dealer_name", "")
        if not thread_id:
            continue  # not sent yet (still just a draft) — nothing to poll

        try:
            thread = gmail.users().threads().get(userId="me", id=thread_id, format="full").execute()
        except Exception as e:
            print(f"  ⚠ Could not fetch thread {thread_id} for {dealer_name}: {e}")
            continue

        messages = thread.get("messages", [])[1:]  # skip index 0 = original outbound
        for msg in messages:
            msg_id = msg["id"]
            if msg_id in seen or msg_id in existing_dedupe_keys:
                continue

            from_header = get_header(msg, "From").lower()
            if any(addr in from_header for addr in INTERNAL_SENDERS):
                continue  # internal thread chatter, not the GM's answer

            body_text, is_html_fallback = extract_plaintext_body(msg)
            new_text = strip_quoted(body_text)
            option, timing, unmatched_timing = parse_selection(new_text)

            seen.add(msg_id)  # mark seen regardless of match — never re-parse this message

            if option is None:
                print(f"  ℹ Reply from {dealer_name} has no 1/2/3 selection — needs human attention: {new_text[:80]!r}")
                continue

            evidence = new_text.strip()[:60]
            if unmatched_timing:
                evidence += f" [unmatched timing: {unmatched_timing} days]"
            if is_html_fallback:
                evidence += " [parsed from HTML fallback — lower confidence]"

            new_engagement_rows.append([
                msg_id, datetime.now().isoformat(timespec="seconds"), legacy_id, dealer_name,
                "reply", str(option), timing or "", evidence, msg_id,
            ])
            touched_legacy_ids.add(legacy_id)
            print(f"  ✓ Parsed reply: {dealer_name} → option {option}"
                  + (f", timing {timing} days" if timing else ""))

    if args.dry_run:
        print(f"\n[dry-run] Would append {len(new_engagement_rows)} Engagements row(s); no writes made.")
        return

    if new_engagement_rows:
        eng_ws.append_rows(new_engagement_rows)
        eng_rows.extend([dict(zip(
            ["event_id", "detected_at", "legacy_id", "dealer_name", "channel",
             "option", "timing_override", "raw_evidence", "dedupe_key"], r
        )) for r in new_engagement_rows])

    save_seen_cache(seen)

    # ── Reconcile Status for every dealer with new activity ──────────────────
    status_header = status_ws.row_values(1)
    for legacy_id in touched_legacy_ids:
        dealer_rows = [r for r in eng_rows if r["legacy_id"] == legacy_id]
        combos = {(r["option"], r["timing_override"]) for r in dealer_rows}
        dealer_name = dealer_rows[0]["dealer_name"] if dealer_rows else legacy_id
        existing_status = status_by_legacy.get(legacy_id)

        if existing_status and existing_status.get("resolution_status") == "applied":
            # Late reply after an already-applied write — never silently overwrite.
            detail = f"Already applied: option {existing_status.get('resolved_option')}. New activity: {combos}"
            _upsert_status(status_ws, status_header, legacy_id, dealer_name,
                            "conflict", "", "", "", detail)
            if not args.dry_run:
                notify_conflict(gmail, dealer_name, legacy_id, detail)
            continue

        if len(combos) == 1:
            option, timing = next(iter(combos))
            _upsert_status(status_ws, status_header, legacy_id, dealer_name,
                            "ready", option, timing, "", "")
        else:
            detail = "; ".join(f"option {o}, timing {t or 'default'}" for o, t in combos)
            _upsert_status(status_ws, status_header, legacy_id, dealer_name,
                            "conflict", "", "", "", detail)
            if not args.dry_run:
                notify_conflict(gmail, dealer_name, legacy_id, detail)

    print(f"\nDone — {len(new_engagement_rows)} new engagement(s) logged, "
          f"{len(touched_legacy_ids)} dealer(s) reconciled.")


def _upsert_status(status_ws, header, legacy_id, dealer_name, resolution_status,
                    resolved_option, resolved_timing, conflict_detail_existing, conflict_detail):
    """Find-or-append a Status row for this legacy_id and update it in place."""
    all_values = status_ws.get_all_values()
    row_idx = None
    for i, row in enumerate(all_values[1:], start=2):  # 1-indexed, skip header
        if row and row[0] == legacy_id:
            row_idx = i
            break

    now = datetime.now().isoformat(timespec="seconds")
    new_row = [
        legacy_id, dealer_name, resolution_status, resolved_option, resolved_timing,
        "", conflict_detail, "", "", 0, now,
    ]
    if row_idx:
        status_ws.update(f"A{row_idx}:{chr(64+len(header))}{row_idx}", [new_row])
    else:
        status_ws.append_row(new_row)


if __name__ == "__main__":
    main()
