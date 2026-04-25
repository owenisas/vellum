#!/usr/bin/env bash
# Vellum bootstrap: install Python + Node deps, init DB, optional Solana/Auth0.
set -euo pipefail

# ----- ANSI colors -----
RED=$'\033[0;31m'
GREEN=$'\033[0;32m'
YELLOW=$'\033[1;33m'
BLUE=$'\033[0;34m'
CYAN=$'\033[0;36m'
BOLD=$'\033[1m'
RESET=$'\033[0m'

# ----- Args -----
WITH_SOLANA=0
WITH_AUTH0=0
for arg in "$@"; do
  case "$arg" in
    --with-solana) WITH_SOLANA=1 ;;
    --with-auth0)  WITH_AUTH0=1 ;;
    -h|--help)
      echo "Usage: $0 [--with-solana] [--with-auth0]"
      exit 0
      ;;
    *)
      echo "${RED}Unknown argument: $arg${RESET}" >&2
      exit 1
      ;;
  esac
done

# ----- Paths -----
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT_DIR"

info()  { echo "${CYAN}==>${RESET} $*"; }
ok()    { echo "${GREEN}[ok]${RESET} $*"; }
warn()  { echo "${YELLOW}[warn]${RESET} $*"; }
fail()  { echo "${RED}[fail]${RESET} $*" >&2; exit 1; }

# ----- Banner -----
cat <<EOF
${BOLD}${BLUE}
   ___       _                       _
  / _ \ _ __(_) __ _ _ __ __ _ _ __ | |__
 | | | | '__| |/ _\` | '__/ _\` | '_ \| '_ \\
 | |_| | |  | | (_| | | | (_| | |_) | | | |
  \___/|_|  |_|\__, |_|  \__,_| .__/|_| |_|
               |___/          |_|
${RESET}${BOLD}  bootstrap${RESET}
EOF
echo

# ----- Python check -----
info "Checking Python >= 3.11"
if ! command -v python3 >/dev/null 2>&1; then
  fail "python3 not found on PATH."
fi
PY_VER="$(python3 --version 2>&1 | awk '{print $2}')"
PY_MAJOR="${PY_VER%%.*}"
PY_REST="${PY_VER#*.}"
PY_MINOR="${PY_REST%%.*}"
if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 11 ]; }; then
  fail "Python $PY_VER detected; need >= 3.11."
fi
ok "Python $PY_VER"

# ----- Node check -----
info "Checking Node >= 20"
if ! command -v node >/dev/null 2>&1; then
  fail "node not found on PATH. Install Node 20+ (https://nodejs.org)."
fi
NODE_RAW="$(node --version)"           # e.g. v20.10.0
NODE_VER="${NODE_RAW#v}"
NODE_MAJOR="${NODE_VER%%.*}"
if [ "$NODE_MAJOR" -lt 20 ]; then
  fail "Node $NODE_VER detected; need >= 20."
fi
ok "Node $NODE_VER"

# ----- uv check -----
info "Checking uv"
if ! command -v uv >/dev/null 2>&1; then
  echo "${YELLOW}uv not found.${RESET} Install with:"
  echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
  fail "uv missing"
fi
ok "uv $(uv --version | awk '{print $2}')"

# ----- uv sync -----
info "Syncing Python workspace (uv sync)"
if [ "$WITH_SOLANA" -eq 1 ]; then
  uv sync --extra solana
  ok "uv sync --extra solana"
else
  uv sync
  ok "uv sync"
fi

# ----- Frontend deps -----
info "Installing frontend deps"
(
  cd frontend
  if [ -f package-lock.json ]; then
    npm ci || npm install
  else
    npm install
  fi
)
ok "frontend deps installed"

# ----- .env files -----
info "Ensuring .env files"
if [ ! -f .env ] && [ -f .env.example ]; then
  cp .env.example .env
  ok "created .env from .env.example"
else
  ok ".env present"
fi
if [ ! -f frontend/.env ] && [ -f frontend/.env.example ]; then
  cp frontend/.env.example frontend/.env
  ok "created frontend/.env"
fi

# ----- data dir -----
info "Creating data/ directory"
mkdir -p data
ok "data/ ready"

# ----- DB init -----
info "Initializing database"
uv run python -c "import asyncio; from vellum.db.connection import init_db; asyncio.run(init_db('data/vellum.db'))"
ok "data/vellum.db initialized"

# ----- Optional integrations -----
if [ "$WITH_SOLANA" -eq 1 ]; then
  info "Running setup_solana.sh"
  bash "$SCRIPT_DIR/setup_solana.sh"
fi

if [ "$WITH_AUTH0" -eq 1 ]; then
  info "Running setup_auth0.sh"
  bash "$SCRIPT_DIR/setup_auth0.sh"
fi

# ----- Done -----
echo
echo "${GREEN}${BOLD}Bootstrap complete.${RESET}"
echo
echo "${BOLD}Next steps:${RESET}"
echo "  ${CYAN}make dev${RESET}                  # start backend + frontend"
echo "  Backend:  ${BLUE}http://127.0.0.1:5050${RESET}"
echo "  Frontend: ${BLUE}http://127.0.0.1:5173${RESET}"
echo "  API docs: ${BLUE}http://127.0.0.1:5050/docs${RESET}"
echo
exit 0
