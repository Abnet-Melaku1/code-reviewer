from datetime import datetime
from enum import StrEnum

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    false,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from codereviewer.db.base import Base, IntPk, TimestampMixin
from codereviewer.schemas import IndexStatus, Language, SymbolKind

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
