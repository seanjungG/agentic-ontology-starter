# AI Coding Agent Bootstrap Guide (`GEMINI.md` / `AGENTS.md`)

> **Jetski / Antigravity / Cursor / Claude Code 에이전트 필수 지침**:
> 이 저장소(`agentic-ontology-starter`)를 클론하거나 다른 프로젝트 폴더로 가져와 새로운 도메인 프로토타입을 구축할 때, **에이전트가 임의로 디렉터리 구조를 뒤집거나 Mock DB·다크 테마 UI를 새로 만드는 것을 방지**하기 위한 최상위 부트스트랩 규칙입니다. 코드 작성 전 반드시 [`01_prod.md`](01_prod.md), [`PROTOTYPING_PLAYBOOK.md`](PROTOTYPING_PLAYBOOK.md), [`DESIGN.md`](DESIGN.md)를 먼저 읽으십시오.

---

## 1. 절대 준수 원칙 (Golden Rules for AI Agents)

1. **기존 5-Stage 파이프라인 & 6-Tab 스튜디오 골격 유지 (No Arbitrary Rewrites)**:
   - 이 스타터팩은 이미 완성된 엔드투엔드 참조 아키텍처(`pipeline/ingest.py` → `pipeline/graph_builder.py` → `src/agent/mcp_server.py` → `src/agent/reasoning_engine.py` → `pipeline/validator.py` → `src/web/studio_server.py`)를 갖추고 있습니다.
   - 사용자가 "우리 도메인(제조/금융/리테일/병원/인사 등)에 맞게 프로토타이핑해줘"라고 요청하면, **기존 프레임워크와 6-Tab 웹 스튜디오를 허물고 새로 짜지 마십시오.** 반드시 [`PROTOTYPING_PLAYBOOK.md`](PROTOTYPING_PLAYBOOK.md)의 **5-File Domain Swap 절차**에 따라 데이터·규칙·그래프 DDL·프로필만 교체하십시오.
2. **실데이터 무환각 원칙 (Zero Mock SQLite / No Fake Output)**:
   - 샘플 SQLite나 하드코딩된 가짜 JSON 응답으로 실제 BigQuery/GCS/Vertex AI가 동작하는 것처럼 모사하는 행위를 엄격히 금지합니다.
   - 모든 데이터 적재와 GQL/SQL 질의는 `src/gcp_client.py`를 통해 실제 BigQuery(`BQ_DATASET_ID`), GCS(`GCS_BUCKET_NAME`), Vertex AI(`gemini-3.8-flash`)를 대상으로 실행하고 실측 결과를 보고하십시오.
3. **모델 임의 다운그레이드 및 시크릿 하드코딩 금지**:
   - 기본 서빙 모델은 `VERTEX_GEMINI_MODEL="gemini-3.8-flash"`입니다. 권한/인증 오류 발생 시 임의로 하위 모델로 바꾸거나 우회하지 말고 사용자에게 `gcloud auth application-default login` 또는 IAM 권한 부여를 안내하십시오.
   - 소스 코드, 설정 파일, 노트북 어디에도 API 키(Google API Key), 토큰(OAuth Access Token), 로컬 절대 경로(로컬 사용자 홈 경로)를 하드코딩하지 마십시오.
4. **디자인 시스템(`DESIGN.md`) 100% 일관성 유지**:
   - 웹 스튜디오(`src/web/studio_server.py`) 수정 시 Apple/Google Enterprise 라이트 테마(`#f5f5f7` 배경, Pretendard 폰트, 44px 글로벌 탑바, 52px 6-Tab 서브바, `#0284c7` 시맨틱 허브 노드)를 유지하십시오. 다크 테마나 장식용 이모지 남발은 금지합니다.
5. **Terraform(IaC) 및 2단계 Git 브랜치 배포 원칙**:
   - GCP 리소스 생성·수정은 `terraform/` 선언적 구성을 기본으로 합니다.
   - GitHub 푸시 시 `main` 브랜치에 직접 커밋하지 말고, 작업 브랜치(`feat/...` 또는 `proto/...`)에 먼저 커밋·푸시한 뒤 `main`으로 `--no-ff` 머지하여 푸시하십시오.
6. **고객·데이터 영역별 프로젝트 분리 (Multi-Project)**:
   - 새 고객 데이터나 별도 데이터 영역은 루트 샘플을 덮어쓰지 말고 `python3 new_project.py <id> --name "<이름>"`으로 `projects/<id>/`를 만들어 그 안에 둡니다. 스튜디오 상단 `PROJECT` 선택기에 자동 표시됩니다.
   - 스키마가 샘플과 다르면 공용 파일을 프로젝트 폴더에 복사해 수정하고 `project.json`의 `mcp_module`·`engine_module`·`ingest_module`·`graph_module`·`validator_module`로 지정합니다. 공용 서버·파이프라인 코드에 프로젝트별 `if` 분기를 추가하지 않습니다.
   - Stage 5 리니지는 프로젝트의 `config/lineage_spec.json`에 실제 자산만 적습니다. 볼륨은 `bq_table` 실측값을 쓰고 추정치를 적지 않습니다.

---

## 2. 신규 도메인 프로토타이핑 5단계 표준 절차 (5-Step Domain Swap)

사용자가 새로운 비즈니스 도메인이나 데이터를 제시하면, 에이전트는 다음 순서로 프로토타이핑을 수행합니다. (상세 시나리오 A~D는 [`PROTOTYPING_PLAYBOOK.md`](PROTOTYPING_PLAYBOOK.md) 참조)

### Step 0. 시나리오(Track) 판별 및 작업 대시보드(`00_dashboard.md`) 생성
- 사용자의 데이터 구성을 보고 4대 시나리오 중 하나를 선택합니다:
  - **Scenario A (문서만 있음)** → `config/starter_config.json`의 `"active_track": "lite"` (`Stage 1 → 2 → 4`)
  - **Scenario B (DW 테이블 + 정책 문서)** → `"active_track": "standard"`, `"graph_engine": "bigquery"` (`Stage 1 → 2 → 3 → 4`)
  - **Scenario C (실시간 운영 그래프 DDL 필요)** → `"active_track": "standard"` + `create_spanner_graph.sql`
  - **Scenario D (리니지 + 50회 경계값 평가 + 배포 게이트)** → `"active_track": "full"` (`Stage 1 → 2 → 3 → 4 → 5`)
- `industry_cases/` 폴더에 유사 산업군 참조 템플릿(제조·금융·리테일·통신 8종)이 있으므로, 가장 가까운 템플릿을 참고하여 스키마와 규칙을 설계합니다.

### Step 1. 입력 데이터 배치 (`data/input/`)
- 신규 고객·데이터 영역이면 아래 경로 앞에 `projects/<id>/`를 붙입니다 (Golden Rule 6).
- `data/input/01_guides/`: 도메인 정책·업무 매뉴얼 마크다운 파일 배치
- `data/input/03_tables/`: 정형 마스터·트랜잭션 CSV 배치 (Track 1 Lite에서는 생략 가능)
- `data/input/04_cq/`: `golden_cqs.json`(핵심 검증 질의 5건) 및 `boundary_cases.json`(모호·정보부족·카탈로그 외 경계 케이스 10건) 작성
- `data/input/05_glossary/business_glossary.json`: 도메인 표준 용어 및 동의어 사전 정의

### Step 2. 인제스트 및 3-Layer 위키 컴파일 수정 (`pipeline/ingest.py`)
- `DOMAIN_RULES` 배열과 `compile_3layer_wiki()`를 새 도메인의 엔티티·개념·비즈니스 규칙에 맞게 업데이트합니다.
- `python3 pipeline/ingest.py`를 실행하여 `data/llm_wiki/*.md`, `tb_doc_chunks`(SHA-256 해시 포함), `tb_domain_rules`, 정형 테이블·엣지 테이블을 BigQuery와 GCS에 실제 적재합니다.

### Step 3. Property Graph DDL 갱신 (`pipeline/graph_builder.py`)
- (Track 2/3인 경우) 새 노드 테이블과 엣지 테이블을 묶는 `CREATE OR REPLACE PROPERTY GRAPH` DDL을 갱신하고 `python3 pipeline/graph_builder.py`로 BigQuery에 그래프를 생성합니다.

### Step 4. 런타임 MCP 도구 3종 및 에이전트 슬롯 연결 (`src/agent/mcp_server.py`, `src/agent/reasoning_engine.py`)
- Stage MCP 5종(`mcp_stage1_asset_discovery` ~ `mcp_stage5_lineage_and_eval`)의 함수 시그니처는 그대로 유지합니다.
- Runtime MCP 3종(`mcp_lookup_customer_profile`, `mcp_calculate_penalty_rule`, `mcp_query_graph_and_wiki` 또는 도메인 대응 도구 3종)의 내부 SQL/GQL 및 규칙 수식을 새 도메인 테이블에 맞게 수정합니다.
- `src/agent/reasoning_engine.py`의 카탈로그 엔티티 슬롯 추출 로직이 새 도메인의 마스터 테이블을 읽도록 맞춥니다.

### Step 5. 스튜디오 프로필(`config/portal_profile.json`) 및 검증(`pipeline/validator.py`) 실행
- `config/portal_profile.json`의 프로젝트 타이틀, Stage 1~5 설명, 샘플 질의 버튼을 새 도메인 내용으로 교체합니다.
- `python3 pipeline/validator.py`로 Golden CQ 5건 및 경계값 평가를 실행하고, `python3 -m src.web.studio_server 8080`으로 6-Tab 스튜디오를 구동하여 검증합니다.

---

## 3. 작업 상태 추적 및 블로커 관리 (`00_dashboard.md` & `backlog.md`)

- 복합 작업이나 `/goal` 수행 시 루트에 `00_dashboard.md`를 생성하여 **단계별 플랜(WP1~WPn), 진행 상태, 실제 실행한 명령어·검증 결과, 수정한 파일 링크**를 투명하게 기록하십시오.
- GCP 인증 만료, 데이터셋/버킷 권한(HTTP 403), 쿼터 부족 등 **사용자의 사전 조치가 필요한 블로커**가 발생하면 임의로 Mock 처리를 하지 말고 즉시 `backlog.md`에 원인과 해결 명령어를 기록한 뒤 사용자에게 안내하십시오.
- 모든 보고서와 문서는 과장된 수식어('완벽한', '무결점', '무손실' 등)를 배제하고 실제 측정된 행 수, 통과 건수, GQL/SQL 실행 결과만을 담백하게 서술하십시오.
