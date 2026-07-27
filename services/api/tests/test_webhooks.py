import hashlib
import hmac
import json
from collections.abc import AsyncGenerator
from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from codereviewer.api.main import create_app
from codereviewer.api.webhooks import get_db_session


@pytest.fixture
def client_and_mocks() -> tuple[TestClient, AsyncMock]:
    """Provide a TestClient with overridden database session dependencies."""
    app = create_app()
    mock_session = AsyncMock()
    mock_session.add = MagicMock()

    async def override_db() -> AsyncGenerator[AsyncSession, None]:
        yield mock_session

    app.dependency_overrides[get_db_session] = override_db

    client = TestClient(app)
    return client, mock_session


def test_webhook_unauthorized(
    client_and_mocks: tuple[TestClient, AsyncMock],
) -> None:
    client, _ = client_and_mocks
    response = client.post("/webhooks/github", content=b"{}")
    assert response.status_code == 401


def test_webhook_invalid_signature(
    client_and_mocks: tuple[TestClient, AsyncMock],
) -> None:
    client, _ = client_and_mocks
    headers = {"X-Hub-Signature-256": "sha256=invalid"}
    response = client.post("/webhooks/github", content=b"{}", headers=headers)
    assert response.status_code == 401


@patch("codereviewer.api.webhooks.create_pool")
def test_webhook_valid_signature_bad_json(
    mock_pool: MagicMock,
    client_and_mocks: tuple[TestClient, AsyncMock],
) -> None:
    client, _ = client_and_mocks
    secret = "super_secret_webhook_key"
    body = b"not a json"
    sig = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    headers = {"X-Hub-Signature-256": sig}
    response = client.post("/webhooks/github", content=body, headers=headers)
    assert response.status_code == 400


@patch("codereviewer.api.webhooks.create_pool")
def test_webhook_installation_created(
    mock_create_pool: MagicMock,
    client_and_mocks: tuple[TestClient, AsyncMock],
) -> None:
    client, mock_session = client_and_mocks

    mock_redis = AsyncMock()
    mock_create_pool.return_value = mock_redis

    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = None
    mock_session.execute.return_value = mock_result

    payload = {
        "action": "created",
        "installation": {"id": 123},
        "repositories": [{"full_name": "owner/repo"}],
    }
    body = json.dumps(payload).encode()
    secret = "super_secret_webhook_key"
    sig = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

    headers = {
        "X-Hub-Signature-256": sig,
        "X-GitHub-Event": "installation",
    }
    response = client.post("/webhooks/github", content=body, headers=headers)
    assert response.status_code == 202
    assert response.json() == {"status": "enqueued"}

    mock_redis.enqueue_job.assert_called_once_with(
        "index_repo",
        repository_id=ANY,
        clone_url="https://github.com/owner/repo.git",
        commit_sha="HEAD",
    )
