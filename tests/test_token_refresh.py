"""GOAL-234: runtime-token staleness must not surface as `/ucc` comment errors.

- call_core_mcp_tool retries once with a fresh token when Core MCP reports 401 / Invalid Credentials
  for the cached runtime token (never for an explicitly passed or request-bound user token).
- list_comments serves the last good list (stale) when GCS listing fails transiently.
"""
import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src import gcp_client  # noqa: E402
from src.web import ucc_pages  # noqa: E402

AUTH_401 = {"status": "ERROR", "error": {"http_status": 401, "api": "storage", "message": "Invalid Credentials"}}
OK = {"status": "SUCCESS", "items": [], "count": 0}


def _fake_core(responses, calls):
    def fake(method, params=None, url=None, timeout_s=120, access_token=None):
        calls.append(access_token)
        sc = responses.pop(0)
        return {"status": "SUCCESS", "result": {"structuredContent": dict(sc)}}
    return fake


def test_401_with_runtime_token_retries_once(monkeypatch):
    calls, invalidated = [], []
    monkeypatch.setattr(gcp_client, "call_core_mcp", _fake_core([AUTH_401, OK], calls))
    monkeypatch.setattr(gcp_client, "invalidate_gcp_token", lambda: invalidated.append(1))
    sc = gcp_client.call_core_mcp_tool("storage_list_objects", {"bucket": "b", "prefix": "p"})
    assert sc["status"] == "SUCCESS"
    assert len(calls) == 2 and invalidated == [1]


def test_401_retry_happens_only_once(monkeypatch):
    calls = []
    monkeypatch.setattr(gcp_client, "call_core_mcp", _fake_core([AUTH_401, AUTH_401], calls))
    monkeypatch.setattr(gcp_client, "invalidate_gcp_token", lambda: None)
    sc = gcp_client.call_core_mcp_tool("storage_list_objects", {"bucket": "b", "prefix": "p"})
    assert sc["status"] == "ERROR" and len(calls) == 2


def test_no_retry_for_explicit_or_bound_token(monkeypatch):
    calls = []
    monkeypatch.setattr(gcp_client, "call_core_mcp", _fake_core([AUTH_401], calls))
    sc = gcp_client.call_core_mcp_tool("storage_list_objects", {}, access_token="tok-" + "explicit")
    assert sc["status"] == "ERROR" and len(calls) == 1

    from src import identity
    calls2 = []
    monkeypatch.setattr(gcp_client, "call_core_mcp", _fake_core([AUTH_401], calls2))
    with identity.bind("tok-" + "user-bound", {"mode": "token"}):
        sc = gcp_client.call_core_mcp_tool("storage_list_objects", {})
    assert sc["status"] == "ERROR" and len(calls2) == 1


def test_list_comments_serves_stale_cache_on_failure(monkeypatch):
    monkeypatch.setattr(ucc_pages, "_bucket", lambda: "b")
    cached = [{"id": "20261020T100000_abcdef", "section_id": "s01", "text": "hi"}]
    with ucc_pages._cache_lock:
        ucc_pages._cache["brd"] = (time.time() - 3600, cached)
    monkeypatch.setattr(gcp_client, "gcs_list", lambda prefix, bucket: (401, {"error": {"code": 401, "message": "Invalid Credentials"}}))
    try:
        code, payload = ucc_pages.list_comments("brd")
        assert code == 200 and payload["stale"] is True and payload["comments"] == cached
    finally:
        with ucc_pages._cache_lock:
            ucc_pages._cache.pop("brd", None)
