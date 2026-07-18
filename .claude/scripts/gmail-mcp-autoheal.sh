#!/usr/bin/env bash
# gmail-mcp-autoheal.sh — keep the persistent Gmail MCP HTTP daemon healthy.
#
# Wired to the UserPromptSubmit hook (async). Gmail MCP now runs as a launchd HTTP
# service (com.jcrawley.gmail-mcp-http) on 127.0.0.1:8765, and Claude Code connects
# over HTTP (type:http) — which auto-reconnects on drops. This hook:
#   1. Refreshes ~/.gmail-mcp/credentials.json if the access token expires soon, so a
#      freshly (re)started daemon always loads a valid token.
#   2. Pings the daemon; if it is unresponsive, restarts it via launchd. Claude's HTTP
#      transport then reconnects on its own — NO manual /mcp needed.
#
# Unlike the old stdio setup, a hook CAN restore Gmail here: the daemon is an
# independent process, not a stdio child of the Claude session.

CREDS="$HOME/.gmail-mcp/credentials.json"
KEYS="$HOME/.gmail-mcp/gcp-oauth.keys.json"
PORT=8765
SERVICE="com.jcrawley.gmail-mcp-http"
PLIST="$HOME/Library/LaunchAgents/$SERVICE.plist"
REFRESH_WINDOW_SEC=600   # refresh if access token expires within 10 minutes

# ── 1. Keep the OAuth token fresh ──
if [ -f "$CREDS" ] && [ -f "$KEYS" ]; then
    python3 - "$CREDS" "$KEYS" "$REFRESH_WINDOW_SEC" <<'PY' 2>/dev/null || true
import json, sys, time, urllib.request, urllib.parse
creds_path, keys_path, window = sys.argv[1], sys.argv[2], int(sys.argv[3])
token = json.load(open(creds_path))
if token.get("expiry_date", 0) / 1000.0 - time.time() > window:
    sys.exit(0)  # still fresh
keys = json.load(open(keys_path))["installed"]
data = urllib.parse.urlencode({
    "client_id": keys["client_id"], "client_secret": keys["client_secret"],
    "refresh_token": token["refresh_token"], "grant_type": "refresh_token",
}).encode()
new = json.loads(urllib.request.urlopen(
    urllib.request.Request("https://oauth2.googleapis.com/token", data=data, method="POST"),
    timeout=10).read())
token["access_token"] = new["access_token"]
token["expiry_date"] = int(time.time() * 1000) + new.get("expires_in", 3599) * 1000
json.dump(token, open(creds_path, "w"), indent=2)
PY
fi

# ── 2. Ping the daemon; restart via launchd if it is not answering ──
# Any HTTP response (even 400 "no session") means the daemon is alive; only a
# connection failure (refused/timeout) means it is down.
if ! curl -s -m 2 -o /dev/null "http://127.0.0.1:$PORT/mcp" 2>/dev/null; then
    launchctl kickstart -k "gui/$(id -u)/$SERVICE" 2>/dev/null \
        || launchctl load -w "$PLIST" 2>/dev/null
    jq -nc '{systemMessage: "🟡 Gmail MCP daemon was down — restarted it via launchd. Claude auto-reconnects over HTTP; retry your last Gmail action in a few seconds."}'
fi
exit 0
