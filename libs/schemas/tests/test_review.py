from typing import Any

import pytest
from pydantic import ValidationError

from codereviewer.schemas import Review, ReviewStatus


def _valid_data() -> dict[str, Any]:
    return {"head_sha": "cafe123", "model": "claude-opus-4-8"}


def test_review_construction_and_defaults() -> None:
    review = Review.model_validate(_valid_data())

    assert review.status is ReviewStatus.queued
    assert review.summary is None
    assert review.must_fix == review.suggestions == review.nits == 0
    assert review.tokens_in == review.tokens_out == 0
    assert review.cost_cents == review.latency_ms == 0


def test_review_coerces_status_string() -> None:
    review = Review.model_validate(_valid_data() | {"status": "completed"})

    assert review.status is ReviewStatus.completed


@pytest.mark.parametrize(
    "field",
    ["must_fix", "suggestions", "nits", "tokens_in", "tokens_out", "cost_cents", "latency_ms"],
)
def test_review_rejects_negative_counts_and_metrics(field: str) -> None:
    with pytest.raises(ValidationError):
        Review.model_validate(_valid_data() | {field: -1})


@pytest.mark.parametrize("field", ["head_sha", "model"])
@pytest.mark.parametrize("value", ["", "   "])
def test_review_rejects_blank_identifiers(field: str, value: str) -> None:
    with pytest.raises(ValidationError):
        Review.model_validate(_valid_data() | {field: value})


@pytest.mark.parametrize("blank", ["", "   \n"])
def test_review_normalizes_blank_summary_to_none(blank: str) -> None:
    review = Review.model_validate(_valid_data() | {"summary": blank})

    assert review.summary is None


def test_review_rejects_unknown_field() -> None:
    with pytest.raises(ValidationError):
        Review.model_validate(_valid_data() | {"reviewer": "bot"})


@pytest.mark.parametrize("field", ["head_sha", "model"])
def test_review_requires_each_identity_field(field: str) -> None:
    data = _valid_data()
    del data[field]

    with pytest.raises(ValidationError):
        Review.model_validate(data)
