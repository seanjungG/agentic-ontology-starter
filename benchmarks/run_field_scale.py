# Copyright (c) 2026 Sean Jung (seanjung@google.com). All Rights Reserved.
# Non-Commercial Use Only: Methodology & Docs under CC BY-NC-ND 4.0; Source Code under PolyForm Noncommercial License 1.0.0.
# Commercial use, paid consulting/SI/PoC delivery, or production deployment requires prior written permission from seanjung@google.com.

# -*- coding: utf-8 -*-
"""Field-scale benchmark: RAG vs OKF Wiki vs Graph on the synthetic field-scale pack (GOAL-296).

The hands-on sample (4 documents) is too small to tell RAG and a wiki apart — every retriever finds the one relevant
paragraph. This runner builds the SAME three systems the starter builds for any workspace, on a pack that looks like a
real policy estate (53 documents: guides, dated notices, addenda, FAQs, archives, memos + 4 tables), then runs the
pack's 50 CQs through each system with one system-blind judge.

    python3 benchmarks/run_field_scale.py --lang ko                      # build + run everything
    python3 benchmarks/run_field_scale.py --lang ko --ws ws-...          # reuse a workspace
    python3 benchmarks/run_field_scale.py --lang ko --ws ws-... --stages compare
    python3 benchmarks/run_field_scale.py --lang ko --ws ws-... --cleanup   # delete the RAG corpus (it bills while it exists)

Nothing here is specific to the pack's questions: the stages are the normal `src.aos.pipeline` stages, the CQ file is
written to the workspace instead of being drafted by Gemini (the pack ships its own, with deterministic ledger-backed
answers), and the result is saved as it comes out — ties and losses included.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.aos import pipeline, rag  # noqa: E402
from src.aos.ws import McpLog, error_text, get_json, load, new_workspace, prefix, put_json, save  # noqa: E402

PACK = os.path.join(ROOT, "data", "field_scale_pack")
# pack CQ type → starter agent type (which agents are expected to answer) — used only for grouping in reports
STAGES = ("prepare", "ingest", "wiki", "graph", "rag", "compare")


def _print(ev: dict) -> None:
    if ev.get("type") in ("stage", "step"):
        print(f"   [{ev.get('type')}] {ev.get('stage') or ev.get('step')} {ev.get('status')} {ev.get('label', '')} "
              f"{str(ev.get('detail') or ev.get('error') or '')[:200]} {ev.get('ms', '')}", flush=True)
    elif ev.get("type") == "cq":
        print(f"   [cq] {ev['id']} {ev['agent']:5} {ev['score']:>5} {ev['verdict']}", flush=True)


def upload_pack(lang: str, bucket: str, pack_dir: str = "", name: str = "field_scale") -> dict:
    """Pack files → gs://<bucket>/aos_benchmark/<name>/<lang>/ (through the Core MCP, like every other write)."""
    log = McpLog("upload", None)
    base = f"aos_benchmark/{name}/{lang}/"
    jobs = []
    for sub, ctype in (("docs", "text/markdown; charset=utf-8"), ("tables", "text/csv; charset=utf-8")):
        d = os.path.join(pack_dir or os.path.join(PACK, lang), sub)
        for fn in sorted(os.listdir(d)) if os.path.isdir(d) else []:
            jobs.append((base + f"{sub}/{fn}", os.path.join(d, fn), ctype))

    def put(job):
        name, path, ctype = job
        r = log.call("storage_upload_object", {"bucket": bucket, "name": name, "text": open(path, encoding="utf-8").read(), "content_type": ctype}, timeout_s=60)
        if r.get("status") != "SUCCESS":
            raise RuntimeError(f"upload {name}: {error_text(r)}")
        return name
    with ThreadPoolExecutor(max_workers=8) as ex:
        names = list(ex.map(put, jobs))
    docs = [{"name": os.path.basename(n), "origin": "gcs", "uri": f"gs://{bucket}/{n}"} for n in names if "/docs/" in n]
    tables = [{"name": os.path.basename(n).rsplit(".", 1)[0], "origin": "gcs", "uri": f"gs://{bucket}/{n}"} for n in names if "/tables/" in n]
    return {"docs": docs, "tables": tables}


def workspace_cqs(lang: str, pack_dir: str = "") -> list:
    pack = json.load(open(os.path.join(pack_dir or os.path.join(PACK, lang), "cqs.json"), encoding="utf-8"))
    return [{"id": c["id"], "type": c["type"], "question": c["question"], "reference_answer": c["expected_answer"],
             "key_facts": c.get("key_facts") or []} for c in pack["cqs"]]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", default="ko", choices=["ko", "en"])
    ap.add_argument("--ws", default="")
    ap.add_argument("--bucket", default="")
    ap.add_argument("--project", default="")
    ap.add_argument("--graph-engine", default="", choices=["", "spanner", "bigquery"])
    ap.add_argument("--stages", default=",".join(STAGES))
    ap.add_argument("--ids", default="", help="comma separated CQ ids (compare only; result is printed, not stored)")
    ap.add_argument("--systems", default="", help="comma separated subset of rag,wiki,graph (compare only)")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--out", default="", help="result file (default data/field_scale_pack/results/<lang>.json)")
    ap.add_argument("--pack-dir", default="", help="another pack with the same layout: docs/*.md, tables/*.csv, cqs.json (default: the shipped field-scale pack)")
    ap.add_argument("--name", default="field_scale", help="pack name (GCS prefix, result label)")
    ap.add_argument("--bq-tables", default="", help="comma separated project.dataset.table to use as source tables instead of CSV files")
    ap.add_argument("--region", default="")
    ap.add_argument("--objective", default="")
    ap.add_argument("--cleanup", action="store_true", help="delete the workspace's RAG corpus and exit")
    a = ap.parse_args(argv)
    from src.aos.ws import env_defaults
    bucket = a.bucket or env_defaults()["bucket"]
    if a.ws:
        ws = load(bucket, a.ws)
    else:
        env = {"bucket": bucket}
        if a.project:
            env["project"] = a.project
        if a.graph_engine:
            env["graph_engine"] = a.graph_engine
        if a.region:
            env["region"] = a.region
        sources = upload_pack(a.lang, bucket, a.pack_dir, a.name)
        for fq in [x for x in a.bq_tables.split(",") if x]:
            sources["tables"].append({"name": fq.rsplit(".", 1)[-1], "origin": "bigquery", "fq": fq})
        title = "Field-scale benchmark — telecom subsidy · bundles · penalties (synthetic)"
        if a.pack_dir:
            title = f"Benchmark — {a.name}"
        ws = new_workspace({"env": env, "sources": sources,
                            "scenario": {"preset": a.name[:40], "title": title,
                                         "objective": a.objective or ("Answer counter and back-office questions about subsidies, plan bundles, early-termination "
                                                       "penalties and their exceptions as of the pack's as-of date, including what changed and when."
                                                       if a.lang == "en" else
                                                       "기준일 현재 지원금 · 결합 할인 · 위약금과 예외 조건, 그리고 무엇이 언제 바뀌었는지에 대한 창구 · 백오피스 질문에 답한다."),
                                         "question_type": "W3"}}, a.lang)
        save(ws, McpLog("new", None))
        print("workspace", ws["ws_id"], f"gs://{bucket}/{prefix(ws['ws_id'])}", flush=True)
    b, pf = ws["env"]["bucket"], prefix(ws["ws_id"])
    if a.cleanup:
        cfg = rag.load_config(ws)
        if cfg.get("corpus"):
            r = McpLog("cleanup", None).call("aos_core_rag_delete_corpus", {"corpus": cfg["corpus"], "wait_s": 120}, timeout_s=180)
            print("delete", cfg["corpus"], r.get("status"), error_text(r) if r.get("status") != "SUCCESS" else "")
            put_json(McpLog("cleanup", None), b, pf + "rag/config.json", {**cfg, "corpus": "", "deleted_at": time.strftime("%Y-%m-%dT%H:%M:%S")})
        return 0
    stages = [s.strip() for s in a.stages.split(",") if s.strip()]
    for st in stages:
        if st == "compare":
            put_json(McpLog("cqs", None), b, pf + "cqs.json", workspace_cqs(a.lang, a.pack_dir))
            if a.ids or a.systems:
                log = McpLog("compare", _print)
                res = rag.stage_compare(ws, log, _print, cq_ids=[x for x in a.ids.split(",") if x] or None, workers=a.workers,
                                        systems=[x for x in a.systems.split(",") if x] or None)
                print(json.dumps({k: v for k, v in res.items() if k != "run"}, ensure_ascii=False))
                if a.out and res.get("run"):
                    json.dump(res["run"], open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
                return 0
        rec = pipeline.run_stage(ws, st, _print)
        print(f"== {st}: {rec['status']} {rec.get('ms')} ms {json.dumps(rec.get('summary') or rec.get('error'), ensure_ascii=False)[:600]}", flush=True)
        if rec["status"] == "error":
            return 1
    if "compare" in stages:
        run = get_json(None, b, pf + "runs/three_way_latest.json", None)
        if run:
            if a.pack_dir and not a.out:
                raise SystemExit("--out is required with --pack-dir")
            out = a.out or os.path.join(PACK, "results", f"{a.lang}.json")
            os.makedirs(os.path.dirname(out), exist_ok=True)
            run["pack"] = {"name": a.name if a.pack_dir else "field_scale_pack", "lang": a.lang, "synthetic": not a.pack_dir, "docs": ws.get("summary", {}).get("docs"),
                           "tables": ws.get("summary", {}).get("tables"), "wiki": ws.get("summary", {}).get("wiki"),
                           "graph": ws.get("summary", {}).get("graph"), "rag": ws.get("summary", {}).get("rag"),
                           "graph_engine": ws["env"].get("graph_engine")}
            json.dump(run, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            print("wrote", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
