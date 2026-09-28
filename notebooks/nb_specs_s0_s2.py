# -*- coding: utf-8 -*-
"""Notebook cell specifications for Stage 0, Stage 1 (KO/EN), and Stage 2 (KO/EN)."""

FQ = "seanjung-poc.starter_ontology_dw"
GRAPH = f"{FQ}.STARTER_ONTOLOGY_GRAPH"


def md(text):
    return {"cell_type": "markdown", "metadata": {}, "source": text.strip() + "\n"}


def code(src):
    return {"cell_type": "code", "metadata": {}, "source": src.strip() + "\n", "outputs": [], "execution_count": None}


def build_stage0():
    return [
        md("""# 0. Overview — End-to-End Agentic Ontology Walkthrough
## 5-Stage × 9-Step Lifecycle · BigQuery Property Graph (ISO GQL) · AI FDE Agent

본 노트북은 **Agentic Ontology Starter Pack v2.0**의 전체 흐름(`0. Overview` + `Stage 1` ~ `Stage 5`)을 실환경 BigQuery(`seanjung-poc.starter_ontology_dw`)와 Vertex AI(`gemini-3.8-flash`) 위에서 한눈에 탐색·시각화·실행하는 종합 가이드입니다.

![Evolutionary Journey Overview](attachment:evolutionary_overview_flow.png)

| 트랙 (Track) | 실행 Stage 구성 | 대상 환경 및 목적 |
| :--- | :--- | :--- |
| **Track 1 · Lite** | `Stage 1 → Stage 2 → Stage 4` | 정형 그래프 없이 비정형 정책 문서 위키(3-Layer LLM-Wiki)만으로 즉시 에이전트 구동 |
| **Track 2 · Standard** | `Stage 1 → Stage 2 → Stage 3 → Stage 4` | 정형 DW 원장 4종 + 비정형 규칙을 듀얼 Property Graph(BigQuery / Spanner)로 결합 |
| **Track 3 · Full-Stack** | `Stage 1 → Stage 2 → Stage 3 → Stage 4 → Stage 5` | 4-Tier 데이터 리니지 및 Golden CQ 5건 / Boundary 10건 회귀 평가까지 전 주기 운영 |"""),
        code("""%load_ext bigframes
import nb_helpers as H
H.setup("ko")"""),
        md("### 1. BigQuery 데이터셋(`starter_ontology_dw`) 10개 물리 테이블 프로파일링 (`%%bqsql`)"),
        code(f"""%%bqsql df_tables
SELECT table_id, row_count, size_bytes,
  CASE WHEN STARTS_WITH(table_id, 'edge_') THEN 'edge'
       WHEN table_id IN ('tb_doc_chunks', 'tb_domain_rules') THEN 'knowledge'
       ELSE 'master' END AS kind
FROM `{FQ}.__TABLES__`
ORDER BY kind, table_id"""),
        code("""H.show(df_tables)
H.bar(df_tables, "table_id", "row_count", "starter_ontology_dw 테이블별 행 수 (실측)", horizontal=True)"""),
        md("### 2. BigQuery Property Graph(`STARTER_ONTOLOGY_GRAPH`) 전체 경로 추출 및 토폴로지 시각화 (`%%bqsql` + ISO GQL)"),
        code(f"""%%bqsql df_paths
GRAPH `{GRAPH}`
MATCH p = (a)-[e]->(b)
RETURN TO_JSON(p) AS path"""),
        code("""nodes, edges = H.paths_to_graph(H.pdf(df_paths)["path"])
H.md(f"**추출된 그래프 노드 `{len(nodes)}`개 · 엣지 `{len(edges)}`개**")
H.draw_graph(nodes, edges, "STARTER_ONTOLOGY_GRAPH 전체 노드·엣지 토폴로지 (실측)", legend=H.LABEL_COLORS)"""),
        md("### 3. 자연어 질의 → ISO GQL 자동 생성 및 BigQuery 실행 (`nl2gql`)"),
        code("""node_labels, edge_labels, _ = H.graph_metadata()
schema_str = H.schema_text(node_labels, edge_labels)
_ = H.nl2gql("각 고객이 사용 중인 단말기명과 가입 요금제명, 월정액을 고객 ID 순으로 보여줘", schema_str)"""),
        md("### 4. AI FDE 에이전트 2-Pass 추론 및 결정론적 MCP 체이닝 (Golden CQ-03 & CQ-05)"),
        code("""from src.agent.reasoning_engine import AiFdeAgentEngine
agent = AiFdeAgentEngine()
H.show_agent(agent.execute_cycle("CUST_DEMO_001 고객이 개통 120일 시점에 5G Light(37,000원)로 하향 시 위약금과 근거 앵커는?"), "Golden CQ-03 · 120일 일할 위약금 산출")
H.show_agent(agent.execute_cycle("CUST_DEMO_003(시니어 복지 대상) 고객이 개통 88일차에 시니어 요금제로 변경 시 위약금 면제 여부와 그래프 경로 확인해줘"), "Golden CQ-05 · 시니어 복지 면제 & 그래프 경로")"""),
    ]


def build_stage1(lang="ko"):
    ko = lang == "ko"
    return [
        md(f"""# Stage 1. {"자산 탐색 · 비식별화 & Golden CQ 설계" if ko else "Asset Discovery, De-identification & Golden CQ Design"}
## {"Step 1.1 정형 DW 원장 & 비정형 가이드 프로파일링 · Step 1.2 Golden CQ 5종 & 경계값 10건" if ko else "Step 1.1 DW Ledger & Policy Guide Profiling · Step 1.2 5 Golden CQs & 10 Boundary Cases"}

![Step 1 Architecture Flow](attachment:step1_architecture_flow.png)"""),
        code(f"""%load_ext bigframes
import nb_helpers as H
H.setup("{lang}")"""),
        md(f"### 1. {'BigQuery 10개 테이블 인벤토리 및 크기·행수 분포 (`%%bqsql`)' if ko else 'BigQuery 10-Table Inventory & Row/Size Distribution (`%%bqsql`)'}"),
        code(f"""%%bqsql df_tables
SELECT table_id, row_count, size_bytes,
  CASE WHEN STARTS_WITH(table_id, 'edge_') THEN 'edge'
       WHEN table_id IN ('tb_doc_chunks', 'tb_domain_rules') THEN 'knowledge'
       ELSE 'master' END AS kind
FROM `{FQ}.__TABLES__`
ORDER BY kind, table_id"""),
        code("""H.show(df_tables)
H.bar(df_tables, "table_id", "size_bytes", H.t("테이블별 물리 크기 (Bytes)", "Table Size in Bytes"), horizontal=True)"""),
        md(f"### 2. {'비식별화 고객 약정 원장(`CUST_DEMO_*`) · 단말 · 요금제 결합 탐색 (`%%bqsql`)' if ko else 'De-identified Customer Contracts (`CUST_DEMO_*`) Joined with Devices & Plans (`%%bqsql`)'}"),
        code(f"""%%bqsql df_contracts
SELECT c.customer_id, c.customer_segment, c.age_group, c.welfare_status, c.contract_type,
       c.elapsed_days, c.granted_subsidy_krw, d.device_name, p.plan_name, p.monthly_fee_krw
FROM `{FQ}.tb_customer_contract` c
JOIN `{FQ}.tb_device_master` d USING (device_id)
JOIN `{FQ}.tb_plan_master` p USING (plan_id)
ORDER BY c.customer_id"""),
        code("""H.show(df_contracts)
H.bar(df_contracts, "customer_id", "elapsed_days", H.t("고객별 개통 경과일수 및 180일 의무유지 기준선", "Elapsed Days per Customer vs. 180-Day Retention Line"), hline=180, hline_label="180d mandatory")"""),
        md(f"### 3. {'단말기 × 요금제별 공시/추가지원금 및 실구매가 히트맵 (`%%bqsql`)' if ko else 'Device × Plan Subsidy Breakdown & Net Price Heatmap (`%%bqsql`)'}"),
        code(f"""%%bqsql df_sub
SELECT d.device_name, p.plan_name, p.monthly_fee_krw, d.factory_price_krw,
       s.base_subsidy_krw, s.additional_subsidy_cap_krw,
       s.base_subsidy_krw + s.additional_subsidy_cap_krw AS total_subsidy_krw,
       d.factory_price_krw - (s.base_subsidy_krw + s.additional_subsidy_cap_krw) AS net_price_krw
FROM `{FQ}.tb_subsidy_policy` s
JOIN `{FQ}.tb_device_master` d USING (device_id)
JOIN `{FQ}.tb_plan_master` p USING (plan_id)
ORDER BY d.device_name, p.monthly_fee_krw DESC"""),
        code("""d_sub = H.pdf(df_sub)
d_sub["device_plan"] = d_sub["device_name"].str.replace(" 256GB", "") + " / " + d_sub["plan_name"]
H.show(d_sub[["device_name", "plan_name", "monthly_fee_krw", "factory_price_krw", "base_subsidy_krw", "additional_subsidy_cap_krw", "total_subsidy_krw", "net_price_krw"]])
H.grouped_bar(d_sub, "device_plan", ["base_subsidy_krw", "additional_subsidy_cap_krw", "net_price_krw"], H.t("단말 × 요금제별 공시지원금 · 추가지원금 · 실구매가 비교", "Base Subsidy, Additional Cap & Net Price by Device × Plan"))
H.heatmap(d_sub.pivot(index="device_name", columns="plan_name", values="net_price_krw"), H.t("단말 × 요금제 실구매가 히트맵 (KRW)", "Net Purchase Price Heatmap (KRW)"))"""),
        md(f"### 4. {'비정형 정책 가이드 청크(`DOC_CHUNK_001~005`) 및 도메인 용어 빈도 히트맵 (`%%bqsql`)' if ko else 'Unstructured Policy Chunks (`DOC_CHUNK_001~005`) & Domain Term Frequency Heatmap (`%%bqsql`)'}"),
        code(f"""%%bqsql df_chunks
SELECT chunk_id, source_file, section_title, trust_tier, CHAR_LENGTH(content) AS chars, content_sha256
FROM `{FQ}.tb_doc_chunks`
ORDER BY chunk_id"""),
        code(f"""%%bqsql df_terms
SELECT term, chunk_id, ARRAY_LENGTH(REGEXP_EXTRACT_ALL(content, term)) AS hits
FROM `{FQ}.tb_doc_chunks`, UNNEST(['공시지원금', '유통망', '180일', '차액정산', '위약금', '선택약정', '복지']) AS term
ORDER BY term, chunk_id"""),
        code("""H.show(df_chunks)
H.heatmap(H.pdf(df_terms).pivot(index="term", columns="chunk_id", values="hits"), H.t("핵심 도메인 용어 × 문서 청크 출현 빈도", "Domain Term × Document Chunk Frequency"), fmt="{:.0f}")"""),
        md(f"### 5. {'Golden CQ 5종 검증 SQL 대조 및 Boundary 질의 10건 명세' if ko else '5 Golden CQs Verification SQL Check & 10 Boundary Cases'}"),
        code("""cqs = H.read_json("data/input/04_cq/golden_competency_questions.json")
H.show(H.check_cq_sql(cqs))
bcs = H.read_json("data/input/04_cq/boundary_cases.json")
H.show(bcs, ["case_id", "root_cause_code", "missing_context", "query", "expected_behavior"])"""),
    ]


def build_stage2(lang="ko"):
    ko = lang == "ko"
    return [
        md(f"""# Stage 2. {"3-Layer LLM-Wiki & 시맨틱 온톨로지 그래프" if ko else "3-Layer LLM-Wiki & Semantic Ontology Graph"}
## {"Step 2.1 OKF v0.2 3-Layer Wiki 컴파일 · Step 2.2 Entity=Node, Concept=Edge 시맨틱 그래프" if ko else "Step 2.1 OKF v0.2 3-Layer Wiki Compilation · Step 2.2 Entity=Node, Concept=Edge Semantic Graph"}

![Step 1 Architecture Flow](attachment:step1_architecture_flow.png)"""),
        code(f"""%load_ext bigframes
import nb_helpers as H
H.setup("{lang}")"""),
        md(f"### 1. {'Karpathy 3-Layer LLM-Wiki 산출물 탐색 (`summary.md`, `entities.md`, `concepts.md`, `rules.md`)' if ko else 'Inspect Compiled 3-Layer LLM-Wiki (`summary.md`, `entities.md`, `concepts.md`, `rules.md`)'}"),
        code("""for fname in ("summary.md", "entities.md", "concepts.md", "rules.md"):
    H.show_md_file(H.ROOT / "data/llm_wiki" / fname, max_lines=28)"""),
        md(f"### 2. {'도메인 규칙(`tb_domain_rules`) 및 요금제 적용 엣지(`edge_rule_applies_to_plan`) 조회 (`%%bqsql`)' if ko else 'Domain Rules (`tb_domain_rules`) & Rule-to-Plan Edges (`edge_rule_applies_to_plan`) (`%%bqsql`)'}"),
        code(f"""%%bqsql df_rules
SELECT r.rule_id, r.rule_name, r.rule_category, r.condition_expr, r.formula_expr,
       r.source_chunk_id, c.section_title, c.content_sha256
FROM `{FQ}.tb_domain_rules` r
JOIN `{FQ}.tb_doc_chunks` c ON c.chunk_id = r.source_chunk_id
ORDER BY r.rule_id"""),
        code(f"""%%bqsql df_rule_plan
SELECT e.rule_id, e.plan_id, p.plan_name, p.monthly_fee_krw, e.relation_label_ko, e.source_chunk_id
FROM `{FQ}.edge_rule_applies_to_plan` e
JOIN `{FQ}.tb_plan_master` p USING (plan_id)
ORDER BY e.rule_id, p.monthly_fee_krw DESC"""),
        code("""H.show(df_rules)
H.show(df_rule_plan)"""),
        md(f"### 3. {'시맨틱 온톨로지 그래프 시각화 (`Entity=Node`, `Concept=Edge`, Sky Blue 허브)' if ko else 'Semantic Ontology Graph Visualization (`Entity=Node`, `Concept=Edge`, Sky Blue Hub)'}"),
        code("""ont = H.read_json("data/output/ontology.jsonld")
rp = H.pdf(df_rule_plan)
nodes, edges = [], []
for g in ont.get("@graph", []):
    nid = g["@id"].replace("chunk:", "").replace("domain:", "")
    nodes.append({"id": nid, "name": g.get("title") or g.get("label", nid), "color": "#0284c7" if g.get("@type") == "DomainOntology" else "#9334E6"})
for r in rp.itertuples():
    nodes.append({"id": r.rule_id, "name": r.rule_id, "color": "#F9AB00"})
    nodes.append({"id": r.plan_name, "name": r.plan_name, "color": "#0284c7"})
    nodes.append({"id": r.source_chunk_id, "name": r.source_chunk_id, "color": "#9334E6"})
    edges.append({"src": r.rule_id, "dst": r.plan_name, "label": r.relation_label_ko})
    edges.append({"src": r.rule_id, "dst": r.source_chunk_id, "label": "GROUNDED_IN", "style": "dashed"})
uniq_nodes = list({n["id"]: n for n in nodes}.values())
H.draw_graph(uniq_nodes, edges, H.t("Stage 2 시맨틱 온톨로지 그래프 (Rule → Plan & SHA-256 Chunk)", "Stage 2 Semantic Ontology Graph (Rule → Plan & SHA-256 Chunk)"),
             legend={"Plan / Domain Hub (#0284c7)": "#0284c7", "Domain Rule (#F9AB00)": "#F9AB00", "Doc Chunk (#9334E6)": "#9334E6"})"""),
        md(f"### 4. {'Vertex AI Gemini(`gemini-3.8-flash`) 기반 정책 문단 트리플 후보 추출 실험' if ko else 'Live Gemini (`gemini-3.8-flash`) Candidate Triple Extraction from Policy Chunks'}"),
        code("""triples = H.propose_triples(["DOC_CHUNK_001", "DOC_CHUNK_003", "DOC_CHUNK_004"])
H.show(triples)"""),
        md(f"### 5. {'Stage 2 파이프라인 MCP(`mcp_stage2_wiki_and_semantic`) 실행 검증' if ko else 'Stage 2 Pipeline MCP (`mcp_stage2_wiki_and_semantic`) Execution'}"),
        code("""from src.agent.mcp_server import DomainMcpServer
server = DomainMcpServer()
res_s2 = server.execute_tool("mcp_stage2_wiki_and_semantic", {"steps": ["compile_3layer_wiki", "bind_semantic_bridges"]})
H.show_tool(res_s2, "anchored_chunks")"""),
    ]
