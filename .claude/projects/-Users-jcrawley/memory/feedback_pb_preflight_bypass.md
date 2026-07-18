---
name: PB Report Pre-flight Bypass Rules
description: When to skip pre-flight checks in PB report workflows and fall back to Playwright
type: feedback
originSessionId: 1c9763c3-f674-4172-bbda-b16a9cd87d15
---
Skip TOTP pre-flight check until further notice — Keychain seed not yet enrolled, user approves JumpCloud Mobile Push manually if SSO is hit.

If Tableau MCP returns 401 or is disconnected, skip the MCP pre-flight and proceed directly to Playwright for the LEI download (navigate to Tableau web UI, apply filters, download crosstab). Do not abort — move to Playwright without waiting for MCP reconnect.

**Why:** Tableau MCP 401 can persist even after `/mcp` reconnect; Playwright is a reliable fallback. TOTP setup is blocked pending IT reset.

**How to apply:** In Step 0 of any PB report, if TOTP check fails → continue. If Tableau MCP 401 → skip to Playwright. Surface the failures as informational but do not abort.
