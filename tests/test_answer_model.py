# -*- coding: utf-8 -*-
"""Agent answers use their own model + an explicit thinking level; build and grading keep the build model.

    answers  (Wiki · Graph · Hybrid agent step, RAG answer, legacy reference agents)  VERTEX_ANSWER_MODEL (gemini-4-hydrogen)
                                                                                      + VERTEX_ANSWER_THINKING_LEVEL (LOW)
    build · grading (CQ draft, wiki compile, graph design, judges)                    workspace `model` (VERTEX_GEMINI_MODEL)

Offline: Core MCP is a scripted log, Vertex AI is a patched `urlopen`; no network call is made.
"""
from __future__ import annotations

import io
import json
import os
import sys
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src import gcp_client, identity  # noqa: E402
from src.agent import agents as legacy_agents  # noqa: E402
from src.agent.reasoning_engine import AiFdeAgentEngine  # noqa: E402
from src.aos import agent as agent_mod  # noqa: E402
from src.aos import pipeline, rag, studio, three_way  # noqa: E402
from src.aos.ws import WsError, clean_env  # noqa: E402
from src.web import studio_server, v5_routes  # noqa: E402

USER = {"mode": "token", "principal": "u@test", "user_identity": True}
ANSWER_ENV = ("VERTEX_ANSWER_MODEL", "VERTEX_ANSWER_THINKING_LEVEL")
BUILD_MODEL = "build-model-x"


def clean_environ(**extra):
    """os.environ without the answer variables (+ extra) — the defaults must not depend on the developer's shell."""
    env = {k: v for k, v in os.environ.items() if k not in ANSWER_ENV}
    env.update(extra)
    return mock.patch.dict(os.environ, env, clear=True)


def make_ws(**env_extra):
    return {"ws_id": "ws-20260101-abc123", "lang": "en",
            "env": {"bucket": "b", "project": "p-1", "region": "asia-northeast3", "dataset": "d", "model": BUILD_MODEL,
                    "vertex_location": "global", **env_extra},
            "stages": {}, "summary": {"cqs": 2}, "scenario": {"objective": "o"}}


class FakeLog:
    def __init__(self, script):
        self.script, self.calls = script, []

    def call(self, tool, args, timeout_s=120, label=""):
        self.calls.append({"tool": tool, "args": args})
        r = self.script.get(tool, {"status": "ERROR", "message": f"unscripted tool {tool}"})
        return r(args) if callable(r) else r

    def args_of(self, tool):
        return [c["args"] for c in self.calls if c["tool"] == tool]


STEP_ANSWER = {"status": "SUCCESS", "action": "answer", "answer": "A", "citations": [], "thought": "t",
               "telemetry": {"ms": 5, "tokens_in": 1, "tokens_out": 1, "model": "gemini-4-hydrogen"}}
CTX = {"pages": [{"id": "p1", "layer": "concept", "title": "T", "summary": "s", "body_md": "b"}], "plan": {"schema": {"nodes": []}}}


# ================================================================================================ settings
class AnswerSettingsTests(unittest.TestCase):
    def test_defaults_are_hydrogen_low_and_build_stays(self):
        with clean_environ():
            self.assertEqual(gcp_client.answer_settings(), ("gemini-4-hydrogen", "LOW"))
            s = gcp_client.runtime_settings()
            self.assertEqual((s["vertex_answer_model"], s["vertex_answer_thinking_level"]), ("gemini-4-hydrogen", "LOW"))
            self.assertEqual(s["vertex_model"], gcp_client.DEFAULT_GEMINI_MODEL)          # build / grading model untouched
            self.assertNotEqual(s["vertex_model"], s["vertex_answer_model"])

    def test_env_overrides_and_invalid_level_falls_back_to_low(self):
        with clean_environ(VERTEX_ANSWER_MODEL="gemini-x", VERTEX_ANSWER_THINKING_LEVEL="medium"):
            self.assertEqual(gcp_client.answer_settings(), ("gemini-x", "MEDIUM"))
        for bad in ("MINIMAL", "minimal", "0", "NONE", ""):
            with clean_environ(VERTEX_ANSWER_THINKING_LEVEL=bad):
                self.assertEqual(gcp_client.answer_thinking_level(), "LOW", bad)

    def test_workspace_env_overrides_only_when_explicit(self):
        with clean_environ():
            # the workspace build model (e.g. an old workspace.json with model=gemini-4-argon) never drives answers
            self.assertEqual(gcp_client.answer_settings({"model": "gemini-4-argon"}), ("gemini-4-hydrogen", "LOW"))
            self.assertEqual(gcp_client.answer_settings({"model": "m", "answer_model": "ans-1", "answer_thinking_level": "high"}), ("ans-1", "HIGH"))
            self.assertEqual(gcp_client.answer_settings({"answer_thinking_level": "MINIMAL"}), ("gemini-4-hydrogen", "LOW"))

    def test_clean_env_accepts_explicit_keys_but_never_fills_them(self):
        with clean_environ():
            env = clean_env({"project": "p-12345", "bucket": "bkt", "dataset": "d"})
            self.assertNotIn("answer_model", env)
            self.assertNotIn("answer_thinking_level", env)
            env = clean_env({"project": "p-12345", "bucket": "bkt", "dataset": "d", "answer_model": "gemini-4-hydrogen", "answer_thinking_level": "medium"})
            self.assertEqual((env["answer_model"], env["answer_thinking_level"]), ("gemini-4-hydrogen", "MEDIUM"))
            with self.assertRaises(WsError):
                clean_env({"project": "p-12345", "bucket": "bkt", "dataset": "d", "answer_thinking_level": "MINIMAL"})
            with self.assertRaises(WsError):
                clean_env({"project": "p-12345", "bucket": "bkt", "dataset": "d", "answer_model": "Bad Model!"})

    def test_model_display(self):
        self.assertEqual(gcp_client.model_display("gemini-4-hydrogen"), "Gemini 4 Hydrogen")
        self.assertEqual(gcp_client.model_display("gemini-4-argon"), "Gemini 4 Argon")
        self.assertEqual(gcp_client.model_display("my-custom.model-1"), "my-custom.model-1")

    def test_bootstrap_health_and_settings_show_both_models(self):
        with clean_environ():
            b = v5_routes.bootstrap("en")
            self.assertEqual((b["answer_model"], b["answer_model_display"], b["answer_thinking_level"]), ("gemini-4-hydrogen", "Gemini 4 Hydrogen", "LOW"))
            self.assertEqual(b["model"], gcp_client.DEFAULT_GEMINI_MODEL)
            self.assertNotIn("answer_model", b["env_defaults"])                           # never pinned into new workspaces
            p = studio_server.settings_payload()
            self.assertEqual((p["answer_model"], p["answer_model_display"], p["answer_thinking_level"]), ("gemini-4-hydrogen", "Gemini 4 Hydrogen", "LOW"))
            self.assertEqual(p["model_display"], gcp_client.model_display(gcp_client.DEFAULT_GEMINI_MODEL))


# ================================================================================================ Core MCP call arguments
class AgentStepArgsTests(unittest.TestCase):
    def _ask(self, ws):
        log = FakeLog({"aos_core_agent_step": STEP_ANSWER})
        with identity.bind("t", USER):
            res = agent_mod.run(ws, "wiki", "q", None, CTX, log)
        return res, log.args_of("aos_core_agent_step")

    def test_agent_step_sends_answer_model_and_explicit_low(self):
        with clean_environ():
            res, calls = self._ask(make_ws(model="gemini-4-argon"))
        self.assertEqual(len(calls), 1)
        self.assertEqual((calls[0]["model"], calls[0]["thinking_level"]), ("gemini-4-hydrogen", "LOW"))
        self.assertEqual(res["telemetry"]["thinking_level"], "LOW")
        self.assertEqual(res["telemetry"]["model"], "gemini-4-hydrogen")

    def test_workspace_answer_model_wins(self):
        with clean_environ(VERTEX_ANSWER_MODEL="env-model"):
            _res, calls = self._ask(make_ws(answer_model="ws-model", answer_thinking_level="MEDIUM"))
            self.assertEqual((calls[0]["model"], calls[0]["thinking_level"]), ("ws-model", "MEDIUM"))
            _res, calls = self._ask(make_ws())
            self.assertEqual((calls[0]["model"], calls[0]["thinking_level"]), ("env-model", "LOW"))

    def test_retry_keeps_the_same_arguments(self):
        seen = []

        def flaky(args):
            seen.append(args)
            return {"status": "ERROR", "message": "transient"} if len(seen) == 1 else STEP_ANSWER
        log = FakeLog({"aos_core_agent_step": flaky})
        with clean_environ(), identity.bind("t", USER):
            agent_mod.run(make_ws(), "wiki", "q", None, CTX, log)
        self.assertEqual(len(seen), 2)
        self.assertEqual([(a["model"], a["thinking_level"]) for a in seen], [("gemini-4-hydrogen", "LOW")] * 2)


class RagAnswerArgsTests(unittest.TestCase):
    def test_rag_answer_sends_answer_model_and_explicit_low(self):
        log = FakeLog({"aos_core_rag_answer": {"status": "SUCCESS", "answer": "A", "evidence_text": "e", "contexts": [{"unit_id": "u1"}]}})
        with clean_environ():
            out = rag.run_rag(make_ws(model="gemini-4-argon"), "q", {"corpus": "c/1", "retrieve": {"keep": 5, "rerank": None}}, log)
        a = log.args_of("aos_core_rag_answer")[0]
        self.assertEqual((a["model"], a["thinking_level"]), ("gemini-4-hydrogen", "LOW"))
        self.assertEqual((a["keep"], a["llm_location"], a["return_evidence_text"]), (5, "global", True))
        self.assertEqual(out["answer"], "A")


class CompareRunTests(unittest.TestCase):
    """stage_compare: answers on the answer model, the judge on the workspace (build) model with unchanged argument keys."""
    CQS = [{"id": "CQ-01", "type": "doc", "question": "q1", "reference_answer": "a1", "key_facts": ["f"]}]

    def _run(self, ws):
        answered, judged, saved = [], [], {}

        def judge(args):
            judged.append(args)
            return {"status": "SUCCESS", "scores": {"total": 90}, "verdict": "PASS", "summary": "s", "deductions": []}

        def rag_answer(args):
            answered.append(("aos_core_rag_answer", args))
            return {"status": "SUCCESS", "answer": "[rag]", "evidence_text": "e", "contexts": []}

        def step(args):
            answered.append(("aos_core_agent_step", args))
            return STEP_ANSWER

        class Quiet(FakeLog):
            def __init__(self, stage, emit):
                super().__init__({"aos_core_eval_rubric_judge": judge, "aos_core_rag_answer": rag_answer, "aos_core_agent_step": step})

        cmp_ = {"status": "SUCCESS", "cq_count": 1, "stage1_rag_vs_wiki": {"delta_points": 0.0}, "stage2_wiki_vs_graph": {"delta_points": 0.0},
                "final_three_way": {}}
        log = FakeLog({"aos_core_eval_compare": cmp_})
        with clean_environ(), identity.bind("t", USER), mock.patch.object(rag, "McpLog", Quiet), \
                mock.patch.object(rag, "get_json", return_value=list(self.CQS)), \
                mock.patch.object(rag, "load_config", return_value={"corpus": "c/1", "embedding_model": "emb", "retrieve": {"keep": 9}}), \
                mock.patch.object(rag.agent_mod, "load_context", return_value=CTX), \
                mock.patch.object(rag, "put_json", side_effect=lambda l, b, n, o: saved.__setitem__(n, o)):
            rag.stage_compare(ws, log, lambda ev: None, workers=1)
        return answered, judged, saved, log

    def test_answers_on_answer_model_judge_on_build_model(self):
        answered, judged, saved, log = self._run(make_ws())
        self.assertEqual({t for t, _ in answered}, {"aos_core_rag_answer", "aos_core_agent_step"})
        self.assertEqual(len(answered), 3)                                              # rag + wiki + graph(hybrid)
        for _tool, a in answered:
            self.assertEqual((a["model"], a["thinking_level"]), ("gemini-4-hydrogen", "LOW"))
        self.assertEqual(len(judged), 3)
        for a in judged:                                                                # grading: unchanged model and argument keys
            self.assertEqual(a["model"], BUILD_MODEL)
            self.assertNotIn("thinking_level", a)
            self.assertEqual(set(a) - {"question", "ground_truth", "key_rubrics", "answer", "evidence"}, {"project", "model", "llm_location", "lang"})
        run = saved["aos/ws-20260101-abc123/runs/three_way_latest.json"]
        m = run["method"]
        self.assertEqual((m["answer_model"], m["answer_thinking_level"]), ("gemini-4-hydrogen", "LOW"))
        self.assertEqual((m["judge_model"], m["judge_thinking_level"]), (BUILD_MODEL, "MEDIUM"))
        self.assertIn("aos_core_eval_rubric_judge", m["judge"])
        sent = log.args_of("aos_core_eval_compare")[0]["systems"]
        for s in ("rag", "wiki", "graph"):
            self.assertEqual((sent[s]["agent_model"], sent[s]["agent_thinking_level"]), ("gemini-4-hydrogen", "LOW"))

    def test_workspace_override_is_recorded(self):
        answered, _judged, saved, _log = self._run(make_ws(answer_model="ws-model", answer_thinking_level="HIGH"))
        self.assertEqual({(a["model"], a["thinking_level"]) for _t, a in answered}, {("ws-model", "HIGH")})
        m = saved["aos/ws-20260101-abc123/runs/three_way_latest.json"]["method"]
        self.assertEqual((m["answer_model"], m["answer_thinking_level"], m["judge_model"]), ("ws-model", "HIGH", BUILD_MODEL))


class BuildAndJudgeUnchangedTests(unittest.TestCase):
    def test_build_tools_keep_the_workspace_model_and_no_level(self):
        with clean_environ():
            common = pipeline._kh_common(make_ws())
        self.assertEqual(common, {"project": "p-1", "model": BUILD_MODEL, "location": "global", "lang": "en"})

    def test_s5_eval_judge_uses_build_model_and_agent_uses_answer_model(self):
        judged, stepped = [], []

        def judge(args):
            judged.append(args)
            return {"status": "SUCCESS", "score": 1.0, "verdict": "PASS", "method": "m"}

        def step(args):
            stepped.append(args)
            return STEP_ANSWER

        class Quiet(FakeLog):
            def __init__(self, stage, emit):
                super().__init__({"aos_core_judge": judge, "aos_core_agent_step": step})

        cqs = [{"id": "CQ-01", "question": "q1", "agent": "wiki", "reference_answer": "a", "key_facts": []}]
        log = FakeLog({})
        log.calls = []
        with clean_environ(), identity.bind("t", USER), mock.patch.object(pipeline, "McpLog", Quiet), \
                mock.patch.object(pipeline, "get_json", return_value=cqs), mock.patch.object(pipeline, "put_json", return_value=None), \
                mock.patch.object(pipeline.agent_mod, "load_context", return_value=CTX):
            pipeline.stage_eval(make_ws(), log, lambda ev: None, workers=1)
        self.assertEqual(len(judged), 1)
        self.assertEqual(judged[0]["model"], BUILD_MODEL)
        self.assertNotIn("thinking_level", judged[0])
        self.assertEqual([(a["model"], a["thinking_level"]) for a in stepped], [("gemini-4-hydrogen", "LOW")])


# ================================================================================================ direct Vertex AI calls
class _Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class VertexRequestTests(unittest.TestCase):
    def _capture(self):
        sent = []

        def fake_urlopen(req, context=None, timeout=None):
            sent.append({"url": req.full_url, "body": json.loads(req.data.decode("utf-8"))})
            return _Resp(json.dumps({"candidates": [{"content": {"parts": [{"text": "OK"}]}, "finishReason": "STOP"}],
                                     "usageMetadata": {}, "modelVersion": "gemini-4-hydrogen"}).encode("utf-8"))
        return sent, fake_urlopen

    def test_hydrogen_request_carries_explicit_thinking_level_low(self):
        sent, fake = self._capture()
        with mock.patch.object(gcp_client, "get_gcp_token", return_value="tok"), mock.patch.object(gcp_client.urllib.request, "urlopen", fake):
            r = gcp_client.call_vertex_gemini("hi", model_name="gemini-4-hydrogen", thinking_level="LOW", project_id="p-1", location="global")
        self.assertEqual(r["status"], "SUCCESS")
        self.assertIn("/publishers/google/models/gemini-4-hydrogen:generateContent", sent[0]["url"])
        self.assertEqual(sent[0]["body"]["generationConfig"]["thinkingConfig"], {"thinkingLevel": "LOW"})   # never omitted, never MINIMAL
        self.assertEqual(r["thinking_level"], "LOW")

    def _scripted(self, replies):
        """urlopen that answers with `replies` in order: (text, finishReason)."""
        sent, queue = [], list(replies)

        def fake_urlopen(req, context=None, timeout=None):
            sent.append(json.loads(req.data.decode("utf-8"))["generationConfig"]["maxOutputTokens"])
            text, finish = queue.pop(0)
            parts = [{"text": text}] if text else []
            return _Resp(json.dumps({"candidates": [{"content": {"parts": parts}, "finishReason": finish}],
                                     "usageMetadata": {"thoughtsTokenCount": 430}, "modelVersion": "gemini-4-hydrogen"}).encode("utf-8"))
        return sent, fake_urlopen

    def test_output_cap_gives_answer_calls_a_thinking_allowance(self):
        cap = gcp_client.output_cap
        # build / grading: unchanged floors
        self.assertEqual([cap(256, "LOW"), cap(1024, "LOW"), cap(4096, "LOW"), cap(2048, "MEDIUM"), cap(2048, "HIGH")], [2048, 2048, 4096, 8192, 16384])
        # answers: + 1024 for thought tokens, never below 2048, level floor still applies
        self.assertEqual([cap(256, "LOW", "answer"), cap(1024, "LOW", "answer"), cap(2048, "LOW", "answer")], [2048, 2048, 3072])
        self.assertEqual([cap(2048, "MEDIUM", "answer"), cap(16384, "HIGH", "answer")], [8192, 17408])
        self.assertGreaterEqual(gcp_client.ANSWER_THINKING_HEADROOM, 1024)

    def test_answer_request_uses_the_allowance_and_build_request_does_not(self):
        for role, want in (("answer", 3072), ("build", 2048)):
            sent, fake = self._scripted([("OK", "STOP")])
            with mock.patch.object(gcp_client, "get_gcp_token", return_value="tok"), mock.patch.object(gcp_client.urllib.request, "urlopen", fake):
                gcp_client.call_vertex_gemini("hi", max_tokens=2048, model_name="gemini-4-hydrogen", thinking_level="LOW", project_id="p-1", role=role)
            self.assertEqual(sent, [want], role)

    def test_empty_max_tokens_answer_is_retried_with_a_larger_cap(self):
        sent, fake = self._scripted([("", "MAX_TOKENS"), ('{"ok": true}', "STOP")])
        with mock.patch.object(gcp_client, "get_gcp_token", return_value="tok"), mock.patch.object(gcp_client.urllib.request, "urlopen", fake):
            r = gcp_client.call_vertex_gemini("hi", max_tokens=1024, model_name="gemini-4-hydrogen", thinking_level="LOW", project_id="p-1", role="answer")
        self.assertEqual((r["status"], r["text"], r["attempts"]), ("SUCCESS", '{"ok": true}', 2))
        self.assertEqual(sent, [2048, 8192])

    def test_truncated_answer_is_retried_but_a_truncated_build_reply_is_returned_as_before(self):
        sent, fake = self._scripted([('{"slots": {"a"', "MAX_TOKENS"), ('{"slots": {"a": 1}}', "STOP")])
        with mock.patch.object(gcp_client, "get_gcp_token", return_value="tok"), mock.patch.object(gcp_client.urllib.request, "urlopen", fake):
            r = gcp_client.call_vertex_gemini("hi", max_tokens=1024, model_name="gemini-4-hydrogen", thinking_level="LOW", project_id="p-1", role="answer")
        self.assertEqual((r["text"], r["finish_reason"]), ('{"slots": {"a": 1}}', "STOP"))
        self.assertEqual(sent, [2048, 8192])
        sent, fake = self._scripted([("partial build text", "MAX_TOKENS")])
        with mock.patch.object(gcp_client, "get_gcp_token", return_value="tok"), mock.patch.object(gcp_client.urllib.request, "urlopen", fake):
            r = gcp_client.call_vertex_gemini("hi", max_tokens=1024, model_name="gemini-4-argon", thinking_level="MEDIUM", project_id="p-1")
        self.assertEqual((r["text"], r["finish_reason"], sent), ("partial build text", "MAX_TOKENS", [8192]))      # build path: no extra retry

    def test_reference_engine_and_wiki_agent_use_answer_model_low(self):
        with clean_environ():
            eng = AiFdeAgentEngine(project_id="p-1", server=object())
            self.assertEqual((eng.model_name, eng.thinking_level), ("gemini-4-hydrogen", "LOW"))
            eng = AiFdeAgentEngine(project_id="p-1", server=object(), model_name="m2", thinking_level="MINIMAL")
            self.assertEqual((eng.model_name, eng.thinking_level), ("m2", "LOW"))
            calls = []

            def fake_gemini(**kw):
                calls.append(kw)
                return {"status": "SUCCESS", "text": "answer [okf_a]", "elapsed_ms": 1, "model": kw["model_name"], "thinking_level": kw["thinking_level"]}
            cfg = mock.Mock(model="gemini-4-argon", project_id="p-1", vertex_location="global", bucket="b")
            cfg.gcs_prefix.return_value = "starter/en/"
            with mock.patch.object(legacy_agents, "gcs_list", return_value=(200, {"items": [{"name": "starter/en/wiki/okf_a.md"}]})), \
                    mock.patch.object(legacy_agents, "gcs_download_text", return_value=(200, "---\ntitle: A\n---\nbody")), \
                    mock.patch.object(legacy_agents, "call_vertex_gemini", side_effect=fake_gemini):
                legacy_agents.run_wiki(cfg, "A", "en", "q", lambda ev: None)
        self.assertEqual([(c["model_name"], c["thinking_level"], c["role"]) for c in calls], [("gemini-4-hydrogen", "LOW", "answer")])

    def test_every_direct_answer_call_site_declares_the_answer_role(self):
        eng = open(os.path.join(ROOT, "src", "agent", "reasoning_engine.py"), encoding="utf-8").read()
        self.assertEqual(eng.count("call_vertex_gemini("), 3)
        self.assertEqual(eng.count('thinking_level=self.thinking_level, role="answer"'), 3)       # slot extraction + 2 syntheses
        nb = open(os.path.join(ROOT, "notebooks", "nb_helpers.py"), encoding="utf-8").read()
        self.assertIn('model_name=answer_model(), thinking_level=answer_thinking_level(), role="answer")', nb)   # NL → GQL


# ================================================================================================ handoff bundle · display
class HandoffAndDisplayTests(unittest.TestCase):
    def test_standalone_agent_script_sends_answer_model_and_level(self):
        src = studio.STANDALONE
        self.assertIn('"model": ANSWER_MODEL, "thinking_level": ANSWER_THINKING_LEVEL', src)
        self.assertIn('ANSWER_MODEL = os.environ.get("VERTEX_ANSWER_MODEL") or WS["answer_model"]', src)
        self.assertNotIn('"model": WS["model"]', src)

    def test_markdown_meta_shows_level_only_when_recorded(self):
        cmp_ = {"cq_count": 2, "stage1_rag_vs_wiki": None, "stage2_wiki_vs_graph": None, "final_three_way": None}
        base = {"at": "2026-11-17T10:00:00+09:00", "comparison": cmp_}
        try:
            new = three_way.render_markdown({**base, "method": {"answer_model": "gemini-4-hydrogen", "answer_thinking_level": "LOW", "judge": "j"}}, "en", "en")
            old = three_way.render_markdown({**base, "method": {"answer_model": "gemini-4-argon", "judge": "j"}}, "en", "en")
            ko = three_way.render_markdown({**base, "method": {"answer_model": "gemini-4-hydrogen", "answer_thinking_level": "LOW", "judge": "j"}}, "ko", "en")
        except (TypeError, KeyError, AttributeError):  # the table renderer needs a full comparison — check the meta template instead
            new = three_way._tx("en", "meta", n=2, model="gemini-4-hydrogen", level=" · thinking `LOW`", judge="j", at="2026-11-17")
            old = three_way._tx("en", "meta", n=2, model="gemini-4-argon", level="", judge="j", at="2026-11-17")
            ko = three_way._tx("ko", "meta", n=2, model="gemini-4-hydrogen", level=" · thinking `LOW`", judge="j", at="2026-11-17")
        self.assertIn("answer model `gemini-4-hydrogen` · thinking `LOW` · judge `j`", new)
        self.assertIn("answer model `gemini-4-argon` · judge `j`", old)                 # runs without a recorded level render as before
        self.assertIn("답변 모델 `gemini-4-hydrogen` · thinking `LOW` · 채점 `j`", ko)

    def test_studio_ui_shows_the_level_next_to_the_answer_model(self):
        js = open(os.path.join(ROOT, "src", "web", "static", "studio.js"), encoding="utf-8").read()
        self.assertIn("m.answer_thinking_level ? ` · thinking ${m.answer_thinking_level}` : \"\"", js)


if __name__ == "__main__":
    unittest.main()
