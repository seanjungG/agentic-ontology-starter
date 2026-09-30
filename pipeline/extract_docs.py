# Copyright (c) 2026 Sean Jung (seanjung@google.com). All Rights Reserved.
# Non-Commercial Use Only: Methodology & Docs under CC BY-NC-ND 4.0; Source Code under PolyForm Noncommercial License 1.0.0.
# Commercial use, paid consulting/SI/PoC delivery, or production deployment requires prior written permission from seanjung@google.com.

# -*- coding: utf-8 -*-
"""
Stage 1 original-text conversion (code only, no LLM).

    python3 pipeline/extract_docs.py --project <id>

`projects/<id>/customer_doc/*` -> `data/input/01_guides/<name>.md`
- PDF: pypdf text per page, `<!-- page: N -->` before each page. DOCX: python-docx paragraphs and table cells.
  MD / TXT: copied unchanged.
- Allowed cleanup (PDF / DOCX only): whitespace normalization and removal of repeated page headers / footers
  (the count is reported). Nothing is summarized or rewritten.
- A page without a text layer stops the run (`needs_ocr`).
- `data/output/input_manifest.json` records the SHA-256 of each original and of the written file. It has no
  timestamps, so re-runs give identical bytes. Gate 0 (`pipeline/validator.py`) checks chunks against the originals.
"""
import argparse
import hashlib
import json
import os
import re
import sys
from collections import Counter

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

DOC_DIR = "customer_doc"
GUIDE_DIR = "data/input/01_guides"
MANIFEST = "data/output/input_manifest.json"
SUPPORTED = (".pdf", ".docx", ".md", ".txt")
REPEAT_MIN_PAGES = 3    # header / footer detection needs at least this many pages
REPEAT_MIN_SHARE = 0.5  # a first / last line (digits ignored) on at least half of the pages is a header / footer
ARTICLE_RE = re.compile(r"^(제\d+조(?:의\d+)?)\s*\(")  # article heading at line start, e.g. "제15조(표시)"


def nonws(s: str) -> str:
    return re.sub(r"\s+", "", s)


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(path: str) -> str:
    with open(path, "rb") as f:
        return sha256_bytes(f.read())


def read_pages(path: str) -> list:
    """Original text per page, as extracted (before any cleanup)."""
    ext = os.path.splitext(path)[1].lower()
    if ext == ".pdf":
        from pypdf import PdfReader
        return [p.extract_text() or "" for p in PdfReader(path).pages]
    if ext == ".docx":
        import docx
        d = docx.Document(path)
        return ["\n".join([p.text for p in d.paragraphs] + [c.text for t in d.tables for r in t.rows for c in r.cells])]
    with open(path, "r", encoding="utf-8") as f:
        return [f.read()]


def _normalize(text: str) -> str:
    lines = [re.sub(r"[ \t\u00a0\u3000]+", " ", ln).strip() for ln in re.split(r"\r\n|\r|\n", text)]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def _strip_repeats(pages: list) -> tuple:
    if len(pages) < REPEAT_MIN_PAGES:
        return pages, 0
    key = lambda ln: re.sub(r"\d+", "#", ln)  # noqa: E731  page numbers differ per page
    removed = 0
    for pos in (0, -1):
        split = [p.split("\n") for p in pages]
        counts = Counter(key(ls[pos]) for ls in split if ls and ls[pos])
        repeated = {k for k, n in counts.items() if n >= REPEAT_MIN_SHARE * len(pages)}
        for ls in split:
            if ls and ls[pos] and key(ls[pos]) in repeated:
                ls.pop(pos)
                removed += 1
        pages = ["\n".join(ls) for ls in split]
    return pages, removed


DEFAULT_ENGINE_CHECKLIST = {
    "source_system": "bigquery_dw",
    "latency_slo": "seconds_ok",
    "concurrency": "analytical_qps",
    "write_freshness": "batch_or_hourly",
    "data_scale": "tb_to_pb",
}


def _engine_manifest_fields(root: str) -> dict:
    meta_path = os.path.join(root, "config/project.json" if os.path.abspath(root) == BASE_DIR else "project.json")
    meta = {}
    if os.path.exists(meta_path):
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
    raw_cl = meta.get("graph_engine_checklist") or {}
    checklist = {k: raw_cl.get(k) or v for k, v in DEFAULT_ENGINE_CHECKLIST.items()}
    return {
        "graph_engine": meta.get("graph_engine") or "bigquery",
        "graph_engine_reason": meta.get("graph_engine_reason") or "",
        "graph_engine_checklist": checklist,
    }


def extract_project(root: str, track: dict = None) -> dict:
    """track: {"track", "track_reason"} from src.project_context.resolve_track, recorded in the manifest."""
    src_dir, out_dir = os.path.join(root, DOC_DIR), os.path.join(root, GUIDE_DIR)
    files = sorted(f for f in os.listdir(src_dir) if f.lower().endswith(SUPPORTED)) if os.path.isdir(src_dir) else []
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(os.path.join(root, "data/output"), exist_ok=True)
    docs, needs_ocr = [], []
    for fn in files:
        path, ext = os.path.join(src_dir, fn), os.path.splitext(fn)[1].lower()
        raw = read_pages(path)
        empty = [i + 1 for i, t in enumerate(raw) if not t.strip()]
        if empty:
            needs_ocr.append({"source_doc": fn, "pages_without_text": empty})
            continue
        pages, removed = _strip_repeats([_normalize(t) for t in raw]) if ext in (".pdf", ".docx") else (raw, 0)
        md_name = os.path.splitext(fn)[0] + ".md"
        if any(os.path.basename(d["md_file"]) == md_name for d in docs):
            sys.exit(f"Two originals map to {md_name}; rename one in {DOC_DIR}/.")
        src_sha = sha256_file(path)
        text = (f"<!-- source_doc: {fn} -->\n<!-- source_sha256: {src_sha} -->\n<!-- pages: {len(pages)} -->\n\n"
                + "\n\n".join(f"<!-- page: {i + 1} -->\n{t}" for i, t in enumerate(pages)) + "\n")
        with open(os.path.join(out_dir, md_name), "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        docs.append({"source_doc": fn, "source_sha256": src_sha, "format": ext[1:], "pages": len(pages),
                     "md_file": f"{GUIDE_DIR}/{md_name}", "md_sha256": sha256_bytes(text.encode("utf-8")),
                     "chars_original": len(nonws("".join(raw))), "chars_written": len(nonws("".join(pages))),
                     "removed_header_footer_lines": removed})
    manifest = {"extractor": "pipeline/extract_docs.py", "status": "NEEDS_OCR" if needs_ocr else "OK",
                **(track or {}), **_engine_manifest_fields(root), "documents": docs, "needs_ocr": needs_ocr}
    with open(os.path.join(root, MANIFEST), "w", encoding="utf-8", newline="\n") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return manifest


def main():
    from src.project_context import get_project, resolve_track
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", help="project id (default: sample or env STARTER_PROJECT)")
    p = get_project(ap.parse_args().project)
    track, _, reason = resolve_track(p)
    m = extract_project(p["root"], {"track": track, "track_reason": reason})
    for d in m["documents"]:
        print(f"[EXTRACT] {d['source_doc']} -> {d['md_file']} · {d['pages']} pages · "
              f"{d['chars_written']:,}/{d['chars_original']:,} chars · header/footer lines removed {d['removed_header_footer_lines']}")
    for d in m["needs_ocr"]:
        print(f"[NEEDS_OCR] {d['source_doc']} pages without text: {d['pages_without_text']} (OCR is not part of the starter)")
    print(f"[EXTRACT] {len(m['documents'])} documents -> {p['root_dir']}/{MANIFEST}")
    if m["needs_ocr"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
