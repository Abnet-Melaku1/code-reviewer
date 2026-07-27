from openai import AsyncOpenAI

from codereviewer.providers.base import EmbeddingsProvider


class OpenAIEmbeddingsProvider(EmbeddingsProvider):
    """OpenAI embeddings provider wrapper."""

    def __init__(
        self,
        api_key: str,
        model_name: str = "text-embedding-3-large",
        dimension: int = 1024,
    ):
        self._client = AsyncOpenAI(api_key=api_key)
        self._model_name = model_name
        self._dimension = dimension

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Embed a list of texts asynchronously using OpenAI."""
        if not texts:
            return []

        if "text-embedding-3" in self._model_name:
            response = await self._client.embeddings.create(
                input=texts,
                model=self._model_name,
                dimensions=self._dimension,
            )
        else:
            response = await self._client.embeddings.create(
                input=texts,
                model=self._model_name,
            )
        return [item.embedding for item in response.data]

    @property
    def dimension(self) -> int:
        """The output dimension of the OpenAI embedding model."""
        return self._dimension
