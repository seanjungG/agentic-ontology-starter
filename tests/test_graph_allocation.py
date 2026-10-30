# -*- coding: utf-8 -*-
"""GOAL-258: data allocation map (src/aos/graph_allocation.py) — offline tests with a synthetic, anonymized workspace."""
import json
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.aos import graph_allocation as GA  # noqa: E402

STATIC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src", "web", "static")

DESIGN = {
    "graph_name": "AOS_ONTOLOGY_GRAPH",
    "nodes": [
        {"label": "Account", "table": "N_Account", "key": "account_id", "display": "name", "source": {"kind": "table", "table": "accounts"},
         "properties": ["account_id", "name", "tier"], "types": {"account_id": "STRING", "name": "STRING", "tier": "STRING"}},
        {"label": "Order", "table": "N_Order", "key": "order_id", "display": "order_id", "source": {"kind": "table", "table": "orders"},
         "properties": ["order_id", "account_id", "amount"], "types": {"order_id": "STRING", "account_id": "STRING", "amount": "INT64"}},
        {"label": "Segment", "table": "N_Segment", "key": "wiki_id", "display": "title",
         "source": {"kind": "wiki", "layers": ["entity"], "exclude_table_backed": True},
         "properties": ["wiki_id", "title", "body_md", "policy_text"], "types": {}},
        {"label": "Rule", "table": "N_Rule", "key": "wiki_id", "display": "title", "source": {"kind": "wiki", "layers": ["concept"]},
         "properties": ["wiki_id", "title", "body_md", "sources_text"], "types": {}},
    ],
    "edges": [
        {"label": "PLACED_BY", "from": "Order", "to": "Account", "table": "E_PLACED_BY_Order_Account", "source": {"kind": "fk", "column": "account_id"}},
        {"label": "GOVERNS", "from": "Rule", "to": "Segment", "table": "E_GOVERNS_Rule_Segment", "source": {"kind": "wiki_relation", "types": ["APPLIES_TO"]}},
        {"label": "CLASSIFIES", "from": "Segment", "to": "Account", "table": "E_CLASSIFIES_Segment_Account", "source": {"kind": "wiki_bridge"}},
        {"label": "LIMITS", "from": "Rule", "to": "Order", "table": "E_LIMITS_Rule_Order", "source": {"kind": "wiki_bridge"}},
    ],
}
PAGES = [
    {"id": "SUM-GUIDE", "layer": "summary", "title": "Guide", "summary": "s", "body_md": "a\nb", "policy": [], "relations": [],
     "applies_to": [], "sources": [{"doc": "DOC-1", "section": "1"}]},
    {"id": "ENT-ACCOUNT", "layer": "entity", "title": "Account", "summary": "", "body_md": "account body", "policy": [],
     "relations": [], "applies_to": [{"table": "accounts", "where": None, "keys": None}], "sources": [{"doc": "DOC-1", "section": "2"}]},
    {"id": "ENT-GOLD", "layer": "entity", "title": "Gold segment", "summary": "", "body_md": "line1\n\nline2\nline3",
     "policy": [{"name": "min_spend", "value": 100, "unit": "USD"}], "relations": [],
     "applies_to": [{"table": "accounts", "where": {"column": "tier", "op": "=", "value": "GOLD"}, "keys": None}],
     "sources": [{"doc": "DOC-1", "section": "3"}]},
    {"id": "CON-CAP", "layer": "concept", "title": "Order cap", "summary": "", "body_md": "cap rule", "policy": [],
     "relations": [{"type": "APPLIES_TO", "target": "ENT-GOLD"}, {"type": "RELATED_TO", "target": "ENT-GOLD"}],
     "applies_to": [{"table": "orders", "where": {"column": "amount", "op": ">", "value": "50"}, "keys": None}],
     "sources": [{"doc": "DOC-2", "section": "1"}, {"doc": "DOC-2", "section": "2"}]},
]
TABLES = [
    {"name": "accounts", "row_count": 3, "pk": "account_id",
     "columns": [{"name": "account_id", "type": "STRING"}, {"name": "name", "type": "STRING"}, {"name": "tier", "type": "STRING"},
                 {"name": "load_ts", "type": "TIMESTAMP"}],
     "rows": [{"account_id": "A1", "name": "x", "tier": "GOLD"}, {"account_id": "A2", "name": "y", "tier": "GOLD"},
              {"account_id": "A3", "name": "z", "tier": "BASIC"}]},
    {"name": "orders", "row_count": 4, "pk": "order_id",
     "columns": [{"name": "order_id", "type": "STRING"}, {"name": "account_id", "type": "STRING"}, {"name": "amount", "type": "INTEGER"}],
     "rows": [{"order_id": "O1", "account_id": "A1", "amount": "70"}, {"order_id": "O2", "account_id": "A1", "amount": "20"},
              {"order_id": "O3", "account_id": "A3", "amount": 99}, {"order_id": "O4", "account_id": "A9", "amount": 10}]},
]
PLAN = {"design": DESIGN, "engine": "spanner", "node_counts": {"Account": 3, "Order": 4, "Segment": 1, "Rule": 1},
        "loads": [{"id": "edge:E_GOVERNS_Rule_Segment", "kind": "edge_rows", "row_count": 1}],
        "stats": {"table_backed": {"Account": ["ENT-ACCOUNT"]}}}


class Allocation(unittest.TestCase):
    def setUp(self):
        self.al = GA.compute(PLAN, PAGES, TABLES)

    def test_page_fates_follow_the_design_contract(self):
        fate = {p["id"]: (p["fate"], p["node"]) for p in self.al["pages"]}
        self.assertEqual(fate["SUM-GUIDE"], ("excluded", ""))  # no wiki node takes the summary layer
        self.assertEqual(fate["ENT-ACCOUNT"], ("table_note", "Account"))  # table-backed → business notes, no duplicate node
        self.assertEqual(fate["ENT-GOLD"], ("node", "Segment"))
        self.assertEqual(fate["CON-CAP"], ("node", "Rule"))
        t = self.al["totals"]
        self.assertEqual((t["pages"], t["node_rows"], t["table_notes"], t["excluded"], t["sections"]), (4, 2, 1, 1, 5))
        self.assertEqual(t["constants"], 1)

    def test_page_properties_and_edges(self):
        gold = next(p for p in self.al["pages"] if p["id"] == "ENT-GOLD")
        self.assertEqual(gold["lines"], 3)
        props = {x["name"]: x["chars"] for x in gold["properties"]}
        self.assertEqual(set(props), {"wiki_id", "title", "body_md", "policy_text"})
        self.assertEqual(props["policy_text"], len("min_spend=100USD"))
        self.assertEqual([(e["label"], e["count"]) for e in gold["edges"]], [("CLASSIFIES", 2)])  # A1, A2
        cap = next(p for p in self.al["pages"] if p["id"] == "CON-CAP")
        self.assertEqual({e["label"]: e["count"] for e in cap["edges"]}, {"GOVERNS": 1, "LIMITS": 2})  # O1, O3 (> 50)

    def test_table_path(self):
        acc = next(x for x in self.al["tables"] if x["label"] == "Account")
        self.assertEqual((acc["source_table"], acc["key"], acc["rows"], acc["rows_basis"]), ("accounts", "account_id", 3, "graph"))
        self.assertEqual([c["property"] for c in acc["columns"]], ["account_id", "name", "tier"])
        self.assertTrue(acc["columns"][0]["key"])
        self.assertEqual(acc["dropped"], ["load_ts"])
        self.assertEqual(acc["business_notes"], [{"id": "ENT-ACCOUNT", "title": "Account"}])
        order = next(x for x in self.al["tables"] if x["label"] == "Order")
        amount = next(c for c in order["columns"] if c["column"] == "amount")
        self.assertEqual((amount["type"], amount["source_type"]), ("INT64", "INTEGER"))

    def test_edge_allocation(self):
        ed = {e["label"]: e for e in self.al["edges"]}
        self.assertEqual(ed["PLACED_BY"]["basis"], {"column": "account_id", "from_table": "orders", "to_key": "account_id"})
        self.assertEqual((ed["PLACED_BY"]["count"], ed["PLACED_BY"]["count_basis"]), (3, "computed"))  # O4 → A9 has no target
        self.assertEqual((ed["GOVERNS"]["count"], ed["GOVERNS"]["count_basis"]), (1, "loaded"))
        self.assertEqual(ed["GOVERNS"]["basis"], {"types": ["APPLIES_TO"]})
        self.assertEqual((ed["CLASSIFIES"]["count"], ed["CLASSIFIES"]["count_basis"]), (2, "computed"))
        self.assertEqual(ed["CLASSIFIES"]["basis"]["conditions"][0]["text"], "tier = GOLD")
        self.assertEqual(ed["LIMITS"]["count"], 2)
        self.assertEqual(self.al["totals"]["edge_kinds"], {"fk": 1, "wiki_relation": 1, "wiki_bridge": 2})
        wn = {n["label"]: n for n in self.al["wiki_nodes"]}
        self.assertEqual(wn["Segment"]["pages"], ["ENT-GOLD"])
        self.assertTrue(wn["Segment"]["exclude_table_backed"])

    def test_sample_rows_are_marked(self):
        tables = json.loads(json.dumps(TABLES))
        tables[1]["row_count"] = 500  # only 4 rows stored → sample
        al = GA.compute(PLAN, PAGES, tables)
        ed = {e["label"]: e for e in al["edges"]}
        self.assertEqual(ed["PLACED_BY"]["count_basis"], "sample")
        self.assertEqual(ed["LIMITS"]["count_basis"], "sample")
        self.assertTrue(al["totals"]["edge_rows_partial"])
        cap = next(p for p in al["pages"] if p["id"] == "CON-CAP")
        self.assertTrue(next(e for e in cap["edges"] if e["label"] == "LIMITS")["sample"])

    def test_match_where_ops(self):
        r = {"n": "1,200", "b": "true", "s": "X"}
        self.assertTrue(GA.match_where(r, {"column": "n", "op": ">=", "value": 1200}))
        self.assertTrue(GA.match_where(r, {"column": "b", "op": "=", "value": True}))
        self.assertTrue(GA.match_where(r, {"column": "s", "op": "in", "value": ["Y", "X"]}))
        self.assertFalse(GA.match_where(r, {"column": "s", "op": "!=", "value": "X"}))
        self.assertFalse(GA.match_where(r, {"column": "missing", "op": "=", "value": 1}))
        self.assertTrue(GA.match_where(r, None))

    def test_ensure_on_read_and_never_raises(self):
        plan = json.loads(json.dumps(PLAN))
        out = GA.ensure(plan, lambda: PAGES, lambda: TABLES)
        self.assertEqual(out["allocation"]["v"], GA.VERSION)
        self.assertEqual(out["allocation"]["computed"], "on_read")
        calls = []
        GA.ensure(out, lambda: calls.append(1), lambda: calls.append(1))  # already current → loaders not called
        self.assertEqual(calls, [])
        bad = {"design": {"nodes": [{"label": "X", "source": {"kind": "table", "table": "t"}, "properties": 5}], "edges": []}}
        self.assertIn("error", GA.ensure(bad, lambda: [], lambda: [{"name": "t", "columns": [], "rows": []}])["allocation"])
        self.assertEqual(GA.ensure({}, lambda: [], lambda: []), {})  # no design → untouched

    def test_engine_neutral_and_serializable(self):
        self.assertEqual(self.al["engine"], "spanner")
        json.dumps(self.al)


class AllocationUi(unittest.TestCase):
    def test_i18n_keys_used_by_the_panel_exist_in_ko_and_en(self):
        i18n = json.load(open(os.path.join(STATIC, "studio_i18n.json"), encoding="utf-8"))
        js = open(os.path.join(STATIC, "studio.js"), encoding="utf-8").read()
        used = {k for k in re.findall(r'T\("(ga\.[A-Za-z0-9_.]+)"', js) if not k.endswith(".")}  # "ga.c." + x = dynamic prefix
        for k in ("ga.k.fk", "ga.k.wiki_relation", "ga.k.wiki_bridge", "ga.fate.node", "ga.fate.table_note", "ga.fate.excluded",
                  "ga.c.loaded", "ga.c.computed", "ga.c.sample", "ga.rows.graph", "ga.rows.source"):
            used.add(k)
        self.assertGreater(len(used), 40)
        han = re.compile(r"[\uac00-\ud7a3]")
        for k in used:
            self.assertIn(k, i18n["ko"], k)
            self.assertIn(k, i18n["en"], k)
            self.assertIsNone(han.search(i18n["en"][k]), k)
        self.assertIn("allocPanel(plan.allocation)", js)
        self.assertIn("allocNodeCard(plan.allocation, node.label)", js)


if __name__ == "__main__":
    unittest.main()
