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

    # 6. Session context (if available)
    if ctx.session_context:
        sections.append(ctx.session_xml)

    # 7. Instructions
    sections.append(f"""<instructions>
- Generate concise, appropriate commands for the user's request
- Consider working directory, project context, and command history
- Leverage shell history to understand the user's workflow
- Use proper {ctx.system_context.shell} syntax for {ctx.system_context.os_name}
- When user references "that file" or "the error", check session_context
</instructions>""")

    return "\n\n".join(sections)
