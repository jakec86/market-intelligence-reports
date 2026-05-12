# Price Badge Report — Weekly Workflow (Hendrick Automotive Group)

Run the full weekly Price Badge Report workflow for Hendrick Automotive Group. Scheduled: **Mondays at 6:00 AM MST**.

---

## Key Differences from Nalley

- **No admin.cars.com / Demand Signals step** — PTM % from that source is omitted for this dealer group
- **Price badge range: $500** (Nalley uses $1,000)
- **DMA filter: ALL** (select all DMAs)
- **Dealer filter: "Hendricks"** (select all related stores under the Hendrick Automotive Group)

---

## Email Drafting Rule

Each draft must feel fresh but follow a consistent strategy:
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

## Steps

### Step 0 — Pre-flight (REQUIRED — abort on any failure)

Run these before any work. Do not proceed with partial auth state.

1. **TOTP Keychain** — run `bash ~/.claude/scripts/check-totp-keychain.sh`. If warning fires, abort — TOTP is required for this workflow (no push fallback).
2. **Tableau PAT** — run `bash ~/.claude/scripts/check-tableau-pat.sh`. If warning fires, abort and fix PAT in `~/.claude/settings.json` before continuing.
3. **Gmail MCP** — run `bash ~/.claude/scripts/verify-gmail-mcp.sh`. If warning fires, stop — Gmail draft creation will fail.

### Step 1 — Tableau: Low Engaged Inventory
- Use the `tableau` MCP to pull the **LEI-Local v2** view from the Low Engaged Inventory Report (site: cars, us-west-2b)
- **If the Tableau login redirects to a JumpCloud SSO page**, run the JumpCloud MFA Sub-procedure (defined below) before continuing.
- **Filters:**
  - DMA: **ALL** (select all)
  - Maj Dealer Name: **Hendricks** (selects all Hendrick Automotive Group stores)
- **CSV schema validation (before import):** read the first row of the downloaded CSV and confirm the expected columns are present in the expected order. If the header row differs from the last known good run, abort with a diff — the Tableau export format has changed silently before and caused bad sheet data. Log the observed headers so the expected-schema list can be updated if the change is intentional.
- Export the report data into the sheet's **Data Import_Inventory Report** tab

### Step 2 — Google Sheet QC
Sheet: [Price Badge Report - Hendricks](https://docs.google.com/spreadsheets/d/1guqWV9HFb2MijC7qQ7qinL4oljbu0N1o9TU5zcmy3GM/edit?gid=565895707#gid=565895707)

- **DO NOT modify any formulas** — the VLOOKUPs and column J formulas are correct. If data looks wrong, it's a data import issue. Fix the import, not the formulas.
- **NEVER clear+rewrite the Price Badge Tool tab** — this destroys the VLOOKUPs. Only touch the Data Import tab and the sort range on the PBT tab.

#### QC Checks
1. Confirm columns E (Days Live), F (# Photos), G (Your Price), H (Current Badge), I (Next Badge), J (Difference to Next Badge) are all populating from the formulas
2. Verify SAMs are populating correctly based on the **SAM Assignment** tab
3. **Clear all filters** before sorting — ensure filter is grabbing ALL data
4. **Sort range A3:J only** — Hendrick PBT has the header in Row 2 (purple bg, white bold). Use "Sort range" on data rows A3 downward only — this prevents header corruption.
5. Within that range: sort SAMs alphabetically A–Z (column A), then sort column J by green fill color (green on top).
6. Read **J1** percentage — this is the stat for the email (% within $500 of moving badges)
7. Update the report date in the sheet name if needed

### Step 3 — Draft Email (do NOT send — draft only)
Use Gmail MCP to compose a draft:

**To:** anne.Lewis@hendrickauto.com
**Subject:** `Re: Cars.com: Price Badge Report`
**Body:** (vary wording per the rule above, keep this structure)
```
[Varied opening — e.g. "Good Day Anne,"]

[1–2 sentence insight: X% of inventory within $500 of moving price badges. Optional: flag a specific vehicle or badge opportunity.]

[Hyperlinked "Price Badge Report" — use HTML <a> tag with sheet URL as href]

Cheers,

Jake
```

- **Hyperlink** the Google Sheet name (e.g. `<a href="URL">Price Badge Report</a>`) — do NOT paste raw URL
- Use `Content-Type: text/html` and base64url-encode as RFC 2822 `raw` parameter
- Include `In-Reply-To` and `References` headers from the last message in the thread
- Use `From: jcrawley@carscommerce.inc` for Hendrick (not @cars.com)
- Save as draft for review — **never send directly**

---

## JumpCloud MFA Sub-procedure

Invoke whenever Playwright lands on a JumpCloud SSO challenge page (URL matches `sso.jumpcloud.com/*` or page title contains "JumpCloud").

1. **Detect the factor form.**
   - If a visible "Verification Code" input field is present → proceed to step 2.
   - If only a "Send Push" button is visible → click the "Try another way" / "Use authenticator code" link to reveal the TOTP input, then proceed.
   - If neither is available → abort with the error: `"JumpCloud MFA page shows no TOTP option — change default factor at console.jumpcloud.com/userconsole → Security → Multi-Factor Authentication"`.
2. **Retrieve a current code.** Run `~/.claude/scripts/jumpcloud-totp.py` as a subprocess. Capture stdout. If exit code is non-zero, abort and surface the helper's stderr verbatim (it includes the remediation command).
3. **Submit.** Type the 6-digit code into the Verification Code input, then click the Submit/Verify button.
4. **Verify success.** Wait up to 10 seconds for the page to redirect away from `sso.jumpcloud.com`.
5. **Handle rejection (retry once).** If the page re-renders with an "invalid code" error:
   - Wait until the next 30-second TOTP boundary (`sleep $(( (30 - $(date +%S) % 30) % 30 ))`).
   - Fetch a fresh code from the helper.
   - Submit it.
   - If that also fails, abort with: `"TOTP rejected twice — check Mac clock (sudo sntp -sS time.apple.com) and that the Keychain seed matches the current JumpCloud enrollment"`.
6. **Never log the 6-digit code or the seed.** If logging page HTML for debugging, redact the Verification Code input value.

---

## Defaults
- Dealer Group: Hendrick Automotive Group
- Sheet: [Price Badge Report - Hendricks](https://docs.google.com/spreadsheets/d/1guqWV9HFb2MijC7qQ7qinL4oljbu0N1o9TU5zcmy3GM/edit?gid=565895707#gid=565895707)
- Primary recipient: anne.Lewis@hendrickauto.com
- Override dealer by specifying at invocation: `/hendricks-pb-report [dealer name or ID]`
