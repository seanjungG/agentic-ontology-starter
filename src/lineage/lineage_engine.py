# Copyright (c) 2026 Sean Jung (seanjung@google.com). All Rights Reserved.
# Non-Commercial Use Only: Methodology & Docs under CC BY-NC-ND 4.0; Source Code under PolyForm Noncommercial License 1.0.0.
# Commercial use, paid consulting/SI/PoC delivery, or production deployment requires prior written permission from seanjung@google.com.

# -*- coding: utf-8 -*-
"""
Spec-driven enterprise data lineage (DAG) engine for Stage 5.

- Graph structure comes from the project's `config/lineage_spec.json` (see `projects/_template/`).
- Nodes with `bq_table` get their row count from BigQuery `__TABLES__`; `live` is true only when fetched.
- Categories flagged `pii` are hidden by default; their nodes are bypassed (upstream -> downstream).
- Nodes without `x`/`y` are laid out in category columns (same layout as the main studio lineage view).
"""
import json
import os
import time
from collections import deque
from typing import Any, Dict, List

from src.gcp_client import execute_bq_sql

COL_X0, COL_DX, ROW_Y0 = 80, 380, 60
LIVE_TTL_SEC = 120


class LineageEngine:
    def __init__(self, spec_path: str, variables: Dict[str, str]):
        self.spec_path = spec_path
        self.vars = variables  # project_id, dataset_id, fq, bucket, model -> `{name}` placeholders in the spec
        self._live: Dict[str, Any] = {}
        self._live_at = 0.0

    def _spec(self) -> Dict[str, Any]:
        if not os.path.exists(self.spec_path):
            return {}
        with open(self.spec_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _fill(self, s: Any) -> str:
        s = str(s or "")
        for k, v in self.vars.items():
            s = s.replace("{" + k + "}", str(v))
        return s

    def _live_rows(self) -> Dict[str, Any]:
        if self._live and time.time() - self._live_at < LIVE_TTL_SEC:
            return self._live
        res = execute_bq_sql(f"SELECT table_id, row_count FROM `{self.vars['fq']}.__TABLES__`",
                             project_id=self.vars["project_id"])
        ok = res.get("status") == "SUCCESS"
        self._live = {"status": res.get("status"), "job_id": res.get("job_id"),
                      "error": None if ok else str(res.get("error", ""))[:300],
                      "rows": {r["table_id"]: int(r["row_count"]) for r in res.get("rows", [])} if ok else {}}
        self._live_at = time.time()
        return self._live

    def build_graph(self, include_pii: bool = False) -> Dict[str, Any]:
        spec = self._spec()
        cats = [c for c in spec.get("categories", []) if include_pii or not c.get("pii")]
        col = {c["id"]: i for i, c in enumerate(cats)}
        raw_nodes = spec.get("nodes", [])
        visible = [n for n in raw_nodes if n.get("cat") in col]
        hidden = {n["id"] for n in raw_nodes} - {n["id"] for n in visible}
        live = self._live_rows() if any(n.get("bq_table") for n in visible) else {"status": "SKIPPED", "rows": {}}

        per_col: Dict[str, int] = {}
        counts = {c: sum(1 for n in visible if n["cat"] == c) for c in col}
        nodes = []
        for n in visible:
            idx = per_col[n["cat"]] = per_col.get(n["cat"], -1) + 1
            node = {**n, "resource": self._fill(n.get("resource")), "volume": self._fill(n.get("volume")),
                    "volume_en": self._fill(n.get("volume_en") or n.get("volume")), "live": False}
            node.setdefault("x", COL_X0 + col[n["cat"]] * COL_DX)
            node.setdefault("y", ROW_Y0 + idx * (72 if counts[n["cat"]] > 8 else 92))
            rows = live["rows"].get(n.get("bq_table"))
            if rows is not None:
                node.update(volume=f"{rows:,} rows", volume_en=f"{rows:,} rows", live=True)
            nodes.append(node)

        edges = [dict(e) for e in spec.get("edges", [])]
        for h in hidden:  # bypass hidden (PII) nodes so the flow stays connected
            ins = [e for e in edges if e["target"] == h]
            outs = [e for e in edges if e["source"] == h]
            edges = [e for e in edges if h not in (e["source"], e["target"])]
            edges += [{"source": i["source"], "target": o["target"], "label": o.get("label", "")} for i in ins for o in outs]
        ids, seen, uniq = {n["id"] for n in nodes}, set(), []
        for e in edges:
            key = (e["source"], e["target"])
            if key not in seen and e["source"] in ids and e["target"] in ids:
                seen.add(key)
                uniq.append(e)

        bq_nodes = [n for n in nodes if n.get("bq_table")]
        return {
            "metadata": {"title": spec.get("title", ""), "fq": self.vars["fq"], "bq_status": live["status"],
                         "bq_job_id": live.get("job_id"), "bq_error": live.get("error"),
                         "bq_nodes": len(bq_nodes), "live_nodes": sum(1 for n in bq_nodes if n["live"])},
            "stats": {"total_nodes": len(nodes), "total_edges": len(uniq), "total_categories": len(cats),
                      "category_counts": counts, "pii_layer_visible": include_pii},
            "categories": cats, "presets": spec.get("presets", []), "nodes": nodes, "edges": uniq,
        }

    def trace(self, node_id: str, include_pii: bool = False) -> Dict[str, Any]:
        """BFS upstream and downstream from `node_id`."""
        g = self.build_graph(include_pii)
        nodes = {n["id"]: n for n in g["nodes"]}
        if node_id not in nodes:
            return {"error": f"Node '{node_id}' not found in lineage graph."}

        def walk(src_key: str, dst_key: str):
            seen, found, q = {node_id}, [], deque([node_id])
            while q:
                cur = q.popleft()
                for e in g["edges"]:
                    if e[dst_key] == cur:
                        found.append(e)
                        if e[src_key] not in seen:
                            seen.add(e[src_key])
                            q.append(e[src_key])
            return seen - {node_id}, found

        up_ids, up_edges = walk("source", "target")
        down_ids, down_edges = walk("target", "source")
        return {
            "selected_node": nodes[node_id],
            "highlighted_nodes": sorted(up_ids | down_ids | {node_id}),
            "highlighted_edges": up_edges + down_edges,
            "upstream": {"count": len(up_ids), "nodes": sorted(up_ids), "edges": up_edges},
            "downstream": {"count": len(down_ids), "nodes": sorted(down_ids), "edges": down_edges},
        }

    def explain(self, node_id: str, include_pii: bool = False, lang: str = "ko") -> Dict[str, Any]:
        """Rule-based summary of a node's position in the lineage (no LLM call)."""
        t = self.trace(node_id, include_pii)
        if "error" in t:
            return {**t, "explanation": "Node not found." if lang == "en" else "노드를 찾을 수 없습니다."}
        n, up, down = t["selected_node"], t["upstream"]["count"], t["downstream"]["count"]
        vol = n.get("volume_en" if lang == "en" else "volume") or "-"
        src = ("BigQuery __TABLES__ (live)" if n["live"] else "lineage spec") if lang == "en" else \
              ("BigQuery __TABLES__ 실측" if n["live"] else "리니지 스펙 기재값")
        if lang == "en":
            text = (f"[{n.get('title_en') or n['title']}] belongs to the {n['cat']} tier (resource: {n['resource']}). "
                    f"It depends on {up} upstream node(s) and affects {down} downstream node(s). "
                    f"Volume: {vol} (source: {src}).")
        else:
            text = (f"[{n['title']}] 노드는 {n['cat']} 계층 자산입니다 (리소스: {n['resource']}). "
                    f"상류 {up}개 노드에 의존하고 하류 {down}개 노드에 영향을 줍니다. "
                    f"볼륨: {vol} (출처: {src}).")
        return {"node_id": node_id, "explanation": text, "upstream_count": up, "downstream_count": down, "lang": lang}
