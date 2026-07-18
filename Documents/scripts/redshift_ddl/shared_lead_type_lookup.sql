DROP VIEW IF EXISTS bi_vw.shared_lead_type_lookup;

CREATE VIEW bi_vw.shared_lead_type_lookup AS
SELECT lead_type_id,
       lead_type_name,
       lead_type_category,
    CASE
        WHEN lead_type_name = 'Used Car E-Mail Quote (Employee)' THEN 'Used Salesperson Connect'
        WHEN lead_type_name = 'New Car E-Mail Quote (Employee)' THEN 'New Salesperson Connect'
        WHEN lead_type_name = 'Non-Inventory E-Mail Quote (Employee)' THEN 'Salesperson Connect'
        WHEN lead_type_name = 'More Details Page Browser Print' THEN 'VDP Print'
        WHEN lead_type_name = 'New Online Shopper Submission' THEN 'New Online Shopper'
        WHEN lead_type_name = 'Used Online Shopper Submission' THEN 'Used Online Shopper'
        WHEN lead_type_name = 'Used Car E-Mail Quote' THEN 'Used Car Email Lead'
        WHEN lead_type_name IN ('New Car E-Mail Quote (Inventory)','New Car E-Mail Quote (Non-Config)') THEN 'New Car Email Lead'
        WHEN lead_type_name = 'Driving Directions Page Views' THEN 'Directions'
        WHEN lead_type_name = 'Map to Dealership' THEN 'Maps'
        WHEN lead_type_name = 'New Car Toll Free Lead' THEN 'New Car Phone Lead'
        WHEN lead_type_name = 'Used Car Toll Free Lead' THEN 'Used Car Phone Lead'
        WHEN lead_type_name = 'Service Toll Free Lead' THEN 'Service Phone Lead'
        WHEN lead_type_name = 'Deep Link VDP Website Transfer' THEN 'VDP Deep Link'
        WHEN lead_type_name = 'Visit Dealer Service Website' THEN 'Service Website Transfer'
        WHEN lead_type_name = 'Visit the Dealer Website' THEN 'Dealer Website Transfer'
        WHEN lead_type_name = 'Inventory Ad Dealer Hyperlink' THEN 'Inventory Ad Dealer Hyperlink'
        WHEN lead_type_name = 'Clicklane Website Transfer' THEN 'Clicklane Website Transfer'
        WHEN lead_type_name = 'Walk In Distinct Visitor' THEN 'Walk In'
        WHEN lead_type_name = 'Instant Offer Submission' THEN 'Instant Offer - Cars.com'
        WHEN lead_type_id = 129 THEN 'New Car Email Lead' --New Car Meta Lead Gen Offsite
        WHEN lead_type_id = 130 THEN 'Used Car Email Lead' --Used Car Meta Lead Gen Offsite
    ELSE lead_type_name END AS lead_type_name_label,
    CASE
        WHEN lead_type_category IN ('Driving Directions','Email This Page','Map to Dealership','Print Vehicle Details') THEN 'Other (map view, vdp print)'
        WHEN lead_type_category IN ('New Car E-Mail Lead','Non-Inventory Email Lead','Online Shopper','Used Car E-Mail Lead','Sell Email Lead','Instant Offer Lead') THEN 'Email Lead'
        WHEN lead_type_category IN ('New Car Chat Lead','Used Car Chat Lead') THEN 'Chat Lead'
        WHEN lead_type_category IN ('New Car Toll Free Lead','Service Toll Free Lead','Used Car Toll Free Lead') THEN 'Phone Lead'
        WHEN lead_type_category IN ('Used Car Chat Event','New Car Chat Event') THEN 'Chat Event'
        WHEN lead_type_category IN ('Visit Dealer Website','Inventory Ads') THEN 'Web Transfer'
        WHEN lead_type_category = 'Walk In' THEN 'Walk In'
        ELSE 'Other'
    END AS lead_type_group
    FROM dw_vw.lead_type_vw

;



-- View Level Comment
COMMENT ON VIEW bi_vw.shared_lead_type_lookup IS 'Shared logic for standardizing Lead Types for BI reporting. Source: dw_vw.lead_type_vw';
-- Column Level Comments
COMMENT ON COLUMN bi_vw.shared_lead_type_lookup.lead_type_id IS 'Data Warehouse surrogate key to identify the lead type';
COMMENT ON COLUMN bi_vw.shared_lead_type_lookup.lead_type_name IS 'CARS standardized version of lead type name.';
COMMENT ON COLUMN bi_vw.shared_lead_type_lookup.lead_type_category IS 'Lead type category from the source systemEx: used car Toll Free Lead, Visit Dealer Website';
COMMENT ON COLUMN bi_vw.shared_lead_type_lookup.lead_type_name_label IS 'BI reporting standardized version of lead type name.Ex: Used Car Email Lead, New Car Email Lead';
COMMENT ON COLUMN bi_vw.shared_lead_type_lookup.lead_type_group IS 'BI reporting grouping for lead types.Ex: Email Lead, Phone Lead, Web Transfer';
