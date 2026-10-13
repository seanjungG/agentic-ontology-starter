# Custom Ontology Project Workspace Template

이 디렉터리는 `new_project.py` 또는 스타터 포털의 **`+ 신규 프로젝트`** 모달을 통해 생성되는 도메인별 격리 워크스페이스 템플릿입니다.

| 경로 | 역할 및 산출물 |
| :--- | :--- |
| `project.json` | 프로젝트 식별자, 선택 트랙(`lite` / `hybrid` / `full`), 그래프 엔진(`bigquery` / `spanner` / `both`), 연결 GCP 리소스 설정 |
| `data/input/01_raw`, `03_tables`, `04_cq` | 도메인 원천 정책 문서(`.md`/`.txt`/`.pdf`), 정형 CSV 마스터 테이블, 도메인 Golden CQ 정의 |
| `data/llm_wiki`, `data/output` | 3-Layer OKF 위키(`summary.md`, `entities.md`, `concepts.md`, `rules.md`), 비즈니스 규칙(`business_rules.json`), 비즈니스 워크플로(`business_workflows.json`, `W1~W3` 및 `Gate G2-W`), Property Graph DDL 및 Golden CQ 검증 리포트 |
