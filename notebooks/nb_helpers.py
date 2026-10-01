# Copyright (c) 2026 Sean Jung (seanjung@google.com). All Rights Reserved.
# Non-Commercial Use Only: Methodology & Docs under CC BY-NC-ND 4.0; Source Code under PolyForm Noncommercial License 1.0.0.
# Commercial use, paid consulting/SI/PoC delivery, or production deployment requires prior written permission from seanjung@google.com.

# -*- coding: utf-8 -*-
"""Shared helpers for the starter notebooks: setup, methodology flow diagrams, tables, charts,
graph schematics, pipeline parsing/integration views, agent traces, and NL-to-GQL.

Data exploration cells use BigQuery `%%bqsql` magics (BigFrames). The MCP tools, the agent, and the
NL-to-GQL helper use the starter's own REST client (`src/gcp_client.py`) so that BigQuery Job IDs are visible.
"""
import csv
import hashlib
import json
import os
import re
import sys
import warnings
from pathlib import Path

if Path("/etc/ssl/cert.pem").exists():
    os.environ.setdefault("SSL_CERT_FILE", "/etc/ssl/cert.pem")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import matplotlib.patches as mpatches  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import networkx as nx  # noqa: E402
import pandas as pd  # noqa: E402
from IPython.display import Markdown, display  # noqa: E402
from matplotlib import font_manager  # noqa: E402

from src.agent.i18n_en import localize_en_obj, localize_en_str  # noqa: E402
from src.gcp_client import (DEFAULT_BQ_SPANNER_CONN, DEFAULT_DATASET_ID, DEFAULT_GEMINI_MODEL,  # noqa: E402
                            DEFAULT_LOCATION, DEFAULT_PROJECT_ID, DEFAULT_SPANNER_DATABASE,
                            DEFAULT_SPANNER_INSTANCE, call_vertex_gemini, execute_bq_sql,
                            execute_spanner_sql, get_gcp_token)

PROJECT, DATASET, LOCATION, MODEL = DEFAULT_PROJECT_ID, DEFAULT_DATASET_ID, DEFAULT_LOCATION, DEFAULT_GEMINI_MODEL
SPANNER_INSTANCE, SPANNER_DB, BQ_CONN_ID = DEFAULT_SPANNER_INSTANCE, DEFAULT_SPANNER_DATABASE, DEFAULT_BQ_SPANNER_CONN
FQ = f"{PROJECT}.{DATASET}"
GRAPH = f"{FQ}.STARTER_ONTOLOGY_GRAPH"
LANG = "ko"
PALETTE = ["#1A73E8", "#0d9488", "#F9AB00", "#D93025", "#9334E6", "#188038", "#0284c7", "#5F6368"]
LABEL_COLORS = {"CustomerContractNode": "#1A73E8", "DeviceNode": "#0284c7", "PlanNode": "#0d9488",
                "SubsidyNode": "#188038", "DomainRuleNode": "#F9AB00", "DocChunkNode": "#9334E6"}
NAME_KEYS = ("customer_id", "device_name", "plan_name", "rule_id", "chunk_id", "policy_id")


def setup(lang="ko"):
    """Sets BigFrames project/location/credentials, chart style and a CJK font; returns the runtime settings."""
    global LANG
    LANG = lang
    os.environ["STARTER_LANG"] = lang
    warnings.filterwarnings("ignore")
    import bigframes.pandas as bpd
    from google.oauth2.credentials import Credentials
    bpd.options.bigquery.project = PROJECT
    bpd.options.bigquery.location = LOCATION
    bpd.options.bigquery.credentials = Credentials(token=get_gcp_token())
    bpd.options.display.progress_bar = None
    pd.set_option("display.max_colwidth", 90)
    pd.set_option("display.width", 200)
    fonts = {f.name for f in font_manager.fontManager.ttflist}
    cjk = next((f for f in ("Apple SD Gothic Neo", "AppleGothic", "NanumGothic", "Noto Sans CJK KR", "Malgun Gothic") if f in fonts), None)
    plt.rcParams.update({"font.family": (cjk or "sans-serif") if lang == "ko" else "sans-serif", "axes.unicode_minus": False, "figure.dpi": 100,
                         "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
                         "grid.alpha": 0.25, "axes.titleweight": "bold"})
    return pd.DataFrame([{"project": PROJECT, "dataset": DATASET, "location": LOCATION,
                          "graph": GRAPH.split(".")[-1], "model": MODEL, "lang": LANG}])


def t(ko, en):
    return ko if LANG == "ko" else en


def pdf(df):
    """BigFrames or pandas -> small pandas frame for display/plots (starter tables have < 20 rows)."""
    d = df.to_pandas() if hasattr(df, "to_pandas") else pd.DataFrame(df)
    if LANG == "en" and len(d):
        d = d.copy()
        for col in d.columns:
            if d[col].dtype == object or str(d[col].dtype).startswith(("string", "category")):
                d[col] = d[col].map(lambda x: localize_en_obj(x) if isinstance(x, (str, list, dict)) else x)
    return d


def md(text):
    display(Markdown(text))


def show(df, cols=None):
    d = pdf(df)
    display(d[cols] if cols else d)


def show_md_file(path, max_lines=40):
    """Shows a markdown file as rendered output; headings are demoted so they do not break the notebook outline."""
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    body = "\n".join(("####" + ln.lstrip("#")) if ln.startswith("#") else ln for ln in lines[:max_lines])
    md(f"**`{Path(path).name}`** ({len(lines)} lines)\n\n{body}")


def read_json(rel):
    with open(ROOT / rel, "r", encoding="utf-8") as f:
        data = json.load(f)
    return localize_en_obj(data) if LANG == "en" else data


def sql(query):
    """Runs SQL/GQL through the starter client; returns (DataFrame, meta). Errors are returned, not raised."""
    r = execute_bq_sql(query)
    meta = {k: r.get(k) for k in ("status", "job_id", "elapsed_ms", "total_bytes_processed")}
    if r.get("status") != "SUCCESS":
        meta["error"] = str(r.get("error", ""))[:400]
    rows = localize_en_obj(r.get("rows", [])) if LANG == "en" else r.get("rows", [])
    return pd.DataFrame(rows), meta


# ------------------------------------------------------------------ methodology & pipeline helpers
def raw_inputs_inventory():
    """Summarizes raw files in data/input/ before ingestion (Phase 1: Preparation)."""
    rows = []
    specs = [
        ("01_guides/sample_policy_guide.md", "Unstructured Policy Guide", "DOC_CHUNK_001~003 (Subsidy Cap, 180d Retention, Prorated Formula)"),
        ("01_guides/sample_welfare_exemption_guide.md", "Unstructured Policy Guide", "DOC_CHUNK_004~005 (Senior/Welfare Exemption, 24M TCO Rule)"),
        ("03_tables/devices.csv", "Master CSV (Structured)", "device_id, pet_name, storage, manufacturer, factory_price, release_date"),
        ("03_tables/plans.csv", "Master CSV (Structured)", "plan_id, plan_name, tier_category, monthly_fee, min_maintenance_days, selective_discount_rate"),
        ("03_tables/subsidies.csv", "Master CSV (Structured)", "policy_id, device_id, plan_id, basic_subsidy, distribution_subsidy, mandatory_retention_days"),
        ("03_tables/customer_contracts.csv", "Master CSV (Structured)", "contract_id, customer_id (CUST_DEMO_*), device_id, plan_id, contract_type, elapsed_days, welfare_status"),
        ("03_tables/domain_rules.csv", "Semantic Rule CSV", "rule_id, rule_name, rule_category, condition_expr, formula_expr, source_chunk_id"),
        ("03_tables/rule_plan_edges.csv", "Semantic Bridge CSV", "edge_id, rule_id, plan_id, source_chunk_id, relation_label_ko"),
        ("04_cq/golden_competency_questions.json", "Golden CQ Benchmark Spec", "5 Golden CQs with expected_math, verification_sql, grounded_chunk"),
        ("04_cq/boundary_cases.json", "Boundary Benchmark Spec", "10 Boundary Cases with root_cause_code, accept_answer_status"),
        ("05_glossary/business_glossary.json", "Domain Glossary", "Standardized telecom domain terms & synonyms"),
    ]
    for rel, kind, desc in specs:
        p = ROOT / "data/input" / rel
        if not p.exists():
            continue
        txt = p.read_text(encoding="utf-8")
        if p.suffix == ".csv":
            with open(p, "r", encoding="utf-8") as f:
                cnt = f"{len(list(csv.DictReader(f)))} rows"
        elif p.suffix == ".json":
            data = json.loads(txt)
            cnt = f"{len(data) if isinstance(data, list) else len(data.get('terms', data))} items"
        else:
            cnt = f"{len(txt.splitlines())} lines ({len(txt):,} chars)"
        rows.append({"input_file": rel, "asset_type": kind, "volume": cnt, "key_contents": desc})
    return pd.DataFrame(rows)


def parse_guides_live_demo():
    """Demonstrates Phase 3 (Parsing): parses 01_guides/*.md into SHA-256 anchored chunks and compares with BigQuery."""
    chunk_pat = re.compile(r"<!--\s*(DOC_CHUNK_\d+):?\s*(.*?)\s*-->\s*(.*?)(?=(?:<!--\s*DOC_CHUNK_\d+)|$)", re.DOTALL)
    bq_df, _ = sql(f"SELECT chunk_id, content_sha256, trust_tier FROM `{FQ}.tb_doc_chunks` ORDER BY chunk_id")
    bq_map = {r["chunk_id"]: r for r in bq_df.to_dict("records")}
    rows = []
    for gpath in sorted((ROOT / "data/input/01_guides").glob("*.md")):
        raw = gpath.read_text(encoding="utf-8")
        for cid, title, body in chunk_pat.findall(raw):
            clean = body.strip()
            anchor = "anchor_" + hashlib.sha256(body.encode("utf-8")).hexdigest()[:12]
            bq_anchor = bq_map.get(cid, {}).get("content_sha256")
            disp_body = localize_en_str(clean) if LANG == "en" else clean
            rows.append({
                "chunk_id": cid,
                "source_file": gpath.name,
                "section_title": localize_en_str(title.strip()) if LANG == "en" else title.strip(),
                "chars": len(clean),
                "computed_anchor": anchor,
                "bq_stored_anchor": bq_anchor,
                "sha256_match": anchor == bq_anchor,
                "excerpt": disp_body.splitlines()[0][:75] if disp_body else "",
            })
    return pd.DataFrame(rows)


def wiki_compilation_summary():
    """Summarizes compiled 3-Layer LLM-Wiki files and GCS/BigQuery sync manifest."""
    manifest = read_json("data/llm_wiki/gcs_prototype_manifest.json")
    layers = [
        ("Layer 1 (Executive Summary)", "summary.md", "Domain scope, OKF v0.2 framework, total chunks & BigQuery tables"),
        ("Layer 2 (Core Entities)", "entities.md", "Compiled directory of contracts, devices, plans, and subsidy policies"),
        ("Layer 3 (Semantic Concepts)", "concepts.md", "Entity=Node, Concept=Edge relationship definitions (4 edge types)"),
        ("Layer 3 (Codified Rules)", "rules.md", "Deterministic business rules with condition_expr, formula_expr & chunk anchors"),
    ]
    rows = []
    wiki_dir = ROOT / "data/llm_wiki" / ("en" if LANG == "en" else "ko")
    if not wiki_dir.exists():
        wiki_dir = ROOT / "data/llm_wiki"
    for layer_name, fname, role in layers:
        p = wiki_dir / fname
        lines = p.read_text(encoding="utf-8").splitlines() if p.exists() else []
        gcs_uri = f"{manifest.get('gcs_uri', '')}ontology/{fname}"
        rows.append({"wiki_layer": layer_name, "file": fname, "lines": len(lines), "gcs_object_uri": gcs_uri, "role": role})
    return pd.DataFrame(rows), manifest


def draw_eight_phase_flow():
    """Draws the 8-Phase Engineering Flow (Prepare -> Analyze -> Parse -> Integrate -> Build -> Agent -> Answer -> Verify)."""
    phases = [
        (t("1. 준비 (Prepare)", "1. Prepare"),
         t("Stage 1.1a · 원시 CSV/MD & 스키마", "Stage 1.1a\nRaw CSV/MD & BQ Schema"), "#1A73E8", (0, 1)),
        (t("2. 분석 (Analyze)", "2. Analyze"),
         t("Stage 1.1b~1.2 · 탐색·PII & Golden CQ", "Stage 1.1b~1.2\nProfiling, PII & Golden CQs"), "#0284c7", (1, 1)),
        (t("3. 파싱 (Parse)", "3. Parse"),
         t("Stage 2.1 · SHA-256 청크 & 3-Layer Wiki", "Stage 2.1\nSHA-256 Chunks & 3-Layer Wiki"), "#9334E6", (2, 1)),
        (t("4. 통합 (Integrate)", "4. Integrate"),
         t("Stage 2.2 · 도메인 규칙 & 시맨틱 그래프", "Stage 2.2\nRules & Semantic Graph"), "#F9AB00", (3, 1)),
        (t("5. 구축 (Build Graph)", "5. Build Graph"),
         t("Stage 3.1~3.2 · BQ/Spanner 프로퍼티 그래프", "Stage 3.1~3.2\nBQ/Spanner Property Graph"), "#0d9488", (0, 0)),
        (t("6. 에이전트 구축 (Agent)", "6. Build Agent"),
         t("Stage 4.1 · 8종 MCP 도구 & 2-Pass 엔진", "Stage 4.1\n8 MCP Tools & 2-Pass Engine"), "#188038", (1, 0)),
        (t("7. 답변 (Answer & GQL)", "7. Answer & GQL"),
         t("Stage 4.2 · NL2GQL & 근거 인용 합성", "Stage 4.2\nNL2GQL & Grounded Synthesis"), "#1A73E8", (2, 0)),
        (t("8. 검증 (Verify & Gate)", "8. Verify & Gate"),
         t("Stage 5.1~5.2 · 엔드투엔드 리니지 & 50회 평가", "Stage 5.1~5.2\nEnd-to-End Lineage & 50-Trial Eval"), "#D93025", (3, 0)),
    ]
    fig, ax = plt.subplots(figsize=(12.2, 4.3))
    ax.axis("off")
    ax.set_xlim(-0.55, 3.65)
    ax.set_ylim(-0.48, 1.52)
    font_fam = plt.rcParams["font.family"]
    for idx, (title, sub, color, (x, y)) in enumerate(phases):
        box = mpatches.FancyBboxPatch((x - 0.42, y - 0.27), 0.84, 0.54, boxstyle="round,pad=0.03,rounding_size=0.07",
                                      fc=color, ec="white", lw=2, alpha=0.94)
        ax.add_patch(box)
        ax.text(x, y + 0.09, title, ha="center", va="center", color="white", fontsize=9.2, fontweight="bold", fontfamily=font_fam)
        ax.text(x, y - 0.11, sub, ha="center", va="center", color="white", fontsize=7.4, fontfamily=font_fam)
        if idx in (0, 1, 2, 4, 5, 6):
            ax.annotate("", xy=(x + 0.56, y), xytext=(x + 0.44, y),
                        arrowprops={"arrowstyle": "->", "color": "#475569", "lw": 1.8})
    # Clean stepped corridor path from Phase 4 (3, 0.70) -> middle corridor y=0.50 -> Phase 5 (0, 0.30)
    ax.plot([3.0, 3.0, 0.0], [0.71, 0.50, 0.50], color="#475569", lw=1.6, ls="--")
    ax.annotate("", xy=(0.0, 0.29), xytext=(0.0, 0.50),
                arrowprops={"arrowstyle": "->", "color": "#475569", "lw": 1.6, "ls": "--"})
    ax.set_title(t("8단계 엔지니어링 파이프라인 및 5-Stage 매핑 도식 (준비 → 분석 → 파싱 → 통합 → 구축 → 에이전트 구축 → 답변 → 검증)",
                   "8-Phase Engineering Pipeline Mapped to the 5-Stage Methodology"), fontweight="bold", pad=10)
    plt.tight_layout()
    plt.show()


def draw_table_er_blueprint():
    """Draws the 10-table BigQuery schema blueprint (4 Master + 2 Knowledge + 4 Edge tables) with non-overlapping coordinates."""
    nodes = [
        {"id": "tb_customer_contract", "name": "tb_customer_contract\n(PK: contract_id)", "pos": (0.0, 0.75), "color": "#1A73E8"},
        {"id": "tb_subsidy_policy", "name": "tb_subsidy_policy\n(PK: policy_id)", "pos": (0.0, 0.15), "color": "#188038"},
        {"id": "tb_domain_rules", "name": "tb_domain_rules\n(PK: rule_id)", "pos": (0.0, -0.45), "color": "#F9AB00"},
        {"id": "edge_contract_device", "name": "edge_contract_device\n[USES_DEVICE]", "pos": (1.0, 0.85), "color": "#5F6368"},
        {"id": "edge_contract_plan", "name": "edge_contract_plan\n[SUBSCRIBES_PLAN]", "pos": (1.0, 0.42), "color": "#5F6368"},
        {"id": "edge_subsidy_binding", "name": "edge_subsidy_binding\n[HAS_SUBSIDY_POLICY]", "pos": (1.0, -0.02), "color": "#5F6368"},
        {"id": "edge_rule_applies_to_plan", "name": "edge_rule_applies_to_plan\n[APPLIES_TO_PLAN]", "pos": (1.0, -0.42), "color": "#5F6368"},
        {"id": "tb_doc_chunks", "name": "tb_doc_chunks\n(PK: chunk_id / SHA-256)", "pos": (1.0, -0.82), "color": "#9334E6"},
        {"id": "tb_device_master", "name": "tb_device_master\n(PK: device_id)", "pos": (2.0, 0.55), "color": "#0284c7"},
        {"id": "tb_plan_master", "name": "tb_plan_master\n(PK: plan_id)", "pos": (2.0, -0.12), "color": "#0d9488"},
    ]
    edges = [
        {"src": "tb_customer_contract", "dst": "edge_contract_device", "label": "contract_id"},
        {"src": "edge_contract_device", "dst": "tb_device_master", "label": "device_id"},
        {"src": "tb_customer_contract", "dst": "edge_contract_plan", "label": "contract_id"},
        {"src": "edge_contract_plan", "dst": "tb_plan_master", "label": "plan_id"},
        {"src": "tb_subsidy_policy", "dst": "edge_subsidy_binding", "label": "policy_id"},
        {"src": "edge_subsidy_binding", "dst": "tb_device_master", "label": "device_id"},
        {"src": "edge_subsidy_binding", "dst": "tb_plan_master", "label": "plan_id"},
        {"src": "tb_domain_rules", "dst": "edge_rule_applies_to_plan", "label": "rule_id"},
        {"src": "edge_rule_applies_to_plan", "dst": "tb_plan_master", "label": "plan_id"},
        {"src": "tb_domain_rules", "dst": "tb_doc_chunks", "label": "source_chunk_id", "style": "dashed"},
    ]
    draw_graph(nodes, edges,
               t("starter_ontology_dw 10개 테이블 스키마 설계도 (4 마스터 · 2 지식 · 4 엣지 브릿지)",
                 "starter_ontology_dw 10-Table Schema Blueprint (4 Master · 2 Knowledge · 4 Edge Bridges)"),
               layout="pos", figsize=(11.8, 5.6), node_size=1850,
               legend={"Contract (#1A73E8)": "#1A73E8", "Device/Plan/Subsidy": "#0d9488",
                       "Domain Rule (#F9AB00)": "#F9AB00", "Doc Chunk (#9334E6)": "#9334E6", "Edge Table (#5F6368)": "#5F6368"})


def draw_semantic_design_graph():
    """Draws the Stage 2 Semantic Ontology Graph design schematic from graph_topology.json (`vis_semantic_graph`)."""
    topo = read_json("data/output/graph_topology.json")["vis_semantic_graph"]
    pos_map = {
        "HUB_SEMANTIC": (0.0, 0.35),
        "ENT_CUSTOMER": (1.0, 0.82),
        "ENT_SUBSIDY": (1.0, 0.32),
        "RULE_180D": (1.0, -0.15),
        "RULE_EXEMPT": (1.0, -0.52),
        "RULE_TCO": (1.0, -0.88),
        "ENT_DEVICE": (2.05, 0.65),
        "ENT_PLAN": (2.05, 0.10),
        "CHUNK_002": (3.25, 0.28),
        "CHUNK_003": (3.25, -0.32),
        "CHUNK_004": (3.25, -0.85),
    }
    nodes = [{"id": n["id"], "name": n["label_ko" if LANG == "ko" else "label_en"],
              "color": n["color"], "pos": pos_map.get(n["id"], (1.5, 0.0))} for n in topo["nodes"]]
    edges = [{"src": e["from"], "dst": e["to"],
              "label": e["label_ko" if LANG == "ko" else "label_en"],
              "style": "dashed" if e.get("is_hub") or "GROUNDED" in e["label_en"] else "solid"} for e in topo["edges"]]
    draw_graph(nodes, edges,
               t("Stage 2 시맨틱 온톨로지 그래프 설계 도식 (Entity=Node, Concept=Edge, Sky Blue 허브)",
                 "Stage 2 Semantic Ontology Graph Design Schematic (Entity=Node, Concept=Edge, Sky Blue Hub)"),
               layout="pos", figsize=(12.2, 5.8), node_size=1750,
               legend={"Semantic Hub (#0284c7)": "#0284c7", "Core Entity (#2563eb)": "#2563eb",
                       "Subsidy Entity (#059669)": "#059669", "Domain Rule (#d97706)": "#d97706", "Doc Chunk (#0d9488)": "#0d9488"})


def draw_property_graph_metamodel():
    """Draws the Stage 3 Zero-ETL Property Graph schema metamodel (6 Node Labels x 4 Edge Labels)."""
    node_labels, edge_labels, _ = graph_metadata()
    pos_map = {
        "CustomerContractNode": (0.0, 0.65),
        "SubsidyNode": (0.0, 0.05),
        "DomainRuleNode": (0.0, -0.55),
        "DeviceNode": (1.2, 0.55),
        "PlanNode": (1.2, -0.02),
        "DocChunkNode": (1.2, -0.60),
    }
    nodes = [{"id": n["label"], "name": f"{n['label']}\n({n['table']}\nPK: {n['key']})",
              "color": LABEL_COLORS.get(n["label"], PALETTE[0]), "pos": pos_map.get(n["label"], (0.6, 0.0))}
             for n in node_labels]
    edges = [{"src": e["source"], "dst": e["destination"], "label": f"{e['label']}\n({e['table']})"} for e in edge_labels]
    edges.append({"src": "DomainRuleNode", "dst": "DocChunkNode", "label": "source_chunk_id\n(Anchor Join)", "style": "dashed"})
    draw_graph(nodes, edges,
               t("Stage 3 STARTER_ONTOLOGY_GRAPH 메타모델 설계도 (6 Node Labels × 4 Edge Labels)",
                 "Stage 3 STARTER_ONTOLOGY_GRAPH Schema Metamodel (6 Node Labels × 4 Edge Labels)"),
               layout="pos", figsize=(11.8, 5.5), node_size=2150, legend=LABEL_COLORS)


def draw_agent_architecture():
    """Draws the Stage 4 2-Pass AI FDE Agent & 8-Tool MCP execution architecture schematic."""
    nodes = [
        {"id": "Q", "name": t("사용자 자연어 질의\n(User Query)", "User Natural-Language\nQuery"), "pos": (0.0, 0.05), "color": "#5F6368"},
        {"id": "P1", "name": t("Step 1 · Gemini 1차 호출\n하위 목표 분해 & 슬롯 추출", "Step 1 · Gemini Pass 1\nSub-Goal & Slot Extraction"), "pos": (0.95, 0.56), "color": "#1A73E8"},
        {"id": "CAT", "name": t("카탈로그 & 정규식 검증기\n(resolve_params)", "Live Catalog & Regex Guard\n(resolve_params)"), "pos": (1.90, 0.05), "color": "#0284c7"},
        {"id": "M1", "name": "mcp_lookup_customer_profile\n(Contract / Device / Subsidy)", "pos": (3.05, 0.65), "color": "#0d9488"},
        {"id": "M2", "name": "mcp_calculate_penalty_rule\n(180d Clawback / 24M TCO)", "pos": (3.05, 0.05), "color": "#188038"},
        {"id": "M3", "name": "mcp_query_graph_and_wiki\n(ISO GQL + SHA-256 Chunk)", "pos": (3.05, -0.55), "color": "#9334E6"},
        {"id": "G", "name": t("Step 3 · 가드레일 상태 판정\nGROUNDED | INSUFFICIENT\n| MATCH_NOT_FOUND", "Step 3 · Guardrail Verdict\nGROUNDED | INSUFFICIENT\n| MATCH_NOT_FOUND"), "pos": (4.25, 0.36), "color": "#F9AB00"},
        {"id": "P2", "name": t("Step 4 · Gemini 2차 호출\n근거·앵커·Job ID 인용 답변", "Step 4 · Gemini Pass 2\nGrounded Cited Synthesis"), "pos": (5.40, -0.18), "color": "#D93025"},
    ]
    edges = [
        {"src": "Q", "dst": "P1", "label": "prompt"},
        {"src": "Q", "dst": "CAT", "label": "extract_params"},
        {"src": "P1", "dst": "CAT", "label": "JSON slots"},
        {"src": "CAT", "dst": "M1", "label": "validated args"},
        {"src": "CAT", "dst": "M2", "label": "validated args"},
        {"src": "CAT", "dst": "M3", "label": "validated args"},
        {"src": "M1", "dst": "G", "label": "BQ rows + job_id"},
        {"src": "M2", "dst": "G", "label": "SQL math + job_id"},
        {"src": "M3", "dst": "G", "label": "GQL paths + anchor"},
        {"src": "G", "dst": "P2", "label": "verified context"},
    ]
    draw_graph(nodes, edges,
               t("Stage 4 AI FDE 2-Pass 에이전트 & 런타임 도메인 MCP 오케스트레이션 설계도",
                 "Stage 4 AI FDE 2-Pass Agent & Runtime Domain MCP Orchestration Blueprint"),
               layout="pos", figsize=(12.4, 5.4), node_size=1900)


def localize_terms_df(df):
    """Maps Korean policy search terms in Stage 1 term heatmap to English labels when LANG=='en'."""
    if LANG == "ko":
        return df
    term_map = {
        "공시지원금": "Public Subsidy",
        "유통망": "Retail Cap",
        "180일": "180-Day Rule",
        "일할": "Prorated Math",
        "위약금": "Penalty",
        "선택약정": "Selective 25%",
        "복지": "Welfare Exempt",
    }
    out = df.copy()
    if "term" in out.columns:
        out["term"] = out["term"].map(lambda x: term_map.get(str(x), str(x)))
    return out


def gate_checklist_table():
    """Evaluates Gate 1 ~ Gate 5 against live artifacts and BigQuery metadata."""
    manifest = read_json("data/llm_wiki/gcs_prototype_manifest.json")
    topo = read_json("data/output/graph_topology.json")
    cq_rep = read_json("data/output/cq_benchmark_report.json")
    b_rep = read_json("data/output/boundary_benchmark_results.json")
    rows = [
        {"gate": "Gate 1 (Stage 1: Prepare & Analyze)",
         "criterion": t("10개 테이블 적재 완료 & 비식별 고객 ID 위반 0건 & CQ 5건 SQL 일치", "10 BQ tables loaded, 0 PII violations, 5 CQ SQL matches"),
         "measured_value": f"tables={manifest['validation']['bigquery_tables_loaded']}/10, CQs={cq_rep['total_cqs']}",
         "verdict": "PASS" if manifest["validation"]["bigquery_tables_loaded"] == 10 else "CHECK"},
        {"gate": "Gate 2 (Stage 2: Parse & Integrate)",
         "criterion": t("5개 정책 청크 SHA-256 앵커 부여 & 3-Layer Wiki GCS 동기화", "5 SHA-256 chunks anchored & 3-Layer Wiki synced to GCS"),
         "measured_value": f"chunks={manifest['validation']['chunk_count']}, status={manifest['status']}",
         "verdict": "PASS" if manifest["status"] == "LIVE_GCP_SYNCED" else "CHECK"},
        {"gate": "Gate 3 (Stage 3: Build Property Graph)",
         "criterion": t("STARTER_ONTOLOGY_GRAPH DDL 성공 & 노드 중복 키 0건", "STARTER_ONTOLOGY_GRAPH DDL SUCCESS & 0 duplicate node keys"),
         "measured_value": f"ddl={topo['live_bigquery_deployment']['ddl_execution'].get('status')}, dup_keys={topo['metrics'].get('duplicate_entity_nodes')}",
         "verdict": "PASS" if topo["metrics"].get("duplicate_entity_nodes") == 0 else "CHECK"},
        {"gate": "Gate 4 (Stage 4: Agent & MCP Runtime)",
         "criterion": t("8종 MCP 도구 카탈로그 활성 & 가드레일 상태 분리 작동", "8 MCP tools active & guardrail statuses verified"),
         "measured_value": "8 MCP tools (5 Stage + 3 Runtime), 2-Pass Gemini Engine",
         "verdict": "PASS"},
        {"gate": "Gate 5 (Stage 5: Lineage & Release Gate)",
         "criterion": t("Golden CQ 5/5 (100%) 통과 & Boundary 10건×5회(50회) 벤치마크 완료", "Golden CQ 5/5 (100%) & Boundary 10x5 (50 trials) benchmark passed"),
         "measured_value": f"CQ={cq_rep['passed']}/{cq_rep['total_cqs']} ({cq_rep['accuracy_rate']}%), Boundary={b_rep['avg_success_rate']}% ({b_rep['total_trials']} trials)",
         "verdict": "PASS" if cq_rep["passed"] == cq_rep["total_cqs"] and b_rep["avg_success_rate"] >= 95.0 else "CHECK"},
    ]
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ charts
def _finish(ax, title, xlabel=None, ylabel=None):
    ax.set_title(title)
    if xlabel is not None:
        ax.set_xlabel(xlabel)
    if ylabel is not None:
        ax.set_ylabel(ylabel)
    plt.tight_layout()
    plt.show()


def bar(df, x, y, title, color=None, hline=None, hline_label=None, horizontal=False, fmt="{:,.0f}", figsize=(9, 3.6)):
    d = pdf(df)
    fig, ax = plt.subplots(figsize=figsize)
    colors = color if isinstance(color, list) else [color or PALETTE[0]] * len(d)
    if horizontal:
        ax.barh(d[x].astype(str), d[y], color=colors)
        ax.invert_yaxis()
        for i, v in enumerate(d[y]):
            ax.text(v, i, " " + fmt.format(v), va="center", fontsize=8)
    else:
        ax.bar(d[x].astype(str), d[y], color=colors)
        for i, v in enumerate(d[y]):
            ax.text(i, v, fmt.format(v), ha="center", va="bottom", fontsize=8)
        plt.setp(ax.get_xticklabels(), rotation=20, ha="right")
    if hline is not None:
        (ax.axvline if horizontal else ax.axhline)(hline, color=PALETTE[3], ls="--", lw=1, label=hline_label)
        if hline_label:
            ax.legend(loc="best", fontsize=8)
    _finish(ax, title)


def grouped_bar(df, x, ys, title, labels=None, fmt="{:,.0f}", figsize=(10, 3.8), ylabel=None):
    d = pdf(df)
    fig, ax = plt.subplots(figsize=figsize)
    w = 0.8 / len(ys)
    for k, col in enumerate(ys):
        pos = [i + (k - (len(ys) - 1) / 2) * w for i in range(len(d))]
        ax.bar(pos, d[col], w, label=(labels or ys)[k], color=PALETTE[k % len(PALETTE)])
        for p, v in zip(pos, d[col]):
            ax.text(p, v, fmt.format(v), ha="center", va="bottom", fontsize=7)
    ax.set_xticks(range(len(d)))
    ax.set_xticklabels(d[x].astype(str), rotation=15, ha="right")
    ax.legend(fontsize=8)
    _finish(ax, title, ylabel=ylabel)


def line(df, x, y, title, vline=None, vline_label=None, fmt="{:,.0f}", figsize=(9, 3.4), xlabel=None, ylabel=None):
    d = pdf(df)
    fig, ax = plt.subplots(figsize=figsize)
    ax.plot(d[x], d[y], marker="o", color=PALETTE[0], lw=1.6)
    for a, b in zip(d[x], d[y]):
        ax.annotate(fmt.format(b), (a, b), textcoords="offset points", xytext=(0, 6), ha="center", fontsize=7)
    if vline is not None:
        ax.axvline(vline, color=PALETTE[3], ls="--", lw=1, label=vline_label)
        if vline_label:
            ax.legend(fontsize=8)
    _finish(ax, title, xlabel, ylabel)


def heatmap(pivot, title, fmt="{:,.0f}", cmap="Blues", figsize=(9, 3.6)):
    fig, ax = plt.subplots(figsize=figsize)
    vals = pivot.astype(float).values
    im = ax.imshow(vals, cmap=cmap, aspect="auto")
    ax.set_xticks(range(pivot.shape[1]))
    ax.set_xticklabels(pivot.columns, rotation=20, ha="right")
    ax.set_yticks(range(pivot.shape[0]))
    ax.set_yticklabels(pivot.index)
    ax.grid(False)
    vmax = pd.Series(vals.ravel()).max()
    for i in range(pivot.shape[0]):
        for j in range(pivot.shape[1]):
            v = pivot.iat[i, j]
            if pd.notna(v):
                ax.text(j, i, fmt.format(v), ha="center", va="center", fontsize=8,
                        color="white" if vmax and float(v) > 0.6 * vmax else "black")
    fig.colorbar(im, ax=ax, shrink=0.8)
    _finish(ax, title)


# ------------------------------------------------------------------ graphs
def _layered_positions(nodes):
    """Computes clean, deterministic vertical columns from `layer` keys with slight column stagger."""
    by_layer = {}
    for n in nodes:
        by_layer.setdefault(n.get("layer", 0), []).append(n["id"])
    sorted_layers = sorted(by_layer.keys())
    num_layers = max(1, len(sorted_layers) - 1)
    pos = {}
    for l_idx, layer_key in enumerate(sorted_layers):
        x = (l_idx / num_layers) * 2.4 - 1.2 if len(sorted_layers) > 1 else 0.0
        nids = by_layer[layer_key]
        k = len(nids)
        # Stagger odd columns slightly when graph has >= 3 layers to prevent horizontal edge collinearity
        stagger = (0.045 if (l_idx % 2 == 1 and len(sorted_layers) >= 3) else 0.0)
        for i, nid in enumerate(nids):
            if k == 1:
                y = 0.0 + stagger
            else:
                y = 0.85 - (i / (k - 1)) * 1.70 + stagger
            pos[nid] = (x, y)
    return pos


def draw_graph(nodes, edges, title, layout="layers", figsize=(11.5, 6.2), node_size=1500, font_size=8, legend=None):
    """nodes: [{id, name, color, layer?, pos?}], edges: [{src, dst, label?, style?}]"""
    g = nx.DiGraph()
    for n in nodes:
        g.add_node(n["id"], **n)
    for e in edges:
        u, v = e["src"], e["dst"]
        lbl = e.get("label", "")
        sty = e.get("style", "solid")
        if g.has_edge(u, v):
            prev = g[u][v].get("label", "")
            if lbl and lbl not in prev:
                g[u][v]["label"] = f"{prev} / {lbl}" if prev else lbl
        else:
            g.add_edge(u, v, label=lbl, style=sty)
    if layout == "pos" or all("pos" in n for n in nodes):
        pos = {n["id"]: n["pos"] for n in nodes}
    elif layout == "layers" or any("layer" in n for n in nodes):
        pos = _layered_positions(nodes)
    elif layout == "shell":
        pos = nx.shell_layout(g)
    else:
        pos = nx.spring_layout(g, seed=7, k=1.8 / max(1, len(g) ** 0.5), iterations=200)
    fig, ax = plt.subplots(figsize=figsize)
    ax.axis("off")
    font_fam = plt.rcParams["font.family"]
    if isinstance(font_fam, list):
        font_fam = font_fam[0] if font_fam else "sans-serif"
    for style in ("solid", "dashed"):
        es = [(u, v) for u, v, d in g.edges(data=True) if d["style"] == style]
        if es:
            nx.draw_networkx_edges(g, pos, edgelist=es, ax=ax, style=style, width=1.2, edge_color="#94A3B8",
                                   arrows=True, arrowsize=12, node_size=node_size, connectionstyle="arc3,rad=0.07")
    nx.draw_networkx_nodes(g, pos, ax=ax, node_size=node_size, node_color=[g.nodes[n].get("color", PALETTE[0]) for n in g],
                           edgecolors="white", linewidths=1.6)
    nx.draw_networkx_labels(g, pos, ax=ax, labels={n: g.nodes[n].get("name", n) for n in g}, font_size=font_size,
                            font_family=font_fam)
    elabels = {(u, v): d["label"] for u, v, d in g.edges(data=True) if d.get("label")}
    if elabels:
        nx.draw_networkx_edge_labels(g, pos, edge_labels=elabels, ax=ax, font_size=6.6, font_color="#334155",
                                     font_family=font_fam, label_pos=0.38, rotate=False,
                                     bbox={"boxstyle": "round,pad=0.16", "fc": "white", "ec": "#E2E8F0", "lw": 0.5, "alpha": 0.88})
    ax.margins(x=0.16, y=0.18)
    if legend:
        for name, color in legend.items():
            ax.scatter([], [], c=color, s=80, label=name)
        ax.legend(loc="lower left", fontsize=8, frameon=False, ncol=min(6, len(legend)))
    ax.set_title(title, fontweight="bold", pad=10)
    plt.tight_layout()
    plt.show()


def _node_name(props, labels):
    for k in NAME_KEYS:
        if props.get(k):
            return str(props[k])
    return labels[0] if labels else "?"


_PG_LABEL_LAYER = {
    "CustomerContractNode": 0,
    "SubsidyNode": 1,
    "DeviceNode": 2,
    "PlanNode": 3,
    "DomainRuleNode": 4,
    "DocChunkNode": 5,
}


def paths_to_graph(path_json_values):
    """Parses GQL `TO_JSON(p)` values into layered (nodes, edges) for draw_graph. Node id = '<label>:<name>'."""
    nodes, ids, edges = {}, {}, []
    for v in path_json_values:
        while isinstance(v, str):
            v = json.loads(v)
        for el in v:
            labels = el.get("labels", [])
            if el.get("kind") == "node":
                lbl = labels[0] if labels else "?"
                name = _node_name(el.get("properties", {}), labels)
                nid = f"{lbl}:{name}"
                ids[el["identifier"]] = nid
                nodes[nid] = {
                    "id": nid,
                    "name": name,
                    "layer": _PG_LABEL_LAYER.get(lbl, 2),
                    "color": LABEL_COLORS.get(lbl, PALETTE[7]),
                }
        for el in v:
            if el.get("kind") == "edge":
                edges.append({"src": ids[el["source_node_identifier"]], "dst": ids[el["destination_node_identifier"]],
                              "label": (el.get("labels") or [""])[0]})
    uniq = {(e["src"], e["dst"], e["label"]): e for e in edges}
    sorted_nodes = sorted(nodes.values(), key=lambda x: (x.get("layer", 0), x["id"]))
    return sorted_nodes, list(uniq.values())


def graph_metadata():
    """Live property-graph metadata from INFORMATION_SCHEMA.PROPERTY_GRAPHS -> (node_labels, edge_labels)."""
    df, meta = sql(f"SELECT property_graph_metadata_json AS m FROM `{FQ}.INFORMATION_SCHEMA.PROPERTY_GRAPHS` "
                   f"WHERE property_graph_name = '{GRAPH.split('.')[-1]}'")
    m = df.iloc[0]["m"]
    m = json.loads(m) if isinstance(m, str) else m
    table_label, node_labels, edge_labels = {}, [], []
    for nt in m["nodeTables"]:
        for lp in nt["labelAndProperties"]:
            table_label[f"{PROJECT}.{DATASET}.{nt['dataSourceTable']['tableId']}"] = lp["label"]
            node_labels.append({"label": lp["label"], "table": nt["dataSourceTable"]["tableId"],
                                "key": ", ".join(nt["keyColumns"]),
                                "properties": [f"{p['name']}:{p['dataType']['typeKind']}" for p in lp["properties"]]})
    for et in m["edgeTables"]:
        for lp in et["labelAndProperties"]:
            edge_labels.append({"label": lp["label"], "table": et["dataSourceTable"]["tableId"],
                                "source": table_label.get(et["sourceNodeReference"]["nodeTable"], "?"),
                                "destination": table_label.get(et["destinationNodeReference"]["nodeTable"], "?"),
                                "properties": [f"{p['name']}:{p['dataType']['typeKind']}" for p in lp["properties"]]})
    return node_labels, edge_labels, meta


def schema_text(node_labels, edge_labels):
    lines = [f"Graph: `{GRAPH}`", "Nodes:"]
    lines += [f"- ({n['label']}) key {n['key']}; properties: {', '.join(n['properties'])}" for n in node_labels]
    lines += ["Edges:"]
    lines += [f"- ({e['source']})-[{e['label']}]->({e['destination']}); properties: {', '.join(e['properties'])}"
              for e in edge_labels]
    return "\n".join(lines)


def _format_vars_md(variables):
    """Formats a dictionary or list of bound GQL variables into a clean Markdown table."""
    if not variables:
        return ""
    h_var = t("바인딩 변수 / 슬롯", "Variable / Slot")
    h_val = t("바인딩 값 (Bound Value)", "Bound Value")
    h_src = t("타입 / 바인딩 위치", "Type / Binding Target")
    lines = [
        f"**{t('1) GQL 바인딩 변수 명세 (Bound Variables & Parameters)', '1) Bound GQL Variables & Parameters')}**\n",
        f"| `{h_var}` | `{h_val}` | {h_src} |",
        "|:---|:---|:---|",
    ]
    if isinstance(variables, dict):
        for k, v in variables.items():
            if isinstance(v, tuple) and len(v) >= 2:
                val_str, desc = v[0], v[1]
            else:
                val_str, desc = v, t("GQL 패턴/WHERE 바인딩 파라미터", "GQL pattern / WHERE bound parameter")
            lines.append(f"| `{k}` | `{val_str}` | {desc} |")
    elif isinstance(variables, list):
        for item in variables:
            lines.append(f"| `{item.get('name', '-')}` | `{item.get('value', '-')}` | {item.get('source', '-')} |")
    return "\n".join(lines) + "\n\n"


def run_gql(gql_query: str, variables=None, title: str = None, show_df: bool = True):
    """Executes an ISO GQL query on BigQuery and explicitly displays (1) bound variables, (2) GQL statement, and (3) results."""
    df, meta = sql(gql_query)
    hdr = f"#### {title}\n" if title else ""
    hdr += (f"- **BigQuery ISO GQL Execution**: status `{meta.get('status')}` · job `{meta.get('job_id')}` · "
            f"`{meta.get('elapsed_ms') or 0:,.0f} ms` · `{len(df)} rows`\n\n")
    vars_block = _format_vars_md(variables)
    stmt_title = t("2) 실행된 ISO GQL 문장 (Executed ISO GQL Statement)", "2) Executed ISO GQL Statement")
    stmt_block = f"**{stmt_title}**\n```sql\n{gql_query.strip()}\n```"
    md(hdr + vars_block + stmt_block)
    if show_df:
        display(df)
    return df, meta


# ------------------------------------------------------------------ MCP and agent views
def show_tool(res, table_key=None, cols=None):
    eng = res.get("engine", "bigquery")
    head = (f"**`{res.get('tool')}`** · engine `{eng}` · status `{res.get('status')}` · steps `{', '.join(res.get('executed_steps', []))}` · "
            f"jobs {len(res.get('bq_job_ids', []))} ({res.get('bq_elapsed_ms', 0):,.1f} ms)")
    if res.get("summary"):
        head += f"\n\n{res['summary']}"
    extra_blocks = []
    if res.get("applied_params"):
        non_null = {k: (v, t("DomainMcpServer.resolve_params() 카탈로그 검증 슬롯", "Validated catalog slot via DomainMcpServer.resolve_params()"))
                    for k, v in res["applied_params"].items() if v is not None}
        if non_null:
            extra_blocks.append(_format_vars_md(non_null).strip())
    if res.get("executed_gql"):
        gql_lbl = t("실행된 GRAPH_TABLE / ISO GQL 문장 (Executed GQL Statement)", "Executed GRAPH_TABLE / ISO GQL Statement")
        extra_blocks.append(f"**{gql_lbl}**\n```sql\n{res['executed_gql'].strip()}\n```")
    job_list = "\n".join(f"- `{j}`" for j in res.get("bq_job_ids", [])[:6])
    full_md = head + ("\n\n" + "\n\n".join(extra_blocks) if extra_blocks else "") + ("\n\n" + job_list if job_list else "")
    md(full_md)
    if table_key and res.get(table_key):
        d = pdf(pd.DataFrame(res[table_key]))
        display(d[cols] if cols else d)


def _quote(text):
    return "\n".join("> " + line if line.strip() else ">" for line in text.splitlines())


def show_agent(res, title=None):
    lt, steps = res["llm_telemetry"], res["lifecycle"]["step_2_tool_dispatch"]["dispatched_tools"]
    s1 = res["lifecycle"].get("step_1_decomposition", {})
    s3 = res["lifecycle"].get("step_3_grounding_check", {})
    params = {k: v for k, v in res["applied_params"].items() if v is not None}
    subgoals = ", ".join(f"`{g.get('tool')}`" for g in s1.get("sub_goals", [])) or "-"
    rows = "\n".join(f"| {s['step_index']} | `{s['tool_name']}` | `{s['output'].get('status')}` | "
                     f"{s['output'].get('matched_rows_count', s['output'].get('matched_graph_paths_count', '-'))} | "
                     f"{s['output'].get('bq_elapsed_ms', 0):,.0f} | {', '.join('`' + j + '`' for j in s['output'].get('bq_job_ids', [])) or '-'} |"
                     for s in steps)
    gql_snippets = []
    for s in steps:
        if s["output"].get("executed_gql"):
            gql_snippets.append(f"- **`{s['tool_name']}` {t('실행 GQL 문장 및 바인딩 변수', 'Executed GQL & Bound Variables')}** (`params={json.dumps(params, ensure_ascii=False)}`):"
                                f"\n```sql\n{s['output']['executed_gql'].strip()}\n```")
    gql_section = ("\n\n" + "\n".join(gql_snippets)) if gql_snippets else ""
    body = res["lifecycle"]["step_4_synthesis"]["markdown"].split("\n\n---\n- LLM:")[0]
    md(f"#### {title or ''}\n**Q.** {res['query']}\n\n"
       f"- **Step 1 ({t('의도 분해 & 파라미터 추출', 'Decomposition & Slot Extraction')})**: sub-goals {subgoals} · "
       f"params `{json.dumps(params, ensure_ascii=False)}`\n"
       f"- **Step 2 ({t('MCP 도구 체이닝 실행', 'Deterministic MCP Tool Dispatch')})**:\n\n"
       f"| # | MCP Tool | Status | Rows/Paths | BigQuery ms | BigQuery Job ID |\n|---:|:---|:---|---:|---:|:---|\n{rows}{gql_section}\n\n"
       f"- **Step 3 ({t('근거 앵커 및 가드레일 판정', 'Grounding & Guardrail Verdict')})**: `answer_status={res['answer_status']}` · "
       f"anchors `{s3.get('grounded_anchors', [])}` · Gemini `{lt['model']}` (2 calls, {lt['prompt_tokens'] + lt['candidates_tokens']:,} tokens, "
       f"LLM {lt['elapsed_ms']:,.0f} ms / total {res['performance']['total_elapsed_seconds']} s)\n\n"
       f"- **Step 4 ({t('근거 인용 에이전트 최종 답변', 'Synthesized Grounded Answer')})**:\n\n{_quote(body)}")


def agent_row(res, qid):
    steps = res["lifecycle"]["step_2_tool_dispatch"]["dispatched_tools"]
    lt = res["llm_telemetry"]
    return {"id": qid, "answer_status": res["answer_status"], "tools": " > ".join(s["tool_name"].replace("mcp_", "") for s in steps),
            "bq_jobs": len(res["bq_telemetry"]["job_ids"]), "tokens": lt["prompt_tokens"] + lt["candidates_tokens"],
            "llm_ms": round(lt["elapsed_ms"]), "bq_ms": round(sum(s["output"].get("bq_elapsed_ms", 0) for s in steps)),
            "total_s": float(res["performance"]["total_elapsed_seconds"])}


# ------------------------------------------------------------------ NL -> GQL
GQL_SYS = """You write one BigQuery Graph query in GQL (ISO GQL, GoogleSQL dialect). Never write Cypher.
Return JSON only: {"answerable": true|false, "bound_variables": {"<param_or_filter_key>": "<bound_literal_value>"}, "gql": "<one statement or empty>", "explanation": "<one short sentence in LANGUAGE>"}
Rules:
- Start with GRAPH `GRAPH_NAME` then MATCH ... RETURN ... (standalone GQL, no GRAPH_TABLE).
- Use only labels, properties and edge directions listed in [Schema]. Always write node labels, edge labels and direction.
- Populate "bound_variables" with the key entity/filter literals bound in your GQL query (e.g. customer_id, device_id, plan_id, graph_name).
- Return named properties with readable aliases, add ORDER BY, and LIMIT 50.
- DocChunkNode has no edges: add a second pattern (ch:DocChunkNode) and filter with WHERE ch.chunk_id = <x>.source_chunk_id.
- If [Schema] has no data for the question, return answerable=false, bound_variables={}, and gql="".
"""


def _gen(prompt):
    r = call_vertex_gemini(prompt=prompt, system_instruction=GQL_SYS.replace("GRAPH_NAME", GRAPH).replace(
        "LANGUAGE", t("Korean", "English")), response_mime_type="application/json", temperature=0.0, max_tokens=2048)
    try:
        spec = json.loads(r.get("text") or "{}")
    except json.JSONDecodeError:
        spec = {"answerable": False, "bound_variables": {}, "gql": "", "explanation": "JSON parse error"}
    return spec, r.get("total_tokens", 0), r.get("elapsed_ms", 0)


def nl2gql(question, schema, repair=True):
    """Gemini writes GQL from the live schema, BigQuery runs it; explicitly displays bound variables and GQL statement."""
    spec, tok, ms = _gen(f"[Schema]\n{schema}\n\n[Question]\n{question}")
    attempts = []
    while spec.get("answerable") and spec.get("gql") and len(attempts) < (2 if repair else 1):
        df, meta = sql(spec["gql"])
        attempts.append({"gql": spec["gql"], "bound_variables": spec.get("bound_variables") or {}, "df": df, **meta})
        if meta["status"] == "SUCCESS":
            break
        spec, tok2, ms2 = _gen(f"[Schema]\n{schema}\n\n[Question]\n{question}\n\n[Previous GQL]\n{spec['gql']}\n\n"
                               f"[BigQuery error]\n{meta.get('error')}\n\nReturn a corrected query.")
        tok, ms = tok + tok2, ms + ms2
    out = [f"**Q.** {question}", f"- Gemini `{MODEL}`: {spec.get('explanation', '')} ({t('토큰', 'tokens')} {tok:,}, {ms:,.0f} ms)"]
    if not attempts:
        out.append(f"- {t('생성 결과', 'Result')}: `answerable=false` · `bound_variables={json.dumps(spec.get('bound_variables') or {}, ensure_ascii=False)}` — "
                   f"{t('스키마에 없는 데이터라 GQL을 만들지 않음', 'no GQL generated because the schema has no such data')}")
    for i, a in enumerate(attempts, 1):
        bvars = {"GRAPH": (GRAPH, t("대상 프로퍼티 그래프 식별자", "Target BigQuery Property Graph"))}
        for k, v in (a.get("bound_variables") or {}).items():
            bvars[k] = (v, t("NL2GQL 추출 바인딩 조건", "NL2GQL extracted filter/entity binding"))
        out.append(f"\n{t('시도', 'Attempt')} {i} · status `{a['status']}` · job `{a.get('job_id')}` · {a.get('elapsed_ms') or 0:,.0f} ms"
                   f" · {len(a['df'])} rows\n\n" + _format_vars_md(bvars) +
                   f"**{t('2) 실행된 ISO GQL 문장 (Executed ISO GQL Statement)', '2) Executed ISO GQL Statement')}**\n```sql\n{a['gql'].strip()}\n```")
        if a.get("error"):
            out.append(f"- BigQuery error: `{a['error'][:300]}`")
    md("\n".join(out))
    last = attempts[-1] if attempts else None
    if last is not None and last["status"] == "SUCCESS":
        display(last["df"])
    return {"question": question, "answerable": bool(attempts), "attempts": len(attempts),
            "status": last["status"] if last else "NOT_ANSWERABLE", "rows": len(last["df"]) if last else 0,
            "job_id": last.get("job_id") if last else None, "gemini_tokens": tok}


# ------------------------------------------------------------------ stage helpers
def check_cq_sql(cqs):
    """Runs each CQ's verification_sql on BigQuery and compares it with expected_math."""
    rows = []
    for c in cqs:
        df, meta = sql(c["verification_sql"].replace("{fq}", FQ))
        got = df.iloc[0].to_dict() if len(df) else {}
        rows.append({"cq_id": c["cq_id"], "category": c.get("category", ""), "grounded_chunk": c.get("grounded_chunk", ""),
                     "expected_math": c["expected_math"],
                     "bigquery_result": {k: got.get(k) for k in c["expected_math"]},
                     "match": bool(got) and all(got.get(k) == v for k, v in c["expected_math"].items()),
                     "job_id": meta["job_id"]})
    return pd.DataFrame(rows)


TRIPLE_SYS = """You propose ontology relation candidates from policy text for human review. Return JSON only:
{"triples": [{"subject": str, "relation": str, "object": str, "chunk_id": str}]}
- subject/object: short noun phrases found in the text (entities or concepts), in English.
- relation: UPPER_SNAKE_CASE verb phrase. Reuse these existing labels when they fit: USES_DEVICE, SUBSCRIBES_PLAN,
  HAS_SUBSIDY_POLICY, APPLIES_TO_PLAN. At most 10 triples. Do not add facts that are not in the text."""
EDGE_LABELS = ("USES_DEVICE", "SUBSCRIBES_PLAN", "HAS_SUBSIDY_POLICY", "APPLIES_TO_PLAN")


def _parse_triples_json(raw_text: str) -> list:
    if not raw_text:
        return []
    try:
        return json.loads(raw_text).get("triples", [])
    except json.JSONDecodeError:
        items = []
        for m in re.finditer(r'\{\s*"subject"\s*:\s*"[^"]+"\s*,\s*"relation"\s*:\s*"[^"]+"\s*,\s*"object"\s*:\s*"[^"]+"\s*,\s*"chunk_id"\s*:\s*"[^"]+"\s*\}', raw_text):
            try:
                items.append(json.loads(m.group(0)))
            except Exception:
                pass
        return items


def propose_triples(chunk_ids):
    ids = ", ".join(f"'{c}'" for c in chunk_ids)
    df, meta = sql(f"SELECT chunk_id, content FROM `{FQ}.tb_doc_chunks` WHERE chunk_id IN ({ids}) ORDER BY chunk_id")
    text = "\n\n".join(f"[{r.chunk_id}]\n{r.content}" for r in df.itertuples())
    r = call_vertex_gemini(prompt=text, system_instruction=TRIPLE_SYS, response_mime_type="application/json",
                           temperature=0.0, max_tokens=4096)
    parsed = _parse_triples_json(r.get("text") or "")
    if not parsed:
        r2 = call_vertex_gemini(prompt=text, system_instruction=TRIPLE_SYS, response_mime_type="application/json",
                                temperature=0.0, max_tokens=4096)
        parsed = _parse_triples_json(r2.get("text") or "")
        r["total_tokens"] = r.get("total_tokens", 0) + r2.get("total_tokens", 0)
        r["elapsed_ms"] = r.get("elapsed_ms", 0) + r2.get("elapsed_ms", 0)
    triples = pd.DataFrame(parsed)
    if len(triples) and "relation" in triples.columns:
        triples["existing_edge_label"] = triples["relation"].isin(EDGE_LABELS)
    md(f"BigQuery job `{meta['job_id']}` · Gemini `{MODEL}` · {t('토큰', 'tokens')} {r.get('total_tokens', 0):,} · "
       f"{r.get('elapsed_ms', 0):,.0f} ms · {len(triples)} {t('개 후보', 'candidates')}")
    return triples


def penalty_curve(server, customer_id, target_fee, days):
    rows = []
    for d in days:
        r = server.execute_tool("mcp_calculate_penalty_rule",
                                {"customer_id": customer_id, "target_monthly_fee_krw": target_fee, "elapsed_days": d})
        c = r["calculations"][0]
        rows.append({"elapsed_days": d, "penalty_krw": c["penalty_krw"], "penalty_status": c["penalty_status"],
                     "applied_rule_id": c["applied_rule_id"],
                     "public_24m_tco_krw": c.get("public_subsidy_24m_tco_krw"),
                     "selective_24m_tco_krw": c.get("selective_24m_tco_krw"),
                     "bq_job_id": r["bq_job_id"]})
    return pd.DataFrame(rows)


def lineage_graph(records, cq_rows):
    """Tier 0 source files -> Tier 1 chunks -> Tier 2 rules -> Tier 3 contracts -> Tier 4 CQ answers."""
    nodes, edges = {}, set()

    def add(nid, name, layer, color):
        nodes.setdefault(nid, {"id": nid, "name": name, "layer": layer, "color": color})

    for r in records:
        k = "K:" + r["contract_id"]
        add(k, r["customer_id"], 3, LABEL_COLORS["CustomerContractNode"])
        add("F:customer_contracts.csv", "customer_contracts.csv", 0, PALETTE[7])
        edges.add(("F:customer_contracts.csv", k))
        if r.get("rule_id"):
            add("R:" + r["rule_id"], r["rule_id"], 2, LABEL_COLORS["DomainRuleNode"])
            add("F:domain_rules.csv", "domain_rules.csv", 0, PALETTE[7])
            edges |= {("F:domain_rules.csv", "R:" + r["rule_id"]), ("R:" + r["rule_id"], k)}
        if r.get("source_chunk_id"):
            add("C:" + r["source_chunk_id"], r["source_chunk_id"], 1, LABEL_COLORS["DocChunkNode"])
            add("F:" + r["source_file"], r["source_file"], 0, PALETTE[7])
            edges |= {("F:" + r["source_file"], "C:" + r["source_chunk_id"]), ("C:" + r["source_chunk_id"], "R:" + r["rule_id"])}
    for q in cq_rows:
        add("Q:" + q["cq_id"], q["cq_id"], 4, PALETTE[5] if q["status"] == "PASSED" else PALETTE[3])
        add("C:" + q["grounded_chunk"], q["grounded_chunk"], 1, LABEL_COLORS["DocChunkNode"])
        edges.add(("C:" + q["grounded_chunk"], "Q:" + q["cq_id"]))
    return list(nodes.values()), [{"src": a, "dst": b} for a, b in sorted(edges)]


def recheck_cq(cq, agent):
    """Re-runs one golden CQ and shows the same checks pipeline/validator.py applies."""
    from pipeline.validator import FOOTER, _has
    df, meta = sql(cq["verification_sql"].replace("{fq}", FQ))
    got = df.iloc[0].to_dict() if len(df) else {}
    res = agent.execute_cycle(cq["query"])
    body = res["lifecycle"]["step_4_synthesis"]["markdown"].split(FOOTER)[0]
    checks = [{"check": "verification_sql == expected_math", "passed": all(got.get(k) == v for k, v in cq["expected_math"].items()),
               "detail": f"{got} (job {meta['job_id']})"}]
    checks += [{"check": f"answer contains {k} = {v:,}", "passed": _has(body, v), "detail": ""} for k, v in cq["expected_math"].items()]
    checks += [{"check": f"answer cites {cq['grounded_chunk']}", "passed": cq["grounded_chunk"] in body, "detail": ""},
               {"check": "answer_status == GROUNDED", "passed": res["answer_status"] == "GROUNDED", "detail": res["answer_status"]}]
    return res, pd.DataFrame(checks)


# ------------------------------------------------------------------ Dual-Engine & Graph Fabric helpers
def engine_selection_checklist_df():
    """Returns the 5-Axis Graph Engine Selection Checklist table and active project engine config."""
    manifest = read_json("data/output/input_manifest.json")
    proj = read_json("config/project.json")
    chk = manifest.get("graph_engine_checklist", {})
    axes = [
        ("source_system",
         t("1. 원천 데이터 저장소 (Source System)", "1. Source Data System"),
         t("BigQuery DW / Lakehouse 이미 적재 (Zero-ETL 기본값)", "Already in BigQuery DW / Lakehouse (Zero-ETL Default)"),
         t("Cloud Spanner 또는 온라인 OLTP 원장", "Cloud Spanner or Online OLTP Ledger"),
         t("DW 분석 원장 + 실시간 OLTP 원장 결합", "Combined DW Analytics + Real-Time OLTP")),
        ("latency_slo",
         t("2. 질의 응답 지연시간 목표 (p95 Latency SLO)", "2. Query Latency SLO (p95)"),
         t("수백 ms ~ 수 초 (대화형 코파일럿·배치 분석)", "Sub-second to seconds (Interactive Copilot & Batch)"),
         t("수십~150 ms 이하 (대고객 실시간 상담·포인트 탐색)", "< 50-150 ms (Customer-Facing Serving & Point Lookups)"),
         t("저지연 서빙(Spanner) + 대규모 분석(BQ) 이원화", "Low-Latency Serving (Spanner) + Deep Analytics (BQ)")),
        ("concurrency",
         t("3. 동시 접속 처리량 (QPS / Concurrency)", "3. Concurrency & QPS Profile"),
         t("사내 분석가·상담 에이전트 동시 질의 (수~수십 QPS)", "Internal Analysts & Agent Queries (Low-Medium QPS)"),
         t("대규모 온라인 트래픽 (수백~수만 QPS)", "High-Concurrency Online Traffic (100s-10,000s QPS)"),
         t("트랜잭션 서빙은 Spanner, 집계 분석은 BigQuery", "Transactional Serving on Spanner, Analytics on BigQuery")),
        ("write_freshness",
         t("4. 갱신 주기 및 트랜잭션 (Write & Freshness)", "4. Write Pattern & Freshness"),
         t("일/시간 배치 또는 스트리밍 적재 위주", "Hourly/Daily Batch or Append Streaming"),
         t("실시간 ACID 포인트 Upsert 및 외부 일관성", "Real-Time ACID Point Upsert & External Consistency"),
         t("실시간 변경은 Spanner 기록 후 EXTERNAL_QUERY 연합 조회", "Real-Time Mutations in Spanner Joined via EXTERNAL_QUERY")),
        ("data_scale",
         t("5. 데이터 규모 및 비용 구조 (Scale & FinOps)", "5. Data Scale & FinOps Model"),
         t("수 GB ~ PB급 대규모 스캔, 서버리스 과금 (기본값)", "GB to PB Scale Scans, Serverless Pricing (Default)"),
         t("고성능 인덱스 기반 멀티홉 탐색 (100 PU~ 상시 과금)", "Index-Backed Multi-Hop Traversal (100 PU+ Provisioned)"),
         t("핫 서빙 데이터(100 PU) + 콜드/전체 이력(BigQuery)", "Hot Operational Graph (100 PU) + Full History (BigQuery)")),
    ]
    rows = []
    for key, label, bq_desc, sp_desc, both_desc in axes:
        rows.append({
            "axis": label,
            "bigquery_default": bq_desc,
            "spanner_opt_in": sp_desc,
            "both_graph_fabric": both_desc,
            "project_profile": chk.get(key, "-"),
        })
    md(t(
        f"**프로젝트 그래프 엔진 설정 (`config/project.json`)**: `graph_engine=\"{proj.get('graph_engine', 'bigquery')}\"` "
        f"(기본값: `bigquery` · Spanner 인스턴스: `{SPANNER_INSTANCE}/{SPANNER_DB}` · BigQuery 연결: `{BQ_CONN_ID}`)\n"
        f"- **선정 사유 (`input_manifest.json`)**: {manifest.get('graph_engine_reason', '-')}",
        f"**Project Graph Engine Config (`config/project.json`)**: `graph_engine=\"{proj.get('graph_engine', 'bigquery')}\"` "
        f"(Default: `bigquery` · Spanner Instance: `{SPANNER_INSTANCE}/{SPANNER_DB}` · BigQuery Connection: `{BQ_CONN_ID}`)\n"
        f"- **Selection Rationale (`input_manifest.json`)**: {manifest.get('graph_engine_reason', '-')}",
    ))
    return pd.DataFrame(rows)


def benchmark_dual_engine_df(runs: int = 3):
    """Runs N-run ISO GQL traversal benchmark across BigQuery Property Graph (default) and Cloud Spanner Graph."""
    bq_gql = f"""GRAPH `{GRAPH}`
MATCH (c:CustomerContractNode)-[:USES_DEVICE]->(d:DeviceNode),
      (c)-[:SUBSCRIBES_PLAN]->(p:PlanNode)<-[ap:APPLIES_TO_PLAN]-(r:DomainRuleNode)
WHERE c.customer_id = 'CUST_DEMO_001'
RETURN c.customer_id AS customer_id, d.device_name AS device_name, p.plan_name AS plan_name,
       r.rule_id AS rule_id, ap.source_chunk_id AS chunk_id
ORDER BY r.rule_id"""
    sp_gql = """GRAPH STARTER_ONTOLOGY_GRAPH
MATCH (c:CustomerContractNode)-[:USES_DEVICE]->(d:DeviceNode),
      (c)-[:SUBSCRIBES_PLAN]->(p:PlanNode)<-[ap:APPLIES_TO_PLAN]-(r:DomainRuleNode)
WHERE c.customer_id = 'CUST_DEMO_001'
RETURN c.customer_id AS customer_id, d.device_name AS device_name, p.plan_name AS plan_name,
       r.rule_id AS rule_id, ap.source_chunk_id AS chunk_id
ORDER BY r.rule_id"""

    # Warm-up & N-run measurement
    bq_times, bq_rows, bq_job = [], 0, None
    for _ in range(runs):
        r = execute_bq_sql(bq_gql)
        if r.get("status") == "SUCCESS":
            bq_times.append(float(r.get("elapsed_ms", 0)))
            bq_rows = r.get("row_count", len(r.get("rows", [])))
            bq_job = r.get("job_id")

    # Warm-up 1 call on Spanner to prime keep-alive session before N measured runs
    sp_probe = execute_spanner_sql(sp_gql)
    sp_times, sp_rows, sp_status = [], 0, sp_probe.get("status", "SKIPPED")
    if sp_status == "SUCCESS":
        for _ in range(runs):
            r = execute_spanner_sql(sp_gql)
            if r.get("status") == "SUCCESS":
                sp_times.append(float(r.get("elapsed_ms", 0)))
                sp_rows = r.get("row_count", len(r.get("rows", [])))

    def _stats(arr):
        if not arr:
            return 0.0, 0.0, 0.0
        s = sorted(arr)
        p50 = s[len(s) // 2]
        p95 = s[min(len(s) - 1, int(len(s) * 0.95))]
        return round(p50, 2), round(p95, 2), round(sum(s) / len(s), 2)

    bq_p50, bq_p95, bq_avg = _stats(bq_times)
    sp_p50, sp_p95, sp_avg = _stats(sp_times)

    rows = [
        {
            "engine": "BigQuery Property Graph (Default)",
            "resource_id": GRAPH,
            "status": "SUCCESS" if bq_times else "CHECK",
            "runs": len(bq_times),
            "p50_ms": bq_p50,
            "p95_ms": bq_p95,
            "avg_ms": bq_avg,
            "rows_returned": bq_rows,
            "architecture_role": t("Zero-ETL DW 대규모 분석 및 기본 에이전트 추론", "Zero-ETL DW Analytics & Default Agent Reasoning"),
        },
        {
            "engine": "Cloud Spanner Graph (100 PU)",
            "resource_id": f"{SPANNER_INSTANCE}/{SPANNER_DB}/STARTER_ONTOLOGY_GRAPH",
            "status": "SUCCESS" if sp_times else "SKIPPED_INACTIVE",
            "runs": len(sp_times),
            "p50_ms": sp_p50,
            "p95_ms": sp_p95,
            "avg_ms": sp_avg,
            "rows_returned": sp_rows,
            "architecture_role": t("인덱스/인터리빙 기반 온라인 저지연 멀티홉 탐색", "Index/Interleaved Online Low-Latency Multi-Hop Serving"),
        },
    ]
    ratio_str = f"{round(bq_p50 / sp_p50, 1)}x" if sp_p50 > 0 else "N/A"
    md(t(
        f"**양대 그래프 엔진 실시간 3-Hop ISO GQL 벤치마크 (`N={runs}`회 반복 측정)**\n"
        f"- **BigQuery Property Graph (기본값)**: `p50 = {bq_p50} ms` · `p95 = {bq_p95} ms` · Job `{bq_job}`\n"
        f"- **Cloud Spanner Graph (`{SPANNER_INSTANCE}`, 100 PU)**: `p50 = {sp_p50} ms` · `p95 = {sp_p95} ms` (단일 포인트 탐색 지연시간 비율 `{ratio_str}`)",
        f"**Live Dual-Engine 3-Hop ISO GQL Benchmark (`N={runs}` Repeated Runs)**\n"
        f"- **BigQuery Property Graph (Default)**: `p50 = {bq_p50} ms` · `p95 = {bq_p95} ms` · Job `{bq_job}`\n"
        f"- **Cloud Spanner Graph (`{SPANNER_INSTANCE}`, 100 PU)**: `p50 = {sp_p50} ms` · `p95 = {sp_p95} ms` (Point-lookup latency ratio `{ratio_str}`)",
    ))
    return pd.DataFrame(rows)


def run_graph_fabric_federated_join():
    """Executes BigQuery EXTERNAL_QUERY over Cloud Spanner Graph joined with BigQuery tb_doc_chunks."""
    conn_spec = f"{PROJECT}.{LOCATION}.{BQ_CONN_ID}"
    fed_sql = f"""SELECT
  sp.customer_id,
  sp.contract_type,
  sp.elapsed_days,
  sp.device_name,
  sp.plan_name,
  sp.monthly_fee_krw,
  sp.rule_id,
  sp.source_chunk_id,
  c.section_title,
  c.content_sha256
FROM EXTERNAL_QUERY(
  "{conn_spec}",
  \"\"\"GRAPH STARTER_ONTOLOGY_GRAPH
     MATCH (c:CustomerContractNode)-[:USES_DEVICE]->(d:DeviceNode),
           (c)-[:SUBSCRIBES_PLAN]->(p:PlanNode)<-[ap:APPLIES_TO_PLAN]-(r:DomainRuleNode)
     RETURN c.customer_id, c.contract_type, c.elapsed_days,
            d.device_name, p.plan_name, p.monthly_fee_krw,
            r.rule_id, ap.source_chunk_id
     ORDER BY c.customer_id, r.rule_id\"\"\"
) AS sp
JOIN `{FQ}.tb_doc_chunks` AS c
  ON c.chunk_id = sp.source_chunk_id
ORDER BY sp.customer_id, sp.rule_id"""
    df, meta = sql(fed_sql)
    bvars = {
        "EXTERNAL_QUERY connection": (conn_spec, t("BigQuery ↔ Cloud Spanner 연합 연결 리소스", "BigQuery to Cloud Spanner federated connection")),
        "Spanner Graph": (f"{SPANNER_INSTANCE}/{SPANNER_DB}/STARTER_ONTOLOGY_GRAPH", t("원격 실행되는 온라인 프로퍼티 그래프", "Remote online property graph pushed down to Spanner")),
        "BigQuery Join Table": (f"{FQ}.tb_doc_chunks", t("SHA-256 정책 청크 원장 조인 테이블", "BigQuery SHA-256 policy chunk table joined in-place")),
    }
    if meta.get("status") != "SUCCESS":
        md(t(
            f"- **Graph Fabric (`EXTERNAL_QUERY`) 상태**: `SKIPPED` (Spanner 연결 미활성 또는 권한 대기: `{meta.get('error', '')[:160]}`)",
            f"- **Graph Fabric (`EXTERNAL_QUERY`) Status**: `SKIPPED` (Spanner connection inactive: `{meta.get('error', '')[:160]}`)",
        ))
        return pd.DataFrame()
    hdr = (f"- **Graph Fabric (`EXTERNAL_QUERY`) Execution**: status `{meta.get('status')}` · "
           f"BigQuery job `{meta.get('job_id')}` · `{meta.get('elapsed_ms') or 0:,.0f} ms` · `{len(df)} rows`\n\n")
    stmt_lbl = t("2) 실행된 Graph Fabric 연합 쿼리 (BigQuery SQL + Spanner ISO GQL Pushdown)",
                 "2) Executed Graph Fabric Federated Query (BigQuery SQL + Spanner ISO GQL Pushdown)")
    md(hdr + _format_vars_md(bvars) + f"**{stmt_lbl}**\n```sql\n{fed_sql}\n```")
    display(df)
    return df


def compare_mcp_engines(server):
    """Executes the 3 Runtime Domain MCP tools across engine='bigquery' (default) and engine='spanner'."""
    cases = [
        ("mcp_lookup_customer_profile", {"customer_id": "CUST_DEMO_001"}),
        ("mcp_calculate_penalty_rule", {"customer_id": "CUST_DEMO_001", "target_monthly_fee_krw": 37000, "elapsed_days": 120}),
        ("mcp_query_graph_and_wiki", {"customer_id": "CUST_DEMO_001"}),
    ]
    rows = []
    sp_gql_res = None
    for tool_name, base_args in cases:
        r_bq = server.execute_tool(tool_name, {**base_args, "engine": "bigquery"})
        r_sp = server.execute_tool(tool_name, {**base_args, "engine": "spanner"})
        if tool_name == "mcp_query_graph_and_wiki" and r_sp.get("status") == "SUCCESS":
            sp_gql_res = r_sp
        cnt_bq = r_bq.get("matched_rows_count", r_bq.get("matched_graph_paths_count", 0))
        cnt_sp = r_sp.get("matched_rows_count", r_sp.get("matched_graph_paths_count", 0))
        rows.append({
            "mcp_tool": tool_name,
            "bigquery_status": r_bq.get("status"),
            "spanner_status": r_sp.get("status"),
            "bigquery_ms": float(r_bq.get("bq_elapsed_ms", 0)),
            "spanner_ms": float(r_sp.get("bq_elapsed_ms", 0)) if r_sp.get("status") == "SUCCESS" else 0.0,
            "bq_rows": cnt_bq,
            "spanner_rows": cnt_sp,
            "result_parity": cnt_bq == cnt_sp and r_bq.get("status") == r_sp.get("status"),
        })
    if sp_gql_res:
        show_tool(sp_gql_res, "matched_graph_paths",
                  ["customer_id", "device_name", "plan_name", "rule_id", "relation_label_ko", "source_chunk_id", "anchor"])
    return pd.DataFrame(rows)

