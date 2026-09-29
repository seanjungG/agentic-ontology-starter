# Stage 5. 리니지·평가·배포 게이트

> 스튜디오 [`Stage 5. Lineage & Eval`](https://agentic-ontology-starter-lwrlf7yogq-du.a.run.app/?tab=stage5) · MCP `mcp_stage5_lineage_and_eval` · 노트북 [stage5_lineage_and_evaluation_ko.ipynb](../../notebooks/ko/stage5_lineage_and_evaluation_ko.ipynb) · [English](../en/05_stage5_lineage_and_eval_en.md) · [전체 방법론](./METHODOLOGY_KO.md)

## 목적

원천 자산(CSV·가이드 문서)부터 BigQuery 테이블, Property Graph(`STARTER_ONTOLOGY_GRAPH`), MCP 도구(8종), 에이전트까지 이어지는 4계층 데이터 리니지를 확인하고, Golden CQ 5건과 경계값 질의 10건(×5회 반복)을 통과했는지 검증해 배포 여부를 판정한다.

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

## 절차 (`pipeline/validator.py`)

1. **4계층 데이터 리니지 구성**:
   - Tier 0 (Raw Files): `sample_policy_guide.md`, `sample_welfare_exemption_guide.md`, CSV 6종
   - Tier 1 (Anchored Chunks): `tb_doc_chunks` (`DOC_CHUNK_001`~`005`, `content_sha256`)
   - Tier 2 (Domain Rules & Bridges): `tb_domain_rules`, `edge_rule_applies_to_plan`
   - Tier 3 (Contracts & Property Graph): `tb_customer_contract`, `STARTER_ONTOLOGY_GRAPH` (6 노드 / 4 엣지)
   - Tier 4 (Golden CQ Answers): `CQ-01`~`CQ-05` 에이전트 응답 및 근거 인용
2. **Golden CQ 5건 결정론적 검증 (`run_validation`)**:
   - 각 CQ마다 독립 실행한 BigQuery `verification_sql` 결과가 `expected_math`와 일치하는지, 그리고 에이전트(`AiFdeAgentEngine`) 실시간 답변이 정답 수치와 `grounded_chunk`를 정확히 포함하는지 검증해 `data/output/cq_benchmark_report.json`에 기록한다.
3. **경계값 10건 × 5회 라이브 벤치마크 (`run_boundary`)**:
   - 정상 근거 질의(`GROUNDED`), 조건 미일치(`MATCH_NOT_FOUND`), 필수 파라미터 누락(`INSUFFICIENT_PARAMETERS`)이 섞인 10개 질문을 각 5회(총 50회) 실행한다.
   - 통과율(`avg_success_rate`), 문항 내 일관성(`avg_consistency_rate`), 의도 안정성(`avg_intent_stability`)을 측정해 `data/output/boundary_benchmark_results.json`에 기록한다.

## 산출물

| ID | 산출물 | 스타터에서 |
| :--- | :--- | :--- |
| `D5.1` | 5-Stage 엔드투엔드 데이터 리니지 명세 및 영향도 맵 | 스튜디오 `Stage 5. Lineage & Eval` 리니지 뷰 및 `mcp_stage5_lineage_and_eval` (`lineage_records`) |
| `D5.2` | PII 마스킹 및 접근 제어 거버넌스 정책 | `tb_customer_contract`의 고객 식별자(`CUST_DEMO_001`~`006`) 비식별 코드 사용 |
| `D5.3` | Golden CQ 검증 리포트 | `data/output/cq_benchmark_report.json` (5/5 통과, 100.0%) |
| `D5.4` | 경계값·일관성 벤치마크 리포트 | `data/output/boundary_benchmark_results.json` (10건 × 5회 = 50회 실측) |
| `D5.5` | 프로덕션 배포 패키지 (Dockerfile · Terraform IaC) | `Dockerfile`, `terraform/` (`main.tf`, `bigquery.tf`, `storage.tf`, `iam.tf`, `cloud_run.tf`) |

## 게이트 (Gate 5 — 최종 배포 승인)

- [ ] Golden CQ 5건 검증 통과율 100.0% (`cq_benchmark_report.json`).
- [ ] 경계값 10건 × 5회 벤치마크에서 `INSUFFICIENT_PARAMETERS` 및 `MATCH_NOT_FOUND` 가드레일이 정상 작동하고 결과가 `boundary_benchmark_results.json`에 기록됨.
- [ ] 저장소 내 시크릿(`AIza...`), 고객사 고유 식별자, 로컬 절대 경로(`/<local-home>/`) 0건 확인.
- [ ] `terraform apply` 통과 및 Cloud Run 헬스체크(`/api/portal/profile`) 정상 응답 확인.

## 스튜디오에서 보기

[Stage 5. Lineage & Eval 탭 열기](https://agentic-ontology-starter-lwrlf7yogq-du.a.run.app/?tab=stage5)

## 노트북

[stage5_lineage_and_evaluation_ko.ipynb](../../notebooks/ko/stage5_lineage_and_evaluation_ko.ipynb) · [English Notebook](../../notebooks/en/stage5_lineage_and_evaluation_en.ipynb)

## 내 데이터에 적용하기

1. `data/input/04_cq/golden_competency_questions.json`에 도메인 핵심 질문과 `expected_math`, `verification_sql`, `grounded_chunk`를 등록한다.
2. `data/input/04_cq/boundary_cases.json`에 파라미터 누락(`INSUFFICIENT_PARAMETERS`), 미존재 엔티티(`MATCH_NOT_FOUND`), 정상 복합 질의(`GROUNDED`) 케이스를 정의한다.
3. `python3 pipeline/validator.py`를 실행해 두 리포트를 갱신한다.
