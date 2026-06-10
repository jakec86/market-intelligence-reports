# Redshift Query Library — Reporting Workflow Replacements

Maps every manual/scraped reporting workflow to direct Redshift SQL via the Atlan
connector. Built 2026-06-10 from Atlan catalog DDL (schemas verified; **SQL is
DRAFT — nothing has executed yet**, blocked on per-user Redshift credentials).

**How to run (once creds are in Jake's Atlan profile):**
- Claude: `query_assets_tool` with `connection_qualified_name: "default/redshift/1662759587"`
  (connection `redshift-prod`; `rs-prod-consumer` = `default/redshift/1698171927`)
- Manually: Atlan Insights, or any client → `dw.data-prod.cars.com:5439`, db `dw`

**First session with creds — run the VERIFICATION queries at the bottom before
trusting anything here.**

---

## Join keys (from customer_vw DDL — verified in catalog)

| Field | Meaning |
|---|---|
| `customer_id` | Internal warehouse ID — joins everything in `dw.*` / `dw_vw.*` |
| `ccid` | The CCID used in Salesforce (`CCID__c`) and reporting |
| `legacy_id` / `uuid` | admin.cars.com legacy id (numeric → `uuid` cast in customer_vw) |
| `ultimate_parent_customer_legacy_id` / `_name` | Dealer group umbrella (Asbury, Sonic...) |
| `major_acct_customer_name` | Major-account grouping ≈ Tableau "Maj Cust Name" filter |
| `dma_code` / `dma_market_name` | Market |

---

## 1. Dealer roster & products — `dw_vw.customer_vw`
**Replaces:** SF CLI account lookups, AE Insights Tableau (products/MRR), parts of
`/book-scan`, `/prep`, Sonic/Hendrick billing reconciliation.

Catalog-verified columns: `ccid`, `customer_name`, `cars_customer_status`,
`customer_status`, `dma_market_name`, `ultimate_parent_customer_name`,
`major_acct_customer_name`, `active_product_name_list`, `ad_package_name_list`,
`cars_core_package_revenue_amount`, and per-product triplets
(`*_ind`, `*_count`, `*_revenue_amount`) for: dealer_rater, cars_accutrade,
dealer_position, power_position, cars360, cars_social, premier, website,
conversations, online_shopper, seo/metal/digad inds. Plus
`marketplace_account_owner_id` (AE when active), `dr_drc_ind`/`dr_drc_plus_ind`,
`last_activity_date`, GA4 IDs.

```sql
-- Store roster for a group (e.g. Sonic ~101, ACA ~72, EchoPark 17)
SELECT ccid, customer_name, city, state, dma_market_name,
       cars_customer_status, active_product_name_list,
       cars_core_package_revenue_amount, premier_ind, cars_social_ind,
       dealer_rater_ind
FROM dw_vw.customer_vw
WHERE ultimate_parent_customer_name ILIKE '%sonic%'      -- or major_acct_customer_name
  AND cars_customer_status = 'Active'
ORDER BY customer_name;

-- Billing reconciliation (Sonic + Hendrick): per-store package revenue
SELECT ccid, customer_name, ad_package_name_list,
       cars_core_package_revenue_amount, cars_ancillary_package_revenue_amount,
       premier_count, premier_revenue_amount,
       cars_social_count, cars_social_revenue_amount,
       dealer_rater_count, dealer_rater_revenue_amount
FROM dw_vw.customer_vw
WHERE ultimate_parent_customer_name ILIKE '%hendrick%'
  AND cars_customer_status = 'Active';
```
Note: revenue fields are **current-month** snapshot (view takes latest
`customer_daily` row). For historical months use `dw.customer_daily` with
`date_id` = month-end.

## 2. Price Badge Report — `dw_vw.vehicle_daily_vw` (+ `master_data.vehicle`)
**Replaces:** Tableau LEI crosstab download (the whole Playwright/MFA dance).

Catalog-verified columns on `vehicle_daily` / `vehicle_daily_vw`: `price_badge`,
`has_price_badge`, `good_threshold`, `great_threshold`, `fair_threshold`,
`customer_id`. (`master_data.vehicle` has the same per current listing, 594M rows
incl. history — prefer vehicle_daily latest day.) VERIFY: stock number, photos
count, days-live column names; price column name.

```sql
-- PB report core: vehicles within $X of next badge (LEI replacement)
-- VERIFY column names marked ⚠ on first run
WITH v AS (
    SELECT vd.customer_id, vd.vin, vd.stock_no,            -- ⚠ stock_no
           vd.model_year, vd.make_name, vd.model_name, vd.trim_name,  -- ⚠ names
           vd.price,                                        -- ⚠ price col
           vd.price_badge, vd.good_threshold, vd.great_threshold
    FROM dw_vw.vehicle_daily_vw vd
    WHERE vd.date_id = (SELECT MAX(date_id) FROM dw_vw.vehicle_daily_vw)  -- ⚠ date col
      AND vd.stock_type = 'Used'                            -- ⚠ stock type col; PB = Used only
)
SELECT c.ccid, c.customer_name, v.*,
       CASE WHEN v.price_badge NOT IN ('Good','Great')
            THEN v.price - v.good_threshold END  AS drop_for_good,
       CASE WHEN v.price_badge <> 'Great'
            THEN v.price - v.great_threshold END AS drop_for_great
FROM v JOIN dw_vw.customer_vw c ON v.customer_id = c.customer_id
WHERE c.ultimate_parent_customer_name ILIKE '%hendrick%'   -- or c.ccid = '109754' for Nalley
  AND (   (v.price - v.good_threshold)  BETWEEN 0 AND 500
       OR (v.price - v.great_threshold) BETWEEN 0 AND 500 )
ORDER BY LEAST(NVL(v.price - v.good_threshold, 999999),
               NVL(v.price - v.great_threshold, 999999));
```
Related: `insight.price_badge_explainer` (badge notes), `insight.price_badge_v2`
(model detail: `pred_price`, `pred_price_diff`, `per_pred_price_diff` — the
"price vs market %" for Demand Signals framing), `insight.realtime_inventory_listing`
(current listing state incl. thresholds).

## 3. Store performance metrics — `dw_vw.agg_vehicle_metric_daily_vw` / `_monthly_vw`
**Replaces:** Tableau "By Store" view (Sonic/Hendrick/ACA/EchoPark/Asbury monthly
reports), admin.cars.com Performance Trends, JLR/HCC4 VDP pulls.

DDL-verified columns: `DATE_ID`/`YEAR_MONTH`, `CUSTOMER_ID`, `DMA_CODE`,
`STOCK_TYPE_ID`, `VDP_IMP`, `SRP_IMP`, `SRP_VIEWABLE_IMP`, `EMAIL_LEAD`,
`PHONE_LEAD`, `CHAT_LEAD`, `DEALER_TEXT_LEAD`, `INV_EMAIL_LEAD`,
`VISIT_DLR_WEB_CONTACT`, `MAP_DLR_CONTACT`, `DRIV_DIR_CONTACT`, `SHARE_CONTACT`,
`TOTAL_WALKIN_LEAD` (OTL/NTL), `PREMIER_IMP/LEAD`, `FINANCE_LEAD`, device/source dims.

Definitions (per [[connections-vs-leads]]): **Leads** = phone + email + chat;
**Connections** = leads + map/directions/website clicks etc.

```sql
-- Monthly store scorecard, current vs prior month (group report core)
SELECT c.ccid, c.customer_name, m.year_month,
       SUM(m.srp_imp)  AS srps,
       SUM(m.vdp_imp)  AS vdps,
       SUM(m.email_lead + m.phone_lead + m.chat_lead) AS leads,
       SUM(m.email_lead + m.phone_lead + m.chat_lead
           + m.visit_dlr_web_contact + m.map_dlr_contact
           + m.driv_dir_contact)                      AS connections,  -- ⚠ confirm component set
       SUM(m.total_walkin_lead) AS walkins
FROM dw_vw.agg_vehicle_metric_monthly_vw m
JOIN dw_vw.customer_vw c ON m.customer_id = c.customer_id
WHERE c.ultimate_parent_customer_name ILIKE '%echopark%'
  AND m.year_month IN (202605, 202604)
GROUP BY 1,2,3 ORDER BY 2,3;
```

## 4. Lead detail — `dw.lead` (116 cols, most-queried table)
**Replaces:** Tableau lead crosstabs; feeds `/investigate-stores` lead-perf flags.
⚠ Columns not yet pulled from catalog — run verification query, and see the
Confluence SQL Query Library (Ralf Kloeckner) for canonical lead-classification SQL.

## 5. Search / market demand — `insight.search_activity_raw`
**Replaces:** Searches-by-Zip Tableau view (490K rows), `/dealer-marketshareanalysis`
demand side. 82 cols: search results, impressions, clicks, connections per listing.
⚠ Verify zip/DMA/date columns on first run.

## 6. Reviews — `master_data.dealer_review`
**Feeds:** `/ep-review-report`, reputation sections of `/prep` and monthly reports.
⚠ Columns not yet pulled; verify. customer_vw also carries `dealer_rater_id_list`
and DR product flags (`dr_drc_ind`, `dr_review_builder_ind`, `dr_autoresponse_ind`).

## 7. Churn / health signals — `insight.dealer_churn_reason`, `insight.dealer_churn_explainer`
**Feeds:** `/book-scan` (CRITICAL/SUSTAINED flags), `/investigate-stores`.
Has `churn_threshold` + reason/explainer fields — this is the warehouse's own
churn-risk model. ⚠ Explore columns on first run; potentially replaces several
hand-built health heuristics.

---

## Workflow → source map

| Workflow | Today | Redshift replacement |
|---|---|---|
| `/nalley-pb-report`, `/hendricks-pb-report` | Tableau LEI crosstab via Playwright+MFA | §2 vehicle_daily_vw badge query |
| PB Demand Signals paragraph (Nalley) | admin.cars.com Price Comparison crosstab | §2 price_badge_v2 `per_pred_price_diff` buckets |
| `/sonic-monthly-report`, `/hendrick-monthly-report`, `/aca-monthly-report`, `/echopark-monthly-report`, `/asbury-monthly-report` | Tableau By Store view | §3 monthly_vw + §1 roster |
| `/jlr-swh-report`, `/hcc4-vdp-report`, `/ecarone-vpm-report` | Tableau/admin crosstabs | §3 daily_vw filtered to store |
| `/sonic-billing` | Tableau + sheet pivots | §1 revenue fields (current month) / customer_daily (history) |
| `/book-scan` | SF + Tableau + admin scrape | §1 products + §3 trends + §7 churn model |
| `/prep`, `/investigate-stores` | SF + Tableau + admin + DR | §1 + §3 + §4 + §6 |
| `/dealer-marketshareanalysis`, `/auto-research` | Searches-by-Zip view + admin | §5 search_activity_raw |
| `/ep-review-report` | DealerRater admin via Playwright | §6 dealer_review |

**What Redshift does NOT replace:** DealerRater employee-profile *edits*
(`/dr-employee-update`, Herb Chambers — write operations, still Playwright),
Gmail drafts/sends, Google Sheets population, SF activity logging.

---

## Verification queries (run these FIRST when creds land)

```sql
-- 1. Connectivity + row freshness
SELECT MAX(date_id) FROM dw_vw.vehicle_daily_vw;
SELECT MAX(date_id) FROM dw_vw.agg_vehicle_metric_daily_vw;

-- 2. Column discovery for the ⚠-flagged tables
SELECT column_name, data_type FROM information_schema.columns
WHERE table_schema = 'dw' AND table_name = 'vehicle_daily' ORDER BY ordinal_position;
-- repeat for: dw.lead, insight.search_activity_raw, master_data.dealer_review,
--             insight.dealer_churn_reason

-- 3. Ground-truth check: Nalley (CCID 109754) vehicle count + badge mix vs LEI CSV
SELECT vd.price_badge, COUNT(*) FROM dw_vw.vehicle_daily_vw vd
JOIN dw_vw.customer_vw c ON vd.customer_id = c.customer_id
WHERE c.ccid = '109754' AND vd.date_id = (SELECT MAX(date_id) FROM dw_vw.vehicle_daily_vw)
GROUP BY 1;
-- Compare against the same day's Tableau LEI export before cutting over.

-- 4. Group roster counts vs known store counts (Sonic ~101 active, EchoPark 17...)
SELECT ultimate_parent_customer_name, COUNT(*) FROM dw_vw.customer_vw
WHERE cars_customer_status = 'Active'
  AND ultimate_parent_customer_name ILIKE ANY ('%sonic%','%echopark%','%asbury%','%hendrick%')
GROUP BY 1;
```

**Cutover rule:** run any migrated report in parallel with the existing pipeline
for at least 2 cycles and diff the outputs before retiring the scrape.
