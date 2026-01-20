"""Tests for summarizers."""

from pathlib import Path

import pytest

from claude_smart_fork.config import Config
from claude_smart_fork.parser import parse_session_file
from claude_smart_fork.summarizers.simple import SimpleSummarizer


class TestSimpleSummarizer:
    """Tests for the simple keyword-based summarizer."""

    @pytest.fixture
    def config(self, tmp_path: Path) -> Config:
        """Create a test configuration."""
        return Config(
            data_dir=tmp_path / ".claude-smart-fork",
            summarizer="simple",
        )

    @pytest.fixture
    def summarizer(self, config: Config) -> SimpleSummarizer:
        """Create a test summarizer."""
        return SimpleSummarizer(config)

    @pytest.fixture
    def sample_session(self):
        """Load the sample session."""
        sample_path = Path(__file__).parent / "fixtures" / "sample_session.jsonl"
        session = parse_session_file(sample_path)
        assert session is not None
        return session

    def test_summarizer_name(self, summarizer: SimpleSummarizer) -> None:
        """Test summarizer name property."""
        assert summarizer.name == "simple"

    def test_summarize_extracts_topic(self, summarizer: SimpleSummarizer, sample_session) -> None:
        """Test that summarization extracts a topic."""
        result = summarizer.summarize(sample_session)

        assert result.topic
        assert len(result.topic) > 0
        # Should contain something about JWT or authentication
        assert "JWT" in result.topic or "authentication" in result.topic.lower()

    def test_summarize_detects_technologies(
        self, summarizer: SimpleSummarizer, sample_session
    ) -> None:
        """Test that summarization detects technologies."""
        result = summarizer.summarize(sample_session)

        assert result.technologies
        # Should detect TypeScript from .ts files
        assert "TypeScript" in result.technologies

    def test_summarize_extracts_files(self, summarizer: SimpleSummarizer, sample_session) -> None:
        """Test that summarization extracts modified files."""
        result = summarizer.summarize(sample_session)

        assert result.files_modified
        assert any("auth.ts" in f for f in result.files_modified)

    def test_summarize_determines_outcome(
        self, summarizer: SimpleSummarizer, sample_session
    ) -> None:
        """Test that summarization determines outcome."""
        result = summarizer.summarize(sample_session)

        assert result.outcome
        # The sample session mentions "complete" so should be detected
        assert "complete" in result.outcome.lower() or "session" in result.outcome.lower()


class TestTechnologyDetection:
    """Tests for technology detection patterns."""

    @pytest.fixture
    def summarizer(self, tmp_path: Path) -> SimpleSummarizer:
        """Create a test summarizer."""
        config = Config(data_dir=tmp_path / ".claude-smart-fork")
        return SimpleSummarizer(config)

    def test_detects_python_from_extension(self, summarizer: SimpleSummarizer) -> None:
        """Test Python detection from file extensions."""
        from datetime import datetime

        from claude_smart_fork.parser import Message, SessionData

        session = SessionData(
            session_id="test",
            project_path="/test",
            git_branch=None,
            messages=[Message(role="user", content="test", timestamp=datetime.now(), tool_uses=[])],
            files_touched=["main.py", "utils.py", "tests/test_main.py"],
            first_timestamp=datetime.now(),
            last_timestamp=datetime.now(),
            source_file=Path("/test.jsonl"),
        )

        result = summarizer.summarize(session)
        assert "Python" in result.technologies

    def test_detects_react_from_content(self, summarizer: SimpleSummarizer) -> None:
        """Test React detection from message content."""
        from datetime import datetime

        from claude_smart_fork.parser import Message, SessionData

        session = SessionData(
            session_id="test",
            project_path="/test",
            git_branch=None,
            messages=[
                Message(
                    role="user",
                    content="I need to create a React component",
                    timestamp=datetime.now(),
                    tool_uses=[],
                )
            ],
            files_touched=[],
            first_timestamp=datetime.now(),
            last_timestamp=datetime.now(),
            source_file=Path("/test.jsonl"),
        )

        result = summarizer.summarize(session)
        assert "React" in result.technologies
