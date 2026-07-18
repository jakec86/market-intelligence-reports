# Herb Chambers — Quarterly DealerRater Employee Profile Update

Run the quarterly Herb Chambers DealerRater employee profile audit. Cross-references dealer website team pages with DealerRater employee listings to identify adds, removes, and title updates.

---

## Overview

Herb Chambers has ~24 active stores on Cars.com and/or DealerRater. Each quarter, employee profiles on DealerRater need to be updated to match the current staff listed on each store's website team page. This skill automates the data collection and comparison, producing an actionable report.

**Report folder:** `~/Documents/Reports/HerbChambers/`

**Store lookup:** `~/Documents/Reports/HerbChambers/herb_chambers_store_lookup.json`
- 27 DealerRater entries across 24 SF accounts (some stores have multiple DR listings)
- Contains CCIDs, DealerRater IDs, employee page URLs, website URLs, products

---

## Data Sources

### 1. DealerRater Employee Pages (public, no auth)
- URL pattern: `https://www.dealerrater.com/sales/{Store-Name}-Employees-{DR_ID}/`
- Scrape via WebFetch — returns structured employee name/title/department
- ~27 pages to scrape (batch in parallel via agents)

### 2. Dealer Website Team Pages (Cloudflare-protected)
- URL pattern: `https://www.{store-domain}/dealership/staff.htm`
- **Requires Playwright** (headed mode to bypass Cloudflare bot detection, also `ignore_https_errors=True` for some stores)
- Staff names are in `<h3>` elements, titles in adjacent `<p>` tags within parent container
- Script: `~/Documents/Reports/HerbChambers/scrape_website_staff.py`
- **17 of 27 DR listings** have working `/dealership/staff.htm` pages
- Stores without staff pages (check each quarter for changes):
  - Alfa Romeo Boston: Redirects to herbchambers.com group site
  - INFINITI of Westborough: Store sold/closed — no DR ID in SF
  - Porsche: Website returns HTTP 400 on staff page (different CMS)
  - Volvo Cars Norwood: Only GM listed on staff page (volvocarsnorwood.com)
  - Lamborghini/Bentley/Rolls-Royce: Redirect to herbchambers.com group site
  - Lincoln of Westborough: DR page loads via JS only

**URL corrections discovered (2026-04-08):**
- Cadillac of Lynnfield: SF has `herbchamberscadillaclynnfield.com` — actual URL is `herbchamberscadillac**of**lynnfield.com`
- Volvo: SF has `volvoofnorwood.com` — actual URL is `volvocarsnorwood.com`
- Lexus of Hingham: Needs `ignore_https_errors=True` and 30s timeout (slow render)
- Lexus of Sharon: Needs `domcontentloaded` wait (networkidle times out)

### 3. Salesforce (subscription + DR ID verification)
- Query `SBQQ__Subscription__c` for `SBQQ__Account__r.Name LIKE '%Herb Chambers%' AND SBQQ__TerminatedDate__c = null`
- Products: DealerRater Connections (20 stores), Franchise Premium Listings (7 stores)
- **SF field `DealerRater_ID__c`** on Account stores the DR IDs (comma-separated for multi-listing stores)
- **SF field `Cars_com_Dealer_Profile_Page_URL__c`** has Cars.com profile links
- **DealerRater Success Partner:** Kyle Panfil (as of 2026-04-08)
- Porsche has 2 DR IDs: 6477, 15386; Luxury group (CCID 159284) has 4: 25309, 28828, 43580, 113874

---

## Steps

### Step 1 — Verify Active Stores
Query Salesforce SBQQ subscriptions to confirm the active store list hasn't changed. Compare against `herb_chambers_store_lookup.json`. Add any new stores, remove any that lost DealerRater products.

### Step 2 — Scrape DealerRater Employee Pages
Batch-fetch all 27 DealerRater employee page URLs from the lookup file. Use WebFetch or parallel agents. Save results to `dr_employee_rosters.json`.

**Known issues:**
- INFINITI of Westborough (DR 27165): Employee page redirects to homepage (deactivated)
- Lincoln of Westborough (DR 40707): Employee data loads via JavaScript (needs Playwright)

### Step 3 — Scrape Dealer Website Staff Pages
Run the Playwright scraper:
```bash
cd ~/Documents/Reports/HerbChambers && python3 scrape_website_staff.py
```
- Launches headed Chromium (required for Cloudflare bypass)
- Extracts staff from `<h3>` elements on `/dealership/staff.htm`
- Saves to `website_staff_rosters.json`
- ~24 stores, ~3-5 min total runtime

### Step 4 — Generate Comparison Report
Cross-reference the two rosters using last-name fuzzy matching:
- **TO ADD:** On website but not on DealerRater → new employee, needs DR profile created
- **TO REMOVE:** On DealerRater but not on website → likely departed, remove from DR
- **TITLE UPDATES:** Same person, different title → update title on DR

Filter out navigation elements (e.g., "Finance Center", "Our Inventory", "Service & Parts", "Dealership Hours").

Save actionable report to `staff_update_report.json`.

### Step 5 — Manual Updates on DealerRater
DealerRater admin requires METAL SSO login at `dealerrater.com/login`. Updates are manual:
1. Log in to DealerRater admin
2. Navigate to each store's employee management page
3. Add new employees, remove departed ones, update titles
4. Cross-reference the report store by store

---

## Store Inventory (as of 2026-04-08)

| Store | CCID | DR ID | Products |
|---|---|---|---|
| Alfa Romeo of Boston | 5373020 | 113874 | DR Connections |
| BMW of Boston | 3111 | 2 | Franchise Premium |
| MINI of Boston | 3111 | 17990 | Franchise Premium |
| Cadillac of Lynnfield | 5243150 | 31478 | DR Connections |
| Cadillac/AR/Maserati of Warwick | 81741 | 6471 | Franchise Premium |
| Chevrolet of Danvers | 156476 | 23077 | DR Connections |
| CDJR FIAT of Danvers | 99392 | 23090 | DR Connections |
| CDJR FIAT of Millbury | 3123 | 6472 | DR Connections |
| Ford of Braintree | 81773 | 6473 | DR Connections |
| Ford of Westborough | 3138 | 16793 | DR Connections |
| Honda in Boston | 3349 | 163 | DR Connections |
| Honda of Burlington | 3204 | 18404 | DR Connections |
| Honda of Seekonk | 3544 | 18799 | Franchise Premium |
| Hyundai of Auburn | 3112 | 6474 | DR Connections |
| INFINITI of Westborough | 194702 | 27165 | DR Connections + Website Pkg |
| Kia of Burlington | 198442 | 29628 | DR Connections |
| Lexus of Hingham | 5243175 | 43936 | DR Connections |
| Lexus of Sharon | 3304 | 17780 | DR Connections |
| Lincoln of Norwood | 5354177 | 105096 | DR Connections |
| Lincoln of Westborough | 6062473 | 40707 | DR Connections |
| Porsche | 178854 | 15386 | Franchise Premium |
| Toyota of Auburn | 99374 | 6478 | DR Connections |
| Toyota of Boston | 99373 | 6479 | DR Connections + Franchise Premium |
| Volvo Cars Norwood | 3299 | 18619 | DR Connections |
| Lamborghini Boston | 159284 | 25309 | Franchise Premium |
| Bentley Boston | 159284 | 28828 | Franchise Premium |
| Rolls-Royce NE | 159284 | 28830 | Franchise Premium |

---

## Known Patterns

- **CCID 159284 (Luxury group):** Lamborghini (25309), Bentley (28828), Rolls-Royce (28830) only. **Maserati and Alfa Romeo of Boston are no longer part of this group** (confirmed 2026-04-08). SF `DealerRater_ID__c` still shows 43580 (Maserati) and 113874 (AR Boston) but those are stale. Maserati (Sold) is at CCID 6057985. AR Boston has its own account at CCID 5373020.
- **Luxury stores share staff:** Lamborghini, Bentley, and Rolls-Royce share Brad Taylor (GM), Dominic Warrell, Vadzim Kelly, Christine Scott, Joe Swisher, Raymond Guarino, Steve LaFond. Cross-reference these 3 DR listings against each other (no website staff page exists).
- **Alfa Romeo Boston (CCID 5373020):** Has DR Connections but website redirects to herbchambers.com group site — no individual staff page. DR-only for now.
- **Courtney Blasco** appears at multiple stores (regional BDM role)
- **BMW/MINI of Boston** share some staff (co-located, single SF account CCID 3111)
- **Cadillac of Warwick** DR listing includes Alfa Romeo and Maserati of Warwick (DR 6471)
- **Cadillac of Lynnfield** correct website URL is `herbchamberscadillac**of**lynnfield.com` (SF has it wrong, missing "of")
- **Volvo Cars Norwood** actual URL is `volvocarsnorwood.com` (SF has `volvoofnorwood.com`); only GM listed on staff page
- Honda of Seekonk has a minimal website staff page (only GM visible) but extensive DR roster — website may be incomplete
- Ford of Westborough staff page shows only GM — DR roster is likely more accurate
- **Porsche (CCID 178854)** has 2 DR IDs in SF: 6477 and 15386. Website returns HTTP 400 on staff page.

---

## Key Reference

- **Dealer Group:** Herb Chambers Companies
- **~24 active stores** in MA and RI
- **Report folder:** `~/Documents/Reports/HerbChambers/`
- **DealerRater admin:** `dealerrater.com/login` (METAL SSO)
- **Schedule:** Quarterly, manually triggered
- **Playwright required** for website scraping (Cloudflare protection)
