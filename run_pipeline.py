# -*- coding: utf-8 -*-
"""
One-Click End-to-End Pipeline Runner:
Executes original-text extraction ➔ Gate 0 ➔ Ingestion ➔ Property Graph DDL Generation ➔ CQ Validation.

    python3 run_pipeline.py                      # bundled sample (repository root)
    python3 run_pipeline.py --project <id>       # projects/<id>/ data + that project's GCP dataset/bucket
"""
import argparse
import os
import sys

from src.project_context import get_project, load_override


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", help="project id (default: sample or env STARTER_PROJECT)")
    p = get_project(ap.parse_args().project)
    gcp = p.get("gcp") or {}
    env = {"GCP_PROJECT_ID": gcp.get("project_id"), "BQ_DATASET_ID": gcp.get("dataset_id"),
           "GCS_WIKI_BUCKET": gcp.get("gcs_bucket"), "STARTER_PROJECT_ROOT": p["root"]}
    os.environ.update({k: v for k, v in env.items() if v})  # read by src/gcp_client.py and pipeline/* on import

    from pipeline.ingest import run_ingest
    from pipeline.graph_builder import build_graph
    from pipeline.validator import run_validation
    # Projects whose schema differs from the sample point project.json at their own modules (same function names).
    run_ingest = load_override(p, "ingest_module", "run_ingest") or run_ingest
    build_graph = load_override(p, "graph_module", "build_graph") or build_graph
    run_validation = load_override(p, "validator_module", "run_validation") or run_validation

    print("==================================================================")
    print(f" [Enterprise Agentic Ontology Starter] Executing Unified Pipeline · project={p['project_id']}")
    print("==================================================================")
    from pipeline.extract_docs import extract_project
    from pipeline.ingest import build_chunks
    from pipeline.validator import run_gate0
    print(">>> Stage 1: Converting customer_doc/ originals to 01_guides (code only, no summary)...")
    if extract_project(p["root"])["needs_ocr"]:
        sys.exit("[STOP] Pages without text (needs_ocr). See data/output/input_manifest.json.")
    print("\n>>> Gate 0: Chunks vs. original text...")
    if run_gate0(build_chunks()[1])["status"] != "PASS":
        sys.exit("[STOP] Gate 0 failed. See data/output/gate0_report.json. Nothing was loaded.")

    print("\n>>> Stage 1 & 2: Ingesting Unstructured Guides & Extracting Anchors...")
    run_ingest()

    print("\n>>> Stage 3: Synthesizing BigQuery SQL:2023 Property Graph DDL...")
    build_graph()

    print("\n>>> Stage 5: Live Golden CQ validation (BigQuery verification SQL + Gemini agent answers)...")
    run_validation()

    print("==================================================================")
    print(f" [PIPELINE COMPLETE] All artifacts verified in {p['root_dir']}/data/output/")
    print("==================================================================")

if __name__ == "__main__":
    main()
