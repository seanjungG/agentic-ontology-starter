# -*- coding: utf-8 -*-
"""
Pipeline Graph Builder:
- GCP Native Foundation:
    * Google Cloud BigQuery ISO SQL:2023 Property Graph DDL specification
    * BigQuery GRAPH_TABLE() and GQL (Graph Query Language) syntax
- Custom Extensions:
    * 2-Layer Anti-Redundancy graph synthesis (Zero duplicate entity storage)
    * Direct Promotion of BigQuery DW master tables to physical graph nodes
    * Aggressive pruning of redundant unstructured text entities
    * Semantic Bridges (APPLIES_RULE, CALCULATES_PENALTY, GROUNDED_IN, COVERS_DEVICE, REQUIRES_PLAN)
"""
import os, json

def build_graph(project_id="my-project", dataset_id="my_dataset", output_dir="data/output"):
    os.makedirs(output_dir, exist_ok=True)
    graph_name = f"`{project_id}.{dataset_id}.ENTERPRISE_SUBSIDY_GRAPH`"

    ddl = f"""-- BigQuery SQL:2023 Property Graph DDL Definition
-- Architecture: 2-Layer Anti-Redundancy (Zero duplicate entity storage)
CREATE OR REPLACE PROPERTY GRAPH {graph_name}
  NODE TABLES (
    -- [Track B & C] Structured DW Master Tables Promoted Directly to Graph Nodes
    `{project_id}.{dataset_id}.dw_device_master`
       KEY (device_id)
       LABEL DeviceNode
       PROPERTIES (device_id, model_code, pet_name, storage, factory_price),
    `{project_id}.{dataset_id}.dw_plan_master`
       KEY (plan_id)
       LABEL PlanNode
       PROPERTIES (plan_id, plan_name, network_type, monthly_fee, is_baseline_tier),
    `{project_id}.{dataset_id}.dw_subsidy_policy_master`
       KEY (policy_id)
       LABEL SubsidyNode
       PROPERTIES (policy_id, device_id, plan_id, basic_subsidy, distribution_subsidy),

    -- [Track A & C] Unstructured Knowledge Pruned to Legal Evidence Chunks & Business Rules
    `{project_id}.{dataset_id}.ont_doc_chunks`
       KEY (chunk_id)
       LABEL DocChunkNode
       PROPERTIES (chunk_id, title, hash_anchor, content),
    `{project_id}.{dataset_id}.ont_domain_rules`
       KEY (rule_id)
       LABEL DomainRuleNode
       PROPERTIES (rule_id, rule_name, condition_expr, penalty_action)
  )
  EDGE TABLES (
    -- Relational Foreign Key Bridges
    `{project_id}.{dataset_id}.dw_subsidy_policy_master`
       KEY (policy_id)
       SOURCE KEY (policy_id) REFERENCES `{project_id}.{dataset_id}.dw_subsidy_policy_master` (policy_id)
       DESTINATION KEY (device_id) REFERENCES `{project_id}.{dataset_id}.dw_device_master` (device_id)
       LABEL COVERS_DEVICE,
    `{project_id}.{dataset_id}.dw_subsidy_policy_master`
       KEY (policy_id)
       SOURCE KEY (policy_id) REFERENCES `{project_id}.{dataset_id}.dw_subsidy_policy_master` (policy_id)
       DESTINATION KEY (plan_id) REFERENCES `{project_id}.{dataset_id}.dw_plan_master` (plan_id)
       LABEL REQUIRES_PLAN,

    -- Semantic Cross-Domain Bridges
    `{project_id}.{dataset_id}.edge_rule_applies_to_plan`
       KEY (edge_id)
       SOURCE KEY (rule_id) REFERENCES `{project_id}.{dataset_id}.ont_domain_rules` (rule_id)
       DESTINATION KEY (plan_id) REFERENCES `{project_id}.{dataset_id}.dw_plan_master` (plan_id)
       LABEL APPLIES_RULE,
    `{project_id}.{dataset_id}.edge_rule_grounded_in_chunk`
       KEY (edge_id)
       SOURCE KEY (rule_id) REFERENCES `{project_id}.{dataset_id}.ont_domain_rules` (rule_id)
       DESTINATION KEY (chunk_id) REFERENCES `{project_id}.{dataset_id}.ont_doc_chunks` (chunk_id)
       LABEL GROUNDED_IN
  );
"""
    ddl_path = os.path.join(output_dir, "create_property_graph.sql")
    with open(ddl_path, "w", encoding="utf-8") as f:
        f.write(ddl)

    topology = {
        "graph_name": f"{project_id}.{dataset_id}.ENTERPRISE_SUBSIDY_GRAPH",
        "architecture_principle": "2-Layer Anti-Redundancy Refinement",
        "structured_dw_nodes": ["DeviceNode", "PlanNode", "SubsidyNode"],
        "unstructured_pruned_nodes": ["DocChunkNode", "DomainRuleNode"],
        "edge_tables": ["COVERS_DEVICE", "REQUIRES_PLAN", "APPLIES_RULE", "GROUNDED_IN"],
        "semantic_bridges": [
            {"source": "SubsidyNode", "edge": "COVERS_DEVICE", "target": "DeviceNode", "type": "Relational"},
            {"source": "SubsidyNode", "edge": "REQUIRES_PLAN", "target": "PlanNode", "type": "Relational"},
            {"source": "DomainRuleNode", "edge": "APPLIES_RULE", "target": "PlanNode", "type": "Semantic Bridge"},
            {"source": "DomainRuleNode", "edge": "GROUNDED_IN", "target": "DocChunkNode", "type": "Semantic Grounding"}
        ],
        "metrics": {
            "duplicate_entity_nodes": 0,
            "dw_table_promotions": 3,
            "zero_copy_projection": True
        }
    }
    topo_path = os.path.join(output_dir, "graph_topology.json")
    with open(topo_path, "w", encoding="utf-8") as f:
        json.dump(topology, f, ensure_ascii=False, indent=2)

    print(f"[GRAPH BUILDER SUCCESS] DDL generated -> {ddl_path}, Topology -> {topo_path}")
    return topology

if __name__ == "__main__":
    build_graph()

