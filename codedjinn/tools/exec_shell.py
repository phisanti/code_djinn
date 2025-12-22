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


def _is_fullscreen_tui(command: str) -> bool:
    """
    Detect full-screen TUI programs that require PTY support.

    These programs require full terminal control (cursor positioning, screen
    management) and don't produce useful text output for session context.
    They will fail or behave incorrectly without a real TTY.

    Args:
        command: Shell command string to check

    Returns:
        True if command contains a full-screen TUI program

    Example:
        >>> _is_fullscreen_tui("htop --filter=python")
        True
        >>> _is_fullscreen_tui("ps aux | grep python")
        False

    Performance:
        - Regex check: ~0.01ms
        - Executed before command runs (zero runtime overhead)
    """
    # Full-screen TUI programs that need PTY
    tui_programs = [
        r'\bhtop\b',
        r'\btop\b',
        r'\bvim?\b',      # vim or vi
        r'\bnvim\b',      # neovim
        r'\bemacs\b',
        r'\bnano\b',
        r'\bless\b',
        r'\bmore\b',
    ]

    # Combine patterns
    pattern = '|'.join(tui_programs)

    # Check if command contains TUI program
    return bool(re.search(pattern, command))


def _execute_with_streaming(args, shell: bool, cwd: Optional[Path]) -> Tuple[int, str]:
    """
    Execute command with real-time output streaming and interactive input support.

    Uses subprocess.Popen to enable:
    1. Real-time output display (not buffered until completion)
    2. Interactive input (stdin inherited from parent terminal)
    3. Output capture for session storage

    This is the simplified streaming approach that combines stderr into stdout
    for easier handling and cross-platform compatibility (no select module).

    Args:
        args: Command arguments (list for shell=False, str for shell=True)
        shell: Whether to use shell processing
        cwd: Working directory (optional)

    Returns:
        Tuple of (exit_code, captured_output)

    Stream Architecture:
        - stdout/stderr → PIPE → line-by-line read → print + capture
        - stdin → inherited from parent (user can type responses)

    Example:
        Interactive commands like 'conda update' can now prompt for y/n
        and accept user input, while Code Djinn captures the output.

    Performance:
        - Overhead: ~0.3-0.5ms vs subprocess.run (negligible)
        - Enables interactivity with minimal cost
    """
    # Start process with pipes for output but inherited stdin
    process = subprocess.Popen(
        args,
        shell=shell,
        cwd=str(cwd) if cwd else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,  # Combine stderr into stdout (simplified approach)
        stdin=None,  # Inherit from parent - KEY for interactivity
        text=True,
        bufsize=1  # Line buffered for responsive streaming
    )

    # Capture output while streaming to terminal
    output_lines = []

    # Stream line by line
    for line in process.stdout:
        # Print to terminal immediately (real-time display)
        print(line, end='')
        sys.stdout.flush()
        # Capture for session storage
        output_lines.append(line)

    # Wait for process to complete
    exit_code = process.wait()

    return exit_code, ''.join(output_lines)


def execute_command(command: str, cwd: Optional[Path] = None, optimize: bool = True) -> Tuple[int, str]:
    """
    Execute shell command with real-time streaming and interactive input support.

    NEW: Now uses subprocess.Popen for real-time output streaming and stdin
    inheritance, enabling interactive commands (conda update, npm install, etc.)
    to work properly with user prompts.

    Optimized execution path:
    - Simple commands (no shell metacharacters): Use shell=False (~10-30ms faster)
    - Complex commands (pipes, redirects, etc.): Use shell=True (required)

    The output is both:
    1. Streamed to terminal in real-time (user sees it immediately)
    2. Captured and returned (for session storage)

    Interactive commands are supported:
    - stdin inherited from parent terminal
    - User can respond to prompts (y/n, passwords, etc.)
    - Progress bars and spinners display correctly

    Args:
        command: Shell command string to execute
        cwd: Working directory (defaults to current directory)
        optimize: Enable shell=False optimization for simple commands (default: True)

    Returns:
        Tuple of (exit_code, output)
        - exit_code: Command's exit code (0 = success)
        - output: Combined stdout + stderr output

    Performance:
        - Streaming overhead: ~0.3-0.5ms (negligible)
        - shell=False (simple commands): ~10-30ms faster than shell=True
        - Detection overhead: ~0.01ms (negligible)
        - Best for: ls, pwd, echo, cat, etc.
        - Requires shell=True: pipes, redirects, variables, globs

    Design Notes:
        - Real-time streaming via subprocess.Popen
        - Interactive input via stdin inheritance
        - Automatic optimization via is_simple_command()
        - Falls back to shell=True for safety

    Security Note:
        This executes arbitrary commands without validation.
        Safety checks are handled by core/policy.py before execution.
    """
    # Check for unsupported full-screen TUI commands
    if _is_fullscreen_tui(command):
        error_msg = (
            f"Warning: Command '{command}' uses a full-screen TUI program.\n"
            "Full TUI commands are not supported yet.\n"
            "Please use text-output alternatives (e.g., 'ps aux | grep ...' instead of 'htop')."
        )
        print(error_msg, file=sys.stderr)
        return 1, error_msg

    # Optimize simple commands to avoid shell spawn
    if optimize and is_simple_command(command):
        # Simple command - use shell=False (faster)
        try:
            # Parse command into arguments
            args = shlex.split(command)
            # Use streaming execution for real-time output and interactivity
            return _execute_with_streaming(args, shell=False, cwd=cwd)
        except (ValueError, FileNotFoundError):
            # Parsing failed or command not found - fall back to shell=True
            pass

    # Complex command or fallback - use shell=True (required)
    # Use streaming execution for real-time output and interactivity
    return _execute_with_streaming(command, shell=True, cwd=cwd)
