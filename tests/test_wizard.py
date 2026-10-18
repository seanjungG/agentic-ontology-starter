# -*- coding: utf-8 -*-
"""GOAL-223 wizard tests: static serving, KO/EN parity (UI strings + data pack), recipes, and the JSON API surface.

No network: every API call here either needs no GCP access (settings, catalog, static files) or is rejected by
request validation before any GCP call (CONFIG_ERROR, unknown agent).
"""
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import unittest
import urllib.error
import urllib.request

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from src import datapack, recipes  # noqa: E402
from src.config import APP_VERSION, StarterConfig, ConfigError  # noqa: E402
from src.web.studio_server import STATIC_DIR, StudioHandler, ThreadingStudioServer, resolve_static  # noqa: E402

HANGUL = re.compile(r"[\u3131-\uD79D]")
LAB_WEB = os.path.abspath(os.path.join(ROOT, "..", "ontology_lab", "web"))


def _read(name: str) -> str:
    with open(os.path.join(STATIC_DIR, name), encoding="utf-8") as f:
        return f.read()


def _strings(obj):
    """Yields every string leaf of a JSON-like object."""
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from _strings(v)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            yield from _strings(v)


class StaticServingTests(unittest.TestCase):
    def test_wizard_files_resolve(self):
        for name, ctype in (("index.html", "text/html"), ("app.js", "javascript"), ("app.css", "text/css"), ("i18n.json", "json"),
                            ("flows.js", "javascript"), ("aolflow.js", "javascript"), ("aolflow.css", "text/css")):
            hit = resolve_static(name)
            self.assertIsNotNone(hit, name)
            self.assertIn(ctype, hit[1], name)

    def test_traversal_and_unknown_types_rejected(self):
        for name in ("../config.py", "..", "../../README.md", "sub/app.js", "studio_server.py", ".env", "app.js/..", ""):
            self.assertIsNone(resolve_static(name), name)

    def test_index_is_the_wizard_shell(self):
        html = _read("index.html")
        for ref in ("/static/aolflow.js", "/static/flows.js", "/static/app.js", "/static/app.css", "/static/aolflow.css",
                    'id="rail"', 'id="page"', 'id="lang-toggle"', 'id="chip-mcp"', 'id="chip-project"', 'id="chip-version"'):
            self.assertIn(ref, html)
        self.assertIsNone(HANGUL.search(html), "static markup must stay language-neutral (EN screen = zero Hangul)")
        self.assertNotIn("vis-network", html, "the old 6-tab page must be gone")

    def test_app_js_has_no_hard_coded_hangul(self):
        self.assertIsNone(HANGUL.search(_read("app.js")), "all UI text must come from i18n.json")

    def test_shared_renderer_copy_is_byte_identical(self):
        for name in ("aolflow.js", "aolflow.css"):
            lab = os.path.join(LAB_WEB, name)
            if not os.path.isfile(lab):
                self.skipTest("ontology_lab/ not present (public starter repo)")
            with open(lab, "rb") as a, open(os.path.join(STATIC_DIR, name), "rb") as b:
                self.assertEqual(a.read(), b.read(), name)


class I18nParityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.i18n = json.loads(_read("i18n.json"))

    def test_same_keys_and_placeholders(self):
        ko, en = self.i18n["ko"], self.i18n["en"]
        self.assertEqual(set(ko), set(en), sorted(set(ko) ^ set(en)))
        ph = re.compile(r"\{(\w+)\}")
        for k in ko:
            self.assertTrue(ko[k].strip() and en[k].strip(), k)
            self.assertEqual(set(ph.findall(ko[k])), set(ph.findall(en[k])), k)

    def test_en_has_no_hangul(self):
        bad = {k: v for k, v in self.i18n["en"].items() if HANGUL.search(v)}
        self.assertEqual(bad, {})

    def test_every_literal_key_used_by_app_js_exists(self):
        src = _read("app.js")
        used = set(re.findall(r"(?<![A-Za-z0-9_.$])t\(\"([a-z0-9_]+)\"", src))
        self.assertGreater(len(used), 100)
        self.assertEqual(sorted(used - set(self.i18n["ko"])), [])
        for n in range(1, 7):  # dynamic keys: step{n}_t/_s, s{n}_eyebrow/_title/_desc
            for k in (f"step{n}_t", f"step{n}_s", f"s{n}_eyebrow", f"s{n}_title", f"s{n}_desc"):
                self.assertIn(k, self.i18n["en"], k)


class DataParityTests(unittest.TestCase):
    """EN screen runs on the EN data set: no Hangul, same ids and numbers as KO."""

    @classmethod
    def setUpClass(cls):
        cls.ko, cls.en = datapack.catalog("ko"), datapack.catalog("en")

    def test_en_data_pack_has_no_hangul(self):
        bad = [s[:80] for s in _strings(self.en) if HANGUL.search(s)]
        self.assertEqual(bad, [])

    def test_same_ids_and_numbers(self):
        key = lambda c: (c["cq_id"], c["agent"], tuple(c["recipes"]), tuple(c["expect_numbers"]), c["source"])  # noqa: E731
        self.assertEqual([key(c) for c in self.ko["cqs"]], [key(c) for c in self.en["cqs"]])
        self.assertEqual([(t["name"], t["row_count"], tuple(t["key"]), tuple(t["recipes"])) for t in self.ko["tables"]],
                         [(t["name"], t["row_count"], tuple(t["key"]), tuple(t["recipes"])) for t in self.en["tables"]])
        self.assertEqual([p["page"] for p in self.ko["wiki"]], [p["page"] for p in self.en["wiki"]])
        self.assertEqual([[s["step_id"] for s in w["steps"]] for w in self.ko["workflows"]],
                         [[s["step_id"] for s in w["steps"]] for w in self.en["workflows"]])
        self.assertEqual(self.ko["policy"], self.en["policy"])
        self.assertEqual([d["doc_id"] for d in self.ko["docs"]], [d["doc_id"] for d in self.en["docs"]])

    def test_en_catalog_payload_has_no_hangul(self):
        from src.web.studio_server import catalog_payload
        bad = [s[:80] for s in _strings(catalog_payload("en")) if HANGUL.search(s)]
        self.assertEqual(bad, [])


class RecipeTests(unittest.TestCase):
    def test_matrix_resolves_all_nine_choices(self):
        m = recipes.matrix()
        self.assertEqual(len(m), 9)
        self.assertEqual(m["P1-W1"], {"recipe": "A", "exact": True, "reason": None})
        self.assertEqual(m["P2-W2"]["recipe"], "B")
        self.assertEqual(m["P3-W3"]["recipe"], "C")
        for k, v in m.items():
            if not v["exact"]:
                self.assertEqual(v["recipe"], "C", k)
                self.assertTrue(v["reason"]["ko"] and v["reason"]["en"], k)
        self.assertIsNone(recipes.resolve("P9", "W1"))

    def test_load_plans_per_recipe(self):
        keys = lambda r: [s["key"] for s in recipes.load_plan(r)]  # noqa: E731
        self.assertEqual(keys("A"), ["gate0", "docs", "wiki", "manifest"])
        self.assertEqual(keys("B"), ["dataset", "tables_p2", "graph", "graph_check"])
        self.assertEqual(keys("C"), ["gate0", "docs", "wiki", "dataset", "tables_p2", "tables_p3", "graph", "graph_check", "manifest"])
        for r in "ABC":
            for s in recipes.load_plan(r):
                self.assertIn(s["node"], ("gcs", "bq", "graph"))
                self.assertTrue(s["core_mcp"], s["key"])

    def test_step_plan_covers_steps_3_to_6_in_order(self):
        for r in "ABC":
            steps = [p["step"] for p in recipes.step_plan(r)]
            self.assertEqual(steps, sorted(steps))
            self.assertEqual(set(steps), {3, 4, 5, 6})
            agents = [p for p in recipes.step_plan(r) if p["step"] == 5]
            self.assertEqual(len(agents), len(recipes.RECIPES[r]["agents"]))

    def test_request_config_is_validated_and_never_takes_the_mcp_url(self):
        cfg = StarterConfig.from_request({"project_id": "my-project-1", "core_mcp_url": "http://evil.example/mcp"}, "B")
        self.assertEqual(cfg.project_id, "my-project-1")
        self.assertNotEqual(cfg.core_mcp_url, "http://evil.example/mcp")
        with self.assertRaises(ConfigError):
            StarterConfig.from_request({"dataset_id": "bad-name!"}, "C")


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

    def get(self, path):
        with urllib.request.urlopen(self.base + path, timeout=20) as r:
            return r.status, r.headers.get("Content-Type", ""), r.read()

    def post(self, path, body):
        req = urllib.request.Request(self.base + path, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    def test_index_and_static(self):
        code, ctype, body = self.get("/")
        self.assertEqual((code, "text/html" in ctype), (200, True))
        self.assertIn(b"/static/app.js", body)
        code, ctype, _ = self.get("/static/app.js")
        self.assertEqual((code, "javascript" in ctype), (200, True))
        code, ctype, body = self.get("/static/i18n.json")
        self.assertEqual(code, 200)
        self.assertEqual(set(json.loads(body)), {"ko", "en"})
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self.get("/static/..%2Fstudio_server.py")
        self.assertEqual(ctx.exception.code, 404)

    def test_health_settings_catalog(self):
        _, _, body = self.get("/health")
        self.assertEqual(json.loads(body)["version"], APP_VERSION)
        _, _, body = self.get("/api/settings")
        s = json.loads(body)
        for k in ("defaults", "graph_defaults", "write_projects", "core_mcp_url", "version", "github_url"):
            self.assertIn(k, s)
        self.assertTrue(s["core_mcp_url"].endswith("/mcp"))
        for lang in ("ko", "en"):
            _, _, body = self.get(f"/api/catalog?lang={lang}")
            c = json.loads(body)
            self.assertEqual(c["lang"], lang)
            self.assertEqual(set(c["recipes"]), {"A", "B", "C"})
            self.assertEqual(set(c["presets"]["C"]), {"wiki", "graph", "workflow"})
            if lang == "en":
                self.assertEqual([x for x in _strings(c) if HANGUL.search(x)], [])

    def test_bad_requests_are_rejected_before_any_gcp_call(self):
        code, body = self.post("/api/verify", {"recipe": "C", "lang": "en", "config": {"project_id": "Bad_Project"}})
        self.assertEqual((code, body["status"], body["field"]), (400, "CONFIG_ERROR", "project_id"))
        self.assertIsNone(HANGUL.search(body["message"]))
        code, body = self.post("/api/verify", {"recipe": "C", "lang": "ko", "config": {"bucket": "UPPER"}})
        self.assertEqual((code, body["field"]), (400, "bucket"))
        code, body = self.post("/api/agent", {"recipe": "A", "lang": "en", "agent": "workflow", "question": "x"})
        self.assertEqual(code, 400)
        code, body = self.post("/api/agent", {"recipe": "C", "lang": "en", "agent": "wiki", "question": "  "})
        self.assertEqual(code, 400)
        code, body = self.post("/api/load", {"recipe": "Z"})
        self.assertEqual(code, 400)


class NoLatexTests(unittest.TestCase):
    """Formulas reach the screen as plain text: prompts ask for it, and app.js delatex() converts leftovers."""

    def test_answer_prompts_ask_for_plain_text_formulas(self):
        from src.agent.agents import WIKI_SYS
        from src.agent.reasoning_engine import SYNTH_SYS, SYNTH_SYS_EN
        for name, prompt in (("WIKI_SYS.ko", WIKI_SYS["ko"]), ("WIKI_SYS.en", WIKI_SYS["en"]), ("SYNTH_SYS", SYNTH_SYS), ("SYNTH_SYS_EN", SYNTH_SYS_EN)):
            self.assertIn("LaTeX", prompt, name)
            self.assertIn("× (180 − 120) ÷ 180", prompt, name)
        self.assertIsNone(HANGUL.search(WIKI_SYS["en"]))
        self.assertIsNone(HANGUL.search(SYNTH_SYS_EN))

    @unittest.skipUnless(shutil.which("gjs"), "gjs (JavaScript shell) not installed")
    def test_delatex_converts_math_and_keeps_prices(self):
        src = _read("app.js")
        m = re.search(r"// delatex:start(.*?)// delatex:end", src, re.S)
        self.assertIsNotNone(m, "delatex block markers missing in app.js")
        self.assertIn("delatex(src)", src.split("function md(src)", 1)[1][:200], "md() must run delatex first")
        cases = [
            r"$$\text{penalty} = \text{ROUND}\left((450,000 - 150,000) \times \frac{180 - 120}{180}\right)$$",
            "Price is $5 and $10 per month.",
            r"Inline $x \le 180$ days and \(a \ge b\)",
            "```\n$$keep$$\n```",
            r"\[ 300,000 \cdot \frac{60}{180} \]",
        ]
        script = "//" + m.group(1) + "\nprint(JSON.stringify(" + json.dumps(cases) + ".map(delatex)));\n"
        res = subprocess.run(["gjs", "-c", script], capture_output=True, text=True, timeout=60)
        self.assertEqual(res.returncode, 0, res.stderr[-800:])
        out = json.loads(res.stdout.strip().splitlines()[-1])
        self.assertEqual(out, [
            "penalty = ROUND((450,000 - 150,000) × (180 - 120) ÷ (180))",
            "Price is $5 and $10 per month.",
            "Inline x ≤ 180 days and a ≥ b",
            "```\n$$keep$$\n```",
            "300,000 · (60) ÷ (180)",
        ])


if __name__ == "__main__":
    unittest.main()
