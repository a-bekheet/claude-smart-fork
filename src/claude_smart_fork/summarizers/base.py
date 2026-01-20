"""Base classes for summarization providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from claude_smart_fork.config import Config
    from claude_smart_fork.parser import SessionData


@dataclass
class SessionSummaryData:
    """Data structure for session summary."""

    topic: str
    key_decisions: list[str]
    files_modified: list[str]
    technologies: list[str]
    outcome: str


@runtime_checkable
class Summarizer(Protocol):
    """Protocol for summarization providers."""

    def __init__(self, config: Config) -> None:
        """Initialize the summarizer with configuration."""
        ...

    def summarize(self, session: SessionData) -> SessionSummaryData:
        """
        Generate a summary for a session.

        Args:
            session: Parsed session data

        Returns:
            Summary data structure
        """
        ...

    @property
    def name(self) -> str:
        """Return the summarizer name."""
        ...


class BaseSummarizer(ABC):
    """Abstract base class for summarizers."""

    def __init__(self, config: Config) -> None:
        self.config = config

    @abstractmethod
    def summarize(self, session: SessionData) -> SessionSummaryData:
        """Generate a summary for a session."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the summarizer name."""
        pass
