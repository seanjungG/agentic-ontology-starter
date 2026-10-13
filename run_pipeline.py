# -*- coding: utf-8 -*-
"""
Enterprise Agentic Ontology Starter (v2.2 · Resource-Connected Runner):
By default, connects directly to Ready-to-Use Google Cloud Ontology Resources
(BigQuery DW & Property Graph, GCS 3-Layer OKF Wiki, Business Workflows W1~W3, and 3 Domain Tools)
and verifies readiness across all 5 Stages without requiring manual MCP builder setup.

    python3 run_pipeline.py                      # Verify Ready-to-Use GCP Resources & Golden CQ 15/15
    python3 run_pipeline.py --project <id>       # Verify specific project's Ready-to-Use GCP Resources
    python3 run_pipeline.py --rebuild            # Optional: Rebuild/refresh local & GCP artifacts from raw inputs
"""
import argparse
import os
import sys

from src.project_context import get_project, load_override, resolve_track

NO_TABLES = """[STOP] track={track} needs customer tables, but project.json lists none ({reason}).
Choose one and tell the operator (the agent must not create tables):
  (a) Ask the customer for the table extracts, put them in data/input/03_tables/ and list them in project.json "tables".
  (b) Physical graph built from the documents: not implemented (separate request).
  (c) Synthetic demo data: only with explicit user approval, recorded in project.json "synthetic".
Or set "track": "auto" / "lite" to run the documents-only path."""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", help="project id (default: sample or env STARTER_PROJECT)")
    ap.add_argument(
        "--rebuild",
        action="store_true",
        help="Rebuild/re-ingest local & GCP ontology artifacts from raw inputs (default: connect & verify Ready-to-Use resources)",
    )
    args = ap.parse_args()
    p = get_project(args.project)
    track, tables, reason = resolve_track(p)
    if track != "lite" and not tables:
        sys.exit(NO_TABLES.format(track=track, reason=reason))
    gcp = p.get("gcp") or {}
    env = {
        "GCP_PROJECT_ID": gcp.get("project_id"),
        "BQ_DATASET_ID": gcp.get("dataset_id"),
        "GCS_WIKI_BUCKET": gcp.get("gcs_bucket"),
        "STARTER_PROJECT_ROOT": p["root"],
    }
    os.environ.update({k: v for k, v in env.items() if v})

    print("==================================================================")
    print(
        f" [Enterprise Agentic Ontology Starter v2.2 · Resource-Connected]"
        f" project={p['project_id']} · track={track} ({reason})"
    )
    print("==================================================================")

    if not args.rebuild:
        from src.resource_connector import OntologyResourceConnector

        connector = OntologyResourceConnector(
            project_id=gcp.get("project_id") or "seanjung-poc",
            dataset_id=gcp.get("dataset_id") or "starter_ontology_dw",
            gcs_bucket=gcp.get("gcs_bucket") or "seanjung-poc-starter-ontology",
            root_dir=p["root"],
        )
        manifest = connector.get_resource_manifest()
        rg = manifest["ready_to_use_gcp_resources"]
        print(f">>> Connected BigQuery DW       : {rg['bigquery_dw']['fq_dataset']}")
        print(f">>> Connected Property Graph    : {rg['bigquery_property_graph_detail']['fq_graph']}")
        print(f">>> Connected GCS 3-Layer Wiki  : {rg['gcs_okf_wiki']['uri']}")
        print(f">>> Domain Business Tools (3)   : {', '.join(t['tool_name'] for t in manifest['domain_business_tools'])}")
        print("\n>>> Verifying Ready-to-Use Resources across Stage 1 ~ Stage 5...")
        report = connector.verify_ready_resources()
        for stg, res in report["stages"].items():
            print(f"  - [{stg.upper()}] status={res.get('status')} | summary={res.get('summary')}")
        print("==================================================================")
        print(f" [RESOURCE CONNECTION VERIFIED] overall_status={report['status']} ({p['root']}/data/output/)")
        print("==================================================================")
        return

    from pipeline.ingest import run_ingest
    from pipeline.graph_builder import build_graph
    from pipeline.validator import run_validation

    run_ingest = load_override(p, "ingest_module", "run_ingest") or run_ingest
    build_graph = load_override(p, "graph_module", "build_graph") or build_graph
    run_validation = load_override(p, "validator_module", "run_validation") or run_validation

    from pipeline.extract_docs import extract_project
    from pipeline.ingest import build_chunks
    from pipeline.validator import run_gate0

    print(">>> Stage 1: Converting customer_doc/ originals to 01_guides (code only, no summary)...")
    if extract_project(p["root"], {"track": track, "track_reason": reason})["needs_ocr"]:
        sys.exit("[STOP] Pages without text (needs_ocr). See data/output/input_manifest.json.")
    print("\n>>> Gate 0: Chunks vs. original text...")
    if run_gate0(build_chunks()[1])["status"] != "PASS":
        sys.exit("[STOP] Gate 0 failed. See data/output/gate0_report.json. Nothing was loaded.")

    print("\n>>> Stage 1 & 2: Ingesting Unstructured Guides & Extracting Anchors...")
    run_ingest()

    if track == "lite":
        from pipeline.extract_wiki import extract_wiki

        print("\n>>> Stage 2: Document-based wiki (entities = nodes, concepts = edges; quotes checked against chunks)...")
        extract_wiki()
        print("\n>>> Stage 3: skipped (track=lite, no customer tables; the property graph needs tables)")
    else:
        print("\n>>> Stage 3: Synthesizing BigQuery SQL:2023 Property Graph DDL...")
        build_graph()

    print("\n>>> Stage 5: Live Golden CQ validation (Gate 1 CQ checks, then sql / citation scoring)...")
    run_validation()

    print("==================================================================")
    print(f" [PIPELINE COMPLETE] All artifacts verified in {p['root_dir']}/data/output/")
    print("==================================================================")


if __name__ == "__main__":
    main()
