# -*- coding: utf-8 -*-
# Copyright (c) 2026 Sean Jung (seanjung@google.com). All rights reserved.
# Licensed under CC BY-NC-ND 4.0 (Methodology & Slide Deck) & PolyForm Noncommercial 1.0.0 (Code).

"""
18-Slide English Training Curriculum Specification for Agentic Ontology Starter Methodology.
100% English (0 Hangul characters) — covers 8-Phase Engineering Flow, 5-Stage Lifecycle (Stage 1..5),
3-Track Adoption Model, 5-File Swap Playbook, AI Coding Agent Bootstrap, and 8 Industry Archetypes.
"""

SLIDES_EN = [
    {
        "slide_no": 1,
        "badge": "MODULE 00 · EXECUTIVE OVERVIEW",
        "accent": "#1A73E8",
        "title": "5-Stage Agentic Ontology Engineering Methodology",
        "subtitle": "Unifying Enterprise Structured DW (BigQuery) & Unstructured Policy Docs (OKF v0.2) into ISO GQL Property Graphs, 8 Domain MCP Tools, and 2-Pass Gemini Agents",
        "banner_img": "stage0_overview_flow_en.png",
        "cards": [
            {
                "tag": "PILLAR 1 · UNSTRUCTURED",
                "title": "Immutable Hash Anchors & 3-Layer Wiki",
                "accent": "#1A73E8",
                "bullets": [
                    "Paragraph-level SHA-256 hashes (anchor_<12hex>) stored in tb_doc_chunks",
                    "OKF v0.2 JSON-LD + L1 (Summary), L2 (Entities), L3 (Concepts & Rules) Wiki",
                    "Deterministic citation lineage from every agent answer back to exact clauses"
                ]
            },
            {
                "tag": "PILLAR 2 · PROPERTY GRAPH",
                "title": "Zero-ETL Dual Property Graph",
                "accent": "#0F9D58",
                "bullets": [
                    "Declares CREATE OR REPLACE PROPERTY GRAPH directly over DW tables without ETL",
                    "Projects 6 Vertex Tables × 4 Edge Tables into STARTER_ONTOLOGY_GRAPH",
                    "Supports BigQuery (OLAP multi-hop GQL) + Cloud Spanner (OLTP interlock DDL)"
                ]
            },
            {
                "tag": "PILLAR 3 · AGENT & GATE",
                "title": "8 Domain MCPs & 2-Pass Agent",
                "accent": "#4F46E5",
                "bullets": [
                    "Executes prorated clawbacks & 24-month TCO via SQL/Python MCP formulas, not LLM math",
                    "Vertex AI Gemini (gemini-3.8-flash) 2-Pass loop with 4 explicit guardrail states",
                    "Validated via 5 Golden CQs + 50 Boundary runs (10×5) before Cloud Run release"
                ]
            }
        ],
        "table": {
            "headers": ["Core Architectural Axis", "Technology Stack (Google Cloud Native + Custom)", "Primary Code / Artifact Path", "Verification Gate"],
            "rows": [
                ["1. Data & Wiki Layer", "BigQuery DW (10 Tables) + GCS 3-Layer OKF Wiki", "pipeline/ingest.py · data/llm_wiki/en/", "10 tables loaded · SHA-256 anchors"],
                ["2. Semantic & Graph Layer", "BigQuery SQL:2023 Property Graph (ISO GQL) + Spanner DDL", "pipeline/graph_builder.py · create_property_graph.sql", "0 duplicate keys · Multi-hop GQL paths"],
                ["3. Tool & Reasoning Layer", "DomainMcpServer (8 Tools) + AiFdeAgentEngine (2-Pass)", "src/agent/mcp_server.py · reasoning_engine.py", "GROUNDED / INSUFFICIENT / MATCH_NOT_FOUND"],
                ["4. Lineage & Release Layer", "End-to-End Lineage + Dual Validator + Terraform Cloud Run", "pipeline/validator.py · terraform/*.tf", "Golden CQ 5/5 · Boundary 50 live runs"]
            ]
        },
        "takeaway": "Core Rule: Bind unstructured policy clauses (SHA-256 anchors) and structured DW tables (PK/FK) into a unified graph and deterministic MCP tools to eliminate free-form guessing.",
        "speaker_notes": (
            "[Instructor Guide — Slide 01: Executive Overview & Core Philosophy]\n"
            "• Welcome & Course Goal: This training curriculum walks through the 5-Stage Agentic Ontology Engineering Methodology in 'agentic-ontology-starter', showing how to unify structured BigQuery DW tables and unstructured policy documents into a Property Graph, 8 MCP tools, and a 2-Pass Gemini agent.\n"
            "• Highlight the 4 Core Principles:\n"
            "  1) Immutable Lexical Anchors: Every policy paragraph is hashed with a 12-character SHA-256 prefix (anchor_<12hex>) in tb_doc_chunks.\n"
            "  2) Zero-ETL Property Graph: Structured tables and unstructured rule bridges are projected directly via CREATE OR REPLACE PROPERTY GRAPH.\n"
            "  3) Deterministic Arithmetic: Prorated penalties and 24-month TCO comparisons are computed inside SQL/Python MCP tools rather than LLM mental math.\n"
            "  4) Explicit Guardrail States: Responses strictly separate GROUNDED, MATCH_NOT_FOUND, INSUFFICIENT_PARAMETERS, and BQ_QUERY_ERROR.\n"
            "• Licensing: Methodology and slides are licensed under CC BY-NC-ND 4.0; code is under PolyForm Noncommercial 1.0.0 (contact seanjung@google.com for commercial use)."
        )
    },
    {
        "slide_no": 2,
        "badge": "MODULE 00 · PROBLEM & MOTIVATION",
        "accent": "#D97706",
        "title": "Why Naive RAG & Standalone Text-to-SQL Fail in Enterprise Production",
        "subtitle": "Three structural failure modes when unstructured policy documents and structured ledger tables remain disconnected",
        "banner_img": None,
        "cards": [
            {
                "tag": "FAILURE MODE 1",
                "title": "Structured vs. Unstructured Silos",
                "accent": "#DC2626",
                "bullets": [
                    "Customer contracts & plan fees live in BigQuery, while clawback & exemption clauses live in Markdown/PDFs",
                    "Naive Vector RAG cannot look up a customer's actual contract, device subsidy, or elapsed days (90d)",
                    "Standalone Text-to-SQL ignores unstructured exceptions like 180-day prorated retention or senior exemptions"
                ]
            },
            {
                "tag": "FAILURE MODE 2",
                "title": "LLM Mental-Math Errors",
                "accent": "#D97706",
                "bullets": [
                    "Relying on free-form token generation for formulas like (500,000 - 300,000) × (180 - 90) / 180",
                    "Skipping priority decision branches such as SENIOR_EXEMPT welfare waivers (0 KRW)",
                    "Inconsistent numbers or conflicting rule citations across repeated runs of the same prompt"
                ]
            },
            {
                "tag": "FAILURE MODE 3",
                "title": "Zero Auditability & Missing Guardrails",
                "accent": "#4F46E5",
                "bullets": [
                    "Fixed-size character chunking shifts chunk IDs whenever a policy document is edited",
                    "Hallucinating assumed numbers when required parameters (e.g., elapsed_days) are omitted",
                    "No pre-deployment release gate to verify both ground-truth accuracy and boundary refusal"
                ]
            }
        ],
        "table": {
            "headers": ["Comparison Dimension", "Naive Vector RAG", "Standalone Text-to-SQL", "5-Stage Agentic Ontology (This Methodology)"],
            "rows": [
                ["Unstructured Policy + DW Join", "Not supported (text snippets only)", "Not supported (tables only, blind to policy docs)", "Unified via edge_rule_applies_to_plan & Property Graph"],
                ["Arithmetic & TCO Calculation", "Free-form LLM token generation", "Ad-hoc LLM-generated SQL (prone to JOIN omissions)", "Deterministic SQL/Python formulas inside Domain MCP tools"],
                ["Source Citation & Audit Trail", "Approximate top-k cosine similarity", "No policy clause citation", "Exact DOC_CHUNK_001..005 + SHA-256 hash + BigQuery Job ID"],
                ["Missing Params / Unknown Entities", "Guesses arbitrary default assumptions", "Misinterprets empty 0-row result sets", "Explicit INSUFFICIENT_PARAMETERS / MATCH_NOT_FOUND"]
            ]
        },
        "takeaway": "Architectural Fix: Restrict the LLM to Catalog-Constrained Slot Extraction (Pass 1) and Grounded Synthesis (Pass 2), while Property Graph GQL and MCP SQL handle traversal and math.",
        "speaker_notes": (
            "[Instructor Guide — Slide 02: Why Naive RAG & Text-to-SQL Fail]\n"
            "• Walk through a concrete telecom scenario: A customer (CUST_DEMO_001) asks how much penalty they owe if they downgrade to 5G Standard after 90 days.\n"
            "• Answering accurately requires joining 4 structured tables (contract, device, plan, subsidy) AND applying 3 policy clauses (180-day prorated formula, 85,000 KRW baseline threshold, and senior welfare exemption priority).\n"
            "• Show how the 5-Stage Agentic Ontology bridges both worlds deterministically."
        )
    },
    {
        "slide_no": 3,
        "badge": "MODULE 00 · 8-PHASE & 5-STAGE MAP",
        "accent": "#1A73E8",
        "title": "8-Phase Engineering Flow & 5-Stage Lifecycle Master Map",
        "subtitle": "End-to-end progression: 1. Prepare → 2. Analyze → 3. Parse → 4. Integrate → 5. Build Graph → 6. Build Agent → 7. Answer (GQL) → 8. Verify & Gate",
        "banner_img": "stage0_overview_flow_en.png",
        "cards": [
            {
                "tag": "PHASES 1~4 (STAGES 1 & 2)",
                "title": "Asset Scoping, 3-Layer Wiki & Bridges",
                "accent": "#1A73E8",
                "bullets": [
                    "Phases 1–2 (Stage 1): Define CQs, ingest 4 master CSVs & 2 guides, verify PII de-identification",
                    "Phases 3–4 (Stage 2): SHA-256 chunking, 3-Layer Wiki, 12 rule-to-plan semantic bridges",
                    "Deliverables: D1.1–D1.4 and D2.1–D2.6 (10 BigQuery tables populated)"
                ]
            },
            {
                "tag": "PHASE 5 (STAGE 3)",
                "title": "Property Graph & ISO GQL",
                "accent": "#0F9D58",
                "bullets": [
                    "Phase 5 (Stage 3): Declare 6 vertex tables & 4 edge tables as STARTER_ONTOLOGY_GRAPH",
                    "Validate multi-hop BigQuery GQL GRAPH_TABLE paths and generate Spanner Graph DDL",
                    "Deliverables: D3.1–D3.4 (create_property_graph.sql, graph_topology.json)"
                ]
            },
            {
                "tag": "PHASES 6~8 (STAGES 4 & 5)",
                "title": "8 MCP Tools, 2-Pass Agent & Gate",
                "accent": "#4F46E5",
                "bullets": [
                    "Phases 6–7 (Stage 4): 5 Stage MCPs + 3 Runtime MCPs and 2-Pass Gemini orchestration",
                    "Phase 8 (Stage 5): end-to-end data lineage, 5 Golden CQs, and 50-run boundary benchmark",
                    "Deliverables: D4.1–D4.4 and D5.1–D5.5 (Terraform Cloud Run deployment package)"
                ]
            }
        ],
        "table": {
            "headers": ["8-Phase Engineering Flow", "Stage", "Studio Tab", "Stage MCP Tool", "Deliverables", "Bilingual Notebooks (KO / EN)"],
            "rows": [
                ["0. End-to-End Tour", "Overview", "0. Overview", "Run Stage 1–5 individually or all", "-", "stage0_overview_walkthrough_{ko,en}.ipynb"],
                ["1. Prepare · 2. Analyze", "Stage 1", "Stage 1. Asset", "mcp_stage1_asset_discovery", "D1.1 – D1.4", "stage1_asset_and_cq_{ko,en}.ipynb"],
                ["3. Parse · 4. Integrate", "Stage 2", "Stage 2. Wiki & Semantic", "mcp_stage2_wiki_and_semantic", "D2.1 – D2.6", "stage2_wiki_and_semantic_graph_{ko,en}.ipynb"],
                ["5. Build Graph", "Stage 3", "Stage 3. Property Graph", "mcp_stage3_property_graph", "D3.1 – D3.4", "stage3_property_graph_bigquery_spanner_{ko,en}.ipynb"],
                ["6. Build Agent · 7. Answer", "Stage 4", "Stage 4. Agent & MCP", "mcp_stage4_agent_orchestration (+3 Runtime)", "D4.1 – D4.4", "stage4_agent_and_mcp_execution_{ko,en}.ipynb"],
                ["8. Verify & Gate", "Stage 5", "Stage 5. Lineage & Eval", "mcp_stage5_lineage_and_eval", "D5.1 – D5.5", "stage5_lineage_and_evaluation_{ko,en}.ipynb"]
            ]
        },
        "takeaway": "1:1 Alignment: Every stage maps directly to (1) a Methodology Guide, (2) a Studio Tab, (3) an MCP Tool, and (4) a Bilingual Jupyter Notebook.",
        "speaker_notes": (
            "[Instructor Guide — Slide 03: 8-Phase Engineering Flow & 5-Stage Lifecycle]\n"
            "• Point to the top architecture banner (stage0_overview_flow_en.png) and explain how the 8 engineering phases map onto the 5 stages.\n"
            "• Emphasize that this methodology is executable: running `python3 run_pipeline.py` executes Stage 1 through Stage 5 end-to-end against live BigQuery, GCS, and Vertex AI."
        )
    },
    {
        "slide_no": 4,
        "badge": "MODULE 00 · ADOPTION TRACKS & GCP NATIVE",
        "accent": "#0F9D58",
        "title": "3-Track Adoption Model (`Lite` · `Standard` · `Full`) & GCP Native First",
        "subtitle": "Configurable adoption tracks (`config/starter_config.json`) tailored to organizational data readiness and Google Cloud Native boundaries",
        "banner_img": None,
        "cards": [
            {
                "tag": "TRACK 1 · LITE",
                "title": "Unstructured Policy Quickstart",
                "accent": "#1A73E8",
                "bullets": [
                    "Active Stages: Stage 1 → Stage 2 → Stage 4 (skips Stage 3)",
                    "Graph Engine: none (3-Layer Wiki + tb_domain_rules lookup)",
                    "Best For: Rapidly validating policy Q&A and rule math before DW table integration"
                ]
            },
            {
                "tag": "TRACK 2 · STANDARD (RECOMMENDED)",
                "title": "Hybrid DW + Policy Property Graph",
                "accent": "#0F9D58",
                "bullets": [
                    "Active Stages: Stage 1 → Stage 2 → Stage 3 → Stage 4",
                    "Graph Engine: bigquery (STARTER_ONTOLOGY_GRAPH) + optional Spanner DDL",
                    "Best For: Combining structured master/contract tables and policy rules via multi-hop ISO GQL"
                ]
            },
            {
                "tag": "TRACK 3 · FULL",
                "title": "Full Lineage, 50-Run Eval & Release",
                "accent": "#4F46E5",
                "bullets": [
                    "Active Stages: Stage 1 → Stage 2 → Stage 3 → Stage 4 → Stage 5",
                    "Graph Engine: bigquery + End-to-End Lineage + Dual Validator Gate",
                    "Best For: Enterprise audit traceability, 10×5 boundary testing, and Terraform Cloud Run release"
                ]
            }
        ],
        "table": {
            "headers": ["Architectural Layer", "Google Cloud Native Capabilities (Adopted First)", "Starter Custom Extensions", "Engineering Rationale"],
            "rows": [
                ["Data & Graph", "BigQuery Managed Tables, Cloud Storage, SQL:2023 Property Graph", "2-Layer anti-redundancy builder, semantic bridge (edge_rule_applies_to_plan)", "Eliminate external graph DB ETL and bind clauses to plans"],
                ["Ontology & Wiki", "OKF v0.2 JSON-LD compatible graph schema", "Deterministic SHA-256 chunker (anchor_<12hex>), Karpathy 3-Layer Wiki", "Immutable paragraph-level grounding and structured LLM context"],
                ["MCP Tool Layer", "BigQuery Python Client, Parameterized SQL/GQL", "8 Domain MCP Tools (5 Stage MCPs + 3 Runtime MCPs)", "Encapsulate multi-hop GQL and deterministic clawback/TCO math"],
                ["Agent & Infra", "Vertex AI Gemini (gemini-3.8-flash), Cloud Run, Terraform IaC", "2-Pass reasoning loop (catalog validation + guardrail states), 6-Tab Studio", "Prevent parameter guessing and provide visual stage governance"]
            ]
        },
        "takeaway": "GCP Native First: Use 100% managed Google Cloud services for storage, graph querying, LLM inference, and serverless hosting; extend only where domain semantics require it.",
        "speaker_notes": (
            "[Instructor Guide — Slide 04: 3-Track Adoption Model & GCP Native First]\n"
            "• Show how `config/starter_config.json` allows teams to start with `lite` (documents only), graduate to `standard` (BigQuery Property Graph), and finalize with `full` (Lineage + 50-run Boundary Gate).\n"
            "• Review the bottom table so architects clearly understand which components are native GCP features versus starter Python extensions."
        )
    },
    {
        "slide_no": 5,
        "badge": "MODULE 01 · STAGE 1 OVERVIEW",
        "accent": "#1A73E8",
        "title": "Stage 1. Asset Discovery, Domain Scoping & Competency Questions (`D1.1`–`D1.4`)",
        "subtitle": "Define target Competency Questions (CQs) first, select only the required tables and policy guides, and load them atomically into BigQuery",
        "banner_img": "stage1_prepare_analyze_flow_en.png",
        "cards": [
            {
                "tag": "STEP 1 · CQ-FIRST SCOPING",
                "title": "Competency-Question-Driven Scope",
                "accent": "#1A73E8",
                "bullets": [
                    "Avoid boiling the ocean; scope only the tables and documents needed to answer target CQs",
                    "Starter scope: 2 policy guides (subsidy & welfare exemption) + 6 structured CSV files",
                    "Standardize 4 core domain terms in business_glossary.json"
                ]
            },
            {
                "tag": "STEP 2 · ATOMIC INGESTION",
                "title": "Transactional BigQuery Loading",
                "accent": "#0F9D58",
                "bullets": [
                    "Provision 10 BigQuery tables declaratively via Terraform (terraform/bigquery.tf)",
                    "pipeline/ingest.py (run_ingest) performs atomic TRUNCATE → INSERT from CSVs & chunks",
                    "Zero hardcoded domain values in Python — data/input/ files act as the single source of truth"
                ]
            },
            {
                "tag": "STEP 3 · STAGE 1 MCP",
                "title": "mcp_stage1_asset_discovery",
                "accent": "#4F46E5",
                "bullets": [
                    "profile_tables: Queries __TABLES__ metadata for live row counts and byte sizes across 10 tables",
                    "tag_pii_governance: Verifies all customer IDs match synthetic pattern ^CUST_DEMO_[0-9]{3}$",
                    "Requires non_deidentified_ids == 0 to pass Gate 1"
                ]
            }
        ],
        "table": {
            "headers": ["Input Asset Path (`data/input/`)", "Target BigQuery Table", "Row Count", "Role & Key Attributes"],
            "rows": [
                ["01_guides/sample_policy_guide.md (+1 guide)", "tb_doc_chunks", "5 rows", "DOC_CHUNK_001–005 source paragraphs and SHA-256 hash anchors"],
                ["03_tables/devices.csv · plans.csv · subsidies.csv", "tb_device_master · tb_plan_master · tb_subsidy_policy", "4 / 6 / 6 rows", "Device retail prices, monthly plan fees/discount rates, public & extra subsidies"],
                ["03_tables/customer_contracts.csv", "tb_customer_contract", "6 rows", "CUST_DEMO_001–006 active device, plan, elapsed_days, and welfare status"],
                ["03_tables/domain_rules.csv · rule_plan_edges.csv", "tb_domain_rules · edge_rule_applies_to_plan", "4 / 12 rows", "4 deterministic business rules and 12 rule-to-plan semantic bridge edges"]
            ]
        },
        "takeaway": "Stage 1 Rule: Never model schemas in a vacuum — define Golden Competency Questions (CQs) first, then ingest only the tables and clauses required to prove them.",
        "speaker_notes": (
            "[Instructor Guide — Slide 05: Stage 1 Asset Discovery & Scoping]\n"
            "• Emphasize why CQ-first scoping saves weeks of wasted modeling.\n"
            "• Demonstrate `mcp_stage1_asset_discovery` in Studio Tab 1 (`Stage 1. Asset`) or `notebooks/en/stage1_asset_and_cq_en.ipynb` to inspect the 10 BigQuery tables and verify `non_deidentified_ids: 0`."
        )
    },
    {
        "slide_no": 6,
        "badge": "MODULE 01 · STAGE 1 DEEP DIVE",
        "accent": "#1A73E8",
        "title": "Stage 1 Deep Dive: Golden CQ Specification & Independent SQL Oracle (`Gate 1`)",
        "subtitle": "Pairing every Competency Question with human-verified ground-truth math (`expected_math`) and an independent BigQuery `verification_sql` query",
        "banner_img": None,
        "cards": [
            {
                "tag": "ANATOMY OF A CQ",
                "title": "6 Mandatory Fields per Golden CQ",
                "accent": "#1A73E8",
                "bullets": [
                    "query: Natural-language business question sent to the agent",
                    "expected_math: Ground-truth numeric dictionary (e.g., {\"penalty\": 100000})",
                    "verification_sql: Independent BigQuery SQL query that computes the exact answer",
                    "grounded_chunk: Mandatory policy chunk ID that must be cited (e.g., DOC_CHUNK_002)"
                ]
            },
            {
                "tag": "EXAMPLE · CQ-02",
                "title": "180-Day Prorated Penalty Verification",
                "accent": "#0F9D58",
                "bullets": [
                    "Query: What is the penalty if CUST_DEMO_001 downgrades to 5G Standard at day 90?",
                    "Ledger: Initial subsidy 500,000 KRW → Target plan subsidy 300,000 KRW (Diff: 200,000 KRW)",
                    "Formula: 200,000 × (180 - 90) / 180 = 100,000 KRW (Must cite DOC_CHUNK_002)"
                ]
            },
            {
                "tag": "GATE 1 CHECKLIST",
                "title": "Stage 1 Quality Gate (Gate 1)",
                "accent": "#4F46E5",
                "bullets": [
                    "1) All 5 Golden CQs define expected_math, verification_sql, and grounded_chunk",
                    "2) Live BigQuery execution of verification_sql matches expected_math (SQL_MATCH)",
                    "3) pii_check.non_deidentified_ids == 0 and all 10 table row counts match CSV inputs"
                ]
            }
        ],
        "table": {
            "headers": ["CQ ID", "Verification Scenario Summary", "Expected Ground Truth (`expected_math`)", "Required Chunk", "Primary Target MCP Tool"],
            "rows": [
                ["CQ-01", "Lookup CUST_DEMO_001 contract, device, plan, total subsidy, and installment principal", "total_subsidy: 575,000 / principal: 675,000", "DOC_CHUNK_001", "mcp_lookup_customer_profile"],
                ["CQ-02", "Compute 180-day prorated penalty for CUST_DEMO_001 downgrading to 5G Standard at day 90", "penalty_krw: 100,000", "DOC_CHUNK_002", "mcp_calculate_penalty_rule"],
                ["CQ-03", "Verify 0 KRW penalty waiver for senior welfare customer CUST_DEMO_003 on plan downgrade", "penalty_krw: 0 (EXEMPT_WELFARE)", "DOC_CHUNK_004", "mcp_calculate_penalty_rule"],
                ["CQ-04", "Compare 24-month TCO (Public Subsidy vs. 25% Optional Discount) for Core Flagship 256GB on 5G Signature", "subsidy_tco: 3,422,500 / contract_tco: 3,590,000", "DOC_CHUNK_005", "mcp_calculate_penalty_rule"],
                ["CQ-05", "Traverse multi-hop graph for 5G Premium plan rules and retrieve SHA-256 source chunks", "matched_rules: 3 / chunks: DOC_CHUNK_001–003", "DOC_CHUNK_002", "mcp_query_graph_and_wiki"]
            ]
        },
        "takeaway": "Gate 1 Principle: Golden CQs (5 cases) and Boundary Cases (10 cases) authored in Stage 1 serve directly as the automated release gate in Stage 5.",
        "speaker_notes": (
            "[Instructor Guide — Slide 06: Golden CQ Design & Gate 1]\n"
            "• Review CQ-01 through CQ-05 in the table.\n"
            "• Explain why `verification_sql` is superior to LLM-as-a-Judge: the SQL query runs directly against BigQuery to prove `expected_math` before grading the agent's response."
        )
    },
    {
        "slide_no": 7,
        "badge": "MODULE 02 · STAGE 2 OVERVIEW",
        "accent": "#0F9D58",
        "title": "Stage 2. Unstructured Parsing, SHA-256 Lexical Anchors & OKF v0.2 (`D2.1`–`D2.6`)",
        "subtitle": "Segmenting policy guides into semantic chunks (`DOC_CHUNK_001`–`005`) with immutable cryptographic hashes (`anchor_<12hex>`) and JSON-LD",
        "banner_img": "stage2_parse_integrate_flow_en.png",
        "cards": [
            {
                "tag": "STEP 1 · DETERMINISTIC CHUNKING",
                "title": "Semantic Markers & SHA-256 Anchors",
                "accent": "#1A73E8",
                "bullets": [
                    "Splits guides by explicit <!-- DOC_CHUNK_NNN: Title --> markers (or ## headers)",
                    "Computes the first 12 hex digits of SHA-256 over paragraph text (anchor_<12hex>)",
                    "Any single-character policy edit changes the hash immediately for drift detection"
                ]
            },
            {
                "tag": "STEP 2 · OKF v0.2 JSON-LD",
                "title": "Standard Ontology Serialization",
                "accent": "#0F9D58",
                "bullets": [
                    "Serializes the domain root node and lexical chunk nodes into W3C JSON-LD format",
                    "Generates local artifacts data/output/doc_chunks.jsonl and ontology.jsonld",
                    "Loads tb_doc_chunks in BigQuery and syncs raw/, parsed/, ontology/ to GCS"
                ]
            },
            {
                "tag": "STEP 3 · STAGE 2 MCP",
                "title": "mcp_stage2_wiki_and_semantic",
                "accent": "#4F46E5",
                "bullets": [
                    "compile_3layer_wiki: Verifies synchronized objects in GCS bucket",
                    "extract_hash_anchors: Inspects content_sha256 anchors in tb_doc_chunks",
                    "bind_semantic_bridges: Verifies inner join between tb_domain_rules and tb_doc_chunks"
                ]
            }
        ],
        "table": {
            "headers": ["Chunk ID", "Source Guide (`data/input/01_guides/`)", "Section Title", "Bound Business Rule ID", "Core Policy Clause Summary"],
            "rows": [
                ["DOC_CHUNK_001", "sample_policy_guide.md", "Public & Additional Subsidy Cap", "RULE_SUBSIDY_CAP", "Additional subsidy is capped at 15% of public subsidy; total subsidy <= retail price"],
                ["DOC_CHUNK_002", "sample_policy_guide.md", "180-Day Retention & Prorated Clawback", "RULE_SIX_PLAN_180D", "Downgrading within 180 days triggers prorated clawback on the subsidy difference"],
                ["DOC_CHUNK_003", "sample_policy_guide.md", "High-Tier Plan Retention Threshold (85,000 KRW)", "RULE_SIX_PLAN_180D", "Plan changes remaining at or above 85,000 KRW/month incur 0 KRW subsidy difference clawback"],
                ["DOC_CHUNK_004", "sample_welfare_exemption_guide.md", "Senior & Welfare Penalty Exemption", "RULE_WELFARE_EXEMPT", "Contracts with SENIOR_EXEMPT welfare status receive 100% penalty exemption (0 KRW)"],
                ["DOC_CHUNK_005", "sample_welfare_exemption_guide.md", "24-Month TCO Comparison Rule", "RULE_TCO_24M", "Compare 24-month total cost between Public Subsidy and 25% Optional Contract Discount"]
            ]
        },
        "takeaway": "Immutable Lexical Anchoring: Every business rule in tb_domain_rules references a mandatory source_chunk_id and cryptographic SHA-256 anchor in tb_doc_chunks.",
        "speaker_notes": (
            "[Instructor Guide — Slide 07: Stage 2 Unstructured Parsing & SHA-256 Anchors]\n"
            "• Explain why arbitrary token/character sliding windows break legal and policy clauses.\n"
            "• By anchoring each semantic section (`DOC_CHUNK_001`–`005`) with a deterministic SHA-256 hash, every rule calculation and agent answer can cite the exact immutable policy clause."
        )
    },
    {
        "slide_no": 8,
        "badge": "MODULE 02 · STAGE 2 DEEP DIVE",
        "accent": "#0F9D58",
        "title": "Stage 2 Deep Dive: Karpathy 3-Layer LLM-Wiki & Semantic Bridges (`Gate 2`)",
        "subtitle": "Compiling human- and LLM-readable 3-Layer Markdown Wikis (`L1 Summary · L2 Entities · L3 Concepts/Rules`) and binding rules to plans",
        "banner_img": None,
        "cards": [
            {
                "tag": "LAYER 1 · SUMMARY",
                "title": "L1 Summary (summary.md)",
                "accent": "#1A73E8",
                "bullets": [
                    "Executive corpus index: 2 policy guides, 5 hashed chunks, and 4 master tables",
                    "Lists every chunk ID with its SHA-256 anchor prefix and section summary",
                    "Serves as the top-level entry point for both engineers and LLM agents"
                ]
            },
            {
                "tag": "LAYER 2 · ENTITIES",
                "title": "L2 Entities (entities.md)",
                "accent": "#0F9D58",
                "bullets": [
                    "Canonical catalog of structured entities (4 Devices, 6 Plans, 6 Subsidies, 6 Contracts)",
                    "Maintained symmetrically in data/llm_wiki/en/ (100% English) and data/llm_wiki/ko/",
                    "Provides authoritative entity names, retail prices, monthly fees, and retention days"
                ]
            },
            {
                "tag": "LAYER 3 · CONCEPTS & RULES",
                "title": "L3 Concepts & Rules (concepts/rules.md)",
                "accent": "#4F46E5",
                "bullets": [
                    "concepts.md: Defines 4 core graph relations (USES_DEVICE, SUBSCRIBES_PLAN, HAS_SUBSIDY_POLICY, APPLIES_TO_PLAN)",
                    "rules.md: Documents 4 deterministic formulas and their source chunk bindings",
                    "edge_rule_applies_to_plan (12 rows) bridges unstructured rules to structured plan IDs"
                ]
            }
        ],
        "table": {
            "headers": ["Deliverable ID", "Artifact Name", "File Path / BigQuery Table", "Gate 2 Pass Criteria"],
            "rows": [
                ["D2.1", "OKF v0.2 Domain Ontology Specification", "data/output/ontology.jsonld", "Valid JSON-LD context, domain root node, and 5 chunk nodes"],
                ["D2.2", "Karpathy 3-Layer LLM-Wiki (EN / KO)", "data/llm_wiki/{en,ko}/{summary,entities,concepts,rules}.md", "All 4 Markdown layers compiled with 0 broken links"],
                ["D2.3", "GCS Ontology Prototype Manifest", "data/llm_wiki/gcs_prototype_manifest.json · gs://.../ontology/", "status == LIVE_GCP_SYNCED · bigquery_tables_loaded == 10"],
                ["D2.4 – D2.6", "Hashed Chunks, Domain Rules & Bridges", "tb_doc_chunks(5) · tb_domain_rules(4) · edge_rule_applies_to_plan(12)", "100% of tb_domain_rules.source_chunk_id resolved in tb_doc_chunks"]
            ]
        },
        "takeaway": "Semantic Bridge (edge_rule_applies_to_plan): Connects unstructured policy rules (rule_id + source_chunk_id) directly to structured rate plans (plan_id).",
        "speaker_notes": (
            "[Instructor Guide — Slide 08: 3-Layer LLM-Wiki & Semantic Bridge Matrix]\n"
            "• Show how `data/llm_wiki/en/` provides a clean, 100% English 3-Layer Wiki (`summary.md`, `entities.md`, `concepts.md`, `rules.md`).\n"
            "• Explain how `edge_rule_applies_to_plan` acts as the semantic bridge table that allows Stage 3 GQL queries to hop from a customer's rate plan directly to the governing policy rule and paragraph chunk."
        )
    },
    {
        "slide_no": 9,
        "badge": "MODULE 03 · STAGE 3 OVERVIEW",
        "accent": "#4F46E5",
        "title": "Stage 3. Zero-ETL 2-Layer Property Graph Architecture (`D3.1`–`D3.4`)",
        "subtitle": "Projecting BigQuery DW tables directly into a SQL:2023 Property Graph (`STARTER_ONTOLOGY_GRAPH`) with zero data duplication",
        "banner_img": "stage3_property_graph_flow_en.png",
        "cards": [
            {
                "tag": "ANTI-REDUNDANCY",
                "title": "2-Layer Anti-Redundancy Principle",
                "accent": "#1A73E8",
                "bullets": [
                    "Never duplicate structured DW tables into external graph databases or text blobs",
                    "Keep relational tables intact and declare VERTEX TABLES (6) & EDGE TABLES (4) in place",
                    "Guarantees 0 duplicate entity keys (duplicate_keys_total == 0) and instant data freshness"
                ]
            },
            {
                "tag": "6 VERTEX TABLES",
                "title": "6 Physical Node Labels",
                "accent": "#0F9D58",
                "bullets": [
                    "CustomerContractNode (tb_customer_contract, KEY: contract_id)",
                    "DeviceNode (tb_device_master) · PlanNode (tb_plan_master) · SubsidyNode (tb_subsidy_policy)",
                    "DomainRuleNode (tb_domain_rules) · DocChunkNode (tb_doc_chunks)"
                ]
            },
            {
                "tag": "4 EDGE TABLES",
                "title": "4 Physical Edge Labels",
                "accent": "#4F46E5",
                "bullets": [
                    "USES_DEVICE (edge_contract_device: Contract → Device)",
                    "SUBSCRIBES_PLAN (edge_contract_plan: Contract → Plan)",
                    "HAS_SUBSIDY_POLICY (Device → Plan) · APPLIES_TO_PLAN (DomainRule → Plan)"
                ]
            }
        ],
        "table": {
            "headers": ["Graph Element", "Graph Label (`STARTER_ONTOLOGY_GRAPH`)", "Underlying BigQuery Table", "Key / Endpoint Mapping (`KEY` / `SOURCE` → `DESTINATION`)", "Rows"],
            "rows": [
                ["Vertex (Node)", "CustomerContractNode / DeviceNode / PlanNode", "tb_customer_contract / tb_device_master / tb_plan_master", "contract_id / device_id / plan_id", "6 / 4 / 6"],
                ["Vertex (Node)", "SubsidyNode / DomainRuleNode / DocChunkNode", "tb_subsidy_policy / tb_domain_rules / tb_doc_chunks", "policy_id / rule_id / chunk_id", "6 / 4 / 5"],
                ["Edge", "USES_DEVICE / SUBSCRIBES_PLAN", "edge_contract_device / edge_contract_plan", "contract_id → device_id / contract_id → plan_id", "6 / 6"],
                ["Edge", "HAS_SUBSIDY_POLICY / APPLIES_TO_PLAN", "edge_subsidy_binding / edge_rule_applies_to_plan", "device_id → plan_id / rule_id → plan_id (with source_chunk_id)", "7 / 12"]
            ]
        },
        "takeaway": "Zero-ETL Property Graph: Any update to underlying BigQuery tables is immediately reflected in graph traversals with zero replication lag or extra storage cost.",
        "speaker_notes": (
            "[Instructor Guide — Slide 09: Stage 3 Zero-ETL Property Graph]\n"
            "• Walk through `pipeline/graph_builder.py` and `data/output/create_property_graph.sql`.\n"
            "• Point out how `STARTER_ONTOLOGY_GRAPH` unifies 6 vertex tables and 4 edge tables inside BigQuery using standard ISO SQL:2023 DDL."
        )
    },
    {
        "slide_no": 10,
        "badge": "MODULE 03 · STAGE 3 DEEP DIVE",
        "accent": "#4F46E5",
        "title": "Stage 3 Deep Dive: Dual DDL (BigQuery vs. Spanner) & Multi-Hop ISO GQL (`Gate 3`)",
        "subtitle": "Comparing analytical BigQuery Property Graph DDL with operational Cloud Spanner Graph DDL and executing 2-Hop/3-Hop GQL traversals",
        "banner_img": None,
        "cards": [
            {
                "tag": "BIGQUERY PROPERTY GRAPH",
                "title": "Serverless Analytical Graph (OLAP)",
                "accent": "#1A73E8",
                "bullets": [
                    "Artifact: data/output/create_property_graph.sql (deployed & queried live)",
                    "Virtualizes enterprise DW tables in place for multi-hop reasoning and reporting",
                    "Combines GRAPH_TABLE(... MATCH ...) with SQL JOIN tb_doc_chunks in one query"
                ]
            },
            {
                "tag": "CLOUD SPANNER GRAPH",
                "title": "Low-Latency Operational Graph (OLTP)",
                "accent": "#0F9D58",
                "bullets": [
                    "Artifact: data/output/create_spanner_graph.sql (automated DDL synthesis)",
                    "Uses INTERLEAVE IN PARENT physical co-location for sub-10ms operational traversals",
                    "Ideal for real-time fraud detection (FDS), equipment interlocks, and order-time gating"
                ]
            },
            {
                "tag": "MULTI-HOP ISO GQL",
                "title": "3-Hop Traversal + Lexical Chunk Join",
                "accent": "#4F46E5",
                "bullets": [
                    "Traverses CustomerContract(c) → Device(d) & Plan(p) ← DomainRule(r) in one MATCH",
                    "Joins tb_doc_chunks via edge property ap.source_chunk_id to attach clause text & hash",
                    "Gate 3: DDL status == SUCCESS, GQL path count > 0, duplicate keys == 0"
                ]
            }
        ],
        "table": {
            "headers": ["Traversal Mode", "ISO GQL `GRAPH_TABLE` Pattern", "Hops", "Lexical Evidence Binding", "Executing MCP Tool"],
            "rows": [
                ["Customer-Centric Traversal (with customer_id)", "MATCH (c:CustomerContractNode)-[:USES_DEVICE]->(d:DeviceNode), (c)-[:SUBSCRIBES_PLAN]->(p:PlanNode)<-[ap:APPLIES_TO_PLAN]-(r:DomainRuleNode)", "3-Hop", "JOIN tb_doc_chunks ch ON ch.chunk_id = ap.source_chunk_id", "mcp_query_graph_and_wiki"],
                ["Catalog Policy Traversal (without customer_id)", "MATCH (d:DeviceNode)-[hs:HAS_SUBSIDY_POLICY]->(p:PlanNode)<-[ap:APPLIES_TO_PLAN]-(r:DomainRuleNode)", "2-Hop", "JOIN tb_doc_chunks ch ON ch.chunk_id = ap.source_chunk_id", "mcp_query_graph_and_wiki"],
                ["Stage 3 Topology Verification Probe", "MATCH (d:DeviceNode)-[hs:HAS_SUBSIDY_POLICY]->(p:PlanNode)<-[ap:APPLIES_TO_PLAN]-(r:DomainRuleNode) RETURN COUNT(*)", "2-Hop", "Counts total valid rule-to-subsidy graph paths (gql_paths)", "mcp_stage3_property_graph"]
            ]
        },
        "takeaway": "Single-Query Fusion: GRAPH_TABLE resolves multi-hop entity-rule relationships while the outer SQL JOIN attaches the exact policy paragraph and SHA-256 anchor.",
        "speaker_notes": (
            "[Instructor Guide — Slide 10: Dual Graph DDL & Multi-Hop ISO GQL]\n"
            "• Show how the Studio `Stage 3. Property Graph` tab lets learners toggle between BigQuery Property Graph DDL and Cloud Spanner Graph DDL.\n"
            "• Highlight how `notebooks/en/stage3_property_graph_bigquery_spanner_en.ipynb` prints both the exact GQL statement and bound variables (`customer_id`, `plan_name`) before rendering the result DataFrame."
        )
    },
    {
        "slide_no": 11,
        "badge": "MODULE 04 · STAGE 4 OVERVIEW",
        "accent": "#D97706",
        "title": "Stage 4. 8 Domain MCP Tools Architecture (`5 Stage + 3 Runtime`) (`D4.1`–`D4.4`)",
        "subtitle": "Isolating agent cognitive load by encapsulating complex SQL joins, GQL traversals, and domain math behind 8 structured MCP tools",
        "banner_img": "stage4_agent_mcp_flow_en.png",
        "cards": [
            {
                "tag": "COGNITIVE ISOLATION",
                "title": "Agent Cognitive Load Isolation",
                "accent": "#1A73E8",
                "bullets": [
                    "Agents never write raw multi-table SQL joins or brittle GQL syntax on the fly",
                    "Domain semantics (customer profile, penalty/TCO calculator, graph traversal) are pre-packaged",
                    "Every MCP call returns structured JSON records plus the exact BigQuery Job ID"
                ]
            },
            {
                "tag": "5 STAGE MCP TOOLS",
                "title": "Lifecycle Governance MCPs (5 Tools)",
                "accent": "#0F9D58",
                "bullets": [
                    "mcp_stage1_asset_discovery · mcp_stage2_wiki_and_semantic",
                    "mcp_stage3_property_graph · mcp_stage4_agent_orchestration",
                    "mcp_stage5_lineage_and_eval (powers Studio stage verification & gate checks)"
                ]
            },
            {
                "tag": "3 RUNTIME MCP TOOLS",
                "title": "Real-Time Agent Inference MCPs (3 Tools)",
                "accent": "#D97706",
                "bullets": [
                    "mcp_lookup_customer_profile: Contract, device, plan, subsidy, principal + RULE_SUBSIDY_CAP",
                    "mcp_calculate_penalty_rule: Exemption check, 180-day prorated clawback & 24M TCO comparison",
                    "mcp_query_graph_and_wiki: Multi-hop GQL traversal over STARTER_ONTOLOGY_GRAPH + chunk text"
                ]
            }
        ],
        "table": {
            "headers": ["Category", "MCP Tool Name (`src/agent/mcp_server.py`)", "Internal Execution Steps", "Key Output Payload & Status Codes"],
            "rows": [
                ["Stages 1–3", "mcp_stage1 / stage2 / stage3", "profile_tables, tag_pii / bind_semantic_bridges / verify_gql_templates", "Table row counts, PII check (0), anchored chunks, GQL path count"],
                ["Stages 4–5", "mcp_stage4 / stage5", "verify_grounding_anchors / build_4tier_lineage, run_golden_cq_suite", "4 active rules, end-to-end lineage (18 rows), Golden CQ & Boundary reports"],
                ["Runtime 1", "mcp_lookup_customer_profile", "lookup_contract → lookup_device_price → lookup_subsidy_policy", "Contract ledger, total subsidy, installment principal, DOC_CHUNK_001"],
                ["Runtime 2", "mcp_calculate_penalty_rule", "check_exemptions → compute_180d_prorated_clawback → compare_24m_tco", "Exemption status, prorated penalty KRW, 24M TCO matrix (SUCCESS / INSUFFICIENT)"],
                ["Runtime 3", "mcp_query_graph_and_wiki", "traverse_property_graph → fetch_okf_hash_anchor → verify_dw_schema", "Matched GQL paths, rule formulas, source chunk text & SHA-256 hash"]
            ]
        },
        "takeaway": "Domain MCP Abstraction: The LLM only extracts validated catalog parameters; the MCP server executes deterministic SQL/GQL and arithmetic.",
        "speaker_notes": (
            "[Instructor Guide — Slide 11: Stage 4 8 Domain MCP Tools]\n"
            "• Explain the division between the 5 Stage Governance MCPs and the 3 Runtime Inference MCPs inside `src/agent/mcp_server.py`.\n"
            "• Note that in English mode (`lang='en'` / `STARTER_LANG='en'`), `src/agent/i18n_en.py` ensures all tool summaries and returned records are 100% localized into English."
        )
    },
    {
        "slide_no": 12,
        "badge": "MODULE 04 · STAGE 4 DEEP DIVE",
        "accent": "#D97706",
        "title": "Stage 4 Deep Dive: Deterministic Penalty Decision Tree & 2-Pass Gemini Loop (`Gate 4`)",
        "subtitle": "Combining a 6-step SQL penalty/TCO engine with a 2-Pass Vertex AI Gemini (`gemini-3.8-flash`) reasoning loop and explicit guardrail states",
        "banner_img": None,
        "cards": [
            {
                "tag": "PASS 1 · DECOMPOSE & VALIDATE",
                "title": "Pass 1: Catalog-Constrained Slot Parsing",
                "accent": "#1A73E8",
                "bullets": [
                    "Loads live device, plan, and customer ID catalogs from BigQuery (5-minute cache)",
                    "Gemini Pass 1 decomposes the user query into structured parameters and MCP sub-goals",
                    "Strips any entity name not present in the catalog and accepts only explicit numbers"
                ]
            },
            {
                "tag": "DETERMINISTIC ENGINE",
                "title": "6-Step Penalty Tree & 24M TCO Math",
                "accent": "#D97706",
                "bullets": [
                    "1) Welfare exemption (SENIOR_EXEMPT) → 0 KRW  2) No public subsidy → 0 KRW",
                    "3) Missing target plan or elapsed days → Returns INSUFFICIENT_PARAMETERS",
                    "4) Elapsed ≥ 180d → 0 KRW  5) Target fee ≥ 85,000 KRW → 0 KRW  6) Prorated clawback"
                ]
            },
            {
                "tag": "PASS 2 · GROUNDED SYNTHESIS",
                "title": "Pass 2: Guardrail-Enforced Answer",
                "accent": "#0F9D58",
                "bullets": [
                    "Locks response_status: GROUNDED / MATCH_NOT_FOUND / INSUFFICIENT_PARAMETERS / BQ_ERROR",
                    "Gemini Pass 2 synthesizes the final response strictly from MCP tool JSON outputs",
                    "Enforces structure: Conclusion → Supporting Ledger Data → Rule & Chunk Hash → BQ Job ID"
                ]
            }
        ],
        "table": {
            "headers": ["Agent Response Status (`response_status`)", "Trigger Condition", "Mandatory Agent Behavior (Gate 4 Standard)", "Representative Test Cases"],
            "rows": [
                ["GROUNDED", "All required parameters resolved and MCP queries return valid rows", "Cite exact calculated KRW amounts, Rule ID, DOC_CHUNK_00X hash, and BQ Job ID", "CQ-01 – CQ-05, BQ-01, BQ-06, BQ-10"],
                ["INSUFFICIENT_PARAMETERS", "Penalty query omits customer_id/device or target_plan/elapsed_days", "Refuse to guess numbers; list the exact missing parameters needed from the user", "BQ-02, BQ-03, BQ-07, BQ-08"],
                ["MATCH_NOT_FOUND", "Requested device, plan, or subsidy combination does not exist in catalog", "State MATCH_NOT_FOUND (0 rows) in the opening sentence and list valid catalog options", "BQ-04, BQ-05, BQ-09"],
                ["BQ_QUERY_ERROR", "BigQuery execution error, permission failure, or network interruption", "Surface the query error transparently instead of masking it as 0 rows", "Fault-injection / IAM checks"]
            ]
        },
        "takeaway": "Gate 4 Rule: An enterprise agent is defined not just by answering valid queries (GROUNDED), but by refusing to guess when parameters are missing (INSUFFICIENT_PARAMETERS).",
        "speaker_notes": (
            "[Instructor Guide — Slide 12: 6-Step Penalty Tree & 2-Pass Gemini Loop]\n"
            "• Walk through `AiFdeAgentEngine.execute_cycle()` in `src/agent/reasoning_engine.py`.\n"
            "• Explain why `response_status` is determined in Python between Pass 1 (Tool Dispatch) and Pass 2 (Answer Synthesis), preventing the LLM from inventing numbers when `INSUFFICIENT_PARAMETERS` or `MATCH_NOT_FOUND` occurs."
        )
    },
    {
        "slide_no": 13,
        "badge": "MODULE 05 · STAGE 5 OVERVIEW",
        "accent": "#0F9D58",
        "title": "Stage 5. End-to-End Data Lineage & Impact Traceability (`D5.1`–`D5.2`)",
        "subtitle": "Full auditability from Raw Files (`Tier 0`) → Hashed Chunks (`Tier 1`) → Rules & Bridges (`Tier 2`) → Property Graph (`Tier 3`) → Agent Answers (`Tier 4`)",
        "banner_img": "stage5_lineage_eval_flow_en.png",
        "cards": [
            {
                "tag": "TIER 0 & TIER 1",
                "title": "Raw Guides & CSVs → Hashed Chunks",
                "accent": "#1A73E8",
                "bullets": [
                    "Tier 0: sample_policy_guide.md, sample_welfare_exemption_guide.md, and 6 CSV files",
                    "Tier 1: tb_doc_chunks (DOC_CHUNK_001–005 with SHA-256 content_sha256)",
                    "Detects exact paragraph modifications whenever policy documents are revised"
                ]
            },
            {
                "tag": "TIER 2 & TIER 3",
                "title": "Domain Rules → Property Graph",
                "accent": "#0F9D58",
                "bullets": [
                    "Tier 2: tb_domain_rules (4 rules) + edge_rule_applies_to_plan (12 plan bridges)",
                    "Tier 3: tb_customer_contract (6 contracts) + STARTER_ONTOLOGY_GRAPH (6V × 4E)",
                    "mcp_stage5_lineage_and_eval joins 18 end-to-end lineage records in real time"
                ]
            },
            {
                "tag": "TIER 4 · AUDIT TRAIL",
                "title": "Grounded CQ Answers & Job IDs",
                "accent": "#4F46E5",
                "bullets": [
                    "Tier 4: Links every agent response to Rule ID, Chunk ID, SHA-256 hash, and BQ Job ID",
                    "Proves to auditors exactly which table row and policy clause produced any number",
                    "Enforces synthetic customer IDs (CUST_DEMO_001–006) for PII governance (D5.2)"
                ]
            }
        ],
        "table": {
            "headers": ["Lineage Tier Transition", "Participating Assets / Tables", "Join / Bridge Key", "Downstream Impact Analysis"],
            "rows": [
                ["Tier 0 → Tier 1", "Policy Markdown Guides (2) → tb_doc_chunks (5 rows)", "chunk_id (DOC_CHUNK_001–005) + content_sha256", "Paragraph text edit alters SHA-256 hash → flags bound rules for review"],
                ["Tier 1 → Tier 2", "tb_doc_chunks → tb_domain_rules · edge_rule_applies_to_plan", "source_chunk_id → rule_id → target_plan_id", "Identifies which rate plans (e.g., 5G Signature) are affected by a clause change"],
                ["Tier 2 → Tier 3", "edge_rule_applies_to_plan → STARTER_ONTOLOGY_GRAPH", "plan_id · device_id · contract_id (18 lineage paths)", "Maps affected rate plans to active customer contracts (CUST_DEMO_001–006)"],
                ["Tier 3 → Tier 4", "STARTER_ONTOLOGY_GRAPH → 8 MCPs → Gemini 2-Pass Answer", "rule_id + source_chunk_id + bq_job_id", "Flags Golden CQs (CQ-01–05) whose expected ground truth must be re-verified"]
            ]
        },
        "takeaway": "End-to-End Lineage: When a single paragraph in a policy document changes, one query traces every affected business rule, rate plan, customer contract, and CQ.",
        "speaker_notes": (
            "[Instructor Guide — Slide 13: Stage 5 End-to-End Data Lineage]\n"
            "• Demonstrate `Stage 5. Lineage & Eval` in the Studio or `notebooks/en/stage5_lineage_and_evaluation_en.ipynb`.\n"
            "• Explain how the 18 lineage paths connect `CUST_DEMO_001`–`006` through their devices and rate plans to the 4 domain rules and 5 hashed document chunks."
        )
    },
    {
        "slide_no": 14,
        "badge": "MODULE 05 · STAGE 5 DEEP DIVE",
        "accent": "#0F9D58",
        "title": "Stage 5 Deep Dive: Dual Benchmark (`5 Golden CQs + 10×5 Boundary`) & Release Gate (`Gate 5`)",
        "subtitle": "Automated SQL ground-truth verification, 50-run boundary consistency benchmarking (`pipeline/validator.py`), and Terraform Cloud Run deployment",
        "banner_img": None,
        "cards": [
            {
                "tag": "BENCHMARK 1 · GOLDEN CQ",
                "title": "5 Golden CQs Accuracy Suite (D5.3)",
                "accent": "#1A73E8",
                "bullets": [
                    "Artifact: data/output/cq_benchmark_report.json (5/5 PASS, 100.0%)",
                    "Compares live BigQuery verification_sql results against expected_math (SQL_MATCH)",
                    "Verifies that live agent answers contain exact target numbers and DOC_CHUNK_00X citations"
                ]
            },
            {
                "tag": "BENCHMARK 2 · BOUNDARY 10×5",
                "title": "10 Boundary Cases × 5 Runs = 50 Calls (D5.4)",
                "accent": "#0F9D58",
                "bullets": [
                    "Artifact: data/output/boundary_benchmark_results.json (50 live Gemini + BQ runs)",
                    "Mixes GROUNDED (3), INSUFFICIENT_PARAMETERS (4), and MATCH_NOT_FOUND (3) cases",
                    "Measures avg_success_rate, avg_consistency_rate, and avg_intent_stability across 5 runs"
                ]
            },
            {
                "tag": "GATE 5 & TERRAFORM IaC",
                "title": "Production Release Gate (D5.5)",
                "accent": "#4F46E5",
                "bullets": [
                    "Dockerfile + declarative Terraform (main.tf, bigquery.tf, storage.tf, iam.tf, cloud_run.tf)",
                    "Security audit: 0 hardcoded API keys (AIza...), 0 real customer names, 0 local paths",
                    "Approves Cloud Run deployment only when Gate 1 through Gate 5 all pass"
                ]
            }
        ],
        "table": {
            "headers": ["Evaluation Suite", "Input Dataset (`data/input/04_cq/`)", "Total Executions", "Primary KPIs Measured", "Output Report (`data/output/`)"],
            "rows": [
                ["Golden CQ Ground-Truth Suite", "golden_competency_questions.json (CQ-01 – CQ-05)", "5 runs + 5 SQL oracle checks", "accuracy_rate (100.0%), verification_status (SQL_MATCH)", "cq_benchmark_report.json"],
                ["Boundary — Grounded Edge Cases", "boundary_cases.json (BQ-01, BQ-06, BQ-10)", "3 cases × 5 runs = 15 runs", "Exact numeric/chunk grounding & 5-run repeatability", "boundary_benchmark_results.json"],
                ["Boundary — Missing Parameters", "boundary_cases.json (BQ-02, BQ-03, BQ-07, BQ-08)", "4 cases × 5 runs = 20 runs", "Zero hallucinated assumptions & INSUFFICIENT_PARAMETERS stability", "boundary_benchmark_results.json"],
                ["Boundary — Unmatched Catalog", "boundary_cases.json (BQ-04, BQ-05, BQ-09)", "3 cases × 5 runs = 15 runs", "Out-of-catalog rejection & MATCH_NOT_FOUND consistency", "boundary_benchmark_results.json"]
            ]
        },
        "takeaway": "Release Gate (Gate 5): Production deployment requires passing both answerable questions (5 Golden CQs) and unanswerable/ambiguous questions (50 Boundary runs).",
        "speaker_notes": (
            "[Instructor Guide — Slide 14: Dual Evaluation Harness & Gate 5]\n"
            "• Explain how `python3 pipeline/validator.py` executes both the 5 Golden CQs and the 10×5 Boundary Benchmark.\n"
            "• Emphasize repeatability: running each boundary case 5 times verifies that the 2-Pass agent deterministically returns `INSUFFICIENT_PARAMETERS` or `MATCH_NOT_FOUND` without temperature drift."
        )
    },
    {
        "slide_no": 15,
        "badge": "MODULE 06 · HANDS-ON LABS",
        "accent": "#1A73E8",
        "title": "Hands-On Lab Environment: 6-Tab Governance Studio & 12 Bilingual Notebooks",
        "subtitle": "Interactive exploration via the live Cloud Run Studio and step-by-step code execution in `notebooks/ko/` and `notebooks/en/`",
        "banner_img": None,
        "cards": [
            {
                "tag": "WEB STUDIO (6-TAB)",
                "title": "Interactive Governance Studio",
                "accent": "#1A73E8",
                "bullets": [
                    "0. Overview: 8-Phase architecture diagram, active track badge, 1-click Stage 1–5 runner",
                    "Stages 1–3 Tabs: Asset inventory, 3-Layer Wiki viewer, Semantic & Property Graph canvas",
                    "Stages 4–5 Tabs: 8 MCP tool runner, 2-Pass Agent console, End-to-End Lineage & Eval dashboard"
                ]
            },
            {
                "tag": "ENGLISH NOTEBOOKS (6)",
                "title": "100% English Notebooks (notebooks/en/)",
                "accent": "#0F9D58",
                "bullets": [
                    "stage0_overview_walkthrough_en.ipynb through stage5_lineage_and_evaluation_en.ipynb",
                    "Powered by STARTER_LANG='en' & src/agent/i18n_en.py — 0 Hangul characters in outputs",
                    "Displays explicit GQL statements, bound variables, English DataFrames, and Gemini answers"
                ]
            },
            {
                "tag": "KOREAN NOTEBOOKS (6)",
                "title": "Korean Notebooks (notebooks/ko/)",
                "accent": "#4F46E5",
                "bullets": [
                    "stage0_overview_walkthrough_ko.ipynb through stage5_lineage_and_evaluation_ko.ipynb",
                    "Symmetric structure with embedded Korean architecture banners (stage0..5_*_flow_ko.png)",
                    "Validated via notebooks/validate_and_pack_notebooks.py (12/12 PASS)"
                ]
            }
        ],
        "table": {
            "headers": ["Stage", "English Notebook (`notebooks/en/`)", "Korean Notebook (`notebooks/ko/`)", "Hands-On Lab Exercises & Visual Outputs"],
            "rows": [
                ["Stage 0", "stage0_overview_walkthrough_en.ipynb", "stage0_overview_walkthrough_ko.ipynb", "8-Phase pipeline tour, 10-table snapshot, GQL traversal, MCP call, and 2-Pass agent demo"],
                ["Stage 1", "stage1_asset_and_cq_en.ipynb", "stage1_asset_and_cq_ko.ipynb", "Master table profiling, policy term frequency chart, and Golden CQ SQL verification"],
                ["Stage 2", "stage2_wiki_and_semantic_graph_en.ipynb", "stage2_wiki_and_semantic_graph_ko.ipynb", "SHA-256 chunking, 3-Layer Wiki inspection, and DocChunk-Rule-Plan bridge graph"],
                ["Stage 3", "stage3_property_graph_bigquery_spanner_en.ipynb", "stage3_property_graph_bigquery_spanner_ko.ipynb", "BigQuery Property Graph vs. Spanner DDL comparison and 2-Hop/3-Hop ISO GQL queries"],
                ["Stage 4", "stage4_agent_and_mcp_execution_en.ipynb", "stage4_agent_and_mcp_execution_ko.ipynb", "8 MCP tool executions, 180-day penalty & 24M TCO charts, and live 2-Pass Gemini traces"],
                ["Stage 5", "stage5_lineage_and_evaluation_en.ipynb", "stage5_lineage_and_evaluation_ko.ipynb", "end-to-end lineage graph visualization, Golden CQ 5/5 report, and 50-run boundary charts"]
            ]
        },
        "takeaway": "Symmetric Bilingual Packaging: methodology/{ko,en}/, data/llm_wiki/{ko,en}/, notebooks/{ko,en}/, and slides/{ko,en}/ mirror each other 1:1.",
        "speaker_notes": (
            "[Instructor Guide — Slide 15: Hands-On Studio & 12 Bilingual Notebooks]\n"
            "• Point learners to `notebooks/README.md` for choosing between the English (`notebooks/en/`) and Korean (`notebooks/ko/`) tracks.\n"
            "• Show how `validate_and_pack_notebooks.py` embeds the top PNG banner attachments and verifies zero cell errors across all 12 notebooks."
        )
    },
    {
        "slide_no": 16,
        "badge": "MODULE 07 · RAPID PROTOTYPING PLAYBOOK",
        "accent": "#4F46E5",
        "title": "Domain Adaptation Playbook: 4 Scenarios (`A`–`D`) & `5-File Swap`",
        "subtitle": "Keep the 4 core engine files untouched and swap only 5 domain data/rule slots to build a new industry prototype in half a day",
        "banner_img": None,
        "cards": [
            {
                "tag": "IMMUTABLE CORE (DO NOT REWRITE)",
                "title": "4 Core Engine Modules",
                "accent": "#DC2626",
                "bullets": [
                    "src/gcp_client.py: BigQuery SQL/GQL runner, GCS uploader, Vertex AI client",
                    "src/agent/reasoning_engine.py: 2-Pass reasoning loop & 4 guardrail state transitions",
                    "src/web/studio_server.py & terraform/*.tf: 6-Tab Studio UI and declarative IaC"
                ]
            },
            {
                "tag": "5-FILE SWAP (DOMAIN SLOTS)",
                "title": "5 Files Modified per New Domain",
                "accent": "#1A73E8",
                "bullets": [
                    "① config/starter_config.json (active_track: lite | standard | full)",
                    "② data/input/* (01_guides/*.md, 03_tables/*.csv, 04_cq/*.json)",
                    "③ pipeline/ingest.py  ④ pipeline/graph_builder.py  ⑤ mcp_server.py + portal_profile.json"
                ]
            },
            {
                "tag": "4 SCENARIOS (A – D)",
                "title": "Scenario Selection by Data Readiness",
                "accent": "#0F9D58",
                "bullets": [
                    "Scenario A (Lite): Policy docs & formulas only → Stages 1·2·4 (4 files swapped)",
                    "Scenario B (Standard): DW tables + Policy docs → BigQuery Property Graph (5 files)",
                    "Scenario C (Spanner): Add OLTP Spanner DDL / Scenario D (Full): 50-run Eval + Release"
                ]
            }
        ],
        "table": {
            "headers": ["Swap Step", "Target File Path", "What to Customize for Your Domain", "Verification Command"],
            "rows": [
                ["Swap ①", "config/starter_config.json", "Set active_track ('lite' | 'standard' | 'full'), graph_engine, and graph_name", "cat config/starter_config.json"],
                ["Swap ②", "data/input/{01_guides,03_tables,04_cq}/", "Replace policy Markdown guides, master/contract CSVs, and Golden CQ / Boundary JSONs", "ls -la data/input/*"],
                ["Swap ③", "pipeline/ingest.py", "Update table load list, DOMAIN_RULES metadata, and 3-Layer Wiki summary templates", "python3 pipeline/ingest.py"],
                ["Swap ④", "pipeline/graph_builder.py", "Map VERTEX TABLES and EDGE TABLES inside CREATE OR REPLACE PROPERTY GRAPH", "python3 pipeline/graph_builder.py"],
                ["Swap ⑤", "src/agent/mcp_server.py · config/portal_profile.json", "Update Runtime MCP SQL/GQL formulas and Studio UI profile / sample queries", "python3 pipeline/validator.py"]
            ]
        },
        "takeaway": "5-File Swap Principle: Never rebuild the Studio UI or 2-Pass agent loop from scratch — swap only the 5 domain slots defined in PROTOTYPING_PLAYBOOK.md.",
        "speaker_notes": (
            "[Instructor Guide — Slide 16: Rapid Prototyping Playbook & 5-File Swap]\n"
            "• Review `PROTOTYPING_PLAYBOOK.md` and explain the strict separation between the Immutable Core Engine and the 5 Domain Swap Slots.\n"
            "• This architecture allows Customer Engineers and Solution Architects to build a live customer PoC in 30 minutes to half a day."
        )
    },
    {
        "slide_no": 17,
        "badge": "MODULE 07 · AI CODING AGENT BOOTSTRAP",
        "accent": "#1A73E8",
        "title": "AI Coding Agent (`Antigravity` · `Cursor` · `Claude Code`) 3-Step Prompt Guide",
        "subtitle": "Pre-bundled guardrail files and copy-paste prompt sequence that prevent coding agents from inventing mock SQLite databases or breaking the UI",
        "banner_img": None,
        "cards": [
            {
                "tag": "GUARDRAIL BUNDLE",
                "title": "6 Auto-Loaded Agent Rule Files",
                "accent": "#1A73E8",
                "bullets": [
                    "01_prod.md: Master specification with 6 immutable architectural principles & 5-File Swap map",
                    "GEMINI.md (Antigravity/Jetski) · CLAUDE.md (Claude Code) · .cursorrules (Cursor)",
                    "AGENTS.md (Cross-tool instructions) · DESIGN.md (Apple/Google Enterprise light theme tokens)"
                ]
            },
            {
                "tag": "3-STEP WORKFLOW",
                "title": "3-Step Progressive Execution Strategy",
                "accent": "#0F9D58",
                "bullets": [
                    "Step 1 (Environment & IaC): Verify GCP ADC auth, set up .venv, run Terraform for BQ & GCS",
                    "Step 2 (Data Ingestion): Place domain guides/CSVs in data/input/ and run pipeline/ingest.py",
                    "Step 3 (Ontology & Studio): Run graph_builder.py, bind MCP SQL/GQL, run validator.py & Studio"
                ]
            },
            {
                "tag": "ANTI-DRIFT GUARDRAILS",
                "title": "3 Prohibited Agent Actions",
                "accent": "#DC2626",
                "bullets": [
                    "1) Never replace live BigQuery/GCS calls with local SQLite or in-memory mock dictionaries",
                    "2) Never rewrite the 6-Tab Studio layout (studio_server.py) or switch to random dark themes",
                    "3) Never hardcode Gemini API keys (AIza...) in source files — always use GCP ADC"
                ]
            }
        ],
        "table": {
            "headers": ["Prompt Step", "Target Objective", "Standard Prompt Template for Antigravity / Cursor / Claude Code", "Completion Check"],
            "rows": [
                ["Step 1", "GCP Setup & Provisioning", "Read @01_prod.md @GEMINI.md first. Configure GCP_PROJECT_ID, BQ_DATASET_ID, GCS_WIKI_BUCKET, install .venv, and provision the 10 BigQuery tables and GCS bucket via Terraform.", "gcloud auth verified · 10 BQ tables created"],
                ["Step 2", "Data Ingestion & 3-Layer Wiki", "Following @01_prod.md @PROTOTYPING_PLAYBOOK.md, load my domain guides and CSVs in data/input/ via pipeline/ingest.py into BigQuery and compile the 3-Layer OKF Wiki.", "gcs_prototype_manifest.json (LIVE_GCP_SYNCED)"],
                ["Step 3", "Property Graph & Studio Launch", "Run pipeline/graph_builder.py to deploy STARTER_ONTOLOGY_GRAPH, wire mcp_server.py, run pipeline/validator.py, and start the Studio server on port 8080.", "GQL paths > 0 · Golden CQ 100% · HTTP 200"],
                ["One-Shot Swap", "Scenario A–D Domain Adaptation", "Read @01_prod.md @GEMINI.md @PROTOTYPING_PLAYBOOK.md and execute the 5-File Swap for [Scenario B: Track 2 Standard] targeting [Your Domain].", "Only 5 files modified · Core engine intact"]
            ]
        },
        "takeaway": "Prompting Best Practice: Always start your coding agent prompt with `@01_prod.md @GEMINI.md @PROTOTYPING_PLAYBOOK.md` so architectural guardrails load into context first.",
        "speaker_notes": (
            "[Instructor Guide — Slide 17: AI Coding Agent Bootstrap Workflow]\n"
            "• Show learners where the copy-paste prompts live in the main `README.md` (§1) and `PROTOTYPING_PLAYBOOK.md`.\n"
            "• Explain how the 6 guardrail files (`01_prod.md`, `GEMINI.md`, `CLAUDE.md`, `.cursorrules`, `AGENTS.md`, `DESIGN.md`) keep autonomous coding agents aligned."
        )
    },
    {
        "slide_no": 18,
        "badge": "MODULE 08 · INDUSTRY ARCHETYPES & WRAP-UP",
        "accent": "#0F9D58",
        "title": "4 Industry Sectors × 8 Enterprise Reference Templates (`industry_cases/`) & Wrap-Up",
        "subtitle": "Ready-to-use de-identified ontology templates across Manufacturing, Finance, Retail/Commerce, and Telecommunications",
        "banner_img": None,
        "cards": [
            {
                "tag": "MANUFACTURING & FINANCE",
                "title": "Smart Manufacturing (2) & Fintech/Banking (2)",
                "accent": "#1A73E8",
                "bullets": [
                    "Mfg A: Smart Steel Mill continuous-process vibration (4.5mm/s) interlock SOP & bearing inventory",
                    "Mfg B: Global Automotive SDV controller firmware compatibility & ISO 26262 ASIL-D supply chain",
                    "Finance A: Digital Bank unattended mortgage stress DSR 40% & first-home LTV 80% underwriting",
                    "Finance B: Super-App Fintech MyData multi-lender refinancing & merchant fee tier settlement"
                ]
            },
            {
                "tag": "RETAIL & TELECOM",
                "title": "Retail/Logistics (2) & Telecom/Media (2)",
                "accent": "#0F9D58",
                "bullets": [
                    "Retail A: Convenience Franchise fresh-food (FF) 40% waste subsidy & quick-commerce stock",
                    "Retail B: Omnichannel Health & Beauty 3-hour delivery SLA compensation & 50% promo cap",
                    "Telecom A: Mobile 5G subscription bundle, 180-day prorated subsidy clawback & senior exemption",
                    "Telecom B: Wired/Wireless internet+TV bundle retention & enterprise dedicated line 99.9% SLA"
                ]
            },
            {
                "tag": "COURSE TAKEAWAYS",
                "title": "Methodology Summary & Licensing",
                "accent": "#4F46E5",
                "bullets": [
                    "1) CQ-First Scoping (Stage 1) → 2) SHA-256 Chunks & 3-Layer Wiki (Stage 2)",
                    "3) Zero-ETL Property Graph (Stage 3) → 4) 8 MCPs & 2-Pass Agent (Stage 4) → 5) 50-Run Gate (Stage 5)",
                    "Non-Commercial Dual License (CC BY-NC-ND 4.0 / PolyForm Noncommercial) · Contact: seanjung@google.com"
                ]
            }
        ],
        "table": {
            "headers": ["Industry Folder (`industry_cases/`)", "De-identified Enterprise Archetypes", "Core Property Graph Nodes × Edges", "Deterministic MCP Formula Example"],
            "rows": [
                ["01_manufacturing/", "Smart Steel Mill Co. A · Global Automaker Co. B", "Equipment · Sensor · BearingInventory · SafetySOP (APPLIES_INTERLOCK)", "Vibration >= 4.5mm/s triggers immediate speed interlock & spare line cost calculation"],
                ["02_finance/", "Digital Bank Co. A · Super-App Fintech Co. B", "LoanApplicant · CreditLoan · MortgageRule · FSSRegulation (GOVERNED_BY)", "Annual debt service / annual income <= 40% DSR cap with stress rate adder"],
                ["03_retail_commerce/", "National Franchise Co. A · Omnichannel Retail Co. B", "FranchiseStore · FreshSKU · PromoContract · FairTradeRule (SUBSIDIZES)", "Fresh-food waste cost × 40% HQ subsidy & Fair Trade 50% promotional share cap"],
                ["04_telecommunications/", "Mobile Carrier Co. A · Converged Carrier Co. B", "CustomerContract · Device · Plan · Subsidy · DomainRule (APPLIES_TO_PLAN)", "180-day prorated penalty, senior exemption (0 KRW), 24M TCO, and B2B SLA credit"]
            ]
        },
        "takeaway": "Fastest Starting Point: Pick the closest template from industry_cases/ (complete with SQL DDL, CSVs, policy Markdown, and CQs) and apply the 5-File Swap.",
        "speaker_notes": (
            "[Instructor Guide — Slide 18: 8 Enterprise Industry Archetypes & Course Wrap-Up]\n"
            "• Walk through the 4 industry folders under `industry_cases/` (`01_manufacturing`, `02_finance`, `03_retail_commerce`, `04_telecommunications`).\n"
            "• Remind participants that every template includes ready-to-run BigQuery DDL, sample CSV rows, policy Markdown clauses, and Competency Questions.\n"
            "• Conclude the training session and remind participants to reach out to seanjung@google.com for commercial licensing or enterprise deployment inquiries."
        )
    }
]
