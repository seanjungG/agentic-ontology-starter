# Copyright (c) 2026 Sean Jung (seanjung@google.com). All Rights Reserved.
# Non-Commercial Use Only: Methodology & Docs under CC BY-NC-ND 4.0; Source Code under PolyForm Noncommercial License 1.0.0.
# Commercial use, paid consulting/SI/PoC delivery, or production deployment requires prior written permission from seanjung@google.com.

# -*- coding: utf-8 -*-
"""Data sources for a workspace (GOAL-233): uploads · GCS paths · BigQuery tables · the bundled sample pack.

Documents: .md / .txt (UTF-8). Tables: .csv (header row; types inferred) or existing BigQuery tables.
"""
from __future__ import annotations

import csv
import io
import os
import re
from typing import Any, Dict, List, Optional, Tuple

from src.aos.ws import McpLog, error_text, get_text

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
SAMPLE_DIR = os.path.join(BASE_DIR, "data", "input")
DOC_EXT = (".md", ".markdown", ".txt")
TABLE_EXT = (".csv",)
CONVERT_EXT = (".pdf", ".docx", ".pptx", ".xlsx", ".html", ".htm")  # GOAL-243: converted to Markdown by Core MCP
MAX_FILE_BYTES = 6 * 1024 * 1024
MAX_FILES = 30
_GS = re.compile(r"^gs://([a-z0-9][a-z0-9._-]{1,220}[a-z0-9])/?(.*)$")
_FQ = re.compile(r"^`?([a-z][a-z0-9-]{4,28}[a-z0-9])[.:]([A-Za-z_][A-Za-z0-9_]{0,1023})\.([A-Za-z_][A-Za-z0-9_$-]{0,1023})`?$")
_DS = re.compile(r"^`?([a-z][a-z0-9-]{4,28}[a-z0-9])[.:]([A-Za-z_][A-Za-z0-9_]{0,1023})`?$")


def parse_gs(uri: str) -> Tuple[str, str]:
    m = _GS.match(str(uri or "").strip())
    if not m:
        raise ValueError(f"not a gs:// URI: {uri}")
    return m.group(1), m.group(2)


def parse_fq(fq: str) -> Tuple[str, str, str]:
    m = _FQ.match(str(fq or "").strip())
    if not m:
        raise ValueError(f"not a BigQuery table id (project.dataset.table): {fq}")
    return m.group(1), m.group(2), m.group(3)


def parse_dataset(fq: str) -> Tuple[str, str]:
    m = _DS.match(str(fq or "").strip())
    if not m:
        raise ValueError(f"not a BigQuery dataset id (project.dataset): {fq}")
    return m.group(1), m.group(2)


def safe_name(name: str) -> str:
    base = os.path.basename(str(name or "")).strip()
    base = re.sub(r"[^A-Za-z0-9._가-힣-]+", "_", base)[:120]
    return base or "file"


def table_name(name: str) -> str:
    stem = os.path.splitext(os.path.basename(name))[0]
    s = re.sub(r"[^A-Za-z0-9_]+", "_", stem).strip("_").lower()
    if not s or not s[0].isalpha():
        s = "t_" + s
    return s[:100]


def doc_id(name: str) -> str:
    stem = os.path.splitext(os.path.basename(name))[0]
    s = re.sub(r"[^A-Za-z0-9]+", "-", stem).strip("-").upper()
    return (s or "DOC")[:40]


# ------------------------------------------------------------------------------------------------ CSV
_INT = re.compile(r"^-?\d{1,18}$")
_FLOAT = re.compile(r"^-?\d+(\.\d+)?([eE][-+]?\d+)?$")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_BOOL = {"true", "false"}


def infer_type(values: List[str]) -> str:
    vals = [v for v in values if v not in ("", None)]
    if not vals:
        return "STRING"
    if all(_INT.match(v) for v in vals) and not any(len(v) > 1 and v.startswith("0") and not v.startswith("0.") for v in vals):
        return "INT64"
    if all(_FLOAT.match(v) for v in vals):
        return "FLOAT64"
    if all(v.lower() in _BOOL for v in vals):
        return "BOOL"
    if all(_DATE.match(v) for v in vals):
        return "DATE"
    return "STRING"


def col_name(c: str, i: int) -> str:
    s = re.sub(r"[^A-Za-z0-9_]+", "_", str(c or "").strip()).strip("_").lower()
    if not s or not (s[0].isalpha() or s[0] == "_"):
        s = f"col_{i + 1}" if not s else "c_" + s
    return s[:120]


def parse_csv(text: str) -> Dict[str, Any]:
    text = text.lstrip("\ufeff")
    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel
    rdr = csv.reader(io.StringIO(text), dialect)
    rows = [r for r in rdr if any(c.strip() for c in r)]
    if not rows:
        raise ValueError("empty CSV")
    header = rows[0]
    names, seen = [], set()
    for i, h in enumerate(header):
        n = col_name(h, i)
        while n in seen:
            n += "_x"
        seen.add(n)
        names.append(n)
    body = rows[1:]
    types = [infer_type([r[i] if i < len(r) else "" for r in body[:5000]]) for i in range(len(names))]
    out_rows = []
    for r in body:
        rec: Dict[str, Any] = {}
        for i, n in enumerate(names):
            v = r[i] if i < len(r) else ""
            if v == "":
                rec[n] = None
            elif types[i] == "INT64":
                rec[n] = int(v)
            elif types[i] == "FLOAT64":
                rec[n] = float(v)
            elif types[i] == "BOOL":
                rec[n] = v.lower() == "true"
            else:
                rec[n] = v
        out_rows.append(rec)
    return {"columns": [{"name": n, "type": t, "description": str(header[i]).strip() if str(header[i]).strip() != n else ""}
                        for i, (n, t) in enumerate(zip(names, types))], "rows": out_rows}


# ------------------------------------------------------------------------------------------------ sample pack
SAMPLE_TABLES = ("devices", "plans", "subsidies", "customer_contracts", "domain_rules", "rule_plan_edges")


def sample_sources(lang: str) -> Dict[str, Any]:
    lang = "en" if lang == "en" else "ko"
    gdir = os.path.join(SAMPLE_DIR, "01_guides", lang)
    docs = []
    for fn in sorted(os.listdir(gdir)):
        if fn.endswith(".md"):
            p = os.path.join(gdir, fn)
            docs.append({"name": fn, "origin": "sample", "uri": f"sample:01_guides/{lang}/{fn}", "chars": len(open(p, encoding="utf-8").read())})
    tables = []
    for tname in SAMPLE_TABLES:
        p = os.path.join(SAMPLE_DIR, "03_tables", f"{tname}.csv")
        if os.path.exists(p):
            n = sum(1 for _ in open(p, encoding="utf-8")) - 1
            tables.append({"name": tname, "origin": "sample", "uri": f"sample:03_tables/{tname}.csv", "rows": n})
    return {"docs": docs, "tables": tables, "sample": lang}


def read_sample(uri: str) -> str:
    rel = uri.split(":", 1)[1]
    p = os.path.realpath(os.path.join(SAMPLE_DIR, rel))
    if not p.startswith(os.path.realpath(SAMPLE_DIR) + os.sep):
        raise ValueError("sample path escapes the data directory")
    with open(p, encoding="utf-8") as f:
        return f.read()


# ------------------------------------------------------------------------------------------------ readers
def read_source_text(log: McpLog, uri: str) -> str:
    if uri.startswith("sample:"):
        return read_sample(uri)
    bucket, name = parse_gs(uri)
    code, txt = get_text(log, bucket, name)
    if code != 200:
        raise RuntimeError(f"gs://{bucket}/{name}: HTTP {code} {txt[:200]}")
    return txt


def list_gcs(log: McpLog, uri: str) -> Dict[str, Any]:
    bucket, pfx = parse_gs(uri)
    res = log.call("storage_list_objects", {"bucket": bucket, "prefix": pfx}, timeout_s=40, label=uri)
    if res.get("status") != "SUCCESS":
        return {"status": "ERROR", "error": error_text(res)}
    docs, tables, other = [], [], []
    for it in (res.get("items") or [])[:500]:
        name = it.get("name", "")
        if name.endswith("/"):
            continue
        size = int(it.get("size") or 0)
        entry = {"name": os.path.basename(name), "uri": f"gs://{bucket}/{name}", "size": size}
        low = name.lower()
        if low.endswith(DOC_EXT):
            docs.append({**entry, "origin": "gcs", "chars": size})
        elif low.endswith(CONVERT_EXT):  # GOAL-243: PDF / Office / HTML → converted by Core MCP when added
            docs.append({**entry, "origin": "gcs", "chars": 0, "convert": True})
        elif low.endswith(TABLE_EXT):
            tables.append({**entry, "origin": "gcs", "name": table_name(name)})
        else:
            other.append(entry)
    return {"status": "SUCCESS", "docs": docs[:MAX_FILES], "tables": tables[:MAX_FILES], "other": other[:50]}


def bq_list_tables(log: McpLog, dataset_fq: str, region: str) -> Dict[str, Any]:
    project, dataset = parse_dataset(dataset_fq)
    sql = (f"SELECT table_name, table_type FROM `{project}.{dataset}.INFORMATION_SCHEMA.TABLES` "
           f"WHERE table_type IN ('BASE TABLE','VIEW') ORDER BY table_name LIMIT 200")
    res = log.call("bigquery_execute_sql", {"project": project, "sql": sql, "location": region, "labels": {"datacloud": "jetski"}},
                   timeout_s=70, label=dataset_fq)
    if res.get("status") != "SUCCESS":
        return {"status": "ERROR", "error": error_text(res)}
    return {"status": "SUCCESS", "tables": [{"name": r["table_name"], "fq": f"{project}.{dataset}.{r['table_name']}", "origin": "bigquery",
                                             "type": r.get("table_type")} for r in res.get("rows") or []]}


def bq_table_profile(log: McpLog, fq: str, region: str, sample_rows: int = 120) -> Dict[str, Any]:
    project, dataset, table = parse_fq(fq)
    info = log.call("bigquery_get_table_info", {"project": project, "dataset": dataset, "table": table}, timeout_s=40, label=fq)
    if info.get("status") != "SUCCESS":
        raise RuntimeError(f"{fq}: {error_text(info)}")
    meta = info.get("table") or info
    fields = ((meta.get("schema") or {}).get("fields")) or meta.get("fields") or []
    cols = [{"name": f["name"], "type": str(f.get("type") or "STRING").upper(), "description": f.get("description", "")}
            for f in fields if str(f.get("type", "")).upper() not in ("RECORD", "STRUCT") and f.get("mode") != "REPEATED"]
    rows_res = log.call("bigquery_execute_sql", {"project": project, "location": region, "labels": {"datacloud": "jetski"},
                                                 "sql": f"SELECT {', '.join('`' + c['name'] + '`' for c in cols[:80])} FROM `{project}.{dataset}.{table}` LIMIT {sample_rows}"},
                        timeout_s=70, label=f"sample {fq}")
    rows = rows_res.get("rows") or [] if rows_res.get("status") == "SUCCESS" else []
    return {"name": table_name(table), "fq": f"{project}.{dataset}.{table}", "columns": cols[:80], "rows": rows,
            "row_count": int(meta.get("numRows") or meta.get("num_rows") or len(rows)), "description": meta.get("description", "")}


def table_from_csv_text(name: str, text: str) -> Dict[str, Any]:
    parsed = parse_csv(text)
    return {"name": table_name(name), "columns": parsed["columns"], "rows": parsed["rows"], "row_count": len(parsed["rows"])}


def bq_schema(columns: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [{"name": c["name"], "type": c["type"], "mode": "NULLABLE", **({"description": c["description"][:1000]} if c.get("description") else {})}
            for c in columns]


def json_rows(rows: List[Dict[str, Any]], columns: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Rows as JSON-safe values for bigquery_load_table (DATE stays 'YYYY-MM-DD')."""
    names = [c["name"] for c in columns]
    return [{n: r.get(n) for n in names} for r in rows]


def detect_kind(name: str) -> Optional[str]:
    low = name.lower()
    if low.endswith(DOC_EXT):
        return "doc"
    if low.endswith(TABLE_EXT):
        return "table"
    return None
