# Stage 1: Asset Discovery, Scoping & Governance Ingestion Detailed Execution Guide
## Stage 1: Asset Discovery, Scoping & Governance Ingestion (English Edition)

- **Master Methodology**: [METHODOLOGY_EN.md](file:///Users/seanjung/Downloads/Uplus%20Ontology/agentic-ontology-starter/methodology/METHODOLOGY_EN.md)
- **Document Version**: `v1.0.0`
- **Objective**: Identify distributed structured DW ledgers and unstructured SOP manuals across the enterprise, proactively prune irrelevant noise, formulate 20 Golden Competency Questions (CQs), and ingest metadata into Google Cloud Dataplex Knowledge Catalog.

---

## 1. Overall Execution Process

Stage 1 defines the operational scope, quality benchmarks, and foundational data governance for building an enterprise agentic ontology.

```mermaid
flowchart TD
    subgraph Step1 ["Step 1.1: Source Data Asset Inventory"]
        DW_Raw["Structured DW Master Tables<br/>(Device Catalog, Plan Master, Subsidy Master)"]
        Doc_Raw["Unstructured Policy Manuals<br/>(Consultation SOPs, Terms & Conditions)"]
    end

    subgraph Step2 ["Step 1.2: Domain Scoping & Noise Pruning"]
        ScopeFilter{"Direct Relevance to Core<br/>Pricing, Contract & Penalty Decisions?"}
        NoisePrune["Prune Noise<br/>- Plan auxiliary specs (data packages)<br/>- Membership/points programs<br/>- Static vocabulary nodes"]
        CoreScope["Confirm Core Scope<br/>- Factory price & subsidy tables<br/>- Baseline plan tiers (5G/LTE thresholds)<br/>- 180-day commitment & penalty math"]
    end

    subgraph Step3 ["Step 1.3: Formulate 20 Golden Competency Questions (CQs)"]
        CQ_Draft["Domain Engineers & Advisors<br/>Curate Top 20 Real-World Inquiries"]
        CQ_GroundTruth["Map Verified Ground Truth,<br/>Formulas & Source References"]
    end

    subgraph Step4 ["Step 1.4: Governance Profiling & Dataplex Ingestion"]
        SchemaProfile["Profile BigQuery DW Schemas<br/>(Types, Keys, Partitions, Row Counts)"]
        CatalogTag["Dataplex Knowledge Catalog<br/>Sync Business Tags & PII Classifications"]
    end

    subgraph Step5 ["Step 1.5: Stage 1 Milestone Gate Review"]
        GateCheck{"Gate 1 Exit Criteria Met?<br/>- Charter signed<br/>- 20 CQs locked<br/>- Source access granted"}
        GatePass["Gate 1 Pass ➔ Enter Stage 2"]
    end

    DW_Raw & Doc_Raw --> ScopeFilter
    ScopeFilter -- "Auxiliary Noise" --> NoisePrune
    ScopeFilter -- "Core Decision Ledgers" --> CoreScope
    CoreScope --> CQ_Draft --> CQ_GroundTruth
    CoreScope --> SchemaProfile --> CatalogTag
    CQ_GroundTruth & CatalogTag --> GateCheck
    GateCheck -- "Approved" --> GatePass
```

---

## 2. Detailed Methodology & Technology Standards

### 2.1 Abstracted Source Asset Blueprint
To ensure broad cross-industry applicability, the starter pack abstracts customer-specific table names into standardized business architectural components.

| Abstracted Asset Name | Asset Type | Contents & Schema Blueprint | De-identified Concrete Example |
| :--- | :---: | :--- | :--- |
| **[Device Catalog DW Table]** | Structured DW | Manufacturer, model code, marketing name, storage tier, list price | `L0NUEM_TB_RCSP_MBL_TRM_M` |
| **[Tariff & Plan Master DW Table]** | Structured DW | Plan code, plan name, network tier (5G/LTE), monthly charge, threshold flag | `L0NUEM_TB_RCSP_FEE_PRD_M` |
| **[Subsidy Policy Master DW Table]** | Structured DW | Policy ID, applicable device, commitment tier, base subsidy, bonus discount | `L0NUEM_TB_RCSP_MBL_TRM_SUFU_PLCY_M` |
| **[Customer Consultation SOP Manual]** | Unstructured SOP | MHTML/PDF consultation guide, penalty math formulas, 180-day grace policy | `Consultation_Guide_2.0_Subsidy.mhtml` |
| **[Business Glossary Registry]** | Governance | Standard enterprise lexicon, synonym registry, boundary definitions | `Business_Glossary.json` |

### 2.2 Noise Pruning Charter & Scoping Rules
1. **Decision-Centric Knowledge Focus**:
   - 100% of modeling effort is concentrated on financial subsidies, contractual penalty formulas, and legal commitment grace periods.
2. **Auxiliary Feature Pruning**:
   - Secondary plan features (e.g., streaming subscriptions, data rollover options) that do not alter subsidy eligibility are pruned to prevent semantic drift.
3. **Glossary Excluded from Graph Topology**:
   - The business glossary serves as an Asset Registry and LLM prompt grounding anchor, but is strictly **excluded from GQL traversal nodes**.

---

## 3. Stage 1 Quality Gate Checklist

- [ ] Domain Scoping Charter signed by Data Architect and business stakeholders.
- [ ] 20 Golden CQs with verified ground truth formulas fully established.
- [ ] Source DW schemas and unstructured documents access verified.
- [ ] Dataplex catalog metadata and PII security profiles applied.
