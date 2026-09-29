# Agentic Ontology Starter — 마스터 제품·아키텍처 헌장 (`01_prod.md`)

- **역할**: 이 스타터팩을 클론하여 새로운 도메인/고객사 프로토타입을 구축할 때, **사람(FDE·엔지니어)과 AI 코딩 에이전트(Jetski / Antigravity / Cursor / Claude Code)가 공통으로 준수해야 하는 최상위 기준 문서**입니다.
- **핵심 원칙**: 이 저장소는 백지상태에서 코드를 새로 짜는 보일러플레이트가 아니라, **이미 동작이 검증된 5-Stage 온톨로지 파이프라인·8종 MCP·2-Pass 에이전트·6-Tab 라이트 스튜디오를 그대로 유지한 채 데이터와 도메인 규칙만 빠르게 교체(Swap)하여 프로토타이핑**하는 레퍼런스 엔진입니다.
- **관련 문서**:
  - 상황별 프로토타이핑 레시피: [`PROTOTYPING_PLAYBOOK.md`](PROTOTYPING_PLAYBOOK.md)
  - AI 에이전트 부트스트랩 지침: [`GEMINI.md`](GEMINI.md) · [`AGENTS.md`](AGENTS.md) · [`.cursorrules`](.cursorrules)
  - 웹 UI 디자인 시스템 표준: [`DESIGN.md`](DESIGN.md)
  - 5-Stage 방법론 상세: [`methodology/METHODOLOGY_KO.md`](methodology/METHODOLOGY_KO.md) · [`methodology/METHODOLOGY_EN.md`](methodology/METHODOLOGY_EN.md)
  - 8단계 실습 노트북 허브: [`notebooks/README.md`](notebooks/README.md)

---

## 1. 아키텍처 불변 계약 (AI 에이전트가 임의로 변경하면 안 되는 6대 원칙)

다른 프로젝트로 이 스타터팩을 가져가서 프로토타이핑할 때, AI 코딩 에이전트는 아래 **6대 아키텍처 골격**을 임의로 삭제하거나 다른 프레임워크로 재작성해서는 안 됩니다.

| 번호 | 불변 아키텍처 요소 | 기준 명세 및 파일 위치 | 금지 행위 (Anti-Patterns) |
| :---: | :--- | :--- | :--- |
| **1** | **5-Stage × 8단계 엔지니어링 흐름 & 6-Tab 스튜디오** | `0. Overview` · `Stage 1. Asset` · `Stage 2. Wiki & Semantic Graph` · `Stage 3. Property Graph` · `Stage 4. Agent & MCP` · `Stage 5. Lineage & Eval` (`src/web/studio_server.py`) | 탭 구조를 임의로 쪼개거나 별도 React/Streamlit 서버·다중 포트를 새로 띄우는 행위 금지 |
| **2** | **3-Track 도입 설정 (`starter_config.json`)** | `lite`(`Stage 1→2→4`, 물리 그래프 없음) · `standard`(`Stage 1→2→3→4`, BigQuery/Spanner Graph) · `full`(`Stage 1→2→3→4→5`, 리니지·50회 경계 평가·배포 게이트) | 설정 파일을 무시하고 코드에 특정 트랙 분기를 하드코딩하는 행위 금지 |
| **3** | **정형 DW 원장 + 비정형 3-Layer OKF 위키 이중 근거 구조** | 정형 마스터/트랜잭션은 BigQuery 테이블 노드로 적재하고, 비정형 문서는 `data/llm_wiki/`(`summary.md`, `entities.md`, `concepts.md`, `rules.md`)와 `tb_doc_chunks`(SHA-256 해시)·`tb_domain_rules`로 적재 (`pipeline/ingest.py`) | 문서를 단순 벡터 청크로만 쪼개고 도메인 규칙(`tb_domain_rules`)과 출처 해시(`sha256_hash`) 연결을 생략하는 행위 금지 |
| **4** | **Stage MCP 5종 + Runtime MCP 3종 (총 8종 표면)** | Stage 1~5 파이프라인 검증용 MCP 5종 고정 유지 + 도메인 런타임 도구 3종(`src/agent/mcp_server.py`) | 기존 MCP 인터페이스를 깨뜨리고 에이전트 내부에 SQL을 직접 인라인 작성하는 행위 금지 |
| **5** | **2-Pass Gemini 추론 엔진 & 3상태 판정** | 1회차(카탈로그 기반 슬롯 추출·도구 선택) → MCP 실행 → 2회차(근거 합성 및 `GROUNDED` / `MATCH_NOT_FOUND` / `INSUFFICIENT_PARAMETERS` 판정, `src/agent/reasoning_engine.py`) | 카탈로그에 없는 상품을 임의 추측해 답하거나 필수 조건 누락 시 역질문(`INSUFFICIENT_PARAMETERS`) 없이 답변을 생성하는 행위 금지 |
| **6** | **실데이터(BigQuery · GCS · Vertex AI) 및 디자인 표준 준수** | `src/gcp_client.py`를 통한 실제 GCP 리소스 연동, `DESIGN.md`의 Apple/Google Enterprise 라이트 테마(`#f5f5f7`, Pretendard, 44px+52px 바) 준수 | 샘플 SQLite/인메모리 Mock DB로 실제 BigQuery가 도는 것처럼 위장하거나 다크 테마·장식 이모지를 넣는 행위 금지 |

---

## 2. 상황별 빠른 프로토타이핑 진입점 (`PROTOTYPING_PLAYBOOK.md` 요약)

신규 도메인 프로토타이핑 시 모든 코드를 다 고치지 말고, 아래 **4가지 상황(Scenario A~D)** 중 하나를 선택한 뒤 **교체 대상 5개 지점**만 수정합니다. 상세 가이드와 복사 가능한 프롬프트는 [`PROTOTYPING_PLAYBOOK.md`](PROTOTYPING_PLAYBOOK.md)를 참조하십시오.

| 상황 (Scenario) | 보유 데이터 및 목표 | 선택 트랙 (`active_track`) | 수정할 핵심 파일 (5-File Swap) |
| :--- | :--- | :---: | :--- |
| **Scenario A**<br>비정형 규정·매뉴얼 문서만 있는 경우 | 사내 규정집, SOP, 약관 Markdown/PDF만으로 빠르게 위키 + 규칙 계산 + 에이전트 Q&A 프로토타이핑 | **`lite`**<br>(`Stage 1 → 2 → 4`) | ① `data/input/01_guides/*.md`<br>② `config/starter_config.json` (`"active_track": "lite"`)<br>③ `pipeline/ingest.py` (`DOMAIN_RULES` 규칙 추출부)<br>④ `src/agent/mcp_server.py` (규칙 계산 MCP 1종)<br>⑤ `config/portal_profile.json` (스튜디오 타이틀·시나리오 문구) |
| **Scenario B**<br>정형 DW 테이블 + 비정형 정책 문서를 결합하는 경우 *(기본 권장)* | 마스터/트랜잭션 CSV·BigQuery 테이블과 정책 문서를 결합해 ISO GQL 다중 홉 그래프 추론 + 에이전트 구축 | **`standard`**<br>(`Stage 1 → 2 → 3 → 4`) | ① `data/input/01_guides/*.md` & `03_tables/*.csv`<br>② `config/starter_config.json` (`"active_track": "standard"`, `"graph_engine": "bigquery"`)<br>③ `pipeline/ingest.py` & `pipeline/graph_builder.py` (노드·엣지 DDL)<br>④ `src/agent/mcp_server.py` (런타임 MCP 3종 쿼리)<br>⑤ `config/portal_profile.json` |
| **Scenario C**<br>저지연 운영 트랜잭션 그래프가 필요한 경우 | 실시간 이상거래 탐지(FDS), 설비 인터락 등 밀리초 단위 온라인 그래프 탐색용 DDL 산출 | **`standard`** + Spanner DDL<br>(`Stage 1 → 2 → 3 → 4`) | Scenario B와 동일 + `pipeline/graph_builder.py`의 `create_spanner_graph.sql` 스키마 매핑 (`INTERLEAVE IN PARENT`) |
| **Scenario D**<br>감사 추적·정량 릴리스 게이트까지 검증하는 경우 | 4계층 데이터 리니지 시각화 + Golden CQ 정합성 검증 + 경계값 10건×5회(50회) 벤치마크 통과 후 Cloud Run 배포 | **`full`**<br>(`Stage 1 → 2 → 3 → 4 → 5`) | Scenario B 전체 + `data/input/04_cq/golden_cqs.json` & `boundary_cases.json` + `pipeline/validator.py` + `terraform/terraform.tfvars` |

---

## 3. 런타임 기준값 및 환경 변수

새로운 GCP 프로젝트에 배포할 때는 코드 내부의 상수를 직접 수정하지 말고 환경 변수 또는 `terraform/terraform.tfvars`를 통해 주입합니다.

| 항목 | 환경 변수명 | 기본값 (데모 기준) | 코드 참조 위치 |
| :--- | :--- | :--- | :--- |
| GCP 프로젝트 ID | `GCP_PROJECT_ID` | `seanjung-poc` | `src/gcp_client.py`, `Dockerfile` |
| GCP 리전 | `GCP_LOCATION` | `asia-northeast3` | `src/gcp_client.py`, `Dockerfile` |
| BigQuery 데이터셋 | `BQ_DATASET_ID` | `starter_ontology_dw` | `src/gcp_client.py`, `pipeline/*.py` |
| Property Graph 명칭 | *(코드/설정 상수)* | `STARTER_ONTOLOGY_GRAPH` | `config/starter_config.json`, `pipeline/graph_builder.py` |
| GCS 위키 버킷 | `GCS_BUCKET_NAME` | `seanjung-poc-starter-ontology` | `src/gcp_client.py`, `pipeline/ingest.py` |
| Vertex AI 서빙 모델 | `VERTEX_GEMINI_MODEL` | `gemini-3.8-flash` | `src/gcp_client.py`, `src/agent/reasoning_engine.py` |
| 웹 스튜디오 포트 | `PORT` | `8080` | `src/web/studio_server.py`, `Dockerfile` |

---

## 4. 표준 디렉터리 및 문서 지도

| 경로 | 역할 | 프로토타이핑 시 수정 여부 |
| :--- | :--- | :---: |
| [`01_prod.md`](01_prod.md) | 마스터 제품·아키텍처 헌장 (현재 문서) | 도메인 요약만 갱신 |
| [`PROTOTYPING_PLAYBOOK.md`](PROTOTYPING_PLAYBOOK.md) | 4대 시나리오별 빠른 프로토타이핑 가이드 & 프롬프트 레시피 | 참조용 (수정 불필요) |
| [`GEMINI.md`](GEMINI.md) / [`AGENTS.md`](AGENTS.md) / [`.cursorrules`](.cursorrules) | Jetski·Antigravity·Cursor·Claude Code용 에이전트 부트스트랩 규칙 | 참조용 (수정 불필요) |
| [`DESIGN.md`](DESIGN.md) | Apple/Google Enterprise 라이트 테마 디자인 토큰 및 UI 규칙 | 참조용 (수정 불필요) |
| [`config/starter_config.json`](config/starter_config.json) | 3-Track 활성 단계, 그래프 엔진, MCP 도구 목록 정의 | **수정 (Step 1)** |
| [`config/portal_profile.json`](config/portal_profile.json) | 스튜디오 헤더 타이틀, 도메인 배지, Stage별 설명, 샘플 질의 정의 | **수정 (Step 5)** |
| [`data/input/`](data/input/) | `01_guides/`(문서), `03_tables/`(CSV), `04_cq/`(CQ·경계값), `05_glossary/`(용어사전) | **수정 (Step 2)** |
| [`industry_cases/`](industry_cases/README.md) | 제조·금융·리테일·통신 4대 산업군 8종 비식별 참조 스키마·규칙 템플릿 | 참조·복사원본 |
| [`pipeline/ingest.py`](pipeline/ingest.py) | 마크다운 청킹, 3-Layer 위키 생성, BigQuery 테이블·엣지 적재 | **수정 (Step 3)** |
| [`pipeline/graph_builder.py`](pipeline/graph_builder.py) | BigQuery `CREATE OR REPLACE PROPERTY GRAPH` 및 Spanner DDL 생성·실행 | **수정 (Step 3)** |
| [`src/agent/mcp_server.py`](src/agent/mcp_server.py) | Stage MCP 5종 + 도메인 Runtime MCP 3종 | **수정 (Step 4)** |
| [`src/agent/reasoning_engine.py`](src/agent/reasoning_engine.py) | 2-Pass Gemini 에이전트 (슬롯 추출 → MCP 호출 → 근거 합성) | 카탈로그 슬롯만 조정 |
| [`pipeline/validator.py`](pipeline/validator.py) | Golden CQ 5건 SQL 대조 및 경계값 10건×5회 라이브 벤치마크 | CQ 변경 시 쿼리 조정 |
| [`src/web/studio_server.py`](src/web/studio_server.py) | 6-Tab 통합 웹 스튜디오 서버 (`config/portal_profile.json` 기반 렌더링) | 코어 레이아웃 유지 |
| [`notebooks/ko/`](notebooks/ko/) · [`notebooks/en/`](notebooks/en/) | Stage 0~5 국문(6종) · 영문(6종) 실행형 노트북 및 `nb_helpers.py` | 필요 시 쿼리만 갱신 |
| [`terraform/`](terraform/) | BigQuery, GCS, IAM, Cloud Run 선언적 IaC | `terraform.tfvars`만 수정 |
