-- ============================================================================
-- Telecommunications Domain Schema (BigQuery Compatible SQL DDL)
-- Focus: Mobile Carrier A Subscription / Penalty & 유무선 통신사 B Combined Bundle / SLA
-- ============================================================================

-- 1. Subscriber Line Status Master
CREATE TABLE IF NOT EXISTS `telecom_dw.TB_LINE_STATUS` (
  line_no STRING NOT NULL,
  plan_code STRING NOT NULL,
  join_date DATE NOT NULL,
  elapsed_days INT64 NOT NULL,
  subsidy_received INT64 NOT NULL,
  cust_age INT64 NOT NULL
);

-- 2. Plan Tier Catalog
CREATE TABLE IF NOT EXISTS `telecom_dw.TB_PLAN_TIER` (
  plan_code STRING NOT NULL,
  plan_name STRING NOT NULL,
  monthly_fee INT64 NOT NULL,
  subsidy_amount INT64 NOT NULL,
  is_safe_lower_bound STRING NOT NULL
);

-- 3. 유무선 통신사 B Bundle Group Master
CREATE TABLE IF NOT EXISTS `telecom_dw.TB_KT_BUNDLE_GROUP` (
  bundle_id STRING NOT NULL,
  bundle_type STRING NOT NULL,
  internet_circuit_id STRING NOT NULL,
  mobile_count INT64 NOT NULL,
  total_mobile_fee INT64 NOT NULL,
  internet_discount INT64 NOT NULL,
  mobile_total_discount INT64 NOT NULL
);

-- 4. B2B Enterprise Circuit SLA Monitoring
CREATE TABLE IF NOT EXISTS `telecom_dw.TB_KT_B2B_CIRCUIT` (
  circuit_id STRING NOT NULL,
  customer_name STRING NOT NULL,
  monthly_fee INT64 NOT NULL,
  sla_target_rate FLOAT64 NOT NULL,
  outage_minutes INT64 NOT NULL,
  billing_month STRING NOT NULL
);
