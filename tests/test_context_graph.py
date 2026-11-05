# -*- coding: utf-8 -*-
"""Starter Context Graph store + routes (GOAL-285). Offline: GCS reads/writes are replaced by an in-memory bucket.

Run from agentic-ontology-starter/:  python3 -m unittest tests.test_context_graph -v
"""
from __future__ import annotations

import json
import sys
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.aos import context_graph as cg  # noqa: E402
from src.aos.ws import WsError  # noqa: E402

WS = {"ws_id": "ws-20261105-abcdef", "lang": "ko", "env": {"bucket": "test-bucket", "project": "p-test-1"}}
Q = "공시지원금 받은 뒤 해지하면 위약금은 얼마인가요?"
A = "위약금은 지원금의 25%입니다."


class FakeBucket:
    """Replaces ws.get_text / ws.put_json inside context_graph."""

    def __init__(self):
        self.objects, self.writes, self.fail_read = {}, 0, False

    def get_text(self, log, bucket, name):
        if self.fail_read:
            return 500, "backend error"
        key = f"{bucket}/{name}"
        if key not in self.objects:
            return 404, f"No such object: {key}"
        return 200, self.objects[key]

    def put_json(self, log, bucket, name, obj):
        self.objects[f"{bucket}/{name}"] = json.dumps(obj, ensure_ascii=False)
        self.writes += 1
        return {"status": "SUCCESS"}

    def graph(self):
        return json.loads(self.objects[f"test-bucket/{cg.graph_name(WS['ws_id'])}"])

    def patch(self):
        return mock.patch.multiple(cg, get_text=self.get_text, put_json=self.put_json)


def agent_result(agent="wiki"):
    return {"agent": agent, "status": "GROUNDED", "question": Q, "answer": A, "citations": ["W-01"], "graph_engine": "bigquery",
            "steps": [{"action": "read_wiki", "thought": "read policy", "pages": ["W-01"]},
                      {"action": "gql", "thought": "count", "query": "GRAPH g MATCH (n) RETURN n", "rows": [{"n": 1}], "row_count": 1, "ms": 12},
                      {"action": "answer", "thought": "done"}],
            "telemetry": {"total_ms": 900, "steps": 3, "tokens_in": 10, "tokens_out": 5, "model": "m"}}


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.b = FakeBucket()
        self.p = self.b.patch()
        self.p.start()

    def tearDown(self):
        self.p.stop()

    def test_record_run_writes_l1_run_and_l0_events(self):
        out = cg.record_run(WS, agent_result("graph"))
        self.assertTrue(out["cg_recorded"])
        self.assertTrue(out["cg_run_id"].startswith("run-"))
        self.assertEqual(out["agent_surface"], "bqg_agent")
        g = self.b.graph()
        self.assertEqual(len(g["runs"]), 1)
        self.assertEqual(g["runs"][0]["run_id"], out["cg_run_id"])
        kinds = [e["kind"] for e in g["events"]]
        self.assertEqual(kinds[0], "question")
        self.assertEqual(kinds[-1], "answer")
        self.assertIn("tool", kinds)
        self.assertEqual(g["runs"][0]["n_events"], len(g["events"]))

    def test_record_run_is_best_effort(self):
        self.b.fail_read = True  # a non-404 read error must not wipe the graph — and must not raise
        out = cg.record_run(WS, agent_result())
        self.assertFalse(out["cg_recorded"])
        self.assertIn("cg_error", out)
        self.assertEqual(self.b.writes, 0)
        with self.assertRaises(WsError):
            cg.load_graph("test-bucket", WS["ws_id"])

    def test_feedback_with_known_run(self):
        rid = cg.record_run(WS, agent_result("wiki"))["cg_run_id"]
        r = cg.record_feedback(WS, {"run_id": rid, "agent": "wiki", "question": Q, "answer": A,
                                    "sentence": "위약금은 25%가 아니라 잔여 약정 기간에 비례해 계산해야 합니다."})
        self.assertEqual(r["run_id"], rid)
        self.assertFalse(r["synthesized_run"])
        self.assertEqual(r["signal"]["feedback_mode"], "SENTENCE")
        self.assertIsNotNone(r["candidate"])
        self.assertIn("regression_cq", r["candidate"])
        g = self.b.graph()
        self.assertEqual(len(g["runs"]), 1)
        self.assertEqual(len(g["feedback"]), 1)
        self.assertEqual(g["feedback"][0]["raw_sentence"][:3], "위약금")
        self.assertEqual(len(g["candidates"]), 1)
        self.assertEqual(g["candidates"][0]["status"], "PENDING")

    def test_feedback_without_run_synthesizes_run(self):
        r = cg.record_feedback(WS, {"agent": "hybrid", "question": Q, "answer": A, "rating": "down", "reason_code": "WRONG_POLICY_VALUE"})
        self.assertTrue(r["synthesized_run"])
        self.assertEqual(r["signal"]["feedback_mode"], "THUMBS_CHIP")
        g = self.b.graph()
        self.assertEqual(g["runs"][0]["run_id"], r["run_id"])
        self.assertTrue(g["runs"][0]["synthesized"])
        self.assertEqual(g["runs"][0]["agent_surface"], "hybrid_agent")
        # unknown run id (another instance / older answer) → synthesized with the same id, nothing lost
        r2 = cg.record_feedback(WS, {"run_id": "run-deadbeef", "agent": "graph", "question": Q, "answer": A, "rating": "up"})
        self.assertEqual(r2["run_id"], "run-deadbeef")
        self.assertIsNone(r2["candidate"])  # a bare 👍 changes nothing
        self.assertEqual(len(self.b.graph()["feedback"]), 2)

    def test_feedback_requires_content(self):
        with self.assertRaises(ValueError):
            cg.record_feedback(WS, {"agent": "wiki", "question": Q, "answer": A})

    def test_review_approve_creates_changeset_and_cq(self):
        r = cg.record_feedback(WS, {"agent": "graph", "question": Q, "answer": A, "rating": "down",
                                    "sentence": "약정 12개월 미만 해지는 위약금 100% 예외 규칙을 추가해야 합니다."})
        cid = r["candidate"]["candidate_id"]
        store = {"cqs": [{"id": "CQ-01", "question": "x"}, {"id": "CG-2", "question": "old cg"}]}
        saved = {}

        def save(cqs):
            saved["cqs"] = cqs
            return {"status": "SUCCESS", "cqs": cqs}
        out = cg.review(WS, cid, "approve", "ok", by="sme@example.com", read_cqs=lambda: store["cqs"], save_cqs=save)
        self.assertEqual(out["candidate"]["status"], "APPROVED")
        self.assertEqual(out["cq"]["id"], "CG-3")
        self.assertEqual(out["cq"]["origin"], "context_graph")
        self.assertEqual(out["cq"]["agent"], "graph")
        self.assertEqual(out["cq"]["type"], "data")
        self.assertEqual(len(saved["cqs"]), 3)
        cs = out["changeset"]
        self.assertEqual(cs["status"], "APPLIED")
        self.assertTrue(cs["graph_reflected"])
        self.assertEqual([o["op"] for o in cs["ops"]][-1], "ADD_REGRESSION_CQ")
        g = self.b.graph()
        self.assertEqual(len(g["approvals"]), 1)
        self.assertEqual(len(g["changesets"]), 1)
        with self.assertRaises(WsError):  # already reviewed
            cg.review(WS, cid, "reject")

    def test_review_reject_and_errors(self):
        r = cg.record_feedback(WS, {"agent": "wiki", "question": Q, "answer": A, "sentence": "용어 '선약'은 선택약정의 줄임말입니다."})
        out = cg.review(WS, r["candidate"]["candidate_id"], "reject", "not now")
        self.assertEqual(out["candidate"]["status"], "REJECTED")
        self.assertIsNone(out["changeset"])
        with self.assertRaises(ValueError):
            cg.review(WS, "cand-x", "maybe")
        with self.assertRaises(WsError):
            cg.review(WS, "cand-missing", "approve")

    def test_review_cq_limit_still_records(self):
        r = cg.record_feedback(WS, {"agent": "wiki", "question": Q, "answer": A, "sentence": "답변이 틀렸습니다. 위약금은 30%입니다."})
        full = [{"id": f"CQ-{i}", "question": "q"} for i in range(cg.MAX_CQS)]
        out = cg.review(WS, r["candidate"]["candidate_id"], "approve", read_cqs=lambda: full, save_cqs=lambda c: {"status": "SUCCESS"})
        self.assertIsNone(out["cq"])
        self.assertIn("CQ_LIMIT", out["cq_error"])
        self.assertEqual(out["changeset"]["status"], "RECORDED")

    def test_graph_view_layers(self):
        rid = cg.record_run(WS, agent_result("hybrid"))["cg_run_id"]
        r = cg.record_feedback(WS, {"run_id": rid, "agent": "hybrid", "question": Q, "answer": A, "sentence": "좋은 답변입니다. 항상 출처를 인용해 주세요."})
        cg.record_feedback(WS, {"run_id": rid, "agent": "hybrid", "question": Q, "answer": A, "rating": "up"})
        cg.review(WS, r["candidate"]["candidate_id"], "approve", read_cqs=lambda: [], save_cqs=lambda c: {"status": "SUCCESS", "cqs": c})
        v = cg.graph_view(WS, "en")
        self.assertEqual([s["id"] for s in v["stages"]], ["input", "l0", "l1", "l2", "sme", "changeset", "graph"])
        kinds = sorted({n["kind"] for n in v["nodes"]})
        self.assertEqual(kinds, ["approval", "candidate", "changeset", "feedback", "run"])
        icons = sorted(n["icon"] for n in v["nodes"] if n["kind"] == "feedback")
        self.assertEqual(icons, ["sentence", "up"])
        self.assertEqual({e["type"] for e in v["edges"]}, {"HAS_FEEDBACK", "EXTRACTED_TACIT_CLAIM", "REVIEWED_BY", "APPLIED_AS"})
        self.assertEqual(v["counts"]["changesets"], 1)
        self.assertEqual(v["pending"], 0)
        self.assertTrue(v["events"])

    def test_caps(self):
        g = cg.empty_graph(WS["ws_id"])
        g["events"] = [{"i": i} for i in range(cg.CAPS["events"] + 10)]
        cg._trim(g)
        self.assertEqual(len(g["events"]), cg.CAPS["events"])
        self.assertEqual(g["events"][-1]["i"], cg.CAPS["events"] + 9)

    def test_approved_rules_feed_the_next_run(self):
        """REQ-9 L3: approved statements come back as the CG-RULES page every agent step sees."""
        from src.aos import agent as agent_mod
        r1 = cg.record_feedback(WS, {"agent": "wiki", "question": Q, "answer": A, "sentence": "18개월 이상 유지 고객은 잔여 할부금 면제 예외 규칙을 먼저 확인해야 함"})
        r2 = cg.record_feedback(WS, {"agent": "graph", "question": Q, "answer": A, "sentence": "해지 고객은 제외하고 활성 회선만 기준으로 계산해야 합니다."})
        for r in (r1, r2):
            cg.review(WS, r["candidate"]["candidate_id"], "approve", read_cqs=lambda: [], save_cqs=lambda c: {"status": "SUCCESS", "cqs": c})
        rules = cg.approved_rules(WS, "graph")
        self.assertEqual(len(rules), 2)
        self.assertEqual(rules[0]["agent"], "graph")  # the asking agent's own rules first
        seen = {}

        class Log:
            calls = []

            def call(self, tool, args, timeout_s=0, label=""):
                seen["context"] = args["context"]
                return {"status": "SUCCESS", "action": "answer", "answer": "ok", "citations": [agent_mod.RULES_PAGE_ID], "telemetry": {}}
        ws = dict(WS, env={**WS["env"], "dataset": "d", "model": "m", "vertex_location": "global", "region": "asia-northeast3"})
        res = agent_mod.run(ws, "wiki", Q, None, {"pages": [{"id": "W-01", "title": "t", "summary": "s"}], "plan": {}}, Log(),
                            extra_rules=[x["statement"] for x in rules])
        ids = [p["id"] for p in seen["context"]["wiki_index"]]
        self.assertEqual(ids, ["W-01", agent_mod.RULES_PAGE_ID])
        self.assertIn("18개월", seen["context"]["wiki_index"][1]["summary"])
        self.assertEqual([x["id"] for x in res["refs"]], [agent_mod.RULES_PAGE_ID])
        cg.record_run(WS, dict(res, cg_rules_applied=rules), compare_of="run-abc")
        run = self.b.graph()["runs"][-1]
        self.assertEqual(run["compare_of"], "run-abc")
        self.assertEqual(len(run["rules_applied"]), 2)


class CliTests(unittest.TestCase):
    def test_cg_subcommand_parses(self):
        from src import cli
        with mock.patch.object(cli, "load", return_value=dict(WS)), mock.patch.object(cli, "_cg", return_value=0) as m, \
                mock.patch("src.identity.resolve", return_value={"mode": "runtime", "token": None, "principal": "rt", "expires_in": None, "user_identity": False}):
            rc = cli.main(["cg", "--bucket", "test-bucket", "--ws", WS["ws_id"], "feedback", "--agent", "wiki", "--sentence", "x"])
        self.assertEqual(rc, 0)
        a = m.call_args[0][0]
        self.assertEqual((a.action, a.agent, a.sentence), ("feedback", "wiki", "x"))


class RouteTests(unittest.TestCase):
    """/api/v5/cg/* through the real HTTP handler (identity + workspace loading mocked)."""

    @classmethod
    def setUpClass(cls):
        from src.web.studio_server import StudioHandler, ThreadingStudioServer
        cls.httpd = ThreadingStudioServer(("127.0.0.1", 0), StudioHandler)
        cls.base = f"http://127.0.0.1:{cls.httpd.server_address[1]}"
        threading.Thread(target=cls.httpd.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def setUp(self):
        self.b = FakeBucket()
        self.cqs = []

        def save_cqs(ws, cqs):
            self.cqs = cqs
            return {"status": "SUCCESS", "cqs": cqs}
        self.patches = [self.b.patch(),
                        mock.patch("src.identity.resolve", return_value={"mode": "runtime", "token": None, "principal": "rt@test", "expires_in": None, "user_identity": False}),
                        mock.patch("src.web.v5_routes._ws_ref", return_value=dict(WS)),
                        mock.patch("src.aos.studio.studio_data", side_effect=lambda ws, what: {"cqs": list(self.cqs)}),
                        mock.patch("src.aos.studio.save_cqs", side_effect=save_cqs)]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in reversed(self.patches):
            p.stop()

    def post(self, path, body):
        req = urllib.request.Request(self.base + path, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    def test_feedback_graph_review_flow(self):
        ws = {"bucket": "test-bucket", "ws_id": WS["ws_id"]}
        code, fb = self.post("/api/v5/cg/feedback", {"ws": ws, "agent": "graph", "question": Q, "answer": A, "rating": "down",
                                                     "sentence": "위약금 계산 기준이 틀렸습니다. 잔여 기간 비례로 계산해야 합니다."})
        self.assertEqual(code, 200, fb)
        self.assertTrue(fb["synthesized_run"])
        self.assertEqual(fb["signal"]["feedback_mode"], "HYBRID")
        cid = fb["candidate"]["candidate_id"]
        code, g = self.post("/api/v5/cg/graph", {"ws": ws, "lang": "en"})
        self.assertEqual(code, 200)
        self.assertEqual(g["pending"], 1)
        self.assertEqual(g["stages"][-1]["label"], "Reflected in the graph")
        code, rv = self.post("/api/v5/cg/review", {"ws": ws, "candidate_id": cid, "decision": "approve", "note": "SME ok"})
        self.assertEqual(code, 200, rv)
        self.assertEqual(rv["cq"]["id"], "CG-1")
        self.assertEqual(rv["approval"]["by"], "rt@test")
        self.assertEqual(self.cqs[-1]["origin"], "context_graph")
        code, rv = self.post("/api/v5/cg/review", {"ws": ws, "candidate_id": "cand-nope", "decision": "approve"})
        self.assertEqual(code, 404)
        code, rv = self.post("/api/v5/cg/review", {"ws": ws, "candidate_id": cid, "decision": "later"})
        self.assertEqual(code, 400)
        code, rv = self.post("/api/v5/cg/feedback", {"ws": ws, "agent": "wiki", "question": Q, "answer": A})
        self.assertEqual(code, 400)


if __name__ == "__main__":
    unittest.main()
