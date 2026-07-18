#!/bin/bash
# Pre-warm MCP connections at session start by making lightweight test calls.
# Failures are warnings, not hard stops — the session should still proceed.

ERRORS=()

# ── Tableau PAT: lightweight ping via sign-in (already validated by check-tableau-pat.sh) ──
# Skipped here to avoid duplicate work with the existing hook.

# ── Gmail: verify credentials.json is present and has a refresh token ──
CREDS="/Users/jcrawley/.gmail-mcp/credentials.json"
if [ ! -f "$CREDS" ]; then
    ERRORS+=("Gmail credentials missing at ~/.gmail-mcp/credentials.json")
elif ! python3 -c "import json; d=json.load(open('$CREDS')); assert d.get('refresh_token'), 'no refresh_token'" 2>/dev/null; then
    ERRORS+=("Gmail credentials have no refresh_token — re-run OAuth flow")
fi

# ── Google Sheets: verify token file exists ──
SHEETS_TOKEN="/Users/jcrawley/.claude/tokens/sheets_token.json"
if [ ! -f "$SHEETS_TOKEN" ]; then
    ERRORS+=("Google Sheets token missing at ~/.claude/tokens/sheets_token.json")
fi

# ── Playwright: verify npx is available (Playwright MCP starts on demand) ──
if ! command -v npx &>/dev/null; then
    ERRORS+=("npx not found — Playwright MCP will not start")
fi

# ── State dir: ensure checkpoint directory exists ──
mkdir -p /Users/jcrawley/.claude/state

# ── Output ──
if [ ${#ERRORS[@]} -gt 0 ]; then
    MSG=$(printf '%s\n' "${ERRORS[@]}" | paste -sd '; ' -)
    jq -nc --arg m "⚠️ Pre-warm warnings — $MSG" '{systemMessage: $m}'
fi
