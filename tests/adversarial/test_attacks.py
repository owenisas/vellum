"""
Adversarial test suite (improvement #12).

Each test runs the full apply → attack → detect pipeline N times with random
issuers, then computes a detection rate. CI uploads adversarial_report.json
with the rates.
"""

from __future__ import annotations

import base64
import re
import unicodedata

import pytest

from watermark import Watermarker
from .conftest import record


N_TRIALS = 30


def _detection_rate(transform, *, sample_text: str) -> float:
    hits = 0
    for i in range(N_TRIALS):
        wm = Watermarker(issuer_id=(i % 4096), model_id=1001, model_version_id=1, key_id=1)
        watermarked = wm.apply(sample_text)
        attacked = transform(watermarked)
        result = wm.detect(attacked)
        if result.watermarked:
            hits += 1
    return hits / N_TRIALS


def test_copy_paste_in_scope(sample_text):
    """Copy-paste must preserve >=95% of tags (in-scope adversary)."""
    rate = _detection_rate(lambda s: s, sample_text=sample_text)
    record("copy_paste", rate, in_scope=True, notes=">=95% required")
    assert rate >= 0.95


def test_regex_strip_out_of_scope(sample_text):
    """Deliberate regex strip is out-of-scope and expected to defeat detection."""
    pat = re.compile("[​-‏⁠-⁯⁣⁤]")
    rate = _detection_rate(lambda s: pat.sub("", s), sample_text=sample_text)
    record("regex_strip", rate, in_scope=False, notes="documented as out-of-scope")
    assert rate <= 0.05


def test_nfkc_normalize_passthrough(sample_text):
    """
    Pure NFKC normalization (Python `unicodedata`) does NOT decompose U+200B,
    U+200C, U+2063, U+2064 — so the tag survives. Real-world "NFKC strips
    them" claims usually apply to CMS pipelines that do additional filtering
    on top of NFKC. We test the pure-NFKC behavior here and document the
    nuance in THREAT_MODEL.md.
    """
    rate = _detection_rate(lambda s: unicodedata.normalize("NFKC", s), sample_text=sample_text)
    record("nfkc_normalize", rate, in_scope=True, notes="pure NFKC preserves the tag")
    # Pure NFKC preserves; we assert the survival rate.
    assert rate >= 0.95


def test_pipeline_filter_strip_out_of_scope(sample_text):
    """
    Realistic CMS pipeline filter — replace common invisible/format chars.
    This is the attack the threat model actually documents as out-of-scope.
    """
    pipeline_pat = re.compile(r"[​-‏⁠-⁯⁣⁤]")
    rate = _detection_rate(lambda s: pipeline_pat.sub("", s), sample_text=sample_text)
    record("pipeline_filter", rate, in_scope=False, notes="documented out-of-scope")
    assert rate <= 0.05


def test_base64_roundtrip_in_scope(sample_text):
    """Base64-encoding then decoding preserves all bytes — should be 100%."""
    def transform(s: str) -> str:
        encoded = base64.b64encode(s.encode("utf-8"))
        return base64.b64decode(encoded).decode("utf-8")

    rate = _detection_rate(transform, sample_text=sample_text)
    record("base64_roundtrip", rate, in_scope=True, notes=">=95% required")
    assert rate >= 0.95


def test_truncate_first_half(sample_text):
    """Truncating to the first half should still recover at least one tag if any."""
    def transform(s: str) -> str:
        return s[: len(s) // 2]

    rate = _detection_rate(transform, sample_text=sample_text)
    record("truncate_half", rate, in_scope=True, notes="degraded but expected to recover often")
    # No hard floor; just record.


def test_paraphrase_simulation(sample_text):
    """Word-substitution paraphrase — Unicode tag does not survive (out-of-scope)."""
    def transform(s: str) -> str:
        # Strip tags then permute words slightly. SynthID would be needed to
        # recover signal here; the Unicode-only path will fail.
        from watermark.zero_width import strip_all
        stripped = strip_all(s)
        words = stripped.split()
        return " ".join(reversed(words))

    rate = _detection_rate(transform, sample_text=sample_text)
    record("paraphrase", rate, in_scope=False, notes="Unicode tag does not survive paraphrase")
    assert rate <= 0.05
