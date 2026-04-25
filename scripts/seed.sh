#!/usr/bin/env bash
# Seed demo companies + a fixture-mode anchor for /api/chain/blocks.
set -euo pipefail

GREEN=$'\033[0;32m'
YELLOW=$'\033[1;33m'
CYAN=$'\033[0;36m'
BOLD=$'\033[1m'
RESET=$'\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT_DIR"

echo "${BOLD}${CYAN}Seeding demo data${RESET}"
echo "${YELLOW}Note: the backend should not be running (writes go directly to data/vellum.db).${RESET}"
echo

uv run python - <<'PYCODE'
import asyncio, sys
from vellum.db.connection import init_db
from vellum.services.signing_service import SigningService
try:
    from vellum.services.anchor_service import AnchorService
except Exception:
    AnchorService = None
try:
    from watermark import Watermarker
except Exception:
    Watermarker = None

async def main():
    await init_db("data/vellum.db")
    svc = SigningService()
    companies = []
    for i in range(3):
        name = f"Acme Corp {i+1}"
        result = await svc.register_company(name=name, auto_generate=True)
        companies.append(result)
        print(f"  company: {name}  issuer_id={result['issuer_id']}  addr={result.get('address')}")
    anchors = 0
    chain_len = 0
    if AnchorService is not None and Watermarker is not None and companies:
        wm = Watermarker()
        text = "Demo content for fixture anchor."
        marked = wm.embed(text, payload=b"fixture")
        first = companies[0]
        priv = first.get("private_key") or first.get("privkey")
        anchor_svc = AnchorService()
        await anchor_svc.anchor(
            content=marked,
            issuer_id=first["issuer_id"],
            private_key=priv,
        )
        anchors = 1
        try:
            blocks = await anchor_svc.list_blocks()
            chain_len = len(blocks)
        except Exception:
            chain_len = -1
    print()
    print(f"summary: companies={len(companies)} anchors={anchors} chain_length={chain_len}")

asyncio.run(main())
PYCODE

echo
echo "${GREEN}${BOLD}Seed complete.${RESET}"
exit 0
