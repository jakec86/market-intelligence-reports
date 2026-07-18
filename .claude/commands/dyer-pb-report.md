# Price Badge Report — Dyer & Dyer Volvo Weekly Workflow

Run the full weekly Price Badge Report for Dyer & Dyer Volvo Cars. Scheduled: **Thursdays at 8:00 AM MST**.

> **Status: LIVE (2026-06-12).** Format approved by Jake; recipients flipped to Roman & Victor
> in `pb_dealers.py` (`email_to`), launchd job `com.jcrawley.dyer-pb-report` loaded (Thu 8 AM).
> Tableau custom view (`DyerDyerVolvo`) and admin UUID recorded below. `--send` now goes
> straight to the dealer.

---

## Email Drafting Rule

Each draft must feel fresh but follow a consistent strategy:
- **Vary:** opening line, phrasing of the insight stat, any notable callout (e.g. a specific vehicle or badge tier worth flagging)
- **Keep consistent:** professional-casual tone, concise (3–5 sentences max), lead with the data, close with "Cheers, Jake"
- **Never:** use the same opening line twice in a row, be vague about the stat, or skip the sheet link

---

## Pre-flight (REQUIRED — abort on any failure)

Run these before touching Tableau. Do not proceed with partial auth state.

1. **Auth creds in Keychain** — confirm all three are retrievable (values are never printed):
   ```bash
   security find-generic-password -a jcrawley -s jumpcloud-username -w >/dev/null && echo "user ok"
   security find-generic-password -a jcrawley -s jumpcloud-password -w >/dev/null && echo "pass ok"
   bash ~/.claude/scripts/check-totp-keychain.sh   # TOTP seed present
   ```
   If username/password are missing, the Login Sub-procedure can't run unattended — abort and flag. If only TOTP is missing, MFA falls back to push.
2. **Playwright MCP** — verify `browser_navigate` is available (`mcp__playwright__browser_navigate`). Required for Tableau LEI download. If missing, abort and recommend `/mcp` check.
3. **Gmail MCP not required** — email is sent via Gmail API directly by `pb_report.py`.

> **Note:** Tableau MCP PAT returns 401 for this view due to RLS — use Playwright only for all Tableau steps. The headless browser runs a **persistent profile**, so when the session is still valid the views load with no login at all.

---

## Step 1 — Tableau: LEI Crosstab Download

Navigate directly to the **Dyer Custom View** (pre-filtered: Dyer's DMA, Dealer=Dyer & Dyer Volvo, Used inventory):
```
https://us-west-2b.online.tableau.com/#/site/cars/views/LowEngagedInventoryReport/LEI-Localv2/df8e4b1f-0a39-49e8-a08a-c20b4b4192f4/DyerDyerVolvo
```

If a login page appears (Tableau Cloud sign-in or JumpCloud), run the **JumpCloud / Tableau Login + MFA Sub-procedure**, then re-navigate to this URL.

Wait for the viz to fully render (~15–30 sec). No filter changes needed — all filters are pre-applied in the saved view.

> **Do NOT click any filters** — any filter interaction will trigger a recompute.

**Download the crosstab:**
1. Click **Download** in the toolbar
2. Click **Crosstab**
3. Sheet: `Low Engaged Inventory Report - Local v2` (pre-selected — leave it)
4. Format: switch to **CSV**
5. Click **Download**

File lands at: `~/.playwright-mcp/Low-Engaged-Inventory-Report---Local-v2.csv`

**Immediately rename to avoid collision with other dealers:**
```bash
mv ~/.playwright-mcp/Low-Engaged-Inventory-Report---Local-v2.csv ~/.playwright-mcp/dyer_lei.csv
```

**CSV schema validation (required before import):**
```python
# Expected headers (col 0–4):
# Dealer name | Dealer id | Stock num | VIN | Make name
```
If col 2 is not `Stock num`, abort — format changed. `col_reorder: False` assumes this order.

---

## Step 2 — ~~admin.cars.com: Demand Signals~~ (DEPRECATED as of 2026-07-03)

> **The Demand Signals Price Comparison page was redesigned to a native component with no CSV/Crosstab download button.** `--dem` is not used for Dyer — skip this step entirely. Dem Signal stats (At/Above/Under %) come from the sheet's existing VLOOKUP formulas and are still reported correctly in script output.

---

## Step 3 — Run pb_report.py

This script handles everything: import LEI CSV → sort PBT → read stats → hide Data Import tab → send email per `pb_dealers.py` config.

```bash
python3 ~/Documents/scripts/pb_report.py \
  --dealer dyer \
  --lei ~/.playwright-mcp/dyer_lei.csv \
  --send
```

Expected output:
```
✓ Imported 45–60 LEI rows to 'Data Import_Inventory Report'
✓ Pass 1: empty rows pushed to bottom (A4:L5X)
✓ Pass 2: sorted A4:L5X by J ascending (green first)
✓ Stats: X/NN within $1,000 (XX%), N at $0 (excluded from %), N already Great
✓ Dem Signal: XX% At / XX% Above / XX% Under
✓ Hidden tab 'Data Import_Inventory Report'
✓ Gmail draft created (id: ...)
✓ Email sent (message id: ...)
```

If the script errors on Gmail auth, check `~/.claude/tokens/gmail_jcrawley.json`.

---

## Step 4 — Post-Run QC

1. Open the sheet: [Price Badge Report - Dyer & Dyer Volvo](https://docs.google.com/spreadsheets/d/1TWMwKUnntKZpjQDX6rbrScDHHfV5jQisG1EIAwIFwC8/edit?gid=565895707#gid=565895707)
2. Confirm **threshold cell E1 = 1000** (badge range $). If blank/wrong, set it before trusting stats.
3. Confirm **Price Badge Tool** tab has data in cols E–J (Days Live, Photos, Price, Current Badge, Next Badge, Diff)
4. Check **col K** — confirm K formulas are filled down to match the data rows
5. Sheet title should be `Price Badge Report - Dyer & Dyer Volvo - M.D.YY`
6. **Rows sorted by col J ascending** — smallest diff (closest to badge) at top, blank J rows at bottom. No SAM grouping (single dealer).
7. **Do NOT modify any formulas** — VLOOKUPs and col J are correct. If data looks wrong, re-run the import.

**QC benchmarks (from live runs):**

| Metric | Expected | Red flag |
|---|---|---|
| Total rows | 45–60 | < 30 or > 80 → stale data or import issue |
| Within $1,000 (J1 %) | 20–40% | < 5% → J formula broken; > 60% → data issue |
| At $0 | 0–10 | > 20 → import or formula problem |
| Already Great | 10–20 | < 5 → data issue |
| Dem Signal At % | 85–95% | < 70% → pricing outlier issue (verify manually) |

---

## Step 5 — Mark Google Task Complete

```
task_search query: "Dyer & Dyer Volvo"   (substring match — "Dyer LEI" does NOT match the title)
→ if found: mark status = "completed"
→ if not found: skip
```
Task: **"Dyer & Dyer Volvo - LEI Report"** in the **Priority Tasks** list (mirrors Nalley). Google Tasks
search is substring-based, so query a contiguous piece of the title. The task is a single dated item, not
auto-recurring — see the note in [[project_dyer_pb_report]] about regenerating it each cycle.

---

## Step 6 — Confirm Send

**LIVE — client-send.** `--send` goes straight to the dealer (`email_to` in `pb_dealers.py`):
**To:** Roman Byczek (Roman.Byczek@dyeranddyervolvo.com), Victor Traitel (Victor.Traitel@dyeranddyervolvo.com)
Confirm the script output shows `✓ Email sent (message id: ...)`.

The sheet link in the email is the **tracked link** (`?report=dyer&r=dyer`) — an open by the
dealer emails jcrawley@cars.com. See `~/Documents/scripts/pb_link_tracker/DEPLOY.md`.

---

## JumpCloud / Tableau Login + MFA Sub-procedure

The headless browser uses a **persistent profile** (`--user-data-dir`), so when the Tableau/JumpCloud session is still valid the views load with no login — skip this entire sub-procedure. Run it only when a login page actually appears. All credentials come from Keychain and must **never** be printed, echoed, or logged.

**Step A — Tableau Cloud username page** (`sso.online.tableau.com`, heading "Sign in to Tableau Cloud", a "Username" field):
1. Retrieve username: `security find-generic-password -a jcrawley -s jumpcloud-username -w`
2. Type it into the Username field → click **Sign In**. This redirects to the JumpCloud IdP.

**Step B — JumpCloud login** (`sso.jumpcloud.com` / `console.jumpcloud.com` showing email and/or password fields):
1. If an email/username field is shown, fill it from the Keychain username (A.1).
2. If a password field is shown, retrieve `security find-generic-password -a jcrawley -s jumpcloud-password -w` and type it in.
3. Click **Sign In / Continue**. If the profile already has an active JumpCloud session, this is skipped automatically — just proceed to MFA or Step D.

**Step C — MFA (TOTP primary):**
1. If a push prompt is shown, click "Try another way" / "Use authenticator code". If the Verification Code input is already visible, skip this click.
2. Retrieve code: `python3 ~/.claude/scripts/jumpcloud-totp.py` (capture stdout). Non-zero exit → fall back to Push (Step E); surface the helper's stderr verbatim.
3. Type the 6-digit code → Submit/Verify. Retry once at the next 30s boundary if rejected. Rejected twice → abort: `"TOTP rejected twice — check Mac clock: sudo sntp -sS time.apple.com"`. **Never log the code or seed.**

**Step D — Land back on target:** After auth, if the browser lands on the JumpCloud **console/dashboard** instead of the report, **re-navigate to the original target URL**. The session is now established, so it loads directly.

**Step E — Push fallback (only if TOTP unavailable):** Click "Send Push", output `"⏳ JumpCloud push sent — approve on your phone to continue."`, poll every 5s up to 90s for a redirect off the login page. No redirect after 90s → abort: `"⚠️ Push not approved after 90s — re-run"`.

> **Current status (2026-06-12):** Persistent Playwright profile + Keychain creds + TOTP seed all enrolled → login is fully unattended. Push remains a fallback.

---

## Key Facts

| Item | Value |
|------|-------|
| Dealer | Dyer & Dyer Volvo Cars |
| cars.com Dealer id | `10730` |
| admin.cars.com UUID | `f4cb3cc7-1b08-5d24-a78d-1e877a122410` (Chamblee GA 30341) |
| Sheet ID | `1TWMwKUnntKZpjQDX6rbrScDHHfV5jQisG1EIAwIFwC8` |
| LEI Tableau URL | `https://us-west-2b.online.tableau.com/#/site/cars/views/LowEngagedInventoryReport/LEI-Localv2/df8e4b1f-0a39-49e8-a08a-c20b4b4192f4/DyerDyerVolvo` |
| Download path | `~/.playwright-mcp/` |
| PBT sort range | `A4:L5000` (data rows on R4+, headers R3, empty R1–R2) |
| Sort col | J (Difference to Next Badge) |
| Threshold cell | E1 (= $1000) |
| Schedule | Thursdays 8:00 AM MST (`com.jcrawley.dyer-pb-report`) |

> ⚠️ **Always compose HTML email** — use `Content-Type: text/html` and base64url-encode as RFC 2822 `raw` parameter.
