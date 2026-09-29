# Copyright (c) 2026 Sean Jung (seanjung@google.com). All Rights Reserved.
# Non-Commercial Use Only: Methodology & Docs under CC BY-NC-ND 4.0; Source Code under PolyForm Noncommercial License 1.0.0.
# Commercial use, paid consulting/SI/PoC delivery, or production deployment requires prior written permission from seanjung@google.com.

# -*- coding: utf-8 -*-
"""
Stage 5 Validator (live GCP). No fixed results: every number in the reports comes from execution.
- Golden CQ: independent verification SQL (BigQuery) vs golden expected_math, and the live agent
  answer (Vertex AI Gemini + BigQuery MCP) must contain the expected values and the grounded chunk.
- Boundary: each boundary question runs N times; success / consistency / intent stability are measured.
"""
import json
import os
import re
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_ROOT = os.environ.get("STARTER_PROJECT_ROOT", BASE_DIR)  # project data root (run_pipeline.py --project)
sys.path.insert(0, BASE_DIR)
from src.agent.reasoning_engine import AiFdeAgentEngine  # noqa: E402
from src.gcp_client import execute_bq_sql  # noqa: E402

CQ_PATH = os.path.join(DATA_ROOT, "data/input/04_cq/golden_competency_questions.json")
BOUNDARY_PATH = os.path.join(DATA_ROOT, "data/input/04_cq/boundary_cases.json")
OUT_DIR = os.path.join(DATA_ROOT, "data/output")
FOOTER = "\n\n---\n- LLM:"  # telemetry footer appended by the engine (excluded from checks)


def _now() -> str:
    return datetime.now(timezone(timedelta(hours=9))).isoformat(timespec="seconds")


def _has(text: str, v) -> bool:
    """String: substring. Number: exact number match (1,698,400 or 1698400); 0 must carry a unit."""
    if isinstance(v, str):
        return v in text
    v = int(v)
    if v == 0:
        return re.search(r"(?<![\d.])(?<!\d,)0\s*(원|KRW|건|개)", text) is not None
    return re.search(rf"(?<![\d.])(?<!\d,)({v:,}|{v})(?!\d|,\d)", text) is not None


def _agent(engine: AiFdeAgentEngine, query: str) -> dict:
    t0 = time.perf_counter()
    try:
        res = engine.execute_cycle(query)
    except Exception as e:  # network / auth failure is recorded as a failed trial
        return {"error": repr(e)[:500], "body": "", "answer_status": "EXCEPTION", "tools": [], "jobs": [],
                "tokens": 0, "elapsed_s": round(time.perf_counter() - t0, 2)}
    lt = res["llm_telemetry"]
    return {"body": res["lifecycle"]["step_4_synthesis"]["markdown"].split(FOOTER)[0],
            "answer_status": res["answer_status"],
            "tools": list(res["bq_telemetry"]["tool_statuses"].keys()),
            "tool_statuses": res["bq_telemetry"]["tool_statuses"],
            "jobs": res["bq_telemetry"]["job_ids"],
            "tokens": (lt.get("prompt_tokens") or 0) + (lt.get("candidates_tokens") or 0),
            "elapsed_s": round(time.perf_counter() - t0, 2)}


def _sql(sql: str, fq: str) -> dict:
    r = execute_bq_sql(sql.replace("{fq}", fq))
    return {"status": r.get("status"), "job_id": r.get("job_id"), "rows": r.get("rows", []),
            "error": str(r.get("error", ""))[:500] or None}


PROVENANCE = ("CUSTOMER_PROVIDED", "EXTRACTED", "SYNTHETIC_DEMO")


def _input_errors(root: str, sample: bool) -> list:
    """F6: every row of data/input/03_tables/*.csv needs provenance + source_ref; SYNTHETIC_DEMO rows need
    project.json synthetic.allowed=true (set only with user approval). F10: a customer project must not contain
    files identical to the bundled sample or industry_cases."""
    import csv
    import glob
    from pipeline.extract_docs import sha256_file
    meta_path = os.path.join(root, "config/project.json" if sample else "project.json")
    meta = {}
    if os.path.exists(meta_path):
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
    synth_ok = (meta.get("synthetic") or {}).get("allowed") is True
    errors = []
    for path in sorted(glob.glob(os.path.join(root, "data/input/03_tables/*.csv"))):
        with open(path, "r", encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
        bad = [i for i, r in enumerate(rows, 2) if r.get("provenance") not in PROVENANCE or not (r.get("source_ref") or "").strip()]
        synth = [i for i, r in enumerate(rows, 2) if r.get("provenance") == "SYNTHETIC_DEMO"] if not synth_ok else []
        name = os.path.relpath(path, root)
        if bad:
            errors.append(f"{name}: {len(bad)} row(s) without provenance {PROVENANCE} or source_ref (first line {bad[0]})")
        if synth:
            errors.append(f"{name}: {len(synth)} SYNTHETIC_DEMO row(s) but project.json synthetic.allowed is not true "
                          f"(first line {synth[0]}); synthetic data needs user approval")
    if not sample:
        ref = {}
        for d in ("data/input", "industry_cases"):
            for f in glob.glob(os.path.join(BASE_DIR, d, "**/*"), recursive=True):
                if os.path.isfile(f) and os.path.getsize(f):
                    ref[sha256_file(f)] = os.path.relpath(f, BASE_DIR)
        for d in ("data/input", "customer_doc"):
            for f in sorted(glob.glob(os.path.join(root, d, "**/*"), recursive=True)):
                if os.path.isfile(f) and os.path.getsize(f) and sha256_file(f) in ref:
                    errors.append(f"{os.path.relpath(f, root)}: same content as starter file {ref[sha256_file(f)]} "
                                  "(sample / industry_cases data must not be loaded as customer data)")
    return errors


def run_gate0(chunks: list, root: str = None) -> dict:
    """Gate 0 (before any load): chunks vs. the customer originals, per document. File checks only (no LLM / GCP).
    In a customer project every 01_guides/*.md must be written by pipeline/extract_docs.py and unchanged since.
    Also table provenance and sample isolation (_input_errors)."""
    from pipeline.extract_docs import ARTICLE_RE, DOC_DIR, GUIDE_DIR, MANIFEST, nonws, read_pages, sha256_bytes, sha256_file
    root = root or DATA_ROOT
    with open(os.path.join(BASE_DIR, "config/starter_config.json"), "r", encoding="utf-8") as f:
        th = json.load(f)["gates"]["gate0"]
    n, gdir, man_path = th["ngram_len"], os.path.join(root, GUIDE_DIR), os.path.join(root, MANIFEST)
    manifest = {"documents": []}
    if os.path.exists(man_path):
        with open(man_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
    by_md = {os.path.basename(d["md_file"]): d for d in manifest["documents"]}
    guides = sorted(g for g in os.listdir(gdir) if g.endswith(".md")) if os.path.isdir(gdir) else []
    sample = os.path.abspath(root) == BASE_DIR
    docs, legacy, errors = [], [], [f"needs_ocr: {d}" for d in manifest.get("needs_ocr", [])]
    errors += [f"{m}: listed in {MANIFEST} but missing in {GUIDE_DIR}" for m in by_md if m not in guides]
    errors += _input_errors(root, sample)
    for g in guides:
        with open(os.path.join(gdir, g), "rb") as f:
            raw_md = f.read()
        d = by_md.get(g)
        if d is None or not raw_md.startswith(b"<!-- source_doc:"):
            if sample:
                legacy.append(g)
            else:
                errors.append(f"{g}: not written by pipeline/extract_docs.py (put the original in {DOC_DIR}/ and run it)")
            continue
        if sha256_bytes(raw_md) != d["md_sha256"]:
            errors.append(f"{g}: changed after extraction (SHA-256 differs from {MANIFEST})")
            continue
        orig = os.path.join(root, DOC_DIR, d["source_doc"])
        if not os.path.exists(orig) or sha256_file(orig) != d["source_sha256"]:
            errors.append(f"{g}: original {DOC_DIR}/{d['source_doc']} missing or changed; re-run extract_docs.py")
            continue
        pages = read_pages(orig)
        o = nonws("".join(pages))
        mine = [c for c in chunks if c["source_doc"] == g]
        c = nonws("".join(x["content"] for x in mine))
        grams = {c[i:i + n] for i in range(len(c) - n + 1)}
        pieces = [o[i:i + n] for i in range(0, len(o) - n + 1, n)]
        text_pages = {i + 1 for i, t in enumerate(pages) if t.strip()}
        covered = {p for x in mine for p in range(x["page_from"], x["page_to"] + 1)}
        articles = {m.group(1) for t in pages for ln in t.split("\n") if (m := ARTICLE_RE.match(ln.strip()))}
        r = {"source_doc": d["source_doc"], "guide": g, "pages": len(pages), "chunks": len(mine),
             "chars_original": len(o), "chars_chunks": len(c),
             "char_ratio": round(len(c) / len(o), 4) if o else 1.0,
             "ngram_coverage": round(sum(p in grams for p in pieces) / len(pieces), 4) if pieces else 1.0,
             "page_coverage": round(len(text_pages & covered) / len(text_pages), 4) if text_pages else 1.0,
             "pages_missing": sorted(text_pages - covered),
             "articles": len(articles), "articles_missing": sorted(articles - {x["article_no"] for x in mine})}
        r["status"] = "PASS" if (r["char_ratio"] >= th["min_char_ratio"] and r["ngram_coverage"] >= th["min_ngram_coverage"]
                                 and r["page_coverage"] >= th["min_page_coverage"]
                                 and len(r["articles_missing"]) <= th["max_missing_articles"]) else "FAIL"
        docs.append(r)
    report = {"gate": "GATE_0", "evaluated_at": _now(),
              "status": "PASS" if not errors and all(r["status"] == "PASS" for r in docs) else "FAIL",
              "thresholds": {k: v for k, v in th.items() if not k.startswith("_")},
              "documents": docs, "legacy_sample_guides": legacy, "errors": errors}
    os.makedirs(os.path.join(root, "data/output"), exist_ok=True)
    with open(os.path.join(root, "data/output/gate0_report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    for r in docs:
        print(f"[GATE 0] {r['status']} {r['source_doc']} · chars {r['char_ratio']:.1%} · 12-char {r['ngram_coverage']:.1%} · "
              f"pages {r['page_coverage']:.0%} · chunks {r['chunks']} · articles missing {len(r['articles_missing'])}")
    for e in errors:
        print(f"[GATE 0] FAIL {e}")
    print(f"[GATE 0] {report['status']} ({len(docs)} documents, {len(legacy)} sample guides) -> data/output/gate0_report.json")
    return report


ID_RE = re.compile(r"\b[A-Z][A-Z0-9]*(?:[-_][A-Z0-9]+)+\b")  # ID-like strings, e.g. CUST_DEMO_001, PLAN-5G-85
QUOTED_RE = re.compile(r"[\"“'‘「『]([^\"”'’」』]{2,60})[\"”'’」』]")
CHUNK_ID_RE = re.compile(r"DOC_CHUNK_\d{3,}")


def _project_meta(root: str) -> dict:
    path = os.path.join(root, "config/project.json" if os.path.abspath(root) == BASE_DIR else "project.json")
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _table_rows(root: str) -> list:
    import csv
    import glob
    rows = []
    for path in sorted(glob.glob(os.path.join(root, "data/input/03_tables/*.csv"))):
        with open(path, "r", encoding="utf-8", newline="") as f:
            rows += list(csv.DictReader(f))
    return rows


def load_cqs(root: str = None) -> list:
    """Gate 1 (F7), file checks only. Each CQ is evidence_type "sql" (verification_sql + expected_math over loaded
    tables) or "citation" (expected_citation {chunk_id, quote} + expected_facts, all verbatim in that chunk).
    ID-like strings and quoted names in the question must exist in the chunks or tables. sql CQs over
    SYNTHETIC_DEMO rows need project.json synthetic.allowed. Any rejected CQ stops the evaluation."""
    root = root or DATA_ROOT
    with open(os.path.join(root, "data/input/04_cq/golden_competency_questions.json"), "r", encoding="utf-8") as f:
        cqs = json.load(f)
    chunk_path = os.path.join(root, "data/output/doc_chunks.jsonl")
    chunks = {}
    if os.path.exists(chunk_path):
        with open(chunk_path, "r", encoding="utf-8") as f:
            chunks = {c["chunk_id"]: c for c in (json.loads(x) for x in f if x.strip())}
    rows = _table_rows(root)
    corpus = "\n".join(c["content"] for c in chunks.values()) + "\n" + "\n".join(str(v) for r in rows for v in r.values())
    table_prov = sorted({r.get("provenance") for r in rows})
    synth_ok = (_project_meta(root).get("synthetic") or {}).get("allowed") is True
    rejected = []
    for cq in cqs:
        why, et = [], cq.get("evidence_type")
        names = ID_RE.findall(cq["query"]) + QUOTED_RE.findall(cq["query"])
        why += [f"'{n}' is not in the chunks or tables" for n in names if n not in corpus]
        if et == "sql":
            if not rows:
                why.append("sql CQ but no table is loaded")
            elif "SYNTHETIC_DEMO" in table_prov and not synth_ok:
                why.append("sql CQ over SYNTHETIC_DEMO rows without synthetic.allowed")
            why += [f"missing {k}" for k in ("verification_sql", "expected_math") if not cq.get(k)]
            cq["_evidence_provenance"] = table_prov
        elif et == "citation":
            ec, facts = cq.get("expected_citation") or {}, cq.get("expected_facts") or []
            ch = chunks.get(ec.get("chunk_id"))
            if not ch:
                why.append(f"expected_citation.chunk_id {ec.get('chunk_id')} not in doc_chunks.jsonl")
            else:
                why += [f"'{t}' is not verbatim in {ch['chunk_id']}" for t in [ec.get("quote") or ""] + facts if not t or t not in ch["content"]]
                cq["_evidence_provenance"] = [ch.get("provenance")]
        else:
            why.append('evidence_type must be "sql" or "citation"')
        if why:
            rejected.append({"cq_id": cq.get("cq_id"), "reasons": why})
    if rejected:
        for r in rejected:
            print(f"[GATE 1] REJECT {r['cq_id']}: {'; '.join(r['reasons'])}")
        raise SystemExit(f"[GATE 1] {len(rejected)} CQ(s) rejected. Fix data/input/04_cq/golden_competency_questions.json.")
    return cqs


def run_validation(workers: int = 5) -> dict:
    import hashlib
    import uuid
    cqs = load_cqs()
    engine = AiFdeAgentEngine()
    fq = engine.server.fq

    def cite(cq):
        ec, facts = cq["expected_citation"], cq["expected_facts"]
        a = _agent(engine, cq["query"])
        cited = sorted(set(CHUNK_ID_RE.findall(a["body"])))
        found = {t: t in a["body"] for t in facts}
        reasons = ([] if ec["chunk_id"] in cited else [f"ANCHOR_NOT_CITED {ec['chunk_id']}"]) + \
                  [f"ANSWER_MISSING {t}" for t, ok in found.items() if not ok] + \
                  ([] if a["answer_status"] == "GROUNDED" else [f"ANSWER_STATUS {a['answer_status']}"])
        return {
            "cq_id": cq["cq_id"], "category": cq.get("category"), "query": cq["query"], "prompt": cq["query"],
            "expected_value": " · ".join(facts), "expected_citation": ec, "verification_sql_result": {},
            "verification_job_id": None,
            "actual_value": " · ".join(f"{t} {'포함' if ok else '누락'}" for t, ok in found.items())
                            + f" · cited {', '.join(cited) or '-'} · {a['answer_status']}",
            "grounded_chunk": ec["chunk_id"], "legal_anchor": ec["chunk_id"],
            "status": "PASSED" if not reasons else "FAILED",
            "verification_status": "CITATION_MATCH·ANSWER_MATCH" if not reasons else "; ".join(reasons),
            "dispatched_tools": a["tools"], "agent_bq_job_ids": a["jobs"], "llm_tokens": a["tokens"],
            "elapsed_s": a["elapsed_s"], "answer_excerpt": a["body"][:600], "error": a.get("error"),
        }

    def one(cq):
        row = cite(cq) if cq["evidence_type"] == "citation" else sql_one(cq)
        row.update(evidence_type=cq["evidence_type"], evidence_provenance=cq["_evidence_provenance"],
                   answer_confirmed_by=cq.get("answer_confirmed_by"), confirmed_at=cq.get("confirmed_at"),
                   answer_confirmed=bool(cq.get("answer_confirmed_by")), executed_at=_now())
        return row

    def sql_one(cq):
        exp = cq["expected_math"]
        v = _sql(cq["verification_sql"], fq)
        row = v["rows"][0] if v["rows"] else {}
        sql_ok = v["status"] == "SUCCESS" and all(k in row and row[k] == x for k, x in exp.items())
        a = _agent(engine, cq["query"])
        found = {k: _has(a["body"], x) for k, x in exp.items()}
        anchor_ok = cq["grounded_chunk"] in a["body"]
        reasons = ([] if sql_ok else [f"SQL_MISMATCH {row}"]) + \
                  [f"ANSWER_MISSING {k}={exp[k]}" for k, ok in found.items() if not ok] + \
                  ([] if anchor_ok else [f"ANCHOR_NOT_CITED {cq['grounded_chunk']}"]) + \
                  ([] if a["answer_status"] == "GROUNDED" else [f"ANSWER_STATUS {a['answer_status']}"])
        return {
            "cq_id": cq["cq_id"], "category": cq["category"], "query": cq["query"], "prompt": cq["query"],
            "expected_value": cq["expected_value"], "expected_math": exp,
            "verification_sql_result": row, "verification_job_id": v["job_id"],
            "actual_value": " · ".join(f"{k} {'포함' if ok else '누락'}" for k, ok in found.items())
                            + f" · {cq['grounded_chunk']} {'인용' if anchor_ok else '미인용'} · {a['answer_status']}",
            "grounded_chunk": cq["grounded_chunk"], "legal_anchor": cq["grounded_chunk"],
            "status": "PASSED" if not reasons else "FAILED",
            "verification_status": "SQL_MATCH·ANSWER_MATCH" if not reasons else "; ".join(reasons),
            "dispatched_tools": a["tools"], "agent_bq_job_ids": a["jobs"], "llm_tokens": a["tokens"],
            "elapsed_s": a["elapsed_s"], "answer_excerpt": a["body"][:600], "error": a.get("error"),
        }

    with ThreadPoolExecutor(workers) as ex:
        rows = list(ex.map(one, cqs))
    passed = sum(r["status"] == "PASSED" for r in rows)
    man_path = os.path.join(DATA_ROOT, "data/output/input_manifest.json")
    man_sha = None
    if os.path.exists(man_path):
        with open(man_path, "rb") as f:
            man_sha = hashlib.sha256(f.read()).hexdigest()
    prov = sorted({p for r in rows for p in r["evidence_provenance"] if p})
    report = {
        "benchmark_id": "STARTER_GOLDEN_CQ_LIVE", "evaluated_at": _now(),
        "run_id": f"{datetime.now(timezone(timedelta(hours=9))).strftime('%Y%m%dT%H%M%S')}-{uuid.uuid4().hex[:8]}",
        "input_manifest_sha256": man_sha, "track": "lite" if getattr(engine, "is_lite", lambda: False)() else "table",
        "evidence_provenance": prov, "synthetic_basis": "SYNTHETIC_DEMO" in prov,
        "unconfirmed_cqs": sum(not r["answer_confirmed"] for r in rows),
        "method": f"sql CQ: verification_sql(BigQuery) vs expected_math + live agent answer; citation CQ: agent answer "
                  f"must cite expected chunk and contain expected_facts (Vertex AI {engine.model_name})",
        "model": engine.model_name, "dataset": fq,
        "total_cqs": len(rows), "passed": passed, "accuracy_rate": round(passed / len(rows) * 100, 1) if rows else None,
        "llm_tokens_total": sum(r["llm_tokens"] for r in rows),
        "evaluation_details": rows, "test_results": rows,
    }
    path = os.path.join(OUT_DIR, "cq_benchmark_report.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"[VALIDATOR] Golden CQ {passed}/{len(rows)} passed -> {path}")
    return report


def _check(case: dict, a: dict) -> list:
    body, reasons = a["body"], []
    if a.get("error"):
        return [f"EXCEPTION {a['error'][:120]}"]
    if case.get("accept_answer_status") and a["answer_status"] not in case["accept_answer_status"]:
        reasons.append(f"ANSWER_STATUS {a['answer_status']}")
    if case.get("answer_terms_any") and not any(t in body for t in case["answer_terms_any"]):
        reasons.append(f"TERMS_MISSING {case['answer_terms_any']}")
    reasons += [f"ANSWER_MISSING {v}" for v in case.get("answer_numbers_all", []) if not _has(body, v)]
    vals = case.get("_sql_values") or []
    if vals:
        hits = [v for v in vals if _has(body, v)]
        if (case.get("sql_values_match") == "all" and len(hits) < len(vals)) or not hits:
            reasons.append(f"SQL_VALUES_MISSING {sorted(set(vals) - set(hits))}")
    return reasons


def run_boundary(trials: int = 5, workers: int = 5) -> dict:
    engine = AiFdeAgentEngine()
    fq = engine.server.fq
    with open(BOUNDARY_PATH, "r", encoding="utf-8") as f:
        cases = json.load(f)
    for c in cases:
        if c.get("verification_sql"):
            v = _sql(c["verification_sql"], fq)
            c["_sql_job_id"] = v["job_id"]
            c["_sql_values"] = [x for r in v["rows"] for x in r.values() if x is not None]
    work = [(c, t) for c in cases for t in range(trials)]
    with ThreadPoolExecutor(workers) as ex:
        results = list(ex.map(lambda ct: (ct[0]["case_id"], _agent(engine, ct[0]["query"])), work))

    out = []
    for c in cases:
        runs = [a for cid, a in results if cid == c["case_id"]]
        checks = [_check(c, a) for a in runs]
        ok = [not r for r in checks]
        sig = Counter((a["answer_status"], o) for a, o in zip(runs, ok))
        intents = Counter(tuple(a["tools"]) for a in runs)
        out.append({
            "case_id": c["case_id"], "query": c["query"], "missing_context": c["missing_context"],
            "root_cause_code": c["root_cause_code"], "expected_behavior": c["expected_behavior"],
            "trials": len(runs), "passed_trials": sum(ok),
            "success_rate": round(sum(ok) / len(runs) * 100, 1),
            "consistency_rate": round(sig.most_common(1)[0][1] / len(runs) * 100, 1),
            "intent_stability": round(intents.most_common(1)[0][1] / len(runs) * 100, 1),
            "answer_statuses": dict(Counter(a["answer_status"] for a in runs)),
            "tool_sets": {" > ".join(k): n for k, n in intents.items()},
            "failure_reasons": sorted({x for r in checks for x in r}),
            "verification_sql_values": c.get("_sql_values"), "verification_job_id": c.get("_sql_job_id"),
            "sample_answer": runs[0]["body"][:600] if runs else "",
            "sample_bq_job_ids": runs[0]["jobs"] if runs else [],
        })
    avg = lambda k: round(sum(x[k] for x in out) / len(out), 1) if out else None  # noqa: E731
    report = {
        "benchmark_id": "STARTER_BOUNDARY_LIVE", "evaluated_at": _now(),
        "method": f"live agent (Vertex AI {engine.model_name} + BigQuery MCP) x {trials} trials per case; "
                  "checks from data/input/04_cq/boundary_cases.json",
        "model": engine.model_name, "dataset": fq,
        "case_count": len(out), "trials_per_case": trials, "total_trials": len(results),
        "avg_success_rate": avg("success_rate"), "avg_consistency_rate": avg("consistency_rate"),
        "avg_intent_stability": avg("intent_stability"),
        "llm_tokens_total": sum(a["tokens"] for _, a in results),
        "cases": out,
    }
    path = os.path.join(OUT_DIR, "boundary_benchmark_results.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"[VALIDATOR] Boundary success {report['avg_success_rate']}% · consistency {report['avg_consistency_rate']}% "
          f"· intent {report['avg_intent_stability']}% ({len(results)} trials) -> {path}")
    return report


if __name__ == "__main__":
    run_validation()
    run_boundary()
