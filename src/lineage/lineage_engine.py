# Copyright (c) 2026 Sean Jung (seanjung@google.com). All Rights Reserved.
# Non-Commercial Use Only: Methodology & Docs under CC BY-NC-ND 4.0; Source Code under PolyForm Noncommercial License 1.0.0.
# Commercial use, paid consulting/SI/PoC delivery, or production deployment requires prior written permission from seanjung@google.com.

# -*- coding: utf-8 -*-
"""
Spec-driven enterprise data lineage (DAG) engine for Stage 5.

- Graph structure comes from the project's `config/lineage_spec.json` (see `projects/_template/`).
  The spec describes what the pipeline code actually reads and writes; edit it when the code changes.
- Volumes are measured on request, never typed into the spec:
  `bq_table` -> BigQuery `__TABLES__` row count, `gcs_prefix` -> GCS object count,
  `bq_graph` / `spanner_graph` -> node/edge table count from `INFORMATION_SCHEMA.PROPERTY_GRAPHS`.
  A failed lookup is shown as "lookup failed"; `live` is true only for measured values.
- Nodes without `x`/`y` are laid out in category columns, each column centred vertically.
"""
import json
import os
import time
from collections import deque
from typing import Any, Dict

from src.gcp_client import execute_bq_sql, execute_spanner_sql, list_gcs_objects

COL_X0, COL_DX, ROW_Y0 = 80, 380, 60
LIVE_TTL_SEC = 120
GRAPH_SQL = ("SELECT property_graph_name AS g, property_graph_metadata_json AS m "
             "FROM {src}INFORMATION_SCHEMA.PROPERTY_GRAPHS")


def _graph_counts(res: Dict[str, Any]) -> Dict[str, str]:
    out = {}
    for r in res.get("rows", []):
        m = json.loads(r.get("m") or r.get("property_graph_metadata_json") or "{}")
        out[r.get("g") or r.get("property_graph_name")] = \
            f"{len(m.get('nodeTables', []))} node / {len(m.get('edgeTables', []))} edge tables"
    return out


class LineageEngine:
    def __init__(self, spec_path: str, variables: Dict[str, str]):
        self.spec_path = spec_path
        self.vars = variables  # project_id, dataset_id, fq, bucket, model, spanner_* -> `{name}` placeholders
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

    def _measure(self, nodes) -> Dict[str, Any]:
        if self._live and time.time() - self._live_at < LIVE_TTL_SEC:
            return self._live
        live: Dict[str, Any] = {"status": "SKIPPED", "rows": {}, "gcs": {}, "bq_graph": {}, "spanner_graph": {}, "errors": []}
        if any(n.get("bq_table") for n in nodes):
            res = execute_bq_sql(f"SELECT table_id, row_count FROM `{self.vars['fq']}.__TABLES__`",
                                 project_id=self.vars["project_id"])
            live.update(status=res.get("status"), job_id=res.get("job_id"))
            if res.get("status") == "SUCCESS":
                live["rows"] = {r["table_id"]: int(r["row_count"]) for r in res.get("rows", [])}
            else:
                live["errors"].append(f"__TABLES__: {str(res.get('error', ''))[:200]}")
        for p in {n["gcs_prefix"] for n in nodes if n.get("gcs_prefix")}:
            try:
                live["gcs"][p] = len(list_gcs_objects(prefix=p, bucket=self.vars["bucket"]))
            except Exception as e:  # noqa: BLE001 - shown in the UI as a failed lookup
                live["errors"].append(f"gs://{self.vars['bucket']}/{p}: {str(e)[:200]}")
        if any(n.get("bq_graph") for n in nodes):
            res = execute_bq_sql(GRAPH_SQL.format(src=f"`{self.vars['fq']}`."), project_id=self.vars["project_id"])
            live["bq_graph"] = _graph_counts(res) if res.get("status") == "SUCCESS" else {}
            if res.get("status") != "SUCCESS":
                live["errors"].append(f"BigQuery PROPERTY_GRAPHS: {str(res.get('error', ''))[:200]}")
        if any(n.get("spanner_graph") for n in nodes) and self.vars.get("spanner_instance"):
            res = execute_spanner_sql(GRAPH_SQL.format(src=""), project_id=self.vars["project_id"],
                                      instance_id=self.vars["spanner_instance"], database_id=self.vars["spanner_database"])
            live["spanner_graph"] = _graph_counts(res) if res.get("status") == "SUCCESS" else {}
            if res.get("status") != "SUCCESS":
                live["errors"].append(f"Spanner PROPERTY_GRAPHS: {str(res.get('error', ''))[:200]}")
        self._live, self._live_at = live, time.time()
        return live

    def build_graph(self) -> Dict[str, Any]:
        spec = self._spec()
        cats = spec.get("categories", [])
        col = {c["id"]: i for i, c in enumerate(cats)}
        visible = [n for n in spec.get("nodes", []) if n.get("cat") in col]
        live = self._measure(visible)

        # column = optional spec "col" (e.g. node tables before edge tables), else the category order
        ci = {n["id"]: n.get("col", col[n["cat"]]) for n in visible}
        counts = {k: sum(1 for v in ci.values() if v == k) for k in set(ci.values())}
        step = {k: 72 if m > 8 else 92 for k, m in counts.items()}
        height = max([counts[k] * step[k] for k in counts] or [0])
        per_col: Dict[int, int] = {}
        nodes = []
        for n in visible:
            c = ci[n["id"]]
            idx = per_col[c] = per_col.get(c, -1) + 1
            node = {**n, "col": c, "resource": self._fill(n.get("resource")), "volume": self._fill(n.get("volume")),
                    "volume_en": self._fill(n.get("volume_en") or n.get("volume")), "live": False, "live_src": ""}
            node.setdefault("x", COL_X0 + c * COL_DX)
            node.setdefault("y", ROW_Y0 + (height - counts[c] * step[c]) // 2 + idx * step[c])
            measured, src = None, ""
            if n.get("bq_table"):
                rows = live["rows"].get(n["bq_table"])
                measured, src = (f"{rows:,} rows" if rows is not None else None), f"BigQuery __TABLES__ ({live.get('job_id') or '-'})"
            elif n.get("gcs_prefix"):
                k = live["gcs"].get(n["gcs_prefix"])
                measured, src = (f"{k} objects" if k is not None else None), "GCS JSON API objects.list"
            elif n.get("bq_graph"):
                measured, src = live["bq_graph"].get(self._fill(n["bq_graph"])), "BigQuery INFORMATION_SCHEMA.PROPERTY_GRAPHS"
            elif n.get("spanner_graph"):
                measured, src = live["spanner_graph"].get(self._fill(n["spanner_graph"])), "Spanner INFORMATION_SCHEMA.PROPERTY_GRAPHS"
            if measured:
                node.update(volume=measured, volume_en=measured, live=True, live_src=src)
            elif src:
                node.update(volume="조회 실패", volume_en="lookup failed", live_src=src)
            nodes.append(node)

        ids, seen, uniq = {n["id"] for n in nodes}, set(), []
        for e in spec.get("edges", []):
            key = (e["source"], e["target"])
            if key not in seen and e["source"] in ids and e["target"] in ids:
                seen.add(key)
                uniq.append(dict(e))

        measured_nodes = [n for n in nodes if n["live_src"]]
        return {
            "metadata": {"title": spec.get("title", ""), "fq": self.vars["fq"], "bq_status": live["status"],
                         "bq_job_id": live.get("job_id"), "bq_error": "; ".join(live["errors"]) or None,
                         "bq_nodes": len(measured_nodes), "live_nodes": sum(1 for n in measured_nodes if n["live"])},
            "stats": {"total_nodes": len(nodes), "total_edges": len(uniq), "total_categories": len(cats),
                      "category_counts": {c: sum(1 for n in visible if n["cat"] == c) for c in col}},
            "categories": cats, "presets": spec.get("presets", []), "nodes": nodes, "edges": uniq,
        }

    def trace(self, node_id: str) -> Dict[str, Any]:
        """BFS upstream and downstream from `node_id`."""
        g = self.build_graph()
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

    def explain(self, node_id: str, lang: str = "ko") -> Dict[str, Any]:
        """Rule-based summary of a node's position in the lineage (no LLM call)."""
        t = self.trace(node_id)
        if "error" in t:
            return {**t, "explanation": "Node not found." if lang == "en" else "노드를 찾을 수 없습니다."}
        n, up, down = t["selected_node"], t["upstream"]["count"], t["downstream"]["count"]
        vol = n.get("volume_en" if lang == "en" else "volume") or "-"
        src = n["live_src"] if n["live"] else ("lineage spec" if lang == "en" else "리니지 스펙 기재값")
        if lang == "en":
            text = (f"[{n.get('title_en') or n['title']}] belongs to the {n['cat']} tier (resource: {n['resource']}). "
                    f"It depends on {up} upstream node(s) and affects {down} downstream node(s). "
                    f"Volume: {vol} (source: {src}).")
        else:
            text = (f"[{n['title']}] 노드는 {n['cat']} 계층 자산입니다 (리소스: {n['resource']}). "
                    f"상류 {up}개 노드에 의존하고 하류 {down}개 노드에 영향을 줍니다. "
                    f"볼륨: {vol} (출처: {src}).")
        return {"node_id": node_id, "explanation": text, "upstream_count": up, "downstream_count": down, "lang": lang}
