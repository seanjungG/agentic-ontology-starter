# Stage 5. 리니지·평가·배포 게이트

> 스튜디오 [`Stage 5. Lineage & Eval`](https://agentic-ontology-starter-lwrlf7yogq-du.a.run.app/?tab=stage5) · MCP `mcp_stage5_lineage_and_eval` · 노트북 [stage5_lineage_and_evaluation_ko.ipynb](../../notebooks/ko/stage5_lineage_and_evaluation_ko.ipynb) · [English](../en/05_stage5_lineage_and_eval_en.md) · [전체 방법론](./METHODOLOGY_KO.md)

## 목적

원천 자산(CSV·가이드 문서)부터 BigQuery 테이블, Property Graph(`STARTER_ONTOLOGY_GRAPH`), MCP 도구(8종), 에이전트까지 이어지는 엔드투엔드 데이터 리니지를 확인하고, Golden CQ 5건과 경계값 질의 10건(×5회 반복)을 통과했는지 검증해 배포 여부를 판정한다.

## 입력

- BigQuery 테이블 10개 및 `STARTER_ONTOLOGY_GRAPH`
- Golden CQ 평가셋: `data/input/04_cq/golden_competency_questions.json` (5건: `CQ-01`~`CQ-05`)
- 경계값 평가셋: `data/input/04_cq/boundary_cases.json` (10건: `BQ-01`~`BQ-10`)
- 평가 실행 모듈: `pipeline/validator.py` (`run_validation`, `run_boundary`)

## 이 Stage의 MCP: `mcp_stage5_lineage_and_eval`

| Step | 실제 수행 (`src/agent/mcp_server.py`) |
| :--- | :--- |
| `build_4tier_lineage` | `tb_customer_contract` → `tb_device_master` / `tb_plan_master` / `tb_subsidy_policy` → `edge_rule_applies_to_plan` → `tb_doc_chunks` 리니지 조인(`lineage_records`, 18행)을 조회한다 |
| `run_golden_cq_suite` | `data/output/cq_benchmark_report.json`의 최근 Golden CQ 5건 검증 결과(`evaluated_at`, `total_cqs`, `passed`, `accuracy_rate`, `method`)를 반환한다 |
| `diagnose_boundary_failures` | `data/output/boundary_benchmark_results.json`의 경계값 10건×5회 결과(`avg_success_rate`, `avg_consistency_rate`, `avg_intent_stability`)를 함께 점검한다 |

## 스튜디오 리니지 DAG (`config/lineage_spec.json`)

`Stage 5. Lineage & Eval` Part A는 메인 스튜디오 리니지와 같은 캔버스 DAG입니다 (`src/lineage/lineage_engine.py`, `/api/lineage/{graph,trace,explain}`).

- 스펙: 카테고리 7열(데이터 연결 → GCP 원천 → 데이터 변환 → 도메인 규칙 → 온톨로지 시맨틱 → MCP → 에이전트·평가), 프리셋 3종, 노드, 엣지. 샘플은 37 노드 / 67 엣지이며 열마다 세로 중앙에 배치합니다.
- 구조 원칙: 파이프라인 코드가 실제로 읽고 쓰는 자원만 적습니다 (`pipeline/ingest.py`의 GCS `raw/`·`parsed/`·`ontology/` 업로드, BigQuery 10개 테이블, `graph_engine`이 `spanner`/`both`일 때 Spanner Graph, 에이전트 최종 답변 → `pipeline/validator.py` 루브릭 심사). 가상 커넥터나 없는 테이블은 넣지 않고, 코드가 바뀌면 스펙도 함께 고칩니다.
- 볼륨은 요청 시 실측합니다 (120초 캐시): `bq_table` → BigQuery `__TABLES__` 행 수, `gcs_prefix` → GCS 객체 수, `bq_graph`/`spanner_graph` → `INFORMATION_SCHEMA.PROPERTY_GRAPHS`의 노드·엣지 테이블 수. 조회에 실패하면 `조회 실패`로 표시하고 다른 값으로 채우지 않습니다. 측정 키가 없는 노드(MCP 도구 등)만 스펙 설명값을 표시합니다.
- 숨김 계층은 두지 않습니다. 도메인 규칙은 별도 열로 항상 표시합니다.
- 노드 클릭: 상·하류 BFS 하이라이트, 상세 패널(메타데이터·볼륨 출처·직접 상/하류·규칙 기반 요약), Stage 4 에이전트 질의 연결.
- 프로젝트별 스펙은 `projects/<id>/config/lineage_spec.json`에 작성합니다 ([`projects/_template/README.md`](../../projects/_template/README.md)).

## 절차 (`pipeline/validator.py`)

1. **레코드 단위 리니지 조인 (`build_4tier_lineage`)**:
   - Tier 0 (Raw Files): `sample_policy_guide.md`, `sample_welfare_exemption_guide.md`, CSV 6종 (또는 외부 프로젝트 문서·데이터)
   - Tier 1 (Anchored Chunks): `tb_doc_chunks` (`DOC_CHUNK_001`~`005`, `content_sha256`, `origin_type`, `extract_method`, `source_locator`)
   - Tier 2 (Domain Rules & Bridges): `tb_domain_rules`, `edge_rule_applies_to_plan` (또는 `03_wiki/entities.md`, `concepts.md`)
   - Tier 3 (Contracts & Property Graph): `tb_customer_contract`, `STARTER_ONTOLOGY_GRAPH` (6 노드 / 4 엣지)
   - Tier 4 (Golden CQ Answers): `CQ-01`~`CQ-05` 에이전트 응답 및 근거 인용
2. **Golden CQ 결정론적 검증 (`run_validation`) — `evidence_type` 분기 채점**:
   - **`evidence_type: "sql"` (`full` 트랙)**: 독립 실행한 BigQuery `verification_sql` 결과가 `expected_math`와 일치하는지, 그리고 에이전트(`AiFdeAgentEngine.execute_cycle`) 실시간 답변이 정답 수치와 `grounded_chunk`를 포함하는지 검증한다.
   - **`evidence_type: "citation"` (`lite` 트랙)**: 에이전트(`execute_lite_doc_cycle`) 답변에 `grounded_chunk`(`DOC_CHUNK_XXX`) 인용이 포함되어 있고 `expected_keywords` 중 최소 1개 이상이 포함되는지 검증한다.
   - **`status: "UNCONFIRMED"` 문항 처리**: 고객이 정답(`expected_math` 또는 `expected_keywords`)을 아직 확정하지 않은 문항은 자동 통과(100%)로 위장하지 않고 `unconfirmed_cq_count`로 별도 집계한다.
   - **최종 답변 루브릭 채점 (`_judge`)**: 값 포함 검사만으로는 질문과 다른 답을 해도 통과할 수 있다. 그래서 에이전트 최종 답변을 LLM 심사(같은 Gemini 모델)가 질문 적합성 20 · 정확성 30 · 완결성 20 · 근거 충실도 15 · 명확성 15로 채점한다. 심사에는 질문, 정답, 에이전트가 실제 조회한 도구 결과와 인용 청크 원문만 넣는다. 질문 적합성 8점 미만이면 총점 상한 40, 근거에 없는 수치는 항목당 3점 이상 감점. 판정이 `PASS`가 아니면 문항은 `FAILED`(`RUBRIC_PARTIAL`/`RUBRIC_FAIL`).
   - **중복 답변 검사**: 서로 다른 문항의 답변 3-gram Jaccard가 0.5 이상이면 두 문항 모두 `DUPLICATE_ANSWER`로 실패 처리한다. 질문이 다른데 답이 같다는 것은 조회나 답변 생성이 질문을 반영하지 못했다는 신호다.
   - 채점을 올리려고 정답·근거를 미리 넣어 두거나 고정 응답을 쓰지 않는다. 점수 개선은 프롬프트와 조회 로직으로만 한다.
3. **실행 출처 메타데이터 기록 (`cq_benchmark_report.json`)**:
   - 평가 리포트에는 반드시 입력 자산 매니페스트 해시(`input_manifest_sha256`), 출처 분류(`evidence_provenance`), 합성 데이터 포함 여부(`synthetic_basis`), 정답 미확정 문항 수(`unconfirmed_cq_count`)를 함께 기록한다.
   ```json
   {
     "run_id": "val_20260929_143012",
     "project_id": "telecom_sample",
     "track": "full",
     "evaluated_at": "2026-09-29T14:30:12+09:00",
     "input_manifest_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
     "evidence_provenance": "CUSTOMER_PROVIDED",
     "synthetic_basis": false,
     "unconfirmed_cq_count": 0,
     "total_cqs": 5,
     "passed": 5,
     "accuracy_rate": 100.0
   }
   ```
4. **스튜디오 평가 배지 표시 상태**:
   - **미측정 (`NOT_EVALUATED`)**: 리포트 파일이 없거나 `run_id`가 없는 초기 상태.
   - **입력 변경 후 재평가 필요 (`STALE_EVALUATION`)**: 현재 프로젝트 입력 파일의 해시가 리포트의 `input_manifest_sha256`과 불일치할 때 경고 배지 표시.
   - **합성 데이터 기준 (`SYNTHETIC_BASIS: NN%`)**: `SYNTHETIC_DEMO` 자산이 포함된 상태에서 측정된 점수는 고객 실데이터 점수와 혼동되지 않도록 `[합성 데이터 기준 NN%]`로 구분 표기.
   - **정답 미확정 N건 (`UNCONFIRMED: N건`)**: `unconfirmed_cq_count > 0`인 경우 확정 문항 통과율과 미확정 건수를 분리 표기.
5. **경계값 10건 × 5회 라이브 벤치마크 (`run_boundary`)**:
   - 정상 근거 질의(`GROUNDED`), 조건 미일치(`MATCH_NOT_FOUND`), 필수 파라미터 누락(`INSUFFICIENT_PARAMETERS`)이 섞인 10개 질문을 각 5회(총 50회) 실행한다.
   - 통과율(`avg_success_rate`), 문항 내 일관성(`avg_consistency_rate`), 의도 안정성(`avg_intent_stability`)을 측정해 `data/output/boundary_benchmark_results.json`에 기록한다.

## 산출물

| ID | 산출물 | 스타터에서 |
| :--- | :--- | :--- |
| `D5.1` | 5-Stage 엔드투엔드 데이터 리니지 명세 및 영향도 맵 | 스튜디오 `Stage 5. Lineage & Eval` 리니지 DAG(`config/lineage_spec.json`) 및 `mcp_stage5_lineage_and_eval` (`lineage_records`) |
| `D5.2` | PII 마스킹 및 접근 제어 거버넌스 정책 | `tb_customer_contract`의 고객 식별자(`CUST_DEMO_001`~`006`) 비식별 코드 사용 |
| `D5.3` | Golden CQ 검증 리포트 | `data/output/cq_benchmark_report.json` (`input_manifest_sha256`, `synthetic_basis` 포함) |
| `D5.4` | 경계값·일관성 벤치마크 리포트 | `data/output/boundary_benchmark_results.json` (10건 × 5회 = 50회 실측) |
| `D5.5` | 프로덕션 배포 패키지 (Dockerfile · Terraform IaC) | `Dockerfile`, `terraform/` (`main.tf`, `bigquery.tf`, `storage.tf`, `iam.tf`, `cloud_run.tf`) |

## 게이트 (Gate 5 — 최종 배포 승인)

- [ ] 확정된 Golden CQ 검증 통과율 100.0% 및 `input_manifest_sha256` 일치 확인 (`cq_benchmark_report.json`).
- [ ] 모든 문항의 최종 답변 루브릭 판정 `PASS`, `duplicate_pairs` 0건 (`rubric_avg_total`, `rubric_axis_avg` 기록).
- [ ] 경계값 10건 × 5회 벤치마크에서 `INSUFFICIENT_PARAMETERS` 및 `MATCH_NOT_FOUND` 가드레일이 정상 작동하고 결과가 `boundary_benchmark_results.json`에 기록됨.
- [ ] 저장소 내 시크릿(`AIza...`), 고객사 고유 식별자, 로컬 절대 경로(`/<local-home>/`) 0건 확인.
- [ ] `terraform apply` 통과 및 Cloud Run 헬스체크(`/api/portal/profile`) 정상 응답 확인.

## 스튜디오에서 보기

[Stage 5. Lineage & Eval 탭 열기](https://agentic-ontology-starter-lwrlf7yogq-du.a.run.app/?tab=stage5)

## 노트북

[stage5_lineage_and_evaluation_ko.ipynb](../../notebooks/ko/stage5_lineage_and_evaluation_ko.ipynb) · [English Notebook](../../notebooks/en/stage5_lineage_and_evaluation_en.ipynb)

## 내 데이터에 적용하기

1. `data/input/04_cq/golden_competency_questions.json`에 도메인 핵심 질문을 등록한다 (`full` 트랙은 `"evidence_type": "sql"`, `"verification_sql"`, `"expected_math"`, `lite` 트랙은 `"evidence_type": "citation"`, `"expected_keywords"`, `"grounded_chunk"`).
2. `data/input/04_cq/boundary_cases.json`에 파라미터 누락(`INSUFFICIENT_PARAMETERS`), 미존재 엔티티(`MATCH_NOT_FOUND`), 정상 복합 질의(`GROUNDED`) 케이스를 정의한다.
3. `python3 pipeline/validator.py --project <id>`를 실행해 리포트를 갱신한다.
