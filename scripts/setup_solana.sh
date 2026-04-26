#!/usr/bin/env bash
# Solana devnet keypair setup for Vellum.
set -euo pipefail

RED=$'\033[0;31m'
GREEN=$'\033[0;32m'
YELLOW=$'\033[1;33m'
BLUE=$'\033[0;34m'
CYAN=$'\033[0;36m'
BOLD=$'\033[1m'
RESET=$'\033[0m'

info()  { echo "${CYAN}==>${RESET} $*"; }
ok()    { echo "${GREEN}[ok]${RESET} $*"; }
warn()  { echo "${YELLOW}[warn]${RESET} $*"; }
fail()  { echo "${RED}[fail]${RESET} $*" >&2; exit 1; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT_DIR"

KEYPAIR_PATH="data/solana-keypair.json"
ENV_FILE=".env"

echo "${BOLD}${BLUE}Vellum Solana devnet setup${RESET}"
echo

# ----- CLI check -----
if ! command -v solana >/dev/null 2>&1; then
  echo "${RED}solana CLI not found.${RESET}"
  echo "Install with:"
  echo "  ${CYAN}sh -c \"\$(curl -sSfL https://release.anza.xyz/stable/install)\"${RESET}"
  echo "Then re-run this script."
  exit 1
fi
ok "solana CLI: $(solana --version | head -n1)"

# ----- Configure devnet -----
info "Setting Solana cluster to devnet"
solana config set --url devnet >/dev/null
ok "cluster = devnet"

# ----- Keypair -----
mkdir -p data
if [ -f "$KEYPAIR_PATH" ]; then
  ok "keypair already exists: $KEYPAIR_PATH"
else
  info "Generating new keypair at $KEYPAIR_PATH"
  solana-keygen new --outfile "$KEYPAIR_PATH" --no-bip39-passphrase --force >/dev/null
  ok "keypair generated"
fi

PUBKEY="$(solana-keygen pubkey "$KEYPAIR_PATH")"
ok "pubkey: ${BOLD}$PUBKEY${RESET}"

# ----- Airdrop (best-effort) -----
info "Requesting 2 SOL airdrop on devnet (best-effort)"
if solana airdrop 2 "$PUBKEY" --url devnet >/dev/null 2>&1; then
  ok "airdrop succeeded"
else
  warn "airdrop failed or rate-limited; you can retry later with:"
  echo "  solana airdrop 2 $PUBKEY --url devnet"
fi

# ----- Patch .env idempotently -----
patch_env() {
  local key="$1"
  local val="$2"
  local file="$3"
  [ -f "$file" ] || touch "$file"
  cp "$file" "$file.bak.$$"
  if grep -qE "^${key}=" "$file"; then
    awk -v k="$key" -v v="$val" -F= '
      BEGIN { OFS="=" }
      {
        if ($1 == k) { print k, v }
        else         { print $0 }
      }
    ' "$file.bak.$$" > "$file"
  else
    cp "$file.bak.$$" "$file"
    printf '%s=%s\n' "$key" "$val" >> "$file"
  fi
  rm -f "$file.bak.$$"
}

info "Patching $ENV_FILE"
patch_env "CHAIN_BACKEND" "solana" "$ENV_FILE"
patch_env "SOLANA_KEYPAIR_PATH" "$KEYPAIR_PATH" "$ENV_FILE"
ok "CHAIN_BACKEND=solana"
ok "SOLANA_KEYPAIR_PATH=$KEYPAIR_PATH"

# ----- Balance + explorer -----
BAL="$(solana balance "$PUBKEY" --url devnet 2>/dev/null || echo 'unknown')"
echo
echo "${BOLD}Balance:${RESET} $BAL"
echo "${BOLD}Explorer:${RESET} ${BLUE}https://explorer.solana.com/address/${PUBKEY}?cluster=devnet${RESET}"
echo
echo "${GREEN}${BOLD}Solana setup complete.${RESET}"
exit 0
