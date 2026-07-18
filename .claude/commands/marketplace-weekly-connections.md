# Weekly Marketplace Metrics — Connections Tracker

Pulls **Total Connections** per store per Mon–Sun week from admin.cars.com's
Connections & Contact Details report, for the 11 stores in the onboarding-audit
sheet, and upserts into that sheet's `Weekly Connections` tab. Scheduled:
**Mondays at 7:00 AM MST**, pulling the just-completed week.

> **Status: LIVE (2026-07-17).** First backfill (week of 7/13–7/19, partial)
> run manually and verified against a live-dashboard spot check. Script is
> idempotent — safe to re-run mid-week or same-day without creating duplicate
> rows. Scheduled via launchd (`com.jcrawley.market-metrics-weekly`, loaded),
> **not** `claude -p` / Cowork — the script is fully self-contained (Playwright
> pip package + Keychain + Sheets REST API) with no Claude API or MCP
> dependency, so it runs as a plain wrapper script (`market_metrics_weekly.sh`),
> the same pattern as `com.jcrawley.aca-review-cycle`. 7 AM was picked
> deliberately clear of Hendrick PB (Mon 6 AM, `hendrick-profile`) and Nalley PB
> (Mon 8 AM, `nalley-profile`) — this script uses `pb-profile`.

---

## Pre-flight (REQUIRED — abort on any failure)

1. **Auth creds in Keychain** — confirm retrievable (values never printed):
   ```bash
   security find-generic-password -a jcrawley -s jumpcloud-username -w >/dev/null && echo "user ok"
   security find-generic-password -a jcrawley -s jumpcloud-password -w >/dev/null && echo "pass ok"
   security find-generic-password -a jcrawley -s jumpcloud-totp -w >/dev/null && echo "totp ok"
   ```
2. **pb-profile not locked by another run** — check before starting:
   ```bash
   pgrep -fl "pb-profile"
   ```
   If another process holds it (e.g. a concurrent Nalley/Hendrick/Dyer PB run), wait for it to
   free up rather than forcing a second instance against the same profile — see
   `feedback_pb_retry_concurrent_run.md`.
3. **Google Sheets token valid** — `~/.claude/tokens/sheets_token.json` present and refreshable.

> **Why pb-profile specifically:** JumpCloud enforces device-trust conditional access on the
> webadmin SAML app fronting admin.cars.com — a fresh/isolated Playwright profile authenticates
> fully (username, password, TOTP all pass) but then gets denied at the redirect step
> (`error=policyDenial`). `pb-profile` is an existing, already-trusted persistent profile
> (confirmed working against admin.cars.com 2026-07-17) — never spin up a new profile for this
> report. See `reference_jumpcloud_device_trust.md`.

---

## Step 1 — Run the script

```bash
python3 ~/Documents/scripts/market_metrics_weekly.py
```

This does everything:
1. Reads the 11 stores (CCID + Store Name) from `Sheet1` of the tracking sheet.
2. Launches `pb-profile` headless via Playwright, confirms/establishes the admin.cars.com
   session (only fills the JumpCloud login form if actually redirected there — normally the
   persistent profile already has a valid session, so this is a no-op).
3. For each store: resolves (or reuses cached) admin.cars.com UUID from
   `~/.claude/market_metrics_uuid_cache.json`, navigates to
   `/dealers/{uuid}/reports/connections_contact_details`, and pulls **only** the
   `Submitted Date/Time` column off the `exportdetails` Tableau worksheet via the Embedding API
   (`getSummaryDataAsync`) — no PII field is ever read or written anywhere in this pipeline.
4. Buckets timestamps into Mon–Sun weeks (starting 7/13/2026) and computes Total Connections
   per store per week.
5. Upserts into `Weekly Connections` (keyed on CCID + Week Start) — updates the current
   in-progress week in place rather than duplicating it, and only appends genuinely new weeks.

Expected output:
```
  <Store Name> (<CCID>): N week(s) computed
  ... (11 lines)
Upserted. Weekly Connections now has NN data rows.
```

If a store errors with "Could not resolve admin.cars.com UUID for CCID ...", the store's CCID may
be wrong or the dealer record may not exist under that ID — check manually via
`https://admin.cars.com/dealers/all/reports?query={ccid}` before re-running.

---

## Step 2 — Spot-check

Open the [tracking sheet](https://docs.google.com/spreadsheets/d/1oNeDOhANTwpiku6lEF8oNUpnu-kOmrYJb-YmUrXPatw/edit),
`Weekly Connections` tab:
1. Confirm one row per store for the newly-added week (11 rows total, no duplicates).
2. `Partial Week?` should read `No` for any fully-elapsed week, `Yes` only for the current
   in-progress week.
3. If a store's Total Connections looks off (e.g. suddenly 0 for a previously-active store),
   spot-check the live dashboard's own "last 7 days" KPI tile before trusting the number —
   the report's rolling 13-month window means very old/inactive stores can legitimately show 0.

---

## Key Facts

| Item | Value |
|------|-------|
| Source sheet (11 stores) | `1oNeDOhANTwpiku6lEF8oNUpnu-kOmrYJb-YmUrXPatw`, tab `Sheet1` |
| Output tab | `Weekly Connections` (same spreadsheet) |
| Script | `~/Documents/scripts/market_metrics_weekly.py` |
| Shared helpers | `~/Documents/scripts/market_metrics_shared.py` |
| UUID cache | `~/.claude/market_metrics_uuid_cache.json` |
| Playwright profile | `~/Library/Caches/ms-playwright-mcp/pb-profile` (shared — coordinate with PB report schedule) |
| First tracked week | 2026-07-13 – 2026-07-19 |
| Metric captured | Total Connections only (no type breakdown, no % Mobile — by design) |
| Schedule | Mondays 8:00 AM MST, pulling the just-completed Mon–Sun week |

> ⚠️ Remember `caffeinate` / keep the Mac awake for the scheduled window — scheduled jobs
> won't fire if the machine is asleep/locked.
