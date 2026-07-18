DROP VIEW IF EXISTS bi_vw.current_inventory_13mo_detail;

CREATE VIEW bi_vw.current_inventory_13mo_detail AS
WITH Last_Vehicle_Records AS (
    SELECT
        veh.customer_id,
        veh.vehicle_id,
        veh.listing_id,
        veh.vin,
        veh.dealer_stock_num,
        CASE
            WHEN veh.classified_ad_status_id = 0 THEN 'Yes'
            ELSE 'No'
        END AS listed_on_site,
        veh.video_ind,
        COALESCE(veh.transmission,
            CASE
                WHEN veh.original_transmission = '-' THEN NULL
                ELSE veh.original_transmission
            END, 'Unknown'
        ) AS transmission,
        COALESCE(veh.engine,
            CASE
                WHEN veh.original_engine = '-' THEN NULL
                ELSE veh.original_engine
            END, 'Unknown'
        ) AS engine,
        COALESCE(veh.interior_color,
            CASE
                WHEN veh.original_interior_color = '-' THEN NULL
                ELSE veh.original_interior_color
            END, 'Unknown'
        ) AS interior_color,
        COALESCE(veh.exterior_color,
            CASE
                WHEN veh.original_exterior_color = '-' THEN NULL
                ELSE veh.original_exterior_color
            END, 'Unknown'
        ) AS exterior_color,
        veh.door_count,
        COALESCE(veh.drivetrain,
            CASE
                WHEN veh.original_drivetrain = '-' THEN NULL
                ELSE veh.original_drivetrain
            END, 'Unknown'
        ) AS drivetrain,
        COALESCE(veh.fuel_type,
            CASE
                WHEN veh.original_fuel_type = '-' THEN NULL
                ELSE veh.original_fuel_type
            END, 'Unknown'
        ) AS fuel_type,
        COALESCE(
            CASE WHEN tr.trim_name = 'Unknown' THEN NULL ELSE tr.trim_name END,
            CASE WHEN veh.original_trim = '-' THEN NULL ELSE veh.original_trim END,
            'Unknown'
        ) AS trim_name,
        veh.make_id,
        veh.make_model_id,
        veh.trim_id,
        veh.original_trim,
        veh.model_year_id,
        veh.cpo_ind,
        veh.bodystyle_id,
        veh.stock_type_id,
        CASE WHEN veh.make_id <> '0' THEN 1 ELSE 0 END AS make_ind,
        CASE WHEN veh.make_model_id <> '0' THEN 1 ELSE 0 END AS model_ind,
        CASE WHEN veh.model_year_id <> '0' THEN 1 ELSE 0 END AS model_year_ind,
        CASE WHEN veh.bodystyle_id <> '0' THEN 1 ELSE 0 END AS bodystyle_ind,
        CASE WHEN COALESCE(veh.door_count, 0) <> 0 THEN 1 ELSE 0 END AS door_count_ind,
        CASE
            WHEN COALESCE(veh.engine, CASE WHEN veh.original_engine = '-' THEN NULL ELSE veh.original_engine END, '0') <> '0' THEN 1
            ELSE 0
        END AS engine_ind,
        CASE
            WHEN COALESCE(veh.exterior_color, CASE WHEN veh.original_exterior_color = '-' THEN NULL ELSE veh.original_exterior_color END, '0') <> '0' THEN 1
            ELSE 0
        END AS exterior_color_ind,
        CASE
            WHEN COALESCE(veh.interior_color, CASE WHEN veh.original_interior_color = '-' THEN NULL ELSE veh.original_interior_color END, '0') <> '0' THEN 1
            ELSE 0
        END AS interior_color_ind,
        CASE
            WHEN COALESCE(veh.transmission, CASE WHEN veh.original_transmission = '-' THEN NULL ELSE veh.original_transmission END, '0') <> '0' THEN 1
            ELSE 0
        END AS transmission_ind,
        CASE
            WHEN COALESCE(veh.drivetrain, CASE WHEN original_drivetrain = '-' THEN NULL ELSE veh.original_drivetrain END, '0') <> '0' THEN 1
            ELSE 0
        END AS drivetrain_ind,
        CASE
            WHEN COALESCE(veh.fuel_type, CASE WHEN original_fuel_type = '-' THEN NULL ELSE veh.original_fuel_type END, '0') <> '0' THEN 1
            ELSE 0
        END AS fuel_type_ind,
        CASE WHEN COALESCE(veh.wheelbase, 0) <> 0 THEN 1 ELSE 0 END AS wheelbase_ind,
        CASE
            WHEN veh.stock_type_id = 1 AND COALESCE(veh.price, 0) = 0 AND COALESCE(veh.msrp, '0') = 0 THEN 0
            WHEN veh.stock_type_id = 2 AND COALESCE(veh.price, 0) = 0 THEN 0
            ELSE 1
        END AS price_ind,
        CASE WHEN COALESCE(veh.standard_feature, '') <> '' THEN 1 ELSE 0 END AS standard_ind,
        CASE
            WHEN veh.mileage IS NULL THEN 0
            WHEN veh.mileage = 0 AND veh.stock_type_id = 2 THEN 0
            ELSE 1
        END AS mileage_ind,
        CASE
            WHEN veh.trim_id = 0 AND (veh.original_trim IS NULL OR veh.original_trim = '-') THEN 0
            ELSE 1
        END AS trim_ind,
        CASE WHEN veh.seller_note_ind = 'Yes' THEN 1 ELSE 0 END AS seller_note_ind,
        CASE WHEN COALESCE(veh.photo_count, 0) <> 0 THEN 1 ELSE 0 END AS photo_ind,
        veh.price::FLOAT AS price,
        CASE WHEN veh.stock_type_id = 1 THEN veh.msrp::FLOAT END AS msrp,
        veh.mileage::BIGINT AS mileage,
        veh.photo_count::BIGINT AS photo_cnt,
        veh.days_live
    FROM dw_vw.vehicle_vw veh
    JOIN dw_vw.vehicle_trim_vw tr ON veh.trim_id = tr.trim_id
    WHERE veh.src_remove_date IS NULL
      AND veh.classified_ad_status_id = 0
)

    SELECT
        CURRENT_DATE AS run_date,
        customer_id,
        vehicle_id,
        listing_id,
        vin,
        dealer_stock_num AS stock_num,
        listed_on_site,
        video_ind,
        transmission,
        engine,
        interior_color,
        exterior_color,
        door_count,
        drivetrain,
        fuel_type,
        CASE WHEN standard_ind = 1 THEN 'Yes' ELSE 'No' END AS standard_feature_ind,
        CASE WHEN mileage_ind = 1 THEN 'Yes' ELSE 'No' END AS mileage_ind,
        CASE WHEN price_ind = 1 THEN 'Yes' ELSE 'No' END AS price_ind,
        CASE WHEN photo_ind = 1 THEN 'Yes' ELSE 'No' END AS photo_ind,
        CASE WHEN seller_note_ind = 1 THEN 'Yes' ELSE 'No' END AS seller_notes_ind,
        cpo_ind,
        make_id,
        make_model_id,
        trim_name,
        model_year_id,
        bodystyle_id,
        stock_type_id,
        CASE
            WHEN stock_type_id = 1 THEN 'New'
            WHEN stock_type_id = 2 AND cpo_ind = 'No' THEN 'Used'
            WHEN stock_type_id = 2 AND cpo_ind = 'Yes' THEN 'CPO'
            ELSE 'Unknown'
        END AS stock_type,
        COALESCE(price, msrp, 0) AS price,
        COALESCE(mileage, 0) AS mileage,
        COALESCE(photo_cnt, 0) AS photo_cnt,
        days_live,
        (
            make_ind + model_ind + model_year_ind + bodystyle_ind + door_count_ind +
            engine_ind + exterior_color_ind + interior_color_ind + transmission_ind +
            fuel_type_ind + price_ind + standard_ind + COALESCE(mileage_ind, 0) +
            trim_ind + seller_note_ind + photo_ind
        ) AS completeness,
        TRIM(TRAILING ',' FROM
            CASE WHEN COALESCE(mileage_ind, 0) = 0 THEN 'mileage,' ELSE '' END ||
            CASE WHEN price_ind = 0 THEN 'price,' ELSE '' END ||
            CASE WHEN photo_ind = 0 THEN 'photos,' ELSE '' END ||
            CASE WHEN seller_note_ind = 0 THEN 'seller notes,' ELSE '' END ||
            CASE WHEN make_ind = 0 THEN 'make,' ELSE '' END ||
            CASE WHEN model_ind = 0 THEN 'model,' ELSE '' END ||
            CASE WHEN model_year_ind = 0 THEN 'year,' ELSE '' END ||
            CASE WHEN bodystyle_ind = 0 THEN 'bodystyle,' ELSE '' END ||
            CASE WHEN door_count_ind = 0 THEN 'door count,' ELSE '' END ||
            CASE WHEN engine_ind = 0 THEN 'engine,' ELSE '' END ||
            CASE WHEN exterior_color_ind = 0 THEN 'exterior color,' ELSE '' END ||
            CASE WHEN interior_color_ind = 0 THEN 'interior color,' ELSE '' END ||
            CASE WHEN transmission_ind = 0 THEN 'transmission,' ELSE '' END ||
            CASE WHEN fuel_type_ind = 0 THEN 'fuel type,' ELSE '' END ||
            CASE WHEN standard_ind = 0 THEN 'standard features,' ELSE '' END ||
            CASE WHEN trim_ind = 0 THEN 'trim,' ELSE '' END
        ) AS missing_merchandising
    FROM Last_Vehicle_Records
;


-- View Level Comment
COMMENT ON VIEW bi_vw.current_inventory_13mo_detail IS 'Dealer inventory on the site as of today. It also includes the missing merchandising information.';
-- Column Level Comments
COMMENT ON COLUMN bi_vw.current_inventory_13mo_detail.run_date IS 'System date of the run';
COMMENT ON COLUMN bi_vw.current_inventory_13mo_detail.customer_id IS 'Data Warehouse surrogate key to identify the listing vehicle which can be displayed on cars.com by customer(dealer/user).';
COMMENT ON COLUMN bi_vw.current_inventory_13mo_detail.vehicle_id IS 'Data Warehouse surrogate key to identify the listing vehicle which can be displayed on cars.com by customer(dealer/user).';
COMMENT ON COLUMN bi_vw.current_inventory_13mo_detail.listing_id IS 'Listing ID';
COMMENT ON COLUMN bi_vw.current_inventory_13mo_detail.vin IS 'A vehicle identification number (VIN) (also called a chassis number or frame number) is a unique code, including a serial number to identify specific automobile of the listing vehicle';
COMMENT ON COLUMN bi_vw.current_inventory_13mo_detail.stock_num IS 'Dealer stock number';
COMMENT ON COLUMN bi_vw.current_inventory_13mo_detail.listed_on_site IS 'Yes if the vehicle is listed on the site';
COMMENT ON COLUMN bi_vw.current_inventory_13mo_detail.video_ind IS 'Yes if the vehicle has a video';
COMMENT ON COLUMN bi_vw.current_inventory_13mo_detail.transmission IS 'CARS normalized transmission type';
COMMENT ON COLUMN bi_vw.current_inventory_13mo_detail.engine IS 'Engine type';
COMMENT ON COLUMN bi_vw.current_inventory_13mo_detail.interior_color IS 'Interior color';
COMMENT ON COLUMN bi_vw.current_inventory_13mo_detail.exterior_color IS 'Exterior color';
COMMENT ON COLUMN bi_vw.current_inventory_13mo_detail.door_count IS 'Number of doors of the listing vehicle';
COMMENT ON COLUMN bi_vw.current_inventory_13mo_detail.drivetrain IS 'CARS normalized drivetrain type';
COMMENT ON COLUMN bi_vw.current_inventory_13mo_detail.fuel_type IS 'Fuel type';
COMMENT ON COLUMN bi_vw.current_inventory_13mo_detail.standard_feature_ind IS 'Yes if the vehicle has standard features';
COMMENT ON COLUMN bi_vw.current_inventory_13mo_detail.mileage_ind IS 'Yes if the vehicle has mileage';
COMMENT ON COLUMN bi_vw.current_inventory_13mo_detail.price_ind IS 'Yes if the vehicle has price';
COMMENT ON COLUMN bi_vw.current_inventory_13mo_detail.photo_ind IS 'Yes if the vehicle has photos';
COMMENT ON COLUMN bi_vw.current_inventory_13mo_detail.seller_notes_ind IS 'Yes if the vehicle has seller notes';
COMMENT ON COLUMN bi_vw.current_inventory_13mo_detail.cpo_ind IS 'An indicator to know whether the listing vehicle is certified pre owned or not';
COMMENT ON COLUMN bi_vw.current_inventory_13mo_detail.make_id IS 'Data Warehouse surrogate key which Identifies the CARS normalized make';
COMMENT ON COLUMN bi_vw.current_inventory_13mo_detail.make_model_id IS 'Data Warehouse surrogate key which Identifies the CARS normalized make model';
COMMENT ON COLUMN bi_vw.current_inventory_13mo_detail.trim_name IS 'Trim name';
COMMENT ON COLUMN bi_vw.current_inventory_13mo_detail.model_year_id IS 'Data Warehouse surrogate key which Identifies the CARS normalized model and year';
COMMENT ON COLUMN bi_vw.current_inventory_13mo_detail.bodystyle_id IS 'Data Warehouse surrogate key which Identifies the CARS normalized bodystyle';
COMMENT ON COLUMN bi_vw.current_inventory_13mo_detail.stock_type IS 'Stock type';
COMMENT ON COLUMN bi_vw.current_inventory_13mo_detail.price IS 'Price';
COMMENT ON COLUMN bi_vw.current_inventory_13mo_detail.mileage IS 'Mileage';
COMMENT ON COLUMN bi_vw.current_inventory_13mo_detail.photo_cnt IS 'Number of photos';
COMMENT ON COLUMN bi_vw.current_inventory_13mo_detail.days_live IS 'Number of days the vehicle is on the site';
COMMENT ON COLUMN bi_vw.current_inventory_13mo_detail.completeness IS 'Completeness score';
COMMENT ON COLUMN bi_vw.current_inventory_13mo_detail.missing_merchandising IS 'Missing merchandising information';
