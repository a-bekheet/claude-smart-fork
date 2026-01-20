"""Claude Code hooks for automatic session indexing."""

from claude_smart_fork.hooks.prompt_submit import on_prompt_submit
from claude_smart_fork.hooks.session_end import on_session_end

__all__ = ["on_session_end", "on_prompt_submit"]
