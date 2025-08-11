from typing import Dict, List, Optional, TextIO, Tuple
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


# Color mapping constant
TEXT_COLOR_MAPPING = {
    "blue": "36;1",
    "yellow": "33;1",
    "pink": "38;5;200",
    "green": "32;1",
    "red": "31;1",
}


def get_color_mapping(
    items: List[str], excluded_colors: Optional[List] = None
) -> Dict[str, str]:
    """Get mapping for items to a support color."""
    colors = list(TEXT_COLOR_MAPPING.keys())
    if excluded_colors is not None:
        colors = [c for c in colors if c not in excluded_colors]
    color_mapping = {item: colors[i % len(colors)] for i, item in enumerate(items)}
    return color_mapping


def get_colored_text(text: str, color: str) -> str:
    """
    Get colored text.

    Args:
        text: The text to color
        color: The color to use

    Returns:
        Colored text string

    Raises:
        ValueError: If the specified color is not supported
    """
    if color not in TEXT_COLOR_MAPPING:
        raise ValueError(
            f"Unsupported color: {color}. Available colors: {', '.join(TEXT_COLOR_MAPPING.keys())}"
        )

    color_str = TEXT_COLOR_MAPPING[color]
    return f"\u001b[{color_str}m\033[1;3m{text}\u001b[0m"


def get_bolded_text(text: str) -> str:
    """Get bolded text."""
    return f"\033[1m{text}\033[0m"


def print_text(
    text: str, color: Optional[str] = None, end: str = "", file: Optional[TextIO] = None
) -> None:
    """
    Print text with highlighting and no end characters.

    Args:
        text: The text to print
        color: Optional color to use
        end: String to append at the end
        file: Optional file object to write to
    """
    if color:
        try:
            text_to_print = get_colored_text(text, color)
        except ValueError:
            # Fall back to plain text if color is invalid
            text_to_print = text
    else:
        text_to_print = text

    print(text_to_print, end=end, file=file)
    if file:
        file.flush()


def get_current_shell() -> Optional[str]:
    """
    Detect the current shell from environment variables.
    
    Returns:
        Shell name (e.g., 'fish', 'zsh', 'bash') or None if not detected
    """
    shell_path = os.environ.get('SHELL', '')
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
