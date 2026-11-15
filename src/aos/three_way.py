# Copyright (c) 2026 Sean Jung (seanjung@google.com). All Rights Reserved.
# Non-Commercial Use Only: Methodology & Docs under CC BY-NC-ND 4.0; Source Code under PolyForm Noncommercial License 1.0.0.
# Commercial use, paid consulting/SI/PoC delivery, or production deployment requires prior written permission from seanjung@google.com.

# -*- coding: utf-8 -*-
"""Read side of the RAG vs OKF Wiki vs Graph comparison (GOAL-296) — what the studio and the docs show.

    latest(ws)            the workspace's latest three-way run + RAG corpus state (runs/three_way_latest.json · rag/config.json)
    delete_corpus(ws)     cleanup — a RAG Engine corpus bills while it exists
    field_scale(lang)     the shipped field-scale benchmark result (data/field_scale_pack/results/<lang>.json)
    render_markdown(run)  the three stage tables as Markdown (README slots — benchmarks/render_results.py)

Nothing here computes or adjusts a score: every number is read from the run file written by `rag.stage_compare`
(tabulated by Core MCP `aos_core_eval_compare`). A result file flagged `"placeholder": true` is never rendered as a measurement.
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

from src.aos import rag as rag_mod
from src.aos.ws import McpLog, WsError, append_calls, can_write, error_text, get_json, now_iso, prefix, put_json, save, t

PACK_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "field_scale_pack")
RESULTS_DIR = os.path.join(PACK_DIR, "results")
SYSTEMS = rag_mod.SYSTEMS
CONFIG_KEYS = ("corpus", "location", "embedding_model", "retrieve", "import", "decompose", "stats", "built_at", "deleted_at", "version")


def corpus_view(cfg: Dict[str, Any]) -> Dict[str, Any]:
    """The corpus state as stored by the `rag` stage — settings are shown as returned by Core MCP, never restated here."""
    out = {k: cfg.get(k) for k in CONFIG_KEYS if cfg.get(k) not in (None, "")}
    out["exists"] = bool(cfg.get("corpus"))
    return out


def latest(ws: Dict[str, Any]) -> Dict[str, Any]:
    b, pf = ws["env"]["bucket"], prefix(ws["ws_id"])
    run = get_json(None, b, pf + "runs/three_way_latest.json", None)
    stages = ws.get("stages") or {}
    return {"status": "OK", "run": run if isinstance(run, dict) else None, "rag": corpus_view(rag_mod.load_config(ws)),
            "stages": {k: stages.get(k) for k in ("rag", "compare")},
            "built": {"wiki": (stages.get("wiki") or {}).get("status") == "done", "graph": (stages.get("graph") or {}).get("status") == "done",
                      "cqs": (stages.get("cqs") or {}).get("status") == "done"}}


def delete_corpus(ws: Dict[str, Any]) -> Dict[str, Any]:
    """Delete the workspace's RAG Engine corpus. The comparison run stays (it is a record of what was measured)."""
    lang = ws.get("lang", "ko")
    ok, allowed = can_write(ws["env"])
    if not ok:
        raise WsError("WRITE_BLOCKED", f"데모 신원(runtime)은 {allowed} 프로젝트에만 쓸 수 있습니다. 내 토큰 또는 SA를 입력하세요.",
                      f"The demo (runtime) identity may only write to {allowed}. Enter your token or SA.")
    log = McpLog("rag", None)
    cfg = rag_mod.load_config(ws, log)
    if not cfg.get("corpus"):
        return {"status": "OK", "deleted": False, "rag": corpus_view(cfg), "ws": ws,
                "message": t(lang, "삭제할 RAG 코퍼스가 없습니다", "there is no RAG corpus to delete")}
    r = log.call("aos_core_rag_delete_corpus", {"corpus": cfg["corpus"], "wait_s": 120}, timeout_s=180)
    if r.get("status") != "SUCCESS":
        append_calls(ws, log)
        return {"status": "ERROR", "message": "aos_core_rag_delete_corpus: " + error_text(r), "rag": corpus_view(cfg)}
    cfg = {**cfg, "deleted_corpus": cfg["corpus"], "corpus": "", "deleted_at": now_iso()}
    put_json(log, ws["env"]["bucket"], prefix(ws["ws_id"]) + "rag/config.json", cfg)
    (ws.setdefault("stages", {})).pop("rag", None)  # not built any more — `compare` refuses to run until `rag` is rebuilt
    summ = ws.setdefault("summary", {})
    summ["rag"] = {**(summ.get("rag") or {}), "deleted_at": cfg["deleted_at"]}
    save(ws, log)
    append_calls(ws, log)
    return {"status": "OK", "deleted": True, "existed": r.get("exists", True) is not False, "rag": corpus_view(cfg), "ws": ws}


# ================================================================================================ field-scale benchmark
def field_scale(lang: str) -> Dict[str, Any]:
    """The shipped synthetic field-scale benchmark result for one language; `available: False` when it has not been measured."""
    lang = "ko" if lang == "ko" else "en"
    path = os.path.join(RESULTS_DIR, f"{lang}.json")
    out: Dict[str, Any] = {"status": "OK", "lang": lang, "available": False, "placeholder": False, "run": None}
    try:
        with open(path, encoding="utf-8") as f:
            run = json.load(f)
    except (OSError, ValueError):
        return out
    if not isinstance(run, dict) or not isinstance(run.get("comparison"), dict) or not isinstance(run.get("results"), dict):
        return out
    out.update(available=True, placeholder=bool(run.get("placeholder")), run=run, pack=pack_info(lang))
    return out


def pack_info(lang: str) -> Dict[str, Any]:
    """What the synthetic pack contains (counted from the shipped files) + the CQ type labels."""
    base = os.path.join(PACK_DIR, "ko" if lang == "ko" else "en")
    info: Dict[str, Any] = {"synthetic": True, "types": {}}
    try:
        with open(os.path.join(base, "cqs.json"), encoding="utf-8") as f:
            pack = json.load(f)
        info["as_of"] = pack.get("as_of")
        info["cqs"] = len(pack.get("cqs") or [])
        info["types"] = {k: (v.get(lang) or v.get("en") or k) for k, v in (pack.get("types") or {}).items() if isinstance(v, dict)}
        info["docs"] = len([n for n in os.listdir(os.path.join(base, "docs")) if n.endswith(".md")])
        info["tables"] = len([n for n in os.listdir(os.path.join(base, "tables")) if n.endswith(".csv")])
    except (OSError, ValueError):
        pass
    return info


# ================================================================================================ markdown (README slots)
_L = {
    "pending": ("_아직 측정 결과가 없습니다 — `python3 benchmarks/run_field_scale.py --lang {pack}` 실행 후 `python3 benchmarks/render_results.py`로 이 표를 생성합니다._",
                "_Not measured yet — run `python3 benchmarks/run_field_scale.py --lang {pack}`, then `python3 benchmarks/render_results.py` generates this table._"),
    "placeholder": ("_결과 파일이 자리표시자(`\"placeholder\": true`)입니다 — 측정값이 아니므로 표를 만들지 않습니다._",
                    "_The result file is a placeholder (`\"placeholder\": true`) — it holds no measurements, so no table is rendered._"),
    "meta": ("CQ {n}개 · 답변 모델 `{model}` · 채점 `{judge}` · 측정 {at}", "{n} CQs · answer model `{model}` · judge `{judge}` · measured {at}"),
    "rag": ("RAG 설정(Core MCP가 돌려준 값): 임베딩 `{emb}` · 검색 `{ret}` · 조각 {units}개",
            "RAG settings (as returned by Core MCP): embedding `{emb}` · retrieval `{ret}` · {units} units"),
    "stage1": ("1단계 — RAG vs OKF 위키", "Stage 1 — RAG vs OKF Wiki"), "stage2": ("2단계 — OKF 위키 vs 그래프", "Stage 2 — OKF Wiki vs Graph"),
    "final": ("최종 — RAG vs OKF 위키 vs 그래프", "Final — RAG vs OKF Wiki vs Graph"), "bytype": ("CQ 유형별 평균", "Average by CQ type"),
    "metric": ("지표", "Metric"), "avg": ("평균 점수 (100점)", "Average score (of 100)"), "pass": ("PASS", "PASS"), "delta": ("차이", "Δ"),
    "wtl": ("{c} 기준 승 · 무 · 패", "{c} wins · ties · losses"), "system": ("방식", "System"), "partial": ("PARTIAL", "PARTIAL"),
    "fail": ("FAIL", "FAIL"), "lat": ("평균 응답 시간(초)", "Avg latency (s)"), "type": ("유형", "Type"), "n": ("문항", "CQs"), "best": ("최고 평균", "Top average"),
    "tie": ("동률", "tie"), "thr": ("PASS ≥ {p} · PARTIAL ≥ {q} · {m}점 이내 차이는 무승부", "PASS ≥ {p} · PARTIAL ≥ {q} · a difference within {m} points is a tie"),
}
NAMES = {"rag": ("RAG", "RAG"), "wiki": ("OKF 위키", "OKF Wiki"), "graph": ("그래프", "Graph")}


def _tx(lang: str, key: str, **kw: Any) -> str:
    s = _L[key][0 if lang == "ko" else 1]
    return s.format(**kw) if kw else s


def _name(lang: str, system: str) -> str:
    return NAMES[system][0 if lang == "ko" else 1]


def _num(v: Any) -> str:
    if v is None:
        return "–"
    return str(v)


def _signed(v: Any) -> str:
    return "–" if v is None else f"{float(v):+.1f}"


def best_of(row: Dict[str, Any]) -> List[str]:
    """Systems sharing the top average of a by-type row (more than one = a tie — never broken in anyone's favour)."""
    vals = {s: row.get(s) for s in SYSTEMS if row.get(s) is not None}
    if not vals:
        return []
    top = max(vals.values())
    return [s for s in SYSTEMS if vals.get(s) == top]


def _pair_table(lang: str, st: Dict[str, Any]) -> List[str]:
    b, c = st["base"], st["candidate"]
    bn, cn = _name(lang, st.get("base_name", "rag")), _name(lang, st.get("candidate_name", "wiki"))
    return [f"| {_tx(lang, 'metric')} | {bn} | {cn} | {_tx(lang, 'delta')} |", "|---|---:|---:|---:|",
            f"| {_tx(lang, 'avg')} | {_num(b.get('avg'))} | {_num(c.get('avg'))} | {_signed(st.get('delta_points'))} |",
            f"| {_tx(lang, 'pass')} | {b.get('pass')}/{b.get('count')} | {c.get('pass')}/{c.get('count')} | {int(st.get('delta_pass') or 0):+d} |",
            f"| {_tx(lang, 'wtl', c=cn)} | | {st.get('wins')} · {st.get('ties')} · {st.get('losses')} | |"]


def render_markdown(run: Optional[Dict[str, Any]], lang: str = "en", pack_lang: str = "") -> str:
    """Stage 1 / stage 2 / final tables for one run. Values are copied from the run file; nothing is recomputed."""
    lang = "ko" if lang == "ko" else "en"
    if not isinstance(run, dict) or not isinstance(run.get("comparison"), dict):
        return _tx(lang, "pending", pack=pack_lang or "en")
    if run.get("placeholder"):
        return _tx(lang, "placeholder")
    cmp_, method = run["comparison"], run.get("method") or {}
    rag_m = method.get("rag") or {}
    lines = [_tx(lang, "meta", n=cmp_.get("cq_count"), model=method.get("answer_model"), judge=method.get("judge"), at=str(run.get("at") or "")[:10]) + "  "]
    if rag_m.get("embedding_model") or rag_m.get("retrieve"):
        lines.append(_tx(lang, "rag", emb=rag_m.get("embedding_model"), ret=json.dumps(rag_m.get("retrieve"), ensure_ascii=False),
                         units=(rag_m.get("stats") or {}).get("units")) + "  ")
    th = cmp_.get("thresholds") or {}
    if th:
        lines.append(_tx(lang, "thr", p=_num(th.get("pass")), q=_num(th.get("partial")), m=_num(th.get("tie_margin"))))
    s1 = {**cmp_["stage1_rag_vs_wiki"], "base_name": "rag", "candidate_name": "wiki"}
    s2 = {**cmp_["stage2_wiki_vs_graph"], "base_name": "wiki", "candidate_name": "graph"}
    lines += ["", f"**{_tx(lang, 'stage1')}**", ""] + _pair_table(lang, s1)
    lines += ["", f"**{_tx(lang, 'stage2')}**", ""] + _pair_table(lang, s2)
    fin = cmp_["final_three_way"]
    lines += ["", f"**{_tx(lang, 'final')}**", "",
              f"| {_tx(lang, 'system')} | {_tx(lang, 'avg')} | {_tx(lang, 'pass')} | {_tx(lang, 'partial')} | {_tx(lang, 'fail')} | {_tx(lang, 'lat')} |",
              "|---|---:|---:|---:|---:|---:|"]
    for s in SYSTEMS:
        sm = (fin.get("summaries") or {}).get(s) or {}
        lines.append(f"| {_name(lang, s)} | {_num(sm.get('avg'))} | {sm.get('pass')}/{sm.get('count')} | {sm.get('partial')} | {sm.get('fail')} | {_num(sm.get('avg_latency_sec'))} |")
    lines += ["", f"**{_tx(lang, 'bytype')}**", "",
              f"| {_tx(lang, 'type')} | {_tx(lang, 'n')} | {_name(lang, 'rag')} | {_name(lang, 'wiki')} | {_name(lang, 'graph')} | {_tx(lang, 'best')} |",
              "|---|---:|---:|---:|---:|---|"]
    for row in fin.get("by_type") or []:
        best = best_of(row)
        label = " = ".join(_name(lang, s) for s in best) + (f" ({_tx(lang, 'tie')})" if len(best) > 1 else "")
        lines.append(f"| `{row.get('type')}` | {row.get('count', '')} | {_num(row.get('rag'))} | {_num(row.get('wiki'))} | {_num(row.get('graph'))} | {label} |")
    return "\n".join(lines)
