---
name: park-place-prospect
description: "Park Place Dealerships (Asbury sub-group) — DFW winback prospect: 4 stores (3 MB + 1 LR), Polk data, historical Cars.com performance, pitch deck status, AEs"
metadata: 
  node_type: memory
  type: project
  originSessionId: 4e772751-adab-48c4-89ac-18a85a248a72
---

## Account Overview
- **Group:** Park Place Dealerships (Asbury Automotive Group sub-group)
- **Market:** Dallas-Ft. Worth, TX
- **Status:** All 4 stores currently dark on Cars.com
- **AEs:** Eileen Day (3 MB stores) · Stephanie Wilson (Land Rover DFW)
- **Cancelled:** Oct 2024 · FPL contracts expired Jul–Aug 2025
- **Winback cohort:** Sept 2024

## The Four Stores

| Store | CCID | UUID | Status | CarGurus |
|---|---|---|---|---|
| Park Place Motorcars Dallas MB | 5394925 | 4a1f6a04-14e4-588c-af29-5d4c835356fb | Cancelled | Paid Listing (162 used) |
| Park Place Motorcars Fort Worth MB | 5394926 | a54ef1e2-062e-5d72-a5fd-af0644f6528b | Cancelled | Paid Listing (97 used) |
| Park Place Motorcars Arlington MB | 5394924 | 5eb983df-194c-563f-9a1d-d8fe1ba69cc5 | Cancelled | Paid Listing (56 used) |
| Land Rover DFW | 6063490 | 8bef12d4-0a3b-4a61-8929-7397b37380fb | Prospecting | Not listing |

## Polk/DMV Market Position (Feb 2026)
**Mercedes-Benz — DFW (2,380 total registrations/mo):**
- Park Place Dallas: #2 · 319 units · 13.4% share
- Park Place Arlington: #6 · 57 units · 2.4%
- Park Place Fort Worth: #36 · 8 units · 0.3%
- Combined: 384 units · 16.1% DFW MB share
- Primary Cars.com competitor: Mercedes-Benz of Plano (CCID 21711) — **Active** — 394 units, 16.6%

**Land Rover — DFW (833 total registrations/mo):**
- Land Rover DFW: **#1** · 123 units · 14.8% share
- Land Rover Dallas (CCID 6035401): **Active** on Cars.com · #3 · 117 units
- Land Rover Frisco (CCID 6035409): **Active** on Cars.com · #4 · 86 units

## Historical Cars.com Performance (May 2025 — FPL contract period)

| Store | Inventory | VDPs/Mo | Connections/Mo | Badge Rate |
|---|---|---|---|---|
| Dallas MB | 129 | 2,078 | 24 | 36% |
| Fort Worth MB | 57 | 1,897 | 18 | 16% |
| Arlington MB | 44 | 1,223 | 8 | 20% |
| Land Rover DFW | — | — | — | Never activated feed |

**Combined MB: 50 connections/mo · 5,198 VDPs/mo · 24% avg badge rate**
**LR DFW: Paid for FPL through Aug 2025 but never activated inventory feed**

**Connection-mix (resolved 2026-06-15):** admin.cars "connections" = ALL digital engagement events except Maps — VDP Deep Links (clicks), Website Transfers, Phone/Email/Chat leads, Instant-Offer/trade. Confirmed by reconciling MB Plano's connection-detail export (`~/Documents/Tableau/MB of Plano exportdetails.csv`, Mar–May 2026): all-excl-Maps = 552/mo ≈ the 531/mo benchmark leg used in the projection.
- **Lead share = 0.23 validated two independent ways:** Park Place's own paid-active window (May–Sep 2025) = 0.23, AND active comparable MB Plano = 0.217. Strong.
- **Earlier walk-in worry is NOT a problem for the projection.** Park Place's OWN thin history was ~75–85% walk-ins (walk-ins persist even when dark — 31 in May 2026 w/ 0 digital leads), but the projection's 222 conn/mo is benchmarked off MB Plano + DFW market, which are **digital and walk-in-free** → legitimately incremental.
- **Real nuance for the pitch:** ~60% of "connections" (both MB Plano's and the projection's) are **VDP Deep-Link clicks**, not direct contacts. So 222 ≠ 222 people reaching out. **Leads (51/mo full, phone+email+chat) is the honest "actual contacts" headline** — lead on that, use connections as the broader engagement number.

## DFW In-Market Audience (June 2026 Demand Signals)
- **Mercedes-Benz DFW on Cars.com:** 4,476 inventory · 26,441 VDPs/mo · 589 connections/mo
- **Land Rover DFW Demand Signals:** Blank — LR DFW has no active inventory feed so report shows no data

## Current Used Inventory (scraped 2026-06-12, dealer-site group feed)
- All PP sites serve ONE pooled group feed (~827 incl. Lexus/Acura/Volvo/JLR); attribute by `account`, scrape any one site. Akamai-protected → chrome-devtools real Chrome only. See [[reference_dealer_site_scrape]].
- **3 MB stores: 313 used** — Dallas 155, Fort Worth 104, Arlington 54. 72% Mercedes (226), 28% mixed trade-ins. Coverage: price 100% / mileage 99% / trim 83%.
- Artifacts: `~/Documents/Reports/ParkPlace/inventory/parkplace_MB_stores_2026-06-12.json` (313) + `parkplace_group_pool_2026-06-12.json` (827).
- **"Would-perform-on-Cars.com" projection tool** (scrape → admin.cars Demand Signals quadrant/"churners" → blended benchmark vs MB of Plano + PP 2025 history + DFW market → projected VDPs/connections/$): plan at `~/.claude/plans/for-the-mb-stores-happy-hearth.md`. cars-mcp gives market supply + identifies MB of Plano by dealer_name (no auth); demand axis + Plano rates still need admin.cars (SSO).

## Polk Competitive Trend (24-month, internal use only)
- Jan–Sep 2024 (FPL active): PP Dallas avg 290/mo · MB Plano avg 149/mo (+141 lead)
- Sep 2025–Jan 2026 (no FPL): PP Dallas avg 355/mo · MB Plano avg 254/mo (+101 lead)
- Feb 2026: PP Dallas 319 · MB Plano 394 (Plano ahead for first time on record)
- **These stores trade positions month to month — do NOT lead with competitor comparison externally**
- MB Plano anomalous near-zero units Oct 2024–Mar 2025 (likely name change) — exclude from averages
- **External pitch angle: proven in-market audience, not competitive decline**

## Pitch Materials
- **LIVE (GitHub Pages):** projection report → `https://jakec86.github.io/market-intelligence-reports/ParkPlace/parkplace_inventory_projection_2026-06-12.html` · slide → `.../parkplace_inventory_projection_SLIDE_2026-06-12.html`. Published from the **`~/Documents/Reports` git repo** (remote `jakec86/market-intelligence-reports`, GH Pages = main@root). Gotcha: local `main` can sit behind remote and `ParkPlace/` can show untracked locally; deploy surgically via the gh git data API (blobs→tree→commit→PATCH ref) to update just the two files without disturbing the working tree or others' untracked files (e.g. DonFranklin). Only the 2 projection HTMLs are tracked/published — the pitch deck (`park_place_pitch_v2.html`) is NOT, so don't link to it from the live report (404). See [[market-intelligence-workflow]].
- **Combined pitch deck (internal + external sections):** `~/Documents/Reports/ParkPlace/park_place_pitch_v2.html`
- **Internal-only brief:** `~/Documents/Reports/ParkPlace/park_place_internal.html`
- **External/client-facing:** `~/Documents/Reports/ParkPlace/park_place_external.html`
- **Shareable Google Drive file (pending permission set):** `https://drive.google.com/file/d/1RDWrqMOGtXJQDYeLMvVuXZq2K_Wgfn6W/view?usp=sharing`
- **PDF:** `~/Documents/Reports/ParkPlace/park_place_pitch.pdf`

## Pitch Strategy
**Why:** LR DFW is the cleanest opener — #1 in DFW, never activated on Cars.com, not on CarGurus, no history to relitigate. MB stores have proven Cars.com performance history (50 conns, 5,198 VDPs). Lead with audience, not competitor comparison.
**CarGurus objection:** All 3 MB stores are active on CarGurus paid listings. Acknowledge it — pivot to audience differentiation (Cars.com reaches earlier-funnel, distinct used-car intent segment).
**Group vs. store:** Park Place is Asbury sub-group. Consider whether store-level buy-in is sufficient or if Asbury-level conversation is needed.

## Data Sources Used
- Polk/DMV: DFW DMA, Feb 2026 snapshot + 24-month Comparative Sales Trend (admin.cars.com)
- Performance Trends: admin.cars.com, May 2025
- Demand Signals: admin.cars.com, June 2026 (MB-specific)
- CarGurus status: Prospect View CSV export (Jun 2026)
- Salesforce subscription history: FPL confirmed expired Jul–Aug 2025
