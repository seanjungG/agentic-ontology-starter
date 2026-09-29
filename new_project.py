# Copyright (c) 2026 Sean Jung (seanjung@google.com). All Rights Reserved.
# Non-Commercial Use Only: Methodology & Docs under CC BY-NC-ND 4.0; Source Code under PolyForm Noncommercial License 1.0.0.
# Commercial use, paid consulting/SI/PoC delivery, or production deployment requires prior written permission from seanjung@google.com.

# -*- coding: utf-8 -*-
"""
Creates a customer / data-domain project from projects/_template/.

    python3 new_project.py acme-claims --name "Acme Claims" --customer "Acme" --domain "Claims review"

The studio lists it in the top PROJECT selector (folder scan); open /?project=acme-claims.
"""
import argparse
import json
import os
import re
import shutil
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
from src.gcp_client import DEFAULT_PROJECT_ID  # noqa: E402
from src.project_context import list_projects  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description="Create projects/<id>/ from projects/_template/")
    ap.add_argument("project_id", help="lowercase letters, digits and hyphens, e.g. acme-claims")
    ap.add_argument("--name", required=True)
    ap.add_argument("--customer", default="")
    ap.add_argument("--domain", default="")
    ap.add_argument("--gcp-project", default=DEFAULT_PROJECT_ID)
    ap.add_argument("--dataset", help="BigQuery dataset (default: <id>_dw with underscores)")
    ap.add_argument("--bucket", help="GCS bucket (default: <gcp-project>-<id>)")
    ap.add_argument("--track", default="auto", choices=["auto", "lite", "standard", "full"])
    ap.add_argument("--engine", default="bigquery", choices=["bigquery", "spanner"])
    a = ap.parse_args()

    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,62}", a.project_id):
        sys.exit("project_id must use lowercase letters, digits and hyphens (2-63 chars).")
    dst = os.path.join(BASE_DIR, "projects", a.project_id)
    if os.path.exists(dst) or a.project_id in {p["project_id"] for p in list_projects()}:
        sys.exit(f"Project already exists: {a.project_id}")

    shutil.copytree(os.path.join(BASE_DIR, "projects/_template"), dst)
    for name in ("portal_profile.json", "eval_rubric.json"):
        shutil.copy(os.path.join(BASE_DIR, "config", name), os.path.join(dst, "config", name))
    meta_path = os.path.join(dst, "project.json")
    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)
    meta.update(project_id=a.project_id, project_name=a.name, customer_org=a.customer, domain=a.domain,
                track=a.track, graph_engine=a.engine,
                gcp={"project_id": a.gcp_project,
                     "dataset_id": a.dataset or a.project_id.replace("-", "_") + "_dw",
                     "gcs_bucket": a.bucket or f"{a.gcp_project}-{a.project_id}"})
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"Created projects/{a.project_id}/ (dataset {meta['gcp']['dataset_id']}, bucket {meta['gcp']['gcs_bucket']}).")
    print(f"Studio: http://127.0.0.1:8080/?project={a.project_id}  |  Pipeline: python3 run_pipeline.py --project {a.project_id}")


if __name__ == "__main__":
    main()
