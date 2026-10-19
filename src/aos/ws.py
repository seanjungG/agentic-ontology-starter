# Copyright (c) 2026 Sean Jung (seanjung@google.com). All Rights Reserved.
# Non-Commercial Use Only: Methodology & Docs under CC BY-NC-ND 4.0; Source Code under PolyForm Noncommercial License 1.0.0.
# Commercial use, paid consulting/SI/PoC delivery, or production deployment requires prior written permission from seanjung@google.com.

# -*- coding: utf-8 -*-
"""Workspace = the unit of a customer build (GOAL-233).

    gs://<bucket>/aos/<ws_id>/workspace.json   scenario · env · sources · stage status (no secrets)
                               raw/ parsed/ cqs.json wiki/ graph/ runs/ mcp_calls.jsonl

Every Core MCP call goes through `McpLog.call()`, which records tool · argument summary · status · ms so the
studio can show (and export) exactly which MCP calls with which parameters produced the result.
"""
from __future__ import annotations

import base64
import json
import re
import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple

from src import identity
from src.config import write_projects
from src.gcp_client import call_core_mcp_tool, runtime_settings

WS_VERSION = "aos-ws-1"
KST = timezone(timedelta(hours=9))
_RX = {
    "project": re.compile(r"^[a-z][a-z0-9-]{4,28}[a-z0-9]$"),
    "region": re.compile(r"^(?:[a-z]+-[a-z]+[0-9]{1,2}|US|EU)$"),
    "dataset": re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,1023}$"),
    "bucket": re.compile(r"^[a-z0-9][a-z0-9._-]{1,220}[a-z0-9]$"),
    "graph_name": re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,127}$"),
    "model": re.compile(r"^[a-z0-9][a-z0-9.\-]{1,62}$"),
    "vertex_location": re.compile(r"^(?:global|[a-z]+-[a-z]+[0-9]{1,2})$"),
    "ws_id": re.compile(r"^ws-[0-9]{8}-[a-z0-9]{6}$"),
}
LABELS = {"project": ("프로젝트", "Project"), "region": ("리전", "Region"), "dataset": ("데이터셋", "Dataset"),
          "bucket": ("버킷", "Bucket"), "graph_name": ("그래프 이름", "Graph name"), "model": ("모델", "Model"),
          "vertex_location": ("Vertex 위치", "Vertex location"), "ws_id": ("워크스페이스 ID", "Workspace ID")}
Emit = Callable[[Dict[str, Any]], None]


class WsError(ValueError):
    def __init__(self, code: str, ko: str, en: str, field: str = ""):
        super().__init__(en)
        self.code, self.ko, self.en, self.field = code, ko, en, field

    def to_dict(self, lang: str = "ko") -> Dict[str, Any]:
        return {"status": self.code, "field": self.field, "message": self.en if lang == "en" else self.ko}


def t(lang: str, ko: str, en: str) -> str:
    return en if lang == "en" else ko


def now_iso() -> str:
    return datetime.now(KST).strftime("%Y-%m-%dT%H:%M:%S+09:00")


def new_ws_id() -> str:
    return f"ws-{datetime.now(KST).strftime('%Y%m%d')}-{secrets.token_hex(3)}"


def default_dataset(ws_id: str) -> str:
    return "aos_" + ws_id.replace("ws-", "").replace("-", "_")


def env_defaults() -> Dict[str, str]:
    s = runtime_settings()
    return {"project": s["gcp_project_id"], "region": s["region"], "bucket": s["gcs_bucket"], "dataset": "",
            "graph_name": "AOS_ONTOLOGY_GRAPH", "model": s["vertex_model"], "vertex_location": s["vertex_location"]}


def clean_env(raw: Optional[Dict[str, Any]], ws_id: str = "") -> Dict[str, str]:
    d = env_defaults()
    env: Dict[str, str] = {}
    for k, v in d.items():
        val = str((raw or {}).get(k) or "").strip() or v
        if k == "dataset" and not val:
            val = default_dataset(ws_id) if ws_id else ""
        if val and not _RX[k].match(val):
            ko, en = LABELS[k]
            raise WsError("CONFIG_ERROR", f"{ko} 값 '{val}'의 형식이 올바르지 않습니다.", f"The {en} value '{val}' is not valid.", k)
        env[k] = val
    return env


def check_ws_id(ws_id: str) -> str:
    if not _RX["ws_id"].match(ws_id or ""):
        raise WsError("CONFIG_ERROR", f"워크스페이스 ID '{ws_id}' 형식 오류", f"invalid workspace id '{ws_id}'", "ws_id")
    return ws_id


def can_write(env: Dict[str, str]) -> Tuple[bool, str]:
    """User identities write wherever their IAM allows; the runtime identity only to STARTER_WRITE_PROJECTS."""
    info = identity.current()
    if info.get("mode") in ("token", "impersonate"):
        return True, ""
    allowed = write_projects()
    if "*" in allowed or env["project"] in allowed:
        return True, ""
    return False, ", ".join(allowed)


def prefix(ws_id: str) -> str:
    return f"aos/{ws_id}/"


# ------------------------------------------------------------------------------------------------ MCP call log
def _summ(v: Any, depth: int = 0) -> Any:
    """Argument summary for the call log: long strings / big arrays are shortened (the log must stay replayable
    for small arguments and readable for big ones)."""
    if isinstance(v, str):
        return v if len(v) <= 400 else f"{v[:300]}… (+{len(v) - 300} chars)"
    if isinstance(v, list):
        if len(v) > 6 or depth > 2:
            return {"_list": len(v), "head": [_summ(x, depth + 1) for x in v[:2]]}
        return [_summ(x, depth + 1) for x in v]
    if isinstance(v, dict):
        return {k: ("<redacted>" if "token" in k.lower() else _summ(x, depth + 1)) for k, x in v.items()}
    return v


class McpLog:
    def __init__(self, stage: str, emit: Optional[Emit] = None):
        self.stage, self.emit, self.calls = stage, emit, []

    def call(self, tool: str, args: Dict[str, Any], timeout_s: int = 120, label: str = "") -> Dict[str, Any]:
        t0 = time.perf_counter()
        res = call_core_mcp_tool(tool, args, timeout_s=timeout_s)
        ms = round((time.perf_counter() - t0) * 1000)
        status = str(res.get("status") or "ERROR")
        rec = {"ts": now_iso(), "stage": self.stage, "tool": tool, "args": _summ(args), "status": status, "ms": ms}
        if status != "SUCCESS":
            rec["error"] = error_text(res)[:400]
        self.calls.append(rec)
        if self.emit:
            self.emit({"type": "mcp", "tool": tool, "status": status, "ms": ms, "label": label, "error": rec.get("error", "")})
        return res


def error_text(res: Dict[str, Any]) -> str:
    err = res.get("error")
    if isinstance(err, dict):
        return str(err.get("message") or err)
    return str(err or res.get("message") or res.get("status") or "")


# ------------------------------------------------------------------------------------------------ GCS objects
def put_text(log: McpLog, bucket: str, name: str, text: str, content_type: str = "application/json; charset=utf-8") -> Dict[str, Any]:
    return log.call("storage_upload_object", {"bucket": bucket, "name": name,
                                              "content_base64": base64.b64encode(text.encode("utf-8")).decode("ascii"),
                                              "content_type": content_type}, timeout_s=60, label=f"gs://{bucket}/{name}")


def put_json(log: McpLog, bucket: str, name: str, obj: Any) -> Dict[str, Any]:
    return put_text(log, bucket, name, json.dumps(obj, ensure_ascii=False, indent=1, default=str))


def get_text(log: Optional[McpLog], bucket: str, name: str) -> Tuple[int, str]:
    args = {"bucket": bucket, "name": name}
    res = log.call("storage_read_object", args, timeout_s=40, label=f"gs://{bucket}/{name}") if log else \
        call_core_mcp_tool("storage_read_object", args, timeout_s=40)
    if res.get("status") != "SUCCESS":
        err = res.get("error") if isinstance(res.get("error"), dict) else {}
        return int(err.get("http_status") or res.get("http_code") or 500), error_text(res)
    if "text" in res:
        return 200, str(res.get("text") or "")
    if "content_base64" in res:
        return 200, base64.b64decode(str(res.get("content_base64") or "")).decode("utf-8", errors="replace")
    return 200, ""


def get_json(log: Optional[McpLog], bucket: str, name: str, default: Any = None) -> Any:
    code, txt = get_text(log, bucket, name)
    if code != 200:
        return default
    try:
        return json.loads(txt)
    except ValueError:
        return default


# ------------------------------------------------------------------------------------------------ workspace
def new_workspace(spec: Dict[str, Any], lang: str) -> Dict[str, Any]:
    ws_id = new_ws_id()
    env = clean_env(spec.get("env"), ws_id)
    sc = spec.get("scenario") or {}
    qtype = str(sc.get("question_type") or "W3").upper()
    return {
        "version": WS_VERSION, "ws_id": ws_id, "created_at": now_iso(), "updated_at": now_iso(),
        "lang": "en" if lang == "en" else "ko",
        "scenario": {"preset": str(sc.get("preset") or "custom")[:40], "title": str(sc.get("title") or "")[:200],
                     "customer": str(sc.get("customer") or "")[:200], "objective": str(sc.get("objective") or "")[:2000],
                     "question_type": qtype if qtype in ("W1", "W2", "W3") else "W3"},
        "env": env,
        "identity": identity.current(),
        "sources": clean_sources(spec.get("sources") or {}),
        "stages": {}, "summary": {},
    }


def clean_sources(src: Dict[str, Any]) -> Dict[str, Any]:
    docs, tables = [], []
    for d in (src.get("docs") or [])[:40]:
        if isinstance(d, dict) and d.get("origin") in ("upload", "gcs", "sample") and (d.get("uri") or d.get("path")):
            docs.append({"name": str(d.get("name") or "")[:200], "origin": d["origin"], "uri": str(d.get("uri") or d.get("path"))[:500],
                         "chars": int(d.get("chars") or 0)})
    for tb in (src.get("tables") or [])[:40]:
        if isinstance(tb, dict) and tb.get("origin") in ("upload", "gcs", "sample", "bigquery") and (tb.get("uri") or tb.get("fq") or tb.get("path")):
            tables.append({"name": re.sub(r"[^A-Za-z0-9_]", "_", str(tb.get("name") or ""))[:120], "origin": tb["origin"],
                           "uri": str(tb.get("uri") or tb.get("path") or "")[:500], "fq": str(tb.get("fq") or "")[:300],
                           "rows": int(tb.get("rows") or 0)})
    return {"docs": docs, "tables": tables, "sample": str(src.get("sample") or "")[:20]}


def load(bucket: str, ws_id: str, log: Optional[McpLog] = None) -> Dict[str, Any]:
    check_ws_id(ws_id)
    ws = get_json(log, bucket, prefix(ws_id) + "workspace.json")
    if not isinstance(ws, dict) or ws.get("ws_id") != ws_id:
        raise WsError("WS_NOT_FOUND", f"gs://{bucket}/{prefix(ws_id)}workspace.json 을 읽을 수 없습니다.",
                      f"Cannot read gs://{bucket}/{prefix(ws_id)}workspace.json.")
    return ws


def save(ws: Dict[str, Any], log: McpLog) -> Dict[str, Any]:
    ws["updated_at"] = now_iso()
    return put_json(log, ws["env"]["bucket"], prefix(ws["ws_id"]) + "workspace.json", ws)


def append_calls(ws: Dict[str, Any], log: McpLog) -> None:
    """Appends this stage's MCP calls to mcp_calls.jsonl (read → append → write)."""
    if not log.calls:
        return
    bucket, name = ws["env"]["bucket"], prefix(ws["ws_id"]) + "mcp_calls.jsonl"
    code, old = get_text(None, bucket, name)
    lines = (old.rstrip("\n") + "\n") if code == 200 and old.strip() else ""
    lines += "\n".join(json.dumps(c, ensure_ascii=False, default=str) for c in log.calls) + "\n"
    call_core_mcp_tool("storage_upload_object", {"bucket": bucket, "name": name, "text": lines,
                                                 "content_type": "application/x-ndjson; charset=utf-8"}, timeout_s=60)


def read_calls(bucket: str, ws_id: str) -> List[Dict[str, Any]]:
    code, txt = get_text(None, bucket, prefix(ws_id) + "mcp_calls.jsonl")
    if code != 200:
        return []
    out = []
    for line in txt.splitlines():
        try:
            out.append(json.loads(line))
        except ValueError:
            continue
    return out
