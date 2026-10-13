# 01_prod.md — Agentic Ontology Starter (v2.2 Resource-Connected Edition) Product Charter

## 1. 제품 비전 및 아키텍처 기준점 (Product Vision & Reference Standard)
**Agentic Ontology Starter (AOS v2.2)**는 엔터프라이즈 기준점 스튜디오인 **LG U+ 공시지원금 & 결합 온톨로지 스튜디오(12-Tab)** 및 **LG생활건강 화장품 표시광고 실증 스튜디오(12-Tab)**의 **6-Layer 표준 아키텍처(`5-Stage × 11-Step`, `P1/P2/P3 × W1/W2/W3 × Gate G2-W`)**를 그대로 계승하되, 무거운 내부 MCP 빌더 파이프라인은 플랫폼 계층으로 **완전 추상화(Excluded & Abstracted)**하고 **즉시 사용 가능한(Ready-to-Use) Google Cloud 온톨로지 리소스**에 직결하는 **Resource-Connected Starter Kit**입니다.

| 구분 | 스튜디오 명칭 | 라이브 URL | 핵심 역할 |
| :--- | :--- | :--- | :--- |
| **Starter (6-Tab)** | **Agentic Ontology Starter v2.2** | `https://agentic-ontology-starter-924723860007.asia-northeast3.run.app/` | Ready-to-Use GCP 리소스에 직결된 6-Tab 실습·커스터마이징 포털 |
| **Reference #1 (12-Tab)** | **LG U+ 공시지원금 & 결합 스튜디오** | `https://agentic-ontology-studio-lguplus-mcp-924723860007.asia-northeast3.run.app/` | 통신 도메인 12-Tab 풀 플랫폼 기준점 |
| **Reference #2 (12-Tab)** | **LG생활건강 화장품 표시광고 스튜디오** | `https://agentic-ontology-studio-hnh-mcp-924723860007.asia-northeast3.run.app/` | 규제·컴플라이언스 도메인 12-Tab 풀 플랫폼 기준점 |

---

## 2. 코드 노출 경계 (Code Exposure Boundary)
1. **추상화/제외 영역 (Excluded from Starter Runtime)**:
   - 내부 온톨로지 빌더 MCP 서버(`mcp_builder_*` / `mcp_stage1..5`) 및 무거운 문서 파서·컴파일러는 스타터 런타임 카탈로그에서 제외됩니다.
   - 컴파일된 결과물은 BigQuery(`seanjung-poc.starter_ontology_dw`), GCS(`gs://seanjung-poc-starter-ontology/ontology/`), Spanner(`starter-spanner`)에 **Ready-to-Use 리소스**로 준비되어 있습니다.
2. **스타터 노출 핵심 코드 4종 (Exposed & Customizable)**:
   - [`src/resource_connector.py`](src/resource_connector.py): Stage 1~5 Ready-to-Use GCP 리소스 직결 커넥터 (`OntologyResourceConnector`)
   - [`src/gcp_client.py`](src/gcp_client.py): BigQuery SQL / SQL:2023 `GRAPH_TABLE` / Cloud Spanner GQL / GCS / Vertex AI `gemini-3.8-flash` 클라이언트
   - [`src/agent/mcp_server.py`](src/agent/mcp_server.py): 커스터마이징 대상 **도메인 비즈니스 도구 3종** (`mcp_lookup_customer_profile`, `mcp_calculate_penalty_rule`, `mcp_query_graph_and_wiki`)
   - [`src/agent/reasoning_engine.py`](src/agent/reasoning_engine.py): 하위 목표 분해 · 도메인 도구 체이닝 · `Gate G2-W` 감사 추론 엔진

---

## 3. 런타임 GCP 환경 기준값 (`seanjung-poc`)
- **GCP Project / Region**: `seanjung-poc` / `asia-northeast3`
- **BigQuery Dataset**: `seanjung-poc.starter_ontology_dw` (10 Tables: 마스터 4종 + `tb_doc_chunks` + `tb_domain_rules` + 엣지 4종 + 평가 2종)
- **BigQuery Property Graph**: `seanjung-poc.starter_ontology_dw.STARTER_ONTOLOGY_GRAPH` (ISO SQL:2023 `GRAPH_TABLE`)
- **Cloud Spanner Graph**: `starter-spanner` / `starter_ontology_db` / `STARTER_ONTOLOGY_GRAPH` (100 PU, ISO GQL)
- **GCS 3-Layer OKF Wiki & Rules**: `gs://seanjung-poc-starter-ontology/ontology/` (`summary.md`, `entities.md`, `concepts.md`, `rules.md`, `business_rules.json`, `business_workflows.json`, `workflow_cqs.json`)
- **Default Serving Model**: Vertex AI `gemini-3.8-flash`
