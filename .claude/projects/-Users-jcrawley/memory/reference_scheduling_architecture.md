---
name: reference-scheduling-architecture
description: "Scheduling architecture decision: use Cowork native scheduler for recurring workflows, Desktop Commander for ad-hoc bash only — never cron for MCP-dependent tasks"
metadata: 
  node_type: memory
  type: reference
  originSessionId: c45ca59c-3848-420e-941f-e1eb2ac99c83
---

## Scheduling Architecture

**SUPERSEDED 2026-07-17 — production has moved to launchd, not Cowork.** The
rule below (Cowork native scheduler, never launchd) no longer reflects
reality: `Library/LaunchAgents/` has live, loaded plists for Nalley/Hendrick/
Dyer PB reports, ACA review cycle, ACA GM report, and now weekly market
metrics — none use Cowork's scheduler. Two proven patterns:
- **LLM-driven skills** (need Claude reasoning: reading Tableau exports,
  drafting emails): plist → `run-report.sh <skill-name>` → headless
  `claude -p /skill` with retry/stall-detection (`~/.claude/schedules/
  run-report.sh`). Used by PB reports.
- **Fully deterministic scripts** (no Claude reasoning needed — just
  Playwright/API calls + fixed logic): plist → a thin bash wrapper → the
  Python script directly, no `claude -p` involved at all. Used by
  `aca_review_cycle.plist`/`aca_review_cycle.sh` and
  `market-metrics-weekly.plist`/`market_metrics_weekly.sh`. Simpler and
  faster to start than the skill-invocation pattern — use this when the task
  truly doesn't need an LLM in the loop.

**How to apply:** For new recurring automation, default to a launchd plist +
wrapper script (deterministic pattern if no Claude reasoning is needed,
`run-report.sh` pattern if it is). Don't suggest Cowork's scheduler UI —
it's not the active mechanism. When picking a schedule time, check
`Library/LaunchAgents/*.plist` for existing Weekday/Hour/Minute entries AND
which Playwright profile each one uses (`~/Library/Caches/ms-playwright-mcp/
<name>-profile`) — same-profile collisions matter more than same-time
collisions across different profiles. See [[reference_jumpcloud_device_trust]]
for why profile choice isn't arbitrary.

---

### Original (now-superseded) rule, kept for context

**Rule:** Use Cowork's native scheduler (`coworkScheduledTasksEnabled: true`) for all recurring workflow tasks. Never migrate these to crontab or launchd.

**Why:** Recurring workflows (Nalley PB, Hendrick PB, Sonic, ACA, etc.) require MCP servers (Gmail, Tableau, Google Sheets), Claude API, JumpCloud SSO session, and browser automation. macOS cron provides none of these — minimal PATH, no Keychain access, no display, no session context.

**How to apply:**
- New recurring tasks → schedule via Cowork's built-in scheduler UI
- Suggest Cowork scheduler when user asks about automating any report or workflow
- Never suggest crontab/launchd for tasks that touch MCP servers, Playwright, or SSO-gated sites

## Desktop Commander MCP (added 2026-05-12)

Added `@wonderwhy-er/desktop-commander` to `~/Library/Application Support/Claude/claude_desktop_config.json`. Gives Cowork ad-hoc bash access to the host — use for:
- Running scripts on demand from Cowork chat
- Checking files / reading local state
- Opening iTerm2 tabs via AppleScript for long-running jobs
- One-off crontab inspection (`crontab -l`)

This does NOT replace the Cowork scheduler — it supplements it for interactive/ad-hoc use.

## Config locations

- Cowork desktop app MCP config: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Claude Code CLI MCP config: `~/.claude/settings.json`
- These are **separate** — adding MCP to one does not affect the other
