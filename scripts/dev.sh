#!/usr/bin/env bash
# Start backend + frontend dev servers in parallel.
set -euo pipefail

trap "kill 0" EXIT INT TERM

echo "==> Backend on http://127.0.0.1:5050"
uv run uvicorn veritext.app:app --reload --host 127.0.0.1 --port 5050 &

echo "==> Frontend on http://127.0.0.1:5173"
(cd frontend && npm run dev) &

wait
