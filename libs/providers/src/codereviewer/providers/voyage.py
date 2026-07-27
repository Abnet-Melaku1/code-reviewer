from typing import cast
import voyageai

from codereviewer.providers.base import EmbeddingsProvider


class VoyageEmbeddingsProvider(EmbeddingsProvider):
    """Voyage AI embeddings provider wrapper."""

    def __init__(self, api_key: str, model_name: str = "voyage-code-3", dimension: int = 1024):
        self._client = voyageai.AsyncClient(api_key=api_key)  # type: ignore[attr-defined]
        self._model_name = model_name
        self._dimension = dimension

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Embed a list of texts asynchronously using Voyage AI."""
        if not texts:
            return []
        # input_type="document" is recommended by Voyage for general document/code chunk indexing
        response = await self._client.embed(
            texts,
            model=self._model_name,
            input_type="document",
        )
        return cast(list[list[float]], response.embeddings)

    @property
    def dimension(self) -> int:
        """The output dimension of the Voyage embedding model."""
        return self._dimension
