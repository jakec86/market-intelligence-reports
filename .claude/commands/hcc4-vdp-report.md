# HCC4 VDP Report — Monthly Workflow

Run the monthly Herb Chambers / C-4 Analytics VDP report. Scheduled: **1st of every month** (as soon as the prior month ends).

---

## Email Drafting Rule

Each draft must feel fresh but follow a consistent strategy:
- **Vary:** opening line, brief acknowledgment phrasing
- **Keep consistent:** professional-casual tone, extremely concise (2-3 sentences max), close with "Cheers, Jake"
- **Never:** use the same opening line twice in a row, include lengthy analysis — this is a delivery email, not a summary
- **Attachment:** Excel file attached (no Google Sheet link in body) — reference it as "the attached report"

Example openings (rotate and riff on these):
- "Brian, March reporting is attached..."
- "Here's the latest Cars.com reporting for Herb Chambers..."
- "Monthly report is ready — see attached..."
- "Dropping in the March numbers for Herb Chambers..."

---

## Steps

### Step 0 — Check for master Excel in Gmail

Before pulling from admin.cars.com, check Gmail for a recent email from Brian Cunningham (brian.cunningham@c-4analytics.com) with an Excel attachment (subject pattern: `Cars.com [Month] Reporting`). The master Excel is more accurate than the ROI One Sheeter — if it exists for the reporting month, use it as the data source and skip Step 1.

### Step 1 — admin.cars.com: ROI One Sheeter (if no master Excel)

- Navigate to `https://admin.cars.com/dealers/{UUID}/reports/roi_one_sheeter` for each dealer (use Chrome DevTools MCP — already authenticated)
- Click the **Export** link (top right) to download a UTF-16 TSV named `exportdetails - [timestamp].csv`
- Extract the **[MM-YY]** column (prior month) for each dealer:
  - **Unique VINs - Used** = `Used Net Vehicles` row
  - **Unique VINs - New** = `New Net Vehicles` row
  - **Total VDP Imps** = `VDP Impressions - New` + `VDP Impressions - Used`
- Dealer UUIDs (14 total):
  1. Audi Brookline → `1d1f2246-8358-5db6-b7ee-bee665b0568c`
  2. Audi Burlington → `f0b7f24e-1e03-5968-8090-61894225841f`
  3. Bentley Boston → `3a25f8ca-f402-4398-bc05-091691bc7a5a`
  4. BMW Certified Pre-Owned Medford, A Herb Chambers Company → `5abef716-f7d8-46cf-9660-1b455a91dc19`
  5. Herb Chambers BMW MINI of Boston → `3c100b29-91c1-567a-b2b3-51695ac7d6ae`
  6. Herb Chambers Cadillac and Herb Chambers Maserati of Warwick → `5fca5142-8e1b-59ed-9614-5e66477811a8`
  7. Herb Chambers Exotics → `d3d81440-779e-5637-9fe8-bcb026b9051f`
  8. Herb Chambers Honda of Seekonk → `e2f29d16-c231-5aa5-87cd-5be7bf2ea8af`
  9. Herb Chambers Porsche → `e445f33b-fa6b-5246-b23e-dcf8ca1d0d97`
  10. Herb Chambers Toyota of Boston → `2d1e516d-faee-5f9a-a21f-af4b18cee5d0`
  11. Herb Chambers Volvo Cars Norwood → `42becf6f-58bc-531c-ac9d-700b439c7100`
  12. Jaguar Land Rover Boston → `94629331-a310-558d-84d0-2ac5b4e2405d`
  13. Mercedes-Benz of Sudbury → `449d362d-6754-522e-b3f1-72d8c9621d7e`
  14. Porsche Burlington → `8a72078b-2984-5074-98d2-9f4ca39fa553`
- Pull the following metrics for **each dealer** under the Herb Chambers group for the **previous month**:
  - Unique VINs - Used
  - Unique VINs - New
  - Total VDP Impressions
- Dealers (14 total):
  1. Audi Brookline
  2. Audi Burlington
  3. Bentley Boston
  4. BMW Certified Pre-Owned Medford, A Herb Chambers Company
  5. Herb Chambers BMW MINI of Boston
  6. Herb Chambers Cadillac and Herb Chambers Maserati of Warwick
  7. Herb Chambers Exotics
  8. Herb Chambers Honda of Seekonk
  9. Herb Chambers Porsche
  10. Herb Chambers Toyota of Boston
  11. Herb Chambers Volvo Cars Norwood
  12. Jaguar Land Rover Boston
  13. Mercedes-Benz of Sudbury
  14. Porsche Burlington

### Step 2 — Google Sheet: Create new month tab & populate

- Open the Google Sheet: `https://docs.google.com/spreadsheets/d/1qDLt1Y824RNSq4NCeOjSrrM1C3hbZv6QJCUztM4yVRI/edit`
- **Duplicate** the most recent month's tab (e.g. Feb) and rename it to the current reporting month (e.g. Mar)
- Update the data in the new tab with the metrics pulled from Step 1:
  - Column A: Customer Name (should already be populated from the duplicate)
  - Column B: Unique VINs - Used
  - Column C: Unique VINs - New
  - Column D: Total VDP Imps
- Verify all 14 dealers have updated values
- Keep the same formatting (bold headers in row 1, same column widths)

### Step 3 — QC (after Step 1 or master Excel)

- Confirm all 14 dealers have data in the new month's tab
- Spot-check: no zeros where there shouldn't be, no missing dealers
- Flag any anomalies (e.g. significant drops or spikes vs. prior month)

### Step 4 — Export as Excel

- Download the Google Sheet as Excel (`.xlsx`) via: `https://docs.google.com/spreadsheets/d/1qDLt1Y824RNSq4NCeOjSrrM1C3hbZv6QJCUztM4yVRI/export?format=xlsx`
- Save to `~/Downloads/`

### Step 5 — Draft Email (do NOT send — draft only)

Use Playwright to compose a Gmail draft:

1. **Search Gmail** for `subject:Cars.com Reporting to:brian.cunningham@c-4analytics.com` and open the most recent thread
2. **Reply all** -> click the reply type dropdown -> **Edit subject** -> update the month (e.g. "Re: Cars.com Feb Reporting" -> "Re: Cars.com Mar Reporting")
3. **Recipients:**
   - **To:** Brian Cunningham (brian.cunningham@c-4analytics.com)
   - **Cc:** Sharon Cunane (scunane@cars.com) — keep from existing thread
4. **Body** (vary wording per the Email Drafting Rule above):
```
[Brief varied opening acknowledging the attached report],

[Optional: one sentence noting anything notable only if a major anomaly was found in QC.]

Cheers,
Jake
```
5. **Attach** the downloaded Excel file from Step 4
6. **Save as draft** for review — never send directly

### Step 6 — Salesforce logging

The Gmail Salesforce extension auto-logs the email to **Herb Chambers Companies** with **Brian Cunningham** as the contact when sent. Ensure "Log on Send" and "Email Tracking" are toggled on in the extension panel before sending.

### Step 7 — Mark Google Task complete

Search Google Tasks for **"Herb Chambers: C-4 VDP Report"** and mark it complete.

---

## Defaults

- Account: Herb Chambers Companies (CCID: 6048251)
- Google Sheet: `https://docs.google.com/spreadsheets/d/1qDLt1Y824RNSq4NCeOjSrrM1C3hbZv6QJCUztM4yVRI/edit`
- Excel export: `https://docs.google.com/spreadsheets/d/1qDLt1Y824RNSq4NCeOjSrrM1C3hbZv6QJCUztM4yVRI/export?format=xlsx`
- Recipient: Brian Cunningham (brian.cunningham@c-4analytics.com)
- Cc: Sharon Cunane (scunane@cars.com)
- Schedule: 1st of every month (as soon as prior month ends)
- 14 Herb Chambers dealers (listed above with UUIDs in Step 1)
