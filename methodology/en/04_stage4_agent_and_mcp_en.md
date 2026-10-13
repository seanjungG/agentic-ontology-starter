# Stage 4. MCP and Agent Orchestration

> Studio [`Stage 4. Agent & MCP`](https://agentic-ontology-starter-924723860007.asia-northeast3.run.app/?tab=stage4) · MCP `mcp_stage4_agent_orchestration` + 3 runtime MCPs · Notebook [stage4_agent_and_mcp_execution_en.ipynb](../../notebooks/en/stage4_agent_and_mcp_execution_en.ipynb) · [Korean (KO)](../ko/04_stage4_agent_and_mcp_ko.md) · [Full methodology](./METHODOLOGY_EN.md)

## Purpose

The agent splits a question into parameters and sub-goals, calls the 8 MCP tools against **the runtime 1st-priority Single Source of Truth — BigQuery Property Graph (`engine="bigquery"` default or `engine="spanner"`)**, and answers only with values found in the tool results.
- **Runtime BQG 1st-Priority SSOT & Prohibition on Runtime Direct `anchor`/`parsed` Access**: In `standard`/`full` tracks and the Enterprise Studio, agents, workflows, and MCP tools **always query BigQuery Property Graph (BQG) as the 1st-priority SSOT**, and `PolicyResolver` resolves policy constants in the order **Layer 1: BQG (`GRAPH_TABLE`) → Layer 2: Ontology Wiki Hub (`ENT-*`, `CON-*`) & Business Rules (`BR-*` `parameters[]`)**. Raw documents (`raw`), parsed markdown (`parsed`), and paragraph hash anchors (`anchor_<12hex>`, `sec-xx-pyy`) are strictly Build-Time (Stage 1~2) artifacts and MUST NEVER be directly queried or linked at runtime.
- Each answer carries the semantic/rule ID (`ENT-*`, `CON-*`, `BR-*` / `RULE_*`) and the backend execution identifier (BigQuery job ID or Spanner database ID).

## Inputs

- The user question (natural language) and graph engine selection (`"bigquery"` default \| `"spanner"`)
- The 10 tables and `STARTER_ONTOLOGY_GRAPH` in BigQuery (`starter_ontology_dw`) or Cloud Spanner (`starter-spanner/starter_ontology_db`) (Stages 1 to 3, **Runtime 1st-Priority SSOT**)
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

### 2) `lite` Track (1-Pass Document-Chunk Context Runtime: `AiFdeAgentEngine._lite_cycle()`)

For document-only projects (`track: "lite"`) without structured customer tables, the engine bypasses BigQuery SQL MCPs and answers from every chunk row of BigQuery `tb_doc_chunks` (`get_doc_chunks`) placed in context (limit `lite.max_context_chars`, default `300,000` characters; above it the answer stops with `CONTEXT_LIMIT`).

- **Mandatory Citation**: Every factual claim in the response must cite a valid chunk ID in `[DOC_CHUNK_XXX]` format.
- **Citation Verification Statuses**:
  - `GROUNDED`: Every cited `[DOC_CHUNK_XXX]` exists among the `tb_doc_chunks` chunk IDs read in this call.
  - `NO_CITATION`: The response failed to include any `[DOC_CHUNK_XXX]` citation.
  - `INVALID_CITATION`: The response cited a chunk ID that is not among the `tb_doc_chunks` chunk IDs read in this call.
  - `CONTEXT_LIMIT`: Total document chunk characters exceeded the `300,000`-character context limit.

### Tool granularity and composite questions

- Each tool has one lookup responsibility (for example subsidy lookup, penalty calculation, rule and chunk check) and returns its status and BigQuery job ID with the result. Empty slots are never filled with hard-coded or default values.
- Tools that return the same data under different names are merged into one; the others remain as aliases.
- A composite question (several conditions or entities) is split into several tool calls during planning, and the answer is written from tool results only. If a required value is not in the data, the agent says so instead of estimating it.
- Check tool coverage with questions outside the evaluation set (other device, plan and day combinations from the catalog). Record possible overfitting when a score was tuned on the same questions.

## Recommended method: Wiki Agent (Stage 2 Gate) vs BQG Agent (Runtime 1st Priority)

The two agents differ in their lifecycle role and where they get their evidence. **Wiki Agent is the Stage 2 quality gate** before building a physical graph, whereas **BQG Agent (along with Workflow Agent and AI FDE) is the 1st-priority runtime serving agent** from Stage 3 onward.

| Step | Wiki Agent (Stage 2 Exit Gate) | BQG Agent (Runtime 1st-Priority Agent) |
| :---: | :--- | :--- |
| 1 | Read the GCS wiki index | Slot extraction (Flash) |
| 2 | Flash reads the index and selects the entity and concept documents to open | **1st-Priority GQL query over BigQuery Property Graph (BQG)** |
| 3 | Read the selected documents and their 1-hop related documents from GCS | Deterministic calculation in code from BQG/DW values & `PolicyResolver` (Layer 1 BQG) |
| 4 | Flash writes the answer (Wiki document ID `ENT-*`/`CON-*` citation · no direct `anchor` links) | Flash writes the answer (Semantic/Graph IDs `ENT-*`/`CON-*`/`BR-*` + `bq_job_ids`) |
| BigQuery and graph | Not used (Stage 2 Gate only) | **1st-Priority Primary SSOT** |

- Both agents record time per step and token usage (input, output and thinking from Vertex `usageMetadata`) in the response.
- Passing whole documents uses more input tokens than chunk search (reference case: about 3 times). Record the number of documents read and the character limit per document.

The current starter implementation differs. There is one agent, `AiFdeAgentEngine`; there are no separate Wiki and BQG agents.

- `lite` track: does not read a GCS wiki index or per-document files; it puts all `tb_doc_chunks` rows into the context of one Gemini call (`_lite_cycle`).
- `standard`/`full` tracks: the MCP tools run real BigQuery or Spanner queries.
- Tokens are recorded as call totals of input (`prompt_tokens`) and output (`candidates_tokens`) only; thinking tokens are not recorded. Time is recorded per tool (`tool_elapsed_ms`, `bq_elapsed_ms`) and in total.

## Recommended method: AI FDE tools and resource display

- The agent toolbox holds only lookup tools that answer business questions. Methodology stage tools that only summarize status and query no data are not offered as agent tools, and there is no "run all 5 stages" button that only checks status.
- Every planner call receives the user question (goal), and sub-goals are shown in a structured form: `id`, `intent`, `tool`, `reason`, `status`.
- Every tool call shows its resource usage: BigQuery job IDs, rows returned, bytes processed, cache hit, query time, tables used, executed SQL. The response shows the token usage of the planner and answer calls.
- Preset questions are grouped into business / engineering / multi-domain scenarios and use values that exist in the data (device, plan, transaction ID, period). Run every preset and record the result status (reference case: 14 of 14 `SUCCESS`).

Current starter implementation:

- The 5 Stage MCPs run real validation queries (table inventory and row counts, duplicate keys, GQL path count, etc.) and stay as they are. All 8 tools are also in the agent tool list (`get_tool_catalog()`).
- Sub-goal fields are `id`, `goal`, `tool`, `category`; there is no `intent` or `status`. Decomposition is one Gemini call.
- Tool results contain `bq_jobs` (job ID, engine, status, elapsed ms, rows returned, SQL), `bq_job_ids`, `bq_elapsed_ms`, `executed_sql`, `tool_elapsed_ms`. Bytes processed, cache hit and the list of tables used are not recorded.
- Presets are the sample CQ buttons (`CQ-02` to `CQ-05`) in the Stage 4 console, without scenario groups.

## Resource-Connected Architecture (Ready-to-Use Resource Connector + 3 Domain Business Tools)

Starting in Starter Pack v2.2, internal ontology builder MCP pipelines are abstracted into the platform layer, while the Starter exposes only the **Ready-to-Use GCP Resource Connector (`src/resource_connector.py`)** and **3 Customizable Domain Business Tools (`src/agent/mcp_server.py`)**:

| Layer | Module / File | Role & Responsibility | Exposed Tools / Methods |
| :--- | :--- | :--- | :--- |
| **Ready-to-Use Resource Connector** | `src/resource_connector.py` (`OntologyResourceConnector`) | **Direct connection & readiness checks for GCP resources**: Verifies BigQuery (`starter_ontology_dw` 10 tables), `STARTER_ONTOLOGY_GRAPH`, GCS 3-Layer OKF Wiki & `W1~W3` workflows, and Cloud Spanner Graph | `verify_ready_resources()`, `stage1_resource_check` ~ `stage5_resource_check` |
| **Domain Business Tools (3 Tools)** | `src/agent/mcp_server.py` (`DomainMcpServer`) | **Project/Domain-Specific Deterministic Execution Tools**: Executes domain ledgers, rules, and SQL formulas bound 1:1 to workflows (`W1~W3`) and business rules (`RULE_*`) | `mcp_lookup_customer_profile`, `mcp_calculate_penalty_rule`, `mcp_query_graph_and_wiki` |

## Deliverables

| ID | Deliverable | In the starter |
| :--- | :--- | :--- |
| `D4.1` | Domain Business Tools Server & Resource Connector | `src/agent/mcp_server.py` (`DomainMcpServer`) + `src/resource_connector.py` (`OntologyResourceConnector`) |
| `D4.2` | AI FDE semantic routing and sub-goal decomposition engine (`Gate G2-W`) | `src/agent/reasoning_engine.py` (`AgenticReasoningEngine`) |
| `D4.3` | Cross-domain context passing and hand-off protocol | `execute_cycle()` passes validated parameters across the 3 Domain Business Tools |
| `D4.4` | Agent boundary test suite | The 10 agent-level boundary questions are covered in [Stage 5](./05_stage5_lineage_and_eval_en.md) |
| `D4.5` | Business Rules (`RULE_*`), Workflows (`W1~W3`) & Domain Tool Bindings | `data/llm_wiki/business_rules.json` and `data/llm_wiki/business_workflows.json` |

## Gate (Gate G2-W & Gate 4)

- [ ] `get_tool_catalog()` cleanly exposes the 3 customizable Domain Business Tools (`mcp_lookup_customer_profile`, `mcp_calculate_penalty_rule`, `mcp_query_graph_and_wiki`).
- [ ] Golden CQ questions end with answer status `GROUNDED`, and the answer contains the evidence chunk ID (`DOC_CHUNK_*`) and a BigQuery job ID.
- [ ] Questions with missing information end with `INSUFFICIENT_PARAMETERS` and no invented numbers.
- [ ] When no data matches, the first sentence of the answer states `MATCH_NOT_FOUND` (0 rows).

## View in the studio

[Open the Stage 4. Agent & Tools tab](https://agentic-ontology-starter-924723860007.asia-northeast3.run.app/?tab=stage4)

- Left: the catalog of 3 Domain Business Tools and Resource Check runner.
- Right: the AI FDE console (`Gate G2-W Audited`). Run a sample CQ button (`CQ-02` to `CQ-05`) or your own question with `Execute FDE` to see the sub-goals, tool calls, and results in order.
- In a local studio you can also call `POST /api/query` (`{"query": "..."}`) and `POST /api/mcp/execute` (`{"tool_name": "...", "args": {...}}`).

## Notebook

[stage4_agent_and_mcp_execution_en.ipynb](../../notebooks/en/stage4_agent_and_mcp_execution_en.ipynb)

## Apply to your data

1. **Document-only projects (`lite` track)**: `_lite_cycle()` reads every `tb_doc_chunks` chunk without SQL edits and enforces `[DOC_CHUNK_XXX]` citations.
2. **Remote Platform Core MCP Build + Custom Business MCP Binding**: Declare your project's `domain_mcp_tools` via `build_domain_spec_from_project()` in `src/agent/platform_core_mcp.py` and invoke `PlatformCoreMcpClient.call_tool("mcp_builder_run_full_pipeline", ...)` to compile Stage 1~6 ontology and Studio bundles.
3. **Tool SQL and regex**: if modifying the default template, edit the SQL of the 3 runtime MCPs, `get_live_catalog()`, `extract_params_from_text()` (customer ID regex `CUST_[A-Z]+_\d{3}`), and prompts (`DECOMPOSE_SYS`, `SYNTH_SYS`).
4. **Model**: separate the runtime Agent serving model (`VERTEX_GEMINI_MODEL`, default `gemini-3.8-flash`) from the Platform Core MCP compiler model (`Gemini 4 Argon` / `gemini-4-argon`, which explicitly raises `QUOTA_EXHAUSTED_ERROR` on quota exhaustion).
