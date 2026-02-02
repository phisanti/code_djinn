"""Mistral-based agent using native tool calling API."""

import json
from typing import Optional, TYPE_CHECKING

from codedjinn.core.agent import Agent
from codedjinn.core.client_cache import get_cached_client
from codedjinn.tools.registry import build_mistral_tool_schema, build_ask_tool_schema
from codedjinn.tools.ask_executor import AskToolExecutor
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

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "mistral-small-latest",
        use_cache: bool = True,
        client: Optional["Mistral"] = None,
    ):
        """
        Initialize Mistral agent.

        Args:
            api_key: Mistral API key (not needed if client is provided)
            model: Model name (e.g., "mistral-small-latest", "codestral-latest")
            use_cache: Use cached client for connection pooling (default: True)
            client: Pre-initialized Mistral client (for daemon mode)

        Performance:
            - client=<Mistral>: Uses pre-initialized client (daemon mode, fastest)
            - use_cache=True: Reuses HTTP connections (~50-100ms faster)
            - use_cache=False: Creates new client each time (testing only)
        """
        if client is not None:
            # Daemon mode: use pre-initialized client (eliminates ~900ms import)
            self.client = client
        elif use_cache and api_key:
            self.client = get_cached_client(api_key, model)
        elif api_key:
            # Only for testing - creates new client without caching
            from mistralai import Mistral
            self.client = Mistral(api_key=api_key)
        else:
            raise ValueError("Either api_key or client must be provided")

        self.model = model

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

    def analyze_with_steps(
        self,
        question: str,
        context: dict,
        max_steps: int = 3,
        previous_context: dict = None,
        conversation_history: list = None
    ) -> str:
        """
        Multi-step reasoning for ask mode with file reading capabilities.
        
        This allows the model to:
        1. Read files for context (via read_file tool)
        2. Gather observations across multiple steps
        3. Synthesize a final answer using finish_reasoning tool
        
        The model receives step-aware prompts with:
        - Base context from build_ask_prompt() (system, shell history, project context)
        - Prior observations from previous steps
        - Step budget metadata (current step, remaining steps)
        - Multi-step specific instructions
        
        Args:
            question: User's question to answer
            context: Execution context (cwd, os_name, shell)
            max_steps: Maximum number of reasoning steps (1-5, default 3)
            previous_context: Optional dict with previous command/output
            conversation_history: Optional list of previous exchanges (Phase 4)
            
        Returns:
            Final synthesized answer from the model
            
        Flow:
            1. Initialize step budget tracking
            2. For each step (1 to max_steps):
               a. Build step-aware prompt with observations
               b. Call Mistral with ask tools
               c. Execute any read_file calls
               d. Check for finish_reasoning and return early
               e. Advance step budget
            3. Synthesize answer from observations if no finish_reasoning
            
        Example:
            >>> agent.analyze_with_steps(
            ...     "why did the test fail?",
            ...     context,
            ...     max_steps=3,
            ...     previous_context={"command": "pytest", "output": "FAIL..."}
            ... )
        """
        observations = []
        executor = AskToolExecutor(cwd=str(context['cwd']))
        
        # Initialize step budget tracking
        session_state = init_session_state_for_steps(max_steps)
        
        for step_num in range(1, max_steps + 1):
            # Refresh step context before building prompt
            refresh_step_context(session_state)
            step_context = session_state.get("step_context", {})
            
            # Build prompt for this step (uses existing infrastructure)
            prompt = self._build_ask_step_prompt(
                question=question,
                step_number=step_num,
                max_steps=max_steps,
                prior_observations=observations,
                context=context,
                previous_context=previous_context,
                conversation_history=conversation_history
            )
            
            # Call Mistral with ask mode tools
            response = self.client.chat.complete(
                model=self.model,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": question}
                ],
                tools=self._get_ask_tools(),
                tool_choice="auto",
                temperature=0.3,
                max_tokens=1500,
            )
            
            message = response.choices[0].message
            
            # Check if this is a text response (model chose not to use tools)
            if not hasattr(message, 'tool_calls') or not message.tool_calls:
                # Model provided direct text response (shouldn't happen with tool_choice="auto")
                content = getattr(message, "content", "")
                if isinstance(content, list):
                    return "\n".join(str(part) for part in content).strip()
                return ("" if content is None else str(content)).strip()
            
            # Process tool calls
            for tool_call in message.tool_calls:
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)
                
                if tool_name == "finish_reasoning":
                    # Model decided to provide final answer (early termination)
                    answer = tool_args.get("answer", "")
                    return answer.strip()
                
                elif tool_name == "read_file":
                    # Execute file read
                    path = tool_args.get("path", "")
                    context_str = tool_args.get("context", "")
                    
                    result = executor.execute_read_file(path)
                    
                    # Record observation for next step
                    observations.append({
                        'step': step_num,
                        'tool': 'read_file',
                        'path': path,
                        'context': context_str,
                        'result': result
                    })
            
            # Advance step budget for next iteration
            advance_step_budget(session_state)
        
        # If we've exhausted all steps without finish_reasoning, synthesize an answer
        return self._synthesize_from_observations(question, observations)

    def _get_ask_tools(self) -> list[dict]:
        """Get tool schema for ask mode."""
        return build_ask_tool_schema()

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
        Build prompt for a single reasoning step in ask mode.
        
        Uses existing contextualiser infrastructure for consistency with run mode.
        Adds multi-step specific sections (observations, step metadata, instructions).
        
        Args:
            question: The original question
            step_number: Current step (1-indexed)
            max_steps: Total available steps
            prior_observations: List of observations from previous steps
            context: Execution context (cwd, os_name, shell)
            previous_context: Optional previous command context
            conversation_history: Optional conversation history (Phase 4)
            
        Returns:
            System prompt for this step
        """
        # Use existing context infrastructure for consistency
        from codedjinn.context import contextualise, build_ask_prompt
        
        ctx = contextualise(
            os_name=context['os_name'],
            shell=context['shell'],
            cwd=str(context['cwd']),
            session_context=previous_context,
        )
        
        # Start with base ask prompt (includes system context, shell history, project context)
        base_prompt = build_ask_prompt(ctx)
        
        # Build multi-step specific sections
        sections = [base_prompt]
        
        # Conversation history section (Phase 4 enhancement)
        if conversation_history:
            sections.append(self._format_conversation_history_xml(conversation_history))
        
        # Step metadata section with current progress
        sections.append(f"""<multi_step_reasoning>
Original question: {question}
Progress: Running step {step_number} of {max_steps}
Reasoning mode: Gathering evidence and context to answer the question
</multi_step_reasoning>""")
        
        # Prior observations section
        if prior_observations:
            sections.append(self._format_observations_xml(prior_observations))
        
        # Tool instructions specific to multi-step reasoning
        sections.append("""<multi_step_instructions>
- Use read_file to gather context when needed for a better answer
- When you have enough information, use finish_reasoning to provide final answer
- You can stop early if you've reached a conclusion before using all steps
- Each step should build on previous findings
- Stay focused on answering the original question
- You can reference previous commands in conversation_history for additional context
</multi_step_instructions>""")
        
        # Step budget metadata with urgency escalation
        remaining = max_steps - step_number
        if step_number >= max_steps:
            sections.append(f"""<step_context>
META: ⚠️ FINAL STEP ({step_number}/{max_steps}) - THIS IS YOUR LAST CHANCE
You have reached the absolute final step. NO MORE STEPS REMAIN after this.
IMMEDIATELY use finish_reasoning to provide your final answer.
Do not perform additional reads. Synthesize your answer from all gathered evidence.
</step_context>""")
        elif remaining <= 1:
            sections.append(f"""<step_context>
META: ⚠️ ALMOST DONE (step {step_number} of {max_steps}) - RUSH TO FINISH
You have only {remaining} step remaining after this one.
Please wrap up your investigation and prepare to call finish_reasoning.
Gather any final critical information and prepare your final answer.
</step_context>""")
        elif remaining <= 2:
            sections.append(f"""<step_context>
META: Getting close (step {step_number} of {max_steps}) - Start planning conclusion
You have {remaining} step(s) remaining. Plan to finish_reasoning within the next step or two.
Continue gathering evidence but keep your final synthesis in mind.
</step_context>""")
        else:
            sections.append(f"""<step_context>
META: Step {step_number} of {max_steps} - {remaining} step(s) remaining
Continue investigating systematically. You have plenty of steps remaining to be thorough.
</step_context>""")
        
        return "\n".join(sections)
    
    def _format_observations_xml(self, observations: list) -> str:
        """
        Format observations into XML section for prompt.
        
        Args:
            observations: List of observation dicts from prior steps
            
        Returns:
            XML-formatted observations section
        """
        if not observations:
            return ""
        
        lines = ["<prior_observations>"]
        for obs in observations:
            step = obs.get('step', '?')
            tool = obs.get('tool', 'unknown')
            path = obs.get('path', 'N/A')
            context_str = obs.get('context', '')
            result = obs.get('result', '')
            
            # Truncate long results for context budget
            if len(result) > 500:
                result = result[:500] + "\n[... file truncated, showing first 500 chars ...]"
            
            lines.append(f"  <observation step='{step}' tool='{tool}'>")
            lines.append(f"    <target>{path}</target>")
            if context_str:
                lines.append(f"    <reason>{context_str}</reason>")
            lines.append(f"    <content>{result}</content>")
            lines.append(f"  </observation>")
        
        lines.append("</prior_observations>")
        return "\n".join(lines)
    
    def _format_conversation_history_xml(self, conversation_history: list) -> str:
        """
        Format conversation history into XML section for prompt.
        
        This allows the model to reference previous commands and their outputs
        when answering questions in a multi-command workflow.
        
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
            from codedjinn.context.parser import escape_xml_content
            safe_command = escape_xml_content(command)
            safe_output = escape_xml_content(output)
            
            lines.append(f"  <exchange number=\"{i}\">")
            lines.append(f"    <command>{safe_command}</command>")
            lines.append(f"    <exit_code>{exit_code}</exit_code>")
            lines.append(f"    <output>{safe_output}</output>")
            lines.append(f"  </exchange>")
        
        lines.append("</conversation_history>")
        return "\n".join(lines)

    def _synthesize_from_observations(self, question: str, observations: list) -> str:
        """
        Synthesize a final answer from observations when steps are exhausted.
        
        This is a fallback when the model doesn't call finish_reasoning.
        Uses an LLM call to synthesize based on gathered observations.
        
        Args:
            question: The original question
            observations: List of observations gathered across steps
            
        Returns:
            Synthesized answer based on observations
        """
        if not observations:
            return "Could not gather enough information to answer the question."
        
        # Format observations for synthesis
        obs_text = self._format_observations_for_synthesis(observations)
        
        # Use LLM to synthesize final answer from observations
        synthesis_prompt = f"""You are Code Djinn. Based on the gathered information below, 
provide a clear, concise answer to the original question.

Original question: {question}

Gathered information:
{obs_text}

Synthesis: Provide a comprehensive answer based on the information gathered."""
        
        try:
            response = self.client.chat.complete(
                model=self.model,
                messages=[
                    {"role": "user", "content": synthesis_prompt}
                ],
                temperature=0.3,
                max_tokens=1000,
            )
            
            message = response.choices[0].message
            content = getattr(message, "content", "")
            
            if isinstance(content, list):
                return "\n".join(str(part) for part in content).strip()
            
            return ("" if content is None else str(content)).strip()
        
        except Exception:
            # Fallback to simple synthesis if LLM call fails
            return self._format_observations_for_synthesis(observations)
    
    def _format_observations_for_synthesis(self, observations: list) -> str:
        """
        Format observations into readable text for synthesis.
        
        Args:
            observations: List of observation dicts
            
        Returns:
            Formatted observations as readable text
        """
        if not observations:
            return ""
        
        lines = []
        for obs in observations:
            tool = obs.get('tool', 'unknown')
            path = obs.get('path', '')
            context_str = obs.get('context', '')
            result = obs.get('result', '')
            
            # Build readable observation entry
            if tool == 'read_file':
                lines.append(f"\n[File: {path}]")
                if context_str:
                    lines.append(f"Reason: {context_str}")
                # Limit result to first 500 chars for readability
                if len(result) > 500:
                    result = result[:500] + "\n[... content truncated ...]"
                lines.append(result)
        
        return "\n".join(lines)

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
        Build system prompt for run mode with execution context.

        Uses the new context API which automatically includes:
        - System context (OS, shell, working directory)
        - Shell history context (recent commands from user's shell)
        - Local project context (git, virtualenv, Makefile, project type)
        - Session context (previous Code Djinn command + output)
        """
        return build_prompt(
            mode="run",
            os_name=context['os_name'],
            shell=context['shell'],
            cwd=str(context['cwd']),
            session_context=previous_context,
        )

    def _build_ask_system_prompt(self, context: dict, previous_context: dict = None) -> str:
        """
        Build ask-mode system prompt with optional previous command context.

        Uses the new context API for consistent prompt building.
        """
        return build_prompt(
            mode="ask",
            os_name=context["os_name"],
            shell=context["shell"],
            cwd=str(context["cwd"]),
            session_context=previous_context,
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
