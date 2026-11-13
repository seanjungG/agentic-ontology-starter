# Copyright (c) 2026 Sean Jung (seanjung@google.com). All Rights Reserved.
# Non-Commercial Use Only: Methodology & Docs under CC BY-NC-ND 4.0; Source Code under PolyForm Noncommercial License 1.0.0.
# Commercial use, paid consulting/SI/PoC delivery, or production deployment requires prior written permission from seanjung@google.com.

# -*- coding: utf-8 -*-
"""Starter Pack Admin Guard (Google Sign-In SSO) & Unified Core MCP Portal + Metering API (GOAL-294 · GOAL-295).

Pure Python 3.11 stdlib.
1. Admin Authentication (Fail-Closed):
   - Primary mode (`STARTER_ADMIN_AUTH_MODE=google`, auto-enabled when `STARTER_ADMIN_FIREBASE_PROJECT` is set):
     * 1-click Google Sign-In via Identity Platform / Firebase Auth (`signInWithPopup`).
     * Pure-Python RS256 ID token verification against Google's `securetoken` JWKs (`iss`, `aud`, `exp`, `iat`,
       `firebase.sign_in_provider == "google.com"`, `email_verified == True`).
     * Strict email allowlist (`STARTER_ADMIN_EMAILS`, e.g., `admin@example.com`). Non-allowlisted Google accounts
       receive HTTP 403 (`ADMIN_FORBIDDEN`).
     * Issues an HMAC-SHA256 signed `HttpOnly; SameSite=Lax[; Secure]` cookie (`aos_starter_admin`, 12h sliding TTL)
       and re-validates the allowlist on every request.
     * Also accepts Google OAuth2 access tokens (`Authorization: Bearer ...` / `X-AOS-Access-Token`) for CLI/ops
       strictly when the token's email is in `STARTER_ADMIN_EMAILS`.
     * Static `admin_key` / `UCC_ADMIN_KEY` login is explicitly disabled in `google` mode.
   - Legacy mode (self-hosted without Identity Platform):
     * Accepts `STARTER_ADMIN_KEY` (fallback `UCC_ADMIN_KEY`) or `STARTER_ADMIN_EMAILS` OAuth token allowlist.
2. Unified Core MCP Portal & Metering Backend:
   - BigQuery metering aggregation (`seanjung-agentic-starter.aos_metering.core_mcp_usage_events`) via direct REST API
     (never creates recursive Core MCP metering events).
   - Authenticated same-origin proxy for Core MCP `/portal/api/catalog` (57 tools, categories, interactive flow lanes,
     input/output schemas) and `/portal/api/usage?source=live` (live Cloud Run instance ring buffer & hourly chart).
"""
from __future__ import annotations

import base64
import csv
import datetime as dt
import hashlib
import hmac
import io
import json
import os
import re
import secrets
import ssl
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Callable, Dict, List, Optional, Tuple

from src.gcp_client import DEFAULT_CORE_MCP_URL, DEFAULT_PROJECT_ID, get_gcp_token

_CAFILE = os.environ.get("SSL_CERT_FILE") or ("/etc/ssl/cert.pem" if os.path.exists("/etc/ssl/cert.pem") else None)
_CTX = ssl.create_default_context(cafile=_CAFILE)
_KST = dt.timezone(dt.timedelta(hours=9))

COOKIE_NAME = "aos_starter_admin"
JWKS_URL = "https://www.googleapis.com/service_accounts/v1/jwk/securetoken@system.gserviceaccount.com"
_SHA256_PREFIX = bytes.fromhex("3031300d060960864801650304020105000420")

DEFAULT_METERING_TABLE = "seanjung-agentic-starter.aos_metering.core_mcp_usage_events"
_TABLE_FQ_RE = re.compile(r"^[a-z][a-z0-9-]{4,30}\.[a-zA-Z0-9_]{1,128}\.[a-zA-Z0-9_]{1,128}$")
_HASH_RE = re.compile(r"^[a-f0-9]{6,64}$")
_TOOL_RE = re.compile(r"^[a-zA-Z0-9_.-]{1,128}$")
_ALLOWED_TYPES = frozenset({"user", "service_account", "api_key", "oauth_client", "anonymous", "unresolved"})
_ALLOWED_STATUS = frozenset({"ok", "error"})

# In-process caches for JWKs & Core MCP metadata/catalog
_JWKS: Dict[str, Any] = {"keys": {}, "exp": 0.0}
_JWKS_LOCK = threading.Lock()
_MCP_META_CACHE: Dict[str, Any] = {"ts": 0.0, "health": None, "policy": None}
_MCP_CATALOG_CACHE: Dict[str, Any] = {"ts": 0.0, "catalog": None}
_FALLBACK_SECRET = secrets.token_hex(32)


class AuthFailed(Exception):
    """Raised when Firebase ID token validation fails."""


def _env(name: str, default: str = "") -> str:
    return (os.environ.get(name) or "").strip() or default


def _b64d(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def _b64e(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode("ascii").rstrip("=")


def core_mcp_base_url() -> str:
    base = (os.environ.get("CORE_MCP_URL") or DEFAULT_CORE_MCP_URL).strip()
    if base.endswith("/mcp"):
        base = base[:-4]
    return base.rstrip("/")


def metering_table_fq() -> str:
    fq = (os.environ.get("AOS_METERING_BQ_TABLE") or DEFAULT_METERING_TABLE).strip()
    if "." not in fq:
        proj = (os.environ.get("AOS_METERING_BQ_PROJECT") or DEFAULT_PROJECT_ID).strip()
        ds = (os.environ.get("AOS_METERING_BQ_DATASET") or "aos_metering").strip()
        fq = f"{proj}.{ds}.{fq}"
    if not _TABLE_FQ_RE.match(fq):
        return DEFAULT_METERING_TABLE
    return fq


def metering_bq_project() -> str:
    explicit = (os.environ.get("AOS_METERING_BQ_PROJECT") or "").strip()
    if explicit:
        return explicit
    return metering_table_fq().split(".", 1)[0]


def firebase_project() -> str:
    return _env("STARTER_ADMIN_FIREBASE_PROJECT")


def firebase_public_config() -> Dict[str, Any]:
    proj = firebase_project()
    api_key = _env("STARTER_ADMIN_FIREBASE_API_KEY")
    auth_domain = _env("STARTER_ADMIN_AUTH_DOMAIN", f"{proj}.firebaseapp.com" if proj else "")
    return {
        "enabled": bool(admin_auth_mode() == "google" and proj and api_key),
        "provider": "google",
        "projectId": proj,
        "apiKey": api_key,
        "authDomain": auth_domain,
    }


def admin_auth_mode() -> str:
    raw = _env("STARTER_ADMIN_AUTH_MODE").lower()
    if raw in ("google", "legacy"):
        return raw
    return "google" if firebase_project() else "legacy"


def _configured_admin_key() -> str:
    return (os.environ.get("STARTER_ADMIN_KEY") or os.environ.get("UCC_ADMIN_KEY") or "").strip()


def _configured_admin_emails() -> List[str]:
    raw = (os.environ.get("STARTER_ADMIN_EMAILS") or "").strip()
    return [x.strip().lower() for x in raw.split(",") if x.strip()]


def session_ttl_sec() -> int:
    try:
        hours = float(_env("STARTER_ADMIN_SESSION_HOURS", "12"))
        return max(300, min(7 * 86400, int(round(hours * 3600))))
    except ValueError:
        return 12 * 3600


def _session_secret() -> bytes:
    s = _env("STARTER_ADMIN_SESSION_SECRET")
    if not s and admin_auth_mode() != "google":
        s = _configured_admin_key()
    if not s:
        s = _FALLBACK_SECRET
    return s.encode("utf-8")


# --------------------------------------------------------------------------- RS256 Firebase ID token verification
def _fetch_jwks() -> Tuple[Dict[str, Tuple[int, int]], float]:
    with urllib.request.urlopen(JWKS_URL, context=_CTX, timeout=10) as r:
        data = json.loads(r.read().decode("utf-8"))
        cc = r.headers.get("Cache-Control", "")
    ttl = 3600.0
    for part in cc.split(","):
        part = part.strip()
        if part.startswith("max-age="):
            try:
                ttl = float(part.split("=", 1)[1])
            except ValueError:
                pass
    keys = {
        k["kid"]: (int.from_bytes(_b64d(k["n"]), "big"), int.from_bytes(_b64d(k["e"]), "big"))
        for k in data.get("keys", [])
        if k.get("kty") == "RSA" and k.get("kid")
    }
    return keys, time.time() + min(ttl, 6 * 3600)


def _jwk(kid: str) -> Tuple[int, int]:
    with _JWKS_LOCK:
        if kid not in _JWKS["keys"] or time.time() > _JWKS["exp"]:
            _JWKS["keys"], _JWKS["exp"] = _fetch_jwks()
        if kid not in _JWKS["keys"]:
            raise AuthFailed("unknown signing key")
        return _JWKS["keys"][kid]


def rsa_pkcs1_sha256_verify(n: int, e: int, message: bytes, signature: bytes) -> bool:
    k = (n.bit_length() + 7) // 8
    if len(signature) != k:
        return False
    m = pow(int.from_bytes(signature, "big"), e, n).to_bytes(k, "big")
    t = _SHA256_PREFIX + hashlib.sha256(message).digest()
    if k < len(t) + 11:
        return False
    expected = b"\x00\x01" + b"\xff" * (k - len(t) - 3) + b"\x00" + t
    return hmac.compare_digest(m, expected)


def verify_firebase_id_token(
    token: str,
    project: Optional[str] = None,
    now: Optional[float] = None,
    jwk_lookup: Optional[Callable[[str], Tuple[int, int]]] = None,
) -> Dict[str, Any]:
    """Verify a Firebase / Identity Platform Google Sign-In ID token using pure-Python stdlib RS256."""
    project = (project or firebase_project()).strip()
    if not project:
        raise AuthFailed("STARTER_ADMIN_FIREBASE_PROJECT is not set")
    tok = (token or "").strip()
    try:
        h64, p64, s64 = tok.split(".")
        header = json.loads(_b64d(h64))
        claims = json.loads(_b64d(p64))
        sig = _b64d(s64)
    except Exception:
        raise AuthFailed("malformed ID token")
    if header.get("alg") != "RS256":
        raise AuthFailed("unexpected JWT alg")
    n, e = (jwk_lookup or _jwk)(str(header.get("kid", "")))
    if not rsa_pkcs1_sha256_verify(n, e, f"{h64}.{p64}".encode("ascii"), sig):
        raise AuthFailed("invalid ID token signature")
    now_ts = time.time() if now is None else now
    if claims.get("aud") != project or claims.get("iss") != f"https://securetoken.google.com/{project}":
        raise AuthFailed("wrong audience or issuer")
    if float(claims.get("exp", 0)) < now_ts - 30 or float(claims.get("iat", now_ts + 999)) > now_ts + 300:
        raise AuthFailed("ID token expired")
    if not claims.get("sub"):
        raise AuthFailed("missing subject")
    if (claims.get("firebase") or {}).get("sign_in_provider") != "google.com":
        raise AuthFailed("Google sign-in provider required")
    email = str(claims.get("email") or "").strip().lower()
    if not email or not claims.get("email_verified"):
        raise AuthFailed("verified Google email required")
    return {
        "email": email,
        "name": str(claims.get("name") or "")[:80],
        "uid": str(claims.get("sub")),
        "picture": str(claims.get("picture") or "")[:300],
    }


# --------------------------------------------------------------------------- Session & Cookie helpers
def _sign_session(
    sub: str,
    method: str,
    ttl_s: Optional[int] = None,
    *,
    name: str = "",
    picture: str = "",
) -> Tuple[str, int]:
    ttl = max(60, int(ttl_s if ttl_s is not None else session_ttl_sec()))
    exp = int(time.time()) + ttl
    payload: Dict[str, Any] = {
        "sub": sub,
        "method": method,
        "exp": exp,
        "sid": secrets.token_hex(6),
    }
    if name:
        payload["name"] = str(name)[:80]
    if picture:
        payload["picture"] = str(picture)[:300]
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True, ensure_ascii=False).encode("utf-8")
    b64 = _b64e(raw)
    sig = hmac.new(_session_secret(), b64.encode("ascii"), hashlib.sha256).hexdigest()
    return f"{b64}.{sig}", exp


def _verify_session(token: str) -> Optional[Dict[str, Any]]:
    tok = (token or "").strip()
    if "." not in tok:
        return None
    b64, sig = tok.rsplit(".", 1)
    expected = hmac.new(_session_secret(), b64.encode("ascii"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expected):
        return None
    try:
        payload = json.loads(_b64d(b64).decode("utf-8"))
    except Exception:
        return None
    if not isinstance(payload, dict) or int(payload.get("exp") or 0) <= int(time.time()):
        return None
    return payload


def cookie_from_headers(headers: Optional[Dict[str, str]]) -> str:
    if not headers:
        return ""
    raw = ""
    for k, v in headers.items():
        if str(k).lower() == "cookie":
            raw = str(v or "")
            break
    for part in raw.split(";"):
        ck, _, val = part.strip().partition("=")
        if ck.strip() == COOKIE_NAME:
            return val.strip()
    return ""


def _is_secure_request(headers: Optional[Dict[str, str]]) -> bool:
    h = {str(k).lower(): str(v or "").strip().lower() for k, v in (headers or {}).items()}
    return h.get("x-forwarded-proto") == "https" or bool(os.environ.get("K_SERVICE"))


def make_set_cookie_header(session_token: str, max_age: int, headers: Optional[Dict[str, str]] = None) -> str:
    secure = "; Secure" if _is_secure_request(headers) else ""
    return f"{COOKIE_NAME}={session_token}; Max-Age={max(0, int(max_age))}; Path=/; HttpOnly; SameSite=Lax{secure}"


def make_clear_cookie_header(headers: Optional[Dict[str, str]] = None) -> str:
    secure = "; Secure" if _is_secure_request(headers) else ""
    return f"{COOKIE_NAME}=; Max-Age=0; Path=/; HttpOnly; SameSite=Lax{secure}"


def maybe_renew_cookie(info: Dict[str, Any], headers: Optional[Dict[str, str]] = None) -> Optional[str]:
    """Sliding session renewal: re-issue HttpOnly cookie once less than 50% of its TTL remains."""
    if not info.get("via_cookie"):
        return None
    exp = int(info.get("expires_at") or 0)
    ttl = session_ttl_sec()
    if exp and (exp - time.time()) < (ttl * 0.5):
        base_method = str(info.get("auth_method") or "google_signin")
        if base_method.startswith("session:"):
            base_method = base_method[8:]
        tok, _ = _sign_session(
            str(info.get("principal") or ""),
            base_method,
            ttl_s=ttl,
            name=str(info.get("name") or ""),
            picture=str(info.get("picture") or ""),
        )
        return make_set_cookie_header(tok, ttl, headers)
    return None


def _verify_google_token(token: str, timeout_s: float = 4.0) -> Tuple[bool, str]:
    tok = (token or "").strip()
    if tok.lower().startswith("bearer "):
        tok = tok[7:].strip()
    if not tok:
        return False, ""
    body = urllib.parse.urlencode({"access_token": tok}).encode("ascii")
    req = urllib.request.Request(
        "https://oauth2.googleapis.com/tokeninfo",
        data=body,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with urllib.request.urlopen(req, context=_CTX, timeout=timeout_s) as resp:
            info = json.loads(resp.read().decode("utf-8") or "{}")
        email = str(info.get("email") or "").strip().lower()
        return bool(email), email
    except Exception:
        return False, ""


def _email_allowed(email: str, allowlist: List[str]) -> bool:
    if not email or not allowlist:
        return False
    e = email.lower().strip()
    return any(e == a or (a.startswith("@") and e.endswith(a)) for a in allowlist)


def admin_config_status(headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    mode = admin_auth_mode()
    emails = _configured_admin_emails()
    gcfg = firebase_public_config()
    modes: List[str] = []
    if mode == "google":
        configured = bool(gcfg["projectId"] and emails)
        if gcfg["enabled"]:
            modes.append("google_signin")
        if emails:
            modes.append("oauth_allowlist")
    else:
        has_key = bool(_configured_admin_key())
        if has_key:
            modes.append("admin_key")
        if emails:
            modes.append("oauth_allowlist")
        configured = bool(modes)

    authenticated = False
    user_info: Optional[Dict[str, Any]] = None
    if headers and configured:
        code, info = authorize_admin({}, headers)
        if code == 200:
            authenticated = True
            user_info = {
                "email": info.get("principal"),
                "name": info.get("name") or "",
                "picture": info.get("picture") or "",
                "auth_method": info.get("auth_method"),
                "expires_at": info.get("expires_at") or 0,
            }

    return {
        "status": "OK",
        "configured": configured,
        "auth_mode": mode,
        "auth_modes": modes,
        "google_auth": gcfg,
        "authenticated": authenticated,
        "user": user_info,
        "allowlist_count": len(emails),
        "table_fq": metering_table_fq(),
        "bq_project": metering_bq_project(),
        "core_mcp_portal_url": f"{core_mcp_base_url()}/portal",
        "session_ttl_s": session_ttl_sec(),
    }


def authorize_admin(
    data: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    *,
    token_verifier: Optional[Callable[[str], Tuple[bool, str]]] = None,
    id_token_verifier: Optional[Callable[[str], Dict[str, Any]]] = None,
) -> Tuple[int, Dict[str, Any]]:
    """Verify admin authorization (fail-closed). Returns (200, admin_info) or (401|403|503, error_payload)."""
    mode = admin_auth_mode()
    emails = _configured_admin_emails()
    has_key = bool(_configured_admin_key())

    if mode == "google":
        if not firebase_project() or not emails:
            return 503, {
                "status": "ADMIN_NOT_CONFIGURED",
                "message": "Google admin auth requires STARTER_ADMIN_FIREBASE_PROJECT and STARTER_ADMIN_EMAILS.",
            }
    elif not has_key and not emails:
        return 503, {
            "status": "ADMIN_NOT_CONFIGURED",
            "message": "Admin guard is disabled because neither STARTER_ADMIN_KEY nor STARTER_ADMIN_EMAILS is configured.",
        }

    d = data or {}
    h = {str(k).lower(): str(v or "").strip() for k, v in (headers or {}).items()}

    # 1. Signed session (HttpOnly cookie preferred, or explicit X-AOS-Admin-Session header / body)
    cookie_val = cookie_from_headers(headers)
    sess = str(d.get("admin_session") or h.get("x-aos-admin-session") or cookie_val or "").strip()
    via_cookie = bool(cookie_val and sess == cookie_val)
    if sess:
        claims = _verify_session(sess)
        if claims:
            sub = str(claims.get("sub") or "").strip()
            if mode == "google" and not _email_allowed(sub, emails):
                return 403, {
                    "status": "FORBIDDEN",
                    "code": "ADMIN_FORBIDDEN",
                    "message": f"Account '{sub}' is no longer in STARTER_ADMIN_EMAILS.",
                }
            return 200, {
                "authorized": True,
                "principal": sub or "admin",
                "name": str(claims.get("name") or ""),
                "picture": str(claims.get("picture") or ""),
                "auth_method": f"session:{claims.get('method', 'google_signin')}",
                "expires_at": int(claims.get("exp") or 0),
                "via_cookie": via_cookie,
            }
        # Invalid/expired cookie falls through ONLY if a fresh credential is supplied in the same request
        has_fresh = bool(d.get("id_token") or d.get("idToken") or d.get("access_token") or d.get("admin_key"))
        if not has_fresh:
            return 401, {"status": "UNAUTHORIZED", "code": "SESSION_EXPIRED", "message": "Admin session is invalid or expired."}

    # 2. Firebase / Identity Platform Google Sign-In ID token
    id_tok = str(d.get("id_token") or d.get("idToken") or h.get("x-aos-id-token") or "").strip()
    if id_tok:
        try:
            verify_id = id_token_verifier or verify_firebase_id_token
            user = verify_id(id_tok)
        except AuthFailed as e:
            return 401, {"status": "UNAUTHORIZED", "code": "INVALID_ID_TOKEN", "message": f"Google sign-in failed: {e}"}
        email = str(user.get("email") or "").strip().lower()
        if not emails or not _email_allowed(email, emails):
            return 403, {
                "status": "FORBIDDEN",
                "code": "ADMIN_FORBIDDEN",
                "email": email,
                "message": f"Google account '{email}' is not authorized for Starter Admin access.",
            }
        return 200, {
            "authorized": True,
            "principal": email,
            "name": str(user.get("name") or ""),
            "picture": str(user.get("picture") or ""),
            "auth_method": "google_signin",
        }

    # 3. Legacy Admin Key (strictly disabled in google mode!)
    key_input = str(d.get("admin_key") or h.get("x-aos-admin-key") or "").strip()
    if key_input:
        if mode == "google":
            return 403, {
                "status": "FORBIDDEN",
                "code": "ADMIN_KEY_DISABLED",
                "message": "Static admin key authentication is disabled. Please sign in with an authorized Google account.",
            }
        expected_key = _configured_admin_key()
        if expected_key and hmac.compare_digest(key_input, expected_key):
            return 200, {"authorized": True, "principal": "admin-key", "auth_method": "admin_key"}
        return 403, {"status": "FORBIDDEN", "code": "INVALID_ADMIN_KEY", "message": "Invalid admin key."}

    # 4. Google OAuth2 Access Token against STARTER_ADMIN_EMAILS (CLI/automated ops)
    oauth_tok = str(
        d.get("access_token")
        or h.get("x-aos-access-token")
        or ((d.get("identity") or {}).get("token") if isinstance(d.get("identity"), dict) else "")
        or ""
    ).strip()
    if not oauth_tok:
        auth_h = h.get("authorization", "")
        if auth_h.lower().startswith("bearer "):
            cand = auth_h[7:].strip()
            if cand.startswith("ya" + "29.") or "." not in cand:
                oauth_tok = cand
    if oauth_tok:
        verify_fn = token_verifier or _verify_google_token
        valid, email = verify_fn(oauth_tok)
        if not valid:
            return 401, {"status": "UNAUTHORIZED", "code": "INVALID_TOKEN", "message": "Google OAuth token is invalid or expired."}
        if not emails:
            return 403, {"status": "FORBIDDEN", "code": "OAUTH_NOT_ENABLED", "message": "OAuth admin allowlist is not enabled."}
        if not _email_allowed(email, emails):
            return 403, {
                "status": "FORBIDDEN",
                "code": "ADMIN_FORBIDDEN",
                "email": email,
                "message": f"Account '{email}' is not in STARTER_ADMIN_EMAILS.",
            }
        return 200, {"authorized": True, "principal": email, "auth_method": "oauth_allowlist"}

    return 401, {
        "status": "UNAUTHORIZED",
        "code": "AUTH_REQUIRED",
        "message": "Sign in with an authorized Google account to access Starter Admin.",
    }


def handle_auth(
    data: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    *,
    token_verifier: Optional[Callable[[str], Tuple[bool, str]]] = None,
    id_token_verifier: Optional[Callable[[str], Dict[str, Any]]] = None,
) -> Tuple[int, Dict[str, Any], Dict[str, str]]:
    """Authenticate admin and return (http_code, json_payload, extra_headers including Set-Cookie)."""
    code, info = authorize_admin(
        data, headers, token_verifier=token_verifier, id_token_verifier=id_token_verifier
    )
    if code != 200:
        return code, info, {"Cache-Control": "no-store"}
    ttl = session_ttl_sec()
    base_method = str(info.get("auth_method") or "google_signin")
    if base_method.startswith("session:"):
        base_method = base_method[8:]
    sess_tok, exp = _sign_session(
        info["principal"],
        base_method,
        ttl_s=ttl,
        name=str(info.get("name") or ""),
        picture=str(info.get("picture") or ""),
    )
    extra = {
        "Cache-Control": "no-store",
        "Set-Cookie": make_set_cookie_header(sess_tok, ttl, headers),
    }
    return 200, {
        "status": "OK",
        "authorized": True,
        "principal": info["principal"],
        "user": {
            "email": info["principal"],
            "name": info.get("name") or "",
            "picture": info.get("picture") or "",
            "auth_method": base_method,
            "expires_at": exp,
        },
        "auth_method": base_method,
        "admin_session": sess_tok,
        "expires_at": exp,
        "expires_in": max(0, exp - int(time.time())),
    }, extra


def handle_logout(headers: Optional[Dict[str, str]] = None) -> Tuple[int, Dict[str, Any], Dict[str, str]]:
    return 200, {"status": "OK", "logged_out": True}, {
        "Cache-Control": "no-store",
        "Set-Cookie": make_clear_cookie_header(headers),
    }


def admin_identity_summary(ainfo: Dict[str, Any]) -> Dict[str, Any]:
    """Authenticated admin context returned inside admin API responses (safe because caller is verified)."""
    return {
        "principal": ainfo.get("principal"),
        "name": ainfo.get("name") or "",
        "picture": ainfo.get("picture") or "",
        "auth_method": ainfo.get("auth_method"),
        "auth_mode": admin_auth_mode(),
        "firebase_project": firebase_project(),
        "allowed_emails": _configured_admin_emails(),
        "session_ttl_s": session_ttl_sec(),
    }


# --------------------------------------------------------------------------- BigQuery REST direct query
def _bq_rest_query(
    sql: str,
    params: List[Dict[str, Any]],
    *,
    project: str,
    location: str = "asia-northeast3",
    timeout_s: float = 25.0,
) -> Dict[str, Any]:
    tok = get_gcp_token()
    url = f"https://bigquery.googleapis.com/bigquery/v2/projects/{project}/queries"
    body: Dict[str, Any] = {
        "query": sql,
        "useLegacySql": False,
        "parameterMode": "NAMED",
        "queryParameters": params,
        "location": location,
        "timeoutMs": int(timeout_s * 1000),
        "labels": {"datacloud": "jetski", "component": "starter-admin-metering"},
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        method="POST",
        headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, context=_CTX, timeout=timeout_s + 5.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")[:600]
        return {"status": "ERROR", "http_code": e.code, "error": f"BigQuery HTTP {e.code}: {raw}"}
    except Exception as e:
        return {"status": "ERROR", "http_code": 0, "error": f"BigQuery request failed: {repr(e)[:300]}"}

    fields = [f["name"] for f in ((data.get("schema") or {}).get("fields") or [])]
    rows_out: List[Dict[str, Any]] = []
    for row in data.get("rows") or []:
        vals = [c.get("v") for c in (row.get("f") or [])]
        rows_out.append(dict(zip(fields, vals)))
    return {
        "status": "SUCCESS",
        "rows": rows_out,
        "job_id": ((data.get("jobReference") or {}).get("jobId") or ""),
        "bytes_processed": int(data.get("totalBytesProcessed") or 0),
        "cache_hit": bool(data.get("cacheHit", False)),
    }


def _http_get_json(url: str, timeout_s: float = 6.0) -> Tuple[int, Any]:
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, context=_CTX, timeout=timeout_s) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as e:
        try:
            body = json.loads(e.read().decode("utf-8", "replace") or "{}")
        except ValueError:
            body = {"message": f"HTTP {e.code}"}
        return e.code, body
    except Exception as e:
        return 0, {"message": f"{type(e).__name__}: {str(e)[:240]}"}


def _fetch_core_mcp_meta(force: bool = False) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    now = time.time()
    if not force and (now - float(_MCP_META_CACHE.get("ts") or 0)) < 30.0 and _MCP_META_CACHE.get("health") is not None:
        return _MCP_META_CACHE.get("health"), _MCP_META_CACHE.get("policy")
    base = core_mcp_base_url()
    health_obj, policy_obj = None, None
    c_h, o_h = _http_get_json(f"{base}/health", timeout_s=4.0)
    if c_h == 200 and isinstance(o_h, dict):
        health_obj = o_h
    c_p, o_p = _http_get_json(f"{base}/portal/api/metering-policy", timeout_s=4.0)
    if c_p == 200 and isinstance(o_p, dict):
        policy_obj = o_p
    _MCP_META_CACHE.update({"ts": now, "health": health_obj, "policy": policy_obj})
    return health_obj, policy_obj


def fetch_core_mcp_catalog(
    *,
    force: bool = False,
    http_get: Optional[Callable[[str, float], Tuple[int, Any]]] = None,
) -> Tuple[int, Dict[str, Any]]:
    """Proxy Core MCP `/portal/api/catalog` (57 tools, categories, interactive flow) for the unified Admin UI."""
    now = time.time()
    base = core_mcp_base_url()
    if not force and (now - float(_MCP_CATALOG_CACHE.get("ts") or 0)) < 60.0 and _MCP_CATALOG_CACHE.get("catalog"):
        health_obj, policy_obj = _fetch_core_mcp_meta(False) if not http_get else (None, None)
        return 200, {
            "status": "OK",
            "cached": True,
            "portal_url": f"{base}/portal",
            "mcp_url": f"{base}/mcp",
            "catalog": _MCP_CATALOG_CACHE["catalog"],
            "core_mcp_health": health_obj,
            "metering_policy": policy_obj,
        }
    getter = http_get or _http_get_json
    code, cat = getter(f"{base}/portal/api/catalog", 8.0)
    if code != 200 or not isinstance(cat, dict) or cat.get("status") != "SUCCESS":
        return 502, {
            "status": "ERROR",
            "message": f"Failed to fetch Core MCP portal catalog (HTTP {code})",
            "detail": cat if isinstance(cat, dict) else {},
        }
    if not http_get:
        _MCP_CATALOG_CACHE.update({"ts": now, "catalog": cat})
    health_obj, policy_obj = _fetch_core_mcp_meta(force) if not http_get else (None, None)
    return 200, {
        "status": "OK",
        "cached": False,
        "portal_url": f"{base}/portal",
        "mcp_url": f"{base}/mcp",
        "catalog": cat,
        "core_mcp_health": health_obj,
        "metering_policy": policy_obj,
    }


def fetch_core_mcp_live_usage(
    data: Optional[Dict[str, Any]] = None,
    *,
    http_get: Optional[Callable[[str, float], Tuple[int, Any]]] = None,
) -> Tuple[int, Dict[str, Any]]:
    """Proxy Core MCP `/portal/api/usage?source=live` (in-memory Cloud Run instance buffer & hourly histogram)."""
    d = data or {}
    try:
        hours = max(1.0, min(720.0, float(d.get("hours") or 24)))
    except (TypeError, ValueError):
        hours = 24.0
    try:
        tz_offset = max(-720, min(840, int(d.get("tz_offset") if d.get("tz_offset") is not None else 540)))
    except (TypeError, ValueError):
        tz_offset = 540
    base = core_mcp_base_url()
    qs = urllib.parse.urlencode({"source": "live", "hours": hours, "tz_offset": tz_offset})
    getter = http_get or _http_get_json
    code, usage = getter(f"{base}/portal/api/usage?{qs}", 6.0)
    if code != 200 or not isinstance(usage, dict) or usage.get("status") != "SUCCESS":
        return 502, {
            "status": "ERROR",
            "message": f"Failed to fetch Core MCP live usage (HTTP {code})",
            "detail": usage if isinstance(usage, dict) else {},
        }
    return 200, {"status": "OK", "usage": usage}


def _clean_filters(data: Dict[str, Any]) -> Dict[str, Any]:
    try:
        days = max(1, min(90, int(data.get("days") or 14)))
    except (TypeError, ValueError):
        days = 14
    ptype = str(data.get("principal_type") or "").strip().lower()
    if ptype not in _ALLOWED_TYPES:
        ptype = ""
    st = str(data.get("status") or "").strip().lower()
    if st not in _ALLOWED_STATUS:
        st = ""
    phash = str(data.get("principal_hash") or "").strip().lower()
    if not _HASH_RE.match(phash):
        phash = ""
    tool = str(data.get("tool_name") or "").strip()
    if not _TOOL_RE.match(tool):
        tool = ""
    try:
        recent_limit = max(10, min(200, int(data.get("recent_limit") or 80)))
    except (TypeError, ValueError):
        recent_limit = 80
    return {
        "days": days,
        "principal_type": ptype,
        "status": st,
        "principal_hash": phash,
        "tool_name": tool,
        "recent_limit": recent_limit,
    }


def _bq_params(f: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [
        {"name": "days", "parameterType": {"type": "INT64"}, "parameterValue": {"value": str(f["days"])}},
        {"name": "principal_type", "parameterType": {"type": "STRING"}, "parameterValue": {"value": f["principal_type"]}},
        {"name": "status", "parameterType": {"type": "STRING"}, "parameterValue": {"value": f["status"]}},
        {"name": "principal_hash", "parameterType": {"type": "STRING"}, "parameterValue": {"value": f["principal_hash"]}},
        {"name": "tool_name", "parameterType": {"type": "STRING"}, "parameterValue": {"value": f["tool_name"]}},
        {"name": "recent_limit", "parameterType": {"type": "INT64"}, "parameterValue": {"value": str(f["recent_limit"])}},
    ]


def build_overview_sql(table_fq: str) -> str:
    return f"""
WITH base AS (
  SELECT *
  FROM `{table_fq}`
  WHERE event_ts >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL @days DAY)
    AND (@principal_type = '' OR principal_type = @principal_type)
    AND (@status = '' OR status = @status)
    AND (@principal_hash = '' OR principal_hash = @principal_hash)
    AND (@tool_name = '' OR tool_name = @tool_name)
),
summary_cte AS (
  SELECT
    COUNT(*) AS calls,
    COUNTIF(status != 'ok') AS errors,
    ROUND(COALESCE(SAFE_DIVIDE(COUNTIF(status != 'ok'), COUNT(*)), 0.0), 4) AS error_rate,
    COUNT(DISTINCT principal_hash) AS accounts,
    COUNT(DISTINCT tool_name) AS tools,
    COALESCE(SUM(gemini_calls), 0) AS gemini_calls,
    COALESCE(SUM(tokens_in), 0) AS tokens_in,
    COALESCE(SUM(tokens_out), 0) AS tokens_out,
    COALESCE(SUM(tokens_thought), 0) AS tokens_thought,
    COALESCE(SUM(tokens_total), 0) AS tokens_total,
    COALESCE(SUM(request_bytes), 0) AS request_bytes,
    COALESCE(SUM(response_bytes), 0) AS response_bytes,
    COALESCE(SUM(bq_bytes_processed), 0) AS bq_bytes_processed,
    ROUND(COALESCE(SUM(metering_units), 0.0), 4) AS metering_units,
    IF(COUNT(*) > 0, CAST(APPROX_QUANTILES(duration_ms, 100)[OFFSET(50)] AS INT64), 0) AS p50_ms,
    IF(COUNT(*) > 0, CAST(APPROX_QUANTILES(duration_ms, 100)[OFFSET(95)] AS INT64), 0) AS p95_ms
  FROM base
),
by_day_cte AS (
  SELECT
    CAST(event_date_kst AS STRING) AS day,
    COUNT(*) AS calls,
    COUNTIF(status != 'ok') AS errors,
    COUNT(DISTINCT principal_hash) AS accounts,
    COALESCE(SUM(gemini_calls), 0) AS gemini_calls,
    COALESCE(SUM(tokens_total), 0) AS tokens_total,
    COALESCE(SUM(request_bytes + response_bytes), 0) AS payload_bytes,
    COALESCE(SUM(bq_bytes_processed), 0) AS bq_bytes_processed,
    ROUND(COALESCE(SUM(metering_units), 0.0), 4) AS metering_units,
    IF(COUNT(*) > 0, CAST(APPROX_QUANTILES(duration_ms, 100)[OFFSET(95)] AS INT64), 0) AS p95_ms
  FROM base
  GROUP BY day
  ORDER BY day ASC
),
by_account_cte AS (
  SELECT
    principal_hash,
    ANY_VALUE(principal_id) AS principal_id,
    ANY_VALUE(principal_type) AS principal_type,
    ANY_VALUE(principal_domain) AS principal_domain,
    ANY_VALUE(auth_method) AS auth_method,
    LOGICAL_OR(auth_verified) AS auth_verified,
    COUNT(*) AS calls,
    COUNTIF(status != 'ok') AS errors,
    ROUND(COALESCE(SAFE_DIVIDE(COUNTIF(status != 'ok'), COUNT(*)), 0.0), 4) AS error_rate,
    COUNT(DISTINCT tool_name) AS tools_used,
    COALESCE(SUM(gemini_calls), 0) AS gemini_calls,
    COALESCE(SUM(tokens_in), 0) AS tokens_in,
    COALESCE(SUM(tokens_out), 0) AS tokens_out,
    COALESCE(SUM(tokens_thought), 0) AS tokens_thought,
    COALESCE(SUM(tokens_total), 0) AS tokens_total,
    COALESCE(SUM(request_bytes + response_bytes), 0) AS payload_bytes,
    COALESCE(SUM(bq_bytes_processed), 0) AS bq_bytes_processed,
    ROUND(COALESCE(SUM(metering_units), 0.0), 4) AS metering_units,
    IF(COUNT(*) > 0, CAST(APPROX_QUANTILES(duration_ms, 100)[OFFSET(50)] AS INT64), 0) AS p50_ms,
    IF(COUNT(*) > 0, CAST(APPROX_QUANTILES(duration_ms, 100)[OFFSET(95)] AS INT64), 0) AS p95_ms,
    FORMAT_TIMESTAMP('%Y-%m-%d %H:%M:%S', MAX(event_ts), 'Asia/Seoul') AS last_seen_kst
  FROM base
  GROUP BY principal_hash
  ORDER BY calls DESC, metering_units DESC
  LIMIT 100
),
by_tool_cte AS (
  SELECT
    tool_name,
    ANY_VALUE(tool_category) AS tool_category,
    COUNT(*) AS calls,
    COUNTIF(status != 'ok') AS errors,
    ROUND(COALESCE(SAFE_DIVIDE(COUNTIF(status != 'ok'), COUNT(*)), 0.0), 4) AS error_rate,
    COUNT(DISTINCT principal_hash) AS accounts,
    COALESCE(SUM(gemini_calls), 0) AS gemini_calls,
    COALESCE(SUM(tokens_total), 0) AS tokens_total,
    COALESCE(SUM(request_bytes + response_bytes), 0) AS payload_bytes,
    COALESCE(SUM(bq_bytes_processed), 0) AS bq_bytes_processed,
    ROUND(COALESCE(SUM(metering_units), 0.0), 4) AS metering_units,
    IF(COUNT(*) > 0, CAST(APPROX_QUANTILES(duration_ms, 100)[OFFSET(50)] AS INT64), 0) AS p50_ms,
    IF(COUNT(*) > 0, CAST(APPROX_QUANTILES(duration_ms, 100)[OFFSET(95)] AS INT64), 0) AS p95_ms,
    FORMAT_TIMESTAMP('%Y-%m-%d %H:%M:%S', MAX(event_ts), 'Asia/Seoul') AS last_seen_kst
  FROM base
  GROUP BY tool_name
  ORDER BY calls DESC, metering_units DESC
  LIMIT 100
),
by_type_cte AS (
  SELECT
    principal_type,
    COUNT(DISTINCT principal_hash) AS accounts,
    COUNT(*) AS calls,
    COUNTIF(status != 'ok') AS errors,
    COALESCE(SUM(gemini_calls), 0) AS gemini_calls,
    COALESCE(SUM(tokens_total), 0) AS tokens_total,
    ROUND(COALESCE(SUM(metering_units), 0.0), 4) AS metering_units
  FROM base
  GROUP BY principal_type
  ORDER BY calls DESC
),
by_client_cte AS (
  SELECT
    IF(client_name = '' OR client_name IS NULL, 'unknown', client_name) AS client_name,
    COUNT(*) AS calls,
    COUNT(DISTINCT principal_hash) AS accounts,
    ROUND(COALESCE(SUM(metering_units), 0.0), 4) AS metering_units
  FROM base
  GROUP BY client_name
  ORDER BY calls DESC
  LIMIT 25
),
recent_cte AS (
  SELECT
    event_id,
    FORMAT_TIMESTAMP('%Y-%m-%d %H:%M:%S', event_ts, 'Asia/Seoul') AS event_ts_kst,
    principal_id,
    principal_hash,
    principal_type,
    auth_method,
    auth_verified,
    tool_name,
    tool_category,
    client_name,
    target_project,
    status,
    error_code,
    duration_ms,
    request_bytes,
    response_bytes,
    gemini_calls,
    gemini_model,
    tokens_in,
    tokens_out,
    tokens_thought,
    tokens_total,
    bq_bytes_processed,
    metering_units
  FROM base
  ORDER BY event_ts DESC
  LIMIT @recent_limit
)
SELECT
  (SELECT TO_JSON_STRING(s) FROM summary_cte s) AS summary_json,
  COALESCE((SELECT TO_JSON_STRING(ARRAY_AGG(d)) FROM by_day_cte d), '[]') AS by_day_json,
  COALESCE((SELECT TO_JSON_STRING(ARRAY_AGG(a)) FROM by_account_cte a), '[]') AS by_account_json,
  COALESCE((SELECT TO_JSON_STRING(ARRAY_AGG(t)) FROM by_tool_cte t), '[]') AS by_tool_json,
  COALESCE((SELECT TO_JSON_STRING(ARRAY_AGG(p)) FROM by_type_cte p), '[]') AS by_type_json,
  COALESCE((SELECT TO_JSON_STRING(ARRAY_AGG(c)) FROM by_client_cte c), '[]') AS by_client_json,
  COALESCE((SELECT TO_JSON_STRING(ARRAY_AGG(r)) FROM recent_cte r), '[]') AS recent_json
""".strip()


def _parse_json_col(raw: Any, default: Any) -> Any:
    if raw is None or raw == "":
        return default
    if isinstance(raw, (dict, list)):
        return raw
    try:
        val = json.loads(str(raw))
        return val if val is not None else default
    except Exception:
        return default


def query_metering_overview(
    data: Optional[Dict[str, Any]] = None,
    *,
    bq_executor: Optional[Callable[[str, List[Dict[str, Any]], str], Dict[str, Any]]] = None,
    meta_fetcher: Optional[Callable[[bool], Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]]] = None,
) -> Tuple[int, Dict[str, Any]]:
    f = _clean_filters(data or {})
    table_fq = metering_table_fq()
    project = metering_bq_project()
    sql = build_overview_sql(table_fq)
    params = _bq_params(f)
    res = bq_executor(sql, params, project) if bq_executor else _bq_rest_query(sql, params, project=project)
    if res.get("status") != "SUCCESS":
        return 502, {
            "status": "ERROR",
            "message": res.get("error") or "Failed to query BigQuery metering table",
            "table_fq": table_fq,
        }
    row = (res.get("rows") or [{}])[0]
    summary = _parse_json_col(row.get("summary_json"), {
        "calls": 0, "errors": 0, "error_rate": 0.0, "accounts": 0, "tools": 0,
        "gemini_calls": 0, "tokens_in": 0, "tokens_out": 0, "tokens_thought": 0, "tokens_total": 0,
        "request_bytes": 0, "response_bytes": 0, "bq_bytes_processed": 0, "metering_units": 0.0,
        "p50_ms": 0, "p95_ms": 0,
    })
    health_obj, policy_obj = (meta_fetcher or _fetch_core_mcp_meta)(bool((data or {}).get("force_refresh")))
    return 200, {
        "status": "OK",
        "generated_at_kst": dt.datetime.now(tz=_KST).strftime("%Y-%m-%d %H:%M:%S KST"),
        "table_fq": table_fq,
        "bq_job_id": res.get("job_id") or "",
        "bq_bytes_scanned": int(res.get("bytes_processed") or 0),
        "filters": f,
        "summary": summary,
        "by_day": _parse_json_col(row.get("by_day_json"), []),
        "by_account": _parse_json_col(row.get("by_account_json"), []),
        "by_tool": _parse_json_col(row.get("by_tool_json"), []),
        "by_type": _parse_json_col(row.get("by_type_json"), []),
        "by_client": _parse_json_col(row.get("by_client_json"), []),
        "recent": _parse_json_col(row.get("recent_json"), []),
        "core_mcp_health": health_obj,
        "metering_policy": policy_obj,
        "portal_url": f"{core_mcp_base_url()}/portal",
    }


def export_metering_bytes(
    data: Optional[Dict[str, Any]] = None,
    *,
    bq_executor: Optional[Callable[[str, List[Dict[str, Any]], str], Dict[str, Any]]] = None,
) -> Tuple[int, bytes, str, str]:
    """Export metering overview/events as CSV or JSON bytes: (http_code, body, content_type, filename)."""
    d = dict(data or {})
    fmt = str(d.get("format") or "csv").strip().lower()
    scope = str(d.get("scope") or "recent").strip().lower()
    d.setdefault("recent_limit", 200)
    code, payload = query_metering_overview(d, bq_executor=bq_executor, meta_fetcher=lambda _f: (None, None))
    if code != 200:
        return code, json.dumps(payload, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8", "error.json"
    stamp = dt.datetime.now(tz=_KST).strftime("%Y%m%d_%H%M")
    if fmt == "json":
        return 200, json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8"), "application/json; charset=utf-8", f"core_mcp_metering_{stamp}.json"
    rows = payload.get("by_account" if scope == "accounts" else "by_tool" if scope == "tools" else "by_day" if scope == "daily" else "recent") or []
    buf = io.StringIO()
    if rows and isinstance(rows[0], dict):
        cols = list(rows[0].keys())
        writer = csv.DictWriter(buf, fieldnames=cols)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)
    else:
        buf.write("event_id,event_ts_kst,principal_id,principal_type,tool_name,status,duration_ms,metering_units\n")
    # UTF-8 BOM for Excel Korean compatibility
    return 200, ("\ufeff" + buf.getvalue()).encode("utf-8"), "text/csv; charset=utf-8", f"core_mcp_metering_{scope}_{stamp}.csv"
