# -*- coding: utf-8 -*-
"""
Pipeline Ingest Engine:
Parses unstructured policy guides, generates deterministic SHA-256 hash anchors,
and compiles Open Knowledge Format (OKF v0.2) ontology artifacts.
"""
import os, re, json, hashlib

def run_ingest(guide_path="data/input/01_guides/sample_policy_guide.md", output_dir="data/output"):
    os.makedirs(output_dir, exist_ok=True)
    with open(guide_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Split by chunks
    chunk_pattern = re.compile(r"<!--\s*(DOC_CHUNK_\d+):?\s*(.*?)\s*-->\s*(.*?)(?=(?:<!--\s*DOC_CHUNK_\d+)|$)", re.DOTALL)
    matches = chunk_pattern.findall(content)

    chunks = []
    if not matches:
        # Fallback to section headers
        sections = re.split(r"(?=\n##\s+)", content)
        for idx, sec in enumerate(sections):
            cid = f"DOC_CHUNK_{idx+1:03d}"
            title_match = re.search(r"##\s+(.*)", sec)
            title = title_match.group(1) if title_match else f"Section {idx+1}"
            h = hashlib.sha256(sec.encode("utf-8")).hexdigest()[:12]
            chunks.append({
                "chunk_id": cid,
                "title": title.strip(),
                "hash_anchor": f"anchor_{h}",
                "content": sec.strip()
            })
    else:
        for cid, title, body in matches:
            h = hashlib.sha256(body.encode("utf-8")).hexdigest()[:12]
            chunks.append({
                "chunk_id": cid,
                "title": title.strip() or cid,
                "hash_anchor": f"anchor_{h}",
                "content": body.strip()
            })

    # Write doc_chunks.jsonl
    chunks_path = os.path.join(output_dir, "doc_chunks.jsonl")
    with open(chunks_path, "w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")

    # Build OKF v0.2 ontology.jsonld
    ontology = {
        "@context": "https://cloud.google.com/ontology/v0.2/context.jsonld",
        "@graph": [
            {
                "@id": "domain:TelecomSubsidyManagement",
                "@type": "DomainOntology",
                "label": "Enterprise Subsidy & Contract Management",
                "summary": "Hybrid ontology unifying structured pricing tables and unstructured penalty rules.",
                "totalChunks": len(chunks)
            }
        ]
    }
    for c in chunks:
        ontology["@graph"].append({
            "@id": f"chunk:{c['chunk_id']}",
            "@type": "DocChunk",
            "title": c["title"],
            "hashAnchor": c["hash_anchor"]
        })

    onto_path = os.path.join(output_dir, "ontology.jsonld")
    with open(onto_path, "w", encoding="utf-8") as f:
        json.dump(ontology, f, ensure_ascii=False, indent=2)

    print(f"[INGEST SUCCESS] Processed {len(chunks)} chunks -> {chunks_path}, {onto_path}")
    return chunks

if __name__ == "__main__":
    run_ingest()
