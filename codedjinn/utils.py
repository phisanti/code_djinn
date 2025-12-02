from typing import Optional, Tuple
import platform
import shutil
import os


def get_os_info() -> Tuple[Optional[str], Optional[str]]:
    """
    Get information about the operating system.

    Returns:
        A tuple containing (operating system name, operating system details)
    """
    try:
        oper_sys = platform.system()
        if oper_sys == "Darwin":
            return ("MacOS", platform.platform(aliased=True, terse=True))
        elif oper_sys == "Windows":
            return (oper_sys, platform.platform(aliased=True, terse=True))
        elif oper_sys == "Linux":
            try:
                return (oper_sys, platform.freedesktop_os_release()["PRETTY_NAME"])
            except (AttributeError, KeyError, OSError):
                return (oper_sys, platform.platform(aliased=True, terse=True))
        return (None, None)
    except Exception:
        return (None, None)

def get_current_shell() -> Optional[str]:
    """
    Detect the current shell from environment variables.

    Returns:
        Shell name (e.g., 'fish', 'zsh', 'bash') or None if not detected
    """
    shell_path = os.environ.get("SHELL", "")
    if shell_path:
        # Extract shell name from path (e.g., '/usr/local/bin/fish' -> 'fish')
        shell_name = os.path.basename(shell_path)
        return shell_name
    return None


def get_shell_path(shell_name: str) -> Optional[str]:
    """
    Get the full path for a given shell.

    Args:
        shell_name: Name of the shell (e.g., 'fish', 'zsh', 'bash')

    Returns:
        Full path to the shell executable, or None if not found
    """
    return shutil.which(shell_name)
