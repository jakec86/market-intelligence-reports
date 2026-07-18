-- ============================================================
-- Cars Commerce Redshift - Ready-to-Run Workflow Queries
-- Schema: bi_vw (BI-856 branch views)
-- Target: DataGrip connected to rs-prod/dw
-- ============================================================
-- These queries replace manual Tableau CSV exports and
-- admin.cars.com scraping for Jake's recurring reports.
--
-- SETUP: Replace placeholder values marked with {{...}}
-- All views use 13-month rolling windows automatically.
-- ============================================================


-- ============================================================
-- 1. PRICE BADGE REPORT (replaces Tableau LEI crosstab download)
--    Used by: /nalley-pb-report, /hendricks-pb-report
-- ============================================================
-- Returns badge distribution by dealer for a major account group.
-- Equivalent to the LEI "Dealer Level" crosstab filtered by group.

SELECT
    cus.maj_dealer_name,
    cus.dealer_id,
    cus.dealer_name,
    pb.first_date_of_month,
    pb.stock_type,
    SUM(pb.great_badge_count)   AS great,
    SUM(pb.good_badge_count)    AS good,
    SUM(pb.fair_badge_count)    AS fair,
    SUM(pb.overpriced_count)    AS overpriced,
    SUM(pb.underpriced_count)   AS underpriced,
    SUM(pb.unbadged_count)      AS unbadged,
    SUM(pb.great_badge_count + pb.good_badge_count + pb.fair_badge_count
        + pb.overpriced_count + pb.underpriced_count + pb.unbadged_count) AS total_vehicles
FROM bi_vw.price_badge_13mo_summary pb
JOIN bi_vw.shared_customer_lookup cus ON pb.customer_id = cus.customer_id
WHERE cus.maj_dealer_name = '{{Hendrick Automotive Group}}'  -- or 'Nalley Automotive Group'
  AND pb.first_date_of_month >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '3 months')
GROUP BY 1, 2, 3, 4, 5
ORDER BY cus.dealer_name, pb.first_date_of_month DESC, pb.stock_type;


-- ============================================================
-- 2. CONNECTIONS / LEADS SUMMARY (replaces admin.cars.com Performance Trends)
--    Used by: /aca-monthly-report, /sonic-billing, dealer health reviews
-- ============================================================
-- Splits Connections (all types) vs Leads (Phone+Email+Chat only).
-- Matches the Connections vs Leads distinction from memory.

-- 2a. Total Connections by dealer + month + lead type group
SELECT
    conn.date_id         AS month,
    conn.dealer_id,
    conn.dealer_name,
    conn.maj_dealer_name,
    conn.dma_market_name,
    conn.lead_type_group,
    conn.stock_type,
    SUM(conn.total)      AS connections,
    SUM(conn.total_7_day) AS connections_7day
FROM bi_vw.connections_13mo_summary conn
WHERE conn.maj_dealer_name = '{{Atlantic Coast Automotive}}'  -- or dealer_id = 6051462
  AND conn.date_id >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '6 months')
GROUP BY 1, 2, 3, 4, 5, 6, 7
ORDER BY conn.dealer_name, month DESC, conn.lead_type_group;

-- 2b. Leads only (Phone + Email + Chat) — the "Leads" number for reporting
SELECT
    conn.date_id         AS month,
    conn.dealer_id,
    conn.dealer_name,
    SUM(conn.total)      AS leads
FROM bi_vw.connections_13mo_summary conn
WHERE conn.maj_dealer_name = '{{Atlantic Coast Automotive}}'
  AND conn.lead_type_group IN ('Email Lead', 'Phone Lead', 'Chat Lead')
  AND conn.date_id >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '6 months')
GROUP BY 1, 2, 3
ORDER BY conn.dealer_name, month DESC;


-- ============================================================
-- 3. VDP / SRP METRICS (replaces admin.cars.com Market Opps Store tab)
--    Used by: /aca-monthly-report, dealer performance reviews
-- ============================================================
-- Note: This pulls from agg_vehicle_metric_monthly which is the
-- full-count source (admin.cars.com Market Opps), NOT the Tableau
-- SRP Detail view that undercounts SRPs ~25%.

SELECT
    vm.first_date_of_month   AS month,
    cus.dealer_id,
    cus.dealer_name,
    cus.maj_dealer_name,
    vm.stock_type,
    vm.vdps,
    vm.srps,
    CASE WHEN vm.srps > 0
         THEN ROUND(vm.vdps::FLOAT / vm.srps * 100, 2)
         ELSE 0 END          AS vdp_srp_conversion_pct
FROM bi_vw.vehicle_metrics_monthly_13mo_summary vm
JOIN bi_vw.shared_customer_lookup cus ON vm.customer_id = cus.customer_id
WHERE cus.maj_dealer_name = '{{Atlantic Coast Automotive}}'
  AND vm.first_date_of_month >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '6 months')
ORDER BY cus.dealer_name, month DESC, vm.stock_type;


-- ============================================================
-- 4. DEMAND SIGNALS / MARKET INTELLIGENCE
--    (replaces Tableau crosstab for generate_market_report.py)
--    Used by: Market Intelligence reports, /auto-research
-- ============================================================
-- YMM-level demand by dealer and market — SRPs, VDPs, connections,
-- saved vehicles, avg price, avg days on lot.

SELECT
    ds.first_date_of_month    AS month,
    ds.dma_market_name,
    ds.dealer_name,
    ds.maj_dealer_name,
    ds.make_name,
    ds.model_name,
    ds.category_name,
    ds.subcategory_name,
    CASE
        WHEN ds.stock_type_id = 1 THEN 'New'
        WHEN ds.stock_type_id = 2 AND ds.cpo_ind = 'No' THEN 'Used'
        WHEN ds.stock_type_id = 2 AND ds.cpo_ind = 'Yes' THEN 'CPO'
        ELSE 'Unknown' END   AS stock_type,
    ds.veh_count,
    ds.avg_price,
    ds.avg_mileage,
    ds.avg_days_live,
    ds.srp_imps,
    ds.vdp_imps,
    ds.connections,
    ds.saved_vehicles
FROM bi_vw.demand_signals_13mo_summary ds
WHERE ds.dma_market_name = '{{Hampton Roads-Norfolk}}'  -- DMA market
  AND ds.first_date_of_month >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '3 months')
ORDER BY ds.first_date_of_month DESC, ds.vdp_imps DESC;


-- ============================================================
-- 5. INVENTORY HEALTH + MERCHANDISING (replaces admin.cars.com Listings Optimizer)
--    Used by: dealer health reviews, /dealer-marketshareanalysis
-- ============================================================
-- Current inventory with completeness scores and missing fields.

SELECT
    cus.dealer_id,
    cus.dealer_name,
    cus.maj_dealer_name,
    inv.stock_type,
    COUNT(*)                                     AS total_vehicles,
    ROUND(AVG(inv.completeness), 1)              AS avg_completeness_score,
    ROUND(AVG(inv.days_live), 0)                 AS avg_days_on_lot,
    ROUND(AVG(inv.price), 0)                     AS avg_price,
    SUM(CASE WHEN inv.photo_cnt = 0 THEN 1 ELSE 0 END) AS missing_photos,
    SUM(CASE WHEN inv.price = 0 THEN 1 ELSE 0 END)     AS missing_price,
    SUM(CASE WHEN inv.mileage = 0 AND inv.stock_type != 'New' THEN 1 ELSE 0 END) AS missing_mileage
FROM bi_vw.current_inventory_13mo_detail inv
JOIN bi_vw.shared_customer_lookup cus ON inv.customer_id = cus.customer_id
WHERE cus.maj_dealer_name = '{{Hendrick Automotive Group}}'
GROUP BY 1, 2, 3, 4
ORDER BY cus.dealer_name, inv.stock_type;


-- ============================================================
-- 6. LISTINGS OPTIMIZER DETAIL (replaces admin.cars.com Listings Optimizer page)
--    Used by: dealer health deep dives, vehicle-level analysis
-- ============================================================
-- Vehicle-level detail with badges, hot car flag, leads, VDPs.

SELECT
    lo.dealer_name,
    lo.make_name,
    lo.model_name,
    lo.model_year,
    lo.trim_name,
    lo.stock_type,
    lo.vin,
    lo.price,
    lo.price_badge,
    lo.hot_car_badge,
    lo.days_live,
    lo.completeness,
    lo.missing_merchandising,
    lo.photo_cnt,
    lo.vdp_imps,
    lo.vdp_imps_30_days,
    lo.srp_imps,
    lo.srp_imps_30_days,
    lo.leads,
    lo.leads_30_days,
    lo.saved_vehicles
FROM bi_vw.listings_optimizer_prvday_detail lo
WHERE lo.dealer_id = {{6051462}}  -- CCID
ORDER BY lo.vdp_imps_30_days DESC;


-- ============================================================
-- 7. REPUTATION / REVIEWS (replaces DealerRater scraping)
--    Used by: /ep-review-report, dealer health
-- ============================================================

SELECT
    rev.review_submit_date,
    rev.dealer_name,
    rev.maj_dealer_name,
    rev.source,
    rev.rating_overall,
    rev.review_title,
    LEFT(rev.review_text, 200) AS review_snippet,
    rev.response_ind,
    rev.response_submit_date,
    LEFT(rev.response_text, 200) AS response_snippet
FROM bi_vw.reputation_reviews_13mo_detail rev
WHERE rev.maj_dealer_name = '{{Sonic Automotive}}'
  AND rev.review_submit_date >= CURRENT_DATE - INTERVAL '90 days'
ORDER BY rev.review_submit_date DESC;


-- ============================================================
-- 8. DEALER LOOKUP (find customer_id / dealer_id / UUID for any dealer)
-- ============================================================
-- Use this to find the right identifiers before running other queries.

SELECT
    customer_id,
    dealer_id,
    DealerUUID,
    dealer_name,
    franchise_independent,
    maj_dealer_id,
    maj_dealer_name,
    grp_dealer_id,
    grp_dealer_name,
    di_group_dealer_id,
    di_group_dealer_name,
    dma_code,
    dma_market_name,
    postal_code
FROM bi_vw.shared_customer_lookup
WHERE dealer_name ILIKE '%{{hendrick}}%'  -- or maj_dealer_name, dealer_id, etc.
ORDER BY maj_dealer_name, dealer_name;
