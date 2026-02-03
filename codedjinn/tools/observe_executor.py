"""Safe observation command executor for ask mode.

Allows the ask agent to run read-only observation commands like:
- git: git log, git diff, git status, git show, git branch
- file inspection: ls, cat, grep, head, tail, find, file
- process observation: ps (with flags), top (batch mode)
- system info: df, du, free, vm_stat, uname, date, wc
- text processing: sed, awk, cut, sort, uniq

Enhanced for process/memory queries:
- ps aux --sort=-%mem | head -10  (top memory consumers)
- ps -eo pid,ppid,cmd,%mem,%cpu --sort=-%mem  (custom format)
- top -l 1 | head -20  (macOS batch mode)
- top -b -n 1 | head -20  (Linux batch mode)
- free -h  (Linux memory info)
- vm_stat  (macOS memory info)
"""

import re
import subprocess
from pathlib import Path
from typing import Optional


class ObserveExecutor:
    """Execute safe observation commands for ask mode.
    
    Uses a whitelist of safe command patterns to prevent abuse
    while allowing useful inspection commands.
    """
    
    # Max output size (100KB) to prevent context explosion
    MAX_OUTPUT_SIZE = 100_000
    
    # Max command execution time (10 seconds)
    MAX_TIMEOUT = 10.0
    
    # Whitelist of safe commands (regex patterns)
    SAFE_COMMANDS = [
        # Git commands (read-only)
        r'^git\s+(log|diff|status|show|branch|tag|remote|config|blame)',

        # File inspection
        r'^(ls|cat|grep|head|tail|find|file|wc|od)\s+',
        r'^(ls|pwd|whoami|date|uname)\s*$',

        # Process observation (enhanced for memory/CPU queries)
        r'^ps\s+',  # Allow ps with any flags (aux, -eo, etc)
        r'^ps\s*$',  # Also allow bare ps
        r'^top\s+-[bln]\s+',  # Batch mode: top -b, top -l, top -n (Linux/macOS)

        # Memory and system info
        r'^(df|du)\s+',  # Disk usage with args
        r'^(df|du)\s*$',  # Disk usage without args
        r'^free\s+',  # Memory info (Linux)
        r'^free\s*$',  # Memory info without args
        r'^vm_stat\s*$',  # Memory info (macOS)

        # Tree/structure inspection
        r'^tree\s+',

        # Text processing
        r'^(sed|awk|cut|sort|uniq)\s+',

        # File comparison
        r'^diff\s+',

        # Search
        r'^locate\s+',

        # Environment
        r'^(printenv|echo|env)\s+',
    ]
    
    def __init__(self, cwd: Optional[str] = None):
        """Initialize executor.
        
        Args:
            cwd: Current working directory for command execution
        """
        self.cwd = cwd or Path.cwd()
    
    def execute_observe_command(self, command: str) -> str:
        """Execute a safe observation command.
        
        Args:
            command: Command to execute (must pass whitelist)
            
        Returns:
            Command output as string, or error message
            
        Examples:
            >>> executor = ObserveExecutor()
            >>> output = executor.execute_observe_command('git log --oneline -5')
            >>> len(output) > 0
            True
        """
        # Validate command
        if not command or len(command) > 1000:
            return f"Error: Invalid command - command too long or empty"
        
        if not self.is_command_safe(command):
            return f"Error: Command not allowed in ask mode - {command}"
        
        # Execute command
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=str(self.cwd),
                capture_output=True,
                text=True,
                timeout=self.MAX_TIMEOUT
            )
            
            # Combine stdout and stderr
            output = result.stdout
            if result.stderr:
                output = output + "\n[stderr]\n" + result.stderr
            
            # Truncate if too large
            if len(output) > self.MAX_OUTPUT_SIZE:
                output = output[:self.MAX_OUTPUT_SIZE] + f"\n[... output truncated, showing first {self.MAX_OUTPUT_SIZE} bytes ...]"
            
            return output if output else "[No output]"
            
        except subprocess.TimeoutExpired:
            return f"Error: Command timed out after {self.MAX_TIMEOUT}s"
        except Exception as e:
            return f"Error: Failed to execute command - {str(e)}"
    
    def is_command_safe(self, command: str) -> bool:
        """Check if command is safe to execute.
        
        Args:
            command: Command to validate
            
        Returns:
            True if command matches whitelist, False otherwise
        """
        command_lower = command.strip().lower()
        
        # Check against whitelist patterns
        for pattern in self.SAFE_COMMANDS:
            if re.match(pattern, command_lower):
                return True
        
        return False
