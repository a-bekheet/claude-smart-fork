"""Session summarization providers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from claude_smart_fork.summarizers.base import SessionSummaryData, Summarizer
from claude_smart_fork.summarizers.simple import SimpleSummarizer

if TYPE_CHECKING:
    from claude_smart_fork.config import Config

# Registry of available summarizers
_SUMMARIZERS: dict[str, type[Summarizer]] = {
    "simple": SimpleSummarizer,
}

# Try to import optional summarizers
try:
    from claude_smart_fork.summarizers.claude import ClaudeSummarizer

    _SUMMARIZERS["claude"] = ClaudeSummarizer
except ImportError:
    pass

try:
    from claude_smart_fork.summarizers.ollama import OllamaSummarizer

    _SUMMARIZERS["ollama"] = OllamaSummarizer
except ImportError:
    pass


def get_summarizer(config: Config) -> Summarizer:
    """
    Get the appropriate summarizer based on configuration.

    Falls back to simple summarizer if the requested one is not available.
    """
    summarizer_name = config.summarizer

    if summarizer_name not in _SUMMARIZERS:
        summarizer_name = "simple"

    summarizer_class = _SUMMARIZERS[summarizer_name]
    return summarizer_class(config)


def list_available_summarizers() -> list[str]:
    """List all available summarizer names."""
    return list(_SUMMARIZERS.keys())


__all__ = [
    "Summarizer",
    "SessionSummaryData",
    "SimpleSummarizer",
    "get_summarizer",
    "list_available_summarizers",
]
