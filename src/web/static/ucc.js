/* UCC shared-doc viewer (GOAL-230 · GOAL-231).
 * - Loads /api/ucc/doc?id=brd|sdd&lang=ko|en (server-split sections), renders each section with marked + DOMPurify,
 *   mermaid for ```mermaid. KO/EN toggle (top bar, same pattern as the starter wizard) with ?lang= deep link + localStorage.
 * - Every section gets a margin comment button (Google-Docs style). Comments POST to /api/ucc/comments (stored in GCS,
 *   relayed to the author's Jetski Google Chat). Section ids are identical across languages, so comments show on both.
 * - Delete: the comment author (delete_token kept in localStorage) or the owner (admin key, 🔑 in the panel header).
 * - BRD ⇄ SDD switch via tabs; Demo is a one-way link (the demo app has no return control).
 * QA hook: window.UCCViewer = { doc(), comments(), open(sectionId), switchDoc(id), setLang(l) }.
 */
(function () {
  "use strict";
  const $ = (s, r) => (r || document).querySelector(s);
  const el = (tag, cls, text) => { const n = document.createElement(tag); if (cls) n.className = cls; if (text != null) n.textContent = text; return n; };
  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  const I18N = {
    ko: {
      title: (d, v) => `UCC · ${d} ${v}`, docHead: (t) => `UCC 2027 · Enterprise Agentic Ontology — ${t}`, ver: (v) => `판 ${v}`,
      loading: "불러오는 중…", loadFail: "문서를 불러오지 못했습니다: ", listFail: "문서 목록을 불러오지 못했습니다: ", cFail: "코멘트를 불러오지 못했습니다: ",
      cOffline: "코멘트 목록을 잠시 불러올 수 없습니다. 자동으로 다시 시도합니다.",
      toc: "목차", overview: "개요", comment: "코멘트", commentBtnTitle: "이 섹션에 코멘트", panelTitle: "코멘트",
      empty: "아직 코멘트가 없습니다. 섹션 옆 💬 버튼으로 첫 의견을 남겨 주세요.", count: (n, d) => `${n}건 · ${d}`,
      relayed: "✓ Jetski Chat 전달됨", pending: "· Jetski Chat 전달 대기 (1분 이내)", anon: "익명",
      foot: "섹션 오른쪽의 💬 코멘트 버튼으로 의견을 남기면 작성자(Sean)의 Jetski Chat으로 바로 전달됩니다. 이름은 선택이며, 내용은 이 페이지의 코멘트 패널에 남습니다. 내 코멘트는 같은 브라우저에서 삭제할 수 있습니다.",
      namePh: "이름 (선택)", textPh: "이 섹션에 대한 의견을 적어 주세요", hint: "Ctrl/⌘ + Enter 로 보내기", cancel: "취소", send: "코멘트", sending: "보내는 중…",
      needText: "내용을 입력해 주세요.", sent: "코멘트를 남겼습니다. 작성자의 Jetski Chat으로 전달됩니다.", sendFail: "전송 실패: ",
      del: "삭제", delConfirm: "이 코멘트를 삭제할까요?", deleted: "코멘트를 삭제했습니다.", delFail: "삭제 실패: ",
      adminTitle: "관리자 키 (모든 코멘트 삭제)", adminPrompt: "관리자 키를 입력하세요 (비우면 해제)", adminOn: "관리자 모드 켜짐", adminOff: "관리자 모드 해제",
      refresh: "새로고침", panelToggle: "코멘트 패널 열기/닫기", demoSub: "Agentic Ontology Studio · LG U+", notebookSub: "실습 랩", brdSub: "Discovery Doc", sddSub: "Solution Design",
      docLabel: { brd: "BRD · Discovery Doc", sdd: "SDD · Solution Design" }, langOf: (l) => (l === "en" ? "EN" : "KO"),
    },
    en: {
      title: (d, v) => `UCC · ${d} ${v}`, docHead: (t) => `UCC 2027 · Enterprise Agentic Ontology — ${t}`, ver: (v) => `Version ${v}`,
      loading: "Loading…", loadFail: "Failed to load the document: ", listFail: "Failed to load the document list: ", cFail: "Failed to load comments: ",
      cOffline: "Comments are temporarily unavailable. Retrying automatically.",
      toc: "Contents", overview: "Overview", comment: "Comment", commentBtnTitle: "Comment on this section", panelTitle: "Comments",
      empty: "No comments yet. Use the 💬 button next to a section to leave the first one.", count: (n, d) => `${n} · ${d}`,
      relayed: "✓ Delivered to Jetski Chat", pending: "· Delivery to Jetski Chat pending (within 1 min)", anon: "Anonymous",
      foot: "Use the 💬 Comment button on the right of each section — your feedback is delivered straight to the author's (Sean) Jetski Chat. Name is optional; comments stay visible in the panel on this page. You can delete your own comments from the same browser.",
      namePh: "Name (optional)", textPh: "Write your feedback on this section", hint: "Ctrl/⌘ + Enter to send", cancel: "Cancel", send: "Comment", sending: "Sending…",
      needText: "Please enter a comment.", sent: "Comment posted. It will be delivered to the author's Jetski Chat.", sendFail: "Failed to send: ",
      del: "Delete", delConfirm: "Delete this comment?", deleted: "Comment deleted.", delFail: "Delete failed: ",
      adminTitle: "Admin key (delete any comment)", adminPrompt: "Enter the admin key (leave empty to turn off)", adminOn: "Admin mode on", adminOff: "Admin mode off",
      refresh: "Refresh", panelToggle: "Toggle comments panel", demoSub: "Agentic Ontology Studio · LG U+", notebookSub: "Hands-on Lab", brdSub: "Discovery Doc", sddSub: "Solution Design",
      docLabel: { brd: "BRD · Business Requirements", sdd: "SDD · Solution Design" }, langOf: (l) => (l === "en" ? "EN" : "KO"),
    },
  };

  const state = { docId: null, lang: "ko", doc: null, meta: null, comments: [], demoUrl: "", composerFor: null, panelOpen: window.innerWidth > 1100 };
  const T = () => I18N[state.lang] || I18N.ko;
  const tokens = () => { try { return JSON.parse(localStorage.getItem("ucc.tokens") || "{}"); } catch (_) { return {}; } };
  const saveToken = (id, tok) => { const t = tokens(); t[id] = tok; localStorage.setItem("ucc.tokens", JSON.stringify(t)); };
  const adminKey = () => localStorage.getItem("ucc.adminKey") || "";

  function docFromPath() { const m = location.pathname.match(/\/ucc\/(brd|sdd)\b/); return m ? m[1] : (new URLSearchParams(location.search).get("doc") || "brd"); }
  function langFromUrl() {
    const q = new URLSearchParams(location.search).get("lang");
    if (q === "en" || q === "ko") return q;
    const saved = localStorage.getItem("ucc.lang");
    return saved === "en" ? "en" : "ko";
  }
  function urlFor(doc, lang, hash) { return `/ucc/${doc}${lang === "en" ? "?lang=en" : ""}${hash || ""}`; }

  function toast(msg, err) {
    const t = $("#ucc-toast"); t.textContent = msg; t.classList.toggle("err", !!err); t.classList.add("show");
    clearTimeout(toast._t); toast._t = setTimeout(() => t.classList.remove("show"), 3200);
  }
  async function getJSON(url, opts) {
    const r = await fetch(url, Object.assign({ headers: { "Content-Type": "application/json" } }, opts || {}));
    let body = null; try { body = await r.json(); } catch (_) { body = null; }
    if (!r.ok) throw new Error((body && (body.message || body.error)) || ("HTTP " + r.status));
    return body;
  }

  // ------------------------------------------------------------------ static UI strings
  function applyStrings() {
    const t = T();
    document.documentElement.lang = state.lang;
    $("#ucc-toc-title") && ($("#ucc-toc-title").textContent = t.toc);
    $("#ucc-panel-title").textContent = t.panelTitle;
    $("#ucc-foot").textContent = t.foot;
    $("#ucc-author").placeholder = t.namePh; $("#ucc-text").placeholder = t.textPh;
    $("#ucc-composer-hint").textContent = t.hint; $("#ucc-cancel").textContent = t.cancel; $("#ucc-send").textContent = t.send;
    $("#ucc-refresh").title = t.refresh; $("#ucc-toggle-panel").title = t.panelToggle; $("#ucc-admin").title = t.adminTitle;
    $("#ucc-admin").classList.toggle("on", !!adminKey());
    document.querySelectorAll(".ucc-tab[data-doc]").forEach((a) => {
      const d = a.dataset.doc; const meta = state.meta && state.meta.docs && state.meta.docs[d]; const m = meta && (meta[state.lang] || meta.ko);
      a.querySelector("small").textContent = (d === "brd" ? t.brdSub : t.sddSub) + (m && m.version ? ` · ${m.version}` : "");
      a.href = urlFor(d, state.lang);
    });
    $("#ucc-demo small").textContent = t.demoSub;
    $("#ucc-notebook") && ($("#ucc-notebook small").textContent = t.notebookSub);
    document.querySelectorAll("#lang-toggle button").forEach((b) => b.classList.toggle("active", b.dataset.lang === state.lang));
  }

  // ------------------------------------------------------------------ rendering
  marked.setOptions({ gfm: true, breaks: false, headerIds: false, mangle: false });
  function renderMarkdown(md) {
    const diagrams = [];
    md = md.replace(/```mermaid\s*\n([\s\S]*?)```/g, (_, src) => { diagrams.push(src); return `<div class="mermaid" data-idx="${diagrams.length - 1}"></div>`; });
    return { html: DOMPurify.sanitize(marked.parse(md), { ADD_ATTR: ["target", "rel"] }), diagrams };
  }
  async function drawMermaid(container, diagrams) {
    if (!diagrams.length) return;
    const run = async () => {
      const m = window.__mermaid;
      for (const node of container.querySelectorAll(".mermaid[data-idx]")) {
        const src = diagrams[Number(node.dataset.idx)];
        try { const { svg } = await m.render("mm-" + Math.random().toString(36).slice(2, 9), src); node.innerHTML = svg; }
        catch (e) { node.innerHTML = `<pre>${esc(src)}</pre>`; }
      }
    };
    if (window.__mermaid) return run();
    window.addEventListener("mermaid-ready", run, { once: true });
  }

  function renderDoc() {
    const doc = state.doc, t = T();
    document.title = t.title(t.docLabel[doc.id] || doc.id.toUpperCase(), doc.version || "");
    $("#ucc-doc-title").textContent = t.docHead(doc.title);
    $("#ucc-doc-sub").textContent = [doc.version && t.ver(doc.version), doc.date, doc.sha256_12 && `#${doc.sha256_12}`].filter(Boolean).join(" · ");
    $("#ucc-meta").textContent = `${doc.id.toUpperCase()} ${doc.version || ""} · ${t.langOf(doc.lang)} · ${doc.date || ""}`;
    document.querySelectorAll(".ucc-tab[data-doc]").forEach((a) => a.classList.toggle("active", a.dataset.doc === doc.id));

    const art = $("#ucc-doc"); art.innerHTML = "";
    const toc = $("#ucc-toc"); toc.innerHTML = "";
    const tocTitle = el("div", "ucc-dim", t.toc); tocTitle.id = "ucc-toc-title"; tocTitle.style.padding = "0 8px 6px"; toc.appendChild(tocTitle);

    doc.sections.forEach((s) => {
      const sec = el("section", "ucc-sec"); sec.id = s.id; sec.dataset.title = s.title;
      const { html, diagrams } = renderMarkdown(s.markdown);
      const body = el("div", "ucc-sec-body"); body.innerHTML = html; sec.appendChild(body);
      body.querySelectorAll("a[href^='http']").forEach((a) => { a.target = "_blank"; a.rel = "noopener"; });
      const btn = el("button", "ucc-cbtn"); btn.type = "button"; btn.title = t.commentBtnTitle;
      btn.innerHTML = `💬 <span>${esc(t.comment)}</span><span class="n"></span>`;
      btn.addEventListener("click", (ev) => { ev.stopPropagation(); openComposer(s.id, btn); });
      sec.appendChild(btn);
      art.appendChild(sec);
      drawMermaid(body, diagrams);
      const a = el("a", "l" + (s.level || 1), s.title || t.overview); a.href = "#" + s.id; a.dataset.sec = s.id;
      a.appendChild(el("span", "badge")); toc.appendChild(a);
    });
    applyCommentMarks(); observeSections();
    if (location.hash) { const target = $(location.hash); if (target) setTimeout(() => target.scrollIntoView({ block: "start" }), 50); }
  }

  function observeSections() {
    if (!("IntersectionObserver" in window)) return;
    if (observeSections._io) observeSections._io.disconnect();
    const io = new IntersectionObserver((entries) => {
      entries.forEach((e) => { if (e.isIntersecting) document.querySelectorAll("#ucc-toc a").forEach((a) => a.classList.toggle("active", a.dataset.sec === e.target.id)); });
    }, { rootMargin: "-60px 0px -70% 0px", threshold: 0 });
    document.querySelectorAll(".ucc-sec").forEach((s) => io.observe(s));
    observeSections._io = io;
  }

  // ------------------------------------------------------------------ comments
  function countsBySection() { const c = {}; state.comments.forEach((x) => { c[x.section_id] = (c[x.section_id] || 0) + 1; }); return c; }
  function applyCommentMarks() {
    const counts = countsBySection();
    document.querySelectorAll(".ucc-sec").forEach((sec) => {
      const n = counts[sec.id] || 0; sec.classList.toggle("has-comments", n > 0);
      const nEl = sec.querySelector(".ucc-cbtn .n"); if (nEl) nEl.textContent = n ? String(n) : "";
    });
    document.querySelectorAll("#ucc-toc a").forEach((a) => { const b = a.querySelector(".badge"); if (b) b.textContent = counts[a.dataset.sec] ? String(counts[a.dataset.sec]) : ""; });
    $("#ucc-count").textContent = String(state.comments.length);
    renderPanel();
  }
  function fmtWhen(iso) {
    try { return new Date(iso).toLocaleString(state.lang === "en" ? "en-US" : "ko-KR", { month: "numeric", day: "numeric", hour: "2-digit", minute: "2-digit" }); } catch (_) { return iso || ""; }
  }
  function renderPanel() {
    const t = T(), list = $("#ucc-panel-list"); list.innerHTML = "";
    $("#ucc-panel-sub").textContent = state.comments.length ? t.count(state.comments.length, t.docLabel[state.docId] || "") : (t.docLabel[state.docId] || "");
    if (state.cOffline) list.appendChild(el("div", "ucc-dim ucc-offline", t.cOffline));
    if (!state.comments.length) { if (!state.cOffline) list.appendChild(el("div", "ucc-empty", t.empty)); return; }
    const titles = {}; (state.doc.sections || []).forEach((s) => { titles[s.id] = s.title; });
    const mine = tokens(), admin = adminKey();
    [...state.comments].reverse().forEach((c) => {
      const card = el("div", "ucc-c"); card.dataset.sec = c.section_id;
      const who = el("div", "who");
      who.appendChild(el("span", "av", (c.author || "?").trim().charAt(0).toUpperCase() || "?"));
      who.appendChild(el("b", null, c.author || t.anon));
      if (c.lang) who.appendChild(el("span", "lang", c.lang.toUpperCase()));
      who.appendChild(el("span", "when", fmtWhen(c.created_at)));
      card.appendChild(who);
      card.appendChild(el("div", "sec", `§ ${titles[c.section_id] || c.section_title || c.section_id}`));
      if (c.quote) card.appendChild(el("div", "q", c.quote));
      card.appendChild(el("div", "txt", c.text));
      const foot = el("div", "cfoot");
      foot.appendChild(el("span", "relay", c.relayed ? t.relayed : t.pending));
      if (mine[c.id] || admin) {
        const del = el("button", "ucc-del", t.del); del.type = "button";
        del.addEventListener("click", (ev) => { ev.stopPropagation(); deleteComment(c); });
        foot.appendChild(del);
      }
      card.appendChild(foot);
      card.addEventListener("click", () => focusSection(c.section_id, card));
      list.appendChild(card);
    });
  }
  function focusSection(id, card) {
    document.querySelectorAll(".ucc-sec.focus, .ucc-c.focus").forEach((n) => n.classList.remove("focus"));
    const sec = document.getElementById(id); if (!sec) return;
    sec.classList.add("focus"); if (card) card.classList.add("focus");
    sec.scrollIntoView({ behavior: "smooth", block: "start" });
    history.replaceState(null, "", urlFor(state.docId, state.lang, "#" + id));
  }
  async function loadComments(force) {
    // GOAL-234: comments are secondary — a list failure must never cover the document with an error toast.
    // Keep the last good list, show a dim note in the panel and retry quietly in the background.
    try {
      const r = await getJSON(`/api/ucc/comments?doc=${state.docId}${force ? "&refresh=1" : ""}`);
      state.comments = (r && r.comments) || []; state.cOffline = false; clearTimeout(loadComments._retry);
    } catch (e) {
      state.comments = state.comments || []; state.cOffline = true;
      if (window.console) console.warn("[ucc] comments unavailable:", e.message);
      clearTimeout(loadComments._retry); loadComments._retry = setTimeout(() => loadComments(false), 15000);
    }
    applyCommentMarks();
  }
  async function deleteComment(c) {
    const t = T();
    if (!confirm(t.delConfirm)) return;
    const body = { doc: state.docId, id: c.id, token: tokens()[c.id] || "", admin_key: adminKey() || "" };
    try {
      await getJSON("/api/ucc/comments/delete", { method: "POST", body: JSON.stringify(body) });
      state.comments = state.comments.filter((x) => x.id !== c.id); applyCommentMarks(); toast(t.deleted);
    } catch (e) { toast(t.delFail + e.message, true); }
  }
  function setAdminKey() {
    const t = T(); const cur = adminKey();
    const v = prompt(t.adminPrompt, cur ? "••••••" : "");
    if (v === null) return;
    if (!v.trim()) { localStorage.removeItem("ucc.adminKey"); toast(t.adminOff); }
    else if (v !== "••••••") { localStorage.setItem("ucc.adminKey", v.trim()); toast(t.adminOn); }
    applyStrings(); renderPanel();
  }

  // ------------------------------------------------------------------ composer
  function selectedQuote(sec) {
    const sel = window.getSelection && window.getSelection();
    if (!sel || sel.isCollapsed || !sel.rangeCount) return "";
    const range = sel.getRangeAt(0); if (!sec.contains(range.commonAncestorContainer)) return "";
    return sel.toString().trim().slice(0, 300);
  }
  function openComposer(sectionId, anchorBtn) {
    const sec = document.getElementById(sectionId); if (!sec) return;
    state.composerFor = sectionId;
    const comp = $("#ucc-composer");
    $("#ucc-composer-sec").textContent = `💬 ${sec.dataset.title || sectionId}`;
    const q = selectedQuote(sec); const qEl = $("#ucc-composer-quote"); qEl.textContent = q; qEl.hidden = !q; comp.dataset.quote = q;
    $("#ucc-author").value = localStorage.getItem("ucc.author") || ""; $("#ucc-text").value = "";
    comp.hidden = false;
    const r = anchorBtn.getBoundingClientRect(), w = 340, h = comp.offsetHeight || 220;
    let left = Math.min(r.right + 12, window.innerWidth - w - 12); if (left < 12) left = 12;
    let top = Math.min(r.top - 8, window.innerHeight - h - 12); if (top < 64) top = 64;
    comp.style.left = left + "px"; comp.style.top = top + "px";
    document.querySelectorAll(".ucc-sec.focus").forEach((n) => n.classList.remove("focus")); sec.classList.add("focus");
    setTimeout(() => $("#ucc-text").focus(), 20);
  }
  function closeComposer() { $("#ucc-composer").hidden = true; state.composerFor = null; }
  async function sendComment() {
    const t = T(), text = $("#ucc-text").value.trim();
    if (!text) { toast(t.needText, true); $("#ucc-text").focus(); return; }
    const author = $("#ucc-author").value.trim(); localStorage.setItem("ucc.author", author);
    const btn = $("#ucc-send"); btn.disabled = true; btn.textContent = t.sending;
    try {
      const r = await getJSON("/api/ucc/comments", { method: "POST", body: JSON.stringify({ doc: state.docId, lang: state.lang, section_id: state.composerFor, author, text, quote: $("#ucc-composer").dataset.quote || "" }) });
      if (r.delete_token) saveToken(r.comment.id, r.delete_token);
      state.comments.push(r.comment); applyCommentMarks();
      closeComposer(); toast(t.sent);
      if (!state.panelOpen) togglePanel(true);
    } catch (e) { toast(t.sendFail + e.message, true); }
    finally { btn.disabled = false; btn.textContent = t.send; }
  }
  function togglePanel(force) { state.panelOpen = typeof force === "boolean" ? force : !state.panelOpen; $("#ucc-panel").classList.toggle("hidden", !state.panelOpen); }

  // ------------------------------------------------------------------ boot
  async function switchDoc(id, push) {
    state.docId = id; closeComposer();
    if (push) history.pushState(null, "", urlFor(id, state.lang));
    applyStrings();
    try { state.doc = await getJSON(`/api/ucc/doc?id=${id}&lang=${state.lang}`); }
    catch (e) { $("#ucc-doc-title").textContent = T().loadFail + e.message; return; }
    if (state.doc.lang !== state.lang) { state.lang = state.doc.lang; applyStrings(); }
    renderDoc();
    loadComments(false);
  }
  function setLang(l, push) {
    l = l === "en" ? "en" : "ko"; if (l === state.lang) return;
    state.lang = l; localStorage.setItem("ucc.lang", l);
    switchDoc(state.docId, push !== false);
  }
  async function boot() {
    state.lang = langFromUrl();
    try {
      state.meta = await getJSON("/api/ucc/docs");
      state.demoUrl = state.meta.demo_url || "";
      $("#ucc-demo").href = state.demoUrl || "#"; // same tab, one-way: the demo app has no "back" control
      if ($("#ucc-notebook")) $("#ucc-notebook").href = state.meta.notebook_url || "#"; // one-way like Demo
      if (!(state.meta.langs || []).includes("en")) $("#lang-toggle").hidden = true;
    } catch (e) { toast(T().listFail + e.message, true); }
    document.querySelectorAll(".ucc-tab[data-doc]").forEach((a) => a.addEventListener("click", (ev) => { ev.preventDefault(); switchDoc(a.dataset.doc, true); }));
    document.querySelectorAll("#lang-toggle button").forEach((b) => b.addEventListener("click", () => setLang(b.dataset.lang, true)));
    window.addEventListener("popstate", () => { state.lang = langFromUrl(); switchDoc(docFromPath(), false); });
    $("#ucc-composer-close").addEventListener("click", closeComposer);
    $("#ucc-cancel").addEventListener("click", closeComposer);
    $("#ucc-send").addEventListener("click", sendComment);
    $("#ucc-text").addEventListener("keydown", (e) => { if ((e.ctrlKey || e.metaKey) && e.key === "Enter") sendComment(); if (e.key === "Escape") closeComposer(); });
    $("#ucc-toggle-panel").addEventListener("click", () => togglePanel());
    $("#ucc-refresh").addEventListener("click", () => loadComments(true));
    $("#ucc-admin").addEventListener("click", setAdminKey);
    togglePanel(state.panelOpen);
    await switchDoc(docFromPath(), false);
    setInterval(() => { if (!document.hidden) loadComments(false); }, 60000);
  }

  window.UCCViewer = { doc: () => state.doc, comments: () => state.comments, lang: () => state.lang, setLang, switchDoc,
    open: (id) => { const b = document.querySelector(`#${id} .ucc-cbtn`); if (b) openComposer(id, b); } };
  document.addEventListener("DOMContentLoaded", boot);
})();
