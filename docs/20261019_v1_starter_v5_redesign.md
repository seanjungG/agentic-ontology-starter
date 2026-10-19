# Agentic Ontology Starter v5 — 재구성 설계 (GOAL-233)

> 목표: **이 스튜디오 + 이 깃헙만 있으면** 누구나 자기 데이터 · 자기 GCP에서 레퍼런스 스튜디오와 거의 같은 수준의 결과물(OKF 위키 · Property Graph · 에이전트 · 평가)을 만들고, 그 과정을 **코드와 MCP 호출 파라미터로 그대로 인계**받는다. 방법론의 핵심 노하우(프롬프트 · 품질 게이트 · 그래프 설계 규칙)는 **Platform Core MCP 안에만** 있다.

## 1. 노트북 랩과의 차이

| | 노트북 랩 | 스타터 v5 |
| :--- | :--- | :--- |
| 목적 | 정해진 데이터로 방법론을 셀 단위로 **배우기** | **내 데이터 · 내 GCP**로 결과물을 **만들고 가져가기** |
| 데이터 | 고정 합성 데이터 | 업로드 · GCS 경로 · BigQuery 테이블 · 샘플 팩 |
| 리소스 | 랩이 세션별로 만들고 지움 | 사용자의 프로젝트 · 버킷 · 데이터셋 (사용자 신원 또는 SA) |
| 결과 | 화면 안에서 끝남 | 스튜디오에서 탐색 · 수정 · 실험 → 코드 번들 · CLI · MCP 설정으로 인계 |

## 2. 사용자 흐름 (3단 + 인계)

```text
① 이해        전체 흐름도 — 입력 → 위키 → 그래프 → 에이전트 → 평가, 각 단계가 무엇을 · 어디에 만드는지
② 구성 · 구축  1 상황 · 목적 → 2 데이터 → 3 GCP · 권한(SA) → 4 구축 실행(단계별 · 재개 가능)
③ 스튜디오     개요 · 자산 · 위키(보기 · 수정 · 게이트) · 그래프(스키마 · GQL/SQL) · 검색 · 에이전트 · 평가(CQ 편집)
④ 코드 · 인계  CLI 재현 명령 · MCP 호출 로그(도구 + 파라미터) · MCP 클라이언트 설정 · 번들(zip)
```

- 1 상황 · 목적: 프리셋(통신 지원금 · 화장품 표시광고 · 금융 상품 약관 · 직접 입력) + 목적 문장 + 질문 유형(W1 규정 안내 · W2 데이터 조회 · W3 판정 · 계산). 데이터 유형(P1 문서 · P2 테이블 · P3 둘 다)은 2단계 입력으로 자동 결정.
- 2 데이터: 파일 업로드(.md · .txt · .csv · .json) · GCS 경로(`gs://bucket/prefix/`) · BigQuery 테이블(`project.dataset.table`) · 샘플 팩(KO/EN). 섞어 쓸 수 있다.
- 3 GCP · 권한: 프로젝트 · 리전 · 버킷 · 데이터셋 · 그래프 이름 + **신원**. 확인 버튼이 실제 권한 · 예약 · Gemini · Core MCP를 점검하고, 부족하면 **그대로 복사해 실행할 설정 스크립트**(API 활성화 · 버킷 · SA · 역할 · 예약)를 만든다.
- 4 구축 실행: 단계마다 별도 요청(NDJSON)이라 중간 실패 시 그 단계부터 다시 실행한다. 모든 MCP 호출은 도구 · 대상 · 파라미터 요약 · ms로 기록된다.

## 3. 신원 (Identity) — "특정 권한 SA를 주면"

| 모드 | 동작 | 쓰는 곳 |
| :--- | :--- | :--- |
| `runtime` | 스타터 서버 자신의 신원(Cloud Run SA · 로컬 gcloud). 쓰기는 `STARTER_WRITE_PROJECTS`만 | 데모 샌드박스 |
| `token` | 사용자가 붙여 넣은 OAuth 토큰 — `gcloud auth print-access-token` 또는 `--impersonate-service-account=SA`. 서버는 저장 · 기록하지 않고 요청 동안만 사용, tokeninfo로 주체 · 만료 표시 | 공개 데모에서 내 프로젝트 · 내 SA |
| `impersonate` | SA 이메일만 입력 → 스타터 런타임 SA가 IAM Credentials `generateAccessToken`으로 단기 토큰 발급 (사용자가 런타임 SA에 `roles/iam.serviceAccountTokenCreator` 부여). `STARTER_IMPERSONATE_ALLOW` 패턴에 맞는 SA만 | 자체 배포(로컬 · 내 Cloud Run) |

토큰은 요청 스레드에만 바인딩되어 Core MCP(`X-AOS-Access-Token`)와 Vertex AI 호출에 쓰인다. 사용자 신원이면 쓰기 보호(`STARTER_WRITE_PROJECTS`)는 적용하지 않는다 — 권한은 그 신원의 IAM이 결정한다.

## 4. 노하우 경계 — 무엇이 공개 코드이고 무엇이 MCP인가

| 공개 (깃헙 · 스타터) | 보호 (Core MCP `mcp_knowhow_*`) | 사용자 GCP |
| :--- | :--- | :--- |
| UI · 오케스트레이션 · CLI · 데이터 플레인 호출 순서 · 워크스페이스 형식 | 소스 스코핑(PK/FK 추론 · 문서 역할) · CQ 초안 · OKF 위키 컴파일 + W1~W7 게이트 · 그래프 설계 + BigQuery DDL/적재 SQL 생성 · 에이전트 추론 단계 · 채점 | GCS(원본 · 위키 · 워크스페이스) · BigQuery(테이블 · 노드/엣지 · Property Graph) · Vertex AI(Gemini 호출 비용) |

- 노하우 도구는 **무상태**다: 입력(문서 텍스트 · 스키마 · 표본 행)을 받아 결과(페이지 · DDL · 다음 행동)를 돌려줄 뿐 데이터를 저장하지 않는다.
- Gemini 호출은 **호출자 토큰 + 호출자 프로젝트**로 실행된다(Core MCP 서비스 계정은 여전히 권한 0).
- 데이터 접근은 기존 데이터 플레인 도구(`storage_*` · `bigquery_*`)로 호출자 토큰을 써서 실행한다.

| 도구 | 입력 | 출력 |
| :--- | :--- | :--- |
| `mcp_knowhow_scope` | 목적 · 문서 목록(머리말) · 테이블 스키마 + 표본 | 데이터 유형(P) · 질문 유형(W) · 문서 역할 · PK/FK 후보 · 단계 계획 |
| `mcp_knowhow_draft_cqs` | 목적 · 문서 · 테이블 표본 · 개수 | CQ(질문 · 유형 · 필요 근거 · 기준 답 · 핵심어) |
| `mcp_knowhow_compile_wiki` | 문서 · 테이블 컬럼 · 목적 (또는 `pages` 검증 모드) | OKF 페이지 · Markdown 파일 · 게이트 W1~W7 · 인덱스 |
| `mcp_knowhow_design_graph` | 테이블 스키마 · 위키 페이지 · 목적 · 데이터셋 · 그래프 이름 | 설계 JSON · 검증 결과 · 실행 SQL(노드/엣지 테이블 · `CREATE PROPERTY GRAPH`) · 위키 노드 행 · 검증 GQL |
| `mcp_knowhow_agent_step` | 에이전트 종류 · 질문 · 컨텍스트(위키 목록 · 그래프 스키마) · 지금까지의 관찰 | 다음 행동(`read_wiki` · `gql` · `sql` · `answer`) — 계산은 도구 안에서 처리 |
| `mcp_knowhow_judge` | 질문 · 기준 답 · 핵심어 · 에이전트 답 | 판정(통과 1 · 부분 0.5 · 실패 0) · 근거 |

## 5. 워크스페이스 — 결과물의 단위

```text
gs://<bucket>/aos/<ws_id>/
  workspace.json        상황 · 목적 · 언어 · 리소스 · 소스 · 단계 상태 (비밀값 없음)
  raw/                  업로드한 원본
  cqs.json              CQ (스튜디오에서 편집)
  wiki/ontology/01_summary|02_entities|03_concepts/*.md · wiki/index.json
  graph/design.json · graph/statements.sql
  runs/<ts>.json        평가 실행 결과
  mcp_calls.jsonl       모든 MCP 호출(도구 · 인자 요약 · 결과 상태 · ms)
BigQuery <project>.<dataset>
  원천 테이블 · N_<Label> 노드 테이블 · E_<LABEL>_<From>_<To> 엣지 테이블 · <GRAPH> Property Graph
```

- 데이터셋 기본값은 워크스페이스마다 하나(`aos_<ws>`)라 여러 사람이 같은 프로젝트를 써도 겹치지 않는다. 런타임 신원(데모)으로 만든 데이터셋은 기본 테이블 만료 7일.
- 스튜디오는 `workspace.json`만 있으면 다시 열 수 있다(버킷 + ws_id).

## 6. 구축 단계

| 단계 | 하는 일 | MCP 호출 |
| :---: | :--- | :--- |
| S0 준비 | 데이터셋 생성(없으면) · workspace.json | `bigquery_create_dataset` · `storage_upload_object` |
| S1 수집 · 프로파일 | 문서 읽기 · CSV → BigQuery 적재 · BigQuery 스키마/표본 · Gate 0 파싱 · 스코핑 | `storage_read_object` · `bigquery_load_table` · `bigquery_get_table_info` · `bigquery_execute_sql` · `mcp_builder_parse_documents_gate0` · `mcp_knowhow_scope` |
| S2 CQ | 목적 기반 CQ 초안 | `mcp_knowhow_draft_cqs` |
| S3 위키 | OKF 3-Layer 위키 + 게이트 → GCS | `mcp_knowhow_compile_wiki` · `storage_upload_object` |
| S4 그래프 | 설계 → 노드/엣지 테이블 → Property Graph → 검증 GQL | `mcp_knowhow_design_graph` · `bigquery_execute_sql` · `bigquery_load_table` |
| S5 평가 | CQ를 에이전트로 다시 묻고 채점 | `mcp_knowhow_agent_step` · 데이터 도구 · `mcp_knowhow_judge` |

P1(문서만)은 S4를 건너뛰고, P2(테이블만)는 S3를 건너뛴다(그래프는 테이블만으로).

## 7. 에이전트 (스튜디오 · CLI 공통)

- **Wiki Agent**: 위키 페이지만 근거 (`read_wiki` → `answer`)
- **Graph Agent**: 그래프 GQL/SQL만 근거 (`gql`/`sql` → `answer`). Enterprise 예약이 없어 GQL이 412면 노드/엣지 테이블 SQL로 자동 전환
- **Hybrid Agent**: 위키 규칙 + 그래프 데이터 + 계산 (W3 판정 · 계산)

루프는 스타터(또는 사용자 코드)가 돈다: `agent_step` → 데이터 행동 실행(사용자 토큰) → 관찰을 붙여 다시 `agent_step` → `answer`. 최대 6단계.

## 8. 코드 인계

1. **CLI** (깃헙 그대로): `python -m src.cli build --workspace gs://<bucket>/aos/<ws>/workspace.json` · `ask` · `eval`
2. **MCP 호출 로그**: 스튜디오가 실행한 순서 그대로의 `tools/call` 목록(도구 · 인자) — 다른 언어 · 다른 오케스트레이터에서도 같은 파라미터로 재현
3. **MCP 클라이언트 설정**: Gemini CLI / ADK에서 Core MCP를 도구로 붙이는 설정 (`X-AOS-Access-Token` 헤더)
4. **번들(zip)**: `workspace.json` · `.env` · `setup_gcp.sh` · `run_build.sh` · `ask.sh` · `mcp_calls.jsonl` · `mcp_config.json` · `README.md`

## 9. 기존 자산 보존

- 기존 6단계 마법사(큐레이션 데이터 · Flow A/B/C · 100점 기준 결과)는 `/wizard`로 그대로 둔다(레퍼런스 결과 비교용).
- `/ucc` 페이지 · API는 변경 없음.
- Core MCP는 **도구 추가만** 한다(기존 38종 동작 불변) — 노트북 랩 실습이 같은 Core MCP를 쓰기 때문.
