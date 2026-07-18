---
name: project_market_metrics_weekly
description: "Weekly Marketplace Metrics (Connections) tracker for 11 onboarding-audit stores — sheet, scripts, schedule"
metadata: 
  node_type: memory
  type: project
  originSessionId: 7ca5ef7a-0f5c-460f-9af4-7d244bfc3414
---

New recurring report tracking **Total Connections per store per Mon–Sun week**
for the 11 stores (10 Hendrick Automotive + Volkswagen of Murrieta) in the
onboarding-audit ("OBA") tracker sheet
`1oNeDOhANTwpiku6lEF8oNUpnu-kOmrYJb-YmUrXPatw`. First week tracked: 7/13–7/19
(2026).

**Why:** Jake wanted onboarding health watched week over week rather than as
a one-time audit, sourced from admin.cars.com's Connections & Contact Details
report.

**How it works:**
- Output tab: `Weekly Connections` (same spreadsheet), long format — CCID,
  Store Name, Week Start, Week End, Total Connections, Partial Week?.
- Script: `~/Documents/scripts/market_metrics_weekly.py` (+ shared helpers in
  `market_metrics_shared.py`) — fully self-contained (Playwright pip package,
  Keychain creds, Sheets REST API), no Claude API/MCP dependency.
- Data source technique: the report has no date-range picker at all; pulls
  the `exportdetails` Tableau worksheet unfiltered and buckets by week in
  Python — see [[reference_admin_cars_tableau_embed_extract]] for the
  extraction pattern and why PII never leaves the browser context.
- Auth: reuses the existing `pb-profile` Playwright profile (already
  admin.cars.com-trusted) — a fresh/isolated profile gets denied by
  JumpCloud device-trust even with correct creds+MFA, see
  [[reference_jumpcloud_device_trust]].
- UUID cache: `~/.claude/market_metrics_uuid_cache.json` (separate from
  `aca_uuid_cache.json` — different dealer group).
- Upsert, not append: keyed on (CCID, Week Start) — safe to re-run same-day
  or mid-week without duplicating rows; the in-progress week gets updated in
  place once it completes.
- Schedule: `com.jcrawley.market-metrics-weekly.plist`, loaded, **Mondays
  7:00 AM** — deliberately offset from Hendrick PB (Mon 6 AM,
  `hendrick-profile`) and Nalley PB (Mon 8 AM, `nalley-profile`) since this
  new job shares `pb-profile` with the PB report family.
- Skill: `/marketplace-weekly-connections` documents the full procedure.

**How to apply:** For future per-store weekly/period metrics work, this is
the reference pattern — check this project's scripts before building a new
admin.cars.com weekly-tracking automation from scratch.
