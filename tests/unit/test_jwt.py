"""Unit tests for the Auth0 JWT decoder.

We never touch a real Auth0 tenant. Instead we generate a local RSA keypair,
sign a JWT against it with python-jose, and monkey-patch ``JWKSCache._refresh``
so :func:`decode_token` resolves our test key by ``kid``.
"""

from __future__ import annotations

import time
import uuid

import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException
from jose import jwt as jose_jwt
from jose.utils import long_to_base64

from vellum.auth.jwt import DEMO_IDENTITY, JWKSCache, decode_token
from vellum.config.settings import AuthSettings

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _b64(n: int) -> str:
    return long_to_base64(n).decode("ascii")


def _rsa_keypair():
    """Return (pem_private_key, jwk_public_key) using a fresh RSA keypair."""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_numbers = key.private_numbers()
    public_numbers = key.public_key().public_numbers()

    kid = uuid.uuid4().hex
    jwk = {
        "kty": "RSA",
        "kid": kid,
        "use": "sig",
        "alg": "RS256",
        "n": _b64(public_numbers.n),
        "e": _b64(public_numbers.e),
        "d": _b64(private_numbers.d),
        "p": _b64(private_numbers.p),
        "q": _b64(private_numbers.q),
        "dp": _b64(private_numbers.dmp1),
        "dq": _b64(private_numbers.dmq1),
        "qi": _b64(private_numbers.iqmp),
    }
    public_jwk = {k: v for k, v in jwk.items() if k in {"kty", "kid", "use", "alg", "n", "e"}}
    return jwk, public_jwk, kid


def _settings(domain: str = "vellum-test.us.auth0.com") -> AuthSettings:
    return AuthSettings(
        AUTH0_DOMAIN=domain,
        AUTH0_AUDIENCE="https://api.vellum.io",
        AUTH0_ALGORITHMS="RS256",
    )


def _install_jwks(monkeypatch, public_jwk: dict, settings: AuthSettings) -> JWKSCache:
    """Pre-populate the global JWKS cache so _refresh becomes a no-op."""
    import vellum.auth.jwt as jwt_module

    cache = JWKSCache(settings.auth0_domain)
    cache._keys = [public_jwk]
    cache._fetched_at = time.time()

    async def _noop_refresh(self) -> None:
        return None

    monkeypatch.setattr(JWKSCache, "_refresh", _noop_refresh)
    monkeypatch.setattr(jwt_module, "_global_cache", cache)
    return cache


def _sign(claims: dict, private_jwk: dict, kid: str) -> str:
    return jose_jwt.encode(
        claims,
        private_jwk,
        algorithm="RS256",
        headers={"kid": kid},
    )


# ---------------------------------------------------------------------------
# tests
# ---------------------------------------------------------------------------


async def test_demo_identity_when_disabled():
    settings = AuthSettings(AUTH0_DOMAIN="")
    identity = await decode_token("anything", settings)
    assert identity is DEMO_IDENTITY
    assert "anchor:create" in identity.permissions


async def test_decode_with_mocked_jwks(monkeypatch):
    private_jwk, public_jwk, kid = _rsa_keypair()
    settings = _settings()
    _install_jwks(monkeypatch, public_jwk, settings)

    now = int(time.time())
    claims = {
        "iss": settings.issuer,
        "aud": settings.auth0_audience,
        "sub": "auth0|user-123",
        "iat": now,
        "exp": now + 600,
        "permissions": ["chat:invoke", "anchor:create"],
        "scope": "openid profile",
        "email": "alice@example.com",
    }
    token = _sign(claims, private_jwk, kid)

    identity = await decode_token(token, settings)

    assert identity.sub == "auth0|user-123"
    assert "chat:invoke" in identity.permissions
    assert "anchor:create" in identity.permissions
    assert "openid" in identity.permissions
    assert identity.email == "alice@example.com"


async def test_expired_token_raises_401(monkeypatch):
    private_jwk, public_jwk, kid = _rsa_keypair()
    settings = _settings()
    _install_jwks(monkeypatch, public_jwk, settings)

    now = int(time.time())
    claims = {
        "iss": settings.issuer,
        "aud": settings.auth0_audience,
        "sub": "auth0|expired",
        "iat": now - 200,
        "exp": now - 100,
    }
    token = _sign(claims, private_jwk, kid)

    with pytest.raises(HTTPException) as exc:
        await decode_token(token, settings)
    assert exc.value.status_code == 401


async def test_bad_audience_raises_401(monkeypatch):
    private_jwk, public_jwk, kid = _rsa_keypair()
    settings = _settings()
    _install_jwks(monkeypatch, public_jwk, settings)

    now = int(time.time())
    claims = {
        "iss": settings.issuer,
        "aud": "https://wrong-audience.example",
        "sub": "auth0|aud-mismatch",
        "iat": now,
        "exp": now + 600,
    }
    token = _sign(claims, private_jwk, kid)

    with pytest.raises(HTTPException) as exc:
        await decode_token(token, settings)
    assert exc.value.status_code == 401


async def test_missing_kid_raises_401(monkeypatch):
    private_jwk, public_jwk, _kid = _rsa_keypair()
    settings = _settings()
    _install_jwks(monkeypatch, public_jwk, settings)

    now = int(time.time())
    claims = {
        "iss": settings.issuer,
        "aud": settings.auth0_audience,
        "sub": "auth0|no-kid",
        "iat": now,
        "exp": now + 600,
    }
    # Build the token WITHOUT a kid header.
    token = jose_jwt.encode(claims, private_jwk, algorithm="RS256")

    with pytest.raises(HTTPException) as exc:
        await decode_token(token, settings)
    assert exc.value.status_code == 401
