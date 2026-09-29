# Agentic Ontology Starter — 마스터 제품·아키텍처 헌장 (`01_prod.md`)

- **역할 및 위상**: 이 저장소(`agentic-ontology-starter`)는 특정 고객사의 프로덕션 비즈니스·데이터를 담고 있지 않은 **교육용 · 테스트용 · 신규 프로젝트 부트스트랩용 심플 레퍼런스 레포지토리**입니다. 반입될 외부 고객 비즈니스와 데이터 형태(문서만 있는 경우, 일부 테이블만 있는 경우, 전혀 다른 산업군 스키마가 들어오는 경우 등)가 완전히 예측 불가능한 상황에서도 유연하게 적응하도록 설계되었으며, 사람(FDE·엔지니어)과 AI 코딩 에이전트(Jetski / Antigravity / Cursor / Claude Code)가 공통으로 준수해야 하는 최상위 기준 문서입니다.
- **핵심 원칙**: 이 저장소는 백지상태에서 코드를 새로 짜는 보일러플레이트가 아니라, **동작이 검증된 5-Stage 온톨로지 파이프라인·8종 MCP·2-Pass/Lite 에이전트·6-Tab 라이트 스튜디오 골격을 그대로 유지한 채, 예측 불가능한 외부 고객 문서·데이터를 `projects/<id>/` 단위로 격리 인입하고 트랙(`auto`/`lite`/`standard`/`full`)과 모듈 오버라이드(`*_module`)로 유연하게 부트스트랩**하는 레퍼런스 엔진입니다.
- **관련 문서**:
  - 비영리 듀얼 라이선스: [`LICENSE`](LICENSE)
  - 상황별 프로토타이핑 레시피: [`PROTOTYPING_PLAYBOOK.md`](PROTOTYPING_PLAYBOOK.md)
  - AI 에이전트 부트스트랩 지침: [`GEMINI.md`](GEMINI.md) · [`CLAUDE.md`](CLAUDE.md) · [`AGENTS.md`](AGENTS.md) · [`.cursorrules`](.cursorrules)
  - 웹 UI 디자인 시스템 표준: [`DESIGN.md`](DESIGN.md)
  - 5-Stage 방법론 상세: [`methodology/ko/METHODOLOGY_KO.md`](methodology/ko/METHODOLOGY_KO.md) · [`methodology/en/METHODOLOGY_EN.md`](methodology/en/METHODOLOGY_EN.md)
  - 8단계 실습 노트북 허브: [`notebooks/README.md`](notebooks/README.md)

---

## 1. 아키텍처 불변 계약 (AI 에이전트가 임의로 변경하면 안 되는 6대 원칙)

다른 프로젝트로 이 스타터팩을 가져가서 프로토타이핑할 때, AI 코딩 에이전트는 아래 **6대 아키텍처 골격**을 임의로 삭제하거나 다른 프레임워크로 재작성해서는 안 됩니다.

| 번호 | 불변 아키텍처 요소 | 기준 명세 및 파일 위치 | 금지 행위 (Anti-Patterns) |
| :---: | :--- | :--- | :--- |
| **1** | **5-Stage × 8단계 엔지니어링 흐름 & 6-Tab 스튜디오** | `0. Overview` · `Stage 1. Asset` · `Stage 2. Wiki & Semantic Graph` · `Stage 3. Property Graph` · `Stage 4. Agent & MCP` · `Stage 5. Lineage & Eval` (`src/web/studio_server.py`) | 탭 구조를 임의로 쪼개거나 별도 React/Streamlit 서버·다중 포트를 새로 띄우는 행위 금지 |
| **2** | **입력 자산 기반 트랙 자동 결정 (`project.json` `track: "auto"`)** | `tables`가 비어 있으면 `lite`(`Stage 1→2→4→5(citation)`, 물리 그래프 생략), 고객 CSV가 등록되어 있으면 `standard`/`full`(`Stage 1→2→3→4→5`)로 자동 분기하고 사유를 `input_manifest.json`에 기록 | 고객 테이블이 없는데 샘플/가짜 CSV를 합성해 넣거나 코드에 특정 트랙 분기를 하드코딩하는 행위 금지 |
| **3** | **코드 기반 원문 추출(Gate 0) + 3-Layer 위키 이중 근거 구조** | 고객 원본 문서(`customer_doc/`)는 `pipeline/extract_docs.py`로 원문 변환 후 Gate 0(글자 보존율·12자 조각 일치율 `>= 95%`) 통과 시에만 `tb_doc_chunks`(출처 5컬럼 + SHA-256 해시)에 적재하고, `pipeline/extract_wiki.py`가 청크 인용 검증(`<=300`자) 기반으로 `entities.md`(Node)·`concepts.md`(Edge) 추출 | LLM으로 원본 문서를 요약·개작해 `01_guides/`에 넣거나, `DOC_CHUNK` 주석을 수동 삽입하거나, 원문에 없는 엔티티를 환각 생성하는 행위 금지 |
| **4** | **Stage MCP 5종 + Runtime MCP 3종 (총 8종 표면) 및 모듈 오버라이드** | Stage 1~5 검증용 MCP 5종 고정 유지 + 도메인 런타임 도구 3종(`src/agent/mcp_server.py`). 스키마가 다른 커스텀 도메인은 `project.json`의 `*_module` 오버라이드로 분리 주입 | 공용 서버/파이프라인 코드에 프로젝트별 `if` 분기를 난립시키거나 에이전트 내부에 SQL을 인라인 하드코딩하는 행위 금지 |
| **5** | **2-Pass MCP 추론(`full`) & 1-Pass 청크 인용 추론(`lite`)** | `full` 트랙은 2-Pass(`GROUNDED` / `MATCH_NOT_FOUND` / `INSUFFICIENT_PARAMETERS`), `lite` 트랙은 `execute_lite_doc_cycle`(`300,000`자 청크 컨텍스트 + `[DOC_CHUNK_XXX]` 인용 검증: `GROUNDED` / `NO_CITATION` / `INVALID_CITATION` / `CONTEXT_LIMIT`, `src/agent/reasoning_engine.py`) | 카탈로그·문서에 없는 상품/수치를 임의 추측해 답하거나 출처 청크 인용 없이 답변을 생성하는 행위 금지 |
| **6** | **3등급 데이터 출처(`provenance`) 구분 및 디자인 표준 준수** | 모든 행·청크에 `CUSTOMER_PROVIDED` / `EXTRACTED` / `SYNTHETIC_DEMO` 출처 기록, `pipeline/validator.py` 실측 리포트(`input_manifest_sha256` 포함) 생성, `DESIGN.md` 라이트 테마 준수 | 샘플 SQLite/인메모리 Mock DB로 실제 BigQuery를 위장하거나, 실행하지 않은 평가 점수를 수기로 작성하는 행위 금지 |

---

## 2. 예측 불가능한 외부 고객 입력 시나리오별 프로토타이핑 진입점 (`PROTOTYPING_PLAYBOOK.md` 요약)

신규 고객·데이터 영역을 부트스트랩할 때는 루트 샘플을 덮어쓰지 않고 `python3 new_project.py <id> --name "<이름>"`으로 `projects/<id>/`를 생성한 뒤, 반입된 고객 자산 형태에 따라 아래 시나리오로 대응합니다. 상세 가이드와 복사 가능한 프롬프트는 [`PROTOTYPING_PLAYBOOK.md`](PROTOTYPING_PLAYBOOK.md)를 참조하십시오.

| 상황 (Scenario) | 고객 투입 자산 및 목표 | 트랙 (`project.json` `track`) | 파이프라인 동작 및 수정 지점 |
| :--- | :--- | :---: | :--- |
| **Scenario A (`lite`)**<br>비정형 규정·약관·매뉴얼 문서만 있는 경우 | 고객 정형 테이블 없이 PDF/DOCX/MD 원본 문서만으로 원문 청크 + 위키(Entity/Concept) + `[DOC_CHUNK_XXX]` 인용 Q&A 및 Citation CQ 평가 구축 | **`lite`** (`"track": "auto"`, `"tables": {}`) | ① `customer_doc/*` 원본 배치 → `extract_docs.py` (Gate 0 `>=95%`)<br>② `extract_wiki.py` (`entities.md`, `concepts.md` 인용 검증 생성)<br>③ Stage 3 물리 그래프 생략 → Stage 4 `execute_lite_doc_cycle`<br>④ `04_cq/golden_competency_questions.json` (`"evidence_type": "citation"`) |
| **Scenario A2 (그래프 요청 시 중단)**<br>문서만 있는데 그래프·SQL 평가를 요청한 경우 | 고객 테이블이 없는데 Stage 3 Property Graph나 SQL 평가를 강제 요청(`track: "full"` 또는 `--stage 3`)한 경우 | **즉시 중단 및 선택지 안내** | 가짜 CSV를 합성하지 않고 즉시 멈춘 뒤 사용자에게 확인:<br>(a) 고객 정형 CSV(`03_tables/`) 추가 제공 요청<br>(b) `track: "lite"`(문서 전용 트랙)로 전환<br>(c) 데모 목적 합성 데이터 명시 승인(`synthetic.allowed: true`, `SYNTHETIC_DEMO`) |
| **Scenario B (표준 / 부분 테이블)**<br>정형 DW 테이블 + 비정형 정책 문서를 결합하는 경우 | 마스터/트랜잭션 CSV(전체 또는 일부)와 정책 문서를 결합해 ISO GQL 다중 홉 그래프 추론 + 2-Pass 에이전트 구축 | **`standard`** (`"track": "auto"`, `"graph_engine": "bigquery"`) | 고객이 실제로 제공한 테이블만 `project.json` `tables`에 등록·적재(`CUSTOMER_PROVIDED`)하고, 미제공 테이블은 빈 상태(0행)로 유지(샘플 데이터 혼합 금지) |
| **Scenario C (커스텀 도메인 스키마 / Spanner)**<br>통신 외 타 산업군 커스텀 테이블 또는 Spanner DDL 확장 | 샘플 6종 CSV와 전혀 다른 도메인 스키마(제조·금융·유통·의료 등)를 연결하거나 `create_spanner_graph.sql` 이중 DDL 산출 | **`standard`** + `*_module` 오버라이드 | 공용 코드를 수정하지 않고 프로젝트 폴더 내 모듈을 `project.json`의 `"ingest_module"`, `"graph_module"`, `"mcp_module"`, `"engine_module"`로 지정 + `projects/<id>/config/lineage_spec.json` 작성 |
| **Scenario D (`full`)**<br>감사 추적 리니지 & 50회 경계값 배포 게이트 완결 | 4계층 데이터 리니지 DAG + Golden CQ(`sql`/`citation`) + 경계값 10건×5회(50회) 벤치마크 통과 후 Cloud Run 배포 | **`full`** (`Stage 1 → 2 → 3 → 4 → 5`) | Scenario B/C 전체 + `04_cq/golden_competency_questions.json` & `boundary_cases.json` + `pipeline/validator.py` 실측(`input_manifest_sha256` 기록) + `terraform/terraform.tfvars` |

### 2.1 최신 문서 변환 · 위키 추출 · CQ 검증 핵심 산출물 예시

1. **원문 변환 (`pipeline/extract_docs.py` → `01_guides/*.md`) 및 Gate 0 (`data/output/gate0_report.json`)**:
   - 모든 변환 마크다운 상단에 `<!-- provenance: source_file=customer_doc/... sha256=... extracted_at=... -->` 및 페이지 경계 `<!-- page: N -->` 기록.
   - `gate0_report.json`에서 문서별 `char_retention_ratio >= 0.95`, `empty_pages: []`, `placeholder_detected: false` 통과 필수.
2. **문서 청크 (`data/output/doc_chunks.jsonl`) 5대 출처 컬럼**:
   - `origin_type`(`EXTRACTED` / `CUSTOMER_PROVIDED`), `source_doc`, `source_sha256`, `extract_method`, `source_locator`(`page=1#article=18`) 및 `content_sha256`(`anchor_<12hex>`).
3. **문서 기반 위키 추출 (`pipeline/extract_wiki.py` → `03_wiki/entities.md`, `concepts.md`, `data/output/wiki_extraction.json`)**:
   - `entities.md`는 핵심 비즈니스 엔티티(Node 후보), `concepts.md`는 엔티티 간 사전/사후 조건·제약 관계(`-[PRECONDITION|POSTCONDITION|CONSTRAINT]->`, Edge 후보)로 구조화하며, 각 항목의 `quote`(`<=300`자)가 실제 청크 원문에 존재하는지 대조해 불일치 항목은 자동 폐기(`entities_dropped_unverified_quote`, `concepts_dropped_unverified_quote` 기록).
4. **Golden CQ (`04_cq/golden_competency_questions.json`) 및 평가 리포트 (`data/output/cq_benchmark_report.json`)**:
   - `evidence_type: "sql"`(`verification_sql` + `expected_math` + `grounded_chunk`)과 `evidence_type: "citation"`(`expected_keywords` + `grounded_chunk`)을 구분 채점하며, 리포트에 `run_id`, `input_manifest_sha256`, `evidence_provenance`, `synthetic_basis`, `unconfirmed_cq_count`를 기록.

---

## 3. 런타임 기준값 및 환경 변수

새로운 GCP 프로젝트에 배포할 때는 코드 내부의 상수를 직접 수정하지 말고 환경 변수 또는 `terraform/terraform.tfvars`를 통해 주입합니다.

| 항목 | 환경 변수명 | 기본값 (데모 기준) | 코드 참조 위치 |
| :--- | :--- | :--- | :--- |
| GCP 프로젝트 ID | `GCP_PROJECT_ID` | `seanjung-poc` | `src/gcp_client.py`, `Dockerfile` |
| GCP 리전 | `GCP_LOCATION` | `asia-northeast3` | `src/gcp_client.py`, `Dockerfile` |
| BigQuery 데이터셋 | `BQ_DATASET_ID` | `starter_ontology_dw` | `src/gcp_client.py`, `pipeline/*.py` |
| Property Graph 명칭 | *(코드/설정 상수)* | `STARTER_ONTOLOGY_GRAPH` | `config/starter_config.json`, `pipeline/graph_builder.py` |
| GCS 위키 버킷 | `GCS_BUCKET_NAME` | `seanjung-poc-starter-ontology` | `src/gcp_client.py`, `pipeline/ingest.py` |
| Vertex AI 서빙 모델 | `VERTEX_GEMINI_MODEL` | `gemini-3.8-flash` | `src/gcp_client.py`, `src/agent/reasoning_engine.py` |
| 웹 스튜디오 포트 | `PORT` | `8080` | `src/web/studio_server.py`, `Dockerfile` |

---

## 4. 표준 디렉터리 및 문서 지도

| 경로 | 역할 | 프로토타이핑 시 수정 여부 |
| :--- | :--- | :---: |
| [`01_prod.md`](01_prod.md) | 마스터 제품·아키텍처 헌장 (현재 문서) | 도메인 요약만 갱신 |
| [`PROTOTYPING_PLAYBOOK.md`](PROTOTYPING_PLAYBOOK.md) | 시나리오별 빠른 프로토타이핑 가이드 & 프롬프트 레시피 | 참조용 (수정 불필요) |
| [`GEMINI.md`](GEMINI.md) / [`CLAUDE.md`](CLAUDE.md) / [`AGENTS.md`](AGENTS.md) / [`.cursorrules`](.cursorrules) | Jetski·Antigravity·Cursor·Claude Code용 에이전트 부트스트랩 규칙 | 참조용 (수정 불필요) |
| [`DESIGN.md`](DESIGN.md) | Apple/Google Enterprise 라이트 테마 디자인 토큰 및 UI 규칙 | 참조용 (수정 불필요) |
| [`config/project.json`](config/project.json) · [`projects/_template/`](projects/_template/README.md) | 기본 샘플 프로젝트 메타 · 고객/데이터 영역별 프로젝트 템플릿 (`new_project.py`로 생성) | 새 고객은 `projects/<id>/project.json`에서 수정 |
| [`config/starter_config.json`](config/starter_config.json) | 3-Track 활성 단계, 그래프 엔진, MCP 도구 목록 정의 | 기본 유지 (`project.json` 우선) |
| [`config/portal_profile.json`](config/portal_profile.json) | 스튜디오 헤더 타이틀, 도메인 배지, Stage별 설명, 샘플 질의 정의 | `projects/<id>/config/portal_profile.json` 수정 |
| [`config/lineage_spec.json`](config/lineage_spec.json) | Stage 5 리니지 DAG 스펙 (카테고리·노드·엣지, `bq_table` 실측 행 수) | `projects/<id>/config/lineage_spec.json` 수정 |
| [`data/input/`](data/input/) | `01_guides/`(원문 변환본), `03_tables/`(CSV), `04_cq/`(CQ·경계값), `05_glossary/`(용어사전) | `projects/<id>/customer_doc/` 및 `data/input/`에 배치 |
| [`industry_cases/`](industry_cases/README.md) | 제조·금융·리테일·통신 4대 산업군 8종 비식별 참조 스키마·규칙 템플릿 | 스키마·규칙 설계 참조용 |
| [`pipeline/extract_docs.py`](pipeline/extract_docs.py) | `customer_doc/` 원본(PDF/DOCX/MD/TXT) 원문 변환, 반복 머리글 제거, 조문/문단 청킹 및 Gate 0(`gate0_report.json`) 검증 | 코어 유지 |
| [`pipeline/extract_wiki.py`](pipeline/extract_wiki.py) | 문서 청크 기반 `entities.md`(Node)·`concepts.md`(Edge) 추출 및 원문 인용(`<=300`자) 검증(`wiki_extraction.json`) | 코어 유지 |
| [`pipeline/ingest.py`](pipeline/ingest.py) | 마크다운 청킹, 3-Layer 위키 생성, BigQuery 테이블·엣지 적재 (`ingest_module` 오버라이드 지원) | 커스텀 스키마 시 프로젝트 모듈로 오버라이드 |
| [`pipeline/graph_builder.py`](pipeline/graph_builder.py) | BigQuery `CREATE OR REPLACE PROPERTY GRAPH` 및 Spanner DDL 생성·실행 (`graph_module` 오버라이드 지원) | 커스텀 스키마 시 프로젝트 모듈로 오버라이드 |
| [`src/agent/mcp_server.py`](src/agent/mcp_server.py) | Stage MCP 5종 + 도메인 Runtime MCP 3종 (`mcp_module` 오버라이드 지원) | 커스텀 스키마 시 프로젝트 모듈로 오버라이드 |
| [`src/agent/reasoning_engine.py`](src/agent/reasoning_engine.py) | 2-Pass MCP 에이전트(`full`) 및 1-Pass 문서 청크 인용 에이전트(`lite` `execute_lite_doc_cycle`) | 커스텀 스키마 시 `engine_module` 오버라이드 |
| [`pipeline/validator.py`](pipeline/validator.py) | Golden CQ(`sql`/`citation` 분기) 및 경계값 10건×5회 라이브 벤치마크 (`input_manifest_sha256` 기록) | 코어 유지 (`validator_module` 오버라이드 지원) |
| [`src/project_context.py`](src/project_context.py) · [`src/lineage/lineage_engine.py`](src/lineage/lineage_engine.py) | 프로젝트 해석·프로젝트별 엔진 캐시 · 리니지 DAG 엔진 | 코어 유지 |
| [`src/web/studio_server.py`](src/web/studio_server.py) | 6-Tab 통합 웹 스튜디오 서버 (`config/portal_profile.json` 기반 렌더링) | 코어 레이아웃 유지 |
| [`notebooks/ko/`](notebooks/ko/) · [`notebooks/en/`](notebooks/en/) | Stage 0~5 국문(6종) · 영문(6종) 실행형 노트북 및 `nb_helpers.py` | 필요 시 쿼리만 갱신 |
| [`terraform/`](terraform/) | BigQuery, GCS, IAM, Cloud Run 선언적 IaC | `terraform.tfvars`만 수정 |

---

## License

This starter pack is licensed under a non-commercial dual license:
- **Methodology, Documentation & Notebooks**: [Creative Commons CC BY-NC-ND 4.0](https://creativecommons.org/licenses/by-nc-nd/4.0/)
- **Source Code & Pipelines**: [PolyForm Noncommercial License 1.0.0](https://polyformproject.org/licenses/noncommercial/1.0.0/)

See [`LICENSE`](LICENSE) for complete terms. For commercial licensing, contact `seanjung@google.com`.
