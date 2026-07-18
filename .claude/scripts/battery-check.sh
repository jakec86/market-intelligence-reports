#!/bin/bash
# Block tool use when battery is critically low (< 5%) and not on AC power.
BATT=$(pmset -g batt 2>/dev/null)
PCT=$(echo "$BATT" | grep -Eo '[0-9]+%' | head -1 | tr -d '%')
AC=$(echo "$BATT" | grep -c 'AC Power' 2>/dev/null || echo 0)

# Allow if: battery unreadable, on AC power, or charge > 5%
if [ -z "$PCT" ] || [ "$AC" -gt 0 ] || [ "$PCT" -gt 5 ]; then
  exit 0
fi

jq -nc --arg p "$PCT" '{
  "systemMessage": ("⚠️  Battery at " + $p + "% — tool use paused to prevent draining to 0. Plug in or charge above 5% to continue."),
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": ("Battery at " + $p + "% — paused to protect battery. Plug in or charge above 5% to resume.")
  }
}'
