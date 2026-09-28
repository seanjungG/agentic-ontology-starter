# Agentic Ontology Starter

정형 데이터(BigQuery DW)와 비정형 정책 문서(업무 가이드·약관)를 **3-Layer 위키(OKF v0.2)**와 **BigQuery Property Graph(ISO SQL:2023 GQL)**로 결합하고, **8종 MCP 도구**와 **Vertex AI Gemini 에이전트(`gemini-3.8-flash`)**로 검증·서빙하는 **5-Stage 엔터프라이즈 온톨로지 스타터 팩**입니다.

- **라이브 스튜디오 (Cloud Run)**: [https://agentic-ontology-starter-924723860007.asia-northeast3.run.app](https://agentic-ontology-starter-924723860007.asia-northeast3.run.app)
- **방법론 마스터 가이드**: [한국어 (`METHODOLOGY_KO.md`)](./methodology/METHODOLOGY_KO.md) · [English (`METHODOLOGY_EN.md`)](./methodology/METHODOLOGY_EN.md)
- **실행형 Jupyter 노트북 (11종)**: [노트북 가이드 (`notebooks/README.md`)](./notebooks/README.md)

---

## 1. 5-Stage 아키텍처 · 스튜디오 · 방법론 · 노트북 통합 지도

| Stage | 핵심 역할 | 라이브 스튜디오 탭 | 방법론 가이드 (KO / EN) | 실습 노트북 (KO / EN) |
| :---: | :--- | :--- | :--- | :--- |
| **0. Overview** | 5-Stage 파이프라인·3-Track·MCP 실행 보드·산업군 쇼케이스 | [`0. Overview`](https://agentic-ontology-starter-924723860007.asia-northeast3.run.app/?tab=overview) | [KO](./methodology/METHODOLOGY_KO.md) · [EN](./methodology/METHODOLOGY_EN.md) | [stage0_overview_walkthrough.ipynb](./notebooks/stage0_overview_walkthrough.ipynb) |
| **Stage 1** | 원천 테이블(10개)·가이드(2종) 프로파일링, 용어사전, Golden CQ(5건)·경계값(10건) 정의 | [`Stage 1. Asset`](https://agentic-ontology-starter-924723860007.asia-northeast3.run.app/?tab=stage1) | [KO](./methodology/01_stage1_asset_and_cq_ko.md) · [EN](./methodology/01_stage1_asset_and_cq_en.md) | [KO](./notebooks/stage1_asset_and_cq_ko.ipynb) · [EN](./notebooks/stage1_asset_and_cq_en.ipynb) |
| **Stage 2** | 3-Layer 위키(`data/llm_wiki/`), SHA-256 문단 앵커, JSON-LD 시맨틱 그래프 구축 | [`Stage 2. Wiki & Semantic Graph`](https://agentic-ontology-starter-924723860007.asia-northeast3.run.app/?tab=stage2) | [KO](./methodology/02_stage2_wiki_and_semantic_graph_ko.md) · [EN](./methodology/02_stage2_wiki_and_semantic_graph_en.md) | [KO](./notebooks/stage2_wiki_and_semantic_graph_ko.ipynb) · [EN](./notebooks/stage2_wiki_and_semantic_graph_en.ipynb) |
| **Stage 3** | BigQuery Property Graph(`STARTER_ONTOLOGY_GRAPH` 6노드/4엣지), ISO GQL 탐색, NL2GQL 실행 | [`Stage 3. Property Graph`](https://agentic-ontology-starter-924723860007.asia-northeast3.run.app/?tab=stage3) | [KO](./methodology/03_stage3_property_graph_ko.md) · [EN](./methodology/03_stage3_property_graph_en.md) | [KO](./notebooks/stage3_property_graph_bigquery_spanner_ko.ipynb) · [EN](./notebooks/stage3_property_graph_bigquery_spanner_en.ipynb) |
| **Stage 4** | Stage MCP(5종) + Runtime MCP(3종) 및 Gemini 2-패스 근거 기반 에이전트 추론 | [`Stage 4. Agent & MCP`](https://agentic-ontology-starter-924723860007.asia-northeast3.run.app/?tab=stage4) | [KO](./methodology/04_stage4_agent_and_mcp_ko.md) · [EN](./methodology/04_stage4_agent_and_mcp_en.md) | [KO](./notebooks/stage4_agent_and_mcp_execution_ko.ipynb) · [EN](./notebooks/stage4_agent_and_mcp_execution_en.ipynb) |
| **Stage 5** | 4계층 데이터 리니지, Golden CQ 5건 검증, 경계값 10건×5회 반복 평가 및 배포 게이트 | [`Stage 5. Lineage & Eval`](https://agentic-ontology-starter-924723860007.asia-northeast3.run.app/?tab=stage5) | [KO](./methodology/05_stage5_lineage_and_eval_ko.md) · [EN](./methodology/05_stage5_lineage_and_eval_en.md) | [KO](./notebooks/stage5_lineage_and_evaluation_ko.ipynb) · [EN](./notebooks/stage5_lineage_and_evaluation_en.ipynb) |

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
# 1. Stage 1~3: 샘플 가이드·CSV 파싱 → 3-Layer 위키 → BigQuery 10개 테이블 & STARTER_ONTOLOGY_GRAPH 적재 → GCS 업로드
python3 -m src.pipeline.ingest

# 2. Stage 5: Golden CQ 5건 검증 및 경계값 10건×5회 라이브 벤치마크 실행
python3 -m src.eval.boundary_eval

# 3. 6-Tab 통합 웹 스튜디오 로컬 실행 (http://127.0.0.1:8080)
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
│   ├── input/                       # Stage 1 입력: 01_guides(2), 03_tables(CSV 6), 04_eval(CQ 5, 경계값 10), 05_glossary
│   ├── llm_wiki/                    # Stage 2 산출물: 3-Layer OKF 위키 (01_summary, 02_entities, 03_concepts, index.md)
│   └── output/                      # Stage 2~5 산출물: ontology.jsonld, BQ/Spanner Graph DDL, 평가 리포트 JSON
├── methodology/                     # 5-Stage 방법론 마스터(KO/EN) 및 Stage 1~5 한/영 상세 가이드 (13개 파일)
├── notebooks/                       # BigFrames %%bqsql + 네트워크 그래프/차트 시각화 실습 노트북 11종 + 헬퍼(nb_helpers.py)
├── src/
│   ├── gcp_client.py                # BigQuery REST/GQL, GCS 업로드, Vertex AI Gemini 호출 클라이언트
│   ├── pipeline/ingest.py           # Stage 1~3 데이터 파싱·위키 컴파일·BigQuery/GCS 적재 파이프라인
│   ├── agent/mcp_server.py          # Stage MCP 5종 + Runtime MCP 3종 (총 8종)
│   ├── agent/reasoning_engine.py    # 2-패스 Gemini 목표 분해 · MCP 호출 · 근거 합성 에이전트 엔진
│   ├── eval/boundary_eval.py        # Golden CQ 5건 검증 및 경계값 10건×5회 반복 평가 엔진
│   └── web/studio_server.py         # 6-Tab Agentic Ontology Studio 웹 서버
├── terraform/                       # BigQuery, GCS, IAM, Cloud Build + Cloud Run 선언적 IaC
└── Dockerfile                       # Cloud Run 컨테이너 이미지 정의
```
