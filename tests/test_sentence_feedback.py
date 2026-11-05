# -*- coding: utf-8 -*-
"""Sentence feedback → Context Graph signal parser (GOAL-285). Offline, deterministic.

Run from agentic-ontology-starter/:  python3 -m unittest tests.test_sentence_feedback -v
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.aos import sentence_feedback as sf  # noqa: E402

Q = "공시지원금 받은 뒤 해지하면 위약금은 얼마인가요?"
A = "위약금은 지원금의 25%입니다."


def intent(sentence, rating="", reason="", agent="wiki", lang="ko", q=Q, a=A):
    return sf.parse_sentence_feedback_to_cg_signal(sentence, q, a, agent, rating=rating, reason_code=reason, lang=lang)


class ModeAndSurface(unittest.TestCase):
    def test_modes(self):
        self.assertEqual(intent("좋아요")["feedback_mode"], "SENTENCE")
        self.assertEqual(intent("", rating="up")["feedback_mode"], "THUMBS_CHIP")
        self.assertEqual(intent("틀렸어요", rating="down")["feedback_mode"], "HYBRID")

    def test_surfaces(self):
        self.assertEqual(sf.normalize_surface("gql"), "bqg_agent")
        self.assertEqual(sf.normalize_surface("graph"), "bqg_agent")
        self.assertEqual(sf.normalize_surface("workflow"), "fde_workflow_agent")
        self.assertEqual(sf.normalize_surface("hybrid"), "hybrid_agent")
        self.assertEqual(sf.normalize_surface("wiki"), "wiki_agent")

    def test_rating_aliases(self):
        self.assertEqual(sf.normalize_rating("👍"), "up")
        self.assertEqual(sf.normalize_rating("DOWN"), "down")
        self.assertEqual(sf.normalize_rating("maybe"), "")


class Polarity(unittest.TestCase):
    def p(self, *a, **k):
        return intent(*a, **k)["parsed_intent"]

    def test_positive_without_thumb(self):
        p = self.p("정확하고 깔끔한 답변입니다. 이대로 유지해 주세요")
        self.assertEqual(p["polarity"], "POSITIVE_REINFORCE")
        self.assertEqual(p["tacit_type"], "T5")
        self.assertEqual(p["reason_code"], "")
        self.assertIn("골든 답변 프레임", p["proposed_rule_statement"])

    def test_negated_positive_is_correction(self):
        p = self.p("정확하지 않습니다. 예외 조건이 빠졌어요")
        self.assertNotEqual(p["polarity"], "POSITIVE_REINFORCE")

    def test_policy_value_correction(self):
        p = self.p("위약금 요율이 틀렸습니다. 25%가 아니라 30%입니다", rating="down")
        self.assertEqual(p["polarity"], "CORRECTION_REQUIRED")
        self.assertEqual(p["tacit_type"], "T2")
        self.assertEqual(p["legacy_tacit_type"], "T4")
        self.assertEqual(p["reason_code"], "WRONG_POLICY_VALUE")
        self.assertIn("30%", p["extracted_entities"])
        self.assertIn("30%", p["regression_cq"]["expected_facts"])
        self.assertEqual(p["regression_cq"]["question"], Q)
        self.assertEqual(p["regression_cq"]["kind"], "FIX")

    def test_term(self):
        p = self.p("선택약정은 약정할인이라고도 부릅니다")
        self.assertEqual(p["polarity"], "TERM_CLARIFICATION")
        self.assertEqual(p["tacit_type"], "T4")
        self.assertEqual(p["legacy_tacit_type"], "T3")
        self.assertEqual(p["reason_code"], "UNKNOWN_TERM")
        self.assertIn("선택약정", p["extracted_entities"])
        self.assertIn("약정할인", p["extracted_entities"])

    def test_route(self):
        p = self.p("이 질문은 위키 말고 그래프 에이전트로 답해야 합니다")
        self.assertEqual(p["polarity"], "ROUTE_OVERRIDE")
        self.assertEqual(p["reason_code"], "WRONG_ROUTE")

    def test_rule_addition_with_rule_id(self):
        p = self.p("R-12 규칙에 예외를 추가해야 합니다: 군 입대는 제외")
        self.assertEqual(p["polarity"], "RULE_ADDITION")
        self.assertEqual(p["tacit_type"], "T3")
        self.assertEqual(p["legacy_tacit_type"], "T1")
        self.assertEqual(p["target_rule_id"], "R-12")

    def test_spec_example_sentence(self):
        # 기획서 §5.1 예시 2 — 옵션 선택 없이 문장만 입력
        p = self.p("공시지원금 위약금 계산 시 18개월 이상 유지 고객은 잔여 할부금 면제 예외 규칙(T3)을 먼저 확인해야 함")
        self.assertEqual(p["tacit_type"], "T3")
        self.assertEqual(p["labels"]["tacit_type"], "예외 정책")
        self.assertIn(p["polarity"], ("RULE_ADDITION", "CORRECTION_REQUIRED"))
        self.assertIn("18개월", p["extracted_entities"])
        self.assertEqual(p["target_rule_id"], "")
        self.assertIn("18개월", p["regression_cq"]["expected_facts"])
        p = self.p("공시지원금 위약금 계산 시 18개월 이상 유지 고객은 잔여 할부금 면제 예외 규칙을 먼저 확인해야 함")
        self.assertEqual(p["tacit_type"], "T3")

    def test_boundary(self):
        p = self.p("요금 분쟁은 에이전트가 답하지 말고 상담원 연결로 넘겨야 합니다")
        self.assertEqual(p["tacit_type"], "T1")

    def test_meta(self):
        p = self.p("항상 근거 위키 페이지 출처를 인용해 주세요")
        self.assertEqual(p["tacit_type"], "KC_META")

    def test_chip_wins(self):
        p = self.p("요금 안내가 이상해요", rating="down", reason="STALE_WIKI")
        self.assertEqual(p["reason_code"], "STALE_WIKI")

    def test_english(self):
        p = self.p("The fee is wrong, it should be 30% not 25%", lang="en")
        self.assertEqual(p["polarity"], "CORRECTION_REQUIRED")
        self.assertEqual(p["tacit_type"], "T2")
        self.assertEqual(p["labels"]["tacit_type"], "Formula / threshold")
        p = self.p("SIM-only means a plan without a device", lang="en")
        self.assertEqual(p["tacit_type"], "T4")
        self.assertIn("SIM-only", p["extracted_entities"])

    def test_thumbs_only(self):
        up = self.p("", rating="up")
        self.assertEqual(up["polarity"], "POSITIVE_REINFORCE")
        down = self.p("", rating="down", reason="MISSING_RULE")
        self.assertEqual(down["polarity"], "CORRECTION_REQUIRED")
        self.assertEqual(down["reason_code"], "MISSING_RULE")
        self.assertLess(down["confidence"], 0.5)

    def test_all_values_in_enums(self):
        for s in ("", "좋아요", "틀렸어요", "뜻이 뭐죠", "에러가 났어요", "최신 개정 내용이 아닙니다"):
            for r in ("", "up", "down"):
                p = self.p(s, rating=r)
                self.assertIn(p["polarity"], sf.POLARITIES)
                self.assertIn(p["tacit_type"], sf.TACIT_TYPES)
                self.assertIn(p["reason_code"], sf.REASON_CODES + ("",))
                self.assertTrue(0 <= p["confidence"] <= 1)

    def test_tool_and_stale(self):
        self.assertEqual(self.p("도구 호출에서 에러가 났어요")["reason_code"], "TOOL_ERROR")
        self.assertEqual(self.p("최신 개정 내용이 아닙니다, 위키가 오래된 것 같아요")["reason_code"], "STALE_WIKI")


class Candidate(unittest.TestCase):
    def test_bare_up_has_no_candidate(self):
        self.assertIsNone(sf.candidate_from_signal(intent("", rating="up"), feedback_id="fb-1"))

    def test_candidate_patch(self):
        sig = intent("선택약정은 약정할인이라고도 부릅니다", agent="gql")
        c = sf.candidate_from_signal(sig, feedback_id="fb-1", run_id="run-1")
        self.assertEqual(c["proposed_patch"]["op"], "ADD_SYNONYM")
        self.assertEqual(c["proposed_patch"]["agent_surface"], "bqg_agent")
        self.assertEqual(c["status"], "PENDING")
        self.assertEqual(c["run_id"], "run-1")
        self.assertTrue(c["candidate_id"].startswith("cand-"))
        self.assertEqual(c, sf.candidate_from_signal(sig, feedback_id="fb-1", run_id="run-1"))  # deterministic id

    def test_route_patch(self):
        c = sf.candidate_from_signal(intent("그래프 에이전트로 답해야 합니다"), feedback_id="fb-2")
        self.assertEqual(c["proposed_patch"]["op"], "SET_ROUTE")

    def test_down_without_sentence_needs_detail(self):
        c = sf.candidate_from_signal(intent("", rating="down"), feedback_id="fb-3")
        self.assertTrue(c["needs_sme_detail"])

    def test_summary_and_stages(self):
        s = sf.summarize(intent("위약금 요율이 틀렸습니다. 25%가 아니라 30%입니다"))
        self.assertIn("T2", s)
        self.assertEqual(len(sf.explain_pipeline("ko")), 7)
        self.assertEqual(sf.explain_pipeline("en")[0][0], "input")


if __name__ == "__main__":
    unittest.main()
