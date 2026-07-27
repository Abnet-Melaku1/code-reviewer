from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from codereviewer.indexer.pipeline import index_repository_delta
from codereviewer.providers.fake import FakeEmbeddingsProvider
from codereviewer.schemas.enums import IndexStatus


@pytest.mark.anyio
async def test_index_repository_delta_pipeline() -> None:
    session = AsyncMock()
    session.add = MagicMock()
    provider = FakeEmbeddingsProvider(dimension=1024)

    # Mock Repository DB model returned by session.execute
    mock_repo = MagicMock()
    mock_repo.id = 42
    mock_repo.index_status = IndexStatus.pending
    mock_repo.indexed_commit_sha = "sha_base"
    mock_repo.last_indexed_at = None

    mock_execute_result = MagicMock()
    mock_execute_result.scalar_one.return_value = mock_repo

    mock_convention_result = MagicMock()
    mock_convention_result.scalars.return_value.all.return_value = []

    async def side_effect(query: object) -> MagicMock:
        query_str = str(query)
        if "repositories" in query_str:
            return mock_execute_result
        if "conventions" in query_str:
            return mock_convention_result
        return MagicMock()

    session.execute.side_effect = side_effect

    mock_delta = {
        "src/added.py": "A",
        "src/modified.py": "M",
        "src/deleted.py": "D",
    }

    file_contents = {
        "src/added.py": "def new_fun():\n    pass\n",
        "src/modified.py": "def mod_fun():\n    pass\n",
    }

    import io

    def custom_open(file: object, mode: str = "r", *args: object, **kwargs: object) -> object:
        normalized = str(file).replace("\\", "/")
        for suffix, content in file_contents.items():
            if normalized.endswith(suffix):
                if "b" in mode:
                    return io.BytesIO(content.encode("utf-8"))
                return io.StringIO(content)
        raise FileNotFoundError(file)

    with (
        patch(
            "codereviewer.indexer.pipeline.get_file_delta", return_value=mock_delta
        ) as mock_get_delta,
        patch("os.path.exists", return_value=True),
        patch("builtins.open", custom_open),
    ):
        await index_repository_delta(
            session=session,
            repo_path="/path/to/mock/repo",
            repository_id=42,
            provider=provider,
            base_sha="sha_base",
            head_sha="sha_head",
        )

        mock_get_delta.assert_called_once_with("/path/to/mock/repo", "sha_base", "sha_head")

        # Check Repository state changes
        assert mock_repo.index_status == IndexStatus.ready
        assert mock_repo.indexed_commit_sha == "sha_head"
        assert mock_repo.last_indexed_at is not None

        # Verify cascading deletes executed
        delete_calls = [
            call[0][0] for call in session.execute.call_args_list if "DELETE" in str(call[0][0])
        ]
        assert len(delete_calls) == 1

        # Verify files and chunks added
        added_objs = [call[0][0] for call in session.add.call_args_list]

        # Assert 2 new/modified IndexedFile models are added
        indexed_files = [obj for obj in added_objs if obj.__class__.__name__ == "IndexedFile"]
        assert len(indexed_files) == 2
        paths = {f.path for f in indexed_files}
        assert paths == {"src/added.py", "src/modified.py"}

        # Assert CodeChunks are added
        chunks = [obj for obj in added_objs if obj.__class__.__name__ == "CodeChunk"]
        assert len(chunks) == 2
        symbols = {c.symbol_name for c in chunks}
        assert symbols == {"new_fun", "mod_fun"}
