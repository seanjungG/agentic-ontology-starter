-- Master Data Warehouse Table Definitions
CREATE TABLE IF NOT EXISTS dw_device_master (
    device_id STRING,
    model_code STRING,
    pet_name STRING,
    storage STRING,
    factory_price INT64
);

CREATE TABLE IF NOT EXISTS dw_plan_master (
    plan_id STRING,
    plan_name STRING,
    network_type STRING,
    monthly_fee INT64,
    is_baseline_tier BOOL
);

CREATE TABLE IF NOT EXISTS dw_subsidy_policy_master (
    policy_id STRING,
    device_id STRING,
    plan_id STRING,
    basic_subsidy INT64,
    distribution_subsidy INT64,
    effective_start_date DATE,
    effective_end_date DATE
);
