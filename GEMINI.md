# AI Coding Agent Bootstrap Guide (`GEMINI.md` / `AGENTS.md`)

> **Jetski / Antigravity / Cursor / Claude Code 에이전트 필수 지침**:
> 이 저장소(`agentic-ontology-starter`)는 특정 고객사의 프로덕션 비즈니스·데이터를 담고 있지 않은 **교육용 · 테스트용 · 신규 프로젝트 부트스트랩용 심플 레퍼런스 레포지토리**입니다. 새로 유입될 외부 고객 비즈니스와 데이터 형태(문서만 있는 경우, 일부 테이블만 있는 경우, 전혀 다른 산업군 스키마가 들어오는 경우 등)가 완전히 예측 불가능한 상황에서도 **에이전트가 임의로 디렉터리 구조를 뒤집거나 가짜 데이터·Mock DB·다크 테마 UI를 새로 만드는 것을 방지하고 유연하게 적응**하기 위한 최상위 부트스트랩 규칙입니다. 코드 작성 전 반드시 [`01_prod.md`](01_prod.md), [`PROTOTYPING_PLAYBOOK.md`](PROTOTYPING_PLAYBOOK.md), [`DESIGN.md`](DESIGN.md)를 먼저 읽으십시오.

---

## 1. 절대 준수 원칙 (Golden Rules for AI Agents)

1. **기존 5-Stage 파이프라인 & 6-Tab 스튜디오 골격 유지 (No Arbitrary Rewrites)**:
   - 이 스타터팩은 이미 완성된 엔드투엔드 참조 아키텍처(`pipeline/extract_docs.py` → `pipeline/ingest.py` → `pipeline/extract_wiki.py` → `pipeline/graph_builder.py` → `src/agent/mcp_server.py` → `src/agent/reasoning_engine.py` → `pipeline/validator.py` → `src/web/studio_server.py`)를 갖추고 있습니다.
   - 사용자가 "우리 도메인(제조/금융/리테일/병원/인사 등)에 맞게 프로토타이핑해줘"라고 요청하면, **기존 프레임워크와 6-Tab 웹 스튜디오를 허물고 새로 짜지 마십시오.** 반드시 [`PROTOTYPING_PLAYBOOK.md`](PROTOTYPING_PLAYBOOK.md)의 시나리오(Scenario A / A2 / B / C / D) 및 **5-File Domain Swap 절차**에 따라 `projects/<id>/` 안에서 데이터·규칙·그래프 DDL·프로필만 교체하십시오.
2. **실데이터 무환각 원칙 (Zero Mock SQLite / No Fake Output)**:
   - 샘플 SQLite나 하드코딩된 가짜 JSON 응답으로 실제 BigQuery/GCS/Vertex AI가 동작하는 것처럼 모사하는 행위를 엄격히 금지합니다.
   - 모든 데이터 적재와 GQL/SQL 질의는 `src/gcp_client.py`를 통해 실제 BigQuery(`BQ_DATASET_ID`), GCS(`GCS_BUCKET_NAME`), Vertex AI(`gemini-3.8-flash`)를 대상으로 실행하고 실측 결과를 보고하십시오.
   - 적재하는 데이터는 고객 자료 또는 그 파생 데이터여야 합니다. 지어낸 데이터를 실제 BigQuery에 넣는 것도 위반입니다(아래 고객 데이터 원칙).
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

## 고객 데이터 원칙

정의
- 고객 자료(`CUSTOMER_PROVIDED`): `customer_doc/`의 원본 파일과 고객이 준 테이블
- 파생 데이터(`EXTRACTED`): 고객 자료에서 코드로 추출한 텍스트·청크·행 (출처 연결 필수)
- 합성 데이터(`SYNTHETIC_DEMO`): 위 둘이 아닌 모든 데이터

규칙 (게이트·검사 코드가 함께 강제합니다)
1. 고객 문서는 `pipeline/extract_docs.py`(`run_pipeline.py`가 먼저 실행)로 원문 그대로 변환한다 (`<!-- provenance: source_file=... sha256=... -->`, `<!-- page: N -->` 자동 삽입). 요약하거나 다시 쓴 글을 `data/input/01_guides/`에 넣지 않는다. 요약은 Stage 2 위키에서만 만들고 출처 청크를 표시한다.
2. 청크 경계는 코드가 정한다(조문 `제N조` 또는 제목·문단 기준 최대 1,500자). `DOC_CHUNK` 주석을 직접 넣지 않는다.
3. Gate 0(문서별 글자 비율·12자 조각 일치 95% 이상, 텍스트 있는 쪽 100% 포함, 누락 조문 0)이 실패하면 다음 단계로 가지 않고 `data/output/gate0_report.json`의 문서별 비율과 누락 쪽을 보고한다.
4. 고객 자료에 없는 테이블·행·엔티티(제품, 고객, 거래, 사례, 광고 문구 등)를 만들지 않는다. 요청(그래프, SQL 평가 등)에 테이블이 필요한데 없으면 멈추고 묻는다: (a) 고객에게 테이블 요청 (b) 문서 기반 물리 그래프(미구현, 별도 요청) (c) 합성 데모 데이터(사용자 승인 시 `project.json` `synthetic.allowed: true`, 행마다 `provenance=SYNTHETIC_DEMO`).
5. 요청 범위 밖 산출물(데이터, 테이블, 평가 수치, 화면용 데이터셋)을 만들지 않는다. 화면 작업에 데이터가 필요하면 먼저 묻는다.
6. 평가 수치는 `pipeline/validator.py` 실행 결과(`run_id`, `input_manifest_sha256` 포함)만 쓴다. 리포트·요약 파일을 손으로 쓰거나 고치지 않는다. 실행하지 못했으면 "미측정"으로 둔다.
7. 실데이터 원칙은 실제 인프라를 쓰는 것과 함께, 적재하는 데이터가 고객 자료 또는 그 파생 데이터여야 한다는 뜻이다. 지어낸 데이터를 실제 BigQuery·Spanner에 넣는 것도 위반이다.
8. 최종 보고에 "데이터 출처 요약"을 넣는다: 문서별 원문 비율과 청크 수, provenance별 행 수, CQ 근거 유형(sql/citation), 평가 근거 중 합성 데이터 여부, 사람이 확정하지 않은 정답 수.
9. 모델명·토큰·비용·행 수 같은 수치는 실측값만 쓴다. 예시 문구를 복사하지 않는다.

---

## 2. 신규 도메인 프로토타이핑 5단계 표준 절차 (5-Step Domain Swap)

사용자가 새로운 비즈니스 도메인이나 데이터를 제시하면, 에이전트는 다음 순서로 프로토타이핑을 수행합니다. (상세 시나리오 A~D는 [`PROTOTYPING_PLAYBOOK.md`](PROTOTYPING_PLAYBOOK.md) 참조)

### Step 0. 시나리오(Track) 판별 및 작업 대시보드(`00_dashboard.md`) 생성
- 트랙은 프로젝트 `project.json`의 `track`으로 정합니다. 기본값 `auto`는 `tables`에 등록된 CSV가 있으면 `standard`, 없으면 `lite`로 정하고 이유를 `input_manifest.json`에 남깁니다.
  - **Scenario A (문서만 있음)** → `lite` (추출 → Gate 0 → 청크·문서 기반 위키 적재 → citation CQ 평가)
  - **Scenario A2 (문서만 있는데 그래프·SQL 평가 요청)** → 멈추고 묻습니다: (a) 고객에게 테이블 요청 (b) 문서 기반 물리 그래프(미구현, 별도 요청) (c) 합성 데모 데이터(승인 필요)
  - **Scenario B (고객이 준 테이블 + 정책 문서)** → `standard`, `config/starter_config.json`의 `"graph_engine": "bigquery"` (`Stage 1 → 2 → 3 → 4`)
  - **Scenario C (실시간 운영 그래프 DDL 필요)** → `standard` + `create_spanner_graph.sql`
  - **Scenario D (리니지 + 50회 경계값 평가 + 배포 게이트)** → `full` (`Stage 1 → 2 → 3 → 4 → 5`)
- `industry_cases/`의 참조 템플릿(제조·금융·리테일·통신 8종)은 스키마와 규칙 구조 참고용입니다. 데이터를 복사하면 `SYNTHETIC_DEMO` 표시와 사용자 승인이 필요합니다.

### Step 1. 입력 데이터 배치 (`data/input/`)
- 신규 고객·데이터 영역이면 아래 경로 앞에 `projects/<id>/`를 붙입니다 (Golden Rule 6).
- `customer_doc/`: 고객 원본 문서(PDF·DOCX·MD·TXT)를 그대로 둡니다. `python3 run_pipeline.py --project <id>`가 `pipeline/extract_docs.py`로 `data/input/01_guides/`에 원문 변환본을 만듭니다. `01_guides/`에 직접 쓴 파일을 넣지 않습니다.
- `data/input/03_tables/`: 고객이 준 CSV만 둡니다. `project.json`의 `tables`에 등록하고 행마다 `provenance`·`source_ref`를 채웁니다. 없으면 비워 두고 `lite`로 진행합니다.
- `data/input/04_cq/`: `golden_cqs.json`(핵심 검증 질의 5건) 및 `boundary_cases.json`(모호·정보부족·카탈로그 외 경계 케이스 10건) 작성
- `data/input/05_glossary/business_glossary.json`: 도메인 표준 용어 및 동의어 사전 정의

### Step 2. 인제스트 및 3-Layer 위키 컴파일 수정 (`pipeline/ingest.py`)
- `DOMAIN_RULES`는 원문 조항을 인용해 `source_chunk_id`·인용문과 함께 정의합니다. `lite`에서는 `pipeline/extract_wiki.py`가 청크에서 entity(node)·concept(edge)를 뽑고, 인용이 청크에 없는 항목은 제외합니다.
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
- 다음 경우에는 멈추고 묻습니다: 입력과 요청이 맞지 않을 때(문서만 있는데 그래프 요청 등), 합성 데이터가 필요할 때, 요청 범위 밖 데이터가 필요할 때.
- 최종 보고에는 "데이터 출처 요약"(고객 데이터 원칙 8)을 넣습니다.
