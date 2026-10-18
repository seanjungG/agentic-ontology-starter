# Copyright (c) 2026 Sean Jung (seanjung@google.com). All Rights Reserved.
# Non-Commercial Use Only: Methodology & Docs under CC BY-NC-ND 4.0; Source Code under PolyForm Noncommercial License 1.0.0.
# Commercial use, paid consulting/SI/PoC delivery, or production deployment requires prior written permission from seanjung@google.com.

# -*- coding: utf-8 -*-
"""Step 3 (verify) and step 4 (load) against the GCP resources the user entered (GOAL-223).

All calls are real REST calls with the server identity (Cloud Run SA, or the gcloud user locally). Nothing is
mocked: errors are returned with the API, HTTP code, the missing permission/role and the principal.
Writes happen only for projects in STARTER_WRITE_PROJECTS and only under:
  gs://<bucket>/starter/<lang>/…   and   <project>.<dataset>.<starter tables + graph>
"""
import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Dict, List, Optional

from src import datapack
from src.config import APP_VERSION, StarterConfig, write_allowed, write_projects
from src.gcp_client import (
    bq_dataset_create,
    bq_dataset_get,
    bq_load_json_rows,
    bq_reservation_assignments,
    bq_table_patch,
    call_core_mcp,
    call_core_mcp_tool,
    call_vertex_gemini,
    check_spanner_available,
    error_message,
    execute_bq_sql,
    execute_spanner_ddl,
    execute_spanner_sql,
    gcs_list,
    gcs_test_permissions,
    gcs_upload,
    http_call,
    project_test_permissions,
    token_principal,
    upsert_spanner_rows,
)
from src.recipes import RECIPES, load_plan

Emit = Callable[[Dict[str, Any]], None]

ROLE_FOR_PERMISSION = {
    "storage.objects.create": "roles/storage.objectAdmin",
    "storage.objects.delete": "roles/storage.objectAdmin",
    "storage.objects.get": "roles/storage.objectViewer",
    "storage.objects.list": "roles/storage.objectViewer",
    "storage.buckets.get": "roles/storage.legacyBucketReader",
    "bigquery.jobs.create": "roles/bigquery.jobUser",
    "bigquery.datasets.create": "roles/bigquery.dataEditor",
    "bigquery.datasets.get": "roles/bigquery.metadataViewer",
    "bigquery.tables.create": "roles/bigquery.dataEditor",
    "bigquery.tables.update": "roles/bigquery.dataEditor",
    "bigquery.tables.updateData": "roles/bigquery.dataEditor",
    "bigquery.tables.getData": "roles/bigquery.dataViewer",
    "bigquery.reservationAssignments.search": "roles/bigquery.resourceViewer",
    "aiplatform.endpoints.predict": "roles/aiplatform.user",
    "spanner.databases.write": "roles/spanner.databaseUser",
    "spanner.databases.read": "roles/spanner.databaseReader",
    "spanner.databases.updateDdl": "roles/spanner.databaseAdmin",
}
_PERM_RE = re.compile(r"\b((?:storage|bigquery|aiplatform|spanner)\.[A-Za-z]+\.[A-Za-z]+)\b")


def t(lang: str, ko: str, en: str) -> str:
    return en if lang == "en" else ko


def member(principal: str) -> str:
    return f"serviceAccount:{principal}" if principal.endswith(".gserviceaccount.com") else f"user:{principal}"


def missing_role(message: str) -> Optional[str]:
    m = _PERM_RE.search(message or "")
    return ROLE_FOR_PERMISSION.get(m.group(1)) if m else None


def fix_for(role: Optional[str], scope: str, cfg: StarterConfig, principal: str) -> Optional[Dict[str, str]]:
    if not role:
        return None
    if scope == "bucket":
        cmd = f"gcloud storage buckets add-iam-policy-binding gs://{cfg.bucket} --member={member(principal)} --role={role}"
    else:
        cmd = f"gcloud projects add-iam-policy-binding {cfg.project_id} --member={member(principal)} --role={role}"
    return {"role": role, "principal": principal, "command": cmd}


def _ms(t0: float) -> float:
    return round((time.perf_counter() - t0) * 1000, 1)


# ================================================================================================ verify (step 3)
def verify(cfg: StarterConfig, recipe: str, lang: str = "ko", spanner: bool = False) -> Dict[str, Any]:
    t0 = time.perf_counter()
    paths = RECIPES[recipe]["paths"]
    principal = token_principal()
    checks: List[Dict[str, Any]] = []

    def gcs_check() -> Dict[str, Any]:
        s = time.perf_counter()
        need = ["storage.objects.create", "storage.objects.get", "storage.objects.list", "storage.objects.delete"]
        code, data = gcs_test_permissions(cfg.bucket, need)
        base = {"id": "gcs", "group": "gcs", "label": t(lang, "GCS 버킷", "GCS bucket"), "target": f"gs://{cfg.bucket}",
                "api": "Core MCP · iam_test_permissions + storage_list_objects", "ms": _ms(s)}
        if code == 404:
            return {**base, "status": "error", "detail": t(lang, "버킷이 없습니다. 먼저 버킷을 만드세요.", "The bucket does not exist. Create it first."),
                    "fix": {"role": "-", "principal": principal,
                            "command": f"gcloud storage buckets create gs://{cfg.bucket} --project={cfg.project_id} --location={cfg.region}"}}
        if code != 200:
            return {**base, "status": "error", "detail": f"HTTP {code} · {error_message(data)}"}
        granted = set((data or {}).get("permissions") or [])
        miss = [p for p in need if p not in granted]
        if miss:
            return {**base, "status": "error",
                    "detail": t(lang, f"권한 부족: {', '.join(miss)}", f"Missing permissions: {', '.join(miss)}"),
                    "fix": fix_for("roles/storage.objectAdmin", "bucket", cfg, principal)}
        lc, items = gcs_list(cfg.gcs_prefix(lang), cfg.bucket)
        n = len((items or {}).get("items") or []) if lc == 200 and isinstance(items, dict) else 0
        return {**base, "status": "ok",
                "detail": t(lang, f"읽기 · 쓰기 가능 · starter/{lang}/ 기존 객체 {n}개 (적재 시 덮어씀)",
                            f"Read and write OK · {n} existing objects under starter/{lang}/ (overwritten on load)")}

    def bq_check() -> Dict[str, Any]:
        s = time.perf_counter()
        base = {"id": "bigquery", "group": "bigquery", "label": t(lang, "BigQuery 데이터셋", "BigQuery dataset"), "target": cfg.fq,
                "api": "Core MCP · bigquery_get_dataset_info + iam_test_permissions"}
        code, data = bq_dataset_get(cfg.project_id, cfg.dataset_id)
        need = ["bigquery.jobs.create", "bigquery.datasets.create", "bigquery.tables.create", "bigquery.tables.updateData",
                "bigquery.tables.getData"]
        pc, pdata = project_test_permissions(cfg.project_id, need)
        granted = set((pdata or {}).get("permissions") or []) if pc == 200 and isinstance(pdata, dict) else set()
        if code == 200:
            loc = (data or {}).get("location", "")
            if loc and loc.lower() != cfg.region.lower():
                return {**base, "ms": _ms(s), "status": "error",
                        "detail": t(lang, f"데이터셋 위치가 {loc}입니다. 리전을 {loc}로 바꾸거나 다른 데이터셋 이름을 쓰세요.",
                                    f"The dataset is in {loc}. Set the region to {loc} or use another dataset name.")}
            exists_txt = t(lang, f"있음 ({loc}) · 적재 시 테이블을 WRITE_TRUNCATE로 다시 씀", f"Exists ({loc}) · tables are rewritten with WRITE_TRUNCATE")
        elif code == 404:
            exists_txt = t(lang, "없음 · 4단계에서 생성", "Not found · created in step 4")
        elif code == 403:
            role = missing_role(error_message(data)) or "roles/bigquery.metadataViewer"
            return {**base, "ms": _ms(s), "status": "error", "detail": f"HTTP 403 · {error_message(data)}",
                    "fix": fix_for(role, "project", cfg, principal)}
        else:
            return {**base, "ms": _ms(s), "status": "error", "detail": f"HTTP {code} · {error_message(data)}"}
        if "bigquery.jobs.create" not in granted:
            return {**base, "ms": _ms(s), "status": "error",
                    "detail": t(lang, f"{exists_txt} · 작업 실행 권한(bigquery.jobs.create) 없음", f"{exists_txt} · missing bigquery.jobs.create"),
                    "fix": fix_for("roles/bigquery.jobUser", "project", cfg, principal)}
        miss = [p for p in need[1:] if p not in granted]
        if code == 404 and "bigquery.datasets.create" in miss:
            return {**base, "ms": _ms(s), "status": "error",
                    "detail": t(lang, f"{exists_txt} · 데이터셋 생성 권한 없음", f"{exists_txt} · missing bigquery.datasets.create"),
                    "fix": fix_for("roles/bigquery.dataEditor", "project", cfg, principal)}
        if miss:
            return {**base, "ms": _ms(s), "status": "warn",
                    "detail": t(lang, f"{exists_txt} · 프로젝트 수준에 없는 권한: {', '.join(miss)} (데이터셋 수준 권한이면 괜찮음)",
                                f"{exists_txt} · not granted at project level: {', '.join(miss)} (fine if granted on the dataset)"),
                    "fix": fix_for("roles/bigquery.dataEditor", "project", cfg, principal)}
        return {**base, "ms": _ms(s), "status": "ok", "detail": t(lang, f"{exists_txt} · 적재 권한 확인", f"{exists_txt} · load permissions OK")}

    def graph_check() -> Dict[str, Any]:
        s = time.perf_counter()
        base = {"id": "graph", "group": "graph", "label": t(lang, "BigQuery Graph 예약", "BigQuery Graph reservation"),
                "target": cfg.graph_fq, "api": "Core MCP · bigquery_check_reservation"}
        code, data = bq_reservation_assignments(cfg.project_id, cfg.region)
        note = t(lang, "BigQuery Graph DDL · 쿼리는 Enterprise 이상 예약이 필요합니다 (없으면 HTTP 412).",
                 "BigQuery Graph DDL and queries need an Enterprise (or Plus) reservation (HTTP 412 otherwise).")
        if code == 200 and isinstance(data, dict):
            assigns = [a for a in data.get("assignments") or [] if a.get("jobType") in ("QUERY", None)]
            for a in assigns:
                res_name = a.get("reservation_name") or a.get("name", "").split("/assignments/")[0].split("/")[-1]
                edition = a.get("edition", "")
                if not edition:
                    raw_res = a.get("name", "").split("/assignments/")[0]
                    if raw_res:
                        rc, rdata = http_call("GET", f"https://bigqueryreservation.googleapis.com/v1/{raw_res}", timeout=15)
                        edition = (rdata or {}).get("edition", "") if rc == 200 and isinstance(rdata, dict) else ""
                if edition in ("ENTERPRISE", "ENTERPRISE_PLUS"):
                    return {**base, "ms": _ms(s), "status": "ok",
                            "detail": t(lang, f"Enterprise 예약 할당됨 ({res_name}, {edition})",
                                        f"Enterprise reservation assigned ({res_name}, {edition})")}
            return {**base, "ms": _ms(s), "status": "warn",
                    "detail": t(lang, f"이 프로젝트에 Enterprise 예약 할당이 없습니다. {note}", f"No Enterprise reservation is assigned to this project. {note}"),
                    "fix": {"role": "-", "principal": principal,
                            "command": (f"bq mk --reservation --project_id={cfg.project_id} --location={cfg.region} --edition=ENTERPRISE "
                                        f"--slots=0 --autoscale_max_slots=50 starter-graph-enterprise && bq mk --reservation_assignment "
                                        f"--reservation_id={cfg.project_id}:{cfg.region}.starter-graph-enterprise --job_type=QUERY "
                                        f"--assignee_type=PROJECT --assignee_id={cfg.project_id}")}}
        return {**base, "ms": _ms(s), "status": "warn",
                "detail": t(lang, f"예약을 확인할 수 없습니다 (HTTP {code}). {note}", f"Could not read reservations (HTTP {code}). {note}"),
                "fix": fix_for("roles/bigquery.resourceViewer", "project", cfg, principal)}

    def vertex_check() -> Dict[str, Any]:
        s = time.perf_counter()
        r = call_vertex_gemini("Reply with exactly: OK", system_instruction=None, temperature=0.0, max_tokens=256,
                               model_name=cfg.model, project_id=cfg.project_id, location=cfg.vertex_location, timeout_s=60)
        base = {"id": "vertex", "group": "vertex", "label": "Vertex AI · Gemini", "target": f"{cfg.model} · {cfg.vertex_location}",
                "api": "aiplatform.generateContent", "ms": _ms(s)}
        if r.get("status") == "SUCCESS":
            return {**base, "status": "ok", "detail": t(lang, f"응답 확인 · {r.get('model')} · {round(r.get('elapsed_ms') or 0)} ms",
                                                         f"Responded · {r.get('model')} · {round(r.get('elapsed_ms') or 0)} ms")}
        code, msg = r.get("http_code"), error_message(r.get("error"))
        try:
            msg = error_message(json.loads(r.get("error") or "{}"))
        except Exception:
            pass
        role = "roles/aiplatform.user" if code == 403 else None
        return {**base, "status": "error", "detail": f"HTTP {code} · {msg}", "fix": fix_for(role, "project", cfg, principal)}

    def core_check() -> Dict[str, Any]:
        s = time.perf_counter()
        r = call_core_mcp("tools/list", url=cfg.core_mcp_url, timeout_s=30)
        tools = ((r.get("result") or {}).get("tools") or []) if r.get("status") == "SUCCESS" else []
        base = {"id": "core_mcp", "group": "core_mcp", "label": "Platform Core MCP", "target": cfg.core_mcp_url,
                "api": "MCP tools/list", "ms": _ms(s)}
        if tools:
            return {**base, "status": "ok", "detail": t(lang, f"도구 {len(tools)}개 응답 (데이터 플레인 28 + 빌드 10)",
                                                         f"{len(tools)} tools listed (28 data-plane + 10 build)")}
        return {**base, "status": "warn", "detail": f"{r.get('http_code') or ''} {error_message(r.get('error'))}".strip()}

    def spanner_check() -> Dict[str, Any]:
        s = time.perf_counter()
        info = check_spanner_available(cfg.project_id, cfg.spanner_instance, cfg.spanner_database)
        base = {"id": "spanner", "group": "spanner", "label": t(lang, "Spanner (선택)", "Spanner (optional)"),
                "target": f"{cfg.spanner_instance}/{cfg.spanner_database}", "api": "Core MCP · spanner_get_database", "ms": _ms(s)}
        if info.get("available"):
            return {**base, "status": "ok", "detail": t(lang, "READY · 적재 시 그래프도 갱신", "READY · the graph is refreshed on load")}
        return {**base, "status": "warn", "detail": f"{info.get('state') or info.get('http_code') or ''} {str(info.get('error') or info.get('reason') or '')[:240]}"}

    jobs = []
    if "P1" in paths:
        jobs.append(gcs_check)
    if "P2" in paths:
        jobs += [bq_check, graph_check]
    jobs += [vertex_check, core_check]
    if spanner and cfg.spanner_instance and cfg.spanner_database and "P2" in paths:
        jobs.append(spanner_check)
    with ThreadPoolExecutor(max_workers=6) as ex:
        results = list(ex.map(lambda f: _safe(f, lang), jobs))
    allowed = write_allowed(cfg.project_id)
    checks.append({"id": "principal", "group": "identity", "label": t(lang, "실행 주체", "Principal"), "target": principal,
                   "api": "oauth2.tokeninfo", "ms": 0, "status": "ok",
                   "detail": t(lang, "서버가 이 계정으로 GCP를 호출합니다", "The server calls GCP as this identity")})
    checks.append({"id": "guard", "group": "guard", "label": t(lang, "쓰기 허용", "Write guard"), "target": cfg.project_id,
                   "api": "STARTER_WRITE_PROJECTS", "ms": 0, "status": "ok" if allowed else "error",
                   "detail": (t(lang, "쓰기 허용 프로젝트입니다", "This project is writable") if allowed else
                              t(lang, f"이 서버는 {', '.join(write_projects())}에만 적재합니다. 다른 프로젝트는 확인 · 조회만 됩니다.",
                                f"This server loads only into {', '.join(write_projects())}. Other projects are verify / read only."))})
    checks += results
    status = "error" if any(c["status"] == "error" for c in checks) else ("warn" if any(c["status"] == "warn" for c in checks) else "ok")
    return {"status": status, "recipe": recipe, "lang": lang, "config": cfg.to_dict(), "principal": principal,
            "write_allowed": allowed, "checks": checks, "elapsed_ms": _ms(t0), "version": APP_VERSION}


def _safe(fn: Callable[[], Dict[str, Any]], lang: str) -> Dict[str, Any]:
    try:
        return fn()
    except Exception as e:  # never hide failures — show them as a failed check
        return {"id": fn.__name__, "group": "internal", "label": fn.__name__, "status": "error", "target": "-", "api": "-",
                "ms": 0, "detail": t(lang, f"확인 중 오류: {e!r}"[:300], f"Check failed: {e!r}"[:300])}


# ================================================================================================ load (step 4)
class LoadError(Exception):
    def __init__(self, message: str, fix: Optional[Dict[str, str]] = None):
        super().__init__(message)
        self.fix = fix


def run_load(cfg: StarterConfig, recipe: str, lang: str, emit: Emit, spanner: bool = False) -> Dict[str, Any]:
    t0 = time.perf_counter()
    principal = token_principal()
    plan = load_plan(recipe)
    if spanner and cfg.spanner_instance and cfg.spanner_database and "P2" in RECIPES[recipe]["paths"]:
        plan = plan + [{"key": "spanner", "node": "graph", "service": "Cloud Spanner", "core_mcp": None,
                        "t": {"ko": "Spanner 그래프 갱신 (선택)", "en": "Refresh the Spanner graph (optional)"},
                        "target": f"{cfg.spanner_instance}/{cfg.spanner_database}"}]
    fmt = {"bucket": cfg.bucket, "lang": lang, "project": cfg.project_id, "dataset": cfg.dataset_id, "graph": cfg.graph_name}
    steps = [{"key": s["key"], "node": s["node"], "service": s["service"], "core_mcp": s["core_mcp"],
              "label": s["t"][lang] if isinstance(s["t"], dict) else s["t"],
              "target": (s["target"][lang] if isinstance(s["target"], dict) else s["target"]).format(**fmt)} for s in plan]
    emit({"type": "plan", "steps": steps, "recipe": recipe, "lang": lang, "config": cfg.to_dict(), "principal": principal})
    if not write_allowed(cfg.project_id):
        msg = t(lang, f"쓰기 차단: 이 서버는 {', '.join(write_projects())} 프로젝트에만 적재합니다. 환경 변수 STARTER_WRITE_PROJECTS에 '{cfg.project_id}'를 추가해 서버를 다시 시작하세요.",
                f"Write blocked: this server only loads into {', '.join(write_projects())}. Add '{cfg.project_id}' to STARTER_WRITE_PROJECTS and restart the server.")
        emit({"type": "error", "message": msg})
        emit({"type": "done", "status": "WRITE_BLOCKED", "ms": _ms(t0)})
        return {"status": "WRITE_BLOCKED", "message": msg}
    ctx = {"objects": [], "tables": {}, "graph": None, "gate0": None, "graph_check": None}
    status = "SUCCESS"
    for i, st in enumerate(steps):
        emit({"type": "step", "key": st["key"], "status": "running", "label": st["label"]})
        s0 = time.perf_counter()
        try:
            res = STEP_FUNCS[st["key"]](cfg, recipe, lang, emit, ctx, principal)
            emit({"type": "step", "key": st["key"], "status": res.get("status", "done"), "label": st["label"],
                  "ms": _ms(s0), "detail": res.get("detail", "")})
            if res.get("status") == "warn":
                status = "PARTIAL" if status == "SUCCESS" else status
        except LoadError as e:
            emit({"type": "log", "key": st["key"], "status": "error", "api": "-", "target": st["target"], "detail": str(e), "ms": _ms(s0)})
            emit({"type": "step", "key": st["key"], "status": "error", "label": st["label"], "ms": _ms(s0), "detail": str(e)})
            emit({"type": "error", "message": str(e), "fix": e.fix})
            for rest in steps[i + 1:]:
                emit({"type": "step", "key": rest["key"], "status": "skipped", "label": rest["label"]})
            status = "ERROR"
            break
    summary = {"objects": len(ctx["objects"]), "tables": len(ctx["tables"]), "rows": sum(ctx["tables"].values()),
               "graph": ctx["graph"], "gate0": ctx["gate0"], "graph_check": ctx["graph_check"],
               "gcs_prefix": f"gs://{cfg.bucket}/{cfg.gcs_prefix(lang)}" if "P1" in RECIPES[recipe]["paths"] else None,
               "dataset": cfg.fq if "P2" in RECIPES[recipe]["paths"] else None}
    emit({"type": "done", "status": status, "ms": _ms(t0), "summary": summary})
    return {"status": status, "summary": summary, "ms": _ms(t0)}


def _log(emit: Emit, key: str, api: str, target: str, ms: float, status: str = "ok", count: Any = None, unit: str = "",
         detail: str = "", job_id: str = "") -> None:
    emit({"type": "log", "key": key, "api": api, "target": target, "count": count, "unit": unit, "ms": ms,
          "status": status, "detail": detail, "job_id": job_id})


def _http_fail(lang: str, api: str, code: int, payload: Any, cfg: StarterConfig, principal: str, scope: str) -> LoadError:
    msg = error_message(payload)
    role = missing_role(msg)
    if code == 403 and not role:
        role = {"bucket": "roles/storage.objectAdmin", "project": "roles/bigquery.dataEditor"}.get(scope)
    text = t(lang, f"{api} 실패 (HTTP {code}): {msg}", f"{api} failed (HTTP {code}): {msg}")
    if code == 403:
        text += t(lang, f" · 필요한 역할: {role} · 실행 주체: {principal}", f" · required role: {role} · principal: {principal}")
    return LoadError(text, fix_for(role, scope, cfg, principal) if code == 403 else None)


def step_gate0(cfg, recipe, lang, emit, ctx, principal):
    docs = datapack.docs(lang)
    inline = [{"bundle": "normative", "doc_stem": d["doc_id"], "content": d["text"]} for d in docs]
    args = {"project_id": f"aol_starter_{lang}", "domain_profile": "custom_starter", "inline_documents": inline, "detail_level": "compact"}
    s = time.perf_counter()
    r = call_core_mcp("tools/call", {"name": "mcp_builder_parse_documents_gate0", "arguments": args}, url=cfg.core_mcp_url, timeout_s=120)
    sc: Dict[str, Any] = {}
    if r.get("status") == "SUCCESS":
        res = r.get("result") or {}
        sc = res.get("structuredContent") or {}
        if not sc:
            try:
                sc = json.loads(((res.get("content") or [{}])[0]).get("text", "{}"))
            except Exception:
                sc = {}
    g = sc.get("gate_results") or {}
    m = sc.get("summary_metrics") or {}
    local_chunks = sum(len(d["chunks"]) for d in docs)
    if sc.get("status") in ("SUCCESS", "OK"):
        detail = t(lang, f"문서 {m.get('total_documents_parsed')}개 · 앵커 {m.get('total_anchors')}개 · 보존율 {g.get('measured_fidelity')} → {g.get('gate0_status')}",
                   f"{m.get('total_documents_parsed')} documents · {m.get('total_anchors')} anchors · fidelity {g.get('measured_fidelity')} → {g.get('gate0_status')}")
        ctx["gate0"] = {"status": g.get("gate0_status"), "fidelity": g.get("measured_fidelity"), "anchors": m.get("total_anchors")}
        _log(emit, "gate0", "Core MCP tools/call mcp_builder_parse_documents_gate0", t(lang, f"문서 {len(docs)}종", f"{len(docs)} documents"),
             _ms(s), "ok", m.get("total_anchors"), "anchors", detail)
        return {"status": "done" if g.get("gate0_status") in ("PASS", None) else "warn", "detail": detail}
    err = error_message(r.get("error")) if r.get("status") != "SUCCESS" else f"{sc.get('status')} {str(sc.get('message', ''))[:200]}"
    detail = t(lang, f"Core MCP 응답 오류: {err} · 로컬 조항 확인 {local_chunks}개로 계속 진행",
               f"Core MCP error: {err} · continuing with the local clause check ({local_chunks} clauses)")
    ctx["gate0"] = {"status": "LOCAL", "anchors": local_chunks}
    _log(emit, "gate0", "Core MCP tools/call mcp_builder_parse_documents_gate0", t(lang, f"문서 {len(docs)}종", f"{len(docs)} documents"),
         _ms(s), "warn", local_chunks, "clauses", detail)
    return {"status": "warn", "detail": detail}


def _upload(cfg, lang, emit, ctx, principal, key, name, data: bytes, content_type: str):
    s = time.perf_counter()
    obj = f"{cfg.gcs_prefix(lang)}{name}"
    code, meta = gcs_upload(obj, data, cfg.bucket, content_type)
    if code not in (200, 201):
        raise _http_fail(lang, "Core MCP storage_upload_object", code, meta, cfg, principal, "bucket")
    ctx["objects"].append(f"gs://{cfg.bucket}/{obj}")
    _log(emit, key, "Core MCP storage_upload_object", f"gs://{cfg.bucket}/{obj}", _ms(s), "ok", len(data), "bytes",
         t(lang, "업로드 완료 (덮어쓰기)", "Uploaded (overwrite)"))


def step_docs(cfg, recipe, lang, emit, ctx, principal):
    docs = datapack.docs(lang)
    for d in docs:
        _upload(cfg, lang, emit, ctx, principal, "docs", f"docs/{d['file']}", d["text"].encode("utf-8"), "text/markdown; charset=utf-8")
    return {"status": "done", "detail": t(lang, f"문서 {len(docs)}개", f"{len(docs)} documents")}


def step_wiki(cfg, recipe, lang, emit, ctx, principal):
    pages = datapack.wiki_pages(lang, recipe)
    s0 = time.perf_counter()
    sc = call_core_mcp_tool(
        "mcp_builder_compile_okf_wiki_stage2",
        {
            "project_id": f"aol_starter_{lang}",
            "inline_pages": [{"page": p["page"], "text": p["text"]} for p in pages],
            "inline_only": True,
        },
        url=cfg.core_mcp_url,
        timeout_s=30,
    )
    if sc.get("status") in ("SUCCESS", "OK"):
        sm = sc.get("summary_metrics") or {}
        _log(
            emit,
            "wiki",
            "Core MCP tools/call mcp_builder_compile_okf_wiki_stage2",
            t(lang, f"위키 {len(pages)}개 검증", f"Validate {len(pages)} wiki pages"),
            _ms(s0),
            "ok",
            sm.get("total_wiki_pages", len(pages)),
            "pages",
            t(lang, f"교차 링크 {sm.get('total_cross_links', 0)}개 확인", f"{sm.get('total_cross_links', 0)} cross-links verified"),
        )
    for p in pages:
        _upload(cfg, lang, emit, ctx, principal, "wiki", f"wiki/{p['page']}.md", p["text"].encode("utf-8"), "text/markdown; charset=utf-8")
    return {"status": "done", "detail": t(lang, f"위키 페이지 {len(pages)}개", f"{len(pages)} wiki pages")}


def step_manifest(cfg, recipe, lang, emit, ctx, principal):
    body = {"version": APP_VERSION, "recipe": recipe, "lang": lang, "loaded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "project": cfg.project_id, "dataset": cfg.fq if "P2" in RECIPES[recipe]["paths"] else None,
            "graph": ctx.get("graph"), "objects": list(ctx["objects"]), "tables": dict(ctx["tables"]), "gate0": ctx.get("gate0"),
            "wiki_pages": [p["page"] for p in datapack.wiki_pages(lang, recipe)]}
    _upload(cfg, lang, emit, ctx, principal, "manifest", "manifest.json", json.dumps(body, ensure_ascii=False, indent=1).encode("utf-8"),
            "application/json; charset=utf-8")
    return {"status": "done", "detail": f"gs://{cfg.bucket}/{cfg.gcs_prefix(lang)}manifest.json"}


def step_dataset(cfg, recipe, lang, emit, ctx, principal):
    s = time.perf_counter()
    code, data = bq_dataset_get(cfg.project_id, cfg.dataset_id)
    if code == 200:
        loc = (data or {}).get("location", "")
        if loc and loc.lower() != cfg.region.lower():
            raise LoadError(t(lang, f"데이터셋 {cfg.fq}의 위치가 {loc}입니다 (입력한 리전 {cfg.region}).",
                              f"Dataset {cfg.fq} is in {loc} (entered region {cfg.region})."))
        _log(emit, "dataset", "Core MCP bigquery_get_dataset_info", cfg.fq, _ms(s), "ok", None, "", t(lang, f"있음 ({loc})", f"Exists ({loc})"))
        return {"status": "done", "detail": t(lang, "기존 데이터셋 사용", "Using the existing dataset")}
    if code != 404:
        raise _http_fail(lang, "Core MCP bigquery_get_dataset_info", code, data, cfg, principal, "project")
    code, data = bq_dataset_create(cfg.project_id, cfg.dataset_id, cfg.region,
                                   t(lang, "Agentic Ontology Starter 데이터셋 (스타터 4단계에서 생성)", "Agentic Ontology Starter dataset (created in starter step 4)"))
    if code not in (200, 201):
        raise _http_fail(lang, "Core MCP bigquery_create_dataset", code, data, cfg, principal, "project")
    _log(emit, "dataset", "Core MCP bigquery_create_dataset", cfg.fq, _ms(s), "ok", None, "", t(lang, f"생성 ({cfg.region})", f"Created ({cfg.region})"))
    return {"status": "done", "detail": t(lang, "데이터셋 생성", "Dataset created")}


def _load_tables(cfg, lang, emit, ctx, principal, key, names: List[str]):
    def one(name: str) -> Dict[str, Any]:
        rows = datapack.table_rows(name)
        fields = datapack.bq_fields(name, lang)
        desc = datapack.table_description(name, lang)
        r = bq_load_json_rows(cfg.project_id, cfg.dataset_id, name, fields, rows, cfg.region, description=desc)
        if r.get("status") == "SUCCESS" and not r.get("patched"):
            pc, pdata = bq_table_patch(cfg.project_id, cfg.dataset_id, name, desc, fields)
            r["patch"] = pc
            r["patch_error"] = error_message(pdata) if pc != 200 else ""
        r["rows_sent"] = len(rows)
        r["table"] = name
        return r

    with ThreadPoolExecutor(max_workers=4) as ex:
        results = list(ex.map(one, names))
    failed = None
    for r in results:
        target = f"{cfg.fq}.{r['table']}"
        if r.get("status") == "SUCCESS":
            ctx["tables"][r["table"]] = r.get("output_rows") or r["rows_sent"]
            note = t(lang, "스키마 + 컬럼 설명", "schema + column descriptions") if r.get("patch") == 200 else \
                t(lang, f"설명 갱신 실패: {r.get('patch_error')}", f"description update failed: {r.get('patch_error')}")
            _log(emit, key, "Core MCP bigquery_load_table (WRITE_TRUNCATE)", target, r["elapsed_ms"], "ok", r.get("output_rows"), "rows",
                 note, r.get("job_id", ""))
        else:
            _log(emit, key, r.get("api", "Core MCP bigquery_load_table"), target, r.get("elapsed_ms", 0), "error", r["rows_sent"], "rows",
                 f"HTTP {r.get('http_code')} · {r.get('error')}", r.get("job_id", ""))
            failed = failed or r
    if failed:
        raise _http_fail(lang, f"BigQuery load {failed['table']}", int(failed.get("http_code") or 0), {"error": {"message": failed.get("error")}},
                         cfg, principal, "project")
    return {"status": "done", "detail": t(lang, f"테이블 {len(names)}개 · 행 {sum(ctx['tables'][n] for n in names)}개",
                                          f"{len(names)} tables · {sum(ctx['tables'][n] for n in names)} rows")}


def step_tables_p2(cfg, recipe, lang, emit, ctx, principal):
    return _load_tables(cfg, lang, emit, ctx, principal, "tables_p2", datapack.tables_for("B"))


def step_tables_p3(cfg, recipe, lang, emit, ctx, principal):
    p2 = set(datapack.tables_for("B"))
    return _load_tables(cfg, lang, emit, ctx, principal, "tables_p3", [n for n in datapack.tables_for("C") if n not in p2])


def step_graph(cfg, recipe, lang, emit, ctx, principal):
    ddl = datapack.graph_ddl(cfg.project_id, cfg.dataset_id, cfg.graph_name, recipe)
    emit({"type": "ddl", "sql": ddl})
    s_val = time.perf_counter()
    sc = call_core_mcp_tool(
        "mcp_builder_synthesize_bqg_stage4",
        {
            "project_id": cfg.project_id,
            "dataset_id": cfg.dataset_id,
            "graph_name": cfg.graph_name,
            "inline_ddl": ddl,
            "inline_only": True,
            "dry_run": True,
        },
        url=cfg.core_mcp_url,
        timeout_s=30,
    )
    if sc.get("status") in ("SUCCESS", "OK"):
        sm = sc.get("summary_metrics") or {}
        _log(
            emit,
            "graph",
            "Core MCP tools/call mcp_builder_synthesize_bqg_stage4",
            cfg.graph_fq,
            _ms(s_val),
            "ok",
            sm.get("total_elements"),
            "elements",
            t(lang, "Stage 4 DDL 검증 완료", "Stage 4 DDL validated"),
        )
    s = time.perf_counter()
    r = execute_bq_sql(ddl, project_id=cfg.project_id, location=cfg.region)
    if r.get("status") != "SUCCESS":
        code = int(r.get("http_code") or 0)
        msg = error_message(_jsonish(r.get("error")))
        fix = None
        if code == 412 or "reservation" in msg.lower():
            msg += t(lang, " · BigQuery Graph는 Enterprise 예약이 필요합니다 (3단계 확인 결과의 명령 참고).",
                     " · BigQuery Graph needs an Enterprise reservation (see the command in the step 3 results).")
        elif code == 403:
            raise _http_fail(lang, "Core MCP bigquery_execute_sql (DDL)", code, {"error": {"message": msg}}, cfg, principal, "project")
        _log(emit, "graph", "Core MCP bigquery_execute_sql (CREATE OR REPLACE PROPERTY GRAPH)", cfg.graph_fq, _ms(s), "error", None, "", msg)
        raise LoadError(t(lang, f"그래프 생성 실패 (HTTP {code}): {msg}", f"Graph creation failed (HTTP {code}): {msg}"), fix)
    nodes, edges = datapack.graph_elements(recipe)
    ctx["graph"] = cfg.graph_fq
    _log(emit, "graph", "Core MCP bigquery_execute_sql (CREATE OR REPLACE PROPERTY GRAPH)", cfg.graph_fq, _ms(s), "ok", len(nodes) + len(edges),
         "elements", t(lang, f"노드 테이블 {len(nodes)} · 엣지 테이블 {len(edges)}", f"{len(nodes)} node tables · {len(edges)} edge tables"),
         r.get("job_id", ""))
    return {"status": "done", "detail": cfg.graph_fq}


def _jsonish(v: Any) -> Any:
    if isinstance(v, str):
        try:
            return json.loads(v)
        except Exception:
            return {"error": {"message": v[:600]}}
    return v


def graph_check_sql(cfg: StarterConfig, recipe: str) -> str:
    g = f"`{cfg.graph_fq}`"
    parts = [
        f"(SELECT COUNT(*) FROM GRAPH_TABLE({g} MATCH (c:CustomerContractNode)-[:USES_DEVICE]->(d:DeviceNode) COLUMNS (c.contract_id AS k))) AS contract_device",
        f"(SELECT COUNT(*) FROM GRAPH_TABLE({g} MATCH (d:DeviceNode)-[:HAS_SUBSIDY_POLICY]->(p:PlanNode)<-[:APPLIES_TO_PLAN]-(r:DomainRuleNode) COLUMNS (d.device_id AS k))) AS device_plan_rule",
    ]
    if recipe == "C":
        parts += [
            f"(SELECT COUNT(*) FROM GRAPH_TABLE({g} MATCH (k:WikiConceptNode)-[:GOVERNS]->(r:DomainRuleNode)-[:GROUNDED_IN]->(c:DocChunkNode) COLUMNS (k.concept_id AS x))) AS concept_rule_clause",
            f"(SELECT COUNT(*) FROM GRAPH_TABLE({g} MATCH (r:DomainRuleNode)-[:USES_PARAM]->(p:PolicyParamNode) COLUMNS (p.param_id AS x))) AS rule_param",
            f"(SELECT COUNT(*) FROM GRAPH_TABLE({g} MATCH (s:WorkflowStepNode)-[:APPLIES_RULE]->(r:DomainRuleNode) COLUMNS (s.step_id AS x))) AS step_rule",
        ]
    return "SELECT\n  " + ",\n  ".join(parts)


def step_graph_check(cfg, recipe, lang, emit, ctx, principal):
    sql = graph_check_sql(cfg, recipe)
    s = time.perf_counter()
    r = execute_bq_sql(sql, project_id=cfg.project_id, location=cfg.region)
    if r.get("status") != "SUCCESS":
        msg = error_message(_jsonish(r.get("error")))
        _log(emit, "graph_check", "Core MCP bigquery_execute_sql (GQL)", cfg.graph_fq, _ms(s), "error", None, "", msg)
        raise LoadError(t(lang, f"그래프 확인 실패: {msg}", f"Graph check failed: {msg}"))
    row = (r.get("rows") or [{}])[0]
    ctx["graph_check"] = row
    zero = [k for k, v in row.items() if not v]
    detail = " · ".join(f"{k}={v}" for k, v in row.items())
    _log(emit, "graph_check", "Core MCP bigquery_execute_sql (GQL MATCH)", cfg.graph_fq, _ms(s), "warn" if zero else "ok",
         sum(int(v or 0) for v in row.values()), "paths", detail, r.get("job_id", ""))
    emit({"type": "gql", "sql": sql, "rows": [row]})
    return {"status": "warn" if zero else "done", "detail": detail}


# ---------------------------------------------------------------------------------------------- optional Spanner
_SPANNER_TABLES = ["tb_device_master", "tb_plan_master", "tb_subsidy_policy", "tb_customer_contract", "tb_doc_chunks", "tb_domain_rules",
                   "edge_contract_device", "edge_contract_plan", "edge_subsidy_binding", "edge_rule_applies_to_plan"]


def _spanner_statements() -> List[str]:
    with open(os.path.join(datapack.DATA, "output", "create_spanner_graph.sql"), "r", encoding="utf-8") as f:
        text = "\n".join(ln for ln in f.read().splitlines() if not ln.strip().startswith("--"))
    return [s.strip() for s in text.split(";") if s.strip()]


def spanner_columns(stmt: str) -> List[str]:
    """Column names of a `CREATE TABLE name (\\n col TYPE,\\n ...\\n) PRIMARY KEY (...)` statement."""
    body = stmt[stmt.index("(") + 1: stmt.index("\n)")]
    return [ln.strip().split()[0] for ln in body.splitlines() if ln.strip()]


def step_spanner(cfg, recipe, lang, emit, ctx, principal):
    s = time.perf_counter()
    info = check_spanner_available(cfg.project_id, cfg.spanner_instance, cfg.spanner_database)
    target = f"{cfg.spanner_instance}/{cfg.spanner_database}"
    if not info.get("available"):
        raise LoadError(t(lang, f"Spanner DB를 쓸 수 없습니다: {info.get('error') or info.get('state') or info.get('reason')}",
                          f"The Spanner database is not available: {info.get('error') or info.get('state') or info.get('reason')}"))
    existing = execute_spanner_sql("SELECT table_name FROM information_schema.tables WHERE table_schema = ''",
                                   cfg.project_id, cfg.spanner_instance, cfg.spanner_database)
    have = {r.get("table_name") for r in existing.get("rows") or []}
    stmts = _spanner_statements()
    create = [x for x in stmts if x.upper().startswith("CREATE TABLE") and x.split()[2] not in have]
    graph = [x for x in stmts if "PROPERTY GRAPH" in x.upper()]
    if create:
        d = execute_spanner_ddl(create, cfg.project_id, cfg.spanner_instance, cfg.spanner_database)
        if d.get("status") != "SUCCESS":
            raise LoadError(f"Spanner DDL: {str(d.get('error'))[:300]}")
        _log(emit, "spanner", "Core MCP spanner_update_ddl (CREATE TABLE)", target, d.get("elapsed_ms", 0), "ok", len(create), "tables")
    cols_by_table: Dict[str, List[str]] = {x.split()[2]: spanner_columns(x) for x in stmts if x.upper().startswith("CREATE TABLE")}
    total = 0
    for name in _SPANNER_TABLES:
        cols = [c for c in cols_by_table.get(name, []) if c]
        rows = [tuple(r.get(c) for c in cols) for r in datapack.table_rows(name)]
        u = upsert_spanner_rows(name, tuple(cols), rows, True, cfg.project_id, cfg.spanner_instance, cfg.spanner_database)
        if u.get("status") != "SUCCESS":
            raise LoadError(f"Spanner {name}: HTTP {u.get('http_code')} {str(u.get('error'))[:300]}")
        total += len(rows)
        _log(emit, "spanner", "Core MCP spanner_commit (insertOrUpdate)", f"{target}.{name}", u.get("elapsed_ms", 0), "ok", len(rows), "rows")
    if graph:
        d = execute_spanner_ddl(graph, cfg.project_id, cfg.spanner_instance, cfg.spanner_database)
        if d.get("status") != "SUCCESS":
            raise LoadError(f"Spanner graph DDL: {str(d.get('error'))[:300]}")
        _log(emit, "spanner", "Core MCP spanner_update_ddl (CREATE OR REPLACE PROPERTY GRAPH)", target, d.get("elapsed_ms", 0), "ok", 1, "graph")
    return {"status": "done", "detail": t(lang, f"행 {total}개 · {_ms(s)} ms", f"{total} rows · {_ms(s)} ms")}


STEP_FUNCS = {
    "gate0": step_gate0, "docs": step_docs, "wiki": step_wiki, "manifest": step_manifest, "dataset": step_dataset,
    "tables_p2": step_tables_p2, "tables_p3": step_tables_p3, "graph": step_graph, "graph_check": step_graph_check,
    "spanner": step_spanner,
}
