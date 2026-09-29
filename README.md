# Agentic Ontology Starter

[![Methodology License: CC BY-NC-ND 4.0](https://img.shields.io/badge/Methodology_%26_Docs-CC_BY--NC--ND_4.0-b91c1c)](./LICENSE)
[![Code License: PolyForm Noncommercial 1.0.0](https://img.shields.io/badge/Code_License-PolyForm_Noncommercial_1.0.0-dc2626)](./LICENSE)
[![Commercial Inquiry: seanjung@google.com](https://img.shields.io/badge/Commercial_Inquiry-seanjung%40google.com-0284c7)](mailto:seanjung@google.com)

> **비영리 라이선스 및 방법론 지식재산권 고지 (Non-Commercial License Notice)**:
> 본 저장소의 핵심인 **5-Stage 에이전틱 온톨로지 엔지니어링 방법론(`methodology/`)·실습 노트북(`notebooks/`)·산업군 아키텍처 템플릿(`industry_cases/`)**은 **CC BY-NC-ND 4.0**으로, **소스 코드(`src/`, `pipeline/`, `terraform/`)**는 **PolyForm Noncommercial 1.0.0**으로 보호됩니다. 개인 학습 및 비상업적 기술 검증 외에 **상용 서비스 탑재, 타 기업/고객사 대상 유상 컨설팅·SI·PoC 딜리버리 활용을 엄격히 금지**하며, 상업적/엔터프라이즈 활용이 필요한 경우 반드시 **[seanjung@google.com](mailto:seanjung@google.com)**으로 사전 논의하시기 바랍니다. ([상세 라이선스 안내 (KO / EN)](#5-라이선스-및-상업적-이용-제한-안내--license--commercial-use-restriction-ko--en) · [`LICENSE`](./LICENSE))

정형 데이터(BigQuery DW)와 비정형 정책 문서(업무 가이드·약관·SOP)를 **3-Layer 위키(OKF v0.2)**와 **BigQuery Property Graph(ISO SQL:2023 GQL)**로 결합하고, **8종 MCP 도구**와 **Vertex AI Gemini 에이전트(`gemini-3.8-flash`)**로 검증·서빙하는 **5-Stage 엔터프라이즈 온톨로지 스타터 팩**입니다.

- **라이브 스튜디오 (Cloud Run)**: [https://agentic-ontology-starter-lwrlf7yogq-du.a.run.app](https://agentic-ontology-starter-lwrlf7yogq-du.a.run.app)
- **빠른 프로토타이핑 & AI 에이전트 부트스트랩 문서**:
  - [**상황별 빠른 프로토타이핑 플레이북 (`PROTOTYPING_PLAYBOOK.md`)**](./PROTOTYPING_PLAYBOOK.md) — 4대 데이터 상황별 5-File Swap 레시피
  - [**마스터 제품·아키텍처 헌장 (`01_prod.md`)**](./01_prod.md) · [**UI 디자인 표준 (`DESIGN.md`)**](./DESIGN.md)
  - **툴별 에이전트 가드레일**: [**Antigravity (`GEMINI.md`)**](./GEMINI.md) · [**Cursor (`.cursorrules`)**](./.cursorrules) · [**Claude Code (`CLAUDE.md` / `AGENTS.md`)**](./CLAUDE.md)
  - [**4대 산업군 8종 비식별 레퍼런스 템플릿 (`industry_cases/README.md`)**](./industry_cases/README.md) — 제조 · 금융 · 리테일 · 통신 스키마/규칙/CQ 샘플
- **방법론 마스터 가이드**: [한국어 (`METHODOLOGY_KO.md`)](./methodology/ko/METHODOLOGY_KO.md) · [English (`METHODOLOGY_EN.md`)](./methodology/en/METHODOLOGY_EN.md)
- **실행형 Jupyter 노트북 (12종 · `ko/` 국문 6종 + `en/` 영문 6종 분리)**: [노트북 허브 (`notebooks/README.md`)](./notebooks/README.md) · [전체 흐름 초기 노트북 (`ko/`)](./notebooks/ko/stage0_overview_walkthrough_ko.ipynb) · [English Overview Notebook (`en/`)](./notebooks/en/stage0_overview_walkthrough_en.ipynb)

---

## 1. AI 코딩 툴(Antigravity · Cursor · Claude Code) 명령 및 수행 요청 가이드

이 스타터팩을 클론하여 새로운 프로젝트(제조·금융·리테일·통신·사내 규정 등)를 시작할 때, 에이전트에게 막연히 *"온톨로지 만들어줘"*라고 지시하면 에이전트가 임의로 디렉터리 구조를 바꾸거나 Mock SQLite·다크 테마 화면을 새로 작성할 수 있습니다.

이를 방지하기 위해 저장소 루트에 **[`01_prod.md`](./01_prod.md), [`GEMINI.md`](./GEMINI.md), [`CLAUDE.md`](./CLAUDE.md), [`.cursorrules`](./.cursorrules), [`PROTOTYPING_PLAYBOOK.md`](./PROTOTYPING_PLAYBOOK.md)**가 내장되어 있습니다. 아래 **툴별 호출 방식**과 **3단계(환경 셋팅 → 데이터 인입 → 온톨로지·에이전트 구축) 프롬프트**를 그대로 복사해 명령하십시오.

### 1.1 코딩 툴별 권장 호출 방식

| 코딩 툴 | 자동 로드되는 규칙 파일 | 명령 시 권장 컨텍스트 멘션 & 슬래시 커맨드 | 특징 및 팁 |
| :--- | :--- | :--- | :--- |
| **Antigravity (Jetski)** | `GEMINI.md`, `01_prod.md` | 프롬프트 첫 줄에 `@01_prod.md @GEMINI.md @PROTOTYPING_PLAYBOOK.md` 멘션 후 끝에 **`/goal`** (자율 완결 실행) 또는 **`/grill-me`** (사전 설계 인터뷰) 부착 | `00_dashboard.md`에 단계별(WP1~WPn) 진행 현황을 기록하며, 권한/인증 블로커 발생 시 `backlog.md`에 분리 기록 |
| **Cursor** | `.cursorrules` | Composer(`Cmd+I` / `Ctrl+I`) 또는 Chat에서 `@01_prod.md @PROTOTYPING_PLAYBOOK.md @DESIGN.md`를 태그하여 지시 | `.cursorrules`가 6-Tab 라이트 테마 UI(`studio_server.py`)와 5-File Swap 규칙을 강제함 |
| **Claude Code** | `CLAUDE.md`, `AGENTS.md` | 터미널에서 `claude` 실행 후 `"01_prod.md와 PROTOTYPING_PLAYBOOK.md를 읽고 Step 1부터 순서대로 수행해줘"`라고 지시 | `CLAUDE.md`를 자동 인식하여 Mock DB 생성 없이 실제 BigQuery·GCS·Vertex AI 파이프라인을 실행함 |

---

### 1.2 단계별 수행 요청 프롬프트 (Step 1: 환경 셋팅 → Step 2: 데이터 인입 → Step 3: 온톨로지 구축)

새 프로젝트 폴더에서 스타터팩을 연 뒤, 아래 **Step 1 → Step 2 → Step 3** 순서로 요청하거나 **1.3의 상황별 원샷 프롬프트**로 한 번에 요청할 수 있습니다.

#### [Step 1 명령] GCP 환경 셋팅 및 리소스 프로비저닝 요청
> **언제 쓰는가**: 프로젝트를 처음 클론한 직후, 내 GCP 프로젝트/데이터셋/버킷 환경변수를 맞추고 BigQuery·GCS 연결이 정상인지 검증할 때.

```text
@01_prod.md @GEMINI.md @PROTOTYPING_PLAYBOOK.md 를 읽고 Step 1 환경 셋팅을 수행해줘.
1. 내 GCP 환경 정보는 다음과 같아:
   - GCP_PROJECT_ID: "[내-GCP-프로젝트-ID]"
   - GCP_LOCATION: "asia-northeast3"
   - BQ_DATASET_ID: "[내-BigQuery-데이터셋명, 예: my_ontology_dw]"
   - GCS_BUCKET_NAME: "[내-GCS-버킷명]"
   - VERTEX_GEMINI_MODEL: "gemini-3.8-flash"
2. 현재 gcloud / ADC 인증 상태와 BigQuery 데이터셋·GCS 버킷 접근 권한을 먼저 점검해줘. (권한 부족이나 미생성 리소스가 있으면 임의로 Mock DB를 만들지 말고 terraform/terraform.tfvars 설정 또는 필요한 gcloud 명령어를 안내해줘.)
3. 기본 샘플 데이터로 python3 pipeline/ingest.py 와 python3 pipeline/graph_builder.py 가 정상 동작하는지 먼저 스모크 테스트해줘. /goal
```

#### [Step 2 명령] 내 도메인 데이터 인입 (Stage 1 Asset & Stage 2 3-Layer Wiki 구축) 요청
> **언제 쓰는가**: 내가 준비한 정책/매뉴얼 문서(MD/PDF 텍스트)와 정형 테이블(CSV 또는 기존 BigQuery 테이블)을 넣어서 **Stage 1(자산 등록·CQ 정의) ~ Stage 2(문단 청킹·SHA-256 해시·3-Layer OKF 위키·도메인 규칙 테이블 적재)**까지 수행할 때.

```text
@01_prod.md @GEMINI.md @PROTOTYPING_PLAYBOOK.md 를 준수해서 내 도메인 데이터를 인입(Stage 1 ~ Stage 2)해줘.
코어 프레임워크는 절대 재작성하지 말고 아래 데이터에 맞춰 인입 파이프라인만 교체해줘:
1. 도메인 개요: [예: 사내 구매/계약 승인 규정 / 스마트팩토리 설비 보전 SOP / 금융 대출 심사 규정]
   (유사한 구조가 필요하면 industry_cases/ 하위 템플릿을 참고해줘.)
2. 입력 데이터 구성 (data/input/):
   - 비정형 가이드 문서(01_guides/): [내가 넣은 마크다운/문서 파일 경로 또는 생성할 도메인 규정 설명]
   - 정형 마스터/트랜잭션 테이블(03_tables/): [내가 넣은 CSV 파일 경로 또는 스키마 설명]
   - 핵심 검증 질문(04_cq/golden_cqs.json 5건, boundary_cases.json 10건)과 용어사전(05_glossary/business_glossary.json)도 이 도메인에 맞게 구성해줘.
3. pipeline/ingest.py 의 테이블 적재 목록, DOMAIN_RULES(핵심 판정/계산 규칙), compile_3layer_wiki() 요약을 이 도메인에 맞게 수정하고, 실제로 python3 pipeline/ingest.py 를 실행해서 data/llm_wiki/*.md 와 BigQuery 테이블(tb_doc_chunks, tb_domain_rules 및 마스터 테이블)에 적재된 행 수를 확인해줘. /goal
```

#### [Step 3 명령] 온톨로지 Property Graph 구축 · MCP 에이전트 연결 · 6-Tab 스튜디오 구동 요청
> **언제 쓰는가**: Step 2에서 인입된 테이블과 위키 위에 **Stage 3(BigQuery/Spanner Property Graph DDL) → Stage 4(런타임 MCP 3종 & 2-Pass 에이전트) → Stage 5(Golden CQ·경계값 검증 및 6-Tab 웹 스튜디오)**를 완성할 때.

```text
@01_prod.md @GEMINI.md @PROTOTYPING_PLAYBOOK.md @DESIGN.md 를 준수해서 Stage 3 ~ Stage 5 온톨로지 그래프와 에이전트 구축을 마무리해줘.
1. [Stage 3 그래프 구축]: pipeline/graph_builder.py 에서 Step 2에 적재한 노드 테이블과 브릿지 엣지 테이블을 연결하도록 CREATE OR REPLACE PROPERTY GRAPH DDL을 업데이트하고, python3 pipeline/graph_builder.py 를 실행해 실제 BigQuery Property Graph를 생성해줘.
2. [Stage 4 MCP & 에이전트 연결]: src/agent/mcp_server.py 의 Stage MCP 5종 인터페이스는 그대로 유지하고, Runtime MCP 3종(프로필/원장 조회, 결정론적 규칙/수식 계산, GQL 그래프+위키 검색)과 src/agent/reasoning_engine.py 의 카탈로그 슬롯 파싱을 우리 도메인 테이블에 맞게 연결해줘.
3. [Stage 5 검증 & 스튜디오 프로필]: pipeline/validator.py 의 Golden CQ 검증 SQL을 맞추고 실행한 뒤, config/portal_profile.json 의 도메인 타이틀·Stage 설명·샘플 질의를 업데이트해서 python3 -m src.web.studio_server 8080 으로 6-Tab 스튜디오가 정상 구동되는지 검증해줘. /goal
```

---

### 1.3 내 데이터 상황에 맞는 시나리오 선택 & 원샷 프로토타이핑 명령 (`PROTOTYPING_PLAYBOOK.md` 요약)

보유한 데이터 상황에 따라 **4가지 시나리오(Scenario A~D)** 중 하나를 골라 에이전트에게 한 번에 지시할 수도 있습니다. (상세 설명은 [**`PROTOTYPING_PLAYBOOK.md`**](./PROTOTYPING_PLAYBOOK.md) 참조)

| 시나리오 | 보유 데이터 및 목표 | 설정 트랙 (`starter_config.json`) | 실행 Stage | 교체 대상 (`5-File Swap`) |
| :--- | :--- | :---: | :---: | :--- |
| **Scenario A · 문서 전용 퀵스타트** | 정형 DW 테이블 없이 **업무 규정·약관·매뉴얼 문서(MD)**와 계산 규칙만으로 위키 + 에이전트 Q&A 구축 | `lite` | `Stage 1 → 2 → 4` | `data/input/01_guides/*`, `starter_config.json`, `pipeline/ingest.py`, `mcp_server.py`, `portal_profile.json` |
| **Scenario B · DW + 문서 하이브리드** *(기본 권장)* | **마스터/트랜잭션 CSV(DW 테이블) + 정책 문서**를 결합해 **BigQuery Property Graph(`ISO GQL`) 다중 홉 추론** 수행 | `standard` (`bigquery`) | `Stage 1 → 2 → 3 → 4` | `data/input/*`, `starter_config.json`, `ingest.py` + `graph_builder.py`, `mcp_server.py`, `portal_profile.json` |
| **Scenario C · 저지연 운영 그래프 확장** | Scenario B + 실시간 이상거래(FDS)/설비 인터락용 **Cloud Spanner Graph DDL(`INTERLEAVE`)** 동시 생성 | `standard` (`bigquery` + Spanner DDL) | `Stage 1 → 2 → 3 → 4` | Scenario B + `pipeline/graph_builder.py` (`create_spanner_graph.sql`) |
| **Scenario D · 감사 리니지 & 배포 게이트** | **4계층 리니지 시각화 + Golden CQ 5건 + 경계값 50회 라이브 평가 게이트** 통과 및 Cloud Run 배포 | `full` | `Stage 1 → 2 → 3 → 4 → 5` | Scenario B + `data/input/04_cq/*`, `pipeline/validator.py`, `terraform/terraform.tfvars` |

```text
# [원샷 프로토타이핑 명령 예시 — Antigravity / Cursor / Claude Code에 그대로 복사해 입력]
@01_prod.md @GEMINI.md @PROTOTYPING_PLAYBOOK.md @DESIGN.md 를 먼저 읽고 준수해줘.
우리 프로젝트를 [Scenario B: Track 2 Standard (정형 DW + 비정형 문서 BigQuery Property Graph 통합)] 방식으로 프로토타이핑하려고 해.
대상 도메인은 [내 도메인 설명 또는 industry_cases/ 하위 템플릿명]이고, 기존 6-Tab 라이트 스튜디오(src/web/studio_server.py) 레이아웃은 절대 바꾸지 마.
PROTOTYPING_PLAYBOOK.md의 5-File Swap 절차에 따라:
1) data/input/ 데이터 구성 ➔ 2) pipeline/ingest.py 실행(3-Layer 위키 & BQ 테이블 적재) ➔ 3) pipeline/graph_builder.py 실행(BigQuery Property Graph 생성) ➔ 4) src/agent/mcp_server.py 런타임 MCP 3종 및 reasoning_engine.py 슬롯 연결 ➔ 5) config/portal_profile.json 및 pipeline/validator.py 검증까지 순서대로 수행하고 실측 결과를 보고해줘. /goal
```

---

## 2. 8단계 엔지니어링 흐름 & 5-Stage · 스튜디오 · 방법론 · 한/영 노트북 통합 지도

전체 과정은 **1. 준비(Prepare) → 2. 분석(Analyze) → 3. 파싱(Parse) → 4. 통합(Integrate) → 5. 구축(Build Graph) → 6. 에이전트 구축(Build Agent) → 7. 답변(Answer & GQL) → 8. 검증(Verify & Gate)**의 8단계 엔지니어링 흐름을 따라 진행되며, 각 단계마다 파이프라인 실행 코드, 중간 테이블/데이터 확인(`%%bqsql`), 바인딩 변수·실행 GQL 문장(`H.run_gql`), 그래프 설계 도식이 함께 제공됩니다.

| 8단계 엔지니어링 흐름 | 정본 Stage | 핵심 구현 및 중간 데이터/그래프 확인 | 라이브 스튜디오 탭 | 방법론 가이드 (KO / EN) | 실습 노트북 (`ko/` / `en/`) |
| :--- | :---: | :--- | :--- | :---: | :---: |
| **0. 전체 흐름 초기 화면**<br>*(End-to-End Tour)* | **0. Overview** | 8단계 파이프라인 흐름도, 10개 테이블 스키마 블루프린트, Stage 1~5 MCP 실행, 시맨틱/물리 그래프 토폴로지, 바인딩 변수 기반 3-Hop GQL & 에이전트 추론, Gate 1~5 판정 | [`0. Overview`](https://agentic-ontology-starter-lwrlf7yogq-du.a.run.app/?tab=overview) | [KO](./methodology/ko/METHODOLOGY_KO.md) · [EN](./methodology/en/METHODOLOGY_EN.md) | [KO](./notebooks/ko/stage0_overview_walkthrough_ko.ipynb) · [EN](./notebooks/en/stage0_overview_walkthrough_en.ipynb) |
| **1. 준비 (Prepare)**<br>**2. 분석 (Analyze)** | **Stage 1** | 원시 CSV/MD 인벤토리, `INFORMATION_SCHEMA` 스키마 설계도, `mcp_stage1_asset_discovery` 비식별화 검증, 약정·단말·요금제·지원금 히트맵, Golden CQ 5종 SQL 검증 | [`Stage 1. Asset`](https://agentic-ontology-starter-lwrlf7yogq-du.a.run.app/?tab=stage1) | [KO](./methodology/ko/01_stage1_asset_and_cq_ko.md) · [EN](./methodology/en/01_stage1_asset_and_cq_en.md) | [KO](./notebooks/ko/stage1_asset_and_cq_ko.ipynb) · [EN](./notebooks/en/stage1_asset_and_cq_en.ipynb) |
| **3. 파싱 (Parse)**<br>**4. 통합 (Integrate)** | **Stage 2** | `pipeline/ingest.py` 정규식 청킹 & SHA-256 해시 앵커 대조, 3-Layer Wiki(`summary`, `entities`, `concepts`, `rules`) 컴파일, Gemini 트리플 추출, 시맨틱 그래프 도식 | [`Stage 2. Wiki & Semantic Graph`](https://agentic-ontology-starter-lwrlf7yogq-du.a.run.app/?tab=stage2) | [KO](./methodology/ko/02_stage2_wiki_and_semantic_graph_ko.md) · [EN](./methodology/en/02_stage2_wiki_and_semantic_graph_en.md) | [KO](./notebooks/ko/stage2_wiki_and_semantic_graph_ko.ipynb) · [EN](./notebooks/en/stage2_wiki_and_semantic_graph_en.ipynb) |
| **5. 구축 (Build Graph)** | **Stage 3** | 6 Node × 4 Edge 메타모델 설계도, BigQuery/Spanner Graph DDL(`pipeline/graph_builder.py`), 5계층 토폴로지 & 1~2홉 서브그래프, 바인딩 변수·ISO GQL 문장(`GQL-01~05`) & `nl2gql` | [`Stage 3. Property Graph`](https://agentic-ontology-starter-lwrlf7yogq-du.a.run.app/?tab=stage3) | [KO](./methodology/ko/03_stage3_property_graph_ko.md) · [EN](./methodology/en/03_stage3_property_graph_en.md) | [KO](./notebooks/ko/stage3_property_graph_bigquery_spanner_ko.ipynb) · [EN](./notebooks/en/stage3_property_graph_bigquery_spanner_en.ipynb) |
| **6. 에이전트 구축 (Agent)**<br>**7. 답변 (Answer)** | **Stage 4** | 2-Pass 에이전트 & 8종 MCP 설계도, 카탈로그 슬롯 파싱(`resolve_params`), 런타임 MCP GQL/SQL 실행, 180일 위약금 곡선, Golden CQ(`GROUNDED`) & 경계(`INSUFFICIENT`, `NOT_FOUND`) 답변 | [`Stage 4. Agent & MCP`](https://agentic-ontology-starter-lwrlf7yogq-du.a.run.app/?tab=stage4) | [KO](./methodology/ko/04_stage4_agent_and_mcp_ko.md) · [EN](./methodology/en/04_stage4_agent_and_mcp_en.md) | [KO](./notebooks/ko/stage4_agent_and_mcp_execution_ko.ipynb) · [EN](./notebooks/en/stage4_agent_and_mcp_execution_en.ipynb) |
| **8. 검증 (Verify & Gate)** | **Stage 5** | 4-Tier 데이터 리니지(`Source File → DocChunk → DomainRule → Contract → CQ`) 멀티파타이트 도식, `pipeline/validator.py` 실시간 CQ 재검증, Boundary 50회 평가 & Gate 1~5 | [`Stage 5. Lineage & Eval`](https://agentic-ontology-starter-lwrlf7yogq-du.a.run.app/?tab=stage5) | [KO](./methodology/ko/05_stage5_lineage_and_eval_ko.md) · [EN](./methodology/en/05_stage5_lineage_and_eval_en.md) | [KO](./notebooks/ko/stage5_lineage_and_evaluation_ko.ipynb) · [EN](./notebooks/en/stage5_lineage_and_evaluation_en.ipynb) |

---

## 3. 터미널 수동 실행 가이드 (3분 Quickstart)

AI 코딩 에이전트 없이 터미널에서 직접 기본 데모 파이프라인을 실행하려면 아래 순서대로 명령어를 입력합니다.

### 3.1 사전 요구사항 및 인증

```bash
gcloud auth login
gcloud auth application-default login
export GCP_PROJECT_ID="seanjung-poc"
export GCP_LOCATION="asia-northeast3"
export BQ_DATASET_ID="starter_ontology_dw"
export GCS_BUCKET_NAME="seanjung-poc-starter-ontology"
export VERTEX_GEMINI_MODEL="gemini-3.8-flash"
```

### 3.2 엔드투엔드 파이프라인 및 평가 실행

```bash
# 1. Stage 1~2: 샘플 가이드·CSV 파싱 → 3-Layer 위키 컴파일 → BigQuery 10개 테이블 적재 및 GCS 업로드
python3 pipeline/ingest.py

# 2. Stage 3: BigQuery Property Graph (STARTER_ONTOLOGY_GRAPH) & Spanner Graph DDL 합성 및 프로비저닝
python3 pipeline/graph_builder.py

# 3. Stage 5: Golden CQ 5건 검증 및 경계값 10건×5회(50회) 라이브 벤치마크 실행
python3 pipeline/validator.py

# 4. 6-Tab 통합 웹 스튜디오 로컬 실행 (http://127.0.0.1:8080)
python3 -m src.web.studio_server 8080
```

### 3.3 Terraform(IaC) 기반 GCP 프로비저닝 및 Cloud Run 배포

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
terraform init
terraform apply
```

---

## 4. 디렉터리 구조

```text
agentic-ontology-starter/
├── LICENSE                          # 비영리 듀얼 라이선스 (방법론 CC BY-NC-ND 4.0 + 코드 PolyForm NC 1.0)
├── 01_prod.md                       # 마스터 제품·아키텍처 헌장 (AI 에이전트 & 엔지니어 최상위 기준)
├── PROTOTYPING_PLAYBOOK.md          # 4대 상황별 빠른 프로토타이핑 레시피 & 에이전트 프롬프트
├── GEMINI.md / CLAUDE.md / AGENTS.md / .cursorrules # Antigravity · Cursor · Claude Code 자동 로드 가드레일
├── DESIGN.md                        # Apple/Google Enterprise 라이트 테마 UI 디자인 표준
├── config/
│   ├── starter_config.json          # 3-Track 설정, 그래프 엔진, MCP 8종 정의
│   └── portal_profile.json          # 스튜디오 프로필 및 산업군 쇼케이스(Telecom/Retail/Finance/Manufacturing)
├── data/
│   ├── input/                       # Stage 1 입력: 01_guides(2), 03_tables(CSV 6), 04_cq(CQ 5, 경계값 10), 05_glossary
│   ├── llm_wiki/                    # Stage 2 산출물: 3-Layer OKF 위키 (summary.md, entities.md, concepts.md, rules.md)
│   └── output/                      # Stage 2~5 산출물: ontology.jsonld, BQ/Spanner Graph DDL, 평가 리포트 JSON
├── industry_cases/                  # 4대 산업군(제조·금융·리테일·통신) 8종 비식별 참조 아키텍처 및 데이터 템플릿
├── methodology/                     # 5-Stage 방법론 마스터(KO/EN) 및 Stage 1~5 한/영 상세 가이드 (13개 파일)
├── notebooks/                       # 8단계 흐름 기반 한/영 실습 노트북 12종(ko/ 6종, en/ 6종) + nb_helpers.py
├── pipeline/
│   ├── ingest.py                    # Stage 1~2 데이터 파싱·위키 컴파일·BigQuery/GCS 적재 파이프라인
│   ├── graph_builder.py             # Stage 3 BigQuery/Spanner Property Graph DDL 합성 및 배포
│   └── validator.py                 # Stage 5 Golden CQ 5건 검증 및 경계값 10건×5회 반복 평가 엔진
├── src/
│   ├── gcp_client.py                # BigQuery REST/GQL, GCS 업로드, Vertex AI Gemini 호출 클라이언트
│   ├── agent/mcp_server.py          # Stage MCP 5종 + Runtime MCP 3종 (총 8종)
│   ├── agent/reasoning_engine.py    # 2-패스 Gemini 목표 분해 · MCP 호출 · 근거 합성 에이전트 엔진
│   └── web/studio_server.py         # 6-Tab Agentic Ontology Studio 웹 서버
├── terraform/                       # BigQuery, GCS, IAM, Cloud Build + Cloud Run 선언적 IaC
└── Dockerfile                       # Cloud Run 컨테이너 이미지 정의
```

---

## 5. 라이선스 및 상업적 이용 제한 안내 / License & Commercial Use Restriction (KO / EN)

### [한국어 안내 — KOREAN]

본 저장소의 핵심 자산인 **5-Stage 에이전틱 온톨로지 엔지니어링 방법론(8단계 엔지니어링 흐름 · 3-Layer OKF 위키 · 듀얼 Property Graph 아키텍처 · 8종 MCP 및 2-Pass 에이전트 오케스트레이션 · 4-Tier 리니지 및 경계값 평가 체계)**과 관련 문서(`methodology/`), 실습 노트북(`notebooks/`), 산업군 아키텍처 템플릿(`industry_cases/`), 그리고 전체 소스 코드(`src/`, `pipeline/`, `terraform/`)는 **비영리 듀얼 라이선스([`LICENSE`](./LICENSE))**로 보호됩니다.

- **적용 라이선스**:
  - **핵심 방법론 · 아키텍처 설계 · 문서 · 노트북 (`methodology/`, `notebooks/`, `industry_cases/`, `*.md`)**: **CC BY-NC-ND 4.0** (저작자표시-비영리-변경금지 4.0 국제 라이선스)
  - **레퍼런스 소스 코드 (`src/`, `pipeline/`, `terraform/`, `*.py`, `*.sql`, `*.tf`)**: **PolyForm Noncommercial License 1.0.0**
- **허용 범위 (Permitted)**: 개인 학습, 학술 연구, 비상업적 목적의 자체 기술 검증(Non-commercial Evaluation)
- **사전 승인 없이 엄격히 금지되는 행위 (Strictly Prohibited)**:
  1. 본 저장소의 **5-Stage 온톨로지 방법론, 산출물 체계(D1.1~D5.5), 아키텍처 설계도, 노트북 또는 소스 코드**를 타 기업·기관 대상 **유상 컨설팅, SI 구축, 유상 PoC/파일럿 딜리버리, 상업적 제안서 또는 고객사 납품 산출물**로 활용하는 행위
  2. 상용 제품, 유료 클라우드/SaaS 서비스, 또는 영리 목적의 프로덕션 시스템에 탑재·운영하는 행위
  3. 본 방법론이나 노트북·코드를 개작·재가공하여 유료 강의, 교육 과정, 상업적 출판물로 판매·배포하는 행위
- **상업적 활용 및 엔터프라이즈 프로젝트 적용 문의**:
  고객사 딜리버리 프로젝트(PoC/SI/컨설팅) 적용이나 상업적 사용이 필요한 경우 반드시 사전에 **[seanjung@google.com](mailto:seanjung@google.com)**으로 논의하시기 바랍니다.

---

### [ENGLISH NOTICE]

The core intellectual asset of this repository — the **5-Stage Agentic Ontology Engineering Methodology** (8-Phase Engineering Flow, 3-Layer OKF Wiki Architecture, Dual Property Graph Design, 8-Tool Modular MCP & 2-Pass Agent Orchestration, and 4-Tier Lineage & Boundary Evaluation Framework) — along with all methodology guides (`methodology/`), executable notebooks (`notebooks/`), industry reference templates (`industry_cases/`), and reference source code (`src/`, `pipeline/`, `terraform/`), is protected under a **Non-Commercial Dual License ([`LICENSE`](./LICENSE))**.

- **Applicable Licenses**:
  - **Core Methodology, Architecture Designs, Documentation & Notebooks (`methodology/`, `notebooks/`, `industry_cases/`, `*.md`)**: **Creative Commons Attribution-NonCommercial-NoDerivatives 4.0 International (CC BY-NC-ND 4.0)**
  - **Reference Source Code (`src/`, `pipeline/`, `terraform/`, `*.py`, `*.sql`, `*.tf`)**: **PolyForm Noncommercial License 1.0.0**
- **Permitted Use**: Personal learning, academic research, and non-commercial internal technical evaluation.
- **Strictly Prohibited Without Prior Written Permission**:
  1. Using the **5-Stage Ontology Methodology, deliverable specifications (D1.1–D5.5), architecture diagrams, notebooks, or source code** in any **paid consulting, system integration (SI) delivery, paid PoC/pilot engagement, commercial proposal, or client deliverable** for third-party organizations;
  2. Embedding, hosting, or operating the code or methodology within any commercial product, paid SaaS/cloud offering, or commercial production environment;
  3. Modifying, translating, repackaging, or redistributing the methodology, notebooks, or code for paid training courses, workshops, or commercial publications.
- **Commercial Licensing & Collaboration Inquiries**:
  For commercial licensing, enterprise PoC/SI delivery, or collaboration inquiries, please contact **Sean Jung ([seanjung@google.com](mailto:seanjung@google.com))** in advance.

Copyright (c) 2026 Sean Jung (`seanjung@google.com`). All Rights Reserved.
