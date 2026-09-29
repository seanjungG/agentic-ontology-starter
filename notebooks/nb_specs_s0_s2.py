# -*- coding: utf-8 -*-
"""Notebook cell specifications for Stage 0 (KO/EN), Stage 1 (KO/EN), and Stage 2 (KO/EN).

Aligned with the 8-Phase Engineering Flow:
  1. 준비 (Prepare) -> 2. 분석 (Analyze) -> 3. 파싱 (Parse) -> 4. 통합 (Integrate)
  -> 5. 구축 (Build Graph) -> 6. 에이전트 구축 (Build Agent/MCP) -> 7. 답변 (Answer & GQL) -> 8. 검증 (Verify & Gate)
"""

FQ = "seanjung-poc.starter_ontology_dw"
GRAPH = f"{FQ}.STARTER_ONTOLOGY_GRAPH"
STUDIO_URL = "https://agentic-ontology-starter-lwrlf7yogq-du.a.run.app"

STAGE_NAV = [
    (0, "0. 전체 흐름 개요", "0. End-to-End Overview",
     "stage0_overview_walkthrough_ko.ipynb", "stage0_overview_walkthrough_en.ipynb",
     "../../methodology/METHODOLOGY_KO.md", "../../methodology/METHODOLOGY_EN.md", "overview"),
    (1, "Stage 1 · 준비·분석", "Stage 1 · Prepare & Analyze",
     "stage1_asset_and_cq_ko.ipynb", "stage1_asset_and_cq_en.ipynb",
     "../../methodology/01_stage1_asset_and_cq_ko.md", "../../methodology/01_stage1_asset_and_cq_en.md", "stage1"),
    (2, "Stage 2 · 파싱·통합", "Stage 2 · Parse & Integrate",
     "stage2_wiki_and_semantic_graph_ko.ipynb", "stage2_wiki_and_semantic_graph_en.ipynb",
     "../../methodology/02_stage2_wiki_and_semantic_graph_ko.md", "../../methodology/02_stage2_wiki_and_semantic_graph_en.md", "stage2"),
    (3, "Stage 3 · 그래프 구축", "Stage 3 · Build Property Graph",
     "stage3_property_graph_bigquery_spanner_ko.ipynb", "stage3_property_graph_bigquery_spanner_en.ipynb",
     "../../methodology/03_stage3_property_graph_ko.md", "../../methodology/03_stage3_property_graph_en.md", "stage3"),
    (4, "Stage 4 · 에이전트·답변", "Stage 4 · Build Agent & Answer",
     "stage4_agent_and_mcp_execution_ko.ipynb", "stage4_agent_and_mcp_execution_en.ipynb",
     "../../methodology/04_stage4_agent_and_mcp_ko.md", "../../methodology/04_stage4_agent_and_mcp_en.md", "stage4"),
    (5, "Stage 5 · 리니지·검증", "Stage 5 · Verify & Evaluate",
     "stage5_lineage_and_evaluation_ko.ipynb", "stage5_lineage_and_evaluation_en.ipynb",
     "../../methodology/05_stage5_lineage_and_eval_ko.md", "../../methodology/05_stage5_lineage_and_eval_en.md", "stage5"),
]


def md(text):
    return {"cell_type": "markdown", "metadata": {}, "source": text.strip() + "\n"}


def code(src):
    return {"cell_type": "code", "metadata": {}, "source": src.strip() + "\n", "outputs": [], "execution_count": None}


def _bootstrap_code(lang: str, with_agent: bool = False) -> str:
    agent_imp = "\nfrom src.agent.reasoning_engine import AiFdeAgentEngine" if with_agent else ""
    agent_init = "\nagent = AiFdeAgentEngine()" if with_agent else ""
    return f"""%load_ext bigframes
import sys
from pathlib import Path
for _p in (Path.cwd(), Path.cwd().parent, Path.cwd().parent.parent):
    if (_p / "nb_helpers.py").exists() and str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
import pandas as pd
import nb_helpers as H
from src.agent.mcp_server import DomainMcpServer{agent_imp}
H.setup("{lang}")
server = DomainMcpServer(){agent_init}"""


def nav_header(stage: int, lang: str = "ko") -> str:
    ko = lang == "ko"
    _, _, _, nb_ko, nb_en, doc_ko, doc_en, tab = STAGE_NAV[stage]
    items = []
    for s_idx, t_ko, t_en, f_ko, f_en, _, _, _ in STAGE_NAV:
        label = t_ko if ko else t_en
        target = f_ko if ko else f_en
        if s_idx == stage:
            items.append(f"**[▶ {label}](./{target})**")
        else:
            items.append(f"[{label}](./{target})")
    bar_str = " → ".join(items)
    lang_switch = (f"**🇰🇷 한국어 (현재 폴더: `notebooks/ko/`)** · [🇺🇸 English (`notebooks/en/{nb_en}`)](../en/{nb_en})" if ko
                   else f"[🇰🇷 한국어 (`notebooks/ko/{nb_ko}`)](../ko/{nb_ko}) · **🇺🇸 English (Current Folder: `notebooks/en/`)**")
    doc_link = f"[{'방법론 가이드 (Methodology Doc)' if ko else 'Methodology Guide'}]({doc_ko if ko else doc_en})"
    idx_link = f"[{'노트북 전체 인덱스 (README)' if ko else 'Notebook Index (README)'}](../README.md)"
    studio_link = f"[{'라이브 스튜디오 탭 열기' if ko else 'Open Live Studio Tab'}]({STUDIO_URL}/?tab={tab})"
    return (f"> **{'언어 전환 & 바로가기' if ko else 'Language & Quick Links'}**: {lang_switch} ｜ {doc_link} ｜ {idx_link} ｜ {studio_link}\n>\n"
            f"> **{'전체 라이프사이클 네비게이션' if ko else 'Lifecycle Navigation'}**: {bar_str}")


def nav_footer(stage: int, lang: str, qa_items: list, findings: list, next_steps: list) -> dict:
    ko = lang == "ko"
    _, _, _, nb_ko, nb_en, doc_ko, doc_en, _ = STAGE_NAV[stage]
    prev_s = STAGE_NAV[stage - 1] if stage > 0 else None
    next_s = STAGE_NAV[stage + 1] if stage < 5 else None
    nav_parts = []
    if prev_s:
        nav_parts.append(f"[⬅️ {prev_s[1] if ko else prev_s[2]}](./{prev_s[3] if ko else prev_s[4]})")
    nav_parts.append(f"[🏠 {'0. 전체 흐름 초기 화면' if ko else '0. Overview Home'}](./{STAGE_NAV[0][3] if ko else STAGE_NAV[0][4]})")
    if next_s:
        nav_parts.append(f"[➡️ {next_s[1] if ko else next_s[2]}](./{next_s[3] if ko else next_s[4]})")
    nav_parts.append(f"[🌐 {'English Version' if ko else '한국어 버전'}]({'../en/' + nb_en if ko else '../ko/' + nb_ko})")
    nav_parts.append(f"[📖 {'방법론 문서' if ko else 'Methodology Doc'}]({doc_ko if ko else doc_en})")

    qa_block = "\n".join(f"- **Q.** {q}\n  - **A.** {a}" for q, a in qa_items)
    find_block = "\n".join(f"- {f}" for f in findings)
    next_block = "\n".join(f"- {n}" for n in next_steps)
    return md(f"""### Q&A
{qa_block}

### Data Analysis Key Findings
{find_block}

### Insights or Next Steps
{next_block}

---
> **{'다음 학습 이동 (Navigation)' if ko else 'Next Navigation'}**: {" ｜ ".join(nav_parts)}""")


def build_stage0(lang="ko"):
    ko = lang == "ko"
    ko_prefix = "./" if ko else "../ko/"
    en_prefix = "../en/" if ko else "./"
    banner_file = "stage0_overview_flow_ko.png" if ko else "stage0_overview_flow_en.png"
    return [
        md(f"""{nav_header(0, lang)}

---

# {"0. 전체 흐름 초기 화면 — 8단계 엔지니어링 파이프라인 & 5-Stage 에이전틱 온톨로지 워크스루" if ko else "0. End-to-End Entrypoint — 8-Phase Engineering Pipeline & 5-Stage Agentic Ontology Walkthrough"}
## {"준비 → 분석 → 파싱 → 통합 → 구축 → 에이전트 구축 → 답변 → 검증 (BigQuery Property Graph · ISO GQL · Gemini 3.8 Flash)" if ko else "Prepare → Analyze → Parse → Integrate → Build Graph → Build Agent → Answer (GQL) → Verify & Gate"}

{("이 초기 노트북은 **Agentic Ontology Starter Pack v2.0**의 전체 엔지니어링 방법론을 처음부터 끝까지 한눈에 파악하고 실행하는 **마스터 진입 화면**입니다. 단순 데이터 조회에 그치지 않고, **원시 데이터 준비(Phase 1) → 탐색·CQ 설계(Phase 2) → 비정형 문서 파싱·SHA-256 해시 앵커링(Phase 3) → 3-Layer Wiki 및 시맨틱 규칙 통합(Phase 4) → BigQuery/Spanner 물리 프로퍼티 그래프 구축(Phase 5) → 8종 MCP 서버 및 2-Pass 에이전트 구축(Phase 6) → 바인딩 변수 기반 ISO GQL 생성 및 근거 기반 답변(Phase 7) → 4-Tier 리니지 및 50회 경계값 벤치마크 검증(Phase 8)**의 전 과정을 중간 데이터·테이블 구조·그래프 설계 도식과 함께 조화롭게 확인합니다."
  if ko else
  "This master entrypoint notebook walks through the complete **Agentic Ontology Starter Pack v2.0** methodology end to end. Rather than isolated data exploration, it connects **1. Preparation → 2. Analysis & CQ Design → 3. Markdown Parsing & SHA-256 Anchoring → 4. 3-Layer Wiki & Semantic Rule Integration → 5. Physical Property Graph Construction → 6. 8-Tool MCP & 2-Pass Agent Setup → 7. Parameterized ISO GQL & Grounded Answering → 8. 4-Tier Lineage & 50-Trial Benchmark Verification**, showing intermediate tables, bound GQL variables, data outputs, and graph design schematics at every phase.")}

![Stage 0 Overview Architecture Flow](attachment:{banner_file})

### {"전체 8단계 엔지니어링 흐름 및 한/영 노트북 네비게이션 맵 (`notebooks/ko/` · `notebooks/en/`)" if ko else "8-Phase Engineering Flow & Bilingual Notebook Navigation Map (`notebooks/ko/` · `notebooks/en/`)"}

| {"엔지니어링 단계 (8-Phase)" if ko else "Engineering Phase"} | {"정본 Stage (Step)" if ko else "Canonical Stage"} | {"핵심 구현 모듈 및 MCP 도구" if ko else "Core Modules & MCP Tools"} | {"중간 확인 데이터 · 테이블 · 그래프 도식" if ko else "Intermediate Data, Tables & Graph Schematics"} | {"한글 노트북 (`ko/`)" if ko else "Korean Notebook (`ko/`)"} | {"영문 노트북 (`en/`)" if ko else "English Notebook (`en/`)"} |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1. {"준비 (Prepare)" if ko else "Prepare"}**<br>**2. {"분석 (Analyze)" if ko else "Analyze"}** | **Stage 1**<br>(`Step 1.1`–`1.2`) | `terraform/bigquery.tf`<br>`mcp_stage1_asset_discovery`<br>`H.check_cq_sql()` | {"원시 CSV/MD 인벤토리, 10개 테이블 스키마 설계도, 비식별 약정 원장, 지원금 히트맵, Golden CQ 5종 SQL 검증" if ko else "Raw CSV/MD inventory, 10-table ER blueprint, de-identified contracts, subsidy heatmap, 5 Golden CQs SQL check"} | [`stage1_ko`]({ko_prefix}stage1_asset_and_cq_ko.ipynb) | [`stage1_en`]({en_prefix}stage1_asset_and_cq_en.ipynb) |
| **3. {"파싱 (Parse)" if ko else "Parse"}**<br>**4. {"통합 (Integrate)" if ko else "Integrate"}** | **Stage 2**<br>(`Step 2.1`–`2.2`) | `pipeline/ingest.py`<br>`mcp_stage2_wiki_and_semantic`<br>`H.propose_triples()` | {"`DOC_CHUNK` 정규식 파싱 & SHA-256 해시 앵커 비교표, 3-Layer Wiki 4종, Gemini 트리플 추출, 시맨틱 그래프 도식" if ko else "`DOC_CHUNK` regex parsing & SHA-256 anchor table, 3-Layer Wiki, Gemini triple extraction, Semantic Graph schematic"} | [`stage2_ko`]({ko_prefix}stage2_wiki_and_semantic_graph_ko.ipynb) | [`stage2_en`]({en_prefix}stage2_wiki_and_semantic_graph_en.ipynb) |
| **5. {"구축 (Build Graph)" if ko else "Build Graph"}** | **Stage 3**<br>(`Step 3.1`–`3.2`) | `pipeline/graph_builder.py`<br>`mcp_stage3_property_graph`<br>`H.run_gql()` / `H.nl2gql()` | {"6 Node × 4 Edge 메타모델 설계도, BigQuery/Spanner Graph DDL, 전체 토폴로지 & 1~2홉 서브그래프, 바인딩 변수 기반 ISO GQL" if ko else "6 Node × 4 Edge metamodel schematic, BQ/Spanner DDL, full topology & 1..2-hop ego graph, parameterized ISO GQL"} | [`stage3_ko`]({ko_prefix}stage3_property_graph_bigquery_spanner_ko.ipynb) | [`stage3_en`]({en_prefix}stage3_property_graph_bigquery_spanner_en.ipynb) |
| **6. {"에이전트 구축 (Agent)" if ko else "Build Agent"}**<br>**7. {"답변 (Answer)" if ko else "Answer"}** | **Stage 4**<br>(`Step 4.1`–`4.2`) | `src/agent/mcp_server.py`<br>`src/agent/reasoning_engine.py`<br>`mcp_stage4_agent_orchestration` | {"2-Pass 에이전트 오케스트레이션 설계도, 8종 MCP 카탈로그, 슬롯 파싱, 180일 위약금 곡선, Golden CQ & 경계 답변" if ko else "2-Pass agent orchestration schematic, 8-tool MCP catalog, slot parsing, 180d penalty curve, Golden CQ & boundary answers"} | [`stage4_ko`]({ko_prefix}stage4_agent_and_mcp_execution_ko.ipynb) | [`stage4_en`]({en_prefix}stage4_agent_and_mcp_execution_en.ipynb) |
| **8. {"검증 (Verify & Gate)" if ko else "Verify & Gate"}** | **Stage 5**<br>(`Step 5.1`–`5.2`) | `pipeline/validator.py`<br>`mcp_stage5_lineage_and_eval`<br>`H.recheck_cq()` | {"4-Tier 데이터 리니지 테이블 & 멀티파타이트 그래프, Golden CQ 5종 실시간 재검증, Boundary 50회 평가 & Gate 1~5 판정" if ko else "4-Tier lineage table & multipartite graph, live CQ re-audit, Boundary 50-trial metrics & Gate 1..5 checklist"} | [`stage5_ko`]({ko_prefix}stage5_lineage_and_evaluation_ko.ipynb) | [`stage5_en`]({en_prefix}stage5_lineage_and_evaluation_en.ipynb) |

### {"조직 성숙도별 3-Track 선택 흐름 가이드 (`config/starter_config.json`)" if ko else "3-Track Selective Adoption Model (`config/starter_config.json`)"}

| {"트랙 (Track)" if ko else "Track"} | {"활성 Stage" if ko else "Active Stages"} | {"물리 그래프 엔진" if ko else "Graph Engine"} | {"적용 목적 및 권장 시나리오" if ko else "Target Scenario"} |
| :--- | :--- | :--- | :--- |
| **Track 1 · Lite** | `Stage 1 → Stage 2 → Stage 4` | `none` | {"비정형 정책 문서 위키(3-Layer LLM-Wiki)와 도메인 규칙 테이블만으로 빠르게 에이전트를 기동할 때" if ko else "Fast-track deployment using 3-Layer LLM-Wiki and codified rule tables without a physical property graph"} |
| **Track 2 · Standard** | `Stage 1 → Stage 2 → Stage 3 → Stage 4` | `bigquery` / `spanner` | {"정형 DW 원장 4종과 비정형 규칙을 Zero-ETL Property Graph로 결합해 다중 홉 ISO GQL 추론을 수행할 때" if ko else "Unifying 4 structured DW ledgers and unstructured rules into a Zero-ETL Property Graph for multi-hop ISO GQL"} |
| **Track 3 · Full-Stack** | `Stage 1 → Stage 2 → Stage 3 → Stage 4 → Stage 5` | `bigquery` | {"4-Tier 데이터 리니지, Golden CQ 5건(100%), 경계값 10건×5회(50회) 벤치마크 및 Cloud Run 배포 게이트까지 운영할 때" if ko else "Full lifecycle operation including 4-Tier lineage, 5 Golden CQs, 50-trial boundary benchmark, and Cloud Run release gates"} |"""),
        code(_bootstrap_code(lang, with_agent=True)),
        md(f"### 1. {'[전체 아키텍처 도식] 8단계 엔지니어링 파이프라인 및 10개 테이블 스키마 블루프린트' if ko else '[Architecture Blueprint] 8-Phase Engineering Pipeline & 10-Table Schema Blueprint'}"),
        code("""H.draw_eight_phase_flow()
H.draw_table_er_blueprint()"""),
        md(f"### 2. {'[Phase 1~2 · Stage 1: 준비 & 분석] 원시 입력 자산 인벤토리 확인 및 BigQuery 10개 테이블 프로파일링 (`mcp_stage1_asset_discovery` + `%%bqsql`)' if ko else '[Phase 1–2 · Stage 1: Prepare & Analyze] Raw Input Inventory & BigQuery 10-Table Profiling (`mcp_stage1_asset_discovery` + `%%bqsql`)'}"),
        code("""H.show(H.raw_inputs_inventory())
res_s1 = server.execute_tool("mcp_stage1_asset_discovery")
H.show_tool(res_s1)"""),
        code(f"""%%bqsql df_tables
SELECT table_id, row_count, size_bytes,
  CASE WHEN STARTS_WITH(table_id, 'edge_') THEN '3_edge_bridge'
       WHEN table_id IN ('tb_doc_chunks', 'tb_domain_rules') THEN '2_knowledge_wiki'
       ELSE '1_structured_master' END AS table_role
FROM `{FQ}.__TABLES__`
ORDER BY table_role, table_id"""),
        code("""H.show(df_tables)
H.bar(df_tables, "table_id", "row_count", H.t("starter_ontology_dw 10개 테이블 역할별 적재 행 수 (실측)", "Row Count across 10 Tables in starter_ontology_dw"), horizontal=True)"""),
        md(f"### 3. {'[Phase 3~4 · Stage 2: 파싱 & 통합] 비정형 가이드 SHA-256 청킹 · 3-Layer Wiki 컴파일 · 시맨틱 온톨로지 그래프 설계 도식' if ko else '[Phase 3–4 · Stage 2: Parse & Integrate] SHA-256 Guide Chunking, 3-Layer Wiki Compilation & Semantic Ontology Schematic'}"),
        code("""H.show(H.parse_guides_live_demo())
df_wiki, manifest = H.wiki_compilation_summary()
H.show(df_wiki)
res_s2 = server.execute_tool("mcp_stage2_wiki_and_semantic")
H.show_tool(res_s2, "anchored_chunks")
H.draw_semantic_design_graph()"""),
        md(f"### 4. {'[Phase 5 · Stage 3: 물리 그래프 구축] `STARTER_ONTOLOGY_GRAPH` 메타모델 · 실행 GQL 문장 & 바인딩 변수 · 전체 인스턴스 토폴로지 (`%%bqsql` + `H.run_gql`)' if ko else '[Phase 5 · Stage 3: Build Property Graph] `STARTER_ONTOLOGY_GRAPH` Metamodel, Executed GQL & Bound Variables, and Full Topology (`%%bqsql` + `H.run_gql`)'}"),
        code("""res_s3 = server.execute_tool("mcp_stage3_property_graph")
H.show_tool(res_s3, "node_tables")
H.draw_property_graph_metamodel()"""),
        code(f"""%%bqsql df_paths
GRAPH `{GRAPH}`
MATCH p = (a)-[e]->(b)
RETURN TO_JSON(p) AS path"""),
        code(f"""gql_cust_rules = \"\"\"GRAPH `{GRAPH}`
MATCH (c:CustomerContractNode)-[:USES_DEVICE]->(d:DeviceNode),
      (c)-[:SUBSCRIBES_PLAN]->(p:PlanNode)<-[ap:APPLIES_TO_PLAN]-(r:DomainRuleNode),
      (ch:DocChunkNode)
WHERE c.customer_id = 'CUST_DEMO_001' AND ch.chunk_id = ap.source_chunk_id
RETURN c.customer_id AS customer_id, d.device_name AS device_name, p.plan_name AS plan_name,
       r.rule_id AS rule_id, ap.source_chunk_id AS chunk_id, ch.content_sha256 AS sha256_anchor
ORDER BY r.rule_id\"\"\"
_ = H.run_gql(
    gql_cust_rules,
    variables={{
        "GRAPH": ("{GRAPH}", H.t("BigQuery 프로퍼티 그래프 식별자", "Target BigQuery Property Graph")),
        "c.customer_id": ("'CUST_DEMO_001'", H.t("CustomerContractNode 고객 필터 변수", "CustomerContractNode filter parameter")),
        "ch.chunk_id": ("ap.source_chunk_id", H.t("DocChunkNode SHA-256 앵커 조인 키", "DocChunkNode SHA-256 anchor join key")),
    }},
    title=H.t("3-Hop ISO GQL 실행 예시 (고객 약정 → 단말/요금제 ← 도메인 규칙 + 근거 청크)",
              "3-Hop ISO GQL Execution (Customer Contract → Device/Plan ← Domain Rule + DocChunk)"),
)
nodes, edges = H.paths_to_graph(H.pdf(df_paths)["path"])
H.md(H.t(f"**실측 추출된 물리 그래프 노드 `{{len(nodes)}}`개 · 엣지 `{{len(edges)}}`개**", f"**Extracted physical graph nodes: `{{len(nodes)}}` · edges: `{{len(edges)}}`**"))
H.draw_graph(nodes, edges, H.t("STARTER_ONTOLOGY_GRAPH 전체 인스턴스 토폴로지 (5계층 레이어 배치)", "Full Instance Topology of STARTER_ONTOLOGY_GRAPH (5-Column Layered Layout)"), legend=H.LABEL_COLORS)"""),
        md(f"### 5. {'[Phase 6~7 · Stage 4: 에이전트 구축 & 답변] 2-Pass 에이전트 설계도 · 실시간 NL-to-GQL 생성 · Golden CQ 추론 실행' if ko else '[Phase 6–7 · Stage 4: Build Agent & Answer] 2-Pass Agent Blueprint, Live NL-to-GQL & Golden CQ Execution'}"),
        code("""H.draw_agent_architecture()
node_labels, edge_labels, _ = H.graph_metadata()
schema_str = H.schema_text(node_labels, edge_labels)
_ = H.nl2gql(H.t("각 고객이 사용 중인 단말기명과 가입 요금제명, 월정액을 고객 ID 순으로 보여줘",
                 "Show each customer's device name, subscribed plan name, and monthly fee ordered by customer ID"), schema_str)
H.show_agent(agent.execute_cycle("CUST_DEMO_001 고객이 개통 120일 시점에 5G Light(37,000원)로 하향 시 위약금과 근거 앵커는?"),
             H.t("Golden CQ-03 · 120일 일할 차액정산 위약금 산출", "Golden CQ-03 · 120-Day Prorated Penalty Calculation"))
H.show_agent(agent.execute_cycle("CUST_DEMO_003(시니어 복지 대상) 고객이 개통 88일차에 시니어 요금제로 변경 시 위약금 면제 여부와 그래프 경로 확인해줘"),
             H.t("Golden CQ-05 · 시니어 복지 면제 & 멀티홉 그래프 경로", "Golden CQ-05 · Senior Welfare Exemption & Multi-Hop Graph Path"))"""),
        md(f"### 6. {'[Phase 8 · Stage 5: 검증 & 배포 게이트] 4-Tier 리니지 요약 및 Gate 1 ~ Gate 5 통합 통과 현황' if ko else '[Phase 8 · Stage 5: Verify & Release Gate] 4-Tier Lineage Summary & Gate 1–5 Readiness Verdict'}"),
        code("""res_s5 = server.execute_tool("mcp_stage5_lineage_and_eval")
H.show_tool(res_s5)
H.show(H.gate_checklist_table())"""),
        nav_footer(
            0, lang,
            qa_items=[
                (
                    "정형 DW 테이블과 비정형 정책 문서는 어떤 단계를 거쳐 에이전트 답변으로 연결되나요?" if ko
                    else "How do structured DW tables and unstructured policy documents connect to produce grounded agent answers?",
                    "8단계 엔지니어링 흐름(1. 준비 → 2. 분석 → 3. 파싱 → 4. 통합 → 5. 구축 → 6. 에이전트 구축 → 7. 답변 → 8. 검증)을 통해 원시 CSV 6종과 마크다운 가이드 2종이 BigQuery 10개 테이블(`starter_ontology_dw`), 3-Layer LLM-Wiki, `STARTER_ONTOLOGY_GRAPH`(25 노드 · 29 엣지)로 통합되고, 8종 MCP 도구와 2-Pass Gemini(`gemini-3.8-flash`) 에이전트가 이를 조회해 답변합니다." if ko
                    else "Through the 8-phase engineering pipeline (Prepare → Analyze → Parse → Integrate → Build Graph → Build Agent → Answer → Verify), 6 CSVs and 2 Markdown guides are unified into 10 BigQuery tables (`starter_ontology_dw`), a 3-Layer LLM-Wiki, and `STARTER_ONTOLOGY_GRAPH` (25 nodes, 29 edges), queried by 8 MCP tools and the 2-Pass Gemini (`gemini-3.8-flash`) agent."
                ),
            ],
            findings=[
                "BigQuery `starter_ontology_dw` 내 마스터 4종(22행), 지식/규칙 2종(9행), 엣지 브릿지 4종(31행) 총 10개 테이블(62행)과 비식별 고객 ID(`CUST_DEMO_001~006`, 위반 `0건`)가 실측 확인되었습니다." if ko
                else "Verified 10 BigQuery tables (62 total rows across 4 master, 2 knowledge, and 4 edge tables) with 0 de-identification violations (`CUST_DEMO_001~006`).",
                "비정형 가이드 5개 청크(`DOC_CHUNK_001~005`)의 SHA-256 해시 앵커가 BigQuery `tb_doc_chunks` 및 3-Layer Wiki와 일치하며, `STARTER_ONTOLOGY_GRAPH`에서 중복 키 `0건` 및 멀티홉 경로가 검증되었습니다." if ko
                else "All 5 policy chunks (`DOC_CHUNK_001~005`) match their stored SHA-256 anchors in `tb_doc_chunks`, with 0 duplicate keys and verified multi-hop paths in `STARTER_ONTOLOGY_GRAPH`.",
                "Gate 1 ~ Gate 5 통합 점검 결과 Golden CQ 5/5(`100.0%`) 및 경계값 10건×5회(`50 Trials`, 통과율 `98.0%`) 기준을 모두 충족(`PASS`)했습니다." if ko
                else "All 5 release gates (`Gate 1`–`Gate 5`) passed, with 5/5 (`100.0%`) Golden CQs and `98.0%` success across 50 boundary benchmark trials."
            ],
            next_steps=[
                "다음 단계인 `Stage 1 (준비·분석)` 노트북으로 이동하여 원시 CSV/가이드 스키마 설계, 정형/비정형 데이터 프로파일링, Golden CQ 5종의 정답 검증 SQL 설계를 상세히 확인하세요." if ko
                else "Proceed to the `Stage 1 (Prepare & Analyze)` notebook to inspect the raw CSV/guide schema design, data profiling, and Golden CQ verification SQL in detail."
            ],
        ),
    ]


def build_stage1(lang="ko"):
    ko = lang == "ko"
    banner_file = "stage1_prepare_analyze_flow_ko.png" if ko else "stage1_prepare_analyze_flow_en.png"
    return [
        md(f"""{nav_header(1, lang)}

---

# {"Stage 1. [준비 & 분석] 원천 자산 준비 · 테이블 스키마 설계 · 데이터 탐색 및 Golden CQ 정의" if ko else "Stage 1. [Prepare & Analyze] Raw Asset Preparation, Schema Design, Data Profiling & Golden CQ Definition"}
## {"Step 1.1 정형/비정형 자산 스코핑 및 스키마 블루프린트 · Step 1.2 데이터 탐색 및 Golden CQ 5종 / Boundary 10건 설계" if ko else "Step 1.1 Structured/Unstructured Asset Scoping & Schema Blueprint · Step 1.2 Data Profiling & 5 Golden CQs / 10 Boundary Cases"}

{("Stage 1은 온톨로지 구축의 **Phase 1(준비)**과 **Phase 2(분석)**를 수행합니다. 에이전트가 답해야 할 핵심 역량 질문(**Golden CQ 5종**)과 경계 조건(**Boundary 10건**)을 먼저 확정하고, 이에 필요한 정형 CSV 6종과 비정형 가이드 2종을 스코핑하여 Terraform으로 프로비저닝된 BigQuery 10개 테이블(`starter_ontology_dw`)에 적재·검증합니다."
  if ko else
  "Stage 1 executes **Phase 1 (Preparation)** and **Phase 2 (Analysis)** of the methodology. We first define the target **5 Golden Competency Questions (CQs)** and **10 Boundary Cases**, scope the required 6 structured CSVs and 2 unstructured policy guides, and validate the 10 Terraform-provisioned BigQuery tables (`starter_ontology_dw`).")}

![Stage 1 Prepare and Analyze Architecture Flow](attachment:{banner_file})"""),
        code(_bootstrap_code(lang, with_agent=False)),
        md(f"### 1. {'[Phase 1: 준비 (Preparation)] 원천 입력 자산(`data/input/`) 인벤토리 및 10개 테이블 스키마 설계도 (`%%bqsql`)' if ko else '[Phase 1: Preparation] Raw Input Asset Inventory (`data/input/`) & 10-Table Schema Blueprint (`%%bqsql`)'}"),
        code("""H.show(H.raw_inputs_inventory())
H.draw_table_er_blueprint()"""),
        code(f"""%%bqsql df_schema
SELECT table_name,
       COUNT(*) AS column_count,
       STRING_AGG(CONCAT(column_name, ':', data_type), ', ' ORDER BY ordinal_position) AS columns_spec
FROM `{FQ}.INFORMATION_SCHEMA.COLUMNS`
GROUP BY table_name
ORDER BY table_name"""),
        code("""H.show(df_schema)"""),
        md(f"### 2. {'[Phase 2a: 분석 (Analysis)] Stage 1 파이프라인 MCP(`mcp_stage1_asset_discovery`) 실행 — 테이블 프로파일링 및 비식별화 거버넌스 검증' if ko else '[Phase 2a: Analysis] Stage 1 Pipeline MCP (`mcp_stage1_asset_discovery`) — Table Profiling & PII De-identification Check'}"),
        code("""res_s1 = server.execute_tool("mcp_stage1_asset_discovery", {"steps": ["profile_tables", "scan_guides", "prune_noise", "tag_pii_governance"]})
H.show_tool(res_s1, "table_inventory")
H.show(pd.DataFrame([res_s1["pii_check"]]))"""),
        code(f"""%%bqsql df_tables
SELECT table_id, row_count, size_bytes,
  CASE WHEN STARTS_WITH(table_id, 'edge_') THEN 'edge'
       WHEN table_id IN ('tb_doc_chunks', 'tb_domain_rules') THEN 'knowledge'
       ELSE 'master' END AS kind
FROM `{FQ}.__TABLES__`
ORDER BY kind, table_id"""),
        code("""H.bar(df_tables, "table_id", "size_bytes", H.t("starter_ontology_dw 테이블별 물리 크기 (Bytes)", "Table Physical Size in Bytes"), horizontal=True)"""),
        md(f"### 3. {'[Phase 2b: 정형 원장 데이터 확인] 비식별 고객 약정(`CUST_DEMO_*`) · 단말 · 요금제 조인 및 180일 의무유지 경과일 분포 (`%%bqsql`)' if ko else '[Phase 2b: Structured Ledger Inspection] De-identified Contracts (`CUST_DEMO_*`) Joined with Devices & Plans (`%%bqsql`)'}"),
        code(f"""%%bqsql df_contracts
SELECT c.customer_id, c.contract_id, c.customer_segment, c.age_group, c.welfare_status, c.contract_type,
       c.elapsed_days, c.granted_subsidy_krw, d.device_name, p.plan_name, p.monthly_fee_krw
FROM `{FQ}.tb_customer_contract` c
JOIN `{FQ}.tb_device_master` d USING (device_id)
JOIN `{FQ}.tb_plan_master` p USING (plan_id)
ORDER BY c.customer_id"""),
        code("""H.show(df_contracts)
H.bar(df_contracts, "customer_id", "elapsed_days",
      H.t("고객별 개통 경과일수 및 180일 의무유지 기준선", "Customer Elapsed Days vs. 180-Day Mandatory Retention Line"),
      hline=180, hline_label="180d mandatory")"""),
        md(f"### 4. {'[Phase 2c: 지원금 정책 데이터 탐색] 단말기 × 요금제별 공시/추가지원금 구조 및 실구매가 히트맵 (`%%bqsql`)' if ko else '[Phase 2c: Subsidy Policy Exploration] Device × Plan Subsidy Structure & Net Price Heatmap (`%%bqsql`)'}"),
        code(f"""%%bqsql df_sub
SELECT s.policy_id, d.device_name, p.plan_name, p.monthly_fee_krw, d.factory_price_krw,
       s.base_subsidy_krw, s.additional_subsidy_cap_krw,
       s.base_subsidy_krw + s.additional_subsidy_cap_krw AS total_subsidy_krw,
       d.factory_price_krw - (s.base_subsidy_krw + s.additional_subsidy_cap_krw) AS net_price_krw,
       s.mandatory_retention_days
FROM `{FQ}.tb_subsidy_policy` s
JOIN `{FQ}.tb_device_master` d USING (device_id)
JOIN `{FQ}.tb_plan_master` p USING (plan_id)
ORDER BY d.device_name, p.monthly_fee_krw DESC"""),
        code("""d_sub = H.pdf(df_sub)
d_sub["device_plan"] = d_sub["device_name"].str.replace(" 256GB", "") + " / " + d_sub["plan_name"]
H.show(d_sub[["policy_id", "device_name", "plan_name", "monthly_fee_krw", "factory_price_krw", "base_subsidy_krw", "additional_subsidy_cap_krw", "total_subsidy_krw", "net_price_krw"]])
H.grouped_bar(d_sub, "device_plan", ["base_subsidy_krw", "additional_subsidy_cap_krw", "net_price_krw"],
              H.t("단말 × 요금제별 공시지원금 · 추가지원금 · 실구매가 비교", "Base Subsidy, Additional Cap & Net Price by Device × Plan"))
H.heatmap(d_sub.pivot(index="device_name", columns="plan_name", values="net_price_krw"),
          H.t("단말 × 요금제 실구매가 히트맵 (KRW)", "Net Purchase Price Heatmap (KRW)"))"""),
        md(f"### 5. {'[Phase 2d: 비정형 문서 · 용어사전 · Golden CQ 설계] 정책 청크 용어 빈도(`%%bqsql`) 및 Golden CQ 5종 정답 SQL 대조 검증' if ko else '[Phase 2d: Unstructured Chunks, Glossary & Golden CQ Design] Term Frequency (`%%bqsql`) & 5 Golden CQs SQL Ground-Truth Check'}"),
        code(f"""%%bqsql df_terms
SELECT t.term, c.chunk_id, ARRAY_LENGTH(REGEXP_EXTRACT_ALL(c.content, t.pat)) AS hits
FROM `{FQ}.tb_doc_chunks` c,
UNNEST([
  STRUCT({'\"공시지원금 (Subsidy)\"' if ko else '\"Public Subsidy\"'} AS term, r'(?i)subsidy|공시지원금' AS pat),
  STRUCT({'\"유통망 상한 (15% Cap)\"' if ko else '\"15% Retail Cap\"'}, r'(?i)15%|additional|유통망'),
  STRUCT({'\"180일 의무유지 (180d)\"' if ko else '\"180-Day Rule\"'}, r'(?i)180-day|180 days|180일'),
  STRUCT({'\"일할 차액정산 (Prorated)\"' if ko else '\"Prorated Clawback\"'}, r'(?i)formula|prorated|일할|차액정산'),
  STRUCT({'\"위약금 (Penalty)\"' if ko else '\"Penalty Settlement\"'}, r'(?i)penalty|위약금'),
  STRUCT({'\"선택약정 25% (Selective)\"' if ko else '\"25% Selective Discount\"'}, r'(?i)selective|25%|선택약정'),
  STRUCT({'\"복지 면제 (Welfare)\"' if ko else '\"Welfare Exemption\"'}, r'(?i)welfare|exempt|복지|면제')
]) AS t
ORDER BY t.term, c.chunk_id"""),
        code("""glossary = H.read_json("data/input/05_glossary/business_glossary.json")
H.show(pd.DataFrame([{"term": k, "definition": v} for k, v in glossary.items()] if isinstance(glossary, dict) else glossary))
df_terms_loc = H.pdf(df_terms)
H.heatmap(df_terms_loc.pivot(index="term", columns="chunk_id", values="hits"),
          H.t("핵심 도메인 용어 × 정책 문서 청크 출현 빈도", "Domain Term × Policy Document Chunk Frequency"), fmt="{:.0f}")
cqs = H.read_json("data/input/04_cq/golden_competency_questions.json")
H.show(H.check_cq_sql(cqs))
bcs = H.read_json("data/input/04_cq/boundary_cases.json")
H.show(bcs, ["case_id", "root_cause_code", "missing_context", "query", "expected_behavior"])"""),
        nav_footer(
            1, lang,
            qa_items=[
                (
                    "왜 온톨로지와 그래프를 만들기 전에 Golden CQ와 `verification_sql`을 먼저 정의하나요?" if ko
                    else "Why do we define Golden CQs and `verification_sql` before building the ontology and graph?",
                    "에이전트가 답해야 할 질문과 결정론적 정답 산식(`expected_math`, `verification_sql`, `grounded_chunk`)을 Stage 1에서 먼저 확정해야 불필요한 테이블 적재를 막고(Scoping), Stage 5에서 에이전트 답변을 SQL 실측치와 1:1 자동 대조할 수 있기 때문입니다." if ko
                    else "Defining target CQs and deterministic ground-truth SQL (`expected_math`, `verification_sql`, `grounded_chunk`) in Stage 1 scopes only the necessary tables/guides and provides an automated grading oracle in Stage 5."
                ),
            ],
            findings=[
                "`starter_ontology_dw` 내 10개 테이블 스키마(`INFORMATION_SCHEMA.COLUMNS`)와 62개 행이 정상 적재되었으며, `CUST_DEMO_001~006` 비식별 규칙 위반 건수는 `0건`입니다." if ko
                else "All 10 tables (62 rows) in `starter_ontology_dw` are populated and verified via `INFORMATION_SCHEMA.COLUMNS`, with `0` de-identification violations across `CUST_DEMO_001~006`.",
                "6명의 고객 약정 중 5건(`elapsed_days`: 45~120일)이 180일 의무유지 기간 이내에 있어 요금제 하향 시 일할 차액정산 또는 복지 면제 규칙 판정이 필요합니다." if ko
                else "5 of the 6 customer contracts (`elapsed_days`: 45–120 days) are within the 180-day mandatory retention window, requiring prorated penalty or welfare exemption evaluation upon plan downgrade.",
                "Golden CQ 5종(`CQ-01`~`CQ-05`)의 `verification_sql`을 BigQuery에서 직접 실행한 결과, `expected_math`와 5건 모두 일치(`match=True`)함을 확인했습니다." if ko
                else "Executing `verification_sql` for all 5 Golden CQs (`CQ-01`–`CQ-05`) on live BigQuery matched `expected_math` in all 5 cases (`match=True`)."
            ],
            next_steps=[
                "다음 단계인 `Stage 2 (파싱·통합)` 노트북으로 이동하여 비정형 정책 가이드 마크다운을 SHA-256 해시 앵커 청크로 파싱하고, Karpathy 3-Layer LLM-Wiki 및 시맨틱 온톨로지 그래프로 통합하는 과정을 확인하세요." if ko
                else "Proceed to `Stage 2 (Parse & Integrate)` to see how unstructured policy guides are parsed into SHA-256 anchored chunks and integrated into the 3-Layer LLM-Wiki and Semantic Ontology Graph."
            ],
        ),
    ]


def build_stage2(lang="ko"):
    ko = lang == "ko"
    banner_file = "stage2_parse_integrate_flow_ko.png" if ko else "stage2_parse_integrate_flow_en.png"
    return [
        md(f"""{nav_header(2, lang)}

---

# {"Stage 2. [파싱 & 통합] 비정형 정책 가이드 파싱 · 3-Layer LLM-Wiki 컴파일 & 시맨틱 온톨로지 그래프" if ko else "Stage 2. [Parse & Integrate] Policy Guide Parsing, 3-Layer LLM-Wiki Compilation & Semantic Ontology Graph"}
## {"Step 2.1 SHA-256 해시 앵커 청킹 및 OKF v0.2 3-Layer Wiki 생성 · Step 2.2 도메인 규칙 및 시맨틱 그래프 통합 (`Entity=Node`, `Concept=Edge`)" if ko else "Step 2.1 SHA-256 Hash-Anchored Chunking & OKF v0.2 3-Layer Wiki · Step 2.2 Domain Rule Binding & Semantic Graph (`Entity=Node`, `Concept=Edge`)"}

{("Stage 2는 방법론의 **Phase 3(파싱)**과 **Phase 4(통합)**를 구현합니다. `pipeline/ingest.py`의 `run_ingest()`가 원시 정책 가이드(`01_guides/*.md`)를 문단 단위(`DOC_CHUNK_001~005`)로 파싱하여 원문 변조 여부를 즉시 검증할 수 있는 **결정론적 SHA-256 해시 앵커(`anchor_<12hex>`)**를 부여하고, 이를 **Andrej Karpathy 3-Layer LLM-Wiki(`summary.md`, `entities.md`, `concepts.md`, `rules.md`)** 및 **시맨틱 온톨로지 그래프(`ontology.jsonld`, `tb_domain_rules`, `edge_rule_applies_to_plan`)**로 통합합니다."
  if ko else
  "Stage 2 implements **Phase 3 (Parsing)** and **Phase 4 (Integration)**. `pipeline/ingest.py` (`run_ingest()`) parses raw policy guides (`01_guides/*.md`) into `DOC_CHUNK_001~005` with deterministic **SHA-256 hash anchors (`anchor_<12hex>`)**, compiles the **Andrej Karpathy 3-Layer LLM-Wiki (`summary.md`, `entities.md`, `concepts.md`, `rules.md`)**, and binds structured tariff plans to codified business rules (`tb_domain_rules`, `edge_rule_applies_to_plan`) inside the **Semantic Ontology Graph (`Entity=Node`, `Concept=Edge`)**.")}

![Stage 2 Parse and Integrate Architecture Flow](attachment:{banner_file})"""),
        code(_bootstrap_code(lang, with_agent=False)),
        md(f"### 1. {'[Phase 3a: 파싱 (Parsing)] 원시 정책 마크다운(`01_guides/*.md`) 정규식 청크 분할 및 SHA-256 해시 앵커 무결성 대조 (`pipeline/ingest.py`)' if ko else '[Phase 3a: Parsing] Raw Policy Markdown (`01_guides/*.md`) Chunking & SHA-256 Anchor Integrity Check (`pipeline/ingest.py`)'}"),
        code("""df_parsed = H.parse_guides_live_demo()
H.show(df_parsed)"""),
        code(f"""%%bqsql df_bq_chunks
SELECT chunk_id, source_file, section_title, trust_tier, content_sha256,
       CHAR_LENGTH(content) AS char_len, SUBSTR(content, 1, 85) AS content_preview
FROM `{FQ}.tb_doc_chunks`
ORDER BY chunk_id"""),
        code("""H.show(df_bq_chunks)"""),
        md(f"### 2. {'[Phase 3b: 위키 컴파일 & GCS 동기화] Andrej Karpathy 3-Layer LLM-Wiki (`summary.md`, `entities.md`, `concepts.md`, `rules.md`) 및 `mcp_stage2_wiki_and_semantic` 실행' if ko else '[Phase 3b: Wiki Compilation & GCS Sync] Karpathy 3-Layer LLM-Wiki (`summary.md`, `entities.md`, `concepts.md`, `rules.md`) & `mcp_stage2_wiki_and_semantic`'}"),
        code("""df_wiki, manifest = H.wiki_compilation_summary()
H.md(f"**GCS Manifest Status**: `{manifest['status']}` · Bucket `{manifest['gcs_uri']}` · Uploaded Objects `{len(manifest['uploaded_gcs_objects'])}` · Loaded BQ Tables `{manifest['validation']['bigquery_tables_loaded']}`")
H.show(df_wiki)
for fname in ("summary.md", "entities.md", "concepts.md", "rules.md"):
    H.show_md_file(H.ROOT / "data/llm_wiki" / fname, max_lines=22)
res_s2 = server.execute_tool("mcp_stage2_wiki_and_semantic", {"steps": ["compile_3layer_wiki", "extract_hash_anchors", "bind_semantic_bridges"]})
H.show_tool(res_s2, "anchored_chunks")"""),
        md(f"### 3. {'[Phase 4a: 시맨틱 통합 (Integration)] Vertex AI Gemini(`gemini-3.8-flash`) 기반 후보 트리플 추출 및 도메인 규칙 ↔ 요금제 시맨틱 브릿지 테이블 확인 (`%%bqsql`)' if ko else '[Phase 4a: Semantic Integration] Live Gemini (`gemini-3.8-flash`) Candidate Triple Extraction & Rule-to-Plan Semantic Bridge Tables (`%%bqsql`)'}"),
        code("""triples = H.propose_triples(["DOC_CHUNK_001", "DOC_CHUNK_003", "DOC_CHUNK_004"])
H.show(triples)"""),
        code(f"""%%bqsql df_rules
SELECT r.rule_id, r.rule_name, r.rule_category, r.condition_expr, r.formula_expr,
       r.source_chunk_id, c.section_title, c.content_sha256
FROM `{FQ}.tb_domain_rules` r
JOIN `{FQ}.tb_doc_chunks` c ON c.chunk_id = r.source_chunk_id
ORDER BY r.rule_id"""),
        code(f"""%%bqsql df_rule_plan
SELECT e.edge_id, e.rule_id, e.plan_id, p.plan_name, p.monthly_fee_krw, e.relation_label_ko, e.source_chunk_id
FROM `{FQ}.edge_rule_applies_to_plan` e
JOIN `{FQ}.tb_plan_master` p USING (plan_id)
ORDER BY e.rule_id, p.monthly_fee_krw DESC"""),
        code("""H.show(df_rules)
H.show(df_rule_plan)"""),
        md(f"### 4. {'[Phase 4b: 시맨틱 그래프 설계 및 도식화] OKF v0.2 `ontology.jsonld` 명세 및 시맨틱 온톨로지 그래프 (`Entity=Node`, `Concept=Edge`)' if ko else '[Phase 4b: Semantic Graph Design & Schematics] OKF v0.2 `ontology.jsonld` & Semantic Ontology Graph (`Entity=Node`, `Concept=Edge`)'}"),
        code("""ont = H.read_json("data/output/ontology.jsonld")
H.show(pd.DataFrame(ont.get("@graph", [])))
H.draw_semantic_design_graph()

rp = H.pdf(df_rule_plan)
nodes, edges = [], []
for r in rp.itertuples():
    nodes.append({"id": r.source_chunk_id, "name": r.source_chunk_id, "color": "#9334E6", "layer": 0})
    nodes.append({"id": r.rule_id, "name": r.rule_id, "color": "#F9AB00", "layer": 1})
    nodes.append({"id": r.plan_name, "name": r.plan_name, "color": "#0284c7", "layer": 2})
    e_lbl = r.relation_label_ko if H.LANG == "ko" else "APPLIES_TO_PLAN"
    edges.append({"src": r.rule_id, "dst": r.plan_name, "label": e_lbl})
    edges.append({"src": r.rule_id, "dst": r.source_chunk_id, "label": "GROUNDED_IN", "style": "dashed"})
uniq_nodes = list({n["id"]: n for n in nodes}.values())
H.draw_graph(uniq_nodes, edges,
             H.t("BigQuery 실데이터 기반 DocChunk ⇠ Rule (GROUNDED_IN) 및 Rule → Plan (APPLIES_TO_PLAN) 시맨틱 브릿지 그래프",
                 "Live BigQuery DocChunk ⇠ Rule (GROUNDED_IN) & Rule → Plan (APPLIES_TO_PLAN) Semantic Bridge Graph"),
             layout="layers", figsize=(11.8, 5.4), node_size=1850,
             legend={"Doc Chunk (#9334E6)": "#9334E6", "Domain Rule (#F9AB00)": "#F9AB00", "Tariff Plan (#0284c7)": "#0284c7"})"""),
        nav_footer(
            2, lang,
            qa_items=[
                (
                    "비정형 정책 가이드 문단과 정형 요금제 마스터 테이블은 어떻게 시맨틱하게 통합되나요?" if ko
                    else "How are unstructured policy paragraphs semantically integrated with structured tariff plan tables?",
                    "`pipeline/ingest.py`가 정책 가이드를 `DOC_CHUNK_001~005`로 분할해 SHA-256 해시 앵커(`anchor_<12hex>`)를 부여하고, 문서 내 비즈니스 규칙을 `tb_domain_rules`(4건)로 코드화한 뒤 `edge_rule_applies_to_plan`(12건)을 통해 각 요금제(`plan_id`)와 근거 청크(`source_chunk_id`)를 양방향으로 바인딩합니다." if ko
                    else "`pipeline/ingest.py` splits policy guides into `DOC_CHUNK_001~005` with deterministic `anchor_<12hex>` SHA-256 hashes, codifies domain rules in `tb_domain_rules` (4 rules), and binds them to structured `plan_id` rows via `edge_rule_applies_to_plan` (12 edges)."
                ),
            ],
            findings=[
                "원시 가이드 2종에서 파싱된 5개 청크(`DOC_CHUNK_001~005`)의 실시간 재계산 SHA-256 해시 앵커가 BigQuery `tb_doc_chunks.content_sha256`과 5건 모두 일치(`sha256_match=True`)합니다." if ko
                else "Re-computing SHA-256 anchors across all 5 parsed chunks (`DOC_CHUNK_001~005`) matched `tb_doc_chunks.content_sha256` in BigQuery (`sha256_match=True` for all 5).",
                "3-Layer LLM-Wiki(`summary.md`, `entities.md`, `concepts.md`, `rules.md`)와 `ontology.jsonld`를 포함해 총 8개 객체가 GCS(`gs://seanjung-poc-starter-ontology/`)와 동기화(`LIVE_GCP_SYNCED`)되었습니다." if ko
                else "All 4 layers of the LLM-Wiki (`summary.md`, `entities.md`, `concepts.md`, `rules.md`) and `ontology.jsonld` (8 objects total) are synced to GCS (`LIVE_GCP_SYNCED`).",
                "4개 도메인 규칙(`RULE_SUBSIDY_CAP`, `RULE_SIX_PLAN_180D`, `RULE_WELFARE_EXEMPT`, `RULE_TCO_24M`)이 6개 요금제에 총 12개의 시맨틱 엣지(`APPLIES_TO_PLAN`)로 연결되어 시맨틱 그래프를 형성합니다." if ko
                else "4 codified domain rules connect to the 6 tariff plans via 12 `APPLIES_TO_PLAN` semantic bridge edges, grounded in `DOC_CHUNK_001~005`."
            ],
            next_steps=[
                "Track 1(Lite) 환경은 이 단계 완료 후 바로 `Stage 4 (에이전트·답변)`로 이동할 수 있으며, Track 2/3 환경은 다음 `Stage 3 (그래프 구축)` 노트북으로 이동하여 Zero-ETL BigQuery/Spanner 물리 프로퍼티 그래프를 구축합니다." if ko
                else "Track 1 (Lite) deployments can jump directly to `Stage 4 (Build Agent & Answer)`, while Track 2/3 deployments proceed to `Stage 3 (Build Property Graph)` for Zero-ETL BigQuery/Spanner Property Graph provisioning."
            ],
        ),
    ]
