# Stage 5. Lineage, Evaluation & Deployment Gate

> Studio [`Stage 5. Lineage & Eval`](https://agentic-ontology-starter-lwrlf7yogq-du.a.run.app/?tab=stage5) · MCP `mcp_stage5_lineage_and_eval` · Notebook [stage5_lineage_and_evaluation_en.ipynb](../../notebooks/en/stage5_lineage_and_evaluation_en.ipynb) · [Korean (KO)](../ko/05_stage5_lineage_and_eval_ko.md) · [Full Methodology](./METHODOLOGY_EN.md)

## Purpose

Trace end-to-end data lineage from raw files (CSVs and policy guides) through BigQuery tables, `STARTER_ONTOLOGY_GRAPH`, and the 8 MCP tools to the agent, then verify the 5 Golden CQs and 10 boundary benchmark cases (×5 runs) before production deployment.

## Inputs

- 10 BigQuery tables and `STARTER_ONTOLOGY_GRAPH`
- Golden CQ suite: `data/input/04_cq/golden_competency_questions.json` (5 questions: `CQ-01`–`CQ-05`)
- Boundary benchmark suite: `data/input/04_cq/boundary_cases.json` (10 cases: `BQ-01`–`BQ-10`)
- Evaluation module: `pipeline/validator.py` (`run_validation`, `run_boundary`)

## Stage MCP: `mcp_stage5_lineage_and_eval`

| Step | Execution (`src/agent/mcp_server.py`) |
| :--- | :--- |
| `build_4tier_lineage` | Joins `tb_customer_contract` → `tb_device_master` / `tb_plan_master` / `tb_subsidy_policy` → `edge_rule_applies_to_plan` → `tb_doc_chunks` (`lineage_records`, 18 rows) |
| `run_golden_cq_suite` | Reads and summarizes the 5 Golden CQ validation results from `data/output/cq_benchmark_report.json` |
| `diagnose_boundary_failures` | Inspects pass rate, consistency rate, intent stability, and per-case diagnostics from `data/output/boundary_benchmark_results.json` |

## Studio Lineage DAG (`config/lineage_spec.json`)

Part A of `Stage 5. Lineage & Eval` is the same canvas DAG as the main studio lineage view (`src/lineage/lineage_engine.py`, `/api/lineage/{graph,trace,explain}`).

- Spec: 7 category columns (data connection → GCP raw sources → data transformations → domain rules → ontology semantic → MCP → agents and evaluation), 3 presets, nodes, and edges. The sample has 37 nodes and 67 edges; each column is centred vertically.
- Structure rule: list only resources that the pipeline code actually reads or writes (GCS `raw/`, `parsed/`, `ontology/` uploads in `pipeline/ingest.py`, the 10 BigQuery tables, the Spanner graph when `graph_engine` is `spanner` or `both`, and agent final answer → rubric judge in `pipeline/validator.py`). Do not add virtual connectors or missing tables; update the spec when the code changes.
- Volumes are measured on request (120 s cache): `bq_table` → BigQuery `__TABLES__` row count, `gcs_prefix` → GCS object count, `bq_graph` / `spanner_graph` → node and edge table count from `INFORMATION_SCHEMA.PROPERTY_GRAPHS`. A failed lookup is shown as `lookup failed` and is not replaced by another value. Only nodes without a measurement key (such as MCP tools) show the spec text.
- There is no hidden layer. Domain rules are always shown in their own column.
- Clicking a node highlights its upstream and downstream paths (BFS) and opens a detail panel (metadata, volume source, direct upstream and downstream, rule-based summary) with a link to the Stage 4 agent.
- Per-project specs live in `projects/<id>/config/lineage_spec.json` (see [`projects/_template/README.md`](../../projects/_template/README.md)).

### Recommended lineage structure

- Structured: one box per table. A table and its graph label share one box.
- Unstructured: RAW → parsing → parsed → re-extraction gate → `latest` → one box per ontology document. Relations between documents are not drawn as edges; their count is shown on the document box.
- Edge tables: one box per kind.
- Agent inputs: the Wiki Agent reads the ontology `latest` on GCS (no BigQuery box); the BQG Agent reads the Property Graph.
- A remote MCP server box that re-exposes the same full tool set is omitted (it adds no lineage information).

The starter spec (`config/lineage_spec.json`) has one box per structured table (`RAW_TB_*`), one box per edge-table kind (`TR_EDGE_*`) and no remote MCP server box. Unstructured data flows guides → chunker (`TR_CHUNKER`) → GCS `parsed/` and a single Wiki box (`SEM_WIKI`); there is no re-extraction gate, no `latest` and no per-document box. There is one agent box, `AGENT_FDE`.

## Procedure (`pipeline/validator.py`)

1. **Record-level lineage join (`build_4tier_lineage`)**:
   - Tier 0 (Raw Files): `sample_policy_guide.md`, `sample_welfare_exemption_guide.md`, 6 CSV files (or external customer documents/tables)
   - Tier 1 (Anchored Chunks): `tb_doc_chunks` (`DOC_CHUNK_001`–`005`, `content_sha256`, `origin_type`, `extract_method`, `source_locator`)
   - Tier 2 (Domain Rules & Bridges): `tb_domain_rules`, `edge_rule_applies_to_plan` (or `03_wiki/entities.md`, `concepts.md`)
   - Tier 3 (Contracts & Property Graph): `tb_customer_contract` and `STARTER_ONTOLOGY_GRAPH`
   - Tier 4 (Golden CQ Answers): `CQ-01`–`CQ-05` agent responses and grounded citations
2. **Golden CQ Validation (`run_validation`) — `evidence_type` Branching**:
   - **`evidence_type: "sql"` (`full` track)**: Verifies that independent BigQuery `verification_sql` matches `expected_math` and that the live agent answer (`AiFdeAgentEngine.execute_cycle`) contains the exact numbers and `grounded_chunk`.
   - **`evidence_type: "citation"` (`lite` track)**: Verifies that the document-context agent answer (`_lite_cycle`) cites `grounded_chunk` (`DOC_CHUNK_XXX`) and includes at least one keyword from `expected_keywords`.
   - **`status: "UNCONFIRMED"` CQs**: Questions without customer-confirmed ground truth are counted separately in `unconfirmed_cq_count` rather than being auto-passed as 100%.
   - **Final-answer rubric (`_judge`)**: Value-presence checks alone can pass an answer that addresses a different question. An LLM judge (same Gemini model) therefore scores the agent's final answer: relevance 20 · accuracy 30 · completeness 20 · grounding 15 · actionability 15. The judge sees only the question, the expected answer, the tool outputs the agent actually retrieved, and the text of the chunks it cited. Relevance below 8 caps the total at 40; each number not found in the evidence costs grounding at least 3 points. A verdict other than `PASS` marks the CQ `FAILED` (`RUBRIC_PARTIAL` / `RUBRIC_FAIL`).
   - **Duplicate-answer check**: If two different CQs get answers with 3-gram Jaccard ≥ 0.5, both fail with `DUPLICATE_ANSWER`. Identical answers to different questions mean retrieval or generation ignored the question.
   - Do not raise scores by preloading answers or evidence, or by returning fixed responses. Improve scores only through prompts and retrieval logic.
3. **Execution Provenance Metadata (`cq_benchmark_report.json`)**:
   - Every validation report records the input file hash (`input_manifest_sha256`), provenance tier (`evidence_provenance`), synthetic data flag (`synthetic_basis`), and unconfirmed CQ count (`unconfirmed_cq_count`).
   ```json
   {
     "run_id": "val_20260929_143012",
     "project_id": "telecom_sample",
     "track": "full",
     "evaluated_at": "2026-09-29T14:30:12+09:00",
     "input_manifest_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
     "evidence_provenance": "CUSTOMER_PROVIDED",
     "synthetic_basis": false,
     "unconfirmed_cq_count": 0,
     "total_cqs": 5,
     "passed": 5,
     "accuracy_rate": 100.0
   }
   ```
4. **Studio Evaluation Badge States**:
   - **`NOT_EVALUATED`**: No report file or missing `run_id`.
   - **`STALE_EVALUATION` (Re-evaluation required after input change)**: Current project input file SHA-256 differs from `input_manifest_sha256` in the report.
   - **`SYNTHETIC_BASIS: NN%`**: When `SYNTHETIC_DEMO` rows are present (`synthetic_basis: true`), the score is explicitly badged so demo scores are never mistaken for customer production data.
   - **`UNCONFIRMED: N cases`**: Displays confirmed CQ pass rate separately from `unconfirmed_cq_count`.
5. **Boundary Benchmark (`run_boundary`)**:
   - Executes 10 boundary questions (`GROUNDED`, `MATCH_NOT_FOUND`, `INSUFFICIENT_PARAMETERS`) for 5 iterations (50 live runs) and records `avg_success_rate`, `avg_consistency_rate`, and `avg_intent_stability` in `data/output/boundary_benchmark_results.json`.

## Recommended method: evaluation screen layout

- Evaluation screen order: A overall results → B CQ verification → C rubric criteria.
- Rubric dimension names, definitions and judge instructions have Korean fields (`name_ko`, `desc_ko`, `judge_instructions_ko`) shown in Korean mode. The judge script keeps using the base fields.
- Selecting a CQ shows the actual agent answer, the ground truth, per-dimension scores, deduction reasons and the retrieved evidence (chunks, rules, executed queries with job IDs).
- The Overview shows only a summary: dimension averages, number of CQs with deductions, per-CQ score and a short evidence and deduction summary. It links to the evaluation screen for detail.

The current starter implementation differs. The Stage 5 tab shows the Golden CQ table (expected, actual, evidence anchor, verdict) and the boundary table (`src/web/studio_server.py`). There is no per-CQ detail (dimension scores, deduction reasons, retrieved evidence), and `config/eval_rubric.json` has a single `description` field per dimension.

## Deliverables

| ID | Deliverable | In This Starter |
| :--- | :--- | :--- |
| `D5.1` | End-to-End Data Lineage & Impact Map | Studio `Stage 5. Lineage & Eval` lineage DAG (`config/lineage_spec.json`) and `mcp_stage5_lineage_and_eval` (`lineage_records`) |
| `D5.2` | PII Masking & Access Governance Policy | Pseudonymous contract IDs (`CUST_DEMO_001`–`006`) in `tb_customer_contract` |
| `D5.3` | Golden CQ Validation Report | `data/output/cq_benchmark_report.json` (with `input_manifest_sha256` and `synthetic_basis`) |
| `D5.4` | Boundary & Consistency Benchmark Report | `data/output/boundary_benchmark_results.json` (10 cases × 5 runs = 50 live executions) |
| `D5.5` | Production Deployment Package (Docker & Terraform) | `Dockerfile` and `terraform/` (`main.tf`, `bigquery.tf`, `storage.tf`, `iam.tf`, `cloud_run.tf`) |

## Gate 5 (Production Release Gate)

- [ ] Confirmed Golden CQs achieve `100.0%` pass rate and `input_manifest_sha256` matches current inputs (`cq_benchmark_report.json`).
- [ ] Every final answer gets a rubric verdict of `PASS` and `duplicate_pairs` is empty (`rubric_avg_total`, `rubric_axis_avg` recorded).
- [ ] Boundary benchmark (`10 × 5`) verifies `GROUNDED`, `MATCH_NOT_FOUND`, and `INSUFFICIENT_PARAMETERS` guardrails in `boundary_benchmark_results.json`.
- [ ] Zero hardcoded secrets (`AIza...`), customer identifiers, or local paths (`/<local-home>/`).
- [ ] `terraform apply` succeeds and Cloud Run `/api/portal/profile` returns HTTP 200.

## View in Studio

[Open Stage 5. Lineage & Eval Tab](https://agentic-ontology-starter-lwrlf7yogq-du.a.run.app/?tab=stage5)

## Notebook

[stage5_lineage_and_evaluation_en.ipynb](../../notebooks/en/stage5_lineage_and_evaluation_en.ipynb) · [Korean Notebook](../../notebooks/ko/stage5_lineage_and_evaluation_ko.ipynb)

## Adapting to Your Data

1. Define your domain's Golden CQs in `data/input/04_cq/golden_competency_questions.json` (`"evidence_type": "sql"`, `"verification_sql"`, `"expected_math"` for `full` track; `"evidence_type": "citation"`, `"expected_keywords"`, `"grounded_chunk"` for `lite` track).
2. Add boundary test cases (`GROUNDED`, `MATCH_NOT_FOUND`, `INSUFFICIENT_PARAMETERS`) in `data/input/04_cq/boundary_cases.json`.
3. Run `python3 pipeline/validator.py --project <id>` to regenerate the evaluation reports.
