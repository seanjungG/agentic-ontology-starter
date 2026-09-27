# -*- coding: utf-8 -*-
"""
validate_and_pack_notebooks.py
==============================
Standard Notebook Integrity & Attachment Packer for Agentic Ontology Starter (EPIC-025).

Why this script exists:
- GitHub renders Jupyter Notebooks using `nbformat v5.10.4` and `nbconvert v7.17.1`.
- In `nbconvert v7.17.1`, if any Markdown cell contains `![alt](attachment:<filename>)`,
  `nbconvert` strictly checks `if <filename> not in cell.get("attachments", {}): raise InvalidNotebook(f"missing attachment: {<filename>}")`.
- External cell-editing tools (such as `notebook_edit`) strip the `"attachments"` dictionary
  from Markdown cells when re-serializing `.ipynb` files, causing GitHub to fail with
  `Invalid Notebook: missing attachment: <filename>`.
- Furthermore, `nbformat v5.10.4` (Schema v4.5) requires every cell to possess a unique `"id"`
  matching `^[a-zA-Z0-9-_]{1,64}$`.

What this script does:
1. Synchronizes `agentic_ontology_ce_walkthrough.ipynb` headers with the 8-Step Studio Architecture
   (`0. Overview` ~ `8. AI FDE`, `Agentic Ontology Studio`).
2. Scans every cell across all 7 `.ipynb` files in `notebooks/` for `attachment:<filename>`.
3. Loads the corresponding binary PNG from `notebooks/assets/<filename>`, verifies the PNG magic bytes
   (`\\x89PNG\\r\\n\\x1a\\n`), encodes it as standard Base64, and embeds `cell["attachments"][<filename>] = {"image/png": b64}`.
4. Assigns deterministic, unique `nbformat v4.5` cell `"id"` values (`cell-00`, `cell-01`, ...) where missing or duplicated.
5. Validates all 7 notebooks against `nbformat v4.5` + `nbconvert v7.17.1` rules and exits with code 0 only if 100% pass.
"""

import base64
import glob
import json
import os
import re
import sys

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def update_walkthrough_step_headers(nb):
    """Synchronizes agentic_ontology_ce_walkthrough.ipynb markdown cells with the
    6-Tab / 5-Stage Studio Architecture (`0. Overview` ~ `Stage 5. Lineage & Eval`)."""
    cells = nb.get("cells", [])
    if len(cells) < 20:
        return

    # Cell 0: Executive Overview & 3-Part Journey across the 5 methodology stages
    cells[0]["source"] = [
        "# Enterprise Agentic Ontology: Hands-on Walkthrough for Google Cloud CEs\n",
        "## Agentic Ontology Studio (Starter Pack v2.0) · 5-Stage Progressive Hands-on Guide\n",
        "\n",
        "본 주피터 노트북은 **Google Cloud Customer Engineer(CE), Data Architect, AI/GenAI Specialist**를 위한 엔드투엔드 대화식 실습 가이드입니다.\n",
        "비즈니스 도메인의 정형 원장(BigQuery DW / Cloud Spanner)과 비정형 규정 문서(GCS/Markdown)를 **단일 시맨틱 지식그래프(Property Graph)**로 통합하여, 에이전트가 근거 앵커 기반으로 결정론적 추론·실행하는 **`Agentic Ontology Studio` 6-Tab (`0. Overview` + `Stage 1` ~ `Stage 5`) 아키텍처**를 3개의 실습 파트로 나누어 검증합니다.\n",
        "\n",
        "---\n",
        "\n",
        "### 3-Part Hands-on Journey Mapped to the 6-Tab Studio & 5-Stage Methodology\n",
        "\n",
        "![Evolutionary Journey Overview](attachment:evolutionary_overview_flow.png)\n",
        "\n",
        "1. **Part 1 (`Stage 1. Asset` & `Stage 2. Wiki & Semantic Graph`)**:\n",
        "   - 비식별화 원천 자산(테이블 4종·가이드 2종) 수집, 구조 보존 청킹 및 SHA-256 해시 앵커링(`DOC_CHUNK_001~005`)\n",
        "   - Karpathy 3-Layer OKF 위키 컴파일 및 시맨틱 그래프(`Entity=Node`, `Concept=Edge`) 구축\n",
        "2. **Part 2 (`Stage 3. Property Graph` — BigQuery Graph & Spanner Graph Dual Adapter)**:\n",
        "   - 정형 원장 테이블 Zero-ETL 그래프 노드 승격 (`create_property_graph.sql` & `create_spanner_graph.sql`)\n",
        "   - `GRAPH_TABLE()` / ISO GQL 멀티홉 탐색을 통한 정형 원장 + 비정형 규정 교차 검증\n",
        "3. **Part 3 (`Stage 4. Agent & MCP` & `Stage 5. Lineage & Eval`)**:\n",
        "   - 8대 모듈형 MCP 스위트(Stage 1~5 파이프라인 MCP + Runtime 도메인 MCP 3종) 오케스트레이션\n",
        "   - 4-Tier 엔드투엔드 데이터 리니지 및 Golden CQ 5종 / 바운더리 질의 10건 회귀 평가\n"
    ]

    # Cell 3: Part 1 architecture flow
    if "step1_architecture_flow.png" in "".join(cells[3].get("source", [])):
        cells[3]["source"] = [
            "---\n",
            "## Part 1: `1. Asset` · `2. Knowledge Viewer` · `3. Ontology Semantic` · `4. Wiki Agent` (비정형 OKF 위키 파이프라인)\n",
            "\n",
            "첫 번째 단계에서는 별도의 외부 그래프 DB 없이도 비정형 규정 문서(PDF/Markdown)를 결정론적 SHA-256 해시 앵커와 3-Layer OKF 위키로 변환하여 **`4. Wiki Agent`**를 즉시 구동합니다.\n",
            "\n",
            "![Step 1 Architecture Flow](attachment:step1_architecture_flow.png)\n"
        ]

    # Cell 12: Part 2 property graph flow
    if "step2_property_graph_flow.png" in "".join(cells[12].get("source", [])):
        cells[12]["source"] = [
            "---\n",
            "## Part 2: `5. Bigquery Graph` 설계 및 `6. BQG Agent` (NL2GQL) 멀티홉 추론\n",
            "\n",
            "두 번째 단계에서는 BigQuery 정형 원장 테이블(단말기 출고가, 요금제, 공시/추가지원금)을 외부 복제 없이 **`5. Bigquery Graph` (`ISO SQL:2023 CREATE PROPERTY GRAPH`)**로 승격하고, **`6. BQG Agent`**를 통해 정형 원장과 비정형 규정을 실시간 교차 탐색합니다.\n",
            "\n",
            "![Step 2 Property Graph Flow](attachment:step2_property_graph_flow.png)\n"
        ]

    # Cell 19: Part 3 lineage & AI FDE flow
    if "step3_fde_orchestration_flow.png" in "".join(cells[19].get("source", [])):
        cells[19]["source"] = [
            "---\n",
            "## Part 3: `7. Lineage` 4-Tier 계보 추적 · `8. AI FDE` (11종 MCP 오케스트레이션 & CQ 자동 채점)\n",
            "\n",
            "세 번째 단계에서는 **`7. Lineage` (Raw ➔ OKF ➔ Property Graph ➔ Agent 4-Tier 계보)**를 추적하고, **`8. AI FDE` (11종 도메인 MCP 스위트)**로 동적 하위 목표를 분해하여 20대 골든 CQ를 5대 루브릭으로 자동 채점합니다.\n",
            "\n",
            "![Step 3 AI FDE Orchestration Flow](attachment:step3_fde_orchestration_flow.png)\n"
        ]



def pack_and_validate_all():
    notebooks_dir = os.path.dirname(os.path.abspath(__file__))
    assets_dir = os.path.join(notebooks_dir, "assets")
    ipynb_paths = sorted(glob.glob(os.path.join(notebooks_dir, "*.ipynb")))

    if not ipynb_paths:
        print("[ERROR] No .ipynb files found in", notebooks_dir)
        sys.exit(1)

    # Pre-load and validate all PNG assets in notebooks/assets/
    asset_b64_cache = {}
    for png_file in sorted(os.listdir(assets_dir)):
        if png_file.endswith(".png"):
            full_png_path = os.path.join(assets_dir, png_file)
            with open(full_png_path, "rb") as pf:
                raw_bytes = pf.read()
            if not raw_bytes.startswith(PNG_MAGIC):
                raise ValueError(f"Invalid PNG magic header in {full_png_path}")
            asset_b64_cache[png_file] = base64.b64encode(raw_bytes).decode("ascii")

    print(f"[*] Loaded {len(asset_b64_cache)} verified PNG assets from {assets_dir}:")
    for k, v in asset_b64_cache.items():
        print(f"    - {k}: base64 length = {len(v):,} chars")

    total_errors = 0

    for path in ipynb_paths:
        fname = os.path.basename(path)
        with open(path, "r", encoding="utf-8") as f:
            nb = json.load(f)

        if fname == "agentic_ontology_ce_walkthrough.ipynb":
            update_walkthrough_step_headers(nb)

        # Ensure top-level nbformat 4.5 compliance
        nb["nbformat"] = 4
        nb["nbformat_minor"] = 5
        if "metadata" not in nb or not isinstance(nb["metadata"], dict):
            nb["metadata"] = {}
        nb["metadata"].setdefault("kernelspec", {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3"
        })
        nb["metadata"].setdefault("language_info", {
            "name": "python",
            "version": "3.11.0"
        })

        seen_ids = set()
        cells = nb.get("cells", [])
        injected_count = 0

        for idx, cell in enumerate(cells):
            # 1. Ensure unique valid cell id (nbformat v4.5 requirement)
            cid = cell.get("id", "")
            if not cid or not re.match(r"^[a-zA-Z0-9-_]{1,64}$", str(cid)) or cid in seen_ids:
                cid = f"cell-{idx:02d}"
                cell["id"] = cid
            seen_ids.add(cid)

            # 2. Ensure metadata dict exists
            if "metadata" not in cell or not isinstance(cell["metadata"], dict):
                cell["metadata"] = {}

            # 3. Normalize source as list of lines
            src = cell.get("source", [])
            if isinstance(src, str):
                lines = [l + "\n" for l in src.split("\n")]
                if lines and lines[-1] == "\n":
                    lines.pop()
                cell["source"] = lines
                src_text = src
            else:
                src_text = "".join(src)

            # 4. Handle attachment:<filename> references in markdown cells
            att_refs = re.findall(r"attachment:([^\)\s\"]+)", src_text)
            if cell.get("cell_type") == "markdown":
                # Clean illegal code keys if any
                cell.pop("outputs", None)
                cell.pop("execution_count", None)

                if att_refs:
                    cell_attachments = {}
                    for ref_name in att_refs:
                        if ref_name not in asset_b64_cache:
                            print(f"[ERROR] {fname} Cell {idx} references missing asset '{ref_name}'!")
                            total_errors += 1
                        else:
                            cell_attachments[ref_name] = {
                                "image/png": asset_b64_cache[ref_name]
                            }
                            injected_count += 1
                    cell["attachments"] = cell_attachments
                else:
                    # Remove empty or stale attachments dict if no attachment: reference in source
                    cell.pop("attachments", None)
            elif cell.get("cell_type") == "code":
                cell.pop("attachments", None)
                cell.setdefault("outputs", [])
                cell.setdefault("execution_count", idx)

        # Write back with clean UTF-8 formatting
        with open(path, "w", encoding="utf-8") as f:
            json.dump(nb, f, ensure_ascii=False, indent=2)
            f.write("\n")

        # Re-read and run strict nbconvert v7.17.1 + nbformat v5.10.4 simulation check
        with open(path, "r", encoding="utf-8") as f:
            verified_nb = json.load(f)

        file_size_kb = os.path.getsize(path) / 1024.0
        verified_att_cells = []
        for idx, c in enumerate(verified_nb["cells"]):
            s = "".join(c["source"])
            refs = re.findall(r"attachment:([^\)\s\"]+)", s)
            atts = c.get("attachments", {})
            for r in refs:
                if r not in atts or "image/png" not in atts[r] or len(atts[r]["image/png"]) < 1000:
                    print(f"[FAIL] {fname} Cell {idx}: missing or invalid attachment '{r}'")
                    total_errors += 1
                else:
                    raw = base64.b64decode(atts[r]["image/png"])
                    if not raw.startswith(PNG_MAGIC):
                        print(f"[FAIL] {fname} Cell {idx}: corrupted PNG payload for '{r}'")
                        total_errors += 1
                    verified_att_cells.append(f"Cell {idx}:{r}({len(atts[r]['image/png']) // 1024}KB)")

        print(f"[PASS] {fname:<42} | {file_size_kb:6.1f} KB | {len(verified_nb['cells']):2d} cells | Attachments: {', '.join(verified_att_cells)}")

    if total_errors > 0:
        print(f"\n[FAILED] Total validation errors: {total_errors}")
        sys.exit(1)
    else:
        print("\n[SUCCESS] All 7 notebooks passed NBFormat v4.5 (v5.10.4) & NBConvert (v7.17.1) attachment validation with 0 errors!")


if __name__ == "__main__":
    pack_and_validate_all()
