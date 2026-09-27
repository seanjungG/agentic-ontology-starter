# Agentic Ontology Studio — Enterprise Starter Pack (v2.0)
## 엔터프라이즈 에이전틱 온톨로지 스튜디오 스타터 팩 (`Agentic Ontology Studio`)

> **고객 데이터 성숙도별 3-Track 설정, BigQuery Property Graph & Cloud Spanner Graph 듀얼 어댑터, 8대 모듈형 MCP 스위트(Stage 1~5 파이프라인 MCP + Runtime 도메인 MCP 3종), 그리고 Light Enterprise 디자인 표준을 갖춘 통합 AI 스튜디오(`0. Overview` ~ `Stage 5. Lineage & Eval`) 스타터 킷**

본 저장소는 기업의 정형 데이터웨어하우스(BigQuery DW / Cloud Spanner)와 비정형 업무 규정(Markdown/PDF)을 통합하여, 누구나 자신의 데이터 상황(`Track 1 Lite` / `Track 2 Standard` / `Track 3 Full-Stack`)과 타깃 그래프 엔진(`bigquery` / `spanner`)만 `config/starter_config.json`에서 지정하면 즉시 **3-Layer LLM-Wiki (`Stage 2`)**, **듀얼 Property Graph (`Stage 3`)**, **8대 모듈형 MCP & AI FDE 에이전트 (`Stage 4`)**, 그리고 **4-Tier 리니지 & 바운더리 회귀 평가 (`Stage 5`)**를 구동할 수 있는 참조 스타터 패키지입니다.

---

## 라이브 포털 바로 보기 (Live Demo)

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Agentic%20Ontology%20Studio-0071e3?logo=googlecloud&logoColor=white)](https://agentic-ontology-starter-924723860007.asia-northeast3.run.app)
[![Runtime](https://img.shields.io/badge/Runtime-Cloud%20Run%20(asia--northeast3)-059669?logo=googlecloud&logoColor=white)](https://agentic-ontology-starter-924723860007.asia-northeast3.run.app)
[![Design](https://img.shields.io/badge/Design-Apple%2FGoogle%20Light%20Enterprise-0d9488)](#)

**➔ [Agentic Ontology Studio 라이브 포털 열기](https://agentic-ontology-starter-924723860007.asia-northeast3.run.app)**

저장소를 복제하거나 설치하지 않고도 **6-Tab (5-Stage 직관 매핑) Light Enterprise 스튜디오**의 실제 화면과 인터랙티브 그래프·MCP 실행기를 브라우저에서 바로 확인할 수 있습니다.

| 스튜디오 탭 (6-Tab) | 라이브 링크 | 연계 방법론 & MCP | 화면에서 확인할 수 있는 핵심 기능 |
| :--- | :---: | :--- | :--- |
| **`0. Overview`** | [열기](https://agentic-ontology-starter-924723860007.asia-northeast3.run.app/?tab=overview) | 전체 아키텍처 & `starter_config.json` | 3-Track / BigQuery·Spanner 엔진 전환기, 5-Stage 실행 보드(`▶ Stage 1~5 MCP`), 3-Band 하이브리드 아키텍처 다이어그램, 피처 갭 매트릭스 |
| **`Stage 1. Asset`** | [열기](https://agentic-ontology-starter-924723860007.asia-northeast3.run.app/?tab=stage1) | [Stage 1 가이드](methodology/01_asset_discovery_and_scoping_ko.md)<br>`mcp_stage1_asset_discovery` | 비식별화 정형 마스터 원장 4종(`customer_contracts`, `devices`, `plans`, `subsidies`) + 정책 가이드 2종 인벤토리 및 6:4 실시간 데이터 인스펙터 |
| **`Stage 2. Wiki & Semantic Graph`** | [열기](https://agentic-ontology-starter-924723860007.asia-northeast3.run.app/?tab=stage2) | [Stage 2 가이드](methodology/02_semantic_modeling_and_okf_ko.md)<br>`mcp_stage2_wiki_and_semantic` | 좌: Karpathy 3-Layer LLM-Wiki(`summary`/`entities`/`concepts`/`rules`) & SHA-256 청크 · 우: `vis-network` 시맨틱 그래프(`Entity=Node`, `Concept=Edge`, Sky Blue 허브 `#0284c7`) |
| **`Stage 3. Property Graph`** | [열기](https://agentic-ontology-starter-924723860007.asia-northeast3.run.app/?tab=stage3) | [Stage 3 가이드](methodology/03_property_graph_and_gql_ko.md)<br>`mcp_stage3_property_graph` | 상단 `BigQuery Property Graph (SQL:2023)` ↔ `Cloud Spanner Graph (ISO GQL)` 실시간 전환기 · 좌: 물리 Property Graph 토폴로지(Teal 허브 `#0d9488`) · 우: 듀얼 DDL 및 멀티홉 GQL 실행기 |
| **`Stage 4. Agent & MCP`** | [열기](https://agentic-ontology-starter-924723860007.asia-northeast3.run.app/?tab=stage4) | [Stage 4 가이드](methodology/04_multi_domain_mcp_and_agent_ko.md)<br>`mcp_stage4_agent_orchestration` | 좌: **8대 모듈형 MCP 스위트**(Stage 1~5 파이프라인 MCP + Runtime 도메인 MCP 3종, 세부 `steps` 선택 실행) · 우: AI FDE 하위 목표 분해 및 근거 앵커 추론 콘솔 |
| **`Stage 5. Lineage & Eval`** | [열기](https://agentic-ontology-starter-924723860007.asia-northeast3.run.app/?tab=stage5) | [Stage 5 가이드](methodology/05_enterprise_studio_and_deployment_ko.md)<br>`mcp_stage5_lineage_and_eval` | 상단: 4-Tier 엔드투엔드 데이터 리니지(Raw ➔ OKF ➔ Graph ➔ Agent) · 하단: Golden CQ 5종 채점표 및 바운더리 질의 10건 회귀 평가(Round 1 `32%` ➔ Round 2 `92%`) |

---

## 1. 3-Track 데이터 성숙도 모델 & 듀얼 그래프 엔진 어댑터 (`config/starter_config.json`)

고객사마다 보유한 데이터 자산과 운영 DB 환경이 다르므로, 코드 수정 없이 [`config/starter_config.json`](config/starter_config.json) 설정만으로 3가지 트랙과 2가지 그래프 엔진을 선택할 수 있습니다:

| 구분 | 설정값 (`starter_config.json`) | 대상 고객 환경 | 활성화 파이프라인 및 특징 |
| :--- | :--- | :--- | :--- |
| **Track 1 · Lite** | `"track": "lite"`<br>`"graph_engine": "none"` | 비정형 규정·약관 문서만 존재하는 환경 | 물리 그래프 DB 구축 없이 **Stage 2 (3-Layer LLM-Wiki & 시맨틱 그래프)**만으로 즉시 에이전트 구동 |
| **Track 2 · Standard** | `"track": "standard"`<br>`"graph_engine": "bigquery"` | 정형 DW 마스터 테이블과 산식 중심 환경 | 정형 원장 4종을 Zero-ETL로 물리 노드로 승격하고 결정론적 산식 MCP(`mcp_calculate_penalty_rule`)로 결합 |
| **Track 3 · Full-Stack** | `"track": "full"`<br>`"graph_engine": "bigquery" \| "spanner"` | 비정형 규정 위키 + 정형 DW 원장 통합 환경 | 3-Layer Wiki(OKF v0.2) + Property Graph(BigQuery 또는 Spanner) + 8대 모듈형 MCP 전주기 가동 |

### BigQuery Property Graph vs. Cloud Spanner Graph 듀얼 어댑터
- **BigQuery Property Graph (`data/output/create_property_graph.sql`)**: 대규모 DW 원장 분석(OLAP), 복제 없는 Zero-ETL 테이블 뷰 투영, `GRAPH_TABLE()` 기반 배치·대화형 하이브리드 추론에 적합합니다.
- **Cloud Spanner Graph (`data/output/create_spanner_graph.sql`)**: 초저지연 온라인 트랜잭션(OLTP), 실시간 다중 홉 탐색 및 고빈도 고객 상담 에이전트 서빙에 적합합니다.

---

## 2. 8대 핵심 모듈형 MCP 아키텍처 (`src/agent/mcp_server.py`)

초기 사용자의 인지 부담을 줄이고 파이프라인 자동화와 런타임 추론을 명확히 분리하기 위해 **8개 핵심 모듈형 MCP**로 구성되어 있습니다. 특히 각 Stage MCP는 `steps=[...]` 파라미터를 통해 원하는 세부 스텝만 선택적으로 실행할 수 있습니다.

| 구분 | MCP 도구명 | 연계 탭 / 단계 | 선택 가능한 모듈형 `steps` | 핵심 역할 |
| :--- | :--- | :---: | :--- | :--- |
| **Stage 1 MCP** | `mcp_stage1_asset_discovery` | `Stage 1. Asset` | `profile_tables`, `scan_guides`, `prune_noise`, `tag_pii_governance` | 원천 테이블(4종)·가이드(2종) 스캔, 노이즈 제외 및 비식별화(`CUST_DEMO_*`) 검증 |
| **Stage 2 MCP** | `mcp_stage2_wiki_and_semantic` | `Stage 2. Wiki & Semantic` | `compile_3layer_wiki`, `extract_hash_anchors`, `bind_semantic_bridges` | 3-Layer LLM-Wiki 컴파일, SHA-256 해시 앵커(`DOC_CHUNK_001~005`) 및 시맨틱 브릿지 생성 |
| **Stage 3 MCP** | `mcp_stage3_property_graph` | `Stage 3. Property Graph` | `promote_dw_nodes`, `synthesize_graph_ddl`, `verify_gql_templates` | Zero-ETL 노드 승격 및 BigQuery / Spanner 듀얼 Property Graph DDL 합성 |
| **Stage 4 MCP** | `mcp_stage4_agent_orchestration` | `Stage 4. Agent & MCP` | `decompose_subgoals`, `dispatch_domain_mcps`, `verify_grounding_anchors` | 복합 질의 하위 목표 분해, 런타임 MCP 체이닝 및 원문 앵커 검증 |
| **Stage 5 MCP** | `mcp_stage5_lineage_and_eval` | `Stage 5. Lineage & Eval` | `build_4tier_lineage`, `run_golden_cq_suite`, `diagnose_boundary_failures` | 4-Tier 데이터 리니지 집계, Golden CQ 5종 및 바운더리 10건 회귀 평가 |
| **Runtime MCP 1** | `mcp_lookup_customer_profile` | `Stage 4` 런타임 | `lookup_contract`, `lookup_device_price`, `lookup_subsidy_policy` | 비식별화 고객 약정 원장(`customer_contracts`), 단말 출고가, 공시지원금 통합 조회 |
| **Runtime MCP 2** | `mcp_calculate_penalty_rule` | `Stage 4` 런타임 | `check_exemptions`, `compute_180d_prorated_clawback`, `compare_24m_tco` | 180일 일할 차액정산 위약금, 시니어·복지 면제 특례, 24개월 공시 vs 선택약정 TCO 산출 |
| **Runtime MCP 3** | `mcp_query_graph_and_wiki` | `Stage 4` 런타임 | `traverse_property_graph`, `fetch_okf_hash_anchor`, `verify_dw_schema` | BigQuery/Spanner 멀티홉 그래프 경로 탐색 및 OKF v0.2 SHA-256 해시 앵커 인출 |

---

## 3. 비식별화 슬림 샘플 데이터셋 (`data/input/` & `data/output/`)

실제 기업 고객 정보나 고유 식별자를 100% 배제하고 합성 식별자(`CUST_DEMO_001` ~ `CUST_DEMO_006`, `CONTRACT_DEMO_101` ~ `CONTRACT_DEMO_106`)로 구성된 슬림 데이터셋이 동봉되어 있습니다:

1. **정형 마스터 테이블 4종 (`data/input/03_tables/`)**:
   - `customer_contracts.csv` (고객 약정 원장 6건: 일반 VIP, 시니어 복지 면제 대상, 군입대 유예 대상, 법인 B2B 등)
   - `devices.csv` (단말기 마스터 4건: Galaxy S26 Ultra 256/512GB, iPhone 16 Pro 256/512GB)
   - `plans.csv` (요금제 마스터 6건: 5G Premier Super/Essential, 5G Slim 45,000원 기준선, 5G Light 등)
   - `subsidies.csv` (공시지원금 정책 5건: 단말×요금제별 공시지원금 및 유통망 지원금)
2. **비정형 정책 가이드 2종 (`data/input/01_guides/`)**:
   - `sample_policy_guide.md` (`DOC_CHUNK_001` ~ `DOC_CHUNK_003`: 180일 기준선 유지 의무 및 일할 위약금 산식)
   - `sample_welfare_exemption_guide.md` (`DOC_CHUNK_004` ~ `DOC_CHUNK_005`: 시니어·군입대 위약금 면제 특례 및 24개월 TCO 비교 규칙)
3. **평가 벤치마크 데이터셋**:
   - `data/input/04_cq/golden_competency_questions.json` (Golden CQ 5문항: `CQ-01` ~ `CQ-05`)
   - `data/output/boundary_benchmark_results.json` (바운더리 경계 질의 10문항 × 5회 반복 결과: Round 1 `32.0%` ➔ Round 2 `92.0%`)

---

## 4. 5단계 표준 방법론 (`methodology/`) & 실습 노트북 (`notebooks/`)

| Stage | 스튜디오 탭 | 국문/영문 방법론 가이드 | 연계 실습 주피터 노트북 |
| :---: | :--- | :--- | :--- |
| **Stage 1** | `Stage 1. Asset` | [01_asset_discovery_and_scoping_ko.md](methodology/01_asset_discovery_and_scoping_ko.md)<br>[01_asset_discovery_and_scoping_en.md](methodology/01_asset_discovery_and_scoping_en.md) | [01_okf_unstructured_agent_ko.ipynb](notebooks/01_okf_unstructured_agent_ko.ipynb)<br>[01_okf_unstructured_agent_en.ipynb](notebooks/01_okf_unstructured_agent_en.ipynb) |
| **Stage 2** | `Stage 2. Wiki & Semantic Graph` | [02_semantic_modeling_and_okf_ko.md](methodology/02_semantic_modeling_and_okf_ko.md)<br>[02_semantic_modeling_and_okf_en.md](methodology/02_semantic_modeling_and_okf_en.md) | [01_okf_unstructured_agent_ko.ipynb](notebooks/01_okf_unstructured_agent_ko.ipynb)<br>[01_okf_unstructured_agent_en.ipynb](notebooks/01_okf_unstructured_agent_en.ipynb) |
| **Stage 3** | `Stage 3. Property Graph` | [03_property_graph_and_gql_ko.md](methodology/03_property_graph_and_gql_ko.md)<br>[03_property_graph_and_gql_en.md](methodology/03_property_graph_and_gql_en.md) | [02_property_graph_and_gql_ko.ipynb](notebooks/02_property_graph_and_gql_ko.ipynb)<br>[02_property_graph_and_gql_en.ipynb](notebooks/02_property_graph_and_gql_en.ipynb) |
| **Stage 4** | `Stage 4. Agent & MCP` | [04_multi_domain_mcp_and_agent_ko.md](methodology/04_multi_domain_mcp_and_agent_ko.md)<br>[04_multi_domain_mcp_and_agent_en.md](methodology/04_multi_domain_mcp_and_agent_en.md) | [03_graph_integration_mcp_agent_ko.ipynb](notebooks/03_graph_integration_mcp_agent_ko.ipynb)<br>[03_graph_integration_mcp_agent_en.ipynb](notebooks/03_graph_integration_mcp_agent_en.ipynb) |
| **Stage 5** | `Stage 5. Lineage & Eval` | [05_enterprise_studio_and_deployment_ko.md](methodology/05_enterprise_studio_and_deployment_ko.md)<br>[05_enterprise_studio_and_deployment_en.md](methodology/05_enterprise_studio_and_deployment_en.md) | [agentic_ontology_ce_walkthrough.ipynb](notebooks/agentic_ontology_ce_walkthrough.ipynb) (All-in-One) |

---

## 5. 빠른 시작 가이드 (Quickstart)

```bash
# 1. 저장소 복제 (Python 3.10+ 표준 라이브러리만으로 즉시 동작)
git clone https://github.com/seanjungG/agentic-ontology-starter.git
cd agentic-ontology-starter

# 2. 원클릭 파이프라인 실행 (OKF Wiki + BigQuery/Spanner 듀얼 DDL + Golden CQ 검증)
python3 run_pipeline.py

# 3. Light Enterprise 스튜디오 서버 실행 (기본 포트 8080)
PORT=8088 python3 -m src.web.studio_server
# 브라우저에서 http://127.0.0.1:8088 접속
```
