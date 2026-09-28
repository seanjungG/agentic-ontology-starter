# Agentic Ontology Starter — Interactive Jupyter Notebooks (`Stage 0` ~ `Stage 5`)

This directory contains **11 interactive Jupyter Notebooks** (`0. Overview` + bilingual `Stage 1` ~ `Stage 5` KO/EN) mapped 1:1 to the **5-Stage × 9-Step Enterprise Agentic Ontology Methodology** and the 6-Tab **Agentic Ontology Studio**.

Every notebook focuses on:
1. **Live BigQuery Data & Property Graph Exploration (`%%bqsql` BigFrames Magics)**: Direct SQL and ISO GQL queries against `seanjung-poc.starter_ontology_dw` and `STARTER_ONTOLOGY_GRAPH`.
2. **Visualizations & Graph Topology (`matplotlib` + `networkx`)**: Subsidy heatmaps, 180-day penalty curves, Semantic Ontology Hub graphs (`Entity=Node`, `Concept=Edge`), full Property Graph topologies, 1..2-hop variable-length ego subgraphs, and 4-Tier multipartite lineage graphs.
3. **Live Vertex AI Gemini (`gemini-3.8-flash`) & Agentic MCP Execution**: Candidate triple extraction, schema-guarded NL-to-GQL generation & auto-repair (`nl2gql`), 8 modular MCP tools, and 2-Pass `AiFdeAgentEngine` responses across `GROUNDED`, `INSUFFICIENT_PARAMETERS`, and `MATCH_NOT_FOUND`.

---

## 1. Canonical Notebook Index (11 Files)

| Stage / Step | Korean Notebook (`.ipynb`) | English Notebook (`.ipynb`) | Methodology Doc | Core Explorations, Visualizations & Live Executions |
| :--- | :--- | :--- | :--- | :--- |
| **0. Overview** | [`stage0_overview_walkthrough.ipynb`](./stage0_overview_walkthrough.ipynb) | [`stage0_overview_walkthrough.ipynb`](./stage0_overview_walkthrough.ipynb) | [`METHODOLOGY_KO.md`](../methodology/METHODOLOGY_KO.md) · [`EN`](../methodology/METHODOLOGY_EN.md) | 10-table BigQuery inventory bar chart, full `STARTER_ONTOLOGY_GRAPH` topology, live `nl2gql`, and Golden CQ-03 / CQ-05 agent runs |
| **Stage 1** (`Step 1.1`–`1.2`) | [`stage1_asset_and_cq_ko.ipynb`](./stage1_asset_and_cq_ko.ipynb) | [`stage1_asset_and_cq_en.ipynb`](./stage1_asset_and_cq_en.ipynb) | [`01_stage1_asset_and_cq_ko.md`](../methodology/01_stage1_asset_and_cq_ko.md) · [`EN`](../methodology/01_stage1_asset_and_cq_en.md) | Table byte/row profiling, de-identified `CUST_DEMO_*` retention distribution, Device × Plan net-price heatmap, domain term × chunk frequency heatmap, 5 Golden CQs verification SQL check |
| **Stage 2** (`Step 2.1`–`2.2`) | [`stage2_wiki_and_semantic_graph_ko.ipynb`](./stage2_wiki_and_semantic_graph_ko.ipynb) | [`stage2_wiki_and_semantic_graph_en.ipynb`](./stage2_wiki_and_semantic_graph_en.ipynb) | [`02_stage2_wiki_and_semantic_ko.md`](../methodology/02_stage2_wiki_and_semantic_ko.md) · [`EN`](../methodology/02_stage2_wiki_and_semantic_en.md) | Karpathy 3-Layer LLM-Wiki (`summary.md`, `entities.md`, `concepts.md`, `rules.md`), SHA-256 chunk integrity, Semantic Graph (`Entity=Node`, `Concept=Edge`), Gemini triple extraction, `mcp_stage2_wiki_and_semantic` |
| **Stage 3** (`Step 3.1`–`3.2`) | [`stage3_property_graph_bigquery_spanner_ko.ipynb`](./stage3_property_graph_bigquery_spanner_ko.ipynb) | [`stage3_property_graph_bigquery_spanner_en.ipynb`](./stage3_property_graph_bigquery_spanner_en.ipynb) | [`03_stage3_property_graph_ko.md`](../methodology/03_stage3_property_graph_ko.md) · [`EN`](../methodology/03_stage3_property_graph_en.md) | BigQuery Graph vs. Spanner Graph DDL, live `INFORMATION_SCHEMA.PROPERTY_GRAPHS`, node/edge distribution charts, full topology & `CUST_DEMO_001` 1..2-hop subgraph, 6 ISO GQL patterns, live Gemini `nl2gql` + unanswerable schema guard |
| **Stage 4** (`Step 4.1`–`4.2`) | [`stage4_agent_and_mcp_execution_ko.ipynb`](./stage4_agent_and_mcp_execution_ko.ipynb) | [`stage4_agent_and_mcp_execution_en.ipynb`](./stage4_agent_and_mcp_execution_en.ipynb) | [`04_stage4_agent_and_mcp_ko.md`](../methodology/04_stage4_agent_and_mcp_ko.md) · [`EN`](../methodology/04_stage4_agent_and_mcp_en.md) | 8 MCP tools catalog, direct calls to 3 domain MCP tools, 30..200-day prorated penalty curve chart, 2-Pass `AiFdeAgentEngine` execution (`CQ-01`, `CQ-02`, `CQ-03`, `BC-PARAM`, `BC-NOTFOUND`), LLM vs. BigQuery latency chart |
| **Stage 5** (`Step 5.1`–`5.2`) | [`stage5_lineage_and_evaluation_ko.ipynb`](./stage5_lineage_and_evaluation_ko.ipynb) | [`stage5_lineage_and_evaluation_en.ipynb`](./stage5_lineage_and_evaluation_en.ipynb) | [`05_stage5_lineage_and_eval_ko.md`](../methodology/05_stage5_lineage_and_eval_ko.md) · [`EN`](../methodology/05_stage5_lineage_and_eval_en.md) | 4-Tier end-to-end lineage SQL (`Source File → DocChunk → DomainRule → Contract → CQ`), multipartite lineage graph, Golden CQ 5 live re-verification (`recheck_cq`), Boundary 10 cases × 5 trials (50 trials) metrics & failure taxonomy |

---

## 2. Shared Helper Module & Utilities

- [`nb_helpers.py`](./nb_helpers.py): Configures `bigframes.pandas` (`%%bqsql`), CJK typography (`AppleGothic` / `NanumGothic`), chart builders (`bar`, `grouped_bar`, `line`, `heatmap`), NetworkX graph renderers (`draw_graph`, `paths_to_graph`, `lineage_graph`), live schema inspection (`graph_metadata`), Gemini `nl2gql`, and MCP/Agent formatters (`show_tool`, `show_agent`, `recheck_cq`).
- [`nb_specs_s0_s2.py`](./nb_specs_s0_s2.py) & [`nb_specs_s3_s5.py`](./nb_specs_s3_s5.py): Declarative cell definitions for Stages 0–2 and Stages 3–5.
- [`generate_notebooks.py`](./generate_notebooks.py): Rebuilds all 11 `.ipynb` files, optionally executes them via `jupyter nbconvert --execute`, and packs embedded PNG attachments.
- [`validate_and_pack_notebooks.py`](./validate_and_pack_notebooks.py): Embeds Base64 PNG attachments from `notebooks/assets/` and validates `nbformat v4.5` & `nbconvert v7.17.1` compliance.

---

## 3. Prerequisites & Execution

1. **Authenticate Application Default Credentials (ADC)** with an account that has BigQuery (`roles/bigquery.jobUser`, `roles/bigquery.dataViewer`) and Vertex AI (`roles/aiplatform.user`) access on your target project (`seanjung-poc`):
   ```bash
   gcloud auth application-default login
   ```
2. **Execute & Pack All 11 Notebooks**:
   ```bash
   SSL_CERT_FILE=/etc/ssl/cert.pem .venv/bin/python notebooks/generate_notebooks.py --execute
   ```
3. **Validate Attachment & Schema Integrity Only**:
   ```bash
   .venv/bin/python notebooks/validate_and_pack_notebooks.py
   ```
