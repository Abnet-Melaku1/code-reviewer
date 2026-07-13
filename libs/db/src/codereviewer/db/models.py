from datetime import datetime
from enum import StrEnum

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    false,
    text,
    true,
)
from sqlalchemy.orm import Mapped, MappedColumn, mapped_column

from codereviewer.db.base import Base, IntPk, TimestampMixin
from codereviewer.schemas import (
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

# Dimension of the embedding vector, tied to the configured embedding model
# (voyage-code-3 @ 1024 dims). Changing the model changes this — a migration plus a full
# re-index, never a hot swap (see docs/02-data-model.md and ADR-0002).
EMBEDDING_DIM = 1024


def _str_enum(enum_type: type[StrEnum]) -> Enum:
    # Store StrEnums by their value (not member name) as a VARCHAR + CHECK, so the column is
    # portable and Alembic-friendly rather than a native Postgres enum type. create_constraint
    # is required: SQLAlchemy 2.0 defaults it to False, which would leave the value domain
    # unenforced at the database.
    return Enum(
        enum_type,
        native_enum=False,
        length=32,
        create_constraint=True,
        values_callable=lambda enum: [member.value for member in enum],
    )


def _counter() -> MappedColumn[int]:
    """A non-negative running count/metric that starts at zero, in the DB as well as the ORM."""
    return mapped_column(Integer, default=0, server_default=text("0"))


class Repository(IntPk, TimestampMixin, Base):
    """A connected GitHub repository. Mirrors codereviewer.schemas.Repository."""

    __tablename__ = "repositories"
    __table_args__ = (
        UniqueConstraint("owner", "name", name="uq_repositories_owner_name"),
        CheckConstraint("github_installation_id > 0", name="github_installation_id_positive"),
    )

    github_installation_id: Mapped[int] = mapped_column(BigInteger, index=True)
    owner: Mapped[str] = mapped_column(String(255))
    name: Mapped[str] = mapped_column(String(255))
    default_branch: Mapped[str] = mapped_column(String(255))
    index_status: Mapped[IndexStatus] = mapped_column(
        _str_enum(IndexStatus), default=IndexStatus.pending, server_default=text("'pending'")
    )
    indexed_commit_sha: Mapped[str | None] = mapped_column(String(64))
    last_indexed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # server_default keeps the S2 dry-run guardrail safe even for non-ORM inserts/backfills.
    posting_enabled: Mapped[bool] = mapped_column(default=False, server_default=false())


class IndexedFile(IntPk, TimestampMixin, Base):
    """A file currently represented in the index. Mirrors codereviewer.schemas.IndexedFile."""

    __tablename__ = "indexed_files"
    __table_args__ = (
        UniqueConstraint("repository_id", "path", name="uq_indexed_files_repository_id_path"),
        CheckConstraint("chunk_count >= 0", name="chunk_count_non_negative"),
    )

    repository_id: Mapped[int] = mapped_column(
        ForeignKey("repositories.id", ondelete="CASCADE"), index=True
    )
    path: Mapped[str] = mapped_column(String(1024))
    language: Mapped[Language] = mapped_column(_str_enum(Language))
    blob_sha: Mapped[str] = mapped_column(String(64))
    chunk_count: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))


class CodeChunk(IntPk, TimestampMixin, Base):
    """An embedded unit of code. Mirrors codereviewer.schemas.CodeChunk plus the embedding
    vector, which is a persistence concern kept out of the domain schema."""

    __tablename__ = "code_chunks"
    __table_args__ = (
        # Mirror the schema's domain invariants at the DB, since the ORM is a separate write
        # path from Pydantic (backfills, raw SQL) that could otherwise persist illegal rows.
        CheckConstraint("start_line >= 1", name="start_line_positive"),
        CheckConstraint("end_line >= start_line", name="line_span_ordered"),
        CheckConstraint("token_count >= 1", name="token_count_positive"),
        # ANN search over embeddings uses this HNSW index (cosine); guardrail S7 forbids
        # full vector scans. Removing the index would silently fall back to one.
        Index(
            "ix_code_chunks_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    indexed_file_id: Mapped[int] = mapped_column(
        ForeignKey("indexed_files.id", ondelete="CASCADE"), index=True
    )
    symbol_kind: Mapped[SymbolKind] = mapped_column(_str_enum(SymbolKind))
    symbol_name: Mapped[str | None] = mapped_column(String(255))
    start_line: Mapped[int] = mapped_column(Integer)
    end_line: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIM))
    token_count: Mapped[int] = mapped_column(Integer)


class Convention(IntPk, TimestampMixin, Base):
    """A learned rule about the codebase. Mirrors codereviewer.schemas.Convention."""

    __tablename__ = "conventions"
    __table_args__ = (
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="confidence_in_unit_interval"),
    )

    repository_id: Mapped[int] = mapped_column(
        ForeignKey("repositories.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    example_code: Mapped[str | None] = mapped_column(Text)
    source: Mapped[ConventionSource] = mapped_column(_str_enum(ConventionSource))
    confidence: Mapped[float] = mapped_column(Float)
    active: Mapped[bool] = mapped_column(default=True, server_default=true())


class PullRequest(IntPk, TimestampMixin, Base):
    """A pull request under review. Mirrors codereviewer.schemas.PullRequest."""

    __tablename__ = "pull_requests"
    __table_args__ = (
        UniqueConstraint("repository_id", "number", name="uq_pull_requests_repository_id_number"),
        CheckConstraint("number >= 1", name="number_positive"),
    )

    repository_id: Mapped[int] = mapped_column(
        ForeignKey("repositories.id", ondelete="CASCADE"), index=True
    )
    number: Mapped[int] = mapped_column(Integer)
    head_sha: Mapped[str] = mapped_column(String(64))
    base_sha: Mapped[str] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(String(512))
    author: Mapped[str] = mapped_column(String(255))
    state: Mapped[PullRequestState] = mapped_column(
        _str_enum(PullRequestState), default=PullRequestState.open, server_default=text("'open'")
    )


class Review(IntPk, TimestampMixin, Base):
    """One review run on a pull request. Mirrors codereviewer.schemas.Review.

    Unique on (pull_request_id, head_sha): the idempotency key that keeps a re-run from
    producing a duplicate review (see the review pipeline invariants).
    """

    __tablename__ = "reviews"
    __table_args__ = (
        UniqueConstraint("pull_request_id", "head_sha", name="uq_reviews_pull_request_id_head_sha"),
        CheckConstraint(
            "must_fix >= 0 AND suggestions >= 0 AND nits >= 0 AND tokens_in >= 0 "
            "AND tokens_out >= 0 AND cost_cents >= 0 AND latency_ms >= 0",
            name="counts_and_metrics_non_negative",
        ),
    )

    pull_request_id: Mapped[int] = mapped_column(
        ForeignKey("pull_requests.id", ondelete="CASCADE"), index=True
    )
    head_sha: Mapped[str] = mapped_column(String(64))
    status: Mapped[ReviewStatus] = mapped_column(
        _str_enum(ReviewStatus), default=ReviewStatus.queued, server_default=text("'queued'")
    )
    summary: Mapped[str | None] = mapped_column(Text)
    must_fix: Mapped[int] = _counter()
    suggestions: Mapped[int] = _counter()
    nits: Mapped[int] = _counter()
    tokens_in: Mapped[int] = _counter()
    tokens_out: Mapped[int] = _counter()
    cost_cents: Mapped[int] = _counter()
    latency_ms: Mapped[int] = _counter()
    model: Mapped[str] = mapped_column(String(255))


class ReviewComment(IntPk, TimestampMixin, Base):
    """One margin note produced by a review. Mirrors codereviewer.schemas.ReviewComment.

    The grounding invariant (at least one Citation) is enforced in the schema and the review
    pipeline (ADR-0005), not here — a "has children" rule is not a DB constraint.
    """

    __tablename__ = "review_comments"
    __table_args__ = (
        CheckConstraint("line >= 1", name="line_positive"),
        CheckConstraint("github_comment_id > 0", name="github_comment_id_positive"),
    )

    review_id: Mapped[int] = mapped_column(ForeignKey("reviews.id", ondelete="CASCADE"), index=True)
    file_path: Mapped[str] = mapped_column(String(1024))
    line: Mapped[int] = mapped_column(Integer)
    side: Mapped[DiffSide] = mapped_column(_str_enum(DiffSide))
    severity: Mapped[Severity] = mapped_column(_str_enum(Severity))
    body: Mapped[str] = mapped_column(Text)
    suggested_patch: Mapped[str | None] = mapped_column(Text)
    posted_to_github: Mapped[bool] = mapped_column(default=False, server_default=false())
    github_comment_id: Mapped[int | None] = mapped_column(BigInteger)


class Citation(IntPk, TimestampMixin, Base):
    """Evidence grounding a review comment. Mirrors codereviewer.schemas.Citation.

    A citation belongs to its comment (CASCADE), but its evidence references SET NULL: a
    review is a historical record, so re-indexing away a cited chunk (or removing a
    convention) must not delete the past comment — the grounding just goes stale.

    That leaves a persistence-only "stale" state (kind set, target NULL) that the strict
    schemas.Citation — which requires a present target — would reject. The read path must not
    hydrate stale rows into schemas.Citation; it filters them or projects them into an
    "evidence unavailable" form. The ORM->schema read mapping (with a round-trip test for the
    stale case) will encode that when it is built. See docs/02-data-model.md 2.8.
    """

    __tablename__ = "citations"
    __table_args__ = (
        # The kind-consistency half of the invariant: only the target matching `kind` may be
        # set. "Matching target present" stays the Pydantic validator's job, since SET NULL
        # can legitimately null a matching reference after the fact.
        CheckConstraint(
            "(kind = 'code_chunk' AND convention_id IS NULL AND diff_ref IS NULL) "
            "OR (kind = 'convention' AND code_chunk_id IS NULL AND diff_ref IS NULL) "
            "OR (kind = 'diff_hunk' AND code_chunk_id IS NULL AND convention_id IS NULL)",
            name="target_matches_kind",
        ),
    )

    review_comment_id: Mapped[int] = mapped_column(
        ForeignKey("review_comments.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[CitationKind] = mapped_column(_str_enum(CitationKind))
    code_chunk_id: Mapped[int | None] = mapped_column(
        ForeignKey("code_chunks.id", ondelete="SET NULL"), index=True
    )
    convention_id: Mapped[int | None] = mapped_column(
        ForeignKey("conventions.id", ondelete="SET NULL"), index=True
    )
    diff_ref: Mapped[str | None] = mapped_column(String(255))
