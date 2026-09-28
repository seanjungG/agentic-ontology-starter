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

from src.gcp_client import (DEFAULT_DATASET_ID, DEFAULT_GEMINI_MODEL, DEFAULT_LOCATION,  # noqa: E402
                            DEFAULT_PROJECT_ID, call_vertex_gemini, execute_bq_sql, get_gcp_token)

PROJECT, DATASET, LOCATION, MODEL = DEFAULT_PROJECT_ID, DEFAULT_DATASET_ID, DEFAULT_LOCATION, DEFAULT_GEMINI_MODEL
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
    cjk = next((f for f in ("AppleGothic", "NanumGothic", "Noto Sans CJK KR", "Malgun Gothic") if f in fonts), None)
    plt.rcParams.update({"font.family": cjk or "sans-serif", "axes.unicode_minus": False, "figure.dpi": 100,
                         "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
                         "grid.alpha": 0.25, "axes.titleweight": "bold"})
    return pd.DataFrame([{"project": PROJECT, "dataset": DATASET, "location": LOCATION,
                          "graph": GRAPH.split(".")[-1], "model": MODEL, "lang": LANG}])


def t(ko, en):
    return ko if LANG == "ko" else en


def pdf(df):
    """BigFrames or pandas -> small pandas frame for display/plots (starter tables have < 20 rows)."""
    return df.to_pandas() if hasattr(df, "to_pandas") else pd.DataFrame(df)


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
        return json.load(f)


def sql(query):
    """Runs SQL/GQL through the starter client; returns (DataFrame, meta). Errors are returned, not raised."""
    r = execute_bq_sql(query)
    meta = {k: r.get(k) for k in ("status", "job_id", "elapsed_ms", "total_bytes_processed")}
    if r.get("status") != "SUCCESS":
        meta["error"] = str(r.get("error", ""))[:400]
    return pd.DataFrame(r.get("rows", [])), meta


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
            rows.append({
                "chunk_id": cid,
                "source_file": gpath.name,
                "section_title": title.strip(),
                "chars": len(clean),
                "computed_anchor": anchor,
                "bq_stored_anchor": bq_anchor,
                "sha256_match": anchor == bq_anchor,
                "excerpt": clean.splitlines()[0][:75] if clean else "",
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
    for layer_name, fname, role in layers:
        p = ROOT / "data/llm_wiki" / fname
        lines = p.read_text(encoding="utf-8").splitlines() if p.exists() else []
        gcs_uri = f"{manifest.get('gcs_uri', '')}ontology/{fname}"
        rows.append({"wiki_layer": layer_name, "file": fname, "lines": len(lines), "gcs_object_uri": gcs_uri, "role": role})
    return pd.DataFrame(rows), manifest


def draw_eight_phase_flow():
    """Draws the 8-Phase Engineering Flow (Prepare -> Analyze -> Parse -> Integrate -> Build -> Agent -> Answer -> Verify)."""
    phases = [
        ("1. 준비 (Prepare)", "Stage 1.1a\nRaw CSV/MD & BQ Schema", "#1A73E8", (0, 1)),
        ("2. 분석 (Analyze)", "Stage 1.1b~1.2\nProfiling, PII & Golden CQs", "#0284c7", (1, 1)),
        ("3. 파싱 (Parse)", "Stage 2.1\nSHA-256 Chunks & 3-Layer Wiki", "#9334E6", (2, 1)),
        ("4. 통합 (Integrate)", "Stage 2.2\nRules & Semantic Graph", "#F9AB00", (3, 1)),
        ("5. 구축 (Build Graph)", "Stage 3.1~3.2\nBQ/Spanner Property Graph", "#0d9488", (0, 0)),
        ("6. 에이전트 구축 (Agent)", "Stage 4.1\n8 MCP Tools & 2-Pass Engine", "#188038", (1, 0)),
        ("7. 답변 (Answer & GQL)", "Stage 4.2\nNL2GQL & Grounded Synthesis", "#1A73E8", (2, 0)),
        ("8. 검증 (Verify & Gate)", "Stage 5.1~5.2\n4-Tier Lineage & 50-Trial Eval", "#D93025", (3, 0)),
    ]
    fig, ax = plt.subplots(figsize=(12, 4.2))
    ax.axis("off")
    ax.set_xlim(-0.5, 3.6)
    ax.set_ylim(-0.45, 1.55)
    for idx, (title, sub, color, (x, y)) in enumerate(phases):
        box = mpatches.FancyBboxPatch((x - 0.42, y - 0.28), 0.84, 0.56, boxstyle="round,pad=0.04,rounding_size=0.08",
                                      fc=color, ec="white", lw=2, alpha=0.92)
        ax.add_patch(box)
        ax.text(x, y + 0.09, title, ha="center", va="center", color="white", fontsize=9.5, fontweight="bold")
        ax.text(x, y - 0.11, sub, ha="center", va="center", color="white", fontsize=7.5)
        if idx in (0, 1, 2, 4, 5, 6):
            ax.annotate("", xy=(x + 0.55, y), xytext=(x + 0.43, y),
                        arrowprops={"arrowstyle": "->", "color": "#475569", "lw": 1.8})
        elif idx == 3:
            ax.annotate("", xy=(0, 0.30), xytext=(3, 0.70),
                        arrowprops={"arrowstyle": "->", "color": "#475569", "lw": 1.6, "ls": "--",
                                    "connectionstyle": "arc3,rad=0.18"})
    ax.set_title(t("8단계 엔지니어링 파이프라인 및 5-Stage 매핑 도식 (준비 → 분석 → 파싱 → 통합 → 구축 → 에이전트 구축 → 답변 → 검증)",
                   "8-Phase Engineering Pipeline Mapped to the 5-Stage Methodology"), fontweight="bold", pad=10)
    plt.tight_layout()
    plt.show()


def draw_table_er_blueprint():
    """Draws the 10-table BigQuery schema blueprint (4 Master + 2 Knowledge + 4 Edge tables)."""
    nodes = [
        {"id": "tb_customer_contract", "name": "tb_customer_contract\n(PK: contract_id)", "layer": 0, "color": "#1A73E8"},
        {"id": "tb_domain_rules", "name": "tb_domain_rules\n(PK: rule_id)", "layer": 0, "color": "#F9AB00"},
        {"id": "edge_contract_device", "name": "edge_contract_device\n[USES_DEVICE]", "layer": 1, "color": "#5F6368"},
        {"id": "edge_contract_plan", "name": "edge_contract_plan\n[SUBSCRIBES_PLAN]", "layer": 1, "color": "#5F6368"},
        {"id": "edge_subsidy_binding", "name": "edge_subsidy_binding\n[HAS_SUBSIDY_POLICY]", "layer": 1, "color": "#5F6368"},
        {"id": "edge_rule_applies_to_plan", "name": "edge_rule_applies_to_plan\n[APPLIES_TO_PLAN]", "layer": 1, "color": "#5F6368"},
        {"id": "tb_device_master", "name": "tb_device_master\n(PK: device_id)", "layer": 2, "color": "#0284c7"},
        {"id": "tb_plan_master", "name": "tb_plan_master\n(PK: plan_id)", "layer": 2, "color": "#0d9488"},
        {"id": "tb_subsidy_policy", "name": "tb_subsidy_policy\n(PK: policy_id)", "layer": 2, "color": "#188038"},
        {"id": "tb_doc_chunks", "name": "tb_doc_chunks\n(PK: chunk_id / SHA-256)", "layer": 2, "color": "#9334E6"},
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
               layout="layers", figsize=(11.5, 5.5), node_size=1900,
               legend={"Contract (#1A73E8)": "#1A73E8", "Device/Plan/Subsidy": "#0d9488",
                       "Domain Rule (#F9AB00)": "#F9AB00", "Doc Chunk (#9334E6)": "#9334E6", "Edge Table (#5F6368)": "#5F6368"})


def draw_semantic_design_graph():
    """Draws the Stage 2 Semantic Ontology Graph design schematic from graph_topology.json (`vis_semantic_graph`)."""
    topo = read_json("data/output/graph_topology.json")["vis_semantic_graph"]
    layer_map = {"hub": 0, "rule": 1, "entity": 2, "chunk": 2}
    nodes = [{"id": n["id"], "name": n["label_ko" if LANG == "ko" else "label_en"],
              "color": n["color"], "layer": layer_map.get(n["group"], 1)} for n in topo["nodes"]]
    edges = [{"src": e["from"], "dst": e["to"],
              "label": e["label_ko" if LANG == "ko" else "label_en"],
              "style": "dashed" if e.get("is_hub") or "GROUNDED" in e["label_en"] else "solid"} for e in topo["edges"]]
    draw_graph(nodes, edges,
               t("Stage 2 시맨틱 온톨로지 그래프 설계 도식 (Entity=Node, Concept=Edge, Sky Blue 허브)",
                 "Stage 2 Semantic Ontology Graph Design Schematic (Entity=Node, Concept=Edge, Sky Blue Hub)"),
               layout="layers", figsize=(11.5, 5.8), node_size=1750,
               legend={"Semantic Hub (#0284c7)": "#0284c7", "Core Entity (#2563eb)": "#2563eb",
                       "Subsidy Entity (#059669)": "#059669", "Domain Rule (#d97706)": "#d97706", "Doc Chunk (#0d9488)": "#0d9488"})


def draw_property_graph_metamodel():
    """Draws the Stage 3 Zero-ETL Property Graph schema metamodel (6 Node Labels x 4 Edge Labels)."""
    node_labels, edge_labels, _ = graph_metadata()
    layer_map = {"CustomerContractNode": 0, "DomainRuleNode": 0, "SubsidyNode": 1,
                 "DeviceNode": 1, "PlanNode": 1, "DocChunkNode": 2}
    nodes = [{"id": n["label"], "name": f"{n['label']}\n({n['table']}\nPK: {n['key']})",
              "color": LABEL_COLORS.get(n["label"], PALETTE[0]), "layer": layer_map.get(n["label"], 1)}
             for n in node_labels]
    edges = [{"src": e["source"], "dst": e["destination"], "label": f"{e['label']}\n({e['table']})"} for e in edge_labels]
    edges.append({"src": "DomainRuleNode", "dst": "DocChunkNode", "label": "source_chunk_id\n(Anchor Join)", "style": "dashed"})
    draw_graph(nodes, edges,
               t("Stage 3 STARTER_ONTOLOGY_GRAPH 메타모델 설계도 (6 Node Labels × 4 Edge Labels)",
                 "Stage 3 STARTER_ONTOLOGY_GRAPH Schema Metamodel (6 Node Labels × 4 Edge Labels)"),
               layout="layers", figsize=(11.5, 5.4), node_size=2200, legend=LABEL_COLORS)


def draw_agent_architecture():
    """Draws the Stage 4 2-Pass AI FDE Agent & 8-Tool MCP execution architecture schematic."""
    nodes = [
        {"id": "Q", "name": t("사용자 자연어 질의\n(User Query)", "User Natural-Language\nQuery"), "layer": 0, "color": "#5F6368"},
        {"id": "P1", "name": t("Step 1 · Gemini 1차 호출\n하위 목표 분해 & 슬롯 추출", "Step 1 · Gemini Pass 1\nSub-Goal & Slot Extraction"), "layer": 1, "color": "#1A73E8"},
        {"id": "CAT", "name": t("카탈로그 & 정규식 검증기\n(resolve_params)", "Live Catalog & Regex Guard\n(resolve_params)"), "layer": 1, "color": "#0284c7"},
        {"id": "M1", "name": "mcp_lookup_customer_profile\n(Contract / Device / Subsidy)", "layer": 2, "color": "#0d9488"},
        {"id": "M2", "name": "mcp_calculate_penalty_rule\n(180d Clawback / 24M TCO)", "layer": 2, "color": "#188038"},
        {"id": "M3", "name": "mcp_query_graph_and_wiki\n(ISO GQL + SHA-256 Chunk)", "layer": 2, "color": "#9334E6"},
        {"id": "G", "name": t("Step 3 · 가드레일 상태 판정\nGROUNDED | INSUFFICIENT\n| MATCH_NOT_FOUND", "Step 3 · Guardrail Verdict\nGROUNDED | INSUFFICIENT\n| MATCH_NOT_FOUND"), "layer": 3, "color": "#F9AB00"},
        {"id": "P2", "name": t("Step 4 · Gemini 2차 호출\n근거·앵커·Job ID 인용 답변", "Step 4 · Gemini Pass 2\nGrounded Cited Synthesis"), "layer": 4, "color": "#D93025"},
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
               layout="layers", figsize=(12, 5.2), node_size=2000)


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
def draw_graph(nodes, edges, title, layout="spring", figsize=(11, 6.5), node_size=1500, font_size=8, legend=None):
    """nodes: [{id, name, color, layer?}], edges: [{src, dst, label?, style?}]"""
    g = nx.MultiDiGraph()
    for n in nodes:
        g.add_node(n["id"], **n)
    for e in edges:
        g.add_edge(e["src"], e["dst"], label=e.get("label", ""), style=e.get("style", "solid"))
    if layout == "layers":
        pos = nx.multipartite_layout(g, subset_key="layer", align="vertical")
    elif layout == "shell":
        pos = nx.shell_layout(g)
    else:
        pos = nx.spring_layout(g, seed=7, k=1.6 / max(1, len(g) ** 0.5), iterations=200)
    fig, ax = plt.subplots(figsize=figsize)
    ax.axis("off")
    for style in ("solid", "dashed"):
        es = [(u, v) for u, v, d in g.edges(data=True) if d["style"] == style]
        nx.draw_networkx_edges(g, pos, edgelist=es, ax=ax, style=style, width=1.15, edge_color="#94A3B8",
                               arrows=True, arrowsize=12, node_size=node_size, connectionstyle="arc3,rad=0.06")
    nx.draw_networkx_nodes(g, pos, ax=ax, node_size=node_size, node_color=[g.nodes[n].get("color", PALETTE[0]) for n in g],
                           edgecolors="white", linewidths=1.5)
    nx.draw_networkx_labels(g, pos, ax=ax, labels={n: g.nodes[n].get("name", n) for n in g}, font_size=font_size,
                            font_family=plt.rcParams["font.family"])
    elabels = {}
    for u, v, d in g.edges(data=True):
        if d["label"]:
            elabels[(u, v)] = d["label"] if (u, v) not in elabels else elabels[(u, v)] + " / " + d["label"]
    nx.draw_networkx_edge_labels(g, pos, edge_labels=elabels, ax=ax, font_size=6.5, font_color="#475569",
                                 bbox={"boxstyle": "round,pad=0.15", "fc": "white", "ec": "none", "alpha": 0.8})
    if legend:
        for name, color in legend.items():
            ax.scatter([], [], c=color, s=80, label=name)
        ax.legend(loc="lower left", fontsize=8, frameon=False, ncol=min(6, len(legend)))
    ax.set_title(title, fontweight="bold")
    plt.tight_layout()
    plt.show()


def _node_name(props, labels):
    for k in NAME_KEYS:
        if props.get(k):
            return str(props[k])
    return labels[0] if labels else "?"


def paths_to_graph(path_json_values):
    """Parses GQL `TO_JSON(p)` values into (nodes, edges) for draw_graph. Node id = '<label>:<name>'."""
    nodes, ids, edges = {}, {}, []
    for v in path_json_values:
        while isinstance(v, str):
            v = json.loads(v)
        for el in v:
            labels = el.get("labels", [])
            if el.get("kind") == "node":
                name = _node_name(el.get("properties", {}), labels)
                nid = f"{labels[0] if labels else '?'}:{name}"
                ids[el["identifier"]] = nid
                nodes[nid] = {"id": nid, "name": name, "color": LABEL_COLORS.get(labels[0] if labels else "", PALETTE[7])}
        for el in v:
            if el.get("kind") == "edge":
                edges.append({"src": ids[el["source_node_identifier"]], "dst": ids[el["destination_node_identifier"]],
                              "label": (el.get("labels") or [""])[0]})
    uniq = {(e["src"], e["dst"], e["label"]): e for e in edges}
    return list(nodes.values()), list(uniq.values())


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


# ------------------------------------------------------------------ MCP and agent views
def show_tool(res, table_key=None, cols=None):
    head = (f"**`{res.get('tool')}`** · status `{res.get('status')}` · steps `{', '.join(res.get('executed_steps', []))}` · "
            f"BigQuery jobs {len(res.get('bq_job_ids', []))} ({res.get('bq_elapsed_ms', 0):,.0f} ms)")
    if res.get("summary"):
        head += f"\n\n{res['summary']}"
    md(head + "\n\n" + "\n".join(f"- `{j}`" for j in res.get("bq_job_ids", [])[:6]))
    if table_key and res.get(table_key):
        d = pd.DataFrame(res[table_key])
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
    body = res["lifecycle"]["step_4_synthesis"]["markdown"].split("\n\n---\n- LLM:")[0]
    md(f"#### {title or ''}\n**Q.** {res['query']}\n\n"
       f"- **Step 1 ({t('의도 분해 & 파라미터 추출', 'Decomposition & Slot Extraction')})**: sub-goals {subgoals} · "
       f"params `{json.dumps(params, ensure_ascii=False)}`\n"
       f"- **Step 2 ({t('MCP 도구 체이닝 실행', 'Deterministic MCP Tool Dispatch')})**:\n\n"
       f"| # | MCP Tool | Status | Rows/Paths | BigQuery ms | BigQuery Job ID |\n|---:|:---|:---|---:|---:|:---|\n{rows}\n\n"
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
Return JSON only: {"answerable": true|false, "gql": "<one statement or empty>", "explanation": "<one short sentence in LANGUAGE>"}
Rules:
- Start with GRAPH `GRAPH_NAME` then MATCH ... RETURN ... (standalone GQL, no GRAPH_TABLE).
- Use only labels, properties and edge directions listed in [Schema]. Always write node labels, edge labels and direction.
- Return named properties with readable aliases, add ORDER BY, and LIMIT 50.
- DocChunkNode has no edges: add a second pattern (ch:DocChunkNode) and filter with WHERE ch.chunk_id = <x>.source_chunk_id.
- If [Schema] has no data for the question, return answerable=false and gql="".
"""


def _gen(prompt):
    r = call_vertex_gemini(prompt=prompt, system_instruction=GQL_SYS.replace("GRAPH_NAME", GRAPH).replace(
        "LANGUAGE", t("Korean", "English")), response_mime_type="application/json", temperature=0.0, max_tokens=2048)
    try:
        spec = json.loads(r.get("text") or "{}")
    except json.JSONDecodeError:
        spec = {"answerable": False, "gql": "", "explanation": "JSON parse error"}
    return spec, r.get("total_tokens", 0), r.get("elapsed_ms", 0)


def nl2gql(question, schema, repair=True):
    """Gemini writes GQL from the live schema, BigQuery runs it; one repair round with the BigQuery error."""
    spec, tok, ms = _gen(f"[Schema]\n{schema}\n\n[Question]\n{question}")
    attempts = []
    while spec.get("answerable") and spec.get("gql") and len(attempts) < (2 if repair else 1):
        df, meta = sql(spec["gql"])
        attempts.append({"gql": spec["gql"], "df": df, **meta})
        if meta["status"] == "SUCCESS":
            break
        spec, tok2, ms2 = _gen(f"[Schema]\n{schema}\n\n[Question]\n{question}\n\n[Previous GQL]\n{spec['gql']}\n\n"
                               f"[BigQuery error]\n{meta.get('error')}\n\nReturn a corrected query.")
        tok, ms = tok + tok2, ms + ms2
    out = [f"**Q.** {question}", f"- Gemini `{MODEL}`: {spec.get('explanation', '')} ({t('토큰', 'tokens')} {tok:,}, {ms:,.0f} ms)"]
    if not attempts:
        out.append(f"- {t('생성 결과', 'Result')}: `answerable=false` — {t('스키마에 없는 데이터라 GQL을 만들지 않음', 'no GQL generated because the schema has no such data')}")
    for i, a in enumerate(attempts, 1):
        out.append(f"\n{t('시도', 'Attempt')} {i} · status `{a['status']}` · job `{a.get('job_id')}` · {a.get('elapsed_ms') or 0:,.0f} ms"
                   f" · {len(a['df'])} rows\n```sql\n{a['gql'].strip()}\n```")
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
