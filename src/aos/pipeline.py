# Copyright (c) 2026 Sean Jung (seanjung@google.com). All Rights Reserved.
# Non-Commercial Use Only: Methodology & Docs under CC BY-NC-ND 4.0; Source Code under PolyForm Noncommercial License 1.0.0.
# Commercial use, paid consulting/SI/PoC delivery, or production deployment requires prior written permission from seanjung@google.com.

# -*- coding: utf-8 -*-
"""Build pipeline for a workspace (GOAL-233). One stage per request so a failed stage can simply be re-run.

    prepare  dataset (+ 7-day table expiry for the demo identity) · bucket permission · workspace.json
    ingest   documents → parsed/docs.json · CSV → BigQuery tables · BigQuery tables → profile · Gate 0 · scope
    cqs      Competency Questions (Core MCP aos_core_draft_cqs) → cqs.json
    wiki     OKF 3-layer wiki + gates (aos_core_compile_wiki) → wiki/*.md · pages.json · index.json
    graph    design → node/edge tables → Property Graph → verification GQL (aos_core_design_graph + bigquery_*)
    eval     every CQ through its agent (aos_core_agent_step) + scoring (aos_core_judge) → runs/

All GCS / BigQuery work is a Core MCP data-plane call with the request identity's token; all method know-how is a
Core MCP `aos_core_*` call. This module only decides the order and moves the results around.
"""
from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Dict, List, Optional

from src import identity
from src.aos import agent as agent_mod
from src.aos import sources as S
from src.aos.ws import (McpLog, WsError, append_calls, can_write, error_text, get_json, now_iso, prefix, put_json, put_text,
                        save, t)

Emit = Callable[[Dict[str, Any]], None]
STAGES = ("prepare", "ingest", "cqs", "wiki", "graph", "eval")
STAGE_LABEL = {
    "prepare": ("S0 준비", "S0 Prepare"), "ingest": ("S1 수집 · 프로파일", "S1 Ingest & profile"), "cqs": ("S2 CQ 초안", "S2 CQ draft"),
    "wiki": ("S3 OKF 위키", "S3 OKF wiki"), "graph": ("S4 Property Graph", "S4 Property Graph"), "eval": ("S5 평가", "S5 Evaluate"),
}


class StageSkip(Exception):
    pass


def _ms(t0: float) -> int:
    return round((time.perf_counter() - t0) * 1000)


def _kh_common(ws: Dict[str, Any]) -> Dict[str, Any]:
    env = ws["env"]
    return {"project": env["project"], "model": env["model"], "location": env["vertex_location"], "lang": ws.get("lang", "ko")}


def run_stage(ws: Dict[str, Any], stage: str, emit: Emit) -> Dict[str, Any]:
    lang = ws.get("lang", "ko")
    if stage not in STAGES:
        raise WsError("BAD_REQUEST", f"알 수 없는 단계: {stage}", f"unknown stage: {stage}")
    ok, allowed = can_write(ws["env"])
    if not ok and stage != "eval":
        raise WsError("WRITE_BLOCKED",
                      f"데모 신원(runtime)은 {allowed} 프로젝트에만 쓸 수 있습니다. 내 프로젝트에 만들려면 3단계에서 내 토큰 또는 SA를 입력하세요.",
                      f"The demo (runtime) identity may only write to {allowed}. To build in your project, enter your token or SA in step 3.")
    log = McpLog(stage, emit)
    label = t(lang, *STAGE_LABEL[stage])
    emit({"type": "stage", "stage": stage, "status": "running", "label": label})
    t0 = time.perf_counter()
    fn = {"prepare": stage_prepare, "ingest": stage_ingest, "cqs": stage_cqs, "wiki": stage_wiki, "graph": stage_graph, "eval": stage_eval}[stage]
    rec: Dict[str, Any]
    try:
        summary = fn(ws, log, emit)
        rec = {"status": "done", "summary": summary}
    except StageSkip as e:
        rec = {"status": "skipped", "summary": {"reason": str(e)}}
    except Exception as e:  # noqa: BLE001 — recorded in the workspace and the stream
        rec = {"status": "error", "error": f"{type(e).__name__}: {str(e)[:600]}"}
    rec.update(ms=_ms(t0), at=now_iso(), mcp_calls=len(log.calls), identity=identity.current())
    ws.setdefault("stages", {})[stage] = rec
    for later in STAGES[STAGES.index(stage) + 1:]:
        if rec["status"] == "done" and ws["stages"].get(later, {}).get("status") == "done" and stage in ("ingest", "wiki", "graph"):
            ws["stages"][later]["stale"] = True
    ws["stages"][stage].pop("stale", None)
    try:
        save(ws, log)
        append_calls(ws, log)
    except Exception as e:  # noqa: BLE001
        emit({"type": "warn", "message": f"workspace save failed: {e}"})
    emit({"type": "stage", "stage": stage, "status": rec["status"], "label": label, "ms": rec["ms"],
          "summary": rec.get("summary"), "error": rec.get("error", "")})
    return rec


def _step(emit: Emit, key: str, status: str, label: str, detail: str = "", ms: Optional[int] = None) -> None:
    ev: Dict[str, Any] = {"type": "step", "step": key, "status": status, "label": label}
    if detail:
        ev["detail"] = detail
    if ms is not None:
        ev["ms"] = ms
    emit(ev)


# ================================================================================================ S0 prepare
def stage_prepare(ws: Dict[str, Any], log: McpLog, emit: Emit) -> Dict[str, Any]:
    lang, env = ws.get("lang", "ko"), ws["env"]
    s = time.perf_counter()
    perms = ["storage.objects.create", "storage.objects.get", "storage.objects.list"]
    r = log.call("iam_test_permissions", {"bucket": env["bucket"], "bucket_permissions": perms}, timeout_s=30, label=env["bucket"])
    have = r.get("bucket_permissions") or r.get("permissions") or []
    missing = [p for p in perms if p not in have]
    if r.get("status") != "SUCCESS" or missing:
        raise RuntimeError(t(lang, f"버킷 gs://{env['bucket']} 권한 부족: {missing or error_text(r)} — roles/storage.objectAdmin 필요",
                             f"bucket gs://{env['bucket']} lacks permissions: {missing or error_text(r)} — needs roles/storage.objectAdmin"))
    _step(emit, "bucket", "done", t(lang, "버킷 권한 확인", "bucket permissions"), env["bucket"], _ms(s))
    s = time.perf_counter()
    info = log.call("bigquery_get_dataset_info", {"project": env["project"], "dataset": env["dataset"]}, timeout_s=30)
    created = False
    if info.get("status") == "SUCCESS" and info.get("exists"):
        loc = (info.get("dataset") or {}).get("location", "")
        if loc and loc.lower() != env["region"].lower():
            raise RuntimeError(t(lang, f"데이터셋 {env['dataset']} 위치({loc})가 리전({env['region']})과 다릅니다", f"dataset {env['dataset']} is in {loc}, not {env['region']}"))
    else:
        c = log.call("bigquery_create_dataset", {"project": env["project"], "dataset": env["dataset"], "location": env["region"],
                                                 "description": f"Agentic Ontology Starter workspace {ws['ws_id']}",
                                                 "labels": {"datacloud": "jetski", "app": "aos-starter", "aos_ws": ws["ws_id"].replace("-", "_")}}, timeout_s=40)
        if c.get("status") != "SUCCESS":
            raise RuntimeError(t(lang, f"데이터셋 생성 실패: {error_text(c)} — roles/bigquery.dataEditor(프로젝트) 필요",
                                 f"dataset creation failed: {error_text(c)} — needs roles/bigquery.dataEditor on the project"))
        created = True
        if identity.current().get("mode") == "runtime":
            log.call("bigquery_execute_sql", {"project": env["project"], "location": env["region"], "labels": {"datacloud": "jetski"},
                                              "sql": f"ALTER SCHEMA `{env['project']}.{env['dataset']}` SET OPTIONS (default_table_expiration_days = 7)"},
                     timeout_s=60, label="demo expiry 7d")
    _step(emit, "dataset", "done", t(lang, "BigQuery 데이터셋", "BigQuery dataset"), f"{env['project']}.{env['dataset']}" + (" (new)" if created else ""), _ms(s))
    return {"bucket": env["bucket"], "dataset": f"{env['project']}.{env['dataset']}", "dataset_created": created,
            "workspace": f"gs://{env['bucket']}/{prefix(ws['ws_id'])}workspace.json"}


# ================================================================================================ S1 ingest
def stage_ingest(ws: Dict[str, Any], log: McpLog, emit: Emit) -> Dict[str, Any]:
    lang, env = ws.get("lang", "ko"), ws["env"]
    pf = prefix(ws["ws_id"])
    src = ws.get("sources") or {}
    docs: List[Dict[str, Any]] = []
    seen_ids: Dict[str, int] = {}
    for d in src.get("docs") or []:
        s = time.perf_counter()
        try:
            text = S.read_source_text(log, d["uri"])
        except Exception as e:  # noqa: BLE001
            _step(emit, f"doc:{d['name']}", "error", d["name"], str(e)[:200])
            continue
        did = S.doc_id(d["name"])
        if did in seen_ids:
            seen_ids[did] += 1
            did = f"{did}-{seen_ids[did]}"
        else:
            seen_ids[did] = 1
        title = next((ln.lstrip("# ").strip() for ln in text.splitlines() if ln.startswith("# ")), d["name"])
        item = {"doc_id": did, "title": title[:200], "name": d["name"], "uri": d["uri"], "origin": d["origin"], "text": text}
        if d.get("kind"):  # GOAL-243: user-confirmed document type + wiki strategy (types step)
            item["kind"] = d["kind"]
        if d.get("strategy"):
            item["strategy"] = d["strategy"]
        conv = d.get("conversion") or {}
        if conv:
            item["conversion"] = {k: conv.get(k) for k in ("source", "source_ext", "method", "fidelity", "grade", "pages") if conv.get(k) is not None}
        docs.append(item)
        _step(emit, f"doc:{did}", "done", t(lang, "문서 ", "document ") + did,
              f"{len(text):,} chars" + (f" · {d['kind']}/{d.get('strategy') or '-'}" if d.get("kind") else "")
              + (f" · fidelity {conv.get('fidelity')}" if conv.get("fidelity") is not None else ""), _ms(s))

    tables: List[Dict[str, Any]] = []
    used: set = set()

    def load_csv(tb: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        s = time.perf_counter()
        text = S.read_source_text(log, tb["uri"])
        parsed = S.table_from_csv_text(tb["name"] or tb["uri"], text)
        name = tb["_name"]
        r = log.call("bigquery_load_table", {"project": env["project"], "dataset": env["dataset"], "table": name,
                                             "schema": S.bq_schema(parsed["columns"]), "rows": S.json_rows(parsed["rows"], parsed["columns"]),
                                             "location": env["region"], "timeout_s": 150,
                                             "description": f"AOS starter source table ({tb['origin']}: {tb['uri']})"}, timeout_s=180, label=name)
        if r.get("status") != "SUCCESS":
            _step(emit, f"table:{name}", "error", name, error_text(r)[:200])
            return None
        _step(emit, f"table:{name}", "done", t(lang, "테이블 적재 ", "load table ") + name,
              f"{int(r.get('output_rows') or len(parsed['rows'])):,} rows → {env['project']}.{env['dataset']}.{name}", _ms(s))
        return {"name": name, "fq": f"{env['project']}.{env['dataset']}.{name}", "origin": tb["origin"], "uri": tb["uri"],
                "columns": parsed["columns"], "rows": parsed["rows"][:120], "row_count": len(parsed["rows"]), "description": ""}

    def load_bq(tb: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        s = time.perf_counter()
        try:
            prof = S.bq_table_profile(log, tb["fq"], env["region"])
        except Exception as e:  # noqa: BLE001
            _step(emit, f"table:{tb['fq']}", "error", tb["fq"], str(e)[:200])
            return None
        name = prof["name"]
        while name in used:
            name += "_2"
        used.add(name)
        _step(emit, f"table:{name}", "done", t(lang, "BigQuery 테이블 ", "BigQuery table ") + tb["fq"], f"{prof['row_count']:,} rows", _ms(s))
        return {**prof, "name": name, "origin": "bigquery", "uri": tb["fq"]}

    csv_specs = []
    for tb in src.get("tables") or []:
        if tb["origin"] == "bigquery":
            try:
                got = load_bq(tb)
            except Exception as e:  # noqa: BLE001
                _step(emit, f"table:{tb.get('fq')}", "error", str(tb.get("fq")), str(e)[:200])
                got = None
            if got:
                tables.append(got)
            continue
        name = S.table_name(tb["name"] or tb["uri"])
        while name in used:
            name += "_2"
        used.add(name)
        csv_specs.append({**tb, "_name": name})

    def safe_csv(tb: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            return load_csv(tb)
        except Exception as e:  # noqa: BLE001
            _step(emit, f"table:{tb.get('_name')}", "error", str(tb.get("_name")), str(e)[:200])
            return None
    with ThreadPoolExecutor(max_workers=4) as ex:  # CSV → BigQuery loads in parallel
        tables += [t for t in ex.map(identity.carry(safe_csv), csv_specs) if t]
    if not docs and not tables:
        raise RuntimeError(t(lang, "읽을 수 있는 문서 · 테이블이 없습니다 (2단계 데이터 확인)", "no readable documents or tables (check step 2 data)"))

    gate0: Dict[str, Any] = {}
    if docs:
        s = time.perf_counter()
        g = log.call("aos_builder_parse_documents_gate0", {"project_id": ws["ws_id"].replace("-", "_"), "domain_profile": "custom",
                                                           "inline_documents": [{"bundle": ws["ws_id"], "doc_stem": d["doc_id"], "content": d["text"][:200000]} for d in docs],
                                                           "detail_level": "compact"}, timeout_s=120)
        gate0 = {"status": g.get("status"), "fidelity": g.get("gate0_fidelity") or g.get("fidelity") or (g.get("gate0") or {}).get("fidelity"),
                 "passed": g.get("gate0_passed") if "gate0_passed" in g else (g.get("gate0") or {}).get("passed"),
                 "sections": g.get("total_sections") or g.get("sections_count")}
        _step(emit, "gate0", "done" if g.get("status") == "SUCCESS" else "warn", "Gate 0 · aos_builder_parse_documents_gate0",
              json.dumps({k: v for k, v in gate0.items() if v is not None}, ensure_ascii=False)[:200], _ms(s))
    s = time.perf_counter()
    sc = log.call("aos_core_scope", {"objective": ws["scenario"].get("objective", ""), "question_type": ws["scenario"].get("question_type", ""),
                                        "lang": lang, "docs": [{"doc_id": d["doc_id"], "title": d["title"], "text": d["text"][:3000]} for d in docs],
                                        "tables": [{"name": tb["name"], "columns": tb["columns"], "rows": tb["rows"][:60], "row_count": tb["row_count"]} for tb in tables]},
                  timeout_s=60)
    if sc.get("status") != "SUCCESS":
        raise RuntimeError("aos_core_scope: " + error_text(sc))
    for tb in tables:
        tb["pk"] = (sc.get("primary_keys") or {}).get(tb["name"], "")
    _step(emit, "scope", "done", "aos_core_scope", f"{sc.get('data_type')} × {sc.get('question_type')} · FK {len(sc.get('fk_candidates') or [])}", _ms(s))
    b = env["bucket"]
    put_json(log, b, pf + "parsed/docs.json", docs)
    put_json(log, b, pf + "parsed/tables.json", tables)
    scope = {k: sc.get(k) for k in ("data_type", "question_type", "question_type_note", "recipe", "agents", "stages", "documents",
                                    "primary_keys", "fk_candidates", "warnings", "tables")}
    ws["scope"] = scope
    ws.setdefault("summary", {}).update(docs=len(docs), tables=len(tables), data_type=sc.get("data_type"), agents=sc.get("agents"),
                                        rows=sum(tb["row_count"] for tb in tables), chars=sum(len(d["text"]) for d in docs))
    strat = {k: sum(1 for d in docs if d.get("strategy") == k) for k in ("direct", "typed", "reconvert")}
    if any(strat.values()):
        ws["summary"]["doc_strategies"] = strat
    return {"docs": len(docs), "tables": len(tables), "data_type": sc.get("data_type"), "question_type": sc.get("question_type"),
            "fk_candidates": len(sc.get("fk_candidates") or []), "gate0": gate0, "warnings": sc.get("warnings") or []}


def _parsed(ws: Dict[str, Any], log: McpLog) -> Dict[str, Any]:
    b, pf = ws["env"]["bucket"], prefix(ws["ws_id"])
    docs = get_json(log, b, pf + "parsed/docs.json", None)
    tables = get_json(log, b, pf + "parsed/tables.json", None)
    if docs is None or tables is None:
        raise RuntimeError(t(ws.get("lang", "ko"), "S1(수집)을 먼저 실행하세요", "run S1 (ingest) first"))
    return {"docs": docs, "tables": tables}


def _kh_tables(tables: List[Dict[str, Any]], rows: int) -> List[Dict[str, Any]]:
    return [{"name": tb["name"], "columns": tb["columns"], "rows": tb["rows"][:rows], "row_count": tb["row_count"], "pk": tb.get("pk", ""),
             "fq": f"`{tb['fq']}`", "description": tb.get("description", "")} for tb in tables]


# ================================================================================================ S2 CQs
def stage_cqs(ws: Dict[str, Any], log: McpLog, emit: Emit) -> Dict[str, Any]:
    lang = ws.get("lang", "ko")
    p = _parsed(ws, log)
    s = time.perf_counter()
    _step(emit, "cqs", "running", t(lang, "CQ 초안 · Gemini (약 40초)", "CQ draft · Gemini (~40 s)"))
    r = log.call("aos_core_draft_cqs", {**_kh_common(ws), "objective": ws["scenario"].get("objective", ""),
                                           "question_type": ws["scenario"].get("question_type", "W3"), "count": 8,
                                           "docs": [{"doc_id": d["doc_id"], "title": d["title"], "text": d["text"]} for d in p["docs"]],
                                           "tables": _kh_tables(p["tables"], 120)}, timeout_s=300)
    if r.get("status") != "SUCCESS":
        raise RuntimeError("aos_core_draft_cqs: " + error_text(r))
    cqs = r.get("cqs") or []
    put_json(log, ws["env"]["bucket"], prefix(ws["ws_id"]) + "cqs.json", cqs)
    _step(emit, "cqs", "done", t(lang, f"CQ {len(cqs)}개", f"{len(cqs)} CQs"), ", ".join(sorted({c['type'] for c in cqs})), _ms(s))
    ws.setdefault("summary", {})["cqs"] = len(cqs)
    tel = r.get("telemetry") or {}
    return {"cqs": len(cqs), "by_type": {k: sum(1 for c in cqs if c["type"] == k) for k in ("doc", "data", "hybrid")},
            "llm_ms": tel.get("ms"), "tokens_out": tel.get("tokens_out")}


# ================================================================================================ S3 wiki
def wiki_doc(d: Dict[str, Any]) -> Dict[str, Any]:
    """compile_wiki payload for one parsed document (GOAL-243). `kind` is sent only when the confirmed strategy needs a
    type-specific guide (typed · reconvert); 'direct' documents use the standard OKF prompt. Core MCPs before 1.5.0
    ignore the extra fields, so the call stays backward compatible."""
    out = {"doc_id": d["doc_id"], "title": d["title"], "text": d["text"]}
    if d.get("kind") and d.get("strategy") != "direct":
        out["kind"] = d["kind"]
    if d.get("strategy"):
        out["strategy"] = d["strategy"]
    return out


def stage_wiki(ws: Dict[str, Any], log: McpLog, emit: Emit) -> Dict[str, Any]:
    lang, env = ws.get("lang", "ko"), ws["env"]
    p = _parsed(ws, log)
    if not p["docs"]:
        raise StageSkip(t(lang, "문서가 없어 위키 단계를 건너뜁니다 (P2)", "no documents — wiki stage skipped (P2)"))
    s = time.perf_counter()
    _step(emit, "wiki", "running", t(lang, "OKF 위키 컴파일 · Gemini (약 2~4분)", "OKF wiki compile · Gemini (~2–4 min)"))
    kh_docs = [wiki_doc(d) for d in p["docs"]]
    typed = [f"{d['doc_id']}={d['kind']}" for d in kh_docs if d.get("kind")]
    if typed:
        _step(emit, "wiki_types", "done", t(lang, "유형별 위키 지침", "type-specific wiki guides"), ", ".join(typed)[:200])
    r = log.call("aos_core_compile_wiki", {**_kh_common(ws), "objective": ws["scenario"].get("objective", ""),
                                              "docs": kh_docs, "tables": _kh_tables(p["tables"], 5)}, timeout_s=600)
    if r.get("status") != "SUCCESS":
        raise RuntimeError("aos_core_compile_wiki: " + error_text(r))
    _step(emit, "wiki", "done", t(lang, "위키 컴파일", "wiki compiled"),
          f"{r.get('counts')} · gates {r.get('gates_passed')}/{r.get('gates_total')}", _ms(s))
    s = time.perf_counter()
    write_wiki(ws, log, r)
    _step(emit, "wiki_upload", "done", t(lang, "GCS 업로드", "upload to GCS"), f"gs://{env['bucket']}/{prefix(ws['ws_id'])}wiki/ · {len(r.get('files') or {})} files", _ms(s))
    ws.setdefault("summary", {})["wiki"] = {"pages": len(r.get("pages") or []), "counts": r.get("counts"),
                                            "gates_passed": r.get("gates_passed"), "gates_total": r.get("gates_total")}
    tel = r.get("telemetry") or {}
    return {"pages": len(r.get("pages") or []), "counts": r.get("counts"), "gates_passed": r.get("gates_passed"),
            "gates_total": r.get("gates_total"), "llm_ms": tel.get("ms"), "tokens_out": tel.get("tokens_out"), "notes": (r.get("notes") or [])[:6]}


def write_wiki(ws: Dict[str, Any], log: McpLog, r: Dict[str, Any]) -> None:
    b, pf = ws["env"]["bucket"], prefix(ws["ws_id"])
    files = r.get("files") or {}
    with ThreadPoolExecutor(max_workers=6) as ex:
        list(ex.map(identity.carry(lambda kv: put_text(log, b, pf + "wiki/" + kv[0], kv[1], "text/markdown; charset=utf-8")), files.items()))
    put_json(log, b, pf + "wiki/pages.json", r.get("pages") or [])
    put_json(log, b, pf + "wiki/index.json", r.get("index") or {})
    put_json(log, b, pf + "wiki/gates.json", {"gates": r.get("gates") or [], "passed": r.get("gates_passed"), "total": r.get("gates_total"), "at": now_iso()})


# ================================================================================================ S4 graph
def stage_graph(ws: Dict[str, Any], log: McpLog, emit: Emit, design: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    lang, env = ws.get("lang", "ko"), ws["env"]
    p = _parsed(ws, log)
    if not p["tables"]:
        raise StageSkip(t(lang, "테이블이 없어 그래프 단계를 건너뜁니다 (P1)", "no tables — graph stage skipped (P1)"))
    b, pf = env["bucket"], prefix(ws["ws_id"])
    pages = get_json(log, b, pf + "wiki/pages.json", []) or []
    s = time.perf_counter()
    _step(emit, "design", "running", t(lang, "그래프 설계 · Gemini (약 40초)", "graph design · Gemini (~40 s)") if design is None else
          t(lang, "그래프 설계 컴파일 (편집본)", "compile edited design"))
    args = {**_kh_common(ws), "objective": ws["scenario"].get("objective", ""), "dataset": env["dataset"], "graph_name": env["graph_name"],
            "tables": _kh_tables(p["tables"], 120), "pages": pages}
    if design:
        args["design"] = design
    r = log.call("aos_core_design_graph", args, timeout_s=400)
    if r.get("status") != "SUCCESS":
        raise RuntimeError("aos_core_design_graph: " + error_text(r) + (" · " + "; ".join(r.get("errors") or [])[:400] if r.get("errors") else ""))
    nd = r.get("design") or {}
    _step(emit, "design", "done", t(lang, "그래프 설계", "graph design"),
          f"{len(nd.get('nodes') or [])} nodes · {len(nd.get('edges') or [])} edges" + (f" · {len(r.get('warnings') or [])} warnings" if r.get("warnings") else ""), _ms(s))
    results: List[Dict[str, Any]] = []

    def exec_sql(item: Dict[str, Any]) -> bool:
        s1 = time.perf_counter()
        rr = log.call("bigquery_execute_sql", {"project": env["project"], "sql": item["sql"], "location": env["region"], "timeout_ms": 60000,
                                               "labels": {"datacloud": "jetski", "app": "aos-starter"}}, timeout_s=90, label=item["title"])
        ok = rr.get("status") == "SUCCESS"
        results.append({"id": item["id"], "title": item["title"], "ok": ok, "ms": _ms(s1), "error": "" if ok else error_text(rr)[:500]})
        _step(emit, item["id"], "done" if ok else "error", item["title"], "" if ok else error_text(rr)[:200], _ms(s1))
        return ok

    def exec_load(item: Dict[str, Any]) -> bool:
        s1 = time.perf_counter()
        rr = log.call("bigquery_load_table", {"project": env["project"], "dataset": env["dataset"], "table": item["table"], "schema": item["schema"],
                                              "rows": item["rows"], "location": env["region"], "timeout_s": 120}, timeout_s=150, label=item["title"])
        ok = rr.get("status") == "SUCCESS"
        results.append({"id": item["id"], "title": item["title"], "ok": ok, "ms": _ms(s1), "error": "" if ok else error_text(rr)[:500]})
        _step(emit, item["id"], "done" if ok else "error", item["title"], "" if ok else error_text(rr)[:200], _ms(s1))
        return ok

    stmts, loads = r.get("statements") or [], r.get("loads") or []
    node_stmts = [x for x in stmts if x["kind"] == "node_table"]
    edge_stmts = [x for x in stmts if x["kind"] != "node_table"]
    node_loads = [x for x in loads if x["kind"] == "node_rows"]
    edge_loads = [x for x in loads if x["kind"] != "node_rows"]
    with ThreadPoolExecutor(max_workers=4) as ex:
        list(ex.map(identity.carry(exec_sql), node_stmts))
        list(ex.map(identity.carry(exec_load), node_loads))
        list(ex.map(identity.carry(exec_sql), edge_stmts))
        list(ex.map(identity.carry(exec_load), edge_loads))
    failed = [x for x in results if not x["ok"]]
    graph_ready, graph_error = False, ""
    gd = r.get("graph_ddl") or {}
    if not failed and gd.get("sql"):
        s1 = time.perf_counter()
        rr = log.call("bigquery_execute_sql", {"project": env["project"], "sql": gd["sql"], "location": env["region"], "timeout_ms": 60000,
                                               "labels": {"datacloud": "jetski", "app": "aos-starter"}}, timeout_s=90, label="CREATE PROPERTY GRAPH")
        graph_ready = rr.get("status") == "SUCCESS"
        graph_error = "" if graph_ready else error_text(rr)[:600]
        hint = ""
        if not graph_ready and ("412" in graph_error or "reservation" in graph_error.lower() or "enterprise" in graph_error.lower()):
            hint = t(lang, " — BigQuery Graph는 Enterprise 예약이 필요합니다. 노드/엣지 테이블은 만들어졌으므로 에이전트는 SQL로 동작합니다.",
                     " — BigQuery Graph needs an Enterprise reservation. Node/edge tables exist, so agents fall back to SQL.")
        results.append({"id": "graph", "title": gd.get("title", "graph"), "ok": graph_ready, "ms": _ms(s1), "error": graph_error})
        _step(emit, "graph", "done" if graph_ready else "warn", gd.get("title", "graph"), (graph_error[:200] + hint) if not graph_ready else env["graph_name"], _ms(s1))
    verify: List[Dict[str, Any]] = []
    if graph_ready:
        for q in r.get("verify") or []:
            s1 = time.perf_counter()
            rr = log.call("bigquery_execute_sql", {"project": env["project"], "sql": q["sql"], "location": env["region"],
                                                   "labels": {"datacloud": "jetski"}}, timeout_s=70, label=q["title"])
            ok = rr.get("status") == "SUCCESS"
            rows = rr.get("rows") or []
            verify.append({**q, "ok": ok, "rows": rows[:8], "row_count": len(rows), "ms": _ms(s1), "error": "" if ok else error_text(rr)[:300]})
        good = sum(1 for v in verify if v["ok"])
        _step(emit, "verify", "done" if good == len(verify) else "warn", t(lang, "검증 GQL", "verification GQL"), f"{good}/{len(verify)}")
    counts = {}
    for v in verify:
        if v.get("kind") == "count" and v.get("rows"):
            counts[v["title"].split("·")[-1].strip()] = v["rows"][0].get("cnt")
    plan = {"design": nd, "design_raw": r.get("design_raw"), "schema": r.get("schema"), "statements": stmts, "graph_ddl": gd,
            "loads": [{k: v for k, v in x.items() if k != "rows"} | {"row_count": len(x.get("rows") or [])} for x in loads],
            "verify": verify, "results": results, "warnings": r.get("warnings") or [], "errors": r.get("errors") or [],
            "stats": r.get("stats"), "graph_ready": graph_ready, "graph_error": graph_error, "node_counts": counts, "at": now_iso()}
    put_json(log, b, pf + "graph/plan.json", plan)
    put_text(log, b, pf + "graph/statements.sql", "\n\n".join(f"-- {x['title']}\n{x['sql']};" for x in stmts + ([gd] if gd else [])),
             "text/plain; charset=utf-8")
    ws.setdefault("summary", {})["graph"] = {"name": env["graph_name"], "fq": f"{env['project']}.{env['dataset']}.{env['graph_name']}",
                                             "nodes": len(nd.get("nodes") or []), "edges": len(nd.get("edges") or []),
                                             "ready": graph_ready, "mode": "gql" if graph_ready else "sql", "failed": len(failed)}
    if failed:
        raise RuntimeError(t(lang, f"그래프 테이블 {len(failed)}개 실패: ", f"{len(failed)} graph tables failed: ") + "; ".join(f"{x['title']}: {x['error'][:160]}" for x in failed[:3]))
    tel = r.get("telemetry") or {}
    return {"nodes": len(nd.get("nodes") or []), "edges": len(nd.get("edges") or []), "graph_ready": graph_ready,
            "graph_error": graph_error[:300], "verify_ok": sum(1 for v in verify if v["ok"]), "verify_total": len(verify),
            "warnings": (r.get("warnings") or [])[:6], "llm_ms": tel.get("ms")}


# ================================================================================================ S5 eval
def stage_eval(ws: Dict[str, Any], log: McpLog, emit: Emit, cq_ids: Optional[List[str]] = None, workers: int = 4) -> Dict[str, Any]:
    lang, env = ws.get("lang", "ko"), ws["env"]
    b, pf = env["bucket"], prefix(ws["ws_id"])
    cqs = get_json(log, b, pf + "cqs.json", []) or []
    if cq_ids:
        cqs = [c for c in cqs if c.get("id") in cq_ids]
    if not cqs:
        raise RuntimeError(t(lang, "CQ가 없습니다 — S2를 먼저 실행하거나 평가 탭에서 CQ를 추가하세요", "no CQs — run S2 or add CQs in the Evaluate tab"))
    ctx = agent_mod.load_context(ws, log)
    built = {"wiki": bool(ctx["pages"]), "graph": bool(ctx["plan"].get("schema")), "hybrid": bool(ctx["pages"] or ctx["plan"].get("schema"))}
    results: List[Dict[str, Any]] = []

    def one(cq: Dict[str, Any]) -> Dict[str, Any]:
        ag = cq.get("agent") or "hybrid"
        if not built.get(ag):
            ag = "hybrid" if built["hybrid"] else ag
        s1 = time.perf_counter()
        quiet = McpLog("eval", None)
        res = agent_mod.run(ws, ag, cq["question"], None, ctx, quiet)
        j = quiet.call("aos_core_judge", {**_kh_common(ws), "question": cq["question"], "reference_answer": cq.get("reference_answer", ""),
                                             "key_facts": cq.get("key_facts") or [], "answer": res.get("answer", "")}, timeout_s=120)
        log.calls.extend(quiet.calls)
        row = {"id": cq.get("id"), "question": cq["question"], "type": cq.get("type"), "agent": ag, "status": res.get("status"),
               "answer": res.get("answer", ""), "reference_answer": cq.get("reference_answer", ""), "key_facts": cq.get("key_facts") or [],
               "score": j.get("score", 0.0) if j.get("status") == "SUCCESS" else 0.0, "verdict": j.get("verdict", "ERROR"),
               "method": j.get("method", ""), "judge": {k: j.get(k) for k in ("deterministic", "llm")}, "steps": len(res.get("steps") or []),
               "ms": _ms(s1), "tokens_out": (res.get("telemetry") or {}).get("tokens_out", 0)}
        emit({"type": "cq", **{k: row[k] for k in ("id", "question", "agent", "status", "score", "verdict", "ms")}})
        return row
    s = time.perf_counter()
    with ThreadPoolExecutor(max_workers=max(1, workers)) as ex:
        results = list(ex.map(identity.carry(one), cqs))
    total = len(results)
    score = round(100 * sum(r["score"] for r in results) / total, 1) if total else 0.0
    run = {"at": now_iso(), "ws_id": ws["ws_id"], "score": score, "total": total, "passed": sum(1 for r in results if r["score"] >= 1),
           "partial": sum(1 for r in results if 0 < r["score"] < 1), "ms": _ms(s), "results": results,
           "by_agent": {a: round(100 * sum(r["score"] for r in results if r["agent"] == a) / max(1, sum(1 for r in results if r["agent"] == a)), 1)
                        for a in sorted({r["agent"] for r in results})}}
    stamp = run["at"].replace(":", "").replace("-", "")[:15]
    put_json(log, b, pf + f"runs/{stamp}.json", run)
    put_json(log, b, pf + "runs/latest.json", run)
    if not cq_ids:
        ws.setdefault("summary", {})["eval"] = {"score": score, "passed": run["passed"], "partial": run["partial"], "total": total, "at": run["at"]}
    return {"score": score, "passed": run["passed"], "partial": run["partial"], "total": total, "by_agent": run["by_agent"]}
