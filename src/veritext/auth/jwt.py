"""
Auth0 JWT verification with JWKS caching (improvement #11).

- TTL: 5 minutes (configurable via JWKS_CACHE_TTL_SECONDS)
- On `kid` not found, asyncio-Lock-protected synchronous refresh + retry once
- Custom claim namespace: https://veritext.io/
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any

import httpx
from jose import jwt as jose_jwt
from jose.exceptions import JWTError


CLAIM_NAMESPACE = "https://veritext.io/"


@dataclass
class AuthClaims:
    sub: str
    email: str | None
    issuer_id: int | None
    scopes: list[str]
    raw: dict[str, Any]


class JWKSCache:
    """JWKS cache with asyncio-Lock-protected synchronous refresh."""

    def __init__(self, domain: str, ttl_seconds: int = 300) -> None:
        self._domain = domain.rstrip("/")
        self._ttl = ttl_seconds
        self._jwks: dict[str, Any] = {}
        self._fetched_at: float = 0.0
        self._lock = asyncio.Lock()

    async def get(self, kid: str) -> dict[str, Any] | None:
        now = time.time()
        if not self._jwks or (now - self._fetched_at) > self._ttl:
            await self._refresh()
        key = self._find_key(kid)
        if key:
            return key
        # KID miss: synchronously refresh once with lock
        async with self._lock:
            # Double-check after acquiring lock
            key = self._find_key(kid)
            if key:
                return key
            await self._refresh()
        return self._find_key(kid)

    def _find_key(self, kid: str) -> dict[str, Any] | None:
        for k in self._jwks.get("keys", []):
            if k.get("kid") == kid:
                return k
        return None

    async def _refresh(self) -> None:
        url = f"https://{self._domain}/.well-known/jwks.json"
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            self._jwks = resp.json()
        self._fetched_at = time.time()


class JWTVerifier:
    def __init__(self, domain: str, audience: str, ttl_seconds: int = 300) -> None:
        self._domain = domain
        self._audience = audience
        self._cache = JWKSCache(domain, ttl_seconds=ttl_seconds)

    async def verify(self, token: str) -> AuthClaims:
        try:
            unverified_header = jose_jwt.get_unverified_header(token)
        except JWTError as exc:
            raise ValueError("invalid token header") from exc

        kid = unverified_header.get("kid")
        if not kid:
            raise ValueError("token missing kid")
        jwk = await self._cache.get(kid)
        if jwk is None:
            raise ValueError(f"unknown kid: {kid}")

        try:
            claims = jose_jwt.decode(
                token,
                jwk,
                algorithms=["RS256"],
                audience=self._audience,
                issuer=f"https://{self._domain}/",
            )
        except JWTError as exc:
            raise ValueError(f"jwt verification failed: {exc}") from exc

        return _to_claims(claims)


def _to_claims(claims: dict[str, Any]) -> AuthClaims:
    raw_scopes = claims.get("scope", "")
    scopes = raw_scopes.split() if isinstance(raw_scopes, str) else list(raw_scopes)
    permissions = claims.get("permissions") or []
    if isinstance(permissions, list):
        scopes = list(set(scopes) | set(permissions))
    issuer_id = claims.get(f"{CLAIM_NAMESPACE}issuer_id")
    return AuthClaims(
        sub=claims.get("sub", ""),
        email=claims.get(f"{CLAIM_NAMESPACE}email") or claims.get("email"),
        issuer_id=int(issuer_id) if issuer_id is not None else None,
        scopes=scopes,
        raw=claims,
    )


# Demo identity used when Auth0 is disabled.
DEMO_CLAIMS = AuthClaims(
    sub="demo|local",
    email="demo@veritext.local",
    issuer_id=1,
    scopes=[
        "anchor:create",
        "company:create",
        "company:rotate_key",
        "chat:invoke",
        "admin:reset",
    ],
    raw={"demo": True},
)
