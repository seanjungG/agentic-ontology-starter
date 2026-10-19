# Copyright (c) 2026 Sean Jung (seanjung@google.com). All Rights Reserved.
# Non-Commercial Use Only: Methodology & Docs under CC BY-NC-ND 4.0; Source Code under PolyForm Noncommercial License 1.0.0.

# -*- coding: utf-8 -*-
"""
UCC sub-pages for the starter (GOAL-230): Markdown viewer for the shared BRD / SDD with per-section comments.

Documents are published into ``<repo>/ucc/`` by ``ucc/scripts/publish_to_starter.py`` (``brd.md`` · ``sdd.md`` ·
``manifest.json``). Comments are stored as one JSON object each in GCS under ``ucc/comments/<doc>/`` through the
Platform Core MCP data-plane tools (runtime SA token), and a Cloudtop relay forwards new objects to the Jetski Google
Chat space. This module is HTTP-framework agnostic: ``studio_server.py`` calls the ``handle_*`` helpers.

  GET  /ucc · /ucc/brd · /ucc/sdd        ucc.html (static shell, document picked from the path)
  GET  /api/ucc/docs                     manifest (titles · versions per lang · demo url)
  GET  /api/ucc/doc?id=brd|sdd&lang=ko|en  {id, lang, title, version, date, sections:[{id, title, level, markdown}]}
  GET  /api/ucc/comments?doc=brd|sdd     {comments:[...]} newest last (both languages; section ids are shared)
  POST /api/ucc/comments                 {doc, section_id, lang?, author, text, quote?} → {status, comment, delete_token}
  POST /api/ucc/comments/delete          {doc, id, token?, admin_key?} → soft delete (author token or UCC_ADMIN_KEY)
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
import secrets
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
UCC_DIR = os.environ.get("UCC_DOCS_DIR") or os.path.join(BASE_DIR, "ucc")
DOC_IDS = ("brd", "sdd")
LANGS = ("ko", "en")
ADMIN_KEY = os.environ.get("UCC_ADMIN_KEY", "").strip()
COMMENTS_PREFIX = os.environ.get("UCC_COMMENTS_PREFIX", "ucc/comments/").strip("/") + "/"
DEMO_URL_DEFAULT = "https://agentic-ontology-studio-lguplus-924723860007.asia-northeast3.run.app/"
KST = dt.timezone(dt.timedelta(hours=9))

MAX_TEXT = 2000
MAX_AUTHOR = 80
MAX_QUOTE = 300
RATE_LIMIT_PER_MIN = 10          # per client key
CACHE_TTL_S = 20                 # comments list cache (GCS listing + downloads are remote calls)

_SECTION_ID = re.compile(r"^s\d{2}$")
_FENCE = re.compile(r"^(```|~~~)")
_HEADING = re.compile(r"^(#{1,3})\s+(.*?)\s*#*\s*$")


# ----------------------------------------------------------------------------------------------------- documents
def manifest() -> Dict[str, Any]:
    path = os.path.join(UCC_DIR, "manifest.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        data = {"docs": {}}
    data.setdefault("demo_url", DEMO_URL_DEFAULT)
    data["demo_url"] = os.environ.get("UCC_DEMO_URL") or data["demo_url"]
    data.setdefault("docs", {})
    return data


def split_sections(markdown: str) -> List[Dict[str, Any]]:
    """Splits a document at ``#``/``##`` headings (outside code fences). Section 0 holds the H1 + preamble.

    Each section: {id: 's00', level, title, markdown}. ``###`` headings stay inside their parent section so a comment
    anchors to a reviewable "part" of the document rather than a sub-bullet.
    """
    lines = markdown.splitlines()
    sections: List[Dict[str, Any]] = []
    cur: Dict[str, Any] = {"level": 0, "title": "개요", "lines": []}
    in_fence = False
    for ln in lines:
        if _FENCE.match(ln.strip()):
            in_fence = not in_fence
        m = None if in_fence else _HEADING.match(ln)
        if m and len(m.group(1)) <= 2:
            if cur["lines"] or sections:
                sections.append(cur)
            cur = {"level": len(m.group(1)), "title": _plain(m.group(2)), "lines": [ln]}
            continue
        cur["lines"].append(ln)
    sections.append(cur)
    # drop an empty leading preamble (document starting directly with a heading)
    if sections and sections[0]["level"] == 0 and not "".join(sections[0]["lines"]).strip():
        sections.pop(0)
    out: List[Dict[str, Any]] = []
    for i, s in enumerate(sections):
        out.append({"id": f"s{i:02d}", "level": s["level"], "title": s["title"], "markdown": "\n".join(s["lines"]).strip("\n")})
    return out


def _plain(title: str) -> str:
    title = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", title)
    title = re.sub(r"[*_`]", "", title)
    return title.strip()[:160]


def norm_lang(lang: Any) -> str:
    return "en" if str(lang or "").lower() == "en" else "ko"


def _doc_meta(doc_id: str, lang: str) -> Dict[str, Any]:
    """manifest.docs[kind] is either {lang: meta} (new) or a flat meta (legacy, KO only)."""
    entry = manifest()["docs"].get(doc_id) or {}
    if any(k in entry for k in LANGS):
        return entry.get(lang) or {}
    return entry if lang == "ko" else {}


def load_doc(doc_id: str, lang: str = "ko") -> Optional[Dict[str, Any]]:
    if doc_id not in DOC_IDS:
        return None
    lang = norm_lang(lang)
    path = os.path.join(UCC_DIR, f"{doc_id}.md" if lang == "ko" else f"{doc_id}_{lang}.md")
    try:
        with open(path, "r", encoding="utf-8") as f:
            md = f.read()
    except OSError:
        return None
    meta = _doc_meta(doc_id, lang)
    sections = split_sections(md)
    return {"id": doc_id, "lang": lang, "title": meta.get("title") or doc_id.upper(), "version": meta.get("version", ""),
            "date": meta.get("date", ""), "sha256_12": meta.get("sha256_12", ""), "sections": sections,
            "section_count": len(sections), "langs": available_langs(doc_id)}


def available_langs(doc_id: str) -> List[str]:
    out = []
    for lang in LANGS:
        name = f"{doc_id}.md" if lang == "ko" else f"{doc_id}_{lang}.md"
        if os.path.isfile(os.path.join(UCC_DIR, name)):
            out.append(lang)
    return out


def docs_payload() -> Dict[str, Any]:
    m = manifest()
    docs: Dict[str, Any] = {}
    for k in DOC_IDS:
        if k not in m["docs"]:
            continue
        docs[k] = {}
        for lang in LANGS:
            meta = _doc_meta(k, lang)
            if meta:
                docs[k][lang] = {kk: vv for kk, vv in meta.items() if kk != "source"}
    return {"docs": docs, "demo_url": m["demo_url"], "published_at": m.get("published_at", ""),
            "langs": [l for l in LANGS if any(l in v for v in docs.values())], "admin_enabled": bool(ADMIN_KEY)}


# ----------------------------------------------------------------------------------------------------- comments
PRIVATE_FIELDS = ("client", "user_agent", "delete_token")
_cache: Dict[str, Tuple[float, List[Dict[str, Any]]]] = {}
_cache_lock = threading.Lock()
_rate: Dict[str, List[float]] = {}
_rate_lock = threading.Lock()


def _bucket() -> str:
    from src.gcp_client import runtime_settings  # lazy: keeps this module importable in unit tests without env
    return os.environ.get("UCC_COMMENTS_BUCKET") or runtime_settings()["gcs_bucket"]


def _client_key(remote: str) -> str:
    return hashlib.sha256((remote or "?").encode("utf-8")).hexdigest()[:10]


def _rate_ok(key: str) -> bool:
    now = time.time()
    with _rate_lock:
        hits = [t for t in _rate.get(key, []) if now - t < 60]
        if len(hits) >= RATE_LIMIT_PER_MIN:
            _rate[key] = hits
            return False
        hits.append(now)
        _rate[key] = hits
        return True


def validate_comment(data: Dict[str, Any], doc: Optional[Dict[str, Any]]) -> Tuple[Optional[str], Dict[str, Any]]:
    """Returns (error_message | None, normalized fields)."""
    doc_id = str(data.get("doc") or "").strip().lower()
    if doc_id not in DOC_IDS:
        return "doc must be 'brd' or 'sdd'", {}
    if doc is None:
        return f"document '{doc_id}' is not published", {}
    section_id = str(data.get("section_id") or "").strip()
    ids = {s["id"]: s for s in doc["sections"]}
    if not _SECTION_ID.match(section_id) or section_id not in ids:
        return "unknown section_id", {}
    text = str(data.get("text") or "").strip()
    if not text:
        return "text is empty", {}
    if len(text) > MAX_TEXT:
        return f"text longer than {MAX_TEXT} chars", {}
    lang = norm_lang(data.get("lang") or doc.get("lang"))
    author = re.sub(r"\s+", " ", str(data.get("author") or "").strip())[:MAX_AUTHOR] or ("Anonymous" if lang == "en" else "익명")
    quote = str(data.get("quote") or "").strip()[:MAX_QUOTE]
    return None, {"doc": doc_id, "doc_version": doc.get("version", ""), "lang": lang, "section_id": section_id,
                  "section_title": ids[section_id]["title"], "author": author, "text": text, "quote": quote}


def create_comment(data: Dict[str, Any], remote: str = "", user_agent: str = "") -> Tuple[int, Dict[str, Any]]:
    from src.gcp_client import error_message, gcs_upload
    doc_id = str(data.get("doc") or "").strip().lower()
    lang = norm_lang(data.get("lang"))
    doc = load_doc(doc_id, lang) if doc_id in DOC_IDS else None
    if doc is None and doc_id in DOC_IDS and lang != "ko":  # section ids are shared across languages
        doc = load_doc(doc_id, "ko")
    err, fields = validate_comment(data, doc)
    if err:
        return 400, {"status": "BAD_REQUEST", "message": err}
    key = _client_key(remote)
    if not _rate_ok(key):
        return 429, {"status": "RATE_LIMITED", "message": f"too many comments; try again in a minute ({RATE_LIMIT_PER_MIN}/min)"}
    now = dt.datetime.now(KST)
    cid = f"{now.strftime('%Y%m%dT%H%M%S')}_{secrets.token_hex(3)}"
    delete_token = secrets.token_urlsafe(18)
    record = {**fields, "id": cid, "created_at": now.isoformat(timespec="seconds"), "client": key,
              "user_agent": (user_agent or "")[:160], "delete_token": delete_token,
              "page_url": f"/ucc/{fields['doc']}{'?lang=en' if fields['lang'] == 'en' else ''}#{fields['section_id']}",
              "relayed": False, "deleted": False}
    name = f"{COMMENTS_PREFIX}{fields['doc']}/{cid}.json"
    code, payload = gcs_upload(name, json.dumps(record, ensure_ascii=False, indent=2).encode("utf-8"), _bucket(),
                               content_type="application/json; charset=utf-8")
    if code != 200:
        return 502, {"status": "ERROR", "message": f"comment not saved (GCS {code}): {error_message(payload)}"}
    with _cache_lock:
        _cache.pop(fields["doc"], None)
    public = {k: v for k, v in record.items() if k not in PRIVATE_FIELDS}
    return 200, {"status": "SUCCESS", "comment": public, "object": name, "delete_token": delete_token}


def list_comments(doc_id: str, force: bool = False) -> Tuple[int, Dict[str, Any]]:
    from src.gcp_client import error_message, gcs_download_text, gcs_list
    if doc_id not in DOC_IDS:
        return 400, {"status": "BAD_REQUEST", "message": "doc must be 'brd' or 'sdd'"}
    now = time.time()
    with _cache_lock:
        hit = _cache.get(doc_id)
    if hit and not force and now - hit[0] < CACHE_TTL_S:
        return 200, {"status": "SUCCESS", "doc": doc_id, "comments": hit[1], "cached": True}
    bucket = _bucket()
    code, payload = gcs_list(f"{COMMENTS_PREFIX}{doc_id}/", bucket)
    if code != 200:
        return 502, {"status": "ERROR", "message": f"list failed (GCS {code}): {error_message(payload)}", "comments": []}
    items = payload.get("items") or []
    names = sorted(str(it.get("name") or it) for it in items if str(it.get("name") or it).endswith(".json"))
    comments: List[Dict[str, Any]] = []
    for name in names[-300:]:
        c, txt = gcs_download_text(name, bucket)
        if c != 200:
            continue
        try:
            rec = json.loads(txt)
        except json.JSONDecodeError:
            continue
        if rec.get("deleted"):
            continue
        comments.append({k: v for k, v in rec.items() if k not in PRIVATE_FIELDS})
    comments.sort(key=lambda r: r.get("created_at", ""))
    with _cache_lock:
        _cache[doc_id] = (now, comments)
    return 200, {"status": "SUCCESS", "doc": doc_id, "comments": comments, "cached": False}


_COMMENT_ID = re.compile(r"^\d{8}T\d{6}_[0-9a-f]{6}$")


def delete_comment(data: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
    """Soft-deletes a comment: the author (delete_token issued at creation) or the owner (UCC_ADMIN_KEY) may delete.
    The GCS object is overwritten with deleted=true (audit trail kept); listings and the page hide it."""
    from src.gcp_client import error_message, gcs_download_text, gcs_upload
    doc_id = str(data.get("doc") or "").strip().lower()
    cid = str(data.get("id") or "").strip()
    token = str(data.get("token") or "").strip()
    admin = str(data.get("admin_key") or "").strip()
    if doc_id not in DOC_IDS or not _COMMENT_ID.match(cid):
        return 400, {"status": "BAD_REQUEST", "message": "doc/id invalid"}
    if not token and not admin:
        return 401, {"status": "UNAUTHORIZED", "message": "token or admin_key required"}
    name = f"{COMMENTS_PREFIX}{doc_id}/{cid}.json"
    bucket = _bucket()
    code, txt = gcs_download_text(name, bucket)
    if code == 404:
        return 404, {"status": "NOT_FOUND", "message": "comment not found"}
    if code != 200:
        return 502, {"status": "ERROR", "message": f"read failed (GCS {code}): {error_message(txt)}"}
    try:
        rec = json.loads(txt)
    except json.JSONDecodeError:
        return 502, {"status": "ERROR", "message": "comment object unreadable"}
    is_admin = bool(ADMIN_KEY) and admin and secrets.compare_digest(admin, ADMIN_KEY)
    is_author = bool(token) and bool(rec.get("delete_token")) and secrets.compare_digest(token, str(rec.get("delete_token")))
    if not (is_admin or is_author):
        return 403, {"status": "FORBIDDEN", "message": "not allowed to delete this comment"}
    if rec.get("deleted"):
        return 200, {"status": "SUCCESS", "id": cid, "already": True}
    rec["deleted"] = True
    rec["deleted_at"] = dt.datetime.now(KST).isoformat(timespec="seconds")
    rec["deleted_by"] = "admin" if is_admin else "author"
    code, payload = gcs_upload(name, json.dumps(rec, ensure_ascii=False, indent=2).encode("utf-8"), bucket,
                               content_type="application/json; charset=utf-8")
    if code != 200:
        return 502, {"status": "ERROR", "message": f"delete not saved (GCS {code}): {error_message(payload)}"}
    with _cache_lock:
        _cache.pop(doc_id, None)
    return 200, {"status": "SUCCESS", "id": cid, "deleted_by": rec["deleted_by"]}
