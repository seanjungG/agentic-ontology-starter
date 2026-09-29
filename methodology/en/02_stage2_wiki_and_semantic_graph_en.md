# Stage 2. OKF Wiki and Semantic Modeling

> Studio [`Stage 2. Wiki & Semantic Graph`](https://agentic-ontology-starter-924723860007.asia-northeast3.run.app/?tab=stage2) · MCP `mcp_stage2_wiki_and_semantic` · Notebook [stage2_wiki_and_semantic_graph_en.ipynb](../../notebooks/en/stage2_wiki_and_semantic_graph_en.ipynb) · [Korean (KO)](../ko/02_stage2_wiki_and_semantic_graph_ko.md) · [Full methodology](./METHODOLOGY_EN.md)

## Purpose

Split the unstructured guides into evidence units (chunks) and give each chunk an anchor that stays the same as long as the text does not change.
Turn the rules in the documents into table rows and link them to structured data (plans). This stage makes it possible to trace which paragraph an agent answer is based on.

## Inputs

| Path | Content |
| :--- | :--- |
| `data/input/01_guides/*.md` | 2 guides, 5 chunks |
| `data/input/03_tables/domain_rules.csv` | 4 rules (`RULE_SUBSIDY_CAP`, `RULE_SIX_PLAN_180D`, `RULE_WELFARE_EXEMPT`, `RULE_TCO_24M`). `source_chunk_id` points to the evidence chunk |
| `data/input/03_tables/rule_plan_edges.csv` | 12 rule-to-plan links, with a Korean relation label (`relation_label_ko`) and `source_chunk_id` |
| 4 master CSV files (Stage 1) | Source of Wiki L2 (entities) |

## MCP of this Stage: `mcp_stage2_wiki_and_semantic`

| Step | What the code does (`src/agent/mcp_server.py`) |
| :--- | :--- |
| `compile_3layer_wiki` | Only lists the GCS bucket objects → `gcs_objects`. The Wiki itself is built by `run_ingest()` |
| `extract_hash_anchors` | Reads the anchors (`content_sha256`) from `tb_doc_chunks`. Anchors are created by `run_ingest()` |
| `bind_semantic_bridges` | Joins `tb_doc_chunks` and `tb_domain_rules` on `source_chunk_id` → `anchored_chunks` |

The `steps` argument is recorded in `executed_steps` of the result. The current handler runs the join query and the GCS listing regardless of the selected steps.

## Procedure (`run_ingest()` in `pipeline/ingest.py`)

1. **Chunking**: split each guide at the `DOC_CHUNK_*` comments and build an anchor from the first 12 hex characters of the text's SHA-256 (`anchor_` + 12 characters) → `data/output/doc_chunks.jsonl`. If the text changes, the anchor changes.
2. **Ontology file**: write one domain node and the chunk nodes as JSON-LD → `data/output/ontology.jsonld`.
3. **3-Layer Wiki**: build 4 Markdown files from the same chunks and CSV rows → `data/llm_wiki/`.

   | File | Layer | Source |
   | :--- | :--- | :--- |
   | `summary.md` | L1 summary | Number of chunks, guides and tables |
   | `entities.md` | L2 entities | The 4 master CSV files |
   | `concepts.md` | L3 relations | 4 relations defined in `pipeline/ingest.py` (`USES_DEVICE`, `SUBSCRIBES_PLAN`, `HAS_SUBSIDY_POLICY`, `APPLIES_TO_PLAN`) |
   | `rules.md` | L3 rules | `domain_rules.csv` |

4. **Load and upload**: chunks go to `tb_doc_chunks`, rules to `tb_domain_rules`, rule-to-plan links to `edge_rule_applies_to_plan`. The raw guides (`raw/`), chunks (`parsed/`), Wiki and JSON-LD (`ontology/`) are uploaded to GCS. The result is recorded in `data/llm_wiki/gcs_prototype_manifest.json`.
5. **Semantic graph**: the studio graph draws `vis_semantic_graph` (11 nodes, 13 edges) from `data/output/graph_topology.json`. That file is written by `build_graph()` in Stage 3, and its nodes and labels are defined in `pipeline/graph_builder.py`. The rule is entity = node, relation (concept) = edge.

### Lite track: document-based Wiki (projects without customer tables)

1. **Chunks**: the source `01_guides/*.md` files written by `extract_docs.py` are split by article (lines that start with a statute article heading, pattern `ARTICLE_RE` in `pipeline/extract_docs.py`) or by heading and paragraph (max 1,500 characters). Each chunk records `source_doc`, `source_sha256`, `page_from`, `page_to`, `article_no`, `origin_type`, `extract_method`, and `source_locator`; `trust_tier` is `EXTRACTED`.
2. **Wiki extraction**: `pipeline/extract_wiki.py` extracts entities (main business units) as nodes and concepts (pre-conditions, post-conditions and constraints between entities) as edges (`-[PRECONDITION|POSTCONDITION|CONSTRAINT]->`) from the chunks. It uses Gemini and records the model name.
3. **Quote check**: every item carries a `source_chunk_id` and a quote of at most 300 characters. Items whose quote is not in the chunk (whitespace differences ignored) are dropped, and the drop counts are written to `data/output/wiki_extraction.json`.
4. **Result**: `data/llm_wiki/entities.md` and `concepts.md` are uploaded to GCS `ontology/`. No physical graph is loaded (Stage 3 is skipped). Item counts can vary between runs with the same input because Gemini output varies.

#### Conversion Output Samples (`doc_chunks.jsonl`, `entities.md`, `concepts.md`, `wiki_extraction.json`)

**1) `data/output/doc_chunks.jsonl` (with 5-Column Provenance Metadata)**
```json
{"chunk_id": "DOC_CHUNK_001", "doc_name": "01_telecom_terms.md", "section_title": "Article 18 (Subsidy Clawback and Exemptions)", "chunk_text": "Article 18 (Subsidy Clawback and Exemptions) 1. If a subscriber lowers the rate plan before 180 days of mandatory retention, a prorated penalty is charged...", "content_sha256": "anchor_9c8b7a6d5e4f", "origin_type": "EXTRACTED", "source_doc": "customer_doc/telecom_service_terms.pdf", "source_sha256": "8f9d2a1c4b...", "extract_method": "pypdf_article_split", "source_locator": "page=1#article=18"}
```

**2) `03_wiki/entities.md` (L2 Entity Nodes)**
```markdown
# L2 Entities (Extracted Business Entities — Node Candidates)

## ENT_SUBSIDY_PENALTY — Public Subsidy Clawback Penalty
- **Entity Type**: `PolicyRuleEntity`
- **Role in Graph**: `Node`
- **Source Chunk ID**: `DOC_CHUNK_001` (`anchor_9c8b7a6d5e4f`)
- **Verbatim Quote (<=300 chars)**: "If a subscriber lowers the rate plan before 180 days of mandatory retention, a prorated penalty is charged on the subsidy difference."
```

**3) `03_wiki/concepts.md` (L3 Concept Relations / Edges)**
```markdown
# L3 Concepts & Relations (Edge Candidates)

## REL_001: `ENT_WELFARE_SENIOR` -[EXEMPTS]-> `ENT_SUBSIDY_PENALTY`
- **Relation Type**: `CONSTRAINT`
- **Source Node**: `ENT_WELFARE_SENIOR` (Senior Welfare Subscriber >= 65)
- **Target Node**: `ENT_SUBSIDY_PENALTY` (Public Subsidy Clawback Penalty)
- **Condition / Formula**: `age >= 65 OR welfare_status = 'SENIOR_EXEMPT' => penalty = 0`
- **Source Chunk ID**: `DOC_CHUNK_001` (`anchor_9c8b7a6d5e4f`)
- **Verbatim Quote (<=300 chars)**: "Subscribers aged 65 or older (SENIOR_EXEMPT) or enlisting for mandatory military service are exempt from the clawback penalty (0 KRW)."
```

**4) `data/output/wiki_extraction.json` (Quote Verification & Hallucination Drop Audit)**
```json
{
  "project_id": "my_project",
  "extracted_at": "2026-09-29T12:01:15+09:00",
  "model": "gemini-3.8-flash",
  "chunks_processed": 18,
  "entities_extracted": 9,
  "entities_dropped_unverified_quote": 0,
  "concepts_extracted": 11,
  "concepts_dropped_unverified_quote": 1,
  "status": "VERIFIED"
}
```

## Deliverables

| ID | Deliverable | In the starter |
| :--- | :--- | :--- |
| `D2.1` | OKF v0.2 domain ontology specification | `data/output/ontology.jsonld` (domain node + chunk nodes) |
| `D2.2` | Karpathy 3-Layer LLM-Wiki directory | `data/llm_wiki/summary.md`, `entities.md`, `concepts.md`, `rules.md` |
| `D2.3` | GCS ontology prototype registry | `data/llm_wiki/gcs_prototype_manifest.json`, GCS `raw/` · `parsed/` · `ontology/` |
| `D2.4` | Unstructured text chunk and hash anchor manifest | `data/output/doc_chunks.jsonl`, BigQuery `tb_doc_chunks` |
| `D2.5` | Deterministic business rule registry | `domain_rules.csv` → BigQuery `tb_domain_rules` |
| `D2.6` | Semantic bridge mapping matrix | `rule_plan_edges.csv` → BigQuery `edge_rule_applies_to_plan` |

## Gate (Gate 2)

- [ ] Every chunk has an anchor and no two anchors are the same.
- [ ] Every `tb_domain_rules.source_chunk_id` exists in `tb_doc_chunks`. Check the chunks with attached rules in `anchored_chunks` of the Stage 2 MCP result.
- [ ] The manifest `status` is `LIVE_GCP_SYNCED` and `validation.bigquery_tables_loaded` is 10.
- [ ] On the Lite track, passing this gate moves the work to Stage 4.

## View in the studio

[Open the Stage 2. Wiki & Semantic Graph tab](https://agentic-ontology-starter-924723860007.asia-northeast3.run.app/?tab=stage2)

- Left: Wiki viewer (`L1 Summary`, `L2 Entities`, `L3 Concepts`, `L3 Rules`, `Chunks`).
- Right: semantic graph. Clicking a node shows its relations and the evidence chunk description.
- Stage 2 MCP button (top right): runs the MCP above.

## Notebook

[stage2_wiki_and_semantic_graph_en.ipynb](../../notebooks/en/stage2_wiki_and_semantic_graph_en.ipynb)

## Apply to your data

1. **Chunk boundaries**: for customer documents, code sets the chunk boundaries (articles, headings and paragraphs of the `extract_docs.py` output). `<!-- DOC_CHUNK_NNN: Title -->` comments are for the sample only; do not add them to customer documents.
2. **Rules**: write rules in `domain_rules.csv` by quoting the source clause, and put the evidence chunk ID in `source_chunk_id`. The SQL in `src/agent/mcp_server.py` refers to the 4 rule IDs by name, so update that SQL if you change the IDs.
3. **Rule-to-table links**: link each rule to the `plan_id` values it applies to in `rule_plan_edges.csv`.
4. **Graph view**: to change the nodes and labels of the semantic graph, edit `vis_semantic_graph` in `pipeline/graph_builder.py`. The relation text of the Wiki is in the `concepts.md` part of `pipeline/ingest.py`.
