# Veritext Architecture

## High-level flow

```
┌─────────────────────┐
│  React SPA (Vite)   │  signs bundles via ethers.js EIP-712
└──────────┬──────────┘
           │ HTTPS + Auth0 JWT
           ▼
┌─────────────────────┐         ┌──────────────────────┐
│  veritext-server    │ ◄─────► │  Auth0 (JWKS, JWT)   │
│  (FastAPI)          │         └──────────────────────┘
│  ┌───────────────┐  │
│  │ ChatService   │  │
│  │ AnchorService │  │  per_response  ┌──────────────┐
│  │ ProofBuilder  │ ─┼──────────────► │ Solana devnet│
│  │ MerkleBatch   │ ─┼──merkle─batch► │ Memo program │
│  └───────────────┘  │                └──────────────┘
│         │           │
│         ▼           │
│  ┌───────────────┐  │
│  │  aiosqlite    │  │
│  │  data/...db   │  │
│  └───────────────┘  │
└─────────────────────┘
           ▲
           │
┌──────────┴──────────┐
│  Chrome MV3 ext     │  stateless detector (no backend call)
│  + veritext-verify  │
│  CLI                │
└─────────────────────┘
```

## Layers

1. **Watermark library** (`packages/watermark/`) — pure Python, zero deps. Encodes 64-bit BCH-protected payload as invisible Unicode. Optional AES-128-CCM encryption.
2. **Generation-time layer** (`packages/genwatermark/`) — SynthID-Text wrapper, defense in depth. Optional, gated by `GENWATERMARK_ENABLED`.
3. **Merkle batching** (`packages/merklebatch/`) — leaf → tree → inclusion proof. Used by Solana batched anchoring.
4. **Backend** (`src/veritext/`) — FastAPI app factory, layered services with dependency injection.
5. **Frontend** (`frontend/`) — React 19 SPA with EIP-712 signing in browser via ethers.js.
6. **Extension** (`extension/`) — Chrome MV3 detection-only.
7. **CLI** (`src/veritext/cli/verify.py`) — stateless verifier; takes a bundle JSON, returns pass/fail.

## Configuration surface

All configuration via Pydantic `BaseSettings` (env-driven). See `.env.example`.

Key flags:
- `CHAIN_BACKEND=simulated|solana`
- `ANCHOR_STRATEGY=per_response|merkle_batch`
- `PAYLOAD_VISIBILITY=plaintext|encrypted`
- `WATERMARK_INJECTION_MODE=whitespace|grapheme`
- `GENWATERMARK_ENABLED=false|true`
- `JWKS_CACHE_TTL_SECONDS=300`

## Cryptographic primitives

- **Hash**: SHA-256
- **Signature**: ECDSA secp256k1 — EIP-712 typed-data primary, EIP-191 personal_sign fallback
- **FEC**: BCH(63,16) — pure-Python implementation in `packages/watermark/_bch.py`
- **Symmetric**: AES-128-CCM (for encrypted-payload mode)
- **Canonical JSON**: RFC 8785 (JCS)
- **Borsh schema**: versioned with leading `v: u8 = 2` byte

## Threat model and compliance

See `THREAT_MODEL.md` and `COMPLIANCE.md`.
