.PHONY: install dev test lint build bootstrap bootstrap-solana bootstrap-auth0 bootstrap-all clean

install:                          ## Install all dependencies
	uv sync
	cd frontend && npm ci

dev:                              ## Start backend + frontend dev servers
	bash scripts/dev.sh

test:                             ## Run all tests
	uv run pytest tests/ -v --tb=short
	cd frontend && npm test --silent || true

test-backend:                     ## Run backend tests only
	uv run pytest tests/ -v --tb=short

test-frontend:                    ## Run frontend tests only
	cd frontend && npm test

lint:                             ## Lint Python + TypeScript
	uv run ruff check src/ packages/ tests/
	uv run mypy src/ packages/
	cd frontend && npm run lint

format:                           ## Auto-format Python + TS
	uv run ruff format src/ packages/ tests/
	cd frontend && npm run format || true

build:                            ## Build frontend for production
	cd frontend && npm run build

bootstrap:                        ## Full setup from scratch
	bash scripts/bootstrap.sh

bootstrap-solana:                 ## Setup + Solana devnet
	bash scripts/bootstrap.sh --with-solana

bootstrap-auth0:                  ## Setup + Auth0 tenant
	bash scripts/bootstrap.sh --with-auth0

bootstrap-all:                    ## Setup + Solana + Auth0
	bash scripts/bootstrap.sh --with-solana --with-auth0

run:                              ## Run backend server
	uv run uvicorn vellum.app:app --host 127.0.0.1 --port 5050 --reload

clean:                            ## Remove caches and build artifacts
	rm -rf .venv __pycache__ .pytest_cache .ruff_cache .mypy_cache
	rm -rf frontend/node_modules frontend/dist
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

help:                             ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-22s\033[0m %s\n", $$1, $$2}'
