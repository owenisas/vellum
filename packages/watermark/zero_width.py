"""Zero-width Unicode encoding/decoding and tag injection."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .config import TagConfig
from .payload import Payload, from_bits, pack, to_bits, to_hex, unpack


def encode_bits(bits: str, tag: TagConfig) -> str:
    """Encode a binary string as zero-width characters."""
    if any(c not in "01" for c in bits):
        raise ValueError("bits must contain only '0' and '1'")
    return "".join(tag.bit_one if b == "1" else tag.bit_zero for b in bits)


def decode_bits(text: str, tag: TagConfig) -> str:
    """Inverse of encode_bits — extract '0'/'1' from zero-width characters."""
    out: list[str] = []
    for c in text:
        if c == tag.bit_zero:
            out.append("0")
        elif c == tag.bit_one:
            out.append("1")
    return "".join(out)


def build_tag(payload64: int, tag: TagConfig) -> str:
    """Wrap the payload bits between the tag start/end delimiters."""
    bits = to_bits(payload64, tag.payload_bits)
    return tag.tag_start + encode_bits(bits, tag) + tag.tag_end


@dataclass(frozen=True)
class TagMatch:
    """A single watermark tag found in a body of text."""

    start_index: int  # Index of tag_start in original text
    end_index: int  # Index after tag_end
    raw_bits: str
    payload64: int
    payload: Payload


@dataclass
class TagInjector:
    """Streaming-friendly tag injector.

    Counts whitespace-delimited tokens and inserts a tag after the next whitespace
    boundary every `repeat_interval_tokens` tokens. On finalize, ensures at least
    one tag is emitted for non-trivial input.
    """

    payload64: int
    tag: TagConfig
    repeat_interval_tokens: int = 160

    _buffer: str = field(default="", init=False, repr=False)
    _token_count: int = field(default=0, init=False, repr=False)
    _tags_emitted: int = field(default=0, init=False, repr=False)
    _total_chars: int = field(default=0, init=False, repr=False)
    _full_text: list[str] = field(default_factory=list, init=False, repr=False)

    def inject_delta(self, chunk: str, finalize: bool = False) -> str:
        """Process a streamed chunk and return the equivalent watermarked chunk.

        State is preserved across calls so a streaming response can be tagged
        incrementally without disturbing token boundaries.
        """
        if not chunk and not finalize:
            return ""

        out: list[str] = []
        self._buffer += chunk
        self._full_text.append(chunk)

        # Walk the buffer character by character, emit chars + tags at whitespace breaks
        i = 0
        while i < len(self._buffer):
            c = self._buffer[i]
            out.append(c)
            self._total_chars += 1
            if c.isspace():
                self._token_count += 1
                if (
                    self._token_count > 0
                    and self._token_count % self.repeat_interval_tokens == 0
                ):
                    out.append(build_tag(self.payload64, self.tag))
                    self._tags_emitted += 1
            i += 1

        # Reset buffer; we've emitted everything we processed
        self._buffer = ""

        if finalize and self._tags_emitted == 0:
            full_text = "".join(self._full_text)
            if len(full_text) >= 20:
                # Force one tag at ~40% position to guarantee detection
                emitted = "".join(out)
                pos = max(1, int(len(emitted) * 0.4))
                # Try to land on a whitespace boundary at/after pos
                while pos < len(emitted) and not emitted[pos].isspace():
                    pos += 1
                if pos >= len(emitted):
                    pos = len(emitted)
                tag_str = build_tag(self.payload64, self.tag)
                out = [emitted[:pos], tag_str, emitted[pos:]]
                self._tags_emitted += 1

        return "".join(out)

    def finalize(self) -> str:
        return self.inject_delta("", finalize=True)


def find_tags(text: str, tag: TagConfig) -> list[TagMatch]:
    """Locate all watermark tags in text.

    Returns matches in document order. Invalid CRC payloads are still returned
    so callers can report them as `invalid_count`.
    """
    if not text:
        return []

    pattern = re.compile(
        re.escape(tag.tag_start)
        + r"([" + re.escape(tag.bit_zero) + re.escape(tag.bit_one) + r"]+?)"
        + re.escape(tag.tag_end),
    )

    matches: list[TagMatch] = []
    for m in pattern.finditer(text):
        bit_chars = m.group(1)
        bits = decode_bits(bit_chars, tag)
        if len(bits) != tag.payload_bits:
            continue
        try:
            payload64 = from_bits(bits)
        except ValueError:
            continue
        matches.append(
            TagMatch(
                start_index=m.start(),
                end_index=m.end(),
                raw_bits=bits,
                payload64=payload64,
                payload=unpack(payload64),
            ),
        )
    return matches


def strip_tags(text: str, tag: TagConfig) -> str:
    """Remove every watermark tag from text. Leaves the rest of the string untouched."""
    if not text:
        return text
    pattern = re.compile(
        re.escape(tag.tag_start)
        + r"[" + re.escape(tag.bit_zero) + re.escape(tag.bit_one) + r"]*?"
        + re.escape(tag.tag_end),
    )
    return pattern.sub("", text)


__all__ = [
    "TagInjector",
    "TagMatch",
    "build_tag",
    "decode_bits",
    "encode_bits",
    "find_tags",
    "from_bits",
    "pack",
    "strip_tags",
    "to_bits",
    "to_hex",
    "unpack",
]
