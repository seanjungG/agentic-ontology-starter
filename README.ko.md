# Agentic Ontology Starter (한국어)

**[🇺🇸 English README](README.md)** · **[🇰🇷 한국어](README.ko.md)** · **[✨ 3종 라이브 데모 쇼케이스 ↗](https://agentic-ontology-starter-notebook-dasz7pvvua-du.a.run.app/showcase)**

> **이 스튜디오 + 이 깃헙만 있으면** 내 데이터 · 내 GCP로 엔터프라이즈 온톨로지 에이전트(**OKF 위키** · **Spanner Graph**(기본 Semantic Graph) · **Wiki/Graph/Hybrid 에이전트** · **CQ 평가** · **4-Layer Context Graph 폐루프**)를 만들고, 같은 결과를 다시 만드는 **CLI · MCP 호출 파라미터 · 단일 파일 에이전트 · 코드 번들**로 가져가는 스타터 팩입니다.
>
> 방법론의 핵심 노하우(스코핑 · CQ 초안 · 위키 컴파일 + W1~W9 게이트 · 그래프 설계 · 에이전트 추론 · 채점 · Context Graph)는 무상태 **Platform Core MCP 도구(`aos_core_*`, `v1.12.0` 57종)** 안에만 있고, 이 공개 저장소는 그 도구를 **어떤 순서로 · 어떤 파라미터로** 부르는지를 담습니다. 서버는 외부 패키지 없이 Python 3.11 표준 라이브러리만 씁니다.

> **스타터팩의 역할 — "쉽게 시작하고 직접 경험하는 것"**
> 설치 없이 완성된 **100/100** 워크스페이스를 1클릭으로 열어 보고 → 로그인 없이 **게스트로 3-Lab 노트북**을 끝까지 실행해 원리를 익힌 뒤 → **내 데이터 · 내 GCP**로 만들어 코드로 가져가세요.

---

## 30초 만에 시작하고 직접 경험하기 (Zero Setup)

모든 웹 화면은 **영문(English)이 기본값**이며, 상단 바의 **`EN | KO`** 토글로 즉시 한국어로 전환할 수 있습니다.

| 구분 | 바로가기 | 무엇을 경험하나 |
| :--- | :--- | :--- |
| ✨ **3종 데모 쇼케이스 허브** | [`/showcase` ↗](https://agentic-ontology-starter-notebook-dasz7pvvua-du.a.run.app/showcase) | Accelerate '27 핵심 3종 자산(인터랙티브 노트북 랩 · LG U+ 운영 스튜디오 · 공개 스타터 깃헙)을 한눈에 연결하는 통합 랜딩 허브 |
| 📓 **노트북 Lab 1 · 온톨로지** (약 10분) | [`#ov` 전체 도식 ↗](https://agentic-ontology-starter-notebook-dasz7pvvua-du.a.run.app/#ov) | **게스트 즉시 체험**(Google 로그인 선택): `#n1` CQ → `#n2` OKF 위키 + 커버리지 보완 → `#n3` 그래프 설계 · Spanner 적재 · GQL 확인 → `#n4` Knowledge Catalog · GQL Agent → `#n5` Wiki vs GQL Agent 평가 |
| 📓 **노트북 Lab 2 · 워크플로우** (약 6분) | [`#w0` 전체 도식 ↗](https://agentic-ontology-starter-notebook-dasz7pvvua-du.a.run.app/#w0) | `#w1` 룰 · 워크플로우 추출 → `#w2` Spanner Graph 확장 → `#w3` Workflow Agent 대화 → `#w4` 평가 → `#w5` 변경 요청 · 어드민 승인 · 반영 · 전/후 비교 · 원복 |
| 📓 **노트북 Lab 3 · Context Graph** (약 6분) | [`#c0` 전체 도식 ↗](https://agentic-ontology-starter-notebook-dasz7pvvua-du.a.run.app/#c0) | `#c1` BigQuery Graph 준비 → `#c2` 답변 기록 → `#c3` GQL 감사 → `#c4` 👍/👎 · 정정 → 암묵지 후보 → `#c5` 승인 · KC 반영 · 재질의 → `#c6` 루프 대시보드 · KG 스냅샷 · 적재 데이터 탐색 |
| 🏛️ **스타터 스튜디오 (`v6.14.0`)** | [스타터 스튜디오 열기 ↗](https://agentic-ontology-starter-dasz7pvvua-du.a.run.app/) | `⓪ 이해` 전체 흐름 → **샘플로 바로 체험**(데모 신원 · 샘플 팩) → 내 데이터로 구축 → CLI · 코드 번들 인계 |
| ⚡ **완성 100/100 워크스페이스** | [3-에이전트 질의 · 피드백 ↗](https://agentic-ontology-starter-dasz7pvvua-du.a.run.app/?bucket=seanjung-agentic-starter-ontology&ws=ws-20261105-5525c8#/studio/agents) · [Context Graph 시연 ↗](https://agentic-ontology-starter-dasz7pvvua-du.a.run.app/?bucket=seanjung-agentic-starter-ontology&ws=ws-20261105-5525c8#/studio/cg) | 구축 대기 0초 · 평가 **100점** 워크스페이스 `ws-20261105-5525c8`에서 3-에이전트 질의와 1클릭 Context Graph 폐루프 시연 |
| 🏢 **운영 도메인 스튜디오 (LG U+)** | [LG U+ 스튜디오 열기 ↗](https://agentic-ontology-studio-lguplus-lwrlf7yogq-du.a.run.app/) | 13개 탭 통합 엔터프라이즈 온톨로지 레퍼런스 플랫폼 (통신 지원금 도메인, 영문 기본 + `EN | KO` 전환) |
| 🧭 **레퍼런스 마법사** | [`/wizard` ↗](https://agentic-ontology-starter-dasz7pvvua-du.a.run.app/wizard#step-1) | 큐레이션된 6단계 샘플 결과(Flow A/B/C, 기준 100점) — 비교용 |
| 🔌 **Platform Core MCP (`v1.12.0`)** | `https://aos-builder-core-mcp-dasz7pvvua-du.a.run.app/mcp` | **도구 57종** = 빌드 10 + 데이터 플레인 28 + 코어 · 인테이크 12 + Drive 2 + **Context Graph 5** (`aos_core_cg_*`) · JSON-RPC `tools/list` · `tools/call` |

> **노트북 랩 세션 정책**: 로그인 없이 **게스트로 바로 시작**하거나 Google 계정(선택)으로 로그인할 수 있습니다. 세션마다 전용 GCS 버킷 · Spanner DB가 자동 생성되고 미사용 3시간 뒤 자동 정리됩니다. 사이드바 **▶ Run all**로 Lab을 끝까지 실행할 수 있으며, PC가 잠들거나 새로고침돼도 완료된 셀은 건너뛰고 이어서 실행합니다.

---

### 시작 → 경험 → 적용 (Onboarding Journey)

| 단계 | 시간 | 하는 일 | 바로가기 |
| :---: | :---: | :--- | :--- |
| **① 시작** | 1분 | 설치 · 빌드 없이 완성 워크스페이스에서 3-에이전트 질의 → 문장 피드백 → Context Graph 반영을 바로 경험 | [에이전트](https://agentic-ontology-starter-dasz7pvvua-du.a.run.app/?bucket=seanjung-agentic-starter-ontology&ws=ws-20261105-5525c8#/studio/agents) · [Context Graph](https://agentic-ontology-starter-dasz7pvvua-du.a.run.app/?bucket=seanjung-agentic-starter-ontology&ws=ws-20261105-5525c8#/studio/cg) |
| **② 경험** | Lab당 6~10분 | 노트북 Lab 1 · 2 · 3을 셀 단위 또는 **▶ Run all**로 실행하며 OKF 위키 · Spanner Graph · Workflow Agent · Context Graph의 작동 원리를 체득 | [Lab 1](https://agentic-ontology-starter-notebook-dasz7pvvua-du.a.run.app/#ov) · [Lab 2](https://agentic-ontology-starter-notebook-dasz7pvvua-du.a.run.app/#w0) · [Lab 3](https://agentic-ontology-starter-notebook-dasz7pvvua-du.a.run.app/#c0) |
| **③ 적용** | 구축 6~10분 | 노트북에서 익힌 같은 단계를 스튜디오에서 내 문서 · 테이블(PDF · DOCX · CSV · BigQuery)로 구축하고 CLI · 단일 파일 에이전트(`aos_agent_standalone.py`) · MCP 번들로 이식 | [스튜디오](https://agentic-ontology-starter-dasz7pvvua-du.a.run.app/) · [§4 빠른 시작](#4-빠른-시작) · [§6 인계 번들](#6-코드--mcp-인계-번들) |

#### ③ 적용 맵 — 노트북 셀 · 스튜디오 화면 · Core MCP 도구 · 결과물

| 단계 | 노트북에서 경험 | 스튜디오에서 적용 | Core MCP | 내 GCP 결과물 |
| :--- | :--- | :--- | :--- | :--- |
| **질문 정의 (CQ)** | Lab 1 `#n1` CQ 만들기 · 평가 세트 확정 | 구축 `S2` CQ · 평가 탭에서 CQ 편집 | `aos_core_draft_cqs` | `gs://<버킷>/aos/<ws>/cqs.json` |
| **OKF 위키** | Lab 1 `#n2` 파싱 · 위키 컴파일 · 커버리지 보완 · Wiki Agent | 구축 `S3` 위키 · 위키 탭(보기 · 편집 · 게이트 W1~W9) | `aos_builder_parse_documents_gate0` · `aos_core_compile_wiki` | `gs://<버킷>/aos/<ws>/wiki/` |
| **Semantic Graph** | Lab 1 `#n3` 설계 → DDL → Spanner 적재 → GQL 확인 | 구축 `S4` 그래프 · 그래프 탭(스키마 · 노드/엣지 할당 · GQL 콘솔) | `aos_core_design_graph` · `spanner_update_ddl` · `spanner_commit` | **Spanner Graph**(기본) · BigQuery 스테이징 테이블 |
| **에이전트 · 평가** | Lab 1 `#n4` KC · GQL Agent · `#n5` 두 에이전트 평가 | 구축 `S5` 평가 · 에이전트 탭(Wiki · Graph · Hybrid) | `aos_core_agent_step` · `aos_core_judge` | `gs://<버킷>/aos/<ws>/runs/` · 평가 점수 |
| **워크플로우 · 승인 변경** | Lab 2 `#w1`~`#w5` 룰 · 워크플로우 · Workflow Agent · 변경 승인 | 노트북에서 먼저 경험 (스튜디오 로드맵) | 노트북 세션 Spanner Graph | 세션 Spanner DB (`T_ChangeRequest` · `T_ChangeAudit`) |
| **Context Graph 루프** | Lab 3 `#c1`~`#c6` 기록 · 감사 · 피드백 · 승인 · 재질의 | Context Graph 탭 · 답변마다 문장 피드백 · SME 승인 · ChangeSet | `aos_core_cg_parse_feedback` · `submit_feedback` · `feedback_flow` · `review_candidate` · `changeset` | `gs://<버킷>/aos/<ws>/context_graph/graph.json` |

#### 노트북을 운영하며 정리한 5가지 원칙

1. **Semantic Graph 기본 엔진은 Spanner Graph**, **BigQuery Property Graph**는 Lab 3 Context Graph(감사 · 액션 리니지) 엔진으로 동작하며 선택 옵션으로도 사용할 수 있습니다(새 프로젝트에서 BigQuery Graph 사용 시 Enterprise 예약 필요).
2. **정책 수치는 위키 한 곳에만(`G2-W1`)** 두고 그래프 · 룰 · 에이전트는 그 단일 출처를 참조합니다.
3. **리소스가 지워지면 그 위에 만든 결과도 무효**입니다. 선행 단계는 버킷 · DB · 데이터셋의 실제 존재 여부를 확인한 뒤 실행합니다.
4. **데이터 변경 · 지식 반영은 사람 승인 후에만** 적용하고 전/후 비교와 원복 기록을 남깁니다(Lab 2 `#w5`, Lab 3 `#c5`, 스튜디오 SME 게이트).
5. **긴 실행은 끊겨도 이어지게** — 게스트 즉시 진입(선택 로그인) · 진행 상태 저장 · 미사용 리소스 자동 정리(노트북 세션 3시간, 스튜디오 데모 신원 7일).

디자인 시스템 참고: [`DESIGN.md`](DESIGN.md)

---

## 1. 스튜디오 흐름 — 5단계 구성 + 스튜디오 + 배포 · 인계

- `⓪ 이해` → `① 플로우 · 서비스` → `② GCP · 권한` → `③ 데이터(업로드 · GCS · Google Drive · BigQuery · 샘플, PDF/Office → Markdown 변환 + 변환율 측정)` → `④ 문서 유형 판별` → `⑤ 구축(S0~S5)` → **스튜디오**(개요 · 자산 · 위키 · 그래프 · 검색 · 에이전트 · 평가 · Context Graph) → **배포 준비도 점검** → **코드 · MCP 인계 번들** · **어드민 포털(`/admin`, Google SSO 허용 계정 전용)**.
- **4-Layer Context Graph**: 모든 에이전트 답변 아래 문장 피드백 바 → 결정적 파서(`src/aos/sentence_feedback.py`)가 극성 · 암묵지 유형(`T1~T5`, `KC_META`) · 엔티티 · 회귀 CQ로 구조화 → SME 승인 → `ChangeSet` + `CG-n` 회귀 CQ 등록 → `CG-RULES` 1-Hop 컨텍스트로 재질의(Before vs After).

---

## 2. 3개 층 보안 및 경계 모델

- **Zero-Privilege Core MCP**: 런타임 서비스 계정에는 데이터 IAM 권한이 0개이며, 모든 GCP 및 Vertex AI 호출은 호출자의 OAuth 토큰(`X-AOS-Access-Token`) 권한으로만 실행됩니다.
- **신원 모드**: 데모(`runtime`, `STARTER_WRITE_PROJECTS` 한정 · 7일 자동 만료) · 내 토큰(`token`, 브라우저 탭 전용 · 서버 비저장) · SA 위임(`impersonate`, `STARTER_IMPERSONATE_ALLOW` 허용 목록).
- **통합 어드민 포털 (`/admin`)**: 설정 완료 전까지 Fail-Closed. 운영 환경은 **Google Sign-In(RS256 ID 토큰 검증 + `STARTER_ADMIN_EMAILS` 허용 목록 + 12시간 슬라이딩 `HttpOnly` 쿠키)** 으로 Core MCP 57종 카탈로그 · BigQuery 계정별 미터링(PII 최소화) · 실시간 링버퍼 사용량을 제공합니다.

---

## 3. 노트북 — 라이브 인터랙티브 랩 + 오프라인 참고 12종

- **추천 시작점(라이브)**: [인터랙티브 3-Lab 노트북 랩 ↗](https://agentic-ontology-starter-notebook-dasz7pvvua-du.a.run.app/#ov) — 설치 없이 게스트로 즉시 실행.
- **코드 수준 오프라인 참고**: [`notebooks/`](notebooks/README.md)에 Stage 0~5 정적 `.ipynb` 12종(한국어 `ko/` 6종 · 영어 `en/` 6종)이 함께 포함되어 있습니다.

---

## 4. 빠른 시작

### 4.1 공개 스튜디오
0. **가장 빠른 길**: [완성 100/100 워크스페이스 바로 열기 ↗](https://agentic-ontology-starter-dasz7pvvua-du.a.run.app/?bucket=seanjung-agentic-starter-ontology&ws=ws-20261105-5525c8#/studio/overview)
1. [스튜디오 ↗](https://agentic-ontology-starter-dasz7pvvua-du.a.run.app/) → **샘플로 바로 체험** → **전체 실행**
2. 내 데이터: **내 데이터로 시작** → 플로우 · 목적 → 신원/토큰 · 버킷 → **환경 점검** → 데이터 추가 → **S0~S5 구축** → **코드 · MCP 인계**

### 4.2 로컬 실행
```bash
git clone https://github.com/seanjungG/agentic-ontology-starter.git && cd agentic-ontology-starter
gcloud auth login
cp .env.example .env   # GCP_PROJECT_ID · GCS_WIKI_BUCKET · STARTER_WRITE_PROJECTS · CORE_MCP_URL
set -a && source .env && set +a
python3 -m src.web.studio_server        # http://localhost:8080 (영문 기본 · EN | KO 전환)
```

### 4.3 CLI
```bash
python3 -m src.cli check --project MY_PROJECT --bucket MY_BUCKET --region asia-northeast3
python3 -m src.cli new --spec spec.json [--impersonate aos-starter@MY_PROJECT.iam.gserviceaccount.com]
python3 -m src.cli build --bucket MY_BUCKET --ws ws-... [--stages ingest,cqs,wiki,graph,eval]
python3 -m src.cli ask   --bucket MY_BUCKET --ws ws-... --agent hybrid "질문"
python3 -m src.cli eval  --bucket MY_BUCKET --ws ws-...
python3 -m src.cli calls --bucket MY_BUCKET --ws ws-... --stage graph
python3 -m src.cli purge-spanner --project MY_PROJECT --dry-run
```

### 4.4 내 Cloud Run 배포
```bash
gcloud run deploy agentic-ontology-starter --source . --region asia-northeast3 \
  --service-account aos-starter@MY_PROJECT.iam.gserviceaccount.com --timeout 600 \
  --set-env-vars GCP_PROJECT_ID=MY_PROJECT,BQ_LOCATION=asia-northeast3,GCS_WIKI_BUCKET=MY_BUCKET,STARTER_WRITE_PROJECTS=MY_PROJECT,CORE_MCP_URL=https://aos-builder-core-mcp-dasz7pvvua-du.a.run.app/mcp
```

---

## 5. 워크스페이스 & 그래프 엔진

- GCS `gs://<버킷>/aos/<ws_id>/` (원본 · 파싱 · CQ · 위키 · 그래프 설계 · `context_graph/graph.json` · 평가 · `mcp_calls.jsonl`), BigQuery 스테이징(`aos_<ws>`), **Spanner Graph**(`starter_graph_db`, 기본 엔진 · 데모 신원 7일 자동 정리).

---

## 6. 코드 · MCP 인계 번들

`workspace.json` · `.env` · `setup_gcp.sh` · `run_build.sh` · `ask.sh` · `mcp_calls.jsonl` · `mcp_config.gemini-cli.json` · `aos_agent_standalone.py`(저장소 없이 Core MCP만으로 질의하는 단일 파일 에이전트)를 zip으로 내려받습니다.

---

## 7. 오프라인 검증 테스트

```bash
python3 -m pip install pytest && python3 -m pytest tests -q
```

GCP 호출이 없는 100% 오프라인 테스트(영문 기본값 · KO/EN 동등성 · 워크스페이스 · Context Graph · Spanner Graph · 어드민 Google SSO RS256 검증 · 레퍼런스 마법사)를 실행합니다.

---

## 라이선스

방법론 · 문서: **CC BY-NC-ND 4.0** · 소스 코드: **PolyForm Noncommercial License 1.0.0** — [`LICENSE`](LICENSE) 참고. 상업적 이용 시 사전 서면 허가가 필요합니다.
