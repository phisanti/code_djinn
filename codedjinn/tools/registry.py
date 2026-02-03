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
    """
    return [
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": (
                    "Read file contents to gather context for answering questions. "
                    "Use this to understand code, configuration, or other files relevant to your analysis. "
                    "Can read files in current directory or home directory (~/)."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": (
                                "Path to file to read. "
                                "Use relative paths (./file.py), home paths (~/Documents/file.txt), "
                                "or absolute paths within cwd."
                            )
                        },
                        "context": {
                            "type": "string",
                            "description": (
                                "Why you're reading this file - what context are you gathering? "
                                "Example: 'to understand database schema' or 'to see error handling'"
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
                    "Execute safe read-only observation commands for gathering context. "
                    "Allowed commands include: "
                    "git (log/diff/status), ls, cat, grep, find, diff, "
                    "ps (with flags like 'aux', '-m', '-eo'), top (batch mode: -l/-b/-n), "
                    "df, du, free, vm_stat, and other system inspection tools. "
                    "Use this to inspect processes, memory usage, system state, version control history, or file listings. "
                    "Examples: "
                    "macOS: 'ps aux -m | head -10' (sorted by memory), 'top -l 1 | head -20'; "
                    "Linux: 'ps aux --sort=-%mem | head -10', 'top -b -n 1 | head -20', 'free -h'. "
                    "No destructive commands allowed."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": (
                                "Safe observation command to execute. "
                                "Examples: 'git log --oneline -5', 'ls -la src/', 'grep -r \"pattern\" .' "
                            )
                        },
                        "context": {
                            "type": "string",
                            "description": (
                                "Why you're running this command - what context do you need? "
                                "Example: 'to see recent changes in the repository'"
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
                    "Provide your final answer and complete the reasoning process. "
                    "Use this when you have gathered enough information to answer the question. "
                    "You can stop early if you've reached a conclusion before using all available steps."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "answer": {
                            "type": "string",
                            "description": (
                                "Your final answer to the user's original question. "
                                "Should be comprehensive and grounded in the evidence you gathered."
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
