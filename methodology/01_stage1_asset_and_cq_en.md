# Stage 1. Asset Discovery, Scoping and CQ Definition

> Studio [`Stage 1. Asset`](https://agentic-ontology-starter-924723860007.asia-northeast3.run.app/?tab=stage1) · MCP `mcp_stage1_asset_discovery` · Notebook [stage1_asset_and_cq_en.ipynb](../notebooks/en/stage1_asset_and_cq_en.ipynb) · [한국어](./01_stage1_asset_and_cq_ko.md) · [Full methodology](./METHODOLOGY_EN.md)

## Purpose

Decide first which questions (CQ, Competency Questions) the agent must answer, then load only the documents and tables those answers need into BigQuery.
Writing the expected answer and an answer-check SQL for every CQ gives Stage 5 its scoring criteria directly.

## Inputs

| Path (`data/input/`) | Content |
| :--- | :--- |
| `01_guides/sample_policy_guide.md` | Policy guide. Chunks `DOC_CHUNK_001`–`003` (180-day retention duty, penalty formula) |
| `01_guides/sample_welfare_exemption_guide.md` | Exemption guide. Chunks `DOC_CHUNK_004`–`005` (welfare and military exemptions, 24-month cost comparison) |
| `03_tables/devices.csv`, `plans.csv`, `subsidies.csv`, `customer_contracts.csv` | 4 master tables: 4 devices, 6 plans, 5 subsidy policies, 6 customer contracts |
| `03_tables/domain_rules.csv`, `rule_plan_edges.csv` | 4 rules, 12 rule-to-plan links (used in Stage 2) |
| `03_tables/schema_master_tables.sql` | Reference DDL only. The real schema is `terraform/bigquery.tf`; no code reads this file |
| `04_cq/golden_competency_questions.json` | 5 Golden CQs (`CQ-01`–`CQ-05`) |
| `04_cq/boundary_cases.json` | 10 boundary questions (`BQ-01`–`BQ-10`, used in Stage 5) |
| `05_glossary/business_glossary.json` | 4 terms. The current pipeline code does not read it |

Customer IDs are synthetic identifiers in the form `CUST_DEMO_001`–`CUST_DEMO_006`.

Fields of one CQ:

| Field | Use |
| :--- | :--- |
| `query` | Question sent to the agent |
| `expected_value` | Human-readable description of the answer |
| `expected_math` | Answer values used for scoring (e.g. `{"penalty": 100000}`) |
| `verification_sql` | BigQuery SQL that computes the answer independently of the agent. `{fq}` is replaced with `project.dataset` |
| `grounded_chunk` | Chunk ID the answer must cite |
| `target_tools` | Expected tools. Reference only; not used for scoring |

## MCP of this Stage: `mcp_stage1_asset_discovery`

| Step | What the code does (`src/agent/mcp_server.py`) |
| :--- | :--- |
| `profile_tables` | Reads row count and size per table from `__TABLES__` → `table_inventory` |
| `scan_guides` | Not done by this MCP. Guide chunking is done by `run_ingest()` in `pipeline/ingest.py` |
| `prune_noise` | No matching code (step name only) |
| `tag_pii_governance` | Counts `tb_customer_contract.customer_id` values that do not match `^CUST_DEMO_[0-9]{3}$` → `pii_check.non_deidentified_ids` |

The `steps` argument is recorded in `executed_steps` of the result. The current handler runs both queries above regardless of the selected steps.

## Procedure

1. **Set the scope**: keep only the documents and tables needed to answer the CQs. The starter begins with 2 guides and 6 CSV files.
2. **Write the CQs**: fill `expected_math`, `verification_sql` and `grounded_chunk` for every CQ. A person confirms the answers.
3. **Prepare the tables**: the BigQuery dataset and its 10 tables are created with Terraform (`terraform/bigquery.tf`).
4. **Load**: `run_ingest()` reads the 6 CSV files and the guide chunks, empties the 10 tables (`TRUNCATE`) and refills them (`INSERT`). Each table is one transaction; any failure stops the pipeline. Values come only from the CSV files, not from code.
5. **Check**: run `mcp_stage1_asset_discovery` to confirm row counts and the number of de-identification violations.

## Deliverables

| ID | Deliverable | In the starter |
| :--- | :--- | :--- |
| `D1.1` | Domain scoping and noise-filtering charter | No separate document. The sample data defines the scope |
| `D1.2` | Golden CQ and answer verification specification | `data/input/04_cq/golden_competency_questions.json` |
| `D1.3` | Source asset inventory and schema profile | `terraform/bigquery.tf` (schema), MCP result `table_inventory` (rows, size) |
| `D1.4` | Dataplex catalog tagging and governance map | Not implemented in the starter |

## Gate (Gate 1)

- [ ] Every CQ has `expected_math`, `verification_sql` and `grounded_chunk`.
- [ ] The `verification_sql` result equals `expected_math`. The Stage 5 report records it as `SQL_MATCH` in `verification_status`.
- [ ] `pii_check.non_deidentified_ids` is 0.
- [ ] Row counts in `table_inventory` equal the CSV row counts.

## View in the studio

[Open the Stage 1. Asset tab](https://agentic-ontology-starter-924723860007.asia-northeast3.run.app/?tab=stage1)

- Asset list: 4 master tables and 2 guides. Clicking a row shows the CSV records or the chunk text in the right panel.
- Stage 1 MCP button (top right): runs the MCP above on BigQuery and shows the result.

## Notebook

[stage1_asset_and_cq_en.ipynb](../notebooks/en/stage1_asset_and_cq_en.ipynb)

## Apply to your data

1. **Documents**: replace the `.md` files in `data/input/01_guides/`. Mark chunk boundaries with `<!-- DOC_CHUNK_001: Title -->` comments. Without them, the text is split at `## ` headings.
2. **Tables**: if you keep the file names and column names, replacing the CSV rows is enough. File and column names are fixed in `pipeline/ingest.py`. To change the schema, edit `terraform/bigquery.tf`, `pipeline/ingest.py`, `pipeline/graph_builder.py` and `src/agent/mcp_server.py` together.
3. **CQs**: rewrite `golden_competency_questions.json` with the same fields.
4. **De-identification rule**: if your customer IDs use another format, change the regular expression (`^CUST_DEMO_[0-9]{3}$`) in `mcp_stage1_asset_discovery`.
5. **Run**: set the environment variables `GCP_PROJECT_ID`, `BQ_DATASET_ID` and `GCS_WIKI_BUCKET`, then run `python3 run_pipeline.py`.
