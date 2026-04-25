"""Unit tests for the high-level :class:`watermark.Watermarker` API."""

from __future__ import annotations

import pytest

from watermark import Watermarker, apply, detect, pack, strip


SAMPLE_PARAGRAPH = (
    "Vellum proves provenance for AI-generated text by combining invisible "
    "Unicode watermarks with on-chain anchors and ECDSA signatures from the "
    "issuing company. Each response carries a 64-bit payload describing schema "
    "version, issuer, model, and key. Detection is robust to copy-paste because "
    "the tags ride along inside whitespace boundaries. The same pipeline runs in "
    "fixture mode for tests, in live mode against real LLM providers, and on a "
    "simulated hash chain or Solana memo program for production. " * 3
).strip()


def test_apply_then_detect_round_trip():
    wm = Watermarker(issuer_id=42, model_id=1001)
    out = wm.apply(SAMPLE_PARAGRAPH)

    assert out != SAMPLE_PARAGRAPH

    result = wm.detect(out)
    assert result.watermarked is True
    assert result.valid_count >= 1
    assert result.invalid_count == 0
    assert result.payloads, "expected at least one decoded payload"

    payload = result.payloads[0]
    assert payload.issuer_id == 42
    assert payload.model_id == 1001
    assert payload.crc_valid is True


def test_strip_removes_all_tags():
    wm = Watermarker(issuer_id=7, model_id=3)
    out = wm.apply(SAMPLE_PARAGRAPH)
    stripped = wm.strip(out)

    detect_after = wm.detect(stripped)
    assert detect_after.watermarked is False
    assert detect_after.tag_count == 0

    # strip should fully restore the original visible text
    assert stripped == SAMPLE_PARAGRAPH
    assert len(stripped) == len(SAMPLE_PARAGRAPH)


def test_short_text_force_emit():
    """Text > 20 chars but with fewer than 160 tokens should still get one tag.

    The injector's `finalize()` step inserts a forced fallback tag at ~40%
    when no normal interval has fired yet.
    """
    short = "Vellum watermarks small texts too, even short blurbs."
    assert len(short) > 20

    wm = Watermarker(issuer_id=11)
    out = wm.apply(short)

    result = wm.detect(out)
    assert result.watermarked is True
    assert result.tag_count >= 1
    assert result.payloads[0].issuer_id == 11


def test_empty_text():
    wm = Watermarker()

    assert wm.apply("") == ""
    assert apply("") == ""

    result = wm.detect("")
    assert result.watermarked is False
    assert result.tag_count == 0
    assert result.payloads == []

    assert detect("").watermarked is False


def test_text_under_20_chars_no_tag():
    wm = Watermarker()
    out = wm.apply("hello")
    # Forced fallback only triggers for len >= 20, so output should be unchanged.
    assert out == "hello"


def test_invalid_payload_overflow():
    """Module-level pack() rejects schema_version=16 (4-bit field maxes at 15)."""
    with pytest.raises(ValueError):
        pack(
            schema_version=16,
            issuer_id=1,
            model_id=0,
            model_version_id=0,
            key_id=1,
        )


def test_unicode_text_round_trip():
    text = (
        "Hello world. Bonjour le monde. "
        "Hola mundo. "
        "Greetings from across cultures and continents to all readers everywhere. " * 4
    ).strip()
    wm = Watermarker(issuer_id=99, model_id=2024)
    out = wm.apply(text)

    result = wm.detect(out)
    assert result.watermarked is True
    assert result.payloads[0].issuer_id == 99
    assert result.payloads[0].model_id == 2024
    assert result.payloads[0].crc_valid is True

    # Strip restores original text exactly.
    assert wm.strip(out) == text


def test_module_level_strip_round_trip():
    """The module-level strip() helper mirrors the class method."""
    text = "An entirely ordinary blurb about provenance and watermarking systems."
    out = apply(text, issuer_id=5)
    assert strip(out) == text
