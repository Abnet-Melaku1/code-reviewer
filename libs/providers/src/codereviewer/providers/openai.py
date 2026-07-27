from openai import AsyncOpenAI

from codereviewer.providers.base import EmbeddingsProvider, LlmProvider


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


class OpenAiLlmProvider(LlmProvider):
    """OpenAI Chat Completion provider wrapper."""

    def __init__(self, api_key: str, model_name: str = "gpt-4o"):
        self._client = AsyncOpenAI(api_key=api_key)
        self._model_name = model_name

    async def generate_response(
        self, system_prompt: str, user_prompt: str, temperature: float = 0.2
    ) -> str:
        """Generate response using OpenAI chat completions."""
        response = await self._client.chat.completions.create(
            model=self._model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
        )
        content = response.choices[0].message.content
        return content if content is not None else ""
