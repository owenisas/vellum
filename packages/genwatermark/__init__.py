"""
Veritext generation-time watermark layer (defense in depth — improvement #5).

Wraps the SynthID-Text scheme (Apache 2.0). When `transformers` and `torch`
are not installed (the default), provides a no-op detector that returns
`StatisticalResult(present=False, score=0.0, p_value=1.0)`.

This package is gated by `GENWATERMARK_ENABLED` in settings. The Unicode tag
in `packages/watermark` remains the primary defense.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class StatisticalResult:
    present: bool
    score: float
    p_value: float
    method: str = "synthid"


def detect_statistical(text: str, *, model_id: str | None = None) -> StatisticalResult:
    """
    Return a statistical detection result. If SynthID stack is unavailable,
    returns a no-op result (still safe to call). Logs a warning at first call.
    """
    try:
        return _synthid_detect(text, model_id)
    except _SynthIDUnavailable:
        return StatisticalResult(present=False, score=0.0, p_value=1.0, method="noop")


class _SynthIDUnavailable(RuntimeError):
    pass


def _synthid_detect(text: str, model_id: str | None) -> StatisticalResult:
    """
    Real SynthID-Text detection. Requires `transformers` + `torch` and a
    model-specific watermarking config; in this scaffolding we use a
    placeholder detector that returns a deterministic score so downstream
    code paths can be exercised end-to-end.

    A full SynthID integration is described in `synthid.py` and is gated by
    the `[genwatermark]` optional extra in pyproject.toml.
    """
    try:
        import torch  # noqa: F401
        import transformers  # noqa: F401
    except ImportError as exc:
        raise _SynthIDUnavailable("synthid stack not installed") from exc
    from .synthid import SynthIDDetector

    return SynthIDDetector().detect(text, model_id=model_id)


__all__ = ["StatisticalResult", "detect_statistical"]
