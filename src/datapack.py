# Copyright (c) 2026 Sean Jung (seanjung@google.com). All Rights Reserved.
# Non-Commercial Use Only: Methodology & Docs under CC BY-NC-ND 4.0; Source Code under PolyForm Noncommercial License 1.0.0.
# Commercial use, paid consulting/SI/PoC delivery, or production deployment requires prior written permission from seanjung@google.com.

# -*- coding: utf-8 -*-
"""Bilingual starter data pack (GOAL-223).

Two complete sets — `ko` and `en` — with the same ids, keys and numbers:
  data/input/01_guides/{ko,en}/*.md         source documents (DOC_CHUNK_00x markers)
  data/llm_wiki/{ko,en}/*.md                OKF wiki pages (rules.md frontmatter = single source of policy values)
  data/input/03_tables/*.csv                language-neutral rows + *_ko / *_en label columns
  data/input/03_tables/table_specs.json     BigQuery schema, ko/en column descriptions, graph elements
  data/input/04_cq/{ko,en}/*.json           golden CQs + boundary questions
  data/input/05_glossary/{ko,en}/*.json     glossary = wiki concepts
  data/input/06_workflows/{ko,en}/*.json    W1–W3 workflow steps
"""
import csv
import hashlib
import json
import os
import re
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA = os.path.join(BASE_DIR, "data")
LANGS = ("ko", "en")
HANGUL = re.compile(r"[\u3131-\uD79D]")

DOC_FILES = ("sample_policy_guide.md", "sample_welfare_exemption_guide.md")
WIKI_PAGES = ("summary", "concepts", "rules", "entities")
# Flow A (documents only) uploads the document-derived pages; Flow C adds the table-meaning page (P3 bridge).
WIKI_BY_RECIPE = {"A": ("summary", "concepts", "rules"), "B": (), "C": WIKI_PAGES}
TABLE_GROUPS_BY_RECIPE = {"A": (), "B": ("p2_source", "p2_edges"), "C": ("p2_source", "p2_edges", "p3_nodes", "p3_edges")}
LEGACY_KO_COLUMNS = {("tb_domain_rules", "rule_name")}
LEGACY_EN_COLUMNS = {("tb_doc_chunks", "section_title"), ("tb_doc_chunks", "content")}
_CHUNK_RE = re.compile(r"<!--\s*(DOC_CHUNK_\d{3})\s*:\s*(.*?)\s*-->")


def _lang(lang: Optional[str]) -> str:
    return "en" if str(lang or "").lower() == "en" else "ko"


def _read(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------------------------------- documents
@lru_cache(maxsize=4)
def docs(lang: str = "ko") -> Tuple[Dict[str, Any], ...]:
    lang = _lang(lang)
    out = []
    for fname in DOC_FILES:
        path = os.path.join(DATA, "input", "01_guides", lang, fname)
        text = _read(path)
        title = next((ln.lstrip("# ").strip() for ln in text.splitlines() if ln.startswith("# ")), fname)
        marks = list(_CHUNK_RE.finditer(text))
        chunks = []
        for i, m in enumerate(marks):
            end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
            body = text[m.end():end].strip()
            heading = next((ln for ln in body.splitlines() if ln.startswith("## ")), "")
            art = re.match(r"##\s*(\d+)\.", heading)
            chunks.append({"chunk_id": m.group(1), "title": m.group(2), "content": body,
                           "article_no": f"§{art.group(1)}" if art else ""})
        out.append({"doc_id": fname[:-3], "file": fname, "title": title, "text": text, "chars": len(text),
                    "sha256": sha256(text), "chunks": chunks})
    return tuple(out)


def doc_chunk_rows() -> List[Dict[str, Any]]:
    ko = {c["chunk_id"]: (d, c) for d in docs("ko") for c in d["chunks"]}
    en = {c["chunk_id"]: (d, c) for d in docs("en") for c in d["chunks"]}
    rows = []
    for cid in sorted(en):
        d_en, c_en = en[cid]
        _, c_ko = ko[cid]
        rows.append({
            "chunk_id": cid, "source_file": d_en["file"], "section_title": c_en["title"], "content": c_en["content"],
            "content_sha256": sha256(c_en["content"]), "trust_tier": "SYNTHETIC_DEMO", "source_doc": d_en["doc_id"],
            "source_sha256": d_en["sha256"], "page_from": 1, "page_to": 1, "article_no": c_en["article_no"],
            "section_title_ko": c_ko["title"], "section_title_en": c_en["title"],
            "content_ko": c_ko["content"], "content_en": c_en["content"],
        })
    return rows


# ---------------------------------------------------------------------------------------------------- wiki
def parse_frontmatter(text: str) -> Tuple[Dict[str, Any], str]:
    """Tiny YAML-subset parser for the wiki frontmatter (nested maps of scalars, inline [a, b] lists)."""
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end < 0:
        return {}, text
    head, body = text[3:end].strip("\n"), text[end + 4:].lstrip("\n")
    root: Dict[str, Any] = {}
    stack: List[Tuple[int, Dict[str, Any]]] = [(-1, root)]
    for raw in head.splitlines():
        if not raw.strip() or raw.strip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        key, _, val = raw.strip().partition(":")
        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]
        val = val.strip()
        if not val:
            child: Dict[str, Any] = {}
            parent[key.strip()] = child
            stack.append((indent, child))
            continue
        if val.startswith("[") and val.endswith("]"):
            parent[key.strip()] = [v.strip() for v in val[1:-1].split(",") if v.strip()]
            continue
        num: Any = val
        try:
            num = int(val)
        except ValueError:
            try:
                num = float(val)
            except ValueError:
                num = val.strip("'\"")
        parent[key.strip()] = num
    return root, body


@lru_cache(maxsize=4)
def wiki(lang: str = "ko") -> Tuple[Dict[str, Any], ...]:
    lang = _lang(lang)
    out = []
    for page in WIKI_PAGES:
        text = _read(os.path.join(DATA, "llm_wiki", lang, f"{page}.md"))
        fm, body = parse_frontmatter(text)
        out.append({"page": page, "title": fm.get("title", page), "layer": fm.get("layer", ""), "text": text,
                    "body": body, "chars": len(text), "sources": fm.get("sources", []),
                    "recipes": [r for r, pages in WIKI_BY_RECIPE.items() if page in pages]})
    return tuple(out)


def wiki_pages(lang: str, recipe: str) -> List[Dict[str, Any]]:
    keep = WIKI_BY_RECIPE.get(recipe, ())
    return [p for p in wiki(lang) if p["page"] in keep]


def policy_constants(text: Optional[str] = None, lang: str = "ko") -> Dict[str, Any]:
    if text is None:
        text = next(p["text"] for p in wiki(lang) if p["page"] == "rules")
    fm, _ = parse_frontmatter(text)
    return dict(((fm.get("graph") or {}).get("properties") or {}))


# ---------------------------------------------------------------------------------------------------- CQs · glossary · workflows
@lru_cache(maxsize=4)
def cq_set(lang: str = "ko") -> Dict[str, Any]:
    return _json(os.path.join(DATA, "input", "04_cq", _lang(lang), "golden_cqs.json"))


def cqs(lang: str = "ko", recipe: Optional[str] = None) -> List[Dict[str, Any]]:
    items = cq_set(lang)["cqs"]
    return [c for c in items if not recipe or recipe in c["recipes"]]


@lru_cache(maxsize=4)
def boundary(lang: str = "ko") -> List[Dict[str, Any]]:
    return _json(os.path.join(DATA, "input", "04_cq", _lang(lang), "boundary_cases.json"))


@lru_cache(maxsize=4)
def glossary(lang: str = "ko") -> List[Dict[str, Any]]:
    return _json(os.path.join(DATA, "input", "05_glossary", _lang(lang), "business_glossary.json"))


@lru_cache(maxsize=4)
def workflows(lang: str = "ko") -> List[Dict[str, Any]]:
    return _json(os.path.join(DATA, "input", "06_workflows", _lang(lang), "workflows.json"))["workflows"]


# ---------------------------------------------------------------------------------------------------- tables
@lru_cache(maxsize=1)
def table_specs() -> Dict[str, Any]:
    return _json(os.path.join(DATA, "input", "03_tables", "table_specs.json"))


def _csv(name: str) -> List[Dict[str, str]]:
    with open(os.path.join(DATA, "input", "03_tables", name), "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def tables_for(recipe: str) -> List[str]:
    groups = TABLE_GROUPS_BY_RECIPE.get(recipe, ())
    return [n for g in groups for n, t in table_specs()["tables"].items() if t["group"] == g]


def bq_fields(table: str, lang: str = "ko") -> List[Dict[str, Any]]:
    lang = _lang(lang)
    return [{"name": c["name"], "type": c["type"], "mode": "NULLABLE", "description": c[lang]}
            for c in table_specs()["tables"][table]["columns"]]


def table_description(table: str, lang: str = "ko") -> str:
    return table_specs()["tables"][table][f"description_{_lang(lang)}"]


@lru_cache(maxsize=1)
def _all_rows() -> Dict[str, Tuple[Dict[str, Any], ...]]:
    devices = _csv("devices.csv")
    plans = _csv("plans.csv")
    subs = _csv("subsidies.csv")
    contracts = _csv("customer_contracts.csv")
    rules = _csv("domain_rules.csv")
    rp_edges = _csv("rule_plan_edges.csv")

    dev_rows = [{
        "device_id": d["device_id"], "device_name": f"{d['pet_name']} {d['storage']}", "manufacturer": d["manufacturer"],
        "storage_gb": int(re.sub(r"\D", "", d["storage"]) or 0), "factory_price_krw": int(d["factory_price"]),
        "release_date": d["release_date"], "provenance": d["provenance"], "source_ref": d["source_ref"], "model_code": d["model_code"],
    } for d in devices]
    plan_rows = [{
        "plan_id": p["plan_id"], "plan_name": p["plan_name"], "tier_category": p["tier_category"],
        "monthly_fee_krw": int(p["monthly_fee"]), "min_maintenance_days": int(p["min_maintenance_days"]),
        "selective_discount_rate": float(p["selective_discount_rate"]), "provenance": p["provenance"], "source_ref": p["source_ref"],
        "network_type": p["network_type"], "is_baseline_tier": p["is_baseline_tier"].strip().lower() == "true",
    } for p in plans]
    sub_rows = [{
        "policy_id": s["policy_id"], "device_id": s["device_id"], "plan_id": s["plan_id"],
        "base_subsidy_krw": int(s["basic_subsidy"]), "additional_subsidy_cap_krw": int(s["distribution_subsidy"]),
        "mandatory_retention_days": int(s["mandatory_retention_days"]), "effective_from": s["effective_start_date"],
        "provenance": s["provenance"], "source_ref": s["source_ref"], "effective_to": s["effective_end_date"],
        "total_subsidy_krw": int(s["basic_subsidy"]) + int(s["distribution_subsidy"]),
    } for s in subs]
    total_by_pair = {(s["device_id"], s["plan_id"]): s["total_subsidy_krw"] for s in sub_rows}
    con_rows = [{
        "customer_id": c["customer_id"], "contract_id": c["contract_id"], "customer_segment": c["customer_segment"],
        "age_group": c["age_group"], "device_id": c["device_id"], "plan_id": c["plan_id"], "contract_type": c["contract_type"],
        "commitment_months": int(c["commitment_months"]), "elapsed_days": int(c["elapsed_days"]),
        "granted_subsidy_krw": total_by_pair.get((c["device_id"], c["plan_id"]), 0) if c["contract_type"] == "PUBLIC_SUBSIDY" else 0,
        "welfare_status": c["welfare_status"], "status": c["status"], "provenance": c["provenance"], "source_ref": c["source_ref"],
        "policy_id": c["policy_id"], "activation_date": c["activation_date"],
    } for c in contracts]
    rule_rows = [{k: r[k] for k in ("rule_id", "rule_name", "rule_category", "condition_expr", "formula_expr", "source_chunk_id",
                                    "description_ko", "provenance", "source_ref", "rule_name_ko", "rule_name_en", "description_en")}
                 for r in rules]
    rp_rows = [{"edge_id": e["edge_id"], "rule_id": e["rule_id"], "plan_id": e["plan_id"], "source_chunk_id": e["source_chunk_id"],
                "relation_label_ko": e["relation_label_ko"], "edge_type": "APPLIES_TO_PLAN", "provenance": e["provenance"],
                "source_ref": e["source_ref"], "relation_label_en": e["relation_label_en"]} for e in rp_edges]

    # P3 — wiki concepts · policy values · workflow steps · clause anchors and their bridge edges
    g_ko = {g["concept_id"]: g for g in glossary("ko")}
    concepts = [{"concept_id": g["concept_id"], "name_ko": g_ko[g["concept_id"]]["term"], "name_en": g["term"],
                 "definition_ko": g_ko[g["concept_id"]]["definition"], "definition_en": g["definition"],
                 "source_chunk_id": g["source_chunk_id"], "wiki_page": g["wiki_page"]} for g in glossary("en")]
    consts = policy_constants(lang="ko")
    meta = table_specs()["policy_params"]
    params = [{"param_id": k, "value": float(v), "value_text": str(v), "unit": meta[k]["unit"], "rule_id": meta[k]["rule_id"],
               "label_ko": meta[k]["ko"], "label_en": meta[k]["en"], "wiki_page": "rules",
               "source_chunk_id": meta[k]["source_chunk_id"]} for k, v in consts.items() if k in meta]
    wf_ko = {s["step_id"]: (w, s) for w in workflows("ko") for s in w["steps"]}
    steps = []
    for w in workflows("en"):
        for s in w["steps"]:
            wko, sko = wf_ko[s["step_id"]]
            steps.append({"step_id": s["step_id"], "workflow_id": w["workflow_id"], "workflow_point": w["point"],
                          "step_order": s["order"], "step_kind": s["kind"], "name_ko": sko["name"], "name_en": s["name"],
                          "workflow_name_ko": wko["name"], "workflow_name_en": w["name"], "rule_id": s["rule_id"] or "",
                          "tool_name": s["tool"] or ""})
    governs = [{"edge_id": f"GOV_{g['concept_id']}_{r}", "concept_id": g["concept_id"], "rule_id": r, "edge_type": "GOVERNS"}
               for g in glossary("en") for r in g["rules"]]
    uses = [{"edge_id": f"USE_{p['rule_id']}_{p['param_id']}", "rule_id": p["rule_id"], "param_id": p["param_id"],
             "edge_type": "USES_PARAM"} for p in params]
    grounded_pairs = sorted({(r["rule_id"], r["source_chunk_id"]) for r in rule_rows} |
                            {(e["rule_id"], e["source_chunk_id"]) for e in rp_rows})
    grounded = [{"edge_id": f"GRD_{r}_{c}", "rule_id": r, "chunk_id": c, "edge_type": "GROUNDED_IN"} for r, c in grounded_pairs]
    applies = [{"edge_id": f"APR_{s['step_id']}_{s['rule_id']}", "step_id": s["step_id"], "rule_id": s["rule_id"],
                "edge_type": "APPLIES_RULE"} for s in steps if s["rule_id"]]

    rows = {
        "tb_device_master": dev_rows, "tb_plan_master": plan_rows, "tb_subsidy_policy": sub_rows,
        "tb_customer_contract": con_rows, "tb_domain_rules": rule_rows, "edge_rule_applies_to_plan": rp_rows,
        "edge_contract_device": [{"contract_id": c["contract_id"], "customer_id": c["customer_id"], "device_id": c["device_id"],
                                  "edge_type": "USES_DEVICE"} for c in con_rows],
        "edge_contract_plan": [{"contract_id": c["contract_id"], "customer_id": c["customer_id"], "plan_id": c["plan_id"],
                                "edge_type": "SUBSCRIBES_PLAN"} for c in con_rows],
        "edge_subsidy_binding": [{"policy_id": s["policy_id"], "device_id": s["device_id"], "plan_id": s["plan_id"],
                                  "total_subsidy_krw": s["total_subsidy_krw"], "edge_type": "HAS_SUBSIDY_POLICY"} for s in sub_rows],
        "tb_doc_chunks": doc_chunk_rows(), "tb_wiki_concepts": concepts, "tb_policy_params": params, "tb_workflow_steps": steps,
        "edge_concept_governs_rule": governs, "edge_rule_uses_param": uses, "edge_rule_grounded_in": grounded,
        "edge_step_applies_rule": applies,
    }
    return {k: tuple(v) for k, v in rows.items()}


def table_rows(table: str) -> List[Dict[str, Any]]:
    return [dict(r) for r in _all_rows()[table]]


def visible_columns(table: str, lang: str) -> List[str]:
    """Columns whose values are shown on a `lang` screen (EN screens never show Korean label values)."""
    lang = _lang(lang)
    cols = []
    for c in table_specs()["tables"][table]["columns"]:
        n = c["name"]
        if lang == "en" and (n.endswith("_ko") or (table, n) in LEGACY_KO_COLUMNS):
            continue
        if lang == "ko" and (n.endswith("_en") or (table, n) in LEGACY_EN_COLUMNS):
            continue
        cols.append(n)
    return cols


# ---------------------------------------------------------------------------------------------------- graph DDL
def graph_elements(recipe: str) -> Tuple[List[str], List[str]]:
    names = tables_for(recipe)
    specs = table_specs()["tables"]
    return [n for n in names if specs[n]["kind"] == "node"], [n for n in names if specs[n]["kind"] == "edge"]


def graph_ddl(project_id: str, dataset_id: str, graph_name: str, recipe: str) -> str:
    specs = table_specs()["tables"]
    fq = lambda t: f"`{project_id}.{dataset_id}.{t}`"  # noqa: E731
    nodes, edges = graph_elements(recipe)
    if not nodes:
        return ""
    def props(t: str) -> str:
        return ", ".join(c["name"] for c in specs[t]["columns"])
    node_sql = ",\n".join(
        f"    {fq(t)}\n      KEY ({', '.join(specs[t]['key'])})\n      LABEL {specs[t]['label']}\n      PROPERTIES ({props(t)})"
        for t in nodes)
    edge_sql = ",\n".join(
        f"    {fq(t)}\n      KEY ({', '.join(specs[t]['key'])})\n"
        f"      SOURCE KEY ({', '.join(specs[t]['src']['key'])}) REFERENCES {fq(specs[t]['src']['ref'])} ({', '.join(specs[t]['src']['ref_key'])})\n"
        f"      DESTINATION KEY ({', '.join(specs[t]['dst']['key'])}) REFERENCES {fq(specs[t]['dst']['ref'])} ({', '.join(specs[t]['dst']['ref_key'])})\n"
        f"      LABEL {specs[t]['label']}\n      PROPERTIES ({props(t)})"
        for t in edges)
    return (f"CREATE OR REPLACE PROPERTY GRAPH {fq(graph_name)}\n  NODE TABLES (\n{node_sql}\n  )\n"
            f"  EDGE TABLES (\n{edge_sql}\n  )")


# ---------------------------------------------------------------------------------------------------- UI catalog
def catalog(lang: str = "ko") -> Dict[str, Any]:
    lang = _lang(lang)
    specs = table_specs()
    tables = []
    for name, t in specs["tables"].items():
        cols = visible_columns(name, lang)
        rows = table_rows(name)
        tables.append({
            "name": name, "group": t["group"], "group_label": specs["groups"][t["group"]][lang],
            "path": specs["groups"][t["group"]]["path"], "kind": t["kind"], "label": t["label"],
            "description": t[f"description_{lang}"], "row_count": len(rows), "key": t["key"],
            "columns": [{"name": c["name"], "type": c["type"], "description": c[lang]} for c in t["columns"]],
            "visible_columns": cols, "sample": [{k: r.get(k) for k in cols} for r in rows[:8]],
            "recipes": [r for r, groups in TABLE_GROUPS_BY_RECIPE.items() if t["group"] in groups],
        })
    return {
        "lang": lang,
        "docs": [{"doc_id": d["doc_id"], "file": d["file"], "title": d["title"], "chars": d["chars"], "text": d["text"],
                  "chunks": [{"chunk_id": c["chunk_id"], "title": c["title"], "article_no": c["article_no"]} for c in d["chunks"]]}
                 for d in docs(lang)],
        "wiki": [{k: p[k] for k in ("page", "title", "layer", "chars", "text", "recipes")} for p in wiki(lang)],
        "tables": tables,
        "cqs": cqs(lang),
        "boundary": boundary(lang),
        "glossary": glossary(lang),
        "workflows": workflows(lang),
        "policy": policy_constants(lang=lang),
    }
