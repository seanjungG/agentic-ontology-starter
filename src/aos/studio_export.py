# Copyright (c) 2026 Sean Jung (seanjung@google.com). All Rights Reserved.
# Non-Commercial Use Only: Methodology & Docs under CC BY-NC-ND 4.0; Source Code under PolyForm Noncommercial License 1.0.0.
# Commercial use, paid consulting/SI/PoC delivery, or production deployment requires prior written permission from seanjung@google.com.

# -*- coding: utf-8 -*-
"""Starter workspace → Agentic Ontology Studio project folder (GOAL-249).

Reads a finished workspace (workspace.json · wiki/pages.json · graph/plan.json · cqs.json · runs/latest.json) through Core MCP,
calls `aos_core_export_studio_project` (deterministic, no LLM) and writes the returned bundle to a local folder
(`projects/<project_id>/` in the Studio repo). Optionally mirrors the OKF wiki bundles to GCS for the Studio Wiki Agent.
"""
from __future__ import annotations

import base64
import os
from typing import Any, Dict, List

from src.aos import sources as S
from src.aos.pipeline import get_json
from src.aos.ws import McpLog, WsError, error_text, prefix
from src.gcp_client import call_core_mcp_tool


def collect(ws: Dict[str, Any]) -> Dict[str, Any]:
    log = McpLog("export", None)
    b, pre = ws["env"]["bucket"], prefix(ws["ws_id"])
    cqs = get_json(log, b, pre + "cqs.json", []) or []
    if isinstance(cqs, dict):
        cqs = cqs.get("cqs") or cqs.get("items") or []
    docs: List[Dict[str, Any]] = []
    for d in (ws.get("sources") or {}).get("docs") or []:
        conv = d.get("conversion") or {}
        docs.append({"doc_id": S.doc_id(d["name"]), "title": os.path.splitext(d["name"])[0], "name": d["name"], "uri": d.get("uri"),
                     "kind": d.get("kind") or "", "chars": d.get("chars"), "fidelity": conv.get("fidelity")})
    tables = [{"name": t.get("name"), "fq": t.get("fq") or "", "uri": t.get("uri") or t.get("fq")}
              for t in (ws.get("sources") or {}).get("tables") or []]
    return {"workspace": ws, "pages": get_json(log, b, pre + "wiki/pages.json", []) or [], "plan": get_json(log, b, pre + "graph/plan.json", {}) or {},
            "cqs": cqs, "eval_run": get_json(log, b, pre + "runs/latest.json", {}) or {}, "docs": docs, "tables": tables}


def export(ws: Dict[str, Any], project_id: str, out_dir: str, *, labels: Dict[str, Any] | None = None, studio_url: str = "",
           gcs_prefix: str = "", upload: bool = False, lang: str = "ko") -> Dict[str, Any]:
    args = {**collect(ws), "project_id": project_id, "lang": lang, "labels": labels or {}, "studio_url": studio_url,
            "gcs_wiki_bucket": ws["env"]["bucket"], "gcs_wiki_prefix": gcs_prefix or f"studio_projects/{project_id}",
            "created_at": ws.get("updated_at") or ""}
    r = call_core_mcp_tool("aos_core_export_studio_project", args, timeout_s=120)
    if r.get("status") != "SUCCESS":
        raise WsError("EXPORT_FAILED", error_text(r))
    root = os.path.join(out_dir, project_id)
    for rel, content in r["files"].items():
        path = os.path.join(root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
    uploaded, failed = 0, []
    if upload:
        for o in r["gcs_objects"]:
            up = call_core_mcp_tool("storage_upload_object", {"bucket": o["bucket"], "name": o["name"], "content_type": "text/markdown; charset=utf-8"
                                    if o["name"].endswith(".md") else "application/json",
                                    "content_base64": base64.b64encode(r["files"][o["path"]].encode("utf-8")).decode("ascii")}, timeout_s=60)
            if up.get("status") == "SUCCESS":
                uploaded += 1
            else:
                failed.append(f"{o['name']}: {error_text(up)[:120]}")
    return {"root": root, "summary": r["summary"], "notes": r.get("notes") or [], "uploaded": uploaded, "upload_failed": failed}
