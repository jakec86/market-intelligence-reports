#!/usr/bin/env bash
# ACA ReviewBuilder automation cycle — runs the engagement poller then the
# DealerRater config-writer in sequence, so replies detected this cycle get a
# chance to reach 'ready' before the writer looks for work in the same pass.
# Invoked by com.jcrawley.aca-review-cycle.plist every 30 min, business hours.
set -uo pipefail
cd "$(dirname "$0")" || exit 1

LOG="$HOME/Library/Logs/aca_review_cycle.log"
echo "=== $(date) ===" >> "$LOG"

python3 aca_review_engagement_poller.py >> "$LOG" 2>&1
python3 aca_review_config_writer.py >> "$LOG" 2>&1

echo "" >> "$LOG"
