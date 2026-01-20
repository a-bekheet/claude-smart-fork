"""ChromaDB backend for semantic vector search."""

from __future__ import annotations

import json
from typing import Any

try:
    import chromadb
    from chromadb.config import Settings

    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False

from claude_smart_fork.backends.base import BaseBackend, SearchResult, SessionSummary
from claude_smart_fork.config import Config


class ChromaDBBackend(BaseBackend):
    """
    ChromaDB-based backend for semantic vector search.

    Requires: pip install claude-smart-fork[chromadb]

    This backend stores embeddings and enables semantic similarity search.
    """

    def __init__(self, config: Config) -> None:
        if not CHROMADB_AVAILABLE:
            raise ImportError(
                "ChromaDB is not installed. Install with: pip install claude-smart-fork[chromadb]"
            )

        super().__init__(config)

        # Initialize ChromaDB client
        db_path = config.db_path / "chromadb"
        db_path.mkdir(parents=True, exist_ok=True)

        self.client = chromadb.PersistentClient(
            path=str(db_path),
            settings=Settings(anonymized_telemetry=False),
        )

        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name="claude_sessions",
            metadata={"hnsw:space": "cosine"},
        )

    def _summary_to_metadata(self, summary: SessionSummary) -> dict[str, Any]:
        """Convert summary to ChromaDB metadata."""
        return {
            "project_path": summary.project_path,
            "git_branch": summary.git_branch or "",
            "topic": summary.topic,
            "key_decisions": json.dumps(summary.key_decisions),
            "files_modified": json.dumps(summary.files_modified),
            "technologies": json.dumps(summary.technologies),
            "outcome": summary.outcome,
            "message_count": summary.message_count,
            "duration_minutes": summary.duration_minutes,
            "created_at": summary.created_at,
            "last_updated": summary.last_updated,
        }

    def _metadata_to_summary(self, session_id: str, metadata: dict[str, Any]) -> SessionSummary:
        """Convert ChromaDB metadata to SessionSummary."""
        return SessionSummary(
            session_id=session_id,
            project_path=metadata["project_path"],
            git_branch=metadata["git_branch"] or None,
            topic=metadata["topic"],
            key_decisions=json.loads(metadata["key_decisions"]),
            files_modified=json.loads(metadata["files_modified"]),
            technologies=json.loads(metadata["technologies"]),
            outcome=metadata["outcome"],
            message_count=metadata["message_count"],
            duration_minutes=metadata["duration_minutes"],
            created_at=metadata["created_at"],
            last_updated=metadata["last_updated"],
        )

    def index_session(self, summary: SessionSummary, embedding: list[float] | None = None) -> None:
        """
        Index a session summary.

        If no embedding is provided, the document text will be stored for
        later embedding by ChromaDB's default embedding function.
        """
        metadata = self._summary_to_metadata(summary)
        document = summary.to_embedding_text()

        if embedding is not None:
            self.collection.upsert(
                ids=[summary.session_id],
                embeddings=[embedding],
                metadatas=[metadata],
                documents=[document],
            )
        else:
            # Let ChromaDB handle embedding
            self.collection.upsert(
                ids=[summary.session_id],
                metadatas=[metadata],
                documents=[document],
            )

    def search(
        self,
        query: str,
        query_embedding: list[float] | None = None,
        limit: int = 5,
        project_filter: str | None = None,
    ) -> list[SearchResult]:
        """
        Search for sessions using vector similarity.
        """
        # Build where filter if project filter is specified
        where_filter = None
        if project_filter:
            where_filter = {"project_path": {"$contains": project_filter}}

        # Search
        if query_embedding is not None:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=limit,
                where=where_filter,
                include=["metadatas", "documents", "distances"],
            )
        else:
            results = self.collection.query(
                query_texts=[query],
                n_results=limit,
                where=where_filter,
                include=["metadatas", "documents", "distances"],
            )

        search_results = []

        if results["ids"] and results["ids"][0]:
            for i, session_id in enumerate(results["ids"][0]):
                metadata = results["metadatas"][0][i]
                distance = results["distances"][0][i]

                # Convert cosine distance to similarity score (0-100)
                # Cosine distance: 0 = identical, 2 = opposite
                similarity = (1 - distance / 2) * 100
                score = round(max(0, min(100, similarity)), 1)

                summary = self._metadata_to_summary(session_id, metadata)

                search_results.append(
                    SearchResult(
                        session_id=session_id,
                        score=score,
                        summary=summary,
                        match_type="semantic",
                    )
                )

        return search_results

    def get_session(self, session_id: str) -> SessionSummary | None:
        """Get a session by ID."""
        results = self.collection.get(
            ids=[session_id],
            include=["metadatas"],
        )

        if results["ids"]:
            metadata = results["metadatas"][0]
            return self._metadata_to_summary(session_id, metadata)

        return None

    def delete_session(self, session_id: str) -> bool:
        """Delete a session from the index."""
        try:
            self.collection.delete(ids=[session_id])
            return True
        except Exception:
            return False

    def get_stats(self) -> dict[str, Any]:
        """Get statistics about the index."""
        count = self.collection.count()

        # Get project distribution
        results = self.collection.get(include=["metadatas"])
        by_project: dict[str, int] = {}

        if results["metadatas"]:
            for metadata in results["metadatas"]:
                project = metadata.get("project_path", "unknown")
                by_project[project] = by_project.get(project, 0) + 1

        return {
            "total_sessions": count,
            "by_project": by_project,
            "backend": "chromadb",
            "db_path": str(self.config.db_path / "chromadb"),
        }

    def is_indexed(self, session_id: str) -> bool:
        """Check if a session is already indexed."""
        results = self.collection.get(ids=[session_id])
        return bool(results["ids"])

    def clear(self) -> None:
        """Clear all indexed data."""
        # Delete and recreate collection
        self.client.delete_collection("claude_sessions")
        self.collection = self.client.get_or_create_collection(
            name="claude_sessions",
            metadata={"hnsw:space": "cosine"},
        )
