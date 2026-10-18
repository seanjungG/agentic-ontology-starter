---
id: rules
title: 업무 규칙 · 정책값
layer: L3
sources: [DOC_CHUNK_001, DOC_CHUNK_002, DOC_CHUNK_003, DOC_CHUNK_004, DOC_CHUNK_005]
graph:
  properties:
    mandatory_retention_days: 180
    baseline_fee_krw: 45000
    retail_subsidy_cap_rate: 0.15
    selective_discount_rate: 0.25
    tco_months: 24
---
# 업무 규칙 · 정책값

> **G2-W 단일 출처**: 모든 정책값은 위 frontmatter `graph.properties`에만 선언합니다. 그래프의 `PolicyParamNode`와 워크플로우 판정은 이 값을 그대로 씁니다.

## 정책값
| 키 | 값 | 뜻 | 근거 |
| :--- | :--- | :--- | :--- |
| `mandatory_retention_days` | 180일 | 공시지원금 고객의 기준 요금제 의무유지 기간 | `DOC_CHUNK_002` |
| `baseline_fee_krw` | 월 45,000원 | 5G 기준 요금제선 (참고: 문서상 LTE 기준선은 월 26,400원) | `DOC_CHUNK_002` |
| `retail_subsidy_cap_rate` | 15% | 유통망 추가지원금 상한 (공시지원금 대비) | `DOC_CHUNK_001` |
| `selective_discount_rate` | 25% | 선택약정 월 요금 할인율 | `DOC_CHUNK_005` |
| `tco_months` | 24개월 | 총비용 비교 기간 | `DOC_CHUNK_005` |

## 규칙
### `RULE_SUBSIDY_CAP` · 공시지원금 + 유통망 추가지원금 합산 (`DOC_CHUNK_001`)
- **조건**: `contract_type == 'PUBLIC_SUBSIDY'`
- **계산**: `총 지원금 = 공시지원금 + 유통망 추가지원금`, `실구매 원금 = 출고가 - 총 지원금`
- 유통망 추가지원금은 공시지원금의 최대 15%까지 지급합니다.

### `RULE_SIX_PLAN_180D` · 180일 기준선 유지와 일할 차액정산금 (`DOC_CHUNK_002`, `DOC_CHUNK_003`)
- **조건**: `경과일수 < 180` 이고 `변경 요금제 월정액 < 45,000원`
- **계산**: `위약금 = ROUND((최초 공시지원금 - 하위 요금제 공시지원금) × (180 - 경과일수) / 180)`
- 경과일수가 180일 이상이면 위약금은 0원입니다. 변경 요금제가 기준선 이상이어도 위약금이 없습니다.

### `RULE_WELFARE_EXEMPT` · 시니어 · 복지 면제와 군 입대 일시정지 (`DOC_CHUNK_004`)
- **조건**: `welfare_status IN ('SENIOR_EXEMPT', 'MILITARY_PAUSE_ELIGIBLE')`
- **판정**: `SENIOR_EXEMPT`는 시니어 · 복지 요금제로 바꾸면 180일 안이라도 위약금 0원(면제). `MILITARY_PAUSE_ELIGIBLE`은 복무 기간 동안 의무기간 계산이 멈추고 조기 해지 위약금이 없습니다(`RULE_MILITARY_HOLD`).

### `RULE_TCO_24M` · 24개월 공시지원금 vs 25% 선택약정 (`DOC_CHUNK_005`)
- **조건**: `commitment_months == 24`
- **계산**: `공시지원금 총비용 = (출고가 - 총 지원금) + 월 요금 × 24`, `선택약정 총비용 = 출고가 + 월 요금 × 0.75 × 24`
- 두 값을 비교해 더 낮은 쪽과 절감액(차이)을 안내합니다.
