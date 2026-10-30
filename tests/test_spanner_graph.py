# -*- coding: utf-8 -*-
"""GOAL-256: Semantic Graph default = Spanner Graph — offline tests for src/aos/spanner_graph.py and the engine defaults."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.aos import spanner_graph as SG  # noqa: E402
from src.aos import ws as W  # noqa: E402

ND = {
    "graph_name": "AOS_ONTOLOGY_GRAPH",
    "nodes": [
        {"label": "Device", "table": "N_Device", "key": "device_id", "display": "device_name", "source": {"kind": "table", "table": "devices"},
         "properties": ["device_id", "device_name", "price", "launched"], "types": {"device_id": "STRING", "device_name": "STRING", "price": "INT64", "launched": "DATE"}},
        {"label": "Plan", "table": "N_Plan", "key": "plan_id", "display": "plan_name", "source": {"kind": "table", "table": "plans"},
         "properties": ["plan_id", "plan_name", "fee"], "types": {"plan_id": "INT64", "plan_name": "STRING", "fee": "NUMERIC"}},
        {"label": "Rule", "table": "N_Rule", "key": "wiki_id", "display": "title", "source": {"kind": "wiki", "layers": ["concept"]},
         "properties": ["wiki_id", "title"], "types": {"wiki_id": "STRING", "title": "STRING"}},
        {"label": "Concept", "table": "N_Concept", "key": "wiki_id", "display": "title", "source": {"kind": "wiki", "layers": ["entity"]},
         "properties": ["wiki_id", "title"], "types": {"wiki_id": "STRING", "title": "STRING"}},
    ],
    "edges": [
        {"label": "ON_PLAN", "from": "Device", "to": "Plan", "table": "E_ON_PLAN_Device_Plan", "source": {"kind": "fk", "column": "plan_id"}},
        {"label": "APPLIES_TO", "from": "Rule", "to": "Device", "table": "E_APPLIES_TO_Rule_Device", "source": {"kind": "wiki_bridge"}},
        {"label": "RELATES", "from": "Rule", "to": "Concept", "table": "E_RELATES_Rule_Concept", "source": {"kind": "wiki_relation", "types": []}},
    ],
}
ENV = {"project": "seanjung-agentic-starter", "dataset": "aos_20261029_abc123", "region": "asia-northeast3", "graph_name": "AOS_ONTOLOGY_GRAPH",
       "graph_engine": "spanner", "spanner_instance": "starter-spanner", "spanner_database": "starter_graph_db"}
WS = "ws-20261029-abc123"


class EngineDefaults(unittest.TestCase):
    def test_new_workspace_default_is_spanner(self):
        d = W.env_defaults()
        self.assertEqual(d["graph_engine"], "spanner")
        self.assertEqual(d["spanner_database"], SG.DEFAULT_DATABASE)
        env = W.clean_env({}, WS)
        self.assertEqual(env["graph_engine"], "spanner")

    def test_bigquery_stays_selectable_and_legacy_is_bigquery(self):
        self.assertEqual(W.clean_env({"graph_engine": "bigquery"}, WS)["graph_engine"], "bigquery")
        self.assertEqual(SG.engine({"project": "p"}), "bigquery")  # workspace created before GOAL-256
        with self.assertRaises(W.WsError):
            W.clean_env({"graph_engine": "neo4j"}, WS)

    def test_names(self):
        self.assertEqual(SG.table_prefix(WS), "ws20261029_abc123_")
        self.assertEqual(SG.graph_name(ENV, WS), "AOS_ONTOLOGY_GRAPH_20261029_abc123")
        self.assertEqual(SG.db_path(ENV), "projects/seanjung-agentic-starter/instances/starter-spanner/databases/starter_graph_db")


class Ddl(unittest.TestCase):
    def test_tables_and_graph(self):
        spec = SG.ddl(ND, WS, SG.graph_name(ENV, WS))
        self.assertEqual(len(spec["table_statements"]), 7)
        dev = spec["table_statements"][0]
        self.assertIn("CREATE TABLE `ws20261029_abc123_N_Device`", dev)
        self.assertIn("`device_id` STRING(MAX) NOT NULL", dev)
        self.assertIn("`price` INT64", dev)
        self.assertIn("`launched` DATE", dev)
        self.assertIn("PRIMARY KEY (`device_id`)", dev)
        self.assertIn("`fee` FLOAT64", spec["table_statements"][1])  # NUMERIC → FLOAT64
        fk = next(s for s in spec["table_statements"] if "E_ON_PLAN" in s)
        self.assertIn("src_key STRING(MAX) NOT NULL", fk)
        self.assertIn("dst_key INT64 NOT NULL", fk)  # FK edge key types follow the node keys
        rel = next(s for s in spec["table_statements"] if "E_RELATES" in s)
        self.assertIn("relation STRING(MAX)", rel)
        g = spec["graph_statement"]
        self.assertTrue(g.startswith("CREATE OR REPLACE PROPERTY GRAPH AOS_ONTOLOGY_GRAPH_20261029_abc123"))
        self.assertIn("SOURCE KEY (src_key) REFERENCES `ws20261029_abc123_N_Device` (`device_id`)", g)
        self.assertIn("DESTINATION KEY (dst_key) REFERENCES `ws20261029_abc123_N_Plan` (`plan_id`)", g)
        self.assertIn("LABEL APPLIES_TO", g)

    def test_drop_only_this_workspace(self):
        existing = ["CREATE TABLE `ws20261029_abc123_N_Device` (x INT64) PRIMARY KEY (x)",
                    "CREATE TABLE ws20261029_zzz999_N_Device (x INT64) PRIMARY KEY (x)",
                    "CREATE TABLE starter_table (x INT64) PRIMARY KEY (x)",
                    "CREATE PROPERTY GRAPH AOS_ONTOLOGY_GRAPH_20261029_abc123 NODE TABLES (`ws20261029_abc123_N_Device`)",
                    "CREATE PROPERTY GRAPH OTHER_GRAPH NODE TABLES (starter_table)"]
        drops = SG.drop_statements(existing, WS, SG.graph_name(ENV, WS))
        self.assertEqual(drops[0], "DROP PROPERTY GRAPH AOS_ONTOLOGY_GRAPH_20261029_abc123")
        self.assertEqual(drops[1:], ["DROP TABLE `ws20261029_abc123_N_Device`"])


class Values(unittest.TestCase):
    def test_spanner_json_values(self):
        self.assertEqual(SG.sp_value("INT64", 12), "12")
        self.assertEqual(SG.sp_value("INT64", "7.0"), "7")
        self.assertEqual(SG.sp_value("FLOAT64", "1.5"), 1.5)
        self.assertIs(SG.sp_value("BOOL", "true"), True)
        self.assertEqual(SG.sp_value("DATE", "2026-10-29"), "2026-10-29")
        self.assertEqual(SG.sp_value("TIMESTAMP", "1.7616E9"), "2025-10-27T21:20:00.000000Z")
        self.assertIsNone(SG.sp_value("STRING(MAX)", None))
        self.assertEqual(SG.sp_value("STRING(MAX)", 5), "5")


class Translate(unittest.TestCase):
    def setUp(self):
        self.names = SG.name_map(ND, ENV, WS)
        self.plan = {"graph_ready": True, "spanner": {"names": self.names, "database": SG.db_path(ENV)}}

    def test_graph_table_columns_to_return(self):
        q = ("SELECT COUNT(*) AS cnt FROM GRAPH_TABLE(`seanjung-agentic-starter.aos_20261029_abc123.AOS_ONTOLOGY_GRAPH`\n"
             "  MATCH (n:Device)\n  COLUMNS (n.`device_id` AS k)\n)")
        out, unmapped = SG.to_spanner(q, self.names, ENV["project"], ENV["dataset"])
        self.assertEqual(unmapped, [])
        self.assertIn("GRAPH_TABLE(AOS_ONTOLOGY_GRAPH_20261029_abc123", out)
        self.assertIn("RETURN n.`device_id` AS k", out)
        self.assertNotIn("COLUMNS", out)
        self.assertTrue(out.rstrip().endswith(")"))

    def test_columns_inside_strings_and_nested_parens(self):
        q = ("SELECT x.first, COUNT(*) c FROM GRAPH_TABLE(`seanjung-agentic-starter.aos_20261029_abc123.AOS_ONTOLOGY_GRAPH` "
             "MATCH (a:Device {device_name: 'COLUMNS (x)'})-[:ON_PLAN]->(b:Plan) WHERE b.fee > (1 + 2) "
             "COLUMNS (a.device_name AS first, CAST(b.fee AS STRING) AS fee)) x GROUP BY x.first LIMIT 5")
        out, _ = SG.to_spanner(q, self.names, ENV["project"], ENV["dataset"])
        self.assertIn("'COLUMNS (x)'", out)  # string literal untouched
        self.assertIn("RETURN a.device_name AS first, CAST(b.fee AS STRING) AS fee) x GROUP BY", out)

    def test_table_mapping_and_routing(self):
        r = SG.route("SELECT * FROM `seanjung-agentic-starter.aos_20261029_abc123.N_Device` LIMIT 50", self.plan, ENV)
        self.assertEqual(r["target"], "spanner")
        self.assertIn("FROM `ws20261029_abc123_N_Device`", r["query"])
        r = SG.route("SELECT * FROM `seanjung-agentic-starter.aos_20261029_abc123.devices` LIMIT 5", self.plan, ENV)
        self.assertEqual(r["target"], "bigquery")  # raw source tables only live in BigQuery
        r = SG.route("SELECT * FROM `other-proj.ds.t`", self.plan, ENV)
        self.assertEqual(r["target"], "bigquery")
        r = SG.route("SELECT 1", {"graph_ready": False, "spanner": {"names": self.names}}, ENV)
        self.assertEqual(r["target"], "bigquery")


class ExpiryPurge(unittest.TestCase):
    """GOAL-259: shared starter_graph_db TTL (same 7 days as the BigQuery demo datasets)."""
    DDL = [
        "CREATE TABLE `ws20261001_aaaaaa_N_Device` (\n  `device_id` STRING(MAX) NOT NULL\n) PRIMARY KEY (`device_id`)",
        "CREATE TABLE `ws20261001_aaaaaa_E_ON_PLAN` (\n  src_key STRING(MAX) NOT NULL\n) PRIMARY KEY (src_key, dst_key)",
        "CREATE TABLE `ws20261028_bbbbbb_N_Device` (\n  `device_id` STRING(MAX) NOT NULL\n) PRIMARY KEY (`device_id`)",
        "CREATE TABLE `ws20261002_cccccc_N_Plan` (\n  `plan_id` INT64 NOT NULL\n) PRIMARY KEY (`plan_id`)",
        "CREATE TABLE `Customers` (\n  `id` INT64 NOT NULL\n) PRIMARY KEY (`id`)",
        "CREATE PROPERTY GRAPH AOS_ONTOLOGY_GRAPH_20261001_aaaaaa\n  NODE TABLES (`ws20261001_aaaaaa_N_Device`)",
        "CREATE PROPERTY GRAPH AOS_ONTOLOGY_GRAPH_20261028_bbbbbb\n  NODE TABLES (`ws20261028_bbbbbb_N_Device`)",
        "CREATE PROPERTY GRAPH FinGraph\n  NODE TABLES (`Customers`)",
    ]
    NOW = SG.datetime(2026, 10, 30, tzinfo=SG.timezone.utc)

    def test_only_expired_workspaces_graph_first(self):
        stmts, wss = SG.expired_drop_statements(self.DDL, days=7, now=self.NOW)
        self.assertEqual(stmts[0], "DROP PROPERTY GRAPH AOS_ONTOLOGY_GRAPH_20261001_aaaaaa")
        self.assertIn("DROP TABLE `ws20261001_aaaaaa_N_Device`", stmts)
        self.assertIn("DROP TABLE `ws20261001_aaaaaa_E_ON_PLAN`", stmts)
        self.assertIn("DROP TABLE `ws20261002_cccccc_N_Plan`", stmts)
        joined = "\n".join(stmts)
        self.assertNotIn("20261028_bbbbbb", joined)   # 2 days old → kept
        self.assertNotIn("Customers", joined)         # not a workspace object
        self.assertNotIn("FinGraph", joined)
        self.assertEqual(sorted(wss), ["20261001_aaaaaa", "20261002_cccccc"])

    def test_keep_current_workspace_and_disable(self):
        stmts, _ = SG.expired_drop_statements(self.DDL, days=7, now=self.NOW, keep_ws="ws-20261001-aaaaaa")
        self.assertNotIn("20261001_aaaaaa", "\n".join(stmts))
        self.assertEqual(SG.expired_drop_statements(self.DDL, days=0, now=self.NOW), ([], []))


if __name__ == "__main__":
    unittest.main()
