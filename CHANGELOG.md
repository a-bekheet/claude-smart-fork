# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-01-19

### Added

- Initial release
- Session JSONL parser for Claude Code session files
- SQLite backend with FTS5 for keyword search
- ChromaDB backend for semantic vector search (optional)
- Local embedding support via sentence-transformers (optional)
- OpenAI embedding support (optional)
- Simple keyword-based summarizer
- Claude API summarizer (optional)
- Ollama local LLM summarizer (optional)
- Typer-based CLI with commands:
  - `smart-fork init` - Initialize configuration
  - `smart-fork search` - Search sessions
  - `smart-fork index` - Index all sessions
  - `smart-fork index-session` - Index specific session
  - `smart-fork stats` - Show statistics
  - `smart-fork config` - View/edit configuration
  - `smart-fork clear` - Clear indexed data
- Claude Code hooks for automatic indexing:
  - SessionEnd hook
  - UserPromptSubmit hook
- Comprehensive test suite
- GitHub Actions CI workflow
