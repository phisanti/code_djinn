from typing import Optional, Tuple
from .base_mode import BaseMode
from ..core.command_executor import CommandExecutor
from ..core.prompt_builder import build_safety_assessment_prompt
from ..core.response_parser import ResponseParser
from ..utils import print_text
import re


class ExecutionMode(BaseMode):
    """
    Handles execution mode - generates commands and executes them with confirmation.
    Inherits from BaseMode to reuse command generation logic.
    """

    def __init__(
        self,
        llm_instance,
        provider: str,
        os_fullname: str,
        shell: str,
        system_prompt_preferences: str = "",
        shell_path: str = "",
    ):
        """
        Initialize execution mode.

        Args:
            llm_instance: The LLM instance to use
            provider: The LLM provider name
            os_fullname: Operating system name
            shell: Shell type
            system_prompt_preferences: Additional user preferences for prompts
            shell_path: Full path to the shell executable
        """
        super().__init__(
            llm_instance, provider, os_fullname, shell, system_prompt_preferences
        )
        self.executor = CommandExecutor(shell, shell_path)

    def ask_and_execute(
        self,
        wish: str,
        explain: bool = False,
        llm_verbose: bool = False,
        auto_confirm: bool = False,
    ) -> Tuple[str, Optional[str], bool, str, str]:
        """
        Generate and execute a command with user confirmation.

        Args:
            wish: The command the user wants to generate
            explain: Whether to include an explanation
            llm_verbose: Whether to show verbose LLM output
            auto_confirm: Skip execution confirmation (for testing)

        Returns:
            Tuple of (command, description, execution_success, stdout, stderr)

        Raises:
            RuntimeError: If command generation fails
        """
        try:
            # First generate the command (reuse parent class logic)
            command, description = self.ask(wish, explain, llm_verbose)

            # Display the generated command
            print_text("\nGenerated command:\n", "green")
            print_text(command, "blue")

            if description:
                print_text(f"\nDescription: {description}", "pink")

            # Execute with confirmation
            success, stdout, stderr = self.executor.execute_with_confirmation(
                command, description, auto_confirm, llm_verbose
            )

            return command, description, success, stdout, stderr

        except Exception as e:
            raise RuntimeError(f"Error in execution mode: {str(e)}")

    def execute_with_confirmation(
        self, wish: str, explain: bool = False, verbose: bool = False
    ) -> bool:
        """
        Generate and execute a command with full user confirmation flow.

        Args:
            wish: The user's request
            explain: Whether to show command explanation
            verbose: Whether to show verbose output

        Returns:
            True if command executed successfully, False otherwise
        """
        try:
            _, description, success, _, _ = self.ask_and_execute(wish, explain, verbose)

            # Show final status if verbose or has description
            if verbose or description:
                if success:
                    print_text("\nCommand completed successfully", "green")
                else:
                    print_text("\nCommand execution failed", "red")

            return success

        except Exception as e:
            print_text(f"Error: {e}", "red")
            return False

    def execute_safe_command(
        self, wish: str, explain: bool = False, verbose: bool = False
    ) -> bool:
        """
        Generate and execute command using AI-based safety assessment.

        Args:
            wish: The user's request
            explain: Whether to show command explanation
            verbose: Whether to show verbose output

        Returns:
            True if command executed successfully, False otherwise
        """
        try:
            # Generate command first
            command, description = self.ask(wish, explain, verbose)

            if not command:
                print_text("No command was generated.", "red")
                return False

            # Display the generated command
            print()
            print_text(f"Generated command: {command}", "blue")
            if description and explain:
                print_text(f"Description: {description}", "pink")

            # Use AI to assess command safety
            safety_level = self._assess_command_safety(command)
            
            if safety_level == "low":
                # Low risk - execute directly without confirmation
                print_text("Command assessed as low risk", "green")
                success, _, _ = self.executor.execute_with_confirmation(
                    command,
                    description if explain else None,
                    auto_confirm=True,
                    verbose=verbose,
                    quiet=True,  # Skip confirmation prompts for low risk
                )
                if verbose or description:
                    if success:
                        print_text("\nCommand completed successfully", "green")
                    else:
                        print_text("\nCommand execution failed", "red")
                return success
                
            elif safety_level == "medium":
                # Medium risk - use traditional confirmation (y/yes/enter)
                print_text("WARNING: Command assessed as medium risk", "yellow")
                success, _, _ = self.executor.execute_with_confirmation(
                    command,
                    description if explain else None,
                    auto_confirm=False,
                    verbose=verbose,
                    require_yes=False,  # Traditional confirmation
                )
                if verbose or description:
                    if success:
                        print_text("\nCommand completed successfully", "green")
                    else:
                        print_text("\nCommand execution failed", "red")
                return success
                
            elif safety_level == "high":
                # High risk - require explicit "YES" confirmation
                print_text("DANGER: Command assessed as high risk - explicit confirmation required", "red")
                success, _, _ = self.executor.execute_with_confirmation(
                    command,
                    description if explain else None,
                    auto_confirm=False,
                    verbose=verbose,
                    require_yes=True,  # Require "YES" for high risk
                )
                if verbose or description:
                    if success:
                        print_text("\nCommand completed successfully", "green")
                    else:
                        print_text("\nCommand execution failed", "red")
                return success
            else:
                # Fallback to old behavior if AI assessment fails
                print_text("WARNING: Could not assess command safety, using legacy check...", "yellow")
                is_dangerous = self.executor._is_dangerous_command(command)
                success, _, _ = self.executor.execute_with_confirmation(
                    command,
                    description if explain else None,
                    auto_confirm=not is_dangerous,
                    verbose=verbose,
                    require_yes=is_dangerous,
                )
                if verbose or description:
                    if success:
                        print_text("\nCommand completed successfully", "green")
                    else:
                        print_text("\nCommand execution failed", "red")
                return success

        except Exception as e:
            print_text(f"Error: {e}", "red")
            return False

    def _assess_command_safety(self, command: str) -> str:
        """
        Use AI to assess the safety level of a command.

        Args:
            command: The command to assess

        Returns:
            Safety level: "low", "medium", "high", or "unknown" if assessment fails
        """
        try:
            # Build safety assessment prompt
            safety_prompt_builder = build_safety_assessment_prompt(
                self.os_fullname, self.shell
            )
            
            # Format the prompt with the command
            safety_prompt = safety_prompt_builder.format(command=command)
            
            # Get AI assessment
            response = self.llm.invoke(safety_prompt)
            response_content = response.content if hasattr(response, 'content') else str(response)
            
            # Parse safety level from response
            safety_match = re.search(r'<safety>\s*(low|medium|high)\s*</safety>', response_content.lower())
            if safety_match:
                return safety_match.group(1)
            else:
                print_text("Warning: Could not parse AI safety assessment", "yellow")
                return "unknown"
                
        except Exception as e:
            print_text(f"Warning: AI safety assessment failed: {e}", "yellow")
            return "unknown"
