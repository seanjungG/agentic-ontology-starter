# 5-Stage 에이전틱 온톨로지 구축 방법론 (`METHODOLOGY_KO.md`)

> 라이브 스튜디오 [`Agentic Ontology Studio`](https://agentic-ontology-starter-lwrlf7yogq-du.a.run.app) · [English](./METHODOLOGY_EN.md) · [Stage별 가이드 인덱스](./README.md) · [노트북 디렉터리](../notebooks/README.md) · [라이선스 (`LICENSE`)](../LICENSE)
>
> **[방법론 저작권 및 상업적 이용 금지 고지 (CC BY-NC-ND 4.0 / Non-Commercial Only)]**: 본 5-Stage 에이전틱 온톨로지 엔지니어링 방법론(8단계 엔지니어링 흐름, 산출물 D1.1~D5.5, 3-Layer OKF 위키, 듀얼 Property Graph 설계, 8종 MCP 및 2-Pass 에이전트 오케스트레이션)은 **CC BY-NC-ND 4.0** 라이선스로 보호됩니다. 개인 학습 및 비상업적 연구 외에 **유상 컨설팅, SI 구축, 유상 PoC 딜리버리, 고객사 제안서·산출물 활용을 엄격히 금지**하며, 상업적/엔터프라이즈 활용이 필요한 경우 **[seanjung@google.com](mailto:seanjung@google.com)**으로 사전 논의하시기 바랍니다.

## 1. 목적과 핵심 원칙 (8단계 엔지니어링 흐름)

이 문서는 정형 데이터(BigQuery DW 테이블)와 비정형 정책 문서(업무 가이드·약관)를 **1. 준비(Prepare) → 2. 분석(Analyze) → 3. 파싱(Parse) → 4. 통합(Integrate) → 5. 구축(Build Graph) → 6. 에이전트 구축(Build Agent) → 7. 답변(Answer & GQL) → 8. 검증(Verify & Gate)**의 8단계 엔지니어링 흐름을 통해 **3-Layer 위키(OKF v0.2)**와 **BigQuery Property Graph(ISO GQL)**로 결합하고, **MCP 도구(8종)**와 **Vertex AI Gemini 에이전트(`gemini-3.8-flash`)**로 근거 기반 답변을 제공하는 5-Stage 절차를 정의한다.

1. **원문 해시 앵커 보존**: 비정형 문서는 문단별 SHA-256 해시(`anchor_<12hex>`)와 함께 `tb_doc_chunks`에 적재해 에이전트 답변에서 원문 문단까지 역추적한다.
2. **Zero-ETL 그래프 투영**: 정형 원장(`tb_device_master`, `tb_plan_master`, `tb_subsidy_policy`, `tb_customer_contract`)과 비정형 규칙·청크(`tb_domain_rules`, `tb_doc_chunks`)를 복제 없이 `CREATE OR REPLACE PROPERTY GRAPH`로 묶는다.
3. **결정론적 산식 실행**: 위약금 일할 계산이나 24개월 총비용(TCO) 비교는 LLM 암산에 맡기지 않고 MCP 도구 내부 SQL/Python 산식으로 계산한다.
4. **가드레일 상태 분리**: 근거 확인(`GROUNDED`), 조건 미일치(`MATCH_NOT_FOUND`), 필수 정보 부족(`INSUFFICIENT_PARAMETERS`), 쿼리 오류(`BQ_QUERY_ERROR`)를 명확히 구분한다.

## 2. 8단계 엔지니어링 흐름 & 5-Stage 라이프사이클 · 스튜디오 · MCP · 노트북 매핑

| 8단계 엔지니어링 흐름 | Stage | 단계명 | 스튜디오 탭 | Stage MCP 도구 (`src/agent/mcp_server.py`) | 산출물 ID | 상세 가이드 / 한·영 노트북 |
| :--- | :---: | :--- | :--- | :--- | :---: | :--- |
| **0. 전체 흐름 투어** | **공통** | 아키텍처 개요 및 파이프라인 투어 | [`0. Overview`](https://agentic-ontology-starter-lwrlf7yogq-du.a.run.app/?tab=overview) | Stage 1~5 일괄/개별 실행 | - | [KO 노트북](../notebooks/ko/stage0_overview_walkthrough_ko.ipynb) · [EN 노트북](../notebooks/en/stage0_overview_walkthrough_en.ipynb) |
| **1. 준비 · 2. 분석** | **Stage 1** | 자산 탐색 · 스코핑 · CQ 정의 | [`Stage 1. Asset`](https://agentic-ontology-starter-lwrlf7yogq-du.a.run.app/?tab=stage1) | `mcp_stage1_asset_discovery` | `D1.1`~`D1.4` | [가이드](./01_stage1_asset_and_cq_ko.md) · [KO](../notebooks/ko/stage1_asset_and_cq_ko.ipynb) · [EN](../notebooks/en/stage1_asset_and_cq_en.ipynb) |
| **3. 파싱 · 4. 통합** | **Stage 2** | 3-Layer 위키 · 시맨틱 그래프 | [`Stage 2. Wiki & Semantic Graph`](https://agentic-ontology-starter-lwrlf7yogq-du.a.run.app/?tab=stage2) | `mcp_stage2_wiki_and_semantic` | `D2.1`~`D2.6` | [가이드](./02_stage2_wiki_and_semantic_graph_ko.md) · [KO](../notebooks/ko/stage2_wiki_and_semantic_graph_ko.ipynb) · [EN](../notebooks/en/stage2_wiki_and_semantic_graph_en.ipynb) |
| **5. 구축** | **Stage 3** | Property Graph · ISO GQL | [`Stage 3. Property Graph`](https://agentic-ontology-starter-lwrlf7yogq-du.a.run.app/?tab=stage3) | `mcp_stage3_property_graph` | `D3.1`~`D3.4` | [가이드](./03_stage3_property_graph_ko.md) · [KO](../notebooks/ko/stage3_property_graph_bigquery_spanner_ko.ipynb) · [EN](../notebooks/en/stage3_property_graph_bigquery_spanner_en.ipynb) |
| **6. 에이전트 · 7. 답변** | **Stage 4** | MCP 스위트 · 에이전트 오케스트레이션 | [`Stage 4. Agent & MCP`](https://agentic-ontology-starter-lwrlf7yogq-du.a.run.app/?tab=stage4) | `mcp_stage4_agent_orchestration` + 런타임 3종 | `D4.1`~`D4.4` | [가이드](./04_stage4_agent_and_mcp_ko.md) · [KO](../notebooks/ko/stage4_agent_and_mcp_execution_ko.ipynb) · [EN](../notebooks/en/stage4_agent_and_mcp_execution_en.ipynb) |
| **8. 검증** | **Stage 5** | 4계층 리니지 · 평가 · 배포 게이트 | [`Stage 5. Lineage & Eval`](https://agentic-ontology-starter-lwrlf7yogq-du.a.run.app/?tab=stage5) | `mcp_stage5_lineage_and_eval` | `D5.1`~`D5.5` | [가이드](./05_stage5_lineage_and_eval_ko.md) · [KO](../notebooks/ko/stage5_lineage_and_evaluation_ko.ipynb) · [EN](../notebooks/en/stage5_lineage_and_evaluation_en.ipynb) |

## 3. 도입 트랙 (3-Track Adoption Model)

조직의 데이터 준비도에 따라 `config/starter_config.json`에서 3가지 트랙을 선택할 수 있다.

| 트랙 | 활성 Stage | 물리 그래프 엔진 | 적용 환경 |
| :--- | :---: | :---: | :--- |
| **Track 1 · Lite** | `Stage 1 → 2 → 4` | `none` (위키·규칙 조회) | 비정형 정책 가이드 문서 위주 환경에서 빠르게 위키·에이전트를 검증할 때 |
| **Track 2 · Standard** | `Stage 1 → 2 → 3 → 4` | `bigquery` (또는 Spanner DDL) | 정형 DW 원장과 비정형 위키를 Property Graph로 통합해 다중 홉 GQL 추론을 수행할 때 |
| **Track 3 · Full** | `Stage 1 → 2 → 3 → 4 → 5` | `bigquery` | 4계층 리니지, Golden CQ 5건, 경계값 벤치마크(10건×5회) 및 Terraform Cloud Run 배포까지 전주기를 운영할 때 |

> 참고: Cloud Spanner Graph는 DDL 생성(`data/output/create_spanner_graph.sql`)을 지원하며, 라이브 쿼리 실행은 BigQuery Property Graph(`STARTER_ONTOLOGY_GRAPH`)를 사용한다.

## 4. 런타임 리소스 및 MCP 8종 명세

### 4.1 BigQuery `starter_ontology_dw` (10개 테이블 + `STARTER_ONTOLOGY_GRAPH`)

- **노드 테이블 6종**: `tb_device_master`(4), `tb_plan_master`(6), `tb_subsidy_policy`(6), `tb_customer_contract`(6), `tb_domain_rules`(4), `tb_doc_chunks`(5)
- **엣지 테이블 4종**: `edge_contract_device`(6), `edge_contract_plan`(6), `edge_subsidy_binding`(7), `edge_rule_applies_to_plan`(12)
- **GCS 위키 버킷**: `gs://seanjung-poc-starter-ontology` (`raw/`, `parsed/`, `ontology/` 3-Layer 마크다운 및 매니페스트)

### 4.2 MCP 도구 8종 (`src/agent/mcp_server.py`)

| 구분 | 도구 이름 | 주요 Step / 기능 |
| :--- | :--- | :--- |
| Stage MCP (5종) | `mcp_stage1_asset_discovery` | `profile_tables`, `scan_guides`, `prune_noise`, `tag_pii_governance` |
| Stage MCP | `mcp_stage2_wiki_and_semantic` | `compile_3layer_wiki`, `extract_hash_anchors`, `bind_semantic_bridges` |
| Stage MCP | `mcp_stage3_property_graph` | `promote_dw_nodes`, `synthesize_graph_ddl`, `verify_gql_templates` |
| Stage MCP | `mcp_stage4_agent_orchestration` | `decompose_subgoals`, `dispatch_domain_mcps`, `verify_grounding_anchors` |
| Stage MCP | `mcp_stage5_lineage_and_eval` | `build_4tier_lineage`, `run_golden_cq_suite`, `diagnose_boundary_failures` |
| Runtime MCP (3종) | `mcp_lookup_customer_profile` | 계약·단말·요금제·지원금 조인, 할부원금 계산, `RULE_SUBSIDY_CAP` 청크 결합 |
| Runtime MCP | `mcp_calculate_penalty_rule` | 복지 면제 확인, 180일 일할 위약금 정산, 공시지원금 vs 25% 선택약정 24개월 TCO 비교 |
| Runtime MCP | `mcp_query_graph_and_wiki` | `STARTER_ONTOLOGY_GRAPH` GQL 다중 홉 탐색 및 `tb_doc_chunks` 원문 결합 |

## 5. Stage별 산출물 요약 (D1.1 ~ D5.5)

- **Stage 1 (`D1.1`~`D1.4`)**: 테이블 스키마·행수 프로파일, 가이드 문서 인벤토리, 표준 용어사전(`business_glossary.json`), Golden CQ 5건(`golden_competency_questions.json`) 및 경계값 10건(`boundary_cases.json`).
- **Stage 2 (`D2.1`~`D2.6`)**: 3-Layer 위키(`data/llm_wiki/`), SHA-256 해시 앵커(`tb_doc_chunks`), JSON-LD 시맨틱 그래프(`data/output/ontology.jsonld`).
- **Stage 3 (`D3.1`~`D3.4`)**: BigQuery Property Graph DDL(`create_property_graph.sql`), Spanner Graph DDL(`create_spanner_graph.sql`), GQL 탐색 패턴 검증.
- **Stage 4 (`D4.1`~`D4.4`)**: MCP 8종 서버(`mcp_server.py`), 2-패스 Gemini 에이전트(`reasoning_engine.py`), 근거·가드레일 검증.
- **Stage 5 (`D5.1`~`D5.5`)**: 4계층 리니지, Golden CQ 리포트(`cq_benchmark_report.json`), 경계값 10×5 리포트(`boundary_benchmark_results.json`), Terraform·Cloud Run 배포 패키지.
