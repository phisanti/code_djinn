from agno.agent import Agent

from codedjinn.core.configs import (
    AgentSettings,
    ModelConfig,
    get_agent_settings,
    get_model_config,
    load_raw_config,
)
from codedjinn.core.parser import parse_response
from codedjinn.providers.model import build_model
from codedjinn.tools.registry import get_tools
from codedjinn.prompts.system_prompt import get_system_prompt
from codedjinn.prompts.step_budget import (
    advance_step_budget,
    init_session_state_for_steps,
    normalize_max_steps,
)


def _make_step_budget_tool_hook(session_state: dict) -> object:
    """
    Tool hook that advances the step budget after each tool call.

    This relies on Agno including `session_state` in the system message between
    tool calls when add_session_state_to_context=True.
    """

    def hook(*, func=None, function=None, args=None, arguments=None, **_kwargs):
        next_func = func or function
        call_args = args if args is not None else (arguments or {})
        result = next_func(**call_args)
        advance_step_budget(session_state)
        return result

    return hook


def get_agent(
    config: dict | None = None,
    *,
    include_tools: bool = False,
    instructions_override: str | None = None,
    max_steps: int | None = None,
    session_state_for_hooks: dict | None = None,
) -> Agent:
    """
    Build a minimal Agno agent using the stored configuration.
    """
    raw = config or load_raw_config()

    model_cfg: ModelConfig = get_model_config(raw)
    agent_settings: AgentSettings = get_agent_settings(raw)

    model = build_model(
        provider=model_cfg.provider,
        model_id=model_cfg.model,
        api_key=model_cfg.api_key,
        temperature=model_cfg.temperature,
        max_tokens=model_cfg.max_tokens,
        timeout=model_cfg.timeout,
    )

    instructions = instructions_override or agent_settings.instructions
    if not instructions:
        instructions = get_system_prompt()

    tools = get_tools(raw) if include_tools else []

    max_steps = normalize_max_steps(max_steps)
    tool_call_limit = None
    tool_hooks = None
    if include_tools and max_steps is not None:
        # Treat "steps" as total turns including the final answer.
        # This maps neatly to a tool call limit of (steps - 1).
        tool_call_limit = max(0, max_steps - 1)
        if session_state_for_hooks is not None:
            tool_hooks = [_make_step_budget_tool_hook(session_state_for_hooks)]

    return Agent(
        model=model,
        instructions=instructions,
        markdown=agent_settings.markdown,
        add_history_to_context=agent_settings.add_history_to_context,
        tools=tools,
        tool_call_limit=tool_call_limit,
        tool_hooks=tool_hooks,
    )


def run_and_parse(
    prompt: str = "hello",
    config: dict | None = None,
    *,
    include_tools: bool = False,
    instructions_override: str | None = None,
    max_steps: int | None = None,
) -> dict[str, str]:
    """
    Convenience helper to run a prompt and parse out minimal fields.
    """
    max_steps = normalize_max_steps(max_steps)
    session_state = init_session_state_for_steps(max_steps) if max_steps is not None else None

    agent = get_agent(
        config,
        include_tools=include_tools,
        instructions_override=instructions_override,
        max_steps=max_steps,
        session_state_for_hooks=session_state,
    )
    raw = agent.run(
        prompt,
        session_state=session_state,
        add_session_state_to_context=session_state is not None,
    )
    return parse_response(raw)


if __name__ == "__main__":
    # This will reach out to the configured provider. Use sparingly.
    print(run_and_parse("hello"))
