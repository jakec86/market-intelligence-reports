---
name: SRP/VDP Source Must Be Market Opportunities
description: SRP/VDP conversion data must come from admin.cars.com Market Opportunities (Store tab), not the Tableau SRP Detail view — different SRP impression counts cause ~25% discrepancy
type: feedback
originSessionId: ecade04a-2571-4aff-8a65-e5301a4a464c
---
Always use admin.cars.com Market Opportunities → Store tab → filter by Stock Type (Used/New separately) for SRP/VDP conversion data.

**Why:** The Tableau "SRP Detail" view (45-col format in Feb RAW tab) undercounts SRP impressions by ~25% vs Market Opportunities, inflating conversion rates. The old 79-col Market Summary format (Dec/Jan RAW) is also slightly different. Using Market Opportunities for all months ensures apples-to-apples comparison. Discovered 2026-04-10 when Feb showed a suspicious jump from 3.76% to 6.97% — turned out to be a source mismatch, not a real trend.

**How to apply:** When running ACA monthly reports, download SRP/VDP conversion from Market Opportunities (Store tab, stock type filter) — not from Tableau SRP detail or the 79-col Market Summary export. Download Used and New separately as CSV crosstabs.
