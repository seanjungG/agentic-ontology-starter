# 5-Stage Agentic Ontology Methodology (`METHODOLOGY_EN.md`)

> Live Studio [`Agentic Ontology Starter (6-Tab)`](https://agentic-ontology-starter-924723860007.asia-northeast3.run.app/) · Reference Studios [`LG U+ (12-Tab)`](https://agentic-ontology-studio-lguplus-mcp-924723860007.asia-northeast3.run.app/) · [`LG H&H (12-Tab)`](https://agentic-ontology-studio-hnh-mcp-924723860007.asia-northeast3.run.app/) · [Korean (KO)](../ko/METHODOLOGY_KO.md) · [Stage Index](../README.md) · [Notebooks](../../notebooks/README.md) · [License (`LICENSE`)](../../LICENSE)

## 1. Purpose & Core Principles (Resource-Connected Starter Architecture v2.2)

This guide defines the **Agentic Ontology Starter v2.2** methodology — aligned 1:1 with the production **LG U+ Telecom Reference Studio (12-Tab)** and **LG H&H Compliance Reference Studio (12-Tab)** (`5-Stage × 11-Step`, `P1/P2/P3` × `W1/W2/W3` × `Gate G2-W`). Heavy internal MCP builder pipelines are **excluded and abstracted** into the platform layer, while the Starter connects directly to **Ready-to-Use Google Cloud Ontology Resources**.

1. **Code Exposure Boundary**:
   - **Abstracted Platform Layer**: Internal ontology builder MCP tools and heavy document parsers/compilers are excluded from the Starter runtime catalog (`get_tool_catalog()`). Pre-compiled assets are served as **Ready-to-Use GCP Resources** in BigQuery (`seanjung-poc.starter_ontology_dw`), GCS (`gs://seanjung-poc-starter-ontology/ontology/`), and Cloud Spanner (`starter-spanner`).
   - **Exposed Customizable Starter Code (4 Core Files)**:
     1. [`src/resource_connector.py`](../../src/resource_connector.py) (`OntologyResourceConnector` — Stage 1~5 resource readiness checks)
     2. [`src/gcp_client.py`](../../src/gcp_client.py) (`EnterpriseOntologyBenchmarker` — BigQuery SQL/GQL, Spanner GQL, GCS, Vertex AI `gemini-3.8-flash`)
     3. [`src/agent/mcp_server.py`](../../src/agent/mcp_server.py) (`DomainMcpServer` — **3 Customizable Domain Business Tools**)
     4. [`src/agent/reasoning_engine.py`](../../src/agent/reasoning_engine.py) (`AgenticReasoningEngine` — sub-goal decomposition, tool chaining, `Gate G2-W` audit)
2. **Runtime BQG 1st-Priority SSOT**:
   - At runtime, **BigQuery Property Graph (`STARTER_ONTOLOGY_GRAPH`)** and its synced 3-Layer OKF Wiki (`summary/entities/concepts/rules.md`), Business Rules (`business_rules.json`), and Business Workflows (`business_workflows.json`, `W1~W3`) act as the Single Source of Truth.
3. **Deterministic SQL Math & `Gate G2-W` Runtime Audit**:
   - Subsidy, penalty clawback, and 24-month TCO calculations execute deterministically in SQL inside the 3 Domain Business Tools, audited by `Gate G2-W` for exception priority (`SENIOR_EXEMPT`) and `DOC_CHUNK_*` SHA-256 citation.

## 2. Unified Stage 0~5 Map: Demo Tab ↔ Process ↔ Connected Resource ↔ Exposed Code ↔ Notebooks (1:1)

| Stage | Starter Portal Tab | Standard Process (`Step` / `P·W·Gate`) | Connected Ready-to-Use GCP Resource | Exposed Core Code / Tool | Stage Guide / Bilingual Notebooks |
| :---: | :--- | :--- | :--- | :--- | :--- |
| **Stage 0** | [`0. Overview`](https://agentic-ontology-starter-924723860007.asia-northeast3.run.app/?tab=overview) | Architecture Overview · Reference Hub · 3-Track Selector | `config/starter_config.json` · `portal_profile.json` | `src/resource_connector.py` | [Guide](./00_overview_and_4tracks_en.md) · [KO](../../notebooks/ko/stage0_overview_walkthrough_ko.ipynb) · [EN](../../notebooks/en/stage0_overview_walkthrough_en.ipynb) |
| **Stage 1** | [`Stage 1. Asset`](https://agentic-ontology-starter-924723860007.asia-northeast3.run.app/?tab=stage1) | Asset Check · Resource Binding · Golden CQs (`P1`·`P2`) | `seanjung-poc.starter_ontology_dw` (10 Tables) | `stage1_resource_check` | [Guide](./01_stage1_asset_and_cq_en.md) · [KO](../../notebooks/ko/stage1_asset_and_cq_ko.ipynb) · [EN](../../notebooks/en/stage1_asset_and_cq_en.ipynb) |
| **Stage 2** | [`Stage 2. Wiki & Semantic`](https://agentic-ontology-starter-924723860007.asia-northeast3.run.app/?tab=stage2) | 3-Layer OKF Wiki · Business Rules (4) · Workflows (`W1~W3`) | `gs://seanjung-poc-starter-ontology/ontology/` + `tb_domain_rules` | `stage2_resource_check` | [Guide](./02_stage2_wiki_and_semantic_graph_en.md) · [KO](../../notebooks/ko/stage2_wiki_and_semantic_graph_ko.ipynb) · [EN](../../notebooks/en/stage2_wiki_and_semantic_graph_en.ipynb) |
| **Stage 3** | [`Stage 3. Property Graph`](https://agentic-ontology-starter-924723860007.asia-northeast3.run.app/?tab=stage3) | Zero-ETL BigQuery Graph & Spanner Graph (`P1`·`P3`) | `STARTER_ONTOLOGY_GRAPH` (BQ SQL:2023 & Spanner GQL) | `stage3_resource_check` · `src/gcp_client.py` | [Guide](./03_stage3_property_graph_en.md) · [KO](../../notebooks/ko/stage3_property_graph_bigquery_spanner_ko.ipynb) · [EN](../../notebooks/en/stage3_property_graph_bigquery_spanner_en.ipynb) |
| **Stage 4** | [`Stage 4. Agent & Tools`](https://agentic-ontology-starter-924723860007.asia-northeast3.run.app/?tab=stage4) | 3 Domain Business Tools & AI FDE (`P3` · `Gate G2-W`) | Vertex AI `gemini-3.8-flash` + 3 Domain Tools | `src/agent/mcp_server.py` · `src/agent/reasoning_engine.py` | [Guide](./04_stage4_agent_and_mcp_en.md) · [KO](../../notebooks/ko/stage4_agent_and_mcp_execution_ko.ipynb) · [EN](../../notebooks/en/stage4_agent_and_mcp_execution_en.ipynb) |
| **Stage 5** | [`Stage 5. Lineage & Eval`](https://agentic-ontology-starter-924723860007.asia-northeast3.run.app/?tab=stage5) | 6-Layer Data Lineage DAG & Golden/WF/Boundary Eval | `tb_golden_cq_results` · `config/lineage_spec.json` | `stage5_resource_check` · `src/lineage_service.py` | [Guide](./05_stage5_lineage_and_eval_en.md) · [KO](../../notebooks/ko/stage5_lineage_and_evaluation_ko.ipynb) · [EN](../../notebooks/en/stage5_lineage_and_evaluation_en.ipynb) |

## 3. 3 Customizable Domain Business Tools (`src/agent/mcp_server.py`)

| Tool Name | Category | Function & Connected GCP Resources |
| :--- | :--- | :--- |
| **`mcp_lookup_customer_profile`** | `runtime_domain` | Direct lookup of customer contracts (`tb_customer_contract`), device prices (`tb_device_master`), and subsidy policies (`tb_subsidy_policy`) |
| **`mcp_calculate_penalty_rule`** | `runtime_domain` | Deterministic SQL calculation of senior welfare exemption (`RULE_WELFARE_EXEMPT`), 180-day prorated penalty (`RULE_SIX_PLAN_180D`), and 24-month TCO (`RULE_TCO_24M`) bound to workflows `W1~W3` |
| **`mcp_query_graph_and_wiki`** | `runtime_domain` | Multi-hop `GRAPH_TABLE` traversal on `STARTER_ONTOLOGY_GRAPH` joined with `tb_doc_chunks` SHA-256 anchors |
