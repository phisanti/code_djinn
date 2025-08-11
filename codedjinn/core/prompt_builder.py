from typing import Dict, Any
from string import Template


class PromptBuilder:
    """
    A utility class for building and formatting string prompts using templates.
    Validates required input variables and supports safe substitution.
    """

    def __init__(self, template: str, input_variables: list[str]):
        """
        Initialize the prompt builder.

        Args:
            template: The template string with placeholders
            input_variables: List of variable names expected in the template
        """
        self.template = template
        self.input_variables = input_variables
        self._string_template = Template(template)

    def format(self, **kwargs: Any) -> str:
        """
        Format the template with provided variables.

        Args:
            **kwargs: Variables to substitute in the template

        Returns:
            Formatted template string

        Raises:
            KeyError: If required variables are missing
            ValueError: If template formatting fails
        """
        # Validate that all required variables are provided
        missing_vars = set(self.input_variables) - set(kwargs.keys())
        if missing_vars:
            raise KeyError(f"Missing required variables: {missing_vars}")

        try:
            # Use safe_substitute to avoid KeyError for extra variables
            return self._string_template.safe_substitute(**kwargs)
        except Exception as e:
            raise ValueError(f"Template formatting failed: {e}")

    def get_input_variables(self) -> list[str]:
        """Get the list of input variables for this template."""
        return self.input_variables.copy()

    def get_template(self) -> str:
        """Get the raw template string."""
        return self.template


def build_command_prompt(
    os_fullname: str,
    shell: str,
    explain: bool = False,
    system_prompt_preferences: str = "",
) -> PromptBuilder:
    """
    Build a prompt for CLI command generation using the lightweight prompt builder.

    Args:
        os_fullname: The operating system name
        shell: The shell being used
        explain: Boolean indicating whether to include an explanation
        system_prompt_preferences: Additional user preferences for command generation

    Returns:
        PromptBuilder instance configured for command generation
    """
    # Build system preferences section
    system_prefs_section = ""
    if system_prompt_preferences.strip():
        system_prefs_section = f"""
    <user_preferences>
    {system_prompt_preferences.strip()}
    </user_preferences>"""

    # Build guidelines with conditional preferences line
    preferences_guideline = ""
    if system_prompt_preferences.strip():
        preferences_guideline = (
            "\n    - Follow the user preferences specified above when possible"
        )

    # XML-structured prompt
    template = f"""You are an expert terminal CLI assistant. Your only job is to generate shell commands that work on {os_fullname} with {shell}. Always respond in the exact XML format specified.

        <context>
        <os>{os_fullname}</os>
        <shell>{shell}</shell>
        <task>$wish</task>
        </context>{system_prefs_section}

        <rules>
        - Generate ONE working command for {os_fullname}/{shell}
        - Use pipes to chain commands efficiently: cmd1 | cmd2 | cmd3
        - Combine tools for powerful one-liners when appropriate
        - Avoid destructive operations without clear warnings{preferences_guideline}
        </rules>

        <examples>
        <task>list files with details</task>
        <command>ls -la</command>

        <task>find large files over 100MB</task>
        <command>find . -type f -size +100M | head -10</command>

        <task>count lines in Python files</task>
        <command>find . -name "*.py" | xargs wc -l | sort -n</command>
        </examples>

        Respond ONLY in this format:
        <response>
        <command>your_command_here</command>
        {("<description>brief_explanation</description>" if explain else "")}
        </response>"""

    return PromptBuilder(template=template, input_variables=["wish"])


def build_chat_prompt(
    os_fullname: str, shell: str, system_prompt_preferences: str = ""
) -> PromptBuilder:
    """
    Build a prompt for chat mode interactions.

    Args:
        os_fullname: The operating system name
        shell: The shell being used
        system_prompt_preferences: Additional user preferences

    Returns:
        PromptBuilder instance configured for chat mode
    """
    # Build system preferences section (consistent with build_command_prompt approach)
    system_prefs_section = ""
    if system_prompt_preferences.strip():
        system_prefs_section = f"""
    <user_preferences>
    {system_prompt_preferences.strip()}
    </user_preferences>"""

    # Build guidelines with conditional preferences line
    preferences_guideline = ""
    if system_prompt_preferences.strip():
        preferences_guideline = (
            "\n    - Follow the user preferences specified above when possible"
        )

    # Use XML-structured prompt (consistent with build_command_prompt approach)
    template = f"""You are Code Djinn, a helpful command-line assistant having a natural conversation with {os_fullname}/{shell}.

        <context>
        <os>{os_fullname}</os>
        <shell>{shell}</shell>
        <current_directory>$current_dir</current_directory>
        <conversation_history>$context</conversation_history>
        <user_input>$user_input</user_input>
        </context>{system_prefs_section}

        <rules>
        - For questions/conversation: Respond with <answer>your response</answer>
        - For command requests: Use <command>shell_command</command> with optional <description>explanation</description>
        - You can provide both answer AND command when it makes sense
        - Be conversational, consider context and current directory
        - Keep responses concise and practical
        {preferences_guideline}
        </rules>

        <examples>
        <user>What files are in this directory?</user>
        <response><answer>Let me show you the files in this directory.</answer><command>ls -la</command></response>

        <user>How are you doing today?</user>
        <response><answer>I'm doing great! Ready to help with your command-line tasks.</answer></response>

        <user>Find large log files</user>
        <response><command>find . -name "*.log" -size +10M</command><description>Find log files larger than 10MB</description></response>
        </examples>

    Respond using <answer> for conversation and/or <command>/<description> for shell commands."""

    return PromptBuilder(
        template=template, input_variables=["current_dir", "context", "user_input"]
    )
