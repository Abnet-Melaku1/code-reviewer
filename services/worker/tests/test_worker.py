from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest

from codereviewer.providers.fake import FakeEmbeddingsProvider
from codereviewer.worker.config import WorkerConfig
from codereviewer.worker.jobs import get_embeddings_provider, index_repo


def test_worker_config() -> None:
    config = WorkerConfig(embeddings_provider="openai", embeddings_model="text-embedding-3-large")
    assert config.embeddings_provider == "openai"
    assert config.embeddings_model == "text-embedding-3-large"


def test_get_embeddings_provider_default() -> None:
    # Default config specifies "fake" provider
    provider = get_embeddings_provider()
    assert isinstance(provider, FakeEmbeddingsProvider)


@pytest.mark.anyio
@patch("codereviewer.worker.jobs.clone_repository")
@patch("codereviewer.worker.jobs.index_repository_files", new_callable=AsyncMock)
@patch("codereviewer.worker.jobs.db_session")
@patch("codereviewer.worker.jobs.tempfile.mkdtemp")
@patch("codereviewer.worker.jobs.shutil.rmtree")
async def test_index_repo_job(
    mock_rmtree: MagicMock,
    mock_mkdtemp: MagicMock,
    mock_db_session: MagicMock,
    mock_index_pipeline: AsyncMock,
    mock_clone: MagicMock,
) -> None:
    mock_mkdtemp.return_value = "/tmp/mock-repo"

    mock_engine = AsyncMock()
    mock_session = AsyncMock()

    mock_db_session.make_engine.return_value = mock_engine
    mock_db_session.create_session_factory.return_value = MagicMock()

    # Mock session scope context manager
    class MockSessionScope:
        async def __aenter__(self) -> AsyncMock:
            return mock_session

        async def __aexit__(self, *args: object) -> None:
            pass

    mock_db_session.session_scope.return_value = MockSessionScope()

    # Call job
    ctx: dict[str, object] = {}
    await index_repo(
        ctx,
        repository_id=123,
        clone_url="https://github.com/org/repo.git",
        commit_sha="sha_abc",
    )

    # Asserts
    mock_mkdtemp.assert_called_once()
    mock_clone.assert_called_once_with("https://github.com/org/repo.git", "/tmp/mock-repo")

    # Assert pipeline invocation
    mock_index_pipeline.assert_called_once_with(
        session=mock_session,
        repo_path="/tmp/mock-repo",
        repository_id=123,
        provider=ANY,
        commit_sha="sha_abc",
    )

    # Verify clean up and resources disposal
    mock_rmtree.assert_called_once_with("/tmp/mock-repo", ignore_errors=True)
    mock_engine.dispose.assert_called_once()
