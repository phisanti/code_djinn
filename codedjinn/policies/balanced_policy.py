"""
Balanced safety policy - DEFAULT policy.
Blocks common dangerous patterns while allowing normal CLI workflows.
This is the policy that FIXES the over-zealous safety bug.
"""

from .base_policy import BasePolicy, PolicyDecision


class BalancedPolicy(BasePolicy):
    """DEFAULT - Balanced safety, blocks common dangerous patterns."""

    # Expanded blocklist with common dangerous patterns
    BLOCKLIST = {
        # Filesystem destruction
        "rm -rf /", "rm -fr /",
        "mkfs", "fdisk",
        "dd if=/dev/", "dd of=/dev/",

        # System power
        "shutdown", "reboot", "halt", "poweroff",
        "init 0", "init 6",  # System shutdown/reboot

        # Critical process termination
        "kill -9 1", "killall -9",

        # Dangerous permissions
        "sudo rm", "chmod 777", "chmod -R 777",

        # Malicious patterns
        ":(){ :|:& };:",  # fork bomb
    }

    def assess(self, command: str) -> PolicyDecision:
        """
        Evaluate command with balanced safety approach.
        
        This is the CORE FIX for the over-zealous safety bug.
        
        Args:
            command: Command to evaluate
            
        Returns:
            PolicyDecision based on blocklist only
        """
        cmd_lower = command.lower().strip()

        # Check blocklist
        for blocked in self.BLOCKLIST:
            if blocked in cmd_lower:
                return PolicyDecision.DENY

        # 🎯 THE KEY FIX: Default ALLOW everything else
        # 
        # The old implementation checked for:
        # - Pipes: |
        # - Redirects: >, >>
        # - Chaining: &&, ||, ;
        # 
        # These are NORMAL CLI patterns and should NOT require confirmation!
        # 
        # Examples that are now ALLOWED without "YES" confirmation:
        # - ls -la | grep foo
        # - git log | head -10  
        # - npm test && npm build
        # - echo "test" > file.txt
        # - find . -name "*.py" | wc -l
        #
        return PolicyDecision.ALLOW

    def get_blocklist(self) -> set:
        """Get the blocklist for this policy."""
        return self.BLOCKLIST.copy()
    
    def get_description(self) -> str:
        """Get policy description."""
        return "Balanced safety - blocks dangerous commands, allows normal CLI workflows"
