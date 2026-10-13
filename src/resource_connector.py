# Copyright (c) 2026 Sean Jung (seanjung@google.com). All Rights Reserved.
# Non-Commercial Use Only: Methodology & Docs under CC BY-NC-ND 4.0; Source Code under PolyForm Noncommercial License 1.0.0.
# Commercial use, paid consulting/SI/PoC delivery, or production deployment requires prior written permission from seanjung@google.com.

# -*- coding: utf-8 -*-
"""
resource_connector.py
Ready-to-Use GCP Ontology Resource Connector (Starter Pack v2.2)

Architectural Principle (Code Exposure Boundary):
- The Starter Pack abstracts away heavy ontology compiler and internal MCP server plumbing.
- Instead of exposing complex parsing, LLM-Wiki compilation, or internal MCP pipeline servers,
  this connector binds directly to **Ready-to-Use Google Cloud Ontology Resources** provisioned
  according to our Enterprise Standard (`5-Stage x 11-Step`, `P1/P2/P3 x W1/W2/W3 x Gate G2-W`):
    1. BigQuery DW & Ontology Dataset (`seanjung-poc.starter_ontology_dw`)
    2. BigQuery SQL:2023 Property Graph (`seanjung-poc.starter_ontology_dw.STARTER_ONTOLOGY_GRAPH`)
    3. Cloud Storage 3-Layer OKF Wiki (`gs://seanjung-poc-starter-ontology/ontology/`)
    4. Cloud Spanner Graph (`starter-spanner/starter_ontology_db/STARTER_ONTOLOGY_GRAPH`)
    5. Business Rules (`BR-*`), Decision Workflows (`W1/W2/W3`), and Unified CQs (`Golden + Workflow + Boundary`)
"""

import json
import os
import time
from typing import Any, Dict, List, Optional

from src.gcp_client import (
    DEFAULT_DATASET_ID,
    DEFAULT_GCS_BUCKET,
    DEFAULT_GEMINI_MODEL,
    DEFAULT_LOCATION,
    DEFAULT_PROJECT_ID,
    DEFAULT_SPANNER_DATABASE,
    DEFAULT_SPANNER_INSTANCE,
    check_spanner_available,
    execute_bq_sql,
    list_gcs_objects,
)

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

REFERENCE_STUDIOS = {
    "starter_live_studio": {
        "id": "starter",
        "name_ko": "스타터 포털 라이브 데모 (6-Tab 리소스 직결 스튜디오)",
        "name_en": "Starter Portal Live Demo (6-Tab Resource-Connected Studio)",
        "url": "https://agentic-ontology-starter-924723860007.asia-northeast3.run.app/",
        "secondary_url": "https://agentic-ontology-starter-lwrlf7yogq-du.a.run.app/",
        "domain": "Telecom Subsidy & Contract (De-identified Starter Sample)",
        "tabs": "6-Tab Starter Twin (0. Overview · Stage 1~5)",
        "resources": "seanjung-poc.starter_ontology_dw.STARTER_ONTOLOGY_GRAPH + gs://seanjung-poc-starter-ontology",
    },
    "lguplus_reference_studio": {
        "id": "lguplus_mcp",
        "name_ko": "기준 스튜디오 #1 · LG U+ 엔터프라이즈 스튜디오 (12-Tab Full Standard)",
        "name_en": "Reference Standard #1 · LG U+ Enterprise Studio (12-Tab Full Standard)",
        "url": "https://agentic-ontology-studio-lguplus-mcp-924723860007.asia-northeast3.run.app/",
        "domain": "LG U+ Mobile Subsidy, Penalty & Retention Consultation",
        "tabs": "12-Tab Full Standard (0. Overview ~ 11. Evaluation, 5-Stage × 11-Step)",
        "resources": "177 Anchors · 242 Wiki Nodes · 39 Rules · 10 Workflows (W1:1/W2:2/W3:7) · 14/14 WCQ · 44 BQ Tables",
    },
    "hnh_reference_studio": {
        "id": "hnh_mcp",
        "name_ko": "기준 스튜디오 #2 · LG생활건강(H&H) 화장품 표시·광고 스튜디오 (12-Tab Full Standard)",
        "name_en": "Reference Standard #2 · LG H&H Cosmetics Compliance Studio (12-Tab Full Standard)",
        "url": "https://hnh-agentic-ontology-studio-mcp-384182013777.asia-northeast3.run.app/",
        "domain": "LG H&H Cosmetics Labeling & Advertising Compliance",
        "tabs": "12-Tab Full Standard (0. Overview ~ 11. Evaluation, 5-Stage × 11-Step)",
        "resources": "49 Docs · 341 Wiki Nodes · 24 Rules · 10 Workflows · 20/20 WCQ · 43 BQ Tables",
    },
}

CODE_EXPOSURE_BOUNDARY = {
    "principle_ko": "복잡한 온톨로지 컴파일러 및 내부 MCP 서버 파트는 추상화하여 숨기고, 스타터 코드는 이미 준비된 GCP 온톨로지 리소스(BigQuery Property Graph, GCS 3-Layer Wiki, 비즈니스 룰·워크플로우)에 즉시 연결하여 도메인 비즈니스 함수와 에이전트만 간결하게 구현·검증합니다.",
    "principle_en": "Heavy ontology compiler and internal MCP server plumbing are abstracted away. The Starter repo exposes clean connectors to ready-to-use GCP ontology resources (BigQuery Property Graph, GCS 3-Layer Wiki, Business Rules & Workflows) plus concise domain business functions and agent orchestration.",
    "abstracted_platform_layer": [
        {
            "component": "Raw Document Parsing & OCR Engine (Gate 0)",
            "role_ko": "PDF/DOCX/표 이미지 무손실 파싱(>=95% 보존율) 및 문단별 SHA-256 해시 앵커링",
            "role_en": "Lossless PDF/DOCX/table parsing (>=95% fidelity) & paragraph SHA-256 hash anchoring",
            "ready_resource": "data/output/doc_chunks.jsonl & BigQuery tb_doc_chunks",
        },
        {
            "component": "OKF v0.2 3-Layer LLM-Wiki Compiler (P1)",
            "role_ko": "원문에서 L1(Summary)·L2(Entity)·L3(Concept) 위키 및 Frontmatter 정책 상수(graph.properties) 컴파일",
            "role_en": "Compiles L1 Summary, L2 Entity, L3 Concept wiki & frontmatter policy constants (graph.properties)",
            "ready_resource": "gs://seanjung-poc-starter-ontology/ontology/ & data/llm_wiki/*.md",
        },
        {
            "component": "Multi-Source Workflow Extractor & Gate G2-W (W1·W2·W3)",
            "role_ko": "P1(규범 가이드)·P2(상태 원장)·P3(상담 대화)에서 W1/W2/W3 의사결정 워크플로우 추출 및 G2-W 역방향 환류",
            "role_en": "Extracts W1/W2/W3 decision workflows across P1/P2/P3 and enforces Gate G2-W feedback into Wiki & Graph",
            "ready_resource": "data/llm_wiki/business_rules.json, business_workflows.json, workflow_cqs.json",
        },
        {
            "component": "Dual Property Graph DDL Synthesizer & Loader (P2·P3)",
            "role_ko": "BigQuery SQL:2023 Property Graph 및 Cloud Spanner ISO GQL 그래프 스키마·뷰 프로비저닝",
            "role_en": "Provisions BigQuery SQL:2023 Property Graph & Cloud Spanner ISO GQL graph schemas and views",
            "ready_resource": "seanjung-poc.starter_ontology_dw.STARTER_ONTOLOGY_GRAPH & starter-spanner/starter_ontology_db",
        },
    ],
    "exposed_starter_layer": [
        {
            "file": "src/resource_connector.py & src/gcp_client.py",
            "category": "1. Resource Connector (리소스 직결 커넥터)",
            "role_ko": "즉시 사용 가능한 BigQuery Property Graph, GCS 3-Layer Wiki, Spanner Graph, Vertex AI Gemini에 바로 연결하는 경량 커넥터",
            "role_en": "Lightweight connector directly binding to ready-to-use BigQuery Property Graph, GCS 3-Layer Wiki, Spanner Graph, and Vertex AI Gemini",
        },
        {
            "file": "src/agent/mcp_server.py",
            "category": "2. Domain Business Tools (비즈니스 도메인 도구 3종)",
            "role_ko": "준비된 리소스 위에서 동작하는 프로젝트 맞춤 도메인 함수 3종 (고객/단말 원장 조회 · 180일 일할 위약금/24M TCO 결정론 산식 · 그래프+위키 멀티홉 탐색)",
            "role_en": "3 domain business tools operating on ready-to-use resources (Customer/Device Ledger Lookup · 180D Penalty/24M TCO Deterministic Math · Graph+Wiki Multi-Hop Traversal)",
        },
        {
            "file": "src/agent/reasoning_engine.py",
            "category": "3. AI FDE Agent Orchestrator (에이전트 추론 엔진)",
            "role_ko": "Vertex AI gemini-3.8-flash 기반 슬롯 추출, 도메인 도구 체이닝 및 위키/청크 근거 합성 엔진",
            "role_en": "Vertex AI gemini-3.8-flash slot extraction, deterministic domain tool chaining, and grounded synthesis engine",
        },
        {
            "file": "src/web/studio_server.py & notebooks/{ko,en}/*.ipynb",
            "category": "4. Starter Portal UI & 12 Hands-on Notebooks (포털 & 실습 노트북)",
            "role_ko": "기준 스튜디오(lguplus-mcp) 흐름과 연결된 6-Tab 스타터 포털 및 Stage 0~5 한/영 실습 노트북 12종",
            "role_en": "6-Tab Starter Portal aligned with the reference studio (lguplus-mcp) and 12 KO/EN Stage 0~5 hands-on notebooks",
        },
    ],
}

STAGE_UNIFIED_MAP = [
    {
        "stage": "Stage 0",
        "title_ko": "아키텍처 오버뷰 · 리소스 직결 점검 & 라이브 데모 허브",
        "title_en": "Architecture Overview · Resource Connection Check & Live Demo Hub",
        "process_flow": "6-Layer Architecture (원천 ➔ 위키 ➔ 시맨틱/BQG ➔ 워크플로우 ➔ 도메인 도구 ➔ 에이전트) & Code Exposure Boundary",
        "starter_tab": "?tab=overview (0. Overview)",
        "reference_tab": "0. Overview (데이터 흐름 P1/P2/P3 · GCP 시스템 아키텍처 · 평가 요약)",
        "ready_resource": "config/starter_config.json · Ready-to-Use GCP Endpoints",
        "methodology_ko": "methodology/ko/METHODOLOGY_KO.md",
        "methodology_en": "methodology/en/METHODOLOGY_EN.md",
        "notebook_ko": "notebooks/ko/stage0_overview_walkthrough_ko.ipynb",
        "notebook_en": "notebooks/en/stage0_overview_walkthrough_en.ipynb",
    },
    {
        "stage": "Stage 1",
        "title_ko": "데이터 준비성 · 스코핑 · 비식별화 & Gate 0 원문 앵커 리소스",
        "title_en": "Data Readiness · Scoping · De-identification & Gate 0 Anchored Resources",
        "process_flow": "P1 (비정형 가이드 Gate 0 >=95%) + P2 (정형 DW 마스터 원장 4종 비식별화) + 5축 그래프 엔진 선택",
        "starter_tab": "?tab=stage1 (Stage 1. Asset)",
        "reference_tab": "1. Asset (정형/비정형/룰/워크플로우/CQ 자산 카탈로그)",
        "ready_resource": "BigQuery tb_customer_contract, tb_device_master, tb_plan_master, tb_subsidy_policy + tb_doc_chunks",
        "methodology_ko": "methodology/ko/01_stage1_asset_and_cq_ko.md",
        "methodology_en": "methodology/en/01_stage1_asset_and_cq_en.md",
        "notebook_ko": "notebooks/ko/stage1_asset_and_cq_ko.ipynb",
        "notebook_en": "notebooks/en/stage1_asset_and_cq_en.ipynb",
    },
    {
        "stage": "Stage 2",
        "title_ko": "OKF 3-Layer 온톨로지 위키 허브 & 시맨틱 그래프 리소스",
        "title_en": "OKF 3-Layer Ontology Wiki Hub & Semantic Graph Resources",
        "process_flow": "P1 ➔ OKF 3-Layer Wiki (01_summary · 02_entities · 03_concepts, Wiki Hub 불변식) ➔ Wiki Agent",
        "starter_tab": "?tab=stage2 (Stage 2. Wiki & Semantic Graph)",
        "reference_tab": "2. Ontology Wiki · 3. Ontology Semantic · 4. Wiki Agent",
        "ready_resource": "gs://seanjung-poc-starter-ontology/ontology/ & data/llm_wiki/{summary,entities,concepts,rules}.md",
        "methodology_ko": "methodology/ko/02_stage2_wiki_and_semantic_graph_ko.md",
        "methodology_en": "methodology/en/02_stage2_wiki_and_semantic_graph_en.md",
        "notebook_ko": "notebooks/ko/stage2_wiki_and_semantic_graph_ko.ipynb",
        "notebook_en": "notebooks/en/stage2_wiki_and_semantic_graph_en.ipynb",
    },
    {
        "stage": "Stage 3",
        "title_ko": "비즈니스 룰 · W1/W2/W3 워크플로우 · Gate G2-W & 듀얼 Property Graph 리소스",
        "title_en": "Business Rules · W1/W2/W3 Workflows · Gate G2-W & Dual Property Graph Resources",
        "process_flow": "P1/P2/P3 × W1/W2/W3 워크플로우 ➔ Gate G2-W (위키·그래프 역방향 피드백) ➔ BigQuery/Spanner Property Graph",
        "starter_tab": "?tab=stage3 (Stage 3. Property Graph)",
        "reference_tab": "5. BigQuery Graph · 6. BQG Agent · 8. Workflow",
        "ready_resource": "seanjung-poc.starter_ontology_dw.STARTER_ONTOLOGY_GRAPH & business_workflows.json",
        "methodology_ko": "methodology/ko/03_stage3_property_graph_ko.md",
        "methodology_en": "methodology/en/03_stage3_property_graph_en.md",
        "notebook_ko": "notebooks/ko/stage3_property_graph_bigquery_spanner_ko.ipynb",
        "notebook_en": "notebooks/en/stage3_property_graph_bigquery_spanner_en.ipynb",
    },
    {
        "stage": "Stage 4",
        "title_ko": "리소스 직결 도메인 비즈니스 도구(3종) & AI FDE 에이전트 실행",
        "title_en": "Resource-Connected Domain Business Tools (3 Tools) & AI FDE Agent Runtime",
        "process_flow": "Contract 4 (D4.5) 워크플로우 분기 ↔ 도메인 비즈니스 도구 1:1 바인딩 ➔ Workflow Agent & AI FDE 추론",
        "starter_tab": "?tab=stage4 (Stage 4. Agent & Domain Tools)",
        "reference_tab": "9. Workflow Agent · 10. AI FDE",
        "ready_resource": "DomainMcpServer (3 Domain Tools) + AiFdeAgentEngine (Vertex AI gemini-3.8-flash)",
        "methodology_ko": "methodology/ko/04_stage4_agent_and_mcp_ko.md",
        "methodology_en": "methodology/en/04_stage4_agent_and_mcp_en.md",
        "notebook_ko": "notebooks/ko/stage4_agent_and_mcp_execution_ko.ipynb",
        "notebook_en": "notebooks/en/stage4_agent_and_mcp_execution_en.ipynb",
    },
    {
        "stage": "Stage 5",
        "title_ko": "6-Layer 엔드투엔드 데이터 리니지 & 통합 CQ(Golden·Workflow·Boundary) 검증",
        "title_en": "6-Layer End-to-End Data Lineage & Unified CQ (Golden·Workflow·Boundary) Evaluation",
        "process_flow": "6-Layer Lineage (원천 ➔ 위키 ➔ BQG ➔ 워크플로우 ➔ 도구 ➔ 에이전트) & Golden/Workflow/Boundary 평가 루프",
        "starter_tab": "?tab=stage5 (Stage 5. Lineage & Eval)",
        "reference_tab": "7. Lineage · 11. Evaluation",
        "ready_resource": "config/lineage_spec.json · cq_benchmark_report.json · boundary_benchmark_results.json",
        "methodology_ko": "methodology/ko/05_stage5_lineage_and_eval_ko.md",
        "methodology_en": "methodology/en/05_stage5_lineage_and_eval_en.md",
        "notebook_ko": "notebooks/ko/stage5_lineage_and_evaluation_ko.ipynb",
        "notebook_en": "notebooks/en/stage5_lineage_and_evaluation_en.ipynb",
    },
]


class OntologyResourceConnector:
    """
    Direct connector to Ready-to-Use Google Cloud Ontology Resources.
    Abstracts away internal MCP builder servers and compiler pipelines so Starter users
    can immediately inspect, query, and extend the provisioned ontology resources.
    """

    def __init__(
        self,
        project_id: str = DEFAULT_PROJECT_ID,
        dataset_id: str = DEFAULT_DATASET_ID,
        location: str = DEFAULT_LOCATION,
        gcs_bucket: str = DEFAULT_GCS_BUCKET,
        spanner_instance_id: str = DEFAULT_SPANNER_INSTANCE,
        spanner_database_id: str = DEFAULT_SPANNER_DATABASE,
        root_dir: str = BASE_DIR,
    ):
        self.project_id = project_id
        self.dataset_id = dataset_id
        self.location = location
        self.gcs_bucket = gcs_bucket
        self.spanner_instance_id = spanner_instance_id
        self.spanner_database_id = spanner_database_id
        self.root_dir = os.path.abspath(root_dir)
        self.fq = f"{self.project_id}.{self.dataset_id}"
        self.graph_id = f"{self.fq}.STARTER_ONTOLOGY_GRAPH"

    def get_resource_manifest(self) -> Dict[str, Any]:
        """Returns the unified architecture, code exposure boundary, reference demos, and stage map."""
        return {
            "version": "2.2.0",
            "architecture_mode": "RESOURCE_CONNECTED_STARTER (MCP Build Internals Abstracted)",
            "reference_standard": {
                "pipeline": "5-Stage x 11-Step",
                "flow_matrix": "P1 (Normative Docs) / P2 (Structured DW State) / P3 (Dialogue & Integrated Graph) x W1 / W2 / W3 x Gate G2-W",
                "layers": [
                    "1. 원천 데이터 (Raw Docs & DW Tables)",
                    "2. 온톨로지 위키 허브 (OKF 3-Layer Wiki: Summary · Entities · Concepts)",
                    "3. 시맨틱 & 물리 Property Graph (BigQuery SQL:2023 GRAPH_TABLE & Cloud Spanner ISO GQL)",
                    "4. 비즈니스 룰 & 의사결정 워크플로우 (W1 · W2 · W3 & Gate G2-W)",
                    "5. 도메인 비즈니스 도구 (Contract 4 / D4.5 1:1 Bound Functions)",
                    "6. 에이전트 런타임 & 통합 평가 (Wiki/BQG/Workflow Agent · AI FDE · 6-Layer Lineage)",
                ],
            },
            "ready_to_use_gcp_resources": {
                "gcp_project_id": self.project_id,
                "region": self.location,
                "bigquery_dataset": self.fq,
                "bigquery_dw": {"fq_dataset": self.fq},
                "bigquery_property_graph": self.graph_id,
                "bigquery_property_graph_detail": {"fq_graph": self.graph_id},
                "gcs_wiki_bucket": f"gs://{self.gcs_bucket}/ontology/",
                "gcs_okf_wiki": {"uri": f"gs://{self.gcs_bucket}/ontology/"},
                "spanner_graph": f"projects/{self.project_id}/instances/{self.spanner_instance_id}/databases/{self.spanner_database_id}/graphs/STARTER_ONTOLOGY_GRAPH",
                "serving_model": DEFAULT_GEMINI_MODEL,
            },
            "domain_business_tools": [
                {
                    "tool_name": "mcp_lookup_customer_profile",
                    "role_ko": "정형 DW 원장(고객 계약·단말 출고가·요금제·지원금) 결정론 조회",
                    "role_en": "Deterministic lookup of customer contract, device price, plan, and subsidy ledger",
                },
                {
                    "tool_name": "mcp_calculate_penalty_rule",
                    "role_ko": "180일 일할 위약금·면제 조건·24개월 TCO 결정론 산식 계산",
                    "role_en": "180-day prorated penalty, exemption check, and 24-month TCO deterministic calculation",
                },
                {
                    "tool_name": "mcp_query_graph_and_wiki",
                    "role_ko": "BigQuery/Spanner Property Graph 멀티홉 탐색 + OKF 3-Layer Wiki/원문 청크 근거 결합",
                    "role_en": "BigQuery/Spanner Property Graph multi-hop traversal + OKF 3-Layer Wiki/chunk grounding",
                },
            ],
            "reference_studios": REFERENCE_STUDIOS,
            "code_exposure_boundary": CODE_EXPOSURE_BOUNDARY,
            "stage_unified_map": STAGE_UNIFIED_MAP,
        }

    def get_resource_summary(self, verify_gcp: bool = False) -> Dict[str, Any]:
        """Returns the resource manifest and optionally includes live GCP resource verification."""
        manifest = self.get_resource_manifest()
        if verify_gcp:
            manifest["verification"] = self.verify_ready_resources()
        return manifest

    def verify_ready_resources(self, engine: str = "bigquery") -> Dict[str, Any]:
        """Verifies that all Ready-to-Use GCP & local ontology resources are live and accessible."""
        t0 = time.perf_counter()
        bq_check = execute_bq_sql(
            f"""
            SELECT
              (SELECT COUNT(*) FROM `{self.fq}.tb_customer_contract`) AS contracts,
              (SELECT COUNT(*) FROM `{self.fq}.tb_device_master`) AS devices,
              (SELECT COUNT(*) FROM `{self.fq}.tb_plan_master`) AS plans,
              (SELECT COUNT(*) FROM `{self.fq}.tb_subsidy_policy`) AS policies,
              (SELECT COUNT(*) FROM `{self.fq}.tb_doc_chunks`) AS doc_chunks,
              (SELECT COUNT(*) FROM `{self.fq}.tb_domain_rules`) AS domain_rules
            """,
            project_id=self.project_id,
            location=self.location,
        )
        gql_check = execute_bq_sql(
            f"""
            SELECT COUNT(*) AS graph_paths
            FROM GRAPH_TABLE(`{self.graph_id}`
              MATCH (d:DeviceNode)-[:HAS_SUBSIDY_POLICY]->(p:PlanNode)<-[:APPLIES_TO_PLAN]-(r:DomainRuleNode)
              COLUMNS (d.device_id, p.plan_id, r.rule_id))
            """,
            project_id=self.project_id,
            location=self.location,
        )

        wiki_dir = os.path.join(self.root_dir, "data/llm_wiki")
        if not os.path.isdir(wiki_dir):
            wiki_dir = os.path.join(self.root_dir, "data/output/ontology")
        wiki_files = sorted(os.listdir(wiki_dir)) if os.path.isdir(wiki_dir) else []
        rules_path = os.path.join(wiki_dir, "business_rules.json")
        wf_path = os.path.join(wiki_dir, "business_workflows.json")
        wcq_path = os.path.join(wiki_dir, "workflow_cqs.json")

        rules_count = len(json.load(open(rules_path, encoding="utf-8")).get("rules", [])) if os.path.exists(rules_path) else 0
        wf_count = len(json.load(open(wf_path, encoding="utf-8")).get("workflows", [])) if os.path.exists(wf_path) else 0
        wcq_count = len(json.load(open(wcq_path, encoding="utf-8")).get("workflow_cqs", [])) if os.path.exists(wcq_path) else 0

        try:
            gcs_items = list_gcs_objects(prefix="ontology/", bucket=self.gcs_bucket)
            gcs_count = len(gcs_items)
        except Exception:
            gcs_count = 0

        sp_info = check_spanner_available(self.project_id, self.spanner_instance_id, self.spanner_database_id)
        bq_row = (bq_check.get("rows") or [{}])[0]
        gql_row = (gql_check.get("rows") or [{}])[0]

        bq_ok = bq_check.get("status") == "SUCCESS"
        gql_ok = gql_check.get("status") == "SUCCESS"
        stages = {
            "stage1": {
                "status": "READY" if bq_ok else "PARTIAL",
                "summary": f"BigQuery DW ({self.fq}): contracts={bq_row.get('contracts', 0)}, devices={bq_row.get('devices', 0)}, plans={bq_row.get('plans', 0)}, policies={bq_row.get('policies', 0)}, chunks={bq_row.get('doc_chunks', 0)}",
            },
            "stage2": {
                "status": "READY" if (gcs_count > 0 or len(wiki_files) > 0) else "PARTIAL",
                "summary": f"OKF 3-Layer Wiki (gs://{self.gcs_bucket}/ontology/={gcs_count} objs, local={len(wiki_files)} files) · domain_rules={bq_row.get('domain_rules', 0)}",
            },
            "stage3": {
                "status": "READY" if gql_ok else "PARTIAL",
                "summary": f"Property Graph ({self.graph_id}): multi-hop paths={gql_row.get('graph_paths', 0)} · Workflows={wf_count} · Rules={rules_count}",
            },
            "stage4": {
                "status": "READY",
                "summary": f"3 Domain Business Tools (mcp_lookup_customer_profile, mcp_calculate_penalty_rule, mcp_query_graph_and_wiki) + AI FDE ({DEFAULT_GEMINI_MODEL})",
            },
            "stage5": {
                "status": "READY",
                "summary": f"6-Layer Lineage Spec & Golden/Workflow CQ Suite (WCQ={wcq_count}, Spanner={sp_info.get('available', False)})",
            },
        }

        return {
            "status": "READY" if bq_ok and gql_ok else "PARTIAL",
            "elapsed_ms": round((time.perf_counter() - t0) * 1000, 1),
            "stages": stages,
            "bigquery_dw": {
                "dataset": self.fq,
                "status": bq_check.get("status"),
                "job_id": bq_check.get("job_id"),
                "counts": bq_row,
            },
            "bigquery_property_graph": {
                "graph_id": self.graph_id,
                "status": gql_check.get("status"),
                "job_id": gql_check.get("job_id"),
                "verified_multi_hop_paths": gql_row.get("graph_paths", 0),
            },
            "okf_3layer_wiki_and_workflows": {
                "gcs_bucket": f"gs://{self.gcs_bucket}/ontology/",
                "gcs_object_count": gcs_count,
                "local_wiki_files": wiki_files,
                "business_rules_count": rules_count,
                "business_workflows_count": wf_count,
                "workflow_cqs_count": wcq_count,
            },
            "cloud_spanner_graph": sp_info,
        }
