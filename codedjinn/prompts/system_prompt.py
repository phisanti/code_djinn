"""Minimal system prompt builder for Mistral agent."""


def build_system_prompt(os_name: str, shell: str, cwd: str) -> str:
    """
    Build minimal system prompt for single-command generation.

    This prompt is intentionally minimal to reduce token count and
    processing time. It provides just enough context for the model
    to generate appropriate commands for the user's environment.

    Args:
        os_name: Operating system (e.g., "macOS", "Linux")
        shell: Shell type (e.g., "zsh", "bash")
        cwd: Current working directory

    Returns:
        System prompt string for Mistral API

    Design Notes:
        - Kept minimal for speed (fewer tokens = faster processing)
        - No examples (model is pre-trained on command generation)
        - No lengthy instructions (tool schema provides structure)
        - Context-aware (includes OS, shell, directory)

    TODO (Future Enhancements):
        - Add common command examples for improved accuracy
        - Add error handling instructions
        - Add safety guidelines (warn on dangerous commands)
        - Add multi-step planning instructions (Phase 2)
    """
    return f"""You are a {os_name} shell assistant using {shell}.
Current directory: {cwd}

Generate the appropriate shell command to fulfill the user's request.
Use the execute_shell_command tool to provide the command.

Be concise and generate only the necessary command."""


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


# Legacy function for backward compatibility (if needed)
def get_system_prompt() -> str:
    """
    Return a basic system prompt without context.

    NOTE: This is a legacy function. New code should use build_system_prompt()
    with proper context parameters for better results.
    """
    return """You are a shell command assistant.
Generate appropriate shell commands to fulfill user requests.
Use the execute_shell_command tool to provide commands.
Be concise and accurate."""
