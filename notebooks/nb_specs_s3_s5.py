# -*- coding: utf-8 -*-
"""Cell builders for Stage 3, Stage 4, and Stage 5 notebooks (KO/EN)."""
from nb_specs_s0_s2 import FQ, GRAPH, code, md


def build_stage3(lang="ko"):
    ko = lang == "ko"
    return [
        md(f"""# Stage 3. {"물리 프로퍼티 그래프 (BigQuery Graph / Spanner Graph) & ISO GQL" if ko else "Physical Property Graph (BigQuery Graph / Spanner Graph) & ISO GQL"}
## {"Step 3.1 BigQuery/Spanner Graph DDL 프로비저닝 · Step 3.2 ISO GQL 다중 홉 패턴 및 Gemini NL-to-GQL" if ko else "Step 3.1 BigQuery/Spanner Graph DDL Provisioning · Step 3.2 ISO GQL Multi-Hop Patterns & Gemini NL-to-GQL"}

![Step 2 Property Graph Flow](attachment:step2_property_graph_flow.png)"""),
        code(f"""%load_ext bigframes
import pandas as pd
import nb_helpers as H
H.setup("{lang}")"""),
        md(f"### 1. {'BigQuery Graph / Spanner Graph DDL 비교 및 라이브 스키마(`INFORMATION_SCHEMA.PROPERTY_GRAPHS`)' if ko else 'BigQuery Graph / Spanner Graph DDL & Live Schema (`INFORMATION_SCHEMA.PROPERTY_GRAPHS`)'}"),
        code("""H.show_md_file(H.ROOT / "data/output/create_property_graph.sql", max_lines=38)
H.show_md_file(H.ROOT / "data/output/create_spanner_graph.sql", max_lines=38)
node_labels, edge_labels, meta = H.graph_metadata()
H.md(f"BigQuery job `{meta['job_id']}` ({meta['elapsed_ms']} ms)")
H.show(pd.DataFrame(node_labels))
H.show(pd.DataFrame(edge_labels))"""),
        md(f"### 2. {'노드 · 엣지 레이블 분포(`%%bqsql`) 및 전체 프로퍼티 그래프 토폴로지 시각화' if ko else 'Node & Edge Label Distribution (`%%bqsql`) and Full Property Graph Topology'}"),
        code(f"""%%bqsql df_gnodes
GRAPH `{GRAPH}`
MATCH (n)
RETURN LABELS(n)[OFFSET(0)] AS label, COUNT(*) AS nodes
GROUP BY label
ORDER BY nodes DESC"""),
        code(f"""%%bqsql df_gedges
GRAPH `{GRAPH}`
MATCH ()-[e]->()
RETURN LABELS(e)[OFFSET(0)] AS label, COUNT(*) AS edges
GROUP BY label
ORDER BY edges DESC"""),
        code(f"""%%bqsql df_all_paths
GRAPH `{GRAPH}`
MATCH p = (a)-[e]->(b)
RETURN TO_JSON(p) AS path"""),
        code("""H.show(df_gnodes)
H.show(df_gedges)
H.bar(df_gnodes, "label", "nodes", H.t("STARTER_ONTOLOGY_GRAPH 노드 레이블별 개수", "Node Count by Label"), color=[H.LABEL_COLORS.get(x, "#1A73E8") for x in H.pdf(df_gnodes)["label"]])
H.bar(df_gedges, "label", "edges", H.t("STARTER_ONTOLOGY_GRAPH 엣지 레이블별 개수", "Edge Count by Label"), color="#0d9488")
nodes, edges = H.paths_to_graph(H.pdf(df_all_paths)["path"])
H.draw_graph(nodes, edges, H.t("STARTER_ONTOLOGY_GRAPH 전체 물리 프로퍼티 그래프 토폴로지", "Full STARTER_ONTOLOGY_GRAPH Topology"), legend=H.LABEL_COLORS)"""),
        md(f"### 3. {'ISO GQL 핵심 탐색 패턴 6종 실습 (`%%bqsql`) 및 1~2홉 서브그래프 시각화' if ko else '6 Core ISO GQL Traversal Patterns (`%%bqsql`) & 1..2-Hop Ego Subgraph'}"),
        code(f"""%%bqsql df_g1
GRAPH `{GRAPH}`
MATCH (c:CustomerContractNode)-[:USES_DEVICE]->(d:DeviceNode),
      (c)-[:SUBSCRIBES_PLAN]->(p:PlanNode)
RETURN c.customer_id AS customer_id, c.welfare_status AS welfare_status, c.elapsed_days AS elapsed_days,
       d.device_name AS device_name, p.plan_name AS plan_name, p.monthly_fee_krw AS monthly_fee_krw
ORDER BY customer_id"""),
        code(f"""%%bqsql df_g3
GRAPH `{GRAPH}`
MATCH (c:CustomerContractNode)-[:USES_DEVICE]->(d:DeviceNode)-[hs:HAS_SUBSIDY_POLICY]->(p:PlanNode)<-[:SUBSCRIBES_PLAN]-(c)
RETURN c.customer_id AS customer_id, d.device_name AS device_name, p.plan_name AS plan_name,
       hs.total_subsidy_krw AS policy_total_subsidy_krw, c.granted_subsidy_krw AS granted_subsidy_krw
ORDER BY customer_id"""),
        code(f"""%%bqsql df_g5
GRAPH `{GRAPH}`
MATCH p = (c:CustomerContractNode)-[e]-{{{{1,2}}}}(n)
WHERE c.customer_id = 'CUST_DEMO_001'
RETURN LABELS(n)[OFFSET(0)] AS reached_label, PATH_LENGTH(p) AS hops, TO_JSON(p) AS path
ORDER BY hops, reached_label"""),
        code(f"""%%bqsql df_g6
GRAPH `{GRAPH}`
MATCH (r:DomainRuleNode)-[a:APPLIES_TO_PLAN]->(p:PlanNode),
      (ch:DocChunkNode)
WHERE p.plan_id = 'PLAN-5G-37' AND ch.chunk_id = a.source_chunk_id
RETURN r.rule_id AS rule_id, a.relation_label_ko AS relation_label_ko, p.plan_name AS plan_name,
       ch.chunk_id AS chunk_id, ch.section_title AS section_title, SUBSTR(ch.content, 1, 90) AS excerpt
ORDER BY rule_id"""),
        code(f"""%%bqsql df_g8
GRAPH `{GRAPH}`
MATCH (c:CustomerContractNode)-[:USES_DEVICE]->(d:DeviceNode)-[cur:HAS_SUBSIDY_POLICY]->(p:PlanNode)<-[:SUBSCRIBES_PLAN]-(c),
      (d)-[tgt:HAS_SUBSIDY_POLICY]->(t:PlanNode),
      (s1:SubsidyNode), (s2:SubsidyNode)
WHERE c.customer_id = 'CUST_DEMO_001' AND t.plan_id = 'PLAN-5G-37'
  AND s1.policy_id = cur.policy_id AND s2.policy_id = tgt.policy_id
RETURN c.customer_id AS customer_id, p.plan_name AS current_plan, t.plan_name AS target_plan,
       s1.base_subsidy_krw AS current_base_subsidy_krw, s2.base_subsidy_krw AS target_base_subsidy_krw,
       s1.mandatory_retention_days AS retention_days, 120 AS elapsed_days,
       CAST(ROUND((s1.base_subsidy_krw - s2.base_subsidy_krw) * (s1.mandatory_retention_days - 120) / s1.mandatory_retention_days) AS INT64) AS penalty_krw"""),
        code("""H.show(df_g1)
H.show(df_g3)
H.show(df_g6)
H.show(df_g8)
enodes, eedges = H.paths_to_graph(H.pdf(df_g5)["path"])
H.draw_graph(enodes, eedges, H.t("CUST_DEMO_001 중심 1~2홉 가변 길이 경로 탐색 서브그래프", "CUST_DEMO_001 1..2-Hop Variable-Length Subgraph"), legend=H.LABEL_COLORS)"""),
        md(f"### 4. {'Vertex AI Gemini(`gemini-3.8-flash`) 기반 자연어 → ISO GQL 생성 및 스키마 가드 실험' if ko else 'Live Gemini (`gemini-3.8-flash`) NL-to-GQL Generation & Schema Guard'}"),
        code("""schema_str = H.schema_text(node_labels, edge_labels)
questions = [
    H.t("고객 계약별로 사용 중인 단말기 이름과 가입 요금제 이름, 월정액을 조회해줘.", "List each customer contract with its device name, subscribed plan name, and monthly fee."),
    H.t("요금제별로 연결된 도메인 규칙(DomainRuleNode) 개수와 규칙 ID 목록을 월정액 내림차순으로 보여줘.", "For each plan, count the applied DomainRuleNodes and list their rule_ids ordered by monthly fee desc."),
    H.t("2025년 8월 고객별 기지국 통화 품질 불만 건수와 해지 예측 점수를 조회해줘.", "Show base-station call quality complaints and churn scores per customer for August 2025."),
]
nl_rows = [H.nl2gql(q, schema_str) for q in questions]
H.show(pd.DataFrame(nl_rows))"""),
    ]


def build_stage4(lang="ko"):
    ko = lang == "ko"
    return [
        md(f"""# Stage 4. {"모듈형 MCP 서버 (8 Tools) & AI FDE 에이전트 런타임" if ko else "Modular MCP Server (8 Tools) & AI FDE Agent Runtime"}
## {"Step 4.1 8종 MCP 도구 카탈로그 및 위약금 곡선 시뮬레이션 · Step 4.2 2-Pass Gemini 에이전트 실행 및 경계 조건 방어" if ko else "Step 4.1 8 MCP Tools Catalog & Penalty Curve Simulation · Step 4.2 2-Pass Gemini Agent Execution & Boundary Defense"}

![Step 3 AI FDE Orchestration Flow](attachment:step3_fde_orchestration_flow.png)"""),
        code(f"""%load_ext bigframes
import pandas as pd
import nb_helpers as H
from src.agent.mcp_server import DomainMcpServer
from src.agent.reasoning_engine import AiFdeAgentEngine
H.setup("{lang}")
server = DomainMcpServer()
agent = AiFdeAgentEngine()"""),
        md(f"### 1. {'8종 모듈형 MCP 도구 카탈로그 및 고객 계약 현황 (`%%bqsql`)' if ko else '8 Modular MCP Tools Catalog & Customer Contracts (`%%bqsql`)'}"),
        code(f"""%%bqsql df_cust
SELECT c.customer_id, c.customer_segment, c.age_group, c.welfare_status, c.contract_type,
       c.elapsed_days, c.granted_subsidy_krw, d.device_name, p.plan_name, p.monthly_fee_krw
FROM `{FQ}.tb_customer_contract` c
JOIN `{FQ}.tb_device_master` d USING (device_id)
JOIN `{FQ}.tb_plan_master` p USING (plan_id)
ORDER BY c.customer_id"""),
        code("""H.show(pd.DataFrame(server.get_tool_catalog()))
H.show(df_cust)"""),
        md(f"### 2. {'도메인 추론 MCP 3종 직접 호출 및 경과일별 위약금 곡선 · 24개월 TCO 비교 차트' if ko else 'Direct Execution of 3 Domain Reasoning MCP Tools, Penalty Curve & 24-Month TCO Chart'}"),
        code("""r_prof = server.execute_tool("mcp_lookup_customer_profile", {"customer_id": "CUST_DEMO_001"})
H.show_tool(r_prof, "matched_rows")
r_pen = server.execute_tool("mcp_calculate_penalty_rule", {"customer_id": "CUST_DEMO_001", "target_monthly_fee_krw": 37000, "elapsed_days": 120})
H.show_tool(r_pen, "calculations")
r_gql = server.execute_tool("mcp_query_graph_and_wiki", {"device_keyword": "AlphaPhone 16 Pro", "plan_keyword": "115"})
H.show_tool(r_gql, "matched_graph_paths")
df_curve = H.penalty_curve(server, "CUST_DEMO_001", 37000, [30, 60, 90, 120, 150, 179, 180, 200])
H.show(df_curve)
H.line(df_curve, "elapsed_days", "penalty_krw", H.t("CUST_DEMO_001 경과일(30~200일)에 따른 차액정산 위약금 곡선 (180일 면제 경계)", "CUST_DEMO_001 Penalty Curve by Elapsed Days (180-Day Exemption Threshold)"), vline=180, vline_label="180d threshold")"""),
        md(f"### 3. {'AI FDE 2-Pass 에이전트 실행 — Golden CQ(`GROUNDED`) 및 경계 조건(`INSUFFICIENT_PARAMETERS`, `MATCH_NOT_FOUND`)' if ko else 'AI FDE 2-Pass Agent Execution — Golden CQs (`GROUNDED`) & Boundary Cases (`INSUFFICIENT_PARAMETERS`, `MATCH_NOT_FOUND`)'}"),
        code("""prompts = [
    ("CQ-01", "AlphaPhone 16 Pro 256GB 단말기를 5G Signature 115 요금제로 개통할 때 공시지원금, 유통망 추가지원금 상한, 총 지원금과 실구매가는 얼마인가요?"),
    ("CQ-02", "CUST_DEMO_001 고객이 개통 후 120일 시점에 월 37,000원 요금제(5G Lite 37)로 하향 변경하면 차액정산 위약금은 얼마인가요?"),
    ("CQ-03", "국가유공자 복지감면 등록 고객인 CUST_DEMO_002가 개통 95일 만에 하위 요금제로 변경할 때 위약금이 면제되나요?"),
    ("BC-PARAM", "방금 개통한 고객인데 지금 5G Lite 37 요금제로 내리면 위약금이 얼마인가요?"),
    ("BC-NOTFOUND", "CUST_NOT_EXIST_999 고객이 QuantumFold 99 단말기로 요금제를 변경할 때 위약금을 계산해 주세요."),
]
runs = []
for qid, q in prompts:
    res = agent.execute_cycle(q)
    H.show_agent(res, title=qid)
    runs.append(H.agent_row(res, qid))
df_runs = pd.DataFrame(runs)
H.show(df_runs)
H.grouped_bar(df_runs, "id", ["llm_ms", "bq_ms"], H.t("질의 유형별 Gemini LLM 추론 시간 vs BigQuery 실행 시간 (ms)", "Gemini LLM vs BigQuery Latency by Query Type (ms)"))"""),
    ]


def build_stage5(lang="ko"):
    ko = lang == "ko"
    return [
        md(f"""# Stage 5. {"End-to-End 데이터 리니지 & CQ · 경계 벤치마크 평가" if ko else "End-to-End Data Lineage & CQ / Boundary Benchmark Evaluation"}
## {"Step 5.1 4-Tier 데이터 리니지 그래프 검증 · Step 5.2 Golden CQ 5종 및 Boundary 10건 × 5회 평가 리포트" if ko else "Step 5.1 4-Tier Data Lineage Graph Verification · Step 5.2 5 Golden CQs & 10 Boundary Cases × 5 Trials Evaluation"}

![Step 3 AI FDE Orchestration Flow](attachment:step3_fde_orchestration_flow.png)"""),
        code(f"""%load_ext bigframes
import pandas as pd
import nb_helpers as H
from src.agent.reasoning_engine import AiFdeAgentEngine
H.setup("{lang}")"""),
        md(f"### 1. {'4-Tier End-to-End 데이터 리니지 조회(`%%bqsql`) 및 멀티파타이트 리니지 그래프 시각화' if ko else '4-Tier End-to-End Data Lineage (`%%bqsql`) & Multipartite Lineage Graph'}"),
        code(f"""%%bqsql df_lineage
SELECT c.contract_id, c.customer_id, d.device_name, p.plan_name, s.policy_id,
       e.rule_id, e.source_chunk_id, ch.content_sha256 AS anchor, ch.source_file
FROM `{FQ}.tb_customer_contract` c
JOIN `{FQ}.tb_device_master` d ON d.device_id = c.device_id
JOIN `{FQ}.tb_plan_master` p ON p.plan_id = c.plan_id
LEFT JOIN `{FQ}.tb_subsidy_policy` s ON s.device_id = c.device_id AND s.plan_id = c.plan_id
LEFT JOIN `{FQ}.edge_rule_applies_to_plan` e ON e.plan_id = c.plan_id
LEFT JOIN `{FQ}.tb_doc_chunks` ch ON ch.chunk_id = e.source_chunk_id
ORDER BY c.contract_id, e.rule_id"""),
        code("""H.show(df_lineage)
cq_rep = H.read_json("data/output/cq_benchmark_report.json")
lnodes, ledges = H.lineage_graph(H.pdf(df_lineage).to_dict("records"), cq_rep["test_results"])
H.draw_graph(lnodes, ledges, H.t("4-Tier End-to-End 리니지 그래프 (Source File → DocChunk → DomainRule → Contract → CQ)", "4-Tier End-to-End Lineage Graph (Source File → DocChunk → DomainRule → Contract → CQ)"),
             layout="layers", legend={"Tier 0 Source File": "#5F6368", "Tier 1 DocChunk": "#9334E6", "Tier 2 DomainRule": "#F9AB00", "Tier 3 Contract": "#1A73E8", "Tier 4 Golden CQ": "#188038"})"""),
        md(f"### 2. {'Golden CQ 5종 벤치마크 결과 분석 및 실시간 에이전트 재검증 (`recheck_cq`)' if ko else '5 Golden CQs Benchmark Analysis & Live Agent Re-Verification (`recheck_cq`)'}"),
        code("""df_cq = pd.DataFrame(cq_rep["test_results"])
H.show(df_cq, ["cq_id", "category", "status", "verification_status", "grounded_chunk", "llm_tokens", "elapsed_s", "verification_job_id"])
H.bar(df_cq, "cq_id", "elapsed_s", H.t("Golden CQ별 에이전트 응답 소요 시간 (초)", "Golden CQ Agent Elapsed Time (s)"), fmt="{:.2f}")
cqs = H.read_json("data/input/04_cq/golden_competency_questions.json")
agent = AiFdeAgentEngine()
res_cq2, df_chk = H.recheck_cq(cqs[1], agent)
H.show_agent(res_cq2, title="Live Re-Check: CQ-02")
H.show(df_chk)"""),
        md(f"### 3. {'Boundary 질의 10건 × 5회 반복(50 Trials) 안정성 · 일관성 평가 및 실패 분류 체계' if ko else '10 Boundary Cases × 5 Trials (50 Trials) Stability Evaluation & Failure Taxonomy'}"),
        code("""b_rep = H.read_json("data/output/boundary_benchmark_results.json")
df_bc = pd.DataFrame(b_rep["cases"])
H.md(f"**Benchmark `{b_rep['benchmark_id']}`** · trials={b_rep['total_trials']} · avg_success_rate=`{b_rep['avg_success_rate']}%` · avg_consistency_rate=`{b_rep['avg_consistency_rate']}%` · avg_intent_stability=`{b_rep['avg_intent_stability']}%`")
H.show(df_bc, ["case_id", "root_cause_code", "missing_context", "trials", "passed_trials", "success_rate", "consistency_rate", "intent_stability"])
H.grouped_bar(df_bc, "case_id", ["success_rate", "consistency_rate", "intent_stability"], H.t("Boundary 10건 × 5회 평가 지표 비교 (%)", "Boundary 10 Cases × 5 Trials Metrics (%)"))
df_tax = df_bc.groupby("root_cause_code", as_index=False).agg(cases=("case_id", "count"), avg_success=("success_rate", "mean"), avg_consistency=("consistency_rate", "mean"))
H.show(df_tax)"""),
    ]
