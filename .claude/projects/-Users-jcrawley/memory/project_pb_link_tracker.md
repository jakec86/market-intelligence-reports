---
name: project_pb_link_tracker
description: PB report click-tracking — Apps Script web-app redirect tracker (clasp deploy); why in-sheet onOpen fails
metadata: 
  node_type: memory
  type: project
  originSessionId: 6b430de4-c66a-46ca-9fc4-3d25ccc164f7
---

Tracking "who opened the Price Badge Report" is solved with a Google Apps Script **web-app redirect tracker**, not anything inside the Sheet. Project: `~/Documents/scripts/pb_link_tracker/` (`Code.js` multi-report router, `appsscript.json`, `deploy.sh`, `DEPLOY.md`).

**How it works:** hand the dealer `…/exec?report=<key>&r=<tag>` instead of the raw Sheet URL. Stage-1 landing page (no email — defeats SafeLinks/Mimecast scanners), Stage-2 "Open the Report" click → emails jcrawley@cars.com + redirects to the Sheet. Covers `dyer` / `nalley` / `hendrick` via the `report` param; add a report by editing the `REPORTS` map.

**Why not in-sheet:** confirmed live (Activity Dashboard showed only internal views) — `onOpen` never fires for view-only users, `Session.getActiveUser().getEmail()` is blank for external users, and `=IMAGE()` pixels get cached by Google. So the old `nalley_pb_open_notify.gs` / `hendrick_pb_open_notify.gs` (onOpen approach) are **deprecated/broken for external tracking** — this replaces them.

**DEPLOYED LIVE 2026-06-12 via clasp** under jcrawley@cars.com. BASE `/exec` = `https://script.google.com/macros/s/AKfycbySKt9As-7CVpAeoi3oCzlk7YEYLOxDZXrNc55wrIZEXEZ5pZnsqtK-ggqmF-3ww6juMg/exec`; script project id `1Yhc3NyT1edF_sCMXf1-kxuJlPxPoRQvyhepQtyUclS9gJFop_EUjJd_V`. clasp gotchas hit: web app = `--type standalone` (NOT `webapp` → "Invalid container file type"); must enable Apps Script API at script.google.com/home/usersettings first; clasp can't trigger the OAuth consent → run `clasp open-script` then Run ▸ `authorizeScopes`. Re-deploy after edits: `clasp push -f && clasp create-deployment`. **Open-link design (fixed 2026-06-12, v5):** the report MUST open in one click. Stage-1 landing-page button uses `href = SHEET_URL target="_top"` (opens directly) + `onclick` fires a `fetch(exec+'?open=1…',{mode:'no-cors',keepalive:true})` ping (notification survives the navigation). DO NOT use a relative href (`?open=1…`) — it resolves against the sandbox googleusercontent.com iframe and silently breaks ("report doesn't open"); use `ScriptApp.getService().getUrl()` for absolute. DO NOT rely on a server-side `window.top.location` redirect — the browser blocks auto top-navigation from the sandboxed iframe. `onclick` JS string literals must be SINGLE-quoted (double quotes via JSON.stringify → "Malformed HTML content"). Scanner-safe: SafeLinks/Mimecast fetch the bare link but never click → no ping. Verified live (one click → sheet + notification email arrived).

**Workspace "Anyone access" CONFIRMED working 2026-06-12** — anonymous curl of BASE returned the stage-1 landing page (no login wall); stage-2 curl redirected to the correct sheet. So cars.com does NOT block external Apps Script web apps.

**Wired into the live PB pipeline:** `pb_dealers.py` has `TRACKER_BASE` + `email_link_url` for hendrick (`?report=hendrick&r=hendrick`) and nalley (`?report=nalley&r=nalley`); `pb_report.py` email body uses `cfg.get("email_link_url", cfg["sheet_url"])`. Bulk email → one per-dealer tag, not per-person (per-person links for manual sends are in DEPLOY.md). Skill files' "open the sheet" steps stay RAW (Jake's own QC opens shouldn't alert). Old `nalley_/hendrick_pb_open_notify.gs` moved to `~/Documents/scripts/_deprecated/`.

**Dyer resolved 2026-06-12:** tracker `dyer` key repointed → PB pipeline sheet `1TWMwKUn` (deployment updated in place via `clasp update-deployment -V2 <id>`, so the `/exec` URL is unchanged). The one-time Inventory Engagement Report `1ntpeO3gy5` is retired. To keep the URL stable when editing the tracker: `clasp push -f` → `clasp create-version` → `clasp update-deployment -V <n> AKfycbySKt9…` (NOT `create-deployment`, which mints a new URL).

Related: [[reference_price_badge_sheets]], [[project_pb_report_production]].
