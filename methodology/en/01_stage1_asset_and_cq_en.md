# Stage 1. Asset Discovery, Scoping and CQ Definition

> Studio [`Stage 1. Asset`](https://agentic-ontology-starter-924723860007.asia-northeast3.run.app/?tab=stage1) · MCP `mcp_stage1_asset_discovery` · Notebook [stage1_asset_and_cq_en.ipynb](../../notebooks/en/stage1_asset_and_cq_en.ipynb) · [Korean (KO)](../ko/01_stage1_asset_and_cq_ko.md) · [Full methodology](./METHODOLOGY_EN.md)

## Purpose

Decide first which questions (CQ, Competency Questions) the agent must answer, then load only the documents and tables those answers need into BigQuery.
Scope is chosen per file. Sentences inside a chosen file are not shortened or edited.
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

Customer IDs are synthetic identifiers in the form `CUST_DEMO_001`–`CUST_DEMO_006`. Every row of the sample CSV files has `provenance=SYNTHETIC_DEMO` and `source_ref=project.json#synthetic`.

Fields of one CQ:

| Field | Use |
| :--- | :--- |
| `query` | Question sent to the agent. IDs and quoted names in it must exist in the chunks or tables |
| `evidence_type` | `sql` (table evidence) or `citation` (document evidence) |
| `expected_citation` | For citation CQs: the evidence `chunk_id` and the source passage `quote`. The quote must appear in the chunk verbatim |
| `expected_facts` | For citation CQs: source expressions the answer must contain |
| `answer_confirmed_by`, `confirmed_at` | Person and time that confirmed the answer. Empty means "answer not confirmed" |
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

1. **Set the scope**: choose the documents and tables needed to answer the CQs, per file. Do not shorten or edit sentences inside a file. The starter begins with 2 guides and 6 CSV files.
2. **Write the CQs**: fill `expected_math`, `verification_sql` and `grounded_chunk` for sql CQs, and `expected_citation` and `expected_facts` for citation CQs. A person confirms the answers and is recorded in `answer_confirmed_by`.
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

- [ ] If customer documents exist, Gate 0 (`data/output/gate0_report.json`) is `PASS`.
- [ ] Every CQ has `evidence_type` `sql` or `citation`. sql CQs have `expected_math`, `verification_sql` and `grounded_chunk`; citation CQs have an `expected_citation` that appears verbatim in the chunk. `load_cqs()` in `pipeline/validator.py` checks this.
- [ ] For sql CQs, the `verification_sql` result equals `expected_math`. The Stage 5 report records it as `SQL_MATCH` in `verification_status`.
- [ ] `pii_check.non_deidentified_ids` is 0.
- [ ] Row counts in `table_inventory` equal the CSV row counts.

## View in the studio

[Open the Stage 1. Asset tab](https://agentic-ontology-starter-924723860007.asia-northeast3.run.app/?tab=stage1)

- Asset list: 4 master tables and 2 guides. Clicking a row shows the CSV records or the chunk text in the right panel.
- Stage 1 MCP button (top right): runs the MCP above on BigQuery and shows the result.

## Notebook

[stage1_asset_and_cq_en.ipynb](../../notebooks/en/stage1_asset_and_cq_en.ipynb)

## Apply to your data

1. **Documents**: put the originals (PDF, DOCX) in `customer_doc/` and run `python3 pipeline/extract_docs.py --project <id>`. The full source text is converted to `01_guides/*.md`, and chunks are split automatically by article, heading or paragraph (max 1,500 characters). Do not summarize or rewrite the source. Gate 0: source character ratio of 95% or more per document. `DOC_CHUNK` comments are for the sample only.
2. **Tables**: put only tables the customer provided in `03_tables/` and register them in `tables` of `project.json`. Every row has `provenance` and `source_ref`. If there are no customer tables, leave the folder empty and use the lite track. Do not fill it with sample or synthetic data. If the schema differs from the sample, change `terraform/bigquery.tf` and the `*_module` overrides in `project.json` together.
3. **CQs**: write document-based CQs with `evidence_type: citation` and table-based CQs with `evidence_type: sql`. IDs and names used in questions must exist in the chunks or tables. A person confirms each answer and is recorded in `answer_confirmed_by`.
4. **De-identification rule**: if your customer IDs use another format, change the regular expression (`^CUST_DEMO_[0-9]{3}$`) in `mcp_stage1_asset_discovery`.
5. **Run**: run `python3 run_pipeline.py --project <id>`. It converts the source documents and runs Gate 0 first; if Gate 0 fails, nothing is loaded.

### Conversion Output Examples (`extract_docs.py`, `gate0_report.json`, `golden_competency_questions.json`)

#### 1) Verbatim Document Extraction (`01_guides/01_telecom_terms.md`)
```markdown
<!-- provenance: source_file=customer_doc/telecom_service_terms.pdf sha256=8f9d2a1c4b... extracted_at=2026-09-29T12:00:00Z -->
# Mobile Service Terms and Conditions

<!-- page: 1 -->
Article 1 (Purpose) These Terms govern the rights, obligations, and responsibilities between the company and subscribers.

Article 18 (Subsidy Clawback and Exemptions)
1. If a subscriber lowers the rate plan before 180 days of mandatory retention, a prorated penalty is charged on the subsidy difference.
2. Subscribers aged 65 or older (SENIOR_EXEMPT) or enlisting for mandatory military service are exempt from the clawback penalty (0 KRW).
```

#### 2) Gate 0 Fidelity Report (`data/output/gate0_report.json`)
```json
{
  "project_id": "my_project",
  "checked_at": "2026-09-29T12:00:02+09:00",
  "gate0_passed": true,
  "threshold_ratio": 0.95,
  "documents": [
    {
      "source_file": "customer_doc/telecom_service_terms.pdf",
      "output_markdown": "01_guides/01_telecom_terms.md",
      "source_chars": 48210,
      "extracted_chars": 47950,
      "char_retention_ratio": 0.9946,
      "empty_pages": [],
      "placeholder_detected": false,
      "status": "PASS"
    }
  ]
}
```

#### 3) Golden CQ Schema Examples (`sql` Track vs `citation` Track)
```json
[
  {
    "cq_id": "CQ-02",
    "evidence_type": "sql",
    "status": "CONFIRMED",
    "answer_confirmed_by": "domain_lead@example.com",
    "query": "If customer CUST_DEMO_001 switches from 5G Signature (130,000 KRW) to 5G Slim (55,000 KRW) at 90 days, what is the penalty?",
    "expected_math": { "penalty": 150000 },
    "verification_sql": "SELECT CAST(ROUND((500000 - 200000) * (180 - 90) / 180.0) AS INT64) AS penalty",
    "grounded_chunk": "DOC_CHUNK_002"
  },
  {
    "cq_id": "CQ-LITE-01",
    "evidence_type": "citation",
    "status": "CONFIRMED",
    "answer_confirmed_by": "policy_owner@example.com",
    "query": "Under what conditions is a subscriber exempt from the 180-day subsidy clawback penalty?",
    "expected_keywords": ["65", "SENIOR_EXEMPT", "0 KRW"],
    "grounded_chunk": "DOC_CHUNK_004"
  }
]
```
