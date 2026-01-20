"""Local embedding provider using sentence-transformers."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, TypedDict

try:
    from sentence_transformers import SentenceTransformer

    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False

from claude_smart_fork.embeddings.base import BaseEmbeddingProvider

if TYPE_CHECKING:
    from claude_smart_fork.config import Config


class ModelConfig(TypedDict):
    """Type for model configuration."""

    dimension: int
    query_prefix: str
    document_prefix: str
    trust_remote_code: bool


# Model configurations
MODEL_CONFIGS: dict[str, ModelConfig] = {
    "nomic-ai/nomic-embed-text-v1": {
        "dimension": 768,
        "query_prefix": "search_query: ",
        "document_prefix": "search_document: ",
        "trust_remote_code": True,
    },
    "all-MiniLM-L6-v2": {
        "dimension": 384,
        "query_prefix": "",
        "document_prefix": "",
        "trust_remote_code": False,
    },
    "all-mpnet-base-v2": {
        "dimension": 768,
        "query_prefix": "",
        "document_prefix": "",
        "trust_remote_code": False,
    },
}


class LocalEmbeddingProvider(BaseEmbeddingProvider):
    """
    Local embedding provider using sentence-transformers.

    Requires: pip install claude-smart-fork[embeddings]

    Supported models:
    - nomic-ai/nomic-embed-text-v1 (recommended, best for code)
    - all-MiniLM-L6-v2 (smaller, faster)
    - all-mpnet-base-v2 (good quality)
    """

    def __init__(self, config: Config) -> None:
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            raise ImportError(
                "sentence-transformers is not installed. "
                "Install with: pip install claude-smart-fork[embeddings]"
            )

        super().__init__(config)

        self._model_name = config.embedding_model
        default_config: ModelConfig = {
            "dimension": 768,
            "query_prefix": "",
            "document_prefix": "",
            "trust_remote_code": False,
        }
        self._model_config: ModelConfig = MODEL_CONFIGS.get(self._model_name, default_config)

        # Set cache directory
        cache_dir = config.data_dir / "models"
        cache_dir.mkdir(parents=True, exist_ok=True)
        os.environ["SENTENCE_TRANSFORMERS_HOME"] = str(cache_dir)

        # Load model (downloads on first use)
        self._model = SentenceTransformer(
            self._model_name,
            trust_remote_code=bool(self._model_config["trust_remote_code"]),
        )

    def embed(self, text: str) -> list[float]:
        """Generate embedding for a document text."""
        prefix = self._model_config["document_prefix"]
        prefixed_text = f"{prefix}{text}" if prefix else text

        embedding = self._model.encode(prefixed_text, convert_to_numpy=True)
        return list(embedding.tolist())

    def embed_query(self, query: str) -> list[float]:
        """Generate embedding for a search query."""
        prefix = self._model_config["query_prefix"]
        prefixed_query = f"{prefix}{query}" if prefix else query

        embedding = self._model.encode(prefixed_query, convert_to_numpy=True)
        return list(embedding.tolist())

    def embed_batch(self, texts: list[str], batch_size: int = 32) -> list[list[float]]:
        """Generate embeddings for multiple texts efficiently."""
        prefix = self._model_config["document_prefix"]
        prefixed_texts = [f"{prefix}{t}" if prefix else t for t in texts]

        embeddings = self._model.encode(
            prefixed_texts,
            convert_to_numpy=True,
            batch_size=batch_size,
            show_progress_bar=len(texts) > 10,
        )

        return [list(e) for e in embeddings.tolist()]

    @property
    def dimension(self) -> int:
        """Return the embedding dimension."""
        return self._model_config["dimension"]

    @property
    def model_name(self) -> str:
        """Return the model name."""
        return self._model_name
