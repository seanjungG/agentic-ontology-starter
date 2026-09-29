# Copyright (c) 2026 Sean Jung (seanjung@google.com). All Rights Reserved.
# Non-Commercial Use Only: Methodology & Docs under CC BY-NC-ND 4.0; Source Code under PolyForm Noncommercial License 1.0.0.
# Commercial use, paid consulting/SI/PoC delivery, or production deployment requires prior written permission from seanjung@google.com.

# -*- coding: utf-8 -*-
"""
English Localization Dictionary & Data/Output Translator (`src/agent/i18n_en.py`).
Ensures that when `STARTER_LANG=en` (or inside `notebooks/en/*.ipynb`), all structured table
descriptions, rule names, semantic edge labels, policy chunk parentheticals, business glossary terms,
Golden CQs, Boundary Cases, and MCP tool summaries are rendered in 100% English with zero Korean characters.
"""
import re
from typing import Any, Dict, List

# 1. Exact string replacement map for BigQuery table fields & JSON values
EXACT_KO_TO_EN: Dict[str, str] = {
    # tb_domain_rules.rule_name
    "공시지원금 및 유통망 추가지원금(15%) 합산 규칙": "Public Subsidy & Retail Additional Subsidy Cap (15%) Rule",
    "180일 기준선(45,000원) 의무유지 및 일할 차액위약금 규칙": "180-Day Baseline (45,000 KRW) Mandatory Retention & Prorated Penalty Rule",
    "시니어·복지 요금제 전환 및 군입대 장기정지 위약금 면제 특례": "Senior/Welfare Plan Transition & Military Suspension Penalty Exemption Rule",
    "24개월 공시지원금 vs 25% 선택약정 총비용(TCO) 비교 규칙": "24-Month Public Subsidy vs. 25% Selective Contract TCO Comparison Rule",
    # tb_domain_rules.description_ko
    "유통망 추가지원금은 공시지원금의 최대 15%까지 지급되며, 실구매 원금은 출고가에서 총 지원금을 차감하여 산정함.": (
        "Retail additional subsidy is capped at 15% of the base public subsidy; net installment principal equals factory price minus total subsidy."
    ),
    "개통 후 180일 이내에 월정액 45,000원 미만 요금제로 하향 변경 시, 기본 공시지원금 차액에 잔여일수 비율((180-유지일수)/180)을 곱한 일할 위약금이 부과됨. 180일 경과 시 위약금 0원.": (
        "Downgrading to a plan below 45,000 KRW/month within 180 days of activation incurs a prorated penalty on the base subsidy difference ((180 - elapsed_days) / 180). Penalty is 0 KRW after 180 days."
    ),
    "만 65세 이상 시니어 복지 특례(SENIOR_EXEMPT) 대상자가 시니어/복지 요금제로 전환 시 180일 이내라도 차액정산 위약금을 100% 면제(0원)함.": (
        "Subscribers registered under Senior (Age 65+) Welfare Exemption (SENIOR_EXEMPT) are 100% exempt (0 KRW) from prorated penalties when switching to senior/welfare plans within 180 days."
    ),
    "24개월 총소유비용(TCO) 비교 시 공시지원금 총액과 24개월 25% 요금할인 총액(월정액×0.25×24)을 비교하여 유리한 약정을 추천함.": (
        "Compares total public subsidy against 24-month 25% selective fee discount (monthly_fee * 0.25 * 24) to recommend the lower 24-month Total Cost of Ownership (TCO)."
    ),
    # edge_rule_applies_to_plan.relation_label_ko
    "180일 기준선 유지 의무 적용": "180-day baseline retention duty applies",
    "24개월 공시 vs 선택약정 비교 적용": "24-month public subsidy vs. selective contract TCO applies",
    "기준선 미만 하향 시 일할 위약금 발생": "Prorated penalty applies when downgrading below baseline",
    "시니어 복지 전환 시 위약금 면제 특례": "Penalty exemption applies for senior welfare transition",
    # business_glossary.json keys & values
    "공시지원금": "Public Subsidy (Base Subsidy)",
    "단말기 출고가에서 이동통신사가 최초 개통 시 1회 직접 차감해주는 법적 단말 구매 보조금": (
        "One-time statutory device purchase subsidy deducted directly from the factory price upon initial activation."
    ),
    "유통망지원금": "Retail Additional Subsidy (15% Cap)",
    "유통 대리점에서 공시지원금의 최대 15% 한도 내에서 합법적으로 추가 지급하는 보조금": (
        "Additional retail subsidy legally granted by authorized dealers up to 15% of the base public subsidy."
    ),
    "180일 의무유지 약정 (Baseline Retention Plan)": "180-Day Baseline Retention Plan",
    "공시지원금을 수령한 고객이 개통일로부터 180일 동안 특정 요금제선 이상을 유지해야 하는 의무 약정": (
        "Mandatory commitment requiring public-subsidy subscribers to maintain a plan at or above the baseline threshold (45,000 KRW) for 180 days."
    ),
    "차액정산금 (위약금)": "Subsidy Difference Clawback (Prorated Penalty)",
    "180일 이내에 기준 요금제선 미만으로 하향 변경 시 잔여 기간에 비례하여 부과되는 반환금": (
        "Prorated clawback charge levied in proportion to remaining days when downgrading below the baseline plan within 180 days."
    ),
    # Golden CQs (CQ-01 .. CQ-05)
    "Galaxy S26 Ultra 256GB 모델의 공식 출고가는 얼마인가?": "What is the official factory price of the Galaxy S26 Ultra 256GB model?",
    "Galaxy S26 Ultra 256GB를 5G Premier Essential(85,000원) 요금제로 개통할 때 총 지원금과 실구매가는?": (
        "When activating a Galaxy S26 Ultra 256GB on the 5G Premier Essential (85,000 KRW) plan, what are the total subsidy and net purchase price?"
    ),
    "지원금 517,500 KRW / 실구매가 1,180,900 KRW": "Total Subsidy 517,500 KRW / Net Price 1,180,900 KRW",
    "CUST_DEMO_001 고객이 개통 후 120일 시점에 5G Slim(45,000원) 미만인 5G Light(37,000원) 요금제로 하향 변경 시 차액정산 위약금은?": (
        "If customer CUST_DEMO_001 downgrades at 120 elapsed days to the 5G Light (37,000 KRW) plan below the 5G Slim (45,000 KRW) baseline, what is the prorated penalty?"
    ),
    "Galaxy S26 Ultra 256GB + 5G Premier Essential(85,000원) 24개월 유지 시 공시지원금과 선택약정(25%) 중 유리한 조건과 절감액은?": (
        "For Galaxy S26 Ultra 256GB + 5G Premier Essential (85,000 KRW) over 24 months, which option is better between Public Subsidy and 25% Selective Discount, and what are the savings?"
    ),
    "공시지원금 유리 (공시지원금 총액 517,500원 vs 선택약정 할인 총액 510,000원 · 24개월 총비용 차액 7,500원)": (
        "Public Subsidy is better (Total Subsidy 517,500 KRW vs. Selective Discount 510,000 KRW · 24M TCO savings 7,500 KRW)"
    ),
    "CUST_DEMO_003(시니어 복지 대상) 고객이 개통 88일차에 시니어 요금제로 변경할 때 위약금 면제 여부와 근거 규정 앵커를 확인해줘.": (
        "When customer CUST_DEMO_003 (Senior Welfare eligible) switches to a senior plan at 88 elapsed days, is the penalty exempted and what is the grounding chunk anchor?"
    ),
    "0 KRW (시니어/복지 특례 면제 · DOC_CHUNK_004)": "0 KRW (Senior/Welfare statutory exemption · DOC_CHUNK_004)",
    # Boundary Cases (BQ-01 .. BQ-10)
    "개통한 지 4개월 됐는데 요금제 낮추면 위약금 나오나요?": "I activated my phone 4 months ago; will I be charged a penalty if I downgrade my plan?",
    "고객 ID / 현재 요금제 / 변경 희망 요금제 미지정": "Missing customer ID, current plan, and target downgrade plan",
    "금액을 단정하지 않고 부족한 정보(고객 ID·변경 요금제 등)를 안내": "Do not fabricate a penalty amount; request the missing slots (customer ID, target plan, elapsed days)",
    "어르신 요금제로 바꾸려는데 180일 안 지났으면 위약금 내야 하나요?": "I want to switch to a senior plan before 180 days; do I have to pay a penalty?",
    "시니어 특례 면제 등록 여부 미지정": "Missing Senior Welfare exemption registration status (customer ID)",
    "시니어 특례(RULE_WELFARE_EXEMPT / DOC_CHUNK_004) 조건을 안내하고 고객 정보를 요청": "Explain the Senior Welfare exemption condition (RULE_WELFARE_EXEMPT / DOC_CHUNK_004) and request customer ID",
    "갤럭시 S26 울트라 지금 사면 지원금 얼마 받아요?": "How much subsidy do I get if I buy a Galaxy S26 Ultra right now?",
    "용량(256GB/512GB) 및 가입 요금제 미지정": "Unspecified storage capacity (256GB/512GB) and subscription plan",
    "BigQuery 지원금 정책의 요금제별 총 지원금을 제시": "Present total subsidy amounts across available plans from BigQuery subsidy policies",
    "군대 입대 때문에 일시정지하면 180일 의무기간은 어떻게 되나요?": "If I suspend my line for military enlistment, what happens to the 180-day mandatory retention period?",
    "군입대 정지 특례 엔티티 참조": "Military enlistment suspension rule reference",
    "군입대 장기정지 특례(MILITARY_PAUSE_ELIGIBLE / DOC_CHUNK_004) 근거를 인용": "Cite the military enlistment suspension clause (MILITARY_PAUSE_ELIGIBLE / DOC_CHUNK_004)",
    "아이폰 최신형 프로 모델 선약이랑 공시 중 뭐가 더 이득인가요?": "For the latest iPhone Pro model, is the 25% selective discount or public subsidy better?",
    "단말 별칭(아이폰 최신형 프로) 및 요금제 미지정": "Device alias ('latest iPhone Pro') and unspecified tariff plan",
    "카탈로그의 iPhone 16 Pro로 매핑하고 BigQuery 정책 기준 24개월 총비용 차액을 제시": "Map to catalog iPhone 16 Pro and present the 24-month TCO difference from BigQuery policies",
    "개통 185일째인데 제일 싼 LTE 요금제로 내려도 위약금 없죠?": "It has been 185 days since activation; is there zero penalty if I downgrade to the cheapest LTE plan?",
    "180일 경과 후 면제 경계값": "Post-180-day full exemption boundary condition",
    "경과일 185일이 의무기간 이상이므로 위약금 0원": "Zero penalty (0 KRW) because 185 elapsed days exceeds the 180-day mandatory retention window",
    "지원금 테이블이랑 실제 그래프 노드에 중복 적재된 데이터가 있나요?": "Are there any duplicate keys loaded in the subsidy table or property graph nodes?",
    "노드 테이블 중복 키 메타데이터 조회": "Node table duplicate-key metadata inspection",
    "Stage 3 실측 결과(노드 테이블 중복 키 건수)를 제시": "Report the Stage 3 measured duplicate-key count (0 duplicates) across node tables",
    "5G 프리미어 에센셜에서 다이렉트 61로 바꾸면 기준선 위반인가요?": "If I switch from 5G Premier Essential to 5G Direct 61, does that violate the baseline threshold?",
    "기준선 이상 요금제 간 하향 시 차액정산 여부": "Downgrade between plans above the 45,000 KRW baseline threshold",
    "변경 요금제 월정액이 기준선 이상이므로 기준선 위반 아님": "No baseline violation (0 KRW penalty) because the target plan fee (61,000 KRW) is above the 45,000 KRW baseline",
    "법인 명의로 개통한 회선도 180일 의무유지 기준선 룰이 똑같이 적용되나요?": "Does the 180-day baseline retention rule apply equally to Corporate B2B lines?",
    "법인(Corporate_B2B) 세그먼트 정책 매핑": "Corporate_B2B segment policy mapping",
    "세그먼트별 예외 규칙 존재 여부를 도구 결과로 밝히고 RULE_SIX_PLAN_180D 근거를 인용": "Report whether segment exceptions exist based on tool output and cite RULE_SIX_PLAN_180D",
    "Spanner Graph로 전환하면 지금 쓰는 GQL 쿼리랑 스키마를 다 새로 짜야 하나요?": "If we migrate to Cloud Spanner Graph, do we have to rewrite all our GQL queries and schema from scratch?",
    "BigQuery Graph vs Spanner Graph 호환성": "BigQuery Property Graph vs. Cloud Spanner Graph ISO GQL compatibility",
    "도구 실측 결과(BigQuery Property Graph)에 근거해 답하고 결과에 없는 내용은 단정하지 않음": "Answer grounded in BigQuery Property Graph / ISO GQL tool results without unverified speculation",
}

SUBSTRING_KO_TO_EN = [
    (" (위약금 면제 특례 규정)", " (Statutory Exemption Clauses)"),
    ("(위약금 면제 특례 규정)", "(Statutory Exemption Clauses)"),
    (" (차액정산금)", " (subsidy difference clawback)"),
    ("(차액정산금)", "(subsidy difference clawback)"),
]


def localize_en_str(val: str) -> str:
    if not val or not isinstance(val, str):
        return val
    if val in EXACT_KO_TO_EN:
        return EXACT_KO_TO_EN[val]
    out = val
    for ko_sub, en_sub in SUBSTRING_KO_TO_EN:
        if ko_sub in out:
            out = out.replace(ko_sub, en_sub)
    return out


def localize_en_obj(obj: Any) -> Any:
    """Recursively translates known Korean strings in dicts/lists/strings into English."""
    if isinstance(obj, str):
        return localize_en_str(obj)
    if isinstance(obj, list):
        return [localize_en_obj(x) for x in obj]
    if isinstance(obj, dict):
        return {localize_en_str(k) if isinstance(k, str) else k: localize_en_obj(v) for k, v in obj.items()}
    return obj


def is_english_mode(lang: str = None, text: str = None) -> bool:
    import os
    if lang:
        return str(lang).lower() == "en"
    env_lang = os.environ.get("STARTER_LANG", "").lower()
    if env_lang == "en":
        return True
    if env_lang == "ko":
        return False
    if text and isinstance(text, str) and text.strip():
        return not bool(re.search(r"[\uac00-\ud7a3]", text))
    return False
