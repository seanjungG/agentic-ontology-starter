---
id: concepts
title: Key concepts
layer: L2
sources: [DOC_CHUNK_001, DOC_CHUNK_002, DOC_CHUNK_003, DOC_CHUNK_004, DOC_CHUNK_005]
---
# Key concepts

Each concept becomes a `WikiConceptNode` in the graph and links to rules ([rules]) through `GOVERNS`. Policy values such as periods, amounts and rates live only on [rules].

| Concept ID | Concept | Meaning | Rules | Source clause |
| :--- | :--- | :--- | :--- | :--- |
| `CON-PUBLIC-SUBSIDY` | Public subsidy | A device purchase subsidy deducted once from the factory price at activation. Receiving it creates a baseline plan commitment. | `RULE_SUBSIDY_CAP`, `RULE_SIX_PLAN_180D` | `DOC_CHUNK_001` |
| `CON-RETAIL-SUBSIDY` | Retail additional subsidy | An extra subsidy paid by the dealer on top of the public subsidy. Its cap is a ratio of the public subsidy. | `RULE_SUBSIDY_CAP` | `DOC_CHUNK_001` |
| `CON-BASELINE-PLAN` | Baseline plan threshold | The lowest monthly fee level to keep during the commitment period. Going below it creates a difference penalty. | `RULE_SIX_PLAN_180D` | `DOC_CHUNK_002` |
| `CON-COMMITMENT-180D` | Plan commitment | The commitment of a public-subsidy customer to stay at or above the baseline for a fixed period from activation. | `RULE_SIX_PLAN_180D` | `DOC_CHUNK_002` |
| `CON-DIFF-PENALTY` | Difference penalty | The amount reclaimed when going below the baseline within the commitment period: the subsidy difference times the remaining-period ratio. | `RULE_SIX_PLAN_180D` | `DOC_CHUNK_003` |
| `CON-WELFARE-EXEMPT` | Senior and welfare exemption | Verified seniors and welfare recipients who switch to a designated plan are exempt from the difference penalty, even within the commitment period. | `RULE_WELFARE_EXEMPT` | `DOC_CHUNK_004` |
| `CON-MILITARY-HOLD` | Military enlistment hold | When a line is suspended for active-duty service, the commitment clock pauses for the service period and no early termination penalty applies. | `RULE_WELFARE_EXEMPT` | `DOC_CHUNK_004` |
| `CON-SELECTIVE-25` | Selective contract discount | A contract that discounts the monthly fee by a fixed rate instead of a public subsidy. | `RULE_TCO_24M` | `DOC_CHUNK_005` |
| `CON-TCO-24M` | 24-month total cost (TCO) | The sum of device principal and plan fees over the contract; the basis for comparing the public subsidy with the selective contract. | `RULE_TCO_24M` | `DOC_CHUNK_005` |

## Relations between concepts (graph edges)
1. `USES_DEVICE` — customer contract → activated device
2. `SUBSCRIBES_PLAN` — customer contract → subscribed plan
3. `HAS_SUBSIDY_POLICY` — device → plan (public + retail subsidy binding)
4. `APPLIES_TO_PLAN` — rule → plan (P3 bridge)
5. `GOVERNS` — concept → rule · `USES_PARAM` — rule → policy value · `GROUNDED_IN` — rule → source clause · `APPLIES_RULE` — workflow step → rule
