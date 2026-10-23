/* Agentic Ontology Starter v6 studio (GOAL-233 · v6 intake GOAL-243).
 * Vanilla JS, no build step. All visible text comes from studio_i18n.json (KO · EN) — keep this file free of UI prose.
 * Routes: #/start · #/scenario · #/env · #/data · #/types · #/build · #/studio/{overview,assets,wiki,graph,search,agents,eval} · #/deploy · #/handoff
 * v6 (GOAL-243): flow & service catalog + template (Core MCP), local/GCS/Drive intake with PDF/Office → Markdown conversion and
 * fidelity, document types + wiki strategy, deployment plan. Every piece of know-how is a Core MCP call made by the server.
 * State: localStorage "aol.studio.v5" (no secrets) · the pasted token lives in sessionStorage only.
 * QA hook: window.AOLStudio = { state(), go(route), setLang(l), api(path, body) }
 */
(function () {
  "use strict";
  const LS = "aol.studio.v5";
  const TOKEN_KEY = "aol.studio.v5.token";
  const STAGES = ["prepare", "ingest", "cqs", "wiki", "graph", "eval"];
  const ROUTES = ["start", "scenario", "env", "data", "types", "build", "studio/overview", "studio/assets", "studio/wiki", "studio/graph",
    "studio/search", "studio/agents", "studio/eval", "deploy", "handoff"];
  const STRATEGIES = ["direct", "typed", "reconvert"];
  const S = {
    lang: "ko", boot: null, i18n: {}, route: "start",
    scenario: { preset: "", title: "", customer: "", objective: "", question_type: "W3" },
    env: {}, identMode: "runtime", sa: "", identInfo: null, draftId: "", wsId: "", wsCreated: false, ws: null,
    sources: { docs: [], tables: [] }, check: null, data: {}, dataFor: "", busy: {}, log: [], ui: {},
    tpl: { flow: "", services: [], target: "sandbox" }, catalog: null, template: null, types: null, deploy: null, previews: {},
  };

  // ------------------------------------------------------------------ utils
  const $ = (s, el) => (el || document).querySelector(s);
  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  function T(k, v) {
    let s = (S.i18n[S.lang] || {})[k];
    if (s == null) s = (S.i18n.ko || {})[k] != null ? S.i18n.ko[k] : k;
    if (v) for (const [a, b] of Object.entries(v)) s = s.split("{" + a + "}").join(String(b));
    return s;
  }
  if (window.marked) window.marked.use({ tokenizer: { del() { return undefined; } } });
  function md(src) {
    const raw = String(src || "");
    if (window.marked && window.DOMPurify) return window.DOMPurify.sanitize(window.marked.parse(raw));
    return esc(raw).replace(/\n/g, "<br>");
  }
  function toast(msg, ms) {
    const el = $("#toast");
    el.textContent = msg;
    el.classList.add("on");
    clearTimeout(toast._t);
    toast._t = setTimeout(() => el.classList.remove("on"), ms || 2600);
  }
  function save() {
    const keep = { lang: S.lang, scenario: S.scenario, env: S.env, identMode: S.identMode, sa: S.sa, draftId: S.draftId, wsId: S.wsId,
      wsCreated: S.wsCreated, sources: S.sources, tpl: S.tpl, template: S.template, ui: { tab: S.ui.tab, agent: S.ui.agent } };
    localStorage.setItem(LS, JSON.stringify(keep));
  }
  function load() {
    try {
      const d = JSON.parse(localStorage.getItem(LS) || "{}");
      Object.assign(S, { lang: d.lang || S.lang, scenario: d.scenario || S.scenario, env: d.env || {}, identMode: d.identMode || "runtime",
        sa: d.sa || "", draftId: d.draftId || "", wsId: d.wsId || "", wsCreated: !!d.wsCreated, sources: d.sources || S.sources,
        tpl: Object.assign({ flow: "", services: [], target: "sandbox" }, d.tpl || {}), template: d.template || null });
      S.ui = Object.assign({}, d.ui || {});
    } catch (e) { /* fresh start */ }
  }
  const token = () => sessionStorage.getItem(TOKEN_KEY) || "";
  function identity() {
    if (S.identMode === "token") return { mode: "token", token: token() };
    if (S.identMode === "impersonate") return { mode: "impersonate", sa: S.sa };
    return { mode: "runtime" };
  }
  function wsRef() { return { bucket: (S.ws && S.ws.env && S.ws.env.bucket) || S.env.bucket, ws_id: S.wsId }; }
  async function api(path, body) {
    try {
      const r = await fetch(path, { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(Object.assign({}, body || {}, { lang: S.lang, identity: identity() })) });
      const j = await r.json().catch(() => ({ status: "ERROR", message: "HTTP " + r.status }));
      j._http = r.status;
      return j;
    } catch (e) { return { status: "ERROR", message: T("err.network", { e: e.message }), _http: 0 }; }
  }
  async function stream(path, body, on) {
    let r;
    try {
      r = await fetch(path, { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(Object.assign({}, body || {}, { lang: S.lang, identity: identity() })) });
    } catch (e) { on({ type: "error", message: T("err.network", { e: e.message }) }); return; }
    if (!(r.headers.get("content-type") || "").includes("ndjson")) {
      const j = await r.json().catch(() => ({}));
      on({ type: "error", message: j.message || j.status || ("HTTP " + r.status) });
      return;
    }
    const reader = r.body.getReader();
    const dec = new TextDecoder();
    let buf = "";
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += dec.decode(value, { stream: true });
      let i;
      while ((i = buf.indexOf("\n")) >= 0) {
        const line = buf.slice(0, i);
        buf = buf.slice(i + 1);
        if (line.trim()) { try { on(JSON.parse(line)); } catch (e) { /* partial line */ } }
      }
    }
  }
  async function copy(text) {
    try { await navigator.clipboard.writeText(text); toast(T("common.copied")); } catch (e) { toast(text.slice(0, 80)); }
  }
  function download(name, text, type) {
    const blob = text instanceof Blob ? text : new Blob([text], { type: type || "text/plain" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = name;
    document.body.appendChild(a);
    a.click();
    setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 500);
  }
  function codeBlock(text, id) {
    return `<div class="copyable"><pre class="code" ${id ? `id="${id}"` : ""}>${esc(text)}</pre><button class="btn small" data-act="copy-pre">${T("common.copy")}</button></div>`;
  }
  function table(rows, max) {
    if (!rows || !rows.length) return `<div class="empty">${T("gr.noRows")}</div>`;
    const cols = Object.keys(rows[0]);
    const body = rows.slice(0, max || 100).map((r) => "<tr>" + cols.map((c) => {
      const v = r[c];
      const s = v != null && typeof v === "object" ? JSON.stringify(v) : v;
      return `<td class="${typeof v === "number" ? "num" : ""}">${esc(String(s == null ? "" : s).slice(0, 400))}</td>`;
    }).join("") + "</tr>").join("");
    return `<div class="tbl-wrap"><table class="tbl"><thead><tr>${cols.map((c) => `<th class="mono">${esc(c)}</th>`).join("")}</tr></thead><tbody>${body}</tbody></table></div>`;
  }
  const statusDot = (st) => `<span class="dot ${esc(st || "idle")}"></span>`;
  const stageOf = (k) => ((S.ws && S.ws.stages) || {})[k] || null;
  const built = () => !!(S.wsCreated && S.ws);
  function dataType() {
    const d = S.sources.docs.length, t = S.sources.tables.length;
    return d && t ? "P3" : d ? "P1" : t ? "P2" : "";
  }
  const typesDone = () => S.sources.docs.length > 0 && S.sources.docs.every((d) => d.kind && d.strategy);
  // Core MCP know-how errors: an older Core MCP without the v6 tools answers MCP_UPDATE_NEEDED → explain instead of failing silently
  function errNote(j) {
    if (!j) return "";
    if (j.status === "MCP_UPDATE_NEEDED") return `<div class="note warn"><b>${T("mcp.updateTitle")}</b> ${esc(j.message || "")}<div class="meta mt8">${esc(T("mcp.updateHelp", { u: (S.boot && S.boot.core_mcp_url) || "" }))}</div></div>`;
    if (j.code === "DRIVE_ACCESS") return `<div class="note err">${esc(j.message || j.status)}</div>${driveHelp()}`;
    return `<div class="note err">${esc(j.message || j.error || j.status)}</div>`;
  }
  function errToast(j, extra) {
    toast((j.status === "MCP_UPDATE_NEEDED" ? T("mcp.updateTitle") + " " : "") + (j.message || j.error || j.status) + (extra ? " · " + extra : ""), 6000);
  }
  function driveHelp() {
    const who = (S.identInfo && S.identInfo.principal) || "";
    return `<div class="note"><b>${T("drive.helpTitle")}</b><ul class="plain">
      <li>${esc(T("drive.helpRuntime", { p: who || T("drive.saUnknown") }))}</li>
      <li>${esc(T("drive.helpToken"))} <code>gcloud auth login --enable-gdrive-access</code></li></ul></div>`;
  }
  const pct = (v) => (v == null || v === "" ? "-" : Math.round(Number(v) * 100) + "%");
  const gradeCls = (g) => ({ A: "ok", B: "ok", C: "warn", D: "error", F: "error" }[String(g || "").toUpperCase()] || "idle");
  const gsHttp = (uri) => { const m = /^gs:\/\/([^/]+)\/(.+)$/.exec(uri || ""); return m ? `https://storage.cloud.google.com/${m[1]}/${m[2].split("/").map(encodeURIComponent).join("/")}` : ""; };
  function templateSpec() {
    const t = S.template;
    if (t && t.flow) return { flow: t.flow.id, services: (t.services || []).map((x) => x.id), target: t.target, stages: t.stages, agents: t.flow.agents,
      data_type: t.flow.data_type, question_type: t.flow.question_type, catalog_version: (S.catalog && S.catalog.catalog_version) || "" };
    return S.tpl.flow ? { flow: S.tpl.flow, services: S.tpl.services, target: S.tpl.target } : {};
  }
  async function ensureCatalog() {
    if (S.catalog && S.catalog._lang === S.lang) return;
    const j = await api("/api/v5/catalog", {});
    if (j.status === "OK") { j._lang = S.lang; S.catalog = j; S.ui.catErr = null; } else S.ui.catErr = j;
    if (S.route === "scenario" || S.route === "env") rerender();
  }

  // ------------------------------------------------------------------ shell
  function topbar() {
    $("#brand-sub").textContent = T("brand.sub");
    const ws = $("#chip-ws");
    ws.innerHTML = S.wsId && S.wsCreated ? `${T("top.ws")} <b class="mono">${esc(S.wsId)}</b>` : esc(T("top.noWs"));
    const info = S.identInfo;
    $("#chip-id").innerHTML = `${statusDot(info ? "ok" : "idle")} ${esc(T("id." + S.identMode))}${info && info.principal ? ` <b class="mono">${esc(info.principal)}</b>` : ""}`;
    $("#chip-version").textContent = (S.boot && S.boot.version) || "";
    $("#chip-wizard").textContent = T("top.wizard");
    document.querySelectorAll("#lang-toggle button").forEach((b) => b.classList.toggle("on", b.dataset.lang === S.lang));
    document.documentElement.lang = S.lang;
  }
  function railItem(route, num, label, sub, state, enabled) {
    const on = S.route === route;
    const cls = ["rail-step", sub ? "" : "", on ? "on" : "", state === "done" ? "done" : "", enabled === false ? "off" : ""].join(" ");
    const numCls = state === "running" ? "num running" : state === "error" ? "num error" : "num";
    return `<a class="${cls}" ${enabled === false ? "" : `href="#/${route}"`} title="${enabled === false ? esc(T("rail.needWs")) : ""}">
      <span class="${numCls}">${esc(num)}</span><span><div class="t">${esc(label)}</div>${sub ? `<div class="s">${esc(sub)}</div>` : ""}</span></a>`;
  }
  function rail() {
    const st = (k) => { const s = stageOf(k); return s ? s.status : ""; };
    const buildState = STAGES.every((k) => st(k) === "done" || st(k) === "skipped") ? "done" : STAGES.some((k) => st(k) === "error") ? "error" : S.busy.build ? "running" : "";
    const has = built();
    const studio = [["studio/overview", "rail.overview"], ["studio/assets", "rail.assets"], ["studio/wiki", "rail.wiki"], ["studio/graph", "rail.graph"],
      ["studio/search", "rail.search"], ["studio/agents", "rail.agents"], ["studio/eval", "rail.eval"]];
    $("#rail").innerHTML = `
      <div class="rail-group"><div class="rail-label">${T("rail.g.understand")}</div>${railItem("start", "0", T("rail.start"), T("rail.start.s"), "")}</div>
      <div class="rail-group"><div class="rail-label">${T("rail.g.build")}</div>
        ${railItem("scenario", "1", T("rail.scenario"), T("rail.scenario.s"), S.scenario.objective ? "done" : "")}
        ${railItem("env", "2", T("rail.env"), T("rail.env.s"), S.check && S.check.status === "OK" ? "done" : "")}
        ${railItem("data", "3", T("rail.data"), T("rail.data.s"), dataType() ? "done" : "")}
        ${railItem("types", "4", T("rail.types"), T("rail.types.s"), typesDone() ? "done" : "")}
        ${railItem("build", "5", T("rail.build"), T("rail.build.s"), buildState)}</div>
      <div class="rail-group"><div class="rail-label">${T("rail.g.studio")}</div>
        ${studio.map(([r, k], i) => railItem(r, String.fromCharCode(65 + i), T(k), "", "", has)).join("")}</div>
      <div class="rail-group"><div class="rail-label">${T("rail.g.handoff")}</div>${railItem("deploy", "↗", T("rail.deploy"), T("rail.deploy.s"), S.deploy && S.deploy.verdict === "ready" ? "done" : "", has)}
        ${railItem("handoff", "→", T("rail.handoff"), T("rail.handoff.s"), "", has)}</div>
      <div class="rail-actions"><button class="btn small" data-act="ws-open-modal">${T("rail.open")}</button><button class="btn small" data-act="reset">${T("rail.new")}</button></div>`;
  }
  function go(route) { location.hash = "#/" + route; }
  function route() {
    let h = location.hash.replace(/^#\/?/, "");
    if (/^step-\d/.test(h)) h = "start";
    if (!ROUTES.includes(h)) h = "start";
    if ((h.startsWith("studio/") || h === "handoff" || h === "deploy") && !built()) h = S.wsId ? "build" : "start";
    S.route = h;
    render();
  }
  function render() {
    topbar();
    rail();
    const fn = PAGES[S.route] || PAGES.start;
    $("#page").innerHTML = fn();
    const after = AFTER[S.route];
    if (after) after();
    window.scrollTo(0, 0);
  }
  function rerender() { const y = window.scrollY; topbar(); rail(); $("#page").innerHTML = (PAGES[S.route] || PAGES.start)(); const a = AFTER[S.route]; if (a) a(); window.scrollTo(0, y); }
  const head = (eyebrow, title, lead, right) => `<div class="card step-head"><div class="flex"><div class="grow"><div class="eyebrow">${esc(eyebrow)}</div><h1>${esc(title)}</h1><p>${esc(lead)}</p></div>${right || ""}</div></div>`;

  // ------------------------------------------------------------------ pages
  const PAGES = {};
  const AFTER = {};

  PAGES.start = () => `
    <div class="card hero"><div class="eyebrow">${T("start.eyebrow")}</div><h1>${T("start.title")}</h1><p>${T("start.lead")}</p>
      <div class="cta"><button class="btn big primary" data-act="start-sample">${T("start.ctaSample")}</button>
      <button class="btn big dark" data-act="start-own">${T("start.ctaOwn")}</button>
      <button class="btn big" data-act="ws-open-modal">${T("start.ctaOpen")}</button></div></div>
    <div class="card"><div class="card-head"><h2>${T("start.flowTitle")}</h2><span class="sub">${T("start.flowSub")}</span></div><div id="flow-host" class="flow-host"></div></div>
    <div class="card"><div class="card-head"><h2>${T("start.layersTitle")}</h2></div><div class="layers">
      ${[1, 2, 3].map((i) => `<div class="layer l${i}"><h3>${T(`start.l${i}.t`)}</h3><p>${T(`start.l${i}.d`)}</p><ul>${[1, 2, 3].map((j) => `<li>${esc(T(`start.l${i}.b${j}`))}</li>`).join("")}</ul></div>`).join("")}
    </div></div>
    <div class="card"><div class="card-head"><h2>${T("start.stepsTitle")}</h2></div><div class="steps4">
      ${[["scenario", 1], ["env", 2], ["data", 3], ["build", 4]].map(([r, i]) => `<div class="step4" data-act="go" data-route="${r}"><div class="t">${T(`start.s${i}.t`)}</div><div class="d">${T(`start.s${i}.d`)}</div></div>`).join("")}
    </div></div>
    <div class="grid2"><div class="card"><div class="card-head"><h3>${T("start.outTitle")}</h3></div><div class="box"><ul>
      ${[1, 2, 3].map((i) => `<li><span class="ld" style="background:var(--c-mcp)"></span><span class="lt">${esc(T(`start.out${i}`))}</span></li>`).join("")}</ul></div></div>
    <div class="card"><div class="card-head"><h3>${T("start.vsTitle")}</h3></div><div class="tbl-wrap"><table class="tbl"><thead><tr><th>${T("start.vs.h1")}</th><th>${T("start.vs.h2")}</th><th>${T("start.vs.h3")}</th></tr></thead><tbody>
      ${[1, 2, 3, 4].map((i) => `<tr><td><b>${T(`start.vs.r${i}`)}</b></td><td>${T(`start.vs.r${i}a`)}</td><td>${T(`start.vs.r${i}b`)}</td></tr>`).join("")}</tbody></table></div></div></div>`;
  AFTER.start = () => {
    if (!window.AOLFlow || !window.STARTER_V5) return;
    const states = {};
    const nodes = window.STARTER_V5.stageNodes;
    for (const k of Object.keys(nodes)) { const s = stageOf(k); if (s && s.status === "done") nodes[k].forEach((n) => { states[n] = "done"; }); }
    window.AOLFlow.render($("#flow-host"), window.STARTER_V5.build, { lang: S.lang, states, highlight: dataType() ? window.STARTER_V5.paths[dataType()] : [],
      focusStyle: "dim", onChip: (c) => { if (built()) go(c.key === "eval" ? "studio/agents" : c.key === "graph" ? "studio/graph" : c.key === "wiki" ? "studio/wiki" : "studio/assets"); } });
  };

  // 1 scenario
  PAGES.scenario = () => {
    const ps = (S.boot && S.boot.presets) || [];
    const q = S.scenario.question_type || "W3";
    return head(T("rail.g.build"), T("scn.title"), T("scn.lead")) + `
    <div class="card"><div class="card-head"><h3>${T("scn.presets")}</h3></div><div class="sel-grid">
      ${ps.map((p) => `<button class="sel ${S.scenario.preset === p.id ? "on" : ""}" data-act="preset" data-id="${p.id}"><span class="check"></span>
        <div class="top"><span class="ttl">${esc(p.title)}</span>${p.sample ? `<span class="tag mcp">${T("scn.sampleTag")}</span>` : ""}</div>
        <div class="desc">${esc(p.customer)}</div><div class="ex">${esc(p.data)}</div></button>`).join("")}</div></div>
    <div class="card"><div class="form">
      <div class="field"><label>${T("scn.fTitle")}</label><input data-bind="scenario.title" value="${esc(S.scenario.title)}"></div>
      <div class="field"><label>${T("scn.fCustomer")}</label><input data-bind="scenario.customer" value="${esc(S.scenario.customer)}"></div>
      <div class="field full"><label>${T("scn.fObjective")}</label><textarea rows="3" data-bind="scenario.objective" placeholder="${esc(T("scn.fObjectiveHelp"))}">${esc(S.scenario.objective)}</textarea></div>
      <div class="field full"><label>${T("scn.qtype")}</label><div class="sel-grid">
        ${["W1", "W2", "W3"].map((w) => `<button class="sel ${q === w ? "on" : ""}" data-act="qtype" data-q="${w}"><span class="check"></span><div class="top"><span class="wbadge">${w}</span><span class="ttl">${T("scn." + w.toLowerCase())}</span></div><div class="desc">${T("scn." + w.toLowerCase() + "d")}</div></button>`).join("")}
      </div></div></div></div>
    ${catalogCard()}
    <div class="step-nav"><a class="btn" href="#/start">${T("common.prev")}</a><span class="spacer"></span><button class="btn primary" data-act="go" data-route="env" data-need="objective">${T("common.next")}</button></div>`;
  };

  function catalogCard() {
    const c = S.catalog;
    if (!c) return `<div class="card"><div class="card-head"><h3>${T("cat.title")}</h3></div>${S.ui.catErr ? errNote(S.ui.catErr) : `<div class="empty">${T("common.loading")}</div>`}</div>`;
    const flow = (c.flows || []).find((f) => f.id === S.tpl.flow);
    const svcName = {};
    (c.services || []).forEach((x) => { svcName[x.id] = x.name; });
    const flows = (c.flows || []).map((f) => `<button class="sel ${S.tpl.flow === f.id ? "on" : ""}" data-act="tpl-flow" data-id="${esc(f.id)}"><span class="check"></span>
      <div class="top"><span class="ttl">${esc(f.title)}</span></div><div class="desc">${esc(f.summary)}</div>
      <div class="flex mt8"><span class="pill-p">${esc(f.data_type)}</span><span class="wbadge">${esc(f.question_type)}</span>${f.convert ? `<span class="tag mcp">${T("cat.convert")}</span>` : ""}</div>
      <div class="ex">${esc(T("cat.stages"))}: ${(f.stages || []).map(esc).join(" → ")} · ${esc(T("cat.agents"))}: ${(f.agents || []).map((a) => esc(T("ag." + a))).join(", ")}</div></button>`).join("");
    const svc = (c.services || []).map((x) => {
      const req = flow ? flow.services.includes(x.id) : x.required;
      const opt = flow ? (flow.optional || []).includes(x.id) : !x.required;
      const on = req || S.tpl.services.includes(x.id);
      const dis = flow && !req && !opt;
      return `<button class="svc ${on ? "on" : ""} ${dis ? "off" : ""}" data-act="tpl-svc" data-id="${esc(x.id)}" ${req || dis ? "disabled" : ""}>
        <div class="top"><span class="ttl">${esc(x.name)}</span>${req ? `<span class="tag">${T("cat.required")}</span>` : opt ? `<span class="tag mcp">${T("cat.optional")}</span>` : ""}</div>
        <div class="desc">${esc(x.role)}</div><div class="ex">${esc(T("cat.cost"))}: ${esc(x.cost)}${(x.apis || []).length ? " · " + x.apis.map(esc).join(", ") : ""}</div></button>`;
    }).join("");
    return `<div class="card"><div class="card-head"><h3>${T("cat.title")}</h3><span class="sub">${T("cat.sub")}</span><span class="right"><span class="tag mono">catalog ${esc(c.catalog_version || "")}</span></span></div>
      <div class="sel-grid four">${flows}</div>
      <div class="eyebrow mt16">${T("cat.services")}${flow ? " · " + esc(flow.title) : ""}</div><div class="svc-grid mt8">${svc}</div>
      ${flow ? `<div class="note">${esc(T("cat.picked", { f: flow.title, s: (flow.services || []).concat(S.tpl.services.filter((x) => (flow.optional || []).includes(x))).map((x) => svcName[x] || x).join(", ") }))}</div>` : `<div class="note">${T("cat.pickHint")}</div>`}</div>`;
  }
  AFTER.scenario = () => { ensureCatalog(); };

  function templateCard() {
    const c = S.catalog, t = S.template;
    const targets = (c && c.targets) || [];
    const tg = targets.map((x) => `<button class="sel ${S.tpl.target === x.id ? "on" : ""}" data-act="tpl-target" data-id="${esc(x.id)}"><span class="check"></span>
      <div class="top"><span class="ttl">${esc(x.title)}</span></div><div class="desc">${esc(x.summary)}</div></button>`).join("");
    let prev = "";
    if (t && t.flow) {
      prev = `<div class="tpl-prev mt12"><div class="flex"><span class="pill-p">${esc(t.flow.data_type)}</span><span class="wbadge">${esc(t.flow.question_type)}</span><b>${esc(t.flow.title)}</b>
          <span class="tag">${esc(T("tpl.target." + t.target))}</span><span class="tag">${esc(T("tpl.identity"))}: ${esc(t.identity && t.identity.mode)}</span></div>
        <div class="cols3"><div class="box"><div class="ttl">${T("tpl.stages")}</div><ul>${(t.stages || []).map((x) => `<li><span class="ld"></span><span class="lt mono">${esc(x)}</span></li>`).join("")}</ul></div>
          <div class="box"><div class="ttl">${T("tpl.services")}</div><ul>${(t.services || []).map((x) => `<li><span class="ld" style="background:var(--c-mcp)"></span><span class="lt">${esc(x.name)}${x.required ? "" : ` <span class="k">${T("cat.optional")}</span>`}</span></li>`).join("")}</ul></div>
          <div class="box"><div class="ttl">${T("tpl.sources")}</div><ul>${(t.sources || []).map((x) => `<li><span class="ld" style="background:var(--c-wiki)"></span><span class="lt">${esc(T("data.origin." + x))}</span></li>`).join("")}</ul></div></div>
        <div class="grid2 mt12"><div class="box"><div class="ttl">${T("tpl.apis")}</div><div class="mono small">${(t.apis || []).map(esc).join("<br>") || "-"}</div></div>
          <div class="box"><div class="ttl">${T("tpl.iam")}</div><div class="mono small">${(t.iam || []).map(esc).join("<br>") || "-"}</div></div></div>
        ${t.identity && t.identity.note ? `<div class="note">${esc(t.identity.note)}</div>` : ""}
        ${(t.warnings || []).length ? `<div class="note warn">${t.warnings.map(esc).join(" · ")}</div>` : ""}
        ${t.setup_script ? `<div class="card-head mt16"><h3>${T("tpl.script")}</h3><span class="right"><button class="btn small" data-act="dl-tpl-script">${T("common.download")}</button></span></div>${codeBlock(t.setup_script)}` : ""}</div>`;
    }
    return `<div class="card"><div class="card-head"><h3>${T("tpl.title")}</h3><span class="sub">${T("tpl.sub")}</span></div>
      ${S.tpl.flow ? "" : `<div class="note warn">${T("tpl.needFlow")} <a class="btn small" href="#/scenario">${T("rail.scenario")}</a></div>`}
      ${c ? `<div class="sel-grid two">${tg}</div>` : S.ui.catErr ? errNote(S.ui.catErr) : `<div class="empty">${T("common.loading")}</div>`}
      <div class="form-actions"><button class="btn primary" data-act="tpl-compose" ${!S.tpl.flow || S.busy.tpl ? "disabled" : ""}>${S.busy.tpl ? T("common.loading") : T("tpl.compose")}</button>
        ${t && t.flow ? `<span class="st">${statusDot("ok")}<b>${esc(T("tpl.ready", { f: t.flow.id, n: (t.stages || []).length }))}</b></span>` : ""}</div>
      ${S.ui.tplErr ? errNote(S.ui.tplErr) : ""}${prev}</div>`;
  }

  // 2 env
  PAGES.env = () => {
    const e = S.env, info = S.identInfo, chk = S.check;
    const userCmd = "gcloud auth print-access-token";
    const saCmd = `gcloud auth print-access-token --impersonate-service-account=${S.sa || "aos-starter@" + (e.project || "PROJECT") + ".iam.gserviceaccount.com"}`;
    const mode = (m, t, d) => `<button class="sel ${S.identMode === m ? "on" : ""}" data-act="ident-mode" data-mode="${m}"><span class="check"></span><div class="top"><span class="ttl">${T(t)}</span></div><div class="desc">${T(d)}</div></button>`;
    const fld = (k, lab, help) => `<div class="field"><label>${T(lab)}</label><input data-bind="env.${k}" value="${esc(e[k] || "")}" ${k === "dataset" ? `placeholder="aos_${esc((S.draftId || "").replace("ws-", "").replace(/-/g, "_"))}"` : ""}>${help ? `<span class="help">${T(help)}</span>` : ""}</div>`;
    return head(T("rail.g.build"), T("env.title"), T("env.lead")) + templateCard() + `
    <div class="card"><div class="card-head"><h3>${T("env.idTitle")}</h3></div>
      <div class="modes">${mode("runtime", "env.idRuntime", "env.idRuntimeD")}${mode("token", "env.idToken", "env.idTokenD")}${mode("impersonate", "env.idSa", "env.idSaD")}</div>
      ${S.identMode === "token" ? `<div class="field mt12"><label>${T("env.tokenLabel")}</label><textarea class="ta" id="tok" rows="2" spellcheck="false">${esc(token())}</textarea>
        <span class="help">${T("env.tokenHelp")}</span>
        <div class="cmd"><span class="tag">${T("env.cmdUser")}</span><code>${esc(userCmd)}</code><button class="btn small" data-act="copy" data-text="${esc(userCmd)}">${T("common.copy")}</button></div>
        <div class="cmd"><span class="tag">${T("env.cmdSa")}</span><code>${esc(saCmd)}</code><button class="btn small" data-act="copy" data-text="${esc(saCmd)}">${T("common.copy")}</button></div></div>` : ""}
      ${S.identMode === "impersonate" ? `<div class="field mt12"><label>${T("env.saLabel")}</label><input data-bind="sa" value="${esc(S.sa)}" placeholder="aos-starter@PROJECT.iam.gserviceaccount.com">
        ${S.boot && !S.boot.impersonation ? `<div class="note warn">${T("env.saDisabled")}</div>` : ""}</div>` : ""}
      ${S.identMode === "runtime" ? `<div class="note">${T("env.demoNote", { p: esc(((S.boot && S.boot.env_defaults) || {}).project || "") })}</div>` : ""}
      <div class="form-actions"><button class="btn" data-act="verify-id">${T("env.verifyId")}</button>
        ${info ? `<span class="st">${statusDot("ok")}<b>${esc(T("env.idOk", { p: info.principal || "-" }))}</b>${info.expires_in ? " · " + esc(T("env.idExpires", { m: Math.round(info.expires_in / 60) })) : ""}</span>` : ""}
        ${S.ui.idError ? `<span class="st">${statusDot("error")}${esc(S.ui.idError)}</span>` : ""}</div></div>
    <div class="card"><div class="card-head"><h3>${T("env.resTitle")}</h3></div><div class="form">
      ${fld("project", "env.fProject")}${fld("region", "env.fRegion")}${fld("bucket", "env.fBucket")}${fld("dataset", "env.fDataset", "env.fDatasetHelp")}
      ${fld("graph_name", "env.fGraph")}${fld("model", "env.fModel")}</div>
      <div class="form-actions"><button class="btn primary" data-act="check" ${S.busy.check ? "disabled" : ""}>${S.busy.check ? T("env.checking") : T("env.check")}</button>
        <button class="btn" data-act="script">${T("env.script")}</button>
        ${chk ? `<span class="st">${statusDot(chk.status === "OK" ? "ok" : "error")}<b>${chk.status === "OK" ? T("env.checkOk") : T("env.checkFail", { n: chk.errors })}</b></span>` : ""}</div>
      ${chk ? `<div class="checks mt12">${chk.checks.map((c) => `<div class="check-row">${statusDot(c.status)}<div><div class="l1"><span class="lbl">${esc(c.label)}</span></div><div class="det">${esc(c.detail)}</div>
        ${c.fix && c.status !== "ok" ? `<div class="fix">${T("env.fix")}<code>${esc(c.fix)}</code></div>` : ""}</div><div class="api">${c.ms ? esc(T("common.ms", { n: c.ms })) : ""}</div></div>`).join("")}</div>` : ""}
      ${S.ui.script ? `<div class="mt16"><div class="card-head"><h3>${T("env.scriptTitle")}</h3><span class="sub">${T("env.scriptSub")}</span><span class="right"><button class="btn small" data-act="dl-script">${T("common.download")}</button></span></div>${codeBlock(S.ui.script)}</div>` : ""}
    </div>
    <div class="step-nav"><a class="btn" href="#/scenario">${T("common.prev")}</a><span class="spacer"></span><a class="btn primary" href="#/data">${T("common.next")}</a></div>`;
  };
  AFTER.env = () => { ensureCatalog(); };

  // 3 data
  PAGES.data = () => {
    const tab = S.ui.dtab || "sample";
    const dt = dataType();
    const src = (x, kind, i) => `<div class="src"><span class="tag">${T("data.origin." + x.origin)}</span><div class="nm">${esc(x.name)} <div class="uri">${esc(x.uri || x.fq || "")}</div></div>
      <span class="meta">${kind === "doc" ? (x.chars ? x.chars.toLocaleString() + " chars" : "") : (x.rows ? T("common.rows", { n: x.rows }) : "")}</span>
      <button class="btn small danger" data-act="src-del" data-kind="${kind}" data-i="${i}">${T("common.delete")}</button></div>`;
    const tabs = ["sample", "upload", "gcs", "drive", "bq"];
    const tk = { sample: "data.tabSample", upload: "data.tabUpload", gcs: "data.tabGcs", drive: "data.tabDrive", bq: "data.tabBq" };
    let body = "";
    if (tab === "sample") {
      const sm = (S.boot && S.boot.sample) || { docs: [], tables: [] };
      body = `<p class="muted">${T("data.sampleD")}</p><div class="cols3"><div class="box"><div class="ttl">${T("data.docs")}</div><ul>${sm.docs.map((d) => `<li>${esc(d.name)}</li>`).join("")}</ul></div>
        <div class="box"><div class="ttl">${T("data.tables")}</div><ul>${sm.tables.map((t) => `<li>${esc(t.name)} <span class="k">${T("common.rows", { n: t.rows })}</span></li>`).join("")}</ul></div></div>
        <div class="form-actions"><button class="btn primary" data-act="add-sample">${T("data.sampleAdd")}</button></div>`;
    } else if (tab === "upload") {
      const acc = ((S.boot && S.boot.upload_ext) || [".md", ".markdown", ".txt", ".csv"]).join(",");
      body = `<div class="drop" id="drop">${T("data.uploadD", { b: esc(S.env.bucket || ""), w: esc(S.draftId) })}<div class="meta mt8">${esc(T("data.uploadTypes", { m: Math.round(((S.boot && S.boot.max_upload_bytes) || 0) / 1048576) }))}</div>
        <div class="mt12"><label class="btn"><input type="file" id="file-in" multiple accept="${esc(acc)}" hidden>${T("data.uploadPick")}</label>
        <label class="small muted"><input type="checkbox" id="pdf-gemini" ${S.ui.pdfMode === "baseline" ? "" : "checked"}> ${T("data.pdfGemini")}</label></div>
        ${S.ui.upMsg ? `<div class="mt8 meta">${esc(S.ui.upMsg)}</div>` : ""}</div>`;
    } else if (tab === "gcs") {
      const r = S.ui.gcs;
      body = `<p class="muted">${T("data.gcsD")}</p><div class="flex"><input class="grow mono" style="height:34px;border:1px solid var(--line-2);border-radius:10px;padding:0 10px" id="gcs-uri" value="${esc(S.ui.gcsUri || "gs://" + (S.env.bucket || "") + "/")}"><button class="btn" data-act="gcs-list">${T("data.gcsList")}</button></div>
        ${r ? (r.status !== "SUCCESS" ? errNote(r) : `<div class="pick">${[...r.docs.map((d) => ["doc", d]), ...r.tables.map((t) => ["table", t])].map(([k, x], i) => `<label><input type="checkbox" data-pick="${i}" checked> <span class="tag">${k === "doc" ? T("data.docs") : T("data.tables")}</span>${x.convert ? ` <span class="tag mcp">${T("data.willConvert")}</span>` : ""} ${esc(x.name)} <span class="mono">${esc(x.uri)}</span></label>`).join("") || `<div class="empty">${T("common.none")}</div>`}</div>
        <div class="form-actions"><button class="btn primary" data-act="gcs-add" ${S.busy.conv ? "disabled" : ""}>${T("data.addSel")}</button>${S.ui.convMsg ? `<span class="meta">${esc(S.ui.convMsg)}</span>` : ""}</div>`) : ""}`;
    } else if (tab === "drive") {
      const r = S.ui.drive;
      body = `<p class="muted">${T("data.driveD")}</p><div class="flex"><input class="grow mono" style="height:34px;border:1px solid var(--line-2);border-radius:10px;padding:0 10px" id="drive-url" placeholder="https://drive.google.com/drive/folders/..." value="${esc(S.ui.driveUrl || "")}"><button class="btn" data-act="drive-list">${T("data.driveList")}</button></div>
        ${driveHelp()}
        ${r ? (r.status !== "OK" ? errNote(r) : `<div class="pick">${r.files.map((f, i) => `<label class="${f.kind === "folder" || f.kind === "other" ? "off" : ""}"><input type="checkbox" data-pick="${i}" ${f.kind === "folder" || f.kind === "other" ? "disabled" : "checked"}> <span class="tag">${esc(T("data.dkind." + f.kind))}</span> ${esc(f.name)} <span class="mono">${esc(f.mimeType || "")}</span></label>`).join("") || `<div class="empty">${T("common.none")}</div>`}</div>
        <div class="form-actions"><button class="btn primary" data-act="drive-add" ${S.busy.conv ? "disabled" : ""}>${T("data.addSel")}</button>${S.ui.convMsg ? `<span class="meta">${esc(S.ui.convMsg)}</span>` : ""}</div>`) : ""}`;
    } else {
      const r = S.ui.bq;
      body = `<p class="muted">${T("data.bqD")}</p><div class="flex"><input class="grow mono" style="height:34px;border:1px solid var(--line-2);border-radius:10px;padding:0 10px" id="bq-ds" value="${esc(S.ui.bqDs || (S.env.project || "") + ".")}"><button class="btn" data-act="bq-list">${T("data.bqList")}</button></div>
        ${r ? (r.status !== "SUCCESS" ? `<div class="note err">${esc(r.error || r.message)}</div>` : `<div class="pick">${r.tables.map((t, i) => `<label><input type="checkbox" data-pick="${i}"> ${esc(t.name)} <span class="mono">${esc(t.fq)}</span></label>`).join("") || `<div class="empty">${T("common.none")}</div>`}</div>
        <div class="form-actions"><button class="btn primary" data-act="bq-add">${T("data.addSel")}</button></div>`) : ""}`;
    }
    return head(T("rail.g.build"), T("data.title"), T("data.lead")) + `
    <div class="card"><div class="card-head"><h3>${T("data.selected")}</h3>${dt ? `<span class="pill-p">${dt}</span><span class="sub">${T("data." + dt.toLowerCase())}</span>` : ""}</div>
      ${!S.sources.docs.length && !S.sources.tables.length ? `<div class="empty">${T("data.empty")}</div>` : `<div class="grid2"><div><div class="eyebrow">${T("data.docs")} · ${S.sources.docs.length}</div><div class="srclist mt8">${S.sources.docs.map((d, i) => src(d, "doc", i)).join("")}</div></div>
      <div><div class="eyebrow">${T("data.tables")} · ${S.sources.tables.length}</div><div class="srclist mt8">${S.sources.tables.map((t, i) => src(t, "table", i)).join("")}</div></div></div>`}</div>
    <div class="card"><div class="tabs">${tabs.map((t) => `<button class="${tab === t ? "on" : ""}" data-act="dtab" data-t="${t}">${T(tk[t])}</button>`).join("")}</div>
      ${tab !== "sample" && S.identMode === "runtime" && !S.identInfo ? `<div class="note">${T("data.needEnv")}</div>` : ""}${body}</div>
    ${conversionCard()}
    <div class="step-nav"><a class="btn" href="#/env">${T("common.prev")}</a><span class="spacer"></span><a class="btn primary" href="#/${S.sources.docs.length ? "types" : "build"}">${T("common.next")}</a></div>`;
  };
  function conversionCard() {
    const conv = S.sources.docs.map((d, i) => [d, i]).filter(([d]) => d.conversion);
    if (!conv.length) return "";
    const rows = conv.map(([d, i]) => {
      const c = d.conversion, st = c.structure || {}, prev = S.previews[d.uri];
      return `<tr><td><b>${esc(d.name)}</b><div class="meta mono">${esc(c.source_ext || "")} · ${esc(T("data.origin." + d.origin))}</div></td>
        <td class="mono small">${esc(c.method || "")}</td>
        <td><span class="st">${statusDot(gradeCls(c.grade))}<b>${esc(pct(c.fidelity))}</b> <span class="tag">${esc(c.grade || "-")}</span></span><div class="meta">${esc(T("conv.recall", { t: pct(c.token_recall), n: pct(c.number_recall) }))}</div></td>
        <td class="num">${c.pages != null ? esc(c.pages) : "-"}</td>
        <td class="meta">${esc(T("conv.structure", { h: st.headings || 0, t: st.tables || 0, l: st.list_items || 0 }))}</td>
        <td>${d.kind ? `<span class="tag">${esc(T("types.t." + d.kind))}</span>` : ""}${d.strategy ? ` <span class="tag strat-${esc(d.strategy)}">${esc(T("types.s." + d.strategy))}</span>` : ""}</td>
        <td class="nowrap">${c.pdf ? `<a class="btn small" href="${esc(gsHttp(c.pdf))}" target="_blank" rel="noopener">PDF</a>` : ""} <a class="btn small" href="${esc(gsHttp(d.uri))}" target="_blank" rel="noopener">MD</a></td></tr>
        ${(c.notes || []).length ? `<tr class="sub"><td colspan="7" class="meta">${c.notes.map(esc).join(" · ")}</td></tr>` : ""}
        ${prev ? `<tr class="sub"><td colspan="7"><details class="fold"><summary>${T("conv.preview")}</summary><div class="inner md conv-md">${md(prev)}</div></details></td></tr>` : ""}`;
    }).join("");
    const avg = conv.reduce((a, [d]) => a + (Number(d.conversion.fidelity) || 0), 0) / conv.length;
    return `<div class="card"><div class="card-head"><h3>${T("conv.title")} · ${conv.length}</h3><span class="sub">${esc(T("conv.sub", { a: pct(avg) }))}</span>
      <span class="right"><a class="btn small primary" href="#/types">${T("conv.toTypes")}</a></span></div>
      <div class="tbl-wrap"><table class="tbl conv"><thead><tr><th>${T("conv.doc")}</th><th>${T("conv.method")}</th><th>${T("conv.fidelity")}</th><th>${T("conv.pages")}</th><th>${T("conv.struct")}</th><th>${T("conv.type")}</th><th></th></tr></thead><tbody>${rows}</tbody></table></div>
      <div class="note">${T("conv.legend")}</div></div>`;
  }
  AFTER.data = () => {
    const fin = $("#file-in"), drop = $("#drop");
    if (fin) fin.addEventListener("change", () => uploadFiles(fin.files));
    const pg = $("#pdf-gemini");
    if (pg) pg.addEventListener("change", () => { S.ui.pdfMode = pg.checked ? "auto" : "baseline"; });
    if (drop) {
      drop.addEventListener("dragover", (e) => { e.preventDefault(); drop.classList.add("over"); });
      drop.addEventListener("dragleave", () => drop.classList.remove("over"));
      drop.addEventListener("drop", (e) => { e.preventDefault(); drop.classList.remove("over"); uploadFiles(e.dataTransfer.files); });
    }
  };
  async function uploadFiles(files) {
    const list = Array.from(files || []);
    let n = 0;
    for (const f of list) {
      S.ui.upMsg = T("data.uploading", { n: f.name });
      rerender();
      const b64 = await new Promise((res) => { const r = new FileReader(); r.onload = () => res(String(r.result).split(",")[1] || ""); r.readAsDataURL(f); });
      const max = (S.boot && S.boot.max_upload_bytes) || 0;
      if (max && f.size > max) { toast(T("data.tooBig", { n: f.name, m: Math.round(max / 1048576) }), 5000); continue; }
      const j = await api("/api/v5/upload", { env: S.env, ws_id: S.draftId, name: f.name, content_base64: b64, pdf_mode: S.ui.pdfMode || "auto" });
      if (j.status === "OK") { addIntake(j); n += 1; } else { errToast(j, f.name); }
    }
    S.ui.upMsg = T("data.uploaded", { n });
    save();
    rerender();
  }

  function addIntake(j) {
    // one upload / conversion / Drive import result → selected sources (converted docs replace an earlier entry for the same file)
    const e = j.entry;
    if (!e) return;
    const list = j.kind === "table" ? S.sources.tables : S.sources.docs;
    const at = list.findIndex((x) => x.uri === e.uri);
    if (at >= 0) list.splice(at, 1, e); else list.push(e);
    (j.tables || []).forEach((t) => { if (!S.sources.tables.some((x) => x.uri === t.uri)) S.sources.tables.push(t); });
    if (j.markdown_preview) S.previews[e.uri] = j.markdown_preview;
    S.types = null;
  }
  async function convertMany(items, call) {
    S.busy.conv = true;
    let n = 0;
    for (const x of items) {
      S.ui.convMsg = T("data.converting", { n: x.name }); rerender();
      const j = await call(x);
      if (j.status === "OK") { addIntake(j); n += 1; } else { errToast(j, x.name); if (j.status === "MCP_UPDATE_NEEDED") break; }
    }
    S.busy.conv = false; S.ui.convMsg = T("data.uploaded", { n }); save(); rerender();
  }

  // 4 types
  PAGES.types = () => {
    const docs = S.sources.docs;
    const r = S.types;
    if (!docs.length) return head(T("rail.g.build"), T("types.title"), T("types.lead")) + `<div class="card"><div class="empty">${T("types.noDocs")}</div></div>
      <div class="step-nav"><a class="btn" href="#/data">${T("common.prev")}</a><span class="spacer"></span><a class="btn primary" href="#/build">${T("common.next")}</a></div>`;
    const typeIds = ((r && r.types) || []).map((x) => x.id);
    const opts = (cur) => (typeIds.length ? typeIds : ["policy", "manual", "faq", "contract", "report", "slides", "spreadsheet", "dialogue", "spec", "notice", "other"])
      .map((id) => `<option value="${esc(id)}" ${cur === id ? "selected" : ""}>${esc(T("types.t." + id))}</option>`).join("");
    const byUri = {};
    ((r && r.documents) || []).forEach((x) => { byUri[x.uri] = x; });
    const rows = docs.map((d, i) => {
      const x = byUri[d.uri] || {};
      const dec = (S.ui.typeDec || {})[d.uri] || {};
      const type = dec.type || x.type || d.kind || "";
      const strat = dec.strategy || x.strategy || d.strategy || "";
      const ask = x.ask && !dec.type;
      const conv = d.conversion || {};
      return `<tr class="${ask ? "ask" : ""}"><td><b>${esc(d.name)}</b><div class="meta">${esc(T("data.origin." + d.origin))}${conv.fidelity != null ? " · " + esc(T("types.fid", { f: pct(conv.fidelity) })) : ""}</div></td>
        <td><select data-tdec="${i}" data-f="type"><option value="">-</option>${opts(type)}</select>${x.method ? `<div class="meta">${esc(T("types.method." + (x.method === "rules+llm" ? "llm" : x.method)))}${x.confidence != null ? " · " + pct(x.confidence) : ""}</div>` : ""}
          ${ask ? `<div class="ask-chip">${T("types.ask")}</div>` : ""}</td>
        <td><select data-tdec="${i}" data-f="strategy"><option value="">-</option>${STRATEGIES.map((s2) => `<option value="${s2}" ${strat === s2 ? "selected" : ""}>${esc(T("types.s." + s2))}</option>`).join("")}</select>
          ${x.reason ? `<div class="meta">${esc(x.reason)}</div>` : ""}</td>
        <td class="meta">${x.guide ? `<details class="fold"><summary>${T("types.guide")}</summary><div class="inner">${esc(x.guide)}</div></details>` : ""}
          ${strat === "reconvert" && /^gs:\/\//.test(conv.source || "") ? `<button class="btn small" data-act="reconvert" data-i="${i}" ${S.busy.conv ? "disabled" : ""}>${T("types.reconvert")}</button>` : ""}</td></tr>`;
    }).join("");
    const sm = r && r.summary;
    return head(T("rail.g.build"), T("types.title"), T("types.lead")) + `
    <div class="card"><div class="card-head"><h3>${T("types.auto")}</h3><span class="sub">${T("types.autoD")}</span>
      <span class="right"><label class="small muted"><input type="checkbox" id="cls-llm" ${S.ui.clsLlm ? "checked" : ""}> ${T("types.useLlm")}</label>
      <button class="btn primary" data-act="classify" ${S.busy.cls ? "disabled" : ""}>${S.busy.cls ? T("types.classifying") : T("types.run")}</button></span></div>
      ${S.ui.clsErr ? errNote(S.ui.clsErr) : ""}
      ${r && r.question ? `<div class="note"><b>${esc(r.question.text)}</b></div>` : ""}
      ${sm ? `<div class="flex mt8">${STRATEGIES.map((k) => `<span class="tag strat-${k}">${esc(T("types.s." + k))} <b>${sm[k] || 0}</b></span>`).join("")}</div>` : ""}
      <div class="tbl-wrap mt12"><table class="tbl types"><thead><tr><th>${T("conv.doc")}</th><th>${T("types.type")}</th><th>${T("types.strategy")}</th><th></th></tr></thead><tbody>${rows}</tbody></table></div>
      <div class="note">${T("types.legend")}</div>
      <div class="form-actions"><button class="btn primary" data-act="types-save" ${S.busy.cls ? "disabled" : ""}>${T("types.save")}</button>
        ${typesDone() ? `<span class="st">${statusDot("ok")}<b>${T("types.saved")}</b></span>` : ""}</div></div>
    <div class="step-nav"><a class="btn" href="#/data">${T("common.prev")}</a><span class="spacer"></span><a class="btn primary" href="#/build">${T("common.next")}</a></div>`;
  };
  AFTER.types = () => {
    document.querySelectorAll("[data-tdec]").forEach((el) => el.addEventListener("change", () => {
      const d = S.sources.docs[+el.dataset.tdec];
      S.ui.typeDec = S.ui.typeDec || {};
      const cur = S.ui.typeDec[d.uri] || (S.ui.typeDec[d.uri] = {});
      cur[el.dataset.f] = el.value;
    }));
    const cb = $("#cls-llm");
    if (cb) cb.addEventListener("change", () => { S.ui.clsLlm = cb.checked; });
  };
  function typeDecisions() {
    const byUri = {};
    ((S.types && S.types.documents) || []).forEach((x) => { byUri[x.uri] = x; });
    return S.sources.docs.map((d) => {
      const x = byUri[d.uri] || {}, dec = (S.ui.typeDec || {})[d.uri] || {};
      return { uri: d.uri, name: d.name, type: dec.type || x.type || d.kind || "", strategy: dec.strategy || x.strategy || d.strategy || "",
        confidence: dec.type ? 1 : x.confidence, method: dec.type || dec.strategy ? "user" : x.method || "" };
    }).filter((x) => x.type && x.strategy);
  }

  // 5 build
  PAGES.build = () => {
    const e = S.env;
    const ds = e.dataset || "aos_" + (S.draftId || "").replace("ws-", "").replace(/-/g, "_");
    const rows = STAGES.map((k) => {
      const s = stageOf(k) || {};
      const status = S.busy.stage === k ? "running" : s.stale ? "warn" : s.status || "idle";
      return `<li>${statusDot(status)}<div><div class="t">${T("build.s." + k)} ${s.stale ? `<span class="tag">${T("common.status.stale")}</span>` : ""}</div><div class="d">${T("build.s." + k + ".d")}</div>
        ${s.summary ? `<div class="sum">${esc(JSON.stringify(s.summary)).slice(0, 420)}</div>` : ""}${s.error ? `<div class="err">${esc(s.error)}</div>` : ""}</div>
        <div class="acts">${s.ms ? `<span class="meta">${(s.ms / 1000).toFixed(1)} s · MCP ${s.mcp_calls || 0}</span>` : ""}<button class="btn small" data-act="run-stage" data-stage="${k}" ${S.busy.build ? "disabled" : ""}>${s.status ? T("common.rerun") : T("common.run")}</button></div></li>`;
    }).join("");
    const allDone = STAGES.every((k) => { const s = stageOf(k); return s && (s.status === "done" || s.status === "skipped"); });
    return head(T("rail.g.build"), T("build.title"), T("build.lead")) + `
    <div class="card"><div class="card-head"><h3>${T("build.target")}</h3><span class="right"><button class="btn primary" data-act="run-all" ${S.busy.build ? "disabled" : ""}>${built() ? T("build.runFrom") : T("build.runAll")}</button></span></div>
      <div class="flex small"><span class="tag mono">gs://${esc(e.bucket)}/aos/${esc(S.wsId || S.draftId)}/</span><span class="tag mono">${esc(e.project)}.${esc(ds)}</span><span class="tag mono">${esc(e.graph_name)}</span>
      <span class="tag">${esc(T("id." + S.identMode))}${S.identInfo ? " · " + esc(S.identInfo.principal) : ""}</span>${dataType() ? `<span class="pill-p">${dataType()}</span>` : ""}</div>
      ${allDone ? `<div class="note mt12"><b>${T("build.done")}</b> <a class="btn small primary" href="#/studio/agents">${T("build.toAgent")}</a> <a class="btn small" href="#/studio/overview">${T("build.toStudio")}</a> <a class="btn small dark" href="#/deploy">${T("build.toDeploy")}</a></div>` : ""}
      ${S.template && S.template.flow ? `<div class="flex small mt8"><span class="tag">${esc(T("build.tpl", { f: S.template.flow.title }))}</span><span class="tag">${esc(T("tpl.target." + S.template.target))}</span></div>` : ""}
      <ul class="stage-list mt12">${rows}</ul></div>
    <div class="card"><div class="card-head"><h3>${T("build.log")}</h3></div><div class="stream" id="stream">${S.log.length ? S.log.map(logLine).join("") : `<div class="mc">${T("build.logEmpty")}</div>`}</div></div>`;
  };
  AFTER.build = () => { const el = $("#stream"); if (el) el.scrollTop = el.scrollHeight; };
  function logLine(ev) {
    const ts = new Date(ev._t || Date.now()).toTimeString().slice(0, 8);
    if (ev.type === "stage") return `<div><span class="lv">${ts}</span><span class="stg ${ev.status === "error" ? "er" : ev.status === "done" ? "ok" : ""}">== ${esc(ev.label)} · ${esc(T("common.status." + ev.status))}${ev.ms ? " · " + (ev.ms / 1000).toFixed(1) + " s" : ""}${ev.error ? " · " + esc(ev.error) : ""}</span></div>`;
    if (ev.type === "step") return `<div><span class="lv">${ts}</span><span class="${ev.status === "error" ? "er" : ev.status === "done" ? "ok" : ""}">${esc(ev.label)}${ev.detail ? " — " + esc(ev.detail) : ""}${ev.ms != null ? ` (${ev.ms} ms)` : ""}</span></div>`;
    if (ev.type === "mcp") return `<div><span class="lv">${ts}</span><span class="mc">mcp ${esc(ev.tool)} · ${esc(ev.status)} · ${ev.ms} ms${ev.error ? " · " + esc(ev.error.slice(0, 160)) : ""}</span></div>`;
    if (ev.type === "cq") return `<div><span class="lv">${ts}</span><span class="verdict-${esc(ev.verdict)}">${esc(ev.id)} [${esc(ev.agent)}] ${esc(ev.verdict)} ${ev.score}</span> <span class="mc">${esc((ev.question || "").slice(0, 90))}</span></div>`;
    if (ev.type === "error" || ev.type === "warn") return `<div><span class="lv">${ts}</span><span class="er">${esc(ev.message || ev.status)}</span></div>`;
    return "";
  }
  function pushLog(ev) {
    ev._t = Date.now();
    S.log.push(ev);
    if (S.log.length > 800) S.log.splice(0, S.log.length - 800);
    const el = $("#stream");
    if (el && S.route === "build") { if (S.log.length === 1) el.innerHTML = ""; el.insertAdjacentHTML("beforeend", logLine(ev)); el.scrollTop = el.scrollHeight; }
  }
  async function ensureWs() {
    if (!S.scenario.objective) { toast(T("build.needObjective")); go("scenario"); return false; }
    if (!dataType()) { toast(T("build.needData")); go("data"); return false; }
    if (!S.wsCreated) {
      pushLog({ type: "step", status: "running", label: T("build.create") });
      const j = await api("/api/v5/ws/create", { ws_id: S.draftId, scenario: S.scenario, env: S.env, sources: S.sources, template: templateSpec() });
      if (j.status !== "OK") { pushLog({ type: "error", message: j.message || j.status }); toast(j.message || j.status, 6000); return false; }
      S.ws = j.ws; S.wsId = j.ws.ws_id; S.wsCreated = true; S.env = Object.assign({}, S.env, { dataset: j.ws.env.dataset });
      save();
    } else {
      const j = await api("/api/v5/ws/update", { ws: wsRef(), scenario: S.scenario, sources: S.sources, template: templateSpec() });
      if (j.status === "OK") S.ws = j.ws;
    }
    return true;
  }
  async function runStage(stage) {
    S.busy.stage = stage;
    rerender();
    let ok = true;
    await stream("/api/v5/build", { ws: wsRef(), stage }, (ev) => {
      if (ev.type === "result") { S.ws = ev.ws; ok = ev.record && ev.record.status !== "error"; S.dataFor = ""; }
      else if (ev.type === "error") { ok = false; pushLog(ev); }
      else pushLog(ev);
      if (ev.type === "stage" && ev.status !== "running") { const tmp = S.busy.stage; rail(); S.busy.stage = tmp; }
    });
    S.busy.stage = "";
    save();
    rerender();
    return ok;
  }
  async function runAll(only) {
    if (S.busy.build) return;
    S.busy.build = true;
    rerender();
    try {
      if (!(await ensureWs())) return;
      for (const k of only ? [only] : STAGES) {
        const s = stageOf(k);
        if (!only && s && (s.status === "done" || s.status === "skipped") && !s.stale) continue;
        if (!(await runStage(k))) break;
      }
    } finally { S.busy.build = false; S.busy.stage = ""; rerender(); }
  }

  // ------------------------------------------------------------------ studio data
  async function ensureData(what, force) {
    const key = S.wsId;
    if (S.dataFor !== key) { S.data = {}; S.dataFor = key; }
    const need = what.filter((w) => force || !(w in S.data));
    if (!need.length) return;
    const j = await api("/api/v5/data", { ws: wsRef(), what: need });
    if (j.status === "OK") { for (const w of need) S.data[w] = j[w] == null ? null : j[w]; if (j.ws) S.ws = j.ws; }
    else toast(j.message || j.status, 5000);
  }
  function studioPage(what, fn) {
    if (S.dataFor === S.wsId && what.every((w) => w in S.data)) return fn();
    ensureData(what).then(() => { if (PAGES[S.route]) rerender(); });
    return `<div class="card"><div class="empty">${T("common.loading")}</div></div>`;
  }
  const consoleUrl = {
    gcs: (b, p) => `https://console.cloud.google.com/storage/browser/${encodeURIComponent(b)}/${p}`,
    bq: (p, d) => `https://console.cloud.google.com/bigquery?project=${encodeURIComponent(p)}&ws=!1m4!1m3!3m2!1s${encodeURIComponent(p)}!2s${encodeURIComponent(d)}`,
  };

  PAGES["studio/overview"] = () => {
    const w = S.ws || {}, env = w.env || {}, sm = w.summary || {}, sc = w.scope || {};
    const wk = sm.wiki || {}, gr = sm.graph || {}, ev = sm.eval || {};
    const kpi = (k, v, s) => `<div class="kpi"><div class="k">${k}</div><div class="v">${v}</div><div class="s">${s || ""}</div></div>`;
    return head(T("rail.g.studio"), (w.scenario && w.scenario.title) || T("ov.title"), (w.scenario && w.scenario.objective) || T("ov.lead"),
      `<span class="tag mono">${esc(w.ws_id || "")}</span>`) + `
    <div class="kpis">${kpi(T("ov.docs"), sm.docs ?? "-", sm.chars ? sm.chars.toLocaleString() + " chars" : "")}${kpi(T("ov.tables"), sm.tables ?? "-", sm.rows ? T("common.rows", { n: sm.rows.toLocaleString() }) : "")}
      ${kpi(T("ov.wiki"), wk.pages ?? "-", wk.gates_total ? T("ov.gates", { p: wk.gates_passed, t: wk.gates_total }) : "")}
      ${kpi(T("ov.graph"), gr.nodes != null ? `${gr.nodes}N · ${gr.edges}E` : "-", gr.mode ? T("ov.graphMode." + gr.mode) : "")}
      ${kpi(T("ov.cqs"), sm.cqs ?? "-", "")}${kpi(T("ov.eval"), ev.score != null ? ev.score : "-", ev.total ? `${ev.passed}/${ev.total} PASS` : "")}</div>
    <div class="grid2"><div class="card"><div class="card-head"><h3>${T("ov.stages")}</h3><span class="right"><a class="btn small" href="#/build">${T("rail.build")}</a></span></div><ul class="stage-list">
      ${STAGES.map((k) => { const s = stageOf(k) || {}; return `<li>${statusDot(s.stale ? "warn" : s.status || "idle")}<div><div class="t">${T("build.s." + k)}</div><div class="d">${s.at ? esc(s.at) : ""} ${s.identity && s.identity.principal ? " · " + esc(s.identity.principal) : ""}</div></div><div class="meta">${s.ms ? (s.ms / 1000).toFixed(1) + " s" : ""}</div></li>`; }).join("")}</ul></div>
    <div class="card"><div class="card-head"><h3>${T("ov.resources")}</h3></div><div class="box"><ul>
      <li><span class="ld wiki"></span><span class="lt"><a href="${consoleUrl.gcs(env.bucket, "aos/" + w.ws_id + "/")}" target="_blank" rel="noopener">gs://${esc(env.bucket)}/aos/${esc(w.ws_id)}/</a></span></li>
      <li><span class="ld table"></span><span class="lt"><a href="${consoleUrl.bq(env.project, env.dataset)}" target="_blank" rel="noopener">${esc(env.project)}.${esc(env.dataset)}</a></span></li>
      <li><span class="ld concept"></span><span class="lt mono small">${esc(gr.fq || env.project + "." + env.dataset + "." + env.graph_name)}</span></li></ul></div>
      <div class="card-head mt16"><h3>${T("ov.scope")}</h3></div><div class="flex">${sc.data_type ? `<span class="pill-p">${esc(sc.data_type)}</span><span class="wbadge">${esc(sc.question_type)}</span>` : ""}${(sc.agents || []).map((a) => `<span class="tag">${esc(T("ag." + a))}</span>`).join("")}</div>
      ${(sc.fk_candidates || []).length ? `<div class="meta mt8">${T("ov.fk")}: ${sc.fk_candidates.map((f) => esc(`${f.table}.${f.column} → ${f.ref_table}.${f.ref_key}`)).join(" · ")}</div>` : ""}
      ${(sc.warnings || []).length ? `<div class="note warn">${T("ov.warnings")}: ${sc.warnings.map(esc).join(" · ")}</div>` : ""}</div></div>`;
  };

  PAGES["studio/assets"] = () => studioPage(["docs", "tables"], () => {
    const docs = S.data.docs || [], tables = S.data.tables || [];
    const sel = S.ui.asset || (docs[0] ? "d:0" : tables[0] ? "t:0" : "");
    let view = "";
    if (sel.startsWith("d:")) { const d = docs[+sel.slice(2)]; if (d) view = `<div class="card-head"><h3>${esc(d.title)}</h3><span class="tag mono">${esc(d.doc_id)}</span><span class="meta">${esc(d.uri)}</span></div><div class="md">${md(d.text)}</div>`; }
    if (sel.startsWith("t:")) {
      const t = tables[+sel.slice(2)];
      if (t) view = `<div class="card-head"><h3>${esc(t.name)}</h3><span class="tag mono">${esc(t.fq)}</span><span class="meta">${T("common.rows", { n: t.row_count })}</span><span class="right"><button class="btn small" data-act="to-query" data-sql="${esc(`SELECT * FROM \`${t.fq}\` LIMIT 50`)}">${T("as.toQuery")}</button></span></div>
        ${table(t.columns.map((c) => ({ column: c.name, type: c.type, key: c.name === t.pk ? T("as.pk") : "", description: c.description || "" })))}
        <div class="eyebrow mt16">${T("as.sample")}</div><div class="mt8">${table(t.rows, 30)}</div>`;
    }
    return head(T("rail.g.studio"), T("as.title"), T("as.lead")) + `<div class="wk" style="grid-template-columns:260px minmax(0,1fr)"><div class="card tight wk-list">
      <div class="wk-layer">${T("data.docs")}</div>${docs.map((d, i) => `<button class="wk-item ${sel === "d:" + i ? "on" : ""}" data-act="asset" data-id="d:${i}"><div>${esc(d.title)}</div><div class="id">${esc(d.doc_id)}</div></button>`).join("") || `<div class="empty">${T("common.none")}</div>`}
      <div class="wk-layer">${T("data.tables")}</div>${tables.map((t, i) => `<button class="wk-item ${sel === "t:" + i ? "on" : ""}" data-act="asset" data-id="t:${i}"><div>${esc(t.name)}</div><div class="id">${T("common.rows", { n: t.row_count })} · ${T("data.cols", { n: t.columns.length })}</div></button>`).join("") || `<div class="empty">${T("common.none")}</div>`}
      </div><div class="card">${view || `<div class="empty">${T("common.none")}</div>`}</div></div>`;
  });

  // wiki
  function wikiPageView(p, pages) {
    const inc = pages.filter((q) => (q.relations || []).some((r) => r.target === p.id));
    return `<div class="card-head"><span class="ld ${esc(p.layer)}"></span><h2>${esc(p.title)}</h2><span class="tag mono">${esc(p.id)}</span><span class="right"><button class="btn small" data-act="wk-edit">${T("common.edit")}</button></span></div>
      ${p.summary ? `<p class="muted">${esc(p.summary)}</p>` : ""}<div class="md">${md(p.body_md)}</div>
      ${(p.policy || []).length ? `<div class="eyebrow mt16">${T("wk.policy")}</div><div class="mt8">${table(p.policy.map((c) => ({ name: c.name, value: c.value, unit: c.unit })))}</div>` : ""}
      ${(p.relations || []).length ? `<div class="eyebrow mt16">${T("wk.relations")}</div><div class="flex mt8">${p.relations.map((r) => `<button class="tag" data-act="wk-page" data-id="${esc(r.target)}"><b>${esc(r.type)}</b> → ${esc(r.target)}</button>`).join("")}</div>` : ""}
      ${(p.applies_to || []).length ? `<div class="eyebrow mt16">${T("wk.applies")}</div><div class="flex mt8">${p.applies_to.map((a) => `<span class="tag mono">${esc(a.table)}${a.where ? esc(` WHERE ${a.where.column} ${a.where.op || "="} ${JSON.stringify(a.where.value)}`) : ""}</span>`).join("")}</div>` : ""}
      ${(p.sources || []).length ? `<div class="eyebrow mt16">${T("wk.sources")}</div><div class="meta mt8">${p.sources.map((s) => esc(`${s.doc} §${s.section}`)).join(" · ")}</div>` : ""}
      ${inc.length ? `<div class="eyebrow mt16">${T("wk.incoming")}</div><div class="flex mt8">${inc.map((q) => `<button class="tag" data-act="wk-page" data-id="${esc(q.id)}">${esc(q.id)}</button>`).join("")}</div>` : ""}`;
  }
  function wikiEditor(p) {
    const j = (v) => esc(JSON.stringify(v || [], null, 1));
    return `<div class="card-head"><h2>${esc(p.id || T("wk.newPage"))}</h2><span class="right"><button class="btn small" data-act="wk-cancel">${T("common.cancel")}</button><button class="btn small primary" data-act="wk-save">${T("wk.saveValidate")}</button></span></div>
      <div class="form"><div class="field"><label>${T("wk.fId")}</label><input id="we-id" value="${esc(p.id || "")}"></div>
      <div class="field"><label>${T("wk.fLayer")}</label><select id="we-layer">${["summary", "entity", "concept"].map((l) => `<option value="${l}" ${p.layer === l ? "selected" : ""}>${T("wk.layer." + l)}</option>`).join("")}</select></div>
      <div class="field full"><label>${T("wk.fTitle")}</label><input id="we-title" value="${esc(p.title || "")}"></div>
      <div class="field full"><label>${T("wk.fSummary")}</label><input id="we-summary" value="${esc(p.summary || "")}"></div>
      <div class="field full"><label>${T("wk.fBody")}</label><textarea class="ta prose tall" id="we-body">${esc(p.body_md || "")}</textarea></div>
      <div class="field"><label>${T("wk.fPolicy")}</label><textarea class="ta" id="we-policy">${j(p.policy)}</textarea></div>
      <div class="field"><label>${T("wk.fRelations")}</label><textarea class="ta" id="we-relations">${j(p.relations)}</textarea></div>
      <div class="field"><label>${T("wk.fApplies")}</label><textarea class="ta" id="we-applies">${j(p.applies_to)}</textarea></div>
      <div class="field"><label>${T("wk.fSources")}</label><textarea class="ta" id="we-sources">${j(p.sources)}</textarea></div></div>`;
  }
  PAGES["studio/wiki"] = () => studioPage(["wiki", "gates"], () => {
    const pages = S.data.wiki || [];
    if (!pages.length && !S.ui.wkEdit) return head(T("rail.g.studio"), T("wk.title"), T("wk.lead")) + `<div class="card"><div class="empty">${T("wk.empty")}</div></div>`;
    const f = (S.ui.wkFilter || "").toLowerCase();
    const cur = pages.find((p) => p.id === S.ui.wkSel) || pages[0];
    const gates = (S.data.gates && S.data.gates.gates) || [];
    const list = ["summary", "entity", "concept"].map((l) => {
      const ps = pages.filter((p) => p.layer === l && (!f || (p.id + " " + p.title + " " + p.summary).toLowerCase().includes(f)));
      return `<div class="wk-layer"><span class="ld ${l}"></span>${T("wk.layer." + l)} · ${ps.length}</div>` + ps.map((p) => `<button class="wk-item ${cur && cur.id === p.id ? "on" : ""}" data-act="wk-page" data-id="${esc(p.id)}"><div>${esc(p.title)}</div><div class="id">${esc(p.id)}</div></button>`).join("");
    }).join("");
    const stale = stageOf("graph") && stageOf("graph").stale;
    return head(T("rail.g.studio"), T("wk.title"), T("wk.lead"), `<button class="btn" data-act="wk-new">${T("wk.newPage")}</button>`) +
      (stale ? `<div class="note warn">${T("wk.graphStale")} <button class="btn small" data-act="run-stage" data-stage="graph">${T("build.s.graph")}</button></div>` : "") + `
    <div class="wk"><div class="card tight wk-list"><input id="wk-filter" placeholder="${esc(T("wk.filter"))}" value="${esc(S.ui.wkFilter || "")}" style="width:100%;height:30px;border:1px solid var(--line-2);border-radius:9px;padding:0 9px">${list}</div>
      <div class="card">${S.ui.wkEdit ? wikiEditor(S.ui.wkEdit) : cur ? wikiPageView(cur, pages) : ""}</div>
      <div class="card tight"><div class="card-head"><h3>${T("wk.gates")}</h3></div><div class="gates">${gates.map((g) => `<div class="gate">${statusDot(g.ok ? "ok" : g.level === "warn" ? "warn" : "error")}<span class="gid">${esc(g.id)}</span><div><div>${esc(g.name)}</div><div class="gd">${esc(g.detail)}</div></div></div>`).join("")}</div></div></div>`;
  });
  AFTER["studio/wiki"] = () => { const el = $("#wk-filter"); if (el) el.addEventListener("input", () => { S.ui.wkFilter = el.value; rerender(); const n = $("#wk-filter"); n.focus(); n.setSelectionRange(n.value.length, n.value.length); }); };

  // graph
  function graphSvg(schema) {
    const nodes = schema.nodes || [], edges = schema.edges || [];
    const wiki = nodes.filter((n) => n.kind === "wiki"), tabs = nodes.filter((n) => n.kind !== "wiki");
    const W = 200, H = 46, pos = {};
    const RY = 104;
    wiki.forEach((n, i) => { pos[n.label] = [30, 40 + i * RY]; });
    const cols = tabs.length > 4 ? 2 : 1;
    tabs.forEach((n, i) => { pos[n.label] = wiki.length ? [400 + (i % cols) * 360, 40 + Math.floor(i / cols) * RY + (i % cols) * 40] : [30 + (i % 3) * 330, 40 + Math.floor(i / 3) * RY]; });
    const maxY = Math.max(...Object.values(pos).map((p) => p[1])) + 90;
    const width = Math.max(...Object.values(pos).map((p) => p[0])) + W + 40;
    const ep = edges.map((e) => {
      const a = pos[e.from], b = pos[e.to];
      if (!a || !b) return "";
      let d;
      if (e.from === e.to) d = `M${a[0] + W} ${a[1] + 14} c 40 -30 40 40 0 18`;
      else { const x1 = a[0] + (b[0] >= a[0] ? W : 0), y1 = a[1] + H / 2, x2 = b[0] + (b[0] >= a[0] ? 0 : W), y2 = b[1] + H / 2; const mx = (x1 + x2) / 2; d = `M${x1} ${y1} C ${mx} ${y1}, ${mx} ${y2}, ${x2} ${y2}`; }
      const lx = e.from === e.to ? a[0] + W + 30 : (a[0] + b[0]) / 2 + W / 2, ly = e.from === e.to ? a[1] + 4 : (a[1] + b[1]) / 2 + H / 2 - 4;
      return `<g class="gedge ${esc(e.kind === "wiki_bridge" ? "bridge" : e.kind)}"><path d="${d}" marker-end="url(#arr)"/><text x="${lx}" y="${ly}" text-anchor="middle">${esc(e.label)}</text></g>`;
    }).join("");
    const np = nodes.map((n) => { const p = pos[n.label]; return `<g class="gnode ${S.ui.grNode === n.label ? "on" : ""}" data-act="gr-node" data-label="${esc(n.label)}" transform="translate(${p[0]},${p[1]})"><rect width="${W}" height="${H}" rx="10"/><circle cx="14" cy="${H / 2}" r="5" fill="var(--c-${n.kind === "wiki" ? "wiki" : "semantic"})"/><text x="26" y="20">${esc(n.label)}</text><text class="sub" x="26" y="35">${esc(n.source_table || "wiki")} · ${n.properties.length}</text></g>`; }).join("");
    return `<svg width="${width}" height="${maxY}" viewBox="0 0 ${width} ${maxY}"><defs><marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0 0 L10 5 L0 10z" fill="#9aa0ad"/></marker></defs>${ep}${np}</svg>`;
  }
  PAGES["studio/graph"] = () => studioPage(["graph"], () => {
    const plan = S.data.graph;
    if (!plan || !plan.schema) return head(T("rail.g.studio"), T("gr.title"), T("gr.lead")) + `<div class="card"><div class="empty">${T("gr.empty")}</div></div>`;
    const sch = plan.schema;
    const node = (sch.nodes || []).find((n) => n.label === S.ui.grNode);
    const presets = [...(plan.verify || []).map((v) => ({ t: v.title, sql: v.sql })),
      ...(sch.nodes || []).map((n) => ({ t: `${T("gr.node")} · ${n.label}`, sql: `SELECT * FROM \`${n.table}\` LIMIT 50` }))];
    const q = S.ui.grSql != null ? S.ui.grSql : (presets[0] && presets[0].sql) || "";
    const r = S.ui.grRes;
    return head(T("rail.g.studio"), T("gr.title"), T("gr.lead")) + `
    <div class="card"><div class="card-head"><h3>${T("gr.schema")}</h3>${plan.graph_ready ? `<span class="st">${statusDot("ok")}${esc(T("gr.ready", { g: sch.graph }))}</span>` : `<span class="st">${statusDot("warn")}${esc(T("gr.sqlMode", { e: (plan.graph_error || "").slice(0, 160) }))}</span>`}</div>
      <div class="graph-wrap">${graphSvg(sch)}</div>
      ${node ? `<div class="stepcard"><div class="h"><span class="ld ${node.kind === "wiki" ? "wiki" : "table"}"></span>${esc(node.label)} <span class="tag mono">${esc(node.table)}</span><span class="right"><button class="btn small" data-act="to-query" data-sql="${esc(`SELECT * FROM \`${node.table}\` LIMIT 50`)}">${T("gr.rows")}</button></span></div>
        <div class="meta">${esc(node.description || "")}</div><div class="flex mt8">${node.properties.map((p) => `<span class="tag mono">${esc(p.name)} <b>${esc(p.type)}</b></span>`).join("")}</div></div>` : ""}</div>
    <div class="card console"><div class="card-head"><h3>${T("gr.console")}</h3><span class="right"><select id="gr-preset" style="height:30px;border:1px solid var(--line-2);border-radius:9px;max-width:420px"><option value="">${T("gr.presets")}</option>${presets.map((p, i) => `<option value="${i}">${esc(p.t)}</option>`).join("")}</select></span></div>
      <textarea class="ta" id="gr-sql" spellcheck="false">${esc(q)}</textarea>
      <div class="form-actions"><button class="btn primary" data-act="gr-run" ${S.busy.q ? "disabled" : ""}>${T("gr.run")}</button>
      ${r ? (r.status === "SUCCESS" ? `<span class="st">${statusDot("ok")}${esc(T("gr.result", { n: r.row_count, ms: r.ms }))}</span>` : `<span class="st">${statusDot("error")}${esc((r.error || r.status).slice(0, 300))}</span>`) : ""}</div>
      ${r && r.status === "SUCCESS" ? `<div class="mt12">${table(r.rows, 200)}</div><details class="fold mt12"><summary>${T("gr.call")}</summary><div class="inner">${codeBlock(JSON.stringify(r.call, null, 1))}</div></details>` : ""}</div>
    <div class="grid2"><details class="fold card tight"><summary>${T("gr.ddl")}</summary><div class="inner">${codeBlock([...(plan.statements || []), plan.graph_ddl || {}].filter((x) => x.sql).map((x) => "-- " + x.title + "\n" + x.sql + ";").join("\n\n"))}</div></details>
      <details class="fold card tight"><summary>${T("gr.design")}</summary><div class="inner"><p class="meta">${T("gr.designD")}</p><textarea class="ta tall" id="gr-design" spellcheck="false">${esc(JSON.stringify(plan.design_raw || {}, null, 1))}</textarea>
      <div class="form-actions"><button class="btn" data-act="gr-rebuild" ${S.busy.build ? "disabled" : ""}>${T("gr.rebuild")}</button></div></div></details></div>`;
  });
  AFTER["studio/graph"] = () => {
    const sel = $("#gr-preset");
    if (sel) sel.addEventListener("change", () => {
      const plan = S.data.graph, sch = plan.schema;
      const presets = [...(plan.verify || []).map((v) => v.sql), ...(sch.nodes || []).map((n) => `SELECT * FROM \`${n.table}\` LIMIT 50`)];
      if (sel.value !== "") { S.ui.grSql = presets[+sel.value]; $("#gr-sql").value = S.ui.grSql; }
    });
  };

  // search
  PAGES["studio/search"] = () => {
    const r = S.ui.sr;
    return head(T("rail.g.studio"), T("sr.title"), T("sr.lead")) + `<div class="card"><div class="flex"><input id="sr-q" class="grow" style="height:38px;border:1px solid var(--line-2);border-radius:12px;padding:0 12px;font-size:14px" placeholder="${esc(T("sr.ph"))}" value="${esc(S.ui.srQ || "")}">
      <button class="btn primary big" data-act="sr-go" ${S.busy.sr ? "disabled" : ""}>${T("sr.go")}</button></div></div>
      ${r ? `<div class="grid2"><div class="card"><div class="card-head"><h3>${T("sr.wiki")} · ${r.wiki.length}</h3></div>${r.wiki.map((w) => `<div class="stepcard" data-act="wk-goto" data-id="${esc(w.id)}" style="cursor:pointer"><div class="h"><span class="ld ${esc(w.layer)}"></span>${esc(w.title)} <span class="tag mono">${esc(w.id)}</span></div><div class="meta">${esc(w.snippet)}</div></div>`).join("") || `<div class="empty">${T("sr.none")}</div>`}
        <div class="card-head mt16"><h3>${T("sr.docs")} · ${r.docs.length}</h3></div>${r.docs.map((d) => `<div class="stepcard"><div class="h">${esc(d.doc_id)} · ${esc(d.section)}</div><div class="meta">${esc(d.snippet)}</div></div>`).join("") || `<div class="empty">${T("sr.none")}</div>`}</div>
        <div class="card"><div class="card-head"><h3>${T("sr.tables")} · ${r.tables.length}</h3><span class="meta">${r.ms} ms</span></div>${r.tables.map((t) => `<div class="stepcard"><div class="h">${esc(t.table)} <span class="right"><button class="btn small" data-act="to-query" data-sql="${esc(t.sql)}">${T("as.toQuery")}</button></span></div>${table(t.rows, 5)}</div>`).join("") || `<div class="empty">${T("sr.none")}</div>`}</div></div>` : ""}`;
  };
  AFTER["studio/search"] = () => { const el = $("#sr-q"); if (el) { el.addEventListener("keydown", (e) => { if (e.key === "Enter") ACTIONS["sr-go"](); }); el.focus(); } };

  // agents
  PAGES["studio/agents"] = () => studioPage(["cqs"], () => {
    const ag = S.ui.agent || "hybrid";
    const cqs = (S.data.cqs || []).filter((c) => c.agent === ag);
    const r = S.ui.agRes, live = S.ui.agLive || [];
    const stepHtml = (s) => `<div class="stepcard"><div class="h"><span class="tag">${esc(s.action)}</span>${esc(s.thought || "")}</div>
      ${s.pages ? `<div class="flex">${s.pages.map((p) => `<span class="tag mono">${esc(p)}</span>`).join("")}</div>` : ""}
      ${s.input != null && s.action === "calc" ? `<div class="mono small">${esc(s.input)} = ${esc(s.result)}</div>` : ""}
      ${s.query ? `<pre class="code">${esc(s.query)}</pre>` : ""}${s.error ? `<div class="note err">${esc(s.error)}</div>` : ""}${s.rows ? `<div class="mt8">${table(s.rows, 10)}</div>` : ""}</div>`;
    return head(T("rail.g.studio"), T("ag.title"), T("ag.lead")) + `
    <div class="agent-pick">${["wiki", "graph", "hybrid"].map((a) => `<button class="sel ${ag === a ? "on" : ""}" data-act="ag-pick" data-a="${a}"><span class="check"></span><div class="top"><span class="ttl">${T("ag." + a)}</span></div><div class="desc">${T("ag." + a + "D")}</div></button>`).join("")}</div>
    <div class="ag-wrap"><div><div class="card"><textarea class="ta prose" id="ag-q" rows="3" placeholder="${esc(T("ag.ph"))}">${esc(S.ui.agQ || "")}</textarea>
      <div class="form-actions"><button class="btn primary" data-act="ag-ask" ${S.busy.ag ? "disabled" : ""}>${T("ag.ask")}</button>${r ? `<button class="btn small" data-act="ag-tocq">${T("ag.toCq")}</button>` : ""}</div>
      ${cqs.length ? `<div class="eyebrow mt12">${T("ag.presets")}</div><div class="presets mt8">${cqs.map((c) => `<button class="preset" data-act="ag-preset" data-q="${esc(c.question)}">${esc(c.question)}</button>`).join("")}</div>` : ""}</div>
      ${r ? `<div class="answer mt12"><div class="hd"><span class="st">${statusDot(r.status === "GROUNDED" ? "ok" : r.status === "UNGROUNDED" ? "warn" : "error")}<b>${esc(T("ag.status." + r.status) || r.status)}</b></span><span class="tag">${esc(T("ag." + r.agent))}</span>
        <span class="meta">${r.telemetry ? esc(T("ag.steps", { n: r.telemetry.steps || 0 })) + " · " + ((r.telemetry.total_ms || 0) / 1000).toFixed(1) + " s · " + esc(T("ag.tokens", { i: r.telemetry.tokens_in || 0, o: r.telemetry.tokens_out || 0 })) : ""}</span></div>
        <div class="md">${md(r.answer)}</div>${(r.citations || []).length ? `<div class="flex mt8">${r.citations.map((c) => `<span class="tag mono">${esc(c)}</span>`).join("")}</div>` : ""}</div>` : ""}</div>
    <div class="card"><div class="card-head"><h3>${T("ag.trace")}</h3></div><ul class="trace">${live.map((e) => `<li>${statusDot(e.status)}<span>${esc(e.label)}${e.detail ? " — " + esc(e.detail) : ""}</span><span class="ms">${e.ms != null ? e.ms + " ms" : ""}</span></li>`).join("")}</ul>
      ${r && r.steps ? `<div class="eyebrow mt16">${T("ag.evidence")}</div>${r.steps.filter((s) => s.action !== "answer").map(stepHtml).join("")}` : ""}</div></div>`;
  });

  // eval
  PAGES["studio/eval"] = () => studioPage(["cqs", "run"], () => {
    const cqs = S.ui.cqDraft || S.data.cqs || [];
    const run = S.data.run;
    const res = {};
    ((run && run.results) || []).forEach((x) => { res[x.id] = x; });
    const live = S.ui.evLive || {};
    return head(T("rail.g.studio"), T("ev.title"), T("ev.lead")) + `
    ${run ? `<div class="card"><div class="flex"><div class="score-big">${esc(run.score)}</div><div><div><b>${run.passed}/${run.total} PASS</b> · ${run.partial} PARTIAL</div><div class="meta">${T("ev.latest")} · ${esc(run.at)} · ${(run.ms / 1000).toFixed(0)} s</div></div>
      <span class="spacer grow"></span><div class="flex">${Object.entries(run.by_agent || {}).map(([a, s]) => `<span class="tag">${esc(T("ag." + a))} <b>${s}</b></span>`).join("")}</div></div></div>` : ""}
    <div class="card"><div class="card-head"><h3>${T("ev.cqs")} · ${cqs.length}</h3><span class="right"><button class="btn small" data-act="cq-add">${T("ev.addCq")}</button><button class="btn small" data-act="cq-save">${T("ev.saveCqs")}</button>
      <button class="btn small primary" data-act="ev-run" ${S.busy.ev ? "disabled" : ""}>${T("ev.runAll")}</button></span></div>
      ${cqs.length ? `<div class="tbl-wrap cq-table"><table class="tbl"><thead><tr><th>ID</th><th>${T("ev.q")}</th><th>${T("ev.agent")}</th><th>${T("ev.ref")}</th><th>${T("ev.facts")}</th><th>${T("ev.verdict")}</th><th></th></tr></thead><tbody>
      ${cqs.map((c, i) => { const x = live[c.id] || res[c.id]; return `<tr><td class="mono nowrap">${esc(c.id)}</td><td style="min-width:260px"><textarea data-cq="${i}" data-f="question">${esc(c.question)}</textarea></td>
        <td><select data-cq="${i}" data-f="agent">${["wiki", "graph", "hybrid"].map((a) => `<option value="${a}" ${c.agent === a ? "selected" : ""}>${a}</option>`).join("")}</select></td>
        <td style="min-width:200px"><textarea data-cq="${i}" data-f="reference_answer">${esc(c.reference_answer)}</textarea></td>
        <td style="min-width:120px"><input data-cq="${i}" data-f="key_facts" value="${esc((c.key_facts || []).join(", "))}"></td>
        <td style="min-width:200px">${x ? `<span class="verdict-${esc(x.verdict)}">${esc(x.verdict)}</span> <span class="meta">${x.score}</span>${x.answer ? `<details class="fold mt8"><summary>${T("ev.answer")}</summary><div class="inner md">${md(x.answer)}</div></details>` : ""}` : ""}</td>
        <td class="nowrap"><button class="btn small" data-act="ev-one" data-id="${esc(c.id)}" ${S.busy.ev ? "disabled" : ""}>${T("ev.runOne")}</button> <button class="btn small danger" data-act="cq-del" data-i="${i}">${T("common.delete")}</button></td></tr>`; }).join("")}
      </tbody></table></div>` : `<div class="empty">${T("ev.none")}</div>`}</div>`;
  });
  AFTER["studio/eval"] = () => {
    document.querySelectorAll("[data-cq]").forEach((el) => el.addEventListener("change", () => {
      const list = S.ui.cqDraft || (S.ui.cqDraft = JSON.parse(JSON.stringify(S.data.cqs || [])));
      const c = list[+el.dataset.cq];
      c[el.dataset.f] = el.dataset.f === "key_facts" ? el.value.split(",").map((x) => x.trim()).filter(Boolean) : el.value;
    }));
  };

  // hand-off
  PAGES.handoff = () => studioPage(["calls"], () => {
    const w = S.ws, env = w.env, core = (S.boot && S.boot.core_mcp_url) || "";
    const imp = S.identMode === "impersonate" && S.sa ? ` --impersonate ${S.sa}` : "";
    const cli = [`git clone ${(S.boot && S.boot.github_url) || ""} && cd agentic-ontology-starter`,
      `export CORE_MCP_URL=${core}`,
      `python3 -m src.cli check --project ${env.project} --bucket ${env.bucket} --region ${env.region}${imp}`,
      `python3 -m src.cli build --bucket ${env.bucket} --ws ${w.ws_id}${imp}`,
      `python3 -m src.cli build --bucket ${env.bucket} --ws ${w.ws_id} --stages graph,eval${imp}`,
      `python3 -m src.cli ask --bucket ${env.bucket} --ws ${w.ws_id} --agent hybrid "..."${imp}`,
      `python3 -m src.cli eval --bucket ${env.bucket} --ws ${w.ws_id}${imp}`,
      `python3 -m src.cli calls --bucket ${env.bucket} --ws ${w.ws_id} --stage graph`].join("\n");
    const calls = S.data.calls || [];
    const f = S.ui.hoStage || "";
    const shown = calls.map((c, i) => [c, i]).filter(([c]) => !f || c.stage === f);
    const selC = calls[S.ui.hoSel];
    const curl = selC ? `curl -s -X POST ${core} \\\n  -H 'Content-Type: application/json' \\\n  -H "X-AOS-Access-Token: $(gcloud auth print-access-token)" \\\n  -d '${JSON.stringify({ jsonrpc: "2.0", id: 1, method: "tools/call", params: { name: selC.tool, arguments: selC.args } }).replace(/'/g, "'\\''")}'` : "";
    const cfg = JSON.stringify({ mcpServers: { "aos-core": { httpUrl: core, headers: { "X-AOS-Access-Token": "$AOS_ACCESS_TOKEN" }, timeout: 600000 } } }, null, 2);
    const stages = [...new Set(calls.map((c) => c.stage))];
    return head(T("rail.g.handoff"), T("ho.title"), T("ho.lead")) + `
    <div class="card"><div class="card-head"><h3>${T("ho.cli")}</h3><span class="sub">${T("ho.cliD")}</span></div>${codeBlock(cli)}</div>
    <div class="card calls"><div class="card-head"><h3>${T("ho.calls")} · ${calls.length}</h3><span class="sub">${T("ho.callsD")}</span><span class="right"><div class="seg"><button class="${!f ? "on" : ""}" data-act="ho-stage" data-s="">ALL</button>${stages.map((s) => `<button class="${f === s ? "on" : ""}" data-act="ho-stage" data-s="${esc(s)}">${esc(s)}</button>`).join("")}</div></span></div>
      <div class="tbl-wrap" style="max-height:360px;overflow:auto"><table class="tbl"><thead><tr><th>${T("ho.stage")}</th><th>${T("ho.tool")}</th><th>${T("ho.args")}</th><th></th><th>ms</th></tr></thead><tbody>
      ${shown.slice(-300).map(([c, i]) => `<tr class="${S.ui.hoSel === i ? "sel" : ""}" data-act="ho-sel" data-i="${i}"><td class="mono">${esc(c.stage)}</td><td class="mono">${esc(c.tool)}</td><td class="mono">${esc(JSON.stringify(c.args).slice(0, 140))}</td><td>${statusDot(c.status === "SUCCESS" ? "ok" : "error")}</td><td class="num">${c.ms}</td></tr>`).join("")}</tbody></table></div>
      ${selC ? `<div class="mt12"><div class="eyebrow">${T("ho.req")}</div><div class="mt8">${codeBlock(curl)}</div></div>` : ""}</div>
    <div class="card"><div class="card-head"><h3>${T("ho.client")}</h3><span class="sub">${T("ho.clientD")}</span></div>
      <div class="grid2"><div><div class="eyebrow">mcp_config.gemini-cli.json</div><div class="mt8">${codeBlock("export AOS_ACCESS_TOKEN=$(gcloud auth print-access-token)\n" + cfg)}</div></div>
      <div><div class="eyebrow">${T("ho.standalone")}</div><div class="mt8">${codeBlock("export AOS_ACCESS_TOKEN=$(gcloud auth print-access-token)\npython3 aos_agent_standalone.py \"...\" hybrid")}</div></div></div></div>
    <div class="card"><div class="card-head"><h3>${T("ho.bundle")}</h3><span class="sub">${T("ho.bundleD")}</span><span class="right"><button class="btn primary" data-act="bundle" ${S.busy.bundle ? "disabled" : ""}>${T("ho.bundleBtn")}</button></span></div>
      <div class="boundary">${["public", "mcp", "gcp"].map((k, i) => `<div class="layer l${i + 1}"><h3>${T("ho.b." + k)}</h3><p>${T("ho.b." + k + ".d")}</p></div>`).join("")}</div></div>`;
  });

  // deploy (GOAL-243): readiness + steps from Core MCP mcp_knowhow_deploy_plan
  PAGES.deploy = () => {
    const d = S.deploy;
    if (!d || d._ws !== S.wsId || d._lang !== S.lang) {
      if (!S.busy.dep) loadDeploy();
      return head(T("rail.g.handoff"), T("dep.title"), T("dep.lead")) + `<div class="card">${S.ui.depErr ? errNote(S.ui.depErr) : `<div class="empty">${T("common.loading")}</div>`}</div>`;
    }
    const vcls = { ready: "ok", ready_with_warnings: "warn", not_ready: "error" }[d.verdict] || "idle";
    const ev = ((S.ws && S.ws.summary) || {}).eval || {};
    return head(T("rail.g.handoff"), T("dep.title"), T("dep.lead")) + `
    <div class="card"><div class="flex"><span class="st big">${statusDot(vcls)}<b>${esc(T("dep.v." + d.verdict))}</b></span>
      <span class="tag">${esc(T("dep.score", { s: ev.score != null ? ev.score : "-", t: d.threshold }))}</span><span class="spacer grow"></span>
      <label class="small">${T("dep.target")} <select id="dep-target">${["cloud_run", "mcp_server"].map((x) => `<option value="${x}" ${d.target === x ? "selected" : ""}>${esc(T("dep.t." + x))}</option>`).join("")}</select></label>
      <label class="small">${T("dep.threshold")} <input id="dep-th" type="number" min="0" max="100" value="${esc(d.threshold)}" style="width:64px"></label>
      <button class="btn small" data-act="dep-refresh" ${S.busy.dep ? "disabled" : ""}>${T("dep.refresh")}</button></div>
      <div class="checks mt12">${(d.checks || []).map((c) => `<div class="check-row">${statusDot(c.level === "ok" ? "ok" : c.level === "warn" ? "warn" : "error")}<div><div class="l1"><span class="lbl">${esc(T("dep.c." + c.id))}</span></div><div class="det">${esc(c.detail)}</div></div><div class="api">${esc(T("dep.lv." + c.level))}</div></div>`).join("")}</div>
      ${d.verdict === "not_ready" ? `<div class="note warn">${T("dep.notReady")} <a class="btn small" href="#/studio/agents">${T("build.toAgent")}</a> <a class="btn small" href="#/studio/eval">${T("rail.eval")}</a></div>` : ""}</div>
    <div class="card"><div class="card-head"><h3>${T("dep.steps")}</h3><span class="sub">${esc(d.service_name || "")}</span><span class="right"><button class="btn small primary" data-act="bundle" ${S.busy.bundle ? "disabled" : ""}>${T("ho.bundleBtn")}</button>
      ${d.cloud_shell ? `<a class="btn small" href="${esc(d.cloud_shell)}" target="_blank" rel="noopener">${T("dep.cloudShell")}</a>` : ""}</span></div>
      <ol class="dep-steps">${(d.steps || []).map((x) => `<li><div class="t"><b>${esc(x.n)}.</b> ${esc(x.title)}</div>${x.cmd ? codeBlock(x.cmd) : ""}</li>`).join("")}</ol>
      ${(d.apis || []).length ? `<div class="meta">${T("tpl.apis")}: <span class="mono">${d.apis.map(esc).join(", ")}</span></div>` : ""}
      <div class="form-actions"><a class="btn" href="#/handoff">${T("dep.toHandoff")}</a></div></div>`;
  };
  AFTER.deploy = () => {
    const tg = $("#dep-target"), th = $("#dep-th");
    if (tg) tg.addEventListener("change", () => { S.ui.depTarget = tg.value; loadDeploy(); });
    if (th) th.addEventListener("change", () => { S.ui.depTh = +th.value || 80; });
  };
  async function loadDeploy() {
    S.busy.dep = true; S.ui.depErr = null;
    const j = await api("/api/v5/deploy/plan", { ws: wsRef(), target: S.ui.depTarget || "cloud_run", threshold: S.ui.depTh || 80 });
    S.busy.dep = false;
    if (j.status === "OK") { j._ws = S.wsId; j._lang = S.lang; S.deploy = j; } else { S.ui.depErr = j; S.deploy = null; }
    if (S.route === "deploy") rerender(); else rail();
  }

  // ------------------------------------------------------------------ actions
  const ACTIONS = {
    go: (a) => { if (a.dataset.need === "objective" && !S.scenario.objective.trim()) { toast(T("scn.needObjective")); return; } go(a.dataset.route); },
    "copy-pre": (a) => copy(a.parentElement.querySelector("pre").textContent),
    copy: (a) => copy(a.dataset.text),
    reset: () => {
      if (!confirm(T("ws.resetConfirm"))) return;
      localStorage.removeItem(LS);
      sessionStorage.removeItem(TOKEN_KEY);
      location.hash = "#/start";
      location.reload();
    },
    "start-sample": async () => {
      applyPreset("telecom");
      S.identMode = "runtime";
      S.sources = JSON.parse(JSON.stringify((S.boot && S.boot.sample) || { docs: [], tables: [] }));
      save();
      go("build");
    },
    "start-own": () => { applyPreset("custom"); go("scenario"); },
    preset: (a) => { applyPreset(a.dataset.id); rerender(); },
    qtype: (a) => { S.scenario.question_type = a.dataset.q; save(); rerender(); },
    "ident-mode": (a) => { S.identMode = a.dataset.mode; S.identInfo = null; S.check = null; S.ui.idError = ""; save(); rerender(); },
    "verify-id": async () => {
      S.ui.idError = "";
      const j = await api("/api/v5/identity", {});
      if (j.status === "OK") S.identInfo = j.identity; else { S.identInfo = null; S.ui.idError = j.message || j.status; }
      rerender();
    },
    check: async () => {
      S.busy.check = true; rerender();
      const j = await api("/api/v5/check", { env: S.env, ws_id: S.draftId });
      S.busy.check = false;
      if (j.checks) { S.check = j; S.identInfo = j.identity; } else toast(j.message || j.status, 6000);
      rerender();
    },
    script: async () => { const j = await api("/api/v5/setup-script", { env: S.env }); if (j.script) { S.ui.script = j.script; rerender(); } else toast(j.message || j.status); },
    "dl-script": () => download("setup_gcp.sh", S.ui.script || "", "text/x-shellscript"),
    dtab: (a) => { S.ui.dtab = a.dataset.t; rerender(); },
    "add-sample": () => {
      const sm = (S.boot && S.boot.sample) || { docs: [], tables: [] };
      const have = new Set([...S.sources.docs, ...S.sources.tables].map((x) => x.uri));
      sm.docs.forEach((d) => { if (!have.has(d.uri)) S.sources.docs.push(d); });
      sm.tables.forEach((t) => { if (!have.has(t.uri)) S.sources.tables.push(t); });
      save(); toast(T("data.sampleAdded")); rerender();
    },
    "src-del": (a) => { (a.dataset.kind === "doc" ? S.sources.docs : S.sources.tables).splice(+a.dataset.i, 1); S.types = null; save(); rerender(); },
    "gcs-list": async () => { S.ui.gcsUri = $("#gcs-uri").value.trim(); S.ui.gcs = await api("/api/v5/gcs/list", { uri: S.ui.gcsUri }); rerender(); },
    "gcs-add": async () => {
      const r = S.ui.gcs, items = [...r.docs.map((d) => ["doc", d]), ...r.tables.map((t) => ["table", t])];
      const toConvert = [];
      document.querySelectorAll("[data-pick]").forEach((cb) => {
        if (!cb.checked) return;
        const [k, x] = items[+cb.dataset.pick];
        if (k === "doc" && x.convert) toConvert.push(x);
        else if (k === "doc") S.sources.docs.push({ name: x.name, origin: "gcs", uri: x.uri, chars: x.size });
        else S.sources.tables.push({ name: x.name, origin: "gcs", uri: x.uri });
      });
      S.ui.gcs = null; S.types = null; save(); rerender();
      if (toConvert.length) await convertMany(toConvert, (x) => api("/api/v5/convert", { env: S.env, ws_id: S.draftId, uri: x.uri, pdf_mode: S.ui.pdfMode || "auto" }));
    },
    "drive-list": async () => {
      S.ui.driveUrl = $("#drive-url").value.trim();
      if (!S.ui.driveUrl) return;
      S.ui.drive = await api("/api/v5/drive/list", { url: S.ui.driveUrl }); rerender();
    },
    "drive-add": async () => {
      const files = (S.ui.drive && S.ui.drive.files) || [];
      const pick = [];
      document.querySelectorAll("[data-pick]").forEach((cb) => { if (cb.checked && !cb.disabled) pick.push(files[+cb.dataset.pick]); });
      S.ui.drive = null; rerender();
      await convertMany(pick, (f) => api("/api/v5/drive/import", { env: S.env, ws_id: S.draftId, file_id: f.id }));
    },
    "tpl-flow": (a) => {
      S.tpl.flow = a.dataset.id; S.template = null;
      const f = ((S.catalog && S.catalog.flows) || []).find((x) => x.id === a.dataset.id);
      if (f) { S.scenario.question_type = f.question_type; S.tpl.services = S.tpl.services.filter((x) => (f.optional || []).includes(x)); }
      save(); rerender();
    },
    "tpl-svc": (a) => {
      const id = a.dataset.id, i = S.tpl.services.indexOf(id);
      if (i >= 0) S.tpl.services.splice(i, 1); else S.tpl.services.push(id);
      S.template = null; save(); rerender();
    },
    "tpl-target": (a) => {
      S.tpl.target = a.dataset.id; S.template = null;
      if (a.dataset.id === "sandbox") {  // starter sandbox = runtime identity + the starter project defaults
        S.identMode = "runtime"; S.identInfo = null; S.check = null;
        for (const [k, v] of Object.entries((S.boot && S.boot.env_defaults) || {})) if (k !== "dataset") S.env[k] = v;
      } else if (S.identMode === "runtime") { S.identMode = "token"; S.identInfo = null; S.check = null; }
      save(); rerender();
    },
    "tpl-compose": async () => {
      S.busy.tpl = true; S.ui.tplErr = null; rerender();
      const j = await api("/api/v5/template", { flow: S.tpl.flow, services: S.tpl.services, target: S.tpl.target, env: S.env, ws_id: S.draftId });
      S.busy.tpl = false;
      if (j.status === "OK") { delete j._http; S.template = j; } else S.ui.tplErr = j;
      save(); rerender();
    },
    "dl-tpl-script": () => download("setup_template.sh", (S.template && S.template.setup_script) || "", "text/x-shellscript"),
    classify: async () => {
      S.busy.cls = true; S.ui.clsErr = null; rerender();
      const user = {};
      for (const [u, d] of Object.entries(S.ui.typeDec || {})) if (d.type) user[u] = d.type;
      const j = await api("/api/v5/classify", { env: S.env, ws_id: S.draftId, sources: S.sources, user_types: user, use_llm: !!S.ui.clsLlm });
      S.busy.cls = false;
      if (j.status === "OK") S.types = j; else S.ui.clsErr = j;
      rerender();
    },
    "types-save": async () => {
      const decisions = typeDecisions();
      if (!decisions.length) { toast(T("types.needRun")); return; }
      S.busy.cls = true; rerender();
      const j = await api("/api/v5/types/save", { decisions, sources: S.sources, ws: S.wsCreated ? wsRef() : null });
      S.busy.cls = false;
      if (j.status === "OK") {
        if (j.ws) S.ws = j.ws;
        const prev = {};
        S.sources.docs.forEach((d) => { prev[d.uri] = d; });
        S.sources = j.sources;
        S.sources.docs.forEach((d) => { if (!d.conversion && prev[d.uri] && prev[d.uri].conversion) d.conversion = prev[d.uri].conversion; });
        S.ui.typeDec = {}; save(); toast(T("types.savedN", { n: decisions.length })); rerender();
      } else errToast(j);
    },
    reconvert: async (a) => {
      const d = S.sources.docs[+a.dataset.i];
      if (!d || !d.conversion || !d.conversion.source) return;
      await convertMany([{ name: d.name, uri: d.conversion.source }], (x) => api("/api/v5/convert", { env: S.env, ws_id: S.draftId, uri: x.uri, pdf_mode: "gemini" }));
    },
    "dep-refresh": () => { const th = $("#dep-th"); if (th) S.ui.depTh = +th.value || 80; loadDeploy(); },
    "bq-list": async () => { S.ui.bqDs = $("#bq-ds").value.trim(); S.ui.bq = await api("/api/v5/bq/tables", { dataset: S.ui.bqDs, env: S.env }); rerender(); },
    "bq-add": () => {
      document.querySelectorAll("[data-pick]").forEach((cb) => { if (cb.checked) { const t = S.ui.bq.tables[+cb.dataset.pick]; S.sources.tables.push({ name: t.name, origin: "bigquery", fq: t.fq, uri: t.fq }); } });
      S.ui.bq = null; save(); rerender();
    },
    "run-all": () => runAll(),
    "run-stage": (a) => { if (S.route !== "build") go("build"); runAll(a.dataset.stage); },
    asset: (a) => { S.ui.asset = a.dataset.id; rerender(); },
    "to-query": (a) => { S.ui.grSql = a.dataset.sql; S.ui.grRes = null; go("studio/graph"); setTimeout(() => ACTIONS["gr-run"](), 50); },
    "wk-page": (a) => { S.ui.wkSel = a.dataset.id; S.ui.wkEdit = null; rerender(); },
    "wk-goto": (a) => { S.ui.wkSel = a.dataset.id; S.ui.wkEdit = null; go("studio/wiki"); },
    "wk-edit": () => { const p = (S.data.wiki || []).find((x) => x.id === S.ui.wkSel) || (S.data.wiki || [])[0]; S.ui.wkEdit = JSON.parse(JSON.stringify(p)); S.ui.wkEditOrig = p.id; rerender(); },
    "wk-new": () => { S.ui.wkEdit = { id: "CON-NEW", layer: "concept", title: "", summary: "", body_md: "", policy: [], relations: [], applies_to: [], sources: [] }; S.ui.wkEditOrig = ""; rerender(); },
    "wk-cancel": () => { S.ui.wkEdit = null; rerender(); },
    "wk-save": async () => {
      const pj = (id, f) => { try { return JSON.parse($(id).value || "[]"); } catch (e) { throw new Error(T("wk.badJson", { f })); } };
      let page;
      try {
        page = { id: $("#we-id").value.trim(), layer: $("#we-layer").value, title: $("#we-title").value, summary: $("#we-summary").value, body_md: $("#we-body").value,
          policy: pj("#we-policy", "policy"), relations: pj("#we-relations", "relations"), applies_to: pj("#we-applies", "applies_to"), sources: pj("#we-sources", "sources") };
      } catch (e) { toast(e.message, 5000); return; }
      const pages = (S.data.wiki || []).filter((p) => p.id !== S.ui.wkEditOrig);
      pages.push(page);
      const j = await api("/api/v5/wiki/save", { ws: wsRef(), pages });
      if (j.status !== "SUCCESS") { toast(j.error || j.message || j.status, 6000); return; }
      S.data.wiki = j.pages; S.data.gates = { gates: j.gates, passed: j.gates_passed, total: j.gates_total };
      S.ui.wkEdit = null; S.ui.wkSel = page.id.toUpperCase();
      const o = await api("/api/v5/ws/open", { ws: wsRef() }); if (o.ws) S.ws = o.ws;
      toast(T("wk.saved", { p: j.gates_passed, t: j.gates_total }), 4000); rerender();
    },
    "gr-node": (a) => { S.ui.grNode = a.dataset.label; rerender(); },
    "gr-run": async () => {
      const el = $("#gr-sql");
      if (el) S.ui.grSql = el.value;
      S.busy.q = true; rerender();
      S.ui.grRes = await api("/api/v5/query", { ws: wsRef(), sql: S.ui.grSql });
      S.busy.q = false; rerender();
    },
    "gr-rebuild": async () => {
      let design;
      try { design = JSON.parse($("#gr-design").value); } catch (e) { toast(T("wk.badJson", { f: "design" }), 5000); return; }
      S.busy.build = true; go("build");
      await stream("/api/v5/graph/rebuild", { ws: wsRef(), design }, (ev) => { if (ev.type === "result") { S.ws = ev.ws; S.dataFor = ""; } else pushLog(ev); });
      S.busy.build = false; rerender();
    },
    "sr-go": async () => {
      S.ui.srQ = ($("#sr-q") || {}).value || S.ui.srQ;
      if (!S.ui.srQ) return;
      S.busy.sr = true; rerender();
      const j = await api("/api/v5/search", { ws: wsRef(), q: S.ui.srQ });
      S.busy.sr = false;
      if (j.status === "SUCCESS") S.ui.sr = j; else toast(j.error || j.message || j.status);
      rerender();
    },
    "ag-pick": (a) => { S.ui.agent = a.dataset.a; save(); rerender(); },
    "ag-preset": (a) => { S.ui.agQ = a.dataset.q; const el = $("#ag-q"); if (el) el.value = S.ui.agQ; },
    "ag-ask": async () => {
      S.ui.agQ = $("#ag-q").value.trim();
      if (!S.ui.agQ) return;
      S.busy.ag = true; S.ui.agRes = null; S.ui.agLive = []; rerender();
      await stream("/api/v5/agent", { ws: wsRef(), agent: S.ui.agent || "hybrid", question: S.ui.agQ }, (ev) => {
        if (ev.type === "step") {
          const i = S.ui.agLive.findIndex((x) => x.step === ev.step);
          if (i >= 0) S.ui.agLive[i] = ev; else S.ui.agLive.push(ev);
          const ul = $(".trace"); if (ul) ul.innerHTML = S.ui.agLive.map((e) => `<li>${statusDot(e.status)}<span>${esc(e.label)}${e.detail ? " — " + esc(e.detail) : ""}</span><span class="ms">${e.ms != null ? e.ms + " ms" : ""}</span></li>`).join("");
        } else if (ev.type === "result") S.ui.agRes = ev;
        else if (ev.type === "error") S.ui.agRes = { status: "ERROR", agent: S.ui.agent, answer: ev.message || ev.status };
      });
      S.busy.ag = false; rerender();
    },
    "ag-tocq": async () => {
      const r = S.ui.agRes; if (!r) return;
      const list = JSON.parse(JSON.stringify(S.data.cqs || []));
      const n = list.length + 1;
      list.push({ id: `CQ-U${String(n).padStart(2, "0")}`, question: r.question, agent: r.agent, type: { wiki: "doc", graph: "data", hybrid: "hybrid" }[r.agent], reference_answer: "", key_facts: [], origin: "studio" });
      const j = await api("/api/v5/cqs/save", { ws: wsRef(), cqs: list });
      if (j.status === "SUCCESS") { S.data.cqs = j.cqs; toast(T("ag.addedCq"), 4000); } else toast(j.message || j.status);
    },
    "cq-add": () => { const list = S.ui.cqDraft || (S.ui.cqDraft = JSON.parse(JSON.stringify(S.data.cqs || []))); list.push({ id: `CQ-U${String(list.length + 1).padStart(2, "0")}`, question: "", agent: "hybrid", type: "hybrid", reference_answer: "", key_facts: [], origin: "studio" }); rerender(); },
    "cq-del": (a) => { const list = S.ui.cqDraft || (S.ui.cqDraft = JSON.parse(JSON.stringify(S.data.cqs || []))); list.splice(+a.dataset.i, 1); rerender(); },
    "cq-save": async () => {
      const list = S.ui.cqDraft || S.data.cqs || [];
      list.forEach((c) => { c.type = { wiki: "doc", graph: "data", hybrid: "hybrid" }[c.agent] || c.type; });
      const j = await api("/api/v5/cqs/save", { ws: wsRef(), cqs: list });
      if (j.status === "SUCCESS") { S.data.cqs = j.cqs; S.ui.cqDraft = null; toast(T("ev.savedCqs", { n: j.cqs.length })); rerender(); return true; }
      toast(j.message || j.status); return false;
    },
    "ev-run": async () => evalRun([]),
    "ev-one": async (a) => evalRun([a.dataset.id]),
    "ho-stage": (a) => { S.ui.hoStage = a.dataset.s; rerender(); },
    "ho-sel": (a) => { S.ui.hoSel = +a.dataset.i; rerender(); },
    bundle: async () => {
      S.busy.bundle = true; rerender();
      try {
        const r = await fetch("/api/v5/export", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ ws: wsRef(), lang: S.lang, identity: identity() }) });
        if (r.ok) download(`${S.wsId}.zip`, await r.blob()); else { const j = await r.json().catch(() => ({})); toast(j.message || "HTTP " + r.status, 5000); }
      } finally { S.busy.bundle = false; rerender(); }
    },
    "ws-open-modal": () => openModal(),
    "ws-list": async () => {
      const b = $("#m-bucket").value.trim();
      const j = await api("/api/v5/ws/list", { bucket: b });
      const host = $("#m-list");
      if (j.status !== "OK") { host.innerHTML = `<div class="note err">${esc(j.message || j.status)}</div>`; return; }
      host.innerHTML = j.workspaces.length ? j.workspaces.map((w) => `<div class="src"><span class="tag mono">${esc(w.ws_id)}</span><div class="nm">${esc(w.title || "")}<div class="uri">${esc(w.updated_at || "")} · ${esc(w.lang || "")}</div></div><span class="meta">${Object.values(w.stages || {}).filter((s) => s === "done").length}/6</span><button class="btn small primary" data-act="ws-open" data-b="${esc(j.bucket)}" data-id="${esc(w.ws_id)}">${T("common.open")}</button></div>`).join("") : `<div class="empty">${T("ws.listEmpty")}</div>`;
    },
    "ws-open": async (a) => {
      const b = a.dataset.b || $("#m-bucket").value.trim(), id = a.dataset.id || $("#m-id").value.trim();
      const j = await api("/api/v5/ws/open", { ws: { bucket: b, ws_id: id } });
      if (j.status !== "OK") { toast(j.message || j.status, 5000); return; }
      openWs(j.ws); closeModal(); toast(T("ws.opened")); go("studio/overview");
    },
    "modal-close": () => closeModal(),
  };
  async function evalRun(ids) {
    if (S.ui.cqDraft && !(await ACTIONS["cq-save"]())) return;
    S.busy.ev = true; S.ui.evLive = {}; rerender();
    await stream("/api/v5/eval", { ws: wsRef(), cq_ids: ids }, (ev) => {
      if (ev.type === "cq") { S.ui.evLive[ev.id] = ev; rerender(); }
      else if (ev.type === "result" && ev.ws) S.ws = ev.ws;
      else if (ev.type === "error") toast(ev.message || ev.status, 6000);
    });
    S.busy.ev = false;
    await ensureData(["run"], true);
    S.ui.evLive = {};
    rerender();
  }
  function applyPreset(id) {
    const p = ((S.boot && S.boot.presets) || []).find((x) => x.id === id);
    if (!p) return;
    S.scenario = { preset: p.id, title: p.id === "custom" ? S.scenario.title : p.title, customer: p.customer, objective: p.objective || (p.id === "custom" ? S.scenario.objective : ""), question_type: p.question_type };
    save();
  }
  function openWs(ws) {
    S.ws = ws; S.wsId = ws.ws_id; S.wsCreated = true; S.env = Object.assign({}, ws.env); S.scenario = Object.assign({}, S.scenario, ws.scenario);
    S.sources = ws.sources || S.sources; S.dataFor = ""; S.data = {}; S.draftId = ws.ws_id; S.deploy = null; S.types = null;
    const tp = ws.template || {};
    if (tp.flow) S.tpl = { flow: tp.flow, services: (tp.services || []).slice(), target: tp.target || "sandbox" };
    save();
  }
  function openModal() {
    $("#modal-card").innerHTML = `<div class="card-head"><h2>${T("ws.openTitle")}</h2><span class="right"><button class="btn small" data-act="modal-close">${T("common.close")}</button></span></div>
      <div class="form"><div class="field"><label>${T("ws.bucket")}</label><input id="m-bucket" value="${esc(S.env.bucket || "")}"></div><div class="field"><label>${T("ws.id")}</label><input id="m-id" placeholder="ws-YYYYMMDD-xxxxxx"></div></div>
      <div class="form-actions"><button class="btn" data-act="ws-list">${T("ws.list")}</button><button class="btn primary" data-act="ws-open">${T("common.open")}</button></div><div class="srclist mt12" id="m-list"></div>`;
    $("#modal").hidden = false;
  }
  function closeModal() { $("#modal").hidden = true; }

  document.addEventListener("click", (e) => {
    const a = e.target.closest("[data-act]");
    if (!a) { if (e.target.id === "modal") closeModal(); return; }
    const fn = ACTIONS[a.dataset.act];
    if (fn) { e.preventDefault(); fn(a, e); }
  });
  document.addEventListener("input", (e) => {
    const el = e.target;
    if (el.id === "tok") { sessionStorage.setItem(TOKEN_KEY, el.value.trim()); S.identInfo = null; return; }
    const b = el.dataset && el.dataset.bind;
    if (!b) return;
    const [grp, key] = b.split(".");
    if (key) { S[grp][key] = el.value; if (grp === "env") S.check = null; } else S[grp] = el.value;
    save();
  });
  document.querySelectorAll("#lang-toggle button").forEach((b) => b.addEventListener("click", () => setLang(b.dataset.lang)));
  function setLang(l) {
    S.lang = l === "en" ? "en" : "ko";
    save();
    S.template = null; S.types = null;
    fetch("/api/v5/bootstrap?lang=" + S.lang).then((r) => r.json()).then((b) => { S.boot = b; render(); });
  }
  window.addEventListener("hashchange", route);

  async function boot() {
    load();
    const qs = new URLSearchParams(location.search);
    if (qs.get("lang")) S.lang = qs.get("lang") === "en" ? "en" : "ko";
    if (qs.get("reset") === "1") { localStorage.removeItem(LS); sessionStorage.removeItem(TOKEN_KEY); load(); }
    const [i18n, b] = await Promise.all([fetch("/static/studio_i18n.json").then((r) => r.json()), fetch("/api/v5/bootstrap?lang=" + S.lang).then((r) => r.json())]);
    S.i18n = i18n; S.boot = b;
    for (const [k, v] of Object.entries(b.env_defaults || {})) if (!S.env[k] && k !== "dataset") S.env[k] = v;
    if (!S.draftId) { const j = await api("/api/v5/ws/draft", {}); S.draftId = j.ws_id || ""; }
    if (qs.get("ws") && qs.get("bucket")) {  // deep link: ?bucket=<bucket>&ws=<ws_id>#/studio/overview
      const j = await api("/api/v5/ws/open", { ws: { bucket: qs.get("bucket"), ws_id: qs.get("ws") } });
      if (j.status === "OK") openWs(j.ws);
    } else if (S.wsId && S.wsCreated) {
      const j = await api("/api/v5/ws/open", { ws: wsRef() });
      if (j.status === "OK") S.ws = j.ws; else { S.wsCreated = false; S.ws = null; }
    }
    save();
    route();
  }
  window.AOLStudio = { state: () => S, go, setLang, api, T };
  boot();
})();
