DROP VIEW IF EXISTS bi_vw.saved_vehicles_13mo_summary;

CREATE VIEW bi_vw.saved_vehicles_13mo_summary AS
--Saved Vehicles
WITH valid_from_pages AS (SELECT web_page_type_id
                          FROM dw_vw.web_page_type_vw
                          WHERE web_page_type_name IN (
                                                       'Search Results Page', '2.0 Aggregate Search Results Page',
                                                       'TYP New Similar Vehicles Module',
                                                       'TYP Used Similar Vehicles Module',
                                                       'VDP New Similar Vehicles Module',
                                                       'VDP Used Similar Vehicles Module',
                                                       'Vehicle Listing - VDP New Similar Vehicles Module',
                                                       'Vehicle Listing - VDP Used Similar Vehicles Module',
                                                       '2.0 More Details Page', 'Enhanced Special Offers'
                              )),
     valid_to_pages AS (SELECT web_page_type_id, web_page_type_name, web_page_type_category
                        FROM dw_vw.web_page_type_vw
                        WHERE web_page_type_name IN (
                                                     '2.0 More Details Page',
                                                     'Vehicle Listing - VDP New Similar Vehicles Module',
                                                     'VDP New Similar Vehicles Module',
                                                     'VDP Used Similar Vehicles Module',
                                                     'Vehicle Listing - VDP Used Similar Vehicles Module',
                                                     'Enhanced Special Offers',
                                                     'Program Branding', 'Email Lead Modal Form',
                                                     'Save This Vehicle VDP Impression',
                                                     'Save This Vehicle SRP Impression', 'AutoCheck Free Links',
                                                     'AutoCheck Paid Links',
                                                     'Carfax Free Links', 'Carfax Free Single Owner Link'
                            ))

SELECT to_date(trim(clk.year_month), 'yyyymm') as first_date_of_month,
       clk.customer_id,
       CASE
           WHEN clk.stock_type_id = 1 THEN 'New'
           WHEN clk.stock_type_id = 2 AND clk.cpo_ind = 'Yes' THEN 'CPO'
           WHEN clk.stock_type_id = 2 AND clk.cpo_ind = 'No' THEN 'Used'
           ELSE 'Dealer'
           END                                 AS stock_type,
       to_page.web_page_type_name              as web_page_type_name_to,
       to_page.web_page_type_category          as web_page_type_category_to,
       from_page.web_page_type_name            as web_page_type_name_from,
       from_page.web_page_type_category        as web_page_type_category_from,
       -- Saved vehicle metrics
       SUM(CASE
               WHEN to_page.web_page_type_name IN
                    ('Save This Vehicle VDP Impression', 'Save This Vehicle SRP Impression')
                   AND to_date(TRIM(clk.year_month), 'yyyymm') >= LAST_DAY(ADD_MONTHS(CURRENT_DATE, -14)) + 1
                   THEN clk.clicks
               ELSE 0
           END::BIGINT)                        AS saved_vehicles,

       SUM(CASE
               WHEN to_page.web_page_type_name = 'Save This Vehicle VDP Impression'
                   AND to_date(TRIM(clk.year_month), 'yyyymm') >= LAST_DAY(ADD_MONTHS(CURRENT_DATE, -14)) + 1
                   THEN clk.clicks
               ELSE 0
           END::BIGINT)                        AS saved_vdps,

       SUM(CASE
               WHEN to_page.web_page_type_name = 'Save This Vehicle SRP Impression'
                   AND to_date(TRIM(clk.year_month), 'yyyymm') >= LAST_DAY(ADD_MONTHS(CURRENT_DATE, -14)) + 1
                   THEN clk.clicks
               ELSE 0
           END::BIGINT)                        AS saved_srps,

       -- Vehicle history report metrics
       SUM(CASE
               WHEN from_page.web_page_type_name = 'Search Results Page'
                   AND to_page.web_page_type_category = 'Vehicle History Report'
                   THEN clk.clicks
               ELSE 0
           END)                                AS srp_vehicle_history_report_clicks,

       SUM(CASE
               WHEN from_page.web_page_type_name = '2.0 More Details Page'
                   AND to_page.web_page_type_category = 'Vehicle History Report'
                   THEN clk.clicks
               ELSE 0
           END)                                AS vdp_vehicle_history_report_clicks
FROM dw_vw.click_monthly_vw AS clk
         JOIN dw_vw.web_page_type_vw AS from_page ON clk.web_page_type_from_id = from_page.web_page_type_id
         JOIN dw_vw.web_page_type_vw AS to_page ON clk.web_page_type_to_id = to_page.web_page_type_id
WHERE to_date(TRIM(clk.year_month), 'yyyymm') between LAST_DAY(ADD_MONTHS(CURRENT_DATE, -14)) + 1 and CURRENT_DATE - 1
  AND from_page.web_page_type_id IN (SELECT web_page_type_id FROM valid_from_pages)
  AND to_page.web_page_type_id IN (SELECT web_page_type_id FROM valid_to_pages)
GROUP BY 1, 2, 3, 4, 5, 6, 7
WITH NO SCHEMA BINDING
;

--View level comment
COMMENT ON VIEW bi_vw.saved_vehicles_13mo_summary IS 'This view aggregates saved vehicle SRPs and VDPs for the last 13 months.';
