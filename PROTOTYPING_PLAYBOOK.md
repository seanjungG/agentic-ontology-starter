# 상황별 빠른 프로토타이핑 플레이북 (`PROTOTYPING_PLAYBOOK.md`)

> **목적 및 위상**: 이 스타터팩(`agentic-ontology-starter`)은 특정 고객사 프로덕션 코드베이스가 아닌 **교육용 · 테스트용 · 신규 프로젝트 부트스트랩용 심플 레퍼런스 레포지토리**입니다. 고객 비즈니스와 데이터 형태(문서만 있는 경우, 일부 테이블만 있는 경우, 전혀 다른 산업군 스키마가 들어오는 경우 등)가 완전히 예측 불가능한 상황에서도, 코드를 처음부터 새로 짜지 않고 **`projects/<id>/` 격리 폴더와 시나리오별 교체(Swap)·모듈 오버라이드(`*_module`)만으로 30분~반나절 안에 동작하는 도메인 프로토타입(파이프라인 + BigQuery Graph + 8종 MCP + 6-Tab 스튜디오)을 완성**하기 위한 실전 가이드입니다.
> **AI 코딩 에이전트(Jetski / Antigravity / Cursor / Claude Code) 사용자**: 아래 시나리오 중 본인 상황에 맞는 **복사-붙여넣기 부트스트랩 프롬프트**를 에이전트에게 그대로 전달하십시오.

---

## 0. 고객·데이터 영역별 프로젝트로 시작하기 (기본 동작)

루트 샘플은 그대로 두고 `python3 new_project.py <id> --name "<이름>"`으로 `projects/<id>/`를 만든 뒤, 아래 교체를 그 폴더 안에서 진행합니다. 스튜디오 상단 `PROJECT` 선택기(`?project=<id>`)로 샘플과 전환하며 비교합니다.

| 교체·설정 대상 | 프로젝트에서 수정할 위치 |
| :--- | :--- |
| ① 트랙·엔진·테이블 목록 | `projects/<id>/project.json` (`track`: 기본 `"auto"`, `graph_engine`, `gcp`, `tables`, `synthetic.allowed`) |
| ② 고객 원본 문서 & 입력 자산 | `projects/<id>/customer_doc/*` (`extract_docs.py`가 `01_guides/*.md`로 원문 변환 후 Gate 0 `>=95%` 검증) · `data/input/03_tables/*` (고객 CSV만, `provenance` 필수) · `data/input/04_cq/*` (`sql` 또는 `citation`) |
| ③ 문서 기반 위키 / 인제스트·그래프 | `lite` 트랙은 `extract_wiki.py`가 `entities.md`(Node)·`concepts.md`(Edge) 자동 추출(`<=300`자 인용 검증). 커스텀 스키마는 복사본을 `projects/<id>/`에 두고 `project.json`의 `ingest_module` · `graph_module`로 지정 |
| ④ 에이전트 런타임 & 화면 프로필 | `lite` 트랙은 `_lite_cycle`(`[DOC_CHUNK_XXX]` 인용 강제) 자동 실행. 커스텀 스키마는 `mcp_module` · `engine_module` 지정 + `projects/<id>/config/portal_profile.json` 수정 |
| ⑤ Stage 5 리니지 & 평가 | `projects/<id>/config/lineage_spec.json` 작성 + `python3 pipeline/validator.py --project <id>` (`input_manifest_sha256` 기록) |

실행: `python3 run_pipeline.py --project <id>` (데이터셋·버킷은 Terraform으로 먼저 생성). 상세: [`projects/_template/README.md`](projects/_template/README.md)

---

## 1. 내 프로젝트는 어디에 해당하는가? (4대 프로토타이핑 시나리오 선택)

| 시나리오 | 어떤 상황인가? (보유 자산 & 목표) | 트랙 (`project.json` `track`, 기본 `auto`) | 실행 Stage | 수정할 파일 수 |
| :--- | :--- | :---: | :---: | :---: |
| **[Scenario A](#scenario-a-비정형-정책매뉴얼-문서만-있는-경우-track-1--lite)**<br>**문서 전용 퀵스타트** | 고객 테이블은 없고 **업무 매뉴얼·약관·SOP 원본 문서(PDF/DOCX/MD/TXT)**만으로 원문 청크 + 문서 기반 위키 + 청크 인용 에이전트 Q&A를 띄우고 싶다. | `lite` | `Stage 1 → 2 → 4` | **4개** |
| **Scenario A2**<br>**문서만 있는데 그래프·SQL 평가 요청** | 고객 테이블 없이 Property Graph나 SQL 평가를 요청받았다. 에이전트는 테이블을 만들지 않고 멈춰서 묻는다: (a) 고객에게 테이블 요청 (b) 문서 기반 물리 그래프(미구현, 별도 요청) (c) 합성 데모 데이터(승인 필요, `SYNTHETIC_DEMO`). | 멈춤 | - | - |
| **[Scenario B](#scenario-b-정형-dw-테이블--정책-문서를-결합하는-경우-track-2--standard-가장-많이-사용)**<br>**DW + 문서 하이브리드 그래프** *(기본 권장)* | **마스터/트랜잭션 CSV(또는 BigQuery 테이블)와 업무 정책 문서**가 모두 있어서, **BigQuery Property Graph(`ISO GQL`) 다중 홉 추론 + 2-Pass 에이전트**를 보여주고 싶다. | `standard`<br>(`bigquery`) | `Stage 1 → 2 → 3 → 4` | **5개** |
| **[Scenario C](#scenario-c-실시간-운영-인터락--spanner-graph-ddl이-필요한-경우-track-2--spanner)**<br>**저지연 운영 그래프 확장** | Scenario B와 같지만, 고객이 **이상거래 탐지(FDS)·설비 인터락 등 실시간 운영 DB(`Cloud Spanner Graph`) 적용 가능성**을 함께 확인하고 싶어 한다. | `standard`<br>(`bigquery` + Spanner DDL) | `Stage 1 → 2 → 3 → 4` | **5개** |
| **[Scenario D](#scenario-d-감사-추적-리니지--50회-경계값-릴리스-게이트까지-완결하는-경우-track-3--full)**<br>**엔터프라이즈 검증 & 배포 게이트** | 프로토타입을 넘어 **4계층 데이터 리니지(`문서 해시 → 규칙 → 원장 → CQ`)와 Golden CQ 5건 · 경계값 50회 벤치마크 통과 및 Cloud Run 배포**까지 한 번에 완결하고 싶다. | `full` | `Stage 1 → 2 → 3 → 4 → 5` | **6개** |

---

## 2. 왜 코드를 새로 짜지 않는가? — 5-File Swap 구조

이 스타터팩은 **코어 엔진(수정 불필요)**과 **도메인 데이터/규칙 슬롯(교체 대상 5개)**이 분리되어 있습니다.

```text
[절대 건드리지 않는 코어 엔진]
  ├── src/gcp_client.py             (BigQuery SQL/GQL 실행, GCS 업로드, Vertex AI Gemini 호출)
  ├── src/agent/reasoning_engine.py (2-Pass 추론 루프 및 GROUNDED / MATCH_NOT_FOUND / INSUFFICIENT_PARAMETERS 판정 프레임워크)
  ├── src/web/studio_server.py      (Apple/Google 라이트 테마 6-Tab 스튜디오 UI 레이아웃 및 렌더링 엔진)
  └── terraform/*.tf                (BigQuery, GCS, IAM, Cloud Run 선언적 인프라 코드)

[도메인 프로토타이핑 시 교체하는 5개 파일 (5-File Swap)]
  ① config/starter_config.json      → active_track ("lite" | "standard" | "full") 및 그래프 이름 지정
  ② data/input/*                    → 01_guides/*.md (extract_docs.py가 customer_doc/ 원본에서 생성), 03_tables/*.csv (고객이 준 테이블만), 04_cq/*.json (검증 질의)
  ③ pipeline/ingest.py              → DOMAIN_RULES (원문 조항 인용 + source_chunk_id) 및 compile_3layer_wiki() 도메인 요약
  ④ pipeline/graph_builder.py       → CREATE OR REPLACE PROPERTY GRAPH 의 VERTEX TABLES / EDGE TABLES 매핑
  ⑤ src/agent/mcp_server.py &       → Runtime MCP 3종의 SQL/GQL 쿼리 + config/portal_profile.json 의 화면 문구/샘플 질문
     config/portal_profile.json
```

> **산업군 레퍼런스**: [`industry_cases/README.md`](industry_cases/README.md)의 **4대 산업군 8종 비식별 템플릿**(제조 2종, 금융 2종, 리테일 2종, 통신 2종)은 노드·엣지 설계 구조 참고용입니다. CSV 데이터를 복사하면 행마다 `provenance=SYNTHETIC_DEMO` 표시와 사용자 승인(`synthetic.allowed: true`)이 필요하며, 고객 프로젝트에 샘플과 같은 파일이 있으면 적재가 실패합니다.

---

## 3. 시나리오별 실행 레시피 & Jetski / Cursor 부트스트랩 프롬프트

### Scenario A: 비정형 정책·매뉴얼 문서만 있는 경우 (`Track 1 · Lite`)

- **적합한 경우**: 인사/법무 규정, 금융 여신 심사 지침서, 설비 안전 매뉴얼 등 **고객 원본 문서는 있으나 고객 테이블이 없을 때**.
- **동작 방식**: `pipeline/extract_docs.py`가 `customer_doc/` 원본을 원문 그대로 `01_guides/*.md`로 변환하고, Gate 0(문서별 원문 비율 95% 이상 등)을 통과한 청크만 `tb_doc_chunks`에 적재합니다. `pipeline/extract_wiki.py`가 청크에서 entity(node)·concept(edge)를 인용과 함께 뽑아 위키를 만들고, 물리 Property Graph(`Stage 3`)는 건너뜁니다. 에이전트(`Stage 4`)는 청크 전체를 컨텍스트로 받아 청크 ID를 인용해 답하고, validator는 citation CQ로 채점합니다.

#### Step-by-Step 수정 포인트
1. `projects/<id>/project.json`: `track`은 `auto`(테이블이 없으면 `lite`), `tables`는 비워 둠.
2. `projects/<id>/customer_doc/`: 고객 원본 문서를 그대로 둠. `01_guides/`에 직접 쓴 파일을 넣지 않음.
3. `data/input/04_cq/`: 문서에 있는 내용으로만 CQ를 쓰고 `evidence_type: citation`, `expected_citation`(chunk_id, quote)을 붙임. 정답은 사람이 확정해 `answer_confirmed_by`에 기록.
4. `config/portal_profile.json`의 Stage 설명·샘플 질의를 갱신.

#### Jetski / Cursor 복사-붙여넣기 프롬프트 (Scenario A)
```text
@AGENTS.md @PROTOTYPING_PLAYBOOK.md 를 먼저 읽고 준수해줘.
고객 문서를 projects/<id>/customer_doc/에 넣었어. 고객 테이블은 없고 이 문서만으로 진행한다.
1. python3 pipeline/extract_docs.py --project <id> 로 원문을 그대로 변환하고, python3 run_pipeline.py --project <id> 의 Gate 0 결과(data/output/gate0_report.json의 문서별 원문 비율, 청크 수, 누락 쪽)를 먼저 보여줘. 요약하거나 다시 쓰지 마.
2. 트랙은 입력 기준(auto)으로 정하고 결정 이유를 보고해줘.
3. CQ는 문서에 있는 내용으로만 만들고, CQ마다 근거 청크와 원문 구절을 붙여줘. 문서에 없는 제품·고객·사례를 만들지 마.
4. 그래프나 SQL 평가에 테이블이 필요하면 만들지 말고 나에게 선택지를 물어봐.
5. 평가는 validator.py 실행 결과만 보고하고, 마지막에 데이터 출처 요약을 붙여줘.
```

---

### Scenario B: 정형 DW 테이블 + 정책 문서를 결합하는 경우 (`Track 2 · Standard`, 가장 많이 사용)

- **적합한 경우**: 상품/단말/설비/고객 계약 등 **정형 테이블(CSV 4~6개)과 비정형 정책 문서(MD 1~2개)를 하나의 BigQuery Property Graph로 연결**해 다중 홉 GQL 추론과 2-Pass 에이전트를 시연할 때.
- **동작 방식**:
  - 정형 CSV → BigQuery 마스터/트랜잭션 노드 테이블 적재
  - 비정형 MD → `tb_doc_chunks` + `tb_domain_rules` 적재 및 `edge_*` 브릿지 테이블 생성
  - `pipeline/graph_builder.py`가 `CREATE OR REPLACE PROPERTY GRAPH`를 실행하여 6 Node × 4 Edge 그래프 구축
  - `Stage 4`에서 에이전트가 카탈로그 슬롯을 추출한 뒤 ISO GQL + SQL + 위키를 결합해 답변 생성

#### Step-by-Step 수정 포인트
1. `config/starter_config.json`: `"active_track": "standard"`, `"graph_engine": "bigquery"` 확인.
2. `data/input/03_tables/*.csv` & `customer_doc/`: 고객이 준 CSV만 두고 `project.json`의 `tables`에 등록(행마다 `provenance`·`source_ref`), 정책 문서 원본은 `customer_doc/`에 둠. 고객 테이블이 없으면 만들지 말고 Scenario A2의 (a)(b)(c)를 물음.
3. `pipeline/ingest.py`: CSV 로드 목록과 브릿지 엣지(`edge_*`) 생성 로직을 새 테이블 PK/FK에 맞게 수정 후 `python3 pipeline/ingest.py` 실행.
4. `pipeline/graph_builder.py`: `VERTEX TABLES`와 `EDGE TABLES`의 `KEY(...)`, `SOURCE KEY(...) REFERENCES ...`를 새 테이블에 맞게 수정 후 `python3 pipeline/graph_builder.py` 실행.
5. `src/agent/mcp_server.py`, `src/agent/reasoning_engine.py`, `config/portal_profile.json`: 런타임 MCP 3종 쿼리, 카탈로그 슬롯 목록, 스튜디오 UI 프로필을 새 도메인에 맞게 갱신.

#### Jetski / Cursor 복사-붙여넣기 프롬프트 (Scenario B)
```text
@01_prod.md @GEMINI.md @PROTOTYPING_PLAYBOOK.md @DESIGN.md 를 먼저 읽고 준수해줘.
우리 프로젝트를 [Scenario B: Track 2 Standard (정형 DW + 비정형 문서 BigQuery Property Graph 통합)]으로 프로토타이핑하려고 해.
대상 도메인은 [예: 스마트 제철소 설비 예지보전 / 인터넷은행 신용대출 DSR 심사 / 편의점 신선식품 폐기 지원금]이야. (industry_cases/ 하위 참조 템플릿 활용 가능)
코어 웹 서버(studio_server.py) 레이아웃과 라이트 테마 디자인은 그대로 유지하고, 5-File Swap 절차에 따라:
1. 고객이 준 테이블만 03_tables/에 두고 project.json tables에 등록(provenance 포함), 문서 원본은 customer_doc/에 둠. 테이블이 없으면 만들지 말고 나에게 선택지를 물어봐
2. pipeline/ingest.py와 pipeline/graph_builder.py의 노드·엣지 테이블 및 BigQuery Property Graph DDL을 갱신하고 실제 BigQuery에 적재·생성 실행
3. src/agent/mcp_server.py의 Runtime MCP 3종과 src/agent/reasoning_engine.py의 카탈로그 슬롯 파싱을 새 테이블에 맞게 연결
4. config/portal_profile.json을 업데이트해 6-Tab 스튜디오에서 Stage 1~4와 GQL 그래프가 실제 BigQuery 데이터로 동작하도록 완성해줘.
```

---

### Scenario C: 실시간 운영 인터락 · Cloud Spanner Graph 및 Graph Fabric 연동이 필요한 경우 (`Track 2/3 + Spanner / Both`)

- **적합한 경우**: 분석용 BigQuery Property Graph(기본값)뿐 아니라, **5축 그래프 엔진 선택 체크리스트**(`source_system`, `latency_slo`, `concurrency`, `write_freshness`, `data_scale`) 점검 결과 실시간 온라인 트랜잭션(OLTP, 수십~수백 ms) 서빙을 위한 **Cloud Spanner Graph(최소 100 PU)** 또는 **BigQuery `EXTERNAL_QUERY` 기반 Graph Fabric 연합 조인(`both` 모드)**이 필요할 때.
- **Step-by-Step 수정 포인트**:
  1. `project.json`: `"graph_engine"`을 `"spanner"` 또는 `"both"`로 설정하고 `"graph_engine_checklist"` 5축 판단 근거를 기록합니다. (별도 지정이 없을 때의 기본값은 `"bigquery"`입니다.)
  2. `terraform/terraform.tfvars`: `graph_engine = "both"`(또는 `"spanner"`) 설정 후 `python3 terraform/apply_terraform.py`를 실행하여 Spanner 인스턴스(`starter-spanner`, 100 PU), 데이터베이스(`starter_ontology_db`), BigQuery Spanner 연결(`spanner_fabric_conn`)을 선언적으로 프로비저닝합니다.
  3. `python3 pipeline/ingest.py`와 `python3 pipeline/graph_builder.py`를 실행하면 양쪽 엔진에 10개 테이블과 `STARTER_ONTOLOGY_GRAPH`가 배포되고, N-run `p50/p95` 비교 벤치마크 및 `EXTERNAL_QUERY` 연합 조인이 검증됩니다.
  4. 스튜디오 `Stage 3. Property Graph` 및 `Stage 4. Agent & MCP` 탭에서 `BigQuery Graph (Default)`와 `Spanner Graph (Online)`를 실시간 전환하며 8종 MCP 도구를 모두 실행할 수 있습니다.

#### Jetski / Cursor 복사-붙여넣기 프롬프트 (Scenario C)
```text
@01_prod.md @GEMINI.md @PROTOTYPING_PLAYBOOK.md 를 먼저 읽고 준수해줘.
[Scenario C: BigQuery Property Graph(기본) + Cloud Spanner Graph(선택) & Graph Fabric(both) 프로토타이핑]을 수행해줘.
1. project.json의 graph_engine_checklist 5축(source_system, latency_slo, concurrency, write_freshness, data_scale)을 점검해 기록하고 graph_engine을 "both"(또는 "spanner")로 설정해줘.
2. pipeline/ingest.py와 pipeline/graph_builder.py를 실행해 양쪽 엔진에 테이블과 STARTER_ONTOLOGY_GRAPH를 반영하고, BigQuery vs Spanner p50/p95 지연 시간 비교 및 EXTERNAL_QUERY 연합 조인 결과를 보고해줘.
```

---

### Scenario D: 감사 추적 리니지 & 50회 경계값 릴리스 게이트까지 완결하는 경우 (`Track 3 · Full`)

- **적합한 경우**: PoC 최종 검수나 경영진/보안 감사 시연을 위해 **문서 청크 해시(`SHA-256`)부터 최종 답변까지의 4계층 리니지(`Stage 5`)**, **Golden CQ 5건 정합성 검증**, **모호·정보부족·카탈로그 외 질의 10건×5회(50회) 라이브 벤치마크**, **Terraform 기반 Cloud Run 배포**까지 전주기를 완결할 때.
- **Step-by-Step 수정 포인트**:
  1. `config/starter_config.json`: `"active_track": "full"` 설정.
  2. Scenario B의 1~5단계 완료 후 `data/input/04_cq/golden_cqs.json`(정답 검증용 핵심 질의 5건)과 `boundary_cases.json`(필수 조건 누락 `INSUFFICIENT_PARAMETERS` 4건, 카탈로그 외 `MATCH_NOT_FOUND` 3건, 정상 경계 `GROUNDED` 3건 등 총 10건)을 도메인에 맞게 작성.
  3. `pipeline/validator.py`의 Golden CQ 검증 SQL을 새 테이블 기준으로 맞추고 `python3 pipeline/validator.py`를 실행해 `data/output/validation_report.json` 및 `boundary_benchmark_results.json` 실측 리포트를 생성.
  4. `terraform/terraform.tfvars`에 대상 GCP 프로젝트·리전을 기입하고 `terraform apply`로 Cloud Run 서비스를 배포.

#### Jetski / Cursor 복사-붙여넣기 프롬프트 (Scenario D)
```text
@01_prod.md @GEMINI.md @PROTOTYPING_PLAYBOOK.md 를 먼저 읽고 준수해줘.
현재 도메인 프로토타입을 [Scenario D: Track 3 Full-Stack (Stage 1~5 전주기 리니지·경계값 50회 평가·배포 게이트)] 기준으로 완결해줘.
1. config/starter_config.json의 active_track을 "full"로 설정
2. data/input/04_cq/golden_cqs.json(5건)과 boundary_cases.json(10건: GROUNDED / INSUFFICIENT_PARAMETERS / MATCH_NOT_FOUND 포함)을 우리 도메인 기준으로 점검·갱신
3. pipeline/validator.py를 실제 BigQuery 및 Vertex AI(gemini-3.8-flash) 대상으로 실행해 validation_report.json과 boundary_benchmark_results.json 실측 결과를 생성하고 Gate 1~5 통과 여부를 보고해줘.
```

---

## 4. 프로토타이핑 완료 점검표 (5분 Self-Check)

프로토타이핑 수정을 마친 후 아래 명령어가 에러 없이 실데이터로 통과하고, 다음 항목을 확인하면 시연할 수 있습니다.

- `data/output/gate0_report.json`의 `status`가 `PASS` (고객 문서가 있는 경우)
- 최종 보고에 데이터 출처 요약(문서별 원문 비율·청크 수, provenance별 행 수, CQ 근거 유형, 합성 데이터 여부, 정답 미확정 수)이 있음

```bash
# 0. 고객 문서 원문 변환 (customer_doc/ → 01_guides/*.md)
python3 pipeline/extract_docs.py --project <id>

# 1. Stage 1~2: 마크다운 파싱 · 3-Layer 위키 생성 · BigQuery 테이블/엣지 적재
python3 pipeline/ingest.py

# 2. Stage 3: BigQuery Property Graph & Spanner Graph DDL 생성·적용
python3 pipeline/graph_builder.py

# 3. Stage 5: Golden CQ 5건 & 경계값 10건×5회 라이브 평가
python3 pipeline/validator.py

# 4. 6-Tab 통합 웹 스튜디오 구동 및 UI 확인 (http://127.0.0.1:8080)
python3 -m src.web.studio_server 8080

# (추가 프로젝트) 0~3과 Gate 0를 한 번에: python3 run_pipeline.py --project <id> → http://127.0.0.1:8080/?project=<id>
```
