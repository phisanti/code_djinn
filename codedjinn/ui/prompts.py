"""
User prompt management for confirmations and interactions.
Simple implementation using prompt_toolkit.
"""

from typing import TYPE_CHECKING
from prompt_toolkit import prompt
from prompt_toolkit.shortcuts import confirm

if TYPE_CHECKING:
    from ..policies.base_policy import PolicyDecision


class PromptManager:
    """Manages user prompts and confirmations."""

    def __init__(self):
        """Initialize prompt manager."""
        pass
    
    def confirm_execution(self, command: str, policy_decision: "PolicyDecision") -> bool:
        """
        Get user confirmation for command execution.
        
        Args:
            command: The command to be executed
            policy_decision: Policy decision (ALLOW, CONFIRM, DENY)
            
        Returns:
            True if user confirms, False otherwise
        """
        from ..policies.base_policy import PolicyDecision
        
        if policy_decision == PolicyDecision.DENY:
            # Should not reach here, but handle gracefully
            return False
        
        if policy_decision == PolicyDecision.CONFIRM:
            # Strict confirmation required
            print(f"\n⚠️  Command requires explicit confirmation:")
            print(f"   {command}")
            print("\nThis command has been flagged as potentially risky.")
            
            try:
                response = prompt("Type 'YES' (all caps) to confirm execution: ")
                return response == "YES"
            except (KeyboardInterrupt, EOFError):
                return False
        
        # PolicyDecision.ALLOW - simple confirmation
        print(f"\nCommand: {command}")
        try:
            return confirm("Execute?", default=True)
        except (KeyboardInterrupt, EOFError):
            return False
    
    def display_command_preview(self, command: str, description: str = None) -> None:
        """
        Display command preview with optional description.
        
        Args:
            command: The generated command
            description: Optional description of what the command does
        """
        print(f"\nGenerated command:")
        print(f"  {command}")
        
        if description:
            print(f"\nDescription:")
            print(f"  {description}")
    
    def get_user_input(self, message: str) -> str:
        """
        Get user input.

        Args:
            message: Prompt message

        Returns:
            User input string
        """
        try:
            return prompt(message)
        except (KeyboardInterrupt, EOFError):
            return ""
    
    def get_simple_confirmation(self, message: str) -> bool:
        """
        Get simple yes/no confirmation.

        Args:
            message: Confirmation message

        Returns:
            True if confirmed, False otherwise
        """
        try:
            return confirm(message, default=False)
        except (KeyboardInterrupt, EOFError):
            return False
