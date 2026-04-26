"""Global exception handlers — convert raised errors into JSON responses."""

from __future__ import annotations

from uuid import uuid4

import structlog
from fastapi import HTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse


async def global_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all for unhandled exceptions. Returns a correlation ID for log lookup."""
    error_id = uuid4().hex[:8]
    structlog.get_logger().error(
        "unhandled_error",
        error_id=error_id,
        path=request.url.path,
        method=request.method,
        exc_type=type(exc).__name__,
        exc=str(exc),
    )
    return JSONResponse(
        status_code=500,
        content={"error": str(exc), "error_id": error_id},
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Normalize HTTPException to {detail, error_id}."""
    error_id = uuid4().hex[:8]
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "error_id": error_id},
        headers=getattr(exc, "headers", None) or {},
    )
