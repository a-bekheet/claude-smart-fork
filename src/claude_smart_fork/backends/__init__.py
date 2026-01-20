"""Storage backends for session indexing."""

from __future__ import annotations

from typing import TYPE_CHECKING

from claude_smart_fork.backends.base import Backend, SearchResult
from claude_smart_fork.backends.sqlite import SQLiteBackend

if TYPE_CHECKING:
    from claude_smart_fork.config import Config

# Registry of available backends
_BACKENDS: dict[str, type[Backend]] = {
    "sqlite": SQLiteBackend,
}

# Try to import optional backends
try:
    from claude_smart_fork.backends.chromadb import ChromaDBBackend

    _BACKENDS["chromadb"] = ChromaDBBackend
except ImportError:
    pass


def get_backend(config: Config) -> Backend:
    """
    Get the appropriate backend based on configuration.

    Falls back to SQLite if the requested backend is not available.
    """
    backend_name = config.backend

    if backend_name not in _BACKENDS:
        # Fall back to sqlite
        backend_name = "sqlite"

    backend_class = _BACKENDS[backend_name]
    return backend_class(config)


def list_available_backends() -> list[str]:
    """List all available backend names."""
    return list(_BACKENDS.keys())


__all__ = [
    "Backend",
    "SearchResult",
    "SQLiteBackend",
    "get_backend",
    "list_available_backends",
]
