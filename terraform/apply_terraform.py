#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
apply_terraform.py
Executes the declarative Terraform IaC in `agentic-ontology-starter/terraform/`:
- If local `terraform` binary is available, executes `terraform init / validate / plan / apply` locally.
- Otherwise (e.g., corporate gMac with Santa Lockdown), packages `terraform/*.tf` to GCS and runs
  official `hashicorp/terraform:1.8.5` via Google Cloud Build in `seanjung-poc`.
Options (environment): TF_PLAN_ONLY=1 stops after `terraform plan` (review before apply);
TF_WORKSPACE_NAME=<name> selects or creates a separate state workspace (e.g. a test dataset);
TF_VAR_* and TF_CLI_ARGS_* (e.g. TF_CLI_ARGS_plan="-target=...") are passed to Terraform.
"""

import io
import json
import os
import shutil
import ssl
import subprocess
import sys
import tarfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

TF_DIR = Path(__file__).resolve().parent
PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "seanjung-poc")
REGION = os.environ.get("GCP_REGION", "asia-northeast3")
BUILD_BUCKET = f"{PROJECT_ID}_cloudbuild"
SOURCE_OBJECT = "source/agentic_ontology_starter_terraform.tgz"
CTX = ssl._create_unverified_context()
PLAN_ONLY = os.environ.get("TF_PLAN_ONLY") == "1"
WORKSPACE = os.environ.get("TF_WORKSPACE_NAME", "")


def get_token() -> str:
    for cmd in [
        ["gcloud", "auth", "print-access-token", "admin@seanjung.altostrat.com"],
        ["gcloud", "auth", "print-access-token"],
    ]:
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            if r.returncode == 0 and r.stdout.strip().startswith("ya29."):
                return r.stdout.strip()
        except Exception:
            pass
    raise RuntimeError("Could not obtain GCP access token via gcloud.")


def api_request(method: str, url: str, token: str, data: bytes = None, content_type: str = "application/json") -> dict:
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": content_type,
        },
    )
    try:
        with urllib.request.urlopen(req, context=CTX, timeout=60) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code} on {method} {url}: {err}")


def run_via_cloud_build(token: str) -> dict:
    print(f"[Terraform IaC] Packaging {TF_DIR} (.tf files) -> gs://{BUILD_BUCKET}/{SOURCE_OBJECT} ...")
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for f in sorted(TF_DIR.glob("*.tf")):
            tar.add(f, arcname=f.name)
    tgz_bytes = buf.getvalue()

    upload_url = (
        f"https://storage.googleapis.com/upload/storage/v1/b/{BUILD_BUCKET}/o"
        f"?uploadType=media&name={urllib.parse.quote(SOURCE_OBJECT, safe='')}"
    )
    api_request("POST", upload_url, token, data=tgz_bytes, content_type="application/gzip")
    print(f"[Terraform IaC] Uploaded {len(tgz_bytes)} bytes to gs://{BUILD_BUCKET}/{SOURCE_OBJECT}")

    build_Spec = {
        "source": {
            "storageSource": {
                "bucket": BUILD_BUCKET,
                "object": SOURCE_OBJECT,
            }
        },
        "steps": [
            {
                "name": "hashicorp/terraform:1.8.5",
                "entrypoint": "sh",
                "env": [f"GOOGLE_OAUTH_ACCESS_TOKEN={token}"] + [f"{k}={v}" for k, v in sorted(os.environ.items())
                                                                  if k.startswith(("TF_VAR_", "TF_CLI_ARGS"))],
                "args": [
                    "-c",
                    (
                        "set -e\n"
                        "terraform version\n"
                        "terraform init -input=false\n"
                        + (f"terraform workspace select -or-create=true {WORKSPACE}\n" if WORKSPACE else "")
                        + "terraform validate\n"
                        "terraform plan -out=tfplan -input=false\n"
                        + ("" if PLAN_ONLY else
                           "terraform apply -input=false -auto-approve tfplan\n"
                           "terraform output -json > /workspace/terraform_outputs.json\n"
                           "cat /workspace/terraform_outputs.json\n")
                    ),
                ],
            }
        ],
        "serviceAccount": f"projects/{PROJECT_ID}/serviceAccounts/924723860007-compute@developer.gserviceaccount.com",
        "options": {
            "logging": "GCS_ONLY",
        },
        "logsBucket": f"gs://{BUILD_BUCKET}/logs",
    }

    trigger_url = f"https://cloudbuild.googleapis.com/v1/projects/{PROJECT_ID}/builds"
    op = api_request("POST", trigger_url, token, data=json.dumps(build_Spec).encode("utf-8"))
    build_id = op["metadata"]["build"]["id"]
    print(f"[Terraform IaC] Triggered Cloud Build ID: {build_id} (hashicorp/terraform:1.8.5)")

    status_url = f"https://cloudbuild.googleapis.com/v1/projects/{PROJECT_ID}/builds/{build_id}"
    for i in range(200):  # up to 10 minutes (Cloud Run revision rollout included)
        time.sleep(3)
        b_info = api_request("GET", status_url, token)
        status = b_info.get("status", "UNKNOWN")
        print(f"  [Poll {i+1}] Cloud Build Status: {status}")
        if status in ("SUCCESS", "FAILURE", "INTERNAL_ERROR", "TIMEOUT", "CANCELLED"):
            # Fetch build log from GCS
            log_obj = f"logs/log-{build_id}.txt"
            log_url = f"https://storage.googleapis.com/storage/v1/b/{BUILD_BUCKET}/o/{urllib.parse.quote(log_obj, safe='')}?alt=media"
            try:
                req = urllib.request.Request(log_url, headers={"Authorization": f"Bearer {token}"})
                log_text = urllib.request.urlopen(req, context=CTX, timeout=15).read().decode("utf-8", errors="replace")
                print("\n=== HashiCorp Terraform Execution Log ===")
                print(log_text[-3500:])
                print("=========================================\n")
                # Save log locally for verification
                (TF_DIR / "last_terraform_apply.log").write_text(log_text, encoding="utf-8")
            except Exception as e:
                print(f"Could not fetch log: {e}")
            if status != "SUCCESS":
                raise RuntimeError(f"Terraform Cloud Build ended with status: {status}")
            return {"status": status, "build_id": build_id}
    raise RuntimeError("Timed out waiting for Terraform Cloud Build")


def main():
    token = get_token()
    tf_bin = shutil.which("terraform")
    if tf_bin:
        print(f"[Terraform IaC] Found local terraform binary: {tf_bin}")
        env = os.environ.copy()
        env["GOOGLE_OAUTH_ACCESS_TOKEN"] = token
        for cmd in [
            [tf_bin, "init", "-input=false"],
            *([[tf_bin, "workspace", "select", "-or-create=true", WORKSPACE]] if WORKSPACE else []),
            [tf_bin, "validate"],
            [tf_bin, "plan", "-input=false"] if PLAN_ONLY else [tf_bin, "apply", "-input=false", "-auto-approve"],
        ]:
            subprocess.run(cmd, cwd=str(TF_DIR), env=env, check=True)
    else:
        res = run_via_cloud_build(token)
        print(f"[Terraform IaC] Completed successfully via Cloud Build: {res}")


if __name__ == "__main__":
    main()
