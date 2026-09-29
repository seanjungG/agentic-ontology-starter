# 상황별 빠른 프로토타이핑 플레이북 (`PROTOTYPING_PLAYBOOK.md`)

> **목적**: 이 스타터팩을 다른 프로젝트로 클론했을 때, 백과사전식 온톨로지 이론을 처음부터 공부하거나 코드를 새로 짜지 않고 **현재 가진 데이터 상황(4가지 시나리오)에 맞춰 핵심 파일 5개만 교체(Swap)하여 30분~반나절 안에 동작하는 도메인 프로토타입(파이프라인 + BigQuery Graph + 8종 MCP + 6-Tab 스튜디오)을 완성**하기 위한 실전 가이드입니다.
> **AI 코딩 에이전트(Jetski / Antigravity / Cursor / Claude Code) 사용자**: 아래 시나리오 중 본인 상황에 맞는 **복사-붙여넣기 부트스트랩 프롬프트**를 에이전트에게 그대로 전달하십시오.

---

## 1. 내 프로젝트는 어디에 해당하는가? (4대 프로토타이핑 시나리오 선택)

| 시나리오 | 어떤 상황인가? (보유 자산 & 목표) | 설정 트랙 (`active_track`) | 실행 Stage | 수정할 파일 수 |
| :--- | :--- | :---: | :---: | :---: |
| **[Scenario A](#scenario-a-비정형-정책매뉴얼-문서만-있는-경우-track-1--lite)**<br>**문서 전용 퀵스타트** | 아직 DW 테이블 연동은 없고, **업무 매뉴얼·약관·SOP 문서(MD/TXT)와 계산 규칙**만으로 3-Layer 위키 + 규칙 계산 MCP + 에이전트 Q&A를 즉시 띄우고 싶다. | `lite` | `Stage 1 → 2 → 4` | **4개** |
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
  ② data/input/*                    → 01_guides/*.md (정책 문서), 03_tables/*.csv (정형 테이블), 04_cq/*.json (검증 질의)
  ③ pipeline/ingest.py              → DOMAIN_RULES (비즈니스 규칙 메타데이터) 및 compile_3layer_wiki() 도메인 요약
  ④ pipeline/graph_builder.py       → CREATE OR REPLACE PROPERTY GRAPH 의 VERTEX TABLES / EDGE TABLES 매핑
  ⑤ src/agent/mcp_server.py &       → Runtime MCP 3종의 SQL/GQL 쿼리 + config/portal_profile.json 의 화면 문구/샘플 질문
     config/portal_profile.json
```

> **산업군 레퍼런스 즉시 활용 팁**: 바닥부터 스키마를 고민하기 어렵다면 [`industry_cases/README.md`](industry_cases/README.md)에 준비된 **4대 산업군 8종 비식별 템플릿**(제조 2종, 금융 2종, 리테일 2종, 통신 2종)의 노드·엣지 설계와 CSV/SQL 샘플을 그대로 복사해 시작하십시오.

---

## 3. 시나리오별 실행 레시피 & Jetski / Cursor 부트스트랩 프롬프트

### Scenario A: 비정형 정책·매뉴얼 문서만 있는 경우 (`Track 1 · Lite`)

- **적합한 경우**: 인사/법무 규정, 금융 여신 심사 지침서, 설비 안전 매뉴얼 등 **문서(Markdown)와 계산 수식(위약금, 한도, 패널티 등)은 있으나 정형 DW 테이블 없이 빠르게 에이전트를 시연**해야 할 때.
- **동작 방식**: 물리 Property Graph(`Stage 3`)를 건너뛰고, 문서를 **SHA-256 해시 기반 청크(`tb_doc_chunks`) + 3-Layer OKF 위키(`data/llm_wiki/*.md`) + 결정론적 규칙(`tb_domain_rules`)**으로 컴파일한 뒤 에이전트(`Stage 4`)가 위키와 규칙 계산 MCP로 답변합니다.

#### Step-by-Step 수정 포인트
1. `config/starter_config.json`: `"active_track": "lite"`, `"graph_engine": "none"`으로 설정.
2. `data/input/01_guides/`: 기존 가이드 대신 새 도메인의 정책 마크다운 파일(`01_domain_policy.md` 등) 배치.
3. `pipeline/ingest.py`: `DOMAIN_RULES` 리스트에 문서 내 핵심 계산 규칙(예: 중도상환수수료율, 안전 임계치 등) 3~4건을 정의.
4. `src/agent/mcp_server.py`: `mcp_calculate_penalty_rule` 함수 내부의 수식을 해당 도메인 계산식으로 변경하고, `config/portal_profile.json`의 샘플 질의를 갱신.

#### Jetski / Cursor 복사-붙여넣기 프롬프트 (Scenario A)
```text
@01_prod.md @GEMINI.md @PROTOTYPING_PLAYBOOK.md 를 먼저 읽고 준수해줘.
현재 프로젝트는 [Scenario A: Track 1 Lite (비정형 문서 기반 프로토타이핑)]으로 진행할 거야.
기존 6-Tab 스튜디오(src/web/studio_server.py)와 2-Pass 에이전트 구조는 절대 재작성하지 말고 다음 4가지만 수정해서 프로토타이핑해줘:
1. config/starter_config.json의 active_track을 "lite"로 설정
2. 내가 제공한 [도메인명/문서내용]을 기반으로 data/input/01_guides/ 마크다운 문서와 data/input/05_glossary/business_glossary.json 갱신
3. pipeline/ingest.py의 DOMAIN_RULES와 3-Layer 위키 생성 로직을 이 도메인 규칙에 맞게 업데이트하고 python3 pipeline/ingest.py 실행
4. src/agent/mcp_server.py의 규칙 계산 MCP 도구와 config/portal_profile.json의 Stage 설명·샘플 질의를 이 도메인에 맞게 업데이트한 뒤 스튜디오 서버 동작 확인해줘.
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
2. `data/input/03_tables/*.csv` & `01_guides/*.md`: 새 도메인의 CSV 테이블과 정책 문서 배치 (빠른 시작을 원하면 `industry_cases/{manufacturing,finance,retail,telecom}/` 하위 샘플 CSV 참조).
3. `pipeline/ingest.py`: CSV 로드 목록과 브릿지 엣지(`edge_*`) 생성 로직을 새 테이블 PK/FK에 맞게 수정 후 `python3 pipeline/ingest.py` 실행.
4. `pipeline/graph_builder.py`: `VERTEX TABLES`와 `EDGE TABLES`의 `KEY(...)`, `SOURCE KEY(...) REFERENCES ...`를 새 테이블에 맞게 수정 후 `python3 pipeline/graph_builder.py` 실행.
5. `src/agent/mcp_server.py`, `src/agent/reasoning_engine.py`, `config/portal_profile.json`: 런타임 MCP 3종 쿼리, 카탈로그 슬롯 목록, 스튜디오 UI 프로필을 새 도메인에 맞게 갱신.

#### Jetski / Cursor 복사-붙여넣기 프롬프트 (Scenario B)
```text
@01_prod.md @GEMINI.md @PROTOTYPING_PLAYBOOK.md @DESIGN.md 를 먼저 읽고 준수해줘.
우리 프로젝트를 [Scenario B: Track 2 Standard (정형 DW + 비정형 문서 BigQuery Property Graph 통합)]으로 프로토타이핑하려고 해.
대상 도메인은 [예: 스마트 제철소 설비 예지보전 / 인터넷은행 신용대출 DSR 심사 / 편의점 신선식품 폐기 지원금]이야. (industry_cases/ 하위 참조 템플릿 활용 가능)
코어 웹 서버(studio_server.py) 레이아웃과 라이트 테마 디자인은 그대로 유지하고, 5-File Swap 절차에 따라:
1. data/input/01_guides/, 03_tables/, 04_cq/, 05_glossary/ 데이터를 해당 도메인에 맞게 구성
2. pipeline/ingest.py와 pipeline/graph_builder.py의 노드·엣지 테이블 및 BigQuery Property Graph DDL을 갱신하고 실제 BigQuery에 적재·생성 실행
3. src/agent/mcp_server.py의 Runtime MCP 3종과 src/agent/reasoning_engine.py의 카탈로그 슬롯 파싱을 새 테이블에 맞게 연결
4. config/portal_profile.json을 업데이트해 6-Tab 스튜디오에서 Stage 1~4와 GQL 그래프가 실제 BigQuery 데이터로 동작하도록 완성해줘.
```

---

### Scenario C: 실시간 운영 인터락 · Spanner Graph DDL이 필요한 경우 (`Track 2 + Spanner`)

- **적합한 경우**: 분석용 BigQuery Property Graph뿐 아니라, **실시간 온라인 트랜잭션(OLTP) 환경인 Cloud Spanner Graph로의 이관·병행 아키텍처(`INTERLEAVE IN PARENT`)**를 고객에게 함께 제시해야 할 때.
- **Step-by-Step 수정 포인트**:
  - Scenario B의 1~5단계를 동일하게 수행하면서, `pipeline/graph_builder.py`의 `build_spanner_ddl()` 함수가 새 도메인 노드/엣지 스키마에 맞는 `data/output/create_spanner_graph.sql`을 생성하도록 매핑합니다.
  - 스튜디오 `Stage 3. Property Graph` 탭에서 BigQuery Graph DDL과 Spanner Graph DDL을 나란히 비교 시연할 수 있습니다.

#### Jetski / Cursor 복사-붙여넣기 프롬프트 (Scenario C)
```text
@01_prod.md @GEMINI.md @PROTOTYPING_PLAYBOOK.md 를 먼저 읽고 준수해줘.
[Scenario C: BigQuery Property Graph + Cloud Spanner Graph 이중 DDL 프로토타이핑]을 수행해줘.
Scenario B 절차에 더해 pipeline/graph_builder.py의 build_spanner_ddl()이 우리 도메인 엔티티의 부모-자식 계층(INTERLEAVE IN PARENT)을 반영한 data/output/create_spanner_graph.sql을 생성하도록 업데이트하고 python3 pipeline/graph_builder.py를 실행해줘.
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

프로토타이핑 수정을 마친 후 아래 4개 명령어가 에러 없이 실데이터로 통과하면 즉시 시연 및 배포가 가능합니다.

```bash
# 1. Stage 1~2: 마크다운 파싱 · 3-Layer 위키 생성 · BigQuery 테이블/엣지 적재
python3 pipeline/ingest.py

# 2. Stage 3: BigQuery Property Graph & Spanner Graph DDL 생성·적용
python3 pipeline/graph_builder.py

# 3. Stage 5: Golden CQ 5건 & 경계값 10건×5회 라이브 평가
python3 pipeline/validator.py

# 4. 6-Tab 통합 웹 스튜디오 구동 및 UI 확인 (http://127.0.0.1:8080)
python3 -m src.web.studio_server 8080
```
