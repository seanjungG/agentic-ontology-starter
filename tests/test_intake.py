# -*- coding: utf-8 -*-
"""Starter v6 intake (GOAL-243): catalog · template · upload/convert · GCS/Drive · types · deploy plan · S3 kind pass-through.
Core MCP is mocked (no GCP calls): every McpLog call goes through `src.aos.ws.call_core_mcp_tool`."""
import base64
import json
import os
import re
import sys
import threading
import unittest
import urllib.error
import urllib.request
from unittest import mock

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, BASE)

from src import identity  # noqa: E402
from src.aos import intake, pipeline, sources  # noqa: E402
from src.aos.ws import WsError, clean_sources, clean_template, new_workspace  # noqa: E402
from src.web.studio_server import StudioHandler, ThreadingStudioServer  # noqa: E402

HANGUL = re.compile(r"[가-힣]")
WS_ID = "ws-20261022-abc123"
ENV = {"project": "my-project-1", "bucket": "my-bucket", "region": "asia-northeast3"}
USER = {"mode": "token", "principal": "user@example.com"}


class FakeMcp:
    """Records calls; `handlers[tool]` returns the structured result (default: SUCCESS {})."""

    def __init__(self, handlers=None):
        self.handlers = dict(handlers or {})
        self.calls = []
        self.objects = {}

    def __call__(self, tool, args, url=None, timeout_s=120, access_token=None):
        self.calls.append((tool, args))
        if tool in self.handlers:
            h = self.handlers[tool]
            return h(args) if callable(h) else h
        if tool == "storage_upload_object":
            self.objects[(args["bucket"], args["name"])] = args.get("content_base64") or base64.b64encode(args.get("text", "").encode()).decode()
            return {"status": "SUCCESS"}
        if tool == "storage_read_object":
            b64 = self.objects.get((args["bucket"], args["name"]))
            if b64 is None:
                return {"status": "ERROR", "error": {"http_status": 404, "message": "not found"}}
            return {"status": "SUCCESS", "content_base64": b64}
        return {"status": "SUCCESS"}

    def tools(self):
        return [t for t, _ in self.calls]


def unknown(tool):
    return {"status": "ERROR", "error": {"message": f"Unknown Builder Core MCP tool: '{tool}'. Available tools: []"}}


CONVERTED = {"status": "SUCCESS", "source_ext": ".pdf", "method": "gemini_multimodal", "markdown": "# Claims manual\n\n## 1. Scope\nText 100 KRW",
             "fidelity": {"score": 0.93, "grade": "A", "method": "recall", "token_recall": 0.95, "number_recall": 1.0},
             "stats": {"pages": 3, "headings": 2, "tables": 0, "list_items": 0},
             "detected": {"type": "manual", "confidence": 0.8, "strategy": "direct", "reason": "ok"}, "notes": [], "telemetry": {}}


class TemplateAndSourcesTests(unittest.TestCase):
    def test_clean_template(self):
        tpl = clean_template({"flow": {"id": "D", "agents": ["wiki"], "data_type": "P1", "question_type": "W1"}, "target": "own",
                              "services": [{"id": "gcs"}, {"id": "drive"}, {"id": "Bad Id"}], "stages": ["prepare", "convert", "x y"],
                              "setup_script": "rm -rf /"})
        self.assertEqual((tpl["flow"], tpl["target"], tpl["services"], tpl["stages"], tpl["agents"]), ("D", "own", ["gcs", "drive"], ["prepare", "convert"], ["wiki"]))
        self.assertEqual((tpl["data_type"], tpl["question_type"]), ("P1", "W1"))
        self.assertNotIn("setup_script", tpl)
        self.assertEqual(clean_template({"flow": "Z"}), {})
        self.assertEqual(clean_template(None), {})
        self.assertEqual(clean_template({"flow": "b", "target": "mars"})["target"], "sandbox")

    def test_new_workspace_template_and_legacy(self):
        ws = new_workspace({"env": ENV, "template": {"flow": "C", "services": ["gcs", "bigquery"]}}, "en")
        self.assertEqual(ws["template"]["flow"], "C")
        self.assertEqual(new_workspace({"env": ENV}, "ko")["template"], {})  # older clients: no template

    def test_sources_keep_kind_strategy_conversion(self):
        s = clean_sources({"docs": [{"name": "a.md", "origin": "drive", "uri": "gs://b/a.md", "kind": "faq!", "strategy": "typed",
                                     "conversion": {"fidelity": 0.9, "pdf": "gs://b/a.pdf", "obj": object()}},
                                    {"name": "b.md", "origin": "upload", "uri": "gs://b/b.md", "strategy": "weird"}]})
        a, b = s["docs"]
        self.assertEqual((a["kind"], a["strategy"], a["conversion"]["fidelity"]), ("faq", "typed", 0.9))
        self.assertNotIn("obj", a["conversion"])
        self.assertNotIn("strategy", b)

    def test_kind_of_and_gcs_listing(self):
        self.assertEqual([intake.kind_of(n) for n in ("a.PDF", "b.md", "c.csv", "d.exe")], ["convert", "doc", "table", None])
        fake = FakeMcp({"storage_list_objects": {"status": "SUCCESS", "items": [{"name": "in/a.pdf", "size": 10}, {"name": "in/b.md", "size": 5},
                                                                                {"name": "in/c.csv", "size": 3}, {"name": "in/d.zip", "size": 1}]}})
        with mock.patch("src.aos.ws.call_core_mcp_tool", fake):
            r = sources.list_gcs(intake.McpLog("gcs", None), "gs://my-bucket/in/")
        self.assertEqual([(d["name"], d.get("convert", False)) for d in r["docs"]], [("a.pdf", True), ("b.md", False)])
        self.assertEqual((len(r["tables"]), len(r["other"])), (1, 1))


class IntakeTests(unittest.TestCase):
    def test_catalog_and_missing_tool(self):
        fake = FakeMcp({"aos_core_catalog": {"status": "SUCCESS", "flows": [{"id": "A"}], "services": [], "targets": [], "catalog_version": "1"}})
        with mock.patch("src.aos.ws.call_core_mcp_tool", fake):
            self.assertEqual(intake.catalog("en")["flows"], [{"id": "A"}])
        with mock.patch("src.aos.ws.call_core_mcp_tool", FakeMcp({"aos_core_catalog": unknown("aos_core_catalog")})):
            with self.assertRaises(WsError) as cm:
                intake.catalog("en")
        self.assertEqual(cm.exception.code, "MCP_UPDATE_NEEDED")
        self.assertIsNone(HANGUL.search(cm.exception.to_dict("en")["message"]))

    def test_template_passes_selection(self):
        fake = FakeMcp({"aos_core_compose_template": lambda a: {"status": "SUCCESS", "flow": {"id": a["flow"]}, "target": a["target"],
                                                                     "services": [{"id": s} for s in a["services"]], "tool": "x", "version": "1"}})
        with mock.patch("src.aos.ws.call_core_mcp_tool", fake):
            r = intake.template({"flow": "D", "services": ["drive"], "target": "own", "env": ENV, "ws_id": WS_ID}, "ko")
        self.assertEqual((r["status"], r["flow"]["id"], r["target"]), ("OK", "D", "own"))
        self.assertNotIn("tool", r)
        self.assertEqual(fake.calls[0][1]["project"], "my-project-1")

    def test_upload_pdf_converts_and_stores_markdown(self):
        fake = FakeMcp({"aos_core_convert_document": CONVERTED})
        with mock.patch("src.aos.ws.call_core_mcp_tool", fake), identity.bind("t", USER):
            r = intake.upload({"env": ENV, "ws_id": WS_ID, "name": "Claims Manual.pdf", "content_base64": base64.b64encode(b"%PDF-1.4 x").decode()}, "en")
        self.assertEqual((r["status"], r["kind"], r["converted"]), ("OK", "doc", True))
        e = r["entry"]
        self.assertEqual(e["name"], "Claims_Manual.md")
        self.assertEqual(e["uri"], f"gs://my-bucket/aos/{WS_ID}/converted/Claims_Manual.md")
        self.assertEqual((e["kind"], e["strategy"], e["conversion"]["fidelity"], e["conversion"]["grade"], e["conversion"]["pages"]),
                         ("manual", "direct", 0.93, "A", 3))
        self.assertEqual(e["conversion"]["pdf"], f"gs://my-bucket/aos/{WS_ID}/raw/Claims_Manual.pdf")  # the PDF itself is the source
        self.assertIn(("my-bucket", f"aos/{WS_ID}/converted/Claims_Manual.md"), fake.objects)
        self.assertTrue(r["markdown_preview"].startswith("# Claims manual"))
        self.assertEqual(fake.tools(), ["storage_upload_object", "aos_core_convert_document", "storage_upload_object"])

    def test_upload_text_and_csv_unchanged(self):
        fake = FakeMcp()
        with mock.patch("src.aos.ws.call_core_mcp_tool", fake), identity.bind("t", USER):
            md = intake.upload({"env": ENV, "ws_id": WS_ID, "name": "guide.md", "text": "# Guide\nhello"}, "ko")
            csv = intake.upload({"env": ENV, "ws_id": WS_ID, "name": "Claims.csv", "text": "id,amt\n1,10\n2,20\n"}, "ko")
        self.assertEqual((md["kind"], md["entry"]["chars"]), ("doc", 13))
        self.assertEqual((csv["kind"], csv["entry"]["name"], csv["entry"]["rows"]), ("table", "claims", 2))
        self.assertNotIn("aos_core_convert_document", fake.tools())
        with self.assertRaises(ValueError), identity.bind("t", USER):
            intake.upload({"env": ENV, "ws_id": WS_ID, "name": "evil.exe", "text": "x"}, "ko")

    def test_upload_xlsx_sheets_become_tables(self):
        res = dict(CONVERTED, source_ext=".xlsx", method="stdlib", sheets_csv=[{"name": "Rates", "rows": 2, "csv": "a,b\n1,2\n3,4\n"}])
        fake = FakeMcp({"aos_core_convert_document": res})
        with mock.patch("src.aos.ws.call_core_mcp_tool", fake), identity.bind("t", USER):
            r = intake.upload({"env": ENV, "ws_id": WS_ID, "name": "plan.xlsx", "content_base64": base64.b64encode(b"PK..").decode()}, "ko")
        self.assertEqual([(t["name"], t["rows"]) for t in r["tables"]], [("plan_rates", 2)])

    def test_upload_blocked_for_runtime_outside_write_projects(self):
        with mock.patch("src.aos.ws.call_core_mcp_tool", FakeMcp()), mock.patch.dict(os.environ, {"STARTER_WRITE_PROJECTS": "starter-proj"}):
            with self.assertRaises(WsError) as cm:
                intake.upload({"env": ENV, "ws_id": WS_ID, "name": "a.md", "text": "x"}, "en")
        self.assertEqual(cm.exception.code, "WRITE_BLOCKED")

    def test_convert_gcs(self):
        fake = FakeMcp({"aos_core_convert_document": CONVERTED})
        fake.objects[("src-bucket", "in/a.pdf")] = base64.b64encode(b"%PDF").decode()
        with mock.patch("src.aos.ws.call_core_mcp_tool", fake), identity.bind("t", USER):
            r = intake.convert_gcs({"env": ENV, "ws_id": WS_ID, "uri": "gs://src-bucket/in/a.pdf", "pdf_mode": "gemini"}, "ko")
        self.assertEqual((r["entry"]["origin"], r["entry"]["conversion"]["source"], r["entry"]["conversion"]["pdf"]),
                         ("gcs", "gs://src-bucket/in/a.pdf", "gs://src-bucket/in/a.pdf"))
        self.assertEqual(fake.calls[1][1]["pdf_mode"], "gemini")

    def test_drive_list_import_and_scope_error(self):
        fake = FakeMcp({"drive_list_files": {"status": "SUCCESS", "files": [
            {"id": "1", "name": "F", "mimeType": "application/vnd.google-apps.folder"},
            {"id": "2", "name": "Guide", "mimeType": "application/vnd.google-apps.document"},
            {"id": "3", "name": "deck.pptx", "mimeType": "application/x"}, {"id": "4", "name": "x.zip", "mimeType": "application/zip"}]},
            "drive_get_file": {"status": "SUCCESS", "file": {"id": "2", "name": "Guide"}, "exports": [
                {"ext": ".md", "mime_type": "text/markdown", "content_base64": base64.b64encode(b"# Guide\n## A\nx").decode()},
                {"ext": ".pdf", "mime_type": "application/pdf", "content_base64": base64.b64encode(b"%PDF").decode()}]},
            "aos_core_convert_document": dict(CONVERTED, source_ext=".md", method="stdlib")})
        with mock.patch("src.aos.ws.call_core_mcp_tool", fake), identity.bind("t", USER):
            ls = intake.drive_list({"url": "https://drive.google.com/drive/folders/abc"})
            imp = intake.drive_import({"env": ENV, "ws_id": WS_ID, "file_id": "2"}, "en")
        self.assertEqual([f["kind"] for f in ls["files"]], ["folder", "google_doc", "convert", "other"])
        self.assertEqual((imp["entry"]["origin"], imp["entry"]["conversion"]["drive_id"]), ("drive", "2"))
        self.assertTrue(imp["entry"]["conversion"]["pdf"].endswith("/converted/Guide.pdf"))
        err = {"status": "ERROR", "error": {"http_status": 403, "message": "drive.files.list HTTP 403: insufficient authentication scopes"}}
        with mock.patch("src.aos.ws.call_core_mcp_tool", FakeMcp({"drive_list_files": err})):
            r = intake.drive_list({"url": "abc"})
        self.assertEqual((r["status"], r["code"]), ("ERROR", "DRIVE_ACCESS"))

    def test_classify_and_types(self):
        fake = FakeMcp({"aos_core_classify_documents": lambda a: {"status": "SUCCESS", "documents": [
            {"type": "faq", "confidence": 0.4, "strategy": "typed", "reason": "r", "ask": True, "method": "rules"} for _ in a["docs"]],
            "summary": {"direct": 0, "typed": len(a["docs"]), "reconvert": 0}, "types_catalog": [{"id": "faq"}], "question": {"text": "q"}}})
        fake.objects[("my-bucket", "x/a.md")] = base64.b64encode("Q: 왜?\nA: 그래서".encode()).decode()
        src = {"docs": [{"name": "a.md", "origin": "upload", "uri": "gs://my-bucket/x/a.md", "conversion": {"fidelity": 0.8, "source_ext": ".pdf"}}]}
        with mock.patch("src.aos.ws.call_core_mcp_tool", fake):
            r = intake.classify({"env": ENV, "ws_id": WS_ID, "sources": src, "user_types": {"gs://my-bucket/x/a.md": "faq"}}, "ko")
        sent = fake.calls[-1][1]["docs"][0]
        self.assertEqual((sent["ext"], sent["fidelity"], sent["user_type"]), (".pdf", 0.8, "faq"))
        self.assertEqual((r["documents"][0]["type"], r["documents"][0]["ask"], r["summary"]["typed"]), ("faq", True, 1))
        merged = intake.apply_types(src, [{"uri": "gs://my-bucket/x/a.md", "type": "faq", "strategy": "typed"}, {"uri": "gs://other", "type": "x"}])
        self.assertEqual((merged["docs"][0]["kind"], merged["docs"][0]["strategy"]), ("faq", "typed"))
        with self.assertRaises(ValueError):
            intake.classify({"env": ENV, "sources": {"docs": []}}, "ko")

    def test_deploy_plan_args(self):
        fake = FakeMcp({"aos_core_deploy_plan": lambda a: {"status": "SUCCESS", "verdict": "not_ready" if a["sandbox"] else "ready", "steps": [], "args": a}})
        ws = {"ws_id": WS_ID, "env": dict(ENV, dataset="aos_x", graph_name="G"), "summary": {"eval": {"score": 100, "total": 8}}, "template": {"target": "sandbox"}}
        with mock.patch("src.aos.ws.call_core_mcp_tool", fake):
            r = intake.deploy_plan(ws, {"target": "mcp_server"}, "token", "http://core/mcp", "en")
        self.assertEqual((r["status"], r["verdict"]), ("OK", "not_ready"))
        a = r["args"]
        self.assertEqual((a["target"], a["identity_mode"], a["core_mcp_url"], a["summary"]["eval"]["score"]), ("mcp_server", "token", "http://core/mcp", 100))
        self.assertTrue(a["workspace_uri"].endswith(f"/aos/{WS_ID}/workspace.json"))


class PipelineTests(unittest.TestCase):
    def test_wiki_doc_kind_only_for_typed(self):
        self.assertNotIn("kind", pipeline.wiki_doc({"doc_id": "D", "title": "t", "text": "x", "kind": "policy", "strategy": "direct"}))
        self.assertEqual(pipeline.wiki_doc({"doc_id": "D", "title": "t", "text": "x", "kind": "faq", "strategy": "typed"})["kind"], "faq")
        self.assertEqual(pipeline.wiki_doc({"doc_id": "D", "title": "t", "text": "x"}), {"doc_id": "D", "title": "t", "text": "x"})

    def test_stage_wiki_sends_types_to_core_mcp(self):
        sent = {}

        def compile_wiki(a):
            sent.update(a)
            return {"status": "SUCCESS", "pages": [{"id": "SUM-1"}], "files": {"a.md": "x"}, "index": {}, "gates": [], "gates_passed": 7,
                    "gates_total": 7, "counts": {"summary": 1}}
        fake = FakeMcp({"aos_core_compile_wiki": compile_wiki})
        pf = f"aos/{WS_ID}/"
        docs = [{"doc_id": "FAQ", "title": "FAQ", "text": "Q", "kind": "faq", "strategy": "typed"},
                {"doc_id": "POL", "title": "Policy", "text": "P", "kind": "policy", "strategy": "direct"}]
        fake.objects[("my-bucket", pf + "parsed/docs.json")] = base64.b64encode(json.dumps(docs).encode()).decode()
        fake.objects[("my-bucket", pf + "parsed/tables.json")] = base64.b64encode(b"[]").decode()
        ws = {"ws_id": WS_ID, "lang": "en", "env": dict(ENV, model="gemini-4-argon", vertex_location="global"), "scenario": {"objective": "o"}}
        events = []
        with mock.patch("src.aos.ws.call_core_mcp_tool", fake), identity.bind("t", USER):
            out = pipeline.stage_wiki(ws, intake.McpLog("wiki", events.append), events.append)
        self.assertEqual([d.get("kind") for d in sent["docs"]], ["faq", None])
        self.assertEqual([d.get("strategy") for d in sent["docs"]], ["typed", "direct"])
        self.assertEqual(out["gates_passed"], 7)
        self.assertTrue(any(e.get("step") == "wiki_types" for e in events))


class IntakeApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p = mock.patch("src.gcp_client.token_principal", lambda *a, **k: "runtime-sa@example.iam.gserviceaccount.com")
        cls.p.start()
        cls.httpd = ThreadingStudioServer(("127.0.0.1", 0), StudioHandler)
        cls.base = f"http://127.0.0.1:{cls.httpd.server_address[1]}"
        threading.Thread(target=cls.httpd.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.p.stop()

    def post(self, path, body):
        req = urllib.request.Request(self.base + path, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    def test_bootstrap_upload_limits(self):
        with urllib.request.urlopen(self.base + "/api/v5/bootstrap?lang=en", timeout=20) as r:
            b = json.loads(r.read())
        self.assertEqual(b["max_upload_bytes"], 12 * 1024 * 1024)
        self.assertIn(".pdf", b["upload_ext"])
        self.assertTrue(b["version"].startswith("v6."))

    def test_catalog_route_and_mcp_update_needed(self):
        ok = FakeMcp({"aos_core_catalog": {"status": "SUCCESS", "flows": [{"id": "A"}, {"id": "D"}], "services": [], "targets": []}})
        with mock.patch("src.aos.ws.call_core_mcp_tool", ok):
            code, body = self.post("/api/v5/catalog", {"lang": "en"})
        self.assertEqual((code, body["status"], len(body["flows"])), (200, "OK", 2))
        with mock.patch("src.aos.ws.call_core_mcp_tool", FakeMcp({"aos_core_catalog": unknown("aos_core_catalog")})):
            code, body = self.post("/api/v5/catalog", {"lang": "en"})
        self.assertEqual((code, body["status"]), (501, "MCP_UPDATE_NEEDED"))
        self.assertIsNone(HANGUL.search(body["message"]))

    def test_types_save_before_workspace(self):
        src = {"docs": [{"name": "a.md", "origin": "upload", "uri": "gs://b/a.md"}], "tables": []}
        code, body = self.post("/api/v5/types/save", {"lang": "en", "sources": src, "decisions": [{"uri": "gs://b/a.md", "type": "manual", "strategy": "typed"}]})
        self.assertEqual((code, body["persisted"]), (200, False))
        self.assertEqual((body["sources"]["docs"][0]["kind"], body["sources"]["docs"][0]["strategy"]), ("manual", "typed"))

    def test_upload_rejects_unknown_extension(self):
        code, body = self.post("/api/v5/upload", {"lang": "en", "identity": {"mode": "runtime"}, "env": {"project": "my-project-1", "bucket": "my-bucket"},
                                                  "ws_id": WS_ID, "name": "virus.exe", "text": "x"})
        self.assertIn(code, (400, 403))


class LangOnlyTest(unittest.TestCase):
    """Bilingual Core MCP catalogs (doc_types) must not leak Hangul into EN responses."""

    CAT = {"status": "SUCCESS", "flows": [{"id": "A", "title": "Flow A"}], "services": [], "targets": [], "sources": ["upload"],
           "catalog_version": "1.0.0", "doc_types": [{"id": "policy", "ko": "규정", "en": "Policy", "desc_ko": "조항", "desc_en": "Articles"}]}

    def test_catalog_en_has_no_hangul(self):
        fake = FakeMcp({"aos_core_catalog": self.CAT})
        with mock.patch("src.aos.ws.call_core_mcp_tool", fake):
            out = intake.catalog("en")
        self.assertEqual(out["doc_types"], [{"id": "policy", "en": "Policy", "desc_en": "Articles"}])
        self.assertFalse(HANGUL.search(json.dumps(out, ensure_ascii=False)))

    def test_catalog_ko_keeps_korean(self):
        fake = FakeMcp({"aos_core_catalog": self.CAT})
        with mock.patch("src.aos.ws.call_core_mcp_tool", fake):
            out = intake.catalog("ko")
        self.assertEqual(out["doc_types"], [{"id": "policy", "ko": "규정", "desc_ko": "조항"}])


if __name__ == "__main__":
    unittest.main()


def test_identity_free_routes_survive_bad_identity(monkeypatch):
    """GOAL-244: an incomplete SA/token left in the browser must not break the step-1 catalog."""
    from src.web import v5_routes
    from src import identity
    monkeypatch.setattr(v5_routes.intake, "catalog", lambda lang: {"status": "OK", "flows": []})
    monkeypatch.setattr(identity, "resolve",
                        lambda spec, lang="ko": (_ for _ in ()).throw(identity.IdentityError("SA_FORMAT", "x", "x"))
                        if spec else {"mode": "runtime", "token": None, "principal": "rt", "expires_in": None, "user_identity": False})
    out = []
    bad = {"identity": {"mode": "impersonate", "sa": ""}, "lang": "ko"}
    assert v5_routes.handle_post("/api/v5/catalog", bad, lambda b, c: out.append((c, b)), None, None)
    assert out[-1][0] == 200 and out[-1][1]["status"] == "OK"
    assert v5_routes.handle_post("/api/v5/check", bad, lambda b, c: out.append((c, b)), None, None)
    assert out[-1][0] == 401
