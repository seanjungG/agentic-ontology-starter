# 5-Stage 에이전틱 온톨로지 구축 방법론 (`METHODOLOGY_KO.md`)

> 라이브 스튜디오 [`Agentic Ontology Studio`](https://agentic-ontology-starter-lwrlf7yogq-du.a.run.app) · [English](../en/METHODOLOGY_EN.md) · [Stage별 가이드 인덱스](../README.md) · [노트북 디렉터리](../../notebooks/README.md) · [라이선스 (`LICENSE`)](../../LICENSE)

## 1. 목적과 핵심 원칙 (교육·테스트·부트스트랩용 유연한 온톨로지 엔진)

본 레포지토리(`agentic-ontology-starter`)는 특정 고객사 비즈니스나 정형 데이터가 고정되어 있지 않은 상태에서, **어떤 산업군의 문서나 정형 데이터가 들어올지 예측할 수 없는 상황에서도 유연하게 온톨로지와 에이전트를 구축·검증할 수 있도록 설계된 교육용·테스트용·부트스트랩용 심플 레포지토리**다.

정형 데이터(BigQuery DW 테이블)와 비정형 정책 문서(업무 가이드·약관·매뉴얼)를 **1. 준비(Prepare) → 2. 분석(Analyze) → 3. 파싱(Parse) → 4. 통합(Integrate) → 5. 구축(Build Graph) → 6. 에이전트 구축(Build Agent) → 7. 답변(Answer & GQL) → 8. 검증(Verify & Gate)**의 8단계 엔지니어링 흐름을 통해 **3-Layer 위키(OKF v0.2)**와 **BigQuery Property Graph(ISO GQL)**로 결합하고, **MCP 도구(8종)**와 **Vertex AI Gemini 에이전트(`gemini-3.8-flash`)**로 근거 기반 답변을 제공하는 5-Stage 절차를 정의한다.

1. **코드 기반 원문 변환 및 Gate 0 검증**: 외부 고객 문서(`PDF`, `DOCX`, `MD`, `TXT`)는 AI 요약 없이 `pipeline/extract_docs.py`가 원문 그대로 `01_guides/*.md`로 변환하며, 적재 전 Gate 0(글자 수·12-gram 보존율 95% 이상, 텍스트 누락 쪽·조문 0건, 수동 작성 `.md` 0건)을 통과해야 한다.
2. **결정론적 청킹 및 출처 5컬럼 보존**: 조문 문서(`제N조(`)는 조문 단위로, 일반 문서는 제목·문단 단위(상한 1,500자)로 분할하며, 모든 청크에 `source_doc`·`source_sha256`·`page_from`·`page_to`·`article_no`와 SHA-256 해시 앵커(`anchor_<12hex>`)를 기록한다.
3. **데이터 유무에 따른 유연한 트랙·그래프 전환**: 정형 원장이 있으면 복제 없이 `CREATE OR REPLACE PROPERTY GRAPH`로 묶고(`standard`/`full`), 문서만 있으면 가짜 테이블을 만들지 않고 문서 내 주요 업무 단위를 `Entity`(Node), 사전·사후·제약 조건을 `Concept`(Edge)으로 추출한 위키와 전체 청크 인용 에이전트(`lite`)로 구동한다.
4. **결정론적 산식 실행 및 가드레일 상태 분리**: 금액·일수 계산은 MCP 도구 내부 SQL/Python 산식으로 수행하며, 응답 상태를 `GROUNDED`, `MATCH_NOT_FOUND`, `INSUFFICIENT_PARAMETERS`, `BQ_QUERY_ERROR` 및 `lite` 전용 인용 상태(`NO_CITATION`, `INVALID_CITATION`, `CONTEXT_LIMIT`)로 명확히 구분한다.

## 2. 8단계 엔지니어링 흐름 & 5-Stage 라이프사이클 · 스튜디오 · MCP · 노트북 매핑

| 8단계 엔지니어링 흐름 | Stage | 단계명 | 스튜디오 탭 | Stage MCP 도구 (`src/agent/mcp_server.py`) | 산출물 ID | 상세 가이드 / 한·영 노트북 |
| :--- | :---: | :--- | :--- | :--- | :---: | :--- |
| **0. 전체 흐름 투어** | **공통** | 아키텍처 개요 및 파이프라인 투어 | [`0. Overview`](https://agentic-ontology-starter-lwrlf7yogq-du.a.run.app/?tab=overview) | Stage 1~5 일괄/개별 실행 | - | [KO 노트북](../../notebooks/ko/stage0_overview_walkthrough_ko.ipynb) · [EN 노트북](../../notebooks/en/stage0_overview_walkthrough_en.ipynb) |
| **1. 준비 · 2. 분석** | **Stage 1** | 자산 탐색 · 스코핑 · CQ 정의 (Gate 0·1) | [`Stage 1. Asset`](https://agentic-ontology-starter-lwrlf7yogq-du.a.run.app/?tab=stage1) | `mcp_stage1_asset_discovery` | `D1.1`~`D1.4` | [가이드](./01_stage1_asset_and_cq_ko.md) · [KO](../../notebooks/ko/stage1_asset_and_cq_ko.ipynb) · [EN](../../notebooks/en/stage1_asset_and_cq_en.ipynb) |
| **3. 파싱 · 4. 통합** | **Stage 2** | 3-Layer 위키 · 시맨틱 그래프 | [`Stage 2. Wiki & Semantic Graph`](https://agentic-ontology-starter-lwrlf7yogq-du.a.run.app/?tab=stage2) | `mcp_stage2_wiki_and_semantic` | `D2.1`~`D2.6` | [가이드](./02_stage2_wiki_and_semantic_graph_ko.md) · [KO](../../notebooks/ko/stage2_wiki_and_semantic_graph_ko.ipynb) · [EN](../../notebooks/en/stage2_wiki_and_semantic_graph_en.ipynb) |
| **5. 구축** | **Stage 3** | Property Graph · ISO GQL | [`Stage 3. Property Graph`](https://agentic-ontology-starter-lwrlf7yogq-du.a.run.app/?tab=stage3) | `mcp_stage3_property_graph` | `D3.1`~`D3.4` | [가이드](./03_stage3_property_graph_ko.md) · [KO](../../notebooks/ko/stage3_property_graph_bigquery_spanner_ko.ipynb) · [EN](../../notebooks/en/stage3_property_graph_bigquery_spanner_en.ipynb) |
| **6. 에이전트 · 7. 답변** | **Stage 4** | MCP 스위트 · 에이전트 오케스트레이션 | [`Stage 4. Agent & MCP`](https://agentic-ontology-starter-lwrlf7yogq-du.a.run.app/?tab=stage4) | `mcp_stage4_agent_orchestration` + 런타임 3종 | `D4.1`~`D4.4` | [가이드](./04_stage4_agent_and_mcp_ko.md) · [KO](../../notebooks/ko/stage4_agent_and_mcp_execution_ko.ipynb) · [EN](../../notebooks/en/stage4_agent_and_mcp_execution_en.ipynb) |
| **8. 검증** | **Stage 5** | 4계층 리니지 · 평가 · 배포 게이트 | [`Stage 5. Lineage & Eval`](https://agentic-ontology-starter-lwrlf7yogq-du.a.run.app/?tab=stage5) | `mcp_stage5_lineage_and_eval` | `D5.1`~`D5.5` | [가이드](./05_stage5_lineage_and_eval_ko.md) · [KO](../../notebooks/ko/stage5_lineage_and_evaluation_ko.ipynb) · [EN](../../notebooks/en/stage5_lineage_and_evaluation_en.ipynb) |

## 3. 도입 트랙 (3-Track Adoption Model) 및 예측 불가능한 데이터 유입 시 분기

트랙은 프로젝트 `project.json`의 `track`으로 정한다. 기본값 `auto`는 `tables`에 등록된 고객 정형 CSV가 실제로 존재하면 `standard`, 문서만 있고 정형 CSV가 없으면 `lite`로 자동 결정한다.

| 트랙 | 활성 Stage | 물리 그래프 엔진 (`graph_engine`) | 적용 환경 및 동작 방식 |
| :--- | :---: | :---: | :--- |
| **Track 1 · Lite** | `Stage 1 → 2 → 4 → 5(citation)` | `none` (청크·문서 기반 위키) | 정형 테이블 없이 원본 문서(`customer_doc/`)만 유입되었을 때. `extract_wiki.py`가 문서에서 `Entity`(Node)·`Concept`(Edge) 위키를 추출하고, 에이전트는 전체 청크(300,000자 한도)를 컨텍스트로 받아 `[DOC_CHUNK_XXX]`를 인용해 답하며 `evidence_type: "citation"` CQ로 채점한다 |
| **Track 2 · Standard** | `Stage 1 → 2 → 3 → 4` | `bigquery` (기본) \| `spanner` (선택) \| `both` (Graph Fabric) | 정형 DW 원장(`CUSTOMER_PROVIDED`)과 비정형 위키(`EXTRACTED`)를 Property Graph로 통합해 다중 홉 GQL 추론과 2-Pass MCP 오케스트레이션을 수행할 때 |
| **Track 3 · Full** | `Stage 1 → 2 → 3 → 4 → 5` | `bigquery` (기본) \| `spanner` (선택) \| `both` (Graph Fabric) | 선언형 리니지(`config/lineage_spec.json`), Golden CQ(`sql` + `citation`), 경계값 벤치마크(10건×5회) 및 Terraform Cloud Run 배포까지 전주기를 운영할 때 |

### 3.1 유입 데이터 상황별 대응, 5축 그래프 엔진 선택 체크리스트 및 출처(`provenance`) 원칙

- **5축 그래프 엔진 선택 체크리스트 (`project.json` → `input_manifest.json`)**:
  - Stage 1에서 `source_system`(원천 위치), `latency_slo`(응답 지연 목표), `concurrency`(동시 처리량), `write_freshness`(갱신 주기), `data_scale`(데이터 규모·비용) 5개 축을 점검해 `graph_engine`을 결정한다.
  - **기본값(`"bigquery"`)**: Zero-ETL 논리 뷰 기반 대규모 분석 및 유휴 비용 0원.
  - **선택형(`"spanner"`)**: Cloud Spanner Enterprise(최소 100 PU) 기반 수십~수백 ms 온라인 멀티홉 탐색.
  - **듀얼·연동(`"both"`)**: 양쪽 엔진에 동일한 10개 테이블과 `STARTER_ONTOLOGY_GRAPH`를 적재하고, BigQuery `EXTERNAL_QUERY(spanner_fabric_conn)`를 통해 Spanner 실시간 그래프 탐색 결과와 BigQuery 문서 청크·원장을 단일 SQL로 연합 조인(Graph Fabric)한다.
- **정형 테이블 없이 그래프(Stage 3)나 SQL 평가 요청 시**: 임의로 합성 테이블을 생성하지 않고 즉시 중단한 뒤 사용자에게 **(a) 고객 정형 CSV 추가 제공, (b) 문서 기반 물리 그래프(별도 설계), (c) 합성 데모 시드 사용(명시적 승인 필요)** 또는 **`lite` 트랙 전환**을 확인받는다.
- **타 산업·신규 스키마 유입 시 모듈 오버라이드**: 통신 샘플과 다른 테이블 스키마가 들어오면 공용 파이프라인 코드를 수정하지 않고 `projects/<id>/project.json`의 `ingest_module`·`graph_module`·`mcp_module`·`engine_module`·`validator_module`에 프로젝트 전용 모듈을 지정한다.
- **출처(`provenance`) 3등급 구분**: 모든 데이터는 `CUSTOMER_PROVIDED`(고객 직접 제공 CSV), `EXTRACTED`(고객 문서에서 코드로 추출한 청크·위키), `SYNTHETIC_DEMO`(기본 데모 전용 합성 시드)로 구분하며, 고객 프로젝트에는 데모 시드나 `industry_cases` 파일 적재를 차단한다.

## 4. 런타임 리소스 및 MCP 8종 명세

### 4.1 BigQuery `starter_ontology_dw` & Cloud Spanner `starter_ontology_db` (10개 테이블 + `STARTER_ONTOLOGY_GRAPH`)

- **노드 테이블 6종**: `tb_device_master`(4), `tb_plan_master`(6), `tb_subsidy_policy`(5), `tb_customer_contract`(6), `tb_domain_rules`(4), `tb_doc_chunks`(5)
- **엣지 테이블 4종**: `edge_contract_device`(6), `edge_contract_plan`(6), `edge_subsidy_binding`(7), `edge_rule_applies_to_plan`(12)
- **Graph Fabric 연결**: `projects/<project>/locations/asia-northeast3/connections/spanner_fabric_conn` (`EXTERNAL_QUERY` 연합 조인용)
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
