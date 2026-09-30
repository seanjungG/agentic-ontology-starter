# Stage 3. Property Graph·GQL

> 스튜디오 [`Stage 3. Property Graph`](https://agentic-ontology-starter-924723860007.asia-northeast3.run.app/?tab=stage3) · MCP `mcp_stage3_property_graph` · 노트북 [stage3_property_graph_bigquery_spanner_ko.ipynb](../../notebooks/ko/stage3_property_graph_bigquery_spanner_ko.ipynb) · [English](../en/03_stage3_property_graph_en.md) · [전체 방법론](./METHODOLOGY_KO.md)

## 목적

Stage 1·2에서 적재한 테이블을 복사하지 않고 그대로 그래프의 노드·엣지로 선언한다.
에이전트는 `GRAPH_TABLE` 질의 한 번으로 여러 테이블을 따라가며 답의 경로(약정·단말 → 요금제 ← 규칙 → 근거 청크)를 얻는다.

## 엔진 지원 범위 및 Graph Fabric 연동

| 엔진 / 모드 | 스타터에서 지원하는 것 | 특징 및 권장 용도 |
| :--- | :--- | :--- |
| **BigQuery Property Graph (`bigquery`, 기본)** | DDL 생성(`create_property_graph.sql`), BigQuery에서 DDL 실행, 에이전트 및 8종 MCP의 `GRAPH_TABLE` 조회 | Zero-ETL 무복제 논리 그래프, TB~PB급 분석, 유휴 비용 0원 |
| **Cloud Spanner Graph (`spanner`, 선택)** | Terraform Opt-in 프로비저닝(`starter-spanner`, 100 PU, `starter_ontology_db`), 10개 테이블 적재, `STARTER_ONTOLOGY_GRAPH` DDL 적용, 에이전트 및 8종 MCP 실시간 GQL 조회 | 인덱스 포인터 기반 수십~수백 ms 초저지연 온라인 멀티홉 탐색 (`p50 ~120ms`) |
| **Graph Fabric 연합 (`both` 모드)** | 양대 엔진 동시 적재·배포, N-run `p50/p95` 지연 시간 비교 벤치마크, BigQuery `EXTERNAL_QUERY(spanner_fabric_conn)` 연합 조인 | Spanner 실시간 그래프 탐색 결과와 BigQuery 문서 청크(`tb_doc_chunks`)를 복제 없이 단일 SQL로 조인 |

> **운영 환경 동기화 패턴 (Production Sync)**:
> - **BigQuery → Spanner (Reverse ETL)**: BigQuery 배치 집계 결과를 온라인 서빙 그래프로 내보낼 때는 BigQuery `EXPORT DATA` 또는 Dataflow `BigQueryToSpanner` 템플릿을 사용한다.
> - **Spanner → BigQuery (Change Streams)**: 온라인 트랜잭션 원장의 실시간 변경분을 분석용 BigQuery DW로 반영할 때는 **Spanner Change Streams → Dataflow → BigQuery** CDC 파이프라인을 사용한다.

## 입력

`terraform/bigquery.tf` 및 `terraform/spanner.tf`로 만든 10개 테이블 (Stage 1·2에서 양쪽 엔진에 동일 스키마로 적재).

- 노드용 (6종): `tb_customer_contract`, `tb_device_master`, `tb_plan_master`, `tb_subsidy_policy`, `tb_doc_chunks`, `tb_domain_rules`
- 엣지용 (4종): `edge_contract_device`, `edge_contract_plan`, `edge_subsidy_binding`, `edge_rule_applies_to_plan`

## 이 Stage의 MCP: `mcp_stage3_property_graph`

| Step | 실제 수행 (`src/agent/mcp_server.py`, `engine="bigquery" \| "spanner"`) |
| :--- | :--- |
| `promote_dw_nodes` | 선택된 엔진(`bigquery` 또는 `spanner`)에서 노드 테이블 6개의 행 수와 중복 키 수 조회 → `node_tables`, `duplicate_keys_total` |
| `synthesize_graph_ddl` | 이 MCP에서는 수행하지 않는다. DDL 생성·실행은 `pipeline/graph_builder.py`의 `build_graph()`가 한다 |
| `verify_gql_templates` | 선택된 엔진의 `STARTER_ONTOLOGY_GRAPH`에서 `GRAPH_TABLE`로 `(DeviceNode)-[HAS_SUBSIDY_POLICY]->(PlanNode)<-[APPLIES_TO_PLAN]-(DomainRuleNode)` 경로 수를 센다 → `gql_paths` |

## 절차 (`pipeline/graph_builder.py`의 `build_graph()`)

1. **BigQuery & Spanner DDL 생성**:
   - `data/output/create_property_graph.sql` (BigQuery `CREATE OR REPLACE PROPERTY GRAPH <프로젝트>.<데이터셋>.STARTER_ONTOLOGY_GRAPH`)
   - `data/output/create_spanner_graph.sql` (Cloud Spanner 10개 테이블 + `CREATE OR REPLACE PROPERTY GRAPH STARTER_ONTOLOGY_GRAPH`)

   | 노드 레이블 | 테이블 | 키 |
   | :--- | :--- | :--- |
   | `CustomerContractNode` | `tb_customer_contract` | `contract_id` |
   | `DeviceNode` | `tb_device_master` | `device_id` |
   | `PlanNode` | `tb_plan_master` | `plan_id` |
   | `SubsidyNode` | `tb_subsidy_policy` | `policy_id` |
   | `DocChunkNode` | `tb_doc_chunks` | `chunk_id` |
   | `DomainRuleNode` | `tb_domain_rules` | `rule_id` |

   | 엣지 레이블 | 테이블 | 방향 |
   | :--- | :--- | :--- |
   | `USES_DEVICE` | `edge_contract_device` | 약정 → 단말 |
   | `SUBSCRIBES_PLAN` | `edge_contract_plan` | 약정 → 요금제 |
   | `HAS_SUBSIDY_POLICY` | `edge_subsidy_binding` | 단말 → 요금제 (지원금 정책) |
   | `APPLIES_TO_PLAN` | `edge_rule_applies_to_plan` | 규칙 → 요금제 |

2. **DDL 실행**: 활성 엔진 설정에 따라 BigQuery 및 Cloud Spanner(`starter-spanner/starter_ontology_db`)에서 `CREATE OR REPLACE PROPERTY GRAPH` DDL을 실행한다.
3. **양대 엔진 검증 질의 및 N-run 벤치마크**: 동일한 3-Hop `GRAPH_TABLE` 질의를 BigQuery와 Cloud Spanner에서 각각 5회 반복 실행하여 `p50_ms`, `p95_ms`, `mean_ms`와 반환 행 수를 측정한다.
4. **Graph Fabric 연합 질의 (`EXTERNAL_QUERY`)**: `"both"` 모드에서는 `EXTERNAL_QUERY("projects/<project>/locations/asia-northeast3/connections/spanner_fabric_conn", ...)`를 실행해 Spanner Graph 멀티홉 결과와 BigQuery `tb_doc_chunks`를 실시간 조인한다.
5. **토폴로지 기록**: 양대 엔진 배포 상태, 벤치마크(`engine_comparison_benchmark`), 연합 조인(`graph_fabric_federated_probe`), 노드 통계를 `data/output/graph_topology.json`에 기록한다.

## 에이전트가 쓰는 GQL 패턴 (`mcp_query_graph_and_wiki`)

| 조건 | `MATCH` 패턴 | 홉 |
| :--- | :--- | :---: |
| 고객 ID 있음 | `(c:CustomerContractNode)-[:USES_DEVICE]->(d:DeviceNode), (c)-[:SUBSCRIBES_PLAN]->(p:PlanNode)<-[ap:APPLIES_TO_PLAN]-(r:DomainRuleNode)` | 3 |
| 고객 ID 없음 | `(d:DeviceNode)-[hs:HAS_SUBSIDY_POLICY]->(p:PlanNode)<-[ap:APPLIES_TO_PLAN]-(r:DomainRuleNode)` | 2 |

두 경우 모두 `ap.source_chunk_id`로 `tb_doc_chunks`를 조인해 근거 문단(`chunk_text`)과 앵커를 붙인다 (`engine="bigquery"` 및 `engine="spanner"` 모두 동일하게 동작).

## 산출물

| ID | 산출물 | 스타터에서 |
| :--- | :--- | :--- |
| `D3.1` | BigQuery & Spanner Property Graph 물리 DDL 스크립트 | `data/output/create_property_graph.sql`, `data/output/create_spanner_graph.sql` |
| `D3.2` | 그래프 토폴로지 구조도 및 데이터플로우 명세서 | `data/output/graph_topology.json` |
| `D3.3` | GQL 질의 패턴 카탈로그 및 템플릿 엔진 | 위 GQL 패턴 (`src/agent/mcp_server.py`, `pipeline/graph_builder.py`) |
| `D3.4` | BigQuery vs Spanner GQL 성능 벤치마크 및 Graph Fabric 검증 | `data/output/graph_topology.json` 내 `engine_comparison_benchmark` 및 `graph_fabric_federated_probe` |

## 게이트 (Gate 3)

- [ ] `graph_topology.json`의 `live_bigquery_deployment.ddl_execution.status`가 `SUCCESS`다.
- [ ] Spanner 활성 시 `live_spanner_deployment.ddl_execution.status`가 `SUCCESS`이고 `gql_verification_probe.row_count > 0`이다.
- [ ] `both` 모드 시 `graph_fabric_federated_probe.status`가 `SUCCESS`다.
- [ ] `metrics.duplicate_entity_nodes`와 Stage 3 MCP의 `duplicate_keys_total`이 0이다.

## 스튜디오에서 보기

[Stage 3. Property Graph 탭 열기](https://agentic-ontology-starter-924723860007.asia-northeast3.run.app/?tab=stage3)

- 위쪽 `BigQuery Property Graph` / `Cloud Spanner Graph` 전환: 오른쪽 DDL 뷰가 바뀌고 선택 엔진이 전환된다.
- 오른쪽 상단 `▶ 선택 엔진 GQL 실행` 및 `▶ 양대 엔진 비교 실행` 버튼: BigQuery와 Cloud Spanner에서 실시간 `GRAPH_TABLE` 멀티홉 탐색을 실행하고 지연 시간·결과를 비교한다.

## 노트북

[stage3_property_graph_bigquery_spanner_ko.ipynb](../../notebooks/ko/stage3_property_graph_bigquery_spanner_ko.ipynb)

## 내 데이터에 적용하기 (정형 테이블 유무 및 타 도메인 스키마 대응)

1. **정형 테이블이 없는 문서 전용 프로젝트 (`lite` 트랙)**:
   - 고객이 정형 테이블(`03_tables/*.csv`)을 주지 않았을 때는 Stage 3 물리 Property Graph 생성을 실행하지 않고 건너뛴다(Stage 2에서 추출한 `entities.md`·`concepts.md`가 시맨틱 관계를 담당).
   - 만약 정형 테이블이 없는 상태에서 사용자가 `track: "standard"/"full"`이나 Stage 3 실행을 요청하면, `run_pipeline.py`와 `graph_builder.py`는 가짜 테이블을 만들지 않고 즉시 중단하여 **(a) 고객 정형 테이블 CSV 추가 제공, (b) 문서 기반 물리 그래프(별도 설계), (c) 합성 데모 시드 사용(승인 필요)** 또는 **`lite` 트랙 전환**을 확인받는다.
2. **타 산업·신규 스키마의 정형 테이블이 유입된 경우 (`graph_module` 오버라이드)**:
   - 루트 공용 `pipeline/graph_builder.py`를 직접 수정하지 않고, `projects/<id>/project.json`에 `"graph_module": "projects.<id>.custom_graph"`를 지정해 해당 도메인 테이블에 맞는 `CREATE OR REPLACE PROPERTY GRAPH`와 `vis_property_graph`를 생성한다.
3. **테이블 및 DDL 정의**:
   - 노드·엣지로 쓸 테이블을 `terraform/bigquery.tf`(또는 프로젝트별 BigQuery 데이터셋)에 정의한다. 엣지 테이블에는 양 끝 노드의 키 열이 있어야 한다.
   - 그래프 이름을 바꾸려면 `project.json`의 `bq_graph` 설정을 함께 변경한다.
