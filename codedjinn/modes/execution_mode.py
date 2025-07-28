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
    
    def execute_command_directly(
        self, 
        command: str, 
        description: Optional[str] = None,
        auto_confirm: bool = False,
        verbose: bool = False
    ) -> Tuple[bool, str, str]:
        """
        Execute a command directly without generating it first.
        
        Args:
            command: The command to execute
            description: Optional description of the command
            auto_confirm: Skip execution confirmation
            verbose: Whether to show verbose status messages
            
        Returns:
            Tuple of (success, stdout, stderr)
        """
        return self.executor.execute_with_confirmation(command, description, auto_confirm, verbose)