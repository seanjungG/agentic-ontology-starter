# -*- coding: utf-8 -*-
"""Unit tests for the UCC sub-pages (GOAL-230): section splitting, comment validation, routes (no network)."""
import json
import os
import sys
import threading
import unittest
import urllib.request
from http.server import ThreadingHTTPServer

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, BASE)

from src.web import ucc_pages  # noqa: E402
from src.web.studio_server import StudioHandler  # noqa: E402

SAMPLE = """# Title

| 항목 | 내용 |
| :--- | :--- |
| 버전 | v9 |

## 1. First

text

```mermaid
flowchart LR
  A --> B
```

### 1.1 sub (stays inside)

## 2. Second

```text
## not a heading (inside fence)
```
"""


class SplitSections(unittest.TestCase):
    def test_split_at_h1_h2_only(self):
        secs = ucc_pages.split_sections(SAMPLE)
        self.assertEqual([s["title"] for s in secs], ["Title", "1. First", "2. Second"])
        self.assertEqual([s["id"] for s in secs], ["s00", "s01", "s02"])
        self.assertIn("### 1.1 sub", secs[1]["markdown"])
        self.assertIn("## not a heading", secs[2]["markdown"])
        self.assertIn("```mermaid", secs[1]["markdown"])

    def test_published_docs_have_many_sections(self):
        for d in ("brd", "sdd", "onepager", "discovery"):
            doc = ucc_pages.load_doc(d)
            self.assertIsNotNone(doc, f"{d}.md must be published (ucc/scripts/publish_to_starter.py)")
            self.assertGreaterEqual(doc["section_count"], 5 if d in ("onepager", "discovery") else 8)
            self.assertTrue(doc["version"].startswith("v"))
            # no internal IDs leak into the shared docs
            full = "\n".join(s["markdown"] for s in doc["sections"])
            for tag in ("GOAL-", "TASK-", "BACKLOG-"):
                self.assertNotIn(tag, full, f"{d}: internal id {tag} leaked")

    def test_english_edition_matches_korean_structure(self):
        for d in ("brd", "sdd", "onepager", "discovery"):
            ko, en = ucc_pages.load_doc(d, "ko"), ucc_pages.load_doc(d, "en")
            self.assertIsNotNone(en, f"{d}_en.md must be published")
            self.assertEqual(en["lang"], "en")
            self.assertEqual(ko["section_count"], en["section_count"], f"{d}: section ids must align across languages")
            self.assertEqual([s["level"] for s in ko["sections"]], [s["level"] for s in en["sections"]])
            full = "\n".join(s["markdown"] for s in en["sections"])
            self.assertFalse(any("\uac00" <= ch <= "\ud7a3" for ch in full), f"{d}_en: Hangul left in English edition")
            self.assertEqual(en["langs"], ["ko", "en"])
        self.assertEqual(ucc_pages.load_doc("brd", "xx")["lang"], "ko")  # unknown lang falls back to ko

    def test_manifest_demo_url(self):
        m = ucc_pages.docs_payload()
        self.assertTrue(m["demo_url"].startswith("https://"))
        self.assertEqual(set(m["docs"]) & {"brd", "sdd", "onepager", "discovery"}, {"brd", "sdd", "onepager", "discovery"})
        self.assertEqual(m["langs"], ["ko", "en"])
        self.assertEqual(m["docs"]["brd"]["en"]["version"], m["docs"]["brd"]["ko"]["version"])
        self.assertEqual(m["docs"]["onepager"]["en"]["version"], m["docs"]["onepager"]["ko"]["version"])
        self.assertEqual(m["docs"]["discovery"]["en"]["version"], m["docs"]["discovery"]["ko"]["version"])


class ValidateComment(unittest.TestCase):
    def setUp(self):
        self.doc = ucc_pages.load_doc("brd")

    def test_rejects_bad_doc_and_section(self):
        self.assertEqual(ucc_pages.validate_comment({"doc": "x", "section_id": "s01", "text": "a"}, None)[0], "doc must be 'brd' or 'sdd'")
        self.assertEqual(ucc_pages.validate_comment({"doc": "brd", "section_id": "zz", "text": "a"}, self.doc)[0], "unknown section_id")
        self.assertEqual(ucc_pages.validate_comment({"doc": "brd", "section_id": "s99", "text": "a"}, self.doc)[0], "unknown section_id")

    def test_rejects_empty_and_long(self):
        self.assertEqual(ucc_pages.validate_comment({"doc": "brd", "section_id": "s01", "text": "  "}, self.doc)[0], "text is empty")
        self.assertIn("longer", ucc_pages.validate_comment({"doc": "brd", "section_id": "s01", "text": "x" * 2001}, self.doc)[0])

    def test_normalizes(self):
        err, f = ucc_pages.validate_comment({"doc": "BRD", "section_id": "s01", "text": " hi ", "author": "  Cholho   Kim ", "quote": "q" * 500}, self.doc)
        self.assertIsNone(err)
        self.assertEqual(f["author"], "Cholho Kim")
        self.assertEqual(len(f["quote"]), 300)
        self.assertEqual(f["section_title"], self.doc["sections"][1]["title"])
        err, f = ucc_pages.validate_comment({"doc": "brd", "section_id": "s01", "text": "a"}, self.doc)
        self.assertEqual(f["author"], "익명")
        self.assertEqual(f["lang"], "ko")
        err, f = ucc_pages.validate_comment({"doc": "brd", "section_id": "s01", "text": "a", "lang": "en"}, self.doc)
        self.assertEqual((f["author"], f["lang"]), ("Anonymous", "en"))

    def test_delete_validation_before_network(self):
        self.assertEqual(ucc_pages.delete_comment({"doc": "brd", "id": "bad"})[0], 400)
        self.assertEqual(ucc_pages.delete_comment({"doc": "brd", "id": "20261019T140817_230a6c"})[0], 401)

    def test_rate_limit(self):
        key = "unit-test-key"
        ucc_pages._rate.pop(key, None)
        for _ in range(ucc_pages.RATE_LIMIT_PER_MIN):
            self.assertTrue(ucc_pages._rate_ok(key))
        self.assertFalse(ucc_pages._rate_ok(key))


class Routes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), StudioHandler)
        cls.port = cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def get(self, path):
        with urllib.request.urlopen(f"http://127.0.0.1:{self.port}{path}", timeout=5) as r:
            return r.status, r.headers.get("Content-Type", ""), r.read()

    def test_pages_and_apis(self):
        for p in ("/ucc", "/ucc/brd", "/ucc/sdd", "/ucc/onepager", "/ucc/discovery"):
            st, ct, body = self.get(p)
            self.assertEqual(st, 200)
            self.assertIn("text/html", ct)
            self.assertIn(b'id="ucc-demo"', body)
            self.assertNotIn(b"back-to-ucc", body)
        st, _, body = self.get("/api/ucc/doc?id=sdd")
        self.assertEqual(st, 200)
        self.assertEqual(json.loads(body)["id"], "sdd")
        st, _, body = self.get("/api/ucc/doc?id=onepager")
        self.assertEqual(st, 200)
        self.assertEqual(json.loads(body)["id"], "onepager")
        st, _, body = self.get("/api/ucc/doc?id=onepager&lang=en")
        d_op = json.loads(body)
        self.assertEqual((d_op["lang"], d_op["id"]), ("en", "onepager"))
        st, _, body = self.get("/api/ucc/doc?id=discovery")
        self.assertEqual(st, 200)
        self.assertEqual(json.loads(body)["id"], "discovery")
        st, _, body = self.get("/api/ucc/doc?id=discovery&lang=en")
        d_dc = json.loads(body)
        self.assertEqual((d_dc["lang"], d_dc["id"]), ("en", "discovery"))
        st, _, body = self.get("/api/ucc/doc?id=sdd&lang=en")
        d = json.loads(body)
        self.assertEqual((d["lang"], d["title"]), ("en", "SDD — Solution Design"))
        st, _, body = self.get("/ucc/brd?lang=en")
        self.assertEqual(st, 200)
        self.assertIn(b'id="lang-toggle"', body)
        st, _, body = self.get("/api/ucc/docs")
        self.assertIn("demo_url", json.loads(body))

    def test_post_validation_before_network(self):
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}/api/ucc/comments", method="POST",
                                     data=json.dumps({"doc": "brd", "section_id": "nope", "text": "x"}).encode(), headers={"Content-Type": "application/json"})
        try:
            urllib.request.urlopen(req, timeout=5)
            self.fail("expected 400")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 400)
            self.assertEqual(json.loads(e.read())["message"], "unknown section_id")


if __name__ == "__main__":
    unittest.main()
