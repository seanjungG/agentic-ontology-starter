# Copyright (c) 2026 Sean Jung (seanjung@google.com). All Rights Reserved.
# Non-Commercial Use Only: Methodology & Docs under CC BY-NC-ND 4.0; Source Code under PolyForm Noncommercial License 1.0.0.
# Commercial use, paid consulting/SI/PoC delivery, or production deployment requires prior written permission from seanjung@google.com.

# -*- coding: utf-8 -*-
"""
Pipeline Ingest Engine (Real GCP BigQuery & Cloud Storage Integration):
- Parses unstructured policy guides (`01_guides/*.md`) into SHA-256 anchored chunks (`doc_chunks.jsonl`)
- Compiles Andrej Karpathy 3-Layer LLM-Wiki (`summary.md`, `entities.md`, `concepts.md`, `rules.md`)
- Uploads `raw/`, `parsed/`, and `ontology/` artifacts to real GCS bucket `gs://seanjung-poc-starter-ontology`
- Loads the 10 Terraform-provisioned BigQuery tables from data/input/03_tables/*.csv (no values typed in code)
"""

import csv
import hashlib
import json
import os
import re
import sys
from datetime import datetime

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_ROOT = os.environ.get("STARTER_PROJECT_ROOT", BASE_DIR)  # project data root (run_pipeline.py --project)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from src.gcp_client import (
    DEFAULT_DATASET_ID,
    DEFAULT_GCS_BUCKET,
    DEFAULT_PROJECT_ID,
    execute_bq_sql,
    upload_gcs_object,
)


def _sql_str(val: str) -> str:
    if val is None:
        return "NULL"
    escaped = str(val).replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n").replace("\r", "")
    return f"'{escaped}'"


def _lit(v) -> str:
    if v is None:
        return "NULL"
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return repr(v)
    return _sql_str(v)


def _read_csv(rel_path: str):
    full = os.path.join(DATA_ROOT, rel_path)
    with open(full, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def run_ingest(
    guide_dir: str = "data/input/01_guides",
    output_dir: str = "data/output",
    wiki_dir: str = "data/llm_wiki",
    sync_gcp: bool = True,
):
    abs_guide_dir = os.path.join(DATA_ROOT, guide_dir)
    abs_output_dir = os.path.join(DATA_ROOT, output_dir)
    abs_wiki_dir = os.path.join(DATA_ROOT, wiki_dir)
    os.makedirs(abs_output_dir, exist_ok=True)
    os.makedirs(abs_wiki_dir, exist_ok=True)

    guide_files = []
    if os.path.isdir(abs_guide_dir):
        for fn in sorted(os.listdir(abs_guide_dir)):
            if fn.endswith(".md"):
                guide_files.append(os.path.join(abs_guide_dir, fn))
    elif os.path.isfile(abs_guide_dir):
        guide_files.append(abs_guide_dir)

    chunk_pattern = re.compile(
        r"<!--\s*(DOC_CHUNK_\d+):?\s*(.*?)\s*-->\s*(.*?)(?=(?:<!--\s*DOC_CHUNK_\d+)|$)",
        re.DOTALL,
    )
    chunks = []

    for gpath in guide_files:
        with open(gpath, "r", encoding="utf-8") as f:
            content = f.read()
        source_doc = os.path.basename(gpath)
        matches = chunk_pattern.findall(content)
        if not matches:
            sections = re.split(r"(?=\n##\s+)", content)
            for idx, sec in enumerate(sections):
                cid = f"DOC_CHUNK_{len(chunks)+1:03d}"
                title_match = re.search(r"##\s+(.*)", sec)
                title = title_match.group(1) if title_match else f"Section {idx+1}"
                h = hashlib.sha256(sec.encode("utf-8")).hexdigest()[:12]
                chunks.append(
                    {
                        "chunk_id": cid,
                        "title": title.strip(),
                        "source_doc": source_doc,
                        "hash_anchor": f"anchor_{h}",
                        "content": sec.strip(),
                    }
                )
        else:
            for cid, title, body in matches:
                h = hashlib.sha256(body.encode("utf-8")).hexdigest()[:12]
                chunks.append(
                    {
                        "chunk_id": cid,
                        "title": title.strip() or cid,
                        "source_doc": source_doc,
                        "hash_anchor": f"anchor_{h}",
                        "content": body.strip(),
                    }
                )

    chunks_path = os.path.join(abs_output_dir, "doc_chunks.jsonl")
    with open(chunks_path, "w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")

    ontology = {
        "@context": "https://cloud.google.com/ontology/v0.2/context.jsonld",
        "@graph": [
            {
                "@id": "domain:TelecomSubsidyManagement",
                "@type": "DomainOntology",
                "label": "Enterprise Subsidy & Contract Management (Starter v2.0)",
                "summary": "Hybrid ontology unifying structured BigQuery DW tables and unstructured policy manuals.",
                "totalChunks": len(chunks),
                "supportedTracks": ["lite", "standard", "full"],
                "supportedGraphEngines": ["bigquery", "spanner"],
            }
        ],
    }
    for c in chunks:
        ontology["@graph"].append(
            {
                "@id": f"chunk:{c['chunk_id']}",
                "@type": "DocChunk",
                "title": c["title"],
                "sourceDoc": c.get("source_doc", "sample_policy_guide.md"),
                "hashAnchor": c["hash_anchor"],
            }
        )

    onto_path = os.path.join(abs_output_dir, "ontology.jsonld")
    with open(onto_path, "w", encoding="utf-8") as f:
        json.dump(ontology, f, ensure_ascii=False, indent=2)

    # Structured sample tables (data/input/03_tables) -> rows for the 10 Terraform-provisioned tables (terraform/bigquery.tf)
    devices = _read_csv("data/input/03_tables/devices.csv")
    plans = _read_csv("data/input/03_tables/plans.csv")
    subsidies = _read_csv("data/input/03_tables/subsidies.csv")
    contracts = _read_csv("data/input/03_tables/customer_contracts.csv")
    rules = _read_csv("data/input/03_tables/domain_rules.csv")
    rule_edges = _read_csv("data/input/03_tables/rule_plan_edges.csv")
    total_subsidy = {s["policy_id"]: int(s["basic_subsidy"]) + int(s["distribution_subsidy"]) for s in subsidies}
    rule_cols = ("rule_id", "rule_name", "rule_category", "condition_expr", "formula_expr", "source_chunk_id", "description_ko")
    tables = {
        "tb_device_master": (
            ("device_id", "device_name", "manufacturer", "storage_gb", "factory_price_krw", "release_date"),
            [(d["device_id"], f"{d['pet_name']} {d['storage']}", d["manufacturer"], int(re.sub(r"\D", "", d["storage"])),
              int(d["factory_price"]), d["release_date"] or None) for d in devices]),
        "tb_plan_master": (
            ("plan_id", "plan_name", "tier_category", "monthly_fee_krw", "min_maintenance_days", "selective_discount_rate"),
            [(p["plan_id"], p["plan_name"], p["tier_category"], int(p["monthly_fee"]), int(p["min_maintenance_days"]),
              float(p["selective_discount_rate"])) for p in plans]),
        "tb_subsidy_policy": (
            ("policy_id", "device_id", "plan_id", "base_subsidy_krw", "additional_subsidy_cap_krw", "mandatory_retention_days", "effective_from"),
            [(s["policy_id"], s["device_id"], s["plan_id"], int(s["basic_subsidy"]), int(s["distribution_subsidy"]),
              int(s["mandatory_retention_days"]), s["effective_start_date"]) for s in subsidies]),
        "tb_customer_contract": (
            ("customer_id", "contract_id", "customer_segment", "age_group", "device_id", "plan_id", "contract_type",
             "commitment_months", "elapsed_days", "granted_subsidy_krw", "welfare_status", "status"),
            [(c["customer_id"], c["contract_id"], c["customer_segment"], c["age_group"], c["device_id"], c["plan_id"],
              c["contract_type"], int(c["commitment_months"]), int(c["elapsed_days"]),
              0 if c["contract_type"] == "SELECTIVE_25PCT" else total_subsidy.get(c["policy_id"]),
              c["welfare_status"], c["status"]) for c in contracts]),
        "tb_doc_chunks": (
            ("chunk_id", "source_file", "section_title", "content", "content_sha256", "trust_tier"),
            [(ch["chunk_id"], ch["source_doc"], ch["title"], ch["content"], ch["hash_anchor"], "GOLDEN_VERIFIED") for ch in chunks]),
        "tb_domain_rules": (rule_cols, [tuple(r[k] for k in rule_cols) for r in rules]),
        "edge_contract_device": (
            ("contract_id", "customer_id", "device_id", "edge_type"),
            [(c["contract_id"], c["customer_id"], c["device_id"], "USES_DEVICE") for c in contracts]),
        "edge_contract_plan": (
            ("contract_id", "customer_id", "plan_id", "edge_type"),
            [(c["contract_id"], c["customer_id"], c["plan_id"], "SUBSCRIBES_PLAN") for c in contracts]),
        "edge_subsidy_binding": (
            ("policy_id", "device_id", "plan_id", "total_subsidy_krw", "edge_type"),
            [(s["policy_id"], s["device_id"], s["plan_id"], total_subsidy[s["policy_id"]], "HAS_SUBSIDY_POLICY") for s in subsidies]),
        "edge_rule_applies_to_plan": (
            ("edge_id", "rule_id", "plan_id", "source_chunk_id", "relation_label_ko", "edge_type"),
            [(e["edge_id"], e["rule_id"], e["plan_id"], e["source_chunk_id"], e["relation_label_ko"], "APPLIES_TO_PLAN") for e in rule_edges]),
    }

    # 3-Layer LLM-Wiki generated from the same parsed chunks / CSV rows (no values typed in code)
    fq = f"{DEFAULT_PROJECT_ID}.{DEFAULT_DATASET_ID}"
    seg = lambda s: s.replace("_", " ")  # noqa: E731
    wiki = {
        "summary.md": (
            "# Enterprise Knowledge Wiki: Executive Summary (Layer 1)\n"
            "- **Domain**: Telecom Terminal Subsidy, Tariff Plans & Customer Commitment Management\n"
            f"- **Target Framework**: OKF v0.2 & Dual Property Graph (`{fq}.STARTER_ONTOLOGY_GRAPH`)\n"
            f"- **Total Parsed Chunks**: {len(chunks)} (Across {len(guide_files)} Policy Guides)\n"
            f"- **BigQuery Tables Loaded**: {len(tables)} tables in `{fq}` (schema: `terraform/bigquery.tf`)\n\n"
            "## Operational Philosophy\n"
            "Unstructured policy guides and structured BigQuery tables share one ontology. The agent answers with live "
            "BigQuery SQL/GQL results, SHA-256 paragraph anchors and Vertex AI Gemini, and cites the rule and chunk used.\n"),
        "entities.md": "\n".join(
            ["# Enterprise Knowledge Wiki: Core Entities Directory (Layer 2)",
             f"Generated from `data/input/03_tables/*.csv` (the rows loaded into `{fq}`).", "",
             "## 1. Customer Contract Ledger (`tb_customer_contract`)"]
            + [f"- `{c['contract_id']}` (`{c['customer_id']}` · {seg(c['customer_segment'])} · `{c['device_id']}` · `{c['plan_id']}` · "
               f"{c['elapsed_days']} Days Elapsed" + (f" · `{c['welfare_status']}`" if c["welfare_status"] != "NONE" else "")
               + (f" · `{c['contract_type']}`" if c["contract_type"] != "PUBLIC_SUBSIDY" else "") + ")" for c in contracts]
            + ["", "## 2. Terminal Device Master (`tb_device_master`)"]
            + [f"- `{d['pet_name']} {d['storage']}` (`{d['device_id']}`, Factory Price: {int(d['factory_price']):,} KRW)" for d in devices]
            + ["", "## 3. Tariff Plan Master (`tb_plan_master`)"]
            + [f"- `{p['plan_name']}` (`{p['plan_id']}`, {int(p['monthly_fee']):,} KRW, Minimum Maintenance: {p['min_maintenance_days']} Days)" for p in plans]
            + ["", "## 4. Subsidy Policy Master (`tb_subsidy_policy`)"]
            + [f"- `{s['policy_id']}` (`{s['device_id']}` + `{s['plan_id']}`: Basic {int(s['basic_subsidy']):,} + Dist "
               f"{int(s['distribution_subsidy']):,} = {total_subsidy[s['policy_id']]:,} KRW)" for s in subsidies]) + "\n",
        "concepts.md": (
            "# Enterprise Knowledge Wiki: Semantic Concepts & Edges (Layer 3)\n"
            "In the Agentic Ontology Studio graph model, **Entities are represented as Nodes** and **Semantic Concepts/Relationships are represented as Edges**:\n\n"
            "1. `USES_DEVICE` (`개통 단말기 관계`): Links a Customer Contract (`tb_customer_contract`) to its Terminal Device (`tb_device_master`).\n"
            "2. `SUBSCRIBES_PLAN` (`가입 요금제 관계`): Links a Customer Contract (`tb_customer_contract`) to its Tariff Plan (`tb_plan_master`).\n"
            "3. `HAS_SUBSIDY_POLICY` (`단말×요금제 지원금 결합`): Connects a Terminal Device (`tb_device_master`) to a Tariff Plan (`tb_plan_master`) with public and distribution subsidy amounts.\n"
            "4. `APPLIES_TO_PLAN` (`비즈니스 규칙 적용`): Binds a codified Domain Rule (`tb_domain_rules`) to Tariff Plans (`tb_plan_master`) with SHA-256 chunk grounding.\n"),
        "rules.md": "\n".join(
            ["# Enterprise Knowledge Wiki: Codified Business Rules (Layer 3)",
             "Generated from `data/input/03_tables/domain_rules.csv` (BigQuery `tb_domain_rules`).", ""]
            + [f"### `{r['rule_id']}` · {r['rule_name']} (`{r['source_chunk_id']}`)\n- **Condition**: `{r['condition_expr']}`\n"
               f"- **Formula**: `{r['formula_expr']}`\n- {r['description_ko']}\n" for r in rules]),
    }
    for fn, body in wiki.items():
        with open(os.path.join(abs_wiki_dir, fn), "w", encoding="utf-8") as f:
            f.write(body)

    uploaded_objects, bq_jobs = [], []
    if sync_gcp:
        # 1. raw/ guides, parsed/ chunks and ontology/ wiki -> GCS bucket (Terraform-provisioned)
        uploads = [(f"raw/{os.path.basename(g)}", g, "text/markdown; charset=utf-8") for g in guide_files]
        uploads += [("parsed/doc_chunks.jsonl", chunks_path, "application/json; charset=utf-8")]
        uploads += [(f"ontology/{fn}", os.path.join(abs_wiki_dir, fn), "text/markdown; charset=utf-8") for fn in wiki]
        uploads += [("ontology/ontology.jsonld", onto_path, "application/ld+json; charset=utf-8")]
        for obj, path, ctype in uploads:
            with open(path, "rb") as f:
                upload_gcs_object(obj, f.read(), bucket=DEFAULT_GCS_BUCKET, content_type=ctype)
            uploaded_objects.append(f"gs://{DEFAULT_GCS_BUCKET}/{obj}")

        # 2. TRUNCATE + INSERT each BigQuery table in one transaction (auto rollback on error); any failed job stops the pipeline
        for table, (cols, rows) in tables.items():
            res = execute_bq_sql(
                f"BEGIN TRANSACTION;\nTRUNCATE TABLE `{fq}.{table}`;\nINSERT INTO `{fq}.{table}` ({', '.join(cols)}) VALUES\n"
                + ",\n".join("(" + ", ".join(_lit(v) for v in r) + ")" for r in rows) + ";\nCOMMIT TRANSACTION;")
            bq_jobs.append({"table": table, "rows": len(rows), "job_id": res.get("job_id"), "status": res.get("status")})
            if res.get("status") != "SUCCESS":
                raise RuntimeError(f"BigQuery load failed ({table}): {str(res.get('error', ''))[:500]}")

    gcs_manifest = {
        "gcs_uri": f"gs://{DEFAULT_GCS_BUCKET}/",
        "bigquery_dataset": fq,
        "status": "LIVE_GCP_SYNCED" if sync_gcp else "LOCAL_ONLY",
        "uploaded_gcs_objects": uploaded_objects,
        "bigquery_load_jobs": bq_jobs,
        "sync_timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
        "validation": {
            "chunk_count": len(chunks),
            "guide_count": len(guide_files),
            "bigquery_tables_loaded": sum(j["status"] == "SUCCESS" for j in bq_jobs),
        },
    }
    with open(os.path.join(abs_wiki_dir, "gcs_prototype_manifest.json"), "w", encoding="utf-8") as f:
        json.dump(gcs_manifest, f, ensure_ascii=False, indent=2)

    print(
        f"[INGEST SUCCESS] Processed {len(chunks)} chunks across {len(guide_files)} guides | "
        f"GCS Uploaded: {len(uploaded_objects)} objects | BigQuery Loaded: {len(bq_jobs)} tables"
    )
    return chunks


if __name__ == "__main__":
    run_ingest()
