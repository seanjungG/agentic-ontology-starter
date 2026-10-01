# Stage 4. MCP and Agent Orchestration

> Studio [`Stage 4. Agent & MCP`](https://agentic-ontology-starter-924723860007.asia-northeast3.run.app/?tab=stage4) · MCP `mcp_stage4_agent_orchestration` + 3 runtime MCPs · Notebook [stage4_agent_and_mcp_execution_en.ipynb](../../notebooks/en/stage4_agent_and_mcp_execution_en.ipynb) · [Korean (KO)](../ko/04_stage4_agent_and_mcp_ko.md) · [Full methodology](./METHODOLOGY_EN.md)

## Purpose

The agent splits a question into parameters and sub-goals, calls the 8 MCP tools against the selected graph engine (`engine="bigquery"` default or `engine="spanner"`), and answers only with values found in the tool results.
Each answer carries the rule ID, the evidence chunk ID, and the backend execution identifier (BigQuery job ID or Spanner database ID).

## Inputs

- The user question (natural language) and graph engine selection (`"bigquery"` default \| `"spanner"`)
- The 10 tables and `STARTER_ONTOLOGY_GRAPH` in BigQuery (`starter_ontology_dw`) or Cloud Spanner (`starter-spanner/starter_ontology_db`) (Stages 1 to 3)
- A Vertex AI Gemini model (environment variable `VERTEX_GEMINI_MODEL`, default `gemini-3.8-flash`)

The full list of the 8 MCPs is in section 4 of [METHODOLOGY_EN.md](./METHODOLOGY_EN.md). All of them are in `DomainMcpServer` in `src/agent/mcp_server.py` and support `engine="bigquery" | "spanner"`.

## MCP of this Stage

### `mcp_stage4_agent_orchestration`

| Step | What the code does (`engine="bigquery" \| "spanner"`) |
| :--- | :--- |
| `decompose_subgoals` | Not done by this MCP. The agent decomposes the question with Gemini |
| `dispatch_domain_mcps` | Not done by this MCP. The agent calls the tools |
| `verify_grounding_anchors` | Reads the 4 rules and their evidence chunk anchors (`tb_domain_rules` joined with `tb_doc_chunks`) on the selected engine → `active_rules` |

The `steps` argument is recorded in `executed_steps` of the result.

### The 3 runtime MCPs

Common arguments (`resolve_params`): `customer_id`, `device_name`, `storage_gb`, `plan_name`, `monthly_fee_krw`, `target_plan_name`, `target_monthly_fee_krw`, `elapsed_days`, `engine` (`"bigquery"` default \| `"spanner"`).
If only `query` (natural language) is given, numbers and catalog names are extracted from the question with fixed rules. Device and plan names that are not in the catalog are dropped.

| Tool | Steps | What it does (supports both `bigquery` and `spanner`) | Returned status |
| :--- | :--- | :--- | :--- |
| `mcp_lookup_customer_profile` | `lookup_contract`, `lookup_device_price`, `lookup_subsidy_policy` | Joins contract, device, plan and subsidy on the selected engine, computes the total subsidy and the installment principal, and attaches the evidence chunk of `RULE_SUBSIDY_CAP` | `SUCCESS`, `MATCH_NOT_FOUND` (returns the actual plan and subsidy lists) |
| `mcp_calculate_penalty_rule` | `check_exemptions`, `compute_180d_prorated_clawback`, `compare_24m_tco` | Computes the penalty decision and the 24-month cost comparison in one SQL query on the selected engine (order below) | `SUCCESS`, `INSUFFICIENT_PARAMETERS` (neither customer ID nor device), `MATCH_NOT_FOUND` |
| `mcp_query_graph_and_wiki` | `traverse_property_graph`, `fetch_okf_hash_anchor`, `verify_dw_schema` | Traverses paths with `GRAPH_TABLE` on the selected engine and joins the evidence chunk text ([Stage 3 GQL patterns](./03_stage3_property_graph_en.md)) | `SUCCESS`, `MATCH_NOT_FOUND` |

Every tool returns a backend query error as `BQ_QUERY_ERROR` or `SPANNER_QUERY_ERROR` (it is not turned into 0 rows).

Decision order of `mcp_calculate_penalty_rule`:

1. Welfare exemption (`welfare_status = 'SENIOR_EXEMPT'`) → `EXEMPT_WELFARE`, 0 KRW
2. No public subsidy policy → `NOT_APPLICABLE_NO_PUBLIC_SUBSIDY`, 0 KRW
3. Target plan or elapsed days unknown → `TARGET_PLAN_NOT_RESOLVED` / `ELAPSED_DAYS_MISSING`
4. Elapsed days ≥ required retention days → `EXEMPT_RETENTION_COMPLETED`, 0 KRW
5. Target plan fee ≥ baseline fee (lowest monthly fee among plans with minimum retention days) → `NO_PENALTY_ABOVE_BASELINE`, 0 KRW
6. Otherwise → `PRORATED_PENALTY`, `(initial public subsidy - public subsidy of the target plan) × (retention days - elapsed days) / retention days`

The 24-month cost is computed for both paths: public subsidy `(factory price - total subsidy) + monthly fee × 24` and selective discount `factory price + monthly fee × (1 - discount rate) × 24`.

## Procedure (`AiFdeAgentEngine.execute_cycle()` in `src/agent/reasoning_engine.py`)

### 1) `full` Track (2-Pass MCP Orchestration)

1. **Catalog**: read the device, plan and customer lists from BigQuery (5-minute cache).
2. **Decomposition (Gemini call 1)**: turn the question into parameter JSON and sub-goals (tool choices). Only catalog names are allowed.
3. **Validation**: fees and day counts must be numbers written in the question. Names not in the catalog are dropped. If the Gemini call fails, rule-based extraction is used instead.
4. **Tool calls**: run the MCPs in sub-goal order. When runtime tools are used, `mcp_query_graph_and_wiki` is added as the evidence step.
5. **Answer status**: set from the tool statuses in the order `BQ_ERROR` → `MATCH_NOT_FOUND` → `INSUFFICIENT_PARAMETERS` → `GROUNDED`. If answer generation fails, the status is `LLM_ERROR`.
6. **Answer (Gemini call 2)**: uses only the tool result JSON as evidence. Order: conclusion → evidence data → rules and chunks → related information (exceptions, caveats) → execution info (job IDs). The conclusion applies the question's conditions to the rules and gives one answer; if it depends on a condition, it is split by condition. Stage 5 scores the final answer with a rubric.

Each question calls Gemini twice, and the result records the token count and the BigQuery job IDs.

### 2) `lite` Track (1-Pass Document-Chunk Context Runtime: `execute_lite_doc_cycle()`)

For document-only projects (`track: "lite"`) without structured customer tables, the engine bypasses BigQuery SQL MCPs and answers directly from the project's `doc_chunks.jsonl` and `03_wiki/entities.md` · `concepts.md` context (up to `300,000` characters).

- **Mandatory Citation**: Every factual claim in the response must cite a valid chunk ID in `[DOC_CHUNK_XXX]` format.
- **Citation Verification Statuses**:
  - `GROUNDED`: Every cited `[DOC_CHUNK_XXX]` exists in the project's `doc_chunks.jsonl`.
  - `NO_CITATION`: The response failed to include any `[DOC_CHUNK_XXX]` citation.
  - `INVALID_CITATION`: The response cited a chunk ID that does not exist in `doc_chunks.jsonl`.
  - `CONTEXT_LIMIT`: Total document chunk characters exceeded the `300,000`-character context limit.

### Tool granularity and composite questions

- Each tool has one lookup responsibility (for example subsidy lookup, penalty calculation, rule and chunk check) and returns its status and BigQuery job ID with the result. Empty slots are never filled with hard-coded or default values.
- Tools that return the same data under different names are merged into one; the others remain as aliases.
- A composite question (several conditions or entities) is split into several tool calls during planning, and the answer is written from tool results only. If a required value is not in the data, the agent says so instead of estimating it.
- Check tool coverage with questions outside the evaluation set (other device, plan and day combinations from the catalog). Record possible overfitting when a score was tuned on the same questions.

## Deliverables

| ID | Deliverable | In the starter |
| :--- | :--- | :--- |
| `D4.1` | Ontology MCP server spec and implementation | `src/agent/mcp_server.py` (`DomainMcpServer`, 8 tools) |
| `D4.2` | AI FDE semantic routing and multi-goal decomposition engine | `src/agent/reasoning_engine.py` (`AiFdeAgentEngine`) |
| `D4.3` | Cross-domain context passing and hand-off protocol | No separate document. `execute_cycle()` passes one validated parameter set to every tool in the same format |
| `D4.4` | MCP boundary test suite and improvement report | No tool-level boundary suite. The 10 agent-level boundary questions are covered in [Stage 5](./05_stage5_lineage_and_eval_en.md) |

## Gate (Gate 4)

- [ ] `get_tool_catalog()` returns 8 tools (the studio catalog shows 8).
- [ ] Golden CQ questions end with answer status `GROUNDED`, and the answer contains the evidence chunk ID and a BigQuery job ID (`full` track) or verified `[DOC_CHUNK_XXX]` citations (`lite` track).
- [ ] Questions with missing information end with `INSUFFICIENT_PARAMETERS` and no invented numbers.
- [ ] When no data matches, the first sentence of the answer states `MATCH_NOT_FOUND` (0 rows).

## View in the studio

[Open the Stage 4. Agent & MCP tab](https://agentic-ontology-starter-924723860007.asia-northeast3.run.app/?tab=stage4)

- Left: the catalog of 8 MCPs (filters `Stage MCP (5)` and `Runtime MCP (3)`). Each tool has a Step run button that opens a runner (`Execute Stage MCP`).
- Right: the agent console. Run a sample CQ button (`CQ-02` to `CQ-05`) or your own question with `Execute FDE` to see the sub-goals, tool calls and results in order.
- In a local studio you can also call `POST /api/query` (`{"query": "..."}`) and `POST /api/mcp/execute` (`{"tool_name": "...", "args": {...}}`).

## Notebook

[stage4_agent_and_mcp_execution_en.ipynb](../../notebooks/en/stage4_agent_and_mcp_execution_en.ipynb)

## Apply to your data

1. **Document-only projects (`lite` track)**: `execute_lite_doc_cycle()` automatically reads `doc_chunks.jsonl` and `03_wiki/` without SQL edits and enforces `[DOC_CHUNK_XXX]` citations.
2. **Custom domain tables (Scenario C)**: when your table schema differs from the 6-table telecom sample, set `"mcp_module"` and `"engine_module"` in `project.json` to inject domain-specific MCP handlers and agent prompts.
3. **Tool SQL and regex**: if modifying the default template, edit the SQL of the 3 runtime MCPs, `get_live_catalog()`, `extract_params_from_text()` (customer ID regex `CUST_[A-Z]+_\d{3}`), and prompts (`DECOMPOSE_SYS`, `SYNTH_SYS`).
4. **Model**: set it with `VERTEX_GEMINI_MODEL`.
