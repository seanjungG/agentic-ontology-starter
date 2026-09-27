-- [Engine 2: Cloud Spanner Graph] ISO GQL Property Graph Schema & DDL
-- Architecture: Low-Latency Online Graph Traversal on Cloud Spanner
CREATE TABLE dw_device_master (
  device_id STRING(64) NOT NULL,
  model_code STRING(64),
  pet_name STRING(128),
  storage STRING(32),
  factory_price INT64
) PRIMARY KEY (device_id);

CREATE TABLE dw_plan_master (
  plan_id STRING(64) NOT NULL,
  plan_name STRING(128),
  network_type STRING(32),
  monthly_fee INT64,
  is_baseline_tier BOOL
) PRIMARY KEY (plan_id);

CREATE TABLE dw_subsidy_policy_master (
  policy_id STRING(64) NOT NULL,
  device_id STRING(64) NOT NULL,
  plan_id STRING(64) NOT NULL,
  basic_subsidy INT64,
  distribution_subsidy INT64
) PRIMARY KEY (policy_id);

CREATE TABLE dw_customer_contract (
  contract_id STRING(64) NOT NULL,
  customer_id STRING(64) NOT NULL,
  customer_segment STRING(64),
  device_id STRING(64) NOT NULL,
  plan_id STRING(64) NOT NULL,
  policy_id STRING(64) NOT NULL,
  contract_type STRING(64),
  elapsed_days INT64,
  welfare_status STRING(64)
) PRIMARY KEY (contract_id);

CREATE TABLE ont_doc_chunks (
  chunk_id STRING(64) NOT NULL,
  title STRING(256),
  hash_anchor STRING(64),
  content STRING(MAX)
) PRIMARY KEY (chunk_id);

CREATE TABLE ont_domain_rules (
  rule_id STRING(64) NOT NULL,
  rule_name STRING(256),
  condition_expr STRING(MAX),
  penalty_action STRING(MAX)
) PRIMARY KEY (rule_id);

CREATE OR REPLACE PROPERTY GRAPH EnterpriseSubsidyGraph
  NODE TABLES (
    dw_customer_contract KEY (contract_id) LABEL CustomerContractNode,
    dw_device_master KEY (device_id) LABEL DeviceNode,
    dw_plan_master KEY (plan_id) LABEL PlanNode,
    dw_subsidy_policy_master KEY (policy_id) LABEL SubsidyNode,
    ont_doc_chunks KEY (chunk_id) LABEL DocChunkNode,
    ont_domain_rules KEY (rule_id) LABEL DomainRuleNode
  )
  EDGE TABLES (
    dw_customer_contract AS EdgeContractPlan
      KEY (contract_id)
      SOURCE KEY (contract_id) REFERENCES dw_customer_contract (contract_id)
      DESTINATION KEY (plan_id) REFERENCES dw_plan_master (plan_id)
      LABEL SUBSCRIBES_PLAN,
    dw_subsidy_policy_master AS EdgeSubsidyDevice
      KEY (policy_id)
      SOURCE KEY (policy_id) REFERENCES dw_subsidy_policy_master (policy_id)
      DESTINATION KEY (device_id) REFERENCES dw_device_master (device_id)
      LABEL COVERS_DEVICE,
    dw_subsidy_policy_master AS EdgeSubsidyPlan
      KEY (policy_id)
      SOURCE KEY (policy_id) REFERENCES dw_subsidy_policy_master (policy_id)
      DESTINATION KEY (plan_id) REFERENCES dw_plan_master (plan_id)
      LABEL REQUIRES_PLAN
  );
