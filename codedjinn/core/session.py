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


@dataclass
class CommandExchange:
    """Single command-response exchange for conversation history."""
    command: str
    output: str
    exit_code: int
    timestamp: str


class Session:
    """
    Manages command history for conversational context.

    Stores two types of history:
    1. Last command (for immediate context)
    2. Conversation history (last N exchanges for multi-command workflows)

    Files:
    - ~/.config/codedjinn/sessions/{session_name}.json - Last command
    - ~/.config/codedjinn/sessions/{session_name}_history.json - Full history (last N exchanges)

    Phase 4 enhancement: Conversation history enables ask mode to reference
    multiple previous commands for better multi-step reasoning.
    """

    MAX_HISTORY_EXCHANGES = 5  # Keep last 5 command-response pairs

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
        self.history_file = self.session_dir / f"{session_name}_history.json"

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

        Overwrites previous command (only keeps most recent) and adds to conversation history.

        Args:
            command: The shell command that was executed
            output: The command's stdout + stderr output
            exit_code: The command's exit code (0 = success)
        """
        timestamp = datetime.now().isoformat()
        
        # Save as last command (overwrites previous)
        history = CommandHistory(
            command=command,
            output=output,
            timestamp=timestamp,
            exit_code=exit_code
        )

        with open(self.session_file, 'w') as f:
            json.dump(asdict(history), f, indent=2)
        
        # Add to conversation history (keeps last N exchanges)
        self.add_to_history(command, output, exit_code)

    def add_to_history(self, command: str, output: str, exit_code: int):
        """
        Add a command execution to conversation history.

        Keeps the last MAX_HISTORY_EXCHANGES exchanges, trimming oldest if needed.

        Args:
            command: The shell command that was executed
            output: The command's stdout + stderr output
            exit_code: The command's exit code
        """
        exchanges = self.load_history()
        
        # Add new exchange
        exchange = CommandExchange(
            command=command,
            output=output,
            exit_code=exit_code,
            timestamp=datetime.now().isoformat()
        )
        exchanges.append(exchange)
        
        # Trim to MAX_HISTORY_EXCHANGES
        if len(exchanges) > self.MAX_HISTORY_EXCHANGES:
            exchanges = exchanges[-self.MAX_HISTORY_EXCHANGES:]
        
        # Save
        with open(self.history_file, 'w') as f:
            json.dump([asdict(ex) for ex in exchanges], f, indent=2)

    def load_history(self) -> list:
        """
        Load conversation history.

        Returns:
            List of CommandExchange objects (empty list if no history)
        """
        if not self.history_file.exists():
            return []
        
        try:
            with open(self.history_file, 'r') as f:
                data = json.load(f)
                return [CommandExchange(**item) for item in data]
        except (json.JSONDecodeError, KeyError, TypeError):
            # Corrupted history file - start fresh
            return []

    def get_conversation_history(self) -> Optional[list[dict]]:
        """
        Get conversation history formatted for prompts.

        Returns:
            List of dicts with 'command', 'output', 'exit_code' keys, or None if no history.
            Output is trimmed to 200 chars to maintain token budget.
        """
        exchanges = self.load_history()
        if not exchanges:
            return None
        
        return [
            {
                'command': ex.command,
                'output': ex.output[:200] if len(ex.output) > 200 else ex.output,
                'exit_code': ex.exit_code
            }
            for ex in exchanges
        ]

    def clear(self):
        """Clear session history (start fresh)."""
        if self.session_file.exists():
            self.session_file.unlink()
        if self.history_file.exists():
            self.history_file.unlink()

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
