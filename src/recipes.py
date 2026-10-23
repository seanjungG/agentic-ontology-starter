# Copyright (c) 2026 Sean Jung (seanjung@google.com). All Rights Reserved.
# Non-Commercial Use Only: Methodology & Docs under CC BY-NC-ND 4.0; Source Code under PolyForm Noncommercial License 1.0.0.
# Commercial use, paid consulting/SI/PoC delivery, or production deployment requires prior written permission from seanjung@google.com.

# -*- coding: utf-8 -*-
"""Step-1 choices (data type × purpose) → recipe (Flow A / B / C), agents, resources and the plan of steps 3–6."""
from typing import Any, Dict, List, Optional

from src import datapack


def T(ko: str, en: str) -> Dict[str, str]:
    return {"ko": ko, "en": en}


def localize(obj: Any, lang: str) -> Any:
    """Replaces every {"ko": .., "en": ..} leaf with the string of `lang`."""
    lang = "en" if lang == "en" else "ko"
    if isinstance(obj, dict):
        if set(obj.keys()) == {"ko", "en"}:
            return obj[lang]
        return {k: localize(v, lang) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [localize(v, lang) for v in obj]
    return obj


TYPES = [
    {"id": "P1", "t": T("문서만", "Documents only"), "s": T("정책 · 규정 문서로 시작합니다", "Start from policy documents"),
     "meta": T("가이드 2종 · 조항 5개", "2 guides · 5 clauses")},
    {"id": "P2", "t": T("테이블만", "Tables only"), "s": T("BigQuery 원장 테이블로 시작합니다", "Start from BigQuery ledger tables"),
     "meta": T("원천 테이블 6종", "6 source tables")},
    {"id": "P3", "t": T("문서 + 테이블", "Documents + tables"), "s": T("둘을 하나의 그래프로 묶습니다", "Bind both into one graph"),
     "meta": T("문서 2 · 테이블 6 · 위키 4", "2 docs · 6 tables · 4 wiki pages")},
]
PURPOSES = [
    {"id": "W1", "t": T("규정 안내", "Policy guidance"), "s": T("규정 · 기간 · 면제 조건을 근거와 함께 안내", "Explain rules, periods and exemptions with sources"),
     "q": T("공시지원금을 받으면 며칠 동안 기준 요금제를 유지해야 하나요?", "How long must I keep the baseline plan after a public subsidy?")},
    {"id": "W2", "t": T("원장 조회", "Ledger lookup"), "s": T("단말 · 요금제 · 고객 계약 값을 정확히 조회", "Look up device, plan and contract values exactly"),
     "q": T("Galaxy S26 Ultra 256GB의 출고가는?", "What is the factory price of the Galaxy S26 Ultra 256GB?")},
    {"id": "W3", "t": T("판정 · 계산", "Decide & calculate"), "s": T("규정과 원장을 함께 써서 위약금 · 면제 · 총비용 판정", "Combine rules and ledgers to decide penalties, exemptions and costs"),
     "q": T("CUST_DEMO_001 고객이 120일째에 5G Light로 낮추면 위약금은?", "What is the penalty if CUST_DEMO_001 moves to 5G Light at day 120?")},
]

AGENTS = {
    "wiki": {"id": "wiki", "name": "Wiki Agent", "layer": "agent", "point": "W1",
             "s": T("GCS의 위키 페이지만 읽고 근거 페이지를 인용해 답합니다", "Reads only the wiki pages in GCS and cites its source pages")},
    "graph": {"id": "graph", "name": "Graph Agent", "layer": "agent", "point": "W2",
              "s": T("BigQuery 그래프 · SQL과 도메인 MCP 도구로 숫자까지 조회합니다", "Queries the BigQuery graph · SQL and domain MCP tools down to the number")},
    "workflow": {"id": "workflow", "name": "Workflow Agent", "layer": "agent", "point": "W3",
                 "s": T("W1–W3 단계를 따라 MCP 도구로 판정 · 계산합니다 (G2-W 확인 포함)", "Follows the W1–W3 steps and decides with MCP tools (incl. the G2-W check)")},
}

RECIPES = {
    "A": {"key": "A", "paths": ["P1"], "points": ["W1"], "gate": False, "agents": ["wiki"],
          "t": T("Flow A · 문서 중심", "Flow A · document-first"), "s": T("P1 + W1", "P1 + W1"),
          "d": T("문서를 OKF 위키로 바꿔 GCS에 올리고, Wiki Agent가 위키만 읽고 규정 질문에 답합니다. 테이블과 그래프는 쓰지 않습니다.",
                 "Documents become an OKF wiki in GCS, and the Wiki Agent answers policy questions from the wiki alone. No tables or graph.")},
    "B": {"key": "B", "paths": ["P2"], "points": ["W2"], "gate": False, "agents": ["graph"],
          "t": T("Flow B · 테이블 중심", "Flow B · table-first"), "s": T("P2 + W2", "P2 + W2"),
          "d": T("원장 테이블을 BigQuery에 적재하고 테이블 서브그래프를 만든 뒤, Graph Agent가 SQL · GQL과 MCP 도구로 값을 조회합니다.",
                 "Ledger tables are loaded into BigQuery with a table subgraph, and the Graph Agent looks values up with SQL · GQL and MCP tools.")},
    "C": {"key": "C", "paths": ["P1", "P2", "P3"], "points": ["W1", "W2", "W3"], "gate": True, "agents": ["wiki", "graph", "workflow"],
          "t": T("Flow C · 통합", "Flow C · unified"), "s": T("P1 + P2 + P3 × W1 + W2 + W3 + G2-W", "P1 + P2 + P3 × W1 + W2 + W3 + G2-W"),
          "d": T("위키와 테이블을 하나의 BigQuery Property Graph로 묶고, 세 에이전트가 같은 데이터를 씁니다. Workflow Agent는 위키 정책값과 원장 값이 같은지(G2-W) 확인한 뒤 판정 · 계산합니다.",
                 "The wiki and the tables are bound into one BigQuery Property Graph used by all three agents. The Workflow Agent checks that wiki policy values match the ledgers (G2-W) before deciding.")},
}

_REASON = {
    ("P1", "W2"): T("원장 조회에는 테이블(P2)이 필요해 문서 + 테이블 통합 구성으로 맞췄습니다.",
                    "Ledger lookups need tables (P2), so the recipe was widened to documents + tables."),
    ("P1", "W3"): T("판정 · 계산에는 규정 문서와 원장 테이블이 함께 필요해 통합 구성으로 맞췄습니다.",
                    "Decisions and calculations need both policy documents and ledger tables, so the unified recipe is used."),
    ("P2", "W1"): T("규정 안내에는 문서(P1)가 필요해 문서 + 테이블 통합 구성으로 맞췄습니다.",
                    "Policy guidance needs documents (P1), so the recipe was widened to documents + tables."),
    ("P2", "W3"): T("판정 · 계산에는 규정 문서와 원장 테이블이 함께 필요해 통합 구성으로 맞췄습니다.",
                    "Decisions and calculations need both policy documents and ledger tables, so the unified recipe is used."),
    ("P3", "W1"): T("문서 + 테이블이면 세 경로를 모두 쓰는 통합 구성입니다. 규정 안내는 그중 Wiki Agent가 맡습니다.",
                    "Documents + tables always use all three paths. Policy guidance is handled by the Wiki Agent."),
    ("P3", "W2"): T("문서 + 테이블이면 세 경로를 모두 쓰는 통합 구성입니다. 원장 조회는 그중 Graph Agent가 맡습니다.",
                    "Documents + tables always use all three paths. Ledger lookups are handled by the Graph Agent."),
}


def resolve(type_id: Optional[str], purpose_id: Optional[str]) -> Optional[Dict[str, Any]]:
    if type_id not in ("P1", "P2", "P3") or purpose_id not in ("W1", "W2", "W3"):
        return None
    if (type_id, purpose_id) == ("P1", "W1"):
        return {"recipe": "A", "exact": True, "reason": None}
    if (type_id, purpose_id) == ("P2", "W2"):
        return {"recipe": "B", "exact": True, "reason": None}
    if (type_id, purpose_id) == ("P3", "W3"):
        return {"recipe": "C", "exact": True, "reason": None}
    return {"recipe": "C", "exact": False, "reason": _REASON[(type_id, purpose_id)]}


def matrix() -> Dict[str, Dict[str, Any]]:
    return {f"{t['id']}-{p['id']}": resolve(t["id"], p["id"]) for t in TYPES for p in PURPOSES}


def load_plan(recipe: str) -> List[Dict[str, Any]]:
    """Ordered load steps for step 4 (keys are also used by the UI to light up the resources diagram)."""
    pages = len(datapack.WIKI_BY_RECIPE.get(recipe, ()))
    p2 = [t for t in datapack.tables_for("B")]
    p3 = [t for t in datapack.tables_for("C") if t not in p2]
    steps = []
    if "P1" in RECIPES[recipe]["paths"]:
        steps += [
            {"key": "gate0", "node": "gcs", "service": "Core MCP", "core_mcp": "aos_builder_parse_documents_gate0",
             "t": T("문서 파싱 · Gate 0 (원문 보존율)", "Parse documents · Gate 0 (fidelity)"),
             "target": T("문서 2종 → Core MCP", "2 documents → Core MCP")},
            {"key": "docs", "node": "gcs", "service": "Cloud Storage", "core_mcp": "storage_upload_object",
             "t": T("원본 문서 업로드", "Upload source documents"), "target": "gs://{bucket}/starter/{lang}/docs/"},
            {"key": "wiki", "node": "gcs", "service": "Cloud Storage", "core_mcp": "aos_builder_compile_okf_wiki_stage2 + storage_upload_object",
             "t": T(f"OKF 위키 페이지 {pages}개 업로드", f"Upload {pages} OKF wiki pages"), "target": "gs://{bucket}/starter/{lang}/wiki/"},
        ]
    if "P2" in RECIPES[recipe]["paths"]:
        steps += [
            {"key": "dataset", "node": "bq", "service": "BigQuery", "core_mcp": "bigquery_get_dataset_info + bigquery_create_dataset",
             "t": T("데이터셋 확인 · 없으면 생성", "Check the dataset · create if missing"), "target": "{project}.{dataset}"},
            {"key": "tables_p2", "node": "bq", "service": "BigQuery", "core_mcp": "bigquery_load_table (Stage 1)",
             "t": T(f"원장 테이블 {len(p2)}개 적재 (WRITE_TRUNCATE)", f"Load {len(p2)} ledger tables (WRITE_TRUNCATE)"),
             "target": "{project}.{dataset}", "tables": p2},
        ]
    if "P3" in RECIPES[recipe]["paths"]:
        steps.append({"key": "tables_p3", "node": "bq", "service": "BigQuery", "core_mcp": "bigquery_load_table (Stage 3)",
                      "t": T(f"위키 · 규칙 테이블 {len(p3)}개 적재", f"Load {len(p3)} wiki / rule tables"),
                      "target": "{project}.{dataset}", "tables": p3})
    if "P2" in RECIPES[recipe]["paths"]:
        steps += [
            {"key": "graph", "node": "graph", "service": "BigQuery Graph", "core_mcp": "aos_builder_synthesize_bqg_stage4 + bigquery_execute_sql",
             "t": T("Property Graph 생성 (CREATE OR REPLACE)", "Create the property graph (CREATE OR REPLACE)"),
             "target": "{project}.{dataset}.{graph}"},
            {"key": "graph_check", "node": "graph", "service": "BigQuery Graph", "core_mcp": "bigquery_execute_sql (GQL)",
             "t": T("그래프 경로 확인 (GQL)", "Check graph paths (GQL)"), "target": "{project}.{dataset}.{graph}"},
        ]
    if "P1" in RECIPES[recipe]["paths"]:
        steps.append({"key": "manifest", "node": "gcs", "service": "Cloud Storage", "core_mcp": "storage_upload_object",
                      "t": T("적재 기록 저장 (manifest.json)", "Save the load manifest (manifest.json)"),
                      "target": "gs://{bucket}/starter/{lang}/manifest.json"})
    return steps


def step_plan(recipe: str) -> List[Dict[str, Any]]:
    """What steps 3–6 will do for the recipe (shown on step 2)."""
    r = RECIPES[recipe]
    n_cq = len(datapack.cqs("ko", recipe))
    items = [{"step": 3, "t": T("GCP 리소스 확인", "Verify GCP resources"), "service": "IAM · Vertex AI · Core MCP",
              "what": T("입력한 프로젝트 · 버킷 · 데이터셋의 존재와 권한, Gemini · Core MCP 연결을 실제로 확인합니다.",
                        "Checks that the project, bucket and dataset exist and are writable, and that Gemini and the Core MCP respond.")}]
    for s in load_plan(recipe):
        items.append({"step": 4, "t": s["t"], "service": s["service"], "what": s["target"], "core_mcp": s["core_mcp"]})
    for a in r["agents"]:
        items.append({"step": 5, "t": T(f"{AGENTS[a]['name']} 실행", f"Run the {AGENTS[a]['name']}"), "service": "Vertex AI · Gemini",
                      "what": AGENTS[a]["s"]})
    items.append({"step": 6, "t": T(f"기준 CQ {n_cq}개로 평가", f"Evaluate with {n_cq} golden CQs"), "service": "Gemini · BigQuery",
                  "what": T("같은 질문으로 에이전트를 채점합니다 (숫자 · 핵심어 일치).", "Scores the agents on the same questions (numbers and key terms).")})
    return items


IAM = [
    {"step": 3, "role": "roles/aiplatform.user", "scope": T("프로젝트", "project"), "why": T("Gemini 연결 확인 · 에이전트 답변", "Gemini check and agent answers")},
    {"step": 3, "role": "roles/bigquery.metadataViewer", "scope": T("프로젝트 또는 데이터셋", "project or dataset"), "why": T("데이터셋 · 그래프 존재 확인", "Dataset and graph checks")},
    {"step": 3, "role": "roles/bigquery.resourceViewer", "scope": T("프로젝트 (선택)", "project (optional)"), "why": T("Enterprise 예약 할당 확인", "Enterprise reservation assignment check")},
    {"step": 4, "role": "roles/storage.objectAdmin", "scope": T("버킷", "bucket"), "why": T("문서 · 위키 업로드 (starter/<lang>/)", "Upload docs and wiki (starter/<lang>/)")},
    {"step": 4, "role": "roles/bigquery.dataEditor", "scope": T("프로젝트 (데이터셋 생성 시) 또는 데이터셋", "project (to create datasets) or dataset"), "why": T("데이터셋 · 테이블 · 그래프 생성과 적재", "Create and load datasets, tables and the graph")},
    {"step": 4, "role": "roles/bigquery.jobUser", "scope": T("프로젝트", "project"), "why": T("적재 · DDL · 쿼리 작업 실행", "Run load, DDL and query jobs")},
    {"step": 4, "role": "roles/spanner.databaseUser + databaseAdmin", "scope": T("Spanner DB (선택)", "Spanner database (optional)"), "why": T("Spanner 그래프 적재를 켤 때만", "Only when the Spanner graph load is enabled")},
    {"step": 5, "role": "roles/bigquery.dataViewer · roles/storage.objectViewer", "scope": T("데이터셋 · 버킷", "dataset · bucket"), "why": T("에이전트 조회 (적재 권한에 포함)", "Agent reads (included in the load roles)")},
]


def catalog(lang: str) -> Dict[str, Any]:
    recipes = {}
    for k, r in RECIPES.items():
        recipes[k] = {
            **r,
            "agents": [AGENTS[a] for a in r["agents"]],
            "wiki_pages": list(datapack.WIKI_BY_RECIPE[k]),
            "tables": datapack.tables_for(k),
            "cq_count": len(datapack.cqs(lang, k)),
            "load_plan": load_plan(k),
            "step_plan": step_plan(k),
        }
    return localize({"types": TYPES, "purposes": PURPOSES, "recipes": recipes, "matrix": matrix(), "agents": AGENTS,
                     "iam": IAM}, lang)
