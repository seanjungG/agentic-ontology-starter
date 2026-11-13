# Copyright (c) 2026 Sean Jung (seanjung@google.com). All Rights Reserved.
# Non-Commercial Use Only: Methodology & Docs under CC BY-NC-ND 4.0; Source Code under PolyForm Noncommercial License 1.0.0.
# Commercial use, paid consulting/SI/PoC delivery, or production deployment requires prior written permission from seanjung@google.com.

# -*- coding: utf-8 -*-
"""
gcp_client.py
Real Google Cloud Platform REST Client for Agentic Ontology Starter:
- Connects to real BigQuery (`$GCP_PROJECT_ID.$BQ_DATASET_ID`) for SQL & SQL:2023 Property Graph GQL queries
- Connects to real Cloud Storage (`gs://$GCS_WIKI_BUCKET`) for 3-Layer OKF Wiki artifacts
- Connects to real Vertex AI (`$VERTEX_GEMINI_MODEL`, default `gemini-4-argon` on location `global`)
  for dynamic decomposition & grounded synthesis
- Calls the remote Platform Core MCP (`$CORE_MCP_URL`, JSON-RPC 2.0) — may live in another GCP project
- Zero external pip dependencies (uses standard library urllib + Metadata Server / gcloud token)

All resource ids come from environment variables; the defaults below are only the reference sample project.
"""

import base64
import json
import os
import ssl
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

DEFAULT_PROJECT_ID = os.environ.get("GCP_PROJECT_ID") or os.environ.get("GOOGLE_CLOUD_PROJECT") or "seanjung-agentic-starter"
DEFAULT_DATASET_ID = os.environ.get("BQ_DATASET_ID", "starter_ontology_dw")
DEFAULT_LOCATION = os.environ.get("BQ_LOCATION", "asia-northeast3")
DEFAULT_GCS_BUCKET = (
    os.environ.get("GCS_WIKI_BUCKET") or os.environ.get("GCS_BUCKET_NAME") or "seanjung-agentic-starter-ontology"
)
DEFAULT_GEMINI_MODEL = os.environ.get("VERTEX_GEMINI_MODEL", "gemini-4-argon")
DEFAULT_VERTEX_LOCATION = os.environ.get("VERTEX_LOCATION", "global")
# GOAL-228: gemini-4-argon thinkingLevel MEDIUM for chat/agent answers AND build/extraction (HIGH was 2-3x slower).
DEFAULT_THINKING_LEVEL = os.environ.get("VERTEX_THINKING_LEVEL", "MEDIUM").upper()
DEFAULT_BUILD_THINKING_LEVEL = os.environ.get("VERTEX_BUILD_THINKING_LEVEL", "MEDIUM").upper()
DEFAULT_GEMINI_TIMEOUT_S = int(os.environ.get("VERTEX_TIMEOUT_S", "150"))
DEFAULT_SPANNER_INSTANCE = os.environ.get("SPANNER_INSTANCE_ID", "starter-spanner")
DEFAULT_SPANNER_DATABASE = os.environ.get("SPANNER_DATABASE_ID", "starter_ontology_db")
DEFAULT_BQ_SPANNER_CONN = os.environ.get("BQ_SPANNER_CONNECTION_ID", "spanner_fabric_conn")
DEFAULT_CORE_MCP_URL = (
    os.environ.get("CORE_MCP_URL")
    or os.environ.get("AOS_CORE_MCP_URL")
    or "https://aos-builder-core-mcp-dasz7pvvua-du.a.run.app/mcp"
)


def _core_mcp_url(url: Optional[str] = None) -> str:
    if url and url != DEFAULT_CORE_MCP_URL:
        return url
    return (
        os.environ.get("CORE_MCP_URL")
        or os.environ.get("AOS_CORE_MCP_URL")
        or url
        or DEFAULT_CORE_MCP_URL
    )


def _fallback_direct() -> bool:
    """D8: Default is 'strict' (retry transient 502/503/504, no silent bypass). Set AOS_CORE_MCP_FALLBACK=direct for direct REST fallback."""
    return os.environ.get("AOS_CORE_MCP_FALLBACK", "strict").strip().lower() == "direct"


def runtime_settings() -> Dict[str, Any]:
    """Effective runtime settings (env-driven) for UI/config display."""
    return {
        "gcp_project_id": DEFAULT_PROJECT_ID,
        "region": DEFAULT_LOCATION,
        "bq_dataset_id": DEFAULT_DATASET_ID,
        "bq_fq_dataset": f"{DEFAULT_PROJECT_ID}.{DEFAULT_DATASET_ID}",
        "bq_property_graph": f"{DEFAULT_PROJECT_ID}.{DEFAULT_DATASET_ID}.STARTER_ONTOLOGY_GRAPH",
        "gcs_bucket": DEFAULT_GCS_BUCKET,
        "gcs_wiki_uri": f"gs://{DEFAULT_GCS_BUCKET}/ontology/",
        "spanner_instance_id": DEFAULT_SPANNER_INSTANCE,
        "spanner_database_id": DEFAULT_SPANNER_DATABASE,
        "bq_spanner_connection_id": DEFAULT_BQ_SPANNER_CONN,
        "vertex_model": DEFAULT_GEMINI_MODEL,
        "vertex_location": DEFAULT_VERTEX_LOCATION,
        "vertex_thinking_level": DEFAULT_THINKING_LEVEL,
        "vertex_build_thinking_level": DEFAULT_BUILD_THINKING_LEVEL,
        "core_mcp_url": _core_mcp_url(),
        "core_mcp_fallback": os.environ.get("AOS_CORE_MCP_FALLBACK", "strict"),
    }

_CAFILE = os.environ.get("SSL_CERT_FILE") or ("/etc/ssl/cert.pem" if os.path.exists("/etc/ssl/cert.pem") else None)
_CTX = ssl.create_default_context(cafile=_CAFILE)
_CACHED_TOKEN: str = ""
_TOKEN_EXPIRY: float = 0.0
_SPANNER_SESSIONS: Dict[Tuple[str, str, str], Tuple[str, float]] = {}


def get_gcp_token() -> str:
    """Retrieves a valid GCP OAuth2 access token: the request-bound user/SA token (src.identity, GOAL-233) if any,
    else the runtime identity from the Cloud Run Metadata Server or the gcloud CLI."""
    global _CACHED_TOKEN, _TOKEN_EXPIRY
    try:
        from src.identity import current_token
        bound = current_token()
    except Exception:  # identity module unavailable (stand-alone use)
        bound = None
    if bound:
        return bound
    now = time.time()
    if _CACHED_TOKEN and now < _TOKEN_EXPIRY:
        return _CACHED_TOKEN

    env_tok = os.environ.get("GCP_ACCESS_TOKEN", "").strip()
    if env_tok.startswith("ya29."):
        _CACHED_TOKEN = env_tok
        _TOKEN_EXPIRY = now + 1800
        return _CACHED_TOKEN

    ttl = {"s": 600.0}  # cache lifetime of the token picked below (gcloud: conservative 10 min)

    def _from_metadata() -> str:
        for host in ("metadata.google.internal", "169.254.169.254"):
            try:
                req = urllib.request.Request(
                    f"http://{host}/computeMetadata/v1/instance/service-accounts/default/token",
                    headers={"Metadata-Flavor": "Google"},
                )
                with urllib.request.urlopen(req, timeout=1.2) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    tok = data.get("access_token", "")
                    if tok:
                        # GOAL-234: the metadata server may return a token with only minutes left — never cache it past
                        # its real expiry (a fixed 40-min cache delegated expired tokens → GCS 401 Invalid Credentials).
                        ttl["s"] = max(30.0, min(float(data.get("expires_in") or 600) - 300.0, 2400.0))
                        return tok
            except Exception:
                pass
        return ""

    def _from_gcloud() -> str:
        env = os.environ.copy()
        sdk_bin = os.path.expanduser("~/google-cloud-sdk/bin")
        if os.path.isdir(sdk_bin) and sdk_bin not in env.get("PATH", ""):
            env["PATH"] = f"{sdk_bin}:{env.get('PATH', '')}"
        env["CLOUDSDK_METRICS_ENVIRONMENT"] = "datacloud.jetski"
        acct = (os.environ.get("GCP_GCLOUD_ACCOUNT") or "").strip()
        cmds = []
        if acct:
            cmds.append(["gcloud", "auth", "print-access-token", acct])
        cmds.extend([
            ["gcloud", "auth", "print-access-token"],
            ["gcloud", "auth", "application-default", "print-access-token"],
        ])
        for cmd in cmds:
            try:
                r = subprocess.run(cmd, capture_output=True, text=True, timeout=8, env=env)
                if r.returncode == 0 and r.stdout.strip().startswith("ya29."):
                    return r.stdout.strip()
            except Exception:
                pass
        return ""

    # On Cloud Run (K_SERVICE set), use Metadata Server first; on local/Cloudtop, use gcloud first to avoid VM default SA mismatches.
    providers = (_from_metadata, _from_gcloud) if os.environ.get("K_SERVICE") else (_from_gcloud, _from_metadata)
    for fn in providers:
        tok = fn()
        if tok:
            _CACHED_TOKEN = tok
            _TOKEN_EXPIRY = now + ttl["s"]
            return _CACHED_TOKEN

    raise RuntimeError(
        "GCP Authentication token unavailable. Please run `gcloud auth login` or set GCP_ACCESS_TOKEN."
    )


def _parse_bq_rows(schema_fields: List[Dict[str, Any]], raw_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    parsed: List[Dict[str, Any]] = []
    for row in raw_rows:
        cells = row.get("f", [])
        item: Dict[str, Any] = {}
        for idx, field in enumerate(schema_fields):
            fname = field["name"]
            ftype = field.get("type", "STRING").upper()
            val = cells[idx].get("v") if idx < len(cells) else None
            if val is not None:
                if ftype in ("INTEGER", "INT64"):
                    try:
                        val = int(val)
                    except Exception:
                        pass
                elif ftype in ("FLOAT", "FLOAT64", "NUMERIC", "BIGNUMERIC"):
                    try:
                        val = float(val)
                    except Exception:
                        pass
                elif ftype in ("BOOLEAN", "BOOL"):
                    val = str(val).lower() == "true"
            item[fname] = val
        parsed.append(item)
    return parsed


def _direct_execute_bq_sql(
    sql: str,
    project_id: str = DEFAULT_PROJECT_ID,
    location: str = DEFAULT_LOCATION,
    timeout_ms: int = 60000,
) -> Dict[str, Any]:
    """Direct BigQuery REST fallback (used only when AOS_CORE_MCP_FALLBACK=direct)."""
    t0 = time.perf_counter()
    token = get_gcp_token()
    url = f"https://bigquery.googleapis.com/bigquery/v2/projects/{project_id}/queries"
    payload = {
        "query": sql,
        "useLegacySql": False,
        "location": location,
        "timeoutMs": timeout_ms,
        "labels": {"datacloud": "jetski"},
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, context=_CTX, timeout=65) as resp:
            res = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
        return {
            "status": "ERROR",
            "http_code": e.code,
            "error": err_body,
            "sql": sql,
            "elapsed_ms": elapsed_ms,
            "rows": [],
        }

    job_id = res.get("jobReference", {}).get("jobId", "")
    if not res.get("jobComplete", True) and job_id:
        poll_url = f"https://bigquery.googleapis.com/bigquery/v2/projects/{project_id}/queries/{job_id}?location={location}"
        for _ in range(60):
            time.sleep(0.8)
            preq = urllib.request.Request(poll_url, headers={"Authorization": f"Bearer {token}"})
            with urllib.request.urlopen(preq, context=_CTX, timeout=30) as presp:
                res = json.loads(presp.read().decode("utf-8"))
            if res.get("jobComplete"):
                break

    elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
    schema_fields = res.get("schema", {}).get("fields", [])
    raw_rows = res.get("rows", [])
    rows = _parse_bq_rows(schema_fields, raw_rows)
    return {
        "status": "SUCCESS",
        "project_id": project_id,
        "location": location,
        "job_id": job_id,
        "elapsed_ms": elapsed_ms,
        "total_rows": int(res.get("totalRows", len(rows))),
        "total_bytes_processed": int(res.get("totalBytesProcessed", 0)),
        "cache_hit": bool(res.get("cacheHit", False)),
        "rows": rows,
        "sql": sql,
    }


def execute_bq_sql(
    sql: str,
    project_id: str = DEFAULT_PROJECT_ID,
    location: str = DEFAULT_LOCATION,
    timeout_ms: int = 60000,
) -> Dict[str, Any]:
    """Executes a BigQuery SQL or SQL:2023 GQL query via Core MCP (`bigquery_execute_sql`) with caller credentials."""
    sc = call_core_mcp_tool(
        "bigquery_execute_sql",
        {"project": project_id, "sql": sql, "location": location, "timeout_ms": timeout_ms, "labels": {"datacloud": "jetski"}},
        timeout_s=max(65, int(timeout_ms / 1000) + 15),
    )
    if sc.get("status") == "SUCCESS":
        rows = sc.get("rows", [])
        return {
            "status": "SUCCESS",
            "project_id": project_id,
            "location": location,
            "job_id": sc.get("job_id", ""),
            "elapsed_ms": sc.get("ms", 0),
            "total_rows": len(rows),
            "total_bytes_processed": int(sc.get("bytes_processed", 0)),
            "cache_hit": False,
            "rows": rows,
            "sql": sql,
            "via": "core_mcp:bigquery_execute_sql",
        }
    if _fallback_direct() and sc.get("_transport_error"):
        return _direct_execute_bq_sql(sql, project_id=project_id, location=location, timeout_ms=timeout_ms)
    code, _, msg = _mcp_err(sc)
    return {
        "status": "ERROR",
        "http_code": code,
        "error": msg,
        "sql": sql,
        "elapsed_ms": sc.get("ms", 0),
        "rows": [],
        "via": "core_mcp:bigquery_execute_sql",
    }


def upload_gcs_object(
    object_name: str,
    content_bytes: bytes,
    bucket: str = DEFAULT_GCS_BUCKET,
    content_type: str = "text/markdown; charset=utf-8",
) -> Dict[str, Any]:
    """Uploads an object to the Google Cloud Storage bucket via Core MCP (`storage_upload_object`)."""
    sc = call_core_mcp_tool(
        "storage_upload_object",
        {
            "bucket": bucket,
            "name": object_name,
            "content_base64": base64.b64encode(content_bytes).decode("ascii"),
            "content_type": content_type,
        },
        timeout_s=45,
    )
    if sc.get("status") == "SUCCESS":
        return sc.get("object") or sc
    if _fallback_direct() and sc.get("_transport_error"):
        token = get_gcp_token()
        encoded = urllib.parse.quote(object_name, safe="")
        url = f"https://storage.googleapis.com/upload/storage/v1/b/{bucket}/o?uploadType=media&name={encoded}"
        req = urllib.request.Request(
            url,
            data=content_bytes,
            method="POST",
            headers={"Authorization": f"Bearer {token}", "Content-Type": content_type},
        )
        with urllib.request.urlopen(req, context=_CTX, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    code, api, msg = _mcp_err(sc)
    raise RuntimeError(f"Core MCP storage_upload_object failed (HTTP {code} {api}): {msg}")


def list_gcs_objects(prefix: str = "", bucket: str = DEFAULT_GCS_BUCKET) -> List[Dict[str, Any]]:
    """Lists objects in the Google Cloud Storage bucket via Core MCP (`storage_list_objects`)."""
    sc = call_core_mcp_tool("storage_list_objects", {"bucket": bucket, "prefix": prefix}, timeout_s=30)
    if sc.get("status") == "SUCCESS":
        return sc.get("items", [])
    if _fallback_direct() and sc.get("_transport_error"):
        token = get_gcp_token()
        q = f"?prefix={urllib.parse.quote(prefix, safe='')}" if prefix else ""
        url = f"https://storage.googleapis.com/storage/v1/b/{bucket}/o{q}"
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
        with urllib.request.urlopen(req, context=_CTX, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("items", [])
    code, api, msg = _mcp_err(sc)
    raise RuntimeError(f"Core MCP storage_list_objects failed (HTTP {code} {api}): {msg}")


_LEVEL_MODELS: set = set()  # models that reject thinkingBudget and need thinkingLevel (e.g. gemini-4-argon)


def _thinking_cfg(model_name: str, level: str) -> Dict[str, Any]:
    """gemini-4-* rejects `thinkingBudget` (HTTP 400) and accepts `thinkingLevel` LOW/MEDIUM/HIGH (MINIMAL rejected)."""
    if model_name.startswith("gemini-4") or model_name in _LEVEL_MODELS:
        lvl = level if level in ("LOW", "MEDIUM", "HIGH") else "MEDIUM"
        return {"thinkingLevel": lvl}
    return {"thinkingBudget": 0}


def call_vertex_gemini(
    prompt: str,
    system_instruction: Optional[str] = None,
    response_mime_type: str = "text/plain",
    temperature: float = 0.1,
    max_tokens: int = 2048,
    model_name: str = DEFAULT_GEMINI_MODEL,
    project_id: str = DEFAULT_PROJECT_ID,
    thinking_level: str = DEFAULT_THINKING_LEVEL,
    timeout_s: int = DEFAULT_GEMINI_TIMEOUT_S,
    location: str = DEFAULT_VERTEX_LOCATION,
) -> Dict[str, Any]:
    """
    Calls the real Vertex AI Gemini model (`$VERTEX_GEMINI_MODEL`, default `gemini-4-argon`) on `location`
    (default `$VERTEX_LOCATION`, request-scoped callers pass their own).
    Never downgrades the model silently; returns full telemetry (model, latency_ms, token usage, text).
    Thought tokens count against maxOutputTokens, so the limit is floored (LOW 2048 / MEDIUM 8192 / HIGH 16384)
    and an empty MAX_TOKENS answer is retried with a 4x larger limit. 429/5xx/timeouts are retried with backoff.
    """
    t0 = time.perf_counter()
    location = location or DEFAULT_VERTEX_LOCATION
    host = "aiplatform.googleapis.com" if location == "global" else f"{location}-aiplatform.googleapis.com"
    url = (
        f"https://{host}/v1/projects/{project_id}/locations/{location}/"
        f"publishers/google/models/{model_name}:generateContent"
    )
    eff_level = str(thinking_level or DEFAULT_THINKING_LEVEL).upper()
    min_out = {"HIGH": 16384, "MEDIUM": 8192}.get(eff_level, 2048)
    gen_cfg: Dict[str, Any] = {
        "temperature": temperature,
        "maxOutputTokens": max(int(max_tokens), min_out),
        "topP": 0.95,
        "thinkingConfig": _thinking_cfg(model_name, eff_level),
    }
    if response_mime_type == "application/json":
        gen_cfg["responseMimeType"] = "application/json"

    body: Dict[str, Any] = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": gen_cfg,
    }
    if system_instruction:
        body["systemInstruction"] = {"parts": [{"text": system_instruction}]}

    def _err(code: Any, msg: str) -> Dict[str, Any]:
        return {
            "status": "ERROR",
            "model": model_name,
            "project_id": project_id,
            "http_code": code,
            "error": msg,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000, 2),
            "text": "",
        }

    last_err: Tuple[Any, str] = (None, "")
    for attempt in range(5):
        req = urllib.request.Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            method="POST",
            headers={"Authorization": f"Bearer {get_gcp_token()}", "Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, context=_CTX, timeout=timeout_s) as resp:
                raw = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            last_err = (e.code, err_body)
            if e.code == 400 and "thinking" in err_body.lower() and model_name not in _LEVEL_MODELS:
                _LEVEL_MODELS.add(model_name)
                gen_cfg["thinkingConfig"] = _thinking_cfg(model_name, thinking_level)
                continue
            if e.code == 401 and attempt == 0:
                invalidate_gcp_token()
                continue
            if e.code in (429, 500, 502, 503, 504) and attempt < 4:
                time.sleep(min(16, 2 ** (attempt + 1)))
                continue
            return _err(e.code, err_body)
        except Exception as e:  # timeout / connection reset: the next attempt usually answers
            last_err = (0, repr(e))
            if attempt < 2:
                continue
            return _err(0, repr(e))
        candidates = raw.get("candidates", [])
        parts = candidates[0].get("content", {}).get("parts", []) if candidates else []
        text = "".join(p.get("text", "") for p in parts if "text" in p and not p.get("thought")).strip()
        finish = candidates[0].get("finishReason", "") if candidates else ""
        usage = raw.get("usageMetadata", {})
        if not text:
            last_err = (200, f"empty response (finishReason={finish or 'NO_CANDIDATES'})")
            if finish == "MAX_TOKENS":
                gen_cfg["maxOutputTokens"] = min(int(gen_cfg["maxOutputTokens"]) * 4, 32768)
            if attempt < 3:
                continue
            return _err(200, last_err[1])
        return {
            "status": "SUCCESS",
            "model": raw.get("modelVersion") or model_name,
            "thinking_level": eff_level,
            "project_id": project_id,
            "location": location,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000, 2),
            "prompt_tokens": usage.get("promptTokenCount", 0),
            "candidates_tokens": usage.get("candidatesTokenCount", 0),
            "thoughts_tokens": usage.get("thoughtsTokenCount", 0),
            "total_tokens": usage.get("totalTokenCount", 0),
            "finish_reason": finish,
            "attempts": attempt + 1,
            "text": text,
        }
    return _err(last_err[0], last_err[1] or "retry exhausted")


def invalidate_gcp_token() -> None:
    global _CACHED_TOKEN, _TOKEN_EXPIRY
    _CACHED_TOKEN, _TOKEN_EXPIRY = "", 0.0


def call_core_mcp(
    method: str,
    params: Optional[Dict[str, Any]] = None,
    url: str = DEFAULT_CORE_MCP_URL,
    timeout_s: int = 120,
    access_token: Optional[str] = None,
) -> Dict[str, Any]:
    """Calls the remote Platform Core MCP (`aos-builder-core-mcp`, JSON-RPC 2.0 over HTTP).
    Automatically attaches caller credentials (`X-AOS-Access-Token`) and retries transient 502/503/504 errors up to 2 times (D8)."""
    t0 = time.perf_counter()
    target_url = _core_mcp_url(url)
    tok = access_token
    if tok is None:
        try:
            tok = get_gcp_token()
        except Exception:
            tok = ""
    try:
        from src.config import APP_VERSION as _APP_VER
    except Exception:
        _APP_VER = "starter"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-AOS-Client": f"agentic-ontology-starter/{_APP_VER}",
    }
    if tok:
        headers["X-AOS-Access-Token"] = tok
    payload = {"jsonrpc": "2.0", "id": int(time.time() * 1000) % 100000, "method": method, "params": params or {}}
    body_bytes = json.dumps(payload).encode("utf-8")
    last_err: Dict[str, Any] = {}
    for attempt in range(3):
        req = urllib.request.Request(target_url, data=body_bytes, method="POST", headers=headers)
        try:
            with urllib.request.urlopen(req, context=_CTX, timeout=timeout_s) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            out: Dict[str, Any] = {
                "status": "ERROR" if "error" in data else "SUCCESS",
                "url": target_url,
                "method": method,
                "elapsed_ms": round((time.perf_counter() - t0) * 1000, 2),
                "attempts": attempt + 1,
            }
            if "error" in data:
                out["error"] = data["error"]
            else:
                out["result"] = data.get("result", {})
            return out
        except urllib.error.HTTPError as e:
            err_txt = e.read().decode("utf-8", errors="replace")[:1000]
            last_err = {
                "status": "ERROR",
                "url": target_url,
                "method": method,
                "http_code": e.code,
                "error": err_txt,
                "elapsed_ms": round((time.perf_counter() - t0) * 1000, 2),
            }
            if e.code in (502, 503, 504) and attempt < 2:
                time.sleep(1.0 * (attempt + 1))
                continue
            return last_err
        except Exception as e:
            last_err = {
                "status": "ERROR",
                "url": target_url,
                "method": method,
                "http_code": 0,
                "error": repr(e)[:500],
                "elapsed_ms": round((time.perf_counter() - t0) * 1000, 2),
            }
            if attempt < 2:
                time.sleep(1.0 * (attempt + 1))
                continue
            return last_err
    return last_err


def call_core_mcp_tool(
    tool_name: str,
    arguments: Dict[str, Any],
    url: Optional[str] = None,
    timeout_s: int = 120,
    access_token: Optional[str] = None,
    _retry_401: bool = False,
) -> Dict[str, Any]:
    """Invokes a single tool on Platform Core MCP (`tools/call`) with caller token delegation and returns `structuredContent`."""
    r = call_core_mcp(
        "tools/call",
        {"name": tool_name, "arguments": arguments},
        url=url or DEFAULT_CORE_MCP_URL,
        timeout_s=timeout_s,
        access_token=access_token,
    )
    if r.get("status") != "SUCCESS":
        code = int(r.get("http_code") or 502)
        return {
            "status": "ERROR",
            "http_code": code,
            "error": {"http_status": code, "api": f"core-mcp:{tool_name}", "message": str(r.get("error") or "Core MCP transport failure")},
            "ms": r.get("elapsed_ms", 0),
            "_transport_error": True,
        }
    res = r.get("result") or {}
    sc = res.get("structuredContent")
    if not isinstance(sc, dict):
        try:
            sc = json.loads(((res.get("content") or [{}])[0]).get("text", "{}"))
        except Exception:
            sc = {"status": "ERROR", "error": {"http_status": 500, "api": tool_name, "message": "Invalid structuredContent from Core MCP"}}
    sc.setdefault("ms", r.get("elapsed_ms", 0))
    if access_token is None and not _retry_401 and _is_auth_401(sc) and not _bound_token():
        # GOAL-234: the cached runtime token went stale → drop it and retry once with a fresh one.
        invalidate_gcp_token()
        return call_core_mcp_tool(tool_name, arguments, url=url, timeout_s=timeout_s, _retry_401=True)
    return sc


def _bound_token() -> Optional[str]:
    try:
        from src.identity import current_token
        return current_token()
    except Exception:
        return None


def _is_auth_401(sc: Dict[str, Any]) -> bool:
    if sc.get("status") == "SUCCESS":
        return False
    err = sc.get("error")
    code = (err.get("http_status") or err.get("code")) if isinstance(err, dict) else sc.get("http_code")
    text = str(err or "")
    return str(code) == "401" or "Invalid Credentials" in text or "UNAUTHENTICATED" in text


def _mcp_err(sc: Dict[str, Any]) -> Tuple[int, str, str]:
    err = sc.get("error")
    if isinstance(err, dict):
        code = int(err.get("http_status") or err.get("code") or sc.get("http_code") or 500)
        api = str(err.get("api") or sc.get("tool") or "core-mcp")
        msg = str(err.get("message") or err)[:600]
        return code, api, msg
    code = int(sc.get("http_code") or 500)
    return code, str(sc.get("tool") or "core-mcp"), str(err or sc)[:600]


def check_spanner_available(
    project_id: str = DEFAULT_PROJECT_ID,
    instance_id: str = DEFAULT_SPANNER_INSTANCE,
    database_id: str = DEFAULT_SPANNER_DATABASE,
) -> Dict[str, Any]:
    """Checks whether the Cloud Spanner instance and database are provisioned and READY via Core MCP (`spanner_get_database`)."""
    if not instance_id or not database_id:
        return {"available": False, "reason": "SPANNER_INSTANCE_ID or SPANNER_DATABASE_ID is empty"}
    db_uri = f"projects/{project_id}/instances/{instance_id}/databases/{database_id}"
    sc = call_core_mcp_tool("spanner_get_database", {"database": db_uri}, timeout_s=20)
    if sc.get("status") == "SUCCESS":
        if not sc.get("exists"):
            return {"available": False, "http_code": 404, "error": f"Database {db_uri} not found"}
        info = sc.get("database") or {}
        state = info.get("state", "UNKNOWN")
        return {"available": state == "READY", "state": state, "database": info.get("name"), "via": "core_mcp:spanner_get_database"}
    if _fallback_direct() and sc.get("_transport_error"):
        token = get_gcp_token()
        url = f"https://spanner.googleapis.com/v1/{db_uri}"
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
        try:
            with urllib.request.urlopen(req, context=_CTX, timeout=10) as resp:
                info = json.loads(resp.read().decode("utf-8"))
            state = info.get("state", "UNKNOWN")
            return {"available": state == "READY", "state": state, "database": info.get("name")}
        except urllib.error.HTTPError as e:
            return {"available": False, "http_code": e.code, "error": e.read().decode("utf-8", errors="replace")[:500]}
        except Exception as e:
            return {"available": False, "error": repr(e)[:300]}
    code, _, msg = _mcp_err(sc)
    return {"available": False, "http_code": code, "error": msg[:500]}


def _get_spanner_session(
    project_id: str = DEFAULT_PROJECT_ID,
    instance_id: str = DEFAULT_SPANNER_INSTANCE,
    database_id: str = DEFAULT_SPANNER_DATABASE,
    force_new: bool = False,
) -> str:
    key = (project_id, instance_id, database_id)
    now = time.time()
    if not force_new and key in _SPANNER_SESSIONS:
        sess_name, exp = _SPANNER_SESSIONS[key]
        if now < exp:
            return sess_name
    token = get_gcp_token()
    url = f"https://spanner.googleapis.com/v1/projects/{project_id}/instances/{instance_id}/databases/{database_id}/sessions"
    req = urllib.request.Request(
        url,
        data=b"{}",
        method="POST",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, context=_CTX, timeout=15) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    sess_name = data["name"]
    _SPANNER_SESSIONS[key] = (sess_name, now + 1200)
    return sess_name


def _parse_spanner_rows(fields: List[Dict[str, Any]], raw_rows: List[List[Any]]) -> List[Dict[str, Any]]:
    parsed: List[Dict[str, Any]] = []
    for row in raw_rows:
        item: Dict[str, Any] = {}
        for idx, f in enumerate(fields):
            fname = f.get("name") or f"col_{idx}"
            ftype = (f.get("type") or {}).get("code", "STRING").upper()
            val = row[idx] if idx < len(row) else None
            if val is not None:
                if ftype == "INT64":
                    try:
                        val = int(val)
                    except Exception:
                        pass
                elif ftype in ("FLOAT64", "FLOAT32", "NUMERIC"):
                    try:
                        val = float(val)
                    except Exception:
                        pass
                elif ftype == "BOOL":
                    val = val if isinstance(val, bool) else str(val).lower() == "true"
            item[fname] = val
        parsed.append(item)
    return parsed


import http.client
import threading

_SPANNER_LOCAL = threading.local()


def _spanner_post_json(path: str, payload: Dict[str, Any], token: str, timeout: int = 30) -> Dict[str, Any]:
    """Sends a POST request to spanner.googleapis.com reusing a thread-local HTTPS keep-alive connection."""
    body = json.dumps(payload).encode("utf-8")
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Content-Length": str(len(body)),
        "Connection": "keep-alive",
    }
    for attempt in range(2):
        conn: Optional[http.client.HTTPSConnection] = getattr(_SPANNER_LOCAL, "conn", None)
        try:
            if conn is None:
                conn = http.client.HTTPSConnection("spanner.googleapis.com", timeout=timeout, context=_CTX)
                _SPANNER_LOCAL.conn = conn
            conn.request("POST", path, body=body, headers=headers)
            resp = conn.getresponse()
            raw = resp.read().decode("utf-8", errors="replace")
            if resp.status >= 400:
                raise urllib.error.HTTPError(
                    f"https://spanner.googleapis.com{path}", resp.status, resp.reason, resp.headers, None
                )
            return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as he:
            he.body_text = raw  # type: ignore[attr-defined]
            raise
        except Exception:
            try:
                if conn:
                    conn.close()
            except Exception:
                pass
            _SPANNER_LOCAL.conn = None
            if attempt == 1:
                raise
    return {}


def execute_spanner_sql(
    sql: str,
    project_id: str = DEFAULT_PROJECT_ID,
    instance_id: str = DEFAULT_SPANNER_INSTANCE,
    database_id: str = DEFAULT_SPANNER_DATABASE,
) -> Dict[str, Any]:
    """Executes a GoogleSQL or ISO GQL (GRAPH_TABLE) query on Cloud Spanner via Core MCP (`spanner_execute_sql`)."""
    db_uri = f"projects/{project_id}/instances/{instance_id}/databases/{database_id}"
    sc = call_core_mcp_tool("spanner_execute_sql", {"database": db_uri, "sql": sql, "timeout_s": 30}, timeout_s=35)
    if sc.get("status") == "SUCCESS":
        rows = sc.get("rows", [])
        return {
            "status": "SUCCESS",
            "engine": "spanner",
            "project_id": project_id,
            "instance_id": instance_id,
            "database_id": database_id,
            "job_id": f"spanner:{instance_id}/{database_id}@{int(time.time()*1000)}",
            "elapsed_ms": sc.get("ms", 0),
            "total_rows": len(rows),
            "rows": rows,
            "sql": sql,
            "via": "core_mcp:spanner_execute_sql",
        }
    if not (_fallback_direct() and sc.get("_transport_error")):
        code, _, msg = _mcp_err(sc)
        return {
            "status": "ERROR",
            "engine": "spanner",
            "http_code": code,
            "error": msg,
            "sql": sql,
            "elapsed_ms": sc.get("ms", 0),
            "rows": [],
            "via": "core_mcp:spanner_execute_sql",
        }
    t0 = time.perf_counter()
    token = get_gcp_token()
    for attempt in range(2):
        try:
            sess = _get_spanner_session(project_id, instance_id, database_id, force_new=(attempt > 0))
            t_query = time.perf_counter()
            res = _spanner_post_json(f"/v1/{sess}:executeSql", {"sql": sql}, token, timeout=30)
            elapsed_ms = round((time.perf_counter() - t_query) * 1000, 2)
            fields = res.get("metadata", {}).get("rowType", {}).get("fields", [])
            rows = _parse_spanner_rows(fields, res.get("rows", []))
            return {
                "status": "SUCCESS",
                "engine": "spanner",
                "project_id": project_id,
                "instance_id": instance_id,
                "database_id": database_id,
                "job_id": f"spanner:{instance_id}/{database_id}@{int(time.time()*1000)}",
                "elapsed_ms": elapsed_ms,
                "total_rows": len(rows),
                "rows": rows,
                "sql": sql,
            }
        except urllib.error.HTTPError as e:
            err_body = getattr(e, "body_text", "") or (e.read().decode("utf-8", errors="replace") if e.fp else str(e))
            if e.code == 404 and "Session not found" in err_body and attempt == 0:
                continue
            elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
            return {
                "status": "ERROR",
                "engine": "spanner",
                "http_code": e.code,
                "error": err_body,
                "sql": sql,
                "elapsed_ms": elapsed_ms,
                "rows": [],
            }
        except Exception as e:
            elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
            return {
                "status": "ERROR",
                "engine": "spanner",
                "error": repr(e),
                "sql": sql,
                "elapsed_ms": elapsed_ms,
                "rows": [],
            }
    return {"status": "ERROR", "engine": "spanner", "error": "Session retry exhausted", "sql": sql, "rows": []}


def upsert_spanner_rows(
    table: str,
    cols: Tuple[str, ...],
    rows: List[Tuple[Any, ...]],
    truncate_first: bool = True,
    project_id: str = DEFAULT_PROJECT_ID,
    instance_id: str = DEFAULT_SPANNER_INSTANCE,
    database_id: str = DEFAULT_SPANNER_DATABASE,
) -> Dict[str, Any]:
    """Truncates (optional) and inserts/updates rows in a Cloud Spanner table via Core MCP (`spanner_commit`)."""
    mutations: List[Dict[str, Any]] = []
    if truncate_first:
        mutations.append({"delete": {"table": table, "keySet": {"all": True}}})
    if rows:
        enc_rows = [
            [str(v) if isinstance(v, int) and not isinstance(v, bool) else v for v in r]
            for r in rows
        ]
        mutations.append({
            "insertOrUpdate": {
                "table": table,
                "columns": list(cols),
                "values": enc_rows,
            }
        })
    db_uri = f"projects/{project_id}/instances/{instance_id}/databases/{database_id}"
    sc = call_core_mcp_tool("spanner_commit", {"database": db_uri, "mutations": mutations}, timeout_s=45)
    if sc.get("status") == "SUCCESS":
        commit = sc.get("commit") or {}
        ts = commit.get("commitTimestamp", "")
        return {
            "status": "SUCCESS",
            "table": table,
            "rows": len(rows),
            "commit_timestamp": ts,
            "job_id": f"spanner-commit:{table}@{ts}",
            "elapsed_ms": sc.get("ms", 0),
            "via": "core_mcp:spanner_commit",
        }
    if not (_fallback_direct() and sc.get("_transport_error")):
        code, _, msg = _mcp_err(sc)
        return {
            "status": "ERROR",
            "table": table,
            "http_code": code,
            "error": msg,
            "elapsed_ms": sc.get("ms", 0),
            "via": "core_mcp:spanner_commit",
        }
    t0 = time.perf_counter()
    token = get_gcp_token()
    sess = _get_spanner_session(project_id, instance_id, database_id)
    url = f"https://spanner.googleapis.com/v1/{sess}:commit"
    payload = {"singleUseTransaction": {"readWrite": {}}, "mutations": mutations}
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, context=_CTX, timeout=30) as resp:
            res = json.loads(resp.read().decode("utf-8"))
        elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
        return {
            "status": "SUCCESS",
            "table": table,
            "rows": len(rows),
            "commit_timestamp": res.get("commitTimestamp"),
            "job_id": f"spanner-commit:{table}@{res.get('commitTimestamp', '')}",
            "elapsed_ms": elapsed_ms,
        }
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        return {
            "status": "ERROR",
            "table": table,
            "http_code": e.code,
            "error": err_body,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000, 2),
        }


def execute_spanner_ddl(
    statements: List[str],
    project_id: str = DEFAULT_PROJECT_ID,
    instance_id: str = DEFAULT_SPANNER_INSTANCE,
    database_id: str = DEFAULT_SPANNER_DATABASE,
) -> Dict[str, Any]:
    """Executes DDL statements on Cloud Spanner via Core MCP (`spanner_update_ddl` + `spanner_get_operation`)."""
    t0 = time.perf_counter()
    clean_stmts = [s.strip().rstrip(";").strip() for s in statements if s and s.strip()]
    db_uri = f"projects/{project_id}/instances/{instance_id}/databases/{database_id}"
    sc = call_core_mcp_tool("spanner_update_ddl", {"database": db_uri, "statements": clean_stmts, "timeout_s": 90}, timeout_s=100)
    if sc.get("status") == "SUCCESS":
        op = sc.get("operation") or {}
        op_name = op.get("name", "")
        while not op.get("done", False) and op_name:
            time.sleep(1.5)
            osc = call_core_mcp_tool("spanner_get_operation", {"name": op_name}, timeout_s=30)
            if osc.get("status") != "SUCCESS":
                code, _, msg = _mcp_err(osc)
                return {"status": "ERROR", "http_code": code, "error": msg, "elapsed_ms": round((time.perf_counter() - t0) * 1000, 2)}
            op = osc.get("operation") or {}
        elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
        if "error" in op:
            return {"status": "ERROR", "operation": op_name, "error": json.dumps(op["error"]), "elapsed_ms": elapsed_ms}
        return {"status": "SUCCESS", "operation": op_name, "elapsed_ms": elapsed_ms, "via": "core_mcp:spanner_update_ddl"}
    if not (_fallback_direct() and sc.get("_transport_error")):
        code, _, msg = _mcp_err(sc)
        return {"status": "ERROR", "http_code": code, "error": msg, "elapsed_ms": sc.get("ms", 0), "via": "core_mcp:spanner_update_ddl"}
    token = get_gcp_token()
    url = f"https://spanner.googleapis.com/v1/{db_uri}/ddl"
    req = urllib.request.Request(
        url,
        data=json.dumps({"statements": clean_stmts}).encode("utf-8"),
        method="PATCH",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, context=_CTX, timeout=30) as resp:
            op = json.loads(resp.read().decode("utf-8"))
        op_name = op.get("name", "")
        while not op.get("done", False) and op_name:
            time.sleep(1.5)
            preq = urllib.request.Request(
                f"https://spanner.googleapis.com/v1/{op_name}",
                headers={"Authorization": f"Bearer {token}"},
            )
            with urllib.request.urlopen(preq, context=_CTX, timeout=20) as presp:
                op = json.loads(presp.read().decode("utf-8"))
        elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
        if "error" in op:
            return {"status": "ERROR", "operation": op_name, "error": json.dumps(op["error"]), "elapsed_ms": elapsed_ms}
        return {"status": "SUCCESS", "operation": op_name, "elapsed_ms": elapsed_ms}
    except urllib.error.HTTPError as e:
        return {
            "status": "ERROR",
            "http_code": e.code,
            "error": e.read().decode("utf-8", errors="replace"),
            "elapsed_ms": round((time.perf_counter() - t0) * 1000, 2),
        }


# ---------------------------------------------------------------------------------------------------------------
# Wizard helpers (GOAL-223 / GOAL-224) — every helper delegates to Core MCP (`X-AOS-Access-Token`) and returns
# (http_code, payload) without raising for HTTP errors, so the caller can show the exact API, status and missing
# permission to the user.
# ---------------------------------------------------------------------------------------------------------------
_PRINCIPAL: Dict[str, Any] = {"email": "", "at": 0.0}


def http_call(method: str, url: str, body: Any = None, timeout: int = 30, raw: Optional[bytes] = None,
              content_type: str = "application/json") -> Tuple[int, Any]:
    """Authorized HTTP call → (status code, parsed JSON | text). Code 0 = network error."""
    data = raw if raw is not None else (json.dumps(body).encode("utf-8") if body is not None else None)
    try:
        token = get_gcp_token()
    except Exception as e:  # no credentials at all
        return 401, {"error": {"code": 401, "message": str(e)}}
    headers = {"Authorization": f"Bearer {token}"}
    if data is not None:
        headers["Content-Type"] = content_type
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, context=_CTX, timeout=timeout) as resp:
            txt = resp.read().decode("utf-8", errors="replace")
            code = resp.status
    except urllib.error.HTTPError as e:
        txt = e.read().decode("utf-8", errors="replace")
        code = e.code
    except Exception as e:
        return 0, {"error": {"code": 0, "message": repr(e)[:400]}}
    try:
        return code, json.loads(txt) if txt else {}
    except Exception:
        return code, txt


def error_message(payload: Any) -> str:
    """Extracts the human message from a Google API error payload."""
    if isinstance(payload, dict):
        err = payload.get("error")
        if isinstance(err, dict):
            return str(err.get("message") or err.get("status") or err)[:600]
        if isinstance(err, str):
            return err[:600]
        res = payload.get("status")
        if isinstance(res, dict) and res.get("errorResult"):
            return str(res["errorResult"].get("message"))[:600]
    return str(payload)[:600]


def token_principal() -> str:
    """Email of the identity behind get_gcp_token() (Cloud Run SA, or the gcloud user locally)."""
    try:
        from src.identity import current
        bound = current()
        if bound.get("mode") in ("token", "impersonate") and bound.get("principal"):
            return str(bound["principal"])
    except Exception:
        pass
    now = time.time()
    if _PRINCIPAL["email"] and now - _PRINCIPAL["at"] < 600:
        return _PRINCIPAL["email"]
    try:
        tok = get_gcp_token()
        with urllib.request.urlopen(f"https://oauth2.googleapis.com/tokeninfo?access_token={tok}", context=_CTX,
                                    timeout=10) as r:
            email = json.loads(r.read().decode("utf-8")).get("email") or ""
    except Exception:
        email = ""
    if not email:
        try:  # metadata server (Cloud Run / GCE)
            req = urllib.request.Request(
                "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/email",
                headers={"Metadata-Flavor": "Google"})
            with urllib.request.urlopen(req, timeout=1.5) as r:
                email = r.read().decode("utf-8").strip()
        except Exception:
            email = ""
    _PRINCIPAL.update(email=email or "unknown", at=now)
    return _PRINCIPAL["email"]


def gcs_test_permissions(bucket: str, permissions: List[str]) -> Tuple[int, Any]:
    sc = call_core_mcp_tool("iam_test_permissions", {"bucket": bucket, "bucket_permissions": permissions}, timeout_s=20)
    if sc.get("status") == "SUCCESS":
        return 200, {"permissions": sc.get("bucket_permissions") or sc.get("permissions") or []}
    if _fallback_direct() and sc.get("_transport_error"):
        q = "&".join("permissions=" + urllib.parse.quote(p) for p in permissions)
        return http_call("GET", f"https://storage.googleapis.com/storage/v1/b/{bucket}/iam/testPermissions?{q}", timeout=15)
    code, _, msg = _mcp_err(sc)
    return code, {"error": {"code": code, "message": msg}}


def gcs_upload(object_name: str, data: bytes, bucket: str, content_type: str = "text/markdown; charset=utf-8") -> Tuple[int, Any]:
    sc = call_core_mcp_tool(
        "storage_upload_object",
        {
            "bucket": bucket,
            "name": object_name,
            "content_base64": base64.b64encode(data).decode("ascii"),
            "content_type": content_type,
        },
        timeout_s=45,
    )
    if sc.get("status") == "SUCCESS":
        return 200, sc.get("object") or sc
    if _fallback_direct() and sc.get("_transport_error"):
        enc = urllib.parse.quote(object_name, safe="")
        return http_call("POST", f"https://storage.googleapis.com/upload/storage/v1/b/{bucket}/o?uploadType=media&name={enc}",
                         raw=data, content_type=content_type, timeout=30)
    code, _, msg = _mcp_err(sc)
    return code, {"error": {"code": code, "message": msg}}


def gcs_download_text(object_name: str, bucket: str) -> Tuple[int, str]:
    sc = call_core_mcp_tool("storage_read_object", {"bucket": bucket, "name": object_name}, timeout_s=25)
    if sc.get("status") == "SUCCESS":
        if "text" in sc:
            return 200, str(sc.get("text") or "")
        if "content_base64" in sc:
            return 200, base64.b64decode(str(sc.get("content_base64") or "")).decode("utf-8", errors="replace")
        return 200, ""
    if _fallback_direct() and sc.get("_transport_error"):
        enc = urllib.parse.quote(object_name, safe="")
        try:
            token = get_gcp_token()
        except Exception as e:
            return 401, str(e)
        req = urllib.request.Request(f"https://storage.googleapis.com/storage/v1/b/{bucket}/o/{enc}?alt=media",
                                     headers={"Authorization": f"Bearer {token}"})
        try:
            with urllib.request.urlopen(req, context=_CTX, timeout=20) as r:
                return r.status, r.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8", errors="replace")
        except Exception as e:
            return 0, repr(e)[:300]
    code, _, msg = _mcp_err(sc)
    return code, msg


def gcs_list(prefix: str, bucket: str) -> Tuple[int, Any]:
    sc = call_core_mcp_tool("storage_list_objects", {"bucket": bucket, "prefix": prefix}, timeout_s=25)
    if sc.get("status") == "SUCCESS":
        return 200, {"items": sc.get("items", []), "count": sc.get("count", 0)}
    if _fallback_direct() and sc.get("_transport_error"):
        q = urllib.parse.quote(prefix, safe="")
        return http_call("GET", f"https://storage.googleapis.com/storage/v1/b/{bucket}/o?prefix={q}&fields=items(name,size,updated,md5Hash)",
                         timeout=20)
    code, _, msg = _mcp_err(sc)
    return code, {"error": {"code": code, "message": msg}}


def bq_dataset_get(project_id: str, dataset_id: str) -> Tuple[int, Any]:
    sc = call_core_mcp_tool("bigquery_get_dataset_info", {"project": project_id, "dataset": dataset_id}, timeout_s=20)
    if sc.get("status") == "SUCCESS":
        if not sc.get("exists"):
            return 404, {"error": {"code": 404, "message": f"Dataset {project_id}:{dataset_id} not found"}}
        return 200, sc.get("dataset") or {}
    if _fallback_direct() and sc.get("_transport_error"):
        return http_call("GET", f"https://bigquery.googleapis.com/bigquery/v2/projects/{project_id}/datasets/{dataset_id}", timeout=15)
    code, _, msg = _mcp_err(sc)
    return code, {"error": {"code": code, "message": msg}}


def bq_dataset_create(project_id: str, dataset_id: str, location: str, description: str = "") -> Tuple[int, Any]:
    sc = call_core_mcp_tool(
        "bigquery_create_dataset",
        {
            "project": project_id,
            "dataset": dataset_id,
            "location": location,
            "description": description,
            "labels": {"datacloud": "jetski", "app": "agentic-ontology-starter"},
        },
        timeout_s=25,
    )
    if sc.get("status") == "SUCCESS":
        return 200, sc.get("dataset") or {}
    if _fallback_direct() and sc.get("_transport_error"):
        body = {"datasetReference": {"projectId": project_id, "datasetId": dataset_id}, "location": location,
                "description": description, "labels": {"datacloud": "jetski", "app": "agentic-ontology-starter"}}
        return http_call("POST", f"https://bigquery.googleapis.com/bigquery/v2/projects/{project_id}/datasets", body=body, timeout=20)
    code, _, msg = _mcp_err(sc)
    return code, {"error": {"code": code, "message": msg}}


def bq_table_patch(project_id: str, dataset_id: str, table_id: str, description: str, fields: List[Dict[str, Any]]) -> Tuple[int, Any]:
    sc = call_core_mcp_tool(
        "bigquery_load_table",
        {
            "project": project_id,
            "dataset": dataset_id,
            "table": table_id,
            "schema": fields,
            "description": description,
            "patch_only": True,
        },
        timeout_s=25,
    )
    if sc.get("status") == "SUCCESS":
        return 200, sc.get("table_resource") or sc
    if _fallback_direct() and sc.get("_transport_error"):
        body = {"description": description, "schema": {"fields": fields}}
        return http_call("PATCH", f"https://bigquery.googleapis.com/bigquery/v2/projects/{project_id}/datasets/{dataset_id}/tables/{table_id}",
                         body=body, timeout=20)
    code, _, msg = _mcp_err(sc)
    return code, {"error": {"code": code, "message": msg}}


def bq_load_json_rows(
    project_id: str,
    dataset_id: str,
    table_id: str,
    fields: List[Dict[str, Any]],
    rows: List[Dict[str, Any]],
    location: str,
    timeout_s: int = 150,
    description: Optional[str] = None,
) -> Dict[str, Any]:
    """Loads rows via Core MCP (`bigquery_load_table`, multipart upload, NEWLINE_DELIMITED_JSON, WRITE_TRUNCATE)."""
    args: Dict[str, Any] = {
        "project": project_id,
        "dataset": dataset_id,
        "table": table_id,
        "schema": fields,
        "rows": rows,
        "location": location,
        "timeout_s": timeout_s,
    }
    if description is not None:
        args["description"] = description
    sc = call_core_mcp_tool("bigquery_load_table", args, timeout_s=timeout_s + 15)
    if sc.get("status") == "SUCCESS":
        return {
            "status": "SUCCESS",
            "job_id": sc.get("job_id", ""),
            "elapsed_ms": sc.get("ms", 0),
            "api": "Core MCP bigquery_load_table",
            "output_rows": int(sc.get("output_rows", len(rows))),
            "patched": sc.get("patched", False),
            "patch": sc.get("patch_status", 200),
            "patch_error": sc.get("patch_error", ""),
        }
    if not (_fallback_direct() and sc.get("_transport_error")):
        code, api, msg = _mcp_err(sc)
        return {
            "status": "ERROR",
            "http_code": code,
            "error": msg,
            "api": f"Core MCP bigquery_load_table ({api})",
            "elapsed_ms": sc.get("ms", 0),
        }
    t0 = time.perf_counter()
    meta = {
        "jobReference": {"projectId": project_id, "location": location},
        "configuration": {
            "labels": {"datacloud": "jetski"},
            "load": {
                "destinationTable": {"projectId": project_id, "datasetId": dataset_id, "tableId": table_id},
                "schema": {"fields": fields},
                "sourceFormat": "NEWLINE_DELIMITED_JSON",
                "writeDisposition": "WRITE_TRUNCATE",
                "createDisposition": "CREATE_IF_NEEDED",
            },
        },
    }
    ndjson = "\n".join(json.dumps(r, ensure_ascii=False) for r in rows).encode("utf-8")
    boundary = f"aolstarter{int(time.time() * 1000)}"
    body = (f"--{boundary}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n{json.dumps(meta)}\r\n"
            f"--{boundary}\r\nContent-Type: application/octet-stream\r\n\r\n").encode("utf-8") + ndjson + \
        f"\r\n--{boundary}--\r\n".encode("utf-8")
    code, job = http_call("POST", f"https://bigquery.googleapis.com/upload/bigquery/v2/projects/{project_id}/jobs?uploadType=multipart",
                          raw=body, content_type=f"multipart/related; boundary={boundary}", timeout=60)
    if code not in (200, 201) or not isinstance(job, dict):
        return {"status": "ERROR", "http_code": code, "error": error_message(job), "api": "bigquery.jobs.insert (load)",
                "elapsed_ms": round((time.perf_counter() - t0) * 1000, 1)}
    job_id = (job.get("jobReference") or {}).get("jobId", "")
    deadline = time.time() + timeout_s
    while (job.get("status") or {}).get("state") != "DONE" and time.time() < deadline:
        time.sleep(0.8)
        code, job = http_call("GET", f"https://bigquery.googleapis.com/bigquery/v2/projects/{project_id}/jobs/{job_id}?location={location}",
                              timeout=20)
        if code != 200 or not isinstance(job, dict):
            return {"status": "ERROR", "http_code": code, "error": error_message(job), "job_id": job_id,
                    "api": "bigquery.jobs.get", "elapsed_ms": round((time.perf_counter() - t0) * 1000, 1)}
    st = job.get("status") or {}
    out = {"job_id": job_id, "elapsed_ms": round((time.perf_counter() - t0) * 1000, 1), "api": "bigquery.jobs.insert (load)",
           "output_rows": int(((job.get("statistics") or {}).get("load") or {}).get("outputRows") or 0)}
    if st.get("state") != "DONE":
        return {**out, "status": "ERROR", "http_code": 504, "error": "load job did not finish in time"}
    if st.get("errorResult"):
        return {**out, "status": "ERROR", "http_code": 400, "error": str(st["errorResult"].get("message"))[:600]}
    return {**out, "status": "SUCCESS"}


def project_test_permissions(project_id: str, permissions: List[str]) -> Tuple[int, Any]:
    sc = call_core_mcp_tool("iam_test_permissions", {"project": project_id, "project_permissions": permissions}, timeout_s=20)
    if sc.get("status") == "SUCCESS":
        return 200, {"permissions": sc.get("project_permissions") or sc.get("permissions") or []}
    if _fallback_direct() and sc.get("_transport_error"):
        return http_call("POST", f"https://cloudresourcemanager.googleapis.com/v1/projects/{project_id}:testIamPermissions",
                         body={"permissions": permissions}, timeout=15)
    code, _, msg = _mcp_err(sc)
    return code, {"error": {"code": code, "message": msg}}


def bq_reservation_assignments(project_id: str, location: str) -> Tuple[int, Any]:
    sc = call_core_mcp_tool("bigquery_check_reservation", {"project": project_id, "location": location}, timeout_s=25)
    if sc.get("status") == "SUCCESS":
        return 200, {
            "assignments": sc.get("assignments", []),
            "editions": sc.get("editions", []),
            "has_enterprise": sc.get("has_enterprise", False),
        }
    if _fallback_direct() and sc.get("_transport_error"):
        q = urllib.parse.quote(f"assignee=projects/{project_id}")
        return http_call("GET", f"https://bigqueryreservation.googleapis.com/v1/projects/{project_id}/locations/{location}:searchAllAssignments?query={q}",
                         timeout=15)
    code, _, msg = _mcp_err(sc)
    return code, {"error": {"code": code, "message": msg}}


