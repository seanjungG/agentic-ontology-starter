# Stage 2. OKF Wiki·시맨틱 모델링

> 스튜디오 [`Stage 2. Wiki & Semantic Graph`](https://agentic-ontology-starter-924723860007.asia-northeast3.run.app/?tab=stage2) · MCP `mcp_stage2_wiki_and_semantic` · 노트북 [stage2_wiki_and_semantic_graph_ko.ipynb](../../notebooks/ko/stage2_wiki_and_semantic_graph_ko.ipynb) · [English](../en/02_stage2_wiki_and_semantic_graph_en.md) · [전체 방법론](./METHODOLOGY_KO.md)

## 목적

비정형 가이드를 근거 단위(청크)로 나누고, 본문이 바뀌지 않는 한 같은 값이 나오는 앵커를 붙인다.
문서의 규칙을 테이블 행으로 정리하고 정형 데이터(요금제)와 연결한다. 에이전트 답변이 어느 문단을 근거로 했는지 추적하기 위한 단계다.

## 입력

| 경로 | 내용 |
| :--- | :--- |
| `data/input/01_guides/*.md` | 가이드 2개, 청크 5개 |
| `data/input/03_tables/domain_rules.csv` | 규칙 4개 (`RULE_SUBSIDY_CAP`, `RULE_SIX_PLAN_180D`, `RULE_WELFARE_EXEMPT`, `RULE_TCO_24M`). `source_chunk_id`로 근거 청크를 가리킨다 |
| `data/input/03_tables/rule_plan_edges.csv` | 규칙→요금제 연결 12개. 한글 관계명(`relation_label_ko`)과 `source_chunk_id` 포함 |
| 마스터 CSV 4개 (Stage 1) | Wiki L2(엔티티)의 원천 |

## 이 Stage의 MCP: `mcp_stage2_wiki_and_semantic`

| Step | 실제 수행 (`src/agent/mcp_server.py`) |
| :--- | :--- |
| `compile_3layer_wiki` | GCS 버킷 객체 목록만 조회한다 → `gcs_objects`. Wiki 생성은 `run_ingest()`가 한다 |
| `extract_hash_anchors` | `tb_doc_chunks`의 앵커(`content_sha256`)를 조회한다. 앵커 생성은 `run_ingest()`가 한다 |
| `bind_semantic_bridges` | `tb_doc_chunks`와 `tb_domain_rules`를 `source_chunk_id`로 조인한다 → `anchored_chunks` |

`steps` 인자는 결과의 `executed_steps`에 기록된다. 현재 핸들러는 선택한 Step과 관계없이 조인 쿼리와 GCS 목록 조회를 모두 실행한다.

## 절차 (`pipeline/ingest.py`의 `run_ingest()`)

1. **청크 분할**: 가이드를 `DOC_CHUNK_*` 주석 단위로 나누고, 본문 SHA-256의 앞 12자리로 앵커(`anchor_` + 12자리)를 만든다 → `data/output/doc_chunks.jsonl`. 본문이 바뀌면 앵커도 바뀐다.
2. **온톨로지 파일**: 도메인 노드 1개와 청크 노드를 JSON-LD로 쓴다 → `data/output/ontology.jsonld`.
3. **3-Layer Wiki**: 같은 청크와 CSV 행에서 Markdown 4개를 만든다 → `data/llm_wiki/`.

   | 파일 | Layer | 원천 |
   | :--- | :--- | :--- |
   | `summary.md` | L1 요약 | 청크 수, 가이드 수, 테이블 수 |
   | `entities.md` | L2 엔티티 | 마스터 CSV 4개 |
   | `concepts.md` | L3 관계 | `pipeline/ingest.py`에 정의된 관계 4종 (`USES_DEVICE`, `SUBSCRIBES_PLAN`, `HAS_SUBSIDY_POLICY`, `APPLIES_TO_PLAN`) |
   | `rules.md` | L3 규칙 | `domain_rules.csv` |

4. **적재·업로드**: 청크는 `tb_doc_chunks`, 규칙은 `tb_domain_rules`, 규칙→요금제 연결은 `edge_rule_applies_to_plan`에 적재한다. 가이드 원문(`raw/`), 청크(`parsed/`), Wiki와 JSON-LD(`ontology/`)는 GCS에 올린다. 결과는 `data/llm_wiki/gcs_prototype_manifest.json`에 남는다.
5. **시맨틱 그래프**: 스튜디오 그래프는 `data/output/graph_topology.json`의 `vis_semantic_graph`(노드 11, 엣지 13)를 그린다. 이 파일은 Stage 3의 `build_graph()`가 쓰며, 노드와 라벨은 `pipeline/graph_builder.py`에 정의되어 있다. 원칙은 엔티티 = 노드, 관계(개념) = 엣지다.

## 산출물

| ID | 산출물 | 스타터에서 |
| :--- | :--- | :--- |
| `D2.1` | OKF v0.2 도메인 온톨로지 명세서 | `data/output/ontology.jsonld` (도메인 노드 + 청크 노드) |
| `D2.2` | Karpathy 3-Layer LLM-Wiki 디렉토리 | `data/llm_wiki/summary.md`, `entities.md`, `concepts.md`, `rules.md` |
| `D2.3` | GCS 온톨로지 프로토타입 레지스트리 | `data/llm_wiki/gcs_prototype_manifest.json`, GCS `raw/` · `parsed/` · `ontology/` |
| `D2.4` | 비정형 텍스트 청크 및 해시 앵커 매니페스트 | `data/output/doc_chunks.jsonl`, BigQuery `tb_doc_chunks` |
| `D2.5` | 결정론적 비즈니스 규칙 레지스트리 | `domain_rules.csv` → BigQuery `tb_domain_rules` |
| `D2.6` | 시맨틱 브릿지 매핑 매트릭스 | `rule_plan_edges.csv` → BigQuery `edge_rule_applies_to_plan` |

## 게이트 (Gate 2)

- [ ] 모든 청크에 앵커가 있고 서로 겹치지 않는다.
- [ ] `tb_domain_rules.source_chunk_id`가 모두 `tb_doc_chunks`에 있다. Stage 2 MCP 결과 `anchored_chunks`에서 규칙이 붙은 청크를 확인한다.
- [ ] manifest의 `status`가 `LIVE_GCP_SYNCED`이고 `validation.bigquery_tables_loaded`가 10이다.
- [ ] Lite 트랙은 이 게이트를 통과하면 Stage 4로 넘어간다.

## 스튜디오에서 보기

[Stage 2. Wiki & Semantic Graph 탭 열기](https://agentic-ontology-starter-924723860007.asia-northeast3.run.app/?tab=stage2)

- 왼쪽: Wiki 뷰어 (`L1 Summary`, `L2 Entities`, `L3 Concepts`, `L3 Rules`, `Chunks`).
- 오른쪽: 시맨틱 그래프. 노드를 누르면 연결 관계와 근거 청크 설명이 나온다.
- `▶ Stage 2 MCP 실행` 버튼 (오른쪽 위): 위 MCP를 실행한다.

## 노트북

[stage2_wiki_and_semantic_graph_ko.ipynb](../../notebooks/ko/stage2_wiki_and_semantic_graph_ko.ipynb)

## 내 데이터에 적용하기

1. **청크 경계**: 가이드에 `<!-- DOC_CHUNK_NNN: 제목 -->` 주석을 넣어 근거 단위를 직접 정한다. 규칙과 CQ가 청크 ID를 참조하므로 문서를 고쳐도 ID는 유지한다.
2. **규칙**: `domain_rules.csv`에 규칙을 쓰고 `source_chunk_id`에 근거 청크 ID를 적는다. 규칙 ID 4개는 `src/agent/mcp_server.py`의 SQL이 이름으로 참조하므로, ID를 바꾸면 그 SQL도 고친다.
3. **규칙-테이블 연결**: `rule_plan_edges.csv`에 규칙이 적용되는 `plan_id`를 연결한다.
4. **그래프 뷰**: 시맨틱 그래프의 노드·라벨을 바꾸려면 `pipeline/graph_builder.py`의 `vis_semantic_graph`를 고친다. Wiki의 관계 설명은 `pipeline/ingest.py`의 `concepts.md` 부분에 있다.
