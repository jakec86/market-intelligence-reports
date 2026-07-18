# eCarOne VPM Report — Monthly Workflow

Run the monthly VPM Premium+ performance report for eCarOne. Updates the Google Sheet with the latest month's VDP and Leads data from Tableau. Output is used for a **digital meeting** (no email draft).

---

## Steps

### Step 1 — Tableau: VPM Premium+ VDP

- **Auth:** Tableau requires JumpCloud SSO. If the browser redirects to a JumpCloud login page, pause and ask the user to log in manually before continuing.
- Use Playwright to open (with URL filter pre-applied — do NOT use the dropdown filter UI):
  `https://us-west-2b.online.tableau.com/#/site/cars/views/UATVPMPremiumReporting_17556278088300/VPMPremiumVDP?Dealer%20Name%20%2B%20ID=eCarOne%20-%206000362`
- Wait for the viz to load (~5 seconds), then verify the Dealer Name + ID filter shows `eCarOne - 6000362`
- Read the data table at the bottom of the viz to capture:
  - **Total Cars.com VDPs** (this is the total impressions value)
  - **VPM VDP's** (this is the VPM impressions value)
- Take a **full-viewport screenshot** and save it (e.g. `ecarone_vdp_screenshot.png`) — this will be inserted into the sheet later
- If the data table is hard to read on-screen, use the **Download > Crosstab** button to export a CSV, then parse the values
- Record these two numbers — they map to the sheet as:
  - `NON VPM Imp` (col C) = Total Cars.com VDPs − VPM VDPs
  - `VPM Imp` (col D) = VPM VDPs
  - `Total Impr` (col E) = Total Cars.com VDPs

### Step 2 — Tableau: VPM Premium+ Leads

- Navigate directly with the URL filter (same approach as Step 1):
  `https://us-west-2b.online.tableau.com/#/site/cars/views/UATVPMPremiumReporting_17556278088300/VPMPremiumLeads?Dealer%20Name%20%2B%20ID=eCarOne%20-%206000362`
- Wait for the viz to load (~5 seconds), then verify the Dealer Name + ID filter shows `eCarOne - 6000362`
- Read the data table to capture:
  - **Total Cars.com Leads (email, phone, chat)** (total leads)
  - **VPM Total Leads** (VPM leads)
- Take a **full-viewport screenshot** and save it (e.g. `ecarone_leads_screenshot.png`) — this will be inserted into the sheet later
- Record these two numbers — they map to the sheet as:
  - `NON VPM Leads` (col F) = Total Cars.com Leads − VPM Total Leads
  - `# VPM Leads` (col G) = VPM Total Leads
  - `# Total Leads` (col H) = Total Cars.com Leads

### Step 2b — Google Sheet: Update screenshots

- Open: `https://docs.google.com/spreadsheets/d/1E6CIiKbmFIWJdr3uWZHPkXMyQFtnDpAK6xdnJ58jz1Q/edit?gid=247007646#gid=247007646`
- **Delete old images:** Take a snapshot to find any floating `Image` elements in the sheet. Click each one and press Delete. **Important:** verify the image is selected (blue handles visible) before pressing Delete — pressing Delete when a cell is active will clear cell contents instead.
- **Insert VDP screenshot:** Navigate to cell B10, then Insert > Image > Image over cells. In the dialog, click Browse inside the iframe and upload the VDP screenshot. Use Playwright's `waitForEvent('filechooser')` + `fileChooser.setFiles()` pattern.
- **Insert Leads screenshot:** Navigate to ~2 rows below the VDP image (e.g. B28), repeat the insert process with the Leads screenshot.
- Verify both images are visible and the data table (rows 1–9) is not covered.

### Step 3 — Google Sheet: Add new month row

- Open: `https://docs.google.com/spreadsheets/d/1E6CIiKbmFIWJdr3uWZHPkXMyQFtnDpAK6xdnJ58jz1Q/edit?gid=247007646#gid=247007646`
- Tab: **VPM Performance**
- Find the next empty row after the last month of data (above the Averages row)
- Insert the new month's data:

| Column | Field | Source |
|--------|-------|--------|
| B | Month name (e.g. "March") | Reporting month |
| C | # NON VPM Imp | Total Cars.com VDPs − VPM VDPs |
| D | VPM Imp | VPM VDPs (from Step 1) |
| E | Total Impr | Total Cars.com VDPs (from Step 1) |
| F | NON VPM Leads | Total Cars.com Leads − VPM Total Leads |
| G | # VPM Leads | VPM Total Leads (from Step 2) |
| H | # Total Leads | Total Cars.com Leads (from Step 2) |
| I | % VPM of total Imp | = D / E (format as %) |
| J | VPM Incremental Imp Lift | Carry forward the formula pattern from the row above |
| K | VPM Incremental Leads Lift | Carry forward the formula pattern from the row above |

- **Move the Averages row** (row 8 currently) down one row so it stays below all data
- Update the Averages formulas if needed to include the new row in their range

### Step 4 — QC

- Verify the new row values match what was pulled from Tableau
- Confirm columns I, J, K formulas are calculating correctly
- Spot-check: compare to prior month — flag any major swings (>50% change) for awareness
- Confirm the chart below the table updated to include the new month

---

## Scheduling

- **Meeting:** "Cars Commerce/eCarOne" — recurring **second Wednesday of each month**, 1:00 PM ET
- **Run this report:** The Monday before the meeting (i.e., the Monday of that same week)
  - May: run Mon May 11 → meeting Wed May 13
  - June: run Mon Jun 8 → meeting Wed Jun 10
  - July: run Mon Jul 7 → meeting Wed Jul 8

---

## Defaults

- **Account:** eCarOne (CCID: 6000362)
- **Tableau workbook:** VPM Premium+ Reporting (Cars Mktg Customer Analytics project)
  - VDP tab: `https://us-west-2b.online.tableau.com/#/site/cars/views/UATVPMPremiumReporting_17556278088300/VPMPremiumVDP`
  - Leads tab: `https://us-west-2b.online.tableau.com/#/site/cars/views/UATVPMPremiumReporting_17556278088300/VPMPremiumLeads`
- **Google Sheet:** `https://docs.google.com/spreadsheets/d/1E6CIiKbmFIWJdr3uWZHPkXMyQFtnDpAK6xdnJ58jz1Q/edit?gid=247007646#gid=247007646`
- **Schedule:** Monthly
- **Delivery:** Digital meeting prep (no email draft needed)
