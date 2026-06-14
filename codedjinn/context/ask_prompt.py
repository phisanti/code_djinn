"""Ask-mode system prompt builder for lightweight analysis."""

from codedjinn.context.contextualiser import ContextualiserResult


def build_ask_prompt(ctx: ContextualiserResult) -> str:
    """
    Build system prompt for ask mode.

    This mode answers questions from existing context and can use read-only
    tools for quick file or repository inspection.

    Args:
        ctx: ContextualiserResult from contextualiser.contextualise()

    Returns:
        XML-structured system prompt for analysis

    Structure:
        1. <role> - Analysis assistant
        2. <system_context> - OS, shell, cwd
        3. <session_context> - Previous command (critical for ask mode)
        4. <instructions> - How to answer
    """
    sections = []

    # 1. Role description
    sections.append(f"""<role>
You are Code Djinn, a concise {ctx.system_context.os_name} command-line assistant for {ctx.system_context.shell}.
Answer from the provided context first. Use read-only tools only when extra file or repository evidence is needed.
</role>""")

    # 2. System context
    sections.append(ctx.system_xml)

    # 3. File context (user-added files)
    if ctx.file_context and not ctx.file_context.is_empty():
        sections.append(ctx.file_xml)

    # 4. Session context (critical for ask mode)
    if ctx.session_context:
        sections.append(ctx.session_xml)
    else:
        # Explicit message if no context available
        sections.append("""<session_context>
  <note>No previous command context available.</note>
  <suggestion>Run a command first, then use ask mode to analyze its output.</suggestion>
</session_context>""")

    # 5. Instructions
    sections.append("""<instructions>
- Prefer a direct answer when session_context or file_context already contains enough evidence.
- For "which file contains X", "where is X", or similar source searches, use execute_observe_command with `rg -n --hidden --glob '!.git' <pattern> .`; if ripgrep is unavailable, use grep/find.
- Use read_file only after locating a specific file that needs inspection.
- For git or directory questions, use focused read-only commands such as git status, git diff, git log, ls, find, head, tail, wc, sed, awk, sort, and uniq.
- For process or system diagnostics, use focused read-only commands such as pgrep, ps, lsof, df, du, vm_stat, free, netstat, or ss.
- Never use destructive commands. If evidence is insufficient, say what is missing.
- Keep answers terminal-friendly and concise. Do not include tool traces unless the UI asks for verbose output.
</instructions>""")

    return "\n\n".join(sections)
