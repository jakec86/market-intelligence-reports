---
name: caffeinate for Scheduled Tasks
description: Use caffeinate to keep Mac awake when running scheduled/recurring Claude Code tasks that depend on local MCP servers
type: reference
originSessionId: 3213e376-cf04-47bb-9286-c4a932b03250
---
`caffeinate -s &` keeps the Mac awake indefinitely (plugged in). Screen lock is fine — local MCP servers (Gmail, SF, Sheets, Tableau, Playwright) keep running. Sleep kills them.

- `caffeinate -t 28800 &` — 8-hour variant
- Also: System Settings → Energy → "Prevent automatic sleeping when display is off"
- `launchd` (StartCalendarInterval) can wake the Mac from sleep if needed for true cron-style scheduling

**How to apply:** When setting up overnight or away-from-desk recurring tasks (e.g., `/loop`, scheduled reports), remind Jake to run `caffeinate` first.
