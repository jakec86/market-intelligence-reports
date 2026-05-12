# Price Badge Report — Nalley Lexus Galleria Weekly Workflow

Run the full weekly Price Badge Report for Nalley Lexus Galleria. Scheduled: **Mondays and Fridays at 6:00 AM MST**.

---

## Email Drafting Rule

Each draft must feel fresh but follow a consistent strategy:
- **Vary:** opening line, phrasing of the insight stat, any notable callout (e.g. a specific vehicle or badge tier worth flagging)
- **Keep consistent:** professional-casual tone, concise (3–5 sentences max), lead with the data, close with "Cheers, Jake"
- **Never:** use the same opening line twice in a row, be vague about the stat, or skip the sheet link

---

## Pre-flight (REQUIRED — abort on any failure)

Run these before touching Tableau or admin.cars.com. Do not proceed with partial auth state.

1. **TOTP Keychain** — run `bash ~/.claude/scripts/check-totp-keychain.sh`. If warning fires, TOTP is missing — MFA will fall back to push. Note this before proceeding.
2. **Playwright MCP** — verify `browser_navigate` tool is available (`mcp__playwright__browser_navigate`). Required for both Tableau and admin.cars.com. If missing, abort and recommend `/mcp` check.
3. **Gmail MCP** — run `bash ~/.claude/scripts/verify-gmail-mcp.sh`. If warning fires, stop — Gmail draft creation will fail.

> **Note:** Tableau MCP PAT returns 401 for this view due to RLS — use Playwright only for all Tableau steps.

---

## Step 1 — Tableau: LEI Crosstab Download

**Navigate** to the full Tableau Cloud portal URL (not the embed URL):
```
https://us-west-2b.online.tableau.com/#/site/cars/views/LowEngagedInventoryReport/LEI-Localv2
```

**Step A — Apply DMA filter (Atlanta):**

1. Click the `Filter DMA Inclusive` combobox
2. In the dialog, find and click the `Atlanta` checkbox (Detroit stays checked — do not uncheck it)
3. Press Escape to close the DMA dialog
4. **Wait for recompute** — a `tab-glass` overlay will cover the viz. Wait until it clears (~60 sec). Any click while the overlay is up will fail with a timeout.

**Step B — Apply Dealer Name filter (Nalley only):**

1. Click the `Filter Dealer Name and ID Inclusive` combobox
2. **Deselect everything first** (regardless of current state): click the **inner `<input>` checkbox** inside the `(All)` row — this toggles to all-off. If it was already in All state, one click deselects all. If a prior run left Nalley selected, clicking (All) inner checkbox first clears it then checks all; click it a second time to deselect all.
3. Type `Nalley Lexus Galleria` in the search box and press Enter → "Found 1 matches"
4. Check `Nalley Lexus Galleria - 109754`
5. Clear the search box (fill with a space, then Backspace) — Apply is **disabled while search text is present**
6. Click **Apply**
7. Wait for recompute (~15–30 sec)

> **Maj dealer name / Grp dealer name: skip entirely** — not needed for this report.
> **Stock type: leave as "Used"** — correct for this report.

**Download the crosstab:**
1. Click **Download** in the toolbar
2. Click **Crosstab**
3. Sheet: `Low Engaged Inventory Report - Local v2` (pre-selected — leave it)
4. Format: switch to **CSV**
5. Click **Download**

File lands at: `~/.playwright-mcp/Low-Engaged-Inventory-Report---Local-v2.csv`

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

If JumpCloud SSO fires, run the MFA Sub-procedure before continuing.

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

This script handles everything: import both CSVs → sort PBT → read stats → hide Data Import tab → create Gmail draft.

```bash
python3 ~/Documents/scripts/pb_report.py \
  --dealer nalley \
  --lei ~/.playwright-mcp/Low-Engaged-Inventory-Report---Local-v2.csv \
  --dem ~/.playwright-mcp/Pricing.csv
```

Expected output:
```
✓ Imported 50–60 LEI rows to 'Data Import_Inventory Report'
✓ Imported ~166 Dem Signal rows to 'Data Import_Dem Signal - $ Comp'
✓ Pass 1–4: sort complete
✓ Stats: X/51 within $1,000 (XX%), 14 already Great
✓ Dem Signal: XX% At / XX% Above / XX% Under
✓ Hidden tab 'Data Import_Inventory Report'
✓ Gmail draft created (id: ...)
```

If the script errors on Gmail auth, check `~/.claude/tokens/gmail_jcrawley.json` — the refresh token is permanent but the access token may need a refresh via the Google OAuth endpoint.

---

## Step 4 — Post-Run QC

1. Open the sheet: [Price Badge Report - Nalley Lexus Galleria](https://docs.google.com/spreadsheets/d/13Jn8vJSG7vRYW9xpuxrMi9kXNhiV_TaCrjQ5lNQRPP8/edit?gid=565895707#gid=565895707)
2. Confirm **Price Badge Tool** tab has data in cols E–J (Days Live, Photos, Price, Current Badge, Next Badge, Diff)
3. Check **col K** — confirm K formulas are filled down to match the data rows
4. Sheet title should be `Price Badge Report - Nalley Lexus Galleria - M.D.YY`
5. **Do NOT modify any formulas** — VLOOKUPs and col J are correct. If data looks wrong, re-run the import.

---

## Step 5 — Finalize Gmail Draft

The draft is created without recipients (Nalley `email_to` is blank in config). Add them:

**To:** Grayson Caudill `gcaudill1@nalleycars.com`, Jason E. Brown `jbrown1@nalleycars.com`, Zlatan Ibrahimbegovic `zibrahimbegovic@asburyauto.com`, Rashad Saeed `rsaeed@nalleycars.com`
**Cc:** Shashank Dharanendra `sdharanendra@asburyauto.com`

> **Warning:** Do NOT guess `@nalleyauto.com` addresses — they bounce. All four primary contacts are at `@nalleycars.com` or `@asburyauto.com`. Confirmed from sent mail 2026-05-04.

Use Gmail MCP to find the draft by ID (printed in pb_report.py output) and update recipients, OR open Gmail and add them manually before sending.

---

## JumpCloud MFA Sub-procedure

Invoke whenever Playwright lands on `sso.jumpcloud.com`.

**Primary method: TOTP**

1. **Detect the factor form.** If only "Send Push" is visible, click "Try another way" / "Use authenticator code" to reveal the TOTP input. If no TOTP option exists, fall back to Push (step 5).
2. **Retrieve code.** Run `python3 ~/.claude/scripts/jumpcloud-totp.py`. Capture stdout. If exit code is non-zero, fall back to Push (step 5) — surface the helper's stderr verbatim.
3. **Submit.** Type the 6-digit code into the Verification Code input, click Submit/Verify.
4. **Retry once if rejected.** Wait for next 30s TOTP boundary, fetch a fresh code, submit again. If rejected twice: abort with `"TOTP rejected twice — check Mac clock: sudo sntp -sS time.apple.com"`. Never log the code or seed.

**Push fallback (only when TOTP unavailable):**
5. Click "Send Push". Output `"⏳ JumpCloud push sent — approve on your phone to continue."` Poll every 5s for up to 90s for redirect away from `sso.jumpcloud.com`. If no redirect after 90s: abort with `"⚠️ Push not approved after 90s — check JumpCloud app and re-run"`.

> **Current status:** TOTP Keychain seed not yet enrolled (IT reset pending). Push is the active fallback until seed is added.

---

## Key Facts

| Item | Value |
|------|-------|
| Dealer | Nalley Lexus Galleria |
| Customer ID | 109754 |
| admin.cars.com UUID | `156f9bb7-3c44-549c-b16b-0c3af73fdb1f` |
| Sheet ID | `13Jn8vJSG7vRYW9xpuxrMi9kXNhiV_TaCrjQ5lNQRPP8` |
| LEI Tableau URL | `https://us-west-2b.online.tableau.com/#/site/cars/views/LowEngagedInventoryReport/LEI-Localv2` |
| Download path | `~/.playwright-mcp/` |
| PBT sort range | `A4:L5000` (data rows only — headers on R3, empty R1–R2; script uses 5000 as upper bound) |
| Sort col | J (Difference to Next Badge) |
| Threshold cell | E1 |
| Stock type filter | Used (leave as-is) |
| DMA filter | Atlanta (click checkbox — Detroit stays checked; wait ~60s for tab-glass to clear) |

> ⚠️ **Always compose HTML email** — use `Content-Type: text/html` and base64url-encode as RFC 2822 `raw` parameter.

HTML fallback
