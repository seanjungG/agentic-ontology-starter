-- [Engine 2: Cloud Spanner Graph] ISO GQL Property Graph Schema & DDL
-- Architecture: Low-Latency Online Graph Traversal on Cloud Spanner
CREATE TABLE tb_device_master (
  device_id STRING(64) NOT NULL,
  device_name STRING(128),
  manufacturer STRING(64),
  storage_gb INT64,
  factory_price_krw INT64,
  release_date STRING(32)
) PRIMARY KEY (device_id);

CREATE TABLE tb_plan_master (
  plan_id STRING(64) NOT NULL,
  plan_name STRING(128),
  tier_category STRING(64),
  monthly_fee_krw INT64,
  min_maintenance_days INT64,
  selective_discount_rate FLOAT64
) PRIMARY KEY (plan_id);

CREATE TABLE tb_subsidy_policy (
  policy_id STRING(64) NOT NULL,
  device_id STRING(64) NOT NULL,
  plan_id STRING(64) NOT NULL,
  base_subsidy_krw INT64,
  additional_subsidy_cap_krw INT64,
  mandatory_retention_days INT64
) PRIMARY KEY (policy_id);

CREATE TABLE tb_customer_contract (
  contract_id STRING(64) NOT NULL,
  customer_id STRING(64) NOT NULL,
  customer_segment STRING(64),
  device_id STRING(64) NOT NULL,
  plan_id STRING(64) NOT NULL,
  contract_type STRING(64),
  elapsed_days INT64,
  granted_subsidy_krw INT64,
  welfare_status STRING(64)
) PRIMARY KEY (contract_id);

CREATE TABLE tb_domain_rules (
  rule_id STRING(64) NOT NULL,
  rule_name STRING(256),
  rule_category STRING(64),
  condition_expr STRING(MAX),
  formula_expr STRING(MAX),
  source_chunk_id STRING(64)
) PRIMARY KEY (rule_id);

CREATE OR REPLACE PROPERTY GRAPH StarterOntologyGraph
  NODE TABLES (
    tb_customer_contract KEY (contract_id) LABEL CustomerContractNode,
    tb_device_master KEY (device_id) LABEL DeviceNode,
    tb_plan_master KEY (plan_id) LABEL PlanNode,
    tb_subsidy_policy KEY (policy_id) LABEL SubsidyNode,
    tb_domain_rules KEY (rule_id) LABEL DomainRuleNode
  )
  EDGE TABLES (
    tb_customer_contract AS EdgeContractDevice
      KEY (contract_id)
      SOURCE KEY (contract_id) REFERENCES tb_customer_contract (contract_id)
      DESTINATION KEY (device_id) REFERENCES tb_device_master (device_id)
      LABEL USES_DEVICE,
    tb_customer_contract AS EdgeContractPlan
      KEY (contract_id)
      SOURCE KEY (contract_id) REFERENCES tb_customer_contract (contract_id)
      DESTINATION KEY (plan_id) REFERENCES tb_plan_master (plan_id)
      LABEL SUBSCRIBES_PLAN,
    tb_subsidy_policy AS EdgeSubsidyBinding
      KEY (policy_id)
      SOURCE KEY (device_id) REFERENCES tb_device_master (device_id)
      DESTINATION KEY (plan_id) REFERENCES tb_plan_master (plan_id)
      LABEL HAS_SUBSIDY_POLICY
  );
