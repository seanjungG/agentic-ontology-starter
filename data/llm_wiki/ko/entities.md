---
id: entities
title: 엔티티 · 테이블 의미
layer: L2
sources: [tb_device_master, tb_plan_master, tb_subsidy_policy, tb_customer_contract, tb_domain_rules, edge_rule_applies_to_plan]
---
# 엔티티 · 테이블 의미

테이블의 **의미만** 위키에 둡니다. 행 값(가격 · 금액 · 고객 정보)은 BigQuery 테이블에 그대로 있고, 숫자 질문은 Graph Agent가 테이블과 그래프를 조회해 답합니다.

| 엔티티 (그래프 라벨) | 테이블 | 키 | 뜻 · 주요 컬럼 |
| :--- | :--- | :--- | :--- |
| 단말 (`DeviceNode`) | `tb_device_master` | `device_id` | 판매 단말 모델. `device_name`(모델명 + 용량), `factory_price_krw`(출고가) |
| 요금제 (`PlanNode`) | `tb_plan_master` | `plan_id` | 월정액 요금제. `monthly_fee_krw`, `min_maintenance_days`(의무유지 대상이면 0보다 큼), `selective_discount_rate` |
| 지원금 정책 (`SubsidyNode`, `HAS_SUBSIDY_POLICY`) | `tb_subsidy_policy` | `policy_id` | 단말 × 요금제 지원금. `base_subsidy_krw`(공시지원금), `additional_subsidy_cap_krw`(유통망 추가지원금 상한), `mandatory_retention_days` |
| 고객 계약 (`CustomerContractNode`) | `tb_customer_contract` | `contract_id` | 비식별 고객 계약. `customer_id`, `contract_type`(`PUBLIC_SUBSIDY` · `SELECTIVE_25PCT`), `elapsed_days`, `welfare_status` |
| 업무 규칙 (`DomainRuleNode`) | `tb_domain_rules` | `rule_id` | [rules]의 규칙을 행으로 옮긴 것. `condition_expr`, `formula_expr`, `source_chunk_id` |
| 규칙 → 요금제 (`APPLIES_TO_PLAN`) | `edge_rule_applies_to_plan` | `edge_id` | 어떤 규칙이 어떤 요금제에 적용되는지 (P3 브릿지) |

## 코드 값
- `welfare_status`: `NONE`(일반) · `SENIOR_EXEMPT`(시니어 · 복지 면제 대상) · `MILITARY_PAUSE_ELIGIBLE`(군 입대 일시정지 대상)
- `contract_type`: `PUBLIC_SUBSIDY`(공시지원금 약정) · `SELECTIVE_25PCT`(선택약정)
- `customer_segment`: `General_VIP` · `General_Standard` · `Senior_Welfare` · `Youth_Family` · `Corporate_B2B`
