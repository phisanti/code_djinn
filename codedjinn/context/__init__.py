"""Context building and prompt management.

This module provides context detection and prompt construction for Code Djinn.
"""

from codedjinn.context.contextualiser import (
    contextualise,
    ContextualiserResult,
)
from codedjinn.context.run_prompt import build_run_prompt
from codedjinn.context.ask_prompt import build_ask_prompt
from codedjinn.context.parser import (
    escape_xml_content,
    wrap_xml_tag,
    simple_xml_tag,
)
from codedjinn.context.step_budget import (
    init_session_state_for_steps,
    advance_step_budget,
    normalize_max_steps,
    refresh_step_context,
)

# Re-exports from sources/ (advanced usage)
from codedjinn.context.sources.project import (
    get_project_detector,
    LocalProjectContext,
)
from codedjinn.context.sources.shell import (
    get_shell_context,
    SystemContext,
    ShellHistContext,
)


def build_prompt(
    mode: str,
    os_name: str,
    shell: str,
    cwd: str,
    session_context: dict = None,
    include_shellhist: bool = True,
    include_localproject: bool = True
) -> str:
    """
    Main entry point - build prompt for any mode.

    This is the primary function used by providers.

    Args:
        mode: "run" or "ask"
        os_name: OS name from config
        shell: Shell type from config
        cwd: Current working directory
        session_context: Previous command context from Session
        include_shellhist: Include shell history
        include_localproject: Include project detection

    Returns:
        Complete system prompt string

    Example:
        >>> from codedjinn.context import build_prompt
        >>> prompt = build_prompt(
        ...     mode="run",
        ...     os_name="macOS",
        ...     shell="zsh",
        ...     cwd="/Users/dev/project",
        ...     session_context=None
        ... )
    """
    # 1. Gather all context
    ctx = contextualise(
        os_name=os_name,
        shell=shell,
        cwd=cwd,
        session_context=session_context,
        include_shellhist=include_shellhist,
        include_localproject=include_localproject
    )

    # 2. Build mode-specific prompt
    if mode == "run":
        return build_run_prompt(ctx)
    elif mode == "ask":
        return build_ask_prompt(ctx)
    else:
        raise ValueError(f"Unknown mode: {mode}. Use 'run' or 'ask'.")


__all__ = [
    # Main API
    "build_prompt",
    "contextualise",
    "ContextualiserResult",

    # Mode builders
    "build_run_prompt",
    "build_ask_prompt",

    # XML utilities
    "escape_xml_content",
    "wrap_xml_tag",
    "simple_xml_tag",

    # Step budget
    "init_session_state_for_steps",
    "advance_step_budget",
    "normalize_max_steps",
    "refresh_step_context",

    # Advanced (sources)
    "get_project_detector",
    "get_shell_context",
    "LocalProjectContext",
    "SystemContext",
    "ShellHistContext",
]
