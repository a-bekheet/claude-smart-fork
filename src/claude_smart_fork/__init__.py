"""
claude-smart-fork: Semantic search across Claude Code sessions.

Find the most relevant context for new tasks by searching your session history.
"""

__version__ = "0.1.0"
__author__ = "a-bekheet"

from claude_smart_fork.config import Config, get_config
from claude_smart_fork.parser import SessionData, parse_session_file
from claude_smart_fork.search import search_sessions

__all__ = [
    "__version__",
    "Config",
    "get_config",
    "SessionData",
    "parse_session_file",
    "search_sessions",
]
