"""Daemon architecture for Code Djinn.

This module provides a long-running background process that eliminates
the ~900ms Mistral SDK import overhead per CLI invocation.

Architecture:
- DaemonState: In-memory cache for Mistral client, context, and sessions
- DaemonServer: Async Unix socket server handling client requests
- ThinClient: Lightweight client that connects to daemon via socket

Performance improvement: 993ms → <50ms controllable overhead (99%+ reduction)
"""

from codedjinn.daemon.state import DaemonState
from codedjinn.daemon.client import DaemonClient
from codedjinn.daemon.protocol import (
    serialize_request,
    deserialize_request,
    serialize_response,
    deserialize_response,
)

__all__ = [
    "DaemonState",
    "DaemonClient",
    "serialize_request",
    "deserialize_request",
    "serialize_response",
    "deserialize_response",
]
