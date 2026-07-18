---
name: project_aca_mae_proposal
description: "ACA Market Area Expansion (MAE) proposal — sheet, data sources, and wave-ranking methodology"
metadata: 
  node_type: memory
  type: project
  originSessionId: 36c675f4-0a55-4be7-b180-73d5817eb7f2
---

ACA "Market Area Expansion" proposal: ranks ACA stores being targeted by **CarGurus MAE** to prioritize a Cars.com counter-play into "strategy waves." Semi-manual (no script). Google Sheet **ACA MAE** = `1fffKRZV0mXNWtfc7k-HPLAmrDdfEe99wdbIkXiub6AI`.

**Data sources (3 layers):**
- **Performance / wave-ranking inputs** → admin.cars.com Market Opportunities for ACA dealer group UUID `b5bfa8c4-9e2e-454e-a56a-5a1057a58f58`, sheet **Store Performance → By Store** worksheet. Pull via [[reference_admin_cars_tableau_embed_extract]] (no PAT/SSO-CSV needed). 21 measures incl. Total Leads, VDPs Per VIN, Unique VINs.
- **Eligibility / competitive / economics** → Tableau **AE Insights Dashboard** "MKP View" sheet (manual UTF-16 crosstab export `~/Documents/Tableau/MKP View_data.csv`). Key field **`MAE wCar Gurus`=Yes** = CarGurus is running MAE against that store (the candidate pool). Also `paid cg subscription`, CPL, Total Inv, Cars MRR, Risk Group. Rows are exploded by Product Tower — dedupe by CCID.
- **VPM VDPs/Leads (display only, NOT a ranking input)** → VPM Premium+ workbook, manual exports `VDPs.csv` + `Leads.csv` (Store × month: Total / VPM / %).

**Wave methodology (validated reproduces Feb exactly):** within the MAE-wCarGurus=Yes pool (~28 stores), compute 3-month **average** of Total Leads, VDPs Per VIN, Unique VINs; rank each desc (1=best); **Combined Rank Score = sum of the 3 ranks** (lower=stronger); top 13 = Wave 1. Join all layers by **Legacy Id == CCID**.

**June 2026 (May refresh):** added tabs `MAE Targets May`, `VPM Only May`, `Eligibility May`, and the strategy tab (Jake renamed `CG Strategy May` → **`MAE Strategy May`**, gid 1017749518 — resolve by gid, not title). Preserved Feb baseline tabs. Window Mar–May 2026. Counter-play re-rank: Wave 1 stable, ONE swap — Southern Buick GMC Virginia Beach in (Feb#14→#4), Southern VW Greenbrier out.

**Two-segment wave structure (the map artifact uses THIS):** Wave 1 = CarGurus counter-play (MAE wCarGurus=Yes, top 7 by Combined Rank Score); Wave 2 = High Lead Volume / whitespace (top 7 non-MAE rooftops by avg leads, delivery locations excluded). 14 stores total. "Whitespace" = high-lead stores outside the CG counter-play (incl. "not on CG" and "on CG, no MAE"). MAE Strategy May tab also has an "Uncovered High-Volume" section + "Recommended Wave Map" block.

**Map artifact:** Leaflet HTML built by `/tmp/build_map.py` (run with arg `public` for the redacted build). Wave labels "CarGurus Geo" / "High Volume Lead"; marker fill = OEM segment (CDJR/VW/Ford/etc.), ring = wave (purple #6B2D8B / teal #00A88E); Portfolio Summary panel + OEM count table; city-level coords. **Published (redacted: MRR + Risk stripped from data & popups) to GitHub Pages: https://jakec86.github.io/aca-mae-map/ (repo jakec86/aca-mae-map, index.html).** Sheet "Map" tab B2 now HYPERLINKs there. Full (unredacted) local copy: `~/Documents/Reports/ACA_MAE/aca_mae_wave_map_may2026.html` — keep internal only.

Danielle McJunkins is the ACA account AE (internal colleague, not the client); she requested the May refresh + "did any recommended stores change." Answer given: one counter-play swap (Southern Buick GMC VA Beach in, Southern VW Greenbrier out) + new High-Volume-Lead Wave 2. NOTE: Slack MCP is decommissioned ([[project_slack_mcp_decommissioned]]) — Slack messages are drafted for manual paste, not sent. See [[project_aca_reporting]].
