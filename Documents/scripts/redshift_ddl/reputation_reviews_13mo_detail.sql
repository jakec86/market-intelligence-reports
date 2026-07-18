DROP VIEW IF EXISTS bi_vw.reputation_reviews_13mo_detail;

CREATE VIEW bi_vw.reputation_reviews_13mo_detail AS

--Reputation Reviews 13Mo Detail
WITH base_reviews as (
select
    review_submit_date::date as review_submit_date,
    customer_id,
    source,
    src_dealer_review_id,
    shop_new_ind,
    shop_used_ind,
    service_repair_ind,
    display_name,
    review_title,
    review_text,
    rating_overall,
    count(dealer_review_id) as review_cnt
from
    dw_vw.dealer_review_vw
where
    review_submit_date between last_day(add_months(current_date,-14)) + 1 and current_date -1
    and dealer_review_status_desc = 'Approved'
    and sales_person_review_ind = 'No'
    and active_ind = 'Yes'
group by
    1,2,3,4,5,6,7,8,9,10,11),

base_responses as (
select a.*
from (
    select
        src_dealer_review_id,
        response_submit_date::date as response_submit_date,
        response_text,
        row_number() over (partition by dealer_review_id order by update_date desc) as row_num
    from
        dw_vw.dealer_review_response_vw a
    where
        response_submit_date between last_day(add_months(current_date,-14)) + 1 and current_date -1) a
where a.row_num = 1)

select
    current_date::DATE as run_date,
    rev.review_submit_date,
    cus.dealer_id,
    cus.dealer_name,
    cus.franchise_independent as franchise_independent,
    cus.maj_dealer_id,
    cus.maj_dealer_name,
    cus.grp_dealer_id,
    cus.grp_dealer_name,
    cus.dma_code,
    cus.dma_market_name,
    rev.source,
    rev.src_dealer_review_id,
    rev.shop_new_ind,
    rev.shop_used_ind,
    rev.service_repair_ind,
    rev.display_name,
    rev.review_title,
    rev.review_text,
    rev.rating_overall,
    coalesce(resp.response_text,'') as response_text,
    resp.response_submit_date,
    case when resp.response_submit_date is null then 'No' else 'Yes' end as response_ind,
    review_cnt
from
    base_reviews rev
    join bi_vw.dltl_shared_customer_map cus on rev.customer_id = cus.customer_id
    left join base_responses resp on rev.src_dealer_review_id = resp.src_dealer_review_id
WITH NO SCHEMA BINDING
;

COMMENT ON VIEW bi_vw.reputation_reviews_13mo_detail IS 'Shows all dealer reviews and responses for a given dealer by source and review status.';
