"""Mistral-based agent using native tool calling API."""

import json
from mistralai import Mistral

from codedjinn.core.agent import Agent
from codedjinn.tools.registry import build_mistral_tool_schema
from codedjinn.prompts.system_prompt import build_system_prompt


class MistralAgent(Agent):
    """
    Agent implementation using Mistral's native tool calling.

    This implementation bypasses heavy frameworks (like Agno) and calls
    the Mistral API directly for maximum speed. Benchmarks show ~274ms
    mean latency for tool calling, making this approach ideal for
    single-command requests.
    """

    def __init__(self, api_key: str, model: str):
        """
        Initialize Mistral agent.

        Args:
            api_key: Mistral API key
            model: Model name (e.g., "mistral-small-latest", "codestral-latest")
        """
        self.client = Mistral(api_key=api_key)
        self.model = model

    def generate_command(self, query: str, context: dict) -> str:
        """
        Generate command using Mistral native tool calling.

        Flow:
        1. Build tool schema with OS/shell context (delegate to registry)
        2. Build system prompt with context
        3. Call Mistral API with tools + tool_choice="any"
        4. Extract command from tool call response

        This bypasses text parsing entirely - Mistral returns structured
        JSON with the command in a predictable location.
        """
        # Build tool schema (delegates to tools/registry.py)
        tools = self._get_tool_schema(context)

        # Build system prompt with context
        system_prompt = self._build_system_prompt(context)

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

    def _build_system_prompt(self, context: dict) -> str:
        """
        Build minimal system prompt with execution context.

        Delegates to prompts/system_prompt.py for easy iteration on prompts.
        """
        return build_system_prompt(
            os_name=context['os_name'],
            shell=context['shell'],
            cwd=str(context['cwd'])
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
