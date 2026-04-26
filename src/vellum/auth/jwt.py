"""Auth0 JWT decoding with JWKS caching (async via httpx)."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

import httpx
from fastapi import HTTPException, Request, status
from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTClaimsError, JWTError

from vellum.config import AppSettings, AuthSettings, get_settings

ISSUER_ID_CLAIM = "https://vellum.io/issuer_id"
EMAIL_CLAIM = "https://vellum.io/email"


@dataclass
class Identity:
    """Decoded JWT identity."""

    sub: str
    permissions: list[str] = field(default_factory=list)
    email: str | None = None
    gty: str | None = None
    issuer_id: int | None = None
    raw_claims: dict[str, Any] = field(default_factory=dict)


# Demo identity: returned when Auth0 is disabled. Has every scope so /api/* works as-is.
DEMO_IDENTITY = Identity(
    sub="demo|anonymous",
    permissions=["anchor:create", "company:create", "chat:invoke", "admin:reset"],
    email="demo@vellum.local",
)


class JWKSCache:
    """In-memory JWKS cache with TTL + key-rotation refetch on miss."""

    def __init__(self, domain: str, ttl: int = 3600) -> None:
        self._url = f"https://{domain}/.well-known/jwks.json" if domain else ""
        self._ttl = ttl
        self._keys: list[dict[str, Any]] = []
        self._fetched_at: float = 0.0

    @property
    def url(self) -> str:
        return self._url

    def _is_stale(self) -> bool:
        return (time.time() - self._fetched_at) > self._ttl

    def _find(self, kid: str) -> dict[str, Any] | None:
        for key in self._keys:
            if key.get("kid") == kid:
                return key
        return None

    async def _refresh(self) -> None:
        if not self._url:
            self._keys = []
            return
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(self._url)
            resp.raise_for_status()
            self._keys = resp.json().get("keys", [])
            self._fetched_at = time.time()

    async def get_signing_key(self, kid: str) -> dict[str, Any]:
        if not self._keys or self._is_stale() or self._find(kid) is None:
            await self._refresh()
        key = self._find(kid)
        if not key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Signing key not found for kid={kid}",
            )
        return key


# Process-global JWKS cache. Settings are passed in once via decode_token.
_global_cache: JWKSCache | None = None


def _cache_for(settings: AuthSettings) -> JWKSCache:
    global _global_cache
    if _global_cache is None or _global_cache.url != f"https://{settings.auth0_domain}/.well-known/jwks.json":
        _global_cache = JWKSCache(settings.auth0_domain)
    return _global_cache


def _extract_token(request: Request) -> str | None:
    auth = request.headers.get("Authorization") or request.headers.get("authorization")
    if not auth:
        return None
    parts = auth.split(None, 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return parts[1].strip() or None


async def decode_token(token: str, settings: AuthSettings) -> Identity:
    """Decode and validate an Auth0 JWT. Raises HTTPException(401/403) on any failure."""
    if not settings.enabled:
        return DEMO_IDENTITY

    try:
        unverified_header = jwt.get_unverified_header(token)
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token header: {exc}",
        ) from exc

    kid = unverified_header.get("kid")
    if not kid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token header missing 'kid'",
        )

    cache = _cache_for(settings)
    signing_key = await cache.get_signing_key(kid)

    try:
        claims = jwt.decode(
            token,
            signing_key,
            algorithms=settings.algorithms_list,
            audience=settings.auth0_audience,
            issuer=settings.issuer,
        )
    except ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired"
        ) from exc
    except JWTClaimsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Token claims invalid: {exc}"
        ) from exc
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Token decode failed: {exc}"
        ) from exc

    perms_set: set[str] = set()
    perms = claims.get("permissions") or []
    if isinstance(perms, list):
        perms_set.update(str(p) for p in perms)
    scope = claims.get("scope") or ""
    if isinstance(scope, str):
        perms_set.update(s for s in scope.split() if s)

    issuer_id = claims.get(ISSUER_ID_CLAIM)
    if isinstance(issuer_id, str) and issuer_id.isdigit():
        issuer_id = int(issuer_id)
    elif not isinstance(issuer_id, int):
        issuer_id = None

    return Identity(
        sub=str(claims.get("sub", "")),
        permissions=sorted(perms_set),
        email=claims.get(EMAIL_CLAIM) or claims.get("email"),
        gty=claims.get("gty"),
        issuer_id=issuer_id,
        raw_claims=claims,
    )


async def get_current_user(request: Request) -> Identity:
    """Required auth dependency. Returns DEMO_IDENTITY when Auth0 disabled."""
    settings: AppSettings = get_settings()
    if not settings.auth.enabled:
        return DEMO_IDENTITY

    token = _extract_token(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing or malformed",
        )
    return await decode_token(token, settings.auth)


async def get_optional_user(request: Request) -> Identity | None:
    """Optional auth dependency. Returns None instead of 401."""
    settings: AppSettings = get_settings()
    if not settings.auth.enabled:
        return DEMO_IDENTITY

    token = _extract_token(request)
    if not token:
        return None
    try:
        return await decode_token(token, settings.auth)
    except HTTPException:
        return None
