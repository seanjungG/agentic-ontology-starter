# Copyright (c) 2026 Sean Jung (seanjung@google.com). All Rights Reserved.
# Non-Commercial Use Only: Methodology & Docs under CC BY-NC-ND 4.0; Source Code under PolyForm Noncommercial License 1.0.0.
# Commercial use, paid consulting/SI/PoC delivery, or production deployment requires prior written permission from seanjung@google.com.

# -*- coding: utf-8 -*-
"""Step-5 agents on the user's resources (GOAL-223): Wiki Agent · Graph Agent · Workflow Agent.

Every agent returns the same shape: {agent, status, answer, evidence{refs, queries, tools, params, timing, …}}.
Language comes from the request: KO questions run on the KO data set, EN questions on the EN data set (answers,
evidence labels and table label columns are English).
"""
import json
import re
import time
from typing import Any, Callable, Dict, List, Optional

from src import datapack
from src.agent.mcp_server import BqQueryError, DomainMcpServer
from src.agent.reasoning_engine import AiFdeAgentEngine
from src.config import StarterConfig
from src.gcp_client import call_vertex_gemini, error_message, execute_bq_sql, gcs_download_text, gcs_list

Emit = Callable[[Dict[str, Any]], None]
GRAPH_TOOLS = ["mcp_lookup_customer_profile", "mcp_query_graph_and_wiki"]
PAGE_RE = re.compile(r"\[(summary|concepts|rules|entities)\]")

WIKI_SYS = {
    "ko": """당신은 OKF 위키만 읽는 Wiki Agent입니다. 아래 [위키 페이지]만 근거로 한국어 Markdown으로 답하세요.
규칙:
1. 결론을 첫 문장에 쓰고, 필요하면 근거를 2~4개 bullet로 정리합니다.
2. 근거가 된 문장 끝에 페이지 id를 [rules] 처럼 대괄호로 붙입니다. 쓸 수 있는 id: {ids}
3. 위키에 없는 사실 · 수치 · 이름은 쓰지 않습니다. 근거가 없으면 "위키에서 근거를 찾지 못했습니다."라고만 답합니다.
4. 과장하지 않고, 고객 개인 정보나 원장 값은 추측하지 않습니다 (위키에는 테이블 값이 없습니다).
5. 수식은 LaTeX 없이 일반 텍스트로 씁니다 (예: (450,000 − 150,000) × (180 − 120) ÷ 180).""",
    "en": """You are the Wiki Agent and you read only the OKF wiki. Answer in English Markdown using ONLY the [Wiki pages] below.
Rules:
1. Give the conclusion in the first sentence, then 2-4 supporting bullets if useful.
2. End each grounded sentence with the page id in square brackets, like [rules]. Allowed ids: {ids}
3. Never state facts, numbers or names that are not in the wiki. If the wiki has no support, reply only: "No supporting passage was found in the wiki."
4. Do not exaggerate and do not guess customer or ledger values (the wiki holds no table values). Write English only.
5. Write formulas as plain text without LaTeX (e.g. (450,000 − 150,000) × (180 − 120) ÷ 180).""",
}
NOT_FOUND = {"ko": "위키에서 근거를 찾지 못했습니다", "en": "No supporting passage was found in the wiki"}


def t(lang: str, ko: str, en: str) -> str:
    return en if lang == "en" else ko


def _ms(t0: float) -> float:
    return round((time.perf_counter() - t0) * 1000, 1)


def _short(v: Any, n: int = 160) -> Any:
    if isinstance(v, str) and len(v) > n:
        return v[: n - 1] + "…"
    return v


def make_server(cfg: StarterConfig, recipe: str) -> DomainMcpServer:
    return DomainMcpServer(project_id=cfg.project_id, dataset_id=cfg.dataset_id, gcs_bucket=cfg.bucket,
                           spanner_instance_id=cfg.spanner_instance or None, spanner_database_id=cfg.spanner_database or None,
                           graph_name=cfg.graph_name, location=cfg.region, mode="ledger" if recipe == "B" else "full")


# ================================================================================================ Wiki Agent
def run_wiki(cfg: StarterConfig, recipe: str, lang: str, question: str, emit: Emit) -> Dict[str, Any]:
    t0 = time.perf_counter()
    prefix = f"{cfg.gcs_prefix(lang)}wiki/"
    emit({"type": "step", "step": "gcs", "status": "running", "label": t(lang, "GCS 위키 페이지 읽기", "Read wiki pages from GCS")})
    code, items = gcs_list(prefix, cfg.bucket)
    if code != 200:
        msg = f"storage.objects.list HTTP {code} · {error_message(items)}"
        emit({"type": "step", "step": "gcs", "status": "error", "label": t(lang, "GCS 위키 페이지 읽기", "Read wiki pages from GCS"), "detail": msg})
        return _fail("wiki", "GCS_ERROR", msg, lang, t0)
    names = sorted(i["name"] for i in (items or {}).get("items") or [] if i["name"].endswith(".md"))
    if not names:
        msg = t(lang, f"gs://{cfg.bucket}/{prefix} 에 위키가 없습니다. 4단계(데이터 적재)를 이 언어로 먼저 실행하세요.",
                f"No wiki pages under gs://{cfg.bucket}/{prefix}. Run step 4 (load data) in this language first.")
        emit({"type": "step", "step": "gcs", "status": "error", "label": t(lang, "GCS 위키 페이지 읽기", "Read wiki pages from GCS"), "detail": msg})
        return _fail("wiki", "NOT_LOADED", msg, lang, t0)
    pages = []
    g0 = time.perf_counter()
    for n in names:
        c, text = gcs_download_text(n, cfg.bucket)
        if c != 200:
            continue
        fm, _ = datapack.parse_frontmatter(text)
        pid = n.rsplit("/", 1)[-1][:-3]
        pages.append({"id": pid, "title": fm.get("title", pid), "uri": f"gs://{cfg.bucket}/{n}", "chars": len(text), "text": text})
    gcs_ms = _ms(g0)
    emit({"type": "step", "step": "gcs", "status": "done", "ms": gcs_ms, "label": t(lang, "GCS 위키 페이지 읽기", "Read wiki pages from GCS"),
          "detail": ", ".join(p["id"] for p in pages)})
    ids = [p["id"] for p in pages]
    context = "\n\n".join(f"[{p['id']}] {p['title']}\n{p['text']}" for p in pages)
    prompt = (f"[Wiki pages]\n{context}\n\n[Question]\n{question}" if lang == "en" else f"[위키 페이지]\n{context}\n\n[질문]\n{question}")
    emit({"type": "step", "step": "gemini", "status": "running", "label": f"Gemini · {t(lang, '위키 근거 답변', 'wiki-grounded answer')}"})
    r = call_vertex_gemini(prompt=prompt, system_instruction=WIKI_SYS[lang].replace("{ids}", ", ".join(ids)), temperature=0.0,
                           max_tokens=2048, model_name=cfg.model, project_id=cfg.project_id, location=cfg.vertex_location)
    answer = r.get("text") or ""
    emit({"type": "step", "step": "gemini", "status": "done" if answer else "error", "ms": r.get("elapsed_ms"),
          "label": f"Gemini · {t(lang, '위키 근거 답변', 'wiki-grounded answer')}"})
    cited = sorted(set(PAGE_RE.findall(answer)))
    if not answer:
        status, answer = "LLM_ERROR", f"Vertex AI `{cfg.model}` HTTP {r.get('http_code')}: {str(r.get('error'))[:300]}"
    elif NOT_FOUND[lang].lower() in answer.lower():
        status = "NOT_FOUND"
    elif not cited:
        status = "NO_CITATION"
    elif set(cited) - set(ids):
        status = "INVALID_CITATION"
    else:
        status = "GROUNDED"
    refs = [{"id": p["id"], "title": p["title"], "uri": p["uri"], "chars": p["chars"], "cited": p["id"] in cited} for p in pages]
    return {"agent": "wiki", "status": status, "answer": answer, "lang": lang,
            "evidence": {"refs": refs, "cited": cited, "queries": [], "tools": [
                {"name": "Core MCP · storage_list_objects + storage_read_object", "status": "SUCCESS", "ms": gcs_ms, "detail": f"{len(pages)} pages · {prefix}"},
                {"name": f"Vertex AI · {cfg.model}", "status": r.get("status"), "ms": r.get("elapsed_ms"),
                 "detail": f"{r.get('prompt_tokens', 0)} in / {r.get('candidates_tokens', 0)} out"}],
                "timing": {"model": r.get("model") or cfg.model, "location": cfg.vertex_location, "tokens_in": r.get("prompt_tokens", 0),
                           "tokens_out": r.get("candidates_tokens", 0), "llm_ms": r.get("elapsed_ms"), "gcs_ms": gcs_ms, "total_ms": _ms(t0)}}}


def _fail(agent: str, status: str, msg: str, lang: str, t0: float) -> Dict[str, Any]:
    return {"agent": agent, "status": status, "answer": msg, "lang": lang, "error": msg,
            "evidence": {"refs": [], "queries": [], "tools": [], "timing": {"total_ms": _ms(t0)}}}


# ================================================================================================ Graph / Workflow
def _engine_evidence(res: Dict[str, Any], lang: str) -> Dict[str, Any]:
    disp = ((res.get("lifecycle") or {}).get("step_2_tool_dispatch") or {}).get("dispatched_tools") or []
    queries, tools, refs = [], [], []
    for d in disp:
        out = d.get("output") or {}
        rows = out.get("matched_rows") or out.get("calculations") or out.get("matched_graph_paths") or []
        rows = [{k: _short(v) for k, v in r.items()} for r in rows[:20]]
        sql = out.get("executed_gql") or ((out.get("bq_jobs") or [{}])[-1].get("sql") if out.get("bq_jobs") else "")
        queries.append({"tool": d.get("tool_name"), "status": out.get("status"), "ms": out.get("tool_elapsed_ms"),
                        "kind": "GQL" if out.get("executed_gql") else "SQL", "sql": sql, "row_count": len(out.get("matched_rows")
                        or out.get("calculations") or out.get("matched_graph_paths") or []), "rows": rows,
                        "job_ids": out.get("bq_job_ids") or [], "all_sql": [j.get("sql") for j in out.get("bq_jobs") or []]})
        tools.append({"name": d.get("tool_name"), "status": out.get("status"), "ms": out.get("tool_elapsed_ms"), "detail": d.get("reason", "")})
        for a in out.get("grounded_anchors") or []:
            refs.append({"id": a.split(" ")[0], "title": a, "kind": "clause"})
        for r in out.get("calculations") or []:
            for k in ("applied_rule_id", "grounded_chunk_id", "tco_rule_id"):
                if r.get(k):
                    refs.append({"id": r[k], "title": r[k], "kind": "rule" if "RULE" in str(r[k]) else "clause"})
    seen, uniq = set(), []
    for r in refs:
        if r["id"] not in seen:
            seen.add(r["id"])
            uniq.append(r)
    llm = res.get("llm_telemetry") or {}
    bq = res.get("bq_telemetry") or {}
    return {"refs": uniq, "queries": queries, "tools": tools, "params": {k: v for k, v in (res.get("applied_params") or {}).items() if v is not None},
            "notes": res.get("param_notes") or [],
            "timing": {"model": llm.get("model"), "location": llm.get("location"), "tokens_in": llm.get("prompt_tokens"),
                       "tokens_out": llm.get("candidates_tokens"), "llm_ms": llm.get("elapsed_ms"),
                       "total_ms": round(float((res.get("performance") or {}).get("total_elapsed_seconds") or 0) * 1000, 1),
                       "dataset": bq.get("dataset"), "graph": bq.get("graph"), "job_ids": bq.get("job_ids") or []}}


def _run_engine(cfg: StarterConfig, recipe: str, lang: str, question: str, emit: Emit, tools: Optional[List[str]]) -> Dict[str, Any]:
    server = make_server(cfg, recipe)
    eng = AiFdeAgentEngine(project_id=cfg.project_id, model_name=cfg.model, server=server, location=cfg.vertex_location,
                           tools=tools, trace=lambda ev: emit({"type": "step", **ev}))
    return eng.execute_cycle(question, engine="bigquery", lang=lang)


def _not_loaded(agent: str, lang: str, e: BqQueryError, cfg: StarterConfig, t0: float) -> Dict[str, Any]:
    msg = str(e.res.get("error", ""))[:400]
    hint = t(lang, f"BigQuery 조회 실패 ({cfg.fq}). 4단계(데이터 적재)를 먼저 실행했는지 확인하세요. · {msg}",
             f"BigQuery query failed ({cfg.fq}). Make sure step 4 (load data) ran first. · {msg}")
    return _fail(agent, "NOT_LOADED", hint, lang, t0)


def run_graph(cfg: StarterConfig, recipe: str, lang: str, question: str, emit: Emit) -> Dict[str, Any]:
    t0 = time.perf_counter()
    try:
        res = _run_engine(cfg, recipe, lang, question, emit, GRAPH_TOOLS)
    except BqQueryError as e:
        return _not_loaded("graph", lang, e, cfg, t0)
    return {"agent": "graph", "status": res.get("answer_status"), "answer": res.get("answer_body") or "", "lang": lang,
            "evidence": _engine_evidence(res, lang)}


def g2w_check(cfg: StarterConfig, lang: str, emit: Emit) -> Dict[str, Any]:
    """G2-W single source: policy values in the wiki rules frontmatter must equal what the ledgers / graph use."""
    s = time.perf_counter()
    label = t(lang, "G2-W · 정책값 단일 출처 확인", "G2-W · single-source policy values")
    emit({"type": "step", "step": "g2w", "status": "running", "label": label})
    obj = f"{cfg.gcs_prefix(lang)}wiki/rules.md"
    code, text = gcs_download_text(obj, cfg.bucket)
    source = f"gs://{cfg.bucket}/{obj}"
    if code != 200:
        text = next(p["text"] for p in datapack.wiki(lang) if p["page"] == "rules")
        source = t(lang, f"로컬 data/llm_wiki/{lang}/rules.md (GCS 위키 없음)", f"local data/llm_wiki/{lang}/rules.md (no GCS wiki)")
    consts = datapack.policy_constants(text)
    fq = cfg.fq
    sql = f"""SELECT
  (SELECT MAX(mandatory_retention_days) FROM `{fq}.tb_subsidy_policy`) AS mandatory_retention_days,
  (SELECT MIN(monthly_fee_krw) FROM `{fq}.tb_plan_master` WHERE min_maintenance_days > 0) AS baseline_fee_krw,
  (SELECT ROUND(MAX(SAFE_DIVIDE(additional_subsidy_cap_krw, base_subsidy_krw)), 4) FROM `{fq}.tb_subsidy_policy`) AS retail_subsidy_cap_rate,
  (SELECT MAX(selective_discount_rate) FROM `{fq}.tb_plan_master`) AS selective_discount_rate,
  (SELECT MAX(commitment_months) FROM `{fq}.tb_customer_contract`) AS tco_months"""
    r = execute_bq_sql(sql, project_id=cfg.project_id, location=cfg.region)
    ledger = (r.get("rows") or [{}])[0] if r.get("status") == "SUCCESS" else {}
    g = execute_bq_sql(f"SELECT param_id, value FROM `{fq}.tb_policy_params`", project_id=cfg.project_id, location=cfg.region)
    graph_vals = {x["param_id"]: x["value"] for x in g.get("rows") or []} if g.get("status") == "SUCCESS" else {}
    rows = []
    for k, v in consts.items():
        lv = ledger.get(k)
        gv = graph_vals.get(k)
        match = lv is not None and abs(float(lv) - float(v)) < 1e-6 and (gv is None or abs(float(gv) - float(v)) < 1e-6)
        rows.append({"key": k, "wiki": v, "ledger": lv, "graph": gv, "match": match})
    status = "PASS" if rows and all(x["match"] for x in rows) else ("ERROR" if r.get("status") != "SUCCESS" else "FAIL")
    detail = " · ".join(f"{x['key']}={x['wiki']}{'' if x['match'] else ' ≠ ' + str(x['ledger'])}" for x in rows)
    emit({"type": "step", "step": "g2w", "status": "done" if status == "PASS" else "error", "ms": _ms(s), "label": label, "detail": detail})
    return {"status": status, "source": source, "rows": rows, "sql": sql, "ms": _ms(s),
            "error": error_message(r.get("error")) if r.get("status") != "SUCCESS" else ""}


def _workflow_trace(res: Dict[str, Any], g2w: Dict[str, Any], lang: str) -> Dict[str, Any]:
    outs = {d["tool_name"]: d.get("output") or {} for d in
            ((res.get("lifecycle") or {}).get("step_2_tool_dispatch") or {}).get("dispatched_tools") or []}
    look, calc, graph = outs.get("mcp_lookup_customer_profile"), outs.get("mcp_calculate_penalty_rule"), outs.get("mcp_query_graph_and_wiki")
    st = lambda o: "skipped" if o is None else ("done" if o.get("status") == "SUCCESS" else "warn")  # noqa: E731
    point = "W3" if calc else ("W2" if look else "W1")
    wf = next(w for w in datapack.workflows(lang) if w["point"] == point)
    names = {s["step_id"]: s["name"] for s in wf["steps"]}
    c0 = (calc or {}).get("calculations") or [{}]
    c0 = c0[0] if c0 else {}
    outcome = c0.get("penalty_status") or (calc or {}).get("status") or res.get("answer_status")
    if point == "W3":
        steps = [
            {"step_id": "W3-1", "name": names["W3-1"], "status": st(look), "detail": f"{(look or {}).get('status', '-')} · rows={(look or {}).get('matched_rows_count', 0)}"},
            {"step_id": "W3-2", "name": names["W3-2"], "status": "done" if g2w.get("status") == "PASS" else "error", "detail": g2w.get("status", "-")},
            {"step_id": "W3-3", "name": names["W3-3"], "status": st(calc), "detail": str(c0.get("penalty_status") or (calc or {}).get("status") or "-")},
            {"step_id": "W3-4", "name": names["W3-4"], "status": st(calc),
             "detail": (f"penalty_krw={c0.get('penalty_krw')}" if c0.get("penalty_krw") is not None else "") +
                       (f" · tco={c0.get('tco_recommendation')} ({c0.get('tco_savings_krw')})" if c0.get("tco_recommendation") else "")},
            {"step_id": "W3-5", "name": names["W3-5"], "status": st(graph), "detail": str(c0.get("grounded_chunk_id") or res.get("answer_status"))},
        ]
    elif point == "W2":
        steps = [{"step_id": "W2-1", "name": names["W2-1"], "status": "done", "detail": ""},
                 {"step_id": "W2-2", "name": names["W2-2"], "status": st(look), "detail": (look or {}).get("status", "-")},
                 {"step_id": "W2-3", "name": names["W2-3"], "status": st(graph), "detail": (graph or {}).get("status", "-")},
                 {"step_id": "W2-4", "name": names["W2-4"], "status": "done", "detail": res.get("answer_status")}]
    else:
        steps = [{"step_id": "W1-1", "name": names["W1-1"], "status": "done", "detail": ""},
                 {"step_id": "W1-2", "name": names["W1-2"], "status": st(graph), "detail": (graph or {}).get("status", "-")},
                 {"step_id": "W1-3", "name": names["W1-3"], "status": "done", "detail": res.get("answer_status")}]
    return {"workflow_id": wf["workflow_id"], "point": point, "name": wf["name"], "steps": steps, "outcome": outcome}


def run_workflow(cfg: StarterConfig, recipe: str, lang: str, question: str, emit: Emit) -> Dict[str, Any]:
    t0 = time.perf_counter()
    g2w = g2w_check(cfg, lang, emit)
    try:
        res = _run_engine(cfg, "C", lang, question, emit, None)
    except BqQueryError as e:
        return _not_loaded("workflow", lang, e, cfg, t0)
    ev = _engine_evidence(res, lang)
    ev["g2w"] = g2w
    ev["workflow"] = _workflow_trace(res, g2w, lang)
    return {"agent": "workflow", "status": res.get("answer_status"), "answer": res.get("answer_body") or "", "lang": lang, "evidence": ev}


AGENT_FUNCS = {"wiki": run_wiki, "graph": run_graph, "workflow": run_workflow}


def run_agent(cfg: StarterConfig, recipe: str, agent: str, lang: str, question: str, emit: Optional[Emit] = None) -> Dict[str, Any]:
    emit = emit or (lambda ev: None)
    fn = AGENT_FUNCS.get(agent)
    if not fn:
        return _fail(agent, "UNKNOWN_AGENT", f"unknown agent: {agent}", lang, time.perf_counter())
    try:
        out = fn(cfg, recipe, lang, question.strip(), emit)
    except Exception as e:  # surface, never swallow
        out = _fail(agent, "ERROR", f"{type(e).__name__}: {str(e)[:400]}", lang, time.perf_counter())
    out["question"] = question
    out["recipe"] = recipe
    return out


def presets(lang: str, recipe: str, agent: str) -> List[str]:
    qs = [c["query"] for c in datapack.cqs(lang, recipe) if c["agent"] == agent][:3]
    qs += [b["query"] for b in datapack.boundary(lang) if b.get("agent") == agent][:1]
    return qs


def to_json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, default=str)
