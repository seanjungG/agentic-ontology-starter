# Stage 3. Property Graph·GQL

> 스튜디오 [`Stage 3. Property Graph`](https://agentic-ontology-starter-924723860007.asia-northeast3.run.app/?tab=stage3) · MCP `mcp_stage3_property_graph` · 노트북 [stage3_property_graph_bigquery_spanner_ko.ipynb](../notebooks/ko/stage3_property_graph_bigquery_spanner_ko.ipynb) · [English](./03_stage3_property_graph_en.md) · [전체 방법론](./METHODOLOGY_KO.md)

## 목적

Stage 1·2에서 적재한 테이블을 복사하지 않고 그대로 그래프의 노드·엣지로 선언한다.
에이전트는 `GRAPH_TABLE` 질의 한 번으로 여러 테이블을 따라가며 답의 경로(약정·단말 → 요금제 ← 규칙 → 근거 청크)를 얻는다.

## 엔진 지원 범위

| 엔진 | 스타터에서 지원하는 것 | 없는 것 |
| :--- | :--- | :--- |
| BigQuery Property Graph | DDL 생성, BigQuery에서 DDL 실행, 에이전트의 `GRAPH_TABLE` 조회 | - |
| Cloud Spanner Graph | DDL 파일 생성만 (`data/output/create_spanner_graph.sql`) | 인스턴스 생성, DDL 적용, Spanner 조회 코드. `engine: "spanner"`를 넘겨도 조회는 BigQuery에서 실행되고, 값은 결과에 표기만 된다 |

## 입력

`terraform/bigquery.tf`로 만든 BigQuery 테이블 10개 (Stage 1·2에서 적재).

- 노드용: `tb_customer_contract`, `tb_device_master`, `tb_plan_master`, `tb_subsidy_policy`, `tb_doc_chunks`, `tb_domain_rules`
- 엣지용: `edge_contract_device`, `edge_contract_plan`, `edge_subsidy_binding`, `edge_rule_applies_to_plan`

## 이 Stage의 MCP: `mcp_stage3_property_graph`

| Step | 실제 수행 (`src/agent/mcp_server.py`) |
| :--- | :--- |
| `promote_dw_nodes` | 노드 테이블 6개의 행 수와 중복 키 수 → `node_tables`, `duplicate_keys_total` |
| `synthesize_graph_ddl` | 이 MCP에서는 수행하지 않는다. DDL 생성·실행은 `pipeline/graph_builder.py`의 `build_graph()`가 한다 |
| `verify_gql_templates` | `GRAPH_TABLE`로 `(DeviceNode)-[HAS_SUBSIDY_POLICY]->(PlanNode)<-[APPLIES_TO_PLAN]-(DomainRuleNode)` 경로 수를 센다 → `gql_paths` |

`steps` 인자는 결과의 `executed_steps`에 기록된다. 현재 핸들러는 선택한 Step과 관계없이 두 쿼리를 모두 실행한다.

## 절차 (`pipeline/graph_builder.py`의 `build_graph()`)

1. **BigQuery DDL 생성**: `CREATE OR REPLACE PROPERTY GRAPH <프로젝트>.<데이터셋>.STARTER_ONTOLOGY_GRAPH` → `data/output/create_property_graph.sql`

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

2. **DDL 실행**: `deploy_live_bq=True`(기본값)이면 BigQuery에서 DDL을 실행한다.
3. **검증 질의**: 약정 → 단말, 약정 → 요금제 ← 규칙 경로를 `GRAPH_TABLE`로 조회한다 (최대 10행).
4. **노드 통계**: 노드 테이블 6개의 행 수와 중복 키 수를 센다.
5. **Spanner DDL 생성**: 테이블 5개와 `StarterOntologyGraph`(노드 5, 엣지 3)를 파일로 쓴다. `tb_doc_chunks`와 `APPLIES_TO_PLAN`은 들어가지 않으며, 실행하지 않는다.
6. **토폴로지 기록**: DDL 실행 Job, 검증 질의 결과, 노드 통계, 뷰어용 그래프 정의를 `data/output/graph_topology.json`에 쓴다.

`DocChunkNode`는 노드로 선언되지만 연결된 엣지가 없다. 규칙과 근거 청크는 `APPLIES_TO_PLAN` 엣지의 `source_chunk_id` 속성으로 `tb_doc_chunks`에 조인해 연결한다.

## 에이전트가 쓰는 GQL 패턴 (`mcp_query_graph_and_wiki`)

| 조건 | `MATCH` 패턴 | 홉 |
| :--- | :--- | :---: |
| 고객 ID 있음 | `(c:CustomerContractNode)-[:USES_DEVICE]->(d:DeviceNode), (c)-[:SUBSCRIBES_PLAN]->(p:PlanNode)<-[ap:APPLIES_TO_PLAN]-(r:DomainRuleNode)` | 3 |
| 고객 ID 없음 | `(d:DeviceNode)-[hs:HAS_SUBSIDY_POLICY]->(p:PlanNode)<-[ap:APPLIES_TO_PLAN]-(r:DomainRuleNode)` | 2 |

두 경우 모두 `ap.source_chunk_id`로 `tb_doc_chunks`를 조인해 근거 문단(`chunk_text`)과 앵커를 붙인다.

## 산출물

| ID | 산출물 | 스타터에서 |
| :--- | :--- | :--- |
| `D3.1` | BigQuery Property Graph 물리 DDL 스크립트 | `data/output/create_property_graph.sql` (Spanner용 `create_spanner_graph.sql`은 생성만) |
| `D3.2` | 그래프 토폴로지 구조도 및 데이터플로우 명세서 | `data/output/graph_topology.json` |
| `D3.3` | GQL 질의 패턴 카탈로그 및 템플릿 엔진 | 위 GQL 패턴 (`src/agent/mcp_server.py`, `pipeline/graph_builder.py`). 별도 카탈로그 파일은 없다 |
| `D3.4` | SQL vs GQL 성능·비용 벤치마크 보고서 | 스타터 미포함 (측정 파일 없음) |

## 게이트 (Gate 3)

- [ ] `graph_topology.json`의 `live_bigquery_deployment.ddl_execution.status`가 `SUCCESS`다.
- [ ] `gql_verification_probe.row_count`가 0보다 크다.
- [ ] `metrics.duplicate_entity_nodes`와 Stage 3 MCP의 `duplicate_keys_total`이 0이다.
- [ ] Spanner를 쓸 계획이면 `create_spanner_graph.sql`을 Spanner에 직접 적용하고 검증한다 (스타터 범위 밖).

## 스튜디오에서 보기

[Stage 3. Property Graph 탭 열기](https://agentic-ontology-starter-924723860007.asia-northeast3.run.app/?tab=stage3)

- 위쪽 `BigQuery Property Graph` / `Cloud Spanner Graph` 전환: 오른쪽 DDL 뷰가 `create_property_graph.sql` / `create_spanner_graph.sql`로 바뀐다.
- 왼쪽: Property Graph 뷰어 (`graph_topology.json`의 `vis_property_graph`).
- `▶ 멀티홉 GQL 실행` 버튼: `mcp_query_graph_and_wiki`를 BigQuery에서 실행한다.
- `▶ Stage 3 MCP 실행` 버튼 (오른쪽 위): 위 MCP를 실행한다.

## 노트북

[stage3_property_graph_bigquery_spanner_ko.ipynb](../notebooks/ko/stage3_property_graph_bigquery_spanner_ko.ipynb)

## 내 데이터에 적용하기

1. **테이블**: 노드·엣지로 쓸 테이블을 `terraform/bigquery.tf`에 정의한다. 엣지 테이블에는 양 끝 노드의 키 열이 있어야 한다.
2. **DDL**: `pipeline/graph_builder.py`의 BigQuery DDL(노드 레이블, 키, 속성, 엣지)을 새 테이블에 맞게 고친다. Spanner DDL도 같은 파일에 있다.
3. **질의**: `src/agent/mcp_server.py`의 `MATCH` 패턴과 열 이름을 새 레이블에 맞게 고친다.
4. **그래프 이름**: 이름을 바꾸려면 `DomainMcpServer`의 `self.graph`와 `build_graph()`의 `graph_fqn`을 함께 바꾼다.
