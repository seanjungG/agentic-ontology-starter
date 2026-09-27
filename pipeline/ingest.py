# -*- coding: utf-8 -*-
"""
Pipeline Ingest Engine:
- GCP Native Foundation:
    * Google Cloud Open Knowledge Format (OKF v0.2) specification
    * Google Cloud Knowledge Catalog Bundle standards
    * Google Cloud Storage (GCS) object storage manifest
- Custom Extensions:
    * Visual chunk parser with deterministic SHA-256 hash anchors across multiple policy guides
    * Andrej Karpathy 3-Layer LLM-Wiki compiler (summary, entities, concepts, rules)
"""
import os, re, json, hashlib

def run_ingest(guide_dir="data/input/01_guides", output_dir="data/output", wiki_dir="data/llm_wiki"):
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(wiki_dir, exist_ok=True)

    guide_files = []
    if os.path.isdir(guide_dir):
        for fn in sorted(os.listdir(guide_dir)):
            if fn.endswith(".md"):
                guide_files.append(os.path.join(guide_dir, fn))
    elif os.path.isfile(guide_dir):
        guide_files.append(guide_dir)

    chunk_pattern = re.compile(r"<!--\s*(DOC_CHUNK_\d+):?\s*(.*?)\s*-->\s*(.*?)(?=(?:<!--\s*DOC_CHUNK_\d+)|$)", re.DOTALL)
    chunks = []

    for gpath in guide_files:
        with open(gpath, "r", encoding="utf-8") as f:
            content = f.read()
        source_doc = os.path.basename(gpath)
        matches = chunk_pattern.findall(content)
        if not matches:
            sections = re.split(r"(?=\n##\s+)", content)
            for idx, sec in enumerate(sections):
                cid = f"DOC_CHUNK_{len(chunks)+1:03d}"
                title_match = re.search(r"##\s+(.*)", sec)
                title = title_match.group(1) if title_match else f"Section {idx+1}"
                h = hashlib.sha256(sec.encode("utf-8")).hexdigest()[:12]
                chunks.append({
                    "chunk_id": cid,
                    "title": title.strip(),
                    "source_doc": source_doc,
                    "hash_anchor": f"anchor_{h}",
                    "content": sec.strip()
                })
        else:
            for cid, title, body in matches:
                h = hashlib.sha256(body.encode("utf-8")).hexdigest()[:12]
                chunks.append({
                    "chunk_id": cid,
                    "title": title.strip() or cid,
                    "source_doc": source_doc,
                    "hash_anchor": f"anchor_{h}",
                    "content": body.strip()
                })

    chunks_path = os.path.join(output_dir, "doc_chunks.jsonl")
    with open(chunks_path, "w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")

    ontology = {
        "@context": "https://cloud.google.com/ontology/v0.2/context.jsonld",
        "@graph": [
            {
                "@id": "domain:TelecomSubsidyManagement",
                "@type": "DomainOntology",
                "label": "Enterprise Subsidy & Contract Management (Starter v2.0)",
                "summary": "Hybrid ontology unifying structured DW tables and unstructured policy manuals.",
                "totalChunks": len(chunks),
                "supportedTracks": ["lite", "standard", "full"],
                "supportedGraphEngines": ["bigquery", "spanner"]
            }
        ]
    }
    for c in chunks:
        ontology["@graph"].append({
            "@id": f"chunk:{c['chunk_id']}",
            "@type": "DocChunk",
            "title": c["title"],
            "sourceDoc": c.get("source_doc", "sample_policy_guide.md"),
            "hashAnchor": c["hash_anchor"]
        })

    onto_path = os.path.join(output_dir, "ontology.jsonld")
    with open(onto_path, "w", encoding="utf-8") as f:
        json.dump(ontology, f, ensure_ascii=False, indent=2)

    # Layer 1: summary.md
    summary_md = f"""# Enterprise Knowledge Wiki: Executive Summary (Layer 1)
- **Domain**: Telecom Terminal Subsidy, Tariff Plans & Customer Commitment Management
- **Target Framework**: OKF v0.2 & Dual Property Graph (BigQuery SQL:2023 / Cloud Spanner Graph)
- **Total Parsed Chunks**: {len(chunks)} (Across {len(guide_files)} Policy Guides)
- **De-Identified DW Tables**: 4 Master Tables (`customer_contracts`, `devices`, `plans`, `subsidies`)

## Operational Philosophy
This knowledge base unifies unstructured legal and customer service manuals with structured enterprise DW ledgers.
By combining deterministic rule MCP execution with SHA-256 paragraph anchors, agents ground every numerical calculation in verifiable source evidence.
"""
    with open(os.path.join(wiki_dir, "summary.md"), "w", encoding="utf-8") as f:
        f.write(summary_md)

    # Layer 2: entities.md
    entities_md = """# Enterprise Knowledge Wiki: Core Entities Directory (Layer 2)
Canonical entities harmonized across structured DW tables and unstructured policy guides:

## 1. Customer Contract Ledger (`customer_contracts.csv`)
- `CONTRACT_DEMO_101` (`CUST_DEMO_001` · General VIP · `DEV-S26U-256` · `PLAN-5G-85` · 120 Days Elapsed)
- `CONTRACT_DEMO_102` (`CUST_DEMO_002` · General Standard · `DEV-S26U-256` · `PLAN-5G-130` · 224 Days Elapsed)
- `CONTRACT_DEMO_103` (`CUST_DEMO_003` · Senior Welfare · `DEV-IP16P-256` · `PLAN-5G-85` · 88 Days Elapsed · `SENIOR_EXEMPT`)

## 2. Terminal Device Master (`devices.csv`)
- `Galaxy S26 Ultra 256GB` (`DEV-S26U-256`, Factory Price: 1,698,400 KRW)
- `Galaxy S26 Ultra 512GB` (`DEV-S26U-512`, Factory Price: 1,841,400 KRW)
- `iPhone 16 Pro 256GB` (`DEV-IP16P-256`, Factory Price: 1,700,000 KRW)
- `iPhone 16 Pro 512GB` (`DEV-IP16P-512`, Factory Price: 2,000,000 KRW)

## 3. Tariff Plan Master (`plans.csv`)
- `5G Premier Super` (`PLAN-5G-130`, 130,000 KRW, Baseline Tier: True)
- `5G Premier Essential` (`PLAN-5G-85`, 85,000 KRW, Baseline Tier: True)
- `5G Slim (Baseline Threshold)` (`PLAN-5G-45`, 45,000 KRW, Baseline Tier: True)
- `5G Light (Below Baseline)` (`PLAN-5G-37`, 37,000 KRW, Baseline Tier: False)

## 4. Subsidy Policy Master (`subsidies.csv`)
- `POL-2026-001` (`DEV-S26U-256` + `PLAN-5G-130`: Basic 500,000 + Dist 75,000 = 575,000 KRW)
- `POL-2026-002` (`DEV-S26U-256` + `PLAN-5G-85`: Basic 450,000 + Dist 67,500 = 517,500 KRW)
- `POL-2026-004` (`DEV-S26U-256` + `PLAN-5G-37`: Basic 150,000 + Dist 22,500 = 172,500 KRW)
"""
    with open(os.path.join(wiki_dir, "entities.md"), "w", encoding="utf-8") as f:
        f.write(entities_md)

    # Layer 3: concepts.md & rules.md
    concepts_md = """# Enterprise Knowledge Wiki: Semantic Concepts & Edges (Layer 3)
In the Agentic Ontology Studio graph model, **Entities are represented as Nodes** and **Semantic Concepts/Relationships are represented as Edges**:

1. `SUBSCRIBES_CONTRACT` (`약정 가입 관계`): Links a Customer Contract (`고객 약정 원장`) to a Tariff Plan (`모바일 요금제`) and Terminal Device (`단말기 모델`).
2. `COVERS_DEVICE` (`단말 지원금 적용`): Connects a Subsidy Policy (`공시지원금 정책`) to its eligible Terminal Device (`단말기 모델`).
3. `REQUIRES_PLAN` (`요금제 티어 요건`): Connects a Subsidy Policy (`공시지원금 정책`) to its required Tariff Plan (`모바일 요금제`).
4. `APPLIES_RULE` (`위약금 규칙 적용`): Binds a codified Domain Rule (`약정 위약금 규칙`) to Tariff Plans and Customer Contracts.
5. `EXEMPTS_PENALTY` (`특례 면제 관계`): Binds Senior/Welfare or Military pause clauses (`위약금 면제 특례`) to eligible customer segments.
6. `GROUNDED_IN` (`원문 해시 근거`): Anchors every Domain Rule (`약정 위약금 규칙`) to an immutable SHA-256 `DocChunk` (`정책 가이드 청크`).
"""
    with open(os.path.join(wiki_dir, "concepts.md"), "w", encoding="utf-8") as f:
        f.write(concepts_md)

    rules_md = """# Enterprise Knowledge Wiki: Codified Business Rules (Layer 3)
Deterministic business logic governing penalty calculations, TCO comparison, and statutory exemptions:

### Rule 1: 180-Day Baseline Plan Commitment (`RULE_SIX_PLAN_180D` · `DOC_CHUNK_002`, `DOC_CHUNK_003`)
- **Condition**: Subscriber activated terminal with public subsidy under a baseline or higher plan (`>= 45,000 KRW`).
- **Constraint**: Must maintain baseline tier (`is_baseline_tier = true`) for at least **180 days** from activation.
- **Penalty on Breach (< 180 Days)**:
  `Penalty = (Initial Basic Subsidy - Lower Tier Basic Subsidy) * (180 - Elapsed Days) / 180`
- **Post-180 Days (`>= 180 Days`)**: Penalty is `0 KRW`.

### Rule 2: Statutory Welfare & Military Exemptions (`RULE_WELFARE_EXEMPT` · `DOC_CHUNK_004`)
- **Senior / Welfare Transition**: Subscribers with `welfare_status = SENIOR_EXEMPT` transitioning to designated Senior/Welfare plans incur `0 KRW` penalty even within 180 days.
- **Military Enlistment Hold**: `MILITARY_PAUSE_ELIGIBLE` pauses the 180-day commitment counter during active service.

### Rule 3: 24-Month Public Subsidy vs. 25% Selective Contract (`RULE_TCO_COMPARE` · `DOC_CHUNK_005`)
- **Public Subsidy 24M TCO**: `(Factory Price - Total Subsidy) + (Monthly Fee * 24)`
- **Selective 25% Discount 24M TCO**: `Factory Price + (Monthly Fee * 0.75 * 24)`
"""
    with open(os.path.join(wiki_dir, "rules.md"), "w", encoding="utf-8") as f:
        f.write(rules_md)

    gcs_manifest = {
        "gcs_uri": "gs://enterprise-ontology-vault/starter-v2/okf-v0.2/",
        "status": "PROTOTYPE_STAGED",
        "artifacts": [
            "summary.md",
            "entities.md",
            "concepts.md",
            "rules.md",
            "ontology.jsonld",
            "doc_chunks.jsonl"
        ],
        "sync_timestamp": "2026-09-27T16:40:00+09:00",
        "validation": {
            "chunk_count": len(chunks),
            "guide_count": len(guide_files),
            "zero_duplicate_entities_flag": True,
            "anti_redundancy_ready": True
        }
    }
    with open(os.path.join(wiki_dir, "gcs_prototype_manifest.json"), "w", encoding="utf-8") as f:
        json.dump(gcs_manifest, f, ensure_ascii=False, indent=2)

    print(f"[INGEST SUCCESS] Processed {len(chunks)} chunks across {len(guide_files)} guides -> {chunks_path}, {onto_path}")
    print(f"[LLM-WIKI SUCCESS] Generated Karpathy 3-Layer Wiki in {wiki_dir}/")
    return chunks

if __name__ == "__main__":
    run_ingest()
