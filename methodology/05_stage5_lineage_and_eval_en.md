# Stage 5. Lineage, Evaluation & Deployment Gate

> Studio [`Stage 5. Lineage & Eval`](https://agentic-ontology-starter-924723860007.asia-northeast3.run.app/?tab=stage5) · MCP `mcp_stage5_lineage_and_eval` · Notebook [stage5_lineage_and_evaluation_en.ipynb](../notebooks/stage5_lineage_and_evaluation_en.ipynb) · [한국어](./05_stage5_lineage_and_eval_ko.md) · [Full Methodology](./METHODOLOGY_EN.md)

## Purpose

Trace 4-tier data lineage from raw files (CSVs and policy guides) through BigQuery tables, `STARTER_ONTOLOGY_GRAPH`, and the 8 MCP tools to the agent, then verify the 5 Golden CQs and 10 boundary benchmark cases (×5 runs) before production deployment.

## Inputs

- 10 BigQuery tables and `STARTER_ONTOLOGY_GRAPH`
- Golden CQ suite: `data/input/04_eval/sample_cq_eval.json` (5 questions: `CQ_001`–`CQ_005`)
- Boundary benchmark suite: `data/input/04_eval/boundary_eval_10.json` (10 cases: `BND_001`–`BND_010`)
- Evaluation module: `src/eval/boundary_eval.py` (`run_validation`, `run_boundary_benchmark`)

## Stage MCP: `mcp_stage5_lineage_and_eval`

| Step | Execution (`src/agent/mcp_server.py`) |
| :--- | :--- |
| `build_4tier_lineage` | Queries live row counts across the 10 BigQuery tables and builds the 4-tier lineage map (Raw → BigQuery → Property Graph → MCP & Agent) |
| `run_golden_cq_suite` | Reads or summarizes the 5 Golden CQ validation results from `data/output/validation_report.json` |
| `diagnose_boundary_failures` | Returns pass rate, consistency rate, intent stability rate, and per-case diagnostics from `data/output/boundary_eval_report.json` |

## Procedure (`src/eval/boundary_eval.py`)

1. **4-Tier Lineage Mapping**:
   - Tier 1 (Raw Assets): `sample_policy_guide.md`, `sample_welfare_exemption_guide.md`, 6 CSV files
   - Tier 2 (BigQuery DW & Chunks): 6 node tables + 4 edge tables in `starter_ontology_dw`
   - Tier 3 (Semantic & Property Graph): `ontology.jsonld` and `STARTER_ONTOLOGY_GRAPH`
   - Tier 4 (MCP & Agent): 5 Stage MCPs + 3 Runtime MCPs → `AiFdeAgentEngine` (`gemini-3.8-flash`)
2. **Golden CQ Validation (`run_validation`)**:
   - Verifies that every Golden CQ (`CQ_001`–`CQ_005`) resolves its target BigQuery tables, rules, and lexical chunk anchors, writing `data/output/validation_report.json`.
3. **Boundary Benchmark (`run_boundary_benchmark`)**:
   - Executes 10 boundary questions (`GROUNDED`, `MATCH_NOT_FOUND`, `INSUFFICIENT_PARAMETERS`) for 5 iterations (50 live runs) and records `overall_pass_rate`, `consistency_rate`, and `intent_stability_rate` in `data/output/boundary_eval_report.json`.
4. **Iterative Refinement (Hill-Climbing)**:
   - Any failing case is traced back to missing wiki chunks, rule conditions, or MCP parameter validation guards, fixed at the source layer, and re-evaluated.

## Deliverables

| ID | Deliverable | In This Starter |
| :--- | :--- | :--- |
| `D5.1` | End-to-End Data Lineage & Impact Map | Studio `Stage 5. Lineage & Eval` lineage view and `mcp_stage5_lineage_and_eval` |
| `D5.2` | PII Masking & Access Governance Policy | Pseudonymous contract IDs (`CUST_DEMO_001`–`005`) in `tb_customer_contracts` |
| `D5.3` | Golden CQ Validation Report | `data/output/validation_report.json` (5/5 pass, 100.0%) |
| `D5.4` | Boundary & Consistency Benchmark Report | `data/output/boundary_eval_report.json` (10 cases × 5 runs = 50 live executions) |
| `D5.5` | Production Deployment Package (Docker & Terraform) | `Dockerfile` and `terraform/` (`main.tf`, `bigquery.tf`, `storage.tf`, `iam.tf`, `cloud_run.tf`) |

## Gate 5 (Production Release Gate)

- [ ] Golden CQ 5/5 pass rate (`100.0%` in `validation_report.json`).
- [ ] Boundary benchmark (`10 × 5`) verifies `GROUNDED`, `MATCH_NOT_FOUND`, and `INSUFFICIENT_PARAMETERS` guardrails.
- [ ] Zero hardcoded secrets (`AIza...`), customer identifiers, or local paths (`/<local-home>/`).
- [ ] `terraform validate` succeeds and Cloud Run `/api/status` returns HTTP 200.

## View in Studio

[Open Stage 5. Lineage & Eval Tab](https://agentic-ontology-starter-924723860007.asia-northeast3.run.app/?tab=stage5)

## Notebook

[stage5_lineage_and_evaluation_en.ipynb](../notebooks/stage5_lineage_and_evaluation_en.ipynb)

## Adapting to Your Data

1. Define your domain's Golden CQs in `data/input/04_eval/sample_cq_eval.json`.
2. Add boundary test cases (`GROUNDED`, `MATCH_NOT_FOUND`, `INSUFFICIENT_PARAMETERS`) in `data/input/04_eval/boundary_eval_10.json`.
3. Run `python3 -m src.eval.boundary_eval` to regenerate both reports.
