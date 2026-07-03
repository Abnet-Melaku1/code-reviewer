from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from codereviewer.schemas.enums import IndexStatus


class DomainModel(BaseModel):
    """Base for all domain models: reject unknown fields so bad input fails at the boundary."""

    model_config = ConfigDict(extra="forbid")


class Repository(DomainModel):
    """A connected GitHub repository and the state of its index.

    ``posting_enabled`` defaults to False: posting to a PR is a dry run until a repo owner
    opts in (guardrail S2). ``index_status`` starts at ``pending`` — the initial state of
    the index lifecycle.

    Strips whitespace on its string fields (all identifiers/refs) so a value like ``"  "``
    fails ``min_length`` rather than slipping through as a valid-looking blank. Scoped to
    this model rather than the base because other entities (e.g. code content) must preserve
    whitespace verbatim.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    github_installation_id: int = Field(gt=0)
    owner: str = Field(min_length=1)
    name: str = Field(min_length=1)
    default_branch: str = Field(min_length=1)
    index_status: IndexStatus = IndexStatus.pending
    indexed_commit_sha: str | None = None
    last_indexed_at: datetime | None = None
    posting_enabled: bool = False
