# Copyright (c) 2026 Sean Jung (seanjung@google.com). All Rights Reserved.
# Non-Commercial Use Only: Methodology & Docs under CC BY-NC-ND 4.0; Source Code under PolyForm Noncommercial License 1.0.0.
# Commercial use, paid consulting/SI/PoC delivery, or production deployment requires prior written permission from seanjung@google.com.

# -*- coding: utf-8 -*-
"""
Track-Driven Project Creation, GCP Resource Recommendation & Step-by-Step Gemini Workbench (`[GRILL-011]`).
- Recommends GCP resource names (`dataset_id`, `gcs_bucket`, `gcs_prefix`, `graph_name`, `spanner_*`) from `project_id` + `track` + `graph_engine`.
- Scaffolds `projects/<project_id>/` from `projects/_template/`.
- Handles browser file uploads (`customer_doc/*` and `data/input/03_tables/*.csv` with automatic `provenance`/`source_ref` normalization).
- Executes Step-by-Step Gemini transformations (`run_workbench_step`) and real GCP provisioning/loading approvals (`approve_workbench_step`) across Stage 1 ~ Stage 5.
"""

import base64
import csv
import datetime
import glob
import hashlib
import io
import json
import os
import re
import shutil
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

from src.gcp_client import (
    DEFAULT_BQ_SPANNER_CONN,
    DEFAULT_DATASET_ID,
    DEFAULT_GCS_BUCKET,
    DEFAULT_GEMINI_MODEL,
    DEFAULT_LOCATION,
    DEFAULT_PROJECT_ID,
    DEFAULT_SPANNER_DATABASE,
    DEFAULT_SPANNER_INSTANCE,
    _CTX,
    call_vertex_gemini,
    execute_bq_sql,
    get_gcp_token,
    upload_gcs_object,
)
from src.project_context import BASE_DIR, _CACHE, get_project, list_projects

SUPPORTED_GEMINI_MODELS = (
    "gemini-3.8-flash",
    "gemini-3.1-pro-preview",
    "gemini-2.5-pro",
    "gemini-2.5-flash",
)


def _now_kst() -> str:
    tz = datetime.timezone(datetime.timedelta(hours=9))
    return datetime.datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S KST")


def _clean_id(raw_id: str) -> str:
    s = re.sub(r"[^a-z0-9-]+", "-", (raw_id or "").strip().lower()).strip("-")
    return s[:62] or "custom-ontology"


def recommend_gcp_resources(
    project_id: str,
    track: str = "standard",
    graph_engine: str = "bigquery",
    gcp_project_id: str = DEFAULT_PROJECT_ID,
) -> Dict[str, Any]:
    """Returns recommended GCP resource names tailored to project_id, track (lite/standard/full), and graph_engine."""
    pid = _clean_id(project_id)
    underscored = pid.replace("-", "_")
    upper = underscored.upper()
    norm_track = track if track in ("lite", "standard", "full") else "standard"
    norm_engine = "none" if norm_track == "lite" else (
        graph_engine if graph_engine in ("bigquery", "spanner", "both") else "bigquery"
    )
    use_spanner = norm_engine in ("spanner", "both")
    return {
        "project_id": gcp_project_id or DEFAULT_PROJECT_ID,
        "location": DEFAULT_LOCATION,
        "dataset_id": f"{underscored}_dw",
        "gcs_bucket": DEFAULT_GCS_BUCKET,
        "gcs_prefix": f"projects/{pid}/ontology",
        "graph_name": "" if norm_track == "lite" else f"{upper}_ONTOLOGY_GRAPH",
        "spanner_instance_id": DEFAULT_SPANNER_INSTANCE if use_spanner else "",
        "spanner_database_id": DEFAULT_SPANNER_DATABASE if use_spanner else "",
        "bq_spanner_connection_id": DEFAULT_BQ_SPANNER_CONN if norm_engine == "both" else "",
        "track": norm_track,
        "graph_engine": norm_engine,
    }


def _workbench_state_path(root: str) -> str:
    out_dir = os.path.join(root, "data/output")
    os.makedirs(out_dir, exist_ok=True)
    return os.path.join(out_dir, "workbench_state.json")


def _default_workbench_state(project: Dict[str, Any]) -> Dict[str, Any]:
    track = project.get("track") or "standard"
    if track == "auto":
        track = "standard" if (project.get("tables") or []) else "lite"
    is_sample = os.path.abspath(project["root"]) == os.path.abspath(BASE_DIR)
    default_st = "APPROVED" if is_sample else "PENDING"
    s3_status = "BYPASSED" if track == "lite" else default_st
    return {
        "project_id": project.get("project_id", ""),
        "track": track,
        "graph_engine": "none" if track == "lite" else (project.get("graph_engine") or "bigquery"),
        "gemini_model": project.get("gemini_model") or DEFAULT_GEMINI_MODEL,
        "updated_at": _now_kst(),
        "stages": {
            "stage1": {
                "status": default_st,
                "title_ko": "Step 1 · 입력 데이터 업로드 & 원문 추출·Gate 0 검증 · BQ 데이터셋 적재",
                "title_en": "Step 1 · Asset Upload, Gate 0 Extraction & BQ Dataset Load",
                "summary": "기본 샘플 자산 적재 완료" if is_sample else "문서(.md/.txt/.pdf) 및 정형 테이블(.csv)을 업로드한 뒤 [1. 변환 실행]을 클릭하세요.",
                "gcp_target": f"BigQuery `{project.get('gcp', {}).get('dataset_id', '')}`",
                "artifacts": [],
                "approved_at": _now_kst() if is_sample else None,
            },
            "stage2": {
                "status": default_st,
                "title_ko": "Step 2 · 최신 Gemini 기반 시맨틱 위키(3-Layer OKF) & 도메인 규칙 추출 · GCS 적재",
                "title_en": "Step 2 · Gemini Semantic Wiki (3-Layer OKF) & Domain Rules · GCS Sync",
                "summary": "3-Layer OKF 위키 및 도메인 규칙 적재 완료" if is_sample else "Stage 1 청크와 스키마를 기반으로 최신 Gemini가 엔티티·컨셉·3-Layer 위키와 도메인 규칙을 합성합니다.",
                "gcp_target": f"GCS `gs://{project.get('gcp', {}).get('gcs_bucket', DEFAULT_GCS_BUCKET)}/projects/{project.get('project_id', '')}/ontology/`",
                "artifacts": [],
                "approved_at": _now_kst() if is_sample else None,
            },
            "stage3": {
                "status": s3_status,
                "title_ko": "Step 3 · SQL:2023 Property Graph DDL 합성 & 실제 그래프 배포",
                "title_en": "Step 3 · SQL:2023 Property Graph DDL Synthesis & Live Graph Deploy",
                "summary": (
                    "Track 1 (Lite: 1→2→4) 선택에 따라 물리 Property Graph 구축 단계가 생략(Bypassed)됩니다."
                    if track == "lite"
                    else ("Property Graph 배포 완료" if is_sample else "업로드된 테이블 스키마와 도메인 규칙을 연결하는 SQL:2023 Property Graph DDL을 Gemini가 합성합니다.")
                ),
                "gcp_target": "Bypassed (Lite Track)" if track == "lite" else f"Graph `{project.get('gcp', {}).get('graph_name', 'ONTOLOGY_GRAPH')}`",
                "artifacts": [],
                "approved_at": _now_kst() if (is_sample and track != "lite") else None,
            },
            "stage4": {
                "status": default_st,
                "title_ko": "Step 4 · 도메인 맞춤 추천 질의 합성 & 에이전트/MCP 런타임 활성화",
                "title_en": "Step 4 · Domain Sample Queries & Agent/MCP Runtime Activation",
                "summary": "에이전트 및 8종 MCP 런타임 활성화 완료" if is_sample else "생성된 위키와 스키마에 맞춘 추천 질의 칩을 생성하고 에이전트 런타임을 활성화합니다.",
                "gcp_target": "Vertex AI Gemini + Live MCP Runtime",
                "artifacts": [],
                "approved_at": _now_kst() if is_sample else None,
            },
            "stage5": {
                "status": default_st,
                "title_ko": "Step 5 · 도메인 맞춤 Golden CQ 검증 세트 & 엔드투엔드 리니지 구성",
                "title_en": "Step 5 · Domain Golden CQ Suite & End-to-End Lineage",
                "summary": "Golden CQ 및 엔드투엔드 리니지 검증 완료" if is_sample else "프로젝트 자산 기반 Golden CQ 검증 문항과 리니지 DAG를 합성하고 실시간 검증합니다.",
                "gcp_target": "Live Golden CQ & Lineage Validator",
                "artifacts": [],
                "approved_at": _now_kst() if is_sample else None,
            },
        },
        "logs": [],
    }


def get_workbench_state(project: Dict[str, Any]) -> Dict[str, Any]:
    root = project["root"]
    path = _workbench_state_path(root)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            state = json.load(f)
    else:
        state = _default_workbench_state(project)
    # Sync track / engine / model with project.json
    track = project.get("track") or "standard"
    if track == "auto":
        track = "standard" if (project.get("tables") or []) else "lite"
    state["track"] = track
    state["graph_engine"] = "none" if track == "lite" else (project.get("graph_engine") or "bigquery")
    state["gemini_model"] = project.get("gemini_model") or state.get("gemini_model") or DEFAULT_GEMINI_MODEL
    rec = recommend_gcp_resources(project["project_id"], track, state["graph_engine"])
    if os.path.abspath(root) == os.path.abspath(BASE_DIR):  # bundled sample: empty project.json values use src/gcp_client.py defaults
        rec.update(dataset_id=DEFAULT_DATASET_ID, gcs_prefix="", graph_name="STARTER_ONTOLOGY_GRAPH")
    state["gcp"] = {**rec, **{k: v for k, v in (project.get("gcp") or {}).items() if v}}
    if track == "lite":
        state["stages"]["stage3"]["status"] = "BYPASSED"
        state["stages"]["stage3"]["summary"] = "Track 1 (Lite: 1→2→4) 선택에 따라 물리 Property Graph 구축 단계가 생략(Bypassed)됩니다."
    elif state["stages"]["stage3"]["status"] == "BYPASSED":
        state["stages"]["stage3"]["status"] = "APPROVED" if state["stages"]["stage3"].get("approved_at") else "PENDING"
    # Attach uploaded file inventory
    doc_dir = os.path.join(root, "customer_doc")
    guide_dir = os.path.join(root, "data/input/01_guides")
    tbl_dir = os.path.join(root, "data/input/03_tables")
    docs = sorted(f for f in (os.listdir(doc_dir) if os.path.isdir(doc_dir) else []) if not f.startswith("."))
    guides = sorted(f for f in (os.listdir(guide_dir) if os.path.isdir(guide_dir) else []) if f.endswith(".md"))
    tables = sorted(f for f in (os.listdir(tbl_dir) if os.path.isdir(tbl_dir) else []) if f.endswith(".csv"))
    table_items = []
    for t in tables:
        tp = os.path.join(tbl_dir, t)
        rc = max(0, sum(1 for _ in open(tp, encoding="utf-8", errors="replace")) - 1) if os.path.isfile(tp) else 0
        table_items.append({"name": t, "rows": rc})
    state["project_name"] = project.get("project_name") or project.get("project_id", "")
    state["supported_models"] = list(SUPPORTED_GEMINI_MODELS)
    state["files"] = {
        "customer_docs": docs,
        "guides": guides,
        "tables": tables,
        "is_sample": os.path.abspath(root) == os.path.abspath(BASE_DIR),
    }
    state["uploaded_files"] = {
        "docs": [{"name": d} for d in (docs or guides)],
        "tables": table_items,
    }
    return state


def _save_workbench_state(root: str, state: Dict[str, Any], log_msg: Optional[str] = None) -> Dict[str, Any]:
    state["updated_at"] = _now_kst()
    if log_msg:
        state.setdefault("logs", []).insert(0, f"[{state['updated_at']}] {log_msg}")
        state["logs"] = state["logs"][:30]
    with open(_workbench_state_path(root), "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    return state


def seed_sample_domain_files(root: str, project_id: str, track: str) -> Dict[str, Any]:
    """Seeds a unique B2B Cloud SaaS Subscription & SLA Penalty Policy dataset (distinct from root telecom sample)."""
    doc_dir = os.path.join(root, "customer_doc")
    tbl_dir = os.path.join(root, "data/input/03_tables")
    os.makedirs(doc_dir, exist_ok=True)
    os.makedirs(tbl_dir, exist_ok=True)

    policy_md = f"""# 엔터프라이즈 클라우드 SaaS 구독 요금제 및 SLA 위약금 운영 규정 ({project_id})

제1조(목적 및 적용 범위)
본 규정은 기업 고객(Tenant)이 가입하는 엔터프라이즈 클라우드 SaaS 구독 요금제(Enterprise AI Pro, Standard Ops, Core Starter)의 약정 할인율, 의무 사용 기간, 중도 해지 위약금 및 월간 가용성 SLA 위반 시 크레딧 보상 기준을 정의한다.

제2조(구독 플랜 및 의무 약정 할인 기준)
1. Enterprise AI Pro 플랜(`PLAN_SAAS_PRO`)의 기본 월 이용료는 2,400,000원이며, 12개월 약정 가입 시 월 480,000원(20%)의 약정 할인이 제공된다. 최소 의무 유지 기간은 180일이다.
2. Standard Ops 플랜(`PLAN_SAAS_STD`)의 기본 월 이용료는 950,000원이며, 12개월 약정 가입 시 월 190,000원(20%)의 약정 할인이 제공된다. 최소 의무 유지 기간은 90일이다.
3. Core Starter 플랜(`PLAN_SAAS_CORE`)의 기본 월 이용료는 300,000원이며, 무약정 전용 상품으로 최소 의무 유지 기간은 30일이다.

제3조(중도 해지 및 플랜 하향 시 할인 반환금 산정식)
1. 고객이 의무 유지 기간(Enterprise AI Pro 180일, Standard Ops 90일) 이내에 계약을 해지하거나 하위 플랜으로 변경할 경우, 누적 제공된 약정 할인액의 100%를 할인 반환금(위약금)으로 청구한다.
2. 의무 유지 기간을 초과한 후 잔여 약정 기간 내에 해지할 경우, `할인 반환금 = 누적 할인액 × (잔여 약정일수 / (전체 약정일수 - 의무 유지일수))` 산식을 적용하여 일할 감면한다.
3. 단, 공공·교육기관 특례 고객(`PUBLIC_EDU_EXEMPT`)이거나 당초 가입일로부터 14일 이내 철회(청약 철회)인 경우 할인 반환금을 100% 면제(0원)한다.

제4조(월간 가용성 SLA 미달 시 서비스 크레딧 보상 및 해지 특례)
1. 월간 서비스 가용성이 99.9% 미만 ~ 99.0% 이상인 경우 당월 청구 금액의 10%를 크레딧으로 감액한다.
2. 월간 서비스 가용성이 99.0% 미만으로 하락한 중대 장애 발생 시 당월 청구 금액의 30%를 크레딧으로 보상하며, 해당 고객이 30일 이내 해지를 요청할 경우 약정 잔여일수와 무관하게 중도 해지 할인 반환금을 전액 면제(0원)한다.
"""
    doc_path = os.path.join(doc_dir, "cloud_saas_sla_policy_v1.md")
    with open(doc_path, "w", encoding="utf-8") as f:
        f.write(policy_md)

    seeded_tables: List[str] = []
    if track in ("standard", "full"):
        plans_csv = """plan_id,plan_name,tier_category,monthly_fee_krw,discount_monthly_krw,min_maintenance_days,sla_target_pct,provenance,source_ref
PLAN_SAAS_PRO,Enterprise AI Pro,ENTERPRISE_TIER,2400000,480000,180,99.95,CUSTOMER_PROVIDED,saas_billing_catalog_v1.csv
PLAN_SAAS_STD,Standard Ops,BUSINESS_TIER,950000,190000,90,99.90,CUSTOMER_PROVIDED,saas_billing_catalog_v1.csv
PLAN_SAAS_CORE,Core Starter,STARTER_TIER,300000,0,30,99.50,CUSTOMER_PROVIDED,saas_billing_catalog_v1.csv
"""
        subs_csv = """subscription_id,tenant_id,tenant_name,plan_id,commitment_days,elapsed_days,accumulated_discount_krw,monthly_sla_actual_pct,exemption_type,status,provenance,source_ref
SUB_9001,TENANT_ALPHA,알파핀테크,PLAN_SAAS_PRO,365,120,1920000,99.98,NONE,ACTIVE,CUSTOMER_PROVIDED,tenant_subscriptions_v1.csv
SUB_9002,TENANT_BETA,베타바이오,PLAN_SAAS_PRO,365,240,3840000,98.75,SLA_BREACH,ACTIVE,CUSTOMER_PROVIDED,tenant_subscriptions_v1.csv
SUB_9003,TENANT_GAMMA,감마교육원,PLAN_SAAS_STD,365,60,380000,99.92,PUBLIC_EDU_EXEMPT,ACTIVE,CUSTOMER_PROVIDED,tenant_subscriptions_v1.csv
"""
        for fname, content in (("saas_plans.csv", plans_csv), ("tenant_subscriptions.csv", subs_csv)):
            with open(os.path.join(tbl_dir, fname), "w", encoding="utf-8") as f:
                f.write(content)
            seeded_tables.append(f"data/input/03_tables/{fname}")

    meta_path = os.path.join(root, "project.json")
    if os.path.exists(meta_path):
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
        meta["tables"] = seeded_tables
        if not meta.get("domain"):
            meta["domain"] = "Enterprise Cloud SaaS Subscription & SLA Penalty Policy"
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
            f.write("\n")

    return {"seeded_docs": ["cloud_saas_sla_policy_v1.md"], "seeded_tables": seeded_tables}


def create_project_workspace(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Creates a new project under `projects/<project_id>/` configured for the chosen Track, Graph Engine & Gemini Model."""
    raw_id = payload.get("project_id") or ""
    pid = _clean_id(raw_id)
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,62}", pid):
        return {"status": "ERROR", "error": "project_id must be 2~63 lowercase alphanumeric characters or hyphens."}

    track = payload.get("track") if payload.get("track") in ("lite", "standard", "full") else "standard"
    engine = "none" if track == "lite" else (
        payload.get("graph_engine") if payload.get("graph_engine") in ("bigquery", "spanner", "both") else "bigquery"
    )
    model = payload.get("gemini_model") if payload.get("gemini_model") in SUPPORTED_GEMINI_MODELS else DEFAULT_GEMINI_MODEL
    rec = recommend_gcp_resources(pid, track, engine, payload.get("gcp_project_id") or DEFAULT_PROJECT_ID)

    # Allow user overrides of recommended GCP names
    user_gcp = payload.get("gcp") or payload.get("gcp_overrides") or {}
    for k in ("project_id", "dataset_id", "gcs_bucket", "gcs_prefix", "graph_name", "spanner_instance_id", "spanner_database_id"):
        if user_gcp.get(k):
            rec[k] = str(user_gcp[k]).strip()

    dst = os.path.join(BASE_DIR, "projects", pid)
    if not os.path.exists(dst):
        shutil.copytree(os.path.join(BASE_DIR, "projects/_template"), dst)
        for name in ("portal_profile.json", "eval_rubric.json"):
            src_cfg = os.path.join(BASE_DIR, "config", name)
            if os.path.exists(src_cfg):
                os.makedirs(os.path.join(dst, "config"), exist_ok=True)
                shutil.copy(src_cfg, os.path.join(dst, "config", name))

    meta_path = os.path.join(dst, "project.json")
    meta = {}
    if os.path.exists(meta_path):
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)

    meta.update({
        "project_id": pid,
        "project_name": (payload.get("project_name") or pid).strip(),
        "customer_org": (payload.get("customer_org") or "Enterprise Customer").strip(),
        "domain": (payload.get("domain") or "Custom Ontology Domain").strip(),
        "track": track,
        "graph_engine": "bigquery" if engine == "none" else engine,
        "gemini_model": model,
        "graph_engine_reason": f"Configured via Studio Workbench (track={track}, engine={engine}, model={model})",
        "gcp": {
            "project_id": rec["project_id"],
            "dataset_id": rec["dataset_id"],
            "gcs_bucket": rec["gcs_bucket"],
            "gcs_prefix": rec["gcs_prefix"],
            "graph_name": rec["graph_name"],
            "spanner_instance_id": rec["spanner_instance_id"],
            "spanner_database_id": rec["spanner_database_id"],
            "bq_spanner_connection_id": rec["bq_spanner_connection_id"],
        },
    })
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
        f.write("\n")

    if payload.get("seed_sample"):
        seed_sample_domain_files(dst, pid, track)

    proj = get_project(pid)
    wb = _default_workbench_state(proj)
    _save_workbench_state(
        dst,
        wb,
        f"신규 프로젝트 `{pid}` 생성 완료 (Track={track}, Engine={engine}, Model={model}, Dataset={rec['dataset_id']})",
    )
    return {
        "status": "SUCCESS",
        "project_id": pid,
        "project": {k: v for k, v in proj.items() if k != "root"},
        "recommended_gcp": rec,
        "workbench": get_workbench_state(proj),
    }


create_new_project_workspace = create_project_workspace


def reconfigure_project_track(project_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Updates an existing project's track, graph_engine, and gemini_model dynamically from the Studio UI."""
    proj = get_project(project_id)
    root = proj["root"]
    is_sample = os.path.abspath(root) == os.path.abspath(BASE_DIR)
    meta_path = os.path.join(root, "config/project.json" if is_sample else "project.json")
    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)

    track = payload.get("track") if payload.get("track") in ("lite", "standard", "full") else meta.get("track", "full")
    engine = payload.get("graph_engine") if payload.get("graph_engine") in ("none", "bigquery", "spanner", "both") else meta.get("graph_engine", "bigquery")
    model = payload.get("gemini_model") if payload.get("gemini_model") in SUPPORTED_GEMINI_MODELS else meta.get("gemini_model", DEFAULT_GEMINI_MODEL)

    meta["track"] = track
    meta["graph_engine"] = "bigquery" if engine == "none" else engine
    meta["gemini_model"] = model
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
        f.write("\n")

    _CACHE.pop((project_id, "engine"), None)
    _CACHE.pop((project_id, "lineage"), None)
    updated_proj = get_project(project_id)
    wb = get_workbench_state(updated_proj)
    _save_workbench_state(root, wb, f"프로젝트 트랙/엔진 재구성: track={track}, engine={engine}, model={model}")
    return {"status": "SUCCESS", "project": {k: v for k, v in updated_proj.items() if k != "root"}, "workbench": wb}


def _normalize_csv_provenance(csv_text: str, filename: str) -> str:
    """Ensures every uploaded CSV has `provenance` and `source_ref` columns required by Gate 0."""
    reader = csv.DictReader(io.StringIO(csv_text))
    if not reader.fieldnames:
        return csv_text
    fieldnames = list(reader.fieldnames)
    if "provenance" not in fieldnames:
        fieldnames.append("provenance")
    if "source_ref" not in fieldnames:
        fieldnames.append("source_ref")
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    for row in reader:
        if not (row.get("provenance") or "").strip():
            row["provenance"] = "CUSTOMER_PROVIDED"
        if not (row.get("source_ref") or "").strip():
            row["source_ref"] = filename
        writer.writerow(row)
    return out.getvalue()


def upload_project_files(project_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Saves uploaded documents (`customer_doc/`) and CSV tables (`data/input/03_tables/`) into the project workspace."""
    proj = get_project(project_id)
    root = proj["root"]
    if os.path.abspath(root) == os.path.abspath(BASE_DIR):
        return {
            "status": "ERROR",
            "error": "기본 샘플 프로젝트는 보호되어 있습니다. [+ 선택 트랙으로 신규 프로젝트 생성]을 눌러 새 프로젝트에 업로드하세요.",
        }

    track = proj.get("track") or "standard"
    if payload.get("seed_sample"):
        seeded = seed_sample_domain_files(root, project_id, track)
        proj = get_project(project_id)
        wb = get_workbench_state(proj)
        _save_workbench_state(root, wb, f"샘플 도메인 파일 자동 적재 완료: 문서 {len(seeded['seeded_docs'])}건, 테이블 {len(seeded['seeded_tables'])}건")
        return {"status": "SUCCESS", "seeded": seeded, "workbench": get_workbench_state(proj)}

    files = payload.get("files") or []
    doc_dir = os.path.join(root, "customer_doc")
    tbl_dir = os.path.join(root, "data/input/03_tables")
    os.makedirs(doc_dir, exist_ok=True)
    os.makedirs(tbl_dir, exist_ok=True)

    saved_docs, saved_tables = [], []
    for item in files:
        fname = os.path.basename(item.get("filename") or item.get("name") or "").strip()
        if not fname:
            continue
        ext = os.path.splitext(fname)[1].lower()
        content_b64 = item.get("content_base64")
        content_text = item.get("content") or ""
        if ext == ".csv":
            if content_b64 and not content_text:
                content_text = base64.b64decode(content_b64).decode("utf-8", errors="replace")
            norm_csv = _normalize_csv_provenance(content_text, fname)
            dst_path = os.path.join(tbl_dir, fname)
            with open(dst_path, "w", encoding="utf-8") as f:
                f.write(norm_csv)
            saved_tables.append(f"data/input/03_tables/{fname}")
        elif ext in (".md", ".txt", ".pdf", ".docx"):
            dst_path = os.path.join(doc_dir, fname)
            if content_b64:
                with open(dst_path, "wb") as f:
                    f.write(base64.b64decode(content_b64))
            else:
                with open(dst_path, "w", encoding="utf-8") as f:
                    f.write(content_text)
            saved_docs.append(fname)

    meta_path = os.path.join(root, "project.json")
    if os.path.exists(meta_path) and saved_tables:
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
        existing = set(meta.get("tables") or [])
        meta["tables"] = sorted(existing.union(saved_tables))
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
            f.write("\n")

    proj = get_project(project_id)
    wb = get_workbench_state(proj)
    _save_workbench_state(root, wb, f"파일 업로드 완료: 문서 {len(saved_docs)}건({', '.join(saved_docs)}), CSV 테이블 {len(saved_tables)}건")
    return {"status": "SUCCESS", "saved_docs": saved_docs, "saved_tables": saved_tables, "workbench": get_workbench_state(proj)}


def _infer_bq_type(values: List[str]) -> str:
    non_empty = [v.strip() for v in values if v is not None and str(v).strip() != ""]
    if not non_empty:
        return "STRING"
    if all(re.fullmatch(r"-?\d+", v) for v in non_empty):
        return "INT64"
    if all(re.fullmatch(r"-?\d+(?:\.\d+)?", v) for v in non_empty):
        return "FLOAT64"
    return "STRING"


def _profile_project_tables(root: str) -> List[Dict[str, Any]]:
    profiles = []
    for p in sorted(glob.glob(os.path.join(root, "data/input/03_tables/*.csv"))):
        tname = os.path.splitext(os.path.basename(p))[0]
        bq_table = tname if tname.startswith("tb_") else f"tb_{tname}"
        with open(p, "r", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        cols = list(rows[0].keys()) if rows else []
        col_types = {c: _infer_bq_type([r.get(c, "") for r in rows]) for c in cols}
        pk_cand = next((c for c in cols if c.endswith("_id")), cols[0] if cols else "id")
        fk_cands = [c for c in cols if c.endswith("_id") and c != pk_cand]
        profiles.append({
            "csv_file": os.path.basename(p),
            "table_name": bq_table,
            "row_count": len(rows),
            "columns": [{"name": c, "bq_type": col_types[c]} for c in cols],
            "primary_key": pk_cand,
            "foreign_keys": fk_cands,
            "sample_rows": rows[:3],
        })
    return profiles


def ensure_bq_dataset(project_id: str, dataset_id: str, location: str = DEFAULT_LOCATION) -> Dict[str, Any]:
    """Ensures a BigQuery dataset exists in `location`, creating it via BigQuery REST API if missing."""
    token = get_gcp_token()
    get_url = f"https://bigquery.googleapis.com/bigquery/v2/projects/{project_id}/datasets/{dataset_id}"
    req = urllib.request.Request(get_url, headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req, context=_CTX, timeout=15) as resp:
            info = json.loads(resp.read().decode("utf-8"))
            return {"status": "EXISTS", "dataset_id": dataset_id, "location": info.get("location", location)}
    except urllib.error.HTTPError as e:
        if e.code != 404:
            return {"status": "ERROR", "http_code": e.code, "error": e.read().decode("utf-8", errors="replace")}

    post_url = f"https://bigquery.googleapis.com/bigquery/v2/projects/{project_id}/datasets"
    body = {
        "datasetReference": {"projectId": project_id, "datasetId": dataset_id},
        "location": location,
        "description": f"Provisioned by Agentic Ontology Starter Workbench ({dataset_id})",
    }
    preq = urllib.request.Request(
        post_url,
        data=json.dumps(body).encode("utf-8"),
        method="POST",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(preq, context=_CTX, timeout=20) as resp:
            info = json.loads(resp.read().decode("utf-8"))
            return {"status": "CREATED", "dataset_id": dataset_id, "location": info.get("location", location)}
    except urllib.error.HTTPError as e:
        return {"status": "ERROR", "http_code": e.code, "error": e.read().decode("utf-8", errors="replace")}


def _sql_literal(val: Any, bq_type: str = "STRING") -> str:
    if val is None or str(val).strip() == "":
        return "NULL"
    s = str(val).strip()
    if bq_type == "INT64":
        try:
            return str(int(s))
        except Exception:
            return "NULL"
    if bq_type == "FLOAT64":
        try:
            return repr(float(s))
        except Exception:
            return "NULL"
    esc = s.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n").replace("\r", "")
    return f"'{esc}'"


def run_workbench_step(project_id: str, stage: str, model_name: Optional[str] = None) -> Dict[str, Any]:
    """Executes the Gemini-powered transformation for `stage1`..`stage5` and saves artifacts for user review."""
    proj = get_project(project_id)
    root = proj["root"]
    wb = get_workbench_state(proj)
    track = wb["track"]
    model = model_name if model_name in SUPPORTED_GEMINI_MODELS else wb.get("gemini_model", DEFAULT_GEMINI_MODEL)
    wb["gemini_model"] = model
    gcp = wb["gcp"]
    ds_fqn = f"{gcp['project_id']}.{gcp['dataset_id']}"

    if stage == "stage1":
        # Sample data is added only by the explicit seed button, never automatically.
        dirs = (os.path.join(root, "customer_doc"), os.path.join(root, "data/input/01_guides"))
        if not any(os.path.isdir(d) and [f for f in os.listdir(d) if not f.startswith(".")] for d in dirs):
            return {"status": "ERROR", "stage": "stage1", "error": "입력 문서가 없습니다. 문서를 업로드하거나 [샘플 도메인 데이터 시드]를 먼저 실행하세요."}

        from pipeline.extract_docs import extract_project
        from pipeline.ingest import build_chunks
        from pipeline.validator import run_gate0

        ext_res = extract_project(root, {"track": track, "track_reason": f"track={track} workbench"})
        guide_files, chunks = build_chunks(root=root)
        os.makedirs(os.path.join(root, "data/output"), exist_ok=True)
        chunk_path = os.path.join(root, "data/output/doc_chunks.jsonl")
        with open(chunk_path, "w", encoding="utf-8") as f:
            for c in chunks:
                f.write(json.dumps(c, ensure_ascii=False) + "\n")
        g0 = run_gate0(chunks, root=root)
        table_profiles = _profile_project_tables(root) if track != "lite" else []

        prompt = (
            f"[프로젝트 정보] ID={project_id}, Track={track}, Target BigQuery Dataset=`{ds_fqn}`\n"
            f"[문서 청크 ({len(chunks)}건)]\n"
            + "\n".join(f"- {c['chunk_id']} ({c['source_doc']}): {c['content'][:180]}" for c in chunks[:8])
            + f"\n\n[정형 CSV 테이블 프로파일 ({len(table_profiles)}종)]\n"
            + json.dumps(table_profiles, ensure_ascii=False, indent=2)
            + "\n\n위 입력 자산을 바탕으로 1) 핵심 도메인 요약(2문장), 2) 식별된 핵심 엔티티/키 구조, 3) 추천 BigQuery 적재 테이블 구성을 한국어 4줄 이내로 간결하게 요약하세요."
        )
        llm_res = call_vertex_gemini(prompt=prompt, temperature=0.1, max_tokens=600, model_name=model)
        ai_note = llm_res.get("text") or f"Gemini 요약 실패 ({llm_res.get('status')} {llm_res.get('http_code', '')})"

        wb["stages"]["stage1"].update({
            "status": "TRANSFORMED",
            "summary": (
                f"원문 추출 {len(guide_files)}건 · 청크 {len(chunks)}건 · Gate 0 `{g0.get('status')}` · "
                f"CSV 테이블 {len(table_profiles)}종 프로파일링 완료 (Gemini `{model}` · {llm_res.get('elapsed_ms', 0)} ms)\n{ai_note}"
            ),
            "artifacts": ["data/output/input_manifest.json", "data/output/doc_chunks.jsonl", "data/output/gate0_report.json"],
            "table_profiles": table_profiles,
            "chunk_count": len(chunks),
            "gate0_status": g0.get("status"),
            "llm_telemetry": {
                "model": model,
                "elapsed_ms": llm_res.get("elapsed_ms", 0),
                "tokens": llm_res.get("total_tokens", 0),
            },
        })
        _save_workbench_state(root, wb, f"[Stage 1 변환 완료] 청크 {len(chunks)}건, Gate 0={g0.get('status')}, 테이블 {len(table_profiles)}종 (Model={model})")
        return {"status": "SUCCESS", "stage": "stage1", "workbench": get_workbench_state(proj)}

    if stage == "stage2":
        chunk_file = os.path.join(root, "data/output/doc_chunks.jsonl")
        if not os.path.exists(chunk_file):
            run_workbench_step(project_id, "stage1", model_name=model)
        with open(chunk_file, "r", encoding="utf-8") as f:
            chunks = [json.loads(line) for line in f if line.strip()]
        table_profiles = _profile_project_tables(root) if track != "lite" else []

        chunks_text = "\n\n".join(f"[{c['chunk_id']}] ({c.get('source_doc')})\n{c['content']}" for c in chunks)
        sys_inst = """당신은 엔터프라이즈 온톨로지 아키텍트입니다. 제공된 [문서 청크]와 [테이블 스키마]만 근거로 JSON 한 개를 출력하세요.
출력 JSON 스키마:
{
  "domain_title": "도메인 제목",
  "executive_summary_Bullets": ["핵심 요약 1", "핵심 요약 2", "핵심 요약 3"],
  "entities": [
    {"id": "ENT_01", "name": "엔티티명", "category": "ACTOR|PRODUCT|CONTRACT|POLICY", "table_mapping": "매핑 테이블명 또는 DOC_ONLY", "description": "설명", "source_chunk_id": "DOC_CHUNK_001", "quote": "원문 발췌 구절(120자 이내)"}
  ],
  "concepts": [
    {"id": "REL_01", "from": " 엔티티명", "to": "대상 엔티티명", "kind": "PRECONDITION|POSTCONDITION|CONSTRAINT|GOVERNED_BY", "statement": "관계 및 제약조건 설명", "source_chunk_id": "DOC_CHUNK_001", "quote": "원문 발췌 구절(120자 이내)"}
  ],
  "domain_rules": [
    {"rule_id": "RULE_01", "rule_name": "규칙명", "rule_category": "PENALTY|DISCOUNT|EXEMPTION|SLA", "condition_expr": "적용 조건식", "formula_expr": "산식 또는 판정식", "source_chunk_id": "DOC_CHUNK_001", "description_ko": "한국어 상세 설명"}
  ],
  "glossary": [
    {"term": "용어명", "definition": "문서 기반 정의", "mapped_column": "관련 컬럼 또는 청크 ID"}
  ]
}
규칙: 반드시 실제 청크 ID(DOC_CHUNK_001 등)와 문서에 있는 사실만 사용하세요."""
        prompt = f"[문서 청크]\n{chunks_text}\n\n[테이블 스키마]\n{json.dumps(table_profiles, ensure_ascii=False)}"
        llm_res = call_vertex_gemini(
            prompt=prompt,
            system_instruction=sys_inst,
            response_mime_type="application/json",
            temperature=0.0,
            max_tokens=4096,
            model_name=model,
        )
        parsed = {}
        if llm_res.get("status") == "SUCCESS":
            try:
                parsed = json.loads(llm_res["text"])
            except Exception:
                parsed = {}

        if not parsed:
            return {"status": "ERROR", "stage": "stage2",
                    "error": f"Gemini `{model}` 응답을 JSON으로 읽지 못했습니다 ({llm_res.get('status')} {str(llm_res.get('error', ''))[:200]}). 저장한 파일 없음."}
        text_of = {c["chunk_id"]: c["content"] for c in chunks}
        quoted = lambda x: bool(x.get("quote")) and x["quote"] in text_of.get(x.get("source_chunk_id"), "")  # noqa: E731
        entities = [e for e in parsed.get("entities") or [] if quoted(e)]
        concepts = [c for c in parsed.get("concepts") or [] if quoted(c)]
        rules = [r for r in parsed.get("domain_rules") or [] if r.get("rule_id") and r.get("source_chunk_id") in text_of]
        dropped = sum(len(parsed.get(k) or []) for k in ("entities", "concepts", "domain_rules")) - len(entities) - len(concepts) - len(rules)
        glossary = parsed.get("glossary") or []
        domain_title = parsed.get("domain_title") or proj.get("domain") or project_id

        wiki_dir = os.path.join(root, "data/llm_wiki")
        os.makedirs(wiki_dir, exist_ok=True)
        summary_md = (
            f"# Enterprise Knowledge Wiki: Executive Summary (`{project_id}`)\n"
            f"- **Domain**: {domain_title}\n"
            f"- **Track & Engine**: `{track}` · Graph Engine `{wb['graph_engine']}` · Dataset `{ds_fqn}`\n"
            f"- **Extracted by**: Vertex AI `{model}` (`{llm_res.get('elapsed_ms', 0)} ms`)\n"
            f"- **Total Chunks / Tables / Rules**: {len(chunks)} chunks · {len(table_profiles)} tables · {len(rules)} domain rules\n\n"
            "## Key Domain Takeaways\n"
            + "\n".join(f"- {b}" for b in (parsed.get("executive_summary_Bullets") or [f"총 {len(entities)}개 핵심 엔티티 및 {len(rules)}개 도메인 비즈니스 규칙 추출 완료."]))
            + "\n"
        )
        entities_md = (
            f"# Knowledge Wiki: Domain Entities (`{project_id}`)\n"
            f"Extracted by Vertex AI `{model}` · {len(entities)} entities grounded in `{len(chunks)}` document chunks.\n\n"
            + "\n".join(
                f"- **{e.get('id', f'E{i+1:02d}')} {e.get('name')}** (`{e.get('category', 'ENTITY')}` · Table: `{e.get('table_mapping', 'DOC_ONLY')}`)\n"
                f"  - 설명: {e.get('description')}\n"
                f"  - 근거: `{e.get('source_chunk_id')}` — \"{e.get('quote', '')}\""
                for i, e in enumerate(entities)
            )
            + "\n"
        )
        concepts_md = (
            f"# Knowledge Wiki: Semantic Concepts & Relations (`{project_id}`)\n"
            f"Extracted by Vertex AI `{model}` · {len(concepts)} semantic relations.\n\n"
            + "\n".join(
                f"- **{c.get('from')} -[{c.get('kind', 'RELATES_TO')}]-> {c.get('to')}**\n"
                f"  - 규칙/제약: {c.get('statement')}\n"
                f"  - 근거: `{c.get('source_chunk_id')}` — \"{c.get('quote', '')}\""
                for c in concepts
            )
            + "\n"
        )
        rules_md = (
            f"# Knowledge Wiki:Executable Domain Rules (`{project_id}`)\n\n"
            "| Rule ID | 규칙명 | 카테고리 | 조건식 (`condition_expr`) | 산식/판정 (`formula_expr`) | 근거 청크 |\n"
            "| :--- | :--- | :---: | :--- | :--- | :---: |\n"
            + "\n".join(
                f"| `{r.get('rule_id')}` | **{r.get('rule_name')}** | `{r.get('rule_category')}` | `{r.get('condition_expr')}` | `{r.get('formula_expr')}` | `{r.get('source_chunk_id')}` |"
                for r in rules
            )
            + "\n"
        )
        glossary_md = (
            f"# Knowledge Wiki: Domain Glossary (`{project_id}`)\n\n"
            + "\n".join(f"- **{g.get('term')}**: {g.get('definition')} (`{g.get('mapped_column', '-')}`)" for g in glossary)
            + "\n"
        )
        for fname, content in (
            ("summary.md", summary_md),
            ("entities.md", entities_md),
            ("concepts.md", concepts_md),
            ("rules.md", rules_md),
            ("glossary.md", glossary_md),
            ("index.md", summary_md + "\n" + entities_md),
        ):
            with open(os.path.join(wiki_dir, fname), "w", encoding="utf-8") as f:
                f.write(content)

        # Save proposed_domain_rules.json and update semantic_graph in graph_topology.json
        rules_out = os.path.join(root, "data/output/proposed_domain_rules.json")
        with open(rules_out, "w", encoding="utf-8") as f:
            json.dump(rules, f, ensure_ascii=False, indent=2)

        sem_nodes = [{
            "id": "HUB_SEMANTIC",
            "label": f"{project_id} 시맨틱 허브",
            "label_ko": f"{project_id} 시맨틱 허브",
            "label_en": f"{project_id} Semantic Hub",
            "group": "hub",
            "color": "#0284c7",
            "desc_ko": f"OKF 3-Layer Wiki & Semantic Hub ({model})",
            "desc_en": f"OKF 3-Layer Wiki & Semantic Hub ({model})",
        }]
        name_to_id = {}
        for i, e in enumerate(entities):
            nid = e.get("id") or f"ENT_{i+1:02d}"
            ename = (e.get("name") or nid).strip()
            name_to_id[ename] = nid
            sem_nodes.append({
                "id": nid,
                "label": ename,
                "label_ko": ename,
                "label_en": ename,
                "group": "entity",
                "color": "#2563eb",
                "desc_ko": f"{e.get('description', '')} (근거: {e['source_chunk_id']})",
                "desc_en": f"{e.get('description', '')} (Source: {e['source_chunk_id']})",
            })
        for r in rules:
            rid = r["rule_id"]
            rlabel = f"{rid}: {r.get('rule_name', '')}"
            sem_nodes.append({
                "id": rid,
                "label": rlabel,
                "label_ko": rlabel,
                "label_en": rlabel,
                "group": "rule",
                "color": "#d97706",
                "desc_ko": f"{r.get('condition_expr', '')} -> {r.get('formula_expr', '')} ({r.get('description_ko', '')})",
                "desc_en": f"{r.get('condition_expr', '')} -> {r.get('formula_expr', '')}",
            })
        sem_edges = []
        for n in sem_nodes[1:]:
            if n["group"] == "entity":
                sem_edges.append({
                    "from": "HUB_SEMANTIC",
                    "to": n["id"],
                    "label": "HAS_ENTITY",
                    "label_ko": "도메인 엔티티",
                    "label_en": "HAS_ENTITY",
                    "is_hub": True,
                })
        for c in concepts:
            u, v = name_to_id.get((c.get("from") or "").strip()), name_to_id.get((c.get("to") or "").strip())
            if not (u and v):  # endpoint is not an extracted entity: no edge is invented
                continue
            sem_edges.append({
                "from": u,
                "to": v,
                "label": c.get("kind", "RELATES_TO"),
                "label_ko": c.get("kind", "RELATES_TO"),
                "label_en": c.get("kind", "RELATES_TO"),
                "is_hub": False,
            })
        for r in rules:
            sem_edges.append({
                "from": "HUB_SEMANTIC",
                "to": r["rule_id"],
                "label": "HAS_RULE",
                "label_ko": "도메인 규칙",
                "label_en": "HAS_RULE",
                "is_hub": True,
            })

        topo_path = os.path.join(root, "data/output/graph_topology.json")
        topo = {}
        if os.path.exists(topo_path):
            with open(topo_path, "r", encoding="utf-8") as f:
                topo = json.load(f)
        sem_payload = {
            "description": f"OKF 3-Layer Semantic Ontology Graph for {project_id} (Synthesized by {model})",
            "nodes": sem_nodes,
            "edges": sem_edges,
        }
        topo["semantic_graph"] = sem_payload
        topo["vis_semantic_graph"] = sem_payload
        if not topo.get("vis_property_graph"):
            topo["property_graph"] = sem_payload
            topo["vis_property_graph"] = sem_payload
        with open(topo_path, "w", encoding="utf-8") as f:
            json.dump(topo, f, ensure_ascii=False, indent=2)

        wb["stages"]["stage2"].update({
            "status": "TRANSFORMED",
            "summary": (
                f"Gemini `{model}` 기반 3-Layer OKF 위키 6종(`summary.md`, `entities.md`, `concepts.md`, `rules.md`, `glossary.md`, `index.md`) 및 "
                f"엔티티 {len(entities)}개 · 컨셉 관계 {len(concepts)}개 · 도메인 규칙 {len(rules)}개 합성 (원문 인용 불일치로 제외 {dropped}건, {llm_res.get('elapsed_ms', 0)} ms)"
            ),
            "artifacts": ["data/llm_wiki/summary.md", "data/llm_wiki/entities.md", "data/llm_wiki/concepts.md", "data/llm_wiki/rules.md", "data/output/proposed_domain_rules.json"],
            "entities_count": len(entities),
            "concepts_count": len(concepts),
            "rules_count": len(rules),
            "llm_telemetry": {
                "model": model,
                "elapsed_ms": llm_res.get("elapsed_ms", 0),
                "tokens": llm_res.get("total_tokens", 0),
            },
        })
        _save_workbench_state(root, wb, f"[Stage 2 변환 완료] 엔티티 {len(entities)}개, 컨셉 {len(concepts)}개, 규칙 {len(rules)}개 합성 (Model={model})")
        return {"status": "SUCCESS", "stage": "stage2", "workbench": get_workbench_state(proj)}

    if stage == "stage3":
        if track == "lite":
            wb["stages"]["stage3"]["status"] = "BYPASSED"
            _save_workbench_state(root, wb, "[Stage 3 생략] Track 1 (Lite)은 물리 Property Graph를 생성하지 않습니다.")
            return {"status": "SUCCESS", "stage": "stage3", "workbench": get_workbench_state(proj)}

        table_profiles = _profile_project_tables(root)
        if not table_profiles:
            return {"status": "ERROR", "stage": "stage3", "error": "data/input/03_tables에 CSV 테이블이 없습니다. 테이블을 업로드하거나 Track 1 (Lite)을 선택하세요."}

        graph_name = gcp.get("graph_name") or f"{project_id.replace('-', '_').upper()}_ONTOLOGY_GRAPH"
        graph_fqn = f"`{ds_fqn}.{graph_name}`"

        # Build valid BigQuery SQL:2023 Property Graph DDL over the project's actual uploaded CSV tables + tb_doc_chunks + tb_domain_rules
        node_clauses = []
        for prof in table_profiles:
            tname = prof["table_name"]
            pk = prof["primary_key"]
            cols = ", ".join(c["name"] for c in prof["columns"])
            label = "".join(w.capitalize() for w in tname.replace("tb_", "").split("_")) + "Node"
            node_clauses.append(
                f"    `{ds_fqn}.{tname}`\n      KEY ({pk})\n      LABEL {label}\n      PROPERTIES ({cols})"
            )
        node_clauses.append(
            f"    `{ds_fqn}.tb_doc_chunks`\n      KEY (chunk_id)\n      LABEL DocChunkNode\n      PROPERTIES (chunk_id, source_doc, section_title, content, content_sha256, trust_tier)"
        )
        node_clauses.append(
            f"    `{ds_fqn}.tb_domain_rules`\n      KEY (rule_id)\n      LABEL DomainRuleNode\n      PROPERTIES (rule_id, rule_name, rule_category, condition_expr, formula_expr, source_chunk_id, description_ko)"
        )

        # Build edge clauses connecting FK tables or rule->chunk bindings
        edge_clauses = []
        pk_map = {prof["primary_key"]: prof["table_name"] for prof in table_profiles}
        for prof in table_profiles:
            src_tbl = prof["table_name"]
            src_pk = prof["primary_key"]
            for fk in prof["foreign_keys"]:
                if fk in pk_map and pk_map[fk] != src_tbl:
                    dst_tbl = pk_map[fk]
                    edge_label = f"LINKS_TO_{dst_tbl.replace('tb_', '').upper()}"
                    edge_clauses.append(
                        f"    `{ds_fqn}.{src_tbl}` AS {src_tbl}_{fk}_edge\n"
                        f"      KEY ({src_pk})\n"
                        f"      SOURCE KEY ({src_pk}) REFERENCES `{ds_fqn}.{src_tbl}` ({src_pk})\n"
                        f"      DESTINATION KEY ({fk}) REFERENCES `{ds_fqn}.{dst_tbl}` ({fk})\n"
                        f"      LABEL {edge_label}\n"
                        f"      PROPERTIES ({src_pk}, {fk})"
                    )
        edge_clauses.append(
            f"    `{ds_fqn}.tb_domain_rules` AS edge_rule_grounded_in_chunk\n"
            f"      KEY (rule_id)\n"
            f"      SOURCE KEY (rule_id) REFERENCES `{ds_fqn}.tb_domain_rules` (rule_id)\n"
            f"      DESTINATION KEY (source_chunk_id) REFERENCES `{ds_fqn}.tb_doc_chunks` (chunk_id)\n"
            f"      LABEL GROUNDED_IN_CHUNK\n"
            f"      PROPERTIES (rule_id, source_chunk_id, rule_category)"
        )

        bq_ddl = (
            f"-- [BigQuery ISO SQL:2023 Property Graph DDL · Synthesized for project `{project_id}`]\n"
            f"-- Target Dataset: {ds_fqn} | Model: {model}\n"
            f"CREATE OR REPLACE PROPERTY GRAPH {graph_fqn}\n"
            f"  NODE TABLES (\n" + ",\n".join(node_clauses) + "\n  )\n"
            f"  EDGE TABLES (\n" + ",\n".join(edge_clauses) + "\n  );\n"
        )
        spanner_ddl = bq_ddl.replace(f"`{ds_fqn}.", "`").replace(graph_fqn, f"`{graph_name}`")

        os.makedirs(os.path.join(root, "data/output"), exist_ok=True)
        with open(os.path.join(root, "data/output/create_property_graph.sql"), "w", encoding="utf-8") as f:
            f.write(bq_ddl)
        with open(os.path.join(root, "data/output/create_spanner_graph.sql"), "w", encoding="utf-8") as f:
            f.write(spanner_ddl)

        # Build property_graph nodes & edges in graph_topology.json from actual CSV rows + rules + chunks
        pg_nodes = [{
            "id": "HUB_PG",
            "label": graph_name,
            "label_ko": graph_name,
            "label_en": graph_name,
            "group": "hub",
            "color": "#0d9488",
            "desc_ko": f"Zero-ETL Property Graph (`{ds_fqn}.{graph_name}`)",
            "desc_en": f"Zero-ETL Property Graph (`{ds_fqn}.{graph_name}`)",
        }]
        pg_edges = []
        for prof in table_profiles:
            tname = prof["table_name"]
            pk = prof["primary_key"]
            name_col = next((c["name"] for c in prof["columns"] if "name" in c["name"]), pk)
            for row in prof["sample_rows"][:6]:
                nid = str(row.get(pk) or "")
                if not nid:
                    continue
                nlabel = f"{nid}\n({row.get(name_col, nid)})"
                pg_nodes.append({
                    "id": nid,
                    "label": nlabel,
                    "label_ko": nlabel,
                    "label_en": nlabel,
                    "group": "dw",
                    "color": "#2563eb",
                    "table": f"{ds_fqn}.{tname}",
                    "desc_ko": f"테이블 `{ds_fqn}.{tname}` 레코드: {json.dumps(row, ensure_ascii=False)}",
                    "desc_en": f"Table `{ds_fqn}.{tname}` record: {json.dumps(row, ensure_ascii=False)}",
                })
                pg_edges.append({
                    "from": "HUB_PG",
                    "to": nid,
                    "label": tname,
                    "label_ko": tname,
                    "label_en": tname,
                    "is_hub": True,
                })
                for fk in prof["foreign_keys"]:
                    fk_val = str(row.get(fk) or "")
                    if fk_val:
                        pg_edges.append({
                            "from": nid,
                            "to": fk_val,
                            "label": f"LINKS_TO ({fk})",
                            "label_ko": f"LINKS_TO ({fk})",
                            "label_en": f"LINKS_TO ({fk})",
                            "is_hub": False,
                            "table": f"{ds_fqn}.{tname}",
                        })

        rules_path = os.path.join(root, "data/output/proposed_domain_rules.json")
        rules = json.load(open(rules_path, encoding="utf-8")) if os.path.exists(rules_path) else []
        for r in rules[:6]:
            rid, cid = r.get("rule_id"), r.get("source_chunk_id")
            if not (rid and cid):
                continue
            rlabel = f"{rid}\n({r.get('rule_name', '')[:18]})"
            pg_nodes.append({
                "id": rid,
                "label": rlabel,
                "label_ko": rlabel,
                "label_en": rlabel,
                "group": "rule",
                "color": "#d97706",
                "table": f"{ds_fqn}.tb_domain_rules",
                "desc_ko": r.get("description_ko", ""),
                "desc_en": r.get("description_ko", ""),
            })
            pg_nodes.append({
                "id": cid,
                "label": cid,
                "label_ko": cid,
                "label_en": cid,
                "group": "chunk",
                "color": "#0d9488",
                "table": f"{ds_fqn}.tb_doc_chunks",
                "desc_ko": f"Grounded Chunk {cid}",
                "desc_en": f"Grounded Chunk {cid}",
            })
            pg_edges.append({
                "from": rid,
                "to": cid,
                "label": "GROUNDED_IN_CHUNK",
                "label_ko": "GROUNDED_IN_CHUNK",
                "label_en": "GROUNDED_IN_CHUNK",
                "is_hub": False,
                "table": f"{ds_fqn}.tb_doc_chunks",
            })

        # Dedup pg_nodes
        dedup_nodes = list({n["id"]: n for n in pg_nodes}.values())
        topo_path = os.path.join(root, "data/output/graph_topology.json")
        topo = json.load(open(topo_path, encoding="utf-8")) if os.path.exists(topo_path) else {}
        topo["graph_name"] = f"{ds_fqn}.{graph_name}"
        topo["graph_engine"] = wb["graph_engine"]
        pg_payload = {
            "description": f"ISO SQL:2023 Property Graph `{graph_name}` ({len(dedup_nodes)} nodes, {len(pg_edges)} edges)",
            "nodes": dedup_nodes,
            "edges": pg_edges,
        }
        topo["property_graph"] = pg_payload
        topo["vis_property_graph"] = pg_payload
        with open(topo_path, "w", encoding="utf-8") as f:
            json.dump(topo, f, ensure_ascii=False, indent=2)

        wb["stages"]["stage3"].update({
            "status": "TRANSFORMED",
            "summary": f"SQL:2023 Property Graph DDL(`{graph_name}`) 및 그래프 토폴로지(노드 {len(dedup_nodes)}개, 엣지 {len(pg_edges)}개) 합성 완료",
            "artifacts": ["data/output/create_property_graph.sql", "data/output/create_spanner_graph.sql", "data/output/graph_topology.json"],
        })
        _save_workbench_state(root, wb, f"[Stage 3 변환 완료] `{graph_name}` DDL 및 토폴로지 합성 완료")
        return {"status": "SUCCESS", "stage": "stage3", "workbench": get_workbench_state(proj)}

    if stage == "stage4":
        chunk_file = os.path.join(root, "data/output/doc_chunks.jsonl")
        chunks = [json.loads(x) for x in open(chunk_file, encoding="utf-8") if x.strip()] if os.path.exists(chunk_file) else []
        table_profiles = _profile_project_tables(root) if track != "lite" else []
        prompt = (
            f"[프로젝트 `{project_id}` (Track={track})]\n"
            f"[청크 샘플]\n" + "\n".join(f"- {c['chunk_id']}: {c['content'][:200]}" for c in chunks[:5])
            + f"\n[테이블 샘플]\n{json.dumps(table_profiles, ensure_ascii=False)}\n\n"
            '이 데이터에 대해 사용자가 Stage 4 에이전트에게 바로 클릭해 질문할 수 있는 구체적인 질문 4개를 JSON으로 생성하세요:\n'
            '{"questions": [{"label_ko": "버튼 라벨", "label_en": "Button Label", "query_ko": "한국어 질문", "query_en": "English Question"}]}'
        )
        llm_res = call_vertex_gemini(
            prompt=prompt,
            response_mime_type="application/json",
            temperature=0.1,
            max_tokens=1024,
            model_name=model,
        )
        q_list = []
        if llm_res.get("status") == "SUCCESS":
            try:
                q_list = json.loads(llm_res["text"]).get("questions") or []
            except Exception:
                q_list = []
        if not q_list:
            return {"status": "ERROR", "stage": "stage4", "error": f"Gemini `{model}` 추천 질의 생성 실패 ({llm_res.get('status')}). 저장한 파일 없음."}
        prof_path = os.path.join(root, "config/portal_profile.json")
        if os.path.exists(prof_path):
            prof = json.load(open(prof_path, encoding="utf-8"))
            prof["agent_questions"] = q_list
            with open(prof_path, "w", encoding="utf-8") as f:
                json.dump(prof, f, ensure_ascii=False, indent=2)

        wb["stages"]["stage4"].update({
            "status": "TRANSFORMED",
            "summary": f"Gemini `{model}` 기반 도메인 맞춤 추천 질의 {len(q_list)}건 생성 완료 (`config/portal_profile.json` 반영)",
            "artifacts": ["config/portal_profile.json"],
            "agent_questions": q_list,
        })
        _save_workbench_state(root, wb, f"[Stage 4 변환 완료] 도메인 맞춤 추천 질의 {len(q_list)}건 생성 완료")
        return {"status": "SUCCESS", "stage": "stage4", "workbench": get_workbench_state(proj)}

    if stage == "stage5":
        chunk_file = os.path.join(root, "data/output/doc_chunks.jsonl")
        chunks = [json.loads(x) for x in open(chunk_file, encoding="utf-8") if x.strip()] if os.path.exists(chunk_file) else []
        table_profiles = _profile_project_tables(root) if track != "lite" else []
        rules_path = os.path.join(root, "data/output/proposed_domain_rules.json")
        rules = json.load(open(rules_path, encoding="utf-8")) if os.path.exists(rules_path) else []

        # Lineage spec in the template format: only what this workbench actually reads and writes.
        # Volumes are measured by src/lineage/lineage_engine.py at view time and are never stored here.
        prefix = gcp.get("gcs_prefix") or f"projects/{project_id}/ontology"
        node = lambda i, cat, title, res, desc, **kw: {"id": i, "cat": cat, "title": title, "resource": res, "desc": desc, "desc_en": desc, **kw}  # noqa: E731
        edge = lambda a, b, label: {"source": a, "target": b, "label": label}  # noqa: E731
        lin_nodes = [
            node("CONN_DOCS", "DATA_CONNECTION", "customer_doc/ · 01_guides/", "customer_doc/*", "업로드 원문 → pipeline/extract_docs.py 변환", volume="Batch"),
            node("RAW_CQ", "RAW_DATASETS", "golden_competency_questions.json", "data/input/04_cq/golden_competency_questions.json", "Gemini CQ 초안 (원문 일치 확인, 정답 확정 전)", volume="JSON"),
            node("TR_CHUNK_FILE", "DATA_TRANSFORMATION", "doc_chunks.jsonl (Gate 0)", "data/output/doc_chunks.jsonl", "청크 분할 + 해시 앵커 + Gate 0", volume="JSONL"),
            node("TR_CHUNKS_BQ", "DATA_TRANSFORMATION", "tb_doc_chunks", f"{ds_fqn}.tb_doc_chunks", "Stage 1 승인 시 적재", bq_table="tb_doc_chunks"),
            node("RULE_FILE", "DOMAIN_RULES", "proposed_domain_rules.json", "data/output/proposed_domain_rules.json", "Stage 2 Gemini 추출 규칙 (근거 청크 확인)", volume="JSON"),
            node("RULE_BQ", "DOMAIN_RULES", "tb_domain_rules", f"{ds_fqn}.tb_domain_rules", "Stage 2 승인 시 적재", bq_table="tb_domain_rules"),
            node("SEM_WIKI", "ONTOLOGY_SEMANTIC", "OKF 위키 (GCS)", f"gs://{gcp['gcs_bucket']}/{prefix}/", "Stage 2 승인 시 data/llm_wiki/*.md 업로드", gcs_prefix=prefix + "/"),
            node("AGENT", "INTELLIGENT_AGENTS", "워크벤치 에이전트", "src/web/project_workbench.py", f"execute_custom_project_agent_query · Vertex AI {model}", volume=model),
            node("EVAL", "INTELLIGENT_AGENTS", "Golden CQ 평가 + 루브릭", "data/output/cq_benchmark_report.json", "Stage 5 승인 시 에이전트 답변을 인용·사실·LLM 루브릭으로 채점", volume="Report JSON"),
        ]
        lin_edges = [edge("CONN_DOCS", "TR_CHUNK_FILE", "extract + chunk"), edge("TR_CHUNK_FILE", "TR_CHUNKS_BQ", "load"),
                     edge("TR_CHUNK_FILE", "RULE_FILE", "Gemini extraction"), edge("RULE_FILE", "RULE_BQ", "load"),
                     edge("TR_CHUNK_FILE", "SEM_WIKI", "wiki"), edge("RULE_FILE", "SEM_WIKI", "rules.md"),
                     edge("TR_CHUNK_FILE", "AGENT", "chunk context"), edge("RULE_FILE", "AGENT", "rule context"),
                     edge("TR_CHUNK_FILE", "RAW_CQ", "CQ draft"), edge("RAW_CQ", "EVAL", "questions"), edge("AGENT", "EVAL", "final answer")]
        if table_profiles:
            lin_nodes.append(node("CONN_TABLES", "DATA_CONNECTION", "data/input/03_tables", "data/input/03_tables/*.csv", "업로드 CSV", volume="Batch"))
            graph = gcp.get("graph_name") if track != "lite" else ""
            if graph:
                lin_nodes.append(node("SEM_GRAPH", "ONTOLOGY_SEMANTIC", graph, f"{ds_fqn}.{graph}", "Stage 3 승인 시 CREATE PROPERTY GRAPH", bq_graph=graph))
                lin_edges += [edge("TR_CHUNKS_BQ", "SEM_GRAPH", "NODE TABLE"), edge("RULE_BQ", "SEM_GRAPH", "NODE TABLE")]
            for prof in table_profiles:
                t = prof["table_name"]
                lin_nodes.append(node(f"RAW_{t}", "RAW_DATASETS", t, f"{ds_fqn}.{t}", f"Stage 1 승인 시 {prof['csv_file']} 적재", bq_table=t))
                lin_edges += [edge("CONN_TABLES", f"RAW_{t}", "load"), edge(f"RAW_{t}", "AGENT", "SELECT … LIMIT 25")]
                if graph:
                    lin_edges.append(edge(f"RAW_{t}", "SEM_GRAPH", "NODE TABLE"))
        spec = json.load(open(os.path.join(BASE_DIR, "projects/_template/config/lineage_spec.json"), encoding="utf-8"))
        used = {n["cat"] for n in lin_nodes}
        spec.update(title=f"{project_id}: workbench lineage", nodes=lin_nodes, edges=lin_edges,
                    categories=[c for c in spec["categories"] if c["id"] in used],
                    presets=[p for p in spec.get("presets", []) if set(p["cats"]) <= used])
        os.makedirs(os.path.join(root, "config"), exist_ok=True)
        with open(os.path.join(root, "config/lineage_spec.json"), "w", encoding="utf-8") as f:
            json.dump(spec, f, ensure_ascii=False, indent=2)
        _CACHE.pop((project_id, "lineage"), None)

        # Golden CQ drafts: Gemini proposes, code keeps only quotes/facts found verbatim in the chunk.
        # They stay unconfirmed (answer_confirmed_by empty) until a person confirms the expected answer.
        cq_prompt = ("[문서 청크]\n" + "\n\n".join(f"[{c['chunk_id']}]\n{c['content']}" for c in chunks[:12])
                     + "\n\n위 청크만 근거로 업무 담당자가 실제로 물을 만한 검증 질문 3개를 만드세요. 질문마다 정답 근거 청크 1개, "
                       "그 청크에 글자 그대로 있는 인용구(quote, 80자 이내), 정답의 핵심 사실 1~3개(expected_facts, 각각 청크에 글자 그대로 있는 짧은 구절)를 적으세요. JSON만 출력:\n"
                       '{"cqs": [{"query": "질문", "chunk_id": "DOC_CHUNK_001", "quote": "원문 그대로", "expected_facts": ["원문 그대로"]}]}')
        llm_res = call_vertex_gemini(prompt=cq_prompt, response_mime_type="application/json", temperature=0.0, max_tokens=2048, model_name=model)
        try:
            drafts = json.loads(llm_res.get("text") or "{}").get("cqs") or []
        except ValueError:
            drafts = []
        text_of = {c["chunk_id"]: c["content"] for c in chunks}
        cqs = []
        for d in drafts:
            ch = text_of.get(d.get("chunk_id"), "")
            facts = [x for x in d.get("expected_facts") or [] if x and x in ch]
            if ch and d.get("query") and d.get("quote") and d["quote"] in ch and facts:
                cqs.append({"cq_id": f"CQ-{len(cqs) + 1:02d}", "category": "Document Grounded Policy Verification",
                            "evidence_type": "citation", "query": d["query"],
                            "expected_citation": {"chunk_id": d["chunk_id"], "quote": d["quote"]}, "expected_facts": facts,
                            "answer_confirmed_by": None, "drafted_by": f"Vertex AI {model}"})
        if not cqs:
            return {"status": "ERROR", "stage": "stage5",
                    "error": f"Gemini CQ 초안 {len(drafts)}건 중 원문과 일치하는 문항이 없습니다 ({llm_res.get('status')}). 리니지 스펙만 저장했습니다."}
        cq_dir = os.path.join(root, "data/input/04_cq")
        os.makedirs(cq_dir, exist_ok=True)
        with open(os.path.join(cq_dir, "golden_competency_questions.json"), "w", encoding="utf-8") as f:
            json.dump(cqs, f, ensure_ascii=False, indent=2)

        wb["stages"]["stage5"].update({
            "status": "TRANSFORMED",
            "summary": f"Golden CQ 초안 {len(cqs)}건 (Gemini 초안 {len(drafts)}건 중 원문 일치분, 정답 확정 전) · 리니지 스펙 노드 {len(lin_nodes)}개 / 엣지 {len(lin_edges)}개 작성",
            "artifacts": ["data/input/04_cq/golden_competency_questions.json", "config/lineage_spec.json"],
        })
        _save_workbench_state(root, wb, f"[Stage 5 변환 완료] Golden CQ 초안 {len(cqs)}건, 리니지 노드 {len(lin_nodes)}개")
        return {"status": "SUCCESS", "stage": "stage5", "workbench": get_workbench_state(proj)}

    return {"status": "ERROR", "error": f"Unknown stage: {stage}"}


def _bq_run(sql: str, gcp_proj: str, jobs: List[str], errors: List[str]) -> Dict[str, Any]:
    res = execute_bq_sql(sql, project_id=gcp_proj)
    if res.get("job_id"):
        jobs.append(res["job_id"])
    if res.get("status") != "SUCCESS":
        errors.append(f"{res.get('status')}: {str(res.get('error', ''))[:200]}")
    return res


def _approval_failed(root: str, wb: Dict[str, Any], stage: str, errors: List[str], proj: Dict[str, Any]) -> Dict[str, Any]:
    wb["stages"][stage].update({"status": "FAILED", "summary": f"[반영 실패] BigQuery 오류 {len(errors)}건: {' | '.join(errors)[:600]}"})
    _save_workbench_state(root, wb, f"[{stage} 반영 실패] {errors[0][:200]}")
    return {"status": "ERROR", "stage": stage, "error": errors[0], "workbench": get_workbench_state(proj)}


def approve_workbench_step(project_id: str, stage: str) -> Dict[str, Any]:
    """Approves a transformed stage and executes real GCP resource provisioning/loading (BigQuery dataset/tables/graph, GCS wiki)."""
    proj = get_project(project_id)
    root = proj["root"]
    wb = get_workbench_state(proj)
    if wb["stages"].get(stage, {}).get("status") == "PENDING":
        run_workbench_step(project_id, stage, model_name=wb.get("gemini_model"))
        wb = get_workbench_state(proj)

    gcp = wb["gcp"]
    gcp_proj = gcp["project_id"]
    dataset_id = gcp["dataset_id"]
    ds_fqn = f"{gcp_proj}.{dataset_id}"
    bucket = gcp["gcs_bucket"]
    prefix = gcp.get("gcs_prefix") or f"projects/{project_id}/ontology"

    if stage == "stage1":
        ds_res = ensure_bq_dataset(gcp_proj, dataset_id, DEFAULT_LOCATION)
        chunk_file = os.path.join(root, "data/output/doc_chunks.jsonl")
        chunks = [json.loads(x) for x in open(chunk_file, encoding="utf-8") if x.strip()] if os.path.exists(chunk_file) else []
        jobs, errors = [], ([] if ds_res.get("status") in ("EXISTS", "CREATED", "SUCCESS") else [f"dataset: {ds_res}"])

        # Create and load tb_doc_chunks in the project's BigQuery dataset
        create_chunks_sql = f"""
        CREATE OR REPLACE TABLE `{ds_fqn}.tb_doc_chunks` (
          chunk_id STRING,
          source_doc STRING,
          source_file STRING,
          section_title STRING,
          page_from INT64,
          page_to INT64,
          article_no STRING,
          content STRING,
          content_sha256 STRING,
          trust_tier STRING,
          provenance STRING
        )"""
        _bq_run(create_chunks_sql, gcp_proj, jobs, errors)
        if chunks:
            vals = []
            for c in chunks:
                vals.append(
                    "("
                    + ", ".join([
                        _sql_literal(c.get("chunk_id")),
                        _sql_literal(c.get("source_doc")),
                        _sql_literal(c.get("source_doc")),
                        _sql_literal(c.get("title")),
                        _sql_literal(c.get("page_from", 1), "INT64"),
                        _sql_literal(c.get("page_to", 1), "INT64"),
                        _sql_literal(c.get("article_no", "")),
                        _sql_literal(c.get("content", "")),
                        _sql_literal(c.get("hash_anchor", "")),
                        _sql_literal("TIER_1_OFFICIAL"),
                        _sql_literal(c.get("provenance", "EXTRACTED")),
                    ])
                    + ")"
                )
            ins_sql = f"INSERT INTO `{ds_fqn}.tb_doc_chunks` VALUES " + ", ".join(vals)
            _bq_run(ins_sql, gcp_proj, jobs, errors)

        loaded_tables = ["tb_doc_chunks"]
        if wb["track"] != "lite":
            for prof in _profile_project_tables(root):
                tname = prof["table_name"]
                col_defs = ", ".join(f"{c['name']} {c['bq_type']}" for c in prof["columns"])
                ct_sql = f"CREATE OR REPLACE TABLE `{ds_fqn}.{tname}` ({col_defs})"
                _bq_run(ct_sql, gcp_proj, jobs, errors)
                csv_path = os.path.join(root, "data/input/03_tables", prof["csv_file"])
                with open(csv_path, "r", encoding="utf-8") as f:
                    rows = list(csv.DictReader(f))
                if rows:
                    row_sqls = []
                    for row in rows:
                        row_sqls.append(
                            "(" + ", ".join(_sql_literal(row.get(c["name"]), c["bq_type"]) for c in prof["columns"]) + ")"
                        )
                    _bq_run(f"INSERT INTO `{ds_fqn}.{tname}` VALUES " + ", ".join(row_sqls), gcp_proj, jobs, errors)
                loaded_tables.append(tname)

        if errors:
            return _approval_failed(root, wb, "stage1", errors, proj)
        wb["stages"]["stage1"].update({
            "status": "APPROVED",
            "approved_at": _now_kst(),
            "summary": f"[승인 완료] BigQuery 데이터셋 `{ds_fqn}` ({ds_res.get('status')}) 내 테이블 {len(loaded_tables)}종({', '.join(loaded_tables)}) 실환경 적재 완료 (Jobs: {len(jobs)}건)",
            "bq_jobs": jobs,
        })
        _save_workbench_state(root, wb, f"[Stage 1 승인 & GCP 적재 완료] `{ds_fqn}` 테이블 {len(loaded_tables)}종 적재 (Jobs: {', '.join(jobs[:3])})")
        return {"status": "SUCCESS", "stage": "stage1", "next_stage": "stage2", "workbench": get_workbench_state(proj)}

    if stage == "stage2":
        wiki_dir = os.path.join(root, "data/llm_wiki")
        uploaded_uris = []
        if os.path.isdir(wiki_dir):
            for fname in sorted(os.listdir(wiki_dir)):
                if fname.endswith(".md"):
                    with open(os.path.join(wiki_dir, fname), "rb") as f:
                        upload_gcs_object(f"{prefix}/{fname}", f.read(), bucket=bucket)
                    uploaded_uris.append(f"gs://{bucket}/{prefix}/{fname}")

        # Also load tb_domain_rules into BigQuery
        ensure_bq_dataset(gcp_proj, dataset_id, DEFAULT_LOCATION)
        rules_path = os.path.join(root, "data/output/proposed_domain_rules.json")
        rules = json.load(open(rules_path, encoding="utf-8")) if os.path.exists(rules_path) else []
        jobs, errors = [], []
        ct_rules = f"""
        CREATE OR REPLACE TABLE `{ds_fqn}.tb_domain_rules` (
          rule_id STRING,
          rule_name STRING,
          rule_category STRING,
          condition_expr STRING,
          formula_expr STRING,
          source_chunk_id STRING,
          description_ko STRING,
          provenance STRING,
          source_ref STRING
        )"""
        _bq_run(ct_rules, gcp_proj, jobs, errors)
        if rules:
            r_vals = []
            for r in rules:
                r_vals.append(
                    "("
                    + ", ".join([
                        _sql_literal(r.get("rule_id")),
                        _sql_literal(r.get("rule_name")),
                        _sql_literal(r.get("rule_category")),
                        _sql_literal(r.get("condition_expr")),
                        _sql_literal(r.get("formula_expr")),
                        _sql_literal(r.get("source_chunk_id")),
                        _sql_literal(r.get("description_ko")),
                        _sql_literal("EXTRACTED"),
                        _sql_literal(r.get("source_chunk_id", "wiki_extractor")),
                    ])
                    + ")"
                )
            _bq_run(f"INSERT INTO `{ds_fqn}.tb_domain_rules` VALUES " + ", ".join(r_vals), gcp_proj, jobs, errors)

        if errors:
            return _approval_failed(root, wb, "stage2", errors, proj)
        next_st = "stage4" if wb["track"] == "lite" else "stage3"
        wb["stages"]["stage2"].update({
            "status": "APPROVED",
            "approved_at": _now_kst(),
            "summary": f"[승인 완료] GCS `gs://{bucket}/{prefix}/` 위키 {len(uploaded_uris)}종 업로드 및 BigQuery `{ds_fqn}.tb_domain_rules` ({len(rules)}건) 적재 완료",
            "gcs_uris": uploaded_uris,
            "bq_jobs": jobs,
        })
        _save_workbench_state(root, wb, f"[Stage 2 승인 & GCS/BQ 반영 완료] GCS {len(uploaded_uris)}종 업로드, `tb_domain_rules` {len(rules)}건 적재")
        return {"status": "SUCCESS", "stage": "stage2", "next_stage": next_st, "workbench": get_workbench_state(proj)}

    if stage == "stage3":
        if wb["track"] == "lite":
            return {"status": "SUCCESS", "stage": "stage3", "next_stage": "stage4", "workbench": get_workbench_state(proj)}
        ddl_path = os.path.join(root, "data/output/create_property_graph.sql")
        ddl_sql = open(ddl_path, encoding="utf-8").read() if os.path.exists(ddl_path) else ""
        if not ddl_sql:
            return _approval_failed(root, wb, "stage3", ["data/output/create_property_graph.sql 없음 (Stage 3 변환을 먼저 실행)"], proj)
        jobs, errors = [], []
        res = _bq_run(ddl_sql, gcp_proj, jobs, errors)
        if errors:
            return _approval_failed(root, wb, "stage3", errors, proj)
        wb["stages"]["stage3"].update({
            "status": "APPROVED",
            "approved_at": _now_kst(),
            "summary": f"[승인 완료] BigQuery SQL:2023 Property Graph `{ds_fqn}.{gcp.get('graph_name')}` 실환경 배포 완료 (Status: `{res.get('status')}`, Job: `{res.get('job_id', '-')}`)",
            "bq_job_id": res.get("job_id"),
        })
        _save_workbench_state(root, wb, f"[Stage 3 승인 & 그래프 배포 완료] `{ds_fqn}.{gcp.get('graph_name')}` (Job={res.get('job_id', '-')})")
        return {"status": "SUCCESS", "stage": "stage3", "next_stage": "stage4", "workbench": get_workbench_state(proj)}

    if stage == "stage4":
        _CACHE.pop((project_id, "engine"), None)
        wb["stages"]["stage4"].update({
            "status": "APPROVED",
            "approved_at": _now_kst(),
            "summary": f"[승인 완료] 프로젝트 `{project_id}` 전용 에이전트 및 MCP 런타임 활성화 완료 (Model: `{wb.get('gemini_model')}`, Track: `{wb['track']}`)",
        })
        _save_workbench_state(root, wb, f"[Stage 4 승인 완료] 에이전트 & MCP 런타임 활성화 (Track={wb['track']})")
        return {"status": "SUCCESS", "stage": "stage4", "next_stage": "stage5", "workbench": get_workbench_state(proj)}

    if stage == "stage5":
        # Same checks as pipeline/validator.py citation CQs, run through this project's agent.
        from types import SimpleNamespace
        from pipeline.validator import CHUNK_ID_RE, _judge, _trigrams
        cq_path = os.path.join(root, "data/input/04_cq/golden_competency_questions.json")
        cqs = json.load(open(cq_path, encoding="utf-8")) if os.path.exists(cq_path) else []
        man_path = os.path.join(root, "data/output/input_manifest.json")
        man_sha = hashlib.sha256(open(man_path, "rb").read()).hexdigest() if os.path.exists(man_path) else None
        chunk_file = os.path.join(root, "data/output/doc_chunks.jsonl")
        chunks = {c["chunk_id"]: c for c in (json.loads(x) for x in open(chunk_file, encoding="utf-8") if x.strip())} if os.path.exists(chunk_file) else {}
        judge = SimpleNamespace(model_name=wb.get("gemini_model") or DEFAULT_GEMINI_MODEL, project_id=gcp_proj)
        results = []
        for cq in cqs:
            ec, facts = cq.get("expected_citation") or {}, cq.get("expected_facts") or []
            res = execute_custom_project_agent_query(proj, cq.get("query", ""))
            body = res["lifecycle"]["step_4_synthesis"]["markdown"].split("\n\n---\n")[0]
            cited = sorted(set(CHUNK_ID_RE.findall(body)))
            found = {t: t in body for t in facts}
            outs = [d.get("output") for d in res["lifecycle"]["step_2_tool_dispatch"]["dispatched_tools"]]
            a = {"body": body, "jobs": res["bq_telemetry"]["job_ids"], "error": None if body else "empty answer",
                 "tool_outputs": json.dumps(outs, ensure_ascii=False, default=str)[:6000]}
            rubric = _judge(judge, cq.get("query", ""), " · ".join(facts), a, chunks)
            reasons = ([] if ec.get("chunk_id") in cited else [f"ANCHOR_NOT_CITED {ec.get('chunk_id')}"]) + \
                      [f"ANSWER_MISSING {t}" for t, ok in found.items() if not ok] + \
                      ([] if res["answer_status"] == "GROUNDED" else [f"ANSWER_STATUS {res['answer_status']}"]) + \
                      ([] if rubric["verdict"] == "PASS" else [f"RUBRIC_{rubric['verdict']} {rubric['scores']['total']}"])
            results.append({
                "cq_id": cq.get("cq_id"), "category": cq.get("category"), "evidence_type": "citation",
                "query": cq.get("query"), "prompt": cq.get("query"), "expected_value": " · ".join(facts),
                "actual_value": " · ".join(f"{t} {'포함' if ok else '누락'}" for t, ok in found.items()) + f" · cited {', '.join(cited) or '-'} · {res['answer_status']}",
                "grounded_chunk": ec.get("chunk_id"), "legal_anchor": ec.get("chunk_id"),
                "status": "PASSED" if not reasons else "FAILED",
                "verification_status": "CITATION_MATCH·ANSWER_MATCH·RUBRIC_PASS" if not reasons else "; ".join(reasons),
                "rubric": rubric, "answer": body, "agent_bq_job_ids": a["jobs"],
                "evidence_provenance": [chunks.get(ec.get("chunk_id"), {}).get("provenance")],
                "answer_confirmed": bool(cq.get("answer_confirmed_by")), "executed_at": _now_kst(),
            })
        tg = {r["cq_id"]: _trigrams(r["answer"]) for r in results}
        for i, x in enumerate(results):
            for y in results[i + 1:]:
                j = len(tg[x["cq_id"]] & tg[y["cq_id"]]) / max(1, len(tg[x["cq_id"]] | tg[y["cq_id"]]))
                if j >= 0.5:  # near-identical answers to different questions
                    for r in (x, y):
                        r["status"] = "FAILED"
                        r["verification_status"] += f"; DUPLICATE_ANSWER {x['cq_id']}~{y['cq_id']} {j:.2f}"
        passed_cnt = sum(r["status"] == "PASSED" for r in results)
        tot = [r["rubric"]["scores"]["total"] for r in results]
        prov = sorted({p for r in results for p in r["evidence_provenance"] if p})
        report = {
            "run_id": f"wb-{project_id}-{int(time.time())}", "evaluated_at": _now_kst(), "project_id": project_id,
            "track": wb["track"], "model": judge.model_name, "input_manifest_sha256": man_sha,
            "evidence_provenance": prov, "synthetic_basis": "SYNTHETIC_DEMO" in prov,
            "unconfirmed_cqs": sum(not r["answer_confirmed"] for r in results),
            "method": "workbench agent answer must cite the expected chunk, contain expected_facts and get a PASS from the LLM rubric judge; duplicate answers fail",
            "total_cqs": len(results), "passed": passed_cnt,
            "accuracy_rate": round(passed_cnt / len(results) * 100, 1) if results else None,
            "rubric_avg_total": round(sum(tot) / len(tot), 1) if tot else None,
            "evaluation_details": results, "test_results": results,
        }
        with open(os.path.join(root, "data/output/cq_benchmark_report.json"), "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        wb["stages"]["stage5"].update({
            "status": "APPROVED",
            "approved_at": _now_kst(),
            "summary": (f"[평가 실행] Golden CQ {passed_cnt}/{len(results)} 통과 · 루브릭 평균 {report['rubric_avg_total']} · "
                        f"정답 미확정 {report['unconfirmed_cqs']}건 (data/output/cq_benchmark_report.json)"),
        })
        _save_workbench_state(root, wb, f"[Stage 5 평가 실행] Golden CQ {passed_cnt}/{len(results)} 통과 (루브릭 평균 {report['rubric_avg_total']})")
        return {"status": "SUCCESS", "stage": "stage5", "next_stage": "overview", "workbench": get_workbench_state(proj)}

    return {"status": "ERROR", "error": f"Unknown stage: {stage}"}


def execute_custom_project_agent_query(project: Dict[str, Any], query: str, engine: str = "bigquery", lang: str = None) -> Dict[str, Any]:
    """Executes a live grounded query for a custom project (`projects/<id>/`) using its BigQuery tables, Property Graph & doc chunks."""
    t0 = time.perf_counter()
    root = project["root"]
    wb = get_workbench_state(project)
    track = wb["track"]
    model = wb.get("gemini_model") or DEFAULT_GEMINI_MODEL
    gcp = wb["gcp"]
    gcp_proj = gcp["project_id"]
    dataset_id = gcp["dataset_id"]
    ds_fqn = f"{gcp_proj}.{dataset_id}"

    chunk_file = os.path.join(root, "data/output/doc_chunks.jsonl")
    chunks = [json.loads(x) for x in open(chunk_file, encoding="utf-8") if x.strip()] if os.path.exists(chunk_file) else []
    rules_path = os.path.join(root, "data/output/proposed_domain_rules.json")
    rules = json.load(open(rules_path, encoding="utf-8")) if os.path.exists(rules_path) else []
    table_profiles = _profile_project_tables(root) if track != "lite" else []

    jobs: List[str] = []
    dispatched: List[Dict[str, Any]] = []
    bq_rows_map: Dict[str, Any] = {}

    if track != "lite" and table_profiles:
        for idx, prof in enumerate(table_profiles):
            tname = prof["table_name"]
            sql = f"SELECT * FROM `{ds_fqn}.{tname}` LIMIT 25"
            res = execute_bq_sql(sql, project_id=gcp_proj)
            if res.get("job_id"):
                jobs.append(res["job_id"])
            rows = res.get("rows") if res.get("status") == "SUCCESS" else []  # no local CSV fallback
            bq_rows_map[tname] = rows
            dispatched.append({
                "step_index": idx + 1,
                "tool_name": f"bq_query_{tname}",
                "category": "runtime_domain",
                "reason": f"Query live BigQuery table `{ds_fqn}.{tname}`",
                "output": {"status": res.get("status") or "BQ_QUERY_ERROR", "rows": rows, "job_id": res.get("job_id"),
                           "error": None if res.get("status") == "SUCCESS" else str(res.get("error", ""))[:300]},
                "intermediate_observation": f"table={ds_fqn}.{tname} · rows={len(rows)} · job={res.get('job_id', '-')}",
            })

    chunks_context = "\n\n".join(f"[{c['chunk_id']}] ({c.get('source_doc')})\n{c['content']}" for c in chunks)
    dispatched.append({
        "step_index": len(dispatched) + 1,
        "tool_name": "doc_chunk_context",
        "category": "runtime_domain",
        "reason": "Ground answer in project document chunks & domain rules",
        "output": {"status": "SUCCESS", "chunks": len(chunks), "rules": len(rules)},
        "intermediate_observation": f"chunks={len(chunks)} · rules={len(rules)} · track={track}",
    })

    sys_inst = (
        "당신은 엔터프라이즈 온톨로지 AI 에이전트입니다. 제공된 [문서 청크], [도메인 규칙], [BigQuery 테이블 조회 결과]만 근거로 한국어 Markdown 답변을 작성하세요.\n"
        "규칙:\n"
        "1. 모든 핵심 문장이나 수치 끝에 반드시 근거 청크 ID를 `[DOC_CHUNK_001]` 형식으로 인용하고, 테이블 행이나 규칙 ID(`RULE_01` 등)도 함께 명시하세요.\n"
        "2. 제공된 데이터에 없는 수치나 조건은 절대 추측하지 마세요.\n"
        "3. **결론** → **정형 테이블/규칙 계산 근거** → **원문 조항 인용(`[DOC_CHUNK_XXX]`)** 순서로 명확히 작성하세요."
    )
    prompt = (
        f"[사용자 질문]\n{query}\n\n"
        f"[프로젝트 메타데이터] project_id={project['project_id']}, track={track}, dataset={ds_fqn}\n\n"
        f"[BigQuery 테이블 조회 결과]\n{json.dumps(bq_rows_map, ensure_ascii=False, default=str)}\n\n"
        f"[도메인 규칙]\n{json.dumps(rules, ensure_ascii=False)}\n\n"
        f"[문서 청크]\n{chunks_context}"
    )
    synth = call_vertex_gemini(prompt=prompt, system_instruction=sys_inst, temperature=0.1, max_tokens=2048, model_name=model)
    body = synth.get("text") or f"Vertex AI `{model}` 호출 오류: {synth.get('error', '')}"
    cited = sorted(set(re.findall(r"DOC_CHUNK_\d{3,}", body)))
    statuses = {d["tool_name"]: d["output"]["status"] for d in dispatched}
    if synth.get("status") != "SUCCESS" or not synth.get("text"):
        answer_status = "LLM_ERROR"
    elif any(v != "SUCCESS" for v in statuses.values()):
        answer_status = "BQ_ERROR"
    elif not cited:
        answer_status = "NO_CITATION"
    elif set(cited) - {c["chunk_id"] for c in chunks}:
        answer_status = "INVALID_CITATION"
    else:
        answer_status = "GROUNDED"
    p_tok = synth.get("prompt_tokens") or 0
    c_tok = synth.get("candidates_tokens") or 0
    elapsed_s = round(time.perf_counter() - t0, 2)

    footer = (
        f"\n\n---\n"
        f"- LLM: Vertex AI `{model}` (`{gcp_proj}`) · Track `{track}` · 토큰 {p_tok + c_tok:,} (입력 {p_tok:,} / 출력 {c_tok:,}) · {synth.get('elapsed_ms', 0):,.0f} ms\n"
        f"- Dataset: `{ds_fqn}` · Graph `{gcp.get('graph_name') or 'Bypassed (Lite)'}` · Jobs `{', '.join(jobs) or 'doc-context'}`\n"
        f"- 응답 상태: `{answer_status}` · 인용 청크: `{', '.join(cited) or '-'}`"
    )
    return {
        "status": "SUCCESS",
        "engine": "bigquery",
        "track": track,
        "answer_status": answer_status,
        "query": query,
        "cited_chunks": cited,
        "applied_params": {"project_id": project["project_id"], "track": track, "dataset": ds_fqn},
        "param_notes": [],
        "llm_telemetry": {
            "model": model,
            "project_id": gcp_proj,
            "decomposition_status": None,
            "synthesis_status": synth.get("status"),
            "prompt_tokens": p_tok,
            "candidates_tokens": c_tok,
            "elapsed_ms": synth.get("elapsed_ms", 0),
        },
        "bq_telemetry": {
            "engine": "bigquery",
            "dataset": ds_fqn,
            "graph": gcp.get("graph_name") or None,
            "job_ids": jobs,
            "tool_statuses": statuses,
        },
        "lifecycle": {
            "step_1_thought": {
                "model": model,
                "extracted_parameters": {"project_id": project["project_id"], "track": track},
                "sub_goals": [{"id": f"G-0{i+1}", "goal": d["reason"], "tool": d["tool_name"], "category": d["category"]} for i, d in enumerate(dispatched)],
                "execution_mode": f"WORKBENCH_{track.upper()}_GROUNDED_CYCLE",
            },
            "step_2_tool_dispatch": {"dispatched_tools": dispatched},
            "step_3_observation": {"cross_domain_integration_reason": f"Track={track} · Tables={len(bq_rows_map)} · Chunks={len(chunks)} · Cited={cited}"},
            "step_4_synthesis": {"markdown": body + footer},
        },
        "performance": {"total_elapsed_seconds": str(elapsed_s)},
    }
