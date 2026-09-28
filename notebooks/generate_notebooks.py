# -*- coding: utf-8 -*-
"""Generates (and optionally executes) the 11 canonical starter notebooks (`stage0`..`stage5`, KO/EN)."""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from nb_specs_s0_s2 import build_stage0, build_stage1, build_stage2
from nb_specs_s3_s5 import build_stage3, build_stage4, build_stage5
from validate_and_pack_notebooks import pack_and_validate_all

NB_DIR = Path(__file__).resolve().parent
SPECS = {
    "stage0_overview_walkthrough.ipynb": build_stage0,
    "stage1_asset_and_cq_ko.ipynb": lambda: build_stage1("ko"),
    "stage1_asset_and_cq_en.ipynb": lambda: build_stage1("en"),
    "stage2_wiki_and_semantic_graph_ko.ipynb": lambda: build_stage2("ko"),
    "stage2_wiki_and_semantic_graph_en.ipynb": lambda: build_stage2("en"),
    "stage3_property_graph_bigquery_spanner_ko.ipynb": lambda: build_stage3("ko"),
    "stage3_property_graph_bigquery_spanner_en.ipynb": lambda: build_stage3("en"),
    "stage4_agent_and_mcp_execution_ko.ipynb": lambda: build_stage4("ko"),
    "stage4_agent_and_mcp_execution_en.ipynb": lambda: build_stage4("en"),
    "stage5_lineage_and_evaluation_ko.ipynb": lambda: build_stage5("ko"),
    "stage5_lineage_and_evaluation_en.ipynb": lambda: build_stage5("en"),
}


def write_notebook(filename: str, cells: list) -> Path:
    for idx, c in enumerate(cells):
        c["id"] = f"cell-{idx:02d}"
    nb = {
        "cells": cells,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3.13.0"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    out = NB_DIR / filename
    with open(out, "w", encoding="utf-8") as f:
        json.dump(nb, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return out


def execute_notebook(path: Path) -> None:
    env = os.environ.copy()
    if Path("/etc/ssl/cert.pem").exists():
        env.setdefault("SSL_CERT_FILE", "/etc/ssl/cert.pem")
    cmd = [
        sys.executable,
        "-m",
        "jupyter",
        "nbconvert",
        "--to",
        "notebook",
        "--execute",
        "--inplace",
        "--ExecutePreprocessor.timeout=600",
        "--ExecutePreprocessor.kernel_name=python3",
        str(path),
    ]
    print(f"[EXEC] Running {path.name} ...")
    subprocess.run(cmd, cwd=str(NB_DIR), env=env, check=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true", help="Execute notebooks via nbconvert")
    parser.add_argument("--only", nargs="*", help="Filter notebook filenames")
    args = parser.parse_args()

    targets = [k for k in SPECS if not args.only or any(f in k for f in args.only)]
    for fname in targets:
        p = write_notebook(fname, SPECS[fname]())
        print(f"[WRITE] {p.name} ({len(SPECS[fname]())} cells)")
        if args.execute:
            execute_notebook(p)

    pack_and_validate_all()


if __name__ == "__main__":
    main()
