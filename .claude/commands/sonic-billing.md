# Sonic & Hendrick Billing Report — Monthly Workflow

Process the monthly billing files from Ewa Sarat into pivot-table summaries and draft the email to Sharon Cunane.

---

## Overview

Each month, Ewa Sarat (esarat@carscommerce.inc) sends an email with subject **"Sonic & Hendrick Billing Files | {Month} {Year}"** containing two Excel attachments:
1. `Sonic Billing Files-{Month} {Year}.xlsx`
2. `Hendrick Automotive Billing File-{Month} {Year}.xlsx`

The goal is to create a pivot table summary for each file, save as Excel to their respective folders, and draft a reply email to Sharon Cunane. Sonic and Hendrick are **separate reports** with **separate output directories**.

---

## Steps

### Step 1 — Find and Download the Email

- Search Gmail for the most recent email from `esarat@carscommerce.inc` with subject containing "Sonic & Hendrick Billing Files"
- Download both Excel attachments to `~/Downloads/`
- Note the billing month/year from the subject line

### Step 2 — Process Each Billing File

For **each** attachment (Sonic and Hendrick), do the following using Python + openpyxl:

1. **Read all data sheets** — each file has multiple tabs (e.g., Cars.com, AccuTrade, eCarOne for Sonic). Every tab shares the same 53-column schema with headers in row 1:
   - Key columns: `Ship To Cust Name` (col Y), `Ship To MAX ID` (col Z), `Product Description` (col I), `Net Amount` (col S)
   - **EXCLUDE the AccuTrade tab** — do not include AccuTrade data in the pivot table or QC analysis

2. **Combine all tabs (except AccuTrade)** into a single DataFrame (or list), keeping all rows from every included sheet.

3. **Create pivot table** on an "Overview" sheet with:
   - **Row fields (in order):**
     1. Ship To Cust Name (sorted A→Z)
     2. Ship To MAX ID
     3. Product Description (sorted A→Z)
   - **Values:** SUM of Net Amount (formatted as currency `$#,##0.00`)
   - Include subtotals per dealer (Ship To Cust Name level)
   - Include a grand total row at the bottom

4. **Keep the original data sheets** intact but **hide them** — after adding the Overview, set `ws.sheet_state = 'hidden'` on every non-Overview sheet so only the pivot is visible when the file is opened.

5. **Format the Overview sheet:**
   - Bold header row
   - Currency format on the Net Amount column
   - Auto-fit column widths
   - Freeze the header row(s)

6. **Save** the processed files to their respective directories:
   - Sonic: `~/Documents/Reports/Sonic Automotive Group/Sonic Billing Files-{Month} {Year}.xlsx`
   - Hendrick: `~/Documents/Reports/Hendrick Automotive Group/Hendrick Automotive Billing File-{Month} {Year}.xlsx`

### Step 3 — QC: Month-over-Month Comparison (Optional but Recommended)

- When reading a previous month's file for comparison, **exclude the Overview sheet** (it contains subtotal rows that corrupt the dealer list). Only read from raw data sheets (Cars.com, eCarOne, etc.).
- If a previous month's processed file exists in `~/Documents/Reports/`, compare:
  - Any dealers that are **new** this month (not in last month)
  - Any dealers that **dropped off** (in last month but not this month)
  - Any products that changed for a dealer
  - Significant Net Amount changes (>20% swing)
- Summarize findings briefly — flag canceled accounts or newly invoiced dealers

### Step 4 — Draft Email to Sharon Cunane

- **To:** Sharon Cunane (scunane@cars.com)
- **Subject:** Re: Sonic Billing Files | {Month} {Year}  (Sonic only — do not include "Hendrick" in subject)
- **Body:** Keep it minimal — "Attached."
  - If QC found notable changes (new/canceled dealers, significant amount changes), include a brief note
- **Attach** only the Sonic processed Excel file
- **No CC** — Sharon is the sole recipient
- Draft via Gmail (do not send — just create draft)

---

## Key Reference

- **Source email sender:** Ewa Sarat (esarat@carscommerce.inc)
- **Recipient:** Sharon Cunane (scunane@cars.com)
- **Output locations:**
  - Sonic: `~/Documents/Reports/Sonic Automotive Group/`
  - Hendrick: `~/Documents/Reports/Hendrick Automotive Group/`
- **Pivot structure:** Ship To Cust Name → Ship To MAX ID → Product Description, with SUM of Net Amount
- **Exclude AccuTrade tab** — only include Cars.com, eCarOne, and any other non-AccuTrade tabs
- **Email only includes Sonic attachment** — Hendrick is processed separately but not emailed to Sharon (not currently requested)
