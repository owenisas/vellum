"""FastAPI application factory + lifespan manager."""

from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path

import structlog
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse, JSONResponse

from vellum.api import (
    chain_router,
    chat_router,
    companies_router,
    demo_router,
    health_router,
    registry_router,
    responses_router,
    solana_router,
)
from vellum.chain.factory import create_chain
from vellum.config import AppSettings, get_settings
from vellum.db.connection import init_db
from vellum.db.repositories import (
    ChainBlockRepository,
    CompanyRepository,
    ResponseRepository,
)
from vellum.middleware import (
    StructuredLoggingMiddleware,
    configure_logging,
    global_error_handler,
    http_exception_handler,
)
from vellum.providers import ProviderRouter
from vellum.services import (
    AnchorService,
    ChatService,
    ProofBundleBuilder,
    SigningService,
    WatermarkService,
)

FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"


@dataclass
class ServiceContainer:
    chat: ChatService
    anchor: AnchorService
    signing: SigningService
    watermark: WatermarkService


@dataclass
class RepoContainer:
    company: CompanyRepository
    response: ResponseRepository
    chain: ChainBlockRepository


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings: AppSettings = get_settings()
    configure_logging(level=settings.log_level, fmt=settings.log_format.value)

    await init_db(settings.db_path)

    company_repo = CompanyRepository(settings.db_path)
    response_repo = ResponseRepository(settings.db_path)
    chain_repo = ChainBlockRepository(settings.db_path)

    chain = await create_chain(settings)
    signing = SigningService(company_repo, admin_secret=settings.registry_admin_secret)
    watermark = WatermarkService()
    provider_router = ProviderRouter(
        settings.llm,
        fixture_only=settings.is_fixture_mode,
    )
    proof_builder = ProofBundleBuilder(
        settings.chain_backend,
        settings.solana.solana_cluster,
        settings.solana.solana_rpc_url,
    )
    chat_service = ChatService(
        provider_router, watermark, fixture_mode=settings.is_fixture_mode
    )
    anchor_service = AnchorService(
        chain, signing, company_repo, response_repo, chain_repo, proof_builder
    )

    app.state.settings = settings
    app.state.services = ServiceContainer(
        chat=chat_service,
        anchor=anchor_service,
        signing=signing,
        watermark=watermark,
    )
    app.state.repos = RepoContainer(
        company=company_repo, response=response_repo, chain=chain_repo
    )
    app.state.chain_backend = chain
    app.state.provider_router = provider_router

    structlog.get_logger().info(
        "vellum_started",
        chain_backend=settings.chain_backend.value,
        demo_mode=settings.demo_mode.value,
        auth0=settings.auth.enabled,
        google=bool(settings.llm.google_api_key),
        minimax=bool(settings.llm.minimax_api_key),
    )

    try:
        yield
    finally:
        structlog.get_logger().info("vellum_shutdown")


def create_app(settings: AppSettings | None = None) -> FastAPI:
    """Build the FastAPI app. Settings auto-loaded from env if not provided."""
    if settings is None:
        settings = get_settings()

    app = FastAPI(
        title="Vellum",
        version="2.0.0",
        description="Provenance tracking for AI-generated text.",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(StructuredLoggingMiddleware)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(Exception, global_error_handler)

    app.include_router(health_router)
    app.include_router(chat_router)
    app.include_router(registry_router)
    app.include_router(companies_router)
    app.include_router(chain_router)
    app.include_router(solana_router)
    app.include_router(demo_router)
    app.include_router(responses_router)

    # SPA static fallback
    if FRONTEND_DIST.exists():
        assets_dir = FRONTEND_DIST / "assets"
        if assets_dir.exists():
            app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

        @app.get("/{full_path:path}", include_in_schema=False)
        async def spa_fallback(full_path: str):
            if full_path.startswith("api/"):
                return JSONResponse({"detail": "Not Found"}, status_code=404)
            index = FRONTEND_DIST / "index.html"
            if not index.exists():
                return JSONResponse({"detail": "frontend not built"}, status_code=404)
            return FileResponse(index)

    return app


app = create_app()


def main() -> None:  # pragma: no cover
    """uvicorn entrypoint registered as `vellum` console script."""
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "vellum.app:app",
        host=settings.host,
        port=settings.port,
        reload=False,
    )


if __name__ == "__main__":  # pragma: no cover
    main()
