# Vellum v2

> Provenance-tracking platform for AI-generated text. Identity via Auth0, integrity via invisible
> Unicode watermarks, timestamping via on-chain anchoring.

## Quick Start

```bash
# Full bootstrap (creates .venv, installs everything, initializes DB)
make bootstrap

# Or step by step
make install        # uv sync + npm ci
cp .env.example .env
make dev            # backend + frontend in parallel
```

Open <http://localhost:5173> for the SPA, <http://localhost:5050/api/health> for the API.

## Architecture

```
React SPA  ─┬─►  vellum-server (FastAPI)  ─┬─►  Auth0
            │                                ├─►  Solana Devnet (memo program)
Extension  ─┘                                └─►  SQLite (aiosqlite)
```

See [REWRITE_SPEC.md](REWRITE_SPEC.md) for the full design.

## Project Layout

| Path | Purpose |
|---|---|
| `packages/watermark/` | Pure-Python invisible-watermark library |
| `src/vellum/` | FastAPI backend (config, auth, services, providers, chain, db, api) |
| `frontend/` | React 19 + Vite SPA |
| `extension/` | Chrome MV3 extension (TypeScript) |
| `tests/` | Pytest suites: unit, integration, e2e |
| `scripts/` | Bootstrap and dev scripts |

## Common Commands

```bash
make dev              # backend + frontend
make test             # full test suite
make lint             # ruff + mypy + eslint
make build            # production frontend build
make bootstrap-solana # full setup + Solana devnet keypair
make bootstrap-auth0  # full setup + Auth0 tenant
```

## Configuration

All settings come from environment variables (see `.env.example`). Empty `AUTH0_DOMAIN` enables
demo mode (no auth). `DEMO_MODE=fixture` swaps live LLM calls for deterministic responses.

## DigitalOcean Deployment

The repo includes a GitHub Actions workflow for DigitalOcean App Platform. It builds a container
image with the Vite frontend and FastAPI backend, then deploys it through DigitalOcean Container
Registry.

See [`docs/digitalocean-deploy.md`](docs/digitalocean-deploy.md) for required GitHub secrets and
variables.

## Feature Notes

See [`docs/features.md`](docs/features.md) for the redesigned Studio/Ledger UI,
Auth0 agent action flow, browser wallet proof model, DigitalOcean deployment
status, and Solana readiness notes.

## License

MIT
