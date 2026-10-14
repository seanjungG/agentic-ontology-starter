# Copyright (c) 2026 Sean Jung (seanjung@google.com). All Rights Reserved.
# Non-Commercial Use Only: Methodology & Docs under CC BY-NC-ND 4.0; Source Code under PolyForm Noncommercial License 1.0.0.
# Commercial use, paid consulting/SI/PoC delivery, or production deployment requires prior written permission from seanjung@google.com.

# -*- coding: utf-8 -*-
"""
resource_connector.py — Minimal Resource Connector, Selective Flow Composer & 2-Tier MCP Guide (Starter v3.0)

Core Design:
1. Ready-to-Use GCP Resource Connection (`connect_my_resources()` / `OntologyResourceConnector`):
   Connects directly to BigQuery DW & SQL:2023 Property Graph, GCS 3-Layer OKF Wiki, Cloud Spanner Graph, and Vertex AI (`gemini-3.8-flash`).
2. Selective Flow Composer (`P1/P2/P3` Data Paths x `W1/W2/W3` Workflow Extraction Points x `Gate G2-W`):
   Allows teams to start with the exact subset of the `v1-mcp` architecture they need (Document-Only `P1+W1`, Ledger-Only `P2+W2`, or Full Hybrid `P3+W3`).
3. 2-Tier MCP Architecture & Customization Guide:
   - Tier 1 (Build-Time Core MCP — `aos-builder-core-mcp`, 8 Tools): Compiles raw docs & DW tables into OKF Wiki, `W1~W3` workflows, and BigQuery Property Graph.
   - Tier 2 (Runtime Domain MCP — `src/agent/mcp_server.py`, 3 Tools): Executes deterministic domain business logic bound 1:1 to workflow nodes (`D4.5`).
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
        "name_ko": "스타터 스튜디오 (Minimal v1-MCP Flow Starter)",
        "name_en": "Starter Studio (Minimal v1-MCP Flow Starter)",
        "url": "https://agentic-ontology-starter-924723860007.asia-northeast3.run.app/",
        "domain": "Telecom Subsidy & Contract (De-identified Starter Sample)",
        "tabs": "Getting Started · 1. v1-MCP Flow Grid · 2. MCP Guide · 3. Wiki & Graph · 4. Workflow & Agent · 5. Lineage & Eval",
        "resources": "seanjung-poc.starter_ontology_dw.STARTER_ONTOLOGY_GRAPH + gs://seanjung-poc-starter-ontology",
    },
    "lguplus_reference_studio": {
        "id": "lguplus_mcp",
        "name_ko": "기준 스튜디오 #1 · LG U+ v1-MCP 엔터프라이즈 스튜디오 (12-Tab Full Standard)",
        "name_en": "Reference Standard #1 · LG U+ v1-MCP Enterprise Studio (12-Tab Full Standard)",
        "url": "https://agentic-ontology-studio-lguplus-mcp-924723860007.asia-northeast3.run.app/",
        "domain": "LG U+ Mobile Subsidy, Penalty & Retention Consultation",
        "tabs": "12-Tab Full Standard (0. Overview ~ 11. Evaluation · 6-Layer × P1/P2/P3 × Gate G2-W)",
        "resources": "177 Anchors · 141 Wiki Nodes · 39 Rules · 10 Workflows (W1:1/W2:2/W3:7) · 14/14 WCQ · 4 Graphs",
    },
    "hnh_reference_studio": {
        "id": "hnh_mcp",
        "name_ko": "기준 스튜디오 #2 · LG생활건강(H&H) v1-MCP 스튜디오 (12-Tab Full Standard)",
        "name_en": "Reference Standard #2 · LG H&H v1-MCP Cosmetics Compliance Studio",
        "url": "https://hnh-agentic-ontology-studio-mcp-384182013777.asia-northeast3.run.app/",
        "domain": "LG H&H Cosmetics Labeling & Advertising Compliance",
        "tabs": "12-Tab Full Standard (0. Overview ~ 11. Evaluation · 6-Layer × P1/P2/P3 × Gate G2-W)",
        "resources": "49 Docs · 341 Wiki Nodes · 24 Rules · 10 Workflows · 20/20 WCQ · 43 BQ Tables",
    },
    "builder_core_mcp_server": {
        "id": "aos_builder_core_mcp",
        "name_ko": "코어 빌더 MCP 서버 (`aos-builder-core-mcp` · 8 Tools)",
        "name_en": "Builder Core MCP Server (`aos-builder-core-mcp` · 8 Tools)",
        "url": "https://aos-builder-core-mcp-924723860007.asia-northeast3.run.app/mcp/builder",
        "domain": "6-Stage Automated Ontology & Studio Compiler MCP",
        "tabs": "JSON-RPC 2.0 MCP Endpoint (`/mcp/builder`) & REST (`/api/mcp/builder/execute`)",
        "resources": "Stage 1 Scope ➔ Gate 0 Parse ➔ Stage 2 Wiki ➔ Stage 3 Rules/WF ➔ Stage 4 BQG ➔ Stage 5 CQ Eval ➔ Stage 6 Provision",
    },
}

SELECTIVE_FLOW_PRESETS: Dict[str, Dict[str, Any]] = {
    "flow_p1_w1": {
        "id": "flow_p1_w1",
        "badge": "Flow A · Document-First (P1 + W1)",
        "title_ko": "문서·위키 중심 경량 플로우 (P1 + W1)",
        "title_en": "Document & Wiki-First Lightweight Flow (P1 + W1)",
        "desc_ko": "정형 DW 테이블 없이 정책 가이드·약관·매뉴얼 문서만으로 시작합니다. 원문을 3-Layer OKF 위키로 컴파일하고 규정 판정 워크플로우(W1)와 위키 근거 탐색 도구를 즉시 구성합니다.",
        "desc_en": "Start with policy guides and manuals only (no DW tables required). Compiles documents into a 3-Layer OKF Wiki and runs normative decision workflows (W1) with grounded citations.",
        "paths": ["P1"],
        "workflows": ["W1"],
        "gate_g2w": True,
        "active_layers": ["L1", "L2", "L4", "L5", "L6"],
        "required_gcp": ["GCS OKF Wiki Bucket (or Local data/llm_wiki)", "BigQuery tb_doc_chunks", "Vertex AI (gemini-3.8-flash)"],
        "builder_mcp_stages": [
            "mcp_builder_inspect_and_scope_stage1",
            "mcp_builder_parse_documents_gate0",
            "mcp_builder_compile_okf_wiki_stage2",
            "mcp_builder_extract_rules_workflows_stage3",
        ],
        "runtime_mcp_tools": ["mcp_query_graph_and_wiki"],
        "recommended_tabs": ["getting-started", "flow-grid", "mcp-guide", "wiki-graph", "workflow-agent"],
    },
    "flow_p2_w2": {
        "id": "flow_p2_w2",
        "badge": "Flow B · Ledger-First (P2 + W2)",
        "title_ko": "정형 원장·그래프 중심 플로우 (P2 + W2)",
        "title_en": "Structured DW Ledger & Graph Flow (P2 + W2)",
        "desc_ko": "기존 BigQuery/Spanner 정형 마스터·거래 원장(DW)에서 시작합니다. 테이블 스키마와 FK 관계를 Property Graph로 묶고 원장 상태 검증 워크플로우(W2) 및 원장 조회 도구를 실행합니다.",
        "desc_en": "Start from existing BigQuery/Spanner structured DW tables. Synthesizes SQL:2023 Property Graph views and runs ledger state verification workflows (W2) and deterministic SQL lookups.",
        "paths": ["P2"],
        "workflows": ["W2"],
        "gate_g2w": False,
        "active_layers": ["L1", "L3", "L4", "L5", "L6"],
        "required_gcp": ["BigQuery DW Dataset (or Cloud Spanner)", "BigQuery Property Graph (GRAPH_TABLE)", "Vertex AI (gemini-3.8-flash)"],
        "builder_mcp_stages": [
            "mcp_builder_inspect_and_scope_stage1",
            "mcp_builder_extract_rules_workflows_stage3",
            "mcp_builder_synthesize_bqg_stage4",
        ],
        "runtime_mcp_tools": ["mcp_lookup_customer_profile", "mcp_query_graph_and_wiki"],
        "recommended_tabs": ["getting-started", "flow-grid", "mcp-guide", "wiki-graph", "workflow-agent"],
    },
    "flow_p3_w3": {
        "id": "flow_p3_w3",
        "badge": "Flow C · Full v1-MCP Hybrid (P1 + P2 + P3 × W1 + W2 + W3 + Gate G2-W)",
        "title_ko": "v1-MCP 엔터프라이즈 풀 하이브리드 표준 (P1·P2·P3 × W1·W2·W3)",
        "title_en": "Full v1-MCP Enterprise Hybrid Standard (P1·P2·P3 × W1·W2·W3)",
        "desc_ko": "LG U+ 및 LG생활건강(H&H) v1-MCP 프로덕션 표준과 동일한 전체 플로우입니다. 비정형 규정 위키(P1)와 정형 DW 원장 그래프(P2)를 브릿지 엣지(P3) 및 Gate G2-W 단일 출처 원칙으로 통합하고 3종 도메인 MCP 도구와 AI FDE를 구동합니다.",
        "desc_en": "The complete production architecture used in LG U+ and LG H&H v1-MCP studios. Unifies OKF Wiki (P1) and DW Property Graph (P2) via Concept-to-DW Bridge Edges (P3), Gate G2-W single-source constants, 3 Domain MCP tools, and AI FDE.",
        "paths": ["P1", "P2", "P3"],
        "workflows": ["W1", "W2", "W3"],
        "gate_g2w": True,
        "active_layers": ["L1", "L2", "L3", "L4", "L5", "L6"],
        "required_gcp": [
            "BigQuery DW & Property Graph (STARTER_ONTOLOGY_GRAPH)",
            "GCS 3-Layer OKF Wiki (gs://seanjung-poc-starter-ontology/ontology/)",
            "Cloud Spanner Graph (Optional Dual-Engine)",
            "Vertex AI (gemini-3.8-flash)",
        ],
        "builder_mcp_stages": [
            "mcp_builder_get_domain_spec_template",
            "mcp_builder_inspect_and_scope_stage1",
            "mcp_builder_parse_documents_gate0",
            "mcp_builder_compile_okf_wiki_stage2",
            "mcp_builder_extract_rules_workflows_stage3",
            "mcp_builder_synthesize_bqg_stage4",
            "mcp_builder_verify_gates_and_cqs_stage5",
            "mcp_builder_provision_studio_infra_stage6",
        ],
        "runtime_mcp_tools": [
            "mcp_lookup_customer_profile",
            "mcp_calculate_penalty_rule",
            "mcp_query_graph_and_wiki",
        ],
        "recommended_tabs": ["getting-started", "flow-grid", "mcp-guide", "wiki-graph", "workflow-agent", "lineage-eval"],
    },
}

V1_MCP_FLOW_ARCHITECTURE = {
    "data_paths": [
        {
            "id": "P1",
            "name_ko": "P1 · 비정형 문서 경로 (Normative Docs ➔ OKF Wiki)",
            "name_en": "P1 · Unstructured Document Path (Normative Docs ➔ OKF Wiki)",
            "flow_ko": "정책 가이드·약관 PDF/MD ➔ Gate 0 파싱(>=95%) & SHA-256 앵커 ➔ OKF 3-Layer 위키(Summary · Entities · Concepts) & graph.properties 정책 상수",
            "flow_en": "Policy Guides/Manuals ➔ Gate 0 Parsing (>=95%) & SHA-256 Anchors ➔ OKF 3-Layer Wiki (Summary · Entities · Concepts) & graph.properties",
        },
        {
            "id": "P2",
            "name_ko": "P2 · 정형 DW 원장 경로 (Structured DW ➔ Property Graph)",
            "name_en": "P2 · Structured DW Ledger Path (Structured DW ➔ Property Graph)",
            "flow_ko": "고객계약·단말·요금제·지원금 마스터 테이블 ➔ PK/FK 무결성 검증 & PII 비식별화 ➔ BigQuery SQL:2023 GRAPH_TABLE & Spanner ISO GQL 노드/엣지",
            "flow_en": "Customer/Device/Plan/Subsidy DW Tables ➔ PK/FK Check & De-identification ➔ BigQuery SQL:2023 GRAPH_TABLE & Spanner ISO GQL Nodes/Edges",
        },
        {
            "id": "P3",
            "name_ko": "P3 · 하이브리드 통합·상담 경로 (Concept-DW Bridge & Dialogue)",
            "name_en": "P3 · Hybrid Bridge & Consultation Path (Concept-DW Bridge & Dialogue)",
            "flow_ko": "P1 위키 정책 노드(`DomainRuleNode`) ↔ P2 정형 원장 노드(`PlanNode`/`DeviceNode`)를 `APPLIES_TO_PLAN` 브릿지 엣지로 결합하여 멀티홉 추론 수행",
            "flow_en": "Bridges P1 Wiki Policy Nodes (`DomainRuleNode`) ↔ P2 DW Ledger Nodes (`PlanNode`/`DeviceNode`) via `APPLIES_TO_PLAN` edges for multi-hop reasoning",
        },
    ],
    "workflow_points": [
        {
            "id": "W1",
            "profile": "guide",
            "name_ko": "W1 · 규정 판정 워크플로우 (Normative Guide Workflow)",
            "name_en": "W1 · Normative Guide Workflow",
            "desc_ko": "P1 위키 문서의 규정·면제 조항만으로 분기 판정 (예: 시니어/복지 특례 면제, 당일 원복 규정)",
            "desc_en": "Decision branching grounded purely in P1 normative wiki rules (e.g., senior/welfare exemption, same-day rollback rule)",
        },
        {
            "id": "W2",
            "profile": "ledger",
            "name_ko": "W2 · 원장 상태 검증 워크플로우 (Ledger State Workflow)",
            "name_en": "W2 · Ledger State Verification Workflow",
            "desc_ko": "P2 정형 DW 원장의 계약 상태·경과일수·정산 금액 정합성 조회 및 검증",
            "desc_en": "Verifies customer contract status, elapsed days, and billing ledger consistency on P2 structured DW tables",
        },
        {
            "id": "W3",
            "profile": "full",
            "name_ko": "W3 · 규정+원장 통합 정산 워크플로우 (Full Hybrid Workflow)",
            "name_en": "W3 · Integrated Policy + Ledger Settlement Workflow",
            "desc_ko": "P1 정책 상수(180일, 45,000원 안전선) + P2 고객 원장(가입일, 지급 지원금)을 결합해 일할 위약금과 24개월 TCO를 결정론적으로 산출",
            "desc_en": "Combines P1 policy constants (180-day window, 45,000 KRW floor) + P2 customer ledger to deterministically compute prorated penalty & 24M TCO",
        },
    ],
    "gate_g2w": {
        "id": "G2-W",
        "name_ko": "Gate G2-W · 정책 상수 단일 출처 & 역방향 피드백 불변식",
        "name_en": "Gate G2-W · Single-Source Policy Constants & Reverse Feedback Gate",
        "rules_ko": [
            "G2-W1 (단일 출처): 모든 정책 수치(180일, 25%, 45,000원 등)는 오직 위키 Frontmatter `graph.properties`에만 선언하며 코드 하드코딩을 금지합니다.",
            "G2-W2 (슬롯 소싱): 워크플로우 입력 슬롯은 `lookup`(원장 조회) · `derive`(파생 계산) · `user`(고객 질문) 출처를 명시합니다.",
            "G2-W3 (종단 상태 코드): 모든 워크플로우 END 노드는 표준 상태 어휘(`ACTIVE`, `EXEMPT`, `PRORATED_PENALTY` 등)로 귀결됩니다.",
            "D4.5 (도구 1:1 바인딩): 워크플로우 RULE/DECISION 노드는 런타임 도메인 MCP 도구와 1:1로 바인딩됩니다.",
        ],
        "rules_en": [
            "G2-W1 (Single Source): Policy constants (180 days, 25%, 45,000 KRW) are authored ONLY in wiki frontmatter `graph.properties` (zero hardcoded numbers).",
            "G2-W2 (Slot Sourcing): Every workflow slot declares its source (`lookup` from DW, `derive` expression, or `user` input).",
            "G2-W3 (End State Vocabulary): Every workflow END node resolves to a canonical state/outcome code.",
            "D4.5 (1:1 Tool Binding): Every executable RULE node binds 1:1 to a deterministic Domain MCP tool.",
        ],
    },
    "six_layers": [
        {"layer": "Layer 1", "id": "L1", "name_ko": "1. 원천 데이터 (Raw Docs & DW Tables)", "name_en": "1. Raw Sources (Docs & DW Tables)", "paths": ["P1", "P2"]},
        {"layer": "Layer 2", "id": "L2", "name_ko": "2. OKF 3-Layer 위키 허브 (Summary · Entities · Concepts)", "name_en": "2. OKF 3-Layer Wiki Hub", "paths": ["P1", "P3"]},
        {"layer": "Layer 3", "id": "L3", "name_ko": "3. 시맨틱 & 물리 Property Graph (BigQuery / Spanner)", "name_en": "3. Dual Property Graph (BigQuery / Spanner)", "paths": ["P2", "P3"]},
        {"layer": "Layer 4", "id": "L4", "name_ko": "4. 비즈니스 룰 & W1/W2/W3 워크플로우 (+ Gate G2-W)", "name_en": "4. Business Rules & W1/W2/W3 Workflows (+ Gate G2-W)", "paths": ["P1", "P2", "P3"]},
        {"layer": "Layer 5", "id": "L5", "name_ko": "5. 도메인 비즈니스 MCP 도구 3종 (D4.5 1:1 바인딩)", "name_en": "5. Domain Business MCP Tools (3 Tools · D4.5 Bound)", "paths": ["P1", "P2", "P3"]},
        {"layer": "Layer 6", "id": "L6", "name_ko": "6. 에이전트 런타임 & 6-Layer 리니지/CQ 평가 (AI FDE)", "name_en": "6. AI FDE Runtime & 6-Layer Lineage / CQ Eval", "paths": ["P1", "P2", "P3"]},
    ],
}

MCP_ARCHITECTURE_GUIDE: Dict[str, Any] = {
    "overview_ko": "Agentic Ontology는 역할을 명확히 분리한 2-Tier MCP 아키텍처를 사용합니다: ① 빌드 타임에 원천 문서·테이블로부터 위키·워크플로우·그래프를 자동 구축하는 코어 빌더 MCP(`aos-builder-core-mcp`, 8종 도구)와 ② 런타임에 워크플로우 노드에 바인딩되어 실제 고객/원장/그래프 질의를 무환각 실행하는 도메인 비즈니스 MCP(`src/agent/mcp_server.py`, 3종 도구)입니다.",
    "overview_en": "Agentic Ontology separates concerns into a 2-Tier MCP Architecture: (1) Build-Time Core MCP (`aos-builder-core-mcp`, 8 tools) that compiles raw docs & DW tables into OKF Wiki, W1~W3 workflows, and BigQuery Property Graph, and (2) Runtime Domain Business MCP (`src/agent/mcp_server.py`, 3 tools) bound 1:1 to workflow nodes for zero-hallucination execution.",
    "tier1_builder_core_mcp": {
        "server_name": "aos-builder-core-mcp",
        "endpoint_url": "https://aos-builder-core-mcp-924723860007.asia-northeast3.run.app/mcp/builder",
        "rest_execute_url": "https://aos-builder-core-mcp-924723860007.asia-northeast3.run.app/api/mcp/builder/execute",
        "mcp_client_config_snippet": {
            "mcpServers": {
                "aos-builder-core-mcp": {
                    "type": "http",
                    "url": "https://aos-builder-core-mcp-924723860007.asia-northeast3.run.app/mcp/builder",
                }
            }
        },
        "how_to_use_ko": [
            "1단계 (MCP 등록): Gemini CLI (`~/.gemini/settings.json`), Claude Code, 또는 Cursor의 `mcpServers`에 `aos-builder-core-mcp` URL을 등록합니다.",
            "2단계 (도메인 스펙 생성): `mcp_builder_get_domain_spec_template`를 호출해 내 도메인용 `build_spec` 템플릿(`source_config`, `wiki_spec`, `workflow_spec`, `graph_spec`)을 받습니다.",
            "3단계 (선택형 또는 전 과정 실행): 내가 선택한 플로우(Flow A/B/C)에 맞춰 개별 Stage 도구(`stage1`~`stage6`)를 순서대로 호출하거나 `mcp_builder_run_full_pipeline`으로 원클릭 컴파일합니다.",
        ],
        "how_to_use_en": [
            "Step 1 (Register MCP): Add `aos-builder-core-mcp` HTTP endpoint to Gemini CLI (`~/.gemini/settings.json`), Claude Code, or Cursor `mcpServers`.",
            "Step 2 (Generate Build Spec): Call `mcp_builder_get_domain_spec_template` to scaffold your domain's `build_spec` (`source_config`, `wiki_spec`, `workflow_spec`, `graph_spec`).",
            "Step 3 (Run Selective or Full Pipeline): Invoke individual stage tools (`stage1`~`stage6`) matching your selected flow (Flow A/B/C), or run `mcp_builder_run_full_pipeline`.",
        ],
        "tools": [
            {
                "tool_name": "mcp_builder_get_domain_spec_template",
                "stage": "INIT",
                "flows": ["P1", "P2", "P3"],
                "role_ko": "신규 프로젝트 온보딩을 위한 선언형 `build_spec` JSON 스키마 및 도메인 프로필 템플릿 반환",
                "role_en": "Returns the declarative `build_spec` JSON schema and starter templates for new domain onboarding",
                "key_args": "domain_profile ('lguplus_subsidy' | 'hnh_compliance' | 'custom_starter')",
                "outputs": "build_spec template (source_config, wiki_spec, workflow_spec, graph_spec)",
            },
            {
                "tool_name": "mcp_builder_inspect_and_scope_stage1",
                "stage": "STAGE 1",
                "flows": ["P1", "P2", "P3"],
                "role_ko": "원천 문서 번들(P1) 및 정형 DW 테이블(P2) 인벤토리 스캔, PK/FK 무결성 점검 및 `project.json` 초기화",
                "role_en": "Scans raw document bundles (P1) and DW tables (P2), checks PK/FK integrity, and initializes `project.json`",
                "key_args": "project_id, domain_profile, build_spec",
                "outputs": "projects/<id>/project.json, Stage 1 inventory summary",
            },
            {
                "tool_name": "mcp_builder_parse_documents_gate0",
                "stage": "GATE 0",
                "flows": ["P1", "P3"],
                "role_ko": "비정형 가이드·대화록 원문을 문단/표 단위로 무손실 파싱하고 문단별 SHA-256 해시 앵커 및 보존율(>=95%) 검증",
                "role_en": "Parses unstructured guides/dialogues into SHA-256 anchored sections and verifies Gate 0 parse fidelity (>=95%)",
                "key_args": "project_id, min_fidelity (default 0.95)",
                "outputs": "parsed/*.md, gate0_report.json",
            },
            {
                "tool_name": "mcp_builder_compile_okf_wiki_stage2",
                "stage": "STAGE 2",
                "flows": ["P1", "P3"],
                "role_ko": "파싱된 원문에서 3-Layer OKF 위키(`01_summary`, `02_entities`, `03_concepts`)와 Frontmatter `graph.properties` 정책 상수를 컴파일 및 Gate 2 감사",
                "role_en": "Compiles 3-Layer OKF Wiki (`01_summary`, `02_entities`, `03_concepts`) and `graph.properties` policy constants with Gate 2 audit",
                "key_args": "project_id, sync_to_gcs",
                "outputs": "ontology/{01_summary,02_entities,03_concepts}/*.md, gate2_wiki_report.json",
            },
            {
                "tool_name": "mcp_builder_extract_rules_workflows_stage3",
                "stage": "STAGE 3",
                "flows": ["W1", "W2", "W3", "G2-W"],
                "role_ko": "비즈니스 룰(`BR-*`), 선택형 `W1/W2/W3` 의사결정 워크플로우 DAG, `Gate G2-W` 정책 상수 매핑 및 `D4.5` 도메인 MCP 도구 바인딩 생성",
                "role_en": "Extracts business rules (`BR-*`), `W1/W2/W3` workflow DAGs, `Gate G2-W` policy mappings, and `D4.5` domain MCP tool bindings",
                "key_args": "project_id, workflow_spec, sync_to_gcs",
                "outputs": "business_rules.json, business_workflows.json, workflow_cqs.json, workflow_binding_registry.json",
            },
            {
                "tool_name": "mcp_builder_synthesize_bqg_stage4",
                "stage": "STAGE 4",
                "flows": ["P2", "P3"],
                "role_ko": "BigQuery 데이터셋에 정형 원장 노드(P2) + 위키 정책 노드(P1) + 브릿지 엣지(P3) 테이블을 적재하고 `CREATE OR REPLACE PROPERTY GRAPH` DDL 실행",
                "role_en": "Materializes DW nodes (P2) + Wiki rule nodes (P1) + Bridge edges (P3) in BigQuery and executes `CREATE OR REPLACE PROPERTY GRAPH` DDL",
                "key_args": "project_id, target_dataset_id, graph_name, execute_ddl",
                "outputs": "BigQuery Property Graph & gate3_bqg_report.json",
            },
            {
                "tool_name": "mcp_builder_verify_gates_and_cqs_stage5",
                "stage": "STAGE 5",
                "flows": ["P1", "P2", "P3", "W1", "W2", "W3"],
                "role_ko": "Gate 0 / Gate 2 / Gate G2-W / Gate 3 / Gate 4(`D4.5`) 및 워크플로우 CQ(`WCQ-*`) 결정론 리플레이 전수 검증",
                "role_en": "Verifies Gate 0, Gate 2, Gate G2-W, Gate 3, Gate 4 (`D4.5`), and deterministic Workflow CQ (`WCQ-*`) replay",
                "key_args": "project_id, compare_with_baseline",
                "outputs": "evals/stage5_verification_report.json",
            },
            {
                "tool_name": "mcp_builder_provision_studio_infra_stage6",
                "stage": "STAGE 6",
                "flows": ["P1", "P2", "P3"],
                "role_ko": "스튜디오 레지스트리(`assets_registry.json`, `cq_registry.json`), 호환 뷰, GCS 위키 버킷 동기화 및 `project.json` 최종 프로비저닝 (`mcp_builder_run_full_pipeline`으로 Stage 1~6 일괄 실행 가능)",
                "role_en": "Provisions Studio registries, compatibility views, GCS wiki sync, and final `project.json` (or run Stage 1~6 end-to-end via `mcp_builder_run_full_pipeline`)",
                "key_args": "project_id, studio_url, sync_to_gcs",
                "outputs": "evals/stage6_provisioning_report.json, ready-to-serve Studio bundle",
            },
        ],
        "custom_build_spec_example": {
            "project_id": "my_custom_ontology",
            "domain_profile": "custom_starter",
            "domain_name": "내 엔터프라이즈 도메인 온톨로지",
            "source_config": {
                "source_bundles": {
                    "01_guides": {"role": "normative", "description": "정책 가이드 및 규정 문서 (P1)"},
                    "03_sample_tables": {"role": "state", "description": "BigQuery/Spanner 정형 마스터 및 거래 원장 (P2)"},
                }
            },
            "wiki_spec": {
                "policy_property_keys": [
                    {"key": "mandatory_days", "unit": "일", "example": "180일", "description": "의무 유지 일수 (Gate G2-W1 단일 출처)"},
                    {"key": "baseline_fee_krw", "unit": "원", "example": "45,000원", "description": "위약금 면제 최저 요금제 안전선"},
                ]
            },
            "workflow_spec": {
                "extraction_points": {"W1": "guide", "W2": "ledger", "W3": "full"},
                "domain_mcp_tools": [
                    "mcp_lookup_customer_profile",
                    "mcp_calculate_penalty_rule",
                    "mcp_query_graph_and_wiki",
                ],
            },
            "graph_spec": {
                "gcp_project_id": "seanjung-poc",
                "target_dataset_id": "starter_ontology_dw",
                "graph_name": "STARTER_ONTOLOGY_GRAPH",
                "gcs_bucket": "seanjung-poc-starter-ontology",
            },
        },
    },
    "tier2_runtime_domain_mcp": {
        "server_class": "DomainMcpServer",
        "source_file": "src/agent/mcp_server.py",
        "orchestrator_file": "src/agent/reasoning_engine.py",
        "tools": [
            {
                "tool_name": "mcp_lookup_customer_profile",
                "flow_binding": "P2 · W2 (원장 상태 조회 · Ledger Lookup)",
                "role_ko": "BigQuery/Spanner 정형 DW 원장(`tb_customer_contract`, `tb_device_master`, `tb_plan_master`, `tb_subsidy_policy`)에서 고객 약정 상태, 단말 출고가, 공시/추가지원금, 할부원금을 결정론적 SQL로 조회합니다.",
                "role_en": "Deterministic SQL lookup on structured DW ledgers (`tb_customer_contract`, `tb_device_master`, `tb_plan_master`, `tb_subsidy_policy`) for contract status, device price, and subsidy.",
                "input_schema": {"customer_id": "CUST_DEMO_001 (optional)", "device_name": "Galaxy S25 Ultra 256GB (optional)", "plan_name": "5G 프리미어 에센셜 (85,000원) (optional)"},
                "sample_args": {"customer_id": "CUST_DEMO_001"},
                "customize_tip_ko": "내 도메인의 마스터/거래 테이블(예: 주문 원장, 보험 계약 원장, 설비 센서 원장) SELECT 쿼리로 `_mcp_lookup_customer_profile()`의 SQL만 교체하세요.",
                "customize_tip_en": "Replace the SELECT query inside `_mcp_lookup_customer_profile()` with your domain's master/transaction ledger tables.",
            },
            {
                "tool_name": "mcp_calculate_penalty_rule",
                "flow_binding": "P3 · W3 · Gate G2-W (규정+원장 통합 정산 · Rule Math)",
                "role_ko": "워크플로우 `DECISION`/`RULE` 노드에 1:1 바인딩되어, 위키 정책 상수(`mandatory_retention_days=180`, `baseline_fee_krw=45000`, 시니어 면제)와 고객 원장을 결합해 일할 위약금 및 24개월 TCO 비교를 무환각 SQL로 계산합니다.",
                "role_en": "Bound 1:1 to workflow `DECISION`/`RULE` nodes; combines wiki policy constants (`180d`, `45,000 KRW floor`, welfare exemption) with customer ledger data to compute prorated penalties and 24M TCO in SQL.",
                "input_schema": {"customer_id": "CUST_DEMO_001", "target_plan_name": "5G 라이트+ (55,000원)", "elapsed_days": 95},
                "sample_args": {"customer_id": "CUST_DEMO_001", "target_plan_name": "5G 슬림 (45,000원)", "elapsed_days": 95},
                "customize_tip_ko": "내 도메인의 핵심 판정·정산 수식(예: 여신 한도 DSR 계산, 화장품 배합 한도 판정, 물류 SLA 패널티 산식)을 `_mcp_calculate_penalty_rule()`에 구현하세요.",
                "customize_tip_en": "Implement your domain's core compliance or settlement formula (e.g., loan DSR math, ingredient limit check, SLA penalty) in `_mcp_calculate_penalty_rule()`.",
            },
            {
                "tool_name": "mcp_query_graph_and_wiki",
                "flow_binding": "P1 + P2 + P3 · W1/W3 (Property Graph 멀티홉 탐색 + OKF 위키 앵커)",
                "role_ko": "BigQuery `GRAPH_TABLE(STARTER_ONTOLOGY_GRAPH)` 또는 Spanner GQL로 `(DeviceNode)-[:HAS_SUBSIDY_POLICY]->(PlanNode)<-[:APPLIES_TO_PLAN]-(DomainRuleNode)` 멀티홉 경로를 탐색하고 `tb_doc_chunks`의 SHA-256 원문 앵커를 결합 반환합니다.",
                "role_en": "Executes multi-hop `GRAPH_TABLE` traversal across `(DeviceNode)-[:HAS_SUBSIDY_POLICY]->(PlanNode)<-[:APPLIES_TO_PLAN]-(DomainRuleNode)` and joins SHA-256 document chunk anchors.",
                "input_schema": {"device_name": "Galaxy S25 Ultra 256GB", "plan_name": "5G 프리미어 에센셜 (85,000원)", "engine": "bigquery | spanner"},
                "sample_args": {"device_name": "Galaxy S25 Ultra 256GB", "engine": "bigquery"},
                "customize_tip_ko": "내 Property Graph의 노드/엣지 패턴(`MATCH (a)-[r]->(b)`)으로 `_mcp_query_graph_and_wiki()`의 `GRAPH_TABLE` 구문을 커스텀하세요.",
                "customize_tip_en": "Customize the `GRAPH_TABLE(... MATCH ...)` pattern in `_mcp_query_graph_and_wiki()` to match your Property Graph node and edge labels.",
            },
        ],
        "customization_3steps_code": """# [Step 1] Connect your GCP resources in .env or Python (src/resource_connector.py)
from src.resource_connector import connect_my_resources
conn = connect_my_resources(
    project_id="my-gcp-project",
    dataset_id="my_ontology_dw",
    gcs_bucket="my-ontology-wiki-bucket",
)

# [Step 2] Customize or add a domain tool in src/agent/mcp_server.py (DomainMcpServer)
#   1) Register tool metadata in DomainMcpServer.get_tool_catalog()
#   2) Implement _mcp_<your_tool_name>(self, args, jobs) using self._run(sql, jobs)
#   3) Bind the tool name in data/llm_wiki/business_workflows.json (Contract 4 / D4.5)

# [Step 3] Run deterministic tool or full AI FDE cycle (src/agent/reasoning_engine.py)
from src.agent.reasoning_engine import AiFdeAgentEngine
agent = AiFdeAgentEngine(project_id="my-gcp-project")
result = agent.execute_cycle("CUST_DEMO_001 고객이 95일째에 45,000원 요금제로 하향하면 위약금이 얼마인가요?")""",
    },
}

CODE_EXPOSURE_BOUNDARY = {
    "principle_ko": "복잡한 빌드 파이프라인 코드는 코어 빌더 MCP(`aos-builder-core-mcp`)로 추상화하고, 스타터 레포지토리는 준비된 GCP 온톨로지 리소스(BigQuery Property Graph, GCS 3-Layer Wiki, W1~W3 워크플로우)에 직결되는 커넥터(`resource_connector.py`)와 런타임 도메인 MCP 도구 3종(`mcp_server.py`), 에이전트 추론 엔진(`reasoning_engine.py`)만 최소한으로 유지합니다.",
    "principle_en": "Heavy build compiler pipelines are abstracted into `aos-builder-core-mcp`. This Starter repo keeps only the minimal runtime core: the GCP resource connector (`resource_connector.py`), 3 customizable Domain MCP tools (`mcp_server.py`), the AI FDE agent (`reasoning_engine.py`), and the selective `v1-mcp` studio (`studio_server.py`).",
    "minimal_repo_files": [
        {"file": "src/resource_connector.py", "role_ko": "내 GCP 리소스 연결(`connect_my_resources`), 선택형 플로우(`P1/P2/P3 × W1/W2/W3`) 프리셋 및 2-Tier MCP 가이드", "role_en": "GCP resource connector (`connect_my_resources`), selective flow presets (`P1/P2/P3 × W1/W2/W3`), and 2-Tier MCP guide"},
        {"file": "src/gcp_client.py", "role_ko": "외부 SDK 의존성 없는 순수 Python 표준 라이브러리 기반 BigQuery / Spanner / GCS / Vertex AI REST 클라이언트", "role_en": "Zero-dependency Python stdlib REST client for BigQuery, Cloud Spanner, GCS, and Vertex AI Gemini"},
        {"file": "src/agent/mcp_server.py", "role_ko": "워크플로우 노드에 1:1 바인딩되는 런타임 도메인 비즈니스 MCP 도구 3종 (`DomainMcpServer`)", "role_en": "3 Runtime Domain Business MCP tools bound 1:1 to workflow nodes (`DomainMcpServer`)"},
        {"file": "src/agent/reasoning_engine.py", "role_ko": "Vertex AI `gemini-3.8-flash` 기반 슬롯 추출, 도메인 MCP 도구 체이닝 및 SHA-256 근거 합성 엔진 (`AiFdeAgentEngine`)", "role_en": "Vertex AI `gemini-3.8-flash` slot extraction, domain MCP tool chaining, and grounded synthesis (`AiFdeAgentEngine`)"},
        {"file": "src/web/studio_server.py", "role_ko": "`0. Getting Started` + 선택형 `v1-mcp` 플로우 구성기 + `MCP 역할/커스텀 가이드` + 라이브 실행 스튜디오 UI", "role_en": "`0. Getting Started` + Selective `v1-mcp` Flow Composer + `MCP Guide` + Live Studio UI"},
    ],
}

STAGE_UNIFIED_MAP = [
    {
        "stage": "Getting Started",
        "title_ko": "3-Step 온보딩 · 선택형 플로우(P1/P2/P3 × W1/W2/W3) 구성 & GCP 리소스 직결",
        "title_en": "3-Step Onboarding · Selective Flow (P1/P2/P3 × W1/W2/W3) Composer & GCP Resource Check",
        "starter_tab": "?tab=getting-started",
        "reference_tab": "0. Overview (Project & Flow Selector)",
        "notebook_ko": "notebooks/ko/stage0_overview_walkthrough_ko.ipynb",
        "notebook_en": "notebooks/en/stage0_overview_walkthrough_en.ipynb",
    },
    {
        "stage": "Stage 1 · P1/P2",
        "title_ko": "원천 문서(Gate 0) & 정형 DW 원장 자산 인벤토리",
        "title_en": "Raw Document (Gate 0) & Structured DW Ledger Asset Inventory",
        "starter_tab": "?tab=flow-grid",
        "reference_tab": "1. Asset (정형/비정형/룰/워크플로우/CQ 카탈로그)",
        "notebook_ko": "notebooks/ko/stage1_asset_and_cq_ko.ipynb",
        "notebook_en": "notebooks/en/stage1_asset_and_cq_en.ipynb",
    },
    {
        "stage": "Stage 2 · P1 Wiki",
        "title_ko": "OKF 3-Layer 온톨로지 위키 허브 & `graph.properties` 단일 출처 상수",
        "title_en": "OKF 3-Layer Ontology Wiki Hub & `graph.properties` Single-Source Constants",
        "starter_tab": "?tab=wiki-graph",
        "reference_tab": "2. Ontology Wiki · 3. Ontology Semantic · 4. Wiki Agent",
        "notebook_ko": "notebooks/ko/stage2_wiki_and_semantic_graph_ko.ipynb",
        "notebook_en": "notebooks/en/stage2_wiki_and_semantic_graph_en.ipynb",
    },
    {
        "stage": "Stage 3 · P2/P3 Graph & W1~W3",
        "title_ko": "BigQuery/Spanner 듀얼 Property Graph & W1/W2/W3 의사결정 워크플로우 (Gate G2-W)",
        "title_en": "BigQuery/Spanner Dual Property Graph & W1/W2/W3 Decision Workflows (Gate G2-W)",
        "starter_tab": "?tab=wiki-graph",
        "reference_tab": "5. BigQuery Graph · 6. BQG Agent · 8. Workflow",
        "notebook_ko": "notebooks/ko/stage3_property_graph_bigquery_spanner_ko.ipynb",
        "notebook_en": "notebooks/en/stage3_property_graph_bigquery_spanner_en.ipynb",
    },
    {
        "stage": "Stage 4 · 2-Tier MCP & AI FDE",
        "title_ko": "`aos-builder-core-mcp`(8종) · 런타임 도메인 MCP 도구(3종) & AI FDE 에이전트 실행",
        "title_en": "`aos-builder-core-mcp` (8 Tools) · Runtime Domain MCP (3 Tools) & AI FDE Execution",
        "starter_tab": "?tab=workflow-agent",
        "reference_tab": "9. Workflow Agent · 10. AI FDE",
        "notebook_ko": "notebooks/ko/stage4_agent_and_mcp_execution_ko.ipynb",
        "notebook_en": "notebooks/en/stage4_agent_and_mcp_execution_en.ipynb",
    },
    {
        "stage": "Stage 5 · Lineage & CQ Eval",
        "title_ko": "6-Layer 엔드투엔드 데이터 리니지 & Golden/Workflow/Boundary CQ 검증",
        "title_en": "6-Layer End-to-End Data Lineage & Golden/Workflow/Boundary CQ Evaluation",
        "starter_tab": "?tab=lineage-eval",
        "reference_tab": "7. Lineage · 11. Evaluation",
        "notebook_ko": "notebooks/ko/stage5_lineage_and_evaluation_ko.ipynb",
        "notebook_en": "notebooks/en/stage5_lineage_and_evaluation_en.ipynb",
    },
]


class OntologyResourceConnector:
    """
    Minimal, direct connector to Ready-to-Use Google Cloud Ontology Resources,
    Selective Flow Presets (`P1/P2/P3 x W1/W2/W3`), and 2-Tier MCP Guide.
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
        """Returns the complete starter manifest: GCP resources, selective flow presets, v1-MCP architecture, and 2-Tier MCP guide."""
        return {
            "version": "3.0.0-minimal",
            "architecture_mode": "MINIMAL_V1_MCP_STARTER (Selective Flow P1/P2/P3 x W1/W2/W3 + 2-Tier MCP)",
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
                "builder_core_mcp_url": MCP_ARCHITECTURE_GUIDE["tier1_builder_core_mcp"]["endpoint_url"],
            },
            "selective_flow_presets": SELECTIVE_FLOW_PRESETS,
            "v1_mcp_flow_architecture": V1_MCP_FLOW_ARCHITECTURE,
            "mcp_architecture_guide": MCP_ARCHITECTURE_GUIDE,
            "domain_business_tools": MCP_ARCHITECTURE_GUIDE["tier2_runtime_domain_mcp"]["tools"],
            "reference_studios": REFERENCE_STUDIOS,
            "code_exposure_boundary": CODE_EXPOSURE_BOUNDARY,
            "stage_unified_map": STAGE_UNIFIED_MAP,
        }

    def get_resource_summary(self, verify_gcp: bool = False) -> Dict[str, Any]:
        manifest = self.get_resource_manifest()
        if verify_gcp:
            manifest["verification"] = self.verify_ready_resources()
        return manifest

    def verify_ready_resources(self, engine: str = "bigquery") -> Dict[str, Any]:
        """Verifies live connectivity to BigQuery DW tables, Property Graph, GCS 3-Layer Wiki, local rules/workflows, and Spanner."""
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
                "summary": f"2-Tier MCP (Builder Core 8 Tools + Runtime Domain 3 Tools) + AI FDE ({DEFAULT_GEMINI_MODEL})",
            },
            "stage5": {
                "status": "READY",
                "summary": f"6-Layer Lineage & CQ Suite (WCQ={wcq_count}, Spanner={sp_info.get('available', False)})",
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


def connect_my_resources(
    project_id: Optional[str] = None,
    dataset_id: Optional[str] = None,
    gcs_bucket: Optional[str] = None,
    spanner_instance_id: Optional[str] = None,
    spanner_database_id: Optional[str] = None,
    verify: bool = False,
) -> Dict[str, Any]:
    """One-line helper for notebooks and scripts to bind custom or default GCP ontology resources."""
    conn = OntologyResourceConnector(
        project_id=project_id or os.environ.get("GCP_PROJECT_ID", DEFAULT_PROJECT_ID),
        dataset_id=dataset_id or os.environ.get("BQ_DATASET_ID", DEFAULT_DATASET_ID),
        gcs_bucket=gcs_bucket or os.environ.get("GCS_BUCKET_NAME", DEFAULT_GCS_BUCKET),
        spanner_instance_id=spanner_instance_id or os.environ.get("SPANNER_INSTANCE_ID", DEFAULT_SPANNER_INSTANCE),
        spanner_database_id=spanner_database_id or os.environ.get("SPANNER_DATABASE_ID", DEFAULT_SPANNER_DATABASE),
    )
    return conn.get_resource_summary(verify_gcp=verify)
