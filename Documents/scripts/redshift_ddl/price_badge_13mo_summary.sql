DROP VIEW IF EXISTS bi_vw.price_badge_13mo_summary;

CREATE VIEW bi_vw.price_badge_13mo_summary AS
WITH filtered_badges AS (SELECT date_trunc('month', bdg.filedate::date)::date as first_date_of_month,
                                bdg.filedate,
                                bdg.customer_id,
                                bdg.vehicle_id,
                                inv.new_used_ind,
                                inv.cpoind,
                                CASE
                                    WHEN bdg.per_pred_price_diff <= -25 THEN 'OVERPRICED'
                                    WHEN bdg.per_pred_price_diff >= 25 THEN 'UNDERPRICED'
                                    WHEN bdg.price_badge is null THEN 'UNBADGED'
                                    ELSE bdg.price_badge
                                    END                                       AS price_badge,
                                bdg.pred_price                                as predicted_price,
                                bdg.per_pred_price_diff,
                                bdg.pred_price_diff,
                                bdg.good_threshold,
                                bdg.great_threshold,
                                case
                                    when bdg.price_badge is null and notes = '' and
                                         notes_internal ilike '%percent price difference outside bounds%'
                                        then 'price +/- 25% of pred price'
                                    when bdg.price_badge is null and notes = '' and
                                         notes_internal ilike '%mileage under min%' then 'mileage under min'
                                    when notes = ' ' then ''
                                    else split_part(notes, ':', 1) end        as price_badge_notes_trunc,
                                ROW_NUMBER() OVER (
                                    PARTITION BY bdg.customer_id, first_date_of_month, bdg.vehicle_id
                                    ORDER BY bdg.filedate DESC
                                    )                                         AS row_rank
                         FROM insight.price_badge_v2 bdg
                                  join insight.inventory_activity inv
                                       on bdg.vehicle_id = inv.vehicle_id and bdg.filedate = inv.filedate
                         WHERE bdg.filedate BETWEEN LAST_DAY(ADD_MONTHS(CURRENT_DATE, -14)) + 1 and CURRENT_DATE - 1
                           and inv.filedate BETWEEN LAST_DAY(ADD_MONTHS(CURRENT_DATE, -14)) + 1 and CURRENT_DATE - 1
                           AND bdg.customer_id != '0')

SELECT fb.first_date_of_month,
       fb.customer_id,
       CASE
           WHEN fb.new_used_ind = 'New' THEN 'New'
           WHEN fb.new_used_ind = 'Used' AND fb.cpoind = 'Yes' THEN 'CPO'
           WHEN fb.new_used_ind = 'Used' AND fb.cpoind = 'No' THEN 'Used'
           ELSE 'Dealer'
           END                                                                AS stock_type,
       fb.price_badge,
       fb.price_badge_notes_trunc,
       COUNT(CASE WHEN fb.price_badge = 'GREAT' THEN fb.vehicle_id END)       AS great_badge_count,
       COUNT(CASE WHEN fb.price_badge = 'GOOD' THEN fb.vehicle_id END)        AS good_badge_count,
       COUNT(CASE WHEN fb.price_badge = 'FAIR' THEN fb.vehicle_id END)        AS fair_badge_count,
       COUNT(CASE WHEN fb.price_badge = 'OVERPRICED' THEN fb.vehicle_id END)  AS overpriced_count,
       COUNT(CASE WHEN fb.price_badge = 'UNDERPRICED' THEN fb.vehicle_id END) AS underpriced_count,
       COUNT(CASE WHEN fb.price_badge = 'UNBADGED' THEN fb.vehicle_id END)    AS unbadged_count
FROM filtered_badges fb
WHERE row_rank = 1
GROUP BY 1, 2, 3, 4, 5
WITH NO SCHEMA BINDING
;

--View level comment
COMMENT ON VIEW bi_vw.price_badge_13mo_summary IS 'Price badge activity for the last 13 months for BI reporting';
