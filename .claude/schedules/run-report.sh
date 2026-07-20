#!/bin/bash
# Wrapper script for headless Claude Code PB report execution
# Usage: run-report.sh <skill-name>
#   e.g.: run-report.sh /nalley-pb-report
#         run-report.sh /hendricks-pb-report
#
# Reliability features:
#   - Auth pre-flight: a trivial claude -p ping before the retry loop. A 401
#     (expired/invalid claude.ai OAuth login) is NOT transient, so we abort
#     immediately with a distinct "AUTH EXPIRED — run /login" alert instead of
#     burning all 3 long retries. (2026-06-22: an expired OAuth token 401'd all 6
#     Hendrick+Nalley attempts in seconds and only surfaced via the failure email.)
#   - In-loop 401 short-circuit: if any attempt's log shows a 401, stop retrying.
#   - Real 45-min timeout per attempt (background watchdog — macOS has no `timeout`)
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

# 2026-06-15: raised 1800->2700 (45 min) hard wall-clock cap. A cold run took
# ~30 min and met the old 30-min wall — the send landed at the wire, then SIGKILL
# logged exit 137 before the run could record success, triggering an idempotent
# retry (no double-send, but every report ran ~2x and the logs looked like
# failures). The ~5-min cold-start is now cut by SECURITY_GUIDANCE_DISABLE (see
# exports below; measured 327s -> 24s); 45 min is comfortable headroom on top.
TIMEOUT_SECS=2700
MAX_ATTEMPTS=3
RETRY_WAITS=(0 120 300)   # seconds to wait before attempts 1, 2, 3
# Stall detector: kill a run early if its session transcript shows zero activity
# for this long AFTER work has started (the MCP cold-start, which has no transcript
# writes, never trips it — see run_claude_with_timeout). A hard mid-run hang then
# fails fast into the retry loop instead of burning to TIMEOUT_SECS. 600s = 10 min;
# the longest legit quiet gap observed was ~3 min.
STALL_SECS=600

mkdir -p "$LOGDIR"

# Set env explicitly — do NOT source .zshrc (bash + set -e + zsh-only commands = exit 127)
export HOME="/Users/jcrawley"
export PATH="$HOME/.npm-global/bin:$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
export ANTHROPIC_API_KEY="$(security find-generic-password -s 'anthropic-api-key' -w 2>/dev/null || true)"
export TABLEAU_PAT_SECRET="$(security find-generic-password -a jcrawley -s 'tableau-pat' -w 2>/dev/null || true)"
export TABLEAU_PAT_NAME="Claude"
# THE cold-start fix. The security-guidance plugin's hooks (UserPromptSubmit/Stop)
# run an agent-SDK LLM security review that blocked turn 1 for ~5 MIN per headless
# run (measured: 327s -> 24s with this set) and add no value to a trusted, repeating
# automated report. SECURITY_GUIDANCE_DISABLE=1 is the plugin's documented master
# kill switch (security_reminder_hook.py:2160 -> sys.exit(0)). Interactive sessions,
# which don't source this script, keep the plugin.
export SECURITY_GUIDANCE_DISABLE=1

# Per-dealer isolation: each report gets its own MCP config + browser profile so
# concurrent runs (Hendrick 7:30 + Nalley 8:00 on Mondays) never share a profile
# or kill each other's browser during cleanup.
case "$SKILL" in
  *nalley*)   DEALER=nalley ;;
  *hendrick*) DEALER=hendrick ;;
  *dyer*)     DEALER=dyer ;;
  *)          DEALER=default ;;
esac
MCP_CONFIG="$HOME/.claude/schedules/mcp-config-${DEALER}.json"
[ -f "$MCP_CONFIG" ] || MCP_CONFIG="$HOME/.claude/schedules/mcp-config.json"
PROFILE_DIR="$HOME/Library/Caches/ms-playwright-mcp/${DEALER}-profile"
# Empty MCP config for the auth pre-flight: load NO servers so the ping is a pure
# auth/model check (no playwright/gmail cold-start, no false negatives from a down MCP).
EMPTY_MCP_CONFIG="$HOME/.claude/schedules/mcp-config-empty.json"

cleanup_stale_processes() {
  # Scoped to THIS dealer's profile only — a concurrent run for another dealer
  # (different --user-data-dir) is never touched, nor is an interactive Playwright.
  # Kills any playwright-mcp/Chrome bound to this profile, then clears stale
  # Singleton locks a kill -9 left behind (a leftover lock hangs the next launch).
  pkill -f "${DEALER}-profile" 2>/dev/null || true
  rm -f "$PROFILE_DIR"/Singleton* 2>/dev/null || true
  sleep 2
}

# Regex matching the CLI's authentication-failure output. A 401 here means the
# claude.ai OAuth login token is expired/invalid — not a transient API blip — so
# retrying is pointless. Kept broad to catch wording changes across CLI versions.
AUTH_FAIL_RE='API Error: 401|Invalid authentication credentials|Failed to authenticate|authentication_error|OAuth token (has )?expired|Please run /login|Invalid bearer token'

# Cheap, pure-auth pre-flight: a trivial prompt with NO MCP servers loaded. Returns
# 2 on a detected auth failure (caller aborts fast), 0 otherwise. A non-auth error
# is treated as inconclusive (return 0) so a flaky ping never blocks a real run.
preflight_auth() {
  local out rc
  out="$(/Users/jcrawley/.local/bin/claude \
          -p "Reply with the single word: OK" \
          --model "opus[1m]" \
          --mcp-config "$EMPTY_MCP_CONFIG" \
          --strict-mcp-config \
          < /dev/null 2>&1)"
  rc=$?
  if printf '%s\n' "$out" | grep -qiE "$AUTH_FAIL_RE"; then
    echo "=== $(date) === AUTH PRE-FLIGHT: detected auth failure ===" >> "$LOGFILE"
    printf '%s\n' "$out" | tail -3 >> "$LOGFILE"
    return 2
  fi
  echo "=== $(date) === AUTH PRE-FLIGHT: ok (rc=$rc) ===" >> "$LOGFILE"
  return 0
}

run_claude_with_timeout() {
  local prompt="$1"

  # Snapshot existing session transcripts so the stall detector can identify
  # THIS run's transcript (the new .jsonl that appears after launch).
  local PROJDIR="$HOME/.claude/projects"
  local before_tx
  before_tx="$(mktemp -t pb_tx_before)"
  find "$PROJDIR" -name '*.jsonl' 2>/dev/null | sort > "$before_tx"

  # --strict-mcp-config: load ONLY the servers in $MCP_CONFIG (playwright + gmail),
  # not all ~37 from ~/.claude.json. Hygiene (fewer node procs + failure surface;
  # ~7s saved) — NOT the cold-start fix: the ~5-min cold-start was the
  # security-guidance plugin hook, killed via SECURITY_GUIDANCE_DISABLE above. The
  # workflow only uses playwright + gmail. `< /dev/null` drops a 3s "no stdin" wait.
  /Users/jcrawley/.local/bin/claude \
    -p "$prompt" \
    --model "opus[1m]" \
    --mcp-config "$MCP_CONFIG" \
    --strict-mcp-config \
    --add-dir /Users/jcrawley/Documents/scripts \
    --dangerously-skip-permissions \
    --verbose \
    < /dev/null \
    >> "$LOGFILE" 2>> "$ERRFILE" &
  local pid=$!

  # Hard wall-clock timeout (background watchdog — macOS has no `timeout`).
  ( sleep "$TIMEOUT_SECS"; if kill -0 "$pid" 2>/dev/null; then
      echo "=== $(date) === TIMEOUT after ${TIMEOUT_SECS}s — killing PID $pid ===" >> "$LOGFILE"
      kill -9 "$pid" 2>/dev/null
    fi ) &
  local watchdog=$!

  # No-activity stall detector: kill the run early if its transcript goes silent
  # for STALL_SECS *after* work has begun, so a hard mid-run hang fails fast into
  # the retry loop. Armed only once the transcript is modified >30s post-launch,
  # so the MCP cold-start (no transcript writes) never trips it. Runs in a subshell;
  # vars are subshell-local so nothing leaks to the function.
  ( tx=""; armed=0; t0=$(date +%s)
    while kill -0 "$pid" 2>/dev/null; do
      sleep 30
      if [ -z "$tx" ]; then
        newest=""; newest_mt=0
        while IFS= read -r f; do
          [ -f "$f" ] || continue
          fmt="$(stat -f %m "$f" 2>/dev/null)" || continue
          if [ "$fmt" -gt "$newest_mt" ]; then newest_mt="$fmt"; newest="$f"; fi
        done < <(comm -13 "$before_tx" <(find "$PROJDIR" -name '*.jsonl' 2>/dev/null | sort))
        tx="$newest"
        continue
      fi
      [ -f "$tx" ] || continue
      mt="$(stat -f %m "$tx" 2>/dev/null)" || continue
      if [ "$armed" -eq 0 ]; then
        [ "$mt" -gt $(( t0 + 30 )) ] && armed=1
        continue
      fi
      if [ $(( $(date +%s) - mt )) -ge "$STALL_SECS" ]; then
        echo "=== $(date) === STALL: no transcript activity for >=${STALL_SECS}s — killing PID $pid ===" >> "$LOGFILE"
        kill -9 "$pid" 2>/dev/null
        break
      fi
    done ) &
  local staller=$!

  wait "$pid"
  local rc=$?
  # Tear down both monitors (and their child sleeps) so neither fires on a recycled PID.
  pkill -P "$watchdog" 2>/dev/null || true
  kill "$watchdog" 2>/dev/null || true
  pkill -P "$staller" 2>/dev/null || true
  kill "$staller" 2>/dev/null || true
  rm -f "$before_tx"
  return $rc
}

notify_failure() {
  local rc="$1"
  # Desktop notification (best-effort; no-op when no GUI session)
  osascript -e "display notification \"$SKILL failed after $MAX_ATTEMPTS attempts (exit $rc) — see $LOGFILE\" with title \"Scheduled report FAILED\"" 2>/dev/null || true
  # Email alert. PRIMARY: the always-on Gmail MCP HTTP daemon (127.0.0.1:8765,
  # launchd KeepAlive — independent of pb_report and its OAuth token, and uses no
  # heavy imports, so it survives the post-crash environment that broke the old
  # `from pb_report import` path on 2026-06-12). FALLBACK: pb_report's Gmail API.
  SKILL_NAME="$SKILL" RC_VAL="$rc" LOGFILE_PATH="$LOGFILE" ERRFILE_PATH="$ERRFILE" \
  python3 - <<'PYEOF' 2>>"$ERRFILE" || echo "=== $(date) === Failure-alert email could not be sent ===" >> "$LOGFILE"
import os, json, urllib.request

skill, rc = os.environ["SKILL_NAME"], os.environ["RC_VAL"]
reason = os.environ.get("FAIL_REASON", "").strip()
def tail(path, n=30):
    try:
        with open(path) as f:
            return "".join(f.readlines()[-n:])
    except Exception:
        return "(unreadable)"

subject = f"⚠️ Scheduled report FAILED: {skill} (exit {rc})" + (f" — {reason}" if reason else "")
recover = (f"AUTH: run /login in an interactive Claude Code session to refresh the "
           f"claude.ai OAuth token, then re-run {skill}.") if reason.startswith("AUTH") \
          else f"Recover manually: run {skill} in an interactive session."
body = (f"Scheduled run {skill} FAILED (exit {rc}).\n"
        + (f"Reason: {reason}\n" if reason else "")
        + f"\n=== last 30 log lines ===\n{tail(os.environ['LOGFILE_PATH'])}\n"
        f"=== last 10 err lines ===\n{tail(os.environ['ERRFILE_PATH'], 10)}\n\n"
        f"{recover}")

def _rpc(payload, sid=None):
    h = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
    if sid:
        h["mcp-session-id"] = sid
    req = urllib.request.Request("http://127.0.0.1:8765/mcp",
                                 data=json.dumps(payload).encode(), headers=h, method="POST")
    with urllib.request.urlopen(req, timeout=15) as r:
        sid_out, raw = r.headers.get("mcp-session-id"), r.read().decode()
    data = None
    for line in raw.splitlines():
        s = line.strip()
        if s.startswith("data:"):
            try:
                data = json.loads(s[5:].strip())
            except Exception:
                pass
    return sid_out, data

def send_via_daemon():
    sid, _ = _rpc({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                   "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                              "clientInfo": {"name": "pb-alert", "version": "1"}}})
    _rpc({"jsonrpc": "2.0", "method": "notifications/initialized"}, sid)
    _, res = _rpc({"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                   "params": {"name": "send_message",
                              "arguments": {"to": ["jcrawley@cars.com"],
                                            "subject": subject, "body": body}}}, sid)
    if not res or res.get("error") or (res.get("result") or {}).get("isError"):
        raise RuntimeError("daemon send rejected: " + json.dumps(res)[:200])

def send_via_pbreport():
    import base64, sys
    from email.mime.text import MIMEText
    sys.path.insert(0, os.path.expanduser("~/Documents/scripts"))
    from pb_report import get_gmail_service
    m = MIMEText(body)
    m["To"] = "jcrawley@cars.com"; m["From"] = "jcrawley@cars.com"; m["Subject"] = subject
    raw = base64.urlsafe_b64encode(m.as_bytes()).decode()
    get_gmail_service().users().messages().send(userId="me", body={"raw": raw}).execute()

try:
    send_via_daemon()
    print("failure alert emailed via gmail daemon")
except Exception as e1:
    try:
        send_via_pbreport()
        print("failure alert emailed via pb_report fallback (daemon failed: %s)" % e1)
    except Exception as e2:
        raise SystemExit("both alert paths failed: daemon=%s; pbreport=%s" % (e1, e2))
PYEOF
}

# Auth pre-flight — fail fast on an expired/invalid claude.ai OAuth login (401)
# rather than burning all MAX_ATTEMPTS × TIMEOUT_SECS retries on a non-transient error.
if ! preflight_auth; then
  echo "=== $(date) === $SKILL ABORTED before run — claude.ai OAuth token invalid/expired (401) ===" >> "$LOGFILE"
  FAIL_REASON="AUTH EXPIRED — run /login to refresh the claude.ai OAuth token" notify_failure 3
  exit 3
fi

RC=1
AUTH_FAIL=0
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

  # In-loop 401 short-circuit: if this attempt failed on auth, the token died
  # mid-batch — retrying won't help. Stop now and alert with the auth reason.
  if tail -n 25 "$LOGFILE" | grep -qiE "$AUTH_FAIL_RE"; then
    echo "=== $(date) === AUTH 401 detected during attempt $attempt — aborting remaining retries ===" >> "$LOGFILE"
    AUTH_FAIL=1
    break
  fi
done

if [ "$RC" -ne 0 ]; then
  if [ "$AUTH_FAIL" -eq 1 ]; then
    echo "=== $(date) === $SKILL FAILED (auth 401 mid-run) — sending alert ===" >> "$LOGFILE"
    FAIL_REASON="AUTH EXPIRED — run /login to refresh the claude.ai OAuth token" notify_failure "$RC"
  else
    echo "=== $(date) === $SKILL FAILED after $MAX_ATTEMPTS attempts — sending alert ===" >> "$LOGFILE"
    notify_failure "$RC"
  fi
fi

exit $RC
