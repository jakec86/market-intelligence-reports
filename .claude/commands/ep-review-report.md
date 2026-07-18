# EchoPark DealerRater Review Report — Monthly Workflow

Run the full monthly EchoPark DealerRater Review Report. Scheduled: **1st of every month via cron** (`3 7 1 * *`).

---

## Email Drafting Rule

- **Vary:** opening line, phrasing of key insights, any notable callout
- **Include:** award eligibility progress (stores at/near 25-review threshold, newly eligible this month)
- **Keep consistent:** professional-casual, concise (4–6 sentences max), close with "Cheers, Jake"
- **Attachment:** Excel file attached — reference as "the attached report"

Example openings:
- "Quick update on the May DealerRater numbers for EchoPark..."
- "Happy first of the month — here's the latest review data..."
- "Dropping in your monthly review report..."

---

## Recipients

- **To:** julie.mcalister@echopark.com, suhail.niazi@echopark.com, geremy.smith@echopark.com, Shane.Stevens@sonicautomotive.com, travielle.ross@sonicautomotive.com
- **Cc:** scunane@cars.com
- **Thread:** reply to existing `subject:DealerRater Reporting` thread; update subject month

---

## Stores & Dealer IDs

| Store | DR ID |
|-------|-------|
| Atlanta | 117976 |
| Birmingham | 40624 |
| Centennial | 106056 |
| Charlotte | 115220 |
| Colorado Springs | 114436 |
| Dallas | 16566 |
| Houston (North) | 115219 |
| Houston Stafford | 117761 |
| Las Vegas | 118428 |
| Nashville | 3760 |
| New Braunfels | 115221 |
| Phoenix | 23325 |
| Raleigh | 118708 |
| Sacramento | 120085 |
| San Antonio | 114739 |
| St. Louis | 118753 |
| Thornton | 106054 |

---

## Steps

### Step 1 — DealerRater: Log in & collect metrics

**Login (Chrome DevTools MCP):**
1. Navigate to `https://www.dealerrater.com/dp/106349/dashboard`
2. If redirected to `login.carscommerce.inc`:
   - Fill Email field with `jcrawley@cars.com`
   - Click **Sign In** — no password required, email alone completes login

**Collect for each store** via `https://www.dealerrater.com/dp/{ID}/reviews/`:
- Wait 3s after navigation, then read `document.body.innerText`
- Parse from the "Cars Commerce" block in the text:
  ```
  Cars Commerce

  Cars.com
  4.X
  NNNN
  DealerRater
  4.X
  NNNN
  ```
  → `cars_rating`, `cars_count`, `dr_rating`, `dr_count`
- **Resolution:** check for `"Respond now to X review"` text + grab the `a[href*="OnlyNegative"]` href
- Use a subagent to parallelise all 17 stores for speed

### Step 2 — Google Sheet: Update "2026" tab

**⚠️ File is XLSX on Drive — Sheets API/gspread cannot write to it.** Use download → openpyxl → re-upload.

**Download** (browser already authenticated):
```
Navigate to: https://docs.google.com/spreadsheets/d/1S1hNN35ph7evbY9tqVIiOUKr2HCwtft9/export?format=xlsx
File lands in ~/Downloads/ as EchoPark DealerRater Reporting & Award Eligibility - 2026 (N).xlsx
```

**Edit with openpyxl**, then **upload via Drive API**:
```python
import requests, json
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

with open("/Users/jcrawley/.claude/tokens/gsheets_credentials.json") as f:
    td = json.load(f)
with open("/Users/jcrawley/.claude/google_credentials.json") as f:
    s = json.load(f)
cc = s.get("installed") or s.get("web") or {}
creds = Credentials(token=td.get("access_token",""), refresh_token=td["refresh_token"],
    token_uri="https://oauth2.googleapis.com/token",
    client_id=cc["client_id"], client_secret=cc["client_secret"],
    scopes=["https://www.googleapis.com/auth/drive","https://www.googleapis.com/auth/spreadsheets"])
creds.refresh(Request())
td["access_token"] = creds.token
with open("/Users/jcrawley/.claude/tokens/gsheets_credentials.json","w") as f:
    json.dump(td, f)

with open("updated_file.xlsx","rb") as f:
    content = f.read()
r = requests.patch(
    "https://www.googleapis.com/upload/drive/v3/files/1S1hNN35ph7evbY9tqVIiOUKr2HCwtft9?uploadType=media",
    headers={"Authorization": f"Bearer {creds.token}",
             "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"},
    data=content)
assert r.status_code == 200
```

**Sheet layout — 2026 tab:**
- Headers: Row 1 (DEALERRATER / CARS.COM / Note), Row 2 (Month / Reviews / Rating / Reviews / Rating)
- 17 stores alphabetical, each occupying 12 rows (Jan–Dec), starting at row 3:
  ```
  Atlanta=3, Birmingham=15, Centennial=27, Charlotte=39, Colorado Springs=51,
  Dallas=63, Houston=75, Houston Stafford=87, Las Vegas=99, Nashville=111,
  Phoenix=123, Raleigh=135, San Antonio=147, New Braunfels=159, Thornton=171,
  Sacramento=183, St. Louis=195
  ```
- Month offset: Jan=+0, Feb=+1, Mar=+2, Apr=+3, May=+4 … Dec=+11
- Columns per row:
  - B: Month name — verify/fix if wrong
  - C: DealerRater reviews count
  - D: DealerRater star rating
  - E: Cars.com reviews count
  - F: Cars.com star rating
  - G: `=HYPERLINK("url","X Review(s) Resolution")` if resolution; else `None`
- **After writing current month: clear G for all OTHER months** (only current month keeps resolution link)
- Columns K–N are hidden — do not touch

**Prior month data recovery:** If a month is missing, search Gmail for `subject:DealerRater Reporting - [Month]`, download the attachment, and read the correct values from it.

### Step 3 — Google Sheet: Update "Award Eligibility" tab

Rows 2–18, alphabetical by store. For each store:
- **B**: Total DR reviews Jan 1 – last day of current month (use `?StartDate=1/1/YYYY&EndDate=M/31/YYYY` filter on DR reviews page)
- **C**: At least 1 positive review in the **current quarter** — Y/N
  - Determine the current quarter from today's date: Q1=Jan–Mar, Q2=Apr–Jun, Q3=Jul–Sep, Q4=Oct–Dec
  - Query DR reviews page with `?StartDate=M/1/YYYY&EndDate=M/D/YYYY` spanning the first day of the current quarter through today
  - A review counts as positive if the star rating is 4 or 5
  - Y = at least 1 positive review found; N = zero positive reviews so far this quarter
  - **Flag N stores in the sheet:** apply a yellow fill (`FFFF00`) to the C cell for any store with N, so stores that still need a positive review before quarter end are immediately visible
  - **In the email:** call out N stores by name (e.g. "X stores — [Store A], [Store B] — have not yet received a positive review this quarter and need focus before [last month of quarter].")
- **D**: Current DR rating > 4.0 — Y/N
- **E**: Eligible = B ≥ 25 AND C = Y AND D = Y

### Step 4 — QC

- All 17 stores populated in "2026" tab for current month (C–F non-null)
- All B column month labels correct (no numbers in place of month names)
- G column: only current month has resolution links; all prior months cleared
- Award Eligibility tab reflects updated counts
- Cumulative DR counts increase month-over-month (flag any decreases)

### Step 5 — Build Gmail Draft (recipients pre-filled, ready to send)

Use Gmail API directly (not Playwright — more reliable). Create a **draft** with actual recipients already in To/Cc so Jake just reviews and hits Send.

```python
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import base64

# Find prior thread
results = gmail.users().messages().list(userId="me",
    q="subject:DealerRater Reporting", maxResults=1).execute()
thread = gmail.users().threads().get(userId="me",
    id=results["messages"][0]["threadId"], format="metadata").execute()
thread_id = thread["id"]
last_msg_id = thread["messages"][-1]["id"]

msg = MIMEMultipart("alternative")
msg["Subject"] = f"Re: DealerRater Reporting - {month_name}"
msg["From"] = "jcrawley@cars.com"
msg["To"] = "julie.mcalister@echopark.com, suhail.niazi@echopark.com, geremy.smith@echopark.com, Shane.Stevens@sonicautomotive.com, travielle.ross@sonicautomotive.com"
msg["Cc"] = "scunane@cars.com"
msg["In-Reply-To"] = last_msg_id
msg["References"] = last_msg_id
# attach HTML body + XLSX, then:
draft = gmail.users().drafts().create(userId="me",
    body={"message": {
        "raw": base64.urlsafe_b64encode(msg.as_bytes()).decode(),
        "threadId": thread_id
    }}).execute()
print(f"✓ Draft ready for review: {draft['id']}")
```

Attach the fresh XLSX export (re-download after Drive upload). Draft sits in Jake's inbox with recipients pre-filled — review and send when ready.

---

## Defaults

- Google Sheet ID: `1S1hNN35ph7evbY9tqVIiOUKr2HCwtft9`
- DR portal: `https://www.dealerrater.com/dp/106349/dashboard`
- Schedule: `3 7 1 * *` (7:03 AM local, 1st of every month) via `~/.claude/schedules/run-report.sh`
- MCP config for scheduled runs: `~/.claude/schedules/mcp-config.json` (includes google-sheets, gmail, playwright, gdrive)
- 17 stores (see table above)

> ⚠️ **Always send via Gmail API with HTML body** — base64url-encode the full RFC 2822 message as `raw`.
> ⚠️ **DealerRater login is email-only** — fill `jcrawley@cars.com` in the Email field and click Sign In. No password needed. Works in both interactive and headless Playwright sessions.
