# Copyright (c) 2026 Sean Jung (seanjung@google.com). All Rights Reserved.
# Non-Commercial Use Only: Methodology & Docs under CC BY-NC-ND 4.0; Source Code under PolyForm Noncommercial License 1.0.0.
# Commercial use, paid consulting/SI/PoC delivery, or production deployment requires prior written permission from seanjung@google.com.

# -*- coding: utf-8 -*-
"""Generic agents over a workspace (GOAL-233): Wiki · Graph · Hybrid.

The reasoning (prompts, next-action policy, calculation) lives in the Core MCP tool `aos_core_agent_step`.
This loop only executes the actions with the caller's credentials and feeds the observations back:

    agent_step → read_wiki (workspace pages) | gql / sql (Core MCP bigquery_execute_sql) → agent_step … → answer
"""
from __future__ import annotations

import re
import time
from typing import Any, Callable, Dict, List, Optional

from src.aos.ws import McpLog, error_text, get_json, prefix, t

Emit = Callable[[Dict[str, Any]], None]
AGENTS = ("wiki", "graph", "hybrid")
MAX_STEPS = 6


def page_text(p: Dict[str, Any], lang: str) -> str:
    lines = [f"# {p.get('title')} ({p.get('id')})", f"> {p.get('summary', '')}", "", str(p.get("body_md") or "")]
    if p.get("policy"):
        lines.append("\n" + t(lang, "정책 상수", "Policy constants") + ": " +
                     "; ".join(f"{c.get('name')}={c.get('value')}{c.get('unit', '')}" for c in p["policy"]))
    if p.get("relations"):
        lines.append(t(lang, "관계", "Relations") + ": " + ", ".join(f"{r.get('type')}→{r.get('target')}" for r in p["relations"]))
    if p.get("applies_to"):
        lines.append("applies_to: " + "; ".join(
            f"{a.get('table')}" + (f" WHERE {a['where'].get('column')} {a['where'].get('op', '=')} {a['where'].get('value')}" if a.get("where") else "")
            for a in p["applies_to"]))
    if p.get("sources"):
        lines.append(t(lang, "근거", "Sources") + ": " + "; ".join(f"{s.get('doc')} §{s.get('section')}" for s in p["sources"]))
    return "\n".join(lines)


def load_context(ws: Dict[str, Any], log: Optional[McpLog] = None) -> Dict[str, Any]:
    b, pf = ws["env"]["bucket"], prefix(ws["ws_id"])
    pages = get_json(log, b, pf + "wiki/pages.json", []) or []
    plan = get_json(log, b, pf + "graph/plan.json", {}) or {}
    return {"pages": pages, "plan": plan}


def _policy_text(p: Dict[str, Any]) -> str:
    return "; ".join(f"{c.get('name')}={c.get('value')}{c.get('unit', '')}" for c in p.get("policy") or [])


def run(ws: Dict[str, Any], agent: str, question: str, emit: Optional[Emit] = None, ctx: Optional[Dict[str, Any]] = None,
        log: Optional[McpLog] = None, max_steps: int = MAX_STEPS) -> Dict[str, Any]:
    emit = emit or (lambda ev: None)
    lang = ws.get("lang", "ko")
    env = ws["env"]
    log = log or McpLog("agent", None)
    t0 = time.perf_counter()
    agent = agent if agent in AGENTS else "hybrid"
    ctx = ctx or load_context(ws, log)
    pages: List[Dict[str, Any]] = ctx.get("pages") or []
    plan: Dict[str, Any] = ctx.get("plan") or {}
    schema = plan.get("schema") if plan else None
    graph_ready = bool(plan.get("graph_ready")) if plan else False
    by_id = {str(p.get("id")): p for p in pages}
    if agent == "wiki" and not pages:
        return _fail(agent, "NOT_BUILT", t(lang, "위키가 아직 없습니다 — 구축 S3(위키)를 먼저 실행하세요.", "No wiki yet — run build stage S3 (wiki) first."), lang, t0)
    if agent in ("graph", "hybrid") and not schema:
        if agent == "graph" or not pages:
            return _fail(agent, "NOT_BUILT", t(lang, "그래프가 아직 없습니다 — 구축 S4(그래프)를 먼저 실행하세요.", "No graph yet — run build stage S4 (graph) first."), lang, t0)
    context = {"wiki_index": [{"id": p.get("id"), "layer": p.get("layer"), "title": p.get("title"), "summary": p.get("summary"),
                               "policy_text": _policy_text(p)} for p in pages],
               "graph": schema, "graph_ready": graph_ready, "project": env["project"], "dataset": env["dataset"]}
    observations: List[Dict[str, Any]] = []
    steps: List[Dict[str, Any]] = []
    tel = {"llm_ms": 0, "tokens_in": 0, "tokens_out": 0, "data_ms": 0, "steps": 0, "model": ""}
    answer, citations, confidence, status = "", [], "", "ERROR"
    for i in range(max_steps):
        emit({"type": "step", "step": f"think-{i + 1}", "status": "running", "label": t(lang, f"추론 {i + 1} · Core MCP aos_core_agent_step", f"Reason {i + 1} · Core MCP aos_core_agent_step")})
        res = log.call("aos_core_agent_step", {"agent": agent, "question": question, "lang": lang, "context": context,
                                                  "observations": observations, "max_steps": max_steps, "project": env["project"],
                                                  "model": env["model"], "location": env["vertex_location"]}, timeout_s=300)
        if res.get("status") != "SUCCESS" and res.get("status") != "AUTH_REQUIRED":  # one retry for transient model errors
            res = log.call("aos_core_agent_step", {"agent": agent, "question": question, "lang": lang, "context": context,
                                                      "observations": observations, "max_steps": max_steps, "project": env["project"],
                                                      "model": env["model"], "location": env["vertex_location"]}, timeout_s=300)
        if res.get("status") != "SUCCESS":
            msg = error_text(res)
            emit({"type": "step", "step": f"think-{i + 1}", "status": "error", "label": "aos_core_agent_step", "detail": msg[:300]})
            return _fail(agent, "ERROR", msg, lang, t0, steps)
        tt = res.get("telemetry") or {}
        tel["llm_ms"] += int(tt.get("ms") or 0)
        tel["tokens_in"] += int(tt.get("tokens_in") or 0)
        tel["tokens_out"] += int(tt.get("tokens_out") or 0)
        tel["model"] = tt.get("model") or tel["model"]
        for c in res.get("calcs") or []:
            observations.append(c)
            steps.append({"action": "calc", "thought": c.get("thought", ""), "input": c.get("input"), "result": c.get("result"), "error": c.get("error")})
            emit({"type": "step", "step": f"calc-{len(steps)}", "status": "done" if not c.get("error") else "error", "label": f"calc · {c.get('input')} = {c.get('result')}"})
        action = res.get("action")
        thought = res.get("thought", "")
        emit({"type": "step", "step": f"think-{i + 1}", "status": "done", "ms": tt.get("ms"), "label": f"{action} · {thought[:120]}"})
        if action == "answer":
            answer, citations, confidence = res.get("answer", ""), res.get("citations") or [], res.get("confidence", "")
            steps.append({"action": "answer", "thought": thought})
            break
        if action == "read_wiki":
            ids = [i_ for i_ in (res.get("page_ids") or []) if i_ in by_id]
            got = [{"id": pid, "title": by_id[pid].get("title"), "text": page_text(by_id[pid], lang)} for pid in ids]
            obs = {"action": "read_wiki", "input": ids, "result": got} if got else {"action": "read_wiki", "input": res.get("page_ids"), "error": "no such page ids"}
            observations.append(obs)
            steps.append({"action": "read_wiki", "thought": thought, "pages": ids})
            emit({"type": "step", "step": f"wiki-{i + 1}", "status": "done" if got else "error", "label": t(lang, "위키 읽기 · ", "read wiki · ") + ", ".join(ids or ["-"])})
            continue
        q = res.get("query", "")
        if res.get("query_error"):
            observations.append({"action": action, "input": q, "error": res["query_error"]})
            steps.append({"action": action, "thought": thought, "query": q, "error": res["query_error"]})
            emit({"type": "step", "step": f"q-{i + 1}", "status": "error", "label": f"{action} · {res['query_error']}"})
            continue
        s0 = time.perf_counter()
        r = log.call("bigquery_execute_sql", {"project": env["project"], "sql": q, "location": env["region"], "timeout_ms": 45000,
                                              "labels": {"datacloud": "jetski", "app": "aos-starter"}}, timeout_s=70)
        ms = round((time.perf_counter() - s0) * 1000)
        tel["data_ms"] += ms
        if r.get("status") == "SUCCESS":
            rows = r.get("rows") or []
            observations.append({"action": action, "input": q, "result": {"rows": rows[:30]}})
            steps.append({"action": action, "thought": thought, "query": q, "rows": rows[:50], "row_count": len(rows), "ms": ms})
            emit({"type": "step", "step": f"q-{i + 1}", "status": "done", "ms": ms, "label": f"{action.upper()} · {len(rows)} rows"})
        else:
            err = error_text(r)
            observations.append({"action": action, "input": q, "error": err[:800]})
            steps.append({"action": action, "thought": thought, "query": q, "error": err[:800], "ms": ms})
            emit({"type": "step", "step": f"q-{i + 1}", "status": "error", "ms": ms, "label": f"{action.upper()} · {err[:160]}"})
    tel["steps"] = len(steps)
    if answer:
        used_data = any(s.get("action") in ("gql", "sql") and not s.get("error") for s in steps)
        used_wiki = any(s.get("action") == "read_wiki" and s.get("pages") for s in steps)
        grounded = (agent == "wiki" and used_wiki) or (agent == "graph" and used_data) or (agent == "hybrid" and (used_data or used_wiki))
        status = "GROUNDED" if grounded else "UNGROUNDED"
    else:
        answer = t(lang, "최대 단계 안에 답을 만들지 못했습니다.", "No answer within the step limit.")
        status = "NO_ANSWER"
    cited_pages = [c for c in citations if c in by_id] + [p for s in steps for p in s.get("pages") or []]
    refs = [{"id": pid, "title": by_id[pid].get("title"), "layer": by_id[pid].get("layer"), "cited": pid in citations}
            for pid in dict.fromkeys(cited_pages)]
    return {"agent": agent, "status": status, "answer": answer, "citations": citations, "confidence": confidence, "lang": lang,
            "question": question, "steps": steps, "refs": refs, "graph_ready": graph_ready,
            "telemetry": {**tel, "total_ms": round((time.perf_counter() - t0) * 1000)}}


def _fail(agent: str, status: str, msg: str, lang: str, t0: float, steps: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    return {"agent": agent, "status": status, "answer": msg, "error": msg, "lang": lang, "steps": steps or [], "refs": [],
            "citations": [], "telemetry": {"total_ms": round((time.perf_counter() - t0) * 1000)}}


def guard_query(q: str, project: str, dataset: str) -> Optional[str]:
    """Studio query console guard: read-only single statement on the workspace dataset (or its declared sources)."""
    q = str(q or "").strip().rstrip(";")
    if not re.match(r"^(SELECT|WITH|GRAPH)\b", q, re.I):
        return "SELECT / WITH / GRAPH only"
    if ";" in q:
        return "one statement only"
    body = re.sub(r"'(?:[^'\\]|\\.)*'", "''", q)
    if re.search(r"\b(INSERT|UPDATE|DELETE|MERGE|DROP|CREATE|ALTER|TRUNCATE|GRANT|REVOKE|CALL|EXECUTE|EXPORT|LOAD|DECLARE|SET)\b", body, re.I):
        return "read-only queries only"
    return None
