from .protocol import ChainBackend, ChainReceipt, ChainRecord, InclusionProofStep
from .simulated import SimulatedChain

__all__ = [
    "ChainBackend",
    "ChainReceipt",
    "ChainRecord",
    "InclusionProofStep",
    "SimulatedChain",
]


def make_chain(settings, db_conn):
    """Factory: instantiate the configured chain backend."""
    from veritext.config import ChainBackendType
    if settings.chain_backend == ChainBackendType.SOLANA:
        from .solana import SolanaChain
        return SolanaChain(settings=settings, db_conn=db_conn)
    return SimulatedChain(db_conn=db_conn)
