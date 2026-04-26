# Veritext

**Cryptographic provenance tags for AI-generated text.**

Veritext is a production-grade provenance system that combines invisible Unicode tags, ECDSA-signed proof bundles, and Merkle-batched chain anchoring to answer three questions about any text:

1. **Who issued it?** — ECDSA secp256k1 signing with EIP-712 typed-data, Auth0 identity binding
2. **Was it tampered with?** — invisible Unicode payload tags with BCH(63,16) error correction
3. **When was it registered?** — Solana devnet anchoring (per-response or Merkle-batched)

> Veritext is **not** a watermark in the SynthID/Kirchenbauer sense. It is a *cryptographic provenance tag* embedded in cooperative pipelines. See [`docs/THREAT_MODEL.md`](docs/THREAT_MODEL.md) for the full threat model.

## Quick start

```bash
make bootstrap    # install deps, init DB
make dev          # backend on :5050, frontend on :5173
make test         # run all tests
```

For Solana devnet anchoring:
```bash
make bootstrap-solana
```

For full Auth0 + Solana setup:
```bash
make bootstrap-all
```

## Architecture

```
+--------------+       HTTPS       +-----------------+    Solana RPC    +-----------+
| React SPA    | <---------------> | veritext-server | <--------------> | Solana    |
| (Vite, MV3   |                   | (FastAPI)       |                  | devnet    |
| extension)   |                   |                 |                  |           |
+--------------+                   +-----------------+                  +-----------+
                                          |
                                          v
                                    +------------+
                                    | aiosqlite  |
                                    | (SQLite)   |
                                    +------------+
```

## Repo layout

- `packages/watermark/` — pure-Python Unicode tagging library (BCH-protected payload, AES-128-CCM optional, grapheme + whitespace injection modes)
- `packages/genwatermark/` — generation-time SynthID-Text layer (defense in depth)
- `packages/merklebatch/` — Merkle tree builder for batched chain anchoring
- `src/veritext/` — FastAPI backend (config / auth / db / chain / providers / services / api / middleware)
- `frontend/` — React 19 + Vite 7 SPA
- `extension/` — Chrome MV3 detection extension
- `cli/` — `veritext-verify` stateless CLI (Python) plus a Go binary stretch artifact
- `tests/` — unit, integration, adversarial, e2e
- `docs/` — architecture, threat model, EU AI Act + C2PA compliance matrix

## Compliance

Veritext is built for [EU AI Act Article 50](docs/COMPLIANCE.md) (machine-readable marking of synthetic text — binding August 2026) and aligns with [C2PA 2.2 Content Credentials](https://spec.c2pa.org/specifications/specifications/2.2/specs/C2PA_Specification.html).

## License

MIT.
