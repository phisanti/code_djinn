"""Session history management for command context."""

from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
import json
from typing import Optional


@dataclass
class CommandHistory:
    """Single command execution record."""
    command: str
    output: str
    timestamp: str
    exit_code: int


class Session:
    """
    Manages command history for conversational context.

    Stores the most recent command and output in a JSON file
    at ~/.config/codedjinn/sessions/{session_name}.json

    Only keeps the last command (not full history) to minimize
    token usage and disk space.
    """

    def __init__(self, session_name: str = "default"):
        """
        Initialize session.

        Args:
            session_name: Name of the session (default: "default")
                         Future: Could support multiple named sessions
        """
        self.session_name = session_name
        self.session_dir = Path.home() / ".config/codedjinn/sessions"
        self.session_file = self.session_dir / f"{session_name}.json"

        # Create session directory if it doesn't exist
        self.session_dir.mkdir(parents=True, exist_ok=True)

    def load_previous(self) -> Optional[CommandHistory]:
        """
        Load the previous command from session file.

        Returns:
            CommandHistory if exists, None if no previous command
        """
        if not self.session_file.exists():
            return None

        try:
            with open(self.session_file, 'r') as f:
                data = json.load(f)
                return CommandHistory(**data)
        except (json.JSONDecodeError, KeyError, TypeError):
            # Corrupted session file - ignore and start fresh
            return None

    def save(self, command: str, output: str, exit_code: int):
        """
        Save command execution to session file.

        Overwrites previous command (only keeps most recent).

        Args:
            command: The shell command that was executed
            output: The command's stdout + stderr output
            exit_code: The command's exit code (0 = success)
        """
        history = CommandHistory(
            command=command,
            output=output,
            timestamp=datetime.now().isoformat(),
            exit_code=exit_code
        )

        with open(self.session_file, 'w') as f:
            json.dump(asdict(history), f, indent=2)

    def clear(self):
        """Clear session history (start fresh)."""
        if self.session_file.exists():
            self.session_file.unlink()

    def get_context_for_prompt(self) -> Optional[dict]:
        """
        Get previous context formatted for prompt building.

        Returns:
            Dict with 'command', 'output', 'exit_code' keys, or None
        """
        prev = self.load_previous()
        if prev is None:
            return None

        return {
            'command': prev.command,
            'output': prev.output,
            'exit_code': prev.exit_code
        }
