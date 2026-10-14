# 🚀 Agentic Ontology Starter (v3.0 Minimal · `v1-mcp` Standard)

> **누구든 3분 만에 시작하는 초경량 엔터프라이즈 Agentic Ontology 스타터 팩**
> 복잡한 온톨로지 컴파일러 코드는 **코어 빌더 MCP(`aos-builder-core-mcp`)**로 추상화하고, 내 도메인에 필요한 **데이터 경로(`P1 문서` · `P2 원장` · `P3 통합`)**와 **워크플로우(`W1 규정` · `W2 원장` · `W3 하이브리드`)**만 선택해 바로 실행·확장할 수 있도록 **단 5개의 핵심 Python 파일**만 남겼습니다.

---

## 🌐 Live Studios & Reference Endpoints

| 구분 | 서비스명 | 라이브 URL | 설명 |
| :--- | :--- | :--- | :--- |
| **Starter Portal** | `agentic-ontology-starter` | [**Starter Live Studio ↗**](https://agentic-ontology-starter-924723860007.asia-northeast3.run.app/) | **`0. Getting Started`** + 선택형 `P1/P2/P3 × W1/W2/W3` 플로우 구성기 + **2-Tier MCP 가이드 & 라이브 실행기** |
| **Reference #1** | `lguplus_mcp_built` (`v1-mcp`) | [**LG U+ v1-MCP Studio ↗**](https://agentic-ontology-studio-lguplus-mcp-924723860007.asia-northeast3.run.app/) | `aos-builder-core-mcp`로 구축된 LG U+ 단말지원금·위약금 12-Tab 엔터프라이즈 기준 스튜디오 |
| **Reference #2** | `hnh_mcp_built` (`v1-mcp`) | [**LG H&H v1-MCP Studio ↗**](https://hnh-agentic-ontology-studio-mcp-384182013777.asia-northeast3.run.app/) | `aos-builder-core-mcp`로 구축된 LG생활건강 화장품 표시·광고 컴플라이언스 12-Tab 스튜디오 |
| **Builder Core MCP** | `aos-builder-core-mcp` | `https://aos-builder-core-mcp-924723860007.asia-northeast3.run.app/mcp/builder` | 원천 문서·DW 원장으로부터 위키·워크플로우·BigQuery Property Graph를 자동 컴파일하는 **8종 코어 빌더 MCP** |

---

## ⚡ 1. Quickstart (3분 만에 로컬 실행)

외부 무거운 패키지 설치 없이 **Python 3.11 표준 라이브러리**만으로 즉시 실행됩니다.

```bash
# 1. 저장소 클론 및 이동
git clone https://github.com/seanjungG/agentic-ontology-starter.git
cd agentic-ontology-starter

# 2. GCP 인증 (기본 제공되는 Ready-to-Use 샘플 리소스 즉시 사용 가능)
gcloud auth application-default login

# 3. 스타터 스튜디오 웹 서버 실행 (http://localhost:8080)
python3 -m src.web.studio_server
```

브라우저에서 **`http://localhost:8080`**을 열면 **`🚀 0. Getting Started`** 페이지가 나타나며, 플로우 선택부터 GCP 리소스 연결 검증, MCP 도구 실행까지 한 화면에서 진행할 수 있습니다.

---

## 📂 2. 초경량 5-File 핵심 코드 구조 (Minimal Core)

불필요한 슬라이드, 이론 문서, 테라폼, 내부 파이프라인 스크립트를 모두 제거하고 **실제 커스터마이징에 필요한 5개 핵심 코드**만 남겼습니다.

```text
agentic-ontology-starter/
├── src/
│   ├── resource_connector.py       # [파일 1] 내 GCP 리소스 연결(connect_my_resources) + 선택형 플로우 프리셋 + 2-Tier MCP 명세
│   ├── gcp_client.py               # [파일 2] 순수 Python 표준 라이브러리 기반 BigQuery / Spanner / GCS / Vertex AI REST 어댑터
│   ├── agent/
│   │   ├── mcp_server.py           # [파일 3] 워크플로우 노드에 1:1 바인딩되는 런타임 도메인 비즈니스 MCP 도구 3종
│   │   └── reasoning_engine.py     # [파일 4] Vertex AI (gemini-3.8-flash) 슬롯 추출 · 도메인 도구 체이닝 · SHA-256 근거 합성 엔진
│   └── web/
│       └── studio_server.py        # [파일 5] Getting Started + v1-MCP 선택형 플로우 UI + MCP 커스텀 가이드 웹 서버
├── config/                         # starter_config.json, lineage_spec.json, eval_rubric.json
├── data/                           # 즉시 실행 가능한 비식별 샘플 데이터 (문서 청크, 3-Layer OKF 위키, W1~W3 워크플로우, CSV)
├── notebooks/{ko,en}/              # Stage 0 ~ Stage 5 한/영 Google Colab 실습 노트북 (12종)
└── tests/test_data_fidelity.py     # 미니멀 코어 구조 · 플로우 프리셋 · 2-Tier MCP · API 엔드포인트 검증 테스트
```

---

## 🧭 3. 선택형 플로우 구성기 (`P1/P2/P3 × W1/W2/W3 × Gate G2-W`)

처음부터 모든 구성요소를 다 구축할 필요가 없습니다. 내 프로젝트의 데이터 준비 상황에 맞춰 **3가지 플로우 중 하나를 선택**하거나 개별 경로를 조합해 시작하세요.

| 선택 플로우 | 데이터 경로 (`P1~P3`) | 워크플로우 (`W1~W3`) | 언제 선택하나요? | 필수 GCP 리소스 |
| :--- | :---: | :---: | :--- | :--- |
| **Flow A · Document-First** | **`P1`** (비정형 문서) | **`W1`** (규정 판정) | 정형 DB/원장 없이 **정책 가이드·약관·매뉴얼 문서**만으로 규정 질의응답 에이전트를 빠르게 시작할 때 | GCS OKF Wiki + `tb_doc_chunks` + Vertex AI |
| **Flow B · Ledger-First** | **`P2`** (정형 DW 원장) | **`W2`** (원장 검증) | 기존 **BigQuery / Spanner 마스터·거래 테이블**을 Property Graph로 묶어 계약·상태 조회를 자동화할 때 | BigQuery DW & Property Graph + Vertex AI |
| **Flow C · Full `v1-mcp` Hybrid** | **`P1 + P2 + P3`** | **`W1 + W2 + W3` + `Gate G2-W`** | **문서 규정(`P1`)과 고객 원장(`P2`)을 브릿지 엣지(`P3`) 및 단일 출처 상수(`G2-W`)로 결합**해 위약금/정산/컴플라이언스를 무환각 판정할 때 (LG U+ / LG H&H 표준) | BigQuery DW & Graph + GCS 3-Layer Wiki + Vertex AI (+ Spanner 선택) |

---

## 🛠️ 4. 2-Tier MCP 아키텍처: 역할 및 커스터마이징 가이드

Agentic Ontology는 **① 온톨로지를 자동으로 컴파일하는 빌드 타임 코어 MCP(`aos-builder-core-mcp`)**와 **② 런타임에 실제 비즈니스 데이터를 조회·계산하는 도메인 비즈니스 MCP(`src/agent/mcp_server.py`)**로 역할을 분리합니다.

### 🏗️ Tier 1 — 코어 빌더 MCP (`aos-builder-core-mcp` · 8종 도구)

복잡한 파서나 그래프 컴파일러를 직접 코딩하지 않고, Gemini CLI / Claude Code / Cursor에 `aos-builder-core-mcp`를 연결하여 6단계 온톨로지 파이프라인을 실행합니다.

#### ① MCP 클라이언트 연결 설정 (`~/.gemini/settings.json` 또는 `.mcp.json`)
```json
{
  "mcpServers": {
    "aos-builder-core-mcp": {
      "type": "http",
      "url": "https://aos-builder-core-mcp-924723860007.asia-northeast3.run.app/mcp/builder"
    }
  }
}
```

#### ② `aos-builder-core-mcp` 8대 도구 역할 및 플로우별 사용 단계

| 단계 | 코어 빌더 MCP 도구명 | 적용 플로우 | 핵심 역할 및 산출물 |
| :---: | :--- | :---: | :--- |
| **Init** | `mcp_builder_get_domain_spec_template` | `All` | 신규 도메인 온보딩용 선언형 `build_spec` JSON 템플릿 반환 |
| **Stage 1** | `mcp_builder_inspect_and_scope_stage1` | `P1, P2, P3` | 원천 문서 번들(`P1`) 및 정형 DW 원장(`P2`) 스캔, PK/FK 무결성 점검 및 `project.json` 생성 |
| **Gate 0** | `mcp_builder_parse_documents_gate0` | `P1, P3` | 비정형 문서를 문단/표 단위로 무손실 파싱(`>=95%`)하고 SHA-256 해시 앵커 부여 (`gate0_report.json`) |
| **Stage 2** | `mcp_builder_compile_okf_wiki_stage2` | `P1, P3` | 3-Layer OKF 위키(`01_summary`, `02_entities`, `03_concepts`) 및 `graph.properties` 정책 상수 컴파일 |
| **Stage 3** | `mcp_builder_extract_rules_workflows_stage3` | `W1, W2, W3, G2-W` | 비즈니스 룰(`BR-*`), `W1/W2/W3` 워크플로우 DAG, `Gate G2-W` 상수 검증 및 `D4.5` 도메인 도구 바인딩 생성 |
| **Stage 4** | `mcp_builder_synthesize_bqg_stage4` | `P2, P3` | BigQuery에 정형 노드(`P2`) + 위키 룰 노드(`P1`) + 브릿지 엣지(`P3`) 적재 및 `CREATE PROPERTY GRAPH` 실행 |
| **Stage 5** | `mcp_builder_verify_gates_and_cqs_stage5` | `All` | Gate 0 / Gate 2 / Gate G2-W / Gate 3 / Gate 4(`D4.5`) 및 워크플로우 CQ(`WCQ-*`) 결정론 리플레이 검증 |
| **Stage 6** | `mcp_builder_provision_studio_infra_stage6` | `All` | 스튜디오 카탈로그(`assets_registry.json`, `cq_registry.json`), 호환 뷰, GCS 위키 동기화 (`mcp_builder_run_full_pipeline`으로 일괄 실행 가능) |

---

### ⚡ Tier 2 — 런타임 도메인 비즈니스 MCP (`src/agent/mcp_server.py` · 3종 도구)

런타임 에이전트(`AiFdeAgentEngine`)와 워크플로우(`W1~W3`)가 호출하는 결정론적 비즈니스 도구 3종입니다.

| 도메인 MCP 도구명 | 바인딩 플로우 | 핵심 역할 | 내 도메인 커스텀 포인트 (`src/agent/mcp_server.py`) |
| :--- | :---: | :--- | :--- |
| **`mcp_lookup_customer_profile`** | `P2 · W2` | 정형 DW 마스터·계약 원장에서 고객 계약, 단말 출고가, 지원금 정책을 결정론 SQL로 조회 | `_mcp_lookup_customer_profile()` 내 SQL을 내 도메인의 마스터/거래 원장 테이블 조회 쿼리로 교체 |
| **`mcp_calculate_penalty_rule`** | `P3 · W3 · Gate G2-W` | 위키 정책 상수(`180일`, `45,000원`, 복지 면제)와 고객 원장을 결합해 일할 위약금 및 24개월 TCO를 SQL로 계산 | `_mcp_calculate_penalty_rule()` 내 수식을 내 도메인의 정산·한도·컴플라이언스 판정 산식으로 교체 |
| **`mcp_query_graph_and_wiki`** | `P1 + P2 · W1/W3` | BigQuery/Spanner `GRAPH_TABLE` 멀티홉 탐색 + `tb_doc_chunks` SHA-256 원문 해시 앵커 결합 | `_mcp_query_graph_and_wiki()`의 `MATCH (a)-[r]->(b)` 패턴을 내 Property Graph 노드/엣지 라벨로 변경 |

#### 내 도메인 적용 3단계 코드 레시피
```python
# Step 1. 내 GCP 리소스 연결 (src/resource_connector.py)
from src.resource_connector import connect_my_resources
manifest = connect_my_resources(
    project_id="my-gcp-project",
    dataset_id="my_ontology_dw",
    gcs_bucket="my-ontology-wiki-bucket",
    verify=True,
)

# Step 2. 런타임 도메인 MCP 도구 단독 테스트 (src/agent/mcp_server.py)
from src.agent.mcp_server import DomainMcpServer
mcp = DomainMcpServer(project_id="my-gcp-project", dataset_id="my_ontology_dw")
res = mcp.execute_tool("mcp_calculate_penalty_rule", {
    "customer_id": "CUST_DEMO_001",
    "target_plan_name": "5G 슬림 (45,000원)",
    "elapsed_days": 95,
})

# Step 3. AI FDE 에이전트 전체 추론 사이클 실행 (src/agent/reasoning_engine.py)
from src.agent.reasoning_engine import AiFdeAgentEngine
agent = AiFdeAgentEngine(project_id="my-gcp-project")
answer = agent.execute_cycle("CUST_DEMO_001 고객이 95일째에 45,000원 요금제로 변경하면 위약금이 얼마인가요?")
print(answer["final_synthesis"])
```

---

## 📓 5. 단계별 Google Colab 실습 노트북 (`notebooks/{ko,en}/`)

| 단계 | 한국어 노트북 | English Notebook | 핵심 실습 내용 |
| :--- | :--- | :--- | :--- |
| **Stage 0** | [`stage0_overview_walkthrough_ko.ipynb`](notebooks/ko/stage0_overview_walkthrough_ko.ipynb) | [`stage0_overview_walkthrough_en.ipynb`](notebooks/en/stage0_overview_walkthrough_en.ipynb) | `connect_my_resources()` 연결 및 `P1/P2/P3 × W1/W2/W3` 아키텍처 점검 |
| **Stage 1** | [`stage1_asset_and_cq_ko.ipynb`](notebooks/ko/stage1_asset_and_cq_ko.ipynb) | [`stage1_asset_and_cq_en.ipynb`](notebooks/en/stage1_asset_and_cq_en.ipynb) | 원천 문서(Gate 0 SHA-256 앵커) 및 정형 DW 원장 데이터 준비성 점검 |
| **Stage 2** | [`stage2_wiki_and_semantic_graph_ko.ipynb`](notebooks/ko/stage2_wiki_and_semantic_graph_ko.ipynb) | [`stage2_wiki_and_semantic_graph_en.ipynb`](notebooks/en/stage2_wiki_and_semantic_graph_en.ipynb) | OKF 3-Layer 위키(`summary/entities/concepts/rules.md`) 및 `Gate G2-W1` 단일 출처 상수 |
| **Stage 3** | [`stage3_property_graph_bigquery_spanner_ko.ipynb`](notebooks/ko/stage3_property_graph_bigquery_spanner_ko.ipynb) | [`stage3_property_graph_bigquery_spanner_en.ipynb`](notebooks/en/stage3_property_graph_bigquery_spanner_en.ipynb) | BigQuery SQL:2023 `GRAPH_TABLE` & Cloud Spanner ISO GQL 멀티홉 탐색 |
| **Stage 4** | [`stage4_agent_and_mcp_execution_ko.ipynb`](notebooks/ko/stage4_agent_and_mcp_execution_ko.ipynb) | [`stage4_agent_and_mcp_execution_en.ipynb`](notebooks/en/stage4_agent_and_mcp_execution_en.ipynb) | 도메인 비즈니스 MCP 도구 3종 및 Vertex AI `gemini-3.8-flash` AI FDE 실행 |
| **Stage 5** | [`stage5_lineage_and_evaluation_ko.ipynb`](notebooks/ko/stage5_lineage_and_evaluation_ko.ipynb) | [`stage5_lineage_and_evaluation_en.ipynb`](notebooks/en/stage5_lineage_and_evaluation_en.ipynb) | 6-Layer 데이터 리니지 역추적 및 Golden/Boundary CQ 전수 검증 |

---

## 🧪 6. 테스트 실행

```bash
python3 -m unittest discover -s tests -p "test_*.py" -v
```
