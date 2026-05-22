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
3. **Gmail MCP not required** — email is sent via Gmail API directly by `pb_report.py`.

> **Note:** Tableau MCP PAT returns 401 for this view due to RLS — use Playwright only for all Tableau steps.

---

## Step 1 — Tableau: LEI Crosstab Download

Navigate directly to the **Nalley Custom View** (pre-filtered: DMA=Atlanta+Detroit, Dealer=Nalley Lexus Galleria, Used inventory):
```
https://us-west-2b.online.tableau.com/#/site/cars/views/LowEngagedInventoryReport/LEI-Localv2/eaf9a030-bda1-4bc9-a771-574c63bacb9d/NalleyLexusGalleriaPBReport
```

If JumpCloud SSO fires, run the **JumpCloud MFA Sub-procedure** before continuing.

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

This script handles everything: import both CSVs → sort PBT → read stats → hide Data Import tab → send email to recipients.

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

## Step 5 — Confirm Send

Email is sent automatically by `pb_report.py --send`. Recipients are baked into the script config:

**To:** Grayson Caudill, Jason E. Brown, Zlatan Ibrahimbegovic, Rashad Saeed
**Cc:** Shashank Dharanendra

Confirm the script output shows `✓ Email sent (message id: ...)`. If it shows only `✓ Gmail draft created` without a send line, re-run with `--send` explicitly.

---

## JumpCloud MFA Sub-procedure

Invoke whenever Playwright lands on `sso.jumpcloud.com`.

**Primary method: TOTP**

1. **Switch to TOTP.** Click "Try another way" / "Use authenticator code" immediately on landing — don't wait to detect the default. If the Verification Code input is already visible, the click will fail harmlessly; proceed to step 2.
2. **Retrieve code.** Run `python3 ~/.claude/scripts/jumpcloud-totp.py`. Capture stdout. If exit code is non-zero, fall back to Push (step 4) — surface the helper's stderr verbatim.
3. **Submit.** Type the 6-digit code into the Verification Code input, click Submit/Verify. Retry once at the next 30s boundary if rejected. If rejected twice: abort with `"TOTP rejected twice — check Mac clock: sudo sntp -sS time.apple.com"`. Never log the code or seed.

**Push fallback (only when TOTP unavailable):**
4. Click "Send Push". Output `"⏳ JumpCloud push sent — approve on your phone to continue."` Poll every 5s for up to 90s for redirect away from `sso.jumpcloud.com`. If no redirect after 90s: abort with `"⚠️ Push not approved after 90s — check JumpCloud app and re-run"`.

> **Current status:** TOTP active — seed enrolled in Keychain, verified 2026-05-18. Push fallback remains available if TOTP fails.

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
