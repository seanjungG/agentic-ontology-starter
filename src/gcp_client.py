# Copyright (c) 2026 Sean Jung (seanjung@google.com). All Rights Reserved.
# Non-Commercial Use Only: Methodology & Docs under CC BY-NC-ND 4.0; Source Code under PolyForm Noncommercial License 1.0.0.
# Commercial use, paid consulting/SI/PoC delivery, or production deployment requires prior written permission from seanjung@google.com.

# -*- coding: utf-8 -*-
"""
gcp_client.py
Real Google Cloud Platform REST Client for Agentic Ontology Starter:
- Connects to real BigQuery (`seanjung-poc.starter_ontology_dw`) for SQL & SQL:2023 Property Graph GQL queries
- Connects to real Cloud Storage (`gs://seanjung-poc-starter-ontology`) for 3-Layer OKF Wiki artifacts
- Connects to real Vertex AI (`gemini-3.8-flash` on `seanjung-poc`) for dynamic decomposition & grounded synthesis
- Zero external pip dependencies (uses standard library urllib + Metadata Server / gcloud token)
"""

import json
import os
import ssl
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

DEFAULT_PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "seanjung-poc")
DEFAULT_DATASET_ID = os.environ.get("BQ_DATASET_ID", "starter_ontology_dw")
DEFAULT_LOCATION = os.environ.get("BQ_LOCATION", "asia-northeast3")
DEFAULT_GCS_BUCKET = os.environ.get("GCS_WIKI_BUCKET", "seanjung-poc-starter-ontology")
DEFAULT_GEMINI_MODEL = os.environ.get("VERTEX_GEMINI_MODEL", "gemini-3.8-flash")
DEFAULT_SPANNER_INSTANCE = os.environ.get("SPANNER_INSTANCE_ID", "starter-spanner")
DEFAULT_SPANNER_DATABASE = os.environ.get("SPANNER_DATABASE_ID", "starter_ontology_db")
DEFAULT_BQ_SPANNER_CONN = os.environ.get("BQ_SPANNER_CONNECTION_ID", "spanner_fabric_conn")

_CAFILE = os.environ.get("SSL_CERT_FILE") or ("/etc/ssl/cert.pem" if os.path.exists("/etc/ssl/cert.pem") else None)
_CTX = ssl.create_default_context(cafile=_CAFILE)
_CACHED_TOKEN: str = ""
_TOKEN_EXPIRY: float = 0.0
_SPANNER_SESSIONS: Dict[Tuple[str, str, str], Tuple[str, float]] = {}


def get_gcp_token() -> str:
    """Retrieves a valid GCP OAuth2 access token from Cloud Run Metadata Server or gcloud CLI."""
    global _CACHED_TOKEN, _TOKEN_EXPIRY
    now = time.time()
    if _CACHED_TOKEN and now < _TOKEN_EXPIRY:
        return _CACHED_TOKEN

    # 1. Cloud Run / GCE Metadata Server
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
                    _CACHED_TOKEN = tok
                    _TOKEN_EXPIRY = now + 2400
                    return tok
        except Exception:
            pass

    # 2. Local gcloud CLI token (prioritize admin@seanjung.altostrat.com for seanjung-poc)
    for cmd in (
        ["gcloud", "auth", "print-access-token", "admin@seanjung.altostrat.com"],
        ["gcloud", "auth", "print-access-token"],
        ["gcloud", "auth", "application-default", "print-access-token"],
    ):
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            if r.returncode == 0 and r.stdout.strip().startswith("ya29."):
                _CACHED_TOKEN = r.stdout.strip()
                _TOKEN_EXPIRY = now + 2400
                return _CACHED_TOKEN
        except Exception:
            pass

    raise RuntimeError(
        "GCP Authentication token unavailable. Please run `gcloud auth login` (admin@seanjung.altostrat.com)."
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


def execute_bq_sql(
    sql: str,
    project_id: str = DEFAULT_PROJECT_ID,
    location: str = DEFAULT_LOCATION,
    timeout_ms: int = 60000,
) -> Dict[str, Any]:
    """Executes a real BigQuery SQL or SQL:2023 GQL query via BigQuery REST API."""
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


def upload_gcs_object(
    object_name: str,
    content_bytes: bytes,
    bucket: str = DEFAULT_GCS_BUCKET,
    content_type: str = "text/markdown; charset=utf-8",
) -> Dict[str, Any]:
    """Uploads an object to the real Google Cloud Storage bucket."""
    token = get_gcp_token()
    encoded = urllib.parse.quote(object_name, safe="")
    url = f"https://storage.googleapis.com/upload/storage/v1/b/{bucket}/o?uploadType=media&name={encoded}"
    req = urllib.request.Request(
        url,
        data=content_bytes,
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": content_type,
        },
    )
    with urllib.request.urlopen(req, context=_CTX, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def list_gcs_objects(prefix: str = "", bucket: str = DEFAULT_GCS_BUCKET) -> List[Dict[str, Any]]:
    """Lists objects in the real Google Cloud Storage bucket."""
    token = get_gcp_token()
    q = f"?prefix={urllib.parse.quote(prefix, safe='')}" if prefix else ""
    url = f"https://storage.googleapis.com/storage/v1/b/{bucket}/o{q}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, context=_CTX, timeout=20) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        return data.get("items", [])


def call_vertex_gemini(
    prompt: str,
    system_instruction: Optional[str] = None,
    response_mime_type: str = "text/plain",
    temperature: float = 0.1,
    max_tokens: int = 2048,
    model_name: str = DEFAULT_GEMINI_MODEL,
    project_id: str = DEFAULT_PROJECT_ID,
) -> Dict[str, Any]:
    """
    Calls the real Vertex AI Gemini model (`gemini-3.8-flash`) on `seanjung-poc`.
    Never downgrades the model silently; returns full telemetry (model, latency_ms, token usage, text).
    """
    t0 = time.perf_counter()
    token = get_gcp_token()
    url = (
        f"https://aiplatform.googleapis.com/v1/projects/{project_id}/locations/global/"
        f"publishers/google/models/{model_name}:generateContent"
    )
    gen_cfg: Dict[str, Any] = {
        "temperature": temperature,
        "maxOutputTokens": max_tokens,
        "topP": 0.95,
    }
    if response_mime_type == "application/json":
        gen_cfg["responseMimeType"] = "application/json"

    body: Dict[str, Any] = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": gen_cfg,
    }
    if system_instruction:
        body["systemInstruction"] = {"parts": [{"text": system_instruction}]}

    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, context=_CTX, timeout=45) as resp:
            raw = json.loads(resp.read().decode("utf-8"))
        elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
        candidates = raw.get("candidates", [])
        parts = candidates[0].get("content", {}).get("parts", []) if candidates else []
        text = "".join(p.get("text", "") for p in parts if "text" in p).strip()
        usage = raw.get("usageMetadata", {})
        return {
            "status": "SUCCESS",
            "model": model_name,
            "project_id": project_id,
            "elapsed_ms": elapsed_ms,
            "prompt_tokens": usage.get("promptTokenCount", 0),
            "candidates_tokens": usage.get("candidatesTokenCount", 0),
            "total_tokens": usage.get("totalTokenCount", 0),
            "text": text,
        }
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
        return {
            "status": "ERROR",
            "model": model_name,
            "project_id": project_id,
            "http_code": e.code,
            "error": err_body,
            "elapsed_ms": elapsed_ms,
            "text": "",
        }


def check_spanner_available(
    project_id: str = DEFAULT_PROJECT_ID,
    instance_id: str = DEFAULT_SPANNER_INSTANCE,
    database_id: str = DEFAULT_SPANNER_DATABASE,
) -> Dict[str, Any]:
    """Checks whether the Cloud Spanner instance and database are provisioned and READY."""
    if not instance_id or not database_id:
        return {"available": False, "reason": "SPANNER_INSTANCE_ID or SPANNER_DATABASE_ID is empty"}
    token = get_gcp_token()
    url = f"https://spanner.googleapis.com/v1/projects/{project_id}/instances/{instance_id}/databases/{database_id}"
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
    """Executes a GoogleSQL or ISO GQL (GRAPH_TABLE) query on Cloud Spanner via REST API."""
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
    """Truncates (optional) and inserts/updates rows in a Cloud Spanner table in a single transaction."""
    t0 = time.perf_counter()
    token = get_gcp_token()
    sess = _get_spanner_session(project_id, instance_id, database_id)
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
    """Executes DDL statements on Cloud Spanner via updateDdl REST API and polls until completion."""
    t0 = time.perf_counter()
    token = get_gcp_token()
    clean_stmts = [s.strip().rstrip(";").strip() for s in statements if s and s.strip()]
    url = f"https://spanner.googleapis.com/v1/projects/{project_id}/instances/{instance_id}/databases/{database_id}/ddl"
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

