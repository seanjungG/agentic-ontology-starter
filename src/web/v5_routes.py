# Copyright (c) 2026 Sean Jung (seanjung@google.com). All Rights Reserved.
# Non-Commercial Use Only: Methodology & Docs under CC BY-NC-ND 4.0; Source Code under PolyForm Noncommercial License 1.0.0.
# Commercial use, paid consulting/SI/PoC delivery, or production deployment requires prior written permission from seanjung@google.com.

# -*- coding: utf-8 -*-
"""Starter v5 API (GOAL-233) — `/api/v5/*`. Every POST carries `identity` (runtime | token | impersonate) and a
workspace reference `ws: {bucket, ws_id}`; the server keeps no state (workspaces live in the user's bucket).

  GET  /api/v5/bootstrap?lang=        presets · env defaults · sample sources · settings
  POST /api/v5/identity               resolve identity → principal · expiry (token never echoed)
  POST /api/v5/check                  environment check (Core MCP · bucket · project · dataset · reservation · Gemini)
  POST /api/v5/setup-script           bash script that prepares the GCP environment
  POST /api/v5/ws/draft               new workspace id + default dataset
  POST /api/v5/upload                 one file → gs://bucket/aos/<ws>/raw/<name>
  POST /api/v5/gcs/list               documents · CSVs under a gs:// prefix
  POST /api/v5/bq/tables              tables of a BigQuery dataset
  POST /api/v5/ws/create · open · list · update
  POST /api/v5/build                  one stage (NDJSON)       {stage}
  POST /api/v5/data                   studio data              {what: [docs, tables, wiki, gates, graph, cqs, run, calls]}
  POST /api/v5/wiki/save · cqs/save   edits (wiki re-validated by Core MCP)
  POST /api/v5/graph/rebuild          S4 with an edited design (NDJSON)
  POST /api/v5/query · search         SQL/GQL console · search across wiki/docs/tables
  POST /api/v5/agent · eval           NDJSON
  POST /api/v5/export                 zip bundle
"""
from __future__ import annotations

import base64
import json
from typing import Any, Callable, Dict

from src import identity
from src.aos import agent as agent_mod
from src.aos import pipeline, sources, studio
from src.aos.ws import (McpLog, WsError, clean_env, clean_sources, default_dataset, env_defaults, error_text, load, new_workspace,
                        new_ws_id, now_iso, prefix, save)
from src.config import APP_VERSION, GITHUB_URL
from src.gcp_client import call_core_mcp_tool, runtime_settings

UPLOAD_MAX = sources.MAX_FILE_BYTES
STREAM_PATHS = {"/api/v5/build", "/api/v5/agent", "/api/v5/eval", "/api/v5/graph/rebuild"}


def bootstrap(lang: str) -> Dict[str, Any]:
    s = runtime_settings()
    return {"version": APP_VERSION, "lang": lang, "presets": studio.presets(lang), "env_defaults": env_defaults(),
            "sample": sources.sample_sources(lang), "core_mcp_url": s["core_mcp_url"], "github_url": GITHUB_URL,
            "model": s["vertex_model"], "impersonation": bool(__import__("os").environ.get("STARTER_IMPERSONATE_ALLOW", "").strip()),
            "stages": list(pipeline.STAGES), "max_upload_bytes": UPLOAD_MAX}


def _ws_ref(data: Dict[str, Any]) -> Dict[str, Any]:
    return studio.ws_from_request(data)


def handle_post(path: str, data: Dict[str, Any], send_json: Callable[[Any, int], None], stream: Callable[[Callable], None],
                send_bytes: Callable[[int, bytes, str, Dict[str, str]], None]) -> bool:
    """Returns True when the path was handled."""
    if not path.startswith("/api/v5/"):
        return False
    lang = "en" if data.get("lang") == "en" else "ko"
    try:
        ident = identity.resolve(data.get("identity"), lang)
    except identity.IdentityError as e:
        send_json(e.to_dict(lang), 401)
        return True
    pub = identity.public(ident)

    def guarded(fn: Callable[[], Any], code_ok: int = 200) -> None:
        with identity.bind(ident.get("token"), pub):
            try:
                send_json(fn(), code_ok)
            except WsError as e:
                send_json(e.to_dict(lang), 400 if e.code in ("CONFIG_ERROR", "BAD_REQUEST") else 404 if e.code == "WS_NOT_FOUND" else 403)
            except ValueError as e:
                send_json({"status": "BAD_REQUEST", "message": str(e)[:400]}, 400)

    def streamed(fn: Callable[[Callable], None]) -> None:
        def run(emit: Callable) -> None:
            with identity.bind(ident.get("token"), pub):
                try:
                    fn(emit)
                except WsError as e:
                    emit({"type": "error", **e.to_dict(lang)})
        stream(run)

    if path == "/api/v5/identity":
        guarded(lambda: {"status": "OK", "identity": pub})
    elif path == "/api/v5/check":
        guarded(lambda: studio.check_env(clean_env(data.get("env"), str(data.get("ws_id") or "ws-00000000-000000")), lang))
    elif path == "/api/v5/setup-script":
        guarded(lambda: {"status": "OK", "script": studio.setup_script(clean_env(data.get("env"), "ws-00000000-000000"), lang,
                                                                       str(data.get("sa_name") or "aos-starter")[:30])})
    elif path == "/api/v5/ws/draft":
        def draft() -> Dict[str, Any]:
            ws_id = new_ws_id()
            return {"status": "OK", "ws_id": ws_id, "dataset": default_dataset(ws_id)}
        guarded(draft)
    elif path == "/api/v5/upload":
        def upload() -> Dict[str, Any]:
            env = clean_env(data.get("env"), str(data.get("ws_id") or ""))
            ws_id = str(data.get("ws_id") or "")
            from src.aos.ws import check_ws_id, can_write
            check_ws_id(ws_id)
            ok, allowed = can_write(env)
            if not ok:
                raise WsError("WRITE_BLOCKED", f"데모 신원은 {allowed}에만 업로드할 수 있습니다", f"the demo identity may only upload to {allowed}")
            name = sources.safe_name(str(data.get("name") or ""))
            kind = sources.detect_kind(name)
            if not kind:
                raise ValueError("supported files: .md .txt .csv")
            raw = base64.b64decode(str(data.get("content_base64") or "")) if data.get("content_base64") else str(data.get("text") or "").encode("utf-8")
            if len(raw) > UPLOAD_MAX:
                raise ValueError(f"file too large ({len(raw)} > {UPLOAD_MAX} bytes)")
            text = raw.decode("utf-8", errors="replace")
            info: Dict[str, Any] = {}
            if kind == "table":
                parsed = sources.parse_csv(text)
                info = {"columns": parsed["columns"], "rows": len(parsed["rows"]), "sample": parsed["rows"][:5]}
            obj = f"{prefix(ws_id)}raw/{name}"
            log = McpLog("upload", None)
            r = log.call("storage_upload_object", {"bucket": env["bucket"], "name": obj, "content_base64": base64.b64encode(raw).decode("ascii"),
                                                   "content_type": "text/csv; charset=utf-8" if kind == "table" else "text/markdown; charset=utf-8"},
                         timeout_s=90)
            if r.get("status") != "SUCCESS":
                return {"status": "ERROR", "message": error_text(r)}
            uri = f"gs://{env['bucket']}/{obj}"
            entry = {"name": name if kind == "doc" else sources.table_name(name), "origin": "upload", "uri": uri}
            entry.update({"chars": len(text)} if kind == "doc" else {"rows": info.get("rows", 0)})
            return {"status": "OK", "kind": kind, "entry": entry, "info": info, "bytes": len(raw)}
        guarded(upload)
    elif path == "/api/v5/gcs/list":
        guarded(lambda: sources.list_gcs(McpLog("gcs", None), str(data.get("uri") or "")))
    elif path == "/api/v5/bq/tables":
        guarded(lambda: sources.bq_list_tables(McpLog("bq", None), str(data.get("dataset") or ""), str((data.get("env") or {}).get("region") or env_defaults()["region"])))
    elif path == "/api/v5/ws/create":
        def create() -> Dict[str, Any]:
            spec = {"scenario": data.get("scenario") or {}, "env": data.get("env") or {}, "sources": data.get("sources") or {}}
            ws = new_workspace(spec, lang)
            want = str(data.get("ws_id") or "")
            if want:
                from src.aos.ws import check_ws_id
                ws["ws_id"] = check_ws_id(want)
                ws["env"] = clean_env(data.get("env"), want)
            ok, allowed = pipeline.can_write(ws["env"])
            if not ok:
                raise WsError("WRITE_BLOCKED",
                              f"데모 신원(runtime)은 {allowed} 프로젝트에만 쓸 수 있습니다. 내 토큰 또는 SA를 입력하세요.",
                              f"The demo (runtime) identity may only write to {allowed}. Enter your token or SA.")
            r = save(ws, McpLog("create", None))
            if r.get("status") != "SUCCESS":
                return {"status": "ERROR", "message": error_text(r)}
            return {"status": "OK", "ws": ws}
        guarded(create)
    elif path == "/api/v5/ws/open":
        guarded(lambda: {"status": "OK", "ws": _ws_ref(data)})
    elif path == "/api/v5/ws/update":
        def update() -> Dict[str, Any]:
            ws = _ws_ref(data)
            if isinstance(data.get("scenario"), dict):
                sc = data["scenario"]
                for k in ("title", "customer", "objective", "question_type", "preset"):
                    if k in sc:
                        ws["scenario"][k] = str(sc[k])[:2000]
            if isinstance(data.get("sources"), dict):
                ws["sources"] = clean_sources(data["sources"])
            save(ws, McpLog("update", None))
            return {"status": "OK", "ws": ws}
        guarded(update)
    elif path == "/api/v5/ws/list":
        def wslist() -> Dict[str, Any]:
            bucket = str(data.get("bucket") or (data.get("env") or {}).get("bucket") or env_defaults()["bucket"])
            sources.parse_gs(f"gs://{bucket}/")
            r = call_core_mcp_tool("storage_list_objects", {"bucket": bucket, "prefix": "aos/"}, timeout_s=40)
            if r.get("status") != "SUCCESS":
                return {"status": "ERROR", "message": error_text(r)}
            items = [i for i in r.get("items") or [] if str(i.get("name", "")).endswith("/workspace.json") and str(i["name"]).count("/") == 2]
            items.sort(key=lambda i: i.get("updated", ""), reverse=True)
            out = []
            for it in items[:12]:
                try:
                    w = load(bucket, it["name"].split("/")[1])
                    out.append({"ws_id": w["ws_id"], "title": w["scenario"].get("title"), "updated_at": w.get("updated_at"), "lang": w.get("lang"),
                                "stages": {k: v.get("status") for k, v in (w.get("stages") or {}).items()}, "summary": w.get("summary")})
                except Exception:  # noqa: BLE001
                    continue
            return {"status": "OK", "bucket": bucket, "workspaces": out}
        guarded(wslist)
    elif path == "/api/v5/build":
        def build(emit: Callable) -> None:
            ws = _ws_ref(data)
            rec = pipeline.run_stage(ws, str(data.get("stage") or ""), emit)
            emit({"type": "result", "stage": data.get("stage"), "record": rec, "ws": ws})
        streamed(build)
    elif path == "/api/v5/graph/rebuild":
        def rebuild(emit: Callable) -> None:
            ws = _ws_ref(data)
            design = data.get("design") if isinstance(data.get("design"), dict) else None
            log = McpLog("graph", emit)
            from src.aos.pipeline import stage_graph
            from src.aos.ws import append_calls
            try:
                summary = stage_graph(ws, log, emit, design=design)
                rec = {"status": "done", "summary": summary, "at": now_iso(), "edited": bool(design)}
            except Exception as e:  # noqa: BLE001
                rec = {"status": "error", "error": f"{type(e).__name__}: {str(e)[:600]}", "at": now_iso()}
            ws.setdefault("stages", {})["graph"] = rec
            save(ws, log)
            append_calls(ws, log)
            emit({"type": "result", "stage": "graph", "record": rec, "ws": ws})
        streamed(rebuild)
    elif path == "/api/v5/data":
        what = [str(w) for w in (data.get("what") or ["wiki", "graph", "cqs"])][:10]
        guarded(lambda: {"status": "OK", **studio.studio_data(_ws_ref(data), what)})
    elif path == "/api/v5/wiki/save":
        guarded(lambda: studio.save_wiki(_ws_ref(data), [p for p in (data.get("pages") or []) if isinstance(p, dict)]))
    elif path == "/api/v5/cqs/save":
        guarded(lambda: studio.save_cqs(_ws_ref(data), [c for c in (data.get("cqs") or []) if isinstance(c, dict)]))
    elif path == "/api/v5/query":
        guarded(lambda: studio.run_query(_ws_ref(data), str(data.get("sql") or "")))
    elif path == "/api/v5/search":
        guarded(lambda: studio.search(_ws_ref(data), str(data.get("q") or ""), [s for s in (data.get("scopes") or ["wiki", "docs", "tables"])]))
    elif path == "/api/v5/agent":
        def ask(emit: Callable) -> None:
            ws = _ws_ref(data)
            q = str(data.get("question") or "").strip()[:2000]
            if not q:
                emit({"type": "error", "message": "question is empty"})
                return
            log = McpLog("agent", None)
            res = agent_mod.run(ws, str(data.get("agent") or "hybrid"), q, emit, None, log)
            res["mcp_calls"] = log.calls
            emit({"type": "result", **res})
        streamed(ask)
    elif path == "/api/v5/eval":
        def ev(emit: Callable) -> None:
            ws = _ws_ref(data)
            ids = [str(x) for x in (data.get("cq_ids") or [])]
            if ids:
                log = McpLog("eval", None)
                from src.aos.pipeline import stage_eval
                summary = stage_eval(ws, log, emit, cq_ids=ids)
                emit({"type": "result", "record": {"status": "done", "summary": summary}})
            else:
                rec = pipeline.run_stage(ws, "eval", emit)
                emit({"type": "result", "record": rec, "ws": ws})
        streamed(ev)
    elif path == "/api/v5/export":
        with identity.bind(ident.get("token"), pub):
            try:
                ws = _ws_ref(data)
                blob = studio.export_bundle(ws, lang)
            except WsError as e:
                send_json(e.to_dict(lang), 404)
                return True
        send_bytes(200, blob, "application/zip", {"Content-Disposition": f'attachment; filename="{ws["ws_id"]}.zip"'})
    else:
        send_json({"status": "NOT_FOUND", "path": path}, 404)
    return True
