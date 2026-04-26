"""End-to-end Watermarker apply/detect/strip tests."""

import pytest

from watermark import Watermarker


def test_apply_detect_short_text_forces_tag():
    text = "Hello, this is a short response."
    wm = Watermarker(issuer_id=42, model_id=1001, model_version_id=2, repeat_interval_tokens=160)
    out = wm.apply(text)
    assert out != text
    result = wm.detect(out)
    assert result.watermarked is True
    assert result.tag_count >= 1
    assert result.valid_count >= 1
    p = result.payloads[0]
    assert p.issuer_id == 42
    assert p.model_id == 1001
    assert p.model_version_id == 2
    assert p.code_valid is True


def test_apply_detect_long_text_multiple_tags():
    words = ["word"] * 500
    text = " ".join(words)
    wm = Watermarker(issuer_id=7, model_id=99, repeat_interval_tokens=100)
    out = wm.apply(text)
    result = wm.detect(out)
    assert result.tag_count >= 4  # 500 / 100 = 5, allow ±1
    for p in result.payloads:
        assert p.issuer_id == 7
        assert p.model_id == 99


def test_strip_removes_tags():
    text = "Hello world"
    wm = Watermarker()
    out = wm.apply(text)
    stripped = Watermarker.strip(out)
    assert stripped == text


def test_apply_empty_text_is_noop():
    wm = Watermarker()
    assert wm.apply("") == ""


def test_detect_no_tags():
    wm = Watermarker()
    r = wm.detect("plain text without watermark")
    assert r.watermarked is False
    assert r.tag_count == 0


def test_detection_survives_one_bit_flip_in_payload():
    """Improvement #2: BCH(63,16)-style FEC corrects one-bit errors."""
    text = "This is a slightly longer test response with several words."
    wm = Watermarker(issuer_id=42, model_id=1001)
    watermarked = wm.apply(text)

    # Find a tag and flip one bit (replace one ZWSP with ZWNJ inside)
    from watermark.zero_width import find_tags, ZWSP, ZWNJ, TAG_START, TAG_END
    tags = find_tags(watermarked)
    assert len(tags) >= 1
    start, end, tag = tags[0]
    # Pick a ZWSP inside the tag body and flip it
    body = tag[1:-1]
    flipped_body = list(body)
    for i, ch in enumerate(flipped_body):
        if ch == ZWSP:
            flipped_body[i] = ZWNJ
            break
    flipped_tag = TAG_START + "".join(flipped_body) + TAG_END
    flipped_text = watermarked[:start] + flipped_tag + watermarked[end:]

    r = wm.detect(flipped_text)
    # At least one tag should still recover (errors_corrected >= 1)
    recovered = [p for p in r.payloads if p.code_valid]
    assert len(recovered) >= 1
    assert any(p.errors_corrected == 1 for p in recovered)


def test_grapheme_mode():
    pytest.importorskip("regex")
    from watermark import InjectionMode
    text = "héllo wörld with áccents"
    wm = Watermarker(injection_mode=InjectionMode.GRAPHEME, repeat_interval_tokens=10)
    out = wm.apply(text)
    r = wm.detect(out)
    assert r.watermarked is True
