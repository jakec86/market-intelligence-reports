# Price Badge Report — Weekly Workflow (Hendrick Automotive Group)

Run the full weekly Price Badge Report workflow for Hendrick Automotive Group. Scheduled: **Mondays at 6:00 AM MST**.

---

## Key Differences from Nalley

- **No admin.cars.com / Demand Signals step** — omitted for this dealer group
- **Price badge range: $500** (Nalley uses $1,000)
- **DMA filter: ALL** (click (All) to select all DMAs — Detroit is the default, must expand)
- **Maj dealer name filter: "Hendrick Automotive Group"** (selects all ~72 stores)
- **Email from:** `jcrawley@carscommerce.inc` (not @cars.com)
- **Callout style:** SAM-led bullets (store abbreviation first, then vehicle)

> **Note:** Tableau MCP PAT returns 401 for this view due to RLS — use Playwright only for all Tableau steps. The headless browser runs a **persistent profile**, so when the session is still valid the view loads with no login at all.

---

## Email Drafting Rule

Each email must feel fresh but follow a consistent strategy:
- **Always use HTML-formatted email body** — `Content-Type: text/html`, base64url-encoded as RFC 2822 `raw` parameter. Never fall back to unformatted text.
- **Vary:** opening line, phrasing of the insight stat, any notable callout (e.g. a specific store, vehicle, or badge tier worth flagging)
- **Keep consistent:** professional-casual tone, concise (3–5 sentences max), lead with the data, close with "Cheers, Jake"
- **Never:** use the same opening line twice in a row, be vague about the stat, or skip the sheet link

Example openings (rotate and riff on these):
- "Good Day Anne,"
- "Hope your week is going well, Anne — your Price Badge Report is ready..."
- "Quick update for the team this week..."
- "Anne, dropping in your weekly Price Badge Report..."
- "Team, here's your weekly snapshot..."

---

## Pre-flight (REQUIRED — abort on any failure)

1. **Auth creds in Keychain** — confirm all three are retrievable (values are never printed):
   ```bash
   security find-generic-password -a jcrawley -s jumpcloud-username -w >/dev/null && echo "user ok"
   security find-generic-password -a jcrawley -s jumpcloud-password -w >/dev/null && echo "pass ok"
   bash ~/.claude/scripts/check-totp-keychain.sh   # TOTP seed present
   ```
   If username/password are missing, the Login Sub-procedure can't run unattended — abort and flag. If only TOTP is missing, MFA falls back to push.
2. **Playwright MCP** — verify `mcp__playwright__browser_navigate` tool is available. If missing, abort and recommend `/mcp` check.
3. **Gmail MCP not required** — email is sent via Gmail API directly by `pb_report.py`.

---

## Step 1 — Tableau: LEI Crosstab Download

Navigate directly to the **Hendrick Custom View** (pre-filtered: All DMAs + Hendrick Automotive Group, Used inventory):
```
https://us-west-2b.online.tableau.com/#/site/cars/views/LowEngagedInventoryReport/LEI-Localv2/8a3a0039-6729-4f23-98bb-099bca061385/HendrickPBReport
```

If a login page appears (Tableau Cloud sign-in or JumpCloud), run the **JumpCloud / Tableau Login + MFA Sub-procedure**, then re-navigate to this URL.

Wait for the viz to fully render (~15–30 sec). No filter changes needed — all filters are pre-applied in the saved view.

> **Do NOT click any filters** — the custom view has DMA=All and Maj dealer=Hendrick Automotive Group pre-set. Any filter interaction will trigger a full recompute and may crash the browser.

**Download the crosstab:**
1. Click **Download** in the toolbar
2. Click **Crosstab**
3. Sheet: `Low Engaged Inventory Report - Local v2` (pre-selected)
4. Format: switch to **CSV**
5. Click **Download**

File lands at: `~/.playwright-mcp/Low-Engaged-Inventory-Report---Local-v2.csv`

**Immediately rename to avoid collision with Nalley:**
```bash
mv ~/.playwright-mcp/Low-Engaged-Inventory-Report---Local-v2.csv ~/.playwright-mcp/hendrick_lei.csv
```

**CSV schema validation (required before import):**
```
Expected headers (col 0–4): Dealer name | Dealer id | Stock num | VIN | Make name
```
If col 2 is not `Stock num`, abort — format changed.

---

## Step 2 — Run pb_report.py

```bash
python3 ~/Documents/scripts/pb_report.py \
  --dealer hendrick \
  --lei ~/.playwright-mcp/hendrick_lei.csv \
  --send
```

Expected output:
```
✓ Imported 4,690–4,710 LEI rows to 'Data Import_Inventory Report'
✓ Pass 1: empty rows pushed to bottom (A3:J4697)
✓ Pass 2: sorted A3:J4697 by SAM A-Z
✓ N total rows: X within threshold (green via CF), Y above
✓ Reset basicFilter (hiddenByFilter state cleared)
✓ Stats: X/N within $500 (5–13%), 0 at $0, ~367 already Great
✓ Email sent → anne.Lewis@hendrickauto.com
```

**QC Benchmarks — if outside these ranges, investigate before forwarding to Anne:**

| Metric | Expected | Red flag |
|---|---|---|
| Within $500 (J1 %) | **5–13%** | < 3% → J formula broken (row-position refs); > 15% → data issue |
| Vehicle count | **237–370** | < 100 or > 500 |
| At $0 count | **0–10** | > 100 → J formula returning 0 for most rows |
| Already Great | **350–500** | < 100 → data issue |
| Total rows | **~4,695** | < 4,000 or > 6,000 → import/stale row issue |

**If stats look wrong (especially % < 3% or at $0 > 100):**
The PBT J column may have row-position formulas (`ABS(DataImport!O4526)`) instead of VLOOKUP. These break when rows are sorted. Recovery: write VLOOKUP formula to J3, then copyPaste with PASTE_FORMULA to J4:J4997. See memory `project-pb-report-fixes-2026-06-05` for full script.

---

## Step 3 — Post-Run QC

1. Open the sheet: [Price Badge Report - Hendricks](https://docs.google.com/spreadsheets/d/1guqWV9HFb2MijC7qQ7qinL4oljbu0N1o9TU5zcmy3GM/edit?gid=565895707#gid=565895707)
2. Filter shows **~4,698 of 11,000 rows displayed** — if far fewer, basicFilter is corrupted (run `clearBasicFilter` + re-add)
3. Rows sorted: SAM A-Z, green (within-$500 via CF on col J) rows first within each SAM group
4. J1 shows **5–13%**
5. **Never set `userEnteredFormat.backgroundColor` on data rows** — this blocks the conditional format on col J that the filter uses for green-first sorting
6. Header in Row 2 (purple bg, white bold) — data starts Row 3

---

## Step 4 — Confirm Send

Email goes directly to **anne.Lewis@hendrickauto.com** — no pre-send review step.

**To:** anne.Lewis@hendrickauto.com
**From:** jcrawley@carscommerce.inc

The script outputs `✓ Email sent → anne.Lewis@hendrickauto.com`. Review QC benchmarks above before running if unsure about data quality.

---

## Step 5 — Mark Google Task Complete

Mark the **"Hendricks - LEI Report"** task complete in the **Priority Tasks** list. The 6 AM automated run marks it automatically — verify it shows `status: completed`. If not, mark it complete manually.

```
task_search query: "Hendricks - LEI"   (substring of exact title; "Hendricks LEI Report" won't match — the dash is required)
→ confirm title = "Hendricks - LEI Report", due = today
→ if status != "completed": mark status = "completed"
→ if not found: skip
```

---

## Step 6 — Log Email in Salesforce

After the email is confirmed sent, log it as an activity against the **Hendrick Automotive Group** account in Salesforce so the contact record stays current.

1. Account ID is known: **`0011Q00001zfPm9QAE`** (Hendrick Automotive Group). No lookup needed.

2. Use the Salesforce MCP (`mcp__salesforce__create_record`) to create a Task record:
```json
{
  "sObject": "Task",
  "targetOrg": "jcrawley@onecars.com",
  "recordJson": {
    "Subject": "Hendrick Automotive Group — Price Badge Report {M.D.YY}",
    "Type": "Email",
    "Status": "Completed",
    "Description": "Weekly Price Badge Report sent to anne.Lewis@hendrickauto.com — {N} vehicles within $500 of Good/Great badge across {stores} stores. Top callout: {bullet 1}, {bullet 2}, {bullet 3}.",
    "WhatId": "0011Q00001zfPm9QAE",
    "ActivityDate": "{YYYY-MM-DD}"
  }
}
```

Confirm the task appears in the account's Activity History in Salesforce.

---

## JumpCloud / Tableau Login + MFA Sub-procedure

The headless browser uses a **persistent profile** (`--user-data-dir`), so when the Tableau/JumpCloud session is still valid the view loads with no login — skip this entire sub-procedure. Run it only when a login page actually appears. All credentials come from Keychain and must **never** be printed, echoed, or logged.

**Step A — Tableau Cloud username page** (`sso.online.tableau.com`, heading "Sign in to Tableau Cloud", a "Username" field):
1. Retrieve username: `security find-generic-password -a jcrawley -s jumpcloud-username -w`
2. Type it into the Username field → click **Sign In**. Redirects to the JumpCloud IdP.

**Step B — JumpCloud login** (`sso.jumpcloud.com` / `console.jumpcloud.com` showing email and/or password fields):
1. If an email/username field is shown, fill it from the Keychain username (A.1) with `browser_type` (the username is non-sensitive).
2. If a password field is shown, retrieve `security find-generic-password -a jcrawley -s jumpcloud-password -w` and fill it into the field with `browser_type`. (In-page fetch / clipboard auto-fill are CSP/headless-blocked, so a direct fill is required.) The run logs are **gitignored**, so the value stays on local disk only — never committed. Do NOT echo the password in your chat replies or print it to stdout.
3. Click **Sign In / Continue**. If the profile already has an active JumpCloud session, this is skipped automatically — proceed.

**Step C — MFA (TOTP primary):**
1. If a push prompt is shown, click "Try another way" / "Use authenticator code". If the Verification Code input is already visible, skip this click.
2. Retrieve code: `python3 ~/.claude/scripts/jumpcloud-totp.py` (capture stdout). Non-zero exit → fall back to Push (Step E); surface the helper's stderr verbatim.
3. Type the 6-digit code into the Verification Code input — **if individual digit boxes are shown, type one char per box** — then Submit / press Enter. Retry once at the next 30s boundary if rejected. Rejected twice → abort: `"TOTP rejected twice — check Mac clock: sudo sntp -sS time.apple.com"`. **Never log the code or seed.**

**Step D — Land back on target:** After auth, if the browser lands on the JumpCloud **console/dashboard** (`console.jumpcloud.com`) instead of the report, **re-navigate to the Hendrick LEI view URL**. The session is now established, so it loads directly.

**Step E — Push fallback (only if TOTP unavailable):** Click "Send Push", output `"⏳ JumpCloud push sent — approve on your phone to continue."`, poll every 5s up to 90s for a redirect off the login page. No redirect after 90s → abort: `"⚠️ Push not approved after 90s — re-run"`.

> **Current status (2026-06-12):** Persistent Playwright profile + Keychain creds (`jumpcloud-username`, `jumpcloud-password`) + TOTP seed all enrolled → login is fully unattended. Push remains a fallback.

---

## Key Facts

| Item | Value |
|------|-------|
| Dealer | Hendrick Automotive Group |
| Sheet ID | `1guqWV9HFb2MijC7qQ7qinL4oljbu0N1o9TU5zcmy3GM` |
| LEI Tableau URL | `https://us-west-2b.online.tableau.com/#/site/cars/views/LowEngagedInventoryReport/LEI-Localv2/8a3a0039-6729-4f23-98bb-099bca061385/HendrickPBReport` |
| Download path | `~/.playwright-mcp/` |
| PBT sort range | `A3:J5000` (header Row 2, data Row 3+) |
| Sort col | J (Difference to Next Badge) |
| DMA filter | Pre-applied in custom view — do not touch |
| Maj dealer filter | Pre-applied in custom view — do not touch |
| Stock type | Pre-applied in custom view (Used) — do not touch |
| Email from | jcrawley@carscommerce.inc |
