# Agent Instructions (`AGENTS.md`)

이 문서는 **Jetski / Antigravity / Cursor / Claude Code** 등 모든 AI 코딩 에이전트가 이 저장소(`agentic-ontology-starter`)를 열었을 때 준수해야 하는 부트스트랩 지침입니다. 이 저장소는 특정 고객사 프로덕션 코드베이스가 아닌 **교육용 · 테스트용 · 신규 프로젝트 부트스트랩용 심플 레퍼런스 레포지토리**로서, 예측 불가능한 외부 고객 비즈니스와 데이터 형태(문서 전용, 일부 테이블 제공, 커스텀 스키마 유입 등)에 유연하게 적응하도록 설계되었습니다.

- **최상위 제품·아키텍처 헌장**: [`01_prod.md`](01_prod.md)
- **상세 에이전트 규칙**: [`GEMINI.md`](GEMINI.md)
- **상황별 빠른 프로토타이핑 플레이북**: [`PROTOTYPING_PLAYBOOK.md`](PROTOTYPING_PLAYBOOK.md)
- **웹 UI 디자인 시스템 표준**: [`DESIGN.md`](DESIGN.md)

## 핵심 요약 (Quick Checklist)

1. **임의 재작성 금지**: `src/web/studio_server.py`(6-Tab 스튜디오), `src/agent/mcp_server.py`(8종 MCP), `src/agent/reasoning_engine.py`(2-Pass MCP 및 Lite 청크 인용 에이전트), `pipeline/extract_docs.py` · `ingest.py` · `extract_wiki.py` · `graph_builder.py` · `validator.py`의 파이프라인 골격을 허물고 다른 프레임워크로 새로 짜지 마십시오.
2. **시나리오별 유연한 프로토타이핑 및 5축 그래프 엔진 선택**: 새로운 도메인 적용 요청 시 [`PROTOTYPING_PLAYBOOK.md`](PROTOTYPING_PLAYBOOK.md)의 **Scenario A(문서 전용 Lite) / A2(문서 전용 상태에서 그래프 요청 시 멈춤·선택지 안내) / B(DW+문서 BigQuery Property Graph 기본) / C(5축 체크리스트 기반 Cloud Spanner Graph 선택 또는 `both` 모드 `EXTERNAL_QUERY` Graph Fabric 연동) / D(Full-Stack 평가·배포)** 중 하나를 선택하십시오. 별도 지정이 없으면 `"graph_engine": "bigquery"`가 기본값입니다.
3. **실데이터 원칙**: Mock SQLite나 가짜 하드코딩 응답을 만들지 말고 `src/gcp_client.py`로 실제 BigQuery·GCS·Vertex AI(`gemini-3.8-flash`)를 호출하십시오. 적재하는 데이터는 고객 자료 또는 그 파생 데이터여야 합니다(아래 고객 데이터 원칙).
4. **라이트 테마 UI 유지**: `DESIGN.md`에 정의된 Apple/Google Enterprise 라이트 테마(`#f5f5f7` 배경, Pretendard 폰트, 44px 글로벌 탑바, 52px 6-Tab 서브바, `#0284c7` 시맨틱 허브 노드)를 100% 유지하십시오.
5. **보안 및 배포**: API 키(Google API Key)나 로컬 절대 경로(로컬 사용자 홈 경로)를 절대 커밋하지 마십시오. GitHub 배포 시 작업 브랜치(`feat/...`) 푸시 후 `main --no-ff` 머지 절차를 따르십시오.
6. **고객·데이터 영역별 프로젝트**: 새 고객 데이터는 `python3 new_project.py <id>`로 만든 `projects/<id>/`에 두고 루트 샘플을 덮어쓰지 마십시오. 도메인 코드 차이는 `project.json`의 `*_module` 오버라이드로 처리합니다 ([`projects/_template/README.md`](projects/_template/README.md)).

## 고객 데이터 원칙

정의
- 고객 자료: `customer_doc/`의 원본 파일과 고객이 준 테이블
- 파생 데이터: 고객 자료에서 코드로 추출한 텍스트·청크·행 (출처 연결 필수)
- 합성 데이터: 위 둘이 아닌 모든 데이터

규칙 (게이트·검사 코드가 함께 강제합니다)
1. 고객 문서는 `pipeline/extract_docs.py`(`run_pipeline.py`가 먼저 실행)로 원문 그대로 변환한다. 요약하거나 다시 쓴 글을 `data/input/01_guides/`에 넣지 않는다. 요약은 Stage 2 위키에서만 만들고 출처 청크를 표시한다.
2. 청크 경계는 코드가 정한다. `DOC_CHUNK` 주석을 직접 넣지 않는다.
3. Gate 0(문서별 글자 비율·12자 조각 일치 95% 이상, 텍스트 있는 쪽 100% 포함, 누락 조문 0)이 실패하면 다음 단계로 가지 않고 `data/output/gate0_report.json`의 문서별 비율과 누락 쪽을 보고한다.
4. 고객 자료에 없는 테이블·행·엔티티(제품, 고객, 거래, 사례, 광고 문구 등)를 만들지 않는다. 요청(그래프, SQL 평가 등)에 테이블이 필요한데 없으면 멈추고 묻는다: (a) 고객에게 테이블 요청 (b) 문서 기반 물리 그래프(미구현, 별도 요청) (c) 합성 데모 데이터(사용자 승인 시 `project.json` `synthetic.allowed: true`, 행마다 `provenance=SYNTHETIC_DEMO`).
5. 요청 범위 밖 산출물(데이터, 테이블, 평가 수치, 화면용 데이터셋)을 만들지 않는다. 화면 작업에 데이터가 필요하면 먼저 묻는다.
6. 평가 수치는 `pipeline/validator.py` 실행 결과만 쓴다. 리포트·요약 파일을 손으로 쓰거나 고치지 않는다. 실행하지 못했으면 "미측정"으로 둔다.
7. 실데이터 원칙은 실제 인프라를 쓰는 것과 함께, 적재하는 데이터가 고객 자료 또는 그 파생 데이터여야 한다는 뜻이다. 지어낸 데이터를 실제 BigQuery·Spanner에 넣는 것도 위반이다.
8. 최종 보고에 "데이터 출처 요약"을 넣는다: 문서별 원문 비율과 청크 수, provenance별 행 수, CQ 근거 유형(sql/citation), 평가 근거 중 합성 데이터 여부, 사람이 확정하지 않은 정답 수.
9. 모델명·토큰·비용·행 수 같은 수치는 실측값만 쓴다. 예시 문구를 복사하지 않는다.
