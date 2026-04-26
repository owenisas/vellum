#!/usr/bin/env bash
# Setup Solana devnet + keypair + airdrop.
set -euo pipefail

if ! command -v solana >/dev/null; then
    echo "Solana CLI not found. Install: https://docs.solanalabs.com/cli/install"
    exit 1
fi

mkdir -p data
KEYPAIR_PATH="data/solana-keypair.json"

if [ ! -f "$KEYPAIR_PATH" ]; then
    solana-keygen new --outfile "$KEYPAIR_PATH" --no-bip39-passphrase --force
fi

solana config set --url devnet --keypair "$KEYPAIR_PATH"
PUBKEY=$(solana-keygen pubkey "$KEYPAIR_PATH")

echo "==> Airdropping 2 SOL to $PUBKEY (devnet)"
solana airdrop 2 "$PUBKEY" --url devnet || echo "Airdrop may be rate-limited; you can retry."

echo
echo "Append to .env:"
echo "  CHAIN_BACKEND=solana"
echo "  SOLANA_KEYPAIR_PATH=$KEYPAIR_PATH"
echo "  SOLANA_CLUSTER=devnet"
