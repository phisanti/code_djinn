"""File context source - user-added files for deep analysis.

Allows users to add files to persistent context that gets included
in all subsequent prompts until expiration. Files are stored as
metadata on disk, with content read on-demand (or cached in daemon).

Storage: ~/.local/share/codedjinn/context/files.json
"""

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import List, Optional, Dict, Any
import json
import time
import os


@dataclass
class FileEntry:
    """Single file entry in context."""
    path: str              # Absolute path to file
    display_path: str      # Relative path for display
    added_at: float        # Unix timestamp when added
    expires_at: float      # Unix timestamp when expires
    size_bytes: int        # File size in bytes
    content: str = ""      # File content (loaded separately for performance)

    @property
    def token_estimate(self) -> int:
        """Rough token estimate (4 chars per token)."""
        return self.size_bytes // 4


@dataclass
class FileContext:
    """Collection of user-added files."""
    files: List[FileEntry] = field(default_factory=list)

    @property
    def total_size(self) -> int:
        """Total size of all files in bytes."""
        return sum(f.size_bytes for f in self.files)

    @property
    def total_tokens(self) -> int:
        """Rough total token estimate."""
        return sum(f.token_estimate for f in self.files)

    def is_empty(self) -> bool:
        """Check if context has no files."""
        return len(self.files) == 0


class FileContextManager:
    """
    Manages persistent file context storage and retrieval.

    Storage format (metadata only, content read on-demand):
    {
        "files": [
            {
                "path": "/abs/path/file.py",
                "display_path": "src/file.py",
                "added_at": 1703000000.0,
                "expires_at": 1703000600.0,
                "size_bytes": 1234
            }
        ],
        "version": 1
    }

    Limits:
    - 100KB total across all files
    - 50KB per individual file
    - Default TTL: 10 minutes

    Performance:
    - Metadata load: ~5ms (small JSON file)
    - Content load: Delegated to caller (daemon caches it)
    """

    # Size limits
    MAX_TOTAL_SIZE = 100 * 1024       # 100KB total
    MAX_FILE_SIZE = 50 * 1024         # 50KB per file
    DEFAULT_TTL = 600                  # 10 minutes

    def __init__(self, session_name: str = "default"):
        """
        Initialize file context manager.

        Args:
            session_name: Session name for context isolation
        """
        self.session_name = session_name
        self.storage_dir = Path.home() / ".local/share/codedjinn/context"
        self.storage_file = self.storage_dir / f"{session_name}.json"
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def add_files(
        self,
        file_paths: List[str],
        duration_seconds: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Add files to context.

        Args:
            file_paths: List of file paths (relative or absolute)
            duration_seconds: How long files stay in context (default: 10 min)

        Returns:
            {
                'added': List[str],      # Successfully added files
                'skipped': List[str],    # Skipped files (binary/non-text)
                'errors': List[str],     # Error messages
                'context': FileContext   # Updated context
            }
        """
        if duration_seconds is None:
            duration_seconds = self.DEFAULT_TTL

        # Load existing metadata and clean expired
        current = self._load_metadata()
        current = self._remove_expired(current)

        now = time.time()
        expires_at = now + duration_seconds

        added = []
        skipped = []
        errors = []

        for path_str in file_paths:
            try:
                path = Path(path_str).resolve()

                # Check if file exists
                if not path.exists():
                    errors.append(f"File not found: {path_str}")
                    continue

                if not path.is_file():
                    errors.append(f"Not a file: {path_str}")
                    continue

                # Skip if already in context
                if any(f['path'] == str(path) for f in current):
                    continue

                # Get file size
                size = path.stat().st_size

                # Check individual file size
                if size > self.MAX_FILE_SIZE:
                    errors.append(f"File too large ({size // 1024}KB > {self.MAX_FILE_SIZE // 1024}KB): {path_str}")
                    continue

                # Check total size would not exceed limit
                current_total = sum(f['size_bytes'] for f in current)
                if current_total + size > self.MAX_TOTAL_SIZE:
                    errors.append(
                        f"Would exceed total limit ({(current_total + size) // 1024}KB > "
                        f"{self.MAX_TOTAL_SIZE // 1024}KB): {path_str}"
                    )
                    continue

                # Check if text file (try to read as UTF-8)
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        f.read(1024)  # Read first 1KB to check
                except UnicodeDecodeError:
                    skipped.append(f"Binary file: {path_str}")
                    continue

                # Add to context
                current.append({
                    'path': str(path),
                    'display_path': self._make_relative(path),
                    'added_at': now,
                    'expires_at': expires_at,
                    'size_bytes': size,
                })
                added.append(str(path))

            except Exception as e:
                errors.append(f"Error adding {path_str}: {str(e)}")
                continue

        # Save updated metadata
        self._save_metadata(current)

        return {
            'added': added,
            'skipped': skipped,
            'errors': errors,
            'context': self._build_context(current),
        }

    def drop_files(self, file_paths: List[str]) -> List[str]:
        """
        Remove specific files from context.

        Args:
            file_paths: Files to remove (relative or absolute)

        Returns:
            List of removed file paths
        """
        current = self._load_metadata()
        removed = []

        # Resolve paths to compare
        paths_to_remove = set()
        for path_str in file_paths:
            try:
                paths_to_remove.add(str(Path(path_str).resolve()))
            except Exception:
                paths_to_remove.add(path_str)

        # Also try to match by display_path
        new_current = []
        for f in current:
            if f['path'] in paths_to_remove or f['display_path'] in file_paths:
                removed.append(f['display_path'])
            else:
                new_current.append(f)

        self._save_metadata(new_current)
        return removed

    def list_files(self) -> FileContext:
        """
        Get active (non-expired) files in context.

        Returns:
            FileContext with active files (no content loaded)
        """
        metadata = self._load_metadata()
        metadata = self._remove_expired(metadata)
        return self._build_context(metadata)

    def clear(self) -> int:
        """
        Remove all files from context.

        Returns:
            Number of files removed
        """
        metadata = self._load_metadata()
        count = len(metadata)
        self._save_metadata([])
        return count

    def get_context(self) -> FileContext:
        """
        Get active file context (metadata only, no content).

        This is the main entry point for the context system.
        Content should be loaded separately by daemon or direct caller.

        Returns:
            FileContext with files (content empty)
        """
        metadata = self._load_metadata()
        metadata = self._remove_expired(metadata)
        # Persist the cleanup
        self._save_metadata(metadata)
        return self._build_context(metadata)

    def get_context_with_content(self) -> FileContext:
        """
        Get file context with content loaded from disk.

        Use this for direct mode (non-daemon). For daemon mode,
        use DaemonState.get_file_context_with_content() for caching.

        Returns:
            FileContext with files and content populated
        """
        ctx = self.get_context()

        # Load content for each file
        for entry in ctx.files:
            try:
                content = Path(entry.path).read_text(encoding='utf-8', errors='ignore')
                entry.content = content
            except Exception:
                # File deleted or unreadable - skip silently
                entry.content = f"[Error: Could not read file {entry.display_path}]"

        return ctx

    def _load_metadata(self) -> List[Dict[str, Any]]:
        """Load metadata from disk."""
        if not self.storage_file.exists():
            return []

        try:
            with open(self.storage_file, 'r') as f:
                data = json.load(f)
            return data.get('files', [])
        except (json.JSONDecodeError, KeyError, TypeError):
            return []

    def _save_metadata(self, files: List[Dict[str, Any]]) -> None:
        """Save metadata to disk."""
        with open(self.storage_file, 'w') as f:
            json.dump({'files': files, 'version': 1}, f, indent=2)

    def _remove_expired(self, files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove expired files from list."""
        now = time.time()
        return [f for f in files if f['expires_at'] > now]

    def _make_relative(self, path: Path) -> str:
        """Convert absolute path to relative for display."""
        try:
            return str(path.relative_to(Path.cwd()))
        except ValueError:
            # Path is not relative to cwd, use filename
            return path.name

    def _build_context(self, metadata: List[Dict[str, Any]]) -> FileContext:
        """
        Build FileContext from metadata.

        Note: Does NOT load file content - caller must do this.
        """
        entries = []
        for meta in metadata:
            entries.append(FileEntry(
                path=meta['path'],
                display_path=meta['display_path'],
                added_at=meta['added_at'],
                expires_at=meta['expires_at'],
                size_bytes=meta['size_bytes'],
                content="",  # Loaded separately
            ))

        return FileContext(files=entries)


# ============================================================================
# Singleton Pattern (Convenience)
# ============================================================================

_manager: Optional[FileContextManager] = None


def get_file_context_manager(session_name: str = "default") -> FileContextManager:
    """
    Get or create singleton file context manager.

    Args:
        session_name: Session name for context isolation

    Returns:
        Singleton FileContextManager instance
    """
    global _manager
    if _manager is None or _manager.session_name != session_name:
        _manager = FileContextManager(session_name)
    return _manager


def get_file_context(session_name: str = "default") -> FileContext:
    """
    Main entry point - get file context for session (metadata only).

    For content, call get_file_context_with_content() on the manager
    or use daemon caching.

    Returns:
        FileContext with files (content empty)
    """
    manager = get_file_context_manager(session_name)
    return manager.get_context()


def parse_duration(duration_str: str) -> int:
    """
    Parse duration string to seconds.

    Supported formats:
    - "10m" or "10min" → 10 minutes (600 seconds)
    - "2h" or "2hr" → 2 hours (7200 seconds)
    - "1d" or "1day" → 1 day (86400 seconds)

    Returns:
        Duration in seconds (default: 600 = 10 minutes)
    """
    import re
    duration_str = duration_str.lower().strip()

    match = re.match(r'^(\d+)\s*(m|min|h|hr|hour|d|day)s?$', duration_str)
    if not match:
        return FileContextManager.DEFAULT_TTL

    value = int(match.group(1))
    unit = match.group(2)

    if unit in ('m', 'min'):
        return value * 60
    elif unit in ('h', 'hr', 'hour'):
        return value * 3600
    elif unit in ('d', 'day'):
        return value * 86400

    return FileContextManager.DEFAULT_TTL
