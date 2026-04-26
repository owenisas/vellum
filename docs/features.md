# Vellum Feature Notes

Vellum is an AI provenance app that ties generated text to identity, signatures,
watermarks, and chain anchors. This document summarizes the hackathon-facing
features and what is live today.

## Auth0-Secured AI Agent Actions

Vellum uses Auth0 to protect the AI generation and anchoring workflow.

- `POST /api/chat` requires the `chat:invoke` permission when Auth0 is enabled.
- `POST /api/anchor` requires the `anchor:create` permission.
- Anchored proof bundles include an `agent_action` section with the Auth0
  subject, email, permissions, grant type, provider, and model.
- This lets a verifier see which authenticated actor authorized the
  generate-watermark-sign-anchor action.

## Browser Wallet Proofs

Vellum can attach optional browser wallet proofs to an anchored artifact.
The redesigned Studio flow exposes this in the Sign and Anchor stages: users
choose a registered issuer, sign with either a local demo key or MetaMask, and
optionally attach MetaMask/EVM and Phantom/Solana wallet-control proofs.

The signed message is bound to the final SHA-256 text hash:

```text
Vellum wallet proof
wallet_type: evm|solana
address: <wallet address>
text_hash: <sha256 hash>
purpose: authorize_ai_provenance_anchor
```

The backend re-verifies each proof during `/api/anchor` and stores verified
metadata in the response record, chain payload, and proof bundle.

Private keys never leave the browser wallet. The backend only receives public
addresses, messages, signatures, and optional transaction identifiers.

## EVM vs Solana Verification

EVM wallet proofs are designed for MetaMask-compatible wallets.

- The frontend asks the wallet to sign the canonical message.
- The backend uses EIP-191 `personal_sign` recovery.
- The proof is valid only if the recovered address matches the submitted wallet
  address.
- MetaMask can also sign the issuer hash directly, replacing the older demo
  private-key input when the connected wallet matches the selected issuer.

Solana wallet proofs are designed for Phantom/Solflare-style wallets.

- The frontend asks the wallet to sign the canonical message with Ed25519.
- The backend verifies the signature against the Solana public key.
- If a Solana transaction signature is supplied, the backend can verify it
  through the Solana RPC path when the Solana backend is enabled.

## DigitalOcean Deployment

The project includes a DigitalOcean App Platform deployment workflow.

- GitHub Actions builds a container with the Vite frontend and FastAPI backend.
- The image is pushed to DigitalOcean Container Registry.
- App Platform deploys the combined web/API service.
- The live app currently uses SQLite at `DB_PATH=/workspace/data/vellum.db`.

SQLite is enough for a demo, but it is not durable production storage on App
Platform. A stronger DigitalOcean version should move responses, anchors, and
wallet proof history to DigitalOcean Managed Postgres.

## Solana Readiness

Solana support exists in the backend, but deployment mode matters.

Implemented:

- `SolanaChain` can submit provenance hashes to Solana's Memo program.
- Local SQLite mirroring preserves chain records.
- Proof bundles distinguish real Solana anchors from `solana_local_fallback`.
- `/api/solana/balance` and `/api/solana/verify/{tx_signature}` exist when the
  Solana backend is enabled.
- Browser Solana wallet proofs can be attached and verified cryptographically.

Current deployed status:

- The live app has been observed running with `chain_backend: "simulated"`.
- In simulated mode, Solana wallet signatures can prove wallet control, but the
  app is not submitting live Solana Memo transactions.

To claim the Solana sponsor track in a live demo, enable `CHAIN_BACKEND=solana`,
install the Solana optional dependencies in the deployment image, provide a
funded devnet keypair, and show a proof bundle with a real Solana explorer link.

## Frontend Experience

The Justin redesign is now the active frontend experience:

- `/` presents the visual cover page.
- `/studio` runs the full write, sign, anchor, and prove workflow against the
  existing backend APIs.
- `/ledger` shows recent chain blocks and issuer administration.
- `/principles` explains the provenance model.
- Legacy routes such as `/generate`, `/verify`, and `/chain` redirect into the
  new Studio/Ledger pages.
