"""Merkle tree build + inclusion proof verification (improvement #3)."""

import hashlib
import os

import pytest

from merklebatch import build_root_and_proofs, verify_inclusion


def _h(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def test_single_leaf():
    leaves = [_h(b"a")]
    root, proofs = build_root_and_proofs(leaves)
    assert root == leaves[0]
    assert proofs[0].steps == []
    assert verify_inclusion(leaves[0], 0, proofs[0].steps, root)


def test_pair():
    leaves = [_h(b"a"), _h(b"b")]
    root, proofs = build_root_and_proofs(leaves)
    assert root != leaves[0] and root != leaves[1]
    for i, leaf in enumerate(leaves):
        assert verify_inclusion(leaf, i, proofs[i].steps, root)


def test_arbitrary_size_round_trip():
    for n in (1, 2, 3, 4, 5, 7, 8, 16, 33, 64):
        leaves = [_h(os.urandom(8)) for _ in range(n)]
        root, proofs = build_root_and_proofs(leaves)
        for i, leaf in enumerate(leaves):
            assert verify_inclusion(leaf, i, proofs[i].steps, root), f"failed at n={n}, i={i}"


def test_tampered_leaf_rejected():
    leaves = [_h(os.urandom(8)) for _ in range(5)]
    root, proofs = build_root_and_proofs(leaves)
    bad_leaf = _h(b"tampered")
    assert not verify_inclusion(bad_leaf, 0, proofs[0].steps, root)
