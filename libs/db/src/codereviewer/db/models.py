from datetime import datetime
from enum import StrEnum

from sqlalchemy import BigInteger, DateTime, Enum, String, UniqueConstraint, false, text
from sqlalchemy.orm import Mapped, mapped_column

from codereviewer.db.base import Base, IntPk, TimestampMixin
from codereviewer.schemas import IndexStatus


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
    __table_args__ = (UniqueConstraint("owner", "name", name="uq_repositories_owner_name"),)

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
