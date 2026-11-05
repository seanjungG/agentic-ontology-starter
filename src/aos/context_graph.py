# Copyright (c) 2026 Sean Jung (seanjung@google.com). All Rights Reserved.
# Non-Commercial Use Only: Methodology & Docs under CC BY-NC-ND 4.0; Source Code under PolyForm Noncommercial License 1.0.0.
# Commercial use, paid consulting/SI/PoC delivery, or production deployment requires prior written permission from seanjung@google.com.

# -*- coding: utf-8 -*-
"""Starter Context Graph (GOAL-285 · REQ-4/REQ-6) — one JSON graph per workspace in the user's bucket.

    gs://<bucket>/aos/<ws_id>/context_graph/graph.json

    L0 events      every agent step / tool call of a run (question · read_wiki · gql/sql · calc · answer)
    L1 runs        one per agent answer (Wiki · Graph · Hybrid), `cg_run_id` is returned with the answer
    L1 feedback    FeedbackSignal: feedback_mode SENTENCE | THUMBS_CHIP | HYBRID · raw_sentence · parsed_intent
    L2 candidates  proposed_patch + regression_cq (src.aos.sentence_feedback)
    SME approvals  approve / reject per candidate
    ChangeSets     approved candidate → regression CQ appended to the workspace CQ set (origin `context_graph`) so the
                   Evaluation tab guards the fix; the wiki patch itself stays a reviewed proposal ("그래프 반영").

The server keeps no state: every call is read-modify-write on the bucket object, serialized per workspace by an
in-process lock. Writes are best-effort for agent runs — a Context Graph failure never breaks an answer, the error is
returned in the payload instead. A feedback whose run is unknown (no run id, an older answer, another instance)
synthesizes the L1 Run from the question/answer snapshot, so no feedback is ever lost.
"""
from __future__ import annotations

import json
import secrets
import threading
from typing import Any, Callable, Dict, List, Optional

from src.aos import sentence_feedback as sf
from src.aos.ws import McpLog, WsError, error_text, get_text, now_iso, prefix, put_json

CG_VERSION = "aos-cg-1"
CAPS = {"events": 1500, "runs": 300, "feedback": 500, "candidates": 300, "approvals": 300, "changesets": 300}
LISTS = tuple(CAPS)
SURFACE_AGENT = {"wiki_agent": "wiki", "bqg_agent": "graph", "hybrid_agent": "hybrid"}
CQ_TYPE = {"wiki": "doc", "graph": "data", "hybrid": "hybrid"}
MAX_CQS = 60  # studio.save_cqs keeps at most 60

_LOCKS: Dict[str, threading.Lock] = {}
_LOCKS_GUARD = threading.Lock()


def graph_name(ws_id: str) -> str:
    return prefix(ws_id) + "context_graph/graph.json"


def _lock(bucket: str, ws_id: str) -> threading.Lock:
    key = f"{bucket}/{ws_id}"
    with _LOCKS_GUARD:
        if key not in _LOCKS:
            _LOCKS[key] = threading.Lock()
        return _LOCKS[key]


def _new_id(kind: str) -> str:
    return f"{kind}-{secrets.token_hex(4)}"


def empty_graph(ws_id: str) -> Dict[str, Any]:
    return {"version": CG_VERSION, "ws_id": ws_id, "created_at": now_iso(), "updated_at": now_iso(), **{k: [] for k in LISTS}}


def load_graph(bucket: str, ws_id: str, log: Optional[McpLog] = None) -> Dict[str, Any]:
    """Reads the graph. A missing object is an empty graph; any other read error raises (never overwrite history)."""
    code, txt = get_text(log, bucket, graph_name(ws_id))
    if code == 404 or (code != 200 and "not found" in txt.lower()) or (code == 200 and not txt.strip()):
        return empty_graph(ws_id)
    if code != 200:
        raise WsError("CG_READ_ERROR", f"Context Graph를 읽지 못했습니다: {txt[:300]}", f"Cannot read the Context Graph: {txt[:300]}")
    try:
        g = json.loads(txt)
    except ValueError as e:
        raise WsError("CG_READ_ERROR", "Context Graph JSON이 손상되었습니다.", "The Context Graph JSON is corrupt.") from e
    if not isinstance(g, dict):
        return empty_graph(ws_id)
    for k in LISTS:
        if not isinstance(g.get(k), list):
            g[k] = []
    return g


def _trim(g: Dict[str, Any]) -> None:
    for k, cap in CAPS.items():
        if len(g[k]) > cap:
            g[k] = g[k][-cap:]


def mutate(ws: Dict[str, Any], fn: Callable[[Dict[str, Any]], Any], log: Optional[McpLog] = None) -> Any:
    """Locked read → fn(graph) → write. Returns fn's result. Raises WsError when the write fails."""
    bucket, ws_id = ws["env"]["bucket"], ws["ws_id"]
    log = log or McpLog("cg", None)
    with _lock(bucket, ws_id):
        g = load_graph(bucket, ws_id, log)
        out = fn(g)
        _trim(g)
        g["updated_at"] = now_iso()
        r = put_json(log, bucket, graph_name(ws_id), g)
        if r.get("status") != "SUCCESS":
            raise WsError("CG_WRITE_ERROR", f"Context Graph 저장 실패: {error_text(r)[:300]}", f"Context Graph write failed: {error_text(r)[:300]}")
    return out


# ------------------------------------------------------------------------------------------------ L0 / L1 runs
def _events_from_steps(run_id: str, surface: str, res: Dict[str, Any], ts: str) -> List[Dict[str, Any]]:
    ev = [{"event_id": f"{run_id}:0", "run_id": run_id, "ts": ts, "kind": "question", "agent_surface": surface,
           "label": str(res.get("question") or "")[:300], "status": "done"}]
    for i, s in enumerate(res.get("steps") or [], 1):
        act = str(s.get("action") or "")
        e: Dict[str, Any] = {"event_id": f"{run_id}:{i}", "run_id": run_id, "ts": ts, "kind": "tool" if act in ("gql", "sql", "read_wiki", "calc") else act or "step",
                             "action": act, "agent_surface": surface, "label": str(s.get("thought") or "")[:240],
                             "status": "error" if s.get("error") else "done"}
        if s.get("query"):
            e["query"] = str(s["query"])[:600]
        if s.get("pages"):
            e["pages"] = [str(p) for p in s["pages"]][:10]
        if "row_count" in s:
            e["row_count"] = s.get("row_count")
        if s.get("ms") is not None:
            e["ms"] = s.get("ms")
        if s.get("engine"):
            e["engine"] = s.get("engine")
        if act == "calc":
            e["calc"] = f"{s.get('input')} = {s.get('result')}"[:200]
        if s.get("error"):
            e["error"] = str(s["error"])[:300]
        ev.append(e)
    n = len(ev)
    ev.append({"event_id": f"{run_id}:{n}", "run_id": run_id, "ts": ts, "kind": "answer", "agent_surface": surface,
               "label": str(res.get("answer") or "")[:300], "status": "error" if res.get("error") else "done"})
    return ev


def _run_node(run_id: str, agent: str, question: str, answer: str, ts: str, *, status: str = "", synthesized: bool = False,
              res: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    res = res or {}
    tel = res.get("telemetry") or {}
    return {"run_id": run_id, "agent": agent, "agent_surface": sf.normalize_surface(agent), "question": question[:1000],
            "answer": answer[:3000], "status": status or ("SYNTHESIZED" if synthesized else ""), "ts": ts, "synthesized": synthesized,
            "citations": [str(c) for c in (res.get("citations") or [])][:10], "graph_engine": res.get("graph_engine", ""),
            "telemetry": {k: tel.get(k) for k in ("total_ms", "steps", "tokens_in", "tokens_out", "model") if k in tel},
            "n_events": 0}


def record_run(ws: Dict[str, Any], res: Dict[str, Any], log: Optional[McpLog] = None, compare_of: str = "") -> Dict[str, Any]:
    """L1 Run + L0 events for one agent answer. Best-effort: never raises (errors are returned as `cg_error`)."""
    agent = str(res.get("agent") or "hybrid")
    surface = sf.normalize_surface(agent)
    run_id = _new_id("run")
    ts = now_iso()
    out: Dict[str, Any] = {"cg_run_id": run_id, "agent_surface": surface}
    try:
        node = _run_node(run_id, agent, str(res.get("question") or ""), str(res.get("answer") or ""), ts, status=str(res.get("status") or ""), res=res)
        events = _events_from_steps(run_id, surface, res, ts)
        node["n_events"] = len(events)
        if res.get("cg_rules_applied"):
            node["rules_applied"] = [r.get("candidate_id") for r in res["cg_rules_applied"]][:12]
        if compare_of:
            node["compare_of"] = compare_of[:40]

        def fn(g: Dict[str, Any]) -> None:
            g["runs"].append(node)
            g["events"].extend(events)
        mutate(ws, fn, log)
        out["cg_recorded"] = True
    except Exception as e:  # noqa: BLE001 — the answer must survive a Context Graph failure
        out["cg_recorded"] = False
        out["cg_error"] = (e.en if isinstance(e, WsError) else f"{type(e).__name__}: {e}")[:300]
    return out


# ------------------------------------------------------------------------------------------------ L1 feedback → L2
def record_feedback(ws: Dict[str, Any], data: Dict[str, Any], lang: str = "ko", log: Optional[McpLog] = None) -> Dict[str, Any]:
    sentence = str(data.get("sentence") or "").strip()[:2000]
    rating = sf.normalize_rating(data.get("rating"))
    if not sentence and not rating:
        raise ValueError("sentence or rating is required")
    agent = str(data.get("agent") or "hybrid")
    agent = agent if agent in SURFACE_AGENT.values() else SURFACE_AGENT.get(sf.normalize_surface(agent), "hybrid")
    question = str(data.get("question") or "").strip()[:2000]
    answer = str(data.get("answer") or "").strip()[:6000]
    want_run = str(data.get("run_id") or "").strip()[:40]
    signal = sf.parse_sentence_feedback_to_cg_signal(sentence, question, answer, agent, rating=rating,
                                                     reason_code=str(data.get("reason_code") or ""), lang=lang)
    feedback_id = _new_id("fb")
    ts = now_iso()

    def fn(g: Dict[str, Any]) -> Dict[str, Any]:
        run = next((r for r in g["runs"] if r.get("run_id") == want_run), None) if want_run else None
        synthesized = run is None
        if synthesized:  # 0% loss: build the L1 Run from the snapshot the client still holds
            rid = want_run if want_run.startswith("run-") else _new_id("run")
            run = _run_node(rid, agent, question, answer, ts, synthesized=True)
            run["n_events"] = 2
            g["runs"].append(run)
            g["events"].extend([
                {"event_id": f"{rid}:0", "run_id": rid, "ts": ts, "kind": "question", "agent_surface": run["agent_surface"], "label": question[:300], "status": "done", "synthesized": True},
                {"event_id": f"{rid}:1", "run_id": rid, "ts": ts, "kind": "answer", "agent_surface": run["agent_surface"], "label": answer[:300], "status": "done", "synthesized": True}])
        rid = run["run_id"]
        fb = {"feedback_id": feedback_id, "run_id": rid, "ts": ts, "agent": run.get("agent") or agent, **signal,
              "summary": sf.summarize(signal, lang)}
        g["feedback"].append(fb)
        g["events"].append({"event_id": f"{rid}:fb:{feedback_id}", "run_id": rid, "ts": ts, "kind": "feedback",
                            "agent_surface": signal["agent_surface"], "label": (sentence or rating)[:300], "status": "done"})
        cand = sf.candidate_from_signal(signal, feedback_id=feedback_id, run_id=rid, lang=lang)
        if cand:
            cand.update({"created_at": ts, "agent": run.get("agent") or agent, "question": run.get("question") or question})
            g["candidates"].append(cand)
        return {"feedback": fb, "candidate": cand, "run": run, "synthesized_run": synthesized}

    r = mutate(ws, fn, log)
    return {"status": "OK", "feedback_id": feedback_id, "run_id": r["run"]["run_id"], "synthesized_run": r["synthesized_run"],
            "signal": signal, "candidate": r["candidate"], "summary": r["feedback"]["summary"],
            "stages": [k for k, _ in sf.explain_pipeline(lang)]}


# ------------------------------------------------------------------------------------------------ SME review → ChangeSet
def _cq_from_candidate(cand: Dict[str, Any], existing: List[Dict[str, Any]]) -> Dict[str, Any]:
    n = 1 + max([int(c["id"][3:]) for c in existing if str(c.get("id", "")).startswith("CG-") and str(c["id"])[3:].isdigit()] or [0])
    rq = cand.get("regression_cq") or {}
    agent = cand.get("agent") if cand.get("agent") in CQ_TYPE else SURFACE_AGENT.get((cand.get("proposed_patch") or {}).get("agent_surface", ""), "hybrid")
    return {"id": f"CG-{n}", "question": str(rq.get("question") or cand.get("question") or cand.get("title") or "")[:1000],
            "type": CQ_TYPE[agent], "agent": agent, "reference_answer": str(rq.get("must_reflect") or "")[:2000],
            "key_facts": [str(x) for x in (rq.get("expected_facts") or [])][:6],
            "business_need": f"Context Graph {cand.get('candidate_id', '')} · {rq.get('kind', 'FIX')}"[:500],
            "reasoning": str((cand.get("proposed_patch") or {}).get("statement") or "")[:1000], "origin": "context_graph"}


def review(ws: Dict[str, Any], candidate_id: str, decision: str, note: str = "", by: str = "",
           read_cqs: Optional[Callable[[], List[Dict[str, Any]]]] = None,
           save_cqs: Optional[Callable[[List[Dict[str, Any]]], Dict[str, Any]]] = None,
           log: Optional[McpLog] = None) -> Dict[str, Any]:
    """SME approval. approve → ChangeSet + regression CQ `CG-<n>` (origin context_graph) appended to the CQ set."""
    decision = str(decision or "").lower()
    if decision not in ("approve", "reject"):
        raise ValueError("decision must be approve or reject")
    ts = now_iso()
    holder: Dict[str, Any] = {}

    def find(g: Dict[str, Any]) -> Dict[str, Any]:
        cand = next((c for c in g["candidates"] if c.get("candidate_id") == candidate_id), None)
        if not cand:
            raise WsError("CG_NOT_FOUND", f"후보 {candidate_id}를 찾을 수 없습니다.", f"Candidate {candidate_id} not found.")
        if cand.get("status") in ("APPROVED", "REJECTED"):
            raise WsError("BAD_REQUEST", f"이미 검토된 후보입니다 ({cand['status']}).", f"Candidate already reviewed ({cand['status']}).")
        return cand

    # 1) regression CQ first (outside the graph lock — it writes cqs.json + workspace.json)
    cq, cq_error = None, ""
    if decision == "approve":
        cand_now = find(load_graph(ws["env"]["bucket"], ws["ws_id"], log))
        if read_cqs and save_cqs:
            try:
                existing = list(read_cqs() or [])
                if len(existing) >= MAX_CQS:
                    cq_error = f"CQ_LIMIT: {MAX_CQS}"
                else:
                    cq = _cq_from_candidate(cand_now, existing)
                    r = save_cqs(existing + [cq])
                    if r.get("status") != "SUCCESS":
                        cq, cq_error = None, error_text(r)[:300]
                    else:
                        holder["cqs"] = r.get("cqs")
            except Exception as e:  # noqa: BLE001
                cq, cq_error = None, f"{type(e).__name__}: {str(e)[:250]}"

    def fn(g: Dict[str, Any]) -> Dict[str, Any]:
        cand = find(g)
        ap = {"approval_id": _new_id("sme"), "candidate_id": candidate_id, "decision": decision, "note": str(note or "")[:1000],
              "by": str(by or "")[:200], "ts": ts}
        g["approvals"].append(ap)
        cand["status"] = "APPROVED" if decision == "approve" else "REJECTED"
        cand["approval_id"] = ap["approval_id"]
        cs = None
        if decision == "approve":
            ops = [dict(cand.get("proposed_patch") or {}, status="PROPOSED_FOR_WIKI")]
            if cq:
                ops.append({"op": "ADD_REGRESSION_CQ", "cq_id": cq["id"], "question": cq["question"], "status": "APPLIED"})
            cs = {"changeset_id": _new_id("cs"), "candidate_id": candidate_id, "approval_id": ap["approval_id"], "feedback_id": cand.get("feedback_id"),
                  "run_id": cand.get("run_id"), "ts": ts, "ops": ops, "cq_id": cq["id"] if cq else "", "cq_error": cq_error,
                  "status": "APPLIED" if cq else "RECORDED", "graph_reflected": True}
            g["changesets"].append(cs)
            cand["changeset_id"] = cs["changeset_id"]
        return {"approval": ap, "changeset": cs, "candidate": dict(cand)}

    r = mutate(ws, fn, log)
    return {"status": "OK", **r, "cq": cq, "cq_error": cq_error, "cqs": holder.get("cqs")}


# ------------------------------------------------------------------------------------------------ L3 closed loop
def approved_rules(ws: Dict[str, Any], agent: str = "", limit: int = 12, log: Optional[McpLog] = None) -> List[Dict[str, Any]]:
    """SME-approved candidate statements (latest first, the asking agent's own rules first) — injected into the next
    agent run as the synthetic `CG-RULES` wiki page (agent.run(extra_rules=…)) for the Before/After re-ask."""
    g = load_graph(ws["env"]["bucket"], ws["ws_id"], log)
    out = []
    for c in reversed(g["candidates"]):
        st = str((c.get("proposed_patch") or {}).get("statement") or "").strip()
        if c.get("status") == "APPROVED" and st:
            out.append({"candidate_id": c["candidate_id"], "changeset_id": c.get("changeset_id", ""), "agent": c.get("agent", ""),
                        "tacit_type": c.get("tacit_type", ""), "statement": st[:600]})
    out.sort(key=lambda r: 0 if r["agent"] == agent else 1)
    return out[:limit]


# ------------------------------------------------------------------------------------------------ viewer
def graph_view(ws: Dict[str, Any], lang: str = "ko", run_limit: int = 40, log: Optional[McpLog] = None) -> Dict[str, Any]:
    g = load_graph(ws["env"]["bucket"], ws["ws_id"], log)
    fb_runs = {f.get("run_id") for f in g["feedback"]}
    runs = g["runs"]
    keep = [r for r in runs if r.get("run_id") in fb_runs][-run_limit:]
    if len(keep) < run_limit:  # fill with the latest runs without feedback
        ids = {r["run_id"] for r in keep}
        keep = sorted(keep + [r for r in runs if r["run_id"] not in ids][-(run_limit - len(keep)):], key=lambda r: r.get("ts", ""))
    run_ids = {r["run_id"] for r in keep}
    fbs = [f for f in g["feedback"] if f.get("run_id") in run_ids]
    fb_ids = {f["feedback_id"] for f in fbs}
    cands = [c for c in g["candidates"] if c.get("feedback_id") in fb_ids]
    cand_ids = {c["candidate_id"] for c in cands}
    aps = [a for a in g["approvals"] if a.get("candidate_id") in cand_ids]
    css = [c for c in g["changesets"] if c.get("candidate_id") in cand_ids]
    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []
    for r in keep:
        nodes.append({"id": r["run_id"], "layer": "L1", "kind": "run", "label": r.get("question", "")[:60], "agent": r.get("agent"),
                      "agent_surface": r.get("agent_surface"), "synthesized": r.get("synthesized", False), "ts": r.get("ts")})
    for f in fbs:
        icon = "sentence" if f.get("raw_sentence") else ("up" if f.get("rating") == "up" else "down")
        nodes.append({"id": f["feedback_id"], "layer": "L1", "kind": "feedback", "icon": icon, "label": (f.get("raw_sentence") or f.get("rating") or "")[:60],
                      "feedback_mode": f.get("feedback_mode"), "polarity": (f.get("parsed_intent") or {}).get("polarity"), "ts": f.get("ts")})
        edges.append({"from": f["run_id"], "to": f["feedback_id"], "type": "HAS_FEEDBACK"})
    for c in cands:
        nodes.append({"id": c["candidate_id"], "layer": "L2", "kind": "candidate", "label": c.get("title", ""), "status": c.get("status"),
                      "tacit_type": c.get("tacit_type"), "ts": c.get("created_at")})
        edges.append({"from": c["feedback_id"], "to": c["candidate_id"], "type": "EXTRACTED_TACIT_CLAIM"})
    for a in aps:
        nodes.append({"id": a["approval_id"], "layer": "SME", "kind": "approval", "label": a.get("decision"), "ts": a.get("ts")})
        edges.append({"from": a["candidate_id"], "to": a["approval_id"], "type": "REVIEWED_BY"})
    for c in css:
        nodes.append({"id": c["changeset_id"], "layer": "CS", "kind": "changeset", "label": c.get("cq_id") or c.get("status"), "status": c.get("status"), "ts": c.get("ts")})
        edges.append({"from": c["approval_id"], "to": c["changeset_id"], "type": "APPLIED_AS"})
    events = [e for e in g["events"] if e.get("run_id") in run_ids][-600:]
    return {"status": "OK", "stages": [{"id": k, "label": v} for k, v in sf.explain_pipeline(lang)], "nodes": nodes, "edges": edges,
            "runs": keep, "events": events, "feedback": fbs, "candidates": cands, "approvals": aps, "changesets": css,
            "counts": {k: len(g[k]) for k in LISTS}, "updated_at": g.get("updated_at"), "object": f"gs://{ws['env']['bucket']}/{graph_name(ws['ws_id'])}",
            "pending": sum(1 for c in g["candidates"] if c.get("status") == "PENDING")}
