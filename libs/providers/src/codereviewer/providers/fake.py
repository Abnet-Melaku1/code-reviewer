import json

from codereviewer.providers.base import EmbeddingsProvider, LlmProvider


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


class FakeLlmProvider(LlmProvider):
    """Deterministic fake LLM completion provider for offline review testing."""

    def __init__(self, default_response: str | None = None):
        self._default_response = default_response

    async def generate_response(
        self, system_prompt: str, user_prompt: str, temperature: float = 0.2
    ) -> str:
        """Generate a deterministic completion containing mock comments."""
        if self._default_response is not None:
            return self._default_response

        mock_comments = [
            {
                "file_path": "src/main.py",
                "line": 10,
                "side": "right",
                "severity": "nit",
                "body": "Fake review comment grounded in code style conventions.",
                "suggested_patch": "@@ -10,1 +10,1 @@\n-print('hello')\n+print('hello world')",
                "citation_ids": [1],
                "citation_conventions": ["CodeReviewer Default Style"],
            }
        ]
        return json.dumps(mock_comments)
