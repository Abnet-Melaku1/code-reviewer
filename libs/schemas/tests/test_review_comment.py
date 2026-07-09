from typing import Any

import pytest
from pydantic import ValidationError

from codereviewer.schemas import DiffSide, ReviewComment, Severity


def _valid_data() -> dict[str, Any]:
    return {
        "file_path": "src/app/main.py",
        "line": 12,
        "side": "right",
        "severity": "must_fix",
        "body": "This call needs an explicit timeout.",
        "citations": [{"kind": "code_chunk", "code_chunk_id": 3}],
    }


def test_review_comment_construction_and_defaults() -> None:
    comment = ReviewComment.model_validate(_valid_data())

    assert comment.side is DiffSide.right
    assert comment.severity is Severity.must_fix
    assert comment.posted_to_github is False
    assert comment.github_comment_id is None
    assert comment.suggested_patch is None
    assert len(comment.citations) == 1


def test_review_comment_requires_at_least_one_citation() -> None:
    with pytest.raises(ValidationError):
        ReviewComment.model_validate(_valid_data() | {"citations": []})


@pytest.mark.parametrize("field", ["file_path", "line", "side", "severity", "body", "citations"])
def test_review_comment_requires_each_field(field: str) -> None:
    data = _valid_data()
    del data[field]

    with pytest.raises(ValidationError):
        ReviewComment.model_validate(data)


def test_review_comment_rejects_invalid_nested_citation() -> None:
    # A citation whose target does not match its kind must fail through the comment.
    with pytest.raises(ValidationError):
        ReviewComment.model_validate(_valid_data() | {"citations": [{"kind": "code_chunk"}]})


def test_review_comment_preserves_suggested_patch_verbatim() -> None:
    patch = "-    do()\n+    do(timeout=5)\n"
    comment = ReviewComment.model_validate(_valid_data() | {"suggested_patch": patch})

    assert comment.suggested_patch == patch


@pytest.mark.parametrize("blank", ["", "   \n"])
def test_review_comment_normalizes_blank_patch_to_none(blank: str) -> None:
    comment = ReviewComment.model_validate(_valid_data() | {"suggested_patch": blank})

    assert comment.suggested_patch is None


@pytest.mark.parametrize("field", ["file_path", "body"])
@pytest.mark.parametrize("value", ["", "   "])
def test_review_comment_rejects_blank_strings(field: str, value: str) -> None:
    with pytest.raises(ValidationError):
        ReviewComment.model_validate(_valid_data() | {field: value})


def test_review_comment_rejects_non_positive_line() -> None:
    with pytest.raises(ValidationError):
        ReviewComment.model_validate(_valid_data() | {"line": 0})


def test_review_comment_rejects_non_positive_github_comment_id() -> None:
    with pytest.raises(ValidationError):
        ReviewComment.model_validate(_valid_data() | {"github_comment_id": 0})


def test_review_comment_rejects_unknown_field() -> None:
    with pytest.raises(ValidationError):
        ReviewComment.model_validate(_valid_data() | {"resolved": True})
