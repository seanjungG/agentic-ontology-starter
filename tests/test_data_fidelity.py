# -*- coding: utf-8 -*-
"""
Minimal Starter Pack v3.0 Verification Suite (test_data_fidelity.py)
Verifies:
1. Minimal 5-file core structure (zero bloated slides/terraform/pipeline/methodology directories)
2. Selective Flow Presets (P1/P2/P3 x W1/W2/W3 x Gate G2-W) & v1-MCP Architecture Grid
3. 2-Tier MCP Guide (`aos-builder-core-mcp` 8 Build Tools + Runtime Domain MCP 3 Tools & Customization Recipe)
4. 3-Layer OKF Wiki, Business Rules, and W1/W2/W3 Workflows (`D4.5` Tool Bindings)
5. 6-Layer End-to-End Lineage Engine
6. Minimal `studio_server.py` HTTP Endpoints (`/`, `/health`, `/api/resources`, `/api/catalog`, `/api/assets`, `/api/graph`, `/api/eval/summary`, `/api/lineage/graph`)
"""
import json
import os
import sys
import threading
import unittest
import urllib.request

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from src.agent.mcp_server import DomainMcpServer  # noqa: E402
from src.resource_connector import (  # noqa: E402
    MCP_ARCHITECTURE_GUIDE,
    SELECTIVE_FLOW_PRESETS,
    V1_MCP_FLOW_ARCHITECTURE,
    OntologyResourceConnector,
    connect_my_resources,
)
from src.web.studio_server import ThreadingStudioServer, StudioHandler  # noqa: E402


class StarterMinimalVerificationTests(unittest.TestCase):
    def test_t1_minimal_repo_structure(self):
        removed_dirs = ["slides", "industry_cases", "pipeline", "projects", "terraform", "docs", "methodology"]
        for d in removed_dirs:
            self.assertFalse(os.path.exists(os.path.join(ROOT, d)), f"Bloated directory should be removed: {d}")
        core_files = [
            "src/resource_connector.py",
            "src/gcp_client.py",
            "src/agent/mcp_server.py",
            "src/agent/reasoning_engine.py",
            "src/web/studio_server.py",
        ]
        for f in core_files:
            self.assertTrue(os.path.isfile(os.path.join(ROOT, f)), f"Core starter file missing: {f}")

    def test_t2_selective_flow_presets_and_v1_mcp_architecture(self):
        self.assertEqual(set(SELECTIVE_FLOW_PRESETS.keys()), {"flow_p1_w1", "flow_p2_w2", "flow_p3_w3"})
        self.assertEqual(SELECTIVE_FLOW_PRESETS["flow_p1_w1"]["paths"], ["P1"])
        self.assertEqual(SELECTIVE_FLOW_PRESETS["flow_p1_w1"]["workflows"], ["W1"])
        self.assertEqual(SELECTIVE_FLOW_PRESETS["flow_p2_w2"]["paths"], ["P2"])
        self.assertEqual(SELECTIVE_FLOW_PRESETS["flow_p2_w2"]["workflows"], ["W2"])
        self.assertEqual(SELECTIVE_FLOW_PRESETS["flow_p3_w3"]["paths"], ["P1", "P2", "P3"])
        self.assertEqual(SELECTIVE_FLOW_PRESETS["flow_p3_w3"]["workflows"], ["W1", "W2", "W3"])

        paths = [p["id"] for p in V1_MCP_FLOW_ARCHITECTURE["data_paths"]]
        wfs = [w["id"] for w in V1_MCP_FLOW_ARCHITECTURE["workflow_points"]]
        layers = [l["id"] for l in V1_MCP_FLOW_ARCHITECTURE["six_layers"]]
        self.assertEqual(paths, ["P1", "P2", "P3"])
        self.assertEqual(wfs, ["W1", "W2", "W3"])
        self.assertEqual(layers, ["L1", "L2", "L3", "L4", "L5", "L6"])

        manifest = connect_my_resources(verify=False)
        self.assertEqual(manifest["version"], "3.0.0-minimal")
        self.assertIn("selective_flow_presets", manifest)
        self.assertIn("mcp_architecture_guide", manifest)

    def test_t3_2tier_mcp_guide_and_custom_spec(self):
        t1 = MCP_ARCHITECTURE_GUIDE["tier1_builder_core_mcp"]
        self.assertEqual(t1["server_name"], "aos-builder-core-mcp")
        self.assertIn("/mcp/builder", t1["endpoint_url"])
        self.assertEqual(len(t1["tools"]), 8)
        self.assertIn("aos-builder-core-mcp", t1["mcp_client_config_snippet"]["mcpServers"])
        self.assertIn("workflow_spec", t1["custom_build_spec_example"])

        t2 = MCP_ARCHITECTURE_GUIDE["tier2_runtime_domain_mcp"]
        self.assertEqual(len(t2["tools"]), 3)
        tool_names = [t["tool_name"] for t in t2["tools"]]
        self.assertEqual(
            tool_names,
            [
                "mcp_lookup_customer_profile",
                "mcp_calculate_penalty_rule",
                "mcp_query_graph_and_wiki",
            ],
        )
        self.assertIn("connect_my_resources", t2["customization_3steps_code"])

    def test_t4_okf_3layer_wiki_and_business_workflows(self):
        wiki_dir = os.path.join(ROOT, "data/llm_wiki")
        for md in ("summary.md", "entities.md", "concepts.md", "rules.md"):
            self.assertTrue(os.path.isfile(os.path.join(wiki_dir, md)), f"Missing wiki file: {md}")
        with open(os.path.join(wiki_dir, "business_workflows.json"), encoding="utf-8") as f:
            wfs = json.load(f).get("workflows", [])
        self.assertGreaterEqual(len(wfs), 3)
        points = {w.get("extraction_point") for w in wfs}
        self.assertEqual(points, {"W1", "W2", "W3"})

    def test_t5_domain_mcp_catalog(self):
        srv = DomainMcpServer()
        cat = srv.get_tool_catalog()
        self.assertEqual(len(cat), 3)
        self.assertEqual(
            [t["name"] for t in cat],
            [
                "mcp_lookup_customer_profile",
                "mcp_calculate_penalty_rule",
                "mcp_query_graph_and_wiki",
            ],
        )

    def test_t6_studio_server_http_endpoints(self):
        httpd = ThreadingStudioServer(("127.0.0.1", 0), StudioHandler)
        port = httpd.server_address[1]
        th = threading.Thread(target=httpd.serve_forever, daemon=True)
        th.start()
        try:
            base = f"http://127.0.0.1:{port}"
            with urllib.request.urlopen(f"{base}/") as r:
                html = r.read().decode("utf-8")
                self.assertEqual(r.status, 200)
                self.assertIn("0. Getting Started", html)
                self.assertIn("aos-builder-core-mcp", html)
                self.assertIn("v1-MCP Flow Grid", html)

            for ep in ("/health", "/api/resources", "/api/catalog", "/api/assets", "/api/graph", "/api/eval/summary", "/api/lineage/graph"):
                with urllib.request.urlopen(f"{base}{ep}") as r:
                    self.assertEqual(r.status, 200, f"Endpoint failed: {ep}")
                    data = json.loads(r.read().decode("utf-8"))
                    self.assertTrue(isinstance(data, (dict, list)))
        finally:
            httpd.shutdown()
            httpd.server_close()


if __name__ == "__main__":
    unittest.main()
