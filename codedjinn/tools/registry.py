"""Mistral tool schema builders.

Tool schemas are prompt surface area. Keeping them short improves latency and
reduces the chance that the model follows long capability prose instead of the
current user request.
"""


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
                "Return the single shell command that fulfills the user's request. "
                "Prefer fast standard CLI tools; use ripgrep (`rg`) for repository searches when available."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": (
                            "The exact command to execute in the user's shell."
                        )
                    }
                },
                "required": ["command"]
            }
        }
    }]


def build_ask_tool_schema() -> list[dict]:
    """
    Build Mistral-compatible tool schema for ask mode (multi-step reasoning).
    
    Ask mode supports read-only operations to gather context during
    investigation. This function constructs the tool schema that allows
    the model to:
    1. Read files for context (read_file)
    2. Execute safe observation commands (execute_observe_command)
    3. Signal completion and provide final answer (finish_reasoning)
    
    Returns:
        List of tool definitions in Mistral's expected format.
        Includes read_file, execute_observe_command, and finish_reasoning tools.
        
    Example:
        >>> schema = build_ask_tool_schema()
        >>> schema[0]['function']['name']
        'read_file'
        >>> schema[1]['function']['name']
        'execute_observe_command'
        >>> schema[2]['function']['name']
        'finish_reasoning'
    
    Note:
        These tools are used exclusively in ask mode for multi-step
        reasoning. Run mode uses different tools (execute_shell_command).
        The descriptions intentionally nudge the model toward `rg` for broad
        repository search and `read_file` only after a specific target exists.
    """
    return [
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": (
                    "Read a specific text file when its contents are needed to answer the question. "
                    "Use after locating the relevant file, not for broad search."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": (
                                "Relative path, home path (~/...), or absolute path within cwd."
                            )
                        },
                        "context": {
                            "type": "string",
                            "description": (
                                "Brief reason for reading this file."
                            ),
                            "optional": True
                        }
                    },
                    "required": ["path"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "execute_observe_command",
                "description": (
                    "Execute safe read-only observation commands for quick evidence gathering. "
                    "Use `rg -n --hidden --glob '!.git' <pattern> .` for content search, "
                    "`rg --files` or find for filenames, and focused git/ls/cat/head/tail/sed/awk/wc/diff commands for inspection. "
                    "Process/system diagnostics are also allowed with focused pgrep, ps, lsof, df, du, vm_stat, free, netstat, or ss commands. "
                    "No destructive commands."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": (
                                "Safe read-only command to execute. Examples: `rg -n \"pattern\" .`, `rg --files | rg \"config\"`, `git status --short`."
                            )
                        },
                        "context": {
                            "type": "string",
                            "description": (
                                "Brief reason for running this command."
                            ),
                            "optional": True
                        }
                    },
                    "required": ["command"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "finish_reasoning",
                "description": (
                    "Provide the final answer once enough evidence has been gathered. Stop early when possible."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "answer": {
                            "type": "string",
                            "description": (
                                "Final answer to the user's original question, grounded in gathered evidence."
                            )
                        }
                    },
                    "required": ["answer"]
                }
            }
        }
    ]


# Future extension point for additional tools
# TODO: Add more ask mode tools in future phases
# - search_files: Search for files matching pattern
# - grep_files: Search file contents
# - compare_files: Show differences between files
def build_extended_tool_schema(os_name: str, shell: str, include_tools: list[str]) -> list[dict]:
    """
    Build extended tool schema with additional tools beyond shell execution.

    NOT IMPLEMENTED IN PHASE 1 - placeholder for future work.
    """
    raise NotImplementedError("Extended tools not implemented in Phase 1")
