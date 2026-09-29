# Claude Code Bootstrap Instructions (`CLAUDE.md`)

이 저장소(`agentic-ontology-starter`)에서 작업을 수행하기 전에 반드시 다음 기준 문서를 먼저 읽고 준수하십시오:

1. [`01_prod.md`](01_prod.md) — 마스터 제품·아키텍처 헌장 (6대 불변 아키텍처 원칙 및 5-File Swap 구조)
2. [`PROTOTYPING_PLAYBOOK.md`](PROTOTYPING_PLAYBOOK.md) — 4대 상황별(Scenario A~D) 빠른 프로토타이핑 레시피 및 단계별 실행 절차
3. [`GEMINI.md`](GEMINI.md) — AI 코딩 에이전트 공통 가드레일 (Antigravity / Cursor / Claude Code 공통)
4. [`DESIGN.md`](DESIGN.md) — Apple/Google Enterprise 라이트 테마 UI 디자인 표준

## 핵심 준수 사항

- **코어 엔진 재작성 금지**: `src/web/studio_server.py`(6-Tab 스튜디오), `src/agent/mcp_server.py`(8종 MCP), `src/agent/reasoning_engine.py`(2-Pass Gemini 에이전트), `pipeline/ingest.py` · `graph_builder.py` · `validator.py` 구조를 임의로 다른 프레임워크나 다크 테마 UI로 재작성하지 마십시오.
- **실데이터 무환각 원칙**: Mock SQLite나 가짜 하드코딩 응답을 생성하지 말고 `src/gcp_client.py`를 통해 실제 BigQuery(`BQ_DATASET_ID`), GCS(`GCS_BUCKET_NAME`), Vertex AI(`VERTEX_GEMINI_MODEL="gemini-3.8-flash"`)를 호출하십시오. 적재하는 데이터는 고객 자료 또는 그 파생 데이터여야 합니다(아래 고객 데이터 원칙).
- **5-File Swap 도메인 이식**: 새로운 도메인 데이터를 인입하고 온톨로지를 구축할 때는 `PROTOTYPING_PLAYBOOK.md`에 정의된 5개 지점(`config/starter_config.json`, `data/input/*`, `pipeline/ingest.py`, `pipeline/graph_builder.py`, `src/agent/mcp_server.py` + `config/portal_profile.json`)만 교체하여 빠르게 프로토타이핑하십시오.
- **고객·데이터 영역별 프로젝트**: 새 고객 데이터는 루트 샘플을 덮어쓰지 말고 `python3 new_project.py <id>`로 만든 `projects/<id>/`에 둡니다. 도메인 코드 차이는 `project.json`의 `*_module` 오버라이드로 처리하고 공용 코드에 프로젝트별 분기를 넣지 않습니다 ([`projects/_template/README.md`](projects/_template/README.md)).
- **작업 추적 및 블로커 기록**: 진행 상황은 `00_dashboard.md`에 기록하고, GCP 권한/인증 이슈 등 사용자 조치가 필요한 사항은 임의 우회하지 말고 `backlog.md`에 기록한 뒤 안내하십시오.

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
