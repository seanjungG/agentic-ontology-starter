# Stage 3: BigQuery Property Graph Engineering & GQL Compilation Detailed Execution Guide
## Stage 3: Property Graph & GQL Compilation (English Edition)

- **Master Methodology**: [METHODOLOGY_EN.md](file:///Users/seanjung/Downloads/Uplus%20Ontology/agentic-ontology-starter/methodology/METHODOLOGY_EN.md)
- **Document Version**: `v1.0.0`
- **Objective**: Physically implement the hybrid ontology into Google Cloud BigQuery SQL:2023 Property Graph, achieve zero-copy node/edge projection, and engineer a multi-hop Graph Query Language (GQL) template engine.

---

## 1. Overall Execution Process

Stage 3 compiles declarative ontology models into production-grade BigQuery graph structures, enabling sub-second multi-hop graph traversals.

```mermaid
flowchart TD
    subgraph Step1 ["Step 3.1: Declarative Property Graph DDL"]
        DDL_Spec["CREATE OR REPLACE PROPERTY GRAPH<br/>[ENTERPRISE_SUBSIDY_GRAPH]"]
        Node_Def["7 Node Tables<br/>(Device, Plan, Subsidy, DocChunk, DomainRule)"]
        Edge_Def["5 Edge Tables<br/>(APPLIES_RULE, REQUIRES_PLAN, COVERS_DEVICE)"]
        DDL_Spec --> Node_Def & Edge_Def
    end

    subgraph Step2 ["Step 3.2: Zero-Copy Physical Projection"]
        BQ_DW["Existing BigQuery DW Master Ledgers"]
        BQ_DW --> ZeroCopy["Zero Data Movement / Zero Storage Duplication<br/>Pointer-based table virtualization"]
    end

    subgraph Step3 ["Step 3.3: GQL Template Engine Patterns"]
        Hop1["1-Hop: Device ➔ Subsidy Matching"]
        Hop2["2-Hop: Plan Downgrade ➔ Commitment Rule"]
        Hop3["Multi-Hop: Device ➔ Plan ➔ Subsidy ➔ Penalty ➔ Exemption"]
    end

    subgraph Step4 ["Step 3.4: SQL vs GQL Benchmarking"]
        RelSQL["Relational Multi-JOIN SQL"]
        GQLQuery["BigQuery Native GQL Query"]
        PerfCompare{"Evaluate Metrics<br/>- Query complexity (Lines of Code)<br/>- Execution latency (ms)<br/>- Slot consumption (Slot-ms)<br/>- Scanned bytes"}
        RelSQL & GQLQuery --> PerfCompare
    end

    Step1 --> Step2 --> Step3 --> Step4
```

### 1.1 GCP Native Foundations & Custom Extensions

| Dimension | Technologies & Specifications | Official Documentation / Spec Reference | Key Role & Engineering Rationale |
| :--- | :--- | :--- | :--- |
| **GCP Native Foundation** | • BigQuery SQL:2023 Property Graph<br>• `GRAPH_TABLE()` Inline Operator<br>• Native GQL (Graph Query Language) Engine | • [BigQuery Property Graph Docs](https://cloud.google.com/bigquery/docs/property-graphs)<br>• [BigQuery Remote MCP Specification](https://docs.cloud.google.com/bigquery/docs/use-bigquery-mcp) | Enables zero-copy graph traversal and multi-hop pattern matching directly inside the petabyte-scale BigQuery engine without requiring external graph databases (Neo4j, TigerGraph). |
| **Custom Extensions** | • 2-Layer Anti-Redundancy DDL Synthesizer (`pipeline/graph_builder.py`)<br>• Dedicated GQL Execution Runner (`src/agent/mcp_server.py`)<br>• Multi-Hop GQL Template Engine | Starter Pack Core Engine | **[Overcoming Critical Platform Limitation]** BigQuery Remote MCP's `execute_sql_readonly` explicitly does NOT support GQL queries. The starter pack introduces a dedicated GQL runner and an anti-redundancy synthesizer to promote DW tables to nodes with zero data duplication. |

---

## 2. Detailed Methodology & Technology Standards

### 2.1 Anti-Redundancy Architecture & BigQuery SQL:2023 Property Graph
- **Direct Promotion of DW Tables**: Projects relational DW master tables directly into graph nodes (`DeviceNode`, `PlanNode`, `SubsidyNode`) without moving or duplicating bytes.
- **Anti-Redundancy Pruning**: Duplicate entities mentioned in unstructured text are pruned away; only source evidence (`DocChunkNode`), source documents (`SourceDocNode`), and codified rules (`DomainRuleNode`) are projected.
- **Semantic Edge Projections**: Maps relationship tables as typed edges (`APPLIES_RULE`, `REQUIRES_PLAN`, `GROUNDED_IN`).

### 2.2 Multi-Hop GQL Traversal Patterns
- **1-Hop Matching**: Direct device-to-subsidy policy lookup.
- **2-Hop Policy Traversal**: Traversing from plan downgrade events to commitment rules and original source chunks.
- **Multi-Hop Synthesis**: Single-statement evaluation spanning device pricing, plan thresholds, penalty calculations, and statutory exemption clauses.

---

## 3. Stage 3 Quality Gate Checklist

- [ ] BigQuery Property Graph DDL compiled successfully with zero syntax errors.
- [ ] 7 node tables and 5 edge tables projected with zero physical data duplication.
- [ ] 1-hop, 2-hop, and multi-hop GQL queries successfully validated.
- [ ] SQL vs GQL performance and cost benchmarking report completed.
