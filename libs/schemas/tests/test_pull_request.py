from typing import Any

import pytest
from pydantic import ValidationError

from codereviewer.schemas import PullRequest, PullRequestState


def _valid_data() -> dict[str, Any]:
    return {
        "number": 7,
        "head_sha": "aaa111",
        "base_sha": "bbb222",
        "title": "Add retry to webhook intake",
        "author": "octocat",
    }


def test_pull_request_construction_and_default_state() -> None:
    pr = PullRequest.model_validate(_valid_data())

    assert pr.number == 7
    assert pr.state is PullRequestState.open


def test_pull_request_coerces_state_string() -> None:
    pr = PullRequest.model_validate(_valid_data() | {"state": "merged"})

    assert pr.state is PullRequestState.merged


def test_pull_request_rejects_non_positive_number() -> None:
    with pytest.raises(ValidationError):
        PullRequest.model_validate(_valid_data() | {"number": 0})


@pytest.mark.parametrize("field", ["head_sha", "base_sha", "title", "author"])
@pytest.mark.parametrize("value", ["", "   "])
def test_pull_request_rejects_blank_strings(field: str, value: str) -> None:
    with pytest.raises(ValidationError):
        PullRequest.model_validate(_valid_data() | {field: value})


def test_pull_request_rejects_unknown_field() -> None:
    with pytest.raises(ValidationError):
        PullRequest.model_validate(_valid_data() | {"merged": True})


@pytest.mark.parametrize("field", ["number", "head_sha", "base_sha", "title", "author"])
def test_pull_request_requires_each_field(field: str) -> None:
    data = _valid_data()
    del data[field]

    with pytest.raises(ValidationError):
        PullRequest.model_validate(data)
