from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from codereviewer.indexer.pipeline import index_repository_files
from codereviewer.indexer.walker import FileCandidate
from codereviewer.providers.fake import FakeEmbeddingsProvider
from codereviewer.schemas.enums import IndexStatus, Language


@pytest.mark.anyio
async def test_index_repository_files_pipeline() -> None:
    # 1. Setup mock session and fake embeddings provider
    session = AsyncMock()
    session.add = MagicMock()  # add is synchronous in AsyncSession
    provider = FakeEmbeddingsProvider(dimension=1024)

    # Mock Repository DB model returned by session.execute
    mock_repo = MagicMock()
    mock_repo.id = 42
    mock_repo.index_status = IndexStatus.pending
    mock_repo.indexed_commit_sha = None
    mock_repo.last_indexed_at = None

    # Mock return value for session.execute when fetching repository
    mock_execute_result = MagicMock()
    mock_execute_result.scalar_one.return_value = mock_repo

    # Also for conventions query
    mock_convention_result = MagicMock()
    mock_convention_result.scalars.return_value.all.return_value = []

    # Configure session.execute side effects
    async def side_effect(query: object) -> MagicMock:
        query_str = str(query)
        if "repositories" in query_str:
            return mock_execute_result
        if "conventions" in query_str:
            return mock_convention_result
        return MagicMock()

    session.execute.side_effect = side_effect

    # 2. Patch walk_files and test with a simple Python candidate file
    mock_candidates = [
        FileCandidate(
            path="src/main.py",
            language=Language.python,
            blob_sha="hash123",
            content="class Test:\n    pass\n",
        )
    ]

    with patch(
        "codereviewer.indexer.pipeline.walk_files", return_value=mock_candidates
    ) as mock_walk:
        # Run index pipeline
        await index_repository_files(
            session=session,
            repo_path="/path/to/mock/repo",
            repository_id=42,
            provider=provider,
            commit_sha="commit_abc123",
        )

        # 3. Verify interactions
        mock_walk.assert_called_once_with("/path/to/mock/repo")

        # Verify status transitions on repo
        assert mock_repo.index_status == IndexStatus.ready
        assert mock_repo.indexed_commit_sha == "commit_abc123"
        assert mock_repo.last_indexed_at is not None

        # Verify session calls (at least flush() is called twice to generate IDs)
        assert session.flush.call_count >= 2

        # Verify added objects
        added_objs = [call[0][0] for call in session.add.call_args_list]

        # Assert an IndexedFile is added
        indexed_files = [obj for obj in added_objs if obj.__class__.__name__ == "IndexedFile"]
        assert len(indexed_files) == 1
        assert indexed_files[0].path == "src/main.py"
        assert indexed_files[0].blob_sha == "hash123"

        # Assert a CodeChunk is added
        chunks = [obj for obj in added_objs if obj.__class__.__name__ == "CodeChunk"]
        assert len(chunks) == 1
        assert chunks[0].symbol_name == "Test"
        assert len(chunks[0].embedding) == 1024

        # Assert a Convention is added (by the infer_conventions stub)
        conventions = [obj for obj in added_objs if obj.__class__.__name__ == "Convention"]
        assert len(conventions) == 1
        assert conventions[0].title == "CodeReviewer Default Style"
