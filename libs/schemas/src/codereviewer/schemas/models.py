from datetime import datetime
from typing import Annotated, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from codereviewer.schemas.enums import (
    ConventionSource,
    IndexStatus,
    Language,
    PullRequestState,
    SymbolKind,
)

# String fields holding verbatim text (source code, patches) opt out of the model-level
# whitespace stripping that StrippedStrModel applies to identifier fields.
VerbatimStr = Annotated[str, StringConstraints(strip_whitespace=False)]


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
        # A blank snippet carries no information; treat it as no example rather than "".
        if value is not None and not value.strip():
            return None
        return value
