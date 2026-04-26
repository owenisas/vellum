# Origraph v2 — Full Rewrite Specification

> Rewrite from scratch with clean architecture, unified project structure, and production-grade backend pipeline. Includes Auth0 identity, Solana devnet anchoring, and Gemma 4 as first-class features.

---

## Table of Contents

1. [Problem Statement](#1-problem-statement)
2. [Architecture Overview](#2-architecture-overview)
3. [Project Structure](#3-project-structure)
4. [Core Library: `origraph-watermark`](#4-core-library-origraph-watermark)
5. [Backend: `origraph-server`](#5-backend-origraph-server)
6. [Frontend: `origraph-web`](#6-frontend-origraph-web)
7. [Browser Extension: `origraph-extension`](#7-browser-extension-origraph-extension)
8. [Database Schema](#8-database-schema)
9. [API Contract](#9-api-contract)
10. [Auth0 Integration](#10-auth0-integration)
11. [Solana Anchoring](#11-solana-anchoring)
12. [LLM Provider Pipeline](#12-llm-provider-pipeline)
13. [Proof Bundle v2 Specification](#13-proof-bundle-v2-specification)
14. [Configuration & Environment](#14-configuration--environment)
15. [Bootstrap & DevOps](#15-bootstrap--devops)
16. [Testing Strategy](#16-testing-strategy)
17. [Migration Path](#17-migration-path)

---

## 1. Problem Statement

### What Origraph Does

Origraph is a provenance-tracking platform for AI-generated text. It answers three questions:
1. **Who generated this text?** (identity via Auth0 JWT + ECDSA signing)
2. **Was this text tampered with?** (integrity via invisible Unicode watermarks)
3. **When was this text registered?** (timestamping via on-chain anchoring)

### Why Rewrite

The v1 codebase grew organically through three hackathon integrations (Gemma 4, Solana, Auth0). Architectural problems accumulated:

| Issue | Impact |
|---|---|
| Watermark SDK lives in a separate `invisible-text-watermark/` subtree with its own `pyproject.toml` | Two build systems, sys.path hacks to import in demo |
| `origraph-registry-demo/` is the "real" app but sounds like a throwaway | Confusing project identity |
| `registry/auth.py` (ECDSA) vs `app/auth.py` (Auth0) — same filename, different packages | Import confusion, no clear boundary |
| Services reach into `registry.db` directly + through repository | Two data-access paths for the same tables |
| `AnchoringService` reconstructs chain via `hasattr()` checks | Fragile; protocol not enforced |
| No async DB access — SQLite `connect()` blocks the event loop | Latency spikes under concurrent requests |
| Frontend `api.ts` uses `fetch()` with no retry, timeout, or error normalization | Silent failures in production |
| Extension has zero tests and raw DOM manipulation | Regressions go undetected |
| `config.py` is a flat dataclass with 14 fields and string-typed enums | No validation, no grouping, easy to misconfigure |
| Fixture mode is scattered across service methods | Hard to add new providers; each needs fixture handling |
| No structured logging — `print()` statements everywhere | No observability |
| Tests cover ~40% of backend, 0% of frontend/extension | Major gaps |
| CORS, host, port scattered across env vars with inconsistent defaults | Deployment friction |
| Chain factory uses lazy imports and string matching | No type safety for backend selection |

### Rewrite Goals

1. **Monorepo with clear package boundaries** — one build, one install, shared types
2. **Layered backend** — config → auth → services → repositories → chain backends
3. **Protocol-driven chain abstraction** — SimulatedChain and SolanaChain are interchangeable without `hasattr()`
4. **Auth0 + ECDSA as orthogonal layers** — JWT handles "who are you?", ECDSA handles "did you sign this?"
5. **Async-first** — aiosqlite for DB, httpx for outbound calls
6. **Structured logging** via `structlog`
7. **100% API test coverage** with pytest-asyncio fixtures
8. **Frontend with proper error boundaries, retry logic, and auth flow**
9. **Extension with Playwright E2E tests**

---

## 2. Architecture Overview

```
                                 +-----------------+
                                 |  Auth0 Tenant   |
                                 | (JWKS, tokens)  |
                                 +--------+--------+
                                          |
                                          | JWT
                                          v
+------------+    HTTPS    +---------------------------+    Solana RPC    +-----------+
|  React SPA | <---------> |    origraph-server        | <-------------> | Solana    |
|  (Vite)    |             |    (FastAPI + Uvicorn)    |                 | Devnet    |
+------------+             +---------------------------+                 +-----------+
      |                    | Auth     | Services       |
      |                    | Layer    | Layer          |
      | ethers.js          |          |                |
      | ECDSA sign         | JWT      | ChatService    |
      |                    | decode   | AnchorService  |
+------------+             | ECDSA    | WatermarkSvc   |
| Chrome     |             | verify   | SigningService  |
| Extension  |             |          |                |
| (MV3)     |             +----------+--------+-------+
+------------+                       |        |
                                     v        v
                              +----------+ +-------+
                              | aiosqlite| | Chain  |
                              | (SQLite) | | Proto  |
                              +----------+ +-------+
                                           /      \
                                  Simulated    Solana
                                  Chain        Chain
```

### Data Flow — Full Pipeline

```
User Prompt
    |
    v
[1] POST /api/chat  (JWT required: chat:invoke)
    |
    +--> ChatService.generate()
    |      |
    |      +--> ProviderRouter.dispatch(provider, model, messages)
    |      |      |
    |      |      +--> GoogleProvider.generate()    <-- Gemma 4 (default)
    |      |      +--> MiniMaxProvider.generate()
    |      |      +--> BedrockProvider.generate()
    |      |      +--> FixtureProvider.generate()   <-- DEMO_MODE=fixture
    |      |
    |      +--> WatermarkService.apply(raw_text, params)
    |             |
    |             +--> Watermarker.apply()  (inject invisible Unicode tags)
    |
    +--> Return { raw_text, watermarked_text, model, usage }
    |
    v
[2] Client-side ECDSA signing  (ethers.js, browser)
    |
    +--> sha256(watermarked_text)
    +--> personal_sign(sha256_hash, privateKey)
    |
    v
[3] POST /api/anchor  (JWT required: anchor:create)
    |
    +--> AnchorService.anchor()
    |      |
    |      +--> SigningService.verify(hash, signature, issuer_id)
    |      |      |
    |      |      +--> ecrecover(hash, signature) → address
    |      |      +--> lookup company by address → verify issuer_id matches
    |      |
    |      +--> Repository.save_response(hash, text, signature)
    |      |
    |      +--> Chain.anchor(hash, issuer_id, signature)
    |      |      |
    |      |      +--> [Simulated] SHA-256 linked chain in SQLite
    |      |      +--> [Solana] Memo program tx + SQLite dual-write
    |      |
    |      +--> ProofBundleBuilder.build(receipt, company, watermark)
    |
    +--> Return { chain_receipt, proof_bundle_v2 }
    |
    v
[4] Verification (public, no auth)
    |
    +--> POST /api/verify  { text }
    |      |
    |      +--> sha256(text) → lookup chain → verify signature → detect watermark
    |      +--> Return { verified, proof_bundle_v2, watermark_info }
    |
    +--> Browser extension scans page for zero-width Unicode → CRC-8 validate
```

---

## 3. Project Structure

```
origraph/
├── pyproject.toml                    # Single build — all Python packages
├── uv.lock                           # Lockfile (uv-based)
├── .env.example                      # Canonical env template
├── alembic.ini                       # DB migration config
├── Makefile                          # dev, test, lint, build, bootstrap
│
├── packages/
│   └── watermark/                    # Pure-Python watermark library
│       ├── __init__.py               # Exports: Watermarker, detect, strip, apply
│       ├── payload.py                # 64-bit pack/unpack + CRC-8
│       ├── zero_width.py             # Unicode encoding/decoding, TagInjector
│       ├── config.py                 # TagConfig, WatermarkConfig dataclasses
│       └── py.typed                  # PEP 561 marker
│
├── src/
│   └── origraph/                     # Main application package
│       ├── __init__.py
│       │
│       ├── config/                   # Configuration layer
│       │   ├── __init__.py
│       │   ├── settings.py           # Pydantic Settings (grouped, validated)
│       │   └── enums.py              # ChainBackend, DemoMode, Provider enums
│       │
│       ├── auth/                     # Authentication layer
│       │   ├── __init__.py
│       │   ├── jwt.py                # Auth0 JWT decode, JWKS cache, dependencies
│       │   ├── ecdsa.py              # secp256k1 sign/verify/recover (from eth-account)
│       │   └── permissions.py        # Scope constants, require_permission, require_m2m
│       │
│       ├── models/                   # Pydantic schemas (request/response)
│       │   ├── __init__.py
│       │   ├── chat.py               # ChatRequest, ChatResponse, WmParams
│       │   ├── registry.py           # AnchorRequest, VerifyResponse, ProofBundle
│       │   ├── company.py            # CreateCompanyRequest, CompanyResponse
│       │   └── chain.py              # ChainReceipt, ChainRecord, ChainStatus
│       │
│       ├── services/                 # Business logic layer
│       │   ├── __init__.py
│       │   ├── chat_service.py       # Orchestrates provider + watermark
│       │   ├── anchor_service.py     # Orchestrates signing + chain + proof bundle
│       │   ├── signing_service.py    # ECDSA verification, company CRUD
│       │   ├── watermark_service.py  # Thin wrapper around packages/watermark
│       │   └── proof_builder.py      # ProofBundle v2 construction (extracted)
│       │
│       ├── providers/                # LLM provider implementations
│       │   ├── __init__.py
│       │   ├── base.py               # ProviderProtocol (ABC)
│       │   ├── router.py             # ProviderRouter — dispatch by enum
│       │   ├── google.py             # Google GenAI SDK (Gemma 4)
│       │   ├── minimax.py            # MiniMax via Anthropic SDK
│       │   ├── bedrock.py            # AWS Bedrock Converse API
│       │   └── fixture.py            # Deterministic fixture responses
│       │
│       ├── chain/                    # Chain backend implementations
│       │   ├── __init__.py
│       │   ├── protocol.py           # ChainBackend Protocol + dataclasses
│       │   ├── simulated.py          # SQLite hash-chain
│       │   ├── solana.py             # Solana Memo program + dual-write
│       │   └── factory.py            # create_chain() from settings
│       │
│       ├── db/                       # Data access layer
│       │   ├── __init__.py
│       │   ├── connection.py         # aiosqlite pool, get_db()
│       │   ├── migrations/           # Alembic migration scripts
│       │   │   └── versions/
│       │   ├── repositories/
│       │   │   ├── __init__.py
│       │   │   ├── company_repo.py   # CompanyRepository (async)
│       │   │   ├── response_repo.py  # ResponseRepository (async)
│       │   │   └── chain_repo.py     # ChainBlockRepository (async)
│       │   └── schema.py             # Table definitions (for reference)
│       │
│       ├── api/                      # FastAPI routers
│       │   ├── __init__.py
│       │   ├── health.py             # GET /api/health
│       │   ├── chat.py               # /api/chat, /api/models
│       │   ├── registry.py           # /api/anchor, /api/verify, /api/proof/*
│       │   ├── companies.py          # /api/companies CRUD
│       │   ├── chain.py              # /api/chain/* status/blocks
│       │   ├── solana.py             # /api/solana/verify, /api/solana/balance
│       │   ├── demo.py               # /api/demo/scenario, /api/demo/reset
│       │   └── deps.py               # Shared FastAPI dependencies
│       │
│       ├── middleware/               # FastAPI middleware
│       │   ├── __init__.py
│       │   ├── cors.py               # CORS configuration
│       │   ├── logging.py            # Request/response structured logging
│       │   └── errors.py             # Global exception → JSON response
│       │
│       └── app.py                    # create_app() factory, lifespan manager
│
├── frontend/                         # React SPA
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── index.html
│   ├── .env.example
│   └── src/
│       ├── main.tsx                  # Entry, Auth0Provider, QueryClient
│       ├── App.tsx                   # Router, ProtectedRoute wrappers
│       ├── vite-env.d.ts
│       │
│       ├── config/
│       │   └── env.ts                # Typed env access, feature flags
│       │
│       ├── auth/
│       │   ├── AuthProvider.tsx       # Conditional Auth0Provider
│       │   ├── AuthGuard.tsx          # ProtectedRoute component
│       │   ├── AuthTokenBridge.tsx    # Bridge useAuth0 → api client
│       │   └── useAuth.ts            # Unified hook (works with/without Auth0)
│       │
│       ├── api/
│       │   ├── client.ts             # Base HTTP client (fetch + retry + auth headers)
│       │   ├── chat.ts               # Chat endpoints + React Query hooks
│       │   ├── registry.ts           # Anchor/verify endpoints + hooks
│       │   ├── companies.ts          # Company CRUD + hooks
│       │   ├── chain.ts              # Chain status/blocks + hooks
│       │   └── types.ts              # Shared API response types
│       │
│       ├── hooks/
│       │   ├── useEcdsa.ts           # ethers.js signing hook
│       │   ├── useWatermark.ts       # Watermark detection display
│       │   └── useProofBundle.ts     # Proof bundle verification
│       │
│       ├── components/
│       │   ├── ui/                   # Primitives (Button, Input, Card, Badge, etc.)
│       │   ├── ProofBundleViewer.tsx  # Renders proof bundle with explorer links
│       │   ├── WatermarkBadge.tsx     # Shows watermark status
│       │   ├── ChainExplorer.tsx      # Block list with Solana links
│       │   ├── ModelSelector.tsx      # Provider/model grouped select
│       │   └── ErrorBoundary.tsx      # Catches rendering errors
│       │
│       ├── pages/
│       │   ├── Landing.tsx
│       │   ├── Dashboard.tsx
│       │   ├── GenerateAndAnchor.tsx  # Full pipeline: generate → sign → anchor
│       │   ├── Verify.tsx             # Text verification
│       │   ├── Companies.tsx          # Company management
│       │   ├── Chain.tsx              # Chain explorer
│       │   ├── GuidedDemo.tsx         # Step-by-step demo walkthrough
│       │   └── DemoOverview.tsx       # Architecture explanation
│       │
│       ├── layout/
│       │   ├── AppShell.tsx           # Nav + header + auth controls
│       │   └── PageContainer.tsx      # Consistent page wrapper
│       │
│       └── styles/
│           ├── globals.css            # CSS variables, reset
│           └── tokens.ts              # Design tokens as JS constants
│
├── extension/                        # Chrome MV3 Extension
│   ├── manifest.json
│   ├── content/
│   │   ├── scanner.ts                # Zero-width detection engine (typed)
│   │   ├── highlighter.ts            # DOM overlay rendering
│   │   └── content.ts                # Entry: MutationObserver + scan
│   ├── popup/
│   │   ├── popup.html
│   │   ├── popup.ts                  # Popup UI logic
│   │   └── popup.css
│   ├── background/
│   │   └── background.ts             # Service worker
│   ├── shared/
│   │   ├── payload.ts                # Port of payload.py (pack/unpack/CRC-8)
│   │   └── constants.ts              # Unicode codepoints, scan config
│   └── icons/
│
├── scripts/
│   ├── bootstrap.sh                  # One-command setup (Python + Node + optional integrations)
│   ├── setup_solana.sh               # Solana CLI + keypair + airdrop
│   ├── setup_auth0.sh                # Auth0 tenant provisioning
│   ├── dev.sh                        # Start backend + frontend in parallel
│   └── seed.sh                       # Seed demo data (companies, fixture anchors)
│
├── tests/
│   ├── conftest.py                   # Shared fixtures: test app, test DB, mock chain
│   ├── unit/
│   │   ├── test_watermark.py         # Watermark library
│   │   ├── test_payload.py           # 64-bit pack/unpack + CRC
│   │   ├── test_ecdsa.py             # ECDSA sign/verify/recover
│   │   ├── test_jwt.py               # Auth0 JWT decode (mocked JWKS)
│   │   ├── test_proof_builder.py     # Proof bundle construction
│   │   ├── test_simulated_chain.py   # Simulated chain operations
│   │   └── test_providers.py         # LLM provider dispatch (mocked)
│   ├── integration/
│   │   ├── test_api_chat.py          # POST /api/chat with fixture mode
│   │   ├── test_api_anchor.py        # Full anchor pipeline
│   │   ├── test_api_verify.py        # Verification endpoints
│   │   ├── test_api_companies.py     # Company CRUD with auth
│   │   ├── test_api_chain.py         # Chain status/blocks
│   │   ├── test_auth_flow.py         # JWT validation, permission checks, demo fallback
│   │   └── test_solana_chain.py      # Solana chain (mocked RPC)
│   └── e2e/
│       ├── test_extension.py         # Playwright: extension detection
│       └── test_full_flow.py         # Playwright: generate → sign → anchor → verify
│
├── docs/
│   ├── architecture.md               # This document, summarized
│   ├── api.md                        # OpenAPI supplement (auth, examples)
│   └── specs/
│       └── proof-bundle-v2.schema.json
│
└── docker/
    ├── Dockerfile                    # Multi-stage: Python backend + frontend build
    └── docker-compose.yml            # Full stack: app + (optional) Solana test validator
```

### Key Differences from v1

| Aspect | v1 (Current) | v2 (Rewrite) |
|---|---|---|
| Watermark library | Separate subtree, own `pyproject.toml` | `packages/watermark/` — same monorepo, imported directly |
| Project root | `origraph-registry-demo/` | `src/origraph/` — proper Python package |
| Auth modules | `registry/auth.py` + `app/auth.py` (name collision) | `origraph/auth/jwt.py` + `origraph/auth/ecdsa.py` |
| Config | Flat dataclass, 14 string fields | Pydantic `BaseSettings` with grouped sub-models |
| Database | Sync `sqlite3`, scattered across modules | `aiosqlite` with repository pattern, Alembic migrations |
| LLM providers | Methods on `ChatService` with `if/elif` dispatch | `ProviderProtocol` + router pattern (open for extension) |
| Chain backends | `hasattr()` checks, lazy imports | `ChainBackend` Protocol + factory, fully typed |
| API routers | Two files: `registry.py` (18 endpoints) + `chat.py` (5 endpoints) | Split by domain: 8 focused router files |
| Frontend API client | One `api.ts` (180+ lines), manual `fetch()` | Split by domain, retry/timeout/auth built into base client |
| Tests | ~40% backend, 0% frontend/extension | 90%+ backend, Playwright E2E for frontend/extension |
| Logging | `print()` | `structlog` (JSON in prod, pretty in dev) |

---

## 4. Core Library: `packages/watermark`

### Purpose

Self-contained, zero-dependency watermarking library. Can be published to PyPI independently.

### Watermark Payload Format (64-bit)

```
Bit layout (MSB first):
[63:60] schema_version    4 bits   (0-15)
[59:48] issuer_id        12 bits   (0-4095)
[47:32] model_id         16 bits   (0-65535)
[31:16] model_version_id 16 bits   (0-65535)
[15:8]  key_id            8 bits   (0-255)
[7:0]   crc8              8 bits   CRC-8 (polynomial 0x07) over bytes [63:8]
```

### Unicode Encoding

| Symbol | Codepoint | Meaning |
|---|---|---|
| `U+2063` | Invisible Separator | Tag start delimiter |
| `U+2064` | Invisible Plus | Tag end delimiter |
| `U+200B` | Zero-Width Space | Binary `0` |
| `U+200C` | Zero-Width Non-Joiner | Binary `1` |

Each tag = start + 64 encoded bits + end = 66 Unicode characters (invisible).

### Public API

```python
# packages/watermark/__init__.py

class Watermarker:
    def __init__(
        self,
        *,
        schema_version: int = 1,
        issuer_id: int = 1,
        model_id: int = 0,
        model_version_id: int = 0,
        key_id: int = 1,
        repeat_interval_tokens: int = 160,
    ) -> None: ...

    def apply(self, text: str) -> str:
        """Inject invisible watermark tags into text."""

    def detect(self, text: str) -> DetectResult:
        """Scan text for watermark tags. Returns structured results."""

    @staticmethod
    def strip(text: str) -> str:
        """Remove all watermark tags from text."""

@dataclass
class DetectResult:
    watermarked: bool
    tag_count: int
    valid_count: int
    invalid_count: int
    payloads: list[PayloadInfo]

@dataclass
class PayloadInfo:
    schema_version: int
    issuer_id: int
    model_id: int
    model_version_id: int
    key_id: int
    crc_valid: bool
    raw_payload_hex: str
```

### Tag Injection Algorithm (TagInjector)

1. Track whitespace-delimited token count as text streams in
2. Every `repeat_interval_tokens` tokens, insert tag after the next whitespace
3. On finalize: if zero tags inserted and text length > 20 chars, force one tag at ~40% position
4. Supports streaming via `inject_delta(chunk, finalize=False)` for real-time watermarking

### CRC-8 Implementation

Standard CRC-8 with polynomial `0x07`:
```python
def crc8(data: bytes) -> int:
    crc = 0
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = ((crc << 1) ^ 0x07) & 0xFF if crc & 0x80 else (crc << 1) & 0xFF
    return crc
```

---

## 5. Backend: `src/origraph`

### 5.1 Configuration (`origraph/config/`)

Replace the flat dataclass with Pydantic `BaseSettings` for automatic env loading, type coercion, and validation.

```python
# origraph/config/enums.py
from enum import StrEnum

class DemoMode(StrEnum):
    LIVE = "live"
    FIXTURE = "fixture"

class ChainBackendType(StrEnum):
    SIMULATED = "simulated"
    SOLANA = "solana"

class LLMProvider(StrEnum):
    GOOGLE = "google"
    MINIMAX = "minimax"
    BEDROCK = "bedrock"
    FIXTURE = "fixture"
```

```python
# origraph/config/settings.py
from pydantic_settings import BaseSettings
from pydantic import Field, model_validator

class AuthSettings(BaseSettings):
    """Auth0 configuration. All optional — empty domain disables Auth0."""
    auth0_domain: str = ""
    auth0_audience: str = "https://api.origraph.io"
    auth0_algorithms: str = "RS256"

    @property
    def enabled(self) -> bool:
        return bool(self.auth0_domain)

    @property
    def issuer(self) -> str:
        return f"https://{self.auth0_domain}/" if self.auth0_domain else ""

class SolanaSettings(BaseSettings):
    """Solana configuration. Only active when chain_backend=solana."""
    solana_rpc_url: str = "https://api.devnet.solana.com"
    solana_keypair_path: str = ""
    solana_cluster: str = "devnet"

class LLMSettings(BaseSettings):
    """LLM provider API keys and endpoints."""
    google_api_key: str = ""
    minimax_api_key: str = ""
    minimax_base_url: str = "https://api.minimax.io/anthropic"
    default_provider: LLMProvider = LLMProvider.GOOGLE
    default_model: str = "gemma-4-27b-it"

class AppSettings(BaseSettings):
    """Top-level application settings."""
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Core
    demo_mode: DemoMode = DemoMode.LIVE
    chain_backend: ChainBackendType = ChainBackendType.SIMULATED
    registry_admin_secret: str = "dev-admin-secret"

    # Server
    host: str = "127.0.0.1"
    port: int = 5050
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:5050"]
    log_level: str = "info"
    log_format: str = "pretty"  # "pretty" or "json"

    # Sub-configs
    auth: AuthSettings = Field(default_factory=AuthSettings)
    solana: SolanaSettings = Field(default_factory=SolanaSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)

    # Database
    db_path: str = "data/origraph.db"

    @model_validator(mode="after")
    def validate_solana_keypair(self) -> "AppSettings":
        if self.chain_backend == ChainBackendType.SOLANA and not self.solana.solana_keypair_path:
            raise ValueError("SOLANA_KEYPAIR_PATH required when CHAIN_BACKEND=solana")
        return self

    @property
    def is_fixture_mode(self) -> bool:
        return self.demo_mode == DemoMode.FIXTURE
```

### 5.2 Auth Layer (`origraph/auth/`)

Two orthogonal auth mechanisms:

#### JWT Authentication (`jwt.py`)

Handles "who is this user/agent?"

```python
@dataclass
class Identity:
    """Decoded JWT identity."""
    sub: str                          # Auth0 subject
    permissions: list[str]            # Auth0 scopes
    email: str | None = None
    gty: str | None = None            # "client-credentials" for M2M
    issuer_id: int | None = None      # Custom claim: https://origraph.io/issuer_id

# JWKS cache with 1-hour TTL, httpx-based async fetch
class JWKSCache:
    def __init__(self, domain: str, ttl: int = 3600) -> None: ...
    async def get_signing_key(self, kid: str) -> dict: ...

async def decode_token(token: str, settings: AuthSettings) -> Identity: ...

# FastAPI dependencies
async def get_current_user(request: Request) -> Identity:
    """Required auth. Returns demo identity when Auth0 is disabled."""

async def get_optional_user(request: Request) -> Identity | None:
    """Optional auth. Returns None if no token (not 401)."""

def require_permission(permission: str) -> Callable:
    """Factory: dependency that checks Identity.permissions includes permission."""

def require_m2m() -> Callable:
    """Dependency: requires gty == 'client-credentials' (AI agent only)."""
```

**Demo Mode Fallback:** When `auth.enabled == False`, `get_current_user` returns:
```python
DEMO_IDENTITY = Identity(
    sub="demo|anonymous",
    permissions=["anchor:create", "company:create", "chat:invoke", "admin:reset"],
)
```
This preserves `DEMO_MODE=fixture` behavior without any Auth0 configuration.

#### ECDSA Signing (`ecdsa.py`)

Handles "did this entity cryptographically sign this text?"

```python
def hash_text(text: str) -> str:
    """SHA-256 hash of UTF-8 encoded text. Returns hex string."""

def recover_address(data_hash: str, signature_hex: str) -> str:
    """Recover Ethereum address from EIP-191 personal_sign signature."""

def verify_signature(data_hash: str, signature_hex: str, expected_address: str) -> bool:
    """Verify signature matches expected address."""

def generate_keypair() -> tuple[str, str, str]:
    """Generate new secp256k1 keypair. Returns (private_key_hex, public_key_hex, eth_address)."""
```

#### Permission Scopes (`permissions.py`)

```python
class Scope:
    ANCHOR_CREATE = "anchor:create"
    COMPANY_CREATE = "company:create"
    CHAT_INVOKE = "chat:invoke"
    ADMIN_RESET = "admin:reset"
```

### 5.3 LLM Provider Pipeline (`origraph/providers/`)

**Design Goal:** Adding a new LLM provider = one new file, no changes to existing code.

```python
# origraph/providers/base.py
from typing import Protocol

@dataclass
class GenerateRequest:
    model: str
    messages: list[dict[str, Any]]
    system: str = "You are a helpful assistant."
    max_tokens: int = 2048
    temperature: float = 0.7

@dataclass
class GenerateResponse:
    text: str
    thinking: str = ""
    model: str = ""
    provider: str = ""
    usage: dict[str, int] = field(default_factory=lambda: {"input_tokens": 0, "output_tokens": 0})
    error: str | None = None

class LLMProvider(Protocol):
    """Every LLM provider implements this protocol."""

    @property
    def provider_name(self) -> str: ...

    @property
    def available_models(self) -> list[dict[str, str]]: ...

    async def generate(self, request: GenerateRequest) -> GenerateResponse: ...
```

```python
# origraph/providers/router.py
class ProviderRouter:
    def __init__(self, settings: LLMSettings) -> None:
        self._providers: dict[str, LLMProvider] = {}
        self._register_defaults(settings)

    def _register_defaults(self, settings: LLMSettings) -> None:
        self._providers["fixture"] = FixtureProvider()
        if settings.google_api_key:
            self._providers["google"] = GoogleProvider(settings.google_api_key)
        if settings.minimax_api_key:
            self._providers["minimax"] = MiniMaxProvider(settings.minimax_api_key, settings.minimax_base_url)
        # Bedrock uses IAM — always available if boto3 is installed
        self._providers["bedrock"] = BedrockProvider()

    def list_models(self) -> dict[str, list[dict]]:
        return {name: p.available_models for name, p in self._providers.items() if name != "fixture"}

    async def generate(self, provider: str, request: GenerateRequest) -> GenerateResponse:
        if provider not in self._providers:
            return GenerateResponse(text="", error=f"Unknown provider: {provider}")
        return await self._providers[provider].generate(request)
```

#### Google Provider (`google.py`)

```python
class GoogleProvider:
    """Google GenAI SDK for Gemma 4 models."""

    MODELS = [
        {"id": "gemma-4-27b-it", "name": "Gemma 4 27B (default)"},
        {"id": "gemma-4-12b-it", "name": "Gemma 4 12B"},
        {"id": "gemma-3-27b-it", "name": "Gemma 3 27B"},
    ]

    def __init__(self, api_key: str) -> None:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        self._genai = genai

    @property
    def provider_name(self) -> str:
        return "google"

    @property
    def available_models(self) -> list[dict]:
        return [{"id": m["id"], "name": m["name"], "provider": "google"} for m in self.MODELS]

    async def generate(self, request: GenerateRequest) -> GenerateResponse:
        model = self._genai.GenerativeModel(
            model_name=request.model,
            system_instruction=request.system,
        )
        # Convert messages: "assistant" → "model"
        contents = self._convert_messages(request.messages)
        config = self._genai.types.GenerationConfig(
            max_output_tokens=request.max_tokens,
            temperature=request.temperature,
        )
        resp = model.generate_content(contents, generation_config=config)

        thinking, text = self._extract_parts(resp)
        usage = self._extract_usage(resp)

        return GenerateResponse(
            text=text,
            thinking=thinking,
            model=request.model,
            provider="google",
            usage=usage,
        )
```

#### Fixture Provider (`fixture.py`)

```python
class FixtureProvider:
    """Deterministic responses for testing and demos. No API calls."""

    FIXTURE_TEXT = (
        "Origraph fixture response: this output is deterministic for demo reliability. "
        "It can be watermarked, signed, anchored, and verified without calling external model APIs."
    )

    async def generate(self, request: GenerateRequest) -> GenerateResponse:
        prompt = self._extract_prompt(request.messages)
        text = f"{self.FIXTURE_TEXT}\n\nRequested model: {request.model}.\nPrompt digest: {prompt[:180]}"
        return GenerateResponse(
            text=text,
            thinking="fixture-mode",
            model=request.model,
            provider="fixture",
            usage={"input_tokens": max(1, len(prompt.split())), "output_tokens": max(1, len(text.split()))},
        )
```

### 5.4 Chain Backends (`origraph/chain/`)

```python
# origraph/chain/protocol.py
from typing import Protocol, runtime_checkable

@dataclass(frozen=True)
class ChainReceipt:
    tx_hash: str
    block_num: int
    data_hash: str
    issuer_id: int
    timestamp: str
    solana_tx_signature: str | None = None

@dataclass(frozen=True)
class ChainRecord:
    block_num: int
    prev_hash: str
    tx_hash: str
    data_hash: str
    issuer_id: int
    signature_hex: str
    timestamp: str
    solana_tx_signature: str | None = None

@runtime_checkable
class ChainBackend(Protocol):
    async def anchor(self, data_hash: str, issuer_id: int, signature_hex: str, metadata: dict | None = None) -> ChainReceipt: ...
    async def lookup(self, data_hash: str) -> ChainRecord | None: ...
    async def lookup_tx(self, tx_hash: str) -> ChainRecord | None: ...
    async def verify(self, data_hash: str, tx_hash: str) -> bool: ...
    async def chain_length(self) -> int: ...
    async def validate_chain(self) -> tuple[bool, str]: ...
```

**Note:** All chain methods are `async` in v2. The simulated chain uses `aiosqlite`, the Solana chain uses `httpx` for RPC calls.

#### Simulated Chain (`simulated.py`)

Same linked-list logic as v1 but using `aiosqlite`:
- Genesis `prev_hash`: 64 zero hex chars
- `tx_hash = SHA-256(prev_hash || data_hash || issuer_id || timestamp)`
- Purely local, no gas fees, instant

#### Solana Chain (`solana.py`)

Dual-write strategy:
1. Build compact JSON memo: `{"v":1,"h":"<hash>","i":<issuer>,"s":"<sig_prefix>","t":"<ts>"}`
2. Submit as Memo program instruction to Solana devnet
3. Write to local SQLite with `solana_tx_signature` column
4. If Solana RPC fails → still write to SQLite (signature = `None`), log warning, return receipt

Key implementation details:
- **Memo Program ID:** `MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr`
- **Keypair:** loaded from JSON file (standard `solana-keygen` format) via `Keypair.from_bytes()`
- **Auto-airdrop:** if balance < 0.05 SOL on devnet, request 1 SOL airdrop
- **On-chain verification:** `verify_on_chain(tx_signature)` fetches transaction via RPC, extracts memo from logs

#### Factory (`factory.py`)

```python
async def create_chain(settings: AppSettings) -> ChainBackend:
    if settings.chain_backend == ChainBackendType.SOLANA:
        from origraph.chain.solana import SolanaChain
        return SolanaChain(
            rpc_url=settings.solana.solana_rpc_url,
            keypair_path=settings.solana.solana_keypair_path,
            cluster=settings.solana.solana_cluster,
            db_path=settings.db_path,
        )
    from origraph.chain.simulated import SimulatedChain
    return SimulatedChain(db_path=settings.db_path)
```

### 5.5 Database Layer (`origraph/db/`)

#### Connection Management

```python
# origraph/db/connection.py
import aiosqlite
from contextlib import asynccontextmanager

DB_PRAGMAS = ["PRAGMA journal_mode=WAL", "PRAGMA foreign_keys=ON"]

@asynccontextmanager
async def get_db(db_path: str):
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        for pragma in DB_PRAGMAS:
            await db.execute(pragma)
        try:
            yield db
            await db.commit()
        except Exception:
            await db.rollback()
            raise

async def init_db(db_path: str) -> None:
    """Create tables and run migrations."""
    async with get_db(db_path) as db:
        await db.executescript(SCHEMA)
```

#### Repository Pattern

Each repository is a thin async class:

```python
class CompanyRepository:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    async def create(self, name: str, issuer_id: int, eth_address: str, public_key_hex: str) -> int: ...
    async def get_by_issuer(self, issuer_id: int) -> dict | None: ...
    async def get_by_address(self, eth_address: str) -> dict | None: ...
    async def list_all(self) -> list[dict]: ...
    async def deactivate(self, issuer_id: int) -> None: ...

class ResponseRepository:
    async def save(self, sha256_hash: str, issuer_id: int, signature_hex: str, raw_text: str, watermarked_text: str, metadata: dict) -> int: ...
    async def get_by_hash(self, sha256_hash: str) -> dict | None: ...
    async def list_recent(self, limit: int = 50, offset: int = 0) -> list[dict]: ...
    async def latest(self) -> dict | None: ...

class ChainBlockRepository:
    async def get_by_tx_hash(self, tx_hash: str) -> dict | None: ...
    async def get_by_solana_tx(self, signature: str) -> dict | None: ...
    async def list_blocks(self, limit: int = 50, offset: int = 0) -> list[dict]: ...
    async def get_block(self, block_num: int) -> dict | None: ...
```

### 5.6 Services Layer (`origraph/services/`)

Services orchestrate business logic. They depend on repositories and chain backends via dependency injection (no global imports).

#### ChatService

```python
class ChatService:
    def __init__(self, provider_router: ProviderRouter, watermark_service: WatermarkService) -> None:
        self.router = provider_router
        self.watermark = watermark_service

    def list_models(self) -> dict[str, list[dict]]:
        return self.router.list_models()

    async def generate(self, request: ChatRequest) -> ChatResponse:
        # 1. Dispatch to provider
        gen_request = GenerateRequest(model=request.model, messages=request.messages, ...)
        result = await self.router.generate(request.provider, gen_request)
        if result.error:
            return ChatResponse(error=result.error)

        # 2. Apply watermark if requested
        raw_text = result.text
        watermarked_text = raw_text
        if request.watermark:
            watermarked_text = self.watermark.apply(raw_text, request.wm_params)

        return ChatResponse(
            text=watermarked_text,
            raw_text=raw_text,
            thinking=result.thinking,
            watermarked=request.watermark,
            model=result.model,
            provider=result.provider,
            usage=result.usage,
        )
```

#### AnchorService

```python
class AnchorService:
    def __init__(
        self,
        chain: ChainBackend,
        signing: SigningService,
        company_repo: CompanyRepository,
        response_repo: ResponseRepository,
        chain_repo: ChainBlockRepository,
        proof_builder: ProofBundleBuilder,
    ) -> None: ...

    async def anchor(self, text: str, raw_text: str, signature_hex: str, issuer_id: int, metadata: dict) -> AnchorResponse:
        # 1. Hash text
        data_hash = hash_text(text)

        # 2. Verify ECDSA signature
        company = await self.company_repo.get_by_issuer(issuer_id)
        if not company:
            raise PermissionError("Unknown issuer_id")
        recovered = recover_address(data_hash, signature_hex)
        if recovered.lower() != company["eth_address"].lower():
            raise PermissionError("Signature does not match registered company address")

        # 3. Store response
        await self.response_repo.save(data_hash, issuer_id, signature_hex, raw_text, text, metadata)

        # 4. Anchor to chain
        receipt = await self.chain.anchor(data_hash, issuer_id, signature_hex, metadata)

        # 5. Detect watermark
        watermark_info = Watermarker().detect(text)

        # 6. Build proof bundle
        bundle = self.proof_builder.build(receipt=receipt, company=company, watermark=watermark_info)

        return AnchorResponse(chain_receipt=receipt, proof_bundle=bundle)

    async def verify(self, text: str) -> VerifyResponse:
        data_hash = hash_text(text)
        record = await self.chain.lookup(data_hash)
        watermark_info = Watermarker().detect(text)
        if record is None:
            return VerifyResponse(verified=False, sha256_hash=data_hash, watermark=watermark_info)
        company = await self.company_repo.get_by_issuer(record.issuer_id)
        bundle = self.proof_builder.build(...)
        return VerifyResponse(verified=True, sha256_hash=data_hash, proof_bundle=bundle, watermark=watermark_info)
```

#### ProofBundleBuilder (extracted)

```python
class ProofBundleBuilder:
    """Builds self-verifiable proof bundles. Extracted from AnchorService for testability."""

    def __init__(self, chain_backend: ChainBackendType, solana_cluster: str | None = None, solana_rpc_url: str | None = None) -> None: ...

    def build(self, *, receipt: ChainReceipt, company: dict, watermark: DetectResult, signature_hex: str) -> dict:
        """Build a complete Proof Bundle v2."""
        ...

    @staticmethod
    def bundle_id(payload: dict) -> str:
        """SHA-256 of canonical JSON, prefixed with 'opb2_'."""
        ...
```

### 5.7 API Routers (`origraph/api/`)

Each router is a focused file handling one domain:

```python
# origraph/api/health.py
router = APIRouter(tags=["health"])

@router.get("/api/health")
async def health(settings: AppSettings = Depends(get_settings)) -> HealthResponse: ...
```

```python
# origraph/api/chat.py
router = APIRouter(prefix="/api", tags=["chat"])

@router.get("/models")
async def list_models(chat: ChatService = Depends(get_chat_service)) -> ModelsResponse: ...

@router.post("/chat", dependencies=[Depends(require_permission(Scope.CHAT_INVOKE))])
async def chat(req: ChatRequest, chat: ChatService = Depends(get_chat_service)) -> ChatResponse: ...

@router.post("/detect")
async def detect(req: TextRequest, wm: WatermarkService = Depends(get_watermark_service)) -> DetectResponse: ...

@router.post("/strip", dependencies=[Depends(get_current_user)])
async def strip(req: StripRequest, wm: WatermarkService = Depends(get_watermark_service)) -> StripResponse: ...

@router.post("/apply", dependencies=[Depends(get_current_user)])
async def apply_watermark(req: TextRequest, wm: WatermarkService = Depends(get_watermark_service)) -> ApplyResponse: ...
```

```python
# origraph/api/registry.py
router = APIRouter(prefix="/api", tags=["registry"])

@router.post("/anchor", dependencies=[Depends(require_permission(Scope.ANCHOR_CREATE))])
async def anchor(req: AnchorRequest, svc: AnchorService = Depends(get_anchor_service)) -> AnchorResponse: ...

@router.post("/verify")
async def verify(req: VerifyRequest, svc: AnchorService = Depends(get_anchor_service)) -> VerifyResponse: ...

@router.post("/proof/text")
async def proof_by_text(req: ProofByTextRequest, svc: AnchorService = Depends(get_anchor_service)) -> ProofResponse: ...

@router.get("/proof/tx/{tx_hash}")
async def proof_by_tx(tx_hash: str, svc: AnchorService = Depends(get_anchor_service)) -> ProofResponse: ...

@router.get("/proof/spec")
async def proof_spec() -> ProofSpecResponse: ...
```

```python
# origraph/api/companies.py
router = APIRouter(prefix="/api/companies", tags=["companies"])

@router.post("/", dependencies=[Depends(require_permission(Scope.COMPANY_CREATE))])
async def create(req: CreateCompanyRequest, signing: SigningService = Depends(get_signing_service)) -> CompanyResponse: ...

@router.get("/", dependencies=[Depends(get_current_user)])
async def list_companies(repo: CompanyRepository = Depends(get_company_repo)) -> list[CompanyResponse]: ...
```

```python
# origraph/api/chain.py
router = APIRouter(prefix="/api/chain", tags=["chain"])

@router.get("/status")
async def status(svc: AnchorService = Depends(get_anchor_service)) -> ChainStatusResponse: ...

@router.get("/blocks")
async def blocks(limit: int = 50, offset: int = 0, repo: ChainBlockRepository = Depends(get_chain_repo)) -> list[dict]: ...

@router.get("/blocks/{block_num}")
async def block(block_num: int, repo: ChainBlockRepository = Depends(get_chain_repo)) -> dict: ...
```

```python
# origraph/api/solana.py
router = APIRouter(prefix="/api/solana", tags=["solana"])

@router.get("/verify/{tx_signature}")
async def verify_on_chain(tx_signature: str, svc: AnchorService = Depends(get_anchor_service)) -> SolanaVerifyResponse: ...

@router.get("/balance")
async def balance(svc: AnchorService = Depends(get_anchor_service)) -> SolanaBalanceResponse: ...
```

```python
# origraph/api/demo.py
router = APIRouter(prefix="/api/demo", tags=["demo"])

@router.get("/scenario")
async def scenario(wm: WatermarkService = Depends(get_watermark_service), signing: SigningService = Depends(get_signing_service)) -> DemoScenarioResponse: ...

@router.post("/reset", dependencies=[Depends(require_permission(Scope.ADMIN_RESET))])
async def reset(svc: AnchorService = Depends(get_anchor_service)) -> ResetResponse: ...
```

#### Auth Requirement Matrix

| Endpoint | Auth | Permission |
|---|---|---|
| `GET /api/health` | Public | — |
| `GET /api/models` | Public | — |
| `POST /api/chat` | Required | `chat:invoke` |
| `POST /api/detect` | Public | — |
| `POST /api/strip` | Required | — |
| `POST /api/apply` | Required | — |
| `POST /api/anchor` | Required | `anchor:create` |
| `POST /api/verify` | Public | — |
| `POST /api/proof/text` | Public | — |
| `GET /api/proof/tx/{tx}` | Public | — |
| `GET /api/proof/spec` | Public | — |
| `POST /api/companies` | Required | `company:create` |
| `GET /api/companies` | Required | — |
| `GET /api/chain/*` | Public | — |
| `GET /api/solana/*` | Public | — |
| `GET /api/demo/scenario` | Public | — |
| `POST /api/demo/reset` | Required | `admin:reset` |

### 5.8 Application Factory (`origraph/app.py`)

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    settings = AppSettings()
    await init_db(settings.db_path)

    # Build dependency graph
    company_repo = CompanyRepository(settings.db_path)
    response_repo = ResponseRepository(settings.db_path)
    chain_repo = ChainBlockRepository(settings.db_path)
    chain = await create_chain(settings)
    signing = SigningService(company_repo, admin_secret=settings.registry_admin_secret)
    watermark = WatermarkService()
    provider_router = ProviderRouter(settings.llm)
    proof_builder = ProofBundleBuilder(settings.chain_backend, settings.solana.solana_cluster, settings.solana.solana_rpc_url)
    chat = ChatService(provider_router, watermark)
    anchor = AnchorService(chain, signing, company_repo, response_repo, chain_repo, proof_builder)

    # Store in app.state for dependency injection
    app.state.settings = settings
    app.state.services = ServiceContainer(chat=chat, anchor=anchor, signing=signing, watermark=watermark)
    app.state.repos = RepoContainer(company=company_repo, response=response_repo, chain=chain_repo)

    logger.info("origraph started", chain_backend=settings.chain_backend, demo_mode=settings.demo_mode, auth0=settings.auth.enabled)
    yield
    # Shutdown
    logger.info("origraph shutting down")

def create_app() -> FastAPI:
    app = FastAPI(title="Origraph", version="2.0.0", lifespan=lifespan)

    # Middleware
    app.add_middleware(CORSMiddleware, ...)
    app.add_middleware(StructuredLoggingMiddleware)
    app.add_exception_handler(Exception, global_error_handler)

    # Routers
    app.include_router(health_router)
    app.include_router(chat_router)
    app.include_router(registry_router)
    app.include_router(companies_router)
    app.include_router(chain_router)
    app.include_router(solana_router)
    app.include_router(demo_router)

    # SPA fallback
    if FRONTEND_DIST.exists():
        app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")))
        @app.get("/{path:path}")
        async def spa_fallback(path: str): ...

    return app

app = create_app()
```

### 5.9 Middleware (`origraph/middleware/`)

```python
# origraph/middleware/logging.py
import structlog
import time

class StructuredLoggingMiddleware:
    async def __call__(self, request, call_next):
        start = time.monotonic()
        response = await call_next(request)
        duration = time.monotonic() - start
        structlog.get_logger().info(
            "http_request",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=round(duration * 1000, 1),
        )
        return response
```

```python
# origraph/middleware/errors.py
async def global_error_handler(request, exc):
    """Convert unhandled exceptions to JSON responses with correlation IDs."""
    error_id = uuid4().hex[:8]
    logger.error("unhandled_error", error_id=error_id, exc=str(exc))
    return JSONResponse({"error": str(exc), "error_id": error_id}, status_code=500)
```

---

## 6. Frontend: `origraph-web`

### 6.1 Tech Stack

| Tool | Version | Purpose |
|---|---|---|
| React | 19 | UI framework |
| Vite | 7 | Build tool |
| TypeScript | ~5.9 | Type safety |
| TanStack React Query | 5 | Server state management |
| React Router | 7 | Client-side routing |
| ethers.js | 6 | ECDSA signing in browser |
| @auth0/auth0-react | 2 | Auth0 integration |

### 6.2 API Client Architecture

```typescript
// frontend/src/api/client.ts

type TokenGetter = () => Promise<string>;
let tokenGetter: TokenGetter | null = null;

export function setTokenGetter(fn: TokenGetter): void {
  tokenGetter = fn;
}

async function authHeaders(): Promise<Record<string, string>> {
  if (!tokenGetter) return {};
  try {
    const token = await tokenGetter();
    return { Authorization: `Bearer ${token}` };
  } catch {
    return {};
  }
}

async function request<T>(method: string, path: string, body?: unknown, options?: RequestOptions): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(await authHeaders()),
  };

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), options?.timeout ?? 30_000);

  let lastError: Error | null = null;
  for (let attempt = 0; attempt <= (options?.retries ?? 1); attempt++) {
    try {
      const resp = await fetch(`${BASE_URL}${path}`, {
        method,
        headers,
        body: body ? JSON.stringify(body) : undefined,
        signal: controller.signal,
      });
      clearTimeout(timeout);

      if (!resp.ok) {
        const error = await resp.json().catch(() => ({ detail: resp.statusText }));
        throw new ApiError(resp.status, error.detail ?? "Request failed", error.error_id);
      }
      return resp.json();
    } catch (err) {
      lastError = err as Error;
      if (attempt < (options?.retries ?? 1)) {
        await new Promise(r => setTimeout(r, 1000 * (attempt + 1)));
      }
    }
  }
  throw lastError;
}

export const get = <T>(path: string, opts?: RequestOptions) => request<T>("GET", path, undefined, opts);
export const post = <T>(path: string, body: unknown, opts?: RequestOptions) => request<T>("POST", path, body, opts);
```

```typescript
// frontend/src/api/chat.ts
import { get, post } from "./client";
import { useQuery, useMutation } from "@tanstack/react-query";

export const chatApi = {
  models: () => get<ModelsResponse>("/api/models"),
  generate: (req: ChatRequest) => post<ChatResponse>("/api/chat", req),
  detect: (text: string, wm_params?: WmParams) => post<DetectResponse>("/api/detect", { text, wm_params }),
  strip: (text: string) => post<StripResponse>("/api/strip", { text }),
  apply: (text: string, wm_params?: WmParams) => post<ApplyResponse>("/api/apply", { text, wm_params }),
};

// React Query hooks
export function useModels() {
  return useQuery({ queryKey: ["models"], queryFn: chatApi.models, staleTime: 60_000 });
}

export function useGenerate() {
  return useMutation({ mutationFn: chatApi.generate });
}
```

### 6.3 Auth Integration

```tsx
// frontend/src/auth/AuthProvider.tsx
import { Auth0Provider } from "@auth0/auth0-react";
import { env } from "../config/env";

export function AuthProvider({ children }: { children: React.ReactNode }) {
  // When Auth0 is not configured, render children directly (demo mode)
  if (!env.AUTH0_DOMAIN || !env.AUTH0_CLIENT_ID) {
    return <>{children}</>;
  }

  return (
    <Auth0Provider
      domain={env.AUTH0_DOMAIN}
      clientId={env.AUTH0_CLIENT_ID}
      authorizationParams={{
        redirect_uri: window.location.origin,
        audience: env.AUTH0_AUDIENCE,
        scope: "openid profile email anchor:create company:create chat:invoke",
      }}
      cacheLocation="localstorage"
      useRefreshTokens
    >
      {children}
    </Auth0Provider>
  );
}
```

```tsx
// frontend/src/auth/AuthTokenBridge.tsx
import { useAuth0 } from "@auth0/auth0-react";
import { setTokenGetter } from "../api/client";
import { useEffect } from "react";

export function AuthTokenBridge() {
  const { getAccessTokenSilently, isAuthenticated } = useAuth0();

  useEffect(() => {
    if (isAuthenticated) {
      setTokenGetter(() => getAccessTokenSilently());
    }
  }, [isAuthenticated, getAccessTokenSilently]);

  return null;
}
```

### 6.4 Page Structure

| Route | Page | Auth Required | Description |
|---|---|---|---|
| `/` | Landing | No | Hero + product overview |
| `/dashboard` | Dashboard | No | Health status, chain stats |
| `/generate` | GenerateAndAnchor | Yes | Full pipeline: prompt → generate → sign → anchor |
| `/verify` | Verify | No | Paste text → verify provenance |
| `/companies` | Companies | Yes | Register/view companies |
| `/chain` | Chain | No | Block explorer with Solana links |
| `/demo` | GuidedDemo | Yes | Step-by-step walkthrough |
| `/about` | DemoOverview | No | Architecture explanation |

### 6.5 Key Components

**ModelSelector** — Grouped dropdown with provider categories:
```tsx
<ModelSelector
  provider={provider}
  model={model}
  onProviderChange={setProvider}
  onModelChange={setModel}
  models={modelsQuery.data}
/>
// Renders: Google (Gemma 4) | MiniMax | Bedrock sections
```

**ProofBundleViewer** — Renders proof bundle with:
- Copy-to-clipboard JSON
- Solana Explorer link (when chain_type === "solana")
- Watermark tag details
- ECDSA signature info

**ChainExplorer** — Block list table with:
- Block number, timestamp, data hash (truncated)
- "Solana Tx" column: clickable Explorer link when `solana_tx_signature` present
- Chain validation status badge

**ErrorBoundary** — Catches render errors, shows friendly message + error ID for correlation with backend logs.

---

## 7. Browser Extension: `origraph-extension`

### 7.1 Architecture

Chrome MV3 extension that detects invisible watermarks in web page text.

```
content.ts (content script)
    ├── scanner.ts    → scans DOM text nodes for zero-width patterns
    ├── highlighter.ts → creates visual overlays on detected regions
    └── ← background.ts (service worker) ← popup.ts (popup UI)
```

### 7.2 Detection Algorithm

1. **Text extraction**: Walk DOM tree, extract text from visible `TEXT_NODE` elements
2. **Pattern scan**: Search for `U+2063` (start) ... `U+2064` (end) with exactly 64 bits of `U+200B`/`U+200C` between
3. **CRC-8 validation**: Unpack 64-bit payload, verify CRC-8 checksum
4. **Display**: Overlay green highlight on text containing valid watermarks; show decoded metadata in popup

### 7.3 Rewrite Improvements

| v1 | v2 |
|---|---|
| Raw JavaScript (`content.js`) | TypeScript with proper types |
| Manual DOM walking | TreeWalker API with performance bounds |
| No tests | Playwright E2E tests |
| Global state | Module-scoped, class-based scanner |
| 14 hardcoded Unicode chars | Imported from `shared/constants.ts` |

```typescript
// extension/shared/constants.ts
export const ZWSP = "​";       // Zero-Width Space → binary 0
export const ZWNJ = "‌";       // Zero-Width Non-Joiner → binary 1
export const TAG_START = "⁣";   // Invisible Separator
export const TAG_END = "⁤";     // Invisible Plus
export const TAG_BITS = 64;

// extension/shared/payload.ts
export function crc8(data: Uint8Array): number { ... }
export function unpackPayload(bits: string): { meta: WatermarkMeta; valid: boolean } { ... }
```

```typescript
// extension/content/scanner.ts
export class WatermarkScanner {
  scan(root: Node = document.body): ScanResult[] { ... }
  scanText(text: string): ScanResult[] { ... }
}

export interface ScanResult {
  startIndex: number;
  endIndex: number;
  payload: WatermarkMeta;
  crcValid: boolean;
  rawBits: string;
}
```

### 7.4 Modes

- **Auto-detect**: MutationObserver watches for DOM changes, auto-scans new content
- **Selection scan**: User selects text, right-click → "Scan for watermark"
- **Full page scan**: Popup button triggers complete document scan

---

## 8. Database Schema

### Tables

```sql
-- Companies authorized to sign and anchor provenance records
CREATE TABLE companies (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT    NOT NULL,
    issuer_id       INTEGER NOT NULL UNIQUE,
    eth_address     TEXT    NOT NULL UNIQUE,       -- 0x-prefixed checksum address
    public_key_hex  TEXT    NOT NULL,              -- Uncompressed secp256k1 public key (no 0x)
    active          INTEGER NOT NULL DEFAULT 1,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- LLM responses with raw and watermarked text
CREATE TABLE responses (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    sha256_hash      TEXT    NOT NULL,
    issuer_id        INTEGER NOT NULL,
    signature_hex    TEXT    NOT NULL,
    raw_text         TEXT    NOT NULL,
    watermarked_text TEXT    NOT NULL,
    metadata_json    TEXT    NOT NULL DEFAULT '{}',
    created_at       TEXT    NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (issuer_id) REFERENCES companies(issuer_id)
);
CREATE INDEX idx_responses_hash ON responses(sha256_hash);

-- Hash-chain of anchored provenance records
CREATE TABLE chain_blocks (
    block_num             INTEGER PRIMARY KEY AUTOINCREMENT,
    prev_hash             TEXT    NOT NULL,
    tx_hash               TEXT    NOT NULL UNIQUE,
    data_hash             TEXT    NOT NULL,
    issuer_id             INTEGER NOT NULL,
    signature_hex         TEXT    NOT NULL,
    payload_json          TEXT    NOT NULL DEFAULT '{}',
    timestamp             TEXT    NOT NULL DEFAULT (datetime('now')),
    solana_tx_signature   TEXT    DEFAULT NULL       -- Solana devnet tx signature (base58)
);
CREATE INDEX idx_chain_data_hash ON chain_blocks(data_hash);
CREATE INDEX idx_chain_solana_tx ON chain_blocks(solana_tx_signature);
```

### Migrations

Use Alembic for schema migrations. Initial migration creates all three tables. Future migrations are additive (new columns, indexes).

---

## 9. API Contract

### Full Endpoint Inventory

#### Health & Models
```
GET  /api/health                    → HealthResponse
GET  /api/models                    → { google: Model[], minimax: Model[], bedrock: Model[] }
```

#### Chat & Watermark
```
POST /api/chat                      → ChatResponse          [auth: chat:invoke]
POST /api/detect                    → DetectResponse         [public]
POST /api/strip                     → StripResponse          [auth: any]
POST /api/apply                     → ApplyResponse          [auth: any]
```

#### Registry
```
POST /api/anchor                    → AnchorResponse         [auth: anchor:create]
POST /api/verify                    → VerifyResponse         [public]
POST /api/proof/text                → ProofResponse          [public]
GET  /api/proof/tx/{tx_hash}        → ProofResponse          [public]
GET  /api/proof/spec                → ProofSpecResponse      [public]
```

#### Companies
```
POST /api/companies                 → CompanyResponse        [auth: company:create]
GET  /api/companies                 → CompanyResponse[]      [auth: any]
```

#### Chain
```
GET  /api/chain/status              → ChainStatusResponse    [public]
GET  /api/chain/blocks?limit&offset → ChainBlock[]           [public]
GET  /api/chain/blocks/{block_num}  → ChainBlock             [public]
```

#### Solana
```
GET  /api/solana/verify/{tx_sig}    → SolanaVerifyResponse   [public]
GET  /api/solana/balance            → SolanaBalanceResponse   [public]
```

#### Demo
```
GET  /api/demo/scenario             → DemoScenarioResponse   [public]
POST /api/demo/reset                → ResetResponse          [auth: admin:reset]
```

#### Responses
```
GET  /api/responses?limit&offset    → Response[]             [public]
GET  /api/responses/latest          → Response               [public]
```

### Key Response Shapes

```typescript
interface HealthResponse {
  status: "ok";
  demo_mode: "live" | "fixture";
  chain_backend: "simulated" | "solana";
  solana_cluster: string | null;
  auth0_enabled: boolean;
  google_api_key_configured: boolean;
  minimax_api_key_configured: boolean;
  chain: { length: number; valid: boolean; message: string };
}

interface ChatResponse {
  text: string;           // Watermarked text (if watermark=true)
  raw_text: string;       // Original LLM output
  thinking: string;       // Model's thinking (if available)
  watermarked: boolean;
  model: string;
  provider: string;
  usage: { input_tokens: number; output_tokens: number };
  error?: string;
}

interface AnchorResponse {
  verified_signer: string;
  eth_address: string;
  sha256_hash: string;
  chain_receipt: ChainReceipt;
  proof_bundle_v2: ProofBundleV2;
}

interface VerifyResponse {
  verified: boolean;
  sha256_hash: string;
  issuer_id?: number;
  company?: string;
  eth_address?: string;
  block_num?: number;
  tx_hash?: string;
  timestamp?: string;
  watermark: WatermarkInfo;
  proof_bundle_v2?: ProofBundleV2;
  reason?: string;          // When verified=false
}
```

---

## 10. Auth0 Integration

### Architecture

```
Human User (SPA)                    AI Agent (M2M)
     |                                    |
     | Authorization Code + PKCE          | Client Credentials
     v                                    v
  Auth0 Universal Login              POST /oauth/token
     |                                    |
     | Access Token (JWT)                 | Access Token (JWT)
     v                                    v
  +-------------------------------------------------+
  |              FastAPI Backend                     |
  |  get_current_user() → decode JWT → Identity      |
  |  require_permission("anchor:create") → check     |
  |                                                  |
  |  When AUTH0_DOMAIN is empty:                     |
  |    → return DEMO_IDENTITY (all permissions)     |
  +-------------------------------------------------+
```

### Auth0 Tenant Configuration

Created via `scripts/setup_auth0.sh`:

1. **API Resource Server**
   - Identifier: `https://api.origraph.io`
   - Signing: RS256
   - Scopes: `anchor:create`, `company:create`, `chat:invoke`, `admin:reset`

2. **SPA Application** (for React frontend)
   - Type: Single Page Application
   - Grant types: Authorization Code, Implicit, Refresh Token
   - Callbacks: `http://localhost:5173`, `http://localhost:5050`
   - Token endpoint auth: None (PKCE)

3. **M2M Application** (for AI agents)
   - Type: Non-Interactive
   - Grant types: Client Credentials
   - Authorized scopes: `anchor:create`, `chat:invoke`

### JWT Structure

```json
{
  "iss": "https://origraph.us.auth0.com/",
  "sub": "auth0|abc123",
  "aud": "https://api.origraph.io",
  "iat": 1714000000,
  "exp": 1714086400,
  "scope": "openid profile email anchor:create company:create chat:invoke",
  "permissions": ["anchor:create", "company:create", "chat:invoke"],
  "gty": "client-credentials",                           // M2M only
  "https://origraph.io/issuer_id": 42,                  // Custom claim
  "https://origraph.io/email": "agent@company.com"      // Custom claim
}
```

### JWKS Caching

```python
class JWKSCache:
    """Caches Auth0 JWKS for 1 hour. Refetches on kid mismatch (key rotation)."""

    def __init__(self, domain: str, ttl: int = 3600):
        self._url = f"https://{domain}/.well-known/jwks.json"
        self._cache: dict = {}
        self._fetched_at: float = 0
        self._ttl = ttl

    async def get_signing_key(self, kid: str) -> dict:
        if self._is_stale() or not self._find_key(kid):
            await self._refresh()
        key = self._find_key(kid)
        if not key:
            raise HTTPException(401, "Signing key not found")
        return key
```

### Graceful Degradation

When `AUTH0_DOMAIN` is empty (local dev, fixture mode):
- All `get_current_user` calls return `DEMO_IDENTITY` with all permissions
- No JWKS fetch, no JWT decode
- Frontend skips Auth0Provider, shows no login button
- All endpoints work as if fully authorized

---

## 11. Solana Anchoring

### Memo Program Transaction

```
+------------------+
| Transaction      |
|  Instructions:   |
|    [0] Memo      |
|      program_id: MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr
|      accounts:   [payer (signer, writable)]
|      data:       UTF-8 encoded JSON memo
+------------------+
```

### Memo Payload Format

```json
{"v":1,"h":"a1b2c3...","i":42,"s":"0x1234567890abcdef1234567890abcdef12345678","t":"2026-04-25T12:00:00+00:00"}
```

| Field | Description | Size |
|---|---|---|
| `v` | Protocol version | 1 byte |
| `h` | SHA-256 data hash | 64 chars |
| `i` | Issuer ID | 1-4 digits |
| `s` | Signature prefix (first 40 chars) | 40 chars |
| `t` | ISO-8601 timestamp | ~25 chars |

Total: ~145 bytes (well within Memo's ~566 byte limit).

### Dual-Write Strategy

```
AnchorService.anchor()
    |
    +--> SolanaChain.anchor()
    |      |
    |      +--> [1] Build memo JSON
    |      +--> [2] Create Memo instruction
    |      +--> [3] Sign transaction with keypair
    |      +--> [4] Send to Solana RPC (confirmed commitment)
    |      |         |
    |      |         +--> Success: solana_tx_signature = "5abc..."
    |      |         +--> Failure: solana_tx_signature = None, log warning
    |      |
    |      +--> [5] Insert into SQLite chain_blocks
    |      |         (always happens, regardless of Solana success)
    |      |
    |      +--> [6] Return ChainReceipt
    |                  tx_hash = solana_tx_signature || sqlite_tx_hash
    |                  solana_tx_signature = "5abc..." | None
```

### Proof Bundle with Solana Anchors

When chain_backend=solana and `solana_tx_signature` is present:

```json
{
  "anchors": [{
    "type": "solana",
    "network": "solana-devnet",
    "tx_signature": "5abc...",
    "block_num": 42,
    "timestamp": "2026-04-25T12:00:00+00:00",
    "data_hash": "a1b2c3..."
  }],
  "verification_hints": {
    "chain_type": "solana",
    "cluster": "devnet",
    "rpc_urls": ["https://api.devnet.solana.com"],
    "explorer_url": "https://explorer.solana.com/tx/5abc...?cluster=devnet",
    "memo_program": "MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr"
  }
}
```

### On-Chain Verification

```python
async def verify_on_chain(self, tx_signature: str) -> dict:
    """Fetch transaction from Solana RPC, extract memo, verify data."""
    sig = Signature.from_string(tx_signature)
    resp = self.client.get_transaction(sig, encoding="jsonParsed", max_supported_transaction_version=0)

    if resp.value is None:
        return {"verified": False, "reason": "Transaction not found"}

    # Extract memo from log messages
    memo_data = self._extract_memo_from_logs(resp.value)
    return {
        "verified": True,
        "tx_signature": tx_signature,
        "slot": resp.value.slot,
        "memo_data": memo_data,
        "explorer_url": f"https://explorer.solana.com/tx/{tx_signature}?cluster={self.cluster}",
    }
```

---

## 12. LLM Provider Pipeline

### Provider Registry

```python
# Providers are registered at startup based on available API keys
class ProviderRouter:
    _providers = {
        "google":  GoogleProvider,    # Gemma 4 (default)
        "minimax": MiniMaxProvider,   # MiniMax M2.x via Anthropic SDK
        "bedrock": BedrockProvider,   # AWS Bedrock Converse API
        "fixture": FixtureProvider,   # Deterministic (DEMO_MODE=fixture)
    }
```

### Model Catalog

```python
# Google (default for demo)
GOOGLE_MODELS = [
    {"id": "gemma-4-27b-it", "name": "Gemma 4 27B (default)"},
    {"id": "gemma-4-12b-it", "name": "Gemma 4 12B"},
    {"id": "gemma-3-27b-it", "name": "Gemma 3 27B"},
]

# MiniMax
MINIMAX_MODELS = [
    {"id": "MiniMax-M2.5", "name": "MiniMax M2.5"},
    {"id": "MiniMax-M2.5-highspeed", "name": "MiniMax M2.5 Highspeed"},
    {"id": "MiniMax-M2.1", "name": "MiniMax M2.1"},
    {"id": "MiniMax-M2.1-highspeed", "name": "MiniMax M2.1 Highspeed"},
    {"id": "MiniMax-M2", "name": "MiniMax M2"},
]

# Bedrock
BEDROCK_MODELS = [
    {"id": "anthropic.claude-sonnet-4-6", "name": "Claude Sonnet 4.6"},
    {"id": "anthropic.claude-opus-4-6-v1", "name": "Claude Opus 4.6"},
    {"id": "deepseek.v3.2", "name": "DeepSeek V3.2"},
    {"id": "amazon.nova-pro-v1:0", "name": "Nova Pro"},
    # ... etc
]
```

### Message Conversion

Each provider has different message format requirements:

| SDK | Role for AI response | Content format |
|---|---|---|
| Google GenAI | `"model"` | `{"role": "model", "parts": [{"text": "..."}]}` |
| Anthropic (MiniMax) | `"assistant"` | `{"role": "assistant", "content": "..."}` |
| Bedrock Converse | `"assistant"` | `{"role": "assistant", "content": [{"text": "..."}]}` |

The `ProviderProtocol` standardizes input/output, each provider handles conversion internally.

### Pipeline: Generate → Watermark → Return

```
ChatRequest { model, provider, messages, watermark, wm_params }
    |
    +--> [fixture?] → FixtureProvider.generate() (no API call)
    |
    +--> [live] → ProviderRouter.dispatch(provider, model, messages)
    |       |
    |       +--> GoogleProvider.generate()
    |       +--> MiniMaxProvider.generate()
    |       +--> BedrockProvider.generate()
    |
    +--> GenerateResponse { text, thinking, usage }
    |
    +--> [watermark=true?]
    |       |
    |       +--> Watermarker(issuer_id, model_id, ...).apply(text)
    |       +--> Invisible Unicode tags injected every ~160 tokens
    |
    +--> ChatResponse { text, raw_text, watermarked, model, provider, usage }
```

---

## 13. Proof Bundle v2 Specification

### Format

```json
{
  "spec": "origraph-proof-bundle/v2",
  "bundle_id": "opb2_<sha256_of_canonical_json>",
  "hashing": {
    "algorithm": "sha256",
    "text_hash": "<64-char-hex>",
    "input_encoding": "utf-8",
    "normalization": "none"
  },
  "issuer": {
    "issuer_id": 42,
    "name": "Acme Corp",
    "eth_address": "0x1234...abcd",
    "public_key_hex": "04abcd...ef01"
  },
  "signature": {
    "scheme": "eip191_personal_sign",
    "signed_payload": "sha256:<text_hash>",
    "signature_hex": "0x...",
    "recoverable_address": true
  },
  "watermark": {
    "detected": true,
    "tag_count": 3,
    "valid_count": 3,
    "invalid_count": 0,
    "payloads": [
      {
        "schema_version": 1,
        "issuer_id": 42,
        "model_id": 1001,
        "model_version_id": 1,
        "key_id": 1,
        "crc_valid": true,
        "raw_payload_hex": "0x1002a03e900010f"
      }
    ]
  },
  "anchors": [
    {
      "type": "solana",
      "network": "solana-devnet",
      "tx_signature": "5abc...",
      "block_num": 42,
      "timestamp": "2026-04-25T12:00:00+00:00",
      "data_hash": "<64-char-hex>"
    }
  ],
  "verification_hints": {
    "chain_type": "solana",
    "cluster": "devnet",
    "rpc_urls": ["https://api.devnet.solana.com"],
    "explorer_url": "https://explorer.solana.com/tx/5abc...?cluster=devnet",
    "memo_program": "MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr"
  }
}
```

### Changes from v1

| Field | v1 | v2 |
|---|---|---|
| `spec` | `origraph-proof-bundle/v1` | `origraph-proof-bundle/v2` |
| `bundle_id` prefix | `opb1_` | `opb2_` |
| `anchors[].type` | `"simulated_chain"` only | `"simulated_chain"` or `"solana"` |
| `verification_hints` | Static contract fields | Dynamic based on chain type |
| `watermark.payloads` | Flat list | Unchanged (was already good) |

### Bundle ID Computation

```python
def bundle_id(payload: dict) -> str:
    # Remove bundle_id from payload before hashing (it's self-referential)
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return f"opb2_{digest}"
```

---

## 14. Configuration & Environment

### `.env.example`

```bash
# === Core ===
DEMO_MODE=live                              # live | fixture
REGISTRY_ADMIN_SECRET=dev-admin-secret      # Fallback admin auth (when Auth0 disabled)

# === Server ===
APP_HOST=127.0.0.1
APP_PORT=5050
CORS_ORIGINS=http://localhost:5173,http://localhost:5050
LOG_LEVEL=info
LOG_FORMAT=pretty                           # pretty | json

# === Database ===
DB_PATH=data/origraph.db

# === LLM Providers ===
GOOGLE_API_KEY=                             # Required for Gemma 4 in live mode
MINIMAX_API_KEY=                            # Optional
MINIMAX_BASE_URL=https://api.minimax.io/anthropic

# === Chain Backend ===
CHAIN_BACKEND=simulated                     # simulated | solana
SOLANA_RPC_URL=https://api.devnet.solana.com
SOLANA_KEYPAIR_PATH=                        # Required when CHAIN_BACKEND=solana
SOLANA_CLUSTER=devnet

# === Auth0 (Optional) ===
AUTH0_DOMAIN=                               # e.g., origraph.us.auth0.com
AUTH0_AUDIENCE=https://api.origraph.io
AUTH0_SPA_CLIENT_ID=                        # For frontend
```

### `frontend/.env.example`

```bash
VITE_AUTH0_DOMAIN=
VITE_AUTH0_CLIENT_ID=
VITE_AUTH0_AUDIENCE=https://api.origraph.io
VITE_API_BASE_URL=http://localhost:5050
```

### Feature Flags (derived from config)

| Flag | Condition | Effect |
|---|---|---|
| Fixture mode | `DEMO_MODE=fixture` | All chat → FixtureProvider, no API keys needed |
| Auth0 enabled | `AUTH0_DOMAIN` is set | JWT validation on protected routes |
| Auth0 disabled | `AUTH0_DOMAIN` empty | All routes return demo identity |
| Solana active | `CHAIN_BACKEND=solana` | Anchors go to Solana + SQLite |
| Solana inactive | `CHAIN_BACKEND=simulated` | Anchors go to SQLite only |
| Google available | `GOOGLE_API_KEY` set | Google/Gemma models available |
| MiniMax available | `MINIMAX_API_KEY` set | MiniMax models available |

---

## 15. Bootstrap & DevOps

### `Makefile`

```makefile
.PHONY: install dev test lint build bootstrap

install:                          ## Install all dependencies
	uv sync
	cd frontend && npm ci

dev:                              ## Start backend + frontend dev servers
	scripts/dev.sh

test:                             ## Run all tests
	uv run pytest tests/ -v --tb=short
	cd frontend && npm test

lint:                             ## Lint Python + TypeScript
	uv run ruff check src/ packages/ tests/
	uv run mypy src/ packages/
	cd frontend && npm run lint

build:                            ## Build frontend for production
	cd frontend && npm run build

bootstrap:                        ## Full setup from scratch
	scripts/bootstrap.sh

bootstrap-solana:                 ## Setup + Solana devnet
	scripts/bootstrap.sh --with-solana

bootstrap-auth0:                  ## Setup + Auth0 tenant
	scripts/bootstrap.sh --with-auth0

bootstrap-all:                    ## Setup + Solana + Auth0
	scripts/bootstrap.sh --with-solana --with-auth0
```

### `scripts/bootstrap.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail

# 1. Check Python >= 3.11
# 2. Check Node >= 20
# 3. uv sync (creates .venv, installs all packages)
# 4. npm ci && npm run build (frontend)
# 5. Copy .env.example → .env (if not exists)
# 6. Initialize database
# 7. Optional: --with-solana → scripts/setup_solana.sh
# 8. Optional: --with-auth0 → scripts/setup_auth0.sh
# 9. Print next steps
```

### `scripts/setup_solana.sh`

1. Check/install Solana CLI
2. Set devnet: `solana config set --url devnet`
3. Generate keypair: `solana-keygen new --outfile data/solana-keypair.json --no-bip39-passphrase`
4. Airdrop 2 SOL: `solana airdrop 2 <pubkey> --url devnet`
5. Write to `.env`: `CHAIN_BACKEND=solana`, `SOLANA_KEYPAIR_PATH=data/solana-keypair.json`

### `scripts/setup_auth0.sh`

1. Prompt for Auth0 domain and Management API token
2. Create API resource server (`https://api.origraph.io`, RS256, 4 scopes)
3. Create SPA application (PKCE, localhost callbacks)
4. Create M2M application (client_credentials, authorized against API)
5. Write to `.env`: `AUTH0_DOMAIN`, `AUTH0_AUDIENCE`, `AUTH0_SPA_CLIENT_ID`
6. Write to `frontend/.env`: `VITE_AUTH0_DOMAIN`, `VITE_AUTH0_CLIENT_ID`, `VITE_AUTH0_AUDIENCE`
7. Print M2M test curl command

### Docker

```dockerfile
# docker/Dockerfile
FROM python:3.12-slim AS backend
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN pip install uv && uv sync --frozen
COPY packages/ packages/
COPY src/ src/

FROM node:20-slim AS frontend
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM backend AS runtime
COPY --from=frontend /app/frontend/dist /app/frontend/dist
EXPOSE 5050
CMD ["uv", "run", "uvicorn", "origraph.app:app", "--host", "0.0.0.0", "--port", "5050"]
```

---

## 16. Testing Strategy

### Unit Tests

| Module | What to test | Mocking |
|---|---|---|
| `packages/watermark` | apply/detect/strip, CRC-8, payload pack/unpack, edge cases (empty text, short text, Unicode) | None (pure logic) |
| `origraph/auth/ecdsa.py` | sign, verify, recover, keypair generation | None (pure crypto) |
| `origraph/auth/jwt.py` | decode valid token, expired token, bad audience, missing kid, demo fallback | Mock JWKS endpoint |
| `origraph/providers/*` | Each provider's message conversion, error handling | Mock SDK responses |
| `origraph/chain/simulated.py` | anchor, lookup, verify, chain validation, genesis | In-memory SQLite |
| `origraph/chain/solana.py` | anchor success, RPC failure fallback, verify_on_chain | Mock Solana Client |
| `origraph/services/proof_builder.py` | Bundle construction, bundle_id determinism | None |

### Integration Tests

```python
# tests/conftest.py
import pytest
from httpx import AsyncClient, ASGITransport
from origraph.app import create_app

@pytest.fixture
async def app():
    """Create test app with fixture mode and in-memory DB."""
    os.environ["DEMO_MODE"] = "fixture"
    os.environ["DB_PATH"] = ":memory:"
    os.environ["AUTH0_DOMAIN"] = ""  # Demo mode (no auth)
    app = create_app()
    yield app

@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
```

```python
# tests/integration/test_api_anchor.py
async def test_full_pipeline(client):
    """Generate → sign → anchor → verify → proof."""
    # 1. Create company
    resp = await client.post("/api/companies", json={"name": "Test Corp", "admin_secret": "dev-admin-secret"})
    assert resp.status_code == 200
    company = resp.json()

    # 2. Generate text
    resp = await client.post("/api/chat", json={"messages": [{"role": "user", "content": "Hello"}]})
    assert resp.status_code == 200
    text = resp.json()["text"]

    # 3. Sign (test helper)
    data_hash = sha256(text.encode()).hexdigest()
    signature = sign_hash(data_hash, company["private_key_hex"])

    # 4. Anchor
    resp = await client.post("/api/anchor", json={
        "text": text,
        "raw_text": resp.json()["raw_text"],
        "signature_hex": signature,
        "issuer_id": company["issuer_id"],
    })
    assert resp.status_code == 200
    assert resp.json()["proof_bundle_v2"]["spec"] == "origraph-proof-bundle/v2"

    # 5. Verify
    resp = await client.post("/api/verify", json={"text": text})
    assert resp.status_code == 200
    assert resp.json()["verified"] is True
```

### E2E Tests

```python
# tests/e2e/test_extension.py
from playwright.sync_api import sync_playwright

def test_extension_detects_watermark():
    """Load extension, inject watermarked text, verify detection overlay."""
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            "", headless=True,
            args=[f"--load-extension={EXTENSION_PATH}", "--disable-extensions-except={EXTENSION_PATH}"]
        )
        page = context.new_page()
        page.set_content(f"<p>{watermarked_text}</p>")
        page.wait_for_selector(".origraph-detected")
        badge = page.query_selector(".origraph-badge")
        assert badge is not None
```

### Coverage Targets

| Area | Target |
|---|---|
| Watermark library | 100% |
| Auth (JWT + ECDSA) | 95% |
| Services | 90% |
| API endpoints | 90% |
| Chain backends | 85% |
| Frontend (vitest) | 70% |
| Extension (Playwright) | 60% |

---

## 17. Migration Path

### Phase 1: Scaffold (Day 1)

- [ ] Create new repo with v2 directory structure
- [ ] Set up `pyproject.toml` with uv, all dependencies
- [ ] Copy `packages/watermark/` from `invisible-text-watermark/src/`
- [ ] Set up frontend with Vite 7 + React 19 + TypeScript

### Phase 2: Core Backend (Day 1-2)

- [ ] `origraph/config/` — Pydantic Settings with grouped sub-models
- [ ] `origraph/auth/ecdsa.py` — port from `registry/auth.py`
- [ ] `origraph/auth/jwt.py` — port from `app/auth.py`, make JWKS fetch async
- [ ] `origraph/db/` — aiosqlite connection, repositories
- [ ] `origraph/chain/protocol.py` — Protocol + dataclasses
- [ ] `origraph/chain/simulated.py` — async SimulatedChain
- [ ] Unit tests for all above

### Phase 3: Services + Providers (Day 2-3)

- [ ] `origraph/providers/` — base, router, google, minimax, bedrock, fixture
- [ ] `origraph/services/` — ChatService, AnchorService, SigningService, WatermarkService, ProofBundleBuilder
- [ ] `origraph/api/` — all routers with auth dependencies
- [ ] `origraph/app.py` — lifespan factory
- [ ] Integration tests for all API endpoints

### Phase 4: Solana Chain (Day 3)

- [ ] `origraph/chain/solana.py` — async SolanaChain with httpx
- [ ] `origraph/api/solana.py` — verify/balance endpoints
- [ ] `scripts/setup_solana.sh`
- [ ] Integration tests (mocked RPC)

### Phase 5: Frontend (Day 3-4)

- [ ] API client with retry + auth headers
- [ ] Auth0 integration (conditional provider)
- [ ] All pages ported with cleaner component structure
- [ ] Vitest unit tests for hooks and API client

### Phase 6: Extension (Day 4)

- [ ] Port content.js → TypeScript
- [ ] Shared payload.ts (port of payload.py)
- [ ] Playwright E2E tests

### Phase 7: Polish (Day 5)

- [ ] Structured logging (structlog)
- [ ] Docker build
- [ ] Bootstrap scripts
- [ ] Final test pass, coverage check
- [ ] Documentation

---

## Dependencies

### Python (`pyproject.toml`)

```toml
[project]
name = "origraph"
version = "2.0.0"
requires-python = ">=3.11"
dependencies = [
    # Web framework
    "fastapi>=0.115",
    "uvicorn[standard]>=0.34",
    "python-dotenv>=1.0",
    "pydantic>=2.10",
    "pydantic-settings>=2.7",

    # Database
    "aiosqlite>=0.21",

    # Auth
    "python-jose[cryptography]>=3.3",
    "httpx>=0.28",

    # Crypto (ECDSA)
    "eth-account>=0.13",
    "eth-keys>=0.6",

    # LLM Providers
    "google-generativeai>=0.8",
    "anthropic>=0.42",
    "boto3>=1.35",

    # Solana (optional, installed via extra)
    # "solana>=0.35",
    # "solders>=0.25",

    # Logging
    "structlog>=24.4",
]

[project.optional-dependencies]
solana = ["solana>=0.35", "solders>=0.25"]
dev = [
    "pytest>=8.3",
    "pytest-asyncio>=0.24",
    "httpx>=0.28",           # For TestClient
    "ruff>=0.8",
    "mypy>=1.13",
    "alembic>=1.14",
]
```

### Frontend (`package.json`)

```json
{
  "dependencies": {
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "react-router": "^7.0.0",
    "@tanstack/react-query": "^5.0.0",
    "ethers": "^6.13.0",
    "@auth0/auth0-react": "^2.2.4"
  },
  "devDependencies": {
    "vite": "^7.0.0",
    "typescript": "~5.9.0",
    "@types/react": "^19.0.0",
    "vitest": "^3.0.0",
    "@testing-library/react": "^16.0.0",
    "playwright": "^1.50.0"
  }
}
```

---

## Summary

This rewrite transforms Origraph from a hackathon prototype into a production-grade platform:

- **One monorepo** with clear boundaries (`packages/watermark`, `src/origraph`, `frontend`, `extension`)
- **Async-first backend** with aiosqlite, structured logging, proper error handling
- **Protocol-driven extensibility** — add new LLM providers or chain backends without touching existing code
- **Auth0 as a first-class feature** with graceful degradation to demo mode
- **Solana anchoring as a first-class feature** with dual-write reliability
- **Gemma 4 as the default LLM** with multi-provider support
- **Comprehensive test suite** covering unit, integration, and E2E
- **One-command bootstrap** with optional integrations via flags
