from datetime import datetime

from sqlalchemy import BigInteger, DateTime, MetaData, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Deterministic constraint/index names so Alembic autogenerate produces stable, reviewable
# migrations instead of database-assigned random names.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class IntPk:
    """Surrogate primary key. BigInteger by default so high-volume tables (e.g. code_chunks)
    never approach the ~2.1B int32 ceiling."""

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)


class TimestampMixin:
    """Audit timestamps maintained by the database, not the application."""

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
