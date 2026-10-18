/* flows.js — Starter diagram specs for aolflow.js (GOAL-223).
 *
 * `dataflow` is a 1:1 port of the studio v6 data flow (enablement/20261006_v6_enablement_overview.html):
 * same 1240×532 canvas, columns, P1/P3/P2 lanes, card coordinates, curves, W1·W2·W3 badges and G2-W gates —
 * re-labelled for the starter data pack (Starter Telecom, synthetic). `resources` shows where step 4 loads data
 * and which agent reads what in step 5. `recipes` = highlight sets for the step-1 choice.
 *
 * Usage:  const r = STARTER_FLOWS.recipes[key];
 *         AOLFlow.render(host, STARTER_FLOWS.dataflow, { lang, highlight: r.all ? [] : r.nodes,
 *                        highlightEdges: r.all ? [] : r.edges, focusStyle: "dim" });
 *         AOLFlow.render(host2, STARTER_FLOWS.resources, { lang, highlight: r.all ? [] : r.res, focusStyle: "dim" });
 */
(function (root) {
  "use strict";

  const P1 = ["raw", "parsed", "wiki", "w1", "guide"];
  const P1E = ["raw-parsed", "parsed-wiki", "wiki-w1", "w1-guide", "arc"];
  const P2 = ["ledger", "twiki", "lgraph", "w2", "mcp", "ledgerag"];
  const P2E = ["ledger-lgraph", "ledger-twiki", "lgraph-w2", "w2-mcp", "mcp-ledgerag"];
  const ALL = ["raw", "parsed", "wiki", "w1", "guide", "unified", "w3", "full", "ledger", "twiki", "lgraph", "w2", "ledgerag", "mcp"];

  const dataflow = {
    id: "starter-dataflow",
    title: ["데이터 3경로 × 워크플로우 3추출 시점", "Three data paths × three workflow extraction points"],
    w: 1240, h: 532, minWidth: 980,
    cols: [
      { x: 146, layer: "source", t: ["원천", "Source"], s: ["문서 · 테이블", "Docs · tables"] },
      { x: 384, layer: "wiki", t: ["온톨로지 위키", "Ontology wiki"], s: ["허브 · ID 정본", "Hub · canonical IDs"] },
      { x: 584, layer: "semantic", t: ["시맨틱 그래프", "Semantic graph"], s: ["Property Graph", "Property Graph"] },
      { x: 792, layer: "workflow", t: ["워크플로우", "Workflow"], s: ["룰 · 단계 · CQ", "Rules · steps · CQs"] },
      { x: 958, layer: "mcp", t: "MCP", s: ["결정론 도구", "Deterministic tools"] },
      { x: 1140, layer: "agent", t: ["에이전트", "Agents"], s: ["3종", "Three kinds"] },
    ],
    lanes: [
      { y: 52, h: 152, pill: "P1", name: ["문서 경로", "Document path"], desc: ["원본 → 파싱 → 위키 · 위키가 되면 바로 에이전트로", "Raw → parsed → wiki · agents use it once it is wiki"] },
      { y: 212, h: 152, pill: "P3", name: ["통합 경로", "Unified path"], desc: ["위키 + 테이블을 묶어 통합 그래프로", "Wiki + tables bound into one graph"] },
      { y: 372, h: 152, pill: "P2", name: ["정형 경로", "Structured path"], desc: ["원래 BigQuery에 있음 · 그래프 설계가 되어야 에이전트로", "Already in BigQuery · reaches agents once the graph is designed"] },
    ],
    bounds: [{ x: 290, y1: 88, y2: 198, l: ["빌드 타임 전용", "Build time only"], r: ["런타임은 위키 · 그래프만", "Runtime: wiki · graph only"] }],
    ghosts: [{ x: 20, y: 268, w: 252, h: 64, t: ["자체 원천 없음", "No source of its own"], s: ["P1 위키 + P2 테이블을 묶는다", "Binds the P1 wiki + P2 tables"] }],
    nodes: [
      // P1
      { id: "raw", nb: "4", x: 20, y: 108, w: 114, layer: "source", t: ["원본", "Raw"], s: [["정책 가이드 2종", "2 policy guides"], ["Markdown", "Markdown"]],
        tip: { d: ["요금제 · 지원금 정책 가이드와 복지 면제 가이드. 위키를 만들 때만 읽습니다.", "The plan/subsidy policy guide and the welfare exemption guide. Read only when the wiki is built."] } },
      { id: "parsed", nb: "4", x: 158, y: 108, w: 114, layer: "source", t: ["파싱", "Parsing"], s: [["조항 앵커", "Clause anchors"], ["Gate 0 통과본", "Gate 0 passed"]],
        tip: { d: ["무손실 변환 + 조항 앵커. Core MCP Gate 0(원문 보존율)을 통과한 문서만 위키로 갑니다.", "Lossless conversion + clause anchors. Only documents that pass Core MCP Gate 0 (fidelity) go on to the wiki."] } },
      { id: "wiki", nb: "4", x: 308, y: 108, w: 152, layer: "wiki", t: ["온톨로지 위키", "Ontology wiki"], s: [["요약 · 엔티티 · 개념", "3-layer pages"], ["정책값 frontmatter", "Policy frontmatter"]],
        tip: { d: ["모든 레이어가 인용하는 허브. 정책값(예: 180일 · 45,000원 기준선)은 frontmatter 한 곳에만 씁니다.", "The hub every layer cites. Policy values (e.g. 180 days · the 45,000 KRW baseline) are written in frontmatter only."] } },
      { id: "w1", nb: "5", x: 716, y: 108, w: 152, layer: "workflow", badge: "W1", t: ["위키 시점", "Wiki point"], s: [["문서 기반", "From documents"], ["규정 안내형", "Policy guidance"]],
        tip: { d: ["P1 완료 직후 열리는 추출 시점. 규정을 안내하는 워크플로우를 위키에서 뽑습니다.", "Opens right after P1. Guidance workflows are extracted from the wiki."] } },
      { id: "guide", nb: "5", x: 1052, y: 108, w: 176, layer: "agent", t: "Wiki Agent", s: [["위키만 읽고 답변", "Answers from the wiki"], ["근거 페이지 인용", "Cites its source pages"]],
        tip: { d: ["GCS의 위키 페이지를 골라 읽고 근거를 인용해 규정 질문에 답합니다.", "Picks wiki pages from GCS, reads them and answers policy questions with citations."] } },
      // P3
      { id: "unified", nb: "4", x: 508, y: 260, w: 152, h: 80, layer: "semantic", t: ["통합 그래프", "Unified graph"], s: [["규칙 · 파라미터 노드", "Rule · parameter nodes"], ["개념 브릿지", "Concept bridges"], ["워크플로우 서브그래프", "Workflow subgraph"]],
        tip: { d: ["위키 개념 · 정책값 + 테이블 노드를 하나의 BigQuery Property Graph로 묶습니다.", "Binds wiki concepts · policy values and table nodes into one BigQuery Property Graph."] } },
      { id: "w3", nb: "5", x: 716, y: 268, w: 152, layer: "workflow", badge: "W3", t: ["통합 그래프 시점", "Unified point"], s: [["문서 + 테이블", "Docs + tables"], ["판정 · 계산형", "Decide & calculate"]],
        tip: { d: ["G2-W 반영 후 열리는 추출 시점. 위약금 판정 · 계산처럼 규정과 값이 함께 필요한 업무입니다.", "Opens after G2-W. Tasks that need rules and values together, such as penalty decisions and calculations."] } },
      { id: "full", nb: "5", x: 1052, y: 268, w: 176, layer: "agent", t: "Workflow Agent", s: [["판정 · 위약금 계산", "Decisions · penalty math"], ["MCP 도구 호출", "Calls MCP tools"]],
        tip: { d: ["워크플로우 단계를 따라 그래프를 조회하고 MCP 도구로 계산해 판정까지 답합니다.", "Follows the workflow steps, queries the graph and calculates with MCP tools to reach a decision."] } },
      // P2
      { id: "ledger", nb: "4", x: 20, y: 428, w: 252, layer: "source", t: ["BigQuery 테이블 6종", "6 BigQuery tables"], s: [["단말 · 요금제 · 지원금 · 계약 · 룰", "Devices · plans · subsidies · contracts · rules"], ["원래 정형 · 파싱 없음", "Structured already · no parsing"]],
        tip: { d: ["단말 출고가 · 요금제 · 지원금 정책 · 고객 계약 · 도메인 룰 · 룰↔요금제 연결 테이블.", "Device prices · plans · subsidy policies · customer contracts · domain rules · rule↔plan links."] } },
      { id: "twiki", nb: "4", x: 318, y: 486, w: 132, h: 26, kind: "pill", layer: "wiki", t: ["테이블 의미만 위키로", "Table semantics"],
        tip: { d: ["테이블의 의미(스키마 · 코드)만 위키 ID로 만들고 값은 테이블에 그대로 둡니다.", "Only table meaning (schema · codes) becomes wiki IDs; values stay in the tables."] } },
      { id: "lgraph", nb: "4", x: 508, y: 428, w: 152, layer: "semantic", t: ["테이블 서브그래프", "Table subgraph"], s: [["노드 · FK 엣지", "Nodes · FK edges"], ["그래프 설계 완료", "Graph designed"]],
        tip: { d: ["테이블 행이 노드, 외래키가 엣지가 됩니다. 그래프 설계가 끝나야 에이전트가 테이블을 조회합니다.", "Rows become nodes and foreign keys become edges. Agents query the tables only after the graph is designed."] } },
      { id: "w2", nb: "5", x: 716, y: 428, w: 152, layer: "workflow", badge: "W2", t: ["원장 그래프 시점", "Ledger point"], s: [["테이블 기반", "From tables"], ["조회 · 대사형", "Lookup & reconcile"]],
        tip: { d: ["P2 완료 직후 열리는 추출 시점. 고객 계약 · 지원금 원장을 조회하는 워크플로우입니다.", "Opens right after P2. Workflows that look up customer contracts and subsidy ledgers."] } },
      { id: "ledgerag", nb: "5", x: 1052, y: 428, w: 176, layer: "agent", t: "Graph Agent", s: [["BigQuery Graph 조회", "BigQuery Graph queries"], ["MCP 원장 조회", "MCP ledger lookups"]],
        tip: { d: ["질문을 GQL/SQL로 바꿔 그래프와 테이블을 조회하고 숫자까지 답합니다.", "Turns questions into GQL/SQL over the graph and tables and answers down to the number."] } },
      // MCP hub (P3 + P2)
      { id: "mcp", nb: "5", x: 904, y: 268, w: 108, h: 224, kind: "hub", layer: "mcp", t: ["MCP 서버", "MCP server"], s: [["결정론 도구", "Deterministic"]],
        big: ["3종", "3 tools"], bigS: ["룰 1 : 도구 1", "1 rule : 1 tool"],
        tip: { d: ["고객 조회 · 위약금 계산 · 그래프+위키 조회 도구 3종. 룰 하나가 도구 하나에 대응합니다.", "Three tools: customer lookup · penalty calculation · graph + wiki query. One rule maps to one tool."] } },
    ],
    edges: [
      { id: "raw-parsed", from: "raw", to: "parsed", layer: "source", d: "M134 140 L156 140" },
      { id: "parsed-wiki", from: "parsed", to: "wiki", layer: "wiki", d: "M272 140 L306 140" },
      { id: "wiki-w1", from: "wiki", to: "w1", layer: "workflow", d: "M460 140 L699 140" },
      { id: "w1-guide", from: "w1", to: "guide", layer: "agent", d: "M868 140 L1050 140" },
      { id: "arc", from: "wiki", to: "guide", layer: "agent", d: "M436 108 C548 62 980 62 1104 106",
        label: { t: ["위키가 되면 바로 → Wiki Agent", "Wiki ready → Wiki Agent"], x: 765, y: 73 },
        tip: { t: ["위키가 되면 바로 에이전트로", "Agents use it once it is wiki"], d: ["Wiki Agent는 그래프 없이 위키만으로 규정 질문에 답합니다.", "The Wiki Agent answers policy questions from the wiki alone, with no graph."] } },
      { id: "ledger-lgraph", from: "ledger", to: "lgraph", layer: "semantic", d: "M272 460 L506 460" },
      { id: "ledger-twiki", from: "ledger", to: "twiki", layer: "wiki", kind: "bridge", d: "M384 460 L384 484" },
      { id: "lgraph-w2", from: "lgraph", to: "w2", layer: "workflow", d: "M660 460 L699 460" },
      { id: "w2-mcp", from: "w2", to: "mcp", layer: "mcp", d: "M868 460 L902 460" },
      { id: "mcp-ledgerag", from: "mcp", to: "ledgerag", layer: "agent", d: "M1012 460 L1050 460" },
      { id: "wiki-unified", from: "wiki", to: "unified", layer: "semantic", d: "M446 172 C446 238 466 286 506 286",
        label: { t: ["개념 · 정책값", "Concepts · policy values"], s: ["→ 규칙 · 파라미터 노드", "→ rule · parameter nodes"], x: 436, y: 250, kind: "plain", anchor: "end" } },
      { id: "lgraph-unified", from: "lgraph", to: "unified", layer: "semantic", d: "M584 428 L584 342",
        label: { t: ["테이블 노드", "Table nodes"], x: 592, y: 392, kind: "plain-left" } },
      { id: "unified-w3", from: "unified", to: "w3", layer: "workflow", d: "M660 300 L699 300" },
      { id: "w3-mcp", from: "w3", to: "mcp", layer: "mcp", d: "M868 300 L902 300" },
      { id: "mcp-full", from: "mcp", to: "full", layer: "agent", d: "M1012 300 L1050 300" },
      { id: "g2w-up", from: "w1", to: "unified", layer: "workflow", kind: "gate", d: "M792 172 C792 216 640 210 640 258",
        label: { t: ["피드백 게이트", "feedback gate"], strong: "G2-W", x: 716, y: 213, kind: "gate" },
        tip: { t: ["G2-W 피드백 게이트", "G2-W feedback gate"], d: ["W1 초안의 요구(파라미터 → frontmatter, 슬롯 → 컬럼)를 그래프 설계로 되돌립니다.", "W1 draft requirements (parameters → frontmatter, slots → columns) flow back into graph design."] } },
      { id: "g2w-dn", from: "w2", to: "unified", layer: "workflow", kind: "gate", d: "M792 428 C792 384 640 392 640 342",
        label: { t: ["초안 → 그래프 재설계", "Drafts → redesign"], x: 716, y: 387, kind: "gate" },
        tip: { t: ["G2-W 피드백 게이트", "G2-W feedback gate"], d: ["W2 초안의 요구도 같은 게이트로 들어가 통합 그래프를 다시 설계합니다. 반영이 끝나야 W3가 열립니다.", "W2 draft requirements enter the same gate and redesign the unified graph. W3 opens only after they are applied."] } },
    ],
    legend: [
      { kind: "flow", color: "semantic", t: ["데이터 흐름 · 색 = 도착 레이어", "Data flow · colour = target layer"] },
      { kind: "gate", t: ["G2-W 피드백 · 역방향", "G2-W feedback · backward"] },
      { kind: "badge", badge: "W", t: ["워크플로우 추출 시점", "Workflow extraction point"] },
    ],
    chips: [
      { n: "A", key: "A", t: ["문서 중심 (P1 + W1)", "Document-first (P1 + W1)"], nodes: P1 },
      { n: "B", key: "B", t: ["테이블 중심 (P2 + W2)", "Table-first (P2 + W2)"], nodes: P2 },
      { n: "C", key: "C", t: ["통합 (P1·P2·P3 × W1~W3)", "Unified (P1·P2·P3 × W1–W3)"], nodes: ALL },
    ],
  };

  // Step 4/5 — where each recipe loads data and which agent reads what
  const resources = {
    id: "starter-resources",
    title: ["적재 위치와 에이전트 — 입력한 GCP 리소스 기준", "Where data is loaded and who reads it — on the GCP resources you enter"],
    w: 1240, h: 340, minWidth: 980,
    cols: [
      { x: 105, layer: "source", t: ["데이터 팩", "Data pack"], s: ["KO · EN 2벌", "KO · EN sets"] },
      { x: 350, layer: "system", t: ["스타터 서버", "Starter server"], s: ["Cloud Run", "Cloud Run"] },
      { x: 690, layer: "semantic", t: ["내 GCP 리소스", "Your GCP resources"], s: ["단계 4에서 적재", "Loaded in step 4"] },
      { x: 1075, layer: "agent", t: ["에이전트", "Agents"], s: ["단계 5에서 실행", "Run in step 5"] },
    ],
    groups: [{ x: 500, y: 52, w: 380, h: 280, t: ["입력한 프로젝트", "Project you entered"], s: ["프로젝트 · 데이터셋 · 버킷 · 그래프 이름", "project · dataset · bucket · graph name"] }],
    nodes: [
      { id: "pack", nb: "4", x: 20, y: 140, w: 170, h: 80, layer: "source", t: ["데이터 팩", "Data pack"], s: [["문서 2 · 위키 페이지", "2 docs · wiki pages"], ["테이블 6 · CQ", "6 tables · CQs"], ["KO · EN 같은 ID · 숫자", "KO · EN, same ids"]] },
      { id: "app", nb: "3", x: 240, y: 132, w: 220, h: 96, kind: "hub", layer: "system", t: ["스타터 서버", "Starter server"], s: [["입력한 리소스로 실행", "Runs on the resources you enter"], ["쓰기 허용 프로젝트만", "Writes only to allowed projects"]] },
      { id: "gcs", nb: "4", x: 520, y: 96, w: 340, h: 60, layer: "wiki", t: ["GCS 버킷", "GCS bucket"], s: [["starter/<lang>/ · 원본 문서 + 위키 페이지", "starter/<lang>/ · source docs + wiki pages"]], tip: { d: ["P1: 문서와 OKF 위키 페이지를 올립니다. Wiki Agent가 여기서 읽습니다.", "P1: uploads the documents and OKF wiki pages. The Wiki Agent reads them here."] } },
      { id: "bq", nb: "4", x: 520, y: 172, w: 340, h: 60, layer: "source", t: ["BigQuery 데이터셋", "BigQuery dataset"], s: [["원천 6 + 원장 엣지 3 · 컬럼 설명 · 멱등 적재", "6 source + 3 ledger-edge tables · descriptions"]], tip: { d: ["P2: 테이블을 같은 스키마로 다시 적재합니다(멱등).", "P2: reloads the tables with the same schema (idempotent)."] } },
      { id: "graph", nb: "4", x: 520, y: 248, w: 340, h: 60, layer: "semantic", t: "BigQuery Property Graph", s: [["+ 조항 · 위키 개념 · 정책값 · 워크플로우 노드", "+ clause · concept · policy · step nodes"]], tip: { d: ["P3: CREATE OR REPLACE PROPERTY GRAPH로 통합 그래프를 만듭니다(Enterprise 예약 필요).", "P3: builds the unified graph with CREATE OR REPLACE PROPERTY GRAPH (needs an Enterprise reservation)."] } },
      { id: "gemini", nb: "3", x: 932, y: 44, w: 290, h: 52, kind: "pill", layer: "gemini", t: ["Gemini 4 Argon · Vertex AI", "Gemini 4 Argon · Vertex AI"] },
      { id: "ag_wiki", nb: "5", x: 932, y: 112, w: 290, h: 56, layer: "agent", t: "Wiki Agent", s: [["위키 페이지 근거로 답변", "Answers from wiki pages"]] },
      { id: "ag_graph", nb: "5", x: 932, y: 184, w: 290, h: 56, layer: "agent", t: "Graph Agent", s: [["그래프 · 테이블 조회 + MCP", "Graph · table queries + MCP"]] },
      { id: "ag_wf", nb: "5", x: 932, y: 256, w: 290, h: 56, layer: "agent", t: "Workflow Agent", s: [["단계별 판정 · 계산 (W1~W3)", "Step-by-step decisions (W1–W3)"]] },
    ],
    edges: [
      { id: "pack-app", from: "pack", to: "app", layer: "system" },
      { id: "app-gcs", pts: ["app.r@0.3", [490, 160.8], [490, 126], "gcs.l+-2,0"], layer: "wiki", label: { t: ["P1 업로드", "P1 upload"], x: 452, y: 112, kind: "plain" } },
      { id: "app-bq", pts: ["app.r@0.5", "bq.l@0.13+-2,0"], from: "app", to: "bq", layer: "source", label: { t: ["P2 적재", "P2 load"], x: 490, y: 172, kind: "plain" } },
      { id: "app-graph", pts: ["app.r@0.7", [490, 199.2], [490, 278], "graph.l+-2,0"], layer: "semantic", label: { t: ["P3 그래프 DDL", "P3 graph DDL"], x: 448, y: 300, kind: "plain" } },
      { id: "gcs-wiki", pts: ["gcs.r", [896, 126], [896, 140], "ag_wiki.l+-2,0"], layer: "agent" },
      { id: "graph-agent", pts: ["graph.r@0.25", [896, 263], [896, 212], "ag_graph.l+-2,0"], layer: "agent" },
      { id: "graph-wf", pts: ["graph.r@0.6", "ag_wf.l+-2,0"], layer: "agent" },
      { id: "gem-agents", pts: ["gemini.b", "ag_wiki.t+0,-2"], layer: "gemini", kind: "bridge" },
    ],
    legend: [
      { kind: "flow", color: "semantic", t: ["적재 · 조회 흐름", "Load · query flow"] },
      { kind: "bridge", color: "gemini", t: ["모든 에이전트가 Gemini 사용", "Every agent uses Gemini"] },
    ],
  };

  const recipes = {
    A: { key: "A", paths: ["P1"], points: ["W1"], nodes: P1, edges: P1E, res: ["pack", "app", "gcs", "gemini", "ag_wiki"],
      t: ["Flow A · 문서 중심", "Flow A · document-first"], s: ["P1 + W1 — 규정 문서만으로 시작", "P1 + W1 — start from policy documents"] },
    B: { key: "B", paths: ["P2"], points: ["W2"], nodes: P2, edges: P2E, res: ["pack", "app", "bq", "graph", "gemini", "ag_graph"],
      t: ["Flow B · 테이블 중심", "Flow B · table-first"], s: ["P2 + W2 — BigQuery 원장으로 시작", "P2 + W2 — start from BigQuery ledgers"] },
    C: { key: "C", all: true, paths: ["P1", "P2", "P3"], points: ["W1", "W2", "W3"], nodes: dataflow.nodes.map((n) => n.id), edges: dataflow.edges.map((e) => e.id),
      res: resources.nodes.map((n) => n.id),
      t: ["Flow C · 통합", "Flow C · unified"], s: ["P1 + P2 + P3 × W1 + W2 + W3 + G2-W", "P1 + P2 + P3 × W1 + W2 + W3 + G2-W"] },
  };

  root.STARTER_FLOWS = { dataflow, resources, recipes };
})(typeof window !== "undefined" ? window : this);
