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


class LlmProvider(Protocol):
    """Protocol for LLM text generation providers used in reviews."""

    async def generate_response(
        self, system_prompt: str, user_prompt: str, temperature: float = 0.2
    ) -> str:
        """Generate text completion from a system prompt and a user prompt asynchronously."""
        ...
