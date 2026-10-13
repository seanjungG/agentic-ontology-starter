# Rapid Customer Prototyping Playbook — Resource-Connected Starter (v2.2)

This playbook explains how to prototype a new enterprise domain on **Agentic Ontology Starter (v2.2)** by connecting directly to **Ready-to-Use Google Cloud Ontology Resources** and customizing the **4 Exposed Core Files** (`src/resource_connector.py`, `src/gcp_client.py`, `src/agent/mcp_server.py`, `src/agent/reasoning_engine.py`).

---

## 1. Architecture Philosophy: Abstract the Builder, Customize the Business Tools

Instead of exposing heavy internal MCP compiler pipelines, the Starter Pack connects directly to pre-built, verifiable GCP resources aligned with our two **12-Tab Enterprise Reference Studios**:
- **LG U+ Telecom Reference Studio (12-Tab)**: `https://agentic-ontology-studio-lguplus-mcp-924723860007.asia-northeast3.run.app/`
- **LG H&H Compliance Reference Studio (12-Tab)**: `https://agentic-ontology-studio-hnh-mcp-924723860007.asia-northeast3.run.app/`
- **Starter Portal (6-Tab)**: `https://agentic-ontology-starter-924723860007.asia-northeast3.run.app/`

| Layer | Resource / Module | Role in Prototyping |
| :--- | :--- | :--- |
| **Ready-to-Use GCP Resources** | `seanjung-poc.starter_ontology_dw` + `STARTER_ONTOLOGY_GRAPH` + `gs://seanjung-poc-starter-ontology/ontology/` + `starter-spanner` | Pre-provisioned DW ledgers, 3-Layer OKF Wiki, business rules (`RULE_*`), workflows (`W1~W3`), and Property Graph |
| **1. Resource Connector** | [`src/resource_connector.py`](src/resource_connector.py) | Verifies Stage 1~5 resource readiness (`stage1_resource_check` .. `stage5_resource_check`) |
| **2. GCP Client** | [`src/gcp_client.py`](src/gcp_client.py) | Executes live BigQuery SQL, SQL:2023 `GRAPH_TABLE`, Spanner GQL, GCS reads, and Vertex AI `gemini-3.8-flash` |
| **3. Domain Business Tools (3)** | [`src/agent/mcp_server.py`](src/agent/mcp_server.py) | **Primary customization target**: `mcp_lookup_customer_profile`, `mcp_calculate_penalty_rule`, `mcp_query_graph_and_wiki` |
| **4. AI FDE Reasoning Engine** | [`src/agent/reasoning_engine.py`](src/agent/reasoning_engine.py) | Sub-goal decomposition, tool chaining, and `Gate G2-W` runtime audit |

---

## 2. 15-Minute Customer Prototyping Flow (`P1/P2/P3 × W1/W2/W3 × Gate G2-W`)

### Step 1: Verify Ready-to-Use GCP Resources (2 mins)
```bash
python3 run_pipeline.py --track full
```
This runs `OntologyResourceConnector.verify_ready_resources()` across Stage 1~5 and verifies all 5 Golden CQs (`5/5 PASS`).

### Step 2: Customize Domain Business Rules & Workflows (`data/llm_wiki/`) (5 mins)
- Edit `data/llm_wiki/business_rules.json` (`RULE_*` deterministic SQL formulas and parameters)
- Edit `data/llm_wiki/business_workflows.json` (`W1/W2/W3` decision trees and `Gate G2-W` preconditions)
- Edit `data/llm_wiki/workflow_cqs.json` (`WF-CQ-01..05` verification questions)

### Step 3: Customize the 3 Domain Business Tools (`src/agent/mcp_server.py`) (5 mins)
Adapt the 3 exposed tools in `DomainMcpServer.get_tool_catalog()` to your customer's tables and formulas:
1. `mcp_lookup_customer_profile`: Ledger/entity profile lookup
2. `mcp_calculate_penalty_rule`: Deterministic SQL rule calculation (zero LLM arithmetic)
3. `mcp_query_graph_and_wiki`: Multi-hop `GRAPH_TABLE` traversal + `DOC_CHUNK_*` SHA-256 citation

### Step 4: Launch the 6-Tab Starter Studio & Run Interactive Notebooks (3 mins)
```bash
python3 -m src.web.studio_server 8080
```
Or walk through the 12 interactive KO/EN notebooks in `notebooks/ko/` and `notebooks/en/`.
