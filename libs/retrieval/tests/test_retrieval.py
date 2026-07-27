from unittest.mock import AsyncMock, MagicMock

import pytest

from codereviewer.providers.fake import FakeEmbeddingsProvider
from codereviewer.retrieval.retriever import Retriever
from codereviewer.schemas.enums import DiffSide
from codereviewer.schemas.models import DiffHunk


@pytest.mark.anyio
async def test_retriever_retrieve_context() -> None:
    session = AsyncMock()
    provider = FakeEmbeddingsProvider(dimension=1024)

    # Mock CodeChunk and Convention query results
    mock_chunk = MagicMock()
    mock_chunk.symbol_kind = "function"
    mock_chunk.symbol_name = "test_fun"
    mock_chunk.start_line = 1
    mock_chunk.end_line = 5
    mock_chunk.content = "def test_fun():\n    pass"
    mock_chunk.token_count = 10

    mock_conv = MagicMock()
    mock_conv.title = "Test Convention"
    mock_conv.description = "Test description"
    mock_conv.example_code = "def test(): pass"
    mock_conv.source = "inferred"
    mock_conv.confidence = 0.9
    mock_conv.active = True

    mock_chunk_result = MagicMock()
    mock_chunk_result.scalars.return_value.all.return_value = [mock_chunk]

    mock_conv_result = MagicMock()
    mock_conv_result.scalars.return_value.all.return_value = [mock_conv]

    async def side_effect(query: object) -> MagicMock:
        query_str = str(query)
        if "code_chunks" in query_str:
            return mock_chunk_result
        if "conventions" in query_str:
            return mock_conv_result
        return MagicMock()

    session.execute.side_effect = side_effect

    # Bypass SQLite dialect check path
    session.bind = MagicMock()
    session.bind.dialect.name = "sqlite"

    retriever = Retriever(session, provider)
    hunk = DiffHunk(
        file_path="src/main.py",
        content="@@ -10,3 +10,3 @@\n def fun():\n-    pass\n+    print('hi')",
        start_line=10,
        end_line=12,
        side=DiffSide.right,
    )

    context = await retriever.retrieve_context(repository_id=42, hunk=hunk, limit=2)

    assert len(context.chunks) == 1
    assert context.chunks[0].symbol_name == "test_fun"
    assert len(context.conventions) == 1
    assert context.conventions[0].title == "Test Convention"
