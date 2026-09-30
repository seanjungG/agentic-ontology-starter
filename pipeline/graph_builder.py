# Copyright (c) 2026 Sean Jung (seanjung@google.com). All Rights Reserved.
# Non-Commercial Use Only: Methodology & Docs under CC BY-NC-ND 4.0; Source Code under PolyForm Noncommercial License 1.0.0.
# Commercial use, paid consulting/SI/PoC delivery, or production deployment requires prior written permission from seanjung@google.com.

# -*- coding: utf-8 -*-
"""
Pipeline Graph Builder (Real BigQuery Property Graph, Cloud Spanner Graph & Graph Fabric Federation):
- Synthesizes and EXECUTES the real BigQuery ISO SQL:2023 Property Graph DDL:
  `CREATE OR REPLACE PROPERTY GRAPH seanjung-poc.starter_ontology_dw.STARTER_ONTOLOGY_GRAPH`
- Synthesizes and EXECUTES the real Cloud Spanner Graph ISO GQL DDL (`create_spanner_graph.sql`)
  when `graph_engine` is `"spanner"` or `"both"`
- Benchmarks p50/p95 multi-hop GQL traversal latency across BigQuery and Cloud Spanner
- Executes live Graph Fabric federation (`EXTERNAL_QUERY`) joining Spanner Graph traversal with BigQuery chunks
- Produces `graph_topology.json` with `TASK-093` & `TASK-108` compliant Semantic & Property Graph definitions
"""

import json
import os
import sys

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_ROOT = os.environ.get("STARTER_PROJECT_ROOT", BASE_DIR)  # project data root (run_pipeline.py --project)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from src.gcp_client import (
    DEFAULT_BQ_SPANNER_CONN,
    DEFAULT_DATASET_ID,
    DEFAULT_LOCATION,
    DEFAULT_PROJECT_ID,
    DEFAULT_SPANNER_DATABASE,
    DEFAULT_SPANNER_INSTANCE,
    check_spanner_available,
    execute_bq_sql,
    execute_spanner_ddl,
    execute_spanner_sql,
)


def _percentile(sorted_vals: list, pct: float) -> float:
    if not sorted_vals:
        return 0.0
    idx = min(len(sorted_vals) - 1, max(0, int(round((pct / 100.0) * (len(sorted_vals) - 1)))))
    return round(float(sorted_vals[idx]), 2)


def build_graph(
    project_id: str = DEFAULT_PROJECT_ID,
    dataset_id: str = DEFAULT_DATASET_ID,
    output_dir: str = "data/output",
    deploy_live_bq: bool = True,
    benchmark_runs: int = 5,
):
    from src.project_context import project_for_root
    try:
        project = project_for_root(DATA_ROOT)
    except Exception:
        project = {}
    graph_engine = project.get("graph_engine") or os.environ.get("GRAPH_ENGINE_MODE") or "bigquery"

    abs_output_dir = os.path.join(DATA_ROOT, output_dir)
    os.makedirs(abs_output_dir, exist_ok=True)
    graph_fqn = f"`{project_id}.{dataset_id}.STARTER_ONTOLOGY_GRAPH`"

    bq_ddl = f"""-- [Engine 1: BigQuery Property Graph] ISO SQL:2023 Property Graph DDL
-- Target Dataset: {project_id}.{dataset_id} (Provisioned via HashiCorp Terraform 1.8.5)
CREATE OR REPLACE PROPERTY GRAPH {graph_fqn}
  NODE TABLES (
    `{project_id}.{dataset_id}.tb_customer_contract`
      KEY (contract_id)
      LABEL CustomerContractNode
      PROPERTIES (contract_id, customer_id, customer_segment, age_group, device_id, plan_id, contract_type, commitment_months, elapsed_days, granted_subsidy_krw, welfare_status, status, provenance, source_ref),
    `{project_id}.{dataset_id}.tb_device_master`
      KEY (device_id)
      LABEL DeviceNode
      PROPERTIES (device_id, device_name, manufacturer, storage_gb, factory_price_krw, release_date, provenance, source_ref),
    `{project_id}.{dataset_id}.tb_plan_master`
      KEY (plan_id)
      LABEL PlanNode
      PROPERTIES (plan_id, plan_name, tier_category, monthly_fee_krw, min_maintenance_days, selective_discount_rate, provenance, source_ref),
    `{project_id}.{dataset_id}.tb_subsidy_policy`
      KEY (policy_id)
      LABEL SubsidyNode
      PROPERTIES (policy_id, device_id, plan_id, base_subsidy_krw, additional_subsidy_cap_krw, mandatory_retention_days, effective_from, provenance, source_ref),
    `{project_id}.{dataset_id}.tb_doc_chunks`
      KEY (chunk_id)
      LABEL DocChunkNode
      PROPERTIES (chunk_id, source_file, section_title, content, content_sha256, trust_tier),
    `{project_id}.{dataset_id}.tb_domain_rules`
      KEY (rule_id)
      LABEL DomainRuleNode
      PROPERTIES (rule_id, rule_name, rule_category, condition_expr, formula_expr, source_chunk_id, description_ko, provenance, source_ref)
  )
  EDGE TABLES (
    `{project_id}.{dataset_id}.edge_contract_device`
      KEY (contract_id, device_id)
      SOURCE KEY (contract_id) REFERENCES `{project_id}.{dataset_id}.tb_customer_contract` (contract_id)
      DESTINATION KEY (device_id) REFERENCES `{project_id}.{dataset_id}.tb_device_master` (device_id)
      LABEL USES_DEVICE
      PROPERTIES (contract_id, customer_id, device_id, edge_type),
    `{project_id}.{dataset_id}.edge_contract_plan`
      KEY (contract_id, plan_id)
      SOURCE KEY (contract_id) REFERENCES `{project_id}.{dataset_id}.tb_customer_contract` (contract_id)
      DESTINATION KEY (plan_id) REFERENCES `{project_id}.{dataset_id}.tb_plan_master` (plan_id)
      LABEL SUBSCRIBES_PLAN
      PROPERTIES (contract_id, customer_id, plan_id, edge_type),
    `{project_id}.{dataset_id}.edge_subsidy_binding`
      KEY (policy_id)
      SOURCE KEY (device_id) REFERENCES `{project_id}.{dataset_id}.tb_device_master` (device_id)
      DESTINATION KEY (plan_id) REFERENCES `{project_id}.{dataset_id}.tb_plan_master` (plan_id)
      LABEL HAS_SUBSIDY_POLICY
      PROPERTIES (policy_id, device_id, plan_id, total_subsidy_krw, edge_type),
    `{project_id}.{dataset_id}.edge_rule_applies_to_plan`
      KEY (edge_id)
      SOURCE KEY (rule_id) REFERENCES `{project_id}.{dataset_id}.tb_domain_rules` (rule_id)
      DESTINATION KEY (plan_id) REFERENCES `{project_id}.{dataset_id}.tb_plan_master` (plan_id)
      LABEL APPLIES_TO_PLAN
      PROPERTIES (edge_id, rule_id, plan_id, source_chunk_id, relation_label_ko, edge_type, provenance, source_ref)
  );
"""

    spanner_graph_only_ddl = """CREATE OR REPLACE PROPERTY GRAPH STARTER_ONTOLOGY_GRAPH
  NODE TABLES (
    tb_customer_contract
      KEY (contract_id)
      LABEL CustomerContractNode
      PROPERTIES (contract_id, customer_id, customer_segment, age_group, device_id, plan_id, contract_type, commitment_months, elapsed_days, granted_subsidy_krw, welfare_status, status, provenance, source_ref),
    tb_device_master
      KEY (device_id)
      LABEL DeviceNode
      PROPERTIES (device_id, device_name, manufacturer, storage_gb, factory_price_krw, release_date, provenance, source_ref),
    tb_plan_master
      KEY (plan_id)
      LABEL PlanNode
      PROPERTIES (plan_id, plan_name, tier_category, monthly_fee_krw, min_maintenance_days, selective_discount_rate, provenance, source_ref),
    tb_subsidy_policy
      KEY (policy_id)
      LABEL SubsidyNode
      PROPERTIES (policy_id, device_id, plan_id, base_subsidy_krw, additional_subsidy_cap_krw, mandatory_retention_days, effective_from, provenance, source_ref),
    tb_doc_chunks
      KEY (chunk_id)
      LABEL DocChunkNode
      PROPERTIES (chunk_id, source_file, section_title, content, content_sha256, trust_tier, source_doc, source_sha256, page_from, page_to, article_no),
    tb_domain_rules
      KEY (rule_id)
      LABEL DomainRuleNode
      PROPERTIES (rule_id, rule_name, rule_category, condition_expr, formula_expr, source_chunk_id, description_ko, provenance, source_ref)
  )
  EDGE TABLES (
    edge_contract_device
      KEY (contract_id, device_id)
      SOURCE KEY (contract_id) REFERENCES tb_customer_contract (contract_id)
      DESTINATION KEY (device_id) REFERENCES tb_device_master (device_id)
      LABEL USES_DEVICE
      PROPERTIES (contract_id, customer_id, device_id, edge_type),
    edge_contract_plan
      KEY (contract_id, plan_id)
      SOURCE KEY (contract_id) REFERENCES tb_customer_contract (contract_id)
      DESTINATION KEY (plan_id) REFERENCES tb_plan_master (plan_id)
      LABEL SUBSCRIBES_PLAN
      PROPERTIES (contract_id, customer_id, plan_id, edge_type),
    edge_subsidy_binding
      KEY (policy_id)
      SOURCE KEY (device_id) REFERENCES tb_device_master (device_id)
      DESTINATION KEY (plan_id) REFERENCES tb_plan_master (plan_id)
      LABEL HAS_SUBSIDY_POLICY
      PROPERTIES (policy_id, device_id, plan_id, total_subsidy_krw, edge_type),
    edge_rule_applies_to_plan
      KEY (edge_id)
      SOURCE KEY (rule_id) REFERENCES tb_domain_rules (rule_id)
      DESTINATION KEY (plan_id) REFERENCES tb_plan_master (plan_id)
      LABEL APPLIES_TO_PLAN
      PROPERTIES (edge_id, rule_id, plan_id, source_chunk_id, relation_label_ko, edge_type, provenance, source_ref)
  )"""

    spanner_ddl = f"""-- [Engine 2: Cloud Spanner Graph] ISO GQL Property Graph Schema & DDL
-- Target Instance/DB: projects/{project_id}/instances/{DEFAULT_SPANNER_INSTANCE}/databases/{DEFAULT_SPANNER_DATABASE}
-- Architecture: Low-Latency Online Graph Traversal on Cloud Spanner (Enterprise 100 PU) + BigQuery Graph Fabric (EXTERNAL_QUERY)

CREATE TABLE tb_device_master (
  device_id STRING(64) NOT NULL,
  device_name STRING(256) NOT NULL,
  manufacturer STRING(128) NOT NULL,
  storage_gb INT64 NOT NULL,
  factory_price_krw INT64 NOT NULL,
  release_date STRING(32),
  provenance STRING(64),
  source_ref STRING(256)
) PRIMARY KEY (device_id);

CREATE TABLE tb_plan_master (
  plan_id STRING(64) NOT NULL,
  plan_name STRING(256) NOT NULL,
  tier_category STRING(64) NOT NULL,
  monthly_fee_krw INT64 NOT NULL,
  min_maintenance_days INT64 NOT NULL,
  selective_discount_rate FLOAT64 NOT NULL,
  provenance STRING(64),
  source_ref STRING(256)
) PRIMARY KEY (plan_id);

CREATE TABLE tb_subsidy_policy (
  policy_id STRING(64) NOT NULL,
  device_id STRING(64) NOT NULL,
  plan_id STRING(64) NOT NULL,
  base_subsidy_krw INT64 NOT NULL,
  additional_subsidy_cap_krw INT64 NOT NULL,
  mandatory_retention_days INT64 NOT NULL,
  effective_from STRING(32),
  provenance STRING(64),
  source_ref STRING(256)
) PRIMARY KEY (policy_id);

CREATE TABLE tb_customer_contract (
  customer_id STRING(64) NOT NULL,
  contract_id STRING(64) NOT NULL,
  customer_segment STRING(64) NOT NULL,
  age_group STRING(64) NOT NULL,
  device_id STRING(64) NOT NULL,
  plan_id STRING(64) NOT NULL,
  contract_type STRING(64) NOT NULL,
  commitment_months INT64 NOT NULL,
  elapsed_days INT64 NOT NULL,
  granted_subsidy_krw INT64 NOT NULL,
  welfare_status STRING(64) NOT NULL,
  status STRING(64) NOT NULL,
  provenance STRING(64),
  source_ref STRING(256)
) PRIMARY KEY (contract_id);

CREATE TABLE tb_doc_chunks (
  chunk_id STRING(64) NOT NULL,
  source_file STRING(256) NOT NULL,
  section_title STRING(512) NOT NULL,
  content STRING(MAX) NOT NULL,
  content_sha256 STRING(128) NOT NULL,
  trust_tier STRING(64) NOT NULL,
  source_doc STRING(256),
  source_sha256 STRING(128),
  page_from INT64,
  page_to INT64,
  article_no STRING(64)
) PRIMARY KEY (chunk_id);

CREATE TABLE tb_domain_rules (
  rule_id STRING(64) NOT NULL,
  rule_name STRING(256) NOT NULL,
  rule_category STRING(64) NOT NULL,
  condition_expr STRING(MAX) NOT NULL,
  formula_expr STRING(MAX) NOT NULL,
  source_chunk_id STRING(64) NOT NULL,
  description_ko STRING(MAX) NOT NULL,
  provenance STRING(64),
  source_ref STRING(256)
) PRIMARY KEY (rule_id);

CREATE TABLE edge_contract_device (
  contract_id STRING(64) NOT NULL,
  customer_id STRING(64) NOT NULL,
  device_id STRING(64) NOT NULL,
  edge_type STRING(64) NOT NULL
) PRIMARY KEY (contract_id, device_id);

CREATE TABLE edge_contract_plan (
  contract_id STRING(64) NOT NULL,
  customer_id STRING(64) NOT NULL,
  plan_id STRING(64) NOT NULL,
  edge_type STRING(64) NOT NULL
) PRIMARY KEY (contract_id, plan_id);

CREATE TABLE edge_subsidy_binding (
  policy_id STRING(64) NOT NULL,
  device_id STRING(64) NOT NULL,
  plan_id STRING(64) NOT NULL,
  total_subsidy_krw INT64 NOT NULL,
  edge_type STRING(64) NOT NULL
) PRIMARY KEY (policy_id);

CREATE TABLE edge_rule_applies_to_plan (
  edge_id STRING(64) NOT NULL,
  rule_id STRING(64) NOT NULL,
  plan_id STRING(64) NOT NULL,
  source_chunk_id STRING(64) NOT NULL,
  relation_label_ko STRING(256) NOT NULL,
  edge_type STRING(64) NOT NULL,
  provenance STRING(64),
  source_ref STRING(256)
) PRIMARY KEY (edge_id);

{spanner_graph_only_ddl};
"""

    bq_ddl_path = os.path.join(abs_output_dir, "create_property_graph.sql")
    with open(bq_ddl_path, "w", encoding="utf-8") as f:
        f.write(bq_ddl)

    spanner_ddl_path = os.path.join(abs_output_dir, "create_spanner_graph.sql")
    with open(spanner_ddl_path, "w", encoding="utf-8") as f:
        f.write(spanner_ddl)

    node_keys = {"tb_customer_contract": "contract_id", "tb_device_master": "device_id", "tb_plan_master": "plan_id",
                 "tb_subsidy_policy": "policy_id", "tb_domain_rules": "rule_id", "tb_doc_chunks": "chunk_id"}
    dw_nodes = ["CustomerContractNode", "DeviceNode", "PlanNode", "SubsidyNode"]
    live_ddl_job = {}
    live_gql_probe = {}
    live_stats = {}
    live_spanner = {"status": "SKIPPED", "reason": f"graph_engine={graph_engine}"}
    engine_benchmark = {}
    fabric_probe = {"status": "SKIPPED", "reason": f"graph_engine={graph_engine}"}
    stats = {}

    probe_gql_template = """
SELECT
  customer_id,
  contract_id,
  device_name,
  plan_name,
  monthly_fee_krw,
  rule_name,
  relation_label_ko
FROM GRAPH_TABLE(
  {graph_ref}
  MATCH (c:CustomerContractNode)-[:USES_DEVICE]->(d:DeviceNode),
        (c)-[:SUBSCRIBES_PLAN]->(p:PlanNode)<-[e:APPLIES_TO_PLAN]-(r:DomainRuleNode)
  COLUMNS (
    c.customer_id AS customer_id,
    c.contract_id AS contract_id,
    d.device_name AS device_name,
    p.plan_name AS plan_name,
    p.monthly_fee_krw AS monthly_fee_krw,
    r.rule_name AS rule_name,
    e.relation_label_ko AS relation_label_ko
  )
)
ORDER BY customer_id, rule_name
LIMIT 10
"""

    if deploy_live_bq:
        bq_runs_ms = []
        if graph_engine in ("bigquery", "both"):
            ddl_res = execute_bq_sql(bq_ddl, project_id=project_id)
            live_ddl_job = {
                "status": ddl_res.get("status"),
                "job_id": ddl_res.get("job_id"),
                "elapsed_ms": ddl_res.get("elapsed_ms"),
            }
            probe_gql = probe_gql_template.format(graph_ref=graph_fqn)
            gql_res = execute_bq_sql(probe_gql, project_id=project_id)
            if gql_res.get("status") == "SUCCESS":
                bq_runs_ms.append(gql_res.get("elapsed_ms", 0.0))
                for _ in range(max(0, benchmark_runs - 1)):
                    r = execute_bq_sql(probe_gql, project_id=project_id)
                    if r.get("status") == "SUCCESS":
                        bq_runs_ms.append(r.get("elapsed_ms", 0.0))
            live_gql_probe = {
                "status": gql_res.get("status"),
                "job_id": gql_res.get("job_id"),
                "elapsed_ms": gql_res.get("elapsed_ms"),
                "row_count": len(gql_res.get("rows", [])),
                "sample_rows": gql_res.get("rows", [])[:3],
            }
            st_res = execute_bq_sql(" UNION ALL ".join(
                f"SELECT '{t}' AS table_id, COUNT(*) AS row_count, COUNT(*) - COUNT(DISTINCT {k}) AS duplicate_keys "
                f"FROM `{project_id}.{dataset_id}.{t}`" for t, k in node_keys.items()), project_id=project_id)
            stats = {r["table_id"]: r for r in st_res.get("rows", [])}
            live_stats = {"status": st_res.get("status"), "job_id": st_res.get("job_id"), "tables": list(stats.values())}

        sp_runs_ms = []
        if graph_engine in ("spanner", "both"):
            sp_avail = check_spanner_available(project_id=project_id)
            if sp_avail.get("available"):
                sp_ddl_res = execute_spanner_ddl([spanner_graph_only_ddl], project_id=project_id)
                sp_probe_sql = probe_gql_template.format(graph_ref="STARTER_ONTOLOGY_GRAPH")
                # Warm up session and execute N benchmark runs
                sp_first = execute_spanner_sql(sp_probe_sql, project_id=project_id)
                for _ in range(benchmark_runs):
                    sr = execute_spanner_sql(sp_probe_sql, project_id=project_id)
                    if sr.get("status") == "SUCCESS":
                        sp_runs_ms.append(sr.get("elapsed_ms", 0.0))
                sp_st = execute_spanner_sql(" UNION ALL ".join(
                    f"SELECT '{t}' AS table_id, COUNT(*) AS row_count, COUNT(*) - COUNT(DISTINCT {k}) AS duplicate_keys FROM {t}"
                    for t, k in node_keys.items()), project_id=project_id)
                if not stats and sp_st.get("status") == "SUCCESS":
                    stats = {r["table_id"]: r for r in sp_st.get("rows", [])}
                live_spanner = {
                    "status": sp_first.get("status"),
                    "instance_id": DEFAULT_SPANNER_INSTANCE,
                    "database_id": DEFAULT_SPANNER_DATABASE,
                    "ddl_execution": sp_ddl_res,
                    "gql_verification_probe": {
                        "status": sp_first.get("status"),
                        "job_id": sp_first.get("job_id"),
                        "elapsed_ms": sp_runs_ms[0] if sp_runs_ms else sp_first.get("elapsed_ms"),
                        "row_count": len(sp_first.get("rows", [])),
                        "sample_rows": sp_first.get("rows", [])[:3],
                    },
                    "node_table_stats": {
                        "status": sp_st.get("status"),
                        "job_id": sp_st.get("job_id"),
                        "tables": sp_st.get("rows", []),
                    },
                }

        if bq_runs_ms or sp_runs_ms:
            bq_sorted = sorted(bq_runs_ms)
            sp_sorted = sorted(sp_runs_ms)
            engine_benchmark = {
                "runs_per_engine": benchmark_runs,
                "query_pattern": "(c:CustomerContractNode)-[:USES_DEVICE]->(d:DeviceNode), (c)-[:SUBSCRIBES_PLAN]->(p:PlanNode)<-[:APPLIES_TO_PLAN]-(r:DomainRuleNode)",
                "bigquery": {
                    "engine": "BigQuery Property Graph",
                    "runs_ms": bq_runs_ms,
                    "p50_ms": _percentile(bq_sorted, 50),
                    "p95_ms": _percentile(bq_sorted, 95),
                    "row_count": live_gql_probe.get("row_count", 0),
                } if bq_runs_ms else None,
                "spanner": {
                    "engine": "Cloud Spanner Graph",
                    "runs_ms": sp_runs_ms,
                    "p50_ms": _percentile(sp_sorted, 50),
                    "p95_ms": _percentile(sp_sorted, 95),
                    "row_count": live_spanner.get("gql_verification_probe", {}).get("row_count", 0),
                } if sp_runs_ms else None,
                "identical_row_count": (
                    live_gql_probe.get("row_count") == live_spanner.get("gql_verification_probe", {}).get("row_count")
                    if (bq_runs_ms and sp_runs_ms) else None
                ),
            }

        if graph_engine == "both" and live_spanner.get("status") == "SUCCESS":
            conn_id = f"projects/{project_id}/locations/{DEFAULT_LOCATION}/connections/{DEFAULT_BQ_SPANNER_CONN}"
            fabric_sql = f"""SELECT
  sp.customer_id,
  sp.contract_id,
  sp.device_name,
  sp.plan_name,
  sp.monthly_fee_krw,
  sp.rule_id,
  sp.rule_name,
  sp.source_chunk_id,
  ch.section_title,
  ch.content_sha256 AS anchor
FROM EXTERNAL_QUERY(
  '{conn_id}',
  '''SELECT customer_id, contract_id, device_name, plan_name, monthly_fee_krw, rule_id, rule_name, source_chunk_id
     FROM GRAPH_TABLE(
       STARTER_ONTOLOGY_GRAPH
       MATCH (c:CustomerContractNode)-[:USES_DEVICE]->(d:DeviceNode),
             (c)-[:SUBSCRIBES_PLAN]->(p:PlanNode)<-[e:APPLIES_TO_PLAN]-(r:DomainRuleNode)
       COLUMNS (
         c.customer_id AS customer_id,
         c.contract_id AS contract_id,
         d.device_name AS device_name,
         p.plan_name AS plan_name,
         p.monthly_fee_krw AS monthly_fee_krw,
         r.rule_id AS rule_id,
         r.rule_name AS rule_name,
         e.source_chunk_id AS source_chunk_id
       )
     )'''
) AS sp
LEFT JOIN `{project_id}.{dataset_id}.tb_doc_chunks` ch
  ON ch.chunk_id = sp.source_chunk_id
ORDER BY sp.customer_id, sp.rule_id
LIMIT 10"""
            fab_res = execute_bq_sql(fabric_sql, project_id=project_id)
            fabric_probe = {
                "status": fab_res.get("status"),
                "connection_id": conn_id,
                "job_id": fab_res.get("job_id"),
                "elapsed_ms": fab_res.get("elapsed_ms"),
                "row_count": len(fab_res.get("rows", [])),
                "sample_rows": fab_res.get("rows", [])[:3],
                "executed_sql": fabric_sql,
                "error": fab_res.get("error") if fab_res.get("status") != "SUCCESS" else None,
            }

    rc = lambda t: stats.get(t, {}).get("row_count")  # noqa: E731  (None when not measured)

    topology = {
        "graph_engine_mode": graph_engine,
        "default_runtime_engine": "spanner" if graph_engine == "spanner" else "bigquery",
        "graph_name": f"{project_id}.{dataset_id}.STARTER_ONTOLOGY_GRAPH",
        "spanner_graph_name": "STARTER_ONTOLOGY_GRAPH",
        "spanner_database_uri": f"projects/{project_id}/instances/{DEFAULT_SPANNER_INSTANCE}/databases/{DEFAULT_SPANNER_DATABASE}",
        "architecture_principle": "Dual-Engine Property Graph & Graph Fabric Federation (Entity=Node, Concept=Edge)",
        "live_bigquery_deployment": {
            "ddl_execution": live_ddl_job,
            "gql_verification_probe": live_gql_probe,
            "node_table_stats": live_stats,
        },
        "live_spanner_deployment": live_spanner,
        "engine_comparison_benchmark": engine_benchmark,
        "graph_fabric_federated_probe": fabric_probe,
        "structured_dw_nodes": dw_nodes,
        "unstructured_pruned_nodes": ["DocChunkNode", "DomainRuleNode"],
        "edge_tables": ["USES_DEVICE", "SUBSCRIBES_PLAN", "HAS_SUBSIDY_POLICY", "APPLIES_TO_PLAN"],
        "semantic_bridges": [
            {"source": "CustomerContractNode", "edge": "USES_DEVICE", "target": "DeviceNode", "type": "Relational FK"},
            {"source": "CustomerContractNode", "edge": "SUBSCRIBES_PLAN", "target": "PlanNode", "type": "Relational FK"},
            {"source": "DeviceNode", "edge": "HAS_SUBSIDY_POLICY", "target": "PlanNode", "type": "Subsidy Bridge"},
            {"source": "DomainRuleNode", "edge": "APPLIES_TO_PLAN", "target": "PlanNode", "type": "Semantic Bridge"},
        ],
        "vis_semantic_graph": {
            "nodes": [
                {"id": "HUB_SEMANTIC", "label_ko": "시맨틱 온톨로지 허브", "label_en": "Semantic Ontology Hub", "group": "hub", "color": "#0284c7", "desc_ko": "비정형 규정 위키(OKF v0.2)와 핵심 엔티티를 연결하는 시맨틱 루트 허브", "desc_en": "Semantic root hub linking OKF v0.2 wiki and core domain entities"},
                {"id": "ENT_CUSTOMER", "label_ko": "고객 약정 원장", "label_en": "Customer Contract", "group": "entity", "color": "#2563eb", "desc_ko": "고객 세그먼트(일반/시니어/군인/법인) 및 개통 경과일(elapsed_days) 보유 엔티티", "desc_en": "Customer subscription entity with elapsed days and welfare status"},
                {"id": "ENT_DEVICE", "label_ko": "단말기 모델", "label_en": "Terminal Device", "group": "entity", "color": "#2563eb", "desc_ko": "Galaxy S26 Ultra, iPhone 16 Pro 등 단말기 출고가(factory_price_krw) 마스터 엔티티", "desc_en": "Terminal device master entity with official factory price"},
                {"id": "ENT_PLAN", "label_ko": "모바일 요금제", "label_en": "Tariff Plan", "group": "entity", "color": "#2563eb", "desc_ko": "5G Premier Super/Essential/Slim/Light 등 월정액 및 45,000원 기준선 엔티티", "desc_en": "Tariff plan entity with monthly fee and 45,000 KRW baseline tier flag"},
                {"id": "ENT_SUBSIDY", "label_ko": "공시지원금 정책", "label_en": "Subsidy Policy", "group": "entity", "color": "#059669", "desc_ko": "단말기×요금제 조합별 공시지원금(base_subsidy_krw) 및 유통망 지원금 정책 엔티티", "desc_en": "Public and distribution subsidy allocation entity per device and plan"},
                {"id": "RULE_180D", "label_ko": "180일 의무유지 위약금 규칙", "label_en": "180-Day Commitment Rule", "group": "rule", "color": "#d97706", "desc_ko": "180일 이내 기준선 미만 하향 시 일할 차액정산 위약금 산정 규칙", "desc_en": "Daily prorated clawback penalty formula within 180 days"},
                {"id": "RULE_EXEMPT", "label_ko": "시니어·복지 위약금 면제 특례", "label_en": "Welfare Exemption Rule", "group": "rule", "color": "#d97706", "desc_ko": "시니어·복지 요금제 전환 및 군입대 정지 시 위약금 면제/유예 규칙", "desc_en": "Statutory penalty exemption for Senior/Welfare and military pause"},
                {"id": "RULE_TCO", "label_ko": "24개월 공시 vs 선택약정 비교 규칙", "label_en": "24M TCO Comparison Rule", "group": "rule", "color": "#d97706", "desc_ko": "공시지원금과 25% 선택약정의 24개월 총비용(TCO) 비교 최적화 규칙", "desc_en": "Deterministic 24-month TCO comparison between subsidy and 25% discount"},
                {"id": "CHUNK_002", "label_ko": "정책 가이드: 180일 기준선 의무", "label_en": "Guide Chunk: 180D Baseline", "group": "chunk", "color": "#0d9488", "desc_ko": "sample_policy_guide.md (SHA-256 해시 앵커 기반 원문 단락)", "desc_en": "Anchored paragraph from sample_policy_guide.md"},
                {"id": "CHUNK_003", "label_ko": "정책 가이드: 일할 위약금 산식", "label_en": "Guide Chunk: Penalty Formula", "group": "chunk", "color": "#0d9488", "desc_ko": "(초기지원금 - 하향지원금) × (180 - 유지일수) / 180 원문 근거", "desc_en": "Source formula anchor from sample_policy_guide.md"},
                {"id": "CHUNK_004", "label_ko": "정책 가이드: 복지 면제 및 TCO", "label_en": "Guide Chunk: Welfare & TCO", "group": "chunk", "color": "#0d9488", "desc_ko": "sample_welfare_exemption_guide.md 특례 면제 및 24개월 비교 원문 근거", "desc_en": "Source exemption anchor from sample_welfare_exemption_guide.md"},
            ],
            "edges": [
                {"from": "HUB_SEMANTIC", "to": "ENT_CUSTOMER", "label_ko": "CONTAINS_ENTITY", "label_en": "CONTAINS_ENTITY", "is_hub": True},
                {"from": "HUB_SEMANTIC", "to": "ENT_DEVICE", "label_ko": "CONTAINS_ENTITY", "label_en": "CONTAINS_ENTITY", "is_hub": True},
                {"from": "HUB_SEMANTIC", "to": "ENT_PLAN", "label_ko": "CONTAINS_ENTITY", "label_en": "CONTAINS_ENTITY", "is_hub": True},
                {"from": "HUB_SEMANTIC", "to": "ENT_SUBSIDY", "label_ko": "CONTAINS_ENTITY", "label_en": "CONTAINS_ENTITY", "is_hub": True},
                {"from": "ENT_CUSTOMER", "to": "ENT_DEVICE", "label_ko": "단말 개통 (USES_DEVICE)", "label_en": "USES_DEVICE", "is_hub": False},
                {"from": "ENT_CUSTOMER", "to": "ENT_PLAN", "label_ko": "요금제 가입 (SUBSCRIBES_PLAN)", "label_en": "SUBSCRIBES_PLAN", "is_hub": False},
                {"from": "ENT_DEVICE", "to": "ENT_PLAN", "label_ko": "지원금 결합 (HAS_SUBSIDY_POLICY)", "label_en": "HAS_SUBSIDY_POLICY", "is_hub": False},
                {"from": "RULE_180D", "to": "ENT_PLAN", "label_ko": "기준선 제약 (APPLIES_TO_PLAN)", "label_en": "APPLIES_TO_PLAN", "is_hub": False},
                {"from": "RULE_EXEMPT", "to": "ENT_PLAN", "label_ko": "특례 면제 (APPLIES_TO_PLAN)", "label_en": "APPLIES_TO_PLAN", "is_hub": False},
                {"from": "RULE_TCO", "to": "ENT_PLAN", "label_ko": "TCO 비교 (APPLIES_TO_PLAN)", "label_en": "APPLIES_TO_PLAN", "is_hub": False},
                {"from": "RULE_180D", "to": "CHUNK_002", "label_ko": "원문 근거 (GROUNDED_IN)", "label_en": "GROUNDED_IN", "is_hub": False},
                {"from": "RULE_180D", "to": "CHUNK_003", "label_ko": "산식 근거 (GROUNDED_IN)", "label_en": "GROUNDED_IN", "is_hub": False},
                {"from": "RULE_EXEMPT", "to": "CHUNK_004", "label_ko": "특례 근거 (GROUNDED_IN)", "label_en": "GROUNDED_IN", "is_hub": False},
            ],
        },
        "vis_property_graph": {
            "nodes": [
                {"id": "HUB_BQG", "label_ko": "Property Graph 마스터 허브", "label_en": "Property Graph Master Hub", "group": "hub", "color": "#0d9488", "table": "STARTER_ONTOLOGY_GRAPH", "key": "graph_root", "rows": len(node_keys)},
                {"id": "PG_CONTRACT", "label_ko": "고객 약정 노드 (CustomerContractNode)", "label_en": "CustomerContractNode", "group": "dw", "color": "#0284c7", "table": "tb_customer_contract", "key": "contract_id", "rows": rc("tb_customer_contract")},
                {"id": "PG_DEVICE", "label_ko": "단말기 마스터 노드 (DeviceNode)", "label_en": "DeviceNode", "group": "dw", "color": "#2563eb", "table": "tb_device_master", "key": "device_id", "rows": rc("tb_device_master")},
                {"id": "PG_PLAN", "label_ko": "요금제 마스터 노드 (PlanNode)", "label_en": "PlanNode", "group": "dw", "color": "#2563eb", "table": "tb_plan_master", "key": "plan_id", "rows": rc("tb_plan_master")},
                {"id": "PG_SUBSIDY", "label_ko": "공시지원금 노드 (SubsidyNode)", "label_en": "SubsidyNode", "group": "dw", "color": "#059669", "table": "tb_subsidy_policy", "key": "policy_id", "rows": rc("tb_subsidy_policy")},
                {"id": "PG_RULE", "label_ko": "비즈니스 규칙 노드 (DomainRuleNode)", "label_en": "DomainRuleNode", "group": "rule", "color": "#d97706", "table": "tb_domain_rules", "key": "rule_id", "rows": rc("tb_domain_rules")},
                {"id": "PG_CHUNK", "label_ko": "정책 청크 노드 (DocChunkNode)", "label_en": "DocChunkNode", "group": "chunk", "color": "#0d9488", "table": "tb_doc_chunks", "key": "chunk_id", "rows": rc("tb_doc_chunks")},
            ],
            "edges": [
                {"from": "HUB_BQG", "to": "PG_CONTRACT", "label_ko": "CONTAINS_TABLE", "label_en": "CONTAINS_TABLE", "is_hub": True},
                {"from": "HUB_BQG", "to": "PG_DEVICE", "label_ko": "CONTAINS_TABLE", "label_en": "CONTAINS_TABLE", "is_hub": True},
                {"from": "HUB_BQG", "to": "PG_PLAN", "label_ko": "CONTAINS_TABLE", "label_en": "CONTAINS_TABLE", "is_hub": True},
                {"from": "HUB_BQG", "to": "PG_SUBSIDY", "label_ko": "CONTAINS_TABLE", "label_en": "CONTAINS_TABLE", "is_hub": True},
                {"from": "PG_CONTRACT", "to": "PG_DEVICE", "label_ko": "개통 단말기 (USES_DEVICE)", "label_en": "USES_DEVICE", "is_hub": False},
                {"from": "PG_CONTRACT", "to": "PG_PLAN", "label_ko": "가입 요금제 (SUBSCRIBES_PLAN)", "label_en": "SUBSCRIBES_PLAN", "is_hub": False},
                {"from": "PG_DEVICE", "to": "PG_PLAN", "label_ko": "지원금 결합 (HAS_SUBSIDY_POLICY)", "label_en": "HAS_SUBSIDY_POLICY", "is_hub": False},
                {"from": "PG_RULE", "to": "PG_PLAN", "label_ko": "규칙 바인딩 (APPLIES_TO_PLAN)", "label_en": "APPLIES_TO_PLAN", "is_hub": False},
            ],
        },
        "metrics": {
            "duplicate_entity_nodes": sum(r["duplicate_keys"] for r in stats.values()) if stats else None,
            "dw_table_promotions": len(dw_nodes),
        },
    }
    topo_path = os.path.join(abs_output_dir, "graph_topology.json")
    with open(topo_path, "w", encoding="utf-8") as f:
        json.dump(topology, f, ensure_ascii=False, indent=2)

    print(
        f"[GRAPH BUILDER SUCCESS] Engine={graph_engine} | "
        f"BQ DDL: {live_ddl_job.get('job_id')} ({live_ddl_job.get('status')}) | "
        f"BQ Probe Rows: {live_gql_probe.get('row_count')} (p50={engine_benchmark.get('bigquery', {}).get('p50_ms') if engine_benchmark.get('bigquery') else '-'} ms) | "
        f"Spanner Probe: {live_spanner.get('status')} (p50={engine_benchmark.get('spanner', {}).get('p50_ms') if engine_benchmark.get('spanner') else '-'} ms) | "
        f"Graph Fabric EXTERNAL_QUERY: {fabric_probe.get('status')} ({fabric_probe.get('row_count', 0)} rows)"
    )
    return topology


if __name__ == "__main__":
    build_graph()
