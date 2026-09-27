# [Enterprise Service Consultation Guide: Statutory Exemptions & Bundle Rules]
<!-- DOC_CHUNK_004: Statutory Penalty Exemptions -->
## 4. Statutory Penalty Exemption Clauses (위약금 면제 특례 규정)
1. **Senior & Social Welfare Exemption (`RULE_WELFARE_EXEMPT`)**: Subscribers registered under verified Senior (Age 65+) or Social Welfare categories are exempt from difference settlement penalties (`0 KRW`) when transitioning to designated Senior/Welfare tariff plans, even within the 180-day commitment window.
2. **Military Enlistment Suspension (`RULE_MILITARY_HOLD`)**: Active-duty enlistment pauses the 180-day mandatory commitment clock during the verified service period without triggering early termination penalties.

<!-- DOC_CHUNK_005: 24-Month Contract TCO Comparison Rule -->
## 5. Public Subsidy vs. 25% Selective Contract Comparison (`RULE_TCO_COMPARE`)
1. **Public Subsidy Path**: `24M Total Cost = (Factory Price - Total Subsidy) + (Monthly Plan Fee * 24)`
2. **Selective 25% Discount Path**: `24M Total Cost = Factory Price + (Monthly Plan Fee * 0.75 * 24)`
3. **Consultation Guideline**: Agents must deterministically compute both paths and recommend the lower 24-month Total Cost of Ownership (TCO) option alongside the exact savings amount.
