from collections.abc import AsyncGenerator
from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

import codereviewer.db.models as db_models
from codereviewer.api.main import create_app
from codereviewer.api.webhooks import get_db_session
from codereviewer.schemas.enums import IndexStatus


@pytest.fixture
def client_and_mocks() -> tuple[TestClient, AsyncMock, MagicMock]:
    """Provide a TestClient with overridden database session and mock arq pool."""
    app = create_app()
    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()

    async def override_db() -> AsyncGenerator[AsyncSession, None]:
        yield mock_session

    app.dependency_overrides[get_db_session] = override_db

    # Mock the arq pool on app state
    mock_arq = AsyncMock()
    app.state.arq_pool = mock_arq

    client = TestClient(app)
    return client, mock_session, mock_arq


def test_list_repositories(
    client_and_mocks: tuple[TestClient, AsyncMock, MagicMock],
) -> None:
    client, mock_session, _ = client_and_mocks

    # Mock DB return value
    mock_repo = db_models.Repository(
        id=10,
        github_installation_id=123,
        owner="org",
        name="repo",
        default_branch="main",
        index_status=IndexStatus.ready,
        posting_enabled=True,
    )
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_repo]
    mock_session.execute.return_value = mock_result

    response = client.get("/api/v1/repositories")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == 10
    assert data[0]["owner"] == "org"
    assert data[0]["index_status"] == "ready"


def test_register_repository(
    client_and_mocks: tuple[TestClient, AsyncMock, MagicMock],
) -> None:
    client, mock_session, mock_arq = client_and_mocks

    # Mock select duplicate repo returns None
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = None
    mock_session.execute.return_value = mock_result

    # Mock refresh to populate the id
    def mock_refresh(instance: db_models.Repository) -> None:
        instance.id = 55

    mock_session.refresh.side_effect = mock_refresh

    payload = {
        "github_installation_id": 999,
        "owner": "org",
        "name": "new-repo",
        "default_branch": "main",
    }
    response = client.post("/api/v1/repositories", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["id"] == 55
    assert data["name"] == "new-repo"

    # Verify arq indexing task is enqueued
    mock_arq.enqueue_job.assert_called_once_with(
        "index_repo",
        repository_id=55,
        clone_url="https://github.com/org/new-repo.git",
        commit_sha="HEAD",
    )


def test_patch_repository_settings(
    client_and_mocks: tuple[TestClient, AsyncMock, MagicMock],
) -> None:
    client, mock_session, _ = client_and_mocks

    mock_repo = db_models.Repository(
        id=12,
        github_installation_id=123,
        owner="org",
        name="repo",
        default_branch="main",
        index_status=IndexStatus.ready,
        posting_enabled=False,
    )
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = mock_repo
    mock_session.execute.return_value = mock_result

    payload = {"posting_enabled": True}
    response = client.patch("/api/v1/repositories/12", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["posting_enabled"] is True
    assert mock_repo.posting_enabled is True
    mock_session.commit.assert_called_once()


def test_trigger_review_pr(
    client_and_mocks: tuple[TestClient, AsyncMock, MagicMock],
) -> None:
    client, mock_session, mock_arq = client_and_mocks

    # Mock PR retrieval and Repository retrieval
    mock_pr = db_models.PullRequest(
        id=88,
        repository_id=10,
        number=5,
        head_sha="head_sha",
        base_sha="base_sha",
        title="test PR",
        author="coder",
    )
    mock_repo = db_models.Repository(
        id=10,
        github_installation_id=123,
        owner="org",
        name="repo",
        default_branch="main",
    )

    mock_pr_result = MagicMock()
    mock_pr_result.scalars.return_value.first.return_value = mock_pr

    mock_repo_result = MagicMock()
    mock_repo_result.scalars.return_value.first.return_value = mock_repo

    # Mock duplicate check return value None
    mock_dup_result = MagicMock()
    mock_dup_result.scalars.return_value.first.return_value = None

    # Make execute return different mock values sequentially
    mock_session.execute.side_effect = [mock_pr_result, mock_repo_result, mock_dup_result]

    # Mock refresh to populate the review id
    def mock_refresh(instance: db_models.Review) -> None:
        instance.id = 999

    mock_session.refresh.side_effect = mock_refresh

    response = client.post("/api/v1/pulls/88/reviews")
    assert response.status_code == 201
    data = response.json()
    assert data["id"] == 999
    assert data["status"] == "queued"

    mock_arq.enqueue_job.assert_called_once_with(
        "review_pr",
        pull_request_id=88,
        repository_id=10,
        clone_url="https://github.com/org/repo.git",
        commit_sha="head_sha",
        base_sha="base_sha",
    )
