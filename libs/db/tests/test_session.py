from typing import cast
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from codereviewer.db.session import create_session_factory, make_engine, session_scope

# A well-formed URL the async engine can be built from without connecting to a database.
URL = "postgresql+asyncpg://user:pass@localhost:5432/codereviewer"


class _FakeSession:
    """Records the transaction calls session_scope makes, so the contract can be asserted
    without a live database."""

    def __init__(self) -> None:
        self.rollback = AsyncMock()
        self.commit = AsyncMock()
        self.close = AsyncMock()

    async def __aenter__(self) -> "_FakeSession":
        return self

    async def __aexit__(self, *exc: object) -> bool:
        await self.close()
        return False


def _factory_yielding(session: _FakeSession) -> async_sessionmaker[AsyncSession]:
    return cast(async_sessionmaker[AsyncSession], lambda: session)


def test_make_engine_is_async_with_expected_driver() -> None:
    engine = make_engine(URL)
    assert isinstance(engine, AsyncEngine)
    assert engine.url.drivername == "postgresql+asyncpg"


def test_session_factory_disables_expire_on_commit() -> None:
    factory = create_session_factory(make_engine(URL))
    assert isinstance(factory, async_sessionmaker)
    assert factory.kw["expire_on_commit"] is False


async def test_session_scope_yields_a_real_session() -> None:
    factory = create_session_factory(make_engine(URL))
    async with session_scope(factory) as session:
        assert isinstance(session, AsyncSession)


async def test_session_scope_rolls_back_and_propagates_on_error() -> None:
    session = _FakeSession()
    with pytest.raises(ValueError):
        async with session_scope(_factory_yielding(session)):
            raise ValueError("boom")

    session.rollback.assert_awaited_once()
    session.commit.assert_not_awaited()
    session.close.assert_awaited_once()


async def test_session_scope_does_not_roll_back_on_success() -> None:
    session = _FakeSession()
    async with session_scope(_factory_yielding(session)):
        pass

    session.rollback.assert_not_awaited()
    session.close.assert_awaited_once()
