"""Mistral-based agent using native tool calling API."""

import json
from typing import Optional, TYPE_CHECKING

from codedjinn.core.agent import Agent
from codedjinn.core.client_cache import get_cached_client
from codedjinn.tools.registry import build_mistral_tool_schema, build_ask_tool_schema
from codedjinn.tools.ask_executor import AskToolExecutor
from codedjinn.tools.observe_executor import ObserveExecutor
from codedjinn.context import (
    build_prompt,
    init_session_state_for_steps,
    advance_step_budget,
    refresh_step_context,
)

if TYPE_CHECKING:
    from mistralai import Mistral


class MistralAgent(Agent):
    """
    Mistral-native agent implementation without langchain overhead.

    Performance-focused design with three initialization paths:
    1. Daemon mode: Use pre-initialized client (fastest, ~0ms overhead)
    2. Direct with cache: Reuse HTTP connections (~50-100ms overhead)
    3. Testing mode: Fresh client each time (slowest, for tests only)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "mistral-small-latest",
        use_cache: bool = True,
        client: Optional["Mistral"] = None
    ):
        """
        Initialize Mistral agent.

        Args:
            api_key: Mistral API key (required if client not provided)
            model: Model identifier (default: mistral-small-latest)
            use_cache: Use client caching for performance (default: True)
            client: Pre-initialized Mistral client (for daemon mode)
        """
        self.model = model

        if client:
            # Daemon mode: use pre-initialized client (fastest)
            self.client = client
        elif use_cache:
            # Direct mode with caching (medium speed)
            self.client = get_cached_client(api_key, model)
        else:
            # Testing mode: fresh client (slowest)
            from mistralai import Mistral
            self.client = Mistral(api_key=api_key)

    def generate_command(
        self,
        query: str,
        context: dict,
        previous_context: dict = None
    ) -> str:
        """
        Generate shell command for user query (run mode).

        Single-shot mode: query → command in one LLM call.
        Uses forced tool calling to ensure structured output.

        Args:
            query: Natural language request for command
            context: Execution context {cwd, os_name, shell}
            previous_context: Optional previous command context

        Returns:
            Shell command string
        """
        # Build system prompt with full context
        system_prompt = self._build_system_prompt(context, previous_context)

        # Get tool schema for shell execution
        tools = self._get_tool_schema(context)

        # Single LLM call with forced tool use
        response = self.client.chat.complete(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ],
            tools=tools,
            tool_choice="any",  # Force tool call
            temperature=0.3,
            max_tokens=500,
        )

        # Extract command from tool call
        tool_call = response.choices[0].message.tool_calls[0]
        arguments = json.loads(tool_call.function.arguments)
        command = arguments["command"]

        return command

    def analyze(
        self,
        question: str,
        context: dict,
        previous_context: dict = None,
        max_steps: int = 1,
        conversation_history: list = None
    ) -> dict:
        """
        Analyze previous output and answer a question (ask mode).

        Unified method supporting single-shot and multi-step reasoning:
        - max_steps=1: Single tool call with immediate follow-up
        - max_steps>1: Multi-step with conversation history preservation

        The model can:
        1. Read files for context (read_file)
        2. Execute safe observation commands (execute_observe_command)
        3. Synthesize answers using finish_reasoning (multi-step only)
        4. Use plain text generation without tools

        Args:
            question: User's question to answer
            context: Execution context (cwd, os_name, shell)
            previous_context: Optional dict with previous command/output
            max_steps: Maximum reasoning steps (1=single-shot, >1=multi-step)
            conversation_history: Optional list of previous exchanges

        Returns:
            Dict with 'answer' and 'tool_calls' for accountability.
        """
        # Single-shot mode: use legacy implementation for now
        # (will be refactored separately to use new pattern)
        if max_steps == 1:
            return self._analyze_single_shot(
                question, context, previous_context, conversation_history
            )

        # Multi-step mode: NEW implementation with full conversation history
        return self._analyze_multi_step(
            question, context, previous_context, max_steps, conversation_history
        )

    def _analyze_single_shot(
        self,
        question: str,
        context: dict,
        previous_context: dict = None,
        conversation_history: list = None
    ) -> dict:
        """
        Single-shot ask mode: one tool call, immediate follow-up for answer.

        Legacy implementation maintained for compatibility and performance.
        """
        file_executor = AskToolExecutor(cwd=str(context['cwd']))
        observe_executor = ObserveExecutor(cwd=str(context['cwd']))
        tool_calls_executed = []

        # Build system prompt
        system_prompt = self._build_ask_system_prompt(context, previous_context)

        # Initial query with forced tool use
        response = self.client.chat.complete(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question},
            ],
            tools=self._get_ask_tools(),
            tool_choice="any",  # Force tool use
            temperature=0.3,
            max_tokens=1500,
        )

        message = response.choices[0].message

        # Execute tool and follow up for answer
        if hasattr(message, 'tool_calls') and message.tool_calls:
            for tool_call in message.tool_calls:
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)

                if tool_name == "read_file":
                    path = tool_args.get("path", "")
                    context_str = tool_args.get("context", "")
                    file_content = file_executor.execute_read_file(path)

                    # Track for accountability
                    tool_calls_executed.append({
                        'tool': 'read_file',
                        'path': path,
                        'context': context_str,
                        'output': file_content[:200] + "..." if len(file_content) > 200 else file_content
                    })

                    # Follow-up call for answer
                    message = self._follow_up_with_tool_result(
                        system_prompt, question, tool_call, file_content
                    )
                    break

                elif tool_name == "execute_observe_command":
                    command = tool_args.get("command", "")
                    context_str = tool_args.get("context", "")
                    command_output = observe_executor.execute_observe_command(command)

                    # Track for accountability
                    tool_calls_executed.append({
                        'tool': 'execute_observe_command',
                        'command': command,
                        'context': context_str,
                        'output': command_output[:200] + "..." if len(command_output) > 200 else command_output
                    })

                    # Follow-up call for answer
                    message = self._follow_up_with_tool_result(
                        system_prompt, question, tool_call, command_output
                    )
                    break

        # Extract answer
        content = getattr(message, "content", "")
        if isinstance(content, list):
            answer = "\n".join(str(part) for part in content).strip()
        else:
            answer = ("" if content is None else str(content)).strip()

        return {"answer": answer, "tool_calls": tool_calls_executed}

    def _analyze_multi_step(
        self,
        question: str,
        context: dict,
        previous_context: dict = None,
        max_steps: int = 3,
        conversation_history: list = None
    ) -> dict:
        """
        Multi-step ask mode: maintain full conversation history across steps.

        NEW IMPLEMENTATION: Preserves full message array with assistant responses
        and tool results. System prompt built once, step metadata added as user
        messages. This follows Mistral API's intended multi-turn pattern.

        Design:
        1. Build base system prompt once (includes all context)
        2. Initialize messages with [system, user]
        3. For each step:
           - Call LLM with accumulated messages
           - Append assistant response with tool_calls
           - Execute tools, append tool results
           - Add step context as user message for next iteration
        4. Return final answer with full tool call history
        """
        file_executor = AskToolExecutor(cwd=str(context['cwd']))
        observe_executor = ObserveExecutor(cwd=str(context['cwd']))
        tool_calls_executed = []

        # Initialize step budget tracking
        session_state = init_session_state_for_steps(max_steps)

        # Build base system prompt ONCE (includes all context)
        # This is set at the beginning and NOT rebuilt on each iteration
        system_prompt = self._build_ask_step_prompt(
            question=question,
            step_number=1,
            max_steps=max_steps,
            prior_observations=[],  # Empty for first step
            context=context,
            previous_context=previous_context,
            conversation_history=conversation_history
        )

        # Initialize messages array with system + user
        # This array will grow as we accumulate conversation history
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question},
        ]

        # Multi-step reasoning loop
        for step_num in range(1, max_steps + 1):
            refresh_step_context(session_state)

            # If not first step, add step context as user message
            # This provides progress updates without rebuilding the entire system prompt
            if step_num > 1:
                remaining = max_steps - step_num + 1

                if step_num >= max_steps:
                    # Final step urgency
                    step_context = (
                        f"⚠️ FINAL STEP ({step_num}/{max_steps}) - THIS IS YOUR LAST CHANCE\n"
                        f"You have reached the absolute final step. NO MORE STEPS REMAIN after this.\n"
                        f"IMMEDIATELY use finish_reasoning to provide your final answer.\n"
                        f"Do not perform additional reads. Synthesize your answer from all gathered evidence."
                    )
                elif remaining <= 1:
                    # Almost done
                    step_context = (
                        f"⚠️ ALMOST DONE (step {step_num} of {max_steps}) - RUSH TO FINISH\n"
                        f"You have only {remaining} step remaining after this one.\n"
                        f"Please wrap up your investigation and prepare to call finish_reasoning.\n"
                        f"Gather any final critical information and prepare your final answer."
                    )
                elif remaining <= 2:
                    # Getting close
                    step_context = (
                        f"Getting close (step {step_num} of {max_steps}) - Start planning conclusion\n"
                        f"You have {remaining} step(s) remaining. Plan to finish_reasoning within the next step or two.\n"
                        f"Continue gathering evidence but keep your final synthesis in mind."
                    )
                else:
                    # Plenty of time
                    step_context = (
                        f"Step {step_num} of {max_steps} - {remaining} step(s) remaining\n"
                        f"Continue investigating systematically. You have plenty of steps remaining to be thorough."
                    )

                messages.append({"role": "user", "content": step_context})

            # Call LLM with accumulated conversation history
            response = self.client.chat.complete(
                model=self.model,
                messages=messages,  # Full conversation history
                tools=self._get_ask_tools(),
                tool_choice="auto",  # Model decides when to use tools
                temperature=0.3,
                max_tokens=1500,
            )

            assistant_message = response.choices[0].message

            # Check if model used tools
            if hasattr(assistant_message, 'tool_calls') and assistant_message.tool_calls:
                # Append assistant message with tool calls to conversation
                messages.append({
                    "role": "assistant",
                    "content": getattr(assistant_message, "content", "") or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
                        }
                        for tc in assistant_message.tool_calls
                    ]
                })

                # Process each tool call
                for tool_call in assistant_message.tool_calls:
                    tool_name = tool_call.function.name
                    tool_args = json.loads(tool_call.function.arguments)

                    if tool_name == "finish_reasoning":
                        # Model is ready to provide final answer
                        answer = tool_args.get("answer", "").strip()
                        return {"answer": answer, "tool_calls": tool_calls_executed}

                    elif tool_name == "read_file":
                        path = tool_args.get("path", "")
                        context_str = tool_args.get("context", "")
                        file_content = file_executor.execute_read_file(path)

                        # Track for accountability
                        tool_calls_executed.append({
                            'tool': 'read_file',
                            'path': path,
                            'context': context_str,
                            'output': file_content[:200] + "..." if len(file_content) > 200 else file_content
                        })

                        # Append tool result to conversation (FULL content, no truncation)
                        messages.append({
                            "role": "tool",
                            "content": file_content,
                            "tool_call_id": tool_call.id
                        })

                    elif tool_name == "execute_observe_command":
                        command = tool_args.get("command", "")
                        context_str = tool_args.get("context", "")
                        command_output = observe_executor.execute_observe_command(command)

                        # Track for accountability
                        tool_calls_executed.append({
                            'tool': 'execute_observe_command',
                            'command': command,
                            'context': context_str,
                            'output': command_output[:200] + "..." if len(command_output) > 200 else command_output
                        })

                        # Append tool result to conversation (FULL content, no truncation)
                        messages.append({
                            "role": "tool",
                            "content": command_output,
                            "tool_call_id": tool_call.id
                        })

            else:
                # No tool calls - model provided direct text response
                # This is the final answer
                content = getattr(assistant_message, "content", "")
                if isinstance(content, list):
                    answer = "\n".join(str(part) for part in content).strip()
                else:
                    answer = ("" if content is None else str(content)).strip()

                return {"answer": answer, "tool_calls": tool_calls_executed}

            # Advance step budget for next iteration
            advance_step_budget(session_state)

        # Steps exhausted without explicit finish_reasoning or text response
        # Try to extract answer from last assistant message
        if messages and messages[-1]["role"] == "assistant":
            content = messages[-1].get("content", "")
            answer = content.strip() if content else ""
        else:
            answer = ""

        # If still no answer, synthesize from tool results
        if not answer and tool_calls_executed:
            answer = self._synthesize_from_tool_calls(question, tool_calls_executed)

        return {"answer": answer, "tool_calls": tool_calls_executed}

    def _synthesize_from_tool_calls(self, question: str, tool_calls: list) -> str:
        """
        Fallback synthesis when steps exhausted without explicit answer.

        Args:
            question: Original question
            tool_calls: List of executed tool calls with results

        Returns:
            Synthesized answer
        """
        # Format tool results
        evidence = []
        for i, tc in enumerate(tool_calls, 1):
            tool = tc.get('tool', 'unknown')
            if tool == 'read_file':
                path = tc.get('path', '')
                output = tc.get('output', '')
                evidence.append(f"{i}. Read {path}:\n{output}\n")
            elif tool == 'execute_observe_command':
                command = tc.get('command', '')
                output = tc.get('output', '')
                evidence.append(f"{i}. Executed `{command}`:\n{output}\n")

        evidence_text = "\n".join(evidence)

        # Make synthesis call
        synthesis_prompt = f"""You are Code Djinn. Based on the gathered information below,
provide a clear, concise answer to the original question.

Original question: {question}

Gathered information:
{evidence_text}

Please provide your answer based on this evidence."""

        try:
            response = self.client.chat.complete(
                model=self.model,
                messages=[
                    {"role": "user", "content": synthesis_prompt}
                ],
                temperature=0.3,
                max_tokens=1000,
            )

            content = response.choices[0].message.content
            return content.strip() if content else "Unable to synthesize answer from gathered evidence."

        except Exception:
            # If synthesis fails, return formatted evidence
            return f"Based on the investigation:\n\n{evidence_text}"

    def _follow_up_with_tool_result(
        self,
        system_prompt: str,
        question: str,
        tool_call,
        tool_result: str
    ):
        """
        Make follow-up call with tool result to get model's answer (single-shot mode).

        Constructs a proper message chain with assistant tool call and tool result,
        then adds explicit user prompt to force text response instead of additional
        tool calls.
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [tool_call]
            },
            {
                "role": "tool",
                "content": tool_result,
                "tool_call_id": tool_call.id
            },
            {
                "role": "user",
                "content": "Based on the output above, please provide your answer to my question. Do not make any additional tool calls."
            }
        ]

        response = self.client.chat.complete(
            model=self.model,
            messages=messages,
            temperature=0.3,
            max_tokens=1500,
        )

        return response.choices[0].message

    def analyze_with_steps(
        self,
        question: str,
        context: dict,
        max_steps: int = 3,
        previous_context: dict = None,
        conversation_history: list = None
    ) -> str:
        """
        DEPRECATED: Use analyze(max_steps=N) instead.

        This method is kept for backwards compatibility but delegates to
        the unified analyze() method.
        """
        result = self.analyze(
            question=question,
            context=context,
            previous_context=previous_context,
            max_steps=max_steps,
            conversation_history=conversation_history
        )
        return result["answer"]

    def _build_system_prompt(self, context: dict, previous_context: dict = None) -> str:
        """Build system prompt for run mode."""
        return build_prompt(
            mode="run",
            os_name=context['os_name'],
            shell=context['shell'],
            cwd=str(context['cwd']),
            session_context=previous_context,
        )

    def _build_ask_system_prompt(self, context: dict, previous_context: dict = None) -> str:
        """Build system prompt for ask mode (single-shot)."""
        return build_prompt(
            mode="ask",
            os_name=context['os_name'],
            shell=context['shell'],
            cwd=str(context['cwd']),
            session_context=previous_context,
        )

    def _build_ask_step_prompt(
        self,
        question: str,
        step_number: int,
        max_steps: int,
        prior_observations: list,
        context: dict,
        previous_context: dict = None,
        conversation_history: list = None
    ) -> str:
        """
        Build prompt for multi-step reasoning (base prompt only, step context added via messages).

        Uses existing context infrastructure for consistency with run/ask modes.
        Includes base context, conversation history, and multi-step instructions.
        Step-specific metadata is NOT included here - it's added as user messages.

        Args:
            question: The original question
            step_number: Current step (used for initial observations check)
            max_steps: Total available steps
            prior_observations: Not used in new implementation (context in messages)
            context: Execution context (cwd, os_name, shell)
            previous_context: Optional previous command context
            conversation_history: Optional conversation history

        Returns:
            Base system prompt for multi-step reasoning
        """
        from codedjinn.context import contextualise, build_ask_prompt

        # Use existing context infrastructure
        ctx = contextualise(
            os_name=context['os_name'],
            shell=context['shell'],
            cwd=str(context['cwd']),
            session_context=previous_context,
        )

        # Start with base ask prompt
        base_prompt = build_ask_prompt(ctx)

        # Build multi-step specific sections
        sections = [base_prompt]

        # Conversation history section
        if conversation_history:
            sections.append(self._format_conversation_history_xml(conversation_history))

        # Multi-step reasoning context
        sections.append(f"""<multi_step_reasoning>
Original question: {question}
Mode: Multi-step reasoning with up to {max_steps} steps
Progress tracking: Step context will be provided as the conversation progresses
</multi_step_reasoning>""")

        # Tool instructions for multi-step
        sections.append("""<multi_step_instructions>
- Use read_file to gather context when needed for a better answer
- Use execute_observe_command to run safe observation commands
- When you have enough information, use finish_reasoning to provide final answer
- You can stop early if you've reached a conclusion before using all steps
- Each step should build on previous findings in the conversation
- Stay focused on answering the original question
- You can reference previous commands in conversation_history for additional context
</multi_step_instructions>""")

        return "\n".join(sections)

    def _format_conversation_history_xml(self, conversation_history: list) -> str:
        """
        Format conversation history into XML section for prompt.

        Args:
            conversation_history: List of dicts with 'command', 'output', 'exit_code'

        Returns:
            XML-formatted conversation history section
        """
        if not conversation_history:
            return ""

        lines = ["<conversation_history>"]
        lines.append("  <!-- Previous commands from this session -->")

        for i, exchange in enumerate(conversation_history, 1):
            command = exchange.get('command', '')
            output = exchange.get('output', '')
            exit_code = exchange.get('exit_code', 0)

            # Escape XML special characters
            command = command.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            output = output.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

            lines.append(f"  <exchange number=\"{i}\">")
            lines.append(f"    <command>{command}</command>")
            lines.append(f"    <exit_code>{exit_code}</exit_code>")
            lines.append(f"    <output>{output}</output>")
            lines.append(f"  </exchange>")

        lines.append("</conversation_history>")
        return "\n".join(lines)

    def _get_tool_schema(self, context: dict) -> list[dict]:
        """Get tool schema for run mode (delegates to registry)."""
        return build_mistral_tool_schema(
            os_name=context['os_name'],
            shell=context['shell']
        )

    def _get_ask_tools(self) -> list[dict]:
        """Get tool schema for ask mode (delegates to registry)."""
        return build_ask_tool_schema()

    def generate_with_steps(self, query: str, context: dict, max_steps: int) -> list[str]:
        """
        NOT IMPLEMENTED: Multi-step command generation.

        Phase 1 does not support multi-step agentic command generation.
        Use generate_command() for single-shot commands.

        Raises:
            NotImplementedError: Always (not supported in Phase 1)
        """
        raise NotImplementedError(
            "Multi-step command generation not supported in Phase 1. "
            "Use generate_command() for single-shot commands."
        )
