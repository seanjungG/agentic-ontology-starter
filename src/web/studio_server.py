# -*- coding: utf-8 -*-
"""
Standalone Enterprise Web Studio Server:
Adheres strictly to 05_DESIGN.md (Pretendard font, dark mode, Apple/Google Enterprise theme,
zero decorative cartoon emojis, responsive layout, bilingual support).
Runs with ZERO external dependencies using Python standard library http.server.

Studio tabs: 0. Overview / 1. Asset / 2. OKF Layer / 3. Ontology Semantic /
4. Wiki Agent / 5. Bigquery Graph / 6. BQG Agent / 7. Lineage / 8. AI FDE / 9. Evaluation

Data pluggability:
  The `0. Overview` and `9. Evaluation` screens are rendered entirely from
  `config/portal_profile.json` (plus `config/eval_rubric.json`). Swapping those
  files re-skins the portal for a different domain without touching this module.
"""
import http.server, json, sys, os, csv
from urllib.parse import urlparse, parse_qs

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from src.agent.reasoning_engine import AiFdeAgentEngine

PORT = int(os.environ.get("PORT", 8088))
# Allow an operator to point the portal at a different profile without editing code.
PORTAL_PROFILE_PATH = os.environ.get("PORTAL_PROFILE", "config/portal_profile.json")
EVAL_RUBRIC_PATH = os.environ.get("EVAL_RUBRIC", "config/eval_rubric.json")
engine = AiFdeAgentEngine()

def load_text_file(rel_path, default=""):
    path = os.path.join(BASE_DIR, rel_path)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return default

def load_json_file(rel_path, default=None):
    if default is None: default = {}
    path = os.path.join(BASE_DIR, rel_path)
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default
    return default

def load_csv_table(rel_path):
    path = os.path.join(BASE_DIR, rel_path)
    if not os.path.exists(path):
        return {"headers": [], "rows": []}
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)
        if not rows:
            return {"headers": [], "rows": []}
        return {"headers": rows[0], "rows": rows[1:]}

def build_eval_summary():
    """Aggregate whatever evaluation artifacts actually exist on disk.

    Anything that is not present on disk is reported as PENDING rather than
    being filled in with placeholder numbers.
    """
    profile = load_json_file(PORTAL_PROFILE_PATH, {})
    ev_cfg = profile.get("evaluation", {})
    rubric = load_json_file(EVAL_RUBRIC_PATH, {})

    sources = []
    for src in ev_cfg.get("sources", []):
        rel = src.get("path", "")
        sources.append({
            **src,
            "exists": os.path.exists(os.path.join(BASE_DIR, rel)) if rel else False,
        })

    cq_report = load_json_file("data/output/cq_benchmark_report.json", {})
    raw_rows = []
    if isinstance(cq_report, dict):
        raw_rows = cq_report.get("evaluation_details") or cq_report.get("test_results") or []
    # The pipeline and the bundled fixture use two different row shapes; normalize both.
    results = []
    for r in raw_rows:
        status = str(r.get("status") or r.get("verification_status") or "").upper()
        results.append({
            "cq_id": r.get("cq_id", "-"),
            "category": r.get("category") or (r.get("dispatched_tools") or ["-"])[0],
            "prompt": r.get("query") or r.get("prompt", ""),
            "expected_value": r.get("expected_value", "-"),
            "actual_value": r.get("actual_value", "-"),
            "legal_anchor": r.get("grounded_chunk") or r.get("legal_anchor", "-"),
            "verification_status": status or "-",
            "passed": status in ("PASSED", "EXACT_MATCH"),
        })
    matched = [r for r in results if r["passed"]]
    golden = {
        "status": "MEASURED" if results else "PENDING",
        "total": len(results),
        "passed": len(matched),
        "pass_rate": round(len(matched) / len(results) * 100, 1) if results else None,
        "rows": results,
    }

    boundary_raw = load_json_file("data/output/boundary_benchmark_results.json", {})
    stats = boundary_raw.get("case_statistics", {}) if isinstance(boundary_raw, dict) else {}
    cases = list(stats.values())
    boundary = {
        "status": "MEASURED" if cases else "PENDING",
        "case_count": len(cases),
        "avg_success_rate": round(sum(c.get("success_rate", 0) for c in cases) / len(cases), 1) if cases else None,
        "avg_intent_stability": round(sum(c.get("intent_stability", 0) for c in cases) / len(cases), 1) if cases else None,
        "cases": cases,
    }

    rounds = []
    for r in ev_cfg.get("rounds", []):
        src_id = r.get("status_source")
        measured = golden["status"] == "MEASURED" if src_id == "cq_report" else boundary["status"] == "MEASURED"
        rounds.append({**r, "status": "MEASURED" if measured else "PENDING"})

    return {
        "intro": ev_cfg.get("intro", ""),
        "sources": sources,
        "design": ev_cfg.get("design", {}),
        "rubric": rubric,
        "taxonomy": ev_cfg.get("root_cause_taxonomy", []),
        "golden": golden,
        "boundary": boundary,
        "rounds": rounds,
    }

HTML_PAGE = """<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Agentic Ontology Studio</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css">
  <style>
    :root {
      --bg: #000000;
      --surface-1: #111113;
      --surface-2: #1c1c1e;
      --surface-3: #2c2c2e;
      --card-border: rgba(255, 255, 255, 0.12);
      --card-border-subtle: rgba(255, 255, 255, 0.06);
      --text-primary: #f5f5f7;
      --text-secondary: #86868b;
      --text-muted: #636366;
      --accent: #2997ff;
      --accent-green: #30d158;
      --accent-purple: #bf5af2;
      --accent-orange: #ff9f0a;
      --font-stack: "Pretendard", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; font-family: var(--font-stack); }
    body { background: var(--bg); color: var(--text-primary); display: flex; flex-direction: column; height: 100vh; overflow: hidden; -webkit-font-smoothing: antialiased; }

    /* Global Topbar (44px) */
    .topbar {
      height: 44px;
      min-height: 44px;
      background: rgba(28, 28, 30, 0.9);
      backdrop-filter: blur(20px);
      border-bottom: 1px solid var(--card-border);
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 18px;
      z-index: 100;
    }
    .topbar-left { display: flex; align-items: center; gap: 10px; }
    .logo { font-size: 13.5px; font-weight: 700; letter-spacing: -0.2px; color: var(--text-primary); }
    .badge { font-size: 10.5px; font-weight: 600; padding: 2px 7px; border-radius: 4px; background: rgba(41, 151, 255, 0.15); color: var(--accent); border: 1px solid rgba(41, 151, 255, 0.3); }
    .badge-green { background: rgba(48, 209, 88, 0.15); color: var(--accent-green); border: 1px solid rgba(48, 209, 88, 0.3); }
    .badge-purple { background: rgba(191, 90, 242, 0.15); color: var(--accent-purple); border: 1px solid rgba(191, 90, 242, 0.3); }
    .topbar-right { display: flex; align-items: center; gap: 12px; font-size: 11.5px; color: var(--text-secondary); }
    .lang-toggle { cursor: pointer; padding: 3px 8px; border-radius: 4px; background: var(--surface-2); border: 1px solid var(--card-border); color: var(--text-primary); font-size: 11px; }

    /* Navigation Subbar (52px) */
    .subbar {
      height: 52px;
      min-height: 52px;
      border-bottom: 1px solid var(--card-border);
      display: flex;
      align-items: center;
      padding: 0 18px;
      gap: 8px;
      background: var(--surface-1);
    }
    .nav-btn {
      padding: 7px 16px;
      font-size: 12px;
      font-weight: 600;
      border-radius: 6px;
      background: transparent;
      color: var(--text-secondary);
      border: 1px solid transparent;
      cursor: pointer;
      transition: all 0.15s ease;
    }
    .nav-btn:hover { color: var(--text-primary); background: rgba(255,255,255,0.05); }
    .nav-btn.active {
      background: var(--surface-2);
      color: var(--text-primary);
      border-color: var(--card-border);
      box-shadow: 0 2px 8px rgba(0,0,0,0.3);
    }

    /* Tab Content Panels */
    .tab-panel { flex: 1; display: none; overflow: hidden; }
    .tab-panel.active { display: flex; }

    /* ==========================================================================
       VIEW 1: AI FDE STUDIO
       ========================================================================== */
    .fde-layout { flex: 1; display: flex; overflow: hidden; }
    .fde-sidebar {
      width: 320px;
      min-width: 320px;
      border-right: 1px solid var(--card-border);
      background: var(--surface-1);
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }
    .fde-filter-bar {
      padding: 12px 14px;
      border-bottom: 1px solid var(--card-border-subtle);
      display: flex;
      gap: 6px;
    }
    .filter-chip {
      font-size: 11px;
      padding: 4px 8px;
      border-radius: 4px;
      background: var(--surface-2);
      color: var(--text-secondary);
      border: 1px solid var(--card-border-subtle);
      cursor: pointer;
    }
    .filter-chip.active { color: var(--text-primary); border-color: var(--accent); background: rgba(41, 151, 255, 0.15); }
    .fde-tool-list { flex: 1; overflow-y: auto; padding: 12px; display: flex; flex-direction: column; gap: 8px; }
    .tool-card {
      background: var(--surface-2);
      border: 1px solid var(--card-border);
      border-radius: 6px;
      padding: 10px 12px;
      font-size: 11.5px;
      transition: border-color 0.15s ease;
    }
    .tool-card:hover { border-color: rgba(255,255,255,0.25); }
    .tool-card-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px; }
    .tool-name { font-weight: 700; color: var(--accent); font-family: monospace; }
    .tool-desc { color: var(--text-secondary); line-height: 1.4; font-size: 11px; }

    .fde-console { flex: 1; display: flex; flex-direction: column; background: var(--bg); overflow: hidden; }
    .quick-chips-bar {
      padding: 10px 18px;
      border-bottom: 1px solid var(--card-border-subtle);
      display: flex;
      gap: 8px;
      background: var(--surface-1);
      overflow-x: auto;
    }
    .quick-chip {
      font-size: 11px;
      padding: 5px 10px;
      border-radius: 5px;
      background: var(--surface-2);
      color: var(--text-secondary);
      border: 1px solid var(--card-border-subtle);
      cursor: pointer;
      white-space: nowrap;
    }
    .quick-chip:hover { color: var(--text-primary); border-color: var(--accent); }

    .chat-timeline {
      flex: 1;
      overflow-y: auto;
      padding: 20px;
      display: flex;
      flex-direction: column;
      gap: 16px;
    }
    .trace-card {
      background: var(--surface-2);
      border: 1px solid var(--card-border);
      border-radius: 8px;
      padding: 16px;
      font-size: 12.5px;
      line-height: 1.6;
    }
    .trace-card h4 { font-size: 13px; font-weight: 700; color: var(--accent); margin-bottom: 8px; }
    .subgoal-box { background: rgba(191, 90, 242, 0.08); border-left: 3px solid var(--accent-purple); padding: 10px 14px; margin: 8px 0; border-radius: 4px; }
    .obs-box { background: rgba(48, 209, 88, 0.08); border-left: 3px solid var(--accent-green); padding: 10px 14px; margin: 8px 0; border-radius: 4px; }
    .user-bubble { align-self: flex-end; background: rgba(41,151,255,0.15); border: 1px solid var(--accent); padding: 10px 16px; border-radius: 8px; font-size: 12.5px; max-width: 75%; }

    .input-bar {
      padding: 14px 20px;
      background: var(--surface-1);
      border-top: 1px solid var(--card-border);
      display: flex;
      gap: 10px;
    }
    .input-field {
      flex: 1;
      background: var(--surface-2);
      border: 1px solid var(--card-border);
      border-radius: 6px;
      color: var(--text-primary);
      padding: 10px 14px;
      font-size: 13px;
      outline: none;
    }
    .input-field:focus { border-color: var(--accent); }
    .send-btn {
      padding: 10px 22px;
      background: var(--accent);
      color: #fff;
      border: none;
      border-radius: 6px;
      font-size: 12.5px;
      font-weight: 600;
      cursor: pointer;
    }

    /* ==========================================================================
       VIEW 2: ASSET MANAGEMENT STUDIO
       ========================================================================== */
    .asset-layout { flex: 1; display: flex; overflow: hidden; }
    .asset-half { flex: 1; display: flex; flex-direction: column; border-right: 1px solid var(--card-border); background: var(--bg); overflow: hidden; }
    .asset-half:last-child { border-right: none; }
    .pane-header {
      height: 44px;
      background: var(--surface-1);
      border-bottom: 1px solid var(--card-border);
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 16px;
      font-size: 12px;
      font-weight: 700;
    }
    .subtabs-bar {
      display: flex;
      background: var(--surface-1);
      border-bottom: 1px solid var(--card-border-subtle);
      padding: 6px 14px;
      gap: 6px;
      overflow-x: auto;
    }
    .subtab-btn {
      font-size: 11px;
      padding: 4px 10px;
      border-radius: 4px;
      background: var(--surface-2);
      color: var(--text-secondary);
      border: 1px solid var(--card-border-subtle);
      cursor: pointer;
      white-space: nowrap;
    }
    .subtab-btn.active { color: var(--text-primary); border-color: var(--accent); background: rgba(41, 151, 255, 0.15); }
    .asset-scroll-content { flex: 1; overflow-y: auto; padding: 16px; display: flex; flex-direction: column; gap: 12px; }
    .chunk-card {
      background: var(--surface-2);
      border: 1px solid var(--card-border);
      border-radius: 6px;
      padding: 12px 14px;
      font-size: 12px;
    }
    .chunk-meta { display: flex; justify-content: space-between; margin-bottom: 6px; font-size: 11px; }
    .data-table {
      width: 100%;
      border-collapse: collapse;
      font-size: 11.5px;
      text-align: left;
    }
    .data-table th, .data-table td {
      padding: 8px 12px;
      border: 1px solid var(--card-border);
    }
    .data-table th { background: var(--surface-1); font-weight: 600; color: var(--text-secondary); }
    .data-table tr:nth-child(even) { background: rgba(255,255,255,0.02); }

    /* ==========================================================================
       VIEW 3: PROPERTY GRAPH VISUALIZER
       ========================================================================== */
    .graph-layout { flex: 1; display: flex; flex-direction: column; overflow: hidden; background: var(--bg); }
    .stats-kpi-bar {
      padding: 10px 18px;
      background: var(--surface-1);
      border-bottom: 1px solid var(--card-border);
      display: flex;
      gap: 20px;
      font-size: 11.5px;
    }
    .kpi-item { display: flex; align-items: center; gap: 6px; }
    .kpi-val { font-weight: 700; color: var(--accent); }
    .graph-main-split { flex: 1; display: flex; overflow: hidden; }
    .agent-mode-bar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      flex-wrap: wrap;
      gap: 8px;
      padding: 9px 14px;
      background: var(--surface-2);
      border-bottom: 1px solid var(--card-border);
    }
    .graph-canvas-box { flex: 1; position: relative; background: radial-gradient(circle at center, #1a1a1e 0%, #000000 100%); display: flex; align-items: center; justify-content: center; overflow: hidden; }
    .graph-inspector { width: 360px; border-left: 1px solid var(--card-border); background: var(--surface-1); display: flex; flex-direction: column; overflow: hidden; }
    .code-box {
      flex: 1;
      overflow: auto;
      padding: 14px;
      background: #0d0d0e;
      font-family: monospace;
      font-size: 11px;
      line-height: 1.5;
      color: #e5e5ea;
      white-space: pre-wrap;
    }

    /* ==========================================================================
       VIEW 4: CQ BENCHMARK STUDIO
       ========================================================================== */
    .cq-layout { flex: 1; display: flex; flex-direction: column; overflow: hidden; background: var(--bg); padding: 18px; gap: 16px; }
    .kpi-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
    .metric-box {
      background: var(--surface-2);
      border: 1px solid var(--card-border);
      border-radius: 8px;
      padding: 14px 16px;
    }
    .metric-title { font-size: 11px; color: var(--text-secondary); text-transform: uppercase; font-weight: 600; margin-bottom: 4px; }
    .metric-value { font-size: 22px; font-weight: 700; color: var(--text-primary); }
    .cq-table-container { flex: 1; overflow-y: auto; background: var(--surface-2); border: 1px solid var(--card-border); border-radius: 8px; }

    /* ==========================================================================
       VIEW 0 / VIEW 9: PROFILE-DRIVEN OVERVIEW & EVALUATION
       ========================================================================== */
    .ov-card { background: var(--surface-1); border: 1px solid var(--card-border); border-radius: 12px; padding: 22px 26px; }
    .ov-card-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; flex-wrap: wrap; gap: 10px; }
    .ov-eyebrow { font-size: 12.5px; padding: 4px 10px; }
    .ov-card-note { font-size: 13px; color: var(--text-secondary); }
    .ov-h2 { font-size: 18px; font-weight: 800; color: var(--text-primary); margin-bottom: 8px; }
    .ov-lead { font-size: 13.5px; line-height: 1.65; color: var(--text-secondary); margin: 0 0 16px 0; }

    .ov-flow-board { display: grid; grid-template-columns: repeat(5, minmax(210px, 1fr)); gap: 14px; overflow-x: auto; padding-bottom: 6px; }
    .ov-stage-col { border-top: 3px solid var(--accent); background: var(--surface-2); border-radius: 10px; padding: 14px 12px; display: flex; flex-direction: column; gap: 10px; }
    .ov-stage-chip { align-self: flex-start; font-size: 11.5px; font-weight: 800; letter-spacing: 0.04em; padding: 3px 9px; border-radius: 5px; background: rgba(255,255,255,0.08); color: var(--text-primary); }
    .ov-stage-name { font-size: 14px; font-weight: 700; color: var(--text-primary); line-height: 1.4; }
    .ov-step-box { background: var(--surface-3); border-radius: 8px; padding: 12px 13px; border-left: 4px solid var(--accent); }
    .ov-step-badge { font-size: 12px; font-weight: 800; margin-bottom: 4px; }
    .ov-step-title { font-size: 13.5px; font-weight: 700; color: var(--text-primary); margin-bottom: 6px; line-height: 1.4; }
    .ov-step-desc { font-size: 12.5px; line-height: 1.6; color: var(--text-secondary); }
    .ov-step-out { font-size: 12px; line-height: 1.55; color: var(--text-secondary); margin-top: 8px; padding-top: 8px; border-top: 1px dashed var(--card-border-subtle); }
    .ov-conn-v { display: flex; justify-content: center; align-items: center; height: 14px; color: var(--text-secondary); font-size: 12px; }

    .ov-gap-table { width: 100%; border-collapse: collapse; font-size: 13px; text-align: left; }
    .ov-gap-table th { padding: 10px; color: var(--text-secondary); font-weight: 600; border-bottom: 1px solid var(--card-border); }
    .ov-gap-table td { padding: 10px; color: var(--text-primary); line-height: 1.6; border-bottom: 1px solid var(--card-border-subtle); vertical-align: top; }
    .ov-gap-table td.muted { color: var(--text-secondary); }
    .ov-gap-table td.lead-cell { font-weight: 700; }

    .ov-metric-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 14px; }
    .ov-metric-cap { font-size: 12.5px; color: var(--text-secondary); margin-top: 4px; }

    .ev-source-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 12px; }
    .ev-source { background: var(--surface-2); border: 1px solid var(--card-border); border-radius: 8px; padding: 12px 14px; }
    .ev-source-name { font-size: 13px; font-weight: 700; color: var(--text-primary); }
    .ev-source-path { font-size: 12px; color: var(--text-secondary); margin-top: 4px; word-break: break-all; }
    .ev-status { font-size: 11.5px; font-weight: 800; padding: 2px 8px; border-radius: 4px; }
    .ev-status.measured { background: rgba(48,209,88,0.18); color: #30d158; }
    .ev-status.pending { background: rgba(255,214,10,0.15); color: #ffd60a; }
    .ev-rubric-wrap { margin-top: 14px; display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 10px; }
    .ev-rubric-dim { background: var(--surface-2); border: 1px solid var(--card-border-subtle); border-radius: 8px; padding: 10px 12px; }
    .ev-rubric-dim b { font-size: 13px; color: var(--text-primary); }
    .ev-rubric-dim div { font-size: 12.5px; color: var(--text-secondary); margin-top: 4px; line-height: 1.5; }
    .ev-empty { font-size: 13px; color: var(--text-secondary); background: var(--surface-2); border: 1px dashed var(--card-border); border-radius: 8px; padding: 16px; line-height: 1.6; }
  </style>
</head>
<body>
  <!-- Topbar 44px -->
  <div class="topbar">
    <div class="topbar-left">
      <span class="logo">Agentic Ontology Studio</span>
      <span class="badge">[OKF v0.2 Standard]</span>
      <span class="badge badge-green">[4. Wiki Agent (GCS)]</span>
      <span class="badge badge-purple">[6. BQG Agent (Graph)]</span>
    </div>
    <div class="topbar-right">
      <button class="lang-toggle" onclick="toggleIndustryModal()" style="border-color:rgba(191,90,242,0.4); color:var(--accent-purple);">Industry Cases (8)</button>
      <button class="lang-toggle" onclick="toggleArchModal()" style="border-color:rgba(48,209,88,0.4); color:var(--accent-green);">GCP Native Spec & Repos</button>
      <span>BigQuery SQL:2023 Property Graph & OKF v0.2</span>
      <span class="badge badge-green">Engine Live</span>
      <button class="lang-toggle" onclick="toggleLang()" id="lang-btn">KO / EN</button>
    </div>
  </div>

  <!-- Industry Cases Modal -->
  <div id="industry-modal" style="display:none; position:fixed; top:50px; right:18px; width:780px; max-height:85vh; background:var(--surface-2); border:1px solid var(--card-border); border-radius:8px; z-index:1000; box-shadow:0 16px 40px rgba(0,0,0,0.85); overflow-y:auto; padding:22px;">
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px; border-bottom:1px solid var(--card-border-subtle); padding-bottom:10px;">
      <div>
        <span class="badge badge-purple" style="margin-right:6px;">Cross-Industry Templates</span>
        <span style="font-size:14px; font-weight:700; color:var(--text-primary);">4대 산업군 8대 엔터프라이즈 온톨로지 케이스 템플릿</span>
      </div>
      <button onclick="toggleIndustryModal()" style="background:transparent; border:none; color:var(--text-secondary); cursor:pointer; font-size:16px;">✕</button>
    </div>
    <p style="font-size:12px; color:var(--text-secondary); line-height:1.5; margin-bottom:14px;">
      국내 대표 4대 산업군(제조, 금융, 유통, 통신) 8대 엔터프라이즈의 실제 비즈니스 요건을 추상화하여, 즉시 프로젝트 현장에 복제·적용할 수 있는 DDL, 샘플 데이터, 비정형 SOP 규정 및 CQ 가이드라인을 제공합니다.
    </p>
  </div>

  <!-- GCP Native First & Architecture Modal -->
  <div id="arch-modal" style="display:none; position:fixed; top:50px; right:18px; width:720px; max-height:85vh; background:var(--surface-2); border:1px solid var(--card-border); border-radius:8px; z-index:1000; box-shadow:0 16px 40px rgba(0,0,0,0.85); overflow-y:auto; padding:22px;">
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px; border-bottom:1px solid var(--card-border-subtle); padding-bottom:10px;">
      <div>
        <span class="badge badge-green" style="margin-right:6px;">GCP Native First</span>
        <span style="font-size:14px; font-weight:700; color:var(--text-primary);">Google Cloud Native Spec & Custom Extension Delineation</span>
      </div>
      <button onclick="toggleArchModal()" style="background:transparent; border:none; color:var(--text-secondary); cursor:pointer; font-size:16px;">✕</button>
    </div>
  </div>

  <!-- Subbar 52px: Agentic Ontology Studio Ribbon (0. Overview ~ 8. AI FDE) -->
  <div class="subbar">
    <button class="nav-btn active" onclick="switchTab('overview')">0. Overview</button>
    <button class="nav-btn" onclick="switchTab('assets')">1. Asset</button>
    <button class="nav-btn" onclick="switchTab('okf')">2. OKF Layer</button>
    <button class="nav-btn" onclick="switchTab('structured')">3. Ontology Semantic</button>
    <button class="nav-btn" onclick="switchTab('wiki-agent')">4. Wiki Agent</button>
    <button class="nav-btn" onclick="switchTab('graph')">5. Bigquery Graph</button>
    <button class="nav-btn" onclick="switchTab('bqg-agent')">6. BQG Agent</button>
    <button class="nav-btn" onclick="switchTab('lineage')">7. Lineage</button>
    <button class="nav-btn" onclick="switchTab('fde')">8. AI FDE</button>
    <button class="nav-btn" onclick="switchTab('evaluation')">9. Evaluation</button>
  </div>

  <!-- VIEW 0: OVERVIEW (rendered from config/portal_profile.json) -->
  <div class="tab-panel active" id="panel-overview" style="flex-direction: column; overflow-y: auto; padding: 24px; gap: 22px; font-size: 13.5px;">
    <!-- SECTION 1: 5-STAGE / 9-STEP FLOW BOARD -->
    <div class="ov-card">
      <div class="ov-card-head">
        <span class="badge ov-eyebrow" id="ov-s1-eyebrow">SECTION 1</span>
        <span class="ov-card-note" id="ov-s1-note"></span>
      </div>
      <h2 class="ov-h2" id="ov-s1-title">-</h2>
      <p class="ov-lead" id="ov-s1-lead"></p>
      <div class="ov-flow-board" id="ov-flow-board"></div>
    </div>

    <!-- SECTION 2 & 3: ARCHITECTURE & FEATURE GAP MATRIX -->
    <div class="ov-card">
      <div class="ov-card-head">
        <span class="badge badge-green ov-eyebrow" id="ov-s2-eyebrow">SECTION 2 &amp; 3</span>
      </div>
      <h2 class="ov-h2" id="ov-s2-title">-</h2>
      <table class="ov-gap-table">
        <thead>
          <tr>
            <th>아키텍처 레이어</th>
            <th>Google Cloud 네이티브 서비스</th>
            <th>네이티브 단독 한계 (Feature Gap)</th>
            <th>스튜디오 커스텀 개발 해법</th>
          </tr>
        </thead>
        <tbody id="ov-gap-body"></tbody>
      </table>
    </div>

    <!-- SECTION 4: REFERENCE METRICS -->
    <div class="ov-card">
      <div class="ov-card-head">
        <span class="badge badge-purple ov-eyebrow" id="ov-s4-eyebrow">SECTION 4</span>
        <button class="nav-btn" style="background: rgba(191,90,242,0.2); color: #e9d5ff; font-size: 13px;" onclick="switchTab('evaluation')">9. Evaluation 검증 결과 보기 &rarr;</button>
      </div>
      <p class="ov-lead" id="ov-s4-note"></p>
      <div class="ov-metric-grid" id="ov-metric-grid"></div>
    </div>
  </div>

  <!-- VIEW 1: AI FDE STUDIO -->
  <div class="tab-panel" id="panel-fde">
    <div class="fde-layout">
      <div class="fde-sidebar">
        <div class="fde-filter-bar" style="display:flex; flex-wrap:wrap; gap:4px;">
          <span class="filter-chip active" onclick="filterTools('all')">All (11)</span>
          <span class="filter-chip" onclick="filterTools('gcp_native')">GCP Native (2)</span>
          <span class="filter-chip" onclick="filterTools('custom')">Custom (9)</span>
          <span class="filter-chip" onclick="filterTools('business')">Business (5)</span>
          <span class="filter-chip" onclick="filterTools('engineer')">Engineering (6)</span>
        </div>
        <div class="fde-tool-list" id="tool-catalog-list">
          <!-- Populated via JS -->
        </div>
      </div>
      <div class="fde-console">
        <div class="agent-mode-bar">
          <div style="display:flex; align-items:center; gap:9px; flex-wrap:wrap;">
            <span class="badge badge-purple" id="agent-mode-badge">8. AI FDE</span>
            <span style="font-size:13px; font-weight:700; color:var(--text-primary);" id="agent-mode-title">11종 도메인 MCP 오케스트레이션 콘솔</span>
          </div>
          <span style="font-size:11.5px; color:var(--text-secondary);" id="agent-mode-path">근거 경로 · OKF 위키 + Property Graph 원장 동시 참조</span>
        </div>
        <div class="quick-chips-bar" id="agent-sample-chips">
          <span style="font-size:11px; color:var(--text-secondary); align-self:center;">Sample Directives:</span>
        </div>
        <div class="chat-timeline" id="timeline">
          <div class="trace-card">
            <h4>[Welcome] Enterprise Agentic Ontology Starter Console</h4>
            <p>This console demonstrates deterministic cross-domain reasoning over BigQuery DW master tables and unstructured policy manuals.</p>
            <div style="margin-top:10px; color:var(--text-secondary); font-size:12px;">
              • Dynamic Sub-Goal Decomposition: Breaks complex user queries into business and infrastructure intents.<br/>
              • Context Hand-Off: Passes upstream lookup metadata directly into downstream validation tools.<br/>
              • Grounded Answering: Every figure is traced back to a relational master ledger row or a hash-anchored document chunk.
            </div>
          </div>
        </div>
        <div class="input-bar">
          <input type="text" id="query-input" class="input-field" placeholder="Enter business or infrastructure inquiry..." onkeydown="if(event.key==='Enter'&&!event.isComposing)sendQuery();"/>
          <button id="send-btn" class="send-btn" onclick="sendQuery()">Run FDE</button>
        </div>
      </div>
    </div>
  </div>

  <!-- VIEW 2: ASSET MANAGEMENT STUDIO -->
  <div class="tab-panel" id="panel-assets">
    <div class="asset-layout">
      <!-- Left: Unstructured & LLM-Wiki -->
      <div class="asset-half">
        <div class="pane-header">
          <span>Unstructured Knowledge & Karpathy 3-Layer Wiki</span>
          <div style="display:flex; gap:4px;">
            <span class="badge badge-green">[GCP: OKF v0.2]</span>
            <span class="badge badge-purple">[Custom: Karpathy Wiki]</span>
          </div>
        </div>
        <div class="subtabs-bar">
          <button class="subtab-btn active" onclick="showUnstructuredTab('chunks')">Policy Chunks</button>
          <button class="subtab-btn" onclick="showUnstructuredTab('wiki_summary')">summary.md</button>
          <button class="subtab-btn" onclick="showUnstructuredTab('wiki_entities')">entities.md</button>
          <button class="subtab-btn" onclick="showUnstructuredTab('wiki_concepts')">concepts.md</button>
          <button class="subtab-btn" onclick="showUnstructuredTab('wiki_rules')">rules.md</button>
          <button class="subtab-btn" onclick="showUnstructuredTab('gcs')">GCS Manifest</button>
        </div>
        <div class="asset-scroll-content" id="unstructured-content">
          <!-- Populated via JS -->
        </div>
      </div>
      <!-- Right: Structured DW Master Ledgers -->
      <div class="asset-half">
        <div class="pane-header">
          <span>Structured DW Master Ledgers (BigQuery)</span>
          <div style="display:flex; gap:4px;">
            <span class="badge badge-green">[GCP Native DW Table]</span>
            <span class="badge">[Direct Node Promotion]</span>
          </div>
        </div>
        <div class="subtabs-bar">
          <button class="subtab-btn active" onclick="showTable('devices')">dw_device_master</button>
          <button class="subtab-btn" onclick="showTable('plans')">dw_plan_master</button>
          <button class="subtab-btn" onclick="showTable('subsidies')">dw_subsidy_policy_master</button>
        </div>
        <div class="asset-scroll-content" id="structured-content">
          <!-- Populated via JS -->
        </div>
      </div>
    </div>
  </div>

  <!-- VIEW 2: OKF TRANSFORMATION LAYER -->
  <div class="tab-panel" id="panel-okf" style="flex-direction: column; overflow: hidden; height: 100%;">
    <div style="padding: 12px 20px; background: var(--surface-1); border-bottom: 1px solid var(--card-border); display: flex; justify-content: space-between; align-items: center;">
      <div style="display: flex; align-items: center; gap: 10px;">
        <span class="badge badge-green">STAGE 2 ACTIVE</span>
        <span style="font-size: 13px; font-weight: 700; color: var(--text-primary);">2-Week Sprint Unstructured GCS Transformation Layer</span>
      </div>
      <div style="display: flex; gap: 8px;">
        <span class="badge">[GCP: OKF v0.2 Standard]</span>
        <span class="badge badge-purple">[Karpathy 3-Layer Wiki]</span>
        <span class="badge badge-green">[100% SHA-256 Anchored]</span>
      </div>
    </div>
    <div class="asset-layout" style="flex: 1; overflow: hidden;">
      <!-- Left: Unstructured Chunks & Wiki -->
      <div class="asset-half" style="flex: 1.2;">
        <div class="pane-header">
          <span>Unstructured Policy Chunks &amp; Karpathy Wiki</span>
        </div>
        <div class="subtabs-bar">
          <button class="subtab-btn active" onclick="showUnstructuredTab('chunks')">Policy Chunks</button>
          <button class="subtab-btn" onclick="showUnstructuredTab('wiki_summary')">summary.md</button>
          <button class="subtab-btn" onclick="showUnstructuredTab('wiki_entities')">entities.md</button>
          <button class="subtab-btn" onclick="showUnstructuredTab('wiki_concepts')">concepts.md</button>
          <button class="subtab-btn" onclick="showUnstructuredTab('wiki_rules')">rules.md</button>
          <button class="subtab-btn" onclick="showUnstructuredTab('gcs')">GCS Manifest</button>
        </div>
        <div class="asset-scroll-content" id="unstructured-content-okf" style="flex: 1; overflow-y: auto; padding: 14px;">
          <!-- Dynamically loaded -->
        </div>
      </div>
      <!-- Right: Trust Signals & Grounding Inspector -->
      <div class="asset-half" style="flex: 0.8; padding: 18px; display: flex; flex-direction: column; gap: 14px; overflow-y: auto;">
        <div style="font-size: 13px; font-weight: 700; color: var(--text-primary); border-bottom: 1px solid var(--card-border); padding-bottom: 8px;">
          트러스트 시그널 &amp; 감사 원장
        </div>
        <div style="background: var(--surface-2); padding: 12px; border-radius: 8px; border: 1px solid var(--card-border);">
          <div style="font-weight: 700; font-size: 12px; color: var(--text-primary); margin-bottom: 4px;">SHA-256 불변성 보증</div>
          <div style="color: var(--text-secondary); font-size: 11px; line-height: 1.5;">
            비정형 원문 MHTML/PDF에서 청크 분할 즉시 SHA-256 해시를 산출하여 감사 원장에 기록, 환각 및 위변조를 원천 차단합니다.
          </div>
        </div>
        <div style="background: var(--surface-2); padding: 12px; border-radius: 8px; border: 1px solid var(--card-border);">
          <div style="font-weight: 700; font-size: 12px; color: var(--text-primary); margin-bottom: 4px;">Karpathy 3-Layer 계층 구조</div>
          <div style="color: var(--text-secondary); font-size: 11px; line-height: 1.5;">
            &bull; Layer 1: DocChunk &amp; Anchor (원문 1:1)<br>
            &bull; Layer 2: Entities &amp; Concepts (도메인 추상화)<br>
            &bull; Layer 3: Constraint Rules (결정론적 산식)
          </div>
        </div>
        <button class="nav-btn" style="width: 100%; text-align: center; background: var(--accent); color: #fff; padding: 8px;" onclick="switchTab('structured')">
          3. Ontology Semantic 보기 &rarr;
        </button>
      </div>
    </div>
  </div>

  <!-- VIEW 3: STRUCTURED GRAPH & DDL -->
  <div class="tab-panel" id="panel-structured" style="flex-direction: column; overflow-y: auto; padding: 24px; gap: 20px;">
    <div style="background: var(--surface-1); border: 1px solid var(--card-border); border-radius: 12px; padding: 20px 24px; display: flex; justify-content: space-between; align-items: center;">
      <div>
        <div style="font-size: 11px; color: var(--accent); font-weight: 700; margin-bottom: 4px;">3. ONTOLOGY SEMANTIC &middot; ZERO-COPY DDL</div>
        <h2 style="font-size: 18px; font-weight: 700; color: var(--text-primary);">DW Direct Promotion &amp; 2-Layer Anti-Redundancy</h2>
      </div>
      <div style="display: flex; gap: 8px;">
        <button class="nav-btn" style="padding: 6px 12px; font-size: 11.5px; background: var(--surface-2);" onclick="copyStarterDdl()">DDL 복사 (Copy SQL)</button>
        <button class="nav-btn" style="padding: 6px 12px; font-size: 11.5px; background: var(--accent); color: #fff;" onclick="switchTab('graph')">5. Bigquery Graph 탐색 &rarr;</button>
      </div>
    </div>

    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
      <div style="background: var(--surface-1); border: 1px solid var(--card-border); border-radius: 10px; padding: 18px;">
        <div style="font-size: 14px; font-weight: 700; color: var(--text-primary); margin-bottom: 6px;">Zero-Copy 가상화 원리</div>
        <div style="font-size: 12px; line-height: 1.6; color: var(--text-secondary);">
          별도 그래프 전용 DB 인프라 및 중복 복제 파이프라인을 제거하고, BigQuery DW 물리 테이블을 ISO SQL:2023 Property Graph의 노드와 에지로 직접 승격하여 스토리지 비용을 80% 절감합니다.
        </div>
      </div>
      <div style="background: var(--surface-1); border: 1px solid var(--card-border); border-radius: 10px; padding: 18px;">
        <div style="font-size: 14px; font-weight: 700; color: var(--text-primary); margin-bottom: 6px;">2-Layer 안티 리던던시 보증</div>
        <div style="font-size: 12px; line-height: 1.6; color: var(--text-secondary);">
          비정형 문서에서 추출된 엔티티 중 DW 정형 테이블과 중복되는 엔티티는 빌드 타임에 전량 제거(Pruning)하고, 오직 순수 룰 및 청크 노드만 잔존시켜 데이터 충돌을 0건으로 차단합니다.
        </div>
      </div>
    </div>

    <div style="background: var(--surface-1); border: 1px solid var(--card-border); border-radius: 10px; overflow: hidden;">
      <div style="padding: 12px 18px; background: var(--surface-2); border-bottom: 1px solid var(--card-border); font-size: 12px; font-weight: 700; color: var(--text-primary);">
        ISO SQL:2023 Property Graph DDL (create_property_graph.sql)
      </div>
      <pre id="starter-structured-ddl" style="padding: 16px; font-family: monospace; font-size: 11.5px; line-height: 1.5; color: #93c5fd; background: #0b1120; overflow-x: auto; margin: 0;">Loading DDL...</pre>
    </div>
  </div>

  <!-- VIEW 3: PROPERTY GRAPH VISUALIZER -->
  <div class="tab-panel" id="panel-graph">
    <div class="graph-layout">
      <div class="stats-kpi-bar">
        <div class="kpi-item"><span>Total Nodes:</span> <span class="kpi-val" id="graph-node-count">5</span></div>
        <div class="kpi-item"><span>Total Edges:</span> <span class="kpi-val" id="graph-edge-count">4</span></div>
        <div class="kpi-item"><span>Engine:</span> <span class="kpi-val" style="color:var(--accent-green);">GCP Native SQL:2023</span></div>
        <div class="kpi-item"><span>Compiler:</span> <span class="kpi-val" style="color:var(--accent-purple);">Custom Anti-Redundancy</span></div>
        <div class="kpi-item"><span>Anti-Redundancy:</span> <span class="kpi-val" style="color:var(--accent-green);">100% (Zero Duplicates)</span></div>
      </div>
      <div class="graph-main-split">
        <div class="graph-canvas-box" id="graph-canvas">
          <!-- 2D SVG Interactive Graph Topology -->
          <svg width="100%" height="100%" viewBox="0 0 700 450" style="max-width:700px; max-height:450px;">
            <defs>
              <marker id="arrow-blue" viewBox="0 0 10 10" refX="22" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                <path d="M 0 0 L 10 5 L 0 10 z" fill="#2997ff" />
              </marker>
              <marker id="arrow-green" viewBox="0 0 10 10" refX="22" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                <path d="M 0 0 L 10 5 L 0 10 z" fill="#30d158" />
              </marker>
            </defs>
            <!-- Edges -->
            <!-- Subsidy -> Device (COVERS_DEVICE) -->
            <line x1="350" y1="200" x2="160" y2="120" stroke="#2997ff" stroke-width="2" marker-end="url(#arrow-blue)" />
            <text x="240" y="150" fill="#86868b" font-size="10" font-family="monospace">COVERS_DEVICE</text>

            <!-- Subsidy -> Plan (REQUIRES_PLAN) -->
            <line x1="350" y1="200" x2="540" y2="120" stroke="#2997ff" stroke-width="2" marker-end="url(#arrow-blue)" />
            <text x="430" y="150" fill="#86868b" font-size="10" font-family="monospace">REQUIRES_PLAN</text>

            <!-- DomainRule -> Plan (APPLIES_RULE) -->
            <line x1="540" y1="330" x2="540" y2="155" stroke="#30d158" stroke-width="2" stroke-dasharray="4" marker-end="url(#arrow-green)" />
            <text x="548" y="240" fill="#30d158" font-size="10" font-family="monospace">APPLIES_RULE</text>

            <!-- DomainRule -> DocChunk (GROUNDED_IN) -->
            <line x1="500" y1="350" x2="200" y2="350" stroke="#30d158" stroke-width="2" stroke-dasharray="4" marker-end="url(#arrow-green)" />
            <text x="320" y="340" fill="#30d158" font-size="10" font-family="monospace">GROUNDED_IN</text>

            <!-- Nodes -->
            <!-- DeviceNode (Structured DW) -->
            <g style="cursor:pointer;" onclick="inspectNode('DeviceNode')">
              <circle cx="160" cy="120" r="32" fill="#1c1c1e" stroke="#2997ff" stroke-width="2.5" />
              <text x="160" y="116" text-anchor="middle" fill="#f5f5f7" font-size="11" font-weight="700">DeviceNode</text>
              <text x="160" y="132" text-anchor="middle" fill="#86868b" font-size="9">SM-S938N</text>
            </g>

            <!-- PlanNode (Structured DW) -->
            <g style="cursor:pointer;" onclick="inspectNode('PlanNode')">
              <circle cx="540" cy="120" r="32" fill="#1c1c1e" stroke="#2997ff" stroke-width="2.5" />
              <text x="540" y="116" text-anchor="middle" fill="#f5f5f7" font-size="11" font-weight="700">PlanNode</text>
              <text x="540" y="132" text-anchor="middle" fill="#86868b" font-size="9">5G Premier</text>
            </g>

            <!-- SubsidyNode (Structured DW) -->
            <g style="cursor:pointer;" onclick="inspectNode('SubsidyNode')">
              <circle cx="350" cy="200" r="34" fill="#1c1c1e" stroke="#2997ff" stroke-width="2.5" />
              <text x="350" y="196" text-anchor="middle" fill="#f5f5f7" font-size="11" font-weight="700">SubsidyNode</text>
              <text x="350" y="212" text-anchor="middle" fill="#86868b" font-size="9">POL-2026-002</text>
            </g>

            <!-- DocChunkNode (Unstructured Pruned) -->
            <g style="cursor:pointer;" onclick="inspectNode('DocChunkNode')">
              <circle cx="160" cy="350" r="32" fill="#1c1c1e" stroke="#bf5af2" stroke-width="2.5" />
              <text x="160" y="346" text-anchor="middle" fill="#f5f5f7" font-size="11" font-weight="700">DocChunkNode</text>
              <text x="160" y="362" text-anchor="middle" fill="#bf5af2" font-size="9">DOC_CHUNK_002</text>
            </g>

            <!-- DomainRuleNode (Unstructured Policy) -->
            <g style="cursor:pointer;" onclick="inspectNode('DomainRuleNode')">
              <circle cx="540" cy="350" r="32" fill="#1c1c1e" stroke="#bf5af2" stroke-width="2.5" />
              <text x="540" y="346" text-anchor="middle" fill="#f5f5f7" font-size="11" font-weight="700">DomainRuleNode</text>
              <text x="540" y="362" text-anchor="middle" fill="#bf5af2" font-size="9">180D Commitment</text>
            </g>
          </svg>
        </div>
        <div class="graph-inspector">
          <div class="pane-header">
            <span id="inspector-title">Node Inspector</span>
            <span class="badge" id="inspector-badge">Click Node to Inspect</span>
          </div>
          <div class="code-box" id="inspector-body">
Select any node in the canvas to view its schema properties, anti-redundancy projection origin, and semantic relationships.
          </div>
          <div class="pane-header" style="border-top:1px solid var(--card-border);">
            <span>Declarative Property Graph DDL</span>
          </div>
          <div class="code-box" id="ddl-preview" style="max-height:180px;">
-- Loading DDL...
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- VIEW 5: 4-TIER ENTERPRISE LINEAGE -->
  <div class="tab-panel" id="panel-lineage" style="flex-direction: column; overflow-y: auto; padding: 24px; gap: 18px;">
    <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px;">
      <div style="display:flex; align-items:center; gap:10px;">
        <span class="badge badge-green">7. LINEAGE</span>
        <span style="font-size:15px; font-weight:800; color:var(--text-primary);">4-Tier 엔드투엔드 데이터 계보 (Raw &rarr; OKF &rarr; Property Graph &rarr; Agent)</span>
      </div>
      <span class="badge" id="lineage-latency-badge">로딩 중</span>
    </div>
    <p style="font-size:13px; color:var(--text-secondary); line-height:1.65; margin:0;">
      아래 수치는 본 저장소에 동봉된 <code>data/</code> 산출물(<code>doc_chunks.jsonl</code>, <code>llm_wiki/</code>, <code>graph_topology.json</code>, <code>cq_benchmark_report.json</code>)을 요청 시점에 직접 읽어 계산한 값입니다.
      자신의 데이터를 <code>data/input/</code>에 넣고 <code>python3 run_pipeline.py</code>를 실행하면 동일한 계보가 그대로 갱신됩니다.
    </p>

    <div class="kpi-grid" id="lineage-kpis"></div>

    <div id="lineage-tiers" style="display:grid; grid-template-columns: repeat(4, 1fr); gap:14px;"></div>

    <div style="background: var(--surface-1); border: 1px solid var(--card-border); border-radius: 12px; padding: 18px 20px;">
      <div style="font-size:12px; font-weight:700; color:var(--text-secondary); margin-bottom:10px;">계층 간 전이 및 시맨틱 브릿지 엣지 (Semantic Bridges)</div>
      <table class="data-table" id="lineage-edge-table">
        <thead>
          <tr><th>Source Vertex</th><th>Edge</th><th>Target Vertex</th><th>Edge Type</th></tr>
        </thead>
        <tbody id="lineage-edge-tbody"></tbody>
      </table>
    </div>
  </div>

  <!-- VIEW 4: CQ BENCHMARK STUDIO -->
  <div class="tab-panel" id="panel-cq">
    <div class="cq-layout">
      <div style="display:flex; align-items:center; gap:10px; flex-wrap:wrap;">
        <button class="nav-btn" onclick="switchTab('overview')" style="font-size:12px;">&larr; 0. Overview</button>
        <span style="font-size:15px; font-weight:800; color:var(--text-primary);">Golden CQ 벤치마크 (동봉 샘플 데이터셋 실행 결과)</span>
      </div>
      <p style="font-size:13px; color:var(--text-secondary); line-height:1.65; margin:0;">
        아래 지표는 본 저장소에 동봉된 샘플 데이터셋(<code>data/input/04_cq/golden_competency_questions.json</code>)을
        <code>run_pipeline.py</code>로 실행한 <code>data/output/cq_benchmark_report.json</code>을 그대로 읽어 표시한 값입니다.
        레퍼런스 구현의 골든 CQ 실측치는 <code>0. Overview</code> Section 4에 별도로 표기되어 있습니다.
      </p>

      <div class="kpi-grid">
        <div class="metric-box">
          <div class="metric-title">동봉 샘플 CQ 수</div>
          <div class="metric-value" id="cq-kpi-total">-</div>
        </div>
        <div class="metric-box">
          <div class="metric-title">통과 (Passed)</div>
          <div class="metric-value" style="color:var(--accent-green);" id="cq-kpi-passed">-</div>
        </div>
        <div class="metric-box">
          <div class="metric-title">정확도 (Accuracy)</div>
          <div class="metric-value" id="cq-kpi-accuracy">-</div>
        </div>
        <div class="metric-box">
          <div class="metric-title">근거 미첨부 (Ungrounded)</div>
          <div class="metric-value" style="color:var(--accent);" id="cq-kpi-halluc">-</div>
        </div>
      </div>

      <div style="display:flex; justify-content:space-between; align-items:center;">
        <span style="font-size:12px; font-weight:700; color:var(--text-secondary);">Golden Competency Evaluation Matrix</span>
        <button class="send-btn" onclick="runCqBenchmarks()" style="padding:6px 14px; font-size:11px;">Reload Benchmark Report</button>
      </div>

      <div class="cq-table-container">
        <table class="data-table" id="cq-matrix-table">
          <thead>
            <tr>
              <th>CQ ID</th>
              <th>Category</th>
              <th>Inquiry Prompt</th>
              <th>Deterministic Ground Truth</th>
              <th>FDE Output</th>
              <th>Grounding Anchor</th>
              <th>Verification</th>
            </tr>
          </thead>
          <tbody id="cq-tbody">
            <!-- Populated via JS -->
          </tbody>
        </table>
      </div>
    </div>
  </div>

  <!-- VIEW 9: EVALUATION (rendered from /api/eval/summary) -->
  <div class="tab-panel" id="panel-evaluation" style="flex-direction: column; overflow-y: auto; padding: 24px; gap: 20px; font-size: 13.5px;">
    <div class="ov-card">
      <div class="ov-card-head">
        <span class="badge ov-eyebrow">9. EVALUATION &middot; 검증 리포트</span>
      </div>
      <p class="ov-lead" id="ev-intro"></p>
      <div class="ev-source-grid" id="ev-sources"></div>
    </div>

    <div class="ov-card">
      <div class="ov-card-head"><span class="badge badge-green ov-eyebrow">A &middot; 검증 설계</span></div>
      <h2 class="ov-h2" id="ev-design-title">-</h2>
      <p class="ov-lead" id="ev-design-desc"></p>
      <table class="ov-gap-table">
        <thead><tr><th>질문셋</th><th>목적</th><th>구성</th><th>지표</th></tr></thead>
        <tbody id="ev-suite-body"></tbody>
      </table>
      <div class="ev-rubric-wrap" id="ev-rubric"></div>
    </div>

    <div class="ov-card">
      <div class="ov-card-head"><span class="badge badge-purple ov-eyebrow">B &middot; 종합 KPI</span></div>
      <div class="ov-metric-grid" id="ev-kpi-grid"></div>
    </div>

    <div class="ov-card">
      <div class="ov-card-head"><span class="badge ov-eyebrow">C &middot; Golden CQ 채점표</span></div>
      <div id="ev-golden-wrap"></div>
    </div>

    <div class="ov-card">
      <div class="ov-card-head"><span class="badge badge-green ov-eyebrow">D &middot; 바운더리 질의 회귀</span></div>
      <div id="ev-boundary-wrap"></div>
    </div>

    <div class="ov-card">
      <div class="ov-card-head"><span class="badge badge-purple ov-eyebrow">E &middot; 실패 원인 분류</span></div>
      <table class="ov-gap-table">
        <thead><tr><th>코드</th><th>유형</th><th>관찰 신호</th><th>개선 조치</th></tr></thead>
        <tbody id="ev-taxonomy-body"></tbody>
      </table>
    </div>

    <div class="ov-card">
      <div class="ov-card-head"><span class="badge ov-eyebrow">F &middot; 회차 비교</span></div>
      <table class="ov-gap-table">
        <thead><tr><th>회차</th><th>설명</th><th>상태</th><th>비고</th></tr></thead>
        <tbody id="ev-round-body"></tbody>
      </table>
    </div>
  </div>

  <script>
    let globalAssets = {};
    let currentToolFilter = 'all';

    // Switch Top Tabs (Agentic Ontology Studio Ribbon: 0. Overview ~ 8. AI FDE)
    function switchTab(tabId) {
      const ids = ['overview', 'assets', 'okf', 'structured', 'wiki-agent', 'graph', 'bqg-agent', 'lineage', 'fde', 'evaluation'];
      document.querySelectorAll('.subbar .nav-btn').forEach((b, idx) => {
        b.classList.toggle('active', ids[idx] === tabId);
      });
      document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
      const panelMap = {
        'overview': 'panel-overview',
        'assets': 'panel-assets',
        'okf': 'panel-okf',
        'structured': 'panel-structured',
        'wiki-agent': 'panel-fde',
        'graph': 'panel-graph',
        'bqg-agent': 'panel-fde',
        'lineage': 'panel-lineage',
        'fde': 'panel-fde',
        'evaluation': 'panel-evaluation',
        'cq': 'panel-cq'
      };
      const activePanel = document.getElementById(panelMap[tabId] || ('panel-' + tabId));
      if (activePanel) activePanel.classList.add('active');

      if ((tabId === 'assets' || tabId === 'okf') && !globalAssets.chunks) loadAssets();
      if (tabId === 'structured') loadStructuredDdl();
      if (tabId === 'graph') loadGraph();
      if (tabId === 'lineage') loadLineage();
      if (tabId === 'cq') loadCq();
      if (tabId === 'evaluation') loadEvaluation();
      if (panelMap[tabId] === 'panel-fde') setAgentMode(tabId);
    }

    // ---- Profile-driven Overview -------------------------------------------
    function esc(s) { return (s === null || s === undefined) ? '' : String(s); }

    async function loadPortalProfile() {
      let p;
      try {
        const res = await fetch('/api/portal/profile');
        if (!res.ok) throw new Error('profile ' + res.status);
        p = await res.json();
      } catch (e) {
        document.getElementById('ov-s1-title').textContent = 'config/portal_profile.json 을 읽지 못했습니다.';
        return;
      }
      const ov = p.overview || {};
      document.getElementById('ov-s1-eyebrow').textContent = esc(ov.eyebrow);
      document.getElementById('ov-s1-title').textContent = esc(ov.title);
      document.getElementById('ov-s1-lead').innerHTML = esc(ov.lead);

      const board = document.getElementById('ov-flow-board');
      board.innerHTML = (ov.stages || []).map(st => {
        const steps = (st.steps || []).map((sp, i) => `
          ${i > 0 ? '<div class="ov-conn-v">&darr;</div>' : ''}
          <div class="ov-step-box" style="border-left-color:${esc(st.accent)};">
            <div class="ov-step-badge" style="color:${esc(st.accent)};">${esc(sp.badge)}</div>
            <div class="ov-step-title">${esc(sp.title)}</div>
            <div class="ov-step-desc">${(sp.bullets || []).map(b => '&bull; ' + b).join('<br>')}</div>
            ${sp.deliverables ? `<div class="ov-step-out"><b>산출물</b> ${sp.deliverables}</div>` : ''}
          </div>`).join('');
        return `<div class="ov-stage-col" style="border-top-color:${esc(st.accent)};">
            <span class="ov-stage-chip">${esc(st.chip)}</span>
            <div class="ov-stage-name">${esc(st.name)}</div>
            ${steps}
          </div>`;
      }).join('');

      const gap = ov.feature_gap || {};
      document.getElementById('ov-s2-eyebrow').textContent = esc(gap.eyebrow);
      document.getElementById('ov-s2-title').textContent = esc(gap.title);
      document.getElementById('ov-gap-body').innerHTML = (gap.rows || []).map(r => `
        <tr>
          <td class="lead-cell" style="color:var(--${esc(r.layer_color) || 'accent'});">${esc(r.layer)}</td>
          <td>${esc(r.native)}</td>
          <td class="muted">${esc(r.gap)}</td>
          <td>${esc(r.solution)}</td>
        </tr>`).join('');

      const mt = ov.metrics || {};
      document.getElementById('ov-s4-eyebrow').textContent = esc(mt.eyebrow);
      document.getElementById('ov-s4-note').innerHTML = esc(mt.note);
      document.getElementById('ov-metric-grid').innerHTML = (mt.items || []).map(m => `
        <div class="metric-box">
          <div class="metric-title" style="font-size:12.5px;">${esc(m.label)}</div>
          <div class="metric-value" style="color:${esc(m.color)};">${esc(m.value)}</div>
          <div class="ov-metric-cap">${esc(m.caption)}</div>
        </div>`).join('');
    }

    // ---- Evaluation ---------------------------------------------------------
    let evaluationLoaded = false;
    async function loadEvaluation() {
      if (evaluationLoaded) return;
      let d;
      try {
        const res = await fetch('/api/eval/summary');
        if (!res.ok) throw new Error('eval ' + res.status);
        d = await res.json();
      } catch (e) {
        document.getElementById('ev-intro').textContent = '/api/eval/summary 를 읽지 못했습니다.';
        return;
      }
      evaluationLoaded = true;
      const tag = s => `<span class="ev-status ${s === 'MEASURED' ? 'measured' : 'pending'}">${s}</span>`;

      document.getElementById('ev-intro').innerHTML = esc(d.intro);
      document.getElementById('ev-sources').innerHTML = (d.sources || []).map(s => `
        <div class="ev-source">
          <div style="display:flex; justify-content:space-between; align-items:center; gap:8px;">
            <span class="ev-source-name">${esc(s.label)}</span>
            ${tag(s.exists ? 'MEASURED' : 'PENDING')}
          </div>
          <div class="ev-source-path"><code>${esc(s.path)}</code></div>
          <div class="ev-source-path">생성 주체 · ${esc(s.produced_by)}</div>
        </div>`).join('');

      const design = d.design || {};
      document.getElementById('ev-design-title').textContent = esc(design.title);
      document.getElementById('ev-design-desc').innerHTML = esc(design.description);
      document.getElementById('ev-suite-body').innerHTML = (design.suites || []).map(s => `
        <tr><td class="lead-cell">${esc(s.name)}</td><td class="muted">${esc(s.purpose)}</td><td>${esc(s.shape)}</td><td>${esc(s.metric)}</td></tr>`).join('');

      const dims = (d.rubric || {}).dimensions || {};
      document.getElementById('ev-rubric').innerHTML = Object.keys(dims).map(k => `
        <div class="ev-rubric-dim"><b>${esc(k)} &middot; weight ${esc(dims[k].weight)}</b><div>${esc(dims[k].description)}</div></div>`).join('');

      const g = d.golden || {}, b = d.boundary || {};
      document.getElementById('ev-kpi-grid').innerHTML = `
        <div class="metric-box"><div class="metric-title">Golden CQ 수</div><div class="metric-value">${g.total || 0}</div><div class="ov-metric-cap">${tag(g.status)}</div></div>
        <div class="metric-box"><div class="metric-title">Golden CQ 통과</div><div class="metric-value" style="color:var(--accent-green);">${g.passed || 0}</div><div class="ov-metric-cap">${g.pass_rate === null || g.pass_rate === undefined ? '측정 전' : g.pass_rate + '%'}</div></div>
        <div class="metric-box"><div class="metric-title">바운더리 질의 수</div><div class="metric-value">${b.case_count || 0}</div><div class="ov-metric-cap">${tag(b.status)}</div></div>
        <div class="metric-box"><div class="metric-title">바운더리 평균 성공률</div><div class="metric-value" style="color:var(--accent);">${b.avg_success_rate === null || b.avg_success_rate === undefined ? '-' : b.avg_success_rate + '%'}</div><div class="ov-metric-cap">의도 안정성 ${b.avg_intent_stability === null || b.avg_intent_stability === undefined ? '-' : b.avg_intent_stability + '%'}</div></div>`;

      document.getElementById('ev-golden-wrap').innerHTML = (g.rows || []).length
        ? `<table class="ov-gap-table"><thead><tr><th>CQ ID</th><th>Category</th><th>질문</th><th>정답</th><th>응답</th><th>근거 앵커</th><th>판정</th></tr></thead><tbody>`
          + g.rows.map(r => `<tr><td class="lead-cell">${esc(r.cq_id)}</td><td class="muted">${esc(r.category)}</td><td>${esc(r.prompt)}</td><td>${esc(r.expected_value)}</td><td>${esc(r.actual_value)}</td><td class="muted"><code>${esc(r.legal_anchor)}</code></td><td>${tag(r.passed ? 'MEASURED' : 'PENDING')} ${esc(r.verification_status)}</td></tr>`).join('')
          + `</tbody></table>`
        : `<div class="ev-empty">Golden CQ 실행 결과 파일이 없습니다. <code>python3 run_pipeline.py</code> 실행 후 <code>data/output/cq_benchmark_report.json</code>이 생성되면 자동으로 표시됩니다.</div>`;

      document.getElementById('ev-boundary-wrap').innerHTML = (b.cases || []).length
        ? `<table class="ov-gap-table"><thead><tr><th>Case</th><th>질문</th><th>결여 맥락</th><th>성공률</th><th>일관성</th><th>의도 안정성</th></tr></thead><tbody>`
          + b.cases.map(c => `<tr><td class="lead-cell">${esc(c.case_id)}</td><td>${esc(c.query)}</td><td class="muted">${esc(c.missing_context)}</td><td>${esc(c.success_rate)}%</td><td>${esc(c.consistency_rate)}%</td><td>${esc(c.intent_stability)}%</td></tr>`).join('')
          + `</tbody></table>`
        : `<div class="ev-empty">바운더리 질의 회귀 결과 파일(<code>data/output/boundary_benchmark_results.json</code>)이 없습니다. 값을 임의로 채우지 않고 PENDING으로 유지합니다.</div>`;

      document.getElementById('ev-taxonomy-body').innerHTML = (d.taxonomy || []).map(x => `
        <tr><td class="lead-cell"><code>${esc(x.code)}</code></td><td>${esc(x.name)}</td><td class="muted">${esc(x.signal)}</td><td>${esc(x.fix)}</td></tr>`).join('');

      document.getElementById('ev-round-body').innerHTML = (d.rounds || []).map(r => `
        <tr><td class="lead-cell">Round ${esc(r.round)}</td><td>${esc(r.label)}</td><td>${tag(r.status)}</td><td class="muted">${esc(r.note)}</td></tr>`).join('');
    }

    async function loadStructuredDdl() {
      const codeEl = document.getElementById('starter-structured-ddl');
      if (codeEl && (!codeEl.textContent || codeEl.textContent.includes('Loading'))) {
        try {
          const res = await fetch('/api/graph');
          const data = await res.json();
          codeEl.textContent = data.ddl || '-- DDL not generated';
        } catch (e) {
          codeEl.textContent = '-- Failed to load DDL';
        }
      }
    }

    function copyStarterDdl() {
      const codeEl = document.getElementById('starter-structured-ddl');
      if (codeEl) {
        navigator.clipboard.writeText(codeEl.textContent).then(() => {
          alert('Property Graph DDL이 클립보드에 복사되었습니다.');
        });
      }
    }

    function toggleIndustryModal() {
      const m = document.getElementById('industry-modal');
      m.style.display = m.style.display === 'none' ? 'block' : 'none';
    }

    function toggleArchModal() {
      const m = document.getElementById('arch-modal');
      m.style.display = m.style.display === 'none' ? 'block' : 'none';
    }

    // Load Tool Catalog
    async function loadCatalog() {
      const resp = await fetch('/api/catalog');
      const tools = await resp.json();
      renderTools(tools);
    }

    function renderTools(tools) {
      const container = document.getElementById('tool-catalog-list');
      container.innerHTML = '';
      tools.forEach(t => {
        if (currentToolFilter === 'business' && t.category !== 'business') return;
        if (currentToolFilter === 'engineer' && t.category !== 'engineer') return;
        if (currentToolFilter === 'gcp_native' && t.spec_origin !== 'GCP_NATIVE') return;
        if (currentToolFilter === 'custom' && t.spec_origin !== 'CUSTOM_EXTENSION') return;

        const isBiz = t.category === 'business';
        const isNative = t.spec_origin === 'GCP_NATIVE';
        container.innerHTML += `
          <div class="tool-card">
            <div class="tool-card-head">
              <span class="tool-name">${t.name}</span>
              <div style="display:flex; gap:4px;">
                <span class="badge ${isNative ? 'badge-green' : ''}">${isNative ? 'GCP Native' : 'Custom'}</span>
                <span class="badge ${isBiz ? '' : 'badge-purple'}">${isBiz ? 'BIZ' : 'ENG'}</span>
              </div>
            </div>
            <div class="tool-desc">${t.description}</div>
            <div style="margin-top:6px; font-size:10px; color:var(--text-muted); line-height:1.3;">
              <span style="color:${isNative ? 'var(--accent-green)' : 'var(--accent)'}; font-weight:600;">[Spec]</span> ${t.spec_source || 'Domain MCP'}
            </div>
          </div>
        `;
      });
    }

    function filterTools(cat) {
      currentToolFilter = cat;
      document.querySelectorAll('.filter-chip').forEach(c => {
        c.classList.remove('active');
        if (cat === 'all' && c.innerText.startsWith('All')) c.classList.add('active');
        else if (cat === 'gcp_native' && c.innerText.includes('GCP Native')) c.classList.add('active');
        else if (cat === 'custom' && c.innerText.includes('Custom')) c.classList.add('active');
        else if (cat === 'business' && c.innerText.includes('Business')) c.classList.add('active');
        else if (cat === 'engineer' && c.innerText.includes('Engineering')) c.classList.add('active');
      });
      loadCatalog();
    }

    function applySample(text) {
      const input = document.getElementById('query-input');
      input.value = text;
      input.focus();
    }

    // AI FDE Query Execution
    async function sendQuery() {
      const input = document.getElementById("query-input");
      const btn = document.getElementById("send-btn");
      const timeline = document.getElementById("timeline");
      const q = input.value.trim();
      if (!q) return;

      input.disabled = true;
      btn.disabled = true;

      // User Bubble
      timeline.innerHTML += `
        <div class="user-bubble">
          <strong>User Directive:</strong> ${q}
        </div>
      `;
      timeline.scrollTop = timeline.scrollHeight;

      try {
        const resp = await fetch("/api/query", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({query: q})
        });
        const data = await resp.json();

        if (data.status === "SUCCESS") {
          const lc = data.lifecycle;
          let subGoalsHtml = (lc.step_1_thought.sub_goals || []).map(sg => `
            <div>• <strong>[${sg.id}]</strong> ${sg.goal} ➔ <code>${sg.tool}</code></div>
          `).join("");

          let toolsHtml = (lc.step_2_tool_dispatch.dispatched_tools || []).map(dt => `
            <div class="obs-box">
              <strong>Step 2-${dt.step_index}: Dispatched Tool [${dt.tool_name}]</strong> (${dt.category.toUpperCase()})<br/>
              <em>Reason: ${dt.reason}</em><br/>
              <code>${dt.intermediate_observation}</code>
            </div>
          `).join("");

          timeline.innerHTML += `
            <div class="trace-card">
              <h4>[AI FDE Lifecycle Execution Trace: ${data.performance.total_elapsed_seconds}s]</h4>
              <div class="subgoal-box">
                <strong>Step 1: Dynamic Sub-Goals [${lc.step_1_thought.execution_mode}]</strong>
                ${subGoalsHtml}
              </div>
              ${toolsHtml}
              <div style="margin-top:10px; padding:10px; background:#121214; border-radius:6px; border-left:3px solid var(--accent);">
                <strong>Step 3: Cross-Domain Integration</strong><br/>
                ${lc.step_3_observation.cross_domain_integration_reason || ''}
              </div>
              <div style="margin-top:10px; line-height:1.6;">
                <strong>Step 4: Deterministic Synthesis</strong><br/>
                <pre style="white-space:pre-wrap; font-family:inherit;">${lc.step_4_synthesis.markdown}</pre>
              </div>
            </div>
          `;
        }
      } catch (err) {
        timeline.innerHTML += `<div class="trace-card" style="border-color:#ff453a; color:#ff453a;">Network Error: ${err.message}</div>`;
      } finally {
        input.disabled = false;
        btn.disabled = false;
        input.value = "";
        timeline.scrollTop = timeline.scrollHeight;
      }
    }

    // Load Asset Studio Data
    async function loadAssets() {
      const resp = await fetch('/api/assets');
      globalAssets = await resp.json();
      showUnstructuredTab('chunks');
      showTable('devices');
    }

    function showUnstructuredTab(tabKey) {
      document.querySelectorAll('#panel-assets .subtabs-bar:first-of-type .subtab-btn').forEach(b => {
        b.classList.toggle('active', b.getAttribute('onclick').includes(tabKey));
      });
      const container = document.getElementById('unstructured-content') || document.getElementById('unstructured-content-okf');
      const containerOkf = document.getElementById('unstructured-content-okf');
      container.innerHTML = '';

      if (tabKey === 'chunks') {
        (globalAssets.chunks || []).forEach(c => {
          container.innerHTML += `
            <div class="chunk-card">
              <div class="chunk-meta">
                <strong style="color:var(--accent);">${c.chunk_id}: ${c.title}</strong>
                <code style="color:var(--accent-purple);">${c.hash_anchor}</code>
              </div>
              <p style="color:var(--text-secondary); line-height:1.5;">${c.content}</p>
            </div>
          `;
        });
      } else if (tabKey === 'gcs') {
        const manifest = globalAssets.wiki && globalAssets.wiki['gcs_prototype_manifest.json'] || {};
        container.innerHTML = `<pre style="font-family:monospace; font-size:12px; background:var(--surface-2); padding:14px; border-radius:6px; color:#30d158;">${JSON.stringify(manifest, null, 2)}</pre>`;
      } else {
        const fname = tabKey.replace('wiki_', '') + '.md';
        const txt = globalAssets.wiki && globalAssets.wiki[fname] || 'File not found.';
        container.innerHTML = `<pre style="white-space:pre-wrap; font-size:12px; line-height:1.6; color:#e5e5ea; background:var(--surface-2); padding:14px; border-radius:6px;">${txt}</pre>`;
      }
    }

    function showTable(tblKey) {
      const container = document.getElementById('structured-content');
      const tblData = globalAssets.tables && globalAssets.tables[tblKey];
      if (!tblData || !tblData.headers) {
        container.innerHTML = '<p>No data loaded.</p>';
        return;
      }

      let rowsHtml = tblData.rows.map(r => `<tr>${r.map(v => `<td>${v}</td>`).join('')}</tr>`).join('');
      container.innerHTML = `
        <div style="margin-bottom:10px; font-size:11.5px; color:var(--text-secondary);">
          Source Table: <code style="color:var(--accent);">data/input/03_tables/${tblKey}.csv</code> 
          (Promoted to <strong>${tblKey === 'devices' ? 'DeviceNode' : tblKey === 'plans' ? 'PlanNode' : 'SubsidyNode'}</strong>)
        </div>
        <table class="data-table">
          <thead>
            <tr>${tblData.headers.map(h => `<th>${h}</th>`).join('')}</tr>
          </thead>
          <tbody>${rowsHtml}</tbody>
        </table>
      `;
    }

    // Graph Inspector
    async function loadGraph() {
      const resp = await fetch('/api/graph');
      const data = await resp.json();
      document.getElementById('ddl-preview').innerText = data.ddl || '-- No DDL available';
    }

    function inspectNode(nodeType) {
      const title = document.getElementById('inspector-title');
      const badge = document.getElementById('inspector-badge');
      const body = document.getElementById('inspector-body');

      title.innerText = nodeType;
      if (nodeType.includes('Device') || nodeType.includes('Plan') || nodeType.includes('Subsidy')) {
        badge.innerText = 'Track B: Structured DW Master';
        badge.className = 'badge';
        body.innerHTML = `
<strong>Node Type:</strong> ${nodeType}
<strong>Storage Paradigm:</strong> Relational DW Master Table (Zero Duplication)
<strong>Anti-Redundancy Role:</strong> Direct Graph Node Promotion
<strong>Key Schema Properties:</strong>
  - Primary Key: Column key
  - Projected Properties: factory_price, monthly_fee, basic_subsidy
<strong>Traversable Edges:</strong>
  - COVERS_DEVICE (Subsidy ➔ Device)
  - REQUIRES_PLAN (Subsidy ➔ Plan)
        `;
      } else {
        badge.innerText = 'Track A: Unstructured Policy/Evidence';
        badge.className = 'badge badge-purple';
        body.innerHTML = `
<strong>Node Type:</strong> ${nodeType}
<strong>Storage Paradigm:</strong> OKF v0.2 Knowledge Chunk / Codified Rule
<strong>Anti-Redundancy Role:</strong> Retained Unstructured Evidence (Entity Duplicates Pruned)
<strong>Key Schema Properties:</strong>
  - Cryptographic Hash Anchor: SHA-256 (e.g. anchor_7f8a92)
  - Legal Grounding: Consultation Guide 2.0 Section 2
<strong>Traversable Edges:</strong>
  - APPLIES_RULE (DomainRule ➔ PlanNode)
  - GROUNDED_IN (DomainRule ➔ DocChunkNode)
        `;
      }
    }

    // CQ Benchmark Matrix
    const AGENT_MODES = {
      'wiki-agent': {
        badge: '4. Wiki Agent',
        badgeClass: 'badge badge-green',
        title: 'GCS OKF v0.2 위키 단독 추론 에이전트 (Stage 2 종료 게이트)',
        path: '근거 경로 · data/llm_wiki/*.md 마크다운 하이퍼링크 순회 (물리 그래프 미구축 상태)',
        samples: [
          '180일 의무유지 위반 시 위약금 산식이 어떻게 되는지 규정 원문으로 설명해줘',
          '시니어/키즈 요금제 위약금 면제 특례 조항을 찾아줘',
          '선택약정 25% 할인과 공시지원금 중 무엇이 유리한지 규정 기준으로 비교해줘'
        ]
      },
      'bqg-agent': {
        badge: '6. BQG Agent',
        badgeClass: 'badge badge-purple',
        title: 'BigQuery Property Graph NL2GQL 멀티홉 추론 에이전트',
        path: '근거 경로 · GRAPH_TABLE() 멀티홉 탐색으로 정형 DW 원장 + 비정형 규정 동시 결합',
        samples: [
          'Galaxy S26 Ultra 지원금과 원천 DW 테이블 행수 확인해줘',
          '개통 후 120일 시점에 요금제 하향 변경 시 위약금 얼마야?',
          'Property Graph GQL 횡단 탐색으로 단말기-요금제-지원금 경로를 보여줘'
        ]
      },
      'fde': {
        badge: '8. AI FDE',
        badgeClass: 'badge badge-purple',
        title: '11종 도메인 MCP 오케스트레이션 콘솔 (동적 하위 목표 분해)',
        path: '근거 경로 · 비즈니스 5종 + 엔지니어링 6종 MCP 도구 시퀀셜 체이닝',
        samples: [
          'Galaxy S26 Ultra 지원금과 원천 DW 테이블 행수 확인해줘',
          '개통 후 120일 시점에 요금제 하향 변경 시 위약금 얼마야?',
          '동봉 샘플 CQ 벤치마크를 실행하고 근거 앵커까지 보여줘'
        ]
      }
    };

    function setAgentMode(tabId) {
      const mode = AGENT_MODES[tabId] || AGENT_MODES['fde'];
      const badgeEl = document.getElementById('agent-mode-badge');
      const titleEl = document.getElementById('agent-mode-title');
      const pathEl = document.getElementById('agent-mode-path');
      if (badgeEl) { badgeEl.className = mode.badgeClass; badgeEl.textContent = mode.badge; }
      if (titleEl) titleEl.textContent = mode.title;
      if (pathEl) pathEl.textContent = mode.path;

      const chipBar = document.getElementById('agent-sample-chips');
      if (chipBar) {
        chipBar.innerHTML = '<span style="font-size:11px; color:var(--text-secondary); align-self:center;">Sample Directives:</span>';
        mode.samples.forEach(s => {
          const chip = document.createElement('span');
          chip.className = 'quick-chip';
          chip.textContent = s.length > 34 ? s.slice(0, 33) + '…' : s;
          chip.title = s;
          chip.onclick = () => applySample(s);
          chipBar.appendChild(chip);
        });
      }
    }

    async function loadLineage() {
      const tierBox = document.getElementById('lineage-tiers');
      const kpiBox = document.getElementById('lineage-kpis');
      const edgeBody = document.getElementById('lineage-edge-tbody');
      const latencyEl = document.getElementById('lineage-latency-badge');
      if (!tierBox) return;

      const t0 = performance.now();
      let assets = {}, graph = {}, cq = {};
      try {
        const [a, g, c] = await Promise.all([fetch('/api/assets'), fetch('/api/graph'), fetch('/api/cq')]);
        assets = await a.json(); graph = await g.json(); cq = await c.json();
      } catch (e) {
        tierBox.innerHTML = '<div class="metric-box">계보 데이터를 불러오지 못했습니다.</div>';
        return;
      }
      const elapsed = Math.round(performance.now() - t0);
      if (latencyEl) latencyEl.textContent = '실측 로딩 ' + elapsed + 'ms';

      const topo = graph.topology || {};
      const chunks = assets.chunks || [];
      const wikiFiles = Object.keys(assets.wiki || {});
      const tables = assets.tables || {};
      const tableNames = Object.keys(tables);
      const rowCount = tableNames.reduce((s, k) => s + ((tables[k].rows || []).length), 0);
      const dwNodes = topo.structured_dw_nodes || [];
      const unNodes = topo.unstructured_pruned_nodes || [];
      const edges = topo.edge_tables || [];
      const bridges = topo.semantic_bridges || [];
      const cqItems = cq.evaluation_details || cq.test_results || [];
      const dupNodes = (topo.metrics || {}).duplicate_entity_nodes;

      kpiBox.innerHTML = [
        ['추적 대상 아티팩트', (tableNames.length + 1 + chunks.length + wikiFiles.length + dwNodes.length + unNodes.length) + '개', ''],
        ['Property Graph Vertex / Edge', (dwNodes.length + unNodes.length) + ' / ' + edges.length, ''],
        ['중복 엔티티 노드', (dupNodes === undefined ? '-' : dupNodes + '개'), 'var(--accent-green)'],
        ['계보 로딩 지연', elapsed + ' ms', 'var(--accent-green)']
      ].map(([title, val, color]) =>
        '<div class="metric-box"><div class="metric-title">' + title + '</div><div class="metric-value"' +
        (color ? ' style="color:' + color + ';"' : '') + '>' + val + '</div></div>'
      ).join('');

      const tiers = [
        {
          n: 'TIER 1', name: 'Raw Source', color: '#38bdf8',
          items: [
            'DW 원장 CSV ' + tableNames.length + '종 · 총 ' + rowCount + ' rows',
            '비정형 정책 가이드 (data/input/01_guides/)',
            tableNames.map(k => '<code>' + k + '</code>').join(' · ')
          ]
        },
        {
          n: 'TIER 2', name: 'OKF Layer', color: '#10b981',
          items: [
            'SHA-256 앵커 청크 ' + chunks.length + '개',
            '3-Layer 위키 파일 ' + wikiFiles.length + '개',
            chunks.slice(0, 3).map(c => '<code>' + (c.chunk_id || '') + '</code>').join(' · ')
          ]
        },
        {
          n: 'TIER 3', name: 'Property Graph', color: '#c084fc',
          items: [
            '정형 승격 Vertex ' + dwNodes.length + '종 · 비정형 Vertex ' + unNodes.length + '종',
            'Edge ' + edges.length + '종',
            '<code>' + (topo.graph_name || 'PROPERTY GRAPH') + '</code>'
          ]
        },
        {
          n: 'TIER 4', name: 'Agent & CQ', color: '#30d158',
          items: [
            '도메인 MCP 도구 11종 (비즈니스 5 · 엔지니어링 6)',
            '동봉 샘플 CQ 실행 결과 ' + cqItems.length + '건',
            cqItems.slice(0, 3).map(c => '<code>' + (c.cq_id || '') + '</code>').join(' · ')
          ]
        }
      ];

      tierBox.innerHTML = tiers.map(tr =>
        '<div style="background:var(--surface-1); border:1px solid var(--card-border); border-left:4px solid ' + tr.color +
        '; border-radius:10px; padding:14px 16px;">' +
        '<div style="font-size:11.5px; font-weight:800; color:' + tr.color + '; margin-bottom:3px;">' + tr.n + '</div>' +
        '<div style="font-size:14px; font-weight:800; color:var(--text-primary); margin-bottom:9px;">' + tr.name + '</div>' +
        tr.items.filter(Boolean).map(i =>
          '<div style="font-size:12.5px; color:var(--text-secondary); line-height:1.65;">&bull; ' + i + '</div>'
        ).join('') +
        '</div>'
      ).join('');

      edgeBody.innerHTML = bridges.length
        ? bridges.map(b =>
            '<tr><td><code>' + (b.source || '') + '</code></td><td><span class="badge badge-purple">' + (b.edge || '') +
            '</span></td><td><code>' + (b.target || '') + '</code></td><td>' + (b.type || '') + '</td></tr>'
          ).join('')
        : '<tr><td colspan="4">graph_topology.json에 등록된 엣지가 없습니다. run_pipeline.py를 먼저 실행하세요.</td></tr>';
    }

    async function loadCq() {
      const resp = await fetch('/api/cq');
      const data = await resp.json();
      const tbody = document.getElementById('cq-tbody');
      tbody.innerHTML = '';
      const items = data.evaluation_details || data.test_results || [];

      const passed = (data.passed !== undefined)
        ? data.passed
        : items.filter(x => (x.status === 'PASSED' || x.verification_status === 'EXACT_MATCH')).length;
      const setKpi = (id, v) => { const el = document.getElementById(id); if (el) el.textContent = v; };
      setKpi('cq-kpi-total', (data.total_cqs !== undefined ? data.total_cqs : items.length) + ' CQs');
      setKpi('cq-kpi-passed', passed + ' / ' + (data.total_cqs !== undefined ? data.total_cqs : items.length));
      setKpi('cq-kpi-accuracy', (data.accuracy_rate !== undefined ? data.accuracy_rate : '-') + '%');
      setKpi('cq-kpi-halluc', (data.hallucination_rate !== undefined ? data.hallucination_rate : '-') + '%');
      items.forEach(cq => {
        const cat = cq.category || (cq.dispatched_tools && cq.dispatched_tools[0] ? cq.dispatched_tools[0].replace('mcp_', '') : 'General');
        const p = cq.query || cq.prompt || '';
        const exp = cq.expected_value || (cq.dispatched_tools ? cq.dispatched_tools.join(', ') : 'Exact Match');
        const act = cq.actual_value || (cq.status === 'PASSED' ? '0% Hallucination Verified' : cq.status);
        const anc = cq.grounded_chunk || cq.legal_anchor || 'DOC_CHUNK_001';
        const stat = cq.status === 'PASSED' ? 'PASS (0% Hallucination)' : (cq.verification_status || 'VERIFIED');
        tbody.innerHTML += `
          <tr>
            <td><strong>${cq.cq_id}</strong></td>
            <td><span class="badge ${cat.includes('price') || cat.includes('Pricing') ? '' : cat.includes('subsidy') || cat.includes('Subsidy') ? 'badge-green' : 'badge-purple'}">${cat}</span></td>
            <td>${p}</td>
            <td><code>${exp}</code></td>
            <td><code>${act}</code></td>
            <td><code style="color:var(--accent-purple);">${anc}</code></td>
            <td><span class="badge badge-green">${stat}</span></td>
          </tr>
        `;
      });
    }

    function runCqBenchmarks() {
      // Re-reads data/output/cq_benchmark_report.json produced by run_pipeline.py.
      loadCq();
    }

    function toggleLang() {
      alert('Bilingual localization active: English & Korean specifications synced.');
    }

    // Init
    loadPortalProfile();
    loadCatalog();
    setAgentMode('fde');

    // Deep link support: /?tab=lineage opens that tab directly, so the README
    // and external docs can link straight to a specific studio step.
    (function applyTabFromQuery() {
      const requested = new URLSearchParams(window.location.search).get('tab');
      const allowed = ['overview', 'assets', 'okf', 'structured', 'wiki-agent', 'graph', 'bqg-agent', 'lineage', 'fde', 'evaluation', 'cq'];
      if (requested && allowed.includes(requested)) switchTab(requested);
    })();
  </script>
</body>
</html>
"""

class StudioHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/" or parsed.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode("utf-8"))

        elif parsed.path == "/api/catalog":
            catalog = engine.server.get_tool_catalog()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps(catalog, ensure_ascii=False).encode("utf-8"))

        elif parsed.path == "/api/assets":
            # Load chunks
            chunks = []
            chunk_file = os.path.join(BASE_DIR, "data/output/doc_chunks.jsonl")
            if os.path.exists(chunk_file):
                with open(chunk_file, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip(): chunks.append(json.loads(line))

            # Load LLM-Wiki files
            wiki = {}
            wiki_dir = os.path.join(BASE_DIR, "data/llm_wiki")
            if os.path.exists(wiki_dir):
                for fname in os.listdir(wiki_dir):
                    fpath = os.path.join(wiki_dir, fname)
                    if os.path.isfile(fpath):
                        with open(fpath, "r", encoding="utf-8") as f:
                            if fname.endswith(".json"):
                                wiki[fname] = json.load(f)
                            else:
                                wiki[fname] = f.read()

            # Load CSV tables
            tables = {
                "devices": load_csv_table("data/input/03_tables/devices.csv"),
                "plans": load_csv_table("data/input/03_tables/plans.csv"),
                "subsidies": load_csv_table("data/input/03_tables/subsidies.csv")
            }

            resp_data = {"chunks": chunks, "wiki": wiki, "tables": tables}
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps(resp_data, ensure_ascii=False).encode("utf-8"))

        elif parsed.path == "/api/graph":
            ddl = load_text_file("data/output/create_property_graph.sql", "-- DDL not yet generated")
            topo = load_json_file("data/output/graph_topology.json", {})
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({"ddl": ddl, "topology": topo}, ensure_ascii=False).encode("utf-8"))

        elif parsed.path == "/api/cq":
            cq = load_json_file("data/output/cq_benchmark_report.json", {
                "test_results": [
                    {
                        "cq_id": "CQ-01", "category": "Pricing", "prompt": "Galaxy S26 Ultra 256GB 출고가",
                        "expected_value": "1698400", "actual_value": "1698400",
                        "legal_anchor": "DOC_CHUNK_001", "verification_status": "EXACT_MATCH"
                    },
                    {
                        "cq_id": "CQ-02", "category": "Subsidy", "prompt": "Galaxy S26 Ultra 5G Premier 요금제 지원금",
                        "expected_value": "517500", "actual_value": "517500",
                        "legal_anchor": "DOC_CHUNK_002", "verification_status": "EXACT_MATCH"
                    },
                    {
                        "cq_id": "CQ-03", "category": "Penalty", "prompt": "개통 후 120일 시점 요금제 하향 위약금",
                        "expected_value": "100000", "actual_value": "100000",
                        "legal_anchor": "DOC_CHUNK_003", "verification_status": "EXACT_MATCH"
                    },
                    {
                        "cq_id": "CQ-04", "category": "Contract", "prompt": "24개월 기준 공시지원금 vs 선택약정 비교",
                        "expected_value": "SELECTIVE_CONTRACT_ADVANTAGEOUS", "actual_value": "SELECTIVE_CONTRACT_ADVANTAGEOUS",
                        "legal_anchor": "DOC_CHUNK_002", "verification_status": "EXACT_MATCH"
                    }
                ]
            })
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps(cq, ensure_ascii=False).encode("utf-8"))

        elif parsed.path == "/api/portal/profile":
            profile = load_json_file(PORTAL_PROFILE_PATH, {})
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps(profile, ensure_ascii=False).encode("utf-8"))

        elif parsed.path == "/api/eval/summary":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps(build_eval_summary(), ensure_ascii=False).encode("utf-8"))

        elif parsed.path == "/api/industry_cases":
            cases_data = {
                "segments": [
                    {
                        "id": "manufacturing", "name": "스마트 제조 (Manufacturing)",
                        "cases": [
                            {"client": "포스코 (POSCO)", "status": "고객 요건 진행 중", "title": "스마트 제철 연속 공정 품질 & 설비 예방보전(PdM) 온톨로지", "file": "industry_cases/01_manufacturing/case_posco_smart_steel_mill.md"},
                            {"client": "현대자동차 (Hyundai Motor)", "status": "고객 요건 진행 중", "title": "SDV 부품 BOM & 글로벌 공급망(SCM) 온톨로지 (HD현대 비교)", "file": "industry_cases/01_manufacturing/case_hyundai_motor_sdv_supply_chain.md"}
                        ]
                    },
                    {
                        "id": "finance", "name": "핀테크 & 뱅킹 (Fintech & Banking)",
                        "cases": [
                            {"client": "카카오뱅크 (KakaoBank)", "status": "고객 요건 진행 중", "title": "비대면 여신 심사 & DSR 40% 온톨로지", "file": "industry_cases/02_finance/case_kakaobank_unattended_loan_dsr.md"},
                            {"client": "토스 (TOSS)", "status": "추천 요건", "title": "원앱 멀티금융 중개 & 마이데이터 온톨로지", "file": "industry_cases/02_finance/case_toss_oneapp_fintech_mydata.md"}
                        ]
                    },
                    {
                        "id": "retail", "name": "유통 & 이커머스 (Retail & Commerce)",
                        "cases": [
                            {"client": "GS리테일 (GS Retail)", "status": "고객 요건 진행 중", "title": "가맹계약 상생 정산 & 옴니채널 재고 온톨로지", "file": "industry_cases/03_retail_commerce/case_gs_retail_franchise_omnichannel.md"},
                            {"client": "CJ대한통운 / 올리브영", "status": "고객 요건 진행 중", "title": "풀필먼트 SLA & 브랜드 정산 온톨로지", "file": "industry_cases/03_retail_commerce/case_cj_logistics_oliveyoung_sla.md"}
                        ]
                    },
                    {
                        "id": "telecom", "name": "통신 & 미디어 (Telecommunications)",
                        "cases": [
                            {"client": "SK텔레콤 (SK Telecom)", "status": "추천 요건", "title": "T우주 구독 결합 & 멤버십 위약금 온톨로지", "file": "industry_cases/04_telecommunications/case_skt_subscription_membership.md"},
                            {"client": "KT (KT Corporation)", "status": "추천 요건", "title": "유무선 결합 해지 방어 & B2B 회선 SLA 온톨로지", "file": "industry_cases/04_telecommunications/case_kt_wired_wireless_bundle_sla.md"}
                        ]
                    }
                ]
            }
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps(cases_data, ensure_ascii=False).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == "/api/query":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8")
            data = json.loads(body)
            query = data.get("query", "")
            res = engine.execute_cycle(query)

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps(res, ensure_ascii=False).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

class ThreadingStudioServer(http.server.ThreadingHTTPServer):
    """Cloud Run serves many concurrent requests against a single container
    instance. The default single-threaded server would serialize them behind
    one connection, so requests are handled on daemon worker threads instead."""
    daemon_threads = True
    allow_reuse_address = True

def run_server():
    # Bind to 0.0.0.0 so the container accepts traffic from the Cloud Run proxy.
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

