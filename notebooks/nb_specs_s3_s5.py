# -*- coding: utf-8 -*-
"""Cell builders for Stage 3, Stage 4, and Stage 5 notebooks (KO/EN).

Aligned with Phases 5, 6, 7, and 8 of the 8-Phase Engineering Flow:
  - Stage 3: Phase 5. 구축 (Physical Property Graph Construction & ISO GQL)
  - Stage 4: Phase 6. 에이전트 구축 (Agent & 8-Tool MCP Setup) & Phase 7. 답변 (Grounded Answering)
  - Stage 5: Phase 8. 검증 (End-to-End Lineage, Golden CQ Audit & 50-Trial Release Gate)
"""
from nb_specs_s0_s2 import FQ, GRAPH, _bootstrap_code, code, md, nav_footer, nav_header, report_values


def build_stage3(lang="ko"):
    ko = lang == "ko"
    banner_file = "stage3_property_graph_flow_ko.png" if ko else "stage3_property_graph_flow_en.png"
    return [
        md(f"""{nav_header(3, lang)}

---

# {"Stage 3. [구축] Zero-ETL 물리 프로퍼티 그래프 (BigQuery Graph / Spanner Graph) & 바인딩 변수 기반 ISO GQL" if ko else "Stage 3. [Build Graph] Zero-ETL Physical Property Graph (BigQuery / Spanner) & Parameterized ISO GQL"}
## {"Step 3.1 6 Node × 4 Edge 그래프 메타모델 설계 및 DDL 프로비저닝 · Step 3.2 인스턴스 토폴로지 시각화 및 ISO GQL / NL2GQL" if ko else "Step 3.1 6 Node × 4 Edge Metamodel Design & DDL Provisioning · Step 3.2 Instance Topology & Parameterized ISO GQL / NL2GQL"}

{("Stage 3은 방법론의 **Phase 5(물리 그래프 구축)**를 구현합니다. Stage 1·2에서 적재한 BigQuery 10개 테이블을 별도 복제 없이(**Zero-ETL**) `pipeline/graph_builder.py`를 통해 **6개 노드 레이블(`CustomerContractNode`, `DeviceNode`, `PlanNode`, `SubsidyNode`, `DomainRuleNode`, `DocChunkNode`)**과 **4개 엣지 레이블(`USES_DEVICE`, `SUBSCRIBES_PLAN`, `HAS_SUBSIDY_POLICY`, `APPLIES_TO_PLAN`)**을 가진 `STARTER_ONTOLOGY_GRAPH`로 선언하고, **바인딩 변수 명세와 실행 ISO GQL 문장**을 투명하게 확인하며 다중 홉 탐색과 Gemini 기반 자연어→GQL 변환(`nl2gql`)을 수행합니다."
  if ko else
  "Stage 3 implements **Phase 5 (Physical Property Graph Construction)**. Without duplicating data (**Zero-ETL**), `pipeline/graph_builder.py` projects the 10 BigQuery tables into `STARTER_ONTOLOGY_GRAPH` with **6 Node Labels** and **4 Edge Labels**, verifies key uniqueness via `mcp_stage3_property_graph`, visualizes both the schema metamodel and layered instance topologies, and executes multi-hop ISO GQL queries—explicitly displaying the **bound variables table**, **executed ISO GQL statement**, and **live BigQuery results** alongside Gemini NL-to-GQL (`nl2gql`).")}

![Stage 3 Build Property Graph Architecture Flow](attachment:{banner_file})"""),
        code(_bootstrap_code(lang, with_agent=False)),
        md(f"### 1. {'[Phase 5a: 그래프 스키마 설계 및 메타모델 도식] `INFORMATION_SCHEMA.PROPERTY_GRAPHS` 라이브 메타데이터 및 6 Node × 4 Edge 설계도' if ko else '[Phase 5a: Graph Schema Design & Metamodel] `INFORMATION_SCHEMA.PROPERTY_GRAPHS` Metadata & 6 Node × 4 Edge Metamodel Schematic'}"),
        code("""node_labels, edge_labels, meta = H.graph_metadata()
H.md(f"**Live Property Graph Catalog Job**: `{meta['job_id']}` ({meta['elapsed_ms']} ms) · Nodes `{len(node_labels)}` · Edges `{len(edge_labels)}`")
H.show(pd.DataFrame(node_labels))
H.show(pd.DataFrame(edge_labels))
H.draw_property_graph_metamodel()"""),
        md(f"### 2. {'[Phase 5b: 듀얼 엔진 DDL 구축 및 무결성 검증] BigQuery Graph / Spanner Graph DDL 비교 및 `mcp_stage3_property_graph` 실행' if ko else '[Phase 5b: Dual-Engine DDL Provisioning & Integrity Check] BigQuery / Spanner Graph DDL & `mcp_stage3_property_graph` Execution'}"),
        code("""H.show_md_file(H.ROOT / "data/output/create_property_graph.sql", max_lines=38)
H.show_md_file(H.ROOT / "data/output/create_spanner_graph.sql", max_lines=38)
res_s3 = server.execute_tool("mcp_stage3_property_graph", {"steps": ["promote_dw_nodes", "synthesize_graph_ddl", "verify_gql_templates"]})
H.show_tool(res_s3, "node_tables")
H.show(pd.DataFrame([res_s3["gql_paths"]]))"""),
        md(f"### 3. {'[Phase 5c: 물리 그래프 데이터 확인 및 토폴로지 도식] 노드 · 엣지 레이블 분포(`%%bqsql`) 및 전체 인스턴스 토폴로지 시각화' if ko else '[Phase 5c: Instance Data & Topology Visualization] Node & Edge Label Distribution (`%%bqsql`) and Full Instance Topology'}"),
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
        code(f"""H.md(H._format_vars_md({{
    "GRAPH": ("{GRAPH}", H.t("대상 BigQuery Property Graph 식별자", "Target BigQuery Property Graph")),
    "pattern (n) / (a)-[e]->(b)": ("ALL_LABELS (6N × 4E)", H.t("전체 노드·엣지 레이블 스캔 및 JSON 경로 추출", "Full node/edge label scan & JSON path projection")),
}}) + "**" + H.t("실행된 ISO GQL 문장 (Executed ISO GQL Statements)", "Executed ISO GQL Statements") + "**\\n```sql\\n"
f"GRAPH `{GRAPH}`\\nMATCH p = (a)-[e]->(b)\\nRETURN TO_JSON(p) AS path\\n```")
H.show(df_gnodes)
H.show(df_gedges)
H.bar(df_gnodes, "label", "nodes", H.t("STARTER_ONTOLOGY_GRAPH 노드 레이블별 인스턴스 수", "Node Count by Label"),
      color=[H.LABEL_COLORS.get(x, "#1A73E8") for x in H.pdf(df_gnodes)["label"]])
H.bar(df_gedges, "label", "edges", H.t("STARTER_ONTOLOGY_GRAPH 엣지 레이블별 인스턴스 수", "Edge Count by Label"), color="#0d9488")
nodes, edges = H.paths_to_graph(H.pdf(df_all_paths)["path"])
H.draw_graph(nodes, edges, H.t("STARTER_ONTOLOGY_GRAPH 전체 물리 프로퍼티 그래프 토폴로지 (25 노드 · 29 엣지 · 5계층 배치)", "Full STARTER_ONTOLOGY_GRAPH Instance Topology (25 Nodes · 29 Edges · 5-Column Layout)"), legend=H.LABEL_COLORS)"""),
        md(f"### 4. {'[Phase 5d: 바인딩 변수 기반 다중 홉 ISO GQL 탐색 실습 (`H.run_gql`)] 실행 GQL 문장 · 바인딩 변수 · 결과 테이블 및 1~2홉 서브그래프 도식' if ko else '[Phase 5d: Parameterized Multi-Hop ISO GQL Patterns (`H.run_gql`)] Executed GQL Statements, Bound Variables, Result Tables & 1..2-Hop Ego Subgraph'}"),
        code(f"""# GQL-01: 2-Hop Customer Contract -> Device & Subscribed Plan
gql_1 = \"\"\"GRAPH `{GRAPH}`
MATCH (c:CustomerContractNode)-[:USES_DEVICE]->(d:DeviceNode),
      (c)-[:SUBSCRIBES_PLAN]->(p:PlanNode)
RETURN c.customer_id AS customer_id, c.welfare_status AS welfare_status, c.elapsed_days AS elapsed_days,
       d.device_name AS device_name, p.plan_name AS plan_name, p.monthly_fee_krw AS monthly_fee_krw
ORDER BY customer_id\"\"\"
df_g1, _ = H.run_gql(
    gql_1,
    variables={{
        "GRAPH": ("{GRAPH}", H.t("프로퍼티 그래프 뷰", "Property Graph view")),
        "edge_1": ("USES_DEVICE", H.t("CustomerContractNode → DeviceNode (edge_contract_device)", "CustomerContractNode -> DeviceNode")),
        "edge_2": ("SUBSCRIBES_PLAN", H.t("CustomerContractNode → PlanNode (edge_contract_plan)", "CustomerContractNode -> PlanNode")),
    }},
    title=H.t("GQL-01 · 고객 약정 중심 단말기 및 가입 요금제 2-Hop 탐색", "GQL-01 · 2-Hop Customer Contract to Device & Subscribed Plan"),
)

# GQL-02: Diamond Pattern (Contract -> Device -> Subsidy -> Plan <- Contract)
gql_3 = \"\"\"GRAPH `{GRAPH}`
MATCH (c:CustomerContractNode)-[:USES_DEVICE]->(d:DeviceNode)-[hs:HAS_SUBSIDY_POLICY]->(p:PlanNode)<-[:SUBSCRIBES_PLAN]-(c)
RETURN c.customer_id AS customer_id, d.device_name AS device_name, p.plan_name AS plan_name,
       hs.total_subsidy_krw AS policy_total_subsidy_krw, c.granted_subsidy_krw AS granted_subsidy_krw
ORDER BY customer_id\"\"\"
df_g3, _ = H.run_gql(
    gql_3,
    variables={{
        "GRAPH": ("{GRAPH}", H.t("프로퍼티 그래프 뷰", "Property Graph view")),
        "pattern": ("(c)-[:USES_DEVICE]->(d)-[hs:HAS_SUBSIDY_POLICY]->(p)<-[:SUBSCRIBES_PLAN]-(c)",
                    H.t("4개 엔티티 간 다이아몬드(폐루프) 정합성 매칭", "4-node closed diamond consistency pattern")),
    }},
    title=H.t("GQL-02 · 다이아몬드 패턴 매칭 (약정 지급 지원금 vs 정책 고시 총지원금 대조)", "GQL-02 · Diamond Pattern Match (Granted Subsidy vs. Policy Total Subsidy)"),
)"""),
        code(f"""# GQL-03: Plan-to-DomainRule & SHA-256 DocChunk Anchor Join
target_plan_for_rules = "PLAN-5G-37"
gql_6 = f\"\"\"GRAPH `{GRAPH}`
MATCH (r:DomainRuleNode)-[a:APPLIES_TO_PLAN]->(p:PlanNode),
      (ch:DocChunkNode)
WHERE p.plan_id = '{{target_plan_for_rules}}' AND ch.chunk_id = a.source_chunk_id
RETURN r.rule_id AS rule_id, a.relation_label_ko AS relation_label_ko, p.plan_name AS plan_name,
       ch.chunk_id AS chunk_id, ch.section_title AS section_title, SUBSTR(ch.content, 1, 90) AS excerpt
ORDER BY rule_id\"\"\"
df_g6, _ = H.run_gql(
    gql_6,
    variables={{
        "GRAPH": ("{GRAPH}", H.t("프로퍼티 그래프 뷰", "Property Graph view")),
        "$target_plan_id (p.plan_id)": (f"'{{target_plan_for_rules}}'", H.t("PlanNode 요금제 ID 필터 변수", "PlanNode target plan_id filter")),
        "ch.chunk_id": ("a.source_chunk_id", H.t("APPLIES_TO_PLAN 엣지 ↔ DocChunkNode 앵커 조인", "APPLIES_TO_PLAN edge to DocChunkNode join key")),
    }},
    title=H.t("GQL-03 · 요금제 바인딩 도메인 규칙 및 원문 정책 청크(SHA-256) 결합 조회", "GQL-03 · Plan-Bound Domain Rules Joined with SHA-256 Policy Chunks"),
)

# GQL-04: Single-Query Prorated Subsidy Clawback Calculation
cust_id_param = "CUST_DEMO_001"
target_plan_param = "PLAN-5G-37"
elapsed_days_param = 120
gql_8 = f\"\"\"GRAPH `{GRAPH}`
MATCH (c:CustomerContractNode)-[:USES_DEVICE]->(d:DeviceNode)-[cur:HAS_SUBSIDY_POLICY]->(p:PlanNode)<-[:SUBSCRIBES_PLAN]-(c),
      (d)-[tgt:HAS_SUBSIDY_POLICY]->(t:PlanNode),
      (s1:SubsidyNode), (s2:SubsidyNode)
WHERE c.customer_id = '{{cust_id_param}}' AND t.plan_id = '{{target_plan_param}}'
  AND s1.policy_id = cur.policy_id AND s2.policy_id = tgt.policy_id
RETURN c.customer_id AS customer_id, p.plan_name AS current_plan, t.plan_name AS target_plan,
       s1.base_subsidy_krw AS current_base_subsidy_krw, s2.base_subsidy_krw AS target_base_subsidy_krw,
       s1.mandatory_retention_days AS retention_days, {{elapsed_days_param}} AS elapsed_days,
       CAST(ROUND((s1.base_subsidy_krw - s2.base_subsidy_krw) * (s1.mandatory_retention_days - {{elapsed_days_param}}) / s1.mandatory_retention_days) AS INT64) AS penalty_krw\"\"\"
df_g8, _ = H.run_gql(
    gql_8,
    variables={{
        "GRAPH": ("{GRAPH}", H.t("프로퍼티 그래프 뷰", "Property Graph view")),
        "$customer_id (c.customer_id)": (f"'{{cust_id_param}}'", H.t("조회 대상 고객 ID (CustomerContractNode)", "Target customer_id on CustomerContractNode")),
        "$target_plan_id (t.plan_id)": (f"'{{target_plan_param}}'", H.t("하향 변경 대상 요금제 ID (PlanNode)", "Target downgrade plan_id on PlanNode")),
        "$elapsed_days": (str(elapsed_days_param), H.t("개통 후 경과일수 (180일 기준 일할 산식 변수)", "Elapsed days since activation (prorated formula input)")),
    }},
    title=H.t("GQL-04 · 단일 ISO GQL 쿼리 기반 요금제 하향 차액정산 위약금 산출", "GQL-04 · Single-Query ISO GQL Prorated Downgrade Penalty Calculation"),
)"""),
        code(f"""# GQL-05: 1..2-Hop Variable-Length Ego Subgraph for CUST_DEMO_001
ego_customer = "CUST_DEMO_001"
gql_5 = f\"\"\"GRAPH `{GRAPH}`
MATCH p = (c:CustomerContractNode)-[e]-{{{{1,2}}}}(n)
WHERE c.customer_id = '{{ego_customer}}'
RETURN LABELS(n)[OFFSET(0)] AS reached_label, PATH_LENGTH(p) AS hops, TO_JSON(p) AS path
ORDER BY hops, reached_label\"\"\"
df_g5, _ = H.run_gql(
    gql_5,
    variables={{
        "GRAPH": ("{GRAPH}", H.t("프로퍼티 그래프 뷰", "Property Graph view")),
        "$customer_id (c.customer_id)": (f"'{{ego_customer}}'", H.t("중심 노드(Ego) 고객 ID", "Center ego node customer_id")),
        "quantifier -{{1,2}}-": ("1..2 hops", H.t("ISO GQL 가변 길이 경로 탐색 범위", "ISO GQL variable-length path quantifier")),
    }},
    title=H.t("GQL-05 · CUST_DEMO_001 중심 1~2홉 가변 길이 서브그래프 경로 추출", "GQL-05 · 1..2-Hop Variable-Length Ego Subgraph Extraction for CUST_DEMO_001"),
    show_df=False,
)
H.show(df_g5[["reached_label", "hops"]])
enodes, eedges = H.paths_to_graph(H.pdf(df_g5)["path"])
H.draw_graph(enodes, eedges, H.t("CUST_DEMO_001 중심 1~2홉 가변 길이 탐색 서브그래프 (5계층 배치)", "CUST_DEMO_001 1..2-Hop Variable-Length Ego Subgraph (5-Column Layout)"), legend=H.LABEL_COLORS)"""),
        md(f"### 5. {'[Phase 5e: 자연어 → ISO GQL 변환(`nl2gql`) 및 스키마 가드 검증] Vertex AI Gemini(`gemini-3.8-flash`) 기반 GQL 문장 · 바인딩 변수 생성 및 실행' if ko else '[Phase 5e: Live Gemini NL-to-GQL (`nl2gql`) & Schema Guard] Natural Language to ISO GQL Statement, Bound Variables & Execution'}"),
        code("""schema_str = H.schema_text(node_labels, edge_labels)
questions = [
    H.t("고객 계약별로 사용 중인 단말기 이름과 가입 요금제 이름, 월정액을 조회해줘.", "List each customer contract with its device name, subscribed plan name, and monthly fee."),
    H.t("요금제별로 연결된 도메인 규칙(DomainRuleNode) 개수와 규칙 ID 목록을 월정액 내림차순으로 보여줘.", "For each plan, count the applied DomainRuleNodes and list their rule_ids ordered by monthly fee desc."),
    H.t("2025년 8월 고객별 기지국 통화 품질 불만 건수와 해지 예측 점수를 조회해줘.", "Show base-station call quality complaints and churn scores per customer for August 2025."),
]
nl_rows = [H.nl2gql(q, schema_str) for q in questions]
H.show(pd.DataFrame(nl_rows))"""),
        md(f"### 6. {'[Phase 5f: 양대 그래프 엔진 지연시간 비교(p50/p95) & Graph Fabric(`EXTERNAL_QUERY`) 연합 조인] BigQuery Property Graph(기본값) vs Cloud Spanner Graph(100 PU)' if ko else '[Phase 5f: Live Dual-Engine Latency Benchmark (p50/p95) & Graph Fabric (`EXTERNAL_QUERY`) Federated Join] BigQuery Property Graph (Default) vs. Cloud Spanner Graph (100 PU)'}"),
        code("""df_bench = H.benchmark_dual_engine_df(runs=3)
H.show(df_bench)
H.grouped_bar(df_bench, "engine", ["p50_ms", "p95_ms"],
              H.t("BigQuery Property Graph(기본값) vs Cloud Spanner Graph(100 PU) 3-Hop ISO GQL 지연시간 비교 (ms)",
                  "BigQuery Property Graph (Default) vs. Cloud Spanner Graph (100 PU) 3-Hop ISO GQL Latency (ms)"),
              fmt="{:,.1f}", ylabel="Latency (ms)")"""),
        code("""_ = H.run_graph_fabric_federated_join()"""),
        nav_footer(
            3, lang,
            qa_items=[
                (
                    "Zero-ETL BigQuery Property Graph(기본값)와 Cloud Spanner Graph(온라인 저지연 옵션), 그리고 Graph Fabric(`EXTERNAL_QUERY`)은 어떻게 상호보완적으로 동작하나요?" if ko
                    else "How do Zero-ETL BigQuery Property Graph (default), Cloud Spanner Graph (low-latency option), and Graph Fabric (`EXTERNAL_QUERY`) complement each other?",
                    "원천 DW 테이블 6종과 엣지 테이블 4종은 기본값인 `BigQuery Property Graph`에서 복제 없이(Zero-ETL) 대규모 분석과 에이전트 추론을 수행하고, 실시간 저지연 포인트 탐색이 필요한 워크로드는 `Cloud Spanner Graph`(`100 PU`)에서 처리하며, `EXTERNAL_QUERY(spanner_fabric_conn)`를 통해 Spanner GQL 탐색 결과와 BigQuery `tb_doc_chunks`를 단일 SQL로 연합 조인(Graph Fabric)합니다." if ko
                    else "`BigQuery Property Graph` (default) projects the 6 node and 4 edge tables with Zero-ETL for analytical and agent workloads, `Cloud Spanner Graph` (`100 PU`) serves low-latency online point traversals, and `EXTERNAL_QUERY(spanner_fabric_conn)` federates Spanner ISO GQL results directly with BigQuery `tb_doc_chunks` in a single query."
                ),
            ],
            findings=[
                "`STARTER_ONTOLOGY_GRAPH`는 6개 노드 레이블(총 31행, 중복 키 `0건`)과 4개 엣지 레이블(총 31행)로 구성되며, 활성 연결 경로에서 25개 노드와 29개 방향성 엣지가 추출되었습니다." if ko
                else "`STARTER_ONTOLOGY_GRAPH` comprises 6 node labels (31 rows, `0` duplicate keys) and 4 edge labels (31 rows), yielding 25 connected nodes and 29 directed edges.",
                "바인딩 변수(`c.customer_id='CUST_DEMO_001'`, `t.plan_id='PLAN-5G-37'`, `elapsed_days=120`)를 적용한 ISO GQL 다이아몬드 쿼리(`GQL-04`)로 일할 위약금(`(500,000 - 200,000) × 60 / 180 = 100,000원`)을 단일 GQL 문장으로 산출했습니다." if ko
                else "Using an ISO GQL diamond pattern (`GQL-04`) bound to `customer_id='CUST_DEMO_001'`, `target_plan_id='PLAN-5G-37'`, and `elapsed_days=120`, we computed the prorated downgrade penalty (`100,000 KRW`) in a single GQL query.",
                "양대 그래프 엔진 3회 반복 실측에서 BigQuery Property Graph(기본값)와 Cloud Spanner Graph(`starter-spanner`, `100 PU`)의 `p50`/`p95` 응답 지연시간을 정량 비교하고, `EXTERNAL_QUERY` 연합 조인으로 Spanner 그래프 탐색 결과(10행)와 BigQuery 정책 청크를 결합했습니다." if ko
                else "Across 3 repeated runs, we benchmarked `p50`/`p95` traversal latency between BigQuery Property Graph (default) and Cloud Spanner Graph (`starter-spanner`, `100 PU`), and verified the `EXTERNAL_QUERY` federated join returning 10 rows across Spanner Graph and BigQuery `tb_doc_chunks`."
            ],
            next_steps=[
                "다음 단계인 `Stage 4 (에이전트·답변)` 노트북으로 이동하여 이 Property Graph와 BigQuery/Spanner 원장을 호출하는 8종 모듈형 MCP 서버와 2-Pass AI FDE 에이전트 구축 및 답변 생성 과정을 확인하세요." if ko
                else "Proceed to `Stage 4 (Build Agent & Answer)` to see how the 8-Tool MCP Server (`engine='bigquery' | 'spanner'`) and 2-Pass AI FDE Agent orchestrate SQL and ISO GQL queries to generate grounded answers."
            ],
        ),
    ]


def build_stage4(lang="ko"):
    ko = lang == "ko"
    banner_file = "stage4_agent_mcp_flow_ko.png" if ko else "stage4_agent_mcp_flow_en.png"
    return [
        md(f"""{nav_header(4, lang)}

---

# {"Stage 4. [에이전트 구축 & 답변] 8종 모듈형 MCP 서버 구축 · 슬롯 검증 & 2-Pass AI FDE 에이전트 답변 생성" if ko else "Stage 4. [Build Agent & Answer] 8-Tool Modular MCP Server, Slot Validation & 2-Pass AI FDE Agent Execution"}
## {"Step 4.1 8종 MCP 도구 및 2-Pass 에이전트 아키텍처 구축 · Step 4.2 결정론적 산식 시뮬레이션 및 가드레일 기반 답변 생성" if ko else "Step 4.1 8 MCP Tools & 2-Pass Agent Architecture Setup · Step 4.2 Deterministic Penalty Simulation & Guardrailed Answering"}

{("Stage 4는 방법론의 **Phase 6(에이전트 구축)**과 **Phase 7(답변 생성)**을 구현합니다. LLM이 위약금이나 지원금을 암산하거나 존재하지 않는 요금제를 환각하지 않도록, **(1) BigQuery 실시간 카탈로그 기반 슬롯 검증(`resolve_params`)**, **(2) 결정론적 SQL 및 바인딩 변수 기반 ISO GQL을 양대 엔진(`engine=\"bigquery\"` 기본값 및 `engine=\"spanner\"`)에서 실행하는 8종 모듈형 MCP 도구(`DomainMcpServer`)**, **(3) 4단계 라이프사이클로 동작하는 2-Pass Gemini(`gemini-3.8-flash`) 추론 엔진(`AiFdeAgentEngine`)**을 구축하고 정상 질의(`GROUNDED`)와 경계 질의(`INSUFFICIENT_PARAMETERS`, `MATCH_NOT_FOUND`)에 대한 답변을 생성합니다."
  if ko else
  "Stage 4 implements **Phase 6 (Agent & MCP Setup)** and **Phase 7 (Grounded Answering)**. To prevent LLM math errors or entity hallucinations, we combine **(1) Live BigQuery Catalog Slot Validation (`resolve_params`)**, **(2) the 8-Tool Modular MCP Server (`DomainMcpServer`) executing deterministic SQL and parameterized ISO GQL across both `engine=\"bigquery\"` (default) and `engine=\"spanner\"`**, and **(3) the 4-Step, 2-Pass Gemini (`gemini-3.8-flash`) Reasoning Engine (`AiFdeAgentEngine`)**, verifying both `GROUNDED` answers and boundary guardrails (`INSUFFICIENT_PARAMETERS`, `MATCH_NOT_FOUND`).")}

![Stage 4 Agent and MCP Orchestration Flow](attachment:{banner_file})"""),
        code(_bootstrap_code(lang, with_agent=True)),
        md(f"### 1. {'[Phase 6a: 에이전트 및 MCP 서버 아키텍처 구축] 2-Pass 오케스트레이션 설계도 · 8종 MCP 도구 카탈로그 · `mcp_stage4_agent_orchestration`' if ko else '[Phase 6a: Agent & MCP Architecture Setup] 2-Pass Orchestration Blueprint, 8-Tool MCP Catalog & `mcp_stage4_agent_orchestration`'}"),
        code("""H.draw_agent_architecture()
H.show(pd.DataFrame(server.get_tool_catalog()), ["name", "stage", "category", "steps", "spec_origin", "description" if H.LANG == "ko" else "description_en"])
res_s4 = server.execute_tool("mcp_stage4_agent_orchestration", {"steps": ["decompose_subgoals", "dispatch_domain_mcps", "verify_grounding_anchors"]})
H.show_tool(res_s4, "active_rules")"""),
        md(f"### 2. {'[Phase 6b: 카탈로그 기반 슬롯 파싱 검증 (`resolve_params`)] 자연어 질문에서 안전하게 파라미터를 추출하고 미등록 엔티티를 차단하는 과정' if ko else '[Phase 6b: Catalog-Validated Slot Resolution (`resolve_params`)] Extracting Parameters & Stripping Unregistered Entities'}"),
        code("""sample_queries = [
    "CUST_DEMO_001 고객이 개통 120일 시점에 5G Light(37,000원)로 하향 변경하면 위약금이 얼마인가요?",
    "AlphaPhone 16 Pro 256GB 단말기를 5G Signature 115 요금제로 개통할 때 지원금과 실구매가는?",
    "CUST_NOT_EXIST_999 고객이 QuantumFold 99 단말기로 99,000원 요금제 변경 시 위약금은?",
    "방금 개통했는데 37,000원 요금제로 내리면 위약금이 얼마인가요?",
]
slot_rows = []
for q in sample_queries:
    resolved = server.resolve_params({"query": q})
    slot_rows.append({"query": q, **{k: v for k, v in resolved.items()}})
H.show(pd.DataFrame(slot_rows))""" if ko else """sample_queries = [
    "If customer CUST_DEMO_001 downgrades to 5G Light (37,000 KRW) on day 120, what is the penalty?",
    "When activating the AlphaPhone 16 Pro 256GB on the 5G Signature 115 plan, what are the subsidy and net price?",
    "What is the penalty if customer CUST_NOT_EXIST_999 switches to a 99,000 KRW plan on a QuantumFold 99 device?",
    "I just activated my line—what is the penalty if I downgrade to the 37,000 KRW plan?",
]
slot_rows = []
for q in sample_queries:
    resolved = server.resolve_params({"query": q})
    slot_rows.append({"query": q, **{k: v for k, v in resolved.items()}})
H.show(pd.DataFrame(slot_rows))"""),
        md(f"### 3. {'[Phase 6c: 런타임 도메인 MCP 3종 직접 호출 및 GQL 문장/변수 확인] 고객 프로필 · 위약금/24개월 TCO 산식 · 그래프/위키 탐색(`executed_gql`) 및 180일 위약금 곡선' if ko else '[Phase 6c: Direct Execution of 3 Runtime Domain MCP Tools] Customer Profile, Penalty/24M TCO Math, Graph Traversal (`executed_gql` + Bound Variables) & 180-Day Penalty Curve'}"),
        code("""r_prof = server.execute_tool("mcp_lookup_customer_profile", {"customer_id": "CUST_DEMO_001"})
H.show_tool(r_prof, "matched_rows", ["customer_id", "device_name", "plan_name", "monthly_fee_krw", "factory_price_krw", "total_subsidy_krw", "net_installment_principal_krw", "grounded_chunk_id"])

r_pen = server.execute_tool("mcp_calculate_penalty_rule", {"customer_id": "CUST_DEMO_001", "target_monthly_fee_krw": 37000, "elapsed_days": 120})
H.show_tool(r_pen, "calculations", ["customer_id", "plan_name", "target_plan_name", "elapsed_days", "penalty_status", "penalty_krw", "public_subsidy_24m_tco_krw", "selective_24m_tco_krw", "tco_recommendation", "grounded_chunk_id"])

r_gql = server.execute_tool("mcp_query_graph_and_wiki", {"customer_id": "CUST_DEMO_001"})
H.show_tool(r_gql, "matched_graph_paths", ["customer_id", "device_name", "plan_name", "rule_id", "relation_label_ko", "source_chunk_id", "anchor"])

df_curve = H.penalty_curve(server, "CUST_DEMO_001", 37000, [30, 60, 90, 120, 150, 179, 180, 200])
H.show(df_curve)
H.line(df_curve, "elapsed_days", "penalty_krw",
       H.t("CUST_DEMO_001 경과일(30~200일)별 차액정산 위약금 시뮬레이션 곡선 (180일 면제 경계)",
           "CUST_DEMO_001 Prorated Penalty Curve Across Elapsed Days 30..200 (180-Day Exemption Threshold)"),
       vline=180, vline_label="180d threshold")"""),
        code("""H.md(H.t("#### MCP 호출별 BigQuery 리소스 (`bq_jobs`: job_id · rows · elapsed_ms)", "#### BigQuery resources per MCP call (`bq_jobs`: job_id, rows, elapsed_ms)"))
H.show(pd.DataFrame([{"tool": r["tool"], "job_id": j["job_id"], "engine": j["engine"], "status": j["status"], "rows": j["rows"], "elapsed_ms": j["elapsed_ms"]}
                     for r in (r_prof, r_pen, r_gql) for j in r.get("bq_jobs", [])]))"""),
        md(f"### 4. {'[Phase 6d: 양대 그래프 엔진 MCP 런타임 비교 (`engine=\"bigquery\"` vs `engine=\"spanner\"`)] Cloud Spanner Graph 직접 실행 및 결과 정합성·지연시간 대조' if ko else '[Phase 6d: Dual-Engine Runtime MCP Execution (`engine=\"bigquery\"` vs. `engine=\"spanner\"`)] Cloud Spanner Graph Execution Parity & Latency Comparison'}"),
        code("""df_mcp_eng = H.compare_mcp_engines(server)
H.show(df_mcp_eng)
H.grouped_bar(df_mcp_eng, "mcp_tool", ["bigquery_ms", "spanner_ms"],
              H.t("런타임 도메인 MCP 도구 3종 — BigQuery(기본값) vs Cloud Spanner(100 PU) 실행 시간 비교 (ms)",
                  "Runtime Domain MCP Tools — BigQuery (Default) vs. Cloud Spanner (100 PU) Latency Comparison (ms)"),
              fmt="{:,.1f}", ylabel="Latency (ms)")"""),
        md(f"### 5. {'[Phase 7: 2-Pass 에이전트 End-to-End 답변 생성] Golden CQ(`GROUNDED`) 및 경계 조건(`INSUFFICIENT_PARAMETERS`, `MATCH_NOT_FOUND`) 4단계 트레이스' if ko else '[Phase 7: End-to-End 2-Pass Agent Answering] Golden CQs (`GROUNDED`) & Boundary Guardrails (`INSUFFICIENT_PARAMETERS`, `MATCH_NOT_FOUND`)'}"),
        code("""prompts = [
    ("CQ-01 (Subsidy & Net Price)", "AlphaPhone 16 Pro 256GB 단말기를 5G Signature 115 요금제로 개통할 때 공시지원금, 유통망 추가지원금 상한, 총 지원금과 실구매가는 얼마인가요?"),
    ("CQ-02 (120d Prorated Penalty)", "CUST_DEMO_001 고객이 개통 후 120일 시점에 월 37,000원 요금제(5G Lite 37)로 하향 변경하면 차액정산 위약금은 얼마인가요?"),
    ("CQ-03 (Welfare Exemption)", "국가유공자 복지감면 등록 고객인 CUST_DEMO_002가 개통 95일 만에 하위 요금제로 변경할 때 위약금이 면제되나요?"),
    ("BC-PARAM (Missing Customer/Device)", "방금 개통한 고객인데 지금 5G Lite 37 요금제로 내리면 위약금이 얼마인가요?"),
    ("BC-NOTFOUND (Unknown Entity)", "CUST_NOT_EXIST_999 고객이 QuantumFold 99 단말기로 요금제를 변경할 때 위약금을 계산해 주세요."),
]
runs = []
for qid, q in prompts:
    res = agent.execute_cycle(q)
    H.show_agent(res, title=qid)
    runs.append({**H.agent_row(res, qid.split()[0]), "prompt_tokens": res["llm_telemetry"]["prompt_tokens"],
                 "completion_tokens": res["llm_telemetry"]["candidates_tokens"]})
df_runs = pd.DataFrame(runs)
H.show(df_runs)
H.grouped_bar(df_runs, "id", ["llm_ms", "bq_ms"],
              H.t("질의 시나리오별 Gemini 2-Pass 추론 시간 vs BigQuery SQL/GQL 실행 시간 (ms)",
                  "Gemini 2-Pass LLM Inference vs. BigQuery SQL/GQL Latency by Scenario (ms)"))""" if ko else """prompts = [
    ("CQ-01 (Subsidy & Net Price)", "When activating the AlphaPhone 16 Pro 256GB on the 5G Signature 115 plan, what are the public subsidy, retail additional subsidy cap, total subsidy, and net purchase price?"),
    ("CQ-02 (120d Prorated Penalty)", "If customer CUST_DEMO_001 downgrades to the 37,000 KRW monthly plan (5G Lite 37) on day 120 after activation, what is the prorated difference penalty?"),
    ("CQ-03 (Welfare Exemption)", "Is customer CUST_DEMO_002 (registered under National Merit Welfare) exempt from penalty charges when downgrading to a lower plan on day 95?"),
    ("BC-PARAM (Missing Customer/Device)", "I am a newly activated subscriber—what is the penalty if I downgrade to the 5G Lite 37 plan right now?"),
    ("BC-NOTFOUND (Unknown Entity)", "Please calculate the penalty when customer CUST_NOT_EXIST_999 changes plans with a QuantumFold 99 device."),
]
runs = []
for qid, q in prompts:
    res = agent.execute_cycle(q)
    H.show_agent(res, title=qid)
    runs.append({**H.agent_row(res, qid.split()[0]), "prompt_tokens": res["llm_telemetry"]["prompt_tokens"],
                 "completion_tokens": res["llm_telemetry"]["candidates_tokens"]})
df_runs = pd.DataFrame(runs)
H.show(df_runs)
H.grouped_bar(df_runs, "id", ["llm_ms", "bq_ms"],
              H.t("질의 시나리오별 Gemini 2-Pass 추론 시간 vs BigQuery SQL/GQL 실행 시간 (ms)",
                  "Gemini 2-Pass LLM Inference vs. BigQuery SQL/GQL Latency by Scenario (ms)"))"""),
        md(S4_AGENTS_MD_KO if ko else S4_AGENTS_MD_EN),
        nav_footer(
            4, lang,
            qa_items=[
                (
                    "AI FDE 에이전트는 위약금 계산 오류나 미등록 단말기/고객 환각을 어떻게 방지하며, 양대 그래프 엔진(`bigquery` / `spanner`)을 어떻게 전환하나요?" if ko
                    else "How does the AI FDE Agent prevent penalty calculation errors and hallucinated entities, and how does it switch between `bigquery` and `spanner` engines?",
                    "`resolve_params()`가 실시간 카탈로그(`get_live_catalog()`)와 대조하여 미등록 단말·요금제·고객 ID를 즉시 필터링하고, 모든 금액 계산과 그래프 탐색은 8종 MCP 도구에서 `engine='bigquery'`(기본값) 또는 `engine='spanner'`를 지정해 결정론적 SQL/GQL로만 수행하며, 필수 정보 누락 시 `INSUFFICIENT_PARAMETERS`, 조건 불일치 시 `MATCH_NOT_FOUND` 상태를 반환합니다." if ko
                    else "`resolve_params()` validates extracted slots against the live catalog (`get_live_catalog()`), delegates all SQL/GQL execution to the 8 MCP tools across `engine='bigquery'` (default) or `engine='spanner'`, and enforces explicit `INSUFFICIENT_PARAMETERS` and `MATCH_NOT_FOUND` guardrail states."
                ),
            ],
            findings=[
                "`CUST_DEMO_001` 경과일 시뮬레이션(30~200일) 결과, 위약금은 30일차 `250,000원`에서 120일차 `100,000원`, 179일차 `1,667원`으로 선형 감소하며 180일 도래 즉시 `0원`(`EXEMPT_RETENTION_COMPLETED`)으로 전환됩니다." if ko
                else "Across elapsed days 30..200 for `CUST_DEMO_001`, the prorated penalty decreases linearly from `250,000 KRW` (day 30) to `100,000 KRW` (day 120) and `1,667 KRW` (day 179), dropping to `0 KRW` (`EXEMPT_RETENTION_COMPLETED`) at day 180.",
                "런타임 도메인 MCP 3종(`mcp_lookup_customer_profile`, `mcp_calculate_penalty_rule`, `mcp_query_graph_and_wiki`)을 `engine='bigquery'`(기본값)와 `engine='spanner'`(`100 PU`) 양쪽에서 실행한 결과 동일한 반환 행 수(`result_parity=True`)와 SHA-256 앵커 정합성을 확인했습니다." if ko
                else "Executing all 3 runtime domain MCP tools across `engine='bigquery'` (default) and `engine='spanner'` (`100 PU`) confirmed identical row counts (`result_parity=True`) and SHA-256 anchor grounding.",
                "Golden CQ(`CQ-01`~`CQ-03`)는 모두 `GROUNDED` 상태와 함께 정확한 금액(`575,000원`, `100,000원`, `0원`) 및 SHA-256 청크 앵커·BigQuery Job ID를 인용하여 답변했고, `BC-PARAM`과 `BC-NOTFOUND`는 수치 환각 없이 차단되었습니다." if ko
                else "All Golden CQs (`CQ-01`–`CQ-03`) returned `GROUNDED` responses citing exact SQL-computed figures (`575,000 KRW`, `100,000 KRW`, `0 KRW`), while `BC-PARAM` and `BC-NOTFOUND` triggered their guardrail states with 0 hallucinated figures."
            ],
            next_steps=[
                "마지막 단계인 `Stage 5 (리니지·검증)` 노트북으로 이동하여 원천 파일부터 CQ 답변까지의 엔드투엔드 데이터 리니지 그래프와 Golden CQ 5종 / Boundary 50회 반복 벤치마크 배포 게이트를 검증하세요." if ko
                else "Proceed to the final `Stage 5 (Verify & Evaluate)` notebook to inspect the end-to-end data lineage graph, Golden CQ re-verification, and the 50-trial boundary benchmark release gate."
            ],
        ),
    ]


S4_AGENTS_MD_KO = """### 6. Wiki Agent와 BQG Agent의 차이 및 사용량 보고

방법론은 두 에이전트를 근거를 가져오는 곳으로 구분한다.

| 구분 | Wiki Agent (방법론) | BQG Agent (방법론) |
| :--- | :--- | :--- |
| 근거 | GCS의 온톨로지 위키 파일 | BigQuery Property Graph |
| 절차 | GCS 위키 목차 읽기 → Flash가 엔티티·개념 파일 선택 → 선택한 파일(+관계 1단계) 읽기 → Flash가 파일 내용만으로 답변 | 슬롯 추출 → Property Graph에 파라미터 GQL 조회 → 코드로 계산 → 답변 |
| BigQuery·그래프 | 사용하지 않음 | 사용 |
| 사용량 보고 | 호출별 토큰(Vertex `usageMetadata`: 입력·출력·thinking), 단계별 지연시간 | 같은 항목 + 쿼리별 BigQuery job ID, 행 수, 소요 ms |

Wiki Agent를 따로 두는 이유는 물리 그래프 없이 Stage 2 산출물만으로 규정·산식 CQ에 답할 수 있는지 확인하기 위해서다.

**스타터 구현 (방법론과 다름)**
- 스타터에는 GCS Wiki Agent가 없다. GCS 온톨로지는 `gs://seanjung-poc-starter-ontology/ontology/{entities.md, concepts.md, rules.md, summary.md, ontology.jsonld}`이며, 엔티티별 파일이 아니라 집계 파일이다.
- Lite 트랙(`src/agent/reasoning_engine.py` `_lite_cycle`): `tb_doc_chunks` 전체 행을 Gemini 컨텍스트에 넣고 청크 ID 인용을 검사한다. BigQuery 조회 1회, 그래프는 쓰지 않는다.
- Standard/Full 트랙(이 노트북): `AiFdeAgentEngine`이 MCP 도구를 호출하고, 도구는 실제 BigQuery/Spanner 쿼리를 실행한다. 각 결과에 `bq_jobs`(job_id, rows, elapsed_ms, status, sql)와 `executed_sql`이 담긴다. bytes processed와 cache hit는 스타터 기록에 없다.
- 토큰: `llm_telemetry.prompt_tokens`/`candidates_tokens`(Vertex `usageMetadata`의 `promptTokenCount`/`candidatesTokenCount`, 분해·합성 호출 합계). thinking 토큰은 스타터가 기록하지 않는다.

**위 실행 결과에서 확인할 곳**: 섹션 3의 MCP 호출별 표(job ID, rows, elapsed ms), 섹션 5의 `df_runs`(prompt/completion 토큰, BigQuery job 수, LLM ms와 BigQuery ms)."""
S4_AGENTS_MD_EN = """### 6. Wiki Agent vs BQG Agent, and usage reporting

The method separates the two agents by where they get evidence.

| Item | Wiki Agent (method) | BQG Agent (method) |
| :--- | :--- | :--- |
| Evidence | Ontology wiki files on GCS | BigQuery Property Graph |
| Steps | Read the wiki index on GCS → Flash selects entity/concept files → read those files (+1 hop of relations) → Flash answers from file content only | Slot extraction → parameterized GQL over the property graph → calculation in code → answer |
| BigQuery and graph | Not used | Used |
| Usage reported | Tokens per call (Vertex `usageMetadata`: prompt, completion, thinking) and latency per step | Same, plus BigQuery job ID, rows and elapsed ms per query |

A separate Wiki Agent checks whether Stage 2 output alone, without the physical graph, can answer rule and formula CQs.

**Starter implementation (differs from the method)**
- The starter has no GCS Wiki Agent. Its GCS ontology is `gs://seanjung-poc-starter-ontology/ontology/{entities.md, concepts.md, rules.md, summary.md, ontology.jsonld}`: aggregate files, not one file per entity.
- Lite track (`src/agent/reasoning_engine.py` `_lite_cycle`): puts all `tb_doc_chunks` rows into the Gemini context and checks chunk ID citations. One BigQuery read, no graph.
- Standard/Full track (this notebook): `AiFdeAgentEngine` calls MCP tools that run real BigQuery/Spanner queries. Each result carries `bq_jobs` (job_id, rows, elapsed_ms, status, sql) and `executed_sql`. Bytes processed and cache hit are not in the starter's record.
- Tokens: `llm_telemetry.prompt_tokens` / `candidates_tokens` (`promptTokenCount` / `candidatesTokenCount` from Vertex `usageMetadata`, summed over the decomposition and synthesis calls). The starter does not record thinking tokens.

**Where to read these values above**: the per-call table in Section 3 (job ID, rows, elapsed ms) and `df_runs` in Section 5 (prompt/completion tokens, BigQuery job count, LLM ms vs BigQuery ms)."""

H_LINEAGE_MD_KO = ("#### 스튜디오 리니지 DAG (`config/lineage_spec.json`) 실측\n"
                   "스튜디오 `Stage 5` 리니지와 같은 엔진(`src/lineage/lineage_engine.py`)입니다. "
                   "볼륨은 BigQuery `__TABLES__` 행 수, GCS 객체 수, `INFORMATION_SCHEMA.PROPERTY_GRAPHS` 노드·엣지 테이블 수를 지금 조회한 값이며, 실패하면 `lookup failed`로 남습니다.\n\n"
                   "**구조 원칙 (방법론)**: 정형 테이블은 테이블당 박스 1개, 엣지 테이블은 종류당 박스 1개로 그린다. "
                   "비정형 문서는 RAW → parsed → 재추출 게이트 → latest → 온톨로지 문서당 박스 1개로 흐르고, Wiki Agent 입력은 GCS의 온톨로지 latest다. 원격 MCP 서버 박스는 그리지 않는다.\n\n"
                   "**스타터 스펙**: 정형 테이블(`RAW_TB_*`)과 엣지 테이블(`TR_EDGE_*`)은 각각 박스 1개이고, 그래프 계층에 테이블별 노드 레이블 박스(`SEM_NODE_*`)가 따로 있다. "
                   "비정형 문서는 가이드 박스 2개 → 청커(`tb_doc_chunks`) → GCS `parsed/`와 위키 박스 1개(`gs://{bucket}/ontology/`)로 흐른다. "
                   "재추출 게이트, `latest` 승격, 온톨로지 문서별 박스, Wiki Agent 박스는 없고 원격 MCP 서버 박스도 없다.")
H_LINEAGE_MD_EN = ("#### Studio lineage DAG (`config/lineage_spec.json`), measured\n"
                   "Same engine as the studio `Stage 5` lineage (`src/lineage/lineage_engine.py`). "
                   "Volumes are BigQuery `__TABLES__` row counts, GCS object counts and node/edge table counts from `INFORMATION_SCHEMA.PROPERTY_GRAPHS`, queried now; a failed lookup stays `lookup failed`.\n\n"
                   "**Structure principle (method)**: one box per structured table and one box per edge-table kind. "
                   "Unstructured documents flow RAW → parsed → re-extraction gate → latest → one box per ontology document; the Wiki Agent input is the ontology latest on GCS. The remote MCP server is not drawn as a box.\n\n"
                   "**Starter spec**: structured tables (`RAW_TB_*`) and edge tables (`TR_EDGE_*`) have one box each, and the graph layer has a separate node-label box per table (`SEM_NODE_*`). "
                   "Unstructured documents flow from 2 guide boxes → chunker (`tb_doc_chunks`) → GCS `parsed/` and one wiki box (`gs://{bucket}/ontology/`). "
                   "There is no re-extraction gate, no `latest` promotion, no per-document ontology box, no Wiki Agent box and no remote MCP server box.")

S5_EVAL_MD_KO = ("#### 평가 표시 순서: A 전체 결과 → B CQ별 검증 → C 루브릭 기준\n"
                 "A는 통과 수, 루브릭 평균, 감점 CQ 수, 축별 평균이다. B는 CQ마다 기대값과 검증 SQL 결과, 점수·판정·감점 수, "
                 "근거(인용 청크, 검증 job ID, 에이전트 BigQuery job 수, 심사 요약)와 실제 답변 발췌다. C는 루브릭 축 정의다. "
                 "값은 모두 `data/output/cq_benchmark_report.json`에서 읽는다. 스타터 리포트의 루브릭 설명은 영문만 있다"
                 "(`name_ko`, `desc_ko`, `judge_instructions_ko` 필드 없음). 답변 원문은 한국어로 저장되어 있어 영문 노트북은 답변 발췌 대신 심사 요약만 보여준다. "
                 "마지막으로 `CQ-02`를 지금 다시 실행해 채점 조건을 확인한다.")
S5_EVAL_MD_EN = ("#### Evaluation order: A overall results → B per-CQ verification → C rubric criteria\n"
                 "A is the pass count, rubric average, number of CQs with deductions and per-axis averages. B is, per CQ, the expected value and "
                 "verification SQL result, score, verdict and deduction count, and evidence (cited chunk, verification job ID, agent BigQuery job count, judge summary). "
                 "C is the rubric axis definitions. All values are read from `data/output/cq_benchmark_report.json`. "
                 "The starter report stores rubric descriptions in English only (no `name_ko`, `desc_ko`, `judge_instructions_ko` fields). "
                 "The answer text is stored in Korean, so the Korean notebook adds an answer excerpt per CQ and this English notebook shows the judge summary only. "
                 "Finally, `CQ-02` is re-run now to check the grading conditions.")


def build_stage5(lang="ko"):
    ko = lang == "ko"
    banner_file = "stage5_lineage_eval_flow_ko.png" if ko else "stage5_lineage_eval_flow_en.png"
    rv = report_values()
    return [
        md(f"""{nav_header(5, lang)}

---

# {"Stage 5. [검증 & 배포 게이트] End-to-End 데이터 리니지 · Golden CQ 감사 & Boundary 50회 벤치마크" if ko else "Stage 5. [Verify & Gate] End-to-End Data Lineage, Golden CQ Audit & 50-Trial Boundary Benchmark"}
## {"Step 5.1 원천 파일→청크→규칙→약정→CQ 엔드투엔드 리니지 검증 · Step 5.2 Golden CQ 5종 및 Boundary 10건×5회(50 Trials) 배포 게이트" if ko else "Step 5.1 Source File → Chunk → Rule → Contract → CQ Lineage · Step 5.2 5 Golden CQs & 10×5 Boundary Benchmark Release Gate"}

{("Stage 5는 전체 엔지니어링 흐름의 최종 단계인 **Phase 8(검증 및 배포 게이트)**을 수행합니다. `mcp_stage5_lineage_and_eval`과 `pipeline/validator.py`를 통해 **(1) 원천 CSV/가이드 파일 → SHA-256 청크 → 도메인 규칙 → 고객 약정 → Golden CQ 답변으로 이어지는 엔드투엔드 데이터 리니지**를 추적하고, **(2) 독립 검증 SQL(`verification_sql`) 대조 기반 Golden CQ 5종 전수 감사**, **(3) 경계 조건 10건 × 5회 반복(총 50 Trials) 안정성·일관성·의도 유지율 평가**, **(4) Gate 1 ~ Gate 5 프로덕션 배포 승인 판정**을 완결합니다."
  if ko else
  "Stage 5 completes **Phase 8 (Verification & Release Gate)**. Using `mcp_stage5_lineage_and_eval` and `pipeline/validator.py`, we verify **(1) the End-to-End Data Lineage (`Source File → DocChunk → DomainRule → CustomerContract → Golden CQ`)**, **(2) deterministic SQL ground-truth auditing across all 5 Golden CQs**, **(3) 10 Boundary Cases × 5 repeated trials (50 live runs) for success, consistency, and intent stability**, and **(4) the Gate 1–5 Production Release Readiness Checklist**.")}

![Stage 5 Lineage and Release Gate Architecture Flow](attachment:{banner_file})"""),
        code(_bootstrap_code(lang, with_agent=True)),
        md(f"### 1. {'[Phase 8a: 엔드투엔드 데이터 리니지 검증] `mcp_stage5_lineage_and_eval` 실행 · 리니지 조인(`%%bqsql`) · 멀티파타이트 리니지 설계 도식' if ko else '[Phase 8a: End-to-End Data Lineage Verification] `mcp_stage5_lineage_and_eval`, Lineage Join (`%%bqsql`) & Multipartite Lineage Graph'}"),
        code("""res_s5 = server.execute_tool("mcp_stage5_lineage_and_eval", {"steps": ["build_4tier_lineage", "run_golden_cq_suite", "diagnose_boundary_failures"]})
H.show_tool(res_s5)"""),
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
H.draw_graph(lnodes, ledges,
             H.t("End-to-End 데이터 리니지 멀티파타이트 그래프 (Source File → DocChunk → DomainRule → Contract → CQ)",
                 "End-to-End Data Lineage Multipartite Graph (Source File → DocChunk → DomainRule → Contract → CQ)"),
             layout="layers", figsize=(12, 6.0),
             legend={"Tier 0 Source File": "#5F6368", "Tier 1 DocChunk": "#9334E6", "Tier 2 DomainRule": "#F9AB00",
                     "Tier 3 Contract": "#1A73E8", "Tier 4 Golden CQ": "#188038"})"""),
        md(H_LINEAGE_MD_KO if ko else H_LINEAGE_MD_EN),
        code("""from src.lineage.lineage_engine import LineageEngine
lg = LineageEngine(str(H.ROOT / "config" / "lineage_spec.json"), {
    "project_id": server.project_id, "fq": server.fq, "dataset_id": server.fq.split(".", 1)[1],
    "bucket": server.gcs_bucket, "model": agent.model_name,
    "spanner_instance": server.spanner_instance_id, "spanner_database": server.spanner_database_id}).build_graph()
H.md(f"**nodes `{lg['stats']['total_nodes']}` · edges `{lg['stats']['total_edges']}` · categories `{lg['stats']['total_categories']}` · "
     f"measured `{lg['metadata']['live_nodes']}/{lg['metadata']['bq_nodes']}` · errors `{lg['metadata']['bq_error'] or 0}`**")
H.show(pd.DataFrame([{"category": n["cat"], "node": n["id"], "volume": n["volume_en"], "measured": n["live"], "source": n["live_src"]}
                     for n in lg["nodes"] if n["live_src"]]))"""),
        md(f"### 2. {'[Phase 8b: Golden CQ 5종 정량 감사 (`pipeline/validator.py`)] 벤치마크 리포트 분석 및 실시간 에이전트 4대 채점 조건 재검증 (`recheck_cq`)' if ko else '[Phase 8b: 5 Golden CQs Deterministic Audit (`pipeline/validator.py`)] Benchmark Report & Live Agent Re-Verification (`recheck_cq`)'}"),
        md(S5_EVAL_MD_KO if ko else S5_EVAL_MD_EN),
        code("""df_cq = pd.DataFrame(cq_rep["test_results"])
H.md(H.t("#### A. 전체 결과", "#### A. Overall results"))
H.md(f"**Golden CQ Benchmark `{cq_rep['benchmark_id']}`** · Evaluated `{cq_rep['evaluated_at']}` · Model `{cq_rep['model']}` · Passed **`{cq_rep['passed']}/{cq_rep['total_cqs']} ({cq_rep['accuracy_rate']}%)`** · "
     f"Rubric avg `{cq_rep['rubric_avg_total']}` · CQs with deductions `{sum(1 for r in cq_rep['test_results'] if r['rubric']['deductions'])}` · LLM tokens `{cq_rep['llm_tokens_total']:,}`")
H.show(pd.DataFrame([cq_rep["rubric_axis_avg"]]))

H.md(H.t("#### B. CQ별 검증 (점수 · 근거 · 실제 답변)", "#### B. Per-CQ verification (score and evidence)"))
df_cq["score"] = df_cq["rubric"].map(lambda r: r["scores"]["total"])
df_cq["verdict"] = df_cq["rubric"].map(lambda r: r["verdict"])
df_cq["deductions"] = df_cq["rubric"].map(lambda r: len(r["deductions"]))
df_cq["judge_summary"] = df_cq["rubric"].map(lambda r: r["summary"])
df_cq["agent_bq_jobs"] = df_cq["agent_bq_job_ids"].map(len)
H.show(df_cq, ["cq_id", "status", "expected_math", "verification_sql_result", "verification_job_id", "score", "verdict", "deductions",
               "grounded_chunk", "agent_bq_jobs", "llm_tokens", "elapsed_s", "judge_summary"])
""" + ("""for r in cq_rep["test_results"]:
    H.md(f"**{r['cq_id']}** · {r['query']}\\n\\n" + "\\n".join("> " + ln.lstrip("# ") if ln.strip() else ">" for ln in r["answer_excerpt"].splitlines()[:10]))
""" if ko else "") + """H.bar(df_cq, "cq_id", "elapsed_s", H.t("Golden CQ별 에이전트 2-Pass 응답 소요 시간 (초)", "Golden CQ Agent 2-Pass Elapsed Time (s)"), fmt="{:.2f}")

H.md(H.t("#### C. 루브릭 기준", "#### C. Rubric criteria"))
H.show(pd.DataFrame(cq_rep["rubric"]))

cqs = H.read_json("data/input/04_cq/golden_competency_questions.json")
res_cq2, df_chk = H.recheck_cq(cqs[1], agent)
H.show_agent(res_cq2, title=H.t("실시간 재검증 (Live Re-Audit): CQ-02", "Live Re-Audit: CQ-02"))
H.show(df_chk)"""),
        md(f"### 3. {'[Phase 8c: Boundary 10건 × 5회 반복(50 Trials) 안정성 평가 & Gate 1~5 배포 승인 판정]' if ko else '[Phase 8c: 10 Boundary Cases × 5 Trials (50 Runs) Stability Evaluation & Gate 1–5 Release Verdict]'}"),
        code("""b_rep = H.read_json("data/output/boundary_benchmark_results.json")
df_bc = pd.DataFrame(b_rep["cases"])
H.md(f"**Boundary Benchmark `{b_rep['benchmark_id']}`** · Trials=`{b_rep['total_trials']}` · "
     f"avg_success_rate=`{b_rep['avg_success_rate']}%` · avg_consistency_rate=`{b_rep['avg_consistency_rate']}%` · "
     f"avg_intent_stability=`{b_rep['avg_intent_stability']}%`")
H.show(df_bc, ["case_id", "root_cause_code", "missing_context", "trials", "passed_trials", "success_rate", "consistency_rate", "intent_stability"])
H.grouped_bar(df_bc, "case_id", ["success_rate", "consistency_rate", "intent_stability"],
              H.t("Boundary 10건 × 5회 반복 평가 지표 비교 (%)", "Boundary 10 Cases × 5 Trials Metrics (%)"))
df_tax = df_bc.groupby("root_cause_code", as_index=False).agg(
    cases=("case_id", "count"), avg_success=("success_rate", "mean"),
    avg_consistency=("consistency_rate", "mean"), avg_intent_stability=("intent_stability", "mean"))
H.show(df_tax)
H.md(H.t("#### Gate 1 ~ Gate 5 프로덕션 배포 준비 완료 최종 판정표", "#### Gate 1 – Gate 5 Production Release Readiness Verdict"))
H.show(H.gate_checklist_table())"""),
        nav_footer(
            5, lang,
            qa_items=[
                (
                    "`pipeline/validator.py`는 에이전트 답변의 정확성과 환각 부재를 어떤 기준으로 채점하나요?" if ko
                    else "How does `pipeline/validator.py` grade agent accuracy and verify zero hallucination?",
                    "각 Golden CQ마다 (1) BigQuery에서 독립 실행한 `verification_sql` 결과가 `expected_math`와 일치하는지, (2) 에이전트 답변 본문에 정답 수치가 포함(`_has` 정규식)되는지, (3) 지정된 `DOC_CHUNK`를 인용했는지, (4) `answer_status == GROUNDED`인지 확인하고, (5) 최종 답변을 LLM 루브릭(`_judge`)으로 채점하며, CQ 간 답변 3-gram 중복이 높으면 실패로 처리합니다." if ko
                    else "For every Golden CQ it checks (1) independent BigQuery `verification_sql` matches `expected_math`, (2) the answer contains the expected values (`_has` regex), (3) the required `DOC_CHUNK` is cited, (4) `answer_status == GROUNDED`, and (5) scores the final answer with an LLM rubric (`_judge`); answers that are near-duplicates across CQs (3-gram overlap) fail."
                ),
            ],
            findings=[
                "엔드투엔드 데이터 리니지 조인(`df_lineage`, 18행)을 통해 원천 파일(`sample_policy_guide.md`, `sample_welfare_exemption_guide.md`, `customer_contracts.csv`, `domain_rules.csv`)부터 `DOC_CHUNK_001~005`, `RULE_*` 4종, 고객 약정 6건, `CQ-01~05`까지의 전 구간 추적성이 확인되었습니다." if ko
                else "The end-to-end lineage join (`df_lineage`, 18 rows) traces every Golden CQ answer back through customer contracts, codified domain rules, and SHA-256 `DOC_CHUNK` anchors to the raw CSV and Markdown source files.",
                f"Golden CQ 리포트({rv['cq_at']}): {rv['cq_passed']}/{rv['cq_total']} 통과(`{rv['cq_rate']}%`), 루브릭 평균 `{rv['cq_rubric']}`. `CQ-02` 실시간 재검증 결과는 위 표를 따릅니다. 스타터 CQ는 단일 값 질문이라 만점이 나오기 쉽습니다." if ko
                else f"Golden CQ report ({rv['cq_at']}): {rv['cq_passed']}/{rv['cq_total']} passed (`{rv['cq_rate']}%`), rubric average `{rv['cq_rubric']}`. See the table above for the live `CQ-02` re-check. Starter CQs ask for single values, so full scores are easy to reach.",
                f"Boundary 리포트({rv['b_at']}, {rv['b_trials']} Trials): 평균 성공률 `{rv['b_success']}%`, 응답 일관성 `{rv['b_consistency']}%`, 의도 안정성 `{rv['b_intent']}%`. Gate 1 ~ Gate 5 판정은 위 판정표를 따릅니다." if ko
                else f"Boundary report ({rv['b_at']}, {rv['b_trials']} trials): average success `{rv['b_success']}%`, consistency `{rv['b_consistency']}%`, intent stability `{rv['b_intent']}%`. The Gate 1–5 verdict follows the table above."
            ],
            next_steps=[
                "5-Stage 에이전틱 온톨로지 전 과정 워크스루를 완료했습니다! 상단 또는 하단 링크를 통해 `0. 전체 흐름 초기 화면`이나 각 Stage 노트북(한/영)으로 자유롭게 이동하거나, 자체 도메인 CSV/가이드 데이터를 `data/input/`에 적용해 보세요." if ko
                else "You have completed the full 5-Stage Agentic Ontology walkthrough! Use the navigation links below to revisit `0. Overview Home` or any Stage notebook (KO/EN), or replace `data/input/` with your own domain tables and policy guides."
            ],
        ),
    ]
