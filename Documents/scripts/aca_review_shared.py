#!/usr/bin/env python3
"""
Shared constants/loaders for the ACA ReviewBuilder engagement-automation project.

Single source of truth for the 3 customer-facing message options so the GM
email, the reply-poller, and the DealerRater config-writer never drift from
each other. Also holds the tracking-sheet ID/tab names and the DealerRater
review-data loader (moved here from aca_review_report.py).
"""

import json
import os
import re

# ─── TRACKING SHEET ───────────────────────────────────────────────────────────

# Filled in once the "ACA ReviewBuilder Engagement Tracking" sheet is created
# (see aca_review_tracking_sheet_setup.py). Left blank until then — every
# script that needs it should fail loudly rather than silently no-op.
TRACKING_SHEET_ID = "1ZlEcGNZo0CMGb5BTyW_lbJc09lh5FzCgqbM8bIdPrHM"

TAB_SENDS = "Sends"
TAB_ENGAGEMENTS = "Engagements"
TAB_STATUS = "Status"

SENDS_HEADER = [
    "legacy_id", "dealer_name", "dr_id", "gm_email", "gm_name",
    "draft_id", "thread_id", "message_id", "status", "drafted_at",
]

ENGAGEMENTS_HEADER = [
    "event_id", "detected_at", "legacy_id", "dealer_name",
    "channel", "option", "timing_override", "raw_evidence", "dedupe_key",
]

STATUS_HEADER = [
    "legacy_id", "dealer_name", "resolution_status", "resolved_option",
    "resolved_timing", "resolution_override", "conflict_detail",
    "applied_at", "error_detail", "retry_count", "updated_at",
]

VALID_TIMING_DAYS = {"7", "14", "30"}
TIMING_LABEL = {
    "7": "in 7 Days",
    "14": "in 14 Days",
    "30": "in 30 Days",
}

# ─── MESSAGE OPTIONS ──────────────────────────────────────────────────────────
# Sales Request Email only (Service is explicitly out of scope for this
# automation). Mapped from the source doc's customer-facing templates onto
# DealerRater's actual tags: {{customer_name}} -> [FirstName],
# [Dealership Name] -> [DealerName], [Link to DealerRater Profile] -> dropped
# (DealerRater auto-appends the real review link/CTA outside these fields;
# [ReviewDestination] renders as text naming the destination, e.g. "DealerRater").
# [Car/Service] reworded to sales-specific language. [Your Name] signature
# dropped/reworded as "The [DealerName] Team" to match DealerRater's own
# signature-less default convention.

MESSAGE_OPTIONS = {
    1: {
        "label": "You made history today!",
        "subject": "You made history today!",
        "message": (
            "Hi [FirstName]! We need to talk about what happened after you left. "
            "The moment we finalized your new ride, the showroom turned into a party. "
            "We're talking confetti cannons, a localized “human wave,” and the "
            "biggest miracle of all — our General Manager actually smiled. "
            "(Trust us, he never smiles.) Earning your business was the highlight of "
            "our month! Since you're officially a legend around here now, would you "
            "mind sharing the love with a quick review on [ReviewDestination]? It "
            "takes 60 seconds and helps us keep the celebration going. Thanks for "
            "being awesome! — The [DealerName] Team"
        ),
    },
    2: {
        "label": "Breaking News: You're a local celebrity!",
        "subject": "Breaking News: You're a local celebrity!",
        "message": (
            "Hi [FirstName]! Word travels fast. The second you drove off the lot in "
            "your new ride, the mood here shifted from “business as usual” "
            "to “Super Bowl halftime show.” Our team is currently debating "
            "whether to retire your name to the rafters. There's a rumor that our "
            "General Manager — a man who usually has the facial expressions of a "
            "stone gargoyle — was actually seen doing a victory dance in his "
            "office. We're still checking the security tapes to confirm, but the "
            "vibes are definitely at an all-time high. You officially made our day. "
            "Since you're the talk of the dealership, would you mind keeping the "
            "momentum going by leaving us a review on [ReviewDestination]? It takes "
            "about a minute, and it's the only way we can justify keeping the disco "
            "ball spinning around here. Thanks for being a total rockstar! — The "
            "[DealerName] Team"
        ),
    },
    3: {
        "label": "We're still cleaning up the confetti!",
        "subject": "We're still cleaning up the confetti!",
        "message": (
            "Hi [FirstName]! The second you drove off in your new ride, this place "
            "turned into a stadium! We're talking standing ovations, high-fives "
            "across the showroom, and — get this — our General Manager was "
            "actually caught doing a celebratory moonwalk. Considering he's usually "
            "as stoic as a brick wall, it was a literal historic event. You're "
            "basically a celebrity here now. Could you keep the good vibes rolling "
            "by leaving us a quick review on [ReviewDestination]? It takes 30 "
            "seconds and keeps our GM's rare smile from disappearing. Thanks for "
            "being the MVP today! — The [DealerName] Team"
        ),
    },
}


def _normalize(name):
    """Lowercase, strip punctuation, collapse spaces — matches aca_gm_report._normalize."""
    name = name.lower()
    name = re.sub(r"[^\w\s]", " ", name)
    return re.sub(r"\s+", " ", name).strip()


DEALERRATER_JSON = os.path.expanduser(
    "/private/tmp/claude-501/-Users-jcrawley/45f5ce84-91b4-4396-b164-642a69e19ce9/scratchpad/dealerrater_results.json"
)


def load_review_data():
    """Load dealerrater_results.json, keyed by normalized dealer_name.
    Each row is the raw JSON dict plus a 'legacy_id' key."""
    with open(DEALERRATER_JSON) as f:
        raw = json.load(f)
    by_name = {}
    for legacy_id, row in raw.items():
        row = dict(row)
        row["legacy_id"] = legacy_id
        by_name[_normalize(row["dealer_name"])] = row
    return by_name


def load_review_data_by_legacy_id():
    """Same data as load_review_data(), keyed by legacy_id instead of name."""
    with open(DEALERRATER_JSON) as f:
        raw = json.load(f)
    by_id = {}
    for legacy_id, row in raw.items():
        row = dict(row)
        row["legacy_id"] = legacy_id
        by_id[legacy_id] = row
    return by_id
