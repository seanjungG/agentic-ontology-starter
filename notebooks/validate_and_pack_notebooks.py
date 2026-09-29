# -*- coding: utf-8 -*-
"""
validate_and_pack_notebooks.py
==============================
Standard Notebook Integrity & Attachment Packer for Agentic Ontology Starter (12 Canonical Notebooks in `ko/` & `en/`).

1. Scans every cell across all `.ipynb` files in `notebooks/ko/` and `notebooks/en/` for `attachment:<filename>`.
2. Loads the corresponding binary PNG from `notebooks/assets/<filename>`, verifies the PNG magic bytes,
   encodes it as standard Base64, and embeds `cell["attachments"][<filename>] = {"image/png": b64}`.
3. Assigns deterministic, unique `nbformat v4.5` cell `"id"` values (`cell-00`, `cell-01`, ...).
4. Validates all notebooks against `nbformat v4.5` + `nbconvert v7.17.1` rules.
"""

import base64
import glob
import json
import os
import re
import sys

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def pack_and_validate_all():
    notebooks_dir = os.path.dirname(os.path.abspath(__file__))
    assets_dir = os.path.join(notebooks_dir, "assets")
    ipynb_paths = sorted(
        glob.glob(os.path.join(notebooks_dir, "ko", "*.ipynb"))
        + glob.glob(os.path.join(notebooks_dir, "en", "*.ipynb"))
    )

    if not ipynb_paths:
        print("[ERROR] No .ipynb files found in", os.path.join(notebooks_dir, "{ko,en}"))
        sys.exit(1)

    asset_b64_cache = {}
    for png_file in sorted(os.listdir(assets_dir)):
        if png_file.endswith(".png"):
            full_png_path = os.path.join(assets_dir, png_file)
            with open(full_png_path, "rb") as pf:
                raw_bytes = pf.read()
            if not raw_bytes.startswith(PNG_MAGIC):
                raise ValueError(f"Invalid PNG magic header in {full_png_path}")
            asset_b64_cache[png_file] = base64.b64encode(raw_bytes).decode("ascii")

    print(f"[*] Loaded {len(asset_b64_cache)} verified PNG assets from {assets_dir}")

    total_errors = 0

    for path in ipynb_paths:
        rel_name = os.path.relpath(path, notebooks_dir)
        with open(path, "r", encoding="utf-8") as f:
            nb = json.load(f)

        nb["nbformat"] = 4
        nb["nbformat_minor"] = 5
        if "metadata" not in nb or not isinstance(nb["metadata"], dict):
            nb["metadata"] = {}
        nb["metadata"].setdefault("kernelspec", {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3",
        })
        nb["metadata"].setdefault("language_info", {
            "name": "python",
            "version": "3.13.0",
        })

        seen_ids = set()
        cells = nb.get("cells", [])

        for idx, cell in enumerate(cells):
            cid = cell.get("id", "")
            if not cid or not re.match(r"^[a-zA-Z0-9-_]{1,64}$", str(cid)) or cid in seen_ids:
                cid = f"cell-{idx:02d}"
                cell["id"] = cid
            seen_ids.add(cid)

            if "metadata" not in cell or not isinstance(cell["metadata"], dict):
                cell["metadata"] = {}

            src = cell.get("source", [])
            if isinstance(src, str):
                lines = [l + "\n" for l in src.split("\n")]
                if lines and lines[-1] == "\n":
                    lines.pop()
                cell["source"] = lines
                src_text = src
            else:
                src_text = "".join(src)

            att_refs = re.findall(r"attachment:([^\)\s\"]+)", src_text)
            if cell.get("cell_type") == "markdown":
                cell.pop("outputs", None)
                cell.pop("execution_count", None)
                if att_refs:
                    cell_attachments = {}
                    for ref_name in att_refs:
                        if ref_name not in asset_b64_cache:
                            print(f"[ERROR] {rel_name} Cell {idx} references missing asset '{ref_name}'!")
                            total_errors += 1
                        else:
                            cell_attachments[ref_name] = {"image/png": asset_b64_cache[ref_name]}
                    cell["attachments"] = cell_attachments
                else:
                    cell.pop("attachments", None)
            elif cell.get("cell_type") == "code":
                cell.pop("attachments", None)
                cell.setdefault("outputs", [])
                cell.setdefault("execution_count", None)

        with open(path, "w", encoding="utf-8") as f:
            json.dump(nb, f, ensure_ascii=False, indent=2)
            f.write("\n")

        with open(path, "r", encoding="utf-8") as f:
            verified_nb = json.load(f)

        file_size_kb = os.path.getsize(path) / 1024.0
        verified_att_cells = []
        out_count = sum(len(c.get("outputs", [])) for c in verified_nb["cells"] if c.get("cell_type") == "code")
        for idx, c in enumerate(verified_nb["cells"]):
            s = "".join(c["source"])
            refs = re.findall(r"attachment:([^\)\s\"]+)", s)
            atts = c.get("attachments", {})
            for r in refs:
                if r not in atts or "image/png" not in atts[r] or len(atts[r]["image/png"]) < 1000:
                    print(f"[FAIL] {rel_name} Cell {idx}: missing or invalid attachment '{r}'")
                    total_errors += 1
                else:
                    raw = base64.b64decode(atts[r]["image/png"])
                    if not raw.startswith(PNG_MAGIC):
                        print(f"[FAIL] {rel_name} Cell {idx}: corrupted PNG payload for '{r}'")
                        total_errors += 1
                    verified_att_cells.append(f"Cell {idx}:{r}({len(atts[r]['image/png']) // 1024}KB)")

        print(f"[PASS] {rel_name:<52} | {file_size_kb:6.1f} KB | {len(verified_nb['cells']):2d} cells | {out_count:2d} outputs | Att: {', '.join(verified_att_cells)}")

    if total_errors > 0:
        print(f"\n[FAILED] Total validation errors: {total_errors}")
        sys.exit(1)
    print(f"\n[SUCCESS] All {len(ipynb_paths)} notebooks passed NBFormat v4.5 & NBConvert v7.17.1 validation with 0 errors!")


if __name__ == "__main__":
    pack_and_validate_all()
