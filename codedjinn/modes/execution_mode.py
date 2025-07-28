from typing import Optional, Tuple
from .question_mode import QuestionMode
from ..core.command_executor import CommandExecutor
from ..utils import print_text


class ExecutionMode(QuestionMode):
    """
    Handles execution mode - generates commands and executes them with confirmation.
    Inherits from QuestionMode to reuse command generation logic.
    """
    
    def __init__(self, llm_instance, provider: str, os_fullname: str, shell: str, system_prompt_preferences: str = "", shell_path: str = ""):
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
        super().__init__(llm_instance, provider, os_fullname, shell, system_prompt_preferences)
        self.executor = CommandExecutor(shell, shell_path)
    
    def ask_and_execute(
        self, 
        wish: str, 
        explain: bool = False, 
        llm_verbose: bool = False,
        auto_confirm: bool = False
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
    
    def execute_with_confirmation(self, wish: str, explain: bool = False, verbose: bool = False) -> bool:
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
                    print_text("\n✓ Command completed successfully", "green")
                else:
                    print_text("\n✗ Command execution failed", "red")
            
            return success
            
        except Exception as e:
            print_text(f"Error: {e}", "red")
            return False
    
    def execute_safe_command(self, wish: str, explain: bool = False, verbose: bool = False) -> bool:
        """
        Generate and execute command - auto-execute safe commands, confirm dangerous ones.
        
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

            # Check if command is dangerous
            is_dangerous = self.executor._is_dangerous_command(command)
            
            if is_dangerous:
                print_text("\n⚠️  Potentially dangerous command detected, requiring confirmation...", "yellow")
                # Use full confirmation flow for dangerous commands
                _, description, success, _, _ = self.ask_and_execute(wish, explain, verbose)
                if verbose or description:
                    if success:
                        print_text("\n✓ Command completed successfully", "green")
                    else:
                        print_text("\n✗ Command execution failed", "red")
                return success
            else:
                # Safe command - execute directly
                success, _, _ = self.executor.execute_with_confirmation(
                    command, description if explain else None, auto_confirm=True, verbose=verbose
                )
                if verbose or description:
                    if success:
                        print_text("\n✓ Command completed successfully", "green")
                    else:
                        print_text("\n✗ Command execution failed", "red")
                return success

        except Exception as e:
            print_text(f"Error: {e}", "red")
            return False