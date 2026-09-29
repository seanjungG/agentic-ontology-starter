#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) 2026 Sean Jung (seanjung@google.com). All rights reserved.
# Licensed under CC BY-NC-ND 4.0 (Methodology & Slide Deck) & PolyForm Noncommercial 1.0.0 (Code).

"""
Uploads the generated 18-slide Google Workspace Slides (.pptx & .html) decks to:
1. Google Cloud Storage (`gs://seanjung-poc-starter-ontology/slides/{ko,en}/...`) via `src.gcp_client`.
2. Google Workspace Drive / Google Slides (`mimeType='application/vnd.google-apps.presentation'`)
   whenever Drive/Slides OAuth scopes are enabled on the active token.
"""

import json
import os
import sys
from pathlib import Path

import requests

THIS_DIR = Path(__file__).resolve().parent
STARTER_ROOT = THIS_DIR.parent
os.environ.setdefault("SSL_CERT_FILE", "/etc/ssl/cert.pem")
sys.path.insert(0, str(STARTER_ROOT))

from src.gcp_client import DEFAULT_GCS_BUCKET, get_gcp_token, upload_gcs_object


def sync_to_gcs() -> list:
    uploaded = []
    targets = [
        ("ko/agentic_ontology_methodology_training_ko.pptx", "slides/ko/agentic_ontology_methodology_training_ko.pptx"),
        ("en/agentic_ontology_methodology_training_en.pptx", "slides/en/agentic_ontology_methodology_training_en.pptx"),
        ("ko/agentic_ontology_methodology_slides_ko.html", "slides/ko/agentic_ontology_methodology_slides_ko.html"),
        ("en/agentic_ontology_methodology_slides_en.html", "slides/en/agentic_ontology_methodology_slides_en.html"),
    ]
    for local_rel, gcs_key in targets:
        local_path = THIS_DIR / local_rel
        if not local_path.exists():
            continue
        content_type = (
            "application/vnd.openxmlformats-officedocument.presentationml.presentation"
            if local_path.suffix == ".pptx"
            else "text/html; charset=utf-8"
        )
        res = upload_gcs_object(
            object_name=gcs_key,
            content_bytes=local_path.read_bytes(),
            bucket=DEFAULT_GCS_BUCKET,
            content_type=content_type,
        )
        uri = f"gs://{DEFAULT_GCS_BUCKET}/{gcs_key}"
        uploaded.append({"uri": uri, "size": int(res.get("size", local_path.stat().st_size))})
        print(f"[GCS OK] Uploaded {local_path.name} -> {uri} ({res.get('size')} bytes)")
    return uploaded


def try_convert_to_google_workspace_slides() -> dict:
    """
    Checks whether the active OAuth token includes Google Drive / Slides scopes.
    If present, converts the .pptx files into native cloud Google Slides documents
    (`application/vnd.google-apps.presentation`) via Google Drive API v3.
    """
    token = get_gcp_token()
    info = requests.get(
        f"https://www.googleapis.com/oauth2/v1/tokeninfo?access_token={token}",
        timeout=10,
    ).json()
    scopes = info.get("scope", "")

    if "drive" not in scopes and "presentations" not in scopes:
        print(
            "\n[INFO] Active token has cloud-platform scope (no Google Drive/Slides OAuth scope).\n"
            "  • Native Google Workspace Slides (.pptx) files are built locally and synced to GCS:\n"
            "    - slides/ko/agentic_ontology_methodology_training_ko.pptx\n"
            "    - slides/en/agentic_ontology_methodology_training_en.pptx\n"
            "  • To open in Google Workspace Slides: Drag & drop the .pptx file into https://drive.google.com or https://slides.new (File > Import slides).\n"
            "  • Or to auto-create cloud Google Slides via CLI, run:\n"
            "    gcloud auth login --scopes='https://www.googleapis.com/auth/cloud-platform,https://www.googleapis.com/auth/drive.file,https://www.googleapis.com/auth/presentations'\n"
            "    and re-run: .venv/bin/python slides/upload_to_google_slides.py"
        )
        return {"status": "LOCAL_AND_GCS_SYNCED", "cloud_presentations": []}

    created = []
    for lang, title, rel_path in [
        ("ko", "[KO] Agentic Ontology Starter — 5-Stage 방법론 교육용 슬라이드", "ko/agentic_ontology_methodology_training_ko.pptx"),
        ("en", "[EN] Agentic Ontology Starter — 5-Stage Methodology Training Slides", "en/agentic_ontology_methodology_training_en.pptx"),
    ]:
        file_path = THIS_DIR / rel_path
        metadata = {"name": title, "mimeType": "application/vnd.google-apps.presentation"}
        files = {
            "data": ("metadata", json.dumps(metadata), "application/json; charset=UTF-8"),
            "file": (
                file_path.name,
                file_path.read_bytes(),
                "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            ),
        }
        r = requests.post(
            "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart&fields=id,name,webViewLink",
            headers={
                "Authorization": f"Bearer {token}",
                "x-goog-user-project": "seanjung-poc",
            },
            files=files,
            timeout=60,
        )
        if r.status_code in (200, 201):
            res = r.json()
            fid = res.get("id")
            web_url = res.get("webViewLink") or f"https://docs.google.com/presentation/d/{fid}/edit"
            for share_email in ("seanjung@google.com", "admin@seanjung.altostrat.com"):
                try:
                    requests.post(
                        f"https://www.googleapis.com/drive/v3/files/{fid}/permissions",
                        headers={
                            "Authorization": f"Bearer {token}",
                            "Content-Type": "application/json",
                            "x-goog-user-project": "seanjung-poc",
                        },
                        json={"role": "writer", "type": "user", "emailAddress": share_email},
                        timeout=15,
                    )
                except Exception:
                    pass
            print(f"[GOOGLE SLIDES CREATED] {res.get('name')}: {web_url}")
            created.append({"lang": lang, "id": fid, "url": web_url})
        else:
            print(f"[WARN] Drive upload returned {r.status_code}: {r.text[:200]}")

    return {"status": "CLOUD_SLIDES_CREATED" if created else "LOCAL_AND_GCS_SYNCED", "cloud_presentations": created}


if __name__ == "__main__":
    gcs_uris = sync_to_gcs()
    ws_res = try_convert_to_google_workspace_slides()
    manifest_path = THIS_DIR / "slides_manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "deck_slide_count": 18,
                "aspect_ratio": "16:9 (13.333 in x 7.5 in)",
                "local_pptx": {
                    "ko": "slides/ko/agentic_ontology_methodology_training_ko.pptx",
                    "en": "slides/en/agentic_ontology_methodology_training_en.pptx",
                },
                "local_html_viewer": {
                    "ko": "slides/ko/agentic_ontology_methodology_slides_ko.html",
                    "en": "slides/en/agentic_ontology_methodology_slides_en.html",
                },
                "gcs_synced_objects": gcs_uris,
                "workspace_sync": ws_res,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(f"[OK] Wrote manifest: {manifest_path}")
