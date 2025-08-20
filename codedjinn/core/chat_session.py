import json
import os
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime


class ChatSession:
    """
    Manages persistent chat sessions with command output capture.
    
    Handles session storage, message history management, and command execution
    result tracking for conversational interactions that persist across
    CLI invocations.
    """

    def __init__(self, session_id: Optional[str] = None, max_messages: int = 50):
        """
        Initialize a chat session.
        
        Args:
            session_id: Unique identifier for the session. If None, generates an ID automatically.
            max_messages: Maximum number of messages to keep in history
        """
        self.max_messages = max_messages
        self.storage_path = Path.home() / ".config" / "codedjinn" / "sessions"
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        if session_id is None:
            # Create new session with timestamp-based ID
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.session_id = f"chat_{timestamp}"
        else:
            self.session_id = session_id
            
        self.session_file = self.storage_path / f"{self.session_id}.json"
        self.messages = self._load_messages()

    def _load_messages(self) -> List[Dict[str, str]]:
        """Load messages from session file."""
        if self.session_file.exists():
            try:
                with open(self.session_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get('messages', [])
            except (json.JSONDecodeError, IOError):
                # If file is corrupted, start fresh
                return []
        return []

    def _save_messages(self):
        """Save messages to session file."""
        try:
            data = {
                'session_id': self.session_id,
                'created_at': datetime.now().isoformat(),
                'messages': self.messages
            }
            with open(self.session_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"Warning: Could not save session {self.session_id}: {e}")

    def add_message(self, role: str, content: str, metadata: Optional[Dict] = None):
        """
        Add a message to the conversation.
        
        Args:
            role: 'user', 'assistant', or 'system'
            content: Message content
            metadata: Additional metadata (command outputs, execution status, etc.)
        """
        message = {
            'role': role,
            'content': content,
            'timestamp': datetime.now().isoformat()
        }
        
        if metadata:
            message['metadata'] = metadata
            
        self.messages.append(message)
        
        # Trim messages if exceeding max_messages, but keep system messages
        if len(self.messages) > self.max_messages:
            # Keep system messages and trim user/assistant pairs
            system_messages = [msg for msg in self.messages if msg['role'] == 'system']
            conversation_messages = [msg for msg in self.messages if msg['role'] != 'system']
            
            # Keep the most recent messages
            if len(conversation_messages) > self.max_messages - len(system_messages):
                keep_count = self.max_messages - len(system_messages)
                # Ensure we keep user/assistant pairs
                if keep_count % 2 == 1:
                    keep_count -= 1
                conversation_messages = conversation_messages[-keep_count:]
            
            self.messages = system_messages + conversation_messages
        
        self._save_messages()

    def add_command_execution(self, command: str, success: bool, stdout: str, stderr: str):
        """
        Add command execution details to the session.
        
        Args:
            command: The executed command
            success: Whether execution was successful
            stdout: Command output
            stderr: Command errors
        """
        # Create a summary of the command execution
        execution_summary = f"Command: {command}\n"
        execution_summary += f"Status: {'Success' if success else 'Failed'}\n"
        
        if stdout.strip():
            # Truncate very long outputs but preserve important information
            if len(stdout) > 2000:
                execution_summary += f"Output (truncated): {stdout[:1500]}...\n[Output truncated - showing first 1500 characters]\n"
            else:
                execution_summary += f"Output: {stdout}\n"
        
        if stderr.strip():
            execution_summary += f"Errors: {stderr}\n"
        
        metadata = {
            'type': 'command_execution',
            'command': command,
            'success': success,
            'output_length': len(stdout) + len(stderr)
        }
        
        self.add_message('system', execution_summary, metadata)

    def get_context_for_prompt(self, max_context_messages: int = 20) -> str:
        """
        Get formatted conversation context for LLM prompts.
        
        Args:
            max_context_messages: Maximum number of recent messages to include
            
        Returns:
            Formatted conversation context string
        """
        if not self.messages:
            return "No previous conversation."
        
        # Get recent messages for context
        recent_messages = self.messages[-max_context_messages:]
        
        context_lines = []
        for msg in recent_messages:
            role = msg['role'].title()
            content = msg['content']
            
            # Format different message types
            if msg.get('metadata', {}).get('type') == 'command_execution':
                # Special formatting for command executions
                context_lines.append(f"[Command Execution Result]")
                context_lines.append(content)
            else:
                context_lines.append(f"{role}: {content}")
        
        return "\n".join(context_lines)

    def clear_session(self):
        """Clear all messages from the current session."""
        self.messages = []
        self._save_messages()

    def list_sessions(self) -> List[str]:
        """List all available session IDs."""
        if not self.storage_path.exists():
            return []
        
        sessions = []
        for session_file in self.storage_path.glob("*.json"):
            session_id = session_file.stem
            sessions.append(session_id)
        
        return sorted(sessions)

    def delete_session(self, session_id: Optional[str] = None):
        """Delete a session file."""
        target_session = session_id or self.session_id
        session_file = self.storage_path / f"{target_session}.json"
        
        if session_file.exists():
            session_file.unlink()
            if target_session == self.session_id:
                self.messages = []

    def get_session_info(self) -> Dict:
        """Get information about the current session."""
        return {
            'session_id': self.session_id,
            'message_count': len(self.messages),
            'session_file': str(self.session_file),
            'exists': self.session_file.exists()
        }
