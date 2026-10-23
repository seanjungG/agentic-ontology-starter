# Copyright (c) 2026 Sean Jung (seanjung@google.com). All Rights Reserved.
# Non-Commercial Use Only: Methodology & Docs under CC BY-NC-ND 4.0; Source Code under PolyForm Noncommercial License 1.0.0.
# Commercial use, paid consulting/SI/PoC delivery, or production deployment requires prior written permission from seanjung@google.com.

# -*- coding: utf-8 -*-
"""Studio services (GOAL-233): presets · environment check · setup script · studio data · edits · query · search · export."""
from __future__ import annotations

import io
import json
import re
import time
import zipfile
from typing import Any, Dict, List, Optional

from src import identity
from src.aos import agent as agent_mod
from src.aos.sources import parse_gs
from src.aos.ws import (McpLog, WsError, error_text, get_json, now_iso, prefix, put_json, read_calls, save, t)
from src.config import APP_VERSION, GITHUB_URL
from src.gcp_client import call_core_mcp, call_vertex_gemini, runtime_settings, token_principal

PRESETS = [
    {"id": "telecom", "sample": True, "question_type": "W3",
     "title": ("통신사 단말 지원금 · 위약금 상담", "Telecom handset subsidy & penalty support"),
     "customer": ("통신사 고객센터 · 대리점", "Telecom contact center & retail stores"),
     "objective": ("상담원이 고객의 계약 · 단말 · 요금제 정보를 근거로 공시지원금, 선택약정 할인, 중도 해지 위약금을 규정에 맞게 안내하고 계산한다.",
                   "Support agents explain and calculate public subsidies, selective-discount options and early-termination penalties from the customer's contract, device and plan, following the policy."),
     "data": ("정책 가이드 2종 + 단말 · 요금제 · 지원금 · 계약 · 규칙 테이블 6종 (샘플 팩 포함)", "2 policy guides + 6 tables: devices, plans, subsidies, contracts, rules (sample pack included)")},
    {"id": "cosmetics", "sample": False, "question_type": "W3",
     "title": ("화장품 표시 · 광고 컴플라이언스 심사", "Cosmetics labeling & advertising compliance"),
     "customer": ("화장품 제조사 마케팅 · 법무팀", "Cosmetics maker — marketing & legal"),
     "objective": ("광고 문구와 제품 표시 사항이 화장품법 · 표시광고 가이드라인에 맞는지 판정하고, 위반 시 근거 조항과 수정안을 제시한다.",
                   "Decide whether ad copy and product labels comply with cosmetics law and labeling/advertising guidelines, and give the clause and a fix when they do not."),
     "data": ("가이드라인 · 심의 기준 문서 + 제품 · 성분 · 광고 문구 테이블", "guideline & review-criteria documents + product, ingredient and ad-copy tables")},
    {"id": "finance", "sample": False, "question_type": "W3",
     "title": ("금융 상품 약관 · 수수료 안내", "Financial product terms & fees"),
     "customer": ("은행 · 카드사 상담 조직", "Bank / card company service desk"),
     "objective": ("고객의 상품 가입 정보와 거래 내역을 근거로 약관상 수수료 · 우대 조건 · 해지 환급금을 계산하고 안내한다.",
                   "Calculate and explain fees, preferential conditions and cancellation refunds under the product terms from the customer's subscription and transactions."),
     "data": ("상품 약관 · 수수료 규정 문서 + 상품 · 고객 가입 · 거래 테이블", "terms & fee-rule documents + product, subscription and transaction tables")},
    {"id": "insurance", "sample": False, "question_type": "W3",
     "title": ("보험 청구 심사 · 지급 판정", "Insurance claim review & payout decision"),
     "customer": ("보험사 보상 심사팀", "Insurer claims-review team"),
     "objective": ("청구 건의 계약 · 담보 · 진단 정보를 약관과 심사 기준에 비춰 지급 여부와 지급액을 판정하고 근거를 제시한다.",
                   "Decide payout eligibility and amount for a claim from its policy, coverage and diagnosis data against the terms and review criteria, with evidence."),
     "data": ("약관 · 심사 기준 문서 + 계약 · 담보 · 청구 테이블", "terms & review-criteria documents + policy, coverage and claim tables")},
    {"id": "custom", "sample": False, "question_type": "W1",
     "title": ("직접 입력", "Custom"), "customer": ("", ""), "objective": ("", ""), "data": ("내 문서 · 테이블", "your documents and tables")},
]


def presets(lang: str) -> List[Dict[str, Any]]:
    i = 1 if lang == "en" else 0
    return [{"id": p["id"], "sample": p["sample"], "question_type": p["question_type"], "title": p["title"][i],
             "customer": p["customer"][i], "objective": p["objective"][i], "data": p["data"][i]} for p in PRESETS]


# ------------------------------------------------------------------------------------------------ environment check
def check_env(env: Dict[str, str], lang: str) -> Dict[str, Any]:
    log = McpLog("check", None)
    checks: List[Dict[str, Any]] = []
    who = identity.current()
    principal = who.get("principal") or token_principal()
    member = ("serviceAccount:" if principal.endswith("gserviceaccount.com") else "user:") + principal

    def add(key: str, status: str, label: str, detail: str = "", fix: str = "", ms: int = 0) -> None:
        checks.append({"key": key, "status": status, "label": label, "detail": detail, "fix": fix, "ms": ms})
    s = time.perf_counter()
    tl = call_core_mcp("tools/list", timeout_s=30)
    names = [x.get("name") for x in ((tl.get("result") or {}).get("tools") or [])]
    kh = [n for n in names if str(n).startswith("aos_core_")]
    add("core_mcp", "ok" if len(kh) >= 6 else ("warn" if names else "error"), t(lang, "Platform Core MCP 연결", "Platform Core MCP"),
        f"{len(names)} tools · know-how {len(kh)}" if names else str(tl.get("error"))[:200],
        "" if kh else t(lang, "Core MCP를 1.4.0 이상(노하우 도구 포함)으로 배포하세요", "Deploy Core MCP ≥ 1.4.0 (with know-how tools)"), round((time.perf_counter() - s) * 1000))
    s = time.perf_counter()
    bperm = ["storage.objects.create", "storage.objects.get", "storage.objects.list"]
    r = log.call("iam_test_permissions", {"bucket": env["bucket"], "bucket_permissions": bperm}, timeout_s=30)
    have = r.get("bucket_permissions") or r.get("permissions") or []
    miss = [p for p in bperm if p not in have]
    add("bucket", "ok" if r.get("status") == "SUCCESS" and not miss else "error", t(lang, "GCS 버킷 권한", "GCS bucket permissions"),
        f"gs://{env['bucket']} · " + ("OK" if not miss and r.get("status") == "SUCCESS" else (", ".join(miss) or error_text(r))[:200]),
        f"gcloud storage buckets add-iam-policy-binding gs://{env['bucket']} --member={member} --role=roles/storage.objectAdmin",
        round((time.perf_counter() - s) * 1000))
    s = time.perf_counter()
    pperm = ["bigquery.datasets.create", "bigquery.jobs.create", "bigquery.tables.create", "aiplatform.endpoints.predict"]
    r = log.call("iam_test_permissions", {"project": env["project"], "project_permissions": pperm}, timeout_s=30)
    have = r.get("project_permissions") or r.get("permissions") or []
    miss = [p for p in pperm if p not in have]
    fixes = []
    if any(p.startswith("bigquery.datasets") or p.startswith("bigquery.tables") for p in miss):
        fixes.append(f"gcloud projects add-iam-policy-binding {env['project']} --member={member} --role=roles/bigquery.dataEditor --condition=None")
    if "bigquery.jobs.create" in miss:
        fixes.append(f"gcloud projects add-iam-policy-binding {env['project']} --member={member} --role=roles/bigquery.jobUser --condition=None")
    if "aiplatform.endpoints.predict" in miss:
        fixes.append(f"gcloud projects add-iam-policy-binding {env['project']} --member={member} --role=roles/aiplatform.user --condition=None")
    add("project", "ok" if r.get("status") == "SUCCESS" and not miss else ("warn" if r.get("status") == "SUCCESS" else "error"),
        t(lang, "프로젝트 권한 (BigQuery · Vertex AI)", "Project permissions (BigQuery · Vertex AI)"),
        env["project"] + " · " + ("OK" if not miss and r.get("status") == "SUCCESS" else (", ".join(miss) or error_text(r))[:200]),
        "\n".join(fixes), round((time.perf_counter() - s) * 1000))
    s = time.perf_counter()
    d = log.call("bigquery_get_dataset_info", {"project": env["project"], "dataset": env["dataset"]}, timeout_s=30)
    if d.get("status") == "SUCCESS" and d.get("exists"):
        loc = (d.get("dataset") or {}).get("location", "")
        st = "ok" if not loc or loc.lower() == env["region"].lower() else "error"
        add("dataset", st, t(lang, "BigQuery 데이터셋", "BigQuery dataset"), f"{env['project']}.{env['dataset']} · {loc}",
            "" if st == "ok" else t(lang, "리전을 데이터셋 위치와 맞추거나 다른 데이터셋 이름을 쓰세요", "match the region to the dataset location or use another dataset"),
            round((time.perf_counter() - s) * 1000))
    else:
        add("dataset", "ok" if d.get("status") == "SUCCESS" else "warn", t(lang, "BigQuery 데이터셋", "BigQuery dataset"),
            f"{env['project']}.{env['dataset']} · " + (t(lang, "없음 → S0에서 생성", "not found → created in S0") if d.get("status") == "SUCCESS" else error_text(d)[:200]),
            "", round((time.perf_counter() - s) * 1000))
    s = time.perf_counter()
    rv = log.call("bigquery_check_reservation", {"project": env["project"], "location": env["region"]}, timeout_s=30)
    ent = bool(rv.get("has_enterprise"))
    add("reservation", "ok" if ent else "warn", t(lang, "BigQuery Graph (Enterprise 예약)", "BigQuery Graph (Enterprise reservation)"),
        ", ".join(rv.get("editions") or []) or (t(lang, "할당 없음 — 그래프 DDL은 412, 에이전트는 SQL로 동작", "no assignment — graph DDL returns 412, agents use SQL") if rv.get("status") == "SUCCESS" else error_text(rv)[:200]),
        "" if ent else (f"bq mk --reservation --project_id={env['project']} --location={env['region']} --edition=ENTERPRISE --slots=0 --autoscale_max_slots=50 aos-graph\n"
                        f"bq mk --reservation_assignment --reservation_id={env['project']}:{env['region']}.aos-graph --job_type=QUERY --assignee_type=PROJECT --assignee_id={env['project']}"),
        round((time.perf_counter() - s) * 1000))
    s = time.perf_counter()
    g = call_vertex_gemini("Reply with OK.", max_tokens=256, model_name=env["model"], project_id=env["project"], location=env["vertex_location"],
                           thinking_level="LOW", timeout_s=60)
    add("gemini", "ok" if g.get("status") == "SUCCESS" else "error", f"Vertex AI · {env['model']}",
        f"{env['project']} · {g.get('elapsed_ms', 0):.0f} ms" if g.get("status") == "SUCCESS" else f"HTTP {g.get('http_code')} {str(g.get('error'))[:200]}",
        f"gcloud services enable aiplatform.googleapis.com --project={env['project']}\n"
        f"gcloud projects add-iam-policy-binding {env['project']} --member={member} --role=roles/aiplatform.user --condition=None",
        round((time.perf_counter() - s) * 1000))
    errors = sum(1 for c in checks if c["status"] == "error")
    return {"status": "OK" if not errors else "FAIL", "identity": {**who, "principal": principal}, "checks": checks,
            "errors": errors, "warnings": sum(1 for c in checks if c["status"] == "warn")}


def setup_script(env: Dict[str, str], lang: str, sa_name: str = "aos-starter") -> str:
    runtime_sa = ""
    try:
        with identity.bind(None, None):
            runtime_sa = token_principal()
    except Exception:  # noqa: BLE001
        runtime_sa = ""
    c = (lambda ko, en: f"# {en if lang == 'en' else ko}")
    lines = [
        "#!/usr/bin/env bash",
        c("Agentic Ontology Starter — 내 GCP 환경 준비 스크립트 (그대로 실행)", "Agentic Ontology Starter — prepare your GCP environment (run as is)"),
        "set -euo pipefail",
        f"PROJECT={env['project']}", f"REGION={env['region']}", f"BUCKET={env['bucket']}", f"SA_NAME={sa_name}",
        'SA="${SA_NAME}@${PROJECT}.iam.gserviceaccount.com"', "",
        c("1) API 활성화", "1) enable APIs"),
        "gcloud services enable bigquery.googleapis.com storage.googleapis.com aiplatform.googleapis.com \\",
        "  iamcredentials.googleapis.com bigqueryreservation.googleapis.com --project=\"$PROJECT\"", "",
        c("2) 버킷 (이미 있으면 건너뜀)", "2) bucket (skipped if it exists)"),
        'gcloud storage buckets describe "gs://$BUCKET" >/dev/null 2>&1 || \\',
        '  gcloud storage buckets create "gs://$BUCKET" --project="$PROJECT" --location="$REGION" --uniform-bucket-level-access', "",
        c("3) 스타터 전용 서비스 계정 + 최소 역할", "3) dedicated service account + least-privilege roles"),
        'gcloud iam service-accounts describe "$SA" --project="$PROJECT" >/dev/null 2>&1 || \\',
        '  gcloud iam service-accounts create "$SA_NAME" --project="$PROJECT" --display-name="Agentic Ontology Starter"',
        "for ROLE in roles/bigquery.dataEditor roles/bigquery.jobUser roles/aiplatform.user; do",
        '  gcloud projects add-iam-policy-binding "$PROJECT" --member="serviceAccount:$SA" --role="$ROLE" --condition=None >/dev/null',
        "done",
        'gcloud storage buckets add-iam-policy-binding "gs://$BUCKET" --member="serviceAccount:$SA" --role=roles/storage.objectAdmin >/dev/null', "",
        c("4) BigQuery Graph용 Enterprise 예약 (없으면 그래프 DDL이 412, 에이전트는 SQL로 동작)", "4) Enterprise reservation for BigQuery Graph (without it graph DDL returns 412 and agents use SQL)"),
        'bq mk --reservation --project_id="$PROJECT" --location="$REGION" --edition=ENTERPRISE --slots=0 --autoscale_max_slots=50 aos-graph || true',
        'bq mk --reservation_assignment --reservation_id="$PROJECT:$REGION.aos-graph" --job_type=QUERY --assignee_type=PROJECT --assignee_id="$PROJECT" || true', "",
        c("5-A) 공개 스타터에서 쓰기: 내가 SA 토큰을 발급해 3단계에 붙여 넣기 (1시간 유효)", "5-A) Using the public starter: mint an SA token yourself and paste it in step 3 (valid 1 h)"),
        'gcloud iam service-accounts add-iam-policy-binding "$SA" --member="user:$(gcloud config get-value account)" --role=roles/iam.serviceAccountTokenCreator >/dev/null',
        'gcloud auth print-access-token --impersonate-service-account="$SA"', "",
    ]
    if runtime_sa and runtime_sa.endswith("gserviceaccount.com"):
        lines += [c("5-B) (선택 · 허용된 서버만) 스타터 서버가 SA 토큰을 직접 발급하도록 위임", "5-B) (optional · allow-listed servers only) let the starter server mint SA tokens"),
                  f'gcloud iam service-accounts add-iam-policy-binding "$SA" --member="serviceAccount:{runtime_sa}" --role=roles/iam.serviceAccountTokenCreator', ""]
    lines += [c("6) 내 Cloud Run에 스타터 배포 (선택)", "6) deploy the starter to your own Cloud Run (optional)"),
              f"# git clone {GITHUB_URL} && cd agentic-ontology-starter",
              '# gcloud run deploy agentic-ontology-starter --source . --region="$REGION" --project="$PROJECT" --service-account="$SA" \\',
              f'#   --set-env-vars=GCP_PROJECT_ID=$PROJECT,BQ_LOCATION=$REGION,GCS_WIKI_BUCKET=$BUCKET,STARTER_WRITE_PROJECTS=$PROJECT,CORE_MCP_URL={runtime_settings()["core_mcp_url"]}',
              'echo "OK — SA: $SA"']
    return "\n".join(lines) + "\n"


# ------------------------------------------------------------------------------------------------ studio data
DATA_FILES = {"docs": "parsed/docs.json", "tables": "parsed/tables.json", "wiki": "wiki/pages.json", "gates": "wiki/gates.json",
              "graph": "graph/plan.json", "cqs": "cqs.json", "run": "runs/latest.json"}


def studio_data(ws: Dict[str, Any], what: List[str]) -> Dict[str, Any]:
    b, pf = ws["env"]["bucket"], prefix(ws["ws_id"])
    out: Dict[str, Any] = {"ws": ws}
    for w in what:
        if w == "calls":
            out["calls"] = read_calls(b, ws["ws_id"])[-400:]
        elif w in DATA_FILES:
            data = get_json(None, b, pf + DATA_FILES[w], None)
            if w == "docs" and isinstance(data, list):
                data = [{**d, "text": d.get("text", "")[:80000]} for d in data]
            if w == "tables" and isinstance(data, list):
                data = [{**x, "rows": (x.get("rows") or [])[:30]} for x in data]
            out[w] = data
    return out


def save_cqs(ws: Dict[str, Any], cqs: List[Dict[str, Any]]) -> Dict[str, Any]:
    clean = []
    for i, c in enumerate(cqs[:60]):
        if not isinstance(c, dict) or not str(c.get("question") or "").strip():
            continue
        typ = c.get("type") if c.get("type") in ("doc", "data", "hybrid") else "hybrid"
        ag = c.get("agent") if c.get("agent") in agent_mod.AGENTS else {"doc": "wiki", "data": "graph", "hybrid": "hybrid"}[typ]
        clean.append({"id": str(c.get("id") or f"CQ-{i + 1:02d}")[:20], "question": str(c["question"]).strip()[:1000], "type": typ, "agent": ag,
                      "reference_answer": str(c.get("reference_answer") or "")[:2000],
                      "key_facts": [str(x).strip()[:200] for x in (c.get("key_facts") or []) if str(x).strip()][:6],
                      "business_need": str(c.get("business_need") or "")[:500], "needs": [str(x)[:200] for x in (c.get("needs") or [])][:6],
                      "reasoning": str(c.get("reasoning") or "")[:1000], "origin": str(c.get("origin") or "edited")[:20]})
    log = McpLog("edit", None)
    put_json(log, ws["env"]["bucket"], prefix(ws["ws_id"]) + "cqs.json", clean)
    ws.setdefault("summary", {})["cqs"] = len(clean)
    save(ws, log)
    return {"status": "SUCCESS", "cqs": clean}


def save_wiki(ws: Dict[str, Any], pages: List[Dict[str, Any]]) -> Dict[str, Any]:
    from src.aos.pipeline import _kh_common, write_wiki
    log = McpLog("edit", None)
    b, pf = ws["env"]["bucket"], prefix(ws["ws_id"])
    docs = get_json(log, b, pf + "parsed/docs.json", []) or []
    tables = get_json(log, b, pf + "parsed/tables.json", []) or []
    r = log.call("aos_core_compile_wiki", {**_kh_common(ws), "mode": "validate", "pages": pages[:200],
                                              "docs": [{"doc_id": d["doc_id"], "title": d["title"], "text": d["text"]} for d in docs],
                                              "tables": [{"name": x["name"], "columns": x["columns"]} for x in tables]}, timeout_s=120)
    if r.get("status") != "SUCCESS":
        return {"status": "ERROR", "error": error_text(r)}
    write_wiki(ws, log, r)
    ws.setdefault("summary", {})["wiki"] = {"pages": len(r.get("pages") or []), "counts": r.get("counts"),
                                            "gates_passed": r.get("gates_passed"), "gates_total": r.get("gates_total"), "edited": now_iso()}
    if ws.get("stages", {}).get("graph", {}).get("status") == "done":
        ws["stages"]["graph"]["stale"] = True
    save(ws, log)
    from src.aos.ws import append_calls
    append_calls(ws, log)
    return {"status": "SUCCESS", "pages": r.get("pages"), "gates": r.get("gates"), "gates_passed": r.get("gates_passed"),
            "gates_total": r.get("gates_total"), "notes": r.get("notes") or []}


def run_query(ws: Dict[str, Any], sql: str) -> Dict[str, Any]:
    env = ws["env"]
    err = agent_mod.guard_query(sql, env["project"], env["dataset"])
    if err:
        return {"status": "BAD_QUERY", "error": err}
    log = McpLog("query", None)
    t0 = time.perf_counter()
    r = log.call("bigquery_execute_sql", {"project": env["project"], "sql": sql.strip().rstrip(";"), "location": env["region"], "timeout_ms": 45000,
                                          "labels": {"datacloud": "jetski", "app": "aos-starter"}}, timeout_s=70)
    ms = round((time.perf_counter() - t0) * 1000)
    if r.get("status") != "SUCCESS":
        return {"status": "ERROR", "error": error_text(r), "ms": ms}
    rows = r.get("rows") or []
    return {"status": "SUCCESS", "rows": rows[:500], "row_count": len(rows), "ms": ms, "bytes": r.get("bytes_processed", 0),
            "call": {"tool": "bigquery_execute_sql", "args": {"project": env["project"], "location": env["region"], "sql": sql.strip()}}}


def search(ws: Dict[str, Any], q: str, scopes: List[str]) -> Dict[str, Any]:
    q = str(q or "").strip()[:200]
    if len(q) < 1:
        return {"status": "BAD_REQUEST", "error": "empty query"}
    b, pf, env = ws["env"]["bucket"], prefix(ws["ws_id"]), ws["env"]
    terms = [x.lower() for x in re.split(r"\s+", q) if x]
    out: Dict[str, Any] = {"status": "SUCCESS", "q": q, "wiki": [], "docs": [], "tables": []}
    t0 = time.perf_counter()

    def score(text: str) -> int:
        low = text.lower()
        return sum(low.count(x) for x in terms)
    if "wiki" in scopes:
        for p in get_json(None, b, pf + "wiki/pages.json", []) or []:
            blob = " ".join(str(p.get(k) or "") for k in ("id", "title", "summary", "body_md")) + " " + json.dumps(p.get("policy") or [], ensure_ascii=False)
            s = score(blob) + 3 * score(str(p.get("title") or ""))
            if s:
                out["wiki"].append({"id": p.get("id"), "title": p.get("title"), "layer": p.get("layer"), "score": s, "snippet": _snippet(blob, terms)})
        out["wiki"].sort(key=lambda x: -x["score"])
    if "docs" in scopes:
        for d in get_json(None, b, pf + "parsed/docs.json", []) or []:
            for sec in re.split(r"\n(?=#{1,6}\s)", d.get("text", "")):
                s = score(sec)
                if s:
                    head = sec.strip().splitlines()[0][:120] if sec.strip() else ""
                    out["docs"].append({"doc_id": d.get("doc_id"), "section": head.lstrip("# "), "score": s, "snippet": _snippet(sec, terms)})
        out["docs"].sort(key=lambda x: -x["score"])
        out["docs"] = out["docs"][:20]
    if "tables" in scopes:
        tables = get_json(None, b, pf + "parsed/tables.json", []) or []
        lit = "'" + q.replace("\\", "\\\\").replace("'", "\\'") + "'"
        log = McpLog("search", None)
        for tb in tables[:10]:
            sql = f"SELECT * FROM `{tb['fq']}` AS t WHERE CONTAINS_SUBSTR(t, {lit}) LIMIT 5"
            r = log.call("bigquery_execute_sql", {"project": env["project"], "sql": sql, "location": env["region"], "labels": {"datacloud": "jetski"}}, timeout_s=60)
            rows = r.get("rows") or [] if r.get("status") == "SUCCESS" else []
            if rows:
                out["tables"].append({"table": tb["name"], "fq": tb["fq"], "rows": rows, "sql": sql})
    out["ms"] = round((time.perf_counter() - t0) * 1000)
    return out


def _snippet(text: str, terms: List[str], width: int = 160) -> str:
    low = text.lower()
    pos = min([low.find(x) for x in terms if low.find(x) >= 0] or [0])
    s = max(0, pos - width // 3)
    return ("…" if s else "") + re.sub(r"\s+", " ", text[s:s + width]).strip() + "…"


# ------------------------------------------------------------------------------------------------ export bundle
STANDALONE = r'''#!/usr/bin/env python3
"""Ask a built Agentic Ontology workspace using ONLY the Platform Core MCP (no starter repo needed).

    export AOS_ACCESS_TOKEN=$(gcloud auth print-access-token)        # or --impersonate-service-account=SA
    python3 aos_agent_standalone.py "your question" [wiki|graph|hybrid]

Method know-how (agent reasoning) = Core MCP `aos_core_agent_step`; data = Core MCP data-plane tools with YOUR token.
"""
import json, os, sys, urllib.request

CORE_MCP_URL = "__CORE__"
WS = __WS__


def mcp(tool, args, timeout=300):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": tool, "arguments": args}}).encode()
    req = urllib.request.Request(CORE_MCP_URL, data=body, method="POST", headers={
        "Content-Type": "application/json", "X-AOS-Access-Token": os.environ["AOS_ACCESS_TOKEN"]})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        res = json.loads(r.read().decode())["result"]
    return res.get("structuredContent") or json.loads(res["content"][0]["text"])


def read_json(name):
    r = mcp("storage_read_object", {"bucket": WS["bucket"], "name": WS["prefix"] + name})
    return json.loads(r.get("text") or "null") if r.get("status") == "SUCCESS" else None


def main():
    question = sys.argv[1] if len(sys.argv) > 1 else input("question> ")
    agent = sys.argv[2] if len(sys.argv) > 2 else "hybrid"
    pages = read_json("wiki/pages.json") or []
    plan = read_json("graph/plan.json") or {}
    by_id = {p["id"]: p for p in pages}
    ctx = {"wiki_index": [{"id": p["id"], "layer": p["layer"], "title": p["title"], "summary": p.get("summary", ""),
                           "policy_text": "; ".join(f"{c['name']}={c['value']}{c.get('unit', '')}" for c in p.get("policy") or [])} for p in pages],
           "graph": plan.get("schema"), "graph_ready": bool(plan.get("graph_ready")), "project": WS["project"], "dataset": WS["dataset"]}
    obs = []
    for step in range(6):
        r = mcp("aos_core_agent_step", {"agent": agent, "question": question, "lang": WS["lang"], "context": ctx, "observations": obs,
                                           "project": WS["project"], "model": WS["model"], "location": WS["vertex_location"]})
        if r.get("status") != "SUCCESS":
            sys.exit(f"agent_step failed: {r}")
        obs += r.get("calcs") or []
        act = r["action"]
        print(f"[{step + 1}] {act}: {r.get('thought', '')}")
        if act == "answer":
            print("\n" + r.get("answer", "") + "\n\ncitations:", ", ".join(r.get("citations") or []))
            return
        if act == "read_wiki":
            got = [{"id": i, "title": by_id[i]["title"], "text": by_id[i].get("summary", "") + "\n" + by_id[i].get("body_md", "")
                    + "\npolicy: " + json.dumps(by_id[i].get("policy") or [], ensure_ascii=False)} for i in r.get("page_ids") or [] if i in by_id]
            obs.append({"action": "read_wiki", "input": r.get("page_ids"), "result": got})
        elif r.get("query_error"):
            obs.append({"action": act, "input": r.get("query"), "error": r["query_error"]})
        else:
            q = mcp("bigquery_execute_sql", {"project": WS["project"], "sql": r["query"], "location": WS["region"]})
            print("    ", r["query"].replace("\n", " ")[:160])
            obs.append({"action": act, "input": r["query"], "result": {"rows": (q.get("rows") or [])[:30]}} if q.get("status") == "SUCCESS"
                       else {"action": act, "input": r["query"], "error": str(q.get("error"))[:800]})
    print("no answer within 6 steps")


if __name__ == "__main__":
    main()
'''


def export_bundle(ws: Dict[str, Any], lang: str) -> bytes:
    env = ws["env"]
    core = runtime_settings()["core_mcp_url"]
    pf = prefix(ws["ws_id"])
    calls = read_calls(env["bucket"], ws["ws_id"])
    ws_pub = {k: v for k, v in ws.items()}
    sa_hint = (ws.get("identity") or {}).get("principal", "") if (ws.get("identity") or {}).get("mode") == "impersonate" else ""
    imp = f" --impersonate {sa_hint}" if sa_hint else ""
    dotenv = "\n".join([f"GCP_PROJECT_ID={env['project']}", f"BQ_LOCATION={env['region']}", f"BQ_DATASET_ID={env['dataset']}",
                        f"GCS_WIKI_BUCKET={env['bucket']}", f"VERTEX_GEMINI_MODEL={env['model']}", f"VERTEX_LOCATION={env['vertex_location']}",
                        f"CORE_MCP_URL={core}", f"STARTER_WRITE_PROJECTS={env['project']}", ""])
    run_build = "\n".join(["#!/usr/bin/env bash", "set -euo pipefail",
                           f"# {t(lang, '깃헙 저장소 루트에서 실행', 'run from the GitHub repository root')}: git clone {GITHUB_URL}",
                           "set -a && source .env && set +a",
                           t(lang, "# 같은 워크스페이스를 다시 구축 (단계 지정: --stages ingest,cqs,wiki,graph,eval)",
                             "# rebuild the same workspace (pick stages with --stages ingest,cqs,wiki,graph,eval)"),
                           f"python3 -m src.cli build --bucket {env['bucket']} --ws {ws['ws_id']}{imp}",
                           t(lang, "# 새 워크스페이스로 복제해 처음부터 구축", "# or clone into a new workspace and build from scratch"),
                           f"# python3 -m src.cli new --from workspace.json{imp} && python3 -m src.cli build --bucket {env['bucket']} --ws <new ws id>{imp}", ""])
    ask = "\n".join(["#!/usr/bin/env bash", "set -euo pipefail", "set -a && source .env && set +a",
                     f'python3 -m src.cli ask --bucket {env["bucket"]} --ws {ws["ws_id"]} --agent "${{2:-hybrid}}"{imp} "$1"',
                     f'python3 -m src.cli eval --bucket {env["bucket"]} --ws {ws["ws_id"]}{imp}  # {t(lang, "전체 CQ 평가", "evaluate all CQs")}', ""])
    mcp_cfg = {"mcpServers": {"aos-core": {"httpUrl": core, "headers": {"X-AOS-Access-Token": "$AOS_ACCESS_TOKEN"}, "timeout": 600000,
                                           "description": "Agentic Ontology Platform Core MCP — data-plane tools with your token + aos_core_* method tools"}}}
    standalone = STANDALONE.replace("__CORE__", core).replace("__WS__", json.dumps(
        {"bucket": env["bucket"], "prefix": pf, "project": env["project"], "dataset": env["dataset"], "region": env["region"],
         "model": env["model"], "vertex_location": env["vertex_location"], "lang": ws.get("lang", "ko")}, ensure_ascii=False))
    tools = sorted({c["tool"] for c in calls})
    readme = README_KO if lang != "en" else README_EN
    readme = readme.format(ws=ws["ws_id"], title=ws["scenario"].get("title") or ws["ws_id"], project=env["project"], dataset=env["dataset"],
                           bucket=env["bucket"], pf=pf, graph=env["graph_name"], core=core, github=GITHUB_URL, ncalls=len(calls),
                           tools=", ".join(tools), version=APP_VERSION, at=now_iso(), imp=imp)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        root = f"{ws['ws_id']}/"
        z.writestr(root + "README.md", readme)
        z.writestr(root + "workspace.json", json.dumps(ws_pub, ensure_ascii=False, indent=1))
        z.writestr(root + ".env", dotenv)
        z.writestr(root + "setup_gcp.sh", setup_script(env, lang))
        z.writestr(root + "run_build.sh", run_build)
        z.writestr(root + "ask.sh", ask)
        z.writestr(root + "mcp_calls.jsonl", "\n".join(json.dumps(c, ensure_ascii=False) for c in calls) + "\n")
        z.writestr(root + "mcp_config.gemini-cli.json", json.dumps(mcp_cfg, indent=2))
        z.writestr(root + "aos_agent_standalone.py", standalone)
    return buf.getvalue()


README_KO = """# {title} — Agentic Ontology 워크스페이스 `{ws}`

스타터 {version}에서 {at}에 내보낸 번들입니다. 이 워크스페이스의 결과물은 **내 GCP**에 있습니다.

| 결과물 | 위치 |
| :--- | :--- |
| 워크스페이스 · 위키 · CQ · 그래프 설계 · 평가 | `gs://{bucket}/{pf}` |
| 원천 · 노드 · 엣지 테이블 | BigQuery `{project}.{dataset}` |
| Property Graph | `{project}.{dataset}.{graph}` |

## 파일
| 파일 | 용도 |
| :--- | :--- |
| `workspace.json` | 상황 · 목적 · 리소스 · 소스 · 단계 상태 (비밀값 없음) |
| `setup_gcp.sh` | API · 버킷 · 전용 SA · 역할 · Graph 예약을 그대로 만드는 스크립트 |
| `.env` | 깃헙 스타터를 이 리소스로 실행하는 환경 변수 |
| `run_build.sh` / `ask.sh` | 깃헙 스타터 CLI로 같은 결과를 재구축 · 질문 · 평가 |
| `mcp_calls.jsonl` | 스튜디오가 실행한 MCP 호출 {ncalls}건 (도구 · 인자 · 상태 · ms) — 다른 언어 · 오케스트레이터에서도 같은 파라미터로 재현 |
| `mcp_config.gemini-cli.json` | Gemini CLI 등 MCP 클라이언트에서 Core MCP를 도구로 붙이는 예시 (`AOS_ACCESS_TOKEN` 환경 변수) |
| `aos_agent_standalone.py` | 저장소 없이 Core MCP만으로 이 워크스페이스에 질문하는 단일 파일 에이전트 |

## 바로 실행
```bash
git clone {github} && cd agentic-ontology-starter
cp /path/to/{ws}/.env .env
bash /path/to/{ws}/ask.sh "질문" hybrid
# 저장소 없이:
export AOS_ACCESS_TOKEN=$(gcloud auth print-access-token)
python3 aos_agent_standalone.py "질문" hybrid
```

## 노하우 경계
- 방법론의 핵심(위키 컴파일 · 그래프 설계 · 에이전트 추론 · 채점)은 Platform Core MCP `{core}`의 `aos_core_*` 도구가 수행합니다. 이 번들과 깃헙 코드는 그 도구를 **어떤 순서로 · 어떤 파라미터로** 부르는지만 담습니다.
- 모든 데이터 접근과 Gemini 호출은 **내 토큰 · 내 프로젝트**로 실행됩니다. Core MCP 서비스 계정에는 데이터 권한이 없습니다.
- 이번 워크스페이스에서 쓴 도구: {tools}
"""

README_EN = """# {title} — Agentic Ontology workspace `{ws}`

Exported from starter {version} at {at}. The results of this workspace live in **your GCP**.

| Result | Location |
| :--- | :--- |
| workspace · wiki · CQs · graph design · evaluation | `gs://{bucket}/{pf}` |
| source · node · edge tables | BigQuery `{project}.{dataset}` |
| Property Graph | `{project}.{dataset}.{graph}` |

## Files
| File | Purpose |
| :--- | :--- |
| `workspace.json` | scenario · objective · resources · sources · stage status (no secrets) |
| `setup_gcp.sh` | creates APIs · bucket · dedicated SA · roles · graph reservation exactly as needed |
| `.env` | environment for running the GitHub starter against these resources |
| `run_build.sh` / `ask.sh` | rebuild · ask · evaluate with the GitHub starter CLI |
| `mcp_calls.jsonl` | the {ncalls} MCP calls the studio made (tool · arguments · status · ms) — replay them with the same parameters from any language or orchestrator |
| `mcp_config.gemini-cli.json` | example for attaching the Core MCP as tools in Gemini CLI or another MCP client (`AOS_ACCESS_TOKEN` env var) |
| `aos_agent_standalone.py` | single-file agent that asks this workspace through the Core MCP only (no repo needed) |

## Run
```bash
git clone {github} && cd agentic-ontology-starter
cp /path/to/{ws}/.env .env
bash /path/to/{ws}/ask.sh "question" hybrid
# without the repo:
export AOS_ACCESS_TOKEN=$(gcloud auth print-access-token)
python3 aos_agent_standalone.py "question" hybrid
```

## Know-how boundary
- The core of the method (wiki compile · graph design · agent reasoning · grading) runs in the `aos_core_*` tools of the Platform Core MCP `{core}`. This bundle and the GitHub code only hold **which tools are called in which order with which parameters**.
- Every data access and Gemini call runs with **your token in your project**. The Core MCP service account has no data permissions.
- Tools used by this workspace: {tools}
"""


def open_ws(bucket: str, ws_id: str) -> Dict[str, Any]:
    from src.aos.ws import load
    return load(bucket, ws_id)


def ws_from_request(data: Dict[str, Any]) -> Dict[str, Any]:
    ref = data.get("ws") or {}
    bucket = str(ref.get("bucket") or (data.get("env") or {}).get("bucket") or "").strip()
    ws_id = str(ref.get("ws_id") or data.get("ws_id") or "").strip()
    if not bucket or not ws_id:
        raise WsError("BAD_REQUEST", "워크스페이스(bucket · ws_id)가 필요합니다", "workspace (bucket · ws_id) is required")
    parse_gs(f"gs://{bucket}/")
    return open_ws(bucket, ws_id)
