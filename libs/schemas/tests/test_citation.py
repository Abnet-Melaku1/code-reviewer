from typing import Any

import pytest
from pydantic import ValidationError

from codereviewer.schemas import Citation, CitationKind


def test_code_chunk_citation_is_valid() -> None:
    citation = Citation.model_validate({"kind": "code_chunk", "code_chunk_id": 5})

    assert citation.kind is CitationKind.code_chunk
    assert citation.code_chunk_id == 5
    assert citation.convention_id is None
    assert citation.diff_ref is None


def test_convention_citation_is_valid() -> None:
    citation = Citation.model_validate({"kind": "convention", "convention_id": 9})

    assert citation.convention_id == 9


def test_diff_hunk_citation_is_valid() -> None:
    citation = Citation.model_validate({"kind": "diff_hunk", "diff_ref": "src/app.py:12"})

    assert citation.diff_ref == "src/app.py:12"


@pytest.mark.parametrize(
    "data",
    [
        {"kind": "code_chunk"},  # missing required target
        {"kind": "convention"},
        {"kind": "diff_hunk"},
        {"kind": "diff_hunk", "diff_ref": "   "},  # blank target
    ],
)
def test_citation_requires_target_matching_kind(data: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        Citation.model_validate(data)


@pytest.mark.parametrize(
    "data",
    [
        {"kind": "code_chunk", "code_chunk_id": 1, "convention_id": 2},
        {"kind": "code_chunk", "code_chunk_id": 1, "diff_ref": "x:1"},
        {"kind": "convention", "convention_id": 1, "code_chunk_id": 2},
        {"kind": "diff_hunk", "diff_ref": "x:1", "code_chunk_id": 2},
    ],
)
def test_citation_rejects_targets_that_do_not_match_kind(data: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        Citation.model_validate(data)


def test_citation_rejects_non_positive_id() -> None:
    with pytest.raises(ValidationError):
        Citation.model_validate({"kind": "code_chunk", "code_chunk_id": 0})


def test_citation_rejects_unknown_field() -> None:
    with pytest.raises(ValidationError):
        Citation.model_validate({"kind": "code_chunk", "code_chunk_id": 1, "weight": 1})
