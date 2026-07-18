---
name: Slack MCP — token rotation requires session restart
description: After rotating SLACK_MCP_XOXB_TOKEN in settings.json, the MCP server must be restarted for the new token to take effect. Check tool availability at session start before assuming Slack works.
type: reference
originSessionId: 4adc8f83-50db-468a-b0c1-eed587d83946
---
> **DECOMMISSIONED 2026-06-16 per Enterprise security directive — do NOT re-enable or fix. See [[slack-mcp-decommissioned-security]].** The details below are historical only.

**Slack MCP server:** `/Users/jcrawley/.npm-global/bin/slack-mcp-server` (Node.js / npm-installed).

**Config location:** `~/.claude/settings.json` → `mcpServers.slack.env.SLACK_MCP_XOXB_TOKEN`.

**Current token type (as of 2026-04-23):** bot token only (`xoxb-...`, 55 chars). The prior config documented in CLAUDE.md had both `xoxb` + `xoxp` — the user token was dropped in the rotation. Consequence: all Slack actions now post as the bot user, not as Jake.

**Key operational rule:** MCP servers are spawned once at Claude Code session start. If the token is rotated mid-session, the new token is NOT picked up — the server keeps using the old token until the session restarts. Symptoms of a stale/missing Slack MCP:
- Zero slack-namespaced tools in tool registry (`ToolSearch` for "slack" returns empty)
- `ps aux | grep slack-mcp` shows no running process
- Any `mcp__slack__*` tool call fails with "tool not found"

**Recovery:** User restarts Claude Code, or runs `/mcp` in the CLI to check + reconnect.

**Detection heuristic for future sessions:** If the user mentions "slack token updated" or similar, check `ToolSearch` for Slack tools immediately. If none present, proactively tell the user a session restart is needed rather than attempting Slack calls that will fail silently.
