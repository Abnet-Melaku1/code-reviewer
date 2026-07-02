from enum import StrEnum

import pytest

from codereviewer.schemas import (
    CitationKind,
    ConventionSource,
    DiffSide,
    IndexStatus,
    Language,
    PullRequestState,
    ReviewStatus,
    SymbolKind,
)


def test_index_status_values() -> None:
    assert [s.value for s in IndexStatus] == ["pending", "indexing", "ready", "error"]


def test_symbol_kind_values() -> None:
    assert [s.value for s in SymbolKind] == [
        "function",
        "class",
        "method",
        "module",
        "block",
        "other",
    ]


def test_convention_source_values() -> None:
    assert [s.value for s in ConventionSource] == ["inferred", "from_review", "user_defined"]


def test_pull_request_state_values() -> None:
    assert [s.value for s in PullRequestState] == ["open", "closed", "merged"]


def test_review_status_values() -> None:
    assert [s.value for s in ReviewStatus] == ["queued", "running", "completed", "failed"]


def test_diff_side_values() -> None:
    assert [s.value for s in DiffSide] == ["left", "right"]


def test_citation_kind_values() -> None:
    assert [s.value for s in CitationKind] == ["code_chunk", "convention", "diff_hunk"]


def test_language_includes_core_set_and_is_string_valued() -> None:
    values = {lang.value for lang in Language}
    assert {"python", "typescript", "javascript", "go", "rust", "java"} <= values
    assert Language.python == "python"


@pytest.mark.parametrize(
    "enum_cls",
    [
        IndexStatus,
        Language,
        SymbolKind,
        ConventionSource,
        PullRequestState,
        ReviewStatus,
        DiffSide,
        CitationKind,
    ],
)
def test_enums_reject_unknown_values(enum_cls: type[StrEnum]) -> None:
    with pytest.raises(ValueError):
        enum_cls("definitely_not_a_member")
