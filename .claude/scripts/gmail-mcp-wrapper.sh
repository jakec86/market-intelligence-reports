#!/usr/bin/env bash
# Wrapper for @shinzolabs/gmail-mcp.
#
# PORT=0 lets the OS assign a free ephemeral port for the internal HTTP server,
# eliminating EADDRINUSE crashes when port 3100 is held by a stale process.
#
# Crashes are logged to $TMPDIR/gmail-mcp.log for diagnosis.

LOGFILE="${TMPDIR:-/tmp}/gmail-mcp.log"
GMAIL_MCP_BIN="$HOME/.npm-global/bin/gmail-mcp"

export PORT=0
export GMAIL_OAUTH_PATH="${GMAIL_OAUTH_PATH:-$HOME/.gmail-mcp/gcp-oauth.keys.json}"
export GMAIL_CREDENTIALS_PATH="${GMAIL_CREDENTIALS_PATH:-$HOME/.gmail-mcp/credentials.json}"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] gmail-mcp starting (wrapper PID $$)" >> "$LOGFILE" 2>/dev/null

# Run gmail-mcp as a child (not exec) so we can log the exit code.
# stdin/stdout are inherited so the MCP stdio transport works normally.
"$GMAIL_MCP_BIN" "$@"
EXIT_CODE=$?

echo "[$(date '+%Y-%m-%d %H:%M:%S')] gmail-mcp exited (code $EXIT_CODE)" >> "$LOGFILE" 2>/dev/null
exit $EXIT_CODE
