# -*- coding: utf-8 -*-
"""
Pipeline Graph Builder (Dual Engine Adapter):
- Synthesizes both:
  1. BigQuery ISO SQL:2023 Property Graph DDL (`create_property_graph.sql`)
  2. Cloud Spanner Graph ISO GQL DDL (`create_spanner_graph.sql`)
- Produces `graph_topology.json` with `TASK-093` compliant Semantic Graph (Stage 2)
  and Property Graph (Stage 3) node/edge definitions (`Entity = Node`, `Concept = Edge`,
  Sky Blue `#0284c7` / Teal `#0d9488` hubs, Korean business labels).
"""
import os, json

def build_graph(project_id="my-project", dataset_id="my_dataset", output_dir="data/output"):
    os.makedirs(output_dir, exist_ok=True)
    graph_name = f"`{project_id}.{dataset_id}.ENTERPRISE_SUBSIDY_GRAPH`"

    bq_ddl = f"""-- [Engine 1: BigQuery Property Graph] ISO SQL:2023 Property Graph DDL
-- Architecture: Zero-ETL Direct Table Projection (0 Duplicate Entity Rows)
CREATE OR REPLACE PROPERTY GRAPH {graph_name}
  NODE TABLES (
    -- [Structured DW Master Ledgers]
    `{project_id}.{dataset_id}.dw_customer_contract`
       KEY (contract_id)
       LABEL CustomerContractNode
       PROPERTIES (contract_id, customer_id, customer_segment, device_id, plan_id, policy_id, contract_type, elapsed_days, welfare_status),
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

    -- [Unstructured OKF v0.2 Knowledge Chunks & Codified Rules]
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
    -- [Relational Foreign Key Bridges]
    `{project_id}.{dataset_id}.dw_customer_contract` AS edge_contract_plan
       KEY (contract_id)
       SOURCE KEY (contract_id) REFERENCES `{project_id}.{dataset_id}.dw_customer_contract` (contract_id)
       DESTINATION KEY (plan_id) REFERENCES `{project_id}.{dataset_id}.dw_plan_master` (plan_id)
       LABEL SUBSCRIBES_PLAN,
    `{project_id}.{dataset_id}.dw_customer_contract` AS edge_contract_policy
       KEY (contract_id)
       SOURCE KEY (contract_id) REFERENCES `{project_id}.{dataset_id}.dw_customer_contract` (contract_id)
       DESTINATION KEY (policy_id) REFERENCES `{project_id}.{dataset_id}.dw_subsidy_policy_master` (policy_id)
       LABEL BOUND_TO_POLICY,
    `{project_id}.{dataset_id}.dw_subsidy_policy_master` AS edge_subsidy_device
       KEY (policy_id)
       SOURCE KEY (policy_id) REFERENCES `{project_id}.{dataset_id}.dw_subsidy_policy_master` (policy_id)
       DESTINATION KEY (device_id) REFERENCES `{project_id}.{dataset_id}.dw_device_master` (device_id)
       LABEL COVERS_DEVICE,
    `{project_id}.{dataset_id}.dw_subsidy_policy_master` AS edge_subsidy_plan
       KEY (policy_id)
       SOURCE KEY (policy_id) REFERENCES `{project_id}.{dataset_id}.dw_subsidy_policy_master` (policy_id)
       DESTINATION KEY (plan_id) REFERENCES `{project_id}.{dataset_id}.dw_plan_master` (plan_id)
       LABEL REQUIRES_PLAN,

    -- [Semantic Cross-Domain Bridges]
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

    spanner_ddl = """-- [Engine 2: Cloud Spanner Graph] ISO GQL Property Graph Schema & DDL
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
"""

    bq_ddl_path = os.path.join(output_dir, "create_property_graph.sql")
    with open(bq_ddl_path, "w", encoding="utf-8") as f:
        f.write(bq_ddl)

    spanner_ddl_path = os.path.join(output_dir, "create_spanner_graph.sql")
    with open(spanner_ddl_path, "w", encoding="utf-8") as f:
        f.write(spanner_ddl)

    topology = {
        "graph_name": f"{project_id}.{dataset_id}.ENTERPRISE_SUBSIDY_GRAPH",
        "spanner_graph_name": "EnterpriseSubsidyGraph",
        "architecture_principle": "Dual-Engine Zero-ETL Property Graph (Entity=Node, Concept=Edge)",
        "structured_dw_nodes": ["CustomerContractNode", "DeviceNode", "PlanNode", "SubsidyNode"],
        "unstructured_pruned_nodes": ["DocChunkNode", "DomainRuleNode"],
        "edge_tables": ["SUBSCRIBES_PLAN", "BOUND_TO_POLICY", "COVERS_DEVICE", "REQUIRES_PLAN", "APPLIES_RULE", "GROUNDED_IN"],
        "semantic_bridges": [
            {"source": "CustomerContractNode", "edge": "SUBSCRIBES_PLAN", "target": "PlanNode", "type": "Relational FK"},
            {"source": "CustomerContractNode", "edge": "BOUND_TO_POLICY", "target": "SubsidyNode", "type": "Relational FK"},
            {"source": "SubsidyNode", "edge": "COVERS_DEVICE", "target": "DeviceNode", "type": "Relational FK"},
            {"source": "SubsidyNode", "edge": "REQUIRES_PLAN", "target": "PlanNode", "type": "Relational FK"},
            {"source": "DomainRuleNode", "edge": "APPLIES_RULE", "target": "PlanNode", "type": "Semantic Bridge"},
            {"source": "DomainRuleNode", "edge": "GROUNDED_IN", "target": "DocChunkNode", "type": "SHA-256 Grounding"}
        ],
        "vis_semantic_graph": {
            "nodes": [
                {"id": "HUB_SEMANTIC", "label_ko": "시맨틱 온톨로지 허브", "label_en": "Semantic Ontology Hub", "group": "hub", "color": "#0284c7", "desc_ko": "비정형 규정 위키(OKF v0.2)와 핵심 엔티티를 연결하는 시맨틱 루트 허브", "desc_en": "Semantic root hub linking OKF v0.2 wiki and core domain entities"},
                {"id": "ENT_CUSTOMER", "label_ko": "고객 약정 원장", "label_en": "Customer Contract", "group": "entity", "color": "#2563eb", "desc_ko": "고객 세그먼트(일반/시니어/군인/법인) 및 개통 경과일(elapsed_days) 보유 엔티티", "desc_en": "Customer subscription entity with elapsed days and welfare status"},
                {"id": "ENT_DEVICE", "label_ko": "단말기 모델", "label_en": "Terminal Device", "group": "entity", "color": "#2563eb", "desc_ko": "Galaxy S26 Ultra, iPhone 16 Pro 등 단말기 출고가(factory_price) 마스터 엔티티", "desc_en": "Terminal device master entity with official factory price"},
                {"id": "ENT_PLAN", "label_ko": "모바일 요금제", "label_en": "Tariff Plan", "group": "entity", "color": "#2563eb", "desc_ko": "5G Premier Super/Essential/Slim/Light 등 월정액 및 45,000원 기준선 엔티티", "desc_en": "Tariff plan entity with monthly fee and 45,000 KRW baseline tier flag"},
                {"id": "ENT_SUBSIDY", "label_ko": "공시지원금 정책", "label_en": "Subsidy Policy", "group": "entity", "color": "#059669", "desc_ko": "단말기×요금제 조합별 공시지원금(basic_subsidy) 및 유통망 지원금 정책 엔티티", "desc_en": "Public and distribution subsidy allocation entity per device and plan"},
                {"id": "RULE_180D", "label_ko": "180일 의무유지 위약금 규칙", "label_en": "180-Day Commitment Rule", "group": "rule", "color": "#d97706", "desc_ko": "180일 이내 기준선 미만 하향 시 일할 차액정산 위약금 산정 규칙", "desc_en": "Daily prorated clawback penalty formula within 180 days"},
                {"id": "RULE_EXEMPT", "label_ko": "시니어·복지 위약금 면제 특례", "label_en": "Welfare Exemption Rule", "group": "rule", "color": "#d97706", "desc_ko": "시니어·복지 요금제 전환 및 군입대 정지 시 위약금 면제/유예 규칙", "desc_en": "Statutory penalty exemption for Senior/Welfare and military pause"},
                {"id": "RULE_TCO", "label_ko": "24개월 공시 vs 선택약정 비교 규칙", "label_en": "24M TCO Comparison Rule", "group": "rule", "color": "#d97706", "desc_ko": "공시지원금과 25% 선택약정의 24개월 총비용(TCO) 비교 최적화 규칙", "desc_en": "Deterministic 24-month TCO comparison between subsidy and 25% discount"},
                {"id": "CHUNK_002", "label_ko": "정책 가이드: 180일 기준선 의무", "label_en": "Guide Chunk: 180D Baseline", "group": "chunk", "color": "#0d9488", "desc_ko": "sample_policy_guide.md (SHA-256 해시 앵커 기반 원문 단락)", "desc_en": "Anchored paragraph from sample_policy_guide.md"},
                {"id": "CHUNK_003", "label_ko": "정책 가이드: 일할 위약금 산식", "label_en": "Guide Chunk: Penalty Formula", "group": "chunk", "color": "#0d9488", "desc_ko": "(초기지원금 - 하향지원금) × (180 - 유지일수) / 180 원문 근거", "desc_en": "Source formula anchor from sample_policy_guide.md"},
                {"id": "CHUNK_004", "label_ko": "정책 가이드: 복지 면제 및 TCO", "label_en": "Guide Chunk: Welfare & TCO", "group": "chunk", "color": "#0d9488", "desc_ko": "sample_welfare_exemption_guide.md 특례 면제 및 24개월 비교 원문 근거", "desc_en": "Source exemption anchor from sample_welfare_exemption_guide.md"}
            ],
            "edges": [
                {"from": "HUB_SEMANTIC", "to": "ENT_CUSTOMER", "label_ko": "CONTAINS_ENTITY", "label_en": "CONTAINS_ENTITY", "is_hub": True},
                {"from": "HUB_SEMANTIC", "to": "ENT_DEVICE", "label_ko": "CONTAINS_ENTITY", "label_en": "CONTAINS_ENTITY", "is_hub": True},
                {"from": "HUB_SEMANTIC", "to": "ENT_PLAN", "label_ko": "CONTAINS_ENTITY", "label_en": "CONTAINS_ENTITY", "is_hub": True},
                {"from": "HUB_SEMANTIC", "to": "ENT_SUBSIDY", "label_ko": "CONTAINS_ENTITY", "label_en": "CONTAINS_ENTITY", "is_hub": True},
                {"from": "ENT_CUSTOMER", "to": "ENT_PLAN", "label_ko": "요금제 가입 (SUBSCRIBES_PLAN)", "label_en": "SUBSCRIBES_PLAN", "is_hub": False},
                {"from": "ENT_CUSTOMER", "to": "ENT_SUBSIDY", "label_ko": "지원금 약정 (BOUND_TO_POLICY)", "label_en": "BOUND_TO_POLICY", "is_hub": False},
                {"from": "ENT_SUBSIDY", "to": "ENT_DEVICE", "label_ko": "단말기 적용 (COVERS_DEVICE)", "label_en": "COVERS_DEVICE", "is_hub": False},
                {"from": "ENT_SUBSIDY", "to": "ENT_PLAN", "label_ko": "요금제 조건 (REQUIRES_PLAN)", "label_en": "REQUIRES_PLAN", "is_hub": False},
                {"from": "RULE_180D", "to": "ENT_PLAN", "label_ko": "기준선 제약 (APPLIES_RULE)", "label_en": "APPLIES_RULE", "is_hub": False},
                {"from": "RULE_EXEMPT", "to": "ENT_CUSTOMER", "label_ko": "특례 면제 (EXEMPTS_PENALTY)", "label_en": "EXEMPTS_PENALTY", "is_hub": False},
                {"from": "RULE_TCO", "to": "ENT_SUBSIDY", "label_ko": "TCO 비교 (COMPARES_TCO)", "label_en": "COMPARES_TCO", "is_hub": False},
                {"from": "RULE_180D", "to": "CHUNK_002", "label_ko": "원문 근거 (GROUNDED_IN)", "label_en": "GROUNDED_IN", "is_hub": False},
                {"from": "RULE_180D", "to": "CHUNK_003", "label_ko": "산식 근거 (GROUNDED_IN)", "label_en": "GROUNDED_IN", "is_hub": False},
                {"from": "RULE_EXEMPT", "to": "CHUNK_004", "label_ko": "특례 근거 (GROUNDED_IN)", "label_en": "GROUNDED_IN", "is_hub": False}
            ]
        },
        "vis_property_graph": {
            "nodes": [
                {"id": "HUB_BQG", "label_ko": "Property Graph 마스터 허브", "label_en": "Property Graph Master Hub", "group": "hub", "color": "#0d9488", "table": "ENTERPRISE_SUBSIDY_GRAPH", "key": "graph_root", "rows": 4},
                {"id": "PG_CONTRACT", "label_ko": "고객 약정 노드 (CustomerContractNode)", "label_en": "CustomerContractNode", "group": "dw", "color": "#0284c7", "table": "dw_customer_contract", "key": "contract_id", "rows": 6},
                {"id": "PG_DEVICE", "label_ko": "단말기 마스터 노드 (DeviceNode)", "label_en": "DeviceNode", "group": "dw", "color": "#2563eb", "table": "dw_device_master", "key": "device_id", "rows": 4},
                {"id": "PG_PLAN", "label_ko": "요금제 마스터 노드 (PlanNode)", "label_en": "PlanNode", "group": "dw", "color": "#2563eb", "table": "dw_plan_master", "key": "plan_id", "rows": 6},
                {"id": "PG_SUBSIDY", "label_ko": "공시지원금 노드 (SubsidyNode)", "label_en": "SubsidyNode", "group": "dw", "color": "#059669", "table": "dw_subsidy_policy_master", "key": "policy_id", "rows": 5},
                {"id": "PG_RULE", "label_ko": "비즈니스 규칙 노드 (DomainRuleNode)", "label_en": "DomainRuleNode", "group": "rule", "color": "#d97706", "table": "ont_domain_rules", "key": "rule_id", "rows": 3},
                {"id": "PG_CHUNK", "label_ko": "정책 청크 노드 (DocChunkNode)", "label_en": "DocChunkNode", "group": "chunk", "color": "#0d9488", "table": "ont_doc_chunks", "key": "chunk_id", "rows": 5}
            ],
            "edges": [
                {"from": "HUB_BQG", "to": "PG_CONTRACT", "label_ko": "CONTAINS_TABLE", "label_en": "CONTAINS_TABLE", "is_hub": True},
                {"from": "HUB_BQG", "to": "PG_DEVICE", "label_ko": "CONTAINS_TABLE", "label_en": "CONTAINS_TABLE", "is_hub": True},
                {"from": "HUB_BQG", "to": "PG_PLAN", "label_ko": "CONTAINS_TABLE", "label_en": "CONTAINS_TABLE", "is_hub": True},
                {"from": "HUB_BQG", "to": "PG_SUBSIDY", "label_ko": "CONTAINS_TABLE", "label_en": "CONTAINS_TABLE", "is_hub": True},
                {"from": "PG_CONTRACT", "to": "PG_PLAN", "label_ko": "가입 요금제 (SUBSCRIBES_PLAN)", "label_en": "SUBSCRIBES_PLAN", "is_hub": False},
                {"from": "PG_CONTRACT", "to": "PG_SUBSIDY", "label_ko": "적용 지원금 (BOUND_TO_POLICY)", "label_en": "BOUND_TO_POLICY", "is_hub": False},
                {"from": "PG_SUBSIDY", "to": "PG_DEVICE", "label_ko": "대상 단말기 (COVERS_DEVICE)", "label_en": "COVERS_DEVICE", "is_hub": False},
                {"from": "PG_SUBSIDY", "to": "PG_PLAN", "label_ko": "요구 요금제 (REQUIRES_PLAN)", "label_en": "REQUIRES_PLAN", "is_hub": False},
                {"from": "PG_RULE", "to": "PG_PLAN", "label_ko": "규칙 바인딩 (APPLIES_RULE)", "label_en": "APPLIES_RULE", "is_hub": False},
                {"from": "PG_RULE", "to": "PG_CHUNK", "label_ko": "해시 앵커 (GROUNDED_IN)", "label_en": "GROUNDED_IN", "is_hub": False}
            ]
        },
        "metrics": {
            "duplicate_entity_nodes": 0,
            "dw_table_promotions": 4,
            "zero_copy_projection": True
        }
    }
    topo_path = os.path.join(output_dir, "graph_topology.json")
    with open(topo_path, "w", encoding="utf-8") as f:
        json.dump(topology, f, ensure_ascii=False, indent=2)

    print(f"[GRAPH BUILDER SUCCESS] BigQuery DDL -> {bq_ddl_path}, Spanner DDL -> {spanner_ddl_path}, Topology -> {topo_path}")
    return topology

if __name__ == "__main__":
    build_graph()
