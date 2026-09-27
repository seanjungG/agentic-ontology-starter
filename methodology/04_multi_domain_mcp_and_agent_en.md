# Stage 4: Multi-Domain MCP Suite Packaging & Agentic Orchestration Detailed Execution Guide
## Stage 4: Multi-Domain MCP Suite & Agentic Orchestration (English Edition)

- **Master Methodology**: [METHODOLOGY_EN.md](./METHODOLOGY_EN.md)
- **Document Version**: `v1.0.0`
- **Objective**: Package domain ontology and graph engines into standardized Model Context Protocol (MCP) tools, and orchestrate an autonomous AI Forward Deployed Engineer (FDE) agent capable of dynamic multi-goal decomposition and cross-domain sequential chaining.

---

## 1. Overall Execution Process

Stage 4 connects intelligent LLM reasoning with certified enterprise tools, enabling transparent multi-step decision pipelines.

```mermaid
sequenceDiagram
    autonumber
    actor User as Enterprise User / FDE
    participant Agent as AI FDE Agent Engine
    participant BizTool as [Business Domain MCP Tools]
    participant EngTool as [Engineering Infra MCP Tools]
    participant DW_Graph as [BigQuery Property Graph]

    User->>Agent: Complex Query ("Compute subsidy and verify underlying DW row counts")
    
    rect rgb(245, 245, 255)
        Note over Agent: Step 4.1: Dynamic Sub-Goal Decomposition
        Agent->>Agent: G-BIZ-01: Price & subsidy calculation<br/>G-ENG-01: DW table metadata & physical count check
    end

    rect rgb(240, 248, 255)
        Note over Agent,BizTool: Step 4.2: Business Tool Execution (Step 2-1)
        Agent->>BizTool: mcp_get_device_subsidy_by_plan(device, plan)
        BizTool->>DW_Graph: Query subsidy policy table
        DW_Graph-->>BizTool: Return subsidy (500,000 KRW), commitment days, target table
        BizTool-->>Agent: Emit Intermediate Observation 1<br/>(Data Hand-off: target table name)
    end

    rect rgb(255, 245, 245)
        Note over Agent,EngTool: Step 4.3: Engineering Cross-Domain Chaining (Step 2-2)
        Agent->>EngTool: mcp_inspect_dw_table_schema(handed_off_table)
        EngTool->>DW_Graph: Scan INFORMATION_SCHEMA & table partitions
        DW_Graph-->>EngTool: Return row count (1,240 rows) & partition state
        EngTool-->>Agent: Emit Intermediate Observation 2
    end

    rect rgb(245, 255, 245)
        Note over Agent: Step 4.4: Cross-Domain Integration & Synthesis
        Agent->>Agent: Cross-verify mathematical math with physical table state
        Agent-->>User: Step 4.5: Output Final AI FDE Report (Math + Policy + Metadata)
    end
```

### 1.1 GCP Native Foundations & Custom Extensions

| Dimension | Technologies & Specifications | Official Open-Source / Endpoint Reference | Key Role & Engineering Rationale |
| :--- | :--- | :--- | :--- |
| **GCP Native Foundation** | • Google Agent Development Kit (ADK Python 2.0)<br>• Google Cloud Data Agent Kit (Conversational Analytics API)<br>• Dataplex & BigQuery Remote MCP<br>• Vertex AI Gemini 3.8 Flash | • [ADK Python GitHub](https://github.com/google/adk-python)<br>• [Conversational Analytics API](https://docs.cloud.google.com/gemini/docs/conversational-analytics-api/overview)<br>• [GCP Remote MCP Specification](https://docs.cloud.google.com/dataplex/docs/use-remote-mcp) | Provides enterprise agent execution runtime (Workflow Runtime, Task API), IAM-governed Remote MCP connections, and foundational multimodal inference. |
| **Custom Extensions** | • Tier 3 Domain Ontology MCP Server (11 tools)<br>• AI FDE Dynamic Sub-Goal Decomposition Engine (`fdeAgentEngine.py`)<br>• Cross-Domain Sequential Chaining (`Data Hand-off`, `Intermediate Observation`) | Starter Pack Agent Engine (`src/agent/`) | Shields LLM agents from cognitive table schemas and orchestrates deterministic reasoning loops across business rules and physical DW table states. |

---

## 2. Detailed Methodology & Technology Standards

### 2.1 MCP as the Domain Ontology Abstraction Layer
Rather than burdening LLMs with writing fragile raw SQL joins or raw GQL graph traversals, the Model Context Protocol (MCP) functions as the **Domain Ontology Abstraction Layer**:
- **Agent Shielding**: Encapsulates table schemas, partitioning keys, and multi-hop graph traversals behind intuitive business domain tool signatures.
- **Deterministic Reliability**: Blends deterministic relational ledger lookups, GQL traversals, and Python math calculations within tool boundaries, returning 0% hallucination facts.
- **Categorized Suite (11 Tools)**:
  - **5 Business Tools**: Device list price, subsidy policies, penalty formulas, 24-month contract comparisons, policy chunk grounding.
  - **6 Engineering/Infra Tools**: Property graph GQL traversal, DW table schema/volume inspection, Dataplex catalog search, 4-tier lineage tracing, graph DDL export, CQ benchmark runner.

### 2.2 Dynamic Sub-Goal Decomposition & Sequential Chaining
- Eliminates fragile hardcoded `if-elif` logic by parsing complex user intents into an array of sub-goals.
- Automatically passes outputs from upstream business queries into downstream infrastructure tools.
- Surfaces intermediate observations directly on the chat timeline, providing complete transparency and auditability.

### 2.3 3-Tier MCP (16 Tools) 24-Scenario Boundary Verification & Iterative Refinement (`scripts/evaluate_mcp_quality_suite.py`)
- **Verification Scope**: 5 Business MCP tools (10 scenarios), 6 BQ+KC Engineering MCP tools (7 scenarios), 5 Methodology Stage MCP tools (5 scenarios), and AI FDE Router (2 scenarios) = **24 Boundary & Contract Scenarios**.
- **2-Round Iterative Refinement (Round 1 ➔ Round 2)**:
  - **Round 1 (Baseline)**: Exposes silent default fallbacks, edge-case arithmetic traps (exact 180-day boundary, 45,000 KRW floor, senior exemptions), and unconditional `SUCCESS` returns on missing assets (**5 / 24 Passed, 20.8%**).
  - **Round 2 (Refined)**: Enforces explicit contract validation (`INVALID_INPUT_BOUNDARY`, `ENTITY_NOT_FOUND`, `UNSUPPORTED_MODALITY_ABSTENTION`, `SECURITY_GUARDRAIL_BLOCKED`, `STAGE_GATE_BLOCKED`) across all handlers (**24 / 24 Passed, 100.0%, +79.2%p**).

---

## 3. Stage 4 Quality Gate Checklist

- [x] All 16 3-Tier MCP tool JSON schemas (5 Business, 6 BQ+KC, 5 Stage) verified.
- [x] Dynamic multi-goal decomposition and 5-Stage sequential chaining verified on multi-part inquiries.
- [x] Inter-tool context hand-off validated across domain boundaries.
- [x] 24-Scenario boundary, contract, exception & injection verification suite (`evaluate_mcp_quality_suite.py`) achieved 24/24 (100.0%).

