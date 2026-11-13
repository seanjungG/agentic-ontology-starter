# -*- coding: utf-8 -*-
"""Unit tests for Starter Pack Admin Google Sign-In Guard & Unified Core MCP Portal + Metering API (GOAL-294 · GOAL-295)."""
from __future__ import annotations

import base64
import hashlib
import json
import re
import sys
import threading
import time
import urllib.error
import urllib.request
from http.server import HTTPServer
from pathlib import Path
from unittest import mock

import pytest

STARTER_ROOT = Path(__file__).resolve().parent.parent
if str(STARTER_ROOT) not in sys.path:
    sys.path.insert(0, str(STARTER_ROOT))

from src.web import admin_metering, studio_server  # noqa: E402

# Deterministic 1024-bit RSA test keypair (two 512-bit primes) for zero-dependency stdlib RS256 JWT tests.
_TEST_P = int(
    "d4e3a7f5b8c91021456789abcdef0123456789abcdef0123456789abcdef0123"
    "789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123805",
    16,
)
_TEST_Q = int(
    "e7b1c2d3f4a5061728394a5b6c7d8e9fa0b1c2d3e4f5061728394a5b6c7d8e9f"
    "112233445566778899aabbccddeeff00112233445566778899aabbccddeeff2d",
    16,
)


def _next_prime(n: int) -> int:
    n |= 1
    while True:
        if all(pow(a, n - 1, n) == 1 for a in (2, 3, 5, 7, 11)):
            return n
        n += 2


def _make_test_rsa():
    p = _next_prime(_TEST_P)
    q = _next_prime(_TEST_Q)
    n = p * q
    phi = (p - 1) * (q - 1)
    e = 65537
    d = pow(e, -1, phi)
    return n, e, d


_RSA_N, _RSA_E, _RSA_D = _make_test_rsa()


def _b64e(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode("ascii").rstrip("=")


def _sign_rs256_jwt(claims: dict, *, kid: str = "test-kid-1", alg: str = "RS256", tamper: bool = False) -> str:
    header = {"alg": alg, "typ": "JWT", "kid": kid}
    h64 = _b64e(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    p64 = _b64e(json.dumps(claims, separators=(",", ":")).encode("utf-8"))
    msg = f"{h64}.{p64}".encode("ascii")
    k = (_RSA_N.bit_length() + 7) // 8
    t = admin_metering._SHA256_PREFIX + hashlib.sha256(msg).digest()
    em = b"\x00\x01" + b"\xff" * (k - len(t) - 3) + b"\x00" + t
    sig_int = pow(int.from_bytes(em, "big"), _RSA_D, _RSA_N)
    sig = sig_int.to_bytes(k, "big")
    if tamper:
        sig = bytes([sig[0] ^ 0xFF]) + sig[1:]
    return f"{h64}.{p64}.{_b64e(sig)}"


def _jwk_lookup(kid: str):
    if kid != "test-kid-1":
        raise admin_metering.AuthFailed("unknown signing key")
    return _RSA_N, _RSA_E


def _clear_admin_env(monkeypatch):
    for var in (
        "STARTER_ADMIN_AUTH_MODE",
        "STARTER_ADMIN_FIREBASE_PROJECT",
        "STARTER_ADMIN_FIREBASE_API_KEY",
        "STARTER_ADMIN_AUTH_DOMAIN",
        "STARTER_ADMIN_SESSION_HOURS",
        "STARTER_ADMIN_KEY",
        "UCC_ADMIN_KEY",
        "STARTER_ADMIN_EMAILS",
        "STARTER_ADMIN_SESSION_SECRET",
    ):
        monkeypatch.delenv(var, raising=False)


def test_google_signin_rs256_verify_allowlist_and_cookie(monkeypatch):
    _clear_admin_env(monkeypatch)
    monkeypatch.setenv("STARTER_ADMIN_AUTH_MODE", "google")
    monkeypatch.setenv("STARTER_ADMIN_FIREBASE_PROJECT", "demo-auth-project")
    monkeypatch.setenv("STARTER_ADMIN_FIREBASE_API_KEY", "test-public-browser-key")
    monkeypatch.setenv("STARTER_ADMIN_EMAILS", "admin@example.com")
    monkeypatch.setenv("STARTER_ADMIN_SESSION_SECRET", "unit-test-hmac-secret-32bytes")
    monkeypatch.setenv("UCC_ADMIN_KEY", "legacy-ucc-key-must-be-rejected")

    st = admin_metering.admin_config_status()
    assert st["configured"] is True
    assert st["auth_mode"] == "google"
    assert st["google_auth"]["enabled"] is True
    assert st["google_auth"]["projectId"] == "demo-auth-project"
    assert st["authenticated"] is False
    assert st["allowlist_count"] == 1

    now = time.time()
    base_claims = {
        "iss": "https://securetoken.google.com/demo-auth-project",
        "aud": "demo-auth-project",
        "sub": "uid-admin-1",
        "email": "admin@example.com",
        "email_verified": True,
        "name": "Demo Admin",
        "picture": "https://example.com/p.png",
        "iat": int(now) - 10,
        "exp": int(now) + 3600,
        "firebase": {"sign_in_provider": "google.com"},
    }
    good_tok = _sign_rs256_jwt(base_claims)
    verified = admin_metering.verify_firebase_id_token(good_tok, project="demo-auth-project", now=now, jwk_lookup=_jwk_lookup)
    assert verified["email"] == "admin@example.com"
    assert verified["name"] == "Demo Admin"

    # Negative JWT cases
    with pytest.raises(admin_metering.AuthFailed, match="invalid ID token signature"):
        admin_metering.verify_firebase_id_token(_sign_rs256_jwt(base_claims, tamper=True), project="demo-auth-project", now=now, jwk_lookup=_jwk_lookup)
    with pytest.raises(admin_metering.AuthFailed, match="wrong audience"):
        admin_metering.verify_firebase_id_token(_sign_rs256_jwt({**base_claims, "aud": "other-proj"}), project="demo-auth-project", now=now, jwk_lookup=_jwk_lookup)
    with pytest.raises(admin_metering.AuthFailed, match="expired"):
        admin_metering.verify_firebase_id_token(_sign_rs256_jwt({**base_claims, "exp": int(now) - 120}), project="demo-auth-project", now=now, jwk_lookup=_jwk_lookup)
    with pytest.raises(admin_metering.AuthFailed, match="Google sign-in provider"):
        admin_metering.verify_firebase_id_token(_sign_rs256_jwt({**base_claims, "firebase": {"sign_in_provider": "password"}}), project="demo-auth-project", now=now, jwk_lookup=_jwk_lookup)
    with pytest.raises(admin_metering.AuthFailed, match="verified Google email"):
        admin_metering.verify_firebase_id_token(_sign_rs256_jwt({**base_claims, "email_verified": False}), project="demo-auth-project", now=now, jwk_lookup=_jwk_lookup)

    # Static admin key MUST be rejected with 403 ADMIN_KEY_DISABLED in google mode
    c_key, p_key = admin_metering.authorize_admin({"admin_key": "legacy-ucc-key-must-be-rejected"}, {})
    assert c_key == 403
    assert p_key["code"] == "ADMIN_KEY_DISABLED"

    # Non-allowlisted Google account -> 403 ADMIN_FORBIDDEN
    other_tok = _sign_rs256_jwt({**base_claims, "email": "other-user@example.com"})
    with mock.patch("src.web.admin_metering._jwk", side_effect=_jwk_lookup):
        c_forb, p_forb, _ = admin_metering.handle_auth({"id_token": other_tok}, {})
        assert c_forb == 403
        assert p_forb["code"] == "ADMIN_FORBIDDEN"
        assert p_forb["email"] == "other-user@example.com"

        # Allowlisted admin@example.com -> 200 + HttpOnly Set-Cookie
        c_ok, p_ok, hdrs = admin_metering.handle_auth({"id_token": good_tok}, {"X-Forwarded-Proto": "https"})
        assert c_ok == 200
        assert p_ok["authorized"] is True
        assert p_ok["user"]["email"] == "admin@example.com"
        sc = hdrs["Set-Cookie"]
        assert sc.startswith("aos_starter_admin=")
        assert "HttpOnly" in sc and "SameSite=Lax" in sc and "Secure" in sc
        cookie_pair = sc.split(";", 1)[0]

    # Cookie authenticates /status and authorize_admin
    st_in = admin_metering.admin_config_status({"Cookie": cookie_pair})
    assert st_in["authenticated"] is True
    assert st_in["user"]["email"] == "admin@example.com"

    ac, ai = admin_metering.authorize_admin({}, {"Cookie": cookie_pair})
    assert ac == 200 and ai["via_cookie"] is True

    # Immediate revocation if email removed from STARTER_ADMIN_EMAILS
    monkeypatch.setenv("STARTER_ADMIN_EMAILS", "someoneelse@example.com")
    ac_rev, ai_rev = admin_metering.authorize_admin({}, {"Cookie": cookie_pair})
    assert ac_rev == 403 and ai_rev["code"] == "ADMIN_FORBIDDEN"

    # Sliding cookie renewal triggers when < 50% TTL left
    monkeypatch.setenv("STARTER_ADMIN_EMAILS", "admin@example.com")
    short_tok, short_exp = admin_metering._sign_session("admin@example.com", "google_signin", ttl_s=1000)
    renew = admin_metering.maybe_renew_cookie(
        {"via_cookie": True, "principal": "admin@example.com", "auth_method": "session:google_signin", "expires_at": short_exp},
        {"X-Forwarded-Proto": "https"},
    )
    assert renew is not None and "aos_starter_admin=" in renew and short_tok not in renew

    # Logout clears cookie
    lc, lp, lhdrs = admin_metering.handle_logout({"X-Forwarded-Proto": "https"})
    assert lc == 200 and lp["logged_out"] is True
    assert "Max-Age=0" in lhdrs["Set-Cookie"]


def test_authorize_admin_legacy_fail_closed_and_key_session_oauth(monkeypatch):
    _clear_admin_env(monkeypatch)
    # 1. Fail-closed when unconfigured
    code, payload = admin_metering.authorize_admin({}, {})
    assert code == 503
    assert payload["status"] == "ADMIN_NOT_CONFIGURED"
    assert admin_metering.admin_config_status()["configured"] is False

    # 2. Legacy mode: Fallback to UCC_ADMIN_KEY works; missing -> 401; wrong -> 403; valid -> 200
    monkeypatch.setenv("UCC_ADMIN_KEY", "ucc-secret-123")
    st = admin_metering.admin_config_status()
    assert st["configured"] is True
    assert st["auth_mode"] == "legacy"
    assert st["auth_modes"] == ["admin_key"]

    assert admin_metering.authorize_admin({}, {})[0] == 401
    assert admin_metering.authorize_admin({"admin_key": "wrong"}, {})[0] == 403
    code, info = admin_metering.authorize_admin({}, {"X-AOS-Admin-Key": "ucc-secret-123"})
    assert code == 200
    assert info["auth_method"] == "admin_key"

    # 3. STARTER_ADMIN_KEY overrides UCC_ADMIN_KEY
    monkeypatch.setenv("STARTER_ADMIN_KEY", "starter-only-key")
    assert admin_metering.authorize_admin({"admin_key": "ucc-secret-123"}, {})[0] == 403
    code, auth_res, extra = admin_metering.handle_auth({"admin_key": "starter-only-key"}, {})
    assert code == 200
    assert "Set-Cookie" in extra
    sess = auth_res["admin_session"]
    assert sess and "." in sess

    # Session works via header or body
    assert admin_metering.authorize_admin({}, {"X-AOS-Admin-Session": sess})[0] == 200
    assert admin_metering.authorize_admin({"admin_session": sess}, {})[0] == 200
    # Tampered session rejected
    assert admin_metering.authorize_admin({}, {"X-AOS-Admin-Session": sess + "tamper"})[0] == 401

    # Expired session rejected
    expired_sess, _ = admin_metering._sign_session("admin-key", "admin_key", ttl_s=60)
    with mock.patch("src.web.admin_metering.time.time", return_value=time.time() + 120):
        assert admin_metering.authorize_admin({"admin_session": expired_sess}, {})[0] == 401

    # 4. OAuth allowlist without STARTER_ADMIN_EMAILS -> 403 OAUTH_NOT_ENABLED
    oauth_pfx = "ya" + "29."
    fake_verify = lambda tok: (True, "admin@example.com") if tok == oauth_pfx + "ok" else (False, "")
    c_no_allow, p_no_allow = admin_metering.authorize_admin({"access_token": oauth_pfx + "ok"}, {}, token_verifier=fake_verify)
    assert c_no_allow == 403
    assert p_no_allow["code"] == "OAUTH_NOT_ENABLED"

    # With STARTER_ADMIN_EMAILS allowlist
    monkeypatch.setenv("STARTER_ADMIN_EMAILS", "admin@example.com")
    assert admin_metering.authorize_admin({"access_token": oauth_pfx + "bad"}, {}, token_verifier=fake_verify)[0] == 401
    assert admin_metering.authorize_admin(
        {"access_token": oauth_pfx + "other"}, {}, token_verifier=lambda _t: (True, "outsider@gmail.com")
    )[0] == 403
    c_ok, i_ok = admin_metering.authorize_admin({"access_token": oauth_pfx + "ok"}, {}, token_verifier=fake_verify)
    assert c_ok == 200
    assert i_ok["principal"] == "admin@example.com"
    assert i_ok["auth_method"] == "oauth_allowlist"


def test_clean_filters_query_overview_export_and_portal_proxy(monkeypatch):
    monkeypatch.setenv("AOS_METERING_BQ_TABLE", "seanjung-agentic-starter.aos_metering.core_mcp_usage_events")
    f = admin_metering._clean_filters({
        "days": 999,
        "principal_type": "DROP TABLE",
        "status": "ok",
        "principal_hash": "deadbeef1234",
        "tool_name": "aos_core_catalog; --",
        "recent_limit": 5,
    })
    assert f["days"] == 90
    assert f["principal_type"] == ""
    assert f["status"] == "ok"
    assert f["principal_hash"] == "deadbeef1234"
    assert f["tool_name"] == ""
    assert f["recent_limit"] == 10

    mock_row = {
        "summary_json": json.dumps({
            "calls": 12, "errors": 1, "error_rate": 0.0833, "accounts": 3, "tools": 4,
            "gemini_calls": 2, "tokens_in": 1500, "tokens_out": 400, "tokens_thought": 300,
            "tokens_total": 2200, "request_bytes": 4000, "response_bytes": 16000,
            "bq_bytes_processed": 1000000, "metering_units": 16.3, "p50_ms": 42, "p95_ms": 510,
        }),
        "by_day_json": json.dumps([
            {"day": "2026-11-12", "calls": 12, "errors": 1, "accounts": 3, "gemini_calls": 2,
             "tokens_total": 2200, "payload_bytes": 20000, "bq_bytes_processed": 1000000,
             "metering_units": 16.3, "p95_ms": 510}
        ]),
        "by_account_json": json.dumps([
            {"principal_hash": "abc123def456", "principal_id": "s***@google.com",
             "principal_type": "user", "principal_domain": "google.com",
             "auth_method": "oauth_user", "auth_verified": True, "calls": 10, "errors": 1,
             "error_rate": 0.1, "tools_used": 3, "gemini_calls": 2, "tokens_total": 2200,
             "payload_bytes": 18000, "bq_bytes_processed": 1000000, "metering_units": 14.3,
             "p50_ms": 45, "p95_ms": 510, "last_seen_kst": "2026-11-12 18:40:00"}
        ]),
        "by_tool_json": json.dumps([
            {"tool_name": "aos_core_catalog", "tool_category": "intake", "calls": 8, "errors": 0,
             "error_rate": 0.0, "accounts": 3, "gemini_calls": 0, "tokens_total": 0,
             "payload_bytes": 12000, "bq_bytes_processed": 0, "metering_units": 8.0,
             "p50_ms": 20, "p95_ms": 40, "last_seen_kst": "2026-11-12 18:40:00"}
        ]),
        "by_type_json": json.dumps([{"principal_type": "user", "accounts": 1, "calls": 10, "errors": 1, "gemini_calls": 2, "tokens_total": 2200, "metering_units": 14.3}]),
        "by_client_json": json.dumps([{"client_name": "agentic-ontology-starter/v6.13.0-GOAL-295", "calls": 10, "accounts": 1, "metering_units": 14.3}]),
        "recent_json": json.dumps([
            {"event_id": "ev1", "event_ts_kst": "2026-11-12 18:40:00", "principal_id": "s***@google.com",
             "principal_hash": "abc123def456", "principal_type": "user", "auth_method": "oauth_user",
             "auth_verified": True, "tool_name": "aos_core_catalog", "tool_category": "intake",
             "client_name": "starter", "target_project": "seanjung-agentic-starter", "status": "ok",
             "error_code": "", "duration_ms": 20, "request_bytes": 100, "response_bytes": 1500,
             "gemini_calls": 0, "gemini_model": "", "tokens_in": 0, "tokens_out": 0, "tokens_thought": 0,
             "tokens_total": 0, "bq_bytes_processed": 0, "metering_units": 1.0002}
        ]),
    }

    def fake_bq(sql, params, project):
        assert project == "seanjung-agentic-starter"
        assert "`seanjung-agentic-starter.aos_metering.core_mcp_usage_events`" in sql
        return {"status": "SUCCESS", "rows": [mock_row], "job_id": "job-123", "bytes_processed": 65536}

    code, res = admin_metering.query_metering_overview(
        {"days": 7, "principal_type": "user"},
        bq_executor=fake_bq,
        meta_fetcher=lambda _f: ({"status": "HEALTHY", "metering": {"bq_enabled": True}}, {"policy_version": "1.0.0"}),
    )
    assert code == 200 and res["summary"]["calls"] == 12

    # CSV export includes UTF-8 BOM
    ec, body, ctype, fname = admin_metering.export_metering_bytes({"format": "csv", "scope": "accounts", "days": 7}, bq_executor=fake_bq)
    assert ec == 200 and ctype.startswith("text/csv") and fname.endswith(".csv") and body.startswith(b"\xef\xbb\xbf")

    # Portal catalog proxy
    c_cat, p_cat = admin_metering.fetch_core_mcp_catalog(
        force=True,
        http_get=lambda url, _t: (200, {"status": "SUCCESS", "tools_count": 57, "categories": [], "tools": [], "flow": {"lanes": [], "callers": []}})
        if "/portal/api/catalog" in url else (404, {}),
    )
    assert c_cat == 200 and p_cat["catalog"]["tools_count"] == 57
    c_cat_err, _ = admin_metering.fetch_core_mcp_catalog(force=True, http_get=lambda _u, _t: (503, {"message": "down"}))
    assert c_cat_err == 502

    # Live usage proxy
    c_live, p_live = admin_metering.fetch_core_mcp_live_usage(
        {"hours": 6, "tz_offset": 540},
        http_get=lambda url, _t: (200, {"status": "SUCCESS", "source": "live", "totals": {"calls": 5}}) if "source=live" in url else (404, {}),
    )
    assert c_live == 200 and p_live["usage"]["totals"]["calls"] == 5


def test_studio_server_http_google_auth_and_portal_routes(monkeypatch):
    _clear_admin_env(monkeypatch)
    monkeypatch.setenv("STARTER_ADMIN_AUTH_MODE", "google")
    monkeypatch.setenv("STARTER_ADMIN_FIREBASE_PROJECT", "demo-auth-project")
    monkeypatch.setenv("STARTER_ADMIN_FIREBASE_API_KEY", "test-public-browser-key")
    monkeypatch.setenv("STARTER_ADMIN_EMAILS", "admin@example.com")
    monkeypatch.setenv("STARTER_ADMIN_SESSION_SECRET", "http-test-secret")
    monkeypatch.setenv("UCC_ADMIN_KEY", "old-static-key")

    httpd = HTTPServer(("127.0.0.1", 0), studio_server.StudioHandler)
    port = httpd.server_address[1]
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()

    def _req(path: str, data=None, headers=None):
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}{path}",
            data=(json.dumps(data).encode("utf-8") if data is not None else None),
            method=("POST" if data is not None else "GET"),
            headers={"Content-Type": "application/json", **(headers or {})},
        )
        try:
            with urllib.request.urlopen(req, timeout=4.0) as r:
                return r.status, r.read(), dict(r.headers)
        except urllib.error.HTTPError as e:
            return e.code, e.read(), dict(e.headers)

    try:
        # GET /admin serves HTML with Referrer-Policy: strict-origin-when-cross-origin
        code, body, hdrs = _req("/admin")
        assert code == 200 and b"chip-admin" in body
        assert hdrs.get("Referrer-Policy") == "strict-origin-when-cross-origin"

        # GET /api/v5/admin/status shows google mode, never leaks session secret or UCC key
        code, body, _ = _req("/api/v5/admin/status")
        st = json.loads(body.decode("utf-8"))
        assert code == 200 and st["auth_mode"] == "google" and st["google_auth"]["enabled"] is True and st["authenticated"] is False
        assert "http-test-secret" not in body.decode("utf-8") and "old-static-key" not in body.decode("utf-8")

        # Unauthenticated portal catalog & overview blocked with 401
        assert _req("/api/v5/admin/metering/overview", data={"days": 7})[0] == 401
        assert _req("/api/v5/admin/portal/catalog", data={})[0] == 401
        assert _req("/api/v5/admin/portal/live-usage", data={"hours": 24})[0] == 401

        # Static admin key blocked with 403 ADMIN_KEY_DISABLED
        c_k, b_k, _ = _req("/api/v5/admin/auth", data={"admin_key": "old-static-key"})
        assert c_k == 403 and json.loads(b_k.decode("utf-8"))["code"] == "ADMIN_KEY_DISABLED"

        # Sign in with valid RS256 Google ID token for admin@example.com -> Set-Cookie
        now = time.time()
        id_tok = _sign_rs256_jwt({
            "iss": "https://securetoken.google.com/demo-auth-project",
            "aud": "demo-auth-project",
            "sub": "uid-1",
            "email": "admin@example.com",
            "email_verified": True,
            "name": "Demo Admin",
            "iat": int(now) - 5,
            "exp": int(now) + 3600,
            "firebase": {"sign_in_provider": "google.com"},
        })
        with mock.patch("src.web.admin_metering._jwk", side_effect=_jwk_lookup):
            c_a, b_a, h_a = _req("/api/v5/admin/auth", data={"id_token": id_tok})
        assert c_a == 200
        cookie_hdr = h_a["Set-Cookie"].split(";", 1)[0]
        assert cookie_hdr.startswith("aos_starter_admin=")

        # Status now reflects authenticated admin@example.com via cookie
        _, b_st2, _ = _req("/api/v5/admin/status", headers={"Cookie": cookie_hdr})
        st2 = json.loads(b_st2.decode("utf-8"))
        assert st2["authenticated"] is True and st2["user"]["email"] == "admin@example.com"

        # Authenticated portal catalog & overview work via cookie
        with mock.patch("src.web.admin_metering.fetch_core_mcp_catalog", return_value=(200, {"status": "OK", "catalog": {"tools_count": 57}})):
            c_c, b_c, _ = _req("/api/v5/admin/portal/catalog", data={}, headers={"Cookie": cookie_hdr})
            assert c_c == 200
            cat_res = json.loads(b_c.decode("utf-8"))
            assert cat_res["catalog"]["tools_count"] == 57
            assert cat_res["admin"]["allowed_emails"] == ["admin@example.com"]

        # Logout clears cookie
        c_lo, _, h_lo = _req("/api/v5/admin/logout", data={}, headers={"Cookie": cookie_hdr})
        assert c_lo == 200 and "Max-Age=0" in h_lo["Set-Cookie"]
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_frontend_i18n_parity_and_no_hangul_in_js():
    static = STARTER_ROOT / "src" / "web" / "static"
    i18n = json.loads((static / "studio_i18n.json").read_text(encoding="utf-8"))
    assert set(i18n["ko"].keys()) == set(i18n["en"].keys())
    hangul = re.compile(r"[\uac00-\ud7a3\u3131-\u318e]")
    en_hangul = [k for k, v in i18n["en"].items() if hangul.search(str(v)) and k != "lang.ko"]
    assert en_hangul == []
    js_src = (static / "studio.js").read_text(encoding="utf-8")
    assert hangul.findall(js_src) == []
