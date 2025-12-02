"""
Lightweight chat input handler with enhanced terminal support.
Provides proper handling of special keys (arrows, backspace) and command history.
"""

from prompt_toolkit import prompt
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.key_binding import KeyBindings
from typing import Optional


class ChatPrompt:
    """Lightweight chat input handler with history and proper terminal support."""
    
    def __init__(self):
        self.history = InMemoryHistory()
        self.bindings = self._setup_key_bindings()
    
    def _setup_key_bindings(self) -> KeyBindings:
        """Setup basic key bindings for enhanced UX."""
        kb = KeyBindings()
        
        @kb.add('c-c')  # Ctrl+C
        def _(event):
            """Handle Ctrl+C gracefully."""
            event.app.exit(exception=KeyboardInterrupt)
            
        return kb
    
    def get_input(self, message: str) -> str:
        """Get user input with history navigation (Up/Down arrows work automatically)."""
        try:
            return prompt(
                message, 
                history=self.history,
                key_bindings=self.bindings
            ).strip()
        except KeyboardInterrupt:
            raise
        except EOFError:
            raise
    
    def get_confirmation(self, message: str, dangerous: bool = False) -> str:
        """Get confirmation input without history (for safety)."""
        prefix = "WARNING: " if dangerous else ""
        try:
            return prompt(f"{prefix}{message}").strip()
        except KeyboardInterrupt:
            raise
        except EOFError:
            raise