# -*- coding: utf-8 -*-
"""RAG vs OKF Wiki vs Graph (GOAL-296): opt-in stage semantics, rag.py units, read side, routes, docs slots, field-scale pack.

Offline: Core MCP is mocked (a scripted `McpLog`), GCS reads/writes are patched, no GCP call is made.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import threading
import unittest
import urllib.error
import urllib.request
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src import identity  # noqa: E402
from src.aos import pipeline, rag, three_way  # noqa: E402
from src.aos.ws import WsError  # noqa: E402
from src.web import v5_routes  # noqa: E402
from src.web.studio_server import StudioHandler, ThreadingStudioServer  # noqa: E402

STATIC = os.path.join(ROOT, "src", "web", "static")
HANGUL = re.compile(r"[가-힣]")
USER = {"mode": "token", "principal": "u@test", "user_identity": True}
RUNTIME = {"mode": "runtime", "principal": "rt@test"}


def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def _load(path):
    return json.loads(_read(path))


def _dump(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f)


def make_ws(**stages):
    return {"ws_id": "ws-20260101-abc123", "lang": "en",
            "env": {"bucket": "b", "project": "p-1", "region": "asia-northeast3", "model": "m", "vertex_location": "global"},
            "stages": {k: dict(v) for k, v in stages.items()}, "summary": {"cqs": 2}}


class FakeLog:
    """Scripted McpLog: `script[tool]` is a response dict, a list of responses (consumed in order) or a callable(args)."""

    def __init__(self, script):
        self.script, self.calls = script, []

    def call(self, tool, args, timeout_s=120, label=""):
        self.calls.append({"tool": tool, "args": args})
        r = self.script.get(tool, {"status": "ERROR", "message": f"unscripted tool {tool}"})
        if callable(r):
            return r(args)
        if isinstance(r, list):
            return r.pop(0)
        return r

    def tools(self):
        return [c["tool"] for c in self.calls]


def comparison(delta1=-2.0, delta2=3.0):
    def summ(avg, p):
        return {"count": 2, "avg": avg, "min": 0.0, "max": 100.0, "pass": p, "partial": 0, "fail": 2 - p, "pass_rate": 50.0 * p, "avg_latency_sec": 1.0}

    def pair(b, c, d):
        return {"count": 2, "base": summ(*b), "candidate": summ(*c), "delta_points": d, "delta_relative_pct": 1.0, "delta_pass": c[1] - b[1],
                "wins": 1, "ties": 0, "losses": 1, "by_type": [{"type": "doc", "count": 2, "base_avg": b[0], "candidate_avg": c[0], "delta_points": d}],
                "rows": [], "top_gains": [], "top_losses": []}
    return {"status": "SUCCESS", "cq_count": 2, "thresholds": {"pass": 85.0, "partial": 60.0, "tie_margin": 5.0}, "labels": {}, "coverage": {},
            "stage1_rag_vs_wiki": {"base": "rag", "candidate": "wiki", **pair((90.0, 2), (88.0, 1), delta1)},
            "stage2_wiki_vs_graph": {"base": "wiki", "candidate": "graph", **pair((88.0, 1), (91.0, 2), delta2)},
            "final_three_way": {"summaries": {"rag": summ(90.0, 2), "wiki": summ(88.0, 1), "graph": summ(91.0, 2)}, "ranking": [],
                                "by_type": [{"type": "doc", "count": 1, "rag": 90.0, "wiki": 90.0, "graph": 80.0, "best": "rag", "best_margin": 0.0},
                                            {"type": "data", "count": 1, "rag": 50.0, "wiki": 60.0, "graph": 95.0, "best": "graph", "best_margin": 35.0}],
                                "per_cq": [{"id": "CQ-01", "type": "doc", "question": "q1", "rag": 90.0, "wiki": 90.0, "graph": 80.0, "best": "rag"}]},
            "findings": [{"stage": "stage1", "kind": "overall", "ko": "k", "en": "e"}]}


def full_run(**extra):
    c = comparison()
    c.pop("status")
    return {"at": "2026-11-15T10:00:00+09:00", "ws_id": "ws-x", "lang": "en", "systems_run": ["rag", "wiki", "graph"],
            "method": {"answer_model": "m", "judge": "j", "rag": {"embedding_model": "emb-x", "retrieve": {"top_k": 7}, "stats": {"units": 12}}},
            "cqs": [{"id": "CQ-01", "type": "doc", "question": "q1", "reference_answer": "a", "key_facts": []}],
            "results": {"rag": [], "wiki": [], "graph": []}, "comparison": c, **extra}


# ============================================================================================ pipeline: opt-in semantics
class OptionalStageTests(unittest.TestCase):
    def test_optional_stages_are_not_in_the_default_build(self):
        self.assertEqual(pipeline.STAGES, ("prepare", "ingest", "cqs", "wiki", "graph", "eval"))
        self.assertEqual(pipeline.OPTIONAL_STAGES, ("rag", "compare"))
        self.assertEqual(pipeline.ALL_STAGES, pipeline.STAGES + pipeline.OPTIONAL_STAGES)
        b = v5_routes.bootstrap("en")
        self.assertEqual(b["stages"], list(pipeline.STAGES))          # what "build all" iterates
        self.assertEqual(b["optional_stages"], ["rag", "compare"])
        self.assertIn('default=",".join(pipeline.STAGES)', _read(os.path.join(ROOT, "src", "cli.py")))   # CLI default build excludes them
        js = _read(os.path.join(STATIC, "studio.js"))
        self.assertIn('const STAGES = ["prepare", "ingest", "cqs", "wiki", "graph", "eval"];', js)
        self.assertIn("for (const k of only ? [only] : STAGES)", js)  # run-all loop never touches OPT_STAGES
        self.assertIn('const OPT_STAGES = ["rag", "compare"];', js)

    def test_unknown_stage_rejected(self):
        with self.assertRaises(WsError) as cm:
            pipeline.run_stage(make_ws(), "rag2", lambda ev: None)
        self.assertEqual(cm.exception.code, "BAD_REQUEST")

    def test_rag_needs_write_permission_but_compare_does_not(self):
        ws = make_ws()
        with identity.bind(None, RUNTIME), mock.patch.object(pipeline, "can_write", return_value=(False, "allowed-project")):
            with self.assertRaises(WsError) as cm:
                pipeline.run_stage(ws, "rag", lambda ev: None)
            self.assertEqual(cm.exception.code, "WRITE_BLOCKED")
            with mock.patch.object(pipeline.rag_mod, "stage_compare", return_value={"total": 2}), \
                    mock.patch.object(pipeline, "save"), mock.patch.object(pipeline, "append_calls"):
                rec = pipeline.run_stage(ws, "compare", lambda ev: None)
            self.assertEqual(rec["status"], "done")

    def _run(self, ws, stage, **patches):
        with identity.bind("t", USER), mock.patch.object(pipeline, "save"), mock.patch.object(pipeline, "append_calls"), \
                mock.patch.object(pipeline, "_parsed", return_value={"docs": [], "tables": []}), \
                mock.patch.object(pipeline.rag_mod, "stage_rag", return_value={"units": 3}), \
                mock.patch.object(pipeline.rag_mod, "stage_compare", return_value={"total": 2}), \
                mock.patch.object(pipeline, "stage_wiki", return_value={"pages": 1}):
            return pipeline.run_stage(ws, stage, lambda ev: None)

    def test_stale_marking(self):
        ws = make_ws(rag={"status": "done"}, compare={"status": "done"}, eval={"status": "done"})
        self.assertEqual(self._run(ws, "rag")["status"], "done")
        self.assertTrue(ws["stages"]["compare"].get("stale"))          # a rebuilt corpus invalidates the comparison
        self.assertFalse(ws["stages"]["eval"].get("stale"))            # … and nothing before it
        self.assertNotIn("stale", ws["stages"]["rag"])
        self._run(ws, "compare")
        self.assertNotIn("stale", ws["stages"]["compare"])             # re-running clears it
        ws = make_ws(wiki={"status": "done"}, compare={"status": "done"})
        self._run(ws, "wiki")
        self.assertTrue(ws["stages"]["compare"].get("stale"))          # a recompiled wiki invalidates the comparison too

    def test_stage_error_is_recorded_not_raised(self):
        ws = make_ws()
        with identity.bind("t", USER), mock.patch.object(pipeline, "save"), mock.patch.object(pipeline, "append_calls"), \
                mock.patch.object(pipeline.rag_mod, "stage_compare", side_effect=RuntimeError("not built yet: rag")):
            rec = pipeline.run_stage(ws, "compare", lambda ev: None)
        self.assertEqual(rec["status"], "error")
        self.assertIn("not built yet: rag", rec["error"])


# ============================================================================================ rag.py units
class StageRagTests(unittest.TestCase):
    PARSED = {"docs": [{"doc_id": "d1", "title": "Guide", "text": "body"}],
              "tables": [{"name": "t1", "columns": [{"name": "id"}], "rows": [{"id": 1}], "row_count": 1, "pk": "id"}]}

    def _script(self, fingerprint="fp-1", files=3):
        return {"aos_core_rag_decompose": {"status": "SUCCESS", "fingerprint": fingerprint, "version": "v1", "options": {"target_chars": 900},
                                           "stats": {"units": 5, "doc_units": 4, "table_units": 1, "median_chars": 700},
                                           "written": {"import_uri": "gs://b/aos/ws/rag/units/"}},
                "aos_core_rag_status": {"status": "SUCCESS", "files": files, "embedding_model": "emb-returned",
                                        "preset": {"import": {"chunk_size": 1024}, "retrieve": {"top_k": 11}}},
                "aos_core_rag_create_corpus": {"status": "SUCCESS", "corpus": "projects/p-1/locations/asia-northeast3/ragCorpora/777", "embedding_model": "emb-returned"},
                "aos_core_rag_import_files": {"status": "SUCCESS", "done": True, "response": {"imported": 5}},
                "aos_core_rag_delete_corpus": {"status": "SUCCESS", "deleted": True}}

    def _run(self, prev, script):
        log, saved = FakeLog(script), {}
        ws = make_ws()
        with mock.patch.object(rag, "load_config", return_value=prev), \
                mock.patch.object(rag, "put_json", side_effect=lambda l, b, n, o: saved.__setitem__(n, o)):
            out = rag.stage_rag(ws, log, lambda ev: None, self.PARSED)
        return ws, log, saved, out

    def test_same_fingerprint_reuses_the_corpus(self):
        prev = {"corpus": "projects/p-1/locations/asia-northeast3/ragCorpora/111", "fingerprint": "fp-1"}
        ws, log, saved, out = self._run(prev, self._script())
        self.assertNotIn("aos_core_rag_create_corpus", log.tools())
        self.assertNotIn("aos_core_rag_import_files", log.tools())
        self.assertNotIn("aos_core_rag_delete_corpus", log.tools())
        self.assertEqual(out["corpus"], prev["corpus"])
        cfg = saved["aos/ws-20260101-abc123/rag/config.json"]
        self.assertEqual((cfg["corpus"], cfg["fingerprint"]), (prev["corpus"], "fp-1"))
        # settings are stored as Core MCP returned them — nothing is restated by the starter
        self.assertEqual((cfg["embedding_model"], cfg["retrieve"], out["retrieve"]), ("emb-returned", {"top_k": 11}, {"top_k": 11}))
        self.assertEqual(ws["summary"]["rag"]["units"], 5)

    def test_changed_sources_drop_the_stale_corpus_and_build_a_new_one(self):
        prev = {"corpus": "projects/p-1/locations/asia-northeast3/ragCorpora/111", "fingerprint": "fp-OLD"}
        _ws, log, saved, out = self._run(prev, self._script())
        tools = log.tools()
        self.assertLess(tools.index("aos_core_rag_delete_corpus"), tools.index("aos_core_rag_create_corpus"))
        self.assertIn("aos_core_rag_import_files", tools)
        self.assertTrue(out["corpus"].endswith("/777"))
        self.assertEqual([c["args"]["corpus"] for c in log.calls if c["tool"] == "aos_core_rag_delete_corpus"], [prev["corpus"]])

    def test_same_fingerprint_but_empty_corpus_is_rebuilt(self):
        prev = {"corpus": "projects/p-1/locations/asia-northeast3/ragCorpora/111", "fingerprint": "fp-1"}
        script = self._script()
        script["aos_core_rag_status"] = [{"status": "SUCCESS", "files": 0}, script["aos_core_rag_status"]]
        _ws, log, _saved, out = self._run(prev, script)
        self.assertIn("aos_core_rag_create_corpus", log.tools())
        self.assertTrue(out["corpus"].endswith("/777"))

    def test_first_build_and_failure_surface(self):
        _ws, log, _saved, _out = self._run({}, self._script())
        self.assertNotIn("aos_core_rag_delete_corpus", log.tools())
        self.assertEqual(log.calls[0]["args"]["tables"]["t1"]["key_columns"], ["id"])   # same tables as the graph, whole rows
        bad = self._script()
        bad["aos_core_rag_create_corpus"] = {"status": "ERROR", "message": "quota"}
        with self.assertRaises(RuntimeError) as cm:
            self._run({}, bad)
        self.assertIn("aos_core_rag_create_corpus", str(cm.exception))

    def test_rag_location(self):
        self.assertEqual(rag.rag_location({"region": "us-central1"}), "us-central1")
        self.assertEqual(rag.rag_location({"region": "US"}), rag.RAG_FALLBACK_REGION)


class StageCompareTests(unittest.TestCase):
    CQS = [{"id": "CQ-01", "type": "doc", "question": "q1", "reference_answer": "a1", "key_facts": ["f1"]},
           {"id": "CQ-02", "type": "data", "question": "q2", "reference_answer": "a2", "key_facts": []}]

    def _run(self, built=("rag", "wiki", "graph"), cq_ids=None, systems=None, judge=None):
        scores = {"rag": 90, "wiki": 70, "graph": 100}
        judged, saved = [], {}

        def fake_rag(ws, q, cfg, log):
            return {"answer": "[rag] " + q, "evidence": "ev", "sources": ["u1"]}

        def fake_agent(ws, kind, q, ctx, log):
            if kind == "wiki" and q == "q2":
                raise TimeoutError("agent timed out")      # an agent failure must be a scored result, not a stage failure
            return {"answer": f"[{kind}] {q}", "evidence": "ev", "sources": ["p1"]}

        def judge_call(args):
            judged.append(args)
            sysname = "rag" if args["answer"].startswith("[rag]") else "wiki" if args["answer"].startswith("[wiki]") else "graph"
            total = scores[sysname]
            return {"status": "SUCCESS", "scores": {"total": total}, "verdict": "PASS" if total >= 85 else "PARTIAL", "summary": "s",
                    "deductions": [{"axis": "accuracy", "points": 100 - total}] if total < 100 else []}

        class Quiet(FakeLog):
            def __init__(self, stage, emit):
                super().__init__({"aos_core_eval_rubric_judge": judge or judge_call})

        log = FakeLog({"aos_core_eval_compare": comparison()})
        ws = make_ws()
        ctx = {"pages": [{"id": "p1"}] if "wiki" in built else [], "plan": {"schema": {"nodes": []}} if "graph" in built else {}}
        with identity.bind("t", USER), mock.patch.object(rag, "McpLog", Quiet), \
                mock.patch.object(rag, "get_json", return_value=list(self.CQS)), \
                mock.patch.object(rag, "load_config", return_value={"corpus": "c/1", "embedding_model": "emb", "retrieve": {"top_k": 9}} if "rag" in built else {}), \
                mock.patch.object(rag.agent_mod, "load_context", return_value=ctx), \
                mock.patch.object(rag, "run_rag", side_effect=fake_rag), mock.patch.object(rag, "run_agent", side_effect=fake_agent), \
                mock.patch.object(rag, "put_json", side_effect=lambda l, b, n, o: saved.__setitem__(n, o)):
            events = []
            out = rag.stage_compare(ws, log, events.append, cq_ids=cq_ids, systems=systems)
        return ws, log, saved, out, judged, events

    def test_three_way_summary_and_saved_run(self):
        ws, log, saved, out, judged, events = self._run()
        self.assertEqual((out["rag"]["avg"], out["rag"]["pass"], out["graph"]["avg"], out["graph"]["pass"]), (90.0, 2, 100.0, 2))
        self.assertEqual((out["wiki"]["avg"], out["wiki"]["pass"], out["wiki"]["count"]), (35.0, 0, 2))   # (70 + 0) / 2 — the failure counts
        self.assertEqual((out["stage1_delta"], out["stage2_delta"], out["total"]), (-2.0, 3.0, 2))        # copied from aos_core_eval_compare
        self.assertIsNone(out["run"])
        run = saved["aos/ws-20260101-abc123/runs/three_way_latest.json"]
        self.assertEqual(sorted(run["results"]), ["graph", "rag", "wiki"])
        self.assertEqual(run["method"]["rag"]["retrieve"], {"top_k": 9})
        self.assertIn("stage1_rag_vs_wiki", run["comparison"])
        self.assertEqual(len([n for n in saved if "runs/three_way_" in n]), 2)                            # latest + timestamped copy
        self.assertEqual(ws["summary"]["compare"]["total"], 2)
        self.assertEqual(len([e for e in events if e.get("type") == "cq"]), 6)
        # the judge is system-blind: same arguments for every system, no system name passed
        self.assertEqual(len(judged), 5)
        for a in judged:
            self.assertFalse({"system", "agent"} & set(a))
            self.assertEqual(set(a) - {"question", "ground_truth", "key_rubrics", "answer", "evidence"}, {"project", "model", "llm_location", "lang"})
        sent = [c for c in log.calls if c["tool"] == "aos_core_eval_compare"][0]["args"]["systems"]
        self.assertEqual({s: len(v["results"]) for s, v in sent.items()}, {"rag": 2, "wiki": 2, "graph": 2})

    def test_agent_failure_is_scored_zero_not_fatal(self):
        _ws, log, saved, _out, _judged, _events = self._run()
        run = saved["aos/ws-20260101-abc123/runs/three_way_latest.json"]
        failed = [r for r in run["results"]["wiki"] if r["id"] == "CQ-02"][0]
        self.assertEqual((failed["score"], failed["verdict"], failed["answer"]), (0, "FAIL", ""))
        self.assertIn("TimeoutError", failed["error"])
        self.assertIn("TimeoutError", failed["judge_summary"])
        sent = [c for c in log.calls if c["tool"] == "aos_core_eval_compare"][0]["args"]["systems"]["wiki"]["results"]
        self.assertEqual([(r["id"], r["score"], r["error"]) for r in sent], [("CQ-01", 70, False), ("CQ-02", 0, True)])

    def test_judge_failure_scores_zero(self):
        _ws, _log, saved, out, _j, _e = self._run(judge={"status": "ERROR", "message": "judge down"})
        self.assertEqual((out["rag"]["avg"], out["rag"]["pass"]), (0.0, 0))
        row = saved["aos/ws-20260101-abc123/runs/three_way_latest.json"]["results"]["rag"][0]
        self.assertEqual((row["verdict"], row["deductions"]), ("FAIL", []))

    def test_missing_system_refuses_to_run(self):
        with self.assertRaises(RuntimeError) as cm:
            self._run(built=("wiki", "graph"))
        self.assertIn("rag", str(cm.exception))

    def test_partial_runs_are_returned_but_never_stored_as_the_latest(self):
        ws, log, saved, out, _j, _e = self._run(built=("wiki", "graph"), systems=["wiki", "graph"])
        self.assertEqual(saved, {})
        self.assertNotIn("compare", ws["summary"])
        self.assertNotIn("aos_core_eval_compare", log.tools())
        self.assertEqual(out["run"]["systems_run"], ["wiki", "graph"])
        _ws, _log, saved, out, _j, _e = self._run(cq_ids=["CQ-01"])
        self.assertEqual((saved, out["total"]), ({}, 1))


# ============================================================================================ read side · cleanup · markdown
class ThreeWayViewTests(unittest.TestCase):
    def test_latest_reports_run_corpus_and_prerequisites(self):
        ws = make_ws(wiki={"status": "done"}, graph={"status": "error"}, rag={"status": "done"})
        cfg = {"corpus": "c/1", "location": "asia-northeast3", "embedding_model": "emb", "retrieve": {"top_k": 9}, "fingerprint": "secret-not-needed"}
        with mock.patch.object(three_way, "get_json", return_value=full_run()), mock.patch.object(three_way.rag_mod, "load_config", return_value=cfg):
            out = three_way.latest(ws)
        self.assertEqual((out["status"], out["run"]["ws_id"], out["rag"]["exists"], out["rag"]["retrieve"]), ("OK", "ws-x", True, {"top_k": 9}))
        self.assertNotIn("fingerprint", out["rag"])
        self.assertEqual(out["built"], {"wiki": True, "graph": False, "cqs": False})
        self.assertEqual(out["stages"]["rag"]["status"], "done")
        with mock.patch.object(three_way, "get_json", return_value=None), mock.patch.object(three_way.rag_mod, "load_config", return_value={}):
            out = three_way.latest(make_ws())
        self.assertEqual((out["run"], out["rag"]), (None, {"exists": False}))

    def _delete(self, cfg, script, info=USER, allowed=True):
        ws = make_ws(rag={"status": "done"}, compare={"status": "done"})
        ws["summary"]["rag"] = {"units": 5}
        log, saved = FakeLog(script), {}
        with identity.bind("t", info), mock.patch.object(three_way, "McpLog", lambda stage, emit: log), \
                mock.patch.object(three_way, "can_write", return_value=(allowed, "allowed-project")), \
                mock.patch.object(three_way.rag_mod, "load_config", return_value=dict(cfg)), \
                mock.patch.object(three_way, "put_json", side_effect=lambda l, b, n, o: saved.__setitem__(n, o)), \
                mock.patch.object(three_way, "save") as save, mock.patch.object(three_way, "append_calls"):
            out = three_way.delete_corpus(ws)
        return ws, log, saved, out, save

    def test_delete_corpus(self):
        cfg = {"corpus": "c/1", "fingerprint": "fp", "embedding_model": "emb"}
        ws, log, saved, out, save = self._delete(cfg, {"aos_core_rag_delete_corpus": {"status": "SUCCESS", "deleted": True}})
        self.assertEqual((out["status"], out["deleted"], out["rag"]["exists"]), ("OK", True, False))
        self.assertEqual(log.calls[0]["args"]["corpus"], "c/1")
        new = saved["aos/ws-20260101-abc123/rag/config.json"]
        self.assertEqual((new["corpus"], new["deleted_corpus"], new["fingerprint"]), ("", "c/1", "fp"))
        self.assertTrue(new["deleted_at"])
        self.assertNotIn("rag", ws["stages"])                          # compare refuses to run until rag is rebuilt
        self.assertEqual(ws["stages"]["compare"]["status"], "done")    # the measured run is kept as a record
        self.assertTrue(ws["summary"]["rag"]["deleted_at"])
        save.assert_called_once()

    def test_delete_corpus_edge_cases(self):
        _ws, log, saved, out, _s = self._delete({}, {})
        self.assertEqual((out["status"], out["deleted"], log.calls, saved), ("OK", False, [], {}))
        ws, _log, saved, out, _s = self._delete({"corpus": "c/1"}, {"aos_core_rag_delete_corpus": {"status": "ERROR", "message": "403 denied"}})
        self.assertEqual((out["status"], saved), ("ERROR", {}))
        self.assertIn("403", out["message"])
        self.assertIn("rag", ws["stages"])                              # nothing forgotten when the delete failed
        _ws, _log, saved, out, _s = self._delete({"corpus": "c/1"}, {"aos_core_rag_delete_corpus": {"status": "SUCCESS", "deleted": False, "exists": False}})
        self.assertEqual((out["deleted"], out["existed"], saved["aos/ws-20260101-abc123/rag/config.json"]["corpus"]), (True, False, ""))
        with self.assertRaises(WsError) as cm:                           # same write guard as the build stages
            self._delete({"corpus": "c/1"}, {}, info=RUNTIME, allowed=False)
        self.assertEqual(cm.exception.code, "WRITE_BLOCKED")

    def test_markdown_never_renders_missing_or_placeholder_results(self):
        self.assertIn("Not measured yet", three_way.render_markdown(None, "en", "ko"))
        self.assertIn("--lang ko", three_way.render_markdown(None, "en", "ko"))
        self.assertIn("아직 측정 결과가 없습니다", three_way.render_markdown({"results": {}}, "ko", "en"))
        ph = three_way.render_markdown(full_run(placeholder=True), "en")
        self.assertIn("placeholder", ph)
        self.assertNotIn("|", ph)                                        # no table, no number

    def test_markdown_copies_the_numbers_and_reports_ties_and_losses(self):
        md = three_way.render_markdown(full_run(), "en")
        self.assertIsNone(HANGUL.search(md))
        for needle in ("Stage 1 — RAG vs OKF Wiki", "Stage 2 — OKF Wiki vs Graph", "Final — RAG vs OKF Wiki vs Graph",
                       "| Average score (of 100) | 90.0 | 88.0 | -2.0 |",   # the wiki scoring below RAG is printed as is
                       "| Average score (of 100) | 88.0 | 91.0 | +3.0 |", "| PASS | 2/2 | 1/2 | -1 |", "| OKF Wiki wins · ties · losses | | 1 · 0 · 1 | |",
                       "| `doc` | 1 | 90.0 | 90.0 | 80.0 | RAG = OKF Wiki (tie) |", "| `data` | 1 | 50.0 | 60.0 | 95.0 | Graph |",
                       "answer model `m`", "embedding `emb-x`", '{"top_k": 7}', "measured 2026-11-15"):
            self.assertIn(needle, md)
        ko = three_way.render_markdown(full_run(), "ko")
        self.assertIn("1단계 — RAG vs OKF 위키", ko)
        self.assertIn("RAG = OKF 위키 (동률)", ko)
        self.assertEqual(three_way.best_of({"rag": 1.0, "wiki": 1.0, "graph": 1.0}), ["rag", "wiki", "graph"])
        self.assertEqual(three_way.best_of({"rag": None}), [])

    def test_field_scale_loader(self):
        with mock.patch.object(three_way, "RESULTS_DIR", os.path.join(ROOT, "no-such-dir")):
            out = three_way.field_scale("en")
        self.assertEqual((out["available"], out["run"], out["placeholder"]), (False, None, False))
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            _dump(os.path.join(d, "en.json"), full_run(placeholder=True))
            _dump(os.path.join(d, "ko.json"), {"results": {}})                     # wiki+graph only → not a three-way result
            with mock.patch.object(three_way, "RESULTS_DIR", d):
                en, ko, other = three_way.field_scale("en"), three_way.field_scale("ko"), three_way.field_scale("fr")
        self.assertEqual((en["available"], en["placeholder"], ko["available"], other["lang"]), (True, True, False, "en"))
        info = three_way.pack_info("en")
        self.assertTrue(info["synthetic"])
        self.assertEqual(info["cqs"], len(_load(os.path.join(three_way.PACK_DIR, "en", "cqs.json"))["cqs"]))
        self.assertEqual(len(info["types"]), 10)
        self.assertIsNone(HANGUL.search(json.dumps(info["types"], ensure_ascii=False)))
        self.assertEqual(three_way.pack_info("ko")["docs"], info["docs"])


# ============================================================================================ shipped pack · docs · UI strings
class PackAndDocsTests(unittest.TestCase):
    def test_field_scale_pack_is_reproducible(self):
        r = subprocess.run([sys.executable, os.path.join(three_way.PACK_DIR, "generate.py"), "--check"], capture_output=True, text=True, timeout=300)
        self.assertEqual(r.returncode, 0, r.stdout[-800:] + r.stderr[-800:])

    def test_shipped_results_are_consistent_with_the_pack(self):
        for lang in ("ko", "en"):
            res = three_way.field_scale(lang)
            if not res["available"]:
                continue                                                 # not measured yet is allowed; a broken file is not
            run = res["run"]
            ids = [c["id"] for c in _load(os.path.join(three_way.PACK_DIR, lang, "cqs.json"))["cqs"]]
            self.assertEqual([c["id"] for c in run["cqs"]], ids, lang)
            self.assertEqual(run["comparison"]["cq_count"], len(ids), lang)
            s1 = run["comparison"]["stage1_rag_vs_wiki"]
            self.assertEqual((s1["scope"], s1["count"], s1["excluded_count"]), ("doc_only", 43, 7), lang)
            self.assertEqual(run["comparison"]["stage2_wiki_vs_graph"]["scope"], "all_unified", lang)
            self.assertEqual(run["comparison"]["final_three_way"]["scope"], "all_unified", lang)
            for s in three_way.SYSTEMS:
                self.assertEqual(sorted(r["id"] for r in run["results"][s]), sorted(ids), f"{lang}/{s}")
                rows = run["results"][s]
                avg = round(sum(r["score"] for r in rows) / len(rows), 1)   # the stored summary is the mean of the stored rows
                self.assertEqual(run["comparison"]["final_three_way"]["summaries"][s]["avg"], avg, f"{lang}/{s}")

    def test_readme_tables_match_the_result_files(self):
        r = subprocess.run([sys.executable, os.path.join(ROOT, "benchmarks", "render_results.py"), "--check"], capture_output=True, text=True, timeout=120)
        self.assertEqual(r.returncode, 0, "README tables differ from data/field_scale_pack/results — run benchmarks/render_results.py\n" + r.stdout)
        for name in ("README.md", "README.ko.md"):
            text = _read(os.path.join(ROOT, name))
            for pl in ("en", "ko"):
                self.assertIn(f"<!-- GOAL296_RESULTS:{pl}:BEGIN -->", text, name)
                self.assertIn(f"<!-- GOAL296_RESULTS:{pl}:END -->", text, name)

    def test_ui_strings_exist_in_both_languages(self):
        js = _read(os.path.join(STATIC, "studio.js"))
        i18n = _load(os.path.join(STATIC, "studio_i18n.json"))
        keys = set(re.findall(r'T\("(cmp\.[A-Za-z0-9.]+[A-Za-z0-9])"\)', js)) | set(re.findall(r'T\("(cmp\.[A-Za-z0-9.]+[A-Za-z0-9])", \{', js)) | {f"cmp.why{i}" for i in (1, 2, 3, 4)} | {f"cmp.sys.{s}" for s in three_way.SYSTEMS}
        keys |= {"rail.compare", "build.s.rag", "build.s.rag.d", "build.s.compare", "build.s.compare.d"}
        self.assertGreater(len(keys), 50)
        for k in sorted(keys):
            self.assertIn(k, i18n["ko"], k)
            self.assertIn(k, i18n["en"], k)
            self.assertIsNone(HANGUL.search(i18n["en"][k]), k)
        self.assertEqual({k for k in i18n["en"] if k.startswith("cmp.")}, {k for k in i18n["ko"] if k.startswith("cmp.")})
        self.assertIn('"studio/compare"', js)
        self.assertIn('["studio/compare", "rail.compare"]', js)
        self.assertIn('id="cmp-placeholder"', js)                         # placeholder results are always labelled
        self.assertIn("b.placeholder ?", js)
        css = _read(os.path.join(STATIC, "studio.css"))
        for cls in (".cmp-kpis", ".cmp-answers", ".cmp-row.on", ".cmp-d.neg"):
            self.assertIn(cls, css)


# ============================================================================================ HTTP routes
class RouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.httpd = ThreadingStudioServer(("127.0.0.1", 0), StudioHandler)
        cls.base = f"http://127.0.0.1:{cls.httpd.server_address[1]}"
        threading.Thread(target=cls.httpd.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def setUp(self):
        self.ws = make_ws(wiki={"status": "done"}, graph={"status": "done"}, cqs={"status": "done"})
        self.patches = [mock.patch("src.identity.resolve", return_value={"mode": "runtime", "token": None, "principal": "rt@test", "expires_in": None, "user_identity": False}),
                        mock.patch("src.web.v5_routes._ws_ref", side_effect=lambda data: self.ws)]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()

    def post(self, path, body, raw=False):
        req = urllib.request.Request(self.base + path, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                data = r.read()
                return r.status, data.decode() if raw else json.loads(data)
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    def get(self, path):
        with urllib.request.urlopen(self.base + path, timeout=20) as r:
            return r.status, json.loads(r.read())

    def test_field_scale_route(self):
        with mock.patch.object(three_way, "RESULTS_DIR", os.path.join(ROOT, "no-such-dir")):
            code, body = self.get("/api/v5/bench/field-scale?lang=ko")
        self.assertEqual((code, body["status"], body["lang"], body["available"]), (200, "OK", "ko", False))
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            _dump(os.path.join(d, "en.json"), full_run(placeholder=True))
            with mock.patch.object(three_way, "RESULTS_DIR", d):
                code, body = self.get("/api/v5/bench/field-scale")           # default language is EN
        self.assertEqual((code, body["lang"], body["available"], body["placeholder"]), (200, "en", True, True))
        self.assertEqual(body["run"]["comparison"]["stage1_rag_vs_wiki"]["delta_points"], -2.0)
        self.assertTrue(body["pack"]["synthetic"])

    def test_compare_latest_route(self):
        with mock.patch.object(three_way, "get_json", return_value=full_run()), \
                mock.patch.object(three_way.rag_mod, "load_config", return_value={"corpus": "c/1", "retrieve": {"top_k": 9}}):
            code, body = self.post("/api/v5/compare/latest", {"lang": "en", "ws": {"bucket": "b", "ws_id": "ws-20260101-abc123"}})
        self.assertEqual((code, body["status"], body["rag"]["exists"], body["built"]["wiki"]), (200, "OK", True, True))
        self.assertEqual(body["run"]["comparison"]["final_three_way"]["summaries"]["graph"]["avg"], 91.0)

    def test_rag_delete_route_respects_the_write_guard(self):
        with mock.patch.object(three_way, "can_write", return_value=(False, "allowed-project")):
            code, body = self.post("/api/v5/rag/delete", {"lang": "en", "ws": {"bucket": "b", "ws_id": "x"}})
        self.assertEqual((code, body["status"]), (403, "WRITE_BLOCKED"))
        self.assertIn("allowed-project", body["message"])
        log = FakeLog({"aos_core_rag_delete_corpus": {"status": "SUCCESS", "deleted": True}})
        with mock.patch.object(three_way, "can_write", return_value=(True, "")), mock.patch.object(three_way, "McpLog", lambda s, e: log), \
                mock.patch.object(three_way.rag_mod, "load_config", return_value={"corpus": "c/1"}), mock.patch.object(three_way, "put_json"), \
                mock.patch.object(three_way, "save"), mock.patch.object(three_way, "append_calls"):
            code, body = self.post("/api/v5/rag/delete", {"lang": "en", "ws": {"bucket": "b", "ws_id": "x"}})
        self.assertEqual((code, body["status"], body["deleted"], body["rag"]["exists"]), (200, "OK", True, False))
        self.assertEqual(log.tools(), ["aos_core_rag_delete_corpus"])

    def _events(self, body):
        code, text = self.post("/api/v5/build", body, raw=True)
        self.assertEqual(code, 200)
        return [json.loads(line) for line in text.splitlines() if line.strip()]

    def test_build_route_runs_optional_stages_and_rejects_unknown_ones(self):
        ev = self._events({"lang": "en", "ws": {"bucket": "b", "ws_id": "x"}, "stage": "rag-all"})
        self.assertEqual((ev[-1]["type"], ev[-1]["status"]), ("error", "BAD_REQUEST"))
        with mock.patch.object(pipeline, "can_write", return_value=(False, "allowed-project")):
            ev = self._events({"lang": "en", "ws": {"bucket": "b", "ws_id": "x"}, "stage": "rag"})
        self.assertEqual((ev[-1]["type"], ev[-1]["status"]), ("error", "WRITE_BLOCKED"))     # a corpus is created in the workspace project
        with mock.patch.object(pipeline, "can_write", return_value=(True, "")), mock.patch.object(pipeline, "save"), mock.patch.object(pipeline, "append_calls"), \
                mock.patch.object(pipeline, "_parsed", return_value={"docs": [], "tables": []}), \
                mock.patch.object(pipeline.rag_mod, "stage_rag", return_value={"units": 3, "corpus": "c/1"}):
            ev = self._events({"lang": "en", "ws": {"bucket": "b", "ws_id": "x"}, "stage": "rag"})
        self.assertEqual([e["type"] for e in ev], ["stage", "stage", "result"])
        self.assertEqual((ev[0]["label"], ev[-1]["record"]["status"], ev[-1]["record"]["summary"]["units"]), ("S6 RAG baseline", "done", 3))
        self.assertEqual(ev[-1]["ws"]["stages"]["rag"]["status"], "done")


if __name__ == "__main__":
    unittest.main()
