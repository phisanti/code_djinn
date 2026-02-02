"""JSON-based protocol for daemon IPC.

Simple, human-readable protocol for communication between CLI client and daemon.

Request format:
    {
        "command": "run" | "ask" | "health" | "shutdown",
        "query": str,           # For run/ask
        "cwd": str,             # Current working directory
        "session_name": str,    # Session identifier
        "options": {            # Command-specific options
            "verbose": bool,
            "no_context": bool,
            ...
        }
    }

Response format:
    {
        "status": "ok" | "error",
        "result": str | dict,   # Command result
        "error": str | None,    # Error message if status == "error"
    }

Performance: JSON serialization is ~0.1ms for typical payloads.
"""

import json
from typing import Any, Dict, Optional


def serialize_request(
    command: str,
    query: str = "",
    cwd: str = "",
    session_name: str = "default",
    steps: int = 0,
    options: Optional[Dict[str, Any]] = None,
) -> bytes:
    """
    Serialize request to bytes for socket transmission.
    
    Args:
        command: Command type (run, ask, health, shutdown)
        query: User query string
        cwd: Current working directory
        session_name: Session name for context
        steps: Number of reasoning steps (for ask command)
        options: Additional options dict
        
    Returns:
        UTF-8 encoded JSON bytes
    """
    request = {
        "command": command,
        "query": query,
        "cwd": cwd,
        "session_name": session_name,
        "steps": steps,
        "options": options or {},
    }
    return json.dumps(request).encode("utf-8")


def deserialize_request(data: bytes) -> Dict[str, Any]:
    """
    Deserialize request from bytes.
    
    Args:
        data: UTF-8 encoded JSON bytes
        
    Returns:
        Request dictionary
        
    Raises:
        json.JSONDecodeError: If data is not valid JSON
    """
    return json.loads(data.decode("utf-8"))


def serialize_response(
    status: str,
    result: Any = None,
    error: Optional[str] = None,
) -> bytes:
    """
    Serialize response to bytes for socket transmission.
    
    Args:
        status: "ok" or "error"
        result: Command result (command string, analysis text, etc.)
        error: Error message if status is "error"
        
    Returns:
        UTF-8 encoded JSON bytes
    """
    response = {
        "status": status,
        "result": result,
        "error": error,
    }
    return json.dumps(response).encode("utf-8")


def deserialize_response(data: bytes) -> Dict[str, Any]:
    """
    Deserialize response from bytes.
    
    Args:
        data: UTF-8 encoded JSON bytes
        
    Returns:
        Response dictionary
        
    Raises:
        json.JSONDecodeError: If data is not valid JSON
    """
    return json.loads(data.decode("utf-8"))
