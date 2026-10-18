---
id: rules
title: Business rules and policy values
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
# Business rules and policy values

> **G2-W single source**: every policy value is declared only in the frontmatter `graph.properties` above. The graph `PolicyParamNode`s and workflow decisions use these values as they are.

## Policy values
| Key | Value | Meaning | Source |
| :--- | :--- | :--- | :--- |
| `mandatory_retention_days` | 180 days | Baseline plan commitment period for public-subsidy customers | `DOC_CHUNK_002` |
| `baseline_fee_krw` | 45,000 KRW per month | 5G baseline plan threshold (for reference, the documents give an LTE baseline of 26,400 KRW per month) | `DOC_CHUNK_002` |
| `retail_subsidy_cap_rate` | 15% | Retail additional subsidy cap (of the public subsidy) | `DOC_CHUNK_001` |
| `selective_discount_rate` | 25% | Monthly fee discount rate of the selective contract | `DOC_CHUNK_005` |
| `tco_months` | 24 months | Total cost comparison period | `DOC_CHUNK_005` |

## Rules
### `RULE_SUBSIDY_CAP` · Public subsidy + retail additional subsidy (`DOC_CHUNK_001`)
- **Condition**: `contract_type == 'PUBLIC_SUBSIDY'`
- **Calculation**: `total subsidy = public subsidy + retail additional subsidy`, `net purchase principal = factory price - total subsidy`
- The retail additional subsidy is paid up to 15% of the public subsidy.

### `RULE_SIX_PLAN_180D` · 180-day baseline and prorated difference penalty (`DOC_CHUNK_002`, `DOC_CHUNK_003`)
- **Condition**: `elapsed days < 180` and `target plan monthly fee < 45,000 KRW`
- **Calculation**: `penalty = ROUND((initial public subsidy - lower plan public subsidy) * (180 - elapsed days) / 180)`
- After 180 or more elapsed days the penalty is 0 KRW. There is also no penalty when the target plan is at or above the baseline.

### `RULE_WELFARE_EXEMPT` · Senior and welfare exemption, military enlistment hold (`DOC_CHUNK_004`)
- **Condition**: `welfare_status IN ('SENIOR_EXEMPT', 'MILITARY_PAUSE_ELIGIBLE')`
- **Decision**: `SENIOR_EXEMPT` customers who switch to a senior or welfare plan pay 0 KRW (exempt), even within 180 days. For `MILITARY_PAUSE_ELIGIBLE` the commitment clock pauses during service and no early termination penalty applies (`RULE_MILITARY_HOLD`).

### `RULE_TCO_24M` · 24-month public subsidy vs. 25% selective contract (`DOC_CHUNK_005`)
- **Condition**: `commitment_months == 24`
- **Calculation**: `public subsidy total cost = (factory price - total subsidy) + monthly fee * 24`, `selective total cost = factory price + monthly fee * 0.75 * 24`
- Compare both and recommend the lower one together with the savings (the difference).
