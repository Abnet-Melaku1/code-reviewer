import pytest

from codereviewer.providers.fake import FakeEmbeddingsProvider


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
