# -*- coding: utf-8 -*-
"""
Standalone Enterprise Web Studio Server:
Adheres strictly to 05_DESIGN.md (Pretendard font, dark mode, Apple/Google Enterprise theme,
zero decorative cartoon emojis, responsive layout, bilingual support).
Runs with ZERO external dependencies using Python standard library http.server.
"""
import http.server, socketserver, json, sys, os
from urllib.parse import urlparse, parse_qs
from src.agent.reasoning_engine import AiFdeAgentEngine

PORT = int(os.environ.get("PORT", 8088))
engine = AiFdeAgentEngine()

HTML_PAGE = """<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Enterprise Agentic Ontology Studio</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css">
  <style>
    :root {
      --bg: #000000;
      --card-bg: #1c1c1e;
      --card-border: rgba(255, 255, 255, 0.1);
      --text-primary: #f5f5f7;
      --text-secondary: #86868b;
      --accent: #2997ff;
      --accent-green: #30d158;
      --accent-purple: #bf5af2;
      --font-stack: "Pretendard", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; font-family: var(--font-stack); }
    body { background: var(--bg); color: var(--text-primary); display: flex; flex-direction: column; height: 100vh; overflow: hidden; }
    
    /* Global Topbar 44px */
    .topbar {
      height: 44px;
      background: rgba(28, 28, 30, 0.85);
      backdrop-filter: blur(20px);
      border-bottom: 1px solid var(--card-border);
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 16px;
    }
    .logo { font-size: 13px; font-weight: 700; letter-spacing: -0.2px; color: var(--text-primary); }
    .badge { font-size: 10px; font-weight: 600; padding: 2px 6px; border-radius: 4px; background: rgba(41, 151, 255, 0.15); color: var(--accent); }
    
    /* Navigation Bar 52px */
    .subbar {
      height: 52px;
      border-bottom: 1px solid var(--card-border);
      display: flex;
      align-items: center;
      padding: 0 16px;
      gap: 12px;
      background: #0d0d0e;
    }
    .nav-btn {
      padding: 6px 14px;
      font-size: 12px;
      font-weight: 600;
      border-radius: 6px;
      background: transparent;
      color: var(--text-secondary);
      border: 1px solid transparent;
      cursor: pointer;
    }
    .nav-btn.active {
      background: var(--card-bg);
      color: var(--text-primary);
      border-color: var(--card-border);
    }

    /* Main Container */
    .main-container { flex: 1; display: flex; overflow: hidden; }
    
    /* Left Sidebar: Tool Catalog */
    .sidebar {
      width: 320px;
      border-right: 1px solid var(--card-border);
      background: #0d0d0e;
      overflow-y: auto;
      padding: 16px;
    }
    .section-title { font-size: 11px; font-weight: 700; text-transform: uppercase; color: var(--text-secondary); margin-bottom: 12px; }
    .tool-chip {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 6px;
      padding: 10px 12px;
      margin-bottom: 8px;
      font-size: 11.5px;
    }
    .tool-chip strong { display: block; color: var(--accent); margin-bottom: 2px; }

    /* Right Console: Chat & Execution Timeline */
    .console-pane {
      flex: 1;
      display: flex;
      flex-direction: column;
      background: var(--bg);
    }
    .chat-timeline {
      flex: 1;
      overflow-y: auto;
      padding: 20px;
      display: flex;
      flex-direction: column;
      gap: 16px;
    }
    .trace-card {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 8px;
      padding: 16px;
      font-size: 12.5px;
      line-height: 1.6;
    }
    .trace-card h4 { font-size: 13px; font-weight: 700; color: var(--accent); margin-bottom: 8px; }
    .subgoal-box { background: rgba(191, 90, 242, 0.1); border-left: 3px solid var(--accent-purple); padding: 8px 12px; margin: 8px 0; border-radius: 4px; }
    .obs-box { background: rgba(48, 209, 88, 0.1); border-left: 3px solid var(--accent-green); padding: 8px 12px; margin: 8px 0; border-radius: 4px; }

    /* Input Bar */
    .input-bar {
      padding: 14px 20px;
      background: #0d0d0e;
      border-top: 1px solid var(--card-border);
      display: flex;
      gap: 10px;
    }
    .input-field {
      flex: 1;
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 6px;
      color: var(--text-primary);
      padding: 10px 14px;
      font-size: 13px;
      outline: none;
    }
    .send-btn {
      padding: 10px 20px;
      background: var(--accent);
      color: #fff;
      border: none;
      border-radius: 6px;
      font-size: 12.5px;
      font-weight: 600;
      cursor: pointer;
    }
  </style>
</head>
<body>
  <div class="topbar">
    <div style="display:flex; align-items:center; gap:8px;">
      <span class="logo">Enterprise Agentic Ontology Starter</span>
      <span class="badge">[Zero-Hallucination FDE]</span>
    </div>
    <div style="font-size:11px; color:var(--text-secondary);">Google Cloud BigQuery SQL:2023 & OKF v0.2</div>
  </div>

  <div class="subbar">
    <button class="nav-btn active">AI FDE Studio</button>
    <button class="nav-btn" onclick="alert('Open pipeline/ to inspect ingest & graph builders.')">Pipeline Monitor</button>
    <button class="nav-btn" onclick="alert('Inspect data/output/create_property_graph.sql')">Property Graph DDL</button>
    <button class="nav-btn" onclick="alert('Inspect data/output/cq_benchmark_report.json')">CQ Benchmarks</button>
  </div>

  <div class="main-container">
    <div class="sidebar">
      <div class="section-title">Domain MCP Tool Catalog (11)</div>
      <div class="tool-chip"><strong>mcp_get_device_factory_price</strong>[비즈니스] 단말기 공식 출고가 조회</div>
      <div class="tool-chip"><strong>mcp_get_device_subsidy_by_plan</strong>[비즈니스] 요금제별 공시지원금 & 180일 약정</div>
      <div class="tool-chip"><strong>mcp_calculate_plan_change_penalty</strong>[비즈니스] 요금제 하향 차액정산 위약금</div>
      <div class="tool-chip"><strong>mcp_compare_contract_plans</strong>[비즈니스] 공시지원금 vs 선택약정 비교</div>
      <div class="tool-chip"><strong>mcp_get_policy_anchor_grounding</strong>[비즈니스] 불변 해시 앵커 원천 증거 인출</div>
      <div class="tool-chip"><strong>mcp_inspect_dw_table_schema</strong>[엔지니어링] 물리 DW 테이블 스키마 & 행수</div>
      <div class="tool-chip"><strong>mcp_explore_property_graph</strong>[엔지니어링] BigQuery Property Graph GQL 탐색</div>
      <div class="tool-chip"><strong>mcp_search_dataplex_catalog</strong>[엔지니어링] Dataplex 카탈로그 태그 & PII</div>
      <div class="tool-chip"><strong>mcp_get_lineage_trace</strong>[엔지니어링] 4-Tier 데이터 리니지 추적</div>
      <div class="tool-chip"><strong>mcp_export_graph_ddl</strong>[엔지니어링] 프로퍼티 그래프 DDL 추출</div>
      <div class="tool-chip"><strong>mcp_run_cq_benchmark</strong>[엔지니어링] 20대 Golden CQ 벤치마크</div>
    </div>

    <div class="console-pane">
      <div class="chat-timeline" id="timeline">
        <div class="trace-card">
          <h4>[Welcome] Enterprise Agentic Ontology Starter Console</h4>
          <p>This console demonstrates 0% hallucination deterministic reasoning across structured DW tables and unstructured policy manuals.</p>
          <div style="margin-top:10px; color:var(--text-secondary);">
            Sample Prompts:<br/>
            - <code>Galaxy S26 Ultra 지원금과 원천 DW 테이블 행수 확인해줘</code><br/>
            - <code>개통 후 120일 시점에 요금제 하향 변경 시 위약금 얼마야?</code>
          </div>
        </div>
      </div>

      <div class="input-bar">
        <input type="text" id="query-input" class="input-field" placeholder="Enter inquiry..." onkeydown="if(event.key==='Enter'&&!event.isComposing)sendQuery();"/>
        <button id="send-btn" class="send-btn" onclick="sendQuery()">Run FDE</button>
      </div>
    </div>
  </div>

  <script>
    async function sendQuery() {
      const input = document.getElementById("query-input");
      const btn = document.getElementById("send-btn");
      const timeline = document.getElementById("timeline");
      const q = input.value.trim();
      if (!q) return;

      input.disabled = true;
      btn.disabled = true;

      // Append user bubble
      timeline.innerHTML += `
        <div style="align-self:flex-end; background:rgba(41,151,255,0.15); border:1px solid var(--accent); padding:10px 14px; border-radius:8px; font-size:12.5px; max-width:70%;">
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
          let subGoalsHtml = (lc.step_1_thought.sub_goals || []).map(sg => `<div>• <strong>[${sg.id}]</strong> ${sg.goal} ➔ <code>${sg.tool}</code></div>`).join("");
          let toolsHtml = (lc.step_2_tool_dispatch.dispatched_tools || []).map(dt => `
            <div class="obs-box">
              <strong>Step 2-${dt.step_index}: Dispatched Tool [${dt.tool_name}]</strong><br/>
              <em>Reason: ${dt.reason}</em><br/>
              <code>${dt.intermediate_observation}</code>
            </div>
          `).join("");

          timeline.innerHTML += `
            <div class="trace-card">
              <h4>[AI FDE Lifecycle Execution Trace]</h4>
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
                <strong>Step 4: Final Synthesis</strong><br/>
                <pre style="white-space:pre-wrap; font-family:inherit;">${lc.step_4_synthesis.markdown}</pre>
              </div>
            </div>
          `;
        } else {
          timeline.innerHTML += `<div class="trace-card" style="border-color:#ff453a; color:#ff453a;">Error: ${data.error || 'Execution failed'}</div>`;
        }
      } catch (err) {
        timeline.innerHTML += `<div class="trace-card" style="border-color:#ff453a; color:#ff453a;">Network Error: ${err.message}</div>`;
      } finally {
        input.disabled = false;
        btn.disabled = false;
        input.value = "";
        input.focus();
        timeline.scrollTop = timeline.scrollHeight;
      }
    }
  </script>
</body>
</html>
"""

class StudioHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(HTML_PAGE.encode("utf-8"))

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

def run_server():
    server = socketserver.TCPServer(("", PORT), StudioHandler)
    print(f"[STUDIO SERVER RUNNING] http://127.0.0.1:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    run_server()
