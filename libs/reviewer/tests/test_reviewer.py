from unittest.mock import AsyncMock, MagicMock

import pytest

from codereviewer.providers.fake import FakeLlmProvider
from codereviewer.reviewer.agent import run_review
from codereviewer.reviewer.analyzers import StyleAnalyzer, register_default_analyzers
from codereviewer.reviewer.base import validate_review_comments
from codereviewer.schemas.enums import (
    CitationKind,
    ConventionSource,
    DiffSide,
    Severity,
    SymbolKind,
)
from codereviewer.schemas.models import (
    Citation,
    CodeChunk,
    Convention,
    DiffHunk,
    RetrievedContext,
    ReviewComment,
)


def test_validate_review_comments() -> None:
    # 1. Hunks cover lines 10-20 in main.py
    hunks = [
        DiffHunk(
            file_path="src/main.py",
            content="...",
            start_line=10,
            end_line=20,
            side=DiffSide.right,
        )
    ]

    # Comment inside diff bounds with a citation
    valid_comment = ReviewComment(
        file_path="src/main.py",
        line=15,
        side=DiffSide.right,
        severity=Severity.nit,
        body="Nice",
        citations=[Citation(kind=CitationKind.diff_hunk, diff_ref="ref")],
    )

    # Comment outside diff bounds
    outside_comment = ReviewComment(
        file_path="src/main.py",
        line=25,
        side=DiffSide.right,
        severity=Severity.nit,
        body="Bad line",
        citations=[Citation(kind=CitationKind.diff_hunk, diff_ref="ref")],
    )

    # Comment in a different file
    diff_file_comment = ReviewComment(
        file_path="src/other.py",
        line=15,
        side=DiffSide.right,
        severity=Severity.nit,
        body="Bad file",
        citations=[Citation(kind=CitationKind.diff_hunk, diff_ref="ref")],
    )

    filtered = validate_review_comments([valid_comment, outside_comment, diff_file_comment], hunks)
    assert len(filtered) == 1
    assert filtered[0].body == "Nice"


@pytest.mark.anyio
async def test_style_analyzer_analyze() -> None:
    llm = FakeLlmProvider()
    analyzer = StyleAnalyzer(llm)

    hunk = DiffHunk(
        file_path="src/main.py",
        content="@@ -10,1 +10,1 @@\n-print('hello')\n+print('hello world')",
        start_line=10,
        end_line=11,
        side=DiffSide.right,
    )

    context = RetrievedContext(
        chunks=[
            CodeChunk(
                id=1,
                symbol_kind=SymbolKind.function,
                symbol_name="test_fun",
                start_line=1,
                end_line=2,
                content="def test_fun(): pass",
                token_count=4,
            )
        ],
        conventions=[
            Convention(
                id=2,
                title="CodeReviewer Default Style",
                description="style rules",
                source=ConventionSource.inferred,
                confidence=0.9,
            )
        ],
    )

    comments = await analyzer.analyze(hunk, context)
    assert len(comments) == 1
    comment = comments[0]
    assert comment.file_path == "src/main.py"
    assert comment.line == 10
    assert len(comment.citations) == 3

    cit_kinds = {c.kind for c in comment.citations}
    assert cit_kinds == {
        CitationKind.diff_hunk,
        CitationKind.code_chunk,
        CitationKind.convention,
    }


@pytest.mark.anyio
async def test_run_review_agent() -> None:
    session = AsyncMock()
    session.add = MagicMock()

    llm = FakeLlmProvider()
    register_default_analyzers(llm)

    # Mock Retriever
    retriever = MagicMock()
    mock_context = RetrievedContext(
        chunks=[
            CodeChunk(
                id=1,
                symbol_kind=SymbolKind.function,
                symbol_name="test_fun",
                start_line=1,
                end_line=2,
                content="def test_fun(): pass",
                token_count=4,
            )
        ],
        conventions=[
            Convention(
                id=2,
                title="CodeReviewer Default Style",
                description="style rules",
                source=ConventionSource.inferred,
                confidence=0.9,
            )
        ],
    )
    retriever.retrieve_context = AsyncMock(return_value=mock_context)

    diff = (
        "diff --git a/src/main.py b/src/main.py\n"
        "--- a/src/main.py\n"
        "+++ b/src/main.py\n"
        "@@ -10,1 +10,1 @@\n"
        "-print('hello')\n"
        "+print('hello world')\n"
    )

    review = await run_review(
        session=session,
        provider=llm,
        retriever=retriever,
        pull_request_id=1,
        repository_id=2,
        diff_content=diff,
        commit_sha="commit_sha",
    )

    assert review.status == "completed"
    assert review.nits == 1

    # Assert session.add calls for Review, ReviewComment, and Citations
    added = [call[0][0] for call in session.add.call_args_list]
    reviews = [o for o in added if o.__class__.__name__ == "Review"]
    comments = [o for o in added if o.__class__.__name__ == "ReviewComment"]
    citations = [o for o in added if o.__class__.__name__ == "Citation"]

    assert len(reviews) == 1
    assert len(comments) == 1
    assert len(citations) == 3
