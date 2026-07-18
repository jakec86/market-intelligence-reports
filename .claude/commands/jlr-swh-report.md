# JLR Southwest Houston — Cars.com Performance Report

Generate and deliver the Cars.com performance and price badge optimization report for Land Rover Southwest Houston. This is an on-demand report — run when the AE requests a fresh analysis or when new data files are available.

---

## Data Files Required

Download all four files before running. Each requires a browser session to admin.cars.com (JumpCloud SSO).

| File | Source | Where to Download |
|---|---|---|
| Houston LEI CSV | Cars.com LEI Tableau | Tableau → LEI view → DMA=Houston (all dealers) → Download Crosstab → CSV |
| JLR SWH Market Share Comp | admin.cars.com | Dealer page → Market Comparison tab → Download Crosstab → CSV |
| JLR SWH Price Comparison | admin.cars.com | Dealer page → Demand Signals → Price Comparison tab → Download Crosstab → CSV |
| CarGurus Dashboard HTML | CarGurus (provided by dealer/AE) | Save the full HTML page from CarGurus dealer dashboard |
| SW H.csv | admin.cars.com | Dealer page → Inventory → export all (SW H naming convention) |
| Connections export | admin.cars.com | Connections & Contact Details → Export (all months, all connection types) |
| VDP Summary | admin.cars.com Performance Trends | Download Crosstab → VDP Summary sheet → CSV |
| Leads Summary | admin.cars.com Performance Trends | Download Crosstab → Leads Summary sheet → CSV |

**admin.cars.com dealer UUID for JLR SW Houston:** `4f22f3c9-d9ac-5cce-abee-1c9aaecf23e1`

**Performance Trends URL:**
```
https://admin.cars.com/dealers/4f22f3c9-d9ac-5cce-abee-1c9aaecf23e1/reports/performance_trends
```

**Connections & Contact Details URL:**
```
https://admin.cars.com/dealers/4f22f3c9-d9ac-5cce-abee-1c9aaecf23e1/reports/connections_contact_details
```

---

## Key Data Notes

- **Instant Offer - Cars.com = AccuTrade.** These connections are labeled "Instant Offer - Cars.com" in the Source column of the Connections export. Exclude them from marketplace connection counts. In Q2 2026: **44 Instant Offer connections** out of 930 total = 886 marketplace connections.
- **"Other (map view, vdp print)"** in the Performance Trends Leads Summary is NOT AccuTrade — it's legitimate marketplace engagement (map views and VDP prints).
- **182 used vehicles** in the Price Comparison CSV — use this as the denominator for badge rate and price-to-market % calculations. The LEI has 189 vehicles total (7 new vehicles without stock type match don't receive badges).
- **New inventory does not receive price badges** on Cars.com. All badge opportunity calculations should filter to Used stock type only.
- **Avg Price-to-Market 102.2%** in the competitive landscape means the weighted average price is 2.2% above market average. This is NOT a badge %, it does NOT match the Fair/Above Badge % shown in admin Performance Trends (different metrics).

---

## Run the Script

As of 2026-07-17, this report runs on the generalized `dealer_market_report.py` engine
(profile: `jlr_swh`) rather than the original one-off `jlr_swh_market_report.py`. The
old script is left in place untouched as a reference/fallback but is no longer the
one to run.

```bash
python3 ~/Documents/scripts/dealer_market_report.py \
  --profile jlr_swh \
  --lei ~/Downloads/"Low Engaged Inventory Report - Houston.6.8.26.csv" \
  --market-share ~/Downloads/"JLR SWH Market Share Comp.csv" \
  --price-comp ~/Downloads/"JLR SWH Price Comparison.csv" \
  --cargurus ~/Downloads/"JLR_SWHouston_Dashboard (1).html" \
  --perf ~/Downloads/"SW H.csv" \
  --no-draft
```

Add `--send` to create a Gmail draft to `jcrawley@cars.com` (pre-send rule always active).

Per-dealer specifics (franchise makes, comp-set, store-name merges, period labels, and
the hand-curated Performance Trends quarter numbers) live in the `jlr_swh` profile
inside `dealer_market_report.py`'s `PROFILES` dict. For a different dealer, either add
a new entry there or pass `--profile-json path/to/profile.json` with the same shape.

**Output:** `~/Documents/Reports/LandRoverSWHouston/landroversouthwesthouston_market_report_YYYY-MM-DD.html`

---

## Updating Q2 Numbers (when period changes)

The Q2 2026 performance metrics live in `PROFILES['jlr_swh']['perf_trends']` in `dealer_market_report.py` (no live CSV parser exists for this section — it's hand-curated each period). When the reporting period changes, update these values:

1. Download fresh VDP Summary and Leads Summary CSVs from Performance Trends
2. Download fresh Connections export from Connections & Contact Details (change date range to new period)
3. Update `PROFILES['jlr_swh']['perf_trends']` with new totals, and `period_label`/`quarter_label`/`month_labels` if the period itself changed
4. Update `conn_monthly_by_type` within that same dict with the new monthly breakdown

**Current Q2 2026 (March–May) confirmed values:**
- VDPs: 30,952 (Mar 10,218 / Apr 10,642 / May 10,092) — source: Performance Trends VDP Summary CSV
- Connections: 930 total, 886 excl. Instant Offer (44) — source: Connections export
- Monthly connections excl. Instant Offer: Mar 230 / Apr 307 / May 349

---

## Report Structure

The report is organized as: **Performance → Optimization**

1. **KPI Cards** — Fair/Good/Great badge rate, Good/Great rate, Price at/under market %, JLR franchise VDP share
2. **VDP & Connection Performance** — Monthly bar charts (VDP first, then Connections) + connection type breakdown table
3. **Inventory Performance** — Engagement tiles: VDPs 90-day, Connections 90-day, Avg Days Live (New vs Used), Badge Opportunities count
4. **Price Badge Optimization** — Badge distribution donut + Price vs. Market bar + Badge Opportunities table (top 5, link to GSheet)
5. **Market Share by Make/Model** — JLR SW Houston vs Houston market, sorted by signal
6. **Competitive Inventory Landscape** — Houston JLR franchise stores ranked by within-$1k % and avg days live

---

## Pre-Send Rule

All drafts go to `jcrawley@cars.com` first. Do not send directly to dealer contacts without Jake's approval.

---

## Google Sheet Link

Full inventory data (badge opportunities, LEI details):
`https://docs.google.com/spreadsheets/d/1JxpuPsusYKoavvT-xet0wd75nLYbawxGD5ZKOWCiRyo/edit?gid=565895707#gid=565895707`
