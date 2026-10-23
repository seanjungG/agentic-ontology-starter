# Copyright (c) 2026 Sean Jung (seanjung@google.com). All Rights Reserved.
# Non-Commercial Use Only: Methodology & Docs under CC BY-NC-ND 4.0; Source Code under PolyForm Noncommercial License 1.0.0.
# Commercial use, paid consulting/SI/PoC delivery, or production deployment requires prior written permission from seanjung@google.com.

# -*- coding: utf-8 -*-
"""
Agentic Ontology Starter — wizard server (v4.0.0-GOAL-223, Python stdlib only).

Front end: static files in src/web/static/ (index.html · app.css · app.js · flows.js · aolflow.js/css).
Six steps: 1 type & purpose → 2 flow → 3 GCP resources (real checks) → 4 load data (real loads, streamed log)
→ 5 run agents (streamed) → 6 evaluate (streamed). Every request carries the resources entered in step 3
(request-scoped StarterConfig); global defaults come from the environment and are never mutated.

  GET  /                      studio.html (v5 studio, GOAL-233) · GET /wizard = classic 6-step wizard (index.html)
  GET  /api/v5/bootstrap · POST /api/v5/*   v5 studio API — see src/web/v5_routes.py
  GET  /static/<file>         static assets (flat directory, whitelisted extensions)
  GET  /health                version · project · model
  GET  /api/settings          env defaults, graph names per recipe, writable projects
  GET  /api/catalog?lang=     recipes · step plans · IAM · bilingual data pack · agent presets
  POST /api/verify            step 3 checks                    {config, recipe, lang, spanner}
  POST /api/ddl               property graph DDL preview       {config, recipe}
  POST /api/load              step 4 (NDJSON stream)           {config, recipe, lang, spanner}
  POST /api/agent             step 5 (NDJSON stream)           {config, recipe, agent, question, lang}
  POST /api/eval              step 6 (NDJSON stream)           {config, recipe, lang}
  POST /api/mcp/execute       one domain MCP tool              {config, recipe, lang, tool_name, args}
  GET  /api/core-mcp/tools    Platform Core MCP tools/list
  POST /api/core-mcp/call     Platform Core MCP tools/call (aos_builder_* only)
  GET  /ucc · /ucc/brd · /ucc/sdd   UCC shared docs viewer (ucc.html) — GOAL-230
  GET  /api/ucc/docs · /api/ucc/doc?id= · /api/ucc/comments?doc=    see src/web/ucc_pages.py
  POST /api/ucc/comments      per-section comment → GCS (relayed to Jetski Chat by the Cloudtop relay)
  POST /api/ucc/comments/delete  soft delete (author delete_token or UCC_ADMIN_KEY) — GOAL-231; docs are KO/EN (?lang=)
"""
import http.server
import json
import os
import re
import socket
import sys
import threading
from typing import Any, Callable, Dict
from urllib.parse import parse_qs, urlparse

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, BASE_DIR)

from src import datapack, recipes  # noqa: E402
from src.agent.agents import make_server, presets, run_agent  # noqa: E402
from src.config import (APP_VERSION, DEFAULT_GRAPH, GITHUB_URL, ConfigError, StarterConfig, defaults,  # noqa: E402
                        write_projects)
from src.evaluation import run_eval  # noqa: E402
from src.gcp_client import call_core_mcp, runtime_settings  # noqa: E402
from src.loader import graph_check_sql, run_load, verify  # noqa: E402
from src.resource_connector import STARTER_PUBLIC_URL  # noqa: E402
from src.web import ucc_pages  # noqa: E402
from src.web import v5_routes  # noqa: E402

PORT = int(os.environ.get("PORT", 8080))
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
MAX_BODY = 512 * 1024
MAX_BODY_V5 = 20 * 1024 * 1024  # /api/v5/* (uploads ≤ 12 MB as base64 — GOAL-243 PDF/Office, wiki pages, workspaces)
_STATIC_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,80}$")
CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8", ".js": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8", ".svg": "image/svg+xml", ".png": "image/png", ".ico": "image/x-icon",
    ".woff2": "font/woff2", ".txt": "text/plain; charset=utf-8",
}


def resolve_static(name: str):
    """Returns (abs_path, content_type) for a whitelisted static file, else None (no traversal, no subdirectories)."""
    if not _STATIC_NAME.match(name or "") or ".." in name:
        return None
    ext = os.path.splitext(name)[1].lower()
    if ext not in CONTENT_TYPES:
        return None
    path = os.path.realpath(os.path.join(STATIC_DIR, name))
    if os.path.dirname(path) != os.path.realpath(STATIC_DIR) or not os.path.isfile(path):
        return None
    return path, CONTENT_TYPES[ext]


def settings_payload() -> Dict[str, Any]:
    return {**runtime_settings(), "version": APP_VERSION, "defaults": defaults(), "graph_defaults": DEFAULT_GRAPH,
            "write_projects": write_projects(), "public_url": STARTER_PUBLIC_URL, "github_url": GITHUB_URL,
            "model_display": "Gemini 4 Argon" if runtime_settings()["vertex_model"] == "gemini-4-argon" else runtime_settings()["vertex_model"]}


def catalog_payload(lang: str) -> Dict[str, Any]:
    lang = "en" if lang == "en" else "ko"
    cat = recipes.catalog(lang)
    cat["presets"] = {k: {a: presets(lang, k, a) for a in r["agents"]} for k, r in recipes.RECIPES.items()}
    cat["data"] = datapack.catalog(lang)
    cat["version"] = APP_VERSION
    cat["lang"] = lang
    return cat


class StudioHandler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "AgenticOntologyStarter/4.0"

    def log_message(self, format, *args):  # quiet access log; errors are returned to the client
        pass

    # ------------------------------------------------------------------ responses
    def _send(self, code: int, body: bytes, ctype: str, cache: str = "no-cache"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", cache)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "same-origin")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _send_bytes(self, code: int, body: bytes, ctype: str, headers: Dict[str, str]):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj: Any, code: int = 200):
        self._send(code, json.dumps(obj, ensure_ascii=False, default=str).encode("utf-8"), "application/json; charset=utf-8")

    def _not_found(self):
        self._json({"status": "NOT_FOUND", "path": urlparse(self.path).path}, 404)

    def _stream(self, fn: Callable[[Callable[[Dict[str, Any]], None]], None]):
        """NDJSON over chunked transfer encoding: one JSON event per line, flushed as it happens."""
        self.send_response(200)
        self.send_header("Content-Type", "application/x-ndjson; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Accel-Buffering", "no")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Transfer-Encoding", "chunked")
        self.end_headers()
        lock, alive = threading.Lock(), [True]

        def emit(ev: Dict[str, Any]) -> None:
            if not alive[0]:
                return
            data = (json.dumps(ev, ensure_ascii=False, default=str) + "\n").encode("utf-8")
            with lock:
                try:
                    self.wfile.write(f"{len(data):X}\r\n".encode("ascii") + data + b"\r\n")
                    self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError, OSError):
                    alive[0] = False

        try:
            fn(emit)
        except Exception as e:  # surface server-side failures in the stream
            emit({"type": "error", "message": f"{type(e).__name__}: {str(e)[:500]}"})
        finally:
            with lock:
                try:
                    self.wfile.write(b"0\r\n\r\n")
                    self.wfile.flush()
                except OSError:
                    pass
            self.close_connection = True

    def _body(self) -> Dict[str, Any]:
        length = int(self.headers.get("Content-Length") or 0)
        limit = MAX_BODY_V5 if urlparse(self.path).path.startswith("/api/v5/") else MAX_BODY
        if length > limit:
            raise ValueError("request body too large")
        raw = self.rfile.read(length).decode("utf-8") if length else ""
        data = json.loads(raw) if raw else {}
        if not isinstance(data, dict):
            raise ValueError("JSON object expected")
        return data

    # ------------------------------------------------------------------ GET
    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        parsed = urlparse(self.path)
        path, qs = parsed.path, parse_qs(parsed.query)
        arg = lambda k, d="": (qs.get(k) or [d])[0]  # noqa: E731
        if path in ("/", "/index.html", "/studio"):
            hit = resolve_static("studio.html")
            with open(hit[0], "rb") as f:
                return self._send(200, f.read(), hit[1])
        if path in ("/wizard", "/wizard/"):  # GOAL-233: the classic 6-step wizard (curated sample, Flow A/B/C)
            hit = resolve_static("index.html")
            with open(hit[0], "rb") as f:
                return self._send(200, f.read(), hit[1])
        if path == "/api/v5/bootstrap":
            return self._json(v5_routes.bootstrap("en" if arg("lang") == "en" else "ko"))
        if path in ("/ucc", "/ucc/", "/ucc/brd", "/ucc/sdd"):
            hit = resolve_static("ucc.html")
            with open(hit[0], "rb") as f:
                return self._send(200, f.read(), hit[1])
        if path == "/api/ucc/docs":
            return self._json(ucc_pages.docs_payload())
        if path == "/api/ucc/doc":
            doc = ucc_pages.load_doc(arg("id", "brd").lower(), arg("lang", "ko"))
            return self._json(doc) if doc else self._json({"status": "NOT_FOUND", "message": "document not published"}, 404)
        if path == "/api/ucc/comments":
            code, payload = ucc_pages.list_comments(arg("doc", "brd").lower(), force=arg("refresh") == "1")
            return self._json(payload, code)
        if path.startswith("/static/"):
            hit = resolve_static(path[len("/static/"):])
            if not hit:
                return self._not_found()
            with open(hit[0], "rb") as f:
                return self._send(200, f.read(), hit[1])
        if path == "/health":
            s = runtime_settings()
            return self._json({"status": "ok", "version": APP_VERSION, "project_id": s["gcp_project_id"], "model": s["vertex_model"],
                               "vertex_thinking_level": s["vertex_thinking_level"], "vertex_build_thinking_level": s["vertex_build_thinking_level"]})
        if path == "/api/settings":
            return self._json(settings_payload())
        if path == "/api/catalog":
            return self._json(catalog_payload(arg("lang", "ko")))
        if path == "/api/core-mcp/tools":
            res = call_core_mcp("tools/list")
            tools = (res.get("result") or {}).get("tools") or []
            return self._json({**{k: v for k, v in res.items() if k != "result"}, "tool_count": len(tools),
                               "tools": [t.get("name") for t in tools]})
        return self._not_found()

    # ------------------------------------------------------------------ POST
    def do_POST(self):
        path = urlparse(self.path).path
        try:
            data = self._body()
        except (ValueError, json.JSONDecodeError) as e:
            return self._json({"status": "BAD_REQUEST", "message": str(e)}, 400)
        if v5_routes.handle_post(path, data, lambda obj, code=200: self._json(obj, code), self._stream,
                                 lambda code, body, ctype, headers: self._send_bytes(code, body, ctype, headers)):
            return None
        if path == "/api/ucc/comments":
            remote = (self.headers.get("X-Forwarded-For") or "").split(",")[0].strip() or self.client_address[0]
            code, payload = ucc_pages.create_comment(data, remote=remote, user_agent=self.headers.get("User-Agent", ""))
            return self._json(payload, code)
        if path == "/api/ucc/comments/delete":
            code, payload = ucc_pages.delete_comment(data)
            return self._json(payload, code)
        lang = "en" if data.get("lang") == "en" else "ko"
        recipe = str(data.get("recipe") or "C").upper()
        if recipe not in recipes.RECIPES:
            return self._json({"status": "BAD_REQUEST", "message": f"unknown recipe: {recipe}"}, 400)

        if path == "/api/core-mcp/call":
            name = data.get("name") or data.get("tool_name") or "aos_builder_get_domain_spec_template"
            if not str(name).startswith("aos_builder_"):
                return self._json({"status": "ERROR", "error": "only aos_builder_* tools are proxied"}, 400)
            return self._json(call_core_mcp("tools/call", {"name": name, "arguments": data.get("arguments") or {}}))

        try:
            cfg = StarterConfig.from_request(data.get("config") or {}, recipe)
        except ConfigError as e:
            return self._json(e.to_dict(lang), 400)

        if path == "/api/verify":
            return self._json(verify(cfg, recipe, lang, spanner=bool(data.get("spanner"))))
        if path == "/api/ddl":
            return self._json({"recipe": recipe, "graph": cfg.graph_fq,
                               "ddl": datapack.graph_ddl(cfg.project_id, cfg.dataset_id, cfg.graph_name, recipe),
                               "check_sql": graph_check_sql(cfg, recipe) if recipe != "A" else ""})
        if path == "/api/load":
            return self._stream(lambda emit: run_load(cfg, recipe, lang, emit, spanner=bool(data.get("spanner"))))
        if path == "/api/agent":
            agent = str(data.get("agent") or "")
            question = str(data.get("question") or "").strip()[:2000]
            if agent not in recipes.RECIPES[recipe]["agents"]:
                return self._json({"status": "BAD_REQUEST", "message": f"agent '{agent}' is not part of recipe {recipe}"}, 400)
            if not question:
                return self._json({"status": "BAD_REQUEST", "message": "question is empty"}, 400)

            def go(emit):
                res = run_agent(cfg, recipe, agent, lang, question, emit)
                emit({"type": "result", **res})
            return self._stream(go)
        if path == "/api/eval":
            return self._stream(lambda emit: run_eval(cfg, recipe, lang, emit))
        if path == "/api/mcp/execute":
            tool = data.get("tool_name") or "mcp_lookup_customer_profile"
            args = dict(data.get("args") or data.get("arguments") or {})
            args["lang"] = lang
            return self._json(make_server(cfg, recipe).execute_tool(tool, args))
        return self._not_found()


class ThreadingStudioServer(http.server.ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True


class DualStackServer(ThreadingStudioServer):
    """Binds [::] with IPV6_V6ONLY=0 so http://localhost works on IPv4 and IPv6 clients."""
    address_family = socket.AF_INET6

    def server_bind(self):
        try:
            self.socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
        except (AttributeError, OSError):
            pass
        super().server_bind()


def make_server_socket(port: int):
    try:
        return DualStackServer(("::", port), StudioHandler)
    except OSError:
        return ThreadingStudioServer(("0.0.0.0", port), StudioHandler)


def run_server():
    server = make_server_socket(PORT)
    print(f"[STARTER {APP_VERSION}] listening on port {PORT}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    run_server()
