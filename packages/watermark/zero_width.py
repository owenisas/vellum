"""
Veritext zero-width Unicode encoding/decoding.

Symbols:
    U+2063 (INVISIBLE SEPARATOR)     — tag start delimiter
    U+2064 (INVISIBLE PLUS)          — tag end delimiter
    U+200B (ZERO-WIDTH SPACE)        — binary 0
    U+200C (ZERO-WIDTH NON-JOINER)   — binary 1

Each tag = start + 64 bits + end = 66 invisible chars.

Injection modes (improvement #14):
    - whitespace: inject after every Nth whitespace token (default).
    - grapheme: inject after every Nth grapheme cluster (handles CJK / Thai /
      Arabic where whitespace tokens are not natural). Lazy-imports the
      `regex` module.
"""

from __future__ import annotations

from enum import Enum

TAG_START = "⁣"
TAG_END = "⁤"
ZWSP = "​"   # binary 0
ZWNJ = "‌"   # binary 1

ALL_INVISIBLES = (TAG_START, TAG_END, ZWSP, ZWNJ)
PAYLOAD_BITS = 64


class InjectionMode(str, Enum):
    WHITESPACE = "whitespace"
    GRAPHEME = "grapheme"


def encode_bits(bits: str) -> str:
    """Encode a 64-bit string into the zero-width tag form."""
    if len(bits) != PAYLOAD_BITS:
        raise ValueError(f"expected {PAYLOAD_BITS} bits, got {len(bits)}")
    body = "".join(ZWNJ if c == "1" else ZWSP for c in bits)
    return TAG_START + body + TAG_END


def decode_tag(tag: str) -> str | None:
    """Decode a zero-width tag back to a 64-bit string, or None on malformed."""
    if not tag.startswith(TAG_START) or not tag.endswith(TAG_END):
        return None
    body = tag[1:-1]
    if len(body) != PAYLOAD_BITS:
        return None
    out = []
    for ch in body:
        if ch == ZWSP:
            out.append("0")
        elif ch == ZWNJ:
            out.append("1")
        else:
            return None
    return "".join(out)


def find_tags(text: str) -> list[tuple[int, int, str]]:
    """
    Locate all watermark tags in `text`. Returns list of (start_idx, end_idx,
    tag_string). Includes both well-formed and malformed-but-delimited tags;
    callers decide which to keep.
    """
    out: list[tuple[int, int, str]] = []
    i = 0
    n = len(text)
    while i < n:
        if text[i] == TAG_START:
            j = text.find(TAG_END, i + 1)
            if j == -1:
                break
            out.append((i, j + 1, text[i : j + 1]))
            i = j + 1
        else:
            i += 1
    return out


def strip_all(text: str) -> str:
    """Remove every Veritext tag from `text`. Other zero-width chars are kept."""
    parts: list[str] = []
    last = 0
    for start, end, _ in find_tags(text):
        parts.append(text[last:start])
        last = end
    parts.append(text[last:])
    return "".join(parts)


def _grapheme_iter(text: str):
    """Yield (start_idx, end_idx) of each grapheme cluster. Lazy-imports `regex`."""
    try:
        import regex  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "`regex` package required for grapheme mode. Install veritext or "
            "`pip install regex`."
        ) from exc
    for m in regex.finditer(r"\X", text):
        yield m.start(), m.end()


def split_for_injection(text: str, mode: InjectionMode) -> list[tuple[int, int]]:
    """
    Return a list of (start, end) intervals of "tokens" — units after which a
    tag may be inserted. For whitespace mode, tokens are runs of non-whitespace.
    For grapheme mode, tokens are grapheme clusters.
    """
    if mode == InjectionMode.WHITESPACE:
        spans: list[tuple[int, int]] = []
        i = 0
        n = len(text)
        while i < n:
            while i < n and text[i].isspace():
                i += 1
            if i >= n:
                break
            j = i
            while j < n and not text[j].isspace():
                j += 1
            spans.append((i, j))
            i = j
        return spans
    elif mode == InjectionMode.GRAPHEME:
        return list(_grapheme_iter(text))
    else:
        raise ValueError(f"unknown injection mode: {mode}")
