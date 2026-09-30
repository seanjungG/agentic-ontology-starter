# Stage 4. MCP·에이전트 오케스트레이션

> 스튜디오 [`Stage 4. Agent & MCP`](https://agentic-ontology-starter-924723860007.asia-northeast3.run.app/?tab=stage4) · MCP `mcp_stage4_agent_orchestration` + 런타임 MCP 3종 · 노트북 [stage4_agent_and_mcp_execution_ko.ipynb](../../notebooks/ko/stage4_agent_and_mcp_execution_ko.ipynb) · [English](../en/04_stage4_agent_and_mcp_en.md) · [전체 방법론](./METHODOLOGY_KO.md)

## 목적

에이전트가 질문을 파라미터와 하위 목표로 나누고, 선택된 물리 엔진(`engine="bigquery"` 기본 또는 `engine="spanner"`)을 조회하는 8종 MCP 도구를 호출한 뒤, 도구 결과에 있는 값만으로 답하게 한다.
답변에는 규칙 ID, 근거 청크 ID, 실행 백엔드 식별자(BigQuery Job ID 또는 Spanner Database ID)가 들어간다.

## 입력

- 사용자 질문 (자연어) 및 그래프 엔진 선택(`"bigquery"` 기본 \| `"spanner"`)
- BigQuery(`starter_ontology_dw`) 또는 Cloud Spanner(`starter-spanner/starter_ontology_db`) 테이블 10개와 `STARTER_ONTOLOGY_GRAPH` (Stage 1~3)
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

### 2) `lite` 트랙 (문서 전용 1-Pass 청크 컨텍스트 런타임: `execute_lite_doc_cycle()`)

고객이 정형 CSV 없이 문서(`01_raw_docs/`, `03_wiki/`)만 투입한 프로젝트(`track: "lite"`)에서는 BigQuery SQL MCP 대신 추출된 `doc_chunks.jsonl` 및 `entities.md`/`concepts.md` 컨텍스트(최대 `300,000`자 한도)를 기반으로 1-Pass 응답을 생성한다.

- **인용 강제**: 모든 답변 문장은 반드시 출처 청크 ID를 `[DOC_CHUNK_XXX]` 형식으로 인용해야 한다.
- **인용 검증 상태**:
  - `GROUNDED`: 답변 내 `[DOC_CHUNK_XXX]` 인용이 실제 프로젝트 `doc_chunks.jsonl`에 존재하는 유효한 청크 ID임이 확인된 상태.
  - `NO_CITATION`: 답변에 `[DOC_CHUNK_XXX]` 인용이 누락된 상태.
  - `INVALID_CITATION`: 실제 `doc_chunks.jsonl`에 존재하지 않는 청크 ID를 환각 인용한 상태.
  - `CONTEXT_LIMIT`: 문서 청크 텍스트 합계가 `300,000`자를 초과하여 컨텍스트 주입이 제한된 상태.

## 산출물

| ID | 산출물 | 스타터에서 |
| :--- | :--- | :--- |
| `D4.1` | 온톨로지 MCP 서버 스펙 및 구현체 | `src/agent/mcp_server.py` (`DomainMcpServer`, 8종) |
| `D4.2` | AI FDE 시맨틱 라우팅 및 다중 목표 분해 엔진 | `src/agent/reasoning_engine.py` (`AiFdeAgentEngine`) |
| `D4.3` | 크로스도메인 컨텍스트 전달 및 핸드오프 프로토콜 | 별도 문서 없음. `execute_cycle()`이 검증된 파라미터 하나를 모든 도구에 같은 형식으로 넘긴다 |
| `D4.4` | MCP 경계값 검증 스위트 및 고도화 리포트 | 도구 단위 경계값 스위트는 없다. 에이전트 단위 경계값 질의 10개는 [Stage 5](./05_stage5_lineage_and_eval_ko.md)에서 다룬다 |

## 게이트 (Gate 4)

- [ ] `get_tool_catalog()`에 8종이 있다 (스튜디오 `전체 (8)`).
- [ ] Golden CQ 질문의 응답 상태가 `GROUNDED`이고, 답변에 근거 청크 ID와 BigQuery Job ID(`full` 트랙) 또는 유효한 `[DOC_CHUNK_XXX]` 인용(`lite` 트랙)이 있다.
- [ ] 정보가 부족한 질문은 `INSUFFICIENT_PARAMETERS`로 끝나고 수치를 지어내지 않는다.
- [ ] 조건에 맞는 데이터가 없으면 답변 첫 문장에서 `MATCH_NOT_FOUND`(0건)를 밝힌다.

## 스튜디오에서 보기

[Stage 4. Agent & MCP 탭 열기](https://agentic-ontology-starter-924723860007.asia-northeast3.run.app/?tab=stage4)

- 왼쪽: MCP 카탈로그 8종 (`Stage MCP (5)`, `Runtime MCP (3)` 필터). 도구마다 `▶ Step 실행` 버튼이 있다.
- 오른쪽: 에이전트 콘솔. CQ 샘플 버튼(`CQ-02`~`CQ-05`)이나 직접 쓴 질문을 `Execute FDE`로 실행하면 하위 목표, 도구 호출, 결과가 순서대로 나온다.
- 로컬 스튜디오에서는 `POST /api/query` (`{"query": "..."}`)와 `POST /api/mcp/execute` (`{"tool_name": "...", "args": {...}}`)로도 호출할 수 있다.

## 노트북

[stage4_agent_and_mcp_execution_ko.ipynb](../../notebooks/ko/stage4_agent_and_mcp_execution_ko.ipynb)

## 내 데이터에 적용하기

1. **문서 전용 프로젝트 (`lite` 트랙)**: 별도 코드 수정 없이 `execute_lite_doc_cycle()`이 자동으로 `doc_chunks.jsonl`과 `03_wiki/`를 읽어 `[DOC_CHUNK_XXX]` 인용 기반으로 동작한다.
2. **커스텀 도메인 테이블 (Scenario C)**: 샘플 6종 CSV와 다른 도메인 테이블 스키마를 쓸 경우, `project.json`에 `"mcp_module"`과 `"engine_module"`을 지정하여 도메인 전용 MCP 핸들러와 에이전트 엔진을 주입한다.
3. **도구 SQL 및 정규식 수정**: 기본 템플릿을 수정할 경우 런타임 MCP 3종의 SQL, `get_live_catalog()`, `extract_params_from_text()`(고객 ID 정규식 `CUST_[A-Z]+_\d{3}`), 프롬프트(`DECOMPOSE_SYS`, `SYNTH_SYS`)를 도메인에 맞게 변경한다.
4. **모델**: `VERTEX_GEMINI_MODEL`로 지정한다.
