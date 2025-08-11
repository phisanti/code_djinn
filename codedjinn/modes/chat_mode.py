from typing import Optional
from .base_mode import BaseMode
from ..core.command_executor import CommandExecutor
from ..core.response_parser import ResponseParser
from ..core.prompt_builder import build_chat_prompt
from ..utils import print_text
import os
import time


class ChatMode(BaseMode):
    """
    Enhanced chat mode with model-driven classification and session persistence.
    Inherits command generation capabilities from BaseMode.
    """

    def __init__(
        self,
        llm_instance,
        provider: str,
        os_fullname: str,
        shell: str,
        system_prompt_preferences: str = "",
        shell_path: str = "",
    ):
        super().__init__(
            llm_instance, provider, os_fullname, shell, system_prompt_preferences
        )
        self.executor = CommandExecutor(shell, shell_path)
        self.conversation_context = []  # Simple context storage
        self.max_context = 10  # Keep conversation manageable for speed
        # Initialize the chat prompt builder
        self.chat_prompt_builder = build_chat_prompt(
            os_fullname, shell, system_prompt_preferences
        )

    def start_chat_session(self):
        """Main chat loop - enhanced UX with directory context."""
        print_text("🧞 Code Djinn Chat Mode \n", "green")
        print_text("Type 'exit' to quit, 'clear' to clear context", "gray")

        while True:
            try:
                # Enhanced prompt showing current directory
                current_dir = os.path.basename(os.getcwd())
                user_input = input(f"\n[{current_dir}]> ").strip()

                if user_input.lower() == "exit":
                    break
                elif user_input.lower() == "clear":
                    self.conversation_context.clear()
                    print_text("Context cleared", "yellow")
                    continue

                if user_input:  # Only process non-empty input
                    self._process_input(user_input)

            except KeyboardInterrupt:
                print_text("\n\nGoodbye! 👋", "green")
                break
            except EOFError:
                break

    def _process_input(self, user_input: str):
        """Process input using model-driven classification."""
        # Build context-aware prompt for model classification using centralized builder
        context = self._get_conversation_context()
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

            # Handle response based on model's classification
            self._handle_response(parsed, user_input)

        except Exception as e:
            print_text(f"Error: {str(e)}", "red")

    def _get_conversation_context(self) -> str:
        """Get formatted recent conversation for context."""
        if not self.conversation_context:
            return "No previous conversation."

        # Last few exchanges for context
        recent = self.conversation_context[-8:]
        return "\n".join(recent)

    def _handle_response(self, parsed: dict, user_input: str):
        """Handle model response based on classification."""
        # Add user input to context
        self.conversation_context.append(f"User: {user_input}")

        if parsed["type"] == "answer":
            # Pure conversational response
            print_text(f"\n{parsed['answer']}", "blue")
            self.conversation_context.append(f"Assistant: {parsed['answer']}")

        elif parsed["type"] in ["command", "both"]:
            # Show any conversational part first
            if parsed["answer"]:
                print_text(f"\n{parsed['answer']}", "blue")

            # Show command
            print_text(f"\n{parsed['command']}", "cyan")
            if parsed["description"]:
                print_text(f"\n   {parsed['description']} \n", "pink")

            # Execute with confirmation
            self._execute_with_confirmation(parsed["command"], parsed["description"])

            # Update context
            context_entry = (
                parsed["answer"] if parsed["answer"] else "[generated command]"
            )
            self.conversation_context.append(f"Assistant: {context_entry}")

        # Trim context to maintain performance - keep pairs of exchanges
        # Each exchange is User: + Assistant:, so keep even number of entries
        while len(self.conversation_context) > self.max_context:
            # Remove the oldest exchange (2 entries)
            self.conversation_context.pop(0)
            if self.conversation_context and not self.conversation_context[
                0
            ].startswith("User:"):
                # Ensure we maintain User/Assistant pairing
                self.conversation_context.pop(0)

    def _execute_with_confirmation(self, command: str, description: str = None):
        """Execute command with smart confirmation based on safety."""
        is_dangerous = self.executor._is_dangerous_command(command)

        if is_dangerous:
            print_text("⚠️  Potentially dangerous command", "yellow")
            response = input("Type 'YES' to execute or Enter to cancel: ").strip()
            if response != "YES":
                print_text("Command cancelled", "yellow")
                return
        else:
            response = (
                input("Execute? (enter to confirm or type n/no to cancel): ")
                .strip()
                .lower()
            )
            if response in ["n", "no"]:
                print_text("Command cancelled", "yellow")
                return

        # Execute using existing safe executor with quiet mode for clean UX
        success, _, _ = self.executor.execute_with_confirmation(
            command, description, auto_confirm=True, verbose=False, quiet=True
        )

        result = "✓ Done" if success else "✗ Failed"
        print_text(result, "green" if success else "red")
        self.conversation_context.append(f"Command: {command} - {result}")
