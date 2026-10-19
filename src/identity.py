# Copyright (c) 2026 Sean Jung (seanjung@google.com). All Rights Reserved.
# Non-Commercial Use Only: Methodology & Docs under CC BY-NC-ND 4.0; Source Code under PolyForm Noncommercial License 1.0.0.
# Commercial use, paid consulting/SI/PoC delivery, or production deployment requires prior written permission from seanjung@google.com.

# -*- coding: utf-8 -*-
"""Request identity (GOAL-233): whose credentials run this request.

  runtime      the starter server's own identity (Cloud Run SA / local gcloud). Writes only to STARTER_WRITE_PROJECTS.
  token        an OAuth access token the user pasted (`gcloud auth print-access-token`, optionally
               `--impersonate-service-account=SA`). Never stored or logged; used for this request only.
  impersonate  a service-account e-mail: the runtime identity mints a short-lived token with IAM Credentials
               `generateAccessToken` (the user grants the runtime SA roles/iam.serviceAccountTokenCreator on it).
               Allowed only for SAs matching STARTER_IMPERSONATE_ALLOW (fnmatch patterns, comma separated).

The resolved token is bound to the current thread (`bind`), so every Core MCP call (X-AOS-Access-Token) and every
Vertex AI call made while handling the request uses it. Worker threads must be wrapped with `carry()`.
"""
from __future__ import annotations

import fnmatch
import json
import os
import re
import ssl
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from contextlib import contextmanager
from typing import Any, Callable, Dict, Iterator, Optional

_CAFILE = os.environ.get("SSL_CERT_FILE") or ("/etc/ssl/cert.pem" if os.path.exists("/etc/ssl/cert.pem") else None)
_CTX = ssl.create_default_context(cafile=_CAFILE)
_LOCAL = threading.local()
_SA_RE = re.compile(r"^[a-z][a-z0-9-]{4,29}@[a-z][a-z0-9-]{4,28}[a-z0-9]\.iam\.gserviceaccount\.com$")
_TOKEN_RE = re.compile(r"^ya29\.[A-Za-z0-9._\-]{20,4000}$")
_CACHE: Dict[str, Any] = {}
_CACHE_LOCK = threading.Lock()
MODES = ("runtime", "token", "impersonate")


class IdentityError(ValueError):
    def __init__(self, code: str, ko: str, en: str):
        super().__init__(en)
        self.code, self.ko, self.en = code, ko, en

    def to_dict(self, lang: str = "ko") -> Dict[str, Any]:
        return {"status": "IDENTITY_ERROR", "code": self.code, "message": self.en if lang == "en" else self.ko}


def current_token() -> Optional[str]:
    return getattr(_LOCAL, "token", None)


def current() -> Dict[str, Any]:
    return dict(getattr(_LOCAL, "info", None) or {"mode": "runtime"})


@contextmanager
def bind(token: Optional[str], info: Optional[Dict[str, Any]] = None) -> Iterator[None]:
    prev_t, prev_i = getattr(_LOCAL, "token", None), getattr(_LOCAL, "info", None)
    _LOCAL.token, _LOCAL.info = token, info
    try:
        yield
    finally:
        _LOCAL.token, _LOCAL.info = prev_t, prev_i


def carry(fn: Callable[..., Any]) -> Callable[..., Any]:
    """Wraps a callable so that it runs with the caller thread's identity (for ThreadPoolExecutor workers)."""
    tok, info = current_token(), getattr(_LOCAL, "info", None)

    def run(*a: Any, **kw: Any) -> Any:
        with bind(tok, info):
            return fn(*a, **kw)
    return run


def impersonate_allowed(sa: str) -> bool:
    pats = [p.strip() for p in os.environ.get("STARTER_IMPERSONATE_ALLOW", "").split(",") if p.strip()]
    return any(fnmatch.fnmatch(sa, p) for p in pats)


def tokeninfo(token: str) -> Dict[str, Any]:
    url = "https://oauth2.googleapis.com/tokeninfo?access_token=" + urllib.parse.quote(token, safe="")
    try:
        with urllib.request.urlopen(url, context=_CTX, timeout=10) as r:
            d = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise IdentityError("TOKEN_INVALID", f"토큰이 유효하지 않거나 만료되었습니다 (tokeninfo HTTP {e.code}). 새로 발급해 붙여 넣으세요.",
                            f"The token is invalid or expired (tokeninfo HTTP {e.code}). Paste a fresh one.")
    except Exception as e:  # noqa: BLE001
        raise IdentityError("TOKEN_CHECK_FAILED", f"토큰 확인 실패: {e!r}"[:300], f"Token check failed: {e!r}"[:300])
    scopes = str(d.get("scope") or "")
    return {"email": d.get("email") or d.get("azp") or "", "expires_in": int(d.get("expires_in") or 0),
            "cloud_platform": "cloud-platform" in scopes, "scopes": scopes.split()}


def _mint(sa: str) -> Dict[str, Any]:
    from src.gcp_client import get_gcp_token  # runtime identity (no override bound while minting)
    with bind(None, None):
        rt = get_gcp_token()
    url = f"https://iamcredentials.googleapis.com/v1/projects/-/serviceAccounts/{urllib.parse.quote(sa)}:generateAccessToken"
    body = json.dumps({"scope": ["https://www.googleapis.com/auth/cloud-platform"], "lifetime": "3600s"}).encode()
    req = urllib.request.Request(url, data=body, method="POST", headers={"Authorization": f"Bearer {rt}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, context=_CTX, timeout=15) as r:
            d = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        msg = e.read().decode("utf-8", "replace")[:300]
        raise IdentityError("IMPERSONATION_DENIED",
                            f"SA 토큰 발급 실패 (HTTP {e.code}). 스타터 런타임 SA에 {sa}의 roles/iam.serviceAccountTokenCreator를 부여했는지 확인하세요. {msg}",
                            f"Could not mint a token for the SA (HTTP {e.code}). Grant the starter runtime SA roles/iam.serviceAccountTokenCreator on {sa}. {msg}")
    return {"token": d.get("accessToken", ""), "expire": d.get("expireTime", "")}


def resolve(spec: Optional[Dict[str, Any]], lang: str = "ko") -> Dict[str, Any]:
    """Validates an identity spec → {mode, token|None, principal, expires_in, user_identity}. Never returns the input token in logs."""
    spec = spec or {}
    mode = str(spec.get("mode") or "runtime").lower()
    if mode not in MODES:
        raise IdentityError("BAD_MODE", f"알 수 없는 신원 모드: {mode}", f"unknown identity mode: {mode}")
    if mode == "runtime":
        from src.gcp_client import token_principal
        return {"mode": "runtime", "token": None, "principal": token_principal(), "expires_in": None, "user_identity": False}
    if mode == "token":
        tok = str(spec.get("token") or "").strip()
        if tok.lower().startswith("bearer "):
            tok = tok[7:].strip()
        if not _TOKEN_RE.match(tok):
            raise IdentityError("TOKEN_FORMAT", "OAuth 액세스 토큰(ya29.…) 형식이 아닙니다.", "This is not an OAuth access token (ya29.…).")
        key = "t:" + tok[-24:]
        with _CACHE_LOCK:
            hit = _CACHE.get(key)
        if hit and hit["until"] > time.time():
            info = hit["info"]
        else:
            info = tokeninfo(tok)
            with _CACHE_LOCK:
                _CACHE[key] = {"info": info, "until": time.time() + 120}
        if not info["cloud_platform"]:
            raise IdentityError("TOKEN_SCOPE", "토큰에 cloud-platform 범위가 없습니다. `gcloud auth print-access-token`으로 발급하세요.",
                                "The token lacks the cloud-platform scope. Create it with `gcloud auth print-access-token`.")
        return {"mode": "token", "token": tok, "principal": info["email"], "expires_in": info["expires_in"], "user_identity": True}
    sa = str(spec.get("sa") or "").strip().lower()
    if not _SA_RE.match(sa):
        raise IdentityError("SA_FORMAT", "서비스 계정 이메일 형식이 아닙니다 (name@project.iam.gserviceaccount.com).",
                            "Not a service-account e-mail (name@project.iam.gserviceaccount.com).")
    if not impersonate_allowed(sa):
        raise IdentityError("IMPERSONATION_DISABLED",
                            "이 서버는 해당 SA의 서버 측 위임을 허용하지 않습니다 (STARTER_IMPERSONATE_ALLOW). 대신 `gcloud auth print-access-token --impersonate-service-account=" + sa + "` 토큰을 붙여 넣으세요.",
                            "This server does not allow server-side impersonation of that SA (STARTER_IMPERSONATE_ALLOW). Paste a token from `gcloud auth print-access-token --impersonate-service-account=" + sa + "` instead.")
    key = "sa:" + sa
    with _CACHE_LOCK:
        hit = _CACHE.get(key)
    if not hit or hit["until"] < time.time():
        minted = _mint(sa)
        hit = {"token": minted["token"], "until": time.time() + 3000}
        with _CACHE_LOCK:
            _CACHE[key] = hit
    return {"mode": "impersonate", "token": hit["token"], "principal": sa, "expires_in": int(hit["until"] - time.time()), "user_identity": True}


def public(info: Dict[str, Any]) -> Dict[str, Any]:
    """Identity info safe to return to the browser / write to workspace.json (no token)."""
    return {k: info.get(k) for k in ("mode", "principal", "expires_in", "user_identity")}


@contextmanager
def use(spec: Optional[Dict[str, Any]], lang: str = "ko") -> Iterator[Dict[str, Any]]:
    info = resolve(spec, lang)
    with bind(info.get("token"), public(info)):
        yield info
