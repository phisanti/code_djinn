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


def build_command_prompt(os_fullname: str, shell: str, explain: bool = False) -> PromptBuilder:
    """
    Build a prompt for CLI command generation using the lightweight prompt builder.
    
    Args:
        os_fullname: The operating system name
        shell: The shell being used
        explain: Boolean indicating whether to include an explanation
        
    Returns:
        PromptBuilder instance configured for command generation
    """
    # XML-structured prompt (same as original but using Template format)
    template = f"""You are a CLI command expert. Generate a command that accomplishes the user's request.

    <context>
    <operating_system>{os_fullname}</operating_system>
    <shell>{shell}</shell>
    <request>$wish</request>
    <explain>{"yes" if explain else "no"}</explain>
    </context>

    <guidelines>
    - Provide a single, concise command that works on the specified OS and shell
    - Use common utilities and avoid complex scripts when possible
    - Prioritize safety (avoid destructive commands without warnings)
    - Use standard flags and options
    - Do not include explanatory text in the command itself
    </guidelines>

    <examples>
    <example>
        <request>Find all PDF files in the current directory and subdirectories</request>
        <response>
        <command>find . -name "*.pdf"</command>
        <description>Searches for PDF files in the current directory and all subdirectories.</description>
        </response>
    </example>
    <example>
        <request>Show disk usage in human-readable format</request>
        <response>
        <command>df -h</command>
        <description>Displays disk space usage with sizes in human-readable format (KB, MB, GB).</description>
        </response>
    </example>
    </examples>

    Respond with a command that fulfills the user's request. Format your response using XML tags as shown below:

    <response>
    <command>your command here</command>
    {("<description>brief explanation here</description>" if explain else "")}
    </response>
    """
    
    return PromptBuilder(template=template, input_variables=["wish"])