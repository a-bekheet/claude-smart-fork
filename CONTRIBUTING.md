# Contributing to claude-smart-fork

Thank you for your interest in contributing! This document provides guidelines and instructions for contributing.

## Development Setup

### Prerequisites

- Python 3.10 or higher
- Git

### Getting Started

1. Fork the repository on GitHub
2. Clone your fork locally:
   ```bash
   git clone https://github.com/YOUR-USERNAME/claude-smart-fork.git
   cd claude-smart-fork
   ```
3. Create a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```
4. Install development dependencies:
   ```bash
   pip install -e ".[dev,all]"
   ```
5. Install pre-commit hooks:
   ```bash
   pre-commit install
   ```

## Code Style

This project uses:
- **Ruff** for linting and formatting
- **MyPy** for type checking
- **Pytest** for testing

### Running Checks

```bash
# Format code
ruff format src tests

# Lint code
ruff check src tests --fix

# Type check
mypy src

# Run tests
pytest

# Run all checks
pre-commit run --all-files
```

## Making Changes

### Branch Naming

- `feature/description` - New features
- `fix/description` - Bug fixes
- `docs/description` - Documentation updates
- `refactor/description` - Code refactoring

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
type(scope): description

[optional body]

[optional footer]
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

Examples:
```
feat(search): add project filtering to search results
fix(parser): handle empty JSONL files gracefully
docs(readme): add installation instructions for Windows
```

### Pull Requests

1. Create a branch from `main`
2. Make your changes
3. Add tests for new functionality
4. Ensure all checks pass
5. Update documentation if needed
6. Submit a pull request

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=claude_smart_fork --cov-report=html

# Run specific test file
pytest tests/test_parser.py

# Run tests matching a pattern
pytest -k "test_search"

# Skip slow tests
pytest -m "not slow"
```

### Writing Tests

- Place tests in the `tests/` directory
- Name test files `test_*.py`
- Name test functions `test_*`
- Use fixtures for common setup
- Mark slow tests with `@pytest.mark.slow`

## Architecture

### Directory Structure

```
src/claude_smart_fork/
├── cli.py              # Typer CLI commands
├── config.py           # Configuration management
├── parser.py           # Session JSONL parsing
├── indexer.py          # Index management
├── search.py           # Search interface
├── backends/           # Storage backends (pluggable)
│   ├── base.py         # Abstract base class
│   ├── sqlite.py       # SQLite backend
│   └── chromadb.py     # ChromaDB backend
├── embeddings/         # Embedding providers (pluggable)
│   ├── base.py
│   ├── local.py
│   └── api.py
├── summarizers/        # Summarization providers (pluggable)
│   ├── base.py
│   ├── simple.py
│   ├── claude.py
│   └── ollama.py
└── hooks/              # Claude Code hooks
```

### Adding a New Backend

1. Create a new file in `backends/`
2. Implement the `Backend` protocol from `backends/base.py`
3. Register it in `backends/__init__.py`
4. Add any new dependencies as optional in `pyproject.toml`
5. Add tests in `tests/test_backends.py`

### Adding a New Embedding Provider

1. Create a new file in `embeddings/`
2. Implement the `EmbeddingProvider` protocol
3. Register it in `embeddings/__init__.py`
4. Add dependencies as optional extras

### Adding a New Summarizer

1. Create a new file in `summarizers/`
2. Implement the `Summarizer` protocol
3. Register it in `summarizers/__init__.py`
4. Add dependencies as optional extras

## Documentation

- Update README.md for user-facing changes
- Add docstrings to all public functions and classes
- Use Google-style docstrings

## Releasing

Releases are managed by maintainers:

1. Update version in `pyproject.toml`
2. Update CHANGELOG.md
3. Create a git tag
4. Push to trigger CI/CD

## Questions?

Open an issue or start a discussion on GitHub.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
