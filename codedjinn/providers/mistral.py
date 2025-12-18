"""Mistral-based agent using native tool calling API."""

import json

from codedjinn.core.agent import Agent
from codedjinn.core.client_cache import get_cached_client
from codedjinn.tools.registry import build_mistral_tool_schema
from codedjinn.prompts.ask_prompt import build_ask_system_prompt
from codedjinn.prompts.system_prompt import build_system_prompt
from codedjinn.prompts.context_builder import get_context_detector


class MistralAgent(Agent):
    """
    Agent implementation using Mistral's native tool calling.

    This implementation bypasses heavy frameworks (like Agno) and calls
    the Mistral API directly for maximum speed. Uses HTTP connection
    pooling via client caching for optimal performance.

    Performance optimizations:
    - Native Mistral SDK (no framework overhead)
    - HTTP connection pooling (reuses connections)
    - Minimal system prompts (fast processing)
    - Structured tool calling (no parsing)
    """

    def __init__(self, api_key: str, model: str, use_cache: bool = True):
        """
        Initialize Mistral agent.

        Args:
            api_key: Mistral API key
            model: Model name (e.g., "mistral-small-latest", "codestral-latest")
            use_cache: Use cached client for connection pooling (default: True)

        Performance:
            - use_cache=True: Reuses HTTP connections (~50-100ms faster)
            - use_cache=False: Creates new client each time (testing only)
        """
        if use_cache:
            self.client = get_cached_client(api_key, model)
        else:
            # Only for testing - creates new client without caching
            from mistralai import Mistral
            self.client = Mistral(api_key=api_key)

        self.model = model

        # Get singleton context detector for smart context detection
        self.context_detector = get_context_detector()

    def generate_command(self, query: str, context: dict, previous_context: dict = None) -> str:
        """
        Generate command using Mistral native tool calling.

        NOW WITH CONTEXT: If previous_context is provided, includes
        it in the system prompt so the model can reference the
        previous command and output.

        Args:
            query: User's natural language request
            context: Execution context (cwd, os_name, shell)
            previous_context: Optional dict from Session.get_context_for_prompt()
                Contains: command, output, exit_code

        Returns:
            Shell command string

        Flow:
        1. Build tool schema with OS/shell context (delegate to registry)
        2. Build system prompt with optional previous context
        3. Call Mistral API with tools + tool_choice="any"
        4. Extract command from tool call response

        This bypasses text parsing entirely - Mistral returns structured
        JSON with the command in a predictable location.

        Example:
            >>> agent = MistralAgent(api_key, model)
            >>>
            >>> # First command (no context)
            >>> cmd1 = agent.generate_command("list files", context)
            >>>
            >>> # Follow-up command (with context)
            >>> prev = {'command': 'ls', 'output': 'file1.txt\\nfile2.txt', 'exit_code': 0}
            >>> cmd2 = agent.generate_command("show details of file1", context, prev)
        """
        # Build tool schema (delegates to tools/registry.py)
        tools = self._get_tool_schema(context)

        # Build system prompt with optional previous context
        system_prompt = self._build_system_prompt(context, previous_context)

        # Call Mistral with native tool calling
        response = self.client.chat.complete(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ],
            tools=tools,
            tool_choice="any"  # Force tool call (no text response)
        )

        # Extract command from tool call
        # Structure: response.choices[0].message.tool_calls[0].function.arguments
        tool_call = response.choices[0].message.tool_calls[0]
        arguments = json.loads(tool_call.function.arguments)

        return arguments["command"]

    def analyze(self, question: str, context: dict, previous_context: dict = None) -> str:
        """
        Analyze the previous command output and answer a question (ask mode).

        This uses plain text generation (no tool calling) and does not execute
        any commands. If previous_context is not provided, the model will
        answer without command output context.
        """
        system_prompt = self._build_ask_system_prompt(context, previous_context)

        response = self.client.chat.complete(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question},
            ],
            temperature=0.3,
            max_tokens=1500,
        )

        message = response.choices[0].message
        content = getattr(message, "content", "")

        if isinstance(content, list):
            return "\n".join(str(part) for part in content).strip()

        return ("" if content is None else str(content)).strip()

    def _get_tool_schema(self, context: dict) -> list[dict]:
        """
        Get Mistral tool schema from registry.

        Delegates the bulk of schema building to tools/registry.py
        to keep this module focused on API interaction.
        """
        return build_mistral_tool_schema(
            os_name=context['os_name'],
            shell=context['shell']
        )

    def _build_system_prompt(self, context: dict, previous_context: dict = None) -> str:
        """
        Build minimal system prompt with execution context.

        NOW WITH CONTEXT: If previous_context is provided, passes it through
        to the prompt builder so it can include command history in the prompt.

        NOW WITH SMART CONTEXT: Automatically detects project context and
        includes it in the prompt for better command generation.

        Delegates to prompts/system_prompt.py for easy iteration on prompts.
        """
        # Detect smart context from current working directory
        smart_ctx = self.context_detector.get_context(str(context['cwd']))

        return build_system_prompt(
            os_name=context['os_name'],
            shell=context['shell'],
            cwd=str(context['cwd']),
            previous_context=previous_context,
            smart_context=smart_ctx  # NEW: pass smart context
        )

    def _build_ask_system_prompt(self, context: dict, previous_context: dict = None) -> str:
        """
        Build ask-mode system prompt with optional previous command context.

        Delegates to prompts/ask_prompt.py to keep provider code focused on
        API interaction.
        """
        return build_ask_system_prompt(
            os_name=context["os_name"],
            shell=context["shell"],
            cwd=str(context["cwd"]),
            previous_context=previous_context,
        )

    def generate_with_steps(self, query: str, context: dict, max_steps: int) -> list[str]:
        """
        Multi-step execution - NOT IMPLEMENTED IN PHASE 1.

        TODO: Implement multi-step execution in Phase 2:
        - Option A: Allow N sequential tool calls in one request
        - Option B: Conversation loop (call → execute → observe → repeat)

        For now, focus on blazing fast single-command execution.
        """
        raise NotImplementedError(
            "Multi-step execution not implemented in Phase 1. "
            "Use --steps 0 for single-command mode."
        )
