---
name: Sonic Monthly Brand Performance Report
description: Monthly brand-segmented reporting for Sonic Automotive Group (~101 stores, 18 brands) — rotating luxury/volume focus, per-brand emails to Sonic managers, CC Sharon Cunane
type: project
originSessionId: e5887f6e-ee90-42c2-9282-6053f498c62f
---
# Sonic Monthly Brand Performance Report

**Skill:** `/sonic-monthly-report`
**Parent Group CCID:** 538486
**Active Stores:** ~101 (excluding Tactical Fleet Charlotte 6001077, Tactical Fleet Dallas 5383761, eCarOne)
**Primary Contact:** Sharon Cunane (scunane@cars.com)
**Report Folder:** ~/Documents/Reports/SonicAutomotive/
**Google Sheet:** TBD — create on first run

## Rotation Schedule

- **Luxury (odd months):** BMW (16), Audi (6), Mercedes-Benz (6), Land Rover (10), Porsche (5), Jaguar (2) = 45 stores
- **Volume (even months):** Honda (12), Toyota (8), Ford (6), Chevrolet (3), Cadillac (4), Lexus (5), Hyundai (3), VW (4), MINI (2), Volvo (2), Subaru (1), Nissan (1), CDJR (1) = 52 stores

## Delivery Model

Per-brand emails to Sonic brand managers, CC Sharon. Brand manager contacts TBD — until identified, draft emails go to Sharon only.

## Known Porsche UUIDs (admin.cars.com)

- Porsche Bethesda: 58980917-f29d-5b36-97b9-23c901b28942
- Porsche Birmingham: 71172a89-0310-5446-ae95-1a8f2d857b84
- Porsche of Nashville: 1e521c7c-b5b4-5202-9899-94a7d438a8ab
- Porsche River Oaks: 1da18bfa-c58a-52e5-b42e-cda3d2b816f8
- Porsche West Houston: a9aefa07-0f2a-5c98-9642-eff42d286a75

## Unmatched Stores (need brand assignment)

- Autobahn Motors (84916) — likely Mercedes-Benz, Belmont CA
- Dave Smith Coeur d'Alene (190771) — multi-franchise
- Vernon Auto Group (194763) — multi-franchise
- W.I. Simonson Inc. (24293) — likely Mercedes-Benz, Santa Monica CA

## Tableau API Access (confirmed 2026-04-14)

**Dealer Health Metrics** view ID: `a0b9bdce-2db3-4ea0-a2fc-365fd08c5786`
- Filter: `vf_Maj Cust Name=Sonic` → 120 stores, 5,808 rows, 48 metrics (CP/PP/Delta)
- API call: `GET /sites/{site_id}/views/{view_id}/data?vf_Maj%20Cust%20Name=Sonic` (no Accept header)
- PAT: "Claude", expires ~April 2027

**AE Insights Dashboard** view ID: `a60dbfc3-0156-4728-884a-fec77a3b7d2c`
- No RLS — returns all 75,933 dealers in universe
- Sonic: 160 CCIDs, AE: blank, Channel: Majors

**Searches by Zip Code** view ID: `39464986-86f3-49a2-af82-37f1486743ff`
- No RLS — 490,645 rows, all DMAs

## Design Notes

- **Why:** Jake asked on 2026-04-13 to build this skill. Goal is consultative, brand-level reporting that positions Sonic stores for success — not a data dump.
- **How to apply:** The EP Mkt Comp demand-indexing pattern (market VDPs/inventory → demand score) is the analytical template for the high-level view. Auto-research deep dives on flagged stores provide the convergent layer.
- **Two layers:** Divergent (brand vs market scorecard) + Convergent (store-level auto-research on top 3-5 flagged stores per brand)
