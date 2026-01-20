"""Embedding providers for semantic search."""

from __future__ import annotations

from typing import TYPE_CHECKING

from claude_smart_fork.embeddings.base import EmbeddingProvider

if TYPE_CHECKING:
    from claude_smart_fork.config import Config

# Registry of available embedding providers
_PROVIDERS: dict[str, type[EmbeddingProvider]] = {}

# Try to import optional providers
try:
    from claude_smart_fork.embeddings.local import LocalEmbeddingProvider

    _PROVIDERS["local"] = LocalEmbeddingProvider
except ImportError:
    pass

try:
    from claude_smart_fork.embeddings.api import OpenAIEmbeddingProvider

    _PROVIDERS["openai"] = OpenAIEmbeddingProvider
except ImportError:
    pass


def get_embedding_provider(config: Config) -> EmbeddingProvider | None:
    """
    Get the appropriate embedding provider based on configuration.

    Returns None if no embedding provider is available/configured.
    """
    provider_name = config.embedding_provider

    if provider_name == "none" or provider_name not in _PROVIDERS:
        return None

    provider_class = _PROVIDERS[provider_name]
    return provider_class(config)


def list_available_providers() -> list[str]:
    """List all available embedding provider names."""
    return list(_PROVIDERS.keys())


__all__ = [
    "EmbeddingProvider",
    "get_embedding_provider",
    "list_available_providers",
]
