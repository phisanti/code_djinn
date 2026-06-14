"""Run-mode system prompt builder for command generation."""

from codedjinn.context.contextualiser import ContextualiserResult


def build_run_prompt(ctx: ContextualiserResult) -> str:
    """
    Build system prompt for run mode.

    This mode uses tool calling: the model returns one shell command through
    execute_shell_command.

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

    # 2. System context (always present)
    sections.append(ctx.system_xml)

    # 3. Shell history (if available)
    if ctx.shellhist_context.recent_commands:
        sections.append(ctx.shellhist_xml)

    # 4. Local project context (if available)
    if ctx.localproject_context:
        sections.append(ctx.project_xml)

    # 5. File context (user-added files)
    if ctx.file_context and not ctx.file_context.is_empty():
        sections.append(ctx.file_xml)

    # 6. Session context (if available)
    if ctx.session_context:
        sections.append(ctx.session_xml)

    # 7. Instructions
    sections.append(f"""<instructions>
- Generate one concise command that fulfills the user's request.
- Prefer simple, fast shell tools over multi-command scripts.
- For file-content searches, prefer `rg -n --hidden --glob '!.git' <pattern> .`; if ripgrep is unavailable, use grep/find.
- For filename searches, prefer `find . -name <pattern>` or `rg --files | rg <pattern>`.
- Consider working directory, project context, and command history only when relevant.
- Use proper {ctx.system_context.shell} syntax for {ctx.system_context.os_name}
- When user references "that file" or "the error", check session_context
- When files are in <file_context>, use them to understand code structure
- Avoid full-screen TUI programs such as htop, vim, and less; prefer commands that print and exit.
</instructions>""")

    return "\n\n".join(sections)
