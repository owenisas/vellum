# syntax=docker/dockerfile:1.7
#
# Vellum multi-stage image: frontend build -> backend deps -> runtime.
#
# WARNING: Do NOT bake secrets into this image. The container reads its
# configuration from environment variables at runtime (.env on the host,
# `--env-file` on `docker run`, or compose `env_file:`).

# ---------------------------------------------------------------------------
# Stage 1: frontend-build
# ---------------------------------------------------------------------------
FROM node:20-slim AS frontend-build
WORKDIR /app

ARG VITE_API_BASE_URL=""
ARG VITE_AUTH0_DOMAIN=""
ARG VITE_AUTH0_CLIENT_ID=""
ARG VITE_AUTH0_AUDIENCE="https://api.vellum.io"
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL \
    VITE_AUTH0_DOMAIN=$VITE_AUTH0_DOMAIN \
    VITE_AUTH0_CLIENT_ID=$VITE_AUTH0_CLIENT_ID \
    VITE_AUTH0_AUDIENCE=$VITE_AUTH0_AUDIENCE

# Install deps first for better layer caching.
COPY frontend/package.json frontend/package-lock.json* ./
RUN if [ -f package-lock.json ]; then npm ci; else npm install; fi

# Copy source and build.
COPY frontend/ ./
RUN npm run build
# Output: /app/dist

# ---------------------------------------------------------------------------
# Stage 2: backend (Python deps via uv)
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS backend
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates curl \
 && rm -rf /var/lib/apt/lists/* \
 && pip install --no-cache-dir uv

# Copy lockfile + manifests first so layers cache when only source changes.
COPY pyproject.toml ./
COPY README.md ./
COPY uv.lock* ./
COPY packages/ ./packages/

# Resolve and install deps without the workspace project itself.
RUN uv sync --no-install-project

# Now copy the workspace project sources and finalize the install.
COPY src/ ./src/
RUN uv sync

# ---------------------------------------------------------------------------
# Stage 3: runtime
# ---------------------------------------------------------------------------
FROM backend AS runtime

# Bring in the built frontend assets so FastAPI can serve them.
COPY --from=frontend-build /app/dist /app/frontend/dist

# Ensure data directory exists (mount a volume here in compose).
RUN mkdir -p /app/data

EXPOSE 5050

# WARNING: do not bake secrets into the image. Pass env at runtime, e.g.
#   docker run --env-file .env -v $(pwd)/data:/app/data vellum
CMD ["uvicorn", "vellum.app:app", "--host", "0.0.0.0", "--port", "5050"]
