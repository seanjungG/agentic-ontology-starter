# Copyright (c) 2026 Sean Jung (seanjung@google.com). All Rights Reserved.
# Non-Commercial Use Only: Methodology & Docs under CC BY-NC-ND 4.0; Source Code under PolyForm Noncommercial License 1.0.0.
# Commercial use, paid consulting/SI/PoC delivery, or production deployment requires prior written permission from seanjung@google.com.

# -*- coding: utf-8 -*-
"""Data allocation map for the Semantic Graph (GOAL-257).

Answers "which source (document page / table / column) ends up as which node row, property and edge" for a finished S4
design — the starter twin of the Notebook Lab n3 "wiki → graph integration units" panel, plus the table path:

    tables   source table → node label · key column · source column → property (type) · rows · dropped columns ·
             table-backed wiki pages absorbed as the table node's business notes
    wiki     wiki node label · layers taken · key · stored properties · rows (pages)
    edges    label · kind (fk / wiki_relation / wiki_bridge / provenance / lexical_hierarchy) · from → to ·
             connection basis (FK column, relation types, applies_to conditions) · count (+ how it was counted)
    pages    per wiki page: ① cited source sections → ② page → ③ node row / table-node note / not in graph →
             ④ stored properties → ⑤ edges leaving it

Deterministic and engine-neutral (Spanner Graph and BigQuery Graph share the same design contract): it only reads the
normalized design (`plan.design`, Core MCP `aos_core_design_graph`), the wiki pages, the parsed source tables and the
build counters already in the plan. No Core MCP / network call — so existing workspaces get the map on the fly.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Set, Tuple

VERSION = 1
WIKI_LAYERS = ("summary", "entity", "concept")


# ------------------------------------------------------------------------------------------------ OKF helpers (mirror)
def policy_text(page: Dict[str, Any]) -> str:
    return "; ".join(f"{c.get('name', '')}={c.get('value', '')}{c.get('unit', '') or ''}" for c in page.get("policy") or [])


def sources_text(page: Dict[str, Any]) -> str:
    return "; ".join(f"{s.get('doc', '')} {s.get('section', '')}".strip() for s in page.get("sources") or [])


def table_backed(page: Dict[str, Any], tables: Any) -> Optional[str]:
    """An entity page about a table's own object (applies_to that table with no where/keys)."""
    if page.get("layer") != "entity":
        return None
    for a in page.get("applies_to") or []:
        if a.get("table") in tables and not a.get("where") and not a.get("keys"):
            return str(a["table"])
    return None


def node_pages(node: Dict[str, Any], pages: List[Dict[str, Any]], tables: Any) -> List[Dict[str, Any]]:
    src = node.get("source") or {}
    out = [p for p in pages if p.get("layer") in (src.get("layers") or [])]
    if src.get("exclude_table_backed"):
        out = [p for p in out if not table_backed(p, tables)]
    return out


# ------------------------------------------------------------------------------------------------ row matching
def _num(v: Any) -> Optional[float]:
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    try:
        return float(str(v).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def _bool(v: Any) -> Optional[bool]:
    if isinstance(v, bool):
        return v
    s = str(v).strip().lower()
    if s in ("true", "t", "1", "yes", "y"):
        return True
    if s in ("false", "f", "0", "no", "n"):
        return False
    return None


def _eq(a: Any, b: Any) -> bool:
    if isinstance(a, bool) or isinstance(b, bool):
        x, y = _bool(a), _bool(b)
        return x is not None and x == y
    x, y = _num(a), _num(b)
    if x is not None and y is not None:
        return x == y
    return str(a).strip() == str(b).strip()


def match_where(row: Dict[str, Any], where: Optional[Dict[str, Any]]) -> bool:
    """Python twin of the applies_to predicate (=, !=, <, <=, >, >=, in)."""
    if not where:
        return True
    col, op, val = where.get("column"), str(where.get("op") or "=").lower(), where.get("value")
    if col not in row:
        return False
    v = row.get(col)
    if v is None or v == "":
        return False
    if op == "in":
        return any(_eq(v, x) for x in (val if isinstance(val, list) else [val]))
    if op == "=":
        return _eq(v, val)
    if op == "!=":
        return not _eq(v, val)
    x, y = _num(v), _num(val)
    if x is None or y is None:
        x, y = str(v), str(val)  # type: ignore[assignment]
    return {"<": x < y, "<=": x <= y, ">": x > y, ">=": x >= y}.get(op, False)  # type: ignore[operator]


def _key(v: Any) -> Optional[str]:
    if v is None or v == "":
        return None
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v).strip()


# ------------------------------------------------------------------------------------------------ allocation
def _tables_index(tables: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for tb in tables or []:
        if not isinstance(tb, dict) or not tb.get("name"):
            continue
        rows = tb.get("rows") or []
        rc = tb.get("row_count")
        rc = int(rc) if isinstance(rc, (int, float)) else None
        out[tb["name"]] = {"columns": [{"name": c.get("name"), "type": c.get("type", ""), "description": c.get("description", "")}
                                       for c in tb.get("columns") or [] if isinstance(c, dict) and c.get("name")],
                           "rows": rows, "row_count": rc, "complete": rc is not None and len(rows) >= rc,
                           "pk": tb.get("pk", ""), "fq": tb.get("fq", ""), "origin": tb.get("origin", "")}
    return out


def _cond_text(ap: Dict[str, Any]) -> str:
    w = ap.get("where")
    parts = []
    if w:
        val = w.get("value")
        sval = "(" + ", ".join(str(x) for x in val) + ")" if isinstance(val, list) else str(val)
        parts.append(f"{w.get('column')} {w.get('op') or '='} {sval}")
    if ap.get("keys"):
        parts.append("key IN (" + ", ".join(str(k) for k in ap["keys"]) + ")")
    return " AND ".join(parts) or "*"


def compute(plan: Dict[str, Any], pages: List[Dict[str, Any]], tables: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Allocation map for a stored S4 plan. ``tables`` = parsed/tables.json (rows may be a sample: see ``complete``)."""
    nd = plan.get("design") or {}
    nodes: List[Dict[str, Any]] = [n for n in nd.get("nodes") or [] if isinstance(n, dict) and n.get("label")]
    edges: List[Dict[str, Any]] = [e for e in nd.get("edges") or [] if isinstance(e, dict) and e.get("label")]
    pages = [p for p in pages or [] if isinstance(p, dict) and p.get("id")]
    tix = _tables_index(tables)
    by_label = {n["label"]: n for n in nodes}
    kind_of = {n["label"]: (n.get("source") or {}).get("kind", "") for n in nodes}
    table_nodes = {(n.get("source") or {}).get("table"): n["label"] for n in nodes if kind_of[n["label"]] == "table"}
    wiki_nodes = [n for n in nodes if kind_of[n["label"]] == "wiki"]
    node_counts = plan.get("node_counts") or {}
    stats = plan.get("stats") or {}
    loads = {str(x.get("id")): x for x in plan.get("loads") or [] if isinstance(x, dict)}

    # page → owning wiki node (first node whose layers take it)
    npages: Dict[str, List[Dict[str, Any]]] = {}
    owner: Dict[str, str] = {}
    for n in wiki_nodes:
        sel = node_pages(n, pages, table_nodes)
        npages[n["label"]] = sel
        for p in sel:
            owner.setdefault(p["id"], n["label"])
    excludes_tb = any((n.get("source") or {}).get("exclude_table_backed") for n in wiki_nodes)

    # key sets of table nodes (for FK / bridge counting)
    def key_set(label: str) -> Tuple[Set[str], bool]:
        n = by_label[label]
        tb = tix.get((n.get("source") or {}).get("table"))
        if not tb:
            return set(), False
        return {k for k in (_key(r.get(n.get("key"))) for r in tb["rows"]) if k is not None}, tb["complete"]

    def bridge_matches(p: Dict[str, Any], b: Dict[str, Any]) -> Tuple[int, bool, bool]:
        """(rows matched, complete?, any condition?) for page p → table node b."""
        tname = (b.get("source") or {}).get("table")
        tb = tix.get(tname)
        conds = [ap for ap in p.get("applies_to") or [] if ap.get("table") == tname]
        if not conds:
            return 0, True, False
        if not tb:
            return 0, False, True
        hit: Set[str] = set()
        for ap in conds:
            want = {str(k) for k in ap.get("keys") or []}
            for r in tb["rows"]:
                k = _key(r.get(b.get("key")))
                if k is None or (want and k not in want):
                    continue
                if match_where(r, ap.get("where")):
                    hit.add(k)
        return len(hit), tb["complete"], True

    # ---------------------------------------------------------------- tables
    tb_out: List[Dict[str, Any]] = []
    tb_backed = stats.get("table_backed") or {}
    for n in nodes:
        if kind_of[n["label"]] != "table":
            continue
        tname = (n.get("source") or {}).get("table", "")
        meta = tix.get(tname) or {}
        cols = {c["name"]: c for c in meta.get("columns") or []}
        types = n.get("types") or {}
        props = n.get("properties") or []
        notes = tb_backed.get(n["label"])
        if notes is None:
            notes = [p["id"] for p in pages if table_backed(p, table_nodes) == tname]
        pmap = {p["id"]: p for p in pages}
        rows, basis = None, ""
        if node_counts.get(n["label"]) is not None:
            rows, basis = node_counts[n["label"]], "graph"
        elif meta.get("row_count") is not None:
            rows, basis = meta["row_count"], "source"
        tb_out.append({
            "label": n["label"], "source_table": tname, "source_fq": meta.get("fq", ""), "origin": meta.get("origin", ""),
            "node_table": n.get("table", ""), "key": n.get("key", ""), "display": n.get("display", ""),
            "description": n.get("description", ""),
            "rows": rows, "rows_basis": basis, "source_rows": meta.get("row_count"),
            "columns": [{"column": p, "property": p, "type": types.get(p, (cols.get(p) or {}).get("type", "")),
                         "source_type": (cols.get(p) or {}).get("type", ""), "key": p == n.get("key"),
                         "description": (cols.get(p) or {}).get("description", "")} for p in props],
            "dropped": [c for c in cols if c not in props],
            "business_notes": [{"id": pid, "title": (pmap.get(pid) or {}).get("title", "")} for pid in notes],
        })

    # ---------------------------------------------------------------- edges
    ed_out: List[Dict[str, Any]] = []
    for e in edges:
        a, b = by_label.get(e.get("from")), by_label.get(e.get("to"))
        if not a or not b:
            continue
        src = e.get("source") or {}
        kind = str(src.get("kind", ""))
        row: Dict[str, Any] = {"label": e["label"], "kind": kind, "from": a["label"], "to": b["label"],
                               "from_kind": kind_of[a["label"]], "to_kind": kind_of[b["label"]], "table": e.get("table", ""),
                               "description": e.get("description", ""), "count": None, "count_basis": "", "basis": {}}
        if kind == "fk":
            col = src.get("column", "")
            row["basis"] = {"column": col, "from_table": (a.get("source") or {}).get("table", ""), "to_key": b.get("key", "")}
            ta = tix.get((a.get("source") or {}).get("table"))
            if ta:
                dst, dst_full = key_set(b["label"])
                pairs = {(_key(r.get(a.get("key"))), _key(r.get(col))) for r in ta["rows"]}
                pairs = {pr for pr in pairs if pr[0] is not None and pr[1] is not None and pr[1] in dst}
                row["count"], row["count_basis"] = len(pairs), ("computed" if ta["complete"] and dst_full else "sample")
        elif kind == "wiki_relation":
            types = [str(x) for x in src.get("types") or []]
            row["basis"] = {"types": types}
            ld = loads.get(f"edge:{e.get('table')}")
            if ld and ld.get("row_count") is not None:
                row["count"], row["count_basis"] = ld["row_count"], "loaded"
            elif e["label"] in (stats.get("wiki_relations") or {}):
                row["count"], row["count_basis"] = stats["wiki_relations"][e["label"]], "loaded"
            else:
                bkeys = {p["id"] for p in npages.get(b["label"], [])}
                uniq = {(p["id"], r.get("target")) for p in npages.get(a["label"], []) for r in p.get("relations") or []
                        if (not types or r.get("type") in types) and r.get("target") in bkeys}
                row["count"], row["count_basis"] = len(uniq), "computed"
        elif kind == "wiki_bridge":
            tname = (b.get("source") or {}).get("table", "")
            conds, total, full = [], 0, True
            for p in npages.get(a["label"], []):
                for ap in p.get("applies_to") or []:
                    if ap.get("table") != tname:
                        continue
                    conds.append({"page": p["id"], "where": ap.get("where"), "keys": ap.get("keys"), "text": _cond_text(ap)})
            hit_all: Set[Tuple[str, str]] = set()
            tb = tix.get(tname)
            if tb:
                for c in conds:
                    want = {str(k) for k in c.get("keys") or []}
                    for r in tb["rows"]:
                        k = _key(r.get(b.get("key")))
                        if k is None or (want and k not in want):
                            continue
                        if match_where(r, c.get("where")):
                            hit_all.add((c["page"], k))
                total, full = len(hit_all), tb["complete"]
                row["count"], row["count_basis"] = total, ("computed" if full else "sample")
            row["basis"] = {"table": tname, "key": b.get("key", ""), "conditions": conds}
        else:  # provenance / lexical_hierarchy / future kinds: show as declared
            row["basis"] = {k: v for k, v in src.items() if k != "kind"}
        ed_out.append(row)

    # ---------------------------------------------------------------- pages (lab n3 integration units)
    pg_out: List[Dict[str, Any]] = []
    totals = {"pages": len(pages), "sections": 0, "node_rows": 0, "table_notes": 0, "excluded": 0, "edges": 0,
              "body_chars": 0, "constants": 0}
    for p in pages:
        label = owner.get(p["id"])
        node = by_label.get(label) if label else None
        tb = table_backed(p, table_nodes)
        fate = "node" if node else ("table_note" if tb and excludes_tb else "excluded")
        body = str(p.get("body_md") or "")
        vals = {"wiki_id": p["id"], "layer": p.get("layer", ""), "title": p.get("title", ""), "summary": p.get("summary", ""),
                "body_md": body, "policy_text": policy_text(p), "sources_text": sources_text(p)}
        props = [{"name": k, "chars": len(str(vals.get(k) or ""))} for k in (node.get("properties") or [] if node else []) if k in vals]
        pe: List[Dict[str, Any]] = []
        if node:
            for e in edges:
                if e.get("from") != label:
                    continue
                b = by_label.get(e.get("to"))
                if not b:
                    continue
                kind = (e.get("source") or {}).get("kind", "")
                cnt, sample = 0, False
                if kind == "wiki_relation" and kind_of[b["label"]] == "wiki":
                    types = set((e.get("source") or {}).get("types") or [])
                    targets = {q["id"] for q in npages.get(b["label"], [])}
                    cnt = len({r.get("target") for r in p.get("relations") or [] if (not types or r.get("type") in types) and r.get("target") in targets})
                elif kind == "wiki_bridge" and kind_of[b["label"]] == "table":
                    cnt, full, _ = bridge_matches(p, b)
                    sample = not full
                if cnt:
                    pe.append({"label": e["label"], "kind": kind, "to": b["label"], "count": cnt, "sample": sample})
        lines = len([ln for ln in body.splitlines() if ln.strip()])
        srcs = [f"{s.get('doc', '')} §{s.get('section', '')}".strip() for s in p.get("sources") or []]
        pg_out.append({"id": p["id"], "layer": p.get("layer", ""), "title": p.get("title", ""), "lines": lines, "chars": len(body),
                       "sources": srcs, "constants": len(p.get("policy") or []), "fate": fate,
                       "node": label or (table_nodes.get(tb, "") if tb else ""), "key": p["id"] if node else "",
                       "table": tb or "", "properties": props, "edges": pe})
        totals["sections"] += len(srcs)
        totals["node_rows"] += fate == "node"
        totals["table_notes"] += fate == "table_note"
        totals["excluded"] += fate == "excluded"
        totals["edges"] += sum(x["count"] for x in pe)
        if fate == "node":
            totals["body_chars"] += len(body)
            totals["constants"] += len(p.get("policy") or [])

    wk_out = []
    for n in wiki_nodes:
        ld = loads.get(f"node:{n['label']}")
        wk_out.append({"label": n["label"], "layers": (n.get("source") or {}).get("layers", []),
                       "exclude_table_backed": bool((n.get("source") or {}).get("exclude_table_backed")),
                       "key": n.get("key", "wiki_id"), "node_table": n.get("table", ""), "properties": n.get("properties") or [],
                       "rows": sum(1 for r in pg_out if r["node"] == n["label"] and r["fate"] == "node"),
                       "loaded_rows": ld.get("row_count") if ld else None,
                       "pages": [r["id"] for r in pg_out if r["node"] == n["label"] and r["fate"] == "node"]})
    other = [{"label": n["label"], "kind": kind_of[n["label"]], "source": n.get("source") or {}, "properties": n.get("properties") or []}
             for n in nodes if kind_of[n["label"]] not in ("table", "wiki")]

    by_kind: Dict[str, int] = {}
    for e in ed_out:
        by_kind[e["kind"]] = by_kind.get(e["kind"], 0) + 1
    totals.update({
        "table_nodes": len(tb_out), "wiki_nodes": len(wk_out), "other_nodes": len(other),
        "table_rows": sum(t["rows"] or 0 for t in tb_out),
        "table_props": sum(len(t["columns"]) for t in tb_out),
        "dropped_columns": sum(len(t["dropped"]) for t in tb_out),
        "edge_types": len(ed_out), "edge_kinds": by_kind,
        "edge_rows": sum(e["count"] or 0 for e in ed_out),
        "edge_rows_partial": any(e["count"] is None or e["count_basis"] == "sample" for e in ed_out),
    })
    return {"v": VERSION, "engine": plan.get("engine") or "bigquery", "graph_name": nd.get("graph_name", ""),
            "totals": totals, "tables": tb_out, "wiki_nodes": wk_out, "other_nodes": other, "edges": ed_out, "pages": pg_out}


def ensure(plan: Optional[Dict[str, Any]], pages_loader, tables_loader) -> Optional[Dict[str, Any]]:
    """Attach ``plan['allocation']`` when missing/outdated (pre-GOAL-257 workspaces). Loaders are called lazily."""
    if not isinstance(plan, dict) or not plan.get("design"):
        return plan
    al = plan.get("allocation")
    if isinstance(al, dict) and al.get("v") == VERSION:
        return plan
    try:
        plan["allocation"] = compute(plan, pages_loader() or [], tables_loader() or [])
        plan["allocation"]["computed"] = "on_read"
    except Exception as e:  # never break the graph tab: show the reason instead of the panel
        plan["allocation"] = {"v": VERSION, "error": f"{type(e).__name__}: {e}"[:300]}
    return plan
