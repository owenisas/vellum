"""Scope/permission constants and FastAPI dependency helpers."""

from __future__ import annotations

try:
    from enum import StrEnum
except ImportError:  # py<3.11 compat shim
    from enum import Enum

    class StrEnum(str, Enum):  # type: ignore
        pass
from typing import Annotated, Callable

from fastapi import Depends, HTTPException, status

from .jwt import AuthClaims


class Scope(StrEnum):
    ANCHOR_CREATE = "anchor:create"
    COMPANY_CREATE = "company:create"
    COMPANY_ROTATE_KEY = "company:rotate_key"
    CHAT_INVOKE = "chat:invoke"
    ADMIN_RESET = "admin:reset"


def require_scope(*needed: Scope) -> Callable[[AuthClaims], AuthClaims]:
    def _dep(claims: Annotated[AuthClaims, Depends(_current_claims_placeholder)]) -> AuthClaims:
        missing = [s for s in needed if s not in claims.scopes]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"missing scopes: {', '.join(missing)}",
            )
        return claims

    return _dep


def _current_claims_placeholder() -> AuthClaims:  # overridden in app.py via dependency_overrides
    raise HTTPException(status_code=500, detail="auth dependency not wired")
