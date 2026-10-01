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

### lite 트랙 및 외부 문서 유입 시: 문서 기반 위키 추출 (고객 테이블이 없는 프로젝트)

1. **결정론적 청크 분할 (`pipeline/ingest.py`)**: `extract_docs.py`가 만든 원문 `01_guides/*.md`를 조문(`제N조(`) 또는 제목·문단 단위(상한 1,500자)로 나눈다. 청크마다 출처 5컬럼(`source_doc`, `source_sha256`, `page_from`, `page_to`, `article_no`)을 기록하고 `trust_tier`는 `EXTRACTED`다.
2. **인용 검증 기반 위키 추출 (`pipeline/extract_wiki.py`)**: 청크에서 주요 업무 단위를 `Entity`(Node)로, 엔티티 사이의 사전조건·사후조건·제약조건을 `Concept`(`-[PRECONDITION|POSTCONDITION|CONSTRAINT]->` Edge)로 추출한다.
3. **인용구 코드 대조**: 항목마다 `source_chunk_id`와 300자 이하 원문 인용구(`quote`)를 붙인다. 인용구가 실제 청크 원문에 없으면(공백 차이만 무시) 즉시 제외하고 제외 건수(`dropped_count`)를 `data/output/wiki_extraction.json`에 남긴다.
4. **결과**: `data/llm_wiki/entities.md`, `concepts.md`를 생성하고 GCS `ontology/`에 올린다. 정형 테이블이 없으므로 물리 그래프 적재(Stage 3)는 생략한다.

#### 실제 변환·추출 산출물 샘플 (`doc_chunks.jsonl`, `entities.md`, `concepts.md`)

`data/output/doc_chunks.jsonl` (출처 5컬럼 포함):
```json
{"chunk_id": "DOC_CHUNK_001", "doc_name": "01_service_terms.md", "section_title": "제1조(목적)", "chunk_text": "제1조(목적) 본 약관은 서비스 이용 조건 및 해지 시 반환금 산정 기준을 규정함을 목적으로 한다.", "trust_tier": "EXTRACTED", "source_doc": "customer_doc/01_service_terms.pdf", "source_sha256": "0004623c1b39ebfd821ef3db6ca1eb8c94fb596094997a5e8f8b2d5a42efac61", "page_from": 1, "page_to": 1, "article_no": "제1조"}
{"chunk_id": "DOC_CHUNK_002", "doc_name": "01_service_terms.md", "section_title": "제2조(의무 유지 기간)", "chunk_text": "제2조(의무 유지 기간) 할인 반환금 면제를 위한 최소 유지 기간은 개통일로부터 180일로 한다.", "trust_tier": "EXTRACTED", "source_doc": "customer_doc/01_service_terms.pdf", "source_sha256": "0004623c1b39ebfd821ef3db6ca1eb8c94fb596094997a5e8f8b2d5a42efac61", "page_from": 1, "page_to": 1, "article_no": "제2조"}
```

`data/llm_wiki/entities.md` (Node) 및 `concepts.md` (Edge):
```markdown
## E001: 서비스 이용 조건 및 반환금 기준
- **Node Type**: `Entity`
- **Source Chunk**: `DOC_CHUNK_001` (`customer_doc/01_service_terms.pdf`, p.1, 제1조)
- **Quote**: "제1조(목적) 본 약관은 서비스 이용 조건 및 해지 시 반환금 산정 기준을 규정함을 목적으로 한다."

## C001: 할인 반환금 면제 최소 유지 조건
- **Edge**: `E001 -[PRECONDITION]-> E002`
- **Condition Type**: `PRECONDITION`
- **Source Chunk**: `DOC_CHUNK_002` (`customer_doc/01_service_terms.pdf`, p.1, 제2조)
- **Quote**: "제2조(의무 유지 기간) 할인 반환금 면제를 위한 최소 유지 기간은 개통일로부터 180일로 한다."
```

## 권장 방법: 온톨로지 레이어 자기충족

온톨로지 폴더만으로 그래프 설계·적재와 질의응답이 가능하도록 엔티티·개념 문서를 쓴다.

| 항목 | 권장 방법 |
| :--- | :--- |
| 문서 내용 | 문서 1건 = 엔티티 또는 개념 1개. 요약 + 원문의 수치·조건·예외(원문 순서). 값마다 parsed 문단 앵커와 짧은 원문 인용을 붙인다 |
| 원문에 없는 값 | 쓰지 않는다. 정형 값은 테이블·컬럼 매핑만 적고 실제 값은 적재 데이터에서 읽는다 |
| frontmatter | 그래프 구조 블록(노드 라벨·속성·관계, 관계마다 앵커), 근거(앵커·인용·값), 추출 모델, 검토 상태 |
| 재추출 게이트 | 승격 전에 스크립트로 검사한다: 앵커가 parsed에 실재, 인용이 해당 앵커 원문의 부분 문자열, 모든 수치가 인용에 존재, parsed 수치 커버리지(예: 문서별 90% 이상). 통과한 항목만 기록한다 |
| `latest` 승격 | 게이트 통과 버전을 `latest`로 올리는 일은 별도 단계로 하고, 사람 검토 기록 여부(검토자 또는 "검토 기록 없음")를 함께 남긴다 |
| 검색 순서 | 온톨로지 문서를 먼저 검색하고, 근거가 없을 때만 parsed 청크를 본다. 답변에 근거 단계(ontology / parsed fallback)를 적는다 |
| 자산 레지스트리 | 고객이 제공한 입력 문서만 관리한다. 추출 중 자동 생성된 규칙·용어 항목은 레지스트리에 넣지 않고 온톨로지 레이어에서 본다 |

```yaml
---
type: Concept            # Entity | Concept
id: CON-001
title: 할인 반환금 면제 최소 유지 조건
source_doc: parsed/<doc>/parsed_document.md
graph:
  label: PolicyRule
  properties: {min_retention_days: "180"}   # 원문 값만
  relations:
    - {type: PRECONDITION, target: ENT-001, anchor: sec-02-p01}
evidence:
  - {anchor: sec-02-p01, quote: "<원문 그대로>", values: ["180"]}
dw_mapping:              # 값 없이 테이블·컬럼만
  - {table: <table>, column: <column>}
extracted_by: <실제 모델명>
review: {status: unverified, reviewer: null}
---
```

스타터의 현재 구현은 다음이 다르다.

- GCS `gs://seanjung-poc-starter-ontology/ontology/`에는 문서별 파일이 아니라 `entities.md`, `concepts.md`, `rules.md`, `summary.md`, `ontology.jsonld` 5개 파일이 올라간다.
- 앵커는 청크 본문의 SHA-256(청크 단위)이며 문단 앵커가 아니다. 표준 트랙 Wiki는 CSV 행과 청크에서 코드로 만든다.
- `extract_wiki.py`는 인용구가 청크 원문에 있는지만 검사한다. 수치 검사, 커버리지 검사, 별도 `latest` 승격 단계는 없다.
- 검색 fallback이 없다. `standard`/`full`은 규칙의 `source_chunk_id`로 청크를 조인하고, `lite`는 `tb_doc_chunks` 전체 행을 Gemini 컨텍스트에 넣는다(`src/agent/reasoning_engine.py` `_lite_cycle`).

## 산출물

| ID | 산출물 | 스타터에서 |
| :--- | :--- | :--- |
| `D2.1` | OKF v0.2 도메인 온톨로지 명세서 | `data/output/ontology.jsonld` (도메인 노드 + 청크 노드) |
| `D2.2` | Karpathy 3-Layer LLM-Wiki 디렉토리 | `data/llm_wiki/summary.md`, `entities.md`, `concepts.md`, `rules.md` (문서 전용 프로젝트는 `extract_wiki.py` 생성분 + `wiki_extraction.json`) |
| `D2.3` | GCS 온톨로지 프로토타입 레지스트리 | `data/llm_wiki/gcs_prototype_manifest.json`, GCS `raw/` · `parsed/` · `ontology/` |
| `D2.4` | 비정형 텍스트 청크 및 해시 앵커 매니페스트 | `data/output/doc_chunks.jsonl` (출처 5컬럼 포함), BigQuery `tb_doc_chunks` |
| `D2.5` | 결정론적 비즈니스 규칙 레지스트리 | `domain_rules.csv` → BigQuery `tb_domain_rules` (`standard`/`full` 트랙) |
| `D2.6` | 시맨틱 브릿지 매핑 매트릭스 | `rule_plan_edges.csv` → BigQuery `edge_rule_applies_to_plan` (`standard`/`full` 트랙) |

## 게이트 (Gate 2)

- [ ] 모든 청크에 앵커(`content_sha256`)와 출처 5컬럼(`source_doc`, `source_sha256`, `page_from`, `page_to`, `article_no`)이 있고 서로 겹치지 않는다.
- [ ] 문서 기반 위키(`extract_wiki.py`) 추출 항목의 모든 `quote`가 원문 청크에 실제 존재한다(불일치 항목은 자동 폐기됨).
- [ ] 정형 테이블이 있는 프로젝트는 `tb_domain_rules.source_chunk_id`가 모두 `tb_doc_chunks`에 있다.
- [ ] Lite 트랙은 이 게이트를 통과하면 Stage 3를 건너뛰고 Stage 4로 넘어간다.
- [ ] (권장, 스타터 미구현) 엔티티·개념 문서가 재추출 게이트(앵커·인용·수치·커버리지)를 통과한 뒤 `latest`로 승격되고, 사람 검토 기록 여부가 적혀 있다.

## 스튜디오에서 보기

[Stage 2. Wiki & Semantic Graph 탭 열기](https://agentic-ontology-starter-924723860007.asia-northeast3.run.app/?tab=stage2)

- 왼쪽: Wiki 뷰어 (`L1 Summary`, `L2 Entities`, `L3 Concepts`, `L3 Rules`, `Chunks`).
- 오른쪽: 시맨틱 그래프. 노드를 누르면 연결 관계와 근거 청크 설명이 나온다.
- `▶ Stage 2 MCP 실행` 버튼 (오른쪽 위): 위 MCP를 실행한다.

## 노트북

[stage2_wiki_and_semantic_graph_ko.ipynb](../../notebooks/ko/stage2_wiki_and_semantic_graph_ko.ipynb)

## 내 데이터에 적용하기

1. **청크 경계**: 고객 문서의 청크 경계는 코드가 정한다(`extract_docs.py` 변환본의 조문·제목·문단). `<!-- DOC_CHUNK_NNN: 제목 -->` 주석은 샘플 전용이며 고객 문서에 직접 넣지 않는다.
2. **문서 기반 위키 추출**: 정형 테이블 없이 문서만 있거나 신규 도메인 문서가 들어오면 `python3 pipeline/extract_wiki.py --project <id>`가 청크에서 `Entity`(Node)와 `Concept`(`PRECONDITION`/`POSTCONDITION`/`CONSTRAINT` Edge)을 인용구 검증과 함께 추출한다.
3. **규칙 및 테이블 연결 (정형 테이블 보유 시)**: `domain_rules.csv`에 원문 조항을 인용해 규칙을 쓰고 `source_chunk_id`에 근거 청크 ID를 적으며, `rule_plan_edges.csv`에 적용 대상을 연결한다.
4. **그래프 뷰**: 시맨틱 그래프의 노드·라벨을 바꾸려면 프로젝트 전용 `graph_module`(`project.json`) 또는 `pipeline/graph_builder.py`의 `vis_semantic_graph`를 고친다.
