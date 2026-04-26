"""RFC 8785 JCS conformance tests (subset)."""

import pytest

from veritext.services._jcs import canonicalize


def test_object_keys_sorted():
    assert canonicalize({"b": 2, "a": 1}) == b'{"a":1,"b":2}'


def test_nested_arrays_preserved():
    assert canonicalize({"a": [3, 2, 1]}) == b'{"a":[3,2,1]}'


def test_literals():
    assert canonicalize(None) == b"null"
    assert canonicalize(True) == b"true"
    assert canonicalize(False) == b"false"


def test_integer_floats_render_as_ints():
    assert canonicalize(1.0) == b"1"
    assert canonicalize(0.0) == b"0"


def test_unicode_string_passthrough():
    assert canonicalize("héllo") == '"héllo"'.encode("utf-8")


def test_determinism_under_key_permutation():
    a = canonicalize({"z": 1, "a": {"b": 2, "x": [1, 2]}, "m": "k"})
    b = canonicalize({"a": {"x": [1, 2], "b": 2}, "m": "k", "z": 1})
    assert a == b


def test_nan_and_inf_rejected():
    with pytest.raises(ValueError):
        canonicalize(float("nan"))
    with pytest.raises(ValueError):
        canonicalize(float("inf"))
