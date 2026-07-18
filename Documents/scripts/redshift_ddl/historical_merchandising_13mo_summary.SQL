DROP VIEW IF EXISTS bi_vw.historical_merchandising_13mo_summary;

CREATE VIEW bi_vw.historical_merchandising_13mo_summary AS

WITH stock_type_lookup AS (
    --  Embedded Stock Type Lookup
        SELECT 'New'::VARCHAR(50) AS stock_type UNION ALL
        SELECT 'CPO'::VARCHAR(50) UNION ALL
        SELECT 'Dealer'::VARCHAR(50) UNION ALL
        SELECT 'Used'::VARCHAR(50)),

  temp_vehicle_monthly_metrics AS (
    SELECT
        date_trunc('month', date_id::date)::date AS month_start_date,
        vdv.customer_id,
        vdv.dma_code,
        v.stock_type_id,
        v.cpo_ind,
        vdv.vehicle_id,
        MIN(vdv.classified_ad_status_id) AS on_glass_status,
        AVG(CAST(COALESCE(vdv.price, 0) AS BIGINT)) AS avg_price,
        AVG(CASE
                WHEN vdv.msrp = '2021-08-09 20:51:58' THEN 0  -- Filter data anomaly
                ELSE CAST(COALESCE(vdv.msrp, '0') AS FLOAT)
            END) AS avg_msrp,
        AVG(CAST(vdv.mileage AS BIGINT)) AS avg_mileage,
        AVG(CAST(COALESCE(vdv.photo_count, 0) AS BIGINT)) AS avg_photos,
        MAX(CAST(vdv.days_live AS BIGINT)) AS max_days_live,
        MAX(vdv.seller_note_ind) AS has_seller_note,
        CASE
            WHEN v.stock_type_id = 1 THEN 'New'
            WHEN v.stock_type_id = 2 AND v.cpo_ind = 'Yes' THEN 'CPO'
            WHEN v.stock_type_id = 2 AND v.cpo_ind = 'No' THEN 'Used'
            ELSE 'Dealer'
        END AS stock_type
    FROM
        dw_vw.vehicle_daily_vw vdv
        JOIN dw_vw.vehicle_vw v ON v.vehicle_id = vdv.vehicle_id
    WHERE
        vdv.date_id between LAST_DAY(ADD_MONTHS(CURRENT_DATE, -14)) + 1 and CURRENT_DATE-1
    GROUP BY
        1, 2, 3, 4, 5, 6
),

monthly_customers AS (
    SELECT DISTINCT vmm.month_start_date,
                    vmm.customer_id,
                    vmm.dma_code,
                    stl.stock_type
    FROM temp_vehicle_monthly_metrics vmm
    CROSS JOIN stock_type_lookup stl
),


-- Vehicle data aggregated by month, customer, and vehicle
vehicle_monthly_metrics_agg AS (SELECT mc.month_start_date                                               as first_date_of_month,
                                               mc.customer_id,
                                               mc.dma_code,
                                               mc.stock_type,
                                               -- Vehicle listing quality metrics
                                               ROUND(AVG(CASE
                                                             WHEN vm.stock_type_id = 1 AND vm.avg_price = 0
                                                                 THEN vm.avg_msrp
                                                             ELSE vm.avg_price
                                                   END))                                                         AS avg_price,
                                               ROUND(AVG(vm.avg_mileage))                                        AS avg_mileage,
                                               ROUND(AVG(vm.avg_photos))                                         AS avg_photos,
                                               ROUND(AVG(vm.max_days_live))                                      AS avg_days_live,

                                               -- Missing data metrics
                                               COUNT(CASE WHEN vm.has_seller_note = 'No' THEN vm.vehicle_id END) AS veh_missing_seller_notes,
                                               COUNT(CASE
                                                         WHEN
                                                             (vm.stock_type_id = 1 AND (vm.avg_price <= 100 OR vm.avg_msrp <= 100)) OR
                                                             (vm.stock_type_id = 2 AND vm.avg_price <= 100)
                                                             THEN vm.vehicle_id
                                                   END)                                                          AS veh_missing_price,
                                               COUNT(CASE
                                                         WHEN vm.stock_type_id = 2 and (vm.avg_mileage IS NULL or vm.avg_mileage = 0)
                                                             THEN vm.vehicle_id
                                                   END)                                                          AS veh_missing_mileage,
                                               COUNT(CASE
                                                         WHEN (vm.stock_type_id = 1 AND vm.avg_photos = 0) OR
                                                              (vm.stock_type_id = 2 AND vm.avg_photos < 2)
                                                             THEN vm.vehicle_id END)                             AS veh_missing_photos,

                                               -- Vehicle completion status counts
                                               COUNT(CASE
                                                         WHEN (
                                                             (vm.stock_type_id = 1 AND (vm.avg_price > 100 AND vm.avg_photos > 0))
                                                                 OR (vm.stock_type_id = 2 AND vm.avg_price > 100 AND
                                                                     vm.avg_mileage > 50 AND vm.avg_photos >= 2))
                                                             THEN vm.vehicle_id
                                                   END)                                                          AS veh_min_merchandised,

                                               COUNT(CASE
                                                         WHEN (
                                                             (vm.stock_type_id = 1 AND (vm.avg_price > 100 AND vm.avg_photos > 0))
                                                                 OR (vm.stock_type_id = 2 AND vm.avg_price > 100 AND
                                                                     vm.avg_mileage > 50 AND vm.avg_photos >= 2))
                                                             THEN null
                                                         ELSE vm.vehicle_id
                                                   END)                                                          AS veh_min_unmerchandised,

                                               -- Total count
                                               COUNT(vm.vehicle_id)                                              AS veh_count
                                        FROM temp_vehicle_monthly_metrics vm
                                        full outer join monthly_customers mc
                                        on vm.month_start_date=mc.month_start_date
                                        and vm.customer_id = mc.customer_id
                                        and vm.dma_code = mc.dma_code
                                        and vm.stock_type = mc.stock_type
                                        GROUP BY 1, 2, 3, 4
)

-- Final result set with dealer hierarchy and vehicle metrics
SELECT
    CURRENT_DATE AS run_date,
    agg.first_date_of_month,
    -- Dealer hierarchy information
    cus.customer_id,
    cus.dealer_id,
    cus.dealer_uuid,
    cus.dealer_name,
    agg.dma_code,
    dma.dma_market_name,
    cus.franchise_independent,
    cus.maj_dealer_id,
    cus.maj_dealer_uuid,
    cus.maj_dealer_name,
    cus.grp_dealer_id,
    cus.grp_dealer_uuid,
    cus.grp_dealer_name,
    agg.stock_type,

    -- Vehicle listing quality metrics
    avg_price,
    avg_mileage,
    avg_photos,
    avg_days_live,

    -- Missing data metrics
    veh_missing_seller_notes,
    veh_missing_price,
    veh_missing_mileage,
    veh_missing_photos,

    -- Vehicle completion status counts
    veh_min_merchandised,
    veh_min_unmerchandised,

    -- Total count
    veh_count
FROM
    vehicle_monthly_metrics_agg agg
    JOIN bi_vw.dltl_shared_customer_map cus ON agg.customer_id = cus.customer_id
    JOIN dw_vw.dma_market_vw dma ON agg.dma_code = dma.dma_code
WHERE
    cus.franchise_independent <> 'Syco'
WITH NO SCHEMA BINDING
   ;

--View level comment
COMMENT ON VIEW bi_vw.historical_merchandising_13mo_summary IS 'Historical merchandising summary for the last 13 months';
