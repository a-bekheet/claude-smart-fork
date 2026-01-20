# claude-smart-fork

[![PyPI version](https://badge.fury.io/py/claude-smart-fork.svg)](https://badge.fury.io/py/claude-smart-fork)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![CI](https://github.com/a-bekheet/claude-smart-fork/actions/workflows/ci.yml/badge.svg)](https://github.com/a-bekheet/claude-smart-fork/actions/workflows/ci.yml)

**Semantic search across your Claude Code sessions.** Find the most relevant context for new tasks instead of starting from scratch.

<p align="center">
  <img src="https://raw.githubusercontent.com/a-bekheet/claude-smart-fork/main/docs/demo.gif" alt="Demo" width="600">
</p>

## The Problem

You've had hundreds of Claude Code sessions. Each one contains valuable context: decisions made, patterns established, problems solved. But when you start a new task, all that knowledge is locked away in session files you can't easily search.

## The Solution

`claude-smart-fork` indexes your Claude Code session history and lets you semantically search for relevant past sessions. Found a good match? Fork from that session and continue with all the context already loaded.

```bash
$ smart-fork search "add rate limiting to Express API"

🔍 Top Matching Sessions:

1. 🟢 [94%] a1b2c3d4...
   📁 ~/projects/my-api
   📝 API middleware and request handling patterns
   🛠️ TypeScript, Express, Redis

2. 🟡 [82%] e5f6g7h8...
   📁 ~/projects/rate-limiter
   📝 Redis-based rate limiting implementation

To fork the top result:
  claude --resume a1b2c3d4-full-session-id
```

## Installation

### Minimal Install (Keyword Search)

```bash
pip install claude-smart-fork
```

This gives you the CLI with basic keyword-based search. No heavy dependencies.

### With Vector Search (Recommended)

```bash
pip install "claude-smart-fork[chromadb,embeddings]"
```

Adds semantic search using local embeddings (~300MB for the model, downloaded once).

### With LLM Summarization

```bash
# Using Claude API
pip install "claude-smart-fork[claude]"

# Using local Ollama
pip install "claude-smart-fork[ollama]"
```

### Everything

```bash
pip install "claude-smart-fork[all]"
```

## Quick Start

### 1. Initialize

```bash
smart-fork init
```

This creates `~/.claude-smart-fork/` with default configuration.

### 2. Index Your Sessions

```bash
# Preview what would be indexed
smart-fork index --dry-run

# Index all sessions
smart-fork index
```

### 3. Search

```bash
smart-fork search "implement OAuth authentication"
```

### 4. Fork

Copy the session ID from the search results and use Claude Code's built-in resume:

```bash
claude --resume <session-id>
```

## Configuration

Configuration is stored in `~/.claude-smart-fork/config.json`:

```json
{
  "sessions_path": "~/.claude/projects",
  "backend": "chromadb",
  "embedding_model": "nomic-ai/nomic-embed-text-v1",
  "summarizer": "simple",
  "auto_index": true,
  "search_results_limit": 5
}
```

### Backend Options

| Backend | Install | Description |
|---------|---------|-------------|
| `sqlite` | Base | Keyword search, no vectors |
| `chromadb` | `[chromadb]` | Vector search with local embeddings |

### Embedding Models

| Model | Size | Quality | Install |
|-------|------|---------|---------|
| `nomic-ai/nomic-embed-text-v1` | 270MB | Best for code | `[embeddings]` |
| `all-MiniLM-L6-v2` | 80MB | Good, faster | `[embeddings]` |
| `openai` | API | Excellent | Requires API key |

### Summarizers

| Summarizer | Install | Description |
|------------|---------|-------------|
| `simple` | Base | Keyword extraction, no LLM |
| `claude` | `[claude]` | Claude API summarization |
| `ollama` | `[ollama]` | Local Ollama models |

## Claude Code Integration

### Automatic Indexing with Hooks

Add to `~/.claude/settings.json`:

```json
{
  "hooks": {
    "SessionEnd": [
      {
        "type": "command",
        "command": "smart-fork index-session $CLAUDE_SESSION_ID"
      }
    ]
  }
}
```

Now sessions are automatically indexed when they end.

### Custom Slash Command

Create `~/.claude/commands/detect-fork.md`:

```markdown
# /detect-fork

Search for relevant past sessions to fork from.

## Usage

Run: `smart-fork search "$ARGUMENTS"`

Present the results and offer to provide the fork command.
```

## CLI Reference

```bash
# Initialize configuration
smart-fork init [--force]

# Index sessions
smart-fork index [--dry-run] [--limit N] [--since DATE]

# Index a specific session
smart-fork index-session <session-id>

# Search sessions
smart-fork search <query> [--limit N] [--project PATH]

# Show statistics
smart-fork stats

# Show configuration
smart-fork config [--edit]

# Update configuration
smart-fork config set <key> <value>
```

## How It Works

1. **Parsing**: Reads Claude Code JSONL session files from `~/.claude/projects/`
2. **Summarization**: Extracts key information (topic, decisions, files, technologies)
3. **Embedding**: Converts summaries to vectors using local models
4. **Storage**: Stores vectors in ChromaDB for fast similarity search
5. **Search**: Converts your query to a vector and finds nearest neighbors

## Development

```bash
# Clone the repo
git clone https://github.com/a-bekheet/claude-smart-fork.git
cd claude-smart-fork

# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run linting
ruff check src tests
ruff format src tests

# Type checking
mypy src
```

## Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## Roadmap

- [ ] Cross-machine sync via Git
- [ ] Project-scoped search
- [ ] Time-based queries ("what was I working on Tuesday?")
- [ ] Session similarity chains
- [ ] VS Code extension
- [ ] Web UI for browsing sessions

## License

MIT License - see [LICENSE](LICENSE) for details.

## Acknowledgments

- Built for use with [Claude Code](https://claude.ai/code)
- Uses [ChromaDB](https://www.trychroma.com/) for vector storage
- Embeddings via [sentence-transformers](https://www.sbert.net/)
