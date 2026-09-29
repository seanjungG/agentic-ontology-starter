# Copyright (c) 2026 Sean Jung (seanjung@google.com). All Rights Reserved.
# Non-Commercial Use Only: Methodology & Docs under CC BY-NC-ND 4.0; Source Code under PolyForm Noncommercial License 1.0.0.
# Commercial use, paid consulting/SI/PoC delivery, or production deployment requires prior written permission from seanjung@google.com.

# -*- coding: utf-8 -*-
"""Generates (and optionally executes) the 12 canonical starter notebooks in `notebooks/ko/` and `notebooks/en/`."""
import argparse
import ast
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from nb_specs_s0_s2 import build_stage0, build_stage1, build_stage2
from nb_specs_s3_s5 import build_stage3, build_stage4, build_stage5
from validate_and_pack_notebooks import pack_and_validate_all

NB_DIR = Path(__file__).resolve().parent
SPECS = {
    "ko/stage0_overview_walkthrough_ko.ipynb": lambda: build_stage0("ko"),
    "ko/stage1_asset_and_cq_ko.ipynb": lambda: build_stage1("ko"),
    "ko/stage2_wiki_and_semantic_graph_ko.ipynb": lambda: build_stage2("ko"),
    "ko/stage3_property_graph_bigquery_spanner_ko.ipynb": lambda: build_stage3("ko"),
    "ko/stage4_agent_and_mcp_execution_ko.ipynb": lambda: build_stage4("ko"),
    "ko/stage5_lineage_and_evaluation_ko.ipynb": lambda: build_stage5("ko"),
    "en/stage0_overview_walkthrough_en.ipynb": lambda: build_stage0("en"),
    "en/stage1_asset_and_cq_en.ipynb": lambda: build_stage1("en"),
    "en/stage2_wiki_and_semantic_graph_en.ipynb": lambda: build_stage2("en"),
    "en/stage3_property_graph_bigquery_spanner_en.ipynb": lambda: build_stage3("en"),
    "en/stage4_agent_and_mcp_execution_en.ipynb": lambda: build_stage4("en"),
    "en/stage5_lineage_and_evaluation_en.ipynb": lambda: build_stage5("en"),
}


def _resolve_ht(src: str, lang: str) -> str:
    """Resolves H.t(ko_str, en_str) calls at notebook generation time so EN notebooks contain 0 Korean literals."""
    if src.lstrip().startswith("%%"):
        return src
    lines = src.splitlines(keepends=True)
    prefix = ""
    body = src
    if lines and lines[0].lstrip().startswith("%"):
        prefix = lines[0]
        body = "".join(lines[1:])
    try:
        tree = ast.parse(body)
    except SyntaxError:
        return src
    replacements = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name) and node.func.value.id == "H"
                and node.func.attr == "t" and len(node.args) == 2):
            chosen = node.args[0 if lang == "ko" else 1]
            seg = ast.get_source_segment(body, chosen)
            full_seg = ast.get_source_segment(body, node)
            if seg and full_seg:
                replacements.append((full_seg, seg))
    for old, new in replacements:
        body = body.replace(old, new)
    return prefix + body


def write_notebook(rel_path: str, cells: list) -> Path:
    lang = "en" if rel_path.startswith("en/") else "ko"
    for idx, c in enumerate(cells):
        c["id"] = f"cell-{idx:02d}"
        if c.get("cell_type") == "code" and isinstance(c.get("source"), str):
            c["source"] = _resolve_ht(c["source"], lang)
    nb = {
        "cells": cells,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3.13.0"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    out = NB_DIR / rel_path
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(nb, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return out


def execute_notebook(path: Path) -> str:
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
    rel = path.relative_to(NB_DIR)
    print(f"[EXEC] Running {rel} ...", flush=True)
    subprocess.run(cmd, cwd=str(NB_DIR), env=env, check=True)
    print(f"[DONE] Finished {rel}", flush=True)
    return str(rel)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true", help="Execute notebooks via nbconvert")
    parser.add_argument("--workers", type=int, default=2, help="Parallel workers for notebook execution")
    parser.add_argument("--only", nargs="*", help="Filter notebook relative paths")
    args = parser.parse_args()

    targets = [k for k in SPECS if not args.only or any(f in k for f in args.only)]
    paths = []
    for rel_path in targets:
        cells = SPECS[rel_path]()
        p = write_notebook(rel_path, cells)
        print(f"[WRITE] {rel_path} ({len(cells)} cells)", flush=True)
        paths.append(p)

    if args.execute:
        with ThreadPoolExecutor(max_workers=max(1, args.workers)) as ex:
            list(ex.map(execute_notebook, paths))

    pack_and_validate_all()


if __name__ == "__main__":
    main()
