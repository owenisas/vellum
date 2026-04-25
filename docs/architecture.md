# Architecture

```
React SPA (frontend/) ─┐
                       ├─►  vellum-server (FastAPI)  ──►  Auth0 (JWT)
Chrome MV3 ext ────────┘                                ├──►  LLM Providers (Google/MiniMax/Bedrock)
                                                        ├──►  Solana Devnet (Memo program)
                                                        └──►  SQLite (aiosqlite)
```

## Layers

| Layer | Module | Responsibility |
|---|---|---|
| Configuration | `vellum.config` | Pydantic settings, enums, validation |
| Auth | `vellum.auth` | Auth0 JWT decode + ECDSA sign/verify/recover |
| Models | `vellum.models` | Pydantic request/response shapes |
| Providers | `vellum.providers` | LLM provider Protocol + impls (Google, MiniMax, Bedrock, Fixture) |
| Chain | `vellum.chain` | ChainBackend Protocol + Simulated/Solana impls |
| Database | `vellum.db` | aiosqlite connection + repositories |
| Services | `vellum.services` | Chat, Anchor, Signing, Watermark, ProofBundleBuilder |
| API | `vellum.api` | FastAPI routers grouped by domain |
| Middleware | `vellum.middleware` | Structured logging, error handling |

## Design rules

1. **Protocol over inheritance** — `LLMProvider` and `ChainBackend` are runtime-checkable
   Protocols. New providers/backends drop in without touching existing code.
2. **Async-first** — repositories use `aiosqlite`; outbound HTTP uses `httpx`; LLM SDK calls
   wrapped in `asyncio.to_thread` so they don't block the event loop.
3. **Auth0 + ECDSA orthogonal** — JWT answers "who is calling?", ECDSA answers "did this
   entity sign these exact bytes?". Both can be disabled independently.
4. **Demo-first** — empty `AUTH0_DOMAIN` returns a `DEMO_IDENTITY` with all permissions;
   `DEMO_MODE=fixture` swaps any LLM call for a deterministic fixture provider. Both work
   without external services.
5. **Structured logging** — every request gets a `structlog` log line; errors get a
   correlation `error_id` returned to the client.

## Request flow: anchor

```
POST /api/anchor  (JWT: anchor:create)
  └► AnchorService.anchor()
       ├► SigningService.verify(hash, sig, issuer_id)        # ECDSA
       ├► ResponseRepository.save(...)                       # raw + watermarked text
       ├► ChainBackend.anchor(hash, issuer_id, sig, meta)    # SimulatedChain | SolanaChain
       ├► Watermarker.detect(text)                           # extract watermark info
       └► ProofBundleBuilder.build(receipt, company, wm, sig) # Proof Bundle v2
  └► Returns AnchorResponse
```

## Request flow: verify

```
POST /api/verify  (public)
  └► AnchorService.verify(text)
       ├► hash_text(text)                                    # SHA-256
       ├► ChainBackend.lookup(hash)                          # find original anchor
       ├► CompanyRepository.get_by_issuer(record.issuer_id)
       └► ProofBundleBuilder.build(...)                      # rebuild bundle from chain
  └► Returns VerifyResponse
```
