"""Run-mode system prompt builder for command generation with tool calling.

This module builds the system prompt for run mode, which uses the LLM's
tool calling capability to execute shell commands.
"""

from codedjinn.context.contextualiser import ContextualiserResult


def build_run_prompt(ctx: ContextualiserResult) -> str:
    """
    Build system prompt for run mode.

    This mode uses tool calling - the LLM calls execute_shell_command tool.

    Args:
        ctx: ContextualiserResult from contextualiser.contextualise()

    Returns:
        Complete XML-structured system prompt

    Structure:
        1. <role> - What the assistant is
        2. <system_context> - OS, shell, cwd
        3. <shellhist_context> - Recent commands (if available)
        4. <localproject_context> - Project detection (if available)
        5. <session_context> - Previous command (if available)
        6. <instructions> - How to behave
    """
    sections = []

    # 1. Role description
    sections.append(f"""<role>
You are Code Djinn - a {ctx.system_context.os_name} shell command assistant using {ctx.system_context.shell}.
Generate shell commands using the execute_shell_command tool.
</role>""")

    # 2. Tool capabilities
    sections.append(ctx.capabilities_xml)

    # 3. System context (always present)
    sections.append(ctx.system_xml)

    # 4. Shell history (if available)
    if ctx.shellhist_context.recent_commands:
        sections.append(ctx.shellhist_xml)

    # 5. Local project context (if available)
    if ctx.localproject_context:
        sections.append(ctx.project_xml)

    # 6. File context (user-added files)
    if ctx.file_context and not ctx.file_context.is_empty():
        sections.append(ctx.file_xml)

    # 7. Session context (if available)
    if ctx.session_context:
        sections.append(ctx.session_xml)

    # 8. Instructions
    sections.append(f"""<instructions>
- Generate concise, appropriate commands for the user's request
- Consider working directory, project context, and command history
- Leverage shell history to understand the user's workflow
- Use proper {ctx.system_context.shell} syntax for {ctx.system_context.os_name}
- When user references "that file" or "the error", check session_context
- When files are in <file_context>, use them to understand code structure
- Avoid full-screen TUI programs (htop, vim, less, etc.) - prefer text-output commands like ps, grep, cat

Context management tips (for multi-step analysis):
- If user needs deep file analysis, suggest: code-djinn context add <file> --duration 30m
- Files in context persist across commands until expiration (default 10 min)
- To view current context: code-djinn context list
- To clear context: code-djinn context clear
- For quick one-off file reads, prefer cat/head instead of adding to context
</instructions>""")

    return "\n\n".join(sections)
