# -*- coding: utf-8 -*-
"""Starter v5 studio (GOAL-233): static shell, i18n parity, workspace/env validation, sources, guards, API errors.
No GCP calls (identity errors and config errors are rejected before any network call)."""
import json
import os
import re
import sys
import threading
import unittest
import urllib.error
import urllib.request

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, BASE)

from src.aos import agent as agent_mod  # noqa: E402
from src.aos import sources  # noqa: E402
from src.aos.ws import WsError, _summ, clean_env, clean_sources, default_dataset, new_ws_id  # noqa: E402
from src.web.studio_server import StudioHandler, ThreadingStudioServer  # noqa: E402

STATIC = os.path.join(BASE, "src", "web", "static")
HANGUL = re.compile(r"[가-힣]")


def _read(n):
    with open(os.path.join(STATIC, n), encoding="utf-8") as f:
        return f.read()


class StaticTests(unittest.TestCase):
    def test_i18n_keys_identical_and_en_clean(self):
        d = json.loads(_read("studio_i18n.json"))
        self.assertEqual(set(d["ko"]), set(d["en"]))
        for k, v in d["en"].items():
            if k != "lang.ko":
                self.assertIsNone(HANGUL.search(v), k)
            self.assertEqual(sorted(re.findall(r"\{\w+\}", v)), sorted(re.findall(r"\{\w+\}", d["ko"][k])), k)

    def test_literal_keys_exist(self):
        d = json.loads(_read("studio_i18n.json"))["ko"]
        used = set(re.findall(r'T\("([a-zA-Z0-9_.]+)"', _read("studio.js")))
        self.assertEqual(sorted(k for k in used if not k.endswith(".") and k not in d), [])

    def test_studio_js_has_no_hangul(self):
        self.assertIsNone(HANGUL.search(_read("studio.js")))
        self.assertIsNone(HANGUL.search(_read("studio.html")))


class WorkspaceTests(unittest.TestCase):
    def test_env_and_ids(self):
        ws = new_ws_id()
        self.assertRegex(ws, r"^ws-\d{8}-[a-z0-9]{6}$")
        env = clean_env({"project": "my-project-1", "bucket": "my-bucket"}, ws)
        self.assertEqual(env["dataset"], default_dataset(ws))
        with self.assertRaises(WsError):
            clean_env({"project": "Bad_Project"}, ws)
        with self.assertRaises(WsError):
            clean_env({"bucket": "UPPER"}, ws)

    def test_sources_and_redaction(self):
        s = clean_sources({"docs": [{"name": "a.md", "origin": "upload", "uri": "gs://b/a.md"}, {"origin": "evil", "uri": "x"}],
                           "tables": [{"name": "t-1", "origin": "bigquery", "fq": "p.d.t"}]})
        self.assertEqual((len(s["docs"]), s["tables"][0]["name"]), (1, "t_1"))
        self.assertEqual(_summ({"access_token": "tok-" + "x" * 30, "sql": "x" * 1000})["access_token"], "<redacted>")

    def test_csv_and_names(self):
        p = sources.parse_csv("ID,Amount KRW,ok,day\nA1,100,true,2026-01-01\nA2,2.5,false,2026-01-02\n")
        self.assertEqual([c["type"] for c in p["columns"]], ["STRING", "FLOAT64", "BOOL", "DATE"])
        self.assertEqual(p["columns"][1]["name"], "amount_krw")
        self.assertEqual(sources.table_name("My Claims.csv"), "my_claims")
        self.assertEqual(sources.parse_fq("p-roject.ds.t1"), ("p-roject", "ds", "t1"))
        with self.assertRaises(ValueError):
            sources.read_sample("sample:../../etc/passwd")
        self.assertEqual(len(sources.sample_sources("en")["tables"]), 6)

    def test_query_guard(self):
        g = agent_mod.guard_query
        self.assertIsNone(g("SELECT 1", "p", "d"))
        self.assertIsNotNone(g("DROP TABLE x", "p", "d"))
        self.assertIsNotNone(g("SELECT 1; DELETE FROM t", "p", "d"))
        self.assertIsNone(g("SELECT 'drop table' AS s", "p", "d"))


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.httpd = ThreadingStudioServer(("127.0.0.1", 0), StudioHandler)
        cls.base = f"http://127.0.0.1:{cls.httpd.server_address[1]}"
        threading.Thread(target=cls.httpd.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def post(self, path, body):
        req = urllib.request.Request(self.base + path, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    def test_shell_and_bootstrap(self):
        with urllib.request.urlopen(self.base + "/", timeout=20) as r:
            self.assertIn(b"studio.js", r.read())
        with urllib.request.urlopen(self.base + "/api/v5/bootstrap?lang=en", timeout=20) as r:
            b = json.loads(r.read())
        self.assertEqual([p["id"] for p in b["presets"]][-1], "custom")
        self.assertEqual(b["stages"], ["prepare", "ingest", "cqs", "wiki", "graph", "eval"])

    def test_identity_errors_before_gcp(self):
        code, body = self.post("/api/v5/identity", {"lang": "en", "identity": {"mode": "token", "token": "not-a-token"}})
        self.assertEqual((code, body["code"]), (401, "TOKEN_FORMAT"))
        code, body = self.post("/api/v5/identity", {"lang": "en", "identity": {"mode": "impersonate", "sa": "nope"}})
        self.assertEqual((code, body["code"]), (401, "SA_FORMAT"))
        code, body = self.post("/api/v5/identity", {"lang": "en", "identity": {"mode": "impersonate", "sa": "aos-x@some-project.iam.gserviceaccount.com"}})
        self.assertEqual((code, body["code"]), (401, "IMPERSONATION_DISABLED"))
        code, body = self.post("/api/v5/identity", {"identity": {"mode": "root"}})
        self.assertEqual(code, 401)


if __name__ == "__main__":
    unittest.main()
