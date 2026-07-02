from enum import StrEnum

# All domain enums are StrEnums so their values serialize as plain strings across the
# API and DB boundaries. This module is the single source of truth; the frontend receives
# these values via the generated types. Members compare lexicographically, not by
# declaration order — rank by an explicit mapping, never by ``<``/``sorted``.


class Severity(StrEnum):
    """Severity of a review comment, listed most to least urgent."""

    must_fix = "must_fix"
    suggestion = "suggestion"
    nit = "nit"
    context = "context"


class IndexStatus(StrEnum):
    """Lifecycle of a repository's index (see the state machine in the data model)."""

    pending = "pending"
    indexing = "indexing"
    ready = "ready"
    error = "error"


class Language(StrEnum):
    """A source language we can detect and chunk.

    Values align with tree-sitter grammar names. Extend this set as grammars are added;
    files whose language is absent fall back to sliding-window chunking.
    """

    python = "python"
    typescript = "typescript"
    javascript = "javascript"
    go = "go"
    rust = "rust"
    java = "java"


class SymbolKind(StrEnum):
    """The kind of symbol a code chunk represents."""

    function = "function"
    class_ = "class"
    method = "method"
    module = "module"
    block = "block"
    other = "other"


class ConventionSource(StrEnum):
    """How a learned convention was established."""

    inferred = "inferred"
    from_review = "from_review"
    user_defined = "user_defined"


class PullRequestState(StrEnum):
    """State of a pull request as reported by GitHub."""

    open = "open"
    closed = "closed"
    merged = "merged"


class ReviewStatus(StrEnum):
    """Lifecycle of a single review run (see the state machine in the data model)."""

    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"


class DiffSide(StrEnum):
    """Which side of a diff a comment anchors to."""

    left = "left"
    right = "right"


class CitationKind(StrEnum):
    """The kind of evidence grounding a review comment."""

    code_chunk = "code_chunk"
    convention = "convention"
    diff_hunk = "diff_hunk"
