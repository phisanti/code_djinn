"""Shell environment and command history detection.

Detects:
- Operating system and shell type (from config)
- Recent command history from shell history files
- Filters sensitive commands (passwords, tokens, API keys)
"""

from dataclasses import dataclass
from typing import List, Optional
from pathlib import Path
import re


@dataclass
class SystemContext:
    """System-level context (OS + shell)."""
    os_name: str      # From config: "macOS", "Linux", "Windows"
    shell: str        # From config: "zsh", "bash", "fish"


@dataclass
class ShellHistContext:
    """Shell command history."""
    recent_commands: List[str]  # Last N commands (chronological order, oldest to newest)


class ShellHistoryReader:
    """Read and parse shell history files."""

    HISTORY_PATHS = {
        'zsh': '~/.zsh_history',
        'bash': '~/.bash_history',
        'fish': '~/.local/share/fish/fish_history',
    }

    # Patterns to exclude (security-sensitive)
    SENSITIVE_PATTERNS = [
        r'password',
        r'token',
        r'api[_-]?key',
        r'secret',
        r'credential',
        r'export.*KEY',
        r'export.*TOKEN',
        r'export.*SECRET',
        r'export.*PASSWORD',
    ]

    def __init__(self, shell_type: str):
        self.shell_type = shell_type
        self.history_path = self._resolve_path()

    def _resolve_path(self) -> Optional[Path]:
        """Resolve shell history file path."""
        path_template = self.HISTORY_PATHS.get(self.shell_type)
        if not path_template:
            return None

        return Path(path_template).expanduser()

    def get_recent(self, count: int = 15, max_len: int = 200) -> List[str]:
        """
        Get recent commands with filtering.

        Algorithm:
        1. Read history file (method depends on shell type)
        2. Reverse list (most recent first)
        3. Filter sensitive commands
        4. Truncate long commands to max_len
        5. Take first `count` commands
        6. Reverse back to chronological order

        Returns: List of command strings (oldest to newest)
        """
        if not self.history_path:
            return []

        try:
            # Read history
            commands = self._read_history()
            if not commands:
                return []

            # Reverse to get most recent first
            commands.reverse()

            # Filter and truncate
            filtered = []
            for cmd in commands:
                # Skip sensitive commands
                if self._is_sensitive(cmd):
                    continue

                # Truncate long commands
                if len(cmd) > max_len:
                    cmd = cmd[:max_len] + "..."

                filtered.append(cmd)

                # Stop when we have enough
                if len(filtered) >= count:
                    break

            # Reverse back to chronological order (oldest to newest)
            filtered.reverse()

            return filtered

        except Exception:
            # Silent failure - history is optional
            return []

    def _read_history(self) -> List[str]:
        """Dispatch to shell-specific reader."""
        if self.shell_type == 'zsh':
            return self._read_zsh()
        elif self.shell_type == 'bash':
            return self._read_bash()
        elif self.shell_type == 'fish':
            return self._read_fish()
        return []

    def _read_bash(self) -> List[str]:
        """
        Read bash history - simple line-based format.

        Format: One command per line
        """
        if not self.history_path or not self.history_path.exists():
            return []

        try:
            text = self.history_path.read_text(errors='ignore')
            commands = [line.strip() for line in text.splitlines() if line.strip()]
            return commands
        except Exception:
            return []

    def _read_zsh(self) -> List[str]:
        """
        Read zsh history - extended format.

        Format: : 1234567890:0;command
        Extract command part after semicolon.
        """
        if not self.history_path or not self.history_path.exists():
            return []

        try:
            text = self.history_path.read_text(errors='ignore')
            commands = []

            for line in text.splitlines():
                line = line.strip()
                if not line:
                    continue

                # Extended format: `: timestamp:duration;command`
                if line.startswith(':') and ';' in line:
                    # Split on first semicolon to get command
                    parts = line.split(';', 1)
                    if len(parts) == 2:
                        cmd = parts[1].strip()
                        if cmd:
                            commands.append(cmd)
                else:
                    # Simple format: just the command
                    if line:
                        commands.append(line)

            return commands
        except Exception:
            return []

    def _read_fish(self) -> List[str]:
        """
        Read fish history - YAML-like format.

        Format:
          - cmd: git status
            when: 1234567890
          - cmd: ls -la
            when: 1234567891

        Extract lines starting with '- cmd:'
        """
        if not self.history_path or not self.history_path.exists():
            return []

        try:
            text = self.history_path.read_text(errors='ignore')
            commands = []

            for line in text.splitlines():
                line_stripped = line.strip()

                # Look for '- cmd:' lines
                if line_stripped.startswith('- cmd:'):
                    # Extract command after '- cmd:'
                    cmd = line_stripped[6:].strip()  # len('- cmd:') == 6
                    if cmd:
                        commands.append(cmd)

            return commands
        except Exception:
            return []

    def _is_sensitive(self, cmd: str) -> bool:
        """Check if command matches sensitive patterns."""
        for pattern in self.SENSITIVE_PATTERNS:
            if re.search(pattern, cmd, re.IGNORECASE):
                return True
        return False


def get_shell_context(
    os_name: str,
    shell: str,
    include_history: bool = True
) -> tuple[SystemContext, ShellHistContext]:
    """
    Get system context and shell history.

    Args from config:
        os_name: OS from config.cfg [DEFAULT] os=
        shell: Shell from config.cfg [DEFAULT] shell=
        include_history: Read command history (default: True)

    Returns:
        (SystemContext, ShellHistContext)
    """
    system_ctx = SystemContext(os_name=os_name, shell=shell)

    if include_history:
        try:
            reader = ShellHistoryReader(shell)
            commands = reader.get_recent(count=15, max_len=200)
            hist_ctx = ShellHistContext(recent_commands=commands)
        except Exception:
            hist_ctx = ShellHistContext(recent_commands=[])
    else:
        hist_ctx = ShellHistContext(recent_commands=[])

    return system_ctx, hist_ctx
