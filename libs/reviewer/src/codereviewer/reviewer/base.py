from typing import Protocol

from codereviewer.schemas.models import DiffHunk, RetrievedContext, ReviewComment

_registry: dict[str, "Analyzer"] = {}


class Analyzer(Protocol):
    """Protocol for pluggable code review analyzers."""

    name: str

    def applies_to(self, language: str) -> bool:
        """Return True if the analyzer applies to the target language."""
        ...

    async def analyze(self, hunk: DiffHunk, context: RetrievedContext) -> list[ReviewComment]:
        """Analyze the diff hunk using RAG context grounding and return review comments."""
        ...


def register_analyzer(analyzer: Analyzer) -> None:
    """Register an analyzer in the registry."""
    _registry[analyzer.name] = analyzer


def get_analyzers() -> list[Analyzer]:
    """Retrieve all registered analyzers."""
    return list(_registry.values())


def validate_review_comments(
    comments: list[ReviewComment], diff_hunks: list[DiffHunk]
) -> list[ReviewComment]:
    """Filter and drop comments that lack grounding or lie outside the diff boundaries.

    - Every comment must have at least one citation (enforced by schema).
    - Every comment must target a file and line number within the actual PR diff hunks.
    """
    valid_comments = []
    for comment in comments:
        # 1. Validation: check if the comment has citations
        if not comment.citations:
            continue

        # 2. Validation: check if the comment targets a line within the diff hunks
        matched = False
        for hunk in diff_hunks:
            if (
                hunk.file_path == comment.file_path
                and hunk.start_line <= comment.line <= hunk.end_line
            ):
                matched = True
                break

        if matched:
            valid_comments.append(comment)

    return valid_comments
