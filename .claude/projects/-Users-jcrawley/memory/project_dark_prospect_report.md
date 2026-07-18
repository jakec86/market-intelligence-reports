---
name: project_dark_prospect_report
description: "/dark-prospect-report tool — scrape a dark prospect's used inventory, plot on Demand Signals churner quadrant, project Cars.com performance"
metadata: 
  node_type: memory
  type: project
  originSessionId: f837ad02-f48d-4c65-88ef-5f45397a6b5c
---

**`/dark-prospect-report`** (skill: `~/.claude/commands/dark-prospect-report.md`, engine: `~/Documents/scripts/dark_prospect_report.py`) — shows a dark prospect how their *current used inventory* would perform on Cars.com. Built 2026-06-12 for Park Place MB ([[park-place-prospect]]).

**Pipeline:** scrape prospect's own-site used inventory (chrome-devtools, Akamai — see [[reference_dealer_site_scrape]]) → classify each vehicle onto the admin.cars Demand Signals "Churners" quadrant → project monthly VDPs/connections/leads/$ via a blended benchmark.

**Inputs (CONFIG block in the script):** inventory JSON + 3 admin.cars CSVs in `~/Documents/Tableau/` — **Market Comparison** (per make/model market vehicles+VDPs → 4-quadrant via median splits), **Demand Quadrants** (broad all-make churner list, classifies trade-ins), **Performance Trends KPIs** (comparable store Avg Inv/VDPs/Connections, monthly). Used-only.

**Blend legs:** prospect's own prior Cars.com history (40%) + active comparable store (30%, de-weighted — its Avg-Inventory KPI may be all-stock not used) + DMA market (30%). Quadrant multipliers (Churner 1.30 … Lot Sitter 0.70) are **normalized to inventory-weighted mean 1.0** → reclassification redistributes, never inflates the total.

**Outputs:** full HTML report (Chart.js quadrant scatter + tables) + deck-styled pitch slide (matches `park_place_pitch_v2.html`). Both written to the group's `~/Documents/Reports/<Group>/`.

**Park Place result (2026-06-12):** 313 used vehicles, **58% Churners**. Full inventory (1,150 new+used): **222 connections/mo · 100 leads/mo** (headline KPIs). Used-lot only: **60 connections/mo · 27 leads/mo** (tracks their 2025 actual of 50 conns/mo). ~$22K/mo (~$268K/yr) incremental. Files: `parkplace_inventory_projection_2026-06-12.html` + `..._SLIDE_2026-06-12.html`.

**Leads (2026-06-15):** Leads = phone+email+chat subset, config knob `revenue.lead_share_of_conn`. Now surfaced first-class — hero KPI card + per-store column (report + slide) + interactive used-lot calculator stat. Two consistent bases: full-inventory tables/KPIs use `proj_conn_total × lead_share`; the used-lot calculator uses `proj_conn × lead_share`. Fixed a latent bug where `proj_leads` was computed off the used number but never rendered. **Calibrated to Park Place's own actual** = 0.23 (was 0.45 placeholder): pooled 62 leads / 269 connections over their paid-active window May–Sep 2025, from the 3 MB Monthly Performance Crosstabs (`~/Documents/Tableau/MB {Dallas,Fft Worth,Arlington} Monthly Performance Crosstab.csv`, UTF-16/tab). At 0.23: full inventory 222 conn → 51 leads/mo; used lot 60 conn → 14 leads/mo. **Revenue model is BLENDED (2026-06-15):** gross = (leads × `close_rate` + non-lead connections × `click_close_rate`) × `gpu`. Rationale: ~60% of connections are VDP deep-link clicks you can't close at a lead-close rate — applying 8% to all 222 connections overstated gross ~3-4×. Config: `close_rate` 0.08 (range .06–.10) on leads, `click_close_rate` 0.01 (range .005–.015) on clicks/transfers, `gpu` $4,500. Park Place midpoint = **~$26K/mo (~$313K/yr)** — down from the old ~$80K/mo (~$960K/yr) off raw connections. **Headline rule:** lead with LEADS (real contacts), connections = broader engagement context. Historical proof table now shows actual leads (Dallas 9/FW 7/Arl 2 = 18/mo) beside connections (50/mo, mostly walk-ins); also fixed a false "most heavily-weighted leg" label (the `self` leg is weighted 0.00 — it's a proof point, not a blend input).

**0.23 cross-validated by the active comparable** MB Plano (`MB of Plano exportdetails.csv`, connection-detail export, Mar–May 2026): lead share 0.217. admin.cars "connections" = all digital events except Maps (incl. VDP Deep Links, which are ~60% of the total) — MB Plano all-excl-Maps = 552/mo ≈ the 531/mo benchmark leg, so the benchmark connections are digital & walk-in-free (the projection is NOT walk-in-inflated). Note: connection rows differ between the aggregate crosstab and detail export; for the dark prospect's OWN thin history, connections were walk-in-heavy, but that does not contaminate the benchmark-driven projection. See [[connections-vs-leads-terminology]] and [[park-place-prospect]].

Reusable for any dark prospect: edit CONFIG (stores, comparable, CSVs, legs) and re-run. Not yet in CLAUDE.md skills table.
