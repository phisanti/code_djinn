"""Safe observation command executor for ask mode.

Allows the ask agent to run read-only observation commands like:
- git: git log, git diff, git status, git show, git branch
- file inspection: ls, cat, grep, rg, head, tail, find, file
- process lookup: pgrep (find PID by name), ps (with flags), pstree
- process detail: lsof (open files/sockets per process), lsof -i (network)
- system info: df, du, free, vm_stat, uname, date, wc
- network: netstat, ss (Linux socket stats)
- text processing: sed, awk, cut, sort, uniq

Process investigation workflow:
- pgrep -la hq                     (find PID of process named 'hq')
- ps aux | grep hq                 (alternative PID lookup)
- lsof -p <PID>                    (open files/sockets for a process)
- lsof -i                          (all network connections)
- netstat -an | grep <port>        (connections on a port)
- top -l 1 | head -20              (macOS batch mode)
- top -b -n 1 | head -20           (Linux batch mode)
- free -h                          (Linux memory info)
- vm_stat                          (macOS memory info)
"""

import re
import subprocess
from pathlib import Path
from typing import Optional


class ObserveExecutor:
    """Execute safe observation commands for ask mode.

    The ask agent needs to inspect the repository and local process state, but
    it must not mutate the user's machine. This executor is the boundary: only
    commands matching the read-only whitelist, plus skill-approved extras, are
    allowed to run.
    """
    
    # Max output size (100KB) to prevent context explosion
    MAX_OUTPUT_SIZE = 100_000
    
    # Max command execution time (10 seconds)
    MAX_TIMEOUT = 10.0
    
    # Whitelist of safe commands (regex patterns). The patterns are command
    # families rather than exact strings because useful observation often needs
    # flags, paths, and pipes, but each family is still intentionally read-only.
    SAFE_COMMANDS = [
        # Git commands (read-only)
        r'^git\s+(log|diff|status|show|branch|tag|remote|config|blame)',

        # File inspection
        r'^(ls|cat|grep|rg|head|tail|find|file|wc|od)\s+',
        r'^rg\s*$',
        r'^(ls|pwd|whoami|date|uname)(\s.*)?$',

        # Process observation (enhanced for memory/CPU queries)
        r'^ps\s+',  # Allow ps with any flags (aux, -eo, etc)
        r'^ps\s*$',  # Also allow bare ps
        r'^top\s+-[bln]\s+',  # Batch mode: top -b, top -l, top -n (Linux/macOS)
        r'^pgrep\s+',  # Find PID by name: pgrep hq, pgrep -la python
        r'^pgrep\s*$',  # Bare pgrep
        r'^pstree\s*',  # Process tree: pstree, pstree -p <pid>
        r'^lsof\s+',  # Open files/sockets per process: lsof -p <pid>, lsof -i
        r'^lsof\s*$',  # Bare lsof
        r'^netstat\s+',  # Network connections: netstat -an, netstat -tulnp
        r'^netstat\s*$',  # Bare netstat
        r'^ss\s+',  # Socket stats (Linux): ss -tulnp, ss -p
        r'^ss\s*$',  # Bare ss
        r'^pidstat\s+',  # Per-process CPU/IO stats (Linux)
        r'^pidstat\s*$',  # Bare pidstat

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

        # Semantic code search (read-only, requires pre-built index)
        r'^semquery\s+(search|find|overview|doctor)\s+',
        r'^semquery\s+(search|find|overview|doctor)\s*$',

        # Environment
        r'^(printenv|echo|env)\s+',
    ]
    
    def __init__(self, cwd: Optional[str] = None, extra_commands: Optional[list] = None):
        """Initialise the executor.

        Args:
            cwd: Working directory for command execution. Defaults to Path.cwd().
            extra_commands: Skill-gated command names from EXTRA_COMMANDS_REGISTRY
                to add to the per-instance whitelist beyond the class-level
                SAFE_COMMANDS. Names absent from EXTRA_COMMANDS_REGISTRY are
                silently ignored — callers (the loader) validate names before
                passing them here.
        """
        self.cwd = cwd or Path.cwd()
        if extra_commands:
            from codedjinn.skills.loader import EXTRA_COMMANDS_REGISTRY
            # Skills can widen observation capability for one request. The
            # loader validates names, but this guard keeps construction robust
            # if a stale or hand-built SkillConfig reaches the executor.
            self._extra_patterns = [
                re.compile(EXTRA_COMMANDS_REGISTRY[name])
                for name in extra_commands
                if name in EXTRA_COMMANDS_REGISTRY
            ]
        else:
            self._extra_patterns = []
    
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
            
            # Keep model context bounded. Full command output can be enormous
            # for `rg`, `find`, or `lsof`, and ask mode only needs enough
            # evidence to answer or decide what to inspect next.
            if len(output) > self.MAX_OUTPUT_SIZE:
                output = output[:self.MAX_OUTPUT_SIZE] + f"\n[... output truncated, showing first {self.MAX_OUTPUT_SIZE} bytes ...]"
            
            return output if output else "[No output]"
            
        except subprocess.TimeoutExpired:
            return f"Error: Command timed out after {self.MAX_TIMEOUT}s"
        except Exception as e:
            return f"Error: Failed to execute command - {str(e)}"
    
    def is_command_safe(self, command: str) -> bool:
        """Return whether a command belongs to an allowed read-only family.
        
        Args:
            command: Command to validate
            
        Returns:
            True if command matches whitelist, False otherwise
        """
        command_lower = command.strip().lower()

        for pattern in self.SAFE_COMMANDS:
            if re.match(pattern, command_lower):
                return True

        for pattern in self._extra_patterns:
            if pattern.match(command_lower):
                return True

        return False
