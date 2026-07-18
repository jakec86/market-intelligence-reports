# eCarOne DealerRater Review Report — Monthly Workflow

Run the full monthly eCarOne DealerRater Review Report.

---

## Email Drafting Rule

- **Vary:** opening line, phrasing of key insights, any notable callout
- **Include:** award eligibility progress (at/near 25-review threshold, quarterly positive review status)
- **Keep consistent:** professional-casual, concise (3–5 sentences max), close with "Cheers, Jake"
- **Attachment:** Excel file attached — reference as "the attached report"

---

## Recipients

- **To:** *(add eCarOne contact — TBD)*
- **Cc:** scunane@cars.com
- **Thread:** reply to existing `subject:DealerRater Reporting` thread (eCarOne); update subject month

---

## Store & Dealer ID

| Store | DR Portal ID |
|-------|-------------|
| eCarOne | 38990 |

---

## Steps

### Step 1 — DealerRater: Log in & collect metrics

**Login (Chrome DevTools or Playwright MCP):**
1. Navigate to `https://www.dealerrater.com/dp/38990/reviews/`
2. If redirected to `login.carscommerce.inc`:
   - Fill Email with `jcrawley@cars.com` → click **Sign In**
   - Google account chooser → select `jcrawley@cars.com`
   - JumpCloud: Continue → fill password from Keychain → SSO Login
   - TOTP: generate from `security find-generic-password -a jcrawley -s jumpcloud-totp -w`

**Collect via fetch in browser context:**
```javascript
async () => {
  const url = 'https://www.dealerrater.com/dp/38990/reviews/';
  const resp = await fetch(url, {credentials: 'include'});
  const html = await resp.text();
  const doc = new DOMParser().parseFromString(html, 'text/html');
  const bodyText = doc.body.innerText;
  const ccIdx = bodyText.indexOf('Cars Commerce');
  const block = bodyText.substring(ccIdx, ccIdx + 1000);
  const lines = block.split('\n').map(l => l.trim()).filter(l => l.length > 0);
  const carsIdx = lines.findIndex(l => l === 'Cars.com');
  const drIdx = lines.findIndex(l => l === 'DealerRater');
  return {
    cars_rating: parseFloat(lines[carsIdx + 1]),
    cars_count: parseInt(lines[carsIdx + 2].replace(/,/g, '')),
    dr_rating: parseFloat(lines[drIdx + 1]),
    dr_count: parseInt(lines[drIdx + 2].replace(/,/g, '')),
    resolution: bodyText.match(/Respond now to (\d+) review/)?.[0] || null,
    resolution_href: doc.querySelector('a[href*="OnlyNegative"]')?.href || null,
  };
}
```

**Award Eligibility data (same session):**
- YTD DR count: `?StartDate=1/1/YYYY&EndDate=M/31/YYYY`
- Q3 positive review check: `?StartDate=7/1/YYYY&EndDate=M/D/YYYY` — look for 4/5-star review text

### Step 2 — Google Sheet: Update "2026" tab

**⚠️ File is XLSX on Drive — use openpyxl + Drive API (not Sheets API).**

**Download:**
```
https://docs.google.com/spreadsheets/d/1GVAusy5imS1J6-Wq2S56EqYl4kwDcCby/export?format=xlsx
```

**Sheet layout — 2026 tab:**
- Headers: Row 1 (DEALERRATER / CARS.COM), Row 2 (Month / Rating / Reviews / Rating / Reviews)
- eCarOne: rows 3–14 (Jan=3, Feb=4, … Dec=14), offset = month_number − 1
- Columns: B=Month, C=DR rating, D=DR reviews, E=Cars.com rating, F=Cars.com reviews, G=resolution HYPERLINK or None
- **Clear G for all months except current** after writing

**Credentials:** `~/.claude/tokens/gsheets_credentials.json` + `~/gcp-oauth.keys.json`

**Upload:**
```python
requests.patch(
  "https://www.googleapis.com/upload/drive/v3/files/1GVAusy5imS1J6-Wq2S56EqYl4kwDcCby?uploadType=media",
  headers={"Authorization": f"Bearer {creds.token}",
           "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"},
  data=updated_bytes)
```

### Step 3 — Google Sheet: Update "Award Eligibility" tab

Row 2 (single store):
- **B**: Total DR reviews Jan 1 – last day of current month
- **C**: At least 1 positive (4/5★) review in current quarter — Y/N; yellow fill (`FFFF00`) for N
- **D**: Current DR rating > 4.0 — Y/N
- **E**: Eligible = B ≥ 25 AND C = Y AND D = Y; yellow fill for N

Quarters: Q1=Jan–Mar, Q2=Apr–Jun, Q3=Jul–Sep, Q4=Oct–Dec

### Step 4 — QC

- 2026 tab: current month row C–F non-null, B = correct month name
- G column: only current month has resolution link; all others cleared
- Award Eligibility: B/C/D/E correct, yellow fills applied
- DR count non-decreasing month-over-month (flag if it drops)

### Step 5 — Build Gmail Draft

```python
# Same pattern as ep-review-report
# Pre-send rule: To: jcrawley@cars.com until format approved
# Actual To: *(TBD — add eCarOne contact)*
# Cc: scunane@cars.com
# Subject: "Re: DealerRater Reporting - {Month}"
# Thread: search Gmail for subject:DealerRater Reporting eCarOne (or start new thread)
# Attachment: fresh XLSX re-downloaded after upload
```

---

## Defaults

- **Google Sheet ID:** `1GVAusy5imS1J6-Wq2S56EqYl4kwDcCby`
- **DR portal:** `https://www.dealerrater.com/dp/38990/dashboard`
- **DR ID:** 38990
- **CCID:** 6000362
- **Cadence:** Monthly (1st of month)
- **Credentials:** same as ep-review-report — `gsheets_credentials.json` + `gcp-oauth.keys.json` + `gmail_jcrawley.json`

> ⚠️ **Gmail draft → Jake first** (pre-send rule) until recipients confirmed and format approved.
> ⚠️ **DealerRater login is JumpCloud SSO** — same flow as PB reports and ep-review-report.
