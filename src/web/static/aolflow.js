/* aolflow.js — Studio v6 flow-diagram renderer shared by the Notebook Lab and the Starter (GOAL-223).
 *
 * Vanilla JS, no dependencies, no build step. KEEP BYTE-IDENTICAL COPIES:
 *   ontology_lab/web/aolflow.js  ⇄  agentic-ontology-starter/src/web/static/aolflow.js   (+ aolflow.css)
 *
 * Visual grammar = agentic-ontology-studio-lguplus `0. Overview` (enablement v6 portal):
 *   layer columns (colour bar + title + sub) × path lanes (grey band + black pill) · white cards with a
 *   layer dot · thin base line + moving dotted flow in the target layer colour · white pill labels ·
 *   orange extraction badges · legend / step chips under the canvas.
 *
 * AOLFlow.render(host, spec, opts) → controller { svg, update(opts), destroy() }
 *   spec = {
 *     w, h,                                   // viewBox size (canvas units ≈ px at 1240 wide)
 *     minWidth,                               // optional: horizontal scroll below this width (default 960)
 *     cols:   [{ x, t, s, layer }],           // column headers (x = centre)
 *     lanes:  [{ y, h, pill, name, desc, x?, w? }],
 *     groups: [{ x, y, w, h, t, s }],         // dashed system bands (system diagrams)
 *     ghosts: [{ x, y, w, h, t, s }],         // dashed placeholder boxes
 *     bounds: [{ x, y1, y2, l, r }],          // vertical dashed boundary with captions left/right
 *     nodes:  [{ id, x, y, w, h=64, layer, t, s:[...], badge, kind:'card'|'hub'|'pill', dashed,
 *                tip:{t,d}, nb, href, meta }],
 *     edges:  [{ id, from, to, layer, kind:'flow'|'gate'|'bridge'|'mcp', route:'auto'|'h'|'v'|'hv'|'vh',
 *                pts:[…] | d:'M…', mx, my, r, label:{ t, s, x, y, kind:'pill'|'plain'|'plain-left'|'gate'|'mcp' },
 *                tip:{t,d} }],
 *     marks:  [{ x, y, t }],                  // free orange badges (W1 …)
 *     notes:  [{ x, y, t, anchor, cls }],     // free captions
 *     legend: [{ kind, t, color }],           // flow | gate | bridge | mcp | badge | done | running | focus | dot
 *     chips:  [{ n, t, nodes:[ids] }]         // step chips: hover = preview, click = opts.onChip
 *   }
 *   Text values may be a string or [ko, en]; opts.lang picks the language.
 *   Point refs in `pts`: [x, y] or "NODE.port" / "NODE.port@f" / "NODE.port+dx,dy"
 *     port = l | r | t | b | c (f = 0..1 along the side, default .5).
 *   opts = { lang, highlight:[ids], highlightEdges:[ids], states:{id:'done'|'running'|'error'|'current'},
 *            animate:'all'|'focus'|'none', onNode(id,node,ev), onEdge(id,edge,ev), onChip(chip,ev),
 *            compact, card:true, legend:true, caption }
 */
(function (root) {
  "use strict";
  const LAYER = {
    source: "#94a3b8", wiki: "#0ea5e9", semantic: "#8b5cf6", workflow: "#f59e0b", mcp: "#10b981",
    agent: "#ef4444", eval: "#f59e0b", system: "#64748b", user: "#1d1d1f", gemini: "#4285f4", kc: "#0ea5e9",
  };
  const HANGUL = /[\u3131-\uD79D]/;
  let UID = 0;
  const T = (v, lang) => (Array.isArray(v) ? (lang === "en" ? (v[1] != null ? v[1] : v[0]) : v[0]) : v == null ? "" : String(v));
  const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const col = (c) => (c && c[0] === "#" ? c : LAYER[c] || LAYER.source);
  const f1 = (n) => (Math.round(n * 10) / 10).toString();

  // ---------------------------------------------------------------- geometry
  function rounded(pts, r) {
    r = r == null ? 10 : r;
    if (!pts || pts.length < 2) return "";
    let d = `M${f1(pts[0][0])},${f1(pts[0][1])}`;
    for (let i = 1; i < pts.length - 1; i++) {
      const [x0, y0] = pts[i - 1], [x1, y1] = pts[i], [x2, y2] = pts[i + 1];
      const l1 = Math.hypot(x1 - x0, y1 - y0), l2 = Math.hypot(x2 - x1, y2 - y1);
      const rr = Math.min(r, l1 / 2, l2 / 2);
      if (!l1 || !l2 || rr < 0.5) { d += ` L${f1(x1)},${f1(y1)}`; continue; }
      const ax = x1 - ((x1 - x0) / l1) * rr, ay = y1 - ((y1 - y0) / l1) * rr;
      const bx = x1 + ((x2 - x1) / l2) * rr, by = y1 + ((y2 - y1) / l2) * rr;
      d += ` L${f1(ax)},${f1(ay)} Q${f1(x1)},${f1(y1)} ${f1(bx)},${f1(by)}`;
    }
    const z = pts[pts.length - 1];
    return `${d} L${f1(z[0])},${f1(z[1])}`;
  }
  function port(n, spec) {
    // "l" | "r" | "t" | "b" | "c", optional @fraction, optional +dx,dy
    const m = /^([lrtbc])(?:@([\d.]+))?(?:\+(-?[\d.]+),(-?[\d.]+))?$/.exec(spec || "c");
    const side = m ? m[1] : "c", f = m && m[2] != null ? parseFloat(m[2]) : 0.5;
    const dx = m && m[3] != null ? parseFloat(m[3]) : 0, dy = m && m[4] != null ? parseFloat(m[4]) : 0;
    const h = n.h || 64;
    let p;
    if (side === "l") p = [n.x, n.y + h * f];
    else if (side === "r") p = [n.x + n.w, n.y + h * f];
    else if (side === "t") p = [n.x + n.w * f, n.y];
    else if (side === "b") p = [n.x + n.w * f, n.y + h];
    else p = [n.x + n.w / 2, n.y + h / 2];
    return [p[0] + dx, p[1] + dy];
  }
  function resolvePt(ref, byId) {
    if (Array.isArray(ref)) return ref;
    const s = String(ref);
    const dot = s.indexOf(".");
    const id = dot < 0 ? s : s.slice(0, dot);
    const n = byId[id];
    if (!n) return [0, 0];
    return port(n, dot < 0 ? "c" : s.slice(dot + 1));
  }
  function edgePoints(e, byId) {
    if (e.pts) return e.pts.map((p) => resolvePt(p, byId));
    const a = byId[e.from], b = byId[e.to];
    if (!a || !b) return [];
    const ah = a.h || 64, bh = b.h || 64;
    const route = e.route || "auto";
    const acx = a.x + a.w / 2, bcx = b.x + b.w / 2, acy = a.y + ah / 2, bcy = b.y + bh / 2;
    const gap = 2; // leave a hair of space before the target card so the arrow tip is visible
    if (route === "v" || (route === "auto" && Math.abs(acx - bcx) < 1)) {
      const down = bcy > acy;
      const x = e.x != null ? e.x : acx;
      return [[x, down ? a.y + ah : a.y], [x, down ? b.y - gap : b.y + bh + gap]];
    }
    if (route === "vh") {
      const down = bcy > acy, right = bcx > acx;
      return [[acx, down ? a.y + ah : a.y], [acx, bcy], [right ? b.x - gap : b.x + b.w + gap, bcy]];
    }
    if (route === "hv") {
      const down = bcy > acy, right = bcx > acx;
      return [[right ? a.x + a.w : a.x, acy], [bcx, acy], [bcx, down ? b.y - gap : b.y + bh + gap]];
    }
    // horizontal (default): straight when aligned, otherwise a rounded step through mx
    const right = bcx >= acx;
    const x1 = right ? a.x + a.w : a.x, x2 = right ? b.x - gap : b.x + b.w + gap;
    const y1 = e.y1 != null ? e.y1 : acy, y2 = e.y2 != null ? e.y2 : bcy;
    if (Math.abs(y1 - y2) < 1) return [[x1, y1], [x2, y2]];
    const mx = e.mx != null ? e.mx : (x1 + x2) / 2;
    return [[x1, y1], [mx, y1], [mx, y2], [x2, y2]];
  }
  function longestSegMid(pts) {
    let best = null;
    for (let i = 1; i < pts.length; i++) {
      const [x0, y0] = pts[i - 1], [x1, y1] = pts[i];
      const len = Math.hypot(x1 - x0, y1 - y0);
      if (!best || len > best.len) best = { len, x: (x0 + x1) / 2, y: (y0 + y1) / 2, horiz: Math.abs(y1 - y0) < 1 };
    }
    return best || { x: 0, y: 0, horiz: true };
  }

  // ---------------------------------------------------------------- svg builder
  function build(spec, o) {
    const lang = o.lang === "en" ? "en" : "ko";
    const uid = `af${++UID}`;
    const W = spec.w || 1240, H = spec.h || 520;
    const byId = {};
    (spec.nodes || []).forEach((n) => { byId[n.id] = n; });
    // explicitly routed edges: infer endpoints from the first / last "NODE.port" refs (used by focus mode)
    const refId = (p) => (typeof p === "string" ? p.split(".")[0] : null);
    (spec.edges || []).forEach((e) => {
      if (!e.pts || !e.pts.length) return;
      if (!e.from) e.from = refId(e.pts[0]);
      if (!e.to) e.to = refId(e.pts[e.pts.length - 1]);
    });
    const hl = new Set(o.highlight || []);
    const hlE = new Set(o.highlightEdges || []);
    const focus = hl.size > 0 || hlE.size > 0;
    const st = o.states || {};
    const anim = o.animate || "all";
    const used = new Set();
    const out = [];
    const edgeOn = (e) => !focus || hlE.has(e.id) || (hl.has(e.from) && hl.has(e.to));

    // edges first (under cards)
    const edgeSvg = [], labelSvg = [];
    (spec.edges || []).forEach((e, i) => {
      const id = e.id || `e${i}`;
      const c = col(e.layer || (byId[e.to] && byId[e.to].layer) || "source");
      used.add(c);
      const pts = e.d ? null : edgePoints(e, byId);
      const d = e.d || rounded(pts, e.r == null ? 12 : e.r);
      if (!d) return;
      const on = edgeOn({ ...e, id });
      const kind = e.kind || "flow";
      const mk = `url(#${uid}-ah-${c.slice(1)})`;
      const tip = e.tip ? ` data-tip-t="${esc(T(e.tip.t, lang))}" data-tip-d="${esc(T(e.tip.d, lang))}"` : "";
      let body;
      if (kind === "gate") body = `<path class="af-eg" d="${d}" stroke="${c}" marker-end="${mk}"/>`;
      else if (kind === "bridge") body = `<path class="af-ebr" d="${d}" stroke="${c}" marker-end="${mk}"/>`;
      else if (kind === "mcp") body = `<path class="af-emcp" d="${d}" stroke="${c}" marker-end="${mk}"/>`;
      else {
        const moving = anim === "all" || (anim === "focus" && focus && on);
        body = `<path class="af-eb" d="${d}" stroke="${c}" marker-end="${mk}"/>${moving ? `<path class="af-ef" d="${d}" stroke="${c}"/>` : ""}`;
      }
      edgeSvg.push(`<g class="af-edge${on && focus ? " on" : ""}${focus && !on ? " off" : ""}" data-edge="${esc(id)}"${tip}><path class="af-ehit" d="${d}"/>${body}</g>`);
      if (e.label) {
        const L = e.label;
        const t = T(L.t, lang);
        const s = L.s ? T(L.s, lang) : "";
        let x = L.x, y = L.y;
        if (x == null || y == null) {
          const m = pts ? longestSegMid(pts) : { x: 0, y: 0, horiz: true };
          x = x == null ? m.x : x;
          y = y == null ? (m.horiz ? m.y - 12 : m.y) : y;
        }
        const lk = L.kind || "pill";
        const cls = `af-elabel af-l-${lk}${on && focus ? " on" : ""}${focus && !on ? " off" : ""}`;
        const ltip = (L.tip || e.tip) ? ` data-tip-t="${esc(T((L.tip || e.tip).t, lang))}" data-tip-d="${esc(T((L.tip || e.tip).d, lang))}"` : "";
        if (lk === "plain" || lk === "plain-left") {
          const anchor = lk === "plain-left" ? "start" : (L.anchor || "middle");
          labelSvg.push(`<g class="${cls}" data-edge="${esc(id)}"${ltip}><text class="af-el-t" x="${x}" y="${y}" style="text-anchor:${anchor}">${esc(t)}</text>${s ? `<text class="af-el-s" x="${x}" y="${y + 14}" style="text-anchor:${anchor}">${esc(s)}</text>` : ""}</g>`);
        } else {
          // pill: rect sized after mount (data-pill); dot for mcp/gate kinds
          const dot = lk === "mcp" ? `<circle class="af-ldot" cx="0" cy="0" r="3.2" fill="${LAYER.mcp}"/>` : "";
          labelSvg.push(`<g class="${cls}" data-edge="${esc(id)}" data-pill="1" data-x="${x}" data-y="${y}"${ltip}><rect x="${x - 40}" y="${y - 10}" width="80" height="20" rx="10"/>${dot}<text x="${x}" y="${y + 4}">${lk === "gate" && L.strong ? `<tspan font-weight="800">${esc(T(L.strong, lang))}</tspan> ` : ""}${esc(t)}</text></g>`);
        }
      }
    });

    // column headers
    (spec.cols || []).forEach((c) => {
      const cc = col(c.layer);
      out.push(`<g class="af-col"><rect x="${c.x - 12}" y="4" width="24" height="4" rx="2" fill="${cc}"/><text class="af-col-t" x="${c.x}" y="25">${esc(T(c.t, lang))}</text>${c.s ? `<text class="af-col-s" x="${c.x}" y="40">${esc(T(c.s, lang))}</text>` : ""}</g>`);
    });
    // lanes
    (spec.lanes || []).forEach((l) => {
      const x = l.x != null ? l.x : 8, w = l.w != null ? l.w : W - 16;
      const pillW = Math.max(30, 10 + String(T(l.pill, lang)).length * 8);
      out.push(`<g class="af-lane-g"><rect class="af-lane${l.tone ? ` af-lane-${l.tone}` : ""}" x="${x}" y="${l.y}" width="${w}" height="${l.h}" rx="16"/>`
        + (l.pill ? `<rect class="af-lane-pill" x="${x + 12}" y="${l.y + 10}" width="${pillW}" height="18" rx="9"/><text class="af-lane-pill-t" x="${x + 12 + pillW / 2}" y="${l.y + 23}">${esc(T(l.pill, lang))}</text>` : "")
        + `<text x="${x + (l.pill ? 20 + pillW : 14)}" y="${l.y + 23}"><tspan class="af-lane-name">${esc(T(l.name, lang))}</tspan>${l.desc ? `<tspan class="af-lane-desc" dx="8">${esc(T(l.desc, lang))}</tspan>` : ""}</text></g>`);
    });
    // system groups (dashed bands)
    (spec.groups || []).forEach((g) => {
      out.push(`<g class="af-group"><rect x="${g.x}" y="${g.y}" width="${g.w}" height="${g.h}" rx="16"/>${g.t ? `<text class="af-group-t" x="${g.x + (g.align === "left" ? 14 : g.w / 2)}" y="${g.y + 18}" text-anchor="${g.align === "left" ? "start" : "middle"}">${esc(T(g.t, lang))}</text>` : ""}${g.s ? `<text class="af-group-s" x="${g.x + (g.align === "left" ? 14 : g.w / 2)}" y="${g.y + 32}" text-anchor="${g.align === "left" ? "start" : "middle"}">${esc(T(g.s, lang))}</text>` : ""}</g>`);
    });
    // boundaries
    (spec.bounds || []).forEach((b) => {
      out.push(`<g class="af-bound"><line x1="${b.x}" y1="${b.y1}" x2="${b.x}" y2="${b.y2}"/>${b.l ? `<text x="${b.x - 6}" y="${b.y2 - 4}" text-anchor="end">${esc(T(b.l, lang))}</text>` : ""}${b.r ? `<text x="${b.x + 6}" y="${b.y2 - 4}">${esc(T(b.r, lang))}</text>` : ""}</g>`);
    });
    // ghosts
    (spec.ghosts || []).forEach((g) => {
      out.push(`<g class="af-ghost"><rect x="${g.x}" y="${g.y}" width="${g.w}" height="${g.h}" rx="12"/><text class="af-ghost-t" x="${g.x + g.w / 2}" y="${g.y + g.h / 2 - (g.s ? 3 : -4)}" data-maxw="${g.w - 16}">${esc(T(g.t, lang))}</text>${g.s ? `<text class="af-ghost-s" x="${g.x + g.w / 2}" y="${g.y + g.h / 2 + 14}" data-maxw="${g.w - 16}">${esc(T(g.s, lang))}</text>` : ""}</g>`);
    });
    out.push(edgeSvg.join(""));

    // nodes
    (spec.nodes || []).forEach((n) => {
      const h = n.h || 64;
      const c = col(n.layer);
      const s = (n.s || []).map((x) => T(x, lang)).filter(Boolean);
      const on = hl.has(n.id);
      const state = st[n.id] || "";
      const cls = ["af-node", n.kind ? `af-k-${n.kind}` : "", on && focus && o.focusStyle !== "dim" ? "on" : "", focus && !on ? "off" : "", n.dashed ? "dashed" : "",
        state ? `st-${state}` : "", n.href || n.nb || o.onNode ? "click" : ""].filter(Boolean).join(" ");
      const tip = n.tip ? ` data-tip-t="${esc(T(n.tip.t || n.t, lang))}" data-tip-d="${esc(T(n.tip.d, lang))}"` : "";
      const title = T(n.t, lang);
      let inner;
      if (n.kind === "hub") {
        // tall centre-aligned hub (e.g. MCP server / Core MCP)
        const cx = n.x + n.w / 2;
        inner = `<rect class="af-cardr" x="${n.x}" y="${n.y}" width="${n.w}" height="${h}" rx="14" filter="url(#${uid}-soft)"/>`
          + `<circle cx="${cx}" cy="${n.y + 22}" r="4.5" fill="${c}"/>`
          + `<text class="af-hub-t" x="${cx}" y="${n.y + 46}" data-maxw="${n.w - 16}">${esc(title)}</text>`
          + s.map((line, i) => `<text class="af-hub-s" x="${cx}" y="${n.y + 64 + i * 16}" data-maxw="${n.w - 16}">${esc(line)}</text>`).join("")
          + (n.big ? `<text class="af-hub-n" x="${cx}" y="${n.y + h - 34}">${esc(T(n.big, lang))}</text>` : "")
          + (n.bigS ? `<text class="af-hub-s" x="${cx}" y="${n.y + h - 16}" data-maxw="${n.w - 16}">${esc(T(n.bigS, lang))}</text>` : "");
      } else if (n.kind === "pill") {
        const small = h <= 30;
        inner = `<rect class="af-cardr" x="${n.x}" y="${n.y}" width="${n.w}" height="${h}" rx="${h / 2}" filter="url(#${uid}-soft)"/>`
          + `<circle cx="${n.x + (small ? 13 : 16)}" cy="${n.y + h / 2}" r="${small ? 3.5 : 4}" fill="${c}"/>`
          + `<text class="${small ? "af-chip-t" : "af-t"}" x="${n.x + (small ? 22 : 28)}" y="${n.y + h / 2 + (small ? 4 : 4.5)}" data-maxw="${n.w - (small ? 30 : 40)}">${esc(title)}</text>`;
      } else {
        const tx = n.badge ? n.x + 24 : n.x + 26;
        const lines = s.slice(0, Math.max(0, Math.floor((h - 34) / 15)));
        const ty = n.y + (lines.length ? 23 : h / 2 + 5);
        inner = `<rect class="af-cardr" x="${n.x}" y="${n.y}" width="${n.w}" height="${h}" rx="12" filter="url(#${uid}-soft)"/>`
          + (n.badge ? `<g class="af-wm"><circle cx="${n.x}" cy="${n.y + h / 2}" r="15"/><text x="${n.x}" y="${n.y + h / 2 + 4}">${esc(T(n.badge, lang))}</text></g>`
            : `<circle cx="${n.x + 14}" cy="${ty - 4}" r="4" fill="${c}"/>`)
          + `<text class="af-t" x="${tx}" y="${ty}" data-maxw="${n.x + n.w - tx - (state ? 22 : 10)}">${esc(title)}</text>`
          + lines.map((line, i) => `<text class="af-s" x="${tx}" y="${ty + 18 + i * 15}" data-maxw="${n.x + n.w - tx - 10}">${esc(line)}</text>`).join("");
      }
      const stMark = state === "done" ? `<g class="af-st"><circle cx="${n.x + n.w - 13}" cy="${n.y + 13}" r="6.5"/><path d="M${n.x + n.w - 16},${n.y + 13} l2.2,2.3 l4,-4.3"/></g>`
        : state === "running" ? `<g class="af-st"><circle class="af-ring" cx="${n.x + n.w - 13}" cy="${n.y + 13}" r="5.5"/></g>`
          : state === "error" ? `<g class="af-st"><circle cx="${n.x + n.w - 13}" cy="${n.y + 13}" r="6.5"/><path d="M${n.x + n.w - 13},${n.y + 9.5} v4 M${n.x + n.w - 13},${n.y + 16} v.6"/></g>` : "";
      out.push(`<g class="${cls}" data-node="${esc(n.id)}"${n.nb ? ` data-nb="${esc(n.nb)}"` : ""} tabindex="0" role="button" aria-label="${esc(title)}"${tip}>${inner}${stMark}</g>`);
    });
    // free badges and notes
    (spec.marks || []).forEach((m) => out.push(`<g class="af-wm"><circle cx="${m.x}" cy="${m.y}" r="${m.r || 13}"/><text x="${m.x}" y="${m.y + 4}">${esc(T(m.t, lang))}</text></g>`));
    (spec.notes || []).forEach((m) => out.push(`<text class="af-note ${m.cls || ""}" x="${m.x}" y="${m.y}" text-anchor="${m.anchor || "start"}">${esc(T(m.t, lang))}</text>`));
    out.push(labelSvg.join(""));

    const markers = Array.from(used).concat([LAYER.mcp, LAYER.workflow]).filter((v, i, a) => a.indexOf(v) === i)
      .map((c) => `<marker id="${uid}-ah-${c.slice(1)}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" markerUnits="userSpaceOnUse" orient="auto"><path d="M1,1.5 L9,5 L1,8.5 z" fill="${c}"/></marker>`).join("");
    const defs = `<defs><filter id="${uid}-soft" x="-10%" y="-20%" width="120%" height="150%"><feDropShadow dx="0" dy="1" stdDeviation="1" flood-color="#000" flood-opacity="0.05"/><feDropShadow dx="0" dy="4" stdDeviation="6" flood-color="#000" flood-opacity="0.05"/></filter>${markers}</defs>`;
    const aria = esc(T(spec.title || ["흐름도", "Flow diagram"], lang));
    return `<svg class="af-svg${focus ? " af-focus" : ""}" viewBox="0 0 ${W} ${H}" role="img" aria-label="${aria}" xmlns="http://www.w3.org/2000/svg">${defs}${out.join("")}</svg>`;
  }

  function legendHtml(spec, o) {
    const lang = o.lang === "en" ? "en" : "ko";
    const items = (spec.legend || []).map((it) => {
      const c = col(it.color || "source");
      let sw;
      if (it.kind === "flow") sw = `<svg width="26" height="8" aria-hidden="true"><line x1="1" y1="4" x2="25" y2="4" stroke="${c}" stroke-width="2.4" stroke-linecap="round" stroke-dasharray=".1 6"/></svg>`;
      else if (it.kind === "gate") sw = `<svg width="26" height="8" aria-hidden="true"><line x1="1" y1="4" x2="25" y2="4" stroke="${col("workflow")}" stroke-width="1.8" stroke-dasharray="6 4"/></svg>`;
      else if (it.kind === "mcp") sw = `<svg width="26" height="8" aria-hidden="true"><line x1="1" y1="4" x2="25" y2="4" stroke="${col("mcp")}" stroke-width="1.6" stroke-dasharray="3 3"/></svg>`;
      else if (it.kind === "bridge") sw = `<svg width="26" height="8" aria-hidden="true"><line x1="1" y1="4" x2="25" y2="4" stroke="${c}" stroke-width="1.4" stroke-dasharray="2 3"/></svg>`;
      else if (it.kind === "badge") sw = `<i class="af-lg-badge">${esc(it.badge || "W")}</i>`;
      else if (it.kind === "done") sw = `<i class="af-lg-done"></i>`;
      else if (it.kind === "running") sw = `<i class="af-lg-run"></i>`;
      else if (it.kind === "focus") sw = `<i class="af-lg-focus"></i>`;
      else sw = `<i class="af-lg-dot" style="background:${c}"></i>`;
      return `<span class="af-lg">${sw}${esc(T(it.t, lang))}</span>`;
    }).join("");
    const chips = (spec.chips || []).map((ch, i) => `<button type="button" class="af-chip" data-chip="${i}"><span class="n">${esc(T(ch.n, lang))}</span>${esc(T(ch.t, lang))}</button>`).join("");
    if (!items && !chips && !o.caption) return "";
    return `<div class="af-bar">${chips ? `<div class="af-chips">${chips}</div>` : ""}<div class="af-legend">${items}${o.caption ? `<span class="af-cap">${esc(T(o.caption, lang))}</span>` : ""}</div></div>`;
  }

  // shrink long texts (EN labels are longer) instead of letting them overflow the card
  function fitTexts(svg) {
    svg.querySelectorAll("text[data-maxw]").forEach((t) => {
      const max = parseFloat(t.getAttribute("data-maxw"));
      if (!(max > 0) || typeof t.getComputedTextLength !== "function") return;
      let len = 0;
      try { len = t.getComputedTextLength(); } catch (e) { return; }
      if (!len || len <= max) return;
      const fs = parseFloat(getComputedStyle(t).fontSize) || 12;
      const scale = Math.max(0.84, max / len);
      t.style.fontSize = `${(fs * scale).toFixed(2)}px`;
      try { len = t.getComputedTextLength(); } catch (e) { return; }
      if (len > max) {
        const full = t.textContent;
        let s = full;
        while (s.length > 2 && t.getComputedTextLength() > max) { s = s.slice(0, -1); t.textContent = `${s.trimEnd()}…`; }
        const ti = document.createElementNS("http://www.w3.org/2000/svg", "title");
        ti.textContent = full;
        t.appendChild(ti);
      }
    });
    svg.querySelectorAll("g[data-pill]").forEach((g) => {
      const t = g.querySelector("text"), r = g.querySelector("rect"), dot = g.querySelector(".af-ldot");
      if (!t || !r) return;
      let w = 60;
      try { w = t.getComputedTextLength(); } catch (e) { /* keep default */ }
      const x = parseFloat(g.getAttribute("data-x")), y = parseFloat(g.getAttribute("data-y"));
      const pad = dot ? 22 : 12;
      const total = w + pad + 12;
      r.setAttribute("x", f1(x - total / 2)); r.setAttribute("width", f1(total));
      r.setAttribute("y", f1(y - 10)); r.setAttribute("height", "20");
      if (dot) { dot.setAttribute("cx", f1(x - total / 2 + 11)); dot.setAttribute("cy", f1(y)); t.setAttribute("x", f1(x + 5)); }
    });
  }

  let TIP = null;
  function tipEl() {
    if (TIP && document.body.contains(TIP)) return TIP;
    TIP = document.createElement("div");
    TIP.className = "af-tip";
    TIP.hidden = true;
    document.body.appendChild(TIP);
    return TIP;
  }

  function render(host, spec, opts) {
    let o = Object.assign({ lang: "ko", animate: "all", card: true, legend: true }, opts || {});
    const wrap = document.createElement("div");
    host.innerHTML = "";
    host.appendChild(wrap);
    const draw = () => {
      wrap.className = `af${o.card ? " af-card" : ""}${o.compact ? " af-compact" : ""}`;
      const minW = spec.minWidth || (o.compact ? 900 : 960);
      wrap.innerHTML = `<div class="af-scroll"><div class="af-stage" style="min-width:${minW}px">${build(spec, o)}</div></div>${o.legend ? legendHtml(spec, o) : ""}`;
      const svg = wrap.querySelector("svg");
      fitTexts(svg);
      bind(svg);
      ctrl.svg = svg;
    };
    const bind = (svg) => {
      const tip = tipEl();
      const show = (el, ev) => {
        const t = el.getAttribute("data-tip-t"), d = el.getAttribute("data-tip-d");
        if (!t && !d) return;
        tip.innerHTML = `${t ? `<b>${esc(t)}</b>` : ""}${d ? esc(d) : ""}`;
        tip.hidden = false;
        const x = Math.min(window.innerWidth - 320, ev.clientX + 14), y = Math.min(window.innerHeight - 90, ev.clientY + 16);
        tip.style.left = `${Math.max(8, x)}px`; tip.style.top = `${Math.max(8, y)}px`;
      };
      svg.addEventListener("mousemove", (ev) => {
        const el = ev.target.closest("[data-tip-t],[data-tip-d]");
        if (el) show(el, ev); else tip.hidden = true;
      });
      svg.addEventListener("mouseleave", () => { tip.hidden = true; });
      svg.addEventListener("click", (ev) => {
        const g = ev.target.closest(".af-node");
        if (g) {
          const n = (spec.nodes || []).find((x) => x.id === g.getAttribute("data-node"));
          if (n && n.href) { location.href = n.href; return; }
          if (o.onNode) o.onNode(g.getAttribute("data-node"), n, ev);
          return;
        }
        const e = ev.target.closest("[data-edge]");
        if (e && o.onEdge) o.onEdge(e.getAttribute("data-edge"), (spec.edges || []).find((x) => x.id === e.getAttribute("data-edge")), ev);
      });
      svg.querySelectorAll(".af-node").forEach((g) => g.addEventListener("keydown", (ev) => {
        if (ev.key !== "Enter" && ev.key !== " ") return;
        ev.preventDefault();
        g.dispatchEvent(new MouseEvent("click", { bubbles: true }));
      }));
      wrap.querySelectorAll(".af-chip").forEach((b) => {
        const ch = (spec.chips || [])[Number(b.getAttribute("data-chip"))];
        if (!ch) return;
        const ids = new Set(ch.nodes || []);
        b.addEventListener("mouseenter", () => {
          svg.classList.add("af-preview");
          svg.querySelectorAll(".af-node").forEach((g) => g.classList.toggle("pv", ids.has(g.getAttribute("data-node"))));
          svg.querySelectorAll(".af-edge,.af-elabel").forEach((g) => {
            const e = (spec.edges || []).find((x) => x.id === g.getAttribute("data-edge"));
            g.classList.toggle("pv", !!e && ids.has(e.from) && ids.has(e.to));
          });
        });
        b.addEventListener("mouseleave", () => svg.classList.remove("af-preview"));
        b.addEventListener("click", (ev) => { if (o.onChip) o.onChip(ch, ev); });
      });
    };
    const ctrl = {
      svg: null,
      update(next) { o = Object.assign(o, next || {}); draw(); return ctrl; },
      destroy() { host.innerHTML = ""; },
    };
    draw();
    return ctrl;
  }

  // EN residue audit: returns visible texts that still contain Hangul (used by tests / QA)
  function hangulResidue(rootEl) {
    const bad = [];
    (rootEl || document).querySelectorAll(".af svg text, .af-bar").forEach((t) => {
      const s = (t.textContent || "").trim();
      if (s && HANGUL.test(s)) bad.push(s.slice(0, 80));
    });
    return bad;
  }

  root.AOLFlow = { render, rounded, LAYER, T, hangulResidue, version: "1.0.0-GOAL-223" };
})(typeof window !== "undefined" ? window : this);
