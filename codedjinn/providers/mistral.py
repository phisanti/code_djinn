"""Mistral-based agent using native tool calling API."""

import json
from typing import Optional, TYPE_CHECKING

from codedjinn.core.client_cache import get_cached_client
from codedjinn.providers.ask_helpers import (
    format_observations_for_synthesis,
    format_observations_xml,
    maybe_answer_file_content_question,
)
from codedjinn.tools.registry import build_mistral_tool_schema, build_ask_tool_schema
from codedjinn.tools.ask_executor import AskToolExecutor
from codedjinn.tools.observe_executor import ObserveExecutor
from codedjinn.context import (
    build_prompt,
    build_run_prompt,
    build_ask_prompt,
    init_session_state_for_steps,
    advance_step_budget,
    refresh_step_context,
)
from codedjinn.context.parser import escape_xml_content

if TYPE_CHECKING:
    from mistralai import Mistral


class MistralAgent:
    """
    Adapter between Code Djinn workflows and Mistral chat/tool calls.

    The class owns provider-specific message construction, tool-call execution,
    and response normalization. Context collection, shell execution, and tool
    schema definitions live in neighboring modules so this file stays focused on
    the Mistral protocol.

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
        previous_context: dict = None,
        conversation_history: list = None,
        context_result=None,
    ) -> str:
        """
        Generate shell command for user query (run mode).

        Single-shot mode: query → command in one LLM call.
        Uses forced tool calling to ensure structured output.

        Args:
            query: Natural language request for command
            context: Execution context {cwd, os_name, shell}
            previous_context: Optional previous command context
            conversation_history: Optional list of previous exchanges

        Returns:
            Shell command string
        """
        # Build system prompt with full context
        system_prompt = self._build_system_prompt(
            context, previous_context, conversation_history, context_result=context_result
        )

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
        conversation_history: list = None,
        extra_commands: list = None,
        skill=None,
        context_result=None,
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
        # Exact file-content reads are deterministic and common in ask mode.
        # Handling them before model dispatch avoids latency and prevents the
        # model from hallucinating that a present file is missing.
        direct_file_answer = self._maybe_answer_file_content_question(
            question=question,
            file_executor=AskToolExecutor(cwd=str(context['cwd'])),
        )
        if direct_file_answer is not None:
            return direct_file_answer

        if max_steps == 1:
            return self._analyze_single_shot(
                question, context, previous_context, conversation_history,
                extra_commands=extra_commands, skill=skill, context_result=context_result,
            )

        return self._analyze_multi_step(
            question, context, previous_context, max_steps, conversation_history,
            extra_commands=extra_commands, skill=skill, context_result=context_result,
        )

    def _analyze_single_shot(
        self,
        question: str,
        context: dict,
        previous_context: dict = None,
        conversation_history: list = None,
        extra_commands: list = None,
        skill=None,
        context_result=None,
    ) -> dict:
        """
        Answer an ask request with at most one model-selected tool round.

        This is the default path for short questions. The model can answer from
        context directly or request one read-only tool call; if it does use a
        tool, we immediately follow up with the tool result and ask for a final
        text answer.
        """
        file_executor = AskToolExecutor(cwd=str(context['cwd']))
        observe_executor = ObserveExecutor(cwd=str(context['cwd']), extra_commands=extra_commands)
        tool_calls_executed = []

        system_prompt = self._build_ask_system_prompt(
            context, previous_context, conversation_history, skill=skill, context_result=context_result
        )

        # Let the model answer directly when context is sufficient. Tool use
        # remains available for file/repository lookup questions.
        response = self.client.chat.complete(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question},
            ],
            tools=self._get_ask_tools(),
            tool_choice="auto",
            temperature=0.3,
            max_tokens=1200,
        )

        message = response.choices[0].message

        # Single-shot mode intentionally executes only the first requested tool.
        # That keeps latency predictable for the default `ask` path; users can
        # opt into multi-step mode when a question needs iterative search.
        if hasattr(message, 'tool_calls') and message.tool_calls:
            for tool_call in message.tool_calls:
                tool_name = tool_call.function.name
                try:
                    tool_args = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError:
                    tool_args = {}

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

                elif tool_name == "finish_reasoning":
                    answer = tool_args.get("answer", "").strip()
                    return {"answer": answer, "tool_calls": tool_calls_executed}

        # Extract answer
        content = getattr(message, "content", "")
        if isinstance(content, list):
            answer = "\n".join(str(part) for part in content).strip()
        else:
            answer = ("" if content is None else str(content)).strip()

        return {"answer": answer, "tool_calls": tool_calls_executed}

    def _maybe_answer_file_content_question(self, question: str, file_executor: AskToolExecutor) -> dict | None:
        """Compatibility wrapper around the deterministic file-content helper."""
        return maybe_answer_file_content_question(question, file_executor)

    def _analyze_multi_step(
        self,
        question: str,
        context: dict,
        previous_context: dict = None,
        max_steps: int = 3,
        conversation_history: list = None,
        extra_commands: list = None,
        skill=None,
        context_result=None,
    ) -> dict:
        """
        Multi-step ask mode: maintain full conversation history across steps.

        This path preserves the full message array with assistant responses and
        tool results. The system prompt is built once, while step metadata is
        added as user messages. Rebuilding the system prompt each step would
        duplicate context and make tool-result grounding less reliable.

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
        observe_executor = ObserveExecutor(cwd=str(context['cwd']), extra_commands=extra_commands)
        tool_calls_executed = []

        # Initialize step budget tracking
        session_state = init_session_state_for_steps(max_steps)

        # Build the base prompt once. Tool results are appended as tool messages
        # so the model can ground later steps in the exact evidence it asked for.
        system_prompt = self._build_ask_step_prompt(
            question=question,
            step_number=1,
            max_steps=max_steps,
            context=context,
            previous_context=previous_context,
            conversation_history=conversation_history,
            skill=skill,
            context_result=context_result,
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

            # Step guidance is sent as user text rather than mutating the system
            # prompt. That preserves a stable instruction hierarchy while still
            # nudging the model to finish as the budget shrinks.
            remaining = max_steps - step_num + 1

            if step_num >= max_steps:
                step_context = (
                    f"Final step ({step_num}/{max_steps}). "
                    f"Use finish_reasoning with the best answer from gathered evidence."
                )
            elif remaining <= 1:
                step_context = (
                    f"Step {step_num}/{max_steps}. One step remains after this. "
                    f"Gather only critical missing evidence, then finish."
                )
            elif remaining <= 2:
                step_context = (
                    f"Step {step_num}/{max_steps}. {remaining} steps remain. "
                    f"Keep searches focused and prepare to synthesize."
                )
            elif step_num == 1:
                step_context = (
                    f"Step {step_num}/{max_steps}. Search first for broad file questions, "
                    f"then read only specific files if needed."
                )
            else:
                step_context = (
                    f"Step {step_num}/{max_steps}. {remaining} steps remain. "
                    f"Continue with the smallest useful read-only check."
                )

            messages.append({"role": "user", "content": step_context})

            # Call LLM with accumulated conversation history
            response = self.client.chat.complete(
                model=self.model,
                messages=messages,  # Full conversation history
                tools=self._get_ask_tools(),
                tool_choice="auto",  # Model decides when to use tools
                temperature=0.3,
                max_tokens=2048,
            )

            choice = response.choices[0]
            assistant_message = choice.message

            # Mistral can truncate either normal text or JSON tool arguments at
            # the token limit. Recovering partial text is better than returning
            # an empty answer after the user waited through multiple steps.
            if choice.finish_reason == "length":
                content = getattr(assistant_message, "content", "") or ""
                if isinstance(content, list):
                    content = "\n".join(str(p) for p in content)
                content = content.strip()
                # Also try to recover text from a truncated finish_reasoning call
                partial_from_tool = ""
                if hasattr(assistant_message, "tool_calls") and assistant_message.tool_calls:
                    for _tc in assistant_message.tool_calls:
                        if _tc.function.name == "finish_reasoning":
                            import re as _re
                            m = _re.search(r'"answer"\s*:\s*"(.*)', _tc.function.arguments, _re.DOTALL)
                            if m:
                                partial_from_tool = m.group(1)
                answer = partial_from_tool if len(partial_from_tool) > len(content) else content
                return {"answer": answer, "tool_calls": tool_calls_executed}

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

                # Mistral may emit evidence-gathering tools and finish_reasoning
                # in the same response. Execute evidence tools first so a final
                # answer never ignores data requested in that same turn.
                finish_call = None
                for tool_call in assistant_message.tool_calls:
                    tool_name = tool_call.function.name
                    try:
                        tool_args = json.loads(tool_call.function.arguments)
                    except json.JSONDecodeError:
                        if tool_name == "finish_reasoning":
                            # Mistral truncated the answer JSON — recover partial text
                            import re as _re
                            m = _re.search(r'"answer"\s*:\s*"(.*)', tool_call.function.arguments, _re.DOTALL)
                            partial = m.group(1) if m else tool_call.function.arguments
                            tool_args = {"answer": partial}
                        else:
                            tool_args = {}

                    if tool_name == "finish_reasoning":
                        # Defer processing until after other tools
                        finish_call = tool_args
                        continue

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

                        # Keep full tool content in the conversation. The short
                        # preview in tool_calls_executed is only for UI display.
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

                        # Keep full command output in the model context; only
                        # the user-facing accountability preview is truncated.
                        messages.append({
                            "role": "tool",
                            "content": command_output,
                            "tool_call_id": tool_call.id
                        })

                # Process finish_reasoning if it was called (after executing other tools)
                if finish_call:
                    answer = finish_call.get("answer", "").strip()
                    return {"answer": answer, "tool_calls": tool_calls_executed}

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
                max_tokens=1200,
            )

            content = response.choices[0].message.content
            return content.strip() if content else "Unable to synthesize answer from gathered evidence."

        except Exception:
            # If synthesis fails, return formatted evidence
            return f"Based on the investigation:\n\n{evidence_text}"

    def _format_observations_xml(self, observations: list) -> str:
        """Compatibility wrapper for tests/tools expecting XML observations."""
        return format_observations_xml(observations)

    def _format_observations_for_synthesis(self, observations: list) -> str:
        """Compatibility wrapper for tests/tools expecting text observations."""
        return format_observations_for_synthesis(observations)

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
                "content": "Answer the question using the tool output above. Keep it concise and do not make more tool calls."
            }
        ]

        response = self.client.chat.complete(
            model=self.model,
            messages=messages,
            temperature=0.3,
            max_tokens=1200,
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

    def _build_system_prompt(
        self,
        context: dict,
        previous_context: dict = None,
        conversation_history: list = None,
        context_result=None,
    ) -> str:
        """Build the run-mode system prompt from cached or fresh context."""
        if context_result is not None:
            # Daemon callers pass a cached ContextualiserResult so prompt
            # construction does not repeat shell history and project scans.
            base = build_run_prompt(context_result)
        else:
            base = build_prompt(
                mode="run",
                os_name=context['os_name'],
                shell=context['shell'],
                cwd=str(context['cwd']),
                session_context=previous_context,
            )
        if conversation_history:
            base += "\n\n" + self._format_conversation_history_xml(conversation_history)
        return base

    def _build_skill_xml(self, skill) -> str:
        """Render a SkillConfig as an XML block prepended to the system prompt.

        The <override> element instructs the model to follow <mandatory_protocol>
        instead of its default heuristics. Skill XML is prepended (not appended)
        so the model sees it before base ask instructions — ordering matters for
        instruction following. All dynamic fields are XML-escaped to prevent
        prompt injection. Caller must ensure skill is not None.
        """
        name = escape_xml_content(skill.name)
        title = escape_xml_content(skill.title)
        description = escape_xml_content(skill.description)
        cmd_elements = "".join(
            f"    <command>{escape_xml_content(c)}</command>\n"
            for c in skill.extra_commands
        )
        return (
            f"<active_skill>\n"
            f"  <name>{name}</name>\n"
            f"  <title>{title}</title>\n"
            f"  <steps>{skill.steps}</steps>\n"
            f"  <extra_commands>\n{cmd_elements}  </extra_commands>\n"
            f"  <override>MANDATORY: Ignore default search/investigation behavior. "
            f"You MUST follow the protocol in mandatory_protocol exactly, step by step. "
            f"Batch all independent tool calls in the same turn.</override>\n"
            f"  <mandatory_protocol>{description}</mandatory_protocol>\n"
            f"</active_skill>"
        )

    def _build_ask_system_prompt(
        self,
        context: dict,
        previous_context: dict = None,
        conversation_history: list = None,
        skill=None,
        context_result=None,
    ) -> str:
        """Build the single-shot ask prompt from cached or fresh context."""
        if context_result is not None:
            # Daemon callers pass a cached ContextualiserResult so prompt
            # construction does not repeat shell history and project scans.
            base = build_ask_prompt(context_result)
        else:
            base = build_prompt(
                mode="ask",
                os_name=context['os_name'],
                shell=context['shell'],
                cwd=str(context['cwd']),
                session_context=previous_context,
            )
        if conversation_history:
            base += "\n\n" + self._format_conversation_history_xml(conversation_history)
        if skill:
            # Prepend skill block so it precedes base instructions
            base = self._build_skill_xml(skill) + "\n\n" + base
        return base

    def _build_ask_step_prompt(
        self,
        question: str,
        step_number: int,
        max_steps: int,
        context: dict,
        previous_context: dict = None,
        conversation_history: list = None,
        skill=None,
        prior_observations: list = None,
        context_result=None,
    ) -> str:
        """
        Build prompt for multi-step reasoning (base prompt only, step context added via messages).

        Uses existing context infrastructure for consistency with run/ask modes.
        Includes base context, conversation history, and multi-step instructions.
        Step-specific metadata is NOT included here - it's added as user messages.

        Args:
            question: The original question
            step_number: Current step (unused, kept for compatibility)
            max_steps: Total available steps
            context: Execution context (cwd, os_name, shell)
            previous_context: Optional previous command context
            conversation_history: Optional conversation history

        Returns:
            Base system prompt for multi-step reasoning
        """
        if context_result is not None:
            base_prompt = build_ask_prompt(context_result)
        else:
            from codedjinn.context import contextualise

            ctx = contextualise(
                os_name=context['os_name'],
                shell=context['shell'],
                cwd=str(context['cwd']),
                session_context=previous_context,
            )
            base_prompt = build_ask_prompt(ctx)

        # Skill block leads the prompt so it precedes all other instructions
        sections = []
        if skill:
            sections.append(self._build_skill_xml(skill))
        sections.append(base_prompt)

        # Conversation history section
        if conversation_history:
            sections.append(self._format_conversation_history_xml(conversation_history))

        if prior_observations:
            sections.append(self._format_observations_xml(prior_observations))

        # Multi-step reasoning context
        sections.append(f"""<multi_step_reasoning>
Original question: {question}
Mode: Multi-step reasoning with up to {max_steps} steps
Progress tracking: Step context will be provided as the conversation progresses
</multi_step_reasoning>""")

        # Tool instructions for multi-step
        skill_note = " Follow the active_skill mandatory_protocol above." if skill else ""
        sections.append(f"""<multi_step_instructions>
- Answer directly when existing context is enough.
- For broad file/content searches, use execute_observe_command with `rg` before reading files.
- Use read_file only for specific files that need inspection.
- Use finish_reasoning as soon as you can answer; you do not need to spend every step.
- Stay focused on the original question and keep each command narrow.
- You can reference previous commands in conversation_history for additional context{skill_note}
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

            # Escape XML special characters using utility function
            safe_command = escape_xml_content(command)
            safe_output = escape_xml_content(output)

            lines.append(f"  <exchange number=\"{i}\">")
            lines.append(f"    <command>{safe_command}</command>")
            lines.append(f"    <exit_code>{exit_code}</exit_code>")
            lines.append(f"    <output>{safe_output}</output>")
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
