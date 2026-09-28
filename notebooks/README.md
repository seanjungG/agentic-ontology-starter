# Agentic Ontology Starter — Interactive Bilingual Jupyter Notebooks (`Stage 0` ~ `Stage 5`, KO / EN)

> **🇰🇷 한국어 초기 화면 (Korean Overview Entrypoint)**: [`stage0_overview_walkthrough.ipynb`](./stage0_overview_walkthrough.ipynb) ｜ **🇺🇸 English Overview Entrypoint**: [`stage0_overview_walkthrough_en.ipynb`](./stage0_overview_walkthrough_en.ipynb)
>
> **Methodology Docs**: [한국어 (`METHODOLOGY_KO.md`)](../methodology/METHODOLOGY_KO.md) · [English (`METHODOLOGY_EN.md`)](../methodology/METHODOLOGY_EN.md) ｜ **Live Studio**: [`Agentic Ontology Studio`](https://agentic-ontology-starter-lwrlf7yogq-du.a.run.app)

---

## 1. 전체 8단계 엔지니어링 흐름 & 12종 한/영 노트북 네비게이션 (8-Phase Flow & Bilingual Navigation)

본 디렉터리의 **12개 실행형 Jupyter 노트북**(`0. Overview` 한/영 2종 + `Stage 1`~`Stage 5` 한/영 10종)은 단순 데이터 조회(EDA)에 머물지 않고, **엔터프라이즈 온톨로지 방법론의 8단계 엔지니어링 파이프라인(`1. 준비 → 2. 분석 → 3. 파싱 → 4. 통합 → 5. 구축 → 6. 에이전트 구축 → 7. 답변 → 8. 검증`)**을 단계별로 구현하면서, 그 중간마다 **실제 테이블 구조·중간 산출물·실데이터(`%%bqsql`)와 그래프 설계 도식**을 함께 확인할 수 있도록 구성되어 있습니다.

모든 노트북 상단과 하단에는 **한국어 ↔ 영어 버전 즉시 전환 링크**와 **이전/다음 Stage 이동 네비게이션 바**가 내장되어 있습니다.

| 8단계 엔지니어링 흐름 (8-Phase Flow) | 정본 Stage (Step) | 🇰🇷 한국어 노트북 (Korean `.ipynb`) | 🇺🇸 영문 노트북 (English `.ipynb`) | 방법론 가이드 (KO / EN) | 단계별 파이프라인 구현 · 중간 데이터 확인 · 그래프 설계 도식 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **0. 전체 흐름 초기 화면**<br>*(Master Entrypoint)* | **0. Overview**<br>(`Stage 0`–`5` Tour) | [`stage0_overview_walkthrough.ipynb`](./stage0_overview_walkthrough.ipynb) | [`stage0_overview_walkthrough_en.ipynb`](./stage0_overview_walkthrough_en.ipynb) | [KO](../methodology/METHODOLOGY_KO.md) · [EN](../methodology/METHODOLOGY_EN.md) | 8단계 엔지니어링 파이프라인 흐름도, 10개 테이블 스키마 블루프린트, Stage 1~5 MCP 실행, SHA-256 파싱 검증, 시맨틱/물리 그래프 토폴로지, 실시간 `nl2gql` & 에이전트 추론(`CQ-03`, `CQ-05`), Gate 1~5 체크리스트 |
| **1. 준비 (Prepare)**<br>**2. 분석 (Analyze)** | **Stage 1**<br>(`Step 1.1`–`1.2`) | [`stage1_asset_and_cq_ko.ipynb`](./stage1_asset_and_cq_ko.ipynb) | [`stage1_asset_and_cq_en.ipynb`](./stage1_asset_and_cq_en.ipynb) | [KO](../methodology/01_stage1_asset_and_cq_ko.md) · [EN](../methodology/01_stage1_asset_and_cq_en.md) | 원천 CSV/가이드 자산 인벤토리, `INFORMATION_SCHEMA.COLUMNS` 스키마 명세 & 10개 테이블 설계도, `mcp_stage1_asset_discovery`(PII 비식별화 검증), 약정·단말·요금제·지원금 데이터 탐색(`%%bqsql`) 및 히트맵, Golden CQ 5종 `verification_sql` 정답 대조 |
| **3. 파싱 (Parse)**<br>**4. 통합 (Integrate)** | **Stage 2**<br>(`Step 2.1`–`2.2`) | [`stage2_wiki_and_semantic_graph_ko.ipynb`](./stage2_wiki_and_semantic_graph_ko.ipynb) | [`stage2_wiki_and_semantic_graph_en.ipynb`](./stage2_wiki_and_semantic_graph_en.ipynb) | [KO](../methodology/02_stage2_wiki_and_semantic_graph_ko.md) · [EN](../methodology/02_stage2_wiki_and_semantic_graph_en.md) | `pipeline/ingest.py` 정규식 청킹 및 SHA-256 해시 앵커(`anchor_<12hex>`) 무결성 대조, Karpathy 3-Layer LLM-Wiki(`summary`, `entities`, `concepts`, `rules`) 컴파일 및 GCS 동기화, Gemini 후보 트리플 추출, `tb_domain_rules`·`edge_rule_applies_to_plan` 통합(`%%bqsql`) 및 시맨틱 그래프 도식(`Entity=Node`, `Concept=Edge`) |
| **5. 구축 (Build Graph)** | **Stage 3**<br>(`Step 3.1`–`3.2`) | [`stage3_property_graph_bigquery_spanner_ko.ipynb`](./stage3_property_graph_bigquery_spanner_ko.ipynb) | [`stage3_property_graph_bigquery_spanner_en.ipynb`](./stage3_property_graph_bigquery_spanner_en.ipynb) | [KO](../methodology/03_stage3_property_graph_ko.md) · [EN](../methodology/03_stage3_property_graph_en.md) | 6 Node × 4 Edge Zero-ETL 메타모델 설계도, `pipeline/graph_builder.py` 기반 BigQuery/Spanner Graph DDL 프로비저닝, `mcp_stage3_property_graph` 중복 키 `0건` 검증, 전체 물리 그래프 토폴로지(25 노드 · 29 엣지) & `CUST_DEMO_001` 1~2홉 서브그래프, 다중 홉 ISO GQL(`%%bqsql`) 및 Gemini `nl2gql` |
| **6. 에이전트 구축 (Agent)**<br>**7. 답변 (Answer)** | **Stage 4**<br>(`Step 4.1`–`4.2`) | [`stage4_agent_and_mcp_execution_ko.ipynb`](./stage4_agent_and_mcp_execution_ko.ipynb) | [`stage4_agent_and_mcp_execution_en.ipynb`](./stage4_agent_and_mcp_execution_en.ipynb) | [KO](../methodology/04_stage4_agent_and_mcp_ko.md) · [EN](../methodology/04_stage4_agent_and_mcp_en.md) | 2-Pass AI FDE 에이전트 & 8종 MCP 오케스트레이션 설계도, 카탈로그 기반 슬롯 파싱(`resolve_params`), 런타임 도메인 MCP 3종 직접 호출 및 30~200일 위약금 곡선 시뮬레이션, Golden CQ(`GROUNDED`) 및 가드레일(`INSUFFICIENT_PARAMETERS`, `MATCH_NOT_FOUND`) 4단계 실행 트레이스 |
| **8. 검증 (Verify & Gate)** | **Stage 5**<br>(`Step 5.1`–`5.2`) | [`stage5_lineage_and_evaluation_ko.ipynb`](./stage5_lineage_and_evaluation_ko.ipynb) | [`stage5_lineage_and_evaluation_en.ipynb`](./stage5_lineage_and_evaluation_en.ipynb) | [KO](../methodology/05_stage5_lineage_and_eval_ko.md) · [EN](../methodology/05_stage5_lineage_and_eval_en.md) | `mcp_stage5_lineage_and_eval` 실행, 4-Tier 리니지(`Source File → DocChunk → DomainRule → Contract → CQ`) 조인(`%%bqsql`) 및 멀티파타이트 그래프 도식, `pipeline/validator.py` Golden CQ 5종 실시간 재검증(`recheck_cq`), Boundary 10건×5회(50 Trials) 안정성 평가 및 Gate 1~5 최종 판정 |

---

## 2. 각 노트북의 4단 조화 구조 (Balanced 4-Part Structure per Stage)

모든 노트북은 다음 4가지 요소가 순서대로 맞물리도록 설계되어 있습니다:
1. **방법론 및 아키텍처 설계 도식 (Methodology & Design Schematic)**: 해당 Stage에서 수행하는 파이프라인 원리와 테이블/그래프/에이전트 설계 도식(`H.draw_eight_phase_flow()`, `H.draw_table_er_blueprint()`, `H.draw_semantic_design_graph()`, `H.draw_property_graph_metamodel()`, `H.draw_agent_architecture()`) 제시
2. **파이프라인 단계 및 Stage MCP 실행 (Pipeline & Stage MCP Execution)**: `pipeline/ingest.py`, `pipeline/graph_builder.py`, `pipeline/validator.py` 및 `mcp_stage1`~`mcp_stage5` 도구를 실제로 실행하여 변환·파싱·컴파일·검증 과정 시연
3. **중간 테이블 구조 및 실데이터 탐색 (`%%bqsql` BigFrames & Artifacts)**: 각 단계 전·후에 생성된 BigQuery 테이블(`starter_ontology_dw`), `STARTER_ONTOLOGY_GRAPH` 경로, JSON-LD/Wiki 아티팩트를 조회하고 차트·히트맵·네트워크 그래프로 시각화
4. **에이전트 추론 · GQL 실행 · 게이트 검증 (Agent, GQL & Gate Verification)**: Gemini `nl2gql`, 2-Pass `AiFdeAgentEngine` 4단계 트레이스, `recheck_cq` 정답 대조, ` notebook-guidance` 표준 요약(`Q&A`, `Data Analysis Key Findings`, `Insights or Next Steps`) 제공

---

## 3. 공통 헬퍼 및 생성/검증 스크립트 (`notebooks/`)

- [`nb_helpers.py`](./nb_helpers.py): BigFrames `%%bqsql` 인증 설정, 한/영 텍스트 헬퍼, 8단계 파이프라인·테이블 스키마·시맨틱 그래프·프로퍼티 그래프 메타모델·에이전트 아키텍처 도식 렌더러, `DOC_CHUNK` 실시간 파싱 검증기, 3-Layer Wiki 요약기, Gemini `nl2gql`, 4단계 에이전트 트레이스 뷰어, Gate 1~5 체크리스트 포함.
- [`nb_specs_s0_s2.py`](./nb_specs_s0_s2.py) & [`nb_specs_s3_s5.py`](./nb_specs_s3_s5.py): 상·하단 한/영 & Stage 네비게이션 바(`nav_header`, `nav_footer`) 및 `Stage 0`~`Stage 5` 한/영 12개 노트북 셀 정의.
- [`generate_notebooks.py`](./generate_notebooks.py): 12개 `.ipynb` 노트북 일괄 생성, `jupyter nbconvert --execute` 병렬 실행(`--workers`), PNG 어태치먼트 패킹 수행.
- [`validate_and_pack_notebooks.py`](./validate_and_pack_notebooks.py): `notebooks/assets/*.png` Base64 임베딩 및 `NBFormat v4.5` / `NBConvert v7.17.1` 무결성 검증.

---

## 4. 실행 및 재검증 방법 (How to Run & Validate)

```bash
# 1. 12개 노트북 전체 실환경 실행 (BigQuery + Property Graph + Vertex AI Gemini) 및 PNG 패킹
SSL_CERT_FILE=/etc/ssl/cert.pem .venv/bin/python notebooks/generate_notebooks.py --execute --workers 2

# 2. 특정 Stage 노트북만 선택 실행
SSL_CERT_FILE=/etc/ssl/cert.pem .venv/bin/python notebooks/generate_notebooks.py --only stage0 stage1 --execute

# 3. NBFormat v4.5 및 PNG 어태치먼트 무결성 검증
.venv/bin/python notebooks/validate_and_pack_notebooks.py
```
