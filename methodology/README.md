# Enterprise Agentic Ontology Methodology & Implementation Process
## 엔터프라이즈 에이전틱 온톨로지 구축 방법론 및 실행 프로세스 가이드

> **라이브 포털**: 설치 없이 [Agentic Ontology Studio 포털](https://agentic-ontology-starter-924723860007.asia-northeast3.run.app)에서 `0. Overview` ~ `8. AI FDE` 전 구간 화면을 바로 확인할 수 있습니다.

본 디렉토리는 정형 데이터웨어하우스(BigQuery DW)와 비정형 업무 가이드(MHTML/PDF)를 단일 지식 체계로 통합하여, 근거 출처 기반 응답(Grounded Answering)과 결정론적 계산 신뢰성을 목표로 하는 **에이전틱 지식 온톨로지(Agentic Knowledge Ontology)**를 엔드투엔드로 구축·배포하기 위한 표준 방법론과 실행 프로세스를 제공합니다.

특정 고객사의 환경에 종속되지 않고 누구나 데이터만 교체하여 재구성할 수 있도록 모든 원천 자산과 테이블 명칭을 표준 비즈니스 아키텍처 수준으로 1단계 추상화(예: `[단말기 카탈로그 마스터 BQ 테이블]`, `[고객 상담가이드 비정형 매뉴얼]`)하여 수록하였습니다.

---

### 1. 진화적 온톨로지 통합 아키텍처 (Evolutionary Architecture Journey)

본 방법론의 핵심은 초기 비정형 문서 프로토타이핑에서 출발하여 엔터프라이즈 프로덕션 수준의 물리 그래프와 에이전트 추상화 계층으로 발전해 나가는 **4단계 진화 여정(Evolutionary Journey)**에 있습니다:

```mermaid
flowchart TD
    subgraph TrackA ["Track A: 비정형 지식 체계화 & 선행 4. Wiki Agent (Unstructured First on GCS)"]
        RawDoc["1. Asset: 비정형 업무 가이드 & SOP<br/>(MHTML / PDF)"] --> OKF["2. Knowledge Viewer: Karpathy 3-Layer LLM-Wiki<br/>(.okf.md & 담백한 원본 YAML Frontmatter)"]
        OKF --> Semantic["3. Ontology Semantic: 5대 요소 추출 & 시맨틱 브릿지"]
        Semantic --> WikiAgent["4. Wiki Agent (선행 GCS 에이전트)<br/>DB 구축 없이 GCS 위키 기반 16대 규정/산식 CQ 즉시 추론"]
    end

    subgraph TrackB ["Track B: 정형 원장 프로파일링 (Structured DW)"]
        DWTable["1. Asset: BigQuery DW 원장 테이블<br/>(단말기, 요금제, 공시지원금, 약정 원장)"] --> SchemaProfile["Domain Pruning (35 ➔ 7 핵심 원장) & PK·FK 분석"]
    end

    subgraph TrackC ["Track C: 5. Bigquery Graph & 6. BQG Agent (BQG Integration & Anti-Redundancy)"]
        WikiAgent & SchemaProfile --> BQGIntegration{"5. Bigquery Graph 통합<br/>(SQL:2023 CREATE PROPERTY GRAPH)"}
        BQGIntegration -->|정형 테이블| DWNode["물리 DW 노드 직접 승격 (Zero-ETL)<br/>(Device, Plan, SubsidyLedger 등)"]
        BQGIntegration -->|시맨틱 브릿지 결합| BQGAgent["6. BQG Agent (그래프 추론 에이전트)<br/>NL2GQL 멀티홉 원장 탐색 + 위키 결합 (20/20 CQ 해결)"]
    end

    subgraph TrackD ["Track D & E: 7. Lineage & 8. AI FDE (Agentic Ontology Studio)"]
        BQGAgent --> Lineage["7. Lineage: 4-Tier 엔터프라이즈 리니지<br/>(39 Nodes / 60 Edges, < 5ms 인메모리 즉시 로딩)"]
        Lineage --> Studio["8. AI FDE & Agentic Ontology Studio<br/>(0. Overview ~ 8. AI FDE 통합 스튜디오: 전체 스텝 ➔ 아키텍처 ➔ 피처갭 ➔ 성능/결과)"]
    end

    TrackA --> TrackC
    TrackB --> TrackC
    TrackC --> TrackD
```

#### 4대 진화 축 및 8단계 스튜디오(`Agentic Ontology Studio`, `1. Asset` ~ `8. AI FDE`) 흐름의 핵심 원리
1. **비정형 우선 지식화 및 선행 `4. Wiki Agent` 구축 (`1. Asset` ➔ `2. Knowledge Viewer` ➔ `3. Ontology Semantic` ➔ `4. Wiki Agent`)**:
   - 비정형 업무 매뉴얼을 파싱하여 OKF(Open Knowledge Format v0.2)로 변환하고, 담백한 원본 YAML Frontmatter(`---\n...\n---`)와 Karpathy 3-Layer LLM-Wiki 구조로 재구성하여 GCS 버킷 상에 배포합니다.
   - 물리 그래프 DB 구축 전이라도, `3. Ontology Semantic` 정의 직후 **`4. Wiki Agent` (GCS 기반 선행 에이전트)**를 즉시 기동하여 위약금 산식·예외 조항 등 16대 규정 중심 CQ(`[GCS Preferred]`)를 1차 해결합니다.
2. **정형 DW 원장 프루닝 및 `5. Bigquery Graph` 구축 (`Track B & C`)**:
   - 데이터웨어하우스 내 35개 원천 테이블 중 노이즈를 80% 제거(Domain Pruning: 35 ➔ 7)하고, 핵심 마스터 테이블을 데이터 복제 없이(Zero-ETL) **`5. Bigquery Graph` (`SQL:2023 Property Graph`)** 노드로 직접 승격합니다.
3. **`6. BQG Agent`로의 진화 (`4. Wiki Agent` ➔ `6. BQG Agent`)**:
   - 선행 구축된 `4. Wiki Agent`의 규정 해석 능력에 `GRAPH_TABLE()` 실시간 멀티홉 원장 탐색(`NL2GQL`)을 결합한 **`6. BQG Agent`**를 통해, 대리점 정산·다회선 결합·단말 출고가 비교를 포함한 20대 골든 CQ 전수(20/20 PASS)를 해결합니다.
4. **4-Tier 즉시 리니지(`7. Lineage`) 및 멀티도메인 `8. AI FDE` (`Agentic Ontology Studio`)**:
   - 비동기 인메모리 캐싱으로 `< 5ms`에 즉시 로딩되는 4-Tier 데이터 리니지(`7. Lineage`)와 11종 도메인 MCP 기반 자율 온톨로지 엔지니어링(`8. AI FDE`)을 **`Agentic Ontology Studio`** 단일 화면에서 제공합니다.

---

### 2. 전체 문서 구성 (Document Structure)

#### 마스터 총괄 가이드
| 문서명 (Master Document) | 언어 (Language) | 주요 내용 및 목적 |
| :--- | :---: | :--- |
| [METHODOLOGY_KO.md](./METHODOLOGY_KO.md) | 한국어 (Korean) | 진화적 통합 아키텍처, 5단계 표준 라이프사이클 마스터 명세서, RACI 매트릭스, 종합 품질 게이트 |
| [METHODOLOGY_EN.md](./METHODOLOGY_EN.md) | 영어 (English) | Evolutionary Architecture Framework, Master 5-Stage Specification, RACI Matrix, Quality Gates |

#### 5대 단계별 세부 하부 실행 명세서 (Detailed Stage Sub-Documents)
| 단계 (Stage) | 한국어 상세 명세서 (KO) | 영어 상세 명세서 (EN) | 핵심 다이어그램 및 기술 스펙 |
| :--- | :--- | :--- | :--- |
| **Stage 1: 자산 탐색 및 거버넌스 수집** | [01_asset_discovery_and_scoping_ko.md](./01_asset_discovery_and_scoping_ko.md) | [01_asset_discovery_and_scoping_en.md](./01_asset_discovery_and_scoping_en.md) | 자산 스코핑 데이터플로우, 노이즈 Pruning 헌장, 20대 Golden CQ 정의, Dataplex 태깅 |
| **Stage 2: 시맨틱 온톨로지 모델링 & LLM-Wiki** | [02_semantic_modeling_and_okf_ko.md](./02_semantic_modeling_and_okf_ko.md) | [02_semantic_modeling_and_okf_en.md](./02_semantic_modeling_and_okf_en.md) | 비정형 파싱, Karpathy 3-Layer LLM-Wiki, GCS 프로토타이핑, 2-Layer 안티 리던던시 |
| **Stage 3: BigQuery 그래프 엔지니어링** | [03_property_graph_and_gql_ko.md](./03_property_graph_and_gql_ko.md) | [03_property_graph_and_gql_en.md](./03_property_graph_and_gql_en.md) | SQL:2023 Property Graph DDL, DW 노드 승격 & 청크/정책 브릿지, 다중 홉 GQL 템플릿 |
| **Stage 4: 멀티도메인 MCP 스위트 구축** | [04_multi_domain_mcp_and_agent_ko.md](./04_multi_domain_mcp_and_agent_ko.md) | [04_multi_domain_mcp_and_agent_en.md](./04_multi_domain_mcp_and_agent_en.md) | 11종 MCP 도구셋(비즈니스/엔지니어링), 에이전트 추상화 계층, 동적 체이닝 시퀀스 |
| **Stage 5: 스튜디오 구축 및 배포** | [05_enterprise_studio_and_deployment_ko.md](./05_enterprise_studio_and_deployment_ko.md) | [05_enterprise_studio_and_deployment_en.md](./05_enterprise_studio_and_deployment_en.md) | 5단계 E2E 데이터 라이프사이클 스튜디오(Overview/레지스트리/Knowledge Viewer/정형/하이브리드 BQG/AI FDE/CQ), 4-Tier 리니지, 무중단 배포 |

### 3. GCP Native First 아키텍처 원칙 및 커스텀 확장 체계 (GCP Native First vs Custom Extension)

본 방법론은 **"Google Cloud Native First (GCP 네이티브 기능 우선 채택)"**을 절대 강령으로 삼습니다. 즉, 관리형 인프라의 확장성, 보안(IAM, Model Armor, Audit Logs), 표준 규격(OKF, SQL:2023, MCP)을 최대한 레버리지하고, GCP 네이티브 기능만으로 해결 불가능한 도메인 고유 비즈니스 연산 및 그래프 중복 제거 영역에 한해서만 커스텀 확장을 적용합니다.

#### 3.1 계층별 네이티브 스펙 vs 커스텀 확장 비교 매트릭스

| 아키텍처 계층 (Layer) | Google Cloud Native Spec / Service | 공식 오픈소스 / 엔드포인트 레퍼런스 | 독자 개발 커스텀 확장 (Custom Extension) | 커스텀 개발 사유 및 기술적 당위성 |
| :--- | :--- | :--- | :--- | :--- |
| **1. Data Lake & DW** | • BigQuery Managed Tables<br>• Cloud Storage (GCS)<br>• BigQuery SQL:2023 Property Graph | • [BigQuery Documentation](https://cloud.google.com/bigquery)<br>• [Cloud Storage Documentation](https://cloud.google.com/storage) | • 2-Layer 안티 리던던시 Graph DDL 컴파일러 (`pipeline/graph_builder.py`)<br>• 시맨틱 브릿지 엣지 (`APPLIES_TO`, `CALCULATES`) | DW 원장 테이블을 그래프 노드로 직접 승격하고 텍스트 중복 엔티티를 프루닝하여 저장 공간 및 쿼리 비용 80% 절감 |
| **2. Catalog & Semantics** | • Dataplex Knowledge Catalog<br>• Open Knowledge Format (OKF v0.2)<br>• Custom Aspect Types & Entries | • [Knowledge Catalog GitHub](https://github.com/GoogleCloudPlatform/knowledge-catalog)<br>• [`references/knowledge-catalog/okf`](https://github.com/GoogleCloudPlatform/knowledge-catalog/tree/main/okf) | • 결정론적 SHA-256 비정형 청커 (`DocChunk`)<br>• Karpathy 3-Layer LLM-Wiki 컴파일러 (`data/llm_wiki/`)<br>• GCS 프로토타입 매니페스트 생성기 | 비정형 PDF/MHTML의 시각적 구조를 무손실 보존하고, BQ 적재 전 GCS 기반 온톨로지 지식망 선행 검증 |
| **3. MCP & Tooling** | • Dataplex KC Remote MCP (`search_entries`, `lookup_entry`, `lookup_context`)<br>• BigQuery Remote MCP (`list_dataset_ids`, `get_table_info`, `execute_sql_readonly`) | • KC Remote MCP: `https://dataplex.googleapis.com/mcp`<br>• BQ Remote MCP: `https://bigquery.googleapis.com/mcp`<br>• [GCP Remote MCP Docs](https://docs.cloud.google.com/dataplex/docs/use-remote-mcp) | • Tier 3 Domain Ontology MCP Server (비즈니스 5종 + 엔지니어링 6종 도구)<br>• BigQuery Property Graph GQL 전용 실행기 | **BigQuery Remote MCP의 결정적 제약사항(GQL `GRAPH_TABLE()` 미지원) 극복** 및 복잡한 SQL/GQL 스키마로부터 AI 에이전트 격리·보호 |
| **4. Agent & Orchestration** | • Google Agent Development Kit (ADK Python 2.0)<br>• ADK Web UI (Angular)<br>• Google Cloud Data Agent Kit (Conversational Analytics API)<br>• Vertex AI Gemini 3.8 Flash | • [ADK Python GitHub](https://github.com/google/adk-python)<br>• [ADK Web GitHub](https://github.com/google/adk-web)<br>• [Conversational Analytics API](https://docs.cloud.google.com/gemini/docs/conversational-analytics-api/overview) | • AI FDE 동적 다중 하위 목표 분해 엔진 (`fdeAgentEngine.py`)<br>• 크로스도메인 시퀀셜 체이닝 (`Data Hand-off`, `Intermediate Observation`) | 정적 1회 질의를 넘어 비즈니스 룰과 물리 DW 원장 실측치를 교차 검증하는 자율 추론 사이클 구현 |
| **5. Presentation & Studio** | • Google Cloud Run (Serverless Container)<br>• Google Cloud Logging / Monitoring | • [Cloud Run Documentation](https://cloud.google.com/run) | • 4대 멀티뷰 엔터프라이즈 스타터 스튜디오 (`src/web/studio_server.py`)<br>• 2D SVG 인터랙티브 토폴로지 맵 & DDL 뷰어<br>• 20대 Golden CQ 결정론적 평가 하네스 | 0 의존성 경량 단일 포트(8088)에서 엔드투엔드 거버넌스, 그래프, 에이전트, CQ 성능을 원스톱 검증 |

#### 3.2 핵심 공식 레퍼런스 저장소 (Official Reference Repositories)
- **Google Cloud Knowledge Catalog (Dataplex / OKF)**:
  - GitHub: `https://github.com/GoogleCloudPlatform/knowledge-catalog`
  - 핵심 스펙: Open Knowledge Format (`okf/bundles/`), Custom Aspect Types, Auto-Enrichment Samples
- **Google Agent Development Kit (ADK Python 2.0)**:
  - GitHub: `https://github.com/google/adk-python`
  - 핵심 모듈: Workflow Runtime, Task API, Data Agent Integrations (`contributing/samples/integrations/data_agent`), FunctionTool
- **Google ADK Web UI**:
  - GitHub: `https://github.com/google/adk-web`
  - 프론트엔드: Angular 기반 엔터프라이즈 대화형 에이전트 웹 인터페이스
- **Google Cloud Remote MCP Server 명세**:
  - Dataplex KC Remote MCP: `https://dataplex.googleapis.com/mcp` (`https://docs.cloud.google.com/dataplex/docs/use-remote-mcp`)
  - BigQuery Remote MCP: `https://bigquery.googleapis.com/mcp` (`https://docs.cloud.google.com/bigquery/docs/use-bigquery-mcp`)
  - 제약사항: `execute_sql_readonly`는 Graph Query Language(GQL)를 지원하지 않음 ➔ 커스텀 실행 계층 필수

---

### 4. 방법론 활용 및 실행 순서
1. **착수 및 스코핑**: [Stage 1 가이드](./01_asset_discovery_and_scoping_ko.md)를 따라 비즈니스 경계와 20대 Golden CQ를 확정합니다.
2. **비정형 체계화 및 LLM-Wiki 프로토타이핑**: [Stage 2 가이드](./02_semantic_modeling_and_okf_ko.md)를 통해 비정형 텍스트 청킹, OKF 변환 및 Karpathy 3-Layer LLM-Wiki를 GCS에 프로토타이핑합니다.
3. **물리 그래프 결합 및 안티 리던던시**: [Stage 3 가이드](./03_property_graph_and_gql_ko.md)에 따라 BigQuery Property Graph DDL을 정의하고, DW 테이블을 물리 노드로 승격하며 비정형은 청크/규칙만 결합합니다.
4. **도메인 MCP 추상화 및 에이전트 오케스트레이션**: [Stage 4 가이드](./04_multi_domain_mcp_and_agent_ko.md)를 기반으로 에이전트가 호출할 11종 도메인 MCP 도구 및 동적 체이닝을 구성합니다.
5. **멀티뷰 스튜디오 검증 및 프로덕션 릴리스**: [Stage 5 가이드](./05_enterprise_studio_and_deployment_ko.md)에 따라 멀티뷰 스튜디오에서 20대 Golden CQ 루브릭 평가와 바운더리 질의 회귀 검증(`9. Evaluation`)을 마치고 배포합니다.
6. **4대 산업군 실무 케이스 템플릿 참조**: [인더스트리 케이스 템플릿](../industry_cases/README.md)에 수록된 스마트 제조(포스코, 현대차), 핀테크·금융(카카오뱅크, 토스), 유통·이커머스(GS리테일, CJ대한통운/올리브영), 통신·미디어(SKT, KT) 8대 엔터프라이즈 템플릿 및 DDL/샘플 데이터/SOP 문서를 즉시 복제·활용합니다.
