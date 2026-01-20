"""Parser for Claude Code session JSONL files."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterator

from claude_smart_fork.config import get_config


@dataclass
class Message:
    """A single message in a session."""

    role: str  # 'user' or 'assistant'
    content: str
    timestamp: datetime
    tool_uses: list[dict] = field(default_factory=list)


@dataclass
class SessionData:
    """Parsed data from a Claude Code session."""

    session_id: str
    project_path: str
    git_branch: str | None
    messages: list[Message]
    files_touched: list[str]
    first_timestamp: datetime
    last_timestamp: datetime
    source_file: Path

    @property
    def message_count(self) -> int:
        """Number of messages in the session."""
        return len(self.messages)

    @property
    def user_message_count(self) -> int:
        """Number of user messages in the session."""
        return sum(1 for m in self.messages if m.role == "user")

    @property
    def duration_minutes(self) -> float:
        """Duration of the session in minutes."""
        delta = self.last_timestamp - self.first_timestamp
        return delta.total_seconds() / 60

    @property
    def project_name(self) -> str:
        """Short project name from path."""
        return Path(self.project_path).name

    def get_user_prompts(self) -> list[str]:
        """Get all user prompts from the session."""
        return [m.content for m in self.messages if m.role == "user" and m.content]

    def get_tool_names(self) -> set[str]:
        """Get unique tool names used in the session."""
        tools = set()
        for msg in self.messages:
            for tool in msg.tool_uses:
                if name := tool.get("name"):
                    tools.add(name)
        return tools


def decode_project_path(encoded: str) -> str:
    """
    Convert Claude Code's encoded project path back to the original.

    Claude encodes paths like /home/user/project as:
    - ~-home-user-project (tilde prefix, dashes)

    This function attempts to reverse that encoding.
    """
    if not encoded:
        return ""

    # Remove leading tilde if present
    if encoded.startswith("~-"):
        encoded = encoded[2:]
    elif encoded.startswith("-"):
        encoded = encoded[1:]

    # Replace dashes with path separators
    # This is imperfect for paths with actual dashes, but it's the best we can do
    path = "/" + encoded.replace("-", "/")

    # Try to detect and preserve common path patterns with dashes
    # e.g., my-project should stay as my-project, not my/project
    # Heuristic: if a segment looks like a common directory, keep previous dash
    common_dirs = {"home", "Users", "var", "opt", "usr", "tmp", "projects", "src", "code"}

    parts = path.split("/")
    result = []
    i = 0
    while i < len(parts):
        part = parts[i]
        if part in common_dirs or i <= 2:  # Keep early path segments as-is
            result.append(part)
        else:
            # For later segments, be more conservative about splitting
            result.append(part)
        i += 1

    return "/".join(result)


def parse_timestamp(ts_str: str) -> datetime:
    """Parse ISO timestamp, handling various formats."""
    # Handle Z suffix
    ts_str = ts_str.replace("Z", "+00:00")

    # Try parsing with fromisoformat
    try:
        return datetime.fromisoformat(ts_str)
    except ValueError:
        # Fallback: try strptime for common formats
        for fmt in [
            "%Y-%m-%dT%H:%M:%S.%f%z",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%S",
        ]:
            try:
                return datetime.strptime(ts_str, fmt)
            except ValueError:
                continue

        # Last resort: return current time
        return datetime.now()


def parse_session_file(filepath: Path) -> SessionData | None:
    """
    Parse a single Claude Code session JSONL file.

    Args:
        filepath: Path to the .jsonl session file

    Returns:
        SessionData object or None if parsing fails
    """
    messages: list[Message] = []
    files_touched: set[str] = set()
    session_id = filepath.stem
    git_branch: str | None = None
    first_ts: datetime | None = None
    last_ts: datetime | None = None

    # Decode project path from parent directory name
    project_path = decode_project_path(filepath.parent.name)

    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue

                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue

                # Extract timestamp
                ts_str = entry.get("timestamp", "")
                if ts_str:
                    ts = parse_timestamp(ts_str)
                    if first_ts is None:
                        first_ts = ts
                    last_ts = ts

                # Extract git branch (may change during session, keep latest)
                if "gitBranch" in entry:
                    git_branch = entry["gitBranch"]

                # Update session_id if available in entry
                if "sessionId" in entry:
                    session_id = entry["sessionId"]

                # Extract message content
                if "message" in entry:
                    msg = entry["message"]
                    role = msg.get("role", "")
                    content_parts = msg.get("content", [])

                    text_content: list[str] = []
                    tool_uses: list[dict] = []

                    for part in content_parts:
                        if isinstance(part, dict):
                            part_type = part.get("type", "")

                            if part_type == "text":
                                text = part.get("text", "")
                                if text:
                                    text_content.append(text)

                            elif part_type == "tool_use":
                                tool_info = {
                                    "name": part.get("name", ""),
                                    "input": part.get("input", {}),
                                }
                                tool_uses.append(tool_info)

                                # Track files from tool usage
                                tool_name = part.get("name", "")
                                if tool_name in ("Read", "Write", "Edit", "Glob", "Grep"):
                                    input_data = part.get("input", {})
                                    file_path = input_data.get(
                                        "file_path", input_data.get("path", "")
                                    )
                                    if file_path:
                                        files_touched.add(file_path)

                        elif isinstance(part, str):
                            text_content.append(part)

                    if text_content or tool_uses:
                        messages.append(
                            Message(
                                role=role,
                                content="\n".join(text_content),
                                timestamp=ts if ts_str else datetime.now(),
                                tool_uses=tool_uses,
                            )
                        )

    except (OSError, IOError) as e:
        # Log error but don't crash
        return None

    # Validate we have enough data
    if not messages or first_ts is None or last_ts is None:
        return None

    return SessionData(
        session_id=session_id,
        project_path=project_path,
        git_branch=git_branch,
        messages=messages,
        files_touched=sorted(files_touched),
        first_timestamp=first_ts,
        last_timestamp=last_ts,
        source_file=filepath,
    )


def get_all_session_files(sessions_path: Path | None = None) -> list[Path]:
    """
    Get all session JSONL files across all projects.

    Args:
        sessions_path: Path to Claude projects directory.
                      Defaults to ~/.claude/projects

    Returns:
        List of paths to session files, sorted by modification time (newest first)
    """
    if sessions_path is None:
        config = get_config()
        sessions_path = config.sessions_path

    sessions_path = Path(sessions_path).expanduser()

    if not sessions_path.exists():
        return []

    files = list(sessions_path.glob("**/*.jsonl"))

    # Sort by modification time, newest first
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)

    return files


def iter_sessions(
    sessions_path: Path | None = None,
    min_messages: int = 3,
) -> Iterator[SessionData]:
    """
    Iterate over all valid sessions.

    Args:
        sessions_path: Path to Claude projects directory
        min_messages: Minimum messages for a session to be yielded

    Yields:
        SessionData objects for valid sessions
    """
    for filepath in get_all_session_files(sessions_path):
        session = parse_session_file(filepath)
        if session and session.message_count >= min_messages:
            yield session


def prepare_for_summarization(session: SessionData, max_chars: int = 50000) -> str:
    """
    Prepare session content for LLM summarization.

    Creates a condensed representation of the session suitable for
    generating a summary.

    Args:
        session: Parsed session data
        max_chars: Maximum characters to include

    Returns:
        Formatted string for summarization
    """
    lines = [
        f"Project: {session.project_path}",
        f"Duration: {session.duration_minutes:.1f} minutes",
    ]

    if session.git_branch:
        lines.append(f"Git Branch: {session.git_branch}")

    if session.files_touched:
        files_str = ", ".join(session.files_touched[:20])
        if len(session.files_touched) > 20:
            files_str += f" (+{len(session.files_touched) - 20} more)"
        lines.append(f"Files touched: {files_str}")

    tools = session.get_tool_names()
    if tools:
        lines.append(f"Tools used: {', '.join(sorted(tools))}")

    lines.append("\n--- Conversation ---\n")

    # Add messages
    message_texts = []
    for msg in session.messages:
        prefix = "USER:" if msg.role == "user" else "CLAUDE:"
        tool_info = ""
        if msg.tool_uses:
            tool_names = [t["name"] for t in msg.tool_uses]
            tool_info = f" [Tools: {', '.join(tool_names)}]"

        # Truncate individual messages
        content = msg.content[:2000]
        if len(msg.content) > 2000:
            content += "..."

        message_texts.append(f"{prefix}{tool_info}\n{content}")

    conversation = "\n\n".join(message_texts)
    header = "\n".join(lines)

    full_text = header + conversation

    # Truncate if needed, keeping header
    if len(full_text) > max_chars:
        available = max_chars - len(header) - 100
        full_text = header + "\n[Earlier messages truncated]\n..." + conversation[-available:]

    return full_text
