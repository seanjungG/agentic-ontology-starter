-- ============================================================================
-- Retail & Commerce Domain Schema (BigQuery Compatible SQL DDL)
-- Focus: Convenience Franchise Corp Franchise Settlement & Fulfillment Logistics Fulfillment SLA
-- ============================================================================

-- 1. Store Franchise Master (Convenience Franchise Corp)
CREATE TABLE IF NOT EXISTS `retail_dw.TB_STORE_FRANCHISE` (
  store_code STRING NOT NULL,
  store_name STRING NOT NULL,
  contract_type STRING NOT NULL, -- 'GS1' (70%), 'GS2' (60%)
  owner_id STRING NOT NULL,
  open_date DATE NOT NULL,
  elec_subsidy_rate FLOAT64 NOT NULL
);

-- 2. POS Monthly Financial Summary
CREATE TABLE IF NOT EXISTS `retail_dw.TB_POS_MONTHLY` (
  settle_month STRING NOT NULL,
  store_code STRING NOT NULL,
  gross_profit INT64 NOT NULL,
  ff_waste_loss INT64 NOT NULL,
  utility_cost INT64 NOT NULL,
  order_compliance_rate FLOAT64
);

-- 3. Logistics Order & Delivery Tracking (풀필먼트)
CREATE TABLE IF NOT EXISTS `retail_dw.TB_LOGISTICS_ORDER` (
  waybill_no STRING NOT NULL,
  order_type STRING NOT NULL, -- 'TODAY_FAST', 'NEXT_DAY'
  carrier_code STRING NOT NULL,
  promise_time TIMESTAMP NOT NULL,
  actual_delivery TIMESTAMP NOT NULL,
  delivery_fee INT64 NOT NULL,
  delay_minutes INT64 NOT NULL
);

-- 4. Brand Supplier Contract Master (Olive Young)
CREATE TABLE IF NOT EXISTS `retail_dw.TB_BRAND_CONTRACT` (
  brand_code STRING NOT NULL,
  brand_name STRING NOT NULL,
  category STRING NOT NULL,
  base_commission_rate FLOAT64 NOT NULL,
  promo_share_ratio FLOAT64 NOT NULL
);
