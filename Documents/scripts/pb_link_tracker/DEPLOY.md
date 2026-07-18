# PB Report Link Tracker — Deploy & Use

One Apps Script **web app** that tracks external opens across **all** Price Badge reports
(Dyer & Dyer, Nalley, Hendrick). You hand the dealer a tracked link instead of the raw
Sheet URL; when they click **"Open the Report"** you get an email and they land on the Sheet.

**Why a web app, not an in-sheet `onOpen`:** `onOpen` never fires for view-only users and
can't see anyone outside cars.com. The old `nalley_/hendrick_pb_open_notify.gs` scripts use
that broken approach — they only catch internal opens. This replaces them.

---

## Deploy (one time)

```bash
# 0. Enable the Apps Script API (one toggle, in your browser):
!  open "https://script.google.com/home/usersettings"     # → turn "Apps Script API" ON

# 1. Log clasp in to jcrawley@cars.com (opens a browser):
clasp login

# 2. Create + push + deploy (re-runnable):
cd ~/Documents/scripts/pb_link_tracker && ./deploy.sh
```

`deploy.sh` prints the **tracked-link base**, e.g.
`https://script.google.com/macros/s/AKfyc…/exec`

```bash
# 3. FINAL one-time step — grant the mail-send consent (clasp can't do this for you):
clasp open-script        # in the editor:  Run ▸ authorizeScopes ▸ approve the consent
```

After step 3 the link is live.

> ⚠ **The one thing that can block this:** the deployment sets *Who has access = Anyone*.
> Some cars.com Workspace policies restrict Apps Script web apps to domain-only. If external
> recipients hit a Google login wall instead of the redirect, that policy is the cause —
> fall back to deploying this from a personal Google account, or use a click-tracking link
> shortener. The deploy itself is how we find out.

---

## Live deployment (2026-06-12)

- **BASE** (tracked-link base): `https://script.google.com/macros/s/AKfycbySKt9As-7CVpAeoi3oCzlk7YEYLOxDZXrNc55wrIZEXEZ5pZnsqtK-ggqmF-3ww6juMg/exec`
- Script project: `https://script.google.com/d/1Yhc3NyT1edF_sCMXf1-kxuJlPxPoRQvyhepQtyUclS9gJFop_EUjJd_V/edit`
- Deployment id: `AKfycbySKt9As-7CVpAeoi3oCzlk7YEYLOxDZXrNc55wrIZEXEZ5pZnsqtK-ggqmF-3ww6juMg`
- Re-deploy after code edits: `clasp push -f && clasp create-deployment`

## Use — tracked links

Format: `BASE?report=<key>&r=<recipient-tag>` (BASE above).
The `r` tag is just a label you assign per person (Google never reveals the visitor's identity).

| Report | Recipient | Link |
|---|---|---|
| Dyer & Dyer Volvo (recurring PB email) | Roman + Victor | `BASE?report=dyer&r=dyer` |
| Nalley Lexus Galleria | Grayson Caudill | `BASE?report=nalley&r=grayson_caudill` |
| Nalley Lexus Galleria | Jason E. Brown | `BASE?report=nalley&r=jason_brown` |
| Nalley Lexus Galleria | Zlatan Ibrahimbegovic | `BASE?report=nalley&r=zlatan` |
| Nalley Lexus Galleria | Rashad Saeed | `BASE?report=nalley&r=rashad` |
| Nalley Lexus Galleria | Shashank Dharanendra | `BASE?report=nalley&r=shashank` |
| Hendrick Automotive | Anne Lewis | `BASE?report=hendrick&r=anne_lewis` |

**You** keep using the raw Sheet URLs — so every notification you receive is a genuine
outside open.

### Adding another report
Edit `Code.js` → add a line to `REPORTS` (`key: { url, name }`) → `clasp push -f && clasp create-deployment`.

### Optional: a running log of every open
Set `LOG_SHEET_ID` in `Code.js` to a Spreadsheet ID; each open appends `[time, report, recipient, name]`.
