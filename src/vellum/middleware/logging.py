"""Structured logging — pretty for dev, JSON for prod."""

from __future__ import annotations

import logging
import sys
import time

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


def configure_logging(level: str = "info", fmt: str = "pretty") -> None:
    """Configure stdlib logging + structlog. Idempotent."""
    log_level = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )

    processors: list = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
    ]
    if fmt == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        cache_logger_on_first_use=True,
    )


class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    """Logs every HTTP request with method, path, status, duration."""

    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.monotonic()
        try:
            response = await call_next(request)
        except Exception:
            duration = (time.monotonic() - start) * 1000
            structlog.get_logger().error(
                "http_request_error",
                method=request.method,
                path=request.url.path,
                duration_ms=round(duration, 1),
            )
            raise

        duration = (time.monotonic() - start) * 1000
        structlog.get_logger().info(
            "http_request",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=round(duration, 1),
        )
        return response
