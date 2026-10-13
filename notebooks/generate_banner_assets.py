# -*- coding: utf-8 -*-
"""Generates 12 bilingual (6 KO + 6 EN) Stage 0..5 architecture banner PNGs in `notebooks/assets/`."""
from pathlib import Path
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
from matplotlib import font_manager

ASSETS_DIR = Path(__file__).resolve().parent / "assets"
ASSETS_DIR.mkdir(parents=True, exist_ok=True)

fonts = {f.name for f in font_manager.fontManager.ttflist}
CJK_FONT = next((f for f in ("Apple SD Gothic Neo", "AppleGothic", "NanumGothic", "Noto Sans CJK KR") if f in fonts), "sans-serif")


def _draw_banner(filename: str, badge: str, title: str, subtitle: str, columns: list, font_name: str):
    """Renders a 4-column enterprise light-theme architecture banner card (1400x440 px at 140 dpi)."""
    plt.rcParams.update({"font.family": font_name, "axes.unicode_minus": False})
    fig, ax = plt.subplots(figsize=(12.8, 4.0), dpi=135)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 34)
    ax.axis("off")

    # Outer container card
    outer = mpatches.FancyBboxPatch((0.6, 0.6), 98.8, 32.8, boxstyle="round,pad=0.3,rounding_size=1.2",
                                    fc="#FFFFFF", ec="#CBD5E1", lw=1.4)
    ax.add_patch(outer)

    # Top header bar
    hdr_bg = mpatches.FancyBboxPatch((0.8, 28.2), 98.4, 5.0, boxstyle="round,pad=0.1,rounding_size=1.0",
                                     fc="#F8FAFC", ec="#E2E8F0", lw=1.0)
    ax.add_patch(hdr_bg)

    # Badge pill
    badge_patch = mpatches.FancyBboxPatch((2.0, 29.2), 15.6, 3.0, boxstyle="round,pad=0.1,rounding_size=0.6",
                                          fc="#1A73E8", ec="none")
    ax.add_patch(badge_patch)
    ax.text(9.8, 30.7, badge, ha="center", va="center", color="#FFFFFF", fontsize=8.0, fontweight="bold", fontfamily=font_name)

    # Title and right subtitle
    ax.text(18.6, 30.7, title, ha="left", va="center", color="#0F172A", fontsize=9.4, fontweight="bold", fontfamily=font_name)
    ax.text(97.6, 30.7, subtitle, ha="right", va="center", color="#475569", fontsize=7.6, fontweight="bold", fontfamily=font_name)

    # 4 Stage/Step columns
    n = len(columns)
    margin_x = 2.2
    gap = 2.2
    col_w = (100 - 2 * margin_x - (n - 1) * gap) / n

    for idx, col in enumerate(columns):
        x0 = margin_x + idx * (col_w + gap)
        y0 = 2.0
        h = 24.8
        color = col["color"]

        # Column container
        col_bg = mpatches.FancyBboxPatch((x0, y0), col_w, h, boxstyle="round,pad=0.15,rounding_size=0.9",
                                         fc="#F8FAFC", ec="#E2E8F0", lw=1.1)
        ax.add_patch(col_bg)

        # Column header ribbon
        col_hdr = mpatches.FancyBboxPatch((x0 + 0.6, y0 + h - 4.2), col_w - 1.2, 3.4,
                                          boxstyle="round,pad=0.1,rounding_size=0.6", fc=color, ec="none")
        ax.add_patch(col_hdr)
        ax.text(x0 + col_w / 2, y0 + h - 2.5, col["header"], ha="center", va="center",
                color="#FFFFFF", fontsize=8.6, fontweight="bold", fontfamily=font_name)

        # Two inner sub-cards per column
        cards = col["cards"]
        card_h = 9.2
        for c_idx, card in enumerate(cards):
            cy = y0 + h - 4.8 - (c_idx + 1) * card_h - c_idx * 0.9
            sub_box = mpatches.FancyBboxPatch((x0 + 0.8, cy), col_w - 1.6, card_h,
                                              boxstyle="round,pad=0.1,rounding_size=0.6",
                                              fc="#FFFFFF", ec="#CBD5E1", lw=0.9)
            ax.add_patch(sub_box)
            ax.text(x0 + 1.6, cy + card_h - 1.7, card["title"], ha="left", va="center",
                    color="#0F172A", fontsize=8.1, fontweight="bold", fontfamily=font_name)
            if card.get("code"):
                ax.text(x0 + 1.6, cy + card_h - 3.8, card["code"], ha="left", va="center",
                        color=color, fontsize=7.4, fontweight="bold", fontfamily=font_name)
            for b_i, b_line in enumerate(card.get("bullets", [])[:2]):
                ax.text(x0 + 1.6, cy + card_h - 5.8 - b_i * 1.7, f"• {b_line}", ha="left", va="center",
                        color="#334155", fontsize=7.2, fontfamily=font_name)

        # Arrow to next column
        if idx < n - 1:
            ax.annotate("", xy=(x0 + col_w + gap - 0.2, y0 + h / 2), xytext=(x0 + col_w + 0.2, y0 + h / 2),
                        arrowprops={"arrowstyle": "-|>,head_length=0.5,head_width=0.35", "color": "#1A73E8", "lw": 1.8})

    plt.subplots_adjust(left=0.01, right=0.99, top=0.99, bottom=0.01)
    out_path = ASSETS_DIR / filename
    fig.savefig(out_path, dpi=135, facecolor="#FFFFFF")
    plt.close(fig)
    print(f"[GENERATED] {out_path.name} ({out_path.stat().st_size // 1024} KB)")


BANNERS = [
    # Stage 0 KO & EN
    (
        "stage0_overview_flow_ko.png", "STAGE 0 · OVERVIEW",
        "엔터프라이즈 에이전틱 온톨로지 5-Stage × 8-Phase 전체 아키텍처",
        "준비 → 분석 → 파싱 → 통합 → 구축 → 에이전트 → 답변 → 검증",
        [
            {"header": "Stage 1 · 준비 & 분석 (Phase 1–2)", "color": "#1A73E8", "cards": [
                {"title": "1. 원천 자산 스코핑 & 스키마 설계", "code": "6 CSVs · 2 Policy MDs · 10 BQ Tables",
                 "bullets": ["Golden CQ 5종 · Boundary 10건 정의", "Terraform 기반 BigQuery DW 프로비저닝"]},
                {"title": "2. 데이터 탐색 & 비식별 거버넌스", "code": "stage1_resource_check",
                 "bullets": ["CUST_DEMO_001~006 비식별 검증", "정답 검증 SQL(verification_sql) 대조"]},
            ]},
            {"header": "Stage 2 · 파싱 & 통합 (Phase 3–4)", "color": "#0284c7", "cards": [
                {"title": "3. 구조화 파싱 & 해시 앵커링", "code": "DOC_CHUNK_001~005 · anchor_<12hex>",
                 "bullets": ["마크다운 조항별 결정론적 SHA-256 해시", "3-Layer LLM-Wiki (summary/entities/rules)"]},
                {"title": "4. 시맨틱 브릿지 & 규칙 통합", "code": "tb_domain_rules · edge_rule_applies_to_plan",
                 "bullets": ["Entity=Node, Concept=Edge 매핑", "4개 도메인 규칙 ↔ 6개 요금제 바인딩"]},
            ]},
            {"header": "Stage 3 · 그래프 구축 (Phase 5)", "color": "#0d9488", "cards": [
                {"title": "5a. Zero-ETL 프로퍼티 그래프 DDL", "code": "STARTER_ONTOLOGY_GRAPH (6N × 4E)",
                 "bullets": ["BigQuery Graph & Spanner Graph DDL", "데이터 복제 없이 원장·규칙 뷰 결합"]},
                {"title": "5b. 다중 홉 ISO GQL & NL2GQL", "code": "MATCH (c)-[:USES_DEVICE]->(d)...",
                 "bullets": ["25 노드 · 29 엣지 토폴로지 탐색", "바인딩 변수 기반 GQL 실행 & 스키마 가드"]},
            ]},
            {"header": "Stage 4–5 · 에이전트 & 검증 (Phase 6–8)", "color": "#188038", "cards": [
                {"title": "6–7. 8종 MCP & 2-Pass AI FDE", "code": "DomainMcpServer · AiFdeAgentEngine",
                 "bullets": ["슬롯 카탈로그 검증 & SQL 결정론 산식", "GROUNDED / INSUFFICIENT / NOT_FOUND"]},
                {"title": "8. 엔드투엔드 리니지 & 배포 게이트", "code": "stage5_resource_check",
                 "bullets": ["Source → Chunk → Rule → Contract → CQ", "Golden CQ 5/5 · Boundary 50회 게이트"]},
            ]},
        ],
    ),
    (
        "stage0_overview_flow_en.png", "STAGE 0 · OVERVIEW",
        "Enterprise Agentic Ontology 5-Stage × 8-Phase Architecture",
        "Prepare → Analyze → Parse → Integrate → Build → Agent → Answer → Verify",
        [
            {"header": "Stage 1 · Prepare & Analyze (P1–P2)", "color": "#1A73E8", "cards": [
                {"title": "1. Asset Scoping & Schema Design", "code": "6 CSVs · 2 Policy MDs · 10 BQ Tables",
                 "bullets": ["Define 5 Golden CQs & 10 Boundary Cases", "Terraform-managed BigQuery DW tables"]},
                {"title": "2. Data Profiling & Governance", "code": "stage1_resource_check",
                 "bullets": ["Verify CUST_DEMO_001~006 de-identification", "Audit ground-truth verification_sql"]},
            ]},
            {"header": "Stage 2 · Parse & Integrate (P3–P4)", "color": "#0284c7", "cards": [
                {"title": "3. Structural Parsing & Anchoring", "code": "DOC_CHUNK_001~005 · anchor_<12hex>",
                 "bullets": ["Deterministic SHA-256 paragraph anchors", "3-Layer LLM-Wiki (summary/entities/rules)"]},
                {"title": "4. Semantic Bridge & Rule Binding", "code": "tb_domain_rules · edge_rule_applies_to_plan",
                 "bullets": ["Entity=Node, Concept=Edge mapping", "Bind 4 codified rules to 6 tariff plans"]},
            ]},
            {"header": "Stage 3 · Build Graph (Phase 5)", "color": "#0d9488", "cards": [
                {"title": "5a. Zero-ETL Property Graph DDL", "code": "STARTER_ONTOLOGY_GRAPH (6N × 4E)",
                 "bullets": ["BigQuery Graph & Spanner Graph DDLs", "Zero-copy projection over 10 BQ tables"]},
                {"title": "5b. Multi-Hop ISO GQL & NL2GQL", "code": "MATCH (c)-[:USES_DEVICE]->(d)...",
                 "bullets": ["25 nodes & 29 directed edges topology", "Parameterized GQL execution & schema guard"]},
            ]},
            {"header": "Stage 4–5 · Agent & Verify (P6–P8)", "color": "#188038", "cards": [
                {"title": "6–7. 8-Tool MCP & 2-Pass Agent", "code": "DomainMcpServer · AiFdeAgentEngine",
                 "bullets": ["Live catalog slot validation & SQL math", "GROUNDED / INSUFFICIENT / NOT_FOUND"]},
                {"title": "8. End-to-End Lineage & Release Gate", "code": "stage5_resource_check",
                 "bullets": ["Source → Chunk → Rule → Contract → CQ", "Golden CQ 5/5 & 50-Trial Boundary Gate"]},
            ]},
        ],
    ),
    # Stage 1 KO & EN
    (
        "stage1_prepare_analyze_flow_ko.png", "STAGE 1 · PREPARE & ANALYZE",
        "원천 자산 스코핑 · 10개 테이블 스키마 설계 · 데이터 탐색 및 Golden CQ 정의",
        "Phase 1 (준비) & Phase 2 (분석) · Step 1.1 – Step 1.2",
        [
            {"header": "1. 역량 질문 & 경계 시나리오 설계", "color": "#1A73E8", "cards": [
                {"title": "Golden CQ 5종 정의", "code": "golden_competency_questions.json",
                 "bullets": ["CQ-01~05 정답 수치(expected_math) 명세", "독립 검증 SQL(verification_sql) 작성"]},
                {"title": "Boundary Case 10건 정의", "code": "boundary_cases.json",
                 "bullets": ["파라미터 누락(MISSING_REQUIRED_PARAM)", "미등록 엔티티(OUT_OF_DOMAIN_ENTITY)"]},
            ]},
            {"header": "2. 정형 CSV 6종 & 가이드 2종 준비", "color": "#0284c7", "cards": [
                {"title": "정형 마스터 & 브릿지 CSV", "code": "devices / plans / subsidies / contracts",
                 "bullets": ["마스터 원장 4종 + 규칙/엣지 CSV 2종", "비식별 고객 ID(CUST_DEMO_001~006) 적용"]},
                {"title": "비정형 정책 가이드 마크다운", "code": "sample_policy / welfare_exemption.md",
                 "bullets": ["180일 의무유지 · 일할 차액정산 산식", "시니어/복지 감면 · 24개월 TCO 비교 규칙"]},
            ]},
            {"header": "3. BigQuery 10개 테이블 스키마 검증", "color": "#0d9488", "cards": [
                {"title": "스키마 블루프린트 & 카탈로그", "code": "INFORMATION_SCHEMA.COLUMNS",
                 "bullets": ["4 마스터(22행) · 2 지식(9행) · 4 엣지(31행)", "PK/FK 참조 무결성 및 컬럼 타입 점검"]},
                {"title": "Stage 1 리소스 검증 실행", "code": "stage1_resource_check",
                 "bullets": ["profile_tables · scan_guides 실행", "prune_noise · tag_pii_governance 검증"]},
            ]},
            {"header": "4. 데이터 프로파일링 & Gate 1 통과", "color": "#188038", "cards": [
                {"title": "정형·비정형 분포 시각 탐색", "code": "%%bqsql + Heatmaps & Bar Charts",
                 "bullets": ["고객별 경과일 vs 180일 기준선 차트", "단말×요금제 실구매가 및 용어 빈도 히트맵"]},
                {"title": "Gate 1 품질 검증 완료", "code": "H.check_cq_sql() → 5/5 Match",
                 "bullets": ["PII 위반 0건 · 10개 테이블 적재 완료", "Stage 2 파싱·위키 통합 단계로 인계"]},
            ]},
        ],
    ),
    (
        "stage1_prepare_analyze_flow_en.png", "STAGE 1 · PREPARE & ANALYZE",
        "Raw Asset Scoping, 10-Table Schema Blueprint, Data Profiling & Golden CQs",
        "Phase 1 (Prepare) & Phase 2 (Analyze) · Step 1.1 – Step 1.2",
        [
            {"header": "1. Golden CQ & Boundary Design", "color": "#1A73E8", "cards": [
                {"title": "5 Golden Competency Questions", "code": "golden_competency_questions.json",
                 "bullets": ["Define expected_math for CQ-01..CQ-05", "Author ground-truth verification_sql"]},
                {"title": "10 Boundary Test Scenarios", "code": "boundary_cases.json",
                 "bullets": ["Missing slots (MISSING_REQUIRED_PARAM)", "Unknown entities (OUT_OF_DOMAIN_ENTITY)"]},
            ]},
            {"header": "2. Raw CSV & Policy Guide Inputs", "color": "#0284c7", "cards": [
                {"title": "6 Structured CSV Files", "code": "devices / plans / subsidies / contracts",
                 "bullets": ["4 master ledgers + 2 rule/edge CSVs", "De-identified IDs (CUST_DEMO_001~006)"]},
                {"title": "2 Unstructured Policy Guides", "code": "sample_policy / welfare_exemption.md",
                 "bullets": ["180-day retention & prorated clawback math", "Senior/welfare exemption & 24M TCO rules"]},
            ]},
            {"header": "3. BigQuery 10-Table Schema Check", "color": "#0d9488", "cards": [
                {"title": "Schema Blueprint & Metadata", "code": "INFORMATION_SCHEMA.COLUMNS",
                 "bullets": ["4 master (22r), 2 knowledge (9r), 4 edge (31r)", "Verify PK/FK columns and data types"]},
                {"title": "Stage 1 Resource Verification Execution", "code": "stage1_resource_check",
                 "bullets": ["Run profile_tables & scan_guides", "Verify prune_noise & tag_pii_governance"]},
            ]},
            {"header": "4. Profiling & Gate 1 Readiness", "color": "#188038", "cards": [
                {"title": "Visual Distribution Profiling", "code": "%%bqsql + Heatmaps & Bar Charts",
                 "bullets": ["Customer elapsed days vs. 180d threshold", "Device×Plan net price & term heatmaps"]},
                {"title": "Gate 1 Verification Passed", "code": "H.check_cq_sql() → 5/5 Match",
                 "bullets": ["0 PII violations & 10 tables verified", "Handoff to Stage 2 Parse & Integrate"]},
            ]},
        ],
    ),
    # Stage 2 KO & EN
    (
        "stage2_parse_integrate_flow_ko.png", "STAGE 2 · PARSE & INTEGRATE",
        "비정형 정책 가이드 SHA-256 해시 청킹 · 3-Layer LLM-Wiki & 시맨틱 그래프 통합",
        "Phase 3 (파싱) & Phase 4 (통합) · Step 2.1 – Step 2.2",
        [
            {"header": "1. 구조화 파싱 & SHA-256 해시 앵커", "color": "#1A73E8", "cards": [
                {"title": "문단 단위 결정론적 청킹", "code": "pipeline/ingest.py · DOC_CHUNK_001~005",
                 "bullets": ["원시 마크다운 섹션·표 구조 원형 보존", "SHA-256(anchor_<12hex>) 위변조 검증"]},
                {"title": "BigQuery 청크 테이블 동기화", "code": "tb_doc_chunks (5 rows)",
                 "bullets": ["실시간 재계산 해시 vs 저장 해시 1:1 대조", "Tier_1_Authoritative 신뢰 등급 부여"]},
            ]},
            {"header": "2. Karpathy 3-Layer LLM-Wiki", "color": "#9334E6", "cards": [
                {"title": "계층형 마크다운 지식 위키 컴파일", "code": "summary / entities / concepts / rules.md",
                 "bullets": ["L1 도메인 요약 · L2 핵심 엔티티 사전", "L3 관계 개념(Concept) 및 결정론 규칙 명세"]},
                {"title": "GCS 버킷 & 매니페스트 동기화", "code": "gs://seanjung-poc-starter-ontology/",
                 "bullets": ["8개 위키·온톨로지 객체 GCS 동기화", "stage2_resource_check 검증"]},
            ]},
            {"header": "3. 도메인 규칙 & 시맨틱 브릿지 통합", "color": "#F9AB00", "cards": [
                {"title": "Gemini 후보 트리플 추출 & 검수", "code": "H.propose_triples() · gemini-3.8-flash",
                 "bullets": ["정책 본문에서 주어-관계-목적어 후보 도출", "표준 엣지 레이블(APPLIES_TO_PLAN 등) 매핑"]},
                {"title": "정형 요금제 ↔ 비정형 규칙 결합", "code": "tb_domain_rules · edge_rule_applies_to_plan",
                 "bullets": ["4개 핵심 규칙(condition/formula_expr)", "6개 요금제에 12개 시맨틱 엣지 바인딩"]},
            ]},
            {"header": "4. 시맨틱 온톨로지 그래프 도식화", "color": "#0d9488", "cards": [
                {"title": "Entity=Node · Concept=Edge 표준", "code": "ontology.jsonld · vis_semantic_graph",
                 "bullets": ["Sky Blue 시맨틱 허브 중심 4계층 구조", "규칙 → 요금제 / 규칙 ⇢ 근거 청크 시각화"]},
                {"title": "Gate 2 통과 & Track 분기", "code": "Track 1 → Stage 4 / Track 2·3 → Stage 3",
                 "bullets": ["5개 청크 해시 일치 및 브릿지 무결성 확인", "물리 프로퍼티 그래프 구축 단계로 인계"]},
            ]},
        ],
    ),
    (
        "stage2_parse_integrate_flow_en.png", "STAGE 2 · PARSE & INTEGRATE",
        "Policy Guide SHA-256 Chunking, 3-Layer LLM-Wiki & Semantic Graph Integration",
        "Phase 3 (Parse) & Phase 4 (Integrate) · Step 2.1 – Step 2.2",
        [
            {"header": "1. Structural Parsing & SHA-256", "color": "#1A73E8", "cards": [
                {"title": "Deterministic Section Chunking", "code": "pipeline/ingest.py · DOC_CHUNK_001~005",
                 "bullets": ["Preserve Markdown headings and tables", "Compute SHA-256 (anchor_<12hex>) hashes"]},
                {"title": "BigQuery Chunk Table Sync", "code": "tb_doc_chunks (5 rows)",
                 "bullets": ["Verify live recomputed vs. stored hashes", "Assign Tier_1_Authoritative provenance"]},
            ]},
            {"header": "2. Karpathy 3-Layer LLM-Wiki", "color": "#9334E6", "cards": [
                {"title": "Compile Hierarchical Wiki Files", "code": "summary / entities / concepts / rules.md",
                 "bullets": ["L1 Domain Overview · L2 Core Entities", "L3 Semantic Concepts & Codified Rules"]},
                {"title": "GCS Bucket & Manifest Sync", "code": "gs://seanjung-poc-starter-ontology/",
                 "bullets": ["Sync 8 wiki & JSON-LD objects to GCS", "Verify via stage2_resource_check"]},
            ]},
            {"header": "3. Rule & Semantic Bridge Binding", "color": "#F9AB00", "cards": [
                {"title": "Gemini Candidate Triple Extraction", "code": "H.propose_triples() · gemini-3.8-flash",
                 "bullets": ["Extract subject-relation-object triples", "Align with canonical edge labels"]},
                {"title": "Bind Structured Plans to Rules", "code": "tb_domain_rules · edge_rule_applies_to_plan",
                 "bullets": ["4 codified rules (condition/formula_expr)", "12 APPLIES_TO_PLAN semantic bridge edges"]},
            ]},
            {"header": "4. Semantic Ontology Schematic", "color": "#0d9488", "cards": [
                {"title": "Entity=Node · Concept=Edge Design", "code": "ontology.jsonld · vis_semantic_graph",
                 "bullets": ["4-column layout with Sky Blue Semantic Hub", "Visualize Rule → Plan & Rule ⇢ DocChunk"]},
                {"title": "Gate 2 Passed & Track Routing", "code": "Track 1 → Stage 4 / Track 2·3 → Stage 3",
                 "bullets": ["100% hash match across all 5 chunks", "Handoff to Stage 3 Property Graph build"]},
            ]},
        ],
    ),
    # Stage 3 KO & EN
    (
        "stage3_property_graph_flow_ko.png", "STAGE 3 · BUILD PROPERTY GRAPH",
        "Zero-ETL 물리 프로퍼티 그래프 (BigQuery / Spanner) 구축 및 파라미터 기반 ISO GQL",
        "Phase 5 (물리 그래프 구축 & GQL 탐색) · Step 3.1 – Step 3.2",
        [
            {"header": "1. 6 Node × 4 Edge 메타모델 설계", "color": "#1A73E8", "cards": [
                {"title": "Zero-ETL 그래프 뷰 아키텍처", "code": "STARTER_ONTOLOGY_GRAPH",
                 "bullets": ["별도 DB 복제 없이 BigQuery 10개 테이블 투영", "INFORMATION_SCHEMA.PROPERTY_GRAPHS"]},
                {"title": "6개 노드 & 4개 방향성 엣지", "code": "Contract / Device / Plan / Subsidy / Rule / Chunk",
                 "bullets": ["USES_DEVICE · SUBSCRIBES_PLAN", "HAS_SUBSIDY_POLICY · APPLIES_TO_PLAN"]},
            ]},
            {"header": "2. 듀얼 그래프 DDL & 무결성 검증", "color": "#0284c7", "cards": [
                {"title": "BigQuery & Spanner Graph DDL", "code": "pipeline/graph_builder.py",
                 "bullets": ["create_property_graph.sql (ISO SQL:2023)", "create_spanner_graph.sql (Spanner 호환)"]},
                {"title": "Stage 3 리소스 검증 검증", "code": "stage3_resource_check",
                 "bullets": ["노드 PK 중복 키 0건(31 rows) 실측 검증", "25개 연결 노드 · 29개 엣지 토폴로지 도식"]},
            ]},
            {"header": "3. 바인딩 변수 기반 다중 홉 ISO GQL", "color": "#0d9488", "cards": [
                {"title": "실행 GQL 문장 & 바인딩 변수 명시", "code": "H.run_gql_example(gql, variables)",
                 "bullets": ["변수명 · 바인딩 값 · 출처 테이블 투명 출력", "다이아몬드 매칭 & 1~2홉 가변 경로 탐색"]},
                {"title": "GQL 단일 쿼리 위약금 산출", "code": "CUST_DEMO_001 → PLAN-5G-37 (120d)",
                 "bullets": ["현재/변경 지원금 차액 × 잔여일 비례 산식", "BigQuery Job ID 및 실행 시간(ms) 기록"]},
            ]},
            {"header": "4. Gemini NL2GQL & 스키마 가드", "color": "#188038", "cards": [
                {"title": "자연어 → ISO GQL 자동 생성·실행", "code": "H.nl2gql() · gemini-3.8-flash",
                 "bullets": ["라이브 그래프 스키마 기반 ISO GQL 합성", "생성된 GQL 문장 · 추출 변수 · 결과 표시"]},
                {"title": "미보유 스키마 질문 차단 가드", "code": "answerable = false (Schema Guard)",
                 "bullets": ["기지국 품질·해지 점수 등 미존재 속성 감지", "잘못된 쿼리 생성 차단 후 Stage 4 인계"]},
            ]},
        ],
    ),
    (
        "stage3_property_graph_flow_en.png", "STAGE 3 · BUILD PROPERTY GRAPH",
        "Zero-ETL Physical Property Graph (BigQuery / Spanner) & Parameterized ISO GQL",
        "Phase 5 (Build Property Graph & GQL Traversal) · Step 3.1 – Step 3.2",
        [
            {"header": "1. 6 Node × 4 Edge Metamodel", "color": "#1A73E8", "cards": [
                {"title": "Zero-ETL Graph View Projection", "code": "STARTER_ONTOLOGY_GRAPH",
                 "bullets": ["Project 10 BQ tables with zero data copy", "INFORMATION_SCHEMA.PROPERTY_GRAPHS"]},
                {"title": "6 Node Labels & 4 Edge Labels", "code": "Contract / Device / Plan / Subsidy / Rule / Chunk",
                 "bullets": ["USES_DEVICE · SUBSCRIBES_PLAN", "HAS_SUBSIDY_POLICY · APPLIES_TO_PLAN"]},
            ]},
            {"header": "2. Dual-Engine DDL & Integrity", "color": "#0284c7", "cards": [
                {"title": "BigQuery & Spanner Graph DDLs", "code": "pipeline/graph_builder.py",
                 "bullets": ["create_property_graph.sql (ISO SQL:2023)", "create_spanner_graph.sql (Cloud Spanner)"]},
                {"title": "Stage 3 Resource Verification Validation", "code": "stage3_resource_check",
                 "bullets": ["Verify 0 duplicate node keys (31 rows)", "Visualize 25-node, 29-edge full topology"]},
            ]},
            {"header": "3. Parameterized Multi-Hop ISO GQL", "color": "#0d9488", "cards": [
                {"title": "Explicit GQL Statement & Variables", "code": "H.run_gql_example(gql, variables)",
                 "bullets": ["Display bound variable names, values & types", "Diamond pattern & 1..2-hop ego subgraphs"]},
                {"title": "Single-Query GQL Penalty Math", "code": "CUST_DEMO_001 → PLAN-5G-37 (120d)",
                 "bullets": ["Compute prorated subsidy clawback in GQL", "Record live BigQuery Job ID & latency"]},
            ]},
            {"header": "4. Gemini NL2GQL & Schema Guard", "color": "#188038", "cards": [
                {"title": "Live Natural Language to ISO GQL", "code": "H.nl2gql() · gemini-3.8-flash",
                 "bullets": ["Synthesize standalone ISO GQL from schema", "Show generated GQL, bound filters & rows"]},
                {"title": "Out-of-Schema Query Guardrail", "code": "answerable = false (Schema Guard)",
                 "bullets": ["Reject unmodeled attributes (e.g. churn)", "Pass Gate 3 and hand off to Stage 4"]},
            ]},
        ],
    ),
    # Stage 4 KO & EN
    (
        "stage4_agent_mcp_flow_ko.png", "STAGE 4 · BUILD AGENT & ANSWER",
        "8종 모듈형 MCP 서버 · 카탈로그 슬롯 검증 & 2-Pass AI FDE 에이전트 답변 생성",
        "Phase 6 (에이전트 구축) & Phase 7 (근거 기반 답변) · Step 4.1 – Step 4.2",
        [
            {"header": "1. 카탈로그 기반 슬롯 검증기", "color": "#1A73E8", "cards": [
                {"title": "실시간 엔티티 카탈로그 대조", "code": "DomainMcpServer.resolve_params()",
                 "bullets": ["BigQuery 원장의 단말·요금제·고객 ID 대조", "미등록 엔티티(QuantumFold 등) 즉시 제거"]},
                {"title": "Gemini Pass 1 의도·슬롯 분해", "code": "step_1_decomposition (JSON)",
                 "bullets": ["자연어 질문에서 하위 목표(Sub-Goals) 도출", "추출 슬롯과 정규식 검증 슬롯 교차 병합"]},
            ]},
            {"header": "2. 8종 모듈형 MCP 도구 스위트", "color": "#0284c7", "cards": [
                {"title": "Stage 리소스 검증 5종", "code": "stage1_resource_check ~ stage5_resource_check",
                 "bullets": ["온톨로지 준비·파싱·그래프·에이전트·평가", "steps 파라미터 기반 선택 실행 지원"]},
                {"title": "Runtime 도메인 MCP 3종", "code": "lookup_profile · calculate_penalty · query_graph",
                 "bullets": ["고객 약정 조회 · 180일 위약금/24M TCO 산식", "ISO GQL 문장·변수 출력 및 청크 앵커 인출"]},
            ]},
            {"header": "3. 가드레일 상태 분기 (Step 3)", "color": "#F9AB00", "cards": [
                {"title": "정상 근거 확보 (GROUNDED)", "code": "answer_status = GROUNDED",
                 "bullets": ["BigQuery 행/경로 및 SHA-256 앵커 확인", "결정론적 SQL 산식 결과만 답변에 사용"]},
                {"title": "경계 조건 차단 가드레일", "code": "INSUFFICIENT_PARAMETERS | MATCH_NOT_FOUND",
                 "bullets": ["필수 슬롯(고객/단말/경과일) 누락 시 역질문", "미등록 고객/단말 조건 불일치 시 계산 차단"]},
            ]},
            {"header": "4. Gemini Pass 2 근거 합성 답변", "color": "#188038", "cards": [
                {"title": "출처·앵커·Job ID 인용 합성", "code": "AiFdeAgentEngine.execute_cycle()",
                 "bullets": ["산출 금액 + DOC_CHUNK 해시 앵커 명시", "실행된 모든 BigQuery Job ID 푸터 기록"]},
                {"title": "경과일 시뮬레이션 & 지연시간 분석", "code": "30~200일 위약금 곡선 · LLM vs BQ ms",
                 "bullets": ["180일 도래 시 위약금 0원 면제 전환 확인", "Stage 5 리니지·벤치마크 검증으로 인계"]},
            ]},
        ],
    ),
    (
        "stage4_agent_mcp_flow_en.png", "STAGE 4 · BUILD AGENT & ANSWER",
        "8-Tool Modular MCP Server, Catalog Slot Guard & 2-Pass AI FDE Agent Execution",
        "Phase 6 (Build Agent) & Phase 7 (Grounded Answering) · Step 4.1 – Step 4.2",
        [
            {"header": "1. Catalog-Validated Slot Guard", "color": "#1A73E8", "cards": [
                {"title": "Live BigQuery Catalog Lookup", "code": "DomainMcpServer.resolve_params()",
                 "bullets": ["Match devices, plans & customer IDs", "Strip unknown entities (e.g. QuantumFold)"]},
                {"title": "Gemini Pass 1 Decomposition", "code": "step_1_decomposition (JSON)",
                 "bullets": ["Decompose query into ordered sub-goals", "Merge LLM slots with regex-verified slots"]},
            ]},
            {"header": "2. 8-Tool Modular MCP Suite", "color": "#0284c7", "cards": [
                {"title": "5 Stage Resource Verification Checks", "code": "stage1_resource_check ~ stage5_resource_check",
                 "bullets": ["Automate Stage 1..5 lifecycle steps", "Support selective step array execution"]},
                {"title": "3 Runtime Domain MCP Tools", "code": "lookup_profile · calculate_penalty · query_graph",
                 "bullets": ["Customer profile & 180d penalty / 24M TCO", "Execute parameterized ISO GQL & fetch chunks"]},
            ]},
            {"header": "3. Guardrail Verdict (Step 3)", "color": "#F9AB00", "cards": [
                {"title": "Verified Grounding (GROUNDED)", "code": "answer_status = GROUNDED",
                 "bullets": ["Confirm BQ rows/paths & SHA-256 anchors", "Bind deterministic SQL figures to context"]},
                {"title": "Boundary Guardrail States", "code": "INSUFFICIENT_PARAMETERS | MATCH_NOT_FOUND",
                 "bullets": ["Request missing slots when context is incomplete", "Refuse calculation on unknown entities"]},
            ]},
            {"header": "4. Gemini Pass 2 Cited Synthesis", "color": "#188038", "cards": [
                {"title": "Grounded Answer with Citations", "code": "AiFdeAgentEngine.execute_cycle()",
                 "bullets": ["Cite exact KRW math & DOC_CHUNK anchors", "Append executed BigQuery Job IDs & telemetry"]},
                {"title": "Penalty Curve & Latency Analysis", "code": "Days 30..200 Curve · LLM vs. BQ ms",
                 "bullets": ["Verify linear decay to 0 KRW at day 180", "Hand off to Stage 5 Lineage & Release Gate"]},
            ]},
        ],
    ),
    # Stage 5 KO & EN
    (
        "stage5_lineage_eval_flow_ko.png", "STAGE 5 · VERIFY & RELEASE GATE",
        "End-to-End 데이터 리니지 · Golden CQ 감사 & Boundary 50회 배포 게이트",
        "Phase 8 (검증 및 프로덕션 릴리스 게이트) · Step 5.1 – Step 5.2",
        [
            {"header": "1. End-to-End 데이터 리니지", "color": "#1A73E8", "cards": [
                {"title": "원천 파일 → CQ 답변 전 구간 추적", "code": "Source → DocChunk → Rule → Contract → CQ",
                 "bullets": ["Tier 0 원시 파일(CSV/MD) · Tier 1 해시 청크", "Tier 2 도메인 규칙 · Tier 3 약정 · Tier 4 CQ"]},
                {"title": "멀티파타이트 리니지 그래프 도식", "code": "H.lineage_graph() · 18 Lineage Rows",
                 "bullets": ["정책 조항 변경 시 영향받는 요금제·고객·CQ 식별", "stage5_resource_check 실시간 검증"]},
            ]},
            {"header": "2. Golden CQ 5종 결정론적 감사", "color": "#0284c7", "cards": [
                {"title": "4대 채점 기준 자동 대조", "code": "pipeline/validator.py · H.recheck_cq()",
                 "bullets": ["1) verification_sql == expected_math 확인", "2) 답변 내 정답 수치 · 3) 청크 인용 · 4) GROUNDED"]},
                {"title": "Golden CQ 5/5 (100.0%) 통과", "code": "cq_benchmark_report.json",
                 "bullets": ["CQ-01~05 전 문항 SQL 정답과 1:1 일치", "실시간 CQ-02 재검증(recheck_cq) 통과"]},
            ]},
            {"header": "3. Boundary 10건 × 5회(50회) 평가", "color": "#9334E6", "cards": [
                {"title": "반복 실행 안정성 3대 지표 측정", "code": "boundary_benchmark_results.json (50 Trials)",
                 "bullets": ["성공률(Success) · 일관성(Consistency)", "도구 선택 의도 안정성(Intent Stability)"]},
                {"title": "실패 원인 분류 체계 (Taxonomy)", "code": "root_cause_code 집계 분석",
                 "bullets": ["MISSING_REQUIRED_PARAM · TEMPORAL_BOUNDARY", "OUT_OF_DOMAIN_ENTITY · POLICY_CONFLICT"]},
            ]},
            {"header": "4. Gate 1 ~ Gate 5 최종 배포 승인", "color": "#188038", "cards": [
                {"title": "전 단계 릴리스 게이트 체크리스트", "code": "H.gate_checklist_table() → ALL PASS",
                 "bullets": ["Gate 1(자산) · Gate 2(위키) · Gate 3(그래프)", "Gate 4(MCP/에이전트) · Gate 5(CQ/Boundary)"]},
                {"title": "Cloud Run & GitHub 프로덕션 운영", "code": "Terraform IaC · 2-Step Git Branch Flow",
                 "bullets": ["검증 완료된 온톨로지·에이전트 패키지 배포", "지속적 회귀 감사(Continuous Regression Gate)"]},
            ]},
        ],
    ),
    (
        "stage5_lineage_eval_flow_en.png", "STAGE 5 · VERIFY & RELEASE GATE",
        "End-to-End Data Lineage, Golden CQ Audit & 50-Trial Release Gate",
        "Phase 8 (Verification & Production Release Gate) · Step 5.1 – Step 5.2",
        [
            {"header": "1. End-to-End Data Lineage", "color": "#1A73E8", "cards": [
                {"title": "Full Provenance Chain Tracking", "code": "Source → DocChunk → Rule → Contract → CQ",
                 "bullets": ["Tier 0 Raw CSV/MD · Tier 1 SHA-256 Chunk", "Tier 2 DomainRule · Tier 3 Contract · Tier 4 CQ"]},
                {"title": "Multipartite Lineage Graph", "code": "H.lineage_graph() · 18 Lineage Rows",
                 "bullets": ["Trace policy edits to impacted plans & CQs", "Verified via stage5_resource_check"]},
            ]},
            {"header": "2. 5 Golden CQs Deterministic Audit", "color": "#0284c7", "cards": [
                {"title": "4-Check Automated Grading Oracle", "code": "pipeline/validator.py · H.recheck_cq()",
                 "bullets": ["1) verification_sql == expected_math", "2) Exact numbers · 3) Chunk cited · 4) GROUNDED"]},
                {"title": "Golden CQ 5/5 (100.0%) Passed", "code": "cq_benchmark_report.json",
                 "bullets": ["All 5 Golden CQs match SQL ground truth", "Live CQ-02 re-audit (recheck_cq) verified"]},
            ]},
            {"header": "3. 10 × 5 (50-Trial) Boundary Suite", "color": "#9334E6", "cards": [
                {"title": "Multi-Trial Stability Metrics", "code": "boundary_benchmark_results.json (50 Trials)",
                 "bullets": ["Measure Success Rate & Consistency Rate", "Measure Tool Routing Intent Stability"]},
                {"title": "Diagnostic Failure Taxonomy", "code": "Group by root_cause_code",
                 "bullets": ["MISSING_REQUIRED_PARAM · TEMPORAL_BOUNDARY", "OUT_OF_DOMAIN_ENTITY · POLICY_CONFLICT"]},
            ]},
            {"header": "4. Gate 1 – Gate 5 Release Verdict", "color": "#188038", "cards": [
                {"title": "End-to-End Release Gate Checklist", "code": "H.gate_checklist_table() → ALL PASS",
                 "bullets": ["Gate 1 (Assets) · Gate 2 (Wiki) · Gate 3 (Graph)", "Gate 4 (Agent/MCP) · Gate 5 (CQ/Boundary)"]},
                {"title": "Production Cloud Run & GitHub", "code": "Terraform IaC · 2-Step Git Branch Flow",
                 "bullets": ["Deploy verified ontology & agent runtime", "Continuous regression gate on policy updates"]},
            ]},
        ],
    ),
]


def main():
    for fname, badge, title, subtitle, cols in BANNERS:
        font = CJK_FONT if fname.endswith("_ko.png") else "sans-serif"
        _draw_banner(fname, badge, title, subtitle, cols, font)


if __name__ == "__main__":
    main()
