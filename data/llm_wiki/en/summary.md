# Enterprise Knowledge Wiki: Executive Summary (Layer 1)
- **Domain**: Telecom Terminal Subsidy, Tariff Plans & Customer Commitment Management
- **Target Framework**: OKF v0.2 & Dual Property Graph (`seanjung-poc.starter_ontology_dw.STARTER_ONTOLOGY_GRAPH`)
- **Total Parsed Chunks**: 5 (Across 2 Policy Guides)
- **BigQuery Tables Loaded**: 10 tables in `seanjung-poc.starter_ontology_dw` (schema: `terraform/bigquery.tf`)

## Operational Philosophy
Unstructured policy guides and structured BigQuery tables share one ontology. The agent answers with live BigQuery SQL/GQL results, SHA-256 paragraph anchors and Vertex AI Gemini, and cites the rule and chunk used.
