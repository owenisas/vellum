"""Permission scopes and dependency factories."""

from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends, HTTPException, Request, status

from .jwt import Identity, get_current_user


class Scope:
    """Auth0 / demo scope constants."""

    ANCHOR_CREATE = "anchor:create"
    COMPANY_CREATE = "company:create"
    CHAT_INVOKE = "chat:invoke"
    ADMIN_RESET = "admin:reset"


def require_permission(permission: str) -> Callable:
    """Factory: dependency that checks Identity.permissions includes `permission`."""

    async def dep(
        request: Request,
        identity: Identity = Depends(get_current_user),
    ) -> Identity:
        if permission not in identity.permissions and "*" not in identity.permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required permission: {permission}",
            )
        return identity

    return dep


def require_m2m() -> Callable:
    """Dependency: requires gty == 'client-credentials' (AI agent only)."""

    async def dep(identity: Identity = Depends(get_current_user)) -> Identity:
        if identity.gty != "client-credentials":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This endpoint requires a machine-to-machine token",
            )
        return identity

    return dep
