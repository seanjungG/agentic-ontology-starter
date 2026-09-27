-- [Engine 1: BigQuery Property Graph] ISO SQL:2023 Property Graph DDL
-- Target Dataset: seanjung-poc.starter_ontology_dw (Provisioned via HashiCorp Terraform 1.8.5)
CREATE OR REPLACE PROPERTY GRAPH `seanjung-poc.starter_ontology_dw.STARTER_ONTOLOGY_GRAPH`
  NODE TABLES (
    `seanjung-poc.starter_ontology_dw.tb_customer_contract`
      KEY (contract_id)
      LABEL CustomerContractNode
      PROPERTIES (contract_id, customer_id, customer_segment, age_group, device_id, plan_id, contract_type, commitment_months, elapsed_days, granted_subsidy_krw, welfare_status, status),
    `seanjung-poc.starter_ontology_dw.tb_device_master`
      KEY (device_id)
      LABEL DeviceNode
      PROPERTIES (device_id, device_name, manufacturer, storage_gb, factory_price_krw, release_date),
    `seanjung-poc.starter_ontology_dw.tb_plan_master`
      KEY (plan_id)
      LABEL PlanNode
      PROPERTIES (plan_id, plan_name, tier_category, monthly_fee_krw, min_maintenance_days, selective_discount_rate),
    `seanjung-poc.starter_ontology_dw.tb_subsidy_policy`
      KEY (policy_id)
      LABEL SubsidyNode
      PROPERTIES (policy_id, device_id, plan_id, base_subsidy_krw, additional_subsidy_cap_krw, mandatory_retention_days, effective_from),
    `seanjung-poc.starter_ontology_dw.tb_doc_chunks`
      KEY (chunk_id)
      LABEL DocChunkNode
      PROPERTIES (chunk_id, source_file, section_title, content, content_sha256, trust_tier),
    `seanjung-poc.starter_ontology_dw.tb_domain_rules`
      KEY (rule_id)
      LABEL DomainRuleNode
      PROPERTIES (rule_id, rule_name, rule_category, condition_expr, formula_expr, source_chunk_id, description_ko)
  )
  EDGE TABLES (
    `seanjung-poc.starter_ontology_dw.edge_contract_device`
      KEY (contract_id, device_id)
      SOURCE KEY (contract_id) REFERENCES `seanjung-poc.starter_ontology_dw.tb_customer_contract` (contract_id)
      DESTINATION KEY (device_id) REFERENCES `seanjung-poc.starter_ontology_dw.tb_device_master` (device_id)
      LABEL USES_DEVICE
      PROPERTIES (contract_id, customer_id, device_id, edge_type),
    `seanjung-poc.starter_ontology_dw.edge_contract_plan`
      KEY (contract_id, plan_id)
      SOURCE KEY (contract_id) REFERENCES `seanjung-poc.starter_ontology_dw.tb_customer_contract` (contract_id)
      DESTINATION KEY (plan_id) REFERENCES `seanjung-poc.starter_ontology_dw.tb_plan_master` (plan_id)
      LABEL SUBSCRIBES_PLAN
      PROPERTIES (contract_id, customer_id, plan_id, edge_type),
    `seanjung-poc.starter_ontology_dw.edge_subsidy_binding`
      KEY (policy_id)
      SOURCE KEY (device_id) REFERENCES `seanjung-poc.starter_ontology_dw.tb_device_master` (device_id)
      DESTINATION KEY (plan_id) REFERENCES `seanjung-poc.starter_ontology_dw.tb_plan_master` (plan_id)
      LABEL HAS_SUBSIDY_POLICY
      PROPERTIES (policy_id, device_id, plan_id, total_subsidy_krw, edge_type),
    `seanjung-poc.starter_ontology_dw.edge_rule_applies_to_plan`
      KEY (edge_id)
      SOURCE KEY (rule_id) REFERENCES `seanjung-poc.starter_ontology_dw.tb_domain_rules` (rule_id)
      DESTINATION KEY (plan_id) REFERENCES `seanjung-poc.starter_ontology_dw.tb_plan_master` (plan_id)
      LABEL APPLIES_TO_PLAN
      PROPERTIES (edge_id, rule_id, plan_id, source_chunk_id, relation_label_ko, edge_type)
  );
