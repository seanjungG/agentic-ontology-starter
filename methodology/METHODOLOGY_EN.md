# 5-Stage Agentic Ontology Methodology (`METHODOLOGY_EN.md`)

> Live Studio [`Agentic Ontology Studio`](https://agentic-ontology-starter-924723860007.asia-northeast3.run.app) · [한국어](./METHODOLOGY_KO.md) · [Stage Index](./README.md) · [Notebooks](../notebooks/README.md)

## 1. Purpose & Core Principles

This guide defines the 5-Stage engineering workflow for combining structured enterprise tables (BigQuery DW) and unstructured policy documents into a **3-Layer Wiki (OKF v0.2)** and a **BigQuery Property Graph (ISO GQL)**, served through **8 MCP tools** and a **Vertex AI Gemini agent (`gemini-3.8-flash`)**.

1. **Immutable Lexical Anchors**: Policy paragraphs are hashed (`anchor_<12hex>`) and stored in `tb_doc_chunks` so every agent answer traces back to exact source paragraphs.
2. **Zero-ETL Property Graph**: Structured tables (`tb_devices`, `tb_plans`, `tb_subsidies`, `tb_customer_contracts`) and unstructured rules/chunks (`tb_domain_rules`, `tb_doc_chunks`) are projected into `STARTER_ONTOLOGY_GRAPH` via `CREATE OR REPLACE PROPERTY GRAPH`.
3. **Deterministic Arithmetic**: Penalty clawbacks and 24-month TCO comparisons are computed inside SQL/Python MCP tools rather than free-form LLM generation.
4. **Explicit Guardrail States**: Responses distinguish `GROUNDED`, `MATCH_NOT_FOUND`, `INSUFFICIENT_PARAMETERS`, and `BQ_QUERY_ERROR`.

## 2. 5-Stage Lifecycle & Studio · MCP · Notebook Matrix

| Stage | Name | Studio Tab | Stage MCP Tool (`src/agent/mcp_server.py`) | Deliverables | Stage Guide / Notebook |
| :---: | :--- | :--- | :--- | :---: | :--- |
| **Overview** | End-to-End Architecture & Tour | [`0. Overview`](https://agentic-ontology-starter-924723860007.asia-northeast3.run.app/?tab=overview) | Run Stage 1–5 individually or all | - | [stage0_overview_walkthrough.ipynb](../notebooks/stage0_overview_walkthrough.ipynb) |
| **Stage 1** | Asset Discovery, Scoping & CQs | [`Stage 1. Asset`](https://agentic-ontology-starter-924723860007.asia-northeast3.run.app/?tab=stage1) | `mcp_stage1_asset_discovery` | `D1.1`–`D1.4` | [Guide](./01_stage1_asset_and_cq_en.md) · [Notebook](../notebooks/stage1_asset_and_cq_en.ipynb) |
| **Stage 2** | 3-Layer Wiki & Semantic Graph | [`Stage 2. Wiki & Semantic Graph`](https://agentic-ontology-starter-924723860007.asia-northeast3.run.app/?tab=stage2) | `mcp_stage2_wiki_and_semantic` | `D2.1`–`D2.6` | [Guide](./02_stage2_wiki_and_semantic_graph_en.md) · [Notebook](../notebooks/stage2_wiki_and_semantic_graph_en.ipynb) |
| **Stage 3** | Property Graph & ISO GQL | [`Stage 3. Property Graph`](https://agentic-ontology-starter-924723860007.asia-northeast3.run.app/?tab=stage3) | `mcp_stage3_property_graph` | `D3.1`–`D3.4` | [Guide](./03_stage3_property_graph_en.md) · [Notebook](../notebooks/stage3_property_graph_bigquery_spanner_en.ipynb) |
| **Stage 4** | MCP Suite & Agent Orchestration | [`Stage 4. Agent & MCP`](https://agentic-ontology-starter-924723860007.asia-northeast3.run.app/?tab=stage4) | `mcp_stage4_agent_orchestration` + 3 Runtime MCPs | `D4.1`–`D4.4` | [Guide](./04_stage4_agent_and_mcp_en.md) · [Notebook](../notebooks/stage4_agent_and_mcp_execution_en.ipynb) |
| **Stage 5** | 4-Tier Lineage, Evaluation & Gate | [`Stage 5. Lineage & Eval`](https://agentic-ontology-starter-924723860007.asia-northeast3.run.app/?tab=stage5) | `mcp_stage5_lineage_and_eval` | `D5.1`–`D5.5` | [Guide](./05_stage5_lineage_and_eval_en.md) · [Notebook](../notebooks/stage5_lineage_and_evaluation_en.ipynb) |

## 3. 3-Track Adoption Model (`config/starter_config.json`)

| Track | Active Stages | Graph Engine | Target Scenario |
| :--- | :---: | :---: | :--- |
| **Track 1 · Lite** | `Stage 1 → 2 → 4` | `none` | Unstructured policy documents only — rapid 3-Layer Wiki and agent validation |
| **Track 2 · Standard** | `Stage 1 → 2 → 3 → 4` | `bigquery` (or Spanner DDL) | Structured DW + unstructured rules unified via `STARTER_ONTOLOGY_GRAPH` and GQL |
| **Track 3 · Full** | `Stage 1 → 2 → 3 → 4 → 5` | `bigquery` | Full lifecycle including 4-tier lineage, Golden CQ 5, boundary benchmark (10×5), and Terraform Cloud Run deployment |

## 4. Runtime Resources & 8 MCP Tools

- **BigQuery Dataset**: `seanjung-poc.starter_ontology_dw` — 6 node tables (`tb_devices`, `tb_plans`, `tb_subsidies`, `tb_customer_contracts`, `tb_domain_rules`, `tb_doc_chunks`), 4 edge tables (`edge_CoversDevice`, `edge_RequiresPlan`, `edge_GovernedByRule`, `edge_GroundedInChunk`), and `STARTER_ONTOLOGY_GRAPH`.
- **Cloud Storage**: `gs://seanjung-poc-starter-ontology` (`llm_wiki/` 3-Layer Markdown and manifest).
- **8 MCP Tools**: 5 Stage MCPs (`mcp_stage1_asset_discovery` .. `mcp_stage5_lineage_and_eval`) + 3 Runtime MCPs (`mcp_lookup_customer_profile`, `mcp_calculate_penalty_rule`, `mcp_query_graph_and_wiki`).
