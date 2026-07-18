#!/usr/bin/env bash
# Weekly Marketplace Metrics (Connections) tracker — runs market_metrics_weekly.py,
# which is fully self-contained (Playwright pip package + Keychain + Sheets REST API,
# no Claude API / MCP dependency), so this is a plain script wrapper, not a
# claude -p skill invocation like the PB reports use.
# Invoked by com.jcrawley.market-metrics-weekly.plist, Mondays 8:00 AM.
set -uo pipefail
cd "$(dirname "$0")" || exit 1

LOG="$HOME/Library/Logs/market_metrics_weekly.log"
echo "=== $(date) ===" >> "$LOG"

python3 market_metrics_weekly.py >> "$LOG" 2>&1
STATUS=$?

if [ $STATUS -ne 0 ]; then
    echo "market_metrics_weekly.py exited $STATUS" >> "$LOG"
fi

echo "" >> "$LOG"
exit $STATUS
