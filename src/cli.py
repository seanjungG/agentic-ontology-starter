# Copyright (c) 2026 Sean Jung (seanjung@google.com). All Rights Reserved.
# Non-Commercial Use Only: Methodology & Docs under CC BY-NC-ND 4.0; Source Code under PolyForm Noncommercial License 1.0.0.
# Commercial use, paid consulting/SI/PoC delivery, or production deployment requires prior written permission from seanjung@google.com.

# -*- coding: utf-8 -*-
"""Agentic Ontology Starter CLI (GOAL-233) — the same pipeline the studio runs, from a terminal.

  python3 -m src.cli new   --spec spec.json | --from workspace.json   [--bucket B] [--project P] ...   → prints the new ws id
  python3 -m src.cli build --bucket B --ws WS [--stages prepare,ingest,cqs,wiki,graph,eval]
  python3 -m src.cli ask   --bucket B --ws WS [--agent wiki|graph|hybrid] [--apply-cg] "question"
  python3 -m src.cli cg    --bucket B --ws WS feedback --agent wiki --question Q --answer A [--sentence S] [--rating up|down] [--reason CODE] [--run-id R]
  python3 -m src.cli cg    --bucket B --ws WS graph | rules | review --candidate ID --decision approve|reject [--note N]
                                    Context Graph (GOAL-285): sentence feedback → L1 signal → L2 candidate → SME → ChangeSet + CQ CG-n
  python3 -m src.cli eval  --bucket B --ws WS
  python3 -m src.cli calls --bucket B --ws WS [--stage graph]        MCP calls (tool · args · status · ms)
  python3 -m src.cli check --project P --bucket B [--region R] [--dataset D]
  python3 -m src.cli export-studio --bucket B --ws WS --project-id my_project [--out projects] [--upload]
                                    finished workspace → Agentic Ontology Studio project folder (Core MCP, GOAL-249)
  python3 -m src.cli purge-spanner --project P [--instance I] [--database D] [--days 7] [--dry-run]
                                    drop expired workspace graphs/tables from the shared Spanner database (GOAL-259)

Identity: default = your gcloud login (runtime); --impersonate SA uses `gcloud auth print-access-token --impersonate-service-account`;
--token-env NAME reads an access token from an environment variable.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, BASE_DIR)

from src import identity  # noqa: E402
from src.aos import agent as agent_mod  # noqa: E402
from src.aos import pipeline, studio  # noqa: E402
from src.aos.ws import McpLog, clean_env, load, new_workspace, read_calls, save  # noqa: E402


def _identity(a: argparse.Namespace) -> dict:
    if getattr(a, "impersonate", ""):
        tok = subprocess.check_output(["gcloud", "auth", "print-access-token", f"--impersonate-service-account={a.impersonate}"],
                                      text=True, stderr=subprocess.DEVNULL).strip()
        return {"mode": "token", "token": tok}
    if getattr(a, "token_env", ""):
        return {"mode": "token", "token": os.environ.get(a.token_env, "")}
    return {"mode": "runtime"}


def _printer(ev: dict) -> None:
    typ = ev.get("type")
    if typ == "stage":
        print(f"\n== {ev.get('label')} · {ev.get('status')}" + (f" · {ev.get('ms')} ms" if ev.get("ms") else "") +
              (f"\n   {json.dumps(ev.get('summary'), ensure_ascii=False)[:600]}" if ev.get("summary") else "") +
              (f"\n   ERROR {ev.get('error')}" if ev.get("error") else ""), flush=True)
    elif typ == "step":
        print(f"   [{ev.get('status')}] {ev.get('label')}" + (f" — {ev.get('detail')}" if ev.get("detail") else "") +
              (f" ({ev.get('ms')} ms)" if ev.get("ms") is not None else ""), flush=True)
    elif typ == "mcp":
        print(f"     · mcp {ev.get('tool')} {ev.get('status')} {ev.get('ms')} ms" + (f" {ev.get('error')[:160]}" if ev.get("error") else ""), flush=True)
    elif typ == "cq":
        print(f"   {ev.get('id')} [{ev.get('agent')}] {ev.get('verdict')} {ev.get('score')} — {ev.get('question')[:80]}", flush=True)


def _cg(a: argparse.Namespace, ws: dict) -> int:
    """Context Graph from the terminal (same store and parser as /api/v5/cg/*)."""
    from src.aos import context_graph as cg
    if a.action == "feedback":
        r = cg.record_feedback(ws, {"agent": a.agent, "question": a.question, "answer": a.answer, "sentence": a.sentence,
                                    "rating": a.rating, "reason_code": a.reason, "run_id": a.run_id}, a.lang)
        print(json.dumps({k: r[k] for k in ("feedback_id", "run_id", "synthesized_run", "summary")}, ensure_ascii=False))
        print(json.dumps({"parsed_intent": r["signal"]["parsed_intent"], "candidate": r["candidate"]}, ensure_ascii=False, indent=1))
        return 0
    if a.action == "graph":
        v = cg.graph_view(ws, a.lang)
        print(json.dumps({"object": v["object"], "counts": v["counts"], "pending": v["pending"]}, ensure_ascii=False))
        for c in v["candidates"]:
            print(f"  {c['candidate_id']}  {c.get('status'):8} {c.get('tacit_type'):7} {c.get('title')}")
        return 0
    if a.action == "rules":
        print(json.dumps(cg.approved_rules(ws, a.agent), ensure_ascii=False, indent=1))
        return 0
    r = cg.review(ws, a.candidate, a.decision, a.note, by=str(identity.current().get("principal") or "cli"),
                  read_cqs=lambda: studio.studio_data(ws, ["cqs"]).get("cqs") or [], save_cqs=lambda cqs: studio.save_cqs(ws, cqs))
    print(json.dumps({"approval": r["approval"], "changeset": r["changeset"], "cq": r["cq"], "cq_error": r["cq_error"]}, ensure_ascii=False, indent=1))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python3 -m src.cli", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p, ws=True):
        p.add_argument("--impersonate", default="", help="service account e-mail to impersonate")
        p.add_argument("--token-env", default="", help="environment variable holding an access token")
        if ws:
            p.add_argument("--bucket", required=True)
            p.add_argument("--ws", required=True)
    p = sub.add_parser("new")
    common(p, ws=False)
    p.add_argument("--spec", default="")
    p.add_argument("--from", dest="from_ws", default="")
    for k in ("bucket", "project", "region", "dataset", "graph_name", "model", "lang"):
        p.add_argument(f"--{k.replace('_', '-')}", dest=k, default="")
    p = sub.add_parser("build")
    common(p)
    p.add_argument("--stages", default=",".join(pipeline.STAGES))
    p = sub.add_parser("ask")
    common(p)
    p.add_argument("--agent", default="hybrid", choices=list(agent_mod.AGENTS))
    p.add_argument("--apply-cg", action="store_true", help="inject SME-approved Context Graph rules (CG-RULES) into the run")
    p.add_argument("question")
    p = sub.add_parser("cg")
    common(p)
    p.add_argument("action", choices=["feedback", "graph", "review", "rules"])
    p.add_argument("--agent", default="hybrid", choices=list(agent_mod.AGENTS))
    for k in ("question", "answer", "sentence", "rating", "reason", "run_id", "candidate", "decision", "note"):
        p.add_argument(f"--{k.replace('_', '-')}", dest=k, default="")
    p.add_argument("--lang", default="ko")
    p = sub.add_parser("eval")
    common(p)
    p = sub.add_parser("calls")
    common(p)
    p.add_argument("--stage", default="")
    p = sub.add_parser("check")
    common(p, ws=False)
    for k in ("bucket", "project", "region", "dataset", "model"):
        p.add_argument(f"--{k}", default="")
    p.add_argument("--lang", default="ko")
    p = sub.add_parser("export-studio")
    common(p)
    p.add_argument("--project-id", required=True, help="Studio folder name ^[a-z][a-z0-9_]{2,40}$")
    p.add_argument("--out", default="projects", help="parent folder of the Studio project (default ./projects)")
    p.add_argument("--studio-url", default="")
    p.add_argument("--upload", action="store_true", help="mirror the OKF wiki to gs://<bucket>/studio_projects/<project_id>/ for the Studio Wiki Agent")
    p.add_argument("--lang", default="ko")
    p = sub.add_parser("purge-spanner")
    common(p, ws=False)
    p.add_argument("--project", required=True)
    p.add_argument("--instance", default=os.environ.get("SPANNER_INSTANCE_ID", "starter-spanner"))
    p.add_argument("--database", default="")
    p.add_argument("--days", type=int, default=-1, help="TTL in days (default AOS_SPANNER_TTL_DAYS = 7)")
    p.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)

    with identity.use(_identity(a)):
        if a.cmd == "new":
            spec = json.load(open(a.spec or a.from_ws, encoding="utf-8")) if (a.spec or a.from_ws) else {}
            env = dict(spec.get("env") or {})
            for k in ("bucket", "project", "region", "dataset", "graph_name", "model"):
                if getattr(a, k):
                    env[k] = getattr(a, k)
            if a.from_ws:
                env.pop("dataset", None) if not a.dataset else None
            spec["env"] = env
            lang = a.lang or spec.get("lang") or "ko"
            ws = new_workspace(spec, lang)
            ok, allowed = pipeline.can_write(ws["env"])
            if not ok:
                print(f"write blocked for runtime identity (allowed: {allowed}) — use --impersonate or --token-env", file=sys.stderr)
                return 2
            save(ws, McpLog("new", None))
            print(ws["ws_id"])
            print(f"gs://{ws['env']['bucket']}/aos/{ws['ws_id']}/workspace.json", file=sys.stderr)
            return 0
        if a.cmd == "check":
            env = clean_env({k: getattr(a, k) for k in ("bucket", "project", "region", "dataset", "model") if getattr(a, k)}, "ws-00000000-000000")
            res = studio.check_env(env, a.lang)
            for c in res["checks"]:
                print(f"[{c['status']:5}] {c['label']}: {c['detail']}" + (f"\n        fix: {c['fix']}" if c["fix"] and c["status"] != "ok" else ""))
            return 0 if res["status"] == "OK" else 1
        if a.cmd == "purge-spanner":
            from src.aos import spanner_graph as SG
            env = {"project": a.project, "spanner_instance": a.instance, "spanner_database": a.database or SG.DEFAULT_DATABASE}
            res = SG.purge_expired(McpLog("purge", None), env, a.days if a.days >= 0 else SG.TTL_DAYS, dry_run=a.dry_run)
            print(json.dumps(res, ensure_ascii=False, indent=1))
            return 0
        ws = load(a.bucket, a.ws)
        if a.cmd == "build":
            rc = 0
            for st in [s.strip() for s in a.stages.split(",") if s.strip()]:
                rec = pipeline.run_stage(ws, st, _printer)
                if rec["status"] == "error":
                    rc = 1
                    break
            return rc
        if a.cmd == "cg":
            return _cg(a, ws)
        if a.cmd == "ask":
            from src.aos import context_graph as cg
            rules = cg.approved_rules(ws, a.agent) if a.apply_cg else []
            if rules:
                print(f"   [cg] {len(rules)} approved rule(s) injected as {agent_mod.RULES_PAGE_ID}", flush=True)
            res = agent_mod.run(ws, a.agent, a.question, _printer, extra_rules=[r["statement"] for r in rules])
            res["cg_rules_applied"] = rules
            rec = cg.record_run(ws, res)
            print(f"   [cg] run {rec.get('cg_run_id')}" + (f" (not recorded: {rec['cg_error']})" if rec.get("cg_error") else ""), flush=True)
            print(f"\n[{res['status']}] {res['answer']}\n")
            if res.get("citations"):
                print("citations:", ", ".join(res["citations"]))
            return 0 if res["status"] in ("GROUNDED", "UNGROUNDED") else 1
        if a.cmd == "eval":
            rec = pipeline.run_stage(ws, "eval", _printer)
            return 0 if rec["status"] == "done" else 1
        if a.cmd == "calls":
            for c in read_calls(a.bucket, a.ws):
                if a.stage and c.get("stage") != a.stage:
                    continue
                print(json.dumps(c, ensure_ascii=False))
            return 0
        if a.cmd == "export-studio":
            from src.aos import studio_export
            res = studio_export.export(ws, a.project_id, a.out, studio_url=a.studio_url, upload=a.upload, lang=a.lang)
            print(json.dumps(res, ensure_ascii=False, indent=1))
            return 0 if not res["upload_failed"] else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
