---
name: slack-mcp-decommissioned-security
description: "Slack MCP integration disabled per Enterprise security directive (2026-06-16) — do NOT re-enable, fix the token, or build a workaround"
metadata: 
  node_type: memory
  type: project
  originSessionId: afa78b3a-b45f-45ba-acb9-cda80867ca5b
---

On 2026-06-16, VP Enterprise Technology relayed a security-team decision: the Slack MCP plugin must NOT be enabled on the Cars Commerce enterprise Slack instance. Workspace-side authorization is being revoked.

Reasons cited by security:
- Bypassing Claude's authorization checkpoints reduces protection against a bad prompt or compromised agent before a human can intervene.
- Local token storage is a security risk.

**Why:** This is a standing org security directive, not a transient outage. The earlier `account_inactive` / `-32000` errors are now moot — the integration is being deliberately retired, not repaired.

**How to apply:** Do NOT attempt to restore the Slack token, generate a new bot/user token, create a replacement Slack app, or build refresh-token plumbing. If a future session sees Slack MCP failing, the correct action is to leave it disabled / remove the config, not fix it. This supersedes the "fix Slack token" guidance in [[slack-mcp-token-rotation-requires-session-restart]].

**Scope (decided by Jake 2026-06-16):** The directive covers ONLY the local `slack-mcp-server` npm plugin (the one with local token storage). The separate **claude.ai Slack connector** (remote OAuth; tools appear as `mcp__claude_ai_Slack__*`) is **intentionally kept active** and is NOT in scope. Do not disable, disconnect, or flag it for cleanup — its presence is expected. If security later extends the directive to the enterprise Slack instance broadly, revisit.

**What was removed (2026-06-16):** revoked the exposed user token; deleted the `slack` block from `.claude.json` (`.projects["/Users/jcrawley"].mcpServers.slack`); uninstalled the `slack-mcp-server` npm package; marked the Slack row DECOMMISSIONED in both CLAUDE.md files.
