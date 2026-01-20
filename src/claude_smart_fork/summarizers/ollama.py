"""Ollama-based local LLM summarizer."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

try:
    import ollama as ollama_client

    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False

from claude_smart_fork.parser import prepare_for_summarization
from claude_smart_fork.summarizers.base import BaseSummarizer, SessionSummaryData

if TYPE_CHECKING:
    from claude_smart_fork.config import Config
    from claude_smart_fork.parser import SessionData


SUMMARIZATION_PROMPT = """Analyze this Claude Code session transcript and generate a structured summary.

SESSION TRANSCRIPT:
{transcript}

Generate a JSON response with this exact structure (no other text):
{{
  "topic": "One-line description of main topic/goal",
  "key_decisions": ["Decision 1", "Decision 2", "Decision 3"],
  "files_modified": ["path/to/file1.ts", "path/to/file2.ts"],
  "technologies": ["Tech1", "Tech2", "Tech3"],
  "outcome": "Brief description of what was accomplished"
}}

Return ONLY the JSON, nothing else."""


class OllamaSummarizer(BaseSummarizer):
    """
    Ollama-based local LLM summarizer.

    Requires:
    1. pip install claude-smart-fork[ollama]
    2. Ollama installed and running (https://ollama.ai)
    3. A model pulled (e.g., `ollama pull llama3.2`)

    Uses llama3.2 by default, configurable via config.ollama_model.
    """

    def __init__(self, config: Config) -> None:
        if not OLLAMA_AVAILABLE:
            raise ImportError(
                "ollama is not installed. Install with: pip install claude-smart-fork[ollama]"
            )

        super().__init__(config)
        self._model = config.ollama_model

        # Verify Ollama is running and model is available
        try:
            models = ollama_client.list()
            available = [m["name"].split(":")[0] for m in models.get("models", [])]
            if self._model not in available and f"{self._model}:latest" not in [
                m["name"] for m in models.get("models", [])
            ]:
                raise ValueError(
                    f"Model '{self._model}' not found. "
                    f"Available models: {available}. "
                    f"Pull with: ollama pull {self._model}"
                )
        except Exception as e:
            if "connection" in str(e).lower():
                raise ConnectionError(
                    "Cannot connect to Ollama. Make sure Ollama is running: ollama serve"
                ) from e
            raise

    def summarize(self, session: SessionData) -> SessionSummaryData:
        """Generate a summary using Ollama."""
        # Prepare transcript (shorter for local models)
        transcript = prepare_for_summarization(session, max_chars=15000)

        # Call Ollama
        response = ollama_client.chat(
            model=self._model,
            messages=[
                {
                    "role": "user",
                    "content": SUMMARIZATION_PROMPT.format(transcript=transcript),
                }
            ],
            options={
                "temperature": 0.3,  # Lower temperature for more consistent output
            },
        )

        response_text = response["message"]["content"].strip()

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
                topic=str(data.get("topic", "Unknown topic"))[:100],
                key_decisions=[str(d) for d in data.get("key_decisions", [])][:5],
                files_modified=[str(f) for f in data.get("files_modified", session.files_touched)][
                    :10
                ],
                technologies=[str(t) for t in data.get("technologies", [])][:5],
                outcome=str(data.get("outcome", "Unknown outcome"))[:100],
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
        return "ollama"
