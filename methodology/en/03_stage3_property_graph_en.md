# Stage 3. Property Graph and GQL

> Studio [`Stage 3. Property Graph`](https://agentic-ontology-starter-924723860007.asia-northeast3.run.app/?tab=stage3) · MCP `mcp_stage3_property_graph` · Notebook [stage3_property_graph_bigquery_spanner_en.ipynb](../../notebooks/en/stage3_property_graph_bigquery_spanner_en.ipynb) · [Korean (KO)](../ko/03_stage3_property_graph_ko.md) · [Full methodology](./METHODOLOGY_EN.md)

## Purpose

Declare the tables loaded in Stages 1 and 2 as graph nodes and edges without copying them.
With one `GRAPH_TABLE` query the agent follows several tables and gets the path behind an answer (contract/device → plan ← rule → evidence chunk).

## Engine Support & Graph Fabric Federation

| Engine / Mode | Supported in the Starter | Characteristics & Target Workload |
| :--- | :--- | :--- |
| **BigQuery Property Graph (`bigquery`, Default)** | DDL generation (`create_property_graph.sql`), DDL execution on BigQuery, `GRAPH_TABLE` queries across all 8 MCP tools | Zero-ETL logical graph view, TB-to-PB analytical scale, zero idle compute cost |
| **Cloud Spanner Graph (`spanner`, Opt-in)** | Terraform opt-in provisioning (`starter-spanner`, 100 PU, `starter_ontology_db`), 10-table ingestion, live `STARTER_ONTOLOGY_GRAPH` DDL deployment, and live GQL queries across all 8 MCP tools | Index-pointer traversal for sub-200ms online multi-hop queries (`p50 ~120ms`) |
| **Graph Fabric Federation (`both` Mode)** | Simultaneous ingestion & deployment on both engines, N-run `p50/p95` latency benchmark, and BigQuery `EXTERNAL_QUERY(spanner_fabric_conn)` federated join | Joins real-time Spanner Graph traversal results with BigQuery `tb_doc_chunks` in a single SQL query without data duplication |

> **Production Synchronization Patterns**:
> - **BigQuery -> Spanner (Reverse ETL)**: Export batch analytical aggregations to the online serving graph via BigQuery `EXPORT DATA` or Dataflow `BigQueryToSpanner`.
> - **Spanner -> BigQuery (Change Streams)**: Replicate real-time operational transactions into BigQuery DW via **Spanner Change Streams -> Dataflow -> BigQuery** CDC pipelines.

## Inputs

The 10 tables created by `terraform/bigquery.tf` and `terraform/spanner.tf` (loaded with identical schemas in Stages 1 and 2).

- Node tables (6): `tb_customer_contract`, `tb_device_master`, `tb_plan_master`, `tb_subsidy_policy`, `tb_doc_chunks`, `tb_domain_rules`
- Edge tables (4): `edge_contract_device`, `edge_contract_plan`, `edge_subsidy_binding`, `edge_rule_applies_to_plan`

## MCP of this Stage: `mcp_stage3_property_graph`

| Step | What the code does (`src/agent/mcp_server.py`, `engine="bigquery" \| "spanner"`) |
| :--- | :--- |
| `promote_dw_nodes` | Row count and duplicate-key count of the 6 node tables on the selected engine (`bigquery` or `spanner`) → `node_tables`, `duplicate_keys_total` |
| `synthesize_graph_ddl` | Not done by this MCP. DDL generation and execution are done by `build_graph()` in `pipeline/graph_builder.py` |
| `verify_gql_templates` | Counts `(DeviceNode)-[HAS_SUBSIDY_POLICY]->(PlanNode)<-[APPLIES_TO_PLAN]-(DomainRuleNode)` paths with `GRAPH_TABLE` on the selected engine → `gql_paths` |

## Procedure (`build_graph()` in `pipeline/graph_builder.py`)

1. **Generate BigQuery & Spanner DDLs**:
   - `data/output/create_property_graph.sql` (BigQuery `CREATE OR REPLACE PROPERTY GRAPH <project>.<dataset>.STARTER_ONTOLOGY_GRAPH`)
   - `data/output/create_spanner_graph.sql` (Cloud Spanner 10 tables + `CREATE OR REPLACE PROPERTY GRAPH STARTER_ONTOLOGY_GRAPH`)

   | Node label | Table | Key |
   | :--- | :--- | :--- |
   | `CustomerContractNode` | `tb_customer_contract` | `contract_id` |
   | `DeviceNode` | `tb_device_master` | `device_id` |
   | `PlanNode` | `tb_plan_master` | `plan_id` |
   | `SubsidyNode` | `tb_subsidy_policy` | `policy_id` |
   | `DocChunkNode` | `tb_doc_chunks` | `chunk_id` |
   | `DomainRuleNode` | `tb_domain_rules` | `rule_id` |

   | Edge label | Table | Direction |
   | :--- | :--- | :--- |
   | `USES_DEVICE` | `edge_contract_device` | contract → device |
   | `SUBSCRIBES_PLAN` | `edge_contract_plan` | contract → plan |
   | `HAS_SUBSIDY_POLICY` | `edge_subsidy_binding` | device → plan (subsidy policy) |
   | `APPLIES_TO_PLAN` | `edge_rule_applies_to_plan` | rule → plan |

2. **Execute the DDLs**: runs `CREATE OR REPLACE PROPERTY GRAPH` on BigQuery and, when Spanner is active, on Cloud Spanner (`starter-spanner/starter_ontology_db`).
3. **Verification query & N-run benchmark**: executes the same 3-hop `GRAPH_TABLE` traversal 5 times on BigQuery and 5 times on Cloud Spanner, recording `p50_ms`, `p95_ms`, `mean_ms`, and row counts.
4. **Graph Fabric federated query (`EXTERNAL_QUERY`)**: in `"both"` mode, executes `EXTERNAL_QUERY("projects/<project>/locations/asia-northeast3/connections/spanner_fabric_conn", ...)` to join Spanner Graph traversal rows with BigQuery `tb_doc_chunks`.
5. **Record the topology**: writes deployment statuses, `engine_comparison_benchmark`, `graph_fabric_federated_probe`, node statistics, and viewer graph definitions to `data/output/graph_topology.json`.

## GQL patterns used by the agent (`mcp_query_graph_and_wiki`)

| Condition | `MATCH` pattern | Hops |
| :--- | :--- | :---: |
| Customer ID given | `(c:CustomerContractNode)-[:USES_DEVICE]->(d:DeviceNode), (c)-[:SUBSCRIBES_PLAN]->(p:PlanNode)<-[ap:APPLIES_TO_PLAN]-(r:DomainRuleNode)` | 3 |
| No customer ID | `(d:DeviceNode)-[hs:HAS_SUBSIDY_POLICY]->(p:PlanNode)<-[ap:APPLIES_TO_PLAN]-(r:DomainRuleNode)` | 2 |

In both cases `tb_doc_chunks` is joined on `ap.source_chunk_id` to attach the evidence paragraph (`chunk_text`) and its anchor (supported on both `engine="bigquery"` and `engine="spanner"`).

## Deliverables

| ID | Deliverable | In the starter |
| :--- | :--- | :--- |
| `D3.1` | BigQuery & Spanner Property Graph physical DDL scripts | `data/output/create_property_graph.sql`, `data/output/create_spanner_graph.sql` |
| `D3.2` | Graph topology and data flow specification | `data/output/graph_topology.json` |
| `D3.3` | GQL query pattern catalog and template engine | The GQL patterns above (`src/agent/mcp_server.py`, `pipeline/graph_builder.py`) |
| `D3.4` | BigQuery vs Spanner GQL latency benchmark & Graph Fabric probe | `engine_comparison_benchmark` and `graph_fabric_federated_probe` in `data/output/graph_topology.json` |

## Gate (Gate 3)

- [ ] `live_bigquery_deployment.ddl_execution.status` in `graph_topology.json` is `SUCCESS`.
- [ ] When Spanner is active, `live_spanner_deployment.ddl_execution.status` is `SUCCESS` and `gql_verification_probe.row_count > 0`.
- [ ] In `both` mode, `graph_fabric_federated_probe.status` is `SUCCESS`.
- [ ] `metrics.duplicate_entity_nodes` and `duplicate_keys_total` of the Stage 3 MCP are 0.

## View in the studio

[Open the Stage 3. Property Graph tab](https://agentic-ontology-starter-924723860007.asia-northeast3.run.app/?tab=stage3)

- `BigQuery Property Graph` / `Cloud Spanner Graph` switch (top): switches the active graph engine and updates the DDL view.
- Single-engine GQL and Dual-Engine Comparison buttons (top right): execute `mcp_query_graph_and_wiki` on the selected engine or side-by-side on both BigQuery and Cloud Spanner.

## Notebook

[stage3_property_graph_bigquery_spanner_en.ipynb](../../notebooks/en/stage3_property_graph_bigquery_spanner_en.ipynb)

## Apply to your data

### 1) Document-Only Projects (`tables: {}` — Scenario A1 & A2)

BigQuery Property Graph (`CREATE OR REPLACE PROPERTY GRAPH`) requires physical BigQuery node and edge tables. When a customer project provides only unstructured documents (`01_raw_docs/`, `01_guides/`) without structured table CSVs:

- **Option 1 (`track: "auto"` or `"lite"` — Recommended)**: Stage 3 is automatically skipped, and the pipeline proceeds directly from Stage 2 (`03_wiki/entities.md`, `concepts.md`, `doc_chunks.jsonl`) to Stage 4 (`execute_lite_doc_cycle`).
- **Option 2 (`track: "full"` or `--stage 3` forced — Scenario A2)**: The pipeline halts immediately before Stage 3 without fabricating synthetic tables, outputting guidance to either supply structured CSVs (`03_tables/`) or switch `track` to `"lite"` / `"auto"`.

### 2) Custom Domain Schemas (Scenario C)

1. **Tables**: define the node and edge tables in `terraform/bigquery.tf`. An edge table needs the key columns of both end nodes.
2. **Module Override (`graph_module`)**: when your domain schema differs from the 6-table telecom sample, specify `"graph_module": "projects.<id>.custom_graph"` in `project.json` to supply your own `build_graph()` implementation.
3. **DDL & Queries**: edit the BigQuery DDL in `pipeline/graph_builder.py` (node labels, keys, properties, edges) and the `MATCH` patterns in `src/agent/mcp_server.py` for your labels.
4. **Graph name**: to rename the graph, change `self.graph` in `DomainMcpServer` and `graph_fqn` in `build_graph()` together.
