"""
UI output management with color-coded terminal output.
Extracted from utils.py to create clean UI layer separation.
"""

from typing import Dict, List, Optional, TextIO


# Color mapping constant (moved from utils.py)
TEXT_COLOR_MAPPING = {
    "blue": "36;1",
    "yellow": "33;1", 
    "pink": "38;5;200",
    "green": "32;1",
    "red": "31;1",
    "cyan": "96;1",  # Added for command display
    "gray": "90",    # Added for dim text
}


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


def get_color_mapping(
    items: List[str], excluded_colors: Optional[List] = None
) -> Dict[str, str]:
    """Get mapping for items to a support color."""
    colors = list(TEXT_COLOR_MAPPING.keys())
    if excluded_colors is not None:
        colors = [c for c in colors if c not in excluded_colors]
    color_mapping = {item: colors[i % len(colors)] for i, item in enumerate(items)}
    return color_mapping


class UIManager:
    """Manages colored terminal output for CodeDjinn."""
    
    def __init__(self):
        """Initialize UI manager."""
        pass
    
    def success(self, message: str) -> None:
        """Print success message in green."""
        self._print_colored(message, "green")
    
    def error(self, message: str) -> None:
        """Print error message in red."""
        self._print_colored(message, "red")
    
    def warning(self, message: str) -> None:
        """Print warning message in yellow."""
        self._print_colored(message, "yellow")
    
    def info(self, message: str) -> None:
        """Print info message in blue."""
        self._print_colored(message, "blue")
    
    def command(self, command: str) -> None:
        """Print command in cyan."""
        self._print_colored(command, "cyan")
    
    def description(self, text: str) -> None:
        """Print description text in pink."""
        self._print_colored(text, "pink")
    
    def dim(self, text: str) -> None:
        """Print dimmed text in gray."""
        self._print_colored(text, "gray")
    
    def _print_colored(
        self, 
        text: str, 
        color: str, 
        end: str = "\n", 
        file: Optional[TextIO] = None
    ) -> None:
        """
        Print text with color highlighting.

        Args:
            text: The text to print
            color: Color to use
            end: String to append at the end
            file: Optional file object to write to
        """
        try:
            colored_text = get_colored_text(text, color)
        except ValueError:
            # Fall back to plain text if color is invalid
            colored_text = text

        print(colored_text, end=end, file=file)
        if file:
            file.flush()
    
    def print_text(
        self, 
        text: str, 
        color: Optional[str] = None, 
        end: str = "", 
        file: Optional[TextIO] = None
    ) -> None:
        """
        Print text with optional highlighting (legacy compatibility).

        Args:
            text: The text to print
            color: Optional color to use
            end: String to append at the end
            file: Optional file object to write to
        """
        if color:
            self._print_colored(text, color, end, file)
        else:
            print(text, end=end, file=file)
            if file:
                file.flush()
