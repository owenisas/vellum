"""
Veritext FastAPI app factory.

Wires:
- Config (Pydantic settings)
- Logging (structlog)
- Database (aiosqlite via Database class)
- Auth (JWT verifier when Auth0 enabled)
- Providers (Google + Fixture)
- Chain (Simulated or Solana)
- Services (chat, watermark, signing, anchor, proof builder, merkle batcher)
- Routers (health, chat, registry, companies, chain, solana, demo)

Lifespan:
- Connect DB on startup, close on shutdown
- Start MerkleBatchService background task when ANCHOR_STRATEGY=merkle_batch
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from veritext.api import chain as api_chain
from veritext.api import chat as api_chat
from veritext.api import companies as api_companies
from veritext.api import demo as api_demo
from veritext.api import health as api_health
from veritext.api import registry as api_registry
from veritext.api import solana as api_solana
from veritext.auth.jwt import JWTVerifier
from veritext.chain import make_chain
from veritext.config import AnchorStrategy, get_settings
from veritext.db.connection import Database
from veritext.db.repositories import (
    ChainRepo,
    CompanyRepo,
    KeyRotationRepo,
    PendingAnchorRepo,
    ResponseRepo,
)
from veritext.middleware import configure_logging, register_error_handlers
from veritext.providers import FixtureProvider, GoogleProvider, ProviderRouter
from veritext.services import (
    AnchorService,
    ChatService,
    MerkleBatchService,
    ProofBuilder,
    WatermarkService,
)
from veritext.services.signing_service import SigningService


log = structlog.get_logger("veritext.app")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    settings.validate_solana_keypair()
    configure_logging(level=settings.log_level, format=settings.log_format)
    log.info("veritext_starting", chain=settings.chain_backend.value, anchor=settings.anchor_strategy.value)

    db = Database(settings.db_path)
    conn = await db.connect()

    company_repo = CompanyRepo(conn)
    key_repo = KeyRotationRepo(conn)
    response_repo = ResponseRepo(conn)
    chain_repo = ChainRepo(conn)
    pending_repo = PendingAnchorRepo(conn)

    chain = make_chain(settings, conn)

    google = GoogleProvider(
        api_key=settings.llm.google_api_key,
        genwatermark_enabled=settings.watermark.genwatermark_enabled,
    )
    fixture = FixtureProvider()
    provider_router = ProviderRouter(google=google, fixture=fixture)

    watermark_service = WatermarkService(
        genwatermark_enabled=settings.watermark.genwatermark_enabled
    )
    chat_service = ChatService(
        provider_router=provider_router,
        watermark_service=watermark_service,
        injection_mode=settings.watermark.watermark_injection_mode.value,
    )
    signing_service = SigningService(company_repo=company_repo, key_repo=key_repo)
    proof_builder = ProofBuilder(settings=settings, key_repo=key_repo)

    anchor_service = AnchorService(
        chain=chain,
        company_repo=company_repo,
        response_repo=response_repo,
        chain_repo=chain_repo,
        pending_repo=pending_repo,
        key_repo=key_repo,
        signing=signing_service,
        watermark=watermark_service,
        proof_builder=proof_builder,
        anchor_strategy=settings.anchor_strategy,
        chain_backend_type=settings.chain_backend.value,
    )

    merkle_service: MerkleBatchService | None = None
    if settings.anchor_strategy == AnchorStrategy.MERKLE_BATCH:
        merkle_service = MerkleBatchService(
            chain=chain,
            chain_repo=chain_repo,
            pending_repo=pending_repo,
            window_seconds=settings.solana.merkle_batch_window_seconds,
            max_leaves=settings.solana.merkle_batch_max_leaves,
        )
        merkle_service.start()

    jwt_verifier = None
    if settings.auth0_enabled():
        jwt_verifier = JWTVerifier(
            domain=settings.auth.auth0_domain,
            audience=settings.auth.auth0_audience,
            ttl_seconds=settings.auth.jwks_cache_ttl_seconds,
        )

    app.state.settings = settings
    app.state.db = db
    app.state.company_repo = company_repo
    app.state.key_repo = key_repo
    app.state.response_repo = response_repo
    app.state.chain_repo = chain_repo
    app.state.pending_repo = pending_repo
    app.state.chain = chain
    app.state.provider_router = provider_router
    app.state.watermark_service = watermark_service
    app.state.chat_service = chat_service
    app.state.signing_service = signing_service
    app.state.proof_builder = proof_builder
    app.state.anchor_service = anchor_service
    app.state.merkle_service = merkle_service
    app.state.jwt_verifier = jwt_verifier

    try:
        yield
    finally:
        log.info("veritext_shutting_down")
        if merkle_service is not None:
            await merkle_service.stop()
        await db.close()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Veritext",
        version="2.0.0",
        description="Cryptographic provenance tags for AI-generated text.",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_error_handlers(app)

    app.include_router(api_health.router)
    app.include_router(api_chat.router)
    app.include_router(api_registry.router)
    app.include_router(api_companies.router)
    app.include_router(api_chain.router)
    app.include_router(api_solana.router)
    app.include_router(api_demo.router)

    return app


app = create_app()


def run() -> None:
    import uvicorn

    s = get_settings()
    uvicorn.run("veritext.app:app", host=s.app_host, port=s.app_port, reload=False)
