/* nb_stage_flows.js — Colab notebook stage diagrams (Stage 0–5) in the Studio v6 grammar (GOAL-223).
 * Rendered to notebooks/assets/stage*_flow_{ko,en}.png by render_stage_flows.html (gbrowser screenshot, 2x).
 * Uses ../../src/web/static/aolflow.js. One lane per stage, four step cards, flow edges coloured by layer.
 */
(function (root) {
  "use strict";
  const X = [20, 330, 640, 950], CW = 270, CY = 54, CH = 94;

  function stage(id, pill, name, desc, steps) {
    const nodes = steps.map((st, i) => ({ id: `${id}-${i}`, x: X[i], y: CY, w: CW, h: CH, layer: st.layer, t: st.t, s: st.s }));
    const edges = steps.slice(1).map((st, i) => ({ id: `${id}-e${i}`, from: `${id}-${i}`, to: `${id}-${i + 1}`, layer: st.layer }));
    return { id, title: name, w: 1240, h: 172, minWidth: 900, lanes: [{ y: 8, h: 156, pill, name, desc }], nodes, edges };
  }

  const S = {};
  S.stage0_overview_flow = stage("s0", "Stage 0", ["전체 흐름", "Overall flow"], ["준비 → 파싱 → 그래프 → 에이전트 → 검증, 5단계 8페이즈", "Prepare → parse → graph → agent → verify · 5 stages, 8 phases"], [
    { layer: "source", t: ["1 · 준비 · 분석", "1 · Prepare · analyze"], s: [["문서 2 · CSV 6 · CQ", "2 docs · 6 CSVs · CQs"], ["BigQuery 테이블 프로파일링", "Profile the BigQuery tables"], ["Golden CQ · 경계 케이스", "Golden CQs · boundary cases"]] },
    { layer: "wiki", t: ["2 · 파싱 · 통합", "2 · Parse · integrate"], s: [["조항 앵커 · 3-Layer 위키", "Clause anchors · 3-layer wiki"], ["룰 ↔ 요금제 바인딩", "Rule ↔ plan binding"], ["엔티티 = 노드 · 개념 = 엣지", "Entity = node · concept = edge"]] },
    { layer: "semantic", t: ["3 · 그래프 구축", "3 · Build the graph"], s: [["Property Graph DDL", "Property Graph DDL"], ["BigQuery · Spanner 동시 지원", "BigQuery and Spanner"], ["멀티홉 GQL · NL2GQL", "Multi-hop GQL · NL2GQL"]] },
    { layer: "agent", t: ["4–5 · 에이전트 · 검증", "4–5 · Agent · verify"], s: [["MCP 도구 3종 + 2-Pass 에이전트", "3 MCP tools + 2-pass agent"], ["근거 판정 GROUNDED", "Grounded verdicts"], ["리니지 · Golden CQ 게이트", "Lineage · Golden CQ gate"]] },
  ]);
  S.stage1_prepare_analyze_flow = stage("s1", "Stage 1", ["준비 · 분석", "Prepare · analyze"], ["입력 자산을 확인하고 답해야 할 질문(CQ)을 먼저 정합니다", "Check the input assets and fix the questions (CQs) first"], [
    { layer: "source", t: ["입력 자산", "Input assets"], s: [["정책 가이드 2종 (Markdown)", "2 policy guides (Markdown)"], ["CSV 테이블 6종", "6 CSV tables"], ["용어집 · CQ 파일", "Glossary · CQ files"]] },
    { layer: "source", t: ["범위 · 스키마 설계", "Scope · schema design"], s: [["BigQuery DW 테이블", "BigQuery DW tables"], ["키 · 관계 정의", "Keys · relations"], ["Golden CQ 5 · 경계 10", "5 golden CQs · 10 boundary"]] },
    { layer: "mcp", t: ["프로파일링 · 거버넌스", "Profiling · governance"], s: [["행 수 · 역할별 테이블", "Row counts · table roles"], ["비식별화 확인", "De-identification check"], ["검증 SQL 정답 감사", "Audit verification SQL"]] },
    { layer: "eval", t: ["평가 기준 확정", "Evaluation baseline"], s: [["CQ마다 정답 · 근거", "Answer + evidence per CQ"], ["마지막 단계의 채점 기준", "Scoring set for the last stage"], ["설계 범위의 출발점", "Starting point of the design"]] },
  ]);
  S.stage2_parse_integrate_flow = stage("s2", "Stage 2", ["파싱 · 통합", "Parse · integrate"], ["문서를 조항 단위로 나누고 위키 · 룰로 통합합니다", "Split documents into clauses and integrate them into a wiki and rules"], [
    { layer: "source", t: ["원본 문서", "Source documents"], s: [["정책 가이드 2종", "2 policy guides"], ["조항 · 표 · 예외 문장", "Clauses · tables · exceptions"], ["런타임에는 직접 읽지 않음", "Never read directly at runtime"]] },
    { layer: "source", t: ["구조 파싱 · 앵커", "Parsing · anchors"], s: [["DOC_CHUNK 단위 분할", "Split into DOC_CHUNKs"], ["SHA-256 문단 앵커", "SHA-256 paragraph anchors"], ["원문 보존 검사", "Fidelity check"]] },
    { layer: "wiki", t: ["3-Layer 위키", "3-layer wiki"], s: [["요약 · 엔티티 · 룰 페이지", "Summary · entity · rule pages"], ["정책값은 한 곳에만", "Each policy value in one place"], ["모든 레이어가 인용", "Cited by every layer"]] },
    { layer: "semantic", t: ["시맨틱 브릿지 · 룰 바인딩", "Semantic bridge · rules"], s: [["엔티티 = 노드 · 개념 = 엣지", "Entity = node · concept = edge"], ["룰 4종 ↔ 요금제 6종", "4 rules ↔ 6 plans"], ["domain_rules · rule_plan_edges", "domain_rules · rule_plan_edges"]] },
  ]);
  S.stage3_property_graph_flow = stage("s3", "Stage 3", ["그래프 구축", "Build the graph"], ["테이블을 복사하지 않고 Property Graph로 투영해 GQL로 조회합니다", "Project the tables as a Property Graph without copying, then query with GQL"], [
    { layer: "semantic", t: ["메타모델 설계", "Metamodel"], s: [["노드 6종 × 엣지 4종", "6 node × 4 edge types"], ["계약 · 단말 · 요금제 · 지원금", "Contract · device · plan · subsidy"], ["룰 · 문서 조각 노드", "Rule · chunk nodes"]] },
    { layer: "semantic", t: ["그래프 DDL · 무결성", "Graph DDL · integrity"], s: [["BigQuery Property Graph", "BigQuery Property Graph"], ["Spanner Graph 호환 DDL", "Spanner Graph DDL"], ["노드 키 중복 0 검증", "Zero duplicate node keys"]] },
    { layer: "mcp", t: ["바인딩 변수 GQL", "Parameterised GQL"], s: [["1~2홉 경로 탐색", "1–2 hop path queries"], ["위약금 산식 단일 쿼리", "Penalty formula in one query"], ["Job ID · 실행 시간 기록", "Job id · latency recorded"]] },
    { layer: "agent", t: ["NL2GQL · 스키마 가드", "NL2GQL · schema guard"], s: [["자연어 → GQL 자동 생성", "Natural language → GQL"], ["없는 속성 질문 차단", "Blocks unknown properties"], ["Stage 4 에이전트로 인계", "Handed to the Stage 4 agent"]] },
  ]);
  S.stage4_agent_mcp_flow = stage("s4", "Stage 4", ["에이전트 · MCP", "Agent · MCP"], ["질문을 계획하고 결정론 도구로 계산해 근거와 함께 답합니다", "Plan the question, calculate with deterministic tools and answer with evidence"], [
    { layer: "source", t: ["질문", "Question"], s: [["고객 · 단말 · 요금제 조건", "Customer · device · plan"], ["CQ · 자유 질문", "CQs or free questions"], ["KO · EN", "KO · EN"]] },
    { layer: "agent", t: ["2-Pass 에이전트", "2-pass agent"], s: [["1차: 슬롯 · 도구 계획", "Pass 1: slots · tool plan"], ["2차: 결과로 답변 작성", "Pass 2: answer from results"], ["Gemini 4 Argon", "Gemini 4 Argon"]] },
    { layer: "mcp", t: ["도메인 MCP 도구 3종", "3 domain MCP tools"], s: [["고객 · 원장 조회", "Customer · ledger lookup"], ["위약금 · 면제 계산", "Penalty · exemption math"], ["그래프 + 위키 조회", "Graph + wiki query"]] },
    { layer: "eval", t: ["근거 있는 답변", "Grounded answer"], s: [["GROUNDED · INSUFFICIENT", "GROUNDED · INSUFFICIENT"], ["NOT_FOUND 정직 응답", "Honest NOT_FOUND"], ["SQL · 위키 근거 표시", "Shows SQL · wiki evidence"]] },
  ]);
  S.stage5_lineage_eval_flow = stage("s5", "Stage 5", ["리니지 · 평가", "Lineage · evaluation"], ["원천에서 답변까지 추적하고 같은 CQ로 채점해 배포 게이트를 통과합니다", "Trace from source to answer, score on the same CQs and pass the release gate"], [
    { layer: "source", t: ["원천 → 조각", "Source → chunks"], s: [["문서 · 테이블 출처", "Document · table origin"], ["조항 앵커 연결", "Clause anchors"], ["데이터 리니지 시작점", "Start of the lineage"]] },
    { layer: "semantic", t: ["룰 → 계약 → CQ", "Rule → contract → CQ"], s: [["룰이 쓰인 계약 추적", "Which contracts a rule hits"], ["CQ별 근거 경로", "Evidence path per CQ"], ["6-Layer 리니지 DAG", "6-layer lineage DAG"]] },
    { layer: "eval", t: ["Golden CQ · 경계 평가", "Golden CQs · boundary"], s: [["Golden CQ 5건", "5 golden CQs"], ["경계 케이스 50회 반복", "50 boundary trials"], ["일관성 · 의도 안정성", "Consistency · intent stability"]] },
    { layer: "agent", t: ["배포 게이트", "Release gate"], s: [["Gate 1 ~ Gate 5 점검", "Gates 1–5 checklist"], ["통과 시 Cloud Run 배포", "Deploy to Cloud Run on pass"], ["실패 항목 재작업", "Rework failed items"]] },
  ]);

  root.NB_STAGE_FLOWS = S;
})(typeof window !== "undefined" ? window : this);
