---------------------------------------
--Vehicle Demand V3 - Optimized
---------------------------------------
DROP VIEW IF EXISTS bi_vw.demand_signals_13mo_summary;
CREATE VIEW bi_vw.demand_signals_13mo_summary AS
-- Vehicle data aggregated directly to vehicle level
WITH vehicle_initial as (
    SELECT
        date_trunc('month', vdv.date_id::date)::date AS first_date_of_month,
        vdv.customer_id,
        v.stock_type_id,
        v.cpo_ind,
        vdv.make_id,
        vdv.make_model_id,
        vdv.vehicle_id,
        ROUND(AVG(COALESCE(vdv.price, 0))) AS avg_price,
        ROUND(AVG(vdv.mileage)) AS avg_mileage,
        ROUND(AVG(COALESCE(vdv.photo_count, 0))) AS avg_photos,
        ROUND(AVG(vdv.days_live)) AS avg_days_live,
        COUNT(DISTINCT vdv.vehicle_id) AS veh_count
    FROM dw_vw.vehicle_daily_vw vdv
    JOIN dw_vw.vehicle_vw v ON v.vehicle_id = vdv.vehicle_id
    WHERE date_id between LAST_DAY(ADD_MONTHS(CURRENT_DATE, -14))+1 and CURRENT_DATE - 1
    AND vdv.classified_ad_status_id = 0
    GROUP BY 1, 2, 3, 4, 5, 6, 7
    ),

-- Vehicle data aggregated directly to final level
vehicle_final as (
    SELECT
        first_date_of_month,
        customer_id,
        stock_type_id,
        cpo_ind,
        make_id,
        make_model_id,
        ROUND(AVG(avg_price)) AS avg_price,
        ROUND(AVG(avg_mileage)) AS avg_mileage,
        ROUND(AVG(avg_photos)) AS avg_photos,
        ROUND(AVG(avg_days_live)) AS avg_days_live,
        SUM(veh_count) AS veh_count
    FROM vehicle_initial
    GROUP BY 1, 2, 3, 4, 5, 6
),

--SRPs and VDPs
srps_vdps as (
    SELECT
        to_date(agg.year_month,'yyyymm') as first_date_of_month,
        agg.customer_id,
        agg.make_id,
        agg.make_model_id,
        agg.stock_type_id,
        agg.cpo_ind,
        SUM(agg.srp_imp) as srp_imps,
        SUM(agg.vdp_imp+agg.llp_imp) as vdp_imps
    FROM dw_vw.agg_vehicle_metric_daily_vw agg
    WHERE date_id between LAST_DAY(ADD_MONTHS(CURRENT_DATE, -14))+1 and CURRENT_DATE - 1
    GROUP BY 1,2,3,4,5,6
),

--Leads data
connections as (
    SELECT
        date_trunc('month',ld.date_id::date)::date as first_date_of_month,
        ld.customer_id,
        ld.make_id,
        ld.make_model_id,
        ld.stock_type_id,
        ld.cpo_ind,
        COUNT(ld.lead_id) as leads
    FROM dw_vw.lead_vw ld
    WHERE date_id between LAST_DAY(ADD_MONTHS(CURRENT_DATE, -14))+1 and CURRENT_DATE - 1
        AND ld.make_model_id != '0'
    GROUP BY 1,2,3,4,5,6
),

-- Saved vehicle metrics (consolidated)
saved_vehicles AS (
    SELECT
        date_trunc('month',clk.date_id::date)::date as first_date_of_month,
        clk.customer_id,
        clk.stock_type_id,
        clk.cpo_ind,
        clk.make_id,
        clk.make_model_id,
        SUM(clk.clicks) AS saved_vehicles
    FROM dw_vw.click_daily_vw clk
    JOIN dw_vw.web_page_type_vw wpt ON clk.web_page_type_to_id = wpt.web_page_type_id
    WHERE wpt.web_page_type_name IN ('Save This Vehicle VDP Impression', 'Save This Vehicle SRP Impression')
    AND date_id between LAST_DAY(ADD_MONTHS(CURRENT_DATE, -14))+1 and CURRENT_DATE - 1
    GROUP BY 1, 2, 3, 4, 5, 6
)

-- Consolidated non-search data with lookups
    SELECT
        current_date as run_date,
        vm.first_date_of_month,
        cus.dma_code,
        cus.dma_market_name,
        cus.dealer_id,
        cus.dealer_name,
        cus.maj_dealer_id,
        cus.maj_dealer_name,
        cus.grp_dealer_id,
        cus.grp_dealer_name,
        vm.stock_type_id,
        vm.cpo_ind,
        mk.make_name,
        mo.model_name,
        cat.category_name,
        cat.subcategory_name,
        vm.avg_price,
        vm.avg_mileage,
        vm.avg_photos,
        vm.avg_days_live,
        vm.veh_count,
        COALESCE(srp.srp_imps, 0) as srp_imps,
        COALESCE(srp.vdp_imps, 0) as vdp_imps,
        COALESCE(con.leads, 0) as connections,
        COALESCE(sv.saved_vehicles, 0) as saved_vehicles
    FROM vehicle_final vm
    JOIN bi_vw.shared_customer_lookup cus on vm.customer_id=cus.customer_id
    JOIN dw_vw.make_vw mk ON vm.make_id = mk.make_id
    JOIN dw_vw.make_model_vw mo ON vm.make_model_id = mo.make_model_id
    LEFT JOIN dw_vw.current_vehicle_category_vw cat ON vm.make_model_id = cat.make_model_id
    LEFT JOIN srps_vdps srp ON (vm.first_date_of_month=srp.first_date_of_month and vm.customer_id=srp.customer_id
                                and vm.make_id=srp.make_id and vm.make_model_id=srp.make_model_id 
                                and vm.stock_type_id=srp.stock_type_id and vm.cpo_ind=srp.cpo_ind)
    LEFT JOIN connections con ON (vm.first_date_of_month=con.first_date_of_month and vm.customer_id=con.customer_id
                                and vm.make_id=con.make_id and vm.make_model_id=con.make_model_id 
                                and vm.stock_type_id=con.stock_type_id and vm.cpo_ind=con.cpo_ind)
    LEFT JOIN saved_vehicles sv ON (vm.first_date_of_month=sv.first_date_of_month and vm.customer_id=sv.customer_id
                                and vm.make_id=sv.make_id and vm.make_model_id=sv.make_model_id 
                                and vm.stock_type_id=sv.stock_type_id and vm.cpo_ind=sv.cpo_ind)
with no schema binding
;

-- View Level Comment
COMMENT ON VIEW bi_vw.demand_signals_13mo_summary IS 'What YMM vehicles are most in demand within specific markets. Data looks back for the last 13 months, and contains metrics such as connections, VDPs, SRPs, and saved vehicles.';

