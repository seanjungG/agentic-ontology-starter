# Stage 5. Lineage, Evaluation & Deployment Gate

> Studio [`Stage 5. Lineage & Eval`](https://agentic-ontology-starter-lwrlf7yogq-du.a.run.app/?tab=stage5) · MCP `mcp_stage5_lineage_and_eval` · Notebook [stage5_lineage_and_evaluation_en.ipynb](../../notebooks/en/stage5_lineage_and_evaluation_en.ipynb) · [Korean (KO)](../ko/05_stage5_lineage_and_eval_ko.md) · [Full Methodology](./METHODOLOGY_EN.md)

## Purpose

Trace 4-tier data lineage from raw files (CSVs and policy guides) through BigQuery tables, `STARTER_ONTOLOGY_GRAPH`, and the 8 MCP tools to the agent, then verify the 5 Golden CQs and 10 boundary benchmark cases (×5 runs) before production deployment.

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

- Spec: category columns (data connection → raw sources → transformations → PII and validation rules → ontology semantic → MCP → agents), presets, nodes, and edges. The sample has 36 nodes and 53 edges.
- Volume: nodes with `bq_table` show the live BigQuery `__TABLES__` row count (green badge); other nodes show the value written in the spec.
- The PII column is hidden by default; edges through hidden nodes are drawn from upstream to downstream (sample: hidden 31/45, shown 36/53).
- Clicking a node highlights its upstream and downstream paths (BFS) and opens a detail panel (metadata, volume source, direct upstream and downstream, rule-based summary) with a link to the Stage 4 agent.
- Per-project specs live in `projects/<id>/config/lineage_spec.json` (see [`projects/_template/README.md`](../../projects/_template/README.md)).

## Procedure (`pipeline/validator.py`)

1. **4-Tier Lineage Mapping**:
   - Tier 0 (Raw Files): `sample_policy_guide.md`, `sample_welfare_exemption_guide.md`, 6 CSV files
   - Tier 1 (Anchored Chunks): `tb_doc_chunks` (`DOC_CHUNK_001`–`005`, `content_sha256`)
   - Tier 2 (Domain Rules & Bridges): `tb_domain_rules`, `edge_rule_applies_to_plan`
   - Tier 3 (Contracts & Property Graph): `tb_customer_contract` and `STARTER_ONTOLOGY_GRAPH`
   - Tier 4 (Golden CQ Answers): `CQ-01`–`CQ-05` agent responses and grounded citations
2. **Golden CQ Validation (`run_validation`)**:
   - Verifies that independent BigQuery `verification_sql` matches `expected_math` and that the live agent answer (`AiFdeAgentEngine`) contains the exact numbers and `grounded_chunk`, writing `data/output/cq_benchmark_report.json`.
3. **Boundary Benchmark (`run_boundary`)**:
   - Executes 10 boundary questions (`GROUNDED`, `MATCH_NOT_FOUND`, `INSUFFICIENT_PARAMETERS`) for 5 iterations (50 live runs) and records `avg_success_rate`, `avg_consistency_rate`, and `avg_intent_stability` in `data/output/boundary_benchmark_results.json`.

## Deliverables

| ID | Deliverable | In This Starter |
| :--- | :--- | :--- |
| `D5.1` | End-to-End Data Lineage & Impact Map | Studio `Stage 5. Lineage & Eval` lineage DAG (`config/lineage_spec.json`) and `mcp_stage5_lineage_and_eval` (`lineage_records`) |
| `D5.2` | PII Masking & Access Governance Policy | Pseudonymous contract IDs (`CUST_DEMO_001`–`006`) in `tb_customer_contract` |
| `D5.3` | Golden CQ Validation Report | `data/output/cq_benchmark_report.json` (5/5 pass, 100.0%) |
| `D5.4` | Boundary & Consistency Benchmark Report | `data/output/boundary_benchmark_results.json` (10 cases × 5 runs = 50 live executions) |
| `D5.5` | Production Deployment Package (Docker & Terraform) | `Dockerfile` and `terraform/` (`main.tf`, `bigquery.tf`, `storage.tf`, `iam.tf`, `cloud_run.tf`) |

## Gate 5 (Production Release Gate)

- [ ] Golden CQ 5/5 pass rate (`100.0%` in `cq_benchmark_report.json`).
- [ ] Boundary benchmark (`10 × 5`) verifies `GROUNDED`, `MATCH_NOT_FOUND`, and `INSUFFICIENT_PARAMETERS` guardrails in `boundary_benchmark_results.json`.
- [ ] Zero hardcoded secrets (`AIza...`), customer identifiers, or local paths (`/<local-home>/`).
- [ ] `terraform apply` succeeds and Cloud Run `/api/portal/profile` returns HTTP 200.

## View in Studio

[Open Stage 5. Lineage & Eval Tab](https://agentic-ontology-starter-lwrlf7yogq-du.a.run.app/?tab=stage5)

## Notebook

[stage5_lineage_and_evaluation_en.ipynb](../../notebooks/en/stage5_lineage_and_evaluation_en.ipynb) · [Korean Notebook](../../notebooks/ko/stage5_lineage_and_evaluation_ko.ipynb)

## Adapting to Your Data

1. Define your domain's Golden CQs (`expected_math`, `verification_sql`, `grounded_chunk`) in `data/input/04_cq/golden_competency_questions.json`.
2. Add boundary test cases (`GROUNDED`, `MATCH_NOT_FOUND`, `INSUFFICIENT_PARAMETERS`) in `data/input/04_cq/boundary_cases.json`.
3. Run `python3 pipeline/validator.py` to regenerate both reports.
