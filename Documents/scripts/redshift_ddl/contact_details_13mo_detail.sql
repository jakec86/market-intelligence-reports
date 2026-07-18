DROP VIEW IF EXISTS bi_vw.contact_details_13mo_detail;

CREATE VIEW bi_vw.contact_details_13mo_detail AS
---contact details 13Mo details
With leads AS (select ld.submitted_date_time,
                      ld.customer_id,
                      ld.lead_id,
                      ld.vehicle_id,
                      ld.stock_type_id,
                      ld.cpo_ind,
                      ld.sponsored_type,
                      case
                          when aff.apn = 'fbooksocial2' and ld.lead_type_id = 12 and
                               (utm_medium <> 'leadgen' or utm_medium is null) then cast(9998 as smallint)
                          when aff.apn = 'fbooksocial2' and ld.lead_type_id = 15 and
                               (utm_medium <> 'leadgen' or utm_medium is null) then cast(9997 as smallint)
                          when ld.lead_type_id = 120 and finance_application_current_status = 'credit app'
                              then cast(9996 as smallint)
                          when ld.lead_type_id = 120 and finance_application_current_status = 'prequalified'
                              then cast(9995 as smallint)
                          when ld.lead_type_id = 120 and finance_application_current_status = 'finance intent'
                              then cast(9994 as smallint)
                          else ld.lead_type_id end                                      as lead_type_id,
                      ld.make_model_id,
                      ld.model_year_id,
                      ld.source_common_name,
                      ld.mobile_ind,
                      aff.apn,
                      aff.branding_name,
                      ld.consumer_name,
                      ld.consumer_email,
                      ld.consumer_city,
                      ld.consumer_state,
                      ld.consumer_zip_code_id,
                      ld.campaign_name,
                      ld.customer_employee_id,
                      replace(translate(ld.caller_phone, '()-', ''), ' ', '')           as caller_phone,
                      replace(translate(ld.consumer_day_phone, '()-', ''), ' ', '')     as consumer_day_phone,
                      replace(translate(ld.consumer_evening_phone, '()-', ''), ' ', '') as consumer_evening_phone,
                      ld.call_duration,
                      ld.call_disposition,
                      ld.chat_handled_by,
                      ld.chat_msg_length,
                      ld.audio_url,
                      split_part(ld.message, '        Give us feedback!       ', 1)     as message,
                      ld.chat_transcript_id,
                      ld.sent_to_dealer_crm,
                      src_lead_id,
                      trade_in_ind,
                      coalesce(ld.trade_in_year || ' ' || ld.trade_in_make || ' ' || ld.trade_in_model,
                               '')                                                      as vehicle_interest
                       ,
                      coalesce(ld.vin, '')                                              as vin,
                      coalesce((ld.price), 0)                                           as price,
                      src_shipping_cost
               from dw_vw.lead_vw ld
                        left join dw_vw.affiliate_vw aff on aff.affiliate_id = ld.front_door_affiliate_id
               where DATE(date_id) between DATEADD('month', -13, DATE_TRUNC('month', current_date)) and current_date - 1
                 and submitted_date_time is not null
                 and lead_id <> 0
                 and lead_type_id not in ('0', '25', '104'))

select current_date                                                as run_date,
       to_char(ld.submitted_date_time, 'yyyy-mm-dd hh12:mi:ss am') as submitted_date_time,
       ld.submitted_date_time::date                                as date_id,
       cus.dealer_id                                               as dealer_id,
       cus.dealerUUID                                              as dealerUUID,
       cus.dealer_name                                             as dealer_name,
       cus.franchise_independent,
       cus.maj_dealer_id                                           as maj_dealer_id,
       cus.maj_dealer_name                                         as maj_dealer_name,
       cus.grp_dealer_id                                           as grp_dealer_id,
       cus.grp_dealer_name                                         as grp_dealer_name,
       ld.campaign_name,
       ld.sponsored_type,
       cus.dma_code,
       cus.dma_market_name,
       ld.lead_id,
       CASE
           WHEN ld.lead_type_id IN (9997, 9998, 9999, 9996, 9995, 9994) THEN 'Email Lead'
           ELSE ltv.lead_type_group
           END                                                     AS lead_type_group,
       CASE
           WHEN ld.lead_type_id = 9997 THEN 'New Car Email-Social'
           WHEN ld.lead_type_id = 9998 THEN 'Used Car Email-Social'
           WHEN ld.lead_type_id = 9999 THEN 'NLP Email'
           WHEN ld.lead_type_id = 9996 THEN 'Email - Credit Application'
           WHEN ld.lead_type_id = 9995 THEN 'Email - Prequalified'
           WHEN ld.lead_type_id = 9994 THEN 'Email - Finance Intent'
           ELSE ltv.lead_type_name_label END                       AS lead_type_name,
       case
           when ld.stock_type_id = 1 then 'New'
           when ld.stock_type_id = 2 and ld.cpo_ind = 'No' then 'Used'
           when ld.stock_type_id = 2 and ld.cpo_ind = 'Yes' then 'CPO'
           else 'Dealer' end                                       as stock_type,
       coalesce(dealer_stock_num, '')                              as dealer_stock_num,
       case
           when mmy.model_year = '0' then ''
           else mmy.model_year || ' ' || coalesce(mmv.make_name, veh.original_make) || ' ' ||
                coalesce(mmv.model_name, veh.original_model) end   as ymm,
       ld.apn,
       ld.branding_name,
       ld.source_common_name,
       ld.mobile_ind,
       ld.customer_employee_id,
       coalesce(ld.consumer_name, '')                              as consumer_name,
       coalesce(ld.consumer_email, '')                             as consumer_email,
       coalesce(ld.consumer_city, '')                              as consumer_city,
       coalesce(ld.consumer_state, '')                             as consumer_state,
       coalesce(left(ld.consumer_zip_code_id, 5), '')              as consumer_zip,
       coalesce(ld.caller_phone, ld.consumer_day_phone, ld.consumer_evening_phone,
                '')                                                as caller_phone,
       call_duration,
       coalesce(initcap(call_disposition), '')                     as call_disposition,
       coalesce(audio_url, '')                                     as audio_url,
       coalesce(chat_handled_by, '')                               as chat_handled_by,
       chat_msg_length,
       replace(coalesce(message, ''), 'NonePurchase', 'Purchase')  as message,
       chat_transcript_id,
       Case
           when chat_transcript is not null then 1
           else 0
           end                                                     as chattranscript,
       ld.sent_to_dealer_crm,
       ld.trade_in_ind,
       ld.vehicle_interest,
       upper(coalesce(veh.vin, ld.vin, ''))                        as vin,
       coalesce(case
                    when veh.src_remove_date is null and veh.classified_ad_status_id = 0 then 'Y'
                    else 'N' end,
                '')                                                as listed_on_site,
       coalesce(cast(ld.price as bigint), 0)                       as price,
       src_shipping_cost,
       count(ld.lead_id)                                           as total
from leads ld
         left join bi_vw.dltl_shared_lead_type_map ltv on ld.lead_type_id = ltv.lead_type_id
         inner join dw_vw.vehicle_vw veh on ld.vehicle_id = veh.vehicle_id
         inner join bi_vw.dltl_shared_customer_map cus on ld.customer_id = cus.customer_id
         left join enrich.di_chat_lead_enrich enc on ld.chat_transcript_id = enc.src_chat_transcript_id
         inner join dw_vw.make_model_vw mmv on ld.make_model_id = mmv.make_model_id
         inner join dw_vw.model_year_vw mmy on ld.model_year_id = mmy.model_year_id
--left join dw_vw.accutrade_appraisal_vw ac on ld.src_lead_id=ac.src_origin_offer_code and ld.customer_id=ac.customer_id and ld.submitted_date_time=ac.submitted_date_time
where cus.franchise_independent <> 'Syco'
  and ltv.lead_type_group <> 'Other'
group by 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26,
         27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47
with no schema binding
;


-- View Level Comment
COMMENT ON VIEW bi_vw.contact_details_13mo_detail IS 'Each record represents an individual lead and all of its related details. For example, the date the lead was submitted, the lead type, the consumer’s contact information (name, phone, email, etc.), and the specific vehicle and dealer that generated the lead. Includes leads NOT sent to the dealer’s CRM – use the sent_to_crm dimension to filter.';

