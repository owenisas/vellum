"""Shared fixtures + adversarial-report writer."""

import json
from pathlib import Path

import pytest

REPORT_PATH = Path("adversarial_report.json")
_results: dict[str, float] = {}


def record(test_name: str, detection_rate: float, *, in_scope: bool, notes: str = "") -> None:
    _results[test_name] = {
        "detection_rate": detection_rate,
        "in_scope": in_scope,
        "notes": notes,
    }


@pytest.fixture(scope="session", autouse=True)
def write_report():
    yield
    if _results:
        REPORT_PATH.write_text(json.dumps(_results, indent=2, sort_keys=True))


@pytest.fixture
def sample_text():
    return (
        "This is a sample paragraph used to exercise the Veritext watermark "
        "detection under various adversarial transformations. The text is long "
        "enough to allow multiple invisible tag insertions, which exercises the "
        "BCH-protected payload path and the streaming injector. Each tag is 66 "
        "invisible Unicode codepoints and carries 64 bits of payload."
    )
