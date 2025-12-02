"""
Loose safety policy - minimal restrictions.
Only blocks truly destructive commands that could cause system damage.
"""

from .base_policy import BasePolicy, PolicyDecision


class LoosePolicy(BasePolicy):
    """Minimal restrictions - only truly destructive commands blocked."""

    # Only the most dangerous commands that could cause irreversible system damage
    BLOCKLIST = {
        "rm -rf /",
        "rm -fr /", 
        "mkfs",
        "dd if=/dev/",
        "dd of=/dev/",
        ":(){ :|:& };:",  # fork bomb
    }

    def assess(self, command: str) -> PolicyDecision:
        """
        Evaluate command with minimal restrictions.
        
        Args:
            command: Command to evaluate
            
        Returns:
            PolicyDecision.DENY for blocklisted commands, ALLOW for everything else
        """
        cmd_lower = command.lower().strip()

        # Check blocklist - only truly dangerous commands
        for blocked in self.BLOCKLIST:
            if blocked in cmd_lower:
                return PolicyDecision.DENY

        # Default: ALLOW everything else
        # This is the KEY difference from old implementation:
        # No checks for pipes (|), redirects (>, >>), or chaining (&&, ||, ;)!
        return PolicyDecision.ALLOW

    def get_blocklist(self) -> set:
        """Get the blocklist for this policy."""
        return self.BLOCKLIST.copy()
    
    def get_description(self) -> str:
        """Get policy description."""
        return "Minimal safety - only blocks system-destroying commands"
