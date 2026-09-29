# Copyright (c) 2026 Sean Jung (seanjung@google.com). All Rights Reserved.
# Non-Commercial Use Only: Methodology & Docs under CC BY-NC-ND 4.0; Source Code under PolyForm Noncommercial License 1.0.0.
# Commercial use, paid consulting/SI/PoC delivery, or production deployment requires prior written permission from seanjung@google.com.

# -*- coding: utf-8 -*-
"""
Project resolver: one starter checkout hosts several customer / data-domain projects.

- Sample project : repository root (`config/project.json`, `config/*`, `data/*`).
- Added projects : `projects/<id>/` with the same layout, created by `new_project.py`.

Studio API, MCP server, agent engine and pipeline resolve files and GCP settings through here.
This module does not import `src.gcp_client`, so `run_pipeline.py --project` can set the
GCP environment variables before that module reads them.
"""
import glob
import importlib.util
import json
import os
from typing import Any, Callable, Dict, List, Optional

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_CACHE: Dict[tuple, Any] = {}


def _read(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def list_projects() -> List[Dict[str, Any]]:
    """Sample project first, then every `projects/<id>/project.json` (folders starting with `_` are templates)."""
    found = [os.path.join(BASE_DIR, "config/project.json")]
    found += [p for p in sorted(glob.glob(os.path.join(BASE_DIR, "projects/*/project.json")))
              if not os.path.basename(os.path.dirname(p)).startswith("_")]
    roots = [BASE_DIR] + [os.path.dirname(p) for p in found[1:]]
    return [{**_read(p), "root": r, "root_dir": os.path.relpath(r, BASE_DIR)}
            for p, r in zip(found, roots) if os.path.exists(p)]


def get_project(project_id: Optional[str] = None) -> Dict[str, Any]:
    """Resolves `project_id` (or env `STARTER_PROJECT`, else the sample). Only registered ids resolve."""
    projects = list_projects()
    pid = project_id or os.environ.get("STARTER_PROJECT") or projects[0]["project_id"]
    for p in projects:
        if p["project_id"] == pid:
            return p
    raise KeyError(f"Unknown project: {pid}")


def cached(project: Dict[str, Any], kind: str, factory: Callable[[Dict[str, Any]], Any]) -> Any:
    key = (project["project_id"], kind)
    if key not in _CACHE:
        _CACHE[key] = factory(project)
    return _CACHE[key]


def load_override(project: Dict[str, Any], key: str, name: str):
    """Optional per-project class/function, e.g. `"mcp_module": "src/mcp_server.py"` (path relative to the project root)."""
    rel = project.get(key)
    if not rel:
        return None
    spec = importlib.util.spec_from_file_location(f"{project['project_id'].replace('-', '_')}_{key}",
                                                  os.path.join(project["root"], rel))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return getattr(mod, name)


def _build_engine(project: Dict[str, Any]):
    from src.agent.mcp_server import DomainMcpServer
    from src.agent.reasoning_engine import AiFdeAgentEngine
    server_cls = load_override(project, "mcp_module", "DomainMcpServer") or DomainMcpServer
    engine_cls = load_override(project, "engine_module", "AiFdeAgentEngine") or AiFdeAgentEngine
    gcp = {k: v for k, v in (project.get("gcp") or {}).items() if v}  # missing keys -> src.gcp_client defaults
    server = server_cls(**gcp, root_dir=project["root"])
    return engine_cls(project_id=server.project_id, server=server)


def get_engine(project: Dict[str, Any]):
    """One agent engine (with its MCP server) per project, created on first use."""
    return cached(project, "engine", _build_engine)
