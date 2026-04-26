"""Global error handlers with correlation IDs."""

from __future__ import annotations

import secrets
from typing import Any

import structlog
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError


log = structlog.get_logger("veritext.errors")


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ValidationError)
    async def _validation(request: Request, exc: ValidationError):
        return _err(400, "validation_error", str(exc))

    @app.exception_handler(ValueError)
    async def _value(request: Request, exc: ValueError):
        return _err(400, "value_error", str(exc))

    @app.exception_handler(PermissionError)
    async def _perm(request: Request, exc: PermissionError):
        return _err(403, "permission_error", str(exc))

    @app.exception_handler(LookupError)
    async def _lookup(request: Request, exc: LookupError):
        return _err(404, "not_found", str(exc))

    @app.exception_handler(Exception)
    async def _fallback(request: Request, exc: Exception):
        eid = secrets.token_hex(4)
        log.error("unhandled_exception", error_id=eid, exc=str(exc), path=str(request.url.path))
        return _err(500, "internal_error", "internal error", error_id=eid)


def _err(status: int, code: str, detail: str, *, error_id: str | None = None) -> JSONResponse:
    body: dict[str, Any] = {"error": code, "detail": detail}
    if error_id:
        body["error_id"] = error_id
    return JSONResponse(status_code=status, content=body)
