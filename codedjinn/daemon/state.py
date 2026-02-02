"""In-memory state for daemon - eliminates per-request overhead.

This class holds all expensive resources that would normally be recreated
on every CLI invocation. By keeping them in memory, we eliminate 99%+ of
startup overhead.

Key caches:
- mistral_client: Mistral SDK client (eliminates ~900ms import)
- context_cache: Context by cwd with TTL (eliminates ~45ms context building)
- sessions: In-memory session storage (eliminates ~1ms disk I/O)
"""

import time
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from mistralai import Mistral


@dataclass
class CachedContext:
    """Cached context with timestamp for TTL expiry."""
    context_result: Any  # ContextualiserResult
    timestamp: float


@dataclass
class SessionData:
    """In-memory session data."""
    command: str
    output: str
    timestamp: str
    exit_code: int


@dataclass
class CachedFileContent:
    """Cached file content with timestamp."""
    content: str
    timestamp: float
    size: int


class DaemonState:
    """
    In-memory state for daemon.
    
    Holds all expensive resources pre-initialized at daemon startup.
    All access is instant (dict lookup) vs CLI startup (imports + I/O).
    
    Thread safety: This class is NOT thread-safe. The daemon uses asyncio
    which is single-threaded, so no locking is needed.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize daemon state with expensive imports.
        
        This is the ONE-TIME cost (~1 second) that eliminates
        ~900ms per CLI invocation.
        
        Args:
            config: Raw config dict from load_raw_config() with keys:
                - mistral_api_key: API key
                - llm_model: Model name
                - os: OS name
                - shell: Shell type
        """
        self.config = config
        self.start_time = time.time()
        
        # Import and create Mistral client (the expensive part!)
        from mistralai import Mistral
        
        # Get API key based on provider
        provider = config.get("llm_provider", "").lower()
        api_key_map = {
            "mistralai": "mistral_api_key",
            "gemini": "gemini_api_key",
            "deepinfra": "deepinfra_api_token",
        }
        api_key = config.get(api_key_map.get(provider, "mistral_api_key"), "")
        self.mistral_client: "Mistral" = Mistral(api_key=api_key)
        
        # Context cache: {cwd: CachedContext}
        self.context_cache: Dict[str, CachedContext] = {}
        self.context_ttl: float = 30.0  # seconds
        
        # Session storage: {session_name: SessionData}
        self.sessions: Dict[str, SessionData] = {}

        # File content cache: {path: CachedFileContent}
        self.file_content_cache: Dict[str, CachedFileContent] = {}
        self.file_cache_ttl: float = 30.0  # Same as context TTL

        # Load existing sessions from disk
        self._load_sessions_from_disk()
    
    def get_context(
        self,
        cwd: str,
        os_name: str,
        shell: str,
        session_context: Optional[Dict[str, Any]] = None,
        session_name: str = "default",
    ) -> Any:
        """
        Get context with caching.

        Cache key: cwd (working directory)
        TTL: 30 seconds (git status changes infrequently)

        Why cache: Building context requires:
        - git status subprocess (~15ms)
        - shell history file read (~5ms)
        - project detection (~10ms)
        Total: ~30-45ms per request

        With cache: ~0ms (memory lookup)

        Args:
            cwd: Current working directory
            os_name: OS name from config
            shell: Shell type from config
            session_context: Previous command context
            session_name: Session name for file context

        Returns:
            ContextualiserResult
        """
        cache_key = str(Path(cwd).resolve())
        now = time.time()

        # Get file context with content (uses file cache)
        file_ctx = self.get_file_context_with_content(session_name)

        # Check cache (without session/file context since those vary)
        if cache_key in self.context_cache:
            cached = self.context_cache[cache_key]
            if (now - cached.timestamp) < self.context_ttl:
                # Cache hit! Update session and file context, return
                result = cached.context_result
                result.session_context = session_context
                result._session_xml = None  # Reset lazy cache
                result.file_context = file_ctx
                result._file_xml = None  # Reset lazy cache
                return result

        # Cache miss - build fresh context
        from codedjinn.context.contextualiser import contextualise

        context_result = contextualise(
            os_name=os_name,
            shell=shell,
            cwd=cwd,
            session_context=session_context,
            file_context=file_ctx,
        )

        # Cache without session/file context (those vary per request)
        cache_result = contextualise(
            os_name=os_name,
            shell=shell,
            cwd=cwd,
            session_context=None,
            include_files=False,  # Don't include file context in cache
        )
        self.context_cache[cache_key] = CachedContext(
            context_result=cache_result,
            timestamp=now,
        )

        return context_result

    def get_file_context_with_content(self, session_name: str = "default") -> Any:
        """
        Get file context with content loaded from cache.

        This is the DAEMON version - uses in-memory cache for performance.

        Performance:
        - Metadata load: ~5ms (file read)
        - Content load: ~1ms per file (memory lookup)
        - Cache miss: ~10ms per file (disk read)
        - Total: ~5-10ms for typical usage

        Args:
            session_name: Session name for context isolation

        Returns:
            FileContext with content populated
        """
        from codedjinn.context.sources.files import (
            get_file_context,
            FileContext,
            FileEntry,
        )

        # Get metadata (fast, ~5ms)
        ctx = get_file_context(session_name)

        if ctx.is_empty():
            return ctx

        # Load content from cache or disk
        now = time.time()
        entries_with_content = []

        for entry in ctx.files:
            path = entry.path

            # Check cache
            if path in self.file_content_cache:
                cached = self.file_content_cache[path]
                if (now - cached.timestamp) < self.file_cache_ttl:
                    # Cache hit! (<1ms)
                    entry.content = cached.content
                    entries_with_content.append(entry)
                    continue

            # Cache miss - load from disk
            try:
                content = Path(path).read_text(encoding='utf-8', errors='ignore')

                # Update cache
                self.file_content_cache[path] = CachedFileContent(
                    content=content,
                    timestamp=now,
                    size=len(content),
                )

                # Update entry
                entry.content = content
                entries_with_content.append(entry)

            except Exception:
                # File deleted/unreadable - skip silently
                continue

        return FileContext(files=entries_with_content)

    def get_session(self, session_name: str) -> Optional[Dict[str, Any]]:
        """
        Get session context from in-memory storage.
        
        Returns dict compatible with Session.get_context_for_prompt():
            {'command': str, 'output': str, 'exit_code': int}
        """
        if session_name not in self.sessions:
            return None
        
        data = self.sessions[session_name]
        return {
            "command": data.command,
            "output": data.output,
            "exit_code": data.exit_code,
        }
    
    def get_conversation_history(self, session_name: str) -> Optional[list[Dict[str, Any]]]:
        """
        Get conversation history from disk for multi-step reasoning.
        
        Returns list of dicts with 'command', 'output', 'exit_code' keys, or None if no history.
        Output is trimmed to 200 chars to maintain token budget.
        """
        import json
        
        history_file = Path.home() / ".config/codedjinn/sessions" / f"{session_name}_history.json"
        
        if not history_file.exists():
            return None
        
        try:
            with open(history_file) as f:
                data = json.load(f)
            
            if not data:
                return None
            
            return [
                {
                    'command': ex.get('command', ''),
                    'output': ex.get('output', '')[:200],  # Trim to 200 chars
                    'exit_code': ex.get('exit_code', 0)
                }
                for ex in data
            ]
        except (json.JSONDecodeError, KeyError, TypeError):
            return None
    
    def save_session(
        self,
        session_name: str,
        command: str,
        output: str,
        exit_code: int,
    ) -> None:
        """
        Save session to in-memory storage.
        
        Memory update is instant (~0ms).
        Disk persistence happens asynchronously.
        """
        self.sessions[session_name] = SessionData(
            command=command,
            output=output,
            timestamp=datetime.now().isoformat(),
            exit_code=exit_code,
        )
    
    def clear_session(self, session_name: str) -> None:
        """Clear a session from memory."""
        if session_name in self.sessions:
            del self.sessions[session_name]
    
    def _load_sessions_from_disk(self) -> None:
        """Load existing sessions from disk on daemon startup."""
        import json
        session_dir = Path.home() / ".config/codedjinn/sessions"
        
        if not session_dir.exists():
            return
        
        for session_file in session_dir.glob("*.json"):
            try:
                with open(session_file) as f:
                    data = json.load(f)
                session_name = session_file.stem
                self.sessions[session_name] = SessionData(**data)
            except (json.JSONDecodeError, KeyError, TypeError):
                pass  # Skip corrupted files
    
    def persist_sessions(self) -> None:
        """Persist all sessions to disk (called on shutdown)."""
        import json
        session_dir = Path.home() / ".config/codedjinn/sessions"
        session_dir.mkdir(parents=True, exist_ok=True)
        
        for session_name, data in self.sessions.items():
            session_file = session_dir / f"{session_name}.json"
            with open(session_file, "w") as f:
                json.dump(asdict(data), f, indent=2)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get daemon statistics for health check."""
        return {
            "uptime_seconds": time.time() - self.start_time,
            "cached_contexts": len(self.context_cache),
            "active_sessions": len(self.sessions),
            "cached_files": len(self.file_content_cache),
            "context_ttl": self.context_ttl,
        }
    
    def clear_context_cache(self) -> None:
        """Clear context cache (useful for testing)."""
        self.context_cache.clear()
