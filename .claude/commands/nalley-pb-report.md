# Price Badge Report — Nalley Lexus Galleria Weekly Workflow

Run the full weekly Price Badge Report for Nalley Lexus Galleria. Scheduled: **Mondays and Fridays at 8:00 AM MST**.

---

## Email Drafting Rule

Each draft must feel fresh but follow a consistent strategy:
- **Vary:** opening line, phrasing of the insight stat, any notable callout (e.g. a specific vehicle or badge tier worth flagging)
- **Keep consistent:** professional-casual tone, concise (3–5 sentences max), lead with the data, close with "Cheers, Jake"
- **Never:** use the same opening line twice in a row, be vague about the stat, or skip the sheet link

---

## Pre-flight (REQUIRED — abort on any failure)

Run these before touching Tableau or admin.cars.com. Do not proceed with partial auth state.

1. **Auth creds in Keychain** — confirm all three are retrievable (values are never printed):
   ```bash
   security find-generic-password -a jcrawley -s jumpcloud-username -w >/dev/null && echo "user ok"
   security find-generic-password -a jcrawley -s jumpcloud-password -w >/dev/null && echo "pass ok"
   bash ~/.claude/scripts/check-totp-keychain.sh   # TOTP seed present
   ```
   If username/password are missing, the Login Sub-procedure can't run unattended — abort and flag. If only TOTP is missing, MFA falls back to push.
2. **Playwright MCP** — verify `browser_navigate` is available (`mcp__playwright__browser_navigate`). Required for both Tableau and admin.cars.com. If missing, abort and recommend `/mcp` check.
3. **Gmail MCP not required** — email is sent via Gmail API directly by `pb_report.py`.

> **Note:** Tableau MCP PAT returns 401 for this view due to RLS — use Playwright only for all Tableau steps. The headless browser runs a **persistent profile**, so when the session is still valid the views load with no login at all.

---

## Step 1 — Tableau: LEI Crosstab Download

Navigate directly to the **Nalley Custom View** (pre-filtered: DMA=Atlanta+Detroit, Dealer=Nalley Lexus Galleria, Used inventory):
```
https://us-west-2b.online.tableau.com/#/site/cars/views/LowEngagedInventoryReport/LEI-Localv2/eaf9a030-bda1-4bc9-a771-574c63bacb9d/NalleyLexusGalleriaPBReport
```

If a login page appears (Tableau Cloud sign-in or JumpCloud), run the **JumpCloud / Tableau Login + MFA Sub-procedure**, then re-navigate to this URL.

Wait for the viz to fully render (~15–30 sec). No filter changes needed — all filters are pre-applied in the saved view.

> **Do NOT click any filters** — the custom view has DMA=Atlanta+Detroit and Dealer=Nalley Lexus Galleria pre-set. Any filter interaction will trigger a recompute.

**Download the crosstab:**
1. Click **Download** in the toolbar
2. Click **Crosstab**
3. Sheet: `Low Engaged Inventory Report - Local v2` (pre-selected — leave it)
4. Format: switch to **CSV**
5. Click **Download**

File lands at: `~/.playwright-mcp/Low-Engaged-Inventory-Report---Local-v2.csv`

**Immediately rename to avoid collision with Hendrick:**
```bash
mv ~/.playwright-mcp/Low-Engaged-Inventory-Report---Local-v2.csv ~/.playwright-mcp/nalley_lei.csv
```

**CSV schema validation (required before import):**
```python
# Expected headers (col 0–4):
# Dealer name | Dealer id | Stock num | VIN | Make name
```
If col 2 is not `Stock num`, abort — format changed. `col_reorder: False` assumes this order.

---

## Step 2 — admin.cars.com: Demand Signals / Price Comparison

Navigate directly to Nalley's Demand Signals page (skips dealer search):
```
https://admin.cars.com/dealers/156f9bb7-3c44-549c-b16b-0c3af73fdb1f/reports/demand_signals
```

If a login page appears, run the **JumpCloud / Tableau Login + MFA Sub-procedure**, then re-navigate to this URL.

1. Page loads → "Nalley Lexus Galleria | Customer ID 109754" confirms correct dealer
2. Click **Price Comparison** tab
3. Click **Download Crosstab** (the spreadsheet icon, not PDF)
4. Sheet: `Pricing` (pre-selected — leave it)
5. Format: switch to **CSV**
6. Click **Download**

File lands at: `~/.playwright-mcp/Pricing.csv`

**CSV schema validation:**
```
Expected: YMMT | Stock num | Stock type | Days live | Price | Price vs Market (%) | Value
```
`Value` column contains: At Market / Above Market / Under Market — required for Dem Signal stats.

---

## Step 3 — Run pb_report.py

This script handles everything: import both CSVs → sort PBT → read stats → hide Data Import tab → send email to recipients.

> **CRITICAL — headless-safe invocation (added 2026-07-17 after the 8:00 AM scheduled run silently failed):** Scheduled runs are a **single-turn headless session** (`claude -p`). If this Bash call auto-backgrounds (the tool's default foreground timeout) and you respond by ending your turn to "wait" for it — via `Monitor`, a background poller, or anything else async — **the CLI process itself exits immediately once you stop issuing tool calls, and the backgrounded `pb_report.py` process is orphaned and killed with it**, even though the wrapper's `wait "$pid"` sees a clean exit and logs `exit: 0`. There is no persistent loop in headless mode to ever deliver a later notification back into that turn. This is exactly what happened on 2026-07-17: Steps 1–2 succeeded, `pb_report.py` auto-backgrounded at the 300s mark, the agent armed a `Monitor` and stopped — the CLI exited 10s later, the backgrounded script died mid-flight, and nothing was sent despite the "success" exit code.
>
> Rules for this step, always:
> 1. Invoke the Bash call with an explicit `timeout: 600000` (the 10-minute max) so the script has the best chance of finishing in one foreground call instead of auto-backgrounding at all.
> 2. If it still backgrounds past that, do **not** stop and wait via `Monitor` or end your turn. Keep issuing foreground Bash polling calls in a loop (e.g. `ps -p <pid> -o stat= || echo DONE`, then a short `sleep`, repeat) until the process exits or ~15 minutes total elapses — all within this same turn, never delegated to a background mechanism.
> 3. Only declare success after reading the process's actual output (or its `.output` file if it did background) — a clean exit code alone is not evidence the send happened.

```bash
python3 ~/Documents/scripts/pb_report.py \
  --dealer nalley \
  --lei ~/.playwright-mcp/nalley_lei.csv \
  --dem ~/.playwright-mcp/Pricing.csv \
  --send
```

Expected output:
```
✓ Imported 50–60 LEI rows to 'Data Import_Inventory Report'
✓ Imported ~166 Dem Signal rows to 'Data Import_Dem Signal - $ Comp'
✓ Pass 1: empty rows pushed to bottom (A4:L5X)
✓ Pass 2: sorted A4:L5X by J ascending (green first)
✓ Stats: X/N within $1,000 (XX%), Y at $0 (excluded from %), 14 already Great
✓ Dem Signal: XX% At / XX% Above / XX% Under
✓ Hidden tab 'Data Import_Inventory Report'
✓ Gmail draft created (id: ...)
✓ Email sent (message id: ...)
```

If the script errors on Gmail auth, check `~/.claude/tokens/gmail_jcrawley.json` — the refresh token is permanent but the access token may need a refresh via the Google OAuth endpoint.

---

## Step 4 — Post-Run QC

1. Open the sheet: [Price Badge Report - Nalley Lexus Galleria](https://docs.google.com/spreadsheets/d/13Jn8vJSG7vRYW9xpuxrMi9kXNhiV_TaCrjQ5lNQRPP8/edit?gid=565895707#gid=565895707)
2. Confirm **Price Badge Tool** tab has data in cols E–J (Days Live, Photos, Price, Current Badge, Next Badge, Diff)
3. Check **col K** — confirm K formulas are filled down to match the data rows
4. Sheet title should be `Price Badge Report - Nalley Lexus Galleria - M.D.YY`
5. **Rows sorted by col J ascending** — smallest diff (closest to badge) at top, blank J rows at bottom. No SAM grouping (single dealer).
6. **Do NOT modify any formulas** — VLOOKUPs and col J are correct. If data looks wrong, re-run the import.

---

## Step 5 — Mark Google Task Complete

Mark the **"Nalley Lexus Galleria - LEI Report"** task complete in the **Priority Tasks** list.

```
task_search query: "Nalley Lexus Galleria"   (substring of exact title)
→ confirm title = "Nalley Lexus Galleria - LEI Report", due = today
→ mark status = "completed"
→ if not found: skip (task may not have been regenerated for this cycle yet)
```

---

## Step 6 — Confirm Send

Email goes directly to the Nalley team (format approved as of 2026-06-08):

**To:** Grayson Caudill, Jason E. Brown, Zlatan Ibrahimbegovic, Rashad Saeed
**Cc:** Shashank Dharanendra

Confirm the script output shows `✓ Email sent (message id: ...)`. If it shows only `✓ Gmail draft created` without a send line, re-run with `--send` explicitly.

---

## JumpCloud / Tableau Login + MFA Sub-procedure

The headless browser uses a **persistent profile** (`--user-data-dir`), so when the Tableau/JumpCloud session is still valid the views load with no login — skip this entire sub-procedure. Run it only when a login page actually appears. All credentials come from Keychain and must **never** be printed, echoed, or logged.

**Step A — Tableau Cloud username page** (`sso.online.tableau.com`, heading "Sign in to Tableau Cloud", a "Username" field):
1. Retrieve username: `security find-generic-password -a jcrawley -s jumpcloud-username -w`
2. Type it into the Username field → click **Sign In**. This redirects to the JumpCloud IdP.

**Step B — JumpCloud login** (`sso.jumpcloud.com` / `console.jumpcloud.com` showing email and/or password fields):
1. If an email/username field is shown, fill it from the Keychain username (A.1).
2. If a password field is shown, retrieve `security find-generic-password -a jcrawley -s jumpcloud-password -w` and fill it into the field with `browser_type`. (In-page fetch / clipboard auto-fill are CSP/headless-blocked, so a direct fill is required.) The run logs are **gitignored**, so the value stays on local disk only — never committed. Do NOT echo the password in your chat replies or print it to stdout.
3. Click **Sign In / Continue**. If the profile already has an active JumpCloud session, this is skipped automatically — just proceed to MFA or Step D.

**Step C — MFA (TOTP primary):**
1. If a push prompt is shown, click "Try another way" / "Use authenticator code". If the Verification Code input is already visible, skip this click.
2. Retrieve code: `python3 ~/.claude/scripts/jumpcloud-totp.py` (capture stdout). Non-zero exit → fall back to Push (Step E); surface the helper's stderr verbatim.
3. Type the 6-digit code → Submit/Verify. Retry once at the next 30s boundary if rejected. Rejected twice → abort: `"TOTP rejected twice — check Mac clock: sudo sntp -sS time.apple.com"`. **Never log the code or seed.**

**Step D — Land back on target:** After auth, if the browser lands on the JumpCloud **console/dashboard** (`console.jumpcloud.com`) instead of the report, **re-navigate to the original target URL** (the Tableau LEI view or the admin.cars page). The session is now established, so it loads directly. (Observed: Tableau SSO frequently drops on the JumpCloud favorites page rather than deep-linking back — re-navigation fixes it.)

**Step E — Push fallback (only if TOTP unavailable):** Click "Send Push", output `"⏳ JumpCloud push sent — approve on your phone to continue."`, poll every 5s up to 90s for a redirect off the login page. No redirect after 90s → abort: `"⚠️ Push not approved after 90s — re-run"`.

> **Current status (2026-06-12):** Persistent Playwright profile + Keychain creds (`jumpcloud-username`, `jumpcloud-password`) + TOTP seed all enrolled → login is fully unattended. Push remains a fallback; Jake is available ~8:00 AM MST as a human backstop only.

---

## Key Facts

| Item | Value |
|------|-------|
| Dealer | Nalley Lexus Galleria |
| Customer ID | 109754 |
| admin.cars.com UUID | `156f9bb7-3c44-549c-b16b-0c3af73fdb1f` |
| Sheet ID | `13Jn8vJSG7vRYW9xpuxrMi9kXNhiV_TaCrjQ5lNQRPP8` |
| LEI Tableau URL | `https://us-west-2b.online.tableau.com/#/site/cars/views/LowEngagedInventoryReport/LEI-Localv2/eaf9a030-bda1-4bc9-a771-574c63bacb9d/NalleyLexusGalleriaPBReport` |
| Download path | `~/.playwright-mcp/` |
| PBT sort range | `A4:L5000` (data rows only — headers on R3, empty R1–R2; script uses 5000 as upper bound) |
| Sort col | J (Difference to Next Badge) |
| Threshold cell | E1 |
| DMA filter | Pre-applied in custom view — do not touch |
| Dealer filter | Pre-applied in custom view — do not touch |

> ⚠️ **Always compose HTML email** — use `Content-Type: text/html` and base64url-encode as RFC 2822 `raw` parameter.

HTML fallback
