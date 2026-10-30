# Copyright (c) 2026 Sean Jung (seanjung@google.com). All Rights Reserved.
# Non-Commercial Use Only: Methodology & Docs under CC BY-NC-ND 4.0; Source Code under PolyForm Noncommercial License 1.0.0.
# Commercial use, paid consulting/SI/PoC delivery, or production deployment requires prior written permission from seanjung@google.com.

# -*- coding: utf-8 -*-
"""Spanner Graph backend for S4 (GOAL-256) — the default Semantic Graph engine.

Engines (workspace ``env.graph_engine``):
    spanner   (default) Semantic Graph = Spanner Graph. The Core MCP design (engine-neutral nodes/edges) is compiled to
              Spanner DDL here; node/edge rows are first materialised in BigQuery (staging · SQL analytics layer, no
              Enterprise reservation needed) and copied into Spanner; CREATE OR REPLACE PROPERTY GRAPH runs in Spanner.
    bigquery  BigQuery Property Graph — kept as an option; meant for audit / action-lineage (Context Graph) capture
              that is added later. Workspaces created before GOAL-256 have no ``graph_engine`` → treated as bigquery.

Workspaces share one Spanner database (``AOS_SPANNER_DATABASE``, default ``starter_graph_db``) — every workspace gets
its own table prefix ``ws<yyyymmdd>_<hex>_`` and graph ``<graph_name>_<yyyymmdd>_<hex>``, so no extra DB slot is used.

The Core MCP agent/verification queries are written in the BigQuery dialect (``GRAPH_TABLE(`p.d.G` MATCH … COLUMNS (…))``).
``to_spanner()`` rewrites them for Spanner (graph/table names → Spanner names, ``COLUMNS (…)`` → ``RETURN …``) and
``route()`` decides where a query runs: everything mapped → Spanner, any remaining BigQuery-only table → BigQuery.
"""
from __future__ import annotations

import os
import re
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple

from src import identity
from src.aos.ws import McpLog, error_text, t

ENGINES = ("spanner", "bigquery")
DEFAULT_ENGINE = (os.environ.get("AOS_GRAPH_ENGINE") or "spanner").strip().lower()
if DEFAULT_ENGINE not in ENGINES:
    DEFAULT_ENGINE = "spanner"
DEFAULT_DATABASE = (os.environ.get("AOS_SPANNER_DATABASE") or "starter_graph_db").strip()
MAX_COPY_ROWS = int(os.environ.get("AOS_SPANNER_MAX_ROWS", "20000") or 20000)
_CELLS_PER_COMMIT = 15000  # Spanner allows 80k mutations (cells) per commit — stay well below

Emit = Callable[[Dict[str, Any]], None]

# std type (Core MCP design) → Spanner column type. NUMERIC → FLOAT64 (BigQuery REST already returns floats);
# DATETIME / TIME have no Spanner equivalent and stay strings.
SP_TYPE = {"STRING": "STRING(MAX)", "INT64": "INT64", "INTEGER": "INT64", "FLOAT64": "FLOAT64", "FLOAT": "FLOAT64",
           "NUMERIC": "FLOAT64", "BIGNUMERIC": "FLOAT64", "BOOL": "BOOL", "BOOLEAN": "BOOL", "DATE": "DATE",
           "TIMESTAMP": "TIMESTAMP", "DATETIME": "STRING(MAX)", "TIME": "STRING(MAX)", "JSON": "JSON", "BYTES": "BYTES(MAX)"}


def engine(env: Dict[str, Any]) -> str:
    """Graph engine of a workspace env. Missing key = workspace created before GOAL-256 = bigquery."""
    e = str((env or {}).get("graph_engine") or "bigquery").lower()
    return e if e in ENGINES else "bigquery"


def ws_suffix(ws_id: str) -> str:
    return str(ws_id or "").replace("ws-", "").replace("-", "_")


def table_prefix(ws_id: str) -> str:
    return f"ws{ws_suffix(ws_id)}_"


def graph_name(env: Dict[str, Any], ws_id: str) -> str:
    return f"{env.get('graph_name') or 'AOS_ONTOLOGY_GRAPH'}_{ws_suffix(ws_id)}"[:128]


def sp_table(ws_id: str, name: str) -> str:
    return (table_prefix(ws_id) + name)[:128]


def instance_path(env: Dict[str, Any]) -> str:
    return f"projects/{env['project']}/instances/{env.get('spanner_instance') or ''}"


def db_path(env: Dict[str, Any]) -> str:
    return f"{instance_path(env)}/databases/{env.get('spanner_database') or DEFAULT_DATABASE}"


def console_url(env: Dict[str, Any]) -> str:
    return (f"https://console.cloud.google.com/spanner/instances/{env.get('spanner_instance')}/databases/"
            f"{env.get('spanner_database') or DEFAULT_DATABASE}/details/tables?project={env['project']}")


def _q(name: str) -> str:
    return f"`{name}`"


# ================================================================================================ DDL
def ddl(nd: Dict[str, Any], ws_id: str, gname: str) -> Dict[str, Any]:
    """CREATE TABLE per node/edge table + CREATE OR REPLACE PROPERTY GRAPH, from the engine-neutral design."""
    by_label = {n["label"]: n for n in nd.get("nodes") or []}
    tables: List[Dict[str, Any]] = []
    stmts: List[str] = []
    for n in nd.get("nodes") or []:
        cols = []
        types = {}
        for p in n["properties"]:
            ty = SP_TYPE.get(str(n["types"].get(p, "STRING")).upper(), "STRING(MAX)")
            types[p] = ty
            cols.append(f"  {_q(p)} {ty}" + (" NOT NULL" if p == n["key"] else ""))
        name = sp_table(ws_id, n["table"])
        stmts.append(f"CREATE TABLE {_q(name)} (\n" + ",\n".join(cols) + f"\n) PRIMARY KEY ({_q(n['key'])})")
        tables.append({"kind": "node", "label": n["label"], "bq": n["table"], "spanner": name, "columns": list(n["properties"]),
                       "types": types, "key": [n["key"]]})
    for e in nd.get("edges") or []:
        a, b = by_label[e["from"]], by_label[e["to"]]
        st = SP_TYPE.get(str(a["types"][a["key"]]).upper(), "STRING(MAX)")
        dt = SP_TYPE.get(str(b["types"][b["key"]]).upper(), "STRING(MAX)")
        cols = [("src_key", st, True), ("dst_key", dt, True)]
        if e["source"]["kind"] == "wiki_relation":
            cols.append(("relation", "STRING(MAX)", False))
        name = sp_table(ws_id, e["table"])
        stmts.append(f"CREATE TABLE {_q(name)} (\n" + ",\n".join(f"  {c} {ty}" + (" NOT NULL" if nn else "") for c, ty, nn in cols)
                     + "\n) PRIMARY KEY (src_key, dst_key)")
        tables.append({"kind": "edge", "label": e["label"], "bq": e["table"], "spanner": name, "columns": [c for c, _, _ in cols],
                       "types": {c: ty for c, ty, _ in cols}, "key": ["src_key", "dst_key"]})
    node_parts = [f"    {_q(sp_table(ws_id, n['table']))}\n      KEY ({_q(n['key'])})\n      LABEL {n['label']}\n"
                  f"      PROPERTIES ({', '.join(_q(p) for p in n['properties'])})" for n in nd.get("nodes") or []]
    graph = f"CREATE OR REPLACE PROPERTY GRAPH {gname}\n  NODE TABLES (\n" + ",\n".join(node_parts) + "\n  )"
    if nd.get("edges"):
        parts = []
        for e in nd["edges"]:
            a, b = by_label[e["from"]], by_label[e["to"]]
            parts.append(f"    {_q(sp_table(ws_id, e['table']))}\n      KEY (src_key, dst_key)\n"
                         f"      SOURCE KEY (src_key) REFERENCES {_q(sp_table(ws_id, a['table']))} ({_q(a['key'])})\n"
                         f"      DESTINATION KEY (dst_key) REFERENCES {_q(sp_table(ws_id, b['table']))} ({_q(b['key'])})\n"
                         f"      LABEL {e['label']}")
        graph += "\n  EDGE TABLES (\n" + ",\n".join(parts) + "\n  )"
    return {"tables": tables, "table_statements": stmts, "graph_statement": graph}


def drop_statements(existing_ddl: List[str], ws_id: str, gname: str) -> List[str]:
    """DROP the workspace's previous graph + tables (rebuild). Only names with this workspace's prefix are touched."""
    pf = table_prefix(ws_id).lower()
    out: List[str] = []
    for s in existing_ddl or []:
        m = re.match(r"\s*CREATE\s+(?:OR\s+REPLACE\s+)?PROPERTY\s+GRAPH\s+`?([A-Za-z0-9_]+)`?", s, re.I)
        if m and (m.group(1) == gname or m.group(1).lower().endswith("_" + ws_suffix(ws_id).lower())):
            out.insert(0, f"DROP PROPERTY GRAPH {m.group(1)}")
    for s in existing_ddl or []:
        m = re.match(r"\s*CREATE\s+TABLE\s+`?([A-Za-z0-9_]+)`?", s, re.I)
        if m and m.group(1).lower().startswith(pf):
            out.append(f"DROP TABLE {_q(m.group(1))}")
    return out


# GOAL-259: TTL for the shared database. BigQuery demo datasets expire after 7 days (pipeline.prepare); the Spanner
# copies of those workspaces would otherwise stay forever in `starter_graph_db`. Names carry the workspace creation
# date (`ws<yyyymmdd>_<hex>_…` tables · `<graph>_<yyyymmdd>_<hex>` graphs), so expiry needs no extra metadata.
TTL_DAYS = int(os.environ.get("AOS_SPANNER_TTL_DAYS", "7") or 7)
_TABLE_WS = re.compile(r"^ws(\d{8})_([0-9a-f]{4,})_", re.I)
_GRAPH_WS = re.compile(r"_(\d{8})_([0-9a-f]{4,})$", re.I)


def _expired(day: str, now: datetime, days: int) -> bool:
    try:
        d = datetime.strptime(day, "%Y%m%d").replace(tzinfo=timezone.utc)
    except ValueError:
        return False
    return (now - d).days >= days


def expired_drop_statements(existing_ddl: List[str], days: int = TTL_DAYS, now: Optional[datetime] = None,
                            keep_ws: str = "") -> Tuple[List[str], List[str]]:
    """DROP statements for workspace graphs/tables older than `days` (graphs first). Returns (statements, ws suffixes).
    Objects without a workspace-date name are never touched; `keep_ws` (the workspace being built) is always kept."""
    if days <= 0:
        return [], []
    now = now or datetime.now(timezone.utc)
    keep = ws_suffix(keep_ws).lower() if keep_ws else ""
    graphs: List[str] = []
    tables: List[str] = []
    wss: Dict[str, None] = {}
    for s in existing_ddl or []:
        m = re.match(r"\s*CREATE\s+(?:OR\s+REPLACE\s+)?PROPERTY\s+GRAPH\s+`?([A-Za-z0-9_]+)`?", s, re.I)
        if m:
            g = _GRAPH_WS.search(m.group(1))
            if g and f"{g.group(1)}_{g.group(2)}".lower() != keep and _expired(g.group(1), now, days):
                graphs.append(f"DROP PROPERTY GRAPH {m.group(1)}")
                wss[f"{g.group(1)}_{g.group(2)}".lower()] = None
            continue
        m = re.match(r"\s*CREATE\s+TABLE\s+`?([A-Za-z0-9_]+)`?", s, re.I)
        if m:
            w = _TABLE_WS.match(m.group(1))
            if w and f"{w.group(1)}_{w.group(2)}".lower() != keep and _expired(w.group(1), now, days):
                tables.append(f"DROP TABLE {_q(m.group(1))}")
                wss[f"{w.group(1)}_{w.group(2)}".lower()] = None
    return graphs + tables, list(wss)


def purge_expired(log: McpLog, env: Dict[str, Any], days: int = TTL_DAYS, dry_run: bool = False) -> Dict[str, Any]:
    """Drop expired workspace graphs/tables from the workspace's Spanner database (CLI `purge-spanner`)."""
    db = db_path(env)
    cur = log.call("spanner_get_ddl", {"database": db}, timeout_s=40, label="get DDL")
    if cur.get("status") != "SUCCESS":
        raise RuntimeError(f"getDdl failed: {error_text(cur)[:300]}")
    stmts, wss = expired_drop_statements(cur.get("statements") or [], days)
    if stmts and not dry_run:
        _wait_op(log, log.call("spanner_update_ddl", {"database": db, "statements": stmts, "timeout_s": 300}, timeout_s=330,
                               label="DROP (expired)"), "DROP (expired)", 600)
    return {"database": db, "days": days, "dry_run": dry_run, "workspaces": wss, "statements": stmts}


# ================================================================================================ values
def sp_value(ty: str, v: Any) -> Any:
    """BigQuery REST value (after Core MCP casting) → Spanner REST JSON value."""
    if v is None:
        return None
    if ty == "INT64":
        try:
            return str(int(float(v)))
        except (TypeError, ValueError):
            return None
    if ty == "FLOAT64":
        try:
            return float(v)
        except (TypeError, ValueError):
            return None
    if ty == "BOOL":
        return v if isinstance(v, bool) else str(v).strip().lower() in ("true", "1", "yes", "y", "t")
    if ty == "TIMESTAMP":
        try:
            return datetime.fromtimestamp(float(v), tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        except (TypeError, ValueError):
            return str(v)
    if ty == "DATE":
        return str(v)[:10]
    if ty == "JSON":
        return v if isinstance(v, str) else __import__("json").dumps(v, ensure_ascii=False)
    return v if isinstance(v, str) else str(v)


# ================================================================================================ query translation
def name_map(nd: Dict[str, Any], env: Dict[str, Any], ws_id: str) -> Dict[str, str]:
    """BigQuery object name (graph · node/edge table) → Spanner name."""
    m = {str(env.get("graph_name") or nd.get("graph_name") or "").lower(): graph_name(env, ws_id), "__graph__": graph_name(env, ws_id)}
    if nd.get("graph_name"):
        m[str(nd["graph_name"]).lower()] = graph_name(env, ws_id)
    for x in list(nd.get("nodes") or []) + list(nd.get("edges") or []):
        m[str(x["table"]).lower()] = sp_table(ws_id, x["table"])
    return m


def _skip_string(q: str, i: int) -> int:
    quote = q[i]
    j = i + 1
    while j < len(q):
        if q[j] == "\\":
            j += 2
            continue
        if q[j] == quote:
            return j + 1
        j += 1
    return j


def _match_paren(q: str, i: int) -> int:
    """Index of the ')' matching the '(' at q[i] (string/backtick aware); -1 if none."""
    depth = 0
    j = i
    while j < len(q):
        c = q[j]
        if c in ("'", '"', "`"):
            j = _skip_string(q, j)
            continue
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return j
        j += 1
    return -1


def _columns_to_return(q: str) -> str:
    """Inside every GRAPH_TABLE( … ) turn the top-level `COLUMNS ( … )` into `RETURN …` (Spanner syntax)."""
    out, pos = [], 0
    for m in re.finditer(r"\bGRAPH_TABLE\s*\(", q, re.I):
        start = m.end() - 1
        if start < pos:
            continue
        end = _match_paren(q, start)
        if end < 0:
            break
        inner = q[start + 1:end]
        depth, j, hit = 0, 0, None
        while j < len(inner):
            c = inner[j]
            if c in ("'", '"', "`"):
                j = _skip_string(inner, j)
                continue
            if c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
            elif depth == 0 and inner[j:j + 7].upper() == "COLUMNS" and (j == 0 or not (inner[j - 1].isalnum() or inner[j - 1] == "_")):
                k = j + 7
                while k < len(inner) and inner[k].isspace():
                    k += 1
                if k < len(inner) and inner[k] == "(":
                    hit = (j, k)
                    break
            j += 1
        if hit:
            j, k = hit
            close = _match_paren(inner, k)
            if close > 0:
                inner = inner[:j] + "RETURN " + inner[k + 1:close].strip() + inner[close + 1:]
        out.append(q[pos:start + 1] + inner + ")")
        pos = end + 1
    out.append(q[pos:])
    return "".join(out)


def to_spanner(q: str, names: Dict[str, str], project: str, dataset: str) -> Tuple[str, List[str]]:
    """Rewrite a BigQuery-dialect query for Spanner. Returns (query, unmapped BigQuery-only object names)."""
    unmapped: List[str] = []
    graph = names.get("__graph__", "")
    pat = re.compile(r"`?(?:" + re.escape(project) + r")\.(?:" + re.escape(dataset) + r")\.([A-Za-z_][A-Za-z0-9_]*)`?", re.I)

    def rep(m: "re.Match[str]") -> str:
        sp = names.get(m.group(1).lower())
        if sp:
            return sp if sp == graph else f"`{sp}`"
        unmapped.append(m.group(1))
        return m.group(0)
    out = pat.sub(rep, q)
    # any other fully-qualified BigQuery table (`p.d.t` of another dataset) cannot run on Spanner
    for ident in re.findall(r"`([^`]+)`", out):
        if ident.count(".") >= 2:
            unmapped.append(ident)
    return _columns_to_return(out), unmapped


def route(q: str, plan: Dict[str, Any], env: Dict[str, Any]) -> Dict[str, Any]:
    """Where to run a (BigQuery-dialect) query of a Spanner-engine workspace.
    → {"target": "spanner", "query": rewritten} or {"target": "bigquery", "query": original, "reason": …}."""
    sp = plan.get("spanner") or {}
    names = sp.get("names") or {}
    if not names or not plan.get("graph_ready"):
        return {"target": "bigquery", "query": q, "reason": "no spanner graph"}
    rq, unmapped = to_spanner(q, names, env["project"], env["dataset"])
    if unmapped:
        if re.search(r"\bGRAPH_TABLE\b|^\s*GRAPH\b", q, re.I):
            return {"target": "spanner", "query": rq, "unmapped": unmapped}
        return {"target": "bigquery", "query": q, "reason": "bigquery-only tables: " + ", ".join(dict.fromkeys(unmapped))}
    return {"target": "spanner", "query": rq}


def run_query(log: McpLog, q: str, plan: Dict[str, Any], env: Dict[str, Any], timeout_s: int = 70,
              label: str = "") -> Dict[str, Any]:
    """Execute a BigQuery-dialect query on the right engine. Adds `engine` + `executed` to the result."""
    r = route(q, plan, env)
    if r["target"] == "spanner":
        res = log.call("spanner_execute_sql", {"database": (plan.get("spanner") or {}).get("database") or db_path(env),
                                               "sql": r["query"], "timeout_s": min(60, timeout_s)}, timeout_s=timeout_s, label=label or "Spanner GQL")
    else:
        res = log.call("bigquery_execute_sql", {"project": env["project"], "sql": q, "location": env["region"], "timeout_ms": 45000,
                                                "labels": {"datacloud": "jetski", "app": "aos-starter"}}, timeout_s=timeout_s, label=label)
    res = dict(res)
    res["engine"] = r["target"]
    res["executed"] = r["query"]
    return res


# ================================================================================================ build
class SpannerUnavailable(RuntimeError):
    """Spanner instance/database missing or not permitted — S4 falls back to BigQuery Graph (visibly)."""


def _wait_op(log: McpLog, res: Dict[str, Any], label: str, limit_s: int = 300) -> None:
    if res.get("status") != "SUCCESS":
        raise RuntimeError(f"{label}: {error_text(res)[:400]}")
    op = res.get("operation") or {}
    t0 = time.perf_counter()
    while not op.get("done") and op.get("name"):
        if time.perf_counter() - t0 > limit_s:
            raise RuntimeError(f"{label}: operation timeout ({limit_s}s) {op.get('name')}")
        time.sleep(2.0)
        g = log.call("spanner_get_operation", {"name": op["name"]}, timeout_s=40, label=label)
        if g.get("status") != "SUCCESS":
            raise RuntimeError(f"{label}: {error_text(g)[:400]}")
        op = g.get("operation") or {}
    if op.get("error"):
        err = op["error"]
        raise RuntimeError(f"{label}: {err.get('message') if isinstance(err, dict) else err}"[:600])


def preflight(log: McpLog, env: Dict[str, Any], lang: str, create: bool = True) -> Dict[str, Any]:
    """Instance reachable + database exists (created when `create`). Raises SpannerUnavailable with a clear reason."""
    if not env.get("spanner_instance"):
        raise SpannerUnavailable(t(lang, "Spanner 인스턴스가 지정되지 않았습니다", "no Spanner instance configured"))
    gi = log.call("spanner_get_instance", {"instance": instance_path(env)}, timeout_s=30, label=instance_path(env))
    if gi.get("status") != "SUCCESS":
        raise SpannerUnavailable(t(lang, f"Spanner 인스턴스 {env['spanner_instance']}에 접근할 수 없습니다: {error_text(gi)[:240]}",
                                   f"cannot access Spanner instance {env['spanner_instance']}: {error_text(gi)[:240]}"))
    inst = gi.get("instance") or {}
    gd = log.call("spanner_get_database", {"database": db_path(env)}, timeout_s=30, label=db_path(env))
    if gd.get("status") != "SUCCESS":
        raise SpannerUnavailable(t(lang, f"Spanner DB 조회 실패: {error_text(gd)[:240]}", f"Spanner database lookup failed: {error_text(gd)[:240]}"))
    created = False
    if not gd.get("exists"):
        if not create:
            return {"instance": inst, "exists": False, "created": False}
        c = log.call("spanner_create_database", {"instance": instance_path(env), "database_id": env.get("spanner_database") or DEFAULT_DATABASE,
                                                 "timeout_s": 120}, timeout_s=150, label="CREATE DATABASE")
        if c.get("status") != "SUCCESS":
            if "already exists" in error_text(c).lower():  # another workspace created it concurrently
                return {"instance": inst, "exists": True, "created": False, "processing_units": inst.get("processingUnits")}
            raise SpannerUnavailable(t(lang, f"Spanner DB 생성 실패: {error_text(c)[:240]} — roles/spanner.databaseAdmin 필요",
                                       f"Spanner database creation failed: {error_text(c)[:240]} — needs roles/spanner.databaseAdmin"))
        try:
            _wait_op(log, c, "CREATE DATABASE", 240)
        except RuntimeError as e:
            raise SpannerUnavailable(str(e)) from e
        created = True
    return {"instance": inst, "exists": True, "created": created, "processing_units": inst.get("processingUnits")}


def build(log: McpLog, env: Dict[str, Any], ws_id: str, nd: Dict[str, Any], verify: List[Dict[str, Any]], lang: str,
          step: Callable[..., None]) -> Dict[str, Any]:
    """Spanner side of S4: preflight → drop old → CREATE TABLE + PROPERTY GRAPH → copy rows from BigQuery → verify.
    Raises SpannerUnavailable (→ caller falls back to BigQuery Graph) for access/DDL problems before any data moved."""
    s = time.perf_counter()
    pre = preflight(log, env, lang)
    db = db_path(env)
    gname = graph_name(env, ws_id)
    step("spanner_db", "done", t(lang, "Spanner DB", "Spanner database"),
         f"{db}" + (" (new)" if pre.get("created") else "") + (f" · {pre.get('processing_units')} PU" if pre.get("processing_units") else ""),
         round((time.perf_counter() - s) * 1000))
    spec = ddl(nd, ws_id, gname)
    s = time.perf_counter()
    cur = log.call("spanner_get_ddl", {"database": db}, timeout_s=40, label="get DDL")
    if cur.get("status") != "SUCCESS":
        raise SpannerUnavailable(t(lang, f"Spanner DDL 조회 실패: {error_text(cur)[:240]}", f"Spanner getDdl failed: {error_text(cur)[:240]}"))
    drops = drop_statements(cur.get("statements") or [], ws_id, gname)
    expired_ws: List[str] = []
    if identity.current().get("mode") == "runtime":  # shared demo DB → same 7-day policy as the BigQuery demo datasets
        exp, expired_ws = expired_drop_statements(cur.get("statements") or [], keep_ws=ws_id)
        exp_g = [x for x in exp if x.startswith("DROP PROPERTY GRAPH") and x not in drops]
        exp_t = [x for x in exp if x.startswith("DROP TABLE") and x not in drops]
        drops = exp_g + [x for x in drops if x.startswith("DROP PROPERTY GRAPH")] + [x for x in drops if x.startswith("DROP TABLE")] + exp_t
    if drops:
        try:
            _wait_op(log, log.call("spanner_update_ddl", {"database": db, "statements": drops, "timeout_s": 120}, timeout_s=150,
                                   label="DROP (rebuild)"), "DROP (rebuild)")
        except RuntimeError as e:
            raise SpannerUnavailable(t(lang, f"이전 Spanner 그래프 삭제 실패: {e} — roles/spanner.databaseAdmin 필요",
                                       f"dropping the previous Spanner graph failed: {e} — needs roles/spanner.databaseAdmin")) from e
    try:
        _wait_op(log, log.call("spanner_update_ddl", {"database": db, "statements": spec["table_statements"] + [spec["graph_statement"]],
                                                      "timeout_s": 120}, timeout_s=150, label="CREATE TABLE + PROPERTY GRAPH"),
                 "CREATE TABLE + PROPERTY GRAPH")
    except RuntimeError as e:
        raise SpannerUnavailable(t(lang, f"Spanner DDL 실패: {e}", f"Spanner DDL failed: {e}")) from e
    step("spanner_ddl", "done", t(lang, "Spanner DDL (테이블 + Property Graph)", "Spanner DDL (tables + Property Graph)"),
         t(lang, f"테이블 {len(spec['tables'])}개 · 그래프 {gname}" + (f" · 이전 {len(drops)}개 삭제" if drops else ""),
           f"{len(spec['tables'])} tables · graph {gname}" + (f" · {len(drops)} old objects dropped" if drops else ""))
         + (t(lang, f" · 만료 워크스페이스 {len(expired_ws)}개 정리({TTL_DAYS}일)", f" · {len(expired_ws)} expired workspaces purged ({TTL_DAYS}d)") if expired_ws else ""),
         round((time.perf_counter() - s) * 1000))

    copies: List[Dict[str, Any]] = []

    def copy(tb: Dict[str, Any]) -> Dict[str, Any]:
        s1 = time.perf_counter()
        cols = ", ".join(f"`{c}`" for c in tb["columns"])
        rr = log.call("bigquery_execute_sql", {"project": env["project"], "location": env["region"], "timeout_ms": 60000,
                                               "sql": f"SELECT {cols} FROM `{env['project']}.{env['dataset']}.{tb['bq']}` LIMIT {MAX_COPY_ROWS + 1}",
                                               "labels": {"datacloud": "jetski", "app": "aos-starter"}}, timeout_s=100, label=f"read {tb['bq']}")
        if rr.get("status") != "SUCCESS":
            return {"table": tb["spanner"], "ok": False, "rows": 0, "error": "BigQuery read: " + error_text(rr)[:300], "ms": round((time.perf_counter() - s1) * 1000)}
        rows = rr.get("rows") or []
        truncated = len(rows) > MAX_COPY_ROWS
        rows = rows[:MAX_COPY_ROWS]
        vals = []
        for r in rows:
            v = [sp_value(tb["types"][c], r.get(c)) for c in tb["columns"]]
            if any(v[tb["columns"].index(k)] is None for k in tb["key"]):
                continue
            vals.append(v)
        per = max(1, _CELLS_PER_COMMIT // max(1, len(tb["columns"])))
        for i in range(0, len(vals), per):
            cm = log.call("spanner_commit", {"database": db, "mutations": [{"insertOrUpdate": {"table": tb["spanner"], "columns": tb["columns"],
                                                                                                 "values": vals[i:i + per]}}]},
                          timeout_s=90, label=f"commit {tb['spanner']}")
            if cm.get("status") != "SUCCESS":
                return {"table": tb["spanner"], "ok": False, "rows": i, "error": "Spanner commit: " + error_text(cm)[:300],
                        "ms": round((time.perf_counter() - s1) * 1000)}
        return {"table": tb["spanner"], "ok": True, "rows": len(vals), "truncated": truncated, "ms": round((time.perf_counter() - s1) * 1000)}

    nodes = [x for x in spec["tables"] if x["kind"] == "node"]
    edges = [x for x in spec["tables"] if x["kind"] == "edge"]
    with ThreadPoolExecutor(max_workers=4) as ex:
        copies += list(ex.map(identity.carry(copy), nodes))
        copies += list(ex.map(identity.carry(copy), edges))
    for c in copies:
        step(f"copy:{c['table']}", "done" if c["ok"] else "error", t(lang, "Spanner 적재 ", "Spanner load ") + c["table"],
             (f"{c['rows']:,} rows" + (t(lang, " (상한 도달 — 일부만)", " (row cap reached — partial)") if c.get("truncated") else "")) if c["ok"] else c["error"][:200],
             c["ms"])
    failed = [c for c in copies if not c["ok"]]
    names = name_map(nd, env, ws_id)
    sp_plan = {"engine": "spanner", "database": db, "instance": env.get("spanner_instance"), "graph": gname, "names": names,
               "statements": spec["table_statements"] + [spec["graph_statement"]], "dropped": drops, "expired_purged": expired_ws, "copies": copies,
               "console": console_url(env)}
    vres: List[Dict[str, Any]] = []
    if not failed:
        fake_plan = {"spanner": sp_plan, "graph_ready": True}
        for q in verify or []:
            s1 = time.perf_counter()
            rr = run_query(log, q["sql"], fake_plan, env, label=q.get("title", "verify"))
            ok = rr.get("status") == "SUCCESS"
            rows = rr.get("rows") or []
            vres.append({**q, "sql_bigquery": q["sql"], "sql": rr.get("executed", q["sql"]), "engine": rr.get("engine"), "ok": ok,
                         "rows": rows[:8], "row_count": len(rows), "ms": round((time.perf_counter() - s1) * 1000),
                         "error": "" if ok else error_text(rr)[:300]})
        good = sum(1 for v in vres if v["ok"])
        step("verify", "done" if good == len(vres) else "warn", t(lang, "검증 GQL (Spanner)", "verification GQL (Spanner)"), f"{good}/{len(vres)}")
    return {"spanner": sp_plan, "verify": vres, "failed": failed, "graph_ready": not failed}
