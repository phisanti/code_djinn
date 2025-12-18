"""
OS and Shell Detection Utilities

Auto-detection helpers for system configuration.
Only imported during configuration setup, not runtime.
"""

import os
import platform
import shutil
from typing import Optional, Tuple


def detect_os() -> Tuple[str, str]:
    """
    Auto-detect OS family and full name.

    Returns:
        tuple: (os_family, os_fullname)
            - os_family: Short name (MacOS, Linux, Windows)
            - os_fullname: Descriptive name with version
    """
    system = platform.system()

    if system == "Darwin":
        mac_version = platform.mac_ver()[0]
        return "MacOS", f"macOS {mac_version}"
    elif system == "Linux":
        return "Linux", f"Linux {platform.release()}"
    elif system == "Windows":
        return "Windows", f"Windows {platform.release()}"

    # Fallback for unknown systems
    return system, platform.platform()


def detect_shell() -> str:
    """
    Auto-detect shell from environment.

    Returns:
        str: Shell name (zsh, bash, fish, etc.)
    """
    shell_path = os.environ.get("SHELL", "")

    if "zsh" in shell_path:
        return "zsh"
    elif "bash" in shell_path:
        return "bash"
    elif "fish" in shell_path:
        return "fish"
    elif "tcsh" in shell_path:
        return "tcsh"
    elif "ksh" in shell_path:
        return "ksh"

    # Fallback to bash
    return "bash"


def get_shell_path(shell_name: str) -> str:
    """
    Get full path to shell executable.

    Args:
        shell_name: Name of the shell (e.g., "bash", "zsh")

    Returns:
        str: Full path to shell executable, or empty string if not found
    """
    path = shutil.which(shell_name)
    return path or ""
