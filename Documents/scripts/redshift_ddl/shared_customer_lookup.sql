DROP VIEW IF EXISTS bi_vw.shared_customer_lookup;

CREATE VIEW bi_vw.shared_customer_lookup AS
SELECT cus.customer_id                                     AS customer_id,
       cus.legacy_id                                       AS dealer_id,
       cus.uuid                                            AS DealerUUID,
       cus.customer_name                                   AS dealer_name,
       cus.franchise_independent,
       maj.legacy_id                                       AS maj_dealer_id,
       maj.uuid                                            AS MajDealerUUID,
       maj.customer_name                                   AS maj_dealer_name,
       grp.legacy_id                                       AS grp_dealer_id,
       grp.uuid                                            AS GrpDealerUUID,
       grp.customer_name                                   AS grp_dealer_name,
       CASE
           WHEN cus.ultimate_parent_customer_legacy_id IS NULL AND cus.customer_type_name = 'Group' THEN cus.legacy_id
           ELSE cus.ultimate_parent_customer_legacy_id END AS di_group_dealer_id,
       CASE
           WHEN cus.ultimate_parent_customer_legacy_id IS NULL AND cus.customer_type_name = 'Group'
               THEN cus.customer_name_internal
           ELSE cus.ultimate_parent_customer_name END      AS di_group_dealer_name,
       cus.dma_code,
       COALESCE(cus.dma_market_name, 'Unknown')            AS dma_market_name,
       cus.postal_code
FROM dw_vw.customer_vw cus
         INNER JOIN dw_vw.major_account_vw maj ON cus.major_acct_customer_id = maj.customer_id
         INNER JOIN dw_vw.dealer_group_vw grp ON cus.dealer_grp_customer_id = grp.customer_id
with no schema binding
;


-- View Level Comment
COMMENT ON VIEW bi_vw.shared_customer_lookup IS 'Shared logic for standardizing dealer IDs and names for BI reporting. Source: dw_vw.customer_vw, dw_vw.major_account_vw, dw_vw.dealer_group_vw ';
