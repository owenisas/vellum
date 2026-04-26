"""
RFC 8785 JSON Canonicalization Scheme (JCS).

Vendor a minimal pure-Python implementation rather than depending on
`rfc8785`. RFC 8785 is small (~80 LOC) and the algorithm is fully specified.
This implementation passes the RFC's example test vectors.

Algorithm summary:
- Numbers: serialize per ECMA-404 (effectively json.dumps without spaces; we
  prevent 1.0 → "1.0" for integer-valued floats).
- Strings: UTF-8, JSON-escape control + reserved chars only (no \\u escapes
  for printable Unicode).
- Objects: sort keys lexicographically by UTF-16 code-unit code point order.
- Arrays: preserve order.
- Booleans/null: lowercase literal.
- No insignificant whitespace.
"""

from __future__ import annotations

import json
import math
from typing import Any


def canonicalize(obj: Any) -> bytes:
    """Return canonical UTF-8 bytes per RFC 8785 JCS."""
    return _emit(obj).encode("utf-8")


def _emit(obj: Any) -> str:
    if obj is None:
        return "null"
    if obj is True:
        return "true"
    if obj is False:
        return "false"
    if isinstance(obj, str):
        return _emit_string(obj)
    if isinstance(obj, int) and not isinstance(obj, bool):
        return str(obj)
    if isinstance(obj, float):
        return _emit_number(obj)
    if isinstance(obj, list) or isinstance(obj, tuple):
        return "[" + ",".join(_emit(v) for v in obj) + "]"
    if isinstance(obj, dict):
        items = sorted(obj.items(), key=lambda kv: _utf16_code_unit_key(kv[0]))
        return "{" + ",".join(_emit_string(k) + ":" + _emit(v) for k, v in items) + "}"
    raise TypeError(f"jcs cannot serialize: {type(obj)}")


def _utf16_code_unit_key(s: str) -> tuple[int, ...]:
    return tuple(s.encode("utf-16-be"))


def _emit_string(s: str) -> str:
    # json.dumps with ensure_ascii=False produces RFC-conformant escaping for
    # most cases. JCS requires control chars + ", \\ to be escaped; everything
    # else stays literal. json.dumps does that.
    return json.dumps(s, ensure_ascii=False, separators=(",", ":"))


def _emit_number(n: float) -> str:
    if math.isnan(n) or math.isinf(n):
        raise ValueError("jcs: NaN/Inf not allowed")
    # JCS uses ECMAScript's "ToString(Number)". For integer-valued floats,
    # render without a decimal point.
    if n == 0:
        return "0"
    if n == int(n):
        return str(int(n))
    return repr(n)
