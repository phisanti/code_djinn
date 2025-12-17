"""Main system prompt builder using XML-structured format.

This module orchestrates the construction of system prompts by combining
multiple components (system info, environment, context, instructions) into
a cohesive XML-structured prompt that follows Anthropic's recommendations.
"""

from typing import Optional
from codedjinn.prompts.prompt_components import (
    build_system_info,
    build_environment,
    build_command_context,
    build_instructions
)


def build_system_prompt(
    os_name: str,
    shell: str,
    cwd: str,
    previous_context: Optional[dict] = None
) -> str:
    """
    Build system prompt using XML-like tags (Anthropic recommended format).

    Constructs a structured prompt with clear XML-like sections for better
    model comprehension. The structure includes:

    1. <system_info> - Role and task description
    2. <environment> - Current working directory
    3. <command_context> - Previous command (if available)
    4. <instructions> - Task guidelines

    Args:
        os_name: Operating system name (e.g., "macOS", "Linux")
        shell: Shell type (e.g., "zsh", "bash")
        cwd: Current working directory path
        previous_context: Optional dict with keys:
            - command: Previous shell command
            - output: Previous command's output (already trimmed)
            - exit_code: Previous command's exit code

    Returns:
        Complete XML-structured system prompt string

    Design Notes:
        - Uses XML-like tags (Anthropic recommendation for better parsing)
        - Sections are separated by double newlines for readability
        - Command context is optional and only included when available
        - Output is XML-escaped to handle special characters safely
    """
    sections = []

    # Section 1: System info (always present)
    sections.append(build_system_info(os_name, shell))

    # Section 2: Environment (always present)
    sections.append(build_environment(cwd))

    # Section 3: Command context (conditional - only if previous command exists)
    if previous_context is not None:
        sections.append(build_command_context(previous_context))

    # Section 4: Instructions (always present)
    sections.append(build_instructions(os_name, shell))

    # Join sections with double newlines for readability
    return "\n\n".join(sections)


# Legacy function for backward compatibility
def get_system_prompt() -> str:
    """
    Return a basic system prompt without context.

    NOTE: This is a legacy function. New code should use build_system_prompt()
    with proper context parameters for better results.

    Deprecated: Use build_system_prompt() instead.
    """
    return """<system_info>
You are a shell command assistant.
Generate appropriate shell commands to fulfill user requests.
Use the execute_shell_command tool to provide commands.
</system_info>

<instructions>
- Be concise and accurate
- Generate only the necessary command
</instructions>"""


# Future: Extended prompt for multi-step workflows
def build_agentic_prompt(os_name: str, shell: str, cwd: str, max_steps: int) -> str:
    """
    Build system prompt for multi-step agentic workflows.

    NOT IMPLEMENTED IN PHASE 1 - placeholder for future work.

    This would include instructions for:
    - Breaking down complex tasks into steps
    - Observing command output before next step
    - Error recovery strategies
    - Step budget management
    """
    raise NotImplementedError("Multi-step prompts not implemented in Phase 1")
