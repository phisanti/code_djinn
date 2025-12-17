"""Abstract agent interface for command generation."""

from abc import ABC, abstractmethod
from typing import Optional


class Agent(ABC):
    """
    Abstract base class for LLM-based command generation agents.

    Each provider (Mistral, Gemini, etc.) implements this interface
    to provide consistent command generation capabilities.
    """

    @abstractmethod
    def generate_command(self, query: str, context: dict) -> str:
        """
        Generate a single shell command from user's natural language query.

        Args:
            query: User's natural language request (e.g., "list git branches")
            context: Execution context containing:
                - cwd: Current working directory (Path)
                - os_name: Operating system (str, e.g., "macOS", "Linux")
                - shell: Shell type (str, e.g., "zsh", "bash")

        Returns:
            Shell command string ready for execution

        Raises:
            Exception: If command generation fails (API error, malformed response, etc.)

        Note:
            This method should be fast (<500ms target) for single-command requests.
        """
        pass

    @abstractmethod
    def generate_with_steps(self, query: str, context: dict, max_steps: int) -> list[str]:
        """
        Generate multiple commands for multi-step execution (agentic workflow).

        NOTE: NOT IMPLEMENTED IN PHASE 1.
        This is a placeholder for future multi-step agentic capabilities.

        Args:
            query: User's natural language request
            context: Execution context (same as generate_command)
            max_steps: Maximum number of steps/commands to generate

        Returns:
            List of shell command strings to execute sequentially

        Raises:
            NotImplementedError: Phase 1 does not support multi-step
        """
        pass
