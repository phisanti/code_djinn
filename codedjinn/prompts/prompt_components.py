"""Component builders for structured XML prompts.

Each function builds a specific section of the system prompt
using XML-like tags following Anthropic's recommendations.
"""

from codedjinn.prompts.parser import escape_xml_content


def build_system_info(os_name: str, shell: str) -> str:
    """
    Build <system_info> section with role and task description.

    Args:
        os_name: Operating system name (e.g., "macOS", "Linux")
        shell: Shell type (e.g., "zsh", "bash")

    Returns:
        XML-formatted system info section
    """
    return f"""<system_info>
You are a {os_name} shell assistant using {shell}.
Generate appropriate shell commands using the execute_shell_command tool.
</system_info>"""


def build_environment(cwd: str) -> str:
    """
    Build <environment> section with working directory.

    Args:
        cwd: Current working directory path

    Returns:
        XML-formatted environment section
    """
    return f"""<environment>
<working_directory>{cwd}</working_directory>
</environment>"""


def build_command_context(context: dict) -> str:
    """
    Build <command_context> section with previous command details.

    Args:
        context: Dictionary containing:
            - command (str): The executed command
            - exit_code (int): Exit code (0 = success)
            - output (str): Command output (stdout + stderr)

    Returns:
        XML-formatted command context section

    Note:
        Output is automatically XML-escaped to handle special characters.
    """
    command = context['command']
    exit_code = context['exit_code']
    output = context['output']

    # Escape output for safe XML embedding
    escaped_output = escape_xml_content(output)

    # Build previous command subsection
    return f"""<command_context>
<previous_command>
  <executed>{command}</executed>
  <exit_code>{exit_code}</exit_code>
  <output>
{escaped_output}
  </output>
</previous_command>

<usage_note>
User requests may reference this previous command or its output.
Examples: "that file", "the error", "those branches", "the first one"
</usage_note>
</command_context>"""


def build_instructions(os_name: str, shell: str) -> str:
    """
    Build <instructions> section with task guidelines.

    Args:
        os_name: Operating system name
        shell: Shell type

    Returns:
        XML-formatted instructions section
    """
    return f"""<instructions>
- Generate concise, appropriate commands for the user's request
- Consider the working directory and any command context provided
- Use proper syntax for {shell} on {os_name}
</instructions>"""
