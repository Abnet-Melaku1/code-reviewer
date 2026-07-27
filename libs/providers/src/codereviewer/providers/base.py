from typing import Protocol


class EmbeddingsProvider(Protocol):
    """Protocol for embedding models."""

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a list of texts asynchronously."""
        ...

    @property
    def dimension(self) -> int:
        """The output dimension of the embedding vectors."""
        ...
