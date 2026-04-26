# Veritext multi-stage build: Python backend + Node frontend.

# Stage 1: build frontend
FROM node:20-slim AS frontend-build
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Python deps via uv
FROM python:3.12-slim AS backend-build
WORKDIR /app
RUN pip install --no-cache-dir uv
COPY pyproject.toml uv.lock* README.md ./
COPY packages/ packages/
COPY src/ src/
RUN uv sync --frozen || uv sync

# Stage 3: runtime
FROM python:3.12-slim AS runtime
WORKDIR /app
COPY --from=backend-build /app /app
COPY --from=frontend-build /app/frontend/dist /app/frontend/dist
COPY scripts/ scripts/
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 5050
CMD ["uvicorn", "veritext.app:app", "--host", "0.0.0.0", "--port", "5050"]
