"""Base classes and protocols for storage backends."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from claude_smart_fork.config import Config


@dataclass
class SessionSummary:
    """Summary data for a session."""

    session_id: str
    project_path: str
    git_branch: str | None
    topic: str
    key_decisions: list[str]
    files_modified: list[str]
    technologies: list[str]
    outcome: str
    message_count: int
    duration_minutes: float
    created_at: str
    last_updated: str

    def to_embedding_text(self) -> str:
        """Create text optimized for embedding."""
        parts = [
            self.topic,
            f"Project: {self.project_path}",
        ]

        if self.git_branch:
            parts.append(f"Branch: {self.git_branch}")

        if self.key_decisions:
            parts.append("Key decisions: " + "; ".join(self.key_decisions))

        if self.technologies:
            parts.append("Technologies: " + ", ".join(self.technologies))

        if self.files_modified:
            parts.append("Files: " + ", ".join(self.files_modified[:10]))

        if self.outcome:
            parts.append(f"Outcome: {self.outcome}")

        return "\n".join(parts)

    def to_search_text(self) -> str:
        """Create text for keyword search."""
        parts = [
            self.topic,
            self.project_path,
            self.git_branch or "",
            " ".join(self.key_decisions),
            " ".join(self.technologies),
            " ".join(self.files_modified),
            self.outcome,
        ]
        return " ".join(p for p in parts if p)


@dataclass
class SearchResult:
    """A single search result."""

    session_id: str
    score: float  # 0-100 percentage
    summary: SessionSummary
    match_type: str = "semantic"  # 'semantic' or 'keyword'

    @property
    def fork_command(self) -> str:
        """Get the command to fork this session."""
        return f"claude --resume {self.session_id}"


@runtime_checkable
class Backend(Protocol):
    """Protocol for storage backends."""

    def __init__(self, config: Config) -> None:
        """Initialize the backend with configuration."""
        ...

    def index_session(self, summary: SessionSummary, embedding: list[float] | None = None) -> None:
        """
        Index a session summary.

        Args:
            summary: The session summary to index
            embedding: Optional pre-computed embedding vector
        """
        ...

    def search(
        self,
        query: str,
        query_embedding: list[float] | None = None,
        limit: int = 5,
        project_filter: str | None = None,
    ) -> list[SearchResult]:
        """
        Search for sessions.

        Args:
            query: Search query text
            query_embedding: Optional pre-computed query embedding
            limit: Maximum results to return
            project_filter: Optional project path filter

        Returns:
            List of search results, sorted by relevance
        """
        ...

    def get_session(self, session_id: str) -> SessionSummary | None:
        """Get a session by ID."""
        ...

    def delete_session(self, session_id: str) -> bool:
        """Delete a session from the index."""
        ...

    def get_stats(self) -> dict[str, Any]:
        """Get statistics about the index."""
        ...

    def is_indexed(self, session_id: str) -> bool:
        """Check if a session is already indexed."""
        ...

    def clear(self) -> None:
        """Clear all indexed data."""
        ...


class BaseBackend(ABC):
    """Abstract base class for backends with common functionality."""

    def __init__(self, config: Config) -> None:
        self.config = config

    @abstractmethod
    def index_session(self, summary: SessionSummary, embedding: list[float] | None = None) -> None:
        """Index a session summary."""
        pass

    @abstractmethod
    def search(
        self,
        query: str,
        query_embedding: list[float] | None = None,
        limit: int = 5,
        project_filter: str | None = None,
    ) -> list[SearchResult]:
        """Search for sessions."""
        pass

    @abstractmethod
    def get_session(self, session_id: str) -> SessionSummary | None:
        """Get a session by ID."""
        pass

    @abstractmethod
    def delete_session(self, session_id: str) -> bool:
        """Delete a session from the index."""
        pass

    @abstractmethod
    def get_stats(self) -> dict[str, Any]:
        """Get statistics about the index."""
        pass

    @abstractmethod
    def is_indexed(self, session_id: str) -> bool:
        """Check if a session is already indexed."""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear all indexed data."""
        pass
