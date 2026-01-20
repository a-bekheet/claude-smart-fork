"""Base classes for embedding providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from claude_smart_fork.config import Config


@runtime_checkable
class EmbeddingProvider(Protocol):
    """Protocol for embedding providers."""

    def __init__(self, config: Config) -> None:
        """Initialize the provider with configuration."""
        ...

    def embed(self, text: str) -> list[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector as list of floats
        """
        ...

    def embed_query(self, query: str) -> list[float]:
        """
        Generate embedding for a search query.

        Some models use different prefixes for documents vs queries.

        Args:
            query: Search query to embed

        Returns:
            Embedding vector as list of floats
        """
        ...

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        ...

    @property
    def dimension(self) -> int:
        """Return the embedding dimension."""
        ...

    @property
    def model_name(self) -> str:
        """Return the model name."""
        ...


class BaseEmbeddingProvider(ABC):
    """Abstract base class for embedding providers."""

    def __init__(self, config: Config) -> None:
        self.config = config

    @abstractmethod
    def embed(self, text: str) -> list[float]:
        """Generate embedding for a single text."""
        pass

    def embed_query(self, query: str) -> list[float]:
        """
        Generate embedding for a search query.

        Default implementation just calls embed().
        Override for models that use different query prefixes.
        """
        return self.embed(query)

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for multiple texts.

        Default implementation calls embed() for each text.
        Override for more efficient batch processing.
        """
        return [self.embed(text) for text in texts]

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Return the embedding dimension."""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the model name."""
        pass
