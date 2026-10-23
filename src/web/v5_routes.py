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
  POST /api/v5/upload                 one file → gs://bucket/aos/<ws>/raw/<name> (pdf/office/html → converted/<stem>.md)
  POST /api/v5/convert                convert a gs:// PDF/Office/HTML document (Core MCP mcp_knowhow_convert_document)
  POST /api/v5/catalog · template     flow & service catalog · build template (Core MCP mcp_knowhow_catalog / compose_template)
  POST /api/v5/drive/list · import    Google Drive folder listing · import (+ conversion) via Core MCP drive_*
  POST /api/v5/classify · types/save  document types + wiki strategy (mcp_knowhow_classify_documents) · user confirmation
  POST /api/v5/deploy/plan            deployment readiness + steps (mcp_knowhow_deploy_plan)
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
from src.aos import intake, pipeline, sources, studio
from src.aos.ws import (McpLog, WsError, clean_env, clean_sources, clean_template, default_dataset, env_defaults, error_text, load,
                        new_workspace, new_ws_id, now_iso, save)
from src.config import APP_VERSION, GITHUB_URL
from src.gcp_client import call_core_mcp_tool, runtime_settings

UPLOAD_MAX = intake.MAX_CONVERT_BYTES  # GOAL-243: binary documents up to 12 MB (converted by Core MCP)
STREAM_PATHS = {"/api/v5/build", "/api/v5/agent", "/api/v5/eval", "/api/v5/graph/rebuild"}


def bootstrap(lang: str) -> Dict[str, Any]:
    s = runtime_settings()
    return {"version": APP_VERSION, "lang": lang, "presets": studio.presets(lang), "env_defaults": env_defaults(),
            "sample": sources.sample_sources(lang), "core_mcp_url": s["core_mcp_url"], "github_url": GITHUB_URL,
            "model": s["vertex_model"], "impersonation": bool(__import__("os").environ.get("STARTER_IMPERSONATE_ALLOW", "").strip()),
            "stages": list(pipeline.STAGES), "max_upload_bytes": UPLOAD_MAX, "upload_ext": list(intake.ALL_UPLOAD_EXT)}


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
                send_json(e.to_dict(lang), 400 if e.code in ("CONFIG_ERROR", "BAD_REQUEST") else 404 if e.code == "WS_NOT_FOUND"
                          else 501 if e.code == "MCP_UPDATE_NEEDED" else 403)
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
    elif path == "/api/v5/upload":  # GOAL-243: md/txt/csv as before · pdf/docx/pptx/xlsx/html → Core MCP conversion
        guarded(lambda: intake.upload(data, lang))
    elif path == "/api/v5/convert":
        guarded(lambda: intake.convert_gcs(data, lang))
    elif path == "/api/v5/catalog":
        guarded(lambda: intake.catalog(lang))
    elif path == "/api/v5/template":
        guarded(lambda: intake.template(data, lang))
    elif path == "/api/v5/drive/list":
        guarded(lambda: intake.drive_list(data))
    elif path == "/api/v5/drive/import":
        guarded(lambda: intake.drive_import(data, lang))
    elif path == "/api/v5/classify":
        guarded(lambda: intake.classify(data, lang))
    elif path == "/api/v5/types/save":
        def types_save() -> Dict[str, Any]:
            decisions = [d for d in (data.get("decisions") or []) if isinstance(d, dict)][:40]
            ref = data.get("ws") if isinstance(data.get("ws"), dict) else {}
            if ref.get("ws_id") and ref.get("bucket"):  # workspace exists → persist (sources + doc_types.json)
                ws = _ws_ref(data)
                log = McpLog("types", None)
                intake.save_types(ws, decisions, log)
                r = save(ws, log)
                if r.get("status") != "SUCCESS":
                    return {"status": "ERROR", "message": error_text(r)}
                return {"status": "OK", "persisted": True, "sources": ws["sources"], "ws": ws}
            src = clean_sources(data.get("sources") or {})  # before the workspace exists: merge only, client keeps it
            return {"status": "OK", "persisted": False, "sources": clean_sources(intake.apply_types(src, decisions))}
        guarded(types_save)
    elif path == "/api/v5/deploy/plan":
        guarded(lambda: intake.deploy_plan(_ws_ref(data), data, str(pub.get("mode") or "runtime"), runtime_settings()["core_mcp_url"], lang))
    elif path == "/api/v5/gcs/list":
        guarded(lambda: sources.list_gcs(McpLog("gcs", None), str(data.get("uri") or "")))
    elif path == "/api/v5/bq/tables":
        guarded(lambda: sources.bq_list_tables(McpLog("bq", None), str(data.get("dataset") or ""), str((data.get("env") or {}).get("region") or env_defaults()["region"])))
    elif path == "/api/v5/ws/create":
        def create() -> Dict[str, Any]:
            spec = {"scenario": data.get("scenario") or {}, "env": data.get("env") or {}, "sources": data.get("sources") or {},
                    "template": data.get("template") or {}}
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
            if isinstance(data.get("template"), dict):
                ws["template"] = clean_template(data["template"])
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
