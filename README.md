# Agentic Ontology Starter

> **이 스튜디오 + 이 깃헙만 있으면** 내 데이터 · 내 GCP로 엔터프라이즈 온톨로지 에이전트(OKF 위키 · BigQuery Property Graph · Wiki/Graph/Hybrid 에이전트 · CQ 평가)를 만들고, 같은 결과를 다시 만드는 **CLI · MCP 호출 파라미터 · 코드 번들**로 가져가는 스타터 팩입니다.
> 방법론의 핵심 노하우(위키 컴파일 · 그래프 설계 · 에이전트 추론 · 채점)는 **Platform Core MCP 도구** 안에만 있고, 이 저장소는 그 도구를 **어떤 순서로 · 어떤 파라미터로** 부르는지를 담습니다. 서버는 Python 3.11 표준 라이브러리만 씁니다.

| 구분 | 주소 | 설명 |
| :--- | :--- | :--- |
| **스타터 스튜디오** | [agentic-ontology-starter ↗](https://agentic-ontology-starter-115847445822.asia-northeast3.run.app/) | 이해 → 상황 · 목적 → GCP · 권한 → 데이터 → 구축 → 스튜디오 → 코드 인계 |
| **레퍼런스 마법사** | [`/wizard` ↗](https://agentic-ontology-starter-115847445822.asia-northeast3.run.app/wizard#step-1) | 큐레이션된 샘플 결과(Flow A/B/C, 기준 100점) — 비교용 |
| **노트북 랩** | [agentic-ontology-starter-notebook ↗](https://agentic-ontology-starter-notebook-115847445822.asia-northeast3.run.app/) | 같은 방법론을 셀 단위로 배우는 실습 |
| **Platform Core MCP** | `https://aos-builder-core-mcp-115847445822.asia-northeast3.run.app/mcp` | 도구 44종 = 빌드 10 + 데이터 플레인 28 + **노하우 6** · JSON-RPC `tools/list` · `tools/call` |

설계 문서: [`docs/20261019_v1_starter_v5_redesign.md`](docs/20261019_v1_starter_v5_redesign.md)

---

## 1. 흐름 — 5단계 구성 + 스튜디오 + 배포 · 인계

> **v6 (GOAL-243)**: 플로우 · 서비스 카탈로그로 **템플릿 구성**(스타터 샌드박스 또는 내 GCP 프로젝트) → 데이터는 **로컬 업로드 · GCS · Google Drive**, PDF · DOCX · PPTX · XLSX · HTML은 **Markdown 변환 + 변환율 측정** → **문서 유형 자동 판별 + 사용자 확인**(그대로 / 유형별 프롬프팅 / 재변환) → 위키 → **에이전트 바로 테스트** → **배포 단계**(준비도 점검 · 명령). 노하우는 모두 Core MCP(`aos_core_catalog · compose_template · convert_document · classify_documents · deploy_plan`, `drive_*`)에 있고, 구버전 Core MCP면 화면에 `MCP_UPDATE_NEEDED` 안내가 뜹니다(기존 흐름은 그대로 동작).

```text
⓪ 이해      전체 흐름도: 입력 → 수집 · CQ → OKF 위키 → Property Graph → 에이전트 → 평가 (P1 문서 · P3 통합 · P2 테이블)
① 상황·목적  프리셋 + 업무 목적 + 질문 유형 W1/W2/W3 + 플로우(A 문서 · B 테이블 · C 통합 · D 변환 우선) · GCP 서비스 카탈로그
② GCP·권한   템플릿 대상(스타터 샌드박스 · 내 프로젝트) → 템플릿 미리보기(단계 · 서비스 · API · IAM · 스크립트) + 신원 · 리소스 실제 점검
③ 데이터     업로드(.md .txt .csv + .pdf .docx .pptx .xlsx .html, 12MB) · GCS · Google Drive · BigQuery · 샘플 — 변환 결과표(방식 · 변환율 · 페이지 · 미리보기 · PDF)
④ 문서 유형  자동 판별(규칙 + 선택 Gemini) · 확신 낮으면 질문 · 전략(direct · typed · reconvert) 저장 → S3에 유형별 지침 반영
⑤ 구축       S0 준비 → S1 수집 · 프로파일 → S2 CQ → S3 OKF 위키 → S4 Property Graph → S5 평가 (단계별 재실행) → 에이전트 테스트 → 배포 단계
스튜디오     개요 · 자산 · 위키(보기 · 편집 · 게이트) · 그래프(스키마 · GQL/SQL 콘솔 · 설계 편집 → 재구축) · 검색 · 에이전트 실험 · 평가(CQ 편집)
배포        준비도 점검(평가 기준 · CQ · 게이트 · 그래프 · 내 프로젝트 여부) · Cloud Run / MCP 클라이언트 단계별 명령 · Cloud Shell
인계        CLI 재현 명령 · MCP 호출 로그(도구 + 파라미터, curl) · MCP 클라이언트 설정 · 단일 파일 에이전트 · 번들(zip)
```

| 단계 | 하는 일 | Core MCP 호출 |
| :---: | :--- | :--- |
| S0 준비 | 버킷 권한 · 데이터셋 생성(데모 신원이면 테이블 7일 만료) · `workspace.json` | `iam_test_permissions` · `bigquery_get_dataset_info` · `bigquery_create_dataset` · `storage_upload_object` |
| S1 수집 · 프로파일 | 문서 읽기 · CSV → BigQuery(병렬) · BigQuery 테이블 프로파일(복사 없음) · Gate 0 · PK/FK 스코핑 | `storage_read_object` · `bigquery_load_table` · `bigquery_get_table_info` · `bigquery_execute_sql` · `aos_builder_parse_documents_gate0` · **`aos_core_scope`** |
| S2 CQ | 목적 기반 역량 질문 + 기준 답 + 핵심 사실 | **`aos_core_draft_cqs`** |
| S3 OKF 위키 | 요약 · 엔티티 · 개념 + 정책 상수(단일 출처) + applies_to + 게이트 W1~W7 → GCS | **`aos_core_compile_wiki`** · `storage_upload_object` |
| S4 Property Graph | 설계 → 노드 · 엣지 테이블(SQL) → `CREATE PROPERTY GRAPH` → 검증 GQL | **`aos_core_design_graph`** · `bigquery_execute_sql` · `bigquery_load_table` |
| S5 평가 | 모든 CQ를 담당 에이전트로 다시 묻고 채점 | **`aos_core_agent_step`** · 데이터 도구 · **`aos_core_judge`** |

실측(2026-10-19, `gemini-4-argon` MEDIUM): 샘플 팩 KO 구축 약 7분 · 평가 **100 (8/8)** · 업로드한 보험 청구 심사 데이터(문서 1 + CSV 3) 구축 약 6.5분 · 평가 **100 (8/8)**, Property Graph 검증 GQL 전부 통과.

---

## 2. 3개 층 — 무엇이 공개이고 무엇이 보호되나

```text
브라우저 / CLI / 내 코드
  └─ 스타터 (이 저장소: 화면 · 순서 · CLI · 워크스페이스 형식)
       ├─ Platform Core MCP ─ 노하우 aos_core_* (무상태 · 프롬프트 · 규칙 · 게이트)  ← 보호
       │                    └ 데이터 플레인 storage_* · bigquery_* · iam_* (호출자 토큰으로만 실행)
       └─ Vertex AI (상태 점검 · 기본 모델 gemini-4-argon)
  모든 결과물 · Gemini 비용 = 내 GCP (GCS 워크스페이스 · BigQuery 데이터셋 · Property Graph)
```

| 노하우 도구 | 입력 | 출력 |
| :--- | :--- | :--- |
| `aos_core_scope` | 목적 · 문서 머리말 · 테이블 스키마 + 표본 | 데이터 유형 · 질문 유형 · 문서 역할 · PK · FK 후보 · 단계 · 에이전트 |
| `aos_core_draft_cqs` | 목적 · 문서 · 테이블 표본 | CQ(질문 · 유형 · 기준 답 · 핵심 사실) |
| `aos_core_compile_wiki` | 문서 · 테이블 컬럼 (또는 `mode=validate` + 편집한 페이지) | OKF 페이지 · Markdown · 게이트 · 인덱스 |
| `aos_core_design_graph` | 테이블 · 위키 페이지 · 데이터셋 · 그래프 이름 (또는 편집한 `design`) | 검증된 설계 · 실행 SQL · 적재 행 · 그래프 DDL · 검증 GQL · 에이전트 스키마 |
| `aos_core_agent_step` | 에이전트 · 질문 · 컨텍스트 · 관찰 | 다음 행동(`read_wiki` · `gql` · `sql` · `answer`), 계산은 도구 안에서 |
| `aos_core_judge` | 질문 · 기준 답 · 핵심 사실 · 답변 | 판정(1 · 0.5 · 0) |

- 노하우 도구는 데이터를 저장하지 않고, Gemini는 **호출자 토큰 · 호출자 프로젝트**로 실행합니다. Core MCP 서비스 계정에는 데이터 권한이 없습니다.
- 에이전트 루프는 스타터(또는 내 코드)가 돕니다: `agent_step` → 행동 실행(내 신원) → 관찰 전달 → … → `answer`.

---

## 3. 신원 — "특정 권한 SA를 주면"

| 모드 | 동작 | 언제 |
| :--- | :--- | :--- |
| 데모 (`runtime`) | 스타터 서버 신원. 쓰기는 `STARTER_WRITE_PROJECTS`만 | 공개 스튜디오에서 바로 체험 |
| 내 토큰 (`token`) | `gcloud auth print-access-token` 또는 `--impersonate-service-account=SA`로 만든 토큰을 붙여 넣기. 서버는 저장 · 기록하지 않음(브라우저 탭에만 보관) | 공개 스튜디오에서 **내 프로젝트 · 내 SA**로 구축 |
| SA 위임 (`impersonate`) | SA 이메일만 입력 → 서버가 IAM Credentials로 단기 토큰 발급 (`STARTER_IMPERSONATE_ALLOW` 패턴에 맞는 SA만, 런타임 SA에 Token Creator 필요) | 내가 배포한 스타터 |

② 단계의 **설정 스크립트**가 API 활성화 · 버킷 · 전용 SA(`aos-starter@`) · 최소 역할(`bigquery.dataEditor` · `bigquery.jobUser` · `aiplatform.user` · 버킷 `storage.objectAdmin`) · Graph 예약 · 토큰 발급까지 그대로 만들어 줍니다.

---

## 4. 빠른 시작

### 4.1 공개 스튜디오
1. [스튜디오](https://agentic-ontology-starter-115847445822.asia-northeast3.run.app/) → **샘플로 바로 체험** (데모 신원 · 샘플 팩) → **전체 실행**
2. 내 데이터: **내 데이터로 시작** → 목적 입력 → 신원에 토큰(또는 SA 토큰) → 버킷 · 프로젝트 → **환경 점검** → 데이터 업로드 → 구축
3. 스튜디오에서 위키 · 그래프 · 에이전트를 실험하고 **코드 · MCP 인계**에서 번들을 내려받습니다. 워크스페이스는 `?bucket=<버킷>&ws=<ID>` 링크로 다시 열 수 있습니다.

### 4.2 로컬
```bash
git clone https://github.com/seanjungG/agentic-ontology-starter.git && cd agentic-ontology-starter
gcloud auth login
cp .env.example .env   # GCP_PROJECT_ID · GCS_WIKI_BUCKET · STARTER_WRITE_PROJECTS · CORE_MCP_URL
set -a && source .env && set +a
python3 -m src.web.studio_server        # http://localhost:8080
```

### 4.3 CLI (화면 없이 같은 파이프라인)
```bash
python3 -m src.cli check --project MY_PROJECT --bucket MY_BUCKET --region asia-northeast3
python3 -m src.cli new --spec spec.json [--impersonate aos-starter@MY_PROJECT.iam.gserviceaccount.com]   # → ws-YYYYMMDD-xxxxxx
python3 -m src.cli build --bucket MY_BUCKET --ws ws-… [--stages ingest,cqs,wiki,graph,eval]
python3 -m src.cli ask   --bucket MY_BUCKET --ws ws-… --agent hybrid "질문"
python3 -m src.cli eval  --bucket MY_BUCKET --ws ws-…
python3 -m src.cli calls --bucket MY_BUCKET --ws ws-… --stage graph      # MCP 호출 (도구 · 인자 · 상태 · ms)
```
`spec.json` = `{"scenario": {"title", "objective", "question_type"}, "env": {"project", "bucket", "region"}, "sources": {"docs": [{"name", "origin": "gcs", "uri": "gs://…"}], "tables": [{"name", "origin": "gcs|bigquery", "uri"|"fq"}]}, "lang": "ko"}`

### 4.4 내 Cloud Run
```bash
gcloud run deploy agentic-ontology-starter --source . --region asia-northeast3 \
  --service-account aos-starter@MY_PROJECT.iam.gserviceaccount.com --timeout 600 \
  --set-env-vars GCP_PROJECT_ID=MY_PROJECT,BQ_LOCATION=asia-northeast3,GCS_WIKI_BUCKET=MY_BUCKET,STARTER_WRITE_PROJECTS=MY_PROJECT,CORE_MCP_URL=https://aos-builder-core-mcp-115847445822.asia-northeast3.run.app/mcp
```

---

## 5. 워크스페이스 — 결과물의 단위

```text
gs://<버킷>/aos/<ws_id>/
  workspace.json · raw/ · parsed/{docs,tables}.json · cqs.json
  wiki/{01_summary,02_entities,03_concepts}/*.md · wiki/{pages,index,gates}.json
  graph/plan.json · graph/statements.sql · runs/latest.json · mcp_calls.jsonl
BigQuery <프로젝트>.<데이터셋 (기본 aos_<ws>)>
  원천 테이블 · N_<Label> 노드 · E_<LABEL>_<From>_<To> 엣지 · <GRAPH> Property Graph
```
BigQuery Graph는 Enterprise 예약이 필요합니다. 예약이 없으면 그래프 DDL은 실패하지만 노드 · 엣지 테이블은 만들어지고 에이전트는 SQL로 답합니다.

## 6. 코드 · MCP 인계 번들

| 파일 | 용도 |
| :--- | :--- |
| `workspace.json` · `.env` | 같은 리소스로 깃헙 스타터를 실행 |
| `setup_gcp.sh` | GCP 환경 준비 (API · 버킷 · SA · 역할 · 예약 · 토큰) |
| `run_build.sh` · `ask.sh` | CLI로 재구축 · 질문 · 평가 |
| `mcp_calls.jsonl` | 실행한 MCP 호출 순서 그대로 (도구 · 인자 · 상태 · ms) |
| `mcp_config.gemini-cli.json` | MCP 클라이언트에 Core MCP를 도구로 등록하는 예시 (`AOS_ACCESS_TOKEN`) |
| `aos_agent_standalone.py` | 저장소 없이 Core MCP만으로 워크스페이스에 질문하는 단일 파일 에이전트 |

---

## 7. 코드 구조

```text
src/
├── web/studio_server.py   HTTP 서버 · 정적 파일 · /api/v5/* (v5_routes.py) · /wizard · /ucc
├── web/static/            studio.html · studio.js · studio.css · studio_i18n.json(KO·EN) · flows_v5.js (+ 레퍼런스 마법사 index.html · app.js)
├── aos/ws.py              워크스페이스 · GCS 영속화 · MCP 호출 로그
├── aos/sources.py         업로드 · GCS · BigQuery · 샘플 팩 · CSV 스키마 추론
├── aos/pipeline.py        구축 단계 S0~S5
├── aos/agent.py           Wiki · Graph · Hybrid 에이전트 루프 (추론 = aos_core_agent_step)
├── aos/studio.py          프리셋 · 환경 점검 · 설정 스크립트 · 편집 · 쿼리 · 검색 · 번들
├── identity.py            요청 단위 신원 (runtime · token · impersonate)
├── cli.py                 CLI
└── (레퍼런스 마법사) config · recipes · datapack · loader · evaluation · agent/
data/ · config/ · notebooks/(Colab 12종) · tests/ · docs/
```

## 8. 환경 변수

| 변수 | 기본값 | 설명 |
| :--- | :--- | :--- |
| `GCP_PROJECT_ID` · `BQ_LOCATION` · `GCS_WIKI_BUCKET` | — · `asia-northeast3` · — | 기본 리소스 (② 단계 기본값) |
| `VERTEX_GEMINI_MODEL` · `VERTEX_LOCATION` | `gemini-4-argon` · `global` | Gemini 모델 |
| `CORE_MCP_URL` | Core MCP `/mcp` | Platform Core MCP (요청으로 바꿀 수 없음) |
| `STARTER_WRITE_PROJECTS` | `GCP_PROJECT_ID` | 데모 신원이 쓸 수 있는 프로젝트 (`*` = 모두). 사용자 신원에는 적용 안 함 |
| `STARTER_IMPERSONATE_ALLOW` | (비어 있음 = 끔) | 서버 측 SA 위임을 허용할 SA 패턴 (예: `*@my-project.iam.gserviceaccount.com`) |
| `AOS_CORE_MCP_FALLBACK` | `strict` | `direct`면 Core MCP 장애 시 직접 API 우회 (개발용) |
| `PORT` | `8080` | HTTP 포트 |

## 9. 테스트
```bash
python3 -m pip install pytest && python3 -m pytest tests -q
```
v5 셸 · KO/EN 문구 동등성(EN 한글 0) · 워크스페이스 · 환경 검증 · CSV 추론 · 쿼리 가드 · 신원 오류(네트워크 호출 전 401) + 레퍼런스 마법사 테스트. GCP 호출이 없는 테스트만 들어 있습니다.

---

## English summary

**Agentic Ontology Starter** lets anyone with **this studio and this repository** build an enterprise ontology agent on **their own data and their own GCP** — OKF wiki, BigQuery Property Graph, Wiki / Graph / Hybrid agents and a CQ evaluation — and take the result away as a **CLI, MCP call parameters and a code bundle**. The core method know-how (wiki compile, graph design, agent reasoning, grading) lives only in the **Platform Core MCP `aos_core_*` tools**; this repository holds which tools are called in which order with which parameters.

- **Flow**: understand → situation & goal (presets or custom, W1/W2/W3) → GCP & permissions (demo identity, pasted token, or SA; live checks + a ready-to-run setup script) → data (upload .md/.txt/.csv, GCS paths, BigQuery tables, sample pack) → build S0–S5 (re-run any stage) → studio (assets, wiki edit + gates, graph schema + GQL/SQL console + design rebuild, search, agent experiments, CQ evaluation) → hand-off (CLI, MCP call log with curl, MCP client config, single-file agent, zip bundle).
- **v6 intake** (GOAL-243): pick a flow and services from the Core MCP catalog and compose a template for the starter sandbox or your own project; bring data from local upload, GCS or Google Drive — PDF/DOCX/PPTX/XLSX/HTML are converted to Markdown with a fidelity score; Core MCP detects each document's type (and asks when unsure) and the chosen wiki strategy (direct · typed · re-convert) feeds the wiki compile; then test the agent and open the deployment page (readiness checks + commands). An older Core MCP shows `MCP_UPDATE_NEEDED` while the existing flow keeps working.
- **Measured** (2026-10-19, `gemini-4-argon` MEDIUM): sample pack ~7 min build, eval **100 (8/8)**; an uploaded insurance-claims data set (1 doc + 3 CSVs) ~6.5 min, eval **100 (8/8)**.
- **Security**: the Core MCP is zero-privilege; data tools and Gemini run with the caller's token in the caller's project. Pasted tokens are never stored. Demo writes are limited to `STARTER_WRITE_PROJECTS`; server-side SA impersonation only for `STARTER_IMPERSONATE_ALLOW`.
- **Quick start**: `python3 -m src.web.studio_server` (local) · `python3 -m src.cli build --bucket … --ws …` (CLI) · `gcloud run deploy … --source .` (your Cloud Run). The curated reference wizard stays at `/wizard`.

## License

Methodology and documents: CC BY-NC-ND 4.0 · Source code: PolyForm Noncommercial License 1.0.0 — see [`LICENSE`](LICENSE). Commercial use requires prior written permission.
