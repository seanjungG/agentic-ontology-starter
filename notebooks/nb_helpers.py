# -*- coding: utf-8 -*-
"""Shared helpers for the starter notebooks: setup, tables, charts, graph drawings, agent views and NL-to-GQL.

Data exploration cells use BigQuery `%%bqsql` magics (BigFrames). The MCP tools, the agent and the
NL-to-GQL example use the starter's own REST client (`src/gcp_client.py`) so that job IDs are visible.
"""
import json
import os
import sys
import warnings
from pathlib import Path

if Path("/etc/ssl/cert.pem").exists():
    os.environ.setdefault("SSL_CERT_FILE", "/etc/ssl/cert.pem")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import matplotlib.pyplot as plt  # noqa: E402
import networkx as nx  # noqa: E402
import pandas as pd  # noqa: E402
from IPython.display import Markdown, display  # noqa: E402
from matplotlib import font_manager  # noqa: E402

from src.gcp_client import (DEFAULT_DATASET_ID, DEFAULT_GEMINI_MODEL, DEFAULT_LOCATION,  # noqa: E402
                            DEFAULT_PROJECT_ID, call_vertex_gemini, execute_bq_sql, get_gcp_token)

PROJECT, DATASET, LOCATION, MODEL = DEFAULT_PROJECT_ID, DEFAULT_DATASET_ID, DEFAULT_LOCATION, DEFAULT_GEMINI_MODEL
FQ = f"{PROJECT}.{DATASET}"
GRAPH = f"{FQ}.STARTER_ONTOLOGY_GRAPH"
LANG = "ko"
PALETTE = ["#1A73E8", "#0d9488", "#F9AB00", "#D93025", "#9334E6", "#188038", "#0284c7", "#5F6368"]
LABEL_COLORS = {"CustomerContractNode": "#1A73E8", "DeviceNode": "#0284c7", "PlanNode": "#0d9488",
                "SubsidyNode": "#188038", "DomainRuleNode": "#F9AB00", "DocChunkNode": "#9334E6"}
NAME_KEYS = ("customer_id", "device_name", "plan_name", "rule_id", "chunk_id", "policy_id")


def setup(lang="ko"):
    """Sets BigFrames project/location/credentials, chart style and a CJK font; returns the runtime settings."""
    global LANG
    LANG = lang
    warnings.filterwarnings("ignore")
    import bigframes.pandas as bpd
    from google.oauth2.credentials import Credentials
    bpd.options.bigquery.project = PROJECT
    bpd.options.bigquery.location = LOCATION
    bpd.options.bigquery.credentials = Credentials(token=get_gcp_token())
    bpd.options.display.progress_bar = None
    pd.set_option("display.max_colwidth", 90)
    pd.set_option("display.width", 200)
    fonts = {f.name for f in font_manager.fontManager.ttflist}
    cjk = next((f for f in ("AppleGothic", "NanumGothic", "Noto Sans CJK KR", "Malgun Gothic") if f in fonts), None)
    plt.rcParams.update({"font.family": cjk or "sans-serif", "axes.unicode_minus": False, "figure.dpi": 100,
                         "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
                         "grid.alpha": 0.25, "axes.titleweight": "bold"})
    return pd.DataFrame([{"project": PROJECT, "dataset": DATASET, "location": LOCATION,
                          "graph": GRAPH.split(".")[-1], "model": MODEL}])


def t(ko, en):
    return ko if LANG == "ko" else en


def pdf(df):
    """BigFrames or pandas -> small pandas frame for display/plots (starter tables have < 20 rows)."""
    return df.to_pandas() if hasattr(df, "to_pandas") else pd.DataFrame(df)


def md(text):
    display(Markdown(text))


def show(df, cols=None):
    d = pdf(df)
    display(d[cols] if cols else d)


def show_md_file(path, max_lines=40):
    """Shows a markdown file as rendered output; headings are demoted so they do not break the notebook outline."""
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    body = "\n".join(("####" + ln.lstrip("#")) if ln.startswith("#") else ln for ln in lines[:max_lines])
    md(f"**`{Path(path).name}`** ({len(lines)} lines)\n\n{body}")


def read_json(rel):
    with open(ROOT / rel, "r", encoding="utf-8") as f:
        return json.load(f)


def sql(query):
    """Runs SQL/GQL through the starter client; returns (DataFrame, meta). Errors are returned, not raised."""
    r = execute_bq_sql(query)
    meta = {k: r.get(k) for k in ("status", "job_id", "elapsed_ms", "total_bytes_processed")}
    if r.get("status") != "SUCCESS":
        meta["error"] = str(r.get("error", ""))[:400]
    return pd.DataFrame(r.get("rows", [])), meta


# ------------------------------------------------------------------ charts
def _finish(ax, title, xlabel=None, ylabel=None):
    ax.set_title(title)
    if xlabel is not None:
        ax.set_xlabel(xlabel)
    if ylabel is not None:
        ax.set_ylabel(ylabel)
    plt.tight_layout()
    plt.show()


def bar(df, x, y, title, color=None, hline=None, hline_label=None, horizontal=False, fmt="{:,.0f}", figsize=(9, 3.6)):
    d = pdf(df)
    fig, ax = plt.subplots(figsize=figsize)
    colors = color if isinstance(color, list) else [color or PALETTE[0]] * len(d)
    if horizontal:
        ax.barh(d[x].astype(str), d[y], color=colors)
        ax.invert_yaxis()
        for i, v in enumerate(d[y]):
            ax.text(v, i, " " + fmt.format(v), va="center", fontsize=8)
    else:
        ax.bar(d[x].astype(str), d[y], color=colors)
        for i, v in enumerate(d[y]):
            ax.text(i, v, fmt.format(v), ha="center", va="bottom", fontsize=8)
        plt.setp(ax.get_xticklabels(), rotation=20, ha="right")
    if hline is not None:
        (ax.axvline if horizontal else ax.axhline)(hline, color=PALETTE[3], ls="--", lw=1, label=hline_label)
        if hline_label:
            ax.legend(loc="best", fontsize=8)
    _finish(ax, title)


def grouped_bar(df, x, ys, title, labels=None, fmt="{:,.0f}", figsize=(10, 3.8), ylabel=None):
    d = pdf(df)
    fig, ax = plt.subplots(figsize=figsize)
    w = 0.8 / len(ys)
    for k, col in enumerate(ys):
        pos = [i + (k - (len(ys) - 1) / 2) * w for i in range(len(d))]
        ax.bar(pos, d[col], w, label=(labels or ys)[k], color=PALETTE[k % len(PALETTE)])
        for p, v in zip(pos, d[col]):
            ax.text(p, v, fmt.format(v), ha="center", va="bottom", fontsize=7)
    ax.set_xticks(range(len(d)))
    ax.set_xticklabels(d[x].astype(str), rotation=15, ha="right")
    ax.legend(fontsize=8)
    _finish(ax, title, ylabel=ylabel)


def line(df, x, y, title, vline=None, vline_label=None, fmt="{:,.0f}", figsize=(9, 3.4), xlabel=None, ylabel=None):
    d = pdf(df)
    fig, ax = plt.subplots(figsize=figsize)
    ax.plot(d[x], d[y], marker="o", color=PALETTE[0], lw=1.6)
    for a, b in zip(d[x], d[y]):
        ax.annotate(fmt.format(b), (a, b), textcoords="offset points", xytext=(0, 6), ha="center", fontsize=7)
    if vline is not None:
        ax.axvline(vline, color=PALETTE[3], ls="--", lw=1, label=vline_label)
        if vline_label:
            ax.legend(fontsize=8)
    _finish(ax, title, xlabel, ylabel)


def heatmap(pivot, title, fmt="{:,.0f}", cmap="Blues", figsize=(9, 3.6)):
    fig, ax = plt.subplots(figsize=figsize)
    vals = pivot.astype(float).values
    im = ax.imshow(vals, cmap=cmap, aspect="auto")
    ax.set_xticks(range(pivot.shape[1]))
    ax.set_xticklabels(pivot.columns, rotation=20, ha="right")
    ax.set_yticks(range(pivot.shape[0]))
    ax.set_yticklabels(pivot.index)
    ax.grid(False)
    vmax = pd.Series(vals.ravel()).max()
    for i in range(pivot.shape[0]):
        for j in range(pivot.shape[1]):
            v = pivot.iat[i, j]
            if pd.notna(v):
                ax.text(j, i, fmt.format(v), ha="center", va="center", fontsize=8,
                        color="white" if vmax and float(v) > 0.6 * vmax else "black")
    fig.colorbar(im, ax=ax, shrink=0.8)
    _finish(ax, title)


# ------------------------------------------------------------------ graphs
def draw_graph(nodes, edges, title, layout="spring", figsize=(11, 6.5), node_size=1500, font_size=8, legend=None):
    """nodes: [{id, name, color, layer?}], edges: [{src, dst, label?, style?}]"""
    g = nx.MultiDiGraph()
    for n in nodes:
        g.add_node(n["id"], **n)
    for e in edges:
        g.add_edge(e["src"], e["dst"], label=e.get("label", ""), style=e.get("style", "solid"))
    if layout == "layers":
        pos = nx.multipartite_layout(g, subset_key="layer", align="vertical")
    elif layout == "shell":
        pos = nx.shell_layout(g)
    else:
        pos = nx.spring_layout(g, seed=7, k=1.6 / max(1, len(g) ** 0.5), iterations=200)
    fig, ax = plt.subplots(figsize=figsize)
    ax.axis("off")
    for style in ("solid", "dashed"):
        es = [(u, v) for u, v, d in g.edges(data=True) if d["style"] == style]
        nx.draw_networkx_edges(g, pos, edgelist=es, ax=ax, style=style, width=1.15, edge_color="#94A3B8",
                               arrows=True, arrowsize=12, node_size=node_size, connectionstyle="arc3,rad=0.06")
    nx.draw_networkx_nodes(g, pos, ax=ax, node_size=node_size, node_color=[g.nodes[n].get("color", PALETTE[0]) for n in g],
                           edgecolors="white", linewidths=1.5)
    nx.draw_networkx_labels(g, pos, ax=ax, labels={n: g.nodes[n].get("name", n) for n in g}, font_size=font_size,
                            font_family=plt.rcParams["font.family"])
    elabels = {}
    for u, v, d in g.edges(data=True):
        if d["label"]:
            elabels[(u, v)] = d["label"] if (u, v) not in elabels else elabels[(u, v)] + " / " + d["label"]
    nx.draw_networkx_edge_labels(g, pos, edge_labels=elabels, ax=ax, font_size=6.5, font_color="#475569",
                                 bbox={"boxstyle": "round,pad=0.15", "fc": "white", "ec": "none", "alpha": 0.8})
    if legend:
        for name, color in legend.items():
            ax.scatter([], [], c=color, s=80, label=name)
        ax.legend(loc="lower left", fontsize=8, frameon=False, ncol=min(6, len(legend)))
    ax.set_title(title, fontweight="bold")
    plt.tight_layout()
    plt.show()


def _node_name(props, labels):
    for k in NAME_KEYS:
        if props.get(k):
            return str(props[k])
    return labels[0] if labels else "?"


def paths_to_graph(path_json_values):
    """Parses GQL `TO_JSON(p)` values into (nodes, edges) for draw_graph. Node id = '<label>:<name>'."""
    nodes, ids, edges = {}, {}, []
    for v in path_json_values:
        while isinstance(v, str):
            v = json.loads(v)
        for el in v:
            labels = el.get("labels", [])
            if el.get("kind") == "node":
                name = _node_name(el.get("properties", {}), labels)
                nid = f"{labels[0] if labels else '?'}:{name}"
                ids[el["identifier"]] = nid
                nodes[nid] = {"id": nid, "name": name, "color": LABEL_COLORS.get(labels[0] if labels else "", PALETTE[7])}
        for el in v:
            if el.get("kind") == "edge":
                edges.append({"src": ids[el["source_node_identifier"]], "dst": ids[el["destination_node_identifier"]],
                              "label": (el.get("labels") or [""])[0]})
    uniq = {(e["src"], e["dst"], e["label"]): e for e in edges}
    return list(nodes.values()), list(uniq.values())


def graph_metadata():
    """Live property-graph metadata from INFORMATION_SCHEMA.PROPERTY_GRAPHS -> (node_labels, edge_labels)."""
    df, meta = sql(f"SELECT property_graph_metadata_json AS m FROM `{FQ}.INFORMATION_SCHEMA.PROPERTY_GRAPHS` "
                   f"WHERE property_graph_name = '{GRAPH.split('.')[-1]}'")
    m = df.iloc[0]["m"]
    m = json.loads(m) if isinstance(m, str) else m
    table_label, node_labels, edge_labels = {}, [], []
    for nt in m["nodeTables"]:
        for lp in nt["labelAndProperties"]:
            table_label[f"{PROJECT}.{DATASET}.{nt['dataSourceTable']['tableId']}"] = lp["label"]
            node_labels.append({"label": lp["label"], "table": nt["dataSourceTable"]["tableId"],
                                "key": ", ".join(nt["keyColumns"]),
                                "properties": [f"{p['name']}:{p['dataType']['typeKind']}" for p in lp["properties"]]})
    for et in m["edgeTables"]:
        for lp in et["labelAndProperties"]:
            edge_labels.append({"label": lp["label"], "table": et["dataSourceTable"]["tableId"],
                                "source": table_label.get(et["sourceNodeReference"]["nodeTable"], "?"),
                                "destination": table_label.get(et["destinationNodeReference"]["nodeTable"], "?"),
                                "properties": [f"{p['name']}:{p['dataType']['typeKind']}" for p in lp["properties"]]})
    return node_labels, edge_labels, meta


def schema_text(node_labels, edge_labels):
    lines = [f"Graph: `{GRAPH}`", "Nodes:"]
    lines += [f"- ({n['label']}) key {n['key']}; properties: {', '.join(n['properties'])}" for n in node_labels]
    lines += ["Edges:"]
    lines += [f"- ({e['source']})-[{e['label']}]->({e['destination']}); properties: {', '.join(e['properties'])}"
              for e in edge_labels]
    return "\n".join(lines)


# ------------------------------------------------------------------ MCP and agent views
def show_tool(res, table_key=None, cols=None):
    head = (f"**`{res.get('tool')}`** · status `{res.get('status')}` · steps `{', '.join(res.get('executed_steps', []))}` · "
            f"BigQuery jobs {len(res.get('bq_job_ids', []))} ({res.get('bq_elapsed_ms', 0):,.0f} ms)")
    if res.get("summary"):
        head += f"\n\n{res['summary']}"
    md(head + "\n\n" + "\n".join(f"- `{j}`" for j in res.get("bq_job_ids", [])[:6]))
    if table_key and res.get(table_key):
        d = pd.DataFrame(res[table_key])
        display(d[cols] if cols else d)


def _quote(text):
    return "\n".join("> " + line if line.strip() else ">" for line in text.splitlines())


def show_agent(res, title=None):
    lt, steps = res["llm_telemetry"], res["lifecycle"]["step_2_tool_dispatch"]["dispatched_tools"]
    params = {k: v for k, v in res["applied_params"].items() if v is not None}
    rows = "\n".join(f"| {s['step_index']} | `{s['tool_name']}` | `{s['output'].get('status')}` | "
                     f"{s['output'].get('matched_rows_count', s['output'].get('matched_graph_paths_count', '-'))} | "
                     f"{s['output'].get('bq_elapsed_ms', 0):,.0f} | {', '.join('`' + j + '`' for j in s['output'].get('bq_job_ids', [])) or '-'} |"
                     for s in steps)
    body = res["lifecycle"]["step_4_synthesis"]["markdown"].split("\n\n---\n- LLM:")[0]
    md(f"#### {title or ''}\n**Q.** {res['query']}\n\n"
       f"- {t('응답 상태', 'Answer status')}: `{res['answer_status']}` · Gemini `{lt['model']}` 2 calls · "
       f"{t('토큰', 'tokens')} {lt['prompt_tokens'] + lt['candidates_tokens']:,} · LLM {lt['elapsed_ms']:,.0f} ms · "
       f"{t('총', 'total')} {res['performance']['total_elapsed_seconds']} s\n"
       f"- {t('추출 파라미터', 'Extracted parameters')}: `{json.dumps(params, ensure_ascii=False)}`\n\n"
       f"| # | MCP | status | rows | BigQuery ms | Job ID |\n|---:|:---|:---|---:|---:|:---|\n{rows}\n\n"
       f"{t('**에이전트 답변**', '**Agent answer**')}\n\n{_quote(body)}")


def agent_row(res, qid):
    steps = res["lifecycle"]["step_2_tool_dispatch"]["dispatched_tools"]
    lt = res["llm_telemetry"]
    return {"id": qid, "answer_status": res["answer_status"], "tools": " > ".join(s["tool_name"].replace("mcp_", "") for s in steps),
            "bq_jobs": len(res["bq_telemetry"]["job_ids"]), "tokens": lt["prompt_tokens"] + lt["candidates_tokens"],
            "llm_ms": round(lt["elapsed_ms"]), "bq_ms": round(sum(s["output"].get("bq_elapsed_ms", 0) for s in steps)),
            "total_s": float(res["performance"]["total_elapsed_seconds"])}


# ------------------------------------------------------------------ NL -> GQL
GQL_SYS = """You write one BigQuery Graph query in GQL (ISO GQL, GoogleSQL dialect). Never write Cypher.
Return JSON only: {"answerable": true|false, "gql": "<one statement or empty>", "explanation": "<one short sentence in LANGUAGE>"}
Rules:
- Start with GRAPH `GRAPH_NAME` then MATCH ... RETURN ... (standalone GQL, no GRAPH_TABLE).
- Use only labels, properties and edge directions listed in [Schema]. Always write node labels, edge labels and direction.
- Return named properties with readable aliases, add ORDER BY, and LIMIT 50.
- DocChunkNode has no edges: add a second pattern (ch:DocChunkNode) and filter with WHERE ch.chunk_id = <x>.source_chunk_id.
- If [Schema] has no data for the question, return answerable=false and gql="".
"""


def _gen(prompt):
    r = call_vertex_gemini(prompt=prompt, system_instruction=GQL_SYS.replace("GRAPH_NAME", GRAPH).replace(
        "LANGUAGE", t("Korean", "English")), response_mime_type="application/json", temperature=0.0, max_tokens=1024)
    try:
        spec = json.loads(r.get("text") or "{}")
    except json.JSONDecodeError:
        spec = {"answerable": False, "gql": "", "explanation": "JSON parse error"}
    return spec, r.get("total_tokens", 0), r.get("elapsed_ms", 0)


def nl2gql(question, schema, repair=True):
    """Gemini writes GQL from the live schema, BigQuery runs it; one repair round with the BigQuery error."""
    spec, tok, ms = _gen(f"[Schema]\n{schema}\n\n[Question]\n{question}")
    attempts = []
    while spec.get("answerable") and spec.get("gql") and len(attempts) < (2 if repair else 1):
        df, meta = sql(spec["gql"])
        attempts.append({"gql": spec["gql"], "df": df, **meta})
        if meta["status"] == "SUCCESS":
            break
        spec, tok2, ms2 = _gen(f"[Schema]\n{schema}\n\n[Question]\n{question}\n\n[Previous GQL]\n{spec['gql']}\n\n"
                               f"[BigQuery error]\n{meta.get('error')}\n\nReturn a corrected query.")
        tok, ms = tok + tok2, ms + ms2
    out = [f"**Q.** {question}", f"- Gemini `{MODEL}`: {spec.get('explanation', '')} ({t('토큰', 'tokens')} {tok:,}, {ms:,.0f} ms)"]
    if not attempts:
        out.append(f"- {t('생성 결과', 'Result')}: `answerable=false` — {t('스키마에 없는 데이터라 GQL을 만들지 않음', 'no GQL generated because the schema has no such data')}")
    for i, a in enumerate(attempts, 1):
        out.append(f"\n{t('시도', 'Attempt')} {i} · status `{a['status']}` · job `{a.get('job_id')}` · {a.get('elapsed_ms') or 0:,.0f} ms"
                   f" · {len(a['df'])} rows\n```sql\n{a['gql'].strip()}\n```")
        if a.get("error"):
            out.append(f"- BigQuery error: `{a['error'][:300]}`")
    md("\n".join(out))
    last = attempts[-1] if attempts else None
    if last is not None and last["status"] == "SUCCESS":
        display(last["df"])
    return {"question": question, "answerable": bool(attempts), "attempts": len(attempts),
            "status": last["status"] if last else "NOT_ANSWERABLE", "rows": len(last["df"]) if last else 0,
            "job_id": last.get("job_id") if last else None, "gemini_tokens": tok}


# ------------------------------------------------------------------ stage helpers
def check_cq_sql(cqs):
    """Runs each CQ's verification_sql on BigQuery and compares it with expected_math."""
    rows = []
    for c in cqs:
        df, meta = sql(c["verification_sql"].replace("{fq}", FQ))
        got = df.iloc[0].to_dict() if len(df) else {}
        rows.append({"cq_id": c["cq_id"], "expected_math": c["expected_math"],
                     "bigquery_result": {k: got.get(k) for k in c["expected_math"]},
                     "match": bool(got) and all(got.get(k) == v for k, v in c["expected_math"].items()),
                     "job_id": meta["job_id"]})
    return pd.DataFrame(rows)


TRIPLE_SYS = """You propose ontology relation candidates from policy text for human review. Return JSON only:
{"triples": [{"subject": str, "relation": str, "object": str, "chunk_id": str}]}
- subject/object: short noun phrases found in the text (entities or concepts), in English.
- relation: UPPER_SNAKE_CASE verb phrase. Reuse these existing labels when they fit: USES_DEVICE, SUBSCRIBES_PLAN,
  HAS_SUBSIDY_POLICY, APPLIES_TO_PLAN. At most 12 triples. Do not add facts that are not in the text."""
EDGE_LABELS = ("USES_DEVICE", "SUBSCRIBES_PLAN", "HAS_SUBSIDY_POLICY", "APPLIES_TO_PLAN")


def propose_triples(chunk_ids):
    ids = ", ".join(f"'{c}'" for c in chunk_ids)
    df, meta = sql(f"SELECT chunk_id, content FROM `{FQ}.tb_doc_chunks` WHERE chunk_id IN ({ids}) ORDER BY chunk_id")
    text = "\n\n".join(f"[{r.chunk_id}]\n{r.content}" for r in df.itertuples())
    r = call_vertex_gemini(prompt=text, system_instruction=TRIPLE_SYS, response_mime_type="application/json",
                           temperature=0.0, max_tokens=2048)
    triples = pd.DataFrame(json.loads(r.get("text") or '{"triples": []}').get("triples", []))
    if len(triples):
        triples["existing_edge_label"] = triples["relation"].isin(EDGE_LABELS)
    md(f"BigQuery job `{meta['job_id']}` · Gemini `{MODEL}` · {t('토큰', 'tokens')} {r.get('total_tokens', 0):,} · "
       f"{r.get('elapsed_ms', 0):,.0f} ms · {len(triples)} {t('개 후보', 'candidates')}")
    return triples


def penalty_curve(server, customer_id, target_fee, days):
    rows = []
    for d in days:
        r = server.execute_tool("mcp_calculate_penalty_rule",
                                {"customer_id": customer_id, "target_monthly_fee_krw": target_fee, "elapsed_days": d})
        c = r["calculations"][0]
        rows.append({"elapsed_days": d, "penalty_krw": c["penalty_krw"], "penalty_status": c["penalty_status"],
                     "applied_rule_id": c["applied_rule_id"], "bq_job_id": r["bq_job_id"]})
    return pd.DataFrame(rows)


def lineage_graph(records, cq_rows):
    """Tier 1 source files -> Tier 2 chunks -> Tier 3 rules / contracts (graph) -> Tier 4 CQ answers."""
    nodes, edges = {}, set()

    def add(nid, name, layer, color):
        nodes.setdefault(nid, {"id": nid, "name": name, "layer": layer, "color": color})

    for r in records:
        k = "K:" + r["contract_id"]
        add(k, r["customer_id"], 3, LABEL_COLORS["CustomerContractNode"])
        add("F:customer_contracts.csv", "customer_contracts.csv", 0, PALETTE[7])
        edges.add(("F:customer_contracts.csv", k))
        if r.get("rule_id"):
            add("R:" + r["rule_id"], r["rule_id"], 2, LABEL_COLORS["DomainRuleNode"])
            add("F:domain_rules.csv", "domain_rules.csv", 0, PALETTE[7])
            edges |= {("F:domain_rules.csv", "R:" + r["rule_id"]), ("R:" + r["rule_id"], k)}
        if r.get("source_chunk_id"):
            add("C:" + r["source_chunk_id"], r["source_chunk_id"], 1, LABEL_COLORS["DocChunkNode"])
            add("F:" + r["source_file"], r["source_file"], 0, PALETTE[7])
            edges |= {("F:" + r["source_file"], "C:" + r["source_chunk_id"]), ("C:" + r["source_chunk_id"], "R:" + r["rule_id"])}
    for q in cq_rows:
        add("Q:" + q["cq_id"], q["cq_id"], 4, PALETTE[5] if q["status"] == "PASSED" else PALETTE[3])
        add("C:" + q["grounded_chunk"], q["grounded_chunk"], 1, LABEL_COLORS["DocChunkNode"])
        edges.add(("C:" + q["grounded_chunk"], "Q:" + q["cq_id"]))
    return list(nodes.values()), [{"src": a, "dst": b} for a, b in sorted(edges)]


def recheck_cq(cq, agent):
    """Re-runs one golden CQ and shows the same checks pipeline/validator.py applies."""
    from pipeline.validator import FOOTER, _has
    df, meta = sql(cq["verification_sql"].replace("{fq}", FQ))
    got = df.iloc[0].to_dict() if len(df) else {}
    res = agent.execute_cycle(cq["query"])
    body = res["lifecycle"]["step_4_synthesis"]["markdown"].split(FOOTER)[0]
    checks = [{"check": "verification_sql == expected_math", "passed": all(got.get(k) == v for k, v in cq["expected_math"].items()),
               "detail": f"{got} (job {meta['job_id']})"}]
    checks += [{"check": f"answer contains {k} = {v:,}", "passed": _has(body, v), "detail": ""} for k, v in cq["expected_math"].items()]
    checks += [{"check": f"answer cites {cq['grounded_chunk']}", "passed": cq["grounded_chunk"] in body, "detail": ""},
               {"check": "answer_status == GROUNDED", "passed": res["answer_status"] == "GROUNDED", "detail": res["answer_status"]}]
    return res, pd.DataFrame(checks)
