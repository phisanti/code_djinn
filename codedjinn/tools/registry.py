"""Mistral tool schema builder for shell execution."""


def build_mistral_tool_schema(os_name: str, shell: str) -> list[dict]:
    """
    Build Mistral-compatible tool schema for shell command execution.

    This function constructs the JSON schema that tells Mistral what
    tools are available and how to call them. The schema includes
    context about the user's environment (OS and shell) to help the
    model generate appropriate commands.

    Args:
        os_name: Operating system name (e.g., "macOS", "Linux", "Windows")
        shell: Shell type (e.g., "zsh", "bash", "fish")

    Returns:
        List of tool definitions in Mistral's expected format.
        Each tool has a "type" and "function" with name, description,
        and parameters (JSON schema).

    Example:
        >>> schema = build_mistral_tool_schema("macOS", "zsh")
        >>> schema[0]['function']['name']
        'execute_shell_command'

    Note:
        This currently defines only one tool (execute_shell_command).
        Future versions may add more tools (e.g., file_read, web_search).
        Keeping this in registry.py makes it easy to extend.
    """
    return [{
        "type": "function",
        "function": {
            "name": "execute_shell_command",
            "description": (
                f"Execute a {shell} command on {os_name}. "
                "Use this tool to fulfill the user's request by generating "
                "the appropriate shell command."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": (
                            "The exact shell command to execute. "
                            "Should be a valid command for the user's shell environment."
                        )
                    }
                },
                "required": ["command"]
            }
        }
    }]


# Future extension point for additional tools
# TODO: Add tools for multi-step workflows (Phase 2)
# - read_file: Read file contents for context
# - search_docs: Search documentation
# - explain_error: Explain command errors
def build_extended_tool_schema(os_name: str, shell: str, include_tools: list[str]) -> list[dict]:
    """
    Build extended tool schema with additional tools beyond shell execution.

    NOT IMPLEMENTED IN PHASE 1 - placeholder for future work.
    """
    raise NotImplementedError("Extended tools not implemented in Phase 1")
