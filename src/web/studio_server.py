# Copyright (c) 2026 Sean Jung (seanjung@google.com). All Rights Reserved.
# Non-Commercial Use Only: Methodology & Docs under CC BY-NC-ND 4.0; Source Code under PolyForm Noncommercial License 1.0.0.
# Commercial use, paid consulting/SI/PoC delivery, or production deployment requires prior written permission from seanjung@google.com.

# -*- coding: utf-8 -*-
"""
Agentic Ontology Studio Server (Starter Pack v2.0)
- Light Enterprise Design System (`05_DESIGN.md` & `methodology/ko/METHODOLOGY_KO.md`):
  * Light Enterprise Theme (`--apple-bg-primary: #ffffff`, `--apple-bg-secondary: #f5f5f7`)
  * 44px Global Navigation Bar with Official Google 'G' Vector SVG + KOR/ENG Pill Switch
  * 52px Local Sub-navigation Bar (`.ac-localnav` + `.compact-pill-bar`) with 6 Compressed Stage Tabs:
      0. Overview | Stage 1. Asset | Stage 2. Wiki & Semantic Graph | Stage 3. Property Graph | Stage 4. Agent & MCP | Stage 5. Lineage & Eval
  * Interactive vis-network Graphs (`Entity=Node`, `Concept=Edge`, Sky Blue/Teal Hubs, 1.15px Edges, Korean Business Labels)
  * 3-Track Data Maturity (`lite: 1→2→4`, `standard: 1→2→3→4`, `full: 1→5`) & Dual Graph Engine Adapter (`BigQuery Property Graph` <-> `Cloud Spanner Graph`)
  * 8 Core Modular MCPs (5 Stage Pipeline MCPs with selectable `steps` + 3 Runtime Execution MCPs)
"""
import os, sys, json, csv, glob, hashlib, http.server, socketserver
from urllib.parse import urlparse, parse_qs

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, BASE_DIR)

from src.lineage.lineage_engine import LineageEngine
from src.project_context import cached, get_engine, get_project, list_projects, resolve_track
from src.web.project_workbench import (
    DEFAULT_GEMINI_MODEL,
    SUPPORTED_GEMINI_MODELS,
    approve_workbench_step,
    create_new_project_workspace,
    execute_custom_project_agent_query,
    get_workbench_state,
    recommend_gcp_resources,
    reconfigure_project_track,
    run_workbench_step,
    seed_sample_domain_files,
    upload_project_files,
)

PORT = int(os.environ.get("PORT", 8080))

PORTAL_PROFILE_PATH = "config/portal_profile.json"
STARTER_CONFIG_PATH = "config/starter_config.json"
EVAL_RUBRIC_PATH = "config/eval_rubric.json"
LINEAGE_SPEC_PATH = "config/lineage_spec.json"
CQ_REPORT_PATH = "data/output/cq_benchmark_report.json"
BOUNDARY_REPORT_PATH = "data/output/boundary_benchmark_results.json"


def load_text_file(rel_path, default="", root=BASE_DIR):
    p = os.path.join(root, rel_path)
    if os.path.exists(p):
        with open(p, "r", encoding="utf-8") as f:
            return f.read()
    return default


def load_json_file(rel_path, default=None, root=BASE_DIR):
    p = os.path.join(root, rel_path)
    if os.path.exists(p):
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    return default if default is not None else {}


def load_csv_table(path):
    with open(path, "r", encoding="utf-8") as f:
        reader = list(csv.reader(f))
        if not reader:
            return {"headers": [], "rows": []}
        return {"headers": reader[0], "rows": reader[1:]}


def get_lineage(project):
    def build(p):
        eng = get_engine(p)
        srv = eng.server
        return LineageEngine(os.path.join(p["root"], LINEAGE_SPEC_PATH), {
            "project_id": srv.project_id, "fq": srv.fq, "dataset_id": srv.fq.split(".", 1)[1],
            "bucket": srv.gcs_bucket, "model": eng.model_name,
            "spanner_instance": srv.spanner_instance_id, "spanner_database": srv.spanner_database_id})
    return cached(project, "lineage", build)


def build_eval_summary(root=BASE_DIR):
    profile = load_json_file(PORTAL_PROFILE_PATH, {}, root)
    ev_cfg = profile.get("evaluation", {})
    rubric = load_json_file(EVAL_RUBRIC_PATH, {}, root)

    cq_exists = os.path.exists(os.path.join(root, CQ_REPORT_PATH))
    cq_raw = load_json_file(CQ_REPORT_PATH, {}, root) if cq_exists else {}
    cq_items = cq_raw.get("evaluation_details") or cq_raw.get("test_results") or []
    cq_total = cq_raw.get("total_cqs", len(cq_items)) if cq_exists else 0
    cq_passed = cq_raw.get(
        "passed",
        sum(1 for x in cq_items if x.get("status") == "PASSED" or x.get("verification_status") == "EXACT_MATCH"),
    ) if cq_exists else 0
    cq_rate = round((cq_passed / cq_total) * 100, 1) if cq_total else None
    # F8: show a score only for a recorded run on the current inputs (data/output/input_manifest.json)
    man_path, man_sha = os.path.join(root, "data/output/input_manifest.json"), None
    if os.path.exists(man_path):
        with open(man_path, "rb") as f:
            man_sha = hashlib.sha256(f.read()).hexdigest()
    if not cq_exists or not cq_total:
        cq_state, cq_label = "PENDING", "미측정"
    elif not cq_raw.get("run_id") or not all(x.get("executed_at") for x in cq_items):
        cq_state, cq_label = "UNMEASURED", "미측정 (실행 기록 없음)"
    elif cq_raw.get("input_manifest_sha256") != man_sha:
        cq_state, cq_label = "STALE", "입력 변경 후 재평가 필요"
    else:
        cq_state = "MEASURED"
        cq_label = f"{cq_passed} / {cq_total} (" + ("합성 데이터 기준 " if cq_raw.get("synthetic_basis") else "") + f"{cq_rate}%)"
    if cq_state != "MEASURED":
        cq_passed = cq_rate = None

    bd_exists = os.path.exists(os.path.join(root, BOUNDARY_REPORT_PATH))
    bd_raw = load_json_file(BOUNDARY_REPORT_PATH, {}, root) if bd_exists else {}
    bd_cases = bd_raw.get("cases", []) if bd_exists else []

    file_state = {
        "cq_report": cq_exists,
        "boundary": bd_exists,
        "rubric": os.path.exists(os.path.join(root, EVAL_RUBRIC_PATH)),
    }
    sources = []
    for s in ev_cfg.get("sources", []):
        sid = s.get("id", "")
        sources.append({**s, "exists": bool(file_state.get(sid, False))})

    rounds = []
    for r in ev_cfg.get("rounds", []):
        src = r.get("status_source", "")
        measured = bool(file_state.get(src, False))
        rounds.append({**r, "status": "MEASURED" if measured else "PENDING"})

    return {
        "intro": ev_cfg.get("intro", ""),
        "sources": sources,
        "design": ev_cfg.get("design", {}),
        "rubric": rubric,
        "golden": {
            "status": cq_state,
            "score_label": cq_label,
            "unconfirmed": cq_raw.get("unconfirmed_cqs"),
            "run_id": cq_raw.get("run_id"),
            "total": cq_total,
            "passed": cq_passed,
            "pass_rate": cq_rate,
            "evaluated_at": cq_raw.get("evaluated_at"),
            "model": cq_raw.get("model"),
            "rows": [
                {
                    "cq_id": x.get("cq_id", ""),
                    "category": x.get("category") or ((x.get("dispatched_tools") or ["general"])[0]),
                    "prompt": x.get("query") or x.get("prompt", ""),
                    "expected_value": x.get("expected_value") or ", ".join(x.get("dispatched_tools", [])) or "Exact Match",
                    "actual_value": x.get("actual_value") or x.get("status", "-"),
                    "legal_anchor": x.get("grounded_chunk") or x.get("legal_anchor", "-"),
                    "verification_status": x.get("verification_status") or x.get("status", "UNKNOWN"),
                    "passed": x.get("status") == "PASSED",
                }
                for x in cq_items
            ],
        },
        "boundary": {
            "status": "MEASURED" if bd_exists and len(bd_cases) > 0 else "PENDING",
            "case_count": len(bd_cases),
            "trials_per_case": bd_raw.get("trials_per_case"),
            "evaluated_at": bd_raw.get("evaluated_at"),
            "model": bd_raw.get("model"),
            "avg_success_rate": bd_raw.get("avg_success_rate") if bd_exists else None,
            "avg_consistency_rate": bd_raw.get("avg_consistency_rate") if bd_exists else None,
            "avg_intent_stability": bd_raw.get("avg_intent_stability") if bd_exists else None,
            "cases": bd_cases,
        },
        "taxonomy": ev_cfg.get("root_cause_taxonomy", []),
        "rounds": rounds,
    }


HTML_PAGE = r"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Agentic Ontology Studio — Starter Pack v2.0</title>
<link rel="stylesheet" as="style" crossorigin href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css" />
<script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
<style>
  :root {
    --apple-bg-primary: #ffffff;
    --apple-bg-secondary: #f5f5f7;
    --apple-bg-tertiary: #e8e8ed;
    --apple-bg-glass: rgba(255, 255, 255, 0.85);
    --apple-bg-glass-heavy: rgba(255, 255, 255, 0.95);
    --apple-text-primary: #1d1d1f;
    --apple-text-secondary: #6e6e73;
    --apple-text-tertiary: #86868b;
    --apple-blue: #0071e3;
    --apple-blue-hover: #0077ED;
    --apple-purple: #9333ea;
    --apple-indigo: #4f46e5;
    --apple-teal: #0d9488;
    --apple-emerald: #059669;
    --apple-amber: #d97706;
    --apple-red: #dc2626;
    --apple-border-subtle: rgba(0, 0, 0, 0.08);
    --apple-border-focus: rgba(0, 113, 227, 0.4);
    --font-sans: 'Pretendard', -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Helvetica Neue", Arial, sans-serif;
    --font-mono: "SF Mono", "JetBrains Mono", Menlo, Monaco, Consolas, monospace;
    --ease-spring: cubic-bezier(0.22, 1, 0.36, 1);
    --ease-smooth: cubic-bezier(0.4, 0, 0.2, 1);
  }

  * { box-sizing: border-box; margin: 0; padding: 0; -webkit-font-smoothing: antialiased; }
  body {
    font-family: var(--font-sans);
    background-color: var(--apple-bg-secondary);
    color: var(--apple-text-primary);
    height: 100vh;
    width: 100vw;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    letter-spacing: -0.011em;
  }

  /* 1. Global Navigation Bar (44px, Apple/Google Light Enterprise) */
  .globalnav {
    height: 44px;
    width: 100%;
    background: var(--apple-bg-glass);
    backdrop-filter: saturate(180%) blur(20px);
    -webkit-backdrop-filter: saturate(180%) blur(20px);
    border-bottom: 1px solid var(--apple-border-subtle);
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0 24px;
    flex-shrink: 0;
    z-index: 9999;
  }
  .globalnav-content {
    width: 100%;
    max-width: 1680px;
    display: flex;
    align-items: center;
    justify-content: space-between;
  }
  .globalnav-left {
    display: flex;
    align-items: center;
    gap: 12px;
  }
  .globalnav-logo {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 14px;
    font-weight: 700;
    color: var(--apple-text-primary);
    text-decoration: none;
    letter-spacing: -0.015em;
  }
  .globalnav-logo svg { width: 20px; height: 20px; flex-shrink: 0; }
  .hdr-meta-badge {
    font-size: 11px;
    font-weight: 600;
    padding: 3px 9px;
    border-radius: 999px;
    background: #f1f5f9;
    color: #334155;
    border: 1px solid #cbd5e1;
  }
  .hdr-meta-badge.teal { background: #f0fdfa; color: #0f766e; border-color: #99f6e4; }
  .hdr-meta-badge.indigo { background: #eef2ff; color: #4338ca; border-color: #c7d2fe; }
  .hdr-right-controls {
    display: flex;
    align-items: center;
    gap: 10px;
  }
  .hdr-pill-switch {
    display: inline-flex;
    background: var(--apple-bg-tertiary);
    padding: 2px;
    border-radius: 980px;
    border: 1px solid var(--apple-border-subtle);
  }
  .hdr-pill-switch button {
    border: none;
    background: transparent;
    padding: 3px 10px;
    border-radius: 980px;
    font-size: 11px;
    font-weight: 600;
    color: var(--apple-text-secondary);
    cursor: pointer;
    transition: all 0.2s var(--ease-spring);
    font-family: var(--font-sans);
  }
  .hdr-pill-switch button.active {
    background: var(--apple-bg-primary);
    color: var(--apple-text-primary);
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.12);
  }
  .hdr-pill-switch.hdr-lang-switch button.active {
    background: var(--apple-blue);
    color: #ffffff;
  }

  /* 2. Local Navigation Ribbon (52px, .ac-localnav + .compact-pill-bar) */
  .ac-localnav {
    height: 52px;
    width: 100%;
    background: rgba(255, 255, 255, 0.82);
    backdrop-filter: saturate(180%) blur(20px);
    -webkit-backdrop-filter: saturate(180%) blur(20px);
    border-bottom: 1px solid var(--apple-border-subtle);
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0 24px;
    flex-shrink: 0;
    z-index: 9990;
  }
  .ac-localnav-content {
    width: 100%;
    max-width: 1680px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
  }
  .compact-pill-bar {
    display: flex;
    align-items: center;
    gap: 4px;
    background: rgba(0, 0, 0, 0.04);
    padding: 3px 4px;
    border-radius: 9999px;
    overflow-x: auto;
    scrollbar-width: none;
  }
  .compact-pill-bar::-webkit-scrollbar { display: none; }
  .view-mode-pill {
    appearance: none;
    border: 1px solid transparent;
    background: transparent;
    color: #4b5563;
    font-family: var(--font-sans);
    font-size: 12.5px;
    font-weight: 500;
    line-height: 1.2;
    padding: 6px 14px;
    border-radius: 9999px;
    cursor: pointer;
    white-space: nowrap;
    transition: all 0.16s ease;
  }
  .view-mode-pill:hover {
    color: #111827;
    background: rgba(255, 255, 255, 0.6);
  }
  .view-mode-pill.active {
    background: #ffffff;
    color: #111827;
    font-weight: 700;
    border-color: rgba(0, 0, 0, 0.12);
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
  }
  .subnav-action-btn {
    padding: 6px 12px;
    border-radius: 980px;
    font-size: 11.5px;
    font-weight: 600;
    border: 1px solid #cbd5e1;
    background: #ffffff;
    color: #1e293b;
    cursor: pointer;
    transition: all 0.15s ease;
    white-space: nowrap;
  }
  .subnav-action-btn:hover {
    border-color: var(--apple-blue);
    color: var(--apple-blue);
    background: #f8fafc;
  }

  /* 3. Main App Container & Views */
  .studio-container {
    flex: 1;
    width: 100%;
    max-width: 1680px;
    margin: 0 auto;
    padding: 16px 24px;
    display: flex;
    flex-direction: column;
    gap: 14px;
    overflow: hidden;
    min-height: 0;
  }
  .tab-panel {
    display: none;
    flex: 1;
    min-height: 0;
    overflow: hidden;
  }
  .tab-panel.active {
    display: flex;
    flex-direction: column;
  }

  /* 4. Overview Styles (100% Parity with governanceStudio.py) */
  .ov-scroll-wrap {
    flex: 1;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 18px;
    padding-right: 4px;
  }
  .ov-card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 14px;
    padding: 20px 24px;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
  }
  .ov-hero-card {
    border-left: 4px solid var(--apple-blue);
    background: linear-gradient(135deg, rgba(0, 113, 227, 0.06), rgba(56, 189, 248, 0.02));
  }
  .ov-card-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    margin-bottom: 8px;
    flex-wrap: wrap;
  }
  .ov-eyebrow {
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.04em;
    padding: 4px 10px;
    border-radius: 999px;
    background: rgba(0, 113, 227, 0.1);
    color: var(--apple-blue);
  }
  .ov-eyebrow.teal { background: #ccfbf1; color: #0f766e; }
  .ov-eyebrow.indigo { background: #e0e7ff; color: #4338ca; }
  .ov-eyebrow.purple { background: #f3e8ff; color: #6d28d9; }
  .ov-h2 {
    font-size: 19px;
    font-weight: 800;
    color: var(--apple-text-primary);
    letter-spacing: -0.02em;
    margin: 2px 0 8px 0;
  }
  .ov-lead {
    font-size: 13.5px;
    color: var(--apple-text-secondary);
    line-height: 1.65;
    margin: 0 0 14px 0;
  }
  .ov-config-strip {
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 12px;
    margin-top: 12px;
    padding: 12px 16px;
    background: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 10px;
  }
  .ov-flow-board {
    display: grid;
    grid-template-columns: repeat(5, minmax(210px, 1fr));
    gap: 12px;
    align-items: stretch;
  }
  .ov-stage-col {
    background: #f8fafc;
    border: 1px solid #cbd5e1;
    border-top-width: 3px;
    border-radius: 12px;
    padding: 14px;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }
  .ov-stage-head-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 6px;
  }
  .ov-stage-chip {
    display: inline-block;
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 0.05em;
    padding: 3px 9px;
    border-radius: 999px;
    background: #e2e8f0;
    color: #0f172a;
  }
  .ov-stage-mcp-btn {
    padding: 3px 8px;
    border-radius: 6px;
    font-size: 10.5px;
    font-weight: 700;
    border: 1px solid #cbd5e1;
    background: #ffffff;
    color: var(--apple-blue);
    cursor: pointer;
    transition: all 0.15s ease;
  }
  .ov-stage-mcp-btn:hover {
    background: var(--apple-blue);
    color: #ffffff;
    border-color: var(--apple-blue);
  }
  .ov-stage-name {
    font-size: 14.5px;
    font-weight: 800;
    color: var(--apple-text-primary);
    line-height: 1.35;
    padding-bottom: 8px;
    border-bottom: 1px dashed rgba(0, 0, 0, 0.12);
  }
  .ov-step-box {
    background: #ffffff;
    border: 1px solid #cbd5e1;
    border-left-width: 3px;
    border-radius: 9px;
    padding: 11px 12px;
    display: flex;
    flex-direction: column;
    gap: 5px;
    cursor: pointer;
    transition: transform 0.15s ease, box-shadow 0.15s ease;
  }
  .ov-step-box:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(15, 23, 42, 0.06);
  }
  .ov-step-badge {
    font-size: 11px;
    font-weight: 800;
    font-family: var(--font-mono);
  }
  .ov-step-title {
    font-size: 13px;
    font-weight: 700;
    color: var(--apple-text-primary);
    line-height: 1.35;
  }
  .ov-step-desc {
    font-size: 12px;
    color: var(--apple-text-secondary);
    line-height: 1.55;
  }
  .ov-step-out {
    margin-top: 4px;
    padding-top: 6px;
    border-top: 1px dotted #cbd5e1;
    font-size: 11px;
    color: #334155;
    font-family: var(--font-mono);
    line-height: 1.45;
  }
  .ov-step-out b { color: #0f172a; }
  .ov-conn-v {
    text-align: center;
    font-size: 12px;
    color: #64748b;
    line-height: 1;
    user-select: none;
  }

  /* Overview Section 2 HTML Architecture Diagram (.ov-diagram-zone, .ovd) */
  .ov-diagram-zone {
    background: #f1f5f9;
    border: 1px solid #cbd5e1;
    border-radius: 12px;
    padding: 18px;
  }
  .ovd { display: flex; flex-direction: column; gap: 12px; font-size: 13px; color: #0f172a; }
  .ovd-band {
    background: #ffffff;
    border: 1px solid #cbd5e1;
    border-left-width: 4px;
    border-radius: 10px;
    padding: 14px 16px;
  }
  .ovd-band.b-teal { border-left-color: #0d9488; background: linear-gradient(90deg, rgba(13,148,136,0.05), #ffffff 35%); }
  .ovd-band.b-indigo { border-left-color: #4f46e5; background: linear-gradient(90deg, rgba(79,70,229,0.05), #ffffff 35%); }
  .ovd-band.b-purple { border-left-color: #7c3aed; background: linear-gradient(90deg, rgba(124,58,237,0.05), #ffffff 35%); }
  .ovd-band-head { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; margin-bottom: 10px; }
  .ovd-band-title { font-size: 13.5px; font-weight: 800; color: #0f172a; }
  .ovd-band-sub { font-size: 11.5px; font-weight: 600; color: #475569; font-family: var(--font-mono); }
  .ovd-flow { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; align-items: stretch; }
  .ovd-node {
    background: #f8fafc;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    padding: 10px 12px;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  .ovd-node.hi-teal { background: #f0fdfa; border-color: #5eead4; }
  .ovd-node.hi-indigo { background: #eef2ff; border-color: #a5b4fc; }
  .ovd-node.hi-purple { background: #f5f3ff; border-color: #c4b5fd; }
  .ovd-node-kicker { font-size: 10.5px; font-weight: 800; font-family: var(--font-mono); color: #0369a1; }
  .ovd-node-title { font-size: 12.5px; font-weight: 800; color: #0f172a; }
  .ovd-node-desc { font-size: 11.5px; color: #334155; line-height: 1.5; }
  .ovd-bridge {
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 10px;
    flex-wrap: wrap;
    padding: 8px 12px;
    background: #e2e8f0;
    border-radius: 8px;
    font-size: 12px;
    font-weight: 700;
    color: #1e293b;
  }
  .ovd-pill {
    background: #ffffff;
    border: 1px solid #94a3b8;
    border-radius: 999px;
    padding: 2px 10px;
    font-family: var(--font-mono);
    font-size: 11px;
    color: #0f172a;
  }

  .ov-gap-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
  }
  .ov-gap-table th {
    text-align: left;
    padding: 10px 14px;
    background: #f1f5f9;
    color: #1e293b;
    font-size: 12px;
    font-weight: 700;
    border-bottom: 1px solid #cbd5e1;
  }
  .ov-gap-table td {
    padding: 12px 14px;
    border-bottom: 1px solid #e2e8f0;
    color: var(--apple-text-primary);
    line-height: 1.55;
    vertical-align: top;
  }
  .ov-gap-table td.lead-cell { font-weight: 700; white-space: nowrap; color: var(--apple-blue); }
  .ov-gap-table td.muted { color: var(--apple-text-secondary); }
  .ov-metric-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
  }
  .metric-box {
    background: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 12px;
    padding: 14px 16px;
  }
  .metric-title {
    font-size: 11.5px;
    font-weight: 700;
    color: var(--apple-text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.03em;
  }
  .metric-value {
    font-size: 22px;
    font-weight: 800;
    color: var(--apple-text-primary);
    margin-top: 4px;
    letter-spacing: -0.02em;
  }
  .ov-metric-cap {
    font-size: 11.5px;
    color: var(--apple-text-secondary);
    margin-top: 4px;
  }

  /* 4-B. Interactive Path Map & Starter Pack Package Builder (GOAL-158) */
  .ov-preset-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(220px, 1fr));
    gap: 10px;
    margin-top: 12px;
  }
  .ov-preset-card {
    background: #ffffff;
    border: 1.5px solid #cbd5e1;
    border-radius: 11px;
    padding: 11px 13px;
    cursor: pointer;
    transition: all 0.16s ease;
    display: flex;
    flex-direction: column;
    gap: 4px;
    text-align: left;
  }
  .ov-preset-card:hover {
    border-color: var(--apple-blue);
    box-shadow: 0 3px 10px rgba(0, 113, 227, 0.08);
    transform: translateY(-1px);
  }
  .ov-preset-card.active {
    border-color: var(--apple-blue);
    background: linear-gradient(135deg, rgba(0, 113, 227, 0.08), rgba(2, 132, 199, 0.02));
    box-shadow: 0 3px 12px rgba(0, 113, 227, 0.12);
  }
  .ov-preset-top {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 6px;
  }
  .ov-preset-tag {
    font-size: 10.5px;
    font-weight: 800;
    font-family: var(--font-mono);
    padding: 2px 8px;
    border-radius: 999px;
    background: #e2e8f0;
    color: #0f172a;
  }
  .ov-preset-card.active .ov-preset-tag {
    background: var(--apple-blue);
    color: #ffffff;
  }
  .ov-preset-title {
    font-size: 13px;
    font-weight: 800;
    color: var(--apple-text-primary);
  }
  .ov-preset-route {
    font-size: 11px;
    font-weight: 700;
    font-family: var(--font-mono);
    color: #0284c7;
  }
  .ov-preset-desc {
    font-size: 11.5px;
    color: var(--apple-text-secondary);
    line-height: 1.45;
  }

  .ov-fullmap-canvas {
    background: #f8fafc;
    border: 1px solid #cbd5e1;
    border-radius: 12px;
    padding: 16px;
    display: flex;
    flex-direction: column;
    gap: 14px;
  }
  .ov-route-diagram-bar {
    background: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 10px;
    padding: 12px 16px;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .ov-map-cols {
    display: grid;
    grid-template-columns: repeat(5, minmax(215px, 1fr));
    gap: 12px;
    align-items: stretch;
  }
  .ov-map-col {
    background: #ffffff;
    border: 1.5px solid #cbd5e1;
    border-top-width: 4px;
    border-radius: 12px;
    padding: 12px;
    display: flex;
    flex-direction: column;
    gap: 8px;
    transition: all 0.18s ease;
  }
  .ov-map-col.bypassed {
    background: #f1f5f9;
    border-color: #cbd5e1;
    border-top-color: #94a3b8 !important;
    opacity: 0.78;
  }
  .ov-map-col-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 6px;
  }
  .ov-map-col-title {
    font-size: 13px;
    font-weight: 800;
    color: var(--apple-text-primary);
    line-height: 1.3;
  }
  .ov-map-col-sub {
    font-size: 11px;
    color: var(--apple-text-secondary);
    padding-bottom: 6px;
    border-bottom: 1px dashed #cbd5e1;
  }
  .ov-pick-card {
    background: #f8fafc;
    border: 1.5px solid #cbd5e1;
    border-radius: 9px;
    padding: 9px 11px;
    cursor: pointer;
    transition: all 0.15s ease;
    display: flex;
    flex-direction: column;
    gap: 4px;
    position: relative;
  }
  .ov-pick-card:hover {
    border-color: #0284c7;
    background: #ffffff;
    box-shadow: 0 2px 8px rgba(2, 132, 199, 0.08);
  }
  .ov-pick-card.selected {
    background: #eff6ff;
    border-color: var(--apple-blue);
    box-shadow: 0 2px 10px rgba(0, 113, 227, 0.12);
  }
  .ov-pick-card.selected.tone-teal {
    background: #f0fdfa;
    border-color: #0d9488;
  }
  .ov-pick-card.selected.tone-indigo {
    background: #eef2ff;
    border-color: #4f46e5;
  }
  .ov-pick-card.selected.tone-purple {
    background: #f5f3ff;
    border-color: #7c3aed;
  }
  .ov-pick-card.selected.tone-amber {
    background: #fffbeb;
    border-color: #d97706;
  }
  .ov-pick-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 6px;
  }
  .ov-pick-tag {
    font-size: 10px;
    font-weight: 800;
    font-family: var(--font-mono);
    color: #0369a1;
  }
  .ov-pick-state {
    font-size: 10px;
    font-weight: 800;
    padding: 1px 7px;
    border-radius: 999px;
    background: #e2e8f0;
    color: #475569;
  }
  .ov-pick-card.selected .ov-pick-state {
    background: var(--apple-blue);
    color: #ffffff;
  }
  .ov-pick-card.selected.tone-teal .ov-pick-state { background: #0d9488; }
  .ov-pick-card.selected.tone-indigo .ov-pick-state { background: #4f46e5; }
  .ov-pick-card.selected.tone-purple .ov-pick-state { background: #7c3aed; }
  .ov-pick-card.selected.tone-amber .ov-pick-state { background: #d97706; }
  .ov-pick-title {
    font-size: 12.5px;
    font-weight: 800;
    color: #0f172a;
    line-height: 1.3;
  }
  .ov-pick-desc {
    font-size: 11px;
    color: #475569;
    line-height: 1.45;
  }
  .ov-pick-meta {
    font-size: 10.5px;
    font-family: var(--font-mono);
    color: #0f172a;
    background: rgba(255, 255, 255, 0.75);
    border-top: 1px dotted #cbd5e1;
    padding-top: 4px;
    margin-top: 2px;
  }

  /* Assembled Package Implementation Diagram & 4-Card Manifest */
  .ov-pkg-pipe-grid {
    display: grid;
    grid-template-columns: repeat(5, minmax(200px, 1fr));
    gap: 10px;
    background: #f8fafc;
    border: 1px solid #cbd5e1;
    border-radius: 12px;
    padding: 14px;
    margin-bottom: 14px;
  }
  .ov-pkg-node {
    background: #ffffff;
    border: 1.5px solid #cbd5e1;
    border-left-width: 4px;
    border-radius: 10px;
    padding: 10px 12px;
    display: flex;
    flex-direction: column;
    gap: 4px;
    position: relative;
  }
  .ov-pkg-node.bypassed {
    background: #f1f5f9;
    border-style: dashed;
    border-left-style: solid;
    border-left-color: #94a3b8 !important;
    opacity: 0.72;
  }
  .ov-pkg-manifest-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(260px, 1fr));
    gap: 12px;
    align-items: stretch;
  }
  .ov-pkg-box {
    background: #f8fafc;
    border: 1px solid #cbd5e1;
    border-radius: 11px;
    padding: 13px 14px;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .ov-pkg-box-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 6px;
    padding-bottom: 6px;
    border-bottom: 1px solid #e2e8f0;
  }
  .ov-pkg-box-title {
    font-size: 12.5px;
    font-weight: 800;
    color: #0f172a;
  }
  .ov-pkg-item-row {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 8px;
    padding: 6px 8px;
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 7px;
    font-size: 11.5px;
  }
  .ov-pkg-item-row.skipped {
    background: #f1f5f9;
    color: #94a3b8;
    border-style: dashed;
  }
  .ov-stage-col.bypassed-col {
    background: #f1f5f9;
    border-style: dashed;
    opacity: 0.68;
  }

  /* 5. Stage 1 Asset Studio Styles (.asset-summary-ribbon, .bento-kpi-grid, .asset-list-card, .inspector-drawer) */
  .asset-summary-ribbon {
    display: flex;
    align-items: center;
    justify-content: space-between;
    background: #ffffff;
    border: 1px solid var(--apple-border-subtle);
    border-radius: 12px;
    padding: 10px 18px;
    flex-shrink: 0;
  }
  .bento-kpi-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
    flex-shrink: 0;
  }
  .bento-card {
    background: var(--apple-bg-primary);
    border-radius: 12px;
    padding: 12px 16px;
    border: 1px solid var(--apple-border-subtle);
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.02);
  }
  .bento-card-label {
    font-size: 11px;
    font-weight: 700;
    color: var(--apple-text-secondary);
    text-transform: uppercase;
  }
  .bento-card-value {
    font-size: 22px;
    font-weight: 800;
    color: var(--apple-text-primary);
    margin-top: 2px;
  }
  .bento-card-sub {
    font-size: 11.5px;
    color: var(--apple-text-secondary);
    margin-top: 2px;
  }
  .governance-toolbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    flex-shrink: 0;
  }
  .apple-segmented-control {
    display: inline-flex;
    background: rgba(118, 118, 128, 0.12);
    padding: 3px;
    border-radius: 9px;
  }
  .segment-btn {
    border: none;
    background: transparent;
    padding: 5px 14px;
    border-radius: 7px;
    font-size: 12px;
    font-weight: 600;
    color: var(--apple-text-secondary);
    cursor: pointer;
    font-family: var(--font-sans);
  }
  .segment-btn.active {
    background: var(--apple-bg-primary);
    color: var(--apple-text-primary);
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
  }
  .workspace-body {
    flex: 1;
    display: flex;
    gap: 16px;
    overflow: hidden;
    min-height: 0;
  }
  .asset-list-card {
    flex: 6;
    background: var(--apple-bg-primary);
    border-radius: 14px;
    border: 1px solid var(--apple-border-subtle);
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }
  .table-scroll-container {
    flex: 1;
    overflow-y: auto;
  }
  .asset-table {
    width: 100%;
    border-collapse: collapse;
    text-align: left;
  }
  .asset-table th {
    position: sticky;
    top: 0;
    background: rgba(245, 245, 247, 0.95);
    padding: 11px 16px;
    font-size: 11px;
    font-weight: 700;
    color: var(--apple-text-secondary);
    text-transform: uppercase;
    border-bottom: 1px solid var(--apple-border-subtle);
    z-index: 5;
  }
  .asset-table td {
    padding: 12px 16px;
    border-bottom: 1px solid rgba(0, 0, 0, 0.04);
    font-size: 13px;
    color: var(--apple-text-primary);
  }
  .asset-table tbody tr { cursor: pointer; transition: background 0.12s ease; }
  .asset-table tbody tr:hover { background: rgba(0, 113, 227, 0.04); }
  .asset-table tbody tr.selected {
    background: rgba(0, 113, 227, 0.08);
    box-shadow: inset 3px 0 0 var(--apple-blue);
  }
  .inspector-drawer {
    flex: 4;
    background: var(--apple-bg-primary);
    border-radius: 14px;
    border: 1px solid var(--apple-border-subtle);
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }
  .drawer-header {
    padding: 14px 18px;
    border-bottom: 1px solid var(--apple-border-subtle);
    background: #f8fafc;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  .drawer-body {
    flex: 1;
    padding: 16px 18px;
    overflow-y: auto;
    font-size: 12.5px;
    line-height: 1.6;
  }

  /* Badges */
  .badge {
    display: inline-flex;
    align-items: center;
    padding: 3px 9px;
    border-radius: 980px;
    font-size: 11px;
    font-weight: 700;
  }
  .badge.approved { background: rgba(5, 150, 105, 0.12); color: #059669; }
  .badge.human { background: rgba(0, 113, 227, 0.12); color: var(--apple-blue); }
  .badge.llm { background: rgba(13, 148, 136, 0.12); color: #0d9488; }
  .badge.indigo { background: #eef2ff; color: #4338ca; }
  .badge.amber { background: #fef3c7; color: #b45309; }

  /* 6. Stage 2 & Stage 3 Split Panes (Wiki + vis-network Canvas + DDL Viewer) */
  .split-pane-grid {
    flex: 1;
    display: grid;
    grid-template-columns: 45% 55%;
    gap: 16px;
    min-height: 0;
    overflow: hidden;
  }
  .pane-card {
    background: #ffffff;
    border: 1px solid var(--apple-border-subtle);
    border-radius: 14px;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    min-height: 0;
  }
  .pane-head {
    padding: 12px 16px;
    background: #f8fafc;
    border-bottom: 1px solid var(--apple-border-subtle);
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    flex-shrink: 0;
  }
  .pane-title {
    font-size: 13px;
    font-weight: 800;
    color: var(--apple-text-primary);
  }
  .pane-body {
    flex: 1;
    padding: 14px 16px;
    overflow-y: auto;
    min-height: 0;
  }
  .graph-canvas-box {
    flex: 1;
    width: 100%;
    min-height: 320px;
    background: radial-gradient(circle at center, #ffffff 0%, #f8fafc 100%);
    position: relative;
  }
  .graph-inspector-strip {
    padding: 12px 16px;
    background: #f8fafc;
    border-top: 1px solid var(--apple-border-subtle);
    font-size: 12.5px;
    color: var(--apple-text-primary);
    line-height: 1.55;
    min-height: 84px;
    flex-shrink: 0;
  }
  .code-pre-light {
    font-family: var(--font-mono);
    font-size: 12px;
    line-height: 1.6;
    background: #f8fafc;
    color: #0f172a;
    border: 1px solid #cbd5e1;
    border-radius: 10px;
    padding: 14px;
    white-space: pre-wrap;
    overflow-x: auto;
  }
  .chunk-card-light {
    background: #ffffff;
    border: 1px solid #cbd5e1;
    border-left: 4px solid #0d9488;
    border-radius: 10px;
    padding: 12px 14px;
    margin-bottom: 10px;
  }

  /* 7. Stage 4 Agent & MCP Workspace (.fde-native-workspace) */
  .fde-native-workspace {
    flex: 1;
    display: flex;
    gap: 16px;
    min-height: 0;
    overflow: hidden;
  }
  .fde-mcp-pane {
    width: 400px;
    flex-shrink: 0;
    background: #ffffff;
    border: 1px solid var(--apple-border-subtle);
    border-radius: 14px;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }
  .fde-console-pane {
    flex: 1;
    background: #ffffff;
    border: 1px solid var(--apple-border-subtle);
    border-radius: 14px;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }
  .mcp-tool-card {
    background: #f8fafc;
    border: 1px solid #cbd5e1;
    border-radius: 10px;
    padding: 12px 14px;
    margin-bottom: 10px;
    transition: border-color 0.15s ease;
  }
  .mcp-tool-card:hover { border-color: var(--apple-blue); }
  .mcp-step-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 5px;
    margin-top: 8px;
  }
  .mcp-step-chip {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    font-size: 11px;
    font-family: var(--font-mono);
    background: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 2px 7px;
    color: #334155;
  }
  .quick-chip-bar {
    padding: 10px 16px;
    background: #f8fafc;
    border-bottom: 1px solid var(--apple-border-subtle);
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
    align-items: center;
  }
  .quick-chip {
    font-size: 11.5px;
    font-weight: 600;
    padding: 5px 11px;
    border-radius: 980px;
    background: #ffffff;
    border: 1px solid #cbd5e1;
    color: #1e293b;
    cursor: pointer;
    transition: all 0.15s ease;
  }
  .quick-chip:hover {
    border-color: var(--apple-blue);
    color: var(--apple-blue);
    background: #eff6ff;
  }
  .console-timeline {
    flex: 1;
    padding: 18px;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 14px;
    background: #f8fafc;
  }
  .user-bubble-light {
    align-self: flex-end;
    background: var(--apple-blue);
    color: #ffffff;
    padding: 10px 16px;
    border-radius: 14px 14px 3px 14px;
    max-width: 78%;
    font-size: 13px;
    font-weight: 500;
    box-shadow: 0 2px 6px rgba(0, 113, 227, 0.2);
  }
  .trace-card-light {
    background: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 12px;
    padding: 16px 18px;
    font-size: 13px;
    color: var(--apple-text-primary);
    box-shadow: 0 2px 6px rgba(15, 23, 42, 0.04);
  }
  .subgoal-box-light {
    background: #f0f9ff;
    border-left: 3px solid #0284c7;
    padding: 10px 12px;
    border-radius: 6px;
    margin-bottom: 10px;
    font-size: 12.5px;
  }
  .obs-box-light {
    background: #f0fdf4;
    border-left: 3px solid #059669;
    padding: 10px 12px;
    border-radius: 6px;
    margin-bottom: 8px;
    font-family: var(--font-mono);
    font-size: 11.5px;
    color: #0f172a;
    word-break: break-all;
  }
  .input-dock-light {
    padding: 12px 16px;
    background: #ffffff;
    border-top: 1px solid var(--apple-border-subtle);
    display: flex;
    gap: 10px;
  }
  .query-input-light {
    flex: 1;
    background: #f8fafc;
    border: 1px solid #cbd5e1;
    color: var(--apple-text-primary);
    padding: 10px 14px;
    border-radius: 10px;
    font-size: 13px;
    font-family: var(--font-sans);
    outline: none;
  }
  .query-input-light:focus { border-color: var(--apple-blue); background: #ffffff; }
  .primary-btn {
    background: var(--apple-blue);
    color: #ffffff;
    border: none;
    padding: 0 18px;
    border-radius: 10px;
    font-weight: 700;
    font-size: 12.5px;
    cursor: pointer;
    font-family: var(--font-sans);
  }
  .primary-btn:hover { background: var(--apple-blue-hover); }

  /* Modal Overlay (Light Enterprise) */
  .modal-overlay {
    display: none;
    position: fixed;
    inset: 0;
    background: rgba(15, 23, 42, 0.45);
    backdrop-filter: blur(6px);
    z-index: 10000;
    align-items: center;
    justify-content: center;
    padding: 24px;
  }
  .modal-overlay.open { display: flex; }
  .modal-card {
    width: 100%;
    max-width: 820px;
    max-height: 85vh;
    background: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 16px;
    box-shadow: 0 20px 50px rgba(15, 23, 42, 0.18);
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }
  /* Project selector (top bar) */
  .hdr-project-select-wrap { display: inline-flex; align-items: center; gap: 6px; background: #ffffff; border: 1px solid #cbd5e1; border-radius: 999px; padding: 2px 10px; box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04); }
  .hdr-project-label { font-size: 10.5px; font-weight: 700; color: var(--apple-text-secondary); text-transform: uppercase; letter-spacing: 0.03em; }
  .hdr-project-select { border: none; background: transparent; font-family: var(--font-sans); font-size: 12px; font-weight: 700; color: var(--apple-blue); cursor: pointer; outline: none; padding: 2px 4px; max-width: 340px; }

  /* Stage 5 Enterprise Data Lineage DAG (same layout as the main studio lineage view) */
  .lineage-toolbar-island { background: var(--apple-bg-secondary); border: 1px solid var(--apple-border-subtle); border-radius: 14px; padding: 8px 14px; margin-bottom: 12px; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px; }
  .lineage-presets { display: inline-flex; background: rgba(0, 0, 0, 0.04); padding: 3px; border-radius: 10px; gap: 3px; flex-wrap: wrap; }
  .lineage-preset-btn { background: transparent; border: 1px solid transparent; padding: 5px 12px; font-size: 11.5px; font-weight: 600; color: var(--apple-text-secondary); border-radius: 8px; cursor: pointer; transition: all 0.16s ease; font-family: inherit; }
  .lineage-preset-btn:hover { color: var(--apple-text-primary); background: rgba(0, 0, 0, 0.04); }
  .lineage-preset-btn.active { background: var(--apple-bg-primary); color: var(--apple-blue); border-color: rgba(0, 113, 227, 0.2); box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08); font-weight: 700; }
  .lineage-icon-btn { height: 30px; min-width: 30px; padding: 0 9px; display: inline-flex; align-items: center; justify-content: center; gap: 5px; border-radius: 8px; }
  .lineage-canvas-viewport { position: relative; height: 640px; overflow: hidden; cursor: grab; border: 1px solid var(--apple-border-subtle); border-radius: 14px; background-color: #edf0f5; background-image: radial-gradient(rgba(203, 213, 225, 0.6) 1px, transparent 1px); background-size: 20px 20px; user-select: none; }
  .lineage-canvas-viewport:active { cursor: grabbing; }
  #lineage-world-container { position: absolute; top: 0; left: 0; width: 3400px; height: 1400px; transform-origin: 0 0; }
  #lineage-edges-svg, #lineage-nodes-layer { position: absolute; top: 0; left: 0; width: 100%; height: 100%; pointer-events: none; }
  #lineage-edges-svg { z-index: 10; }
  #lineage-nodes-layer { z-index: 20; }
  .lineage-empty { position: absolute; top: 40px; left: 40px; font-size: 13px; color: var(--apple-text-secondary); pointer-events: auto; }
  .lineage-node-card { position: absolute; width: 290px; height: 52px; background: #ffffff; border: 1.2px solid rgba(15, 23, 42, 0.18); border-radius: 6px; box-shadow: 0 1px 4px rgba(15, 23, 42, 0.1); display: flex; align-items: center; padding: 0 8px 0 0; cursor: pointer; pointer-events: auto; transition: box-shadow 0.15s ease, opacity 0.2s, border-color 0.15s; }
  .lineage-node-card:hover { box-shadow: 0 6px 16px rgba(15, 23, 42, 0.16); border-color: var(--apple-blue); z-index: 50; }
  .lineage-node-card.active-target { box-shadow: 0 0 0 2px var(--apple-blue), 0 8px 20px rgba(0, 113, 227, 0.35) !important; border-color: var(--apple-blue) !important; z-index: 60; }
  .lineage-node-card.highlighted { box-shadow: 0 0 0 1.5px var(--apple-blue), 0 4px 12px rgba(0, 113, 227, 0.25) !important; border-color: var(--apple-blue) !important; z-index: 45; }
  .lineage-node-card.dimmed { opacity: 0.14; filter: grayscale(85%); }
  .lineage-color-strip { width: 6px; height: 100%; border-top-left-radius: 5px; border-bottom-left-radius: 5px; margin-right: 8px; flex-shrink: 0; }
  .lineage-card-icon { font-size: 9.5px; font-weight: 700; margin-right: 6px; letter-spacing: -0.02em; flex-shrink: 0; }
  .lineage-card-label { flex: 1; min-width: 0; font-size: 11.5px; font-weight: 700; color: #0f172a; line-height: 1.35; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; overflow-wrap: anywhere; letter-spacing: -0.01em; }
  .lineage-card-badge { font-size: 9.5px; font-weight: 600; color: #475569; background: rgba(0, 0, 0, 0.05); padding: 2px 6px; border-radius: 4px; margin-left: 6px; flex-shrink: 0; white-space: nowrap; border: 1px solid rgba(0, 0, 0, 0.08); }
  .lineage-card-badge.live { color: #047857; background: #ecfdf5; border-color: #a7f3d0; }
  .lineage-spline-edge { fill: none; stroke: #64748b; stroke-width: 1.6; opacity: 0.75; transition: stroke 0.25s, stroke-width 0.25s, opacity 0.25s; }
  .lineage-spline-edge.highlighted { stroke: var(--apple-blue); stroke-width: 2.4; opacity: 1; filter: drop-shadow(0 0 4px rgba(0, 113, 227, 0.6)); }
  .lineage-spline-edge.dimmed { opacity: 0.06; }
  .lineage-floating-legend { position: absolute; top: 14px; right: 14px; width: 250px; background: rgba(255, 255, 255, 0.92); backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px); border: 1px solid var(--apple-border-subtle); border-radius: 10px; box-shadow: 0 6px 20px rgba(15, 23, 42, 0.10); z-index: 80; display: flex; flex-direction: column; overflow: hidden; }
  .lineage-legend-hdr { padding: 8px 12px; background: rgba(0, 0, 0, 0.03); border-bottom: 1px solid var(--apple-border-subtle); display: flex; align-items: center; justify-content: space-between; font-size: 11px; font-weight: 700; color: var(--apple-text-primary); }
  .lineage-legend-body { padding: 8px 12px; display: flex; flex-direction: column; gap: 5px; max-height: 290px; overflow-y: auto; }
  .lineage-legend-row { display: flex; align-items: center; justify-content: space-between; font-size: 11px; color: var(--apple-text-primary); cursor: pointer; padding: 3px 6px; border-radius: 4px; }
  .lineage-legend-row:hover { background: rgba(0, 113, 227, 0.08); }
  .lineage-legend-swatch { width: 10px; height: 10px; border-radius: 2px; margin-right: 8px; flex-shrink: 0; }
  .lineage-legend-count { font-size: 10px; font-weight: 600; color: var(--apple-text-secondary); }
  .lineage-minimap-panel { position: absolute; bottom: 14px; left: 14px; width: 180px; height: 100px; background: rgba(255, 255, 255, 0.9); backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px); border: 1px solid var(--apple-border-subtle); border-radius: 10px; z-index: 80; overflow: hidden; }
  .lineage-minimap-indicator { position: absolute; border: 1.5px solid var(--apple-blue); background: rgba(0, 113, 227, 0.18); border-radius: 2px; pointer-events: none; }
  .lineage-drawer { position: absolute; top: 0; right: 0; width: 410px; height: 100%; background: var(--apple-bg-primary); border-left: 1px solid var(--apple-border-subtle); box-shadow: -4px 0 24px rgba(0, 0, 0, 0.12); z-index: 120; transform: translateX(100%); transition: transform 0.25s cubic-bezier(0.16, 1, 0.3, 1); display: flex; flex-direction: column; }
  .lineage-drawer.open { transform: translateX(0); }
  .lineage-drawer-header { padding: 14px 18px; border-bottom: 1px solid var(--apple-border-subtle); display: flex; align-items: center; justify-content: space-between; background: var(--apple-bg-secondary); }
  .lineage-drawer-title { font-size: 13px; font-weight: 700; color: var(--apple-text-primary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .lineage-drawer-close { background: transparent; border: none; font-size: 14px; color: var(--apple-text-secondary); cursor: pointer; padding: 4px; border-radius: 4px; }
  .lineage-drawer-close:hover { background: rgba(0, 0, 0, 0.06); color: var(--apple-text-primary); }
  .lineage-drawer-body { padding: 16px 18px; overflow-y: auto; flex: 1; display: flex; flex-direction: column; gap: 14px; }
  .lineage-drawer-section { background: var(--apple-bg-secondary); border: 1px solid var(--apple-border-subtle); border-radius: 8px; padding: 12px 14px; }
  .lineage-drawer-sec-label { font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em; color: var(--apple-text-secondary); margin-bottom: 8px; }
  .lineage-drawer-prop-row { display: grid; grid-template-columns: 85px 1fr; row-gap: 5px; font-size: 11px; }
  .lineage-prop-k { color: var(--apple-text-secondary); }
  .lineage-prop-v { color: var(--apple-text-primary); font-weight: 500; word-break: break-all; }
  .lineage-link-row { background: var(--apple-bg-primary); padding: 5px 8px; border-radius: 4px; border: 1px solid var(--apple-border-subtle); cursor: pointer; display: flex; justify-content: space-between; align-items: center; gap: 8px; }
  .lineage-agent-card { background: rgba(0, 113, 227, 0.06); border: 1px solid rgba(0, 113, 227, 0.2); border-radius: 8px; padding: 12px 14px; }
  .lineage-citation-text { font-size: 11.5px; color: var(--apple-blue); line-height: 1.5; white-space: pre-wrap; }
  .lineage-btn-ask-agent { width: 100%; margin-top: 10px; background: var(--apple-blue); color: #ffffff; border: none; padding: 7px 12px; border-radius: 999px; font-size: 11.5px; font-weight: 600; cursor: pointer; font-family: inherit; }
  .lineage-btn-ask-agent:hover { background: var(--apple-blue-hover); }

  /* 9. Track-Driven Project Workbench & Step-by-Step Approval (GRILL-011) */
  .view-mode-pill.bypassed-tab {
    opacity: 0.65;
    border: 1px dashed #94a3b8 !important;
  }
  .tab-bypass-chip {
    display: inline-block;
    margin-left: 5px;
    padding: 1px 6px;
    font-size: 9.5px;
    font-weight: 800;
    border-radius: 999px;
    background: #e2e8f0;
    color: #475569;
    vertical-align: middle;
  }
  .stage-workbench-bar {
    background: linear-gradient(135deg, #f8fafc 0%, #f0f9ff 100%);
    border: 1.5px solid #93c5fd;
    border-left: 4px solid var(--apple-blue);
    border-radius: 12px;
    padding: 12px 16px;
    display: flex;
    flex-direction: column;
    gap: 10px;
    box-shadow: 0 2px 8px rgba(0, 113, 227, 0.06);
  }
  .wb-top-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 10px;
  }
  .wb-stepper {
    display: flex;
    align-items: center;
    gap: 6px;
    flex-wrap: wrap;
  }
  .wb-step-pill {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 4px 10px;
    border-radius: 999px;
    font-size: 11px;
    font-weight: 700;
    border: 1px solid #cbd5e1;
    background: #ffffff;
    color: #334155;
    cursor: pointer;
    transition: all 0.14s ease;
  }
  .wb-step-pill.current {
    border-color: var(--apple-blue);
    box-shadow: 0 0 0 2px rgba(0, 113, 227, 0.15);
  }
  .wb-step-pill.st-APPROVED {
    background: #ecfdf5;
    border-color: #6ee7b7;
    color: #065f46;
  }
  .wb-step-pill.st-TRANSFORMED {
    background: #eff6ff;
    border-color: #60a5fa;
    color: #1e40af;
  }
  .wb-step-pill.st-BYPASSED {
    background: #f1f5f9;
    border-style: dashed;
    color: #64748b;
  }
  .wb-upload-strip {
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 10px;
    background: #ffffff;
    border: 1px dashed #60a5fa;
    border-radius: 10px;
    padding: 9px 12px;
  }
  .wb-action-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 10px;
    padding-top: 6px;
    border-top: 1px solid rgba(148, 163, 184, 0.28);
  }
  .wb-summary-text {
    font-size: 12px;
    color: #1e293b;
    line-height: 1.5;
    flex: 1;
    min-width: 260px;
    white-space: pre-line;
  }
  .wb-btn-run {
    background: #ffffff;
    color: var(--apple-blue);
    border: 1.5px solid var(--apple-blue);
    border-radius: 8px;
    padding: 6px 13px;
    font-size: 12px;
    font-weight: 700;
    cursor: pointer;
    font-family: inherit;
    transition: all 0.15s ease;
  }
  .wb-btn-run:hover {
    background: rgba(0, 113, 227, 0.08);
  }
  .wb-btn-approve {
    background: #059669;
    color: #ffffff;
    border: 1.5px solid #047857;
    border-radius: 8px;
    padding: 6px 14px;
    font-size: 12px;
    font-weight: 700;
    cursor: pointer;
    font-family: inherit;
    transition: all 0.15s ease;
  }
  .wb-btn-approve:hover {
    background: #047857;
  }
  .lite-bypass-banner {
    display: none;
    background: #fffbeb;
    border: 1.5px solid #fcd34d;
    border-left: 4px solid #f59e0b;
    border-radius: 12px;
    padding: 14px 18px;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    flex-wrap: wrap;
  }
  .np-form-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
  }
  .np-field {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  .np-field label {
    font-size: 11.5px;
    font-weight: 700;
    color: #334155;
  }
  .np-input {
    padding: 8px 10px;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    font-size: 12.5px;
    font-family: inherit;
    color: #0f172a;
    background: #ffffff;
  }
</style>
</head>
<body>

  <!-- 1. GLOBAL TOPBAR (44px, Official Google 'G' SVG + Brand + KOR/ENG Switch) -->
  <nav class="globalnav">
    <div class="globalnav-content">
      <div class="globalnav-left">
        <a href="/" class="globalnav-logo">
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path fill="#4285F4" d="M23.49 12.27c0-.79-.07-1.54-.19-2.27H12v4.51h6.47c-.29 1.48-1.14 2.73-2.4 3.58v3h3.86c2.26-2.09 3.56-5.17 3.56-8.82z"/>
            <path fill="#34A853" d="M12 24c3.24 0 5.95-1.08 7.93-2.91l-3.86-3c-1.08.72-2.45 1.16-4.07 1.16-3.13 0-5.78-2.11-6.73-4.96H1.29v3.09C3.26 21.3 7.31 24 12 24z"/>
            <path fill="#FBBC05" d="M5.27 14.29c-.25-.72-.38-1.49-.38-2.29s.13-1.57.38-2.29V6.62H1.29C.47 8.24 0 10.06 0 12s.47 3.76 1.29 5.38l3.98-3.09z"/>
            <path fill="#EA4335" d="M12 4.75c1.77 0 3.35.61 4.6 1.8l3.42-3.42C17.95 1.19 15.24 0 12 0 7.31 0 3.26 2.7 1.29 6.62l3.98 3.09c.95-2.85 3.6-4.96 6.73-4.96z"/>
          </svg>
          <span>Agentic Ontology Studio</span>
        </a>
        <div class="hdr-project-select-wrap" title="고객·데이터 영역별 프로젝트 전환 (projects/<id>/)">
          <span class="hdr-project-label">Project</span>
          <select id="hdr-project-select" class="hdr-project-select" onchange="switchProject(this.value)"></select>
        </div>
        <button class="subnav-action-btn" style="padding:3px 10px; font-size:11px; border-color:var(--apple-blue); color:var(--apple-blue); font-weight:700;" onclick="openNewProjectModal()" data-ko="+ 선택 트랙으로 신규 프로젝트" data-en="+ New Project with Track">+ 선택 트랙으로 신규 프로젝트</button>
        <span class="hdr-meta-badge">Starter Pack v2.0</span>
        <span class="hdr-meta-badge teal" id="hdr-track-badge">Track 3 · Full-Stack</span>
        <span class="hdr-meta-badge indigo" id="hdr-engine-badge">BigQuery Property Graph</span>
      </div>
      <div class="hdr-right-controls">
        <button class="subnav-action-btn" onclick="openIndustryModal()" data-ko="업종별 추천 유즈케이스 (8대 기업)" data-en="Industry Use Cases (8 Enterprises)">업종별 추천 유즈케이스 (8대 기업)</button>
        <div class="hdr-pill-switch hdr-lang-switch" title="한글 / 영문 표시 전환">
          <button id="lang-btn-ko" class="active" onclick="setStudioLanguage('ko')">KOR</button>
          <button id="lang-btn-en" onclick="setStudioLanguage('en')">ENG</button>
        </div>
      </div>
    </div>
  </nav>

  <!-- 2. LOCAL SUBBAR (52px, .ac-localnav + .compact-pill-bar with 6 Compressed Stage Tabs) -->
  <div class="ac-localnav">
    <div class="ac-localnav-content">
      <div class="compact-pill-bar" id="main-tab-ribbon">
        <button class="view-mode-pill active" data-tab="overview" onclick="switchTab('overview')">0. Overview</button>
        <button class="view-mode-pill" data-tab="stage1" onclick="switchTab('stage1')" id="tab-btn-stage1">Stage 1. Asset</button>
        <button class="view-mode-pill" data-tab="stage2" onclick="switchTab('stage2')" id="tab-btn-stage2">Stage 2. Wiki &amp; Semantic Graph</button>
        <button class="view-mode-pill" data-tab="stage3" onclick="switchTab('stage3')" id="tab-btn-stage3">Stage 3. Property Graph</button>
        <button class="view-mode-pill" data-tab="stage4" onclick="switchTab('stage4')" id="tab-btn-stage4">Stage 4. Agent &amp; MCP</button>
        <button class="view-mode-pill" data-tab="stage5" onclick="switchTab('stage5')" id="tab-btn-stage5">Stage 5. Lineage &amp; Eval</button>
      </div>
      <div style="display:flex; align-items:center; gap:8px;">
        <button class="subnav-action-btn" style="border-color:#0d9488; color:#0f766e; font-weight:700;" onclick="openNewProjectModal()" data-ko="+ 선택 트랙으로 프로젝트 생성 &amp; 워크벤치 시작" data-en="+ Create Project with Selected Track">+ 선택 트랙으로 프로젝트 생성 &amp; 워크벤치 시작</button>
        <button class="subnav-action-btn" onclick="openStageMcpModal('mcp_stage1_asset_discovery')">▶ Run Stage MCP</button>
      </div>
    </div>
  </div>

  <!-- 3. STUDIO CONTAINER -->
  <main class="studio-container">

    <!-- =================================================================== -->
    <!-- TAB 0: 0. OVERVIEW (Light Enterprise Architecture & 5-Stage Board)  -->
    <!-- =================================================================== -->
    <section class="tab-panel active" id="panel-overview">
      <div class="ov-scroll-wrap">

        <!-- PART 1: Interactive Full-Picture Path Map & Building Block Selector -->
        <div class="ov-card ov-hero-card" id="ov-fullmap-card">
          <div class="ov-card-head">
            <span class="ov-eyebrow" id="ov-builder-eyebrow" data-ko="INTERACTIVE PATH MAP &amp; STARTER PACK PACKAGE BUILDER" data-en="INTERACTIVE PATH MAP &amp; STARTER PACK PACKAGE BUILDER">INTERACTIVE PATH MAP &amp; STARTER PACK PACKAGE BUILDER</span>
            <div style="display:flex; gap:6px; align-items:center; flex-wrap:wrap;">
              <span class="badge approved" data-ko="전체 경로 그림 + 항목 클릭형 패키지 조립" data-en="Visual Path Map + Click-to-Assemble Package">전체 경로 그림 + 항목 클릭형 패키지 조립</span>
              <a class="subnav-action-btn" style="text-decoration:none; padding:3px 10px; font-size:11px;" href="/docs/architecture/gcp_system_architecture.html" target="_blank" rel="noopener" data-ko="GCP 시스템 아키텍처 (HTML)" data-en="GCP System Architecture (HTML)">GCP 시스템 아키텍처 (HTML)</a>
              <a class="subnav-action-btn" style="text-decoration:none; padding:3px 10px; font-size:11px;" href="https://github.com/seanjungG/agentic-ontology-starter/blob/main/methodology/ko/METHODOLOGY_KO.md" target="_blank" rel="noopener" data-ko="방법론 (METHODOLOGY_KO.md)" data-en="Methodology (METHODOLOGY_EN.md)">방법론 (METHODOLOGY_KO.md)</a>
              <a class="subnav-action-btn" style="text-decoration:none; padding:3px 10px; font-size:11px;" href="https://github.com/seanjungG/agentic-ontology-starter/blob/main/notebooks/ko/stage0_overview_walkthrough_ko.ipynb" target="_blank" rel="noopener" data-ko="노트북 (Stage 0)" data-en="Notebook (Stage 0)">노트북 (Stage 0)</a>
            </div>
          </div>
          <h2 class="ov-h2" id="ov-builder-title" data-ko="전체 경로(Lite · Standard · Full-Stack) 다이어그램 &amp; 스타터팩 패키지 조립 보드" data-en="Full-Picture Path Map (Lite · Standard · Full-Stack) &amp; Starter Pack Package Builder">전체 경로(Lite · Standard · Full-Stack) 다이어그램 &amp; 스타터팩 패키지 조립 보드</h2>
          <p class="ov-lead" id="ov-builder-lead" style="margin-bottom:10px;" data-ko="아래 <b>전체 경로 그림(Stage 1 ➔ Stage 5)</b>에서 <b>패스 프리셋(Lite / Standard / Full-Stack / Dual Fabric)</b>을 누르거나 <b>각 단계의 구성 항목 카드를 직접 클릭</b>해 보세요. 선택한 경로가 실시간으로 연결되며, 바로 아래에 <b>선택한 조합으로 조립·구현되는 스타터팩 패키지 구성도(파이프라인 아키텍처, 포함 코드 모듈, 활성 MCP·노트북, project.json·Terraform, 실행 CLI)</b>가 즉시 재구성됩니다." data-en="Select a <b>Path Preset (Lite / Standard / Full-Stack / Dual Fabric)</b> or <b>click any building block inside the Stage 1 ➔ Stage 5 diagram</b> below. The active route lights up in real time and dynamically assembles the <b>Starter Pack Package Blueprint (pipeline flow, Python modules, MCP tools, notebooks, project.json/Terraform, and CLI commands)</b>.">
            아래 <b>전체 경로 그림(Stage 1 ➔ Stage 5)</b>에서 <b>패스 프리셋(Lite / Standard / Full-Stack / Dual Fabric)</b>을 누르거나 <b>각 단계의 구성 항목 카드를 직접 클릭</b>해 보세요. 선택한 경로가 실시간으로 연결되며, 바로 아래에 <b>선택한 조합으로 조립·구현되는 스타터팩 패키지 구성도(파이프라인 아키텍처, 포함 코드 모듈, 활성 MCP·노트북, project.json·Terraform, 실행 CLI)</b>가 즉시 재구성됩니다.
          </p>

          <!-- 1-A. 4 Quick Path Preset Cards + Synchronized Segmented Strip -->
          <div class="ov-preset-grid" id="ov-preset-grid"></div>

          <div class="ov-config-strip" style="margin-top:10px;">
            <div style="display:flex; align-items:center; gap:10px; flex-wrap:wrap;">
              <span style="font-size:12px; font-weight:700; color:#1e293b;" data-ko="데이터 성숙도 트랙 (Track):" data-en="Data Maturity Track:">데이터 성숙도 트랙 (Track):</span>
              <div class="apple-segmented-control" id="ov-track-selector">
                <button class="segment-btn" onclick="selectTrack('lite')">Track 1 · Lite (Stage 1→2→4)</button>
                <button class="segment-btn" onclick="selectTrack('standard')">Track 2 · Standard (Stage 1→2→3→4)</button>
                <button class="segment-btn active" onclick="selectTrack('full')">Track 3 · Full-Stack (Stage 1→5)</button>
              </div>
            </div>
            <div style="display:flex; align-items:center; gap:10px; flex-wrap:wrap;">
              <span style="font-size:12px; font-weight:700; color:#1e293b;" data-ko="물리 그래프 엔진 어댑터 (Graph Engine):" data-en="Physical Graph Engine Adapter:">물리 그래프 엔진 어댑터 (Graph Engine):</span>
              <div class="apple-segmented-control" id="ov-engine-selector">
                <button class="segment-btn active" onclick="selectGraphEngine('bigquery')">BigQuery Property Graph (SQL:2023)</button>
                <button class="segment-btn" onclick="selectGraphEngine('spanner')">Cloud Spanner Graph (ISO GQL)</button>
                <button class="segment-btn" onclick="selectGraphEngine('both')">Dual Fabric (BQ + Spanner)</button>
                <button class="segment-btn" onclick="selectGraphEngine('none')">미사용 (Lite Bypass)</button>
              </div>
            </div>
          </div>

          <!-- 1-B. Full-Picture Path Diagram & 5-Column Clickable Building Blocks -->
          <div class="ov-fullmap-canvas" style="margin-top:12px;">
            <div class="ov-route-diagram-bar" id="ov-route-diagram-bar"></div>
            <div class="ov-map-cols" id="ov-map-cols"></div>
          </div>
        </div>

        <!-- PART 2: Assembled Starter Pack Package Implementation Blueprint -->
        <div class="ov-card" id="ov-assembled-package-card" style="border-left:4px solid #0d9488;">
          <div class="ov-card-head">
            <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap;">
              <span class="ov-eyebrow teal" data-ko="ASSEMBLED STARTER PACK BLUEPRINT · 선택 조합 패키지 구현 구성도" data-en="ASSEMBLED STARTER PACK BLUEPRINT · PACKAGE IMPLEMENTATION VIEW">ASSEMBLED STARTER PACK BLUEPRINT · 선택 조합 패키지 구현 구성도</span>
              <span class="badge human" id="ov-pkg-active-badge">Track 3 · Full-Stack + BigQuery Property Graph</span>
            </div>
            <div style="display:flex; gap:8px; align-items:center; flex-wrap:wrap;">
              <div style="display:flex; gap:6px; align-items:center; flex-wrap:wrap;" id="ov-pkg-kpi-pills"></div>
              <button class="wb-btn-run" onclick="applyTrackToCurrentProject()" data-ko="현재 프로젝트에 선택 트랙/엔진 즉시 적용" data-en="Apply Track/Engine to Current Project">현재 프로젝트에 선택 트랙/엔진 즉시 적용</button>
              <button class="wb-btn-approve" onclick="openNewProjectModal()" data-ko="+ 선택 트랙으로 신규 프로젝트 생성 (파일 업로드 &amp; Gemini 스텝별 승인)" data-en="+ Create New Project with Selected Track (Upload &amp; Step-by-Step Gemini)">+ 선택 트랙으로 신규 프로젝트 생성 (파일 업로드 &amp; Gemini 스텝별 승인)</button>
            </div>
          </div>
          <h2 class="ov-h2" id="ov-pkg-title">선택한 구성 항목으로 조립된 스타터팩 패키지 아키텍처 &amp; 구현 명세</h2>
          <p class="ov-lead" id="ov-pkg-subtitle" style="margin-bottom:12px;"></p>

          <!-- 2-A. Visual 5-Stage Package Implementation Pipeline Diagram -->
          <div class="ov-pkg-pipe-grid" id="ov-pkg-pipe-grid"></div>

          <!-- 2-B. 4-Column Package Manifest (Code Modules / MCP & Notebooks / project.json & Terraform / CLI) -->
          <div class="ov-pkg-manifest-grid" id="ov-pkg-manifest-grid"></div>
        </div>

        <!-- PART 3: 5-Stage Detailed Step & MCP Execution Board (Synced with Selected Path) -->
        <div class="ov-card">
          <div class="ov-card-head">
            <span class="ov-eyebrow" id="ov-s1-eyebrow">SECTION 2 · 5-STAGE METHODOLOGY &amp; MODULAR MCP PIPELINE</span>
            <span class="badge human" id="ov-s1-path-hint">선택한 패스에 포함된 활성 Stage와 생략(Bypass) Stage가 구분 표시됩니다</span>
          </div>
          <h2 class="ov-h2" id="ov-s1-title">5-Stage 온톨로지 엔지니어링 방법론과 모듈형 Stage MCP 실행 보드</h2>
          <p class="ov-lead" id="ov-s1-lead"></p>
          <div class="ov-flow-board" id="ov-flow-board"></div>
        </div>

        <!-- PART 4: Feature Gap Matrix & Measured Starter Benchmark -->
        <div class="ov-card">
          <div class="ov-card-head">
            <span class="ov-eyebrow indigo" id="ov-s2-eyebrow">SECTION 3 · GOOGLE CLOUD NATIVE FOUNDATION VS. STARTER PACK EXTENSIONS</span>
            <span class="ov-eyebrow purple" id="ov-s4-eyebrow">MEASURED STARTER BENCHMARK</span>
          </div>
          <h2 class="ov-h2" id="ov-s2-title">Google Cloud 네이티브 기반 기술과 스타터팩 모듈형 확장 아키텍처</h2>
          <p class="ov-lead" id="ov-s4-note" style="margin-bottom:10px;"></p>
          <div class="ov-metric-grid" id="ov-metric-grid" style="margin-bottom:14px;"></div>
          <table class="ov-gap-table">
            <thead>
              <tr>
                <th style="width:22%;">스튜디오 단계 (Stage)</th>
                <th style="width:24%;">Google Cloud Native 기반</th>
                <th style="width:26%;">단독 사용 시 한계 (Gap)</th>
                <th style="width:28%;">스타터팩 모듈형 해법 (Solution)</th>
              </tr>
            </thead>
            <tbody id="ov-gap-body"></tbody>
          </table>
        </div>

      </div>
    </section>

    <!-- =================================================================== -->
    <!-- TAB 1: STAGE 1. ASSET (De-identified DW Ledgers & Policy Guides)    -->
    <!-- =================================================================== -->
    <section class="tab-panel" id="panel-stage1">
      <div style="display:flex; flex-direction:column; gap:12px; flex:1; min-height:0;">
        <div id="wb-bar-stage1"></div>
        <div class="asset-summary-ribbon">
          <div style="display:flex; align-items:center; gap:10px;">
            <span class="badge human">STAGE 1 · ASSET DISCOVERY &amp; GOVERNANCE</span>
            <span id="st1-ribbon-title" style="font-size:13.5px; font-weight:700; color:var(--apple-text-primary);">비식별화 정형 마스터 원장(4종) &amp; 비정형 정책 가이드(2종) 통합 인벤토리</span>
          </div>
          <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap;">
            <span class="badge approved">PII De-identified (CUST_DEMO_*)</span>
            <a class="subnav-action-btn" style="text-decoration:none;" href="https://github.com/seanjungG/agentic-ontology-starter/blob/main/methodology/ko/01_stage1_asset_and_cq_ko.md" target="_blank" rel="noopener">방법론 (Stage 1)</a>
            <a class="subnav-action-btn" style="text-decoration:none;" href="https://github.com/seanjungG/agentic-ontology-starter/blob/main/notebooks/ko/stage1_asset_and_cq_ko.ipynb" target="_blank" rel="noopener">노트북 (Stage 1)</a>
            <button class="subnav-action-btn" onclick="openStageMcpModal('mcp_stage1_asset_discovery')">▶ Stage 1 MCP 실행</button>
          </div>
        </div>

        <div class="bento-kpi-grid">
          <div class="bento-card">
            <div class="bento-card-label" data-ko="스코핑 완료 핵심 자산" data-en="SCOPED CORE ASSETS">스코핑 완료 핵심 자산</div>
            <div class="bento-card-value" style="color:var(--apple-blue);" id="st1-kpi-assets">-</div>
            <div class="bento-card-sub" id="st1-kpi-assets-sub">-</div>
          </div>
          <div class="bento-card">
            <div class="bento-card-label" data-ko="정형 원장 레코드" data-en="STRUCTURED DW ROWS">정형 원장 레코드</div>
            <div class="bento-card-value" style="color:var(--apple-indigo);" id="st1-kpi-rows">-</div>
            <div class="bento-card-sub" id="st1-kpi-rows-sub">-</div>
          </div>
          <div class="bento-card">
            <div class="bento-card-label" data-ko="비정형 해시 앵커 청크" data-en="ANCHORED DOC CHUNKS">비정형 해시 앵커 청크</div>
            <div class="bento-card-value" style="color:var(--apple-teal);" id="st1-kpi-chunks">-</div>
            <div class="bento-card-sub" id="st1-kpi-chunks-sub">-</div>
          </div>
          <div class="bento-card">
            <div class="bento-card-label" data-ko="노이즈 프루닝 & 비식별화" data-en="NOISE PRUNING & PII GUARD">노이즈 프루닝 &amp; 비식별화</div>
            <div class="bento-card-value" style="color:var(--apple-emerald);" id="st1-kpi-pii">-</div>
            <div class="bento-card-sub" id="st1-kpi-pii-sub">-</div>
          </div>
        </div>

        <div class="governance-toolbar">
          <div class="apple-segmented-control">
            <button class="segment-btn active" id="st1-filter-all" onclick="filterStage1Assets('all')">전체 자산 (6)</button>
            <button class="segment-btn" id="st1-filter-dw" onclick="filterStage1Assets('dw')">정형 DW 마스터 원장 (4)</button>
            <button class="segment-btn" id="st1-filter-doc" onclick="filterStage1Assets('doc')">비정형 정책 가이드 (2)</button>
          </div>
          <span style="font-size:12px; color:var(--apple-text-secondary);" data-ko="행을 클릭하면 우측 6:4 인스펙터에 실제 CSV 레코드 및 원문 청크가 표시됩니다." data-en="Click any row to inspect live CSV records or anchored policy chunks in the right drawer.">행을 클릭하면 우측 6:4 인스펙터에 실제 CSV 레코드 및 원문 청크가 표시됩니다.</span>
        </div>

        <div class="workspace-body">
          <div class="asset-list-card">
            <div class="table-scroll-container">
              <table class="asset-table">
                <thead>
                  <tr>
                    <th>자산 식별자 (Asset ID)</th>
                    <th>비즈니스 명칭</th>
                    <th>트랙 구분</th>
                    <th>규모 / 스키마</th>
                    <th>거버넌스 상태</th>
                  </tr>
                </thead>
                <tbody id="stage1-asset-tbody"></tbody>
              </table>
            </div>
          </div>
          <div class="inspector-drawer">
            <div class="drawer-header">
              <div>
                <div style="font-size:11px; font-weight:700; color:var(--apple-blue);" id="st1-insp-kicker">STAGE 1 ASSET INSPECTOR</div>
                <div style="font-size:14px; font-weight:800; color:var(--apple-text-primary);" id="st1-insp-title">자산을 선택하세요</div>
              </div>
              <span class="badge approved" id="st1-insp-badge">VERIFIED</span>
            </div>
            <div class="drawer-body" id="st1-insp-body"></div>
          </div>
        </div>
      </div>
    </section>

    <!-- =================================================================== -->
    <!-- TAB 2: STAGE 2. WIKI & SEMANTIC GRAPH (3-Layer Wiki + vis-network)  -->
    <!-- =================================================================== -->
    <section class="tab-panel" id="panel-stage2">
      <div style="display:flex; flex-direction:column; gap:12px; flex:1; min-height:0;">
        <div id="wb-bar-stage2"></div>
        <div class="asset-summary-ribbon">
          <div style="display:flex; align-items:center; gap:10px;">
            <span class="badge llm">STAGE 2 · 3-LAYER LLM-WIKI &amp; SEMANTIC GRAPH</span>
            <span style="font-size:13.5px; font-weight:700; color:var(--apple-text-primary);" data-ko="Karpathy 3-Layer Wiki 컴파일러 & 시맨틱 온톨로지 그래프 (Entity=Node, Concept=Edge)" data-en="Karpathy 3-Layer Wiki Compiler & Semantic Ontology Graph (Entity=Node, Concept=Edge)">Karpathy 3-Layer Wiki 컴파일러 &amp; 시맨틱 온톨로지 그래프 (Entity=Node, Concept=Edge)</span>
          </div>
          <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap;">
            <span class="badge human">Track 1 (Lite: 1→2→4) Bridge</span>
            <a class="subnav-action-btn" style="text-decoration:none;" href="https://github.com/seanjungG/agentic-ontology-starter/blob/main/methodology/ko/02_stage2_wiki_and_semantic_graph_ko.md" target="_blank" rel="noopener">방법론 (Stage 2)</a>
            <a class="subnav-action-btn" style="text-decoration:none;" href="https://github.com/seanjungG/agentic-ontology-starter/blob/main/notebooks/ko/stage2_wiki_and_semantic_graph_ko.ipynb" target="_blank" rel="noopener">노트북 (Stage 2)</a>
            <button class="subnav-action-btn" onclick="openStageMcpModal('mcp_stage2_wiki_and_semantic')">▶ Stage 2 MCP 실행</button>
          </div>
        </div>

        <div class="split-pane-grid">
          <!-- Left: 3-Layer LLM-Wiki & SHA-256 Chunks -->
          <div class="pane-card">
            <div class="pane-head">
              <span class="pane-title">OKF v0.2 3-Layer LLM-Wiki &amp; SHA-256 Chunks</span>
              <div class="apple-segmented-control">
                <button class="segment-btn active" id="wtab-summary" onclick="showWikiDoc('summary.md', 'wtab-summary')">L1 Summary</button>
                <button class="segment-btn" id="wtab-entities" onclick="showWikiDoc('entities.md', 'wtab-entities')">L2 Entities</button>
                <button class="segment-btn" id="wtab-concepts" onclick="showWikiDoc('concepts.md', 'wtab-concepts')">L3 Concepts</button>
                <button class="segment-btn" id="wtab-rules" onclick="showWikiDoc('rules.md', 'wtab-rules')">L3 Rules</button>
                <button class="segment-btn" id="wtab-chunks" onclick="showWikiDoc('chunks', 'wtab-chunks')">Chunks (5)</button>
              </div>
            </div>
            <div class="pane-body" id="stage2-wiki-body"></div>
          </div>

          <!-- Right: Interactive vis-network Semantic Graph -->
          <div class="pane-card">
            <div class="pane-head">
              <span class="pane-title" data-ko="시맨틱 온톨로지 그래프 (Entity=Node · Concept=Edge · Sky Blue 허브)" data-en="Semantic Ontology Graph (Entity=Node · Concept=Edge · Sky Blue Hub)">시맨틱 온톨로지 그래프 (Entity=Node · Concept=Edge · Sky Blue 허브)</span>
              <div style="display:flex; gap:6px; align-items:center;">
                <span class="badge human" style="background:#e0f2fe; color:#0369a1;">Hub #0284c7</span>
                <span class="badge approved">Edge 1.15px</span>
                <button class="subnav-action-btn" style="padding:3px 9px; font-size:11px;" onclick="renderSemanticGraph()">Fit Graph</button>
              </div>
            </div>
            <div class="graph-canvas-box" id="semantic-graph-canvas"></div>
            <div class="graph-inspector-strip" id="semantic-graph-inspector">
              <strong>[시맨틱 그래프 인스펙터]</strong> 노드를 클릭하면 연결된 시맨틱 관계(Edge)와 원문 해시 앵커(<code>DOC_CHUNK_*</code>) 설명이 여기에 표시됩니다.
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- =================================================================== -->
    <!-- TAB 3: STAGE 3. PROPERTY GRAPH (BigQuery Graph <-> Spanner Graph)   -->
    <!-- =================================================================== -->
    <section class="tab-panel" id="panel-stage3">
      <div style="display:flex; flex-direction:column; gap:12px; flex:1; min-height:0;">
        <div id="wb-bar-stage3"></div>
        <div id="st3-lite-bypass-banner" class="lite-bypass-banner"></div>
        <div class="asset-summary-ribbon">
          <div style="display:flex; align-items:center; gap:10px;">
            <span class="badge indigo">STAGE 3 · DUAL PROPERTY GRAPH ENGINEERING</span>
            <span style="font-size:13.5px; font-weight:700; color:var(--apple-text-primary);" data-ko="Zero-ETL 물리 그래프 토폴로지 & BigQuery / Spanner 듀얼 DDL 합성기" data-en="Zero-ETL Physical Graph Topology & BigQuery / Spanner Dual DDL Synthesizer">Zero-ETL 물리 그래프 토폴로지 &amp; BigQuery / Spanner 듀얼 DDL 합성기</span>
          </div>
          <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap;">
            <div class="apple-segmented-control">
              <button class="segment-btn active" id="st3-btn-bq" onclick="selectGraphEngine('bigquery')">BigQuery Property Graph (SQL:2023)</button>
              <button class="segment-btn" id="st3-btn-sp" onclick="selectGraphEngine('spanner')">Cloud Spanner Graph (ISO GQL)</button>
            </div>
            <a class="subnav-action-btn" style="text-decoration:none;" href="https://github.com/seanjungG/agentic-ontology-starter/blob/main/methodology/ko/03_stage3_property_graph_ko.md" target="_blank" rel="noopener">방법론 (Stage 3)</a>
            <a class="subnav-action-btn" style="text-decoration:none;" href="https://github.com/seanjungG/agentic-ontology-starter/blob/main/notebooks/ko/stage3_property_graph_bigquery_spanner_ko.ipynb" target="_blank" rel="noopener">노트북 (Stage 3)</a>
            <button class="subnav-action-btn" onclick="openStageMcpModal('mcp_stage3_property_graph')">▶ Stage 3 MCP 실행</button>
          </div>
        </div>

        <div class="split-pane-grid">
          <!-- Left: Interactive vis-network Property Graph -->
          <div class="pane-card">
            <div class="pane-head">
              <span class="pane-title" id="st3-graph-title">물리 Property Graph 토폴로지 (4 DW Nodes + 2 Unstructured Nodes)</span>
              <div style="display:flex; gap:6px; align-items:center;">
                <span class="badge llm">Hub #0d9488 (Teal)</span>
                <span class="badge approved">중복 엔티티 0건</span>
                <button class="subnav-action-btn" style="padding:3px 9px; font-size:11px;" onclick="renderPropertyGraph()">Fit Graph</button>
              </div>
            </div>
            <div class="graph-canvas-box" id="property-graph-canvas"></div>
            <div class="graph-inspector-strip" id="property-graph-inspector">
              <strong>[물리 그래프 노드 인스펙터]</strong> 물리 노드(<code>CustomerContractNode</code>, <code>DeviceNode</code>, <code>PlanNode</code>, <code>SubsidyNode</code> 등)를 클릭하면 Zero-ETL 원장 투영 메타데이터가 표시됩니다.
            </div>
          </div>

          <!-- Right: Dual Engine DDL & GQL Multi-Hop Template Runner -->
          <div class="pane-card">
            <div class="pane-head">
              <span class="pane-title" id="st3-ddl-title">BigQuery ISO SQL:2023 Property Graph DDL (create_property_graph.sql)</span>
              <div style="display:flex; gap:6px; flex-wrap:wrap;">
                <button class="subnav-action-btn" style="padding:3px 10px; font-size:11px;" onclick="copyActiveGraphDdl()">DDL 복사</button>
                <button class="subnav-action-btn" style="padding:3px 10px; font-size:11px; color:var(--apple-blue);" onclick="runSampleGqlTraversal()">▶ 선택 엔진 GQL 실행</button>
                <button class="subnav-action-btn" style="padding:3px 10px; font-size:11px; color:var(--apple-indigo);" onclick="runDualEngineComparison()">▶ 양대 엔진 비교 실행</button>
              </div>
            </div>
            <div class="pane-body" style="display:flex; flex-direction:column; gap:10px;">
              <pre class="code-pre-light" id="st3-ddl-code" style="flex:1; max-height:245px;">-- Loading Property Graph DDL...</pre>
              <div style="background:#f8fafc; border:1px solid #cbd5e1; border-radius:10px; padding:10px 12px; font-size:11.5px; color:#0f172a;" id="st3-benchmark-box">
                <div style="font-weight:800; color:#4f46e5; margin-bottom:4px;">[Dual-Engine Benchmark &amp; Graph Fabric (EXTERNAL_QUERY) Telemetry]</div>
                <div style="color:#475569;">Loading measured BigQuery vs. Cloud Spanner p50/p95 latency and Graph Fabric federation status...</div>
              </div>
              <div style="background:#f0fdfa; border:1px solid #99f6e4; border-radius:10px; padding:10px 12px; font-size:12px; color:#0f172a;" id="st3-gql-result">
                <div style="font-weight:800; color:#0f766e; margin-bottom:4px;">[GQL Multi-Hop Traversal Preview]</div>
                <code>MATCH (c:CustomerContractNode)-[:BOUND_TO_POLICY]->(s:SubsidyNode)-[:REQUIRES_PLAN]->(p:PlanNode)&lt;-[:APPLIES_RULE]-(r:DomainRuleNode)-[:GROUNDED_IN]->(ch:DocChunkNode)</code>
                <div style="margin-top:6px; color:#334155;">우측 상단의 <b>▶ 선택 엔진 GQL 실행</b> 또는 <b>▶ 양대 엔진 비교 실행</b> 버튼을 클릭하면 실시간 멀티홉 탐색 결과를 검증합니다.</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- =================================================================== -->
    <!-- TAB 4: STAGE 4. AGENT & MCP (8 Modular MCPs + AI FDE Console)       -->
    <!-- =================================================================== -->
    <section class="tab-panel" id="panel-stage4">
      <div style="display:flex; flex-direction:column; gap:12px; flex:1; min-height:0;">
        <div id="wb-bar-stage4"></div>
        <div class="fde-native-workspace" style="flex:1; min-height:0;">
        <!-- Left: 8 Core Modular MCP Catalog & Step Runner -->
        <div class="fde-mcp-pane">
          <div class="pane-head">
            <span class="pane-title">8 Core Modular MCP Suite</span>
            <span class="badge indigo">Stage 5 + Runtime 3</span>
          </div>
          <div style="padding:8px 12px; border-bottom:1px solid var(--apple-border-subtle); background:#f8fafc;">
            <div class="apple-segmented-control" style="width:100%; justify-content:space-between;">
              <button class="segment-btn active" id="mcp-flt-all" onclick="filterMcpCatalog('all')">전체 (8)</button>
              <button class="segment-btn" id="mcp-flt-stage" onclick="filterMcpCatalog('stage_pipeline')">Stage MCP (5)</button>
              <button class="segment-btn" id="mcp-flt-runtime" onclick="filterMcpCatalog('runtime_domain')">Runtime MCP (3)</button>
            </div>
          </div>
          <div class="pane-body" id="stage4-mcp-list"></div>
        </div>

        <!-- Right: Interactive AI FDE Reasoning Console -->
        <div class="fde-console-pane">
          <div class="pane-head">
            <div>
              <span class="badge human" id="agent-mode-badge">STAGE 4 · AI FDE ORCHESTRATOR</span>
              <span style="font-size:13.5px; font-weight:800; color:var(--apple-text-primary); margin-left:6px;" id="agent-mode-title">동적 하위 목표 분해 &amp; 결정론적 MCP 체이닝 콘솔</span>
            </div>
            <div style="display:flex; align-items:center; gap:6px; flex-wrap:wrap;">
              <div class="apple-segmented-control">
                <button class="segment-btn active" id="st4-btn-bq" onclick="selectGraphEngine('bigquery')">BigQuery Graph (Default)</button>
                <button class="segment-btn" id="st4-btn-sp" onclick="selectGraphEngine('spanner')">Spanner Graph (Online)</button>
              </div>
              <a class="subnav-action-btn" style="text-decoration:none; padding:3px 9px; font-size:11px;" href="https://github.com/seanjungG/agentic-ontology-starter/blob/main/methodology/ko/04_stage4_agent_and_mcp_ko.md" target="_blank" rel="noopener">방법론 (Stage 4)</a>
              <a class="subnav-action-btn" style="text-decoration:none; padding:3px 9px; font-size:11px;" href="https://github.com/seanjungG/agentic-ontology-starter/blob/main/notebooks/ko/stage4_agent_and_mcp_execution_ko.ipynb" target="_blank" rel="noopener">노트북 (Stage 4)</a>
              <span class="badge approved" id="agent-engine-pill">Engine: BigQuery Graph</span>
            </div>
          </div>

          <div class="quick-chip-bar" id="agent-sample-chips">
            <span style="font-size:11px; font-weight:700; color:var(--apple-text-secondary);">Golden CQ 샘플 질의:</span>
            <span class="quick-chip" onclick="applySample('Galaxy S26 Ultra 256GB를 5G Premier Essential(85,000원)로 개통 시 총 지원금과 실구매가는?')">CQ-02 · 지원금 &amp; 실구매가</span>
            <span class="quick-chip" onclick="applySample('CUST_DEMO_001 고객이 개통 120일 시점에 5G Light(37,000원)로 하향 시 위약금과 근거 앵커는?')">CQ-03 · 120일 일할 위약금 산출</span>
            <span class="quick-chip" onclick="applySample('Galaxy S26 Ultra 256GB 24개월 유지 시 공시지원금과 선택약정 25% 중 유리한 조건 비교해줘')">CQ-04 · 24개월 공시 vs 선약 TCO</span>
            <span class="quick-chip" onclick="applySample('CUST_DEMO_003(시니어 복지 대상) 고객이 개통 88일차에 시니어 요금제로 변경 시 위약금 면제 여부와 그래프 경로 확인해줘')">CQ-05 · 시니어 복지 면제 &amp; 그래프 경로</span>
          </div>

          <div class="console-timeline" id="timeline">
            <div class="trace-card-light">
              <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                <span style="font-weight:800; color:var(--apple-blue);">[AI FDE Reasoning Engine Ready]</span>
                <span class="badge approved">8 Modular MCPs Connected</span>
              </div>
              <p style="font-size:12.5px; color:var(--apple-text-secondary); line-height:1.6;">
                상단의 <b>Golden CQ 샘플 질의 칩</b>을 클릭하거나 아래 입력창에 질문을 입력하면, 에이전트가 질의를 하위 목표로 분해(Step 1)하고 <b>런타임 도메인 MCP 3종</b>(<code>mcp_lookup_customer_profile</code>, <code>mcp_calculate_penalty_rule</code>, <code>mcp_query_graph_and_wiki</code>)을 순차 호출(Step 2)하여 원문 해시 앵커(<code>DOC_CHUNK_001~005</code>)가 결합된 결정론적 응답을 생성합니다.
              </p>
            </div>
          </div>

          <div class="input-dock-light">
            <input type="text" id="query-input" class="query-input-light" placeholder="단말기 지원금, 180일 일할 위약금, 시니어 특례 면제, 그래프 경로 등을 질문해 보세요..." onkeydown="if(event.key==='Enter') sendQuery()">
            <button class="primary-btn" id="send-btn" onclick="sendQuery()">Execute FDE</button>
          </div>
        </div>
        </div>
      </div>
    </section>

    <!-- =================================================================== -->
    <!-- TAB 5: STAGE 5. LINEAGE & EVAL (Lineage DAG + Golden/Boundary)      -->
    <!-- =================================================================== -->
    <section class="tab-panel" id="panel-stage5">
      <div class="ov-scroll-wrap">
        <div id="wb-bar-stage5"></div>
        <div id="st5-track-banner" class="lite-bypass-banner"></div>
        <div class="asset-summary-ribbon">
          <div style="display:flex; align-items:center; gap:10px;">
            <span class="badge approved">STAGE 5 · DATA LINEAGE &amp; CLOSED-LOOP EVALUATION</span>
            <span style="font-size:13.5px; font-weight:700; color:var(--apple-text-primary);">엔드투엔드 데이터 리니지 DAG &amp; Golden CQ / 바운더리 질의 통합 검증 리포트</span>
          </div>
          <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap;">
            <span class="badge human" id="lineage-latency-badge">Lineage Verified</span>
            <a class="subnav-action-btn" style="text-decoration:none;" href="https://github.com/seanjungG/agentic-ontology-starter/blob/main/methodology/ko/05_stage5_lineage_and_eval_ko.md" target="_blank" rel="noopener">방법론 (Stage 5)</a>
            <a class="subnav-action-btn" style="text-decoration:none;" href="https://github.com/seanjungG/agentic-ontology-starter/blob/main/notebooks/ko/stage5_lineage_and_evaluation_ko.ipynb" target="_blank" rel="noopener">노트북 (Stage 5)</a>
            <button class="subnav-action-btn" onclick="openStageMcpModal('mcp_stage5_lineage_and_eval')">▶ Stage 5 MCP 실행</button>
          </div>
        </div>

        <!-- Part A: Enterprise Data Lineage DAG (spec: config/lineage_spec.json) -->
        <div class="ov-card">
          <div class="ov-card-head">
            <span class="ov-eyebrow teal">PART A · ENTERPRISE DATA LINEAGE (CONNECTION &rarr; RAW &rarr; TRANSFORM &rarr; SEMANTIC &rarr; MCP &rarr; AGENT)</span>
          </div>
          <div class="ov-metric-grid" id="lineage-kpis" style="margin-bottom:14px;"></div>
          <div class="lineage-toolbar-island">
            <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap;">
              <span style="font-size:12.5px; font-weight:700;" data-ko="엔터프라이즈 리니지:" data-en="Enterprise Lineage:">엔터프라이즈 리니지:</span>
              <div class="lineage-presets" id="lineage-presets"></div>
              <span class="hdr-meta-badge" id="lineage-node-count">0 Nodes</span>
              <span class="hdr-meta-badge teal" id="lineage-edge-count">0 Edges</span>
              <span class="hdr-meta-badge indigo" id="lineage-cat-count">0 Categories</span>
            </div>
            <div style="display:flex; align-items:center; gap:6px;">
              <button type="button" class="subnav-action-btn lineage-icon-btn" onclick="zoomLineageBy(0.85)" title="Zoom Out">&minus;</button>
              <button type="button" class="subnav-action-btn lineage-icon-btn" onclick="zoomLineageBy(1.18)" title="Zoom In">+</button>
              <button type="button" class="subnav-action-btn lineage-icon-btn" onclick="fitLineageView()" data-ko="맞춤" data-en="Fit">맞춤</button>
              <button type="button" class="subnav-action-btn lineage-icon-btn" onclick="untangleLineageLayout()" data-ko="정렬" data-en="Align">정렬</button>
              <button type="button" class="subnav-action-btn lineage-icon-btn" onclick="resetLineageHighlight(); fetchLineageGraphData();" data-ko="초기화" data-en="Reset">초기화</button>
              <button type="button" class="subnav-action-btn lineage-icon-btn" onclick="toggleLineageLegend()" data-ko="범례" data-en="Legend">범례</button>
            </div>
          </div>
          <div class="lineage-canvas-viewport" id="lineage-viewport">
            <div id="lineage-world-container">
              <svg id="lineage-edges-svg"></svg>
              <div id="lineage-nodes-layer"></div>
            </div>
            <div class="lineage-floating-legend" id="lineage-legend-panel">
              <div class="lineage-legend-hdr"><span data-ko="카테고리 범례" data-en="Legend by color">카테고리 범례</span><span style="cursor:pointer; color:var(--apple-text-secondary);" onclick="toggleLineageLegend()">&times;</span></div>
              <div class="lineage-legend-body" id="lineage-legend-body"></div>
            </div>
            <div class="lineage-minimap-panel" id="lineage-minimap">
              <svg id="lineage-minimap-svg" width="180" height="100"></svg>
              <div class="lineage-minimap-indicator" id="lineage-minimap-indicator"></div>
            </div>
            <aside class="lineage-drawer" id="lineage-drawer">
              <div class="lineage-drawer-header">
                <div class="lineage-drawer-title" id="lineage-drawer-title">Node Inspector</div>
                <button class="lineage-drawer-close" onclick="closeLineageDrawer()" title="Close (Esc)">&times;</button>
              </div>
              <div class="lineage-drawer-body" id="lineage-drawer-body"></div>
            </aside>
          </div>
        </div>

        <!-- Part B: Evaluation KPI & Golden CQ Matrix -->
        <div class="ov-card">
          <div class="ov-card-head">
            <span class="ov-eyebrow">PART B · GOLDEN CQ BENCHMARK SCORECARD (5 GOLDEN CQS)</span>
          </div>
          <h2 class="ov-h2" id="ev-design-title">검증 설계 및 Golden CQ 채점 결과</h2>
          <p class="ov-lead" id="ev-intro"></p>
          <div class="ov-metric-grid" id="ev-kpi-grid" style="margin-bottom:16px;"></div>
          <div id="ev-golden-wrap"></div>
        </div>

        <!-- Part C: 10 Boundary Cases & FDE Remediation -->
        <div class="ov-card">
          <div class="ov-card-head">
            <span class="ov-eyebrow indigo">PART C · BOUNDARY QUESTION EVALUATION (10 CASES &times; N TRIALS, LIVE)</span>
          </div>
          <h2 class="ov-h2">바운더리 질의 10건 실측 평가 (실제 에이전트 반복 실행 · data/input/04_cq/boundary_cases.json 판정 기준)</h2>
          <div id="ev-boundary-wrap" style="margin-bottom:16px;"></div>
          <h3 style="font-size:14px; font-weight:800; margin:14px 0 8px 0; color:var(--apple-text-primary);">실패 원인 4대 분류 (Root Cause Taxonomy) 및 온톨로지 보강 규칙</h3>
          <table class="ov-gap-table">
            <thead><tr><th>분류 코드</th><th>실패 유형</th><th>관찰 신호 (Observed Signal)</th><th>FDE 온톨로지 보강 조치 (Remediation)</th></tr></thead>
            <tbody id="ev-taxonomy-body"></tbody>
          </table>
        </div>
      </div>
    </section>

  </main>

  <input type="file" id="wb-file-input" multiple style="display:none" onchange="handleWorkbenchFileUpload(this.files)">

  <!-- MODAL 1: Stage Pipeline MCP Step Runner -->
  <div class="modal-overlay" id="stage-mcp-modal" onclick="if(event.target===this) closeStageMcpModal()">
    <div class="modal-card">
      <div class="drawer-header">
        <div>
          <div style="font-size:11px; font-weight:800; color:var(--apple-blue);" id="modal-mcp-stage">STAGE PIPELINE MCP RUNNER</div>
          <div style="font-size:16px; font-weight:800; color:var(--apple-text-primary);" id="modal-mcp-title">mcp_stage1_asset_discovery</div>
        </div>
        <button class="subnav-action-btn" onclick="closeStageMcpModal()">✕ 닫기</button>
      </div>
      <div class="drawer-body" style="display:flex; flex-direction:column; gap:14px;">
        <p style="font-size:13px; color:var(--apple-text-secondary);" id="modal-mcp-desc"></p>
        <div>
          <div style="font-size:12px; font-weight:700; color:#1e293b; margin-bottom:8px;">실행할 세부 Step 선택 (복수 선택 가능 · 모듈형 부분 실행):</div>
          <div id="modal-mcp-steps" style="display:flex; gap:8px; flex-wrap:wrap;"></div>
        </div>
        <div style="display:flex; justify-content:flex-end; gap:8px;">
          <button class="primary-btn" style="padding:8px 18px;" onclick="executeModalStageMcp()">▶ 선택한 Step 실행 (Execute Stage MCP)</button>
        </div>
        <pre class="code-pre-light" id="modal-mcp-output">-- Stage MCP 실행 결과가 여기에 JSON으로 출력됩니다.</pre>
      </div>
    </div>
  </div>

  <!-- MODAL 2: Industry Use Cases (8 Enterprises) -->
  <div class="modal-overlay" id="industry-modal" onclick="if(event.target===this) closeIndustryModal()">
    <div class="modal-card">
      <div class="drawer-header">
        <div>
          <div style="font-size:11px; font-weight:800; color:var(--apple-teal);">ENTERPRISE INDUSTRY TEMPLATES</div>
          <div style="font-size:16px; font-weight:800; color:var(--apple-text-primary);">4대 산업군 · 8대 엔터프라이즈 온톨로지 확장 유즈케이스</div>
        </div>
        <button class="subnav-action-btn" onclick="closeIndustryModal()">✕ 닫기</button>
      </div>
      <div class="drawer-body" id="industry-modal-body"></div>
    </div>
  </div>

  <!-- MODAL 3: Track-Driven New Project Creation & GCP Resource Recommender (GRILL-011) -->
  <div class="modal-overlay" id="new-project-modal" onclick="if(event.target===this) closeNewProjectModal()">
    <div class="modal-card" style="width:min(820px, 94vw);">
      <div class="drawer-header">
        <div>
          <div style="font-size:11px; font-weight:800; color:var(--apple-blue);">TRACK-DRIVEN PROJECT CREATOR &amp; GCP RESOURCE RECOMMENDER</div>
          <div style="font-size:16px; font-weight:800; color:var(--apple-text-primary);">선택한 트랙 기반으로 신규 프로젝트 생성 &amp; Step-by-Step Gemini 워크벤치 시작</div>
        </div>
        <button class="subnav-action-btn" onclick="closeNewProjectModal()">✕ 닫기</button>
      </div>
      <div class="drawer-body" style="display:flex; flex-direction:column; gap:14px;">
        <p style="font-size:12.5px; color:#334155; line-height:1.55;">
          선택한 트랙(Track 1 Lite / Track 2 Standard / Track 3 Full-Stack)과 그래프 엔진에 맞춰 <b>GCP 리소스 이름(BigQuery 데이터셋, GCS 위키 경로, Property Graph 이름)</b>을 자동 추천하고, 생성 즉시 각 Stage 탭 상단 워크벤치에서 <b>데이터 업로드 &rarr; 최신 Gemini 변환 &rarr; 단계별 승인(GCP 반영)</b>을 수행합니다.
        </p>
        <div class="np-form-grid">
          <div class="np-field">
            <label>프로젝트 ID (소문자·하이픈, 예: retail-vip-demo)</label>
            <input type="text" id="np-project-id" class="np-input" value="retail-vip-demo" oninput="refreshNewProjectGcpRecommendations()">
          </div>
          <div class="np-field">
            <label>프로젝트 표시 이름 (Project Name)</label>
            <input type="text" id="np-project-name" class="np-input" value="리테일 VIP 멤버십 & 풀필먼트 온톨로지">
          </div>
          <div class="np-field">
            <label>비즈니스 도메인 설명 (Domain)</label>
            <input type="text" id="np-domain" class="np-input" value="Retail Omnichannel Membership & SLA">
          </div>
          <div class="np-field">
            <label>온톨로지 트랙 선택 (Track 1 / 2 / 3)</label>
            <select id="np-track" class="np-input" onchange="onNewProjectTrackChange()">
              <option value="lite">Track 1 · Lite Path (Stage 1→2→4 · 문서 전용, 그래프 생략)</option>
              <option value="standard">Track 2 · Standard Path (Stage 1→2→3→4 · 문서 + DW 그래프)</option>
              <option value="full" selected>Track 3 · Full-Stack Path (Stage 1→5 · 그래프 + 엔드투엔드 리니지)</option>
            </select>
          </div>
          <div class="np-field">
            <label>물리 그래프 엔진 (Stage 3 Graph Engine)</label>
            <select id="np-engine" class="np-input" onchange="refreshNewProjectGcpRecommendations()">
              <option value="bigquery" selected>BigQuery Property Graph (ISO SQL:2023 · 기본)</option>
              <option value="spanner">Cloud Spanner Graph (ISO GQL · OLTP 저지연)</option>
              <option value="both">Dual-Engine Graph Fabric (BigQuery + Spanner EXTERNAL_QUERY)</option>
              <option value="none">No Physical Graph (Track 1 Lite 전용)</option>
            </select>
          </div>
          <div class="np-field">
            <label>Vertex AI Gemini 변환/추론 모델 (Latest Gemini Model)</label>
            <select id="np-model" class="np-input">
              <option value="gemini-3.8-flash" selected>gemini-3.8-flash (Recommended · 고속/고정밀 시맨틱 합성)</option>
              <option value="gemini-3.1-pro-preview">gemini-3.1-pro-preview (Deep Reasoning Preview)</option>
              <option value="gemini-2.5-pro">gemini-2.5-pro (Enterprise Pro Stable)</option>
            </select>
          </div>
        </div>

        <div style="background:#f0f7ff; border:1px solid #bfdbfe; border-radius:12px; padding:12px 14px;">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
            <span style="font-size:12px; font-weight:800; color:#1d4ed8;">[GCP 리소스 이름 자동 추천 (Auto-Recommended GCP Resource Names · 수정 가능)]</span>
            <span class="badge approved" id="np-gcp-badge">Auto-Named</span>
          </div>
          <div class="np-form-grid">
            <div class="np-field">
              <label>GCP Project ID</label>
              <input type="text" id="np-gcp-project" class="np-input" value="seanjung-poc">
            </div>
            <div class="np-field">
              <label>BigQuery Dataset ID (Stage 1 승인 시 자동 생성·적재)</label>
              <input type="text" id="np-bq-dataset" class="np-input" value="retail_vip_demo_dw">
            </div>
            <div class="np-field">
              <label>GCS Wiki Bucket (Stage 2 승인 시 `projects/&lt;id&gt;/ontology/` 업로드)</label>
              <input type="text" id="np-gcs-bucket" class="np-input" value="seanjung-poc-starter-ontology">
            </div>
            <div class="np-field">
              <label>Property Graph Name (Stage 3 승인 시 SQL:2023 DDL 배포)</label>
              <input type="text" id="np-graph-name" class="np-input" value="RETAIL_VIP_DEMO_ONTOLOGY_GRAPH">
            </div>
          </div>
        </div>

        <label style="display:flex; align-items:center; gap:8px; font-size:12.5px; font-weight:700; color:#0f172a; cursor:pointer;">
          <input type="checkbox" id="np-seed-sample" checked>
          <span>초기 테스트용 도메인 샘플 문서(`membership_policy_guide.md`) 및 정형 CSV 테이블(`tb_memberships.csv`, `tb_tier_plans.csv`) 함께 시드 (생성 후 다른 파일 추가 업로드 가능)</span>
        </label>

        <div id="np-status-msg" style="font-size:12px; color:#0369a1; display:none;"></div>

        <div style="display:flex; justify-content:flex-end; gap:8px;">
          <button class="subnav-action-btn" onclick="closeNewProjectModal()">취소</button>
          <button class="wb-btn-approve" id="np-submit-btn" onclick="submitCreateNewProject()">+ 프로젝트 생성 및 Stage 1 워크벤치로 이동</button>
        </div>
      </div>
    </div>
  </div>

<script>
  let studioLang = 'ko';
  let activeTrack = 'full';
  let activeGraphEngine = 'bigquery';
  let globalAssets = null;
  let globalGraph = null;
  let globalCatalog = [];
  let stage1Filter = 'all';
  let mcpFilter = 'all';
  let currentModalTool = null;
  let semanticNet = null;
  let propertyNet = null;

  function esc(s) { return (s === null || s === undefined) ? '' : String(s); }

  // 0. Project context: config/project.json (sample) + projects/<id>/project.json. Every /api call carries ?project=.
  let activeProject = new URLSearchParams(location.search).get('project') || '';
  let projectList = [];
  const nativeFetch = window.fetch.bind(window);
  window.fetch = (url, opts) => {
    if (activeProject && typeof url === 'string' && url.startsWith('/api/')) {
      url += (url.includes('?') ? '&' : '?') + 'project=' + encodeURIComponent(activeProject);
    }
    return nativeFetch(url, opts);
  };

  async function loadProjects() {
    projectList = await (await nativeFetch('/api/projects')).json();
    if (!projectList.some(p => p.project_id === activeProject)) activeProject = (projectList[0] || {}).project_id || '';
    const sel = document.getElementById('hdr-project-select');
    sel.innerHTML = projectList.map(p => `<option value="${esc(p.project_id)}">${esc(p.project_name || p.project_id)}</option>`).join('');
    sel.value = activeProject;
    applyProjectMeta();
  }

  let workbenchState = null;
  let pendingUploadKind = 'auto';

  function applyProjectMeta() {
    const p = projectList.find(x => x.project_id === activeProject) || {};
    const qs = new URLSearchParams(location.search);
    const qsPreset = qs.get('preset');
    const qsEngine = qs.get('engine');
    if (qsPreset && ['lite', 'standard', 'full', 'fabric'].includes(qsPreset)) {
      selectPathPreset(qsPreset);
    } else {
      selectTrack(p.track || 'full');
      selectGraphEngine(p.track === 'lite' ? 'none' : (p.graph_engine || 'bigquery'));
    }
    if (qsEngine && ['none', 'bigquery', 'spanner', 'both'].includes(qsEngine)) {
      selectGraphEngine(qsEngine);
    }
    if (qs.get('scroll') === 'pkg') {
      setTimeout(() => {
        const el = document.getElementById('ov-assembled-package-card');
        if (el) el.scrollIntoView({ behavior: 'instant', block: 'start' });
      }, 200);
    }
    syncTabsWithTrack();
  }

  function switchProject(id) {
    activeProject = id;
    document.getElementById('hdr-project-select').value = id;
    const u = new URL(location.href);
    u.searchParams.set('project', id);
    history.replaceState(null, '', u);
    globalAssets = null; globalGraph = null; globalCatalog = []; lineageGraph = null; lineageActiveTrace = null;
    closeLineageDrawer();
    applyProjectMeta();
    loadPortalProfile();
    loadCatalog();
    loadWorkbenchState();
    const active = document.querySelector('#main-tab-ribbon .view-mode-pill.active');
    switchTab(active ? active.getAttribute('data-tab') : 'overview');
  }

  // 1. Tab Routing (Supports 6 Primary Stage Tabs + Legacy Deep-Link Aliases)
  const TAB_ALIAS_MAP = {
    'overview': 'overview',
    'stage1': 'stage1', 'assets': 'stage1',
    'stage2': 'stage2', 'okf': 'stage2',
    'stage3': 'stage3', 'structured': 'stage3', 'graph': 'stage3',
    'stage4': 'stage4', 'wiki-agent': 'stage4', 'bqg-agent': 'stage4', 'fde': 'stage4',
    'stage5': 'stage5', 'lineage': 'stage5', 'evaluation': 'stage5', 'cq': 'stage5'
  };

  function switchTab(rawTabId) {
    const tabId = TAB_ALIAS_MAP[rawTabId] || 'overview';
    document.querySelectorAll('#main-tab-ribbon .view-mode-pill').forEach(btn => {
      btn.classList.toggle('active', btn.getAttribute('data-tab') === tabId);
    });
    document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
    const panel = document.getElementById('panel-' + tabId);
    if (panel) panel.classList.add('active');

    renderWorkbenchBars();
    if (tabId === 'stage1') ensureAssetsLoaded(() => renderStage1Assets());
    if (tabId === 'stage2') {
      ensureAssetsLoaded(() => showWikiDoc('summary.md', 'wtab-summary'));
      ensureGraphLoaded(() => setTimeout(renderSemanticGraph, 60));
    }
    if (tabId === 'stage3') {
      ensureGraphLoaded(() => {
        updateStage3DdlView();
        setTimeout(renderPropertyGraph, 60);
      });
    }
    if (tabId === 'stage4') {
      if (!globalCatalog.length) loadCatalog();
    }
    if (tabId === 'stage5') {
      loadLineageAndEvaluation();
    }
  }

  // 2. Bilingual KOR / ENG Switch
  function setStudioLanguage(lang) {
    studioLang = (lang === 'en') ? 'en' : 'ko';
    document.getElementById('lang-btn-ko').classList.toggle('active', studioLang === 'ko');
    document.getElementById('lang-btn-en').classList.toggle('active', studioLang === 'en');
    document.querySelectorAll('[data-ko]').forEach(el => {
      const txt = el.getAttribute(studioLang === 'en' ? 'data-en' : 'data-ko');
      if (txt) el.innerHTML = txt;
    });
    if (globalGraph) {
      renderSemanticGraph();
      renderPropertyGraph();
    }
    if (globalCatalog.length) renderMcpCatalog();
    if (lineageGraph) {
      renderLineageAll();
      if (lineageActiveTrace) selectLineageNode(lineageActiveTrace.selected_node.id);
    }
    renderOverviewPathBuilder();
    syncTabsWithTrack();
    renderWorkbenchBars();
  }

  // 3. Interactive Path Map & Starter Pack Package Builder State (GOAL-158)
  let portalOverviewCache = null;
  let pkgBuilderState = {
    preset: 'full',          // 'lite' | 'standard' | 'full' | 'fabric' | 'custom'
    input: 'doc_dw',         // 'doc_only' | 'doc_dw'
    wiki: 'okf_3layer',      // 'chunks' | 'okf_3layer'
    engine: 'bigquery',      // 'none' | 'bigquery' | 'spanner' | 'both'
    runtime: 'mcp_8tools',   // 'lite_agent' | 'mcp_8tools'
    eval: 'full_lineage_boundary' // 'golden_only' | 'full_lineage_boundary'
  };

  function syncTabsWithTrack() {
    const isLite = (activeTrack === 'lite');
    const isFull = (activeTrack === 'full');
    const btn3 = document.getElementById('tab-btn-stage3');
    const btn5 = document.getElementById('tab-btn-stage5');
    if (btn3) {
      btn3.innerHTML = isLite
        ? `Stage 3. Property Graph <span style="font-size:10px; background:#fef3c7; color:#b45309; padding:1px 6px; border-radius:999px; margin-left:4px;">Lite 생략</span>`
        : `Stage 3. Property Graph`;
      btn3.style.opacity = isLite ? '0.68' : '1';
    }
    if (btn5) {
      btn5.innerHTML = isFull
        ? `Stage 5. Lineage &amp; Eval`
        : `Stage 5. Lineage &amp; Eval <span style="font-size:10px; background:#e0f2fe; color:#0369a1; padding:1px 6px; border-radius:999px; margin-left:4px;">Golden CQ</span>`;
    }
    const b3 = document.getElementById('st3-lite-bypass-banner');
    if (b3) {
      b3.style.display = isLite ? 'flex' : 'none';
      if (isLite) {
        b3.innerHTML = `
          <div>
            <div style="font-size:12.5px; font-weight:800; color:#92400e;">[Track 1 · Lite Path (Stage 1 &rarr; 2 &rarr; 4) 물리 그래프 생략 안내]</div>
            <div style="font-size:12px; color:#78350f; margin-top:2px;">현재 프로젝트는 <b>Track 1 (Lite · 문서 전용)</b> 모드로 설정되어 있어 물리 Property Graph(Stage 3)를 생성하지 않고 Stage 2 위키/청크에서 Stage 4 에이전트로 바로 연결됩니다. 정형 CSV 원장과 물리 그래프를 함께 사용하려면 Track 2(Standard) 또는 Track 3(Full-Stack)로 전환하세요.</div>
          </div>
          <div style="display:flex; gap:8px;">
            <button class="wb-btn-run" onclick="switchTab('stage4')">Stage 4 에이전트로 바로 이동 &rarr;</button>
            <button class="wb-btn-approve" onclick="selectTrack('standard'); applyTrackToCurrentProject();">Track 2 (Standard · 물리 그래프 활성)로 즉시 전환</button>
          </div>
        `;
      }
    }
    const b5 = document.getElementById('st5-track-banner');
    if (b5) {
      b5.style.display = (!isFull) ? 'flex' : 'none';
      if (!isFull) {
        b5.innerHTML = `
          <div>
            <div style="font-size:12.5px; font-weight:800; color:#92400e;">[${activeTrack === 'lite' ? 'Track 1 · Lite' : 'Track 2 · Standard'} — Golden CQ 핵심 검증 모드]</div>
            <div style="font-size:12px; color:#78350f; margin-top:2px;">현재 트랙에서는 도메인 <b>Golden CQ 정확도 및 해시 앵커 인용 검증(Part B)</b>을 기본 수행하며, 엔드투엔드 리니지 DAG 및 50-Trial 바운더리 회귀 벤치마크 전체 활성화는 Track 3(Full-Stack)에서 지원됩니다.</div>
          </div>
          <button class="wb-btn-run" onclick="selectTrack('full'); applyTrackToCurrentProject();">Track 3 (Full-Stack)로 전환</button>
        `;
      }
    }
  }

  function syncTrackAndEngineBadges() {
    const isLite = (pkgBuilderState.engine === 'none' || pkgBuilderState.input === 'doc_only');
    const isFull = (!isLite && pkgBuilderState.eval === 'full_lineage_boundary');
    activeTrack = isLite ? 'lite' : (isFull ? 'full' : 'standard');
    activeGraphEngine = (pkgBuilderState.engine === 'spanner') ? 'spanner' : 'bigquery';

    const trackLabels = {
      'lite': 'Track 1 · Lite (1→2→4)',
      'standard': 'Track 2 · Standard (1→2→3→4)',
      'full': 'Track 3 · Full-Stack (1→5)'
    };
    const hdrTrack = document.getElementById('hdr-track-badge');
    if (hdrTrack) hdrTrack.textContent = trackLabels[activeTrack] || trackLabels.full;

    const engLabels = {
      'none': 'No Physical Graph (Lite Bypass)',
      'bigquery': 'BigQuery Property Graph',
      'spanner': 'Cloud Spanner Graph (ISO GQL)',
      'both': 'Dual Graph Fabric (BQ + Spanner)'
    };
    const hdrEng = document.getElementById('hdr-engine-badge');
    if (hdrEng) hdrEng.textContent = engLabels[pkgBuilderState.engine] || engLabels.bigquery;

    const agPill = document.getElementById('agent-engine-pill');
    if (agPill) agPill.textContent = 'Engine: ' + (pkgBuilderState.engine === 'spanner' ? 'Spanner Graph' : (pkgBuilderState.engine === 'both' ? 'Dual Fabric (BQ+Spanner)' : (pkgBuilderState.engine === 'none' ? 'Lite Doc Citation' : 'BigQuery Graph')));

    document.querySelectorAll('#ov-track-selector .segment-btn').forEach((b, idx) => {
      const k = ['lite', 'standard', 'full'][idx];
      b.classList.toggle('active', k === activeTrack);
    });
    document.querySelectorAll('#ov-engine-selector .segment-btn').forEach((b, idx) => {
      const k = ['bigquery', 'spanner', 'both', 'none'][idx];
      b.classList.toggle('active', k === pkgBuilderState.engine);
    });
    ['st3', 'st4'].forEach(prefix => {
      const bqBtn = document.getElementById(prefix + '-btn-bq');
      const spBtn = document.getElementById(prefix + '-btn-sp');
      if (bqBtn && spBtn) {
        bqBtn.classList.toggle('active', activeGraphEngine === 'bigquery');
        spBtn.classList.toggle('active', activeGraphEngine === 'spanner');
      }
    });
    syncTabsWithTrack();
    if (globalGraph) updateStage3DdlView();
  }

  function selectPathPreset(presetKey) {
    if (presetKey === 'lite') {
      pkgBuilderState = { preset: 'lite', input: 'doc_only', wiki: 'okf_3layer', engine: 'none', runtime: 'lite_agent', eval: 'golden_only' };
    } else if (presetKey === 'standard') {
      const eng = (pkgBuilderState.engine === 'spanner') ? 'spanner' : 'bigquery';
      pkgBuilderState = { preset: 'standard', input: 'doc_dw', wiki: 'okf_3layer', engine: eng, runtime: 'mcp_8tools', eval: 'golden_only' };
    } else if (presetKey === 'fabric') {
      pkgBuilderState = { preset: 'fabric', input: 'doc_dw', wiki: 'okf_3layer', engine: 'both', runtime: 'mcp_8tools', eval: 'full_lineage_boundary' };
    } else {
      const eng = (pkgBuilderState.engine === 'spanner') ? 'spanner' : 'bigquery';
      pkgBuilderState = { preset: 'full', input: 'doc_dw', wiki: 'okf_3layer', engine: eng, runtime: 'mcp_8tools', eval: 'full_lineage_boundary' };
    }
    syncTrackAndEngineBadges();
    renderOverviewPathBuilder();
  }

  function selectBuilderItem(category, optKey) {
    pkgBuilderState[category] = optKey;
    if (category === 'input' && optKey === 'doc_only') {
      pkgBuilderState.engine = 'none';
      pkgBuilderState.runtime = 'lite_agent';
    } else if (category === 'input' && optKey === 'doc_dw') {
      if (pkgBuilderState.engine === 'none') pkgBuilderState.engine = 'bigquery';
      pkgBuilderState.runtime = 'mcp_8tools';
    } else if (category === 'engine') {
      if (optKey === 'none') {
        pkgBuilderState.runtime = 'lite_agent';
      } else {
        pkgBuilderState.input = 'doc_dw';
        pkgBuilderState.runtime = 'mcp_8tools';
      }
    } else if (category === 'runtime') {
      if (optKey === 'lite_agent') {
        pkgBuilderState.engine = 'none';
      } else if (pkgBuilderState.engine === 'none') {
        pkgBuilderState.input = 'doc_dw';
        pkgBuilderState.engine = 'bigquery';
      }
    }
    // Determine matching preset label
    if (pkgBuilderState.engine === 'none') {
      pkgBuilderState.preset = 'lite';
    } else if (pkgBuilderState.engine === 'both') {
      pkgBuilderState.preset = 'fabric';
    } else if (pkgBuilderState.eval === 'full_lineage_boundary') {
      pkgBuilderState.preset = 'full';
    } else {
      pkgBuilderState.preset = 'standard';
    }
    syncTrackAndEngineBadges();
    renderOverviewPathBuilder();
  }

  function selectTrack(trackKey) {
    if (trackKey === 'lite') selectPathPreset('lite');
    else if (trackKey === 'standard') selectPathPreset('standard');
    else selectPathPreset('full');
  }

  function selectGraphEngine(engineKey) {
    if (engineKey === 'none') {
      selectBuilderItem('engine', 'none');
    } else if (engineKey === 'both') {
      selectBuilderItem('engine', 'both');
    } else {
      selectBuilderItem('engine', engineKey === 'spanner' ? 'spanner' : 'bigquery');
    }
  }

  function copyPackageCli() {
    const pre = document.getElementById('ov-pkg-cli-code');
    if (!pre) return;
    navigator.clipboard.writeText(pre.textContent || '');
    const btn = document.getElementById('ov-pkg-cli-copy-btn');
    if (btn) {
      const orig = btn.textContent;
      btn.textContent = studioLang === 'en' ? 'Copied!' : '복사 완료!';
      setTimeout(() => { btn.textContent = orig; }, 1400);
    }
  }

  function renderOverviewPathBuilder() {
    const isEn = (studioLang === 'en');
    const st = pkgBuilderState;
    const isStage3Active = (st.engine !== 'none');
    const isStage5Full = (st.eval === 'full_lineage_boundary');

    // 1. Render 4 Quick Path Presets
    const presets = [
      {
        id: 'lite',
        tag: 'TRACK 1 · LITE PATH',
        title: isEn ? 'Document-Only Fast Path' : '문서 중심 빠른 시작 (Lite 패스)',
        route: 'Stage 1 ➔ Stage 2 ──(Stage 3 생략)──▶ Stage 4',
        desc: isEn
          ? 'Guides/PDFs only · Skip physical graph · Direct 3-Layer Wiki & SHA-256 chunk citation'
          : '비정형 약관/문서 단독 · 물리 그래프(Stage 3) 생략 · 원문 청크/3-Layer 위키 직접 인용 추론'
      },
      {
        id: 'standard',
        tag: 'TRACK 2 · STANDARD PATH',
        title: isEn ? 'Single Graph Engine Path' : '정형+비정형 표준 그래프 (Standard 패스)',
        route: 'Stage 1 ➔ Stage 2 ➔ Stage 3 (BQ/Spanner) ➔ Stage 4',
        desc: isEn
          ? 'DW tables + Policy guides · Zero-ETL BigQuery or Spanner Graph · 8 Modular MCPs'
          : '정형 DW 원장 + 정책 문서 · 단일 물리 그래프(BigQuery 기본 / Spanner 선택) + 8대 MCP 추론'
      },
      {
        id: 'full',
        tag: 'TRACK 3 · FULL-STACK PATH',
        title: isEn ? 'Enterprise Governance Full-Stack' : '엔터프라이즈 거버넌스 풀스택 (Full 패스)',
        route: 'Stage 1 ➔ Stage 2 ➔ Stage 3 ➔ Stage 4 ➔ Stage 5',
        desc: isEn
          ? 'All 5 Stages · Physical Graph + End-to-End Lineage DAG + 50-Trial Boundary Regression'
          : 'Stage 1~5 전 구간 · 물리 그래프 + 엔드투엔드 리니지 DAG + 바운더리 50회 회귀 평가'
      },
      {
        id: 'fabric',
        tag: 'DUAL-ENGINE FABRIC PATH',
        title: isEn ? 'BigQuery + Spanner Graph Fabric' : 'BigQuery + Spanner 듀얼 패브릭 통합',
        route: 'Stage 1 ➔ 2 ➔ 3 (BQ + Spanner EXTERNAL_QUERY) ➔ 4 ➔ 5',
        desc: isEn
          ? 'Simultaneous OLAP (BigQuery) + OLTP (Spanner 100 PU) graph with EXTERNAL_QUERY join'
          : 'OLAP(BigQuery) + OLTP(Spanner 100 PU) 동시 구축 및 EXTERNAL_QUERY 연합 조인 풀스택'
      }
    ];
    const presetGrid = document.getElementById('ov-preset-grid');
    if (presetGrid) {
      presetGrid.innerHTML = presets.map(p => `
        <div class="ov-preset-card ${st.preset === p.id ? 'active' : ''}" onclick="selectPathPreset('${p.id}')">
          <div class="ov-preset-top">
            <span class="ov-preset-tag">${esc(p.tag)}</span>
            <span style="font-size:11px; font-weight:800; color:${st.preset === p.id ? 'var(--apple-blue)' : '#64748b'};">
              ${st.preset === p.id ? (isEn ? '● ACTIVE PATH' : '● 현재 선택 패스') : (isEn ? '○ Select Preset' : '○ 패스 선택')}
            </span>
          </div>
          <div class="ov-preset-title">${esc(p.title)}</div>
          <div class="ov-preset-route">${esc(p.route)}</div>
          <div class="ov-preset-desc">${esc(p.desc)}</div>
        </div>
      `).join('');
    }

    // 2. Render Visual Route Diagram Bar (SVG + Route Indicator)
    const routeBar = document.getElementById('ov-route-diagram-bar');
    if (routeBar) {
      const liteColor = !isStage3Active ? '#059669' : '#cbd5e1';
      const liteDash = !isStage3Active ? '' : 'stroke-dasharray="6,5"';
      const mainColor = isStage3Active ? '#4f46e5' : '#cbd5e1';
      const mainDash = isStage3Active ? '' : 'stroke-dasharray="6,5"';
      const st5Color = isStage5Full ? '#db2777' : '#0284c7';
      const st3Label = st.engine === 'none'
        ? (isEn ? 'BYPASSED (Lite Direct)' : '생략됨 (Lite 직행)')
        : (st.engine === 'both' ? 'Dual Fabric (BQ+Spanner)' : (st.engine === 'spanner' ? 'Spanner Graph (100 PU)' : 'BigQuery Graph (Default)'));
      const st5Label = isStage5Full
        ? (isEn ? 'End-to-End Lineage + 50-Trial Eval' : '엔드투엔드 리니지 + 50회 경계평가')
        : (isEn ? 'Golden CQ Basic Check' : 'Golden CQ 기본 점검');

      routeBar.innerHTML = `
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
          <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap;">
            <span class="badge human" style="font-weight:800;">${isEn ? 'ACTIVE ARCHITECTURE ROUTE' : '현재 활성 아키텍처 경로'}</span>
            <span style="font-size:13px; font-weight:800; color:#0f172a;">
              ${!isStage3Active
                ? (isEn ? 'Track 1 · Lite Bypass Route: Stage 1 (Docs) ➔ Stage 2 (Wiki/Chunks) ──[Skip Stage 3]──▶ Stage 4 (Lite Agent) ➔ Stage 5 (CQ Check)' : 'Track 1 · Lite 우회 경로: Stage 1 (문서) ➔ Stage 2 (위키/청크) ──[Stage 3 물리 그래프 생략]──▶ Stage 4 (Lite 에이전트) ➔ Stage 5 (CQ 점검)')
                : (isStage5Full
                    ? (isEn ? `Track 3 · Full-Stack Route: Stage 1 ➔ Stage 2 ➔ Stage 3 (${st3Label}) ➔ Stage 4 (8 MCPs) ➔ Stage 5 (Full Lineage & Boundary)` : `Track 3 · Full-Stack 정식 경로: Stage 1 ➔ Stage 2 ➔ Stage 3 (${st3Label}) ➔ Stage 4 (8대 MCP) ➔ Stage 5 (엔드투엔드 리니지 & 경계평가)`)
                    : (isEn ? `Track 2 · Standard Route: Stage 1 ➔ Stage 2 ➔ Stage 3 (${st3Label}) ➔ Stage 4 (8 MCPs) ➔ Stage 5 (Golden CQ)` : `Track 2 · Standard 표준 경로: Stage 1 ➔ Stage 2 ➔ Stage 3 (${st3Label}) ➔ Stage 4 (8대 MCP) ➔ Stage 5 (Golden CQ 검증)`))}
            </span>
          </div>
          <span style="font-size:11.5px; color:#475569;">
            ${isEn ? 'Click any Stage node or option card below to customize your Starter Pack package' : '아래 다이어그램의 노드 또는 각 Stage 카드를 클릭하면 스타터팩 패키지가 즉시 재조립됩니다'}
          </span>
        </div>
        <svg viewBox="0 0 1200 108" style="width:100%; height:104px; display:block; overflow:visible;">
          <defs>
            <marker id="arr-blue" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
              <path d="M 0 1 L 8 5 L 0 9 z" fill="#0284c7"/>
            </marker>
            <marker id="arr-emerald" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
              <path d="M 0 1 L 8 5 L 0 9 z" fill="${liteColor}"/>
            </marker>
            <marker id="arr-indigo" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
              <path d="M 0 1 L 8 5 L 0 9 z" fill="${mainColor}"/>
            </marker>
            <marker id="arr-pink" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
              <path d="M 0 1 L 8 5 L 0 9 z" fill="${st5Color}"/>
            </marker>
          </defs>

          <!-- Stage 1 -> Stage 2 Always Active -->
          <line x1="205" y1="68" x2="275" y2="68" stroke="#0284c7" stroke-width="3" marker-end="url(#arr-blue)"/>

          <!-- Top Arc: Track 1 Lite Bypass (Stage 2 -> Stage 4 skipping Stage 3) -->
          <path d="M 390 42 C 470 4, 730 4, 810 42" fill="none" stroke="${liteColor}" stroke-width="${!isStage3Active ? '3' : '1.8'}" ${liteDash} marker-end="url(#arr-emerald)"/>
          <g style="cursor:pointer;" onclick="selectPathPreset('lite')">
            <rect x="455" y="2" width="290" height="22" rx="11" fill="${!isStage3Active ? '#ecfdf5' : '#f8fafc'}" stroke="${liteColor}" stroke-width="1.5"/>
            <text x="600" y="17" text-anchor="middle" font-size="11" font-weight="800" fill="${!isStage3Active ? '#047857' : '#64748b'}" font-family="Pretendard, sans-serif">
              ${!isStage3Active ? (isEn ? '★ ACTIVE: Track 1 Lite Direct Bridge (Stage 3 Bypassed)' : '★ 활성 패스: Track 1 Lite 직행 브릿지 (Stage 3 그래프 생략)') : (isEn ? 'Track 1 Lite Bypass Route (Click to skip Stage 3)' : 'Track 1 Lite 우회 경로 (클릭 시 Stage 3 생략)')}
            </text>
          </g>

          <!-- Main Route: Stage 2 -> Stage 3 -> Stage 4 -->
          <line x1="465" y1="68" x2="515" y2="68" stroke="${mainColor}" stroke-width="${isStage3Active ? '3' : '1.8'}" ${mainDash} marker-end="url(#arr-indigo)"/>
          <line x1="695" y1="68" x2="745" y2="68" stroke="${mainColor}" stroke-width="${isStage3Active ? '3' : '1.8'}" ${mainDash} marker-end="url(#arr-indigo)"/>

          <!-- Stage 4 -> Stage 5 -->
          <line x1="935" y1="68" x2="985" y2="68" stroke="${st5Color}" stroke-width="${isStage5Full ? '3' : '2.2'}" ${isStage5Full ? '' : 'stroke-dasharray="5,4"'} marker-end="url(#arr-pink)"/>

          <!-- Node 1: Stage 1 -->
          <g style="cursor:pointer;" onclick="switchTab('stage1')">
            <rect x="15" y="42" width="190" height="52" rx="10" fill="#eff6ff" stroke="#3b82f6" stroke-width="2"/>
            <text x="110" y="62" text-anchor="middle" font-size="11" font-weight="800" fill="#1d4ed8">STAGE 1 · ASSET &amp; GATE 0</text>
            <text x="110" y="80" text-anchor="middle" font-size="11.5" font-weight="700" fill="#0f172a">${st.input === 'doc_only' ? (isEn ? 'Docs Only (PDF/MD)' : '비정형 문서 단독') : (isEn ? '4 DW CSVs + 2 Guides' : '정형 원장 + 정책 문서')}</text>
          </g>

          <!-- Node 2: Stage 2 -->
          <g style="cursor:pointer;" onclick="switchTab('stage2')">
            <rect x="275" y="42" width="190" height="52" rx="10" fill="#f0fdfa" stroke="#0d9488" stroke-width="2"/>
            <text x="370" y="62" text-anchor="middle" font-size="11" font-weight="800" fill="#0f766e">STAGE 2 · WIKI &amp; SEMANTIC</text>
            <text x="370" y="80" text-anchor="middle" font-size="11.5" font-weight="700" fill="#0f172a">${st.wiki === 'chunks' ? (isEn ? 'SHA-256 Chunks Only' : 'SHA-256 해시 청크 인용') : (isEn ? '3-Layer Wiki + JSON-LD' : '3-Layer Wiki + 시맨틱')}</text>
          </g>

          <!-- Node 3: Stage 3 -->
          <g style="cursor:pointer;" onclick="switchTab('stage3')">
            <rect x="515" y="42" width="180" height="52" rx="10" fill="${isStage3Active ? '#eef2ff' : '#f1f5f9'}" stroke="${isStage3Active ? '#4f46e5' : '#94a3b8'}" stroke-width="2" ${isStage3Active ? '' : 'stroke-dasharray="5,4"'}/>
            <text x="605" y="62" text-anchor="middle" font-size="11" font-weight="800" fill="${isStage3Active ? '#4338ca' : '#64748b'}">STAGE 3 · PROPERTY GRAPH</text>
            <text x="605" y="80" text-anchor="middle" font-size="11.5" font-weight="700" fill="${isStage3Active ? '#0f172a' : '#64748b'}">${esc(st3Label)}</text>
          </g>

          <!-- Node 4: Stage 4 -->
          <g style="cursor:pointer;" onclick="switchTab('stage4')">
            <rect x="745" y="42" width="190" height="52" rx="10" fill="#f5f3ff" stroke="#7c3aed" stroke-width="2"/>
            <text x="840" y="62" text-anchor="middle" font-size="11" font-weight="800" fill="#6d28d9">STAGE 4 · AGENT &amp; MCP</text>
            <text x="840" y="80" text-anchor="middle" font-size="11.5" font-weight="700" fill="#0f172a">${st.runtime === 'lite_agent' ? (isEn ? 'Lite Doc Citation Agent' : 'Lite 청크 인용 에이전트') : (isEn ? '8 Modular MCP Suite' : '8대 모듈형 MCP 스위트')}</text>
          </g>

          <!-- Node 5: Stage 5 -->
          <g style="cursor:pointer;" onclick="switchTab('stage5')">
            <rect x="985" y="42" width="200" height="52" rx="10" fill="${isStage5Full ? '#fdf2f8' : '#f0f9ff'}" stroke="${st5Color}" stroke-width="2"/>
            <text x="1085" y="62" text-anchor="middle" font-size="11" font-weight="800" fill="${isStage5Full ? '#be185d' : '#0369a1'}">STAGE 5 · LINEAGE &amp; EVAL</text>
            <text x="1085" y="80" text-anchor="middle" font-size="11.5" font-weight="700" fill="#0f172a">${esc(st5Label)}</text>
          </g>
        </svg>
      `;
    }

    // 3. Render 5-Column Clickable Building Blocks (#ov-map-cols)
    const columnsSpec = [
      {
        stage: 'STAGE 1',
        tab: 'stage1',
        accent: '#3b82f6',
        bypassed: false,
        title: isEn ? '1. Input Assets & Governance' : '1. 입력 자산 & 거버넌스',
        sub: isEn ? 'Select customer input data shape' : '고객 입력 데이터 형태 선택',
        cat: 'input',
        options: [
          {
            key: 'doc_only',
            tone: 'tone-teal',
            tag: '[문서:가이드]',
            title: isEn ? 'Unstructured Docs Only (Lite)' : '비정형 정책·약관 문서 단독',
            desc: isEn ? 'PDF / DOCX / MD guides only. Runs Gate 0 (>=95% char fidelity) without DW CSV tables.' : 'PDF·DOCX·MD 원문만 투입. 정형 CSV 없이 Gate 0(원문 보존율 >=95%) 검증 후 Lite 경로 연결.',
            meta: 'extract_docs.py ➔ gate0_report.json'
          },
          {
            key: 'doc_dw',
            tone: '',
            tag: '[DB:마스터+문서]',
            title: isEn ? 'Structured DW + Policy Guides' : '정형 DW 원장(4종) + 정책 가이드(2종)',
            desc: isEn ? 'Combines de-identified DW tables (CUST_DEMO_*) with anchored policy guides.' : '고객약정·단말·요금제·지원금 정형 테이블(비식별화 CUST_DEMO_*)과 약관·특례 문서 결합.',
            meta: '4 CSVs + 2 Guides ➔ input_manifest.json'
          }
        ]
      },
      {
        stage: 'STAGE 2',
        tab: 'stage2',
        accent: '#0d9488',
        bypassed: false,
        title: isEn ? '2. Wiki & Semantic Layer' : '2. 3-Layer Wiki & 시맨틱 계층',
        sub: isEn ? 'Select document compilation depth' : '문서 지식화 및 시맨틱 구조 선택',
        cat: 'wiki',
        options: [
          {
            key: 'chunks',
            tone: 'tone-teal',
            tag: '[위키:청크]',
            title: isEn ? 'SHA-256 Anchored Chunks Only' : 'SHA-256 해시 앵커 청크 인용',
            desc: isEn ? 'Paragraph chunking with immutable SHA-256 anchors for direct citation.' : '원문 문단별 불변 해시 앵커(DOC_CHUNK_*)만 빠르게 생성하여 에이전트 근거로 주입.',
            meta: 'data/output/doc_chunks.jsonl'
          },
          {
            key: 'okf_3layer',
            tone: 'tone-teal',
            tag: '[위키:OKF]',
            title: isEn ? 'Karpathy 3-Layer Wiki + Semantic Graph' : '3-Layer LLM-Wiki + 시맨틱 그래프',
            desc: isEn ? 'Compiles L1 Summary, L2 Entities (Node), L3 Concepts/Rules (Edge) & ontology.jsonld.' : 'L1(Summary)·L2(Entities=Node)·L3(Concepts/Rules=Edge) 컴파일 및 시맨틱 그래프 구축.',
            meta: 'data/llm_wiki/*.md + ontology.jsonld'
          }
        ]
      },
      {
        stage: 'STAGE 3',
        tab: 'stage3',
        accent: '#4f46e5',
        bypassed: !isStage3Active,
        title: isEn ? '3. Physical Property Graph' : '3. 물리 Property Graph 엔진',
        sub: isEn ? 'Select graph DB or bypass (Lite)' : '5축 기준에 따른 그래프 엔진 선택',
        cat: 'engine',
        options: [
          {
            key: 'none',
            tone: 'tone-amber',
            tag: '[엔진:생략]',
            title: isEn ? 'Bypass Physical Graph (Track 1 Lite)' : '물리 그래프 미사용 (Stage 3 생략)',
            desc: isEn ? 'Skips Stage 3 DDL/ingestion and jumps directly from Stage 2 Wiki to Stage 4 Agent.' : 'Stage 3 물리 그래프 적재를 생략하고 Stage 2 위키/청크에서 Stage 4 에이전트로 직행.',
            meta: 'Stage 2 ──(Direct Bridge)──▶ Stage 4'
          },
          {
            key: 'bigquery',
            tone: 'tone-indigo',
            tag: '[엔진:기본]',
            title: isEn ? 'BigQuery Property Graph (Default)' : 'BigQuery Property Graph (기본)',
            desc: isEn ? 'Zero-ETL logical graph view over BigQuery DW tables (ISO SQL:2023). $0 idle cost.' : 'BigQuery 원장 위 Zero-ETL 무복제 논리 그래프(SQL:2023). 추가 인프라 유휴 비용 $0.',
            meta: 'create_property_graph.sql (p50 ~552ms)'
          },
          {
            key: 'spanner',
            tone: 'tone-indigo',
            tag: '[엔진:선택]',
            title: isEn ? 'Cloud Spanner Graph (Low-Latency)' : 'Cloud Spanner Graph (초저지연 OLTP)',
            desc: isEn ? '100 PU Enterprise edition for index-pointer multi-hop online traversal (ISO GQL).' : '100 PU 최소 사양 기반 실시간 온라인 멀티홉 탐색(ISO GQL). 저지연 SLA 환경 최적.',
            meta: 'create_spanner_graph.sql (p50 ~120ms)'
          },
          {
            key: 'both',
            tone: 'tone-indigo',
            tag: '[엔진:통합]',
            title: isEn ? 'Dual-Engine Graph Fabric (Both)' : 'Dual Graph Fabric (BQ + Spanner 통합)',
            desc: isEn ? 'Provisions both engines and joins Spanner online graph with BigQuery DW via EXTERNAL_QUERY.' : '양대 엔진 동시 적재 및 BigQuery EXTERNAL_QUERY(spanner_fabric_conn)로 실시간 연합 조인.',
            meta: 'BQ + Spanner + spanner_fabric_conn'
          }
        ]
      },
      {
        stage: 'STAGE 4',
        tab: 'stage4',
        accent: '#7c3aed',
        bypassed: false,
        title: isEn ? '4. Agent & MCP Runtime' : '4. 에이전트 & MCP 추론 런타임',
        sub: isEn ? 'Select agent execution architecture' : '에이전트 추론 및 도구 체이닝 방식',
        cat: 'runtime',
        options: [
          {
            key: 'lite_agent',
            tone: 'tone-purple',
            tag: '[런타임:Lite]',
            title: isEn ? 'Lite Document Citation Agent' : 'Lite 문서 청크 인용 에이전트',
            desc: isEn ? 'Injects up to 300k chars of anchored chunks into Gemini with strict [DOC_CHUNK_*] grounding.' : '최대 300,000자 원문 청크와 위키를 컨텍스트로 주입하여 [DOC_CHUNK_*] 인용 답변 생성.',
            meta: '_lite_cycle()'
          },
          {
            key: 'mcp_8tools',
            tone: 'tone-purple',
            tag: '[런타임:MCP]',
            title: isEn ? '8 Modular MCPs + Deterministic Math' : '8대 모듈형 MCP + 결정론적 산식 엔진',
            desc: isEn ? '5 Stage pipeline MCPs + 3 Runtime domain MCPs (Contract lookup, Penalty/TCO math, Graph GQL).' : '파이프라인 5종 MCP + 런타임 3종 MCP(고객원장·위약금/TCO 결정론 산식·그래프 GQL 탐색).',
            meta: 'mcp_server.py + reasoning_engine.py'
          }
        ]
      },
      {
        stage: 'STAGE 5',
        tab: 'stage5',
        accent: '#db2777',
        bypassed: !isStage5Full,
        title: isEn ? '5. Lineage & Evaluation' : '5. 데이터 리니지 & 평가 루프',
        sub: isEn ? 'Select governance & verification depth' : '거버넌스 계보 및 벤치마크 검증 수준',
        cat: 'eval',
        options: [
          {
            key: 'golden_only',
            tone: 'tone-amber',
            tag: '[평가:기본]',
            title: isEn ? 'Golden CQ Verification (Track 1·2)' : 'Golden CQ 정합성 검증 (Track 1·2)',
            desc: isEn ? 'Validates core Golden CQs (SQL or citation grounding) without full 50-trial boundary harness.' : '핵심 Golden CQ(수치 SQL 대조 또는 원문 청크 인용) 통과 여부를 빠르게 검증.',
            meta: 'cq_benchmark_report.json (5 CQs)'
          },
          {
            key: 'full_lineage_boundary',
            tone: 'tone-purple',
            tag: '[평가:풀스택]',
            title: isEn ? 'End-to-End Lineage DAG + 50-Trial Boundary' : '엔드투엔드 리니지 DAG + 바운더리 50회 평가',
            desc: isEn ? 'Source-to-agent data lineage graph + 10 boundary cases × 5 trials closed-loop diagnostics.' : '원천~에이전트 엔드투엔드 리니지 DAG 시각화 및 경계값 10건×5회 반복 실측.',
            meta: 'lineage_spec.json + boundary_benchmark_results.json'
          }
        ]
      }
    ];

    const mapCols = document.getElementById('ov-map-cols');
    if (mapCols) {
      mapCols.innerHTML = columnsSpec.map(col => {
        const cardsHtml = col.options.map(opt => {
          const isSel = (st[col.cat] === opt.key);
          return `
            <div class="ov-pick-card ${isSel ? 'selected ' + opt.tone : ''}" onclick="selectBuilderItem('${col.cat}', '${opt.key}')">
              <div class="ov-pick-head">
                <span class="ov-pick-tag">${esc(opt.tag)}</span>
                <span class="ov-pick-state">${isSel ? (isEn ? '✓ SELECTED' : '✓ 선택됨') : (isEn ? 'Select' : '클릭 선택')}</span>
              </div>
              <div class="ov-pick-title">${esc(opt.title)}</div>
              <div class="ov-pick-desc">${esc(opt.desc)}</div>
              <div class="ov-pick-meta">${esc(opt.meta)}</div>
            </div>
          `;
        }).join('');

        const statusBadge = col.bypassed
          ? `<span class="badge" style="background:#e2e8f0; color:#475569;">${isEn ? 'BYPASSED / LITE' : '생략 / 간소화'}</span>`
          : `<span class="badge approved">${isEn ? 'ACTIVE STAGE' : '구현 포함'}</span>`;

        return `
          <div class="ov-map-col ${col.bypassed ? 'bypassed' : ''}" style="border-top-color:${col.accent};">
            <div class="ov-map-col-head">
              <span class="ov-stage-chip" style="background:${col.accent}; color:#ffffff;">${col.stage}</span>
              <div style="display:flex; gap:4px; align-items:center;">
                ${statusBadge}
                <button class="subnav-action-btn" style="padding:2px 7px; font-size:10px;" onclick="switchTab('${col.tab}')">${isEn ? 'Open ↗' : '탭 이동 ↗'}</button>
              </div>
            </div>
            <div class="ov-map-col-title">${esc(col.title)}</div>
            <div class="ov-map-col-sub">${esc(col.sub)}</div>
            <div style="display:flex; flex-direction:column; gap:7px; flex:1;">
              ${cardsHtml}
            </div>
          </div>
        `;
      }).join('');
    }

    // 4. Render Assembled Starter Pack Package Implementation Blueprint (#ov-assembled-package-card)
    const trackBadgeText = activeTrack === 'lite'
      ? 'Track 1 · Lite (Stage 1→2→4)'
      : (activeTrack === 'standard' ? 'Track 2 · Standard (Stage 1→2→3→4)' : 'Track 3 · Full-Stack (Stage 1→5)');
    const engBadgeText = st.engine === 'none'
      ? (isEn ? 'No Physical Graph (Direct Citation)' : '물리 그래프 생략 (원문 청크 직행)')
      : (st.engine === 'both'
          ? 'Dual Fabric (BigQuery + Spanner EXTERNAL_QUERY)'
          : (st.engine === 'spanner' ? 'Cloud Spanner Graph (ISO GQL · 100 PU)' : 'BigQuery Property Graph (ISO SQL:2023)'));

    const activeBadgeEl = document.getElementById('ov-pkg-active-badge');
    if (activeBadgeEl) activeBadgeEl.textContent = `${trackBadgeText} + ${engBadgeText}`;

    const pkgTitleEl = document.getElementById('ov-pkg-title');
    if (pkgTitleEl) {
      pkgTitleEl.textContent = isEn
        ? `Assembled Starter Pack Implementation Blueprint: ${trackBadgeText}`
        : `선택 조합으로 조립된 스타터팩 패키지 구현 구성도 (${trackBadgeText})`;
    }

    const pkgSubEl = document.getElementById('ov-pkg-subtitle');
    if (pkgSubEl) {
      pkgSubEl.innerHTML = isEn
        ? `Based on your selections above, the Starter Pack wires together the following <b>pipeline stages, Python modules, MCP tools, notebooks, <code>project.json</code> config, Terraform IaC resources, and CLI commands</b>.`
        : `위 다이어그램에서 선택한 항목들에 맞춰 스타터팩의 <b>5단계 파이프라인 모듈, 활성 MCP 도구, 실습 노트북, <code>project.json</code> 설정, GCP Terraform 리소스 및 실행 명령어</b>가 아래와 같이 자동 구성됩니다.`;
    }

    const activeModulesCount = 4 + (isStage3Active ? 1 : 0) + (isStage5Full ? 1 : 0);
    const activeMcpCount = isStage3Active ? (isStage5Full ? 8 : 7) : 3;
    const activeNbCount = 3 + (isStage3Active ? 1 : 0) + (isStage5Full ? 2 : 1);
    const latencyProfile = st.engine === 'none'
      ? (isEn ? 'Lite Context · $0 Extra Infra' : '문서 컨텍스트 추론 · 추가 인프라 $0')
      : (st.engine === 'spanner'
          ? 'Spanner p50 ~120ms · 100 PU'
          : (st.engine === 'both' ? 'Spanner 120ms + Fabric 518ms' : 'BigQuery p50 ~552ms · Serverless $0 Idle'));

    const kpiPillsEl = document.getElementById('ov-pkg-kpi-pills');
    if (kpiPillsEl) {
      kpiPillsEl.innerHTML = `
        <span class="badge approved">${isEn ? `Modules: ${activeModulesCount}/6 Active` : `활성 코드 모듈: ${activeModulesCount}/6종`}</span>
        <span class="badge indigo">${isEn ? `MCP Tools: ${activeMcpCount}/8 Active` : `활성 MCP 도구: ${activeMcpCount}/8종`}</span>
        <span class="badge llm">${isEn ? `Notebooks: ${activeNbCount}/6 Included` : `실습 노트북: ${activeNbCount}/6종`}</span>
        <span class="badge human">${esc(latencyProfile)}</span>
      `;
    }

    // 4-A. Visual 5-Stage Package Implementation Pipeline Grid (#ov-pkg-pipe-grid)
    const pipeStages = [
      {
        num: 'STAGE 1',
        name: isEn ? 'Asset & Gate 0 Extraction' : '자산 수집 & Gate 0 검증',
        active: true,
        color: '#3b82f6',
        script: st.input === 'doc_only' ? 'pipeline/extract_docs.py' : 'pipeline/extract_docs.py + ingest.py',
        gcp: st.input === 'doc_only' ? 'Cloud Storage (Raw Docs)' : 'GCS + BigQuery Raw Tables',
        artifact: st.input === 'doc_only' ? 'gate0_report.json + input_manifest.json' : '4 DW Tables + gate0_report.json',
        note: st.input === 'doc_only'
          ? (isEn ? 'Extracts full text (>=95% ratio) with page/provenance anchors; skips CSV table load.' : '원문 보존율 95% 이상 추출 및 페이지 앵커 고정 (정형 CSV 적재 생략)')
          : (isEn ? 'Loads 4 de-identified DW CSVs + 2 policy guides with provenance check & 5-axis checklist.' : '비식별화 정형 원장 4종 + 정책 문서 2종 적재 및 5축 그래프 체크리스트 산출')
      },
      {
        num: 'STAGE 2',
        name: isEn ? 'Wiki & Semantic Compiler' : '위키 & 시맨틱 그래프 컴파일',
        active: true,
        color: '#0d9488',
        script: 'pipeline/ingest.py (compile_wiki)',
        gcp: 'BigQuery tb_doc_chunks + GCS Wiki',
        artifact: st.wiki === 'chunks' ? 'doc_chunks.jsonl (SHA-256)' : 'summary/entities/concepts/rules.md + ontology.jsonld',
        note: st.wiki === 'chunks'
          ? (isEn ? 'Generates SHA-256 anchored paragraph chunks for direct grounding.' : '문단별 SHA-256 해시 앵커 청크(doc_chunks.jsonl) 생성 및 BigQuery 적재')
          : (isEn ? 'Compiles Karpathy 3-Layer Wiki + Entity(Node)/Concept(Edge) JSON-LD ontology.' : 'Karpathy 3-Layer 위키 마크다운 4종 및 Entity=Node/Concept=Edge 시맨틱 그래프 생성')
      },
      {
        num: 'STAGE 3',
        name: isEn ? 'Physical Property Graph' : '물리 Property Graph 구축',
        active: isStage3Active,
        color: '#4f46e5',
        script: isStage3Active ? 'pipeline/graph_builder.py' : 'BYPASSED (생략됨)',
        gcp: st.engine === 'none'
          ? (isEn ? 'None (Skipped in Lite Path)' : '미사용 (Lite 경로에서 생략)')
          : (st.engine === 'both'
              ? 'BigQuery Graph + Spanner Graph (100 PU) + EXTERNAL_QUERY'
              : (st.engine === 'spanner' ? 'Cloud Spanner Graph (100 PU, ISO GQL)' : 'BigQuery Property Graph (ISO SQL:2023)')),
        artifact: st.engine === 'none'
          ? 'None (Stage 2 ➔ Stage 4 직행)'
          : (st.engine === 'both'
              ? 'create_property_graph.sql + create_spanner_graph.sql'
              : (st.engine === 'spanner' ? 'create_spanner_graph.sql + graph_topology.json' : 'create_property_graph.sql + graph_topology.json')),
        note: st.engine === 'none'
          ? (isEn ? 'Physical graph DDL and node/edge tables are bypassed; Stage 2 connects straight to Stage 4.' : '물리 그래프 DDL 생성을 생략하고 Stage 2 위키/청크가 Stage 4 에이전트로 직결됨')
          : (st.engine === 'both'
              ? (isEn ? 'Builds both BigQuery & Spanner graphs + runs EXTERNAL_QUERY federated join benchmark.' : 'BigQuery 무복제 뷰와 Spanner 물리 그래프를 동시 구축하고 EXTERNAL_QUERY로 연합 조인')
              : (st.engine === 'spanner'
                  ? (isEn ? 'Upserts nodes/edges to Cloud Spanner (100 PU) for sub-150ms ISO GQL multi-hop traversal.' : 'Cloud Spanner(100 PU)에 노드·엣지를 적재하여 120ms대 온라인 멀티홉 GQL 탐색 수행')
                  : (isEn ? 'Projects 4 DW tables + 2 doc tables as a Zero-ETL BigQuery Property Graph.' : '정형 원장 4종과 문서 규칙 노드를 Zero-ETL 무복제 BigQuery Property Graph로 승격')))
      },
      {
        num: 'STAGE 4',
        name: isEn ? 'Agent & MCP Orchestration' : '에이전트 & MCP 런타임',
        active: true,
        color: '#7c3aed',
        script: st.runtime === 'lite_agent' ? 'src/agent/reasoning_engine.py (Lite)' : 'src/agent/mcp_server.py + reasoning_engine.py',
        gcp: `Vertex AI Gemini + ${st.engine === 'spanner' ? 'Spanner GQL' : (st.engine === 'both' ? 'BQ + Spanner Fabric' : 'BigQuery SQL/GQL')}`,
        artifact: st.runtime === 'lite_agent' ? '_lite_cycle ([DOC_CHUNK_*])' : '8 Modular MCP Tools + Deterministic Math',
        note: st.runtime === 'lite_agent'
          ? (isEn ? 'Answers questions directly from anchored document chunks without SQL/GQL table joins.' : 'SQL/그래프 조인 없이 원문 청크 컨텍스트(최대 300k자) 기반으로 [DOC_CHUNK_*] 인용 답변 생성')
          : (isEn ? 'Chains 5 Stage MCPs + 3 Runtime MCPs (Contract, Penalty/TCO formula, Graph/Wiki traversal).' : 'Stage 1~5 파이프라인 MCP와 런타임 도메인 MCP 3종(원장·위약금산식·그래프탐색) 체이닝')
      },
      {
        num: 'STAGE 5',
        name: isEn ? 'Lineage & Closed-Loop Eval' : '리니지 & 바운더리 평가',
        active: true,
        color: isStage5Full ? '#db2777' : '#0284c7',
        script: isStage5Full ? 'pipeline/validator.py (Full + Lineage)' : 'pipeline/validator.py (--golden-only)',
        gcp: isStage5Full ? 'End-to-End Lineage DAG + Vertex Eval' : 'Golden CQ Verification',
        artifact: isStage5Full ? 'lineage_spec.json + cq & boundary reports' : 'cq_benchmark_report.json',
        note: isStage5Full
          ? (isEn ? 'Renders interactive end-to-end lineage DAG (measured BQ / GCS / graph volumes) + 10×5 Boundary regression.' : '실측 볼륨 기반 엔드투엔드 데이터 리니지 DAG 시각화 및 Golden 5건 + Boundary 50회 회귀 평가')
          : (isEn ? 'Runs lightweight Golden CQ accuracy/citation verification (skips 50-trial boundary loop).' : '핵심 Golden CQ 정합성(SQL 대조 또는 청크 인용)만 신속 검증 (바운더리 50회 루프 생략)')
      }
    ];

    const pipeGridEl = document.getElementById('ov-pkg-pipe-grid');
    if (pipeGridEl) {
      pipeGridEl.innerHTML = pipeStages.map(ps => `
        <div class="ov-pkg-node ${ps.active ? '' : 'bypassed'}" style="border-left-color:${ps.color};">
          <div style="display:flex; justify-content:space-between; align-items:center; gap:4px;">
            <span style="font-size:10.5px; font-weight:800; font-family:var(--font-mono); color:${ps.active ? ps.color : '#64748b'};">${ps.num}</span>
            <span class="badge ${ps.active ? 'approved' : ''}" style="${ps.active ? '' : 'background:#e2e8f0; color:#475569;'}">
              ${ps.active ? (isEn ? 'INCLUDED' : '패키지 포함') : (isEn ? 'BYPASSED' : '패스 생략')}
            </span>
          </div>
          <div style="font-size:12.5px; font-weight:800; color:#0f172a;">${esc(ps.name)}</div>
          <div style="font-size:11px; color:#334155; line-height:1.45;">${esc(ps.note)}</div>
          <div style="margin-top:auto; padding-top:6px; border-top:1px dotted #cbd5e1; font-size:10.5px; font-family:var(--font-mono); color:#0f172a;">
            <div><b>Code:</b> ${esc(ps.script)}</div>
            <div><b>GCP:</b> ${esc(ps.gcp)}</div>
            <div><b>Out:</b> ${esc(ps.artifact)}</div>
          </div>
        </div>
      `).join('');
    }

    // 4-B. Render 4-Column Package Implementation Manifest (#ov-pkg-manifest-grid)
    const codeModules = [
      { file: 'pipeline/extract_docs.py', active: true, role: isEn ? 'Gate 0 raw doc parser & 5-axis checklist' : '원문 변환 · Gate 0 검증 · 5축 체크리스트' },
      { file: 'pipeline/ingest.py', active: true, role: st.input === 'doc_only' ? (isEn ? 'Chunks & 3-Layer Wiki compiler (doc-only)' : '청크 & 3-Layer 위키 컴파일 (CSV 생략)') : (isEn ? 'DW CSV + Chunks load to BQ/Spanner' : '정형 원장 + 청크 BigQuery/Spanner 적재') },
      { file: 'pipeline/graph_builder.py', active: isStage3Active, role: isStage3Active ? (isEn ? `Synthesizes ${st.engine.toUpperCase()} DDL & benchmark` : `${st.engine.toUpperCase()} 그래프 DDL 합성 및 벤치마크`) : (isEn ? 'Skipped in Lite path (no physical graph)' : 'Lite 패스에서 실행 생략 (물리 그래프 미사용)') },
      { file: 'src/gcp_client.py', active: true, role: st.engine === 'both' ? (isEn ? 'BQ + Spanner + EXTERNAL_QUERY fabric client' : 'BQ + Spanner + EXTERNAL_QUERY 연합 클라이언트') : (st.engine === 'spanner' ? (isEn ? 'Cloud Spanner GQL + BQ SQL dialect rewrite' : 'Spanner GQL 실행 및 SQL 방언 자동 변환') : (isEn ? 'BigQuery SQL/GRAPH_TABLE & Gemini client' : 'BigQuery SQL/GRAPH_TABLE 및 Gemini 연동')) },
      { file: 'src/agent/mcp_server.py', active: true, role: st.runtime === 'lite_agent' ? (isEn ? 'Stage 1·2·5 MCPs + Lite doc citation' : 'Stage 1·2·5 MCP 및 Lite 문서 인용') : (isEn ? `All 8 MCP tools (engine=${st.engine === 'both' ? 'bigquery|spanner' : st.engine})` : `8대 모듈형 MCP 전수 구동 (engine=${st.engine})`) },
      { file: 'pipeline/validator.py', active: true, role: isStage5Full ? (isEn ? 'Golden CQ 5 + Boundary 50-Trial harness' : 'Golden CQ 5종 + 바운더리 50회 회귀 평가') : (isEn ? 'Golden CQ quick accuracy/citation check' : 'Golden CQ 핵심 정합성/인용 검증') }
    ];

    const mcpAndNotebooks = [
      { name: 'mcp_stage1_asset_discovery', nb: 'stage1_asset_and_cq', active: true, tool: 'mcp_stage1_asset_discovery' },
      { name: 'mcp_stage2_wiki_and_semantic', nb: 'stage2_wiki_and_semantic_graph', active: true, tool: 'mcp_stage2_wiki_and_semantic' },
      { name: 'mcp_stage3_property_graph', nb: 'stage3_property_graph_bigquery_spanner', active: isStage3Active, tool: 'mcp_stage3_property_graph' },
      { name: 'mcp_stage4_agent_orchestration + Runtime 3종', nb: 'stage4_agent_and_mcp_execution', active: true, tool: 'mcp_stage4_agent_orchestration' },
      { name: 'mcp_stage5_lineage_and_eval', nb: 'stage5_lineage_and_evaluation', active: isStage5Full, tool: 'mcp_stage5_lineage_and_eval' }
    ];

    const projectJsonPreview = JSON.stringify({
      project_id: activeProject || 'my_ontology',
      track: activeTrack,
      graph_engine: st.engine === 'none' ? 'bigquery' : st.engine,
      input_mode: st.input,
      wiki_mode: st.wiki,
      eval_mode: st.eval,
      spanner_instance_id: (st.engine === 'spanner' || st.engine === 'both') ? 'starter-spanner' : '',
      spanner_bq_connection_id: (st.engine === 'both') ? 'spanner_fabric_conn' : ''
    }, null, 2);

    const tfResources = [
      { res: 'google_storage_bucket (Wiki & Docs)', active: true },
      { res: 'google_bigquery_dataset + tb_doc_chunks', active: true },
      { res: 'BigQuery Property Graph (SQL:2023 View)', active: st.engine === 'bigquery' || st.engine === 'both' },
      { res: 'google_spanner_instance (100 PU) + DB', active: st.engine === 'spanner' || st.engine === 'both' },
      { res: 'google_bigquery_connection (spanner_fabric_conn)', active: st.engine === 'both' }
    ];

    const spannerTfFlag = (st.engine === 'spanner' || st.engine === 'both') ? ' --enable-spanner' : '';
    const cliCommands = [
      `# 1. ${isEn ? 'Scaffold project with selected Track & Graph Engine' : '선택한 트랙 및 그래프 엔진으로 프로젝트 생성'}`,
      `python3 new_project.py --id my_case --name "My Ontology" \\`,
      `  --track ${activeTrack} --graph-engine ${st.engine === 'none' ? 'bigquery' : st.engine}`,
      ``,
      `# 2. ${isEn ? 'Provision GCP infrastructure via Terraform' : '선택 구성에 필요한 GCP 인프라 Terraform 배포'}`,
      `python3 terraform/apply_terraform.py --project my_case${spannerTfFlag}`,
      ``,
      `# 3. ${isEn ? 'Run selected pipeline path & launch Studio UI' : '선택 패스 파이프라인 실행 및 로컬 스튜디오 구동'}`,
      `python3 pipeline/extract_docs.py --project my_case`,
      `python3 run_pipeline.py --project my_case --track ${activeTrack}`,
      `python3 -m src.web.studio_server 8080`
    ].join('\n');

    const manifestGridEl = document.getElementById('ov-pkg-manifest-grid');
    if (manifestGridEl) {
      const langFolder = isEn ? 'en' : 'ko';
      const langSuffix = isEn ? '_en.ipynb' : '_ko.ipynb';
      manifestGridEl.innerHTML = `
        <!-- Box 1: Code Modules -->
        <div class="ov-pkg-box">
          <div class="ov-pkg-box-head">
            <span class="ov-pkg-box-title">${isEn ? '1. Included Pipeline & Runtime Modules' : '1. [구현:코드] 파이프라인 & 런타임 모듈'}</span>
            <span class="badge approved">${activeModulesCount}/6</span>
          </div>
          <div style="display:flex; flex-direction:column; gap:6px;">
            ${codeModules.map(m => `
              <div class="ov-pkg-item-row ${m.active ? '' : 'skipped'}">
                <div>
                  <code style="font-weight:800; color:${m.active ? 'var(--apple-blue)' : '#94a3b8'};">${esc(m.file)}</code>
                  <div style="font-size:11px; color:${m.active ? '#475569' : '#94a3b8'}; margin-top:2px;">${esc(m.role)}</div>
                </div>
                <span class="badge ${m.active ? 'approved' : ''}" style="flex-shrink:0; ${m.active ? '' : 'background:#e2e8f0; color:#64748b;'}">
                  ${m.active ? (isEn ? 'ACTIVE' : '포함') : (isEn ? 'SKIP' : '생략')}
                </span>
              </div>
            `).join('')}
          </div>
        </div>

        <!-- Box 2: MCP Tools & Notebooks -->
        <div class="ov-pkg-box">
          <div class="ov-pkg-box-head">
            <span class="ov-pkg-box-title">${isEn ? '2. Active MCP Tools & Stage Notebooks' : '2. [구현:MCP & 노트북] 활성 도구 및 노트북'}</span>
            <span class="badge indigo">${activeMcpCount} MCPs</span>
          </div>
          <div style="display:flex; flex-direction:column; gap:6px;">
            ${mcpAndNotebooks.map(item => `
              <div class="ov-pkg-item-row ${item.active ? '' : 'skipped'}">
                <div style="min-width:0; flex:1;">
                  <div style="font-weight:700; color:${item.active ? '#0f172a' : '#94a3b8'}; font-size:11.5px;">${esc(item.name)}</div>
                  <a href="https://github.com/seanjungG/agentic-ontology-starter/blob/main/notebooks/${langFolder}/${item.nb}${langSuffix}" target="_blank" rel="noopener" style="font-size:10px; font-family:var(--font-mono); color:${item.active ? '#0284c7' : '#94a3b8'}; text-decoration:none; word-break:break-all; display:inline-block; line-height:1.3; margin-top:2px;">
                    notebooks/${langFolder}/${item.nb}${langSuffix} ↗
                  </a>
                </div>
                <button class="ov-stage-mcp-btn" style="flex-shrink:0;" onclick="openStageMcpModal('${item.tool}')">▶ MCP</button>
              </div>
            `).join('')}
          </div>
        </div>

        <!-- Box 3: project.json & Terraform Resources -->
        <div class="ov-pkg-box">
          <div class="ov-pkg-box-head">
            <span class="ov-pkg-box-title">${isEn ? '3. Synthesized project.json & Terraform IaC' : '3. [구현:설정 & IaC] project.json & GCP 리소스'}</span>
            <span class="badge llm">Terraform</span>
          </div>
          <pre class="code-pre-light" style="font-size:10.5px; padding:8px 10px; max-height:135px; margin:0;">${esc(projectJsonPreview)}</pre>
          <div style="display:flex; flex-direction:column; gap:4px; margin-top:2px;">
            ${tfResources.map(tf => `
              <div style="display:flex; justify-content:space-between; align-items:center; gap:6px; font-size:11px; padding:4px 7px; background:#ffffff; border:1px solid #e2e8f0; border-radius:6px;">
                <code style="color:${tf.active ? '#0f172a' : '#94a3b8'}; min-width:0; word-break:break-all;">${esc(tf.res)}</code>
                <span style="font-size:10px; font-weight:800; white-space:nowrap; flex-shrink:0; color:${tf.active ? '#059669' : '#94a3b8'};">${tf.active ? (isEn ? '● PROVISIONED' : '● 배포됨') : (isEn ? '○ NOT NEEDED' : '○ 불필요')}</span>
              </div>
            `).join('')}
          </div>
        </div>

        <!-- Box 4: Ready-to-Run CLI Commands -->
        <div class="ov-pkg-box">
          <div class="ov-pkg-box-head">
            <span class="ov-pkg-box-title">${isEn ? '4. Ready-to-Run Package Bootstrap CLI' : '4. [구현:CLI] 선택 패키지 3-Step 실행 명령어'}</span>
            <button class="subnav-action-btn" id="ov-pkg-cli-copy-btn" style="padding:2px 8px; font-size:10.5px;" onclick="copyPackageCli()">${isEn ? 'Copy CLI' : 'CLI 복사'}</button>
          </div>
          <pre class="code-pre-light" id="ov-pkg-cli-code" style="font-size:10.5px; padding:10px; flex:1; margin:0; white-space:pre-wrap;">${esc(cliCommands)}</pre>
        </div>
      `;
    }

    // 5. Sync the 5-Stage Detailed Flow Board (#ov-flow-board) with active/bypassed states
    if (portalOverviewCache) {
      renderFiveStageFlowBoard(portalOverviewCache);
    }
  }

  function renderFiveStageFlowBoard(ov) {
    const board = document.getElementById('ov-flow-board');
    if (!board) return;
    const isEn = (studioLang === 'en');
    const isStage3Active = (pkgBuilderState.engine !== 'none');
    const isStage5Full = (pkgBuilderState.eval === 'full_lineage_boundary');

    board.innerHTML = (ov.stages || []).map(st => {
      const isBypassed = (st.stage_id === 'stage3' && !isStage3Active) || (st.stage_id === 'stage5' && !isStage5Full);
      const statePill = isBypassed
        ? `<span class="badge" style="background:#e2e8f0; color:#475569; font-size:10px;">${isEn ? 'Bypassed in Selected Path' : '현재 선택 패스에서 생략'}</span>`
        : `<span class="badge approved" style="font-size:10px;">${isEn ? 'Active in Selected Path' : '현재 선택 패스 활성'}</span>`;

      const steps = (st.steps || []).map((sp, i) => `
        ${i > 0 ? '<div class="ov-conn-v">&darr;</div>' : ''}
        <div class="ov-step-box" style="border-left-color:${esc(st.accent)};" onclick="switchTab('${esc(st.stage_id || 'stage1')}')">
          <div class="ov-step-badge" style="color:${esc(st.accent)};">${esc(sp.badge)}</div>
          <div class="ov-step-title">${esc(sp.title)}</div>
          <div class="ov-step-desc">${(sp.bullets || []).map(b => '&bull; ' + b).join('<br>')}</div>
          ${sp.deliverables ? `<div class="ov-step-out"><b>산출물</b> ${sp.deliverables}</div>` : ''}
        </div>`).join('');
      return `<div class="ov-stage-col ${isBypassed ? 'bypassed-col' : ''}" style="border-top-color:${esc(st.accent)};">
          <div class="ov-stage-head-row">
            <span class="ov-stage-chip">${esc(st.chip)}</span>
            <button class="ov-stage-mcp-btn" onclick="openStageMcpModal('${esc(st.mcp_tool || 'mcp_stage1_asset_discovery')}')">▶ ${esc(st.chip)} MCP</button>
          </div>
          <div>${statePill}</div>
          <div class="ov-stage-name">${esc(st.name)}</div>
          <div style="display:flex; gap:6px; flex-wrap:wrap; margin-bottom:2px;">
            ${st.methodology_doc ? `<a class="subnav-action-btn" style="text-decoration:none; padding:2px 8px; font-size:10.5px;" href="https://github.com/seanjungG/agentic-ontology-starter/blob/main/${esc(st.methodology_doc)}" target="_blank" rel="noopener">방법론</a>` : ""}
            ${st.notebook ? `<a class="subnav-action-btn" style="text-decoration:none; padding:2px 8px; font-size:10.5px;" href="https://github.com/seanjungG/agentic-ontology-starter/blob/main/${esc(st.notebook)}" target="_blank" rel="noopener">노트북</a>` : ""}
          </div>
          ${steps}
        </div>`;
    }).join('');
  }

  // 4. Overview Loader
  async function loadPortalProfile() {
    try {
      const res = await fetch('/api/portal/profile');
      const p = await res.json();
      const ov = p.overview || {};
      portalOverviewCache = ov;
      if (ov.path_configurator) {
        const pc = ov.path_configurator;
        const eb = document.getElementById('ov-builder-eyebrow');
        const ti = document.getElementById('ov-builder-title');
        const ld = document.getElementById('ov-builder-lead');
        if (eb) { eb.setAttribute('data-ko', pc.eyebrow_ko || ''); eb.setAttribute('data-en', pc.eyebrow_en || ''); eb.textContent = studioLang === 'en' ? pc.eyebrow_en : pc.eyebrow_ko; }
        if (ti) { ti.setAttribute('data-ko', pc.title_ko || ''); ti.setAttribute('data-en', pc.title_en || ''); ti.innerHTML = studioLang === 'en' ? pc.title_en : pc.title_ko; }
        if (ld) { ld.setAttribute('data-ko', pc.lead_ko || ''); ld.setAttribute('data-en', pc.lead_en || ''); ld.innerHTML = studioLang === 'en' ? pc.lead_en : pc.lead_ko; }
      }
      document.getElementById('ov-s1-eyebrow').textContent = esc(ov.eyebrow);
      document.getElementById('ov-s1-title').textContent = esc(ov.title);
      document.getElementById('ov-s1-lead').innerHTML = esc(ov.lead);

      renderOverviewPathBuilder();

      const gap = ov.feature_gap || {};
      document.getElementById('ov-s2-eyebrow').textContent = esc(gap.eyebrow);
      document.getElementById('ov-s2-title').textContent = esc(gap.title);
      document.getElementById('ov-gap-body').innerHTML = (gap.rows || []).map(r => `
        <tr>
          <td class="lead-cell">${esc(r.layer)}</td>
          <td>${esc(r.native)}</td>
          <td class="muted">${esc(r.gap)}</td>
          <td>${esc(r.solution)}</td>
        </tr>`).join('');

      const mt = ov.metrics || {};
      document.getElementById('ov-s4-eyebrow').textContent = esc(mt.eyebrow);
      document.getElementById('ov-s4-note').innerHTML = esc(mt.note);
      document.getElementById('ov-metric-grid').innerHTML = (mt.items || []).map(m => `
        <div class="metric-box">
          <div class="metric-title">${esc(m.label)}</div>
          <div class="metric-value" style="color:${esc(m.color)};">${esc(m.value)}</div>
          <div class="ov-metric-cap">${esc(m.caption)}</div>
        </div>`).join('');

      const chipsEl = document.getElementById('agent-sample-chips');
      if (chipsEl && Array.isArray(p.agent_questions) && p.agent_questions.length > 0) {
        chipsEl.style.display = '';
        chipsEl.innerHTML = `<span style="font-size:11px; font-weight:700; color:var(--apple-text-secondary);">도메인 맞춤 추천 질의:</span>` +
          p.agent_questions.map(q => {
            const lbl = studioLang === 'en' ? (q.label_en || q.label_ko) : (q.label_ko || q.label_en);
            const qtext = studioLang === 'en' ? (q.query_en || q.query_ko) : (q.query_ko || q.query_en);
            return `<span class="quick-chip" onclick="applySample(${esc(JSON.stringify(qtext))})">${esc(lbl)}</span>`;
          }).join('');
      }
    } catch (e) {
      console.error(e);
    }
  }

  // 5. Stage 1 Asset Inventory & 6:4 Inspector
  async function ensureAssetsLoaded(cb) {
    if (globalAssets) { if (cb) cb(); return; }
    const res = await fetch('/api/assets');
    globalAssets = await res.json();
    if (cb) cb();
  }

  const STAGE1_CATALOG = [
    { id: 'customer_contracts', short: '고객약정', name: '고객 약정 원장 (dw_customer_contract)', type: 'dw', pk: 'contract_id', status: 'PII Masked (CUST_DEMO_*)', badge: 'approved' },
    { id: 'devices', short: '단말', name: '단말기 마스터 원장 (dw_device_master)', type: 'dw', pk: 'device_id', status: 'Zero-ETL Promoted', badge: 'human' },
    { id: 'plans', short: '요금제', name: '모바일 요금제 원장 (dw_plan_master)', type: 'dw', pk: 'plan_id', status: 'Zero-ETL Promoted', badge: 'human' },
    { id: 'subsidies', short: '지원금', name: '공시지원금 정책 원장 (dw_subsidy_policy_master)', type: 'dw', pk: 'policy_id', status: 'Zero-ETL Promoted', badge: 'human' },
    { id: 'guide_policy', name: '단말 지원금 및 180일 의무유지 약관 (sample_policy_guide.md)', type: 'doc', doc: 'sample_policy_guide.md', status: 'SHA-256 Anchored', badge: 'llm' },
    { id: 'guide_welfare', name: '시니어·복지 위약금 면제 특례 및 24M TCO 가이드 (sample_welfare_exemption_guide.md)', type: 'doc', doc: 'sample_welfare_exemption_guide.md', status: 'SHA-256 Anchored', badge: 'llm' }
  ];

  // F9: labels come from row provenance (CSV) and input_manifest.json + gate0_report.json; the fixed list is sample-only.
  const PROV_LABEL = { CUSTOMER_PROVIDED: '고객 제공 테이블', EXTRACTED: '문서 추출 테이블', SYNTHETIC_DEMO: '합성 데모 데이터' };
  function stage1TableLabel(id) {
    const t = stage1Table(id), i = t.headers.indexOf('provenance');
    const vals = [...new Set(t.rows.map(r => i < 0 ? '' : r[i]))];
    return vals.length === 1 && PROV_LABEL[vals[0]] ? PROV_LABEL[vals[0]] : '출처 없음 (적재 불가)';
  }
  function stage1DocLabel(doc) {
    const a = globalAssets || {};
    const g = ((a.gate0 || {}).documents || []).find(d => d.guide === doc);
    if (g) return `원문 비율 ${(g.char_ratio * 100).toFixed(1)}% · ${g.pages}쪽`;
    return ((a.chunks || []).find(c => c.source_doc === doc) || {}).provenance === 'SYNTHETIC_DEMO' ? '합성 데모 데이터' : '출처 없음';
  }
  function stage1Catalog() {
    const a = globalAssets || {}, tables = a.tables || {};
    const docs = [...new Set((a.chunks || []).map(c => c.source_doc).filter(Boolean))];
    const label = i => ({ ...i, status: i.type === 'dw' ? stage1TableLabel(i.id) : stage1DocLabel(i.doc), badge: i.type === 'dw' ? 'human' : 'llm' });
    if (a.is_sample) return STAGE1_CATALOG.filter(i => i.type === 'dw' ? tables[i.id] : docs.includes(i.doc)).map(label);
    return Object.keys(tables).map(t => label({ id: t, short: t, name: `${t}.csv`, type: 'dw', pk: tables[t].headers[0] || '-' }))
      .concat(docs.map((d, i) => label({ id: `doc_${i + 1}`, name: d, type: 'doc', doc: d })));
  }

  // Counts come from /api/assets (repo CSVs + data/output/doc_chunks.jsonl), not from fixed values.
  function stage1Table(id) { return ((globalAssets || {}).tables || {})[id] || { headers: [], rows: [] }; }
  function stage1Chunks(doc) { return ((globalAssets || {}).chunks || []).filter(c => !doc || c.source_doc === doc).map(c => c.chunk_id); }
  function stage1Schema(item) {
    if (item.type === 'dw') { const t = stage1Table(item.id); return `${t.rows.length} Rows · ${t.headers.length} Columns (PK: ${item.pk})`; }
    const ids = stage1Chunks(item.doc);
    return `${ids.length} Anchored Chunks (${ids[0] || '-'}~${ids[ids.length - 1] || '-'})`;
  }
  function renderStage1Kpis() {
    const set = (id, v) => { const el = document.getElementById(id); if (el) el.textContent = v; };
    const cat = stage1Catalog(), dw = cat.filter(i => i.type === 'dw');
    set('st1-kpi-assets', `${cat.length} Assets`);
    set('st1-kpi-assets-sub', `테이블 ${dw.length}종 + 문서 ${cat.length - dw.length}종`);
    set('st1-ribbon-title', `테이블 ${dw.length}종 · 문서 ${cat.length - dw.length}종 인벤토리`);
    set('st1-filter-all', `전체 자산 (${cat.length})`);
    set('st1-filter-dw', `테이블 (${dw.length})`);
    set('st1-filter-doc', `문서 (${cat.length - dw.length})`);
    set('st1-kpi-rows', `${dw.reduce((s, i) => s + stage1Table(i.id).rows.length, 0)} Rows`);
    set('st1-kpi-rows-sub', dw.map(i => `${i.short} ${stage1Table(i.id).rows.length}`).join(' · '));
    const ids = stage1Chunks();
    set('st1-kpi-chunks', `${ids.length} Chunks`);
    set('st1-kpi-chunks-sub', `${ids[0] || '-'} ~ ${ids[ids.length - 1] || '-'} (SHA-256)`);
    const ct = stage1Table('customer_contracts'), ci = ct.headers.indexOf('customer_id');
    set('st1-kpi-pii', `${ct.rows.filter(r => /^CUST_DEMO_\d+$/.test(r[ci] || '')).length}/${ct.rows.length} Synthetic IDs`);
    set('st1-kpi-pii-sub', 'customer_id 중 합성 식별자(CUST_DEMO_*) 건수');
  }

  function filterStage1Assets(flt) {
    stage1Filter = flt;
    document.getElementById('st1-filter-all').classList.toggle('active', flt === 'all');
    document.getElementById('st1-filter-dw').classList.toggle('active', flt === 'dw');
    document.getElementById('st1-filter-doc').classList.toggle('active', flt === 'doc');
    renderStage1Assets();
  }

  function renderStage1Assets() {
    const tbody = document.getElementById('stage1-asset-tbody');
    if (!tbody) return;
    renderStage1Kpis();
    const rows = stage1Catalog().filter(item => stage1Filter === 'all' || item.type === stage1Filter);
    if (!rows.length) { tbody.innerHTML = '<tr><td colspan="5">데이터 없음</td></tr>'; return; }
    tbody.innerHTML = rows.map((item, idx) => `
      <tr id="st1-row-${item.id}" onclick="inspectStage1Asset('${item.id}')">
        <td><code style="font-weight:700; color:var(--apple-blue);">${item.id}</code></td>
        <td style="font-weight:600;">${item.name}</td>
        <td><span class="badge ${item.type === 'dw' ? 'human' : 'llm'}">${item.type === 'dw' ? 'Track B · DW Table' : 'Track A · Policy Guide'}</span></td>
        <td style="font-family:var(--font-mono); font-size:12px;">${stage1Schema(item)}</td>
        <td><span class="badge ${item.badge}">${item.status}</span></td>
      </tr>
    `).join('');
    if (rows.length) inspectStage1Asset(rows[0].id);
  }

  function inspectStage1Asset(assetId) {
    document.querySelectorAll('#stage1-asset-tbody tr').forEach(tr => tr.classList.remove('selected'));
    const activeRow = document.getElementById('st1-row-' + assetId);
    if (activeRow) activeRow.classList.add('selected');

    const item = stage1Catalog().find(x => x.id === assetId);
    if (!item || !globalAssets) return;
    document.getElementById('st1-insp-kicker').textContent = item.type === 'dw' ? 'STRUCTURED DW TABLE PREVIEW' : 'UNSTRUCTURED POLICY CHUNKS';
    document.getElementById('st1-insp-title').textContent = item.name;
    document.getElementById('st1-insp-badge').textContent = item.status;

    const body = document.getElementById('st1-insp-body');
    if (item.type === 'dw') {
      const tbl = (globalAssets.tables || {})[assetId] || { headers: [], rows: [] };
      const ths = tbl.headers.map(h => `<th>${esc(h)}</th>`).join('');
      const trs = tbl.rows.map(r => `<tr>${r.map(c => `<td>${esc(c)}</td>`).join('')}</tr>`).join('');
      body.innerHTML = `
        <div style="margin-bottom:10px; font-size:12px; color:var(--apple-text-secondary);">
          물리 파일 경로: <code>data/input/03_tables/${assetId}.csv</code> &middot; ${esc(item.status)}
        </div>
        <div style="overflow-x:auto; border:1px solid #cbd5e1; border-radius:8px;">
          <table class="ov-gap-table" style="font-size:12px;">
            <thead><tr>${ths}</tr></thead>
            <tbody>${trs}</tbody>
          </table>
        </div>
      `;
    } else {
      const docName = item.doc;
      const chunks = (globalAssets.chunks || []).filter(c => !c.source_doc || c.source_doc === docName);
      body.innerHTML = chunks.map(c => `
        <div class="chunk-card-light">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
            <strong style="color:var(--apple-blue);">${esc(c.chunk_id)} · ${esc(c.title)}</strong>
            <code style="font-size:11px; background:#f1f5f9; padding:2px 6px; border-radius:4px;">${esc(c.hash_anchor)}</code>
          </div>
          <div style="font-size:12.5px; color:#334155; white-space:pre-wrap;">${esc(c.content)}</div>
        </div>
      `).join('');
    }
  }

  // 6. Stage 2 Wiki & Semantic Graph (vis-network, TASK-093 compliant)
  function showWikiDoc(key, btnId) {
    document.querySelectorAll('#panel-stage2 .pane-card:first-child .segment-btn').forEach(b => b.classList.remove('active'));
    const btn = document.getElementById(btnId);
    if (btn) btn.classList.add('active');

    const container = document.getElementById('stage2-wiki-body');
    if (!globalAssets || !container) return;
    if (key === 'chunks') {
      container.innerHTML = (globalAssets.chunks || []).map(c => `
        <div class="chunk-card-light">
          <div style="display:flex; justify-content:space-between; margin-bottom:4px;">
            <strong style="color:#0f766e;">${esc(c.chunk_id)}: ${esc(c.title)}</strong>
            <code style="font-size:11px;">${esc(c.hash_anchor)}</code>
          </div>
          <div style="font-size:12px; color:#334155; white-space:pre-wrap;">${esc(c.content)}</div>
        </div>
      `).join('');
    } else {
      const txt = (globalAssets.wiki || {})[key] || 'Not found';
      container.innerHTML = `<pre class="code-pre-light">${esc(txt)}</pre>`;
    }
  }

  async function ensureGraphLoaded(cb) {
    if (globalGraph) { if (cb) cb(); return; }
    const res = await fetch('/api/graph');
    globalGraph = await res.json();
    if (cb) cb();
  }

  function renderSemanticGraph() {
    const container = document.getElementById('semantic-graph-canvas');
    if (!container || !globalGraph || !window.vis) return;
    const sg = ((globalGraph.topology || {}).vis_semantic_graph) || { nodes: [], edges: [] };

    const nodes = new vis.DataSet(sg.nodes.map(n => ({
      id: n.id,
      label: studioLang === 'en' ? n.label_en : n.label_ko,
      shape: n.group === 'hub' ? 'hexagon' : 'dot',
      size: n.group === 'hub' ? 26 : (n.group === 'entity' ? 19 : 16),
      color: {
        background: n.color,
        border: '#ffffff',
        highlight: { background: n.color, border: '#0f172a' }
      },
      font: { color: '#0f172a', size: 12, face: 'Pretendard, sans-serif', bold: n.group === 'hub' },
      raw: n
    })));

    const edges = new vis.DataSet(sg.edges.map((e, i) => ({
      id: 'se-' + i,
      from: e.from,
      to: e.to,
      label: e.is_hub ? e.label_en : (studioLang === 'en' ? e.label_en : e.label_ko),
      width: e.is_hub ? 0.85 : 1.15,
      dashes: e.is_hub,
      arrows: { to: { enabled: true, scaleFactor: 0.55 } },
      color: { color: e.is_hub ? '#94a3b8' : '#64748b', highlight: '#0284c7' },
      font: { size: 10, color: '#475569', align: 'middle', background: 'rgba(255,255,255,0.85)' }
    })));

    semanticNet = new vis.Network(container, { nodes, edges }, {
      physics: { barnesHut: { gravitationalConstant: -3200, springLength: 125, springConstant: 0.04 }, stabilization: { iterations: 120 } },
      interaction: { hover: true, tooltipDelay: 120 }
    });

    semanticNet.on('click', params => {
      const box = document.getElementById('semantic-graph-inspector');
      if (params.nodes && params.nodes.length) {
        const nd = nodes.get(params.nodes[0]).raw;
        box.innerHTML = `<strong>[${esc(studioLang === 'en' ? nd.label_en : nd.label_ko)}]</strong> &middot; Group: <span class="badge human">${esc(nd.group.toUpperCase())}</span><br>${esc(studioLang === 'en' ? nd.desc_en : nd.desc_ko)}`;
      }
    });
  }

  // 7. Stage 3 Property Graph & Dual DDL Viewer
  function updateStage3DdlView() {
    if (!globalGraph) return;
    const isSpanner = activeGraphEngine === 'spanner';
    document.getElementById('st3-ddl-title').textContent = isSpanner
      ? 'Cloud Spanner Graph ISO GQL DDL (create_spanner_graph.sql)'
      : 'BigQuery ISO SQL:2023 Property Graph DDL (create_property_graph.sql)';
    document.getElementById('st3-ddl-code').textContent = isSpanner
      ? (globalGraph.spanner_ddl || '-- Spanner DDL not loaded')
      : (globalGraph.ddl || '-- BigQuery DDL not loaded');

    const benchBox = document.getElementById('st3-benchmark-box');
    if (benchBox) {
      const topo = globalGraph.topology || {};
      const cmp = topo.engine_comparison_benchmark || {};
      const bq = cmp.bigquery || cmp.bigquery_property_graph || {};
      const sp = cmp.spanner || cmp.cloud_spanner_graph || {};
      const fab = topo.graph_fabric_federated_probe || {};
      benchBox.innerHTML = `
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
          <span style="font-weight:800; color:#4f46e5;">[Dual-Engine Benchmark &amp; Graph Fabric (EXTERNAL_QUERY) Telemetry]</span>
          <span class="badge approved">${esc(cmp.runs_per_engine || cmp.runs || 5)}-Run Measured</span>
        </div>
        <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:8px; font-family:var(--font-mono); font-size:11px;">
          <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:6px; padding:6px 8px;">
            <strong style="color:#0284c7;">BigQuery Graph (Default)</strong><br>
            p50: <b>${esc(bq.p50_ms ?? '-')} ms</b> &middot; p95: <b>${esc(bq.p95_ms ?? '-')} ms</b><br>
            Rows: ${esc(bq.row_count ?? bq.rows_returned ?? '-')} &middot; Zero-ETL View
          </div>
          <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:6px; padding:6px 8px;">
            <strong style="color:#4f46e5;">Spanner Graph (Opt-in)</strong><br>
            p50: <b>${esc(sp.p50_ms ?? '-')} ms</b> &middot; p95: <b>${esc(sp.p95_ms ?? '-')} ms</b><br>
            Rows: ${esc(sp.row_count ?? sp.rows_returned ?? '-')} &middot; 100 PU Online
          </div>
          <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:6px; padding:6px 8px;">
            <strong style="color:#059669;">Graph Fabric (EXTERNAL_QUERY)</strong><br>
            Status: <b>${esc(fab.status || '-')}</b> (${esc(fab.elapsed_ms ?? '-')} ms)<br>
            Conn: <code>spanner_fabric_conn</code> (${esc(fab.row_count ?? '-')} rows)
          </div>
        </div>
      `;
    }
  }

  function renderPropertyGraph() {
    const container = document.getElementById('property-graph-canvas');
    if (!container || !globalGraph || !window.vis) return;
    const pg = ((globalGraph.topology || {}).vis_property_graph) || { nodes: [], edges: [] };

    const nodes = new vis.DataSet(pg.nodes.map(n => ({
      id: n.id,
      label: studioLang === 'en' ? n.label_en : n.label_ko,
      shape: n.group === 'hub' ? 'hexagon' : (n.group === 'dw' ? 'box' : 'dot'),
      size: n.group === 'hub' ? 25 : 18,
      margin: 8,
      color: {
        background: n.group === 'dw' ? '#eff6ff' : n.color,
        border: n.color,
        highlight: { background: '#dbeafe', border: '#1d4ed8' }
      },
      font: { color: '#0f172a', size: 12, face: 'Pretendard, sans-serif', bold: true },
      raw: n
    })));

    const edges = new vis.DataSet(pg.edges.map((e, i) => ({
      id: 'pe-' + i,
      from: e.from,
      to: e.to,
      label: e.is_hub ? e.label_en : (studioLang === 'en' ? e.label_en : e.label_ko),
      width: e.is_hub ? 0.85 : 1.15,
      dashes: e.is_hub,
      arrows: { to: { enabled: true, scaleFactor: 0.55 } },
      color: { color: e.is_hub ? '#94a3b8' : '#475569', highlight: '#0d9488' },
      font: { size: 10, color: '#334155', align: 'middle', background: 'rgba(255,255,255,0.85)' }
    })));

    propertyNet = new vis.Network(container, { nodes, edges }, {
      physics: { barnesHut: { gravitationalConstant: -3600, springLength: 135, springConstant: 0.04 }, stabilization: { iterations: 120 } },
      interaction: { hover: true }
    });

    propertyNet.on('click', params => {
      const box = document.getElementById('property-graph-inspector');
      if (params.nodes && params.nodes.length) {
        const nd = nodes.get(params.nodes[0]).raw;
        box.innerHTML = `<strong>[${esc(studioLang === 'en' ? nd.label_en : nd.label_ko)}]</strong> &middot; Source Table: <code>${esc(nd.table)}</code> &middot; Primary Key: <code>${esc(nd.key)}</code> &middot; Rows: <b>${nd.rows}</b> (Zero-ETL Direct Node Projection)`;
      }
    });
  }

  function copyActiveGraphDdl() {
    const code = document.getElementById('st3-ddl-code').textContent;
    navigator.clipboard.writeText(code);
  }

  async function runSampleGqlTraversal() {
    const box = document.getElementById('st3-gql-result');
    box.innerHTML = `<div style="color:#0f766e; font-weight:700;">Running GQL traversal on ${esc(activeGraphEngine.toUpperCase())}...</div>`;
    const res = await fetch('/api/mcp/execute', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ tool_name: 'mcp_query_graph_and_wiki', args: { engine: activeGraphEngine } })
    });
    const d = await res.json();
    box.innerHTML = `
      <div style="font-weight:800; color:#0f766e; margin-bottom:4px;">[GQL Multi-Hop Execution Result · Engine: ${esc(d.graph_engine || activeGraphEngine).toUpperCase()} (${esc(d.elapsed_ms ?? '-')} ms)]</div>
      <div style="font-family:var(--font-mono); font-size:11.5px; margin-bottom:4px;">Graph: <b>${esc(d.graph_name)}</b> &middot; Hops: <b>${d.traversal_hops}</b> &middot; Matched Nodes: <b>${d.matched_nodes}</b> &middot; Backend: <code>${esc(d.bq_job_id || d.spanner_database || '-')}</code></div>
      <div style="font-family:var(--font-mono); font-size:11.5px; color:#1e293b;">Path: ${esc(d.gql_path)}</div>
      <div style="margin-top:4px; font-size:11.5px; color:#059669; font-weight:700;">Grounded Anchors: ${(d.grounded_anchors || []).join(' · ')}</div>
    `;
  }

  async function runDualEngineComparison() {
    const box = document.getElementById('st3-gql-result');
    box.innerHTML = `<div style="color:#4f46e5; font-weight:700;">Running live BigQuery Property Graph vs. Cloud Spanner Graph comparison...</div>`;
    const [bqRes, spRes] = await Promise.all([
      fetch('/api/mcp/execute', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ tool_name: 'mcp_query_graph_and_wiki', args: { engine: 'bigquery' } })
      }).then(r => r.json()),
      fetch('/api/mcp/execute', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ tool_name: 'mcp_query_graph_and_wiki', args: { engine: 'spanner' } })
      }).then(r => r.json())
    ]);
    box.innerHTML = `
      <div style="font-weight:800; color:#4f46e5; margin-bottom:6px;">[Live Side-by-Side Execution · BigQuery Property Graph vs. Cloud Spanner Graph]</div>
      <div style="display:grid; grid-template-columns:1fr 1fr; gap:8px; font-family:var(--font-mono); font-size:11px;">
        <div style="background:#ffffff; border:1px solid #bae6fd; border-radius:6px; padding:8px;">
          <strong style="color:#0284c7;">1. BigQuery Property Graph (SQL:2023)</strong><br>
          Status: <b>${esc(bqRes.status)}</b> &middot; Latency: <b>${esc(bqRes.elapsed_ms ?? '-')} ms</b><br>
          Matched Rows: <b>${esc(bqRes.matched_nodes)}</b> &middot; Job: <code>${esc(bqRes.bq_job_id || '-')}</code><br>
          Anchors: ${(bqRes.grounded_anchors || []).join(', ')}
        </div>
        <div style="background:#ffffff; border:1px solid #c7d2fe; border-radius:6px; padding:8px;">
          <strong style="color:#4f46e5;">2. Cloud Spanner Graph (ISO GQL)</strong><br>
          Status: <b>${esc(spRes.status)}</b> &middot; Latency: <b>${esc(spRes.elapsed_ms ?? '-')} ms</b><br>
          Matched Rows: <b>${esc(spRes.matched_nodes)}</b> &middot; DB: <code>${esc(spRes.spanner_database || '-')}</code><br>
          Anchors: ${(spRes.grounded_anchors || []).join(', ')}
        </div>
      </div>
    `;
  }

  // 8. Stage 4 Modular MCP Suite & AI FDE Console
  async function loadCatalog() {
    const res = await fetch('/api/catalog');
    globalCatalog = await res.json();
    renderMcpCatalog();
  }

  function filterMcpCatalog(cat) {
    mcpFilter = cat;
    document.getElementById('mcp-flt-all').classList.toggle('active', cat === 'all');
    document.getElementById('mcp-flt-stage').classList.toggle('active', cat === 'stage_pipeline');
    document.getElementById('mcp-flt-runtime').classList.toggle('active', cat === 'runtime_domain');
    renderMcpCatalog();
  }

  function renderMcpCatalog() {
    const box = document.getElementById('stage4-mcp-list');
    if (!box) return;
    const items = globalCatalog.filter(t => mcpFilter === 'all' || t.category === mcpFilter);
    box.innerHTML = items.map(t => {
      const isStage = t.category === 'stage_pipeline';
      const stepsHtml = (t.steps || []).map(s => `<span class="mcp-step-chip">✓ ${esc(s)}</span>`).join('');
      return `
        <div class="mcp-tool-card">
          <div style="display:flex; justify-content:space-between; align-items:center; gap:6px; margin-bottom:6px;">
            <code style="font-size:12px; font-weight:800; color:var(--apple-blue);">${esc(t.name)}</code>
            <span class="badge ${isStage ? 'indigo' : 'approved'}">${esc(t.stage || 'RUNTIME')}</span>
          </div>
          <div style="font-size:12px; color:var(--apple-text-primary); line-height:1.5;">${esc(studioLang === 'en' && t.description_en ? t.description_en : t.description)}</div>
          <div class="mcp-step-chips">${stepsHtml}</div>
          <div style="display:flex; justify-content:space-between; align-items:center; margin-top:8px; padding-top:6px; border-top:1px dashed #cbd5e1;">
            <span style="font-size:10.5px; color:var(--apple-text-secondary);">${esc(t.spec_source)}</span>
            <button class="ov-stage-mcp-btn" onclick="openStageMcpModal('${esc(t.name)}')">▶ Step 실행</button>
          </div>
        </div>
      `;
    }).join('');
  }

  function applySample(text) {
    switchTab('stage4');
    const input = document.getElementById('query-input');
    input.value = text;
    input.focus();
  }

  async function sendQuery() {
    const input = document.getElementById('query-input');
    const btn = document.getElementById('send-btn');
    const timeline = document.getElementById('timeline');
    const q = input.value.trim();
    if (!q) return;

    input.disabled = true;
    btn.disabled = true;
    timeline.innerHTML += `<div class="user-bubble-light"><strong>User Inquiry:</strong> ${esc(q)}</div>`;
    timeline.scrollTop = timeline.scrollHeight;

    try {
      const resp = await fetch('/api/query', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ query: q, engine: activeGraphEngine })
      });
      const data = await resp.json();
      if (data.status === 'SUCCESS') {
        const lc = data.lifecycle;
        const sgHtml = (lc.step_1_thought.sub_goals || []).map(sg =>
          `<div>&bull; <strong>[${esc(sg.id)}]</strong> ${esc(sg.goal)} &rarr; <code>${esc(sg.tool)}</code></div>`
        ).join('');
        const toolsHtml = (lc.step_2_tool_dispatch.dispatched_tools || []).map(dt => `
          <div class="obs-box-light">
            <strong>Step 2-${dt.step_index}: Dispatched [${esc(dt.tool_name)}]</strong> (${esc(dt.category)})<br>
            <span>${esc(dt.intermediate_observation)}</span>
          </div>
        `).join('');

        timeline.innerHTML += `
          <div class="trace-card-light">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
              <strong style="color:var(--apple-blue);">[AI FDE Execution Trace · ${esc(data.performance.total_elapsed_seconds)}s]</strong>
              <span class="badge approved">SEQUENTIAL_CHAIN · ${esc(activeGraphEngine.toUpperCase())}</span>
            </div>
            <div class="subgoal-box-light">
              <div style="font-weight:800; margin-bottom:4px;">Step 1: Dynamic Sub-Goal Decomposition</div>
              ${sgHtml}
            </div>
            ${toolsHtml}
            <div style="padding:10px 12px; background:#f8fafc; border-left:3px solid var(--apple-indigo); border-radius:6px; font-size:12.5px; margin-bottom:10px;">
              <strong>Step 3: Cross-Domain Verification</strong> — ${esc(lc.step_3_observation.cross_domain_integration_reason)}
            </div>
            <div style="padding:12px 14px; background:#ffffff; border:1px solid #cbd5e1; border-radius:8px; font-size:13px; line-height:1.65;">
              <pre style="white-space:pre-wrap; font-family:var(--font-sans);">${esc(lc.step_4_synthesis.markdown)}</pre>
            </div>
          </div>
        `;
      }
    } catch (e) {
      timeline.innerHTML += `<div class="trace-card-light" style="border-color:#dc2626; color:#dc2626;">Error: ${esc(e.message)}</div>`;
    } finally {
      input.disabled = false;
      btn.disabled = false;
      input.value = '';
      timeline.scrollTop = timeline.scrollHeight;
    }
  }

  // 9. Stage 5 Lineage & Evaluation
  async function loadLineageAndEvaluation() {
    const t0 = performance.now();
    if (!lineageInitialized) { lineageInitialized = true; setupLineagePanZoom(); }
    const [lg, ev, s3] = await Promise.all([
      fetchLineageGraphData(),
      fetch('/api/eval/summary').then(r => r.json()),
      fetch('/api/mcp/execute', { method: 'POST', headers: {'Content-Type': 'application/json'},
                                  body: JSON.stringify({ tool_name: 'mcp_stage3_property_graph', args: {} }) })
        .then(r => r.json()).catch(e => ({ status: 'ERROR', error: e.message }))
    ]);
    const elapsed = Math.round(performance.now() - t0);
    document.getElementById('lineage-latency-badge').textContent = `Lineage Loaded in ${elapsed} ms`;

    const md = (lg || {}).metadata || {}, st = (lg || {}).stats || {};
    const bq = md.bq_nodes ? [`${md.live_nodes} / ${md.bq_nodes}`, md.bq_error ? '조회 실패: ' + esc(md.bq_error) : esc(md.bq_job_id || 'GCS / Graph')]
      : ['-', '실측 대상 노드 없음'];
    // A project's own stage3 MCP may not return duplicate_keys_total; show N/A instead of "undefined".
    const dup = Number.isFinite(s3.duplicate_keys_total) ? [`${s3.duplicate_keys_total}건`, esc(s3.bq_job_id)]
      : (s3.status === 'SUCCESS' ? ['N/A', 'stage3 MCP가 duplicate_keys_total을 반환하지 않음'] : ['조회 실패', esc(s3.status || s3.error)]);
    document.getElementById('lineage-kpis').innerHTML = [
      ['리니지 노드 / 엣지 / 카테고리', [`${st.total_nodes ?? 0} / ${st.total_edges ?? 0} / ${st.total_categories ?? 0}`, esc(md.fq)], 'var(--apple-blue)'],
      ['실측 노드 (BQ 행 수 · GCS 객체 수 · 그래프 테이블 수)', bq, 'var(--apple-indigo)'],
      ['노드 테이블 중복 키 (BigQuery 실측)', dup, 'var(--apple-emerald)'],
      ['계보 집계 응답 지연', [elapsed + ' ms', 'graph + eval + stage3 MCP 병렬 조회'], 'var(--apple-teal)']
    ].map(([k, [v, cap], c]) => `<div class="metric-box"><div class="metric-title">${k}</div><div class="metric-value" style="color:${c};">${v}</div><div class="ov-metric-cap">${cap}</div></div>`).join('');

    // Evaluation Summary
    document.getElementById('ev-intro').innerHTML = esc(ev.intro);
    const g = ev.golden || {}, b = ev.boundary || {};
    const pct = v => (v === null || v === undefined) ? '미측정' : `${v}%`;
    document.getElementById('ev-kpi-grid').innerHTML = `
      <div class="metric-box"><div class="metric-title">Golden CQ 통과</div><div class="metric-value" style="color:var(--apple-emerald);">${esc(g.score_label || '미측정')}</div><div class="ov-metric-cap">sql: 검증 SQL + 답변 대조 · citation: 청크 인용 + 원문 사실 대조 · 정답 미확정 ${g.unconfirmed ?? '-'}건 · ${esc(g.evaluated_at || '미측정')}</div></div>
      <div class="metric-box"><div class="metric-title">Boundary 성공률</div><div class="metric-value" style="color:var(--apple-blue);">${pct(b.avg_success_rate)}</div><div class="ov-metric-cap">${b.case_count || 0} Cases × ${b.trials_per_case ?? '-'} Trials 실측</div></div>
      <div class="metric-box"><div class="metric-title">응답 일관성</div><div class="metric-value" style="color:var(--apple-indigo);">${pct(b.avg_consistency_rate)}</div><div class="ov-metric-cap">반복 실행 간 (응답 상태, 판정) 일치 비율</div></div>
      <div class="metric-box"><div class="metric-title">의도 안정성</div><div class="metric-value" style="color:var(--apple-teal);">${pct(b.avg_intent_stability)}</div><div class="ov-metric-cap">반복 실행 간 호출 도구 조합 일치 비율 · ${esc(b.model || '')} · ${esc(b.evaluated_at || '미측정')}</div></div>
    `;

    document.getElementById('ev-golden-wrap').innerHTML = `
      <table class="ov-gap-table">
        <thead><tr><th>CQ ID</th><th>카테고리</th><th>검증 질문 (Inquiry Prompt)</th><th>기대 정답 (Expected)</th><th>실측 응답 (Actual)</th><th>근거 앵커</th><th>판정</th></tr></thead>
        <tbody>
          ${(g.rows || []).map(r => `
            <tr>
              <td class="lead-cell">${esc(r.cq_id)}</td>
              <td><span class="badge human">${esc(r.category)}</span></td>
              <td>${esc(r.prompt)}</td>
              <td><code>${esc(r.expected_value)}</code></td>
              <td><code>${esc(r.actual_value)}</code></td>
              <td><span class="badge llm">${esc(r.legal_anchor)}</span></td>
              <td><span class="badge ${r.passed ? 'approved' : 'amber'}">${esc(r.verification_status)}</span></td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    `;

    document.getElementById('ev-boundary-wrap').innerHTML = `
      <table class="ov-gap-table">
        <thead><tr><th>Case ID</th><th>바운더리 질문</th><th>결여 맥락 / 경계 조건</th><th>원인 코드</th><th>성공률</th><th>일관성 / 의도 안정성</th><th>기대 동작 · 실패 사유</th></tr></thead>
        <tbody>
          ${(b.cases || []).map(c => `
            <tr>
              <td class="lead-cell">${esc(c.case_id)}</td>
              <td>${esc(c.query)}</td>
              <td class="muted">${esc(c.missing_context)}</td>
              <td><span class="badge amber">${esc(c.root_cause_code)}</span></td>
              <td style="font-family:var(--font-mono); font-weight:800; color:var(--apple-emerald);">${esc(c.success_rate)}% (${esc(c.passed_trials)}/${esc(c.trials)})</td>
              <td style="font-family:var(--font-mono);">${esc(c.consistency_rate)}% / ${esc(c.intent_stability)}%</td>
              <td>${esc(c.expected_behavior)}${(c.failure_reasons || []).length ? `<br><span class="muted">실패 사유: ${esc(c.failure_reasons.join(' | '))}</span>` : ''}</td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    `;

    document.getElementById('ev-taxonomy-body').innerHTML = (ev.taxonomy || []).map(x => `
      <tr>
        <td class="lead-cell"><code>${esc(x.code)}</code></td>
        <td style="font-weight:700;">${esc(x.name)}</td>
        <td class="muted">${esc(x.signal)}</td>
        <td>${esc(x.fix)}</td>
      </tr>
    `).join('');
  }

  // 9-A. Enterprise Data Lineage DAG (spec: <project>/config/lineage_spec.json, API: /api/lineage/*)
  const LN_W = 290, LN_H = 52;
  let lineageGraph = null, lineageActiveTrace = null, lineageInitialized = false, lineagePreset = 'ALL';
  let lineageScale = 0.85, lineagePanX = 30, lineagePanY = 30, lineagePan = null, lineageDrag = null;

  function lineageNode(id) { return ((lineageGraph || {}).nodes || []).find(n => n.id === id); }
  function lineageBounds() {
    const ns = (lineageGraph || {}).nodes || [];
    return { maxX: Math.max(2600, ...ns.map(n => n.x + LN_W + 60)), maxY: Math.max(1100, ...ns.map(n => n.y + LN_H + 60)) };
  }

  async function fetchLineageGraphData() {
    try {
      const g = await (await fetch('/api/lineage/graph')).json();
      if (!g.nodes) throw new Error(g.error || 'invalid response');
      lineageGraph = g;
    } catch (e) {
      lineageGraph = null;
      document.getElementById('lineage-nodes-layer').innerHTML = `<div class="lineage-empty">Lineage API error: ${esc(e.message)}</div>`;
      return null;
    }
    lineageActiveTrace = null;
    lineagePreset = 'ALL';
    document.getElementById('lineage-node-count').textContent = `${lineageGraph.nodes.length} Nodes`;
    document.getElementById('lineage-edge-count').textContent = `${lineageGraph.edges.length} Edges`;
    document.getElementById('lineage-cat-count').textContent = `${lineageGraph.categories.length} Categories`;
    renderLineageAll();
    setTimeout(fitLineageView, 200);
    return lineageGraph;
  }

  function renderLineageAll() {
    renderLineagePresets();
    renderLineageLegend();
    renderLineageNodes();
    renderLineageEdges();
    updateLineageTransform();
  }

  function renderLineagePresets() {
    const en = studioLang === 'en';
    const items = [{ id: 'ALL', label: '전체 토폴로지', label_en: 'Full Topology' }].concat(lineageGraph.presets || []);
    document.getElementById('lineage-presets').innerHTML = items.map(p =>
      `<button type="button" class="lineage-preset-btn${p.id === lineagePreset ? ' active' : ''}" onclick="filterLineageCategory('${esc(p.id)}')">${esc(en ? (p.label_en || p.label) : p.label)}</button>`).join('');
  }

  function renderLineageLegend() {
    const counts = (lineageGraph.stats || {}).category_counts || {};
    document.getElementById('lineage-legend-body').innerHTML = lineageGraph.categories.map(c => `
      <div class="lineage-legend-row" onclick="filterLineageByCategory('${esc(c.id)}')">
        <div style="display:flex; align-items:center;"><span class="lineage-legend-swatch" style="background-color:${esc(c.color)};"></span><span>${esc(studioLang === 'en' ? c.name : (c.name_ko || c.name))}</span></div>
        <span class="lineage-legend-count">(${counts[c.id] || 0})</span>
      </div>`).join('');
  }

  function renderLineageNodes() {
    const layer = document.getElementById('lineage-nodes-layer');
    const cats = Object.fromEntries(lineageGraph.categories.map(c => [c.id, c]));
    const en = studioLang === 'en';
    const root = (projectList.find(p => p.project_id === activeProject) || {}).root_dir || '.';
    const spec = (root === '.' ? '' : root + '/') + 'config/lineage_spec.json';
    layer.innerHTML = lineageGraph.nodes.length ? '' : `<div class="lineage-empty">${en
      ? `${spec} has no nodes yet (see projects/_template/README.md).`
      : `${spec}에 노드가 없습니다 (projects/_template/README.md 참고).`}</div>`;
    lineageGraph.nodes.forEach(node => {
      const cat = cats[node.cat] || { color: '#64748b', tag: node.cat };
      const title = (en && node.title_en) || node.title;
      const vol = (en && node.volume_en) || node.volume || '';
      const card = document.createElement('div');
      card.className = 'lineage-node-card';
      card.id = 'lineage-card-' + node.id;
      card.dataset.id = node.id;
      card.style.left = node.x + 'px';
      card.style.top = node.y + 'px';
      card.innerHTML = `
        <div class="lineage-color-strip" style="background-color:${esc(cat.color)};"></div>
        <span class="lineage-card-icon" style="color:${esc(cat.color)};">[${esc(cat.tag || node.cat)}]</span>
        <span class="lineage-card-label" title="${esc(title)}">${esc(title)}</span>
        ${vol ? `<span class="lineage-card-badge${node.live ? ' live' : ''}">${esc(vol)}</span>` : ''}`;
      card.addEventListener('mousedown', e => { e.stopPropagation(); startLineageNodeDrag(node, card, e); });
      card.addEventListener('click', e => { e.stopPropagation(); selectLineageNode(node.id); });
      layer.appendChild(card);
    });
  }

  function renderLineageEdges() {
    const b = lineageBounds(), world = document.getElementById('lineage-world-container');
    world.style.width = Math.max(3400, b.maxX) + 'px';
    world.style.height = Math.max(1400, b.maxY) + 'px';
    const nm = Object.fromEntries(lineageGraph.nodes.map(n => [n.id, n]));
    const hl = lineageActiveTrace ? new Set(lineageActiveTrace.highlighted_edges.map(e => e.source + '>' + e.target)) : null;
    document.getElementById('lineage-edges-svg').innerHTML = lineageGraph.edges.map(e => {
      const s = nm[e.source], t = nm[e.target];
      if (!s || !t) return '';
      const x1 = s.x + LN_W, y1 = s.y + LN_H / 2, x2 = t.x, y2 = t.y + LN_H / 2, dx = Math.max(40, Math.abs(x2 - x1) * 0.5);
      const cls = hl ? (hl.has(e.source + '>' + e.target) ? ' highlighted' : ' dimmed') : '';
      return `<path class="lineage-spline-edge${cls}" d="M ${x1} ${y1} C ${x1 + dx} ${y1}, ${x2 - dx} ${y2}, ${x2} ${y2}"></path>`;
    }).join('');
  }

  async function selectLineageNode(nodeId) {
    const t = await (await fetch(`/api/lineage/trace?node_id=${encodeURIComponent(nodeId)}`)).json();
    if (t.error) return;
    lineageActiveTrace = t;
    const hl = new Set(t.highlighted_nodes);
    document.querySelectorAll('.lineage-node-card').forEach(card => {
      card.classList.remove('active-target', 'highlighted', 'dimmed');
      card.classList.add(card.dataset.id === nodeId ? 'active-target' : (hl.has(card.dataset.id) ? 'highlighted' : 'dimmed'));
    });
    renderLineageEdges();
    openLineageDrawer(nodeId);
  }

  function resetLineageHighlight() {
    lineageActiveTrace = null;
    document.querySelectorAll('.lineage-node-card').forEach(c => c.classList.remove('active-target', 'highlighted', 'dimmed'));
    if (lineageGraph) renderLineageEdges();
    closeLineageDrawer();
  }

  async function openLineageDrawer(nodeId) {
    const node = lineageNode(nodeId);
    if (!node) return;
    const en = studioLang === 'en';
    document.getElementById('lineage-drawer-title').textContent = (en ? 'Node: ' : '노드 상세: ') + ((en && node.title_en) || node.title);
    let explanation;
    try {
      explanation = (await (await fetch(`/api/lineage/explain?node_id=${encodeURIComponent(nodeId)}&lang=${studioLang}`)).json()).explanation;
    } catch (e) {
      explanation = en ? 'Summary unavailable.' : '요약을 불러오지 못했습니다.';
    }
    const t = lineageActiveTrace || { highlighted_edges: [], upstream: { count: 0 }, downstream: { count: 0 } };
    const ups = t.highlighted_edges.filter(e => e.target === nodeId);
    const downs = t.highlighted_edges.filter(e => e.source === nodeId);
    const md = lineageGraph.metadata || {};
    const volSrc = node.live_src ? esc(node.live_src) + (node.live ? '' : (en ? ' (lookup failed)' : ' (조회 실패)')) : (en ? 'lineage_spec.json value' : 'lineage_spec.json 기재값');
    const link = (id, label) => `<div class="lineage-link-row" onclick="selectLineageNode('${esc(id)}')"><strong style="color:var(--apple-blue);">${esc(id)}</strong><span style="font-size:10px; color:var(--apple-text-secondary);">${esc(label)}</span></div>`;
    const sec = (label, rows, emptyText) => `<div class="lineage-drawer-section"><div class="lineage-drawer-sec-label">${label}</div>
      <div style="font-size:11px; display:flex; flex-direction:column; gap:5px;">${rows.length ? rows.join('') : `<span style="color:var(--apple-text-secondary);">${emptyText}</span>`}</div></div>`;
    document.getElementById('lineage-drawer-body').innerHTML = `
      <div class="lineage-drawer-section">
        <div class="lineage-drawer-sec-label">${en ? 'RESOURCE METADATA' : '리소스 메타데이터 (Resource Metadata)'}</div>
        <div class="lineage-drawer-prop-row">
          <span class="lineage-prop-k">Category</span><span class="lineage-prop-v">${esc(node.cat)}</span>
          <span class="lineage-prop-k">Resource</span><span class="lineage-prop-v" style="font-family:var(--font-mono); font-size:10.5px; color:var(--apple-blue);">${esc(node.resource)}</span>
          <span class="lineage-prop-k">Volume</span><span class="lineage-prop-v">${esc((en && node.volume_en) || node.volume || '-')}</span>
          <span class="lineage-prop-k">${en ? 'Volume source' : '볼륨 출처'}</span><span class="lineage-prop-v">${volSrc}</span>
          <span class="lineage-prop-k">Description</span><span class="lineage-prop-v">${esc((en && node.desc_en) || node.desc || '')}</span>
        </div>
      </div>
      ${sec(en ? `UPSTREAM DEPENDENCIES (${ups.length})` : `상류 원천 의존도 (Upstream Dependencies: ${ups.length}개)`, ups.map(e => link(e.source, e.label)),
            en ? 'Root node (no upstream)' : '최초 원천 노드 (상류 없음)')}
      ${sec(en ? `DOWNSTREAM IMPACTS (${downs.length})` : `하류 파생 영향도 (Downstream Impacts: ${downs.length}개)`, downs.map(e => link(e.target, e.label)),
            en ? 'Terminal node (no downstream)' : '최종 소비 노드 (하류 없음)')}
      <div class="lineage-agent-card">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
          <strong style="font-size:11.5px; color:var(--apple-blue);">${en ? 'Lineage Summary (rule-based)' : '리니지 요약 (규칙 기반)'}</strong>
          <span class="badge human">${en ? 'Upstream' : '상류'} ${t.upstream.count} · ${en ? 'Downstream' : '하류'} ${t.downstream.count}</span>
        </div>
        <div class="lineage-citation-text">${esc(explanation)}</div>
        <button class="lineage-btn-ask-agent" onclick="askAgentLineage('${esc(node.id)}')">${en ? 'Ask the Stage 4 agent about this lineage chain' : '이 리니지 체인으로 Stage 4 에이전트에 질의하기'}</button>
      </div>`;
    document.getElementById('lineage-drawer').classList.add('open');
  }

  function closeLineageDrawer() { document.getElementById('lineage-drawer').classList.remove('open'); }

  function askAgentLineage(nodeId) {
    applySample(studioLang === 'en'
      ? `Explain the facts of lineage asset [${nodeId}] based on its upstream sources and downstream paths.`
      : `리니지 항목 [${nodeId}]의 원천과 파생 경로를 기반으로 사실관계를 설명해줘`);
  }

  function setupLineagePanZoom() {
    const vp = document.getElementById('lineage-viewport');
    vp.addEventListener('mousedown', e => {
      if (e.target.closest('.lineage-node-card, #lineage-legend-panel, #lineage-drawer, #lineage-minimap')) return;
      lineagePan = { x: e.clientX - lineagePanX, y: e.clientY - lineagePanY };
    });
    window.addEventListener('mousemove', e => {
      if (lineagePan) {
        lineagePanX = e.clientX - lineagePan.x;
        lineagePanY = e.clientY - lineagePan.y;
        updateLineageTransform();
      } else if (lineageDrag) {
        const r = document.getElementById('lineage-world-container').getBoundingClientRect();
        lineageDrag.node.x = Math.round((e.clientX - r.left) / lineageScale - lineageDrag.dx);
        lineageDrag.node.y = Math.round((e.clientY - r.top) / lineageScale - lineageDrag.dy);
        lineageDrag.el.style.left = lineageDrag.node.x + 'px';
        lineageDrag.el.style.top = lineageDrag.node.y + 'px';
        renderLineageEdges();
        updateLineageMinimap();
      }
    });
    window.addEventListener('mouseup', () => { lineagePan = null; lineageDrag = null; });
    vp.addEventListener('wheel', e => {
      e.preventDefault();
      const r = vp.getBoundingClientRect();
      zoomLineageAt(e.deltaY < 0 ? 1.08 : 1 / 1.08, e.clientX - r.left, e.clientY - r.top);
    }, { passive: false });
  }

  function startLineageNodeDrag(node, el, e) {
    const r = el.getBoundingClientRect();
    lineageDrag = { node, el, dx: (e.clientX - r.left) / lineageScale, dy: (e.clientY - r.top) / lineageScale };
  }

  function zoomLineageAt(factor, cx, cy) {
    const prev = lineageScale;
    lineageScale = Math.max(0.2, Math.min(2.5, lineageScale * factor));
    lineagePanX = cx - (cx - lineagePanX) * (lineageScale / prev);
    lineagePanY = cy - (cy - lineagePanY) * (lineageScale / prev);
    updateLineageTransform();
  }

  function zoomLineageBy(factor) {
    const vp = document.getElementById('lineage-viewport');
    zoomLineageAt(factor, vp.clientWidth / 2, vp.clientHeight / 2);
  }

  function updateLineageTransform() {
    document.getElementById('lineage-world-container').style.transform = `translate(${lineagePanX}px, ${lineagePanY}px) scale(${lineageScale})`;
    updateLineageMinimap();
  }

  function updateLineageMinimap() {
    if (!lineageGraph) return;
    const vp = document.getElementById('lineage-viewport'), ind = document.getElementById('lineage-minimap-indicator');
    const b = lineageBounds(), mw = 180, mh = 100;
    const colors = Object.fromEntries(lineageGraph.categories.map(c => [c.id, c.color]));
    document.getElementById('lineage-minimap-svg').innerHTML = lineageGraph.nodes.map(n =>
      `<rect x="${n.x / b.maxX * mw}" y="${n.y / b.maxY * mh}" width="5" height="3" rx="1" fill="${esc(colors[n.cat] || '#64748b')}"></rect>`).join('');
    const x = Math.max(0, Math.min(mw, -lineagePanX / (b.maxX * lineageScale) * mw));
    const y = Math.max(0, Math.min(mh, -lineagePanY / (b.maxY * lineageScale) * mh));
    ind.style.left = x + 'px';
    ind.style.top = y + 'px';
    ind.style.width = Math.max(10, Math.min(mw - x, vp.clientWidth / (b.maxX * lineageScale) * mw)) + 'px';
    ind.style.height = Math.max(10, Math.min(mh - y, vp.clientHeight / (b.maxY * lineageScale) * mh)) + 'px';
  }

  function fitLineageView() {
    const vp = document.getElementById('lineage-viewport'), ns = (lineageGraph || {}).nodes || [];
    if (!vp.clientWidth) return;
    if (!ns.length) { lineageScale = 1; lineagePanX = 0; lineagePanY = 0; updateLineageTransform(); return; }
    const minX = Math.min(...ns.map(n => n.x)), minY = Math.min(...ns.map(n => n.y));
    const maxX = Math.max(...ns.map(n => n.x + LN_W)), maxY = Math.max(...ns.map(n => n.y + LN_H));
    const pad = 60, w = maxX - minX + pad * 2, h = maxY - minY + pad * 2;
    const vw = vp.clientWidth - (document.getElementById('lineage-legend-panel').style.display === 'none' ? 0 : 270);
    lineageScale = Math.min(1, vw / w, vp.clientHeight / h);
    lineagePanX = (vw - w * lineageScale) / 2 - (minX - pad) * lineageScale;
    lineagePanY = (vp.clientHeight - h * lineageScale) / 2 - (minY - pad) * lineageScale;
    updateLineageTransform();
  }

  // Same column layout as src/lineage/lineage_engine.py (restores positions after node drags)
  function untangleLineageLayout() {
    if (!lineageGraph) return;
    const cols = lineageGraph.categories.map(c => lineageGraph.nodes.filter(n => n.cat === c.id));
    const height = Math.max(0, ...cols.map(ns => ns.length * (ns.length > 8 ? 72 : 92)));
    cols.forEach((ns, col) => {
      const step = ns.length > 8 ? 72 : 92;
      ns.forEach((n, i) => {
        n.x = 80 + col * 380;
        n.y = 60 + Math.floor((height - ns.length * step) / 2) + i * step;
        const el = document.getElementById('lineage-card-' + n.id);
        if (el) { el.style.left = n.x + 'px'; el.style.top = n.y + 'px'; }
      });
    });
    renderLineageEdges();
    fitLineageView();
  }

  function toggleLineageLegend() {
    const p = document.getElementById('lineage-legend-panel');
    p.style.display = p.style.display === 'none' ? 'flex' : 'none';
  }

  function filterLineageCategory(presetId) {
    if (!lineageGraph) return;
    lineagePreset = presetId;
    renderLineagePresets();
    const cats = ((lineageGraph.presets || []).find(p => p.id === presetId) || {}).cats;
    document.querySelectorAll('.lineage-node-card').forEach(card => {
      const n = lineageNode(card.dataset.id);
      card.classList.remove('highlighted');
      card.classList.toggle('dimmed', !!cats && !(n && cats.includes(n.cat)));
    });
    if (!cats) document.querySelectorAll('.lineage-spline-edge').forEach(e => e.classList.remove('dimmed'));
  }

  function filterLineageByCategory(catId) {
    document.querySelectorAll('.lineage-node-card').forEach(card => {
      const on = (lineageNode(card.dataset.id) || {}).cat === catId;
      card.classList.toggle('highlighted', on);
      card.classList.toggle('dimmed', !on);
    });
  }

  // 10. Stage Pipeline MCP Modal Runner
  async function openStageMcpModal(toolName) {
    if (!globalCatalog.length) await loadCatalog();
    const tool = globalCatalog.find(t => t.name === toolName) || globalCatalog[0];
    if (!tool) return;
    currentModalTool = tool;
    document.getElementById('modal-mcp-stage').textContent = `${tool.stage || 'MODULAR'} · PIPELINE & STEP RUNNER`;
    document.getElementById('modal-mcp-title').textContent = tool.name;
    document.getElementById('modal-mcp-desc').textContent = tool.description;
    document.getElementById('modal-mcp-steps').innerHTML = (tool.steps || []).map(s => `
      <label style="display:inline-flex; align-items:center; gap:6px; padding:6px 12px; background:#f8fafc; border:1px solid #cbd5e1; border-radius:8px; font-family:var(--font-mono); font-size:12px; cursor:pointer;">
        <input type="checkbox" class="modal-step-cb" value="${esc(s)}" checked> ${esc(s)}
      </label>
    `).join('');
    document.getElementById('modal-mcp-output').textContent = '-- [▶ 선택한 Step 실행] 버튼을 클릭하면 해당 Stage/Runtime MCP가 즉시 실행됩니다.';
    document.getElementById('stage-mcp-modal').classList.add('open');
  }

  function closeStageMcpModal() {
    document.getElementById('stage-mcp-modal').classList.remove('open');
  }

  async function executeModalStageMcp() {
    if (!currentModalTool) return;
    const steps = Array.from(document.querySelectorAll('.modal-step-cb:checked')).map(cb => cb.value);
    const res = await fetch('/api/mcp/execute', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ tool_name: currentModalTool.name, args: { steps, engine: activeGraphEngine } })
    });
    const out = await res.json();
    document.getElementById('modal-mcp-output').textContent = JSON.stringify(out, null, 2);
  }

  // 11. Industry Use Cases Modal
  async function openIndustryModal() {
    const res = await fetch('/api/industry_cases');
    const data = await res.json();
    const body = document.getElementById('industry-modal-body');
    body.innerHTML = (data.segments || []).map(seg => `
      <div style="margin-bottom:14px;">
        <div style="font-size:13px; font-weight:800; color:var(--apple-blue); margin-bottom:6px;">${esc(seg.name)}</div>
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px;">
          ${(seg.cases || []).map(c => `
            <div style="background:#f8fafc; border:1px solid #cbd5e1; border-radius:10px; padding:12px;">
              <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                <strong style="font-size:13px; color:#0f172a;">${esc(c.client)}</strong>
                <span class="badge approved">${esc(c.status)}</span>
              </div>
              <div style="font-size:12px; color:#334155; margin-bottom:4px;">${esc(c.title)}</div>
              <code style="font-size:11px; color:#64748b;">${esc(c.file)}</code>
            </div>
          `).join('')}
        </div>
      </div>
    `).join('');
    document.getElementById('industry-modal').classList.add('open');
  }

  function closeIndustryModal() {
    document.getElementById('industry-modal').classList.remove('open');
  }

  // 12. Track-Driven Project Creation & Step-by-Step Gemini Workbench (GRILL-011)
  async function loadWorkbenchState() {
    try {
      const res = await fetch('/api/project/workbench');
      if (res.ok) {
        workbenchState = await res.json();
        renderWorkbenchBars();
      }
    } catch (e) {
      console.error(e);
    }
  }

  function renderWorkbenchBars() {
    if (!workbenchState) return;
    const wb = workbenchState;
    const isEn = (studioLang === 'en');
    const gcp = wb.gcp || {};
    const stages = wb.stages || {};
    const stageKeys = ['stage1', 'stage2', 'stage3', 'stage4', 'stage5'];
    const stageNames = {
      stage1: isEn ? 'Stage 1. Asset & Upload' : 'Stage 1. 데이터 업로드 & 청킹',
      stage2: isEn ? 'Stage 2. 3-Layer Wiki' : 'Stage 2. Gemini 3-Layer 위키 합성',
      stage3: isEn ? 'Stage 3. Property Graph' : 'Stage 3. 물리 Property Graph 합성',
      stage4: isEn ? 'Stage 4. Agent & Questions' : 'Stage 4. 에이전트 추천 질의 & 런타임',
      stage5: isEn ? 'Stage 5. Golden CQ & Lineage' : 'Stage 5. Golden CQ 검증 & 리니지'
    };
    const runBtnLabels = {
      stage1: isEn ? '1. Run Extract & Gemini Profile' : '1. 문서 청킹 · Gate 0 · Gemini 스키마 분석 실행',
      stage2: isEn ? '1. Synthesize 3-Layer Wiki (Gemini)' : '1. 최신 Gemini로 3-Layer 위키 & 규칙 합성 실행',
      stage3: isEn ? '1. Synthesize Property Graph DDL' : '1. SQL:2023 Property Graph DDL & 토폴로지 합성',
      stage4: isEn ? '1. Generate Domain Agent Questions' : '1. Gemini 도메인 맞춤 추천 질의 생성',
      stage5: isEn ? '1. Synthesize Golden CQ & Lineage' : '1. Gemini 도메인 Golden CQ & 엔드투엔드 리니지 합성'
    };
    const approveBtnLabels = {
      stage1: isEn ? '2. Approve & Load to BigQuery → Stage 2' : '2. 승인 및 BigQuery 데이터셋/테이블 실제 적재 → 다음 단계',
      stage2: isEn ? '2. Approve & Upload to GCS/BQ → Next' : '2. 승인 및 GCS 위키 업로드 · BigQuery 규칙 적재 → 다음 단계',
      stage3: isEn ? '2. Approve & Deploy Graph DDL → Stage 4' : '2. 승인 및 BigQuery Property Graph 실제 배포 → Stage 4',
      stage4: isEn ? '2. Approve & Activate Agent → Stage 5' : '2. 승인 및 에이전트 런타임 활성화 → Stage 5',
      stage5: isEn ? '2. Approve & Run Live CQ Validation' : '2. 승인 및 도메인 Golden CQ 실측 검증 확정'
    };

    stageKeys.forEach(sk => {
      const container = document.getElementById('wb-bar-' + sk);
      if (!container) return;
      const stInfo = stages[sk] || { status: 'PENDING', summary: '' };
      const stCode = stInfo.status || 'PENDING';
      const isBypassed = (stCode === 'BYPASSED');

      const stepperHtml = stageKeys.map(k => {
        const s = (stages[k] || {}).status || 'PENDING';
        const icon = s === 'APPROVED' ? '✓' : (s === 'TRANSFORMED' ? '●' : (s === 'BYPASSED' ? '↷' : '○'));
        return `<span class="wb-step-pill st-${esc(s)} ${k === sk ? 'current' : ''}" onclick="switchTab('${k}')">${icon} ${esc(stageNames[k])}</span>`;
      }).join('');

      const files = wb.uploaded_files || { docs: [], tables: [] };
      const uploadStripHtml = (sk === 'stage1') ? `
        <div class="wb-upload-strip">
          <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap; font-size:12px; color:#1e293b;">
            <span class="badge human">${isEn ? 'Project Input Files' : '업로드된 입력 파일'}</span>
            <span><b>Docs (${(files.docs || []).length}):</b> ${(files.docs || []).map(d => `<code>${esc(d.name)}</code>`).join(', ') || (isEn ? 'None' : '없음')}</span>
            ${wb.track !== 'lite' ? `<span>· <b>CSV Tables (${(files.tables || []).length}):</b> ${(files.tables || []).map(t => `<code>${esc(t.name)} (${t.rows} rows)</code>`).join(', ') || (isEn ? 'None' : '없음')}</span>` : ''}
          </div>
          <div style="display:flex; align-items:center; gap:6px; flex-wrap:wrap;">
            <button class="wb-btn-run" onclick="triggerWorkbenchFileUpload('doc')">+ 문서 업로드 (.md/.txt/.pdf)</button>
            ${wb.track !== 'lite' ? `<button class="wb-btn-run" onclick="triggerWorkbenchFileUpload('table')">+ 정형 CSV 테이블 업로드 (.csv)</button>` : ''}
            <button class="subnav-action-btn" style="padding:5px 10px; font-size:11.5px;" onclick="seedSampleDomainData()">샘플 도메인 데이터 시드</button>
          </div>
        </div>
      ` : '';

      const actionButtonsHtml = isBypassed ? `
        <div style="display:flex; gap:8px; align-items:center;">
          <span class="badge" style="background:#f1f5f9; color:#475569;">Track 1 (Lite) 생략 단계</span>
          <button class="wb-btn-run" onclick="switchTab('stage4')">Stage 4 에이전트로 이동 &rarr;</button>
        </div>
      ` : `
        <div style="display:flex; gap:8px; align-items:center; flex-wrap:wrap;">
          <select class="np-input" style="padding:4px 8px; font-size:11.5px;" onchange="changeWorkbenchModel(this.value)">
            ${(wb.supported_models || ['gemini-3.8-flash', 'gemini-3.1-pro-preview', 'gemini-2.5-pro']).map(m =>
              `<option value="${esc(m)}" ${m === wb.gemini_model ? 'selected' : ''}>Vertex AI: ${esc(m)}</option>`
            ).join('')}
          </select>
          <button class="wb-btn-run" id="wb-run-btn-${sk}" onclick="runWorkbenchStep('${sk}')">${esc(runBtnLabels[sk])}</button>
          <button class="wb-btn-approve" id="wb-app-btn-${sk}" onclick="approveWorkbenchStep('${sk}')">${esc(approveBtnLabels[sk])}</button>
        </div>
      `;

      container.innerHTML = `
        <div class="stage-workbench-bar">
          <div class="wb-top-row">
            <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap;">
              <span class="badge human">STEP-BY-STEP GEMINI WORKBENCH</span>
              <strong style="font-size:12.5px; color:#0f172a;">${esc(wb.project_name || wb.project_id)} (<code>${esc(wb.project_id)}</code>)</strong>
              <span class="badge indigo">Track: ${esc((wb.track || 'full').toUpperCase())}</span>
              <span class="badge approved">BQ: <code>${esc(gcp.project_id)}.${esc(gcp.dataset_id)}</code></span>
              <span class="badge llm">GCS: <code>gs://${esc(gcp.gcs_bucket)}/${esc(gcp.gcs_prefix)}</code></span>
              ${wb.track !== 'lite' ? `<span class="badge human">Graph: <code>${esc(gcp.graph_name)}</code></span>` : ''}
            </div>
            <div class="wb-stepper">${stepperHtml}</div>
          </div>
          ${uploadStripHtml}
          <div class="wb-action-row">
            <div class="wb-summary-text" id="wb-summary-${sk}">
              <span class="badge ${stCode === 'APPROVED' ? 'approved' : (stCode === 'TRANSFORMED' ? 'human' : '')}" style="margin-right:6px;">${esc(stCode)}</span>
              ${esc(stInfo.summary || '단계를 실행하면 Gemini 변환 결과 요약이 여기에 표시됩니다.')}
            </div>
            ${actionButtonsHtml}
          </div>
        </div>
      `;
    });
  }

  function openNewProjectModal() {
    const trkSel = document.getElementById('np-track');
    const engSel = document.getElementById('np-engine');
    if (trkSel) trkSel.value = activeTrack || 'full';
    if (engSel) engSel.value = pkgBuilderState.engine || (activeTrack === 'lite' ? 'none' : 'bigquery');
    refreshNewProjectGcpRecommendations();
    const st = document.getElementById('np-status-msg');
    if (st) st.style.display = 'none';
    document.getElementById('new-project-modal').classList.add('open');
  }

  function closeNewProjectModal() {
    document.getElementById('new-project-modal').classList.remove('open');
  }

  function onNewProjectTrackChange() {
    const trk = document.getElementById('np-track').value;
    const engEl = document.getElementById('np-engine');
    if (trk === 'lite') {
      engEl.value = 'none';
    } else if (engEl.value === 'none') {
      engEl.value = 'bigquery';
    }
    refreshNewProjectGcpRecommendations();
  }

  async function refreshNewProjectGcpRecommendations() {
    const pid = (document.getElementById('np-project-id').value || 'my-ontology').trim();
    const trk = document.getElementById('np-track').value || 'full';
    const eng = document.getElementById('np-engine').value || 'bigquery';
    try {
      const res = await nativeFetch(`/api/projects/recommend_gcp?project_id=${encodeURIComponent(pid)}&track=${encodeURIComponent(trk)}&engine=${encodeURIComponent(eng)}`);
      if (!res.ok) return;
      const g = await res.json();
      document.getElementById('np-gcp-project').value = g.project_id || 'seanjung-poc';
      document.getElementById('np-bq-dataset').value = g.dataset_id || '';
      document.getElementById('np-gcs-bucket').value = g.gcs_bucket || '';
      document.getElementById('np-graph-name').value = g.graph_name || (trk === 'lite' ? '(Lite Track Bypassed)' : '');
    } catch (e) {
      console.error(e);
    }
  }

  async function submitCreateNewProject() {
    const btn = document.getElementById('np-submit-btn');
    const st = document.getElementById('np-status-msg');
    const payload = {
      project_id: document.getElementById('np-project-id').value.trim(),
      project_name: document.getElementById('np-project-name').value.trim(),
      domain: document.getElementById('np-domain').value.trim(),
      track: document.getElementById('np-track').value,
      graph_engine: document.getElementById('np-engine').value,
      gemini_model: document.getElementById('np-model').value,
      seed_sample: document.getElementById('np-seed-sample').checked,
      gcp_overrides: {
        project_id: document.getElementById('np-gcp-project').value.trim(),
        dataset_id: document.getElementById('np-bq-dataset').value.trim(),
        gcs_bucket: document.getElementById('np-gcs-bucket').value.trim(),
        graph_name: document.getElementById('np-graph-name').value.trim()
      }
    };
    btn.disabled = true;
    if (st) {
      st.style.display = 'block';
      st.textContent = '신규 프로젝트 워크스페이스 및 추천 GCP 리소스 구성을 생성 중입니다...';
    }
    try {
      const res = await nativeFetch('/api/projects/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const out = await res.json();
      if (out.status === 'SUCCESS') {
        closeNewProjectModal();
        await loadProjects();
        switchProject(out.project_id);
        switchTab('stage1');
      } else if (st) {
        st.textContent = '생성 오류: ' + (out.error || 'Unknown error');
      }
    } catch (e) {
      if (st) st.textContent = '네트워크 오류: ' + e.message;
    } finally {
      btn.disabled = false;
    }
  }

  async function applyTrackToCurrentProject() {
    try {
      const res = await fetch('/api/project/reconfigure', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          track: activeTrack,
          graph_engine: pkgBuilderState.engine,
          gemini_model: (workbenchState && workbenchState.gemini_model) || 'gemini-3.8-flash'
        })
      });
      const out = await res.json();
      if (out.workbench) {
        workbenchState = out.workbench;
        const p = projectList.find(x => x.project_id === activeProject);
        if (p) {
          p.track = activeTrack;
          p.graph_engine = pkgBuilderState.engine;
        }
        syncTabsWithTrack();
        renderWorkbenchBars();
      }
    } catch (e) {
      console.error(e);
    }
  }

  async function changeWorkbenchModel(newModel) {
    if (!workbenchState) return;
    workbenchState.gemini_model = newModel;
    await applyTrackToCurrentProject();
  }

  function triggerWorkbenchFileUpload(kind) {
    pendingUploadKind = kind || 'auto';
    const inp = document.getElementById('wb-file-input');
    if (!inp) return;
    inp.value = '';
    inp.accept = (kind === 'table') ? '.csv' : '.md,.txt,.pdf,.html,.csv';
    inp.click();
  }

  async function handleWorkbenchFileUpload(fileList) {
    if (!fileList || !fileList.length) return;
    const filesPayload = [];
    for (const f of Array.from(fileList)) {
      const text = await f.text();
      filesPayload.push({ name: f.name, kind: pendingUploadKind, content: text });
    }
    const res = await fetch('/api/project/upload', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ files: filesPayload })
    });
    const out = await res.json();
    if (out.workbench) {
      workbenchState = out.workbench;
      globalAssets = null;
      renderWorkbenchBars();
      ensureAssetsLoaded(() => renderStage1Assets());
    }
  }

  async function seedSampleDomainData() {
    const res = await fetch('/api/project/seed_sample', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({})
    });
    const out = await res.json();
    if (out.workbench) {
      workbenchState = out.workbench;
      globalAssets = null;
      renderWorkbenchBars();
      ensureAssetsLoaded(() => renderStage1Assets());
    }
  }

  async function runWorkbenchStep(stage) {
    const btn = document.getElementById('wb-run-btn-' + stage);
    const sumEl = document.getElementById('wb-summary-' + stage);
    if (btn) btn.disabled = true;
    if (sumEl) sumEl.innerHTML = `<span class="badge human">RUNNING</span> Vertex AI <code>${esc((workbenchState && workbenchState.gemini_model) || 'gemini-3.8-flash')}</code> 변환 및 시맨틱 합성 실행 중...`;
    try {
      const res = await fetch('/api/project/workbench/run_step', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ stage, model_name: (workbenchState && workbenchState.gemini_model) || 'gemini-3.8-flash' })
      });
      const out = await res.json();
      if (out.workbench) {
        workbenchState = out.workbench;
        renderWorkbenchBars();
      }
      if (out.status === 'ERROR') {
        const el = document.getElementById('wb-summary-' + stage);
        if (el) el.innerHTML = `<span class="badge amber" style="margin-right:6px;">ERROR</span>${esc(out.error || '')}`;
        return;
      }
      globalAssets = null; globalGraph = null; lineageGraph = null;
      if (stage === 'stage1') ensureAssetsLoaded(() => renderStage1Assets());
      if (stage === 'stage2') {
        ensureAssetsLoaded(() => showWikiDoc('summary.md', 'wtab-summary'));
        ensureGraphLoaded(() => setTimeout(renderSemanticGraph, 60));
      }
      if (stage === 'stage3') {
        ensureGraphLoaded(() => { updateStage3DdlView(); setTimeout(renderPropertyGraph, 60); });
      }
      if (stage === 'stage4') loadPortalProfile();
      if (stage === 'stage5') loadLineageAndEvaluation();
    } catch (e) {
      if (sumEl) sumEl.textContent = '실행 오류: ' + e.message;
    } finally {
      if (btn) btn.disabled = false;
    }
  }

  async function approveWorkbenchStep(stage) {
    const btn = document.getElementById('wb-app-btn-' + stage);
    const sumEl = document.getElementById('wb-summary-' + stage);
    if (btn) btn.disabled = true;
    if (sumEl) sumEl.innerHTML = `<span class="badge approved">APPROVING &amp; DEPLOYING TO GCP</span> 추천된 GCP 리소스(BigQuery / GCS / Property Graph)에 실제 반영 중...`;
    try {
      const res = await fetch('/api/project/workbench/approve_step', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ stage })
      });
      const out = await res.json();
      if (out.workbench) {
        workbenchState = out.workbench;
        renderWorkbenchBars();
      }
      if (out.status === 'ERROR') {
        const el = document.getElementById('wb-summary-' + stage);
        if (el) el.innerHTML = `<span class="badge amber" style="margin-right:6px;">ERROR</span>${esc(out.error || '')}`;
        return;
      }
      globalAssets = null; globalGraph = null; lineageGraph = null;
      if (out.next_stage && out.next_stage !== 'overview') {
        setTimeout(() => switchTab(out.next_stage), 450);
      } else if (stage === 'stage5') {
        loadLineageAndEvaluation();
      }
    } catch (e) {
      if (sumEl) sumEl.textContent = '승인 오류: ' + e.message;
    } finally {
      if (btn) btn.disabled = false;
    }
  }

  // Init (project list first so every /api call carries the resolved project)
  document.addEventListener('keydown', e => { if (e.key === 'Escape') closeLineageDrawer(); });
  loadProjects().catch(console.error).finally(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const reqProj = urlParams.get('project');
    if (reqProj && projectList.some(p => p.project_id === reqProj)) {
      switchProject(reqProj);
    } else {
      loadPortalProfile();
      loadCatalog();
      loadWorkbenchState();
    }
    const requested = urlParams.get('tab');
    if (requested) switchTab(requested);
    if (urlParams.get('modal') === 'new_project') openNewProjectModal();
  });
</script>
</body>
</html>
"""


INDUSTRY_CASES = {
    "segments": [
        {
            "id": "manufacturing", "name": "스마트 제조 (Manufacturing)",
            "cases": [
                {"client": "스마트 제철소 템플릿 A (Smart Steel Mill)", "status": "아키텍처 템플릿", "title": "스마트 제철 연속 공정 품질 & 설비 예방보전(PdM) 온톨로지", "file": "industry_cases/01_manufacturing/case_smart_steel_mill.md"},
                {"client": "완성차 SDV 템플릿 B (Automotive SDV)", "status": "아키텍처 템플릿", "title": "SDV 부품 BOM & 글로벌 공급망(SCM) 온톨로지", "file": "industry_cases/01_manufacturing/case_automotive_sdv_supply_chain.md"}
            ]
        },
        {
            "id": "finance", "name": "핀테크 & 뱅킹 (Fintech & Banking)",
            "cases": [
                {"client": "인터넷전문은행 템플릿 A (Digital Direct Bank)", "status": "아키텍처 템플릿", "title": "비대면 여신 심사 & DSR 40% 온톨로지", "file": "industry_cases/02_finance/case_digital_bank_unattended_loan_dsr.md"},
                {"client": "원앱 핀테크 템플릿 B (One-App Fintech)", "status": "아키텍처 템플릿", "title": "원앱 멀티금융 중개 & 마이데이터 온톨로지", "file": "industry_cases/02_finance/case_oneapp_fintech_mydata.md"}
            ]
        },
        {
            "id": "retail", "name": "유통 & 이커머스 (Retail & Commerce)",
            "cases": [
                {"client": "편의점·수퍼 가맹 템플릿 A (Convenience Franchise)", "status": "아키텍처 템플릿", "title": "가맹계약 상생 정산 & 옴니채널 재고 온톨로지", "file": "industry_cases/03_retail_commerce/case_convenience_franchise_omnichannel.md"},
                {"client": "옴니채널 풀필먼트 템플릿 B (Omnichannel Fulfillment)", "status": "아키텍처 템플릿", "title": "풀필먼트 SLA & 브랜드 정산 온톨로지", "file": "industry_cases/03_retail_commerce/case_omnichannel_fulfillment_sla.md"}
            ]
        },
        {
            "id": "telecom", "name": "통신 & 미디어 (Telecommunications)",
            "cases": [
                {"client": "모바일 구독 결합 템플릿 A (Mobile Subscription)", "status": "아키텍처 템플릿", "title": "구독 결합 & 멤버십 위약금 온톨로지", "file": "industry_cases/04_telecommunications/case_mobile_subscription_membership.md"},
                {"client": "유무선 결합·전용회선 템플릿 B (Converged B2B SLA)", "status": "아키텍처 템플릿", "title": "유무선 결합 해지 방어 & B2B 회선 SLA 온톨로지", "file": "industry_cases/04_telecommunications/case_converged_bundle_enterprise_sla.md"}
            ]
        }
    ]
}


class StudioHandler(http.server.BaseHTTPRequestHandler):
    def _json(self, obj, code=200):
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(json.dumps(obj, ensure_ascii=False).encode("utf-8"))

    def do_GET(self):
        parsed = urlparse(self.path)
        path, qs = parsed.path, parse_qs(parsed.query)
        arg = lambda k, d="": (qs.get(k) or [d])[0]  # noqa: E731
        if path in ("/", "/index.html"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode("utf-8"))
            return
        if path in ("/docs/architecture/gcp_system_architecture.html", "/docs/architecture/gcp_system_architecture.png"):
            arch_path = os.path.join(BASE_DIR, path.lstrip("/"))
            if os.path.isfile(arch_path):
                ctype = "image/png" if path.endswith(".png") else "text/html; charset=utf-8"
                self.send_response(200)
                self.send_header("Content-Type", ctype)
                self.end_headers()
                with open(arch_path, "rb") as f:
                    self.wfile.write(f.read())
                return
        if path == "/api/config":
            return self._json(load_json_file(STARTER_CONFIG_PATH, {}))
        if path == "/api/industry_cases":
            return self._json(INDUSTRY_CASES)
        if path == "/api/projects":
            return self._json([{**{k: v for k, v in p.items() if k != "root"}, "track": resolve_track(p)[0]} for p in list_projects()])
        if path == "/api/projects/recommend_gcp":
            return self._json(recommend_gcp_resources(arg("project_id", "my-ontology"), arg("track", "full"), arg("engine", "bigquery")))
        try:
            proj = get_project(arg("project") or None)
        except KeyError as e:
            return self._json({"error": str(e)}, 404)
        root = proj["root"]

        if path == "/api/project/workbench":
            return self._json(get_workbench_state(proj))
        elif path == "/api/catalog":
            self._json(get_engine(proj).server.get_tool_catalog())
        elif path == "/api/assets":
            chunks, wiki = [], {}
            chunk_file = os.path.join(root, "data/output/doc_chunks.jsonl")
            if os.path.exists(chunk_file):
                with open(chunk_file, "r", encoding="utf-8") as f:
                    chunks = [json.loads(line) for line in f if line.strip()]
            wiki_dir = os.path.join(root, "data/llm_wiki")
            for fname in (os.listdir(wiki_dir) if os.path.isdir(wiki_dir) else []):
                fpath = os.path.join(wiki_dir, fname)
                if os.path.isfile(fpath) and not fname.startswith("."):
                    with open(fpath, "r", encoding="utf-8") as f:
                        wiki[fname] = json.load(f) if fname.endswith(".json") else f.read()
            tables = {os.path.splitext(os.path.basename(t))[0]: load_csv_table(t)
                      for t in sorted(glob.glob(os.path.join(root, "data/input/03_tables/*.csv")))}
            self._json({"chunks": chunks, "wiki": wiki, "tables": tables, "is_sample": os.path.abspath(root) == BASE_DIR,
                        "manifest": load_json_file("data/output/input_manifest.json", {}, root),
                        "gate0": load_json_file("data/output/gate0_report.json", {}, root)})
        elif path == "/api/graph":
            self._json({
                "ddl": load_text_file("data/output/create_property_graph.sql", "-- BigQuery DDL not yet generated", root),
                "spanner_ddl": load_text_file("data/output/create_spanner_graph.sql", "-- Spanner DDL not yet generated", root),
                "topology": load_json_file("data/output/graph_topology.json", {}, root),
            })
        elif path == "/api/cq":
            self._json(load_json_file(CQ_REPORT_PATH, {"test_results": []}, root))
        elif path == "/api/portal/profile":
            self._json(load_json_file(PORTAL_PROFILE_PATH, {}, root))
        elif path == "/api/eval/summary":
            self._json(build_eval_summary(root))
        elif path == "/api/lineage/graph":
            self._json(get_lineage(proj).build_graph())
        elif path == "/api/lineage/trace":
            self._json(get_lineage(proj).trace(arg("node_id")))
        elif path == "/api/lineage/explain":
            self._json(get_lineage(proj).explain(arg("node_id"), arg("lang", "ko")))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        parsed = urlparse(self.path)
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8")
        data = json.loads(body) if body else {}
        if parsed.path == "/api/projects/create":
            return self._json(create_new_project_workspace(data))
        try:
            proj = get_project((parse_qs(parsed.query).get("project") or [None])[0])
            eng = get_engine(proj)
        except KeyError as e:
            return self._json({"error": str(e)}, 404)
        if parsed.path == "/api/project/reconfigure":
            return self._json(reconfigure_project_track(proj["project_id"], data))
        elif parsed.path == "/api/project/upload":
            return self._json(upload_project_files(proj["project_id"], data))
        elif parsed.path == "/api/project/seed_sample":
            wb = get_workbench_state(proj)
            seed_sample_domain_files(proj["root"], proj["project_id"], wb.get("track", "full"))
            return self._json({"status": "SUCCESS", "workbench": get_workbench_state(proj)})
        elif parsed.path == "/api/project/workbench/run_step":
            return self._json(run_workbench_step(proj["project_id"], data.get("stage", "stage1"), model_name=data.get("model_name")))
        elif parsed.path == "/api/project/workbench/approve_step":
            return self._json(approve_workbench_step(proj["project_id"], data.get("stage", "stage1")))
        elif parsed.path == "/api/query":
            if os.path.abspath(proj["root"]) != BASE_DIR:
                return self._json(execute_custom_project_agent_query(proj, data.get("query", ""), engine=data.get("engine", "bigquery")))
            self._json(eng.execute_cycle(data.get("query", ""), engine=data.get("engine", "bigquery")))
        elif parsed.path == "/api/mcp/execute":
            self._json(eng.server.execute_tool(data.get("tool_name", "mcp_stage1_asset_discovery"), data.get("args", {})))
        else:
            self.send_response(404)
            self.end_headers()


class ThreadingStudioServer(http.server.ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def run_server():
    server = ThreadingStudioServer(("0.0.0.0", PORT), StudioHandler)
    print(f"[STUDIO SERVER RUNNING] listening on 0.0.0.0:{PORT}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    run_server()
