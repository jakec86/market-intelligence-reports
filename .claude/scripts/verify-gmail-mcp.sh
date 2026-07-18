#!/bin/bash
# Verify Gmail MCP credentials file exists and contains a refresh token.
# The SessionStart hook already refreshes the access token; this catches
# cases where the credentials file itself is missing or corrupted.

CREDS="/Users/jcrawley/.gmail-mcp/credentials.json"

if [ ! -f "$CREDS" ]; then
    jq -nc '{systemMessage: "⚠️ Gmail MCP credentials missing at ~/.gmail-mcp/credentials.json — Gmail tools will not work. Re-run OAuth flow."}'
    exit 0
fi

REFRESH=$(python3 -c "import json; print(json.load(open('$CREDS')).get('refresh_token',''))" 2>/dev/null)
if [ -z "$REFRESH" ]; then
    jq -nc '{systemMessage: "⚠️ Gmail MCP credentials have no refresh token — re-run OAuth flow to restore Gmail access."}'
fi
