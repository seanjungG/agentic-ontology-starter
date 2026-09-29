# 5-Stage 에이전틱 온톨로지 엔지니어링 방법론 교육용 슬라이드 (`slides/README.md`)

> 라이브 스튜디오 [`Agentic Ontology Studio`](https://agentic-ontology-starter-lwrlf7yogq-du.a.run.app) · [방법론 인덱스](../methodology/README.md) · [한/영 노트북 인덱스](../notebooks/README.md) · [프로토타이핑 플레이북](../PROTOTYPING_PLAYBOOK.md) · [라이선스 (`LICENSE`)](../LICENSE)
>
> **[저작권 및 비영리 라이선스 고지 (CC BY-NC-ND 4.0 / Non-Commercial Only)]**: 본 교육용 슬라이드 덱(`.pptx`, `.html`)과 5-Stage 온톨로지 엔지니어링 커리큘럼은 **CC BY-NC-ND 4.0** 라이선스로 보호됩니다. 개인 학습 및 비상업적 연구 외에 **유상 컨설팅, SI 구축, 유상 PoC 딜리버리, 유료 강의·교육·출판, 고객사 제안서·산출물 활용을 엄격히 금지**하며, 상업적/엔터프라이즈 활용이 필요한 경우 **[seanjung@google.com](mailto:seanjung@google.com)**으로 사전 논의하시기 바랍니다.

---

## 1. 한/영 슬라이드 파일 구성 (`slides/ko/` & `slides/en/`)

`methodology/{ko,en}/` 및 `notebooks/{ko,en}/` 폴더 구조와 1:1로 대칭되도록 **국문(`slides/ko/`)**과 **영문(`slides/en/`, 한글 노출 0건)** 두 가지 트랙으로 18장 구성의 Google Workspace Slides 교육 자료를 제공합니다.

| 구분 | 국문 슬라이드 (`slides/ko/`) | 영문 슬라이드 (`slides/en/` — 100% English) | 포맷 및 특징 |
| :--- | :--- | :--- | :--- |
| **Google Workspace Slides 파일 (`.pptx`)** | [agentic_ontology_methodology_training_ko.pptx](./ko/agentic_ontology_methodology_training_ko.pptx)<br>*(루트 사본: [agentic_ontology_methodology_training_ko.pptx](./agentic_ontology_methodology_training_ko.pptx))* | [agentic_ontology_methodology_training_en.pptx](./en/agentic_ontology_methodology_training_en.pptx)<br>*(루트 사본: [agentic_ontology_methodology_training_en.pptx](./agentic_ontology_methodology_training_en.pptx))* | **16:9 와이드스크린 (`13.333" × 7.5"`)** 네이티브 편집 가능 도형·표·텍스트박스·아키텍처 배너 PNG + **18개 전 슬라이드 강사 발표자 노트(Speaker Notes)** 내장 |
| **Google Slides 스타일 웹 뷰어 (`.html`)** | [agentic_ontology_methodology_slides_ko.html](./ko/agentic_ontology_methodology_slides_ko.html) | [agentic_ontology_methodology_slides_en.html](./en/agentic_ontology_methodology_slides_en.html) | 브라우저 즉시 실행형 Google Slides UI (좌측 필름스트립 썸네일, 16:9 캔버스, 접이식 발표자 노트 패널, `KOR ⇄ ENG` 전환, 전체화면 발표 모드 `F`) |
| **GCS 클라우드 백업 경로** | `gs://seanjung-poc-starter-ontology/slides/ko/` | `gs://seanjung-poc-starter-ontology/slides/en/` | `slides/upload_to_google_slides.py`로 자동 동기화 |

---

## 2. Google Workspace Slides에서 바로 여는 2가지 방법

### 방법 A: Google Drive / Google Slides 웹에서 직접 열기 (가장 빠른 방법)
1. Google Drive([`https://drive.google.com`](https://drive.google.com))에 [`slides/ko/agentic_ontology_methodology_training_ko.pptx`](./ko/agentic_ontology_methodology_training_ko.pptx) 또는 [`slides/en/agentic_ontology_methodology_training_en.pptx`](./en/agentic_ontology_methodology_training_en.pptx) 파일을 드래그 앤 드롭한 뒤 **더블클릭 → `Google 프레젠테이션(Google Slides)으로 열기`**를 선택합니다.
2. 또는 새 프레젠테이션([`https://slides.new`](https://slides.new))을 열고 상단 메뉴 **`파일(File)` → `슬라이드 가져오기(Import slides)` → `업로드(Upload)`**에서 `.pptx` 파일을 선택하면 도형·표·아키텍처 다이어그램·하단 발표자 노트가 100% 그대로 유지된 Google Slides 문서로 변환됩니다.

### 방법 B: CLI 스크립트로 Google Drive 클라우드 문서 자동 생성 (`upload_to_google_slides.py`)
Google Drive / Slides OAuth 스코프를 포함해 로그인한 뒤 업로더 스크립트를 실행하면, Google Drive API(`mimeType='application/vnd.google-apps.presentation'`)를 통해 클라우드 Google Slides 문서를 자동 생성하고 웹 링크(`webViewLink`)를 출력합니다.
```bash
gcloud auth login --scopes="https://www.googleapis.com/auth/cloud-platform,https://www.googleapis.com/auth/drive.file,https://www.googleapis.com/auth/presentations"
.venv/bin/python slides/upload_to_google_slides.py
```

---

## 3. 전체 18슬라이드 교육 커리큘럼 구성표 (`Slide 01` ~ `Slide 18`)

| Slide | 모듈 / 배지 | 국문 슬라이드 제목 (`slides/ko/`) | 영문 슬라이드 제목 (`slides/en/`) | 연계 방법론 문서 및 노트북 |
| :---: | :--- | :--- | :--- | :--- |
| **01** | `MODULE 00 · OVERVIEW` | 5-Stage 에이전틱 온톨로지 엔지니어링 방법론 | 5-Stage Agentic Ontology Engineering Methodology | [KO](../methodology/ko/METHODOLOGY_KO.md) · [EN](../methodology/en/METHODOLOGY_EN.md) · [Stage 0 NB](../notebooks/ko/stage0_overview_walkthrough_ko.ipynb) |
| **02** | `MODULE 00 · PROBLEM` | 왜 기존 단순 RAG와 Text-to-SQL은 엔터프라이즈에서 실패하는가? | Why Naive RAG & Standalone Text-to-SQL Fail in Enterprise Production | [KO](../methodology/ko/METHODOLOGY_KO.md) · [EN](../methodology/en/METHODOLOGY_EN.md) |
| **03** | `MODULE 00 · ARCHITECTURE` | 8단계 엔지니어링 흐름 & 5-Stage 라이프사이클 전체 지도 | 8-Phase Engineering Flow & 5-Stage Lifecycle Master Map | [KO](../methodology/ko/METHODOLOGY_KO.md) · [EN](../methodology/en/METHODOLOGY_EN.md) |
| **04** | `MODULE 00 · 3-TRACK` | 3-Track 도입 모델 (`Lite` · `Standard` · `Full`) & GCP Native 원칙 | 3-Track Adoption Model (`Lite` · `Standard` · `Full`) & GCP Native First | [`config/starter_config.json`](../config/starter_config.json) |
| **05** | `MODULE 01 · STAGE 1` | Stage 1. 자산 탐색 · 도메인 스코핑 · CQ 정의 (`D1.1`~`D1.4`) | Stage 1. Asset Discovery, Domain Scoping & Competency Questions | [Stage 1 KO](../methodology/ko/01_stage1_asset_and_cq_ko.md) · [EN](../methodology/en/01_stage1_asset_and_cq_en.md) · [NB](../notebooks/ko/stage1_asset_and_cq_ko.ipynb) |
| **06** | `MODULE 01 · DEEP DIVE` | Stage 1 심화: Golden CQ 명세 구조와 독립 정답 검증 SQL (`Gate 1`) | Stage 1 Deep Dive: Golden CQ Specification & Independent SQL Oracle | [`golden_competency_questions.json`](../data/input/04_cq/golden_competency_questions.json) |
| **07** | `MODULE 02 · STAGE 2` | Stage 2. 비정형 문서 파싱 · SHA-256 해시 앵커 · OKF v0.2 (`D2.1`~`D2.6`) | Stage 2. Unstructured Parsing, SHA-256 Lexical Anchors & OKF v0.2 | [Stage 2 KO](../methodology/ko/02_stage2_wiki_and_semantic_graph_ko.md) · [EN](../methodology/en/02_stage2_wiki_and_semantic_graph_en.md) · [NB](../notebooks/ko/stage2_wiki_and_semantic_graph_ko.ipynb) |
| **08** | `MODULE 02 · DEEP DIVE` | Stage 2 심화: Karpathy 3-Layer LLM-Wiki & 시맨틱 브릿지 (`Gate 2`) | Stage 2 Deep Dive: Karpathy 3-Layer LLM-Wiki & Semantic Bridges | [`data/llm_wiki/ko/`](../data/llm_wiki/ko/) · [`data/llm_wiki/en/`](../data/llm_wiki/en/) |
| **09** | `MODULE 03 · STAGE 3` | Stage 3. Zero-ETL 2-Layer Property Graph 구축 (`D3.1`~`D3.4`) | Stage 3. Zero-ETL 2-Layer Property Graph Architecture | [Stage 3 KO](../methodology/ko/03_stage3_property_graph_ko.md) · [EN](../methodology/en/03_stage3_property_graph_en.md) · [NB](../notebooks/ko/stage3_property_graph_bigquery_spanner_ko.ipynb) |
| **10** | `MODULE 03 · DEEP DIVE` | Stage 3 심화: BigQuery vs Spanner 듀얼 DDL 및 다중 홉 ISO GQL 패턴 (`Gate 3`) | Stage 3 Deep Dive: Dual DDL (BigQuery vs. Spanner) & Multi-Hop ISO GQL | [`pipeline/graph_builder.py`](../pipeline/graph_builder.py) |
| **11** | `MODULE 04 · STAGE 4` | Stage 4. 8종 도메인 MCP 도구 아키텍처 (`5 Stage + 3 Runtime`) (`D4.1`~`D4.4`) | Stage 4. 8 Domain MCP Tools Architecture (`5 Stage + 3 Runtime`) | [Stage 4 KO](../methodology/ko/04_stage4_agent_and_mcp_ko.md) · [EN](../methodology/en/04_stage4_agent_and_mcp_en.md) · [NB](../notebooks/ko/stage4_agent_and_mcp_execution_ko.ipynb) |
| **12** | `MODULE 04 · DEEP DIVE` | Stage 4 심화: 결정론적 위약금·TCO 판정 트리와 2-Pass Gemini 추론 (`Gate 4`) | Stage 4 Deep Dive: Deterministic Penalty Decision Tree & 2-Pass Gemini Loop | [`src/agent/mcp_server.py`](../src/agent/mcp_server.py) · [`reasoning_engine.py`](../src/agent/reasoning_engine.py) |
| **13** | `MODULE 05 · STAGE 5` | Stage 5. 4계층 엔드투엔드 데이터 리니지 & 영향도 추적 (`D5.1`~`D5.2`) | Stage 5. 4-Tier End-to-End Data Lineage & Impact Traceability | [Stage 5 KO](../methodology/ko/05_stage5_lineage_and_eval_ko.md) · [EN](../methodology/en/05_stage5_lineage_and_eval_en.md) · [NB](../notebooks/ko/stage5_lineage_and_evaluation_ko.ipynb) |
| **14** | `MODULE 05 · DEEP DIVE` | Stage 5 심화: 이중 벤치마크(`Golden CQ 5` + `Boundary 10×5`) & 배포 게이트 (`Gate 5`) | Stage 5 Deep Dive: Dual Benchmark (`5 Golden CQs + 10×5 Boundary`) & Gate 5 | [`pipeline/validator.py`](../pipeline/validator.py) · [`terraform/`](../terraform/) |
| **15** | `MODULE 06 · HANDS-ON` | 실습 환경 가이드: 6-Tab 거버넌스 스튜디오 & 12종 한/영 주피터 노트북 | Hands-On Lab Environment: 6-Tab Governance Studio & 12 Bilingual Notebooks | [`notebooks/README.md`](../notebooks/README.md) · [`studio_server.py`](../src/web/studio_server.py) |
| **16** | `MODULE 07 · PLAYBOOK` | 도메인 적용 플레이북: 4대 시나리오(`A`~`D`) & `5-File Swap` 아키텍처 | Domain Adaptation Playbook: 4 Scenarios (`A`–`D`) & `5-File Swap` | [`PROTOTYPING_PLAYBOOK.md`](../PROTOTYPING_PLAYBOOK.md) |
| **17** | `MODULE 07 · AI AGENT` | AI 코딩 에이전트(`Antigravity` · `Cursor` · `Claude Code`) 3-Step 명령 가이드 | AI Coding Agent (`Antigravity` · `Cursor` · `Claude Code`) 3-Step Prompt Guide | [`01_prod.md`](../01_prod.md) · [`GEMINI.md`](../GEMINI.md) · [`CLAUDE.md`](../CLAUDE.md) |
| **18** | `MODULE 08 · CASES` | 4대 산업군 8종 엔터프라이즈 레퍼런스 템플릿(`industry_cases/`) & 과정 요약 | 4 Industry Sectors × 8 Enterprise Reference Templates & Wrap-Up | [`industry_cases/README.md`](../industry_cases/README.md) |

---

## 4. 슬라이드 재생성 및 커스터마이징 방법

슬라이드 텍스트·표·발표자 노트는 [`slides/slide_specs_ko.py`](./slide_specs_ko.py)(국문) 및 [`slides/slide_specs_en.py`](./slide_specs_en.py)(영문)에 선언되어 있으며, 아래 명령으로 `.pptx`와 `.html` 덱을 동시에 재생성합니다.

```bash
.venv/bin/python slides/generate_training_slides.py
```
