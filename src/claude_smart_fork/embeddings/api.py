"""API-based embedding providers (OpenAI, etc.)."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

try:
    import openai

    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

from claude_smart_fork.embeddings.base import BaseEmbeddingProvider

if TYPE_CHECKING:
    from claude_smart_fork.config import Config


class OpenAIEmbeddingProvider(BaseEmbeddingProvider):
    """
    OpenAI embedding provider.

    Requires: pip install openai
    Also requires OPENAI_API_KEY environment variable or config setting.

    Uses text-embedding-3-small by default.
    """

    def __init__(self, config: Config) -> None:
        if not OPENAI_AVAILABLE:
            raise ImportError("openai is not installed. Install with: pip install openai")

        super().__init__(config)

        # Get API key from config or environment
        api_key = config.openai_api_key or os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OpenAI API key not found. "
                "Set CSF_OPENAI_API_KEY environment variable or configure in settings."
            )

        self._client = openai.OpenAI(api_key=api_key)
        self._model_name = "text-embedding-3-small"
        self._dimension = 1536

    def embed(self, text: str) -> list[float]:
        """Generate embedding for a single text."""
        response = self._client.embeddings.create(
            model=self._model_name,
            input=text,
        )
        return list(response.data[0].embedding)

    def embed_query(self, query: str) -> list[float]:
        """Generate embedding for a search query."""
        # OpenAI doesn't use different prefixes for queries
        return self.embed(query)

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts."""
        # OpenAI's API supports batch embedding
        response = self._client.embeddings.create(
            model=self._model_name,
            input=texts,
        )
        return [list(item.embedding) for item in response.data]

    @property
    def dimension(self) -> int:
        """Return the embedding dimension."""
        return self._dimension

    @property
    def model_name(self) -> str:
        """Return the model name."""
        return self._model_name
