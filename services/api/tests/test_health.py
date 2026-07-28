from collections.abc import AsyncIterator, Generator
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from codereviewer.api.main import create_app


@pytest.fixture
def mock_dependencies() -> Generator[tuple[MagicMock, AsyncMock, AsyncMock], None, None]:
    with (
        patch("codereviewer.api.main.make_engine") as mock_make_engine,
        patch("codereviewer.api.main.Redis.from_url") as mock_redis_from_url,
    ):
        mock_engine = MagicMock()
        mock_conn = AsyncMock()
        mock_engine.connect.return_value.__aenter__.return_value = mock_conn
        mock_make_engine.return_value = mock_engine

        mock_redis = AsyncMock()
        mock_redis.ping.return_value = True
        mock_redis_from_url.return_value = mock_redis

        yield mock_engine, mock_redis, mock_conn


@pytest.fixture
async def client(mock_dependencies: Any) -> AsyncIterator[AsyncClient]:
    app = create_app()
    mock_engine, mock_redis, _ = mock_dependencies
    app.state.db_engine = mock_engine
    app.state.redis_client = mock_redis

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client


async def test_healthz_reports_ok(client: AsyncClient) -> None:
    response = await client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_readyz_reports_ready(client: AsyncClient) -> None:
    response = await client.get("/readyz")

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


async def test_readyz_db_failure(
    client: AsyncClient,
    mock_dependencies: tuple[MagicMock, AsyncMock, AsyncMock],
) -> None:
    _, _, mock_conn = mock_dependencies
    mock_conn.execute.side_effect = Exception("Connection refused")

    response = await client.get("/readyz")
    assert response.status_code == 503
    assert "Database connection failed" in response.json()["detail"]


async def test_readyz_redis_failure(
    client: AsyncClient,
    mock_dependencies: tuple[MagicMock, AsyncMock, AsyncMock],
) -> None:
    _, mock_redis, _ = mock_dependencies
    mock_redis.ping.side_effect = Exception("Host unreachable")

    response = await client.get("/readyz")
    assert response.status_code == 503
    assert "Redis connection failed" in response.json()["detail"]


async def test_openapi_schema_is_served(client: AsyncClient) -> None:
    response = await client.get("/openapi.json")

    assert response.status_code == 200
    assert response.json()["info"]["title"] == "CodeReviewer.ai API"
