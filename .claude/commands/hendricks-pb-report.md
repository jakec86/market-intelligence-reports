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

> **Note:** Tableau MCP PAT returns 401 for this view due to RLS — use Playwright only for all Tableau steps.

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

1. **TOTP Keychain** — run `bash ~/.claude/scripts/check-totp-keychain.sh`. If warning fires, TOTP is missing — note before proceeding.
2. **Playwright MCP** — verify `mcp__playwright__browser_navigate` tool is available. If missing, abort and recommend `/mcp` check.
3. **Gmail MCP not required** — email is sent via Gmail API directly by `pb_report.py`.

---

## Step 1 — Tableau: LEI Crosstab Download

Navigate to the full Tableau Cloud portal URL (not the embed URL):
```
https://us-west-2b.online.tableau.com/#/site/cars/views/LowEngagedInventoryReport/LEI-Localv2
```

If JumpCloud SSO fires, run the **JumpCloud MFA Sub-procedure** before continuing.

**Step A — Apply DMA filter (All):**

1. Click the `Filter DMA Inclusive` combobox (currently shows "Detroit")
2. In the dialog, click the **inner `<input>` checkbox** inside the `(All)` row to select all DMAs
3. Press Escape to close
4. **Wait for recompute** (~60 sec) — a `tab-glass` overlay will cover the viz. Wait until it clears before proceeding.

**Step B — Apply Maj dealer name filter (Hendrick):**

1. Click the `Filter Maj dealer name Inclusive` combobox
2. **Deselect everything:** click the inner `<input>` checkbox inside `(All)` to deselect all
3. Type `Hendrick Automotive Group` in the search box and press Enter
4. Check `Hendrick Automotive Group`
5. Clear the search box (fill with a space, then Backspace) — Apply is **disabled while search text is present**
6. Click **Apply**
7. Wait for recompute (~15–30 sec)

> **Stock type: leave as "Used"** — correct for this report.

**Download the crosstab:**
1. Click **Download** in the toolbar
2. Click **Crosstab**
3. Sheet: `Low Engaged Inventory Report - Local v2` (pre-selected)
4. Format: switch to **CSV**
5. Click **Download**

File lands at: `~/.playwright-mcp/Low-Engaged-Inventory-Report---Local-v2.csv`

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
  --lei ~/.playwright-mcp/Low-Engaged-Inventory-Report---Local-v2.csv \
  --send
```

Expected output:
```
✓ Imported rows to 'Data Import_Inventory Report'
✓ Pass 1–4: sort complete
✓ Stats: X/N within $500 (XX%), X already Great
✓ Gmail draft created (id: ...)
✓ Email sent (message id: ...)
```

---

## Step 3 — Post-Run QC

1. Open the sheet: [Price Badge Report - Hendricks](https://docs.google.com/spreadsheets/d/1guqWV9HFb2MijC7qQ7qinL4oljbu0N1o9TU5zcmy3GM/edit?gid=565895707#gid=565895707)
2. Confirm **Price Badge Tool** tab has data in cols E–J
3. Header in Row 2 (purple bg, white bold) — data starts Row 3
4. **Do NOT modify any formulas** — VLOOKUPs and col J are correct

---

## Step 4 — Confirm Send

Email is sent automatically by `pb_report.py --send`. Recipients are baked into the script config:

**To:** anne.Lewis@hendrickauto.com
**From:** jcrawley@carscommerce.inc

Confirm the script output shows `✓ Email sent (message id: ...)`.

---

## JumpCloud MFA Sub-procedure

Invoke whenever Playwright lands on `sso.jumpcloud.com`.

**Primary method: TOTP**

1. Switch to TOTP immediately — click "Try another way" / "Use authenticator code". If Verification Code input is already visible, proceed to step 2.
2. Run `python3 ~/.claude/scripts/jumpcloud-totp.py`. Capture stdout. If exit code non-zero, surface stderr and fall back to Push.
3. Type the 6-digit code into each individual digit box (one char per box), then press Enter. Retry once at next 30s boundary if rejected. If rejected twice: abort with `"TOTP rejected twice — check Mac clock: sudo sntp -sS time.apple.com"`.

**Push fallback (only when TOTP unavailable):**
4. Click "Send Push". Poll every 5s for up to 90s for redirect. If no redirect: abort with `"⚠️ Push not approved after 90s"`.

---

## Key Facts

| Item | Value |
|------|-------|
| Dealer | Hendrick Automotive Group |
| Sheet ID | `1guqWV9HFb2MijC7qQ7qinL4oljbu0N1o9TU5zcmy3GM` |
| LEI Tableau URL | `https://us-west-2b.online.tableau.com/#/site/cars/views/LowEngagedInventoryReport/LEI-Localv2` |
| Download path | `~/.playwright-mcp/` |
| PBT sort range | `A3:J5000` (header Row 2, data Row 3+) |
| Sort col | J (Difference to Next Badge) |
| DMA filter | All (click (All) checkbox — Detroit is default) |
| Maj dealer filter | Hendrick Automotive Group |
| Stock type | Used (leave as-is) |
| Email from | jcrawley@carscommerce.inc |
