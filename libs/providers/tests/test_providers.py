import json

import pytest

from codereviewer.providers.fake import FakeEmbeddingsProvider, FakeLlmProvider


@pytest.mark.anyio
async def test_fake_embeddings_provider() -> None:
    provider = FakeEmbeddingsProvider(dimension=1024)

    assert provider.dimension == 1024

    texts = ["hello", "world"]
    embeddings = await provider.embed_texts(texts)

    assert len(embeddings) == 2
    assert len(embeddings[0]) == 1024
    assert len(embeddings[1]) == 1024

    # Assert deterministic output (same text generates same embedding)
    embeddings_again = await provider.embed_texts(["hello"])
    assert embeddings[0] == embeddings_again[0]

    # Empty text case
    assert await provider.embed_texts([]) == []


@pytest.mark.anyio
async def test_fake_llm_provider() -> None:
    provider = FakeLlmProvider()
    response = await provider.generate_response("sys", "user")
    data = json.loads(response)
    assert len(data) == 1
    assert data[0]["file_path"] == "src/main.py"

    custom_provider = FakeLlmProvider(default_response="[]")
    assert await custom_provider.generate_response("sys", "user") == "[]"
