# Copyright (c) 2026 Sean Jung (seanjung@google.com). All Rights Reserved.
# Non-Commercial Use Only: Methodology & Docs under CC BY-NC-ND 4.0; Source Code under PolyForm Noncommercial License 1.0.0.
# Commercial use, paid consulting/SI/PoC delivery, or production deployment requires prior written permission from seanjung@google.com.

# -*- coding: utf-8 -*-
"""
Document-based LLM-Wiki (track=lite): chunks -> ontology/entities.md (nodes) + ontology/concepts.md (edges).

- entity  = business unit named in the documents (actor, activity, object, document ...)
- concept = pre-condition / post-condition / constraint that holds between two entities
Gemini proposes items; code keeps only items whose quote (<= wiki_extraction.max_quote_chars) appears verbatim in
their source chunk (whitespace ignored: PDF text layers break words at line ends), and concepts whose two entities were kept. provenance = EXTRACTED. No physical graph is loaded.

    python3 -m pipeline.extract_wiki --project <id>
"""
import argparse
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_ROOT = os.environ.get("STARTER_PROJECT_ROOT", BASE_DIR)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from pipeline.extract_docs import nonws  # noqa: E402
from src.gcp_client import DEFAULT_GCS_BUCKET, DEFAULT_GEMINI_MODEL, call_vertex_gemini, upload_gcs_object  # noqa: E402

BATCH_CHARS = 12000  # chunk text per Gemini call (the client times out after 45 s)
KINDS = ("PRECONDITION", "POSTCONDITION", "CONSTRAINT")
SYS = """문서 청크에서 온톨로지 위키 항목을 뽑습니다. JSON 한 개만 출력하십시오.
{"entities": [{"name": str, "description": str, "source_chunk_id": str, "quote": str}],
 "concepts": [{"kind": "PRECONDITION"|"POSTCONDITION"|"CONSTRAINT", "from": str, "to": str, "statement": str,
               "source_chunk_id": str, "quote": str}]}
규칙:
- entity: 문서에서 관리·수행되는 업무 단위(주체, 행위, 대상, 서류 등). name은 문서의 용어를 그대로 씀.
- concept: 두 entity 사이의 사전조건·사후조건·제약조건. from/to는 entities의 name과 정확히 같아야 함.
- quote: source_chunk_id 청크 원문에서 줄바꿈 없이 그대로 복사한 구절, {max_quote}자 이하. 바꿔 쓰거나 요약하지 말 것.
- 청크에 없는 내용은 쓰지 말 것."""


def _config(key: str):
    with open(os.path.join(BASE_DIR, "config/starter_config.json"), "r", encoding="utf-8") as f:
        return json.load(f)["wiki_extraction"][key]


def _batches(chunks):
    out, cur = [], []
    for c in chunks:
        if cur and sum(len(x["content"]) for x in cur) + len(c["content"]) > BATCH_CHARS:
            out.append(cur)
            cur = []
        cur.append(c)
    return out + ([cur] if cur else [])


def extract_wiki(root: str = None, sync_gcp: bool = True, bucket: str = None) -> dict:
    root, bucket = root or DATA_ROOT, bucket or DEFAULT_GCS_BUCKET
    from src.project_context import project_for_root, resolve_track
    track, _, _ = resolve_track(project_for_root(root))
    if track != "lite":  # table tracks keep the table-derived wiki written by pipeline/ingest.py
        raise SystemExit(f"[WIKI] track={track}: document-based wiki extraction runs on track=lite only.")
    with open(os.path.join(root, "data/output/doc_chunks.jsonl"), "r", encoding="utf-8") as f:
        chunks = {c["chunk_id"]: c for c in (json.loads(x) for x in f if x.strip())}
    max_quote = _config("max_quote_chars")
    system = SYS.replace("{max_quote}", str(max_quote))

    def call(batch):
        text = "\n\n".join(f"[{c['chunk_id']}]\n{c['content']}" for c in batch)
        return call_vertex_gemini(prompt=f"[문서 청크]\n{text}", system_instruction=system,
                                  response_mime_type="application/json", temperature=0.0, max_tokens=8192)

    batches = _batches(list(chunks.values()))
    with ThreadPoolExecutor(4) as ex:
        results = list(ex.map(call, batches))
    failed = [i for i, r in enumerate(results) if r.get("status") != "SUCCESS"]
    if failed:
        raise SystemExit(f"[WIKI] Gemini failed for batch(es) {failed}: {str(results[failed[0]].get('error', ''))[:300]}")

    def ok(item):  # verbatim quote from its own chunk (whitespace ignored, as in Gate 0), within the length limit
        c, q = chunks.get(item.get("source_chunk_id")), (item.get("quote") or "").strip()
        return bool(c and q and len(q) <= max_quote and nonws(q) in nonws(c["content"]))

    entities, concepts, dropped, parse_errors = {}, [], {"entities": 0, "concepts": 0}, 0
    for r in results:
        try:
            data = json.loads(r["text"])
        except (ValueError, TypeError):
            parse_errors += 1
            continue
        for e in data.get("entities") or []:
            if not ok(e) or not (e.get("name") or "").strip():
                dropped["entities"] += 1
                continue
            entities.setdefault(e["name"].strip(), e)
        for c in data.get("concepts") or []:
            if not ok(c) or c.get("kind") not in KINDS:
                dropped["concepts"] += 1
                continue
            concepts.append(c)
    kept = [c for c in concepts if c["from"].strip() in entities and c["to"].strip() in entities]
    dropped["concepts"] += len(concepts) - len(kept)
    ids = {n: f"E{i + 1:03d}" for i, n in enumerate(entities)}

    def cite(x):
        c = chunks[x["source_chunk_id"]]
        return f"`{x['source_chunk_id']}` ({c.get('source_original') or c['source_doc']} p.{c.get('page_from')}) \"{x['quote'].strip()}\""

    entities_md = ["# Knowledge Wiki: Entities (nodes, from documents)",
                   f"Extracted by `pipeline/extract_wiki.py` with Vertex AI `{DEFAULT_GEMINI_MODEL}` · provenance `EXTRACTED` · "
                   f"{len(entities)} nodes · each quote found in its chunk (whitespace ignored).", ""]
    entities_md += [f"- **{ids[n]}** {n} — {(e.get('description') or '').strip()}  \n  source: {cite(e)}" for n, e in entities.items()]
    concepts_md = ["# Knowledge Wiki: Concepts (edges, from documents)",
                   f"Pre-conditions, post-conditions and constraints between entities · Vertex AI `{DEFAULT_GEMINI_MODEL}` · "
                   f"provenance `EXTRACTED` · {len(kept)} edges.", ""]
    concepts_md += [f"- **{ids[c['from'].strip()]} -[{c['kind']}]-> {ids[c['to'].strip()]}** ({c['from'].strip()} → {c['to'].strip()}) "
                    f"{(c.get('statement') or '').strip()}  \n  source: {cite(c)}" for c in kept]
    wiki_dir = os.path.join(root, "data/llm_wiki")
    os.makedirs(wiki_dir, exist_ok=True)
    files = {"entities.md": "\n".join(entities_md) + "\n", "concepts.md": "\n".join(concepts_md) + "\n"}
    for fn, body in files.items():
        with open(os.path.join(wiki_dir, fn), "w", encoding="utf-8") as f:
            f.write(body)
    report = {
        "extractor": "pipeline/extract_wiki.py", "model": DEFAULT_GEMINI_MODEL, "provenance": "EXTRACTED",
        "chunks": len(chunks), "gemini_calls": len(batches), "parse_errors": parse_errors,
        "prompt_tokens": sum(r.get("prompt_tokens") or 0 for r in results),
        "candidates_tokens": sum(r.get("candidates_tokens") or 0 for r in results),
        "entities": len(entities), "concepts": len(kept), "dropped": dropped,
        "nodes": [{"id": ids[n], "name": n, "source_chunk_id": e["source_chunk_id"], "quote": e["quote"].strip()} for n, e in entities.items()],
        "edges": [{"from": ids[c["from"].strip()], "to": ids[c["to"].strip()], "kind": c["kind"], "statement": c.get("statement"),
                   "source_chunk_id": c["source_chunk_id"], "quote": c["quote"].strip()} for c in kept],
    }
    with open(os.path.join(root, "data/output/wiki_extraction.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    if sync_gcp:
        for fn, body in files.items():
            upload_gcs_object(f"ontology/{fn}", body.encode("utf-8"), bucket=bucket,
                              content_type="text/markdown; charset=utf-8")
    print(f"[WIKI] {len(entities)} entities · {len(kept)} concepts · dropped {dropped} · parse errors {parse_errors} · "
          f"{len(batches)} Gemini calls ({DEFAULT_GEMINI_MODEL}) -> data/llm_wiki/entities.md, concepts.md")
    return report


def main():
    from src.project_context import get_project
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", help="project id (default: sample or env STARTER_PROJECT)")
    p = get_project(ap.parse_args().project)
    extract_wiki(p["root"], bucket=(p.get("gcp") or {}).get("gcs_bucket"))


if __name__ == "__main__":
    main()
