DROP VIEW IF EXISTS bi_vw.listings_optimizer_prvday_detail;
CREATE VIEW bi_vw.listings_optimizer_prvday_detail AS

WITH Last_Vehicle_Records AS (
select
    veh.customer_id,
    veh.vehicle_id,
    veh.listing_id,
    veh.vin,
    veh.dealer_stock_num,
    case when veh.classified_ad_status_id = 0 then 'Yes' else 'No' end as listed_on_site,
    veh.video_ind,
    veh.transmission,
    veh.original_transmission,
    veh.engine,
    veh.original_engine,
    veh.interior_color,
    veh.exterior_color,
    veh.original_exterior_color,
    veh.original_interior_color,
    veh.door_count,
    veh.drivetrain,
    veh.original_drivetrain,
    veh.fuel_type,
    veh.original_fuel_type,
    veh.make_id,
    veh.make_model_id,
    veh.trim_id,
    veh.original_trim,
    veh.model_year_id,
    veh.cpo_ind,
    veh.bodystyle_id,
    veh.stock_type_id,
    case when dealer_vehicle_url is null then 'N' else 'Y' end as deep_link_ind,
    case when veh.make_id <> '0' then 1 else 0 end make_ind,
    case when veh.make_model_id <> '0' then 1 else 0 end model_ind,
    case when veh.model_year_id <> '0' then 1 else 0 end model_year_ind,
    case when veh.bodystyle_id <> '0' then 1 else 0 end bodystyle_ind,
    case when coalesce(veh.door_count,0) <> 0 then 1 else 0 end door_count_ind,
    case when coalesce(veh.engine,case when veh.original_engine = '-' then null else veh.original_engine end,'0') <> '0' then 1 else 0 end engine_ind,
    case when coalesce(veh.exterior_color, case when veh.original_exterior_color = '-' then null else veh.original_exterior_color end, '0') <> '0' then 1 else 0 end exterior_color_ind,
    case when coalesce(veh.interior_color,case when veh.original_interior_color='-' then null else veh.original_interior_color end,'0') <> '0' then 1 else 0 end interior_color_ind,
    case when coalesce(veh.transmission,case when veh.original_transmission='-' then null else veh.original_transmission end,'0') <> '0' then 1 else 0 end transmission_ind,
    case when coalesce(veh.drivetrain,case when original_drivetrain='-' then null else veh.original_drivetrain end,'0') <> '0' then 1 else 0 end drivetrain_ind,
    case when coalesce(veh.fuel_type,case when original_fuel_type='-' then null else veh.original_fuel_type end,'0') <> '0' then 1 else 0 end fuel_type_ind,
    case when coalesce(veh.wheelbase,0) <> 0 then 1 else 0 end wheelbase_ind,
    case when veh.stock_type_id = 1 and coalesce(veh.price,0) = 0  and coalesce(veh.msrp,'0') = 0 then 0
       when veh.stock_type_id = 2 and coalesce(veh.price,0) = 0  then 0
       else 1 end price_ind,
    case when coalesce(veh.standard_feature,'') <> '' then 1 else 0 end standard_ind,
    case when veh.stock_type_id = 1 then 1
       when (veh.mileage = 0 or veh.mileage is null) and veh.stock_type_id = 2 then 0 else 1 end mileage_ind,
    case when veh.trim_id = 0 and (veh.original_trim is null or veh.original_trim = '-') then 0 else 1 end trim_ind,
    case when veh.seller_note_ind = 'Yes' then 1 else 0 end as seller_note_ind,
    case when coalesce(veh.photo_count,0) <> 0 then 1 else 0 end as photo_ind,
    veh.price::float as price,
    case when veh.stock_type_id = 1 then veh.msrp::float end as msrp,
    veh.mileage::bigint as mileage,
    veh.photo_count::bigint as photo_cnt,
    veh.days_live
from
    dw_vw.vehicle_vw veh
where
    veh.src_remove_date is null
    and veh.classified_ad_status_id = 0
    and veh.src_add_date::date < current_date
),

--Current Inventory
Current_Inventory AS(
select
    current_date as run_date,
    a.customer_id,
    a.vehicle_id,
    a.listing_id,
    a.vin,
    a.dealer_stock_num as stock_num,
    a.listed_on_site,
    a.video_ind,
    a.deep_link_ind,
    coalesce(a.transmission,case when a.original_transmission='-' then null else a.original_transmission end,'Unknown') as transmission,
    coalesce(a.engine,case when a.original_engine='-' then null else a.original_engine end,'Unknown') as engine,
    coalesce(a.interior_color,case when a.original_interior_color='-' then null else a.original_interior_color end ,'Unknown') as interior_color,
    coalesce(a.exterior_color,case when a.original_exterior_color='-' then null else a.original_exterior_color end,'Unknown') as exterior_color,
    a.door_count,
    coalesce(a.drivetrain,case when a.original_drivetrain = '-' then null else a.original_drivetrain end,'Unknown') as drivetrain,
    coalesce(a.fuel_type,case when a.original_fuel_type = '-' then null else a.original_fuel_type end,'Unknown') as fuel_type,
    case when a.standard_ind = 1 then 'Yes' else 'No' end as standard_feature_ind,
    case when a.mileage_ind = 1 then 'Yes' else 'No' end as mileage_ind,
    case when a.price_ind = 1 then 'Yes' else 'No' end as price_ind,
    case when a.photo_ind = 1 then 'Yes' else 'No' end as photo_ind,
    case when a.seller_note_ind = 1 then 'Yes' else 'No' end as seller_notes_ind,
    a.cpo_ind,
    a.make_id,
    a.make_model_id,
    coalesce(case when tr.trim_name = 'Unknown' then null else tr.trim_name end,case when a.original_trim = '-' then null else a.original_trim end,'Unknown') as trim_name,
    a.model_year_id,
    a.bodystyle_id,
    a.stock_type_id,
    case when a.stock_type_id = 1 then 'New'
        when a.stock_type_id = 2 and a.cpo_ind = 'No' then 'Used'
        when a.stock_type_id = 2 and a.cpo_ind = 'Yes' then 'CPO'
        else 'Unknown' end as stock_type,
    coalesce(a.price,a.msrp,0) as price,
    coalesce(a.mileage,0) as mileage,
    coalesce(a.photo_cnt,0) as photo_cnt,
    a.days_live,
    a.make_ind+a.model_ind+a.model_year_ind+a.bodystyle_ind+a.door_count_ind+a.engine_ind+a.exterior_color_ind+a.interior_color_ind+a.transmission_ind+
        a.fuel_type_ind+a.price_ind+a.standard_ind+coalesce(a.mileage_ind,0)+a.trim_ind+a.seller_note_ind+a.photo_ind as completeness,
    trim(trailing ',' from case when coalesce(a.mileage_ind,0)=0 then 'mileage,' else '' end||case when a.price_ind=0 then 'price,' else '' end||
          case when a.photo_ind=0 then 'photos,' else '' end||case when a.seller_note_ind=0 then 'seller notes,' else '' end||case when a.make_ind=0 then 'make,' else '' end||
          case when a.model_ind=0 then 'model,' else '' end||case when a.model_year_ind=0 then 'year,' else '' end||case when a.bodystyle_ind=0 then 'bodystyle,' else '' end||
          case when a.door_count_ind=0 then 'door count,' else '' end|| case when a.engine_ind=0 then 'engine,' else '' end||case when a.exterior_color_ind=0 then 'exterior color,' else '' end||
          case when a.interior_color_ind=0 then 'interior color,' else '' end||case when a.transmission_ind=0 then 'transmission,' else '' end||
          case when a.fuel_type_ind=0 then 'fuel type,' else '' end|| case when a.standard_ind=0 then 'standard features,' else '' end||
          case when a.trim_ind=0 then 'trim,' else '' end) as missing_merchandising
from
    Last_Vehicle_Records a
    JOIN dw_vw.vehicle_trim_vw tr on a.trim_id=tr.trim_id
),

--hot car
--Finding the most recent record for each vehicle_id
Hot_Car AS(
select hot.* from
    (select
    vehicle_id,
    case when pred_hot = 1 then 'Hot'
        else '' end as hot_car_badge,
    row_number() over (partition by vehicle_id order by filedate desc) as row_num
    from insight.hot_car_badgingv2
    where filedate >= current_date -3
    ) hot
where row_num = 1),

--leads
Leads AS(
select
    ld.customer_id,
    ld.vehicle_id,
    count(ld.lead_id) as leads,
    count(case when date_id between current_date -7 and current_date -1 then ld.lead_id end) as leads_07_days,
    count(case when date_id between current_date -30 and current_date -1 then ld.lead_id end) as leads_30_days
from
    dw_vw.lead_vw ld
where
    ld.lead_type_id <> 25
    and ld.date_id between last_day(add_months(current_date,-14)) + 1 and current_date -1
group by
    1,2
),

--Saved Vehicles base data pull, imp_daily union all click_daily
Saved_Vehicles AS(
select
    customer_id as dealer_customer_id,
    vehicle_id as vehicle_id,
    sum(clicks::bigint) as saved_vehicles,
    sum(cast(case when date_id between current_date -7 and current_date -1 then clicks end as bigint)) as saved_vehicles_07_days,
    sum(cast(case when date_id between current_date -30 and current_date -1 then clicks end as bigint)) as saved_vehicles_30_days
from
    dw_vw.click_daily_vw
    join dw_vw.web_page_type_vw on (click_daily_vw.web_page_type_to_id = web_page_type_vw.web_page_type_id)
where
    date_id between last_day(add_months(current_date,-14)) + 1 and current_date -1
    and web_page_type_name in ('Save This Vehicle VDP Impression', 'Save This Vehicle SRP Impression')
group by
    1,2
),

--VDP's, SRP's
VDP_SRP AS(
select
    vehicle_id,
    customer_id,
    sum(vdp_imp+llp_imp) as vdp_imps,
    sum(srp_imp) as srp_imps,
    sum(nlp_email_lead) as nlp_leads,
    sum(case when date_id between current_date -7 and current_date -1 then vdp_imp+llp_imp end) as vdp_imps_07_days,
    sum(case when date_id between current_date -7 and current_date -1 then srp_imp end) as srp_imps_07_days,
    sum(case when date_id between current_date -7 and current_date -1 then nlp_email_lead end) as nlp_07_days,
    sum(case when date_id between current_date -30 and current_date -1 then vdp_imp+llp_imp end) as vdp_imps_30_days,
    sum(case when date_id between current_date -30 and current_date -1 then srp_imp end) as srp_imps_30_days,
    sum(case when date_id between current_date -30 and current_date -1 then nlp_email_lead end) as nlp_30_days
from
    dw_vw.agg_vehicle_metric_daily_vw
where
    date_id between last_day(add_months(current_date,-14)) + 1 and current_date -1
group by
    1,2 ),

--price badge
Price_Badge AS (
select lst.*
from
    (select
        vehicle_id,
        price_badge,
        pred_price as predicted_price,
        per_pred_price_diff,
        pred_price_diff,
        good_threshold,
        great_threshold,
        case
            when price_badge is null and notes = '' and notes_internal ilike '%percent price difference outside bounds%' then 'price +/- 25% of pred price'
            when price_badge is null and notes = '' and notes_internal ilike '%mileage under min%' then 'mileage under min'
            when notes = ' ' then '' else split_part(notes, ':', 1) end as price_badge_notes_trunc,
        row_number() over (partition by vehicle_id order by filedate desc) as row_num
    from
        insight.price_badge_v2 prb
    where filedate >= current_date -3
    ) lst
where row_num = 1
)

SELECT
    ci.completeness, ci.cpo_ind, ci.days_live, ci.door_count, ci.drivetrain, ci.engine,
    ci.exterior_color, ci.fuel_type, ci.interior_color, ci.listed_on_site, ci.listing_id,
    ci.mileage, ci.mileage_ind,ci.missing_merchandising,ci.photo_ind, ci.deep_link_ind,
    ci.photo_cnt, ci.price_ind,ci.run_date, ci.seller_notes_ind,ci.standard_feature_ind,
    ci.stock_num, ci.stock_type_id, ci.stock_type, ci.transmission,
    ci.vehicle_id, ci.video_ind, ci.vin, ci.trim_name,cus.dealer_id, cus.dealer_name,
    cus.franchise_independent,cus.grp_dealer_id,cus.grp_dealer_name, cus.maj_dealer_id, cus.maj_dealer_name,
    cus.postal_code,cus.dma_code, cus.dma_market_name,make.make_name,model.model_name,
    year.model_year,lead.leads_07_days,lead.leads_30_days, lead.leads,coalesce(sv.saved_vehicles,0) as saved_vehicles,
    sv.saved_vehicles_07_days,sv.saved_vehicles_30_days,vdp.srp_imps,vdp.srp_imps_07_days,vdp.srp_imps_30_days,
    vdp.vdp_imps,vdp.vdp_imps_07_days,vdp.vdp_imps_30_days,vdp.nlp_leads,vdp.nlp_07_days, vdp.nlp_30_days,
    ci.price, hc.hot_car_badge,pb.good_threshold,pb.great_threshold,pb.predicted_price, 
    coalesce(pb.price_badge_notes_trunc,'') as price_badge_notes_trunc,
    case
        when (ci.stock_type in ('Used','CPO') and pb.per_pred_price_diff <= -25) then 'Overpriced'
        when (ci.stock_type in ('Used','CPO') and pb.per_pred_price_diff >= -25 and pb.price_badge = 'FAIR') then 'Fair'
        when (ci.stock_type in ('Used','CPO') and pb.price_badge = 'GOOD') then 'Good'
        when (ci.stock_type in ('Used','CPO') and pb.price_badge ='GREAT') then 'Great'
        when (ci.stock_type in ('Used','CPO') and pb.per_pred_price_diff >= 25) then 'Underpriced'
        when (ci.stock_type in ('Used','CPO') and pb.price_badge IS NULL) then 'None'
        else '' end as price_badge
from
    current_inventory ci
    join dw_vw.make_vw make on ci.make_id = make.make_id
    join dw_vw.make_model_vw model on ci.make_model_id = model.make_model_id
    join dw_vw.model_year_vw year on ci.model_year_id = year.model_year_id
    join bi_vw.shared_customer_lookup cus on ci.customer_id = cus.customer_id
    left join leads lead on ci.vehicle_id = lead.vehicle_id and ci.customer_id = lead.customer_id
    left join saved_vehicles sv on ci.customer_id = sv.dealer_customer_id and ci.vehicle_id = sv.vehicle_id
    left join vdp_srp vdp on ci.customer_id = vdp.customer_id and ci.vehicle_id = vdp.vehicle_id
    left join price_badge pb on ci.vehicle_id = pb.vehicle_id
    left join hot_car hc on ci.vehicle_id = hc.vehicle_id
where
    cus.franchise_independent != 'Syco'
with no schema binding;

-- View Level Comment
COMMENT ON VIEW bi_vw.listings_optimizer_prvday_detail IS 'All vehicles curreently listed on the Cars website by dealer. Data is by VIN and dealer, and includes stock type, YMMT, merchandising completeness, price badging, etc.'
