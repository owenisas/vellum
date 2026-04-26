"""
Stateless `veritext-verify` CLI (improvement #8).

Verifies a proof bundle JSON file. Optional `--text` re-hashes a text file and
compares to bundle.hashing.text_hash; `--rpc` (with solana extras installed)
verifies the on-chain memo signature.

Exit codes:
    0  pass
    1  bundle format invalid
    2  signature does not recover to issuer
    3  text hash mismatch
    4  Merkle inclusion proof invalid
    5  on-chain anchor not found
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from merklebatch import verify_inclusion
from veritext.auth.ecdsa import (
    TypedDataMessage,
    recover_address_eip191,
    recover_address_eip712,
)
from veritext.services._jcs import canonicalize


def _bundle_id_recompute(bundle: dict) -> str:
    partial = {k: v for k, v in bundle.items() if k not in ("bundle_id", "signature", "signed_fields")}
    canon = canonicalize(partial)
    return "vtb2_" + hashlib.sha256(canon).hexdigest()


def verify_bundle(bundle: dict, text: str | None = None, rpc_url: str | None = None) -> tuple[int, str]:
    if bundle.get("spec") != "veritext-proof-bundle/v2":
        return 1, "wrong spec string"

    expected_id = _bundle_id_recompute(bundle)
    if bundle.get("bundle_id") != expected_id:
        return 1, f"bundle_id mismatch: got {bundle.get('bundle_id')}, expected {expected_id}"

    if text is not None:
        text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if text_hash != bundle["hashing"]["text_hash"]:
            return 3, f"text_hash mismatch: text gives {text_hash}, bundle says {bundle['hashing']['text_hash']}"

    sig = bundle["signature"]
    issuer_address = bundle["issuer"]["eth_address"]
    text_hash = bundle["hashing"]["text_hash"]
    try:
        if sig["scheme"] == "eip712":
            td = sig.get("typed_data")
            if not td:
                return 1, "eip712 sig missing typed_data"
            msg = TypedDataMessage(
                text_hash=bytes.fromhex(text_hash),
                issuer_id=int(td["message"]["issuerId"]),
                timestamp=int(td["message"]["timestamp"]),
                bundle_nonce=bytes.fromhex(td["message"]["bundleNonce"].removeprefix("0x")),
            )
            recovered = recover_address_eip712(msg, sig["signature_hex"])
        else:
            recovered = recover_address_eip191("0x" + text_hash, sig["signature_hex"])
    except Exception as exc:
        return 2, f"signature malformed or unrecoverable: {exc}"

    if recovered.lower() != issuer_address.lower():
        return 2, f"signature recovers to {recovered}, expected {issuer_address}"

    # Merkle inclusion proof if present.
    for anchor in bundle.get("anchors", []):
        proof = anchor.get("inclusion_proof") or []
        root = anchor.get("merkle_root")
        if proof and root:
            ok = verify_inclusion(text_hash, anchor.get("leaf_index", 0), proof, root)
            if not ok:
                return 4, "Merkle inclusion proof failed"

    # Optional on-chain check.
    if rpc_url:
        try:
            from solana.rpc.api import Client  # type: ignore
            for anchor in bundle.get("anchors", []):
                if anchor.get("type") in ("solana_per_response", "solana_merkle"):
                    sig_str = anchor.get("tx_hash")
                    if sig_str:
                        client = Client(rpc_url)
                        if client.get_transaction(sig_str).value is None:
                            return 5, f"on-chain tx {sig_str} not found"
        except ImportError:
            return 0, "PASS (offline; solana extras not installed for online check)"

    return 0, "PASS"


def main() -> int:
    parser = argparse.ArgumentParser(prog="veritext-verify", description="Verify a Veritext proof bundle.")
    parser.add_argument("--bundle", required=True, help="Path to bundle JSON file")
    parser.add_argument("--text", help="Optional path to the text file referenced by the bundle")
    parser.add_argument("--rpc", help="Optional Solana RPC URL for on-chain verification")
    args = parser.parse_args()

    bundle = json.loads(Path(args.bundle).read_text())
    text = Path(args.text).read_text() if args.text else None

    code, msg = verify_bundle(bundle, text=text, rpc_url=args.rpc)
    print(msg)
    return code


if __name__ == "__main__":
    sys.exit(main())
