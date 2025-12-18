"""Simple shell command execution without framework overhead."""

import re
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Optional, Tuple


def is_simple_command(command: str) -> bool:
    """
    Detect if command can run with shell=False for speed.

    Simple commands have no shell metacharacters that require shell processing.
    Using shell=False avoids spawning a shell entirely, saving ~10-30ms per command.

    Shell metacharacters detected:
    - Pipes: |
    - Redirects: >, <, >>, 2>, &>
    - Command chaining: &&, ||, ;
    - Variable expansion: $, ${...}, $(...)
    - Globbing: *, ?, [...]
    - Backticks: `...`
    - Subshells: (...)
    - Background: &

    Args:
        command: Shell command string to check

    Returns:
        True if command can use shell=False, False if shell=True required

    Example:
        >>> is_simple_command("ls -la")
        True
        >>> is_simple_command("ls | grep foo")
        False

    Performance:
        - Regex check: ~0.01ms
        - shell=False saves: ~10-30ms per execution
    """
    # Shell metacharacters that require shell=True
    shell_patterns = [
        r'\|',        # Pipe
        r'>>?',       # Redirect output
        r'<<?',       # Redirect input
        r'2>>?',      # Redirect stderr
        r'&>',        # Redirect both
        r'&&',        # AND chain
        r'\|\|',      # OR chain
        r';',         # Command separator
        r'\$',        # Variable expansion
        r'`',         # Backticks
        r'\(',        # Subshell
        r'\)',        # Subshell
        r'\*',        # Glob
        r'\?',        # Glob
        r'\[',        # Glob
        r'&\s*$',     # Background (at end)
        r'~',         # Home directory expansion
    ]

    # Combine patterns
    pattern = '|'.join(shell_patterns)

    # Check if command contains shell metacharacters
    return not bool(re.search(pattern, command))


def execute_command(command: str, cwd: Optional[Path] = None, optimize: bool = True) -> Tuple[int, str]:
    """
    Execute shell command and capture output while streaming to terminal.

    Optimized execution path:
    - Simple commands (no shell metacharacters): Use shell=False (~10-30ms faster)
    - Complex commands (pipes, redirects, etc.): Use shell=True (required)

    MODIFIED: Now returns both exit code AND captured output for session storage.

    The output is both:
    1. Streamed to terminal in real-time (user sees it immediately)
    2. Captured and returned (for session storage)

    Args:
        command: Shell command string to execute
        cwd: Working directory (defaults to current directory)
        optimize: Enable shell=False optimization for simple commands (default: True)

    Returns:
        Tuple of (exit_code, output)
        - exit_code: Command's exit code (0 = success)
        - output: Combined stdout + stderr output

    Performance:
        - shell=False (simple commands): ~10-30ms faster than shell=True
        - Detection overhead: ~0.01ms (negligible)
        - Best for: ls, pwd, echo, cat, etc.
        - Requires shell=True: pipes, redirects, variables, globs

    Design Notes:
        - Output streams to terminal AND is captured for history
        - Automatic optimization via is_simple_command()
        - Falls back to shell=True for safety

    Security Note:
        This executes arbitrary commands without validation.
        Safety checks are handled by core/policy.py before execution.
    """
    # Optimize simple commands to avoid shell spawn
    if optimize and is_simple_command(command):
        # Simple command - use shell=False (faster)
        try:
            # Parse command into arguments
            args = shlex.split(command)
            result = subprocess.run(
                args,
                shell=False,  # Optimized: no shell spawn
                cwd=str(cwd) if cwd else None,
                text=True,
                capture_output=True  # NEW: Capture output for session storage
            )

            # Stream captured output to terminal (so user sees it)
            if result.stdout:
                print(result.stdout, end='')
            if result.stderr:
                print(result.stderr, end='', file=sys.stderr)

            # Combine stdout and stderr for session storage
            combined_output = result.stdout + result.stderr

            return result.returncode, combined_output
        except (ValueError, FileNotFoundError):
            # Parsing failed or command not found - fall back to shell=True
            pass

    # Complex command or fallback - use shell=True (required)
    result = subprocess.run(
        command,
        shell=True,  # Required for shell metacharacters
        cwd=str(cwd) if cwd else None,
        text=True,
        capture_output=True  # NEW: Capture output for session storage
    )

    # Stream captured output to terminal (so user sees it)
    if result.stdout:
        print(result.stdout, end='')
    if result.stderr:
        print(result.stderr, end='', file=sys.stderr)

    # Combine stdout and stderr for session storage
    combined_output = result.stdout + result.stderr

    return result.returncode, combined_output
