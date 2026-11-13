/* Agentic Ontology Starter — 6-step wizard (GOAL-223). Vanilla JS, no build step.
 *
 *   1 Type & purpose → 2 Flow → 3 GCP resources (real checks) → 4 Load (NDJSON stream) → 5 Agents (NDJSON) → 6 Evaluate (NDJSON)
 *
 * Server: src/web/studio_server.py (/api/settings · /api/catalog · /api/verify · /api/load · /api/agent · /api/eval ·
 * /api/core-mcp/tools). Diagrams: aolflow.js (shared renderer, do not edit here) + flows.js (STARTER_FLOWS specs).
 * UI strings: /static/i18n.json — KO and EN with identical keys. Results are stored per recipe + language, so the EN
 * screen only ever shows runs made on the English data set. Every request carries the resources entered in step 3.
 * State: localStorage "aol.starter.v1". Deep links: #step-1 … #step-6 · ?lang=ko|en · ?recipe=A|B|C · ?reset=1
 */
(function () {
  "use strict";

  const LS_KEY = "aol.starter.v1";
  const FIELDS = ["project_id", "region", "dataset_id", "bucket", "graph_name", "model", "vertex_location", "spanner_instance", "spanner_database"];
  const CANON = { A: ["P1", "W1"], B: ["P2", "W2"], C: ["P3", "W3"] };
  const STEP_CLASS = { 3: "s3", 4: "s4", 5: "s5", 6: "s6" };
  const MAX_MSGS = 8;
  const CITE_RE = /\[((?:summary|concepts|rules|entities)(?:\s*,\s*(?:summary|concepts|rules|entities))*)\]/g;
  const citedIds = (text) => {
    const out = new Set();
    String(text || "").replace(CITE_RE, (m, ids) => { ids.split(/\s*,\s*/).forEach((x) => out.add(x)); return m; });
    return out;
  };
  const R = { i18n: null, settings: null, cats: {}, mcp: null, busy: {}, runs: { load: {}, evals: {} }, res: null, timers: {} };
  let S = restore();

  // ------------------------------------------------------------------ state
  function blank() {
    return { v: 1, lang: "en", step: 1, type: null, purpose: null, config: {}, graphCustom: false, spanner: false, seen: {},
      verify: {}, load: {}, chats: {}, agent: {}, sel: {}, evals: {} };
  }
  function restore() {
    try {
      const s = JSON.parse(localStorage.getItem(LS_KEY) || "null");
      if (s && s.v === 1) return Object.assign(blank(), s);
    } catch (e) {
      console.warn("[starter] state reset:", e);
    }
    return blank();
  }
  function save(now) {
    clearTimeout(R.timers.save);
    const write = () => {
      try {
        localStorage.setItem(LS_KEY, JSON.stringify(S));
      } catch (e) {  // quota: keep the last two messages per agent and retry once
        console.warn("[starter] localStorage full, trimming chats:", e);
        Object.values(S.chats).forEach((byAgent) => Object.keys(byAgent).forEach((a) => { byAgent[a] = byAgent[a].slice(-2); }));
        try { localStorage.setItem(LS_KEY, JSON.stringify(S)); } catch (e2) { console.warn("[starter] state not saved:", e2); }
      }
    };
    if (now) write(); else R.timers.save = setTimeout(write, 250);
  }

  // ------------------------------------------------------------------ helpers
  const $ = (s, r) => (r || document).querySelector(s);
  const $$ = (s, r) => Array.from((r || document).querySelectorAll(s));
  const esc = (v) => String(v == null ? "" : v).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const hasT = (k) => !!(R.i18n && R.i18n[S.lang] && R.i18n[S.lang][k] != null);
  function t(k, vars) {
    let s = R.i18n && R.i18n[S.lang] ? R.i18n[S.lang][k] : null;
    if (s == null) { console.warn("[starter] i18n missing:", S.lang, k); s = k; }
    return vars ? s.replace(/\{(\w+)\}/g, (m, v) => (vars[v] != null ? String(vars[v]) : m)) : s;
  }
  function fmtMs(ms) {
    if (ms == null || ms === "" || isNaN(ms)) return "—";
    ms = Number(ms);
    return ms < 1000 ? `${Math.round(ms)} ms` : `${(ms / 1000).toFixed(ms < 10000 ? 2 : 1)} s`;
  }
  const fmtNum = (n) => (n == null || n === "" ? "—" : isNaN(n) ? String(n) : Number(n).toLocaleString("en-US"));
  function fmtCell(v) {
    if (v == null) return "—";
    if (typeof v === "object") v = JSON.stringify(v);
    v = String(v);
    return v.length > 120 ? `${v.slice(0, 119)}…` : v;
  }
  function norm(raw) {
    const s = String(raw == null ? "" : raw).toLowerCase();
    if (!s || s === "idle") return "idle";
    if (s === "running" || s === "pending") return "running";
    if (s.indexOf("skip") === 0) return "skipped";
    if (/error|fail|blocked|denied|not_loaded|invalid|unknown|false/.test(s)) return "error";
    if (/^(no_|not_|warn|partial|insufficient|out_of_scope|refus|clarif|ambig)/.test(s)) return "warn";
    if (/^(ok|done|success|pass|grounded|answered|match|ready|true|local)/.test(s)) return "ok";
    return "warn";
  }
  const dot = (s) => `<span class="dot ${norm(s)}"></span>`;
  const stText = (s) => (hasT(`st_${s}`) ? t(`st_${s}`) : String(s == null ? "" : s));
  function toast(msg) {
    const el = $("#toast");
    el.textContent = msg;
    el.classList.add("show");
    clearTimeout(R.timers.toast);
    R.timers.toast = setTimeout(() => el.classList.remove("show"), 2400);
  }
  async function copyText(s) {
    try {
      await navigator.clipboard.writeText(s);
    } catch (e) {  // http (non-secure) origins have no clipboard API
      const ta = document.createElement("textarea");
      ta.value = s; document.body.appendChild(ta); ta.select();
      try { document.execCommand("copy"); } catch (e2) { console.warn("[starter] copy failed:", e2); }
      ta.remove();
    }
    toast(t("copied"));
  }
  function bindCopy(root) {
    $$("[data-copy]", root).forEach((b) => b.addEventListener("click", (ev) => { ev.stopPropagation(); copyText(b.getAttribute("data-copy")); }));
  }
  function later(name, fn, ms) {  // coalesce bursts of stream events into one paint
    if (R.timers[name]) return;
    R.timers[name] = setTimeout(() => { R.timers[name] = 0; try { fn(); } catch (e) { console.error("[starter] paint failed:", e); } }, ms || 60);
  }

  // delatex:start — Gemini sometimes writes formulas as LaTeX; show them as plain text before Markdown rendering.
  // Only spans inside math delimiters change ($$…$$, \[…\], \(…\), or $…$ holding a TeX command), so prices
  // such as "$5" and fenced code blocks stay untouched.
  const TEX_SUBS = [
    [/\\left\s*|\\right\s*/g, ""], [/\\times/g, "×"], [/\\div/g, "÷"], [/\\cdot/g, "·"],
    [/\\leq?(?![A-Za-z])/g, "≤"], [/\\geq?(?![A-Za-z])/g, "≥"], [/\\neq?(?![A-Za-z])/g, "≠"], [/\\approx/g, "≈"],
    [/\\[,;:]|\\qquad|\\quad|~/g, " "], [/\\!/g, ""], [/\\%/g, "%"], [/\\_/g, "_"], [/\\([{}])/g, "$1"],
  ];
  function texText(s) {
    let out = String(s);
    for (let i = 0; i < 4; i++) out = out.replace(/\\(?:text|mathrm|mathbf|mathit|textbf|textit|operatorname)\s*\{([^{}]*)\}/g, "$1");
    for (let i = 0; i < 4; i++) out = out.replace(/\\[dt]?frac\s*\{([^{}]*)\}\s*\{([^{}]*)\}/g, "($1) ÷ ($2)");
    TEX_SUBS.forEach((p) => { out = out.replace(p[0], p[1]); });
    return out.replace(/[{}]/g, "").replace(/[ \t]{2,}/g, " ").trim();
  }
  function delatex(src) {
    return String(src == null ? "" : src).split(/(```[\s\S]*?```)/).map((part, i) => (i % 2 ? part : part
      .replace(/\$\$([\s\S]+?)\$\$/g, (m, x) => texText(x))
      .replace(/\\\[([\s\S]+?)\\\]/g, (m, x) => texText(x))
      .replace(/\\\(([\s\S]+?)\\\)/g, (m, x) => texText(x))
      .replace(/(^|[^$\\\w])\$(?=[^\s$])([^$\n]*?\\[A-Za-z][^$\n]*?)\$(?!\d)/g, (m, pre, x) => pre + texText(x)))).join("");
  }
  // delatex:end

  // Small, safe Markdown subset for agent answers (LaTeX → text, escape, then format).
  function md(src) {
    const L = delatex(src).replace(/\r\n?/g, "\n").split("\n");
    const out = [];
    const inl = (s) => esc(s)
      .replace(/`([^`]+)`/g, "<code>$1</code>")
      .replace(/\*\*([^*]+)\*\*/g, "<b>$1</b>")
      .replace(CITE_RE, (m, ids) => ids.split(/\s*,\s*/).map((x) => `<span class="cite">${x}</span>`).join(""))
      .replace(/\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
    const isSep = (s) => /^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$/.test(s || "");
    const isTable = (i) => L[i].indexOf("|") >= 0 && i + 1 < L.length && isSep(L[i + 1]);
    const cells = (s) => s.trim().replace(/^\|/, "").replace(/\|$/, "").split("|").map((x) => x.trim());
    const BLOCK = /^\s*(```|#{1,6}\s|[-*+•]\s|\d+[.)]\s|>)/;
    let i = 0;
    while (i < L.length) {
      const l = L[i];
      if (/^\s*```/.test(l)) {
        const b = []; i++;
        while (i < L.length && !/^\s*```/.test(L[i])) b.push(L[i++]);
        i++;
        out.push(`<pre><code>${esc(b.join("\n"))}</code></pre>`);
      } else if (isTable(i)) {
        const head = cells(l); i += 2;
        const rows = [];
        while (i < L.length && L[i].indexOf("|") >= 0 && L[i].trim()) rows.push(cells(L[i++]));
        out.push(`<table><thead><tr>${head.map((h) => `<th>${inl(h)}</th>`).join("")}</tr></thead><tbody>${rows.map((r) => `<tr>${r.map((c) => `<td>${inl(c)}</td>`).join("")}</tr>`).join("")}</tbody></table>`);
      } else if (/^\s*#{1,6}\s/.test(l)) {
        out.push(`<h4>${inl(l.replace(/^\s*#{1,6}\s+/, ""))}</h4>`); i++;
      } else if (/^\s*[-*+•]\s/.test(l)) {
        const items = [];
        while (i < L.length && /^\s*[-*+•]\s/.test(L[i])) items.push(L[i++].replace(/^\s*[-*+•]\s+/, ""));
        out.push(`<ul>${items.map((x) => `<li>${inl(x)}</li>`).join("")}</ul>`);
      } else if (/^\s*\d+[.)]\s/.test(l)) {
        const items = [];
        while (i < L.length && /^\s*\d+[.)]\s/.test(L[i])) items.push(L[i++].replace(/^\s*\d+[.)]\s+/, ""));
        out.push(`<ol>${items.map((x) => `<li>${inl(x)}</li>`).join("")}</ol>`);
      } else if (/^\s*>/.test(l)) {
        const b = [];
        while (i < L.length && /^\s*>/.test(L[i])) b.push(L[i++].replace(/^\s*>\s?/, ""));
        out.push(`<blockquote>${inl(b.join(" "))}</blockquote>`);
      } else if (/^\s*(-{3,}|\*{3,}|_{3,})\s*$/.test(l)) {
        out.push("<hr>"); i++;
      } else if (!l.trim()) {
        i++;
      } else {
        const p = [L[i++]];
        while (i < L.length && L[i].trim() && !BLOCK.test(L[i]) && !isTable(i)) p.push(L[i++]);
        out.push(`<p>${p.map(inl).join("<br>")}</p>`);
      }
    }
    return out.join("");
  }

  // ------------------------------------------------------------------ http
  async function getJSON(url) {
    const r = await fetch(url, { cache: "no-cache" });
    if (!r.ok) throw new Error(`${url} HTTP ${r.status}`);
    return r.json();
  }
  async function postJSON(url, body) {
    const r = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    let j = null;
    try { j = await r.json(); } catch (e) { throw new Error(`${url} HTTP ${r.status}`); }
    if (!r.ok) { const err = new Error(j.message || j.error || `HTTP ${r.status}`); err.payload = j; throw err; }
    return j;
  }
  async function stream(url, body, onEvent) {
    const r = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    if (!r.ok || (r.headers.get("content-type") || "").indexOf("ndjson") < 0) {
      let j = {};
      try { j = await r.json(); } catch (e) { /* not JSON: keep the HTTP status below */ }
      const err = new Error(j.message || j.error || `HTTP ${r.status}`); err.payload = j; throw err;
    }
    const rd = r.body.getReader(), dec = new TextDecoder();
    let buf = "";
    const line = (s) => {
      s = s.trim();
      if (!s) return;
      let ev;
      try { ev = JSON.parse(s); } catch (e) { console.warn("[starter] bad NDJSON line:", s.slice(0, 200)); return; }
      onEvent(ev);
    };
    for (;;) {
      const { value, done } = await rd.read();
      if (done) break;
      buf += dec.decode(value, { stream: true });
      let i;
      while ((i = buf.indexOf("\n")) >= 0) { line(buf.slice(0, i)); buf = buf.slice(i + 1); }
    }
    line(buf + dec.decode());
  }

  // ------------------------------------------------------------------ catalog · recipe · config
  async function ensureCat(lang) {
    if (!R.cats[lang]) R.cats[lang] = await getJSON(`/api/catalog?lang=${lang}`);
    return R.cats[lang];
  }
  const cat = () => R.cats[S.lang];
  function resolved() {
    const c = cat();
    return c && S.type && S.purpose ? c.matrix[`${S.type}-${S.purpose}`] || null : null;
  }
  const recipeKey = () => { const m = resolved(); return m ? m.recipe : null; };
  const recipe = () => { const k = recipeKey(); return k ? cat().recipes[k] : null; };
  const rk = (k) => `${k || recipeKey()}:${S.lang}`;
  const has = (r, p) => !!r && r.paths.indexOf(p) >= 0;
  const graphDefault = (k) => { const g = (R.settings && R.settings.graph_defaults) || {}; return g[k] || g.C || "STARTER_ONTOLOGY_GRAPH"; };
  function syncGraph() {
    const k = recipeKey();
    if (k && k !== "A" && !S.graphCustom) S.config.graph_name = graphDefault(k);
  }
  function ensureConfig(reset) {
    const d = (R.settings && R.settings.defaults) || {};
    FIELDS.forEach((f) => { if (reset || S.config[f] == null) S.config[f] = d[f] || ""; });
    if (reset) S.graphCustom = false;
    syncGraph();
  }
  function cfgPayload() {
    const c = {};
    FIELDS.forEach((f) => { c[f] = String(S.config[f] == null ? "" : S.config[f]).trim(); });
    if (recipeKey() === "A") c.graph_name = "";
    return c;
  }
  const cfgSig = () => JSON.stringify([cfgPayload(), !!S.spanner, recipeKey()]);
  const body = (extra) => Object.assign({ config: cfgPayload(), recipe: recipeKey(), lang: S.lang, spanner: !!S.spanner }, extra || {});
  function writeAllowed(p) {
    const w = (R.settings && R.settings.write_projects) || [];
    return w.indexOf("*") >= 0 || w.indexOf(p) >= 0;
  }
  function fill(s) {
    const c = S.config;
    return String(s == null ? "" : s).replace(/\{bucket\}/g, c.bucket).replace(/\{lang\}/g, S.lang).replace(/\{project\}/g, c.project_id)
      .replace(/\{dataset\}/g, c.dataset_id).replace(/\{graph\}/g, c.graph_name);
  }
  function choose(type, purpose) {
    S.type = type; S.purpose = purpose;
    syncGraph(); save(); render();
  }
  const loadRun = (key) => R.runs.load[key] || S.load[key] || null;
  const evalRun = (key) => R.runs.evals[key] || S.evals[key] || null;
  const loadedOk = (key) => { const l = S.load[key]; return !!(l && (l.status === "SUCCESS" || l.status === "PARTIAL")); };
  function chats(key, agent) {
    S.chats[key] = S.chats[key] || {};
    S.chats[key][agent] = S.chats[key][agent] || [];
    return S.chats[key][agent];
  }
  function curAgent() {
    const r = recipe(), a = S.agent[rk()];
    return r.agents.some((x) => x.id === a) ? a : r.agents[0].id;
  }

  // ------------------------------------------------------------------ navigation · progress
  function stepDone(n) {
    const k = recipeKey();
    if (!k) return false;
    const key = rk();
    if (n === 1) return true;
    if (n === 2) return !!S.seen[k];
    if (n === 3) { const v = S.verify[key]; return !!(v && v.sig === cfgSig() && v.result && v.result.status !== "error"); }
    if (n === 4) return loadedOk(key);
    if (n === 5) return Object.values(S.chats[key] || {}).some((l) => l.some((m) => m.answer && !m.error));
    if (n === 6) return !!(S.evals[key] && S.evals[key].summary);
    return false;
  }
  function go(n) {
    const h = `#step-${n}`;
    if (location.hash !== h) location.hash = h; else show(n);
  }
  function show(n) {
    n = Math.max(1, Math.min(6, Number(n) || 1));
    if (n > 1 && !recipeKey()) { n = 1; history.replaceState(null, "", "#step-1"); }
    S.step = n; save(); render(); window.scrollTo(0, 0);
  }
  function onHash() {
    const m = /^#step-([1-6])$/.exec(location.hash);
    if (m && Number(m[1]) !== S.step) show(Number(m[1]));
  }
  function updateNext(n) {
    const b = $(".step-nav .btn.next");
    if (b && S.step === n) b.classList.toggle("ready", stepDone(n));
  }

  // ------------------------------------------------------------------ chrome
  function renderTop() {
    document.documentElement.lang = S.lang;
    document.title = t("doc_title");
    $("#brand-sub").textContent = t("brand_sub");
    const v = $("#chip-version");
    v.hidden = false; v.textContent = R.settings.version || "";
    const p = $("#chip-project");
    p.hidden = false;
    p.innerHTML = `${esc(t("chip_project"))} <b class="mono">${esc(S.config.project_id || "—")}</b>`;
    const m = $("#chip-mcp"), st = R.mcp == null ? "running" : R.mcp.ok ? "ok" : "error";
    m.hidden = false;
    m.title = R.settings.core_mcp_url || "";
    m.innerHTML = `<span class="dot ${st}"></span>Core MCP <b>${esc(R.mcp == null ? t("chip_mcp_checking") : R.mcp.ok ? t("chip_mcp_tools", { n: R.mcp.count }) : t("chip_mcp_down"))}</b>`;
    if (R.settings.github_url) $("#chip-github").href = R.settings.github_url;
    $("#lang-toggle").setAttribute("aria-label", t("lang_aria"));
    $$("#lang-toggle button").forEach((b) => {
      const on = b.getAttribute("data-lang") === S.lang;
      b.classList.toggle("on", on);
      b.setAttribute("aria-pressed", on ? "true" : "false");
    });
  }
  function renderRail() {
    const r = recipe(), k = recipeKey();
    const done = [1, 2, 3, 4, 5, 6].filter(stepDone).length;
    const kv = (label, val, mono) => `<div class="kv"><span>${esc(label)}</span><span class="${mono === false ? "v" : "mono"}" title="${esc(val)}">${esc(val)}</span></div>`;
    const steps = [1, 2, 3, 4, 5, 6].map((n) => {
      const cls = ["rail-step", S.step === n ? "on" : "", stepDone(n) ? "done" : "", n > 1 && !k ? "locked" : ""].filter(Boolean).join(" ");
      return `<a class="${cls}" href="#step-${n}"${S.step === n ? ' aria-current="step"' : ""}><span class="num">${n}</span><div><div class="t">${esc(t(`step${n}_t`))}</div><div class="s">${esc(t(`step${n}_s`))}</div></div></a>`;
    }).join("");
    const box = r
      ? `<div class="rec">${esc(r.t)}</div><div class="meta mono">${esc(r.s)}</div>${kv(t("kv_project"), S.config.project_id)}`
        + (has(r, "P2") ? kv(t("kv_dataset"), S.config.dataset_id) : "") + (has(r, "P1") ? kv(t("kv_bucket"), S.config.bucket) : "")
        + (k !== "A" ? kv(t("kv_graph"), S.config.graph_name) : "") + kv(t("kv_lang"), t("lang_name"), false)
      : `<div class="muted">${esc(t("rail_none"))}</div>`;
    $("#rail").innerHTML = `<div class="rail-progress"><div class="row"><span>${esc(t("rail_progress"))}</span><b>${done} / 6</b></div><div class="bar"><i style="width:${Math.round((done / 6) * 100)}%"></i></div></div>
      <div class="rail-label">${esc(t("rail_steps"))}</div><nav aria-label="${esc(t("rail_aria"))}">${steps}</nav>
      <div class="rail-box"><div class="ttl">${esc(t("rail_setup"))}</div>${box}</div>`;
  }
  const head = (n, extra) => `<section class="card step-head"><div class="eyebrow">${esc(t(`s${n}_eyebrow`))}</div><h1>${esc(t(`s${n}_title`))}</h1><p>${esc(t(`s${n}_desc`))}</p>${extra || ""}</section>`;
  function nav(n, ready, hint) {
    const next = n < 6
      ? `<button type="button" class="btn next${ready ? " ready" : ""}" data-go="${n + 1}"${n === 1 && !recipeKey() ? " disabled" : ""}>${esc(t("nav_next", { t: t(`step${n + 1}_t`) }))} →</button>`
      : `<button type="button" class="btn" data-go="1">${esc(t("nav_start"))}</button>`;
    return `<div class="step-nav">${n > 1 ? `<button type="button" class="btn" data-go="${n - 1}">← ${esc(t("nav_prev"))}</button>` : ""}<span class="spacer"></span>${hint ? `<span class="hint">${esc(hint)}</span>` : ""}${next}</div>`;
  }
  function render() {
    renderTop();
    renderRail();
    const page = $("#page");
    if (S.step > 1 && !recipeKey()) S.step = 1;
    R.res = null;
    page.innerHTML = [null, step1, step2, step3, step4, step5, step6][S.step]();
    [null, bind1, bind2, bind3, bind4, bind5, bind6][S.step]();
    $$("[data-go]", page).forEach((b) => b.addEventListener("click", () => go(Number(b.getAttribute("data-go")))));
  }

  // ------------------------------------------------------------------ diagrams
  function markChip(host, spec, key) {
    const i = (spec.chips || []).findIndex((c) => c.key === key);
    $$(".af-chip", host).forEach((b) => b.classList.toggle("on", Number(b.getAttribute("data-chip")) === i));
  }
  function renderRes(states) {
    const host = $("#flow-res");
    if (!host) return;
    const fr = STARTER_FLOWS.recipes[recipeKey()];
    const sig = JSON.stringify([S.lang, recipeKey(), states || {}]);
    if (R.res && R.res.host === host && R.res.sig === sig) return;
    const opts = { lang: S.lang, highlight: fr.all ? [] : fr.res, focusStyle: "dim", states: states || {},
      onNode: (id, n) => { if (n && n.nb && Number(n.nb) !== S.step) go(Number(n.nb)); } };
    if (R.res && R.res.host === host) R.res.ctl.update(opts);
    else R.res = { host, ctl: AOLFlow.render(host, STARTER_FLOWS.resources, opts) };
    R.res.sig = sig;
  }

  // ================================================================== step 1 — type & purpose
  function step1() {
    const c = cat(), res = resolved(), r = recipe();
    const sel = (kind, id, on, badge, title, desc, ex) => `<button type="button" class="sel${on ? " on" : ""}" data-${kind}="${id}" aria-pressed="${on ? "true" : "false"}"><span class="check"></span><span class="top">${badge}<span class="ttl">${esc(title)}</span></span><span class="desc">${esc(desc)}</span>${ex ? `<span class="ex">${ex}</span>` : ""}</button>`;
    return head(1)
      + `<section class="card"><div class="card-head"><h3 class="sec-title"><span class="n">1</span>${esc(t("s1_type_title"))}</h3><span class="sub">${esc(t("s1_type_sub"))}</span></div>
        <div class="sel-grid">${c.types.map((x) => sel("type", x.id, S.type === x.id, `<span class="lane-pill">${esc(x.id)}</span>`, x.t, x.s, esc(x.meta))).join("")}</div></section>`
      + `<section class="card"><div class="card-head"><h3 class="sec-title"><span class="n">2</span>${esc(t("s1_purpose_title"))}</h3><span class="sub">${esc(t("s1_purpose_sub"))}</span></div>
        <div class="sel-grid">${c.purposes.map((x) => sel("purpose", x.id, S.purpose === x.id, `<span class="wbadge">${esc(x.id)}</span>`, x.t, x.s, `<span class="k">${esc(t("s1_example"))}</span> ${esc(x.q)}`)).join("")}</div></section>`
      + recipeCard(res, r)
      + nav(1, !!r, r ? "" : t("nav_hint_select"));
  }
  function mcpTools(r) {
    const out = [];
    r.load_plan.forEach((s) => String(s.core_mcp || "").split("+").forEach((x) => {
      x = x.replace(/\(.*?\)/g, "").trim();
      if (x && out.indexOf(x) < 0) out.push(x);
    }));
    return out;
  }
  function recipeCard(res, r) {
    if (!r) return `<section class="card"><div class="card-head"><h3>${esc(t("s1_recipe_title"))}</h3></div><div class="empty">${esc(t("s1_recipe_empty"))}</div></section>`;
    const c = cat(), tools = mcpTools(r);
    const li = (color, html) => `<li><span class="ld" style="background:${color}"></span><span class="lt">${html}</span></li>`;
    const creates = [];
    if (has(r, "P1")) creates.push(li("var(--c-wiki)", `${esc(t("s1_create_gcs", { docs: c.data.docs.length, pages: r.wiki_pages.length }))}<br><span class="k mono">${esc(t("s1_create_gcs_where", { bucket: S.config.bucket, lang: S.lang }))}</span>`));
    else creates.push(li("var(--line-2)", `<span class="k">${esc(t("s1_create_nogcs"))}</span>`));
    if (has(r, "P2")) {
      creates.push(li("var(--c-source)", `${esc(t("s1_create_bq", { n: r.tables.length }))}<br><span class="k mono">${esc(S.config.project_id)}.${esc(S.config.dataset_id)}</span>`));
      creates.push(li("var(--c-semantic)", esc(t("s1_create_graph", { g: S.config.graph_name }))));
    } else creates.push(li("var(--line-2)", `<span class="k">${esc(t("s1_create_nograph"))}</span>`));
    return `<section class="card">
      <div class="card-head"><h3>${esc(t("s1_recipe_title"))}</h3><span class="right"><span class="tag">${dot(res.exact ? "ok" : "warn")}${esc(res.exact ? t("s1_exact") : t("s1_widened"))}</span></span></div>
      <div class="recipe-top"><span class="recipe-key">${esc(r.key)}</span><div><div class="recipe-name">${esc(r.t)}</div><div class="recipe-sub mono">${esc(r.s)}</div></div></div>
      <p class="recipe-d">${esc(r.d)}</p>${res.reason ? `<div class="note">${esc(res.reason)}</div>` : ""}
      <div class="cols3">
        <div class="box"><div class="ttl">${esc(t("s1_agents"))}</div><ul>${r.agents.map((a) => li("var(--c-agent)", `<b>${esc(a.name)}</b><br><span class="k">${esc(a.s)}</span>`)).join("")}</ul></div>
        <div class="box"><div class="ttl">${esc(t("s1_creates"))}</div><ul>${creates.join("")}</ul></div>
        <div class="box"><div class="ttl">${esc(t("s1_eval_mcp"))}</div><ul>${li("var(--c-workflow)", esc(t("s1_eval_cq", { n: r.cq_count })))}${li("var(--c-mcp)", `${esc(t("s1_mcp_tools", { n: tools.length }))}<br><span class="k mono">${tools.map(esc).join(" · ")}</span>`)}</ul></div>
      </div></section>`;
  }
  function bind1() {
    $$("[data-type]").forEach((b) => b.addEventListener("click", () => choose(b.getAttribute("data-type"), S.purpose)));
    $$("[data-purpose]").forEach((b) => b.addEventListener("click", () => choose(S.type, b.getAttribute("data-purpose"))));
  }

  // ================================================================== step 2 — flow
  function planRow(p) {
    const what = fill(p.what);
    return `<li><span class="stepno ${STEP_CLASS[p.step] || ""}">${p.step}</span><div><div class="pt">${esc(p.t)}</div>`
      + `<div class="pw${p.step === 4 ? " mono" : ""}">${esc(what)}</div>${p.core_mcp ? `<div class="mcp-line">Core MCP · ${esc(p.core_mcp)}</div>` : ""}</div>`
      + `<div class="right"><span class="tag">${esc(p.service)}</span></div></li>`;
  }
  function step2() {
    const r = recipe();
    S.seen[r.key] = true;
    save();
    return head(2)
      + `<section class="card"><div class="card-head"><h2>${esc(AOLFlow.T(STARTER_FLOWS.dataflow.title, S.lang))}</h2><span class="right"><span class="tag"><b>${esc(r.t)}</b>${esc(r.s)}</span></span></div><div class="flow-host" id="flow-data"></div></section>`
      + `<section class="card"><div class="card-head"><h2>${esc(t("s2_plan_title"))}</h2><span class="sub">${esc(t("s2_plan_sub"))}</span></div><ol class="plan">${r.step_plan.map(planRow).join("")}</ol></section>`
      + nav(2, true);
  }
  function bind2() {
    const k = recipeKey(), fr = STARTER_FLOWS.recipes[k], host = $("#flow-data");
    AOLFlow.render(host, STARTER_FLOWS.dataflow, { lang: S.lang, highlight: fr.all ? [] : fr.nodes, highlightEdges: fr.all ? [] : fr.edges, focusStyle: "dim",
      onNode: (id, n) => { if (n && n.nb && Number(n.nb) !== 2) go(Number(n.nb)); },
      onChip: (ch) => { if (ch && CANON[ch.key] && ch.key !== recipeKey()) choose(CANON[ch.key][0], CANON[ch.key][1]); } });
    markChip(host, STARTER_FLOWS.dataflow, k);
    renderRail();
  }

  // ================================================================== step 3 — GCP resources
  function field(f, o) {
    o = o || {};
    const help = o.help != null ? o.help : hasT(`h_${f}`) ? t(`h_${f}`) : "";
    return `<div class="field${o.full ? " full" : ""}" data-field="${f}"><label for="f-${f}">${esc(t(`f_${f}`))}${o.optional ? `<span class="opt">${esc(t("f_optional"))}</span>` : ""}</label>`
      + `<input id="f-${f}" name="${f}" value="${esc(S.config[f])}" spellcheck="false" autocomplete="off" autocapitalize="off"${o.disabled ? " disabled" : ""}>`
      + `${help ? `<span class="help">${esc(help)}</span>` : ""}<span class="err" hidden></span></div>`;
  }
  function step3() {
    const k = recipeKey(), wp = (R.settings.write_projects || []).join(", ");
    const guard = `<div class="note${writeAllowed(S.config.project_id) ? "" : " warn"}">${esc(t("write_guard", { p: wp }))}</div>`;
    return head(3)
      + `<section class="card"><div class="card-head"><h2>${esc(t("s3_form_title"))}</h2><span class="right"><button type="button" class="btn small" id="cfg-defaults">${esc(t("btn_defaults"))}</button></span></div>
        <div class="form">${field("project_id")}${field("region")}${field("dataset_id")}${field("bucket")}
          ${field("graph_name", { disabled: k === "A", help: k === "A" ? t("h_graph_name_A") : t("h_graph_name") })}${field("model")}${field("vertex_location")}
          <div class="field toggle-field"><label class="toggle"><input type="checkbox" id="cfg-spanner"${S.spanner && k !== "A" ? " checked" : ""}${k === "A" ? " disabled" : ""}>${esc(t("f_spanner_toggle"))}</label></div>
          ${S.spanner && k !== "A" ? field("spanner_instance", { optional: true, help: "" }) + field("spanner_database", { optional: true, help: "" }) : ""}
        </div>${guard}
        <div class="form-actions"><button type="button" class="btn primary" id="btn-verify"${R.busy.verify ? " disabled" : ""}>${esc(R.busy.verify ? t("btn_verifying") : t("btn_verify"))}</button></div>
      </section>`
      + `<section class="card" id="verify-card"><div class="card-head"><h2>${esc(t("s3_results"))}</h2><span class="right meta" id="verify-sum"></span></div><div id="verify-body"></div></section>`
      + `<section class="card"><div class="card-head"><h2>${esc(AOLFlow.T(STARTER_FLOWS.resources.title, S.lang))}</h2></div><div class="flow-host" id="flow-res"></div></section>`
      + iamFold()
      + nav(3, stepDone(3));
  }
  function iamFold() {
    const rows = cat().iam.map((x) => `<tr><td class="nowrap">${esc(t("step_n", { n: x.step }))}</td><td class="mono">${esc(x.role)}</td><td>${esc(x.scope)}</td><td>${esc(x.why)}</td></tr>`).join("");
    return `<details class="fold fold-card"><summary>${esc(t("s3_iam_title"))}<span class="meta">${esc(t("s3_iam_sub"))}</span></summary><div class="inner"><div class="tbl-wrap"><table class="tbl"><thead><tr><th>${esc(t("iam_step"))}</th><th>${esc(t("iam_role"))}</th><th>${esc(t("iam_scope"))}</th><th>${esc(t("iam_why"))}</th></tr></thead><tbody>${rows}</tbody></table></div></div></details>`;
  }
  function fixBox(fix) {
    return `<div class="fix"><div class="row-flex"><b>${esc(t("s3_fix"))}</b>${fix.role && fix.role !== "-" ? `<span class="tag mono">${esc(fix.role)}</span>` : ""}<span class="spacer"></span><button type="button" class="btn small" data-copy="${esc(fix.command)}">${esc(t("copy"))}</button></div><code>${esc(fix.command)}</code></div>`;
  }
  function verifyStates() {
    const v = S.verify[rk()], res = v && v.result, st = {};
    if (!res) return st;
    const map = { gcs: "gcs", bigquery: "bq", graph: "graph", vertex: "gemini", core_mcp: "app" };
    (res.checks || []).forEach((c) => {
      const node = map[c.id], s = norm(c.status);
      if (node && s === "ok") st[node] = "done";
      if (node && s === "error") st[node] = "error";
    });
    return st;
  }
  function paintVerify() {
    const box = $("#verify-body");
    if (!box) return;
    const v = S.verify[rk()], res = v && v.result, sum = $("#verify-sum");
    if (!res) {
      box.innerHTML = `<div class="empty">${esc(t("s3_results_empty"))}</div>`;
      sum.textContent = "";
    } else {
      const cs = res.checks || [], n = (s) => cs.filter((c) => norm(c.status) === s).length;
      sum.textContent = t("s3_summary", { n: cs.length, ok: n("ok"), warn: n("warn"), err: n("error"), sec: fmtMs(res.elapsed_ms) });
      box.innerHTML = (v.sig !== cfgSig() ? `<div class="note warn">${esc(t("s3_stale"))}</div>` : "")
        + `<div class="checks">${cs.map((c) => `<div class="check-row">${dot(c.status)}<div><div class="l1"><span class="lbl">${esc(c.label)}</span><span class="tgt">${esc(c.target)}</span></div><div class="det">${esc(c.detail)}</div><div class="api-line">${esc(c.api)}</div>${c.fix && c.fix.command ? fixBox(c.fix) : ""}</div><div class="ms">${c.ms ? fmtMs(c.ms) : ""}</div></div>`).join("")}</div>`;
      bindCopy(box);
    }
    renderRes(verifyStates());
  }
  function fieldErr(f, msg) {
    const el = $(`.field[data-field="${f}"]`);
    if (!el) { toast(msg); return; }
    el.classList.add("invalid");
    const e = $(".err", el);
    e.textContent = msg; e.hidden = false;
  }
  function clearErr() {
    $$(".field.invalid").forEach((el) => { el.classList.remove("invalid"); const e = $(".err", el); e.hidden = true; e.textContent = ""; });
  }
  async function runVerify() {
    if (R.busy.verify) return;
    const key = rk(), sig = cfgSig(), req = body();
    R.busy.verify = true;
    const b = $("#btn-verify");
    if (b) { b.disabled = true; b.textContent = t("btn_verifying"); }
    clearErr();
    try {
      S.verify[key] = { sig, result: await postJSON("/api/verify", req), at: Date.now() };
    } catch (e) {
      if (e.payload && e.payload.status === "CONFIG_ERROR") fieldErr(e.payload.field, e.payload.message);
      else toast(`${t("err_prefix")} · ${e.message || t("err_network")}`);
    } finally {
      R.busy.verify = false;
      save(true);
    }
    if (S.step === 3) {
      const b2 = $("#btn-verify");
      if (b2) { b2.disabled = false; b2.textContent = t("btn_verify"); }
      paintVerify(); renderRail(); updateNext(3);
      const card = $("#verify-card");
      if (card && S.verify[key]) card.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }
  function bind3() {
    FIELDS.forEach((f) => {
      const el = $(`#f-${f}`);
      if (!el) return;
      el.addEventListener("input", () => {
        S.config[f] = el.value.trim();
        if (f === "graph_name") S.graphCustom = true;
        const fe = el.closest(".field");
        if (fe && fe.classList.contains("invalid")) { fe.classList.remove("invalid"); $(".err", fe).hidden = true; }
        save(); renderTop(); renderRail(); paintVerify(); updateNext(3);
      });
    });
    $("#cfg-defaults").addEventListener("click", () => { ensureConfig(true); save(); render(); });
    $("#cfg-spanner").addEventListener("change", (ev) => { S.spanner = !!ev.target.checked; save(); render(); });
    $("#btn-verify").addEventListener("click", runVerify);
    paintVerify();
  }

  // ================================================================== step 4 — load
  const planSteps = (r) => r.load_plan.map((s) => ({ key: s.key, node: s.node, service: s.service, core_mcp: s.core_mcp, label: s.t, target: fill(s.target), status: "idle" }));
  function step4() {
    const r = recipe(), key = rk(), run = loadRun(key), v = S.verify[key];
    const busy = !!(R.runs.load[key] && R.runs.load[key].status === "running");
    const tag = (k, val) => `<span class="tag"><span>${esc(k)}</span><b class="mono">${esc(val)}</b></span>`;
    const tags = [tag(t("kv_project"), S.config.project_id)];
    if (has(r, "P1")) tags.push(tag(t("kv_bucket"), `gs://${S.config.bucket}/starter/${S.lang}/`));
    if (has(r, "P2")) tags.push(tag(t("kv_dataset"), `${S.config.project_id}.${S.config.dataset_id}`), tag(t("kv_graph"), S.config.graph_name));
    const notes = [`<div class="note">${esc(t("s4_lang_note"))}</div>`];
    if (!v || v.sig !== cfgSig()) notes.push(`<div class="note">${esc(t("s4_not_verified"))} <a href="#step-3">${esc(t("step3_t"))} →</a></div>`);
    if (!writeAllowed(S.config.project_id)) notes.push(`<div class="note err">${esc(t("write_guard", { p: (R.settings.write_projects || []).join(", ") }))}</div>`);
    return head(4)
      + `<section class="card"><div class="card-head"><h2>${esc(t("s4_run_title"))}</h2><span class="sub">${esc(r.t)}</span><span class="right"><button type="button" class="btn primary" id="btn-load"${busy ? " disabled" : ""}>${esc(busy ? t("s4_running") : run ? t("s4_rerun") : t("s4_run"))}</button></span></div>
        <div class="row-flex">${tags.join("")}</div>${notes.join("")}<div id="load-summary"></div></section>`
      + `<section class="card"><div class="card-head"><h2>${esc(t("s4_steps"))}</h2><span class="right meta" id="load-elapsed"></span></div><ol class="plan" id="load-steps"></ol></section>`
      + `<section class="card"><div class="card-head"><h2>${esc(AOLFlow.T(STARTER_FLOWS.resources.title, S.lang))}</h2></div><div class="flow-host" id="flow-res"></div></section>`
      + `<section class="card"><div class="card-head"><h2>${esc(t("s4_log"))}</h2><span class="right meta" id="log-count"></span></div><div id="load-log"></div><div id="load-extra"></div></section>`
      + nav(4, stepDone(4));
  }
  function loadStates(run) {
    const st = {};
    if (!run) return st;
    const by = {};
    run.steps.forEach((s) => { (by[s.node] = by[s.node] || []).push(norm(s.status)); });
    Object.keys(by).forEach((n) => {
      const a = by[n];
      if (a.indexOf("error") >= 0) st[n] = "error";
      else if (a.indexOf("running") >= 0) st[n] = "running";
      else if (a.every((x) => x === "ok" || x === "warn")) st[n] = "done";
    });
    if (run.status === "running") { st.pack = "done"; st.app = "running"; }
    else if (run.status === "SUCCESS" || run.status === "PARTIAL") { st.pack = "done"; st.app = "done"; }
    else if (run.status === "ERROR" || run.status === "WRITE_BLOCKED") st.app = "error";
    return st;
  }
  function rowsTable(rows) {
    if (!rows || !rows.length) return "";
    const cols = Object.keys(rows[0]).slice(0, 8);
    return `<div class="tbl-wrap"><table class="tbl mini"><thead><tr>${cols.map((c) => `<th class="mono">${esc(c)}</th>`).join("")}</tr></thead><tbody>${rows.slice(0, 8).map((r) => `<tr>${cols.map((c) => `<td>${esc(fmtCell(r[c]))}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;
  }
  function metric(k, v, s, cls) {
    return `<div class="metric"><div class="k">${esc(k)}</div><div class="v${cls ? ` ${cls}` : ""}">${v}</div>${s ? `<div class="s">${s}</div>` : ""}</div>`;
  }
  function paintLoad() {
    if (S.step !== 4 || !$("#load-steps")) return;
    const key = rk(), run = loadRun(key), r = recipe();
    const steps = run ? run.steps : planSteps(r);
    $("#load-steps").innerHTML = steps.map((s) => `<li>${dot(s.status)}<div><div class="pt">${esc(s.label)}</div><div class="pw mono">${esc(s.target)}</div>`
      + `${s.core_mcp ? `<div class="mcp-line">Core MCP · ${esc(s.core_mcp)}</div>` : ""}${s.detail && s.detail !== s.target ? `<div class="pw">${esc(s.detail)}</div>` : ""}</div>`
      + `<div class="right"><span class="tag">${esc(s.service)}</span><span class="st"><b>${esc(stText(norm(s.status) === "ok" ? "done" : norm(s.status)))}</b>${s.ms != null ? ` · ${fmtMs(s.ms)}` : ""}</span></div></li>`).join("");
    $("#load-elapsed").textContent = run ? fmtMs(run.ms != null ? run.ms : Date.now() - run.t0) : "";
    const logs = run ? run.logs : [];
    $("#log-count").textContent = logs.length ? t("s4_log_count", { n: logs.length }) : "";
    const label = (k) => { const s = steps.find((x) => x.key === k); return s ? s.label : k; };
    $("#load-log").innerHTML = logs.length
      ? `<div class="tbl-wrap log"><table class="tbl"><thead><tr><th>${esc(t("col_step"))}</th><th>${esc(t("col_api"))}</th><th>${esc(t("col_target"))}</th><th class="num">${esc(t("col_count"))}</th><th class="num">${esc(t("col_ms"))}</th><th>${esc(t("col_status"))}</th></tr></thead><tbody>`
        + logs.map((l) => `<tr><td class="stepc">${esc(label(l.key))}</td><td><div class="api">${esc(l.api)}</div>${l.detail ? `<div class="det">${esc(l.detail)}</div>` : ""}</td><td><div class="tgt">${esc(l.target)}</div>${l.job_id ? `<div class="tgt faint">${esc(l.job_id)}</div>` : ""}</td>`
          + `<td class="num">${l.count != null ? `${esc(fmtNum(l.count))}${l.unit ? ` <span class="faint">${esc(l.unit)}</span>` : ""}` : "—"}</td><td class="tm">${fmtMs(l.ms)}</td><td>${dot(l.status)}</td></tr>`).join("")
        + `</tbody></table></div>`
      : `<div class="empty">${esc(t("s4_log_empty"))}</div>`;
    let sum = "";
    if (run && run.status !== "running") {
      const s = run.summary || {}, gc = s.graph_check || null;
      const cells = [metric(t("m_status"), `${dot(run.status)}${esc(stText(run.status))}`, "", "sm")];
      if (has(r, "P1")) cells.push(metric(t("m_objects"), esc(fmtNum(s.objects)), s.gcs_prefix ? `<span class="mono">${esc(s.gcs_prefix)}</span>` : ""));
      if (has(r, "P2")) cells.push(metric(t("m_tables"), esc(fmtNum(s.tables)), s.rows != null ? esc(t("m_rows_n", { n: fmtNum(s.rows) })) : ""));
      if (!has(r, "P2") && s.gate0) cells.push(metric("Gate 0", esc(s.gate0.status || "—"), esc(t("m_gate0", { f: s.gate0.fidelity != null ? s.gate0.fidelity : "—", n: s.gate0.anchors != null ? s.gate0.anchors : "—" }))));
      if (has(r, "P2") && !has(r, "P1")) {
        const paths = gc ? Object.values(gc).reduce((a, v) => a + (Number(v) || 0), 0) : null;
        cells.push(metric(t("m_graph_paths"), esc(fmtNum(paths)), gc ? `<span class="mono">${esc(Object.entries(gc).map(([k, v]) => `${k}=${v}`).join(" · "))}</span>` : ""));
      }
      cells.push(metric(t("m_elapsed"), esc(fmtMs(run.ms)), s.graph ? `<span class="mono">${esc(s.graph)}</span>` : ""));
      sum = `<div class="metrics load-metrics">${cells.join("")}</div>`;
      if (run.error) sum += `<div class="note err">${esc(run.error)}</div>${run.fix && run.fix.command ? fixBox(run.fix) : ""}`;
    }
    $("#load-summary").innerHTML = sum;
    bindCopy($("#load-summary"));
    let extra = "";
    if (run && run.ddl) extra += `<details class="fold"><summary>${esc(t("s4_ddl"))}<span class="meta mono">${esc((run.summary && run.summary.graph) || S.config.graph_name)}</span></summary><div class="inner"><pre class="code">${esc(run.ddl)}</pre></div></details>`;
    if (run && run.gql) extra += `<details class="fold"><summary>${esc(t("s4_gql"))}</summary><div class="inner"><pre class="code">${esc(run.gql.sql)}</pre>${rowsTable(run.gql.rows)}</div></details>`;
    $("#load-extra").innerHTML = extra;
    $("#load-extra").classList.toggle("has", !!extra);
    renderRes(loadStates(run));
  }
  async function runLoad() {
    const key = rk(), r = recipe();
    if (R.runs.load[key] && R.runs.load[key].status === "running") return;
    const run = { status: "running", steps: planSteps(r), logs: [], t0: Date.now() };
    R.runs.load[key] = run;
    const b = $("#btn-load");
    if (b) { b.disabled = true; b.textContent = t("s4_running"); }
    paintLoad();
    R.timers.tick = setInterval(() => { if (S.step === 4 && rk() === key) { const el = $("#load-elapsed"); if (el) el.textContent = fmtMs(Date.now() - run.t0); } }, 1000);
    try {
      await stream("/api/load", body(), (ev) => {
        if (ev.type === "plan") run.steps = (ev.steps || []).map((s) => Object.assign({ status: "idle" }, s));
        else if (ev.type === "step") {
          const s = run.steps.find((x) => x.key === ev.key);
          if (s) { s.status = ev.status; if (ev.ms != null) s.ms = ev.ms; if (ev.detail != null) s.detail = ev.detail; }
        } else if (ev.type === "log") run.logs.push(ev);
        else if (ev.type === "ddl") run.ddl = ev.sql;
        else if (ev.type === "gql") run.gql = { sql: ev.sql, rows: ev.rows || [] };
        else if (ev.type === "error") { run.error = ev.message; run.fix = ev.fix || null; }
        else if (ev.type === "done") { run.status = ev.status; run.ms = ev.ms; run.summary = ev.summary || null; }
        if (rk() === key) later("load", paintLoad);
      });
    } catch (e) {
      run.error = (e.payload && e.payload.message) || e.message || t("err_network");
      run.status = "ERROR";
    }
    clearInterval(R.timers.tick);
    if (run.status === "running") run.status = run.error ? "ERROR" : "PARTIAL";
    if (run.ms == null) run.ms = Date.now() - run.t0;
    delete run.t0;
    S.load[key] = run;
    delete R.runs.load[key];
    save(true);
    if (S.step === 4 && rk() === key) render(); else renderRail();
  }
  function bind4() {
    $("#btn-load").addEventListener("click", runLoad);
    paintLoad();
  }

  // ================================================================== step 5 — agents
  const presetsFor = (agent) => ((cat().presets || {})[recipeKey()] || {})[agent] || [];
  const agentName = (id) => ((cat().agents || {})[id] || {}).name || id;
  function step5() {
    const r = recipe(), key = rk(), agent = curAgent(), a = r.agents.find((x) => x.id === agent);
    const reads = agent === "wiki" ? `gs://${S.config.bucket}/starter/${S.lang}/wiki/` : `${S.config.project_id}.${S.config.dataset_id} · ${S.config.graph_name}`;
    const busy = !!R.busy[`${key}:${agent}`];
    return head(5, loadedOk(key) ? "" : `<div class="note warn">${esc(t("s5_not_loaded"))} <a href="#step-4">${esc(t("step4_t"))} →</a></div>`)
      + `<div class="grid-chat">
        <section class="card chat-card"><div class="card-head"><div class="seg" id="agent-seg">${r.agents.map((x) => `<button type="button" data-agent="${x.id}" class="${x.id === agent ? "on" : ""}">${esc(x.name)}</button>`).join("")}</div><span class="right"><button type="button" class="btn small" id="chat-clear">${esc(t("s5_clear"))}</button></span></div>
          <div class="agent-desc">${esc(a.s)}</div>
          <div class="agent-meta"><span>${esc(t("s5_reads"))}</span><span class="mono">${esc(reads)}</span></div>
          <div class="chat" id="chat"></div>
          <div class="presets-wrap"><div class="ev-h">${esc(t("s5_presets"))}</div><div class="presets" id="presets">${presetsFor(agent).map((q, i) => `<button type="button" class="preset" data-q="${i}"${busy ? " disabled" : ""}>${esc(q)}</button>`).join("")}</div></div>
          <div class="composer"><textarea id="ask" rows="2" placeholder="${esc(t("s5_placeholder"))}"></textarea><button type="button" class="btn primary" id="btn-ask"${busy ? " disabled" : ""}>${esc(busy ? t("s5_sending") : t("s5_send"))}</button></div>
        </section>
        <aside class="card evidence" id="evidence"></aside>
      </div>`
      + nav(5, stepDone(5));
  }
  function msgHtml(m, agent, sel) {
    const running = !m.done;
    const stCode = running ? "running" : m.error && !m.answer ? "error" : m.status || "";
    const steps = running && (m.steps || []).length
      ? `<ul class="live-steps">${m.steps.map((s) => `<li>${dot(s.status)}<span class="lt">${esc(s.label || s.step || s.id)}</span>${s.ms != null ? `<span class="ms">${fmtMs(s.ms)}</span>` : ""}</li>`).join("")}</ul>` : "";
    const err = m.error && m.error !== m.answer ? `<div class="note err">${esc(m.error)}</div>` : "";
    return `<div class="msg user"><div class="who"><b>${esc(t("s5_you"))}</b></div><div class="bubble">${esc(m.q)}</div></div>`
      + `<div class="msg agent${sel ? " sel" : ""}" data-id="${m.id}"><div class="who"><span class="ld"></span><b>${esc(agentName(agent))}</b>`
      + `<span class="st">${dot(stCode)}${esc(running ? t("st_running") : stCode)}</span>${m.ms ? `<span class="meta">${fmtMs(m.ms)}</span>` : ""}</div>`
      + `<div class="bubble">${steps}${m.answer ? `<div class="md">${md(m.answer)}</div>` : running && !steps ? `<div class="meta">${esc(t("s5_sending"))}</div>` : ""}${err}</div></div>`;
  }
  const isActive = (key, agent) => S.step === 5 && rk() === key && curAgent() === agent;
  function paintChat() {
    const box = $("#chat");
    if (!box) return;
    const key = rk(), agent = curAgent(), list = chats(key, agent), selId = S.sel[`${key}:${agent}`];
    if (!list.length) box.innerHTML = `<div class="empty">${esc(t("s5_empty"))}</div>`;
    else {
      const chosen = list.some((m) => m.id === selId) ? selId : list[list.length - 1].id;
      box.innerHTML = list.map((m) => msgHtml(m, agent, m.id === chosen)).join("");
      $$(".msg.agent", box).forEach((el) => el.addEventListener("click", () => {
        S.sel[`${key}:${agent}`] = Number(el.getAttribute("data-id"));
        save();
        $$(".msg.agent", box).forEach((x) => x.classList.toggle("sel", x === el));
        paintEvidence();
      }));
      box.scrollTop = box.scrollHeight;
    }
    paintEvidence();
  }
  function paintEvidence() {
    const box = $("#evidence");
    if (!box) return;
    const key = rk(), agent = curAgent(), list = chats(key, agent), selId = S.sel[`${key}:${agent}`];
    const m = list.find((x) => x.id === selId) || list[list.length - 1];
    const headHtml = (sub) => `<div class="card-head"><h2>${esc(t("s5_ev_title"))}</h2>${sub || ""}</div>`;
    if (!m || (!m.evidence && !(m.steps || []).length)) { box.innerHTML = headHtml("") + `<div class="empty">${esc(t("s5_ev_empty"))}</div>`; return; }
    const ev = m.evidence || {};
    const sec = (title, html, right) => (html ? `<div class="ev-sec"><div class="ev-h">${esc(title)}${right ? `<span class="right">${right}</span>` : ""}</div>${html}</div>` : "");
    const status = m.done ? `<div class="row-flex">${dot(m.error && !m.answer ? "error" : m.status)}<b class="mono">${esc(m.status || "-")}</b><span class="meta">${esc(agentName(agent))} · ${fmtMs(m.ms)}</span></div>` : `<div class="row-flex">${dot("running")}<b>${esc(t("st_running"))}</b></div>`;
    const cites = citedIds(m.answer);
    const refs = (ev.refs || []).map((r) => {
      const c = r.cited || cites.has(r.id);
      let title = String(r.title || "");
      if (title.indexOf(r.id) === 0) title = title.slice(String(r.id).length).trim();
      return `<div class="ref"><span class="dot ${c ? "ok" : "idle"}"></span><div class="lt"><b class="mono">${esc(r.id)}</b>${title ? ` ${esc(title)}` : ""}${c ? ` <span class="tag">${esc(t("s5_ev_cited"))}</span>` : ""}${r.uri ? `<div class="uri">${esc(r.uri)}</div>` : r.kind ? `<div class="uri">${esc(r.kind)}</div>` : ""}</div></div>`;
    }).join("");
    const queries = (ev.queries || []).filter((q) => q.sql || (q.rows || []).length).map((q) => `<div class="q"><div class="row-flex"><b class="mono">${esc(q.tool)}</b><span class="tag mono">${esc(q.kind)}</span><span class="meta">${esc(t("s5_ev_rows", { n: q.row_count || 0 }))} · ${fmtMs(q.ms)}</span></div>${q.sql ? `<pre class="code sql">${esc(q.sql)}</pre>` : ""}${rowsTable(q.rows)}</div>`).join("");
    const tools = (ev.tools || []).map((x) => `<div class="ref">${dot(x.status)}<div class="lt"><b class="mono">${esc(x.name)}</b> <span class="meta">${fmtMs(x.ms)}</span>${x.detail ? `<div class="uri">${esc(x.detail)}</div>` : ""}</div></div>`).join("");
    const w = ev.workflow;
    const wf = w ? `<div class="row-flex"><span class="wbadge">${esc(w.point)}</span><b>${esc(w.name)}</b><span class="tag mono">${esc(w.workflow_id)}</span>${w.outcome ? `<span class="outcome">${esc(w.outcome)}</span>` : ""}</div><div class="wf-strip">${(w.steps || []).map((s) => `<div class="wf-step">${dot(s.status === "done" ? "ok" : s.status)}<div><div class="nm"><span class="mono">${esc(s.step_id)}</span> ${esc(s.name)}</div>${s.detail ? `<div class="dt">${esc(s.detail)}</div>` : ""}</div></div>`).join("")}</div>` : "";
    const g = ev.g2w;
    const g2w = g ? `<div class="row-flex">${dot(g.status)}<b class="mono">${esc(g.status)}</b><span class="meta">${fmtMs(g.ms)}</span></div><div class="uri">${esc(g.source)}</div>`
      + `<div class="tbl-wrap"><table class="tbl mini"><thead><tr><th>${esc(t("g2w_key"))}</th><th class="num">${esc(t("g2w_wiki"))}</th><th class="num">${esc(t("g2w_ledger"))}</th><th class="num">${esc(t("g2w_graph"))}</th><th>${esc(t("g2w_match"))}</th></tr></thead><tbody>`
      + (g.rows || []).map((x) => `<tr><td class="mono">${esc(x.key)}</td><td class="num">${esc(fmtCell(x.wiki))}</td><td class="num">${esc(fmtCell(x.ledger))}</td><td class="num">${esc(fmtCell(x.graph))}</td><td>${dot(x.match ? "ok" : "error")}</td></tr>`).join("") + `</tbody></table></div>` : "";
    const params = Object.keys(ev.params || {}).length ? `<dl class="kvs">${Object.entries(ev.params).map(([k, v]) => `<dt class="mono">${esc(k)}</dt><dd>${esc(fmtCell(v))}</dd>`).join("")}</dl>` : "";
    const notes = (ev.notes || []).length ? `<ul class="notes">${ev.notes.map((x) => `<li>${esc(fmtCell(x))}</li>`).join("")}</ul>` : "";
    const steps = (m.steps || []).length ? `<ul class="live-steps">${m.steps.map((s) => `<li>${dot(s.status)}<span class="lt">${esc(s.label || s.step || s.id)}</span>${s.ms != null ? `<span class="ms">${fmtMs(s.ms)}</span>` : ""}</li>`).join("")}</ul>` : "";
    const tm = ev.timing || {};
    const jobs = (tm.job_ids || []).length ? `${tm.job_ids.slice(0, 3).join(", ")}${tm.job_ids.length > 3 ? ` (+${tm.job_ids.length - 3})` : ""}` : null;
    const kv = [[t("tm_model"), tm.model], [t("tm_location"), tm.location], [t("tm_tokens"), tm.tokens_in != null ? `${tm.tokens_in} / ${tm.tokens_out}` : null],
      [t("tm_llm"), tm.llm_ms != null ? fmtMs(tm.llm_ms) : null], [t("tm_gcs"), tm.gcs_ms != null ? fmtMs(tm.gcs_ms) : null],
      [t("tm_total"), tm.total_ms ? fmtMs(tm.total_ms) : m.ms ? fmtMs(m.ms) : null], [t("tm_dataset"), tm.dataset], [t("tm_graph"), tm.graph], [t("tm_jobs"), jobs]]
      .filter((x) => x[1] != null && x[1] !== "");
    const timing = kv.length ? `<dl class="kvs">${kv.map(([k, v]) => `<dt>${esc(k)}</dt><dd class="mono">${esc(v)}</dd>`).join("")}</dl>` : "";
    box.innerHTML = headHtml(`<span class="sub">${esc(m.q.length > 60 ? `${m.q.slice(0, 59)}…` : m.q)}</span>`)
      + sec(t("s5_ev_status"), status) + sec(t("s5_ev_workflow"), wf) + sec(t("s5_ev_g2w"), g2w) + sec(t("s5_ev_refs"), refs)
      + sec(t("s5_ev_queries"), queries) + sec(t("s5_ev_tools"), tools, esc(t("s5_ev_tools_sub"))) + sec(t("s5_ev_params"), params)
      + sec(t("s5_ev_notes"), notes) + sec(t("s5_ev_steps"), steps) + sec(t("s5_ev_timing"), timing);
  }
  function setAskBusy(busy) {
    const b = $("#btn-ask");
    if (b) { b.disabled = busy; b.textContent = busy ? t("s5_sending") : t("s5_send"); }
    $$("#presets .preset").forEach((p) => { p.disabled = busy; });
  }
  async function ask(agent, q) {
    const key = rk(), bkey = `${key}:${agent}`;
    if (R.busy[bkey] || !q) return;
    const req = body({ agent, question: q });
    const list = chats(key, agent);
    const m = { id: Date.now(), q, steps: [], done: false, t0: Date.now() };
    list.push(m);
    while (list.length > MAX_MSGS) list.shift();
    S.sel[bkey] = m.id;
    R.busy[bkey] = true;
    paintChat(); setAskBusy(true);
    try {
      await stream("/api/agent", req, (ev) => {
        if (ev.type === "step") {
          const id = ev.step || ev.label || `s${m.steps.length}`;
          const s = m.steps.find((x) => x.id === id);
          if (s) Object.assign(s, ev); else m.steps.push(Object.assign({ id }, ev));
        } else if (ev.type === "result") {
          m.status = ev.status; m.answer = ev.answer; m.evidence = ev.evidence || null;
          if (ev.error) m.error = ev.error;
        } else if (ev.type === "error") m.error = ev.message;
        if (isActive(key, agent)) later("chat", paintChat, 80);
      });
    } catch (e) {
      m.error = (e.payload && e.payload.message) || e.message || t("err_network");
    }
    if (!m.status) m.status = m.error ? "ERROR" : "-";
    m.done = true; m.ms = Date.now() - m.t0; delete m.t0;
    R.busy[bkey] = false;
    save(true);
    if (isActive(key, agent)) { paintChat(); setAskBusy(false); renderRail(); updateNext(5); } else renderRail();
  }
  function bind5() {
    const key = rk();
    $$("#agent-seg [data-agent]").forEach((b) => b.addEventListener("click", () => { S.agent[key] = b.getAttribute("data-agent"); save(); render(); }));
    $$("#presets [data-q]").forEach((b) => b.addEventListener("click", () => { const a = curAgent(); ask(a, presetsFor(a)[Number(b.getAttribute("data-q"))]); }));
    const ta = $("#ask");
    const send = () => { const q = (ta.value || "").trim(); if (!q) return; ta.value = ""; ask(curAgent(), q); };
    ta.addEventListener("keydown", (e) => { if (e.key === "Enter" && !e.shiftKey && !e.isComposing) { e.preventDefault(); send(); } });
    $("#btn-ask").addEventListener("click", send);
    $("#chat-clear").addEventListener("click", () => { chats(key, curAgent()).length = 0; save(true); paintChat(); renderRail(); updateNext(5); });
    paintChat();
  }

  // ================================================================== step 6 — evaluate
  function cqsFor(key) {
    const run = evalRun(key), r = recipe();
    if (run && run.order && run.order.length) return run.order.map((id) => run.rows[id]).filter(Boolean);
    return (cat().data.cqs || []).filter((c) => (c.recipes || []).indexOf(r.key) >= 0);
  }
  function step6() {
    const r = recipe(), key = rk();
    return head(6, loadedOk(key) ? "" : `<div class="note warn">${esc(t("s6_not_loaded"))} <a href="#step-4">${esc(t("step4_t"))} →</a></div>`)
      + `<section class="card"><div class="card-head"><h2>${esc(t("s6_card", { n: r.cq_count }))}</h2><span class="sub">${esc(r.t)}</span><span class="right"><button type="button" class="btn primary" id="btn-eval"></button></span></div><div id="eval-metrics"></div></section>`
      + `<section class="card"><div class="tbl-wrap"><table class="tbl eval"><thead><tr><th>${esc(t("col_id"))}</th><th>${esc(t("col_agent"))}</th><th>${esc(t("col_question"))}</th><th>${esc(t("col_expected"))}</th><th>${esc(t("col_verdict"))}</th><th class="num">${esc(t("col_ms"))}</th></tr></thead><tbody id="eval-body"></tbody></table></div></section>`
      + nav(6, false);
  }
  function paintEval() {
    if (S.step !== 6 || !$("#eval-body")) return;
    const key = rk(), run = evalRun(key), rows = cqsFor(key), running = !!(run && run.running);
    const done = rows.filter((x) => x.verdict).length;
    const b = $("#btn-eval");
    b.disabled = running;
    b.textContent = running ? t("s6_running", { d: done, n: rows.length }) : run && run.summary ? t("s6_rerun") : t("s6_run");
    const s = run && run.summary;
    const pa = s ? Object.entries(s.per_agent || {}).map(([a, x]) => `<span class="tag"><span class="ld" style="background:var(--c-agent)"></span>${esc(agentName(a))} <b>${esc(x.score)}</b></span>`).join("") : "";
    $("#eval-metrics").innerHTML = `<div class="metrics">${metric(t("s6_score"), s ? esc(s.score) : "—", s ? `${esc(s.total)} CQ · ${esc(fmtMs(s.ms))}` : "")}`
      + metric(t("s6_pass"), s ? esc(s.pass) : "—") + metric(t("s6_partial"), s ? esc(s.partial) : "—") + metric(t("s6_fail"), s ? esc(s.fail) : "—") + `</div>`
      + (pa ? `<div class="row-flex per-agent"><span class="meta">${esc(t("s6_per_agent"))}</span>${pa}<span class="spacer"></span><span class="meta mono">${esc(s.model || "")}</span></div>` : "")
      + (run && run.error ? `<div class="note err">${esc(run.error)}</div>` : "");
    $("#eval-body").innerHTML = rows.map((c) => {
      const v = c.verdict, st = v ? v : c.status === "running" ? "running" : "";
      const found = (c.numbers_found || []).length ? `<div class="meta">${esc(t("s6_found"))}: ${esc(c.numbers_found.join(", "))}</div>` : "";
      return `<tr><td class="mono nowrap">${esc(c.cq_id)}</td><td class="nowrap">${esc(agentName(c.agent))}<div class="meta">${esc(c.category || "")}</div></td>`
        + `<td>${esc(c.query)}${c.answer ? `<details class="ans"><summary>${esc(t("s6_answer"))}${c.answer_status ? ` · <span class="mono">${esc(c.answer_status)}</span>` : ""}</summary><div class="md">${md(c.answer)}</div>${found}</details>` : ""}</td>`
        + `<td>${esc(c.expected)}</td><td class="nowrap">${st ? `<span class="verdict">${dot(st)}${esc(v ? t(`v_${v}`) : t("st_running"))}</span>` : `<span class="faint">—</span>`}</td><td class="tm num">${c.ms != null ? fmtMs(c.ms) : ""}</td></tr>`;
    }).join("");
  }
  async function runEval() {
    const key = rk();
    if (R.runs.evals[key] && R.runs.evals[key].running) return;
    const run = { running: true, rows: {}, order: [], summary: null };
    R.runs.evals[key] = run;
    paintEval();
    try {
      await stream("/api/eval", body(), (ev) => {
        if (ev.type === "plan") {
          run.order = (ev.cqs || []).map((c) => c.cq_id);
          (ev.cqs || []).forEach((c) => { run.rows[c.cq_id] = Object.assign({}, c); });
        } else if (ev.type === "cq") {
          const x = run.rows[ev.cq_id] || (run.rows[ev.cq_id] = { cq_id: ev.cq_id });
          Object.keys(ev).forEach((k) => { if (k !== "type") x[k] = ev[k]; });
        } else if (ev.type === "summary") run.summary = ev;
        else if (ev.type === "error") run.error = ev.message;
        if (rk() === key) later("eval", paintEval);
      });
    } catch (e) {
      run.error = (e.payload && e.payload.message) || e.message || t("err_network");
    }
    run.running = false;
    if (run.summary) { S.evals[key] = run; delete R.runs.evals[key]; }
    save(true);
    if (rk() === key) paintEval();
    renderRail();
  }
  function bind6() {
    $("#btn-eval").addEventListener("click", runEval);
    paintEval();
  }

  // ------------------------------------------------------------------ boot
  async function setLang(lang) {
    if (lang === S.lang || !R.i18n[lang]) return;
    try { await ensureCat(lang); } catch (e) { toast(`${t("err_prefix")} · ${e.message}`); return; }
    S.lang = lang; save(); render();
  }
  async function checkMcp() {
    try {
      const j = await getJSON("/api/core-mcp/tools");
      R.mcp = { ok: (j.tool_count || 0) > 0, count: j.tool_count || 0 };
    } catch (e) {
      console.warn("[starter] Core MCP tools/list failed:", e);
      R.mcp = { ok: false, count: 0 };
    }
    renderTop();
  }
  async function boot() {
    const q = new URLSearchParams(location.search);
    if (q.get("reset") === "1") S = blank();
    if (q.get("lang") === "en" || q.get("lang") === "ko") S.lang = q.get("lang");
    try {
      const got = await Promise.all([getJSON("/static/i18n.json"), getJSON("/api/settings")]);
      R.i18n = got[0]; R.settings = got[1];
      if (!R.i18n[S.lang]) S.lang = "en";
      await ensureCat(S.lang);
      const rq = (q.get("recipe") || "").toUpperCase();
      if (CANON[rq]) { S.type = CANON[rq][0]; S.purpose = CANON[rq][1]; }
      ensureConfig(false);
      const m = /^#step-([1-6])$/.exec(location.hash);
      if (m) S.step = Number(m[1]);
      if (S.step > 1 && !recipeKey()) S.step = 1;
      if (location.hash !== `#step-${S.step}`) history.replaceState(null, "", `${location.pathname}${location.search}#step-${S.step}`);
      save();
      render();
      window.addEventListener("hashchange", onHash);
      $$("#lang-toggle button").forEach((b) => b.addEventListener("click", () => setLang(b.getAttribute("data-lang"))));
      checkMcp();
      ensureCat(S.lang === "ko" ? "en" : "ko").catch((e) => console.warn("[starter] catalog prefetch failed:", e));
    } catch (e) {
      console.error("[starter] boot failed:", e);
      $("#page").innerHTML = `<section class="card"><div class="note err"><b>${esc(R.i18n ? t("err_boot") : "Error")}</b> · ${esc(e.message)}</div></section>`;
    }
  }
  window.AOLStarter = { state: () => S, go, setLang, md, delatex };  // QA hooks (gbrowser E2E)
  boot();
})();
