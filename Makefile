.PHONY: install dev test test-unit test-integration test-adversarial lint build bootstrap bootstrap-solana bootstrap-auth0 bootstrap-all clean help

help:
	@echo "Veritext — make targets:"
	@echo "  install            Install all Python + Node dependencies"
	@echo "  dev                Start backend (5050) + frontend (5173) dev servers"
	@echo "  test               Run all Python + frontend tests"
	@echo "  test-unit          Unit tests only"
	@echo "  test-integration   Integration tests only"
	@echo "  test-adversarial   Adversarial test suite (writes adversarial_report.json)"
	@echo "  lint               Ruff + mypy + eslint"
	@echo "  build              Build frontend production bundle"
	@echo "  bootstrap          One-shot full setup"
	@echo "  bootstrap-solana   Setup + Solana devnet"
	@echo "  bootstrap-auth0    Setup + Auth0 tenant"
	@echo "  bootstrap-all      Setup + Solana + Auth0"
	@echo "  clean              Remove build artifacts and venv"

install:
	uv sync
	cd frontend && npm ci
	cd extension && npm ci

dev:
	bash scripts/dev.sh

test:
	uv run pytest tests/ -v --tb=short
	cd frontend && npm test --silent --run

test-unit:
	uv run pytest tests/unit -v

test-integration:
	uv run pytest tests/integration -v

test-adversarial:
	uv run pytest tests/adversarial -v

lint:
	uv run ruff check src/ packages/ tests/
	uv run mypy src/ packages/ || true
	cd frontend && npm run lint || true

build:
	cd frontend && npm run build

bootstrap:
	bash scripts/bootstrap.sh

bootstrap-solana:
	bash scripts/bootstrap.sh --with-solana

bootstrap-auth0:
	bash scripts/bootstrap.sh --with-auth0

bootstrap-all:
	bash scripts/bootstrap.sh --with-solana --with-auth0

clean:
	rm -rf .venv frontend/dist frontend/node_modules extension/node_modules .pytest_cache .ruff_cache .mypy_cache **/__pycache__
