/* flows_v5.js — Starter v5 studio diagram spec for aolflow.js (GOAL-233).
 *
 * One canvas for the whole build: inputs → ingest/profile → OKF wiki → Property Graph → agents → evaluation,
 * in the studio grammar (layer columns × P1 / P3 / P2 lanes). `chips` = build stages S1–S5, `paths` = node sets
 * for the data type chosen in step 3 (P1 documents · P2 tables · P3 both).
 *
 *   AOLFlow.render(host, STARTER_V5.build, { lang, highlight: STARTER_V5.paths.P3, states, onChip })
 */
(function (root) {
  "use strict";

  const build = {
    id: "starter-v5-build",
    title: ["스타터 구축 흐름 — 내 데이터 → 위키 · 그래프 → 에이전트 → 평가", "Starter build flow — your data → wiki · graph → agents → evaluation"],
    w: 1240, h: 448, minWidth: 980,
    cols: [
      { x: 105, layer: "source", t: ["입력", "Input"], s: ["내 문서 · 테이블", "Your docs · tables"] },
      { x: 300, layer: "source", t: ["S1 수집 · S2 CQ", "S1 ingest · S2 CQs"], s: ["파싱 · 적재 · 스코핑", "Parse · load · scope"] },
      { x: 495, layer: "wiki", t: ["S3 OKF 위키", "S3 OKF wiki"], s: ["GCS · 허브", "GCS · hub"] },
      { x: 700, layer: "semantic", t: ["S4 Property Graph", "S4 Property Graph"], s: ["BigQuery", "BigQuery"] },
      { x: 915, layer: "agent", t: ["에이전트", "Agents"], s: ["Core MCP 추론", "Core MCP reasoning"] },
      { x: 1135, layer: "mcp", t: ["S5 평가", "S5 Evaluate"], s: ["CQ 채점", "CQ scoring"] },
    ],
    lanes: [
      { y: 52, h: 120, pill: "P1", name: ["문서 경로", "Document path"], desc: ["문서 → 파싱 → 위키 → Wiki Agent", "docs → parse → wiki → Wiki Agent"] },
      { y: 180, h: 120, pill: "P3", name: ["통합 경로", "Unified path"], desc: ["위키 노드 + 테이블 노드를 한 그래프로", "wiki nodes + table nodes in one graph"] },
      { y: 308, h: 120, pill: "P2", name: ["정형 경로", "Structured path"], desc: ["테이블 → BigQuery → 노드 · 엣지", "tables → BigQuery → nodes · edges"] },
    ],
    nodes: [
      { id: "docs", x: 30, y: 80, w: 150, layer: "source", t: ["문서", "Documents"], s: [[".md · .txt", ".md · .txt"], ["업로드 · GCS · 샘플", "upload · GCS · sample"]],
        tip: { d: ["정책 · 약관 · 매뉴얼 같은 규범 문서. 업로드하면 gs://버킷/aos/<워크스페이스>/raw/ 에 저장되고, GCS 경로를 주면 그 자리에서 읽습니다.",
                   "Normative documents such as policies, terms and manuals. Uploads go to gs://bucket/aos/<workspace>/raw/; GCS paths are read in place."] } },
      { id: "gate0", x: 225, y: 80, w: 150, layer: "source", t: ["파싱 · Gate 0", "Parse · Gate 0"], s: [["섹션 앵커 · 보존율", "Section anchors · fidelity"], ["Core MCP", "Core MCP"]],
        tip: { d: ["Core MCP aos_builder_parse_documents_gate0가 섹션을 나누고 원문 보존율(Gate 0)을 확인합니다. 결과는 parsed/docs.json.",
                   "Core MCP aos_builder_parse_documents_gate0 splits sections and checks fidelity (Gate 0). Result: parsed/docs.json."] } },
      { id: "wiki", x: 420, y: 80, w: 150, layer: "wiki", t: ["OKF 위키", "OKF wiki"], s: [["요약 · 엔티티 · 개념", "Summary · entity · concept"], ["정책 상수 · W1~W7", "Policy constants · W1–W7"]],
        tip: { d: ["aos_core_compile_wiki가 목적에 맞춰 3-Layer 위키를 만들고 품질 게이트 W1~W7을 검사합니다. 정책 상수는 한 페이지에만, applies_to는 테이블 행과 연결됩니다.",
                   "aos_core_compile_wiki compiles a 3-layer wiki for the objective and runs gates W1–W7. Policy constants live on one page; applies_to links to table rows."] } },
      { id: "wagent", x: 840, y: 80, w: 150, layer: "agent", t: "Wiki", s: [["위키만 근거", "Wiki only"], ["read_wiki → answer", "read_wiki → answer"]],
        tip: { d: ["aos_core_agent_step이 읽을 페이지를 고르고, 스타터가 페이지를 넘겨 주면 근거를 인용해 답합니다.",
                   "aos_core_agent_step picks the pages to read; the starter hands them over and the agent answers with citations."] } },
      { id: "cqs", x: 225, y: 208, w: 150, layer: "workflow", t: ["CQ 초안", "CQ draft"], s: [["목적 → 역량 질문", "Objective → questions"], ["기준 답 · 핵심 사실", "Reference · key facts"]],
        tip: { d: ["aos_core_draft_cqs가 목적과 데이터로 에이전트가 답해야 할 질문과 기준 답을 만듭니다. 평가 탭에서 고치거나 추가합니다.",
                   "aos_core_draft_cqs writes the questions the agents must answer, with reference answers. Edit or add them in the Evaluate tab."] } },
      { id: "unified", x: 625, y: 208, w: 150, layer: "semantic", t: ["통합 그래프", "Unified graph"], s: [["위키 노드 + 테이블 노드", "Wiki + table nodes"], ["wiki_bridge · FK", "wiki_bridge · FK"]],
        tip: { d: ["aos_core_design_graph가 설계 · 검증하고 BigQuery DDL을 만들면, 스타터가 Core MCP bigquery_execute_sql로 CREATE PROPERTY GRAPH를 실행합니다.",
                   "aos_core_design_graph designs, validates and generates the BigQuery DDL; the starter runs CREATE PROPERTY GRAPH through Core MCP bigquery_execute_sql."] } },
      { id: "hagent", x: 840, y: 208, w: 150, layer: "agent", t: "Hybrid", s: [["규칙 + 데이터 + 계산", "Rules + data + math"], ["판정 · 계산 (W3)", "Decide & calculate (W3)"]],
        tip: { d: ["위키의 규칙 · 상수와 그래프의 실제 값을 함께 조회하고, 계산은 Core MCP 안에서 처리해 판정까지 답합니다.",
                   "Reads wiki rules/constants and graph values together; calculations run inside the Core MCP, up to a decision."] } },
      { id: "eval", x: 1060, y: 208, w: 150, layer: "mcp", t: ["평가", "Evaluation"], s: [["CQ 재질의 · 채점", "Re-ask CQs · score"], ["통과 1 · 부분 0.5", "pass 1 · partial 0.5"]],
        tip: { d: ["모든 CQ를 담당 에이전트로 다시 묻고 aos_core_judge가 핵심 사실 일치(+필요 시 Gemini)로 채점합니다. 결과는 runs/.",
                   "Every CQ is asked again through its agent and aos_core_judge scores key facts (+ Gemini when needed). Results: runs/."] } },
      { id: "tables", x: 30, y: 336, w: 150, layer: "source", t: ["테이블", "Tables"], s: [[".csv · BigQuery", ".csv · BigQuery"], ["업로드 · GCS · 샘플", "upload · GCS · sample"]],
        tip: { d: ["CSV는 BigQuery 데이터셋에 적재하고, 이미 BigQuery에 있는 테이블은 복사하지 않고 그 자리에서 읽습니다.",
                   "CSVs are loaded into the BigQuery dataset; tables already in BigQuery are read in place, not copied."] } },
      { id: "load", x: 225, y: 336, w: 150, layer: "source", t: ["적재 · 프로파일", "Load · profile"], s: [["bigquery_load_table", "bigquery_load_table"], ["PK · FK 스코핑", "PK · FK scoping"]],
        tip: { d: ["aos_core_scope가 표본 행으로 기본 키와 FK 후보, 데이터 유형(P1/P2/P3)을 정합니다.",
                   "aos_core_scope infers primary keys, FK candidates and the data type (P1/P2/P3) from sample rows."] } },
      { id: "nodes", x: 625, y: 336, w: 150, layer: "semantic", t: ["노드 · 엣지 테이블", "Node · edge tables"], s: [["N_<Label> · E_<…>", "N_<Label> · E_<…>"], ["SQL로 생성", "Built with SQL"]],
        tip: { d: ["테이블 노드와 FK · 브릿지 엣지는 원천 테이블에서 SQL로 만들어 데이터 크기와 상관없이 동작합니다. Enterprise 예약이 없으면 에이전트는 이 테이블에 SQL로 답합니다.",
                   "Table nodes and FK/bridge edges are built with SQL from the source tables, so size does not matter. Without an Enterprise reservation the agents answer with SQL on these tables."] } },
      { id: "gagent", x: 840, y: 336, w: 150, layer: "agent", t: "Graph", s: [["GQL · SQL만 근거", "GQL · SQL only"], ["gql/sql → answer", "gql/sql → answer"]],
        tip: { d: ["aos_core_agent_step이 GQL(GRAPH_TABLE) 또는 SQL을 쓰고, 스타터가 내 신원으로 실행해 결과를 돌려줍니다.",
                   "aos_core_agent_step writes GQL (GRAPH_TABLE) or SQL; the starter runs it with your identity and returns the rows."] } },
    ],
    edges: [
      { id: "docs-gate0", from: "docs", to: "gate0", layer: "source" },
      { id: "gate0-wiki", from: "gate0", to: "wiki", layer: "wiki" },
      { id: "wiki-wagent", from: "wiki", to: "wagent", layer: "agent" },
      { id: "wiki-unified", pts: ["wiki.b", [495, 240], "unified.l+-2,0"], layer: "semantic",
        label: { t: ["위키 노드", "Wiki nodes"], x: 503, y: 196, kind: "plain-left" } },
      { id: "gate0-cqs", pts: ["gate0.b", "cqs.t+0,-2"], layer: "workflow" },
      { id: "tables-load", from: "tables", to: "load", layer: "source" },
      { id: "load-nodes", from: "load", to: "nodes", layer: "semantic" },
      { id: "load-cqs", pts: ["load.t@0.3", "cqs.b@0.3+0,2"], layer: "workflow" },
      { id: "nodes-unified", pts: ["nodes.t", "unified.b+0,2"], layer: "semantic", label: { t: ["테이블 노드", "Table nodes"], x: 708, y: 304, kind: "plain-left" } },
      { id: "unified-hagent", from: "unified", to: "hagent", layer: "agent" },
      { id: "nodes-gagent", from: "nodes", to: "gagent", layer: "agent" },
      { id: "wagent-eval", pts: ["wagent.r", [1030, 112], [1030, 227], "eval.l@0.3+-2,0"], layer: "mcp" },
      { id: "hagent-eval", from: "hagent", to: "eval", layer: "mcp" },
      { id: "gagent-eval", pts: ["gagent.r", [1030, 368], [1030, 253], "eval.l@0.7+-2,0"], layer: "mcp" },
      { id: "cqs-eval", pts: ["cqs.b@0.7", [330, 296], [1135, 296], "eval.b+0,2"], layer: "workflow", kind: "bridge",
        label: { t: ["기준 CQ", "Reference CQs"], x: 880, y: 292, kind: "plain" } },
    ],
    legend: [
      { kind: "flow", color: "semantic", t: ["데이터 흐름 · 색 = 도착 레이어", "Data flow · colour = target layer"] },
      { kind: "bridge", color: "workflow", t: ["평가 기준 (CQ)", "Evaluation reference (CQs)"] },
    ],
    chips: [
      { n: "S1", key: "ingest", t: ["수집 · 프로파일", "Ingest · profile"], nodes: ["docs", "gate0", "tables", "load"] },
      { n: "S2", key: "cqs", t: ["CQ 초안", "CQ draft"], nodes: ["cqs"] },
      { n: "S3", key: "wiki", t: ["OKF 위키", "OKF wiki"], nodes: ["wiki"] },
      { n: "S4", key: "graph", t: ["Property Graph", "Property Graph"], nodes: ["nodes", "unified"] },
      { n: "S5", key: "eval", t: ["에이전트 · 평가", "Agents · evaluation"], nodes: ["wagent", "gagent", "hagent", "eval"] },
    ],
  };

  const paths = {
    P1: ["docs", "gate0", "wiki", "wagent", "cqs", "eval"],
    P2: ["tables", "load", "nodes", "gagent", "cqs", "eval"],
    P3: build.nodes.map((n) => n.id),
  };
  const stageNodes = { ingest: ["docs", "gate0", "tables", "load"], cqs: ["cqs"], wiki: ["wiki"], graph: ["nodes", "unified"],
    eval: ["wagent", "gagent", "hagent", "eval"] };

  root.STARTER_V5 = { build, paths, stageNodes };

  /* ---- v6 step 1 (GOAL-244): "flow & services" picker diagram ----
   * A compact, top-down canvas that fits half of the step-1 card: data sources → convert · load → wiki · graph → agents → deploy.
   * Rows are grey bands with a caption in the left gutter (so no edge crosses a label); 4 columns at x = 88 / 206 / 324 / 442.
   * The studio highlights  flowNodes[flow] ∪ serviceNodes[each on service] ∪ sourceNodes[data source]  with focusStyle "dim",
   * and marks the picked data source with state "current".
   *   AOLFlow.render(host, STARTER_V6.pick, { lang, highlight, states, focusStyle: "dim", card: false })
   */
  const R = [4, 92, 180, 268, 356];            // row band tops (band h = 80, node y = top + 13, node h = 54)
  const NY = (r) => R[r] + 13;
  const NB = (r) => R[r] + 67;                 // node bottom
  const C = [88, 206, 324, 442];               // column x (w = 108)
  const CX = (c, f) => C[c] + 108 * (f == null ? 0.5 : f);
  const v = (x, r1, r2, layer, id, from, to) => ({ id, from, to, pts: [[x, NB(r1)], [x, NY(r2) - 2]], layer });
  const pick = {
    id: "starter-v6-pick",
    title: ["플로우 · 서비스 구성도 — 데이터 소스 → 변환 → 위키 · 그래프 → 에이전트", "Flow & services map — data sources → convert → wiki · graph → agents"],
    w: 560, h: 440, minWidth: 420,
    lanes: R.map((y) => ({ y, h: 80, x: 8, w: 544, name: "" })),
    notes: [
      { x: 18, y: R[0] + 44, t: ["데이터 소스", "Sources"], cls: "dark" },
      { x: 18, y: R[1] + 44, t: ["변환 · 적재", "Convert"], cls: "dark" },
      { x: 18, y: R[2] + 44, t: ["위키 · 그래프", "Knowledge"], cls: "dark" },
      { x: 18, y: R[3] + 44, t: ["에이전트", "Agents"], cls: "dark" },
      { x: 18, y: R[4] + 44, t: ["배포", "Deploy"], cls: "dark" },
    ],
    nodes: [
      { id: "src_upload", x: C[0], y: NY(0), w: 108, h: 54, layer: "source", t: ["로컬 업로드", "Upload"], s: [["PDF · Office · MD · CSV", "PDF · Office · MD · CSV"]],
        tip: { d: ["내 PC의 파일을 올립니다. PDF · Office는 Markdown으로 변환됩니다.", "Upload files from your computer. PDF and Office files are converted to Markdown."] } },
      { id: "src_drive", x: C[1], y: NY(0), w: 108, h: 54, layer: "source", t: "Drive", s: [["Docs · Sheets · PDF", "Docs · Sheets · PDF"]],
        tip: { d: ["Drive 폴더 · 파일을 가져와 Markdown으로 변환합니다.", "Import Drive folders or files and convert them to Markdown."] } },
      { id: "src_gcs", x: C[2], y: NY(0), w: 108, h: 54, layer: "source", t: "GCS", s: [["gs:// · 샘플 팩", "gs:// · sample pack"]],
        tip: { d: ["버킷의 파일을 그 자리에서 읽습니다. 샘플 팩도 GCS에 있습니다.", "Reads files in place from a bucket. The sample pack also lives in GCS."] } },
      { id: "src_bq", x: C[3], y: NY(0), w: 108, h: 54, layer: "source", t: "BigQuery", s: [["테이블 그대로", "Tables in place"]],
        tip: { d: ["이미 BigQuery에 있는 테이블을 복사하지 않고 읽습니다.", "Tables already in BigQuery are read in place, not copied."] } },
      { id: "convert", x: C[0], y: NY(1), w: 226, h: 54, layer: "workflow", t: ["문서 변환 → Markdown", "Convert → Markdown"], s: [["PDF · Office · Drive · 보존율 등급", "PDF · Office · Drive · fidelity grade"]],
        tip: { d: ["Core MCP aos_core_convert_document가 변환하고 보존율을 채점합니다.", "Core MCP aos_core_convert_document converts and scores fidelity."] } },
      { id: "parse", x: C[2], y: NY(1), w: 108, h: 54, layer: "source", t: ["파싱", "Parse"], s: [["Gate 0 · 섹션", "Gate 0 · sections"]] },
      { id: "load", x: C[3], y: NY(1), w: 108, h: 54, layer: "source", t: ["적재", "Load"], s: [["프로파일 · PK · FK", "Profile · PK · FK"]] },
      { id: "vertex", x: C[0], y: NY(2), w: 108, h: 54, layer: "gemini", t: "Vertex AI", s: [["Gemini", "Gemini"]],
        tip: { d: ["변환 · 위키 컴파일 · 에이전트 추론에 쓰는 모델입니다.", "The model behind conversion, wiki compile and agent reasoning."] } },
      { id: "wiki", x: C[1], y: NY(2), w: 226, h: 54, layer: "wiki", t: ["OKF 위키", "OKF wiki"], s: [["요약 · 엔티티 · 개념 · GCS", "Summary · entity · concept · GCS"]] },
      { id: "graph", x: C[3], y: NY(2), w: 108, h: 54, layer: "semantic", t: ["그래프", "Graph"], s: [["Property Graph", "Property Graph"]] },
      { id: "coremcp", x: C[0], y: NY(3), w: 108, h: 54, layer: "mcp", t: "Core MCP", s: [["노하우 · 도구", "Know-how · tools"]],
        tip: { d: ["모든 구축 노하우와 데이터 접근을 Core MCP 도구 호출로 처리합니다.", "All build know-how and data access go through Core MCP tool calls."] } },
      { id: "wagent", x: C[1], y: NY(3), w: 108, h: 54, layer: "agent", t: "Wiki", s: [["W1 규정 안내", "W1 guidance"]] },
      { id: "hagent", x: C[2], y: NY(3), w: 108, h: 54, layer: "agent", t: "Hybrid", s: [["W3 판정 · 계산", "W3 decide"]] },
      { id: "gagent", x: C[3], y: NY(3), w: 108, h: 54, layer: "agent", t: "Graph", s: [["W2 데이터 조회", "W2 lookup"]] },
      { id: "deploy", x: C[1], y: NY(4), w: 344, h: 54, layer: "system", t: ["Cloud Run 배포", "Cloud Run deploy"], s: [["에이전트 · MCP 서버로 서비스", "Serve the agents as an app or MCP server"]] },
    ],
    edges: [
      v(CX(0), 0, 1, "workflow", "upload-convert", "src_upload", "convert"),
      v(CX(1), 0, 1, "workflow", "drive-convert", "src_drive", "convert"),
      v(CX(2), 0, 1, "source", "gcs-parse", "src_gcs", "parse"),
      v(CX(3), 0, 1, "source", "bq-load", "src_bq", "load"),
      { id: "convert-wiki", pts: [[C[1] + 74, NB(1)], [C[1] + 74, NY(2) - 2]], layer: "wiki", from: "convert", to: "wiki" },
      v(CX(2), 1, 2, "wiki", "parse-wiki", "parse", "wiki"),
      v(CX(3), 1, 2, "semantic", "load-graph", "load", "graph"),
      { id: "wiki-wagent", pts: [[CX(1), NB(2)], [CX(1), NY(3) - 2]], layer: "agent", from: "wiki", to: "wagent" },
      { id: "wiki-hagent", pts: [[CX(2, 0.3), NB(2)], [CX(2, 0.3), NY(3) - 2]], layer: "agent", from: "wiki", to: "hagent" },
      { id: "graph-hagent", pts: [[CX(3, 0.15), NB(2)], [CX(3, 0.15), NB(2) + 17], [CX(2, 0.75), NB(2) + 17], [CX(2, 0.75), NY(3) - 2]], layer: "agent", from: "graph", to: "hagent" },
      { id: "graph-gagent", pts: [[CX(3, 0.6), NB(2)], [CX(3, 0.6), NY(3) - 2]], layer: "agent", from: "graph", to: "gagent" },
      v(CX(1), 3, 4, "system", "wagent-deploy", "wagent", "deploy"),
      v(CX(2), 3, 4, "system", "hagent-deploy", "hagent", "deploy"),
      v(CX(3), 3, 4, "system", "gagent-deploy", "gagent", "deploy"),
    ],
    legend: [
      { kind: "flow", color: "wiki", t: ["선택한 경로 · 색 = 도착 레이어", "Selected path · colour = target layer"] },
      { kind: "focus", t: ["선택한 데이터 소스", "Picked data source"] },
    ],
  };
  const docs = ["src_upload", "src_gcs", "parse", "wiki", "wagent", "vertex", "coremcp"];
  const tables = ["src_upload", "src_gcs", "src_bq", "load", "graph", "gagent", "vertex", "coremcp"];
  const flowNodes = { A: docs, B: tables, C: docs.concat(tables, ["hagent"]), D: docs.concat(["convert"]) };
  const serviceNodes = { gcs: ["src_gcs"], vertex_ai: ["vertex"], core_mcp: ["coremcp"], drive: ["src_drive", "convert"],
    bigquery: ["src_bq", "load"], bq_graph: ["graph"], cloud_run: ["deploy"] };
  const sourceNodes = { upload: ["src_upload", "convert"], drive: ["src_drive", "convert"], gcs: ["src_gcs"], sample: ["src_gcs"], bigquery: ["src_bq", "load"] };
  root.STARTER_V6 = { pick, flowNodes, serviceNodes, sourceNodes };
})(typeof window !== "undefined" ? window : this);
