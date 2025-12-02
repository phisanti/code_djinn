"""
Strict safety policy - maximum safety with confirmation for risky patterns.
For users who want extra protection and don't mind more confirmations.
"""

from .base_policy import BasePolicy, PolicyDecision


class StrictPolicy(BasePolicy):
    """Maximum safety - extended blocklist + confirmation for risky patterns."""

    # Extended blocklist with additional strict blocks
    BLOCKLIST = {
        # All from BalancedPolicy
        "rm -rf /", "rm -fr /",
        "mkfs", "fdisk", 
        "dd if=/dev/", "dd of=/dev/",
        "shutdown", "reboot", "halt", "poweroff",
        "kill -9 1", "killall -9",
        "sudo rm", "chmod 777", "chmod -R 777",
        ":(){ :|:& };:",

        # Additional strict blocks
        "curl | sh", "wget | sh", "curl | bash", "wget | bash",
        "eval", "python -c", "perl -e",
        "> /dev/", "< /dev/",
        "chown -r",
        "chmod +x /tmp",
    }

    # Patterns that require confirmation (not blocked, but need user approval)
    REQUIRE_CONFIRM = {
        "sudo",     # Any sudo command
        "rm -r",    # Recursive delete
        "rm -rf",   # Recursive force delete (not in root)
    }

    def assess(self, command: str) -> PolicyDecision:
        """
        Evaluate command with strict safety approach.
        
        Args:
            command: Command to evaluate
            
        Returns:
            PolicyDecision based on blocklist and confirmation patterns
        """
        cmd_lower = command.lower().strip()

        # Check blocklist first (highest priority)
        for blocked in self.BLOCKLIST:
            if blocked in cmd_lower:
                return PolicyDecision.DENY

        # Check confirmation patterns
        for pattern in self.REQUIRE_CONFIRM:
            if pattern in cmd_lower:
                return PolicyDecision.CONFIRM

        # Even in strict mode, we DON'T block pipes, redirects, or chaining
        # These are normal CLI patterns:
        # - ls | grep foo → ALLOW
        # - echo "test" > file.txt → ALLOW  
        # - npm test && npm build → ALLOW
        #
        # Only specific dangerous patterns require confirmation
        return PolicyDecision.ALLOW

    def get_blocklist(self) -> set:
        """Get the blocklist for this policy."""
        return self.BLOCKLIST.copy()
    
    def get_confirmation_patterns(self) -> set:
        """Get patterns that require confirmation."""
        return self.REQUIRE_CONFIRM.copy()
    
    def get_description(self) -> str:
        """Get policy description."""
        return "Strict safety - extended blocklist with confirmation for risky patterns"
