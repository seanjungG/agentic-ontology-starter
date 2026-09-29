# Stage 3. Property Graph and GQL

> Studio [`Stage 3. Property Graph`](https://agentic-ontology-starter-924723860007.asia-northeast3.run.app/?tab=stage3) · MCP `mcp_stage3_property_graph` · Notebook [stage3_property_graph_bigquery_spanner_en.ipynb](../../notebooks/en/stage3_property_graph_bigquery_spanner_en.ipynb) · [Korean (KO)](../ko/03_stage3_property_graph_ko.md) · [Full methodology](./METHODOLOGY_EN.md)

## Purpose

Declare the tables loaded in Stages 1 and 2 as graph nodes and edges without copying them.
With one `GRAPH_TABLE` query the agent follows several tables and gets the path behind an answer (contract/device → plan ← rule → evidence chunk).

## Engine support

| Engine | Supported in the starter | Not included |
| :--- | :--- | :--- |
| BigQuery Property Graph | DDL generation, DDL execution on BigQuery, `GRAPH_TABLE` queries by the agent | - |
| Cloud Spanner Graph | DDL file generation only (`data/output/create_spanner_graph.sql`) | Code to create an instance, apply the DDL or query Spanner. Passing `engine: "spanner"` still runs the query on BigQuery; the value is only echoed in the result |

## Inputs

The 10 BigQuery tables created by `terraform/bigquery.tf` (loaded in Stages 1 and 2).

- Node tables: `tb_customer_contract`, `tb_device_master`, `tb_plan_master`, `tb_subsidy_policy`, `tb_doc_chunks`, `tb_domain_rules`
- Edge tables: `edge_contract_device`, `edge_contract_plan`, `edge_subsidy_binding`, `edge_rule_applies_to_plan`

## MCP of this Stage: `mcp_stage3_property_graph`

| Step | What the code does (`src/agent/mcp_server.py`) |
| :--- | :--- |
| `promote_dw_nodes` | Row count and duplicate-key count of the 6 node tables → `node_tables`, `duplicate_keys_total` |
| `synthesize_graph_ddl` | Not done by this MCP. DDL generation and execution are done by `build_graph()` in `pipeline/graph_builder.py` |
| `verify_gql_templates` | Counts `(DeviceNode)-[HAS_SUBSIDY_POLICY]->(PlanNode)<-[APPLIES_TO_PLAN]-(DomainRuleNode)` paths with `GRAPH_TABLE` → `gql_paths` |

The `steps` argument is recorded in `executed_steps` of the result. The current handler runs both queries regardless of the selected steps.

## Procedure (`build_graph()` in `pipeline/graph_builder.py`)

1. **Generate the BigQuery DDL**: `CREATE OR REPLACE PROPERTY GRAPH <project>.<dataset>.STARTER_ONTOLOGY_GRAPH` → `data/output/create_property_graph.sql`

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

2. **Execute the DDL**: with `deploy_live_bq=True` (default) the DDL runs on BigQuery.
3. **Check query**: query the contract → device and contract → plan ← rule paths with `GRAPH_TABLE` (up to 10 rows).
4. **Node statistics**: count rows and duplicate keys of the 6 node tables.
5. **Generate the Spanner DDL**: write 5 tables and `StarterOntologyGraph` (5 nodes, 3 edges) to a file. `tb_doc_chunks` and `APPLIES_TO_PLAN` are not included, and the file is not executed.
6. **Record the topology**: write the DDL job, check-query result, node statistics and the viewer graph definitions to `data/output/graph_topology.json`.

`DocChunkNode` is declared as a node but has no connected edge. Rules are linked to evidence chunks by joining the `source_chunk_id` property of the `APPLIES_TO_PLAN` edge to `tb_doc_chunks`.

## GQL patterns used by the agent (`mcp_query_graph_and_wiki`)

| Condition | `MATCH` pattern | Hops |
| :--- | :--- | :---: |
| Customer ID given | `(c:CustomerContractNode)-[:USES_DEVICE]->(d:DeviceNode), (c)-[:SUBSCRIBES_PLAN]->(p:PlanNode)<-[ap:APPLIES_TO_PLAN]-(r:DomainRuleNode)` | 3 |
| No customer ID | `(d:DeviceNode)-[hs:HAS_SUBSIDY_POLICY]->(p:PlanNode)<-[ap:APPLIES_TO_PLAN]-(r:DomainRuleNode)` | 2 |

In both cases `tb_doc_chunks` is joined on `ap.source_chunk_id` to attach the evidence paragraph (`chunk_text`) and its anchor.

## Deliverables

| ID | Deliverable | In the starter |
| :--- | :--- | :--- |
| `D3.1` | BigQuery Property Graph physical DDL script | `data/output/create_property_graph.sql` (the Spanner file `create_spanner_graph.sql` is generated only) |
| `D3.2` | Graph topology and data flow specification | `data/output/graph_topology.json` |
| `D3.3` | GQL query pattern catalog and template engine | The GQL patterns above (`src/agent/mcp_server.py`, `pipeline/graph_builder.py`). There is no separate catalog file |
| `D3.4` | SQL vs GQL performance and cost benchmark report | Not included in the starter (no measurement file) |

## Gate (Gate 3)

- [ ] `live_bigquery_deployment.ddl_execution.status` in `graph_topology.json` is `SUCCESS`.
- [ ] `gql_verification_probe.row_count` is greater than 0.
- [ ] `metrics.duplicate_entity_nodes` and `duplicate_keys_total` of the Stage 3 MCP are 0.
- [ ] If you plan to use Spanner, apply `create_spanner_graph.sql` to Spanner yourself and verify it (outside the starter).

## View in the studio

[Open the Stage 3. Property Graph tab](https://agentic-ontology-starter-924723860007.asia-northeast3.run.app/?tab=stage3)

- `BigQuery Property Graph` / `Cloud Spanner Graph` switch (top): the DDL view on the right changes between `create_property_graph.sql` and `create_spanner_graph.sql`.
- Left: Property Graph viewer (`vis_property_graph` in `graph_topology.json`).
- Multi-hop GQL button: runs `mcp_query_graph_and_wiki` on BigQuery.
- Stage 3 MCP button (top right): runs the MCP above.

## Notebook

[stage3_property_graph_bigquery_spanner_en.ipynb](../../notebooks/en/stage3_property_graph_bigquery_spanner_en.ipynb)

## Apply to your data

1. **Tables**: define the node and edge tables in `terraform/bigquery.tf`. An edge table needs the key columns of both end nodes.
2. **DDL**: edit the BigQuery DDL in `pipeline/graph_builder.py` (node labels, keys, properties, edges) for your tables. The Spanner DDL is in the same file.
3. **Queries**: edit the `MATCH` patterns and column names in `src/agent/mcp_server.py` for your labels.
4. **Graph name**: to rename the graph, change `self.graph` in `DomainMcpServer` and `graph_fqn` in `build_graph()` together.
