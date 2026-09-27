# Enterprise Knowledge Wiki: Codified Business Rules (Layer 3)
Deterministic business logic governing penalty calculations, TCO comparison, and statutory exemptions:

### Rule 1: 180-Day Baseline Plan Commitment (`RULE_SIX_PLAN_180D` · `DOC_CHUNK_002`, `DOC_CHUNK_003`)
- **Condition**: Subscriber activated terminal with public subsidy under a baseline or higher plan (`>= 45,000 KRW`).
- **Constraint**: Must maintain baseline tier (`is_baseline_tier = true`) for at least **180 days** from activation.
- **Penalty on Breach (< 180 Days)**:
  `Penalty = (Initial Basic Subsidy - Lower Tier Basic Subsidy) * (180 - Elapsed Days) / 180`
- **Post-180 Days (`>= 180 Days`)**: Penalty is `0 KRW`.

### Rule 2: Statutory Welfare & Military Exemptions (`RULE_WELFARE_EXEMPT` · `DOC_CHUNK_004`)
- **Senior / Welfare Transition**: Subscribers with `welfare_status = SENIOR_EXEMPT` transitioning to designated Senior/Welfare plans incur `0 KRW` penalty even within 180 days.
- **Military Enlistment Hold**: `MILITARY_PAUSE_ELIGIBLE` pauses the 180-day commitment counter during active service.

### Rule 3: 24-Month Public Subsidy vs. 25% Selective Contract (`RULE_TCO_COMPARE` · `DOC_CHUNK_005`)
- **Public Subsidy 24M TCO**: `(Factory Price - Total Subsidy) + (Monthly Fee * 24)`
- **Selective 25% Discount 24M TCO**: `Factory Price + (Monthly Fee * 0.75 * 24)`
