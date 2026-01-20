"""Tests for storage backends."""

from pathlib import Path

import pytest

from claude_smart_fork.backends.base import SearchResult, SessionSummary
from claude_smart_fork.backends.sqlite import SQLiteBackend
from claude_smart_fork.config import Config


class TestSQLiteBackend:
    """Tests for SQLite backend."""

    @pytest.fixture
    def config(self, tmp_path: Path) -> Config:
        """Create a test configuration."""
        return Config(
            data_dir=tmp_path / ".claude-smart-fork",
            sessions_path=tmp_path / "sessions",
            backend="sqlite",
        )

    @pytest.fixture
    def backend(self, config: Config) -> SQLiteBackend:
        """Create a test backend."""
        config.ensure_directories()
        return SQLiteBackend(config)

    @pytest.fixture
    def sample_summary(self) -> SessionSummary:
        """Create a sample session summary."""
        return SessionSummary(
            session_id="test-session-123",
            project_path="/home/user/projects/my-api",
            git_branch="feature/auth",
            topic="Implementing JWT authentication for Express API",
            key_decisions=["Using RS256 for signing", "Redis for refresh tokens"],
            files_modified=["src/middleware/auth.ts", "src/config/auth.ts"],
            technologies=["TypeScript", "Express", "Redis", "JWT"],
            outcome="Completed successfully",
            message_count=6,
            duration_minutes=12.0,
            created_at="2026-01-19T10:00:00Z",
            last_updated="2026-01-19T10:12:00Z",
        )

    def test_index_session(self, backend: SQLiteBackend, sample_summary: SessionSummary) -> None:
        """Test indexing a session."""
        backend.index_session(sample_summary)

        assert backend.is_indexed(sample_summary.session_id)

    def test_get_session(self, backend: SQLiteBackend, sample_summary: SessionSummary) -> None:
        """Test retrieving a session."""
        backend.index_session(sample_summary)

        result = backend.get_session(sample_summary.session_id)

        assert result is not None
        assert result.session_id == sample_summary.session_id
        assert result.topic == sample_summary.topic
        assert result.technologies == sample_summary.technologies

    def test_search_finds_matching_session(
        self, backend: SQLiteBackend, sample_summary: SessionSummary
    ) -> None:
        """Test that search finds matching sessions."""
        backend.index_session(sample_summary)

        results = backend.search("JWT authentication")

        assert len(results) >= 1
        assert results[0].session_id == sample_summary.session_id

    def test_search_with_project_filter(
        self, backend: SQLiteBackend, sample_summary: SessionSummary
    ) -> None:
        """Test search with project filter."""
        backend.index_session(sample_summary)

        # Should find with matching filter
        results = backend.search("authentication", project_filter="my-api")
        assert len(results) >= 1

        # Should not find with non-matching filter
        results = backend.search("authentication", project_filter="other-project")
        assert len(results) == 0

    def test_delete_session(self, backend: SQLiteBackend, sample_summary: SessionSummary) -> None:
        """Test deleting a session."""
        backend.index_session(sample_summary)
        assert backend.is_indexed(sample_summary.session_id)

        success = backend.delete_session(sample_summary.session_id)

        assert success
        assert not backend.is_indexed(sample_summary.session_id)

    def test_get_stats(self, backend: SQLiteBackend, sample_summary: SessionSummary) -> None:
        """Test getting statistics."""
        backend.index_session(sample_summary)

        stats = backend.get_stats()

        assert stats["total_sessions"] == 1
        assert stats["backend"] == "sqlite"
        assert sample_summary.project_path in stats["by_project"]

    def test_clear(self, backend: SQLiteBackend, sample_summary: SessionSummary) -> None:
        """Test clearing all data."""
        backend.index_session(sample_summary)
        assert backend.is_indexed(sample_summary.session_id)

        backend.clear()

        assert not backend.is_indexed(sample_summary.session_id)
        assert backend.get_stats()["total_sessions"] == 0

    def test_upsert_updates_existing(
        self, backend: SQLiteBackend, sample_summary: SessionSummary
    ) -> None:
        """Test that indexing twice updates the session."""
        backend.index_session(sample_summary)

        # Update the summary
        updated = SessionSummary(
            session_id=sample_summary.session_id,
            project_path=sample_summary.project_path,
            git_branch=sample_summary.git_branch,
            topic="Updated topic",
            key_decisions=["New decision"],
            files_modified=sample_summary.files_modified,
            technologies=sample_summary.technologies,
            outcome="Updated outcome",
            message_count=10,
            duration_minutes=20.0,
            created_at=sample_summary.created_at,
            last_updated="2026-01-19T11:00:00Z",
        )
        backend.index_session(updated)

        result = backend.get_session(sample_summary.session_id)
        assert result is not None
        assert result.topic == "Updated topic"
        assert result.message_count == 10


class TestSearchResult:
    """Tests for SearchResult dataclass."""

    def test_fork_command(self) -> None:
        """Test fork command generation."""
        summary = SessionSummary(
            session_id="abc123",
            project_path="/test",
            git_branch=None,
            topic="Test",
            key_decisions=[],
            files_modified=[],
            technologies=[],
            outcome="",
            message_count=1,
            duration_minutes=1.0,
            created_at="2026-01-01T00:00:00Z",
            last_updated="2026-01-01T00:00:00Z",
        )

        result = SearchResult(
            session_id="abc123",
            score=95.0,
            summary=summary,
        )

        assert result.fork_command == "claude --resume abc123"
