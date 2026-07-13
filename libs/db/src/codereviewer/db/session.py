from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def make_engine(url: str, *, echo: bool = False) -> AsyncEngine:
    """Create the async engine. (Named to avoid confusion with SQLAlchemy's sync ``create_engine``.)

    ``pool_pre_ping`` validates a pooled connection before use, so a connection dropped by
    the database (idle timeout, restart) is transparently replaced instead of surfacing as a
    stale-connection error on the next query.
    """
    return create_async_engine(url, echo=echo, pool_pre_ping=True)


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Build the session factory bound to ``engine``.

    ``expire_on_commit=False`` so ORM objects stay usable after ``commit()``. Otherwise the
    next attribute access would trigger a lazy refresh — a synchronous DB call on the async
    path, which raises.
    """
    return async_sessionmaker(engine, expire_on_commit=False)


@asynccontextmanager
async def session_scope(
    factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    """Yield a session for a unit of work, rolling back if the block raises.

    The scope guarantees rollback-on-error and close-on-exit, but callers **must commit
    explicitly** on success — uncommitted work is silently discarded on close. For a single
    write that should auto-commit, use SQLAlchemy's ``async with factory.begin() as session``
    instead, which commits on success and rolls back on error.
    """
    async with factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
