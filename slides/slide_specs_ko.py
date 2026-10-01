# -*- coding: utf-8 -*-
# Copyright (c) 2026 Sean Jung (seanjung@google.com). All rights reserved.
# Licensed under CC BY-NC-ND 4.0 (Methodology & Slide Deck) & PolyForm Noncommercial 1.0.0 (Code).

"""
18-Slide Korean Training Curriculum Specification for Agentic Ontology Starter Methodology.
Covers 8-Phase Engineering Flow, 5-Stage Lifecycle (Stage 1..5), 3-Track Model,
5-File Swap Playbook, AI Coding Agent Bootstrap, and 8 Industry Archetypes.
"""

SLIDES_KO = [
    {
        "slide_no": 1,
        "badge": "MODULE 00 · EXECUTIVE OVERVIEW",
        "accent": "#1A73E8",
        "title": "5-Stage 에이전틱 온톨로지 엔지니어링 방법론",
        "subtitle": "정형 DW(BigQuery)와 비정형 정책 문서(OKF v0.2)를 Property Graph(ISO GQL) · 8종 MCP · 2-Pass Gemini 에이전트로 통합하는 표준 교육 과정",
        "banner_img": "stage0_overview_flow_ko.png",
        "cards": [
            {
                "tag": "PILLAR 1 · UNSTRUCTURED",
                "title": "원문 해시 앵커 & 3-Layer 위키",
                "accent": "#1A73E8",
                "bullets": [
                    "문단별 SHA-256 해시(anchor_<12hex>)로 tb_doc_chunks 적재",
                    "OKF v0.2 JSON-LD + L1(요약)·L2(엔티티)·L3(개념·규칙) 위키 컴파일",
                    "에이전트 최종 답변에서 원문 조항 문단까지 결정론적 역추적 보장"
                ]
            },
            {
                "tag": "PILLAR 2 · PROPERTY GRAPH",
                "title": "Zero-ETL 듀얼 Property Graph",
                "accent": "#0F9D58",
                "bullets": [
                    "별도 외부 그래프 DB 복제 없이 CREATE OR REPLACE PROPERTY GRAPH 선언",
                    "6개 노드 테이블 × 4개 엣지 테이블을 STARTER_ONTOLOGY_GRAPH로 투영",
                    "BigQuery(분석·다중 홉 GQL) + Cloud Spanner(실시간 인터락 DDL) 지원"
                ]
            },
            {
                "tag": "PILLAR 3 · AGENT & GATE",
                "title": "8종 도메인 MCP & 2-Pass 에이전트",
                "accent": "#4F46E5",
                "bullets": [
                    "위약금 일할 계산·24개월 TCO 비교를 LLM 암산 대신 MCP SQL 산식으로 실행",
                    "Vertex AI Gemini(gemini-3.8-flash) 2-Pass 추론 및 4대 가드레일 상태 분리",
                    "Golden CQ 5건 + 경계값 10건×5회(50회) 벤치마크 통과 후 Cloud Run 배포"
                ]
            }
        ],
        "table": {
            "headers": ["핵심 구성 축", "구현 기술 스택 (Google Cloud Native + Custom)", "핵심 산출물 코드/경로", "검증 기준"],
            "rows": [
                ["1. 데이터 & 위키 계층", "BigQuery DW (10 Tables) + GCS 3-Layer OKF Wiki", "pipeline/ingest.py · data/llm_wiki/ko/", "10개 테이블 정합성 · SHA-256 앵커"],
                ["2. 시맨틱 & 그래프 계층", "BigQuery SQL:2023 Property Graph (ISO GQL) + Spanner DDL", "pipeline/graph_builder.py · create_property_graph.sql", "중복 노드 0건 · 다중 홉 GQL 경로"],
                ["3. 도구 & 추론 계층", "DomainMcpServer (8 Tools) + AiFdeAgentEngine (2-Pass)", "src/agent/mcp_server.py · reasoning_engine.py", "GROUNDED / INSUFFICIENT / MATCH_NOT_FOUND"],
                ["4. 리니지 & 배포 계층", "End-to-End Lineage + Validator + Terraform Cloud Run", "pipeline/validator.py · terraform/*.tf", "Golden CQ 5/5 · Boundary 50회 실측"]
            ]
        },
        "takeaway": "핵심 원칙: 비정형 정책 조항(SHA-256 앵커)과 정형 원장(PK/FK)을 단일 그래프와 결정론적 MCP 도구로 묶어 에이전트의 임의 추측을 원천 차단한다.",
        "speaker_notes": (
            "[강사 가이드 — Slide 01: 과정 개요 및 핵심 철학]\n"
            "• 환영 및 교육 목적: 본 교육 과정은 'agentic-ontology-starter'의 5-Stage 엔지니어링 방법론을 통해 엔터프라이즈 환경에서 정형 DW 테이블과 비정형 업무 가이드를 어떻게 하나의 온톨로지 그래프와 에이전트로 통합하는지 단계별로 실습합니다.\n"
            "• 4대 핵심 설계 원칙 강조:\n"
            "  1) 원문 해시 앵커 보존: 문서 문단마다 SHA-256 앞 12자리(anchor_<12hex>)를 부여해 에이전트가 인용한 근거를 원문까지 추적합니다.\n"
            "  2) Zero-ETL 그래프 투영: 데이터를 외부 그래프 DB로 복제하지 않고 BigQuery 테이블 위에 바로 PROPERTY GRAPH 뷰를 선언합니다.\n"
            "  3) 결정론적 산식 실행: 위약금·TCO 계산은 LLM이 암산하지 않고 MCP 도구의 SQL/Python 산식이 계산합니다.\n"
            "  4) 가드레일 상태 분리: GROUNDED, MATCH_NOT_FOUND, INSUFFICIENT_PARAMETERS, BQ_QUERY_ERROR 4가지 상태를 엄격히 구분합니다.\n"
            "• 라이선스 고지: 방법론·문서·슬라이드는 CC BY-NC-ND 4.0, 코드는 PolyForm Noncommercial 1.0.0이 적용되며 상업적 활용 시 seanjung@google.com 사전 협의가 필요합니다."
        )
    },
    {
        "slide_no": 2,
        "badge": "MODULE 00 · PROBLEM & MOTIVATION",
        "accent": "#D97706",
        "title": "왜 기존 단순 RAG와 Text-to-SQL은 엔터프라이즈에서 실패하는가?",
        "subtitle": "비정형 규정 문서와 정형 원장 데이터가 단절될 때 발생하는 3대 구조적 실패 모드와 에이전틱 온톨로지의 해법",
        "banner_img": None,
        "cards": [
            {
                "tag": "FAILURE MODE 1",
                "title": "정형·비정형 컨텍스트 단절",
                "accent": "#DC2626",
                "bullets": [
                    "고객 계약·요금제 원장은 BigQuery에, 위약금 산식·면제 조항은 마크다운/PDF에 분리",
                    "단순 벡터 RAG는 고객의 실제 가입 요금제·경과일(90일) 원장을 조회하지 못함",
                    "단순 Text-to-SQL은 '180일 이내 하향 시 일할 반환' 같은 비정형 예외 규정을 모름"
                ]
            },
            {
                "tag": "FAILURE MODE 2",
                "title": "LLM 자유 생성 암산 오류",
                "accent": "#D97706",
                "bullets": [
                    "복합 수식((500,000 - 300,000) × (180 - 90) / 180)을 프롬프트 추론에만 의존",
                    "시니어 복지 면제(SENIOR_EXEMPT → 0원) 등 우선순위 분기 조건 누락 발생",
                    "질문을 반복할 때마다 숫자나 적용 조항이 달라지는 일관성 결여"
                ]
            },
            {
                "tag": "FAILURE MODE 3",
                "title": "근거 추적 불능 & 가드레일 부재",
                "accent": "#4F46E5",
                "bullets": [
                    "문서 개정 시 벡터 청크 인덱스가 밀려 어느 조항을 근거로 답했는지 감사 불가",
                    "카탈로그에 없는 요금제나 필수 파라미터(경과일) 누락 시에도 임의 숫자를 생성",
                    "프로덕션 배포 전 정량적 릴리스 게이트(Golden CQ + Boundary 테스트) 부재"
                ]
            }
        ],
        "table": {
            "headers": ["비교 항목", "단순 Vector RAG", "단독 Text-to-SQL", "5-Stage 에이전틱 온톨로지 (본 방법론)"],
            "rows": [
                ["비정형 정책 + 정형 DW 결합", "불가 (문서 조각만 검색)", "불가 (테이블만 조회, 규정 미인지)", "edge_rule_applies_to_plan 브릿지로 그래프 단일 결합"],
                ["수치/위약금/TCO 계산 주체", "LLM 토큰 생성 (암산 오류 위험)", "LLM이 매번 SQL을 즉석 생성 (JOIN 누락 위험)", "검증된 도메인 MCP 도구 내부 결정론적 SQL 산식 실행"],
                ["원문 근거 추적 (Auditability)", "유사도 상위 청크 추정 (해시 없음)", "문서 근거 인용 불가", "DOC_CHUNK_001~005 + SHA-256 해시 + BQ Job ID 명시"],
                ["파라미터 누락 / 미존재 엔티티", "임의 가정으로 답변 생성", "빈 결과(0행)를 잘못 해석해 오답 생성", "INSUFFICIENT_PARAMETERS / MATCH_NOT_FOUND 즉시 반환"]
            ]
        },
        "takeaway": "해법의 핵심: LLM에게는 '카탈로그 기반 파라미터 추출(Pass 1)'과 '검증된 도구 결과 요약(Pass 2)'만 맡기고, 데이터 탐색과 계산은 Property Graph와 MCP가 수행한다.",
        "speaker_notes": (
            "[강사 가이드 — Slide 02: 기존 접근법의 한계와 온톨로지 도입 배경]\n"
            "• 현업 사례 설명: 통신사 공시지원금 위약금 문의를 예로 들면, 고객(CUST_DEMO_001)의 가입 단말·요금제·지원금은 정형 테이블에 있고, '180일 의무유지 및 시니어 면제' 규정은 업무 가이드 문서에 있습니다.\n"
            "• 단순 RAG는 문서는 찾지만 고객 원장을 모르고, Text-to-SQL은 테이블은 읽지만 문서의 면제 규정 순서를 모릅니다.\n"
            "• 또한 LLM에게 직접 SQL을 짜게 하거나 암산을 시키면, 조건이 빠진 질문('요금제 바꾸면 위약금 얼마야?')에서도 임의로 날짜를 가정해 틀린 금액을 말합니다.\n"
            "• 따라서 본 방법론은 (1) 시맨틱 브릿지 테이블, (2) BigQuery Property Graph, (3) 결정론적 MCP 도구, (4) 2-Pass 가드레일 루프로 이 세 가지 문제를 구조적으로 해결합니다."
        )
    },
    {
        "slide_no": 3,
        "badge": "MODULE 00 · 8-PHASE & 5-STAGE MAP",
        "accent": "#1A73E8",
        "title": "8단계 엔지니어링 흐름 & 5-Stage 라이프사이클 전체 지도",
        "subtitle": "1. 준비 → 2. 분석 → 3. 파싱 → 4. 통합 → 5. 구축 → 6. 에이전트 → 7. 답변(GQL) → 8. 검증의 엔드투엔드 파이프라인",
        "banner_img": "stage0_overview_flow_ko.png",
        "cards": [
            {
                "tag": "PHASE 1~4 (STAGE 1 & 2)",
                "title": "자산 스코핑 · 위키 · 시맨틱 브릿지",
                "accent": "#1A73E8",
                "bullets": [
                    "Phase 1~2 (Stage 1): CQ 정의, 마스터 CSV 4종·가이드 2종 인입, 비식별 검증",
                    "Phase 3~4 (Stage 2): SHA-256 청킹, 3-Layer 위키, 규칙→요금제 브릿지(12행)",
                    "산출물: D1.1~D1.4 및 D2.1~D2.6 (10개 BigQuery 테이블 적재 완료)"
                ]
            },
            {
                "tag": "PHASE 5 (STAGE 3)",
                "title": "Property Graph & ISO GQL",
                "accent": "#0F9D58",
                "bullets": [
                    "Phase 5 (Stage 3): 6개 노드·4개 엣지 테이블을 STARTER_ONTOLOGY_GRAPH로 선언",
                    "BigQuery GQL GRAPH_TABLE 다중 홉 경로 검증 및 Spanner DDL 동시 생성",
                    "산출물: D3.1~D3.4 (create_property_graph.sql, graph_topology.json)"
                ]
            },
            {
                "tag": "PHASE 6~8 (STAGE 4 & 5)",
                "title": "8종 MCP · 2-Pass 에이전트 · 게이트",
                "accent": "#4F46E5",
                "bullets": [
                    "Phase 6~7 (Stage 4): Stage MCP 5종 + Runtime MCP 3종 및 2-Pass Gemini 추론",
                    "Phase 8 (Stage 5): 4계층 데이터 리니지, Golden CQ 5건, 경계값 50회 벤치마크",
                    "산출물: D4.1~D4.4 및 D5.1~D5.5 (Terraform Cloud Run 배포 패키지)"
                ]
            }
        ],
        "table": {
            "headers": ["8단계 엔지니어링 흐름", "Stage", "스튜디오 탭", "대응 Stage MCP 도구", "산출물 ID", "실습 노트북 (KO / EN)"],
            "rows": [
                ["0. 전체 흐름 투어", "Overview", "0. Overview", "Stage 1~5 일괄/개별 실행", "-", "stage0_overview_walkthrough_{ko,en}.ipynb"],
                ["1. 준비 · 2. 분석", "Stage 1", "Stage 1. Asset", "mcp_stage1_asset_discovery", "D1.1 ~ D1.4", "stage1_asset_and_cq_{ko,en}.ipynb"],
                ["3. 파싱 · 4. 통합", "Stage 2", "Stage 2. Wiki & Semantic", "mcp_stage2_wiki_and_semantic", "D2.1 ~ D2.6", "stage2_wiki_and_semantic_graph_{ko,en}.ipynb"],
                ["5. 구축 (Build Graph)", "Stage 3", "Stage 3. Property Graph", "mcp_stage3_property_graph", "D3.1 ~ D3.4", "stage3_property_graph_bigquery_spanner_{ko,en}.ipynb"],
                ["6. 에이전트 · 7. 답변", "Stage 4", "Stage 4. Agent & MCP", "mcp_stage4_agent_orchestration (+런타임 3종)", "D4.1 ~ D4.4", "stage4_agent_and_mcp_execution_{ko,en}.ipynb"],
                ["8. 검증 (Verify & Gate)", "Stage 5", "Stage 5. Lineage & Eval", "mcp_stage5_lineage_and_eval", "D5.1 ~ D5.5", "stage5_lineage_and_evaluation_{ko,en}.ipynb"]
            ]
        },
        "takeaway": "모든 Stage는 (1) 방법론 문서(methodology/ko,en), (2) 스튜디오 탭(6-Tab), (3) MCP 도구, (4) 한/영 실습 노트북(12종)과 1:1로 정확히 매핑된다.",
        "speaker_notes": (
            "[강사 가이드 — Slide 03: 8단계 엔지니어링 흐름과 5-Stage 매핑]\n"
            "• 슬라이드 상단의 아키텍처 배너(stage0_overview_flow_ko.png)를 가리키며 8단계 흐름이 어떻게 5개 Stage로 묶이는지 설명합니다.\n"
            "• 본 스타터팩의 가장 큰 특징은 문서로만 존재하는 방법론이 아니라, 각 Stage가 웹 스튜디오 탭(Stage 1~5), 실행 가능한 MCP 도구(mcp_stage1..5), 그리고 주피터 노트북(stage0..5)과 1:1로 대응된다는 점입니다.\n"
            "• 전체 파이프라인은 루트의 `python3 run_pipeline.py` 명령 하나로 Stage 1부터 Stage 5까지 순차 실행할 수 있습니다."
        )
    },
    {
        "slide_no": 4,
        "badge": "MODULE 00 · ADOPTION TRACKS & GCP NATIVE",
        "accent": "#0F9D58",
        "title": "3-Track 도입 모델 (`Lite` · `Standard` · `Full`) & GCP Native 원칙",
        "subtitle": "조직의 데이터 준비도에 따른 단계적 도입 트랙(`config/starter_config.json`)과 Google Cloud 표준 스펙 분계선",
        "banner_img": None,
        "cards": [
            {
                "tag": "TRACK 1 · LITE",
                "title": "비정형 문서 기반 퀵스타트",
                "accent": "#1A73E8",
                "bullets": [
                    "활성 Stage: Stage 1 → Stage 2 → Stage 4 (Stage 3 생략)",
                    "그래프 엔진: none (3-Layer 위키 + tb_domain_rules 조회)",
                    "적합 환경: 정형 DW 연동 전 정책 매뉴얼·약관·계산 수식만으로 에이전트를 즉시 검증할 때"
                ]
            },
            {
                "tag": "TRACK 2 · STANDARD (권장)",
                "title": "정형 DW + 문서 하이브리드 그래프",
                "accent": "#0F9D58",
                "bullets": [
                    "활성 Stage: Stage 1 → Stage 2 → Stage 3 → Stage 4",
                    "그래프 엔진: bigquery (STARTER_ONTOLOGY_GRAPH) + Spanner DDL 병행",
                    "적합 환경: 마스터/약정 테이블과 정책 문서를 ISO GQL 다중 홉 추론으로 통합 시연할 때"
                ]
            },
            {
                "tag": "TRACK 3 · FULL",
                "title": "전주기 리니지 · 50회 평가 · 배포",
                "accent": "#4F46E5",
                "bullets": [
                    "활성 Stage: Stage 1 → Stage 2 → Stage 3 → Stage 4 → Stage 5",
                    "그래프 엔진: bigquery + End-to-End Lineage + Dual Validator Gate",
                    "적합 환경: 감사 추적 리니지, 경계값 10×5 벤치마크, Terraform Cloud Run 프로덕션 배포"
                ]
            }
        ],
        "table": {
            "headers": ["아키텍처 계층", "Google Cloud Native 표준 기능 (우선 채택)", "스타터팩 커스텀 확장 영역 (Custom Extension)", "설계 근거"],
            "rows": [
                ["데이터 & 그래프", "BigQuery Managed Tables, Cloud Storage, SQL:2023 Property Graph", "2-Layer 안티 리던던시 빌더, 시맨틱 브릿지(edge_rule_applies_to_plan)", "외부 그래프 DB 복제 제거 및 문서-테이블 직결"],
                ["온톨로지 & 위키", "OKF v0.2 JSON-LD 스키마 호환 구조", "SHA-256 문단 해시 청커(anchor_<12hex>), Karpathy 3-Layer LLM-Wiki", "문단 단위 불변 근거 앵커링 및 LLM 가독성 확보"],
                ["MCP 도구 계층", "BigQuery Python Client, Parameterized SQL/GQL", "8종 도메인 MCP 서버 (Stage 5종 + Runtime 3종)", "결정론적 위약금/TCO 산식 및 다중 홉 GQL 캡슐화"],
                ["에이전트 & 인프라", "Vertex AI Gemini (gemini-3.8-flash), Cloud Run, Terraform IaC", "2-Pass 추론 루프(슬롯 검증 + 가드레일 상태 분리), 6-Tab 스튜디오", "임의 추측 차단 및 5-Stage 시각적 거버넌스 제공"]
            ]
        },
        "takeaway": "GCP Native First: 인프라·저장소·그래프 엔진·LLM은 100% Google Cloud 관리형 서비스를 사용하고, 도메인 브릿지와 결정론적 MCP만 경량 파이썬으로 확장한다.",
        "speaker_notes": (
            "[강사 가이드 — Slide 04: 3-Track 도입 전략 및 GCP Native 분계선]\n"
            "• 고객사 PoC나 사내 프로젝트 착수 시 가장 먼저 결정할 사항은 `config/starter_config.json`의 `active_track`입니다.\n"
            "• 문서만 있다면 `lite` 트랙으로 반나절 만에 위키+에이전트를 띄우고, CSV/BigQuery 테이블이 준비되면 `standard` 트랙으로 Property Graph를 켭니다. 최종 릴리스 검증 시 `full` 트랙으로 전환합니다.\n"
            "• 하단 표는 아키텍트들이 자주 묻는 '어디까지가 GCP 순정 기능이고 어디부터가 스타터팩 확장인가?'를 명확히 구분해 줍니다."
        )
    },
    {
        "slide_no": 5,
        "badge": "MODULE 01 · STAGE 1 OVERVIEW",
        "accent": "#1A73E8",
        "title": "Stage 1. 자산 탐색 · 도메인 스코핑 · CQ 정의 (`D1.1`~`D1.4`)",
        "subtitle": "에이전트가 답해야 할 핵심 역량 질문(CQ)을 먼저 확정하고, 필요한 최소 테이블·문서만 선별해 BigQuery에 적재",
        "banner_img": "stage1_prepare_analyze_flow_ko.png",
        "cards": [
            {
                "tag": "STEP 1 · CQ-FIRST SCOPING",
                "title": "역량 질문(CQ) 우선 스코핑",
                "accent": "#1A73E8",
                "bullets": [
                    "백과사전식 전사 테이블 수집을 지양하고 CQ 해결에 필수적인 자산만 선별",
                    "가이드 문서 2종(정책·복지면제) + 정형 CSV 6종으로 도메인 범위 확정",
                    "용어사전(business_glossary.json)으로 비즈니스 핵심 용어 4종 표준화"
                ]
            },
            {
                "tag": "STEP 2 · ATOMIC INGESTION",
                "title": "트랜잭션 기반 BigQuery 적재",
                "accent": "#0F9D58",
                "bullets": [
                    "Terraform(terraform/bigquery.tf)으로 10개 테이블 스키마 선언적 생성",
                    "pipeline/ingest.py의 run_ingest()가 CSV·청크를 TRUNCATE → INSERT 적재",
                    "하드코딩 없이 data/input/ 파일만을 단일 진실 공급원(SSOT)으로 사용"
                ]
            },
            {
                "tag": "STEP 3 · STAGE 1 MCP",
                "title": "mcp_stage1_asset_discovery",
                "accent": "#4F46E5",
                "bullets": [
                    "profile_tables: __TABLES__ 메타데이터에서 10개 테이블 행 수·바이트 실시간 조회",
                    "tag_pii_governance: 고객 ID가 ^CUST_DEMO_[0-9]{3}$ 비식별 패턴인지 전수 검사",
                    "non_deidentified_ids == 0 이어야 Gate 1 통과"
                ]
            }
        ],
        "table": {
            "headers": ["입력 데이터 경로 (`data/input/`)", "대상 BigQuery 테이블", "건수", "역할 및 핵심 컬럼"],
            "rows": [
                ["01_guides/sample_policy_guide.md 외 1종", "tb_doc_chunks", "5행", "DOC_CHUNK_001~005 원문 문단 및 SHA-256 해시 앵커"],
                ["03_tables/devices.csv · plans.csv · subsidies.csv", "tb_device_master · tb_plan_master · tb_subsidy_policy", "4 / 6 / 6행", "단말 출고가, 요금제 월정액·할인율, 요금제별 공시·추가지원금"],
                ["03_tables/customer_contracts.csv", "tb_customer_contract", "6행", "CUST_DEMO_001~006 가입 단말, 요금제, 경과일(elapsed_days), 복지코드"],
                ["03_tables/domain_rules.csv · rule_plan_edges.csv", "tb_domain_rules · edge_rule_applies_to_plan", "4 / 12행", "4대 비즈니스 규칙 산식 및 규칙→요금제 시맨틱 브릿지"]
            ]
        },
        "takeaway": "Stage 1 핵심: 스키마를 먼저 그리지 말고 '에이전트가 답해야 할 질문(Golden CQ)'을 먼저 정의한 뒤, 그 질문에 필요한 테이블과 문서만 인입하라.",
        "speaker_notes": (
            "[강사 가이드 — Slide 05: Stage 1 자산 탐색 및 스코핑]\n"
            "• 많은 온톨로지 프로젝트가 실패하는 이유는 질문(Use Case) 없이 수백 개 테이블부터 모델링하기 때문입니다.\n"
            "• Stage 1에서는 반드시 `golden_competency_questions.json`을 먼저 정의하고, 이에 답하기 위해 필요한 마스터 테이블 4종, 규칙/브릿지 2종, 가이드 2종만 스코핑합니다.\n"
            "• 실습 포인트: 스튜디오 `Stage 1. Asset` 탭에서 `▶ Stage 1 MCP 실행`을 클릭하거나 `stage1_asset_and_cq_ko.ipynb`를 실행해 `table_inventory`(10개 테이블)와 `non_deidentified_ids: 0`을 확인합니다."
        )
    },
    {
        "slide_no": 6,
        "badge": "MODULE 01 · STAGE 1 DEEP DIVE",
        "accent": "#1A73E8",
        "title": "Stage 1 심화: Golden CQ 명세 구조와 독립 정답 검증 SQL (`Gate 1`)",
        "subtitle": "LLM-as-a-Judge의 주관성을 배제하기 위해 모든 핵심 질문마다 인간이 확정한 정답 수식(`expected_math`)과 BigQuery 검증 SQL을 함께 등록",
        "banner_img": None,
        "cards": [
            {
                "tag": "ANATOMY OF A CQ",
                "title": "Golden CQ 6대 필수 필드",
                "accent": "#1A73E8",
                "bullets": [
                    "query: 에이전트에게 입력할 자연어 비즈니스 질문",
                    "expected_math: 채점 기준이 되는 정답 수치 JSON (예: {\"penalty\": 100000})",
                    "verification_sql: BigQuery에서 독립적으로 정답을 산출하는 검증 쿼리",
                    "grounded_chunk: 답변이 반드시 인용해야 하는 원문 청크 ID (예: DOC_CHUNK_002)"
                ]
            },
            {
                "tag": "EXAMPLE · CQ-02",
                "title": "180일 일할 위약금 검증 예시",
                "accent": "#0F9D58",
                "bullets": [
                    "질문: CUST_DEMO_001 고객이 90일 시점에 5G 스탠다드 요금제로 하향 시 위약금은?",
                    "원장: 초기 지원금 500,000원 → 변경 요금제 지원금 300,000원 (차액 200,000원)",
                    "산식: 200,000 × (180 - 90) / 180 = 100,000원 (DOC_CHUNK_002 인용 필수)"
                ]
            },
            {
                "tag": "GATE 1 CHECKLIST",
                "title": "Stage 1 통과 기준 (Gate 1)",
                "accent": "#4F46E5",
                "bullets": [
                    "1) Golden CQ 5건 모두 expected_math · verification_sql · grounded_chunk 보유",
                    "2) verification_sql 실행 결과와 expected_math 100% 일치 (SQL_MATCH)",
                    "3) pii_check.non_deidentified_ids == 0 & 10개 테이블 행 수 일치"
                ]
            }
        ],
        "table": {
            "headers": ["CQ ID", "검증 시나리오 요약", "기대 정답 (`expected_math`)", "필수 인용 청크", "주요 검증 대상 MCP 도구"],
            "rows": [
                ["CQ-01", "CUST_DEMO_001 고객의 가입 단말·요금제·총지원금·할부원금 조회", "total_subsidy: 575,000 / principal: 675,000", "DOC_CHUNK_001", "mcp_lookup_customer_profile"],
                ["CQ-02", "CUST_DEMO_001 고객 90일 경과 시 5G 스탠다드 하향 위약금 계산", "penalty_krw: 100,000", "DOC_CHUNK_002", "mcp_calculate_penalty_rule"],
                ["CQ-03", "CUST_DEMO_003 (시니어 복지 면제 대상) 요금제 하향 시 위약금 면제 확인", "penalty_krw: 0 (EXEMPT_WELFARE)", "DOC_CHUNK_004", "mcp_calculate_penalty_rule"],
                ["CQ-04", "핵심 플래그십 256GB + 5G 시그니처 24개월 공시지원금 vs 25% 선택약정 TCO 비교", "subsidy_tco: 3,422,500 / contract_tco: 3,590,000", "DOC_CHUNK_005", "mcp_calculate_penalty_rule"],
                ["CQ-05", "5G 프리미엄 요금제에 연결된 비즈니스 규칙 및 원문 해시 앵커 다중 홉 조회", "matched_rules: 3 / chunk: DOC_CHUNK_001~003", "DOC_CHUNK_002", "mcp_query_graph_and_wiki"]
            ]
        },
        "takeaway": "Gate 1 원칙: Stage 1에서 정의한 Golden CQ 5건과 경계값 10건(boundary_cases.json)이 곧 Stage 5 배포 승인의 자동 채점 기준이 된다.",
        "speaker_notes": (
            "[강사 가이드 — Slide 06: Golden CQ 5건 상세 및 Gate 1]\n"
            "• 표에 제시된 CQ-01부터 CQ-05까지 5가지 질문이 전체 파이프라인을 관통하는 테스트 케이스입니다.\n"
            "• 왜 `verification_sql`이 중요한지 강조하십시오: 에이전트가 답한 숫자가 맞는지 확인할 때 또 다른 LLM에게 채점하게 하면 환각을 놓칠 수 있습니다. BigQuery SQL이 계산한 `expected_math`와 에이전트 답변을 대조해야 객관적인 100% 정확도 측정이 가능합니다."
        )
    },
    {
        "slide_no": 7,
        "badge": "MODULE 02 · STAGE 2 OVERVIEW",
        "accent": "#0F9D58",
        "title": "Stage 2. 비정형 문서 파싱 · SHA-256 해시 앵커 · OKF v0.2 (`D2.1`~`D2.6`)",
        "subtitle": "비정형 정책 가이드를 의미 단위 청크(`DOC_CHUNK_001`~`005`)로 분할하고 불변 암호학적 해시(`anchor_<12hex>`)와 JSON-LD 온톨로지로 컴파일",
        "banner_img": "stage2_parse_integrate_flow_ko.png",
        "cards": [
            {
                "tag": "STEP 1 · DETERMINISTIC CHUNKING",
                "title": "결정론적 청크 분할 & 해시 앵커",
                "accent": "#1A73E8",
                "bullets": [
                    "마크다운 내 <!-- DOC_CHUNK_NNN: 제목 --> 마커(또는 ## 헤더) 단위로 분할",
                    "문단 본문의 SHA-256 해시 앞 12자리로 anchor_<12hex> 불변 식별자 생성",
                    "본문이 1글자라도 변경되면 해시가 즉시 변경되어 정책 개정 감지에 활용"
                ]
            },
            {
                "tag": "STEP 2 · OKF v0.2 JSON-LD",
                "title": "표준 온톨로지 명세 (ontology.jsonld)",
                "accent": "#0F9D58",
                "bullets": [
                    "도메인 루트 노드와 각 문서 청크 노드를 W3C JSON-LD 표준 형식으로 직렬화",
                    "data/output/doc_chunks.jsonl 및 data/output/ontology.jsonld 로컬 생성",
                    "BigQuery tb_doc_chunks 적재 및 GCS ontology/ 경로 자동 동기화"
                ]
            },
            {
                "tag": "STEP 3 · STAGE 2 MCP",
                "title": "mcp_stage2_wiki_and_semantic",
                "accent": "#4F46E5",
                "bullets": [
                    "compile_3layer_wiki: GCS 버킷(raw/, parsed/, ontology/) 동기화 객체 확인",
                    "extract_hash_anchors: tb_doc_chunks의 content_sha256 해시 무결성 검증",
                    "bind_semantic_bridges: tb_domain_rules ↔ tb_doc_chunks 조인 검증"
                ]
            }
        ],
        "table": {
            "headers": ["청크 ID", "원천 문서 (`data/input/01_guides/`)", "섹션 제목", "연결된 비즈니스 규칙 ID", "핵심 정책 내용"],
            "rows": [
                ["DOC_CHUNK_001", "sample_policy_guide.md", "공시지원금 및 추가지원금 한도", "RULE_SUBSIDY_CAP", "추가지원금은 공시지원금의 최대 15% 이내, 총지원금은 출고가 이하"],
                ["DOC_CHUNK_002", "sample_policy_guide.md", "180일 의무유지 및 일할 위약금 산식", "RULE_SIX_PLAN_180D", "개통 후 180일 미만 저가 요금제 변경 시 지원금 차액 일할 반환"],
                ["DOC_CHUNK_003", "sample_policy_guide.md", "고가 요금제 유지 기준선 (85,000원)", "RULE_SIX_PLAN_180D", "월정액 85,000원 이상 요금제 간 변경 시 차액 위약금 미부과"],
                ["DOC_CHUNK_004", "sample_welfare_exemption_guide.md", "시니어 및 복지 대상 위약금 면제", "RULE_WELFARE_EXEMPT", "SENIOR_EXEMPT 등 복지 감면 코드 보유 계약은 위약금 100% 면제(0원)"],
                ["DOC_CHUNK_005", "sample_welfare_exemption_guide.md", "공시지원금 vs 25% 선택약정 24개월 TCO", "RULE_TCO_24M", "24개월 총비용(단말 할부원금 + 24개월 통신요금) 비교 후 유리한 옵션 안내"]
            ]
        },
        "takeaway": "불변 해시 앵커링: 모든 비즈니스 규칙(tb_domain_rules)은 반드시 원문 청크 ID(source_chunk_id)와 SHA-256 해시를 외래키처럼 참조해야 한다.",
        "speaker_notes": (
            "[강사 가이드 — Slide 07: Stage 2 비정형 파싱 및 해시 앵커]\n"
            "• 일반적인 RAG는 글자 수(예: 500자)로 문서를 자르기 때문에 조항 문장이 중간에 끊기고, 앞 문단이 수정되면 뒤쪽 모든 청크 ID가 밀립니다.\n"
            "• 본 방법론에서는 의미 단위 마커(`DOC_CHUNK_001`~`005`)와 본문 SHA-256 해시(`content_sha256`)를 결합하여, 문서가 개정되더라도 어느 조항이 바뀌었는지 즉시 감지하고 규칙과의 연결을 유지합니다."
        )
    },
    {
        "slide_no": 8,
        "badge": "MODULE 02 · STAGE 2 DEEP DIVE",
        "accent": "#0F9D58",
        "title": "Stage 2 심화: Karpathy 3-Layer LLM-Wiki & 시맨틱 브릿지 (`Gate 2`)",
        "subtitle": "문서와 테이블에서 자동 컴파일되는 3계층 마크다운 위키(`L1 요약 · L2 엔티티 · L3 개념/규칙`)와 비정형-정형 브릿지 매핑",
        "banner_img": None,
        "cards": [
            {
                "tag": "LAYER 1 · SUMMARY",
                "title": "L1 Summary (summary.md)",
                "accent": "#1A73E8",
                "bullets": [
                    "전체 코퍼스 요약: 인입된 가이드 문서 수(2), 청크 수(5), 마스터 테이블 수(4)",
                    "각 청크의 SHA-256 앵커 목록과 도메인 핵심 범위 한눈에 파악",
                    "에이전트 및 신규 엔지니어의 도메인 진입점(Index) 역할 수행"
                ]
            },
            {
                "tag": "LAYER 2 · ENTITIES",
                "title": "L2 Entities (entities.md)",
                "accent": "#0F9D58",
                "bullets": [
                    "마스터 CSV 4종(단말 4, 요금제 6, 지원금 6, 고객약정 6)의 정규 엔티티 카탈로그",
                    "한국어 위키(data/llm_wiki/ko/)와 영어 위키(data/llm_wiki/en/) 대칭 제공",
                    "카탈로그 슬롯 검증 및 엔티티 속성(출고가, 월정액, 의무유지일) 참조 표준"
                ]
            },
            {
                "tag": "LAYER 3 · CONCEPTS & RULES",
                "title": "L3 Concepts & Rules (concepts/rules.md)",
                "accent": "#4F46E5",
                "bullets": [
                    "concepts.md: 4대 핵심 관계(USES_DEVICE, SUBSCRIBES_PLAN, HAS_SUBSIDY_POLICY, APPLIES_TO_PLAN)",
                    "rules.md: 4대 비즈니스 규칙 산식 및 근거 청크(DOC_CHUNK_001~005) 매핑",
                    "edge_rule_applies_to_plan(12행)으로 비정형 규칙과 정형 요금제 물리 연결"
                ]
            }
        ],
        "table": {
            "headers": ["Stage 2 산출물 ID", "산출물 명칭", "생성 경로 / BigQuery 테이블", "Gate 2 검증 기준"],
            "rows": [
                ["D2.1", "OKF v0.2 도메인 온톨로지 명세서", "data/output/ontology.jsonld", "JSON-LD 그래프 노드 및 컨텍스트 유효성"],
                ["D2.2", "Karpathy 3-Layer LLM-Wiki (KO / EN)", "data/llm_wiki/{ko,en}/{summary,entities,concepts,rules}.md", "4종 마크다운 파일 생성 및 한/영 무결성"],
                ["D2.3", "GCS 온톨로지 프로토타입 매니페스트", "data/llm_wiki/gcs_prototype_manifest.json · gs://.../ontology/", "status == LIVE_GCP_SYNCED · 10개 테이블 확인"],
                ["D2.4 ~ D2.6", "해시 청크 · 도메인 규칙 · 시맨틱 브릿지", "tb_doc_chunks(5) · tb_domain_rules(4) · edge_rule_applies_to_plan(12)", "모든 규칙의 source_chunk_id가 tb_doc_chunks에 존재"]
            ]
        },
        "takeaway": "시맨틱 브릿지(edge_rule_applies_to_plan): 비정형 문서에서 추출한 규칙(rule_id)을 정형 요금제(plan_id)와 연결하는 핵심 고리다.",
        "speaker_notes": (
            "[강사 가이드 — Slide 08: 3-Layer LLM-Wiki와 시맨틱 브릿지]\n"
            "• Andrej Karpathy가 제안한 LLM-Wiki 패턴을 엔터프라이즈 온톨로지에 맞게 3계층(L1 Summary, L2 Entities, L3 Concepts & Rules)으로 구조화했습니다.\n"
            "• 특히 `data/llm_wiki/ko/`와 `data/llm_wiki/en/`으로 한/영 위키가 분리되어 있어 글로벌 팀에서도 한글 노출 없이 100% 영문 온톨로지 위키를 활용할 수 있습니다.\n"
            "• 스튜디오 `Stage 2. Wiki & Semantic Graph` 탭에서 좌측 위키 뷰어와 우측 시맨틱 그래프(11 노드, 13 엣지)를 함께 시연하십시오."
        )
    },
    {
        "slide_no": 9,
        "badge": "MODULE 03 · STAGE 3 OVERVIEW",
        "accent": "#4F46E5",
        "title": "Stage 3. Zero-ETL 2-Layer Property Graph 구축 (`D3.1`~`D3.4`)",
        "subtitle": "BigQuery DW 테이블을 별도 그래프 DB로 복제하지 않고 SQL:2023 `CREATE OR REPLACE PROPERTY GRAPH`로 즉시 그래프 가상화",
        "banner_img": "stage3_property_graph_flow_ko.png",
        "cards": [
            {
                "tag": "ANTI-REDUNDANCY",
                "title": "2-Layer 안티 리던던시 원칙",
                "accent": "#1A73E8",
                "bullets": [
                    "정형 DW 마스터 테이블을 비정형 텍스트로 다시 풀어 쓰거나 외부 DB로 복제 금지",
                    "원장 테이블은 그대로 두고 VERTEX TABLES(6종)와 EDGE TABLES(4종)로 그래프 뷰 선언",
                    "중복 엔티티 노드 0건(duplicate_keys_total == 0)으로 데이터 정합성 100% 유지"
                ]
            },
            {
                "tag": "6 VERTEX TABLES",
                "title": "6대 물리 노드 레이블",
                "accent": "#0F9D58",
                "bullets": [
                    "CustomerContractNode (tb_customer_contract, PK: contract_id)",
                    "DeviceNode (tb_device_master) · PlanNode (tb_plan_master) · SubsidyNode (tb_subsidy_policy)",
                    "DomainRuleNode (tb_domain_rules) · DocChunkNode (tb_doc_chunks)"
                ]
            },
            {
                "tag": "4 EDGE TABLES",
                "title": "4대 물리 엣지 레이블",
                "accent": "#4F46E5",
                "bullets": [
                    "USES_DEVICE (edge_contract_device: 약정 → 단말)",
                    "SUBSCRIBES_PLAN (edge_contract_plan: 약정 → 요금제)",
                    "HAS_SUBSIDY_POLICY (단말 → 요금제) · APPLIES_TO_PLAN (규칙 → 요금제)"
                ]
            }
        ],
        "table": {
            "headers": ["구분", "그래프 레이블 (`STARTER_ONTOLOGY_GRAPH`)", "기반 BigQuery 테이블", "식별 키 (`KEY` / `SOURCE` → `DESTINATION`)", "행 수"],
            "rows": [
                ["Vertex (Node)", "CustomerContractNode / DeviceNode / PlanNode", "tb_customer_contract / tb_device_master / tb_plan_master", "contract_id / device_id / plan_id", "6 / 4 / 6행"],
                ["Vertex (Node)", "SubsidyNode / DomainRuleNode / DocChunkNode", "tb_subsidy_policy / tb_domain_rules / tb_doc_chunks", "policy_id / rule_id / chunk_id", "6 / 4 / 5행"],
                ["Edge", "USES_DEVICE / SUBSCRIBES_PLAN", "edge_contract_device / edge_contract_plan", "contract_id → device_id / contract_id → plan_id", "6 / 6행"],
                ["Edge", "HAS_SUBSIDY_POLICY / APPLIES_TO_PLAN", "edge_subsidy_binding / edge_rule_applies_to_plan", "device_id → plan_id / rule_id → plan_id (source_chunk_id 포함)", "7 / 12행"]
            ]
        },
        "takeaway": "Zero-ETL Property Graph: 원장 데이터가 업데이트되는 즉시 그래프 탐색 결과에도 실시간 반영되며, 별도 ETL 파이프라인 비용이 0이다.",
        "speaker_notes": (
            "[강사 가이드 — Slide 09: Stage 3 BigQuery Property Graph 설계]\n"
            "• 기존 그래프 온톨로지 프로젝트의 가장 큰 병목은 BigQuery 데이터를 외부 그래프 DB로 빼내는 ETL 파이프라인과 보안 심의였습니다.\n"
            "• BigQuery SQL:2023 Property Graph는 `CREATE OR REPLACE PROPERTY GRAPH seanjung-poc.starter_ontology_dw.STARTER_ONTOLOGY_GRAPH` 구문 하나로 기존 테이블 10개를 즉시 그래프 노드·엣지로 승격시킵니다.\n"
            "• `pipeline/graph_builder.py`를 실행하면 BigQuery에 그래프가 즉시 배포되고 `data/output/graph_topology.json`에 검증 결과가 기록됩니다."
        )
    },
    {
        "slide_no": 10,
        "badge": "MODULE 03 · STAGE 3 DEEP DIVE",
        "accent": "#4F46E5",
        "title": "Stage 3 심화: BigQuery vs Spanner 듀얼 DDL 및 다중 홉 ISO GQL 패턴 (`Gate 3`)",
        "subtitle": "분석용 BigQuery Property Graph와 실시간 운영용 Cloud Spanner Graph DDL 비교 및 에이전트 GQL 탐색 쿼리 구조",
        "banner_img": None,
        "cards": [
            {
                "tag": "BIGQUERY PROPERTY GRAPH",
                "title": "대규모 분석 & 하이브리드 추론 (OLAP)",
                "accent": "#1A73E8",
                "bullets": [
                    "파일: data/output/create_property_graph.sql (실시간 배포·쿼리 실행)",
                    "DW 원장 테이블 위에 서버리스로 선언, 대규모 분석 및 에이전트 추론에 최적",
                    "GRAPH_TABLE(... MATCH ...) 구문과 일반 SQL JOIN(tb_doc_chunks)을 단일 쿼리로 결합"
                ]
            },
            {
                "tag": "CLOUD SPANNER GRAPH",
                "title": "초저지연 실시간 운영 인터락 (OLTP)",
                "accent": "#0F9D58",
                "bullets": [
                    "파일: data/output/create_spanner_graph.sql (DDL 자동 합성 지원)",
                    "INTERLEAVE IN PARENT 물리적 계층 클러스터링으로 <10ms 다중 홉 탐색 지향",
                    "실시간 이상거래 탐지(FDS), 설비 인터락, 개통 전 실시간 규제 차단 시스템에 적합"
                ]
            },
            {
                "tag": "MULTI-HOP ISO GQL",
                "title": "3-Hop 그래프 탐색 + 원문 청크 조인",
                "accent": "#4F46E5",
                "bullets": [
                    "고객 약정(c) → 단말(d) 및 요금제(p) ← 적용 규칙(r)을 단일 MATCH 패턴으로 순회",
                    "엣지 속성 ap.source_chunk_id로 tb_doc_chunks를 조인해 원문 문단과 해시 인출",
                    "Gate 3: DDL 실행 SUCCESS, GQL 경로 > 0, 중복 키 0건 확인"
                ]
            }
        ],
        "table": {
            "headers": ["탐색 시나리오", "ISO GQL `GRAPH_TABLE` 패턴 요약", "홉 수", "결합되는 비정형 근거", "호출 MCP 도구"],
            "rows": [
                ["고객 맞춤형 규칙·근거 탐색 (customer_id 지정)", "MATCH (c:CustomerContractNode)-[:USES_DEVICE]->(d:DeviceNode), (c)-[:SUBSCRIBES_PLAN]->(p:PlanNode)<-[ap:APPLIES_TO_PLAN]-(r:DomainRuleNode)", "3-Hop", "JOIN tb_doc_chunks ch ON ch.chunk_id = ap.source_chunk_id", "mcp_query_graph_and_wiki"],
                ["단말·요금제 정책 탐색 (customer_id 미지정)", "MATCH (d:DeviceNode)-[hs:HAS_SUBSIDY_POLICY]->(p:PlanNode)<-[ap:APPLIES_TO_PLAN]-(r:DomainRuleNode)", "2-Hop", "JOIN tb_doc_chunks ch ON ch.chunk_id = ap.source_chunk_id", "mcp_query_graph_and_wiki"],
                ["Stage 3 토폴로지 무결성 검증", "MATCH (d:DeviceNode)-[hs:HAS_SUBSIDY_POLICY]->(p:PlanNode)<-[ap:APPLIES_TO_PLAN]-(r:DomainRuleNode) RETURN COUNT(*)", "2-Hop", "그래프 엣지 바인딩 경로 수(gql_paths) 전수 카운트", "mcp_stage3_property_graph"]
            ]
        },
        "takeaway": "단일 쿼리 융합: GRAPH_TABLE 내부에서 정형-비정형 다중 홉 경로를 찾고, 외부 SQL JOIN으로 원문 청크와 SHA-256 해시를 한 번에 가져온다.",
        "speaker_notes": (
            "[강사 가이드 — Slide 10: 듀얼 그래프 DDL과 ISO GQL 쿼리]\n"
            "• 스튜디오 `Stage 3. Property Graph` 탭 상단에서 `BigQuery Property Graph`와 `Cloud Spanner Graph` 버튼을 전환하면 두 엔진의 SQL:2023 DDL 문법 차이를 즉시 비교할 수 있습니다.\n"
            "• 또한 노트북 `stage3_property_graph_bigquery_spanner_{ko,en}.ipynb`에서는 실제 실행된 GQL 문장과 바인딩 변수(`customer_id`, `plan_name`)를 투명하게 출력하여 엔지니어가 쿼리 플랜을 이해할 수 있도록 구성되어 있습니다."
        )
    },
    {
        "slide_no": 11,
        "badge": "MODULE 04 · STAGE 4 OVERVIEW",
        "accent": "#D97706",
        "title": "Stage 4. 8종 도메인 MCP 도구 아키텍처 (`5 Stage + 3 Runtime`) (`D4.1`~`D4.4`)",
        "subtitle": "LLM이 복잡한 다중 테이블 JOIN이나 GQL 문법을 직접 생성하지 않도록 도메인 시맨틱 단위로 추상화된 8종의 MCP 서버 구축",
        "banner_img": "stage4_agent_mcp_flow_ko.png",
        "cards": [
            {
                "tag": "COGNITIVE ISOLATION",
                "title": "에이전트 인지 부하 격리 원칙",
                "accent": "#1A73E8",
                "bullets": [
                    "LLM에게 물리 테이블 컬럼명이나 복잡한 GQL 문법을 직접 작성하게 하지 않음",
                    "비즈니스 의미 단위로 캡슐화된 MCP 도구(고객 프로필, 위약금·TCO 계산, 그래프 탐색) 제공",
                    "모든 도구는 파라미터화된 쿼리와 실행된 BigQuery Job ID를 투명하게 반환"
                ]
            },
            {
                "tag": "5 STAGE MCP TOOLS",
                "title": "파이프라인 거버넌스 MCP (5종)",
                "accent": "#0F9D58",
                "bullets": [
                    "mcp_stage1_asset_discovery · mcp_stage2_wiki_and_semantic",
                    "mcp_stage3_property_graph · mcp_stage4_agent_orchestration",
                    "mcp_stage5_lineage_and_eval (각 Stage 게이트 검증 및 스튜디오 연동)"
                ]
            },
            {
                "tag": "3 RUNTIME MCP TOOLS",
                "title": "실시간 에이전트 추론 MCP (3종)",
                "accent": "#D97706",
                "bullets": [
                    "mcp_lookup_customer_profile: 계약·단말·요금제·지원금·할부원금 + RULE_SUBSIDY_CAP",
                    "mcp_calculate_penalty_rule: 면제 판정·180일 일할 위약금·24개월 TCO 비교",
                    "mcp_query_graph_and_wiki: STARTER_ONTOLOGY_GRAPH 다중 홉 GQL + 원문 청크 인출"
                ]
            }
        ],
        "table": {
            "headers": ["구분", "MCP 도구명 (`src/agent/mcp_server.py`)", "내부 실행 Step", "핵심 반환 데이터 및 상태 코드"],
            "rows": [
                ["Stage 1~3", "mcp_stage1 / stage2 / stage3", "profile_tables, tag_pii / bind_semantic_bridges / verify_gql_templates", "테이블 행 수, 비식별 위반 건수(0), 해시 조인 청크, GQL 경로 수"],
                ["Stage 4~5", "mcp_stage4 / stage5", "verify_grounding_anchors / build_4tier_lineage, run_golden_cq_suite", "활성 규칙 4종, 엔드투엔드 리니지(18행), Golden CQ 및 Boundary 리포트"],
                ["Runtime 1", "mcp_lookup_customer_profile", "lookup_contract → lookup_device_price → lookup_subsidy_policy", "고객 약정, 총지원금, 할부원금, DOC_CHUNK_001 (SUCCESS / MATCH_NOT_FOUND)"],
                ["Runtime 2", "mcp_calculate_penalty_rule", "check_exemptions → compute_180d_prorated_clawback → compare_24m_tco", "면제 여부, 일할 위약금, 24개월 TCO 비교표 (SUCCESS / INSUFFICIENT_PARAMETERS)"],
                ["Runtime 3", "mcp_query_graph_and_wiki", "traverse_property_graph → fetch_okf_hash_anchor → verify_dw_schema", "GQL 매칭 경로, 규칙 수식, 원문 청크 텍스트·해시 (SUCCESS / MATCH_NOT_FOUND)"]
            ]
        },
        "takeaway": "도메인 MCP 추상화: 에이전트는 검증된 파라미터(customer_id, plan_name, elapsed_days 등)만 넘기고, 실제 연산과 그래프 탐색은 MCP 서버가 책임진다.",
        "speaker_notes": (
            "[강사 가이드 — Slide 11: Stage 4 8종 도메인 MCP 아키텍처]\n"
            "• `src/agent/mcp_server.py`의 `DomainMcpServer`는 파이프라인 각 단계를 점검하는 Stage MCP 5종과 고객 질의에 실시간 응답하는 Runtime MCP 3종으로 구성됩니다.\n"
            "• 특히 다국어 환경(`lang='en'` 또는 `STARTER_LANG='en'`)에서는 `src/agent/i18n_en.py`를 통해 모든 MCP 요약 메시지와 반환 레코드가 100% 영문으로 자동 변환됩니다."
        )
    },
    {
        "slide_no": 12,
        "badge": "MODULE 04 · STAGE 4 DEEP DIVE",
        "accent": "#D97706",
        "title": "Stage 4 심화: 결정론적 위약금·TCO 판정 트리와 2-Pass Gemini 추론 (`Gate 4`)",
        "subtitle": "6단계 위약금 의사결정 트리와 Vertex AI Gemini(`gemini-3.8-flash`) 2-Pass 추론 루프를 통한 가드레일 상태 분리",
        "banner_img": None,
        "cards": [
            {
                "tag": "PASS 1 · DECOMPOSE & VALIDATE",
                "title": "Pass 1: 카탈로그 제약 슬롯 추출",
                "accent": "#1A73E8",
                "bullets": [
                    "BigQuery에서 실시간 단말·요금제·고객 카탈로그 로드 (5분 캐시)",
                    "Gemini 1차 호출로 질문에서 파라미터 JSON과 호출할 MCP 하위 목표 분해",
                    "카탈로그에 없는 단말/요금제 이름은 즉시 제거하고 질문에 명시된 숫자만 수용"
                ]
            },
            {
                "tag": "DETERMINISTIC ENGINE",
                "title": "6단계 위약금 판정 & 24개월 TCO",
                "accent": "#D97706",
                "bullets": [
                    "1) 복지 면제(SENIOR_EXEMPT) → 0원  2) 무약정/선택약정 → 0원",
                    "3) 변경요금제·경과일 누락 → INSUFFICIENT_PARAMETERS 즉시 반환",
                    "4) 경과일 ≥ 180일 → 0원  5) 변경 월정액 ≥ 85,000원 → 0원  6) 일할 위약금 산출"
                ]
            },
            {
                "tag": "PASS 2 · GROUNDED SYNTHESIS",
                "title": "Pass 2: 가드레일 상태 기반 답변 합성",
                "accent": "#0F9D58",
                "bullets": [
                    "도구 반환 상태에 따라 GROUNDED / MATCH_NOT_FOUND / INSUFFICIENT_PARAMETERS / BQ_ERROR 확정",
                    "Gemini 2차 호출은 오직 MCP 도구 결과 JSON만을 근거로 답변 작성",
                    "결론 → 근거 데이터 → 적용 규칙·청크 해시 → BigQuery Job ID 순서 강제"
                ]
            }
        ],
        "table": {
            "headers": ["에이전트 응답 상태 (`response_status`)", "발생 조건", "에이전트 답변 동작 원칙 (Gate 4 기준)", "대표 검증 케이스"],
            "rows": [
                ["GROUNDED", "모든 필수 파라미터가 확인되고 MCP 조회 결과가 존재할 때", "정확한 계산 수치 + 규칙 ID + DOC_CHUNK_00X 해시 + BQ Job ID 인용", "CQ-01 ~ CQ-05, BQ-01, BQ-06, BQ-10"],
                ["INSUFFICIENT_PARAMETERS", "위약금 질의에서 고객 ID·단말 또는 변경 요금제·경과일이 빠졌을 때", "임의 수치를 추측하지 않고 누락된 필수 파라미터 항목을 명시하여 재질의 안내", "BQ-02, BQ-03, BQ-07, BQ-08"],
                ["MATCH_NOT_FOUND", "질문한 단말·요금제·지원금 조합이 카탈로그/원장에 존재하지 않을 때", "첫 문장에 조회 결과 0건(MATCH_NOT_FOUND)임을 밝히고 실제 카탈로그 목록 제시", "BQ-04, BQ-05, BQ-09"],
                ["BQ_QUERY_ERROR", "BigQuery 쿼리 실행 오류 또는 권한/네트워크 장애 발생 시", "0건으로 위장하지 않고 쿼리 오류 상태를 투명하게 보고", "장애 주입/권한 점검 시"]
            ]
        },
        "takeaway": "Gate 4 핵심: 정보가 부족할 때 '모른다(INSUFFICIENT_PARAMETERS)'고 답하고, 조건에 맞는 행이 없을 때 '0건(MATCH_NOT_FOUND)'이라고 답하는 것이 진짜 엔터프라이즈 에이전트다.",
        "speaker_notes": (
            "[강사 가이드 — Slide 12: 6단계 위약금 판정 트리와 2-Pass 추론 루프]\n"
            "• `src/agent/reasoning_engine.py`의 `AiFdeAgentEngine.execute_cycle()` 동작 원리를 설명합니다.\n"
            "• 왜 1-Pass가 아니라 2-Pass인가? 1차 호출에서는 카탈로그에 존재하는 엔티티만 골라내어 도구를 실행하고, 도구 실행이 끝난 뒤 `response_status`를 코드 레벨에서 확정한 다음 2차 호출로 요약문을 생성하기 때문입니다.\n"
            "• 덕분에 필수 조건이 빠진 질문에서 에이전트가 임의로 '90일이라고 가정하면...'이라며 환각을 일으키는 현상을 100% 차단합니다."
        )
    },
    {
        "slide_no": 13,
        "badge": "MODULE 05 · STAGE 5 OVERVIEW",
        "accent": "#0F9D58",
        "title": "Stage 5. 4계층 엔드투엔드 데이터 리니지 & 영향도 추적 (`D5.1`~`D5.2`)",
        "subtitle": "원천 파일(`Tier 0`) → 해시 청크(`Tier 1`) → 도메인 규칙·브릿지(`Tier 2`) → 약정·그래프(`Tier 3`) → 에이전트 답변(`Tier 4`)의 전주기 감사 추적",
        "banner_img": "stage5_lineage_eval_flow_ko.png",
        "cards": [
            {
                "tag": "TIER 0 & TIER 1",
                "title": "원천 문서·CSV → 불변 해시 청크",
                "accent": "#1A73E8",
                "bullets": [
                    "Tier 0: sample_policy_guide.md, sample_welfare_exemption_guide.md, CSV 6종",
                    "Tier 1: tb_doc_chunks (DOC_CHUNK_001~005, SHA-256 content_sha256)",
                    "문서 조항 개정 시 변경된 해시 앵커를 통해 하위 영향 범위 즉시 식별"
                ]
            },
            {
                "tag": "TIER 2 & TIER 3",
                "title": "비즈니스 규칙 → Property Graph",
                "accent": "#0F9D58",
                "bullets": [
                    "Tier 2: tb_domain_rules (4종) + edge_rule_applies_to_plan (12개 요금제 브릿지)",
                    "Tier 3: tb_customer_contract (6명) + STARTER_ONTOLOGY_GRAPH (6노드·4엣지)",
                    "mcp_stage5_lineage_and_eval이 18개 엔드투엔드 리니지 조인 경로 실시간 산출"
                ]
            },
            {
                "tag": "TIER 4 · AUDIT TRAIL",
                "title": "Golden CQ 답변 & Job ID 감사",
                "accent": "#4F46E5",
                "bullets": [
                    "Tier 4: 에이전트 최종 답변에 인용된 규칙 ID, 청크 ID, BigQuery Job ID 결합",
                    "금융·통신·공공 감사 시 '이 답변의 숫자가 어느 테이블·어느 규정 문단에서 왔는가' 즉시 입증",
                    "고객 식별자는 CUST_DEMO_001~006 비식별 코드로 거버넌스 준수(D5.2)"
                ]
            }
        ],
        "table": {
            "headers": ["리니지 계층 (Tier)", "구성 자산 / 테이블", "연결 키 (Join / Bridge Key)", "변경 시 하위 영향도 (Impact Analysis)"],
            "rows": [
                ["Tier 0 → Tier 1", "가이드 마크다운 (2종) → tb_doc_chunks (5행)", "chunk_id (DOC_CHUNK_001~005) + content_sha256", "문단 텍스트 수정 시 해시 변경 감지 → 연결된 규칙 재검토 알림"],
                ["Tier 1 → Tier 2", "tb_doc_chunks → tb_domain_rules · edge_rule_applies_to_plan", "source_chunk_id → rule_id → target_plan_id", "특정 조항(예: DOC_CHUNK_002) 개정 시 영향받는 요금제(5G 시그니처 등) 자동 추출"],
                ["Tier 2 → Tier 3", "edge_rule_applies_to_plan → STARTER_ONTOLOGY_GRAPH", "plan_id · device_id · contract_id (18개 리니지 행)", "해당 요금제에 가입된 고객 계약(CUST_DEMO_001~006) 및 지원금 정책 매핑"],
                ["Tier 3 → Tier 4", "STARTER_ONTOLOGY_GRAPH → 8 MCP → Gemini 2-Pass 응답", "rule_id + source_chunk_id + bq_job_id", "Golden CQ(CQ-01~05) 정답 기대값 및 에이전트 응답 검증 리포트 갱신"]
            ]
        },
        "takeaway": "엔드투엔드 리니지: 정책 문서의 한 문단이 바뀌었을 때 어느 규칙, 어느 요금제, 어느 고객 약정, 어느 CQ 답변이 영향받는지 쿼리 한 번으로 추적한다.",
        "speaker_notes": (
            "[강사 가이드 — Slide 13: Stage 5 4계층 데이터 리니지]\n"
            "• 엔터프라이즈 거버넌스에서 가장 중요한 질문은 '정책 문서가 바뀌었을 때 어떤 요금제와 어떤 에이전트 답변이 영향을 받는가?'입니다.\n"
            "• `mcp_stage5_lineage_and_eval`의 `build_4tier_lineage`는 고객 약정부터 단말·요금제·지원금·규칙·문서 청크까지 이어지는 18개 리니지 레코드를 실시간 조인하여 스튜디오 `Stage 5. Lineage & Eval` 탭에 시각화합니다."
        )
    },
    {
        "slide_no": 14,
        "badge": "MODULE 05 · STAGE 5 DEEP DIVE",
        "accent": "#0F9D58",
        "title": "Stage 5 심화: 이중 벤치마크(`Golden CQ 5` + `Boundary 10×5`) & 배포 게이트 (`Gate 5`)",
        "subtitle": "`pipeline/validator.py`를 통한 결정론적 SQL 대조 검증과 50회 반복 경계값 일관성 실측 및 Terraform Cloud Run 배포",
        "banner_img": None,
        "cards": [
            {
                "tag": "BENCHMARK 1 · GOLDEN CQ",
                "title": "Golden CQ 5건 정합성 검증 (D5.3)",
                "accent": "#1A73E8",
                "bullets": [
                    "파일: data/output/cq_benchmark_report.json (5/5 통과, 100.0%)",
                    "BigQuery verification_sql 실행 결과와 expected_math 일치 여부(SQL_MATCH) 확인",
                    "실제 에이전트 응답이 정답 수치와 필수 청크(DOC_CHUNK_00X)를 인용했는지 검증"
                ]
            },
            {
                "tag": "BENCHMARK 2 · BOUNDARY 10×5",
                "title": "경계값 10건 × 5회 반복 실측 (D5.4)",
                "accent": "#0F9D58",
                "bullets": [
                    "파일: data/output/boundary_benchmark_results.json (총 50회 라이브 호출)",
                    "정상(GROUNDED 3건), 파라미터 누락(INSUFFICIENT 4건), 미존재(MATCH_NOT_FOUND 3건)",
                    "통과율(avg_success_rate), 반복 일관성(avg_consistency_rate), 의도 안정성 측정"
                ]
            },
            {
                "tag": "GATE 5 & TERRAFORM IaC",
                "title": "프로덕션 릴리스 게이트 (D5.5)",
                "accent": "#4F46E5",
                "bullets": [
                    "Dockerfile + terraform/ (main.tf, bigquery.tf, storage.tf, iam.tf, cloud_run.tf)",
                    "시크릿(AIza...) 0건, 고객 실명 0건, 로컬 절대경로 0건 보안 감사",
                    "Gate 5 전 항목 통과 시 Cloud Run(agentic-ontology-starter) 배포 승인"
                ]
            }
        ],
        "table": {
            "headers": ["평가 구분", "대상 데이터셋 (`data/input/04_cq/`)", "실행 횟수", "핵심 측정 지표 (KPI)", "산출물 리포트 (`data/output/`)"],
            "rows": [
                ["Golden CQ 정합성 평가", "golden_competency_questions.json (CQ-01 ~ CQ-05)", "5회 (문항당 1회 + SQL 검증)", "accuracy_rate (100.0%), verification_status (SQL_MATCH)", "cq_benchmark_report.json"],
                ["경계값 — 정상 복합 (GROUNDED)", "boundary_cases.json (BQ-01, BQ-06, BQ-10)", "3문항 × 5회 = 15회", "정답 수치·청크 인용 정확도 및 5회 반복 시 일관성", "boundary_benchmark_results.json"],
                ["경계값 — 정보 부족 (INSUFFICIENT)", "boundary_cases.json (BQ-02, BQ-03, BQ-07, BQ-08)", "4문항 × 5회 = 20회", "임의 추측 차단율 및 INSUFFICIENT_PARAMETERS 판정 일관성", "boundary_benchmark_results.json"],
                ["경계값 — 미존재 조합 (MATCH_NOT_FOUND)", "boundary_cases.json (BQ-04, BQ-05, BQ-09)", "3문항 × 5회 = 15회", "카탈로그 외 단말/요금제 거부 및 0건 안내 정확도", "boundary_benchmark_results.json"]
            ]
        },
        "takeaway": "릴리스 게이트(Gate 5): 정답이 있는 질문(Golden CQ)뿐 아니라 '답하면 안 되는 질문(Boundary Cases 50회)'까지 통과해야 프로덕션에 배포할 수 있다.",
        "speaker_notes": (
            "[강사 가이드 — Slide 14: 이중 벤치마크와 Gate 5 배포 승인]\n"
            "• 많은 PoC가 해피 패스(Happy Path) 질문 3~4개만 성공하고 프로덕션에 나갔다가, 모호한 사용자 질문에서 사고를 냅니다.\n"
            "• 따라서 Stage 5에서는 `boundary_cases.json` 10문항을 각 5회씩 총 50회 라이브 호출하여, 에이전트가 흔들림 없이 동일한 가드레일 상태(`INSUFFICIENT_PARAMETERS`, `MATCH_NOT_FOUND`, `GROUNDED`)를 유지하는지 검증합니다."
        )
    },
    {
        "slide_no": 15,
        "badge": "MODULE 06 · HANDS-ON LABS",
        "accent": "#1A73E8",
        "title": "실습 환경 가이드: 6-Tab 거버넌스 스튜디오 & 12종 한/영 주피터 노트북",
        "subtitle": "클라우드 라이브 스튜디오(`Cloud Run`)와 로컬/Workbench 주피터 노트북(`notebooks/ko/`, `notebooks/en/`)을 활용한 양방향 실습",
        "banner_img": None,
        "cards": [
            {
                "tag": "WEB STUDIO (6-TAB)",
                "title": "인터랙티브 거버넌스 스튜디오",
                "accent": "#1A73E8",
                "bullets": [
                    "0. Overview: 8단계 아키텍처 다이어그램, 트랙 배지, Stage 1~5 원클릭 실행",
                    "Stage 1~3 탭: 자산 인벤토리, 3-Layer 위키 뷰어, 시맨틱/Property Graph 시각화",
                    "Stage 4~5 탭: 8종 MCP 개별 실행기, 2-Pass 에이전트 콘솔, 엔드투엔드 리니지 & 평가표"
                ]
            },
            {
                "tag": "KOREAN NOTEBOOKS (6종)",
                "title": "국문 실습 노트북 (notebooks/ko/)",
                "accent": "#0F9D58",
                "bullets": [
                    "stage0_overview_walkthrough_ko.ipynb ~ stage5_lineage_and_evaluation_ko.ipynb",
                    "각 노트북 상단 아키텍처 배너 내장, 단계별 BigQuery SQL/GQL 및 차트 시각화",
                    "GQL 실행 문장 및 바인딩 파라미터 투명 출력으로 쿼리 디버깅 학습 지원"
                ]
            },
            {
                "tag": "ENGLISH NOTEBOOKS (6종)",
                "title": "영문 실습 노트북 (notebooks/en/)",
                "accent": "#4F46E5",
                "bullets": [
                    "stage0_overview_walkthrough_en.ipynb ~ stage5_lineage_and_evaluation_en.ipynb",
                    "STARTER_LANG='en' 및 i18n_en.py 연동으로 데이터·위키·MCP·에이전트 답변 100% 영문화",
                    "글로벌 엔지니어 및 해외 고객사 워크숍에서 한글 노출(0건) 없이 즉시 교육 가능"
                ]
            }
        ],
        "table": {
            "headers": ["노트북 단계", "국문 노트북 (`notebooks/ko/`)", "영문 노트북 (`notebooks/en/`)", "핵심 실습 내용 및 출력 산출물"],
            "rows": [
                ["Stage 0", "stage0_overview_walkthrough_ko.ipynb", "stage0_overview_walkthrough_en.ipynb", "8단계 파이프라인 요약, 10개 테이블 스냅샷, GQL·MCP·에이전트 원스톱 투어"],
                ["Stage 1", "stage1_asset_and_cq_ko.ipynb", "stage1_asset_and_cq_en.ipynb", "마스터 테이블 프로파일링, 정책 용어 히트맵, Golden CQ 5건 SQL 검증"],
                ["Stage 2", "stage2_wiki_and_semantic_graph_ko.ipynb", "stage2_wiki_and_semantic_graph_en.ipynb", "SHA-256 해시 청킹, 3-Layer 위키(ko/en) 탐색, 시맨틱 브릿지 그래프 시각화"],
                ["Stage 3", "stage3_property_graph_bigquery_spanner_ko.ipynb", "stage3_property_graph_bigquery_spanner_en.ipynb", "BigQuery Property Graph vs Spanner DDL 비교, 2-Hop/3-Hop ISO GQL 실행"],
                ["Stage 4", "stage4_agent_and_mcp_execution_ko.ipynb", "stage4_agent_and_mcp_execution_en.ipynb", "8종 MCP 도구 호출, 180일 위약금·24개월 TCO 차트, 2-Pass Gemini 에이전트 실행"],
                ["Stage 5", "stage5_lineage_and_evaluation_ko.ipynb", "stage5_lineage_and_evaluation_en.ipynb", "엔드투엔드 리니지 그래프, Golden CQ 5건 및 Boundary 50회 벤치마크 시각화"]
            ]
        },
        "takeaway": "한/영 대칭 구조: methodology/{ko,en}/ 문서, data/llm_wiki/{ko,en}/ 위키, notebooks/{ko,en}/ 노트북, slides/{ko,en}/ 슬라이드가 모두 1:1 대칭으로 제공된다.",
        "speaker_notes": (
            "[강사 가이드 — Slide 15: 6-Tab 스튜디오 및 12종 노트북 실습 안내]\n"
            "• 수강생들은 브라우저에서 라이브 스튜디오(`https://agentic-ontology-starter-lwrlf7yogq-du.a.run.app`)를 열어 코드 없이 클릭만으로 5단계를 체험하거나, 주피터 노트북으로 코드 레벨 실습을 진행할 수 있습니다.\n"
            "• 노트북 재생성 및 검증 명령어: `.venv/bin/python notebooks/generate_notebooks.py --execute` 및 `.venv/bin/python notebooks/validate_and_pack_notebooks.py`."
        )
    },
    {
        "slide_no": 16,
        "badge": "MODULE 07 · RAPID PROTOTYPING PLAYBOOK",
        "accent": "#4F46E5",
        "title": "도메인 적용 플레이북: 4대 시나리오(`A`~`D`) & `5-File Swap` 아키텍처",
        "subtitle": "코어 엔진(웹 UI · 2-Pass 추론 루프 · GCP 클라이언트 · Terraform)은 건드리지 않고 5개 도메인 슬롯만 교체하여 반나절 안에 신규 도메인 구축",
        "banner_img": None,
        "cards": [
            {
                "tag": "IMMUTABLE CORE (수정 금지)",
                "title": "절대 재작성하지 않는 코어 엔진 4종",
                "accent": "#DC2626",
                "bullets": [
                    "src/gcp_client.py: BigQuery SQL/GQL 실행, GCS 동기화, Vertex AI 호출",
                    "src/agent/reasoning_engine.py: 2-Pass 추론 루프 및 4대 가드레일 상태 판정",
                    "src/web/studio_server.py & terraform/*.tf: 6-Tab 스튜디오 UI 및 IaC 인프라"
                ]
            },
            {
                "tag": "5-FILE SWAP (교체 슬롯)",
                "title": "도메인 교체 시 수정하는 5개 파일",
                "accent": "#1A73E8",
                "bullets": [
                    "① config/starter_config.json (active_track: lite | standard | full)",
                    "② data/input/* (01_guides/*.md, 03_tables/*.csv, 04_cq/*.json)",
                    "③ pipeline/ingest.py  ④ pipeline/graph_builder.py  ⑤ mcp_server.py + portal_profile.json"
                ]
            },
            {
                "tag": "4 SCENARIOS (A ~ D)",
                "title": "보유 데이터 상황별 4대 시나리오",
                "accent": "#0F9D58",
                "bullets": [
                    "Scenario A (Lite): 문서·수식만 보유 → Stage 1·2·4 (수정 파일 4개)",
                    "Scenario B (Standard): 정형 DW + 문서 → BigQuery Graph 통합 (수정 파일 5개)",
                    "Scenario C (Spanner): 실시간 인터락 DDL 추가 / Scenario D (Full): 50회 평가·배포"
                ]
            }
        ],
        "table": {
            "headers": ["Swap 순서", "대상 파일 경로", "도메인 교체 시 수정 내용", "검증 명령어"],
            "rows": [
                ["Swap ①", "config/starter_config.json", "active_track ('lite' | 'standard' | 'full'), graph_engine, graph_name 설정", "cat config/starter_config.json"],
                ["Swap ②", "data/input/{01_guides,03_tables,04_cq}/", "도메인 정책 마크다운(.md), 마스터/트랜잭션 CSV, Golden CQ·Boundary JSON 교체", "ls -la data/input/*"],
                ["Swap ③", "pipeline/ingest.py", "테이블 적재 목록, DOMAIN_RULES 메타데이터, 3-Layer 위키 요약 템플릿 수정", "python3 pipeline/ingest.py"],
                ["Swap ④", "pipeline/graph_builder.py", "CREATE OR REPLACE PROPERTY GRAPH의 VERTEX TABLES / EDGE TABLES 매핑 수정", "python3 pipeline/graph_builder.py"],
                ["Swap ⑤", "src/agent/mcp_server.py · config/portal_profile.json", "Runtime MCP 3종의 도메인 SQL/GQL 산식 및 스튜디오 화면 프로필·샘플 질문 갱신", "python3 pipeline/validator.py"]
            ]
        },
        "takeaway": "5-File Swap 원칙: 새로운 고객사 PoC를 할 때마다 웹 서버나 에이전트 프레임워크를 새로 짜지 말고, 데이터·규칙·그래프 매핑 5곳만 교체하라.",
        "speaker_notes": (
            "[강사 가이드 — Slide 16: PROTOTYPING_PLAYBOOK.md와 5-File Swap]\n"
            "• 실무 엔지니어가 다른 프로젝트에 이 스타터팩을 가져갔을 때 가장 흔히 겪는 실수는 전체 코드를 처음부터 다시 짜는 것입니다.\n"
            "• `PROTOTYPING_PLAYBOOK.md`에 정의된 `5-File Swap` 패턴을 따르면 코어 엔진(`studio_server.py`, `reasoning_engine.py`, `gcp_client.py`)은 100% 그대로 재사용하면서 30분~반나절 만에 금융·제조·유통 도메인 프로토타입으로 전환할 수 있습니다."
        )
    },
    {
        "slide_no": 17,
        "badge": "MODULE 07 · AI CODING AGENT BOOTSTRAP",
        "accent": "#1A73E8",
        "title": "AI 코딩 에이전트(`Antigravity` · `Cursor` · `Claude Code`) 3-Step 명령 가이드",
        "subtitle": "코딩 에이전트가 임의로 Mock SQLite를 만들거나 UI를 깨뜨리지 않도록 제어하는 가드레일 번들과 단계별 표준 프롬프트",
        "banner_img": None,
        "cards": [
            {
                "tag": "GUARDRAIL BUNDLE",
                "title": "에이전트 자동 인식 규칙 파일 6종",
                "accent": "#1A73E8",
                "bullets": [
                    "01_prod.md: 6대 불변 아키텍처 원칙 및 5-File Swap 마스터 명세",
                    "GEMINI.md (Antigravity/Jetski) · CLAUDE.md (Claude Code) · .cursorrules (Cursor)",
                    "AGENTS.md (공통 지침) · DESIGN.md (Apple/Google 라이트 테마 디자인 시스템)"
                ]
            },
            {
                "tag": "3-STEP WORKFLOW",
                "title": "3단계 분할 명령 실행 전략",
                "accent": "#0F9D58",
                "bullets": [
                    "Step 1 (환경 셋팅): GCP 인증 확인, .venv 패키지 설치, Terraform 리소스 생성",
                    "Step 2 (데이터 인입): 01_guides/ · 03_tables/ 교체 후 ingest.py로 10개 테이블·위키 적재",
                    "Step 3 (온톨로지 & 스튜디오): graph_builder.py 실행, MCP 연결, validator.py 검증"
                ]
            },
            {
                "tag": "ANTI-DRIFT RULES",
                "title": "코딩 에이전트 3대 금지 가드레일",
                "accent": "#DC2626",
                "bullets": [
                    "1) 로컬 SQLite나 인메모리 Mock 데이터로 실제 BigQuery 연동 대체 절대 금지",
                    "2) 6-Tab 스튜디오(studio_server.py) 레이아웃 및 다크 테마 임의 변경 금지",
                    "3) 하드코딩된 Gemini API 키(AIza...) 소스 코드 내 삽입 절대 금지 (ADC 사용)"
                ]
            }
        ],
        "table": {
            "headers": ["실행 단계", "목표 작업", "Antigravity (Jetski) / Cursor / Claude Code 표준 명령 프롬프트 요약", "완료 확인 기준"],
            "rows": [
                ["Step 1", "환경 셋팅 & GCP 프로비저닝", "@01_prod.md @GEMINI.md 읽고 GCP_PROJECT_ID, BQ_DATASET_ID, GCS_WIKI_BUCKET 기준으로 .venv 설치 및 Terraform으로 BigQuery 10개 테이블·GCS 버킷 생성해줘.", "gcloud auth 확인 · BQ 데이터셋/테이블 10개 생성"],
                ["Step 2", "도메인 데이터 인입 & 위키 구축", "@01_prod.md @PROTOTYPING_PLAYBOOK.md 기준으로 내 가이드 문서와 CSV를 data/input/에 반영하고 pipeline/ingest.py 실행해 BigQuery 적재 및 3-Layer 위키 생성해줘.", "gcs_prototype_manifest.json (LIVE_GCP_SYNCED)"],
                ["Step 3", "Property Graph & 에이전트 구동", "pipeline/graph_builder.py로 STARTER_ONTOLOGY_GRAPH 생성하고, mcp_server.py 연결 후 validator.py 실행 및 8080 스튜디오 서버 띄워줘.", "GQL 경로 > 0 · Golden CQ 100% · HTTP 200 OK"],
                ["원샷 전환", "시나리오 A~D 도메인 교체", "@01_prod.md @GEMINI.md @PROTOTYPING_PLAYBOOK.md 읽고 [Scenario B: Track 2 Standard] 5-File Swap 절차에 따라 [대상 도메인] 프로토타입으로 전환해줘.", "5개 슬롯만 수정 · 코어 UI/추론 엔진 무결성 유지"]
            ]
        },
        "takeaway": "프롬프트 엔지니어링 팁: 코딩 에이전트에게 명령할 때는 반드시 첫 줄에 `@01_prod.md @GEMINI.md @PROTOTYPING_PLAYBOOK.md`를 멘션해 아키텍처 가드레일을 먼저 로드시켜라.",
        "speaker_notes": (
            "[강사 가이드 — Slide 17: AI 코딩 에이전트 부트스트랩 가이드]\n"
            "• 오늘날 개발자들은 Antigravity(Jetski), Cursor, Claude Code 같은 코딩 에이전트로 스타터팩을 커스터마이징합니다.\n"
            "• 레포지토리 루트에 포함된 `01_prod.md`, `GEMINI.md`, `CLAUDE.md`, `.cursorrules`, `DESIGN.md`는 코딩 에이전트가 프로젝트 구조를 오해해 엉뚱한 앱을 만들지 않도록 잡아주는 안전장치입니다.\n"
            "• GitHub 메인 `README.md` §1에 수록된 Step 1 → Step 2 → Step 3 복사-붙여넣기 프롬프트를 그대로 사용하면 누구나 일관된 결과를 얻을 수 있습니다."
        )
    },
    {
        "slide_no": 18,
        "badge": "MODULE 08 · INDUSTRY ARCHETYPES & WRAP-UP",
        "accent": "#0F9D58",
        "title": "4대 산업군 8종 엔터프라이즈 레퍼런스 템플릿(`industry_cases/`) & 과정 요약",
        "subtitle": "제조 · 금융 · 리테일/커머스 · 통신 4개 세그먼트별 비식별 아키타입(노드·엣지·DDL·CSV·규정 문서·CQ) 즉시 활용 가이드",
        "banner_img": None,
        "cards": [
            {
                "tag": "MANUFACTURING & FINANCE",
                "title": "스마트 제조 (2종) & 금융/핀테크 (2종)",
                "accent": "#1A73E8",
                "bullets": [
                    "제조 A: 스마트 제철소 연속공정 설비 진동(4.5mm/s) 인터락 SOP & 예비 베어링 재고",
                    "제조 B: 글로벌 완성차 SDV 제어기 펌웨어 호환성 & ISO 26262 ASIL-D 납기 리스크",
                    "금융 A: 인터넷전문은행 비대면 주담대 스트레스 DSR 40% & 생애최초 LTV 80% 심사",
                    "금융 B: 원앱 핀테크 마이데이터 다중 채무 대환 중개 & 여전법 가맹점 우대수수료"
                ]
            },
            {
                "tag": "RETAIL & TELECOM",
                "title": "리테일/물류 (2종) & 통신/미디어 (2종)",
                "accent": "#0F9D58",
                "bullets": [
                    "리테일 A: 전국 가맹 편의점 신선식품(FF) 폐기 지원금 40% 정산 & 퀵커머스 재고",
                    "리테일 B: 옴니채널 헬스앤뷰티 오늘드림 3시간 배송 SLA 배상 & 판촉비 50% 분담 한도",
                    "통신 A: 모바일 5G 구독 결합 & 180일 의무유지 공시지원금 차액 일할 위약금·복지 면제",
                    "통신 B: 유무선 인터넷+TV 총액 결합 해지 방어 & B2B 전용회선 월 99.9% SLA 3배 배상"
                ]
            },
            {
                "tag": "COURSE TAKEAWAYS",
                "title": "교육 핵심 요약 & 라이선스 안내",
                "accent": "#4F46E5",
                "bullets": [
                    "1) CQ 우선 스코핑(Stage 1) → 2) SHA-256 청크 & 3-Layer 위키(Stage 2)",
                    "3) Zero-ETL Property Graph(Stage 3) → 4) 8 MCP & 2-Pass 에이전트(Stage 4) → 5) 50회 게이트(Stage 5)",
                    "비영리 듀얼 라이선스(CC BY-NC-ND 4.0 / PolyForm Noncommercial) · 문의: seanjung@google.com"
                ]
            }
        ],
        "table": {
            "headers": ["산업군 폴더 (`industry_cases/`)", "아키타입 케이스 (비식별 표준)", "핵심 Property Graph 노드 × 엣지", "결정론적 MCP 계산 산식 예시"],
            "rows": [
                ["01_manufacturing/", "스마트 제철소 A사 · 글로벌 완성차 B사", "Equipment · Sensor · BearingInventory · SafetySOP (APPLIES_INTERLOCK)", "진동 변위 ≥ 4.5mm/s 시 즉시 감속 인터락 및 대체 라인 전환 비용 산출"],
                ["02_finance/", "인터넷전문은행 A사 · 원앱 핀테크 B사", "LoanApplicant · CreditLoan · MortgageRule · FSSRegulation (GOVERNED_BY)", "연간 원리금 상환액 / 연소득 ≤ DSR 40% 한도 및 스트레스 금리 가산 계산"],
                ["03_retail_commerce/", "전국 가맹 유통 A사 · 옴니채널 리테일 B사", "FranchiseStore · FreshSKU ·PromoContract · FairTradeRule (SUBSIDIZES)", "신선식품 폐기 원가 × 40% 본사 지원금 및 대규모유통업법 판촉비 50% 상한 검증"],
                ["04_telecommunications/", "모바일 구독 통신사 A사 · 유무선 결합 통신사 B사", "CustomerContract · Device · Plan · Subsidy · DomainRule (APPLIES_TO_PLAN)", "180일 일할 위약금, 시니어 면제(0원), 24개월 공시 vs 선택약정 TCO, B2B SLA 배상"]
            ]
        },
        "takeaway": "실전 출발점: 바닥부터 스키마를 설계하지 말고 industry_cases/의 4대 산업군 8종 템플릿 중 가장 유사한 도메인을 골라 5-File Swap으로 즉시 시작하라.",
        "speaker_notes": (
            "[강사 가이드 — Slide 18: 4대 산업군 8종 레퍼런스 케이스 및 마무리]\n"
            "• `industry_cases/` 폴더에는 제조, 금융, 유통, 통신 4개 산업군별로 즉시 실행 가능한 SQL DDL(`schema_*.sql`), 샘플 CSV 데이터, 비정형 규정 마크다운, 그리고 8개 아키타입 설계서가 완비되어 있습니다.\n"
            "• 스튜디오 상단의 `Industry Cases (8)` 모달에서도 각 산업군 케이스를 즉시 열람할 수 있습니다.\n"
            "• 이상으로 5-Stage 에이전틱 온톨로지 엔지니어링 방법론 교육을 마칩니다. 상업적 활용이나 엔터프라이즈 도입 논의는 seanjung@google.com으로 연락주시기 바랍니다."
        )
    }
]
