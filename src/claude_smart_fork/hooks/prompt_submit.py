#!/usr/bin/env python3
"""
UserPromptSubmit hook for Claude Code.

Checks for pending sessions that need indexing.

Add to ~/.claude/settings.json:
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "type": "command",
        "command": "python -m claude_smart_fork.hooks.prompt_submit",
        "timeout": 5000
      }
    ]
  }
}

Note: This hook has a short timeout to avoid slowing down the user experience.
It only checks for pending work and flags it for later processing.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from pathlib import Path


def setup_logging() -> logging.Logger:
    """Set up logging for hooks."""
    log_dir = Path.home() / ".claude-smart-fork" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("smart-fork-hooks")
    logger.setLevel(logging.INFO)

    # Only add handler if not already present
    if not logger.handlers:
        handler = logging.FileHandler(log_dir / "hooks.log")
        handler.setFormatter(logging.Formatter("%(asctime)s - %(message)s"))
        logger.addHandler(handler)

    return logger


def on_prompt_submit() -> None:
    """Handle prompt submit event."""
    logger = setup_logging()

    state_path = Path.home() / ".claude-smart-fork" / "index-state.json"

    if not state_path.exists():
        return

    try:
        with open(state_path) as f:
            state = json.load(f)
    except (json.JSONDecodeError, OSError):
        return

    needs_work = False

    # Check for pending sessions
    pending = state.get("pending_sessions", [])
    if pending:
        needs_work = True
        logger.info(f"Found {len(pending)} pending sessions")

    # Check if current session needs a 30-minute update
    session_id = os.environ.get("CLAUDE_SESSION_ID", "")
    if session_id and session_id in state.get("indexed_sessions", {}):
        session_info = state["indexed_sessions"][session_id]
        last_summary = session_info.get("last_summary_at")

        if last_summary:
            try:
                last_time = datetime.fromisoformat(last_summary)
                elapsed = (datetime.now() - last_time).total_seconds() / 60

                if elapsed >= 30:
                    needs_work = True
                    logger.info(f"Session {session_id[:12]} needs 30-min update")
            except ValueError:
                pass

    # Write flag file for other tools to detect
    flag_path = Path.home() / ".claude-smart-fork" / ".needs_indexing"

    if needs_work:
        flag_path.touch()
    elif flag_path.exists():
        flag_path.unlink()


def main() -> None:
    """Entry point for hook script."""
    on_prompt_submit()


if __name__ == "__main__":
    main()
