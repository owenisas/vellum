"""Zero-width tag encode/decode/find/strip tests."""

import pytest

from watermark.zero_width import (
    InjectionMode,
    decode_tag,
    encode_bits,
    find_tags,
    split_for_injection,
    strip_all,
)


def test_encode_decode_roundtrip():
    bits = "01" * 32
    tag = encode_bits(bits)
    assert len(tag) == 66  # 1 start + 64 bits + 1 end
    assert decode_tag(tag) == bits


def test_decode_malformed_returns_none():
    assert decode_tag("plain text") is None
    assert decode_tag(encode_bits("0" * 64)[:-1]) is None  # missing end


def test_find_tags_in_text():
    bits1 = "0" * 64
    bits2 = "1" * 64
    text = "hello " + encode_bits(bits1) + " world " + encode_bits(bits2)
    tags = find_tags(text)
    assert len(tags) == 2
    assert decode_tag(tags[0][2]) == bits1
    assert decode_tag(tags[1][2]) == bits2


def test_strip_all_removes_tags():
    text = "hello " + encode_bits("0" * 64) + "world"
    stripped = strip_all(text)
    assert "hello world" == stripped


def test_split_whitespace_mode():
    text = "the quick brown fox"
    spans = split_for_injection(text, InjectionMode.WHITESPACE)
    assert len(spans) == 4


def test_split_grapheme_mode():
    pytest.importorskip("regex")
    text = "héllo👨‍👩‍👧"
    spans = split_for_injection(text, InjectionMode.GRAPHEME)
    # 5 ASCII letters + 1 emoji ZWJ family = 6 grapheme clusters
    assert len(spans) == 6
