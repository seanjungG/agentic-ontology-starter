# 5-Stage 에이전틱 온톨로지 구축 방법론 (`METHODOLOGY_KO.md`)

> 라이브 스튜디오 [`Agentic Ontology Starter (6-Tab)`](https://agentic-ontology-starter-924723860007.asia-northeast3.run.app/) · 기준 스튜디오 [`LG U+ (12-Tab)`](https://agentic-ontology-studio-lguplus-mcp-924723860007.asia-northeast3.run.app/) · [`LG생활건강 (12-Tab)`](https://agentic-ontology-studio-hnh-mcp-924723860007.asia-northeast3.run.app/) · [English](../en/METHODOLOGY_EN.md) · [Stage별 가이드 인덱스](../README.md) · [노트북 디렉터리](../../notebooks/README.md) · [라이선스 (`LICENSE`)](../../LICENSE)

## 1. 목적과 핵심 원칙 (Resource-Connected Starter Architecture v2.2)

본 레포지토리(`agentic-ontology-starter` v2.2)는 엔터프라이즈 기준점 스튜디오인 **LG U+ 공시지원금 & 결합 온톨로지 스튜디오(12-Tab)** 및 **LG생활건강 화장품 표시광고 실증 스튜디오(12-Tab)**의 **5-Stage × 11-Step 표준 프로세스(`P1/P2/P3` × `W1/W2/W3` × `Gate G2-W`)**를 흔들리지 않는 단일 기준으로 유지하면서, 무거운 내부 MCP 빌더 파이프라인은 플랫폼 계층으로 **완전 추상화(Excluded & Abstracted)**하고 **즉시 사용 가능한(Ready-to-Use) Google Cloud 온톨로지 리소스**에 직결하는 **Resource-Connected Starter 아키텍처**를 제공한다.

1. **코드 노출 경계 (Code Exposure Boundary)**:
   - **추상화/제외 영역**: 내부 온톨로지 빌더 MCP 도구 및 무거운 문서 파서·컴파일러는 스타터 런타임 카탈로그(`get_tool_catalog()`)에서 제외되며, 컴파일 결과물은 BigQuery(`seanjung-poc.starter_ontology_dw`), GCS(`gs://seanjung-poc-starter-ontology/ontology/`), Spanner(`starter-spanner`)에 **Ready-to-Use 리소스**로 준비되어 있다.
   - **노출된 핵심 커스터마이징 코드 (4 Core Files)**:
     1. [`src/resource_connector.py`](../../src/resource_connector.py) (`OntologyResourceConnector` — Stage 1~5 연결 리소스 점검)
     2. [`src/gcp_client.py`](../../src/gcp_client.py) (`EnterpriseOntologyBenchmarker` — BigQuery SQL/GQL, Spanner GQL, GCS, Vertex AI `gemini-3.8-flash`)
     3. [`src/agent/mcp_server.py`](../../src/agent/mcp_server.py) (`DomainMcpServer` — 커스터마이징 대상 **도메인 비즈니스 도구 3종**)
     4. [`src/agent/reasoning_engine.py`](../../src/agent/reasoning_engine.py) (`AgenticReasoningEngine` — 하위 목표 분해, 도구 체이닝, `Gate G2-W` 감사)
2. **런타임 BQG 1순위 단일 진실 원천 (BQG 1st Priority SSOT)**:
   - 운영·서빙 런타임에서 에이전트·워크플로우·도메인 비즈니스 도구가 참조하는 1순위 데이터 원천은 **BigQuery Property Graph (`STARTER_ONTOLOGY_GRAPH`)**와 그에 동기화된 3-Layer OKF 위키(`summary/entities/concepts/rules.md`), 비즈니스 규칙(`business_rules.json`), 비즈니스 워크플로(`business_workflows.json`, `W1~W3`)이다.
3. **결정론적 산식 실행 및 `Gate G2-W` 런타임 감사**:
   - 위약금·지원금·24개월 TCO 계산은 LLM 암산이 아니라 도메인 비즈니스 도구 내부 SQL 코드로 결정론적으로 실행하며, `Gate G2-W`가 예외 규칙(`SENIOR_EXEMPT`) 선행 분기 및 `DOC_CHUNK_*` SHA-256 해시 앵커 인용 여부를 검증한다.

## 2. Stage 0~5 통합 매핑: 데모 화면 ↔ 프로세스 ↔ 연결 리소스 ↔ 노출 코드 ↔ 노트북 (1:1)

| Stage | 스타터 포털 탭 | 표준 프로세스 (`Step` / `P·W·Gate`) | 연결된 Ready-to-Use GCP 리소스 | 노출된 핵심 코드 / 도구 | 상세 가이드 / 한·영 노트북 |
| :---: | :--- | :--- | :--- | :--- | :--- |
| **Stage 0** | [`0. Overview`](https://agentic-ontology-starter-924723860007.asia-northeast3.run.app/?tab=overview) | 아키텍처 개요 · 기준점 허브 · 3-Track 선택 | `config/starter_config.json` · `portal_profile.json` | `src/resource_connector.py` | [가이드](./00_overview_and_4tracks_ko.md) · [KO](../../notebooks/ko/stage0_overview_walkthrough_ko.ipynb) · [EN](../../notebooks/en/stage0_overview_walkthrough_en.ipynb) |
| **Stage 1** | [`Stage 1. Asset`](https://agentic-ontology-starter-924723860007.asia-northeast3.run.app/?tab=stage1) | 자산 확인 · 리소스 연결 · Golden CQ (`P1`·`P2`) | `seanjung-poc.starter_ontology_dw` (10 Tables) | `stage1_resource_check` | [가이드](./01_stage1_asset_and_cq_ko.md) · [KO](../../notebooks/ko/stage1_asset_and_cq_ko.ipynb) · [EN](../../notebooks/en/stage1_asset_and_cq_en.ipynb) |
| **Stage 2** | [`Stage 2. Wiki & Semantic`](https://agentic-ontology-starter-924723860007.asia-northeast3.run.app/?tab=stage2) | 3-Layer OKF 위키 · 비즈니스 규칙(4종) · 워크플로(`W1~W3`) | `gs://seanjung-poc-starter-ontology/ontology/` + `tb_domain_rules` | `stage2_resource_check` | [가이드](./02_stage2_wiki_and_semantic_graph_ko.md) · [KO](../../notebooks/ko/stage2_wiki_and_semantic_graph_ko.ipynb) · [EN](../../notebooks/en/stage2_wiki_and_semantic_graph_en.ipynb) |
| **Stage 3** | [`Stage 3. Property Graph`](https://agentic-ontology-starter-924723860007.asia-northeast3.run.app/?tab=stage3) | Zero-ETL BigQuery Graph & Spanner Graph (`P1`·`P3`) | `STARTER_ONTOLOGY_GRAPH` (BQ SQL:2023 & Spanner GQL) | `stage3_resource_check` · `src/gcp_client.py` | [가이드](./03_stage3_property_graph_ko.md) · [KO](../../notebooks/ko/stage3_property_graph_bigquery_spanner_ko.ipynb) · [EN](../../notebooks/en/stage3_property_graph_bigquery_spanner_en.ipynb) |
| **Stage 4** | [`Stage 4. Agent & Tools`](https://agentic-ontology-starter-924723860007.asia-northeast3.run.app/?tab=stage4) | 도메인 비즈니스 도구 3종 & AI FDE (`P3` · `Gate G2-W`) | Vertex AI `gemini-3.8-flash` + 도메인 도구 3종 | `src/agent/mcp_server.py` · `src/agent/reasoning_engine.py` | [가이드](./04_stage4_agent_and_mcp_ko.md) · [KO](../../notebooks/ko/stage4_agent_and_mcp_execution_ko.ipynb) · [EN](../../notebooks/en/stage4_agent_and_mcp_execution_en.ipynb) |
| **Stage 5** | [`Stage 5. Lineage & Eval`](https://agentic-ontology-starter-924723860007.asia-northeast3.run.app/?tab=stage5) | 6-Layer 데이터 리니지 DAG & Golden/WF/Boundary 평가 | `tb_golden_cq_results` · `config/lineage_spec.json` | `stage5_resource_check` · `src/lineage_service.py` | [가이드](./05_stage5_lineage_and_eval_ko.md) · [KO](../../notebooks/ko/stage5_lineage_and_evaluation_ko.ipynb) · [EN](../../notebooks/en/stage5_lineage_and_evaluation_en.ipynb) |

## 3. 커스터마이징 대상 도메인 비즈니스 도구 3종 (`src/agent/mcp_server.py`)

| 도구 이름 | 카테고리 | 주요 기능 및 연결 리소스 |
| :--- | :--- | :--- |
| **`mcp_lookup_customer_profile`** | `runtime_domain` | 고객 약정(`tb_customer_contract`), 단말 출고가(`tb_device_master`), 공시지원금/추가지원금(`tb_subsidy_policy`) 원장 조회 |
| **`mcp_calculate_penalty_rule`** | `runtime_domain` | 시니어 복지 면제(`RULE_WELFARE_EXEMPT`), 180일 일할 위약금(`RULE_SIX_PLAN_180D`), 24개월 공시 vs 선택약정 TCO(`RULE_TCO_24M`) 결정론적 SQL 산출 (`W1~W3` 워크플로 바인딩) |
| **`mcp_query_graph_and_wiki`** | `runtime_domain` | `STARTER_ONTOLOGY_GRAPH` 멀티홉 `GRAPH_TABLE` 탐색 및 `tb_doc_chunks` SHA-256 원문 해시 앵커 조인 |
