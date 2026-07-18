DROP VIEW IF EXISTS bi_vw.vehicle_metrics_monthly_13mo_summary;

CREATE VIEW bi_vw.vehicle_metrics_monthly_13mo_summary AS
select --finding the SRPs and VDPs for each vehicle from agg vehicle monthly
  to_date(trim(agg.year_month),'yyyymm') as first_date_of_month,
  customer_id,
  case when agg.stock_type_id = 1 then 'New'
       when agg.stock_type_id = 2 and agg.cpo_ind = 'No' then 'Used'
       when agg.stock_type_id = 2 and agg.cpo_ind = 'Yes' then 'CPO'
       else 'Dealer' end as stock_type,
  sum(agg.vdp_imp+agg.llp_imp) as vdps,
  sum(agg.srp_imp) as srps
from
  dw_vw.agg_vehicle_metric_monthly_vw agg
WHERE
  to_date(trim(agg.year_month),'yyyymm')between LAST_DAY(ADD_MONTHS(CURRENT_DATE, -14)) + 1 and CURRENT_DATE-1
group by
  1,2,3
WITH NO SCHEMA BINDING
;

--View level comment
COMMENT ON VIEW bi_vw.vehicle_metrics_monthly_13mo_summary IS 'This view is used to pull the SRPs and VDPs from agg vehicle monthly by month, customer, and stock type';
