---
id: concepts
title: 핵심 개념
layer: L2
sources: [DOC_CHUNK_001, DOC_CHUNK_002, DOC_CHUNK_003, DOC_CHUNK_004, DOC_CHUNK_005]
---
# 핵심 개념

각 개념은 그래프의 `WikiConceptNode`가 되고, `GOVERNS` 관계로 규칙([rules])에 연결됩니다. 기간 · 금액 · 비율 같은 정책값은 [rules]에만 있습니다.

| 개념 ID | 개념 | 뜻 | 규칙 | 근거 조항 |
| :--- | :--- | :--- | :--- | :--- |
| `CON-PUBLIC-SUBSIDY` | 공시지원금 | 개통 시 출고가에서 한 번 차감해 주는 단말 구매 지원금. 받으면 기준 요금제 유지 의무가 생깁니다. | `RULE_SUBSIDY_CAP`, `RULE_SIX_PLAN_180D` | `DOC_CHUNK_001` |
| `CON-RETAIL-SUBSIDY` | 유통망 추가지원금 | 대리점이 공시지원금에 더해 지급하는 지원금. 상한은 공시지원금 대비 비율입니다. | `RULE_SUBSIDY_CAP` | `DOC_CHUNK_001` |
| `CON-BASELINE-PLAN` | 기준 요금제선 | 의무기간 동안 유지해야 하는 최저 월정액 수준. 이보다 낮추면 차액정산금이 생깁니다. | `RULE_SIX_PLAN_180D` | `DOC_CHUNK_002` |
| `CON-COMMITMENT-180D` | 의무유지 약정 | 공시지원금 고객이 개통일부터 정해진 기간 동안 기준선 이상을 유지하는 약정. | `RULE_SIX_PLAN_180D` | `DOC_CHUNK_002` |
| `CON-DIFF-PENALTY` | 차액정산금 (위약금) | 의무기간 안에 기준선 미만으로 낮출 때 지원금 차액을 남은 기간 비율만큼 돌려받는 금액. | `RULE_SIX_PLAN_180D` | `DOC_CHUNK_003` |
| `CON-WELFARE-EXEMPT` | 시니어 · 복지 면제 | 확인된 시니어 · 사회복지 대상이 지정 요금제로 바꾸면 의무기간 안이라도 차액정산금을 면제. | `RULE_WELFARE_EXEMPT` | `DOC_CHUNK_004` |
| `CON-MILITARY-HOLD` | 군 입대 일시정지 | 현역 입대로 회선을 정지하면 복무 기간 동안 의무기간 계산을 멈추고 조기 해지 위약금이 없습니다. | `RULE_WELFARE_EXEMPT` | `DOC_CHUNK_004` |
| `CON-SELECTIVE-25` | 선택약정 요금할인 | 공시지원금 대신 매월 요금을 일정 비율 할인받는 약정. | `RULE_TCO_24M` | `DOC_CHUNK_005` |
| `CON-TCO-24M` | 24개월 총비용 (TCO) | 약정 기간 동안 내는 단말 원금과 요금의 합계. 공시지원금과 선택약정을 비교하는 기준. | `RULE_TCO_24M` | `DOC_CHUNK_005` |

## 개념 사이의 관계 (그래프 엣지)
1. `USES_DEVICE` — 고객 계약 → 개통 단말
2. `SUBSCRIBES_PLAN` — 고객 계약 → 가입 요금제
3. `HAS_SUBSIDY_POLICY` — 단말 → 요금제 (공시지원금 · 추가지원금 결합)
4. `APPLIES_TO_PLAN` — 규칙 → 요금제 (P3 브릿지)
5. `GOVERNS` — 개념 → 규칙 · `USES_PARAM` — 규칙 → 정책값 · `GROUNDED_IN` — 규칙 → 근거 조항 · `APPLIES_RULE` — 워크플로우 단계 → 규칙
