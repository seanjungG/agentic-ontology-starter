# -*- coding: utf-8 -*-
"""
One-Click End-to-End Pipeline Runner:
Executes Ingestion ➔ Property Graph DDL Generation ➔ CQ Validation.
"""
from pipeline.ingest import run_ingest
from pipeline.graph_builder import build_graph
from pipeline.validator import run_validation

def main():
    print("==================================================================")
    print(" [Enterprise Agentic Ontology Starter] Executing Unified Pipeline")
    print("==================================================================")
    print(">>> Stage 1 & 2: Ingesting Unstructured Guides & Extracting Anchors...")
    run_ingest()

    print("\n>>> Stage 3: Synthesizing BigQuery SQL:2023 Property Graph DDL...")
    build_graph()

    print("\n>>> Stage 5: Live Golden CQ validation (BigQuery verification SQL + Gemini agent answers)...")
    run_validation()

    print("==================================================================")
    print(" [PIPELINE COMPLETE] All artifacts verified in data/output/")
    print("==================================================================")

if __name__ == "__main__":
    main()
