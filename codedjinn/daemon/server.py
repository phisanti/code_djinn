"""Async Unix socket server for Code Djinn daemon.

This module implements the long-running daemon process that:
1. Imports Mistral SDK once at startup (eliminates ~900ms per request)
2. Caches context and sessions in memory
3. Handles requests via Unix socket IPC

Usage:
    python -m codedjinn.daemon.server [--socket-path PATH] [--idle-timeout SECONDS]
    
    Or use the CLI:
    code-djinn daemon start
"""

import asyncio
import json
import logging
import os
import signal
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

from codedjinn.daemon.state import DaemonState
from codedjinn.daemon.protocol import (
    deserialize_request,
    serialize_response,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def get_default_paths() -> tuple[Path, Path, Path]:
    """Get default paths for socket, PID file, and log file."""
    config_dir = Path.home() / ".config/codedjinn"
    return (
        config_dir / "daemon.sock",
        config_dir / "daemon.pid",
        config_dir / "daemon.log",
    )


class DaemonServer:
    """
    Async Unix socket server for daemon.
    
    Handles concurrent client connections using asyncio.
    Each request is processed independently.
    """
    
    def __init__(
        self,
        socket_path: Optional[Path] = None,
        pid_path: Optional[Path] = None,
        idle_timeout: float = 3600.0,  # 1 hour
    ):
        """
        Initialize daemon server.
        
        Args:
            socket_path: Path to Unix socket
            pid_path: Path to PID file
            idle_timeout: Shutdown after this many seconds idle (0 = never)
        """
        default_socket, default_pid, _ = get_default_paths()
        self.socket_path = socket_path or default_socket
        self.pid_path = pid_path or default_pid
        self.idle_timeout = idle_timeout
        
        self.state: Optional[DaemonState] = None
        self.server: Optional[asyncio.Server] = None
        self.last_request_time: float = time.time()
        self._shutdown_event: asyncio.Event = asyncio.Event()
    
    async def start(self) -> None:
        """Start the daemon server."""
        logger.info("Starting Code Djinn daemon...")
        
        # Load configuration
        from codedjinn.core.configs import load_raw_config
        try:
            config = load_raw_config()
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            sys.exit(1)
        
        # Initialize state (imports Mistral SDK - the expensive part!)
        logger.info("Initializing daemon state (importing Mistral SDK)...")
        start = time.time()
        self.state = DaemonState(config)
        elapsed = time.time() - start
        logger.info(f"Daemon state initialized in {elapsed:.2f}s")
        
        # Clean up stale socket
        if self.socket_path.exists():
            self.socket_path.unlink()
        
        # Create parent directory
        self.socket_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write PID file
        self.pid_path.write_text(str(os.getpid()))
        
        # Start Unix socket server
        self.server = await asyncio.start_unix_server(
            self._handle_client,
            path=str(self.socket_path),
        )
        
        # Set socket permissions (owner only)
        os.chmod(self.socket_path, 0o600)
        
        logger.info(f"Daemon listening on {self.socket_path}")
        
        # Setup signal handlers
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, self._signal_handler)
        
        # Start idle timeout watcher
        if self.idle_timeout > 0:
            asyncio.create_task(self._idle_watcher())
        
        # Serve until shutdown
        async with self.server:
            await self._shutdown_event.wait()
        
        # Cleanup
        await self._cleanup()
    
    async def _handle_client(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        """Handle a single client connection."""
        try:
            # Read request (max 64KB)
            data = await asyncio.wait_for(reader.read(65536), timeout=30.0)
            if not data:
                return
            
            # Update activity timestamp
            self.last_request_time = time.time()
            
            # Parse and route request
            try:
                request = deserialize_request(data)
            except json.JSONDecodeError as e:
                response = serialize_response("error", error=f"Invalid JSON: {e}")
                writer.write(response)
                await writer.drain()
                return
            
            # Route to handler
            command = request.get("command", "")
            if command == "run":
                response = await self._handle_run(request)
            elif command == "ask":
                response = await self._handle_ask(request)
            elif command == "save_session":
                response = await self._handle_save_session(request)
            elif command == "health":
                response = await self._handle_health(request)
            elif command == "shutdown":
                response = await self._handle_shutdown(request)
            else:
                response = serialize_response(
                    "error",
                    error=f"Unknown command: {command}",
                )
            
            writer.write(response)
            await writer.drain()
            
        except asyncio.TimeoutError:
            logger.warning("Client connection timed out")
        except Exception as e:
            logger.exception(f"Error handling client: {e}")
            try:
                response = serialize_response("error", error=str(e))
                writer.write(response)
                await writer.drain()
            except Exception:
                pass
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass
    
    async def _handle_run(self, request: Dict[str, Any]) -> bytes:
        """
        Handle 'run' command - generate shell command.
        
        Uses pre-initialized Mistral client and cached context
        for maximum speed.
        """
        query = request.get("query", "")
        cwd = request.get("cwd", str(Path.cwd()))
        session_name = request.get("session_name", "default")
        options = request.get("options", {})
        
        if not query:
            return serialize_response("error", error="Missing 'query' parameter")
        
        try:
            # Get session context (from memory - instant!)
            previous_context = None
            if not options.get("no_context", False):
                previous_context = self.state.get_session(session_name)
            
            # Build context (cached or fresh)
            os_name = self.state.config.get("os", "Linux")
            shell = self.state.config.get("shell", "bash")
            
            context_result = self.state.get_context(
                cwd=cwd,
                os_name=os_name,
                shell=shell,
                session_context=previous_context,
                session_name=session_name,
            )
            
            # Create agent with pre-initialized client
            from codedjinn.providers.mistral import MistralAgent
            
            model = self.state.config.get("llm_model", "mistral-small-latest")
            agent = MistralAgent(
                api_key=None,  # Not used when client is provided
                model=model,
                client=self.state.mistral_client,  # Pre-initialized!
            )
            
            # Build execution context dict
            context = {
                "cwd": Path(cwd),
                "os_name": os_name,
                "shell": shell,
            }
            
            # Generate command
            command = agent.generate_command(
                query=query,
                context=context,
                previous_context=previous_context,
            )
            
            return serialize_response("ok", result={"command": command})
            
        except Exception as e:
            logger.exception(f"Error in handle_run: {e}")
            return serialize_response("error", error=str(e))
    
    async def _handle_ask(self, request: Dict[str, Any]) -> bytes:
        """
        Handle 'ask' command - analyze previous output with optional multi-step reasoning.
        """
        query = request.get("query", "")
        cwd = request.get("cwd", str(Path.cwd()))
        session_name = request.get("session_name", "default")
        steps = request.get("steps", 0)
        options = request.get("options", {})
        
        if not query:
            return serialize_response("error", error="Missing 'query' parameter")
        
        try:
            # Get session context
            previous_context = None
            conversation_history = None
            if not options.get("no_context", False):
                previous_context = self.state.get_session(session_name)
                # Get conversation history for multi-step reasoning
                if steps > 0:
                    conversation_history = self.state.get_conversation_history(session_name)
            
            # Create agent
            from codedjinn.providers.mistral import MistralAgent
            
            model = self.state.config.get("llm_model", "mistral-small-latest")
            agent = MistralAgent(
                api_key=None,
                model=model,
                client=self.state.mistral_client,
            )
            
            # Build context dict
            os_name = self.state.config.get("os", "Linux")
            shell = self.state.config.get("shell", "bash")
            context = {
                "cwd": Path(cwd),
                "os_name": os_name,
                "shell": shell,
            }
            
            # Analyze - route based on steps
            if steps > 0:
                response_text = agent.analyze_with_steps(
                    question=query,
                    context=context,
                    max_steps=steps,
                    previous_context=previous_context,
                    conversation_history=conversation_history,
                )
            else:
                response_text = agent.analyze(
                    question=query,
                    context=context,
                    previous_context=previous_context,
                )
            
            return serialize_response("ok", result={"response": response_text})
            
        except Exception as e:
            logger.exception(f"Error in handle_ask: {e}")
            return serialize_response("error", error=str(e))
    
    async def _handle_save_session(self, request: Dict[str, Any]) -> bytes:
        """Handle session save request (after command execution)."""
        session_name = request.get("session_name", "default")
        options = request.get("options", {})
        
        command = options.get("command", "")
        output = options.get("output", "")
        exit_code = options.get("exit_code", 0)
        
        if not command:
            return serialize_response("error", error="Missing 'command' in options")
        
        self.state.save_session(
            session_name=session_name,
            command=command,
            output=output,
            exit_code=exit_code,
        )
        
        return serialize_response("ok", result={"saved": True})
    
    async def _handle_health(self, request: Dict[str, Any]) -> bytes:
        """Handle health check request."""
        stats = self.state.get_stats() if self.state else {}
        return serialize_response("ok", result=stats)
    
    async def _handle_shutdown(self, request: Dict[str, Any]) -> bytes:
        """Handle graceful shutdown request."""
        logger.info("Shutdown requested via socket")
        self._shutdown_event.set()
        return serialize_response("ok", result={"message": "Shutting down"})
    
    async def _idle_watcher(self) -> None:
        """Watch for idle timeout and shutdown if exceeded."""
        while not self._shutdown_event.is_set():
            await asyncio.sleep(60)  # Check every minute
            
            idle_time = time.time() - self.last_request_time
            if idle_time > self.idle_timeout:
                logger.info(
                    f"Idle timeout reached ({idle_time:.0f}s > {self.idle_timeout:.0f}s), "
                    "shutting down"
                )
                self._shutdown_event.set()
                break
    
    def _signal_handler(self) -> None:
        """Handle SIGTERM/SIGINT for graceful shutdown."""
        logger.info("Received shutdown signal")
        self._shutdown_event.set()
    
    async def _cleanup(self) -> None:
        """Cleanup on shutdown."""
        logger.info("Cleaning up...")

        # Persist sessions to disk
        if self.state:
            self.state.persist_sessions()

        # Close server
        if self.server:
            self.server.close()
            await self.server.wait_closed()

        # Remove socket and PID file
        if self.socket_path.exists():
            self.socket_path.unlink()
        if self.pid_path.exists():
            self.pid_path.unlink()

        logger.info("Daemon stopped")

    def _set_process_title(self, name: str) -> None:
        """
        Set process title for monitoring tools (htop, Activity Monitor, etc.).

        Tries multiple methods in order of preference:
        1. setproctitle (best, cross-platform, requires: pip install setproctitle)
        2. prctl (Linux-only, no deps, max 15 chars)
        3. sys.argv[0] (fallback, limited effectiveness)

        Args:
            name: Process name to display (e.g., "djinn-daemon")
        """
        # Method 1: setproctitle (recommended)
        try:
            import setproctitle

            # Make it dynamic with daemon stats
            if self.state:
                active_sessions = len(self.state.sessions)
                cached_contexts = len(self.state.context_cache)
                display_name = f"{name} [{active_sessions}s {cached_contexts}c]"
            else:
                display_name = name

            setproctitle.setproctitle(display_name)
            logger.info(f"Process title set to '{display_name}' via setproctitle")
            return
        except ImportError:
            logger.debug("setproctitle not installed, trying alternatives")
        except Exception as e:
            logger.debug(f"setproctitle failed: {e}")

        # Method 2: prctl (Linux only, no deps)
        if sys.platform == "linux":
            try:
                import ctypes
                libc = ctypes.CDLL('libc.so.6')
                # PR_SET_NAME = 15, max 15 chars
                truncated_name = name[:15]
                libc.prctl(15, truncated_name.encode(), 0, 0, 0)
                logger.info(f"Process title set to '{truncated_name}' via prctl")
                return
            except Exception as e:
                logger.debug(f"prctl failed: {e}")

        # Method 3: sys.argv[0] (fallback)
        try:
            sys.argv[0] = name
            logger.info(f"Process title set to '{name}' via argv[0] (limited)")
        except Exception as e:
            logger.warning(f"Failed to set process title: {e}")


def run_daemon(
    socket_path: Optional[str] = None,
    idle_timeout: float = 3600.0,
    daemonize: bool = False,
) -> None:
    """
    Run the daemon server.
    
    Args:
        socket_path: Path to Unix socket (default: ~/.config/codedjinn/daemon.sock)
        idle_timeout: Shutdown after this many seconds idle (0 = never)
        daemonize: Fork to background (Unix only)
    """
    if daemonize:
        # Double-fork to daemonize
        pid = os.fork()
        if pid > 0:
            # Parent exits
            sys.exit(0)
        
        os.setsid()
        
        pid = os.fork()
        if pid > 0:
            sys.exit(0)
        
        # Redirect stdio to /dev/null
        sys.stdin.close()
        
        # Redirect stdout/stderr to log file
        _, _, log_path = get_default_paths()
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_file = open(log_path, "a")
        os.dup2(log_file.fileno(), sys.stdout.fileno())
        os.dup2(log_file.fileno(), sys.stderr.fileno())

    # Create and run server
    server = DaemonServer(
        socket_path=Path(socket_path) if socket_path else None,
        idle_timeout=idle_timeout,
    )

    # Set process title after daemonization
    server._set_process_title("djinn-daemon")

    asyncio.run(server.start())


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Code Djinn daemon server")
    parser.add_argument(
        "--socket-path",
        help="Path to Unix socket",
    )
    parser.add_argument(
        "--idle-timeout",
        type=float,
        default=3600.0,
        help="Shutdown after this many seconds idle (0 = never)",
    )
    parser.add_argument(
        "--daemonize",
        action="store_true",
        help="Fork to background",
    )
    
    args = parser.parse_args()
    
    run_daemon(
        socket_path=args.socket_path,
        idle_timeout=args.idle_timeout,
        daemonize=args.daemonize,
    )
