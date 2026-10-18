---
id: entities
title: Entities and table meaning
layer: L2
sources: [tb_device_master, tb_plan_master, tb_subsidy_policy, tb_customer_contract, tb_domain_rules, edge_rule_applies_to_plan]
---
# Entities and table meaning

Only the **meaning** of the tables lives in the wiki. Row values (prices, amounts, customer data) stay in the BigQuery tables, and numeric questions are answered by the Graph Agent from the tables and the graph.

| Entity (graph label) | Table | Key | Meaning · main columns |
| :--- | :--- | :--- | :--- |
| Device (`DeviceNode`) | `tb_device_master` | `device_id` | Device models on sale. `device_name` (model + storage), `factory_price_krw` (factory price) |
| Plan (`PlanNode`) | `tb_plan_master` | `plan_id` | Monthly plans. `monthly_fee_krw`, `min_maintenance_days` (greater than 0 when the plan carries the commitment), `selective_discount_rate` |
| Subsidy policy (`SubsidyNode`, `HAS_SUBSIDY_POLICY`) | `tb_subsidy_policy` | `policy_id` | Subsidy per device x plan. `base_subsidy_krw` (public subsidy), `additional_subsidy_cap_krw` (retail subsidy cap), `mandatory_retention_days` |
| Customer contract (`CustomerContractNode`) | `tb_customer_contract` | `contract_id` | De-identified contracts. `customer_id`, `contract_type` (`PUBLIC_SUBSIDY` · `SELECTIVE_25PCT`), `elapsed_days`, `welfare_status` |
| Business rule (`DomainRuleNode`) | `tb_domain_rules` | `rule_id` | The rules of [rules] as rows. `condition_expr`, `formula_expr`, `source_chunk_id` |
| Rule → plan (`APPLIES_TO_PLAN`) | `edge_rule_applies_to_plan` | `edge_id` | Which rule applies to which plan (P3 bridge) |

## Code values
- `welfare_status`: `NONE` (regular) · `SENIOR_EXEMPT` (senior / welfare exemption) · `MILITARY_PAUSE_ELIGIBLE` (military enlistment hold)
- `contract_type`: `PUBLIC_SUBSIDY` (public subsidy contract) · `SELECTIVE_25PCT` (selective contract)
- `customer_segment`: `General_VIP` · `General_Standard` · `Senior_Welfare` · `Youth_Family` · `Corporate_B2B`
