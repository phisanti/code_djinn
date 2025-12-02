"""
Policy Engine for evaluating command safety using configurable policies.
This replaces the old over-zealous safety detection with a clean, modular approach.
"""

from typing import Optional, Dict, Type
from ..policies import BasePolicy, PolicyDecision
from ..policies import LoosePolicy, BalancedPolicy, StrictPolicy


class PolicyEngine:
    """Evaluates command safety using configurable policies."""

    # Registry of available policies
    POLICIES: Dict[str, Type[BasePolicy]] = {
        "loose": LoosePolicy,
        "balanced": BalancedPolicy,
        "strict": StrictPolicy,
    }

    def __init__(self, policy_name: str = "balanced"):
        """
        Initialize with specified policy.
        
        Args:
            policy_name: Name of policy to use (default: balanced)
            
        Raises:
            ValueError: If policy_name is not recognized
        """
        self.policy = self.load_policy(policy_name)
        self.policy_name = policy_name

    def load_policy(self, name: str) -> BasePolicy:
        """
        Load policy by name.
        
        Args:
            name: Policy name (case-insensitive)
            
        Returns:
            Policy instance
            
        Raises:
            ValueError: If policy name is not recognized
        """
        policy_class = self.POLICIES.get(name.lower())
        if not policy_class:
            available = ', '.join(self.POLICIES.keys())
            raise ValueError(
                f"Unknown policy: {name}. Available policies: {available}"
            )
        return policy_class()

    def assess_command(self, command: str) -> PolicyDecision:
        """
        Evaluate command safety using current policy.
        
        Args:
            command: Command to evaluate
            
        Returns:
            PolicyDecision indicating how to handle the command
        """
        if not command or not command.strip():
            return PolicyDecision.DENY
            
        return self.policy.assess(command)

    def switch_policy(self, policy_name: str) -> bool:
        """
        Switch to a different policy.
        
        Args:
            policy_name: Name of new policy
            
        Returns:
            True if switch successful, False otherwise
        """
        try:
            self.policy = self.load_policy(policy_name)
            self.policy_name = policy_name
            return True
        except ValueError:
            return False

    def get_available_policies(self) -> list:
        """
        List available policy names.
        
        Returns:
            List of policy names
        """
        return list(self.POLICIES.keys())

    def get_current_policy_name(self) -> str:
        """
        Get current policy name.
        
        Returns:
            Current policy name
        """
        return self.policy_name

    def get_current_policy_description(self) -> str:
        """
        Get description of current policy.
        
        Returns:
            Policy description
        """
        return self.policy.get_description()

    def get_blocklist(self) -> set:
        """
        Get blocklist for current policy.
        
        Returns:
            Set of blocked command patterns
        """
        return self.policy.get_blocklist()

    def get_policy_info(self) -> dict:
        """
        Get comprehensive information about current policy.
        
        Returns:
            Dictionary with policy information
        """
        info = {
            "name": self.policy_name,
            "description": self.get_current_policy_description(),
            "blocklist_size": len(self.get_blocklist()),
            "available_policies": self.get_available_policies(),
        }
        
        # Add confirmation patterns if available (for StrictPolicy)
        if hasattr(self.policy, 'get_confirmation_patterns'):
            info["confirmation_patterns"] = self.policy.get_confirmation_patterns()
            
        return info
