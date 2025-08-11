from typing import Optional, Tuple
from ..core.prompt_builder import build_command_prompt
from ..core.response_parser import ResponseParser
from ..providers.parameter_manager import ParameterManager
from ..utils import print_text


class BaseMode:
    """
    Base class for all Code Djinn modes.
    Provides common functionality for command generation.
    """

    def __init__(
        self,
        llm_instance,
        provider: str,
        os_fullname: str,
        shell: str,
        system_prompt_preferences: str = "",
    ):
        """
        Initialize base mode.

        Args:
            llm_instance: The LLM instance to use
            provider: The LLM provider name
            os_fullname: Operating system name
            shell: Shell type
            system_prompt_preferences: Additional user preferences for prompts
        """
        self.llm = llm_instance
        self.provider = provider
        self.os_fullname = os_fullname
        self.shell = shell
        self.system_prompt_preferences = system_prompt_preferences
        self.parameter_manager = ParameterManager()

    def ask(
        self, wish: str, explain: bool = False, llm_verbose: bool = False
    ) -> Tuple[str, Optional[str]]:
        """
        Generate a command using the LLM without executing it.

        Args:
            wish: The command the user wants to generate
            explain: Whether to include an explanation
            llm_verbose: Whether to show verbose LLM output

        Returns:
            Tuple of (command, description)

        Raises:
            RuntimeError: If command generation fails
        """
        try:
            # Apply provider-specific parameters
            self.parameter_manager.apply_parameters(self.llm, self.provider, explain)

            # Build prompt
            prompt_builder = build_command_prompt(
                self.os_fullname, self.shell, explain, self.system_prompt_preferences
            )
            prompt_text = prompt_builder.format(wish=wish)

            if llm_verbose:
                print_text("\nSending prompt to LLM:", "yellow")
                print_text(prompt_text, "blue")

            # Get response from LLM
            response = self._invoke_llm({"wish": wish}, prompt_builder)

            # Extract content from response
            if hasattr(response, "content"):
                response_text = response.content
            else:
                response_text = str(response)

            # Parse response
            command, description = ResponseParser.parse_command_response(response_text)

            return command, description

        except Exception as e:
            raise RuntimeError(f"Error generating command: {str(e)}")

    def test_prompt(self, wish: str, explain: bool = False) -> str:
        """
        Build and return the formatted prompt for testing.

        Args:
            wish: The command the user wants to generate
            explain: Whether to include an explanation

        Returns:
            The formatted prompt string
        """
        prompt_builder = build_command_prompt(
            self.os_fullname, self.shell, explain, self.system_prompt_preferences
        )
        return prompt_builder.format(wish=wish)

    def _invoke_llm(self, inputs: dict, prompt_builder) -> str:
        """
        Invoke the LLM with the given inputs.

        Args:
            inputs: Input variables for the prompt
            prompt_builder: The prompt builder instance

        Returns:
            LLM response
        """
        # Format the prompt
        prompt_text = prompt_builder.format(**inputs)

        # Different invocation methods for different LLM types
        if hasattr(self.llm, "invoke"):
            # For chat models
            return self.llm.invoke(prompt_text)
        elif hasattr(self.llm, "__call__"):
            # For completion models
            return self.llm(prompt_text)
        else:
            raise RuntimeError("LLM instance doesn't support invoke or call methods")
