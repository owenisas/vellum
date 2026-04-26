"""Seed demo companies + sample anchored bundles."""

import asyncio
import os

from eth_account import Account


async def main():
    os.environ.setdefault("DB_PATH", "data/veritext.db")
    from veritext.db.connection import init_db
    from veritext.db.repositories import CompanyRepo

    db = await init_db()
    conn = await db.connect()
    repo = CompanyRepo(conn)

    for issuer_id, name in [(1, "Acme"), (42, "Globex"), (1337, "Initech")]:
        if await repo.get_by_issuer(issuer_id):
            print(f"  · issuer {issuer_id} already exists")
            continue
        acct = Account.create()
        await repo.create(
            name=name, issuer_id=issuer_id, eth_address=acct.address, public_key_hex=acct.address
        )
        print(f"  + {name} #{issuer_id} → {acct.address}")
    await db.close()


def cli() -> int:
    asyncio.run(main())
    return 0


if __name__ == "__main__":
    raise SystemExit(cli())
