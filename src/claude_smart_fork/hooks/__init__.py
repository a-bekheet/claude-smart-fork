"""Claude Code hooks for automatic session indexing."""

from claude_smart_fork.hooks.session_end import on_session_end
from claude_smart_fork.hooks.prompt_submit import on_prompt_submit

__all__ = ["on_session_end", "on_prompt_submit"]
