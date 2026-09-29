# Stage 1. 자산 탐색·스코핑·CQ 정의

> 스튜디오 [`Stage 1. Asset`](https://agentic-ontology-starter-924723860007.asia-northeast3.run.app/?tab=stage1) · MCP `mcp_stage1_asset_discovery` · 노트북 [stage1_asset_and_cq_ko.ipynb](../../notebooks/ko/stage1_asset_and_cq_ko.ipynb) · [English](../en/01_stage1_asset_and_cq_en.md) · [전체 방법론](./METHODOLOGY_KO.md)

## 목적

에이전트가 답해야 할 질문(CQ, Competency Question)을 먼저 정하고, 답에 필요한 문서와 테이블만 골라 BigQuery에 적재한다.
범위는 파일 단위로 정한다. 고른 파일 안의 문장은 줄이거나 고치지 않는다.
CQ마다 정답과 정답 검증 SQL을 함께 적어 두면 Stage 5에서 그대로 채점 기준이 된다.

## 입력

| 경로 (`data/input/`) | 내용 |
| :--- | :--- |
| `01_guides/sample_policy_guide.md` | 정책 가이드. 청크 `DOC_CHUNK_001`~`003` (180일 유지 의무, 위약금 산식) |
| `01_guides/sample_welfare_exemption_guide.md` | 면제 가이드. 청크 `DOC_CHUNK_004`~`005` (복지·군입대 면제, 24개월 비용 비교) |
| `03_tables/devices.csv`, `plans.csv`, `subsidies.csv`, `customer_contracts.csv` | 마스터 테이블 4개: 단말 4행, 요금제 6행, 지원금 정책 5행, 고객 약정 6행 |
| `03_tables/domain_rules.csv`, `rule_plan_edges.csv` | 규칙 4행, 규칙→요금제 연결 12행 (Stage 2에서 사용) |
| `03_tables/schema_master_tables.sql` | 참고용 DDL. 실제 스키마는 `terraform/bigquery.tf`이며 코드는 이 파일을 읽지 않는다 |
| `04_cq/golden_competency_questions.json` | Golden CQ 5개 (`CQ-01`~`CQ-05`) |
| `04_cq/boundary_cases.json` | 경계값 질의 10개 (`BQ-01`~`BQ-10`, Stage 5에서 사용) |
| `05_glossary/business_glossary.json` | 용어 4개. 현재 파이프라인 코드는 읽지 않는다 |

고객 ID는 `CUST_DEMO_001`~`CUST_DEMO_006` 형식의 합성 식별자다. 샘플 CSV의 모든 행은 `provenance=SYNTHETIC_DEMO`, `source_ref=project.json#synthetic`이다.

CQ 한 건의 필드:

| 필드 | 용도 |
| :--- | :--- |
| `query` | 에이전트에 보낼 질문. 질문 속 ID·따옴표 고유명사는 청크나 테이블에 있어야 한다 |
| `evidence_type` | `sql`(테이블 근거) 또는 `citation`(문서 근거) |
| `expected_citation` | citation CQ의 근거 `chunk_id`와 원문 구절 `quote`. 구절은 청크에 그대로 있어야 한다 |
| `expected_facts` | citation CQ 답변에 들어가야 하는 원문 표현 목록 |
| `answer_confirmed_by`, `confirmed_at` | 정답을 확정한 사람과 시각. 비어 있으면 '정답 미확정' |
| `expected_value` | 사람이 읽는 정답 설명 |
| `expected_math` | 채점에 쓰는 정답 값 (예: `{"penalty": 100000}`) |
| `verification_sql` | 에이전트와 별도로 정답을 계산하는 BigQuery SQL. `{fq}`는 `프로젝트.데이터셋`으로 바뀐다 |
| `grounded_chunk` | 답변이 인용해야 하는 청크 ID |
| `target_tools` | 예상 호출 도구. 참고용이며 채점에는 쓰지 않는다 |

## 이 Stage의 MCP: `mcp_stage1_asset_discovery`

| Step | 실제 수행 (`src/agent/mcp_server.py`) |
| :--- | :--- |
| `profile_tables` | `__TABLES__`에서 테이블별 행 수·크기 조회 → `table_inventory` |
| `scan_guides` | 이 MCP에서는 수행하지 않는다. 가이드 청킹은 `pipeline/ingest.py`의 `run_ingest()`가 한다 |
| `prune_noise` | 대응 코드 없음 (Step 이름만 있음) |
| `tag_pii_governance` | `tb_customer_contract.customer_id` 중 `^CUST_DEMO_[0-9]{3}$` 형식이 아닌 건수 → `pii_check.non_deidentified_ids` |

`steps` 인자는 결과의 `executed_steps`에 기록된다. 현재 핸들러는 선택한 Step과 관계없이 위 두 쿼리를 모두 실행한다.

## 절차

1. **범위 정하기**: CQ에 답하는 데 필요한 문서·테이블을 파일 단위로 고른다. 파일 안의 문장은 줄이거나 고치지 않는다. 스타터는 가이드 2개, CSV 6개로 시작한다.
2. **CQ 작성**: sql CQ는 `expected_math`, `verification_sql`, `grounded_chunk`를, citation CQ는 `expected_citation`, `expected_facts`를 채운다. 정답은 사람이 확정하고 `answer_confirmed_by`에 기록한다.
3. **테이블 준비**: BigQuery 데이터셋과 테이블 10개는 Terraform(`terraform/bigquery.tf`)으로 만든다.
4. **적재**: `run_ingest()`가 CSV 6개와 가이드 청크를 읽어 테이블 10개를 비우고(`TRUNCATE`) 다시 채운다(`INSERT`). 테이블마다 한 트랜잭션이며, 하나라도 실패하면 파이프라인이 멈춘다. 값은 코드에 쓰지 않고 CSV에서만 읽는다.
5. **확인**: `mcp_stage1_asset_discovery`로 행 수와 비식별 규칙 위반 건수를 확인한다.

## 산출물

| ID | 산출물 | 스타터에서 |
| :--- | :--- | :--- |
| `D1.1` | 도메인 스코핑 및 노이즈 필터링 헌장 | 별도 문서 없음. 샘플 데이터 범위가 곧 스코프다 |
| `D1.2` | Golden CQ 및 정답 검증 명세서 | `data/input/04_cq/golden_competency_questions.json` |
| `D1.3` | 원천 자산 인벤토리 및 스키마 프로파일 | `terraform/bigquery.tf` (스키마), MCP 결과 `table_inventory` (행 수·크기) |
| `D1.4` | Dataplex 카탈로그 태깅 및 거버넌스 맵 | 스타터 미구현 |

## 게이트 (Gate 1)

- [ ] 고객 문서가 있으면 Gate 0(`data/output/gate0_report.json`)가 `PASS`다.
- [ ] CQ마다 `evidence_type`이 `sql` 또는 `citation`이다. sql CQ는 `expected_math`, `verification_sql`, `grounded_chunk`가, citation CQ는 청크에 그대로 있는 `expected_citation`이 있다. `pipeline/validator.py`의 `load_cqs()`가 검사한다.
- [ ] sql CQ의 `verification_sql` 결과가 `expected_math`와 같다. Stage 5 리포트의 `verification_status`에 `SQL_MATCH`로 남는다.
- [ ] `pii_check.non_deidentified_ids`가 0이다.
- [ ] `table_inventory`의 행 수가 CSV 행 수와 같다.

## 스튜디오에서 보기

[Stage 1. Asset 탭 열기](https://agentic-ontology-starter-924723860007.asia-northeast3.run.app/?tab=stage1)

- 자산 목록: 마스터 테이블 4개와 가이드 2개. 행을 누르면 오른쪽 패널에 CSV 레코드나 청크 원문이 나온다.
- `▶ Stage 1 MCP 실행`: 위 MCP를 BigQuery에서 실행하고 결과를 보여 준다.

## 노트북

[stage1_asset_and_cq_ko.ipynb](../../notebooks/ko/stage1_asset_and_cq_ko.ipynb)

## 최신 문서 변환 결과 · Gate 0 · CQ 샘플 (실제 출력 예시)

### 1. 코드 기반 원문 변환 마크다운 (`01_guides/<stem>.md`)
`pipeline/extract_docs.py`가 `customer_doc/`의 원본(`PDF`, `DOCX`, `MD`, `TXT`)에서 AI 요약 없이 원문을 추출할 때 상단에 출처·SHA-256·총 쪽수를 기록하고 각 페이지 경계에 `<!-- page: N -->` 주석을 붙인다.

```markdown
<!-- source_doc: customer_doc/01_service_terms.pdf | source_sha256: 0004623c1b39ebfd821ef3db6ca1eb8c94fb596094997a5e8f8b2d5a42efac61 | pages: 1 -->

<!-- page: 1 -->
제1조(목적) 본 약관은 서비스 이용 조건 및 해지 시 반환금 산정 기준을 규정함을 목적으로 한다.

제2조(의무 유지 기간) 할인 반환금 면제를 위한 최소 유지 기간은 개통일로부터 180일로 한다.
```

### 2. Gate 0 원문 충실도 검증 리포트 (`data/output/gate0_report.json`)
Stage 1 적재 전 `pipeline/validator.py`의 `run_gate0()`가 문서별 글자 수 비율(`char_ratio >= 0.95`, 머리글 제거 전 원문 대비), 12자 조각 일치율(`ngram_match_ratio >= 0.95`), 텍스트 보유 페이지 100% 포함, 조문 번호 누락 0건, 수동 작성 `.md` 0건을 검사한다.

```json
{
  "status": "PASS",
  "documents": [
    {
      "source_doc": "customer_doc/01_service_terms.pdf",
      "md_file": "01_guides/01_service_terms.md",
      "char_ratio": 1.0,
      "ngram_match_ratio": 1.0,
      "pages_with_text_ratio": 1.0,
      "missing_articles": [],
      "passed": true
    }
  ],
  "unregistered_guides": []
}
```

### 3. `evidence_type: "citation"` vs `"sql"` CQ 정의 샘플 (`golden_competency_questions.json`)

```json
[
  {
    "cq_id": "CQ-DOC-01",
    "query": "할인 반환금 면제를 위한 최소 유지 기간은 몇 일인가요?",
    "evidence_type": "citation",
    "expected_citation": {
      "chunk_id": "DOC_CHUNK_002",
      "quote": "할인 반환금 면제를 위한 최소 유지 기간은 개통일로부터 180일로 한다."
    },
    "expected_facts": ["180일"],
    "answer_confirmed_by": "domain_reviewer",
    "confirmed_at": "2026-09-29T12:00:00Z"
  },
  {
    "cq_id": "CQ-01",
    "query": "고객 CUST_DEMO_001이 가입한 단말과 요금제 기준 할부원금은 얼마인가요?",
    "evidence_type": "sql",
    "expected_math": {"installment_principal": 950000},
    "verification_sql": "SELECT retail_price_krw - total_subsidy_krw AS installment_principal FROM ...",
    "grounded_chunk": "DOC_CHUNK_001",
    "answer_confirmed_by": "domain_reviewer",
    "confirmed_at": "2026-09-29T12:00:00Z"
  }
]
```

## 내 데이터에 적용하기 (예측 불가능한 비즈니스·데이터 유입 시 절차)

1. **문서 변환 및 Gate 0**: 원본(`PDF`·`DOCX`·`MD`·`TXT`)을 `projects/<id>/customer_doc/`에 넣고 `python3 pipeline/extract_docs.py --project <id>`를 실행한다. 원문 전체가 `01_guides/*.md`로 변환되고, 청크는 조문(`제N조(`)·제목·문단 단위로 자동 분할된다(상한 1,500자). 에이전트가 원문을 요약하거나 수동으로 `.md`를 작성하지 않는다. 텍스트가 없는 스캔 페이지가 있으면 `needs_ocr: true`로 멈추고 OCR 여부를 묻는다.
2. **테이블 유무 판별 및 출처 기록**: 고객이 직접 준 테이블만 `03_tables/`에 두고 `project.json`의 `tables`에 등록한다. 모든 행에 `provenance`(`CUSTOMER_PROVIDED`)와 `source_ref`를 둔다. 고객 테이블이 없으면 비워 두고 `track: "auto"`(자동으로 `lite` 전환)로 진행하며, 절대 샘플이나 합성 데이터로 채우지 않는다. 스키마가 샘플과 다르면 `terraform/bigquery.tf`와 `project.json`의 `*_module` 오버라이드를 함께 지정한다.
3. **CQ 작성 및 Gate 1 검증**: 문서 근거 CQ는 `evidence_type: "citation"`, 테이블 근거 CQ는 `evidence_type: "sql"`로 쓴다. 질문에 쓰는 ID·따옴표 고유명사는 실제 청크나 테이블에 존재해야 하며, 정답은 사람이 확정하고 `answer_confirmed_by`에 기록한다.
4. **비식별 규칙**: 고객 ID 형식이 다르면 `mcp_stage1_asset_discovery`의 정규식(`^CUST_DEMO_[0-9]{3}$`)을 바꾼다.
5. **실행**: `python3 run_pipeline.py --project <id>`를 실행한다. 원문 변환과 Gate 0·Gate 1을 먼저 검사하고, 실패하면 적재하지 않는다.
