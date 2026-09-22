-- BigQuery SQL:2023 Property Graph DDL Definition
-- Architecture: 2-Layer Anti-Redundancy (Zero duplicate entity storage)
CREATE OR REPLACE PROPERTY GRAPH `my-gcp-project.telecom_ontology.ENTERPRISE_SUBSIDY_GRAPH`
  NODE TABLES (
    -- [Track B & C] Structured DW Master Tables Promoted Directly to Graph Nodes
    `my-gcp-project.telecom_ontology.dw_device_master`
       KEY (device_id)
       LABEL DeviceNode
       PROPERTIES (device_id, model_code, pet_name, storage, factory_price),
    `my-gcp-project.telecom_ontology.dw_plan_master`
       KEY (plan_id)
       LABEL PlanNode
       PROPERTIES (plan_id, plan_name, network_type, monthly_fee, is_baseline_tier),
    `my-gcp-project.telecom_ontology.dw_subsidy_policy_master`
       KEY (policy_id)
       LABEL SubsidyNode
       PROPERTIES (policy_id, device_id, plan_id, basic_subsidy, distribution_subsidy),

    -- [Track A & C] Unstructured Knowledge Pruned to Legal Evidence Chunks & Business Rules
    `my-gcp-project.telecom_ontology.ont_doc_chunks`
       KEY (chunk_id)
       LABEL DocChunkNode
       PROPERTIES (chunk_id, title, hash_anchor, content),
    `my-gcp-project.telecom_ontology.ont_domain_rules`
       KEY (rule_id)
       LABEL DomainRuleNode
       PROPERTIES (rule_id, rule_name, condition_expr, penalty_action)
  )
  EDGE TABLES (
    -- Relational Foreign Key Bridges
    `my-gcp-project.telecom_ontology.dw_subsidy_policy_master`
       KEY (policy_id)
       SOURCE KEY (policy_id) REFERENCES `my-gcp-project.telecom_ontology.dw_subsidy_policy_master` (policy_id)
       DESTINATION KEY (device_id) REFERENCES `my-gcp-project.telecom_ontology.dw_device_master` (device_id)
       LABEL COVERS_DEVICE,
    `my-gcp-project.telecom_ontology.dw_subsidy_policy_master`
       KEY (policy_id)
       SOURCE KEY (policy_id) REFERENCES `my-gcp-project.telecom_ontology.dw_subsidy_policy_master` (policy_id)
       DESTINATION KEY (plan_id) REFERENCES `my-gcp-project.telecom_ontology.dw_plan_master` (plan_id)
       LABEL REQUIRES_PLAN,

    -- Semantic Cross-Domain Bridges
    `my-gcp-project.telecom_ontology.edge_rule_applies_to_plan`
       KEY (edge_id)
       SOURCE KEY (rule_id) REFERENCES `my-gcp-project.telecom_ontology.ont_domain_rules` (rule_id)
       DESTINATION KEY (plan_id) REFERENCES `my-gcp-project.telecom_ontology.dw_plan_master` (plan_id)
       LABEL APPLIES_RULE,
    `my-gcp-project.telecom_ontology.edge_rule_grounded_in_chunk`
       KEY (edge_id)
       SOURCE KEY (rule_id) REFERENCES `my-gcp-project.telecom_ontology.ont_domain_rules` (rule_id)
       DESTINATION KEY (chunk_id) REFERENCES `my-gcp-project.telecom_ontology.ont_doc_chunks` (chunk_id)
       LABEL GROUNDED_IN
  );
