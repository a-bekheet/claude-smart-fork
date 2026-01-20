"""SQLite backend for keyword-based session search."""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from claude_smart_fork.backends.base import BaseBackend, SearchResult, SessionSummary
from claude_smart_fork.config import Config


class SQLiteBackend(BaseBackend):
    """
    SQLite-based backend using FTS5 for keyword search.

    This is the default backend that requires no extra dependencies.
    It provides fast keyword search but not semantic/vector search.
    """

    def __init__(self, config: Config) -> None:
        super().__init__(config)
        self.db_path = config.db_path / "sessions.db"
        self._ensure_tables()

    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_tables(self) -> None:
        """Create tables if they don't exist."""
        with self._get_connection() as conn:
            # Main sessions table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    project_path TEXT,
                    git_branch TEXT,
                    topic TEXT,
                    key_decisions TEXT,
                    files_modified TEXT,
                    technologies TEXT,
                    outcome TEXT,
                    message_count INTEGER,
                    duration_minutes REAL,
                    created_at TEXT,
                    last_updated TEXT,
                    search_text TEXT
                )
            """)

            # FTS5 virtual table for full-text search
            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS sessions_fts USING fts5(
                    session_id,
                    search_text,
                    content='sessions',
                    content_rowid='rowid'
                )
            """)

            # Triggers to keep FTS in sync
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS sessions_ai AFTER INSERT ON sessions BEGIN
                    INSERT INTO sessions_fts(rowid, session_id, search_text)
                    VALUES (new.rowid, new.session_id, new.search_text);
                END
            """)

            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS sessions_ad AFTER DELETE ON sessions BEGIN
                    INSERT INTO sessions_fts(sessions_fts, rowid, session_id, search_text)
                    VALUES ('delete', old.rowid, old.session_id, old.search_text);
                END
            """)

            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS sessions_au AFTER UPDATE ON sessions BEGIN
                    INSERT INTO sessions_fts(sessions_fts, rowid, session_id, search_text)
                    VALUES ('delete', old.rowid, old.session_id, old.search_text);
                    INSERT INTO sessions_fts(rowid, session_id, search_text)
                    VALUES (new.rowid, new.session_id, new.search_text);
                END
            """)

            conn.commit()

    def _summary_to_row(self, summary: SessionSummary) -> dict[str, Any]:
        """Convert a SessionSummary to a database row."""
        return {
            "session_id": summary.session_id,
            "project_path": summary.project_path,
            "git_branch": summary.git_branch,
            "topic": summary.topic,
            "key_decisions": json.dumps(summary.key_decisions),
            "files_modified": json.dumps(summary.files_modified),
            "technologies": json.dumps(summary.technologies),
            "outcome": summary.outcome,
            "message_count": summary.message_count,
            "duration_minutes": summary.duration_minutes,
            "created_at": summary.created_at,
            "last_updated": summary.last_updated,
            "search_text": summary.to_search_text(),
        }

    def _row_to_summary(self, row: sqlite3.Row) -> SessionSummary:
        """Convert a database row to a SessionSummary."""
        return SessionSummary(
            session_id=row["session_id"],
            project_path=row["project_path"],
            git_branch=row["git_branch"],
            topic=row["topic"],
            key_decisions=json.loads(row["key_decisions"]),
            files_modified=json.loads(row["files_modified"]),
            technologies=json.loads(row["technologies"]),
            outcome=row["outcome"],
            message_count=row["message_count"],
            duration_minutes=row["duration_minutes"],
            created_at=row["created_at"],
            last_updated=row["last_updated"],
        )

    def index_session(self, summary: SessionSummary, _embedding: list[float] | None = None) -> None:
        """Index a session summary."""
        row = self._summary_to_row(summary)

        with self._get_connection() as conn:
            # Use INSERT OR REPLACE for upsert behavior
            conn.execute(
                """
                INSERT OR REPLACE INTO sessions (
                    session_id, project_path, git_branch, topic, key_decisions,
                    files_modified, technologies, outcome, message_count,
                    duration_minutes, created_at, last_updated, search_text
                ) VALUES (
                    :session_id, :project_path, :git_branch, :topic, :key_decisions,
                    :files_modified, :technologies, :outcome, :message_count,
                    :duration_minutes, :created_at, :last_updated, :search_text
                )
            """,
                row,
            )
            conn.commit()

    def search(
        self,
        query: str,
        _query_embedding: list[float] | None = None,
        limit: int = 5,
        project_filter: str | None = None,
    ) -> list[SearchResult]:
        """
        Search for sessions using FTS5.

        Uses BM25 ranking for relevance scoring.
        """
        with self._get_connection() as conn:
            # Build the FTS query
            # Escape special FTS5 characters
            safe_query = query.replace('"', '""')

            if project_filter:
                # Search with project filter
                cursor = conn.execute(
                    """
                    SELECT s.*, bm25(sessions_fts) as rank
                    FROM sessions s
                    JOIN sessions_fts ON s.session_id = sessions_fts.session_id
                    WHERE sessions_fts MATCH ?
                    AND s.project_path LIKE ?
                    ORDER BY rank
                    LIMIT ?
                """,
                    (f'"{safe_query}"', f"%{project_filter}%", limit),
                )
            else:
                cursor = conn.execute(
                    """
                    SELECT s.*, bm25(sessions_fts) as rank
                    FROM sessions s
                    JOIN sessions_fts ON s.session_id = sessions_fts.session_id
                    WHERE sessions_fts MATCH ?
                    ORDER BY rank
                    LIMIT ?
                """,
                    (f'"{safe_query}"', limit),
                )

            results = []
            rows = cursor.fetchall()

            # Normalize BM25 scores to 0-100
            if rows:
                # BM25 returns negative scores (more negative = better match)
                min_rank = min(row["rank"] for row in rows)
                max_rank = max(row["rank"] for row in rows)
                rank_range = max_rank - min_rank if max_rank != min_rank else 1

                for row in rows:
                    summary = self._row_to_summary(row)
                    # Convert BM25 to 0-100 score (inverted because lower BM25 = better)
                    normalized = (max_rank - row["rank"]) / rank_range
                    score = round(normalized * 100, 1)

                    results.append(
                        SearchResult(
                            session_id=summary.session_id,
                            score=score,
                            summary=summary,
                            match_type="keyword",
                        )
                    )

            return results

    def get_session(self, session_id: str) -> SessionSummary | None:
        """Get a session by ID."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM sessions WHERE session_id = ?",
                (session_id,),
            )
            row = cursor.fetchone()
            if row:
                return self._row_to_summary(row)
            return None

    def delete_session(self, session_id: str) -> bool:
        """Delete a session from the index."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM sessions WHERE session_id = ?",
                (session_id,),
            )
            conn.commit()
            return cursor.rowcount > 0

    def get_stats(self) -> dict[str, Any]:
        """Get statistics about the index."""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) as count FROM sessions")
            total = cursor.fetchone()["count"]

            cursor = conn.execute(
                "SELECT project_path, COUNT(*) as count FROM sessions GROUP BY project_path"
            )
            by_project = {row["project_path"]: row["count"] for row in cursor.fetchall()}

            return {
                "total_sessions": total,
                "by_project": by_project,
                "backend": "sqlite",
                "db_path": str(self.db_path),
            }

    def is_indexed(self, session_id: str) -> bool:
        """Check if a session is already indexed."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT 1 FROM sessions WHERE session_id = ? LIMIT 1",
                (session_id,),
            )
            return cursor.fetchone() is not None

    def clear(self) -> None:
        """Clear all indexed data."""
        with self._get_connection() as conn:
            conn.execute("DELETE FROM sessions")
            conn.execute("DELETE FROM sessions_fts")
            conn.commit()
