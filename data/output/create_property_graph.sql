-- [Engine 1: BigQuery Property Graph] ISO SQL:2023 Property Graph DDL
-- Architecture: Zero-ETL Direct Table Projection (0 Duplicate Entity Rows)
CREATE OR REPLACE PROPERTY GRAPH `my-project.my_dataset.ENTERPRISE_SUBSIDY_GRAPH`
  NODE TABLES (
    -- [Structured DW Master Ledgers]
    `my-project.my_dataset.dw_customer_contract`
       KEY (contract_id)
       LABEL CustomerContractNode
       PROPERTIES (contract_id, customer_id, customer_segment, device_id, plan_id, policy_id, contract_type, elapsed_days, welfare_status),
    `my-project.my_dataset.dw_device_master`
       KEY (device_id)
       LABEL DeviceNode
       PROPERTIES (device_id, model_code, pet_name, storage, factory_price),
    `my-project.my_dataset.dw_plan_master`
       KEY (plan_id)
       LABEL PlanNode
       PROPERTIES (plan_id, plan_name, network_type, monthly_fee, is_baseline_tier),
    `my-project.my_dataset.dw_subsidy_policy_master`
       KEY (policy_id)
       LABEL SubsidyNode
       PROPERTIES (policy_id, device_id, plan_id, basic_subsidy, distribution_subsidy),

    -- [Unstructured OKF v0.2 Knowledge Chunks & Codified Rules]
    `my-project.my_dataset.ont_doc_chunks`
       KEY (chunk_id)
       LABEL DocChunkNode
       PROPERTIES (chunk_id, title, hash_anchor, content),
    `my-project.my_dataset.ont_domain_rules`
       KEY (rule_id)
       LABEL DomainRuleNode
       PROPERTIES (rule_id, rule_name, condition_expr, penalty_action)
  )
  EDGE TABLES (
    -- [Relational Foreign Key Bridges]
    `my-project.my_dataset.dw_customer_contract` AS edge_contract_plan
       KEY (contract_id)
       SOURCE KEY (contract_id) REFERENCES `my-project.my_dataset.dw_customer_contract` (contract_id)
       DESTINATION KEY (plan_id) REFERENCES `my-project.my_dataset.dw_plan_master` (plan_id)
       LABEL SUBSCRIBES_PLAN,
    `my-project.my_dataset.dw_customer_contract` AS edge_contract_policy
       KEY (contract_id)
       SOURCE KEY (contract_id) REFERENCES `my-project.my_dataset.dw_customer_contract` (contract_id)
       DESTINATION KEY (policy_id) REFERENCES `my-project.my_dataset.dw_subsidy_policy_master` (policy_id)
       LABEL BOUND_TO_POLICY,
    `my-project.my_dataset.dw_subsidy_policy_master` AS edge_subsidy_device
       KEY (policy_id)
       SOURCE KEY (policy_id) REFERENCES `my-project.my_dataset.dw_subsidy_policy_master` (policy_id)
       DESTINATION KEY (device_id) REFERENCES `my-project.my_dataset.dw_device_master` (device_id)
       LABEL COVERS_DEVICE,
    `my-project.my_dataset.dw_subsidy_policy_master` AS edge_subsidy_plan
       KEY (policy_id)
       SOURCE KEY (policy_id) REFERENCES `my-project.my_dataset.dw_subsidy_policy_master` (policy_id)
       DESTINATION KEY (plan_id) REFERENCES `my-project.my_dataset.dw_plan_master` (plan_id)
       LABEL REQUIRES_PLAN,

    -- [Semantic Cross-Domain Bridges]
    `my-project.my_dataset.edge_rule_applies_to_plan`
       KEY (edge_id)
       SOURCE KEY (rule_id) REFERENCES `my-project.my_dataset.ont_domain_rules` (rule_id)
       DESTINATION KEY (plan_id) REFERENCES `my-project.my_dataset.dw_plan_master` (plan_id)
       LABEL APPLIES_RULE,
    `my-project.my_dataset.edge_rule_grounded_in_chunk`
       KEY (edge_id)
       SOURCE KEY (rule_id) REFERENCES `my-project.my_dataset.ont_domain_rules` (rule_id)
       DESTINATION KEY (chunk_id) REFERENCES `my-project.my_dataset.ont_doc_chunks` (chunk_id)
       LABEL GROUNDED_IN
  );
