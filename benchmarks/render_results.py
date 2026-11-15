# Copyright (c) 2026 Sean Jung (seanjung@google.com). All Rights Reserved.
# Non-Commercial Use Only: Methodology & Docs under CC BY-NC-ND 4.0; Source Code under PolyForm Noncommercial License 1.0.0.
# Commercial use, paid consulting/SI/PoC delivery, or production deployment requires prior written permission from seanjung@google.com.

# -*- coding: utf-8 -*-
"""Regenerate the measured tables in the docs from the field-scale result files (GOAL-296).

    python3 benchmarks/render_results.py            rewrite the slots in README.md · README.ko.md
    python3 benchmarks/render_results.py --check    exit 1 when a slot differs from what the result files say (used by the tests)
    python3 benchmarks/render_results.py --print    print the generated Markdown and change nothing

A slot is the text between `<!-- GOAL296_RESULTS:<pack lang>:BEGIN -->` and `<!-- GOAL296_RESULTS:<pack lang>:END -->`.
The tables are copied from data/field_scale_pack/results/<pack lang>.json (written by benchmarks/run_field_scale.py); no number is
typed by hand. A missing result or one flagged `"placeholder": true` renders a "not measured" line instead of a table.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from typing import Dict, List

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.aos import three_way  # noqa: E402

DOCS = {"README.md": "en", "README.ko.md": "ko"}  # file → prose language of the tables
PACK_LANGS = ("en", "ko")
SLOT = "<!-- GOAL296_RESULTS:{name}:{edge} -->"


def slot_text(pack_lang: str, doc_lang: str) -> str:
    res = three_way.field_scale(pack_lang)
    return three_way.render_markdown(res["run"] if res["available"] else None, doc_lang, pack_lang)


def render(text: str, doc_lang: str) -> str:
    for pl in PACK_LANGS:
        begin, end = SLOT.format(name=pl, edge="BEGIN"), SLOT.format(name=pl, edge="END")
        rx = re.compile(re.escape(begin) + r".*?" + re.escape(end), re.S)
        if not rx.search(text):
            continue
        body = slot_text(pl, doc_lang)
        text = rx.sub(lambda _m, b=body: f"{begin}\n{b}\n{end}", text)
    return text


def main(argv: List[str] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--print", dest="show", action="store_true")
    a = ap.parse_args(argv)
    if a.show:
        for pl in PACK_LANGS:
            for dl in ("en", "ko"):
                print(f"\n===== pack {pl} · tables in {dl} =====\n{slot_text(pl, dl)}")
        return 0
    stale: Dict[str, bool] = {}
    for name, doc_lang in DOCS.items():
        path = os.path.join(ROOT, name)
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as f:
            old = f.read()
        new = render(old, doc_lang)
        stale[name] = new != old
        if stale[name] and not a.check:
            with open(path, "w", encoding="utf-8") as f:
                f.write(new)
        print(f"{name}: {'out of date' if stale[name] and a.check else 'updated' if stale[name] else 'up to date'}")
    return 1 if a.check and any(stale.values()) else 0


if __name__ == "__main__":
    sys.exit(main())
