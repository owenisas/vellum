"""Auth layer — JWT (Auth0) and ECDSA (secp256k1) cryptographic identity."""

from .ecdsa import (
    generate_keypair,
    hash_text,
    public_key_to_address,
    recover_address,
    sign_hash,
    verify_signature,
)
from .jwt import (
    DEMO_IDENTITY,
    Identity,
    JWKSCache,
    decode_token,
    get_current_user,
    get_optional_user,
)
from .permissions import Scope, require_m2m, require_permission

__all__ = [
    "DEMO_IDENTITY",
    "Identity",
    "JWKSCache",
    "Scope",
    "decode_token",
    "generate_keypair",
    "get_current_user",
    "get_optional_user",
    "hash_text",
    "public_key_to_address",
    "recover_address",
    "require_m2m",
    "require_permission",
    "sign_hash",
    "verify_signature",
]
