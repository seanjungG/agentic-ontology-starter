# Copyright (c) 2026 Sean Jung (seanjung@google.com). All Rights Reserved.
# Non-Commercial Use Only: Methodology & Docs under CC BY-NC-ND 4.0; Source Code under PolyForm Noncommercial License 1.0.0.
# Commercial use, paid consulting/SI/PoC delivery, or production deployment requires prior written permission from seanjung@google.com.

# -*- coding: utf-8 -*-
"""
platform_core_mcp.py (Abstracted Compatibility Layer)
In Starter Pack v2.2, internal MCP builder server tools are abstracted away from Starter exposure.
The Starter Pack connects directly to Ready-to-Use GCP Ontology Resources via `OntologyResourceConnector`
(`src/resource_connector.py`). This module delegates to `OntologyResourceConnector` for backward compatibility.
"""

from typing import Any, Dict, Optional
from src.resource_connector import (
    CODE_EXPOSURE_BOUNDARY,
    REFERENCE_STUDIOS,
    STAGE_UNIFIED_MAP,
    OntologyResourceConnector,
)


class PlatformCoreMcpClient(OntologyResourceConnector):
    """Compatibility alias delegating to OntologyResourceConnector (Ready-to-Use GCP Resource Connector)."""

    def __init__(self, endpoint_url: Optional[str] = None, timeout_sec: int = 120, **kwargs: Any):
        super().__init__(**kwargs)
        self.endpoint_url = endpoint_url or "https://agentic-ontology-studio-lguplus-mcp-924723860007.asia-northeast3.run.app"
        self.timeout_sec = timeout_sec

    def get_architecture_overview(self) -> Dict[str, Any]:
        return self.get_resource_manifest()


__all__ = [
    "OntologyResourceConnector",
    "PlatformCoreMcpClient",
    "REFERENCE_STUDIOS",
    "CODE_EXPOSURE_BOUNDARY",
    "STAGE_UNIFIED_MAP",
]
