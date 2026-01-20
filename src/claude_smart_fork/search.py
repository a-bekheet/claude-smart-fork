"""Search interface for finding sessions."""

from __future__ import annotations

from typing import TYPE_CHECKING

from claude_smart_fork.backends import get_backend
from claude_smart_fork.backends.base import SearchResult
from claude_smart_fork.config import Config, get_config
from claude_smart_fork.embeddings import get_embedding_provider

if TYPE_CHECKING:
    pass


def search_sessions(
    query: str,
    limit: int | None = None,
    project_filter: str | None = None,
    config: Config | None = None,
) -> list[SearchResult]:
    """
    Search for sessions matching a query.

    Args:
        query: Search query text
        limit: Maximum results to return (defaults to config value)
        project_filter: Optional project path filter
        config: Configuration to use (defaults to global config)

    Returns:
        List of SearchResult objects, sorted by relevance
    """
    config = config or get_config()
    limit = limit or config.search_results_limit

    backend = get_backend(config)

    # Try to use embeddings for semantic search
    embedding_provider = get_embedding_provider(config)
    query_embedding: list[float] | None = None

    if embedding_provider is not None:
        try:
            query_embedding = embedding_provider.embed_query(query)
        except Exception:
            # Fall back to keyword search if embedding fails
            pass

    return backend.search(
        query=query,
        query_embedding=query_embedding,
        limit=limit,
        project_filter=project_filter,
    )


def format_results(
    results: list[SearchResult],
    show_details: bool = False,
) -> str:
    """
    Format search results for display.

    Args:
        results: List of search results
        show_details: Whether to show detailed information

    Returns:
        Formatted string for display
    """
    if not results:
        return "No matching sessions found."

    lines = ["\n🔍 **Top Matching Sessions:**\n"]

    for i, result in enumerate(results, 1):
        summary = result.summary
        score = result.score

        # Score indicator
        if score >= 90:
            indicator = "🟢"
        elif score >= 70:
            indicator = "🟡"
        else:
            indicator = "🟠"

        # Session ID (truncated for display)
        short_id = result.session_id[:12] + "..." if len(result.session_id) > 12 else result.session_id

        lines.append(f"{i}. {indicator} **[{score}%]** `{short_id}`")
        lines.append(f"   📁 {summary.project_path}")
        lines.append(f"   📝 {summary.topic}")

        if summary.git_branch:
            lines.append(f"   🌿 Branch: {summary.git_branch}")

        if summary.technologies:
            lines.append(f"   🛠️ {', '.join(summary.technologies)}")

        if show_details:
            if summary.key_decisions:
                lines.append("   📋 Key decisions:")
                for decision in summary.key_decisions[:3]:
                    lines.append(f"      - {decision}")

            if summary.outcome:
                lines.append(f"   ✅ {summary.outcome}")

            lines.append(f"   ⏱️ {summary.duration_minutes:.0f} min, {summary.message_count} messages")

        lines.append("")

    # Add fork command for top result
    top = results[0]
    lines.append("---")
    lines.append("**To fork the top result, run:**")
    lines.append("```")
    lines.append(top.fork_command)
    lines.append("```")

    return "\n".join(lines)


def format_results_json(results: list[SearchResult]) -> list[dict]:
    """
    Format search results as JSON-serializable dicts.

    Args:
        results: List of search results

    Returns:
        List of dicts with result data
    """
    return [
        {
            "session_id": r.session_id,
            "score": r.score,
            "match_type": r.match_type,
            "fork_command": r.fork_command,
            "summary": {
                "project_path": r.summary.project_path,
                "git_branch": r.summary.git_branch,
                "topic": r.summary.topic,
                "key_decisions": r.summary.key_decisions,
                "files_modified": r.summary.files_modified,
                "technologies": r.summary.technologies,
                "outcome": r.summary.outcome,
                "message_count": r.summary.message_count,
                "duration_minutes": r.summary.duration_minutes,
                "created_at": r.summary.created_at,
            },
        }
        for r in results
    ]
