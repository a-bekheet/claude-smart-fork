"""Configuration management for claude-smart-fork."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Default paths
DEFAULT_DATA_DIR = Path.home() / ".claude-smart-fork"
DEFAULT_SESSIONS_PATH = Path.home() / ".claude" / "projects"
DEFAULT_CONFIG_PATH = DEFAULT_DATA_DIR / "config.json"


class Config(BaseSettings):
    """Main configuration for claude-smart-fork."""

    model_config = SettingsConfigDict(
        env_prefix="CSF_",
        env_file=".env",
        extra="ignore",
    )

    # Paths
    data_dir: Path = Field(
        default=DEFAULT_DATA_DIR,
        description="Directory for storing index and cache data",
    )
    sessions_path: Path = Field(
        default=DEFAULT_SESSIONS_PATH,
        description="Path to Claude Code sessions directory",
    )

    # Backend configuration
    backend: Literal["sqlite", "chromadb"] = Field(
        default="sqlite",
        description="Storage backend for session index",
    )

    # Embedding configuration
    embedding_provider: Literal["none", "local", "openai"] = Field(
        default="none",
        description="Embedding provider for semantic search",
    )
    embedding_model: str = Field(
        default="nomic-ai/nomic-embed-text-v1",
        description="Model name for local embeddings",
    )

    # Summarization configuration
    summarizer: Literal["simple", "claude", "ollama"] = Field(
        default="simple",
        description="Summarization provider",
    )
    ollama_model: str = Field(
        default="llama3.2",
        description="Ollama model for summarization",
    )

    # Search configuration
    search_results_limit: int = Field(
        default=5,
        ge=1,
        le=50,
        description="Maximum number of search results to return",
    )
    min_session_messages: int = Field(
        default=3,
        ge=1,
        description="Minimum messages for a session to be indexed",
    )

    # Auto-indexing
    auto_index: bool = Field(
        default=True,
        description="Automatically index sessions when they end",
    )

    # API keys (optional, can also be set via environment)
    anthropic_api_key: str | None = Field(
        default=None,
        description="Anthropic API key for Claude summarization",
    )
    openai_api_key: str | None = Field(
        default=None,
        description="OpenAI API key for embeddings",
    )

    @property
    def db_path(self) -> Path:
        """Path to the database directory."""
        return self.data_dir / "db"

    @property
    def summaries_path(self) -> Path:
        """Path to the summaries cache directory."""
        return self.data_dir / "summaries"

    @property
    def logs_path(self) -> Path:
        """Path to logs directory."""
        return self.data_dir / "logs"

    @property
    def state_path(self) -> Path:
        """Path to the index state file."""
        return self.data_dir / "index-state.json"

    def ensure_directories(self) -> None:
        """Create necessary directories if they don't exist."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.db_path.mkdir(parents=True, exist_ok=True)
        self.summaries_path.mkdir(parents=True, exist_ok=True)
        self.logs_path.mkdir(parents=True, exist_ok=True)

    def save(self, path: Path | None = None) -> None:
        """Save configuration to a JSON file."""
        path = path or (self.data_dir / "config.json")
        path.parent.mkdir(parents=True, exist_ok=True)

        # Only save non-sensitive, non-default values
        data = self.model_dump(
            exclude={"anthropic_api_key", "openai_api_key"},
            exclude_defaults=False,
        )

        # Convert paths to strings for JSON
        for key, value in data.items():
            if isinstance(value, Path):
                data[key] = str(value)

        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load(cls, path: Path | None = None) -> Config:
        """Load configuration from a JSON file."""
        path = path or DEFAULT_CONFIG_PATH

        if not path.exists():
            return cls()

        with open(path) as f:
            data = json.load(f)

        return cls(**data)


class IndexState(BaseModel):
    """Tracks the state of indexed sessions."""

    last_full_index: str | None = None
    indexed_sessions: dict[str, SessionIndexInfo] = Field(default_factory=dict)


class SessionIndexInfo(BaseModel):
    """Information about an indexed session."""

    last_indexed: str
    message_count: int
    last_summary_at: str | None = None
    project_path: str | None = None


# Global config instance (lazy loaded)
_config: Config | None = None


def get_config(reload: bool = False) -> Config:
    """Get the global configuration instance."""
    global _config
    if _config is None or reload:
        _config = Config.load()
    return _config


def init_config(force: bool = False) -> Config:
    """Initialize configuration with defaults."""
    config = Config()
    config_path = config.data_dir / "config.json"

    if config_path.exists() and not force:
        return Config.load(config_path)

    config.ensure_directories()
    config.save(config_path)
    return config
