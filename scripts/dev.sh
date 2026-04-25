#!/usr/bin/env bash
# Run backend (uvicorn) and frontend (vite) in parallel.
# SIGINT/SIGTERM kills both children.
set -euo pipefail

GREEN=$'\033[0;32m'
YELLOW=$'\033[1;33m'
CYAN=$'\033[0;36m'
BOLD=$'\033[1m'
RESET=$'\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT_DIR"

BACKEND_PID=0
FRONTEND_PID=0

cleanup() {
  echo
  echo "${YELLOW}Shutting down dev servers...${RESET}"
  if [ "$BACKEND_PID" -ne 0 ] && kill -0 "$BACKEND_PID" 2>/dev/null; then
    kill "$BACKEND_PID" 2>/dev/null || true
  fi
  if [ "$FRONTEND_PID" -ne 0 ] && kill -0 "$FRONTEND_PID" 2>/dev/null; then
    kill "$FRONTEND_PID" 2>/dev/null || true
  fi
  # Give them a moment to exit cleanly, then SIGKILL stragglers.
  sleep 1
  if [ "$BACKEND_PID" -ne 0 ] && kill -0 "$BACKEND_PID" 2>/dev/null; then
    kill -9 "$BACKEND_PID" 2>/dev/null || true
  fi
  if [ "$FRONTEND_PID" -ne 0 ] && kill -0 "$FRONTEND_PID" 2>/dev/null; then
    kill -9 "$FRONTEND_PID" 2>/dev/null || true
  fi
  wait 2>/dev/null || true
  echo "${GREEN}Done.${RESET}"
}
trap cleanup INT TERM EXIT

echo "${BOLD}${CYAN}Starting Vellum dev servers${RESET}"
echo "  backend : http://127.0.0.1:5050"
echo "  frontend: http://127.0.0.1:5173"
echo

# Backend
uv run uvicorn vellum.app:app --host 127.0.0.1 --port 5050 --reload &
BACKEND_PID=$!

# Frontend
( cd frontend && npm run dev ) &
FRONTEND_PID=$!

# Wait on both. If either exits, fall through to cleanup.
wait -n "$BACKEND_PID" "$FRONTEND_PID" || true
# One died; kill the other via cleanup trap.
exit 0
