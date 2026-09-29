# Enterprise Knowledge Wiki: Codified Business Rules (Layer 3)
Generated from `data/input/03_tables/domain_rules.csv` (BigQuery `tb_domain_rules`).

### `RULE_SUBSIDY_CAP` · Public Subsidy & Retail Additional Subsidy Cap (15%) Rule (`DOC_CHUNK_001`)
- **Condition**: `contract_type == 'PUBLIC_SUBSIDY'`
- **Formula**: `total_subsidy = base_subsidy_krw + additional_subsidy_cap_krw; net_principal = factory_price_krw - total_subsidy`
- Retail additional subsidy is capped at 15% of the base public subsidy; net installment principal equals factory price minus total subsidy.

### `RULE_SIX_PLAN_180D` · 180-Day Baseline (45,000 KRW) Mandatory Retention & Prorated Penalty Rule (`DOC_CHUNK_003`)
- **Condition**: `elapsed_days < 180 AND target_plan_monthly_fee < 45000`
- **Formula**: `penalty = ROUND((initial_base_subsidy - lower_tier_base_subsidy) * (180 - elapsed_days) / 180)`
- Downgrading to a plan below 45,000 KRW/month within 180 days of activation incurs a prorated penalty on the base subsidy difference ((180 - elapsed_days) / 180). Penalty is 0 KRW after 180 days.

### `RULE_WELFARE_EXEMPT` · Senior/Welfare Plan Transition & Military Suspension Penalty Exemption Rule (`DOC_CHUNK_004`)
- **Condition**: `welfare_status IN ('SENIOR_EXEMPT', 'MILITARY_PAUSE_ELIGIBLE')`
- **Formula**: `penalty = 0 (SENIOR_EXEMPT) OR pause_commitment_counter (MILITARY_PAUSE_ELIGIBLE)`
- Subscribers registered under Senior (Age 65+) Welfare Exemption (SENIOR_EXEMPT) are 100% exempt (0 KRW) from prorated penalties when switching to senior/welfare plans within 180 days.

### `RULE_TCO_24M` · 24-Month Public Subsidy vs. 25% Selective Contract TCO Comparison Rule (`DOC_CHUNK_005`)
- **Condition**: `commitment_months == 24`
- **Formula**: `subsidy_24m_tco = (factory_price_krw - total_subsidy) + (monthly_fee_krw * 24); selective_24m_tco = factory_price_krw + (monthly_fee_krw * 0.75 * 24)`
- Compares total public subsidy against 24-month 25% selective fee discount (monthly_fee * 0.25 * 24) to recommend the lower 24-month Total Cost of Ownership (TCO).
