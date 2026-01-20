#!/usr/bin/env python3
"""
SessionEnd hook for Claude Code.

Triggers session indexing when a Claude Code session ends.

Add to ~/.claude/settings.json:
{
  "hooks": {
    "SessionEnd": [
      {
        "type": "command",
        "command": "python -m claude_smart_fork.hooks.session_end"
      }
    ]
  }
}
"""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path


def setup_logging() -> logging.Logger:
    """Set up logging for hooks."""
    log_dir = Path.home() / ".claude-smart-fork" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("smart-fork-hooks")
    logger.setLevel(logging.INFO)

    handler = logging.FileHandler(log_dir / "hooks.log")
    handler.setFormatter(logging.Formatter("%(asctime)s - %(message)s"))
    logger.addHandler(handler)

    return logger


def on_session_end() -> None:
    """Handle session end event."""
    logger = setup_logging()

    # Get session info from environment
    session_id = os.environ.get("CLAUDE_SESSION_ID", "")
    session_cwd = os.environ.get("CLAUDE_CWD", os.getcwd())

    if not session_id:
        logger.warning("No CLAUDE_SESSION_ID in environment")
        return

    logger.info(f"Session ended: {session_id}")

    # Try to index immediately if config allows
    try:
        from claude_smart_fork.config import get_config

        config = get_config()

        if not config.auto_index:
            logger.info("Auto-indexing disabled, skipping")
            return

        # Import indexer and index the session
        from claude_smart_fork.indexer import Indexer

        indexer = Indexer(config)
        success = indexer.index_session_by_id(session_id)

        if success:
            logger.info(f"Indexed session: {session_id}")
        else:
            logger.warning(f"Failed to index session: {session_id}")

    except Exception as e:
        logger.error(f"Error indexing session: {e}")

        # Fall back to marking as pending
        mark_session_pending(session_id, logger)


def mark_session_pending(session_id: str, logger: logging.Logger) -> None:
    """Mark a session as pending for later indexing."""
    state_path = Path.home() / ".claude-smart-fork" / "index-state.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)

    # Load or create state
    if state_path.exists():
        with open(state_path) as f:
            state = json.load(f)
    else:
        state = {"indexed_sessions": {}, "pending_sessions": []}

    if "pending_sessions" not in state:
        state["pending_sessions"] = []

    # Add to pending if not already there
    if session_id not in state.get("pending_sessions", []):
        state["pending_sessions"].append(session_id)

        with open(state_path, "w") as f:
            json.dump(state, f, indent=2)

        logger.info(f"Marked session as pending: {session_id}")


def main() -> None:
    """Entry point for hook script."""
    on_session_end()


if __name__ == "__main__":
    main()
