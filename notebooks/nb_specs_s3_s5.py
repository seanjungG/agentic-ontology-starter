# -*- coding: utf-8 -*-
"""Cell builders for Stage 3, Stage 4, and Stage 5 notebooks (KO/EN).

Aligned with Phases 5, 6, 7, and 8 of the 8-Phase Engineering Flow:
  - Stage 3: Phase 5. 구축 (Physical Property Graph Construction & ISO GQL)
  - Stage 4: Phase 6. 에이전트 구축 (Agent & 8-Tool MCP Setup) & Phase 7. 답변 (Grounded Answering)
  - Stage 5: Phase 8. 검증 (4-Tier Lineage, Golden CQ Audit & 50-Trial Release Gate)
"""
from nb_specs_s0_s2 import FQ, GRAPH, _bootstrap_code, code, md, nav_footer, nav_header


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
        nav_footer(
            3, lang,
            qa_items=[
                (
                    "Zero-ETL BigQuery Property Graph는 기존 RDB 조인 대비 어떤 구조적 이점을 제공하나요?" if ko
                    else "What structural advantage does Zero-ETL BigQuery Property Graph provide over traditional relational joins?",
                    "원천 DW 테이블 6종과 엣지 테이블 4종을 별도 그래프 DB로 복제하지 않고 `CREATE OR REPLACE PROPERTY GRAPH` 뷰로 선언하여, 단일 ISO GQL(`MATCH ... -{1,2}-`) 문장과 명시적 바인딩 변수(`$customer_id`, `$target_plan_id`, `$elapsed_days`)만으로 고객 약정·단말·요금제·지원금·비즈니스 규칙·원문 청크 경로를 동시에 탐색할 수 있습니다." if ko
                    else "By projecting 6 node tables and 4 edge tables via `CREATE OR REPLACE PROPERTY GRAPH` without data duplication, a single parameterized ISO GQL statement traverses contracts, devices, plans, subsidies, rules, and policy chunks."
                ),
            ],
            findings=[
                "`STARTER_ONTOLOGY_GRAPH`는 6개 노드 레이블(총 31행, 중복 키 `0건`)과 4개 엣지 레이블(총 31행)로 구성되며, 활성 연결 경로에서 25개 노드와 29개 방향성 엣지가 추출되었습니다." if ko
                else "`STARTER_ONTOLOGY_GRAPH` comprises 6 node labels (31 rows, `0` duplicate keys) and 4 edge labels (31 rows), yielding 25 connected nodes and 29 directed edges.",
                "바인딩 변수(`c.customer_id='CUST_DEMO_001'`, `t.plan_id='PLAN-5G-37'`, `elapsed_days=120`)를 적용한 ISO GQL 다이아몬드 쿼리(`GQL-04`)로 일할 위약금(`(500,000 - 200,000) × 60 / 180 = 100,000원`)을 단일 GQL 문장으로 산출했습니다." if ko
                else "Using an ISO GQL diamond pattern (`GQL-04`) bound to `customer_id='CUST_DEMO_001'`, `target_plan_id='PLAN-5G-37'`, and `elapsed_days=120`, we computed the prorated downgrade penalty (`100,000 KRW`) in a single GQL query.",
                "Gemini `nl2gql`은 스키마 내 다중 홉 질문 2건을 바인딩 변수 및 실행 가능한 ISO GQL로 변환(`SUCCESS`)하고, 스키마에 없는 기지국 품질 질문은 `answerable=false`로 차단했습니다." if ko
                else "Gemini `nl2gql` translated 2 in-schema questions into executable ISO GQL (`SUCCESS`) with extracted bound variables and blocked the out-of-schema base-station query with `answerable=false`."
            ],
            next_steps=[
                "다음 단계인 `Stage 4 (에이전트·답변)` 노트북으로 이동하여 이 Property Graph와 BigQuery 원장을 호출하는 8종 모듈형 MCP 서버와 2-Pass AI FDE 에이전트 구축 및 답변 생성 과정을 확인하세요." if ko
                else "Proceed to `Stage 4 (Build Agent & Answer)` to see how the 8-Tool MCP Server and 2-Pass AI FDE Agent orchestrate SQL and ISO GQL queries to generate grounded answers."
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

{("Stage 4는 방법론의 **Phase 6(에이전트 구축)**과 **Phase 7(답변 생성)**을 구현합니다. LLM이 위약금이나 지원금을 암산하거나 존재하지 않는 요금제를 환각하지 않도록, **(1) BigQuery 실시간 카탈로그 기반 슬롯 검증(`resolve_params`)**, **(2) 결정론적 SQL 및 바인딩 변수 기반 ISO GQL을 실행하는 8종 모듈형 MCP 도구(`DomainMcpServer`)**, **(3) 4단계 라이프사이클로 동작하는 2-Pass Gemini(`gemini-3.8-flash`) 추론 엔진(`AiFdeAgentEngine`)**을 구축하고 정상 질의(`GROUNDED`)와 경계 질의(`INSUFFICIENT_PARAMETERS`, `MATCH_NOT_FOUND`)에 대한 답변을 생성합니다."
  if ko else
  "Stage 4 implements **Phase 6 (Agent & MCP Setup)** and **Phase 7 (Grounded Answering)**. To prevent LLM math errors or entity hallucinations, we combine **(1) Live BigQuery Catalog Slot Validation (`resolve_params`)**, **(2) the 8-Tool Modular MCP Server (`DomainMcpServer`) executing deterministic SQL and parameterized ISO GQL**, and **(3) the 4-Step, 2-Pass Gemini (`gemini-3.8-flash`) Reasoning Engine (`AiFdeAgentEngine`)**, verifying both `GROUNDED` answers and boundary guardrails (`INSUFFICIENT_PARAMETERS`, `MATCH_NOT_FOUND`).")}

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
        md(f"### 4. {'[Phase 7: 2-Pass 에이전트 End-to-End 답변 생성] Golden CQ(`GROUNDED`) 및 경계 조건(`INSUFFICIENT_PARAMETERS`, `MATCH_NOT_FOUND`) 4단계 트레이스' if ko else '[Phase 7: End-to-End 2-Pass Agent Answering] Golden CQs (`GROUNDED`) & Boundary Guardrails (`INSUFFICIENT_PARAMETERS`, `MATCH_NOT_FOUND`)'}"),
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
    runs.append(H.agent_row(res, qid.split()[0]))
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
    runs.append(H.agent_row(res, qid.split()[0]))
df_runs = pd.DataFrame(runs)
H.show(df_runs)
H.grouped_bar(df_runs, "id", ["llm_ms", "bq_ms"],
              H.t("질의 시나리오별 Gemini 2-Pass 추론 시간 vs BigQuery SQL/GQL 실행 시간 (ms)",
                  "Gemini 2-Pass LLM Inference vs. BigQuery SQL/GQL Latency by Scenario (ms)"))"""),
        nav_footer(
            4, lang,
            qa_items=[
                (
                    "AI FDE 에이전트는 위약금 계산 오류나 미등록 단말기/고객 환각을 어떻게 방지하나요?" if ko
                    else "How does the AI FDE Agent prevent penalty calculation errors and hallucinated devices or customers?",
                    "`resolve_params()`가 BigQuery 실시간 카탈로그(`get_live_catalog()`)와 대조하여 미등록 단말·요금제·고객 ID를 즉시 필터링하고, 모든 금액 계산은 LLM이 아닌 `mcp_calculate_penalty_rule` 내부 BigQuery SQL 산식으로만 수행하며, 필수 정보 누락 시 `INSUFFICIENT_PARAMETERS`, 조건 불일치 시 `MATCH_NOT_FOUND` 상태를 반환합니다." if ko
                    else "`resolve_params()` validates extracted slots against the live BigQuery catalog (`get_live_catalog()`), delegates all arithmetic to deterministic BigQuery SQL inside `mcp_calculate_penalty_rule`, and enforces explicit `INSUFFICIENT_PARAMETERS` and `MATCH_NOT_FOUND` guardrail states."
                ),
            ],
            findings=[
                "`CUST_DEMO_001` 경과일 시뮬레이션(30~200일) 결과, 위약금은 30일차 `250,000원`에서 120일차 `100,000원`, 179일차 `1,667원`으로 선형 감소하며 180일 도래 즉시 `0원`(`EXEMPT_RETENTION_COMPLETED`)으로 전환됩니다." if ko
                else "Across elapsed days 30..200 for `CUST_DEMO_001`, the prorated penalty decreases linearly from `250,000 KRW` (day 30) to `100,000 KRW` (day 120) and `1,667 KRW` (day 179), dropping to `0 KRW` (`EXEMPT_RETENTION_COMPLETED`) at day 180.",
                "Golden CQ(`CQ-01`~`CQ-03`)는 모두 `GROUNDED` 상태와 함께 정확한 금액(`575,000원`, `100,000원`, `0원`) 및 SHA-256 청크 앵커·BigQuery Job ID를 인용하여 답변했습니다." if ko
                else "All Golden CQs (`CQ-01`–`CQ-03`) returned `GROUNDED` responses citing exact SQL-computed figures (`575,000 KRW`, `100,000 KRW`, `0 KRW`), SHA-256 chunk anchors, and BigQuery Job IDs.",
                "필수 슬롯 누락 질의(`BC-PARAM`)는 `INSUFFICIENT_PARAMETERS`로, 미등록 고객/단말 질의(`BC-NOTFOUND`)는 `MATCH_NOT_FOUND`로 정확히 분기하여 수치 환각을 차단했습니다." if ko
                else "Missing-slot queries (`BC-PARAM`) triggered `INSUFFICIENT_PARAMETERS` and unknown-entity queries (`BC-NOTFOUND`) triggered `MATCH_NOT_FOUND` with 0 hallucinated figures."
            ],
            next_steps=[
                "마지막 단계인 `Stage 5 (리니지·검증)` 노트북으로 이동하여 원천 파일부터 CQ 답변까지의 4-Tier 데이터 리니지 그래프와 Golden CQ 5종 / Boundary 50회 반복 벤치마크 배포 게이트를 검증하세요." if ko
                else "Proceed to the final `Stage 5 (Verify & Evaluate)` notebook to inspect the 4-Tier end-to-end data lineage graph, Golden CQ re-verification, and the 50-trial boundary benchmark release gate."
            ],
        ),
    ]


def build_stage5(lang="ko"):
    ko = lang == "ko"
    banner_file = "stage5_lineage_eval_flow_ko.png" if ko else "stage5_lineage_eval_flow_en.png"
    return [
        md(f"""{nav_header(5, lang)}

---

# {"Stage 5. [검증 & 배포 게이트] 4-Tier End-to-End 데이터 리니지 · Golden CQ 감사 & Boundary 50회 벤치마크" if ko else "Stage 5. [Verify & Gate] 4-Tier End-to-End Data Lineage, Golden CQ Audit & 50-Trial Boundary Benchmark"}
## {"Step 5.1 원천 파일→청크→규칙→약정→CQ 4-Tier 리니지 검증 · Step 5.2 Golden CQ 5종 및 Boundary 10건×5회(50 Trials) 배포 게이트" if ko else "Step 5.1 Source File → Chunk → Rule → Contract → CQ Lineage · Step 5.2 5 Golden CQs & 10×5 Boundary Benchmark Release Gate"}

{("Stage 5는 전체 엔지니어링 흐름의 최종 단계인 **Phase 8(검증 및 배포 게이트)**을 수행합니다. `mcp_stage5_lineage_and_eval`과 `pipeline/validator.py`를 통해 **(1) 원천 CSV/가이드 파일 → SHA-256 청크 → 도메인 규칙 → 고객 약정 → Golden CQ 답변으로 이어지는 4-Tier 데이터 리니지**를 추적하고, **(2) 독립 검증 SQL(`verification_sql`) 대조 기반 Golden CQ 5종 전수 감사**, **(3) 경계 조건 10건 × 5회 반복(총 50 Trials) 안정성·일관성·의도 유지율 평가**, **(4) Gate 1 ~ Gate 5 프로덕션 배포 승인 판정**을 완결합니다."
  if ko else
  "Stage 5 completes **Phase 8 (Verification & Release Gate)**. Using `mcp_stage5_lineage_and_eval` and `pipeline/validator.py`, we verify **(1) the 4-Tier End-to-End Data Lineage (`Source File → DocChunk → DomainRule → CustomerContract → Golden CQ`)**, **(2) deterministic SQL ground-truth auditing across all 5 Golden CQs**, **(3) 10 Boundary Cases × 5 repeated trials (50 live runs) for success, consistency, and intent stability**, and **(4) the Gate 1–5 Production Release Readiness Checklist**.")}

![Stage 5 Lineage and Release Gate Architecture Flow](attachment:{banner_file})"""),
        code(_bootstrap_code(lang, with_agent=True)),
        md(f"### 1. {'[Phase 8a: 4-Tier 데이터 리니지 검증] `mcp_stage5_lineage_and_eval` 실행 · 리니지 조인(`%%bqsql`) · 멀티파타이트 리니지 설계 도식' if ko else '[Phase 8a: 4-Tier Data Lineage Verification] `mcp_stage5_lineage_and_eval`, Lineage Join (`%%bqsql`) & Multipartite Lineage Graph'}"),
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
             H.t("4-Tier End-to-End 데이터 리니지 멀티파타이트 그래프 (Source File → DocChunk → DomainRule → Contract → CQ)",
                 "4-Tier End-to-End Data Lineage Multipartite Graph (Source File → DocChunk → DomainRule → Contract → CQ)"),
             layout="layers", figsize=(12, 6.0),
             legend={"Tier 0 Source File": "#5F6368", "Tier 1 DocChunk": "#9334E6", "Tier 2 DomainRule": "#F9AB00",
                     "Tier 3 Contract": "#1A73E8", "Tier 4 Golden CQ": "#188038"})"""),
        md(f"### 2. {'[Phase 8b: Golden CQ 5종 정량 감사 (`pipeline/validator.py`)] 벤치마크 리포트 분석 및 실시간 에이전트 4대 채점 조건 재검증 (`recheck_cq`)' if ko else '[Phase 8b: 5 Golden CQs Deterministic Audit (`pipeline/validator.py`)] Benchmark Report & Live Agent Re-Verification (`recheck_cq`)'}"),
        code("""df_cq = pd.DataFrame(cq_rep["test_results"])
H.md(f"**Golden CQ Benchmark `{cq_rep['benchmark_id']}`** · Evaluated `{cq_rep['evaluated_at']}` · Model `{cq_rep['model']}` · Passed **`{cq_rep['passed']}/{cq_rep['total_cqs']} ({cq_rep['accuracy_rate']}%)`**")
H.show(df_cq, ["cq_id", "category", "status", "verification_status", "grounded_chunk", "llm_tokens", "elapsed_s", "verification_job_id"])
H.bar(df_cq, "cq_id", "elapsed_s", H.t("Golden CQ별 에이전트 2-Pass 응답 소요 시간 (초)", "Golden CQ Agent 2-Pass Elapsed Time (s)"), fmt="{:.2f}")

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
                    "각 Golden CQ마다 (1) BigQuery에서 독립 실행한 `verification_sql` 결과가 `expected_math`와 일치하는지, (2) 에이전트 답변 본문에 모든 정답 수치가 정확히 포함(`_has` 정규식)되어 있는지, (3) 지정된 `DOC_CHUNK` 해시 앵커를 인용했는지, (4) `answer_status == GROUNDED`인지 4가지 조건을 동시에 검증합니다." if ko
                    else "For every Golden CQ, it checks 4 conditions simultaneously: (1) independent BigQuery `verification_sql` matches `expected_math`, (2) the agent's answer contains every expected numerical value (`_has` regex), (3) the required `DOC_CHUNK` is cited, and (4) `answer_status == GROUNDED`."
                ),
            ],
            findings=[
                "4-Tier 데이터 리니지 조인(`df_lineage`, 18행)을 통해 원천 파일(`sample_policy_guide.md`, `sample_welfare_exemption_guide.md`, `customer_contracts.csv`, `domain_rules.csv`)부터 `DOC_CHUNK_001~005`, `RULE_*` 4종, 고객 약정 6건, `CQ-01~05`까지의 전 구간 추적성이 확인되었습니다." if ko
                else "The 4-Tier lineage join (`df_lineage`, 18 rows) traces every Golden CQ answer back through customer contracts, codified domain rules, and SHA-256 `DOC_CHUNK` anchors to the raw CSV and Markdown source files.",
                "Golden CQ 5종(`CQ-01`~`CQ-05`) 벤치마크는 5건 전수 통과(`100.0%`)했으며, `CQ-02` 실시간 재검증(`recheck_cq`)에서도 4개 채점 항목 모두 `passed=True`를 기록했습니다." if ko
                else "All 5 Golden CQs (`CQ-01`–`CQ-05`) passed (`100.0%`), and the live `recheck_cq` audit on `CQ-02` passed all 4 verification checks (`passed=True`).",
                "Boundary 10건 × 5회 반복(`50 Trials`) 평가에서 평균 성공률 `98.0%`, 응답 일관성 `98.0%`, 도구 라우팅 의도 안정성 `96.0%`를 달성하여 Gate 1 ~ Gate 5 전 구간 `PASS`를 확인했습니다." if ko
                else "Across 10 boundary cases × 5 repeated trials (`50 Trials`), the agent achieved `98.0%` average success rate, `98.0%` consistency rate, and `96.0%` intent stability, passing all 5 production release gates (`Gate 1`–`Gate 5`)."
            ],
            next_steps=[
                "5-Stage 에이전틱 온톨로지 전 과정 워크스루를 완료했습니다! 상단 또는 하단 링크를 통해 `0. 전체 흐름 초기 화면`이나 각 Stage 노트북(한/영)으로 자유롭게 이동하거나, 자체 도메인 CSV/가이드 데이터를 `data/input/`에 적용해 보세요." if ko
                else "You have completed the full 5-Stage Agentic Ontology walkthrough! Use the navigation links below to revisit `0. Overview Home` or any Stage notebook (KO/EN), or replace `data/input/` with your own domain tables and policy guides."
            ],
        ),
    ]
