# Copyright (c) 2026 Sean Jung (seanjung@google.com). All Rights Reserved.
# Non-Commercial Use Only: Methodology & Docs under CC BY-NC-ND 4.0; Source Code under PolyForm Noncommercial License 1.0.0.
# Commercial use, paid consulting/SI/PoC delivery, or production deployment requires prior written permission from seanjung@google.com.

# -*- coding: utf-8 -*-
"""Request-scoped resource configuration for the starter wizard (GOAL-223).

Every API call carries the GCP resources the user entered in step 3. `StarterConfig.from_request()` validates them
and fills blanks from the environment defaults (`runtime_settings()`); the module never mutates global defaults, so
two browsers can work on different projects at the same time.
"""
import os
import re
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional

from src.gcp_client import runtime_settings

APP_VERSION = "v6.1.1-GOAL-244"
GITHUB_URL = os.environ.get("STARTER_GITHUB_URL", "https://github.com/seanjungG/agentic-ontology-starter")

# Graph names per recipe: the ledger-only graph (Flow B) never overwrites the unified graph (Flow C).
DEFAULT_GRAPH = {"A": "", "B": "STARTER_LEDGER_GRAPH", "C": "STARTER_ONTOLOGY_GRAPH"}

_RX = {
    "project_id": re.compile(r"^[a-z][a-z0-9-]{4,28}[a-z0-9]$"),
    "region": re.compile(r"^(?:[a-z]+-[a-z]+[0-9]{1,2}|US|EU)$"),
    "dataset_id": re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,1023}$"),
    "bucket": re.compile(r"^[a-z0-9][a-z0-9._-]{1,220}[a-z0-9]$"),
    "graph_name": re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,127}$"),
    "spanner_instance": re.compile(r"^[a-z][a-z0-9-]{0,62}[a-z0-9]$"),
    "spanner_database": re.compile(r"^[a-z][a-z0-9_-]{0,28}[a-z0-9]$"),
    "model": re.compile(r"^[a-z0-9][a-z0-9.\-]{1,62}$"),
    "vertex_location": re.compile(r"^(?:global|[a-z]+-[a-z]+[0-9]{1,2})$"),
}
_LABEL = {
    "project_id": ("프로젝트 ID", "Project ID"), "region": ("리전", "Region"), "dataset_id": ("BigQuery 데이터셋", "BigQuery dataset"),
    "bucket": ("GCS 버킷", "GCS bucket"), "graph_name": ("그래프 이름", "Graph name"),
    "spanner_instance": ("Spanner 인스턴스", "Spanner instance"), "spanner_database": ("Spanner 데이터베이스", "Spanner database"),
    "model": ("Vertex AI 모델", "Vertex AI model"), "vertex_location": ("Vertex AI 위치", "Vertex AI location"),
}
OPTIONAL = {"spanner_instance", "spanner_database"}


class ConfigError(ValueError):
    """Invalid user-entered resource id (field + bilingual message)."""

    def __init__(self, field: str, value: str):
        ko, en = _LABEL.get(field, (field, field))
        self.field = field
        self.message_ko = f"{ko} 값 '{value}'의 형식이 올바르지 않습니다."
        self.message_en = f"The {en} value '{value}' is not valid."
        super().__init__(self.message_en)

    def to_dict(self, lang: str = "ko") -> Dict[str, Any]:
        return {"status": "CONFIG_ERROR", "field": self.field, "message": self.message_en if lang == "en" else self.message_ko}


def defaults(recipe: Optional[str] = None) -> Dict[str, str]:
    s = runtime_settings()
    return {
        "project_id": s["gcp_project_id"],
        "region": s["region"],
        "dataset_id": s["bq_dataset_id"],
        "bucket": s["gcs_bucket"],
        "graph_name": DEFAULT_GRAPH.get((recipe or "C").upper(), DEFAULT_GRAPH["C"]) or DEFAULT_GRAPH["C"],
        "spanner_instance": s["spanner_instance_id"],
        "spanner_database": s["spanner_database_id"],
        "model": s["vertex_model"],
        "vertex_location": s["vertex_location"],
    }


def write_projects() -> List[str]:
    raw = os.environ.get("STARTER_WRITE_PROJECTS", "").strip()
    if raw:
        return [p.strip() for p in raw.split(",") if p.strip()]
    return [runtime_settings()["gcp_project_id"]]


def write_allowed(project_id: str) -> bool:
    allowed = write_projects()
    return "*" in allowed or project_id in allowed


@dataclass(frozen=True)
class StarterConfig:
    project_id: str
    region: str
    dataset_id: str
    bucket: str
    graph_name: str
    spanner_instance: str
    spanner_database: str
    model: str
    vertex_location: str
    core_mcp_url: str

    @property
    def fq(self) -> str:
        return f"{self.project_id}.{self.dataset_id}"

    @property
    def graph_fq(self) -> str:
        return f"{self.project_id}.{self.dataset_id}.{self.graph_name}"

    def gcs_prefix(self, lang: str) -> str:
        return f"starter/{'en' if lang == 'en' else 'ko'}/"

    def to_dict(self) -> Dict[str, str]:
        return asdict(self)

    @classmethod
    def from_request(cls, body: Optional[Dict[str, Any]] = None, recipe: Optional[str] = None) -> "StarterConfig":
        base = defaults(recipe)
        given = dict(body or {})
        out: Dict[str, str] = {}
        for k, dv in base.items():
            v = str(given.get(k) if given.get(k) not in (None, "") else dv).strip()
            if k in OPTIONAL and not v:
                out[k] = ""
                continue
            if not _RX[k].match(v):
                raise ConfigError(k, v)
            out[k] = v
        # The Core MCP URL is server-side only (never taken from a request: no SSRF through the wizard).
        out["core_mcp_url"] = runtime_settings()["core_mcp_url"]
        return cls(**out)
