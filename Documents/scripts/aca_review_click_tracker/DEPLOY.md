# ACA ReviewBuilder Click Tracker — Deploy Notes

Modeled directly on `~/Documents/scripts/pb_link_tracker/` — same clasp workflow,
same two-stage scanner-safe click pattern. Kept as a separate deployment (see
the header comment in `Code.js` for why).

## One-time setup

1. Enable the Apps Script API: `! open "https://script.google.com/home/usersettings"` → toggle ON
2. `clasp login` (if not already logged in for `pb_link_tracker`)
3. `./deploy.sh`
4. `clasp open-script` → in the editor, select `authorizeScopes` from the function
   dropdown → Run → approve the Google consent screen (send-mail + sheets scopes).
   clasp cannot trigger this consent itself — skipping this step means the deployed
   link can silently fail to notify or log.
5. Copy the printed `https://script.google.com/macros/s/<id>/exec` base URL into
   `aca_review_shared.py` or wherever `CLICK_TRACKER_BASE_URL` is defined in
   `aca_review_report.py`.

## ⚠ Before going live

`NOTIFY_TO` in `Code.js` is currently set to `['jcrawley@cars.com']` only —
Danielle was temporarily excluded during testing (2026-07-16) to avoid
confusing test-click notifications in her inbox. **Change it back to
`['jcrawley@cars.com', 'dmcjunkins@carscommerce.inc']` and redeploy
(`clasp push -f && clasp deploy --deploymentId <id>`) before enabling the
launchd schedule or sending the real GM batch.**

## Re-deploying after a Code.js change

```
./deploy.sh
```
Safe to re-run — reuses the existing `.clasp.json` project, just pushes + creates
a new deployment version.

## URL shape

```
{BASE}?legacy_id=<legacy_id>&dealer=<dealer_name>&option=<1|2|3>
```

- `legacy_id` — the dealer's legacy_id/CCID (matches `dealerrater_results.json` keys)
- `dealer` — dealer display name, passed through so the Apps Script never needs its
  own copy of the JSON data
- `option` — 1, 2, or 3, matching `aca_review_shared.py::MESSAGE_OPTIONS`

## What it does

Two-stage flow (same anti-scanner reasoning as `pb_link_tracker`):
1. **Stage 1** (`doGet`, no `ack` param): confirm-page with a single "Confirm" button.
   No log write, no email — filters out email-scanner link prefetching.
2. **Stage 2** (`?ack=1`): logs one row to the `Engagements` tab of the "ACA
   ReviewBuilder Engagement Tracking" sheet (ID hardcoded as `LOG_SHEET_ID` in
   `Code.js`), emails `jcrawley@cars.com` + `dmcjunkins@carscommerce.inc`, shows a
   confirmation page. No redirect — there's no "destination" like the PB tracker's
   live report link.

## Downstream consumer

`aca_review_config_writer.py` reads the `Engagements`/`Status` tabs and writes the
selected option into the dealer's live DealerRater ReviewBuilder Sales Request Email
settings. This Apps Script never talks to DealerRater directly.
