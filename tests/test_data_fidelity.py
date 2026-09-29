# Copyright (c) 2026 Sean Jung (seanjung@google.com). All Rights Reserved.
# Non-Commercial Use Only: Methodology & Docs under CC BY-NC-ND 4.0; Source Code under PolyForm Noncommercial License 1.0.0.
# Commercial use, paid consulting/SI/PoC delivery, or production deployment requires prior written permission from seanjung@google.com.

# -*- coding: utf-8 -*-
"""
Data fidelity checks (no GCP calls). Each test builds a throw-away project folder.

    .venv/bin/python -m unittest tests.test_data_fidelity -v
"""
import os
import shutil
import sys
import tempfile
import unittest

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, BASE_DIR)
from pipeline.extract_docs import extract_project  # noqa: E402
from pipeline.ingest import build_chunks  # noqa: E402
from pipeline.validator import run_gate0  # noqa: E402

ORIGINAL = "\n\n".join(
    f"제{i}조(항목{i}) 이 조는 테스트용 원문 문장이다. 사업자는 제{i}조에 따른 의무를 지켜야 한다. 위반하면 과태료를 부과한다."
    for i in range(1, 41))


class DataFidelityTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.root, "customer_doc"))
        self.addCleanup(shutil.rmtree, self.root)

    def _put(self, rel, text):
        path = os.path.join(self.root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        return path

    def _gate0(self):
        return run_gate0(build_chunks(root=self.root)[1], root=self.root)

    def test_extracted_original_passes_gate0(self):
        self._put("customer_doc/rules.txt", ORIGINAL)
        extract_project(self.root)
        r = self._gate0()
        self.assertEqual(r["status"], "PASS", r)
        self.assertEqual(r["documents"][0]["articles"], 40)

    def test_t2_summary_markdown_fails_gate0(self):
        self._put("data/input/01_guides/summary.md", "## 요약\n- 사업자는 의무를 지킨다.\n<!-- DOC_CHUNK_001: 요약 -->\n")
        r = self._gate0()
        self.assertEqual(r["status"], "FAIL")
        self.assertIn("not written by pipeline/extract_docs.py", r["errors"][0])

    def test_t2_edited_extraction_fails_gate0(self):
        self._put("customer_doc/rules.txt", ORIGINAL)
        extract_project(self.root)
        md = os.path.join(self.root, "data/input/01_guides/rules.md")
        with open(md, encoding="utf-8") as f:
            head = f.read()[:400]
        self._put("data/input/01_guides/rules.md", head)  # shortened by hand
        r = self._gate0()
        self.assertEqual(r["status"], "FAIL")
        self.assertIn("changed after extraction", r["errors"][0])

    def test_t2_dropped_chunks_fail_ratio(self):
        self._put("customer_doc/rules.txt", ORIGINAL)
        extract_project(self.root)
        chunks = build_chunks(root=self.root)[1]
        r = run_gate0(chunks[: len(chunks) // 2], root=self.root)
        self.assertEqual(r["status"], "FAIL")
        self.assertLess(r["documents"][0]["char_ratio"], 0.95)
        self.assertTrue(r["documents"][0]["articles_missing"])

    def test_t8_page_without_text_needs_ocr(self):
        from pypdf import PdfWriter
        w = PdfWriter()
        w.add_blank_page(width=595, height=842)
        with open(os.path.join(self.root, "customer_doc/scan.pdf"), "wb") as f:
            w.write(f)
        m = extract_project(self.root)
        self.assertEqual(m["status"], "NEEDS_OCR")
        self.assertEqual(m["needs_ocr"][0]["pages_without_text"], [1])
        self.assertFalse(os.path.exists(os.path.join(self.root, "data/input/01_guides/scan.md")))
        self.assertEqual(self._gate0()["status"], "FAIL")

    def test_chunks_carry_source_and_limit(self):
        self._put("customer_doc/notes.md", "# 개요\n" + "문장입니다. " * 600 + "\n\n# 부록\n마지막 문단.\n")
        extract_project(self.root)
        chunks = build_chunks(root=self.root)[1]
        self.assertTrue(all(len(c["content"]) <= 1500 for c in chunks))
        self.assertTrue(all(c["source_original"] == "notes.md" and c["page_from"] == 1 for c in chunks))
        self.assertEqual(self._gate0()["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
