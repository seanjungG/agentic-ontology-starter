# 5-Stage Agentic Ontology Methodology (`methodology/`)

> **방법론 저작권 및 비영리 라이선스 고지 (Methodology IP & Non-Commercial Notice — CC BY-NC-ND 4.0)**
> - **한국어**: 본 폴더(`methodology/`)에 수록된 **5-Stage 에이전틱 온톨로지 엔지니어링 방법론(8단계 엔지니어링 흐름 · 산출물 체계 D1.1~D5.5 · 3-Layer OKF 위키 · 듀얼 Property Graph · 8종 MCP 및 2-Pass 에이전트 · 4-Tier 리니지/경계값 평가 체계)**은 **CC BY-NC-ND 4.0(저작자표시-비영리-변경금지)** 라이선스로 보호됩니다. 개인 학습 및 비상업적 연구 외에 **타 기업/기관 대상 유상 컨설팅, SI 구축, 유상 PoC 딜리버리, 상업적 제안서/산출물 활용 및 무단 개작 배포를 엄격히 금지**합니다. 상업적 활용이나 고객사 프로젝트 적용이 필요한 경우 반드시 **[seanjung@google.com](mailto:seanjung@google.com)**으로 사전 논의하시기 바랍니다. ([`../LICENSE`](../LICENSE))
> - **English**: The **5-Stage Agentic Ontology Engineering Methodology** contained in this directory (`methodology/`) is protected under **Creative Commons Attribution-NonCommercial-NoDerivatives 4.0 International (CC BY-NC-ND 4.0)**. Any commercial use — including paid consulting, system integration (SI) delivery, paid PoCs, client deliverables, commercial proposals, or unauthorized derivative distribution — is strictly prohibited without prior written permission. For commercial or enterprise inquiries, please contact **[seanjung@google.com](mailto:seanjung@google.com)**. ([`../LICENSE`](../LICENSE))

이 폴더는 **5-Stage 에이전틱 온톨로지 구축 방법론**을 언어별 하위 폴더(`methodology/ko/` · `methodology/en/`)로 구분하여 담고 있습니다. 각 Stage 문서는 라이브 스튜디오 탭, MCP 도구, 실행 가능한 Jupyter 노트북(`notebooks/ko/` · `notebooks/en/`)과 1:1로 대응합니다.

This directory organizes the **5-Stage Agentic Ontology Engineering Methodology** into dedicated Korean (`methodology/ko/`) and English (`methodology/en/`) folders, aligned 1:1 with the interactive notebooks (`notebooks/ko/`, `notebooks/en/`), MCP tools, and Studio tabs.

---

## 1. 폴더 구조 및 전체 방법론 마스터 문서 (Directory Layout & Master Documents)

- **🇰🇷 한국어 방법론 폴더 (`methodology/ko/`)**: [ko/METHODOLOGY_KO.md](./ko/METHODOLOGY_KO.md) + Stage 1~5 상세 가이드 5종
- **🇺🇸 English Methodology Folder (`methodology/en/`)**: [en/METHODOLOGY_EN.md](./en/METHODOLOGY_EN.md) + Stage 1~5 Detailed Guides (100% English)
- **📊 교육용 Google Workspace Slides (18슬라이드 · `slides/ko/` & `slides/en/`)**: [slides/README.md](../slides/README.md) · [국문 `.pptx`](../slides/ko/agentic_ontology_methodology_training_ko.pptx) · [English `.pptx`](../slides/en/agentic_ontology_methodology_training_en.pptx) · [국문 HTML5 뷰어](../slides/ko/agentic_ontology_methodology_slides_ko.html) · [English HTML5 Viewer](../slides/en/agentic_ontology_methodology_slides_en.html)

---

## 2. Stage별 상세 가이드 · 스튜디오 · 노트북 매핑 (Stage Guide · Studio · Notebook Matrix)

### 2.1 🇰🇷 한국어 방법론 가이드 (`methodology/ko/`)

| Stage | 한국어 방법론 가이드 (`methodology/ko/`) | 대응 한국어 노트북 (`notebooks/ko/`) | 스튜디오 탭 | 영문 대칭 문서 (`methodology/en/`) |
| :---: | :--- | :--- | :--- | :--- |
| **공통 (Master)** | [ko/METHODOLOGY_KO.md](./ko/METHODOLOGY_KO.md) | [stage0_overview_walkthrough_ko.ipynb](../notebooks/ko/stage0_overview_walkthrough_ko.ipynb) | [`0. Overview`](https://agentic-ontology-starter-lwrlf7yogq-du.a.run.app/?tab=overview) | [en/METHODOLOGY_EN.md](./en/METHODOLOGY_EN.md) |
| **Stage 1** | [ko/01_stage1_asset_and_cq_ko.md](./ko/01_stage1_asset_and_cq_ko.md) | [stage1_asset_and_cq_ko.ipynb](../notebooks/ko/stage1_asset_and_cq_ko.ipynb) | [`Stage 1. Asset`](https://agentic-ontology-starter-lwrlf7yogq-du.a.run.app/?tab=stage1) | [en/01_stage1_asset_and_cq_en.md](./en/01_stage1_asset_and_cq_en.md) |
| **Stage 2** | [ko/02_stage2_wiki_and_semantic_graph_ko.md](./ko/02_stage2_wiki_and_semantic_graph_ko.md) | [stage2_wiki_and_semantic_graph_ko.ipynb](../notebooks/ko/stage2_wiki_and_semantic_graph_ko.ipynb) | [`Stage 2. Wiki & Semantic Graph`](https://agentic-ontology-starter-lwrlf7yogq-du.a.run.app/?tab=stage2) | [en/02_stage2_wiki_and_semantic_graph_en.md](./en/02_stage2_wiki_and_semantic_graph_en.md) |
| **Stage 3** | [ko/03_stage3_property_graph_ko.md](./ko/03_stage3_property_graph_ko.md) | [stage3_property_graph_bigquery_spanner_ko.ipynb](../notebooks/ko/stage3_property_graph_bigquery_spanner_ko.ipynb) | [`Stage 3. Property Graph`](https://agentic-ontology-starter-lwrlf7yogq-du.a.run.app/?tab=stage3) | [en/03_stage3_property_graph_en.md](./en/03_stage3_property_graph_en.md) |
| **Stage 4** | [ko/04_stage4_agent_and_mcp_ko.md](./ko/04_stage4_agent_and_mcp_ko.md) | [stage4_agent_and_mcp_execution_ko.ipynb](../notebooks/ko/stage4_agent_and_mcp_execution_ko.ipynb) | [`Stage 4. Agent & MCP`](https://agentic-ontology-starter-lwrlf7yogq-du.a.run.app/?tab=stage4) | [en/04_stage4_agent_and_mcp_en.md](./en/04_stage4_agent_and_mcp_en.md) |
| **Stage 5** | [ko/05_stage5_lineage_and_eval_ko.md](./ko/05_stage5_lineage_and_eval_ko.md) | [stage5_lineage_and_evaluation_ko.ipynb](../notebooks/ko/stage5_lineage_and_evaluation_ko.ipynb) | [`Stage 5. Lineage & Eval`](https://agentic-ontology-starter-lwrlf7yogq-du.a.run.app/?tab=stage5) | [en/05_stage5_lineage_and_eval_en.md](./en/05_stage5_lineage_and_eval_en.md) |

### 2.2 🇺🇸 English Methodology Guides (`methodology/en/`)

| Stage | English Methodology Guide (`methodology/en/`) | Paired English Notebook (`notebooks/en/`) | Studio Tab | Korean Counterpart (`methodology/ko/`) |
| :---: | :--- | :--- | :--- | :--- |
| **Master** | [en/METHODOLOGY_EN.md](./en/METHODOLOGY_EN.md) | [stage0_overview_walkthrough_en.ipynb](../notebooks/en/stage0_overview_walkthrough_en.ipynb) | [`0. Overview`](https://agentic-ontology-starter-lwrlf7yogq-du.a.run.app/?tab=overview) | [ko/METHODOLOGY_KO.md](./ko/METHODOLOGY_KO.md) |
| **Stage 1** | [en/01_stage1_asset_and_cq_en.md](./en/01_stage1_asset_and_cq_en.md) | [stage1_asset_and_cq_en.ipynb](../notebooks/en/stage1_asset_and_cq_en.ipynb) | [`Stage 1. Asset`](https://agentic-ontology-starter-lwrlf7yogq-du.a.run.app/?tab=stage1) | [ko/01_stage1_asset_and_cq_ko.md](./ko/01_stage1_asset_and_cq_ko.md) |
| **Stage 2** | [en/02_stage2_wiki_and_semantic_graph_en.md](./en/02_stage2_wiki_and_semantic_graph_en.md) | [stage2_wiki_and_semantic_graph_en.ipynb](../notebooks/en/stage2_wiki_and_semantic_graph_en.ipynb) | [`Stage 2. Wiki & Semantic Graph`](https://agentic-ontology-starter-lwrlf7yogq-du.a.run.app/?tab=stage2) | [ko/02_stage2_wiki_and_semantic_graph_ko.md](./ko/02_stage2_wiki_and_semantic_graph_ko.md) |
| **Stage 3** | [en/03_stage3_property_graph_en.md](./en/03_stage3_property_graph_en.md) | [stage3_property_graph_bigquery_spanner_en.ipynb](../notebooks/en/stage3_property_graph_bigquery_spanner_en.ipynb) | [`Stage 3. Property Graph`](https://agentic-ontology-starter-lwrlf7yogq-du.a.run.app/?tab=stage3) | [ko/03_stage3_property_graph_ko.md](./ko/03_stage3_property_graph_ko.md) |
| **Stage 4** | [en/04_stage4_agent_and_mcp_en.md](./en/04_stage4_agent_and_mcp_en.md) | [stage4_agent_and_mcp_execution_en.ipynb](../notebooks/en/stage4_agent_and_mcp_execution_en.ipynb) | [`Stage 4. Agent & MCP`](https://agentic-ontology-starter-lwrlf7yogq-du.a.run.app/?tab=stage4) | [ko/04_stage4_agent_and_mcp_ko.md](./ko/04_stage4_agent_and_mcp_ko.md) |
| **Stage 5** | [en/05_stage5_lineage_and_eval_en.md](./en/05_stage5_lineage_and_eval_en.md) | [stage5_lineage_and_evaluation_en.ipynb](../notebooks/en/stage5_lineage_and_evaluation_en.ipynb) | [`Stage 5. Lineage & Eval`](https://agentic-ontology-starter-lwrlf7yogq-du.a.run.app/?tab=stage5) | [ko/05_stage5_lineage_and_eval_ko.md](./ko/05_stage5_lineage_and_eval_ko.md) |
