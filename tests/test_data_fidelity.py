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

    def test_t4_row_without_provenance_fails(self):
        self._put("data/input/03_tables/items.csv", "item_id,name,provenance,source_ref\nA1,x,CUSTOMER_PROVIDED,items.xlsx\nA2,y,,\n")
        r = self._gate0()
        self.assertEqual(r["status"], "FAIL")
        self.assertIn("1 row(s) without provenance", r["errors"][0])

    def test_t4_unapproved_synthetic_rows_fail(self):
        self._put("data/input/03_tables/items.csv", "item_id,provenance,source_ref\nA1,SYNTHETIC_DEMO,agent\n")
        r = self._gate0()
        self.assertEqual(r["status"], "FAIL")
        self.assertIn("synthetic.allowed is not true", r["errors"][0])

    def test_t7_sample_file_in_project_fails(self):
        shutil.copytree(os.path.join(BASE_DIR, "data/input/03_tables"), os.path.join(self.root, "data/input/03_tables"))
        r = self._gate0()
        self.assertEqual(r["status"], "FAIL")
        self.assertTrue(any("same content as starter file" in e for e in r["errors"]), r["errors"])

    def test_auto_track_without_tables_is_lite(self):
        from src.project_context import resolve_track
        self.assertEqual(resolve_track({"root": self.root, "track": "auto", "tables": []})[0], "lite")
        self._put("data/input/03_tables/items.csv", "item_id,provenance,source_ref\nA1,CUSTOMER_PROVIDED,items.xlsx\n")
        p = {"root": self.root, "track": "auto", "tables": ["data/input/03_tables/items.csv"]}
        self.assertEqual(resolve_track(p)[0], "standard")
        self.assertEqual(self._gate0()["status"], "PASS")

    def _cq(self, cqs):
        import json
        self._put("data/output/doc_chunks.jsonl", json.dumps(
            {"chunk_id": "DOC_CHUNK_001", "content": "제1조(목적) 사업자는 등록하여야 한다.", "provenance": "EXTRACTED"},
            ensure_ascii=False) + "\n")
        self._put("data/input/04_cq/golden_competency_questions.json", json.dumps(cqs, ensure_ascii=False))

    def test_t5_cq_with_fictional_entity_is_rejected(self):
        from pipeline.validator import load_cqs
        base = {"evidence_type": "citation", "expected_citation": {"chunk_id": "DOC_CHUNK_001", "quote": "사업자는 등록하여야 한다."},
                "expected_facts": ["등록"]}
        self._cq([{**base, "cq_id": "OK", "query": "사업자는 무엇을 해야 하는가?"}])
        self.assertEqual(len(load_cqs(self.root)), 1)
        self._cq([{**base, "cq_id": "BAD", "query": "PROD-0012 제품의 '글로우 세럼' 광고 문구는 적법한가?"}])
        with self.assertRaises(SystemExit):
            load_cqs(self.root)
        self._cq([{**base, "cq_id": "BAD2", "query": "사업자는?", "expected_citation": {"chunk_id": "DOC_CHUNK_001", "quote": "사업자는 신고한다."}}])
        with self.assertRaises(SystemExit):
            load_cqs(self.root)

    def test_t6_report_without_run_record_is_unmeasured(self):
        import json
        from src.web.studio_server import build_eval_summary
        rows = [{"cq_id": f"CQ-{i}", "status": "PASSED"} for i in range(20)]
        self._put("data/output/cq_benchmark_report.json", json.dumps({"total_cqs": 20, "passed": 20, "test_results": rows}))
        g = build_eval_summary(self.root)["golden"]
        self.assertEqual((g["status"], g["passed"], g["score_label"]), ("UNMEASURED", None, "미측정 (실행 기록 없음)"))
        rows = [{**r, "executed_at": "2026-09-29T00:00:00+09:00"} for r in rows]
        self._put("data/output/input_manifest.json", "{}")
        self._put("data/output/cq_benchmark_report.json", json.dumps(
            {"total_cqs": 20, "passed": 20, "test_results": rows, "run_id": "r1", "input_manifest_sha256": "old"}))
        self.assertEqual(build_eval_summary(self.root)["golden"]["status"], "STALE")

    def test_t9_dual_engine_checklist_and_spanner_sql_rewrite(self):
        self._put("customer_doc/rules.txt", ORIGINAL)
        m = extract_project(self.root)
        self.assertEqual(m.get("graph_engine"), "bigquery")
        chk = m.get("graph_engine_checklist", {})
        for key in ("source_system", "latency_slo", "concurrency", "write_freshness", "data_scale"):
            self.assertIn(key, chk)
        from src.agent.mcp_server import DomainMcpServer
        srv = DomainMcpServer(root_dir=BASE_DIR)
        rewritten = srv._to_spanner_sql(
            f"SELECT COUNT(*) FROM GRAPH_TABLE(`{srv.graph}` MATCH (d:DeviceNode) COLUMNS (d.device_id))"
        )
        self.assertIn("GRAPH_TABLE(`STARTER_ONTOLOGY_GRAPH`", rewritten)
        self.assertNotIn(srv.fq, rewritten)

    def test_t10_track_driven_project_workbench(self):
        from src.web.project_workbench import recommend_gcp_resources, get_workbench_state
        rec_std = recommend_gcp_resources("saas-sla-demo", "standard", "bigquery")
        self.assertEqual(rec_std["dataset_id"], "saas_sla_demo_dw")
        self.assertEqual(rec_std["graph_name"], "SAAS_SLA_DEMO_ONTOLOGY_GRAPH")
        rec_lite = recommend_gcp_resources("policy-lite", "lite", "none")
        self.assertEqual(rec_lite["graph_name"], "")
        wb_lite = get_workbench_state({"project_id": "tmp", "root": self.root, "track": "lite", "graph_engine": "none"})
        self.assertEqual(wb_lite["stages"]["stage3"]["status"], "BYPASSED")
        wb_std = get_workbench_state({"project_id": "tmp", "root": self.root, "track": "standard", "graph_engine": "bigquery"})
        self.assertEqual(wb_std["stages"]["stage3"]["status"], "PENDING")


if __name__ == "__main__":
    unittest.main()

