"""Ask-mode system prompt builder for analyzing previous command output.

Ask mode is a lightweight analysis mode that answers a user question using
the most recent command and its output as context. It does not use tool
calling and does not execute anything.
"""

from typing import Optional

from codedjinn.prompts.context_builder import build_environment, build_command_context


def _build_ask_system_info(os_name: str, shell: str) -> str:
    return f"""<system_info>
You are a {os_name} command-line assistant and code analyst using {shell}.
Answer the user's question based on the provided context.
</system_info>"""


def _build_ask_instructions() -> str:
    return """<instructions>
- Prefer using the provided command output as your source of truth
- If context is missing or insufficient, say so explicitly and ask for what you need
- Respond in plain text or markdown suitable for terminal display
</instructions>"""


def build_ask_system_prompt(
    os_name: str,
    shell: str,
    cwd: str,
    previous_context: Optional[dict] = None,
) -> str:
    """
    Build an ask-mode system prompt (no tools; analysis only).

    Args:
        os_name: Operating system name (e.g., "macOS", "Linux")
        shell: Shell type (e.g., "zsh", "bash")
        cwd: Current working directory path
        previous_context: Optional dict with keys:
            - command: Previous shell command
            - output: Previous command's output (already trimmed)
            - exit_code: Previous command's exit code

    Returns:
        XML-structured system prompt string
    """
    sections = [
        _build_ask_system_info(os_name, shell),
        build_environment(cwd),
    ]

    if previous_context is not None:
        sections.append(build_command_context(previous_context))
    else:
        sections.append(
            """<command_context>
<previous_command missing="true">
  <note>No previous command context is available for this session.</note>
</previous_command>
</command_context>"""
        )

    sections.append(_build_ask_instructions())

    return "\n\n".join(sections)
