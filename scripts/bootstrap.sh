#!/usr/bin/env bash
# Veritext bootstrap — one-shot full setup
set -euo pipefail

WITH_SOLANA=0
WITH_AUTH0=0
for arg in "$@"; do
    case "$arg" in
        --with-solana) WITH_SOLANA=1 ;;
        --with-auth0)  WITH_AUTH0=1  ;;
    esac
done

echo "==> Veritext bootstrap"
command -v python3 >/dev/null || { echo "Python 3.11+ required"; exit 1; }
command -v node    >/dev/null || { echo "Node 20+ required"; exit 1; }
command -v uv      >/dev/null || { echo "Installing uv..."; curl -LsSf https://astral.sh/uv/install.sh | sh; }

echo "==> Python dependencies (uv sync)"
uv sync

echo "==> Frontend dependencies"
(cd frontend && npm ci)

echo "==> Extension dependencies"
(cd extension && npm ci) || true

if [ ! -f .env ]; then
    echo "==> Creating .env from .env.example"
    cp .env.example .env
fi
if [ ! -f frontend/.env ]; then
    cp frontend/.env.example frontend/.env
fi

echo "==> Initializing database"
mkdir -p data
uv run python -c "import asyncio; from veritext.db.connection import init_db; asyncio.run(init_db())" || true

if [ "$WITH_SOLANA" -eq 1 ]; then
    bash scripts/setup_solana.sh
fi
if [ "$WITH_AUTH0" -eq 1 ]; then
    bash scripts/setup_auth0.sh
fi

echo
echo "==> Done. Next:"
echo "    make dev      # start backend + frontend"
echo "    make test     # run tests"
