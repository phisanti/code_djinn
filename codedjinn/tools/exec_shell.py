import os
import subprocess
from pathlib import Path

from agno.tools import tool


@tool(
    name="exec_shell",
    description="Execute a shell command locally and return its stdout/stderr.",
    show_result=True,
    stop_after_tool_call=True,
)
def exec_shell(command: str) -> str:
    """
    Execute a shell command in the user's current working directory.

    Args:
        command: Shell command to execute.

    Returns:
        Combined stdout/stderr (and exit code on failure).
    """
    shell_executable = os.environ.get("SHELL") or "/bin/zsh"
    workdir = Path.cwd()

    completed = subprocess.run(
        command,
        shell=True,
        executable=shell_executable,
        cwd=str(workdir),
        capture_output=True,
        text=True,
    )

    stdout = completed.stdout or ""
    stderr = completed.stderr or ""

    if completed.returncode == 0:
        return stdout + stderr

    combined = stdout + stderr
    if combined and not combined.endswith("\n"):
        combined += "\n"
    combined += f"[exit code {completed.returncode}]\n"
    return combined

