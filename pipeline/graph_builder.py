# -*- coding: utf-8 -*-
"""
Pipeline Graph Builder:
Synthesizes declarative BigQuery SQL:2023 Property Graph DDL and exports
graph topology metadata with zero data duplication.
"""
import os, json

def build_graph(project_id="my-project", dataset_id="my_dataset", output_dir="data/output"):
    os.makedirs(output_dir, exist_ok=True)
    graph_name = f"`{project_id}.{dataset_id}.ENTERPRISE_SUBSIDY_GRAPH`"

    ddl = f"""-- BigQuery SQL:2023 Property Graph DDL Definition
CREATE OR REPLACE PROPERTY GRAPH {graph_name}
  NODE TABLES (
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
    `{project_id}.{dataset_id}.ont_doc_chunks`
      KEY (chunk_id)
      LABEL DocChunkNode
      PROPERTIES (chunk_id, title, hash_anchor, content)
  )
  EDGE TABLES (
    `{project_id}.{dataset_id}.dw_subsidy_policy_master`
      KEY (policy_id)
      SOURCE KEY (policy_id) REFERENCES `{project_id}.{dataset_id}.dw_subsidy_policy_master` (policy_id)
      DESTINATION KEY (device_id) REFERENCES `{project_id}.{dataset_id}.dw_device_master` (device_id)
      LABEL COVERS_DEVICE,
    `{project_id}.{dataset_id}.dw_subsidy_policy_master`
      KEY (policy_id)
      SOURCE KEY (policy_id) REFERENCES `{project_id}.{dataset_id}.dw_subsidy_policy_master` (policy_id)
      DESTINATION KEY (plan_id) REFERENCES `{project_id}.{dataset_id}.dw_plan_master` (plan_id)
      LABEL REQUIRES_PLAN
  );
"""
    ddl_path = os.path.join(output_dir, "create_property_graph.sql")
    with open(ddl_path, "w", encoding="utf-8") as f:
        f.write(ddl)

    topology = {
        "graph_name": f"{project_id}.{dataset_id}.ENTERPRISE_SUBSIDY_GRAPH",
        "node_tables": ["DeviceNode", "PlanNode", "SubsidyNode", "DocChunkNode"],
        "edge_tables": ["COVERS_DEVICE", "REQUIRES_PLAN"],
        "semantic_bridges": [
            {"from": "SubsidyNode", "edge": "COVERS_DEVICE", "to": "DeviceNode"},
            {"from": "SubsidyNode", "edge": "REQUIRES_PLAN", "to": "PlanNode"}
        ]
    }
    topo_path = os.path.join(output_dir, "graph_topology.json")
    with open(topo_path, "w", encoding="utf-8") as f:
        json.dump(topology, f, ensure_ascii=False, indent=2)

    print(f"[GRAPH BUILDER SUCCESS] DDL generated -> {ddl_path}, Topology -> {topo_path}")
    return topology

if __name__ == "__main__":
    build_graph()
