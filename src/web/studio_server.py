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
            "bucket": srv.gcs_bucket, "model": eng.model_name})
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
  #btn-toggle-pii.pii-on { background: rgba(225, 29, 72, 0.12); color: #e11d48; border-color: #e11d48; }
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
        <button class="view-mode-pill" data-tab="stage1" onclick="switchTab('stage1')">Stage 1. Asset</button>
        <button class="view-mode-pill" data-tab="stage2" onclick="switchTab('stage2')">Stage 2. Wiki &amp; Semantic Graph</button>
        <button class="view-mode-pill" data-tab="stage3" onclick="switchTab('stage3')">Stage 3. Property Graph</button>
        <button class="view-mode-pill" data-tab="stage4" onclick="switchTab('stage4')">Stage 4. Agent &amp; MCP</button>
        <button class="view-mode-pill" data-tab="stage5" onclick="switchTab('stage5')">Stage 5. Lineage &amp; Eval</button>
      </div>
      <div style="display:flex; align-items:center; gap:8px;">
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

        <!-- Executive Summary & Interactive Track / Graph Engine Selector -->
        <div class="ov-card ov-hero-card">
          <div class="ov-card-head">
            <span class="ov-eyebrow" data-ko="EXECUTIVE SUMMARY · AGENTIC ONTOLOGY STARTER PACK V2.0" data-en="EXECUTIVE SUMMARY · AGENTIC ONTOLOGY STARTER PACK V2.0">EXECUTIVE SUMMARY · AGENTIC ONTOLOGY STARTER PACK V2.0</span>
            <div style="display:flex; gap:6px; align-items:center; flex-wrap:wrap;">
              <span class="badge approved" data-ko="5-Stage × 9-Step 표준 라이프사이클" data-en="5-Stage × 9-Step Canonical Lifecycle">5-Stage × 9-Step 표준 라이프사이클</span>
              <a class="subnav-action-btn" style="text-decoration:none; padding:3px 10px; font-size:11px;" href="https://github.com/seanjungG/agentic-ontology-starter/blob/main/methodology/ko/METHODOLOGY_KO.md" target="_blank" rel="noopener">방법론 (METHODOLOGY_KO.md)</a>
              <a class="subnav-action-btn" style="text-decoration:none; padding:3px 10px; font-size:11px;" href="https://github.com/seanjungG/agentic-ontology-starter/blob/main/notebooks/ko/stage0_overview_walkthrough_ko.ipynb" target="_blank" rel="noopener">노트북 (ko/stage0_overview_walkthrough_ko.ipynb)</a>
            </div>
          </div>
          <h2 class="ov-h2" data-ko="기업 맞춤형 3-Track 온톨로지 방법론 & BigQuery / Spanner 듀얼 그래프 스타터팩" data-en="Configurable 3-Track Ontology Methodology & BigQuery / Spanner Dual Graph Starter Pack">기업 맞춤형 3-Track 온톨로지 방법론 &amp; BigQuery / Spanner 듀얼 그래프 스타터팩</h2>
          <p class="ov-lead" data-ko="본 스타터팩은 고객 식별자를 비식별화(<code>CUST_DEMO_*</code>)한 슬림 샘플 데이터(정형 원장 4종 + 정책 가이드 2종) 위에 <b>Stage 1~5 모듈형 파이프라인 MCP</b>와 <b>BigQuery Property Graph / Cloud Spanner Graph 듀얼 어댑터</b>를 결합한 참조 아키텍처입니다." data-en="This starter pack combines de-identified sample data (4 DW ledgers + 2 policy guides) with Stage 1~5 modular pipeline MCPs and a dual adapter for BigQuery Property Graph and Cloud Spanner Graph.">
            본 스타터팩은 고객 식별자를 비식별화(<code>CUST_DEMO_*</code>)한 슬림 샘플 데이터(정형 원장 4종 + 정책 가이드 2종) 위에 <b>Stage 1~5 모듈형 파이프라인 MCP</b>와 <b>BigQuery Property Graph / Cloud Spanner Graph 듀얼 어댑터</b>를 결합한 참조 아키텍처입니다.
          </p>

          <div class="ov-config-strip">
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
              </div>
            </div>
          </div>
        </div>

        <!-- SECTION 1: 5-Stage Flow Board -->
        <div class="ov-card">
          <div class="ov-card-head">
            <span class="ov-eyebrow" id="ov-s1-eyebrow">SECTION 1 · 5-STAGE METHODOLOGY &amp; MODULAR MCP PIPELINE</span>
          </div>
          <h2 class="ov-h2" id="ov-s1-title">5-Stage 온톨로지 엔지니어링 방법론과 모듈형 Stage MCP 실행 보드</h2>
          <p class="ov-lead" id="ov-s1-lead"></p>
          <div class="ov-flow-board" id="ov-flow-board"></div>
        </div>

        <!-- SECTION 2: 3-Band Architecture Diagram (.ov-diagram-zone, Light Enterprise HTML/CSS) -->
        <div class="ov-card">
          <div class="ov-card-head">
            <span class="ov-eyebrow teal">SECTION 2 · HYBRID ONTOLOGY &amp; DUAL GRAPH ENGINE ARCHITECTURE</span>
            <div style="display:flex; gap:6px; align-items:center; flex-wrap:wrap;">
              <span class="badge human">Default: BigQuery Property Graph</span>
              <span class="badge indigo">Opt-in: Cloud Spanner Graph + EXTERNAL_QUERY</span>
              <a class="subnav-action-btn" style="text-decoration:none; padding:3px 10px; font-size:11px;" href="/docs/architecture/gcp_system_architecture.html" target="_blank" rel="noopener">GCP 시스템 아키텍처 다이어그램 (HTML)</a>
            </div>
          </div>
          <h2 class="ov-h2" data-ko="비정형 3-Layer Wiki + 정형 Zero-ETL 듀얼 Property Graph + 8대 모듈형 MCP 아키텍처" data-en="Unstructured 3-Layer Wiki + Zero-ETL Dual Property Graph + 8 Modular MCP Architecture">비정형 3-Layer Wiki + 정형 Zero-ETL 듀얼 Property Graph + 8대 모듈형 MCP 아키텍처</h2>
          <div class="ov-diagram-zone">
            <div class="ovd">
              <div class="ovd-band b-teal">
                <div class="ovd-band-head">
                  <span class="ovd-band-title">BAND 1 · Unstructured Policy Track (Stage 1 &amp; Stage 2 · Track 1 Lite / Track 3 Full)</span>
                  <span class="ovd-band-sub">data/input/01_guides/*.md &rarr; data/llm_wiki/*.md &amp; doc_chunks.jsonl</span>
                </div>
                <div class="ovd-flow">
                  <div class="ovd-node">
                    <span class="ovd-node-kicker">RAW POLICY GUIDES</span>
                    <span class="ovd-node-title">약관 · 특례 가이드 2종</span>
                    <span class="ovd-node-desc">180일 의무유지 약관 및 시니어·군입대 면제 특례 원문</span>
                  </div>
                  <div class="ovd-node">
                    <span class="ovd-node-kicker">SHA-256 CHUNKING</span>
                    <span class="ovd-node-title">문단 해시 앵커 (5 Chunks)</span>
                    <span class="ovd-node-desc"><code>DOC_CHUNK_001~005</code> 불변 해시 앵커 및 출처 고정</span>
                  </div>
                  <div class="ovd-node hi-teal">
                    <span class="ovd-node-kicker">KARPATHY 3-LAYER WIKI</span>
                    <span class="ovd-node-title">OKF v0.2 위키 컴파일</span>
                    <span class="ovd-node-desc">Layer 1(Summary) &middot; Layer 2(Entities) &middot; Layer 3(Concepts/Rules)</span>
                  </div>
                  <div class="ovd-node hi-teal">
                    <span class="ovd-node-kicker">SEMANTIC GRAPH</span>
                    <span class="ovd-node-title">시맨틱 그래프 (Stage 2)</span>
                    <span class="ovd-node-desc">Entity=Node, Concept=Edge 표준 시각화 (Sky Blue 허브)</span>
                  </div>
                </div>
              </div>

              <div class="ovd-bridge">
                <span>Semantic &amp; Relational Bridge Binding</span>
                <span class="ovd-pill">SUBSCRIBES_PLAN</span>
                <span class="ovd-pill">BOUND_TO_POLICY</span>
                <span class="ovd-pill">COVERS_DEVICE</span>
                <span class="ovd-pill">REQUIRES_PLAN</span>
                <span class="ovd-pill">APPLIES_RULE</span>
                <span class="ovd-pill">GROUNDED_IN (SHA-256)</span>
              </div>

              <div class="ovd-band b-indigo">
                <div class="ovd-band-head">
                  <span class="ovd-band-title">BAND 2 · Structured DW &amp; Dual Property Graph Track (Stage 3 · BigQuery Graph [Default] / Spanner Graph [Opt-in] / Graph Fabric)</span>
                  <span class="ovd-band-sub">create_property_graph.sql (ISO SQL:2023) &harr; create_spanner_graph.sql (ISO GQL) &harr; EXTERNAL_QUERY(spanner_fabric_conn)</span>
                </div>
                <div class="ovd-flow">
                  <div class="ovd-node">
                    <span class="ovd-node-kicker">5-AXIS ENGINE CHECKLIST</span>
                    <span class="ovd-node-title">5축 그래프 엔진 선택 기준</span>
                    <span class="ovd-node-desc"><code>source_system</code> &middot; <code>latency_slo</code> &middot; <code>concurrency</code> &middot; <code>write_freshness</code> &middot; <code>data_scale</code></span>
                  </div>
                  <div class="ovd-node hi-indigo">
                    <span class="ovd-node-kicker">ENGINE A · DEFAULT (OLAP)</span>
                    <span class="ovd-node-title">BigQuery Property Graph</span>
                    <span class="ovd-node-desc">Zero-ETL 무복제 논리 그래프 &middot; 대규모 DW 분석 및 유휴 비용 0원</span>
                  </div>
                  <div class="ovd-node hi-indigo">
                    <span class="ovd-node-kicker">ENGINE B · OPT-IN (OLTP)</span>
                    <span class="ovd-node-title">Cloud Spanner Graph</span>
                    <span class="ovd-node-desc">100 PU 최소 구성 &middot; 인덱스 포인터 기반 수십~수백 ms 실시간 멀티홉 탐색</span>
                  </div>
                  <div class="ovd-node hi-indigo">
                    <span class="ovd-node-kicker">GRAPH FABRIC (BOTH MODE)</span>
                    <span class="ovd-node-title">BigQuery EXTERNAL_QUERY</span>
                    <span class="ovd-node-desc"><code>spanner_fabric_conn</code>을 통해 Spanner 실시간 그래프와 BigQuery 원장·청크 연합 조인</span>
                  </div>
                </div>
              </div>

              <div class="ovd-band b-purple">
                <div class="ovd-band-head">
                  <span class="ovd-band-title">BAND 3 · Modular MCP Suite &amp; Closed-Loop Evaluation (Stage 4 &amp; Stage 5)</span>
                  <span class="ovd-band-sub">5 Stage Pipeline MCPs + 3 Runtime Execution MCPs &rarr; 4-Tier Lineage &amp; Boundary Eval</span>
                </div>
                <div class="ovd-flow">
                  <div class="ovd-node hi-purple">
                    <span class="ovd-node-kicker">PIPELINE AUTOMATION</span>
                    <span class="ovd-node-title">Stage 1~5 파이프라인 MCP</span>
                    <span class="ovd-node-desc">각 Stage의 세부 Step 배열(<code>steps=[...]</code>) 및 <code>engine</code> 선택 실행</span>
                  </div>
                  <div class="ovd-node hi-purple">
                    <span class="ovd-node-kicker">RUNTIME DOMAIN MCP</span>
                    <span class="ovd-node-title">런타임 실행 MCP 3종</span>
                    <span class="ovd-node-desc">고객원장 조회 &middot; 결정론적 위약금/TCO 산식 &middot; 듀얼 그래프/위키 탐색</span>
                  </div>
                  <div class="ovd-node">
                    <span class="ovd-node-kicker">4-TIER LINEAGE</span>
                    <span class="ovd-node-title">엔드투엔드 데이터 계보</span>
                    <span class="ovd-node-desc">Raw DW/Guide &rarr; OKF Wiki &rarr; Property Graph &rarr; Agent 응답</span>
                  </div>
                  <div class="ovd-node">
                    <span class="ovd-node-kicker">CLOSED-LOOP EVAL</span>
                    <span class="ovd-node-title">Golden CQ 5 &amp; Boundary 10</span>
                    <span class="ovd-node-desc">실제 에이전트(Gemini + BigQuery/Spanner) 반복 실행 결과로 정확도·강건성 실측</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- SECTION 3: Feature Gap Matrix -->
        <div class="ov-card">
          <div class="ov-card-head">
            <span class="ov-eyebrow indigo" id="ov-s2-eyebrow">SECTION 3 · GOOGLE CLOUD NATIVE FOUNDATION VS. STARTER PACK EXTENSIONS</span>
          </div>
          <h2 class="ov-h2" id="ov-s2-title">Google Cloud 네이티브 기반 기술과 스타터팩 모듈형 확장 아키텍처</h2>
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

        <!-- SECTION 4: Measured Metrics -->
        <div class="ov-card">
          <div class="ov-card-head">
            <span class="ov-eyebrow purple" id="ov-s4-eyebrow">SECTION 4 · MEASURED STARTER BENCHMARK &amp; REFERENCE TELEMETRY</span>
          </div>
          <p class="ov-lead" id="ov-s4-note"></p>
          <div class="ov-metric-grid" id="ov-metric-grid"></div>
        </div>

      </div>
    </section>

    <!-- =================================================================== -->
    <!-- TAB 1: STAGE 1. ASSET (De-identified DW Ledgers & Policy Guides)    -->
    <!-- =================================================================== -->
    <section class="tab-panel" id="panel-stage1">
      <div style="display:flex; flex-direction:column; gap:12px; flex:1; min-height:0;">
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
      <div class="fde-native-workspace">
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
    </section>

    <!-- =================================================================== -->
    <!-- TAB 5: STAGE 5. LINEAGE & EVAL (Lineage DAG + Golden/Boundary)      -->
    <!-- =================================================================== -->
    <section class="tab-panel" id="panel-stage5">
      <div class="ov-scroll-wrap">
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
              <button type="button" class="subnav-action-btn" id="btn-toggle-pii" onclick="toggleLineagePii()">PII 숨김됨</button>
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

  function applyProjectMeta() {
    const p = projectList.find(x => x.project_id === activeProject) || {};
    selectTrack(p.track || 'full');
    selectGraphEngine(p.graph_engine || 'bigquery');
    const chips = document.getElementById('agent-sample-chips');  // sample-specific questions
    if (chips) chips.style.display = (p.root_dir && p.root_dir !== '.') ? 'none' : '';
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
      updatePiiButton();
      renderLineageAll();
      if (lineageActiveTrace) selectLineageNode(lineageActiveTrace.selected_node.id);
    }
  }

  // 3. Track & Graph Engine Selectors
  function selectTrack(trackKey) {
    activeTrack = trackKey;
    const labels = {
      'lite': 'Track 1 · Lite (1→2→4)',
      'standard': 'Track 2 · Standard (1→2→3→4)',
      'full': 'Track 3 · Full-Stack (1→5)'
    };
    document.getElementById('hdr-track-badge').textContent = labels[trackKey] || labels.full;
    document.querySelectorAll('#ov-track-selector .segment-btn').forEach((b, idx) => {
      const k = ['lite', 'standard', 'full'][idx];
      b.classList.toggle('active', k === trackKey);
    });
  }

  function selectGraphEngine(engineKey) {
    activeGraphEngine = engineKey;
    const label = engineKey === 'spanner' ? 'Cloud Spanner Graph (ISO GQL)' : 'BigQuery Property Graph';
    document.getElementById('hdr-engine-badge').textContent = label;
    const agPill = document.getElementById('agent-engine-pill');
    if (agPill) agPill.textContent = 'Engine: ' + (engineKey === 'spanner' ? 'Spanner Graph' : 'BigQuery Graph');

    document.querySelectorAll('#ov-engine-selector .segment-btn').forEach((b, idx) => {
      const k = ['bigquery', 'spanner'][idx];
      b.classList.toggle('active', k === engineKey);
    });
    ['st3', 'st4'].forEach(prefix => {
      const bqBtn = document.getElementById(prefix + '-btn-bq');
      const spBtn = document.getElementById(prefix + '-btn-sp');
      if (bqBtn && spBtn) {
        bqBtn.classList.toggle('active', engineKey === 'bigquery');
        spBtn.classList.toggle('active', engineKey === 'spanner');
      }
    });
    if (globalGraph) updateStage3DdlView();
  }

  // 4. Overview Loader
  async function loadPortalProfile() {
    try {
      const res = await fetch('/api/portal/profile');
      const p = await res.json();
      const ov = p.overview || {};
      document.getElementById('ov-s1-eyebrow').textContent = esc(ov.eyebrow);
      document.getElementById('ov-s1-title').textContent = esc(ov.title);
      document.getElementById('ov-s1-lead').innerHTML = esc(ov.lead);

      const board = document.getElementById('ov-flow-board');
      board.innerHTML = (ov.stages || []).map(st => {
        const steps = (st.steps || []).map((sp, i) => `
          ${i > 0 ? '<div class="ov-conn-v">&darr;</div>' : ''}
          <div class="ov-step-box" style="border-left-color:${esc(st.accent)};" onclick="switchTab('${esc(st.stage_id || 'stage1')}')">
            <div class="ov-step-badge" style="color:${esc(st.accent)};">${esc(sp.badge)}</div>
            <div class="ov-step-title">${esc(sp.title)}</div>
            <div class="ov-step-desc">${(sp.bullets || []).map(b => '&bull; ' + b).join('<br>')}</div>
            ${sp.deliverables ? `<div class="ov-step-out"><b>산출물</b> ${sp.deliverables}</div>` : ''}
          </div>`).join('');
        return `<div class="ov-stage-col" style="border-top-color:${esc(st.accent)};">
            <div class="ov-stage-head-row">
              <span class="ov-stage-chip">${esc(st.chip)}</span>
              <button class="ov-stage-mcp-btn" onclick="openStageMcpModal('${esc(st.mcp_tool || 'mcp_stage1_asset_discovery')}')">▶ ${esc(st.chip)} MCP</button>
            </div>
            <div class="ov-stage-name">${esc(st.name)}</div>
            <div style="display:flex; gap:6px; flex-wrap:wrap; margin-bottom:2px;">
              ${st.methodology_doc ? `<a class="subnav-action-btn" style="text-decoration:none; padding:2px 8px; font-size:10.5px;" href="https://github.com/seanjungG/agentic-ontology-starter/blob/main/${esc(st.methodology_doc)}" target="_blank" rel="noopener">방법론</a>` : ""}
              ${st.notebook ? `<a class="subnav-action-btn" style="text-decoration:none; padding:2px 8px; font-size:10.5px;" href="https://github.com/seanjungG/agentic-ontology-starter/blob/main/${esc(st.notebook)}" target="_blank" rel="noopener">노트북</a>` : ""}
            </div>
            ${steps}
          </div>`;
      }).join('');

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
    const bq = md.bq_status === 'SUCCESS' ? [`${md.live_nodes} / ${md.bq_nodes}`, esc(md.bq_job_id)]
      : (md.bq_nodes ? ['조회 실패', esc(md.bq_error || md.bq_status)] : ['-', 'bq_table 지정 노드 없음']);
    // A project's own stage3 MCP may not return duplicate_keys_total; show N/A instead of "undefined".
    const dup = Number.isFinite(s3.duplicate_keys_total) ? [`${s3.duplicate_keys_total}건`, esc(s3.bq_job_id)]
      : (s3.status === 'SUCCESS' ? ['N/A', 'stage3 MCP가 duplicate_keys_total을 반환하지 않음'] : ['조회 실패', esc(s3.status || s3.error)]);
    document.getElementById('lineage-kpis').innerHTML = [
      ['리니지 노드 / 엣지 / 카테고리', [`${st.total_nodes ?? 0} / ${st.total_edges ?? 0} / ${st.total_categories ?? 0}`, `${esc(md.fq)} · PII ${st.pii_layer_visible ? '표시' : '숨김'}`], 'var(--apple-blue)'],
      ['BigQuery 실측 노드 (__TABLES__)', bq, 'var(--apple-indigo)'],
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
  let lineageGraph = null, lineageActiveTrace = null, lineageInitialized = false, lineageIncludePii = false, lineagePreset = 'ALL';
  let lineageScale = 0.85, lineagePanX = 30, lineagePanY = 30, lineagePan = null, lineageDrag = null;

  function lineageNode(id) { return ((lineageGraph || {}).nodes || []).find(n => n.id === id); }
  function lineageBounds() {
    const ns = (lineageGraph || {}).nodes || [];
    return { maxX: Math.max(2600, ...ns.map(n => n.x + LN_W + 60)), maxY: Math.max(1100, ...ns.map(n => n.y + LN_H + 60)) };
  }

  async function fetchLineageGraphData() {
    try {
      const g = await (await fetch(`/api/lineage/graph?include_pii=${lineageIncludePii}`)).json();
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
    const t = await (await fetch(`/api/lineage/trace?node_id=${encodeURIComponent(nodeId)}&include_pii=${lineageIncludePii}`)).json();
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
      explanation = (await (await fetch(`/api/lineage/explain?node_id=${encodeURIComponent(nodeId)}&include_pii=${lineageIncludePii}&lang=${studioLang}`)).json()).explanation;
    } catch (e) {
      explanation = en ? 'Summary unavailable.' : '요약을 불러오지 못했습니다.';
    }
    const t = lineageActiveTrace || { highlighted_edges: [], upstream: { count: 0 }, downstream: { count: 0 } };
    const ups = t.highlighted_edges.filter(e => e.target === nodeId);
    const downs = t.highlighted_edges.filter(e => e.source === nodeId);
    const md = lineageGraph.metadata || {};
    const volSrc = node.live ? `BigQuery __TABLES__ (${esc(md.bq_job_id || '-')})` : (en ? 'lineage_spec.json value' : 'lineage_spec.json 기재값');
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
    lineageGraph.categories.forEach((c, col) => {
      const ns = lineageGraph.nodes.filter(n => n.cat === c.id);
      ns.forEach((n, i) => {
        n.x = 80 + col * 380;
        n.y = 60 + i * (ns.length > 8 ? 72 : 92);
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

  function updatePiiButton() {
    const btn = document.getElementById('btn-toggle-pii');
    btn.classList.toggle('pii-on', lineageIncludePii);
    btn.textContent = studioLang === 'en' ? (lineageIncludePii ? 'PII Visible' : 'PII Hidden') : (lineageIncludePii ? 'PII 표시중' : 'PII 숨김됨');
  }

  async function toggleLineagePii() {
    lineageIncludePii = !lineageIncludePii;
    updatePiiButton();
    closeLineageDrawer();
    await fetchLineageGraphData();
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

  // Init (project list first so every /api call carries the resolved project)
  document.addEventListener('keydown', e => { if (e.key === 'Escape') closeLineageDrawer(); });
  loadProjects().catch(console.error).finally(() => {
    loadPortalProfile();
    loadCatalog();
    const requested = new URLSearchParams(window.location.search).get('tab');
    if (requested) switchTab(requested);
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
        try:
            proj = get_project(arg("project") or None)
        except KeyError as e:
            return self._json({"error": str(e)}, 404)
        root = proj["root"]

        if path == "/api/catalog":
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
            self._json(get_lineage(proj).build_graph(arg("include_pii") == "true"))
        elif path == "/api/lineage/trace":
            self._json(get_lineage(proj).trace(arg("node_id"), arg("include_pii") == "true"))
        elif path == "/api/lineage/explain":
            self._json(get_lineage(proj).explain(arg("node_id"), arg("include_pii") == "true", arg("lang", "ko")))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        parsed = urlparse(self.path)
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8")
        data = json.loads(body) if body else {}
        try:
            eng = get_engine(get_project((parse_qs(parsed.query).get("project") or [None])[0]))
        except KeyError as e:
            return self._json({"error": str(e)}, 404)
        if parsed.path == "/api/query":
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
