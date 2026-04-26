"""FastAPI dependencies — wired in app.py."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status

from veritext.auth.jwt import AuthClaims, DEMO_CLAIMS, JWTVerifier


async def get_claims(
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
) -> AuthClaims:
    settings = request.app.state.settings
    if not settings.auth0_enabled():
        return DEMO_CLAIMS
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing bearer token")
    token = authorization.split(" ", 1)[1]
    verifier: JWTVerifier = request.app.state.jwt_verifier
    try:
        return await verifier.verify(token)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc


def require_scopes(*needed: str):
    async def _dep(claims: Annotated[AuthClaims, Depends(get_claims)]) -> AuthClaims:
        missing = [s for s in needed if s not in claims.scopes]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"missing scopes: {', '.join(missing)}",
            )
        return claims

    return _dep
