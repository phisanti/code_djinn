from typing import Optional
from .base_mode import BaseMode
from ..core.command_executor import CommandExecutor
from ..core.response_parser import ResponseParser
from ..core.prompt_builder import build_chat_prompt
from ..core.input_prompt import ChatPrompt
from ..core.chat_session import ChatSession
from ..utils import print_text
import os
import time


class ChatMode(BaseMode):
    """
    Interactive chat mode with persistent sessions and command output capture.
    
    Manages conversational interactions between users and the AI assistant,
    maintaining session history across CLI invocations and capturing command
    execution results for contextual awareness in subsequent exchanges.
    """

    def __init__(
        self,
        llm_instance,
        provider: str,
        os_fullname: str,
        shell: str,
        system_prompt_preferences: str = "",
        shell_path: str = "",
        session_id: Optional[str] = None,
    ):
        super().__init__(
            llm_instance, provider, os_fullname, shell, system_prompt_preferences
        )
        self.executor = CommandExecutor(shell, shell_path)
        
        # Initialize persistent session
        self.session = ChatSession(session_id, max_messages=100)
        
        # Initialize the chat prompt builder
        self.chat_prompt_builder = build_chat_prompt(
            os_fullname, shell, system_prompt_preferences
        )
        
        # Initialize enhanced input handler
        self.chat_prompt = ChatPrompt()
        
        # Session info for display
        self.session_info = self.session.get_session_info()

    def start_chat_session(self):
        """Start and manage the interactive chat session loop."""
        print_text("🧞 Code Djinn Interactive Chat", "green")
        print_text(f"Session: {self.session.session_id}", "gray")
        print_text("Type 'exit' to quit, 'clear' to clear session, 'sessions' to list all sessions", "gray")
        
        # Show session restoration info if continuing existing session
        if self.session.messages:
            message_count = len([m for m in self.session.messages if m['role'] in ['user', 'assistant']])
            print_text(f"Restored session with {message_count} previous messages", "yellow")

        while True:
            try:
                # Enhanced prompt showing current directory and session
                current_dir = os.path.basename(os.getcwd())
                session_short = self.session.session_id.split('_')[-1] if '_' in self.session.session_id else self.session.session_id[:8]
                
                user_input = self.chat_prompt.get_input(f"\n[{current_dir}|{session_short}]> ")

                if user_input.lower() == "exit":
                    print_text(f"\nSession {self.session.session_id} saved", "green")
                    break
                elif user_input.lower() == "clear":
                    self.session.clear_session()
                    print_text("Session cleared", "yellow")
                    continue
                elif user_input.lower() == "sessions":
                    self._list_sessions()
                    continue
                elif user_input.lower().startswith("load "):
                    session_id = user_input[5:].strip()
                    self._load_session(session_id)
                    continue

                if user_input:  # Only process non-empty input
                    self._process_input(user_input)

            except KeyboardInterrupt:
                print_text(f"\n\nSession {self.session.session_id} saved. Goodbye! 👋", "green")
                break
            except EOFError:
                # Handle EOF gracefully - could be from subprocess pager exit
                print_text(f"\nSession {self.session.session_id} saved", "green")
                break
            except Exception as e:
                # Handle any unexpected signals from subprocess commands
                print_text(f"\nUnexpected error: {e}", "red")
                print_text("Continuing chat session...", "yellow")
                continue

    def _process_input(self, user_input: str):
        """Process user input and generate appropriate response using session context."""
        # Add user input to session
        self.session.add_message('user', user_input)
        
        # Build context-aware prompt using session history
        context = self.session.get_context_for_prompt(max_context_messages=16)
        current_dir = os.getcwd()

        chat_prompt = self.chat_prompt_builder.format(
            current_dir=current_dir, context=context, user_input=user_input
        )

        try:
            # Apply provider parameters for consistent LLM behavior
            self.parameter_manager.apply_parameters(
                self.llm, self.provider, explain=False
            )

            # Single LLM call for both classification and response
            response = self.llm.invoke(chat_prompt)
            response_text = (
                response.content if hasattr(response, "content") else str(response)
            )

            # Parse using enhanced parser
            parsed = ResponseParser.parse_chat_response(response_text)

            # Handle response and add to session
            self._handle_response(parsed, user_input)

        except Exception as e:
            error_msg = f"Error: {str(e)}"
            print_text(error_msg, "red")
            # Log errors to session for context
            self.session.add_message('system', error_msg, {'type': 'error'})

    def _handle_response(self, parsed: dict, user_input: str):
        """Handle model response by displaying output and storing in session."""
        
        if parsed["type"] == "answer":
            # Pure conversational response
            print_text(f"\n{parsed['answer']}", "blue")
            self.session.add_message('assistant', parsed['answer'])

        elif parsed["type"] in ["command", "both"]:
            # Prepare assistant response for session
            assistant_response = ""
            
            # Show the unified answer (which includes explanation)
            if parsed["answer"]:
                print_text(f"\n{parsed['answer']}", "blue")
                assistant_response += parsed['answer'] + "\n\n"

            # Show command
            print_text(f"\n{parsed['command']}", "cyan")
            assistant_response += f"Command: {parsed['command']}"

            # Add assistant response to session before execution
            self.session.add_message('assistant', assistant_response)

            # Execute with confirmation and capture output
            self._execute_with_confirmation_and_capture(parsed["command"])

    def _execute_with_confirmation_and_capture(self, command: str):
        """Execute command with user confirmation and capture results in session."""
        is_dangerous = self.executor._is_dangerous_command(command)

        if is_dangerous:
            print_text("⚠️  Potentially dangerous command", "yellow")
            response = self.chat_prompt.get_confirmation(
                "Type 'YES' to execute or Enter to cancel: ", dangerous=True
            )
            if response != "YES":
                print_text("Command cancelled", "yellow")
                self.session.add_message(
                    'system', 
                    f"Command cancelled by user: {command}", 
                    {'type': 'command_cancelled', 'command': command}
                )
                return
        else:
            response = self.chat_prompt.get_confirmation(
                "Execute? (enter to confirm or type n/no to cancel): "
            )
            if response.lower() in ["n", "no"]:
                print_text("Command cancelled", "yellow")
                self.session.add_message(
                    'system', 
                    f"Command cancelled by user: {command}", 
                    {'type': 'command_cancelled', 'command': command}
                )
                return

        # Execute and capture output
        success, stdout, stderr = self.executor.execute_with_confirmation(
            command, None, auto_confirm=True, verbose=False, quiet=True
        )

        # Show execution result
        result = "✓ Done" if success else "✗ Failed"
        print_text(result, "green" if success else "red")

        # Capture command execution in session for context
        self.session.add_command_execution(command, success, stdout or "", stderr or "")

    def _list_sessions(self):
        """List all available sessions."""
        sessions = self.session.list_sessions()
        if sessions:
            print_text("\nAvailable sessions:", "yellow")
            for session_id in sessions:
                current = " (current)" if session_id == self.session.session_id else ""
                print_text(f"  {session_id}{current}", "gray")
            print_text(f"\nUse 'load <session_id>' to switch sessions", "gray")
        else:
            print_text("No saved sessions found", "yellow")

    def _load_session(self, session_id: str):
        """Load and switch to a different chat session."""
        try:
            # Create new session instance
            new_session = ChatSession(session_id)
            
            # Switch to new session
            old_session_id = self.session.session_id
            self.session = new_session
            self.session_info = new_session.get_session_info()
            
            message_count = len([m for m in self.session.messages if m['role'] in ['user', 'assistant']])
            print_text(f"Switched to session: {session_id}", "green")
            if message_count > 0:
                print_text(f"Loaded {message_count} previous messages", "yellow")
            else:
                print_text("Started new session", "yellow")
                
        except Exception as e:
            print_text(f"Error loading session {session_id}: {e}", "red")

    def get_session_summary(self) -> dict:
        """Get summary information about the current session."""
        return {
            'session_id': self.session.session_id,
            'message_count': len(self.session.messages),
            'user_messages': len([m for m in self.session.messages if m['role'] == 'user']),
            'assistant_messages': len([m for m in self.session.messages if m['role'] == 'assistant']),
            'command_executions': len([m for m in self.session.messages 
                                     if m.get('metadata', {}).get('type') == 'command_execution']),
            'session_file_exists': self.session.session_file.exists()
        }