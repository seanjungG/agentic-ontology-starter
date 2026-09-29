# 웹 UI 디자인 표준 (`DESIGN.md`)

- **적용 대상**: `src/web/studio_server.py` (6-Tab Agentic Ontology Studio) 및 노트북/리포트 시각화 자산
- **핵심 원칙**: Apple/Google Enterprise 단일 **라이트 테마(Light Mode Only)**를 사용합니다. 다크 테마(`[data-theme="dark"]`), 네온 컬러, 임의의 프론트엔드 프레임워크 교체, 장식용 이모지 남발을 금지합니다.

---

## 1. 레이아웃 및 네비게이션 규격

| 구성 요소 | 규격 | 구현 기준 (`src/web/studio_server.py`) |
| :--- | :--- | :--- |
| **글로벌 탑바 (Global Topbar)** | 높이 `44px`, 반투명 글래스(`rgba(255,255,255,0.88)`), `backdrop-filter: saturate(180%) blur(20px)`, 하단 `1px` 헤어라인 보더 | 좌측: Google `G` SVG 로고 + `Agentic Ontology Studio` 타이틀 + `PROJECT` 선택기(`projects/<id>`, `?project=`) + 도메인 배지<br>우측: 산업군 쇼케이스 셀렉터, Track 배지, `KOR / ENG` 언어 토글 |
| **로컬 서브바 (Stage Sub-Navigation)** | 높이 `52px`, 가운데 정렬 Pill 세그먼트 바 | **6개 탭 고정**: `0. Overview` · `Stage 1. Asset` · `Stage 2. Wiki & Semantic Graph` · `Stage 3. Property Graph` · `Stage 4. Agent & MCP` · `Stage 5. Lineage & Eval` |
| **본문 워크스페이스** | 최대 폭 `1440px`, 좌우 패딩 `24px`, 카드 그리드 간격 `16px` | 좌측 목록/그래프 캔버스(60%) + 우측 상세 인스펙터/실행 패널(40%) 스플릿 구조 |
| **단일 포트 원칙** | 단일 HTTP 서버 포트(`8080`) | 탭 전환이나 서브 뷰를 위해 별도 포트(`8081`, `3000` 등)를 열지 않음 |

---

## 2. 컬러 토큰 및 타이포그래피

```css
:root {
  --font-sans: "Pretendard Variable", "Pretendard", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  --font-mono: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Monaco, Consolas, monospace;

  /* Surfaces (Light Enterprise Only) */
  --bg-primary: #ffffff;
  --bg-secondary: #f5f5f7;
  --bg-tertiary: #e8e8ed;
  --bg-glass: rgba(255, 255, 255, 0.88);

  /* Typography */
  --text-primary: #1d1d1f;
  --text-secondary: #6e6e73;
  --text-tertiary: #86868b;

  /* Semantic Accents & Graph Node Palette */
  --accent-blue: #0071e3;       /* Primary Action / Device Node */
  --hub-sky-blue: #0284c7;      /* Central Semantic Hub Node (SubsidyRule / Core Policy) */
  --node-indigo: #4f46e5;       /* Plan / Tier Node */
  --node-amber: #d97706;        /* DomainRule / Penalty Node */
  --node-emerald: #059669;      /* DocChunk / Grounding Node */
  --node-purple: #7c3aed;       /* CustomerContract / Transaction Node */

  /* Status Colors */
  --status-pass: #16a34a;       /* GROUNDED / PASS */
  --status-warn: #d97706;       /* INSUFFICIENT_PARAMETERS / WARN */
  --status-fail: #dc2626;       /* MATCH_NOT_FOUND / FAIL */

  /* Borders & Radii */
  --border-subtle: rgba(0, 0, 0, 0.08);
  --border-default: rgba(0, 0, 0, 0.14);
  --radius-sm: 10px;
  --radius-md: 16px;
  --radius-pill: 980px;
}
```

---

## 3. 그래프 시각화 및 정보성 텍스트 태그 표준

1. **그래프 노드·엣지 표현 규칙 (`Stage 2`, `Stage 3`, `Stage 5`)**:
   - 중심 허브 노드(`SubsidyRule` 또는 도메인 핵심 중재 엔티티)는 스카이 블루(`#0284c7`)로 강조합니다.
   - 엣지 선 두께는 `1.2px ~ 1.6px`의 가는 실선/점선으로 유지하여 라벨 겹침을 방지합니다.
   - 한/영 전환(`KOR` / `ENG`) 시 노드 캡션과 엣지 라벨이 즉시 해당 언어로 전환되어야 합니다.
   - `Stage 5` 리니지 DAG 카드는 `[CONN]` `[RAW]` `[ETL]` `[PII]` `[SEM]` `[MCP]` `[AGENT]` 카테고리 태그(`config/lineage_spec.json`의 `tag`)와 색 띠를 쓰고, BigQuery 실측 행 수 배지만 초록으로 구분합니다.
2. **장식용 이모지 배제 및 정보성 텍스트 태그 사용**:
   - 카드 제목이나 목록 앞에 불필요한 장식 이모지를 넣지 않고, 자산의 출처와 성격을 나타내는 대괄호 텍스트 태그를 사용합니다:
     - `[문서:가이드]` (비정형 정책·업무 매뉴얼)
     - `[DB:마스터]` (정형 기준 정보 테이블)
     - `[DB:트랜잭션]` (정형 가입·거래 원장 테이블)
     - `[위키:OKF]` (3-Layer 컴파일 위키 문서)
     - `[평가:CQ]` (Golden Competency Question 및 경계값 케이스)

---

## 4. UI 수정 체크리스트 (AI 코딩 에이전트 필독)

- [ ] 배경색이 `#f5f5f7` / `#ffffff` 기반 라이트 테마인가? (어두운 `#0f172a`, `#1e1e2e` 배경 사용 금지)
- [ ] 상단 44px 글로벌 탑바와 52px 6-Tab 서브바 구조가 그대로 유지되었는가?
- [ ] 도메인 문구 변경 시 `src/web/studio_server.py`에 텍스트를 직접 하드코딩하지 않고 `config/portal_profile.json`을 통해 주입했는가?
- [ ] `KOR / ENG` 토글 클릭 시 새로 추가한 UI 문구도 누락 없이 한/영 전환되는가?
