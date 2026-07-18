---
name: Playwright MCP Download Path
description: Playwright MCP browser downloads land in ~/.playwright-mcp/, NOT ~/Downloads/ — scripts must check both
type: reference
originSessionId: f3635768-f407-43b2-b5b3-c6bedfb26fd9
---
Files downloaded via the Playwright MCP browser (either by Claude automation or by the user in that same browser session) land in `~/.playwright-mcp/`, not `~/Downloads/`.

**How to apply:**
- When a PB/Tableau script expects a CSV, always check `~/.playwright-mcp/*.csv` first, fallback to `~/Downloads/*.csv`.
- When asking the user to "download to ~/Downloads", clarify that if they use the Claude-controlled Playwright browser the file actually lands in `~/.playwright-mcp/`.
- Filenames in `~/.playwright-mcp/` are sanitized (e.g. `Low-Engaged-Inventory-Report---Local-v2.csv`, not the Tableau-default `Low Engaged Inventory Report - Local v2 - 2026-04-17T...csv`).

**Why:** Chromium's download path is configured per-session by Playwright; the MCP server sets it to its own workdir. Caught by observation during /nalley-pb-report run 2026-04-17 — script failed to find the user's CSV because it only scanned ~/Downloads/.
