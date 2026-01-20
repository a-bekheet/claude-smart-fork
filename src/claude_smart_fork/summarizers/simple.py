"""Simple keyword-based summarizer (no LLM required)."""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path
from typing import TYPE_CHECKING

from claude_smart_fork.summarizers.base import BaseSummarizer, SessionSummaryData

if TYPE_CHECKING:
    from claude_smart_fork.config import Config
    from claude_smart_fork.parser import SessionData


# Technology detection patterns
TECH_PATTERNS = {
    # Languages by file extension
    ".py": "Python",
    ".ts": "TypeScript",
    ".tsx": "React",
    ".js": "JavaScript",
    ".jsx": "React",
    ".rs": "Rust",
    ".go": "Go",
    ".java": "Java",
    ".rb": "Ruby",
    ".php": "PHP",
    ".vue": "Vue",
    ".svelte": "Svelte",
    ".swift": "Swift",
    ".kt": "Kotlin",
    ".cs": "C#",
    ".cpp": "C++",
    ".c": "C",
    ".scala": "Scala",
    ".ex": "Elixir",
    ".clj": "Clojure",
    ".hs": "Haskell",
    # Config files
    "Dockerfile": "Docker",
    "docker-compose": "Docker",
    ".yml": "YAML",
    ".yaml": "YAML",
    "package.json": "Node.js",
    "Cargo.toml": "Rust",
    "go.mod": "Go",
    "requirements.txt": "Python",
    "pyproject.toml": "Python",
    "Gemfile": "Ruby",
    "pom.xml": "Maven",
    "build.gradle": "Gradle",
    ".tf": "Terraform",
    "k8s": "Kubernetes",
}

# Keywords that suggest topic categories
TOPIC_KEYWORDS = {
    "auth": ["authentication", "login", "oauth", "jwt", "token", "password", "session"],
    "api": ["api", "endpoint", "rest", "graphql", "route", "controller"],
    "database": ["database", "sql", "query", "migration", "schema", "model"],
    "ui": ["component", "button", "form", "modal", "css", "style", "layout"],
    "test": ["test", "spec", "jest", "pytest", "unittest", "coverage"],
    "deploy": ["deploy", "ci", "cd", "pipeline", "docker", "kubernetes"],
    "bug": ["fix", "bug", "error", "issue", "broken", "crash"],
    "refactor": ["refactor", "cleanup", "optimize", "improve", "restructure"],
    "feature": ["feature", "implement", "add", "create", "new"],
    "docs": ["documentation", "readme", "comment", "docstring"],
}


class SimpleSummarizer(BaseSummarizer):
    """
    Simple summarizer using keyword extraction.

    This summarizer doesn't require any LLM - it uses heuristics
    to extract key information from sessions.
    """

    def __init__(self, config: Config) -> None:
        super().__init__(config)

    def summarize(self, session: SessionData) -> SessionSummaryData:
        """Generate a summary using keyword extraction."""
        # Detect technologies
        technologies = self._detect_technologies(session)

        # Extract topic from user prompts
        topic = self._extract_topic(session)

        # Extract key decisions (heuristic: look for certain patterns)
        key_decisions = self._extract_decisions(session)

        # Get modified files
        files_modified = session.files_touched[:10]

        # Determine outcome
        outcome = self._determine_outcome(session)

        return SessionSummaryData(
            topic=topic,
            key_decisions=key_decisions,
            files_modified=files_modified,
            technologies=technologies,
            outcome=outcome,
        )

    def _detect_technologies(self, session: SessionData) -> list[str]:
        """Detect technologies from file paths and content."""
        techs: set[str] = set()

        # Check file extensions
        for filepath in session.files_touched:
            path = Path(filepath)
            ext = path.suffix.lower()
            name = path.name.lower()

            if ext in TECH_PATTERNS:
                techs.add(TECH_PATTERNS[ext])

            for pattern, tech in TECH_PATTERNS.items():
                if pattern in name:
                    techs.add(tech)

        # Check message content for technology mentions
        all_text = " ".join(m.content.lower() for m in session.messages)

        tech_mentions = [
            ("react", "React"),
            ("vue", "Vue"),
            ("angular", "Angular"),
            ("express", "Express"),
            ("fastapi", "FastAPI"),
            ("django", "Django"),
            ("flask", "Flask"),
            ("nextjs", "Next.js"),
            ("next.js", "Next.js"),
            ("postgres", "PostgreSQL"),
            ("mongodb", "MongoDB"),
            ("redis", "Redis"),
            ("graphql", "GraphQL"),
            ("docker", "Docker"),
            ("kubernetes", "Kubernetes"),
            ("aws", "AWS"),
            ("gcp", "GCP"),
            ("azure", "Azure"),
        ]

        for keyword, tech in tech_mentions:
            if keyword in all_text:
                techs.add(tech)

        return sorted(techs)[:5]

    def _extract_topic(self, session: SessionData) -> str:
        """Extract a topic description from user prompts."""
        user_prompts = session.get_user_prompts()

        if not user_prompts:
            return f"Session in {session.project_name}"

        # Use the first substantial user prompt as the topic
        for prompt in user_prompts:
            # Skip very short prompts
            if len(prompt) < 20:
                continue

            # Clean and truncate
            topic = prompt.strip()
            topic = re.sub(r"\s+", " ", topic)  # Normalize whitespace

            # Take first sentence or first 100 chars
            if "." in topic[:100]:
                topic = topic[: topic.index(".") + 1]
            else:
                topic = topic[:100]
                if len(prompt) > 100:
                    topic += "..."

            return topic

        # Fallback: use project name and category
        category = self._detect_category(session)
        return f"{category} work in {session.project_name}"

    def _detect_category(self, session: SessionData) -> str:
        """Detect the category of work from keywords."""
        all_text = " ".join(m.content.lower() for m in session.messages)

        category_scores: dict[str, int] = {}

        for category, keywords in TOPIC_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in all_text)
            if score > 0:
                category_scores[category] = score

        if category_scores:
            best = max(category_scores, key=lambda k: category_scores[k])
            return best.capitalize()

        return "Development"

    def _extract_decisions(self, session: SessionData) -> list[str]:
        """Extract key decisions from the conversation."""
        decisions: list[str] = []

        decision_patterns = [
            r"(?:let's|we'll|I'll|going to|decided to|choosing|using|implementing)\s+(.+?)(?:\.|$)",
            r"(?:the plan is|the approach is|we should)\s+(.+?)(?:\.|$)",
        ]

        for msg in session.messages:
            if msg.role != "assistant":
                continue

            for pattern in decision_patterns:
                matches = re.findall(pattern, msg.content, re.IGNORECASE)
                for match in matches:
                    decision = match.strip()
                    if 20 < len(decision) < 150:
                        decisions.append(decision)

        # Deduplicate and limit
        seen = set()
        unique_decisions = []
        for d in decisions:
            normalized = d.lower()[:50]
            if normalized not in seen:
                seen.add(normalized)
                unique_decisions.append(d)

        return unique_decisions[:3]

    def _determine_outcome(self, session: SessionData) -> str:
        """Determine the outcome of the session."""
        # Look at the last few messages
        last_messages = session.messages[-3:]

        # Check for completion indicators
        completion_words = ["done", "complete", "finished", "working", "success", "merged"]
        error_words = ["error", "failed", "broken", "issue", "problem", "bug"]

        last_content = " ".join(m.content.lower() for m in last_messages)

        has_completion = any(w in last_content for w in completion_words)
        has_error = any(w in last_content for w in error_words)

        if has_error and not has_completion:
            return "In progress - encountered issues"
        elif has_completion:
            return "Completed successfully"
        else:
            return f"{session.message_count} messages, {session.duration_minutes:.0f} min session"

    @property
    def name(self) -> str:
        """Return the summarizer name."""
        return "simple"
