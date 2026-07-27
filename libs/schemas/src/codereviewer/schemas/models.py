from datetime import datetime
from typing import Annotated, Self, assert_never

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from codereviewer.schemas.enums import (
    CitationKind,
    ConventionSource,
    DiffSide,
    IndexStatus,
    Language,
    PullRequestState,
    ReviewStatus,
    Severity,
    SymbolKind,
)

# String fields holding verbatim text (source code, patches) opt out of the model-level
# whitespace stripping that StrippedStrModel applies to identifier fields.
VerbatimStr = Annotated[str, StringConstraints(strip_whitespace=False)]


def _blank_to_none(value: str | None) -> str | None:
    """Normalize an optional string: a blank/whitespace-only value carries no information."""
    if value is not None and not value.strip():
        return None
    return value


class DomainModel(BaseModel):
    """Base for all domain models: reject unknown fields so bad input fails at the boundary."""

    model_config = ConfigDict(extra="forbid")


class StrippedStrModel(DomainModel):
    """Domain model whose string fields are whitespace-stripped, so ``"   "`` fails
    ``min_length`` rather than passing as a blank identifier.

    For models whose strings are identifiers/refs. Not for models holding verbatim text
    (e.g. source code) — those must preserve whitespace and stay on ``DomainModel``.
    """

    model_config = ConfigDict(str_strip_whitespace=True)


class Repository(StrippedStrModel):
    """A connected GitHub repository and the state of its index.

    ``posting_enabled`` defaults to False: posting to a PR is a dry run until a repo owner
    opts in (guardrail S2). ``index_status`` starts at ``pending`` — the initial state of
    the index lifecycle.
    """

    github_installation_id: int = Field(gt=0)
    owner: str = Field(min_length=1)
    name: str = Field(min_length=1)
    default_branch: str = Field(min_length=1)
    index_status: IndexStatus = IndexStatus.pending
    indexed_commit_sha: str | None = None
    last_indexed_at: datetime | None = None
    posting_enabled: bool = False


class IndexedFile(StrippedStrModel):
    """A file currently represented in the index.

    ``blob_sha`` is the git blob SHA, used as the delta-index reconciliation key: a file
    whose blob is unchanged is skipped on re-index.
    """

    path: str = Field(min_length=1)
    language: Language
    blob_sha: str = Field(min_length=1)
    chunk_count: int = Field(default=0, ge=0)


class CodeChunk(DomainModel):
    """An embedded unit of code — ideally a single symbol plus a little context.

    Does not strip whitespace: ``content`` is source code and must be preserved verbatim.
    The ``embedding`` vector is a storage concern owned by the persistence layer, not part
    of this domain schema. Line numbers are 1-based and inclusive.
    """

    symbol_kind: SymbolKind
    symbol_name: str | None = Field(default=None, min_length=1)
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)
    content: str = Field(min_length=1)
    token_count: int = Field(ge=1)

    @field_validator("content")
    @classmethod
    def _content_not_blank(cls, value: str) -> str:
        # Can't strip a verbatim field, but a whitespace-only chunk must never be embedded.
        if not value.strip():
            raise ValueError("content must not be blank")
        return value

    @model_validator(mode="after")
    def _end_not_before_start(self) -> Self:
        if self.end_line < self.start_line:
            raise ValueError("end_line must be >= start_line")
        return self


class PullRequest(StrippedStrModel):
    """A pull request under review. Identity fields mirror GitHub's PR payload."""

    number: int = Field(ge=1)
    head_sha: str = Field(min_length=1)
    base_sha: str = Field(min_length=1)
    title: str = Field(min_length=1)
    author: str = Field(min_length=1)
    state: PullRequestState = PullRequestState.open


class Convention(StrippedStrModel):
    """A learned rule about the codebase, retrieved as grounding during review.

    ``example_code`` is verbatim source and keeps its whitespace; ``title``/``description``
    are prose and are stripped. ``confidence`` is a 0..1 score; inactive conventions are not
    retrieved (``active`` defaults to True).
    """

    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    example_code: VerbatimStr | None = None
    source: ConventionSource
    confidence: float = Field(ge=0.0, le=1.0)
    active: bool = True

    @field_validator("example_code")
    @classmethod
    def _blank_example_is_absent(cls, value: str | None) -> str | None:
        return _blank_to_none(value)


class Citation(StrippedStrModel):
    """Evidence grounding a review comment.

    Exactly one target is populated, and it must match ``kind``: ``code_chunk_id`` for a
    ``code_chunk``, ``convention_id`` for a ``convention``, ``diff_ref`` for a ``diff_hunk``.
    The parent ``review_comment_id`` link is a persistence concern; the target reference is
    domain payload (the UI shows what grounded each comment).
    """

    kind: CitationKind
    code_chunk_id: int | None = Field(default=None, gt=0)
    convention_id: int | None = Field(default=None, gt=0)
    diff_ref: str | None = None

    @field_validator("diff_ref")
    @classmethod
    def _blank_diff_ref_is_absent(cls, value: str | None) -> str | None:
        return _blank_to_none(value)

    @model_validator(mode="after")
    def _exactly_the_target_for_kind(self) -> Self:
        # match (not a dict) so a newly added CitationKind fails mypy here until it is
        # handled — keeping the exactly-one-target invariant enforced at type-check time.
        match self.kind:
            case CitationKind.code_chunk:
                required: object = self.code_chunk_id
                extras = {"convention_id": self.convention_id, "diff_ref": self.diff_ref}
            case CitationKind.convention:
                required = self.convention_id
                extras = {"code_chunk_id": self.code_chunk_id, "diff_ref": self.diff_ref}
            case CitationKind.diff_hunk:
                required = self.diff_ref
                extras = {"code_chunk_id": self.code_chunk_id, "convention_id": self.convention_id}
            case _ as unreachable:
                assert_never(unreachable)
        if required is None:
            raise ValueError(f"citation of kind {self.kind.value} requires its matching target")
        set_extras = [name for name, value in extras.items() if value is not None]
        if set_extras:
            raise ValueError(
                f"citation of kind {self.kind.value} must not also set: {', '.join(set_extras)}"
            )
        return self


class ReviewComment(StrippedStrModel):
    """One margin note. Carries at least one citation — a comment with no grounding is a bug.

    Its ``(file_path, line, side)`` must exist in the actual diff; that is validated against
    the diff in the review pipeline, not here. ``suggested_patch`` is a verbatim diff.
    """

    file_path: str = Field(min_length=1)
    line: int = Field(ge=1)
    side: DiffSide
    severity: Severity
    body: str = Field(min_length=1)
    suggested_patch: VerbatimStr | None = None
    posted_to_github: bool = False
    github_comment_id: int | None = Field(default=None, gt=0)
    citations: list[Citation] = Field(min_length=1)

    @field_validator("suggested_patch")
    @classmethod
    def _blank_patch_is_absent(cls, value: str | None) -> str | None:
        return _blank_to_none(value)


class Review(StrippedStrModel):
    """One review run on a pull request.

    ``(pull_request_id, head_sha)`` is the idempotency key (the FK is a persistence concern).
    Counts and cost/latency metrics default to zero for a freshly queued run and are filled
    in as it progresses; ``model`` records the resolved model ID for audit.
    """

    head_sha: str = Field(min_length=1)
    status: ReviewStatus = ReviewStatus.queued
    summary: str | None = None
    must_fix: int = Field(default=0, ge=0)
    suggestions: int = Field(default=0, ge=0)
    nits: int = Field(default=0, ge=0)
    tokens_in: int = Field(default=0, ge=0)
    tokens_out: int = Field(default=0, ge=0)
    cost_cents: int = Field(default=0, ge=0)
    latency_ms: int = Field(default=0, ge=0)
    model: str = Field(min_length=1)

    @field_validator("summary")
    @classmethod
    def _blank_summary_is_absent(cls, value: str | None) -> str | None:
        return _blank_to_none(value)


class DiffHunk(DomainModel):
    """A hunk from a git diff to be reviewed.

    Whitespace is preserved verbatim.
    """

    file_path: str = Field(min_length=1)
    content: VerbatimStr
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)
    side: DiffSide


class RetrievedContext(DomainModel):
    """Context gathered during RAG retrieval to ground the review of a diff hunk."""

    chunks: list[CodeChunk]
    conventions: list[Convention]
