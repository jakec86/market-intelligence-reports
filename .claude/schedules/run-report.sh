#!/bin/bash
# Wrapper script for headless Claude Code PB report execution
# Usage: run-report.sh <skill-name>
#   e.g.: run-report.sh /nalley-pb-report
#         run-report.sh /hendricks-pb-report

SKILL="$1"
LOGDIR="/Users/jcrawley/.claude/logs"
LOGFILE="${LOGDIR}/$(echo "$SKILL" | tr '/' '-' | sed 's/^-//').log"
ERRFILE="${LOGDIR}/$(echo "$SKILL" | tr '/' '-' | sed 's/^-//').err"

mkdir -p "$LOGDIR"

# Set env explicitly — do NOT source .zshrc (bash + set -e + zsh-only commands = exit 127)
export HOME="/Users/jcrawley"
export PATH="$HOME/.npm-global/bin:$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
export ANTHROPIC_API_KEY="$(security find-generic-password -s 'anthropic-api-key' -w 2>/dev/null || true)"
export TABLEAU_PAT_SECRET="$(security find-generic-password -a jcrawley -s 'tableau-pat' -w 2>/dev/null || true)"
export TABLEAU_PAT_NAME="Claude"

# Kill any stale Gmail MCP process on port 3100
lsof -ti :3100 2>/dev/null | xargs kill -9 2>/dev/null || true

echo "=== $(date) === Running $SKILL ===" >> "$LOGFILE"

RC=0
/Users/jcrawley/.local/bin/claude \
  -p "$SKILL" \
  --model "opus[1m]" \
  --mcp-config /Users/jcrawley/.claude/schedules/mcp-config.json \
  --add-dir /Users/jcrawley \
  --dangerously-skip-permissions \
  --verbose \
  >> "$LOGFILE" 2>> "$ERRFILE" || RC=$?

echo "=== $(date) === Finished $SKILL (exit: $RC) ===" >> "$LOGFILE"
exit $RC
