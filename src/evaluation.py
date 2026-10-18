# Copyright (c) 2026 Sean Jung (seanjung@google.com). All Rights Reserved.
# Non-Commercial Use Only: Methodology & Docs under CC BY-NC-ND 4.0; Source Code under PolyForm Noncommercial License 1.0.0.
# Commercial use, paid consulting/SI/PoC delivery, or production deployment requires prior written permission from seanjung@google.com.

# -*- coding: utf-8 -*-
"""Step 6 — golden-CQ evaluation of the recipe's agents (deterministic key-fact scoring, no LLM judge)."""
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Dict, List, Optional

from src import datapack
from src.agent.agents import run_agent
from src.config import StarterConfig

Emit = Callable[[Dict[str, Any]], None]
# numbers next to Korean units (원 · 일 · 개월) count; numbers glued to ASCII letters/digits/underscores (5G, CHUNK_003) do not
NUM_RE = re.compile(r"(?<![A-Za-z0-9_.,])(\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)(?![A-Za-z0-9_])")


def numbers_in(text: str) -> List[float]:
    out = []
    for m in NUM_RE.finditer(text or ""):
        try:
            out.append(float(m.group(1).replace(",", "")))
        except ValueError:
            pass
    return out


def score_answer(answer: str, cq: Dict[str, Any]) -> Dict[str, Any]:
    nums = numbers_in(answer)
    need = [float(n) for n in cq.get("expect_numbers") or []]
    hits = [n for n in need if any(abs(n - x) < 1e-6 for x in nums)]
    terms = cq.get("expect_terms_any") or []
    low = (answer or "").lower()
    term_hit = next((t for t in terms if t.lower() in low), None)
    term_ok = (not terms) or term_hit is not None
    if len(hits) == len(need) and term_ok and (need or terms):
        verdict = "PASS"
    elif hits or (terms and term_ok):
        verdict = "PARTIAL"
    else:
        verdict = "FAIL"
    return {"verdict": verdict, "numbers_expected": need, "numbers_found": hits, "term_hit": term_hit}


def run_eval(cfg: StarterConfig, recipe: str, lang: str, emit: Optional[Emit] = None, workers: int = 3) -> Dict[str, Any]:
    emit = emit or (lambda ev: None)
    t0 = time.perf_counter()
    items = datapack.cqs(lang, recipe)
    emit({"type": "plan", "total": len(items), "cqs": [{"cq_id": c["cq_id"], "agent": c["agent"], "query": c["query"],
                                                         "expected": c["expected"], "category": c["category"]} for c in items]})

    def one(cq: Dict[str, Any]) -> Dict[str, Any]:
        s = time.perf_counter()
        res = run_agent(cfg, recipe, cq["agent"], lang, cq["query"])
        sc = score_answer(res.get("answer") or "", cq)
        return {"cq_id": cq["cq_id"], "agent": cq["agent"], "category": cq["category"], "query": cq["query"], "expected": cq["expected"],
                "answer_status": res.get("status"), "answer": res.get("answer") or "", "ms": round((time.perf_counter() - s) * 1000, 1), **sc}

    rows: List[Dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=max(1, workers)) as ex:
        futs = {}
        for cq in items:
            emit({"type": "cq", "cq_id": cq["cq_id"], "status": "running"})
            futs[ex.submit(one, cq)] = cq
        for f in as_completed(futs):
            row = f.result()
            rows.append(row)
            emit({"type": "cq", "status": "done", **{k: (v[:600] if k == "answer" else v) for k, v in row.items()}})
    order = {c["cq_id"]: i for i, c in enumerate(items)}
    rows.sort(key=lambda r: order[r["cq_id"]])
    pts = {"PASS": 1.0, "PARTIAL": 0.5, "FAIL": 0.0}
    per_agent: Dict[str, Dict[str, Any]] = {}
    for r in rows:
        a = per_agent.setdefault(r["agent"], {"n": 0, "pass": 0, "partial": 0, "fail": 0, "points": 0.0})
        a["n"] += 1
        a[r["verdict"].lower()] += 1
        a["points"] += pts[r["verdict"]]
    for a in per_agent.values():
        a["score"] = round(100 * a["points"] / a["n"], 1) if a["n"] else 0.0
    total_pts = sum(pts[r["verdict"]] for r in rows)
    summary = {"recipe": recipe, "lang": lang, "total": len(rows), "pass": sum(r["verdict"] == "PASS" for r in rows),
               "partial": sum(r["verdict"] == "PARTIAL" for r in rows), "fail": sum(r["verdict"] == "FAIL" for r in rows),
               "score": round(100 * total_pts / len(rows), 1) if rows else 0.0, "per_agent": per_agent,
               "ms": round((time.perf_counter() - t0) * 1000, 1), "model": cfg.model}
    emit({"type": "summary", **summary})
    return {"summary": summary, "rows": rows}
