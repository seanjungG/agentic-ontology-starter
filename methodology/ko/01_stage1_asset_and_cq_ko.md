# Stage 1. 자산 탐색·스코핑·CQ 정의

> 스튜디오 [`Stage 1. Asset`](https://agentic-ontology-starter-924723860007.asia-northeast3.run.app/?tab=stage1) · MCP `mcp_stage1_asset_discovery` · 노트북 [stage1_asset_and_cq_ko.ipynb](../../notebooks/ko/stage1_asset_and_cq_ko.ipynb) · [English](../en/01_stage1_asset_and_cq_en.md) · [전체 방법론](./METHODOLOGY_KO.md)

## 목적

에이전트가 답해야 할 질문(CQ, Competency Question)을 먼저 정하고, 답에 필요한 문서와 테이블만 골라 BigQuery에 적재한다.
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

고객 ID는 `CUST_DEMO_001`~`CUST_DEMO_006` 형식의 합성 식별자다.

CQ 한 건의 필드:

| 필드 | 용도 |
| :--- | :--- |
| `query` | 에이전트에 보낼 질문 |
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

1. **범위 정하기**: CQ에 답하는 데 필요한 문서·테이블만 남긴다. 스타터는 가이드 2개, CSV 6개로 시작한다.
2. **CQ 작성**: CQ마다 `expected_math`, `verification_sql`, `grounded_chunk`를 채운다. 정답은 사람이 확정한다.
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

- [ ] CQ마다 `expected_math`, `verification_sql`, `grounded_chunk`가 있다.
- [ ] `verification_sql` 결과가 `expected_math`와 같다. Stage 5 리포트의 `verification_status`에 `SQL_MATCH`로 남는다.
- [ ] `pii_check.non_deidentified_ids`가 0이다.
- [ ] `table_inventory`의 행 수가 CSV 행 수와 같다.

## 스튜디오에서 보기

[Stage 1. Asset 탭 열기](https://agentic-ontology-starter-924723860007.asia-northeast3.run.app/?tab=stage1)

- 자산 목록: 마스터 테이블 4개와 가이드 2개. 행을 누르면 오른쪽 패널에 CSV 레코드나 청크 원문이 나온다.
- `▶ Stage 1 MCP 실행`: 위 MCP를 BigQuery에서 실행하고 결과를 보여 준다.

## 노트북

[stage1_asset_and_cq_ko.ipynb](../../notebooks/ko/stage1_asset_and_cq_ko.ipynb)

## 내 데이터에 적용하기

1. **문서**: `data/input/01_guides/`의 `.md` 파일을 바꾼다. 청크 경계는 `<!-- DOC_CHUNK_001: 제목 -->` 주석으로 표시한다. 주석이 없으면 `## ` 제목 단위로 나뉜다.
2. **테이블**: 파일명과 열 이름을 유지하면 CSV 행만 바꿔도 적재된다. 파일명·열 이름은 `pipeline/ingest.py`에 고정되어 있다. 스키마를 바꾸려면 `terraform/bigquery.tf`, `pipeline/ingest.py`, `pipeline/graph_builder.py`, `src/agent/mcp_server.py`를 함께 고친다.
3. **CQ**: `golden_competency_questions.json`을 같은 필드 구조로 다시 쓴다.
4. **비식별 규칙**: 고객 ID 형식이 다르면 `mcp_stage1_asset_discovery`의 정규식(`^CUST_DEMO_[0-9]{3}$`)을 바꾼다.
5. **실행**: 환경 변수 `GCP_PROJECT_ID`, `BQ_DATASET_ID`, `GCS_WIKI_BUCKET`을 설정하고 `python3 run_pipeline.py`를 실행한다.
