# Enterprise Agentic Ontology — 4대 산업군 8종 비식별 레퍼런스 템플릿 패키지 (`industry_cases/`)

- **상위 문서**: [`01_prod.md`](../01_prod.md) · [`PROTOTYPING_PLAYBOOK.md`](../PROTOTYPING_PLAYBOOK.md) · [`README.md`](../README.md)
- **목적**: 본 디렉토리(`industry_cases/`)는 특정 단일 기업에 종속되지 않고, **4대 핵심 산업군(스마트 제조, 핀테크/금융, 유통/물류, 통신/미디어)의 8대 엔터프라이즈 실무 요건을 비식별 아키타입으로 추상화**하여 즉시 신규 프로젝트에 이식(`5-File Swap`)할 수 있도록 구성한 레퍼런스 템플릿 패키지입니다.

---

## 1. 4대 산업군 8종 비식별 아키타입 요약

| 산업군 (Segment) | 비식별 아키타입 명칭 | 권장 시나리오 (`PROTOTYPING_PLAYBOOK.md`) | 핵심 비즈니스 해결 과제 | 하이브리드 온톨로지 융합 자산 (`data_templates/`) |
| :--- | :--- | :---: | :--- | :--- |
| **1. 스마트 제조<br>(`01_manufacturing/`)** | **[스마트 제철소 A사](./01_manufacturing/case_smart_steel_mill.md)**<br>*(Smart Steel Corp)* | Scenario B / C | • 연속 공정 품질 불량 인과 추적<br>• 설비 예방보전(PdM) 진동/온도 이상 감지<br>• 안전보건 작업허가서(SOP) 및 인터락 지침 | • 설비 텔레메트리 CSV (`sample_equipment_telemetry.csv`)<br>• 제조 그래프 DDL (`schema_manufacturing.sql`)<br>• 베어링 점검 SOP (`sop_steel_bearing_inspection.md`) |
| | **[글로벌 완성차 B사](./01_manufacturing/case_automotive_sdv_supply_chain.md)**<br>*(Mobility OEM Corp)* | Scenario B / D | • 완성차/SDV 전장 부품 복합 BOM 호환성<br>• 1/2차 협력사 공급망(SCM) 리드타임 지연 추적<br>• 설계 변경(ECN) 및 리콜 규정 검증 | • E-BOM / M-BOM 마스터 및 협력사 납기 원장<br>• 자동차 안전기준 및 설계변경 지침 |
| **2. 핀테크 & 뱅킹<br>(`02_finance/`)** | **[인터넷전문은행 A사](./02_finance/case_digital_bank_unattended_loan_dsr.md)**<br>*(Digital Direct Bank)* | Scenario B / D | • 모바일 비대면 여신 심사 및 대출 한도 산정<br>• 금융소비자보호법 설명의무 준수 검증<br>• DSR 40% 산정 및 생애최초 LTV 특례 판정 | • 대출 상품 CSV (`sample_loan_products.csv`)<br>• 금융 그래프 DDL (`schema_finance.sql`)<br>• DSR 감독규정 가이드 (`policy_dsr_regulation_guide.md`) |
| | **[원앱 핀테크 B사](./02_finance/case_oneapp_fintech_mydata.md)**<br>*(One-App Fintech)* | Scenario B / C | • 원앱 멀티 금융 상품 비교·중개<br>• 마이데이터 기반 개인화 지출/보장 진단<br>• 간편결제 가맹점 정산 수수료율 산정 | • 제휴 금융사 대출/카드 상품 원장<br>• 전자금융거래 기본약관 및 제휴 정산 규정 |
| **3. 유통 & 물류<br>(`03_retail_commerce/`)** | **[전국 가맹 유통 A사](./03_retail_commerce/case_convenience_franchise_omnichannel.md)**<br>*(Convenience Franchise Corp)* | Scenario B | • 편의점·수퍼 가맹 상생 정산 지원금 산출<br>• 옴니채널 퀵커머스 매장 재고 밸런싱<br>• 신선식품 유통기한 임박 폐기 지원금 계산 | • 가맹 정산 CSV (`sample_franchise_settlement.csv`)<br>• 리테일 그래프 DDL (`schema_retail.sql`)<br>• 물류/정산 SLA 약관 (`policy_logistics_sla_contract.md`) |
| | **[옴니채널 풀필먼트·리테일 B사](./03_retail_commerce/case_omnichannel_fulfillment_sla.md)**<br>*(Omnichannel Fulfillment)* | Scenario B / C | • 풀필먼트 물류 배송 SLA 지연 배상 판정<br>• 입점 브랜드 판매 수수료 및 프로모션 분담금<br>• 당일 퀵배송 권역 라우팅 패널티 산정 | • 풀필먼트 입출고/배송 타임스탬프 원장<br>• 택배 표준약관 및 물류 SLA 가이드 |
| **4. 통신 & 미디어<br>(`04_telecommunications/`)** | **[모바일 구독 통신사 A사](./04_telecommunications/case_mobile_subscription_membership.md)**<br>*(Mobile Carrier A)* | Scenario B / D | • AI·라이프 구독 결합 상품 할인 규칙<br>• 패밀리/회선 결합 할인 중복 배제 판정<br>• 180일 의무유지 기간 내 요금제 변경 위약금 산정 | • 구독 번들 CSV (`sample_subscription_bundles.csv`)<br>• 통신 그래프 DDL (`schema_telecom.sql`)<br>• 지원금·의무유지 규정 (`policy_baseline_plan_subsidy_rules.md`) |
| | **[유무선 결합 통신사 B사](./04_telecommunications/case_converged_bundle_enterprise_sla.md)**<br>*(Converged Carrier B)* | Scenario B / D | • 유무선 복합 결합(인터넷+모바일+IPTV) 해지 방어<br>• 엔터프라이즈 B2B 전용회선/IDC SLA 장애 배상<br>• 결합 약정 할인 반환금 일할 계산 검증 | • 가입 회선 상태 및 번들 결합 원장<br>• 기업 전용회선 SLA 약관 및 배상 규정 |

---

## 2. 5-Stage × 6-Tab 공통 아키텍처 매핑

8개 산업군 템플릿 모두 스타터팩의 **5-Stage 엔지니어링 파이프라인** 및 **6-Tab 스튜디오(`src/web/studio_server.py`)**와 1:1로 호환됩니다:

```text
[Stage 1. Asset]
  data_templates/*.md (비정형 SOP/약관) + data_templates/*.csv (정형 DW 원장) + Golden CQ
          │
          ▼ (pipeline/ingest.py — SHA-256 청킹 & 3-Layer OKF Wiki 컴파일)
[Stage 2. Wiki & Semantic Graph]
  data/llm_wiki/{summary,entities,concepts,rules}.md + tb_doc_chunks + tb_domain_rules
          │
          ├──► (Track 1 · Lite 선택 시 물리 그래프 없이 Stage 4 에이전트로 직행)
          │
          ▼ (pipeline/graph_builder.py — BigQuery / Spanner Property Graph DDL)
[Stage 3. Property Graph]
  정형 마스터/트랜잭션 노드 ──[관계형 FK 엣지 + 비정형 규칙/근거 엣지]──> 도메인 규칙·문서 청크
          │
          ▼ (src/agent/mcp_server.py & reasoning_engine.py — 2-Pass 추론 & 8종 MCP)
[Stage 4. Agent & MCP]
  1회차 슬롯 추출 ➔ 런타임 MCP 3종(원장 조회·결정론적 수식 계산·GQL/위키 탐색) ➔ 2회차 근거 합성
          │
          ▼ (pipeline/validator.py — 4계층 리니지 & 경계값 50회 벤치마크)
[Stage 5. Lineage & Eval]
  Source File ➔ DocChunk ➔ DomainRule ➔ Contract ➔ CQ 리니지 추적 및 Gate 1~5 검증
```

---

## 3. 빠른 적용 방법 (`PROTOTYPING_PLAYBOOK.md` 연계)

1. 구축하려는 도메인과 가장 유사한 산업군 폴더(`01_manufacturing/` ~ `04_telecommunications/`)의 `case_*.md`와 `data_templates/`를 확인합니다.
2. [`PROTOTYPING_PLAYBOOK.md`](../PROTOTYPING_PLAYBOOK.md)의 **Scenario A ~ D** 중 하나를 선택하고, Jetski / Antigravity / Cursor 에이전트에게 해당 산업군 템플릿 경로를 지정하여 **5-File Swap**을 지시합니다.
3. `python3 pipeline/ingest.py` → `python3 pipeline/graph_builder.py` → `python3 pipeline/validator.py` → `python3 -m src.web.studio_server 8080` 순서로 실행하여 결과를 확인합니다.
