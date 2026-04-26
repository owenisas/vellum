"""Shared FastAPI dependency functions."""

from __future__ import annotations

from fastapi import Request

from vellum.config import AppSettings, get_settings as _get_settings
from vellum.db.repositories import (
    ChainBlockRepository,
    CompanyRepository,
    ResponseRepository,
)
from vellum.services import (
    AnchorService,
    ChatService,
    SigningService,
    WatermarkService,
)


def get_settings() -> AppSettings:
    return _get_settings()


def _state(request: Request):
    return request.app.state


def get_chat_service(request: Request) -> ChatService:
    return _state(request).services.chat


def get_anchor_service(request: Request) -> AnchorService:
    return _state(request).services.anchor


def get_signing_service(request: Request) -> SigningService:
    return _state(request).services.signing


def get_watermark_service(request: Request) -> WatermarkService:
    return _state(request).services.watermark


def get_company_repo(request: Request) -> CompanyRepository:
    return _state(request).repos.company


def get_response_repo(request: Request) -> ResponseRepository:
    return _state(request).repos.response


def get_chain_repo(request: Request) -> ChainBlockRepository:
    return _state(request).repos.chain


def get_chain_backend(request: Request):
    return _state(request).chain_backend
