---
name: ACA Monthly Reporting
description: Atlantic Coast Automotive (CCID 6051462) — monthly store reporting workflow, ~72 stores, Tableau + admin.cars.com → Google Sheet, email to Danielle McJunkins
type: project
originSessionId: ecade04a-2571-4aff-8a65-e5301a4a464c
---
Atlantic Coast Automotive, Inc. (CCID: 6051462) monthly store reporting.

- **~72 franchise stores** across FL, VA, WV, NY
- **Google Sheet:** ACA | CARS.COM - Store Reporting (ID: 1QFjG0ogyPz699uZbIMaAFV1PbSH26Ci2c8FiYuEjg9s)
- **Report folder:** ~/Documents/Reports/ACA/
- **Recipient:** Danielle McJunkins (dmcjunkins@cars.com) — internal review before forwarding to ACA store managers
- **Schedule:** Monthly on a Wednesday, manually triggered via `/aca-monthly-report`
- **Data sources:**
  - Tableau "Table for Export - Dealer" from workbook 1792343 (54 cols, CP/PP/Delta — inventory counts, VDPs, contacts, rating)
  - Tableau "Review Data Detail" (13 cols — per-store reputation metrics, point-in-time snapshot with duplicate rows)
  - CSVs export as UTF-16LE, must convert to UTF-8 before processing
- **Sheet API:** gspread with token at `~/.claude/tokens/sheets_credentials.json`
- **Skill:** `/aca-monthly-report`

**SRP/VDP conversion source (resolved 2026-04-10):** Use admin.cars.com Market Opportunities → Store tab → filter Stock Type (Used/New separately) → Download Crosstab CSV. This is the canonical source — the Tableau SRP Detail view (45-col) undercounts SRPs by ~25% and the old 79-col Market Summary is slightly different. Group UUID: b5bfa8c4-9e2e-454e-a56a-5a1057a58f58. URL: `/dealer_groups/{uuid}/reports/market_opportunities`. Requires Playwright for filter interaction (date range, stock type) and crosstab download. CSVs are UTF-16LE, need iconv conversion.

**% with Pic / Seller's Notes:** Still sourced from admin.cars.com Performance Trends (overall, not split by Used/New for Pic) and Listings Optimizer (for Notes split). These are approximate for older months.

**Why:** New dealer group added to Jake's reporting book of business as of 2026-04-08.

**How to apply:** Use the `/aca-monthly-report` skill for monthly updates. Sheet has colored presentation tabs (Monthly Overview, monthly detail) and raw data import tabs per month. First run completed March 2026 — inventory + reputation data populated, merchandising columns pending.
