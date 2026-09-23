# Enterprise Agentic Ontology - 4대 산업군 8대 엔터프라이즈 케이스 템플릿 패키지

> **라이브 포털**: 설치 없이 [Agentic Ontology Studio 포털](https://agentic-ontology-starter-924723860007.asia-northeast3.run.app)에서 `0. Overview` ~ `8. AI FDE` 전 구간 화면을 바로 확인할 수 있습니다.

본 디렉토리(`industry_cases/`)는 특정 산업이나 단일 기업에 종속되지 않고, **국내 대표 4대 핵심 산업군(스마트 제조, 핀테크/금융, 유통/물류, 통신/미디어)의 대표 8대 기업 실무 요건**을 추상화하여 즉시 현장 프로젝트에 이식할 수 있도록 설계된 엔터프라이즈 온톨로지 템플릿 패키지입니다.

기획자, 데이터 엔지니어, AI 개발자가 고객사 현장에 투입되었을 때, **비정형 업무 규정/SOP 문서**와 **정형 DW(BigQuery) 원장 데이터**를 어떻게 융합하고, **BigQuery Property Graph(SQL:2023)**와 **Tier 3 Domain MCP 도구**로 캡슐화하여 **0% 환각 AI 에이전트**를 완성하는지 구체적인 청사진과 즉시 구동 가능한 템플릿을 제공합니다.

---

## 1. 4대 산업군 8대 고객사 선정 배경 및 요건 현황

고객사의 실제 프로젝트 진행 현황 및 국내 산업별 대표성을 바탕으로 총 4개 세그먼트, 세그먼트당 2개 엔터프라이즈를 선정하여 수록하였습니다.

| 산업군 (Segment) | 엔터프라이즈 고객사 | 진행 상태 | 핵심 도메인 및 해결 과제 (Core Business Problem) | 하이브리드 온톨로지 융합 자산 |
| :--- | :--- | :---: | :--- | :--- |
| **1. 스마트 제조<br>(Manufacturing)** | **포스코 (POSCO)** | `고객 요건 진행 중` | • 제철 연속 공정 품질 불량 인과 추적<br>• 설비 예방보전(PdM) 진동/온도 이상 감지<br>• 안전보건 작업허가서(SOP) 및 긴급 Interlock 지침 | • 실시간 설비 텔레메트리 DW 원장<br>• 압연/제강 공정 품질 판정 매뉴얼<br>• 설비 안전 보전 SOP 비정형 문서 |
| | **현대자동차<br>(Hyundai Motor)** | `고객 요건 진행 중` | • 완성차/SDV 전장 부품 복합 BOM 단종/호환성<br>• 글로벌 공급망(SCM) 1/2차 협력사 리드타임 지연<br>• 설계 변경(ECN) 및 리콜 규제 대응 *(HD현대 비교 수록)* | • E-BOM / M-BOM 마스터 원장<br>• 부품 협력사 출하/납기 현황 DW<br>• 자동차 안전기준 및 설계변경 지침 |
| **2. 핀테크 & 뱅킹<br>(Finance)** | **카카오뱅크<br>(KakaoBank)** | `고객 요건 진행 중` | • 모바일 비대면 여신 심사 및 대출 한도 산정<br>• 금융소비자보호법(금소법) 설명의무 100% 준수<br>• 금융위 DSR 40% 산정 및 생애최초 LTV 특례 판정 | • 고객 신용평점 및 기존 부채 DW<br>• 대출 상품별 가산금리/한도 원장<br>• 은행업 감독규정 및 여신업무 세칙 |
| | **토스<br>(TOSS)** | `추천 요건` | • 원앱(One-App) 멀티 금융 상품 비교/중개<br>• 마이데이터 기반 개인화 지출/보험 보장 진단<br>• 토스페이 가맹점 정산 수수료율 매트릭스 산정 | • 제휴 금융사 대출/카드 상품 원장<br>• 마이데이터 자산/결제 이력 DW<br>• 전자금융거래 기본약관 및 제휴 계약서 |
| **3. 유통 & 물류<br>(Retail & Commerce)** | **GS리테일<br>(GS Retail)** | `고객 요건 진행 중` | • 편의점(GS25)/슈퍼(GS THE FRESH) 가맹 상생 정산<br>• 옴니채널 퀵커머스 실시간 매장 재고 밸런싱<br>• 신선식품 유통기한 임박 상품 폐기 지원금 계산 | • POS 판매 실적 및 매장별 재고 DW<br>• 본부-가맹점 수익 배분 원장<br>• 가맹계약서(상생지원 특약) 규정 |
| | **CJ대한통운 / 올리브영<br>(CJ Logistics / OliveYoung)** | `고객 요건 진행 중` | • 옴니채널 풀필먼트 물류 배송 SLA 지연 보상<br>• 입점 뷰티/헬스 브랜드 판매 수수료 및 프로모션 분담금<br>• 당일배송(오늘드림) 권역 라우팅 패널티 판정 | • 풀필먼트 입출고/배송 타임스탬프 DW<br>• 브랜드별 입점 정산 계약 마스터<br>• 택배 표준약관 및 물류 SLA 가이드 |
| **4. 통신 & 미디어<br>(Telecommunications)** | **SK텔레콤<br>(SK Telecom)** | `추천 요건` | • 구독형 AI/라이프 서비스(T우주) 복합 결합 상품<br>• 패밀리 멤버십/회선 결합 할인 중복 배제 규칙<br>• 5G/LTE 약정 기간 내 요금제 변경 위약금 산정 | • 요금제 기본료 및 단말 출고가 DW<br>• 공시지원금/선택약정 이력 원장<br>• T우주 이용약관 및 식스플랜 정책서 |
| | **KT<br>(KT Corporation)** | `추천 요건` | • 유무선 복합 결합(인터넷+모바일+IPTV) 해지 방어<br>• 엔터프라이즈 B2B 전용회선/IDC SLA 품질 장애 배상<br>• 결합 약정 할인 반환금 일할 계산 공식 검증 | • 가입 회선 상태 및 번들 결합 DW<br>• 기업 전용회선 SLA 회선 모니터링 원장<br>• KT 결합서비스 이용약관 및 SLA 규정 |

---

## 2. 크로스 인더스트리 공통 아키텍처 패턴 (`Agentic Ontology Studio` `0. Overview` ~ `8. AI FDE` 연계)

모든 8개 엔터프라이즈 케이스는 Google Cloud의 **GCP Native First** 원칙과 **`Agentic Ontology Studio` 8단계 진화 라이프사이클(`1. Asset` ~ `8. AI FDE`)**에 따라 동일한 계층 아키텍처를 공유합니다:

```
[Tab 1: 1. Asset (Unstructured SOP & Structured DW)]
  PDF / Markdown 업무 규정, 계약서, 공정 매뉴얼 + BigQuery DW 원장 테이블
          │
          ▼ (Clean YAML Frontmatter + Karpathy 3-Layer LLM-Wiki on GCS)
[Tab 2 & 3: 2. OKF Layer & 3. Ontology Semantic]
  담백한 원본 YAML Frontmatter (.okf.md) + 5대 온톨로지 요소 & 시맨틱 브릿지
          │
          ├──► [Tab 4: 4. Wiki Agent (선행 GCS 위키 에이전트)]
          │      물리 그래프 구축 전 GCS .okf.md 위키만으로 규정/산식/예외 질의 1차 즉시 해결
          │
          ▼ (Domain Pruning 35➔7 & Zero-ETL Node Promotion)
[Tab 5: 5. Bigquery Graph (SQL:2023 Property Graph)]
  정형 DW 마스터 원장 테이블 (Node) ──[APPLIES_TO / CALCULATES]──> 비정형 룰 (Node)
          │
          ▼ (NL2GQL Multi-Hop Traversal + Wiki Hybrid)
[Tab 6: 6. BQG Agent (BigQuery Graph 에이전트)]
  GRAPH_TABLE() 실시간 멀티홉 원장 탐색 + 규정 결합으로 20/20 골든 CQ 전수 해결
          │
          ▼ (Async In-Memory Cache < 5ms & 11 Domain MCP Tools)
[Tab 7 & 8: 7. Lineage & 8. AI FDE]
  4-Tier 엔터프라이즈 리니지 (< 5ms 즉시 로딩) + 11종 도메인 MCP 자율 추론 오케스트레이터
```

---

## 3. 디렉토리 구조 및 구성 파일

```
industry_cases/
├── README.md                                    # 본 총괄 가이드
├── 01_manufacturing/                            # 1. 스마트 제조 (포스코, 현대자동차)
│   ├── README.md                                # 제조 세그먼트 공통 프레임워크 & 도메인 메타모델
│   ├── case_posco_smart_steel_mill.md          # 포스코: 제철 연속 공정·설비·품질 인과 온톨로지
│   ├── case_hyundai_motor_sdv_supply_chain.md  # 현대자동차: SDV 전장 BOM·공급망 온톨로지 (HD현대 비교 포함)
│   └── data_templates/                          # 즉시 실행 가능한 DDL, CSV, SOP 마크다운
│       ├── schema_manufacturing.sql
│       ├── sample_equipment_telemetry.csv
│       └── sop_steel_bearing_inspection.md
├── 02_finance/                                  # 2. 핀테크 & 뱅킹 (카카오뱅크, 토스)
│   ├── README.md                                # 금융 세그먼트 공통 프레임워크 & 규제 컴플라이언스
│   ├── case_kakaobank_unattended_loan_dsr.md   # 카카오뱅크: 비대면 여신 심사 & DSR 40% 온톨로지
│   ├── case_toss_oneapp_fintech_mydata.md      # 토스: 원앱 멀티금융 중개 & 마이데이터 온톨로지
│   └── data_templates/
│       ├── schema_finance.sql
│       ├── sample_loan_products.csv
│       └── policy_dsr_regulation_guide.md
├── 03_retail_commerce/                          # 3. 유통 & 이커머스 (GS리테일, CJ대한통운/올리브영)
│   ├── README.md                                # 유통/물류 세그먼트 공통 프레임워크 & 정산/SLA
│   ├── case_gs_retail_franchise_omnichannel.md # GS리테일: 가맹계약 정산 & 옴니채널 재고 온톨로지
│   ├── case_cj_logistics_oliveyoung_sla.md     # CJ대한통운/올리브영: 풀필먼트 SLA & 정산 온톨로지
│   └── data_templates/
│       ├── schema_retail.sql
│       ├── sample_franchise_settlement.csv
│       └── policy_logistics_sla_contract.md
└── 04_telecommunications/                       # 4. 통신 & 미디어 (SK텔레콤, KT)
    ├── README.md                                # 통신 세그먼트 공통 프레임워크 & 번들링/위약금
    ├── case_skt_subscription_membership.md     # SK텔레콤: T우주 구독 결합 & 멤버십 온톨로지
    ├── case_kt_wired_wireless_bundle_sla.md     # KT: 유무선 결합 해지 방어 & B2B 회선 SLA 온톨로지
    └── data_templates/
        ├── schema_telecom.sql
        ├── sample_subscription_bundles.csv
        └── policy_six_plan_subsidy_rules.md
```

---

## 4. 실무 딜리버리 팀 활용 가이드 (How to Apply)

1. **도메인 선정 및 케이스 복사**:
   - 신규 고객사의 산업군에 매칭되는 `industry_cases/` 서브폴더의 케이스 명세서를 참조합니다.
2. **원천 데이터 매핑 및 선행 `4. Wiki Agent` 검증**:
   - 고객사의 비정형 규정 문서(PDF/Word)를 담백한 YAML Frontmatter(`---\n...\n---`)가 포함된 `2. OKF Layer` 위키로 변환하고, **`4. Wiki Agent` (GCS)**로 규정/예외 질의를 선행 검증합니다.
3. **정형 DW 결합 및 `5. Bigquery Graph` / `6. BQG Agent` 확장**:
   - 고객사 DW 테이블을 `data_templates/schema_*.sql`의 DDL 구조에 맞춰 매핑한 뒤 `python3 run_pipeline.py`를 실행하여 **`5. Bigquery Graph`**와 **`6. BQG Agent`**를 활성화합니다.
4. **`Agentic Ontology Studio` 통합 검증**:
   - `python3 -m src.web.studio_server`를 기동하여 `0. Overview`(전체 스텝 ➔ 아키텍처 ➔ 피처갭 ➔ 성능/결과)부터 `4. Wiki Agent`, `6. BQG Agent`, `7. Lineage`(`< 5ms`), `8. AI FDE`까지 `0. Overview` ~ `8. AI FDE` 전 구간을 확인합니다.
