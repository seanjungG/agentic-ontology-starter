# Claude Code Bootstrap Instructions (`CLAUDE.md`)

이 저장소(`agentic-ontology-starter`)에서 작업을 수행하기 전에 반드시 다음 기준 문서를 먼저 읽고 준수하십시오:

1. [`01_prod.md`](01_prod.md) — 마스터 제품·아키텍처 헌장 (6대 불변 아키텍처 원칙 및 5-File Swap 구조)
2. [`PROTOTYPING_PLAYBOOK.md`](PROTOTYPING_PLAYBOOK.md) — 4대 상황별(Scenario A~D) 빠른 프로토타이핑 레시피 및 단계별 실행 절차
3. [`GEMINI.md`](GEMINI.md) — AI 코딩 에이전트 공통 가드레일 (Antigravity / Cursor / Claude Code 공통)
4. [`DESIGN.md`](DESIGN.md) — Apple/Google Enterprise 라이트 테마 UI 디자인 표준

## 핵심 준수 사항

- **코어 엔진 재작성 금지**: `src/web/studio_server.py`(6-Tab 스튜디오), `src/agent/mcp_server.py`(8종 MCP), `src/agent/reasoning_engine.py`(2-Pass Gemini 에이전트), `pipeline/ingest.py` · `graph_builder.py` · `validator.py` 구조를 임의로 다른 프레임워크나 다크 테마 UI로 재작성하지 마십시오.
- **실데이터 무환각 원칙**: Mock SQLite나 가짜 하드코딩 응답을 생성하지 말고 `src/gcp_client.py`를 통해 실제 BigQuery(`BQ_DATASET_ID`), GCS(`GCS_BUCKET_NAME`), Vertex AI(`VERTEX_GEMINI_MODEL="gemini-3.8-flash"`)를 호출하십시오.
- **5-File Swap 도메인 이식**: 새로운 도메인 데이터를 인입하고 온톨로지를 구축할 때는 `PROTOTYPING_PLAYBOOK.md`에 정의된 5개 지점(`config/starter_config.json`, `data/input/*`, `pipeline/ingest.py`, `pipeline/graph_builder.py`, `src/agent/mcp_server.py` + `config/portal_profile.json`)만 교체하여 빠르게 프로토타이핑하십시오.
- **고객·데이터 영역별 프로젝트**: 새 고객 데이터는 루트 샘플을 덮어쓰지 말고 `python3 new_project.py <id>`로 만든 `projects/<id>/`에 둡니다. 도메인 코드 차이는 `project.json`의 `*_module` 오버라이드로 처리하고 공용 코드에 프로젝트별 분기를 넣지 않습니다 ([`projects/_template/README.md`](projects/_template/README.md)).
- **작업 추적 및 블로커 기록**: 진행 상황은 `00_dashboard.md`에 기록하고, GCP 권한/인증 이슈 등 사용자 조치가 필요한 사항은 임의 우회하지 말고 `backlog.md`에 기록한 뒤 안내하십시오.
