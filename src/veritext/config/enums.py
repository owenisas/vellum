try:
    from enum import StrEnum
except ImportError:  # py<3.11 compat shim
    from enum import Enum

    class StrEnum(str, Enum):  # type: ignore
        pass


class DemoMode(StrEnum):
    LIVE = "live"
    FIXTURE = "fixture"


class ChainBackendType(StrEnum):
    SIMULATED = "simulated"
    SOLANA = "solana"


class AnchorStrategy(StrEnum):
    PER_RESPONSE = "per_response"
    MERKLE_BATCH = "merkle_batch"


class LLMProvider(StrEnum):
    GOOGLE = "google"
    FIXTURE = "fixture"


class PayloadVisibility(StrEnum):
    PLAINTEXT = "plaintext"
    ENCRYPTED = "encrypted"


class WatermarkInjectionMode(StrEnum):
    WHITESPACE = "whitespace"
    GRAPHEME = "grapheme"
