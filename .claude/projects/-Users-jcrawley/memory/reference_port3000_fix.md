---
name: Gmail MCP HTTP Daemon (auto-reconnect)
description: Gmail MCP now runs as a persistent loopback HTTP launchd daemon so Claude Code auto-reconnects on drops. Root cause of old "fails often" was port-3000 collisions from unconditional app.listen. Includes management commands + npm-update re-patch.
type: reference
originSessionId: 2a77f998-3c76-4ca9-b787-d74faaf78a90
---

## Current architecture (2026-06-12) — HTTP daemon

Gmail MCP runs as a **persistent launchd HTTP service**, and Claude Code connects to it over HTTP (which auto-reconnects with backoff). No more manual `/mcp`.

- **Service:** `com.jcrawley.gmail-mcp-http` — plist at `~/Library/LaunchAgents/com.jcrawley.gmail-mcp-http.plist` (RunAtLoad + KeepAlive=true).
- **Endpoint:** `http://127.0.0.1:8765/mcp` — **loopback only** (the Smithery HTTP server is UNAUTHENTICATED; never bind all interfaces).
- **Claude config:** `~/.claude.json` → `projects["/Users/jcrawley"].mcpServers.gmail = {"type":"http","url":"http://127.0.0.1:8765/mcp"}`.
- **Package patch** (`@shinzolabs/gmail-mcp/dist/index.js`): `app.listen(PORT, '127.0.0.1')` + skip stdio when `GMAIL_HTTP_ONLY=1`. **`npm update` reverts this** → re-apply with `~/.claude/scripts/gmail-mcp-http-patch.sh`, then `launchctl kickstart -k gui/$(id -u)/com.jcrawley.gmail-mcp-http`.
- **Autoheal hook** (`~/.claude/scripts/gmail-mcp-autoheal.sh`, UserPromptSubmit async): refreshes the token + pings the daemon and `launchctl kickstart`s it if down. A hook CAN recover Gmail now because the daemon is independent of the session (unlike the old stdio child).
- **SessionEnd `pkill gmail-mcp` hook REMOVED** — it would kill the daemon.

### Manage it
- Status: `launchctl list | grep gmail-mcp-http` (status 0 = ok)
- Restart: `launchctl kickstart -k gui/$(id -u)/com.jcrawley.gmail-mcp-http`
- Stop:    `launchctl bootout gui/$(id -u)/com.jcrawley.gmail-mcp-http`
- Logs:    `~/.claude/logs/gmail-mcp-http.log`
- Activate after config change: **restart the Claude session** (CC reads MCP config at startup).

## Root cause of the old "fails often" (confirmed via source + reproduction)

`@shinzolabs/gmail-mcp` `dist/index.js main()` ran `app.listen(process.env.PORT || 3000)` **unconditionally on every startup**, even in stdio mode. The effective config set no PORT → a second instance (a `/mcp` reconnect before the old socket freed, an overlapping session, or an orphan from a hard-killed session) crashed with `EADDRINUSE :::3000`. Stdio MCP servers have NO auto-reconnect in Claude Code (only HTTP/SSE do), so it stayed down until manual `/mcp` — which re-collided. Reproduced: two direct binaries → #2 EADDRINUSE; two with `PORT=0` → coexist.

## The trap that hid it for months

`~/.claude/settings.json` used to have an `mcpServers` block (15 servers, gmail → a `PORT=0` wrapper). **Claude Code does NOT read `mcpServers` from `settings.json` at all** — it was dead config; the wrapper never ran for interactive sessions. **Removed 2026-06-12**: 11 were duplicates of `.claude.json`; the 4 that lived ONLY there (github, github-work, google-docs, google-sheets — silently not loading) were migrated into `~/.claude.json` `projects["/Users/jcrawley"].mcpServers`. **All MCP servers now live in `~/.claude.json` (project scope); `bigquery` is top-level. Never put MCP servers in `settings.json` — it's ignored.** Effective MCP config = `~/.claude.json` + `.mcp.json`.

## Fallback (stdio) config, if the daemon is ever removed

Set `~/.claude.json` gmail back to `{"type":"stdio","command":".../bin/gmail-mcp","env":{"PORT":"0"}}`. The `PORT=0` is mandatory — it's what stops the port-3000 collisions. (`~/.claude.json` is rewritten live by Claude Code; edit atomically and verify the value survives a restart.)

## Credentials (unchanged)

Package ignores `GMAIL_OAUTH_PATH`/`GMAIL_CREDENTIALS_PATH` env — `config.js` derives paths from `MCP_CONFIG_DIR` (default `~/.gmail-mcp`). Always reads `~/.gmail-mcp/credentials.json`, which the SessionStart + autoheal hooks refresh. The long-running daemon also auto-refreshes the access token in-memory via google-auth-library.

## Backups from the 2026-06-12 work
`~/.claude.json.bak-gmailfix-*` / `.bak-httpswap-*`, `~/.claude/settings.json.bak-gmailfix-*`, `@shinzolabs/gmail-mcp/dist/index.js.bak-gmailfix-*`.
