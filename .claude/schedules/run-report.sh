#!/bin/bash
# Wrapper script for headless Claude Code PB report execution
# Usage: run-report.sh <skill-name>
#   e.g.: run-report.sh /nalley-pb-report
#         run-report.sh /hendricks-pb-report
#
# Reliability features:
#   - Real 30-min timeout per attempt (background watchdog — macOS has no `timeout`)
#   - Up to 3 attempts with backoff (transient Claude API errors killed 3 of 6
#     scheduled runs in May–June 2026; retries are prompted to check for
#     already-sent/drafted reports before resuming, to avoid double-sends)
#   - On final failure: macOS notification + email alert to jcrawley@cars.com
#     via the Gmail API (independent of the Claude API, so it works when the
#     run failed precisely because the Claude API was down)

SKILL="$1"
LOGDIR="/Users/jcrawley/.claude/logs"
LOGFILE="${LOGDIR}/$(echo "$SKILL" | tr '/' '-' | sed 's/^-//').log"
ERRFILE="${LOGDIR}/$(echo "$SKILL" | tr '/' '-' | sed 's/^-//').err"

TIMEOUT_SECS=1800
MAX_ATTEMPTS=3
RETRY_WAITS=(0 120 300)   # seconds to wait before attempts 1, 2, 3

mkdir -p "$LOGDIR"

# Set env explicitly — do NOT source .zshrc (bash + set -e + zsh-only commands = exit 127)
export HOME="/Users/jcrawley"
export PATH="$HOME/.npm-global/bin:$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
export ANTHROPIC_API_KEY="$(security find-generic-password -s 'anthropic-api-key' -w 2>/dev/null || true)"
export TABLEAU_PAT_SECRET="$(security find-generic-password -a jcrawley -s 'tableau-pat' -w 2>/dev/null || true)"
export TABLEAU_PAT_NAME="Claude"

cleanup_stale_processes() {
  # Kill any stale Gmail MCP process on port 3100
  lsof -ti :3100 2>/dev/null | xargs kill -9 2>/dev/null || true
  # Kill stale Playwright/Chrome that would lock the browser profile on the next run.
  # Safe to kill: the headless profile is only used by these scheduled jobs, never
  # by interactive sessions (which use a separate profile path).
  pkill -f "mcp-chrome-9140e24" 2>/dev/null || true
  pkill -f "playwright-mcp --headless" 2>/dev/null || true
  sleep 2
}

run_claude_with_timeout() {
  local prompt="$1"
  /Users/jcrawley/.local/bin/claude \
    -p "$prompt" \
    --model "opus[1m]" \
    --mcp-config /Users/jcrawley/.claude/schedules/mcp-config.json \
    --add-dir /Users/jcrawley/Documents/scripts \
    --dangerously-skip-permissions \
    --verbose \
    >> "$LOGFILE" 2>> "$ERRFILE" &
  local pid=$!
  ( sleep "$TIMEOUT_SECS"; if kill -0 "$pid" 2>/dev/null; then
      echo "=== $(date) === TIMEOUT after ${TIMEOUT_SECS}s — killing PID $pid ===" >> "$LOGFILE"
      kill -9 "$pid" 2>/dev/null
    fi ) &
  local watchdog=$!
  wait "$pid"
  local rc=$?
  # Tear down the watchdog and its sleep so it can't fire on a recycled PID
  pkill -P "$watchdog" 2>/dev/null || true
  kill "$watchdog" 2>/dev/null || true
  return $rc
}

notify_failure() {
  local rc="$1"
  # Desktop notification (best-effort; no-op when no GUI session)
  osascript -e "display notification \"$SKILL failed after $MAX_ATTEMPTS attempts (exit $rc) — see $LOGFILE\" with title \"Scheduled report FAILED\"" 2>/dev/null || true
  # Email alert via Gmail API (uses pb_report.py's existing token/refresh path)
  SKILL_NAME="$SKILL" RC_VAL="$rc" LOGFILE_PATH="$LOGFILE" ERRFILE_PATH="$ERRFILE" \
  python3 - <<'PYEOF' 2>>"$ERRFILE" || echo "=== $(date) === Failure-alert email could not be sent ===" >> "$LOGFILE"
import base64, os, sys
from email.mime.text import MIMEText
sys.path.insert(0, os.path.expanduser("~/Documents/scripts"))
from pb_report import get_gmail_service

skill, rc = os.environ["SKILL_NAME"], os.environ["RC_VAL"]
def tail(path, n=30):
    try:
        with open(path) as f:
            return "".join(f.readlines()[-n:])
    except Exception:
        return "(unreadable)"

body = (f"Scheduled run {skill} FAILED (exit {rc}) after all retry attempts.\n\n"
        f"=== last 30 log lines ===\n{tail(os.environ['LOGFILE_PATH'])}\n"
        f"=== last 10 err lines ===\n{tail(os.environ['ERRFILE_PATH'], 10)}\n\n"
        f"Recover manually: run {skill} in an interactive session.")
msg = MIMEText(body)
msg["To"] = "jcrawley@cars.com"
msg["From"] = "jcrawley@cars.com"
msg["Subject"] = f"⚠️ Scheduled report FAILED: {skill} (exit {rc})"
raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
get_gmail_service().users().messages().send(userId="me", body={"raw": raw}).execute()
print("failure alert emailed")
PYEOF
}

RC=1
for (( attempt=1; attempt<=MAX_ATTEMPTS; attempt++ )); do
  wait_secs="${RETRY_WAITS[$((attempt-1))]:-300}"
  [ "$wait_secs" -gt 0 ] && sleep "$wait_secs"
  cleanup_stale_processes

  if [ "$attempt" -eq 1 ]; then
    PROMPT="$SKILL"
  else
    PROMPT="$SKILL retry attempt $attempt of $MAX_ATTEMPTS — a previous attempt failed partway (likely a transient API error). Before drafting or sending anything, check Gmail sent mail and drafts for today's report: if it was already sent, stop and report success; if a draft exists, resume from that point. Do not create duplicate drafts or double-send."
  fi

  echo "=== $(date) === Running $SKILL (attempt $attempt/$MAX_ATTEMPTS) ===" >> "$LOGFILE"
  RC=0
  run_claude_with_timeout "$PROMPT" || RC=$?
  echo "=== $(date) === Finished $SKILL attempt $attempt (exit: $RC) ===" >> "$LOGFILE"
  [ "$RC" -eq 0 ] && break
done

if [ "$RC" -ne 0 ]; then
  echo "=== $(date) === $SKILL FAILED after $MAX_ATTEMPTS attempts — sending alert ===" >> "$LOGFILE"
  notify_failure "$RC"
fi

exit $RC
