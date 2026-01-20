"""Session indexing logic."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Iterator

from claude_smart_fork.backends import get_backend
from claude_smart_fork.backends.base import SessionSummary
from claude_smart_fork.config import Config, IndexState, SessionIndexInfo, get_config
from claude_smart_fork.embeddings import get_embedding_provider
from claude_smart_fork.parser import SessionData, get_all_session_files, parse_session_file
from claude_smart_fork.summarizers import get_summarizer

if TYPE_CHECKING:
    from claude_smart_fork.backends.base import Backend
    from claude_smart_fork.embeddings.base import EmbeddingProvider
    from claude_smart_fork.summarizers.base import Summarizer


class Indexer:
    """Manages session indexing."""

    def __init__(self, config: Config | None = None) -> None:
        self.config = config or get_config()
        self.config.ensure_directories()

        self._backend: Backend | None = None
        self._embedding_provider: EmbeddingProvider | None = None
        self._summarizer: Summarizer | None = None
        self._state: IndexState | None = None

    @property
    def backend(self) -> Backend:
        """Lazy-load the backend."""
        if self._backend is None:
            self._backend = get_backend(self.config)
        return self._backend

    @property
    def embedding_provider(self) -> EmbeddingProvider | None:
        """Lazy-load the embedding provider."""
        if self._embedding_provider is None:
            self._embedding_provider = get_embedding_provider(self.config)
        return self._embedding_provider

    @property
    def summarizer(self) -> Summarizer:
        """Lazy-load the summarizer."""
        if self._summarizer is None:
            self._summarizer = get_summarizer(self.config)
        return self._summarizer

    @property
    def state(self) -> IndexState:
        """Load index state."""
        if self._state is None:
            self._state = self._load_state()
        return self._state

    def _load_state(self) -> IndexState:
        """Load index state from disk."""
        if self.config.state_path.exists():
            with open(self.config.state_path) as f:
                data = json.load(f)
                return IndexState(
                    last_full_index=data.get("last_full_index"),
                    indexed_sessions={
                        k: SessionIndexInfo(**v)
                        for k, v in data.get("indexed_sessions", {}).items()
                    },
                )
        return IndexState()

    def _save_state(self) -> None:
        """Save index state to disk."""
        self.config.state_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config.state_path, "w") as f:
            json.dump(
                {
                    "last_full_index": self.state.last_full_index,
                    "indexed_sessions": {
                        k: v.model_dump() for k, v in self.state.indexed_sessions.items()
                    },
                },
                f,
                indent=2,
            )

    def is_indexed(self, session_id: str) -> bool:
        """Check if a session is already indexed."""
        return session_id in self.state.indexed_sessions

    def needs_update(self, session: SessionData) -> bool:
        """Check if a session needs to be re-indexed."""
        if session.session_id not in self.state.indexed_sessions:
            return True

        info = self.state.indexed_sessions[session.session_id]
        return info.message_count < session.message_count

    def get_unindexed_sessions(self) -> list[Path]:
        """Get list of session files that haven't been indexed."""
        all_files = get_all_session_files(self.config.sessions_path)
        return [f for f in all_files if f.stem not in self.state.indexed_sessions]

    def index_session(self, session: SessionData, force: bool = False) -> bool:
        """
        Index a single session.

        Args:
            session: Parsed session data
            force: Force re-indexing even if already indexed

        Returns:
            True if indexed, False if skipped
        """
        if not force and not self.needs_update(session):
            return False

        # Generate summary
        summary_data = self.summarizer.summarize(session)

        # Create full summary object
        now = datetime.now().isoformat()
        summary = SessionSummary(
            session_id=session.session_id,
            project_path=session.project_path,
            git_branch=session.git_branch,
            topic=summary_data.topic,
            key_decisions=summary_data.key_decisions,
            files_modified=summary_data.files_modified,
            technologies=summary_data.technologies,
            outcome=summary_data.outcome,
            message_count=session.message_count,
            duration_minutes=session.duration_minutes,
            created_at=session.first_timestamp.isoformat(),
            last_updated=now,
        )

        # Generate embedding if provider is available
        embedding: list[float] | None = None
        if self.embedding_provider is not None:
            embedding_text = summary.to_embedding_text()
            embedding = self.embedding_provider.embed(embedding_text)

        # Index in backend
        self.backend.index_session(summary, embedding)

        # Update state
        self.state.indexed_sessions[session.session_id] = SessionIndexInfo(
            last_indexed=now,
            message_count=session.message_count,
            last_summary_at=now,
            project_path=session.project_path,
        )
        self._save_state()

        return True

    def index_session_by_id(self, session_id: str, force: bool = False) -> bool:
        """
        Index a session by its ID.

        Searches for the session file and indexes it.
        """
        all_files = get_all_session_files(self.config.sessions_path)

        for filepath in all_files:
            if filepath.stem == session_id:
                session = parse_session_file(filepath)
                if session:
                    return self.index_session(session, force)
                break

        return False

    def index_all(
        self,
        limit: int | None = None,
        force: bool = False,
        min_messages: int | None = None,
    ) -> Iterator[tuple[str, bool, str | None]]:
        """
        Index all sessions.

        Args:
            limit: Maximum number of sessions to index
            force: Force re-indexing even if already indexed
            min_messages: Minimum messages for a session to be indexed

        Yields:
            Tuples of (session_id, success, error_message)
        """
        min_messages = min_messages or self.config.min_session_messages
        all_files = get_all_session_files(self.config.sessions_path)

        if limit:
            all_files = all_files[:limit]

        for filepath in all_files:
            session_id = filepath.stem

            try:
                session = parse_session_file(filepath)

                if session is None:
                    yield (session_id, False, "Failed to parse session")
                    continue

                if session.message_count < min_messages:
                    yield (session_id, False, f"Too few messages ({session.message_count})")
                    continue

                indexed = self.index_session(session, force)
                if indexed:
                    yield (session_id, True, None)
                else:
                    yield (session_id, False, "Already indexed")

            except Exception as e:
                yield (session_id, False, str(e))

        # Update state
        self.state.last_full_index = datetime.now().isoformat()
        self._save_state()

    def get_stats(self) -> dict:
        """Get indexing statistics."""
        all_files = get_all_session_files(self.config.sessions_path)
        backend_stats = self.backend.get_stats()

        return {
            "total_session_files": len(all_files),
            "indexed_sessions": len(self.state.indexed_sessions),
            "pending_sessions": len(all_files) - len(self.state.indexed_sessions),
            "last_full_index": self.state.last_full_index,
            "backend": backend_stats,
            "summarizer": self.summarizer.name,
            "embedding_provider": (
                self.embedding_provider.model_name if self.embedding_provider else "none"
            ),
        }

    def clear(self) -> None:
        """Clear all indexed data."""
        self.backend.clear()
        self._state = IndexState()
        self._save_state()
