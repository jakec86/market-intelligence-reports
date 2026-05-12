# EchoPark DealerRater Review Report — Monthly Workflow

Run the full monthly EchoPark DealerRater Review Report. Scheduled: **1st of every month**.

---

## Email Drafting Rule

Each draft must feel fresh but follow a consistent strategy. **Refresh the wording every month** — do not reuse the same email body from the prior month. Mix up the structure, lead with a different insight, and keep it engaging.

- **Vary:** opening line, phrasing of key insights, any notable callout (e.g. a store with standout reviews or a rating change), structure of the body
- **Include:** award eligibility progress update (how many stores have hit the 25-review threshold, which stores are leading, any stores at risk)
- **Keep consistent:** professional-casual tone, concise (4–6 sentences max), lead with high-level summary, mention resolution notes if applicable, close with "Cheers, Jake"
- **Never:** use the same opening line or body structure twice in a row, be vague about the data, copy-paste from the previous month
- **Attachment:** Excel file attached (no Google Sheet link in body) — reference it as "the attached report"

Example openings (rotate and riff on these):
- "Team, your monthly DealerRater report is ready..."
- "Happy first of the month — here's the latest review data..."
- "Quick update: the DealerRater numbers are in..."
- "Dropping in your monthly review report..."
- "March reporting is in — strong numbers across the board..."

---

## Stores

Search each store **by name** on the DealerRater dealer portal dashboard:

1. EchoPark Automotive Nashville
2. EchoPark Automotive St. Louis
3. EchoPark Automotive Houston Stafford
4. EchoPark Automotive Houston
5. EchoPark Automotive Charlotte
6. EchoPark Automotive New Braunfels - Outlet
7. EchoPark Automotive Las Vegas
8. EchoPark Automotive Centennial
9. EchoPark Automotive Atlanta
10. EchoPark Automotive San Antonio
11. EchoPark Automotive Dallas
12. EchoPark Automotive Thornton
13. EchoPark Automotive Colorado Springs
14. EchoPark Automotive Raleigh
15. EchoPark Automotive Birmingham
16. EchoPark Automotive Sacramento - Roseville
17. EchoPark Automotive Phoenix

---

## Steps

### Step 1 — DealerRater: Log in & collect metrics + resolution counts

- Use Playwright to navigate to `https://www.dealerrater.com/dp/106349/dashboard`
- Log in with Cars.com / METAL SSO credentials (jcrawley@cars.com) if prompted
- For **each store**, navigate to its Reviews page (`/dp/{id}/reviews/`):
  1. **Metrics:** Click the DealerRater/Cars.com icon (`#carsBrands img#cars`) to reveal the Cars Commerce popup (`#carsInfoDialog`). **Important:** remove the `#carsInfoDialog` element from DOM before clicking to force a fresh AJAX load — the popup caches stale data across SPA navigations.
  2. Extract **DealerRater** star rating + review count, and **Cars.com** star rating + review count. Note: counts may have commas (e.g. "1,300").
  3. **Resolution count:** Check for the "Respond now to X reviews needing resolution" banner. Record the count and the link URL (filtered to `OnlyNegative` + `NoResponseEntered`).
- Metrics should be current as of the day pulled (the 1st of the month)

#### Known dealer IDs (for direct navigation via `/dp/{id}/reviews/`):
| Store | ID |
|-------|----|
| Nashville | 3760 |
| St. Louis | 118753 |
| Houston Stafford | 117761 |
| Houston (North) | 115219 |
| Charlotte | 115220 |
| New Braunfels | 115221 |
| Las Vegas | 118428 |
| Centennial | 106056 |
| Atlanta | 117976 |
| San Antonio | 114739 |
| Dallas | 16566 |
| Thornton | 106054 |
| Colorado Springs | 114436 |
| Raleigh | 118708 |
| Birmingham | 40624 |
| Sacramento | 120085 |
| Phoenix | 23325 |

### Step 2 — Google Sheet: Update "2026" tab

- Open the Google Sheet: `https://docs.google.com/spreadsheets/d/1S1hNN35ph7evbY9tqVIiOUKr2HCwtft9/edit?gid=81384234#gid=81384234`
- Navigate to the **2026** tab
- Each store occupies 12 rows (Jan–Dec). Stores are alphabetical starting at row 3:
  Atlanta=3, Birmingham=15, Centennial=27, Charlotte=39, Colorado Springs=51, Dallas=63, Houston=75, Houston Stafford=87, Las Vegas=99, Nashville=111, Phoenix=123, Raleigh=135, San Antonio=147, San Antonio (New Braunfels)=159, Thornton=171, Sacramento=183, St. Louis=195
- For each store, find the current month's row (e.g. March = start_row + 2) and enter:
  - Column C: DealerRater star rating
  - Column D: DealerRater review count
  - Column E: Cars.com star rating
  - Column F: Cars.com review count
  - Column G: If the store has reviews needing resolution, add a `=HYPERLINK()` with the DealerRater link and text like "X Review(s) Resolution"
- **Clear previous month's notes:** After entering current month data, delete any resolution notes from the prior month's rows (column G)
- Store names in the sheet map to the Account Name column (A). Match by name — note some sheet names may differ slightly (e.g. "Houston" vs "Houston North", "Phoenix" vs "Phoenix (Avondale)", "New Braunfels - Outlet" vs "San Antonio (New Braunfels)")

### Step 3 — Google Sheet: Update "Award Eligibility" tab

- Switch to the **Award Eligibility** tab
- For each store, collect Jan through current month review data from DealerRater:
  - Filter reviews page with `StartDate=1/1/[year]&EndDate=[last day of current month]/[year]` to get total reviews for the period
  - Also filter with `Filter=OnlyPositive` to get positive review count
- Update eligibility columns (rows 2–18, alphabetical by store):
  - Column B: Total DealerRater reviews received Jan through current month (progress toward 25)
  - Column C: At least 1 positive review per quarter — Y/N for each completed quarter (Q1=Jan-Mar, Q2=Apr-Jun, etc.)
  - Column D: Received Reviews Avg Rating > 4.0 — Y/N (use the current DealerRater star rating)
  - Column E: Eligible? Y if reviews >= 25 AND all completed quarters have positive reviews AND rating > 4.0; N otherwise

### Step 4 — QC

- Confirm all 17 stores have been updated for the current month on the "2026" tab
- Verify Award Eligibility tab reflects the latest data
- Flag any anomalies (e.g. significant rating drops, missing data, stores not found on DealerRater)

### Step 5 — Draft Email (do NOT send — draft only)

Use Playwright to compose a Gmail draft (search for the existing thread and reply):

1. **Search Gmail** for `subject:DealerRater Reporting` and open the most recent thread
2. **Reply all** → click the reply type dropdown → **Edit subject** → change the month (e.g. "February" → "March")
3. **Recipients:**
   - **To:** McAlister, Julie (julie.mcalister@echopark.com), Niazi, Suhail A. (echopark.com), Smith, Geremy, Stevens, Shane (shane.stevens@sonicautomotive.com), Ross, Travielle (Travielle.Ross@sonicautomotive.com)
   - **Cc:** Sharon Cunane (scunane@cars.com)
   - **Remove** any outdated addresses (e.g. travielle.ross@echopark.com)
4. **Body** (vary wording per the Email Drafting Rule above):
```
[Varied opening],

[1–2 sentence high-level summary: highlight any standout stores, notable rating changes, or overall trends across the 17 locations.]

[1 sentence about review resolutions if any stores have them — reference the "Note" column in the attached report.]

Cheers,
Jake
```
5. **Attachment:** Download the Google Sheet as Excel (`.xlsx`) via the export URL: `https://docs.google.com/spreadsheets/d/1S1hNN35ph7evbY9tqVIiOUKr2HCwtft9/export?format=xlsx` — save to `~/Downloads/` and attach to the draft. Do NOT include the Google Sheet link in the body.
6. **Save as draft** for review — never send directly

---

## Defaults

- Dealer portal entry point: `https://www.dealerrater.com/dp/106349/dashboard`
- Google Sheet: `https://docs.google.com/spreadsheets/d/1S1hNN35ph7evbY9tqVIiOUKr2HCwtft9/edit?gid=81384234#gid=81384234`
- Excel export: `https://docs.google.com/spreadsheets/d/1S1hNN35ph7evbY9tqVIiOUKr2HCwtft9/export?format=xlsx`
- Schedule: 1st of every month
- 17 EchoPark stores (listed above)

> ⚠️ **Always compose HTML email** — use `Content-Type: text/html` and base64url-encode as RFC 2822 `raw` parameter.
