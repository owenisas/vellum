"""Tests for the no-op detect path of the generation-time watermark layer."""

from genwatermark import detect_statistical


def test_noop_when_torch_unavailable():
    r = detect_statistical("hello world")
    # Must not raise; returns either real or noop result.
    assert r.score >= 0.0 and r.p_value <= 1.0


def test_empty_text_is_not_present():
    r = detect_statistical("")
    assert r.present is False
