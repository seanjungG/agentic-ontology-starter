# Stage 5. 리니지·평가·배포 게이트

> 스튜디오 [`Stage 5. Lineage & Eval`](https://agentic-ontology-starter-924723860007.asia-northeast3.run.app/?tab=stage5) · MCP `mcp_stage5_lineage_and_eval` · 노트북 [stage5_lineage_and_evaluation_ko.ipynb](../notebooks/stage5_lineage_and_evaluation_ko.ipynb) · [English](./05_stage5_lineage_and_eval_en.md) · [전체 방법론](./METHODOLOGY_KO.md)

## 목적

원천 자산(CSV·가이드 문서)부터 BigQuery 테이블, Property Graph(`STARTER_ONTOLOGY_GRAPH`), MCP 도구(8종), 에이전트까지 이어지는 4계층 데이터 리니지를 확인하고, Golden CQ 5건과 경계값 질의 10건(×5회 반복)을 통과했는지 검증해 배포 여부를 판정한다.

## 입력

- BigQuery 테이블 10개 및 `STARTER_ONTOLOGY_GRAPH`
- Golden CQ 평가셋: `data/input/04_eval/sample_cq_eval.json` (5건: `CQ_001`~`CQ_005`)
- 경계값 평가셋: `data/input/04_eval/boundary_eval_10.json` (10건: `BND_001`~`BND_010`)
- 평가 실행 모듈: `src/eval/boundary_eval.py` (`run_validation`, `run_boundary_benchmark`)

## 이 Stage의 MCP: `mcp_stage5_lineage_and_eval`

| Step | 실제 수행 (`src/agent/mcp_server.py`) |
| :--- | :--- |
| `build_4tier_lineage` | 원천 파일 → BigQuery 테이블(10개) → `STARTER_ONTOLOGY_GRAPH` → MCP(8종)·에이전트 4계층 리니지 요약과 테이블 행수를 조회한다 |
| `run_golden_cq_suite` | `data/output/validation_report.json`의 Golden CQ 5건 검증 결과(`overall_accuracy`, `results`)를 읽거나 실시간 요약을 반환한다 |
| `diagnose_boundary_failures` | `data/output/boundary_eval_report.json`의 경계값 10건×5회 결과(`overall_pass_rate`, `consistency_rate`, `intent_stability_rate`, 실패 케이스)를 반환한다 |

## 절차 (`src/eval/boundary_eval.py`)

1. **4계층 데이터 리니지 구성**:
   - Tier 1 (Raw Assets): `sample_policy_guide.md`, `sample_welfare_exemption_guide.md`, CSV 6종
   - Tier 2 (BigQuery DW & Chunks): `tb_devices`, `tb_plans`, `tb_subsidies`, `tb_customer_contracts`, `tb_domain_rules`, `tb_doc_chunks` + 엣지 테이블 4종
   - Tier 3 (Semantic & Property Graph): `ontology.jsonld`, `STARTER_ONTOLOGY_GRAPH` (6 노드 / 4 엣지)
   - Tier 4 (MCP & Agent): Stage MCP 5종 + Runtime MCP 3종 → `AiFdeAgentEngine` (`gemini-3.8-flash`)
2. **Golden CQ 5건 결정론적 검증 (`run_validation`)**:
   - `CQ_001`~`CQ_005` 각각에 대해 BigQuery 원장·규칙·청크 앵커가 존재하는지 검증하고 `data/output/validation_report.json`을 생성한다.
3. **경계값 10건 × 5회 라이브 벤치마크 (`run_boundary_benchmark`)**:
   - 정상 근거 질의(`GROUNDED`), 조건 미일치(`MATCH_NOT_FOUND`), 필수 파라미터 누락(`INSUFFICIENT_PARAMETERS`)이 섞인 10개 질문을 각 5회(총 50회) 실행한다.
   - 통과율(`overall_pass_rate`), 문항 내 일관성(`consistency_rate`), 의도 안정성(`intent_stability_rate`)을 측정해 `data/output/boundary_eval_report.json`에 기록한다.
4. **반복 개선 (Hill-Climbing)**:
   - 실패한 문항이 있으면 원인(위키 청크 누락, 규칙 산식 조건 누락, MCP 파라미터 검증 미비)을 수정하고 파이프라인과 평가를 재실행한다.

## 산출물

| ID | 산출물 | 스타터에서 |
| :--- | :--- | :--- |
| `D5.1` | 5-Stage 엔드투엔드 데이터 리니지 명세 및 영향도 맵 | 스튜디오 `Stage 5. Lineage & Eval` 리니지 뷰 및 `mcp_stage5_lineage_and_eval` (`build_4tier_lineage`) |
| `D5.2` | PII 마스킹 및 접근 제어 거버넌스 정책 | `tb_customer_contracts`의 고객 식별자(`CUST_DEMO_001`~`005`) 비식별 코드 사용 |
| `D5.3` | Golden CQ 검증 리포트 | `data/output/validation_report.json` (5/5 통과, 100.0%) |
| `D5.4` | 경계값·일관성 벤치마크 및 Hill-Climbing 리포트 | `data/output/boundary_eval_report.json` (10건 × 5회 = 50회 실측) |
| `D5.5` | 프로덕션 배포 패키지 (Dockerfile · Terraform IaC) | `Dockerfile`, `terraform/` (`main.tf`, `bigquery.tf`, `storage.tf`, `iam.tf`, `cloud_run.tf`) |

## 게이트 (Gate 5 — 최종 배포 승인)

- [ ] Golden CQ 5건 검증 통과율 100.0% (`validation_report.json`).
- [ ] 경계값 10건 × 5회 벤치마크에서 `INSUFFICIENT_PARAMETERS` 및 `MATCH_NOT_FOUND` 가드레일이 정상 작동하고 결과가 `boundary_eval_report.json`에 기록됨.
- [ ] 저장소 내 시크릿(`AIza...`), 고객사 고유 식별자, 로컬 절대 경로(`/<local-home>/`) 0건 확인.
- [ ] `terraform validate` 통과 및 Cloud Run 헬스체크(`/api/status`) 정상 응답 확인.

## 스튜디오에서 보기

[Stage 5. Lineage & Eval 탭 열기](https://agentic-ontology-starter-924723860007.asia-northeast3.run.app/?tab=stage5)

- 상단: 4계층 리니지 흐름도와 Stage 5 MCP(`build_4tier_lineage`, `run_golden_cq_suite`, `diagnose_boundary_failures`) 실행 버튼.
- 하단 좌측: Golden CQ 5건 검증 결과 표.
- 하단 우측: 경계값 10건 × 5회 반복 평가 요약(통과율·일관성·의도 안정성) 및 문항별 상세 결과.

## 노트북

[stage5_lineage_and_evaluation_ko.ipynb](../notebooks/stage5_lineage_and_evaluation_ko.ipynb)

## 내 데이터에 적용하기

1. `data/input/04_eval/sample_cq_eval.json`에 도메인 핵심 질문과 기대 규칙·테이블을 등록한다.
2. `data/input/04_eval/boundary_eval_10.json`에 파라미터 누락(`INSUFFICIENT_PARAMETERS`), 미존재 엔티티(`MATCH_NOT_FOUND`), 정상 복합 질의(`GROUNDED`) 케이스를 정의한다.
3. `python3 -m src.eval.boundary_eval`을 실행해 리포트를 갱신한다.
