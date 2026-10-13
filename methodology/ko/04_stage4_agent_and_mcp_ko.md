# Stage 4. MCP·에이전트 오케스트레이션

> 스튜디오 [`Stage 4. Agent & MCP`](https://agentic-ontology-starter-924723860007.asia-northeast3.run.app/?tab=stage4) · MCP `mcp_stage4_agent_orchestration` + 런타임 MCP 3종 · 노트북 [stage4_agent_and_mcp_execution_ko.ipynb](../../notebooks/ko/stage4_agent_and_mcp_execution_ko.ipynb) · [English](../en/04_stage4_agent_and_mcp_en.md) · [전체 방법론](./METHODOLOGY_KO.md)

## 목적

에이전트가 질문을 파라미터와 하위 목표로 나누고, **런타임 1순위 단일 진실 원천인 BigQuery Property Graph(`engine="bigquery"` 기본 또는 `engine="spanner"`)**를 조회하는 8종 MCP 도구를 호출한 뒤, 도구 결과에 있는 값만으로 답하게 한다.
- **런타임 BQG 1순위 및 원천 `anchor`/`parsed` 직접 참조 금지**: 정형·그래프가 구축된 `standard`/`full` 트랙 및 엔터프라이즈 스튜디오 런타임에서 에이전트·워크플로우·MCP는 **항상 BigQuery Property Graph(BQG)를 1순위로 조회**하며, `PolicyResolver` 역시 **Layer 1: BQG (`GRAPH_TABLE`) → Layer 2: 온톨로지 위키 허브(`ENT-*`, `CON-*`) 및 비즈니스 룰(`BR-*` `parameters[]`)** 순으로 정책 상수를 해석한다. 원천 문서(`raw`), 파싱 마크다운(`parsed`), 문단 해시 앵커(`anchor_<12hex>`, `sec-xx-pyy`)는 Stage 1~2 빌드 타임 전용이며 런타임에 직접 조회하거나 링크하지 않는다.
- 답변에는 시맨틱·비즈니스 룰 ID(`ENT-*`, `CON-*`, `BR-*` / `RULE_*`)와 실행 백엔드 식별자(BigQuery Job ID 또는 Spanner Database ID)가 들어간다.

## 입력

- 사용자 질문 (자연어) 및 그래프 엔진 선택(`"bigquery"` 기본 \| `"spanner"`)
- BigQuery(`starter_ontology_dw`) 또는 Cloud Spanner(`starter-spanner/starter_ontology_db`) 테이블 10개와 `STARTER_ONTOLOGY_GRAPH` (Stage 1~3, **런타임 1순위 SSOT**)
- Vertex AI Gemini 모델 (환경 변수 `VERTEX_GEMINI_MODEL`, 기본값 `gemini-3.8-flash`)

MCP 8종 전체 목록은 [METHODOLOGY_KO.md](./METHODOLOGY_KO.md)의 4.2절에 있다. 모두 `src/agent/mcp_server.py`의 `DomainMcpServer`에 있으며 `engine="bigquery" | "spanner"`를 모두 지원한다.

## 이 Stage의 MCP

### `mcp_stage4_agent_orchestration`

| Step | 실제 수행 (`engine="bigquery" \| "spanner"`) |
| :--- | :--- |
| `decompose_subgoals` | 이 MCP에서는 수행하지 않는다. 하위 목표 분해는 에이전트가 Gemini로 한다 |
| `dispatch_domain_mcps` | 이 MCP에서는 수행하지 않는다. 도구 호출은 에이전트가 한다 |
| `verify_grounding_anchors` | 선택된 엔진(`bigquery` 또는 `spanner`)에서 규칙 4개와 근거 청크 앵커를 조회한다 (`tb_domain_rules`와 `tb_doc_chunks` 조인) → `active_rules` |

`steps` 인자는 결과의 `executed_steps`에 기록된다.

### 런타임 MCP 3종

공통 인자(`resolve_params`): `customer_id`, `device_name`, `storage_gb`, `plan_name`, `monthly_fee_krw`, `target_plan_name`, `target_monthly_fee_krw`, `elapsed_days`, `engine`(`"bigquery"` 기본 \| `"spanner"`).
인자 없이 `query`(자연어)만 주면 질문의 숫자와 카탈로그 이름을 규칙 기반으로 뽑는다. 카탈로그에 없는 단말·요금제 이름은 버린다.

| 도구 | Steps | 수행 (`bigquery` & `spanner` 양대 엔진 지원) | 반환 상태 |
| :--- | :--- | :--- | :--- |
| `mcp_lookup_customer_profile` | `lookup_contract`, `lookup_device_price`, `lookup_subsidy_policy` | 선택된 엔진에서 약정·단말·요금제·지원금을 조인해 총지원금과 할부원금을 계산하고 `RULE_SUBSIDY_CAP`의 근거 청크를 붙인다 | `SUCCESS`, `MATCH_NOT_FOUND` (실제 요금제·지원금 목록을 함께 반환) |
| `mcp_calculate_penalty_rule` | `check_exemptions`, `compute_180d_prorated_clawback`, `compare_24m_tco` | 선택된 엔진에서 위약금 판정과 24개월 비용 비교를 SQL 한 번으로 계산한다 (아래 순서) | `SUCCESS`, `INSUFFICIENT_PARAMETERS` (고객 ID와 단말이 모두 없을 때), `MATCH_NOT_FOUND` |
| `mcp_query_graph_and_wiki` | `traverse_property_graph`, `fetch_okf_hash_anchor`, `verify_dw_schema` | 선택된 엔진의 `STARTER_ONTOLOGY_GRAPH`에서 `GRAPH_TABLE` 경로 탐색 후 근거 청크 원문을 조인한다 ([Stage 3 GQL 패턴](./03_stage3_property_graph_ko.md)) | `SUCCESS`, `MATCH_NOT_FOUND` |

백엔드 쿼리 오류는 `BQ_QUERY_ERROR` 또는 `SPANNER_QUERY_ERROR`로 반환한다 (0건으로 바꾸지 않는다).

`mcp_calculate_penalty_rule`의 판정 순서:

1. 복지 면제 대상(`welfare_status = 'SENIOR_EXEMPT'`) → `EXEMPT_WELFARE`, 0원
2. 공시지원금 정책 없음 → `NOT_APPLICABLE_NO_PUBLIC_SUBSIDY`, 0원
3. 변경 요금제 또는 경과일을 알 수 없음 → `TARGET_PLAN_NOT_RESOLVED` / `ELAPSED_DAYS_MISSING`
4. 경과일 ≥ 의무 유지일 → `EXEMPT_RETENTION_COMPLETED`, 0원
5. 변경 요금제 월정액 ≥ 기준 요금(최소 유지일이 있는 요금제 중 최저 월정액) → `NO_PENALTY_ABOVE_BASELINE`, 0원
6. 그 외 → `PRORATED_PENALTY`, `(초기 공시지원금 - 변경 요금제 공시지원금) × (의무 유지일 - 경과일) / 의무 유지일`

24개월 비용은 공시지원금 경로 `(출고가 - 총지원금) + 월정액 × 24`와 선택약정 경로 `출고가 + 월정액 × (1 - 할인율) × 24`를 함께 계산한다.

## 절차 (`src/agent/reasoning_engine.py`의 `AiFdeAgentEngine.execute_cycle()`)

### 1) `full` 트랙 (2-Pass MCP 오케스트레이션)

1. **카탈로그 조회**: BigQuery에서 단말·요금제·고객 목록을 읽는다 (5분 캐시).
2. **분해 (Gemini 1회차)**: 질문을 파라미터 JSON과 하위 목표(도구 선택)로 바꾼다. 이름은 카탈로그 값만 허용한다.
3. **검증**: 요금·일수는 질문에 실제로 적힌 숫자만 쓴다. 카탈로그에 없는 이름은 버린다. Gemini 호출이 실패하면 규칙 기반 추출로 대신한다.
4. **도구 호출**: 하위 목표 순서대로 MCP를 실행한다. 런타임 도구를 쓰면 `mcp_query_graph_and_wiki`를 근거 확인 단계로 추가한다.
5. **응답 상태**: 도구 상태를 보고 `BQ_ERROR` → `MATCH_NOT_FOUND` → `INSUFFICIENT_PARAMETERS` → `GROUNDED` 순서로 정한다. 답변 생성이 실패하면 `LLM_ERROR`다.
6. **답변 (Gemini 2회차)**: 도구 결과 JSON만 근거로 쓴다. 순서는 결론 → 근거 데이터 → 규칙·청크 → 관련 추가 정보(예외·주의사항) → 실행 정보(Job ID)다. 결론은 질문의 조건을 규칙에 대입한 하나의 답이며, 조건에 따라 갈리면 조건별로 나눠 쓴다. 최종 답변은 Stage 5에서 루브릭으로 채점한다.

질문 하나에 Gemini를 2번 호출하며, 결과에 토큰 수와 BigQuery Job ID가 기록된다.

### 2) `lite` 트랙 (문서 전용 1-Pass 청크 컨텍스트 런타임: `AiFdeAgentEngine._lite_cycle()`)

고객이 정형 CSV 없이 문서(`01_raw_docs/`, `03_wiki/`)만 투입한 프로젝트(`track: "lite"`)에서는 BigQuery SQL MCP 대신 BigQuery `tb_doc_chunks`의 전체 청크 행(`get_doc_chunks`)을 컨텍스트(`lite.max_context_chars` 기본 `300,000`자 한도, 초과 시 `CONTEXT_LIMIT`로 중단)로 넣어 1-Pass 응답을 생성한다.

- **인용 강제**: 모든 답변 문장은 반드시 출처 청크 ID를 `[DOC_CHUNK_XXX]` 형식으로 인용해야 한다.
- **인용 검증 상태**:
  - `GROUNDED`: 답변 내 `[DOC_CHUNK_XXX]` 인용이 이번 호출에서 조회한 `tb_doc_chunks` 청크 ID에 존재함이 확인된 상태.
  - `NO_CITATION`: 답변에 `[DOC_CHUNK_XXX]` 인용이 누락된 상태.
  - `INVALID_CITATION`: 조회한 `tb_doc_chunks`에 없는 청크 ID를 환각 인용한 상태.
  - `CONTEXT_LIMIT`: 문서 청크 텍스트 합계가 `300,000`자를 초과하여 컨텍스트 주입이 제한된 상태.

### 도구 단위와 복합 질문 원칙

- 도구 하나는 하나의 조회 책임(예: 지원금 조회, 위약금 산정, 규칙·청크 확인)을 갖고, 결과와 함께 상태와 BigQuery Job ID를 반환한다. 하드코딩 값이나 기본값으로 빈 슬롯을 채우지 않는다.
- 같은 데이터를 다른 이름으로 돌려주는 도구는 하나로 합치고 나머지는 별칭으로 둔다.
- 복합 질문(조건·엔티티가 여럿)은 계획 수립 단계에서 여러 도구 호출로 나누고, 답변은 도구 결과만으로 쓴다. 필요한 값이 데이터에 없으면 산정하지 않고 없다고 답한다.
- 평가셋 밖 질문(카탈로그의 다른 단말·요금제·일수 조합)으로 도구 범위를 함께 점검한다. 같은 문항으로 반복 조정한 점수는 과적합 가능성을 함께 기록한다.

## 권장 방법: Wiki Agent(Stage 2 게이트)와 BQG Agent(런타임 1순위) 비교

두 에이전트의 차이는 역할과 근거를 가져오는 곳이다. **Wiki Agent는 물리 그래프 구축 전 Stage 2 위키 품질을 검증하는 게이트**이고, **BQG Agent(및 Workflow Agent · AI FDE)는 Stage 3 이후 운영 런타임의 1순위 주체**다.

| 단계 | Wiki Agent (Stage 2 종료 게이트) | BQG Agent (런타임 1순위 주체) |
| :---: | :--- | :--- |
| 1 | GCS 위키 목차(index) 읽기 | 슬롯 추출 (Flash) |
| 2 | Flash가 목차를 보고 열 엔티티·개념 문서 선택 | **BigQuery Property Graph (BQG) 1순위 GQL 조회** |
| 3 | 선택 문서와 관계 1단계 문서를 GCS에서 읽기 | BQG/DW 조회 값과 `PolicyResolver`(Layer 1 BQG)로 코드 계산 |
| 4 | Flash 답변 (위키 문서 ID `ENT-*`/`CON-*` 인용 · 원천 `anchor` 직접 링크 금지) | Flash 답변 (시맨틱·그래프 ID `ENT-*`/`CON-*`/`BR-*` + `bq_job_ids` 인용) |
| BigQuery·그래프 | 사용하지 않음 (Stage 2 게이트 전용) | **1순위로 사용 (Primary SSOT)** |

- 두 에이전트 모두 응답에 단계별 소요 시간과 토큰 사용량(Vertex `usageMetadata`의 입력·출력·thinking)을 기록한다.
- 문서를 통째로 넣는 방식은 청크 검색보다 입력 토큰이 늘어난다(참고 사례: 약 3배). 읽는 문서 수와 문서당 글자 상한을 함께 기록한다.

스타터의 현재 구현은 다르다. 에이전트는 `AiFdeAgentEngine` 하나이며 Wiki Agent와 BQG Agent를 따로 두지 않는다.

- `lite` 트랙: GCS 위키 목차나 문서별 파일을 읽지 않고, `tb_doc_chunks` 전체 행을 Gemini 1회 호출 컨텍스트에 넣는다(`_lite_cycle`).
- `standard`/`full` 트랙: MCP 도구가 BigQuery 또는 Spanner를 실제로 조회한다.
- 토큰은 호출 합계의 입력(`prompt_tokens`)·출력(`candidates_tokens`)만 기록하고 thinking 토큰은 기록하지 않는다. 시간은 도구별 `tool_elapsed_ms`, `bq_elapsed_ms`와 전체 소요 시간을 기록한다.

## 권장 방법: AI FDE 도구 구성과 리소스 표시

- 에이전트 도구함에는 업무 질문에 답하는 조회 도구만 둔다. 상태 요약만 하고 데이터를 조회하지 않는 방법론 Stage 도구는 에이전트 도구로 제공하지 않고, 상태만 점검하는 "5개 Stage 전체 실행" 버튼도 두지 않는다.
- 계획 수립 호출마다 사용자 질문(목표)을 함께 넘기고, 하위 목표는 `id`, `intent`, `tool`, `reason`, `status`로 구조화해 표시한다.
- 도구 호출마다 리소스 사용량을 표시한다: BigQuery job ID, 반환 행, 처리 바이트, 캐시 적중, 쿼리 시간, 조회 테이블, 실행 SQL. 응답에는 계획·답변 호출의 토큰 사용량을 표시한다.
- 프리셋 질문은 비즈니스 / 엔지니어링 / 복합(여러 도메인) 시나리오로 나누고, 실제 데이터에 있는 값(단말·요금제·거래 ID·기간)으로 쓴다. 프리셋은 모두 실행해 결과 상태를 기록한다(참고 사례: 14건 중 14건 `SUCCESS`).

스타터의 현재 구현:

- Stage MCP 5종은 실제 검증 쿼리(테이블 목록·행 수, 중복 키, GQL 경로 수 등)를 실행하므로 그대로 둔다. 에이전트 도구 목록(`get_tool_catalog()`)에도 8종이 모두 들어 있다.
- 하위 목표 필드는 `id`, `goal`, `tool`, `category`이며 `intent`·`status`는 없다. 분해는 Gemini 1회 호출이다.
- 도구 결과에는 `bq_jobs`(job ID·엔진·상태·소요 ms·반환 행·SQL), `bq_job_ids`, `bq_elapsed_ms`, `executed_sql`, `tool_elapsed_ms`가 들어간다. 처리 바이트, 캐시 적중, 조회 테이블 목록은 기록하지 않는다.
- 프리셋은 Stage 4 콘솔의 CQ 샘플 버튼(`CQ-02`~`CQ-05`)이며 시나리오 분류는 없다.

## 리소스 직결 아키텍처 (Ready-to-Use 리소스 커넥터 + 도메인 비즈니스 도구 3종)

스타터팩 v2.2부터 내부 온톨로지 빌더 MCP 파이프라인은 플랫폼 계층으로 추상화되어 제외되고, **Ready-to-Use GCP 리소스에 직결된 커넥터(`src/resource_connector.py`)**와 **커스터마이징 대상 도메인 비즈니스 도구 3종(`src/agent/mcp_server.py`)**만 깔끔하게 노출된다:

| 구분 | 모듈 / 파일 | 역할 및 책임 | 노출 도구 / 메서드 |
| :--- | :--- | :--- | :--- |
| **Ready-to-Use Resource Connector** | `src/resource_connector.py` (`OntologyResourceConnector`) | **준비된 GCP 온톨로지 리소스 직결 및 점검**: BigQuery(`starter_ontology_dw` 10개 테이블), `STARTER_ONTOLOGY_GRAPH`, GCS 3-Layer OKF 위키 및 `W1~W3` 워크플로, Cloud Spanner Graph 연결 상태를 점검 | `verify_ready_resources()`, `stage1_resource_check` ~ `stage5_resource_check` |
| **Domain Business Tools (3종)** | `src/agent/mcp_server.py` (`DomainMcpServer`) | **도메인·프로젝트별 결정론적 업무 실행 도구**: 각 프로젝트의 정형 원장·규칙·계산식을 실행하며 워크플로(`W1~W3`) 및 비즈니스 규칙(`RULE_*`)에 1:1 바인딩 | `mcp_lookup_customer_profile`, `mcp_calculate_penalty_rule`, `mcp_query_graph_and_wiki` |

## 산출물

| ID | 산출물 | 스타터에서 |
| :--- | :--- | :--- |
| `D4.1` | 도메인 비즈니스 도구 서버 및 리소스 커넥터 | `src/agent/mcp_server.py` (`DomainMcpServer`) + `src/resource_connector.py` (`OntologyResourceConnector`) |
| `D4.2` | AI FDE 시맨틱 라우팅 및 하위 목표 분해 엔진 (`Gate G2-W`) | `src/agent/reasoning_engine.py` (`AgenticReasoningEngine`) |
| `D4.3` | 크로스도메인 컨텍스트 전달 및 핸드오프 프로토콜 | `execute_cycle()`이 검증된 파라미터를 도메인 도구 3종에 일관된 형식으로 전달 |
| `D4.4` | 에이전트 경계값 검증 스위트 | 에이전트 단위 경계값 질의 10개는 [Stage 5](./05_stage5_lineage_and_eval_ko.md)에서 다룬다 |
| `D4.5` | 비즈니스 규칙(`RULE_*`) · 워크플로(`W1~W3`) · 도메인 도구 바인딩 | `data/llm_wiki/business_rules.json` 및 `data/llm_wiki/business_workflows.json` |

## 게이트 (Gate G2-W & Gate 4)

- [ ] `get_tool_catalog()`에 커스터마이징 가능한 도메인 비즈니스 도구 3종(`mcp_lookup_customer_profile`, `mcp_calculate_penalty_rule`, `mcp_query_graph_and_wiki`)이 깔끔하게 노출된다.
- [ ] Golden CQ 질문의 응답 상태가 `GROUNDED`이고, 답변에 근거 청크 ID(`DOC_CHUNK_*`)와 BigQuery Job ID가 포함된다.
- [ ] 정보가 부족한 질문은 `INSUFFICIENT_PARAMETERS`로 끝나고 수치를 지어내지 않는다.
- [ ] 조건에 맞는 데이터가 없으면 답변 첫 문장에서 `MATCH_NOT_FOUND`(0건)를 밝힌다.

## 스튜디오에서 보기

[Stage 4. Agent & Tools 탭 열기](https://agentic-ontology-starter-924723860007.asia-northeast3.run.app/?tab=stage4)

- 왼쪽: 도메인 비즈니스 도구 3종 카탈로그 및 리소스 점검 버튼.
- 오른쪽: AI FDE 추론 콘솔 (`Gate G2-W Audited`). CQ 샘플 버튼(`CQ-02`~`CQ-05`)이나 직접 쓴 질문을 `Execute FDE`로 실행하면 하위 목표, 도구 호출, 결과가 순서대로 나온다.
- 로컬 스튜디오에서는 `POST /api/query` (`{"query": "..."}`)와 `POST /api/mcp/execute` (`{"tool_name": "...", "args": {...}}`)로도 호출할 수 있다.

## 노트북

[stage4_agent_and_mcp_execution_ko.ipynb](../../notebooks/ko/stage4_agent_and_mcp_execution_ko.ipynb)

## 내 데이터에 적용하기

1. **문서 전용 프로젝트 (`lite` 트랙)**: 별도 코드 수정 없이 `_lite_cycle()`이 `tb_doc_chunks` 전체 청크를 읽어 `[DOC_CHUNK_XXX]` 인용 기반으로 동작한다.
2. **플랫폼 코어 MCP 원격 빌드 + 커스텀 비즈니스 MCP 바인딩**: `src/agent/platform_core_mcp.py`의 `build_domain_spec_from_project()`로 프로젝트의 `domain_mcp_tools`를 선언하고 `PlatformCoreMcpClient.call_tool("mcp_builder_run_full_pipeline", ...)`를 호출해 Stage 1~6 온톨로지 및 스튜디오 번들을 생성한다.
3. **도구 SQL 및 정규식 수정**: 기본 템플릿을 수정할 경우 런타임 MCP 3종의 SQL, `get_live_catalog()`, `extract_params_from_text()`(고객 ID 정규식 `CUST_[A-Z]+_\d{3}`), 프롬프트(`DECOMPOSE_SYS`, `SYNTH_SYS`)를 도메인에 맞게 변경한다.
4. **모델**: 에이전트 서빙 모델은 `VERTEX_GEMINI_MODEL`(기본 `gemini-3.8-flash`), 플랫폼 코어 MCP 빌드 모델은 `Gemini 4 Argon`(`gemini-4-argon`, 쿼터 소진 시 `QUOTA_EXHAUSTED_ERROR` 명시 반환)으로 분리한다.
