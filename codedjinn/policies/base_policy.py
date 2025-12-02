"""
Base policy interface for command safety evaluation.
This is the foundation of the new blocklist-only approach.
"""

from enum import Enum
from abc import ABC, abstractmethod


class PolicyDecision(Enum):
    """Policy decision for command execution."""
    ALLOW = "allow"       # Execute without confirmation
    CONFIRM = "confirm"   # Require user confirmation
    DENY = "deny"         # Block execution


class BasePolicy(ABC):
    """Abstract base class for command safety policies."""

    @abstractmethod
    def assess(self, command: str) -> PolicyDecision:
        """
        Evaluate command safety. Must be implemented by subclasses.
        
        Args:
            command: The command to evaluate
            
        Returns:
            PolicyDecision indicating how to handle the command
        """
        pass

    def get_blocklist(self) -> set:
        """
        Get the blocklist for this policy.
        
        Returns:
            Set of blocked command patterns
        """
        return set()
    
    def get_policy_name(self) -> str:
        """
        Get the name of this policy.
        
        Returns:
            Policy name string
        """
        return self.__class__.__name__.replace("Policy", "").lower()
    
    def get_description(self) -> str:
        """
        Get a description of this policy.
        
        Returns:
            Policy description string
        """
        return "Base policy class"
