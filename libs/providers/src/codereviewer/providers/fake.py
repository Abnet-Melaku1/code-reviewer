from codereviewer.providers.base import EmbeddingsProvider


class FakeEmbeddingsProvider(EmbeddingsProvider):
    """Deterministic fake embeddings provider for testing and sandbox runs."""

    def __init__(self, dimension: int = 1024):
        self._dimension = dimension

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Embed a list of texts deterministically using pseudo-random generation."""
        if not texts:
            return []

        embeddings = []
        for text_val in texts:
            # Generate a deterministic mock float value bounded between 0 and 1
            h = hash(text_val)
            val = float(abs(h) % 1000) / 1000.0
            embeddings.append([val] * self._dimension)

        return embeddings

    @property
    def dimension(self) -> int:
        """The mock dimension."""
        return self._dimension
