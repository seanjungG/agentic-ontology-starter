# Enterprise Knowledge Wiki: Codified Business Rules (Layer 3)
Deterministic business logic governing penalty calculations and statutory exemptions:

### Rule 1: 180-Day Six-Plan Commitment Obligation (`RULE_SIX_PLAN_180D`)
- **Condition**: Subscriber activated terminal with official subsidy under a high-tier plan (>= 95,000 KRW).
- **Constraint**: Must maintain baseline tier or higher for at least 180 days from activation date.
- **Penalty on Breach (< 180 Days)**:
  `Penalty = (Initial Subsidy - Downgraded Plan Subsidy) * (180 - Maintained Days) / 180`
- **Post-180 Days**: Differential clawback is completely waived (0 KRW penalty).

### Rule 2: 24-Month Optional Contract Discount Comparison (`RULE_SELECTIVE_CONTRACT_25PCT`)
- **Formula**: `Monthly Discount = Monthly Plan Fee * 0.25`
- **24-Month Aggregate**: `Total Discount = Monthly Discount * 24`
- **Decision Matrix**: Compare 24-month aggregate discount against initial official subsidy.
