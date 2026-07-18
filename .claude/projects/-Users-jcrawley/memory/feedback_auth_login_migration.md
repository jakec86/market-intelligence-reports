---
name: Claude Code Auth — Login Migration (4/11/2026)
description: Claude Code CLI uses login OAuth auth as of 4/11/2026 — no API key needed for the CLI itself
type: feedback
originSessionId: 03d05f28-537c-427b-8ddd-843e4a0e41e1
---
As of 4/11/2026, Claude Code CLI authenticates via `claude.ai` login (OAuth), not an API key.

**Why:** Anthropic forced migration from API-key to login-based auth for Claude Code on this date.

**How to apply:**
- Never instruct the user to set `ANTHROPIC_API_KEY` as a requirement for running Claude Code itself
- `ANTHROPIC_API_KEY` is still needed for standalone Python scripts that use the Anthropic SDK directly (`dealer_health.py`, `cowork.py`) — it's sourced from macOS Keychain via `.zshrc`
- To re-authenticate Claude Code: run `/login`
- The two auth systems are independent: Python SDK = API key from Keychain; Claude Code CLI = OAuth login
