"""Build the right ChainBackend from settings."""

from __future__ import annotations

from vellum.config import AppSettings, ChainBackendType

from .protocol import ChainBackend


async def create_chain(settings: AppSettings) -> ChainBackend:
    """Construct and initialize the configured chain backend."""
    if settings.chain_backend == ChainBackendType.SOLANA:
        from .solana import SolanaChain

        chain = SolanaChain(
            rpc_url=settings.solana.solana_rpc_url,
            keypair_path=settings.solana.solana_keypair_path,
            cluster=settings.solana.solana_cluster,
            db_path=settings.db_path,
        )
    else:
        from .simulated import SimulatedChain

        chain = SimulatedChain(db_path=settings.db_path)

    await chain.initialize()
    return chain
