"""Lightweight client for daemon communication.

This module provides a thin client that connects to the daemon via Unix socket.
It's designed for minimal imports to keep CLI startup fast (~3ms).

Usage:
    client = DaemonClient()
    if client.is_daemon_running():
        result = client.run("list files")
    else:
        # Fallback to direct mode
        ...
"""

import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from codedjinn.daemon.protocol import (
    serialize_request,
    deserialize_response,
)


def get_socket_path() -> Path:
    """Get default socket path."""
    return Path.home() / ".config/codedjinn/daemon.sock"


def get_pid_path() -> Path:
    """Get default PID file path."""
    return Path.home() / ".config/codedjinn/daemon.pid"


class DaemonClient:
    """
    Lightweight client for daemon communication.
    
    Designed for minimal overhead:
    - Uses stdlib socket (no external deps)
    - Simple JSON protocol
    - Fast connection check
    """
    
    def __init__(
        self,
        socket_path: Optional[Path] = None,
        timeout: float = 30.0,
    ):
        """
        Initialize client.
        
        Args:
            socket_path: Path to Unix socket
            timeout: Socket timeout in seconds
        """
        self.socket_path = socket_path or get_socket_path()
        self.timeout = timeout
    
    def is_daemon_running(self) -> bool:
        """
        Check if daemon is running and healthy.
        
        Returns True if:
        1. Socket file exists
        2. Can connect to socket
        3. Health check returns OK
        """
        if not self.socket_path.exists():
            return False
        
        try:
            response = self._send_request(
                command="health",
                timeout=2.0,  # Quick timeout for health check
            )
            return response.get("status") == "ok"
        except (ConnectionRefusedError, socket.timeout, OSError):
            return False
    
    def ensure_daemon_running(self, auto_start: bool = True) -> bool:
        """
        Ensure daemon is running, optionally auto-starting it.
        
        Args:
            auto_start: If True, start daemon if not running
            
        Returns:
            True if daemon is running (or was started)
        """
        if self.is_daemon_running():
            return True
        
        if not auto_start:
            return False
        
        # Clean up stale PID file
        pid_path = get_pid_path()
        if pid_path.exists():
            try:
                pid = int(pid_path.read_text().strip())
                # Check if process exists
                os.kill(pid, 0)
            except (ValueError, ProcessLookupError, PermissionError):
                # Stale PID file - remove it
                pid_path.unlink(missing_ok=True)
                if self.socket_path.exists():
                    self.socket_path.unlink(missing_ok=True)
        
        # Start daemon
        return self._start_daemon()
    
    def _start_daemon(self) -> bool:
        """
        Start the daemon in background.
        
        Returns True if daemon started successfully.
        """
        # Use subprocess to start daemon with --daemonize
        try:
            subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "codedjinn.daemon.server",
                    "--daemonize",
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
        except Exception:
            return False
        
        # Wait for daemon to be ready (max 5 seconds)
        for _ in range(50):
            time.sleep(0.1)
            if self.is_daemon_running():
                return True
        
        return False
    
    def run(
        self,
        query: str,
        cwd: Optional[str] = None,
        session_name: str = "default",
        no_context: bool = False,
        verbose: bool = False,
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Send 'run' command to daemon.
        
        Args:
            query: Natural language query
            cwd: Current working directory
            session_name: Session name
            no_context: Ignore previous context
            verbose: Verbose output
            
        Returns:
            (success, result_dict)
            result_dict has 'command' key on success, 'error' on failure
        """
        response = self._send_request(
            command="run",
            query=query,
            cwd=cwd or str(Path.cwd()),
            session_name=session_name,
            options={
                "no_context": no_context,
                "verbose": verbose,
            },
        )
        
        if response.get("status") == "ok":
            return True, response.get("result", {})
        else:
            return False, {"error": response.get("error", "Unknown error")}
    
    def ask(
        self,
        query: str,
        cwd: Optional[str] = None,
        session_name: str = "default",
        no_context: bool = False,
        steps: int = 0,
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Send 'ask' command to daemon.
        
        Args:
            query: Question about previous output
            cwd: Current working directory
            session_name: Session name
            no_context: Ignore previous context
            steps: Number of reasoning steps (0=single-shot, 1-5=multi-step)
            
        Returns:
            (success, result_dict)
            result_dict has 'response' key on success, 'error' on failure
        """
        response = self._send_request(
            command="ask",
            query=query,
            cwd=cwd or str(Path.cwd()),
            session_name=session_name,
            steps=steps,
            options={
                "no_context": no_context,
            },
        )
        
        if response.get("status") == "ok":
            return True, response.get("result", {})
        else:
            return False, {"error": response.get("error", "Unknown error")}
    
    def save_session(
        self,
        session_name: str,
        command: str,
        output: str,
        exit_code: int,
    ) -> bool:
        """
        Save session to daemon's in-memory storage.
        
        This is called after command execution to update the session
        for the next 'ask' or 'run' command.
        """
        response = self._send_request(
            command="save_session",
            session_name=session_name,
            options={
                "command": command,
                "output": output,
                "exit_code": exit_code,
            },
        )
        return response.get("status") == "ok"
    
    def health(self) -> Optional[Dict[str, Any]]:
        """
        Get daemon health and stats.
        
        Returns stats dict or None if daemon not running.
        """
        try:
            response = self._send_request(command="health", timeout=2.0)
            if response.get("status") == "ok":
                return response.get("result")
        except (ConnectionRefusedError, socket.timeout, OSError):
            pass
        return None
    
    def shutdown(self) -> bool:
        """
        Request daemon shutdown.
        
        Returns True if shutdown was acknowledged.
        """
        try:
            response = self._send_request(command="shutdown", timeout=5.0)
            return response.get("status") == "ok"
        except (ConnectionRefusedError, socket.timeout, OSError):
            return False
    
    def _send_request(
        self,
        command: str,
        query: str = "",
        cwd: str = "",
        session_name: str = "default",
        steps: int = 0,
        options: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Send request to daemon and return response.
        
        Raises:
            ConnectionRefusedError: If daemon not running
            socket.timeout: If request times out
            OSError: Other socket errors
        """
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(timeout or self.timeout)
        
        try:
            sock.connect(str(self.socket_path))
            
            # Send request
            request_data = serialize_request(
                command=command,
                query=query,
                cwd=cwd,
                session_name=session_name,
                steps=steps,
                options=options,
            )
            sock.sendall(request_data)
            
            # Receive response (up to 1MB)
            chunks = []
            while True:
                chunk = sock.recv(65536)
                if not chunk:
                    break
                chunks.append(chunk)
                # Check if we got a complete JSON response
                try:
                    data = b"".join(chunks)
                    return deserialize_response(data)
                except json.JSONDecodeError:
                    continue
            
            if not chunks:
                return {"status": "error", "error": "Empty response"}
            
            return deserialize_response(b"".join(chunks))
            
        finally:
            sock.close()


def is_daemon_enabled() -> bool:
    """
    Check if daemon mode is enabled.
    
    Daemon is DISABLED if:
    - CODEDJINN_NO_DAEMON=1 environment variable is set
    - Running on Windows (Unix sockets not available)
    
    Returns:
        True if daemon mode should be used
    """
    if os.environ.get("CODEDJINN_NO_DAEMON", "").lower() in ("1", "true", "yes"):
        return False
    
    if sys.platform == "win32":
        return False
    
    return True
