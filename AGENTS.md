# Agent Instructions (`AGENTS.md`)

이 문서는 **Jetski / Antigravity / Cursor / Claude Code** 등 모든 AI 코딩 에이전트가 이 저장소를 열었을 때 준수해야 하는 부트스트랩 지침입니다.

- **최상위 제품·아키텍처 헌장**: [`01_prod.md`](01_prod.md)
- **상세 에이전트 규칙**: [`GEMINI.md`](GEMINI.md)
- **4대 시나리오별 빠른 프로토타이핑 플레이북**: [`PROTOTYPING_PLAYBOOK.md`](PROTOTYPING_PLAYBOOK.md)
- **웹 UI 디자인 시스템 표준**: [`DESIGN.md`](DESIGN.md)

## 핵심 요약 (Quick Checklist)

1. **임의 재작성 금지**: `src/web/studio_server.py`(6-Tab 스튜디오), `src/agent/mcp_server.py`(8종 MCP), `src/agent/reasoning_engine.py`(2-Pass Gemini 에이전트), `pipeline/ingest.py` · `graph_builder.py` · `validator.py`의 파이프라인 골격을 허물고 다른 프레임워크로 새로 짜지 마십시오.
2. **4대 시나리오 & 5-File Swap 프로토타이핑**: 새로운 도메인 적용 요청 시 [`PROTOTYPING_PLAYBOOK.md`](PROTOTYPING_PLAYBOOK.md)의 **Scenario A(문서 전용 Lite) / B(DW+문서 BigQuery Graph) / C(Spanner Graph DDL) / D(Full-Stack 평가·배포)** 중 하나를 선택하고 지정된 5개 영역(`data/input/`, `config/starter_config.json`, `pipeline/ingest.py`+`graph_builder.py`, `src/agent/mcp_server.py`, `config/portal_profile.json`)만 교체하십시오.
3. **실데이터 원칙**: Mock SQLite나 가짜 하드코딩 응답을 만들지 말고 `src/gcp_client.py`로 실제 BigQuery·GCS·Vertex AI(`gemini-3.8-flash`)를 호출하십시오.
4. **라이트 테마 UI 유지**: `DESIGN.md`에 정의된 Apple/Google Enterprise 라이트 테마(`#f5f5f7` 배경, Pretendard 폰트, 44px 글로벌 탑바, 52px 6-Tab 서브바, `#0284c7` 시맨틱 허브 노드)를 100% 유지하십시오.
5. **보안 및 배포**: API 키(Google API Key)나 로컬 절대 경로(로컬 사용자 홈 경로)를 절대 커밋하지 마십시오. GitHub 배포 시 작업 브랜치(`feat/...`) 푸시 후 `main --no-ff` 머지 절차를 따르십시오.
6. **고객·데이터 영역별 프로젝트**: 새 고객 데이터는 `python3 new_project.py <id>`로 만든 `projects/<id>/`에 두고 루트 샘플을 덮어쓰지 마십시오. 도메인 코드 차이는 `project.json`의 `*_module` 오버라이드로 처리합니다 ([`projects/_template/README.md`](projects/_template/README.md)).
