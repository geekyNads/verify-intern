"""Runs the shared fixtures through the Python classifier.

`tools/check_parity.cjs` runs the identical fixtures through
`web/classifier.js`. Both run in CI, so the static site and the API can never
quietly drift apart and give a student two different answers about the same
message.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from api.classifier import Dataset

FIXTURES = json.loads(
    (Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "classifier_cases.json").read_text(
        encoding="utf-8"
    )
)


@pytest.fixture(scope="module")
def ds() -> Dataset:
    return Dataset.load()


@pytest.mark.parametrize("case", FIXTURES["check_cases"], ids=lambda c: c["name"])
def test_check_cases(ds: Dataset, case: dict) -> None:
    result = ds.check_text(case["text"])
    expect = case["expect"]

    assert result.confidence == expect["confidence"]
    assert [m.pattern.id for m in result.matched_patterns] == expect["pattern_ids"]
    assert [e.id for e in result.matched_employers] == expect["employer_ids"]

    # Transparency invariant: nothing is ever flagged without a citable source.
    for m in result.matched_patterns:
        assert m.pattern.sources, f"{m.pattern.id} flagged text with no source"
        assert m.matched_hints, f"{m.pattern.id} matched but reported no hint"
    for e in result.matched_employers:
        assert e.sources, f"{e.id} flagged text with no source"


@pytest.mark.parametrize(
    "case", FIXTURES["lookup_cases"], ids=lambda c: repr(c["query"])
)
def test_lookup_cases(ds: Dataset, case: dict) -> None:
    assert [e.id for e in ds.find_employers(case["query"])] == case["expect_ids"]


def test_score_tracks_confidence(ds: Dataset) -> None:
    """The display score is cosmetic, but it must never contradict the band."""
    for case in FIXTURES["check_cases"]:
        result = ds.check_text(case["text"])
        if result.confidence == "none":
            assert result.score == 0
        else:
            assert 0 < result.score <= 100
