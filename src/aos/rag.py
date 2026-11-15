# Copyright (c) 2026 Sean Jung (seanjung@google.com). All Rights Reserved.
# Non-Commercial Use Only: Methodology & Docs under CC BY-NC-ND 4.0; Source Code under PolyForm Noncommercial License 1.0.0.
# Commercial use, paid consulting/SI/PoC delivery, or production deployment requires prior written permission from seanjung@google.com.

# -*- coding: utf-8 -*-
"""RAG baseline + three-stage comparison for a workspace (GOAL-296).

"Why build an ontology when RAG works?" is the first question every customer asks. These two stages answer it with the
workspace's own data instead of an argument:

    rag      the SAME parsed documents and tables as the wiki / graph → retrieval units → Vertex AI RAG Engine corpus
             (Core MCP aos_core_rag_decompose · aos_core_rag_create_corpus · aos_core_rag_import_files)
    compare  every CQ through three systems — RAG agent (aos_core_rag_answer), Wiki agent, Graph agent (hybrid: wiki +
             semantic graph) — graded by ONE system-blind 100-point judge (aos_core_eval_rubric_judge) and tabulated by
             aos_core_eval_compare:  stage 1 RAG vs OKF Wiki · stage 2 OKF Wiki vs Graph · final RAG vs OKF Wiki vs Graph

Fairness rules kept by this module: same sources, same CQs, same answer model, same judge, and a tuned RAG (the Core MCP
preset: structure-aware units with document context, multilingual embedding, the retrieval settings of the sweep).
Results are stored as they come out — ties and losses included (runs/three_way_latest.json).
"""
from __future__ import annotations

import json
import re
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Dict, List, Optional

from src import identity
from src.aos import agent as agent_mod
from src.aos.ws import McpLog, error_text, get_json, now_iso, prefix, put_json, t

Emit = Callable[[Dict[str, Any]], None]
SYSTEMS = ("rag", "wiki", "graph")
MAX_TABLE_ROWS = 5000
_REGION_RX = re.compile(r"^[a-z]+-[a-z]+[0-9]{1,2}$")
RAG_FALLBACK_REGION = "asia-northeast3"


def _ms(t0: float) -> int:
    return round((time.perf_counter() - t0) * 1000)


def _step(emit: Emit, key: str, status: str, label: str, detail: str = "", ms: Optional[int] = None) -> None:
    ev: Dict[str, Any] = {"type": "step", "step": key, "status": status, "label": label}
    if detail:
        ev["detail"] = detail
    if ms is not None:
        ev["ms"] = ms
    emit(ev)


def rag_location(env: Dict[str, Any]) -> str:
    """RAG Engine is regional: the workspace region when it is a region, else the default RAG region."""
    region = str(env.get("region") or "")
    return region if _REGION_RX.match(region) else RAG_FALLBACK_REGION


def load_config(ws: Dict[str, Any], log: Optional[McpLog] = None) -> Dict[str, Any]:
    return get_json(log, ws["env"]["bucket"], prefix(ws["ws_id"]) + "rag/config.json", {}) or {}


def _full_rows(tb: Dict[str, Any], env: Dict[str, Any], log: McpLog) -> List[Dict[str, Any]]:
    """All rows of a source table (the wiki / graph see the whole table, so the RAG corpus does too)."""
    rows = tb.get("rows") or []
    if int(tb.get("row_count") or 0) <= len(rows) or not tb.get("fq"):
        return rows
    r = log.call("bigquery_execute_sql", {"project": env["project"], "location": env["region"], "timeout_ms": 90000,
                                          "sql": f"SELECT * FROM `{tb['fq']}` LIMIT {MAX_TABLE_ROWS}",
                                          "labels": {"datacloud": "jetski", "app": "aos-starter"}}, timeout_s=120, label=tb["name"])
    return r.get("rows") or rows if r.get("status") == "SUCCESS" else rows


# ================================================================================================ stage: rag
def stage_rag(ws: Dict[str, Any], log: McpLog, emit: Emit, parsed: Dict[str, Any]) -> Dict[str, Any]:
    lang, env = ws.get("lang", "ko"), ws["env"]
    b, pf = env["bucket"], prefix(ws["ws_id"])
    docs = [{"doc_id": d["doc_id"], "title": d.get("title") or d["doc_id"], "text": d.get("text") or ""} for d in parsed["docs"]]
    s = time.perf_counter()
    tables: Dict[str, Dict[str, Any]] = {}
    for tb in parsed["tables"]:
        cols = [c if isinstance(c, dict) else {"name": str(c)} for c in tb.get("columns") or []]
        tables[tb["name"]] = {"description": tb.get("description", ""), "columns": cols, "rows": _full_rows(tb, env, log),
                              "key_columns": [tb["pk"]] if tb.get("pk") else []}
    r = log.call("aos_core_rag_decompose", {"docs": docs, "tables": tables, "lang": lang,
                                               "write_to_gcs": {"bucket": b, "prefix": pf + "rag/units"}}, timeout_s=420)
    if r.get("status") != "SUCCESS":
        raise RuntimeError("aos_core_rag_decompose: " + error_text(r))
    st = r.get("stats") or {}
    _step(emit, "rag_units", "done", t(lang, "검색 조각 분해 · GCS 저장", "retrieval units · written to GCS"),
          t(lang, f"문서 조각 {st.get('doc_units')} · 테이블 행 묶음 {st.get('table_units')} · 중앙값 {st.get('median_chars')}자",
            f"{st.get('doc_units')} document units · {st.get('table_units')} row cards · median {st.get('median_chars')} chars"), _ms(s))
    prev = load_config(ws, log)
    corpus = ""
    if prev.get("corpus") and prev.get("fingerprint") == r.get("fingerprint"):
        chk = log.call("aos_core_rag_status", {"corpus": prev["corpus"]}, timeout_s=60)
        if chk.get("status") == "SUCCESS" and chk.get("files"):
            corpus = prev["corpus"]
            _step(emit, "rag_corpus", "done", t(lang, "RAG Engine 코퍼스 (변경 없음 — 재사용)", "RAG Engine corpus (unchanged — reused)"),
                  f"{corpus.rsplit('/', 1)[-1]} · {chk.get('files')} files")
    loc = rag_location(env)
    if not corpus:
        if prev.get("corpus"):   # sources changed: drop the stale corpus, it keeps billing otherwise
            log.call("aos_core_rag_delete_corpus", {"corpus": prev["corpus"], "wait_s": 60}, timeout_s=120)
        s = time.perf_counter()
        c = log.call("aos_core_rag_create_corpus", {"project": env["project"], "location": loc, "display_name": f"aos-{ws['ws_id']}",
                                                       "description": f"Agentic Ontology Starter workspace {ws['ws_id']} — RAG baseline (same sources as the wiki / graph)",
                                                       "wait_s": 420}, timeout_s=480)
        if c.get("status") != "SUCCESS" or not c.get("corpus"):
            raise RuntimeError("aos_core_rag_create_corpus: " + (error_text(c) or "operation still running"))
        corpus = c["corpus"]
        _step(emit, "rag_corpus", "done", t(lang, "RAG Engine 코퍼스 생성", "RAG Engine corpus created"), f"{loc} · {c.get('embedding_model')}", _ms(s))
        s = time.perf_counter()
        imp = log.call("aos_core_rag_import_files", {"corpus": corpus, "gcs_uris": [r["written"]["import_uri"]], "wait_s": 420}, timeout_s=480)
        if imp.get("status") != "SUCCESS":
            raise RuntimeError("aos_core_rag_import_files: " + error_text(imp))
        for _ in range(8):
            if imp.get("done"):
                break
            imp = log.call("aos_core_rag_get_operation", {"operation": imp["operation"], "wait_s": 240}, timeout_s=300)
            if imp.get("status") != "SUCCESS":
                raise RuntimeError("aos_core_rag_get_operation: " + error_text(imp))
        if not imp.get("done"):
            raise RuntimeError(t(lang, "RAG 임포트가 제한 시간 안에 끝나지 않았습니다 — 단계를 다시 실행하면 이어서 확인합니다", "RAG import did not finish in time — re-run the stage to continue"))
        _step(emit, "rag_import", "done", t(lang, "조각 임포트 · 임베딩", "units imported · embedded"),
              json.dumps(imp.get("response") or {}, ensure_ascii=False)[:160], _ms(s))
    status = log.call("aos_core_rag_status", {"corpus": corpus}, timeout_s=60)
    preset = status.get("preset") or {}
    cfg = {"version": r.get("version"), "built_at": now_iso(), "ws_id": ws["ws_id"], "corpus": corpus, "location": loc,
           "embedding_model": status.get("embedding_model"), "fingerprint": r.get("fingerprint"), "units_gcs": r["written"]["import_uri"],
           "decompose": r.get("options"), "import": preset.get("import"), "retrieve": preset.get("retrieve"),
           "stats": {k: st.get(k) for k in ("units", "doc_units", "table_units", "total_chars", "median_chars", "max_chars")} | {"files": status.get("files")}}
    put_json(log, b, pf + "rag/config.json", cfg)
    ws.setdefault("summary", {})["rag"] = {"units": st.get("units"), "files": status.get("files"), "embedding_model": cfg["embedding_model"], "location": loc}
    return {"units": st.get("units"), "doc_units": st.get("doc_units"), "table_units": st.get("table_units"), "files": status.get("files"),
            "corpus": corpus, "embedding_model": cfg["embedding_model"], "retrieve": cfg["retrieve"]}


# ================================================================================================ the three systems
def run_rag(ws: Dict[str, Any], question: str, cfg: Dict[str, Any], log: McpLog) -> Dict[str, Any]:
    env = ws["env"]
    r = log.call("aos_core_rag_answer", {"corpus": cfg["corpus"], "project": env["project"], "query": question, "lang": ws.get("lang", "ko"),
                                            "model": env["model"], "llm_location": env["vertex_location"], "return_evidence_text": True,
                                            **{k: v for k, v in (cfg.get("retrieve") or {}).items() if v is not None}}, timeout_s=240)
    if r.get("status") != "SUCCESS":
        return {"answer": "", "evidence": "", "error": error_text(r)[:300], "sources": []}
    return {"answer": r.get("answer", ""), "evidence": r.get("evidence_text", ""), "sources": [c["unit_id"] for c in r.get("contexts") or []],
            "trace": r.get("trace")}


def agent_evidence(res: Dict[str, Any], pages: List[Dict[str, Any]], lang: str) -> str:
    """What the Wiki / Graph agent actually read — the judge sees the same kind of evidence for every system."""
    by_id = {str(p.get("id")): p for p in pages}
    out: List[str] = []
    for s in res.get("steps") or []:
        for pid in s.get("pages") or []:
            if pid in by_id:
                out.append(f"[{pid}]\n{agent_mod.page_text(by_id[pid], lang)[:4000]}")
        if s.get("query") and not s.get("error"):
            out.append(f"[{str(s.get('action')).upper()}] {str(s['query'])[:600]}\n{json.dumps((s.get('rows') or [])[:30], ensure_ascii=False)[:3000]}")
    return "\n\n".join(out)


def run_agent(ws: Dict[str, Any], kind: str, question: str, ctx: Dict[str, Any], log: McpLog) -> Dict[str, Any]:
    res = agent_mod.run(ws, kind, question, None, ctx, log)
    if res.get("status") in ("NOT_BUILT",) or res.get("error"):
        return {"answer": "", "evidence": "", "error": str(res.get("error") or res.get("answer"))[:300], "sources": []}
    return {"answer": res.get("answer", ""), "evidence": agent_evidence(res, ctx.get("pages") or [], ws.get("lang", "ko")),
            "sources": [r["id"] for r in res.get("refs") or []], "steps": len(res.get("steps") or [])}


# ================================================================================================ stage: compare
def stage_compare(ws: Dict[str, Any], log: McpLog, emit: Emit, cq_ids: Optional[List[str]] = None, workers: int = 4,
                  systems: Optional[List[str]] = None) -> Dict[str, Any]:
    lang, env = ws.get("lang", "ko"), ws["env"]
    b, pf = env["bucket"], prefix(ws["ws_id"])
    cqs = get_json(log, b, pf + "cqs.json", []) or []
    if cq_ids:
        cqs = [c for c in cqs if c.get("id") in cq_ids]
    if not cqs:
        raise RuntimeError(t(lang, "CQ가 없습니다 — S2를 먼저 실행하세요", "no CQs — run S2 first"))
    cfg = load_config(ws, log)
    ctx = agent_mod.load_context(ws, log)
    built = {"rag": bool(cfg.get("corpus")), "wiki": bool(ctx["pages"]), "graph": bool(ctx["plan"].get("schema"))}
    want = [s for s in (systems or SYSTEMS) if s in SYSTEMS]
    missing = [s for s in want if not built[s]]
    if missing:
        raise RuntimeError(t(lang, f"아직 만들지 않은 방식이 있습니다: {', '.join(missing)} — rag / wiki / graph 단계를 먼저 실행하세요",
                             f"not built yet: {', '.join(missing)} — run the rag / wiki / graph stages first"))
    graph_agent = "hybrid" if ctx["pages"] else "graph"
    common = {"project": env["project"], "model": env["model"], "llm_location": env["vertex_location"], "lang": lang}

    def one(job: Dict[str, Any]) -> Dict[str, Any]:
        cq, system = job["cq"], job["system"]
        quiet = McpLog("compare", None)
        s1 = time.perf_counter()
        try:
            if system == "rag":
                out = run_rag(ws, cq["question"], cfg, quiet)
            else:
                out = run_agent(ws, "wiki" if system == "wiki" else graph_agent, cq["question"], ctx, quiet)
        except Exception as e:  # noqa: BLE001 — an agent failure is a scored result, not a stage failure
            out = {"answer": "", "evidence": "", "error": f"{type(e).__name__}: {str(e)[:240]}", "sources": []}
        ms = _ms(s1)
        if out.get("answer"):
            j = quiet.call("aos_core_eval_rubric_judge", {**common, "question": cq["question"], "ground_truth": cq.get("reference_answer", ""),
                                                             "key_rubrics": cq.get("key_facts") or [], "answer": out["answer"],
                                                             "evidence": out.get("evidence", "")}, timeout_s=200)
        else:
            j = {"status": "SKIP"}
        ok = j.get("status") == "SUCCESS"
        scores = j.get("scores") if ok else {"total": 0}
        row = {"id": cq.get("id"), "type": cq.get("type") or "all", "system": system, "question": cq["question"], "score": scores.get("total", 0),
               "scores": scores, "verdict": j.get("verdict") if ok else "FAIL", "latency_sec": round(ms / 1000.0, 1),
               "answer": out.get("answer", ""), "judge_summary": j.get("summary", "") if ok else (out.get("error") or error_text(j)),
               "deductions": (j.get("deductions") or [])[:6] if ok else [], "sources": (out.get("sources") or [])[:10], "error": out.get("error", "")}
        emit({"type": "cq", "id": row["id"], "agent": system, "score": row["score"], "verdict": row["verdict"], "ms": ms, "question": cq["question"]})
        return row

    jobs = [{"cq": c, "system": s} for c in cqs for s in want]
    s = time.perf_counter()
    _step(emit, "compare", "running", t(lang, f"CQ {len(cqs)}개 × {len(want)}개 방식 실행 · 같은 채점기", f"{len(cqs)} CQs × {len(want)} systems · one judge"))
    with ThreadPoolExecutor(max_workers=max(1, workers)) as ex:
        rows = list(ex.map(identity.carry(one), jobs))
    by_sys = {sname: [r for r in rows if r["system"] == sname] for sname in want}
    out: Dict[str, Any] = {"at": now_iso(), "ws_id": ws["ws_id"], "lang": lang, "systems_run": want, "graph_agent": graph_agent, "ms": _ms(s),
                           "method": {"answer_model": env["model"], "judge": "aos_core_eval_rubric_judge (100 points, system-blind)",
                                      "rag": {k: cfg.get(k) for k in ("embedding_model", "decompose", "import", "retrieve", "stats", "location")}},
                           "cqs": [{"id": c.get("id"), "type": c.get("type") or "all", "question": c["question"],
                                    "reference_answer": c.get("reference_answer", ""), "key_facts": c.get("key_facts") or []} for c in cqs],
                           "results": by_sys}
    summary: Dict[str, Any] = {sname: {"avg": round(sum(r["score"] for r in rs) / max(1, len(rs)), 1), "pass": sum(1 for r in rs if r["verdict"] == "PASS"),
                                       "count": len(rs)} for sname, rs in by_sys.items()}
    if all(sname in by_sys for sname in SYSTEMS):
        cmp_ = log.call("aos_core_eval_compare", {"systems": {sname: {"agent_model": env["model"],
                                                                         "results": [{"id": r["id"], "score": r["score"], "type": r["type"], "latency_sec": r["latency_sec"],
                                                                                      "error": bool(r["error"])} for r in rs]} for sname, rs in by_sys.items()},
                                                    "cqs": [{"id": c["id"], "type": c["type"], "question": c["question"]} for c in out["cqs"]]}, timeout_s=60)
        if cmp_.get("status") != "SUCCESS":
            raise RuntimeError("aos_core_eval_compare: " + error_text(cmp_))
        out["comparison"] = {k: cmp_[k] for k in ("cq_count", "thresholds", "labels", "coverage", "stage1_rag_vs_wiki", "stage2_wiki_vs_graph",
                                                  "final_three_way", "findings") if k in cmp_}
        summary["stage1_delta"] = cmp_["stage1_rag_vs_wiki"]["delta_points"]
        summary["stage2_delta"] = cmp_["stage2_wiki_vs_graph"]["delta_points"]
    stamp = out["at"].replace(":", "").replace("-", "")[:15]
    if not cq_ids and len(want) == len(SYSTEMS):
        put_json(log, b, pf + f"runs/three_way_{stamp}.json", out)
        put_json(log, b, pf + "runs/three_way_latest.json", out)
        ws.setdefault("summary", {})["compare"] = {**summary, "at": out["at"], "total": len(cqs)}
    _step(emit, "compare", "done", t(lang, "3단계 비교 완료", "three-stage comparison done"),
          " · ".join(f"{sname.upper()} {v['avg']}" for sname, v in summary.items() if isinstance(v, dict)), _ms(s))
    return {**summary, "total": len(cqs), "run": out if cq_ids or len(want) != len(SYSTEMS) else None}
