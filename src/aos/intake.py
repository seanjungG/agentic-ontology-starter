# Copyright (c) 2026 Sean Jung (seanjung@google.com). All Rights Reserved.
# Non-Commercial Use Only: Methodology & Docs under CC BY-NC-ND 4.0; Source Code under PolyForm Noncommercial License 1.0.0.
# Commercial use, paid consulting/SI/PoC delivery, or production deployment requires prior written permission from seanjung@google.com.

# -*- coding: utf-8 -*-
"""Starter v6 intake (GOAL-243): flow & service catalog · template · data intake (local · GCS · Drive) · conversion · types · deploy plan.

This module only ORCHESTRATES. Every piece of method know-how is a Core MCP call:
    aos_core_catalog · aos_core_compose_template      flow & service catalog, build template
    aos_core_convert_document                             PDF / Office / HTML → Markdown + conversion fidelity
    aos_core_classify_documents                           document type + wiki strategy (direct · typed · reconvert)
    aos_core_deploy_plan                                  deployment readiness + next steps
    drive_list_files · drive_get_file · storage_*            data plane, with the request identity's token
Results are written to the user's bucket:  gs://<bucket>/aos/<ws>/raw/<original>  ·  converted/<name>.md  ·  converted/<name>.pdf
"""
from __future__ import annotations

import base64
import os
import re
from typing import Any, Dict, List, Optional

from src.aos import sources as S
from src.aos.ws import McpLog, WsError, can_write, check_ws_id, clean_env, error_text, get_json, prefix, put_json, put_text, t

BINARY_DOC_EXT = (".pdf", ".docx", ".pptx", ".xlsx", ".html", ".htm", ".mhtml", ".mht")  # GOAL-249: + web archives (Core MCP 1.8)
TEXT_DOC_EXT = (".md", ".markdown", ".txt")
ALL_UPLOAD_EXT = BINARY_DOC_EXT + TEXT_DOC_EXT + (".csv",)
MAX_CONVERT_BYTES = 12 * 1024 * 1024
_CT = {".pdf": "application/pdf", ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
       ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
       ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", ".html": "text/html; charset=utf-8",
       ".htm": "text/html; charset=utf-8", ".mhtml": "multipart/related", ".mht": "multipart/related",
       ".md": "text/markdown; charset=utf-8", ".markdown": "text/markdown; charset=utf-8",
       ".txt": "text/plain; charset=utf-8", ".csv": "text/csv; charset=utf-8"}


class McpMissing(WsError):
    def __init__(self, tool: str):
        super().__init__("MCP_UPDATE_NEEDED", f"연결된 Core MCP에 {tool} 도구가 없습니다 — Core MCP 1.5.0 이상이 필요합니다 (CORE_MCP_URL 확인)",
                         f"the connected Core MCP has no {tool} tool — Core MCP 1.5.0 or later is required (check CORE_MCP_URL)")


def _call(log: McpLog, tool: str, args: Dict[str, Any], timeout_s: int = 120, label: str = "") -> Dict[str, Any]:
    r = log.call(tool, args, timeout_s=timeout_s, label=label)
    msg = error_text(r).lower() if r.get("status") != "SUCCESS" else ""
    if r.get("status") != "SUCCESS" and ("unknown" in msg and tool in msg or "unknown tool" in msg or "not found" in msg and tool in msg):
        raise McpMissing(tool)
    return r


def ext_of(name: str) -> str:
    return os.path.splitext(str(name or "").lower())[1]


def kind_of(name: str) -> Optional[str]:
    e = ext_of(name)
    if e in TEXT_DOC_EXT:
        return "doc"
    if e in BINARY_DOC_EXT:
        return "convert"
    if e == ".csv":
        return "table"
    return None


def _kh(env: Dict[str, Any], lang: str) -> Dict[str, Any]:
    return {"project": env["project"], "model": env.get("model") or "", "location": env.get("vertex_location") or "global", "lang": lang}


def lang_only(obj: Any, lang: str) -> Any:
    """Drop the other language's labels (`ko`/`en`, `*_ko`/`*_en`) from bilingual Core MCP catalogs (e.g. doc_types), so an
    EN response carries no Hangul and a KO response no duplicate English labels. The UI localizes ids via studio_i18n.json."""
    other = "ko" if lang == "en" else "en"
    if isinstance(obj, dict):
        return {k: lang_only(v, lang) for k, v in obj.items() if k != other and not k.endswith("_" + other)}
    if isinstance(obj, list):
        return [lang_only(v, lang) for v in obj]
    return obj


# ------------------------------------------------------------------------------------------------ catalog · template
def catalog(lang: str) -> Dict[str, Any]:
    r = _call(McpLog("catalog", None), "aos_core_catalog", {"lang": lang}, timeout_s=30)
    if r.get("status") != "SUCCESS":
        return {"status": "ERROR", "message": error_text(r)}
    return {"status": "OK", **lang_only({k: r.get(k) for k in ("flows", "services", "targets", "sources", "doc_types", "catalog_version")}, lang)}


def template(data: Dict[str, Any], lang: str) -> Dict[str, Any]:
    env = data.get("env") or {}
    args = {"lang": lang, "flow": data.get("flow"), "services": data.get("services") or [], "target": data.get("target") or "sandbox",
            "project": env.get("project", ""), "region": env.get("region", ""), "bucket": env.get("bucket", ""), "ws_id": data.get("ws_id", ""),
            "model": env.get("model", ""), "sa_name": data.get("sa_name") or "aos-starter",
            "dataset": env.get("dataset", ""), "graph_name": env.get("graph_name", ""), "identity_mode": data.get("identity_mode") or ""}
    r = _call(McpLog("template", None), "aos_core_compose_template", args, timeout_s=30)
    if r.get("status") != "SUCCESS":
        return {"status": "ERROR", "message": error_text(r)}
    return {"status": "OK", **{k: v for k, v in r.items() if k not in ("status", "tool", "version")}}


# ------------------------------------------------------------------------------------------------ conversion
def _put_bytes(log: McpLog, bucket: str, name: str, data: bytes, ct: str) -> Dict[str, Any]:
    return log.call("storage_upload_object", {"bucket": bucket, "name": name, "content_base64": base64.b64encode(data).decode("ascii"),
                                              "content_type": ct}, timeout_s=120, label=name)


def convert_and_store(log: McpLog, env: Dict[str, Any], ws_id: str, name: str, data: bytes, lang: str, origin: str,
                      source_uri: str = "", extra_pdf: Optional[bytes] = None, pdf_mode: str = "auto") -> Dict[str, Any]:
    """Convert one binary document via Core MCP and store converted/<stem>.md (+ .pdf when available). Returns a doc entry."""
    if len(data) > MAX_CONVERT_BYTES:
        raise ValueError(f"file too large for conversion ({len(data)} > {MAX_CONVERT_BYTES} bytes)")
    r = _call(log, "aos_core_convert_document", {**_kh(env, lang), "name": name, "content_base64": base64.b64encode(data).decode("ascii"),
                                                     "pdf_mode": pdf_mode}, timeout_s=330, label=name)
    if r.get("status") != "SUCCESS":
        raise RuntimeError(f"{name}: {error_text(r)}")
    pf = prefix(ws_id)
    stem = re.sub(r"\.[A-Za-z0-9]+$", "", S.safe_name(name))
    md_obj = f"{pf}converted/{stem}.md"
    w = put_text(log, env["bucket"], md_obj, r.get("markdown") or "", "text/markdown; charset=utf-8")
    if w.get("status") != "SUCCESS":
        raise RuntimeError(f"{md_obj}: {error_text(w)}")
    pdf_uri = ""
    pdf_bytes = data if ext_of(name) == ".pdf" else extra_pdf
    if pdf_bytes and ext_of(name) != ".pdf":
        po = f"{pf}converted/{stem}.pdf"
        if _put_bytes(log, env["bucket"], po, pdf_bytes, "application/pdf").get("status") == "SUCCESS":
            pdf_uri = f"gs://{env['bucket']}/{po}"
    elif ext_of(name) == ".pdf":
        pdf_uri = source_uri
    det = r.get("detected") or {}
    fid = r.get("fidelity") or {}
    entry = {"name": f"{stem}.md", "origin": origin, "uri": f"gs://{env['bucket']}/{md_obj}", "chars": len(r.get("markdown") or ""),
             "kind": det.get("type", ""), "strategy": det.get("strategy", ""),
             "conversion": {"source": source_uri, "source_ext": r.get("source_ext"), "method": r.get("method"), "fidelity": fid.get("score"),
                            "grade": fid.get("grade"), "fid_method": fid.get("method"), "token_recall": fid.get("token_recall"),
                            "number_recall": fid.get("number_recall"), "pages": (r.get("stats") or {}).get("pages"), "pdf": pdf_uri,
                            "confidence": det.get("confidence"), "reason": det.get("reason", ""), "notes": (r.get("notes") or [])[:4],
                            "structure": {k: (r.get("stats") or {}).get(k) for k in ("headings", "tables", "list_items")}}}
    tables: List[Dict[str, Any]] = []
    for sh in r.get("sheets_csv") or []:  # spreadsheets: each sheet also becomes a table source
        tname = S.table_name(f"{stem}_{sh['name']}")
        obj = f"{pf}raw/{tname}.csv"
        if put_text(log, env["bucket"], obj, sh["csv"], "text/csv; charset=utf-8").get("status") == "SUCCESS":
            tables.append({"name": tname, "origin": origin, "uri": f"gs://{env['bucket']}/{obj}", "rows": int(sh.get("rows") or 0)})
    return {"entry": entry, "tables": tables, "markdown_preview": (r.get("markdown") or "")[:4000], "fidelity": fid, "detected": det,
            "telemetry": r.get("telemetry") or {}}


def upload(data: Dict[str, Any], lang: str) -> Dict[str, Any]:
    env = clean_env(data.get("env"), str(data.get("ws_id") or ""))
    ws_id = check_ws_id(str(data.get("ws_id") or ""))
    ok, allowed = can_write(env)
    if not ok:
        raise WsError("WRITE_BLOCKED", f"데모 신원은 {allowed}에만 업로드할 수 있습니다", f"the demo identity may only upload to {allowed}")
    name = S.safe_name(str(data.get("name") or ""))
    kind = kind_of(name)
    if not kind:
        raise ValueError("supported files: " + " ".join(ALL_UPLOAD_EXT))
    raw = base64.b64decode(str(data.get("content_base64") or "")) if data.get("content_base64") else str(data.get("text") or "").encode("utf-8")
    if len(raw) > MAX_CONVERT_BYTES:
        raise ValueError(f"file too large ({len(raw)} > {MAX_CONVERT_BYTES} bytes)")
    log = McpLog("upload", None)
    obj = f"{prefix(ws_id)}raw/{name}"
    r = _put_bytes(log, env["bucket"], obj, raw, _CT.get(ext_of(name), "application/octet-stream"))
    if r.get("status") != "SUCCESS":
        return {"status": "ERROR", "message": error_text(r)}
    uri = f"gs://{env['bucket']}/{obj}"
    if kind == "table":
        parsed = S.parse_csv(raw.decode("utf-8", errors="replace"))
        return {"status": "OK", "kind": "table", "entry": {"name": S.table_name(name), "origin": "upload", "uri": uri, "rows": len(parsed["rows"])},
                "info": {"columns": parsed["columns"], "rows": len(parsed["rows"]), "sample": parsed["rows"][:5]}, "bytes": len(raw)}
    if kind == "doc":
        text = raw.decode("utf-8", errors="replace")
        return {"status": "OK", "kind": "doc", "entry": {"name": name, "origin": "upload", "uri": uri, "chars": len(text)}, "bytes": len(raw)}
    conv = convert_and_store(log, env, ws_id, name, raw, lang, "upload", uri, pdf_mode=str(data.get("pdf_mode") or "auto"))
    return {"status": "OK", "kind": "doc", "converted": True, **conv, "bytes": len(raw), "mcp_calls": log.calls}


def convert_gcs(data: Dict[str, Any], lang: str) -> Dict[str, Any]:
    """Convert a binary document that already lives in GCS (picked from the GCS tab)."""
    env = clean_env(data.get("env"), str(data.get("ws_id") or ""))
    ws_id = check_ws_id(str(data.get("ws_id") or ""))
    ok, allowed = can_write(env)
    if not ok:
        raise WsError("WRITE_BLOCKED", f"데모 신원은 {allowed}에만 쓸 수 있습니다", f"the demo identity may only write to {allowed}")
    uri = str(data.get("uri") or "")
    bucket, name = S.parse_gs(uri)
    log = McpLog("convert", None)
    r = log.call("storage_read_object", {"bucket": bucket, "name": name}, timeout_s=90, label=uri)
    if r.get("status") != "SUCCESS":
        return {"status": "ERROR", "message": error_text(r)}
    raw = base64.b64decode(r["content_base64"]) if r.get("content_base64") else str(r.get("text") or "").encode("utf-8")
    conv = convert_and_store(log, env, ws_id, os.path.basename(name), raw, lang, "gcs", uri, pdf_mode=str(data.get("pdf_mode") or "auto"))
    return {"status": "OK", "converted": True, **conv, "mcp_calls": log.calls}


# ------------------------------------------------------------------------------------------------ Google Drive
def drive_list(data: Dict[str, Any]) -> Dict[str, Any]:
    r = _call(McpLog("drive", None), "drive_list_files", {"url": str(data.get("url") or ""), "page_size": 100}, timeout_s=40)
    if r.get("status") != "SUCCESS":
        return drive_error(r)
    files = []
    for f in r.get("files") or []:
        mime = f.get("mimeType", "")
        k = "folder" if mime.endswith(".folder") else ("google_doc" if mime.startswith("application/vnd.google-apps.") else (kind_of(f.get("name", "")) or "other"))
        files.append({**f, "kind": k})
    return {"status": "OK", "files": files}


def drive_import(data: Dict[str, Any], lang: str) -> Dict[str, Any]:
    env = clean_env(data.get("env"), str(data.get("ws_id") or ""))
    ws_id = check_ws_id(str(data.get("ws_id") or ""))
    ok, allowed = can_write(env)
    if not ok:
        raise WsError("WRITE_BLOCKED", f"데모 신원은 {allowed}에만 쓸 수 있습니다", f"the demo identity may only write to {allowed}")
    log = McpLog("drive", None)
    r = _call(log, "drive_get_file", {"file_id": str(data.get("file_id") or ""), "export": "all"}, timeout_s=120)
    if r.get("status") != "SUCCESS":
        return drive_error(r)
    meta = r.get("file") or {}
    exports = r.get("exports") or []
    base = S.safe_name(meta.get("name") or "drive_file")
    stem = re.sub(r"\.[A-Za-z0-9]+$", "", base) if ext_of(base) in ALL_UPLOAD_EXT else base
    pf = prefix(ws_id)
    stored = []
    for ex in exports:
        e = ex.get("ext") or ext_of(base) or ""
        fname = f"{stem}{e}" if e else base
        raw = base64.b64decode(ex["content_base64"])
        if _put_bytes(log, env["bucket"], f"{pf}raw/{fname}", raw, ex.get("mime_type") or "application/octet-stream").get("status") == "SUCCESS":
            stored.append({"name": fname, "ext": e, "raw": raw, "uri": f"gs://{env['bucket']}/{pf}raw/{fname}"})
    if not stored:
        return {"status": "ERROR", "message": "nothing exported"}
    by_ext = {s["ext"]: s for s in stored}
    pdf = by_ext.get(".pdf")
    # Google Docs: native Markdown export + PDF; Slides: PPTX + PDF; Sheets: XLSX (+ CSV); binary files: as uploaded
    if ".md" in by_ext:
        md = by_ext[".md"]
        conv = convert_and_store(log, env, ws_id, md["name"], md["raw"], lang, "drive", md["uri"], extra_pdf=pdf["raw"] if pdf else None)
    else:
        main = next((s for s in stored if s["ext"] in (".pptx", ".xlsx", ".docx", ".html", ".htm")), None) or pdf or stored[0]
        k = kind_of(main["name"])
        if k == "table":
            return {"status": "OK", "kind": "table", "entry": {"name": S.table_name(main["name"]), "origin": "drive", "uri": main["uri"]}, "mcp_calls": log.calls}
        if k == "doc":
            text = main["raw"].decode("utf-8", errors="replace")
            return {"status": "OK", "kind": "doc", "entry": {"name": main["name"], "origin": "drive", "uri": main["uri"], "chars": len(text)}, "mcp_calls": log.calls}
        conv = convert_and_store(log, env, ws_id, main["name"], main["raw"], lang, "drive", main["uri"],
                                 extra_pdf=pdf["raw"] if pdf and main is not pdf else None)
    conv["entry"]["conversion"]["drive_id"] = meta.get("id")
    return {"status": "OK", "kind": "doc", "converted": True, **conv, "mcp_calls": log.calls}


# ------------------------------------------------------------------------------------------------ types · strategy
def classify(data: Dict[str, Any], lang: str) -> Dict[str, Any]:
    env = clean_env(data.get("env"), str(data.get("ws_id") or ""))
    docs = [d for d in ((data.get("sources") or {}).get("docs") or []) if isinstance(d, dict)][:40]
    if not docs:
        raise ValueError("no documents to classify")
    log = McpLog("classify", None)
    payload = []
    for i, d in enumerate(docs):
        try:
            text = S.read_source_text(log, str(d.get("uri") or ""))
        except Exception as e:  # noqa: BLE001
            text = f"(unreadable: {e})"
        conv = d.get("conversion") or {}
        payload.append({"doc_id": f"D{i + 1:02d}", "title": d.get("name", ""), "name": d.get("name", ""), "text": text[:60000],
                        "ext": conv.get("source_ext") or ext_of(d.get("name", "")), "fidelity": conv.get("fidelity"),
                        "user_type": (data.get("user_types") or {}).get(str(d.get("uri")), "")})
    r = _call(log, "aos_core_classify_documents", {**_kh(env, lang), "docs": payload, "use_llm": bool(data.get("use_llm"))}, timeout_s=120)
    if r.get("status") != "SUCCESS":
        return {"status": "ERROR", "message": error_text(r)}
    out = []
    for d, c in zip(docs, r.get("documents") or []):
        out.append({"uri": d.get("uri"), "name": d.get("name"), "type": c.get("type"), "confidence": c.get("confidence"), "strategy": c.get("strategy"),
                    "reason": c.get("reason"), "ask": c.get("ask"), "candidates": c.get("candidates"), "method": c.get("method"), "guide": c.get("guide"),
                    "fidelity": c.get("fidelity")})
    return {"status": "OK", "documents": out, "summary": r.get("summary"), "types": lang_only(r.get("types_catalog"), lang), "question": r.get("question"),
            "mcp_calls": log.calls}


# ------------------------------------------------------------------------------------------------ deploy
def deploy_plan(ws: Dict[str, Any], data: Dict[str, Any], identity_mode: str, core_mcp_url: str, lang: str) -> Dict[str, Any]:
    env = ws.get("env") or {}
    run = get_json(None, env.get("bucket", ""), prefix(ws["ws_id"]) + "runs/latest.json", None) or {}
    summary = dict(ws.get("summary") or {})
    if run and not summary.get("eval"):
        summary["eval"] = {"score": run.get("score"), "total": run.get("total"), "passed": run.get("passed")}
    args = {"lang": lang, "env": {k: env.get(k) for k in ("project", "region", "bucket", "dataset", "graph_name")}, "summary": summary,
            "target": data.get("target") or "cloud_run", "threshold": data.get("threshold") or 80, "identity_mode": identity_mode,
            "sandbox": (ws.get("template") or {}).get("target") == "sandbox", "service_name": data.get("service_name") or f"aos-agent-{ws['ws_id'][-6:]}",
            "workspace_uri": f"gs://{env.get('bucket')}/{prefix(ws['ws_id'])}workspace.json", "ws_id": ws["ws_id"], "core_mcp_url": core_mcp_url}
    r = _call(McpLog("deploy", None), "aos_core_deploy_plan", args, timeout_s=30)
    if r.get("status") != "SUCCESS":
        return {"status": "ERROR", "message": error_text(r)}
    return {"status": "OK", **{k: v for k, v in r.items() if k not in ("status", "tool", "version")}}


def apply_types(sources: Dict[str, Any], decisions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Merge user-confirmed type / strategy per document (keyed by uri) into a sources dict (returns the same dict)."""
    by = {str(d.get("uri")): d for d in decisions if isinstance(d, dict) and d.get("uri")}
    for d in (sources or {}).get("docs") or []:
        x = by.get(str(d.get("uri")))
        if not x:
            continue
        kind = re.sub(r"[^a-z]", "", str(x.get("type") or x.get("kind") or ""))[:20]
        if kind:
            d["kind"] = kind
        if x.get("strategy") in ("direct", "typed", "reconvert"):
            d["strategy"] = x["strategy"]
    return sources


def save_types(ws: Dict[str, Any], decisions: List[Dict[str, Any]], log: McpLog) -> Dict[str, Any]:
    """Persist the user-confirmed type / strategy per document into workspace sources (used by S1 → S3)."""
    apply_types(ws.setdefault("sources", {}), decisions)
    put_json(log, ws["env"]["bucket"], prefix(ws["ws_id"]) + "doc_types.json",
             [{k: d.get(k) for k in ("uri", "name", "type", "strategy", "confidence", "method")} for d in decisions if isinstance(d, dict)])
    return ws


def drive_error(r: Dict[str, Any]) -> Dict[str, Any]:
    msg = error_text(r)
    low = msg.lower()
    code = "DRIVE_ACCESS" if any(x in low for x in ("403", "404", "insufficient", "scope", "permission", "not found", "forbidden")) else "ERROR"
    return {"status": "ERROR", "code": code, "message": msg}


__all__ = ["catalog", "template", "upload", "convert_gcs", "drive_list", "drive_import", "classify", "deploy_plan", "save_types",
           "apply_types", "drive_error", "kind_of", "ALL_UPLOAD_EXT", "MAX_CONVERT_BYTES", "McpMissing", "t"]
