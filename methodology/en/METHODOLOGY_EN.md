# 5-Stage Agentic Ontology Methodology (`METHODOLOGY_EN.md`)

> Live Studio [`Agentic Ontology Studio`](https://agentic-ontology-starter-lwrlf7yogq-du.a.run.app) · [Korean (KO)](../ko/METHODOLOGY_KO.md) · [Stage Index](../README.md) · [Notebooks](../../notebooks/README.md) · [License (`LICENSE`)](../../LICENSE)

## 1. Purpose & Core Principles (8-Phase Engineering Flow)

This guide defines the 5-Stage engineering workflow — structured across **1. Prepare → 2. Analyze → 3. Parse → 4. Integrate → 5. Build Graph → 6. Build Agent → 7. Answer (GQL) → 8. Verify & Gate** — for combining structured enterprise tables (BigQuery DW) and unstructured policy documents into a **3-Layer Wiki (OKF v0.2)** and a **BigQuery Property Graph (ISO GQL)**, served through **8 MCP tools** and a **Vertex AI Gemini agent (`gemini-3.8-flash`)**.

1. **Immutable Lexical Anchors**: Policy paragraphs are hashed (`anchor_<12hex>`) and stored in `tb_doc_chunks` so every agent answer traces back to exact source paragraphs.
2. **Zero-ETL Property Graph**: Structured tables (`tb_device_master`, `tb_plan_master`, `tb_subsidy_policy`, `tb_customer_contract`) and unstructured rules/chunks (`tb_domain_rules`, `tb_doc_chunks`) are projected into `STARTER_ONTOLOGY_GRAPH` via `CREATE OR REPLACE PROPERTY GRAPH`.
3. **Deterministic Arithmetic**: Penalty clawbacks and 24-month TCO comparisons are computed inside SQL/Python MCP tools rather than free-form LLM generation.
4. **Explicit Guardrail States**: Responses distinguish `GROUNDED`, `MATCH_NOT_FOUND`, `INSUFFICIENT_PARAMETERS`, and `BQ_QUERY_ERROR`.

## 2. 8-Phase Engineering Flow & 5-Stage · Studio · MCP · Notebook Matrix

| 8-Phase Flow | Stage | Name | Studio Tab | Stage MCP Tool (`src/agent/mcp_server.py`) | Deliverables | Stage Guide / Bilingual Notebooks |
| :--- | :---: | :--- | :--- | :--- | :---: | :--- |
| **0. End-to-End Tour** | **Overview** | End-to-End Architecture & Tour | [`0. Overview`](https://agentic-ontology-starter-lwrlf7yogq-du.a.run.app/?tab=overview) | Run Stage 1–5 individually or all | - | [KO Notebook](../../notebooks/ko/stage0_overview_walkthrough_ko.ipynb) · [EN Notebook](../../notebooks/en/stage0_overview_walkthrough_en.ipynb) |
| **1. Prepare · 2. Analyze** | **Stage 1** | Asset Discovery, Scoping & CQs | [`Stage 1. Asset`](https://agentic-ontology-starter-lwrlf7yogq-du.a.run.app/?tab=stage1) | `mcp_stage1_asset_discovery` | `D1.1`–`D1.4` | [Guide](./01_stage1_asset_and_cq_en.md) · [KO](../../notebooks/ko/stage1_asset_and_cq_ko.ipynb) · [EN](../../notebooks/en/stage1_asset_and_cq_en.ipynb) |
| **3. Parse · 4. Integrate** | **Stage 2** | 3-Layer Wiki & Semantic Graph | [`Stage 2. Wiki & Semantic Graph`](https://agentic-ontology-starter-lwrlf7yogq-du.a.run.app/?tab=stage2) | `mcp_stage2_wiki_and_semantic` | `D2.1`–`D2.6` | [Guide](./02_stage2_wiki_and_semantic_graph_en.md) · [KO](../../notebooks/ko/stage2_wiki_and_semantic_graph_ko.ipynb) · [EN](../../notebooks/en/stage2_wiki_and_semantic_graph_en.ipynb) |
| **5. Build Graph** | **Stage 3** | Property Graph & ISO GQL | [`Stage 3. Property Graph`](https://agentic-ontology-starter-lwrlf7yogq-du.a.run.app/?tab=stage3) | `mcp_stage3_property_graph` | `D3.1`–`D3.4` | [Guide](./03_stage3_property_graph_en.md) · [KO](../../notebooks/ko/stage3_property_graph_bigquery_spanner_ko.ipynb) · [EN](../../notebooks/en/stage3_property_graph_bigquery_spanner_en.ipynb) |
| **6. Build Agent · 7. Answer** | **Stage 4** | MCP Suite & Agent Orchestration | [`Stage 4. Agent & MCP`](https://agentic-ontology-starter-lwrlf7yogq-du.a.run.app/?tab=stage4) | `mcp_stage4_agent_orchestration` + 3 Runtime MCPs | `D4.1`–`D4.4` | [Guide](./04_stage4_agent_and_mcp_en.md) · [KO](../../notebooks/ko/stage4_agent_and_mcp_execution_ko.ipynb) · [EN](../../notebooks/en/stage4_agent_and_mcp_execution_en.ipynb) |
| **8. Verify & Gate** | **Stage 5** | End-to-End Lineage, Evaluation & Gate | [`Stage 5. Lineage & Eval`](https://agentic-ontology-starter-lwrlf7yogq-du.a.run.app/?tab=stage5) | `mcp_stage5_lineage_and_eval` | `D5.1`–`D5.5` | [Guide](./05_stage5_lineage_and_eval_en.md) · [KO](../../notebooks/ko/stage5_lineage_and_evaluation_ko.ipynb) · [EN](../../notebooks/en/stage5_lineage_and_evaluation_en.ipynb) |

## 3. Role of Starter Repository & 3-Track Adoption Model (`project.json` `track`)

This repository (`agentic-ontology-starter`) is an **educational, test, and project-bootstrap reference template** designed to handle unpredictable customer business domains and input data configurations without shipping any customer-proprietary assets.

The default `track: "auto"` inspects `project.json` `tables`: if customer table CSV files are listed, it activates `standard` / `full`; if `tables` is empty, it activates `lite`. Customer documents placed in `customer_doc/` are converted verbatim by `pipeline/extract_docs.py` and loaded only after **Gate 0** (`data/output/gate0_report.json`) passes (`char_retention_ratio >= 0.95` per document, zero empty pages, zero placeholder strings). Tables not provided by the customer are never synthesized.

| Track | Active Stages | Graph Engine (`graph_engine`) | Target Scenario |
| :--- | :---: | :---: | :--- |
| **Track 1 · Lite** | `Stage 1 -> 2 -> 4 -> 5(citation)` | `none` | Source documents only (`tables: {}`), no customer tables. `extract_docs.py` + `extract_wiki.py` build `doc_chunks.jsonl`, `entities.md`, and `concepts.md`. Stage 3 is skipped, the agent runs `_lite_cycle()` with `[DOC_CHUNK_XXX]` citations, and Stage 5 scores `evidence_type: "citation"` CQs |
| **Track 2 · Standard** | `Stage 1 -> 2 -> 3 -> 4` | `bigquery` (default) \| `spanner` (opt-in) \| `both` (Graph Fabric) | Structured DW + unstructured rules unified via `STARTER_ONTOLOGY_GRAPH` and ISO GQL |
| **Track 3 · Full** | `Stage 1 -> 2 -> 3 -> 4 -> 5` | `bigquery` (default) \| `spanner` (opt-in) \| `both` (Graph Fabric) | Full lifecycle including end-to-end lineage, Golden CQ 5 (`evidence_type: "sql"`), boundary benchmark (10x5), and Terraform Cloud Run deployment |

### 3.1 5-Axis Graph Engine Selection Checklist & Customer Input Scenario Matrix

In Stage 1 (`project.json` -> `data/output/input_manifest.json`), projects evaluate five axes (`source_system`, `latency_slo`, `concurrency`, `write_freshness`, `data_scale`) to choose `"bigquery"` (Default, Zero-ETL logical graph), `"spanner"` (Opt-in 100 PU online low-latency graph), or `"both"` (Dual-engine ingestion + BigQuery `EXTERNAL_QUERY` Graph Fabric federation over `spanner_fabric_conn`).

| Scenario | Customer Input Assets | `project.json` Settings | Pipeline Execution & Stage Adaptation |
| :--- | :--- | :--- | :--- |
| **Scenario A1 (`lite`)** | Unstructured documents only (`customer_doc/*.pdf, *.docx`) | `"track": "auto"`, `"tables": {}` | `extract_docs.py` (Gate 0 >= 95%) -> `extract_wiki.py` (`entities.md` Node, `concepts.md` Edge) -> Skip Stage 3 -> Stage 4 `_lite_cycle` (300,000-char chunk context) -> Stage 5 `evidence_type: "citation"` CQ scoring |
| **Scenario A2 (Graph Halt)** | Unstructured documents only, but user forces `track: "full"` or `--stage 3` | `"track": "full"`, `"tables": {}` | Halts immediately before Stage 3 with explicit guidance: provide structured tables in `03_tables/` or switch `track` to `"lite"` / `"auto"` (zero synthetic table fabrication) |
| **Scenario B (Standard BigQuery)** | Unstructured documents + structured CSVs | `"track": "auto"`, `"graph_engine": "bigquery"` | Loads customer-supplied tables (`provenance=CUSTOMER_PROVIDED`) into BigQuery and creates `STARTER_ONTOLOGY_GRAPH` (default Zero-ETL) |
| **Scenario C (Spanner / Graph Fabric / Custom)** | Structured tables requiring sub-200ms online GQL or Graph Fabric federation | `"graph_engine": "spanner" \| "both"`, or custom `*_module` overrides | Provisions Cloud Spanner (`starter-spanner`, 100 PU, `starter_ontology_db`), loads all 10 tables, benchmarks BigQuery vs Spanner p50/p95 latency, and executes federated `EXTERNAL_QUERY(spanner_fabric_conn)` joins |

Every ingested record and chunk carries one of three provenance tiers:
- `CUSTOMER_PROVIDED`: Verbatim customer files (`customer_doc/*`, customer CSVs).
- `EXTRACTED`: Chunks, entities, and concept relations extracted from `CUSTOMER_PROVIDED` documents with verified verbatim quotes (`<= 300` chars).
- `SYNTHETIC_DEMO`: Educational demo records inside `projects/telecom_sample` (explicitly badged `[SYNTHETIC_BASIS: NN%]` in Stage 5 reports).

## 4. Runtime Resources & 8 MCP Tools

- **BigQuery Dataset (Default)**: `seanjung-poc.starter_ontology_dw` — 6 node tables (`tb_device_master`, `tb_plan_master`, `tb_subsidy_policy`, `tb_customer_contract`, `tb_domain_rules`, `tb_doc_chunks`), 4 edge tables (`edge_contract_device`, `edge_contract_plan`, `edge_subsidy_binding`, `edge_rule_applies_to_plan`), and `STARTER_ONTOLOGY_GRAPH`.
- **Cloud Spanner Graph (Opt-in 100 PU)**: `starter-spanner/starter_ontology_db` — identical 10 tables and `STARTER_ONTOLOGY_GRAPH` property graph, linked to BigQuery via `projects/924723860007/locations/asia-northeast3/connections/spanner_fabric_conn` (`EXTERNAL_QUERY`).
- **Cloud Storage**: `gs://seanjung-poc-starter-ontology` (`raw/`, `parsed/`, `ontology/` 3-Layer Markdown and manifest).
- **8 MCP Tools**: 5 Stage MCPs (`mcp_stage1_asset_discovery` .. `mcp_stage5_lineage_and_eval`) + 3 Runtime MCPs (`mcp_lookup_customer_profile`, `mcp_calculate_penalty_rule`, `mcp_query_graph_and_wiki`), all supporting `engine="bigquery" | "spanner"`.
