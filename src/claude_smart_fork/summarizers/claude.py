"""Claude API-based summarizer."""

from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING

try:
    import anthropic

    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

from claude_smart_fork.parser import prepare_for_summarization
from claude_smart_fork.summarizers.base import BaseSummarizer, SessionSummaryData

if TYPE_CHECKING:
    from claude_smart_fork.config import Config
    from claude_smart_fork.parser import SessionData


SUMMARIZATION_PROMPT = """Analyze this Claude Code session transcript and generate a structured summary.

SESSION TRANSCRIPT:
{transcript}

Generate a JSON response with this exact structure:
{{
  "topic": "One-line description of main topic/goal (max 100 chars)",
  "key_decisions": ["Decision 1", "Decision 2", "Decision 3"],
  "files_modified": ["path/to/file1.ts", "path/to/file2.ts"],
  "technologies": ["Tech1", "Tech2", "Tech3"],
  "outcome": "Brief description of what was accomplished or current state (max 100 chars)"
}}

Focus on:
- The primary goal or problem being solved
- Important architectural or design decisions made
- Key files that were created or modified
- Technologies, frameworks, and libraries used
- Whether the task was completed, in-progress, or blocked

Return ONLY valid JSON, no other text."""


class ClaudeSummarizer(BaseSummarizer):
    """
    Claude API-based summarizer.

    Requires: pip install claude-smart-fork[claude]
    Also requires ANTHROPIC_API_KEY environment variable or config setting.
    """

    def __init__(self, config: Config) -> None:
        if not ANTHROPIC_AVAILABLE:
            raise ImportError(
                "anthropic is not installed. "
                "Install with: pip install claude-smart-fork[claude]"
            )

        super().__init__(config)

        # Get API key from config or environment
        api_key = config.anthropic_api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError(
                "Anthropic API key not found. "
                "Set ANTHROPIC_API_KEY environment variable or configure in settings."
            )

        self._client = anthropic.Anthropic(api_key=api_key)

    def summarize(self, session: SessionData) -> SessionSummaryData:
        """Generate a summary using Claude."""
        # Prepare transcript
        transcript = prepare_for_summarization(session, max_chars=30000)

        # Call Claude API
        response = self._client.messages.create(
            model="claude-3-5-haiku-20241022",  # Fast and cheap for summarization
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": SUMMARIZATION_PROMPT.format(transcript=transcript),
                }
            ],
        )

        # Parse response
        response_text = response.content[0].text.strip()

        try:
            # Try to extract JSON from response
            if response_text.startswith("{"):
                data = json.loads(response_text)
            else:
                # Try to find JSON in response
                start = response_text.find("{")
                end = response_text.rfind("}") + 1
                if start >= 0 and end > start:
                    data = json.loads(response_text[start:end])
                else:
                    raise ValueError("No JSON found in response")

            return SessionSummaryData(
                topic=data.get("topic", "Unknown topic")[:100],
                key_decisions=data.get("key_decisions", [])[:5],
                files_modified=data.get("files_modified", session.files_touched)[:10],
                technologies=data.get("technologies", [])[:5],
                outcome=data.get("outcome", "Unknown outcome")[:100],
            )

        except (json.JSONDecodeError, ValueError) as e:
            # Fallback to simple extraction
            return SessionSummaryData(
                topic=f"Session in {session.project_name}",
                key_decisions=[],
                files_modified=session.files_touched[:10],
                technologies=[],
                outcome=f"Summarization failed: {e}",
            )

    @property
    def name(self) -> str:
        """Return the summarizer name."""
        return "claude"
