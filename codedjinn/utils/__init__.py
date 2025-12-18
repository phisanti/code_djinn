"""Utilities for Code Djinn.

This package intentionally provides a small "legacy" surface area for backward
compatibility with older imports (and the current test suite).
"""

from __future__ import annotations

import platform
import shutil
from typing import Optional, Tuple, TextIO

TEXT_COLOR_MAPPING = {
    "blue": "36;1",
    "yellow": "33;1",
    "pink": "35;1",
    "green": "32;1",
    "red": "31;1",
}


def get_os_info() -> Tuple[Optional[str], Optional[str]]:
    """
    Return (os_family, os_fullname) or (None, None) if unknown/error.

    Notes:
    - Kept for compatibility with older `codedjinn.utils` imports.
    - The interactive config wizard uses `codedjinn.utils.detection.detect_os`.
    """

    try:
        system = platform.system()

        if system == "Darwin":
            return "MacOS", platform.platform()

        if system == "Linux":
            try:
                pretty = platform.freedesktop_os_release().get("PRETTY_NAME")
                if pretty:
                    return "Linux", pretty
            except Exception:
                pass
            return "Linux", platform.platform()

        if system == "Windows":
            return "Windows", platform.platform()

        return None, None
    except Exception:
        return None, None


def get_shell_path(shell_name: str) -> Optional[str]:
    """Return the full path to `shell_name`, or None if not found."""

    return shutil.which(shell_name)


def get_colored_text(text: str, color: str) -> str:
    """Wrap `text` in ANSI color codes using `TEXT_COLOR_MAPPING`."""

    if color not in TEXT_COLOR_MAPPING:
        raise ValueError(f"Unsupported color: {color}")
    code = TEXT_COLOR_MAPPING[color]
    return f"\u001b[{code}m{text}\u001b[0m"


def print_text(
    text: str,
    *,
    color: Optional[str] = None,
    end: str = "",
    file: Optional[TextIO] = None,
) -> None:
    """
    Print text with optional ANSI color.

    If `color` is invalid, prints plain text (compat behavior expected by tests).
    """

    if color:
        try:
            text = get_colored_text(text, color)
        except ValueError:
            pass

    print(text, end=end, file=file)
    if file is not None and hasattr(file, "flush"):
        file.flush()


__all__ = [
    "TEXT_COLOR_MAPPING",
    "get_colored_text",
    "get_os_info",
    "get_shell_path",
    "print_text",
]
