# Copyright (c) 2026 Sean Jung (seanjung@google.com). All Rights Reserved.
# Non-Commercial Use Only: Methodology & Docs under CC BY-NC-ND 4.0; Source Code under PolyForm Noncommercial License 1.0.0.
# Commercial use, paid consulting/SI/PoC delivery, or production deployment requires prior written permission from seanjung@google.com.

# -*- coding: utf-8 -*-
"""Free-text sentence feedback → Context Graph signal (GOAL-285 · REQ-4/REQ-6).

Users rarely express a domain correction with one of 6–8 fixed reason chips. This module turns the sentence a user
types under an agent answer (with or without 👍/👎) into a structured Context Graph signal:

    Sentence ─▶ polarity (POSITIVE_REINFORCE · CORRECTION_REQUIRED · RULE_ADDITION · TERM_CLARIFICATION · ROUTE_OVERRIDE)
             ─▶ tacit type (T1 예외 규칙 · T2 판단 기준 · T3 현장 용어·동의어 · T4 정책값 해석 · T5 안내 화법/골든 답변 프레임 · KC_META)
             ─▶ reason code · target entities / rule id · proposed rule statement
             ─▶ L2 Candidate (proposed patch) + Regression CQ (the question that must keep passing after the fix)

The parser is deterministic (keyword + pattern rules, KO/EN), runs in microseconds and needs no network, so the
feedback shows up in the Context Graph the instant it is submitted. An LLM can refine the candidate later (SME review),
but the graph never waits for it. Standard library only — the same file ships in the starter
(``src/aos/sentence_feedback.py``) and the notebook lab (``lab/sentence_feedback.py``).
"""
from __future__ import annotations

import hashlib
import re
from typing import Any, Dict, Iterable, List, Optional, Tuple

PARSER_VERSION = "sf-1.0"

FEEDBACK_MODES = ("SENTENCE", "THUMBS_CHIP", "HYBRID")
POLARITIES = ("POSITIVE_REINFORCE", "CORRECTION_REQUIRED", "RULE_ADDITION", "TERM_CLARIFICATION", "ROUTE_OVERRIDE")
REASON_CODES = ("MISSING_RULE", "WRONG_POLICY_VALUE", "UNKNOWN_TERM", "WRONG_ROUTE", "ANSWER_PHRASING", "STALE_WIKI", "TOOL_ERROR")
# Context Graph tacit-knowledge taxonomy of the GOAL-283~285 master spec (§2·§5): T1 실행 경계 · T2 산식/임계치 ·
# T3 예외 정책 · T4 약어/동의어 · T5 골든 답변 프레임 · KC_META. ``legacy_tacit_type`` keeps the older studio / Lab 3
# codes (src/context_graph/schema.py: T1 예외 규칙 · T2 판단 기준 · T3 현장 용어 · T4 정책값 해석 · T5 안내 화법).
TACIT_TYPES: Dict[str, Dict[str, str]] = {
    "T1": {"ko": "실행 경계", "en": "Execution boundary"},
    "T2": {"ko": "산식 · 임계치", "en": "Formula / threshold"},
    "T3": {"ko": "예외 정책", "en": "Exception policy"},
    "T4": {"ko": "약어 · 동의어", "en": "Abbreviation / synonym"},
    "T5": {"ko": "골든 답변 프레임", "en": "Golden answer frame"},
    "KC_META": {"ko": "메타 규칙", "en": "Meta rule"},
}
LEGACY_TACIT_TYPES: Dict[str, Dict[str, str]] = {
    "T1": {"ko": "예외 규칙", "en": "Exception rule"},
    "T2": {"ko": "판단 기준", "en": "Decision criterion"},
    "T3": {"ko": "현장 용어 · 동의어", "en": "Field term / synonym"},
    "T4": {"ko": "정책값 해석", "en": "Policy value interpretation"},
    "T5": {"ko": "안내 화법", "en": "Answer phrasing"},
}
CATEGORY_TO_TACIT = {"boundary": "T1", "value": "T2", "criterion": "T2", "exception": "T3", "term": "T4", "phrasing": "T5", "meta": "KC_META"}
CATEGORY_TO_LEGACY = {"boundary": "T2", "value": "T4", "criterion": "T2", "exception": "T1", "term": "T3", "phrasing": "T5", "meta": "T5"}
TACIT_TO_LEGACY = {"T1": "T2", "T2": "T4", "T3": "T1", "T4": "T3", "T5": "T5", "KC_META": "T5"}
POLARITY_LABELS: Dict[str, Dict[str, str]] = {
    "POSITIVE_REINFORCE": {"ko": "긍정 강화", "en": "Positive reinforcement"},
    "CORRECTION_REQUIRED": {"ko": "정정 필요", "en": "Correction required"},
    "RULE_ADDITION": {"ko": "규칙 추가", "en": "Rule addition"},
    "TERM_CLARIFICATION": {"ko": "용어 명확화", "en": "Term clarification"},
    "ROUTE_OVERRIDE": {"ko": "경로 변경", "en": "Route override"},
}
REASON_LABELS: Dict[str, Dict[str, str]] = {
    "MISSING_RULE": {"ko": "규칙 누락", "en": "Missing rule"},
    "WRONG_POLICY_VALUE": {"ko": "정책값 오류", "en": "Wrong policy value"},
    "UNKNOWN_TERM": {"ko": "모르는 용어", "en": "Unknown term"},
    "WRONG_ROUTE": {"ko": "잘못된 경로", "en": "Wrong route"},
    "ANSWER_PHRASING": {"ko": "답변 화법", "en": "Answer phrasing"},
    "STALE_WIKI": {"ko": "오래된 위키", "en": "Stale wiki"},
    "TOOL_ERROR": {"ko": "도구 오류", "en": "Tool error"},
}
AGENT_SURFACES = ("wiki_agent", "bqg_agent", "fde_workflow_agent", "hybrid_agent")
_SURFACE_ALIASES = {
    "wiki": "wiki_agent", "wiki_agent": "wiki_agent",
    "gql": "bqg_agent", "graph": "bqg_agent", "bqg": "bqg_agent", "bqg_agent": "bqg_agent", "spanner": "bqg_agent",
    "workflow": "fde_workflow_agent", "fde": "fde_workflow_agent", "fde_workflow_agent": "fde_workflow_agent",
    "hybrid": "hybrid_agent", "hybrid_agent": "hybrid_agent",
}
PATCH_OPS = {
    "T1": "SET_EXECUTION_BOUNDARY", "T2": "UPDATE_FORMULA_THRESHOLD", "T3": "ADD_EXCEPTION_POLICY", "T4": "ADD_SYNONYM",
    "T5": "PIN_ANSWER_FRAME", "KC_META": "ADD_META_RULE",
}
_EXPLICIT_T = re.compile(r"(?<![A-Za-z0-9])(T[1-5]|KC[_-]META)(?![A-Za-z0-9])", re.I)

# --------------------------------------------------------------------------- keyword lexicons (lower-cased match)
_NEG = ("틀렸", "틀린", "틀립", "틀려", "잘못", "아닙니다", "아니라", "아니고", "오류", "다릅니다", "다르", "정정", "부정확", "누락", "빠졌", "빠져",
        "없습니다", "모자", "부족", "엉뚱", "않습니다", "않아", "않음", "않고", "안 맞", "안맞",
        "wrong", "incorrect", "inaccurate", "not right", "isn't", "is not", "missing", "mistake", "error in", "doesn't", "does not",
        "should be", "should have", "outdated", "left out")
_POS = ("좋습니다", "좋아요", "좋네", "좋은 답", "정확합니다", "정확해요", "정확하게", "맞습니다", "맞아요", "훌륭", "도움이", "완벽", "깔끔", "명확합니다",
        "그대로 유지", "이대로", "good", "great", "correct", "accurate", "helpful", "perfect", "exactly", "well done", "keep this", "clear answer")
_ROUTE = ("그래프로", "그래프 에이전트", "위키로", "위키 에이전트", "워크플로우로", "워크플로우 에이전트", "에이전트로", "에이전트가 답", "라우팅", "경로로",
          "graph agent", "wiki agent", "workflow agent", "should route", "route to", "routed to", "use the graph", "use the wiki", "routing")
_TERM = ("뜻", "의미", "동의어", "약어", "약자", "줄임말", "같은 말", "라고도", "라고 부", "용어", "말합니다",
         "means", "meaning", "synonym", "abbreviation", "stands for", "also called", "aka", "term ", "refers to")
_RULE = ("추가", "규칙", "예외", "해야", "필요합니다", "필요해요", "반드시", "꼭 ", "제외", "경우에는", "경우 ", "조건", "규정",
         "must", "should", "rule", "add ", "except", "unless", "only if", "required", "need to", "policy")
_EXC = ("예외", "단,", "단 ", "제외", "경우에는", "경우에만", "한해", "한하여", "except", "unless", "only if", "only when", "exception")
_CRIT = ("기준", "판단", "조건", "이상", "이하", "초과", "미만", "이내", "넘으면", "충족", "criteria", "criterion", "threshold", "at least",
         "more than", "less than", "within", "decide", "eligible", "eligibility")
_VALUE = ("금액", "요율", "비율", "값", "한도", "기간", "개월", "만원", "원", "%", "일", "년", "amount", "rate", "value", "limit", "period",
          "months", "days", "fee", "price", "won", "krw")
_PHRASE = ("안내", "말투", "화법", "표현", "문장", "친절", "먼저 말", "요약", "형식", "순서로", "phrasing", "tone", "wording", "format", "polite",
           "summarize", "bullet", "first say", "explain")
_BOUNDARY = ("먼저 확인", "먼저 ", "전에", "하지 말", "하면 안", "금지", "범위", "권한", "상담원 연결", "상담사 연결", "에스컬레이션", "넘기", "답하지",
             "확인 후", "before ", "first check", "do not", "don't", "never", "scope", "escalate", "hand off", "out of scope", "not allowed")
_META = ("항상", "모든 답변", "모든 질문", "출처", "인용", "근거를", "앞으로", "매번", "always", "every answer", "every time", "cite", "source",
         "in general", "from now on")
_STALE = ("오래된", "옛날", "최신", "개정", "바뀌", "변경되", "outdated", "stale", "old version", "latest", "revised", "changed")
_TOOL = ("에러", "실패", "타임아웃", "시간 초과", "응답이 없", "멈췄", "error", "failed", "timeout", "timed out", "crash", "no response")

_PARTICLES = ("으로는", "에서는", "이라고", "라고는", "에게는", "까지는", "부터는", "으로", "에서", "에게", "까지", "부터", "라고", "처럼", "보다",
              "이나", "이며", "이고", "은", "는", "이", "가", "을", "를", "에", "의", "로", "와", "과", "도", "만", "요")
_STOP = {"답변", "답변은", "답변에서", "이번", "그리고", "하지만", "그런데", "때문", "정도", "부분", "내용", "경우", "경우에는", "합니다", "입니다",
         "있습니다", "없습니다", "됩니다", "해야", "해주세요", "주세요", "그대로", "모든", "항상", "the", "and", "for", "that", "this", "with",
         "should", "must", "answer", "please", "also", "from", "into", "are", "was", "were", "not", "but", "you", "your", "its", "it's"}
_QUOTED = re.compile(r"[\"“”'‘’「『]([^\"“”'‘’」』]{1,60})[\"“”'‘’」』]")
_NUM_UNIT = re.compile(r"\d[\d,\.]*\s*(?:%|퍼센트|만\s?원|천\s?원|원|개월|일|년|회|명|GB|MB|days?|months?|years?|KRW|won|times)", re.I)
_RULE_ID = re.compile(r"(?<![A-Za-z0-9])((?:RULE|POL|WCQ|WF|CQ|R|G|W|C)[-_]?(?:G)?[-_]?\d{1,4})(?![A-Za-z0-9])")
_TERM_PAIR = re.compile(r"([가-힣A-Za-z0-9]{2,20})(?:은|는|이란|란)\s+([가-힣A-Za-z0-9]{2,20}?)(?:이라고도|라고도|와 같은|과 같은|의 약어|의 줄임말|을 뜻|를 뜻|을 의미|를 의미)"
                        r"|([A-Za-z][A-Za-z0-9\- ]{1,30}?)\s+(?:means|stands for|is also called|is short for)\s+([A-Za-z][A-Za-z0-9\- ]{1,30})")
_WORD = re.compile(r"[가-힣A-Za-z][가-힣A-Za-z0-9_\-]{1,}")
_LEADS = re.compile(r"^\s*(?:이\s*답변(?:은|에서|에는)?|답변(?:은|에서|에는)?|this answer|the answer)\s*[,:]?\s*", re.I)


def _hits(text: str, words: Iterable[str]) -> List[str]:
    return [w.strip() for w in words if w and w in text]


def normalize_surface(agent: Any) -> str:
    """Maps lab / starter agent names (wiki · gql · graph · workflow · hybrid) to a Context Graph agent surface."""
    return _SURFACE_ALIASES.get(str(agent or "").strip().lower(), "wiki_agent")


def normalize_rating(rating: Any) -> str:
    r = str(rating or "").strip().lower()
    if r in ("up", "like", "good", "👍", "positive", "+1", "thumbs_up"):
        return "up"
    if r in ("down", "dislike", "bad", "👎", "negative", "-1", "thumbs_down"):
        return "down"
    return ""


def feedback_mode_of(rating: Any, sentence: Any) -> str:
    has_s = bool(str(sentence or "").strip())
    has_r = bool(normalize_rating(rating))
    if has_s and has_r:
        return "HYBRID"
    return "SENTENCE" if has_s else "THUMBS_CHIP"


def _strip_particle(w: str) -> str:
    for p in _PARTICLES:
        if len(w) > len(p) + 1 and w.endswith(p):
            return w[: -len(p)]
    return w


def extract_entities(sentence: str, query: str = "", answer: str = "", known_terms: Optional[Iterable[str]] = None, limit: int = 8) -> List[str]:
    """Quoted phrases · numbers with units · known KC terms · words the sentence shares with the question/answer."""
    out: List[str] = []

    def add(x: str) -> None:
        x = x.strip(" .,;:!?()[]")
        if 1 < len(x) <= 60 and x not in out and x.lower() not in _STOP:
            out.append(x)
    for m in _QUOTED.findall(sentence):
        add(m)
    for mt in _TERM_PAIR.finditer(sentence):  # "A는 B라고도 부릅니다" · "A means B"
        for g in mt.groups():
            if g:
                add(_strip_particle(g.strip()))
    for m in _NUM_UNIT.findall(sentence):
        add(re.sub(r"\s+", "", m) if re.search(r"[가-힣]", m) else m)
    low = sentence.lower()
    for term in known_terms or []:
        t = str(term or "").strip()
        if len(t) >= 2 and t.lower() in low:
            add(t)
    ctx = f"{query}\n{answer}".lower()
    for w in _WORD.findall(sentence):
        base = _strip_particle(w)
        if len(base) >= 2 and base.lower() not in _STOP and base.lower() in ctx:
            add(base)
    return out[:limit]


def _first_sentence(text: str, n: int = 160) -> str:
    t = re.sub(r"\s+", " ", str(text or "")).strip()
    m = re.split(r"(?<=[.!?。])\s|(?<=다\.)\s|\n", t, maxsplit=1)
    return (m[0] if m else t)[:n]


def parse_sentence_feedback_to_cg_signal(sentence: Any, query: Any = "", answer: Any = "", agent_surface: Any = "", *,
                                         rating: Any = "", reason_code: Any = "", lang: str = "ko",
                                         known_terms: Optional[Iterable[str]] = None) -> Dict[str, Any]:
    """Structures one piece of feedback (sentence and/or 👍/👎 + chip) into an L1 FeedbackSignal ``parsed_intent``.

    Returns ``{feedback_mode, raw_sentence, rating, agent_surface, parsed_intent: {polarity, tacit_type, reason_code,
    extracted_entities, target_rule_id, proposed_rule_statement, regression_cq, confidence, signals, labels}}``.
    A 👍/👎 without a sentence is still a valid signal (THUMBS_CHIP); polarity is inferred from the sentence when the
    user did not pick a thumb.
    """
    en = lang == "en"
    raw = re.sub(r"\s+", " ", str(sentence or "")).strip()[:2000]
    q = str(query or "").strip()
    a = str(answer or "").strip()
    rate = normalize_rating(rating)
    surface = normalize_surface(agent_surface)
    mode = feedback_mode_of(rate, raw)
    low = raw.lower()
    sig: Dict[str, List[str]] = {
        "negative": _hits(low, _NEG), "positive": _hits(low, _POS), "route": _hits(low, _ROUTE), "term": _hits(low, _TERM),
        "rule": _hits(low, _RULE), "exception": _hits(low, _EXC), "criterion": _hits(low, _CRIT), "value": _hits(low, _VALUE),
        "phrasing": _hits(low, _PHRASE), "boundary": _hits(low, _BOUNDARY), "meta": _hits(low, _META), "stale": _hits(low, _STALE), "tool": _hits(low, _TOOL),
    }
    nums = _NUM_UNIT.findall(raw)
    # "정확하지 않습니다" contains a positive stem — any negative cue cancels the positive ones.
    positive = bool(sig["positive"]) and not sig["negative"]

    # ---- polarity
    if not raw:
        polarity = "POSITIVE_REINFORCE" if rate == "up" else "CORRECTION_REQUIRED"
    elif sig["route"] and (sig["negative"] or rate == "down" or any(k in low for k in ("대신", "instead", "should", "해야"))):
        polarity = "ROUTE_OVERRIDE"
    elif sig["term"] and not positive and len(sig["term"]) >= len(sig["exception"]):
        polarity = "TERM_CLARIFICATION"
    elif sig["negative"] or (rate == "down" and not positive):
        polarity = "RULE_ADDITION" if (sig["rule"] and not nums and not sig["value"] and len(sig["rule"]) > len(sig["negative"])) else "CORRECTION_REQUIRED"
    elif sig["rule"] or sig["exception"] or sig["criterion"] or sig["meta"]:
        polarity = "RULE_ADDITION" if rate != "up" or not positive else "POSITIVE_REINFORCE"
    elif positive or rate == "up":
        polarity = "POSITIVE_REINFORCE"
    else:
        polarity = "CORRECTION_REQUIRED" if rate == "down" else "RULE_ADDITION"

    # ---- tacit type: score internal categories (tie → listed order), then map to the spec taxonomy (T1~T5 · KC_META)
    cat_score = {
        "exception": 5 * len(sig["exception"]),
        "term": 3 * len(sig["term"]) if polarity == "TERM_CLARIFICATION" else len(sig["term"]),
        "value": 2 * len(nums) + (len(sig["value"]) if nums else 0),
        "criterion": 2 * len(sig["criterion"]),
        "boundary": 2 * len(sig["boundary"]) + (3 if polarity == "ROUTE_OVERRIDE" else 0),
        "phrasing": 2 * len(sig["phrasing"]) + (3 if polarity == "POSITIVE_REINFORCE" else 0),
        "meta": 2 * len(sig["meta"]),
    }
    cat = max(cat_score, key=lambda k: (cat_score[k], -list(cat_score).index(k)))
    if cat_score[cat] == 0:
        cat = "exception" if polarity in ("CORRECTION_REQUIRED", "RULE_ADDITION") else ("term" if polarity == "TERM_CLARIFICATION" else "phrasing")
    tacit = CATEGORY_TO_TACIT[cat]
    explicit = _EXPLICIT_T.search(raw)
    if explicit:  # "…예외 규칙(T3)…" — the user named the type herself
        tacit = explicit.group(1).upper().replace("-", "_")
        cat = next((c for c, t in CATEGORY_TO_TACIT.items() if t == tacit), cat)
    legacy = CATEGORY_TO_LEGACY[cat]

    # ---- reason code (a chip the user picked wins)
    chip = str(reason_code or "").strip().upper()
    if chip in REASON_CODES:
        reason = chip
    elif polarity == "POSITIVE_REINFORCE":
        reason = ""
    elif sig["tool"]:
        reason = "TOOL_ERROR"
    elif sig["stale"]:
        reason = "STALE_WIKI"
    elif polarity == "ROUTE_OVERRIDE":
        reason = "WRONG_ROUTE"
    elif polarity == "TERM_CLARIFICATION" or cat == "term":
        reason = "UNKNOWN_TERM"
    elif cat == "value":
        reason = "WRONG_POLICY_VALUE"
    elif cat == "phrasing":
        reason = "ANSWER_PHRASING"
    else:
        reason = "MISSING_RULE"

    entities = extract_entities(raw, q, a, known_terms) if raw else []
    m = _RULE_ID.search(raw) or _RULE_ID.search(q)
    target_rule = m.group(1).upper() if m else ""
    statement = _LEADS.sub("", raw).strip()
    if not statement:
        statement = ((f"Keep the answer frame for: {q[:120]}" if en else f"이 질문의 답변 프레임 유지: {q[:120]}") if rate == "up"
                     else (f"Answer needs review ({REASON_LABELS.get(reason, {}).get('en', reason)}): {q[:120]}" if en
                           else f"답변 검토 필요 ({REASON_LABELS.get(reason, {}).get('ko', reason)}): {q[:120]}"))
    elif polarity == "POSITIVE_REINFORCE" and a:
        statement = (f"Golden answer frame — {statement} · reference: {_first_sentence(a)}" if en
                     else f"골든 답변 프레임 — {statement} · 기준 답변: {_first_sentence(a)}")
    expected = [e for e in entities if _NUM_UNIT.fullmatch(e) or e in nums][:4] or entities[:4]
    regression = {
        "question": q[:400] or (f"Does the agent apply: {statement[:120]}?" if en else f"에이전트가 다음을 반영하는가: {statement[:120]}?"),
        "expected_facts": expected,
        "must_reflect": statement[:400],
        "kind": "PIN" if polarity == "POSITIVE_REINFORCE" else "FIX",
    }
    n_cats = sum(1 for k in ("route", "term", "rule", "exception", "criterion", "phrasing", "meta", "negative", "positive") if sig[k])
    conf = 0.35 if not raw else min(0.95, 0.5 + 0.08 * n_cats + (0.07 if entities else 0) + (0.05 if rate else 0) + (0.05 if len(raw) >= 25 else -0.1))
    flat = sorted({w for v in sig.values() for w in v})[:12]
    k = "en" if en else "ko"
    return {
        "feedback_mode": mode, "raw_sentence": raw, "rating": rate, "agent_surface": surface, "parser": PARSER_VERSION,
        "parsed_intent": {
            "polarity": polarity, "tacit_type": tacit, "legacy_tacit_type": legacy, "reason_code": reason, "extracted_entities": entities,
            "target_rule_id": target_rule, "proposed_rule_statement": statement[:600], "regression_cq": regression,
            "confidence": round(conf, 2), "signals": flat,
            "labels": {"polarity": POLARITY_LABELS[polarity][k], "tacit_type": TACIT_TYPES[tacit][k], "legacy_tacit_type": LEGACY_TACIT_TYPES[legacy][k],
                       "reason_code": REASON_LABELS.get(reason, {}).get(k, "")},
        },
    }


def candidate_from_signal(signal: Dict[str, Any], *, feedback_id: str, run_id: str = "", lang: str = "ko") -> Optional[Dict[str, Any]]:
    """L2 Candidate (proposed patch + regression CQ) for a feedback signal; ``None`` for a bare 👍 (nothing to change)."""
    pi = signal.get("parsed_intent") or {}
    if not signal.get("raw_sentence") and signal.get("rating") == "up":
        return None
    tacit = pi.get("tacit_type") or "T3"
    statement = str(pi.get("proposed_rule_statement") or "")
    target = pi.get("target_rule_id") or (pi.get("extracted_entities") or [""])[0] or signal.get("agent_surface", "")
    op = PATCH_OPS.get(tacit, "ADD_EXCEPTION_POLICY")
    if pi.get("polarity") == "ROUTE_OVERRIDE":
        op = "SET_ROUTE"
    cid = "cand-" + hashlib.sha1(f"{feedback_id}|{statement}".encode("utf-8")).hexdigest()[:12]
    title = statement[:48] + ("…" if len(statement) > 48 else "")
    return {
        "candidate_id": cid, "feedback_id": feedback_id, "run_id": run_id, "tacit_type": tacit,
        "legacy_tacit_type": pi.get("legacy_tacit_type") or TACIT_TO_LEGACY.get(tacit, "T1"), "polarity": pi.get("polarity"),
        "reason_code": pi.get("reason_code", ""), "title": title,
        "proposed_patch": {"op": op, "target": str(target)[:120], "statement": statement[:600], "agent_surface": signal.get("agent_surface")},
        "regression_cq": pi.get("regression_cq") or {}, "confidence": pi.get("confidence", 0.5),
        "status": "PENDING", "needs_sme_detail": not signal.get("raw_sentence"),
    }


def summarize(signal: Dict[str, Any], lang: str = "ko") -> str:
    """One-line human summary used in toasts and the graph inspector."""
    pi = signal.get("parsed_intent") or {}
    lab = pi.get("labels") or {}
    ents = ", ".join(pi.get("extracted_entities") or [])[:80]
    head = f"{lab.get('polarity', '')} · {pi.get('tacit_type', '')} {lab.get('tacit_type', '')}"
    if pi.get("reason_code"):
        head += f" · {pi['reason_code']}"
    return head + (f" · {ents}" if ents else "")


def explain_pipeline(lang: str = "ko") -> List[Tuple[str, str]]:
    """The demo stages shown in the UI: input → L0 → L1 → L2 → SME → ChangeSet → graph."""
    if lang == "en":
        return [("input", "Feedback input"), ("l0", "L0 event"), ("l1", "L1 signal (sentence structured)"), ("l2", "L2 candidate + regression CQ"),
                ("sme", "SME review"), ("changeset", "ChangeSet"), ("graph", "Reflected in the graph")]
    return [("input", "피드백 입력"), ("l0", "L0 이벤트"), ("l1", "L1 신호 (문장 구조화)"), ("l2", "L2 후보 + 회귀 CQ"),
            ("sme", "SME 검토"), ("changeset", "ChangeSet"), ("graph", "그래프 반영")]
