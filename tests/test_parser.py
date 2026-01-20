"""Tests for session parser."""

from pathlib import Path

import pytest

from claude_smart_fork.parser import (
    SessionData,
    decode_project_path,
    parse_session_file,
    prepare_for_summarization,
)


class TestDecodeProjectPath:
    """Tests for project path decoding."""

    def test_decode_simple_path(self) -> None:
        """Test decoding a simple path."""
        encoded = "~-home-user-projects-my-api"
        result = decode_project_path(encoded)
        assert result == "/home/user/projects/my-api"

    def test_decode_empty(self) -> None:
        """Test decoding empty string."""
        assert decode_project_path("") == ""

    def test_decode_no_prefix(self) -> None:
        """Test decoding without tilde prefix."""
        encoded = "-home-user-project"
        result = decode_project_path(encoded)
        assert result == "/home/user/project"


class TestParseSessionFile:
    """Tests for session file parsing."""

    @pytest.fixture
    def sample_session_path(self) -> Path:
        """Get path to sample session file."""
        return Path(__file__).parent / "fixtures" / "sample_session.jsonl"

    def test_parse_valid_session(self, sample_session_path: Path) -> None:
        """Test parsing a valid session file."""
        session = parse_session_file(sample_session_path)

        assert session is not None
        assert session.session_id == "test-session-123"
        assert session.git_branch == "feature/auth"
        assert session.message_count == 6

    def test_parse_session_messages(self, sample_session_path: Path) -> None:
        """Test that messages are parsed correctly."""
        session = parse_session_file(sample_session_path)

        assert session is not None
        assert session.user_message_count == 3

        # Check first user message
        user_messages = [m for m in session.messages if m.role == "user"]
        assert "JWT authentication" in user_messages[0].content

    def test_parse_session_files_touched(self, sample_session_path: Path) -> None:
        """Test that files touched are extracted."""
        session = parse_session_file(sample_session_path)

        assert session is not None
        assert len(session.files_touched) > 0
        assert any("auth.ts" in f for f in session.files_touched)

    def test_parse_session_tool_uses(self, sample_session_path: Path) -> None:
        """Test that tool uses are extracted."""
        session = parse_session_file(sample_session_path)

        assert session is not None
        tools = session.get_tool_names()
        assert "Read" in tools
        assert "Write" in tools
        assert "Edit" in tools

    def test_parse_nonexistent_file(self, tmp_path: Path) -> None:
        """Test parsing a nonexistent file."""
        result = parse_session_file(tmp_path / "nonexistent.jsonl")
        assert result is None

    def test_parse_empty_file(self, tmp_path: Path) -> None:
        """Test parsing an empty file."""
        empty_file = tmp_path / "empty.jsonl"
        empty_file.write_text("")

        result = parse_session_file(empty_file)
        assert result is None

    def test_parse_invalid_json(self, tmp_path: Path) -> None:
        """Test parsing a file with invalid JSON."""
        bad_file = tmp_path / "bad.jsonl"
        bad_file.write_text("not valid json\n{also bad}")

        result = parse_session_file(bad_file)
        assert result is None


class TestPrepareForSummarization:
    """Tests for summarization preparation."""

    @pytest.fixture
    def sample_session(self) -> SessionData:
        """Create a sample session for testing."""
        sample_path = Path(__file__).parent / "fixtures" / "sample_session.jsonl"
        session = parse_session_file(sample_path)
        assert session is not None
        return session

    def test_prepare_includes_metadata(self, sample_session: SessionData) -> None:
        """Test that preparation includes metadata."""
        result = prepare_for_summarization(sample_session)

        assert "feature/auth" in result  # git branch
        assert "Conversation" in result

    def test_prepare_includes_messages(self, sample_session: SessionData) -> None:
        """Test that preparation includes messages."""
        result = prepare_for_summarization(sample_session)

        assert "USER:" in result
        assert "CLAUDE:" in result
        assert "JWT authentication" in result

    def test_prepare_truncates_long_content(self, sample_session: SessionData) -> None:
        """Test that very long content is truncated."""
        result = prepare_for_summarization(sample_session, max_chars=500)

        assert len(result) <= 600  # Some buffer for truncation message
