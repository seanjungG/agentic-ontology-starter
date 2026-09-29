# Agentic Ontology Starter

정형 데이터(BigQuery DW)와 비정형 정책 문서(업무 가이드·약관)를 **3-Layer 위키(OKF v0.2)**와 **BigQuery Property Graph(ISO SQL:2023 GQL)**로 결합하고, **8종 MCP 도구**와 **Vertex AI Gemini 에이전트(`gemini-3.8-flash`)**로 검증·서빙하는 **5-Stage 엔터프라이즈 온톨로지 스타터 팩**입니다.

- **라이브 스튜디오 (Cloud Run)**: [https://agentic-ontology-starter-lwrlf7yogq-du.a.run.app](https://agentic-ontology-starter-lwrlf7yogq-du.a.run.app)
- **방법론 마스터 가이드**: [한국어 (`METHODOLOGY_KO.md`)](./methodology/METHODOLOGY_KO.md) · [English (`METHODOLOGY_EN.md`)](./methodology/METHODOLOGY_EN.md)
- **실행형 Jupyter 노트북 (12종 · `ko/` 국문 6종 + `en/` 영문 6종 분리)**: [노트북 허브 (`notebooks/README.md`)](./notebooks/README.md) · [🇰🇷 전체 흐름 초기 노트북 (`ko/`)](./notebooks/ko/stage0_overview_walkthrough_ko.ipynb) · [🇺🇸 English Overview Notebook (`en/`)](./notebooks/en/stage0_overview_walkthrough_en.ipynb)

---

## 1. 8단계 엔지니어링 흐름 & 5-Stage · 스튜디오 · 방법론 · 한/영 노트북 통합 지도

전체 과정은 **1. 준비(Prepare) → 2. 분석(Analyze) → 3. 파싱(Parse) → 4. 통합(Integrate) → 5. 구축(Build Graph) → 6. 에이전트 구축(Build Agent) → 7. 답변(Answer & GQL) → 8. 검증(Verify & Gate)**의 8단계 엔지니어링 흐름을 따라 진행되며, 각 단계마다 파이프라인 실행 코드, 중간 테이블/데이터 확인(`%%bqsql`), 바인딩 변수·실행 GQL 문장(`H.run_gql`), 그래프 설계 도식이 함께 제공됩니다.

| 8단계 엔지니어링 흐름 | 정본 Stage | 핵심 구현 및 중간 데이터/그래프 확인 | 라이브 스튜디오 탭 | 방법론 가이드 (KO / EN) | 실습 노트북 (`ko/` / `en/`) |
| :--- | :---: | :--- | :--- | :---: | :---: |
| **0. 전체 흐름 초기 화면**<br>*(End-to-End Tour)* | **0. Overview** | 8단계 파이프라인 흐름도, 10개 테이블 스키마 블루프린트, Stage 1~5 MCP 실행, 시맨틱/물리 그래프 토폴로지, 바인딩 변수 기반 3-Hop GQL & 에이전트 추론, Gate 1~5 판정 | [`0. Overview`](https://agentic-ontology-starter-lwrlf7yogq-du.a.run.app/?tab=overview) | [KO](./methodology/METHODOLOGY_KO.md) · [EN](./methodology/METHODOLOGY_EN.md) | [KO](./notebooks/ko/stage0_overview_walkthrough_ko.ipynb) · [EN](./notebooks/en/stage0_overview_walkthrough_en.ipynb) |
| **1. 준비 (Prepare)**<br>**2. 분석 (Analyze)** | **Stage 1** | 원시 CSV/MD 인벤토리, `INFORMATION_SCHEMA` 스키마 설계도, `mcp_stage1_asset_discovery` 비식별화 검증, 약정·단말·요금제·지원금 히트맵, Golden CQ 5종 SQL 검증 | [`Stage 1. Asset`](https://agentic-ontology-starter-lwrlf7yogq-du.a.run.app/?tab=stage1) | [KO](./methodology/01_stage1_asset_and_cq_ko.md) · [EN](./methodology/01_stage1_asset_and_cq_en.md) | [KO](./notebooks/ko/stage1_asset_and_cq_ko.ipynb) · [EN](./notebooks/en/stage1_asset_and_cq_en.ipynb) |
| **3. 파싱 (Parse)**<br>**4. 통합 (Integrate)** | **Stage 2** | `pipeline/ingest.py` 정규식 청킹 & SHA-256 해시 앵커 대조, 3-Layer Wiki(`summary`, `entities`, `concepts`, `rules`) 컴파일, Gemini 트리플 추출, 시맨틱 그래프 도식 | [`Stage 2. Wiki & Semantic Graph`](https://agentic-ontology-starter-lwrlf7yogq-du.a.run.app/?tab=stage2) | [KO](./methodology/02_stage2_wiki_and_semantic_graph_ko.md) · [EN](./methodology/02_stage2_wiki_and_semantic_graph_en.md) | [KO](./notebooks/ko/stage2_wiki_and_semantic_graph_ko.ipynb) · [EN](./notebooks/en/stage2_wiki_and_semantic_graph_en.ipynb) |
| **5. 구축 (Build Graph)** | **Stage 3** | 6 Node × 4 Edge 메타모델 설계도, BigQuery/Spanner Graph DDL(`pipeline/graph_builder.py`), 5계층 토폴로지 & 1~2홉 서브그래프, 바인딩 변수·ISO GQL 문장(`GQL-01~05`) & `nl2gql` | [`Stage 3. Property Graph`](https://agentic-ontology-starter-lwrlf7yogq-du.a.run.app/?tab=stage3) | [KO](./methodology/03_stage3_property_graph_ko.md) · [EN](./methodology/03_stage3_property_graph_en.md) | [KO](./notebooks/ko/stage3_property_graph_bigquery_spanner_ko.ipynb) · [EN](./notebooks/en/stage3_property_graph_bigquery_spanner_en.ipynb) |
| **6. 에이전트 구축 (Agent)**<br>**7. 답변 (Answer)** | **Stage 4** | 2-Pass 에이전트 & 8종 MCP 설계도, 카탈로그 슬롯 파싱(`resolve_params`), 런타임 MCP GQL/SQL 실행, 180일 위약금 곡선, Golden CQ(`GROUNDED`) & 경계(`INSUFFICIENT`, `NOT_FOUND`) 답변 | [`Stage 4. Agent & MCP`](https://agentic-ontology-starter-lwrlf7yogq-du.a.run.app/?tab=stage4) | [KO](./methodology/04_stage4_agent_and_mcp_ko.md) · [EN](./methodology/04_stage4_agent_and_mcp_en.md) | [KO](./notebooks/ko/stage4_agent_and_mcp_execution_ko.ipynb) · [EN](./notebooks/en/stage4_agent_and_mcp_execution_en.ipynb) |
| **8. 검증 (Verify & Gate)** | **Stage 5** | 4-Tier 데이터 리니지(`Source File → DocChunk → DomainRule → Contract → CQ`) 멀티파타이트 도식, `pipeline/validator.py` 실시간 CQ 재검증, Boundary 50회 평가 & Gate 1~5 | [`Stage 5. Lineage & Eval`](https://agentic-ontology-starter-lwrlf7yogq-du.a.run.app/?tab=stage5) | [KO](./methodology/05_stage5_lineage_and_eval_ko.md) · [EN](./methodology/05_stage5_lineage_and_eval_en.md) | [KO](./notebooks/ko/stage5_lineage_and_evaluation_ko.ipynb) · [EN](./notebooks/en/stage5_lineage_and_evaluation_en.ipynb) |

---

## 2. 3-Track 도입 모델 (`config/starter_config.json`)

| 트랙 | 활성 Stage | 물리 그래프 | 권장 적용 시나리오 |
| :--- | :---: | :---: | :--- |
| **Track 1 · Lite** | `Stage 1 → 2 → 4` | `none` | 비정형 가이드·약관 문서만으로 3-Layer 위키와 에이전트를 즉시 구축·검증 |
| **Track 2 · Standard** | `Stage 1 → 2 → 3 → 4` | `bigquery` (Spanner는 DDL 생성) | 정형 DW 테이블과 비정형 위키를 `STARTER_ONTOLOGY_GRAPH`로 통합해 GQL 다중 홉 추론 수행 |
| **Track 3 · Full** | `Stage 1 → 2 → 3 → 4 → 5` | `bigquery` | 4계층 리니지, Golden CQ 5건, 경계값 벤치마크(10×5), Terraform Cloud Run 배포까지 전주기 운영 |

---

## 3. 빠른 시작 (3분 실행 가이드)

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
├── config/
│   ├── starter_config.json          # 3-Track 설정, 그래프 엔진, MCP 8종 정의
│   └── portal_profile.json          # 스튜디오 프로필 및 산업군 쇼케이스(Telecom/Retail/Finance/Manufacturing)
├── data/
│   ├── input/                       # Stage 1 입력: 01_guides(2), 03_tables(CSV 6), 04_cq(CQ 5, 경계값 10), 05_glossary
│   ├── llm_wiki/                    # Stage 2 산출물: 3-Layer OKF 위키 (summary.md, entities.md, concepts.md, rules.md)
│   └── output/                      # Stage 2~5 산출물: ontology.jsonld, BQ/Spanner Graph DDL, 평가 리포트 JSON
├── methodology/                     # 5-Stage 방법론 마스터(KO/EN) 및 Stage 1~5 한/영 상세 가이드 (13개 파일)
├── notebooks/                       # 8단계 흐름 기반 한/영 실습 노트북 12종 + 공통 헬퍼(nb_helpers.py)
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
