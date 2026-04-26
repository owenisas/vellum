"""
Merkle batching for Veritext anchors (improvement #3).

Builds a binary Merkle tree from a list of leaf hashes (hex strings, 32 bytes
SHA-256 each) and produces inclusion proofs for any leaf.

The proof format used in proof bundles is a list of `{hash, side}` steps where
`side` is "L" or "R" (the position of the *sibling* relative to the current
node). To verify: starting from the leaf, repeatedly hash with each sibling on
the indicated side; the result must equal the root.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass


@dataclass
class InclusionProof:
    leaf: str
    leaf_index: int
    steps: list[dict]  # [{"hash": "...", "side": "L"|"R"}]


def _hash_pair(a: str, b: str) -> str:
    return hashlib.sha256(bytes.fromhex(a) + bytes.fromhex(b)).hexdigest()


def build_root_and_proofs(leaves: list[str]) -> tuple[str, list[InclusionProof]]:
    """Build Merkle root + per-leaf inclusion proofs. Single-leaf trees use the
    leaf as the root (no proof steps)."""
    if not leaves:
        raise ValueError("at least one leaf required")
    levels: list[list[str]] = [list(leaves)]
    while len(levels[-1]) > 1:
        prev = levels[-1]
        nxt: list[str] = []
        for i in range(0, len(prev), 2):
            left = prev[i]
            right = prev[i + 1] if i + 1 < len(prev) else prev[i]  # duplicate last
            nxt.append(_hash_pair(left, right))
        levels.append(nxt)
    root = levels[-1][0]

    proofs: list[InclusionProof] = []
    for idx, leaf in enumerate(leaves):
        steps: list[dict] = []
        cur = idx
        for level in levels[:-1]:
            sibling_idx = cur ^ 1
            if sibling_idx >= len(level):
                sibling_idx = cur  # duplicated
            sibling = level[sibling_idx]
            side = "L" if sibling_idx < cur else "R"
            steps.append({"hash": sibling, "side": side})
            cur //= 2
        proofs.append(InclusionProof(leaf=leaf, leaf_index=idx, steps=steps))
    return root, proofs


def verify_inclusion(leaf: str, leaf_index: int, steps: list[dict], root: str) -> bool:
    """Verify a leaf is included in the tree under the given root."""
    cur = leaf
    for step in steps:
        sibling = step["hash"]
        side = step["side"]
        if side == "L":
            cur = _hash_pair(sibling, cur)
        elif side == "R":
            cur = _hash_pair(cur, sibling)
        else:
            return False
    return cur == root


__all__ = ["InclusionProof", "build_root_and_proofs", "verify_inclusion"]
