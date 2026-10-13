# Interactive Jupyter Notebooks — Agentic Ontology Starter (v2.2 Resource-Connected Edition)

본 디렉터리는 **Agentic Ontology Starter Pack v2.2.0 (Resource-Connected Edition)**의 **리소스 직결형 아키텍처(`OntologyResourceConnector` + 커스터마이징 도메인 비즈니스 도구 3종 `DomainMcpServer`)** 및 **5-Stage × 11-Step (12-Tab 기준 스튜디오 ↔ 6-Tab 스타터 포털) 엔터프라이즈 에이전틱 온톨로지 방법론**을 BigQuery(`seanjung-poc.starter_ontology_dw`), BigQuery Property Graph(`STARTER_ONTOLOGY_GRAPH`), Cloud Spanner Graph(`starter-spanner`), Vertex AI Gemini(`gemini-3.8-flash`) 실환경에서 단계별로 실행·검증하는 **12종의 인터랙티브 Jupyter 노트북(한국어 6종 / 영어 6종)**을 제공합니다.

---

## 1. 아키텍처 핵심 원칙 (Code Exposure Boundary)

1. **Ready-to-Use 리소스 커넥터 (`src/resource_connector.py`, `OntologyResourceConnector`)**:
   - 무거운 내부 온톨로지 빌더 MCP 도구는 플랫폼 계층으로 추상화하여 제외하고, 이미 준비된 **BigQuery DW(10개 테이블)**, **Property Graph(`STARTER_ONTOLOGY_GRAPH`)**, **GCS 3-Layer OKF 위키(`summary/entities/concepts/rules.md`)**, **비즈니스 규칙(`RULE_*`) 및 워크플로(`W1~W3`)**, **Cloud Spanner Graph**에 즉시 연결합니다.
2. **커스터마이징 대상 도메인 비즈니스 도구 3종 (`src/agent/mcp_server.py`, `DomainMcpServer`)**:
   - `mcp_lookup_customer_profile`: 고객 약정 · 단말 출고가 · 공시/추가지원금 원장 조회
   - `mcp_calculate_penalty_rule`: 시니어 특례 면제(`RULE_WELFARE_EXEMPT`) · 180일 일할 위약금(`RULE_SIX_PLAN_180D`) · 24개월 TCO(`RULE_TCO_24M`) 결정론적 SQL 산출
   - `mcp_query_graph_and_wiki`: `STARTER_ONTOLOGY_GRAPH` 멀티홉 `GRAPH_TABLE` 탐색 및 `DOC_CHUNK_*` SHA-256 해시 앵커 조인

---

## 2. Stage 0 ~ 5 한/영 노트북 12종 인덱스 (1:1 매핑)

| Stage | 스타터 포털 탭 | 연결된 GCP 리소스 & 노출 코드 | 한국어 노트북 (`ko/`) | 영문 노트북 (`en/`) |
| :---: | :--- | :--- | :--- | :--- |
| **Stage 0** | [`0. Overview`](https://agentic-ontology-starter-924723860007.asia-northeast3.run.app/?tab=overview) | `src/resource_connector.py` · 기준점 허브 · 코드 노출 경계 · Stage 0~5 통합 워크스루 | [**`ko/stage0_overview_walkthrough_ko.ipynb`**](ko/stage0_overview_walkthrough_ko.ipynb) | [**`en/stage0_overview_walkthrough_en.ipynb`**](en/stage0_overview_walkthrough_en.ipynb) |
| **Stage 1** | [`Stage 1. Asset`](https://agentic-ontology-starter-924723860007.asia-northeast3.run.app/?tab=stage1) | `seanjung-poc.starter_ontology_dw` (10 Tables) · `stage1_resource_check` · Golden CQ 5종 | [**`ko/stage1_asset_and_cq_ko.ipynb`**](ko/stage1_asset_and_cq_ko.ipynb) | [**`en/stage1_asset_and_cq_en.ipynb`**](en/stage1_asset_and_cq_en.ipynb) |
| **Stage 2** | [`Stage 2. Wiki & Semantic`](https://agentic-ontology-starter-924723860007.asia-northeast3.run.app/?tab=stage2) | `gs://seanjung-poc-starter-ontology/ontology/` · 3-Layer OKF 위키 · `RULE_*` · `W1~W3` | [**`ko/stage2_wiki_and_semantic_graph_ko.ipynb`**](ko/stage2_wiki_and_semantic_graph_ko.ipynb) | [**`en/stage2_wiki_and_semantic_graph_en.ipynb`**](en/stage2_wiki_and_semantic_graph_en.ipynb) |
| **Stage 3** | [`Stage 3. Property Graph`](https://agentic-ontology-starter-924723860007.asia-northeast3.run.app/?tab=stage3) | `STARTER_ONTOLOGY_GRAPH` (BigQuery SQL:2023 & Spanner ISO GQL) · `src/gcp_client.py` | [**`ko/stage3_property_graph_bigquery_spanner_ko.ipynb`**](ko/stage3_property_graph_bigquery_spanner_ko.ipynb) | [**`en/stage3_property_graph_bigquery_spanner_en.ipynb`**](en/stage3_property_graph_bigquery_spanner_en.ipynb) |
| **Stage 4** | [`Stage 4. Agent & Tools`](https://agentic-ontology-starter-924723860007.asia-northeast3.run.app/?tab=stage4) | 도메인 비즈니스 도구 3종 (`src/agent/mcp_server.py`) · AI FDE (`src/agent/reasoning_engine.py`, `Gate G2-W`) | [**`ko/stage4_agent_and_mcp_execution_ko.ipynb`**](ko/stage4_agent_and_mcp_execution_ko.ipynb) | [**`en/stage4_agent_and_mcp_execution_en.ipynb`**](en/stage4_agent_and_mcp_execution_en.ipynb) |
| **Stage 5** | [`Stage 5. Lineage & Eval`](https://agentic-ontology-starter-924723860007.asia-northeast3.run.app/?tab=stage5) | 6-Layer 데이터 리니지 DAG (`src/lineage_service.py`) · Golden CQ 5건 · Boundary 50회 평가 | [**`ko/stage5_lineage_and_evaluation_ko.ipynb`**](ko/stage5_lineage_and_evaluation_ko.ipynb) | [**`en/stage5_lineage_and_evaluation_en.ipynb`**](en/stage5_lineage_and_evaluation_en.ipynb) |

---

## 3. 노트북 생성 및 무결성 검증 명령어

```bash
# 12종 노트북 일괄 재생성 및 NBFormat v4.5 + Base64 PNG 첨부 무결성 검증
python3 notebooks/generate_notebooks.py
python3 notebooks/validate_and_pack_notebooks.py
```
