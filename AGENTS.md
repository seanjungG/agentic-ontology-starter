# Agentic Ontology Starter (v2.2 — Resource-Connected Edition) Agent Guidelines

## 1. Architecture & Code Exposure Boundary
- **Concept**: Exclude/abstract heavy internal MCP builder pipelines from the Starter catalog and connect directly to **Ready-to-Use GCP Ontology Resources** (`seanjung-poc.starter_ontology_dw`, `STARTER_ONTOLOGY_GRAPH`, `gs://seanjung-poc-starter-ontology/ontology/`, `starter-spanner`).
- **Reference Standard Studios (12-Tab)**:
  - LG U+ Studio: `https://agentic-ontology-studio-lguplus-mcp-924723860007.asia-northeast3.run.app/`
  - LG H&H Studio: `https://agentic-ontology-studio-hnh-mcp-924723860007.asia-northeast3.run.app/`
- **Starter Portal (6-Tab)**:
  - Starter Studio: `https://agentic-ontology-starter-924723860007.asia-northeast3.run.app/`
- **Exposed Core Files (4 Files)**:
  1. `src/resource_connector.py` (`OntologyResourceConnector`, `STAGE_UNIFIED_MAP`, `CODE_EXPOSURE_BOUNDARY`)
  2. `src/gcp_client.py` (`EnterpriseOntologyBenchmarker` — BigQuery SQL/GQL, Spanner GQL, GCS, Vertex AI `gemini-3.8-flash`)
  3. `src/agent/mcp_server.py` (`DomainMcpServer` — exposes ONLY the **3 Domain Business Tools**: `mcp_lookup_customer_profile`, `mcp_calculate_penalty_rule`, `mcp_query_graph_and_wiki`)
  4. `src/agent/reasoning_engine.py` (`AgenticReasoningEngine` — sub-goal decomposition, tool chaining, `Gate G2-W` runtime audit)

## 2. Key Commands
- Verify all Stage 1~5 Ready-to-Use GCP resources & Golden CQs: `python3 run_pipeline.py --track full`
- Launch 6-Tab Starter Portal locally: `python3 -m src.web.studio_server 8080`
- Regenerate & validate all 12 KO/EN notebooks: `python3 generate_notebooks.py && python3 validate_and_pack_notebooks.py`
- Run test suite: `pytest tests/test_data_fidelity.py`
