"""Simple shell command execution without framework overhead."""

import subprocess
from pathlib import Path
from typing import Optional


def execute_command(command: str, cwd: Optional[Path] = None) -> int:
    """
    Execute shell command and stream output directly to terminal.

    This is kept intentionally simple for Phase 1 - just execute and
    stream output. No safety checks, no output capture, no fancy features.

    Args:
        command: Shell command string to execute
        cwd: Working directory (defaults to current directory)

    Returns:
        Exit code from the command (0 = success, non-zero = error)

    Design Notes:
        - Uses shell=True for simplicity (supports pipes, redirects, etc.)
        - Output streams directly to terminal (not captured)
        - No input provided (stdin=DEVNULL would be added for isolation)

    TODO (Future Optimizations - marked for later):
        - Add shell=False optimization for simple commands (no metacharacters)
        - Add dangerous command detection (rm -rf, etc.)
        - Add user confirmation prompts for risky operations
        - Add command sandboxing/isolation
        - Add timeout support for long-running commands
        - Add signal handling (SIGINT, SIGTERM)

    Security Note:
        This executes arbitrary commands without validation. This is
        acceptable for Phase 1 since the developer is the only user.
        Production use MUST add safety checks before deployment.
    """
    result = subprocess.run(
        command,
        shell=True,  # TODO: Optimize with shell=False for simple commands
        cwd=str(cwd) if cwd else None,
        text=True
        # NOTE: Not using capture_output=True - let output stream to terminal
        # NOTE: Not using stdin=DEVNULL yet - add in optimization pass
    )

    return result.returncode


# Future optimization: detect simple commands that don't need shell=True
def is_simple_command(command: str) -> bool:
    """
    Detect if command can run with shell=False for speed.

    NOT IMPLEMENTED IN PHASE 1 - placeholder for optimization.

    Simple commands have no shell metacharacters:
    - No pipes: |
    - No redirects: >, <, >>
    - No command chaining: &&, ||, ;
    - No variable expansion: $, $(...)
    - No globbing: *, ?, [...]
    - No backticks: `...`

    Example:
        >>> is_simple_command("ls -la")
        True
        >>> is_simple_command("ls | grep foo")
        False

    If simple, can run as: subprocess.run(shlex.split(command), ...)
    which avoids spawning a shell entirely (faster by ~50-100ms).
    """
    raise NotImplementedError("Shell optimization not implemented in Phase 1")
