-- ============================================================================
-- Finance & Fintech Domain Schema (BigQuery Compatible SQL DDL)
-- Focus: KakaoBank Unattended Loan / DSR & Toss One-App Settlement
-- ============================================================================

-- 1. Customer Credit & Income Ledger
CREATE TABLE IF NOT EXISTS `finance_dw.TB_CUST_CREDIT` (
  cust_id STRING NOT NULL,
  annual_income INT64 NOT NULL,
  credit_score INT64 NOT NULL,
  existing_debt_repay INT64 NOT NULL,
  is_first_home_buyer STRING NOT NULL
);

-- 2. Loan Product Master
CREATE TABLE IF NOT EXISTS `finance_dw.TB_LOAN_PRODUCT` (
  prod_id STRING NOT NULL,
  prod_name STRING NOT NULL,
  base_rate FLOAT64 NOT NULL,
  spread_rate FLOAT64 NOT NULL,
  max_term_years INT64 NOT NULL,
  early_repay_fee_rate FLOAT64
);

-- 3. Collateral Property Valuation
CREATE TABLE IF NOT EXISTS `finance_dw.TB_COLLATERAL_VAL` (
  property_id STRING NOT NULL,
  region_tier STRING NOT NULL,
  market_price INT64 NOT NULL
);

-- 4. Merchant Payment & Settlement Ledger (Toss)
CREATE TABLE IF NOT EXISTS `finance_dw.TB_MERCHANT_SETTLE` (
  merchant_id STRING NOT NULL,
  merchant_name STRING NOT NULL,
  annual_sales_tier STRING NOT NULL,
  monthly_volume INT64 NOT NULL,
  applied_fee_rate FLOAT64 NOT NULL,
  settlement_status STRING NOT NULL
);
