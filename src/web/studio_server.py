# Copyright (c) 2026 Sean Jung (seanjung@google.com). All Rights Reserved.
# Non-Commercial Use Only: Methodology & Docs under CC BY-NC-ND 4.0; Source Code under PolyForm Noncommercial License 1.0.0.
# Commercial use, paid consulting/SI/PoC delivery, or production deployment requires prior written permission from seanjung@google.com.

# -*- coding: utf-8 -*-
"""
Agentic Ontology Studio Server (Starter Pack v3.0 · Minimal v1-MCP Flow & Selective Composer)
- Light-First Enterprise Design System (`DESIGN.md`):
  * Pure White (`#ffffff`) & Slate (`#f8fafc`) surfaces, 1px micro-borders, Sunset Orange (`#ff5d08`) & Google Blue (`#0071e3`) accents
  * 6 Streamlined Tabs aligned with the `v1-mcp` (`lguplus_mcp_built`) standard:
      0. 🚀 Getting Started (Selective Flow Composer P1/P2/P3 × W1/W2/W3 + 1-Click GCP Resource Verify + 5-File Code Map)
      1. 🗺️ v1-MCP Flow Grid (6-Layer × P1/P2/P3 × Gate G2-W Interactive Architecture & Asset Inventory)
      2. 🛠️ MCP Guide & Customizer (`aos-builder-core-mcp` 8 Tools + Runtime Domain MCP 3 Tools + Live Tool Runner)
      3. 📚 Wiki (P1) & Graph (P2/P3) (OKF 3-Layer Wiki + BigQuery/Spanner Property Graph Topology & DDL)
      4. ⚡ Workflows (W1~W3) & AI FDE (Selective W1/W2/W3 Workflow Inspector + Live AI FDE Grounded Playground)
      5. 🔗 Lineage & CQ Eval (6-Layer End-to-End Data Lineage + Golden/Boundary CQ Evaluation)
"""
import csv
import glob
import hashlib
import http.server
import json
import os
import sys
from urllib.parse import parse_qs, urlparse

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, BASE_DIR)

from src.agent.reasoning_engine import AiFdeAgentEngine
from src.lineage.lineage_engine import LineageEngine

PORT = int(os.environ.get("PORT", 8080))

STARTER_CONFIG_PATH = "config/starter_config.json"
EVAL_RUBRIC_PATH = "config/eval_rubric.json"
LINEAGE_SPEC_PATH = "config/lineage_spec.json"
CQ_REPORT_PATH = "data/output/cq_benchmark_report.json"
BOUNDARY_REPORT_PATH = "data/output/boundary_benchmark_results.json"

_ENGINE_SINGLETON = None
_LINEAGE_SINGLETON = None


def get_engine() -> AiFdeAgentEngine:
    global _ENGINE_SINGLETON
    if _ENGINE_SINGLETON is None:
        _ENGINE_SINGLETON = AiFdeAgentEngine()
    return _ENGINE_SINGLETON


def get_lineage() -> LineageEngine:
    global _LINEAGE_SINGLETON
    if _LINEAGE_SINGLETON is None:
        eng = get_engine()
        srv = eng.server
        _LINEAGE_SINGLETON = LineageEngine(
            os.path.join(BASE_DIR, LINEAGE_SPEC_PATH),
            {
                "project_id": srv.project_id,
                "fq": srv.fq,
                "dataset_id": srv.fq.split(".", 1)[1],
                "bucket": srv.gcs_bucket,
                "model": eng.model_name,
                "spanner_instance": srv.spanner_instance_id,
                "spanner_database": srv.spanner_database_id,
            },
        )
    return _LINEAGE_SINGLETON


def load_text_file(rel_path: str, default: str = "", root: str = BASE_DIR) -> str:
    p = os.path.join(root, rel_path)
    if os.path.exists(p):
        with open(p, "r", encoding="utf-8") as f:
            return f.read()
    return default


def load_json_file(rel_path: str, default=None, root: str = BASE_DIR):
    p = os.path.join(root, rel_path)
    if os.path.exists(p):
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    return default if default is not None else {}


def load_csv_table(path: str):
    with open(path, "r", encoding="utf-8") as f:
        reader = list(csv.reader(f))
        if not reader:
            return {"headers": [], "rows": []}
        return {"headers": reader[0], "rows": reader[1:]}


def build_eval_summary(root: str = BASE_DIR):
    rubric = load_json_file(EVAL_RUBRIC_PATH, {}, root)
    cq_exists = os.path.exists(os.path.join(root, CQ_REPORT_PATH))
    cq_raw = load_json_file(CQ_REPORT_PATH, {}, root) if cq_exists else {}
    cq_items = cq_raw.get("evaluation_details") or cq_raw.get("test_results") or []
    cq_total = cq_raw.get("total_cqs", len(cq_items)) if cq_exists else 0
    cq_passed = (
        cq_raw.get(
            "passed",
            sum(1 for x in cq_items if x.get("status") == "PASSED" or x.get("verification_status") == "EXACT_MATCH"),
        )
        if cq_exists
        else 0
    )
    cq_rate = round((cq_passed / cq_total) * 100, 1) if cq_total else None
    man_path, man_sha = os.path.join(root, "data/output/input_manifest.json"), None
    if os.path.exists(man_path):
        with open(man_path, "rb") as f:
            man_sha = hashlib.sha256(f.read()).hexdigest()
    if not cq_exists or not cq_total:
        cq_state, cq_label = "PENDING", "미측정"
    elif not cq_raw.get("run_id") or not all(x.get("executed_at") for x in cq_items):
        cq_state, cq_label = "UNMEASURED", "미측정 (실행 기록 없음)"
    elif man_sha and cq_raw.get("input_manifest_sha256") and cq_raw.get("input_manifest_sha256") != man_sha:
        cq_state, cq_label = "STALE", "입력 변경 후 재평가 필요"
    else:
        cq_state = "MEASURED"
        cq_label = f"{cq_passed} / {cq_total} ({cq_rate}%)"

    bd_exists = os.path.exists(os.path.join(root, BOUNDARY_REPORT_PATH))
    bd_raw = load_json_file(BOUNDARY_REPORT_PATH, {}, root) if bd_exists else {}
    bd_cases = bd_raw.get("cases", []) if bd_exists else []

    return {
        "rubric": rubric,
        "golden": {
            "status": cq_state,
            "score_label": cq_label,
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
    }


HTML_PAGE = r"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Agentic Ontology Starter — Minimal v1-MCP Flow & Selective Composer</title>
<link rel="stylesheet" as="style" crossorigin href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css" />
<script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
<style>
  :root {
    --bg-primary: #ffffff;
    --bg-secondary: #f8fafc;
    --bg-tertiary: #f1f5f9;
    --text-primary: #0f172a;
    --text-secondary: #475569;
    --text-muted: #64748b;
    --accent-blue: #0071e3;
    --accent-orange: #ff5d08;
    --accent-emerald: #059669;
    --accent-purple: #7c3aed;
    --border-light: rgba(15, 23, 42, 0.08);
    --border-strong: rgba(15, 23, 42, 0.16);
    --shadow-sm: 0 2px 8px rgba(15, 23, 42, 0.04);
    --shadow-md: 0 8px 24px rgba(15, 23, 42, 0.07);
    --radius-lg: 16px;
    --radius-md: 12px;
    --font-sans: "Pretendard", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    --font-mono: "JetBrains Mono", "SFMono-Regular", Consolas, monospace;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: var(--font-sans);
    background: var(--bg-secondary);
    color: var(--text-primary);
    line-height: 1.55;
    -webkit-font-smoothing: antialiased;
  }
  a { color: var(--accent-blue); text-decoration: none; }
  a:hover { text-decoration: underline; }

  /* Global Header */
  .global-nav {
    position: sticky; top: 0; z-index: 100;
    height: 52px;
    background: rgba(255, 255, 255, 0.92);
    backdrop-filter: blur(12px);
    border-bottom: 1px solid var(--border-light);
    display: flex; align-items: center; justify-content: space-between;
    padding: 0 24px;
  }
  .brand-row { display: flex; align-items: center; gap: 10px; font-weight: 700; font-size: 15px; }
  .brand-pill {
    font-size: 11px; font-weight: 700; padding: 3px 9px; border-radius: 999px;
    background: #eff6ff; color: var(--accent-blue); border: 1px solid #bfdbfe;
  }
  .nav-right { display: flex; align-items: center; gap: 10px; font-size: 12px; }
  .ext-link-pill {
    padding: 5px 11px; border-radius: 999px; font-weight: 600;
    background: var(--bg-tertiary); color: var(--text-primary);
    border: 1px solid var(--border-light); transition: all 0.15s;
  }
  .ext-link-pill:hover { background: #e2e8f0; text-decoration: none; }
  .lang-switch {
    display: inline-flex; background: var(--bg-tertiary); border-radius: 999px; padding: 2px;
    border: 1px solid var(--border-light);
  }
  .lang-btn {
    border: none; background: transparent; padding: 4px 10px; border-radius: 999px;
    font-size: 11px; font-weight: 700; cursor: pointer; color: var(--text-secondary);
  }
  .lang-btn.active { background: var(--bg-primary); color: var(--text-primary); box-shadow: var(--shadow-sm); }

  /* Sub-Nav Tabs */
  .sub-nav {
    position: sticky; top: 52px; z-index: 95;
    background: rgba(255, 255, 255, 0.96);
    backdrop-filter: blur(12px);
    border-bottom: 1px solid var(--border-light);
    padding: 8px 24px;
    display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap;
  }
  .tab-bar { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
  .tab-btn {
    border: 1px solid transparent; background: transparent;
    padding: 7px 14px; border-radius: 999px;
    font-size: 13px; font-weight: 600; color: var(--text-secondary);
    cursor: pointer; display: inline-flex; align-items: center; gap: 6px;
    transition: all 0.15s;
  }
  .tab-btn:hover { background: var(--bg-tertiary); color: var(--text-primary); }
  .tab-btn.active {
    background: var(--text-primary); color: #ffffff;
    box-shadow: var(--shadow-sm);
  }
  .tab-btn.flow-recommended:not(.active) {
    border-color: rgba(0, 113, 227, 0.3);
    background: rgba(0, 113, 227, 0.05);
    color: var(--accent-blue);
  }
  .active-flow-indicator {
    display: flex; align-items: center; gap: 8px;
    font-size: 12px; font-weight: 600;
    background: #fff7ed; color: #c2410c; border: 1px solid #fed7aa;
    padding: 5px 12px; border-radius: 999px;
  }

  /* Layout */
  .container { max-width: 1360px; margin: 0 auto; padding: 24px; }
  .tab-pane { display: none; }
  .tab-pane.active { display: block; }

  .hero-card {
    background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
    border: 1px solid var(--border-light);
    border-radius: var(--radius-lg);
    padding: 28px;
    box-shadow: var(--shadow-sm);
    margin-bottom: 20px;
  }
  .hero-title { font-size: 24px; font-weight: 800; letter-spacing: -0.02em; margin-bottom: 8px; }
  .hero-sub { font-size: 14px; color: var(--text-secondary); max-width: 980px; }

  .section-card {
    background: var(--bg-primary);
    border: 1px solid var(--border-light);
    border-radius: var(--radius-lg);
    padding: 22px;
    box-shadow: var(--shadow-sm);
    margin-bottom: 20px;
  }
  .section-header {
    display: flex; align-items: center; justify-content: space-between; gap: 12px;
    margin-bottom: 16px; flex-wrap: wrap;
  }
  .section-title { font-size: 17px; font-weight: 700; display: flex; align-items: center; gap: 8px; }
  .step-num {
    display: inline-flex; align-items: center; justify-content: center;
    width: 24px; height: 24px; border-radius: 999px;
    background: var(--text-primary); color: #fff; font-size: 12px; font-weight: 800;
  }

  .grid-3 { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 16px; }
  .grid-2 { display: grid; grid-template-columns: repeat(auto-fit, minmax(440px, 1fr)); gap: 16px; }

  /* Flow Preset Cards */
  .flow-card {
    border: 2px solid var(--border-light);
    border-radius: var(--radius-md);
    padding: 18px;
    background: var(--bg-primary);
    cursor: pointer;
    transition: all 0.15s;
    display: flex; flex-direction: column; justify-content: space-between;
  }
  .flow-card:hover { border-color: #94a3b8; transform: translateY(-1px); }
  .flow-card.selected {
    border-color: var(--accent-blue);
    background: #f8fbff;
    box-shadow: 0 4px 16px rgba(0, 113, 227, 0.10);
  }
  .flow-badge {
    display: inline-block; font-size: 11px; font-weight: 700;
    padding: 3px 9px; border-radius: 999px; margin-bottom: 10px;
    background: #eff6ff; color: var(--accent-blue);
  }
  .flow-card.selected .flow-badge { background: var(--accent-blue); color: #fff; }

  /* Custom Toggle Bar */
  .composer-bar {
    margin-top: 16px; padding: 14px 18px;
    background: var(--bg-secondary);
    border: 1px solid var(--border-light);
    border-radius: var(--radius-md);
    display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px;
  }
  .toggle-group { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
  .chip-toggle {
    border: 1px solid var(--border-strong);
    background: #fff; color: var(--text-secondary);
    padding: 5px 12px; border-radius: 999px;
    font-size: 12px; font-weight: 700; cursor: pointer;
    transition: all 0.12s;
  }
  .chip-toggle.on-p { background: #0071e3; color: #fff; border-color: #0071e3; }
  .chip-toggle.on-w { background: #7c3aed; color: #fff; border-color: #7c3aed; }
  .chip-toggle.on-g { background: #059669; color: #fff; border-color: #059669; }

  /* 6-Layer Architecture Grid */
  .layer-row {
    display: flex; align-items: center; justify-content: space-between;
    padding: 12px 16px; border-radius: 10px;
    border: 1px solid var(--border-light);
    margin-bottom: 8px; background: #fff;
    transition: all 0.15s;
  }
  .layer-row.inactive { opacity: 0.38; background: #f8fafc; }
  .layer-row.active-layer {
    border-left: 4px solid var(--accent-blue);
    background: #fcfdff;
  }

  /* Tables & Code */
  table.clean-table { width: 100%; border-collapse: collapse; font-size: 13px; }
  table.clean-table th, table.clean-table td {
    text-align: left; padding: 10px 12px; border-bottom: 1px solid var(--border-light);
    vertical-align: top;
  }
  table.clean-table th {
    font-size: 11px; text-transform: uppercase; letter-spacing: 0.04em;
    color: var(--text-muted); background: var(--bg-secondary); font-weight: 700;
  }
  tr.row-dimmed { opacity: 0.4; }
  tr.row-highlighted { background: rgba(0, 113, 227, 0.04); }

  pre.code-box {
    background: #0f172a; color: #e2e8f0;
    padding: 14px 16px; border-radius: var(--radius-md);
    font-family: var(--font-mono); font-size: 12px;
    overflow-x: auto; line-height: 1.5;
  }
  .btn-primary {
    background: var(--accent-blue); color: #fff; border: none;
    padding: 8px 16px; border-radius: 999px; font-size: 13px; font-weight: 700;
    cursor: pointer; transition: background 0.15s;
  }
  .btn-primary:hover { background: #005bb5; }
  .btn-secondary {
    background: var(--bg-tertiary); color: var(--text-primary);
    border: 1px solid var(--border-strong);
    padding: 7px 14px; border-radius: 999px; font-size: 12px; font-weight: 600;
    cursor: pointer;
  }
  .btn-secondary:hover { background: #e2e8f0; }

  .pill {
    display: inline-block; padding: 2px 8px; border-radius: 999px;
    font-size: 11px; font-weight: 700;
  }
  .pill.blue { background: #dbeafe; color: #1d4ed8; }
  .pill.purple { background: #ede9fe; color: #6d28d9; }
  .pill.green { background: #d1fae5; color: #047857; }
  .pill.orange { background: #ffedd5; color: #c2410c; }
  .pill.slate { background: #e2e8f0; color: #334155; }

  .input-box, select.input-box, textarea.input-box {
    width: 100%; padding: 9px 12px; border-radius: 10px;
    border: 1px solid var(--border-strong); font-family: var(--font-sans); font-size: 13px;
    background: #fff;
  }
  .vis-canvas {
    width: 100%; height: 420px; border: 1px solid var(--border-light);
    border-radius: var(--radius-md); background: #ffffff;
  }
</style>
</head>
<body>

<!-- Global Top Bar -->
<header class="global-nav">
  <div class="brand-row">
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none"><path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" stroke="#0071e3" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/></svg>
    <span>Agentic Ontology Starter</span>
    <span class="brand-pill">v3.0 Minimal · v1-MCP Standard</span>
  </div>
  <div class="nav-right">
    <a class="ext-link-pill" href="https://agentic-ontology-studio-lguplus-mcp-924723860007.asia-northeast3.run.app/" target="_blank" rel="noopener">↗ LG U+ v1-MCP 기준 스튜디오</a>
    <a class="ext-link-pill" href="https://hnh-agentic-ontology-studio-mcp-384182013777.asia-northeast3.run.app/" target="_blank" rel="noopener">↗ LG H&H v1-MCP 스튜디오</a>
    <a class="ext-link-pill" href="https://github.com/seanjungG/agentic-ontology-starter" target="_blank" rel="noopener">GitHub</a>
    <div class="lang-switch">
      <button class="lang-btn active" id="btn-lang-ko" onclick="setLang('ko')">KOR</button>
      <button class="lang-btn" id="btn-lang-en" onclick="setLang('en')">ENG</button>
    </div>
  </div>
</header>

<!-- Sub-Nav with Selective Flow Indicator -->
<nav class="sub-nav">
  <div class="tab-bar">
    <button class="tab-btn active" data-tab="getting-started" onclick="switchTab('getting-started')">🚀 0. Getting Started</button>
    <button class="tab-btn" data-tab="flow-grid" onclick="switchTab('flow-grid')">🗺️ 1. v1-MCP Flow Grid</button>
    <button class="tab-btn" data-tab="mcp-guide" onclick="switchTab('mcp-guide')">🛠️ 2. MCP 역할 &amp; 커스텀 가이드</button>
    <button class="tab-btn" data-tab="wiki-graph" onclick="switchTab('wiki-graph')">📚 3. Wiki (P1) &amp; Graph (P2/P3)</button>
    <button class="tab-btn" data-tab="workflow-agent" onclick="switchTab('workflow-agent')">⚡ 4. Workflow (W1~W3) &amp; AI FDE</button>
    <button class="tab-btn" data-tab="lineage-eval" onclick="switchTab('lineage-eval')">🔗 5. Lineage &amp; CQ Eval</button>
  </div>
  <div class="active-flow-indicator" id="nav-flow-badge">
    <span>선택된 플로우:</span>
    <strong id="nav-flow-label">Flow C · Full v1-MCP (P1·P2·P3 × W1·W2·W3 + G2-W)</strong>
  </div>
</nav>

<main class="container">

  <!-- =====================================================================
       TAB 0: GETTING STARTED (Selective Flow Composer + GCP Connect + Code Map)
       ===================================================================== -->
  <section class="tab-pane active" id="pane-getting-started">
    <div class="hero-card">
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
        <span class="pill orange">GETTING STARTED IN 3 STEPS</span>
        <span class="pill blue">v1-MCP ARCHITECTURE ALIGNED</span>
        <span class="pill green">MINIMAL 5-FILE CORE</span>
      </div>
      <h1 class="hero-title" id="gs-hero-title">누구든 3단계로 시작하는 초경량 Agentic Ontology 스타터 팩</h1>
      <p class="hero-sub" id="gs-hero-sub">
        복잡한 내부 컴파일러 코드는 <strong>코어 빌더 MCP(<code>aos-builder-core-mcp</code>)</strong>로 추상화하여 걷어내고,
        내 도메인에 꼭 필요한 <strong>데이터 경로(<code>P1 문서</code> · <code>P2 원장</code> · <code>P3 통합</code>)</strong>와
        <strong>워크플로우(<code>W1 규정</code> · <code>W2 원장</code> · <code>W3 하이브리드</code>)</strong>만 선택해 즉시 구성·실행할 수 있도록 최소한의 코어 파일만 남겼습니다.
      </p>
    </div>

    <!-- STEP 1: Selective Flow Composer -->
    <div class="section-card">
      <div class="section-header">
        <div class="section-title">
          <span class="step-num">1</span>
          <span id="gs-step1-title">내 프로젝트에 필요한 데이터 경로(P1/P2/P3)와 워크플로우(W1/W2/W3) 플로우 선택</span>
        </div>
        <span style="font-size:12px;color:var(--text-muted);" id="gs-step1-hint">플로우를 선택하면 아래 필요 리소스와 사용할 MCP 도구 목록이 자동으로 필터링됩니다.</span>
      </div>

      <div class="grid-3" id="flow-preset-cards"></div>

      <!-- Granular Path & Stage Toggle Bar -->
      <div class="composer-bar">
        <div class="toggle-group">
          <span style="font-size:12px;font-weight:700;color:var(--text-secondary);margin-right:4px;">세부 경로·단계 직접 조합 (Custom Selective Flow):</span>
          <button class="chip-toggle on-p" id="tog-P1" onclick="toggleFlowChip('paths','P1')">P1 · 비정형 문서/위키</button>
          <button class="chip-toggle on-p" id="tog-P2" onclick="toggleFlowChip('paths','P2')">P2 · 정형 DW 원장/그래프</button>
          <button class="chip-toggle on-p" id="tog-P3" onclick="toggleFlowChip('paths','P3')">P3 · 위키↔원장 브릿지</button>
          <span style="color:#cbd5e1;">|</span>
          <button class="chip-toggle on-w" id="tog-W1" onclick="toggleFlowChip('workflows','W1')">W1 · 규정 워크플로우</button>
          <button class="chip-toggle on-w" id="tog-W2" onclick="toggleFlowChip('workflows','W2')">W2 · 원장 워크플로우</button>
          <button class="chip-toggle on-w" id="tog-W3" onclick="toggleFlowChip('workflows','W3')">W3 · 통합 정산 워크플로우</button>
          <span style="color:#cbd5e1;">|</span>
          <button class="chip-toggle on-g" id="tog-G2W" onclick="toggleGateG2W()">Gate G2-W · 단일출처 상수</button>
        </div>
        <button class="btn-secondary" onclick="switchTab('flow-grid')">선택한 플로우 아키텍처 보기 →</button>
      </div>

      <!-- Dynamic Summary of Selected Flow -->
      <div class="grid-2" style="margin-top:16px;">
        <div style="background:var(--bg-secondary);padding:16px;border-radius:12px;border:1px solid var(--border-light);">
          <div style="font-size:12px;font-weight:700;color:var(--text-secondary);margin-bottom:8px;">📌 선택된 플로우에서 활성화되는 6-Layer &amp; 필수 GCP 리소스</div>
          <div id="selected-flow-layers" style="margin-bottom:10px;"></div>
          <div id="selected-flow-gcp" style="font-size:12px;color:var(--text-secondary);"></div>
        </div>
        <div style="background:var(--bg-secondary);padding:16px;border-radius:12px;border:1px solid var(--border-light);">
          <div style="font-size:12px;font-weight:700;color:var(--text-secondary);margin-bottom:8px;">🛠️ 선택된 플로우에 사용되는 2-Tier MCP 도구 조합</div>
          <div id="selected-flow-mcps" style="font-size:12px;"></div>
          <div style="margin-top:10px;">
            <button class="btn-secondary" onclick="switchTab('mcp-guide')">각 MCP 역할 및 커스텀 방법 자세히 보기 →</button>
          </div>
        </div>
      </div>
    </div>

    <!-- STEP 2: 1-Click GCP Resource Connector -->
    <div class="section-card">
      <div class="section-header">
        <div class="section-title">
          <span class="step-num">2</span>
          <span id="gs-step2-title">내 GCP 리소스 연결 및 실시간 상태 검증 (<code>src/resource_connector.py</code>)</span>
        </div>
        <div style="display:flex;gap:8px;">
          <button class="btn-primary" id="btn-verify-gcp" onclick="verifyGcpResources()">⚡ 라이브 GCP 리소스 연결 검증 실행</button>
        </div>
      </div>

      <div class="grid-2">
        <div>
          <div style="font-size:12px;font-weight:700;color:var(--text-secondary);margin-bottom:6px;">1줄 코드로 내 BigQuery · GCS Wiki · Spanner 연결 (<code>.env</code> 또는 Python)</div>
          <pre class="code-box"># 1) .env 설정 (또는 기본 제공 샘플 리소스 즉시 사용)
GCP_PROJECT_ID=seanjung-poc
BQ_DATASET_ID=starter_ontology_dw
GCS_BUCKET_NAME=seanjung-poc-starter-ontology

# 2) Python / Notebook에서 즉시 연결 및 검증
from src.resource_connector import connect_my_resources
manifest = connect_my_resources(verify=True)</pre>
        </div>
        <div>
          <div style="font-size:12px;font-weight:700;color:var(--text-secondary);margin-bottom:6px;">현재 연결된 Ready-to-Use GCP 리소스 &amp; 실시간 검증 결과</div>
          <div id="gcp-resource-status-box" style="background:var(--bg-secondary);border:1px solid var(--border-light);border-radius:12px;padding:14px;font-size:13px;">
            리소스 매니페스트 로딩 중...
          </div>
        </div>
      </div>
    </div>

    <!-- STEP 3: Minimal 5-File Repository Structure & Hands-On Notebooks -->
    <div class="section-card">
      <div class="section-header">
        <div class="section-title">
          <span class="step-num">3</span>
          <span id="gs-step3-title">초경량 5개 핵심 파일 구조 &amp; 단계별 실습 노트북 (Colab)</span>
        </div>
      </div>
      <div class="grid-2">
        <div>
          <div style="font-size:12px;font-weight:700;color:var(--text-secondary);margin-bottom:8px;">📂 스타터 레포지토리 핵심 코드 5종 (복잡한 파이프라인 코드 전면 제거 완료)</div>
          <table class="clean-table" id="minimal-files-table">
            <thead>
              <tr><th>파일 경로</th><th>핵심 역할 및 커스텀 포인트</th></tr>
            </thead>
            <tbody></tbody>
          </table>
        </div>
        <div>
          <div style="font-size:12px;font-weight:700;color:var(--text-secondary);margin-bottom:8px;">📓 Stage 0~5 실습 노트북 &amp; 화면 바로가기</div>
          <table class="clean-table" id="stage-map-table">
            <thead>
              <tr><th>단계</th><th>핵심 내용</th><th>포털 탭</th><th>Colab 노트북</th></tr>
            </thead>
            <tbody></tbody>
          </table>
        </div>
      </div>
    </div>
  </section>

  <!-- =====================================================================
       TAB 1: v1-MCP FLOW GRID (6-Layer x P1/P2/P3 x Gate G2-W & Asset Inventory)
       ===================================================================== -->
  <section class="tab-pane" id="pane-flow-grid">
    <div class="section-card">
      <div class="section-header">
        <div class="section-title">🗺️ v1-MCP 표준 아키텍처 플로우 그리드 (<code>6-Layer × P1/P2/P3 × W1/W2/W3 × Gate G2-W</code>)</div>
        <div style="display:flex;gap:8px;">
          <button class="btn-secondary" onclick="switchTab('getting-started')">← 플로우 선택 변경</button>
          <a class="btn-secondary" href="https://agentic-ontology-studio-lguplus-mcp-924723860007.asia-northeast3.run.app/" target="_blank">↗ LG U+ v1-MCP 원본 스튜디오 비교</a>
        </div>
      </div>
      <p style="font-size:13px;color:var(--text-secondary);margin-bottom:16px;">
        현재 <strong>Getting Started</strong>에서 선택한 플로우(<span id="fg-current-flow-text" style="font-weight:700;color:var(--accent-blue);"></span>)에 해당하는 데이터 경로와 계층이 하이라이트됩니다.
      </p>

      <!-- P1 / P2 / P3 Cards -->
      <div class="grid-3" id="v1mcp-paths-grid" style="margin-bottom:16px;"></div>

      <!-- W1 / W2 / W3 + Gate G2-W -->
      <div class="grid-3" id="v1mcp-workflows-grid" style="margin-bottom:16px;"></div>

      <!-- 6-Layer Stack -->
      <div style="margin-top:16px;">
        <div style="font-size:13px;font-weight:700;margin-bottom:8px;">6-Layer 엔터프라이즈 온톨로지 계층 (선택된 플로우 활성 상태)</div>
        <div id="v1mcp-six-layers-stack"></div>
      </div>
    </div>

    <!-- Stage 1 Asset Inventory (P1 Docs + P2 DW Tables) -->
    <div class="section-card">
      <div class="section-header">
        <div class="section-title">📦 Stage 1 · 원천 데이터 인벤토리 (<code>P1</code> SHA-256 문서 청크 &amp; <code>P2</code> 정형 DW 마스터 테이블)</div>
      </div>
      <div class="grid-2">
        <div>
          <div style="font-size:13px;font-weight:700;margin-bottom:8px;">📄 P1 · 비정형 정책 가이드 원문 청크 (Gate 0 SHA-256 해시 앵커)</div>
          <div id="asset-chunks-box" style="max-height:360px;overflow-y:auto;"></div>
        </div>
        <div>
          <div style="font-size:13px;font-weight:700;margin-bottom:8px;">🗄️ P2 · 정형 DW 마스터 원장 테이블 (비식별 샘플 데이터)</div>
          <div id="asset-tables-box" style="max-height:360px;overflow-y:auto;"></div>
        </div>
      </div>
    </div>
  </section>

  <!-- =====================================================================
       TAB 2: MCP ARCHITECTURE & CUSTOMIZATION GUIDE (aos-builder-core-mcp + Domain MCP)
       ===================================================================== -->
  <section class="tab-pane" id="pane-mcp-guide">
    <div class="hero-card">
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
        <span class="pill blue">TIER 1 · BUILD-TIME CORE MCP (8 TOOLS)</span>
        <span class="pill purple">TIER 2 · RUNTIME DOMAIN MCP (3 TOOLS)</span>
      </div>
      <h2 class="hero-title" style="font-size:21px;">🛠️ 2-Tier MCP 아키텍처: <code>aos-builder-core-mcp</code> 활용법 및 도메인 MCP 커스텀 가이드</h2>
      <p class="hero-sub" id="mcp-overview-text"></p>
    </div>

    <!-- Tier 1: aos-builder-core-mcp -->
    <div class="section-card">
      <div class="section-header">
        <div class="section-title">🏗️ Tier 1 · 코어 빌더 MCP (<code>aos-builder-core-mcp</code>) — 온톨로지 &amp; 스튜디오 6단계 자동 구축</div>
        <span class="pill blue">Endpoint: /mcp/builder</span>
      </div>

      <div class="grid-2" style="margin-bottom:16px;">
        <div>
          <div style="font-size:12px;font-weight:700;color:var(--text-secondary);margin-bottom:6px;">① Gemini CLI / Claude Code / Cursor 연결 설정 (<code>settings.json</code> / <code>.mcp.json</code>)</div>
          <pre class="code-box" id="builder-mcp-config-code"></pre>
          <div id="builder-mcp-steps-list" style="margin-top:10px;font-size:13px;color:var(--text-secondary);"></div>
        </div>
        <div>
          <div style="font-size:12px;font-weight:700;color:var(--text-secondary);margin-bottom:6px;">② 신규 도메인 적용을 위한 <code>build_spec</code> 커스텀 템플릿</div>
          <pre class="code-box" id="builder-mcp-spec-code" style="max-height:240px;overflow-y:auto;"></pre>
        </div>
      </div>

      <div style="font-size:13px;font-weight:700;margin-bottom:8px;">③ <code>aos-builder-core-mcp</code> 8대 빌드 도구 역할 및 선택된 플로우 매핑 (파란색 하이라이트 = 현재 플로우 필수 단계)</div>
      <table class="clean-table" id="builder-mcp-tools-table">
        <thead>
          <tr><th>Stage</th><th>MCP 도구명</th><th>적용 플로우</th><th>핵심 역할 및 기능</th><th>주요 입력 인자</th><th>산출물 (Artifacts)</th></tr>
        </thead>
        <tbody></tbody>
      </table>
    </div>

    <!-- Tier 2: Runtime Domain Business MCP + Live Tester -->
    <div class="section-card">
      <div class="section-header">
        <div class="section-title">⚡ Tier 2 · 런타임 도메인 비즈니스 MCP (<code>src/agent/mcp_server.py</code> · 3종 도구 역할 &amp; 커스텀 방법)</div>
        <span class="pill purple">Contract 4 (D4.5) 1:1 Workflow Bound</span>
      </div>

      <div class="grid-3" id="runtime-mcp-cards" style="margin-bottom:16px;"></div>

      <div class="grid-2">
        <div>
          <div style="font-size:12px;font-weight:700;color:var(--text-secondary);margin-bottom:6px;">내 도메인 비즈니스 MCP 도구 커스텀 3단계 레시피</div>
          <pre class="code-box" id="runtime-mcp-custom-code"></pre>
        </div>
        <div style="background:var(--bg-secondary);padding:16px;border-radius:12px;border:1px solid var(--border-light);">
          <div style="font-size:13px;font-weight:700;margin-bottom:10px;">🧪 런타임 도메인 MCP 도구 라이브 실행 테스터 (<code>POST /api/mcp/execute</code>)</div>
          <div style="display:grid;grid-template-columns:2fr 1fr;gap:8px;margin-bottom:8px;">
            <select class="input-box" id="mcp-test-tool" onchange="fillMcpSampleArgs()">
              <option value="mcp_lookup_customer_profile">1. mcp_lookup_customer_profile (P2·W2 원장 조회)</option>
              <option value="mcp_calculate_penalty_rule">2. mcp_calculate_penalty_rule (P3·W3 위약금/TCO 산식)</option>
              <option value="mcp_query_graph_and_wiki">3. mcp_query_graph_and_wiki (P1+P2 그래프+위키 탐색)</option>
            </select>
            <select class="input-box" id="mcp-test-engine">
              <option value="bigquery">Engine: BigQuery</option>
              <option value="spanner">Engine: Cloud Spanner</option>
            </select>
          </div>
          <textarea class="input-box" id="mcp-test-args" rows="3" style="font-family:var(--font-mono);font-size:12px;margin-bottom:8px;"></textarea>
          <button class="btn-primary" id="btn-run-mcp" onclick="runLiveMcpTool()">▶ 선택한 도메인 MCP 도구 라이브 실행</button>
          <pre class="code-box" id="mcp-test-output" style="margin-top:10px;max-height:240px;overflow-y:auto;">도구를 선택하고 실행 버튼을 누르면 실제 BigQuery/Spanner 실행 결과와 SQL/GQL, Job ID가 출력됩니다.</pre>
        </div>
      </div>
    </div>
  </section>

  <!-- =====================================================================
       TAB 3: WIKI (P1) & PROPERTY GRAPH (P2/P3)
       ===================================================================== -->
  <section class="tab-pane" id="pane-wiki-graph">
    <div class="grid-2">
      <!-- P1: OKF 3-Layer Wiki -->
      <div class="section-card">
        <div class="section-header">
          <div class="section-title">📘 P1 · OKF 3-Layer 온톨로지 위키 &amp; <code>Gate G2-W1</code> 정책 상수</div>
          <div style="display:flex;gap:6px;">
            <button class="btn-secondary" onclick="showWikiDoc('summary.md')">L1 Summary</button>
            <button class="btn-secondary" onclick="showWikiDoc('entities.md')">L2 Entities</button>
            <button class="btn-secondary" onclick="showWikiDoc('concepts.md')">L3 Concepts</button>
            <button class="btn-secondary" onclick="showWikiDoc('rules.md')">Rules &amp; Constants</button>
          </div>
        </div>
        <div style="font-size:12px;color:var(--text-secondary);margin-bottom:8px;">
          모든 비즈니스 상수(180일, 45,000원, 25% 등)는 코드에 하드코딩하지 않고 위키 문서에 단일 출처(Single Source of Truth)로 정의됩니다.
        </div>
        <pre class="code-box" id="wiki-doc-viewer" style="max-height:460px;overflow-y:auto;background:#f8fafc;color:#0f172a;border:1px solid var(--border-light);"></pre>
      </div>

      <!-- P2/P3: Property Graph Topology & DDL -->
      <div class="section-card">
        <div class="section-header">
          <div class="section-title">🕸️ P2/P3 · 듀얼 Property Graph 토폴로지 (BigQuery &amp; Spanner GQL)</div>
          <div style="display:flex;gap:6px;">
            <button class="btn-secondary" onclick="toggleGraphDdl('bq')">BigQuery SQL:2023 DDL</button>
            <button class="btn-secondary" onclick="toggleGraphDdl('spanner')">Spanner ISO GQL DDL</button>
          </div>
        </div>
        <div id="pg-network-canvas" class="vis-canvas" style="height:280px;margin-bottom:10px;"></div>
        <pre class="code-box" id="pg-ddl-viewer" style="max-height:170px;overflow-y:auto;"></pre>
      </div>
    </div>
  </section>

  <!-- =====================================================================
       TAB 4: WORKFLOWS (W1~W3) & AI FDE PLAYGROUND
       ===================================================================== -->
  <section class="tab-pane" id="pane-workflow-agent">
    <!-- W1 / W2 / W3 Workflows & Business Rules -->
    <div class="section-card">
      <div class="section-header">
        <div class="section-title">🔀 Stage 3/4 · 선택형 비즈니스 워크플로우 (<code>W1 · W2 · W3</code>) &amp; <code>D4.5</code> 도구 바인딩</div>
        <div style="display:flex;gap:6px;">
          <button class="btn-secondary" onclick="filterWorkflows('ALL')">전체 (W1+W2+W3)</button>
          <button class="btn-secondary" onclick="filterWorkflows('W1')">W1 (규정 가이드)</button>
          <button class="btn-secondary" onclick="filterWorkflows('W2')">W2 (원장 검증)</button>
          <button class="btn-secondary" onclick="filterWorkflows('W3')">W3 (통합 정산)</button>
        </div>
      </div>
      <div class="grid-3" id="workflow-cards-box"></div>
    </div>

    <!-- AI FDE Agent Playground -->
    <div class="section-card">
      <div class="section-header">
        <div class="section-title">🤖 Stage 4 · AI FDE 무환각 에이전트 플레이그라운드 (<code>gemini-3.8-flash</code> + 3 Domain MCP Tools)</div>
        <div style="display:flex;gap:8px;align-items:center;">
          <select class="input-box" id="fde-engine-select" style="width:210px;">
            <option value="bigquery">Graph Engine: BigQuery</option>
            <option value="spanner">Graph Engine: Cloud Spanner</option>
          </select>
        </div>
      </div>

      <div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:10px;">
        <button class="btn-secondary" onclick="setFdeSample('CUST_DEMO_001 고객이 5G 라이트+ (55,000원) 요금제로 변경하면 위약금이 발생하나요?')">예시 1 (W3 통합 정산 · 위약금 면제 판정)</button>
        <button class="btn-secondary" onclick="setFdeSample('Galaxy S25 Ultra 256GB 단말기로 5G 프리미어 에센셜 (85,000원) 가입 시 공시지원금과 선택약정 24개월 TCO를 비교해줘.')">예시 2 (W3 · 공시지원금 vs 선택약정 24M TCO)</button>
        <button class="btn-secondary" onclick="setFdeSample('CUST_DEMO_002 시니어 고객이 개통 95일째에 요금제를 하향하면 위약금이 얼마인가요?')">예시 3 (W1/W3 · 시니어 복지 특례 면제)</button>
      </div>

      <div style="display:flex;gap:10px;margin-bottom:14px;">
        <input type="text" class="input-box" id="fde-query-input" value="CUST_DEMO_001 고객이 5G 라이트+ (55,000원) 요금제로 변경하면 위약금이 발생하나요?" />
        <button class="btn-primary" id="btn-run-fde" onclick="runFdeQuery()" style="white-space:nowrap;">▶ AI FDE 실행</button>
      </div>

      <div class="grid-2">
        <div>
          <div style="font-size:12px;font-weight:700;color:var(--text-secondary);margin-bottom:6px;">근거 기반 합성 답변 (Grounded Answer &amp; SHA-256 Citations)</div>
          <div id="fde-answer-box" style="background:var(--bg-secondary);border:1px solid var(--border-light);border-radius:12px;padding:16px;min-height:220px;font-size:13px;white-space:pre-wrap;">질문을 입력하고 [AI FDE 실행]을 클릭하세요.</div>
        </div>
        <div>
          <div style="font-size:12px;font-weight:700;color:var(--text-secondary);margin-bottom:6px;">추출된 슬롯 · 체이닝된 도메인 MCP 도구 · BigQuery Job ID</div>
          <pre class="code-box" id="fde-telemetry-box" style="min-height:220px;max-height:360px;overflow-y:auto;">// 실행 텔레메트리 대기 중</pre>
        </div>
      </div>
    </div>
  </section>

  <!-- =====================================================================
       TAB 5: 6-LAYER LINEAGE & CQ EVALUATION
       ===================================================================== -->
  <section class="tab-pane" id="pane-lineage-eval">
    <div class="section-card">
      <div class="section-header">
        <div class="section-title">🔗 Stage 5 · 6-Layer 엔드투엔드 데이터 리니지 (노드 클릭 시 상·하류 추적)</div>
        <span class="pill green" id="lineage-summary-pill">6 Layers Connected</span>
      </div>
      <div class="grid-2">
        <div id="lineage-network-canvas" class="vis-canvas" style="height:360px;"></div>
        <div>
          <div style="font-size:12px;font-weight:700;color:var(--text-secondary);margin-bottom:6px;">선택한 리니지 노드의 상류(Upstream) / 하류(Downstream) 추적 결과</div>
          <pre class="code-box" id="lineage-trace-box" style="height:335px;overflow-y:auto;">왼쪽 그래프에서 노드를 클릭하면 원천 문서/원장부터 에이전트 응답까지의 전체 계보가 표시됩니다.</pre>
        </div>
      </div>
    </div>

    <div class="section-card">
      <div class="section-header">
        <div class="section-title">✅ Golden &amp; Boundary Competency Question (CQ) 벤치마크 검증 결과</div>
        <span class="pill blue" id="eval-score-badge">Loading...</span>
      </div>
      <div style="overflow-x:auto;">
        <table class="clean-table" id="cq-eval-table">
          <thead>
            <tr><th>CQ ID</th><th>분류/도구</th><th>질문 (Competency Question)</th><th>기대 결과 / 호출 도구</th><th>근거 청크 (Anchor)</th><th>상태</th></tr>
          </thead>
          <tbody></tbody>
        </table>
      </div>
    </div>
  </section>

</main>

<script>
  let currentLang = 'ko';
  let resourceManifest = null;
  let globalAssets = null;
  let globalGraph = null;
  let selectedPresetId = 'flow_p3_w3';
  let customFlow = {
    paths: new Set(['P1', 'P2', 'P3']),
    workflows: new Set(['W1', 'W2', 'W3']),
    gate_g2w: true
  };

  function esc(s) {
    return String(s ?? '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  }

  function setLang(lang) {
    currentLang = lang;
    document.getElementById('btn-lang-ko').classList.toggle('active', lang === 'ko');
    document.getElementById('btn-lang-en').classList.toggle('active', lang === 'en');
    renderAll();
  }

  function switchTab(tabId) {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.toggle('active', b.dataset.tab === tabId));
    document.querySelectorAll('.tab-pane').forEach(p => p.classList.toggle('active', p.id === 'pane-' + tabId));
    if (tabId === 'wiki-graph') ensureAssetsAndGraphLoaded();
    if (tabId === 'workflow-agent') ensureAssetsAndGraphLoaded();
    if (tabId === 'flow-grid') ensureAssetsAndGraphLoaded();
    if (tabId === 'lineage-eval') ensureLineageAndEvalLoaded();
  }

  async function initPortal() {
    const res = await fetch('/api/resources');
    resourceManifest = await res.json();
    selectFlowPreset('flow_p3_w3');
    renderAll();
    fillMcpSampleArgs();
  }

  function selectFlowPreset(presetId) {
    selectedPresetId = presetId;
    const presets = (resourceManifest && resourceManifest.selective_flow_presets) || {};
    const p = presets[presetId];
    if (p) {
      customFlow.paths = new Set(p.paths || []);
      customFlow.workflows = new Set(p.workflows || []);
      customFlow.gate_g2w = !!p.gate_g2w;
    }
    renderFlowSelection();
  }

  function toggleFlowChip(group, code) {
    selectedPresetId = 'custom';
    const setObj = customFlow[group];
    if (setObj.has(code) && setObj.size > 1) setObj.delete(code);
    else setObj.add(code);
    renderFlowSelection();
  }

  function toggleGateG2W() {
    selectedPresetId = 'custom';
    customFlow.gate_g2w = !customFlow.gate_g2w;
    renderFlowSelection();
  }

  function renderAll() {
    if (!resourceManifest) return;
    const ko = currentLang === 'ko';
    document.getElementById('gs-hero-title').textContent = ko
      ? '누구든 3단계로 시작하는 초경량 Agentic Ontology 스타터 팩'
      : 'Start in 3 Steps — Minimal Agentic Ontology Starter Pack (v1-MCP Aligned)';
    document.getElementById('gs-hero-sub').innerHTML = ko
      ? '복잡한 내부 컴파일러 코드는 <strong>코어 빌더 MCP(<code>aos-builder-core-mcp</code>)</strong>로 추상화하여 걷어내고, 내 도메인에 꼭 필요한 <strong>데이터 경로(<code>P1 문서</code> · <code>P2 원장</code> · <code>P3 통합</code>)</strong>와 <strong>워크플로우(<code>W1 규정</code> · <code>W2 원장</code> · <code>W3 하이브리드</code>)</strong>만 선택해 즉시 구성·실행할 수 있도록 최소한의 코어 파일만 남겼습니다.'
      : 'Heavy compiler plumbing is abstracted into <strong>Builder Core MCP (<code>aos-builder-core-mcp</code>)</strong>. Select only the <strong>Data Paths (<code>P1 Docs</code> · <code>P2 Ledger</code> · <code>P3 Hybrid</code>)</strong> and <strong>Workflows (<code>W1</code> · <code>W2</code> · <code>W3</code>)</strong> your domain needs.';

    renderFlowSelection();
    renderGcpStatusBox(resourceManifest.ready_to_use_gcp_resources, resourceManifest.verification);
    renderMinimalFilesAndStages();
    renderMcpGuideTab();
  }

  function renderFlowSelection() {
    if (!resourceManifest) return;
    const ko = currentLang === 'ko';
    const presets = resourceManifest.selective_flow_presets || {};
    const cardsEl = document.getElementById('flow-preset-cards');
    cardsEl.innerHTML = Object.values(presets).map(p => {
      const sel = selectedPresetId === p.id ? 'selected' : '';
      return `<div class="flow-card ${sel}" onclick="selectFlowPreset('${esc(p.id)}')">
        <div>
          <span class="flow-badge">${esc(p.badge)}</span>
          <div style="font-size:15px;font-weight:800;margin-bottom:6px;">${esc(ko ? p.title_ko : p.title_en)}</div>
          <div style="font-size:12.5px;color:var(--text-secondary);margin-bottom:12px;">${esc(ko ? p.desc_ko : p.desc_en)}</div>
        </div>
        <div style="display:flex;gap:6px;flex-wrap:wrap;padding-top:8px;border-top:1px solid var(--border-light);">
          ${(p.paths || []).map(x => `<span class="pill blue">${esc(x)}</span>`).join('')}
          ${(p.workflows || []).map(x => `<span class="pill purple">${esc(x)}</span>`).join('')}
          ${p.gate_g2w ? `<span class="pill green">Gate G2-W</span>` : ''}
        </div>
      </div>`;
    }).join('');

    ['P1','P2','P3'].forEach(c => {
      const el = document.getElementById('tog-' + c);
      if (el) el.classList.toggle('on-p', customFlow.paths.has(c));
    });
    ['W1','W2','W3'].forEach(c => {
      const el = document.getElementById('tog-' + c);
      if (el) el.classList.toggle('on-w', customFlow.workflows.has(c));
    });
    const gEl = document.getElementById('tog-G2W');
    if (gEl) gEl.classList.toggle('on-g', customFlow.gate_g2w);

    const pArr = Array.from(customFlow.paths);
    const wArr = Array.from(customFlow.workflows);
    const labelStr = `${pArr.join('+')} × ${wArr.join('+')}${customFlow.gate_g2w ? ' + Gate G2-W' : ''}`;
    document.getElementById('nav-flow-label').textContent = labelStr;
    const fgText = document.getElementById('fg-current-flow-text');
    if (fgText) fgText.textContent = labelStr;

    // Layers & GCP summary
    const arch = resourceManifest.v1_mcp_flow_architecture || {};
    const layers = arch.six_layers || [];
    document.getElementById('selected-flow-layers').innerHTML = layers.map(l => {
      const active = l.paths.some(px => customFlow.paths.has(px));
      return `<span class="pill ${active ? 'blue' : 'slate'}" style="margin:2px;opacity:${active ? 1 : 0.4};">${esc(ko ? l.name_ko : l.name_en)}</span>`;
    }).join('');

    const reqGcp = [];
    if (customFlow.paths.has('P1') || customFlow.paths.has('P3')) reqGcp.push('• GCS 3-Layer OKF Wiki (`gs://seanjung-poc-starter-ontology/ontology/`) & `tb_doc_chunks`');
    if (customFlow.paths.has('P2') || customFlow.paths.has('P3')) reqGcp.push('• BigQuery DW & SQL:2023 Property Graph (`seanjung-poc.starter_ontology_dw.STARTER_ONTOLOGY_GRAPH`)');
    reqGcp.push('• Vertex AI Serving (`gemini-3.8-flash`)');
    document.getElementById('selected-flow-gcp').innerHTML = reqGcp.join('<br>');

    // Active MCP tools for this flow
    const mcpGuide = resourceManifest.mcp_architecture_guide || {};
    const bTools = ((mcpGuide.tier1_builder_core_mcp || {}).tools || []).filter(t => t.flows.some(f => customFlow.paths.has(f) || customFlow.workflows.has(f)));
    const rTools = ((mcpGuide.tier2_runtime_domain_mcp || {}).tools || []).filter(t => {
      if (t.tool_name === 'mcp_lookup_customer_profile') return customFlow.paths.has('P2') || customFlow.workflows.has('W2') || customFlow.workflows.has('W3');
      if (t.tool_name === 'mcp_calculate_penalty_rule') return customFlow.paths.has('P3') || customFlow.workflows.has('W3');
      return true;
    });
    document.getElementById('selected-flow-mcps').innerHTML = `
      <div style="margin-bottom:6px;"><strong>① 빌드 코어 MCP (<code>aos-builder-core-mcp</code>):</strong> ${bTools.map(t => `<span class="pill blue" style="margin:2px;">${esc(t.stage)}: ${esc(t.tool_name)}</span>`).join('')}</div>
      <div><strong>② 런타임 도메인 MCP (<code>mcp_server.py</code>):</strong> ${rTools.map(t => `<span class="pill purple" style="margin:2px;">${esc(t.tool_name)}</span>`).join('')}</div>
    `;

    renderV1McpFlowGrid();
    renderMcpGuideTab();
  }

  function renderV1McpFlowGrid() {
    if (!resourceManifest) return;
    const ko = currentLang === 'ko';
    const arch = resourceManifest.v1_mcp_flow_architecture || {};
    document.getElementById('v1mcp-paths-grid').innerHTML = (arch.data_paths || []).map(p => {
      const on = customFlow.paths.has(p.id);
      return `<div class="flow-card ${on ? 'selected' : ''}" style="opacity:${on ? 1 : 0.45};" onclick="toggleFlowChip('paths','${esc(p.id)}')">
        <div>
          <span class="pill ${on ? 'blue' : 'slate'}" style="margin-bottom:8px;">${esc(p.id)} ${on ? '· ACTIVE' : '· INACTIVE'}</span>
          <div style="font-size:14px;font-weight:800;margin-bottom:6px;">${esc(ko ? p.name_ko : p.name_en)}</div>
          <div style="font-size:12px;color:var(--text-secondary);">${esc(ko ? p.flow_ko : p.flow_en)}</div>
        </div>
      </div>`;
    }).join('');

    document.getElementById('v1mcp-workflows-grid').innerHTML = (arch.workflow_points || []).map(w => {
      const on = customFlow.workflows.has(w.id);
      return `<div class="flow-card ${on ? 'selected' : ''}" style="opacity:${on ? 1 : 0.45};" onclick="toggleFlowChip('workflows','${esc(w.id)}')">
        <div>
          <span class="pill ${on ? 'purple' : 'slate'}" style="margin-bottom:8px;">${esc(w.id)} (${esc(w.profile)}) ${on ? '· ACTIVE' : '· INACTIVE'}</span>
          <div style="font-size:14px;font-weight:800;margin-bottom:6px;">${esc(ko ? w.name_ko : w.name_en)}</div>
          <div style="font-size:12px;color:var(--text-secondary);">${esc(ko ? w.desc_ko : w.desc_en)}</div>
        </div>
      </div>`;
    }).join('');

    document.getElementById('v1mcp-six-layers-stack').innerHTML = (arch.six_layers || []).map(l => {
      const on = l.paths.some(px => customFlow.paths.has(px));
      return `<div class="layer-row ${on ? 'active-layer' : 'inactive'}">
        <div>
          <span class="pill ${on ? 'blue' : 'slate'}" style="margin-right:8px;">${esc(l.layer)}</span>
          <strong>${esc(ko ? l.name_ko : l.name_en)}</strong>
        </div>
        <div>
          ${l.paths.map(px => `<span class="pill ${customFlow.paths.has(px) ? 'green' : 'slate'}" style="margin-left:4px;">${esc(px)}</span>`).join('')}
        </div>
      </div>`;
    }).join('');
  }

  function renderGcpStatusBox(gcp, verification) {
    const el = document.getElementById('gcp-resource-status-box');
    if (!gcp) return;
    let html = `
      <div style="display:grid;grid-template-columns:140px 1fr;row-gap:6px;font-size:12.5px;">
        <span style="color:var(--text-muted);font-weight:600;">GCP Project / Region:</span>
        <code>${esc(gcp.gcp_project_id)} (${esc(gcp.region)})</code>
        <span style="color:var(--text-muted);font-weight:600;">BigQuery DW &amp; Graph:</span>
        <code>${esc(gcp.bigquery_property_graph)}</code>
        <span style="color:var(--text-muted);font-weight:600;">GCS 3-Layer Wiki:</span>
        <code>${esc(gcp.gcs_wiki_bucket)}</code>
        <span style="color:var(--text-muted);font-weight:600;">Builder Core MCP:</span>
        <code>${esc(gcp.builder_core_mcp_url)}</code>
        <span style="color:var(--text-muted);font-weight:600;">Serving Model:</span>
        <code>${esc(gcp.serving_model)}</code>
      </div>
    `;
    if (verification) {
      const st = verification.status === 'READY' ? 'green' : 'orange';
      const cnt = (verification.bigquery_dw || {}).counts || {};
      const gPaths = (verification.bigquery_property_graph || {}).verified_multi_hop_paths ?? 0;
      const wk = verification.okf_3layer_wiki_and_workflows || {};
      html += `
        <div style="margin-top:12px;padding-top:10px;border-top:1px solid var(--border-light);font-size:12px;">
          <span class="pill ${st}">LIVE VERIFIED: ${esc(verification.status)} (${esc(verification.elapsed_ms)}ms)</span>
          <div style="margin-top:6px;color:var(--text-secondary);">
            • <strong>BigQuery DW:</strong> contracts=${esc(cnt.contracts)}, devices=${esc(cnt.devices)}, plans=${esc(cnt.plans)}, policies=${esc(cnt.policies)}, chunks=${esc(cnt.doc_chunks)} (Job: <code>${esc((verification.bigquery_dw || {}).job_id)}</code>)<br>
            • <strong>Property Graph:</strong> verified multi-hop paths=${esc(gPaths)} (Job: <code>${esc((verification.bigquery_property_graph || {}).job_id)}</code>)<br>
            • <strong>OKF Wiki &amp; Workflows:</strong> GCS objects=${esc(wk.gcs_object_count)}, Rules=${esc(wk.business_rules_count)}, Workflows=${esc(wk.business_workflows_count)}, WCQ=${esc(wk.workflow_cqs_count)}
          </div>
        </div>
      `;
    }
    el.innerHTML = html;
  }

  async function verifyGcpResources() {
    const btn = document.getElementById('btn-verify-gcp');
    btn.disabled = true;
    btn.textContent = '⏳ GCP 리소스 라이브 검증 중...';
    try {
      const res = await fetch('/api/resources?verify=1');
      resourceManifest = await res.json();
      renderGcpStatusBox(resourceManifest.ready_to_use_gcp_resources, resourceManifest.verification);
    } finally {
      btn.disabled = false;
      btn.textContent = '⚡ 라이브 GCP 리소스 연결 검증 실행';
    }
  }

  function renderMinimalFilesAndStages() {
    if (!resourceManifest) return;
    const ko = currentLang === 'ko';
    const files = ((resourceManifest.code_exposure_boundary || {}).minimal_repo_files) || [];
    document.querySelector('#minimal-files-table tbody').innerHTML = files.map(f => `
      <tr>
        <td><code>${esc(f.file)}</code></td>
        <td>${esc(ko ? f.role_ko : f.role_en)}</td>
      </tr>
    `).join('');

    const stages = resourceManifest.stage_unified_map || [];
    document.querySelector('#stage-map-table tbody').innerHTML = stages.map(s => {
      const tabKey = (s.starter_tab || '').replace('?tab=', '');
      const nbPath = ko ? s.notebook_ko : s.notebook_en;
      const colabUrl = `https://colab.research.google.com/github/seanjungG/agentic-ontology-starter/blob/main/${nbPath}`;
      return `<tr>
        <td><strong>${esc(s.stage)}</strong></td>
        <td>${esc(ko ? s.title_ko : s.title_en)}</td>
        <td><button class="btn-secondary" style="padding:3px 9px;font-size:11px;" onclick="switchTab('${esc(tabKey)}')">이동</button></td>
        <td><a href="${esc(colabUrl)}" target="_blank" rel="noopener">Colab 열기 ↗</a></td>
      </tr>`;
    }).join('');
  }

  function renderMcpGuideTab() {
    if (!resourceManifest) return;
    const ko = currentLang === 'ko';
    const guide = resourceManifest.mcp_architecture_guide || {};
    document.getElementById('mcp-overview-text').textContent = ko ? guide.overview_ko : guide.overview_en;

    const t1 = guide.tier1_builder_core_mcp || {};
    document.getElementById('builder-mcp-config-code').textContent = JSON.stringify(t1.mcp_client_config_snippet || {}, null, 2);
    document.getElementById('builder-mcp-spec-code').textContent = JSON.stringify(t1.custom_build_spec_example || {}, null, 2);
    const steps = (ko ? t1.how_to_use_ko : t1.how_to_use_en) || [];
    document.getElementById('builder-mcp-steps-list').innerHTML = steps.map(s => `<div style="margin-bottom:4px;">• ${esc(s)}</div>`).join('');

    const bTools = t1.tools || [];
    document.querySelector('#builder-mcp-tools-table tbody').innerHTML = bTools.map(t => {
      const active = (t.flows || []).some(f => customFlow.paths.has(f) || customFlow.workflows.has(f));
      return `<tr class="${active ? 'row-highlighted' : 'row-dimmed'}">
        <td><span class="pill ${active ? 'blue' : 'slate'}">${esc(t.stage)}</span></td>
        <td><code>${esc(t.tool_name)}</code></td>
        <td>${(t.flows || []).map(f => `<span class="pill green" style="margin:1px;">${esc(f)}</span>`).join('')}</td>
        <td>${esc(ko ? t.role_ko : t.role_en)}</td>
        <td><code>${esc(t.key_args)}</code></td>
        <td><code>${esc(t.outputs)}</code></td>
      </tr>`;
    }).join('');

    const t2 = guide.tier2_runtime_domain_mcp || {};
    document.getElementById('runtime-mcp-custom-code').textContent = t2.customization_3steps_code || '';
    document.getElementById('runtime-mcp-cards').innerHTML = (t2.tools || []).map(t => `
      <div class="flow-card selected" style="cursor:default;">
        <div>
          <span class="pill purple" style="margin-bottom:8px;">${esc(t.flow_binding)}</span>
          <div style="font-size:14px;font-weight:800;margin-bottom:6px;"><code>${esc(t.tool_name)}</code></div>
          <div style="font-size:12.5px;color:var(--text-secondary);margin-bottom:10px;">${esc(ko ? t.role_ko : t.role_en)}</div>
        </div>
        <div style="font-size:12px;background:#fff;padding:10px;border-radius:8px;border:1px solid var(--border-light);">
          <strong>💡 커스텀 팁:</strong> ${esc(ko ? t.customize_tip_ko : t.customize_tip_en)}
        </div>
      </div>
    `).join('');
  }

  function fillMcpSampleArgs() {
    const toolName = document.getElementById('mcp-test-tool').value;
    const samples = {
      mcp_lookup_customer_profile: { customer_id: "CUST_DEMO_001" },
      mcp_calculate_penalty_rule: { customer_id: "CUST_DEMO_001", target_plan_name: "5G 슬림 (45,000원)", elapsed_days: 95 },
      mcp_query_graph_and_wiki: { device_name: "Galaxy S25 Ultra 256GB" }
    };
    document.getElementById('mcp-test-args').value = JSON.stringify(samples[toolName] || {}, null, 2);
  }

  async function runLiveMcpTool() {
    const toolName = document.getElementById('mcp-test-tool').value;
    const engine = document.getElementById('mcp-test-engine').value;
    const outEl = document.getElementById('mcp-test-output');
    let args = {};
    try {
      args = JSON.parse(document.getElementById('mcp-test-args').value || '{}');
    } catch (e) {
      outEl.textContent = 'JSON 파싱 오류: ' + e.message;
      return;
    }
    args.engine = engine;
    outEl.textContent = '⏳ 실행 중...';
    const res = await fetch('/api/mcp/execute', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tool_name: toolName, args })
    });
    const data = await res.json();
    outEl.textContent = JSON.stringify(data, null, 2);
  }

  async function ensureAssetsAndGraphLoaded() {
    if (!globalAssets) {
      const r = await fetch('/api/assets');
      globalAssets = await r.json();
      renderAssetsInventory();
      showWikiDoc('summary.md');
      filterWorkflows('ALL');
    }
    if (!globalGraph) {
      const g = await fetch('/api/graph');
      globalGraph = await g.json();
      toggleGraphDdl('bq');
      renderPropertyGraphVis();
    }
  }

  function renderAssetsInventory() {
    if (!globalAssets) return;
    const chunks = globalAssets.chunks || [];
    document.getElementById('asset-chunks-box').innerHTML = `
      <table class="clean-table">
        <thead><tr><th>Chunk ID</th><th>원문 섹션</th><th>SHA-256 Anchor</th></tr></thead>
        <tbody>${chunks.map(c => `
          <tr>
            <td><code>${esc(c.chunk_id)}</code></td>
            <td>${esc(c.section_title)}</td>
            <td><code>${esc((c.content_sha256 || '').slice(0, 18))}</code></td>
          </tr>
        `).join('')}</tbody>
      </table>
    `;
    const tables = globalAssets.tables || {};
    document.getElementById('asset-tables-box').innerHTML = `
      <table class="clean-table">
        <thead><tr><th>DW 테이블명</th><th>행 수</th><th>주요 컬럼</th></tr></thead>
        <tbody>${Object.entries(tables).map(([name, t]) => `
          <tr>
            <td><code>tb_${esc(name)}</code></td>
            <td><span class="pill blue">${esc((t.rows || []).length)} rows</span></td>
            <td><code>${esc((t.headers || []).join(', '))}</code></td>
          </tr>
        `).join('')}</tbody>
      </table>
    `;
  }

  function showWikiDoc(filename) {
    if (!globalAssets || !globalAssets.wiki) return;
    const txt = globalAssets.wiki[filename] || '문서를 찾을 수 없습니다.';
    document.getElementById('wiki-doc-viewer').textContent = typeof txt === 'string' ? txt : JSON.stringify(txt, null, 2);
  }

  function toggleGraphDdl(kind) {
    if (!globalGraph) return;
    document.getElementById('pg-ddl-viewer').textContent = kind === 'spanner' ? globalGraph.spanner_ddl : globalGraph.ddl;
  }

  function renderPropertyGraphVis() {
    if (!globalGraph || !globalGraph.topology || typeof vis === 'undefined') return;
    const container = document.getElementById('pg-network-canvas');
    const topo = globalGraph.topology;
    const nodes = new vis.DataSet((topo.nodes || []).map(n => ({
      id: n.id,
      label: `${n.label || n.id}\n(${n.type || 'Node'})`,
      shape: 'box',
      margin: 8,
      font: { size: 11, face: 'Pretendard' },
      color: { background: '#eff6ff', border: '#0071e3' }
    })));
    const edges = new vis.DataSet((topo.edges || []).map(e => ({
      from: e.source || e.from,
      to: e.target || e.to,
      label: e.label || e.type || '',
      arrows: 'to',
      font: { size: 10, align: 'middle' }
    })));
    new vis.Network(container, { nodes, edges }, {
      physics: { stabilization: true },
      interaction: { hover: true }
    });
  }

  function filterWorkflows(point) {
    if (!globalAssets || !globalAssets.wiki) return;
    const wfObj = globalAssets.wiki['business_workflows.json'] || {};
    const wfs = (wfObj.workflows || []).filter(w => point === 'ALL' || (w.workflow_point || w.extraction_point || w.tier) === point);
    document.getElementById('workflow-cards-box').innerHTML = wfs.map(w => {
      const rules = w.governed_rules || w.rules_bound || [];
      const tools = w.tools_bound || (w.steps || []).filter(s => s && s.mcp_tool).map(s => s.mcp_tool);
      const stepLines = (w.steps || []).map(s => typeof s === 'string' ? s : (s.description_ko || s.step_id || ''));
      return `
      <div class="flow-card selected" style="cursor:default;">
        <div>
          <div style="display:flex;justify-content:space-between;margin-bottom:8px;">
            <span class="pill purple">${esc(w.workflow_point || w.extraction_point || w.tier || 'W3')} · ${esc(w.agent_profile || w.pattern_matrix || 'full')}</span>
            <code>${esc(w.workflow_id)}</code>
          </div>
          <div style="font-size:14px;font-weight:800;margin-bottom:6px;">${esc(w.name_ko || w.name || w.name_en)}</div>
          <div style="font-size:12px;color:var(--text-secondary);margin-bottom:8px;">${esc(w.trigger_intent_ko || w.pattern_matrix || '')}</div>
          <div style="font-size:11.5px;color:var(--text-secondary);margin-bottom:10px;">${stepLines.map(s => `<div>• ${esc(s)}</div>`).join('')}</div>
        </div>
        <div style="font-size:11.5px;border-top:1px solid var(--border-light);padding-top:8px;">
          <div><strong>적용 룰:</strong> ${rules.map(r => `<code>${esc(r)}</code>`).join(', ')}</div>
          <div style="margin-top:4px;"><strong>D4.5 바인딩 도구:</strong> ${tools.map(t => `<span class="pill blue" style="margin:1px;">${esc(t)}</span>`).join('')}</div>
        </div>
      </div>`;
    }).join('');
  }

  function setFdeSample(q) {
    document.getElementById('fde-query-input').value = q;
  }

  async function runFdeQuery() {
    const q = document.getElementById('fde-query-input').value.trim();
    const engine = document.getElementById('fde-engine-select').value;
    if (!q) return;
    const btn = document.getElementById('btn-run-fde');
    const ansEl = document.getElementById('fde-answer-box');
    const telEl = document.getElementById('fde-telemetry-box');
    btn.disabled = true;
    ansEl.textContent = '⏳ Vertex AI (gemini-3.8-flash) 슬롯 추출 및 도메인 MCP 도구 실행 중...';
    telEl.textContent = '// 실행 중...';
    try {
      const res = await fetch('/api/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: q, engine })
      });
      const data = await res.json();
      ansEl.textContent = data.final_synthesis || data.answer || JSON.stringify(data, null, 2);
      telEl.textContent = JSON.stringify({
        status: data.status,
        engine: data.engine,
        model: data.model,
        extracted_parameters: data.extracted_parameters,
        dispatched_tools: data.dispatched_tools,
        bq_job_ids: data.bq_job_ids,
        grounded_chunks: data.grounded_chunks,
        total_elapsed_ms: data.total_elapsed_ms
      }, null, 2);
    } finally {
      btn.disabled = false;
    }
  }

  async function ensureLineageAndEvalLoaded() {
    const [linRes, evalRes] = await Promise.all([
      fetch('/api/lineage/graph'),
      fetch('/api/eval/summary')
    ]);
    const linData = await linRes.json();
    const evalData = await evalRes.json();

    if (typeof vis !== 'undefined') {
      const container = document.getElementById('lineage-network-canvas');
      const nodes = new vis.DataSet((linData.nodes || []).map(n => ({
        id: n.id,
        label: `${n.label}\n[${n.layer}]`,
        shape: 'box',
        margin: 7,
        font: { size: 11 },
        color: { background: '#f8fafc', border: '#0071e3' }
      })));
      const edges = new vis.DataSet((linData.edges || []).map(e => ({
        from: e.source || e.from,
        to: e.target || e.to,
        arrows: 'to'
      })));
      const net = new vis.Network(container, { nodes, edges }, { physics: { stabilization: true } });
      net.on('click', async params => {
        if (params.nodes && params.nodes.length > 0) {
          const nid = params.nodes[0];
          const tr = await (await fetch('/api/lineage/trace?node_id=' + encodeURIComponent(nid))).json();
          document.getElementById('lineage-trace-box').textContent = JSON.stringify(tr, null, 2);
        }
      });
    }

    const g = evalData.golden || {};
    document.getElementById('eval-score-badge').textContent = g.score_label || g.status || 'MEASURED';
    document.querySelector('#cq-eval-table tbody').innerHTML = (g.rows || []).map(r => `
      <tr>
        <td><code>${esc(r.cq_id)}</code></td>
        <td><span class="pill blue">${esc(r.category)}</span></td>
        <td>${esc(r.prompt)}</td>
        <td><code>${esc(r.expected_value)}</code></td>
        <td><code>${esc(r.legal_anchor)}</code></td>
        <td><span class="pill ${r.passed ? 'green' : 'orange'}">${esc(r.verification_status)}</span></td>
      </tr>
    `).join('');
  }

  initPortal();
</script>
</body>
</html>
"""


class StudioHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

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
        if path == "/health":
            return self._json({"status": "ok", "version": "3.0.0-minimal"})
        if path == "/api/config":
            return self._json(load_json_file(STARTER_CONFIG_PATH, {}))
        if path == "/api/resources":
            eng = get_engine()
            manifest = eng.server.get_resource_manifest()
            if arg("verify") == "1":
                manifest = {**manifest, "verification": eng.server.connector.verify_ready_resources()}
            return self._json(manifest)
        if path == "/api/catalog":
            return self._json(get_engine().server.get_tool_catalog())
        if path == "/api/assets":
            chunks, wiki = [], {}
            chunk_file = os.path.join(BASE_DIR, "data/output/doc_chunks.jsonl")
            if os.path.exists(chunk_file):
                with open(chunk_file, "r", encoding="utf-8") as f:
                    chunks = [json.loads(line) for line in f if line.strip()]
            wiki_dir = os.path.join(BASE_DIR, "data/llm_wiki")
            for fname in (os.listdir(wiki_dir) if os.path.isdir(wiki_dir) else []):
                fpath = os.path.join(wiki_dir, fname)
                if os.path.isfile(fpath) and not fname.startswith("."):
                    with open(fpath, "r", encoding="utf-8") as f:
                        wiki[fname] = json.load(f) if fname.endswith(".json") else f.read()
            tables = {
                os.path.splitext(os.path.basename(t))[0]: load_csv_table(t)
                for t in sorted(glob.glob(os.path.join(BASE_DIR, "data/input/03_tables/*.csv")))
            }
            return self._json(
                {
                    "chunks": chunks,
                    "wiki": wiki,
                    "tables": tables,
                    "is_sample": True,
                    "manifest": load_json_file("data/output/input_manifest.json", {}),
                    "gate0": load_json_file("data/output/gate0_report.json", {}),
                }
            )
        if path == "/api/graph":
            return self._json(
                {
                    "ddl": load_text_file("data/output/create_property_graph.sql", "-- BigQuery DDL not found"),
                    "spanner_ddl": load_text_file("data/output/create_spanner_graph.sql", "-- Spanner DDL not found"),
                    "topology": load_json_file("data/output/graph_topology.json", {}),
                }
            )
        if path == "/api/cq":
            return self._json(load_json_file(CQ_REPORT_PATH, {"test_results": []}))
        if path == "/api/eval/summary":
            return self._json(build_eval_summary(BASE_DIR))
        if path == "/api/lineage/graph":
            return self._json(get_lineage().build_graph())
        if path == "/api/lineage/trace":
            return self._json(get_lineage().trace(arg("node_id")))
        if path == "/api/lineage/explain":
            return self._json(get_lineage().explain(arg("node_id"), arg("lang", "ko")))

        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        parsed = urlparse(self.path)
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8")
        data = json.loads(body) if body else {}
        eng = get_engine()

        if parsed.path == "/api/query":
            return self._json(eng.execute_cycle(data.get("query", ""), engine=data.get("engine", "bigquery")))
        if parsed.path == "/api/mcp/execute":
            tool_name = data.get("tool_name") or "mcp_lookup_customer_profile"
            args = data.get("args") or data.get("arguments") or {}
            return self._json(eng.server.execute_tool(tool_name, args))

        self.send_response(404)
        self.end_headers()


class ThreadingStudioServer(http.server.ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def run_server():
    server = ThreadingStudioServer(("0.0.0.0", PORT), StudioHandler)
    print(f"[STARTER STUDIO SERVER RUNNING] listening on 0.0.0.0:{PORT}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    run_server()
