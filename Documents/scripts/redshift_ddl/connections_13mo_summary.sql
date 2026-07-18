
DROP VIEW IF EXISTS bi_vw.connections_13mo_summary;

CREATE VIEW bi_vw.connections_13mo_summary AS
--DLTL Connections 13Mo Summary
WITH CombinedLeads AS (
SELECT
    ADD_MONTHS(ld.date_id - EXTRACT(DAY FROM ld.date_id) + 1, 0) AS date_id,
    ld.customer_id,
    case when ld.shipping_cost_ind = 'Yes' then 'Yes' else 'No' end as shipping_cost_ind,
    CASE
        WHEN af.apn = 'fbooksocial2' AND ld.lead_type_id = 12 AND (utm_medium <> 'leadgen' OR utm_medium IS NULL) THEN CAST(9998 AS SMALLINT)
        WHEN af.apn = 'fbooksocial2' AND ld.lead_type_id = 15 AND (utm_medium <> 'leadgen' OR utm_medium IS NULL) THEN CAST(9997 AS SMALLINT)
        WHEN ld.lead_type_id = 120 AND finance_application_current_status = 'credit app' THEN CAST(9996 AS SMALLINT)
        WHEN ld.lead_type_id = 120 AND finance_application_current_status = 'prequalified' THEN CAST(9995 AS SMALLINT)
        WHEN ld.lead_type_id = 120 AND finance_application_current_status = 'finance intent' THEN CAST(9994 AS SMALLINT)
        ELSE ld.lead_type_id
    END AS lead_type_id,
    ld.mobile_ind,
    CASE
        WHEN ld.stock_type_id = 1 THEN 'New'
        WHEN ld.stock_type_id = 2 AND ld.cpo_ind = 'No' THEN 'Used'
        WHEN ld.stock_type_id = 2 AND ld.cpo_ind = 'Yes' THEN 'CPO'
        ELSE 'Dealer'
    END AS stock_type,
    COUNT(ld.lead_id) AS total,
    COUNT(CASE WHEN ld.date_id >= CURRENT_DATE - 6 THEN ld.lead_id END) AS total_7_day
FROM dw_vw.lead_vw ld
LEFT JOIN dw_vw.affiliate_vw af ON ld.front_door_affiliate_id = af.affiliate_id
WHERE ld.date_id BETWEEN LAST_DAY(ADD_MONTHS(CURRENT_DATE, -13)) + 1 AND CURRENT_DATE 
    AND ld.lead_type_id NOT IN (25, 104) -- 25 Email This Page & 104 Deep Link Sell Your Car Transfer
GROUP BY 1, 2, 3, 4, 5, 6

UNION ALL

SELECT
    ADD_MONTHS(agg.date_id - EXTRACT(DAY FROM agg.date_id) + 1, 0) AS date_id,
    agg.customer_id,
    'No' as shipping_cost_ind,
    CAST(76 AS SMALLINT) AS lead_type_id,
    agg.mobile_ind,
    CASE
        WHEN agg.stock_type_id = 1 THEN 'New'
        WHEN agg.stock_type_id = 2 AND agg.cpo_ind = 'No' THEN 'Used'
        WHEN agg.stock_type_id = 2 AND agg.cpo_ind = 'Yes' THEN 'CPO'
        ELSE 'Dealer'
    END AS stock_type,
    SUM(agg.total_walkin_lead) AS total,
    SUM(CASE WHEN agg.date_id >= CURRENT_DATE - 6 THEN agg.total_walkin_lead END) AS total_7_day
FROM dw_vw.agg_vehicle_metric_daily_vw agg
WHERE agg.date_id BETWEEN LAST_DAY(ADD_MONTHS(CURRENT_DATE, -13)) + 1 AND CURRENT_DATE AND agg.total_walkin_lead > 0
GROUP BY 1, 2, 3, 4, 5, 6

UNION ALL

SELECT
    ADD_MONTHS(agg.date_id - EXTRACT(DAY FROM agg.date_id) + 1, 0) AS date_id,
    agg.customer_id,
    'No' as shipping_cost_ind,
    CAST(9999 AS SMALLINT) AS lead_type_id,
    agg.mobile_ind,
    CASE
        WHEN agg.stock_type_id = 1 THEN 'New'
        WHEN agg.stock_type_id = 2 AND agg.cpo_ind = 'No' THEN 'Used'
        WHEN agg.stock_type_id = 2 AND agg.cpo_ind = 'Yes' THEN 'CPO'
        ELSE 'Dealer'
    END AS stock_type,
    SUM(agg.nlp_email_lead) AS total,
    SUM(CASE WHEN agg.date_id >= CURRENT_DATE - 6 THEN agg.nlp_email_lead END) AS total_7_day
FROM dw_vw.agg_vehicle_metric_daily_vw agg
WHERE agg.date_id BETWEEN LAST_DAY(ADD_MONTHS(CURRENT_DATE, -13)) + 1 AND CURRENT_DATE AND agg.nlp_email_lead > 0
GROUP BY 1, 2, 3, 4, 5, 6
)

SELECT
    CURRENT_DATE AS run_date,
    CAST(ld.date_id AS DATE) AS date_id,
    cus.customer_id,
    cus.dealer_id,
    cus.DealerUUID,
    cus.dealer_name,
    cus.franchise_independent,
    cus.maj_dealer_id,
    cus.MajDealerUUID,
    cus.maj_dealer_name,
    cus.grp_dealer_id,
    cus.GrpDealerUUID,
    cus.grp_dealer_name,
    cus.di_group_dealer_id,
    cus.di_group_dealer_name,
    cus.dma_code,
    cus.dma_market_name,
    ld.shipping_cost_ind,
    CASE
        WHEN ld.lead_type_id IN (9997, 9998, 9999, 9996, 9995, 9994) THEN 'Email Lead'
        ELSE lead_type_group
    END AS lead_type_group,
    CASE
        WHEN ld.lead_type_id = 9997 THEN 'New Car Email-Social'
        WHEN ld.lead_type_id = 9998 THEN 'Used Car Email-Social'
        WHEN ld.lead_type_id = 9999 THEN 'NLP Email'
        WHEN ld.lead_type_id = 9996 THEN 'Email - Credit Application'
        WHEN ld.lead_type_id = 9995 THEN 'Email - Prequalified'
        WHEN ld.lead_type_id = 9994 THEN 'Email - Finance Intent'
    ELSE ltv.lead_type_name_label END AS lead_type_name,
    ld.stock_type,
    ld.mobile_ind,
    SUM(ld.total) AS total,
    SUM(COALESCE(ld.total_7_day, 0)) AS total_7_day
FROM CombinedLeads ld
LEFT JOIN bi_vw.shared_lead_type_lookup ltv ON ld.lead_type_id = ltv.lead_type_id
INNER JOIN bi_vw.shared_customer_lookup cus ON ld.customer_id = cus.customer_id
WHERE cus.franchise_independent <> 'Syco'
GROUP BY 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22
with no schema binding
;


-- View Level Comment
COMMENT ON VIEW bi_vw.connections_13mo_summary IS 'Shows all lead activity (including Social, NLP, and Walk-Ins) for a given dealer by lead type and lead type group. Data is available for the last 13 months and is aggregated at the month level.';
-- Column Level Comments

--COMMENT ON COLUMN bi_vw.connections_13mo_summary.run_date IS 'System current date and time at the time of query execution.';
